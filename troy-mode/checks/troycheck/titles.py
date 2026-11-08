"""PR title parsing (design section 4, from F01 design D1)."""

import re
from dataclasses import asdict, dataclass

STAGES = {"1": "design", "2": "test-plan", "3": "mock", "4": "tests", "5": "impl", "6": "accept"}

_SUMMARY = r"(?P<summary>\S(?:.*\S)?)"
_FEATURE = r"F\d{2,3}"
_BUG = r"B[1-9]\d*"
# A project rule's ID, in its test cleanup PR "[P01 test-fix] ..." (F09 design 5.4).
_RULE = r"P\d{2,3}"
_NUMBER = r"(?:0|[1-9]\d*)"
_VERSION = rf"v{_NUMBER}\.{_NUMBER}"

_PATTERNS = [
    re.compile(rf"\[(?P<id>{_FEATURE}) (?P<n>[1-6])/6 (?P<name>[a-z-]+)\] {_SUMMARY}"),
    re.compile(rf"\[(?P<id>{_BUG}) (?P<stage>A/B) (?P<kind>test)\] {_SUMMARY}"),
    re.compile(rf"\[(?P<id>{_BUG}) (?P<stage>B/B) (?P<kind>fix)\] {_SUMMARY}"),
    re.compile(rf"\[(?P<id>{_FEATURE}|{_BUG}|{_RULE}) (?P<kind>test-fix)\] {_SUMMARY}"),
    re.compile(rf"\[(?P<kind>docs|rules|refactor)\] {_SUMMARY}"),
    re.compile(rf"\[(?P<id>{_VERSION}) (?P<version_tests>tests)\] {_SUMMARY}"),
]
# The kind of a version's tests PR, "[v0.1 tests] ...", written by the Test
# Engineer at a release (F08 design 5.3).
VERSION_TESTS = "version-tests"


@dataclass(frozen=True)
class Title:
    """A parsed PR title.

    Attributes:
        kind: PR kind, for example "mock", "test", "fix", "test-fix", "docs", or
            "version-tests".
        id: Feature or bug ID, the version ("v0.1") of a version-tests PR, the
            P ID of a rule's test-fix PR, or None for docs, rules, and refactor
            PRs.
        stage: "3/6" for a feature stage, "A/B" or "B/B" for a bug PR, else None.
        summary: The text after the bracket.
    """

    kind: str
    id: str | None
    stage: str | None
    summary: str

    def to_dict(self) -> dict:
        """Returns the title as the dict used in the JSON report."""
        return asdict(self)


def _from_match(match: re.Match) -> Title | None:
    """Builds a Title from a pattern match, checking stage number and name."""
    groups = match.groupdict()
    if "n" in groups:
        if STAGES[groups["n"]] != groups["name"]:
            return None
        return Title(groups["name"], groups["id"], f"{groups['n']}/6", groups["summary"])
    if "version_tests" in groups:
        return Title(VERSION_TESTS, groups["id"], None, groups["summary"])
    return Title(groups["kind"], groups.get("id"), groups.get("stage"), groups["summary"])


def parse_title(text: str) -> Title | None:
    """Parses a PR title.

    Spaces must be single, IDs and stage names are case-sensitive, and the
    summary must hold at least one character that is not a space.

    Args:
        text: The PR title.

    Returns:
        The parsed title, or None if it matches no PR kind.
    """
    if "  " in text:
        return None
    for pattern in _PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            return _from_match(match)
    return None


def describe(title: Title | None, allowed: list[str]) -> str:
    """Builds the "Kind:" line of the text report.

    Args:
        title: The parsed title, or None.
        allowed: Path classes this kind may change.

    Returns:
        For example "Kind: impl, feature F04, stage 5/6. May change: source,
        dependencies."
    """
    if title is None:
        return "Kind: unknown. The title matches no PR kind."
    parts = [title.kind]
    if title.id:
        word = {"F": "feature ", "B": "bug ", "v": "version ", "P": "rule "}.get(
            title.id[0], "")
        parts.append(word + title.id)
    if title.stage:
        parts.append(f"stage {title.stage}")
    return f"Kind: {', '.join(parts)}. May change: {', '.join(allowed)}."
