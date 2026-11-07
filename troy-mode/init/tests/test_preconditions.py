"""Preconditions group (F06 design 3.3, 4.1, and 6): each stops the step and changes nothing."""

import unittest

from init_helpers import (
    DATE, EMAIL, ENGINE_REL, PR_TEMPLATE, PROJECT, RECORD, SCRATCH, WORKFLOW, InitCase,
    Project, new_dir, owned_files, run_python, shared_plugin,
)

OWN_TEXT = "# Our own file\n\nWritten before troy-mode came.\n"
WRITTEN_FILES = ("docs/rules.md", "docs/rules.zh-CN.md", WORKFLOW, PR_TEMPLATE)


class SetupPreconditionsTest(InitCase):
    """Setup exits 1 and leaves the project as it was (design 4.1)."""

    @classmethod
    def setUpClass(cls):
        """Uses the plugin with git hooks, so a stray core.hooksPath would show."""
        cls.plugin = shared_plugin(hooks=True)

    def stopped(self, project: Project, *extra: str) -> dict:
        """Runs setup, asserts exit 1 and an unchanged project, and returns the report."""
        before = project.snapshot()
        report = self.report_of(project.setup(self.plugin, *extra), 1)
        self.assert_unchanged(before, project.snapshot())
        self.assertEqual(report["command"], "setup")
        return report

    def problems(self, report: dict) -> str:
        """The report's problems as one text, after checking there is at least one."""
        self.assertNotEqual(report["problems"], [])
        return " ".join(report["problems"])

    def test_setup_stops_without_an_origin_remote(self):
        """A repository with no origin remote is not set up."""
        project = Project()
        project.git("remote", "remove", "origin")
        self.assertIn("origin", self.problems(self.stopped(project)))

    def test_setup_stops_when_origin_main_was_not_fetched(self):
        """An origin whose main branch has not been fetched stops setup."""
        project = Project()
        project.git("remote", "set-head", "origin", "--delete")
        project.git("update-ref", "-d", "refs/remotes/origin/main")
        self.assertIsNotNone(project.config_value("remote.origin.url"))
        self.assertIn("origin", self.problems(self.stopped(project)))

    def test_setup_stops_on_the_main_branch(self):
        """Setup refuses to run while main is checked out."""
        project = Project(branch=None)
        self.assertEqual(project.git("branch", "--show-current").strip(), "main")
        self.assertIn("main", self.problems(self.stopped(project)))

    def test_setup_stops_when_the_project_is_already_set_up(self):
        """A .troy-mode/ folder on origin/main means setup already ran."""
        project = Project(base_files={".troy-mode/config.toml": "[identity]\n"})
        self.assertRegex(self.problems(self.stopped(project)), r"\.troy-mode|upgrade")

    def test_setup_stops_on_each_existing_file_it_would_write(self):
        """Each file setup would write that already exists is a conflict and keeps its content."""
        for path in WRITTEN_FILES:
            with self.subTest(path=path):
                project = Project()
                project.write(path, OWN_TEXT)
                report = self.stopped(project)
                self.assertEqual([item["path"] for item in report["conflicts"]], [path])
                self.assertEqual(project.read(path), OWN_TEXT)

    def test_setup_replace_lets_one_file_through_while_another_conflicts(self):
        """--replace names one file; the other existing file still stops setup."""
        project = Project(base_files={"docs/rules.md": OWN_TEXT, PR_TEMPLATE: OWN_TEXT})
        report = self.stopped(project, "--replace", "docs/rules.md")
        self.assertEqual([item["path"] for item in report["conflicts"]], [PR_TEMPLATE])
        self.assertEqual(project.read("docs/rules.md"), OWN_TEXT)

    def test_setup_replace_overwrites_every_named_file(self):
        """Each file named with a repeated --replace is overwritten, with action replace."""
        project = Project(base_files={"docs/rules.md": OWN_TEXT, PR_TEMPLATE: OWN_TEXT})
        out = project.setup(self.plugin, "--replace", "docs/rules.md", "--replace", PR_TEMPLATE)
        report = self.report_of(out, 0)
        actions = self.actions_of(report)
        self.assertEqual((actions["docs/rules.md"], actions[PR_TEMPLATE]), ("replace", "replace"))
        self.assertEqual(report["conflicts"], [])
        self.assertIn(f"# {PROJECT} rules", project.read("docs/rules.md").split("\n"))
        self.assertEqual(project.read_bytes(PR_TEMPLATE), owned_files(self.plugin)[PR_TEMPLATE])
        self.assertLessEqual({"docs/rules.md", PR_TEMPLATE}, set(report["stage"]))

    def test_setup_stops_below_the_repository_root(self):
        """--repo pointing at a folder inside the repository, not its root, exits 1."""
        project = Project()
        project.write("src/app.txt", "app\n")
        before = project.snapshot()
        args = ["setup", "--email", EMAIL, "--date", DATE, "--json", "--repo", project.root / "src"]
        out = run_python(self.plugin / ENGINE_REL, args, project.tmp)
        self.report_of(out, 1)
        self.assertNotEqual(out.report["problems"], [])
        self.assert_unchanged(before, project.snapshot())


