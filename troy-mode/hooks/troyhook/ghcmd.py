"""GitHub CLI commands: the read-only list for subagents, R19, and R21 (design 7.3, 8.2)."""

from .lexer import Word
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


def _option_values(words: list[Word], long: str, short: str) -> list[Word]:
    """Collects the values of one option in its "--x v", "--x=v", "-x v", and "-xv" forms."""
    found = []
    for i, word in enumerate(words):
        value = word.value
        if value in (long, short) and i + 1 < len(words):
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


def _pr_text(ctx, cmd: SimpleCommand, parsed: Parsed) -> str:
    """Gathers a PR's title and description from the command, its heredocs, and --body-file."""
    parts = []
    for long, short in (("--title", "-t"), ("--body", "-b")):
        for word in _option_values(cmd.words, long, short):
            parts += [word.value, word.raw]
    parts += parsed.heredocs
    for word in _option_values(cmd.words, "--body-file", "-F"):
        if word.value != "-":
            try:
                path = to_native(word.value, cmd.cwd or ctx.cwd)
                with open(path, encoding="utf-8", errors="replace") as handle:
                    parts.append(handle.read())
            except OSError:
                continue
    return "\n".join(parts)


def check_gh(ctx, cmd: SimpleCommand, parsed: Parsed) -> Refusal | None:
    """Checks one gh command (design 7.3 for subagents, 8.2 for every caller)."""
    group, sub, rest = _split_gh([word.value for word in cmd.words[1:]])
    label = " ".join(part for part in ("gh", group, sub if group != "api" else None) if part)
    if ctx.caller.kind != MAIN:
        if gh_read_only(group, sub, rest):
            return None
        return Refusal("gh", f"`{label}` changes GitHub or is not on the read-only list for "
                       f"subagents. {RULE_6}", label)
    if group != "pr" or sub not in ("create", "edit"):
        return None
    if sub == "create" and _from_main(ctx, cmd.words):
        return Refusal("pr-from-main", "R21: never open a PR from main. Create a branch, "
                       "commit there, push it, and open the PR from it.", label)
    from troycheck.attribution import find_attribution  # noqa: PLC0415  (slow to import)

    mode = ctx.config().attribution_mode
    text = _pr_text(ctx, cmd, parsed)
    lines = find_attribution(text, mode)
    if lines:
        snippet = text.splitlines()[lines[0] - 1].strip()[:80] if text.splitlines() else ""
        return Refusal("attribution", f"R19: the PR title or description carries Claude "
                       f"attribution ([attribution] mode {mode}): {snippet!r}. Remove it.", label)
    return None
