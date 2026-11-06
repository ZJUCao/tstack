"""R20: template markers and guidance left in documents (design section 6.7)."""

import re

from .context import PrContext
from .gitio import read_blob
from .globs import matches_any
from .report import FAIL, PASS, Detail, Result

MARKER = re.compile(r"(?<!\$)\{\{(?! )[^{}\n]+(?<! )\}\}")
GUIDANCE = re.compile(r"<!--\s*template:")
NOT_SCANNED = [".github/**", ".troy-mode/**"]


def find_markers(text: str) -> list[tuple[int, str]]:
    """Finds template markers and guidance comments in a text.

    A marker is "{{" not preceded by "$", then text with no braces and no
    line break that neither starts nor ends with a space, then "}}". So
    "${{ github.sha }}", "{{ count }}", and "{{1, 2}, {3, 4}}" do not count.

    Args:
        text: A document or PR description.

    Returns:
        (line number, what was found) pairs, 1-based, in order.
    """
    found = []
    for number, line in enumerate(text.replace("\r\n", "\n").split("\n"), start=1):
        for match in MARKER.finditer(line):
            found.append((number, f"template marker {match.group(0)}"))
        if GUIDANCE.search(line):
            found.append((number, "template guidance comment"))
    return found


def _scanned_paths(ctx: PrContext) -> list[str]:
    """Lists the changed Markdown files R20 reads."""
    skip = NOT_SCANNED + ctx.config.paths["allow_markers"]
    return [c.path for c in ctx.changes
            if c.status != "D" and c.path.endswith(".md") and not matches_any(c.path, skip)]


def check_r20(ctx: PrContext) -> Result:
    """Checks changed documents and the PR description for template leftovers (R20).

    Args:
        ctx: The PR under check.

    Returns:
        FAIL with one detail per marker or guidance comment, PASS otherwise.
    """
    fails = []
    for path in _scanned_paths(ctx):
        text = read_blob(ctx.repo, ctx.head, path) or ""
        fails += [Detail(path, line, what) for line, what in find_markers(text)]
    if ctx.body is not None:
        fails += [Detail(None, line, f"PR description line {line}: {what}")
                  for line, what in find_markers(ctx.body)]
    if fails:
        return Result("R20", FAIL, f"{len(fails)} template leftovers. Fill them in or remove them.",
                      fails)
    return Result("R20", PASS, "No template markers.")
