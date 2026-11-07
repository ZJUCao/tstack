"""The feature loop's six stages and the tasks that belong to each (F07 design 8.1)."""

import re

from troycheck.titles import STAGES, parse_title

# The task that writes each stage, and the reviewers that review it.
AUTHOR_TASK = {1: "IF1", 2: "TM1", 3: "DV1", 4: "TE1", 5: "DV2", 6: "PM3"}
REVIEWERS = {1: ("AR2",), 2: (), 3: ("CR1",), 4: ("TM2", "CR1"), 5: ("CR1",), 6: ()}
# The part 1 tasks each stage allows in a brief (design 6.1 and 8.1). AR5
# answers questions in any stage before acceptance.
STAGE_TASKS = {
    1: ("IF1", "IF2", "AR2", "AR5"),
    2: ("TM1", "IF3", "AR5"),
    3: ("DV1", "CR1", "AR5"),
    4: ("TE1", "TM2", "CR1", "AR5"),
    5: ("DV2", "CR1", "AR5"),
    6: (),
}
# Approvals by Troy (D61, D62) apply to these stages of the first features.
TROY_STAGES = (1, 2)

_SQUASH = re.compile(r" \(#\d+\)$")


def stage_name(stage: int) -> str:
    """Returns a stage's name, for example "mock" for 3."""
    return STAGES[str(stage)]


def title(item: str, stage: int, name: str) -> str:
    """Builds a stage's PR title, for example "[F04 3/6 mock] Export history as CSV"."""
    return f"[{item} {stage}/6 {stage_name(stage)}] {name}"


def branch(item: str, stage: int) -> str:
    """Builds a stage's branch, for example "troy-mode/f04-3-mock"."""
    return f"troy-mode/{item.lower()}-{stage}-{stage_name(stage)}"


def parse_subject(subject: str):
    """Parses a commit subject or PR title as a troy-mode title.

    One trailing " (#<number>)", which a squash merge adds, is removed first.

    Returns:
        The parsed troycheck Title, or None.
    """
    return parse_title(_SQUASH.sub("", subject.strip()))


def feature_stage(subject: str) -> tuple[str, int] | None:
    """Reads the feature and stage number from a subject or title.

    Returns:
        The feature ID and the stage number 1 to 6, or None for any other title.
    """
    parsed = parse_subject(subject)
    if parsed is None or parsed.stage is None or not parsed.stage.endswith("/6"):
        return None
    return parsed.id, int(parsed.stage[0])


def merged_stages(subjects: list[str]) -> dict[str, set[int]]:
    """Collects the stages each feature has merged, from commit subjects.

    Args:
        subjects: Subject lines of origin/main's history.

    Returns:
        Stage numbers by feature ID.
    """
    merged: dict[str, set[int]] = {}
    for subject in subjects:
        found = feature_stage(subject)
        if found:
            merged.setdefault(found[0], set()).add(found[1])
    return merged


def current_stage(merged: set[int]) -> int | None:
    """Returns the lowest stage not merged, or None when all six are."""
    return next((n for n in range(1, 7) if n not in merged), None)
