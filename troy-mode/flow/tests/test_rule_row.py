"""Rule rows (F09 design 3.1, 6, 10.1; interface note sections 1 and 4): ``rule-row``.

``rule-row`` writes one P row into the working tree's ``docs/rules.md`` and
its mirror: a new row after the last P row, a changed row that keeps its
Since date, or a retired row. Both files move to the next major version,
"Approved by Troy on <date>", and get one change-log row. A row whose cells
would break the table, and every other refusal, leaves both files byte for
byte as they were.

Planted bugs of F09 design 10.2 caught here:

- "a reused retired ID": ``RefusalTests`` cases "retired ID changed", "retired ID retired
  again", and "retired ID as a new row".
- "a row written in English only": ``WriteTests.test_add_after_the_last_p_row`` and
  ``test_add_to_a_table_without_p_rows`` (the mirror is compared byte for byte).
- "Since changed on a changed rule": ``WriteTests.test_change_keeps_since``.
- "the version raised by a minor step instead of to the next major":
  ``VersionTests.test_next_major_version``.

F07 D201 (tstack issue #46) writes down that ``rule-row`` refuses, and writes
nothing, when either file has no change-log table, and makes its problem
name that file and both headings, ``Change log`` and ``修改记录``. Its planted
bugs of F07 design 14.2 are caught by ``RefusalTests``:

- "the note with exit 0 kept": the cases "no English change log table",
  "no change log table", and "Chinese change log heading renamed" of
  ``test_each_reason_is_refused_and_nothing_is_written``.
- "the mirror written before the English file's table is checked": its case
  "no English change log table".
- "the check made on the English file only": its cases "no change log table"
  and "Chinese change log heading renamed".
- A problem without the file or the headings:
  ``test_change_log_problem_names_the_file_and_both_headings``.
"""

import datetime
import json
import unittest

from flow_helpers import (
    RULES, SCRATCH, Fakes, FlowCase, Project, crlf, new_dir, parallel, run_engine,
)
from rule_helpers import (
    CLEANUP_EN, CLEANUP_ZH, DAY, DEFAULT_LOG, DEFAULT_RULES, FENCED, P01, P02, P03, P04,
    RULES_ZH, SEED_LOG, TOUCHED_EN, TOUCHED_ZH, PRule, log_row, rule_data, rule_file, rules_doc,
    rules_step,
)

CHANGED = ["docs/rules.md", "docs/rules.zh-CN.md"]
ADD_LOG = log_row("5.0", DAY, "Added P04, approved by Troy. " + CLEANUP_EN,
                  "新增 P04，Troy 批准。" + CLEANUP_ZH)
P02_NEW = PRule("P02", "No print or pprint calls in source.", "源码里不调用 print 或 pprint。",
                        "Soft", "CI (project-rules.yml, T20)", "CI（project-rules.yml，T20）")
CHANGE_P02 = rule_data(P02_NEW.rule, P02_NEW.rule_zh, "Soft", "软", P02_NEW.by, P02_NEW.by_zh,
                       "Changed P02, approved by Troy. " + TOUCHED_EN,
                       "修改 P02，Troy 批准。" + TOUCHED_ZH)
RETIRE_P03 = {"change": {"en": "Retired P03, approved by Troy.", "zh-CN": "停用 P03，Troy 批准。"}}
_ORIGIN = [rules_step()]
# The two change-log headings a D201 problem names (interface note for #46).
HEADINGS = ("Change log", "修改记录")


def approved(rules, log, version: str, **kwargs) -> dict:
    """Both files as rule-row leaves them on DAY: the new version, date, status, and row.

    Args:
        rules: The P rows after the write.
        log: The change-log rows after the write.
        version: The new version.
        **kwargs: More ``rules_doc`` arguments.

    Returns:
        ``{path: text}`` for both files.
    """
    return {path: rules_doc(lang, rules, log, version=version, updated=DAY,
                            status=None, **kwargs)
            for path, lang in ((RULES, "en"), (RULES_ZH, "zh-CN"))}


