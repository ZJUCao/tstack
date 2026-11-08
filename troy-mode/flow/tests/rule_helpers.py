"""Shared fixtures for the F09 engine tests (F09 design 10.1; F09 interface note).

F09's state lives in ``docs/rules.md`` and its mirror on ``origin/main``, in
the baseline lines of config and dependency files, and in open PRs. These
helpers build that state on top of ``flow_helpers``' seed project:

- ``rules_doc`` writes the rules table in the shape troy-init seeds from
  ``troy-mode/templates/rules.md``, template comments removed: front matter,
  the six-column rules table with the real R01 to R21 rows of the template,
  the project's P rows, and the change log. The Chinese mirror follows the
  same rows with Chinese cells (interface note, section 1).
- ``PYPROJECT_TEXT`` and ``WORKFLOW_TEXT`` hold baseline lines: P01's in
  ruff's ``per-file-ignores`` and one in the project workflow, P02's in the
  project workflow.
- ``rule_files`` and ``rules_step`` make a project's first commit with all of
  it, over ``base_files``.
- ``rule_file`` writes the JSON file ``rule-row --rule-file`` reads.

Nothing here imports the engine.
"""

from __future__ import annotations

import functools
import itertools
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Optional, Sequence

from flow_helpers import (
    EMAIL, ENVIRONMENT, PLUGIN_ROOT, RULES, Content, Project, base_files, base_step,
    front_matter,
)

RULES_ZH = "docs/rules.zh-CN.md"
PYPROJECT = "pyproject.toml"
WORKFLOW = ".github/workflows/project-rules.yml"
SEED_DATE = "2026-11-07"
DAY = "2026-11-12"
TEMPLATES = PLUGIN_ROOT / "troy-mode/templates"
TYPE_ZH = {"Hard": "硬", "Soft": "软", "Review": "审查", "Process": "流程"}
SEEDED_EN = "Seeded by troy-init from troy-mode."
SEEDED_ZH = "由 troy-init 根据 troy-mode 初始化。"
CLEANUP_EN = "Existing code: fixed by cleanup PRs."
TOUCHED_EN = "Existing code: fixed when touched."
CLEANUP_ZH = "已有代码：用清理 PR 修复。"
TOUCHED_ZH = "已有代码：改到时修复。"
_COUNTER = itertools.count(1)


# ------------------------------------------------------------------ P rows

@dataclass(frozen=True)
class PRule:
    """One P row of the rules table, in both languages.

    Attributes:
        id: The P ID, for example ``P01``.
        rule: The English Rule cell.
        rule_zh: The Chinese Rule cell.
        type: The English Type cell: Hard, Soft, Review, or Process.
        by: The English Enforced by cell.
        by_zh: The Chinese Enforced by cell.
        since: The Since cell.
        type_zh: The Chinese Type cell, or "" for the pair of ``type``.
    """

    id: str
    rule: str
    rule_zh: str
    type: str
    by: str
    by_zh: str
    since: str = "2026-11-08"
    type_zh: str = ""

    def en_row(self) -> str:
        """The English row, for example ``| P01 | ... | project | 2026-11-08 |``."""
        return f"| {self.id} | {self.rule} | {self.type} | {self.by} | project | {self.since} |"

    def zh_row(self) -> str:
        """The Chinese row, with the Chinese type and the Scope cell ``project``."""
        kind = self.type_zh or TYPE_ZH[self.type]
        return f"| {self.id} | {self.rule_zh} | {kind} | {self.by_zh} | project | {self.since} |"

    def retired(self, date: str) -> "PRule":
        """The row as ``rule-row --retire`` leaves it (interface note, section 4).

        Args:
            date: The ``--date`` of the retirement.

        Returns:
            A copy whose Rule cells start with ``Retired on <date>.`` and
            ``已于 <date> 停用。`` and whose Enforced by cells are None and 无.
        """
        return replace(self, rule=f"Retired on {date}. {self.rule}",
                       rule_zh=f"已于 {date} 停用。{self.rule_zh}", by="None", by_zh="无")


