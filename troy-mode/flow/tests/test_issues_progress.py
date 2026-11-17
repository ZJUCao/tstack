"""Progress issues (F15 design 4, 13.1 "Progress issues"; interface note 4.1).

``troy_flow.py issues`` renders each feature's progress issue from the state
and lists the gh commands that make GitHub match it; the engine itself only
reads GitHub. ``status`` gives the issue's number in ``next.issue`` and the
count of pending changes.

Planted bugs of design 13.2 caught here:

- "a progress issue created for an accepted feature":
  ``CreateTests.test_next_feature_is_created_with_nothing_ticked`` and
  ``test_closed_issue_of_an_accepted_feature_is_left_alone``.
- "a stage ticked from an open PR": ``StageLineTests.test_open_stage_is_not_ticked``.
- "the skipped mock left unticked": ``StageLineTests.test_skipped_mock_is_ticked``.
- "a body edited when nothing changed": ``SyncTests.test_no_action_when_nothing_changed``
  and ``test_line_endings_and_trailing_space_do_not_count``.
- "Troy's closing left in place": ``SyncTests.test_closed_by_troy_is_reopened``.
- "a closed progress issue edited again":
  ``CreateTests.test_closed_issue_of_an_accepted_feature_is_left_alone``.
"""

import unittest
from dataclasses import replace

from flow_helpers import (
    F01, F02, F03, TWO, base_step, comments, custom_design, custom_design_step, pr, stage_pr,
    stage_step, stages, step,
)
from issues_helpers import (
    ALL_LABELS, BLOB, DETAILS, FOOT_EN, FOOT_ZH, STAGE_EN, STAGE_ZH, IssuesCase, all_pr,
    box_lines, gh_issue, issues_run, issues_runs, lines_of, nonblank, progress_issue,
    progress_marker, progress_title, project_files, requirements_pair, split_body, stage_prs,
    status_runs_with, zh_change_step,
)

THREE = (F01, F02, F03)
TEST_FIX = "[F01 test-fix] Wrong expected count in F01-T01"
NONE_SECTION = "None. The change adds no interface; section 3 lists the changed ones.\n"
PROTOTYPE = "docs/prototypes/F01-counter.md"
F01_DOCS = "docs/features/F01-count-words/"
REWORK_ZH = "需要返工（数空行）"
# Out-of-date bodies of F01's issue: with the 6/6 box ticked, and with it open.
FINAL_STALE = progress_marker("F01") + "\n- [x] 6/6 验收：#46，已合并\n\nOld text.\n"
OPEN_STALE = progress_marker("F01") + "\n- [ ] 6/6 验收：#46，进行中\n\nOld text.\n"


def base(features=TWO, extra=None, statuses=None):
    """The first commit, with a Chinese mirror that has a features table."""
    return base_step(project_files(features, statuses=statuses, extra=extra))


def fakes(**kwargs) -> dict:
    """Fakes keyword arguments with the three F15 labels already in the repository."""
    return {"labels": list(ALL_LABELS), **kwargs}


def box(number: int, done: bool, rest: str = "") -> str:
    """A Chinese stage line, for example ``- [x] 1/6 接口设计：#41，已合并``."""
    mark = "x" if done else " "
    return f"- [{mark}] {number}/6 {STAGE_ZH[number]}" + (f"：{rest}" if rest else "")


def stage_en(number: int, rest: str = "") -> str:
    """An English stage line, for example ``1/6 Interface design: #41, merged``."""
    return f"{number}/6 {STAGE_EN[number]}" + (f": {rest}" if rest else "")


def docs_line(lead: str, *links) -> str:
    """A documents line: the lead and each ``[label](full URL)``, joined by `` · ``."""
    return lead + " · ".join(f"[{label}]({BLOB}{path})" for label, path in links)


def stage6_with_status():
    """PR 6 of F01 that sets F01's status to "Ran for real on Troy's PC" in both files."""
    features = (replace(F01, status="Ran for real on Troy's PC"), F02)
    files = {f"{F01.folder}/acceptance.md": "# F01 accepted\n",
             **requirements_pair(features, "1.1", {"F01": "在 Troy 的电脑上真跑过"})}
    return step(F01.title(6), files)


