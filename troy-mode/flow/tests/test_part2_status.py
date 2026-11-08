"""Status in part 2 (F07 design 5.1, 8.7, 11.1, 11.2, 14.1; part 2 note, status).

History-order stages, the skipped mock, which open PR comes first, the kinds
of side and bug PRs, the ``bugs`` key, the ``bug`` action and its place among
the actions, and the progress file's Stage line for them. Rework and the
change's approval are in ``test_rework.py``.

Planted bugs of design 14.2 caught here:

- "PR B offered before PR A merged": ``BugActionTests.test_open_test_pr_is_continued_not_pr_b``
  and ``BugsTests.test_open_test_pr_is_not_merged``.
- "a stage PR continued before its side PR": ``OpenPrOrderTests``.
- "a redo that leaves the later stages counted": ``HistoryOrderTests``.
- "the mock skipped with an interface in section 2":
  ``SkippedMockTests.test_cases_that_do_not_skip`` ("interface in section 2").
"""

import unittest

from flow_helpers import (
    CHANGE_PREFIX, F01, F02, PROGRESS, REQUIREMENTS, RECORD_REQUIREMENTS, FlowCase, Project,
    base_files, base_step, bug_branch, bug_step, bug_title, change_step, custom_design,
    custom_design_step, parallel, pr, progress_fields, rework, stage_pr, stage_step, stages,
    status_runs,
)

CRASH = "Crash on empty history"
NO_APPROVALS = "[flow]\ntroy_approves_first = 0\n"
TEST_FIX = "[F01 test-fix] Wrong count in F01-T01"
DOCS = "[docs] Add cases to the F01 test plan"


def history(*groups, files=None) -> list:
    """A project's first commit followed by the given steps.

    Args:
        *groups: Steps or lists of steps, in order.
        files: The first commit's files, or None for ``base_files()``.

    Returns:
        The steps, oldest first.
    """
    steps = [base_step(files)]
    for group in groups:
        steps.extend(group if isinstance(group, list) else [group])
    return steps


def merged_of(report: dict, feature_id: str) -> list:
    """The ``merged`` list of one feature in a status report."""
    return next(f["merged"] for f in report["features"] if f["id"] == feature_id)


class HistoryOrderTests(FlowCase):
    """Planted bug "a redo that leaves the later stages counted" (design 5.1, part 2 note)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per history, side by side."""
        cls.outs = status_runs({
            # The part 2 note's example, after F01 was accepted.
            "redo design": (history(stages(F01, 6), stages(F02, 3),
                                    change_step(features=(F01, rework(F02))),
                                    stage_step(F02, 1)), []),
            "redo mock": (history(stages(F01, 5), change_step(features=(rework(F01), F02)),
                                  stage_step(F01, 3)), []),
            "repeated stage": (history(stages(F01, 4), stage_step(F01, 2)), []),
            "squash redo": (history(stages(F01, 4), change_step(features=(rework(F01), F02)),
                                    stage_step(F01, 2, "squash", 57)), []),
        })

    def test_redo_of_the_design_leaves_only_stage_one(self):
        """The note's example: F02's 1, 2, 3, a change, then 1 again: F02 has ``[1]``."""
        report = self.report_of(self.outs["redo design"], 0, "status")
        self.assertEqual(merged_of(report, "F02"), [1])
        self.assertEqual(merged_of(report, "F01"), [1, 2, 3, 4, 5, 6])
        self.assertEqual([f["accepted"] for f in report["features"]], [True, False])
        self.assertEqual(report["next_feature"], "F02")
        self.assert_next(report, action="stage", item="F02", stage=2, task="TM1",
                         title=F02.title(2), branch=F02.branch(2), merged_by="troy")
        self.assertEqual(report["bugs"], [])

    def test_redo_of_the_mock_keeps_the_earlier_stages(self):
        """1 to 5 merged, then 3 again: ``[1, 2, 3]``, and the tests stage is next."""
        report = self.report_of(self.outs["redo mock"])
        self.assertEqual(merged_of(report, "F01"), [1, 2, 3])
        self.assertIs(report["features"][0]["accepted"], False)
        self.assert_next(report, action="stage", item="F01", stage=4, task="TE1",
                         title=F01.title(4), branch=F01.branch(4), merged_by="f07")

    def test_a_stage_merged_again_drops_later_stages_without_a_change(self):
        """The rule is about history order alone: 1 to 4, then 2 again, gives ``[1, 2]``."""
        report = self.report_of(self.outs["repeated stage"])
        self.assertEqual(merged_of(report, "F01"), [1, 2])
        self.assert_next(report, action="stage", item="F01", stage=3, task="DV1",
                         title=F01.title(3), branch=F01.branch(3), merged_by="f07")

    def test_a_squashed_redo_counts_the_same(self):
        """A redo subject with `` (#57)`` drops the later stages too."""
        report = self.report_of(self.outs["squash redo"])
        self.assertEqual(merged_of(report, "F01"), [1, 2])
        self.assert_next(report, action="stage", item="F01", stage=3, task="DV1",
                         title=F01.title(3), branch=F01.branch(3), merged_by="f07")


