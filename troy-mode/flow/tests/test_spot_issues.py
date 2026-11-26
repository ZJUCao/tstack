"""Spot checks on Troy's issues (F18 design 7.1, 7.2, 9 F15, 13.1 "Spot checks"; contract 7).

While spot checks are on, a sampled feature's progress issue says it is in the sample, and a
feature at stage 1 or 2 whose stage has marks says why it waits for Troy. Once spot checks
have been on in a project, the version's checklist gets one box for each merged PR 1 or PR 2
that got the spot check comment and that Troy has not answered, and keeps each such box Troy
ticked. ``status`` reads the boxes into ``issues.device_test.samples``, and ``result`` is
``ticked`` only when every sample box is ticked too.

Planted bugs of design 13.2 caught here:

- "the sampled feature getting no line or the sample line shown with spot checks off":
  ``ProgressLineTests.test_sample_and_risky_lines_in_place`` and
  ``test_no_line_with_spot_checks_off``.
- "an unanswered sample without a box": ``ChecklistTests.test_unanswered_samples_get_boxes``.
- "an answered sample keeping an unticked box": ``ChecklistTests.test_sync_keeps_ticked_boxes``.
- "``ticked`` with a sample box unticked": ``TickTests.test_results``.

``ProgressLineTests.test_no_line_with_spot_checks_off`` and
``ChecklistTests.test_no_box_when_never_on`` pass on today's engine: with spot checks never
on, today's bodies stay as they are.
"""

import unittest

from flow_helpers import CONFIG, F01, F02, base_step, config_text, stages, step, version_tests_step
from issues_helpers import (
    COMMIT1, COMMIT2, DETAILS, REVIEWED, TAG, IssuesCase, box_lines, checklist_issue,
    checklist_marker, comments, nonblank, passed, plan_pair, project_files, release_pr,
    split_body, waiting,
)
from issues_helpers import RELEASE_FEATURES
from spot_helpers import (
    APPROVALS_TITLE, ISSUE_LABELS, OLD_TIME, SPOT_COMMENT, Case, all_listed,
    answer_step, arch_review, attempts, chain, closed_idea, curl, custom_design_files,
    flow, gh_issue, issue_comment, link_to, note, overturn, progress_issue, ruled, run_cases,
    spot_files, stage_numbers, stage_open, thread,
)
from stops_helpers import MERGE_FINDINGS, ruling

FIVE = chain(5)
G1, G2, G3 = FIVE[:3]
ON, OFF = flow(1, True, 2), flow(1)
SPOT_ZH = "抽查：这个功能在抽查样本里，设计和测试计划合并后由你复查。"
SPOT_EN = ("Spot check: this feature is in the sample; you review its design and test plan "
           "after they merge.")
RULED_31 = [arch_review(1, "changes-requested", "network access"),
            arch_review(2, "changes-requested"), arch_review(3, "changes-requested"),
            ruling("Product Manager", "merge", *MERGE_FINDINGS)]
NOTE_TEXT = "it renames Troy's files"


def history(config: str, *more) -> list:
    """F01 accepted (one approved), the answer (step 7), F02 accepted, then more."""
    return [base_step(spot_files(FIVE, config)), *stages(G1, 6), answer_step(), *stages(G2, 6),
            *more]


def f03_issue() -> list:
    """F03's progress issue with Troy's ``Risky:`` note and an overturn older than the answer,
    and an open real-run bug of F03."""
    return [progress_issue(8, G3, [issue_comment(8, 801, note("F03", f"Risky: {NOTE_TEXT}")),
                                   issue_comment(8, 802, overturn(curl(31, 3)), OLD_TIME)]),
            gh_issue(50, "Real run of F03: wrong count", "It counts 4.", ("bug",))]


MERGED_12 = [*stage_numbers(G1, 6, 10), *stage_numbers(G2, 6, 20)]


