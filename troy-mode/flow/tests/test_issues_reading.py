"""Reading Troy (F15 design 3.3, 7, 8.4; 13.1 "Reading Troy"; interface note sections 1 to 3).

Troy's "Comment" review on a PR that waits for Troy ends the wait as a
comment does; Troy's comments on progress issues and checklists reach
``issues.troy_comments``; and every heading of design 8.4 is troy-mode's,
on issues and on PRs.

Planted bug of design 13.2 caught here: "a Troy review on a waiting PR
ignored": ``ReviewTests.test_review_after_the_request_ends_the_wait``.
"""

import unittest

from flow_helpers import F01, TWO, base_step, comments, pr, stage_pr
from issues_helpers import (
    ALL_LABELS, HEADINGS, IssuesCase, checklist_issue, gh_issue, progress_issue, project_files,
    review, status_runs_with,
)

REQUEST = "Waiting for Troy: approve this PR"
ASKED = comments("Architect review, round 1: approved\n\nNone", REQUEST)
QUESTION = "Why is the mock so small?"


def base():
    """The first commit, with a Chinese mirror that has a features table."""
    return base_step(project_files(TWO))


def waiting_pr(*reviews) -> dict:
    """Fakes for F01's open design PR #41, which waits for Troy, with reviews."""
    return {"prs": [stage_pr(41, F01, 1)], "comments": {41: ASKED},
            "reviews": {41: list(reviews)}, "labels": list(ALL_LABELS)}


def heading_prs() -> dict:
    """One open docs PR per heading of design 8.4: Troy's question, then the heading."""
    prs = [pr(61 + i, f"[docs] Note {i}", f"troy-mode/note-{i}") for i in range(len(HEADINGS))]
    by_pr = {61 + i: comments(QUESTION, heading + "\n\nThe answer.")
             for i, heading in enumerate(HEADINGS)}
    by_pr[70] = comments(QUESTION, "Reply to Troy\n\nThe answer.", "OK, thanks.")
    prs.append(pr(70, "[docs] Note answered", "troy-mode/note-answered"))
    return {"prs": prs, "comments": by_pr, "labels": list(ALL_LABELS)}


def heading_ideas() -> list:
    """One idea per heading, answered by it; and two whose heading is not a first line."""
    ideas = [gh_issue(110 + i, f"Idea {i}", "Something.", ("idea",),
                      (QUESTION, heading + "\n\nThe answer."))
             for i, heading in enumerate(HEADINGS)]
    ideas.append(gh_issue(130, "Not a heading", "x", ("idea",),
                          (QUESTION, "Thanks.\nReply to Troy")))
    ideas.append(gh_issue(131, "Not a run number", "x", ("idea",),
                          (QUESTION, "Device test, run two: ready")))
    return ideas


ISSUE_THREADS = [
    progress_issue(7, "F01", comment_bodies=(
        "Why is stage 3 slow?", "Reply to Troy\n\nIt waits for the review.",
        "OK. And the docs?", "Also check F02.")),
    progress_issue(8, "F02", comment_bodies=("Reply to Troy\n\nNothing yet.",)),
    progress_issue(6, "F02", state="CLOSED", reason="NOT_PLANNED",
                   comment_bodies=("This one is closed.",)),
    checklist_issue(9, "v0.1.0", comment_bodies=("v0.1-S02 prints 0 on the laptop.",)),
    checklist_issue(4, "v0.0.1", comment_bodies=()),
    gh_issue(101, "An idea", "Count tabs.", ("idea",), ("More: tabs count as one.",)),
]


class ReadingCase(IssuesCase):
    """Runs every status case once, side by side."""

    outs: dict = {}

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case."""
        if ReadingCase.outs:
            return
        ReadingCase.outs = status_runs_with({
            "review after": ([base()], waiting_pr(review("全按推荐", "2026-11-07T11:00:00Z"))),
            "review before": ([base()], waiting_pr(review("Looks right.",
                                                          "2026-11-07T09:00:00Z"))),
            "empty review": ([base()], waiting_pr(review("", "2026-11-07T11:00:00Z",
                                                         "APPROVED"))),
            "headings on PRs": ([base()], heading_prs()),
            "headings on ideas": ([base()], {"all_issues": heading_ideas(),
                                             "labels": list(ALL_LABELS)}),
            "issue threads": ([base()], {"all_issues": ISSUE_THREADS,
                                         "labels": list(ALL_LABELS)}),
        })

    def report(self, name: str) -> dict:
        """A case's status report; exit 0 and only reads."""
        out, fake, _ = self.outs[name]
        self.assert_read_only(fake)
        return self.report_of(out, 0, "status")


