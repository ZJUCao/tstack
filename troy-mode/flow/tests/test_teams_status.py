"""Status with teams (F20 design 3.5, 3.6, 3.8, 3.9, 3.12, 8.1; part 2 contract P2).

Written from F20 design version 1.3 and the part 2 contract before the code exists.
Each case clones a bare origin, makes team worktrees by hand (as ``team start``
does), writes ``<common git folder>/troy-mode/plan.json`` in the contract's shape,
writes role records into a team worktree's git folder, and runs ``status --json``
in the home checkout with a fake gh that also serves PR descriptions.

The project has six features: F01 Count words, F02 Count lines (hard on F01), F03
Count characters (soft on F01), F04 Report totals (hard on F02), F05 Watch folders,
and F06 Sort output. With F01 accepted, F02, F03, F05, and F06 are dependency-ready.

The coordinator's corrections to the contract apply: next entries key their kind as
``action`` and carry every key of F07's next entry (``plan`` and ``team-start`` add
``items``); a feature with a merged stage and no team worktree is under way in the
home checkout and stays out of ``may_start`` and ``needs_plan``; and the home
``next`` is replaced only where today's rule gives a stage 1 or a team feature's
entry, so a home feature at stage 2 or later keeps its ``stage`` entry.

Planted bugs caught here:

- ``may_start`` ignoring an ``after F08 1/6`` order (design 8.2):
  ``MayStartTests.test_unmet_design_order_holds_a_feature``.
- An ``after 6/6`` order ignored: ``MayStartTests.test_acceptance_order``.
- The home ``next`` still giving a team feature's stage:
  ``HomeNextTests.test_team_features_stage_is_not_the_homes`` and
  ``test_team_features_open_pr_is_not_the_homes``.
- A home feature under way not continued:
  ``HomeNextTests.test_home_feature_under_way_behind_a_team_is_continued``.
- ``waiting`` not sorted by holds: ``WaitingTests.test_waiting_sorted_by_holds``.
- ``held`` ignoring the Affects line: ``HeldTests.test_change_holds_only_the_teams_it_names``
  and ``MayStartTests.test_open_change_holds_the_features_it_affects``.
- A team's open PR or its running record read from another team or the home
  checkout: ``TeamEntryTests``.
- Teams mode keys filled outside teams mode: ``OutsideTeamsTests``.
"""

import unittest

from flow_helpers import (
    F01, F02, F03, F05, TWO, Project, base_files, base_step, comments, parallel, pr, same_path,
    stage_pr, stages,
)
from teams2_helpers import (
    F06, SIX, TeamFakes, TeamsCase, add_team, change_pr, git_dir_of, stamp, write_plan,
    write_record,
)

BASE = base_step(base_files(SIX))
A = (BASE, *stages(F01, 6))
B = (*A, *stages(F02, 2), *stages(F05, 1))
B3 = (*B, stages(F02, 3)[-1])
C = (*A, *stages(F02, 5))
C6 = (*A, *stages(F02, 6))
NONE_ACCEPTED = (BASE,)
OUT = (base_step(base_files(TWO)), *stages(F01, 2))
OUT_NEW = (base_step(base_files(TWO)),)
ALL_READY = ["F02", "F03", "F05", "F06"]
WAIT = ("Architect review, round 1: approved\n\nNone", "Waiting for Troy: approve this PR")
TEST_FIX = "[F05 test-fix] Wrong expected count in F05-T01"


def case(steps, teams=(), plan=None, orders=(), prs=(), by_pr=None, records=()):
    """One status case: a clone of the steps, its teams, plan, records, and the fake PRs.

    Args:
        steps: The history of origin/main.
        teams: The features whose worktrees are made, in that order.
        plan: The IDs with a feature line in plan.json, or None for no plan.json.
        orders: The plan's ``(feature, after, stage)`` orders.
        prs: The open PRs, with ``body`` where the test gives one.
        by_pr: PR number mapped to its comments.
        records: ``(team, agent ID, stopped)`` role records in a team's git folder.

    Returns:
        The case's settings, for ``run_case``.
    """
    return {"steps": steps, "teams": tuple(teams), "plan": plan, "orders": tuple(orders),
            "prs": list(prs), "by_pr": dict(by_pr or {}), "records": tuple(records)}