def rework_steps() -> list:
    """F01's stages 1 to 3, then a change that marks F01 "Needs rework"."""
    return [base(), *stages(F01, 3),
            zh_change_step("Count blank lines", (replace(F01, status="Needs rework (Count "
                                                         "blank lines)"), F02),
                           statuses={"F01": REWORK_ZH})]


CASES = {
    "next": ([base(), *stages(F01, 6)], fakes(all_prs=stage_prs(F01, 6))),
    "dependency issue": ([base(), *stages(F01, 6)],
                         fakes(all_prs=stage_prs(F01, 6), all_issues=[
                             progress_issue(7, "F01", FINAL_STALE, state="CLOSED",
                                            reason="COMPLETED")])),
    "closed before render": ([base(), *stages(F01, 6)],
                             fakes(all_prs=stage_prs(F01, 6), all_issues=[
                                 progress_issue(7, "F01", OPEN_STALE, state="CLOSED",
                                                reason="COMPLETED")])),
    "open, 6/6 ticked": ([base(), *stages(F01, 6)],
                         fakes(all_prs=stage_prs(F01, 6), all_issues=[
                             progress_issue(7, "F01", FINAL_STALE)])),
    "merged stage PR": ([base(THREE, {PROTOTYPE: "# F01 counter\n"}), *stages(F01, 2),
                         stage_step(F03, 1, pr=51)],
                        fakes(all_prs=stage_prs(F01, 2) + [all_pr(51, F03.title(1))])),
    "open stage PR": ([base(THREE)], fakes(prs=[stage_pr(12, F03, 1)])),
    "merge styles": ([base(), stage_step(F01, 1), stage_step(F01, 2, "squash", 42),
                      stage_step(F01, 3, "merge", 43)], fakes(all_prs=stage_prs(F01, 3))),
    "no PR number": ([base(), *stages(F01, 2)], fakes(all_prs=[])),
    "review": ([base(), *stages(F01, 2)], fakes(
        prs=[stage_pr(43, F01, 3)],
        comments={43: comments("Developer attempt 1: failed\n\nruff: 2 errors",
                               "Code Reviewer review, round 1: changes-requested\n\n1. Naming.")},
        all_prs=stage_prs(F01, 2) + [all_pr(43, F01.title(3), "OPEN")])),
    "attempt": ([base(), *stages(F01, 4)], fakes(
        prs=[stage_pr(45, F01, 5)],
        comments={45: comments("Code Reviewer review, round 1: approved\n\nNone",
                               "Developer attempt 2: failed\n\nmypy: 1 error")},
        all_prs=stage_prs(F01, 4) + [all_pr(45, F01.title(5), "OPEN")])),
    "approve": ([base()], fakes(
        prs=[stage_pr(41, F01, 1)],
        comments={41: comments("Architect review, round 1: approved\n\nNone",
                               "Waiting for Troy: approve this PR")})),
    "approved": ([base()], fakes(
        prs=[stage_pr(41, F01, 1)],
        comments={41: comments("Architect review, round 1: approved\n\nNone",
                               "Waiting for Troy: approve this PR", "全按推荐")})),
    "question": ([base()], fakes(
        prs=[stage_pr(41, F01, 1)],
        comments={41: comments("Interface Designer review, round 1: needs-answer\n\nWhich?",
                               "Waiting for Troy: choose the output encoding")})),
    "escalation": ([base(), *stages(F01, 2)], fakes(
        prs=[stage_pr(43, F01, 3)],
        comments={43: comments("Code Reviewer review, round 3: changes-requested\n\n1. Naming.",
                               "Escalation: three review rounds without agreement\n\nWhere")},
        all_prs=stage_prs(F01, 2) + [all_pr(43, F01.title(3), "OPEN")])),
    "skipped mock": ([base(), custom_design_step(F01, custom_design(F01, NONE_SECTION)),
                      stage_step(F01, 2)], fakes(all_prs=stage_prs(F01, 2))),
    "rework": (rework_steps(), fakes(all_prs=stage_prs(F01, 3))),
    "redo": (rework_steps() + [stage_step(F01, 1)],
             fakes(all_prs=stage_prs(F01, 3) + [all_pr(57, F01.title(1))])),
    "side lines": ([base(), *stages(F01, 3)], fakes(
        prs=[pr(45, TEST_FIX, "troy-mode/f01-test-fix")],
        all_prs=stage_prs(F01, 3) + [all_pr(44, F01.title(4), "CLOSED"),
                                     all_pr(45, TEST_FIX, "OPEN")],
        all_issues=[gh_issue(50, "Real run of F01: wrong count", labels=("bug",)),
                    gh_issue(52, "Real run of F02: wrong total", labels=("bug",)),
                    gh_issue(53, "Real run of F010: other", labels=("bug",))])),
    "not next": ([base(), *stages(F01, 2)], fakes(
        all_prs=stage_prs(F01, 2),
        all_issues=[progress_issue(8, "F02"), progress_issue(9, "F09")])),
    "next again": ([base(), *stages(F01, 6)], fakes(
        all_prs=stage_prs(F01, 6),
        all_issues=[progress_issue(8, "F02", state="CLOSED", reason="NOT_PLANNED")])),
    "accepted": ([base(), *stages(F01, 5), stage6_with_status()], fakes(
        all_prs=stage_prs(F01, 6), all_issues=[progress_issue(7, "F01")])),
}


