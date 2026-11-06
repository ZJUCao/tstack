"""R03: the size of a source PR, with the soft-limit reason from its description."""

import re

from .classify import SOURCE_KINDS
from .context import PrContext
from .gitio import line_counts
from .globs import matches_any
from .report import FAIL, PASS, SKIP, WARN, Detail, Result

_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_NO_REASON = {"", "none", "none.", "无"}


def soft_limit_reason(body: str | None) -> str | None:
    """Finds the reason in the description's "Soft-limit reason" section.

    Args:
        body: The PR description, or None.

    Returns:
        The section's text with HTML comments removed, or None when the
        section is missing or says nothing, None, None., or 无.
    """
    if not body:
        return None
    lines = _COMMENT.sub("", body.replace("\r\n", "\n")).split("\n")
    collected, inside = [], False
    for line in lines:
        heading = _HEADING.match(line)
        if heading:
            inside = heading.group(1).strip().lower() == "soft-limit reason"
            continue
        if inside:
            collected.append(line)
    text = "\n".join(collected).strip()
    return None if text.lower() in _NO_REASON else text


def _counted(ctx: PrContext) -> tuple[int, int]:
    """Counts changed lines and files, leaving out lock and generated files."""
    skip = ctx.config.paths["lock"] + ctx.config.paths["generated"]
    lines = files = 0
    for count in line_counts(ctx.repo, ctx.base, ctx.head):
        if matches_any(count.path, skip):
            continue
        files += 1
        lines += (count.added or 0) + (count.deleted or 0)
    return lines, files


def _over_limits(lines: int, files: int, ctx: PrContext) -> list[str]:
    """Lists which R03 limits a PR passes."""
    over = []
    if lines > ctx.config.source_lines:
        over.append(f"over {ctx.config.source_lines} lines")
    if files > ctx.config.source_files:
        over.append(f"over {ctx.config.source_files} files")
    return over


def check_r03(ctx: PrContext) -> Result:
    """Checks a source PR's size (R03). A soft limit: a reason turns FAIL into WARN.

    Args:
        ctx: The PR under check.

    Returns:
        SKIP for PRs that are not mock, impl, fix, or refactor. PASS within
        the limits. Over a limit, WARN with a reason and FAIL without one.
    """
    if ctx.title is None or ctx.title.kind not in SOURCE_KINDS:
        return Result("R03", SKIP, "Not a source PR.")
    lines, files = _counted(ctx)
    size = f"{lines} changed lines in {files} files"
    over = _over_limits(lines, files, ctx)
    if not over:
        return Result("R03", PASS, f"{size}.")
    reason = soft_limit_reason(ctx.body)
    if reason:
        first = reason.splitlines()[0]
        return Result("R03", WARN, f"{size}, {' and '.join(over)}. Reason given: \"{first}\"",
                      [Detail(None, None, f"Soft-limit reason: {first}")])
    return Result("R03", FAIL, f"{size}, {' and '.join(over)}. No soft-limit reason given.",
                  [Detail(None, None, "Split the PR or give a reason under "
                                      "\"## Soft-limit reason\" in the description.")])