def run_row(case: dict):
    """In a fresh clone: writes the working tree's rules files, then runs ``rule-row``.

    Args:
        case: ``id``, ``data`` (the rule file's JSON) or ``raw`` (its bytes),
            optional ``files`` (working-tree path to text or bytes, None to
            delete), ``extra`` (more options), and ``date`` (False for none).

    Returns:
        ``(outcome, {path: bytes before}, {path: bytes after}, fakes)``.
    """
    project = Project(_ORIGIN)
    for path, content in case.get("files", {}).items():
        if content is None:
            project.remove(path)
        else:
            project.write(path, content)
    before = {path: project.read_bytes(path) if project.exists(path) else None
              for path in (RULES, RULES_ZH)}
    path = rule_file(project, case.get("data"), case.get("raw"))
    date = [] if case.get("date") is False else ["--date", case.get("date", DAY)]
    fakes = Fakes(fail=True)
    out = project.run("rule-row", "--id", case["id"], "--rule-file", path, *date,
                      *case.get("extra", ()), fakes=fakes)
    after = {path: project.read_bytes(path) if project.exists(path) else None
             for path in (RULES, RULES_ZH)}
    return out, before, after, fakes


def run_rows(cases: dict) -> dict:
    """Runs ``run_row`` for every case side by side; returns name mapped to its result."""
    names = list(cases)
    return dict(zip(names, parallel(lambda name: run_row(cases[name]), names)))


def as_bytes(files: dict) -> dict:
    """Paths mapped to UTF-8 bytes."""
    return {path: text.encode("utf-8") for path, text in files.items()}