def design_project_steps(design, *, upto: int = 2) -> list:
    """F01 merged up to a stage, with a chosen design, and no feature Troy approves.

    Args:
        design: The English design's text, or None for no ``design.md``.
        upto: The last merged stage, 1 or 2 (or 4 to add a merged tests stage
            after stage 2, with no stage 3).

    Returns:
        The steps.
    """
    files = base_files(config_extra=NO_APPROVALS)
    steps = [base_step(files), custom_design_step(F01, design)]
    if upto >= 2:
        steps.append(stage_step(F01, 2))
    if upto >= 4:
        steps.append(stage_step(F01, 4))
    return steps


NONE_SECTION = "None. The change adds no interface; section 3 lists the changed ones.\n"
FENCED_ONLY = ("None.\n\nAn interface subsection would look like this:\n\n"
               "```markdown\n### 2.1 `count_blank`\n```\n")
INTERFACE = "### 2.1 `count_blank`\n\n```python\ndef count_blank(text: str) -> int\n```\n"
SKIP_CASES = {
    "no interface": custom_design(F01, NONE_SECTION),
    "subsection only in a fence": custom_design(F01, FENCED_ONLY),
    "subsection only in section 3": custom_design(
        F01, NONE_SECTION, section3="### 3.1 `count`\n\nNow counts blank lines too.\n"),
}
NO_SKIP_CASES = {
    "interface in section 2": custom_design(F01, INTERFACE),
    "no section 2": custom_design(F01, None),
    "no design": None,
    # A fenced "## 2." line in section 1 is not a heading; the real section 2
    # holds an interface subsection.
    "fenced heading before section 2": custom_design(
        F01, INTERFACE, section1_extra="```text\n## 2. Interfaces\n\nNone\n```\n\n"),
}


