"""Tests for the ``code`` subcommand's command line, report, and exit codes."""

import tempfile
import unittest
from pathlib import Path

from code_helpers import check_code, code_sandbox, run_code
from helpers import CONFIG_PATH, CheckTestCase, make_config, run_checker
from prefetch import PrefetchedCase
from reports import FAIL, PASS, junit, tests

TITLE = "[F04 5/6 impl] Export history as CSV"
CHANGES = {"src/app.py": "x = 1\n"}
RULES = ("R09", "R10", "R11")
GOOD_JUNIT = junit(tests(PASS, "test_f04_t01_writes_header"))


class CodeReportTests(CheckTestCase):
    """The report of a ``code`` run."""

    @classmethod
    def setUpClass(cls):
        """Builds one PR and runs ``code`` on it, with and without reports."""
        cls.sb = code_sandbox(TITLE, CHANGES)
        cls.addClassCleanup(cls.sb.close)
        cls.bare = check_code(cls.sb, TITLE)
        cls.full = check_code(cls.sb, TITLE, junit=[GOOD_JUNIT])

    def test_command_is_code_and_run_is_clean(self):
        """The JSON report names the command and a clean run exits with 0."""
        self.assertEqual(self.full.report["command"], "code", self.full.describe())
        self.assert_clean(self.full)

    def test_report_has_one_result_for_each_part_one_rule(self):
        """R09, R10, and R11 each appear exactly once."""
        for rule in RULES:
            with self.subTest(rule=rule):
                self.assertIn(self.full.status(rule), ("pass", "warn", "fail", "skip"))

    def test_results_are_in_rule_order(self):
        """Results come in the order R09, R10, R11."""
        order = [r["rule"] for r in self.full.report["results"] if r["rule"] in RULES]
        self.assertEqual(order, list(RULES), self.full.describe())

    def test_entries_have_message_and_details(self):
        """Every entry has a string message and a details list."""
        for entry in self.full.report["results"]:
            with self.subTest(rule=entry["rule"]):
                self.assertIsInstance(entry["message"], str)
                self.assertIsInstance(entry["details"], list)

    def test_title_is_parsed_in_the_report(self):
        """The report carries the parsed title like the pr command does."""
        title = self.full.report["title"]
        self.assertEqual((title["kind"], title["id"]), ("impl", "F04"), self.full.describe())

    def test_without_reports_every_rule_is_skipped(self):
        """With no --junit and no --coverage, R09, R10, and R11 skip."""
        for rule in RULES:
            with self.subTest(rule=rule):
                self.assert_rule(self.bare, rule, "skip")
        self.assert_clean(self.bare)

    def test_junit_alone_leaves_r11_skipped(self):
        """R11 needs --coverage, whatever else was given."""
        self.assert_rule(self.full, "R11", "skip")

    def test_text_report_is_printed_without_json(self):
        """Without --json the output is the text report and the exit code is 0."""
        out = check_code(self.sb, TITLE, json_report=False)
        self.assertIn("R10", out.stdout, out.describe())
        self.assert_exit(out, 0)

    def test_doc_warnings_option_is_accepted_and_ignored(self):
        """--doc-warnings takes a path and changes nothing in part 1."""
        log = self.sb.tmp / "doxygen.log"
        log.write_text("src/app.py:1: warning: not documented\n", encoding="utf-8")
        out = check_code(self.sb, TITLE, junit=[GOOD_JUNIT], extra_args=["--doc-warnings", str(log)])
        self.assert_clean(out)
        for rule in RULES:
            self.assertEqual(out.status(rule), self.full.status(rule), out.describe())

    def test_head_defaults_to_head(self):
        """Without --head the checked-out HEAD is the PR head."""
        out = check_code(self.sb, TITLE, junit=[GOOD_JUNIT], head=None)
        self.assert_clean(out)

    def test_repo_defaults_to_the_git_top_level(self):
        """Without --repo the repository is found from a subfolder."""
        out = check_code(self.sb, TITLE, junit=[GOOD_JUNIT], from_cwd="src")
        self.assert_clean(out)

    def test_base_may_be_a_commit_sha(self):
        """The base can be a commit SHA."""
        sha = self.sb.git("rev-parse", "main").strip()
        self.assert_clean(check_code(self.sb, TITLE, base=sha))


