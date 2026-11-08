"""Requirement changes in the state: rework, the redo, and the skipped mock (F07 design 11.2).

A requirement change merges as a "[docs] Change the requirements: ..." commit.
A feature not yet accepted that the Product Manager marked "Needs rework" is in
rework until one of its stages merges again after that commit (D58: the state
stays in git).
"""

from .requirements import Feature
from .stages import feature_stage, plain

CHANGE_PREFIX = "[docs] Change the requirements: "
NEEDS_REWORK = "needs rework"


def is_change(subject: str) -> bool:
    """Tells whether a subject or title is a requirement change PR's (design 11.2, step 1)."""
    return plain(subject).startswith(CHANGE_PREFIX)


def change_index(subjects: list[str]) -> int | None:
    """Returns the index of the newest change commit in subjects (newest first), or None."""
    return next((i for i, s in enumerate(subjects) if is_change(s)), None)


def in_rework(feature: Feature | None, subjects: list[str], merged: set[int]) -> bool:
    """Tells whether a feature is in rework after a requirement change.

    Args:
        feature: The feature's row on origin/main, or None.
        subjects: origin/main's subjects, newest first.
        merged: The feature's merged stages.

    Returns:
        True when the feature is not accepted, its Status starts with "Needs
        rework", origin/main has a change commit, and no stage of the feature
        merged after the newest one.
    """
    if feature is None or 6 in merged or not feature.status.lower().startswith(NEEDS_REWORK):
        return False
    index = change_index(subjects)
    if index is None:
        return False
    return not any((feature_stage(s) or ("", 0))[0] == feature.id for s in subjects[:index])