def merged_f03(config: str, comments31, upto: int = 1) -> Case:
    """F03 with stages 1 to ``upto`` merged (#31, #32), #31's comments, and F03's issue."""
    return Case(history(config, *stages(G3, upto)),
                {"all_prs": all_listed((), [*MERGED_12, *stage_numbers(G3, upto, 30)]),
                 "comments": {31: thread(31, *comments31)}, "all_issues": f03_issue(),
                 "labels": list(ISSUE_LABELS)}, command="issues")


PROGRESS_CASES = {
    "on": merged_f03(ON, RULED_31),
    "off": merged_f03(OFF, RULED_31),
    "sample only": Case(history(ON, *stages(G3, 1)),
                        {"all_prs": all_listed((), [*MERGED_12, (31, G3.title(1))]),
                         "comments": {31: thread(31, arch_review(1))},
                         "labels": list(ISSUE_LABELS)}, command="issues"),
    "stage 3": merged_f03(ON, RULED_31, upto=2),
    "risky only": Case([base_step(spot_files(FIVE, ON)), *stages(G1, 6), answer_step()],
                       {"prs": [stage_open(21, G2, 1)], "comments": {21: thread(21, *ruled())},
                        "all_prs": all_listed([stage_open(21, G2, 1)], stage_numbers(G1, 6, 10)),
                        "labels": list(ISSUE_LABELS)}, command="issues"),
    "interface and premise": Case(
        history(ON), {"prs": [stage_open(31, G3, 1)],
                      "comments": {31: thread(31, *attempts("Interface Designer", 1, 2, 3))},
                      "all_prs": all_listed([stage_open(31, G3, 1)], MERGED_12),
                      "labels": list(ISSUE_LABELS)}, command="issues",
        branches={G3.branch(1): (G3.title(1), custom_design_files(
            G3, "### 3.1 `count` of F02\n\nIt now counts blank lines too.\n"))}),
}


class ProgressLineTests(IssuesCase):
    """The progress issue's sample and risky lines (contract 7)."""

    outs: dict = {}

    @classmethod
    def setUpClass(cls):
        """Runs ``issues`` once per case, side by side."""
        if not ProgressLineTests.outs:
            ProgressLineTests.outs = run_cases(PROGRESS_CASES)

    def parts(self, name: str, item: str) -> tuple:
        """The non-blank Chinese and English lines of one feature's rendered body."""
        out, fake, _ = self.outs[name]
        report = self.issues_report(out)
        self.assert_read_only(fake)
        found = [a for a in report["actions"]
                 if a["item"] == item and a["action"] in ("create", "edit")]
        self.assertEqual(len(found), 1, report["actions"])
        chinese, english = split_body(self.body_of(found[0]))
        return nonblank(chinese), nonblank(english)

    def test_sample_and_risky_lines_in_place(self):
        """Planted bug "the sampled feature getting no line": F03, sampled, at stage 2 with
        PR 1's ruling, the Architect's line, and Troy's note: both lines, after the ruling and
        overturn lines and before the real-run bugs line."""
        chinese, english = self.parts("on", "F03")
        link = curl(31, 3)
        self.assert_in_order(chinese, [
            f"裁定：#31 产品经理第 3 轮：合并（[裁定]({link})）", f"推翻：{link}（进行中）", SPOT_ZH,
            f"风险：第 3 轮有裁定（#31）；架构师：network access（#31）；你：{NOTE_TEXT}，合并前等你批准。",
            "实际运行发现的 bug：#50 Real run of F03: wrong count（未解决）"])
        self.assert_in_order(english, [
            f"Ruling: #31 Product Manager, round 3: merge ([ruling]({link}))",
            f"Overturn: {link} (being carried out)", SPOT_EN,
            f"Risky: a ruling at round 3 (#31); the Architect: network access (#31); you: "
            f"{NOTE_TEXT}; it waits for your approval before the merge.",
            "Real-run bugs: #50 Real run of F03: wrong count (open)"])

    def test_no_line_with_spot_checks_off(self):
        """Planted bug "the sample line shown with spot checks off": no ``spot_checks``: neither
        line, though the marks are there."""
        chinese, english = self.parts("off", "F03")
        self.assertEqual([line for line in chinese if line.startswith(("抽查：", "风险："))], [])
        self.assertEqual([line for line in english
                          if line.startswith(("Spot check:", "Risky:"))], [])
        self.assertIn("实际运行发现的 bug：#50 Real run of F03: wrong count（未解决）", chinese)

    def test_sample_without_marks(self):
        """F03 sampled, PR 1 merged without a mark: the sample line only."""
        chinese, english = self.parts("sample only", "F03")
        self.assertIn(SPOT_ZH, chinese)
        self.assertIn(SPOT_EN, english)
        self.assertEqual([line for line in chinese if line.startswith("风险：")], [])
        self.assertEqual([line for line in english if line.startswith("Risky:")], [])

    def test_risky_line_only_at_stage_1_or_2(self):
        """F03 at stage 3, its PR 1 ruled: the sample line, no risky line."""
        chinese, english = self.parts("stage 3", "F03")
        self.assertIn(SPOT_ZH, chinese)
        self.assertEqual([line for line in chinese if line.startswith("风险：")], [])
        self.assertEqual([line for line in english if line.startswith("Risky:")], [])

    def test_risky_line_of_a_feature_not_sampled(self):
        """F02, not sampled, its open PR 1 ruled: the risky line, no sample line."""
        chinese, english = self.parts("risky only", "F02")
        self.assertIn("风险：第 3 轮有裁定（#21），合并前等你批准。", chinese)
        self.assertIn("Risky: a ruling at round 3 (#21); it waits for your approval before the "
                      "merge.", english)
        self.assertNotIn(SPOT_ZH, chinese)
        self.assertNotIn(SPOT_EN, english)

    def test_interface_and_premise_reasons(self):
        """F03's open PR 1 with a changed interface on its branch and three failed attempts."""
        chinese, english = self.parts("interface and premise", "F03")
        self.assertIn("风险：设计改动了已有接口（#31）；用过前提尝试（#31），合并前等你批准。", chinese)
        self.assertIn("Risky: the design changes an existing interface (#31); a premise attempt "
                      "(#31); it waits for your approval before the merge.", english)


