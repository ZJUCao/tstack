"""Tests for the command line: report shape, exit codes, config, annotations."""

import re
import tempfile
import unittest
from pathlib import Path

from helpers import (
    CONFIG_PATH, EMAIL, OTHER_EMAIL, PR_RULES, CheckTestCase, Sandbox, base_env,
    lines, make_config, parallel, pr_sandbox, run_checker, run_pr, write_file,
)

TITLE = "[docs] Update notes"
RESULTS = {"pass", "warn", "fail", "skip"}


class ReportTests(CheckTestCase):
    """The JSON and text reports."""

    @classmethod
    def setUpClass(cls):
        """Builds one clean docs PR."""
        cls.sb = pr_sandbox({"docs/a.md": "a\n"})
        cls.addClassCleanup(cls.sb.close)

    def test_json_report_shape(self):
        """The JSON report has command, ok, title, and typed results."""
        out = self.sb.check_pr("[docs] Update notes")
        report = out.report
        self.assertEqual(report["command"], "pr")
        self.assertIs(report["ok"], True)
        self.assertEqual(report["title"]["kind"], "docs")
        for entry in report["results"]:
            self.assertIn(entry["result"], RESULTS)
            self.assertIsInstance(entry["message"], str)
            self.assertIsInstance(entry["details"], list)

    def test_pr_reports_every_rule_once(self):
        """A pr run has one result for each of R01, R02, R03, R12, R16, R19, R20."""
        out = self.sb.check_pr(TITLE)
        for rule in PR_RULES:
            self.assertIn(out.rule(rule)["result"], RESULTS)

    def test_detail_entries_have_path_line_and_message_keys(self):
        """Details carry path, line, and message keys."""
        out = run_pr(TITLE, {"src/app.py": "x\n"})
        detail = out.details("R02")[0]
        self.assertEqual(set(detail), {"path", "line", "message"}, out.describe())
        self.assertEqual(detail["path"], "src/app.py")

    def test_exit_zero_when_nothing_fails(self):
        """No failing rule gives exit code 0 and ok true."""
        out = self.sb.check_pr(TITLE)
        self.assert_exit(out, 0)

    def test_exit_zero_with_warnings(self):
        """A warning keeps exit code 0 and ok true."""
        config = make_config(paths={"dependencies": ["pyproject.toml"]})
        out = run_pr("[F04 5/6 impl] Dep", {"pyproject.toml": "x\n"}, config=config)
        self.assert_rule(out, "R16", "warn")
        self.assert_clean(out)

    def test_exit_one_when_a_rule_fails(self):
        """A failing rule gives exit code 1 and ok false."""
        out = run_pr(TITLE, {"src/app.py": "x\n"})
        self.assert_exit(out, 1)
        self.assertIs(out.report["ok"], False)

    def test_title_is_null_when_it_does_not_parse(self):
        """An unparsable title gives a null title in the report."""
        out = run_pr("nonsense", {"docs/a.md": "a\n"})
        self.assertIn("title", out.report)
        self.assertIsNone(out.report["title"])

    def test_text_report_lists_every_rule(self):
        """Without --json the report is text with one line per rule."""
        out = self.sb.check_pr(TITLE, json_report=False)
        self.assertTrue(out.stdout.startswith("troy-check pr:"), out.describe())
        for rule in PR_RULES:
            pattern = rf"^(pass|warn|fail|skip)\s+{rule}\b"
            self.assertRegex(out.stdout, re.compile(pattern, re.M))
        self.assertIn("Result:", out.stdout)

    def test_text_output_is_utf8(self):
        """Chinese text in the title survives a pipe on any console code page."""
        out = self.sb.check_pr("[docs] 更新中文文档", json_report=False)
        self.assertIn("更新中文文档", out.stdout, out.describe())

    def test_default_head_is_head(self):
        """Without --head the checkout's HEAD is the PR head."""
        out = self.sb.check_pr(TITLE, head=None)
        self.assert_rule(out, "R01", "pass")
        self.assert_exit(out, 0)

    def test_repo_defaults_to_the_git_top_level(self):
        """Without --repo the repository is found from a subfolder."""
        out = self.sb.check_pr(TITLE, from_cwd="docs")
        self.assert_rule(out, "R01", "pass")
        self.assert_exit(out, 0)


