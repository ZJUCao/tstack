"""Troy's overturn of a ruling (F18 design 5.3, 7.5, 13.1 "Overturns"; contract 3 and 7).

Troy overturns a ruling on the feature's progress issue or in chat; F07 answers on the
progress issue with ``Overturn: <link to the ruling>``, holds the feature, and its team,
after its current stage PR, carries the overturn out through the stage's side flow, and
posts ``Overturn carried out: <same link>`` once those PRs merge. ``status`` lists every
overturn in ``overturns``; one not carried out turns the feature's next stage into the
``overturn`` action, or holds its team with ``held`` ``overturn``. Both headings are
troy-mode's own, never Troy's comments.

Planted bug of design 13.2 caught here:

- "an overturn that does not hold the team": ``TeamOverturnTests.test_overturn_holds_its_team``
  and ``test_reasons_in_order``; without teams,
  ``OverturnStatusTests.test_overturn_holds_the_feature``.
"""

import unittest

from flow_helpers import (
    ANY, F01, F02, TWO, FlowCase, Project, base_files, base_step, parallel, pr, stage_pr, stages,
)
from issues_helpers import ALL_LABELS, progress_issue, project_files, status_runs_with
from stops_helpers import DOCS_UPDATE, carried_out, overturn, overturn_link
from teams2_helpers import SIX, TeamFakes, TeamsCase, add_team, change_pr, write_plan

LINK = overturn_link(41, 501)
LINK2 = overturn_link(43, 777)
OTHER = overturn_link(44, 900)
TROY_ASK = "The Code Reviewer was right on #41: keep its finding."
STEPS = [base_step(project_files(TWO)), *stages(F01, 1)]       # F01's stage 2 is next
STAGE2 = dict(item="F01", stage=2, task="TM1", title=F01.title(2), branch=F01.branch(2),
              merged_by="troy")


def issue_case(bodies, number: int = 7, item: str = "F01", **more) -> tuple:
    """Status with a progress issue whose comments are the bodies, oldest first."""
    return STEPS, {"labels": list(ALL_LABELS),
                   "all_issues": [progress_issue(number, item, comment_bodies=bodies)], **more}


CASES = {
    "held": issue_case([TROY_ASK, overturn(LINK)]),
    "done": issue_case([overturn(LINK), carried_out(LINK)]),
    "other link carried out": issue_case([overturn(LINK), carried_out(OTHER)]),
    "two overturns": issue_case([overturn(LINK), overturn(LINK2), carried_out(LINK)]),
    "side PR open": issue_case([overturn(LINK)], prs=[pr(50, DOCS_UPDATE, "troy-mode/f01-docs")]),
    "stage PR open": issue_case([overturn(LINK)], prs=[stage_pr(42, F01, 2)]),
    "other feature": issue_case([overturn(LINK2)], number=8, item="F02"),
    "unreadable": issue_case([overturn(LINK)],
                             fail_on=[(["issue", "list"], "HTTP 502: Bad Gateway")]),
}


class OverturnStatusTests(FlowCase):
    """``overturns`` and the ``overturn`` action without feature teams (contract 7)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case, side by side."""
        cls.outs = status_runs_with(CASES)

    def report(self, name: str) -> dict:
        """The case's report, exit 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def test_overturns_are_listed(self):
        """Each ``Overturn:`` comment, oldest first, with its item, issue, ruling, and whether a
        later ``Overturn carried out:`` names the same link."""
        self.assertEqual(self.report("held").get("overturns"),
                         [{"item": "F01", "issue": 7, "ruling": LINK, "done": False}])
        self.assertEqual(self.report("two overturns").get("overturns"), [
            {"item": "F01", "issue": 7, "ruling": LINK, "done": True},
            {"item": "F01", "issue": 7, "ruling": LINK2, "done": False}])
        self.assertEqual(self.report("other link carried out").get("overturns"),
                         [{"item": "F01", "issue": 7, "ruling": LINK, "done": False}])

    def test_overturn_holds_the_feature(self):
        """Planted bug "an overturn that does not hold" its feature: F01's next stage becomes
        the ``overturn`` action, with the progress issue and the ruling."""
        self.assert_next(self.report("held"), action="overturn", item="F01", issue=7,
                         overturn={"issue": 7, "ruling": LINK}, stage=ANY, task=ANY,
                         title=ANY, branch=ANY, merged_by=ANY)

    def test_newest_open_overturn_holds(self):
        """The first overturn carried out, the second not: the second holds F01."""
        self.assert_next(self.report("two overturns"), action="overturn", item="F01", issue=7,
                         overturn={"issue": 7, "ruling": LINK2}, stage=ANY, task=ANY,
                         title=ANY, branch=ANY, merged_by=ANY)

    def test_carried_out_lets_the_feature_go_on(self):
        """``Overturn carried out:`` with the same link: F01's stage 2 again, ``overturn``
        null; with another link the hold stays."""
        self.assert_next(self.report("done"), action="stage", issue=7, **STAGE2)
        self.assertEqual(self.report("done").get("overturns"),
                         [{"item": "F01", "issue": 7, "ruling": LINK, "done": True}])
        self.assertEqual(self.report("other link carried out")["next"]["action"], "overturn")

    def test_open_prs_come_first(self):
        """The ``[docs]`` side PR that carries the overturn out, or the feature's current stage
        PR, is continued first, as side PRs are; ``overturn`` is null there."""
        self.assert_next(self.report("side PR open"), action="continue-pr", pr=50,
                         title=DOCS_UPDATE, branch="troy-mode/f01-docs", merged_by="f07")
        self.assert_next(self.report("stage PR open"), action="continue-pr", pr=42, issue=7,
                         **STAGE2)

    def test_another_features_overturn_does_not_hold(self):
        """An overturn on F02's issue: listed, and F01 goes on with its stage."""
        report = self.report("other feature")
        self.assertEqual(report.get("overturns"),
                         [{"item": "F02", "issue": 8, "ruling": LINK2, "done": False}])
        self.assert_next(report, action="stage", **STAGE2)

    def test_unreadable_issues_give_no_overturns(self):
        """``gh issue list`` fails: ``overturns`` is empty, and nothing is held."""
        report = self.report("unreadable")
        self.assertEqual(report.get("overturns", "missing"), [])
        self.assert_next(report, action="stage", **STAGE2)

    def test_overturn_comment_is_not_troys(self):
        """``Overturn:`` is troy-mode's heading: Troy's comment before it is answered, so the
        issue has no Troy comment left to read."""
        found = [c for c in self.report("held")["issues"]["troy_comments"] if c["issue"] == 7]
        self.assertEqual(found, [])