# ------------------------------------------------------------------ the checklist

SPOT_ON = flow(0, True, 2)
RELEASE_PRS = [release_pr(30, TAG)]
STAGE_PRS = [*stage_numbers(F01, 6, 40), *stage_numbers(F02, 6, 50)]
S02 = "- [ ] **v0.1-S02 在 Troy 的笔记本上统计**"
S04 = "- [ ] **v0.1-S04 在 Windows Terminal 里读中文**"
S05 = "- [ ] **v0.1-S05 PT02**"
ACCEPT = "- [ ] **我接受 v0.1.0。**"


def zh_box(number: int, title: str, ticked: bool = False) -> str:
    """A sample's box in the checklist's Chinese part."""
    return (f"- [{'x' if ticked else ' '}] **抽查 #{number} {title}**：已合并、没等你批准的抽查。"
            "看过它的摘要就勾上；不同意就在这个功能的进度 issue 上评论。")


def en_line(number: int, title: str) -> str:
    """A sample's line in the checklist's English part."""
    return (f"Spot check #{number} {title}: merged without your approval. Tick it once you "
            "have read its summary; to disagree, comment on the feature's progress issue.")


def release_history(config: str, *more) -> list:
    """F01 and F02 accepted, the version tests merged, the plan with Troy's scenarios."""
    files = project_files(RELEASE_FEATURES, extra=plan_pair(), config_extra=config)
    return [base_step(files), *stages(F01, 6), *stages(F02, 6), *more,
            version_tests_step("v0.1")]


SAMPLE_COMMENTS = {
    41: (SPOT_COMMENT,),                                          # answered by an overturn
    42: (SPOT_COMMENT, arch_review(1), note("F02", "Count tabs too.")),   # not answered
    43: (SPOT_COMMENT,),                                          # a mock: no box
    51: (SPOT_COMMENT,),                                          # not answered
    52: (SPOT_COMMENT, "Looks right to me."),                     # answered by Troy
}