def run_case(spec: dict) -> tuple:
    """Builds the case's clone and runs ``status --json`` in its home checkout.

    Returns:
        ``(project, outcome, trees)``, trees mapping each team's ID to its worktree.
    """
    project = Project(spec["steps"])
    trees = {item: add_team(project, item) for item in spec["teams"]}
    if spec["plan"] is not None:
        write_plan(project, spec["plan"], spec["orders"])
    for item, agent, stopped in spec["records"]:
        write_record(git_dir_of(trees[item]), agent, "developer", stamp(-120),
                     stopped=stamp(-60) if stopped else None, worktree=trees[item])
    fakes = TeamFakes(spec["prs"], spec["by_pr"])
    return project, project.run("status", fakes=fakes), trees


CASES = {
    "no plan": case(A),
    "full plan": case(A, plan=ALL_READY),
    "plan without F06": case(A, plan=["F02", "F03", "F05"]),
    "design order": case(A, plan=ALL_READY, orders=[("F03", "F02", 1)]),
    "change": case(A, plan=ALL_READY, prs=[change_pr(60, "Count blank lines", ["F02", "F06"])]),
    "change without affects": case(A, plan=ALL_READY,
                                   prs=[change_pr(60, "Count blank lines", None)]),
    "two teams": case(A, teams=["F05", "F02"], plan=ALL_READY, orders=[("F03", "F02", 1)]),
    "all teams": case(A, teams=["F06", "F02", "F05", "F03"], plan=ALL_READY),
    "home under way": case(B, plan=["F03", "F06"]),
    "home under way, no plan": case(B),
    "acceptance order": case(C, teams=["F02"], plan=ALL_READY, orders=[("F03", "F02", 6)]),
    "acceptance order met": case(C6, teams=["F02"], plan=["F03", "F05", "F06"],
                                 orders=[("F03", "F02", 6)]),
    "teams under way": case(B, teams=["F05", "F02"], plan=ALL_READY, prs=[stage_pr(52, F02, 3)],
                            records=[("F05", "a-dev", False), ("F05", "c-done", True)]),
    "plan hold": case(B, teams=["F02", "F05"], plan=ALL_READY, orders=[("F05", "F02", 3)]),
    "plan hold met": case(B3, teams=["F02", "F05"], plan=ALL_READY, orders=[("F05", "F02", 3)]),
    "change hold": case(B, teams=["F02", "F05"], plan=ALL_READY,
                        prs=[stage_pr(52, F02, 3),
                             change_pr(60, "Count blank lines", ["F02", "F05"])]),
    "change hold other": case(B, teams=["F02", "F05"], plan=ALL_READY,
                              prs=[change_pr(60, "Count blank lines", ["F03"])]),
    "waiting": case(NONE_ACCEPTED, teams=["F06", "F01", "F05"], plan=["F01", "F05", "F06"],
                    orders=[("F06", "F05", 6)],
                    prs=[pr(39, TEST_FIX, "troy-mode/f05-test-fix"), stage_pr(40, F06, 1),
                         stage_pr(41, F05, 1), stage_pr(42, F01, 1),
                         pr(46, "[docs] Fix a typo in the README", "troy-mode/readme")],
                    by_pr={39: comments(*WAIT), 40: comments(*WAIT), 41: comments(*WAIT),
                           42: comments(*WAIT)}),
    "outside": case(OUT),
    "outside, waiting": case(OUT_NEW, prs=[stage_pr(41, F01, 1)], by_pr={41: comments(*WAIT)}),
    "one team": case(OUT, teams=["F01"]),
    "home under way behind a team": case((*A, *stages(F03, 2)), teams=["F02"], plan=ALL_READY),
}
_RESULTS: dict = {}


def results() -> dict:
    """Runs every case once, side by side, on first use."""
    if not _RESULTS:
        names = list(CASES)
        _RESULTS.update(zip(names, parallel(run_case, [CASES[n] for n in names], workers=6)))
    return _RESULTS


