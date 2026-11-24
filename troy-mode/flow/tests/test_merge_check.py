"""Merge check group (F20 design 3.7, 3.9, 4, 8.1; part 2 contract P4): ``merge-check``.

Written from F20 design version 1.3 and the part 2 contract before the code exists.
Each test makes a team worktree by hand (as ``team start`` does), commits a stage
PR's one commit on a branch there, and runs ``troy_flow.py merge-check --repo
<worktree> [--rebased-from <commit>] [--conflicts <path> ...] --json``. The PR's
title is the worktree's HEAD subject (R01). merge-check reads git only, so the
fake gh fails every call and no test expects one.

Where the design and the contract differ, the contract holds: design 3.7 and 4
give ``merge-check --pr <n>``; the contract has no ``--pr`` and reads the title from
HEAD. The coordinator's correction: ``outside-plan`` checks only changed paths of
class ``source``; a test path is never in ``outside``.

Planted bugs caught here:

- ``merge-check`` comparing context lines (design 8.2):
  ``RebasedTests.test_rebase_that_moved_the_lines_needs_no_review``.
- A conflict in tests given to the Developer (8.2):
  ``ConflictTests.test_tests_in_a_developer_stage_escalate`` and
  ``test_each_stage_owner``.
- The next version's PR 3 passing before the tag, and PR 1 held (8.2):
  ``HeldTests.test_next_versions_code_prs_wait_for_the_release`` and
  ``test_next_versions_design_and_test_plan_pass``.
- Line numbers compared: the same test as the context lines.
- Lines compared across files instead of per file:
  ``RebasedTests.test_same_lines_in_another_file_changed_the_diff``.
- A path outside the plan's modules let through:
  ``PlanTests.test_source_outside_the_plans_modules``.
- A test path reported outside the plan: ``PlanTests.test_tests_are_never_outside``.
"""

import unittest
from dataclasses import replace

from flow_helpers import (
    ARCHITECTURE, CONFIG, F01, F02, F03, F05, FIVE, Fakes, Project, base_files, base_step,
    config_text, git, release_step, run_engine, stages, subject_commits, version_tests_step,
)
from teams2_helpers import (
    PrivateClone, TeamsCase, add_team, architecture_with_modules, plan_entry, team_commit,
    write_plan,
)

BASE_PY = "src/wordcount/counter/base.py"
BASE_TEXT = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\nf = 6\ng = 7\n"
FILES = base_files(FIVE, extra={ARCHITECTURE: architecture_with_modules(), BASE_PY: BASE_TEXT})
# F01 accepted, F02 at stage 3: its team builds PR 3 to PR 6 in these tests.
ORIGIN = (base_step(FILES), *stages(F01, 6), *stages(F02, 2))
F02V2 = replace(F02, version="v0.2")
F03V3 = replace(F03, version="v0.3")
VERSIONED = (F01, F02V2, F03V3, F05)
V_FILES = base_files(VERSIONED, extra={ARCHITECTURE: architecture_with_modules()})
# v0.1 (F01, F05) not released: F05 at stage 3. Released: F05 accepted, the version
# tests, and v0.1.0's release commit.
UNRELEASED = (base_step(V_FILES), *stages(F01, 6), *stages(F05, 2))
RELEASED = (base_step(V_FILES), *stages(F01, 6), *stages(F05, 6), version_tests_step("v0.1"),
            release_step("v0.1.0"))
NOTES_CONFIG = config_text().replace('dependencies = ["pyproject.toml"]\n',
                                     'dependencies = ["pyproject.toml"]\n'
                                     'docs = ["src/wordcount/notes/**"]\n')
CLASSES = (base_step(base_files(FIVE, extra={ARCHITECTURE: architecture_with_modules(),
                                            CONFIG: NOTES_CONFIG})), *stages(F01, 6))
REPORT_KEYS = ("command", "ok", "result", "item", "stage", "title", "outside", "held_by",
               "diff_changed", "review_again", "owner", "escalate", "problems", "notes")
FOLDER = F02.folder
STAGE_FILES = {
    1: f"{FOLDER}/design.md", 2: f"{FOLDER}/test-plan.md", 3: "src/wordcount/counter/lines.py",
    4: "tests/test_f02.py", 5: "src/wordcount/counter/lines.py", 6: f"{FOLDER}/acceptance.md",
}
LINES_PY = '"""Counts lines."""\n\n\ndef count_lines(text: str) -> int:\n    """Counts."""\n'