class ProgressCase(IssuesCase):
    """Runs every single-run case once, side by side."""

    outs: dict = {}

    @classmethod
    def setUpClass(cls):
        """Runs ``issues`` on one clone per case."""
        if not ProgressCase.outs:
            ProgressCase.outs = issues_runs(CASES)

    def actions(self, name: str) -> list:
        """The case's actions; the run must exit 0 and make only read calls."""
        out, fake, _ = self.outs[name]
        report = self.issues_report(out)
        self.assert_read_only(fake)
        return report["actions"]

    def project(self, name: str):
        """The case's clone."""
        return self.outs[name][2]

    def body(self, name: str, item: str) -> str:
        """The body of the case's create or edit action for one feature."""
        found = [a for a in self.actions(name)
                 if a["item"] == item and a["action"] in ("create", "edit")]
        self.assertEqual(len(found), 1, self.actions(name))
        body = self.body_of(found[0])
        self.assert_body_shape(body, progress_marker(item))
        return body

    def parts(self, name: str, item: str) -> tuple:
        """The non-blank Chinese and English lines of a rendered body."""
        chinese, english = split_body(self.body(name, item))
        return nonblank(chinese), nonblank(english)


class CreateTests(ProgressCase):
    """Which features get a progress issue (design 4.1; note 4.1's table)."""

    def test_next_feature_is_created_with_nothing_ticked(self):
        """Planted bug "created for an accepted feature": F01 accepted gets none; F02, next,
        gets one with every line of the note's shape."""
        actions = self.actions("next")
        self.assertEqual(len(actions), 1, actions)
        self.assert_create(actions[0], self.project("next"), "progress", "F02",
                           progress_title(F02))
        self.assertEqual(progress_title(F02), "F02 数行数 / Count lines")
        self.assertEqual(nonblank(lines_of(self.body("next", "F02"))), [
            progress_marker("F02"), "**F02 数行数** · v0.1 · 第 1 步，共 6 步", "等你：没有。",
            *[box(n, False) for n in range(1, 7)], "依赖：F01（已验收）",
            docs_line("文档：", ("需求", "docs/requirements.zh-CN.md")), FOOT_ZH, DETAILS,
            "**F02 Count lines** · v0.1 · stage 1 of 6", "Waiting for you: nothing.",
            *[stage_en(n) for n in range(1, 7)], "Depends on: F01 (accepted)",
            docs_line("Documents: ", ("requirements", "docs/requirements.md")), FOOT_EN,
            "</details>"])

    def test_closed_issue_of_an_accepted_feature_is_left_alone(self):
        """Planted bugs "created for an accepted feature" and "a closed progress issue edited
        again": F01's closed #7, its 6/6 box ticked but its text old, gets nothing; F02's
        body names it as F01's issue."""
        actions = self.actions("dependency issue")
        self.assertEqual([(a["action"], a["item"]) for a in actions], [("create", "F02")])
        chinese, english = self.parts("dependency issue", "F02")
        self.assertIn("依赖：F01（#7，已验收）", chinese)
        self.assertIn("Depends on: F01 (#7, accepted)", english)

    def test_feature_with_a_merged_stage_pr_gets_one(self):
        """F01 is next and F03 has a merged stage 1: both are created, F02 is not."""
        actions = self.actions("merged stage PR")
        self.assertEqual([(a["action"], a["item"]) for a in actions],
                         [("create", "F01"), ("create", "F03")])
        self.assert_create(actions[1], self.project("merged stage PR"), "progress", "F03",
                           "F03 数字符 / Count characters")
        chinese, english = self.parts("merged stage PR", "F03")
        self.assert_in_order(chinese, ["**F03 数字符** · v0.1 · 第 2 步，共 6 步",
                                       box(1, True, "#51，已合并"), box(2, False),
                                       "依赖：F01（进行中）"])
        self.assert_in_order(english, ["**F03 Count characters** · v0.1 · stage 2 of 6",
                                       stage_en(1, "#51, merged"), stage_en(2),
                                       "Depends on: F01 (in progress)"])

    def test_feature_with_an_open_stage_pr_gets_one(self):
        """F03 has an open stage 1 PR #12: it is created next to F01, F02 is not."""
        actions = self.actions("open stage PR")
        self.assertEqual([(a["action"], a["item"]) for a in actions],
                         [("create", "F01"), ("create", "F03")])
        chinese, english = self.parts("open stage PR", "F03")
        self.assertIn(box(1, False, "#12，进行中"), chinese)
        self.assertIn(stage_en(1, "#12, open"), english)
        self.assertEqual(box_lines(chinese), [box(1, False, "#12，进行中"),
                                              *[box(n, False) for n in range(2, 7)]])

    def test_documents_and_no_dependency(self):
        """F01: links to the files on main, the mirror's in Chinese, a prototype in both."""
        chinese, english = self.parts("merged stage PR", "F01")
        self.assertIn("依赖：没有。", chinese)
        self.assertIn("Depends on: none.", english)
        self.assertIn(docs_line("文档：", ("需求", "docs/requirements.zh-CN.md"),
                                ("设计", F01_DOCS + "design.zh-CN.md"),
                                ("测试计划", F01_DOCS + "test-plan.zh-CN.md"),
                                ("原型", PROTOTYPE)), chinese)
        self.assertIn(docs_line("Documents: ", ("requirements", "docs/requirements.md"),
                                ("design", F01_DOCS + "design.md"),
                                ("test plan", F01_DOCS + "test-plan.md"),
                                ("prototype", PROTOTYPE)), english)


