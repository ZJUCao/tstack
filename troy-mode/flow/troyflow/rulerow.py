"""The rule-id and rule-row commands (F09 design 3.1, 5.3, and 6).

rule-id reads origin/main. rule-row writes one P row into docs/rules.md and
its mirror in the working tree, raises both to the next major version with
Troy's approval (D82), and adds one change-log row.
"""

import json
import re
from pathlib import Path

from . import repo as git
from .approve import STATUS, check_date, header_of, next_major, rewrite
from .changelog import add_change_log_row
from .errors import FlowError
from .rulestate import RULES, RULES_ZH, read_rules
from .ruletable import P_ID, WIDTH, change_log_rows, is_retired, names_id, next_id, \
    rules_table

LANGS = ("en", "zh-CN")
KEYS = ("rule", "type", "enforced_by", "change")
TYPES = {"Hard": "硬", "Soft": "软", "Review": "审查", "Process": "流程"}
NONE = {"en": "None", "zh-CN": "无"}
RETIRED_TEXT = {"en": "Retired on {date}. ", "zh-CN": "已于 {date} 停用。"}
_PIPE = re.compile(r"(?<!\\)\|")


def run_rule_id(args) -> tuple[dict, int]:
    """Gives the next free P ID, every P row, and each rule's baseline lines (design 3.1).

    Returns:
        The report and the exit code: 1 when origin/main or its rules table is missing.
    """
    repo = git.need_repo(args.repo)
    state = read_rules(repo, lines="always")
    report = {"command": "rule-id", "ok": False, "notes": [], "problems": [],
              "next_id": None, "next_r_id": None, "rules": []}
    if state.table is None:
        report["problems"] = [f"{RULES} on origin/main is missing or has no rules table."]
        return report, 1
    report.update(ok=True, next_id=state.next_id(), next_r_id=state.next_r_id(),
                  rules=state.entries(), notes=state.unknown())
    return report, 0


def _bilingual(data: dict, key: str) -> dict:
    """Checks that a rule file's value is {"en": text, "zh-CN": text}."""
    value = data.get(key)
    if not isinstance(value, dict) or not all(isinstance(value.get(k), str) for k in LANGS):
        raise FlowError(f"the rule file's {key!r} must be an object with \"en\" and \"zh-CN\" "
                        "texts")
    return {k: value[k] for k in LANGS}


