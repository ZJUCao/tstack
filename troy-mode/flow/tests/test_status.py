"""Status group (F07 design 5.1, 8.3, 8.4, 8.6, 14.1): ``troy_flow.py status``.

Planted bugs of design 14.2 caught here:

- "a stage read from the PR title instead of origin/main":
  ``OriginMainOnlyTests.test_open_pr_title_is_not_a_merged_stage`` and
  ``test_local_commit_is_not_a_merged_stage``.
- "the order line not checked": ``OrderTests``.
- "PR 2 of the third feature merged by F07":
  ``MergeRightsTests.test_third_feature_test_plan_waits_for_troy`` and
  ``test_open_prs_say_who_merges``.
- "``troy_approves_first`` off by one": ``MergeRightsTests.test_troy_approves_follows_the_count``
  and ``test_fourth_feature_design_is_merged_by_f07``.
- "rounds counted from every comment":
  ``CommentTests.test_reviews_rounds_attempts_and_troys_comments``,
  ``test_two_reviewers_in_one_round_count_once``, and
  ``test_headings_count_only_as_the_whole_first_line``.
"""

import os
import unittest
from dataclasses import replace

from flow_helpers import (
    ALL_ISSUES_ARGS, ALL_PRS_ARGS, ANY, ARCHITECTURE, CONFIG, F01, F02, F03, F04, FIVE,
    PROGRESS, REQUIREMENTS, SCRATCH,
    SETUP_TITLE, Fakes, FlowCase, Project, base_files, base_step, comments, config_text,
    front_matter, git, lf, new_dir, plugin_checks_files, pr, run_engine, same_path, stage_pr,
    stage_step, stages, status_runs, step,
)

LIST_ARGS = ["pr", "list", "--state", "open", "--limit", "100", "--json",
             "number,title,headRefName,url,createdAt"]
APPROVALS_TITLE = "[rules] Set the features Troy approves"


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


def flow_config(count: int) -> str:
    """Config text that sets ``[flow] troy_approves_first``.

    Args:
        count: The value.

    Returns:
        The ``[flow]`` table.
    """
    return f"[flow]\ntroy_approves_first = {count}\n"


class OutsideProjectTests(FlowCase):
    """Folders that are not yet troy-mode projects (design 4 and 10)."""

    def test_plain_folder_needs_setup_and_stays_untouched(self):
        """Outside a repository: setup, null repo and branch, no gh call, nothing written."""
        folder = new_dir("plain")
        fakes = Fakes(fail=True)
        out = run_engine(["status", "--repo", folder, "--json"], SCRATCH, fakes)
        report = self.report_of(out, 0, "status")
        self.assertIsNone(report["repo"])
        self.assertIsNone(report["branch"])
        for key in ("repository", "origin", "marker", "installed"):
            with self.subTest(key=key):
                self.assertIs(report["project"][key], False)
        for doc in ("requirements", "architecture"):
            with self.subTest(doc=doc):
                self.assertIsNone(report["project"][doc]["version"])
                self.assertIs(report["project"][doc]["approved"], False)
        self.assertEqual(report["checks"], {"outdated": False, "differs": []})
        self.assert_next(report, action="setup", title=SETUP_TITLE, branch="troy-mode/init",
                         merged_by="f07")
        self.assertEqual(fakes.gh_calls(), [])
        self.assertEqual(os.listdir(folder), [])
        self.assertEqual((report["progress"]["written"], report["progress"]["rebuilt"]),
                         (False, False))

    def test_repository_without_origin_needs_setup_without_gh(self):
        """A repository without origin/main and .troy-mode/: setup, gh not called."""
        folder = new_dir("local")
        git(folder, "init", "-q", "-b", "main")
        (folder / "README.md").write_bytes(b"# local\n")
        git(folder, "add", "README.md")
        git(folder, "commit", "-q", "-m", "Initial commit")
        fakes = Fakes(fail=True)
        report = self.report_of(run_engine(["status", "--repo", folder, "--json"], SCRATCH, fakes))
        self.assertTrue(same_path(report["repo"], folder))
        self.assertEqual(report["branch"], "main")
        self.assertIs(report["project"]["repository"], True)
        self.assertIs(report["project"]["origin"], False)
        self.assert_next(report, action="setup", title=SETUP_TITLE, branch="troy-mode/init",
                         merged_by="f07")
        self.assertEqual(fakes.gh_calls(), [])
        self.assertFalse((folder / ".troy-mode").exists())

    def test_origin_without_install_record_needs_setup(self):
        """origin/main without .troy-mode/install.toml: gh is asked, and the action is setup."""
        project = Project([step("Initial commit", {"README.md": "# wordcount\n"})])
        fakes = Fakes()
        report = self.report_of(project.status(fakes=fakes))
        self.assertIs(report["project"]["origin"], True)
        self.assertIs(report["project"]["installed"], False)
        self.assertIs(report["project"]["marker"], False)
        self.assert_next(report, action="setup", title=SETUP_TITLE, branch="troy-mode/init",
                         merged_by="f07")
        self.assertIn(LIST_ARGS, [call["argv"] for call in fakes.gh_calls()])
        self.assertFalse(project.exists(PROGRESS))

    def test_open_setup_pr_is_continued(self):
        """An open ``[rules] Set up troy-mode`` PR is continued, not started again."""
        project = Project([step("Initial commit", {"README.md": "# wordcount\n"})])
        out = project.status(prs=[pr(3, SETUP_TITLE, "troy-mode/init")])
        self.assert_next(self.report_of(out), action="continue-pr", pr=3, title=SETUP_TITLE,
                         branch="troy-mode/init", merged_by="f07")

    def test_text_report_has_the_same_exit_code(self):
        """Without ``--json`` the report is free text, and the exit code is still 0."""
        folder = new_dir("plain")
        out = run_engine(["status", "--repo", folder], SCRATCH, Fakes(fail=True))
        self.assert_exit(out, 0)
        self.assertNotEqual(out.stdout.strip(), "")

    def test_repo_that_is_not_a_folder_exits_two(self):
        """``--repo`` naming nothing: the engine cannot run (exit 2)."""
        out = run_engine(["status", "--repo", SCRATCH / "no-such-folder", "--json"], SCRATCH,
                         Fakes(fail=True))
        self.assert_exit(out, 2)


