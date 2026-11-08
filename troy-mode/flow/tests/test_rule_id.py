"""Rule IDs (F09 design 3.1, 10.1; interface note sections 1 to 3): ``troy_flow.py rule-id``.

``rule-id`` reads ``docs/rules.md`` on ``origin/main`` and gives the next free
P ID, the next R ID, and each P row with whether it is retired, Troy's
choice for existing code, and its baseline lines in config and dependency
files.

Planted bug of F09 design 10.2 caught here: "a reused retired ID":
``NextIdTests.test_retired_id_is_not_reused``.
"""

import unittest

from flow_helpers import (
    CONFIG, RULES, SCRATCH, Fakes, FlowCase, Project, base_files, base_step, git, new_dir,
    parallel, run_engine,
)
from rule_helpers import (
    DEFAULT_LOG, FENCED, P01, P02, P03, PYPROJECT, PYPROJECT_TEXT, SEED_LOG, WORKFLOW,
    WORKFLOW_TEXT, PRule, added, default_entries, entry, log_row, rule_entry, rule_files,
    rules_config, rules_doc, rules_step,
)

P04 = PRule("P04", "No bare except clauses.", "不写裸 except。", "Hard", "Lint (ruff E722)",
            "Lint（ruff E722）", since="2026-11-10")
P99 = PRule("P99", "Commands print to standard error only.", "命令只往标准错误输出。", "Process",
            "troy-mode", "troy-mode")


def rule_id(project: Project, fakes=None):
    """Runs ``rule-id --repo <clone> --json`` with a gh that fails on every call."""
    return project.run("rule-id", fakes=fakes)


def run_cases(cases: dict) -> dict:
    """Clones one origin per case and runs ``rule-id`` in each, side by side.

    Args:
        cases: A name mapped to the history of origin/main.

    Returns:
        Each name mapped to its outcome.
    """
    names = list(cases)
    outs = parallel(lambda name: rule_id(Project(cases[name])), names)
    return dict(zip(names, outs))


class NextIdTests(FlowCase):
    """The next free P ID and the next R ID (interface note, section 1)."""

    @classmethod
    def setUpClass(cls):
        """Runs rule-id on one clone per table, side by side."""
        retired = (P01, P02, P03, P04.retired("2026-11-11"))
        retired_log = DEFAULT_LOG + (added("P04", "5.0", "2026-11-10", "cleanup"),
                                     log_row("6.0", "2026-11-11", "Retired P04, approved by Troy.",
                                             "停用 P04，Troy 批准。"))
        cls.outs = run_cases({
            "three rules": [rules_step()],
            "retired P04": [rules_step(retired, retired_log)],
            "no P row": [rules_step((), (SEED_LOG,))],
            "P99": [rules_step((P01, P99), DEFAULT_LOG[:2] + (added("P99", "3.0", "2026-11-08",
                                                                    None),))],
            "P rows only": [rules_step((P01,), DEFAULT_LOG[:2],
                                       rules_kwargs={"with_r_rows": False})],
            "fenced example": [rules_step(rules_kwargs={"section1_extra": FENCED})],
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name], 0, "rule-id")

    def test_next_id_after_three_rules(self):
        """P01 to P03: the next free ID is P04, and the next R ID is R22."""
        report = self.report("three rules")
        self.assertEqual((report["next_id"], report["next_r_id"]), ("P04", "R22"))
        self.assertEqual(report["problems"], [])

    def test_retired_id_is_not_reused(self):
        """Planted bug "a reused retired ID": P04 is retired, so the next free ID is P05."""
        report = self.report("retired P04")
        self.assertEqual(report["next_id"], "P05")
        self.assertEqual([(r["id"], r["retired"]) for r in report["rules"]],
                         [("P01", False), ("P02", False), ("P03", False), ("P04", True)])
        self.assertEqual(report["rules"][3]["rule"],
                         "Retired on 2026-11-11. No bare except clauses.")
        self.assertEqual(report["rules"][3]["enforced_by"], "None")

    def test_table_without_a_p_row(self):
        """The seeded table: P01 is next, no rule, and R22 is the next R ID."""
        report = self.report("no P row")
        self.assertEqual((report["next_id"], report["next_r_id"], report["rules"]),
                         ("P01", "R22", []))

    def test_next_id_after_p99_has_three_digits(self):
        """The highest number counts: after P99 comes P100."""
        report = self.report("P99")
        self.assertEqual(report["next_id"], "P100")
        self.assertEqual([r["id"] for r in report["rules"]], ["P01", "P99"])

    def test_table_without_an_r_row(self):
        """A table with P rows only is the rules table too: R01 is the next R ID."""
        report = self.report("P rows only")
        self.assertEqual((report["next_id"], report["next_r_id"]), ("P02", "R01"))
        self.assertEqual([r["id"] for r in report["rules"]], ["P01"])

    def test_fenced_table_and_other_tables_are_not_the_rules_table(self):
        """A fenced P99 row and a table without rule rows before the rules table are skipped."""
        report = self.report("fenced example")
        self.assertEqual((report["next_id"], report["next_r_id"]), ("P04", "R22"))
        self.assertEqual([r["id"] for r in report["rules"]], ["P01", "P02", "P03"])


