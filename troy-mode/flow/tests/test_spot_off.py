"""An overturn turns spot checks off (F18 design 5.3, 7.4, 13.1 "Overturns"; part 2 contract 5).

While ``spot_checks`` is true, an ``Overturn: <link>`` comment on any issue turns spot checks
off when it is newer than the newest ``[rules] Set the features Troy approves`` commit on
origin/main and its link names a PR 1 or PR 2, or names no PR, or a PR not among those read.
Spot checks are then off-due: the report's ``spot.off_due`` names the oldest such comment,
every later PR 1 and PR 2 waits for Troy, and once no PR is open ``next`` is ``spot-off``:
the ``[rules]`` PR that turns them off, merged by F07.

Planted bugs of design 13.2 caught here:

- "spot checks left on after an overturn" (``off_due`` null, no ``spot-off``):
  ``OffDueTests.test_newer_overturn_turns_them_off`` and ``SpotOffTests``.
- "an overturn older than the newest ``[rules]`` commit turning spot checks off":
  ``TimeRuleTests.test_older_overturn_keeps_them_on`` and ``test_newest_answer_counts``.
- "an overturn of a PR 3 ruling turning them off": ``LinkRuleTests.test_pr3_link_keeps_them_on``.
- "``spot-off`` coming before an open PR": ``SpotOffTests.test_open_pr_comes_first``.
"""

import unittest

from flow_helpers import PROGRESS, base_step, progress_fields, stages
from spot_helpers import (
    APPROVALS_TITLE, ISSUE_LABELS, OFF_BRANCH, OLD_TIME, Case, SpotCase, all_listed,
    answer_step, chain, closed_idea, flow, gh_issue, issue_comment, issue_url, link_to,
    overturn, overturn_issue, progress_issue, pr_url, run_case, run_cases, spot_files,
    stage_numbers, stage_open, step_time,
)

SIX = chain(6)
F1, F2 = SIX[0], SIX[1]
ON, FALSE, ZERO = flow(1, True, 2), flow(1, False, 2), flow(0, True, 2)


def history(config: str = ON, *more) -> list:
    """F01 accepted (step 6), the answer (step 7), and F02's stages 1 to 3 (steps 8 to 10)."""
    return [base_step(spot_files(SIX, config)), *stages(F1, 6), answer_step(), *stages(F2, 3),
            *more]


MERGED = all_listed((), [*stage_numbers(F1, 6, 0), *stage_numbers(F2, 3, 60)])
ANSWER = 7


def case(issues, config: str = ON, steps=None, prs=(), extra=()) -> Case:
    """Status with the issues given, F02's next stage 4, and the merged PRs #1 to #6, #61 to #63."""
    kwargs = {"all_issues": list(issues), "labels": list(ISSUE_LABELS), "prs": list(prs),
              "all_prs": all_listed(prs) + MERGED}
    return Case(steps or history(config), kwargs, extra)


def turned(issue: int, link: str) -> dict:
    """The report's ``spot.off_due`` for six features."""
    return {"issue": issue, "overturn": link, "approves_first": 6}


def spot_value(on: bool, off_due=None, configured: bool = True) -> dict:
    """The report's ``spot`` with one approved feature, every 2: F03 and F05 sampled."""
    return {"on": on, "configured": configured, "every": 2, "approves_first": 1,
            "sample": ["F03", "F05"] if configured else [], "off_due": off_due}