class StageLineTests(ProgressCase):
    """The boxes and the stage lines (design 4.2; note 4.1)."""

    def test_ticks_from_rebase_squash_and_merge_subjects(self):
        """Stages 1 to 3 merged three ways: three ticks with their PRs, stage 4 next."""
        chinese, english = self.parts("merge styles", "F01")
        self.assertEqual(box_lines(chinese), [
            box(1, True, "#41，已合并"), box(2, True, "#42，已合并"), box(3, True, "#43，已合并"),
            box(4, False), box(5, False), box(6, False)])
        self.assert_in_order(english, ["**F01 Count words** · v0.1 · stage 4 of 6",
                                       stage_en(1, "#41, merged"), stage_en(2, "#42, merged"),
                                       stage_en(3, "#43, merged"), stage_en(4)])
        self.assertIn("**F01 数单词** · v0.1 · 第 4 步，共 6 步", chinese)

    def test_merged_stage_without_a_pr_number(self):
        """No merged PR with the stage's title: ``已合并`` alone, still ticked."""
        chinese, english = self.parts("no PR number", "F01")
        self.assertEqual(box_lines(chinese)[:3],
                         [box(1, True, "已合并"), box(2, True, "已合并"), box(3, False)])
        self.assert_in_order(english, [stage_en(1, "merged"), stage_en(2, "merged")])

    def test_open_stage_is_not_ticked(self):
        """Planted bug "a stage ticked from an open PR": #43 open, with its last review."""
        chinese, english = self.parts("review", "F01")
        self.assertEqual(box_lines(chinese), [
            box(1, True, "#41，已合并"), box(2, True, "#42，已合并"),
            box(3, False, "#43，进行中。代码审查员第 1 轮：要求修改"),
            box(4, False), box(5, False), box(6, False)])
        self.assertIn(stage_en(3, "#43, open. Code Reviewer, round 1: changes requested"),
                      english)
        self.assertIn("等你：没有。", chinese)

    def test_last_heading_may_be_an_attempt(self):
        """The Developer's failed attempt after a review: the attempt is shown."""
        chinese, english = self.parts("attempt", "F01")
        self.assertIn(box(5, False, "#45，进行中。开发工程师第 2 次尝试：失败"), chinese)
        self.assertIn(stage_en(5, "#45, open. Developer, attempt 2: failed"), english)

    def test_skipped_mock_is_ticked(self):
        """Planted bug "the skipped mock left unticked": stage 3 ticked as skipped, stage 4."""
        chinese, english = self.parts("skipped mock", "F01")
        self.assertEqual(box_lines(chinese)[:4], [
            box(1, True, "#41，已合并"), box(2, True, "#42，已合并"),
            box(3, True, "跳过：没有新接口"), box(4, False)])
        self.assertIn(stage_en(3, "skipped: no new interface"), english)
        self.assertIn("**F01 数单词** · v0.1 · 第 4 步，共 6 步", chinese)
        self.assertIn("**F01 Count words** · v0.1 · stage 4 of 6", english)

    def test_rework_shows_the_status(self):
        """F01 in rework after a change: stages 1 to 3 ticked and the Status cell shown."""
        chinese, english = self.parts("rework", "F01")
        self.assertEqual([line[:5] for line in box_lines(chinese)],
                         ["- [x]"] * 3 + ["- [ ]"] * 3)
        self.assertIn(f"状态：{REWORK_ZH}", chinese)
        self.assertIn("Status: Needs rework (Count blank lines)", english)

    def test_redo_unticks_the_later_stages(self):
        """The design merged again (#57) after the change: only stage 1 is ticked."""
        chinese, english = self.parts("redo", "F01")
        self.assertEqual(box_lines(chinese), [box(1, True, "#57，已合并"),
                                              *[box(n, False) for n in range(2, 7)]])
        self.assertIn(stage_en(1, "#57, merged"), english)
        self.assertIn("**F01 数单词** · v0.1 · 第 2 步，共 6 步", chinese)

    def test_status_line_absent_while_not_started(self):
        """The Status cell "Not started" shows no status line."""
        chinese, english = self.parts("merge styles", "F01")
        self.assertFalse([line for line in chinese if line.startswith("状态：")], chinese)
        self.assertFalse([line for line in english if line.startswith("Status:")], english)


