"""Tests for the ``test-fix`` title with a P ID (F09 design 5.4, 8; interface note 8).

``[P01 test-fix] Apply P01 to tests`` is a project rule's test cleanup. It
parses as kind ``test-fix`` with the rule's ID, may change the ``tests`` and
``dependencies`` classes only, and is skipped by R03 and R09. R10 never
looks for a test plan for a P ID and treats the PR as "any other kind".

Planted bug of F09 design 10.2 caught here: "``[P01 test-fix]`` allowed to
change source": ``RulePathClassTests.test_only_tests_and_dependencies`` and
``RuleR02Tests.test_source_or_docs_fail_r02``.
"""

import unittest

from code_helpers import run_code
from helpers import CheckTestCase, lines, make_config, parallel, pr_sandbox
from prefetch import PrefetchedCase, run_pr
from reports import FAIL, PASS, Case, junit, tests

TITLE = "[P01 test-fix] Apply P01 to tests"
ACCEPT_F04 = "[F04 6/6 accept] Export history as CSV"
FIX_B12 = "[B12 B/B fix] Crash on empty history"
F04 = "test_f04_t01_a"
F05 = "test_f05_t01_b"
B12 = "test_b12_crash"
TEST_CHANGE = {"tests/test_count.py": "x = 1\n"}
CONFIG = make_config(paths={"dependencies": ["requirements.txt"]})
LEGACY = make_config(extra='[tests]\nlegacy = ["tests/legacy/**"]\n')
CLASSES = {
    "tests/test_count.py": "tests",
    "tests/data/sample.txt": "tests",
    "test/data.md": "tests",
    "requirements.txt": "dependencies",
    "src/app.py": "source",
    "docs/guide.md": "docs",
    "README.md": "docs",
    ".troy-mode/config.toml.bak": "config",
    "docs/rules.md": "config",
}
F04_PLAN = "docs/features/F04-export/test-plan.md"
P01_PLAN = "docs/features/P01-cleanup/test-plan.md"


def plan(feature: str, *numbers: str) -> str:
    """A test plan document with a table of cases.

    Args:
        feature: The ID the case IDs start with.
        *numbers: Case numbers such as ``01``.

    Returns:
        The Markdown text.
    """
    rows = "".join(f"| {feature}-T{n} | Does thing {n}. | Unit |\n" for n in numbers)
    return (f"# Test plan {feature}\n\n| Case | Description | Level |\n| --- | --- | --- |\n"
            f"{rows}\n")


class RuleTitleTests(CheckTestCase):
    """The title parses with kind, rule ID, and summary; malformed ones do not."""

    @classmethod
    def setUpClass(cls):
        """Builds one PR repository shared by all title cases."""
        cls.sb = pr_sandbox(TEST_CHANGE)
        cls.addClassCleanup(cls.sb.close)

    def parsed(self, title):
        """Runs ``pr`` on a title and returns the outcome."""
        out = self.sb.check_pr(title)
        self.assertIsNotNone(out.report, out.describe())
        return out

    def test_titles_parse(self):
        """Kind ``test-fix``, the P ID with two or three digits, no stage, and the summary."""
        cases = [(TITLE, "P01", "Apply P01 to tests"), ("[P100 test-fix] x", "P100", "x"),
                 ("[P42 test-fix] Apply P42 to tests/legacy", "P42", "Apply P42 to tests/legacy")]
        outs = parallel(self.parsed, [title for title, _, _ in cases])
        for (title, rule_id, summary), out in zip(cases, outs):
            with self.subTest(title=title):
                self.assertEqual(out.report["title"],
                                 {"kind": "test-fix", "id": rule_id, "stage": None,
                                  "summary": summary}, out.describe())

    def test_malformed_titles_are_rejected(self):
        """One or four digits, a lower-case P, another kind word, or the P ID with a stage."""
        self.assertIsNotNone(self.parsed(TITLE).report["title"])
        titles = ["[P1 test-fix] x", "[p01 test-fix] x", "[P01 test] x", "[P0001 test-fix] x",
                  "[P01 A/B test] x", "[P01 B/B fix] x", "[P01 4/6 tests] x", "[P01  test-fix] x",
                  "[P01 test-fix]x", "[P01 test-fix]", "[P01 Test-fix] x", "[P01test-fix] x"]
        for title, out in zip(titles, parallel(self.parsed, titles)):
            with self.subTest(title=title):
                self.assertIsNone(out.report["title"], f"{title!r}\n" + out.describe())
                self.assert_rule(out, "R02", "fail")
                self.assert_rule(out, "R03", "skip")
                self.assert_exit(out, 1)

    def test_text_report_names_the_rule(self):
        """The text report's Kind line names the rule and what the kind may change."""
        out = self.sb.check_pr(TITLE, json_report=False)
        kind = [line for line in out.stdout.splitlines() if line.startswith("Kind:")]
        self.assertEqual(kind, ["Kind: test-fix, rule P01. May change: tests, dependencies."],
                         out.describe())


