"""Change-log rows and the changelog's release notes (F08 design 5.7, 8, D77).

`approve` and `accept-version` add a row to a document's change log, the
table under its "Change log" or "修改记录" heading, in both languages.
`release-notes` writes one tag's section of CHANGELOG.md.
"""

from .versions import heading_text, section_lines, tables

CHANGE_LOG_HEADINGS = ("change log", "修改记录")


def _ending(line: str) -> str:
    """Returns a line's ending: "\\r" when the file uses CRLF (lines split at "\\n"), else ""."""
    return "\r" if line.endswith("\r") else ""


def escape(text: str) -> str:
    """Makes text safe for one Markdown table cell: one line, with "|" escaped."""
    return " ".join(text.split()).replace("|", "\\|")


def table_row(cells: list[str], width: int) -> str:
    """Builds a table row of a given width: the first two cells first, the last cell last."""
    if width <= len(cells):
        values = cells[:width]
    else:
        values = cells[:-1] + [""] * (width - len(cells)) + cells[-1:]
    return "| " + " | ".join(values) + " |"


def append_row(text: str, names: tuple[str, ...], cells: list[str]) -> str | None:
    """Appends a row to the first table of the section under a heading.

    Args:
        text: The document.
        names: The heading texts that name the section, in lower case.
        cells: The row's cells.

    Returns:
        The document with the row added after the table's last row, or None
        when the section or its table is missing.
    """
    lines = text.split("\n")
    span = section_lines(lines, names)
    if span is None:
        return None
    found = tables([line.rstrip("\r") for line in lines[span[0] + 1:span[1]]])
    if not found:
        return None
    start, header, rows = found[0]
    last = span[0] + 1 + start + 1 + len(rows)
    row = table_row(cells, len(header)) + _ending(lines[last])
    lines.insert(last + 1, row)
    return "\n".join(lines)


def add_change_log_row(text: str, version: str, date: str, change: str) -> str | None:
    """Adds "| <version> | <date> | <change> |" to a document's change log, or returns None."""
    return append_row(text, CHANGE_LOG_HEADINGS, [version, date, change])


def release_section(text: str, tag: str) -> str | None:
    """Finds one tag's section of a changelog (F08 design 5.7).

    Args:
        text: CHANGELOG.md.
        tag: The tag, for example "v0.1.0".

    Returns:
        The section from its level-2 heading to the line before the next
        heading of level 1 or 2, trailing blank lines dropped, LF endings,
        and one final newline; or None when there is no such section.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    start, fence = None, None
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")) and len(line) - len(stripped) <= 3:
            mark = stripped[0]
            fence = None if fence == mark else (fence or mark)
            continue
        if fence is not None:
            continue
        found = heading_text(line)
        if found is None:
            continue
        level, raw = found[0], line.lstrip("#").strip()
        if start is None and level == 2 and _names_tag(raw, tag):
            start = index
        elif start is not None and level <= 2:
            return _finish(lines[start:index])
    return _finish(lines[start:]) if start is not None else None


def _names_tag(heading: str, tag: str) -> bool:
    """Tells whether a heading's text starts with the tag, then the end, a space, or "("."""
    return heading.startswith(tag) and heading[len(tag):len(tag) + 1] in ("", " ", "(")


def _finish(lines: list[str]) -> str:
    """Drops trailing blank lines and ends the text with one newline."""
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"