class StatusCase(TeamsCase):
    """Reads the shared case results. It has no tests of its own."""

    def report(self, name: str) -> dict:
        """The case's status report, which must exit 0."""
        return self.report_of(results()[name][1], 0, "status")

    def trees(self, name: str) -> dict:
        """The case's team worktrees."""
        return results()[name][2]

    def lists(self, name: str) -> tuple:
        """The case's ``may_start`` and ``needs_plan``."""
        report = self.report(name)
        return self.need(report, "may_start"), self.need(report, "needs_plan")


class MayStartTests(StatusCase):
    """``may_start`` and ``needs_plan`` (design 3.5; contract P2)."""

    def test_no_plan_needs_a_plan_for_every_ready_feature(self):
        """No plan.json: every ready feature without a team needs a plan; none may start."""
        self.assertEqual(([], ALL_READY), self.lists("no plan"))

    def test_full_plan_lets_every_ready_feature_start(self):
        """A feature line for each ready feature and no orders: all may start, in order."""
        self.assertEqual((ALL_READY, []), self.lists("full plan"))

    def test_feature_without_a_line_needs_a_plan(self):
        """F06 has no feature line: it needs a plan and may not start."""
        self.assertEqual((["F02", "F03", "F05"], ["F06"]), self.lists("plan without F06"))

    def test_unmet_design_order_holds_a_feature(self):
        """``F03 after F02 1/6`` while F02's design has not merged: F03 may not start.

        Planted bug caught: may_start ignoring an ``after F08 1/6`` order (8.2).
        """
        self.assertEqual((["F02", "F05", "F06"], []), self.lists("design order"))

    def test_acceptance_order(self):
        """``F03 after F02 6/6``: F03 waits while F02 is at stage 6, and may start once F02
        is accepted. F04, ready then, has no feature line and needs a plan."""
        self.assertEqual((["F05", "F06"], []), self.lists("acceptance order"))
        self.assertEqual((["F03", "F05", "F06"], ["F04"]), self.lists("acceptance order met"))

    def test_open_change_holds_the_features_it_affects(self):
        """An open change PR whose ``Affects:`` line names F02 and F06: they may not start.

        Planted bug caught: the Affects line ignored.
        """
        self.assertEqual((["F03", "F05"], []), self.lists("change"))
        self.assertEqual((ALL_READY, []), self.lists("change without affects"))

    def test_team_features_are_left_out(self):
        """Features with a team worktree are in neither list."""
        self.assertEqual((["F06"], []), self.lists("two teams"))
        self.assertEqual(([], []), self.lists("all teams"))

    def test_features_under_way_at_home_are_left_out(self):
        """F02 and F05 have merged stages and no team: in neither list, with or without a plan."""
        self.assertEqual((["F03", "F06"], []), self.lists("home under way"))
        self.assertEqual(([], ["F03", "F06"]), self.lists("home under way, no plan"))