class GhCallTests(FlowCase):
    """The read-only gh calls status makes (interface note, the fake gh)."""

    def test_status_lists_open_prs_and_views_each_one(self):
        """One ``gh pr list`` with the note's options, a view per open PR, from the root.

        F15 (interface note section 1) reads each open PR's comments and
        reviews, and adds the issue list and the list of PRs in every state.
        F07 D261 adds one list of CI runs per open PR, by its head branch.
        """
        project = Project(history(stages(F01, 2)))
        open_prs = [stage_pr(9, F01, 3), pr(7, "[docs] Fix a typo in the README")]
        fakes = Fakes(open_prs)
        self.report_of(project.status(fakes=fakes))
        calls = fakes.gh_calls()
        runs = [["run", "list", "--branch", p["headRefName"], "--event", "pull_request",
                 "--limit", "100", "--json",
                 "databaseId,headBranch,headSha,status,conclusion,createdAt,updatedAt,workflowName"]
                for p in open_prs]
        self.assertEqual(sorted(call["argv"] for call in calls), sorted([
            LIST_ARGS, ["pr", "view", "7", "--json", "comments,reviews"],
            ["pr", "view", "9", "--json", "comments,reviews"], ALL_ISSUES_ARGS, ALL_PRS_ARGS,
            *runs]))
        for call in calls:
            self.assertTrue(same_path(call["cwd"], project.root), call)
        self.assertEqual(fakes.mamba_calls(), [])

    def test_gh_failure_exits_two(self):
        """A gh call that fails stops the engine with exit code 2."""
        project = Project(history())
        self.assert_exit(project.status(fakes=Fakes(fail=True)), 2)


class MergedStageTests(FlowCase):
    """Stages read from rebase, squash, and merge-commit subjects on origin/main."""

    @classmethod
    def setUpClass(cls):
        """Stage 1 rebased, stage 2 squashed with `` (#41)``, stage 3 merged with a merge commit."""
        cls.project = Project(history(stage_step(F01, 1), stage_step(F01, 2, "squash", 41),
                                      stage_step(F01, 3, "merge", 43)),
                              branch="troy-mode/f01-4-tests")
        cls.out = cls.project.status()

    def setUp(self):
        """Every test reads the one status report."""
        self.report = self.report_of(self.out, 0, "status")

    def test_every_merge_style_counts_as_merged(self):
        """F01 has stages 1, 2, and 3 merged and is not accepted."""
        first = self.report["features"][0]
        self.assertEqual(first["merged"], [1, 2, 3])
        self.assertIs(first["accepted"], False)

    def test_next_is_the_lowest_stage_not_merged(self):
        """The next action is stage 4 of F01, the Test Engineer's TE1, merged by F07."""
        self.assertEqual(self.report["next_feature"], "F01")
        self.assert_next(self.report, action="stage", item="F01", stage=4, task="TE1",
                         title="[F01 4/6 tests] Count words", branch="troy-mode/f01-4-tests",
                         merged_by="f07")

    def test_feature_entries_follow_the_table(self):
        """Each feature row is read with its dependencies, version, status, and merge rights."""
        self.assertEqual(self.report["features"], [
            {"id": "F01", "name": "Count words", "hard": [], "soft": [], "version": "v0.1",
             "status": "Not started", "merged": [1, 2, 3], "accepted": False,
             "troy_approves": True},
            {"id": "F02", "name": "Count lines", "hard": ["F01"], "soft": [], "version": "v0.1",
             "status": "Not started", "merged": [], "accepted": False, "troy_approves": True},
        ])

    def test_project_state_comes_from_origin_main(self):
        """The project block names the pack and both approved documents."""
        self.assertEqual(self.report["project"], {
            "repository": True, "origin": True, "marker": True, "installed": True,
            "lang": "python",
            "requirements": {"path": REQUIREMENTS, "version": "1.0", "approved": True},
            "architecture": {"path": ARCHITECTURE, "version": "1.0", "approved": True},
        })
        self.assertTrue(same_path(self.report["repo"], self.project.root))
        self.assertEqual(self.report["branch"], "troy-mode/f01-4-tests")

    def test_order_is_read_and_valid(self):
        """The order line gives the order, with no problem and the default count of 3."""
        self.assertEqual(self.report["order"], ["F01", "F02"])
        self.assertEqual(self.report["order_problems"], [])
        self.assertEqual(self.report["troy_approves_first"], 3)
        self.assertEqual(self.report["open_prs"], [])
        self.assertIsNone(self.report["waiting_on_troy"])


