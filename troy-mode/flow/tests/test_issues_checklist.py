"""The device-test checklist (F15 design 6, 13.1 "Checklist"; interface note 3 and 4.2).

``issues`` creates one checklist per version once a release test passed,
with the scenarios Troy runs in both languages and the accept box last;
``status`` reads Troy's ticks into ``issues.device_test``.

Planted bugs of design 13.2 caught here:

- "Troy's ticks lost at a sync": ``TickTests.test_ticks_alone_cause_no_edit`` and
  ``NewRunTests.test_new_run_keeps_the_other_ticks``.
- "the accept box kept at a new run": ``NewRunTests.test_new_run_clears_the_accept_box``.
- "``ticked`` with one scenario unticked": ``TickTests.test_results``.
- "a checklist ticked by the engine": ``CreateTests.test_scenarios_in_both_languages`` and
  ``NewRunTests.test_engine_never_ticks_a_box``.
"""

import unittest

from issues_helpers import (
    BLOB, COMMIT1, COMMIT2, EN_PERF, EN_SCENARIOS, HOW_EN, HOW_ZH, TAG, ZH_PERF,
    ZH_SCENARIOS, IssuesCase, box_lines, checklist_issue, checklist_marker, checklist_title,
    issues_runs, lines_of, nonblank, passed, patch_fakes, patched_steps, plan_pair,
    release_fakes, release_steps, released_steps, split_body, status_run, status_runs_with,
    tick, waiting,
)
from flow_helpers import release_title

PLAN_EN = "docs/versions/v0.1/test-plan.md"
PLAN_ZH = "docs/versions/v0.1/test-plan.zh-CN.md"
TROY_FAILED = "Release test by Troy, run 1: failed\n\nTroy: v0.1-S02 prints 0 on the laptop."
CLAUDE_ONLY = plan_pair(scenarios=([row for row in EN_SCENARIOS if row[2] == "Claude"],
                                   [row for row in ZH_SCENARIOS if row[2] == "Claude"]),
                        perf=([row for row in EN_PERF if row[5] == "Claude"],
                              [row for row in ZH_PERF if row[5] == "Claude"]))
S02, S04, S05 = "**v0.1-S02 ", "**v0.1-S04 ", "**v0.1-S05 "
ACCEPT = "**我接受 v0.1.0。**"
BOXES = [f"- [ ] {S02}在 Troy 的笔记本上统计**", f"- [ ] {S04}在 Windows Terminal 里读中文**",
         f"- [ ] {S05}PT02**", f"- [ ] {ACCEPT}"]
STEP_TEXT = ("Release v0.1.0: Troy tests the version on Troy's devices with checklist #9 and "
             "accepts it (PR #30).")


def release_with(*bodies, issue=None) -> dict:
    """Fakes for release PR #30 with its comments and, optionally, one checklist issue."""
    return release_fakes(*bodies, all_issues=[issue] if issue else [])


SINGLE = {
    "create": (release_steps(), release_with(passed(1, COMMIT1), waiting())),
    "patch": (patched_steps(), patch_fakes(passed(1, COMMIT1), waiting("v0.1.1")),
              ["--device-test-scenarios", "v0.1-S02,v0.1-S05"]),
    "Claude only": (release_steps(CLAUDE_ONLY), release_with(passed(1, COMMIT1), waiting())),
    "released": (released_steps(), {"all_issues": [checklist_issue(9, TAG)],
                                    "labels": ["bug", "idea", "progress", "device-test"]}),
    "no release PR": (release_steps(), {"all_issues": [checklist_issue(9, TAG)],
                                        "labels": ["bug", "idea", "progress", "device-test"]}),
}