class WriteTests(FlowCase):
    """Add, change, and retire (note section 4, "What it writes")."""

    @classmethod
    def setUpClass(cls):
        """Runs every write side by side, each in its own clone."""
        seeded = {RULES: rules_doc("en", (), (SEED_LOG,)),
                  RULES_ZH: rules_doc("zh-CN", (), (SEED_LOG,))}
        padded = rule_data(rule="  No bare except clauses.  ", by_zh=" Lint（ruff E722） ")
        escaped = rule_data(rule=r"Table cells escape the pipe as \|.",
                            rule_zh=r"表格单元格里的竖线写成 \|。")
        cls.results = run_rows({
            "add": {"id": "P04", "data": rule_data()},
            "add to seeded": {"id": "P01", "files": seeded, "data": rule_data(
                change="Added P01, approved by Troy. " + CLEANUP_EN,
                change_zh="新增 P01，Troy 批准。" + CLEANUP_ZH)},
            "change": {"id": "P02", "data": CHANGE_P02},
            "retire": {"id": "P03", "data": RETIRE_P03, "extra": ["--retire"]},
            "retire with other keys": {"id": "P03", "extra": ["--retire"], "data": {
                **RETIRE_P03, "type": {"en": "Bogus"}, "rule": "not an object"}},
            "padded": {"id": "P04", "data": padded},
            "escaped pipe": {"id": "P04", "data": escaped},
            "fenced example": {"id": "P04", "files": {
                RULES: rules_doc("en", section1_extra=FENCED),
                RULES_ZH: rules_doc("zh-CN", section1_extra=FENCED)}, "data": rule_data()},
            "crlf": {"id": "P04", "files": {RULES: crlf(rules_doc("en")),
                                            RULES_ZH: crlf(rules_doc("zh-CN"))},
                     "data": rule_data()},
        })

    def result(self, name: str, rule_id: str, action: str, since: str,
               version=("4.0", "5.0")) -> dict:
        """Asserts the case's exit 0 and report; returns the files after.

        Args:
            name: The case.
            rule_id: The expected ``id``.
            action: The expected ``action``.
            since: The expected ``since``.
            version: The expected ``(from, to)`` versions.

        Returns:
            Paths mapped to the bytes after the run.
        """
        out, _, after, fakes = self.results[name]
        report = self.report_of(out, 0, "rule-row")
        self.assertEqual(report["problems"], [])
        self.assertEqual((report["id"], report["action"], report["since"], report["updated"]),
                         (rule_id, action, since, DAY))
        self.assertEqual(report["version"], {"from": version[0], "to": version[1]})
        self.assertEqual(sorted(report["changed"]), CHANGED)
        self.assertEqual(fakes.gh_calls(), [])
        return after

    def test_add_after_the_last_p_row(self):
        """Planted bug "English only": P04 after P03 in both files, with Since, version 5.0,
        the status, and one change-log row in each file."""
        after = self.result("add", "P04", "add", DAY)
        self.assertEqual(after, as_bytes(approved(DEFAULT_RULES + (P04,),
                                                  DEFAULT_LOG + (ADD_LOG,), "5.0")))

    def test_add_to_a_table_without_p_rows(self):
        """The seeded table at 1.0: P01 after R21, version 2.0, in both files."""
        after = self.result("add to seeded", "P01", "add", DAY, ("1.0", "2.0"))
        p01 = PRule("P01", P04.rule, P04.rule_zh, "Hard", P04.by, P04.by_zh, since=DAY)
        log = (SEED_LOG, log_row("2.0", DAY, "Added P01, approved by Troy. " + CLEANUP_EN,
                                 "新增 P01，Troy 批准。" + CLEANUP_ZH))
        self.assertEqual(after, as_bytes(approved((p01,), log, "2.0")))

    def test_change_keeps_since(self):
        """Planted bug "Since changed": P02's Rule, Type, and Enforced by change in both files;
        its ID, Scope, and Since (2026-11-08) stay."""
        after = self.result("change", "P02", "change", "2026-11-08")
        log = DEFAULT_LOG + (log_row("5.0", DAY, "Changed P02, approved by Troy. " + TOUCHED_EN,
                                     "修改 P02，Troy 批准。" + TOUCHED_ZH),)
        self.assertEqual(after, as_bytes(approved((P01, P02_NEW, P03), log, "5.0")))

    def test_retire_keeps_the_row(self):
        """P03 retired: "Retired on <date>. " and "已于 <date> 停用。" before the old text,
        Enforced by None and 无; Type, Scope, and Since stay."""
        after = self.result("retire", "P03", "retire", "2026-11-09")
        log = DEFAULT_LOG + (log_row("5.0", DAY, "Retired P03, approved by Troy.",
                                     "停用 P03，Troy 批准。"),)
        expected = approved((P01, P02, P03.retired(DAY)), log, "5.0")
        self.assertEqual(after, as_bytes(expected))
        self.assertIn(f"| P03 | Retired on {DAY}. Every error message names the file it is about. "
                      "| Review | None | project | 2026-11-09 |", expected[RULES])
        self.assertIn(f"| P03 | 已于 {DAY} 停用。每条错误信息都写明它说的是哪个文件。 "
                      "| 审查 | 无 | project | 2026-11-09 |", expected[RULES_ZH])

    def test_retire_ignores_every_key_but_change(self):
        """With ``--retire``, a bad ``type`` and a ``rule`` that is no object are ignored."""
        self.assertEqual(self.result("retire with other keys", "P03", "retire", "2026-11-09"),
                         self.result("retire", "P03", "retire", "2026-11-09"))

    def test_cells_are_written_stripped(self):
        """Spaces around a cell's text are not written."""
        after = self.result("padded", "P04", "add", DAY)
        self.assertEqual(after, as_bytes(approved(DEFAULT_RULES + (P04,),
                                                  DEFAULT_LOG + (ADD_LOG,), "5.0")))

    def test_escaped_pipe_is_written_as_is(self):
        """A ``\\|`` in a cell does not break the table and is written unchanged."""
        after = self.result("escaped pipe", "P04", "add", DAY)
        p04 = PRule("P04", r"Table cells escape the pipe as \|.",
                            r"表格单元格里的竖线写成 \|。", "Hard", P04.by, P04.by_zh, since=DAY)
        self.assertEqual(after, as_bytes(approved(DEFAULT_RULES + (p04,),
                                                  DEFAULT_LOG + (ADD_LOG,), "5.0")))

    def test_fenced_table_stays(self):
        """The row goes into the rules table, not into a fenced example before it."""
        after = self.result("fenced example", "P04", "add", DAY)
        self.assertEqual(after, as_bytes(approved(DEFAULT_RULES + (P04,), DEFAULT_LOG + (ADD_LOG,),
                                                  "5.0", section1_extra=FENCED)))

    def test_crlf_files_get_crlf_lines(self):
        """CRLF files: the new row, the log row, and the changed header lines keep CRLF."""
        after = self.result("crlf", "P04", "add", DAY)
        expected = approved(DEFAULT_RULES + (P04,), DEFAULT_LOG + (ADD_LOG,), "5.0")
        self.assertEqual(after, {path: crlf(text) for path, text in expected.items()})


