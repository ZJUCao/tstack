"""Rulings at a review loop's round 3 (F18 design 5.1, 5.2, 13.1 "Rulings"; contract 3, 4, 6).

When round 3 of a review loop still ends in ``changes-requested``, ``status`` gives the
``ruling`` action: AR8, the Architect, for every loop except the Architect's own review,
where PM7, the Product Manager, rules. The ruling is a comment headed ``<Ruler> ruling,
round 3: <result>``; ``fix`` sends the author back once (``ruled-revision``), which is not a
round, and the ruler's check after it gives ``fixed`` or ``not fixed``. ``not fixed`` is
W7. A comment of Troy's that only looks like a ruling is Troy's comment. ``brief --task
AR8`` briefs the Architect wherever it rules.

Planted bugs of design 13.2 caught here:

- "a ruling started at round 2": ``RulingStatusTests.test_round_two_is_no_ruling``.
- "a ruling started when round 3 approved":
  ``RulingStatusTests.test_round_three_approved_is_no_ruling``.
- "AR8 given the Architect's own loop": ``RulingStatusTests.test_design_loop_is_ruled_by_pm7``
  and ``test_docs_design_update_is_ruled_by_pm7``.
- "the ruled revision counted as a round": ``RulingStatusTests.test_fixed_goes_on_to_the_merge``
  and ``test_ruled_revision_is_neither_a_round_nor_an_attempt``.
- "``not fixed`` merged (no ``escalate`` W7)": ``RulingStatusTests.test_not_fixed_escalates_w7``.
- "a Troy comment read as a ruling": ``RulingStatusTests.test_troys_comments_are_not_rulings``.
"""

import json
import unittest

from flow_helpers import (
    F01, F05, Fakes, FlowCase, Project, base_files, base_step, bug_step, fake_status_runs,
    parallel, pr, stage_pr, stages,
)
from stops_helpers import (
    BUG_A, BUG_TEST_FIX, DOCS_UPDATE, FIX_FINDINGS, FIXED_FINDINGS, MERGE_FINDINGS,
    NOT_FIXED_FINDINGS, REFACTOR, TEST_FIX, attempt, brief_project, escalation, finding,
    in_order, rules_project, ruling, task_field, three_rounds,
)
from teams2_helpers import SIX, TeamFakes, TeamsCase, add_team

H = {n: [base_step(), *stages(F01, n - 1)] for n in range(1, 6)}
BUG = [base_step(), bug_step("B12", "test", "Crash on empty history")]
BUG_FIX = "[B12 B/B fix] Crash on empty history"
CR, ARCH, TM, IF = "Code Reviewer", "Architect", "Test Manager", "Interface Designer"
AR8 = {"ruler": "Architect", "task": "AR8"}
PM7 = {"ruler": "Product Manager", "task": "PM7"}
FIX = ruling(ARCH, "fix", *FIX_FINDINGS)
FIXED = ruling(ARCH, "fixed", *FIXED_FINDINGS)
NOT_FIXED = ruling(ARCH, "not fixed", *NOT_FIXED_FINDINGS)
TROY_LOOKALIKES = ("ruling: merge", "Architect ruling: merge", "architect ruling, round 3: merge",
                   "Architect ruling, round 3: merge it", "Product Manager ruling, round 3 merge",
                   "See the Architect ruling, round 3: merge below.")


def tests_rounds(tm_last: str, cr_last: str) -> list:
    """PR 4's rounds: the Test Manager and the Code Reviewer in each of rounds 1 to 3."""
    tm, cr = three_rounds(TM, tm_last), three_rounds(CR, cr_last)
    return [tm[0], cr[0], tm[1], cr[1], tm[2], cr[2]]


def case(steps, number: int, title: str, branch: str, bodies) -> tuple:
    """One status case: an open PR and its comments, oldest first, one minute apart."""
    return steps, {"prs": [pr(number, title, branch)], "comments": {number: in_order(*bodies)}}


def stage_case(stage: int, bodies) -> tuple:
    """F01's stage PR #<40 + stage> open, with its comments."""
    item = stage_pr(40 + stage, F01, stage)
    return case(H[stage], item["number"], item["title"], item["headRefName"], bodies)