class SkippedMockTests(FlowCase):
    """Planted bug "the mock skipped with an interface in section 2" (D65, design 11.2)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per design, side by side."""
        cases = {f"skip: {k}": (design_project_steps(v), []) for k, v in SKIP_CASES.items()}
        cases.update({f"keep: {k}": (design_project_steps(v), [])
                      for k, v in NO_SKIP_CASES.items()})
        cases["skip, stage 1 only"] = (design_project_steps(SKIP_CASES["no interface"], upto=1),
                                       [])
        cases["skip, tests merged"] = (design_project_steps(SKIP_CASES["no interface"], upto=4),
                                       [])
        cls.outs = status_runs(cases)

    def test_design_without_an_interface_subsection_skips_the_mock(self):
        """Section 2 with no ``### `` line outside fences: stage 4 and TE1 come next."""
        for label in SKIP_CASES:
            with self.subTest(case=label):
                report = self.report_of(self.outs[f"skip: {label}"])
                self.assertEqual(merged_of(report, "F01"), [1, 2])
                self.assert_next(report, action="stage", item="F01", stage=4, task="TE1",
                                 title=F01.title(4), branch=F01.branch(4), merged_by="f07")

    def test_cases_that_do_not_skip(self):
        """An interface in section 2, no ``## 2.`` block, or no design: stage 3 and DV1."""
        for label in NO_SKIP_CASES:
            with self.subTest(case=label):
                report = self.report_of(self.outs[f"keep: {label}"])
                self.assertEqual(merged_of(report, "F01"), [1, 2])
                self.assert_next(report, action="stage", item="F01", stage=3, task="DV1",
                                 title=F01.title(3), branch=F01.branch(3), merged_by="f07")

    def test_skip_needs_the_test_plan_merged(self):
        """Only stage 1 merged: the test plan is next, not the tests."""
        report = self.report_of(self.outs["skip, stage 1 only"])
        self.assertEqual(merged_of(report, "F01"), [1])
        self.assert_next(report, action="stage", item="F01", stage=2, task="TM1",
                         title=F01.title(2), branch=F01.branch(2), merged_by="f07")

    def test_skipped_mock_is_never_listed_as_merged(self):
        """Stages 1, 2, and 4 merged with a skipped mock: ``merged`` is ``[1, 2, 4]``, DV2 next."""
        report = self.report_of(self.outs["skip, tests merged"])
        self.assertEqual(merged_of(report, "F01"), [1, 2, 4])
        self.assert_next(report, action="stage", item="F01", stage=5, task="DV2",
                         title=F01.title(5), branch=F01.branch(5), merged_by="f07")


class OpenPrOrderTests(FlowCase):
    """Planted bug "a stage PR continued before its side PR" (design 5.1, 8.7)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per set of open PRs, side by side."""
        four = history(stages(F01, 4))
        bug = history(stages(F01, 2), bug_step("B12", "test", CRASH))
        cls.outs = status_runs({
            "docs and test-fix": (four, [
                stage_pr(5, F01, 5), pr(9, TEST_FIX, "troy-mode/f01-test-fix"),
                pr(8, DOCS, "troy-mode/f01-docs")]),
            "test-fix": (four, [stage_pr(5, F01, 5), pr(9, TEST_FIX, "troy-mode/f01-test-fix")]),
            "bug fix": (bug, [stage_pr(4, F01, 3),
                              pr(6, bug_title("B12", "fix", CRASH), bug_branch("B12", "fix"))]),
            "unparsed first": (four, [pr(3, "WIP: try things", "troy-mode/try-things"),
                                      stage_pr(5, F01, 5)]),
        })

    def test_side_prs_come_first_and_the_lowest_of_them_wins(self):
        """Stage PR #5, test-fix #9, docs #8: #8 is continued; the list stays sorted."""
        report = self.report_of(self.outs["docs and test-fix"])
        self.assertEqual([p["number"] for p in report["open_prs"]], [5, 8, 9])
        self.assert_next(report, action="continue-pr", pr=8, title=DOCS,
                         branch="troy-mode/f01-docs", merged_by="f07")

    def test_test_fix_comes_before_the_stage_pr_it_interrupts(self):
        """Stage PR #5 and test-fix #9: the test fix is continued, with no task."""
        report = self.report_of(self.outs["test-fix"])
        self.assert_next(report, action="continue-pr", pr=9, item="F01", title=TEST_FIX,
                         branch="troy-mode/f01-test-fix", merged_by="f07")

    def test_bug_pr_comes_before_a_stage_pr(self):
        """Stage PR #4 and PR B #6: PR B is continued by DV3."""
        report = self.report_of(self.outs["bug fix"])
        self.assert_next(report, action="continue-pr", pr=6, item="B12", task="DV3",
                         title=bug_title("B12", "fix", CRASH), branch=bug_branch("B12", "fix"),
                         merged_by="f07")

    def test_a_title_that_does_not_parse_is_not_continued(self):
        """``WIP`` #3 and stage PR #5: #5 is continued."""
        report = self.report_of(self.outs["unparsed first"])
        self.assert_next(report, action="continue-pr", pr=5, item="F01", stage=5, task="DV2",
                         title=F01.title(5), branch=F01.branch(5), merged_by="f07")


