"""Versions, tags, and the version test plan as the engine reads them (F08 design 3.2 and 4).

A feature's version is its Version cell in the requirements. A version's test
plan is docs/versions/<version>/test-plan.md, whose scenarios say who runs
them (D71). Tags are vMAJOR.MINOR.PATCH (D73).
"""

import re
from dataclasses import dataclass, field

from .requirements import FEATURE_ID, Feature

_NUMBER = r"(?:0|[1-9]\d*)"
VERSION = re.compile(rf"v{_NUMBER}\.{_NUMBER}")
TAG = re.compile(rf"(v{_NUMBER}\.{_NUMBER})\.({_NUMBER})")
_CELL_VERSION = re.compile(r"[vV]?(\d+)\.(\d+)")
SCENARIO_ID = re.compile(r"(?i)v\d+\.\d+-S\d+")
RELEASE_TITLE = re.compile(rf"\[docs\] Release (v{_NUMBER}\.{_NUMBER}\.{_NUMBER})")
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*$")
_SECTION_NUMBER = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_FEATURES_LINE = re.compile(r"^\s*-\s*Features:(.*)$")
ACCEPTANCE_HEADINGS = ("acceptance record", "验收记录")
RUN_BY = {"claude": "Claude", "troy": "Troy"}
PLAN_PATH = "docs/versions/{version}/test-plan.md"


def plan_path(version: str) -> str:
    """Returns the path of a version's test plan, for example docs/versions/v0.1/test-plan.md."""
    return PLAN_PATH.format(version=version)


def cell_version(text: str) -> str | None:
    """Reads a features table Version cell as "vMAJOR.MINOR", or None for any other text."""
    match = _CELL_VERSION.fullmatch(text.strip())
    if not match:
        return None
    return f"v{int(match.group(1))}.{int(match.group(2))}"


def version_key(version: str) -> tuple[int, int]:
    """Returns the (major, minor) numbers of a "vX.Y" version, for sorting."""
    major, minor = version[1:].split(".")
    return int(major), int(minor)


def parse_tag(tag: str) -> tuple[str, int] | None:
    """Splits a tag "v0.1.2" into its version "v0.1" and patch number 2, or returns None."""
    match = TAG.fullmatch(tag)
    return (match.group(1), int(match.group(2))) if match else None


def is_patch(tag: str) -> bool:
    """Tells whether a tag is a patch release: its PATCH number is above 0 (D75)."""
    parsed = parse_tag(tag)
    return parsed is not None and parsed[1] > 0


def release_tag(subject: str) -> str | None:
    """Returns the tag of a "[docs] Release vX.Y.Z" subject or title, or None."""
    match = RELEASE_TITLE.fullmatch(subject.strip())
    return match.group(1) if match else None


def versions_of(features: list[Feature] | None) -> dict[str, list[str]]:
    """Groups the features by version.

    Returns:
        Feature IDs by version, the versions sorted by number and the features
        in table order. Features without a version are left out.
    """
    found: dict[str, list[str]] = {}
    for feature in features or []:
        version = cell_version(feature.version)
        if version:
            found.setdefault(version, []).append(feature.id)
    return {v: found[v] for v in sorted(found, key=version_key)}


def norm_id(text: str) -> str:
    """Normalizes a scenario ID or test name: lower case, and "-", "_", "." all "_"."""
    return re.sub(r"[-_.]", "_", text.lower())


@dataclass
class Scenario:
    """One scenario of a version test plan (F08 design 4, D71).

    Attributes:
        id: The scenario ID, for example "v0.1-S01".
        run_by: "Claude", "Troy", or the cell as written when it is neither.
        cells: The row's cells by lower-case header name.
        performance: The row comes from a table with a Machine column.
    """

    id: str
    run_by: str
    cells: dict[str, str] = field(default_factory=dict)
    performance: bool = False

    def cell(self, name: str) -> str:
        """Returns a cell by header name, or "" when the table has no such column."""
        return self.cells.get(name.lower(), "")


@dataclass
class Plan:
    """A version test plan read from its English file.

    Attributes:
        features: The feature IDs of its "- Features:" line.
        scenarios: Every scenario row, in document order.
        troy_devices: Troy's devices from the devices table.
        accepted_tags: Tags in the acceptance record's "Accepted" rows.
    """

    features: list[str] = field(default_factory=list)
    scenarios: list[Scenario] = field(default_factory=list)
    troy_devices: list[str] = field(default_factory=list)
    accepted_tags: list[str] = field(default_factory=list)

    def by(self, who: str) -> list[Scenario]:
        """Returns the scenarios one person runs: "Claude" or "Troy"."""
        return [s for s in self.scenarios if s.run_by == who]


