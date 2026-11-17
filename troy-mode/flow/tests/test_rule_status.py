"""Status in F09 (F09 design 3.2, 10.1; interface note sections 0, 2, and 6).

``status`` gains the ``rules`` key and the action ``cleanup``: a rule whose
newest change-log row says "Existing code: fixed by cleanup PRs." and whose
baseline lines remain on ``origin/main`` gets its next cleanup PR. It comes
after the open PRs, the setup steps, ``bug``, and ``release``, and before the
feature loop's next stage. An open PR of the rule flow is continued with
the rule's ID and its task.

Planted bugs of F09 design 10.2 caught here:

- "``cleanup`` given for 'fixed when touched'": ``CleanupTests.test_fixed_when_touched_gives_none``.
- "``cleanup`` given after the last baseline line is gone":
  ``CleanupTests.test_no_cleanup_once_the_baseline_is_gone`` and
  ``test_lines_outside_searched_files_do_not_count``.
"""

import unittest
from dataclasses import replace

from flow_helpers import (
    ALL_ISSUES_ARGS, ALL_PRS_ARGS, F01, F02, F03, FIVE, NEXT_KEYS, PROGRESS, RULES, Fakes,
    FlowCase, Project, bug_step, pr, progress_fields, run_engine, stage_step, stages,
    status_runs,
)
from rule_helpers import (
    DEFAULT_LOG, P01, P02, P03, PYPROJECT, PYPROJECT_CLEAN, PYPROJECT_TEXT, SEED_LOG,
    WORKFLOW, WORKFLOW_CLEAN, WORKFLOW_TEXT, added, default_entries, rule_entry, rules_step,
)

LIST_ARGS = ["pr", "list", "--state", "open", "--limit", "100", "--json",
             "number,title,headRefName,url"]
CLEANUP = dict(action="cleanup", item="P01", merged_by="f07")
STAGE_F01 = dict(action="stage", item="F01", stage=1, task="IF1", title=F01.title(1),
                 branch=F01.branch(1), merged_by="troy")
TOUCHED_LOG = (SEED_LOG, added("P01", "2.0", "2026-11-08", "when-touched"), *DEFAULT_LOG[2:])
P01_GONE = PYPROJECT_CLEAN
WORKFLOW_P02_ONLY = WORKFLOW_TEXT.split("      - name: P01")[0]
ADD_P04 = "[rules] Add P04, no bare except clauses"


def rule_pr(number: int, title: str, branch: str) -> dict:
    """An open PR of the rule flow."""
    return pr(number, title, branch)


class CleanupTests(FlowCase):
    """When ``cleanup`` is given, and for which rule (note section 6)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        both = (SEED_LOG, added("P01", "2.0", "2026-11-08", "when-touched"),
                added("P02", "3.0", "2026-11-08", "cleanup"),
                added("P03", "4.0", "2026-11-09", "cleanup"))
        p03_line = PYPROJECT_TEXT + '"src/wordcount/errors.py" = ["EM102"]  # baseline: P03\n'
        cls.outs = status_runs({
            "cleanup": ([rules_step()], []),
            "touched": ([rules_step(log=TOUCHED_LOG)], []),
            "gone": ([rules_step(extra={PYPROJECT: P01_GONE, WORKFLOW: WORKFLOW_P02_ONLY})], []),
            "outside": ([rules_step(extra={
                PYPROJECT: P01_GONE, WORKFLOW: WORKFLOW_P02_ONLY,
                "src/wordcount/count.py": '"""Count."""\n\nX = 1  # baseline: P01\n',
                "docs/notes.md": "# Notes\n\nbaseline: P01\n",
                ".troy-mode/notes.txt": "baseline: P01\n"})], []),
            "retired": ([rules_step((P01.retired("2026-11-10"), P02, P03))], []),
            "lowest": ([rules_step(log=both, extra={PYPROJECT: p03_line})], []),
            "only P03 left": ([rules_step(log=both, extra={PYPROJECT: p03_line,
                                                           WORKFLOW: WORKFLOW_CLEAN})], []),
            "no plan": ([rules_step(plans=False)], []),
            "no plan, touched": ([rules_step(log=TOUCHED_LOG, plans=False)], []),
            "seeded rules": ([rules_step((), (SEED_LOG,))], []),
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name], 0, "status")

    def test_cleanup_while_baseline_lines_remain(self):
        """P01 says "fixed by cleanup PRs" and has four baseline lines: ``cleanup`` of P01,
        and ``next`` keeps exactly F08's keys."""
        report = self.report("cleanup")
        self.assert_next(report, **CLEANUP)
        self.assertEqual(sorted(report["next"]), sorted(NEXT_KEYS))

    def test_rules_key_holds_every_p_row(self):
        """``rules``: P01, P02, and P03 with their choices and baseline entries (note 2)."""
        self.assertEqual(self.report("cleanup").get("rules"), default_entries())

    def test_fixed_when_touched_gives_none(self):
        """Planted bug "cleanup for when touched": P01 fixed when touched: F01's design next."""
        report = self.report("touched")
        self.assert_next(report, **STAGE_F01)
        self.assertEqual([(r["id"], r["choice"]) for r in report.get("rules") or []],
                         [("P01", "when-touched"), ("P02", "when-touched"),
                          ("P03", "when-touched")])

    def test_no_cleanup_once_the_baseline_is_gone(self):
        """Planted bug "cleanup after the last line": no P01 line left: F01's design next."""
        report = self.report("gone")
        self.assert_next(report, **STAGE_F01)
        self.assertEqual((report.get("rules") or [{}])[0],
                         rule_entry(P01, "cleanup", []))

    def test_lines_outside_searched_files_do_not_count(self):
        """``baseline: P01`` in source, a document, or ``.troy-mode/notes.txt`` is no baseline."""
        report = self.report("outside")
        self.assert_next(report, **STAGE_F01)
        self.assertEqual((report.get("rules") or [{}])[0]["baseline"], [])

    def test_retired_rule_gives_none(self):
        """A retired P01 keeps its baseline lines and its choice, and gets no cleanup."""
        report = self.report("retired")
        self.assert_next(report, **STAGE_F01)
        first = (report.get("rules") or [{}])[0]
        self.assertEqual((first.get("id"), first.get("retired"), first.get("choice")),
                         ("P01", True, "cleanup"))
        self.assertEqual(len(first.get("baseline", [])), 4)

    def test_lowest_rule_number_first(self):
        """P02 and P03 both say "cleanup PRs" with lines left: P02 first; then P03."""
        self.assert_next(self.report("lowest"), action="cleanup", item="P02", merged_by="f07")
        self.assert_next(self.report("only P03 left"), action="cleanup", item="P03",
                         merged_by="f07")

    def test_cleanup_comes_before_the_version_test_plan(self):
        """No version test plan: cleanup first; without a cleanup, TM7's plan."""
        self.assert_next(self.report("no plan"), **CLEANUP)
        self.assertEqual(self.report("no plan, touched")["next"]["action"], "version-test-plan")

    def test_no_p_row_means_empty_rules_and_no_cleanup(self):
        """The seeded table: ``rules`` is [] and F01's design is next."""
        report = self.report("seeded rules")
        self.assertEqual(report.get("rules"), [])
        self.assert_next(report, **STAGE_F01)


