"""``retro`` reports waits, rulings, premise attempts, and overturns (F18 design 4.2, 8, 9;
13.1 "Waits"; part 1 contract section 9).

The version's merged PRs carry every kind of F18 comment: waits for Troy with a ``Wait:``
line (W3 twice, W4, W7 twice, W10) and one older wait without it, a ``fix`` then
``fixed`` ruling, and three stages whose attempts reached 3: one fixed by the premise
attempt, one escalated from the premise attempt's report, and one whose fourth attempt
failed. F01's progress issue holds two overturns, one carried out; F02's, outside the
version, holds one that ``retro`` leaves out.

A wait's hours run from its comment to the next comment on the PR, or to the merge.
"""

import unittest
from dataclasses import replace

from flow_helpers import (
    F01, F02, Fakes, FlowCase, Project, accepted_plan_files, base_step, merged_pr, parallel,
    release_step, stages, subject_commits, version_tests_step,
)
from issues_helpers import ALL_LABELS, progress_issue, project_files
from stops_helpers import (
    FIX_FINDINGS, FIXED_FINDINGS, attempt, carried_out, escalation, finding, overturn,
    overturn_link, pr_url, review, ruling, three_rounds, timed, waiting, when,
)

F02V2 = replace(F02, version="v0.2")
STEPS = ([base_step(project_files((F01, F02V2)))] + stages(F01, 6)
         + [version_tests_step("v0.1"),
            release_step("v0.1.0", accepted_plan_files("v0.1", ["F01"], ["v0.1.0"]))])
NUMBERS = {item.subject: number for number, item in enumerate(STEPS, start=1)}
LINK, LINK2, OTHER = overturn_link(41, 501), overturn_link(43, 777), overturn_link(60, 10)
UNLISTED = "Waiting for Troy: which encoding should the report use"
TE_PREMISE = ("the fixture files are in the wrong folder.", "listed tests/fixtures on main.",
              "the fixtures are where the plan says; the plan's path is wrong.")
PM_PREMISE = ("the prototype's output is right.", "ran the prototype's command on main.",
              "the output differs only in the date line.")


def premise_lines(texts) -> list:
    """The three lines a premise attempt starts its Notes with."""
    return [f"Premise: {texts[0]}", f"Check: {texts[1]}", f"Result: {texts[2]}"]


# Each PR's comments, as (body, minutes after 09:00 UTC) on its own day, and its merge time.
TIMELINE = {
    2: ([(review("Architect", 1, "approved"), 60), (waiting(wait="W3"), 90), ("全按推荐", 180)],
        200),
    3: ([(attempt("Test Manager", 1), 0), (attempt("Test Manager", 2), 5),
         (waiting(wait="W3"), 15)], 150),
    4: ([(body, 60 + index) for index, body in enumerate(three_rounds("Code Reviewer"))]
        + [(ruling("Architect", "fix", *FIX_FINDINGS), 90),
           (ruling("Architect", "fixed", *FIXED_FINDINGS), 120)], 150),
    5: ([(attempt("Test Engineer", n), 10 * (n - 1)) for n in (1, 2, 3)]
        + [(escalation("the tests still fail after a premise attempt", "W7",
                       *premise_lines(TE_PREMISE)), 40),
           ("Fix the plan's path.", 100)], 300),
    6: ([(attempt("Developer", n), 10 * (n - 1)) for n in (1, 2, 3)]
        + [(UNLISTED + "\n\nUTF-8 or the system's encoding?", 240), ("UTF-8.", 260)], 300),
    7: ([(attempt("Product Manager", n), 10 * (n - 1)) for n in (1, 2, 3)]
        + [(attempt("Product Manager", 4, *premise_lines(PM_PREMISE)), 30),
           (escalation("the Product Manager's work still fails", "W7",
                       "The evidence is in attempt 4."), 40)], 160),
    8: ([(escalation("GitHub refused to run CI for billing", "W10"), 0)], 30),
    9: ([(waiting("accept v0.1.0", "W4"), 60), ("Accepted.", 300)], 320),
}
ISSUES = [progress_issue(20, "F01", comment_bodies=[overturn(LINK), carried_out(LINK),
                                                   overturn(LINK2)]),
          progress_issue(21, "F02", comment_bodies=[overturn(OTHER)])]


def merged_entries(project: Project) -> list:
    """Every step as a merged PR, with its merge commit, opening, and merge times."""
    shas = subject_commits(project)
    found = []
    for item in STEPS:
        number = NUMBERS[item.subject]
        entry = merged_pr(number, item.subject, shas[item.subject])
        merged = TIMELINE.get(number, ([], 400))[1]
        entry.update(createdAt=when(0, number) if number not in TIMELINE else when(-60, number),
                     mergedAt=when(merged, number), headRefName=f"troy-mode/pr-{number}")
        found.append(entry)
    return found