class MultipleReportTests(PrefetchedCase):
    """--junit may be given more than once."""

    def test_tests_in_every_file_are_judged(self):
        """An untagged test in the second file fails R10 as well."""
        first = junit(tests(PASS, "test_f04_t01_a"))
        second = junit(tests(PASS, "test_untagged"))
        out = run_code("[docs] Notes", junit=[first, second])
        self.assert_rule(out, "R10", "fail")

    def test_tagged_tests_in_two_files_pass(self):
        """Tagged passing tests spread over two files pass."""
        first = junit(tests(PASS, "test_f04_t01_a"))
        second = junit(tests(PASS, "test_f05_t01_b"))
        out = run_code("[docs] Notes", junit=[first, second])
        self.assert_rule(out, "R10", "pass")


class ExitCodeTests(CheckTestCase):
    """Exit code 2 means the tool could not run."""

    @classmethod
    def setUpClass(cls):
        """Builds a PR to run bad command lines against."""
        cls.sb = code_sandbox(TITLE, CHANGES)
        cls.addClassCleanup(cls.sb.close)

    def run_args(self, *args):
        """Runs ``code`` with raw arguments against the sandbox repository."""
        return run_checker(["code", "--repo", str(self.sb.root), *args], self.sb.tmp)

    def test_missing_base_exits_two(self):
        """--base is required."""
        self.assert_exit(self.run_args("--title", TITLE), 2)

    def test_missing_title_exits_two(self):
        """--title is required."""
        self.assert_exit(self.run_args("--base", "main"), 2)

    def test_unknown_option_exits_two(self):
        """An unknown option stops the tool."""
        self.assert_exit(self.run_args("--base", "main", "--title", TITLE, "--bogus"), 2)

    def test_unknown_base_exits_two(self):
        """A base that is not a ref is a git error."""
        self.assert_exit(check_code(self.sb, TITLE, base="no-such-ref"), 2)

    def test_unknown_head_exits_two(self):
        """A head that is not a ref is a git error."""
        self.assert_exit(check_code(self.sb, TITLE, head="no-such-branch"), 2)

    def test_not_a_git_repository_exits_two(self):
        """A folder that is no repository stops the tool."""
        with tempfile.TemporaryDirectory(prefix="troycheck-plain-") as plain:
            out = run_checker(
                ["code", "--base", "main", "--title", TITLE, "--repo", plain], Path(plain)
            )
        self.assert_exit(out, 2)

    def test_missing_body_file_exits_two(self):
        """A --body-file that cannot be read stops the tool."""
        missing = str(self.sb.tmp / "nope.md")
        out = check_code(self.sb, TITLE, extra_args=["--body-file", missing])
        self.assert_exit(out, 2)


class ExitCodeRunTests(PrefetchedCase):
    """Exit codes that depend on the config and on the reports."""

    def test_invalid_config_exits_two(self):
        """An unknown config key stops the code command like it stops pr."""
        out = run_code(TITLE, CHANGES, config="[bogus]\nx = 1\n")
        self.assert_exit(out, 2)

    def test_a_failing_rule_exits_one(self):
        """A failing R10 gives exit code 1 and ok false."""
        out = run_code(TITLE, CHANGES, junit=[junit(tests(PASS, "test_untagged"))])
        self.assert_exit(out, 1)
        self.assertFalse(out.report["ok"], out.describe())

    def test_config_comes_from_the_merge_base(self):
        """A legacy pattern added by the PR itself does not apply to the PR."""
        legacy = make_config(extra='[tests]\nlegacy = ["tests/**"]\n')
        out = run_code(
            TITLE, {CONFIG_PATH: legacy}, junit=[junit(tests(PASS, "test_x", file="tests/a.py"))]
        )
        self.assert_rule(out, "R10", "fail")

    def test_a_failing_rule_is_still_reported_with_all_rules(self):
        """When R10 fails, R09 and R11 are still in the report."""
        out = run_code(TITLE, CHANGES, junit=[junit(tests(FAIL, "test_untagged"))])
        for rule in RULES:
            out.rule(rule)


if __name__ == "__main__":
    unittest.main()