class MergeCase(TeamsCase):
    """Runs ``merge-check`` and reads its report. It has no tests of its own."""

    def check(self, project, tree, *extra, code=None):
        """Runs ``merge-check --repo <tree> <extra> --json`` and returns the checked report.

        Args:
            project: The clone.
            tree: The worktree.
            *extra: More options.
            code: The expected exit code, or None for 0 when the result is ready, else 1.

        Returns:
            The report.
        """
        fakes = Fakes(fail=True)
        out = run_engine(["merge-check", "--repo", tree, *extra, "--json"], project.tmp, fakes)
        self.assertIsInstance(out.report, dict, out.describe())
        for key in REPORT_KEYS:
            self.assertIn(key, out.report, out.describe())
        self.assertEqual("merge-check", out.report["command"], out.describe())
        self.assertIs(out.report["ok"], out.report["result"] == "ready", out.describe())
        expected = code if code is not None else (0 if out.report["result"] == "ready" else 1)
        self.assertEqual(expected, out.code, out.describe())
        self.assertIsInstance(out.report["notes"], list, out.describe())
        self.assertEqual([], fakes.gh_calls(), "merge-check called gh")
        return out.report

    def stage_commit(self, project, tree, stage: int, files=None, feature=F02, base="origin/main"):
        """Commits one stage PR of a feature in the worktree; returns the commit."""
        content = files if files is not None else {STAGE_FILES[stage]: f"# stage {stage}\n"}
        return team_commit(project, tree, feature.title(stage), content, base)


class ReadyTests(MergeCase):
    """The report of a PR that may merge (contract P4)."""

    def test_ready_pr_reports_its_title(self):
        """HEAD on origin/main, its paths in the plan's modules: ``ready``, exit 0.

        The item, stage, and title come from HEAD's subject.
        """
        project = Project(ORIGIN)
        tree = add_team(project, "F02")
        write_plan(project, ["F02", "F03", "F05"])
        self.stage_commit(project, tree, 3, {"src/wordcount/counter/lines.py": LINES_PY})
        report = self.check(project, tree, code=0)
        self.assertEqual(("ready", "F02", 3, F02.title(3)),
                         (report["result"], report["item"], report["stage"], report["title"]))
        self.assertEqual([], report["problems"])

    def test_without_a_plan_the_plan_check_is_skipped_with_a_note(self):
        """No plan.json, or none for F02: a path outside every module still gives ``ready``."""
        for name in ("no plan", "no line"):
            with self.subTest(case=name):
                project = Project(ORIGIN)
                tree = add_team(project, "F02")
                if name == "no line":
                    write_plan(project, ["F03", "F05"])
                self.stage_commit(project, tree, 3, {"src/wordcount/stray.py": "x = 1\n"})
                report = self.check(project, tree, code=0)
                self.assertEqual("ready", report["result"])
                self.assertNotEqual([], report["notes"], "no note says the plan check was skipped")


class RebaseTests(MergeCase):
    """``rebase`` when origin/main is not an ancestor of HEAD (R24)."""

    def test_rebase_until_the_pr_holds_origin_main(self):
        """Ready, then another team's merge lands: ``rebase``; after the rebase: ``ready``."""
        project = PrivateClone(ORIGIN)
        tree = add_team(project, "F02")
        self.stage_commit(project, tree, 3, {"src/wordcount/counter/lines.py": LINES_PY})
        self.assertEqual("ready", self.check(project, tree)["result"])
        project.land("[F05 1/6 design] Watch folders", {f"{F05.folder}/design.md": "# F05\n"})
        self.assertEqual("rebase", self.check(project, tree, code=1)["result"])
        git(tree, "rebase", "-q", "origin/main")
        self.assertEqual("ready", self.check(project, tree, code=0)["result"])

    def test_rebase_comes_before_the_plan_check(self):
        """A path outside the plan and an old base: ``rebase`` first."""
        project = PrivateClone(ORIGIN)
        tree = add_team(project, "F02")
        write_plan(project, ["F02", "F03", "F05"])
        self.stage_commit(project, tree, 3, {"src/wordcount/cli/lines_option.py": "x = 1\n"})
        project.land("[F05 1/6 design] Watch folders", {f"{F05.folder}/design.md": "# F05\n"})
        self.assertEqual("rebase", self.check(project, tree, code=1)["result"])


