"""Splitting a shell command into simple commands (design section 7.1).

This is not a shell. It finds each program a command line runs, the words
given to it, and the folder it runs in, which is all the git and gh checks
need. It skips leading assignments and the wrappers command, env, exec,
nohup, time, and xargs, reads the string after bash -c, sh -c, and eval as a
command, and follows "cd <literal path>".
"""

import os
import re

from .lexer import Lexer, Op, ParseError, Redirect, Shared, Word
from .paths import to_native
from .variables import expand, value_of

_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?\+?=")
_ABSOLUTE = re.compile(r"^(?:[/\\~]|[A-Za-z]:[/\\])")
_KEYWORDS = frozenset({"if", "then", "else", "elif", "fi", "do", "done", "while", "until",
                       "{", "}", "!", "esac", "coproc"})
_WORD_LISTS = frozenset({"for", "select", "case", "function", "foreach"})
_CD = frozenset({"cd", "pushd", "chdir", "set-location", "sl", "push-location"})
_POPD = frozenset({"popd", "pop-location"})
_SHELLS = frozenset({"bash", "sh"})
_DECLARE = frozenset({"export", "declare", "typeset", "readonly", "local"})
_XARGS_WITH_VALUE = frozenset({"-I", "-n", "-L", "-P", "-d", "-a", "-E", "-s"})


class SimpleCommand:
    """One program run, with wrappers and assignments removed.

    Attributes:
        words: The program and its arguments.
        assignments: Variable assignments written before the program.
        cwd: The real path of the folder it runs in, or None when unknown.
    """

    __slots__ = ("words", "assignments", "cwd")

    def __init__(self, words: list[Word], assignments: dict[str, str], cwd: str | None):
        """Stores the command."""
        self.words, self.assignments, self.cwd = words, assignments, cwd


class Parsed:
    """The result of splitting one command line.

    Attributes:
        commands: Every simple command found, nested ones included.
        heredocs: The bodies of every heredoc and here-string.
        error: Why the line could not be split, or None.
    """

    __slots__ = ("commands", "heredocs", "error")

    def __init__(self, commands: list[SimpleCommand], heredocs: list[str],
                 error: str | None = None):
        """Stores the result."""
        self.commands, self.heredocs, self.error = commands, heredocs, error


def program(value: str) -> str:
    """Names the program a word runs: the last path part, lower case, without .exe."""
    name = re.split(r"[/\\]", value)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


class _Parser:
    """Groups tokens into simple commands and follows "cd" and the variables set."""

    def __init__(self, shared: Shared, depth: int, commands: list,
                 known: dict[str, str] | None = None):
        """Starts a parser that appends to commands, knowing the given variables."""
        self.shared, self.depth, self.commands = shared, depth, commands
        self.known: dict[str, str] = dict(known or {})

    def run(self, tokens: list, cwd: str | None) -> None:
        """Parses one token list. Parentheses open a subshell for "cd"."""
        stack, words, target = [cwd], [], False
        for token in tokens:
            if isinstance(token, Op):
                stack[-1] = self._flush(words, stack[-1])
                words = []
                if token.text == "(":
                    stack.append(stack[-1])
                elif token.text == ")" and len(stack) > 1:
                    stack.pop()
            elif isinstance(token, Redirect):
                target = True
            elif target:
                self._substitutions(token, stack[-1])
                target = False
            else:
                words.append(token)
        self._flush(words, stack[-1])

    def _substitutions(self, word: Word, cwd: str | None) -> None:
        """Parses the command substitutions inside a word, which run in a subshell."""
        for tokens in word.subs:
            self.run(tokens, cwd)

    def _flush(self, words: list[Word], cwd: str | None) -> str | None:
        """Records one simple command; returns the folder for the commands after it."""
        if not words:
            return cwd
        for word in words:
            self._substitutions(word, cwd)
        while words and words[0].raw in _KEYWORDS:
            words = words[1:]
        if not words or words[0].raw in _WORD_LISTS:
            return cwd
        assignments: dict[str, str] = {}
        rest = _take_assignments(words, assignments)
        if not rest:
            self._remember(words, cwd)
            return cwd
        for key, value in assignments.items():
            assignments[key] = expand(Word(value, value, "$" not in value), self.known).value
        words, chdir = _unwrap([expand(word, self.known) for word in rest], assignments)
        if not words:
            return cwd
        name = program(words[0].value)
        if name in _DECLARE:
            self._remember([word for word in words[1:] if _ASSIGN.match(word.raw)], cwd)
            return cwd
        if name in _CD:
            return _cd(words[1:], cwd)
        if name in _POPD:
            return None
        run_in = cwd if chdir is False else chdir
        self.commands.append(SimpleCommand(words, assignments, run_in))
        if name in _SHELLS:
            self._shell_c(words[1:], run_in)
        elif name == "eval":
            self.nested(" ".join(word.value for word in words[1:]), run_in)
        return cwd

    def _remember(self, assigned: list[Word], cwd: str | None) -> None:
        """Records variables a command line sets, forgetting any whose value is unknown."""
        for word in assigned:
            name = word.value.partition("=")[0].rstrip("+")
            value = value_of(word, self.known, cwd)
            if value is None:
                self.known.pop(name, None)
            else:
                self.known[name] = value

    def _shell_c(self, args: list[Word], cwd: str | None) -> None:
        """Parses the command string of "bash -c" and "sh -c"."""
        has_c, i = False, 0
        while i < len(args):
            value = args[i].value
            if value.startswith("--"):
                i += 2 if value in ("--rcfile", "--init-file") else 1
            elif value[:1] in "-+" and len(value) > 1:
                has_c = has_c or "c" in value[1:]
                i += 2 if value in ("-o", "+o", "-O", "+O") else 1
            else:
                break
        if has_c and i < len(args):
            self.nested(args[i].value, cwd)

    def nested(self, text: str, cwd: str | None) -> None:
        """Splits text that another command runs as a command line."""
        shared = Shared(False, self.shared.heredocs, self.shared.extra)
        tokens = Lexer(text, shared, self.depth + 1).lex()
        _Parser(shared, self.depth + 1, self.commands, self.known).run(tokens, cwd)