class RulePathClassTests(CheckTestCase):
    """R02: a ``[P01 test-fix]`` PR may change tests and dependencies only."""

    @classmethod
    def setUpClass(cls):
        """Builds one PR that adds a file of each class."""
        cls.sb = pr_sandbox({path: "x\n" for path in CLASSES}, config=CONFIG)
        cls.addClassCleanup(cls.sb.close)

    def test_only_tests_and_dependencies(self):
        """Planted bug "test-fix allowed to change source": R02 fails exactly for the source,
        docs, and config paths."""
        out = self.sb.check_pr(TITLE)
        self.assert_rule(out, "R02", "fail")
        expected = [p for p, c in CLASSES.items() if c not in ("tests", "dependencies")]
        self.assertEqual(sorted(out.paths("R02")), sorted(expected), out.describe())
        self.assert_exit(out, 1)


class RuleR02Tests(PrefetchedCase):
    """R02 and R03 for a clean or a mixed PR of the kind (note section 8)."""

    def test_tests_and_a_dependency_pass(self):
        """Test files and a configured dependency file: R02 passes."""
        out = run_pr(TITLE, {**TEST_CHANGE, "requirements.txt": "pytest\n"}, config=CONFIG)
        self.assert_rule(out, "R02", "pass")

    def test_source_or_docs_fail_r02(self):
        """Planted bug "test-fix allowed to change source": a source file, or a document, next
        to the tests fails R02 and names the path."""
        cases = {"src/wordcount/count.py": "x = 1\n", "docs/notes.md": "# Notes\n"}
        outs = parallel(lambda path: run_pr(TITLE, {**TEST_CHANGE, path: cases[path]}),
                        list(cases))
        for path, out in zip(cases, outs):
            with self.subTest(path=path):
                self.assert_rule(out, "R02", "fail")
                self.assert_paths(out, "R02", [path])

    def test_r03_skips_the_kind(self):
        """2000 lines of tests, or 900 of source: R03 skips, as for any test-fix PR."""
        cases = [{"tests/test_big.py": lines(2000)}, {"src/big.py": lines(900)}]
        outs = parallel(lambda changes: run_pr(TITLE, changes), cases)
        for changes, out in zip(cases, outs):
            with self.subTest(path=list(changes)[0]):
                self.assert_rule(out, "R03", "skip")
        self.assert_rule(outs[0], "R02", "pass")


class RulePolicyTests(PrefetchedCase):
    """R09 skips the kind; R10 compares no plan and treats it as any other kind (note 8)."""

    def r10(self, cases, history=(), **kwargs):
        """Runs ``code`` for the kind with one JUnit report and returns R10's result."""
        out = run_code(TITLE, TEST_CHANGE, history=history, junit=[junit(cases)], **kwargs)
        return out.status("R10")

    def test_r09_skips(self):
        """Passing or failing tests of a feature: R09 skips with "Not a test PR."."""
        for status in (PASS, FAIL):
            with self.subTest(status=status):
                out = run_code(TITLE, TEST_CHANGE, junit=[junit(tests(status, F04, B12))])
                self.assert_rule(out, "R09", "skip")
                self.assertEqual(out.rule("R09")["message"], "Not a test PR.", out.describe())

    def test_no_test_plan_is_compared(self):
        """Plans for F04 and under a ``P01-`` folder that the tests do not match: no warning.

        The same PR titled ``[F04 test-fix]`` warns, so the plans would be compared.
        """
        base = {F04_PLAN: plan("F04", "01", "02"), P01_PLAN: plan("P01", "01")}
        cases = tests(PASS, F04)
        outs = parallel(lambda title: run_code(title, TEST_CHANGE, base_files=base,
                                               junit=[junit(cases)]),
                        [TITLE, "[F04 test-fix] Wrong case in F04-T02"])
        self.assert_rule(outs[1], "R10", "warn")
        self.assert_rule(outs[0], "R10", "pass")
        self.assert_exit(outs[0], 0)

    def test_accepted_feature_and_fixed_bug_must_pass(self):
        """A failing test of an accepted feature or a fixed bug fails R10."""
        self.assertEqual(self.r10(tests(FAIL, F04), history=[ACCEPT_F04]), "fail")
        self.assertEqual(self.r10(tests(FAIL, B12), history=[FIX_B12]), "fail")

    def test_other_tests_may_fail(self):
        """A failing test of a feature not accepted or a bug not fixed is allowed."""
        self.assertEqual(self.r10(tests(FAIL, F05), history=[ACCEPT_F04]), "pass")
        self.assertEqual(self.r10(tests(FAIL, "test_b13_other"), history=[FIX_B12]), "pass")

    def test_untagged_legacy_tests_must_pass(self):
        """An untagged legacy test passes R10 when it passes and fails it when it fails."""
        passing = Case("test_old_behaviour", file="tests/legacy/test_a.py")
        failing = Case("test_old_behaviour", FAIL, file="tests/legacy/test_a.py")
        self.assertEqual(self.r10([passing], config=LEGACY), "pass")
        self.assertEqual(self.r10([failing], config=LEGACY), "fail")

    def test_passing_tests_pass(self):
        """Every test passing: R10 passes."""
        self.assertEqual(self.r10(tests(PASS, F04, B12), history=[ACCEPT_F04, FIX_B12]), "pass")


if __name__ == "__main__":
    unittest.main()