class PlanTests(MergeCase):
    """``outside-plan``: source paths outside the feature's plan modules (contract P4)."""

    def test_source_outside_the_plans_modules(self):
        """F02's plan gives module counter: a cli path and a path of no module are outside.

        Docs and dependency paths are not checked, nor are paths inside counter.
        Planted bug caught: a path outside the plan's modules let through.
        """
        project = Project(ORIGIN)
        tree = add_team(project, "F02")
        write_plan(project, ["F02", "F03", "F05"])
        self.stage_commit(project, tree, 3, {
            "src/wordcount/counter/lines.py": LINES_PY,
            "src/wordcount/cli/lines_option.py": "x = 1\n",
            "src/wordcount/stray.py": "y = 2\n",
            f"{FOLDER}/notes.md": "# Notes\n",
            "pyproject.toml": '[project]\nname = "wordcount"\nversion = "0.1.1"\n',
        })
        report = self.check(project, tree, code=1)
        self.assertEqual("outside-plan", report["result"])
        self.assertEqual(["src/wordcount/cli/lines_option.py", "src/wordcount/stray.py"],
                         sorted(report["outside"]))

    def test_tests_are_never_outside(self):
        """PR 4 with tests outside every module, and PR 3 with one: tests are not reported.

        Planted bug caught: a test path reported outside the plan.
        """
        project = Project(ORIGIN)
        tree = add_team(project, "F02")
        write_plan(project, ["F02", "F03", "F05"])
        self.stage_commit(project, tree, 4, {"tests/cli/test_lines_option.py": "x = 1\n",
                                             "tests/test_f02.py": "y = 1\n"})
        self.assertEqual("ready", self.check(project, tree, code=0)["result"])
        self.stage_commit(project, tree, 3, {"src/wordcount/cli/lines_option.py": "x = 1\n",
                                             "tests/cli/test_lines_option.py": "x = 1\n"})
        report = self.check(project, tree, code=1)
        self.assertEqual(["src/wordcount/cli/lines_option.py"], report["outside"])

    def test_every_plan_module_counts(self):
        """With modules counter and cli in F02's plan, both paths are inside: ``ready``."""
        project = Project(ORIGIN)
        tree = add_team(project, "F02")
        write_plan(project, ["F03", "F05"], entries={"F02": plan_entry(("counter", "cli"))})
        self.stage_commit(project, tree, 3, {"src/wordcount/counter/lines.py": LINES_PY,
                                             "src/wordcount/cli/lines_option.py": "x = 1\n"})
        self.assertEqual("ready", self.check(project, tree, code=0)["result"])

    def test_path_classes_follow_the_config_at_head(self):
        """``[paths] docs`` names ``src/wordcount/notes/**``: such a path is docs, not source."""
        project = Project(CLASSES)
        tree = add_team(project, "F02")
        write_plan(project, ["F02", "F03", "F05"])
        self.stage_commit(project, tree, 3, {"src/wordcount/notes/readme.py": "x = 1\n",
                                             "src/wordcount/counter/lines.py": LINES_PY})
        self.assertEqual("ready", self.check(project, tree, code=0)["result"])

    def test_outside_plan_comes_before_the_release_hold(self):
        """The next version's PR 3 with a path outside its plan: ``outside-plan`` first."""
        project = Project(UNRELEASED)
        tree = add_team(project, "F02")
        write_plan(project, ["F02", "F03"])
        self.stage_commit(project, tree, 3, {"src/wordcount/cli/lines_option.py": "x = 1\n"},
                          feature=F02V2)
        self.assertEqual("outside-plan", self.check(project, tree, code=1)["result"])