ISSUE_LINK = issue_url(12) + "#issuecomment-5"
CASES = {
    "no overturn": case([]),
    "after the answer": case([overturn_issue(90, link_to(61), step_time(ANSWER, 3600))]),
    "before the answer": case([overturn_issue(90, link_to(61), step_time(ANSWER, -3600))]),
    "two answers, between": case([overturn_issue(90, link_to(61), step_time(9))],
                                 steps=history(ON, answer_step(2))),
    "two answers, after": case([overturn_issue(90, link_to(61), step_time(11, 3600))],
                               steps=history(ON, answer_step(2))),
    "unreadable time": case([overturn_issue(90, link_to(61), "not a time")]),
    "no answer commit": case([overturn_issue(90, link_to(61), OLD_TIME)],
                             steps=[base_step(spot_files(SIX, ZERO)), *stages(F1, 6),
                                    *stages(F2, 3)]),
    "PR 1 link": case([overturn_issue(90, link_to(61))]),
    "PR 2 link": case([overturn_issue(90, link_to(62))]),
    "PR 3 link": case([overturn_issue(90, link_to(63))]),
    "PR 6 link": case([overturn_issue(90, link_to(6))]),
    "PR link at the end": case([overturn_issue(90, pr_url(61))]),
    "no PR in the link": case([overturn_issue(90, ISSUE_LINK)]),
    "PR not read": case([overturn_issue(90, link_to(77))]),
    "progress issue": case([progress_issue(9, F2, [issue_comment(9, 901, overturn(link_to(61)))])]),
    "bug issue": case([gh_issue(70, "Crash on empty input", "It crashes.", ("bug",),
                                [issue_comment(70, 701, overturn(link_to(62)))], "CLOSED",
                                "COMPLETED")]),
    "oldest named": case([
        closed_idea(91, [issue_comment(91, 911, overturn(link_to(61)), "2026-11-22T08:00:00Z")]),
        closed_idea(92, [issue_comment(92, 921, overturn(link_to(62)), "2026-11-21T09:00:00Z")]),
        closed_idea(93, [issue_comment(93, 931, overturn(link_to(63)), "2026-11-20T08:00:00Z")])]),
    "spot checks false": case([overturn_issue(90, link_to(61))], config=FALSE),
    "open PR": case([overturn_issue(90, link_to(61))], prs=[stage_open(64, F2, 4)]),
}


class OffCase(SpotCase):
    """Runs every case once, side by side."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case."""
        if not OffCase.outs:
            OffCase.outs = run_cases(CASES)

    def assert_on(self, name: str) -> None:
        """Spot checks stay on, and F02's stage 4 is next, merged by F07."""
        self.assertEqual(self.spot(name), spot_value(True))
        self.assert_stage4(name)

    def assert_stage4(self, name: str) -> None:
        """``next`` is F02's stage 4, merged by F07."""
        self.assert_next(self.report(name), action="stage", item="F02", stage=4, task="TE1",
                         title=F2.title(4), branch=F2.branch(4), merged_by="f07")

    def assert_off(self, name: str, issue: int, link: str) -> None:
        """Spot checks are off-due, naming the issue and the link."""
        self.assertEqual(self.spot(name), spot_value(False, turned(issue, link)))


class OffDueTests(OffCase):
    """``spot.off_due`` and ``spot.on`` (contract 3 and 5)."""

    def test_no_overturn_keeps_them_on(self):
        """No overturn: on, ``off_due`` null."""
        self.assert_on("no overturn")

    def test_newer_overturn_turns_them_off(self):
        """Planted bug "spot checks left on after an overturn": an overturn of F02's PR 1,
        newer than the answer: off-due, naming the issue and the link."""
        self.assert_off("after the answer", 90, link_to(61))

    def test_oldest_counting_overturn_is_named(self):
        """Three overturns: the PR 3 one, oldest, does not count; of the two that do, the
        older (#92) is named."""
        self.assert_off("oldest named", 92, link_to(62))

    def test_any_issue_counts(self):
        """An overturn on a progress issue, or on a closed bug issue, counts too."""
        self.assert_off("progress issue", 9, link_to(61))
        self.assert_off("bug issue", 70, link_to(62))

    def test_spot_checks_false_ignore_overturns(self):
        """``spot_checks = false``: an overturn changes nothing, and ``next`` is the stage."""
        self.assertEqual(self.spot("spot checks false"), spot_value(False, None, False))
        self.assert_stage4("spot checks false")