class ExitCodeTwoTests(CheckTestCase):
    """The tool could not run."""

    @classmethod
    def setUpClass(cls):
        """Builds one PR repository for the error cases."""
        cls.sb = pr_sandbox({"docs/a.md": "a\n"})
        cls.addClassCleanup(cls.sb.close)

    def test_bad_options_exit_two(self):
        """Missing or unknown options give exit code 2."""
        cases = [["pr"], ["pr", "--base", "main"], ["pr", "--title", "x"],
                 ["pr", "--base", "main", "--title", "x", "--bogus"], ["bogus"], []]
        for args in cases:
            with self.subTest(args=args):
                out = run_checker(args, self.sb.root, None)
                self.assert_exit(out, 2)

    def test_not_a_git_repository_exits_two(self):
        """A folder that is not a git repository gives exit code 2."""
        with tempfile.TemporaryDirectory() as plain:
            env = base_env({"GIT_CEILING_DIRECTORIES": str(Path(plain).parent)})
            args = ["pr", "--base", "main", "--title", TITLE, "--repo", plain, "--json"]
            self.assert_exit(run_checker(args, Path(plain), env), 2)
            args = ["pr", "--base", "main", "--title", TITLE]
            self.assert_exit(run_checker(args, Path(plain), env), 2)

    def test_unknown_base_ref_exits_two(self):
        """A git error, such as an unknown base, gives exit code 2."""
        self.assert_exit(self.sb.check_pr(TITLE, base="no-such-ref"), 2)

    def test_unknown_head_ref_exits_two(self):
        """An unknown head gives exit code 2."""
        self.assert_exit(self.sb.check_pr(TITLE, head="no-such-branch"), 2)

    def test_bad_commit_options_exit_two(self):
        """The commit command needs a message."""
        out = run_checker(["commit", "--repo", str(self.sb.root)], self.sb.tmp)
        self.assert_exit(out, 2)


INVALID_CONFIGS = {
    "unknown key in identity": '[identity]\ncommit_email = "a@b.test"\nnmae = "x"\n',
    "unknown key in limits": "[limits]\nsource_lnes = 5\n",
    "unknown key in paths": "[paths]\ndoc = []\n",
    "unknown section": "[bogus]\nx = 1\n",
    "unknown top-level key": "stray = 1\n",
    "string limit": '[limits]\nsource_lines = "500"\n',
    "float limit": "[limits]\nsource_files = 5.5\n",
    "string instead of list": '[paths]\ndocs = "docs/**"\n',
    "list of numbers": "[paths]\ndocs = [1, 2]\n",
    "numeric email": "[identity]\ncommit_email = 5\n",
    "numeric mode": "[attribution]\nmode = 3\n",
    "unknown mode": '[attribution]\nmode = "loose"\n',
    "malformed toml": "[limits\n",
}
FULL_CONFIG = """\
[identity]
commit_email = "troy@example.test"
[paths]
config = []
dependencies = []
tests = []
docs = []
lock = []
generated = []
allow_markers = []
[limits]
source_lines = 500
source_files = 5
[attribution]
mode = "trailers"
"""


