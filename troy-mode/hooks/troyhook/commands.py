"""Checks of Bash, PowerShell, and Skill calls (design sections 7 and 8.2)."""

import json
import re

from .ghcmd import check_gh, gh_posts, gh_read_only
from .gitcmd import ALWAYS, check_git
from .scopes import MAIN
from .shell import parse, program
from .verdict import RULE_6, Refusal

_GIT_IN_TEXT = re.compile(r"(?:^|[\s;&|()`'\"$/\\=])git(?:\.exe)?[ \t]+([^\n;&|)`]*)", re.I)
_GH_IN_TEXT = re.compile(r"(?:^|[\s;&|()`'\"$/\\=])gh(?:\.exe)?[ \t]+([^\n;&|)`]*)", re.I)
_REVIEW_SKILLS = frozenset({"code-review", "security-review"})
_FIX_OR_COMMENT = re.compile(r"(?:^|\s)--(?:fix|comment)(?=$|[\s=])")


def _first_word(text: str, skip_values: tuple[str, ...]) -> tuple[str | None, list[str]]:
    """Reads the first non-option word of rough command text, without quotes."""
    tokens = [token.strip("'\"") for token in text.split()]
    i = 0
    while i < len(tokens):
        if tokens[i] in skip_values:
            i += 2
        elif tokens[i].startswith("-"):
            i += 1
        else:
            return tokens[i], tokens[i + 1:]
    return None, []


def _gh_in_text(text: str, wanted, api_target: bool) -> str | None:
    """Finds a gh command in rough text for which wanted(group, sub, rest) holds.

    The name it gives keeps "gh api"'s endpoint only when api_target is true.
    """
    for match in _GH_IN_TEXT.finditer(text):
        group, rest = _first_word(match.group(1), ("-R", "--repo"))
        sub = next((token for token in rest if not token.startswith("-")), None)
        if group and wanted(group, sub, rest):
            shown = sub if api_target or group != "api" else None
            return " ".join(part for part in ("gh", group, shown) if part)
    return None


def post_in_text(text: str) -> str | None:
    """Finds a gh command that posts text to GitHub in rough command text (D200)."""
    return _gh_in_text(text, gh_posts, api_target=False)


def _write_in_text(text: str) -> str | None:
    """Finds a git or gh write in text that could not be split (design 7.1)."""
    for match in _GIT_IN_TEXT.finditer(text):
        sub, _ = _first_word(match.group(1), ("-C", "-c", "--git-dir", "--work-tree"))
        if sub and sub not in ALWAYS:
            return "git " + sub
    return _gh_in_text(text, lambda group, sub, rest: not gh_read_only(group, sub, rest),
                       api_target=True)


def _check_unparsed(ctx, text: str, error: str) -> Refusal | None:
    """Checks a command that could not be split, by its text alone."""
    if ctx.caller.kind == MAIN:
        if re.search(r"\bgit\b", text) and re.search(r"core\.hookspath", text, re.I):
            return Refusal("hooks-path", "The command mentions core.hooksPath and could not "
                           f"be split ({error}). Nobody but Troy changes it (F05 8.2).", "git")
        if re.search(r"\bgit\b[^\n]*--no-verify", text):
            return Refusal("no-verify", "The command uses --no-verify and could not be split "
                           f"({error}). Run git without it (F05 8.2).", "git")
        posting = post_in_text(text)
        if posting:
            return Refusal("unparsed", f"The command could not be split ({error}), and its text "
                           f"holds `{posting}`, which posts text to GitHub that the hook must "
                           "check first, or deletes there (R19, F05 D200, F15 D148). Write the command so that its quotes "
                           "balance.", posting)
        return None
    found = _write_in_text(text)
    if found is None:
        return None
    return Refusal("unparsed", f"The command could not be split ({error}), and its text holds "
                   f"`{found}`, which subagents may not run. Write the command so that its "
                   f"quotes balance. {RULE_6}", found)


def check_command(ctx, text: str, powershell: bool) -> Refusal | None:
    """Checks a Bash or PowerShell command line for every caller.

    Every refused git and gh command in the line is named in the reason. The
    first one gives the log's rule and subcommand.
    """
    parsed = parse(text, ctx.cwd, powershell)
    if parsed.error:
        return _check_unparsed(ctx, text, parsed.error)
    refusals = []
    for cmd in parsed.commands:
        name = program(cmd.words[0].value)
        refusal = None
        if name == "git":
            refusal = check_git(ctx, cmd)
        elif name == "gh":
            refusal = check_gh(ctx, cmd, parsed)
        if refusal and refusal.reason not in [r.reason for r in refusals]:
            refusals.append(refusal)
    if not refusals:
        return None
    first = refusals[0]
    return Refusal(first.rule, "\n".join(r.reason for r in refusals), first.subcommand)


def check_skill(ctx, tool_input: dict) -> Refusal | None:
    """Checks a subagent's Skill call (design 7.4)."""
    if ctx.caller.kind == MAIN:
        return None
    raw = str(tool_input.get("skill") or tool_input.get("name") or
              tool_input.get("command") or "").strip()
    parts = raw.split(maxsplit=1)
    name = parts[0].lstrip("/") if parts else ""
    short = name.rsplit(":", 1)[-1]
    args = tool_input.get("args", tool_input.get("arguments", ""))
    text = " ".join([parts[1] if len(parts) > 1 else "",
                     args if isinstance(args, str) else json.dumps(args)])
    label = f"skill {short or '?'}"
    if short not in _REVIEW_SKILLS:
        return Refusal("skill", f"Subagents may run only the code-review and security-review "
                       f"skills, not `{name or raw}`.", label)
    if _FIX_OR_COMMENT.search(text):
        return Refusal("skill", f"`{name}` with --fix or --comment changes code or GitHub. "
                       "Run it without them and report findings (F04 D36).", label)
    return None