P01 = PRule("P01", "No f-string in an exception message.", "异常信息里不用 f-string。", "Hard",
            "Lint (ruff EM102)", "Lint（ruff EM102）")
P02 = PRule("P02", "No print calls in source.", "源码里不调用 print。", "Hard",
            "CI (project-rules.yml)", "CI（project-rules.yml）")
P03 = PRule("P03", "Every error message names the file it is about.",
            "每条错误信息都写明它说的是哪个文件。", "Review", "Code Reviewer", "代码审查员",
            since="2026-11-09")
DEFAULT_RULES = (P01, P02, P03)

# Section 1 text with a fenced example row (P99) and a table without rule
# rows, both before the rules table: neither is the rules table.
FENCED = ("\nA P row looks like this:\n\n```markdown\n"
          "| ID | Rule | Type | Enforced by | Scope | Since |\n"
          "| --- | --- | --- | --- | --- | --- |\n"
          "| P99 | An example inside a fence. | Hard | Lint | project | 2026-01-01 |\n```\n\n"
          "| Type | Blocks the merge |\n| --- | --- |\n| Hard | Yes |\n| Soft | No |\n")


def log_row(version: str, date: str, en: str, zh: str) -> tuple:
    """One change-log row in both languages: ``(version, date, English, Chinese)``."""
    return (version, date, en, zh)


def added(rule_id: str, version: str, date: str, choice: Optional[str]) -> tuple:
    """The change-log row of a rule's approval with Troy's choice for existing code.

    Args:
        rule_id: The P ID.
        version: The table's version after the change.
        date: The date.
        choice: ``cleanup``, ``when-touched``, or None for no choice.

    Returns:
        A ``log_row``.
    """
    en = {"cleanup": " " + CLEANUP_EN, "when-touched": " " + TOUCHED_EN}.get(choice, "")
    zh = {"cleanup": CLEANUP_ZH, "when-touched": TOUCHED_ZH}.get(choice, "")
    return log_row(version, date, f"Added {rule_id}, approved by Troy.{en}",
                   f"新增 {rule_id}，Troy 批准。{zh}")


SEED_LOG = log_row("1.0", SEED_DATE, "Seeded with R01 to R21 from troy-mode.",
                   "初始化，包含来自 troy-mode 的 R01 到 R21。")
DEFAULT_LOG = (SEED_LOG, added("P01", "2.0", "2026-11-08", "cleanup"),
               added("P02", "3.0", "2026-11-08", "when-touched"),
               added("P03", "4.0", "2026-11-09", "when-touched"))


