"""Plan group (F20 design 3.4, 4, 8.1; part 2 contract P1): ``troy_flow.py plan``.

Written from F20 design version 1.3 and the part 2 contract before the code exists.
Each test writes an AR7 report to a file outside the clone and runs ``plan --report
<file> --repo <clone> --json``. The project has five features: F01 accepted, so the
batch (every dependency-ready feature) is F02 (hard on F01), F03 (soft on F01), and
F05; F04 (hard on F02) is not ready. The architecture on origin/main has a module
table under ``## 3.`` with the modules counter, cli, watcher, and report.

Where the design and the contract differ, the contract holds: design 3.4 says the
plan check wants an order for "every overlap of modules or interfaces between
running features", while the contract (and design 3.4's own "Features that only
share a module may run at once") asks an order only for a shared interface.

Planted bugs caught here:

- The plan accepted with an unordered interface overlap (design 8.2):
  ``ProblemTests.test_shared_interface_without_an_order``.
- A module overlap demanding an order: ``AcceptTests.test_shared_module_needs_no_order``.
- A missing batch feature accepted: ``ProblemTests.test_missing_batch_feature``.
- A bad line ignored: ``ProblemTests.test_bad_lines``.
- A cycle accepted: ``ProblemTests.test_cycles``.
- plan.json written despite a problem: ``WriteTests.test_problem_writes_nothing`` and
  ``test_problem_keeps_the_older_plan``, and every ``ProblemTests`` case.
- The plan kept in a team worktree's own git folder:
  ``WriteTests.test_team_worktree_writes_the_common_plan``.
"""

import json
import unittest

from flow_helpers import (
    ARCHITECTURE, F01, F02, FIVE, Fakes, Project, base_files, base_step, new_dir, run_engine,
    stages,
)
from teams2_helpers import (
    TeamsCase, add_team, architecture_with_modules, common_git, git_dir_of, plan_path,
)

WITH_TABLE = (base_step(base_files(FIVE, extra={ARCHITECTURE: architecture_with_modules()})),
              *stages(F01, 6))
WITHOUT_TABLE = (base_step(base_files(FIVE)), *stages(F01, 6))
# F01 accepted and F02 under way in the home checkout (stage 2 merged): still in the batch.
UNDER_WAY = (*WITH_TABLE, *stages(F02, 2))
GOOD = ("F02 modules: counter; interfaces: count_lines; documents: none",
        "F03 modules: counter, cli; interfaces: count_chars, chars_option; documents: architecture",
        "F05 modules: watcher; interfaces: none; documents: none",
        "F05 after F02 1/6")
GOOD_FEATURES = {
    "F02": {"modules": ["counter"], "interfaces": ["count_lines"], "documents": []},
    "F03": {"modules": ["counter", "cli"], "interfaces": ["count_chars", "chars_option"],
            "documents": ["architecture"]},
    "F05": {"modules": ["watcher"], "interfaces": [], "documents": []},
}
GOOD_ORDERS = [{"feature": "F05", "after": "F02", "stage": 1}]
F02_LINE, F03_LINE, F05_LINE = GOOD[:3]


def report_text(*blocks, before: str = "", fence: str = "```", info: str = "text") -> str:
    """An Architect's AR7 report in the shape of the agent file's Report section.

    Args:
        *blocks: Each a list of lines for one fenced block in Summary, in order.
        before: Text placed before the report's fields, such as an earlier block.
        fence: The fence, three backticks or three tildes.
        info: The fences' info string.

    Returns:
        The report.
    """
    parts = [before, "Role: Architect", "Task: AR7, v0.1", "Result: done", "Changed files: None",
             "Checks: None", "Summary: The batch's plan:", ""]
    for lines in blocks:
        parts += [f"{fence}{info}", *lines, fence, ""]
    parts += ["Findings: None", "Question: None", "For Troy: None", ""]
    return "\n".join(parts)


