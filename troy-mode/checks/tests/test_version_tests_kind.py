"""Tests for F08's title kind ``[v<MAJOR>.<MINOR> tests]`` (F08 design 9, interface note 8).

The kind ``version-tests`` parses with the version as its ID, may change the
``tests`` and ``dependencies`` classes only, and is skipped by R03. The
built-in ``tests`` patterns gain ``version-tests/**``. R09 and R10 treat the
kind as "any other kind".
"""

import unittest
from pathlib import Path

from code_helpers import run_code
from helpers import CheckTestCase, lines, make_config, parallel, pr_sandbox
from prefetch import PrefetchedCase, run_pr
from reports import FAIL, PASS, junit, tests

CHECKS = Path(__file__).resolve().parents[1]
TITLE = "[v0.1 tests] End-to-end and stress tests"
ACCEPT_F04 = "[F04 6/6 accept] Export history as CSV"
FIX_B12 = "[B12 B/B fix] Crash on empty history"
F04 = "test_f04_t01_a"
F05 = "test_f05_t01_b"
B12 = "test_b12_crash"
VERSION_CHANGE = {"version-tests/test_v0_1.py": "x = 1\n"}
CONFIG = make_config(paths={"dependencies": ["requirements.txt"]})
CLASSES = {
    "version-tests/test_v0_1.py": "tests",
    "version-tests/data/big.txt": "tests",
    "tests/test_a.py": "tests",
    "test/data.md": "tests",
    "requirements.txt": "dependencies",
    "src/app.py": "source",
    "src/version-tests/helper.py": "source",
    "docs/guide.md": "docs",
    "README.md": "docs",
    ".troy-mode/a.txt": "config",
}


class VersionTitleTests(CheckTestCase):
    """The title parses with kind, version, and summary, and malformed ones do not."""

    @classmethod
    def setUpClass(cls):
        """Builds one PR repository shared by all title cases."""
        cls.sb = pr_sandbox(VERSION_CHANGE)
        cls.addClassCleanup(cls.sb.close)

    def parsed(self, title):
        """Runs ``pr`` on a title and returns the outcome."""
        out = self.sb.check_pr(title)
        self.assertIsNotNone(out.report, out.describe())
        return out

    def test_titles_parse(self):
        """Kind ``version-tests``, the version as the ID, no stage, and the summary."""
        cases = [(TITLE, "v0.1", "End-to-end and stress tests"),
                 ("[v12.30 tests] Fix v12.30-S03", "v12.30", "Fix v12.30-S03"),
                 ("[v1.0 tests] Add the stress case", "v1.0", "Add the stress case")]
        outs = parallel(self.parsed, [title for title, _, _ in cases])
        for (title, version, summary), out in zip(cases, outs):
            with self.subTest(title=title):
                self.assertEqual(out.report["title"],
                                 {"kind": "version-tests", "id": version, "stage": None,
                                  "summary": summary}, out.describe())

    def test_malformed_titles_are_rejected(self):
        """A wrong word, case, or version, extra or missing spaces, or no summary."""
        titles = ["[v0.1 test] x", "[V0.1 tests] x", "[v0.1.0 tests] x", "[v01.1 tests] x",
                  "[v0.01 tests] x", "[v0.1  tests] x", "[v0.1 tests]  x", "[v0.1 tests]x",
                  "[v0.1 tests]", "[v0.1 tests] ", "[v0 tests] x", "[0.1 tests] x",
                  "[v0.1 Tests] x", "[v0.1tests] x", "[ v0.1 tests] x"]
        for title, out in zip(titles, parallel(self.parsed, titles)):
            with self.subTest(title=title):
                self.assertIsNone(out.report["title"], f"{title!r}\n" + out.describe())
                self.assert_rule(out, "R02", "fail")
                self.assert_rule(out, "R03", "skip")
                self.assert_exit(out, 1)

    def test_text_report_names_the_version(self):
        """The text report's Kind line says ``version v0.1`` and what the kind may change."""
        out = self.sb.check_pr(TITLE, json_report=False)
        kind = [line for line in out.stdout.splitlines() if line.startswith("Kind:")]
        self.assertEqual(len(kind), 1, out.describe())
        self.assertIn("version v0.1", kind[0])
        self.assertIn("May change: tests, dependencies.", kind[0])