class WaitingTests(ProgressCase):
    """"Waiting for you" from the open stage PR's comments (design 4.2; note 4.1)."""

    def test_approval_request(self):
        """``Waiting for Troy: approve this PR`` unanswered: approve #41."""
        chinese, english = self.parts("approve", "F01")
        self.assertIn("等你：批准 #41；要决定的事在它描述的开头。", chinese)
        self.assertIn("Waiting for you: approve #41; what to decide is at the top of its "
                      "description.", english)
        self.assertIn(box(1, False, "#41，进行中。架构师第 1 轮：通过"), chinese)
        self.assertIn(stage_en(1, "#41, open. Architect, round 1: approved"), english)

    def test_troys_reply_ends_the_wait(self):
        """Pair: Troy's "全按推荐" after the request: nothing waits."""
        chinese, english = self.parts("approved", "F01")
        self.assertIn("等你：没有。", chinese)
        self.assertIn("Waiting for you: nothing.", english)

    def test_question(self):
        """Another ``Waiting for Troy: <q>``: answer the question on #41."""
        chinese, english = self.parts("question", "F01")
        self.assertIn("等你：回答 #41 上的问题：choose the output encoding。", chinese)
        self.assertIn("Waiting for you: answer the question on #41: choose the output encoding.",
                      english)
        self.assertIn(box(1, False, "#41，进行中。接口设计师第 1 轮：需要回答"), chinese)
        self.assertIn(stage_en(1, "#41, open. Interface Designer, round 1: needs an answer"),
                      english)

    def test_escalation(self):
        """An escalation as the last comment: its trigger, with the PR."""
        chinese, english = self.parts("escalation", "F01")
        self.assertIn("等你：#43 上的上报：three review rounds without agreement。", chinese)
        self.assertIn("Waiting for you: the escalation on #43: three review rounds without "
                      "agreement.", english)
        self.assertIn(box(3, False, "#43，进行中。代码审查员第 3 轮：要求修改"), chinese)