class PlanCase(TeamsCase):
    """Runs ``plan`` and reads its report. It has no tests of its own."""

    def plan(self, project: Project, text: str, repo=None):
        """Writes the report to a new file outside the clone and runs ``plan`` on it."""
        folder = new_dir("ar7")
        path = folder / "ar7-report.md"
        path.write_bytes(text.encode("utf-8"))
        args = ["plan", "--report", path, "--repo", repo or project.root, "--json"]
        return run_engine(args, project.tmp, Fakes(fail=True))

    def plan_report(self, out, code: int) -> dict:
        """Asserts the exit code and the report's keys (contract P1) and returns it."""
        report = self.report_of(out, code, "plan")
        for key in ("batch", "plan"):
            self.need(report, key)
        return report

    def refused(self, project: Project, text: str) -> dict:
        """Runs ``plan`` on a plan with a problem: exit 1, and no plan.json written."""
        report = self.plan_report(self.plan(project, text), 1)
        self.assertNotEqual([], report["problems"])
        self.assertFalse(plan_path(project).exists(), "plan.json written despite a problem")
        return report


class AcceptTests(PlanCase):
    """A plan that passes: exit 0, the report, and plan.json (contract P1)."""

    @classmethod
    def setUpClass(cls):
        """One clone with the module table; the good plan."""
        cls.project = Project(WITH_TABLE)

    def setUp(self):
        """Every test starts with no plan.json."""
        if plan_path(self.project).exists():
            plan_path(self.project).unlink()

    def test_good_plan_is_kept_in_the_common_git_folder(self):
        """plan.json holds origin/main's commit, the features, and the orders, exactly."""
        report = self.plan_report(self.plan(self.project, report_text(GOOD)), 0)
        self.assertEqual([], report["problems"])
        data = json.loads(plan_path(self.project).read_text(encoding="utf-8"))
        self.assertEqual({"commit": self.project.git("rev-parse", "origin/main").strip(),
                          "features": GOOD_FEATURES, "orders": GOOD_ORDERS}, data)

    def test_report_names_the_batch_and_the_parsed_plan(self):
        """``batch`` is the ready features in the requirements' order; ``plan`` the parse."""
        report = self.plan_report(self.plan(self.project, report_text(GOOD)), 0)
        self.assertEqual(["F02", "F03", "F05"], report["batch"])
        self.assertIsInstance(report["plan"], dict, report["plan"])
        self.assertEqual(GOOD_FEATURES, report["plan"].get("features"))
        self.assertEqual(GOOD_ORDERS, report["plan"].get("orders"))

    def test_shared_module_needs_no_order(self):
        """F02 and F03 both name module counter, with no order between them: accepted.

        Planted bug caught: a module overlap demanding an order.
        """
        lines = [F02_LINE, F03_LINE, F05_LINE]
        report = self.plan_report(self.plan(self.project, report_text(lines)), 0)
        self.assertEqual([], report["problems"])
        self.assertEqual([], json.loads(plan_path(self.project).read_text("utf-8"))["orders"])

    def test_tilde_fence_with_any_info_string_and_blank_lines(self):
        """A ``~~~plan`` fence, blank lines inside it skipped, and lines in any order."""
        lines = ["", GOOD[3], "", F05_LINE, F03_LINE, "", F02_LINE, ""]
        text = report_text(lines, fence="~~~", info="plan")
        self.plan_report(self.plan(self.project, text), 0)
        data = json.loads(plan_path(self.project).read_text(encoding="utf-8"))
        self.assertEqual(GOOD_FEATURES, data["features"])
        self.assertEqual(GOOD_ORDERS, data["orders"])

    def test_first_block_with_a_plan_line_is_the_plan(self):
        """A block without a plan line is skipped; a later second plan block is not read."""
        other = ["F02 modules: report; interfaces: totals; documents: none", F03_LINE, F05_LINE]
        text = report_text(["Result of the check: no overlap found."], GOOD, other, info="")
        self.plan_report(self.plan(self.project, text), 0)
        data = json.loads(plan_path(self.project).read_text(encoding="utf-8"))
        self.assertEqual(GOOD_FEATURES, data["features"])

    def test_order_after_acceptance_stage(self):
        """``F03 after F02 6/6`` is an order with stage 6."""
        lines = [F02_LINE, F03_LINE, F05_LINE, "F03 after F02 6/6"]
        self.plan_report(self.plan(self.project, report_text(lines)), 0)
        data = json.loads(plan_path(self.project).read_text(encoding="utf-8"))
        self.assertEqual([{"feature": "F03", "after": "F02", "stage": 6}], data["orders"])

    def test_shared_interface_with_an_order_either_way(self):
        """F02 and F03 both name ``count``: an order in either direction lets the plan pass."""
        shared = ["F02 modules: counter; interfaces: count; documents: none",
                  "F03 modules: cli; interfaces: count; documents: none", F05_LINE]
        for order in ("F03 after F02 1/6", "F02 after F03 6/6"):
            with self.subTest(order=order):
                report = self.plan_report(self.plan(self.project,
                                                    report_text([*shared, order])), 0)
                self.assertEqual([], report["problems"])

    def test_text_output_keeps_the_exit_code(self):
        """Without ``--json`` the good plan still exits 0 and writes plan.json."""
        folder = new_dir("ar7")
        path = folder / "ar7-report.md"
        path.write_bytes(report_text(GOOD).encode("utf-8"))
        out = run_engine(["plan", "--report", path, "--repo", self.project.root],
                         self.project.tmp, Fakes(fail=True))
        self.assert_exit(out, 0)
        self.assertTrue(plan_path(self.project).exists())