class VersionPathClassTests(CheckTestCase):
    """R02: the kind may change tests and dependencies; ``version-tests/**`` is tests."""

    @classmethod
    def setUpClass(cls):
        """Builds one PR that adds a file of each class."""
        cls.sb = pr_sandbox({path: "x\n" for path in CLASSES}, config=CONFIG)
        cls.addClassCleanup(cls.sb.close)

    def test_only_tests_and_dependencies(self):
        """R02 fails exactly for the paths outside the tests and dependencies classes."""
        out = self.sb.check_pr(TITLE)
        self.assert_rule(out, "R02", "fail")
        expected = [p for p, c in CLASSES.items() if c not in ("tests", "dependencies")]
        self.assertEqual(sorted(out.paths("R02")), sorted(expected), out.describe())

    def test_version_tests_folder_is_in_the_tests_class(self):
        """A docs PR may not change it, a feature tests PR may, and a nested folder is source."""
        docs, feature = parallel(self.sb.check_pr, ["[docs] x", "[F04 4/6 tests] x"])
        self.assertIn("version-tests/test_v0_1.py", docs.paths("R02"), docs.describe())
        self.assertIn("version-tests/data/big.txt", docs.paths("R02"), docs.describe())
        self.assertNotIn("version-tests/test_v0_1.py", feature.paths("R02"), feature.describe())
        self.assertNotIn("version-tests/data/big.txt", feature.paths("R02"), feature.describe())
        self.assertIn("src/version-tests/helper.py", feature.paths("R02"), feature.describe())


class VersionRuleTests(PrefetchedCase):
    """R02 passes for a clean PR of the kind, and R03 skips it (note section 8)."""

    def test_tests_and_a_dependency_pass_r02(self):
        """Version tests and a configured dependency file: R02 passes."""
        out = run_pr(TITLE, {**VERSION_CHANGE, "requirements.txt": "pytest\n"}, config=CONFIG)
        self.assert_rule(out, "R02", "pass")

    def test_r03_skips_the_kind(self):
        """2000 lines of version tests, or 900 of source: R03 skips, as for a tests PR."""
        cases = [{"version-tests/test_big.py": lines(2000)}, {"src/big.py": lines(900)}]
        outs = parallel(lambda changes: run_pr(TITLE, changes), cases)
        for changes, out in zip(cases, outs):
            with self.subTest(path=list(changes)[0]):
                self.assert_rule(out, "R03", "skip")
        self.assert_rule(outs[0], "R02", "pass")


class VersionTestPolicyTests(PrefetchedCase):
    """R09 skips the kind; R10 treats it as any other kind (F03, note section 8)."""

    def r10(self, cases, history=()):
        """Runs ``code`` for the kind with one JUnit report and returns R10's result."""
        out = run_code(TITLE, VERSION_CHANGE, history=history, junit=[junit(cases)])
        return out.status("R10")

    def test_r09_skips(self):
        """Passing or failing tests of a feature: R09 skips for the kind."""
        for status in (PASS, FAIL):
            with self.subTest(status=status):
                out = run_code(TITLE, VERSION_CHANGE, junit=[junit(tests(status, F04, B12))])
                self.assert_rule(out, "R09", "skip")

    def test_accepted_feature_and_fixed_bug_must_pass(self):
        """A failing test of an accepted feature or a fixed bug fails R10."""
        self.assertEqual(self.r10(tests(FAIL, F04), history=[ACCEPT_F04]), "fail")
        self.assertEqual(self.r10(tests(FAIL, B12), history=[FIX_B12]), "fail")

    def test_other_tests_may_fail(self):
        """A failing test of a feature not accepted or a bug not fixed is allowed."""
        self.assertEqual(self.r10(tests(FAIL, F05), history=[ACCEPT_F04]), "pass")
        self.assertEqual(self.r10(tests(FAIL, "test_b13_other"), history=[FIX_B12]), "pass")

    def test_passing_tests_pass(self):
        """Every test passing: R10 passes."""
        self.assertEqual(self.r10(tests(PASS, F04, B12), history=[ACCEPT_F04, FIX_B12]), "pass")


class DefaultConfigTests(unittest.TestCase):
    """``config.default.toml`` names ``version-tests/**`` among the built-in tests patterns."""

    def test_comment_names_the_folder(self):
        """A comment line holds ``version-tests/**``."""
        text = (CHECKS / "config.default.toml").read_bytes().decode("utf-8")
        comments = [line for line in text.replace("\r\n", "\n").split("\n")
                    if line.lstrip().startswith("#")]
        self.assertTrue(any("version-tests/**" in line for line in comments), comments)


if __name__ == "__main__":
    unittest.main()
