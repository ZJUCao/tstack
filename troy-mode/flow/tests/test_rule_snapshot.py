"""Snapshot and check (F09 design 3.1, 5.3, 5.4, 10.1; interface note section 5).

``snapshot --role rules`` is the main session's own work on a ``[rules]``
PR: it may change the ``config`` and ``dependencies`` path classes only. In
``check-run``, for every role, a dependency file whose only change is whole
baseline lines deleted is not a dependency problem.

Planted bugs of F09 design 10.2 caught here:

- "the ``rules`` role allowed to change docs":
  ``RulesScopeTests.test_other_classes_are_out_of_scope``
  and ``test_rules_table_with_a_document_is_stopped``.
- "a baseline deletion that also adds a line passing ``check-run``":
  ``BaselineRuleTests.test_deletion_with_an_added_line_is_a_dependency_change`` and
  ``test_deletion_with_a_new_baseline_line_is_a_dependency_change``.
"""

import json
import unittest
from datetime import datetime, timedelta, timezone

from flow_helpers import (
    ARCHITECTURE, CONFIG, RULES, WORK_BRANCH, FlowCase, Project, crlf, hooks_line, parallel,
    problem_kinds,
)
from rule_helpers import (
    DAY, PYPROJECT, RULES_ZH, WORKFLOW, rule_data, rule_file, rules_config, rules_step,
)

HEAD_PYPROJECT = (
    '[project]\nname = "wordcount"\nversion = "0.1.0"\n\n'
    '[tool.ruff.lint]\nextend-select = ["EM102", "T20"]\n\n'
    '[tool.ruff.lint.per-file-ignores]\n'
    '"src/wordcount/count.py" = ["EM102"]  # baseline: P01\n'
    '"src/wordcount/report.py" = ["EM102"]  # baseline: P01\n'
    '"tests/test_count.py" = ["EM102"]  # baseline: P01\n'
    '"src/wordcount/cli.py" = ["T20"]  # baseline: P07\n'
    '"src/wordcount/debug.py" = ["T20"]  # baseline P02\n'
    '"src/wordcount/old.py" = ["T20"]  # baseline: P1\n')
COUNT_LINE = '"src/wordcount/count.py" = ["EM102"]  # baseline: P01\n'
REPORT_LINE = '"src/wordcount/report.py" = ["EM102"]  # baseline: P01\n'
TEST_LINE = '"tests/test_count.py" = ["EM102"]  # baseline: P01\n'
P07_LINE = '"src/wordcount/cli.py" = ["T20"]  # baseline: P07\n'
NO_COLON_LINE = '"src/wordcount/debug.py" = ["T20"]  # baseline P02\n'
SHORT_ID_LINE = '"src/wordcount/old.py" = ["T20"]  # baseline: P1\n'
REQUIREMENTS_TXT = "requirements.txt"
SNAPSHOT_CONFIG = rules_config(dependencies=(PYPROJECT, REQUIREMENTS_TXT))
EXTRA = {PYPROJECT: HEAD_PYPROJECT, CONFIG: SNAPSHOT_CONFIG,
         REQUIREMENTS_TXT: "click==8.1.7\nrich==13.9.4  # baseline: P01\n",
         "src/wordcount/cli.py": '"""CLI."""\n'}