class OtherLinesTests(ProgressCase):
    """Side PRs, real-run bugs, and stage PRs closed unmerged (design 4.2)."""

    def test_side_pr_bug_and_closed_pr(self):
        """The test-fix PR, F01's real-run bug (not F02's or F010's), and #44 closed."""
        chinese, english = self.parts("side lines", "F01")
        self.assertIn(f"附带 PR：#45 {TEST_FIX}（进行中）", chinese)
        self.assertIn("实际运行发现的 bug：#50 Real run of F01: wrong count（未解决）", chinese)
        self.assertIn(f"关闭未合并的 PR：#44 {F01.title(4)}", chinese)
        self.assertIn(f"Side PRs: #45 {TEST_FIX} (open)", english)
        self.assertIn("Real-run bugs: #50 Real run of F01: wrong count (open)", english)
        self.assertIn(f"Closed without merging: #44 {F01.title(4)}", english)
        text = "\n".join(chinese + english)
        self.assertNotIn("#52", text)
        self.assertNotIn("#53", text)
        self.assertIn(box(4, False), chinese)

    def test_side_lines_absent_without_side_prs(self):
        """Pair: none of the three lines without such PRs or bugs."""
        chinese, english = self.parts("merge styles", "F01")
        for lead in ("附带 PR：", "实际运行发现的 bug：", "关闭未合并的 PR："):
            self.assertFalse([line for line in chinese if line.startswith(lead)], lead)
        for lead in ("Side PRs:", "Real-run bugs:", "Closed without merging:"):
            self.assertFalse([line for line in english if line.startswith(lead)], lead)


class LifecycleTests(ProgressCase):
    """Closing, reopening, and acceptance (design 4.1, 4.4, 4.5; note 4.1's table)."""

    def test_no_longer_next_is_closed_as_not_planned(self):
        """F02 with no stage PR is not next: #8 closed as not planned; F09 left the table."""
        actions = self.actions("not next")
        self.assertEqual([(a["action"], a["item"]) for a in actions[:2]],
                         [("create", "F01"), ("close", "F02")])
        self.assert_close(actions[1], "progress", "F02", 8, "not planned")
        f09 = [a for a in actions if a["item"] == "F09"]
        self.assertEqual(len(f09), 1, actions)
        self.assert_close(f09[0], "progress", "F09", 9, "not planned")
        self.assertEqual(len(actions), 3, actions)

    def test_next_again_is_reopened_and_rebuilt(self):
        """F02 next again, its issue closed as not planned: reopen, then edit."""
        actions = self.actions("next again")
        self.assertEqual(len(actions), 2, actions)
        self.assert_reopen(actions[0], "progress", "F02", 8)
        self.assert_edit(actions[1], self.project("next again"), "progress", "F02", 8,
                         progress_title(F02))

    def test_closed_by_pr_6_is_rendered_once_more(self):
        """PR 6's ``Closes #7`` closed it before the sync: an edit to six ticks, no close or
        reopen (design 4.5; note 4.1)."""
        actions = self.actions("closed before render")
        self.assertEqual([(a["action"], a["item"]) for a in actions],
                         [("edit", "F01"), ("create", "F02")])
        self.assert_edit(actions[0], self.project("closed before render"), "progress", "F01",
                         7, progress_title(F01))
        chinese, _ = self.parts("closed before render", "F01")
        self.assertEqual(box_lines(chinese),
                         [box(n, True, f"#{40 + n}，已合并") for n in range(1, 7)])

    def test_open_with_six_ticks_is_only_closed(self):
        """Open, its 6/6 box already ticked: closed as completed with no edit."""
        actions = self.actions("open, 6/6 ticked")
        self.assertEqual([(a["action"], a["item"]) for a in actions],
                         [("close", "F01"), ("create", "F02")])
        self.assert_close(actions[0], "progress", "F01", 7, "completed")

    def test_closed_as_completed_after_pr_6(self):
        """PR 6 merged, #7 still open: rendered once more with six ticks, then closed."""
        actions = self.actions("accepted")
        self.assertEqual([(a["action"], a["item"]) for a in actions],
                         [("edit", "F01"), ("close", "F01"), ("create", "F02")])
        self.assert_edit(actions[0], self.project("accepted"), "progress", "F01", 7,
                         progress_title(F01))
        self.assert_close(actions[1], "progress", "F01", 7, "completed")
        chinese, english = self.parts("accepted", "F01")
        self.assertEqual(box_lines(chinese),
                         [box(n, True, f"#{40 + n}，已合并") for n in range(1, 7)])
        self.assertIn("**F01 数单词** · v0.1 · 第 6 步，共 6 步", chinese)
        self.assertIn("状态：在 Troy 的电脑上真跑过", chinese)
        self.assertIn("Status: Ran for real on Troy's PC", english)