def _take_assignments(words: list[Word], out: dict[str, str]) -> list[Word]:
    """Removes leading NAME=value words, recording them in out."""
    while words and _ASSIGN.match(words[0].raw):
        name, _, value = words[0].value.partition("=")
        out[name.rstrip("+")] = value
        words = words[1:]
    return words


def _unwrap(words: list[Word], assignments: dict[str, str]) -> tuple[list[Word], object]:
    """Removes the wrappers command, env, exec, nohup, time, and xargs.

    Returns:
        The remaining words (empty for "command -v", which runs nothing), and
        False, or the folder "env -C" names (None when it is not literal).
    """
    chdir: object = False
    while words:
        name, rest = program(words[0].value), words[1:]
        if name == "command":
            while rest and rest[0].value.startswith("-"):
                if any(flag in rest[0].value for flag in "vV"):
                    return [], chdir
                rest = rest[1:]
        elif name == "env":
            rest, chdir = _unwrap_env(rest, assignments, chdir)
        elif name in ("exec", "time", "nohup"):
            while rest and rest[0].value.startswith("-") and name != "nohup":
                rest = rest[2:] if rest[0].value == "-a" else rest[1:]
        elif name == "xargs":
            while rest and rest[0].value.startswith("-"):
                done = rest[0].value == "--"
                rest = rest[2:] if rest[0].value in _XARGS_WITH_VALUE else rest[1:]
                if done:
                    break
        else:
            break
        words = rest
    return words, chdir


def _unwrap_env(rest: list[Word], assignments: dict[str, str], chdir: object):
    """Removes env's options and assignments; returns the rest and any -C folder."""
    while rest:
        value = rest[0].value
        if value in ("-C", "--chdir") and len(rest) > 1:
            chdir = to_native(rest[1].value, ".") if rest[1].literal else None
            rest = rest[2:]
        elif value in ("-u", "--unset", "-S", "--split-string"):
            rest = rest[2:]
        elif value.startswith("-"):
            rest = rest[1:]
        elif _ASSIGN.match(rest[0].raw):
            rest = _take_assignments(rest[:1], assignments) + rest[1:]
        else:
            break
    return rest, chdir


def _cd(args: list[Word], cwd: str | None) -> str | None:
    """Gives the folder after "cd": None when it cannot be known from the text."""
    while args and args[0].value.startswith("-") and args[0].value != "-":
        args = args[1:]
    if not args:
        return os.path.expanduser("~")
    target = args[0]
    if not target.literal or target.value == "-":
        return None
    if cwd is None and not _ABSOLUTE.match(target.value):
        return None
    return to_native(target.value, cwd or ".")


def parse(text: str, cwd: str | None, powershell: bool = False) -> Parsed:
    """Splits a command line into simple commands.

    Args:
        text: The command.
        cwd: The real path of the folder it starts in.
        powershell: Read PowerShell syntax instead of Bash.

    Returns:
        The simple commands and heredoc bodies, or an error when the line
        cannot be split.
    """
    shared = Shared(powershell)
    commands: list[SimpleCommand] = []
    try:
        tokens = Lexer(text, shared, 0).lex()
        parser = _Parser(shared, 0, commands)
        parser.run(tokens, cwd)
        for extra in shared.extra:
            parser.run(extra, cwd)
    except ParseError as exc:
        return Parsed([], shared.heredocs, str(exc))
    except RecursionError:
        return Parsed([], shared.heredocs, "commands nested too deeply")
    return Parsed(commands, shared.heredocs)