class HeldTests(MergeCase):
    """``held``: the next version's PR 3 to PR 6 before the earlier version's release."""

    @classmethod
    def setUpClass(cls):
        """Two clones: v0.1 not released, and v0.1 released (its release commit and tag)."""
        cls.unreleased = Project(UNRELEASED)
        cls.released = Project(RELEASED)
        release = subject_commits(cls.released)["[docs] Release v0.1.0"]
        cls.released.git("tag", "v0.1.0", release)
        cls.trees = {(name, item): add_team(getattr(cls, name), item)
                     for name in ("unreleased", "released") for item in ("F02", "F03", "F05")}

    def run_stage(self, name: str, stage: int, feature=F02V2) -> dict:
        """Commits a stage of the feature in the clone's worktree of that feature, checks it."""
        project, tree = getattr(self, name), self.trees[(name, feature.id)]
        self.stage_commit(project, tree, stage, feature=feature)
        return self.check(project, tree)

    def test_next_versions_code_prs_wait_for_the_release(self):
        """F02 (v0.2), PR 3 to PR 6, while v0.1 has no release: ``held`` by v0.1, exit 1.

        Planted bug caught: the next version's PR 3 passing before the tag (8.2).
        """
        for stage in (3, 4, 5, 6):
            with self.subTest(stage=stage):
                report = self.run_stage("unreleased", stage)
                self.assertEqual("held", report["result"])
                self.assertEqual("v0.1", report["held_by"])

    def test_next_versions_design_and_test_plan_pass(self):
        """F02 (v0.2), PR 1 and PR 2, while v0.1 has no release: ``ready``.

        Planted bug caught: PR 1 held (8.2).
        """
        for stage in (1, 2):
            with self.subTest(stage=stage):
                self.assertEqual("ready", self.run_stage("unreleased", stage)["result"])

    def test_released_version_frees_the_next(self):
        """With v0.1.0's release commit on origin/main, F02's PR 3 is ``ready``."""
        self.assertEqual("ready", self.run_stage("released", 3)["result"])

    def test_current_versions_code_pr_is_not_held(self):
        """F05 (v0.1, the current version) PR 3: nothing earlier to wait for, ``ready``."""
        self.assertEqual("ready", self.run_stage("unreleased", 3, feature=F05)["result"])

    def test_held_by_names_the_unreleased_earlier_version(self):
        """F03 (v0.3) PR 3 after v0.1's release, v0.2 not released: ``held`` by v0.2."""
        report = self.run_stage("released", 3, feature=F03V3)
        self.assertEqual(("held", "v0.2"), (report["result"], report["held_by"]))


class RebasedTests(MergeCase):
    """``--rebased-from``: ``diff_changed`` and ``review_again`` (D274)."""

    def test_rebase_that_moved_the_lines_needs_no_review(self):
        """Another team's line lands next to the PR's change; a clean rebase moves the hunk.

        The rebased commit's context lines and line numbers differ from the old one's,
        its added and deleted lines do not: ``diff_changed`` and ``review_again`` false.
        Planted bug caught: merge-check comparing context lines (8.2), or line numbers.
        """
        project = PrivateClone(ORIGIN)
        tree = add_team(project, "F02")
        old = self.stage_commit(project, tree, 3, {
            BASE_PY: BASE_TEXT.replace("d = 4\n", "d = 40\n"),
            "src/wordcount/counter/lines.py": LINES_PY})
        project.land("[F05 1/6 design] Watch folders",
                     {BASE_PY: BASE_TEXT.replace("a = 1\n", "a = 1\na2 = 1\n"),
                      f"{F05.folder}/design.md": "# F05\n"})
        git(tree, "rebase", "-q", "origin/main")
        new = git(tree, "rev-parse", "HEAD").strip()
        old_diff = git(tree, "show", "--format=", old, "--", BASE_PY)
        new_diff = git(tree, "show", "--format=", new, "--", BASE_PY)
        self.assertNotEqual(old_diff, new_diff, "the fixture must change the context")
        self.assertIn("a2 = 1", git(tree, "show", "HEAD:" + BASE_PY))
        report = self.check(project, tree, "--rebased-from", old, code=0)
        self.assertEqual("ready", report["result"])
        self.assertIs(report["diff_changed"], False)
        self.assertIs(report["review_again"], False)

    def test_changed_lines_bring_the_code_review_back(self):
        """A PR 3 whose added lines changed: ``diff_changed`` and ``review_again`` true."""
        project = Project(ORIGIN)
        tree = add_team(project, "F02")
        old = self.stage_commit(project, tree, 3, {"src/wordcount/counter/lines.py": LINES_PY})
        self.stage_commit(project, tree, 3, {"src/wordcount/counter/lines.py":
                                             LINES_PY + "    return 0\n"})
        report = self.check(project, tree, "--rebased-from", old)
        self.assertIs(report["diff_changed"], True)
        self.assertIs(report["review_again"], True)

    def test_same_lines_in_another_file_changed_the_diff(self):
        """The same added line in another file: the diff changed, per file.

        Planted bug caught: lines compared across files instead of per file.
        """
        project = Project(ORIGIN)
        tree = add_team(project, "F02")
        old = self.stage_commit(project, tree, 3, {"src/wordcount/counter/a.py": "VALUE = 1\n"})
        self.stage_commit(project, tree, 3, {"src/wordcount/counter/b.py": "VALUE = 1\n"})
        report = self.check(project, tree, "--rebased-from", old)
        self.assertIs(report["diff_changed"], True)

    def test_same_commit_did_not_change(self):
        """``--rebased-from`` HEAD itself: nothing changed."""
        project = Project(ORIGIN)
        tree = add_team(project, "F02")
        head = self.stage_commit(project, tree, 3, {"src/wordcount/counter/lines.py": LINES_PY})
        report = self.check(project, tree, "--rebased-from", head, code=0)
        self.assertIs(report["diff_changed"], False)
        self.assertIs(report["review_again"], False)

    def test_review_again_only_for_pr_3_to_5(self):
        """Changed lines in every stage: ``review_again`` for PR 3, 4, and 5 only."""
        project = Project(ORIGIN)
        tree = add_team(project, "F02")
        for stage in range(1, 7):
            with self.subTest(stage=stage):
                path = STAGE_FILES[stage]
                old = self.stage_commit(project, tree, stage, {path: "first = 1\n"})
                self.stage_commit(project, tree, stage, {path: "second = 2\n"})
                report = self.check(project, tree, "--rebased-from", old)
                self.assertIs(report["diff_changed"], True)
                self.assertIs(report["review_again"], stage in (3, 4, 5))


