"""Setup group (F06 design 4.2 to 4.6): plugin variants, existing files, dry run, and options."""

import datetime
import tomllib
import unittest
from pathlib import Path

from init_helpers import (
    CONFIG, DATE, EMAIL, HOOKS_DIR, OTHER_EMAIL, PLUGIN_ROOT, PROGRESS, PROJECT, RECORD, RULES,
    InitCase, Project, git, git_proc, hook_paths, make_plugin, owned_files, pack_patterns,
    read_text, setup_stage, sha256_lf, shared_plugin,
)
from rules_helpers import (
    NEW_PATTERN, RULE_TEMPLATES, add_pack_pattern, fill_rules_template, front_matter,
    nonblank_lines,
)

REQUIREMENTS = {
    "docs/requirements.md": '---\ntroy-doc: "requirements"\nlang: "en"\nversion: "0.1"\n'
                            'updated: "2026-11-06"\nstatus: "Draft."\n'
                            'mirror: "requirements.zh-CN.md"\n---\n\n'
                            '# Habit tracker requirements\n',
    "docs/requirements.zh-CN.md": '---\ntroy-doc: "requirements"\nlang: "zh-CN"\nversion: "0.1"\n'
                                  'updated: "2026-11-06"\nstatus: "草稿。"\n'
                                  'mirror-of: "requirements.md"\n---\n\n# 习惯记录需求\n',
}


def first_heading(text: str) -> str:
    """The first level-one heading of a Markdown text."""
    return next(line for line in text.split("\n") if line.startswith("# "))


class SetupWithoutHooksTest(InitCase):
    """Setup with a plugin that has no git-hooks/ and one extra pack pattern."""

    @classmethod
    def setUpClass(cls):
        """Runs setup once, with no user.email in the repository's git config."""
        cls.plugin = make_plugin(hooks=False)
        add_pack_pattern(cls.plugin, "python", "tests", NEW_PATTERN)
        cls.project = Project()
        cls.out = cls.project.setup(cls.plugin)

    def test_setup_leaves_hooks_path_unset_without_git_hooks(self):
        """With no git-hooks/ folder, core.hooksPath stays unset and hooks_path is null."""
        report = self.report_of(self.out, 0)
        self.assertIsNone(report["hooks_path"])
        self.assertIsNone(self.project.config_value("core.hooksPath"))
        self.assertNotIn("core.hookspath", self.project.git("config", "--list", "--local"))

    def test_setup_lists_no_executable_file_without_git_hooks(self):
        """executable is empty and no hook folder is written."""
        report = self.report_of(self.out, 0)
        self.assertEqual(report["executable"], [])
        self.assertEqual(self.project.files(HOOKS_DIR), {})
        self.assertEqual(report["stage"], setup_stage(self.plugin))

    def test_setup_reads_pack_patterns_from_the_plugin_at_run_time(self):
        """A pattern added to a pack's config.toml reaches the project's config."""
        self.report_of(self.out, 0)
        paths = tomllib.loads(self.project.read(CONFIG))["paths"]
        self.assertIn(NEW_PATTERN, paths["tests"])
        self.assertEqual(sorted(set(paths["tests"])), sorted(pack_patterns(self.plugin)["tests"]))

    def test_setup_reports_an_unset_user_email(self):
        """With no user.email configured, email says so and does not match."""
        self.assertEqual(self.report_of(self.out, 0)["email"],
                         {"wanted": EMAIL, "configured": None, "matches": False})