class SequenceTests(FlowCase):
    """``rule-row`` works on the working tree, never on origin/main (note section 4)."""

    def test_second_write_sees_the_first(self):
        """Add P04, then change it: the second run finds P04 in the tree and keeps its Since."""
        project = Project(_ORIGIN)
        first = project.run("rule-row", "--id", "P04", "--rule-file",
                            rule_file(project, rule_data()), "--date", DAY)
        self.report_of(first, 0, "rule-row")
        change = rule_data(by="Lint (ruff E722, BLE001)", by_zh="Lint（ruff E722、BLE001）",
                           change="Changed P04, approved by Troy. " + TOUCHED_EN,
                           change_zh="修改 P04，Troy 批准。" + TOUCHED_ZH)
        second = project.run("rule-row", "--id", "P04", "--rule-file",
                             rule_file(project, change), "--date", "2026-11-13")
        report = self.report_of(second, 0, "rule-row")
        self.assertEqual((report["action"], report["since"], report["version"]),
                         ("change", DAY, {"from": "5.0", "to": "6.0"}))
        p04 = PRule("P04", P04.rule, P04.rule_zh, "Hard", "Lint (ruff E722, BLE001)",
                            "Lint（ruff E722、BLE001）", since=DAY)
        log = DEFAULT_LOG + (ADD_LOG, log_row("6.0", "2026-11-13",
                                               "Changed P04, approved by Troy. " + TOUCHED_EN,
                                               "修改 P04，Troy 批准。" + TOUCHED_ZH))
        for path, lang in ((RULES, "en"), (RULES_ZH, "zh-CN")):
            with self.subTest(path=path):
                self.assertEqual(project.read(path),
                                 rules_doc(lang, DEFAULT_RULES + (p04,), log, version="6.0",
                                           updated="2026-11-13"))
        self.assertEqual(project.git("show", f"origin/main:{RULES}"), rules_doc("en"))

    def test_date_defaults_to_today(self):
        """Without ``--date``, Since, updated, and the log row carry today's date."""
        before = datetime.date.today().isoformat()
        out, _, after, _ = run_row({"id": "P04", "data": rule_data(), "date": False})
        today = datetime.date.today().isoformat()
        report = self.report_of(out, 0, "rule-row")
        self.assertIn(report["since"], {before, today})
        self.assertEqual(report["updated"], report["since"])
        day = report["since"]
        p04 = PRule("P04", P04.rule, P04.rule_zh, "Hard", P04.by, P04.by_zh, since=day)
        log = DEFAULT_LOG + (log_row("5.0", day, ADD_LOG[2], ADD_LOG[3]),)
        self.assertEqual(after[RULES], rules_doc("en", DEFAULT_RULES + (p04,), log,
                                                 version="5.0", updated=day).encode("utf-8"))


class VersionTests(FlowCase):
    """Planted bug "a minor step": the version moves to the next major (note section 4)."""

    CASES = (("0.3", "1.0"), ("1.0", "2.0"), ("2.4", "3.0"), ("9.0", "10.0"), ("10.2", "11.0"))

    def test_next_major_version(self):
        """0.3 to 1.0, 1.0 to 2.0, 2.4 to 3.0, 9.0 to 10.0, and 10.2 to 11.0, in both files."""
        cases = {old: {"id": "P04", "data": rule_data(), "files": {
            RULES: rules_doc("en", version=old), RULES_ZH: rules_doc("zh-CN", version=old)}}
            for old, _ in self.CASES}
        results = run_rows(cases)
        for old, new in self.CASES:
            with self.subTest(version=old):
                out, _, after, _ = results[old]
                report = self.report_of(out, 0, "rule-row")
                self.assertEqual(report["version"], {"from": old, "to": new})
                log = DEFAULT_LOG + (log_row(new, DAY, ADD_LOG[2], ADD_LOG[3]),)
                self.assertEqual(after, as_bytes(approved(DEFAULT_RULES + (P04,), log, new)))


