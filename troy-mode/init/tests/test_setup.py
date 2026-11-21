"""Setup group (F06 design 4.2 to 4.6): one setup run with git hooks, read by every test."""

import os
import stat
import sys
import tomllib
import unittest

from init_helpers import (
    CONFIG, DATE, EMAIL, HOOKS_DIR, PLUGIN_ROOT, PR_TEMPLATE, PROGRESS, PROJECT, RECORD,
    REPORT_KEYS, RULES, WORKFLOW, InitCase, Project, expected_checks, expected_templates,
    git_proc, hook_paths, lf, owned_files, pack_patterns, plugin_version, read_text, setup_stage,
    sha256_lf, shared_plugin,
)
from rules_helpers import (
    RULE_TEMPLATES, fill_rules_template, front_matter, nonblank_lines, row_since, rule_rows,
)


def parse_config_with_troy_check(text: str):
    """Parses a config with troy-check's own parser, imported from troy-mode/checks."""
    checks = str(PLUGIN_ROOT / "troy-mode/checks")
    sys.path.insert(0, checks)
    try:
        from troycheck.config import parse_config  # pylint: disable=import-outside-toplevel
    finally:
        sys.path.remove(checks)
    return parse_config(text)


class SetupWithHooksTest(InitCase):
    """Setup from inside a fresh project, with a plugin that has git hooks."""

    @classmethod
    def setUpClass(cls):
        """Runs setup once; the tests only read its result."""
        cls.plugin = shared_plugin(hooks=True)
        cls.project = Project()
        cls.project.git("config", "user.email", EMAIL)
        cls.config_before = cls.project.git("config", "--list", "--local")
        cls.out = cls.project.setup(cls.plugin, repo_option=False)
        cls.config_after = cls.project.git("config", "--list", "--local")

    def report(self) -> dict:
        """The setup run's JSON report, after checking it exited 0."""
        return self.report_of(self.out, 0)

    def test_setup_exits_zero_with_an_ok_report(self):
        """Setup on a fresh branch exits 0 and reports no conflict or problem."""
        report = self.report()
        self.assertEqual(report["command"], "setup")
        self.assertIs(report["dry_run"], False)
        self.assertIs(report["changed"], True)
        self.assertEqual(report["version"], plugin_version(self.plugin))
        self.assertEqual(report["conflicts"], [])
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["differences"], [])

    def test_setup_report_has_every_interface_key(self):
        """The JSON report holds every key the interface names."""
        self.assertLessEqual(set(REPORT_KEYS), set(self.report()))

    def test_setup_lists_every_written_file_as_created(self):
        """Each file setup writes appears once in actions, with action create."""
        expected = {path: "create" for path in setup_stage(self.plugin)}
        expected[PROGRESS] = "create"
        self.assertEqual(self.actions_of(self.report()), expected)

    def test_setup_stages_every_written_file_except_progress(self):
        """stage is the sorted list of every written path, without the local progress file."""
        self.assertEqual(self.report()["stage"], setup_stage(self.plugin))
        self.assertNotIn(PROGRESS, self.report()["stage"])

    def test_setup_copies_checks_without_tests_workflow_or_default_config(self):
        """.troy-mode/checks/ holds exactly the plugin's troy-check files, unchanged."""
        expected = expected_checks(self.plugin)
        actual = {p: lf(data) for p, data in self.project.files(".troy-mode/checks/").items()}
        self.assertEqual(sorted(actual), sorted(expected))
        for path, data in expected.items():
            with self.subTest(path=path):
                self.assertEqual(actual[path], data)

    def test_setup_copies_every_template_unchanged(self):
        """.troy-mode/templates/ holds every template and README, in both languages, unchanged."""
        expected = expected_templates(self.plugin)
        actual = {p: lf(data) for p, data in self.project.files(".troy-mode/templates/").items()}
        self.assertEqual(sorted(actual), sorted(expected))
        for path, data in expected.items():
            with self.subTest(path=path):
                self.assertEqual(actual[path], data)

    def test_setup_copies_the_pr_template_and_the_workflow(self):
        """The PR template and troy-check's workflow are the plugin's files, unchanged."""
        plugin = self.plugin
        self.assertEqual(lf(self.project.read_bytes(PR_TEMPLATE)),
                         lf((plugin / "troy-mode/templates/pull-request.md").read_bytes()))
        self.assertEqual(lf(self.project.read_bytes(WORKFLOW)),
                         lf((plugin / "troy-mode/checks/workflow.yml").read_bytes()))

    def test_setup_writes_only_lf_line_endings(self):
        """No file setup writes contains a CRLF."""
        for path in [*self.report()["stage"], PROGRESS]:
            with self.subTest(path=path):
                self.assertNotIn(b"\r\n", self.project.read_bytes(path))

    def test_setup_config_fills_the_email_and_keeps_the_default_file(self):
        """The config is the commented default with commit_email set and [lang] still empty."""
        default_text = read_text(self.plugin, "troy-mode/checks/config.default.toml")
        text = self.project.read(CONFIG)
        self.assertEqual(text.split("\n")[0], default_text.split("\n")[0])
        data, default = tomllib.loads(text), tomllib.loads(default_text)
        self.assertEqual(data["identity"], {"commit_email": EMAIL})
        self.assertEqual(data.get("lang", {}), {})
        for table in ("limits", "tests", "attribution"):
            with self.subTest(table=table):
                self.assertEqual(data[table], default[table])

    def test_setup_config_keeps_every_comment_of_the_default_file(self):
        """Every comment line of the default file is still there, in order."""
        default_text = read_text(self.plugin, "troy-mode/checks/config.default.toml")
        wanted = [line for line in default_text.split("\n")
                  if line.startswith("#") and not line.startswith("# commit_email")]
        comments = [line for line in self.project.read(CONFIG).split("\n") if line.startswith("#")]
        found = iter(comments)
        missing = [line for line in wanted if line not in found]
        self.assertEqual(missing, [])

    def test_setup_config_holds_every_pack_pattern(self):
        """Each [paths] list holds every pattern of every pack, plus the D49 header in config."""
        paths = tomllib.loads(self.project.read(CONFIG))["paths"]
        expected = pack_patterns(self.plugin)
        keys = ("config", "dependencies", "tests", "docs", "lock", "generated", "allow_markers")
        for key in keys:
            with self.subTest(key=key):
                self.assertEqual(sorted(set(paths.get(key, []))), sorted(expected.get(key, set())))

    def test_setup_config_passes_troy_check_parser(self):
        """troy-check's own config parser accepts the file and reads the email."""
        config = parse_config_with_troy_check(self.project.read(CONFIG))
        self.assertEqual(config.commit_email, EMAIL)
        self.assertEqual(config.lang, {})
        self.assertIn("pyproject.toml", config.paths["dependencies"])

    def test_setup_install_record_names_version_and_setup_date(self):
        """The install record has the plugin version, no commit, and the setup date."""
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(record["plugin"]["version"], plugin_version(self.plugin))
        self.assertNotIn("commit", record["plugin"])
        self.assertEqual(record["steps"], {"setup": DATE})

    def test_setup_install_record_covers_exactly_the_owned_files(self):
        """[files] lists troy-check, the templates, the workflow, and the PR template, only."""
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(sorted(record["files"]), sorted(owned_files(self.plugin)))

    def test_setup_install_record_hashes_match_the_written_files(self):
        """Each [files] hash is the SHA-256 of the file as written, CRLF made LF."""
        record = tomllib.loads(self.project.read(RECORD))
        for path, digest in record["files"].items():
            with self.subTest(path=path):
                self.assertEqual(digest, sha256_lf(self.project.read_bytes(path)))

    def test_setup_progress_file_says_stage_setup_and_next_requirements(self):
        """The progress file is filled in: stage setup, next action requirements."""
        text = self.project.read(PROGRESS)
        self.assertNotIn("{{", text)
        self.assertNotIn("<!-- template:", text)
        lines = text.split("\n")
        self.assertEqual(lines[0], "# Progress")
        stage = [line for line in lines if line.startswith("- Stage:")]
        following = [line for line in lines if line.startswith("- Next action:")]
        self.assertEqual(len(stage), 1, text)
        self.assertEqual(len(following), 1, text)
        self.assertIn("setup", stage[0])
        self.assertIn("requirements", following[0])

    def test_setup_progress_file_keeps_every_field_of_the_template(self):
        """Every '- Field:' line of the progress template is in the progress file."""
        template = read_text(self.plugin, "troy-mode/templates/progress.md")
        labels = [line.split(":")[0] + ":" for line in template.split("\n")
                  if line.startswith("- ")]
        lines = self.project.read(PROGRESS).split("\n")
        for label in labels:
            with self.subTest(label=label):
                self.assertEqual(len([line for line in lines if line.startswith(label)]), 1)

    def test_setup_progress_file_is_git_ignored(self):
        """git ignores the local progress file."""
        proc = git_proc(self.project.root, "check-ignore", "-q", PROGRESS)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_setup_rules_table_is_the_template_filled_in(self):
        """Both rules files are their template with name and date filled and comments removed."""
        for path, template in RULE_TEMPLATES.items():
            with self.subTest(path=path):
                expected = fill_rules_template(
                    read_text(self.plugin, f"troy-mode/templates/{template}"), PROJECT, DATE)
                self.assertEqual(nonblank_lines(self.project.read(path)), nonblank_lines(expected))

    def test_setup_rules_table_has_no_marker_or_template_comment(self):
        """No {{ and no HTML comment is left in either rules file."""
        for path in RULES:
            with self.subTest(path=path):
                text = self.project.read(path)
                self.assertNotIn("{{", text)
                self.assertNotIn("}}", text)
                self.assertNotIn("<!--", text)

    def test_setup_rules_mirrors_both_keep_version_one_with_the_date(self):
        """Both rules files have version 1.0 and updated set to the setup date."""
        en, zh = (front_matter(self.project.read(path)) for path in RULES)
        self.assertEqual((en["version"], zh["version"]), ("1.0", "1.0"))
        self.assertEqual((en["updated"], zh["updated"]), (DATE, DATE))
        self.assertEqual((en["troy-doc"], zh["troy-doc"]), ("rules", "rules"))

    def test_setup_rules_table_heading_names_the_folder(self):
        """The first heading names the project after the repository folder."""
        headings = [next(line for line in self.project.read(path).split("\n")
                         if line.startswith("# ")) for path in RULES]
        self.assertEqual(headings, [f"# {PROJECT} rules", f"# {PROJECT} 规则"])

    def test_setup_rules_rows_are_r01_to_r23_since_the_setup_date(self):
        """Both tables hold R01 to R23, each with the setup date as Since."""
        for path in RULES:
            with self.subTest(path=path):
                rows = rule_rows(self.project.read(path))
                self.assertEqual([row[2:5] for row in rows], [f"R{n:02d}" for n in range(1, 24)])
                self.assertEqual({row_since(row) for row in rows}, {DATE})

    def test_setup_creates_gitignore_with_the_progress_line(self):
        """A missing .gitignore is created, and its only pattern is the progress file."""
        patterns = [line for line in nonblank_lines(self.project.read(".gitignore"))
                    if not line.startswith("#")]
        self.assertEqual(patterns, [PROGRESS])

    def test_setup_sets_hooks_path_when_the_plugin_has_git_hooks(self):
        """core.hooksPath points at the copied git hooks, and the report says so."""
        self.assertEqual(self.project.config_value("core.hooksPath"), HOOKS_DIR)
        self.assertEqual(self.report()["hooks_path"], HOOKS_DIR)

    def test_setup_changes_no_other_git_config(self):
        """The only local git config setup adds is core.hooksPath."""
        added = set(self.config_after.split("\n")) - set(self.config_before.split("\n"))
        removed = set(self.config_before.split("\n")) - set(self.config_after.split("\n"))
        self.assertEqual(added, {f"core.hookspath={HOOKS_DIR}"})
        self.assertEqual(removed, set())

    def test_setup_lists_every_hook_file_as_executable(self):
        """executable lists each git hook file, and each is also staged."""
        report = self.report()
        self.assertEqual(report["executable"], hook_paths(self.plugin))
        self.assertEqual(len(report["executable"]), 4)
        self.assertLessEqual(set(report["executable"]), set(report["stage"]))

    @unittest.skipIf(os.name == "nt", "Windows has no executable bit on disk")
    def test_setup_writes_hook_files_executable_on_posix(self):
        """On Linux and macOS the copied hook files have the executable bit."""
        for path in hook_paths(self.plugin):
            with self.subTest(path=path):
                mode = os.stat(self.project.root / path).st_mode
                self.assertEqual(mode & stat.S_IXUSR, stat.S_IXUSR)

    def test_setup_reports_an_email_that_matches_git_config(self):
        """email holds --email, the repository's user.email, and that they match."""
        self.assertEqual(self.report()["email"],
                         {"wanted": EMAIL, "configured": EMAIL, "matches": True})

    def test_setup_leaves_the_existing_readme_alone(self):
        """A file setup does not write keeps its content and is not staged."""
        self.assertEqual(self.project.read("README.md"), f"# {PROJECT}\n")
        self.assertNotIn("README.md", self.report()["stage"])


if __name__ == "__main__":
    unittest.main()