def release_fakes(issues=(), sample_comments=None, release_bodies=None) -> dict:
    """The open release PR #30 after run 1 passed, the merged stage PRs, and the issues."""
    found = {30: comments(REVIEWED, *(release_bodies or (passed(1, COMMIT1), waiting())))}
    found.update({n: thread(n, *bodies)
                  for n, bodies in (sample_comments or SAMPLE_COMMENTS).items()})
    return {"prs": RELEASE_PRS, "comments": found, "all_prs": all_listed(RELEASE_PRS, STAGE_PRS),
            "all_issues": [closed_idea(95, [issue_comment(95, 951, overturn(link_to(41)))]),
                           *issues], "labels": list(ISSUE_LABELS)}


def hand_body(*boxes: str) -> str:
    """A checklist body with the given box lines in its Chinese part."""
    return "\n".join([checklist_marker(TAG), "**在你的设备上测试 v0.1.0** · 第 1 轮 · 要测的提交：34a7728",
                      "", *boxes, "", DETAILS, "", "**Test v0.1.0 on your devices**", "",
                      "</details>", ""])


TITLE_42, TITLE_51, TITLE_52 = F01.title(2), F02.title(1), F02.title(2)
ANSWERED_51 = {**SAMPLE_COMMENTS, 51: (SPOT_COMMENT, "Fine by me.")}
CHECKLIST_CASES = {
    "on": Case(release_history(SPOT_ON), release_fakes(), command="issues"),
    "never on": Case(release_history(flow(0)), release_fakes(), command="issues"),
    "on once": Case(release_history(SPOT_ON, step(APPROVALS_TITLE, {
        CONFIG: config_text(extra=flow(0, False, 2))})), release_fakes(), command="issues"),
    "ticked kept": Case(release_history(SPOT_ON), release_fakes(
        [checklist_issue(9, TAG, hand_body(S02, S04, S05, zh_box(42, TITLE_42),
                                           zh_box(51, TITLE_51, True), zh_box(52, TITLE_52),
                                           ACCEPT))], ANSWERED_51), command="issues"),
    "new run": Case(release_history(SPOT_ON), release_fakes(
        [checklist_issue(9, TAG, hand_body(S02, S04, S05, zh_box(42, TITLE_42),
                                           zh_box(51, TITLE_51, True), ACCEPT))],
        release_bodies=(passed(1, COMMIT1), waiting(),
                        "Release test by Troy, run 1: failed\n\nTroy: v0.1-S02 prints 0.",
                        passed(2, COMMIT2), waiting())), command="issues"),
}


class ChecklistTests(IssuesCase):
    """The checklist's boxes for unanswered samples (contract 7)."""

    outs: dict = {}

    @classmethod
    def setUpClass(cls):
        """Runs ``issues`` once per case, side by side."""
        if not ChecklistTests.outs:
            ChecklistTests.outs = run_cases(CHECKLIST_CASES)

    def parts(self, name: str) -> tuple:
        """The checklist body's Chinese and English lines, from its one action."""
        out, fake, _ = self.outs[name]
        report = self.issues_report(out)
        self.assert_read_only(fake)
        found = [a for a in report["actions"]
                 if a.get("kind") == "device-test" and a.get("body_file")]
        self.assertEqual(len(found), 1, report["actions"])
        return split_body(self.body_of(found[0]))

    def test_unanswered_samples_get_boxes(self):
        """Planted bug "an unanswered sample without a box": #42 (a review and a note after
        the spot check comment) and #51: a box each, lowest first, after the scenarios and
        before the accept box; #41 (overturned), #52 (Troy answered), and the mock #43: none."""
        chinese, english = self.parts("on")
        self.assertEqual(box_lines(chinese), [S02, S04, S05, zh_box(42, TITLE_42),
                                              zh_box(51, TITLE_51), ACCEPT])
        self.assert_in_order(nonblank(english), ["v0.1-S05 PT02", en_line(42, TITLE_42),
                                                 en_line(51, TITLE_51)])
        self.assertEqual([line for line in english if line.startswith("Spot check #")],
                         [en_line(42, TITLE_42), en_line(51, TITLE_51)])

    def test_no_box_when_never_on(self):
        """No version of the config ever had ``spot_checks = true``: no sample box."""
        chinese, english = self.parts("never on")
        self.assertEqual(box_lines(chinese), [S02, S04, S05, ACCEPT])
        self.assertEqual([line for line in english if line.startswith("Spot check #")], [])

    def test_boxes_once_spot_checks_were_on(self):
        """Spot checks on in the first commit, turned off later: the boxes still come."""
        chinese, _ = self.parts("on once")
        self.assertEqual(box_lines(chinese), [S02, S04, S05, zh_box(42, TITLE_42),
                                              zh_box(51, TITLE_51), ACCEPT])

    def test_sync_keeps_ticked_boxes(self):
        """Planted bug "an answered sample keeping an unticked box": #51, answered now, keeps
        its ticked box; #52, answered, loses its unticked one; #42 keeps its box."""
        chinese, _ = self.parts("ticked kept")
        self.assertEqual(box_lines(chinese), [S02, S04, S05, zh_box(42, TITLE_42),
                                              zh_box(51, TITLE_51, True), ACCEPT])

    def test_new_run_keeps_ticked_boxes(self):
        """A new run after Troy's failure keeps #51's ticked box."""
        chinese, _ = self.parts("new run")
        self.assertIn(zh_box(51, TITLE_51, True), box_lines(chinese))
        self.assertIn(zh_box(42, TITLE_42), box_lines(chinese))


