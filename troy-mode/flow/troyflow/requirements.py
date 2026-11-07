"""The project's requirements as the engine reads them (F07 design 5.1).

Only the features table, the topological order line, and document versions
matter here. The rest of the document is the Product Manager's.
"""

import re
from dataclasses import dataclass, field

from troycheck.frontmatter import parse_header, version_key

FEATURE_ID = re.compile(r"F\d{2,3}")
ORDER_MARK = "Topological order:"
_NEEDED = ("id", "feature", "hard dependencies", "soft dependencies")


@dataclass
class Feature:
    """One row of the features table.

    Attributes:
        id: The feature ID, for example "F04".
        name: The Feature cell, with runs of white space made single.
        hard: Hard dependencies, in the cell's order.
        soft: Soft dependencies, in the cell's order.
        version: The Version cell, or "" when the table has none.
        status: The Status cell, or "" when the table has none.
    """

    id: str
    name: str
    hard: list[str] = field(default_factory=list)
    soft: list[str] = field(default_factory=list)
    version: str = ""
    status: str = ""


def doc_version(text: str | None) -> str | None:
    """Returns a document's front matter version, or None when it has none."""
    if text is None:
        return None
    header = parse_header(text)
    return header.fields.get("version") if header else None


def approved(version: str | None) -> bool:
    """Tells whether a version means Troy approved the document: major 1 or more."""
    key = version_key(version) if version else None
    return key is not None and key[0] >= 1


def _cells(line: str) -> list[str]:
    """Splits one Markdown table row into trimmed cells without backticks."""
    inner = line.strip().strip("|")
    return [cell.strip().replace("`", "").strip() for cell in inner.split("|")]


def _is_table_row(line: str) -> bool:
    """Tells whether a line is a Markdown table row."""
    return line.strip().startswith("|")


def _cell(cells: list[str], columns: dict[str, int], name: str) -> str:
    """Returns a row's cell in a named column, or "" when the row or table lacks it."""
    index = columns.get(name)
    return cells[index] if index is not None and index < len(cells) else ""


def _feature_rows(lines: list[str], start: int, columns: dict[str, int]) -> list[Feature]:
    """Reads the rows of the features table that starts at a header line."""
    features = []
    for line in lines[start + 2:]:
        if not _is_table_row(line):
            break
        cells = _cells(line)
        fid = _cell(cells, columns, "id")
        if not FEATURE_ID.fullmatch(fid):
            continue
        features.append(Feature(fid, " ".join(_cell(cells, columns, "feature").split()),
                                FEATURE_ID.findall(_cell(cells, columns, "hard dependencies")),
                                FEATURE_ID.findall(_cell(cells, columns, "soft dependencies")),
                                _cell(cells, columns, "version"),
                                _cell(cells, columns, "status")))
    return features


def parse_features(text: str | None) -> list[Feature] | None:
    """Reads the features table: the first table with ID, Feature, and both dependency columns.

    Args:
        text: The requirements document, or None.

    Returns:
        The features in table order, or None when there is no such table.
    """
    if text is None:
        return None
    lines = text.replace("\r\n", "\n").split("\n")
    for index, line in enumerate(lines):
        if not _is_table_row(line):
            continue
        names = [cell.lower() for cell in _cells(line)]
        if all(name in names for name in _NEEDED):
            columns = {name: names.index(name) for name in names}
            return _feature_rows(lines, index, columns)
    return None


def parse_order(text: str | None) -> list[str] | None:
    """Reads the IDs after "Topological order:" on the first line that holds it, or None."""
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        if ORDER_MARK in line:
            return FEATURE_ID.findall(line.split(ORDER_MARK, 1)[1])
    return None


def order_problems(features: list[Feature] | None, order: list[str] | None) -> list[str]:
    """Checks the order line against the features table (design 5.1).

    Every dependency must come earlier in the order, and the order must name
    every feature of the table exactly once.

    Returns:
        One sentence per problem, each naming the features.
    """
    if features is None:
        return ["The requirements have no features table."]
    if order is None:
        return ["The requirements have no \"Topological order:\" line."]
    problems = []
    known = {f.id for f in features}
    for fid in sorted({i for i in order if order.count(i) > 1}):
        problems.append(f"{fid} is listed more than once in the topological order.")
    problems += [f"{i} is in the topological order but not in the features table."
                 for i in order if i not in known]
    problems += [f"{f.id} is in the features table but not in the topological order."
                 for f in features if f.id not in order]
    for feature in features:
        if feature.id not in order:
            continue
        position = order.index(feature.id)
        for dep in feature.hard + feature.soft:
            if dep not in order[:position]:
                problems.append(f"{feature.id} depends on {dep}, which does not come before "
                                f"it in the topological order.")
    return problems
