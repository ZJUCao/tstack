"""The progress issue's part 1 lines (F18 design 4.2, 5.3, 8, 9 F15; part 1 contract section 8).

F15's progress issue names the ID of a wait, gives one line per ruled PR of the feature
with its newest result and a link to its first ruling, and one line per overturn on the
issue. A merged PR's rulings are read once per checkout and kept in the common git folder.

``WaitLineTests.test_unlisted_wait_keeps_todays_text`` passes on today's engine: an
``unlisted`` wait keeps the text F15 gives it now.
"""

import unittest
from pathlib import Path

from flow_helpers import F01, REPO_URL, TWO, base_step, comments, pr, stage_pr, stages
from issues_helpers import (
    ALL_LABELS, IssuesCase, all_pr, issues_run, issues_runs, nonblank, progress_issue,
    progress_marker, project_files, split_body, stage_prs,
)
from stops_helpers import (
    FIX_FINDINGS, FIXED_FINDINGS, MERGE_FINDINGS, NOT_FIXED_FINDINGS, TEST_FIX, carried_out,
    comment_url, escalation, in_order, overturn, overturn_link, review, ruling, three_rounds,
    waiting,
)
from teams2_helpers import common_git

CR, ARCH = "Code Reviewer", "Architect"
U1, U2, U3, U4, U5 = (comment_url(n, c) for n, c in ((43, 11), (43, 12), (46, 31), (46, 32),
                                                    (44, 21)))
LINK, LINK2 = overturn_link(41, 501), overturn_link(43, 777)
BASE = base_step(project_files(TWO))
MOCK_PRS = stage_prs(F01, 2) + [all_pr(43, F01.title(3), "OPEN")]
ESCALATION = escalation("the Developer's mock still fails after a premise attempt", "W7")


def fakes(**kwargs) -> dict:
    """Fakes keyword arguments with the three F15 labels already in the repository."""
    return {"labels": list(ALL_LABELS), **kwargs}


def rounds_then(*rulings_with_urls) -> list:
    """Three Code Reviewer rounds asking for changes, then rulings ``(body, url)``."""
    bodies = [*three_rounds(CR), *(body for body, _ in rulings_with_urls)]
    urls = {3 + index: url for index, (_, url) in enumerate(rulings_with_urls)}
    return in_order(*bodies, urls=urls)


CASES = {
    "W3": ([BASE], fakes(prs=[stage_pr(41, F01, 1)], comments={41: comments(
        review(ARCH, 1, "approved"), waiting(wait="W3"))})),
    "unlisted": ([BASE], fakes(prs=[stage_pr(41, F01, 1)], comments={41: comments(
        review(ARCH, 1, "approved"), waiting())})),
    "W7": ([BASE, *stages(F01, 2)], fakes(prs=[stage_pr(43, F01, 3)], all_prs=MOCK_PRS,
                                          comments={43: comments(ESCALATION)})),
    "open ruled": ([BASE, *stages(F01, 2)], fakes(
        prs=[stage_pr(43, F01, 3)], all_prs=MOCK_PRS,
        comments={43: rounds_then((ruling(ARCH, "fix", *FIX_FINDINGS), U1),
                                  (ruling(ARCH, "fixed", *FIXED_FINDINGS), U2))})),
    "merged ruled": ([BASE, *stages(F01, 2)], fakes(
        all_prs=stage_prs(F01, 2),
        comments={41: in_order(*three_rounds(ARCH),
                               ruling("Product Manager", "merge", *MERGE_FINDINGS))})),
    "side and ruled": ([BASE, *stages(F01, 4)], fakes(
        prs=[pr(46, TEST_FIX, "troy-mode/f01-test-fix")],
        all_prs=stage_prs(F01, 4) + [all_pr(46, TEST_FIX, "OPEN")],
        comments={44: rounds_then((ruling(ARCH, "fix", *FIX_FINDINGS), U5)),
                  46: rounds_then((ruling(ARCH, "fix", *FIX_FINDINGS), U3),
                                  (ruling(ARCH, "not fixed", *NOT_FIXED_FINDINGS), U4))})),
    "overturns": ([BASE, *stages(F01, 1)], fakes(
        all_prs=stage_prs(F01, 1),
        all_issues=[progress_issue(7, "F01", comment_bodies=[
            overturn(LINK), overturn(LINK2), carried_out(LINK)])])),
}


class ProgressLinesCase(IssuesCase):
    """Runs ``issues`` once per case, side by side, and reads F01's rendered body."""

    outs: dict = {}

    @classmethod
    def setUpClass(cls):
        """Runs every case on first use."""
        if not ProgressLinesCase.outs:
            ProgressLinesCase.outs = issues_runs(CASES)

    def parts(self, name: str) -> tuple:
        """F01's body in the case: its non-blank Chinese and English lines."""
        out, fake, _ = self.outs[name]
        report = self.issues_report(out)
        self.assert_read_only(fake)
        found = [a for a in report["actions"]
                 if a["item"] == "F01" and a["action"] in ("create", "edit")]
        self.assertEqual(len(found), 1, report["actions"])
        body = self.body_of(found[0])
        self.assertEqual(body.split("\n")[0], progress_marker("F01"))
        chinese, english = split_body(body)
        return nonblank(chinese), nonblank(english)