CASES = {
    "mock round 3": stage_case(3, three_rounds(CR)),
    "mock round 2": stage_case(3, three_rounds(CR)[:2]),
    "mock round 3 approved": stage_case(3, three_rounds(CR, "approved")),
    "design round 3": stage_case(1, three_rounds(ARCH)),
    "test plan round 3": stage_case(2, three_rounds(IF)),
    "tests, CR asks": stage_case(4, tests_rounds("approved", "changes-requested")),
    "tests, TM asks": stage_case(4, tests_rounds("changes-requested", "approved")),
    "impl round 3": stage_case(5, three_rounds(CR)),
    "test fix round 3": case(H[5], 46, TEST_FIX, "troy-mode/f01-test-fix",
                             tests_rounds("approved", "changes-requested")),
    "bug fix round 3": case(BUG, 47, BUG_FIX, "troy-mode/b12-fix", three_rounds(CR)),
    "docs round 3": case(H[3], 48, DOCS_UPDATE, "troy-mode/f01-docs", three_rounds(ARCH)),
    "merge": stage_case(3, [*three_rounds(CR), ruling(ARCH, "merge", *MERGE_FINDINGS)]),
    "fix": stage_case(3, [*three_rounds(CR), FIX]),
    "fix, attempt failed": stage_case(3, [*three_rounds(CR), FIX, attempt("Developer", 1)]),
    "fixed": stage_case(3, [*three_rounds(CR), FIX, FIXED]),
    "not fixed": stage_case(3, [*three_rounds(CR), FIX, NOT_FIXED]),
    "not fixed, escalated": stage_case(3, [*three_rounds(CR), FIX, NOT_FIXED, escalation(
        "the Developer's fix of the ruled findings still fails", "W7")]),
    "design merge": stage_case(1, [*three_rounds(ARCH),
                                   ruling("Product Manager", "merge", *MERGE_FINDINGS)]),
    "troy lookalikes": stage_case(3, [*three_rounds(CR), *TROY_LOOKALIKES]),
    "ruling before the round": stage_case(3, [*three_rounds(CR)[:2],
                                              ruling(ARCH, "merge", *MERGE_FINDINGS),
                                              three_rounds(CR)[2]]),
}