def p_row_dropped(text: str, rule_id: str) -> str:
    """A rules file with one P row removed."""
    lines = text.split("\n")
    kept = [line for line in lines if not line.startswith(f"| {rule_id} |")]
    if len(kept) != len(lines) - 1:
        raise AssertionError(f"no single {rule_id} row")
    return "\n".join(kept)


RETIRED_FILES = {
    RULES: rules_doc("en", (P01, P02, P03, P04.retired("2026-11-11")),
                     DEFAULT_LOG + (ADD_LOG,)),
    RULES_ZH: rules_doc("zh-CN", (P01, P02, P03, P04.retired("2026-11-11")),
                        DEFAULT_LOG + (ADD_LOG,)),
}


def five_columns(text: str) -> str:
    """The Chinese rules table without its Since column."""
    out = []
    for line in text.split("\n"):
        if line.startswith("| ") and line.count("|") == 7 and ("编号" in line or line[2] in "RP-"):
            out.append("|".join(line.split("|")[:-2]) + "|")
        else:
            out.append(line)
    return "\n".join(out)


def swap(text: str, old: str, new: str) -> str:
    """Replaces a part that occurs exactly once."""
    if text.count(old) != 1:
        raise AssertionError(f"{old!r} occurs {text.count(old)} times")
    return text.replace(old, new)