class EntryTests(FlowCase):
    """Each P row as a rule entry, with Troy's choice and its baseline (note sections 1, 2)."""

    def test_entries_of_the_default_fixture(self):
        """P01 by cleanup PRs with four baseline lines, P02 when touched with two, P03 none."""
        report = self.report_of(rule_id(Project([rules_step()])), 0, "rule-id")
        self.assertEqual(report["rules"], default_entries())
        self.assertEqual(len(report["rules"][0]["baseline"]), 4)
        self.assertEqual(report["rules"][0]["baseline"][0]["path"], WORKFLOW)
        self.assertEqual(report["notes"], [])

    def test_choice_comes_from_the_newest_row_naming_the_rule(self):
        """The last change-log row naming the ID as a word decides, case-sensitively.

        P01: cleanup (a later row names P010, which is not P01). P02: cleanup,
        then changed to "fixed when touched". P03: cleanup, then a row without
        a choice. P04: the phrase in lower case is no choice.
        """
        log = (SEED_LOG, added("P01", "2.0", "2026-11-08", "cleanup"),
               added("P02", "3.0", "2026-11-08", "cleanup"),
               log_row("4.0", "2026-11-09", "Changed P02, approved by Troy. Existing code: "
                       "fixed when touched.", "修改 P02。"),
               added("P03", "5.0", "2026-11-09", "cleanup"),
               log_row("6.0", "2026-11-09", "Changed P03's wording, approved by Troy.",
                       "修改 P03 的措辞。"),
               log_row("7.0", "2026-11-10", "Added P04, approved by Troy. existing code: fixed "
                       "by cleanup PRs.", "新增 P04。"),
               log_row("8.0", "2026-11-10", "Noted P010 for later. Existing code: fixed when "
                       "touched.", "记下 P010。"))
        report = self.report_of(rule_id(Project([rules_step((P01, P02, P03, P04), log)])), 0)
        self.assertEqual([(r["id"], r["choice"]) for r in report["rules"]],
                         [("P01", "cleanup"), ("P02", "when-touched"), ("P03", None),
                          ("P04", None)])

    def test_rule_without_a_change_log_row_has_no_choice(self):
        """A P row whose ID no change-log row names: choice null."""
        report = self.report_of(rule_id(Project([rules_step((P01,), (SEED_LOG,))])), 0)
        self.assertEqual(report["rules"],
                         [rule_entry(P01, None, default_entries()[0]["baseline"])])
        self.assertEqual(report["next_id"], "P02")


SEARCH_CONFIG = rules_config(config=(".clang-tidy",), tail=(
    '[tests]\nlegacy = [\n    "tests/legacy/test_old.py",  # baseline: P01\n]\n'))
SEARCH_PYPROJECT = PYPROJECT_TEXT + (
    '"src/wordcount/a.py" = ["EM102"]  #baseline:P01\n'
    '"src/wordcount/b.py" = ["EM102"]  # baseline:\tP01\n'
    '"src/wordcount/c.py" = ["EM102"]  # baseline: P1\n'
    '"src/wordcount/d.py" = ["EM102"]  # baseline: p01\n'
    '"src/wordcount/e.py" = ["EM102"]  # baseline: P0100\n'
    '"src/wordcount/f.py" = ["EM102"]  # baseline P01\n'
    '"src/wordcount/g.py" = ["EM102"]  # baseline: P07\n')