class OriginMainOnlyTests(FlowCase):
    """Only commit subjects on origin/main count as merged stages (design 5.1)."""

    def test_open_pr_title_is_not_a_merged_stage(self):
        """Planted bug "a stage read from the PR title": an open mock PR leaves stage 3 unmerged."""
        project = Project(history(stages(F01, 2)), branch=F01.branch(3))
        report = self.report_of(project.status(prs=[stage_pr(7, F01, 3)]))
        self.assertEqual(report["features"][0]["merged"], [1, 2])
        self.assertEqual(report["open_prs"], [{
            "number": 7, "title": "[F01 3/6 mock] Count words", "branch": "troy-mode/f01-3-mock",
            "url": "https://github.com/ZJUCao/wordcount/pull/7", "kind": "mock", "item": "F01",
            "stage": 3, "merged_by": "f07", "reviews": [], "rounds": 0, "attempts": 0,
            "ci_failures": [],
            "troy_comments": [], "waiting_for_troy": False, "escalated": False}])
        self.assert_next(report, action="continue-pr", pr=7, item="F01", stage=3, task="DV1",
                         title="[F01 3/6 mock] Count words", branch="troy-mode/f01-3-mock",
                         merged_by="f07")

    def test_local_commit_is_not_a_merged_stage(self):
        """Planted bug "a stage read from the PR title": a commit on HEAD only is not merged."""
        project = Project(history(stages(F01, 2)), branch=F01.branch(3))
        project.commit(F01.title(3), {"src/wordcount/f01.py": '"""Mock."""\n'})
        report = self.report_of(project.status())
        self.assertEqual(report["features"][0]["merged"], [1, 2])
        self.assert_next(report, action="stage", item="F01", stage=3, task="DV1",
                         title="[F01 3/6 mock] Count words", branch="troy-mode/f01-3-mock",
                         merged_by="f07")


class SetupStepTests(FlowCase):
    """Requirements, architecture, and the language step come before features (design 10)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        no_docs = base_files(requirements=None, architecture=None)
        title = "[docs] Add the requirements"
        cls.outs = status_runs({
            "missing requirements": (history(files=no_docs), []),
            "draft requirements": (history(files=base_files(requirements="0.3",
                                                            architecture=None)), []),
            "missing architecture": (history(files=base_files(architecture=None)), []),
            "draft architecture": (history(files=base_files(architecture="0.2")), []),
            "no language": (history(files=base_files(lang=None)), []),
            "open requirements PR": (history(files=no_docs),
                                     [pr(4, title, "troy-mode/requirements")]),
        })

    def test_missing_requirements(self):
        """No requirements on origin/main: the Product Manager writes them, and Troy merges."""
        report = self.report_of(self.outs["missing requirements"])
        self.assertEqual(report["project"]["requirements"],
                         {"path": REQUIREMENTS, "version": None, "approved": False})
        self.assert_next(report, action="requirements", title="[docs] Add the requirements",
                         branch="troy-mode/requirements", merged_by="troy", doc=REQUIREMENTS)
        self.assertEqual(report["order_problems"], [])

    def test_requirements_merged_below_one(self):
        """Requirements at 0.3 on origin/main: record Troy's approval in a PR F07 merges."""
        report = self.report_of(self.outs["draft requirements"])
        self.assertEqual(report["project"]["requirements"],
                         {"path": REQUIREMENTS, "version": "0.3", "approved": False})
        self.assert_next(report, action="record-approval", doc=REQUIREMENTS,
                         title="[docs] Record Troy's approval of docs/requirements.md",
                         branch="troy-mode/approve-requirements", merged_by="f07")

    def test_missing_architecture(self):
        """Approved requirements and no architecture: the architecture is next, merged by Troy."""
        report = self.report_of(self.outs["missing architecture"])
        self.assert_next(report, action="architecture", title="[docs] Add the architecture",
                         branch="troy-mode/architecture", merged_by="troy", doc=ARCHITECTURE)

    def test_architecture_merged_below_one(self):
        """Architecture at 0.2: record Troy's approval of the architecture."""
        report = self.report_of(self.outs["draft architecture"])
        self.assertEqual(report["project"]["architecture"],
                         {"path": ARCHITECTURE, "version": "0.2", "approved": False})
        self.assert_next(report, action="record-approval", doc=ARCHITECTURE,
                         title="[docs] Record Troy's approval of docs/architecture.md",
                         branch="troy-mode/approve-architecture", merged_by="f07")

    def test_language_step_is_next(self):
        """No [lang] in the install record: the language step is next, with no title."""
        report = self.report_of(self.outs["no language"])
        self.assertIsNone(report["project"]["lang"])
        self.assert_next(report, action="language", merged_by="f07", branch=ANY)

    def test_open_requirements_pr_waits_for_troy(self):
        """An open ``[docs] Add the requirements`` PR is continued and Troy merges it."""
        report = self.report_of(self.outs["open requirements PR"])
        entry = report["open_prs"][0]
        self.assertEqual((entry["kind"], entry["item"], entry["stage"], entry["merged_by"]),
                         ("docs", None, None, "troy"))
        self.assert_next(report, action="continue-pr", pr=4, title="[docs] Add the requirements",
                         branch="troy-mode/requirements", merged_by="troy")