class SyncTests(IssuesCase):
    """A second sync against the issue the first one rendered (design 3.2, 4.4)."""

    @classmethod
    def setUpClass(cls):
        """Renders F01's body once, then syncs against variants of that issue."""
        steps = [base(), *stages(F01, 2)]
        cls.steps = steps
        first, _, cls.first_project = issues_run(steps, fakes(all_prs=stage_prs(F01, 2)))
        cls.first = first
        action = first.report["actions"][0] if first.report else {}
        cls.rebuilt = (action.get("body_file") and
                       open(action["body_file"], "rb").read().decode("utf-8")) or ""
        cls.title = action.get("title") or ""
        edited = cls.rebuilt.replace(box(6, False), box(6, True))
        crlf = cls.rebuilt.replace("\n", "\r\n") + "\r\n  \r\n"
        variants = {
            "same": progress_issue(7, "F01", cls.rebuilt, cls.title),
            "crlf": progress_issue(7, "F01", crlf, cls.title),
            "edited body": progress_issue(7, "F01", edited, cls.title),
            "edited title": progress_issue(7, "F01", cls.rebuilt, "F01 counting"),
            "closed": progress_issue(7, "F01", cls.rebuilt, cls.title, "CLOSED", "COMPLETED"),
            "closed and edited": progress_issue(7, "F01", edited, cls.title, "CLOSED",
                                                "COMPLETED"),
        }
        cls.outs = issues_runs({name: (steps, fakes(all_prs=stage_prs(F01, 2),
                                                    all_issues=[found]))
                                for name, found in variants.items()})
        cls.status = status_runs_with({
            "none": (steps, fakes(all_prs=stage_prs(F01, 2))),
            "same": (steps, fakes(all_prs=stage_prs(F01, 2),
                                  all_issues=[variants["same"]])),
            "edited body": (steps, fakes(all_prs=stage_prs(F01, 2),
                                         all_issues=[variants["edited body"]])),
        })

    def setUp(self):
        """The first sync must have created F01's issue."""
        report = self.issues_report(self.first)
        self.assertEqual([(a["action"], a["item"]) for a in report["actions"]],
                         [("create", "F01")])
        self.assertNotEqual(self.rebuilt, "")

    def actions(self, name: str) -> list:
        """A variant's actions; the run must exit 0 and only read GitHub."""
        out, fake, _ = self.outs[name]
        self.assert_read_only(fake)
        return self.issues_report(out)["actions"]

    def test_no_action_when_nothing_changed(self):
        """Planted bug "a body edited when nothing changed": the same title and body."""
        self.assertEqual(self.actions("same"), [])

    def test_line_endings_and_trailing_space_do_not_count(self):
        """Planted bug "edited when nothing changed": CRLF and trailing white space."""
        self.assertEqual(self.actions("crlf"), [])

    def test_troys_edit_of_the_body_is_replaced(self):
        """Troy ticked stage 6 on the phone: an edit puts troy-mode's text back."""
        actions = self.actions("edited body")
        self.assertEqual(len(actions), 1, actions)
        self.assert_edit(actions[0], self.outs["edited body"][2], "progress", "F01", 7,
                         progress_title(F01))
        self.assertEqual(self.body_of(actions[0]).rstrip(), self.rebuilt.rstrip())

    def test_troys_edit_of_the_title_is_replaced(self):
        """Troy renamed the issue: an edit with the rebuilt title."""
        actions = self.actions("edited title")
        self.assertEqual(len(actions), 1, actions)
        self.assert_edit(actions[0], self.outs["edited title"][2], "progress", "F01", 7,
                         progress_title(F01))

    def test_closed_by_troy_is_reopened(self):
        """Planted bug "Troy's closing left in place": reopened, with no edit."""
        actions = self.actions("closed")
        self.assertEqual(len(actions), 1, actions)
        self.assert_reopen(actions[0], "progress", "F01", 7)

    def test_closed_and_edited_is_reopened_then_edited(self):
        """Closed and edited: reopen first, then edit."""
        actions = self.actions("closed and edited")
        self.assertEqual([a["action"] for a in actions], ["reopen", "edit"])
        self.assert_edit(actions[1], self.outs["closed and edited"][2], "progress", "F01", 7,
                         progress_title(F01))

    def test_status_counts_the_pending_changes(self):
        """``issues.pending``: 1 with no issue, 0 when it matches, 1 after Troy's edit."""
        for name, count in (("none", 1), ("same", 0), ("edited body", 1)):
            with self.subTest(case=name):
                out, fake, _ = self.status[name]
                report = self.report_of(out, 0, "status")
                self.assertEqual((report.get("issues") or {}).get("pending"), count)
                self.assert_read_only(fake)

    def test_status_names_the_issue_in_next(self):
        """``next.issue`` on F01's stage entry is the open progress issue #7."""
        report = self.report_of(self.status["same"][0], 0, "status")
        self.assert_next(report, action="stage", item="F01", stage=3, task="DV1",
                         title=F01.title(3), branch=F01.branch(3), merged_by="f07", issue=7)