CLANG_TIDY = "Checks: '-*,bugprone-*'\n# src/wordcount/native.cpp  baseline: P01\n"
NOT_SEARCHED = {
    ".github/pull_request_template.md": "## Checks\n\n- Baseline lines removed: baseline: P01\n",
    ".troy-mode/templates/rules.md": "<!-- baseline: P01 -->\n",
    ".troy-mode/notes.txt": "src/wordcount/count.py  # baseline: P01\n",
    "src/wordcount/count.py": '"""Count."""\n\nVALUE = 1  # baseline: P01\n',
    "tests/test_count.py": '"""Tests."""\n\nVALUE = 1  # baseline: P01\n',
    "tools/lint.cfg": "src/wordcount/count.py  # baseline: P01\n",
    "README.md": "# wordcount\n\nbaseline: P01\n",
}
SEARCH_RULES_EXTRA = "\nA line that holds `baseline: P01` in a config file exempts one file.\n"


class BaselineSearchTests(FlowCase):
    """Which files are searched and which lines are baseline lines (note section 2)."""

    @classmethod
    def setUpClass(cls):
        """Runs rule-id once on a project with baseline-like lines in many files."""
        extra = {CONFIG: SEARCH_CONFIG, PYPROJECT: SEARCH_PYPROJECT, ".clang-tidy": CLANG_TIDY,
                 **NOT_SEARCHED}
        files = rule_files(extra=extra, rules_kwargs={"section1_extra": SEARCH_RULES_EXTRA})
        cls.project = Project([base_step(files)])
        cls.out = rule_id(cls.project)

    def setUp(self):
        """Every test reads the one report."""
        self.report = self.report_of(self.out, 0, "rule-id")
        self.by_id = {r["id"]: r for r in self.report["rules"]}

    def test_p01_lines_in_config_and_dependency_files(self):
        """``.clang-tidy`` (classed config), the workflow, the config, and pyproject.toml.

        ``#baseline:P01`` and ``baseline:<tab>P01`` count; ``P1``, ``p01``,
        ``P0100``, and a line without the colon do not. Entries are sorted by
        path, then line.
        """
        expected = [
            entry(".clang-tidy", CLANG_TIDY, "# src/wordcount/native.cpp  baseline: P01"),
            entry(WORKFLOW, WORKFLOW_TEXT, "            - scripts/release.py  # baseline: P01"),
            entry(CONFIG, SEARCH_CONFIG, '    "tests/legacy/test_old.py",  # baseline: P01'),
            *[entry(PYPROJECT, SEARCH_PYPROJECT, line) for line in (
                '"src/wordcount/count.py" = ["EM102"]  # baseline: P01',
                '"src/wordcount/report.py" = ["EM102"]  # baseline: P01',
                '"tests/test_count.py" = ["EM102"]  # baseline: P01',
                '"src/wordcount/a.py" = ["EM102"]  #baseline:P01',
                '"src/wordcount/b.py" = ["EM102"]  # baseline:\tP01')],
        ]
        self.assertEqual(self.by_id["P01"]["baseline"], expected)

    def test_p02_lines_in_the_workflow(self):
        """P02's two exemptions in the project workflow, in line order."""
        self.assertEqual(self.by_id["P02"]["baseline"], [
            entry(WORKFLOW, WORKFLOW_TEXT, "            - src/wordcount/cli.py  # baseline: P02"),
            entry(WORKFLOW, WORKFLOW_TEXT,
                  "            - src/wordcount/debug.py  # baseline: P02")])
        self.assertEqual(self.by_id["P03"]["baseline"], [])

    def test_documents_templates_source_and_tests_are_not_searched(self):
        """No entry from a ``.md`` file, ``.troy-mode/`` besides the config, source, or tests."""
        paths = {item["path"] for rule in self.report["rules"] for item in rule["baseline"]}
        self.assertEqual(paths, {".clang-tidy", WORKFLOW, CONFIG, PYPROJECT})

    def test_line_of_an_unknown_rule_is_a_note(self):
        """``baseline: P07`` has no P row: one note names the path, the line, and the ID."""
        line = entry(PYPROJECT, SEARCH_PYPROJECT,
                     '"src/wordcount/g.py" = ["EM102"]  # baseline: P07')["line"]
        notes = [note for note in self.report["notes"] if "P07" in note]
        self.assertEqual(len(notes), 1, self.report["notes"])
        self.assertIn(PYPROJECT, notes[0])
        self.assertRegex(notes[0], rf"(?<!\d){line}(?!\d)")
        self.assertEqual([r["id"] for r in self.report["rules"]], ["P01", "P02", "P03"])