class ChecklistCase(IssuesCase):
    """Runs the single-run cases once, then the cases built on the bodies they render."""

    outs: dict = {}
    later: dict = {}
    states: dict = {}
    bodies: dict = {}
    ticked: dict = {}

    @classmethod
    def setUpClass(cls):
        """Renders the checklists, then syncs and reads status against ticked copies."""
        if ChecklistCase.outs:
            return
        ChecklistCase.outs = issues_runs(SINGLE)
        bodies = {}
        for name in ("create", "patch"):
            report = ChecklistCase.outs[name][0].report or {}
            files = [a.get("body_file") for a in report.get("actions", [])
                     if a.get("kind") == "device-test" and a.get("body_file")]
            bodies[name] = open(files[0], "rb").read().decode("utf-8") if files else ""
        ChecklistCase.bodies = bodies
        if not bodies["create"]:
            return
        body = bodies["create"]
        all_ticked = tick(tick(tick(tick(body, S02), S04, "X"), S05), ACCEPT)
        incomplete = tick(tick(tick(body, S02), S04), ACCEPT)
        scenarios_only = tick(tick(tick(body, S02), S04), S05)
        before_failure = tick(tick(tick(body, S02), S04), ACCEPT)
        ChecklistCase.ticked = {"waiting": body, "ticked": all_ticked, "incomplete": incomplete,
                                "scenarios only": scenarios_only, "new run": before_failure}
        run1 = (passed(1, COMMIT1), waiting())
        ChecklistCase.later = issues_runs({
            "ticked": (release_steps(), release_with(*run1, issue=checklist_issue(9, TAG,
                                                                                 all_ticked))),
            "closed": (release_steps(), release_with(*run1, issue=checklist_issue(
                9, TAG, body, state="CLOSED", reason="COMPLETED"))),
            "new run": (release_steps(), release_with(
                *run1, TROY_FAILED, passed(2, COMMIT2), waiting(),
                issue=checklist_issue(9, TAG, before_failure))),
            "patch kept": (patched_steps(), patch_fakes(
                passed(1, COMMIT1), waiting("v0.1.1"),
                all_issues=[checklist_issue(61, "v0.1.1", bodies["patch"])])),
        })
        ChecklistCase.states = status_runs_with({
            name: (release_steps(), release_with(*run1, issue=checklist_issue(9, TAG, text)))
            for name, text in ChecklistCase.ticked.items() if name != "new run"})

    def actions(self, outs: dict, name: str) -> list:
        """A case's actions; the run must exit 0 and only read GitHub."""
        self.assertIn(name, outs, "the first sync rendered no checklist: "
                      + self.outs["create"][0].describe())
        out, fake, _ = outs[name]
        self.assert_read_only(fake)
        return self.issues_report(out)["actions"]

    def rendered(self, name: str) -> str:
        """A rendered checklist body of a first-run case, with the common shape checked."""
        if not self.bodies.get(name):
            self.fail("no checklist rendered: " + self.outs[name][0].describe())
        tag = "v0.1.1" if name == "patch" else TAG
        self.assert_body_shape(self.bodies[name], checklist_marker(tag))
        return self.bodies[name]