class RefusalTests(FlowCase):
    """Exit 1: ok false, a problem per reason, and both files unchanged (note section 4)."""

    @classmethod
    def setUpClass(cls):
        """Runs every refused case side by side, each in its own clone."""
        en, zh = rules_doc("en"), rules_doc("zh-CN")
        no_version = en.replace('version: "4.0"\n', "")
        no_log_zh = zh.split("## 3. 修改记录")[0] + "## 3. 修改记录\n\n无。\n"
        no_table_en = en.split("## 2. Rules")[0] + "## 2. Rules\n\nNone yet.\n\n" + \
            "## 3. Change log" + en.split("## 3. Change log")[1]
        no_log_en = en.split("## 3. Change log")[0] + "## 3. Change log\n\nNone.\n"
        renamed_log_zh = swap(zh, "## 3. 修改记录\n", "## 3. 变更记录\n")
        cls.cases = {
            "English file missing": {"id": "P04", "data": rule_data(), "files": {RULES: None}},
            "mirror missing": {"id": "P04", "data": rule_data(), "files": {RULES_ZH: None}},
            "no version in the front matter": {"id": "P04", "data": rule_data(),
                                               "files": {RULES: no_version}},
            "versions differ": {"id": "P04", "data": rule_data(),
                                "files": {RULES_ZH: rules_doc("zh-CN", version="3.0")}},
            "no rules table": {"id": "P04", "data": rule_data(), "files": {RULES: no_table_en}},
            "five columns": {"id": "P04", "data": rule_data(),
                             "files": {RULES_ZH: five_columns(zh)}},
            "no change log table": {"id": "P04", "data": rule_data(),
                                    "files": {RULES_ZH: no_log_zh}},
            "no English change log table": {"id": "P04", "data": rule_data(),
                                            "files": {RULES: no_log_en}},
            "Chinese change log heading renamed": {"id": "P04", "data": rule_data(),
                                                   "files": {RULES_ZH: renamed_log_zh}},
            "empty cell": {"id": "P04", "data": rule_data(rule="   ")},
            "line break": {"id": "P04", "data": rule_data(by_zh="Lint\n（ruff E722）")},
            "carriage return": {"id": "P04", "data": rule_data(rule_zh="不写裸\rexcept。")},
            "bare pipe": {"id": "P04", "data": rule_data(rule="No a | b in cells.")},
            "bare pipe in the change": {"id": "P04", "data": rule_data(
                change="Added P04 | approved by Troy.")},
            "type not allowed": {"id": "P04", "data": rule_data(type_="Lint", type_zh="硬")},
            "type pair wrong": {"id": "P04", "data": rule_data(type_="Hard", type_zh="软")},
            "change does not name the ID": {"id": "P04", "data": rule_data(
                change="Added P040, approved by Troy.")},
            "Chinese change does not name the ID": {"id": "P04", "data": rule_data(
                change_zh="新增规则，Troy 批准。")},
            "not the next free ID": {"id": "P05", "data": rule_data(
                change="Added P05, approved by Troy.", change_zh="新增 P05。")},
            "retire an ID without a row": {"id": "P05", "extra": ["--retire"], "data": {
                "change": {"en": "Retired P05.", "zh-CN": "停用 P05。"}}},
            "retired ID changed": {"id": "P04", "files": RETIRED_FILES, "data": rule_data(
                change="Changed P04, approved by Troy.", change_zh="修改 P04。")},
            "retired ID retired again": {"id": "P04", "files": RETIRED_FILES,
                                         "extra": ["--retire"], "data": {
                                             "change": {"en": "Retired P04.",
                                                        "zh-CN": "停用 P04。"}}},
            "row only in English": {"id": "P03", "data": CHANGE_P02 | {"change": {
                "en": "Changed P03.", "zh-CN": "修改 P03。"}},
                "files": {RULES_ZH: p_row_dropped(zh, "P03")}},
            "new row only in the mirror": {"id": "P04", "data": rule_data(), "files": {
                RULES_ZH: rules_doc("zh-CN", DEFAULT_RULES + (P04,))}},
            "two reasons": {"id": "P04", "data": rule_data(type_="Lint", change="Added it.")},
        }
        cls.cases["control"] = {"id": "P04", "data": rule_data()}
        cls.cases["next ID after a retired one"] = {
            "id": "P05", "files": RETIRED_FILES, "data": rule_data(
                change="Added P05, approved by Troy. " + CLEANUP_EN,
                change_zh="新增 P05，Troy 批准。" + CLEANUP_ZH)}
        cls.results = run_rows(cls.cases)

    def test_control_is_written(self):
        """The same clone and rule file with nothing wrong: exit 0."""
        self.report_of(self.results["control"][0], 0, "rule-row")

    def test_each_reason_is_refused_and_nothing_is_written(self):
        """Every case: exit 1, ok false, string problems, and both files byte for byte unchanged."""
        self.test_control_is_written()
        for name in self.cases:
            if name in ("control", "next ID after a retired one"):
                continue
            with self.subTest(case=name):
                out, before, after, _ = self.results[name]
                report = self.report_of(out, 1, "rule-row")
                self.assertNotEqual(report["problems"], [])
                for problem in report["problems"]:
                    self.assertIsInstance(problem, str)
                self.assertEqual(after, before)

    def test_one_problem_per_reason(self):
        """A type that is not allowed and a change that does not name the ID: two problems."""
        report = self.report_of(self.results["two reasons"][0], 1, "rule-row")
        self.assertGreaterEqual(len(report["problems"]), 2, report["problems"])

    def test_change_log_problem_names_the_file_and_both_headings(self):
        """D201: a file without a change-log table (English with ``None.``, the mirror with
        ``无。``, the mirror headed ``变更记录``) is refused with both files unchanged, and a
        problem holds that file's path, ``Change log``, and ``修改记录``."""
        for name, path in (("no English change log table", RULES),
                           ("no change log table", RULES_ZH),
                           ("Chinese change log heading renamed", RULES_ZH)):
            with self.subTest(case=name):
                out, before, after, _ = self.results[name]
                problems = self.report_of(out, 1, "rule-row")["problems"]
                self.assertEqual(after, before)
                self.assertTrue(any(isinstance(problem, str) and path in problem
                                    and all(heading in problem for heading in HEADINGS)
                                    for problem in problems), problems)

    def test_next_id_after_a_retired_one_is_written(self):
        """After a retired P04, P05 is the next free ID: added after the retired row."""
        out, _, after, _ = self.results["next ID after a retired one"]
        report = self.report_of(out, 0, "rule-row")
        self.assertEqual((report["id"], report["action"], report["version"]),
                         ("P05", "add", {"from": "5.0", "to": "6.0"}))
        p05 = PRule("P05", P04.rule, P04.rule_zh, "Hard", P04.by, P04.by_zh, since=DAY)
        rules = (P01, P02, P03, P04.retired("2026-11-11"), p05)
        log = DEFAULT_LOG + (ADD_LOG, log_row("6.0", DAY, "Added P05, approved by Troy. "
                                               + CLEANUP_EN, "新增 P05，Troy 批准。" + CLEANUP_ZH))
        self.assertEqual(after, as_bytes(approved(rules, log, "6.0")))