class CrlfBaselineTests(FlowCase):
    """A CRLF dependency file: lines are counted from 1 and given without their line ending."""

    def test_crlf_pyproject(self):
        """The three P01 lines of a CRLF pyproject.toml."""
        crlf_text = PYPROJECT_TEXT.replace("\n", "\r\n")
        project = Project([rules_step(extra={PYPROJECT: crlf_text.encode("utf-8")})])
        report = self.report_of(rule_id(project), 0, "rule-id")
        release = "            - scripts/release.py  # baseline: P01"
        expected = [entry(WORKFLOW, WORKFLOW_TEXT, release)]
        expected += [entry(PYPROJECT, PYPROJECT_TEXT, line) for line in (
            '"src/wordcount/count.py" = ["EM102"]  # baseline: P01',
            '"src/wordcount/report.py" = ["EM102"]  # baseline: P01',
            '"tests/test_count.py" = ["EM102"]  # baseline: P01')]
        self.assertEqual(report["rules"][0]["baseline"], expected)


class OriginMainTests(FlowCase):
    """``rule-id`` reads origin/main only (note section 3)."""

    def test_working_tree_and_branch_changes_are_ignored(self):
        """A P04 committed on the branch and an edited pyproject in the tree change nothing."""
        project = Project([rules_step()])
        en = rules_doc("en", (P01, P02, P03, P04), DEFAULT_LOG + (added("P04", "5.0", "2026-11-10",
                                                                         "cleanup"),))
        project.commit("[rules] Add P04, no bare except clauses", {RULES: en})
        project.write(PYPROJECT, '[project]\nname = "wordcount"\n')
        fakes = Fakes(fail=True)
        report = self.report_of(rule_id(project, fakes), 0, "rule-id")
        self.assertEqual(report["next_id"], "P04")
        self.assertEqual(report["rules"], default_entries())
        self.assertEqual(fakes.gh_calls(), [])
        self.assertEqual(fakes.mamba_calls(), [])


class FailureTests(FlowCase):
    """Exit 1 without a rules table on origin/main, exit 2 outside a repository (note 3)."""

    def assert_refused(self, out) -> None:
        """Exit 1, ok false, a problem, null IDs, and no rules."""
        report = self.report_of(out, 1, "rule-id")
        self.assertNotEqual(report["problems"], [])
        self.assertEqual((report["next_id"], report["next_r_id"], report["rules"]),
                         (None, None, []))

    def test_without_a_rules_table_on_origin_main(self):
        """No origin/main, no ``docs/rules.md`` on it, or a file without a rules table."""
        local = new_dir("local")
        git(local, "init", "-q", "-b", "main")
        (local / "docs").mkdir()
        (local / RULES).write_bytes(rules_doc().encode("utf-8"))
        git(local, "add", "-A")
        git(local, "commit", "-q", "-m", "Initial commit")
        no_file = base_files()
        no_file.pop(RULES)
        no_table = rules_doc().split("## 2. Rules")[0] + "## 2. Rules\n\nNone yet.\n"
        cases = {
            "no origin/main": lambda: run_engine(["rule-id", "--repo", local, "--json"], SCRATCH,
                                                 Fakes(fail=True)),
            "no rules file": lambda: rule_id(Project([base_step(no_file)])),
            "no rules table": lambda: rule_id(Project([rules_step(extra={RULES: no_table})])),
            "control": lambda: rule_id(Project([rules_step()])),
        }
        outs = dict(zip(cases, parallel(lambda name: cases[name](), list(cases))))
        self.report_of(outs.pop("control"), 0, "rule-id")
        for name, out in outs.items():
            with self.subTest(case=name):
                self.assert_refused(out)

    def test_outside_a_repository_exits_two(self):
        """A folder that is not a git repository: exit 2."""
        control = rule_id(Project([rules_step()]))
        self.report_of(control, 0, "rule-id")
        folder = new_dir("plain")
        out = run_engine(["rule-id", "--repo", folder, "--json"], SCRATCH, Fakes(fail=True))
        self.assert_exit(out, 2)


if __name__ == "__main__":
    unittest.main()