KIND_PRS = [
    (21, bug_title("B12", "test", CRASH), "troy-mode/b12-test", ("test", "B12", None, "f07")),
    (22, bug_title("B12", "fix", CRASH), "troy-mode/b12-fix", ("fix", "B12", None, "f07")),
    (23, TEST_FIX, "troy-mode/f01-test-fix", ("test-fix", "F01", None, "f07")),
    (24, "[B12 test-fix] Wrong fixture in the B12 test", "troy-mode/b12-test-fix",
     ("test-fix", "B12", None, "f07")),
    (25, CHANGE_PREFIX + "Count blank lines", "troy-mode/change-blank-lines",
     ("docs", None, None, "troy")),
    (26, DOCS, "troy-mode/f01-docs", ("docs", None, None, "f07")),
    (27, "[rules] Set the features Troy approves", "troy-mode/approvals",
     ("rules", None, None, "f07")),
    (28, "[refactor] Split the counter", "troy-mode/refactor-counter",
     ("refactor", None, None, "f07")),
    (29, RECORD_REQUIREMENTS, "troy-mode/approve-requirements", ("docs", None, None, "f07")),
]
CONTINUE_TASKS = {21: "TE2", 22: "DV3", 23: None, 24: None, 25: None, 26: None, 27: None,
                  28: None, 29: None}


class PrKindTests(FlowCase):
    """Kind, item, stage, and merge rights of bug and side PRs (part 2 note, Open PRs)."""

    @classmethod
    def setUpClass(cls):
        """One status run with every kind open, then one run per kind alone, side by side."""
        steps = history(stages(F01, 2))
        prs = [pr(n, title, branch) for n, title, branch, _ in KIND_PRS]
        cases = {"all": (steps, prs + [stage_pr(30, F01, 3)])}
        cases.update({f"alone {n}": (steps, [pr(n, title, branch)])
                      for n, title, branch, _ in KIND_PRS})
        cls.outs = status_runs(cases)

    def test_each_kind_has_its_item_stage_and_merge_rights(self):
        """Bug and test-fix PRs carry their ID; Troy merges only the change PR (design 11.2)."""
        report = self.report_of(self.outs["all"])
        found = {p["number"]: (p["kind"], p["item"], p["stage"], p["merged_by"])
                 for p in report["open_prs"]}
        expected = {n: want for n, _, _, want in KIND_PRS}
        expected[30] = ("mock", "F01", 3, "f07")
        self.assertEqual(found, expected)
        self.assertEqual([p["number"] for p in report["open_prs"]], sorted(expected))

    def test_the_first_side_pr_is_continued(self):
        """With every kind open, PR A #21, the lowest side PR, is continued by TE2."""
        report = self.report_of(self.outs["all"])
        self.assert_next(report, action="continue-pr", pr=21, item="B12", task="TE2",
                         title=bug_title("B12", "test", CRASH), branch="troy-mode/b12-test",
                         merged_by="f07")

    def test_continue_task_by_kind(self):
        """TE2 for PR A, DV3 for PR B, and no task for test-fix, docs, rules, and refactor."""
        for number, title, branch, (_, item, stage, merged_by) in KIND_PRS:
            with self.subTest(pr=title):
                report = self.report_of(self.outs[f"alone {number}"])
                self.assert_next(report, action="continue-pr", pr=number, title=title,
                                 branch=branch, item=item, stage=stage,
                                 task=CONTINUE_TASKS[number], merged_by=merged_by)