class RulingStatusTests(FlowCase):
    """``next`` and ``rulings`` for an open PR at round 3 (contract 4)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case, side by side."""
        cls.outs = fake_status_runs(CASES)

    def report(self, name: str) -> dict:
        """The case's report, exit 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def entry(self, name: str) -> dict:
        """The case's one open PR entry."""
        prs = self.report(name)["open_prs"]
        self.assertEqual(len(prs), 1, prs)
        return prs[0]

    def assert_stage_next(self, name: str, stage: int, **expected) -> None:
        """Asserts ``next`` for F01's stage PR, with the keys ``continue-pr`` fills."""
        self.assert_next(self.report(name), pr=40 + stage, item="F01", stage=stage,
                         title=F01.title(stage), branch=F01.branch(stage),
                         merged_by="troy" if stage <= 2 else "f07", **expected)

    def test_mock_loop_is_ruled_by_ar8(self):
        """Round 3 of the Code Reviewer ends in ``changes-requested``: ``ruling`` by AR8, with
        no result yet and the PR's three rounds."""
        self.assert_stage_next("mock round 3", 3, action="ruling", task="AR8", rounds=3,
                               ruling={**AR8, "result": None})

    def test_round_two_is_no_ruling(self):
        """Planted bug "a ruling started at round 2": two rounds asking for changes go on."""
        self.assert_stage_next("mock round 2", 3, action="continue-pr", task="DV1", rounds=2)

    def test_round_three_approved_is_no_ruling(self):
        """Planted bug "a ruling started when round 3 approved": the PR goes on, no ruling."""
        self.assert_stage_next("mock round 3 approved", 3, action="continue-pr", task="DV1",
                               rounds=3)

    def test_design_loop_is_ruled_by_pm7(self):
        """Planted bug "AR8 given the Architect's own loop": PR 1's Architect review at round
        3: PM7, the Product Manager, rules."""
        self.assert_stage_next("design round 3", 1, action="ruling", task="PM7", rounds=3,
                               ruling={**PM7, "result": None})

    def test_docs_design_update_is_ruled_by_pm7(self):
        """Planted bug "AR8 given the Architect's own loop": a ``[docs]`` design update
        reviewed by the Architect: PM7."""
        nxt = self.report("docs round 3")["next"]
        self.assertEqual((nxt["action"], nxt["pr"], nxt["task"], nxt.get("ruling"), nxt["rounds"]),
                         ("ruling", 48, "PM7", {**PM7, "result": None}, 3), json.dumps(nxt))

    def test_every_other_loop_is_ruled_by_ar8(self):
        """PR 2 (the Interface Designer's answers), PR 4 with either reviewer asking, PR 5, a
        test fix, and bug PR B: AR8."""
        for name, number in (("test plan round 3", 42), ("tests, CR asks", 44),
                             ("tests, TM asks", 44), ("impl round 3", 45),
                             ("test fix round 3", 46), ("bug fix round 3", 47)):
            with self.subTest(case=name):
                nxt = self.report(name)["next"]
                self.assertEqual((nxt["action"], nxt["pr"], nxt["task"], nxt.get("ruling"),
                                  nxt["rounds"]),
                                 ("ruling", number, "AR8", {**AR8, "result": None}, 3),
                                 json.dumps(nxt))

    def test_ruling_keeps_the_keys_of_continue_pr(self):
        """The test fix and bug PR B: item and merged_by as ``continue-pr`` gives them."""
        self.assert_next(self.report("test fix round 3"), action="ruling", pr=46, item="F01",
                         task="AR8", title=TEST_FIX, branch="troy-mode/f01-test-fix",
                         merged_by="f07", rounds=3, ruling={**AR8, "result": None})
        self.assert_next(self.report("bug fix round 3"), action="ruling", pr=47, item="B12",
                         task="AR8", title=BUG_FIX, branch="troy-mode/b12-fix", merged_by="f07",
                         rounds=3, ruling={**AR8, "result": None})

    def test_merge_goes_on_to_the_merge(self):
        """``Architect ruling, round 3: merge``: ``continue-pr``, the result ``merge``."""
        self.assert_stage_next("merge", 3, action="continue-pr", task="DV1", rounds=3,
                               ruling={**AR8, "result": "merge"})

    def test_fix_sends_the_author_back(self):
        """``fix``: ``ruled-revision`` with the author's task, DV1, and the PR's three rounds."""
        self.assert_stage_next("fix", 3, action="ruled-revision", task="DV1", rounds=3,
                               ruling={**AR8, "result": "fix"})

    def test_fixed_goes_on_to_the_merge(self):
        """Planted bug "the ruled revision counted as a round": ``fix`` then ``fixed``:
        ``continue-pr`` with ``fixed``, rounds still 3, no attempt."""
        self.assert_stage_next("fixed", 3, action="continue-pr", task="DV1", rounds=3,
                               attempts=0, ruling={**AR8, "result": "fixed"})

    def test_ruled_revision_is_neither_a_round_nor_an_attempt(self):
        """Planted bug "the ruled revision counted as a round": the revision's failed checks
        count one attempt, as always, and still no round; the action stays
        ``ruled-revision``."""
        self.assert_stage_next("fix, attempt failed", 3, action="ruled-revision", task="DV1",
                               rounds=3, attempts=1, ruling={**AR8, "result": "fix"})
        self.assertEqual((self.entry("fixed")["rounds"], self.entry("fixed")["attempts"]), (3, 0))

    def test_not_fixed_escalates_w7(self):
        """Planted bug "``not fixed`` merged": ``continue-pr`` with ``escalate`` W7."""
        self.assert_stage_next("not fixed", 3, action="continue-pr", task="DV1", rounds=3,
                               escalate="W7", ruling={**AR8, "result": "not fixed"})

    def test_escalation_after_not_fixed_ends_the_escalate(self):
        """An ``Escalation:`` after ``not fixed``: ``escalate`` null, and the PR waits."""
        self.assert_stage_next("not fixed, escalated", 3, action="continue-pr", task="DV1",
                               rounds=3, ruling={**AR8, "result": "not fixed"})
        self.assertIs(self.entry("not fixed, escalated")["waiting_for_troy"], True)

    def test_pm7_result(self):
        """``Product Manager ruling, round 3: merge`` on the design: ``continue-pr``, Troy
        merges, the ruling PM7's."""
        self.assert_stage_next("design merge", 1, action="continue-pr", task="IF1", rounds=3,
                               ruling={**PM7, "result": "merge"})

    def test_troys_comments_are_not_rulings(self):
        """Planted bug "a Troy comment read as a ruling": six comments that only look like
        rulings are Troy's; the ruling is still due."""
        self.assert_stage_next("troy lookalikes", 3, action="ruling", task="AR8", rounds=3,
                               ruling={**AR8, "result": None})
        entry = self.entry("troy lookalikes")
        self.assertEqual(entry["troy_comments"], list(TROY_LOOKALIKES))
        self.assertEqual(entry.get("rulings"), [])

    def test_ruling_before_the_round_three_review_does_not_count(self):
        """A ruling posted before round 3's review: the ruling is due again, with no result."""
        self.assert_stage_next("ruling before the round", 3, action="ruling", task="AR8",
                               rounds=3, ruling={**AR8, "result": None})

    def test_rulings_are_read_with_their_findings(self):
        """``rulings``: each ruling comment, oldest first, with its numbered findings."""
        self.assertEqual(self.entry("fixed").get("rulings"), [
            {"ruler": "Architect", "round": 3, "result": "fix",
             "findings": [finding(1, "fix", FIX_FINDINGS[0][1]),
                          finding(2, "does not block", FIX_FINDINGS[1][1])]},
            {"ruler": "Architect", "round": 3, "result": "fixed",
             "findings": [finding(1, "fixed", FIXED_FINDINGS[0][1])]}])
        self.assertEqual(self.entry("design merge").get("rulings"), [
            {"ruler": "Product Manager", "round": 3, "result": "merge",
             "findings": [finding(1, "does not block", MERGE_FINDINGS[0][1]),
                          finding(2, "does not block", MERGE_FINDINGS[1][1])]}])

    def test_rulings_are_troy_modes_own_comments(self):
        """A ruling is neither one of Troy's comments, nor a round, nor a wait; a PR with none
        has an empty ``rulings``."""
        entry = self.entry("not fixed")
        self.assertEqual((entry["troy_comments"], entry["rounds"], entry["attempts"],
                          entry["waiting_for_troy"]), ([], 3, 0, False))
        self.assertEqual(self.entry("mock round 3").get("rulings"), [])

    def test_no_ruling_leaves_the_key_null(self):
        """Without a ruling due or made, ``next.ruling`` is null (and present)."""
        self.assertIsNone(self.report("mock round 2")["next"].get("ruling", "missing"))