class UnderWayTests(PlanCase):
    """The batch holds a feature under way in the home checkout (coordinator's P2 note)."""

    def test_feature_under_way_is_still_in_the_batch(self):
        """F02 with stage 2 merged and no team: still a batch feature, so a plan without it
        misses it, and a plan with it passes."""
        project = Project(UNDER_WAY)
        report = self.refused(project, report_text([F03_LINE, F05_LINE]))
        self.assertEqual(["missing"], self.kinds(report))
        self.assertIn("F02", self.message_of(report, "missing"))
        report = self.plan_report(self.plan(project, report_text(GOOD)), 0)
        self.assertEqual(["F02", "F03", "F05"], report["batch"])


class ProblemTests(PlanCase):
    """Plans that stop with a problem: exit 1 and nothing written (contract P1)."""

    @classmethod
    def setUpClass(cls):
        """One clone with the module table; each test's runs must leave no plan.json."""
        cls.project = Project(WITH_TABLE)

    def test_no_plan(self):
        """No fenced block, a block without a plan line, and plan lines outside a fence."""
        cases = {
            "no block": "Role: Architect\nTask: AR7, v0.1\nResult: done\nSummary: Done.\n",
            "no plan line": report_text(["Result: done", "Nothing to plan."]),
            "outside a fence": ("Role: Architect\nResult: done\nSummary:\n\n"
                                + "\n".join(GOOD) + "\n"),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self.assertEqual(["no-plan"], self.kinds(self.refused(self.project, text)))

    def test_bad_lines(self):
        """A line that is neither form: ``line``, its message quoting the line.

        Planted bug caught: a bad line ignored.
        """
        for bad in ("Plan for the batch:", "F05 modules watcher; interfaces: none; documents: none",
                    "F05 after F02", "F05 waits for F02 1/6"):
            with self.subTest(line=bad):
                report = self.refused(self.project, report_text([*GOOD, bad]))
                self.assertEqual(["line"], self.kinds(report))
                self.assertIn(bad, self.message_of(report, "line"))

    def test_missing_batch_feature(self):
        """A plan without F03's line: ``missing``, naming F03.

        Planted bug caught: a missing batch feature accepted.
        """
        report = self.refused(self.project, report_text([F02_LINE, F05_LINE, GOOD[3]]))
        self.assertEqual(["missing"], self.kinds(report))
        self.assertIn("F03", self.message_of(report, "missing"))

    def test_feature_line_of_a_feature_not_ready(self):
        """A line for F04 (its hard dependency F02 not accepted) or F01 (accepted): ``not-ready``."""
        for item, line in (("F04", "F04 modules: report; interfaces: totals; documents: none"),
                           ("F01", "F01 modules: counter; interfaces: words; documents: none")):
            with self.subTest(item=item):
                report = self.refused(self.project, report_text([*GOOD, line]))
                self.assertEqual(["not-ready"], self.kinds(report))
                self.assertIn(item, self.message_of(report, "not-ready"))

    def test_order_for_a_feature_not_ready(self):
        """``F04 after F02 1/6``: F04 is not dependency-ready, so ``not-ready`` names it."""
        report = self.refused(self.project, report_text([*GOOD, "F04 after F02 1/6"]))
        self.assertIn("not-ready", self.kinds(report))
        self.assertIn("F04", self.message_of(report, "not-ready"))

    def test_unknown_module(self):
        """Module parser is not in the module table on origin/main: ``module``, naming it."""
        lines = [F02_LINE, F03_LINE, "F05 modules: watcher, parser; interfaces: none; "
                 "documents: none"]
        report = self.refused(self.project, report_text(lines))
        self.assertEqual(["module"], self.kinds(report))
        self.assertIn("parser", self.message_of(report, "module"))

    def test_shared_interface_without_an_order(self):
        """F02 and F03 both name interface ``count`` and no order joins them: ``overlap``.

        Planted bug caught: the plan accepted with an unordered interface overlap (8.2).
        """
        lines = ["F02 modules: counter; interfaces: count; documents: none",
                 "F03 modules: cli; interfaces: count, chars_option; documents: none",
                 F05_LINE, "F05 after F02 1/6"]
        report = self.refused(self.project, report_text(lines))
        self.assertEqual(["overlap"], self.kinds(report))
        message = self.message_of(report, "overlap")
        for word in ("F02", "F03", "count"):
            self.assertIn(word, message)

    def test_order_whose_feature_has_no_line(self):
        """``F05 after F01 6/6`` and ``F05 after F09 1/6``: no feature line, ``order``."""
        for order in ("F05 after F01 6/6", "F05 after F09 1/6"):
            with self.subTest(order=order):
                report = self.refused(self.project, report_text([F02_LINE, F03_LINE, F05_LINE,
                                                                 order]))
                self.assertIn("order", self.kinds(report))

    def test_cycles(self):
        """Orders that make a cycle of two or of three features: ``order``.

        Planted bug caught: a cycle accepted.
        """
        cycles = {"two": ["F02 after F03 1/6", "F03 after F02 1/6"],
                  "three": ["F02 after F03 1/6", "F03 after F05 6/6", "F05 after F02 1/6"]}
        for name, orders in cycles.items():
            with self.subTest(cycle=name):
                report = self.refused(self.project, report_text([F02_LINE, F03_LINE, F05_LINE,
                                                                 *orders]))
                self.assertEqual(["order"], self.kinds(report))

    def test_every_problem_is_listed(self):
        """A bad line and a missing feature in one plan: both kinds."""
        report = self.refused(self.project, report_text([F02_LINE, F05_LINE, "Plan:"]))
        self.assertEqual(["line", "missing"], self.kinds(report))


class ModuleTableTests(PlanCase):
    """The module check is skipped when origin/main's architecture has no module table."""

    def test_no_module_table_skips_the_module_check(self):
        """Module parser passes when there is no table; the plan is kept."""
        project = Project(WITHOUT_TABLE)
        lines = [F02_LINE, F03_LINE, "F05 modules: watcher, parser; interfaces: none; "
                 "documents: none"]
        report = self.plan_report(self.plan(project, report_text(lines)), 0)
        self.assertEqual([], report["problems"])
        data = json.loads(plan_path(project).read_text(encoding="utf-8"))
        self.assertEqual(["watcher", "parser"], data["features"]["F05"]["modules"])

    def test_table_in_the_working_tree_only_does_not_count(self):
        """A module table written in the working tree, not on origin/main, is not read."""
        project = Project(WITHOUT_TABLE)
        project.write(ARCHITECTURE, architecture_with_modules())
        lines = [F02_LINE, F03_LINE, "F05 modules: watcher, parser; interfaces: none; "
                 "documents: none"]
        self.plan_report(self.plan(project, report_text(lines)), 0)


class WriteTests(PlanCase):
    """Where plan.json goes and when it changes (contract P1)."""

    def test_problem_writes_nothing(self):
        """No plan.json and no ``troy-mode`` plan file anywhere in the git folders.

        Planted bug caught: plan.json written despite a problem.
        """
        project = Project(WITH_TABLE)
        self.refused(project, report_text([F02_LINE, F05_LINE]))
        self.assertEqual([], sorted(p.name for p in common_git(project).rglob("plan.json")))

    def test_problem_keeps_the_older_plan(self):
        """A good plan, then a plan with a problem: plan.json keeps the good plan's bytes.

        Planted bug caught: plan.json written despite a problem.
        """
        project = Project(WITH_TABLE)
        self.plan_report(self.plan(project, report_text(GOOD)), 0)
        before = plan_path(project).read_bytes()
        bad = report_text([F02_LINE, F05_LINE, "F02 after F05 1/6", "F05 after F02 1/6"])
        self.plan_report(self.plan(project, bad), 1)
        self.assertEqual(before, plan_path(project).read_bytes())

    def test_good_plan_replaces_the_older_plan(self):
        """A second good plan replaces the first: its orders and features only."""
        project = Project(WITH_TABLE)
        self.plan_report(self.plan(project, report_text(GOOD)), 0)
        lines = [F02_LINE, "F03 modules: report; interfaces: totals; documents: none", F05_LINE,
                 "F03 after F05 6/6"]
        self.plan_report(self.plan(project, report_text(lines)), 0)
        data = json.loads(plan_path(project).read_text(encoding="utf-8"))
        self.assertEqual({"modules": ["report"], "interfaces": ["totals"], "documents": []},
                         data["features"]["F03"])
        self.assertEqual([{"feature": "F03", "after": "F05", "stage": 6}], data["orders"])

    def test_team_worktree_writes_the_common_plan(self):
        """``--repo <team worktree>``: plan.json in the common git folder, not the worktree's.

        Planted bug caught: the plan kept in a team worktree's own git folder.
        """
        project = Project(WITH_TABLE)
        tree = add_team(project, "F05")
        self.plan_report(self.plan(project, report_text(GOOD), repo=tree), 0)
        self.assertTrue(plan_path(project).is_file())
        self.assertFalse((git_dir_of(tree) / "troy-mode" / "plan.json").exists())
        data = json.loads(plan_path(project).read_text(encoding="utf-8"))
        self.assertEqual(project.git("rev-parse", "origin/main").strip(), data["commit"])

    def test_nothing_else_changes(self):
        """The working tree and HEAD do not change; no gh call is made."""
        project = Project(WITH_TABLE)
        fakes = Fakes(fail=True)
        head = project.head()
        folder = new_dir("ar7")
        path = folder / "r.md"
        path.write_bytes(report_text(GOOD).encode("utf-8"))
        out = run_engine(["plan", "--report", path, "--repo", project.root, "--json"],
                         project.tmp, fakes)
        self.plan_report(out, 0)
        self.assertEqual((head, []), (project.head(), project.status_lines()))
        self.assertEqual([], fakes.gh_calls())


if __name__ == "__main__":
    unittest.main()