def no_table_requirements() -> str:
    """Requirements with an order line and no features table."""
    return (front_matter("requirements", "en", "1.0", "requirements.zh-CN.md")
            + "# wordcount requirements\n\n## 5. Order\n\nTopological order: F01, F02\n")


ORDER_CASES = {
    "hard dependency later": (base_files(order=["F02", "F01"]), ("F01", "F02")),
    "soft dependency later": (base_files((F01, F03), order=["F03", "F01"]), ("F01", "F03")),
    "feature missing from the order": (base_files(order=["F01"]), ("F02",)),
    "ID not in the table": (base_files(order=["F01", "F02", "F09"]), ("F09",)),
    "ID listed twice": (base_files(order=["F01", "F01", "F02"]), ("F01",)),
    "no order line": (base_files(order_line=False), ()),
    "no features table": (base_files(extra={REQUIREMENTS: no_table_requirements()}), ()),
}


class OrderTests(FlowCase):
    """Planted bug "the order line not checked": every dependency must come earlier (design 5.1)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per order mistake, side by side."""
        cls.outs = status_runs({label: (history(files=files), [])
                                for label, (files, _) in ORDER_CASES.items()})

    def test_order_that_breaks_a_hard_dependency_stops_the_loop(self):
        """F02 needs F01 but comes first: a problem naming both, and no stage is offered."""
        report = self.report_of(self.outs["hard dependency later"])
        self.assertEqual(report["order"], ["F02", "F01"])
        self.assertNotEqual(report["order_problems"], [])
        text = " ".join(report["order_problems"])
        self.assertIn("F01", text)
        self.assertIn("F02", text)
        self.assert_next(report, action="order-problem")

    def test_each_kind_of_order_mistake_is_a_problem(self):
        """A late dependency, a missing, unknown, or repeated ID, no order line, no table."""
        for label, (_, named) in ORDER_CASES.items():
            with self.subTest(case=label):
                report = self.report_of(self.outs[label])
                self.assertNotEqual(report["order_problems"], [])
                for feature_id in named:
                    self.assertIn(feature_id, " ".join(report["order_problems"]))
                self.assert_next(report, action="order-problem")


APPROVED_ANSWER = step(APPROVALS_TITLE, {"docs/a.md": "a\n"})
COUNT_CASES = {
    "default": ("", 3, [True, True, True, False, False]),
    "three": (flow_config(3), 3, [True, True, True, False, False]),
    "zero": (flow_config(0), 0, [False] * 5),
    "one": (flow_config(1), 1, [True, False, False, False, False]),
    "more than the features": (flow_config(7), 7, [True] * 5),
}