def _cells(line: str) -> list[str]:
    """Splits a Markdown table row into trimmed cells without backticks."""
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [c.strip().replace("`", "").strip() for c in re.split(r"(?<!\\)\|", inner)]


def tables(lines: list[str]) -> list[tuple[int, list[str], list[list[str]]]]:
    """Finds the Markdown tables outside fenced code.

    Returns:
        For each table: the index of its header line, its lower-case header
        cells, and its body rows' cells.
    """
    found, fence, index = [], None, 0
    while index < len(lines):
        line = lines[index]
        opened = _FENCE.match(line)
        if opened and (fence is None or opened.group(1)[0] == fence):
            fence = None if fence else opened.group(1)[0]
            index += 1
            continue
        nxt = lines[index + 1] if index + 1 < len(lines) else ""
        if fence is None and line.strip().startswith("|") and re.fullmatch(
                r"\s*\|?[\s:|-]*-[\s:|-]*\|?\s*", nxt):
            header = [c.lower() for c in _cells(line)]
            rows, end = [], index + 2
            while end < len(lines) and lines[end].strip().startswith("|"):
                rows.append(_cells(lines[end]))
                end += 1
            found.append((index, header, rows))
            index = end
            continue
        index += 1
    return found


def _cell(row: list[str], header: list[str], name: str) -> str:
    """Returns a row's cell under a header name, or ""."""
    if name not in header:
        return ""
    index = header.index(name)
    return row[index] if index < len(row) else ""


def heading_text(line: str) -> tuple[int, str] | None:
    """Reads a Markdown heading: its level and its text without a leading section number."""
    match = _HEADING.match(line.rstrip("\r"))
    if not match:
        return None
    return len(match.group(1)), _SECTION_NUMBER.sub("", match.group(2)).strip()


def section_lines(lines: list[str], names: tuple[str, ...]) -> tuple[int, int] | None:
    """Finds the section under the first heading whose text is one of names (any case).

    Returns:
        The index of the heading line and the index where the section ends
        (the next heading of the same or a higher level, or the end), or None.
    """
    fence, start, level = None, None, 0
    for index, line in enumerate(lines):
        opened = _FENCE.match(line)
        if opened and (fence is None or opened.group(1)[0] == fence):
            fence = None if fence else opened.group(1)[0]
            continue
        if fence is not None:
            continue
        found = heading_text(line)
        if found is None:
            continue
        if start is None and found[1].lower() in names:
            start, level = index, found[0]
        elif start is not None and found[0] <= level:
            return start, index
    return (start, len(lines)) if start is not None else None


def parse_plan(text: str | None) -> Plan | None:
    """Reads a version test plan's English file, or returns None without one."""
    if text is None:
        return None
    lines = text.replace("\r\n", "\n").split("\n")
    plan = Plan()
    for line in lines:
        match = _FEATURES_LINE.match(line)
        if match:
            plan.features = FEATURE_ID.findall(match.group(1))
            break
    for _, header, rows in tables(lines):
        if "run by" not in header:
            continue
        if "id" not in header:
            if "device" in header:
                plan.troy_devices += [_device(row, header) for row in rows
                                      if _cell(row, header, "run by").lower() == "troy"]
            continue
        for row in rows:
            sid = _cell(row, header, "id")
            if not SCENARIO_ID.fullmatch(sid):
                continue
            who = _cell(row, header, "run by")
            plan.scenarios.append(Scenario(
                sid, RUN_BY.get(who.lower(), who),
                {name: _cell(row, header, name) for name in header},
                "machine" in header))
    plan.accepted_tags = accepted_tags(lines)
    return plan


def _device(row: list[str], header: list[str]) -> str:
    """Names a device row: "<Device> (<Operating system>)", or the device alone."""
    device, system = _cell(row, header, "device"), _cell(row, header, "operating system")
    return f"{device} ({system})" if system else device


def accepted_tags(lines: list[str]) -> list[str]:
    """Lists the tags in the "Accepted" rows of the acceptance record."""
    span = section_lines(lines, ACCEPTANCE_HEADINGS)
    if span is None:
        return []
    found = []
    for _, header, rows in tables(lines[span[0] + 1:span[1]]):
        for row in rows:
            result = _cell(row, header, "result") or (row[1] if len(row) > 1 else "")
            if result.strip().lower().startswith("accepted"):
                found += [m.group(0) for m in re.finditer(r"v\d+\.\d+\.\d+", result)]
        break
    return found


def devices(plan: Plan, scenario: Scenario) -> list[str]:
    """The devices a scenario of Troy's runs on: its Machine cell, or Troy's devices."""
    if scenario.run_by != "Troy":
        return []
    if scenario.performance:
        machine = scenario.cell("machine")
        return [machine] if machine else []
    return list(plan.troy_devices)