def team_steps() -> tuple:
    """Six features, F01 accepted, F02's design and test plan merged."""
    return (base_step(base_files(SIX)), *stages(F01, 6), *stages(F02, 2))


def team_case(f02_bodies=(), f05_bodies=(), prs=(), orders=()) -> dict:
    """A team case: teams for F02 and F05, a plan for every ready feature, their issues."""
    issues = []
    if f02_bodies:
        issues.append(progress_issue(12, "F02", comment_bodies=list(f02_bodies)))
    if f05_bodies:
        issues.append(progress_issue(15, "F05", comment_bodies=list(f05_bodies)))
    return {"issues": issues, "prs": list(prs), "orders": list(orders)}


TEAM_CASES = {
    "held": team_case([overturn(LINK)]),
    "done": team_case([overturn(LINK), carried_out(LINK)]),
    "PR open": team_case([overturn(LINK)], prs=[stage_pr(52, F02, 3)]),
    "reasons": team_case([overturn(LINK)], [overturn(LINK2)],
                         prs=[change_pr(60, "Count blank lines", ["F02"])],
                         orders=[("F05", "F02", 3)]),
}


def run_team_case(spec: dict):
    """Builds the clone, the two teams, the plan, and runs status in the home checkout."""
    project = Project(team_steps())
    for item in ("F02", "F05"):
        add_team(project, item)
    write_plan(project, ["F02", "F03", "F05", "F06"], spec["orders"])
    fakes = TeamFakes(spec["prs"], {}, all_issues=spec["issues"], labels=list(ALL_LABELS))
    return project.run("status", fakes=fakes)


class TeamOverturnTests(TeamsCase):
    """With feature teams, an overturn holds its feature's team (design 7.5; contract 7)."""

    @classmethod
    def setUpClass(cls):
        """Runs every team case, side by side."""
        names = list(TEAM_CASES)
        cls.outs = dict(zip(names, parallel(run_team_case, [TEAM_CASES[n] for n in names],
                                            workers=4)))

    def report(self, name: str) -> dict:
        """The case's report, exit 0."""
        return self.report_of(self.outs[name], 0, "status")

    def test_overturn_holds_its_team(self):
        """Planted bug "an overturn that does not hold the team": F02's next stage is held by
        the overturn; F05's team is not held."""
        report = self.report("held")
        f02 = self.team(report, "F02")
        self.assertEqual((f02.get("held"), f02["next"]["action"], f02["next"]["stage"]),
                         ("overturn", "stage", 3))
        self.assertIsNone(f02["next"].get("overturn", "missing"))
        self.assertIsNone(self.team(report, "F05").get("held"))

    def test_carried_out_releases_the_team(self):
        """Carried out: F02's team is no longer held."""
        self.assertIsNone(self.team(self.report("done"), "F02").get("held"))

    def test_team_with_an_open_pr_is_not_held(self):
        """F02's current stage PR is open: its team goes on with it, not held."""
        f02 = self.team(self.report("PR open"), "F02")
        self.assertEqual((f02.get("held"), f02["next"]["action"], f02["next"]["pr"]),
                         (None, "continue-pr", 52))

    def test_reasons_in_order(self):
        """A change that affects F02 comes before F02's overturn; F05's overturn comes before
        its unmet plan order."""
        report = self.report("reasons")
        held = (self.team(report, "F02").get("held"), self.team(report, "F05").get("held"))
        self.assertEqual(held, ("change", "overturn"))


if __name__ == "__main__":
    unittest.main()
