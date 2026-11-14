"""Upgrade group (F06 design 6, D54): edited files, --replace, a dry run, and nothing to change."""

import tomllib
import unittest

from init_helpers import (
    RECORD, RULES, WORKFLOW, InitCase, Project, make_plugin, owned_files, setup_project,
    sha256_lf, shared_plugin,
)
from rules_helpers import (
    CHANGED_TEMPLATE, DROPPED_TEMPLATE, KEPT_TEMPLATE, NEW_TEMPLATE, P_ROWS, UPGRADE_STAGE,
    add_rows_after, apply_upgrade_changes, rule_rows,
)

LOCAL_NOTE = "\nA note this project added by hand.\n"


class UpgradeConflictTest(InitCase):
    """An owned file edited since setup stops upgrade unless named with --replace."""

    @classmethod
    def setUpClass(cls):
        """Builds the old and the new plugin version once."""
        cls.old = make_plugin(hooks=True, version="0.1.0")
        cls.plugin = make_plugin(hooks=True)
        apply_upgrade_changes(cls.plugin)

    def edited_project(self, path: str) -> Project:
        """A set-up project where one file was changed by hand and committed."""
        project = setup_project(self.old)
        text = project.read(path) if (project.root / path).exists() else ""
        project.write(path, text + LOCAL_NOTE)
        project.commit_paths([path], "[rules] Change a troy-mode file by hand")
        return project

    def assert_conflict(self, project: Project, path: str) -> None:
        """Runs upgrade and asserts exit 1, one conflict for the path, and no change."""
        before = project.snapshot()
        report = self.report_of(project.upgrade(self.plugin), 1)
        self.assertEqual(report["command"], "upgrade")
        self.assertEqual([item["path"] for item in report["conflicts"]], [path])
        self.assert_unchanged(before, project.snapshot())
        self.assertEqual(project.read_bytes(path), before.files[path])

    def test_upgrade_stops_on_an_edited_file_the_plugin_changed(self):
        """An edited owned file is not replaced by the plugin's new version."""
        self.assert_conflict(self.edited_project(CHANGED_TEMPLATE), CHANGED_TEMPLATE)

    def test_upgrade_stops_on_an_edited_file_the_plugin_kept(self):
        """An edited owned file is a conflict even when the plugin did not change it."""
        self.assert_conflict(self.edited_project(KEPT_TEMPLATE), KEPT_TEMPLATE)

    def test_upgrade_stops_on_an_edited_file_the_plugin_dropped(self):
        """An edited file the plugin dropped is not deleted."""
        self.assert_conflict(self.edited_project(DROPPED_TEMPLATE), DROPPED_TEMPLATE)

    def test_upgrade_stops_on_an_edited_workflow(self):
        """The workflow follows the same hash rule as the other owned files."""
        self.assert_conflict(self.edited_project(WORKFLOW), WORKFLOW)

    def test_upgrade_stops_when_a_new_template_path_is_taken(self):
        """A project file where the plugin adds a template is not overwritten."""
        self.assert_conflict(self.edited_project(NEW_TEMPLATE), NEW_TEMPLATE)

    def test_upgrade_replaces_unchanged_files_in_a_crlf_checkout(self):
        """With core.autocrlf=true, an owned file nobody edited is replaced, not a conflict."""
        source = setup_project(self.old)
        project = Project(source=source.root, clone_config=["core.autocrlf=true"])
        self.assertIn(b"\r\n", project.read_bytes(CHANGED_TEMPLATE))
        report = self.report_of(project.upgrade(self.plugin), 0)
        self.assertEqual(report["conflicts"], [])
        self.assertEqual(self.actions_of(report)[CHANGED_TEMPLATE], "replace")
        self.assertEqual(project.read_bytes(CHANGED_TEMPLATE),
                         owned_files(self.plugin)[CHANGED_TEMPLATE])

    def test_upgrade_replace_lets_an_edited_file_through(self):
        """--replace names the edited file, which then gets the plugin's version."""
        project = self.edited_project(CHANGED_TEMPLATE)
        report = self.report_of(project.upgrade(self.plugin, "--replace", CHANGED_TEMPLATE), 0)
        self.assertEqual(self.actions_of(report)[CHANGED_TEMPLATE], "replace")
        content = owned_files(self.plugin)[CHANGED_TEMPLATE]
        self.assertEqual(project.read_bytes(CHANGED_TEMPLATE), content)
        record = tomllib.loads(project.read(RECORD))
        self.assertEqual(record["files"][CHANGED_TEMPLATE], sha256_lf(content))
        self.assertEqual(report["stage"], UPGRADE_STAGE)


class UpgradeDryRunTest(InitCase):
    """A dry run plans the upgrade and changes nothing."""

    def test_upgrade_dry_run_plans_the_upgrade_and_changes_nothing(self):
        """The dry run reports the real run's stage, and no file or git config changes."""
        plugin = make_plugin(hooks=True)
        apply_upgrade_changes(plugin)
        project = setup_project(make_plugin(hooks=True, version="0.1.0"))
        before = project.snapshot()
        report = self.report_of(project.upgrade(plugin, "--dry-run"), 0)
        self.assertIs(report["dry_run"], True)
        self.assertIs(report["changed"], True)
        self.assertEqual(report["stage"], UPGRADE_STAGE)
        self.assert_unchanged(before, project.snapshot())


class UpgradeNothingToChangeTest(InitCase):
    """Upgrade with the plugin version a project already has."""

    @classmethod
    def setUpClass(cls):
        """Uses the plugin with git hooks for both setup and upgrade."""
        cls.plugin = shared_plugin(hooks=True)

    def assert_nothing_to_do(self, project: Project) -> None:
        """Runs upgrade and asserts exit 0, changed false, an empty stage, and no change."""
        before = project.snapshot()
        report = self.report_of(project.upgrade(self.plugin), 0)
        self.assertIs(report["changed"], False)
        self.assertEqual(report["stage"], [])
        self.assertEqual(report["executable"], [])
        self.assertEqual(report["conflicts"], [])
        self.assert_unchanged(before, project.snapshot())

    def test_upgrade_with_the_same_plugin_changes_nothing(self):
        """Nothing to change: exit 0, changed false, and install.toml untouched."""
        self.assert_nothing_to_do(setup_project(self.plugin))

    def test_upgrade_keeps_p_rows_when_r_rows_already_match(self):
        """A rules table with P rows and current R rows is not rewritten."""
        project = setup_project(self.plugin)
        for path in RULES:
            project.write(path, add_rows_after(project.read(path), "R22", P_ROWS[path]))
        project.commit_paths(list(RULES), "[rules] Add P01 and P02")
        self.assert_nothing_to_do(project)
        for path in RULES:
            with self.subTest(path=path):
                self.assertEqual(rule_rows(project.read(path))[-2:], P_ROWS[path])

    def test_upgrade_matches_hashes_in_a_crlf_checkout(self):
        """A checkout with core.autocrlf=true still counts as unchanged."""
        source = setup_project(self.plugin)
        project = Project(source=source.root, clone_config=["core.autocrlf=true"])
        self.assertIn(b"\r\n", project.read_bytes(".troy-mode/checks/troy_check.py"))
        self.assertIn(b"\r\n", project.read_bytes(RULES[0]))
        self.assert_nothing_to_do(project)

    def test_upgrade_needs_no_origin_remote(self):
        """Upgrade runs in a set-up project that has no origin remote."""
        project = setup_project(self.plugin)
        project.git("remote", "remove", "origin")
        self.assert_nothing_to_do(project)


if __name__ == "__main__":
    unittest.main()