class ReviewTests(ReadingCase):
    """A "Comment" review is Troy's reply on a PR (design 3.3, 7; note section 1)."""

    def entry(self, name: str) -> dict:
        """The open PR #41's entry."""
        found = [p for p in self.report(name)["open_prs"] if p["number"] == 41]
        self.assertEqual(len(found), 1, self.report(name)["open_prs"])
        return found[0]

    def test_review_after_the_request_ends_the_wait(self):
        """Planted bug "a Troy review on a waiting PR ignored": "全按推荐" as a review."""
        entry = self.entry("review after")
        self.assertEqual((entry["waiting_for_troy"], entry["troy_comments"]),
                         (False, ["全按推荐"]))
        self.assertIsNone(self.report("review after")["waiting_on_troy"])
        self.assertEqual(self.entry("review after")["reviews"],
                         [{"role": "Architect", "round": 1, "result": "approved"}])

    def test_review_before_the_request_does_not(self):
        """Pair: a review older than the request leaves the PR waiting."""
        entry = self.entry("review before")
        self.assertEqual((entry["waiting_for_troy"], entry["troy_comments"]), (True, []))
        # F18 part 1 (contract 2): a request without a "Wait:" line waits as "unlisted".
        self.assertEqual(self.report("review before")["waiting_on_troy"],
                         f"unlisted, PR #41: {REQUEST}")

    def test_review_without_a_body_does_not(self):
        """Pair: an approval with no text is no reply; the PR still waits."""
        entry = self.entry("empty review")
        self.assertEqual((entry["waiting_for_troy"], entry["troy_comments"]), (True, []))


class HeadingTests(ReadingCase):
    """Every heading of design 8.4 is troy-mode's (note section 2)."""

    def test_headings_on_prs_are_troy_modes(self):
        """Troy's question then a heading: no comment of Troy's is left after it."""
        entries = {p["number"]: p for p in self.report("headings on PRs")["open_prs"]}
        for index, heading in enumerate(HEADINGS):
            with self.subTest(heading=heading):
                self.assertEqual(entries[61 + index]["troy_comments"], [])
        self.assertEqual(entries[70]["troy_comments"], ["OK, thanks."])

    def test_headings_on_issues_are_troy_modes(self):
        """An idea answered under each heading is not new; a heading inside a line is Troy's."""
        found = (self.report("headings on ideas").get("issues") or {}).get("ideas") or []
        ideas = {e["number"]: e for e in found}
        self.assertEqual(sorted(ideas), [110 + i for i in range(len(HEADINGS))] + [130, 131])
        for index, heading in enumerate(HEADINGS):
            with self.subTest(heading=heading):
                self.assertIs(ideas[110 + index]["new"], False)
                self.assertEqual(ideas[110 + index]["comments"][-1]["by"], "troy-mode")
        for number in (130, 131):
            with self.subTest(idea=number):
                self.assertIs(ideas[number]["new"], True)
                self.assertEqual(ideas[number]["comments"][-1]["by"], "troy")


class IssueCommentTests(ReadingCase):
    """Troy's comments on progress issues and checklists (design 3.3, 7; note section 3)."""

    def test_troys_comments_since_troy_modes_last(self):
        """#7: the two after the reply; #9: Troy's only comment; others left out."""
        found = (self.report("issue threads").get("issues") or {}).get("troy_comments")
        self.assertIsInstance(found, list)
        self.assertEqual(sorted(found, key=lambda entry: entry["issue"]), [
            {"issue": 7, "kind": "progress", "item": "F01",
             "bodies": ["OK. And the docs?", "Also check F02."]},
            {"issue": 9, "kind": "device-test", "item": "v0.1.0",
             "bodies": ["v0.1-S02 prints 0 on the laptop."]}])


if __name__ == "__main__":
    unittest.main()