class CreateTests(ChecklistCase):
    """Created at ``troy-test`` with Troy's scenarios (design 6.1, 6.2; note 4.2)."""

    def test_created_once_a_release_test_passed(self):
        """Release PR #30 with run 1 passed: one ``create`` with the checklist's title."""
        actions = self.actions(self.outs, "create")
        self.assertEqual(len(actions), 1, actions)
        self.assert_create(actions[0], self.outs["create"][2], "device-test", TAG,
                           checklist_title(TAG))
        self.assertEqual(checklist_title(TAG), "v0.1.0 在你的设备上测试 / Test v0.1.0 on your devices")
        self.assertIs(actions[0]["new_run"], False)

    def test_head_lines(self):
        """The run, the commit's first 7 characters, the links, and the features, both parts."""
        chinese, english = (nonblank(part) for part in split_body(self.rendered("create")))
        self.assertEqual(chinese[:5], [
            checklist_marker(TAG), "**在你的设备上测试 v0.1.0** · 第 1 轮 · 要测的提交：34a7728",
            f"发布 PR：#30 · [更新记录]({BLOB}CHANGELOG.zh-CN.md) · [版本测试方案]({BLOB}{PLAN_ZH})",
            "功能：F01 数单词（在 main 上通过测试）；F02 数行数（在 main 上通过测试）", HOW_ZH])
        self.assertEqual(english[:4], [
            "**Test v0.1.0 on your devices** · run 1 · commit to test: 34a7728",
            f"Release PR: #30 · [changelog]({BLOB}CHANGELOG.md) · "
            f"[version test plan]({BLOB}{PLAN_EN})",
            "Features: F01 Count words (Passes tests on main); F02 Count lines (Passes tests on "
            "main)", HOW_EN])

    def test_scenarios_in_both_languages(self):
        """Planted bug "ticked by the engine": Troy's rows of sections 2 and 3 in plan order,
        nothing ticked, the accept box last; Claude's rows left out."""
        chinese, english = split_body(self.rendered("create"))
        self.assertEqual(box_lines(chinese), BOXES)
        self.assert_in_order(chinese, [BOXES[0], "  步骤：打开终端，运行 wc notes.txt",
                                       "  预期：显示统计结果", BOXES[1],
                                       "  步骤：在 Windows Terminal 里对中文文件运行 wc",
                                       "  预期：显示统计结果，中文可读", BOXES[2],
                                       "  设备：Troy 的笔记本。",
                                       "  步骤：负载：100 MB 文件；持续时间：3 次",
                                       "  预期：PT02", BOXES[3]])
        self.assert_in_order(english, ["v0.1-S02 Count on Troy's laptop",
                                       "v0.1-S04 Read Chinese text in Windows Terminal",
                                       "v0.1-S05 PT02",
                                       "Device: Troy's laptop. Steps: Load: 100 MB file; "
                                       "duration: 3 runs Expected: PT02"])
        text = "\n".join(chinese + english)
        for left_out in ("v0.1-S01", "v0.1-S03", "统计单词和行数", "Count words and lines"):
            self.assertNotIn(left_out, text)

    def test_device_lines_name_troys_devices(self):
        """A scenario's devices are the plan's devices Troy runs, from each language's file."""
        chinese, english = split_body(self.rendered("create"))
        zh = chinese[chinese.index(BOXES[0]) + 1]
        self.assertTrue(zh.startswith("  设备：") and zh.endswith("。"), zh)
        self.assertLess(zh.index("Troy 的笔记本"), zh.index("Troy 的手机"))
        self.assertIn("、", zh)
        self.assertNotIn("Troy 的电脑", zh)
        en = english[english.index("v0.1-S02 Count on Troy's laptop") + 1]
        self.assertTrue(en.startswith("Device: "), en)
        self.assertTrue(en.endswith("Steps: Open a terminal and run wc notes.txt Expected: "
                                    "Prints the count"), en)
        self.assertLess(en.index("Troy's laptop"), en.index("Troy's phone"))
        self.assertNotIn("Troy's PC", en)

    def test_only_the_accept_box_without_troys_scenarios(self):
        """A plan whose every row Claude runs: one box, the accept box (design 6.1)."""
        actions = self.actions(self.outs, "Claude only")
        self.assertEqual([(a["action"], a["kind"]) for a in actions], [("create", "device-test")])
        chinese, _ = split_body(self.body_of(actions[0]))
        self.assertEqual(box_lines(chinese), [f"- [ ] {ACCEPT}"])

    def test_patch_keeps_the_named_scenarios(self):
        """A patch: only the scenarios ``--device-test-scenarios`` names, in a marker line."""
        actions = self.actions(self.outs, "patch")
        self.assertEqual(len(actions), 1, actions)
        self.assert_create(actions[0], self.outs["patch"][2], "device-test", "v0.1.1",
                           checklist_title("v0.1.1"))
        lines = lines_of(self.rendered("patch"))
        self.assertEqual(lines[1], "<!-- troy-mode: scenarios v0.1-S02,v0.1-S05 -->")
        self.assertIn("**在你的设备上测试 v0.1.1** · 第 1 轮 · 要测的提交：34a7728", lines)
        self.assertTrue([line for line in lines if line.startswith("发布 PR：#60 · ")], lines)
        self.assertEqual(box_lines(split_body(self.rendered("patch"))[0]),
                         [BOXES[0], BOXES[2], "- [ ] **我接受 v0.1.1。**"])

    def test_patch_scenarios_read_back_at_the_next_sync(self):
        """The next sync, without the option, reads the list back: nothing to change."""
        self.assertEqual(self.actions(self.later, "patch kept"), [])