def comments_by_pr() -> dict:
    """Each PR's comments, timed on the PR's own day."""
    return {number: [timed(body, minutes, day=number) for body, minutes in bodies]
            for number, (bodies, _) in TIMELINE.items()}


class RetroStopsTests(FlowCase):
    """``waits``, ``unlisted``, ``rulings``, ``premise_attempts``, and ``overturns``."""

    @classmethod
    def setUpClass(cls):
        """One clone; retro with readable issues, and with ``gh issue list`` failing."""
        cls.project = Project(STEPS)
        merged = merged_entries(cls.project)
        base = {"merged": merged, "comments": comments_by_pr(), "labels": list(ALL_LABELS)}
        fakes = {"read": Fakes(**base, all_issues=ISSUES),
                 "unreadable": Fakes(**base, all_issues=ISSUES,
                                     fail_on=[(["issue", "list"], "HTTP 502: Bad Gateway")])}
        names = list(fakes)
        outs = parallel(lambda n: cls.project.run("retro", "--tag", "v0.1.0", fakes=fakes[n]),
                        names)
        cls.outs = dict(zip(names, outs))

    def report(self, name: str = "read") -> dict:
        """The retro report, exit 0."""
        return self.report_of(self.outs[name], 0, "retro")

    def test_waits_by_id(self):
        """W3 twice (1.5 and 2.25 hours, the second to the merge), W4, W7 twice, and W10."""
        self.assertEqual(self.report().get("waits"), {
            "W3": {"count": 2, "hours": 3.75, "prs": [2, 3]},
            "W4": {"count": 1, "hours": 4.0, "prs": [9]},
            "W7": {"count": 2, "hours": 3.0, "prs": [5, 7]},
            "W10": {"count": 1, "hours": 0.5, "prs": [8]},
        })

    def test_unlisted_waits(self):
        """The older wait without a ``Wait:`` line: its PR, URL, heading, and 20 minutes."""
        self.assertEqual(self.report().get("unlisted"), [
            {"pr": 6, "url": pr_url(6), "heading": UNLISTED, "hours": 0.33}])

    def test_rulings(self):
        """Both rulings of PR #4, oldest first, with their findings."""
        common = {"pr": 4, "url": pr_url(4), "ruler": "Architect", "round": 3}
        self.assertEqual(self.report().get("rulings"), [
            {**common, "result": "fix",
             "findings": [finding(1, "fix", FIX_FINDINGS[0][1]),
                          finding(2, "does not block", FIX_FINDINGS[1][1])]},
            {**common, "result": "fixed",
             "findings": [finding(1, "fixed", FIXED_FINDINGS[0][1])]}])

    def test_premise_attempts(self):
        """#5 escalated with the premise in its escalation, #6 fixed with no premise text, #7
        escalated with the premise in its fourth attempt; #3's two attempts are not one."""
        found = sorted(self.report().get("premise_attempts") or [], key=lambda e: e.get("pr"))
        self.assertEqual(found, [
            {"pr": 5, "url": pr_url(5), "role": "Test Engineer", "outcome": "escalated",
             "premise": TE_PREMISE[0], "check": TE_PREMISE[1], "result": TE_PREMISE[2]},
            {"pr": 6, "url": pr_url(6), "role": "Developer", "outcome": "fixed",
             "premise": None, "check": None, "result": None},
            {"pr": 7, "url": pr_url(7), "role": "Product Manager", "outcome": "escalated",
             "premise": PM_PREMISE[0], "check": PM_PREMISE[1], "result": PM_PREMISE[2]}])

    def test_overturns_of_the_versions_features(self):
        """F01's two overturns, one carried out; F02's, a feature outside the range, is not."""
        self.assertEqual(self.report().get("overturns"), [
            {"item": "F01", "issue": 20, "ruling": LINK, "done": True},
            {"item": "F01", "issue": 20, "ruling": LINK2, "done": False}])

    def test_unreadable_issues_give_no_overturns_and_a_note(self):
        """``gh issue list`` fails: ``overturns`` is empty, a note says why, and the rest
        stays."""
        report = self.report("unreadable")
        self.assertEqual(report.get("overturns", "missing"), [])
        self.assertTrue([n for n in report["notes"] if "issue" in n.lower()], report["notes"])
        self.assertEqual(report.get("waits"), self.report().get("waits"))


if __name__ == "__main__":
    unittest.main()