class TeamRulingTests(TeamsCase):
    """With feature teams, the team's ``next`` is the same ruling entry (contract 4)."""

    @classmethod
    def setUpClass(cls):
        """F05's team has its mock PR #53 at round 3, still asking for changes."""
        project = Project((base_step(base_files(SIX)), *stages(F01, 6), *stages(F05, 2)))
        add_team(project, "F05")
        prs = [stage_pr(53, F05, 3)]
        cls.out = project.run("status", fakes=TeamFakes(prs, {53: in_order(*three_rounds(CR))}))

    def test_team_next_is_the_ruling(self):
        """F05's team: ``ruling`` by AR8 on #53."""
        report = self.report_of(self.out, 0, "status")
        self.assert_entry(self.team(report, "F05").get("next"), "ruling", pr=53, item="F05",
                          stage=3, task="AR8", title=F05.title(3), rounds=3,
                          ruling={**AR8, "result": None})


AR8_ALLOWED = {
    "stage 2": ("briefs", "F03", None),
    "stage 3": ("briefs", "F04", None),
    "stage 4": ("briefs", "F05", None),
    "stage 5": ("briefs", "F01", None),
    "test fix": ("briefs", "F01", TEST_FIX),
    "bug PR A": ("briefs", "B13", BUG_A),
    "bug PR B": ("briefs", "B12", None),
    "bug test fix": ("briefs", "B12", BUG_TEST_FIX),
    "version tests": ("briefs", "v0.1", None),
    "cleanup": ("rules", "P01", REFACTOR),
}
AR8_REFUSED = {
    "stage 1": ("briefs", "F02", None),
    "stage 6": ("briefs", "F06", None),
    "docs side PR": ("briefs", "F01", DOCS_UPDATE),
    "accepted": ("briefs", "F07", None),
}
PROJECTS = {"briefs": brief_project, "rules": rules_project}


