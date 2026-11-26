"""The waits for Troy: the only steps where troy-mode stops (F18 design 4.1 and 4.2, D171).

The Product Manager's instructions list them as W1 to W11. Every wait that
troy-mode records names its ID: `status --waiting` needs `--wait`, and a
`Waiting for Troy:` or `Escalation:` comment has the line `Wait: W<n>` right
under its heading. A wait without a listed ID is `unlisted`, which the
retrospective reports.
"""

import re

WAITS = {
    "W1": ("approval", "The requirements, or a change of them"),
    "W2": ("approval", "The architecture"),
    "W3": ("approval", "PR 1 and PR 2 of the first features, and the question after them"),
    "W4": ("approval", "The version: Troy's device test and acceptance"),
    "W5": ("approval", "Rules"),
    "W6": ("escalation", "A change of the requirements or the architecture"),
    "W7": ("escalation", "An author's work still fails"),
    "W8": ("escalation", "A new third-party dependency"),
    "W9": ("escalation", "An action outside troy-mode's rights"),
    "W10": ("escalation", "A refusal troy-mode must not work around"),
    "W11": ("escalation", "A fault in troy-mode's own checks"),
}
UNLISTED = "unlisted"
_HEADING = re.compile(r"^(?:Waiting for Troy|Escalation): .+$")
_LINE = re.compile(r"^Wait: (\S+)$")
_CARRIED = re.compile(r"^(W[0-9]+), ")


def is_listed(text: str | None) -> bool:
    """Tells whether a text is exactly one of the eleven wait IDs."""
    return text in WAITS


def wait_of(body: str | None) -> str | None:
    """The wait ID of a `Waiting for Troy:` or `Escalation:` comment.

    Returns:
        The ID its `Wait:` line names, "unlisted" when that line is missing or
        names no listed ID, or None for any other comment.
    """
    lines = (body or "").replace("\r\n", "\n").strip().split("\n")
    if not _HEADING.match(lines[0].strip()):
        return None
    rest = next((line.strip() for line in lines[1:] if line.strip()), "")
    found = _LINE.match(rest)
    return found.group(1) if found and is_listed(found.group(1)) else UNLISTED


def carried(text: str | None) -> str | None:
    """The wait ID at the start of a progress file's "Waiting on Troy" text, else "unlisted"."""
    if not text:
        return None
    found = _CARRIED.match(text)
    return found.group(1) if found and is_listed(found.group(1)) else UNLISTED
