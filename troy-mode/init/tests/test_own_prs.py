"""Its own PRs pass (F06 design 4.2, 4.4, and 7): troy-check on the setup and upgrade commits.

Each class stages exactly the report's paths (git hooks with --chmod=+x),
makes the one commit of the PR flow, and runs the project's troy-check.
"""

import unittest

from init_helpers import (
    EMAIL, HOOKS_DIR, SETUP_BODY, SETUP_TITLE, InitCase, Project, hook_paths, make_plugin,
    results_by_rule, shared_plugin,
)
from rules_helpers import NEW_VERSION, UPGRADE_BODY, UPGRADE_TITLE, apply_upgrade_changes


class SetupPrTest(InitCase):
    """The setup commit, checked against origin/main as its PR would be."""

    @classmethod
    def setUpClass(cls):
        """Runs setup, commits its stage, and runs troy-check pr once."""
        cls.plugin = shared_plugin(hooks=True)
        cls.project = Project()
        out = cls.project.setup(cls.plugin)
        if out.code != 0 or not isinstance(out.report, dict):
            raise AssertionError(f"setup did not succeed:\n{out.describe()}")
        cls.report = out.report
        cls.project.commit_report(cls.report, SETUP_TITLE, EMAIL)
        cls.status = cls.project.status_paths()
        cls.modes = cls.project.index_modes()
        cls.committed = cls.project.git(
            "diff", "--name-only", "--no-renames", "origin/main", "HEAD").split("\n")
        cls.check = cls.project.troy_check("origin/main", SETUP_TITLE, SETUP_BODY)

    def test_setup_pr_passes_r01_r02_r12_and_r20(self):
        """One commit, all config paths, matching mirrors, and no template markers."""
        results = results_by_rule(self.check)
        for rule in ("R01", "R02", "R12", "R20"):
            with self.subTest(rule=rule):
                self.assertEqual(results[rule]["result"], "pass", results[rule])

    def test_setup_pr_does_not_fail_r19(self):
        """R19 does not fail; it may warn, as the merge base has no commit_email yet."""
        result = results_by_rule(self.check)["R19"]
        self.assertIn(result["result"], ("pass", "warn"), result)

    def test_setup_pr_report_is_ok(self):
        """troy-check exits 0 and reports ok."""
        self.assertEqual(self.check.code, 0, self.check.describe())
        self.assertIs(self.check.report["ok"], True)

    def test_setup_commit_records_git_hooks_as_executable(self):
        """git records every hook file with mode 100755."""
        modes = {path: mode for path, mode in self.modes.items() if path.startswith(HOOKS_DIR)}
        self.assertEqual(modes, {path: "100755" for path in hook_paths(self.plugin)})

    def test_setup_commit_holds_exactly_the_staged_paths(self):
        """The commit adds exactly the report's stage, and nothing is left unstaged."""
        self.assertEqual(sorted(p for p in self.committed if p), self.report["stage"])
        self.assertEqual(self.status, set())


class UpgradePrTest(InitCase):
    """The upgrade commit, checked with the setup commit as its merge base."""

    @classmethod
    def setUpClass(cls):
        """Sets up with one plugin version, upgrades to the next, and checks the upgrade."""
        old = make_plugin(hooks=True, version="0.1.0")
        cls.plugin = make_plugin(hooks=True)
        apply_upgrade_changes(cls.plugin)
        cls.project = Project()
        out = cls.project.setup(old)
        if out.code != 0 or not isinstance(out.report, dict):
            raise AssertionError(f"setup did not succeed:\n{out.describe()}")
        cls.base = cls.project.commit_report(out.report, SETUP_TITLE, EMAIL)
        cls.project.git("switch", "-q", "-c", f"troy-mode/upgrade-{NEW_VERSION}")
        out = cls.project.upgrade(cls.plugin)
        if out.code != 0 or not isinstance(out.report, dict):
            raise AssertionError(f"upgrade did not succeed:\n{out.describe()}")
        cls.report = out.report
        cls.project.commit_report(cls.report, UPGRADE_TITLE, EMAIL)
        cls.status = cls.project.status_paths()
        cls.modes = cls.project.index_modes()
        cls.committed = cls.project.git(
            "diff", "--name-only", "--no-renames", cls.base, "HEAD").split("\n")
        cls.check = cls.project.troy_check(cls.base, UPGRADE_TITLE, UPGRADE_BODY)

    def test_upgrade_pr_passes_r01_r02_r12_r19_and_r20(self):
        """The upgrade's PR passes every rule troy-init's own PRs must pass."""
        results = results_by_rule(self.check)
        for rule in ("R01", "R02", "R12", "R19", "R20"):
            with self.subTest(rule=rule):
                self.assertEqual(results[rule]["result"], "pass", results[rule])

    def test_upgrade_pr_report_is_ok(self):
        """troy-check exits 0 and reports ok."""
        self.assertEqual(self.check.code, 0, self.check.describe())
        self.assertIs(self.check.report["ok"], True)

    def test_upgrade_commit_keeps_git_hooks_executable(self):
        """A replaced hook is staged with +x, so every hook file stays 100755."""
        self.assertIn(f"{HOOKS_DIR}/commit-msg", self.report["executable"])
        modes = {path: mode for path, mode in self.modes.items() if path.startswith(HOOKS_DIR)}
        self.assertEqual(modes, {path: "100755" for path in hook_paths(self.plugin)})

    def test_upgrade_commit_holds_exactly_the_staged_paths(self):
        """The commit changes exactly the report's stage, deletions included."""
        self.assertEqual(sorted(p for p in self.committed if p), self.report["stage"])
        self.assertEqual(self.status, set())


if __name__ == "__main__":
    unittest.main()
