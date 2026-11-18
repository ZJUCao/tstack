"""The ADRs an architecture approval accepts (F07 D202).

When Troy approves the architecture, `approve` also accepts the ADRs that its
"Decision records" table lists and that are still proposed: each ADR's Status
line, its header (the next major version, the date, and Troy's approval), and
the Status cell of its row in the architecture's table, in both languages.
"""

import re
from pathlib import Path

from .versions import section_lines, tables

ARCHITECTURE = "architecture"
RECORD_HEADINGS = ("decision records", "决策记录")
STATUS_HEADINGS = ("status", "状态")
ADR_ID = re.compile(r"ADR-\d{4}")
PROPOSED = {"en": ("proposed",), "zh-CN": ("提议中", "已提议", "提议", "proposed")}
ACCEPTED_WORD = {"en": "Accepted", "zh-CN": "已接受"}
ACCEPTED_LINE = {"en": "Accepted. Troy accepted it on {date} by approving `docs/architecture.md`.",
                 "zh-CN": "已接受。Troy 于 {date} 批准 `docs/architecture.md`，接受了这条记录。"}
_PUNCT = " \t.。,，;；:："
_COMMENT = re.compile(r"^\s*<!--.*-->\s*$")


def _lines(text: str) -> list[str]:
    """Splits a text at LF; each line keeps a trailing CR."""
    return text.split("\n")


def proposed_rest(text: str, lang: str) -> str | None:
    """Reads a status text that starts with a proposed word.

    Returns:
        The text after the word and its punctuation, or None when the text
        does not start with a proposed word.
    """
    stripped = text.strip()
    for word in PROPOSED.get(lang, PROPOSED["en"]):
        if stripped.lower().startswith(word):
            return stripped[len(word):].lstrip(_PUNCT)
    return None


def listed_ids(text: str) -> list[str]:
    """The ADR IDs in the first cell of each row of the decision records table."""
    lines = [line.rstrip("\r") for line in _lines(text)]
    span = section_lines(lines, RECORD_HEADINGS)
    if span is None:
        return []
    found = tables(lines[span[0] + 1:span[1]])
    if not found:
        return []
    ids = []
    for row in found[0][2]:
        match = ADR_ID.search(row[0]) if row else None
        if match and match.group(0) not in ids:
            ids.append(match.group(0))
    return ids


def status_line(lines: list[str]) -> int | None:
    """Finds the index of the first text line of the Status section, or None."""
    span = section_lines(lines, STATUS_HEADINGS)
    if span is None:
        return None
    for index in range(span[0] + 1, span[1]):
        line = lines[index].rstrip("\r")
        if line.strip() and not _COMMENT.match(line):
            return index
    return None


def is_proposed(text: str, lang: str) -> bool:
    """Tells whether an ADR's Status section starts with a proposed word."""
    lines = _lines(text)
    index = status_line(lines)
    return index is not None and proposed_rest(lines[index], lang) is not None


def accept_status(text: str, lang: str, date: str) -> str:
    """Rewrites the Status line of a proposed ADR; other texts stay as they are."""
    lines = _lines(text)
    index = status_line(lines)
    if index is None:
        return text
    rest = proposed_rest(lines[index], lang)
    if rest is None:
        return text
    ending = "\r" if lines[index].endswith("\r") else ""
    line = ACCEPTED_LINE[lang].format(date=date)
    lines[index] = (f"{line} {rest}" if rest else line) + ending
    return "\n".join(lines)


def accept_rows(text: str, lang: str, ids: set[str]) -> str:
    """Sets the Status cell of each listed ADR's row to Accepted when it says Proposed."""
    lines = _lines(text)
    plain = [line.rstrip("\r") for line in lines]
    span = section_lines(plain, RECORD_HEADINGS)
    if span is None:
        return text
    found = tables(plain[span[0] + 1:span[1]])
    if not found:
        return text
    start, header, rows = found[0]
    column = next((i for i, name in enumerate(header) if name in STATUS_HEADINGS),
                  len(header) - 1)
    for offset, row in enumerate(rows):
        match = ADR_ID.search(row[0]) if row else None
        if not match or match.group(0) not in ids:
            continue
        index = span[0] + 1 + start + 2 + offset
        cells = _split(lines[index].rstrip("\r"))
        if cells is None or column >= len(cells):
            continue
        rest = proposed_rest(cells[column], lang)
        if rest is None:
            continue
        cells[column] = f" {ACCEPTED_WORD[lang]}{(' ' + rest) if rest else ''} "
        ending = "\r" if lines[index].endswith("\r") else ""
        lines[index] = "|" + "|".join(cells) + "|" + ending
    return "\n".join(lines)


def _split(line: str) -> list[str] | None:
    """Splits a table row at the pipes that are not escaped, keeping each cell's spaces."""
    body = line.strip()
    if not body.startswith("|"):
        return None
    body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return re.split(r"(?<!\\)\|", body)


def adr_files(root: Path, adr_id: str) -> list[str]:
    """The English files under docs/adr/ whose name starts with the ID."""
    folder = root / "docs" / "adr"
    if not folder.is_dir():
        return []
    return sorted(f"docs/adr/{p.name}" for p in folder.glob(f"{adr_id}-*.md")
                  if not p.name.endswith(".zh-CN.md"))
