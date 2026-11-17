"""GitHub CLI commands: the read-only list for subagents, R19, and R21 (design 7.3, 8.2).

F15 adds its issue and label commands to the posting table and refuses deleting issues
and labels (F15 design 10.2, D148).
"""

import re

from .lexer import Op, Redirect, Word
from .paths import to_native
from .scopes import MAIN
from .shell import Parsed, SimpleCommand
from .verdict import RULE_6, Refusal

GH_READ = {
    "pr": frozenset({"view", "diff", "list", "checks", "status"}),
    "issue": frozenset({"view", "list", "status"}),
    "repo": frozenset({"view"}),
    "run": frozenset({"view", "list"}),
    "release": frozenset({"view", "list"}),
    "auth": frozenset({"status"}),
}
_GH_ANY = frozenset({"search", "status", "help", "version"})

_TITLE, _BODY = ("--title", "-t"), ("--body", "-b")
_BODY_FILE, _NOTES_FILE = ("--body-file", "-F"), ("--notes-file", "-F")
# The gh commands that post text, with the options that hold it and the
# options that name a file holding it (design 8.2, D200). "gh api" is apart.
POSTING = {
    ("pr", "create"): ((_TITLE, _BODY), (_BODY_FILE,)),
    ("pr", "edit"): ((_TITLE, _BODY), (_BODY_FILE,)),
    ("issue", "create"): ((_TITLE, _BODY), (_BODY_FILE,)),
    ("issue", "edit"): ((_TITLE, _BODY), (_BODY_FILE,)),
    ("pr", "comment"): ((_BODY,), (_BODY_FILE,)),
    ("issue", "comment"): ((_BODY,), (_BODY_FILE,)),
    ("pr", "review"): ((_BODY,), (_BODY_FILE,)),
    ("pr", "merge"): ((("--subject", "-t"), _BODY), (_BODY_FILE,)),
    ("release", "create"): ((_TITLE, ("--notes", "-n")), (_NOTES_FILE,)),
    ("release", "edit"): ((_TITLE, ("--notes", "-n")), (_NOTES_FILE,)),
    ("issue", "close"): ((("--comment", "-c"),), ()),
    ("issue", "reopen"): ((("--comment", "-c"),), ()),
    ("label", "create"): ((("--description", "-d"),), ()),
    ("label", "edit"): ((("--description", "-d"),), ()),
}
# Deleting is irreversible and outside troy-mode's rights (F15 D148, F07 design 9).
DELETES = frozenset({("issue", "delete"), ("label", "delete")})
_HIDDEN = ("--editor", "-e", "--web", "-w")
_ABSOLUTE = re.compile(r"^(?:[/\\~]|[A-Za-z]:)")


def _split_gh(values: list[str]) -> tuple[str | None, str | None, list[str]]:
    """Finds a gh command's group, subcommand, and the words after the group."""
    found, i = [], 0
    while i < len(values) and len(found) < 2:
        value = values[i]
        if value in ("-R", "--repo"):
            i += 2
            continue
        if not value.startswith("-"):
            found.append(i)
        i += 1
    if not found:
        return None, None, []
    group = values[found[0]]
    sub = values[found[1]] if len(found) > 1 else None
    return group, sub, values[found[0] + 1:]


def _gh_api_reads(args: list[str]) -> bool:
    """Tells whether "gh api" only reads: method GET and no fields or input (7.3)."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-f", "-F", "--field", "--raw-field", "--input") or arg.startswith(
                ("--field=", "--raw-field=", "--input=")) or arg[:2] in ("-f", "-F"):
            return False
        if arg in ("-X", "--method"):
            if i + 1 >= len(args) or args[i + 1].upper() != "GET":
                return False
            i += 1
        elif arg.startswith(("--method=", "-X")):
            if arg.split("=", 1)[-1].removeprefix("-X").upper() != "GET":
                return False
        elif arg in ("-H", "--header", "-q", "--jq", "-t", "--template", "--hostname",
                     "--cache", "-p", "--preview"):
            i += 1
        i += 1
    return True


def gh_read_only(group: str | None, sub: str | None, rest: list[str]) -> bool:
    """Tells whether a subagent may run a gh command (design 7.3)."""
    if group is None or group in _GH_ANY:
        return True
    if group == "api":
        return _gh_api_reads(rest)
    return sub in GH_READ.get(group, ())


def gh_posts(group: str | None, sub: str | None, rest: list[str]) -> bool:
    """Tells whether a gh command posts text to GitHub (design 8.2, D200), or deletes (F15)."""
    if (group, sub) in DELETES:
        return True
    if group == "api":
        return not _gh_api_reads(rest)
    return (group, sub) in POSTING


def _option_values(words: list[Word], long: str, short: str) -> list[Word]:
    """Collects the values of one option in its "--x v", "--x=v", "-x v", and "-xv" forms."""
    found = []
    for i, word in enumerate(words):
        value = word.value
        if (value == long or (short and value == short)) and i + 1 < len(words):
            found.append(words[i + 1])
        elif value.startswith(long + "="):
            found.append(Word(value[len(long) + 1:], word.raw, word.literal))
        elif short and value.startswith(short) and len(value) > 2 and not value.startswith("--"):
            found.append(Word(value[2:], word.raw, word.literal))
    return found


def _from_main(ctx, words: list[Word]) -> bool:
    """Tells whether "gh pr create" opens a PR from main (R21)."""
    heads = _option_values(words, "--head", "-H")
    if heads:
        return heads[-1].value.split(":")[-1] == "main"
    return ctx.project.branch() == "main"


class _Unreadable(Exception):
    """Text a posting command would send that the hook cannot read (fail closed, D200)."""


def _heredoc_cat(tokens: list) -> bool:
    """Tells whether a command substitution only prints its heredocs: "cat <<'EOF' ...".

    The heredoc bodies are checked with the rest of the call's heredocs.
    """
    if not tokens or not isinstance(tokens[0], Word) or tokens[0].value != "cat":
        return False
    after_heredoc = False
    for token in tokens[1:]:
        if isinstance(token, Redirect):
            if token.text not in ("<<", "<<-"):
                return False
            after_heredoc = True
        elif isinstance(token, Word):
            if not after_heredoc:
                return False
            after_heredoc = False
        elif isinstance(token, Op) and token.text.strip():
            return False
    return True


def _text_of(word: Word) -> list[str]:
    """Gives an option's text, refusing a variable or a substitution the hook cannot see."""
    if not word.literal and not (word.subs and all(_heredoc_cat(sub) for sub in word.subs)):
        raise _Unreadable(f"the text {word.raw!r} holds a variable or a command the hook "
                          "cannot see")
    return [word.value, word.raw]