class SetupOptionErrorsTest(InitCase):
    """Setup exits 2 when it cannot run (design 3.3)."""

    @classmethod
    def setUpClass(cls):
        """Uses the plugin with git hooks."""
        cls.plugin = shared_plugin(hooks=True)

    def assert_cannot_run(self, project: Project, *args: str, **setup_args) -> None:
        """Runs setup or another command, asserts exit 2 with a message and no change."""
        before = project.snapshot()
        if args:
            out = project.run(self.plugin, *args)
        else:
            out = project.setup(self.plugin, **setup_args)
        self.assertEqual(out.code, 2, out.describe())
        self.assertNotEqual((out.stderr + out.stdout).strip(), "")
        self.assert_unchanged(before, project.snapshot())

    def test_setup_exits_2_outside_a_git_repository(self):
        """A folder that is not in any git repository exits 2 and stays as it was."""
        folder = new_dir("plain") / PROJECT
        folder.mkdir()
        (folder / "notes.txt").write_bytes(b"notes\n")
        args = ["setup", "--email", EMAIL, "--date", DATE, "--json", "--repo", folder]
        out = run_python(self.plugin / ENGINE_REL, args, folder.parent,
                         {"GIT_CEILING_DIRECTORIES": str(SCRATCH)})
        self.assertEqual(out.code, 2, out.describe())
        self.assertNotEqual(out.stderr.strip(), "")
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["notes.txt"])

    def test_setup_exits_2_without_email(self):
        """setup without --email is a usage error."""
        self.assert_cannot_run(Project(), email=None)

    def test_setup_exits_2_on_a_date_not_in_iso_form(self):
        """A --date that is not YYYY-MM-DD is a usage error."""
        for date in ("2026/11/07", "7 November 2026", "2026-11-7"):
            with self.subTest(date=date):
                self.assert_cannot_run(Project(), date=date)

    def test_lang_exits_2_without_a_known_language(self):
        """lang with no language, or one with no pack, exits 2 and changes nothing."""
        for args in (["lang", "--json"], ["lang", "typescript", "--json"]):
            with self.subTest(args=args):
                self.assert_cannot_run(Project(), *args)


class UpgradePreconditionsTest(InitCase):
    """Upgrade exits 1 and leaves the project as it was (design 6)."""

    @classmethod
    def setUpClass(cls):
        """Uses the plugin with git hooks."""
        cls.plugin = shared_plugin(hooks=True)

    def stopped(self, project: Project) -> str:
        """Runs upgrade, asserts exit 1 and no change, and returns its problems as text."""
        before = project.snapshot()
        report = self.report_of(project.upgrade(self.plugin), 1)
        self.assert_unchanged(before, project.snapshot())
        self.assertEqual(report["command"], "upgrade")
        self.assertNotEqual(report["problems"], [])
        return " ".join(report["problems"])

    def test_upgrade_stops_when_the_project_is_not_set_up(self):
        """A project without .troy-mode/install.toml cannot be upgraded."""
        self.stopped(Project())

    def test_upgrade_stops_on_the_main_branch(self):
        """Upgrade refuses to run while main is checked out."""
        project = Project()
        self.report_of(project.setup(self.plugin), 0)
        project.git("switch", "-q", "main")
        self.assertEqual(project.files(RECORD).keys(), {RECORD})
        self.assertIn("main", self.stopped(project))


if __name__ == "__main__":
    unittest.main()