class NextIssueTests(IssuesCase):
    """``next.issue`` on ``stage`` and ``continue-pr`` entries (note section 3)."""

    @classmethod
    def setUpClass(cls):
        """Runs status with F01 at stage 3 and different progress issues."""
        steps = [base(), *stages(F01, 2)]
        cls.outs = status_runs_with({
            "continue": (steps, fakes(prs=[stage_pr(43, F01, 3)],
                                      all_issues=[progress_issue(7, "F01")])),
            "closed only": (steps, fakes(all_issues=[
                progress_issue(5, "F01", state="CLOSED", reason="NOT_PLANNED"),
                progress_issue(9, "F01", state="CLOSED", reason="NOT_PLANNED")])),
            "open preferred": (steps, fakes(all_issues=[
                progress_issue(5, "F01"),
                progress_issue(9, "F01", state="CLOSED", reason="NOT_PLANNED")])),
            "other feature": (steps, fakes(all_issues=[progress_issue(8, "F02")])),
        })

    def report(self, name: str) -> dict:
        """The case's status report, exit 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def test_continue_pr_names_the_issue(self):
        """The open stage PR #43 of F01: ``continue-pr`` with issue 7."""
        self.assert_next(self.report("continue"), action="continue-pr", pr=43, item="F01",
                         stage=3, task="DV1", title=F01.title(3), branch=F01.branch(3),
                         merged_by="f07", issue=7)

    def test_newest_closed_when_none_is_open(self):
        """Two closed issues: the newer, #9."""
        self.assert_next(self.report("closed only"), action="stage", item="F01", stage=3,
                         task="DV1", title=F01.title(3), branch=F01.branch(3), merged_by="f07",
                         issue=9)

    def test_open_issue_preferred(self):
        """Open #5 and closed #9: #5."""
        self.assert_next(self.report("open preferred"), action="stage", item="F01", stage=3,
                         task="DV1", title=F01.title(3), branch=F01.branch(3), merged_by="f07",
                         issue=5)

    def test_another_features_issue_is_not_named(self):
        """Pair: only F02 has an issue: ``next.issue`` is null for F01's stage."""
        self.assert_next(self.report("other feature"), action="stage", item="F01", stage=3,
                         task="DV1", title=F01.title(3), branch=F01.branch(3), merged_by="f07",
                         issue=None)


if __name__ == "__main__":
    unittest.main()