class RulesKeyTests(FlowCase):
    """``rules`` is [] without P rows on origin/main (note sections 0 and 6)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on a project with the flow tests' stub table and one without the file."""
        no_rules = rules_step(extra={RULES: None})
        stub = rules_step(extra={RULES: (
            '---\ntroy-doc: "rules"\nlang: "en"\nversion: "1.0"\n---\n\n# Rules\n\n'
            "| ID | Rule |\n| --- | --- |\n| R01 | One commit per PR. |\n")})
        cls.outs = status_runs({"no file": ([no_rules], []), "stub": ([stub], [])})

    def test_empty_rules(self):
        """No ``docs/rules.md``, or a table without P rows: ``rules`` is [] and no cleanup."""
        for name in ("no file", "stub"):
            with self.subTest(case=name):
                report = self.report_of(self.outs[name], 0, "status")
                self.assertIn("rules", report)
                self.assertEqual(report["rules"], [])
                self.assert_next(report, **STAGE_F01)


class OrderTests(FlowCase):
    """``cleanup`` after open PRs, ``bug``, and ``release``; before ``ask-approvals``."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        five = dict(features=FIVE)
        accepted = [rules_step(), *stages(F01, 6), *stages(F02, 6)]
        cls.outs = status_runs({
            "rules PR": ([rules_step()], [rule_pr(21, ADD_P04, "troy-mode/rule-p04")]),
            "change PR": ([rules_step()], [rule_pr(22, "[rules] Change P02, no pprint calls",
                                                   "troy-mode/rule-p02")]),
            "retire PR": ([rules_step()], [rule_pr(23, "[rules] Retire P03, file names in "
                                                       "errors", "troy-mode/rule-p03")]),
            "refactor PR": ([rules_step()], [rule_pr(24, "[refactor] Apply P01 to counting",
                                                     "troy-mode/p01-cleanup-1")]),
            "test-fix PR": ([rules_step()], [rule_pr(25, "[P01 test-fix] Apply P01 to tests",
                                                     "troy-mode/p01-cleanup-2")]),
            "architecture PR": ([rules_step()], [rule_pr(26, "[docs] Change the architecture "
                                                             "for P04", "troy-mode/p04-arch")]),
            "bug": ([rules_step(), bug_step("B14", "test", "Crash on empty history")], []),
            "release": (accepted, []),
            "ask": ([rules_step(**five), *stages(F01, 6), *stages(F02, 6), *stages(F03, 6)], []),
            "ask, touched": ([rules_step(log=TOUCHED_LOG, **five), *stages(F01, 6),
                              *stages(F02, 6), *stages(F03, 6)], []),
            "language": ([rules_step(lang=None)], []),
            "order problem": ([rules_step(order=["F02", "F01"])], []),
            "record approval": ([rules_step(), stage_step(F01, 1, design="0.4")], []),
            "all accepted": ([rules_step(features=(replace(F01, version="-"),
                                                   replace(F02, version="Later"))),
                              *stages(F01, 6), *stages(F02, 6)], []),
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name], 0, "status")

    def test_open_rules_prs_are_continued_first(self):
        """``[rules] Add``, ``Change``, and ``Retire`` PRs: continued, with the ID and no task."""
        cases = {"rules PR": (21, "P04", ADD_P04, "troy-mode/rule-p04"),
                 "change PR": (22, "P02", "[rules] Change P02, no pprint calls",
                               "troy-mode/rule-p02"),
                 "retire PR": (23, "P03", "[rules] Retire P03, file names in errors",
                               "troy-mode/rule-p03")}
        for name, (number, item, title, branch) in cases.items():
            with self.subTest(case=name):
                self.assert_next(self.report(name), action="continue-pr", pr=number, item=item,
                                 task=None, title=title, branch=branch, merged_by="f07")

    def test_cleanup_prs_are_continued_with_their_task(self):
        """A ``[refactor] Apply P01`` PR by DV5, a ``[P01 test-fix]`` PR by TE6, and the
        architecture PR by AR6."""
        cases = {"refactor PR": (24, "P01", "DV5", "[refactor] Apply P01 to counting",
                                 "troy-mode/p01-cleanup-1"),
                 "test-fix PR": (25, "P01", "TE6", "[P01 test-fix] Apply P01 to tests",
                                 "troy-mode/p01-cleanup-2"),
                 "architecture PR": (26, "P04", "AR6", "[docs] Change the architecture for P04",
                                     "troy-mode/p04-arch")}
        for name, (number, item, task, title, branch) in cases.items():
            with self.subTest(case=name):
                self.assert_next(self.report(name), action="continue-pr", pr=number, item=item,
                                 task=task, title=title, branch=branch, merged_by="f07")

    def test_bug_and_release_come_before_cleanup(self):
        """B14's PR A merged: its PR B first. Every v0.1 feature accepted: the release first."""
        bug = self.report("bug")["next"]
        self.assertEqual((bug["action"], bug["item"]), ("bug", "B14"))
        self.assertEqual(self.report("release")["next"]["action"], "release")

    def test_setup_steps_come_before_cleanup(self):
        """The language step, an order problem, and a design to record come first."""
        for name, action in (("language", "language"), ("order problem", "order-problem"),
                             ("record approval", "record-approval")):
            with self.subTest(case=name):
                self.assertEqual(self.report(name)["next"]["action"], action)

    def test_cleanup_comes_before_all_accepted(self):
        """Every feature accepted, none with a version: cleanup instead of ``all-accepted``."""
        self.assert_next(self.report("all accepted"), **CLEANUP)

    def test_cleanup_comes_before_ask_approvals(self):
        """The third feature accepted: cleanup first; without a cleanup, Troy is asked."""
        self.assert_next(self.report("ask"), **CLEANUP)
        self.assertEqual(self.report("ask, touched")["next"]["action"], "ask-approvals")


