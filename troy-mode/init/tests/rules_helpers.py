"""Rules-table helpers and the upgraded fake plugin, for the troy-init unit tests.

The rules table is compared line by line with the plugin's rules templates.
``apply_upgrade_changes`` turns a fake plugin into its next version; the
constants below name what it changes, as project paths.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from init_helpers import (
    RECORD, RULES, WORKFLOW, pr_body, read_text, replace_in, set_version, write_text,
)

RULE_TEMPLATES = {"docs/rules.md": "rules.md", "docs/rules.zh-CN.md": "rules.zh-CN.md"}
ROW = re.compile(r"^\| ([RP]\d{2}) \|")
CHANGE_LOG_ROW = re.compile(r"^\| \d+\.\d+ \|")
TEMPLATE_COMMENT = re.compile(r"<!--\s*template:.*?-->", re.S)

NEW_VERSION = "0.2.0"
UPGRADE_TITLE = f"[rules] Upgrade troy-mode to {NEW_VERSION}"
UPGRADE_BODY = pr_body(f"Bring troy-mode's files to the plugin's version {NEW_VERSION}.",
                       "The changed templates, troy-check, the workflow, the R rows of the rules "
                       "table, and the install record.")
CHANGED_TEMPLATE = ".troy-mode/templates/README.md"
KEPT_TEMPLATE = ".troy-mode/templates/test-plan.md"
NEW_TEMPLATE = ".troy-mode/templates/glossary.md"
DROPPED_TEMPLATE = ".troy-mode/templates/escalation.md"
CHANGED_CHECK = ".troy-mode/checks/troycheck/__init__.py"
CHANGED_HOOK = ".troy-mode/checks/git-hooks/commit-msg"
NEW_PATTERN = "**/check_*.py"
UPGRADE_STAGE = sorted([
    CHANGED_TEMPLATE, NEW_TEMPLATE, DROPPED_TEMPLATE, CHANGED_CHECK, CHANGED_HOOK, WORKFLOW,
    ".troy-mode/templates/rules.md", ".troy-mode/templates/rules.zh-CN.md", RECORD, *RULES,
])
R23 = {
    "docs/rules.md": "| R23 | Every PR description names the rules it relies on. "
                     "| Review | Product Manager | troy-mode | {{init-date}} |",
    "docs/rules.zh-CN.md": "| R23 | 每个 PR 描述都写明它依据的规则。 | 审查 | 产品经理 "
                           "| troy-mode | {{init-date}} |",
}
R03_EDITS = {
    "docs/rules.md": ("changes at most 500 lines", "changes at most 400 lines"),
    "docs/rules.zh-CN.md": ("最多改动 500 行", "最多改动 400 行"),
}
P_ROWS = {
    "docs/rules.md": [
        "| P01 | Modules keep no global state. | Hard | Review | project | 2026-11-08 |",
        "| P02 | Every public function shows an example. | Review | Architect | project "
        "| 2026-11-09 |",
    ],
    "docs/rules.zh-CN.md": [
        "| P01 | 模块不保存全局状态。 | 硬 | 审查 | project | 2026-11-08 |",
        "| P02 | 每个公开函数都给出示例。 | 审查 | 架构师 | project | 2026-11-09 |",
    ],
}


def fill_rules_template(text: str, name: str, date: str) -> str:
    """The rules template as setup should leave it, apart from blank lines."""
    text = TEMPLATE_COMMENT.sub("", text)
    return text.replace("{{project-name}}", name).replace("{{init-date}}", date)


def nonblank_lines(text: str) -> list:
    """The lines of a text that are not blank."""
    return [line for line in text.split("\n") if line.strip()]


def front_matter(text: str) -> dict:
    """The flat key: "value" pairs of a document's front matter."""
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        return {}
    fields = {}
    for line in lines[1:lines.index("---", 1)]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"')
    return fields


def rule_rows(text: str) -> list:
    """The R and P rows of a rules table, in order."""
    return [line for line in text.split("\n") if ROW.match(line)]


def change_log_rows(text: str) -> list:
    """The rows of a rules table's change log, in order."""
    return [line for line in text.split("\n") if CHANGE_LOG_ROW.match(line)]


def row_since(row: str) -> str:
    """The Since cell of a rules table row."""
    return row.rstrip().rstrip("|").rsplit("|", 1)[-1].strip()


def add_rows_after(text: str, after_id: str, rows: Sequence[str]) -> str:
    """Inserts table rows right after the row with the given ID."""
    lines = text.split("\n")
    index = next(i for i, line in enumerate(lines) if line.startswith(f"| {after_id} |"))
    return "\n".join(lines[:index + 1] + list(rows) + lines[index + 1:])


def apply_upgrade_changes(plugin: Path) -> None:
    """Turns a fake plugin into its next version, as the upgrade tests expect.

    Version NEW_VERSION; README.md changed; glossary.md added; escalation.md
    dropped; an R row's text changed and R23 added in both rules templates;
    the workflow, one troy-check module, and the commit-msg hook changed; and
    a new pattern in the Python pack's [paths] tests.
    """
    set_version(plugin, NEW_VERSION)
    templates = plugin / "troy-mode/templates"
    write_text(templates, "README.md", read_text(templates, "README.md") + "\nNew in 0.2.0.\n")
    write_text(templates, "glossary.md", "# Glossary\n\n<!-- template: One term per row. -->\n")
    (templates / "escalation.md").unlink()
    for project_path, template in RULE_TEMPLATES.items():
        replace_in(templates, template, *R03_EDITS[project_path])
        text = read_text(templates, template)
        write_text(templates, template, add_rows_after(text, "R22", [R23[project_path]]))
    checks = plugin / "troy-mode/checks"
    write_text(checks, "workflow.yml", read_text(checks, "workflow.yml") + "# Version 0.2.0.\n")
    init = read_text(checks, "troycheck/__init__.py")
    write_text(checks, "troycheck/__init__.py", init + "# Version 0.2.0.\n")
    (checks / "git-hooks/commit-msg").write_bytes(b"#!/bin/sh\n# Version 0.2.0.\nexit 0\n")
    add_pack_pattern(plugin, "python", "tests", NEW_PATTERN)


def add_pack_pattern(plugin: Path, pack: str, key: str, pattern: str) -> None:
    """Puts a pattern first in one list of a pack's [paths] table."""
    path = f"troy-mode/lang/{pack}/config.toml"
    replace_in(plugin, path, f"{key} = [", f'{key} = ["{pattern}", ')