class MergeRightsTests(FlowCase):
    """Who merges PR 1 and PR 2, from ``[flow] troy_approves_first`` (D61, D62, design 8.6)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        five = base_files(FIVE)
        cases = {f"count {label}": (history(files=base_files(FIVE, config_extra=extra)), [])
                 for label, (extra, _, _) in COUNT_CASES.items()}
        cases.update({
            "third": (history(stages(F01, 6), stages(F02, 6), stage_step(F03, 1), files=five), []),
            "third with two": (history(stages(F01, 6), stages(F02, 6), APPROVED_ANSWER,
                                       stage_step(F03, 1),
                                       files=base_files(FIVE, config_extra=flow_config(2))), []),
            "ask": (history(stages(F01, 6), stages(F02, 6), stages(F03, 6), files=five), []),
            "older answer": (history(stages(F01, 6), stages(F02, 6), APPROVED_ANSWER,
                                     stages(F03, 6), files=five), []),
            "fourth": (history(stages(F01, 6), stages(F02, 6), stages(F03, 6), APPROVED_ANSWER,
                               files=five), []),
            "open PRs": (history(files=five), [
                stage_pr(11, F03, 2), stage_pr(12, F04, 1), stage_pr(13, F03, 3),
                pr(14, "[docs] Add the architecture", "troy-mode/architecture"),
                pr(15, "[docs] Add the requirements", "troy-mode/requirements"),
                pr(16, "[docs] Fix a typo", "troy-mode/typo")]),
            "design draft": (history(stage_step(F01, 1, design="0.4")), []),
            "plan draft": (history(stage_step(F01, 1), stage_step(F01, 2, plan="0.2")), []),
            "draft, count zero": (history(stage_step(F01, 1, design="0.4"),
                                          files=base_files(config_extra=flow_config(0))), []),
        })
        cls.outs = status_runs(cases)

    def test_troy_approves_follows_the_count(self):
        """Planted bug "off by one": the first N features in the order are Troy's, none past N."""
        for label, (_, count, expected) in COUNT_CASES.items():
            with self.subTest(case=label):
                report = self.report_of(self.outs[f"count {label}"])
                self.assertEqual(report["troy_approves_first"], count)
                self.assertEqual([f["troy_approves"] for f in report["features"]], expected)

    def test_third_feature_test_plan_waits_for_troy(self):
        """Planted bug "PR 2 of the third feature merged by F07": Troy merges F03's test plan."""
        report = self.report_of(self.outs["third"])
        self.assert_next(report, action="stage", item="F03", stage=2, task="TM1",
                         title="[F03 2/6 test-plan] Count characters",
                         branch="troy-mode/f03-2-test-plan", merged_by="troy")

    def test_with_a_count_of_two_the_third_feature_is_f07s(self):
        """With a count of 2 and Troy's answer recorded, F07 merges F03's test plan."""
        report = self.report_of(self.outs["third with two"])
        self.assert_next(report, action="stage", item="F03", stage=2, task="TM1",
                         title="[F03 2/6 test-plan] Count characters",
                         branch="troy-mode/f03-2-test-plan", merged_by="f07")

    def test_ask_approvals_after_the_last_feature_troy_approves(self):
        """When the third of three counted features is accepted, F07 asks Troy once."""
        report = self.report_of(self.outs["ask"])
        self.assertEqual(report["next_feature"], "F04")
        self.assert_next(report, action="ask-approvals", title=APPROVALS_TITLE,
                         branch="troy-mode/approvals", merged_by="f07")

    def test_an_answer_older_than_the_accept_does_not_count(self):
        """A ``[rules] Set the features Troy approves`` commit before F03's accept still asks."""
        report = self.report_of(self.outs["older answer"])
        self.assert_next(report, action="ask-approvals", title=APPROVALS_TITLE,
                         branch="troy-mode/approvals", merged_by="f07")

    def test_fourth_feature_design_is_merged_by_f07(self):
        """Planted bug "off by one": after the answer, F04's design is F07's to merge."""
        report = self.report_of(self.outs["fourth"])
        self.assert_next(report, action="stage", item="F04", stage=1, task="IF1",
                         title="[F04 1/6 design] Report totals",
                         branch="troy-mode/f04-1-design", merged_by="f07")

    def test_open_prs_say_who_merges(self):
        """Troy merges PR 1 and 2 of counted features and the setup documents; F07 the rest."""
        report = self.report_of(self.outs["open PRs"])
        self.assertEqual([(p["number"], p["merged_by"]) for p in report["open_prs"]],
                         [(11, "troy"), (12, "f07"), (13, "f07"), (14, "troy"), (15, "troy"),
                          (16, "f07")])

    def test_design_merged_below_one_is_recorded(self):
        """F01's design merged at 0.4 (Troy merged on GitHub): record the approval next."""
        report = self.report_of(self.outs["design draft"])
        self.assert_next(report, action="record-approval", item="F01", stage=1, doc=F01.design,
                         title=f"[docs] Record Troy's approval of {F01.design}",
                         branch="troy-mode/approve-f01-design", merged_by="f07")

    def test_test_plan_merged_below_one_is_recorded(self):
        """F01's test plan merged at 0.2: record the approval of the test plan."""
        report = self.report_of(self.outs["plan draft"])
        self.assert_next(report, action="record-approval", item="F01", stage=2, doc=F01.plan,
                         title=f"[docs] Record Troy's approval of {F01.plan}",
                         branch="troy-mode/approve-f01-test-plan", merged_by="f07")

    def test_nothing_to_record_when_troy_approves_nothing(self):
        """With a count of 0, a design below 1.0 is not Troy's, and stage 2 is next."""
        report = self.report_of(self.outs["draft, count zero"])
        self.assert_next(report, action="stage", item="F01", stage=2, task="TM1",
                         title="[F01 2/6 test-plan] Count words",
                         branch="troy-mode/f01-2-test-plan", merged_by="f07")

    def test_count_is_read_from_origin_main(self):
        """A count committed on the branch or edited in the tree changes nothing."""
        project = Project(history(files=base_files(config_extra=flow_config(1))))
        project.commit("[rules] Change the count", {CONFIG: config_text(extra=flow_config(0))})
        project.write(CONFIG, config_text(extra=flow_config(2)))
        report = self.report_of(project.status())
        self.assertEqual(report["troy_approves_first"], 1)
        self.assertEqual([f["troy_approves"] for f in report["features"]], [True, False])