@functools.lru_cache(maxsize=None)
def r_rows(lang: str = "en") -> tuple:
    """The R01 to R21 rows of the rules template, as troy-init seeds them.

    Args:
        lang: ``en`` or ``zh-CN``.

    Returns:
        The rows, with ``{{init-date}}`` replaced by the seed date.

    Raises:
        AssertionError: The template does not hold the 21 R rows.
    """
    name = "rules.md" if lang == "en" else "rules.zh-CN.md"
    text = (TEMPLATES / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
    rows = tuple(line.replace("{{init-date}}", SEED_DATE) for line in text.split("\n")
                 if re.match(r"^\| R\d{2} \|", line))
    if [row[2:5] for row in rows] != [f"R{n:02d}" for n in range(1, 22)]:
        raise AssertionError(f"troy-mode/templates/{name} does not hold the rows R01 to R21")
    return rows


def rules_doc(lang: str = "en", rules: Sequence[PRule] = DEFAULT_RULES,
              log: Sequence[tuple] = DEFAULT_LOG, version: Optional[str] = None,
              updated: Optional[str] = None, status: Optional[str] = None,
              with_r_rows: bool = True, section1_extra: str = "") -> str:
    """The rules table or its mirror, as troy-init seeds it and F09 extends it.

    Args:
        lang: ``en`` or ``zh-CN``.
        rules: The P rows, in table order.
        log: The change-log rows, ``log_row`` tuples, oldest first.
        version: The front matter's version, or None for the last log row's.
        updated: The front matter's date, or None for the last log row's.
        status: The front matter's status, or None for the seeded status
            when the log has one row and "Approved by Troy on <updated>"
            (``Troy 已于 <updated> 批准``) otherwise.
        with_r_rows: Whether the table holds the template's R01 to R21.
        section1_extra: Text appended to section 1, before ``## 2.``.

    Returns:
        The document text, with LF line endings.
    """
    english = lang == "en"
    version = version or log[-1][0]
    updated = updated or log[-1][1]
    if status is None:
        if len(log) == 1:
            status = SEEDED_EN if english else SEEDED_ZH
        else:
            status = f"Approved by Troy on {updated}" if english else f"Troy 已于 {updated} 批准"
    head = front_matter("rules", lang, version, "rules.zh-CN.md" if english else "rules.md",
                        status, updated)
    rows = list(r_rows(lang)) if with_r_rows else []
    rows += [rule.en_row() if english else rule.zh_row() for rule in rules]
    log_lines = [f"| {v} | {d} | {en if english else zh} |" for v, d, en, zh in log]
    if english:
        return head + (
            "# wordcount rules\n\n## 1. Rule types\n\n"
            "- **Hard** blocks the merge.\n"
            "- **Soft** allows the PR when its description gives a reason.\n"
            "- **Review** is checked by a role.\n"
            "- **Process** is followed by troy-mode itself.\n" + section1_extra + "\n"
            "## 2. Rules\n\n| ID | Rule | Type | Enforced by | Scope | Since |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n\n"
            "## 3. Change log\n\n| Version | Date | Change |\n| --- | --- | --- |\n"
            + "\n".join(log_lines) + "\n")
    return head + (
        "# wordcount 规则\n\n## 1. 规则类型\n\n"
        "- **硬规则**：不满足就不能合入。\n"
        "- **软规则**：PR 描述里写明原因就可以合入。\n"
        "- **审查**：由某个角色检查。\n"
        "- **流程**：由 troy-mode 自己遵守。\n" + section1_extra + "\n"
        "## 2. 规则\n\n| 编号 | 规则 | 类型 | 由什么保证 | 适用范围 | 起始日期 |\n"
        "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n\n"
        "## 3. 修改记录\n\n| 版本 | 日期 | 修改 |\n| --- | --- | --- |\n"
        + "\n".join(log_lines) + "\n")


def rules_pair(rules: Sequence[PRule] = DEFAULT_RULES, log: Sequence[tuple] = DEFAULT_LOG,
               **kwargs) -> dict:
    """Both rules files, as paths mapped to text.

    Args:
        rules: The P rows.
        log: The change-log rows.
        **kwargs: Passed on to ``rules_doc`` for both files.

    Returns:
        ``{docs/rules.md: ..., docs/rules.zh-CN.md: ...}``.
    """
    return {RULES: rules_doc("en", rules, log, **kwargs),
            RULES_ZH: rules_doc("zh-CN", rules, log, **kwargs)}


# --------------------------------------------------------- baseline files

PYPROJECT_TEXT = (
    '[project]\nname = "wordcount"\nversion = "0.1.0"\n\n'
    '[tool.ruff.lint]\nextend-select = ["EM102"]\n\n'
    '[tool.ruff.lint.per-file-ignores]\n'
    '"src/wordcount/count.py" = ["EM102"]  # baseline: P01\n'
    '"src/wordcount/report.py" = ["EM102"]  # baseline: P01\n'
    '"tests/test_count.py" = ["EM102"]  # baseline: P01\n')
PYPROJECT_CLEAN = (
    '[project]\nname = "wordcount"\nversion = "0.1.0"\n\n'
    '[tool.ruff.lint]\nextend-select = ["EM102"]\n')
WORKFLOW_TEXT = (
    "name: Project rules\non: [pull_request]\njobs:\n  project-rules:\n"
    "    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"
    "      - name: P02, no print calls in source\n"
    "        uses: ./.github/actions/grep-none\n        with:\n"
    "          pattern: 'print('\n          paths: src\n          exempt:\n"
    "            - src/wordcount/cli.py  # baseline: P02\n"
    "            - src/wordcount/debug.py  # baseline: P02\n"
    "      - name: P01, no f-string in exception messages of scripts\n"
    "        uses: ./.github/actions/grep-none\n        with:\n"
    "          pattern: 'Error(f\"'\n          paths: scripts\n          exempt:\n"
    "            - scripts/release.py  # baseline: P01\n")
WORKFLOW_CLEAN = "name: Project rules\non: [pull_request]\njobs: {}\n"
SOURCE = {"src/wordcount/count.py": '"""Count."""\n\n\ndef count(text):\n'
                                    '    """Counts."""\n    return len(text.split())\n',
          "src/wordcount/report.py": '"""Report."""\n',
          "tests/test_count.py": '"""Tests."""\n'}


def entry(path: str, text: str, line: str) -> dict:
    """A baseline entry of the interface note, section 2.

    Args:
        path: The file's path.
        text: The file's text.
        line: The whole line, without its line ending; it must occur once.

    Returns:
        ``{"path": ..., "line": <number from 1>, "text": line}``.

    Raises:
        AssertionError: The line does not occur exactly once.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    if lines.count(line) != 1:
        raise AssertionError(f"{line!r} occurs {lines.count(line)} times in {path}")
    return {"path": path, "line": lines.index(line) + 1, "text": line}


def lines_with(text: str, needle: str) -> list:
    """The lines of a text that hold a needle, in order."""
    return [line for line in text.replace("\r\n", "\n").split("\n") if needle in line]


def baseline_of(rule_id: str, files: Mapping[str, str]) -> list:
    """The baseline entries of one rule in the given searched files, sorted by path and line.

    The caller names the files the engine searches; each line that holds
    ``baseline: <ID>`` written exactly so is an entry.

    Args:
        rule_id: The P ID.
        files: Searched paths mapped to their text.

    Returns:
        The entries.
    """
    found = []
    for path in sorted(files):
        for line in lines_with(files[path], f"baseline: {rule_id}"):
            found.append(entry(path, files[path], line))
    return found


def rule_entry(rule: PRule, choice: Optional[str], baseline: Sequence[dict],
               retired: bool = False) -> dict:
    """A rule entry of ``rule-id`` and ``status`` (interface note, section 2).

    Args:
        rule: The P row.
        choice: ``cleanup``, ``when-touched``, or None.
        baseline: The rule's baseline entries.
        retired: Whether the row is retired.

    Returns:
        The entry.
    """
    return {"id": rule.id, "rule": rule.rule, "type": rule.type, "enforced_by": rule.by,
            "since": rule.since, "retired": retired, "choice": choice,
            "baseline": list(baseline)}


def default_entries(pyproject: str = PYPROJECT_TEXT, workflow: str = WORKFLOW_TEXT) -> list:
    """The rule entries of the default fixture: P01 cleanup, P02 and P03 fixed when touched.

    Args:
        pyproject: The ``pyproject.toml`` text on origin/main.
        workflow: The project workflow's text on origin/main.

    Returns:
        The entries, in table order.
    """
    searched = {PYPROJECT: pyproject, WORKFLOW: workflow}
    return [rule_entry(P01, "cleanup", baseline_of("P01", searched)),
            rule_entry(P02, "when-touched", baseline_of("P02", searched)),
            rule_entry(P03, "when-touched", [])]


# ----------------------------------------------------------------- project

def rules_config(lang: Optional[str] = "python", dependencies: Sequence[str] = (PYPROJECT,),
                 config: Sequence[str] = (), tail: str = "") -> str:
    """A project config with chosen ``[paths]`` lists (troy-check accepts it).

    Args:
        lang: ``python``, ``cpp``, or None for no ``[lang]`` table.
        dependencies: The ``[paths] dependencies`` patterns.
        config: The ``[paths] config`` patterns.
        tail: Raw TOML appended at the end.

    Returns:
        The TOML text.
    """
    text = f'[identity]\ncommit_email = "{EMAIL}"\n\n[paths]\n'
    if config:
        text += f"config = {json.dumps(list(config))}\n"
    text += f'dependencies = {json.dumps(list(dependencies))}\n\n[attribution]\nmode = "strict"\n'
    if lang == "python":
        text += (f'\n[lang]\nname = "python"\nsource_roots = ["src"]\n'
                 f'environment = "{ENVIRONMENT}"\nseries = ["."]\n')
    elif lang == "cpp":
        text += (f'\n[lang]\nname = "cpp"\ninclude_dirs = ["include", "src"]\n'
                 f'environment = "{ENVIRONMENT}"\nseries = ["."]\n')
    return text + (("\n" + tail) if tail else "")


def rule_files(rules: Sequence[PRule] = DEFAULT_RULES, log: Sequence[tuple] = DEFAULT_LOG,
               extra: Optional[Mapping[str, Content]] = None, rules_kwargs=None,
               **base_kwargs) -> dict:
    """A project's first commit with the rules pair, the baseline files, and some source.

    Args:
        rules: The P rows.
        log: The change-log rows.
        extra: More files, which replace the defaults of the same path; a
            None value leaves the path out.
        rules_kwargs: More arguments for ``rules_doc``.
        **base_kwargs: Passed on to ``base_files`` (``features``, ``lang``,
            ``plans``, ...).

    Returns:
        Paths mapped to content.
    """
    files = base_files(**base_kwargs)
    files.update(rules_pair(rules, log, **(rules_kwargs or {})))
    files.update({PYPROJECT: PYPROJECT_TEXT, WORKFLOW: WORKFLOW_TEXT, **SOURCE})
    for path, content in (extra or {}).items():
        if content is None:
            files.pop(path, None)
        else:
            files[path] = content
    return files


def rules_step(*args, **kwargs):
    """The first commit of a project with the F09 fixture (``rule_files``' arguments)."""
    return base_step(rule_files(*args, **kwargs))


def rule_file(project: Project, data, raw: Optional[bytes] = None) -> Path:
    """Writes a rule file for ``rule-row --rule-file`` outside the clone.

    Args:
        project: The clone; the file goes into its scratch folder.
        data: The JSON value to write.
        raw: Exact bytes to write instead of ``data``.

    Returns:
        The file's path.
    """
    path = project.tmp / f"rule-{next(_COUNTER)}.json"
    path.write_bytes(raw if raw is not None else
                     json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))
    return path


def rule_data(rule: str = "No bare except clauses.", rule_zh: str = "不写裸 except。",
              type_: str = "Hard", type_zh: str = "硬", by: str = "Lint (ruff E722)",
              by_zh: str = "Lint（ruff E722）",
              change: str = "Added P04, approved by Troy. " + CLEANUP_EN,
              change_zh: str = "新增 P04，Troy 批准。" + CLEANUP_ZH) -> dict:
    """The JSON object of a rule file (interface note, section 4).

    Returns:
        ``{"rule": {...}, "type": {...}, "enforced_by": {...}, "change": {...}}``.
    """
    return {"rule": {"en": rule, "zh-CN": rule_zh}, "type": {"en": type_, "zh-CN": type_zh},
            "enforced_by": {"en": by, "zh-CN": by_zh},
            "change": {"en": change, "zh-CN": change_zh}}


P04 = PRule("P04", "No bare except clauses.", "不写裸 except。", "Hard", "Lint (ruff E722)",
            "Lint（ruff E722）", since=DAY)
