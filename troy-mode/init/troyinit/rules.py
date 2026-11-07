"""Bringing a project's rules table up to date (design section 6, D54).

Every R row is replaced by the template's row. An R row keeps its "Since"
date, and an R row new in the template gets the upgrade's date. P rows, the
project's own rules, stay after the R rows in their order.
"""

import re

from .errors import InitError

RULES_EN = "docs/rules.md"
RULES_ZH = "docs/rules.zh-CN.md"
_R_ROW = re.compile(r"^\| (R\d+) \|")
_LAST_CELL = re.compile(r"\|\s*([^|]*?)\s*\|\s*$")
_VERSION = re.compile(r'^version: "(\d+)\.(\d+)"$', re.MULTILINE)
_UPDATED = re.compile(r'^updated: "[^"]*"$', re.MULTILINE)
_CHANGE_TEXT = {
    "en": "troy-mode's rules brought up to troy-pstack {version}.",
    "zh-CN": "troy-mode 的规则更新到 troy-pstack {version}。",
}


def _since(row: str) -> str:
    """Returns the last cell of a table row, the "Since" date."""
    match = _LAST_CELL.search(row)
    return match.group(1) if match else ""


def _with_since(row: str, since: str) -> str:
    """Replaces the last cell of a table row."""
    return _LAST_CELL.sub(lambda _: f"| {since} |", row, count=1)


def _rule_block(lines: list[str]) -> tuple[int, int]:
    """Finds the table rows that hold the rules: from the first R row to the table's end.

    Raises:
        InitError: The text has no R row.
    """
    start = next((i for i, line in enumerate(lines) if _R_ROW.match(line)), None)
    if start is None:
        raise InitError("the rules table has no R rows")
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    return start, end


def merge_rows(project: str, template: str, date: str) -> str:
    """Replaces the project's R rows with the template's.

    Args:
        project: The project's rules document.
        template: troy-pstack's rules template in the same language.
        date: The date for R rows that are new.

    Returns:
        The document with the merged table. Everything outside the table's
        rule rows is unchanged.

    Raises:
        InitError: Either text has no R rows.
    """
    lines = project.replace("\r\n", "\n").split("\n")
    start, end = _rule_block(lines)
    block = lines[start:end]
    since = {m.group(1): _since(row) for row in block if (m := _R_ROW.match(row))}
    others = [row for row in block if not _R_ROW.match(row)]
    template_lines = template.replace("\r\n", "\n").split("\n")
    t_start, t_end = _rule_block(template_lines)
    rows = []
    for row in template_lines[t_start:t_end]:
        match = _R_ROW.match(row)
        if match:
            rows.append(_with_since(row, since.get(match.group(1), date)))
    return "\n".join(lines[:start] + rows + others + lines[end:])


def next_version(text: str) -> str:
    """Returns a document's version raised by one minor step.

    Raises:
        InitError: The document has no MAJOR.MINOR version.
    """
    match = _VERSION.search(text)
    if not match:
        raise InitError("the rules table has no version in its header")
    return f"{match.group(1)}.{int(match.group(2)) + 1}"


def _add_change_row(text: str, version: str, date: str, change: str) -> str:
    """Adds a row to the last table of the document, its change log."""
    lines = text.split("\n")
    last = max((i for i, line in enumerate(lines) if line.startswith("|")), default=None)
    if last is None:
        raise InitError("the rules table has no change log")
    lines.insert(last + 1, f"| {version} | {date} | {change} |")
    return "\n".join(lines)


def bump(text: str, version: str, date: str, lang: str, plugin_version: str) -> str:
    """Sets version and updated in the header and records the change.

    Args:
        text: A rules document.
        version: The new version, MAJOR.MINOR.
        date: The upgrade's date.
        lang: "en" or "zh-CN".
        plugin_version: troy-pstack's version, named in the change log.

    Returns:
        The document with its new header values and change-log row.
    """
    text = _VERSION.sub(f'version: "{version}"', text, count=1)
    text = _UPDATED.sub(f'updated: "{date}"', text, count=1)
    change = _CHANGE_TEXT[lang].format(version=plugin_version)
    return _add_change_row(text, version, date, change)


def upgrade_pair(en: str, zh: str, en_template: str, zh_template: str, date: str,
                 plugin_version: str) -> tuple[str, str] | None:
    """Upgrades the rules table and its mirror together.

    Args:
        en: docs/rules.md as it is.
        zh: docs/rules.zh-CN.md as it is.
        en_template: troy-pstack's rules.md template.
        zh_template: troy-pstack's rules.zh-CN.md template.
        date: The upgrade's date.
        plugin_version: troy-pstack's version.

    Returns:
        The new English and Chinese texts, both at the same raised version,
        or None when the R rows already match the templates.
    """
    en_rows = merge_rows(en, en_template, date)
    zh_rows = merge_rows(zh, zh_template, date)
    if en_rows == en.replace("\r\n", "\n") and zh_rows == zh.replace("\r\n", "\n"):
        return None
    version = next_version(en)
    return (bump(en_rows, version, date, "en", plugin_version),
            bump(zh_rows, version, date, "zh-CN", plugin_version))