class BugsTests(FlowCase):
    """The ``bugs`` key, from origin/main subjects and open PR titles (design 5.1, 11.1)."""

    @classmethod
    def setUpClass(cls):
        """One clone with fixed, waiting, and open-only bugs."""
        steps = history(stages(F01, 2),
                        bug_step("B7", "test", "Crash on empty input", pr=31),
                        bug_step("B7", "fix", "Crash on empty input file", pr=32),
                        bug_step("B12", "test", CRASH))
        prs = [pr(40, bug_title("B12", "fix", "Crash when the history is empty"),
                  bug_branch("B12", "fix")),
               pr(41, bug_title("B20", "test", "Wrong total for two files"),
                  bug_branch("B20", "test")),
               pr(43, bug_title("B21", "test", "Second summary"), bug_branch("B21", "test")),
               pr(42, bug_title("B21", "fix", "First summary"), bug_branch("B21", "fix")),
               pr(44, bug_title("B30", "test-fix", "Wrong fixture in the B30 test"),
                  bug_branch("B30", "test-fix")),
               pr(45, "[docs] Explain B99 in the README", "troy-mode/docs-b99")]
        cls.out = Project(steps).status(prs=prs)

    def setUp(self):
        """Every test reads the one report."""
        self.report = self.report_of(self.out)
        self.bugs = {bug["id"]: bug for bug in self.report["bugs"]}

    def test_bugs_are_sorted_by_number(self):
        """B7, B12, B20, B21, B30, by number (not as text); B99 of a docs PR is not a bug."""
        self.assertEqual([bug["id"] for bug in self.report["bugs"]],
                         ["B7", "B12", "B20", "B21", "B30"])

    def test_fixed_bug_takes_the_newest_subjects_summary(self):
        """B7's fix is newer than its test, so its summary wins; `` (#32)`` is not part of it."""
        self.assertEqual(self.bugs["B7"], {"id": "B7", "summary": "Crash on empty input file",
                                           "test_merged": True, "fixed": True})

    def test_merged_subject_comes_before_an_open_pr(self):
        """B12's test merged and its fix is open with another summary: the subject wins."""
        self.assertEqual(self.bugs["B12"], {"id": "B12", "summary": CRASH, "test_merged": True,
                                            "fixed": False})

    def test_open_test_pr_is_not_merged(self):
        """Planted bug "PR B offered before PR A merged": an open PR A is not ``test_merged``."""
        self.assertEqual(self.bugs["B20"], {"id": "B20", "summary": "Wrong total for two files",
                                            "test_merged": False, "fixed": False})

    def test_lowest_open_pr_gives_the_summary(self):
        """B21 only in open PRs: the summary of #42, the lower number."""
        self.assertEqual(self.bugs["B21"], {"id": "B21", "summary": "First summary",
                                            "test_merged": False, "fixed": False})

    def test_test_fix_alone_gives_no_summary(self):
        """B30 only in a test-fix PR: listed, with a null summary."""
        self.assertEqual(self.bugs["B30"], {"id": "B30", "summary": None, "test_merged": False,
                                            "fixed": False})


B12_FIX_TITLE = bug_title("B12", "fix", CRASH)
B12_NEXT = dict(action="bug", item="B12", task="DV3", title=B12_FIX_TITLE,
                branch="troy-mode/b12-fix", merged_by="f07")


