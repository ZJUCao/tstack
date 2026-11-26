"""The feature loop's six stages and the tasks that belong to each (F07 design 8.1)."""

import re

from troycheck.titles import STAGES, parse_title

# The task that writes each stage, and the reviewers that review it.
AUTHOR_TASK = {1: "IF1", 2: "TM1", 3: "DV1", 4: "TE1", 5: "DV2", 6: "PM3"}
REVIEWERS = {1: ("AR2",), 2: (), 3: ("CR1",), 4: ("TM2", "CR1"), 5: ("CR1",), 6: ()}
# The author of a bug PR, by title kind (design 11.1).
KIND_TASK = {"test": "TE2", "fix": "DV3"}
# The tasks each stage allows in a brief (design 6.1, 8.1, and 8.7). AR5
# answers questions and AR3 reviews a new dependency in any stage before
# acceptance; AR4 lists a requirement change's impact. The side flows of
# stage 5 rule on disputed tests and coverage gaps. In stage 6, TM8 rules on
# the mismatches of the real run (F12 design 7.1). The Architect rules at round
# 3 of every review loop but its own, so AR8 belongs to stages 2 to 5 (F18 5.1).
STAGE_TASKS = {
    1: ("IF1", "IF2", "AR2", "AR5", "AR3", "AR4"),
    2: ("TM1", "IF3", "AR5", "AR3", "AR4", "AR8"),
    3: ("DV1", "CR1", "AR5", "AR3", "AR4", "AR8"),
    4: ("TE1", "TM2", "CR1", "AR5", "AR3", "AR4", "AR8"),
    5: ("DV2", "CR1", "AR5", "AR3", "AR4", "TM3", "TM4", "TM6", "IF4", "DV4", "AR8"),
    6: ("TM8",),
}
STAGE_KINDS = tuple(STAGES.values())
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
    return parse_title(plain(subject))


def feature_stage(subject: str) -> tuple[str, int] | None:
    """Reads the feature and stage number from a subject or title.

    Returns:
        The feature ID and the stage number 1 to 6, or None for any other title.
    """
    parsed = parse_subject(subject)
    if parsed is None or parsed.stage is None or not parsed.stage.endswith("/6"):
        return None
    return parsed.id, int(parsed.stage[0])


def plain(subject: str) -> str:
    """Removes one trailing " (#<number>)", which a squash merge adds, and outer spaces."""
    return _SQUASH.sub("", subject.strip())


def merged_stages(subjects: list[str]) -> dict[str, set[int]]:
    """Collects the stages each feature has merged, from commit subjects.

    The subjects count in history order. A stage that merges again, as the
    redo after a requirement change does, drops the feature's later stages
    that merged before it (design 5.1 and 11.2).

    Args:
        subjects: Subject lines of origin/main's history, newest first.

    Returns:
        Stage numbers by feature ID.
    """
    merged: dict[str, set[int]] = {}
    for subject in reversed(subjects):
        found = feature_stage(subject)
        if found:
            fid, number = found
            merged[fid] = {n for n in merged.get(fid, set()) if n < number} | {number}
    return merged


def current_stage(merged: set[int], skip_mock: bool = False) -> int | None:
    """Returns the lowest stage not merged, or None when all six are.

    Args:
        merged: The feature's merged stage numbers.
        skip_mock: The feature's design adds no interface, so stage 3 is
            skipped once stage 2 has merged (design 11.2, D65).
    """
    done = set(merged) | ({3} if skip_mock and 2 in merged else set())
    return next((n for n in range(1, 7) if n not in done), None)