class OriginMainTests(FlowCase):
    """The rule state comes from origin/main; status makes no new gh call for the rules
    (note sections 0, 6); F15's two reads are its only additions (F15 note section 1)."""

    def test_branch_and_tree_changes_do_not_end_the_cleanup(self):
        """The baseline lines removed in a branch commit and in the tree: still ``cleanup``."""
        project = Project([rules_step()])
        project.commit("[refactor] Apply P01 to counting", {PYPROJECT: P01_GONE})
        project.write(WORKFLOW, WORKFLOW_P02_ONLY)
        fakes = Fakes()
        report = self.report_of(project.status(fakes=fakes), 0, "status")
        self.assert_next(report, **CLEANUP)
        self.assertEqual(report.get("rules"), default_entries())
        self.assertEqual(sorted(fakes.gh_argvs()),
                         sorted([LIST_ARGS, ALL_ISSUES_ARGS, ALL_PRS_ARGS]))


class ProgressTests(FlowCase):
    """The text report and the progress file name the rule (note section 6)."""

    def test_progress_and_text_report_name_the_rule(self):
        """Stage starts with ``none.``; Next action and the text report name P01."""
        project = Project([rules_step()])
        out = project.status("--write-progress", fakes=Fakes())
        self.assert_next(self.report_of(out, 0, "status"), **CLEANUP)
        fields = progress_fields(project.read(PROGRESS))
        self.assertTrue(fields["Stage"].startswith("none."), fields["Stage"])
        self.assertIn("P01", fields["Next action"])
        project.remove(PROGRESS)
        text = run_engine(["status", "--repo", project.root], project.tmp, Fakes())
        self.assert_exit(text, 0)
        self.assertIn("P01", text.stdout)


if __name__ == "__main__":
    unittest.main()