class TimeRuleTests(OffCase):
    """The overturn must be newer than the newest ``[rules] Set the features Troy approves``."""

    def test_older_overturn_keeps_them_on(self):
        """Planted bug "an overturn older than the newest [rules] commit": an hour before the
        answer: still on."""
        self.assert_on("before the answer")

    def test_newest_answer_counts(self):
        """Planted bug "an overturn older than the newest [rules] commit": two answers, the
        overturn between them: still on; after the second: off-due."""
        self.assertEqual(self.spot("two answers, between"), spot_value(True))
        self.assert_off("two answers, after", 90, link_to(61))

    def test_unreadable_time_counts(self):
        """A ``createdAt`` that cannot be read counts."""
        self.assert_off("unreadable time", 90, link_to(61))

    def test_no_answer_commit_counts(self):
        """No ``[rules] Set the features Troy approves`` commit: even an old overturn counts."""
        self.assertEqual(self.spot("no answer commit"),
                         {"on": False, "configured": True, "every": 2, "approves_first": 0,
                          "sample": ["F02", "F04", "F06"], "off_due": turned(90, link_to(61))})


class LinkRuleTests(OffCase):
    """The link names a PR 1 or PR 2, no PR, or a PR not read (contract 5, rule 3)."""

    def test_pr1_and_pr2_links_turn_them_off(self):
        """Links to F02's PR 1 and PR 2, also a PR link with nothing after the number."""
        self.assert_off("PR 1 link", 90, link_to(61))
        self.assert_off("PR 2 link", 90, link_to(62))
        self.assert_off("PR link at the end", 90, pr_url(61))

    def test_pr3_link_keeps_them_on(self):
        """Planted bug "an overturn of a PR 3 ruling turning them off": still on."""
        self.assert_on("PR 3 link")

    def test_number_is_read_whole(self):
        """``/pull/6#...`` names F01's PR 6 (#6), not #61 or #62: still on."""
        self.assert_on("PR 6 link")

    def test_link_without_a_pr_or_with_an_unknown_pr_counts(self):
        """A link to an issue comment, or to a PR not among those read: off-due."""
        self.assert_off("no PR in the link", 90, ISSUE_LINK)
        self.assert_off("PR not read", 90, link_to(77))


class SpotOffTests(OffCase):
    """``next.action`` ``spot-off`` (contract 5)."""

    def test_spot_off_is_next(self):
        """Planted bug "no ``spot-off``": off-due with no open PR: the ``[rules]`` PR on
        ``troy-mode/spot-checks-off``, merged by F07, naming the overturn."""
        for name, issue, link in (("after the answer", 90, link_to(61)),
                                  ("no PR in the link", 90, ISSUE_LINK),
                                  ("progress issue", 9, link_to(61))):
            with self.subTest(case=name):
                self.assert_next(self.report(name), action="spot-off", title=APPROVALS_TITLE,
                                 branch=OFF_BRANCH, merged_by="f07",
                                 overturn={"issue": issue, "ruling": link})

    def test_open_pr_comes_first(self):
        """Planted bug "``spot-off`` coming before an open PR": F02's PR 4 is continued."""
        self.assert_next(self.report("open PR"), action="continue-pr", pr=64, item="F02",
                         stage=4, task="TE1", title=F2.title(4), branch=F2.branch(4),
                         merged_by="f07")
        self.assertEqual(self.spot("open PR"), spot_value(False, turned(90, link_to(61))))

    def test_progress_file_text(self):
        """The progress file's Next action: the overturn, the PR, and the count to set."""
        out, _, project = run_case(case([overturn_issue(90, link_to(61))],
                                        extra=("--write-progress",)))
        self.report_of(out, 0, "status")
        self.assertEqual(progress_fields(project.read(PROGRESS)).get("Next action"),
                         "An overturn turned spot checks off: open [rules] Set the features "
                         "Troy approves with spot_checks = false and troy_approves_first = 6, "
                         "and merge it.")


if __name__ == "__main__":
    unittest.main()