class NextFeatureTests(FlowCase):
    """The next feature and the next stage (design 5.1, 8.1)."""

    @classmethod
    def setUpClass(cls):
        """Runs status with F01 accepted, and with both features accepted, side by side.

        F08 changed "all accepted": once every feature of a version is
        accepted, status gives ``release`` (F08 note, section 0, item 2). The
        case keeps F07's meaning with features whose Version cells name no
        version, where ``all-accepted`` still follows.
        """
        unversioned = base_files((replace(F01, version="-"), replace(F02, version="Later")))
        cls.outs = status_runs({
            "first accepted": (history(stages(F01, 6)), []),
            "all accepted": (history(stages(F01, 6), stages(F02, 6), files=unversioned), []),
        })

    def test_next_feature_follows_an_accepted_one(self):
        """F01 accepted: F02 is next, at stage 1, and Troy merges its design."""
        report = self.report_of(self.outs["first accepted"])
        self.assertEqual(report["features"][0]["merged"], [1, 2, 3, 4, 5, 6])
        self.assertIs(report["features"][0]["accepted"], True)
        self.assertEqual(report["next_feature"], "F02")
        self.assert_next(report, action="stage", item="F02", stage=1, task="IF1",
                         title="[F02 1/6 design] Count lines", branch="troy-mode/f02-1-design",
                         merged_by="troy")

    def test_each_stage_has_its_task_title_and_branch(self):
        """With 0 to 5 stages merged, the next stage has the task, title, and branch of 8.1."""
        project = Project(history(stages(F01, 6)))
        commits = project.git("rev-list", "--reverse", "--first-parent", "origin/main").split()
        for merged in range(6):
            with self.subTest(merged=merged):
                project.git("update-ref", "refs/remotes/origin/main", commits[merged])
                project.remove(PROGRESS)
                report = self.report_of(project.status())
                number = merged + 1
                self.assertEqual(report["features"][0]["merged"], list(range(1, number)))
                self.assert_next(report, action="stage", item="F01", stage=number,
                                 task=("IF1", "TM1", "DV1", "TE1", "DV2", "PM3")[merged],
                                 title=F01.title(number), branch=F01.branch(number),
                                 merged_by="troy" if number <= 2 else "f07")

    def test_all_accepted(self):
        """Every feature accepted, and no feature has a version: no next feature."""
        report = self.report_of(self.outs["all accepted"])
        self.assertIsNone(report["next_feature"])
        self.assert_next(report, action="all-accepted")


ROUND_TROY = "Also, the Code Reviewer review, round 3: approved line above is wrong."