class SetupWithExistingFilesTest(InitCase):
    """Setup in a project that already has a .gitignore and the requirements."""

    @classmethod
    def setUpClass(cls):
        """Runs setup once; .gitignore has no newline at its end."""
        cls.base = {".gitignore": "node_modules/\n*.log", **REQUIREMENTS}
        cls.plugin = shared_plugin(hooks=True)
        cls.project = Project(base_files=cls.base)
        cls.out = cls.project.setup(cls.plugin)

    def test_setup_appends_the_progress_line_to_an_existing_gitignore(self):
        """The old lines stay and the progress line is added on its own line."""
        report = self.report_of(self.out, 0)
        self.assertEqual(nonblank_lines(self.project.read(".gitignore")),
                         ["node_modules/", "*.log", PROGRESS])
        self.assertEqual(self.actions_of(report)[".gitignore"], "append")
        self.assertIn(".gitignore", report["stage"])

    def test_setup_says_next_action_architecture_when_requirements_exist(self):
        """With docs/requirements.md present, the progress file's next action is architecture."""
        self.report_of(self.out, 0)
        lines = self.project.read(PROGRESS).split("\n")
        following = [line for line in lines if line.startswith("- Next action:")]
        self.assertEqual(len(following), 1)
        self.assertIn("architecture", following[0])

    def test_setup_never_touches_the_requirements(self):
        """The requirements keep their content and stay out of stage."""
        report = self.report_of(self.out, 0)
        for path, text in REQUIREMENTS.items():
            with self.subTest(path=path):
                self.assertEqual(self.project.read_bytes(path), text.encode("utf-8"))
                self.assertNotIn(path, report["stage"])
                self.assertIn(self.actions_of(report).get(path), (None, "keep"))


class SetupWithIgnoredProgressTest(InitCase):
    """Setup in a project whose .gitignore already ignores the progress file."""

    def test_setup_keeps_a_gitignore_that_already_has_the_line(self):
        """The .gitignore is not changed, its action is keep, and it is not staged."""
        text = f"build/\n{PROGRESS}\n"
        project = Project(base_files={".gitignore": text})
        report = self.report_of(project.setup(shared_plugin(hooks=True)), 0)
        self.assertEqual(project.read_bytes(".gitignore"), text.encode("utf-8"))
        self.assertEqual(self.actions_of(report)[".gitignore"], "keep")
        self.assertEqual(report["stage"], setup_stage(shared_plugin(hooks=True), gitignore=False))


class SetupDryRunTest(InitCase):
    """A dry run plans setup and changes nothing."""

    @classmethod
    def setUpClass(cls):
        """Runs setup --dry-run once between two snapshots."""
        cls.plugin = shared_plugin(hooks=True)
        cls.project = Project()
        cls.before = cls.project.snapshot()
        cls.out = cls.project.setup(cls.plugin, "--dry-run")
        cls.after = cls.project.snapshot()

    def test_setup_dry_run_changes_no_file_and_no_git_config(self):
        """The working tree and the local git config are the same before and after."""
        self.report_of(self.out, 0)
        self.assert_unchanged(self.before, self.after)

    def test_setup_dry_run_reports_the_plan_of_a_real_run(self):
        """The dry run reports the same actions, stage, and executable files a real run would."""
        report = self.report_of(self.out, 0)
        self.assertIs(report["dry_run"], True)
        self.assertIs(report["changed"], True)
        expected = {path: "create" for path in setup_stage(self.plugin)}
        expected[PROGRESS] = "create"
        self.assertEqual(self.actions_of(report), expected)
        self.assertEqual(report["stage"], setup_stage(self.plugin))
        self.assertEqual(report["executable"], hook_paths(self.plugin))


class SetupOptionsTest(InitCase):
    """--project-name, the default --date, and an email that differs from git config."""

    def test_setup_uses_the_project_name_option_in_both_headings(self):
        """--project-name replaces the folder's name in both rules files."""
        project = Project()
        self.report_of(project.setup(shared_plugin(), "--project-name", "Habit Tracker"), 0)
        self.assertEqual([first_heading(project.read(path)) for path in RULES],
                         ["# Habit Tracker rules", "# Habit Tracker 规则"])

    def test_setup_dates_its_files_today_by_default(self):
        """Without --date, the rules files and the install record carry today's date."""
        project = Project()
        before = datetime.date.today().isoformat()
        out = project.setup(shared_plugin(), date=None)
        today = {before, datetime.date.today().isoformat()}
        self.report_of(out, 0)
        for path in RULES:
            with self.subTest(path=path):
                self.assertIn(front_matter(project.read(path))["updated"], today)
        self.assertIn(tomllib.loads(project.read(RECORD))["steps"]["setup"], today)

    def test_setup_reports_an_email_that_differs_from_git_config(self):
        """email shows the mismatch; the config takes --email and git config is left alone."""
        project = Project()
        project.git("config", "user.email", OTHER_EMAIL)
        report = self.report_of(project.setup(shared_plugin()), 0)
        self.assertEqual(report["email"],
                         {"wanted": EMAIL, "configured": OTHER_EMAIL, "matches": False})
        self.assertEqual(project.config_value("user.email"), OTHER_EMAIL)
        self.assertEqual(tomllib.loads(project.read(CONFIG))["identity"]["commit_email"], EMAIL)