class ConfigTests(CheckTestCase):
    """The project config file (design section 7)."""

    def test_invalid_config_exits_two_for_commit(self):
        """Unknown keys, wrong types, and bad TOML stop the tool with 2."""
        def run(text):
            """Runs the commit check with the given config text."""
            with Sandbox(config=text) as sb:
                return sb.check_commit(message="Fix", email=EMAIL)

        for name, out in zip(INVALID_CONFIGS, parallel(run, list(INVALID_CONFIGS.values()))):
            with self.subTest(case=name):
                self.assert_exit(out, 2)

    def test_valid_full_config_is_accepted(self):
        """A config that sets every documented key is valid."""
        with Sandbox(config=FULL_CONFIG) as sb:
            out = sb.check_commit(message="Fix", email=EMAIL)
        self.assert_exit(out, 0)

    def test_empty_config_is_accepted(self):
        """Every key is optional, so an empty file is valid."""
        with Sandbox(config="") as sb:
            out = sb.check_commit(message="Fix", email=EMAIL)
        self.assertIn(out.code, (0, 1), out.describe())

    def test_invalid_config_at_merge_base_exits_two_for_pr(self):
        """The pr command stops on an invalid config at the merge base."""
        for name in ("unknown section", "string limit", "malformed toml"):
            with self.subTest(case=name):
                out = run_pr(TITLE, {"docs/a.md": "a\n"}, config=INVALID_CONFIGS[name])
                self.assert_exit(out, 2)

    def test_pr_cannot_loosen_its_own_limits(self):
        """A config change inside the PR does not apply to that PR."""
        loose = make_config(limits={"source_lines": 5000})
        changes = {"src/a.py": lines(600), CONFIG_PATH: loose}
        out = run_pr("[F04 5/6 impl] Big", changes)
        self.assert_rule(out, "R03", "fail")

    def test_pr_cannot_change_the_commit_email_that_judges_it(self):
        """A PR that sets commit_email to its own author is still judged by the old one."""
        changes = {"docs/a.md": "a\n", CONFIG_PATH: make_config(email=OTHER_EMAIL)}
        out = run_pr(TITLE, changes, author=OTHER_EMAIL, committer=OTHER_EMAIL)
        self.assert_rule(out, "R19", "fail")

    def test_pr_cannot_break_the_checker_with_a_bad_config(self):
        """An invalid config added by the PR is ignored, since it is never read."""
        changes = {"docs/a.md": "a\n", CONFIG_PATH: "[bogus]\nx = 1\n"}
        out = run_pr(TITLE, changes)
        self.assertIn(out.code, (0, 1), out.describe())

    def test_config_is_read_from_merge_base_not_from_base_tip(self):
        """A config change that lands on the base after branching does not apply."""
        with Sandbox() as sb:
            sb.branch()
            sb.commit({"src/a.py": lines(600)})
            sb.checkout("main")
            sb.commit({CONFIG_PATH: make_config(limits={"source_lines": 5000})})
            out = sb.check_pr("[F04 5/6 impl] Big")
        self.assert_rule(out, "R03", "fail")

    def test_config_lists_add_to_builtin_patterns(self):
        """Adding a docs pattern does not remove the built-in docs patterns."""
        config = make_config(paths={"docs": ["notes/*.txt"]})
        out = run_pr(TITLE, {"notes/a.txt": "a\n", "docs/b.md": "b\n"}, config=config)
        self.assert_rule(out, "R02", "pass")


class AnnotationTests(CheckTestCase):
    """GitHub annotations and the step summary (design section 3.3)."""

    @classmethod
    def setUpClass(cls):
        """Runs one PR with R02 failures, an R16 warning, and an R20 failure."""
        config = make_config(paths={"dependencies": ["pyproject.toml"]})
        changes = {"src/app.py": "x\n", "pyproject.toml": "y\n",
                   "docs/guide.md": "a\nb\n{{todo}}\n"}
        cls.sb = pr_sandbox(changes, config=config)
        cls.addClassCleanup(cls.sb.close)
        cls.summary = cls.sb.tmp / "summary.md"
        cls.summary.write_text("previous\n", encoding="utf-8")
        env = {"GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": str(cls.summary)}
        cls.out = cls.sb.check_pr(TITLE, json_report=False, env_extra=env)
        cls.annotations = [x for x in cls.out.stdout.splitlines() if x.startswith("::")]

    def starting(self, prefix):
        """Returns the annotation lines that start with a prefix."""
        return [a for a in self.annotations if a.startswith(prefix)]

    def test_each_failing_detail_gets_an_error_annotation(self):
        """Every R02 failure gives one ::error annotation naming its file."""
        for path in ("src/app.py", "pyproject.toml"):
            with self.subTest(path=path):
                found = self.starting(f"::error file={path}")
                self.assertTrue(any("R02" in a for a in found), self.out.describe())

    def test_error_annotation_carries_the_line(self):
        """A failure with a line gives file and line in the annotation."""
        found = self.starting("::error file=docs/guide.md,line=3::")
        self.assertTrue(any("R20" in a for a in found), self.out.describe())

    def test_warning_gets_a_warning_annotation(self):
        """The R16 warning gives a ::warning annotation."""
        found = self.starting("::warning file=pyproject.toml")
        self.assertTrue(any("R16" in a for a in found), self.out.describe())

    def test_report_is_appended_to_the_step_summary(self):
        """The text report is appended after what the file already held."""
        text = self.summary.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("previous\n"), text)
        self.assertIn("R02", text)
        self.assertIn("R20", text)

    def test_no_annotations_outside_github_actions(self):
        """Without GITHUB_ACTIONS the tool prints plain text only."""
        out = self.sb.check_pr(TITLE, json_report=False)
        self.assertNotIn("::error", out.stdout)
        self.assertNotIn("::warning", out.stdout)
        self.assertEqual(self.summary.read_text(encoding="utf-8").count("previous"), 1)

    def test_false_value_does_not_enable_annotations(self):
        """Only the value true turns annotations on."""
        out = self.sb.check_pr(TITLE, json_report=False, env_extra={"GITHUB_ACTIONS": "false"})
        self.assertNotIn("::error", out.stdout)


if __name__ == "__main__":
    unittest.main()