class BugActionTests(FlowCase):
    """PR B as the next action, and where it stands among the actions (part 2 note, next)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        test_b12 = bug_step("B12", "test", CRASH)
        cls.outs = status_runs({
            "bug before stage": (history(stages(F01, 2), test_b12), []),
            "squashed test": (history(stages(F01, 2), bug_step("B12", "test", CRASH, pr=31)), []),
            "lowest bug": (history(stages(F01, 2), test_b12,
                                   bug_step("B9", "test", "Wrong total for two files")), []),
            "fixed": (history(stages(F01, 2), test_b12, bug_step("B12", "fix", CRASH)), []),
            "test fix only": (history(stages(F01, 2),
                                      bug_step("B12", "test-fix", "Wrong error in B12-T01")), []),
            "open test PR": (history(stages(F01, 2)),
                             [pr(6, bug_title("B12", "test", CRASH), "troy-mode/b12-test")]),
            "open stage PR": (history(stages(F01, 2), test_b12), [stage_pr(7, F01, 3)]),
            "open fix PR": (history(stages(F01, 2), test_b12),
                            [pr(8, B12_FIX_TITLE, "troy-mode/b12-fix")]),
            "design approval first": (history(stage_step(F01, 1, design="0.4"), test_b12), []),
            "change approval first": (history(stages(F01, 2), change_step(version="1.1"),
                                              test_b12), []),
            "bug before rework": (history(stages(F01, 3),
                                          change_step(features=(rework(F01), F02)), test_b12),
                                  []),
            "order problem first": (history(test_b12, files=base_files(order=["F02", "F01"])),
                                    []),
        })

    def test_pr_b_comes_before_the_next_stage(self):
        """PR A merged: PR B is next, by DV3, with PR A's summary, before F01's stage 3."""
        report = self.report_of(self.outs["bug before stage"])
        self.assertEqual(report["bugs"], [{"id": "B12", "summary": CRASH, "test_merged": True,
                                           "fixed": False}])
        self.assert_next(report, **B12_NEXT)

    def test_pr_b_title_drops_the_squash_number(self):
        """PR A merged as ``... (#31)``: PR B's title repeats the summary without it."""
        self.assert_next(self.report_of(self.outs["squashed test"]), **B12_NEXT)

    def test_lowest_bug_number_wins(self):
        """B9 and B12 both wait for PR B: B9 first."""
        self.assert_next(self.report_of(self.outs["lowest bug"]), action="bug", item="B9",
                         task="DV3", title=bug_title("B9", "fix", "Wrong total for two files"),
                         branch="troy-mode/b9-fix", merged_by="f07")

    def test_fixed_bug_is_not_offered(self):
        """PR A and PR B merged: the feature loop goes on."""
        self.assert_next(self.report_of(self.outs["fixed"]), action="stage", item="F01", stage=3,
                         task="DV1", title=F01.title(3), branch=F01.branch(3), merged_by="f07")

    def test_no_pr_b_without_a_merged_pr_a(self):
        """Planted bug "PR B offered before PR A merged": a merged test fix of B12 is no PR A.

        B12 is listed, without a summary (no test or fix title), and the loop goes on.
        """
        report = self.report_of(self.outs["test fix only"])
        self.assertEqual(report["bugs"], [{"id": "B12", "summary": None, "test_merged": False,
                                           "fixed": False}])
        self.assert_next(report, action="stage", item="F01", stage=3, task="DV1",
                         title=F01.title(3), branch=F01.branch(3), merged_by="f07")

    def test_open_test_pr_is_continued_not_pr_b(self):
        """Planted bug "PR B offered before PR A merged": an open PR A is continued by TE2."""
        report = self.report_of(self.outs["open test PR"])
        self.assertEqual(report["bugs"], [{"id": "B12", "summary": CRASH, "test_merged": False,
                                           "fixed": False}])
        self.assert_next(report, action="continue-pr", pr=6, item="B12", task="TE2",
                         title=bug_title("B12", "test", CRASH), branch="troy-mode/b12-test",
                         merged_by="f07")

    def test_open_pr_comes_before_the_bug(self):
        """An open stage PR is continued before PR B is started."""
        self.assert_next(self.report_of(self.outs["open stage PR"]), action="continue-pr", pr=7,
                         item="F01", stage=3, task="DV1", title=F01.title(3),
                         branch=F01.branch(3), merged_by="f07")

    def test_open_pr_b_is_continued(self):
        """PR B open: continued by DV3."""
        self.assert_next(self.report_of(self.outs["open fix PR"]), action="continue-pr", pr=8,
                         item="B12", task="DV3", title=B12_FIX_TITLE, branch="troy-mode/b12-fix",
                         merged_by="f07")

    def test_recording_a_design_approval_comes_first(self):
        """F01's design merged at 0.4 by Troy on GitHub: record it before PR B."""
        self.assert_next(self.report_of(self.outs["design approval first"]),
                         action="record-approval", item="F01", stage=1, doc=F01.design,
                         title=f"[docs] Record Troy's approval of {F01.design}",
                         branch="troy-mode/approve-f01-design", merged_by="f07")

    def test_recording_a_change_approval_comes_first(self):
        """A change merged at 1.1: record Troy's approval before PR B."""
        self.assert_next(self.report_of(self.outs["change approval first"]),
                         action="record-approval", doc=REQUIREMENTS, title=RECORD_REQUIREMENTS,
                         branch="troy-mode/approve-requirements", merged_by="f07")

    def test_pr_b_comes_before_rework(self):
        """F01 in rework and PR B waiting: PR B first."""
        self.assert_next(self.report_of(self.outs["bug before rework"]), **B12_NEXT)

    def test_order_problem_comes_first(self):
        """An order line that breaks a dependency stops everything after it, PR B included."""
        self.assert_next(self.report_of(self.outs["order problem first"]),
                         action="order-problem")


class BugProgressTests(FlowCase):
    """The progress file's Stage line for bugs and side PRs (part 2 note, the progress file)."""

    @classmethod
    def setUpClass(cls):
        """Runs ``status --write-progress`` in one clone per case and reads the files."""
        test_b12 = bug_step("B12", "test", CRASH)
        cases = {
            "bug": (history(stages(F01, 2), test_b12), []),
            "bug PR": (history(stages(F01, 2), test_b12),
                       [pr(6, B12_FIX_TITLE, "troy-mode/b12-fix")]),
            "test-fix PR": (history(stages(F01, 4)), [pr(9, TEST_FIX, "troy-mode/f01-test-fix")]),
            "docs PR": (history(stages(F01, 4)), [pr(8, DOCS, "troy-mode/f01-docs")]),
        }

        def run(case):
            """Writes the progress file in a new clone and returns the outcome and the text."""
            project = Project(case[0])
            out = project.status("--write-progress", prs=case[1])
            text = project.read(PROGRESS) if project.exists(PROGRESS) else ""
            return out, text
        names = list(cases)
        cls.results = dict(zip(names, parallel(run, [cases[n] for n in names])))

    def fields(self, name: str) -> dict:
        """The report must be fine; returns the progress file's fields."""
        out, text = self.results[name]
        self.report_of(out)
        return progress_fields(text)

    def test_bug_action_has_no_current_feature(self):
        """For PR B as the next action: Current feature None, and the Stage line starts none."""
        fields = self.fields("bug")
        self.assertEqual(fields["Current feature"], "None")
        self.assertTrue(fields["Stage"].startswith("none."), fields["Stage"])

    def test_side_and_bug_prs_have_no_stage(self):
        """Continuing a bug, test-fix, or docs PR: ``none. PR #<n> is open.``"""
        for name, number in (("bug PR", 6), ("test-fix PR", 9), ("docs PR", 8)):
            with self.subTest(case=name):
                stage = self.fields(name)["Stage"]
                self.assertTrue(stage.startswith("none."), stage)
                self.assertIn(f"PR #{number} is open.", stage)


class ChangePrMergeRightsTests(FlowCase):
    """Troy merges the change PR (design 11.2), and only that docs PR besides part 1's."""

    def test_change_pr_waits_for_troy_and_other_docs_prs_do_not(self):
        """Only a title that starts ``[docs] Change the requirements: `` is Troy's to merge."""
        title = CHANGE_PREFIX + "Report totals per folder"
        report = self.report_of(Project(history(stages(F01, 2))).status(prs=[
            pr(3, title, "troy-mode/change-totals"),
            pr(4, "[docs] Change log for v0.1", "troy-mode/changelog")]))
        self.assertEqual([(p["number"], p["merged_by"]) for p in report["open_prs"]],
                         [(3, "troy"), (4, "f07")])
        self.assert_next(report, action="continue-pr", pr=3, title=title,
                         branch="troy-mode/change-totals", merged_by="troy")


if __name__ == "__main__":
    unittest.main()