class ConflictTests(MergeCase):
    """``--conflicts``: the stage's author role when its scope holds every path (D273)."""

    @classmethod
    def setUpClass(cls):
        """One clone with F02's worktree; each case commits its stage there in turn."""
        cls.project = Project(ORIGIN)
        cls.tree = add_team(cls.project, "F02")

    def owner(self, stage: int, *paths: str) -> tuple:
        """Commits stage ``stage`` of F02 and returns ``(owner, escalate)`` for the paths."""
        self.stage_commit(self.project, self.tree, stage)
        report = self.check(self.project, self.tree, "--conflicts", *paths)
        return report["owner"], report["escalate"]

    def test_each_stage_owner(self):
        """Design, test plan, source, tests, source and a manifest, and the status row."""
        cases = [
            (1, (f"{FOLDER}/design.md", f"{FOLDER}/design.zh-CN.md"), "interface-designer"),
            (2, (f"{FOLDER}/test-plan.md",), "test-manager"),
            (3, ("src/wordcount/counter/lines.py",), "developer"),
            (3, ("src/wordcount/counter/lines.py", "pyproject.toml"), "developer"),
            (4, ("tests/test_f02.py",), "test-engineer"),
            (5, ("src/wordcount/counter/lines.py", "src/wordcount/cli/main.py"), "developer"),
            (6, ("docs/requirements.md", "docs/requirements.zh-CN.md"), "product-manager"),
        ]
        for stage, paths, role in cases:
            with self.subTest(stage=stage, paths=paths):
                self.assertEqual((role, False), self.owner(stage, *paths))

    def test_tests_in_a_developer_stage_escalate(self):
        """A conflict in tests in PR 3 or PR 5: no owner, escalate.

        Planted bug caught: a conflict in tests given to the Developer (8.2).
        """
        for stage in (3, 5):
            with self.subTest(stage=stage):
                self.assertEqual((None, True), self.owner(stage, "tests/test_f02.py"))

    def test_a_mix_of_scopes_escalates(self):
        """Paths that no one role's scope holds in that stage escalate (5.7)."""
        cases = [
            (4, ("tests/test_f02.py", "src/wordcount/counter/lines.py")),
            (6, ("docs/requirements.md", "src/wordcount/counter/lines.py")),
            (1, ("docs/requirements.md",)),
            (2, (f"{FOLDER}/design.md",)),
        ]
        for stage, paths in cases:
            with self.subTest(stage=stage, paths=paths):
                self.assertEqual((None, True), self.owner(stage, *paths))


if __name__ == "__main__":
    unittest.main()