class HomeNextTests(StatusCase):
    """The home checkout's ``next`` in teams mode (contract P2)."""

    def test_plan_when_a_feature_needs_one(self):
        """``needs_plan`` not empty: ``{"action": "plan", "items": needs_plan}``."""
        self.assert_entry(self.report("no plan")["next"], "plan", items=ALL_READY)
        self.assert_entry(self.report("plan without F06")["next"], "plan", items=["F06"])

    def test_team_start_when_features_may_start(self):
        """Every ready feature planned: ``{"action": "team-start", "items": may_start}``."""
        self.assert_entry(self.report("full plan")["next"], "team-start", items=ALL_READY)
        self.assert_entry(self.report("design order")["next"], "team-start",
                          items=["F02", "F05", "F06"])

    def test_teams_when_nothing_may_start(self):
        """Every ready feature has a team: ``{"action": "teams"}``."""
        self.assert_entry(self.report("all teams")["next"], "teams")

    def test_team_features_stage_is_not_the_homes(self):
        """Today's rule would give F02's stage 1, but F02 has a team: ``team-start`` F06.

        Planted bug caught: the home next still giving a team feature's stage.
        """
        self.assert_entry(self.report("two teams")["next"], "team-start", items=["F06"])

    def test_team_features_open_pr_is_not_the_homes(self):
        """F02's team has PR #52 open: the home's next is neither it nor F02's stage.

        Planted bug caught: the home next still giving a team feature's stage.
        """
        nxt = self.report("teams under way")["next"]
        self.assertNotEqual(52, nxt.get("pr"), nxt)
        self.assertNotEqual("F02", nxt.get("item"), nxt)
        self.assert_entry(nxt, "team-start", items=["F03", "F06"])

    def test_plan_before_team_start(self):
        """With F04 needing a plan and F03 free: ``plan`` with F04."""
        self.assert_entry(self.report("acceptance order met")["next"], "plan", items=["F04"])

    def test_home_pr_is_continued_as_today(self):
        """An open change PR is the home checkout's own: ``continue-pr`` #60, as today."""
        self.assert_entry(self.report("change")["next"], "continue-pr", pr=60)

    def test_home_feature_under_way_keeps_its_stage(self):
        """F02 at stage 3 in the home checkout: its ``stage`` entry, as today."""
        for name in ("home under way", "home under way, no plan"):
            with self.subTest(case=name):
                self.assert_entry(self.report(name)["next"], "stage", item="F02", stage=3,
                                  task="DV1", title=F02.title(3), branch=F02.branch(3),
                                  merged_by="f07")

    def test_home_feature_under_way_behind_a_team_is_continued(self):
        """F02, first in the order, has a team; F03 has 2/6 merged and no team: the home's
        next is F03's stage 3, even though F05 and F06 may start.

        Planted bug caught: a home feature under way not continued.
        """
        report = self.report("home under way behind a team")
        self.assertEqual(["F05", "F06"], self.need(report, "may_start"))
        self.assert_entry(report["next"], "stage", item="F03", stage=3, task="DV1",
                          title=F03.title(3), branch=F03.branch(3))

    def test_one_team_is_teams_mode(self):
        """Only F01 is ready, but it has a team: teams mode, and the home waits (``teams``)."""
        report = self.report("one team")
        self.assertEqual(["F01"], self.team_ids(report))
        self.assertEqual(([], []), self.lists("one team"))
        self.assert_entry(report["next"], "teams")


class TeamEntryTests(StatusCase):
    """``teams``: one entry per team worktree, ordered by ID (contract P2)."""

    def test_teams_are_ordered_by_id(self):
        """Worktrees made F05 then F02, and F06, F02, F05, F03: listed by ID."""
        self.assertEqual(["F02", "F05"], self.team_ids(self.report("teams under way")))
        self.assertEqual(["F02", "F03", "F05", "F06"], self.team_ids(self.report("all teams")))

    def test_team_with_an_open_pr(self):
        """F02: its worktree, stage 3, PR #52, nothing running, not held, and continue-pr."""
        team = self.team(self.report("teams under way"), "F02")
        self.assertTrue(same_path(team.get("worktree"), self.trees("teams under way")["F02"]),
                        team)
        self.assertEqual((3, 52, [], None),
                         (team.get("stage"), team.get("pr"), team.get("running"),
                          team.get("held")), team)
        self.assert_entry(team.get("next"), "continue-pr", pr=52, title=F02.title(3),
                          branch=F02.branch(3), item="F02", stage=3, task="DV1",
                          merged_by="f07", rounds=0, attempts=0)

    def test_team_with_a_new_stage_and_a_running_role(self):
        """F05: stage 2, no PR, its open record running (not the stopped one), next TM1."""
        team = self.team(self.report("teams under way"), "F05")
        self.assertEqual((2, None, ["a-dev"], None),
                         (team.get("stage"), team.get("pr"), team.get("running"),
                          team.get("held")), team)
        self.assert_entry(team.get("next"), "stage", item="F05", stage=2, task="TM1",
                          title=F05.title(2), branch=F05.branch(2), merged_by="f07")

    def test_team_without_a_merged_stage(self):
        """F02 just started: stage 1, IF1, merged by Troy (one of the first three)."""
        team = self.team(self.report("two teams"), "F02")
        self.assertEqual((1, None, []), (team.get("stage"), team.get("pr"), team.get("running")))
        self.assert_entry(team.get("next"), "stage", item="F02", stage=1, task="IF1",
                          title=F02.title(1), branch=F02.branch(1), merged_by="troy")

    def test_accepted_team_ends(self):
        """F02 accepted with its worktree still there: stage null, next ``team-end``."""
        team = self.team(self.report("acceptance order met"), "F02")
        self.assertIsNone(team.get("stage"), team)
        self.assert_entry(team.get("next"), "team-end", item="F02")

    def test_lowest_open_pr_of_the_feature(self):
        """F05 has its test fix #39 and its design #41 open: ``pr`` is 39; F01's is 42."""
        report = self.report("waiting")
        self.assertEqual(39, self.team(report, "F05").get("pr"))
        self.assertEqual(42, self.team(report, "F01").get("pr"))
        self.assertEqual(40, self.team(report, "F06").get("pr"))