def shifted(time_text: str, seconds: int) -> str:
    """A ``YYYY-MM-DDTHH:MM:SSZ`` time moved by some seconds."""
    when = datetime.strptime(time_text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (when + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def without(text: str, *lines: str) -> str:
    """The text with each given whole line removed once."""
    for line in lines:
        if text.count(line) != 1:
            raise AssertionError(f"{line!r} occurs {text.count(line)} times")
        text = text.replace(line, "")
    return text


class RunCase(FlowCase):
    """One shared clone of the F09 fixture, put back to its first state before every test."""

    @classmethod
    def setUpClass(cls):
        """Builds the clone and remembers its HEAD."""
        cls.project = Project([rules_step(extra=EXTRA)])
        cls.base = cls.project.head()

    def setUp(self):
        """Returns to the work branch at the first HEAD, removes every other file and the log."""
        project = self.project
        project.git("switch", "-q", "-f", WORK_BRANCH)
        project.git("reset", "-q", "--hard", self.base)
        project.git("clean", "-q", "-fdx")
        log = project.git_dir() / "troy-mode" / "hooks.log"
        if log.exists():
            log.unlink()

    def run_role(self, role: str, changes: dict, allow=(), code: int = 0) -> dict:
        """Snapshot for one role, the changes, and check-run; returns check-run's report.

        Args:
            role: The role.
            changes: Paths mapped to new text or bytes, None to delete.
            allow: Paths for ``--allow-dependency``.
            code: The expected exit code of check-run.

        Returns:
            The check-run report.
        """
        snap = self.report_of(self.project.run("snapshot", "--role", role), 0, "snapshot")
        for rel, content in changes.items():
            if content is None:
                self.project.remove(rel)
            else:
                self.project.write(rel, content)
        args = ["check-run", "--run", snap["run"]]
        for path in allow:
            args += ["--allow-dependency", path]
        return self.report_of(self.project.run(*args), code, "check-run")

    def assert_passes(self, report: dict, paths) -> None:
        """Asserts no problem, the sorted paths to stage, no undo, and no escalation."""
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["stage"], sorted(paths))
        self.assertEqual(report["undo"], [])
        self.assertIs(report["escalate"], False)

    def assert_problems(self, report: dict, kinds) -> None:
        """Asserts exactly these ``(kind, path)`` problems and nothing to stage."""
        self.assertEqual(problem_kinds(report), sorted(kinds))
        self.assertEqual(report["stage"], [])
        self.assertIs(report["escalate"], False)


class RulesScopeTests(RunCase):
    """The ``rules`` role's scope: the config and dependencies classes (note section 5)."""

    def test_snapshot_records_the_rules_role(self):
        """``snapshot --role rules`` is accepted and records the role."""
        report = self.report_of(self.project.run("snapshot", "--role", "rules"), 0, "snapshot")
        self.assertEqual((report["roles"], report["head"]), (["rules"], self.base))

    def test_rule_pr_changes_pass(self):
        """The rules pair, the config, the project workflow, and a manifest with a new
        baseline line under ``--allow-dependency``: passed and staged."""
        changes = {
            RULES: self.project.read(RULES) + "\n",
            RULES_ZH: self.project.read(RULES_ZH) + "\n",
            CONFIG: SNAPSHOT_CONFIG + "\n[limits]\nsource_lines = 800\n",
            WORKFLOW: (self.project.read(WORKFLOW)
                       + "            - scripts/new.py  # baseline: P01\n"),
            PYPROJECT: HEAD_PYPROJECT + '"src/wordcount/new.py" = ["EM102"]  # baseline: P01\n',
            ".github/workflows/lint.yml": "name: lint\n",
        }
        report = self.run_role("rules", changes, allow=[PYPROJECT])
        self.assert_passes(report, changes)
        self.assertEqual(sorted((c["path"], c["class"]) for c in report["changed"]),
                         sorted([(RULES, "config"), (RULES_ZH, "config"), (CONFIG, "config"),
                                 (WORKFLOW, "config"), (PYPROJECT, "dependencies"),
                                 (".github/workflows/lint.yml", "config")]))

    def test_rule_row_then_check_run(self):
        """``rule-row`` under ``snapshot --role rules``, plus a baseline line: staged."""
        snap = self.report_of(self.project.run("snapshot", "--role", "rules"), 0, "snapshot")
        self.report_of(self.project.run("rule-row", "--id", "P04", "--rule-file",
                                        rule_file(self.project, rule_data()), "--date", DAY),
                       0, "rule-row")
        self.project.write(PYPROJECT, HEAD_PYPROJECT
                           + '"src/wordcount/new.py" = ["E722"]  # baseline: P04\n')
        report = self.report_of(self.project.run("check-run", "--run", snap["run"],
                                                 "--allow-dependency", PYPROJECT), 0, "check-run")
        self.assert_passes(report, [RULES, RULES_ZH, PYPROJECT])

    def test_new_baseline_lines_need_allow_dependency(self):
        """A manifest that gains a line is a dependency change for the ``rules`` role too."""
        report = self.run_role("rules", {PYPROJECT: HEAD_PYPROJECT + '"x.py" = ["E722"]  '
                                                                     '# baseline: P04\n'}, code=1)
        self.assert_problems(report, [("dependency", PYPROJECT)])

    def test_other_classes_are_out_of_scope(self):
        """Planted bug "rules allowed to change docs": documents, source, and tests are scope
        problems, each with its undo step."""
        changes = {ARCHITECTURE: "# changed\n", "README.md": "# changed\n",
                   "docs/notes.md": "# Notes\n", "src/wordcount/count.py": "x = 1\n",
                   "tests/test_count.py": "x = 1\n"}
        report = self.run_role("rules", changes, code=1)
        self.assert_problems(report, [("scope", path) for path in changes])
        restore = "git restore --source=HEAD --staged --worktree -- "
        self.assertEqual(report["undo"], sorted([
            {"path": ARCHITECTURE, "action": "restore", "command": restore + ARCHITECTURE},
            {"path": "README.md", "action": "restore", "command": restore + "README.md"},
            {"path": "docs/notes.md", "action": "delete", "command": "rm -f -- docs/notes.md"},
            {"path": "src/wordcount/count.py", "action": "restore",
             "command": restore + "src/wordcount/count.py"},
            {"path": "tests/test_count.py", "action": "restore",
             "command": restore + "tests/test_count.py"}], key=lambda e: e["path"]))

    def test_rules_table_with_a_document_is_stopped(self):
        """Planted bug "rules allowed to change docs": the rules pair with an architecture
        change: the architecture is the one problem, and nothing is staged."""
        changes = {RULES: self.project.read(RULES) + "\n", ARCHITECTURE: "# changed\n"}
        report = self.run_role("rules", changes, code=1)
        self.assert_problems(report, [("scope", ARCHITECTURE)])

    def test_hooks_log_holds_the_main_sessions_lines(self):
        """A ``rules`` run reports the lines without an agent ID since the snapshot."""
        snap = self.report_of(self.project.run("snapshot", "--role", "rules"), 0, "snapshot")
        main = hooks_line(shifted(snap["time"], 3), None, None, path=ARCHITECTURE)
        folder = self.project.git_dir() / "troy-mode"
        folder.mkdir(parents=True, exist_ok=True)
        lines = [hooks_line(shifted(snap["time"], -60), None, None), main,
                 hooks_line(shifted(snap["time"], 5), "tstack:troy-developer", "a1")]
        (folder / "hooks.log").write_bytes("".join(json.dumps(line) + "\n"
                                                   for line in lines).encode("utf-8"))
        report = self.report_of(self.project.run("check-run", "--run", snap["run"]), 0)
        self.assertEqual(report["hooks_log"], [main])


class BaselineRuleTests(RunCase):
    """Deleting whole baseline lines from a dependency file needs no ``--allow-dependency``."""

    def test_developer_removes_a_baseline_line_with_its_fix(self):
        """DV5's cleanup: the source file and its baseline line, staged together."""
        changes = {"src/wordcount/count.py": '"""Count, fixed."""\n',
                   PYPROJECT: without(HEAD_PYPROJECT, COUNT_LINE)}
        report = self.run_role("developer", changes)
        self.assert_passes(report, changes)
        self.assertEqual(sorted((c["path"], c["class"]) for c in report["changed"]),
                         [(PYPROJECT, "dependencies"), ("src/wordcount/count.py", "source")])

    def test_each_role_with_the_dependencies_class(self):
        """Two lines by the Developer, a test's line by the Test Engineer, every baseline line
        by ``rules``, and a line of a rule with no row (P07): each passes."""
        cases = {
            "developer, two lines": ("developer", {
                PYPROJECT: without(HEAD_PYPROJECT, COUNT_LINE, REPORT_LINE)}),
            "test engineer": ("test-engineer", {
                "tests/test_count.py": '"""Tests, fixed."""\n',
                PYPROJECT: without(HEAD_PYPROJECT, TEST_LINE)}),
            "rules, every line": ("rules", {
                PYPROJECT: without(HEAD_PYPROJECT, COUNT_LINE, REPORT_LINE, TEST_LINE,
                                   P07_LINE),
                REQUIREMENTS_TXT: "click==8.1.7\n"}),
            "developer, P07": ("developer", {PYPROJECT: without(HEAD_PYPROJECT, P07_LINE)}),
        }
        reports = parallel(lambda name: fresh_run(*cases[name]), list(cases))
        for name, out in zip(cases, reports):
            with self.subTest(case=name):
                self.assert_passes(self.report_of(out, 0, "check-run"), cases[name][1])

    def test_deletion_with_an_added_line_is_a_dependency_change(self):
        """Planted bug "deletion that also adds a line": a deleted baseline line and an added
        dependency, or a changed line, are dependency problems."""
        cases = {
            "added dependency": without(HEAD_PYPROJECT, COUNT_LINE).replace(
                'version = "0.1.0"\n', 'version = "0.1.0"\ndependencies = ["click"]\n'),
            "changed line": without(HEAD_PYPROJECT, COUNT_LINE).replace('"0.1.0"', '"0.2.0"'),
            "changed baseline line": HEAD_PYPROJECT.replace(COUNT_LINE, COUNT_LINE.replace(
                "EM102", "EM101")),
            "moved baseline line": without(HEAD_PYPROJECT, COUNT_LINE) + COUNT_LINE,
        }
        reports = parallel(lambda name: fresh_run("developer", {PYPROJECT: cases[name]}),
                           list(cases))
        for name, out in zip(cases, reports):
            with self.subTest(case=name):
                self.assert_problems(self.report_of(out, 1, "check-run"),
                                     [("dependency", PYPROJECT)])

    def test_deletion_with_a_new_baseline_line_is_a_dependency_change(self):
        """Planted bug "deletion that also adds a line": one baseline line swapped for another."""
        text = HEAD_PYPROJECT.replace(COUNT_LINE,
                                      '"src/wordcount/new.py" = ["EM102"]  # baseline: P01\n')
        report = self.run_role("developer", {PYPROJECT: text}, code=1)
        self.assert_problems(report, [("dependency", PYPROJECT)])

    def test_lines_that_are_not_baseline_lines(self):
        """Deleting a rule's config line, a line without the colon, or ``baseline: P1``."""
        cases = {
            "config line": HEAD_PYPROJECT.replace('extend-select = ["EM102", "T20"]\n', ""),
            "no colon": without(HEAD_PYPROJECT, NO_COLON_LINE),
            "P1": without(HEAD_PYPROJECT, SHORT_ID_LINE),
            "baseline and config line": without(HEAD_PYPROJECT, COUNT_LINE).replace(
                'extend-select = ["EM102", "T20"]\n', ""),
        }
        reports = parallel(lambda name: fresh_run("developer", {PYPROJECT: cases[name]}),
                           list(cases))
        for name, out in zip(cases, reports):
            with self.subTest(case=name):
                self.assert_problems(self.report_of(out, 1, "check-run"),
                                     [("dependency", PYPROJECT)])

    def test_line_endings_new_and_deleted_files(self):
        """A baseline line deleted from a file turned CRLF, a new dependency file, and a
        deleted one are dependency problems."""
        cases = {
            "crlf": ({PYPROJECT: crlf(without(HEAD_PYPROJECT, COUNT_LINE))}, PYPROJECT),
            "deleted file": ({REQUIREMENTS_TXT: None}, REQUIREMENTS_TXT),
        }
        reports = parallel(lambda name: fresh_run("developer", cases[name][0]), list(cases))
        for name, out in zip(cases, reports):
            with self.subTest(case=name):
                self.assert_problems(self.report_of(out, 1, "check-run"),
                                     [("dependency", cases[name][1])])
        report = self.run_new_dependency_file()
        self.assert_problems(report, [("dependency", "requirements-dev.txt")])

    def run_new_dependency_file(self) -> dict:
        """A dependency file that does not exist at the snapshot's head, holding only a
        baseline-like line; the config at HEAD names it."""
        self.project.commit("[rules] Name the dev requirements", {CONFIG: rules_config(
            dependencies=(PYPROJECT, REQUIREMENTS_TXT, "requirements-dev.txt"))})
        return self.run_role("developer", {"requirements-dev.txt": "# baseline: P01\n"}, code=1)

    def test_allowed_dependency_still_passes(self):
        """With ``--allow-dependency``, a deletion and an added line pass as before."""
        text = without(HEAD_PYPROJECT, COUNT_LINE) + 'dependencies = ["click"]\n'
        report = self.run_role("developer", {PYPROJECT: text}, allow=[PYPROJECT])
        self.assert_passes(report, [PYPROJECT])

    def test_role_without_the_class_gets_a_scope_problem(self):
        """The Architect deleting a baseline line: a scope problem, not a pass."""
        report = self.run_role("architect", {PYPROJECT: without(HEAD_PYPROJECT, COUNT_LINE)},
                               code=1)
        self.assert_problems(report, [("scope", PYPROJECT)])


def fresh_run(role: str, changes: dict):
    """In a new clone: snapshot for one role, write the changes, and run check-run.

    Args:
        role: The role.
        changes: Paths mapped to new content, None to delete.

    Returns:
        The check-run outcome, or the snapshot's when the snapshot failed.
    """
    project = Project([rules_step(extra=EXTRA)])
    snap = project.run("snapshot", "--role", role)
    if snap.code != 0 or not isinstance(snap.report, dict):
        return snap
    for rel, content in changes.items():
        if content is None:
            project.remove(rel)
        else:
            project.write(rel, content)
    return project.run("check-run", "--run", snap.report["run"])


if __name__ == "__main__":
    unittest.main()