def _file_text(ctx, cmd: SimpleCommand, parsed: Parsed, word: Word) -> str:
    """Reads a named body, notes, or input file as it is when the call starts."""
    if word.value == "-":
        if not parsed.heredocs:
            raise _Unreadable("it reads the text from a pipe (\"-\") with no heredoc in the call")
        return ""
    if not word.literal or not word.value:
        raise _Unreadable(f"the file {word.raw!r} is named by a variable or a command the hook "
                          "cannot follow; name it by its path")
    if cmd.cwd is None and not _ABSOLUTE.match(word.value):
        raise _Unreadable("a file is named relative to a folder the hook cannot follow")
    try:
        with open(to_native(word.value, cmd.cwd or ctx.cwd), encoding="utf-8",
                  errors="replace") as handle:
            return handle.read()
    except OSError:
        raise _Unreadable("a named file is missing or unreadable") from None


def _api_parts(words: list[Word]) -> tuple[list[Word], list[Word]]:
    """Splits "gh api"'s fields into text and named files: -f, -F key=@file, --input."""
    texts, files = [], []
    for long, short in (("--raw-field", "-f"), ("--field", "-F")):
        for word in _option_values(words, long, short):
            key, sep, value = word.value.partition("=")
            if short == "-F" and sep and value.startswith("@"):
                files.append(Word(value[1:], word.raw, word.literal))
            else:
                texts.append(word)
    files += _option_values(words, "--input", "")  # no short form
    return texts, files


def _posted_text(ctx, cmd: SimpleCommand, parsed: Parsed, group: str, sub: str | None) -> str:
    """Gathers the text a posting command sends: option values, heredocs, and files (D200)."""
    if group == "api":
        texts, files = _api_parts(cmd.words)
    else:
        if any(word.value in _HIDDEN or word.value.startswith(("--editor=", "--web="))
               for word in cmd.words):
            raise _Unreadable("--editor and --web write the text where the hook cannot see it")
        text_options, file_options = POSTING[(group, sub)]
        texts = [word for long, short in text_options
                 for word in _option_values(cmd.words, long, short)]
        files = [word for long, short in file_options
                 for word in _option_values(cmd.words, long, short)]
    parts = [part for word in texts for part in _text_of(word)]
    parts += parsed.heredocs
    parts += [_file_text(ctx, cmd, parsed, word) for word in files]
    return "\n".join(parts)


def _check_posting(ctx, cmd: SimpleCommand, parsed: Parsed, group: str, sub: str | None,
                   label: str) -> Refusal | None:
    """Checks the text a main-session gh command posts for R19 (design 8.2, D200)."""
    try:
        text = _posted_text(ctx, cmd, parsed, group, sub)
    except _Unreadable as exc:
        return Refusal("attribution", f"R19: `{label}` posts text the hook cannot check: {exc}. "
                       "Write the text to a file in an earlier call, check it with "
                       "`troy_flow.py check-text --file <file>`, and pass the file by name "
                       "(F05 D200).", label)
    from troycheck.attribution import find_attribution  # noqa: PLC0415  (slow to import)

    mode = ctx.config().attribution_mode
    lines = find_attribution(text, mode)
    if not lines:
        return None
    rows = text.splitlines()
    snippet = rows[lines[0] - 1].strip()[:80] if 0 < lines[0] <= len(rows) else ""
    return Refusal("attribution", f"R19: the text `{label}` would post fails the attribution "
                   f"check ([attribution] mode {mode}) at {snippet!r}. Reword it, check it with "
                   "`troy_flow.py check-text`, and post it in a later call (F05 D200).", label)


def check_gh(ctx, cmd: SimpleCommand, parsed: Parsed) -> Refusal | None:
    """Checks one gh command (design 7.3 for subagents, 8.2 for every caller)."""
    group, sub, rest = _split_gh([word.value for word in cmd.words[1:]])
    label = " ".join(part for part in ("gh", group, sub if group != "api" else None) if part)
    if ctx.caller.kind == MAIN and (group, sub) in DELETES:
        return Refusal("gh-delete", f"`{label}` deletes what cannot be restored, and deleting "
                       "issues and labels is outside troy-mode's rights (F15 D148). Ask Troy.",
                       label)
    if ctx.caller.kind != MAIN:
        if gh_read_only(group, sub, rest):
            return None
        return Refusal("gh", f"`{label}` changes GitHub or is not on the read-only list for "
                       f"subagents. {RULE_6}", label)
    if not gh_posts(group, sub, rest):
        return None
    if (group, sub) == ("pr", "create") and _from_main(ctx, cmd.words):
        return Refusal("pr-from-main", "R21: never open a PR from main. Create a branch, "
                       "commit there, push it, and open the PR from it.", label)
    return _check_posting(ctx, cmd, parsed, group, sub, label)
