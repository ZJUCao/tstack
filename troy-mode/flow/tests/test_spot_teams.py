"""Spot checks with feature teams (F18 design 7.5, 9 F20, 13.1 "Spot checks"; contract 5).

A risky PR's wait stops its team like any wait, and each ``waiting`` entry gains ``risky``.
A sampled PR stops no team: nothing in ``teams[].held`` comes from a sample. An overturn
still holds its feature's team (``held`` ``overturn``). Each team's ``next`` carries
``spot`` and ``risky`` and its ``merged_by`` follows the table of contract 5; while spot
checks are off-due, the home checkout's ``next`` is ``spot-off``.
"""

import unittest

from flow_helpers import F01, F03, F05, Project, base_files, base_step, parallel, stages
from issues_helpers import ALL_LABELS
from spot_helpers import (
    APPROVALS_TITLE, OFF_BRANCH, OLD_TIME, SPOT_COMMENT, WAIT_W3, answer_step, arch_review, curl,
    flow, issue_comment, link_to, mark, open_pr, overturn, overturn_issue, progress_issue,
    stage_open, thread,
)
from teams2_helpers import SIX, TeamFakes, TeamsCase, add_team, write_plan

TEST_FIX = "[F02 test-fix] Wrong expected count in F02-T01"
STEPS = (base_step(base_files(SIX, config_extra=flow(1, True, 2))), *stages(F01, 6),
         answer_step(), *stages(F03, 1))
MERGED = [{"number": 10 + n, "title": F01.title(n)} for n in range(1, 7)] + [
    {"number": 31, "title": F03.title(1)}]
OPEN = [stage_open(55, F05, 1), open_pr(57, TEST_FIX, "troy-mode/f02-test-fix")]
COMMENTS = {55: thread(55, arch_review(1, "approved", "network access"), WAIT_W3),
            57: thread(57, "Test Manager review, round 1: approved\n\nNone", WAIT_W3),
            31: thread(31, arch_review(1), SPOT_COMMENT)}
ARCH_55 = [mark("architect", "network access", 55, curl(55, 0))]
CASES = {
    "on": {"prs": OPEN, "issues": []},
    "overturn": {"prs": OPEN, "issues": [progress_issue(13, F03, [
        issue_comment(13, 1301, overturn(curl(31, 3)), OLD_TIME)])]},
    "off-due": {"prs": [], "issues": [overturn_issue(90, link_to(31))]},
}


def run_team_case(spec: dict):
    """Teams for F02, F03, and F05, a plan for every ready feature, and status at home."""
    project = Project(STEPS)
    for item in ("F02", "F03", "F05"):
        add_team(project, item)
    write_plan(project, ["F02", "F03", "F05", "F06"])
    fakes = TeamFakes(spec["prs"], COMMENTS, merged=MERGED, all_issues=spec["issues"],
                      labels=list(ALL_LABELS))
    return project.run("status", fakes=fakes)


class TeamSpotTests(TeamsCase):
    """``waiting[].risky``, ``held``, and each team's ``next`` (contract 5)."""

    @classmethod
    def setUpClass(cls):
        """Runs every case, side by side."""
        names = list(CASES)
        cls.outs = dict(zip(names, parallel(run_team_case, [CASES[n] for n in names],
                                            workers=3)))

    def report(self, name: str) -> dict:
        """The case's report, exit 0."""
        return self.report_of(self.outs[name], 0, "status")

    def test_waiting_entries_carry_their_marks(self):
        """F05's PR 1 waits with the Architect's mark; F02's test fix waits with none."""
        found = {w.get("pr"): w.get("risky", "missing")
                 for w in self.need(self.report("on"), "waiting")}
        self.assertEqual(found, {55: ARCH_55, 57: []})

    def test_a_sample_holds_no_team(self):
        """F03, sampled, its PR 1 merged with the spot check comment: no team is held, and
        F03's team goes on to its test plan, merged by F07."""
        report = self.report("on")
        self.assertEqual([self.team(report, item).get("held") for item in ("F02", "F03", "F05")],
                         [None, None, None])
        self.assert_entry(self.team(report, "F03").get("next"), "stage", item="F03", stage=2,
                          task="TM1", title=F03.title(2), branch=F03.branch(2), merged_by="f07",
                          spot="sample", risky=[])

    def test_team_next_of_a_marked_pr(self):
        """F05's team: its marked PR 1, Troy's to merge, ``spot`` ``sample``."""
        self.assert_entry(self.team(self.report("on"), "F05").get("next"), "continue-pr",
                          pr=55, item="F05", stage=1, task="IF1", merged_by="troy",
                          spot="sample", risky=ARCH_55)

    def test_team_next_of_another_pr(self):
        """F02's team: its test fix, ``spot`` null and ``risky`` empty."""
        self.assert_entry(self.team(self.report("on"), "F02").get("next"), "continue-pr",
                          pr=57, item="F02", merged_by="f07", spot=None, risky=[])

    def test_overturn_still_holds_its_team(self):
        """An overturn on F03's issue, older than the answer: F03's team is held ``overturn``,
        and spot checks stay on."""
        report = self.report("overturn")
        self.assertEqual(self.team(report, "F03").get("held"), "overturn")
        self.assertIs((report.get("spot") or {}).get("on"), True)

    def test_off_due_teams(self):
        """Off-due with no PR open: the home's ``next`` is ``spot-off``, and each team's next
        PR 1 or PR 2 is Troy's to merge."""
        report = self.report("off-due")
        self.assert_entry(report["next"], "spot-off", title=APPROVALS_TITLE, branch=OFF_BRANCH,
                          merged_by="f07", overturn={"issue": 90, "ruling": link_to(31)},
                          spot=None, risky=[])
        self.assert_entry(self.team(report, "F02").get("next"), "stage", item="F02", stage=1,
                          merged_by="troy", spot=None, risky=[])
        self.assert_entry(self.team(report, "F03").get("next"), "stage", item="F03", stage=2,
                          merged_by="troy", spot=None, risky=[])


if __name__ == "__main__":
    unittest.main()