def load_rule_file(path: str, retire: bool) -> dict:
    """Reads --rule-file: the cells and the change-log text in both languages.

    Raises:
        FlowError: The file cannot be read, is not a JSON object, or lacks a key.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise FlowError(f"cannot read the rule file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FlowError(f"the rule file {path} must hold a JSON object")
    keys = ("change",) if retire else KEYS
    return {key: _bilingual(data, key) for key in keys}


def cell_problems(cells: dict) -> list[str]:
    """Finds the texts that would break the table, and a type that is not a rule type."""
    problems = []
    for key, values in cells.items():
        for lang, text in values.items():
            if not text.strip() or "\n" in text or "\r" in text or _PIPE.search(text):
                problems.append(f"The rule file's {key} ({lang}) would break the table: it is "
                                "empty, holds a line break, or holds a | without a \\.")
    kind = cells.get("type")
    if kind and TYPES.get(kind["en"].strip()) != kind["zh-CN"].strip():
        problems.append(f"The type {kind['en']!r} / {kind['zh-CN']!r} is not one of Hard (硬), "
                        "Soft (软), Review (审查), or Process (流程).")
    return problems


def _read_pair(root: Path) -> tuple[dict, list[str]]:
    """Reads both rules files: their texts and lines, or the problems that stop the write."""
    found, problems = {}, []
    for lang, path in zip(LANGS, (RULES, RULES_ZH)):
        header = header_of(root / path)
        if header is None:
            problems.append(f"{path} is missing or has no troy-doc header with lang and version.")
            continue
        lines = header[0].split("\n")
        table = rules_table(lines)
        if table is None or table.width != WIDTH:
            problems.append(f"{path} has no rules table with {WIDTH} columns.")
        if change_log_rows(lines) is None:
            problems.append(f"{path} has no change log table.")
        found[lang] = {"path": path, "text": header[0], "version": header[1]["version"],
                       "lines": lines, "table": table}
    if not problems and found["en"]["version"] != found["zh-CN"]["version"]:
        problems.append(f"{RULES} and {RULES_ZH} have different versions: "
                        f"{found['en']['version']} and {found['zh-CN']['version']}.")
    return found, problems


def _id_problems(rule_id: str, cells: dict, pair: dict, retire: bool) -> tuple[str, list[str]]:
    """Decides add, change, or retire, and finds what forbids it."""
    problems = [f"The change-log text ({lang}) does not name {rule_id}."
                for lang, text in cells["change"].items() if not names_id(text, rule_id)]
    table = pair["en"]["table"]
    index = table.find(rule_id)
    other = pair["zh-CN"]["table"].find(rule_id)
    free = next_id("P", [row[0] for row in table.rows if P_ID.fullmatch(row[0])])
    if (index is None) != (other is None):
        problems.append(f"{rule_id} has a row in only one of {RULES} and {RULES_ZH}.")
    if index is None:
        if rule_id != free:
            problems.append(f"{rule_id} is no row of {RULES} and not the next free ID, {free}.")
        elif retire:
            problems.append(f"{rule_id} has no row to retire.")
        return "add", problems
    if is_retired(table.rows[index][1]):
        problems.append(f"{rule_id} is retired; a retired ID is never used again.")
    return ("retire" if retire else "change"), problems


def _row_line(cells: list[str], ending: str) -> str:
    """Builds a table row line with single spaces around the pipes."""
    return "| " + " | ".join(cells) + " |" + ending


def _write_row(entry: dict, lang: str, rule_id: str, action: str, cells: dict,
               date: str) -> tuple[list[str], str]:
    """Adds, changes, or retires the row in one file's lines; returns them and the Since cell."""
    lines, table = list(entry["lines"]), entry["table"]
    index = table.find(rule_id)
    if action == "add":
        p_rows = table.p_indexes()
        at = table.line_of(p_rows[-1]) + 1 if p_rows else table.end()
        ending = "\r" if lines[at - 1].endswith("\r") else ""
        row = [rule_id, cells["rule"][lang].strip(), cells["type"][lang].strip(),
               cells["enforced_by"][lang].strip(), "project", date]
        lines.insert(at, _row_line(row, ending))
        return lines, date
    row = (list(table.rows[index]) + [""] * WIDTH)[:WIDTH]
    if action == "retire":
        row[1] = RETIRED_TEXT[lang].format(date=date) + row[1]
        row[3] = NONE[lang]
    else:
        row[1:4] = [cells[k][lang].strip() for k in ("rule", "type", "enforced_by")]
    at = table.line_of(index)
    lines[at] = _row_line(row, "\r" if lines[at].endswith("\r") else "")
    return lines, row[5]


def run_rule_row(args) -> tuple[dict, int]:
    """Writes one P row into the rules table and its mirror (design 3.1).

    Returns:
        The report and the exit code: 1, and nothing written, when a problem
        forbids the row.

    Raises:
        FlowError: Bad options, an unreadable rule file, or no repository.
    """
    if not P_ID.fullmatch(args.id):
        raise FlowError(f"--id {args.id!r} is not a P ID such as P01")
    date = check_date(args.date)
    cells = load_rule_file(args.rule_file, args.retire)
    repo = git.need_repo(args.repo)
    report = {"command": "rule-row", "ok": False, "notes": [], "problems": [], "id": args.id}
    pair, problems = _read_pair(repo.root)
    if not problems:
        action, found = _id_problems(args.id, cells, pair, args.retire)
        problems = cell_problems(cells) + found
    if problems:
        report["problems"] = problems
        return report, 1
    old = pair["en"]["version"]
    new, since = next_major(old), None
    for lang in LANGS:
        lines, row_since = _write_row(pair[lang], lang, args.id, action, cells, date)
        since = since or row_since
        text = rewrite("\n".join(lines), {"version": new, "updated": date,
                                          "status": STATUS[lang].format(date=date)})
        text = add_change_log_row(text, new, date, cells["change"][lang].strip())
        (repo.root / pair[lang]["path"]).write_bytes(text.encode("utf-8"))
    report.update(ok=True, action=action, version={"from": old, "to": new}, updated=date,
                  since=since, changed=[RULES, RULES_ZH])
    return report, 0