class CommentTests(FlowCase):
    """Rounds, attempts, and Troy's comments, from F07's headings (design 8.3, 8.4)."""

    @classmethod
    def setUpClass(cls):
        """One clone with F01's stages 1 and 2 merged."""
        cls.project = Project(history(stages(F01, 2)), branch=F01.branch(3))

    def status_of(self, prs, by_pr) -> dict:
        """Runs status with no progress file and returns the report."""
        self.project.remove(PROGRESS)
        return self.report_of(self.project.status(prs=prs, comments_by_pr=by_pr))

    def test_reviews_rounds_attempts_and_troys_comments(self):
        """Planted bug "rounds counted from every comment": six comments, round 1, two attempts."""
        bodies = comments(
            "Please keep the command line small.",
            "Developer attempt 1: failed\n\nruff check: 2 errors",
            "Developer attempt 2: failed\n\nmypy: 1 error",
            "Code Reviewer review, round 1: changes-requested\n\n1. R05: add a doc comment.",
            "Please rename count() to count_words().",
            ROUND_TROY,
        )
        report = self.status_of([stage_pr(7, F01, 3)], {7: bodies})
        entry = report["open_prs"][0]
        self.assertEqual(entry["reviews"], [{"role": "Code Reviewer", "round": 1,
                                             "result": "changes-requested"}])
        self.assertEqual((entry["rounds"], entry["attempts"]), (1, 2))
        self.assertEqual(entry["troy_comments"], ["Please rename count() to count_words().",
                                                  ROUND_TROY])
        self.assertEqual((entry["waiting_for_troy"], entry["escalated"]), (False, False))
        self.assert_next(report, action="continue-pr", pr=7, item="F01", stage=3, task="DV1",
                         title=F01.title(3), branch=F01.branch(3), merged_by="f07", rounds=1,
                         attempts=2)

    def test_two_reviewers_in_one_round_count_once(self):
        """Planted bug "rounds from every comment": TM2 and CR1 in round 1 make one round."""
        bodies = comments("Test Manager review, round 1: approved\n\nAll cases covered.",
                          "Code Reviewer review, round 1: changes-requested\n\n1. Naming.",
                          "Thanks.\nTest Manager review, round 2: approved")
        report = self.status_of([stage_pr(8, F01, 4)], {8: bodies})
        entry = report["open_prs"][0]
        self.assertEqual(entry["reviews"], [
            {"role": "Test Manager", "round": 1, "result": "approved"},
            {"role": "Code Reviewer", "round": 1, "result": "changes-requested"}])
        self.assertEqual(entry["rounds"], 1)
        self.assertEqual(entry["troy_comments"],
                         ["Thanks.\nTest Manager review, round 2: approved"])

    def test_rounds_are_the_highest_round_number(self):
        """Three Architect reviews give round 3, and the reviews keep their order."""
        bodies = comments("Architect review, round 1: changes-requested\n\n1. Naming.",
                          "Architect review, round 2: changes-requested\n\n1. Errors.",
                          "Architect review, round 3: approved\n\nNone")
        report = self.status_of([stage_pr(6, F01, 1)], {6: bodies})
        entry = report["open_prs"][0]
        self.assertEqual([r["round"] for r in entry["reviews"]], [1, 2, 3])
        self.assertEqual([r["result"] for r in entry["reviews"]],
                         ["changes-requested", "changes-requested", "approved"])
        self.assertEqual((entry["rounds"], entry["attempts"], entry["troy_comments"]), (3, 0, []))

    def test_headings_count_only_as_the_whole_first_line(self):
        """Planted bug "rounds from every comment": a heading inside a line is Troy's text."""
        bodies = comments("Interface Designer review, round 1: needs-answer\n\nWhich encoding?",
                          "I read the Architect review, round 2: approved note.",
                          "Note:\nArchitect review, round 3: approved")
        report = self.status_of([stage_pr(6, F01, 1)], {6: bodies})
        entry = report["open_prs"][0]
        self.assertEqual(entry["reviews"], [{"role": "Interface Designer", "round": 1,
                                             "result": "needs-answer"}])
        self.assertEqual(entry["rounds"], 1)
        self.assertEqual(entry["troy_comments"], [
            "I read the Architect review, round 2: approved note.",
            "Note:\nArchitect review, round 3: approved"])

    def test_waiting_for_troy(self):
        """F07's last comment asks Troy and nothing follows: the PR waits for Troy."""
        bodies = comments("Architect review, round 1: approved\n\nNone",
                          "Waiting for Troy: approve this PR")
        report = self.status_of([stage_pr(7, F01, 1)], {7: bodies})
        entry = report["open_prs"][0]
        self.assertEqual((entry["waiting_for_troy"], entry["escalated"]), (True, False))
        self.assertEqual(entry["troy_comments"], [])
        self.assertEqual(report["waiting_on_troy"], "PR #7: Waiting for Troy: approve this PR")

    def test_troys_reply_ends_the_wait(self):
        """A comment of Troy's after the request: no longer waiting, and the reply is passed on."""
        bodies = comments("Architect review, round 1: approved\n\nNone",
                          "Waiting for Troy: approve this PR", "Approved, go ahead.")
        report = self.status_of([stage_pr(7, F01, 1)], {7: bodies})
        entry = report["open_prs"][0]
        self.assertEqual((entry["waiting_for_troy"], entry["escalated"]), (False, False))
        self.assertEqual(entry["troy_comments"], ["Approved, go ahead."])
        self.assertIsNone(report["waiting_on_troy"])

    def test_escalation_waits_for_troy(self):
        """An escalation as F07's last comment: waiting and escalated."""
        bodies = comments("Code Reviewer review, round 3: changes-requested\n\n1. Naming.",
                          "Escalation: three review rounds without agreement\n\nWhere it stopped")
        report = self.status_of([stage_pr(7, F01, 3)], {7: bodies})
        entry = report["open_prs"][0]
        self.assertEqual((entry["waiting_for_troy"], entry["escalated"], entry["rounds"]),
                         (True, True, 3))
        self.assertEqual(report["waiting_on_troy"],
                         "PR #7: Escalation: three review rounds without agreement")

    def test_only_troys_comments(self):
        """Without any comment of F07's, every comment is Troy's and nothing is counted."""
        report = self.status_of([stage_pr(7, F01, 3)],
                                {7: comments("Looks good.", "One more thing.")})
        entry = report["open_prs"][0]
        self.assertEqual(entry["troy_comments"], ["Looks good.", "One more thing."])
        self.assertEqual((entry["rounds"], entry["attempts"], entry["reviews"]), (0, 0, []))

    def test_title_that_does_not_parse(self):
        """An open PR with a title of no kind is listed with null kind and is not continued."""
        report = self.status_of([pr(5, "WIP: try things", "troy-mode/try-things")], {})
        entry = report["open_prs"][0]
        self.assertEqual((entry["kind"], entry["item"], entry["stage"], entry["merged_by"]),
                         (None, None, None, "f07"))
        self.assert_next(report, action="stage", item="F01", stage=3, task="DV1",
                         title=F01.title(3), branch=F01.branch(3), merged_by="f07")

    def test_lowest_open_pr_is_continued(self):
        """Two open PRs with valid titles: the lower number is continued, and the list is sorted."""
        title = "[docs] Fix a typo in the README"
        report = self.status_of([stage_pr(9, F01, 3), pr(7, title, "troy-mode/typo")], {})
        self.assertEqual([p["number"] for p in report["open_prs"]], [7, 9])
        self.assert_next(report, action="continue-pr", pr=7, title=title, branch="troy-mode/typo",
                         merged_by="f07")


