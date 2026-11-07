"""Checks of Bash, PowerShell, and Skill calls (design sections 7 and 8.2)."""

import json
import re

from .ghcmd import gh_read_only, check_gh
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


def _write_in_text(text: str) -> str | None:
    """Finds a git or gh write in text that could not be split (design 7.1)."""
    for match in _GIT_IN_TEXT.finditer(text):
        sub, _ = _first_word(match.group(1), ("-C", "-c", "--git-dir", "--work-tree"))
        if sub and sub not in ALWAYS:
            return "git " + sub
    for match in _GH_IN_TEXT.finditer(text):
        group, rest = _first_word(match.group(1), ("-R", "--repo"))
        sub = next((token for token in rest if not token.startswith("-")), None)
        if group and not gh_read_only(group, sub, rest):
            return " ".join(part for part in ("gh", group, sub) if part)
    return None


def _check_unparsed(ctx, text: str, error: str) -> Refusal | None:
    """Checks a command that could not be split, by its text alone."""
    if ctx.caller.kind == MAIN:
        if re.search(r"\bgit\b", text) and re.search(r"core\.hookspath", text, re.I):
            return Refusal("hooks-path", "The command mentions core.hooksPath and could not "
                           f"be split ({error}). Nobody but Troy changes it (F05 8.2).", "git")
        if re.search(r"\bgit\b[^\n]*--no-verify", text):
            return Refusal("no-verify", "The command uses --no-verify and could not be split "
                           f"({error}). Run git without it (F05 8.2).", "git")
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