class TickTests(ChecklistCase):
    """Troy's ticks (design 6.3; note sections 3 and 4.2)."""

    def device_test(self, name: str) -> dict:
        """The case's ``issues.device_test``."""
        self.assertIn(name, self.states, "the first sync rendered no checklist: "
                      + self.outs["create"][0].describe())
        out, fake, _ = self.states[name]
        report = self.report_of(out, 0, "status")
        self.assert_read_only(fake)
        return (report.get("issues") or {}).get("device_test")

    def test_results(self):
        """Planted bug "``ticked`` with one scenario unticked": the three results."""
        expected = {
            "waiting": ([False, False, False], False, "waiting"),
            "ticked": ([True, True, True], True, "ticked"),
            "incomplete": ([True, True, False], True, "incomplete"),
            "scenarios only": ([True, True, True], False, "waiting"),
        }
        for name, (ticks, accept, result) in expected.items():
            with self.subTest(case=name):
                # F18 part 2 (contract 7): device_test gains samples, [] without sample boxes.
                self.assertEqual(self.device_test(name), {
                    "number": 9, "tag": TAG, "run": 1,
                    "scenarios": [{"id": scenario, "ticked": done}
                                  for scenario, done in zip(("v0.1-S02", "v0.1-S04",
                                                             "v0.1-S05"), ticks)],
                    "samples": [], "accept": accept, "result": result})

    def test_release_entry_names_the_checklist(self):
        """``next.issue`` on the ``troy-test`` release entry is checklist #9."""
        self.device_test("waiting")
        report = self.report_of(self.states["waiting"][0], 0, "status")
        self.assert_next(report, action="release", step="troy-test", item="v0.1", tag=TAG,
                         pr=30, title=release_title(TAG), branch="troy-mode/release-v0.1.0",
                         merged_by="f07", issue=9)

    def test_release_step_text_names_the_checklist(self):
        """The text report's release step names checklist #9 and PR #30 (note section 3)."""
        self.assertIn("waiting", self.ticked, "the first sync rendered no checklist")
        out, _, _ = status_run(release_steps(), release_with(
            passed(1, COMMIT1), waiting(), issue=checklist_issue(9, TAG, self.ticked["waiting"])),
            json_report=False)
        self.assert_exit(out, 0)
        self.assertIn(STEP_TEXT, out.stdout)

    def test_ticks_alone_cause_no_edit(self):
        """Planted bug "Troy's ticks lost at a sync": every box ticked, no action."""
        self.assertEqual(self.actions(self.later, "ticked"), [])

    def test_closed_while_the_release_is_open_is_reopened(self):
        """Troy closed the checklist while the release PR is open: reopened, not edited."""
        actions = self.actions(self.later, "closed")
        self.assertEqual(len(actions), 1, actions)
        self.assert_reopen(actions[0], "device-test", TAG, 9)