class ChecksCopyTests(FlowCase):
    """The project's troy-check against the plugin's (design 5.1, interface note ``checks``)."""

    CHANGED = ".troy-mode/checks/troycheck/titles.py"
    MISSING = ".troy-mode/checks/troycheck/globs.py"
    EXTRA = ".troy-mode/checks/troycheck/legacy.py"

    @classmethod
    def setUpClass(cls):
        """Runs status with a current, a CRLF, and an older copy of troy-check, side by side."""
        current = plugin_checks_files()
        crlf_copy = {path: lf(data).replace(b"\n", b"\r\n") for path, data in current.items()}
        older = dict(current)
        older[cls.CHANGED] = older[cls.CHANGED] + b"# An older copy.\n"
        del older[cls.MISSING]
        older[cls.EXTRA] = b'"""Gone from the plugin."""\n'
        cls.outs = status_runs({name: (history(files=base_files(extra=copy)), [])
                                for name, copy in (("current", current), ("crlf", crlf_copy),
                                                   ("older", older))})

    def test_current_copy_is_not_outdated(self):
        """A copy equal to the plugin's troy-check is up to date."""
        report = self.report_of(self.outs["current"])
        self.assertEqual(report["checks"], {"outdated": False, "differs": []})

    def test_copy_with_crlf_line_endings_is_not_outdated(self):
        """Line endings do not count: a CRLF copy is up to date."""
        report = self.report_of(self.outs["crlf"])
        self.assertEqual(report["checks"], {"outdated": False, "differs": []})

    def test_older_copy_is_outdated_and_names_the_upgrade(self):
        """A changed, a missing, and an extra file are listed, sorted; a note names the upgrade."""
        report = self.report_of(self.outs["older"])
        self.assertEqual(report["checks"], {
            "outdated": True, "differs": sorted([self.CHANGED, self.MISSING, self.EXTRA])})
        self.assertTrue(any("upgrade" in note.lower() for note in report["notes"]),
                        report["notes"])


class ConfigErrorTests(FlowCase):
    """An invalid config on origin/main stops status (exit 2)."""

    def test_invalid_config_on_origin_main_exits_two(self):
        """An unknown section in the config on origin/main: exit 2."""
        files = base_files(config_extra="[bogus]\nx = 1\n")
        self.assert_exit(Project(history(files=files)).status(), 2)


class PlaceTests(FlowCase):
    """Status runs wherever a session starts (design 5.2, 5.10)."""

    def test_runs_in_a_new_worktree(self):
        """In a fresh worktree with no progress file, status reads the state and writes the file."""
        project = Project(history(stages(F01, 2)))
        tree = project.tmp / "tree"
        project.git("worktree", "add", "-q", "-b", "troy-mode/f01-3-mock", str(tree), "origin/main")
        out = run_engine(["status", "--repo", tree, "--json"], project.tmp, Fakes())
        report = self.report_of(out)
        self.assertTrue(same_path(report["repo"], tree))
        self.assertEqual(report["branch"], "troy-mode/f01-3-mock")
        self.assertEqual(report["features"][0]["merged"], [1, 2])
        self.assertTrue((tree / PROGRESS).is_file())
        self.assertFalse(project.exists(PROGRESS))

    def test_runs_from_a_subfolder_without_repo(self):
        """Without ``--repo``, the repository is found from the working folder."""
        project = Project(history())
        out = project.run("status", fakes=Fakes(), repo_option=False, cwd=project.root / "docs")
        report = self.report_of(out)
        self.assertTrue(same_path(report["repo"], project.root))


if __name__ == "__main__":
    unittest.main()