TICKED = S02.replace("[ ]", "[x]"), S04.replace("[ ]", "[x]"), S05.replace("[ ]", "[x]")
ACCEPTED = ACCEPT.replace("[ ]", "[x]")
TICK_CASES = {
    "all": hand_body(*TICKED, zh_box(42, TITLE_42, True), zh_box(51, TITLE_51, True), ACCEPTED),
    "sample unticked": hand_body(*TICKED, zh_box(42, TITLE_42, True), zh_box(51, TITLE_51),
                                 ACCEPTED),
    "only samples": hand_body(S02, S04, S05, zh_box(42, TITLE_42, True),
                              zh_box(51, TITLE_51, True), ACCEPT),
    "none": hand_body(S02, S04, S05, zh_box(42, TITLE_42), zh_box(51, TITLE_51), ACCEPT),
}


class TickTests(IssuesCase):
    """``read_ticks`` and ``issues.device_test`` with sample boxes (contract 7)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per checklist body, side by side."""
        cls.outs = run_cases({name: Case(release_history(SPOT_ON), release_fakes(
            [checklist_issue(9, TAG, body)])) for name, body in TICK_CASES.items()})

    def device_test(self, name: str) -> dict:
        """The case's ``issues.device_test``."""
        out, fake, _ = self.outs[name]
        report = self.report_of(out, 0, "status")
        self.assert_read_only(fake)
        found = (report.get("issues") or {}).get("device_test")
        self.assertIsInstance(found, dict, report.get("issues"))
        return found

    def test_samples_in_body_order(self):
        """``samples``: #42 then #51, each with its tick."""
        self.assertEqual(self.device_test("sample unticked").get("samples", "missing"),
                         [{"pr": 42, "ticked": True}, {"pr": 51, "ticked": False}])
        self.assertEqual(self.device_test("none").get("samples", "missing"),
                         [{"pr": 42, "ticked": False}, {"pr": 51, "ticked": False}])

    def test_results(self):
        """Planted bug "``ticked`` with a sample box unticked": every box ticked: ``ticked``;
        the accept box ticked and a sample box not: ``incomplete``; the accept box unticked:
        ``waiting``."""
        expected = {"all": ("ticked", True), "sample unticked": ("incomplete", True),
                    "only samples": ("waiting", False), "none": ("waiting", False)}
        for name, (result, accept) in expected.items():
            with self.subTest(case=name):
                found = self.device_test(name)
                self.assertEqual((found.get("result"), found.get("accept")), (result, accept))


if __name__ == "__main__":
    unittest.main()
