"""The project's rules table as text: P rows, IDs, and Troy's choice (F09 design 3 and 6).

The rules table is the first Markdown table with a row whose ID is an R or a
P ID. P rows are the project's own rules. A retired row stays, and its ID is
never used again (D84). The change log's newest row that names a rule says
what Troy chose for the existing code (D81).
"""

import re
from dataclasses import dataclass

from .changelog import CHANGE_LOG_HEADINGS
from .versions import section_lines, tables

P_ID = re.compile(r"P\d{2,3}")
R_ID = re.compile(r"R\d{2,3}")
_ROW_ID = re.compile(r"[RP]\d+")
_SPLIT = re.compile(r"(?<!\\)\|")
WIDTH = 6
RETIRED = {"en": "Retired on ", "zh-CN": "已于 "}
CLEANUP = "Existing code: fixed by cleanup PRs."
WHEN_TOUCHED = "Existing code: fixed when touched."


@dataclass
class RulesTable:
    """Where the rules table sits in a document's lines.

    Attributes:
        start: The index of the header line.
        width: The number of header cells.
        rows: The body rows' cells, split at unescaped pipes and stripped.
    """

    start: int
    width: int
    rows: list[list[str]]

    def line_of(self, index: int) -> int:
        """Returns the line index of a body row."""
        return self.start + 2 + index

    def end(self) -> int:
        """Returns the line index after the table's last row."""
        return self.start + 2 + len(self.rows)

    def find(self, rule_id: str) -> int | None:
        """Returns the index of the body row with an ID, or None."""
        return next((i for i, cells in enumerate(self.rows) if cells[0] == rule_id), None)

    def p_indexes(self) -> list[int]:
        """Returns the indexes of the P rows."""
        return [i for i, cells in enumerate(self.rows) if P_ID.fullmatch(cells[0])]


def split_cells(line: str) -> list[str]:
    """Splits a table row at unescaped pipes into stripped cells, backticks kept."""
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [cell.strip() for cell in _SPLIT.split(inner)]


def rules_table(lines: list[str]) -> RulesTable | None:
    """Finds the rules table: the first table with a row whose first cell is an R or P ID."""
    for start, header, rows in tables(lines):
        if any(cells and _ROW_ID.fullmatch(cells[0]) for cells in rows):
            body = [split_cells(lines[start + 2 + i]) for i in range(len(rows))]
            return RulesTable(start, len(header), body)
    return None


def change_log_rows(lines: list[str]) -> list[list[str]] | None:
    """Returns the change log's rows (cells without backticks), or None without one."""
    span = section_lines(lines, CHANGE_LOG_HEADINGS)
    if span is None:
        return None
    found = tables(lines[span[0] + 1:span[1]])
    return found[0][2] if found else None


def names_id(text: str, rule_id: str) -> bool:
    """Tells whether a text names a rule ID as a word, not inside a longer ID."""
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(rule_id)}(?![A-Za-z0-9])", text) is not None


def choice(rows: list[list[str]] | None, rule_id: str) -> str | None:
    """Reads Troy's choice for existing code from the newest change-log row naming a rule.

    Returns:
        "cleanup", "when-touched", or None.
    """
    for cells in reversed(rows or []):
        change = cells[-1] if cells else ""
        if not names_id(change, rule_id):
            continue
        if CLEANUP in change:
            return "cleanup"
        return "when-touched" if WHEN_TOUCHED in change else None
    return None


def number(rule_id: str) -> int:
    """Returns the number of an R or P ID, for example 4 for "P04"."""
    return int(rule_id[1:])


def next_id(prefix: str, ids: list[str]) -> str:
    """Returns the next free ID after the highest one, with at least two digits."""
    highest = max((number(i) for i in ids), default=0)
    return f"{prefix}{highest + 1:02d}"


def is_retired(rule: str, lang: str = "en") -> bool:
    """Tells whether a Rule cell marks its row retired."""
    return rule.startswith(RETIRED[lang])


@dataclass
class TableState:
    """What the engine reads from one English rules table.

    Attributes:
        rows: The P rows as dicts: id, rule, type, enforced_by, scope, since, retired.
        r_ids: The R IDs of the table.
        log: The change log's rows, or None.
    """

    rows: list[dict]
    r_ids: list[str]
    log: list[list[str]] | None

    def ids(self) -> list[str]:
        """Returns the P IDs, retired ones included."""
        return [row["id"] for row in self.rows]

    def row(self, rule_id: str) -> dict | None:
        """Returns the P row with an ID, or None."""
        return next((row for row in self.rows if row["id"] == rule_id), None)


def read_table(text: str | None) -> TableState | None:
    """Reads the P rows, the R IDs, and the change log of an English rules table.

    Returns:
        The state, or None when the text is missing or has no rules table.
    """
    if text is None:
        return None
    lines = text.split("\n")
    table = rules_table(lines)
    if table is None:
        return None
    rows, r_ids = [], []
    for cells in table.rows:
        if R_ID.fullmatch(cells[0]):
            r_ids.append(cells[0])
        if not P_ID.fullmatch(cells[0]):
            continue
        cells = (cells + [""] * WIDTH)[:WIDTH]
        rows.append({"id": cells[0], "rule": cells[1], "type": cells[2],
                     "enforced_by": cells[3], "scope": cells[4], "since": cells[5],
                     "retired": is_retired(cells[1])})
    return TableState(rows, r_ids, change_log_rows(lines))