class SetupFromCrlfPluginTest(InitCase):
    """Setup from a plugin whose checks and templates have CRLF line endings."""

    @classmethod
    def setUpClass(cls):
        """Runs setup once from a CRLF copy of the plugin."""
        cls.plugin = make_plugin(hooks=True, crlf=True)
        cls.project = Project()
        cls.out = cls.project.setup(cls.plugin)

    def test_setup_from_crlf_plugin_writes_only_lf(self):
        """Every file setup writes has LF line endings, though its source has CRLF."""
        report = self.report_of(self.out, 0)
        self.assertIn(b"\r\n", (self.plugin / "troy-mode/templates/rules.md").read_bytes())
        for path in [*report["stage"], PROGRESS]:
            with self.subTest(path=path):
                self.assertNotIn(b"\r\n", self.project.read_bytes(path))

    def test_setup_from_crlf_plugin_copies_owned_files_and_hashes_them(self):
        """Owned files equal the plugin's content with LF, and the record hashes them."""
        self.report_of(self.out, 0)
        record = tomllib.loads(self.project.read(RECORD))["files"]
        for path, data in owned_files(self.plugin).items():
            with self.subTest(path=path):
                self.assertEqual(self.project.read_bytes(path), data)
                self.assertEqual(record[path], sha256_lf(data))

    def test_setup_from_crlf_plugin_fills_the_rules_table(self):
        """Both rules files are filled in and hold no template comment."""
        self.report_of(self.out, 0)
        for path, template in RULE_TEMPLATES.items():
            with self.subTest(path=path):
                expected = fill_rules_template(
                    read_text(self.plugin, f"troy-mode/templates/{template}"), PROJECT, DATE)
                text = self.project.read_bytes(path).decode("utf-8")
                self.assertNotIn("<!--", text)
                self.assertEqual(nonblank_lines(text), nonblank_lines(expected))


class SetupWithRealPluginTest(InitCase):
    """Setup run from the tstack checkout itself."""

    def test_setup_records_the_commit_of_a_plugin_checkout(self):
        """A fake plugin made the top of its own git checkout has its HEAD in the record."""
        plugin = make_plugin(hooks=False)
        git(plugin, "init", "-q", "-b", "main")
        git(plugin, "add", "-A")
        git(plugin, "commit", "-q", "-m", "Fake plugin")
        head = git(plugin, "rev-parse", "HEAD").strip()
        project = Project()
        self.report_of(project.setup(plugin), 0)
        self.assertEqual(tomllib.loads(project.read(RECORD))["plugin"]["commit"], head)

    def test_setup_records_the_plugin_commit_when_the_plugin_is_a_checkout(self):
        """The install record names the plugin checkout's HEAD commit."""
        top = git_proc(PLUGIN_ROOT, "rev-parse", "--show-toplevel")
        if top.returncode != 0 or Path(top.stdout.strip()).resolve() != PLUGIN_ROOT.resolve():
            self.skipTest("the plugin folder is not the top of a git checkout")
        project = Project()
        self.report_of(project.setup(PLUGIN_ROOT), 0)
        plugin = tomllib.loads(project.read(RECORD))["plugin"]
        self.assertEqual(plugin["commit"], git(PLUGIN_ROOT, "rev-parse", "HEAD").strip())
        self.assertRegex(plugin["commit"], r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