def run_brief(spec: tuple):
    """Runs ``brief --task <task> --item <item> [--title <title>] --json``.

    Args:
        spec: ``(task, clone name, item, title or None)``.

    Returns:
        The outcome.
    """
    task, name, item, title = spec
    args = ["brief", "--task", task, "--item", item] + (["--title", title] if title else [])
    return PROJECTS[name]().run(*args, fakes=Fakes())


class Ar8BriefTests(FlowCase):
    """``brief --task AR8`` where the Architect rules, and PM6 and PM7 (contract 6)."""

    @classmethod
    def setUpClass(cls):
        """Runs every AR8 brief, the CR1 brief beside it, and PM6 and PM7, side by side."""
        brief_project()
        rules_project()
        specs = {("AR8", name): ("AR8", *where) for name, where in
                 {**AR8_ALLOWED, **AR8_REFUSED}.items()}
        specs.update({("CR1", name): ("CR1", *where) for name, where in AR8_ALLOWED.items()
                      if name != "stage 2"})
        specs.update({(task, "pm"): (task, "briefs", "F01", None) for task in ("PM6", "PM7")})
        keys = list(specs)
        cls.outs = dict(zip(keys, parallel(run_brief, [specs[k] for k in keys])))

    def test_allowed_where_the_architect_rules(self):
        """Stages 2 to 5, a test fix, bug PRs A and B and a bug's test fix, the version tests,
        and a rule's cleanup PR: exit 0, the Architect's agent."""
        for name in AR8_ALLOWED:
            with self.subTest(case=name):
                report = self.report_of(self.outs[("AR8", name)], 0, "brief")
                self.assertEqual((report["task"], report["role"], report["agent"]),
                                 ("AR8", "architect", {"subagent_type": "tstack:troy-architect"}))

    def test_stage_title_as_for_cr1(self):
        """At a feature's stage, AR8's title is the stage's own, as CR1's is."""
        report = self.report_of(self.outs[("AR8", "stage 3")], 0, "brief")
        self.assertEqual((report["title"], report["stage"]), ("[F04 3/6 mock] Report totals", 3))

    def test_task_sentence(self):
        """The Task field starts ``AR8, rule on each open finding of round 3`` and ends
        ``Change no file.``"""
        for name in AR8_ALLOWED:
            with self.subTest(case=name):
                report = self.report_of(self.outs[("AR8", name)], 0, "brief")
                task = task_field(report["prompt"])
                self.assertTrue(task.startswith("AR8, rule on each open finding of round 3"), task)
                self.assertTrue(task.endswith("Change no file."), task)

    def test_read_first_as_for_cr1(self):
        """Read first is CR1's on the same item and PR."""
        for name in AR8_ALLOWED:
            if name == "stage 2":
                continue
            with self.subTest(case=name):
                ar8 = self.report_of(self.outs[("AR8", name)], 0, "brief")
                cr1 = self.report_of(self.outs[("CR1", name)], 0, "brief")
                self.assertEqual(ar8["read_first"], cr1["read_first"])

    def test_refused_where_the_architect_does_not_rule(self):
        """Stage 1 (PM7 rules the design), stage 6, a feature's ``[docs]`` side PR, and an
        accepted feature: exit 1 with a problem."""
        for name in AR8_REFUSED:
            with self.subTest(case=name):
                report = self.report_of(self.outs[("AR8", name)], 1, "brief")
                self.assertNotEqual(report["problems"], [])

    def test_pm6_and_pm7_run_in_the_main_session(self):
        """PM6 and PM7 are task IDs now, and like every PM task get no brief: exit 1."""
        for task in ("PM6", "PM7"):
            with self.subTest(task=task):
                report = self.report_of(self.outs[(task, "pm")], 1, "brief")
                self.assertNotEqual(report["problems"], [])


if __name__ == "__main__":
    unittest.main()