class BadInputTests(FlowCase):
    """Exit 2: a rule file, ID, or date the engine cannot use; nothing is written (note 4)."""

    def test_bad_input_exits_two(self):
        """Unreadable, not JSON, not an object, a key missing, a value of the wrong shape,
        an ID that is not a P ID, or a date that is not a real date."""
        missing_by = rule_data()
        missing_by.pop("enforced_by")
        cases = {
            "control": {"id": "P04", "data": rule_data()},
            "not JSON": {"id": "P04", "raw": b"{not json"},
            "not UTF-8": {"id": "P04", "raw": b'{"rule": "\xff\xfe"}'},
            "an array": {"id": "P04", "data": [rule_data()]},
            "enforced_by missing": {"id": "P04", "data": missing_by},
            "change missing with --retire": {"id": "P03", "data": {"rule": {"en": "x",
                                                                            "zh-CN": "x"}},
                                             "extra": ["--retire"]},
            "value not an object": {"id": "P04", "data": rule_data() | {"rule": "No bare except."}},
            "no Chinese value": {"id": "P04", "data": rule_data() | {"type": {"en": "Hard"}}},
            "value not a string": {"id": "P04", "data": rule_data() | {
                "enforced_by": {"en": 7, "zh-CN": "七"}}},
            "ID P4": {"id": "P4", "data": rule_data()},
            "ID p04": {"id": "p04", "data": rule_data()},
            "ID P0004": {"id": "P0004", "data": rule_data()},
            "ID R22": {"id": "R22", "data": rule_data()},
            "date not real": {"id": "P04", "data": rule_data(), "date": "2026-02-30"},
            "date with slashes": {"id": "P04", "data": rule_data(), "date": "2026/11/12"},
        }
        results = run_rows(cases)
        self.report_of(results.pop("control")[0], 0, "rule-row")
        for name, (out, before, after, _) in results.items():
            with self.subTest(case=name):
                self.assert_exit(out, 2)
                self.assertEqual(after, before)

    def test_missing_rule_file_and_no_repository_exit_two(self):
        """A rule file that does not exist, and a folder that is not a repository."""
        project = Project(_ORIGIN)
        control = project.run("rule-row", "--id", "P04", "--rule-file",
                              rule_file(project, rule_data()), "--date", DAY)
        self.report_of(control, 0, "rule-row")
        other = Project(_ORIGIN)
        before = other.read_bytes(RULES)
        out = other.run("rule-row", "--id", "P04", "--rule-file", other.tmp / "nope.json",
                        "--date", DAY)
        self.assert_exit(out, 2)
        self.assertEqual(other.read_bytes(RULES), before)
        folder = new_dir("plain")
        path = folder / "rule.json"
        path.write_bytes(json.dumps(rule_data()).encode("utf-8"))
        out = run_engine(["rule-row", "--id", "P04", "--rule-file", path, "--date", DAY,
                          "--repo", folder, "--json"], SCRATCH, Fakes(fail=True))
        self.assert_exit(out, 2)


if __name__ == "__main__":
    unittest.main()
