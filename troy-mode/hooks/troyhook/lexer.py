"""Turning command text into words, operators, and redirections (design 7.1).

The lexer reads Bash syntax and PowerShell syntax at best effort. It drops
heredoc bodies from the words, and keeps the command substitutions found
inside words as token lists for the parser.
"""

import re

MAX_DEPTH = 16
BREAK = frozenset(" \t\r\n;&|()<>")
_OPERATORS = ("&&", "||", ";;", "|&", ";", "|", "&", "(", ")")
_REDIRECT = re.compile(r"\d*(?:<<<|<<-|<<|&>>|&>|>>|>&|<&|<>|>\||>|<)|\*>>?")
_VARIABLE = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*|[0-9@*#?$!-])")
_PS_VARIABLE = re.compile(r"\$[A-Za-z_][A-Za-z0-9_:]*")
_ANSI_C = re.compile(r"(?:\\.|[^'\\])*'", re.S)


class ParseError(Exception):
    """Raised when a command cannot be split, for example for an unbalanced quote."""


class Word:
    """One shell word.

    Attributes:
        value: The word after quote removal. Expansions stay as written.
        raw: The word's source text.
        literal: False when the word holds an expansion or a glob, so its
            value is not what the shell will use.
        subs: Token lists of the command substitutions inside the word.
    """

    __slots__ = ("value", "raw", "literal", "subs")

    def __init__(self, value: str, raw: str, literal: bool = True, subs: list | None = None):
        """Stores the word."""
        self.value, self.raw, self.literal, self.subs = value, raw, literal, subs or []


class Op:
    """A control operator, a parenthesis, or a line break."""

    __slots__ = ("text",)

    def __init__(self, text: str):
        """Stores the operator."""
        self.text = text


class Redirect:
    """A redirection operator. The next word is its target."""

    __slots__ = ("text",)

    def __init__(self, text: str):
        """Stores the operator."""
        self.text = text


class Shared:
    """State shared by a lexer and the lexers it starts for nested text.

    Attributes:
        powershell: Read PowerShell syntax instead of Bash.
        heredocs: The bodies of every heredoc and here-string.
        extra: Token lists of substitutions found in unquoted heredoc bodies.
    """

    def __init__(self, powershell: bool, heredocs: list | None = None,
                 extra: list | None = None):
        """Starts empty lists unless shared ones are given."""
        self.powershell = powershell
        self.heredocs = heredocs if heredocs is not None else []
        self.extra = extra if extra is not None else []


class Lexer:
    """Turns command text into words, operators, and redirections."""

    def __init__(self, text: str, shared: Shared, depth: int, start: int = 0):
        """Starts a lexer at a position in a text."""
        if depth > MAX_DEPTH:
            raise ParseError("commands nested too deeply")
        self.s, self.i, self.shared, self.depth = text, start, shared, depth
        self.ps = shared.powershell
        self.pending: list[tuple[str, bool, bool]] = []

    def lex(self, until_paren: bool = False) -> list:
        """Reads tokens to the end of the text, or to the ")" that closes "$(".

        Raises:
            ParseError: A quote, substitution, or "$(" is not closed.
        """
        tokens, depth = [], 0
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in " \t\r" or (c == "\\" and not self.ps and self.s.startswith("\\\n", self.i)):
                self.i += 1 if c != "\\" else 2
            elif c == "\n":
                tokens.append(Op("\n"))
                self.i += 1
                self._read_heredocs()
            elif c == "#" or (self.ps and self.s.startswith("<#", self.i)):
                self._comment()
            elif c == ")" and until_paren and depth == 0:
                return tokens
            else:
                depth += self._token(tokens)
        if until_paren:
            raise ParseError("unclosed $(")
        return tokens

    def _token(self, tokens: list) -> int:
        """Reads one operator, redirection, or word; returns the change in "(" depth."""
        s, i = self.s, self.i
        if not self.ps and s[i] in "<>" and s.startswith("(", i + 1):
            self.i += 2
            tokens.append(Word(s[i:i + 1], s[i:i + 2], False, [self._until_paren()]))
            tokens[-1].raw = s[i:self.i]
            return 0
        redirect = _REDIRECT.match(s, i)
        if redirect and not s.startswith("&&", i):
            self.i = redirect.end()
            tokens.append(Redirect(redirect.group(0)))
            if not self.ps and redirect.group(0).lstrip("0123456789") in ("<<", "<<-"):
                tokens.append(self._heredoc_start(redirect.group(0).endswith("-")))
            return 0
        for op in _OPERATORS:
            if s.startswith(op, i):
                self.i += len(op)
                tokens.append(Op(op))
                return {"(": 1, ")": -1}.get(op, 0)
        if self.ps and s.startswith(("@'", '@"'), i):
            tokens.append(self._here_string())
            return 0
        tokens.append(self._word())
        return 0

    def _comment(self) -> None:
        """Skips a comment: to the line end, or to "#>" for a PowerShell block comment."""
        if self.ps and self.s.startswith("<#", self.i):
            end = self.s.find("#>", self.i + 2)
            self.i = len(self.s) if end < 0 else end + 2
            return
        end = self.s.find("\n", self.i)
        self.i = len(self.s) if end < 0 else end

    def _heredoc_start(self, strip_tabs: bool) -> Word:
        """Reads a heredoc's delimiter word and queues its body for the next line."""
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1
        if self.i >= len(self.s) or self.s[self.i] in BREAK:
            raise ParseError("heredoc without a delimiter")
        word = self._word()
        expand = not any(q in word.raw for q in "'\"\\")
        self.pending.append((word.value, strip_tabs, expand))
        return word

    def _read_heredocs(self) -> None:
        """Reads the bodies of the heredocs started on the line just ended."""
        for delimiter, strip_tabs, expand in self.pending:
            lines = []
            while self.i < len(self.s):
                end = self.s.find("\n", self.i)
                line = self.s[self.i:] if end < 0 else self.s[self.i:end]
                self.i = len(self.s) if end < 0 else end + 1
                check = line.lstrip("\t") if strip_tabs else line
                if check.rstrip("\r") == delimiter:
                    break
                lines.append(line)
            body = "\n".join(lines)
            self.shared.heredocs.append(body)
            if expand and ("$(" in body or "`" in body):
                self._body_substitutions(body)
        self.pending = []

    def _body_substitutions(self, body: str) -> None:
        """Collects the command substitutions of an unquoted heredoc body, which run."""
        inner = Lexer(body, self.shared, self.depth + 1)
        subs: list = []
        try:
            inner.double(subs, [], closing=None)
        except ParseError:
            return
        self.shared.extra.extend(subs)

    def _here_string(self) -> Word:
        """Reads a PowerShell here-string (@'...'@ or @"..."@) as one word."""
        quote = self.s[self.i + 1]
        end = self.s.find("\n" + quote + "@", self.i + 2)
        if end < 0:
            raise ParseError("unclosed here-string")
        start, self.i = self.i, end + 3
        body = self.s[start + 2:end].lstrip("\r\n")
        self.shared.heredocs.append(body)
        return Word(body, self.s[start:self.i], False)

    def _word(self) -> Word:
        """Reads one word, removing quotes and noting substitutions."""
        start, value, subs, literal = self.i, [], [], True
        while self.i < len(self.s) and self.s[self.i] not in BREAK:
            c = self.s[self.i]
            if (c == "\\" and not self.ps) or (c == "`" and self.ps):
                nxt = self.s[self.i + 1:self.i + 2]
                value.append("" if nxt == "\n" else nxt)
                self.i += 2
            elif c == "'":
                value.append(self._single())
            elif c == '"':
                self.i += 1
                literal &= self.double(subs, value, closing='"')
            elif c == "$":
                literal &= self._dollar(value, subs)
            elif c == "`":
                self._backtick(value, subs)
                literal = False
            else:
                literal &= c not in "*?["
                value.append(c)
                self.i += 1
        return Word("".join(value), self.s[start:self.i], literal, subs)

    def _single(self) -> str:
        """Reads a single-quoted string; PowerShell doubles a quote to escape it."""
        out = []
        self.i += 1
        while True:
            end = self.s.find("'", self.i)
            if end < 0:
                raise ParseError("unbalanced single quote")
            out.append(self.s[self.i:end])
            self.i = end + 1
            if not (self.ps and self.s.startswith("'", self.i)):
                return "".join(out)
            out.append("'")
            self.i += 1

    def double(self, subs: list, value: list, closing: str | None) -> bool:
        """Reads double-quoted text up to closing, or to the end when closing is None.

        Returns:
            True when the text holds no expansion.

        Raises:
            ParseError: closing is not found.
        """
        literal = True
        while self.i < len(self.s):
            c, nxt = self.s[self.i], self.s[self.i + 1:self.i + 2]
            if c == closing and not (self.ps and nxt == '"'):
                self.i += 1
                return literal
            if (c == '"' and self.ps and nxt == '"') or (self.ps and c == "`"):
                value.append(nxt)
                self.i += 2
            elif c == "\\" and not self.ps and nxt in ('"', "\\", "$", "`", "\n"):
                value.append("" if nxt == "\n" else nxt)
                self.i += 2
            elif c == "`":
                self._backtick(value, subs)
                literal = False
            elif c == "$":
                literal &= self._dollar(value, subs)
            else:
                value.append(c)
                self.i += 1
        if closing is None:
            return literal
        raise ParseError("unbalanced double quote")

    def _until_paren(self) -> list:
        """Lexes from the current position to the matching ")", then skips it."""
        inner = Lexer(self.s, self.shared, self.depth + 1, self.i)
        tokens = inner.lex(until_paren=True)
        self.i = inner.i + 1
        return tokens

    def _dollar(self, value: list, subs: list) -> bool:
        """Reads an expansion that starts with "$"; returns True if it is literal text."""
        s, i = self.s, self.i
        if s.startswith("$((", i) and not self.ps:
            self.i = self._close(i + 3, "(", ")", 2)
        elif s.startswith("$(", i):
            self.i += 2
            subs.append(self._until_paren())
        elif s.startswith("${", i):
            self.i = self._close(i + 2, "{", "}", 1)
        elif s.startswith("$'", i) and not self.ps:
            end = _ANSI_C.match(s, i + 2)
            if not end:
                raise ParseError("unbalanced $' quote")
            value.append(s[i + 2:end.end() - 1])
            self.i = end.end()
            return True
        else:
            match = (_PS_VARIABLE if self.ps else _VARIABLE).match(s, i)
            if not match:
                value.append("$")
                self.i += 1
                return True
            self.i = match.end()
        value.append(s[i:self.i])
        return False

    def _close(self, start: int, opening: str, closing: str, depth: int) -> int:
        """Finds the end of a bracketed expansion by counting brackets."""
        for j in range(start, len(self.s)):
            depth += {opening: 1, closing: -1}.get(self.s[j], 0)
            if depth == 0:
                return j + 1
        raise ParseError(f"unclosed {opening}")

    def _backtick(self, value: list, subs: list) -> None:
        """Reads a backtick command substitution."""
        j, inner = self.i + 1, []
        while j < len(self.s) and self.s[j] != "`":
            if self.s[j] == "\\" and j + 1 < len(self.s):
                pair = self.s[j:j + 2]
                inner.append(pair[1] if pair[1] in "`\\$" else pair)
                j += 2
                continue
            inner.append(self.s[j])
            j += 1
        if j >= len(self.s):
            raise ParseError("unbalanced backtick")
        subs.append(Lexer("".join(inner), self.shared, self.depth + 1).lex())
        value.append(self.s[self.i:j + 1])
        self.i = j + 1