class HeldTests(StatusCase):
    """``held``: ``change``, ``plan``, or null (contract P2)."""

    def test_unmet_order_holds_the_next_stage(self):
        """``F05 after F02 3/6`` and F02's mock not merged: F05's next stage is held by the plan."""
        report = self.report("plan hold")
        self.assertEqual("plan", self.team(report, "F05").get("held"))
        self.assertIsNone(self.team(report, "F02").get("held"))

    def test_met_order_holds_nothing(self):
        """F02's 3/6 merged: F05 is not held."""
        self.assertIsNone(self.team(self.report("plan hold met"), "F05").get("held"))

    def test_change_holds_a_new_stage(self):
        """An open change naming F02 and F05: F05 (next is a new stage) is held by the change,
        F02 (its PR #52 is open) is not."""
        report = self.report("change hold")
        self.assertEqual("change", self.team(report, "F05").get("held"))
        self.assertIsNone(self.team(report, "F02").get("held"))

    def test_change_holds_only_the_teams_it_names(self):
        """An open change whose Affects line names F03 only: neither team is held.

        Planted bug caught: ``held`` ignoring the Affects line.
        """
        report = self.report("change hold other")
        for item in ("F02", "F05"):
            with self.subTest(team=item):
                self.assertIsNone(self.team(report, item).get("held"))


class WaitingTests(StatusCase):
    """``waiting``: each PR waiting for Troy, with what it holds up (design 3.8; P2)."""

    def waiting(self) -> list:
        """The waiting case's ``waiting``, each with its holds sorted."""
        found = self.need(self.report("waiting"), "waiting")
        self.assertIsInstance(found, list, found)
        return [(w.get("pr"), w.get("item"), sorted(w.get("holds") or []), w.get("title"))
                for w in found]

    def test_waiting_sorted_by_holds(self):
        """F01's #42 holds F02 and F03; F05's #39 and #41 hold F06 (an order); F06's #40
        holds nothing. Most holds first, then by PR number; #46 does not wait.

        Planted bug caught: ``waiting`` not sorted by holds.
        """
        self.assertEqual([
            (42, "F01", ["F02", "F03"], F01.title(1)),
            (39, "F05", ["F06"], TEST_FIX),
            (41, "F05", ["F06"], F05.title(1)),
            (40, "F06", [], F06.title(1)),
        ], self.waiting())


class OutsideTeamsTests(StatusCase):
    """Outside teams mode the new keys are empty lists and the rest is as today (P2)."""

    def test_new_keys_are_empty(self):
        """One ready feature and no team worktree: ``teams``, ``may_start``, ``needs_plan``,
        and ``waiting`` are empty, also with a PR waiting for Troy."""
        for name in ("outside", "outside, waiting"):
            report = self.report(name)
            for key in ("teams", "may_start", "needs_plan", "waiting"):
                with self.subTest(case=name, key=key):
                    self.assertEqual([], self.need(report, key))

    def test_next_is_as_today(self):
        """F01's stage 3, and the waiting PR #41 continued, as today."""
        self.assert_entry(self.report("outside")["next"], "stage", item="F01", stage=3,
                          task="DV1", title=F01.title(3), branch=F01.branch(3), merged_by="f07")
        self.assert_entry(self.report("outside, waiting")["next"], "continue-pr", pr=41,
                          item="F01", stage=1, task="IF1")
        self.assertIsNotNone(self.report("outside, waiting")["waiting_on_troy"])

    def test_status_writes_no_plan(self):
        """status reads plan.json and never writes one."""
        project = results()["no plan"][0]
        self.assertFalse((project.root / ".git" / "troy-mode" / "plan.json").exists())


if __name__ == "__main__":
    unittest.main()