class WaitLineTests(ProgressLinesCase):
    """"Waiting for you" starts with a listed wait's ID (contract 8)."""

    def test_listed_wait_starts_with_its_id(self):
        """``Wait: W3`` under the approval request: the line starts with W3 in both parts."""
        chinese, english = self.parts("W3")
        self.assertIn("等你：W3，批准 #41；要决定的事在它描述的开头。", chinese)
        self.assertIn("Waiting for you: W3, approve #41; what to decide is at the top of its "
                      "description.", english)

    def test_escalation_starts_with_its_id(self):
        """``Wait: W7`` under an escalation: the line starts with W7 and keeps the trigger."""
        chinese, english = self.parts("W7")
        zh = [line for line in chinese if line.startswith("等你：")]
        en = [line for line in english if line.startswith("Waiting for you:")]
        self.assertEqual(zh, ["等你：W7，#43 上的上报：the Developer's mock still fails "
                              "after a premise attempt。"])
        self.assertEqual(en, ["Waiting for you: W7, the escalation on #43: the Developer's mock "
                              "still fails after a premise attempt."])

    def test_unlisted_wait_keeps_todays_text(self):
        """An older request without the line: today's text, with no ID."""
        chinese, english = self.parts("unlisted")
        self.assertIn("等你：批准 #41；要决定的事在它描述的开头。", chinese)
        self.assertIn("Waiting for you: approve #41; what to decide is at the top of its "
                      "description.", english)


class RulingLineTests(ProgressLinesCase):
    """One line per ruled PR, with its newest result and its first ruling (contract 8)."""

    def test_open_pr_shows_its_newest_result_and_first_ruling(self):
        """``fix`` then ``fixed`` on the open mock PR: ``fixed``, linked to the ``fix``."""
        chinese, english = self.parts("open ruled")
        self.assertIn(f"裁定：#43 架构师第 3 轮：已改（[裁定]({U1})）", chinese)
        self.assertIn(f"Ruling: #43 Architect, round 3: fixed ([ruling]({U1}))", english)

    def test_merged_pr_without_a_comment_url_links_the_pr(self):
        """The merged design's PM7 ruling, whose comment has no ``url``: the PR's URL."""
        chinese, english = self.parts("merged ruled")
        url = f"{REPO_URL}/pull/41"
        self.assertIn(f"裁定：#41 产品经理第 3 轮：合并（[裁定]({url})）", chinese)
        self.assertIn(f"Ruling: #41 Product Manager, round 3: merge ([ruling]({url}))", english)

    def test_test_fix_and_merged_stage_after_the_side_pr_line(self):
        """The open test fix (``not fixed``) and the merged tests PR (``fix``): a line each,
        after the side PR line."""
        chinese, english = self.parts("side and ruled")
        side_zh = f"附带 PR：#46 {TEST_FIX}（进行中）"
        side_en = f"Side PRs: #46 {TEST_FIX} (open)"
        for zh, en in ((f"裁定：#46 架构师第 3 轮：未改好（[裁定]({U3})）",
                        f"Ruling: #46 Architect, round 3: not fixed ([ruling]({U3}))"),
                       (f"裁定：#44 架构师第 3 轮：要改（[裁定]({U5})）",
                        f"Ruling: #44 Architect, round 3: fix ([ruling]({U5}))")):
            with self.subTest(line=en):
                self.assert_in_order(chinese, [side_zh, zh])
                self.assert_in_order(english, [side_en, en])

    def test_no_line_without_a_ruling(self):
        """A feature whose PRs have no ruling: no ruling line in either part."""
        chinese, english = self.parts("W3")
        self.assertEqual([line for line in chinese if line.startswith("裁定：")], [])
        self.assertEqual([line for line in english if line.startswith("Ruling:")], [])


class OverturnLineTests(ProgressLinesCase):
    """One line per overturn on the issue, carried out or not (contract 8)."""

    def test_each_overturn_has_a_line(self):
        """The first overturn carried out, the second not."""
        chinese, english = self.parts("overturns")
        self.assertIn(f"推翻：{LINK}（已完成）", chinese)
        self.assertIn(f"推翻：{LINK2}（进行中）", chinese)
        self.assertIn(f"Overturn: {LINK} (carried out)", english)
        self.assertIn(f"Overturn: {LINK2} (being carried out)", english)


class MergedRulingsCacheTests(IssuesCase):
    """A merged PR's rulings are read once per checkout, then kept (contract 8)."""

    @classmethod
    def setUpClass(cls):
        """Runs ``issues`` twice in one clone with the same fake gh."""
        steps, kwargs = CASES["merged ruled"]
        cls.first, cls.fakes, cls.project = issues_run(steps, kwargs)
        cls.first_calls = cls.fakes.gh_argvs()
        cls.fakes.clear()
        cls.second = cls.project.run("issues", fakes=cls.fakes)
        cls.second_calls = cls.fakes.gh_argvs()

    def views(self, calls) -> list:
        """The PR numbers of the ``gh pr view`` calls."""
        return sorted(argv[2] for argv in calls if argv[:2] == ["pr", "view"])

    def body(self, out) -> str:
        """F01's rendered body."""
        report = self.issues_report(out)
        found = [a for a in report["actions"] if a["item"] == "F01"]
        self.assertEqual(len(found), 1, report["actions"])
        return self.body_of(found[0])

    def test_first_run_reads_and_keeps_the_rulings(self):
        """The first run reads #41's comments and keeps them in ``troy-mode/rulings.json``."""
        self.issues_report(self.first)
        self.assertIn("41", self.views(self.first_calls))
        self.assertTrue((Path(common_git(self.project)) / "troy-mode" / "rulings.json").is_file())

    def test_second_run_does_not_read_them_again(self):
        """The second run views no merged PR and still shows the ruling line."""
        url = f"{REPO_URL}/pull/41"
        self.assertIn(f"Ruling: #41 Product Manager, round 3: merge ([ruling]({url}))",
                      self.body(self.second).split("\n"))
        self.assertEqual(self.views(self.second_calls), [])


if __name__ == "__main__":
    unittest.main()