class NewRunTests(ChecklistCase):
    """A new run after Troy's failure (design 6.3; note 4.2)."""

    def edited(self) -> tuple:
        """The new run's one edit action and its Chinese and English parts."""
        actions = self.actions(self.later, "new run")
        self.assertEqual(len(actions), 1, actions)
        self.assert_edit(actions[0], self.later["new run"][2], "device-test", TAG, 9,
                         checklist_title(TAG))
        body = self.body_of(actions[0])
        self.assert_body_shape(body, checklist_marker(TAG))
        return actions[0], split_body(body)

    def test_new_run_is_an_edit_with_the_new_commit(self):
        """Run 2 passed: ``new_run`` true, the run number and the commit changed."""
        action, (chinese, english) = self.edited()
        self.assertIs(action["new_run"], True)
        self.assertIn("**在你的设备上测试 v0.1.0** · 第 2 轮 · 要测的提交：9c1f0de", chinese)
        self.assertIn("**Test v0.1.0 on your devices** · run 2 · commit to test: 9c1f0de",
                      english)

    def test_new_run_unticks_the_failed_scenario(self):
        """v0.1-S02, named in Troy's failed comment, is unticked again."""
        _, (chinese, _) = self.edited()
        self.assertIn(BOXES[0], box_lines(chinese))

    def test_new_run_keeps_the_other_ticks(self):
        """Planted bug "Troy's ticks lost": v0.1-S04 stays ticked."""
        _, (chinese, _) = self.edited()
        self.assertIn(BOXES[1].replace("- [ ]", "- [x]"), box_lines(chinese))

    def test_new_run_clears_the_accept_box(self):
        """Planted bug "the accept box kept at a new run"."""
        _, (chinese, _) = self.edited()
        self.assertEqual(box_lines(chinese)[-1], BOXES[3])

    def test_engine_never_ticks_a_box(self):
        """Planted bug "ticked by the engine": v0.1-S05, never ticked, stays unticked."""
        _, (chinese, _) = self.edited()
        self.assertEqual(box_lines(chinese),
                         [BOXES[0], BOXES[1].replace("- [ ]", "- [x]"), BOXES[2], BOXES[3]])


class CloseTests(ChecklistCase):
    """Closed with the release (design 6.5; note 4.2's table)."""

    def test_closed_once_the_release_pr_merged(self):
        """``[docs] Release v0.1.0`` on origin/main: the open checklist closes as completed."""
        actions = self.actions(self.outs, "released")
        self.assertEqual(len(actions), 1, actions)
        self.assert_close(actions[0], "device-test", TAG, 9, "completed")

    def test_left_alone_without_a_release_pr(self):
        """Pair: no release PR and no release commit: nothing."""
        self.assertEqual(self.actions(self.outs, "no release PR"), [])


if __name__ == "__main__":
    unittest.main()


class AsWrittenTests(IssuesCase):
    """Scenario cells are copied as written, code marks included (design 6.2).

    Added after the F15 trial: its checklist dropped the plan's backticks.
    """

    def test_backticks_are_kept_in_both_languages(self):
        """A step with `wc notes.txt` in the plan keeps its backticks in both parts."""
        en = tuple(row if row[0] != "v0.1-S02" else
                   row[:3] + ("Open a terminal and run `wc notes.txt`", "Prints `3`")
                   for row in EN_SCENARIOS)
        zh = tuple(row if row[0] != "v0.1-S02" else
                   row[:3] + ("打开终端，运行 `wc notes.txt`", "显示 `3`") for row in ZH_SCENARIOS)
        outs = issues_runs({"marks": (release_steps(plan_pair(scenarios=(en, zh))),
                                      release_with(passed(1, COMMIT1), waiting()))})
        out, fake, _ = outs["marks"]
        self.assert_read_only(fake)
        files = [a["body_file"] for a in self.issues_report(out)["actions"]
                 if a.get("kind") == "device-test" and a.get("body_file")]
        self.assertEqual(len(files), 1, out.describe())
        body = open(files[0], "rb").read().decode("utf-8")
        chinese, english = ("\n".join(part) for part in split_body(body))
        self.assertIn("  步骤：打开终端，运行 `wc notes.txt`", chinese)
        self.assertIn("  预期：显示 `3`", chinese)
        self.assertIn("Steps: Open a terminal and run `wc notes.txt` Expected: Prints `3`", english)
