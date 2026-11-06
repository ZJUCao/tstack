"""Tests for R09: every new test in a test PR fails against the mock."""

import unittest

from code_helpers import run_code
from helpers import parallel
from prefetch import PrefetchedCase
from reports import ERROR, FAIL, PASS, SKIP, junit, tests

FEATURE_TESTS = "[F04 4/6 tests] Tests for export"
BUG_TEST = "[B12 A/B test] Crash on empty history"
TEST_CHANGES = {"tests/test_x.py": "x = 1\n"}
F04 = ("test_f04_t01_a", "test_f04_t02_b")
B12 = ("test_b12_empty_history", "test_b12_other")

OTHER_KINDS = {
    "design": "[F04 1/6 design] D",
    "test-plan": "[F04 2/6 test-plan] P",
    "mock": "[F04 3/6 mock] M",
    "impl": "[F04 5/6 impl] I",
    "accept": "[F04 6/6 accept] A",
    "bug fix": "[B12 B/B fix] F",
    "test-fix": "[F04 test-fix] T",
    "docs": "[docs] D",
    "rules": "[rules] R",
    "refactor": "[refactor] R",
}


def r09(title, cases, **kwargs):
    """Runs ``code`` for a test PR and returns R09's result.

    Args:
        title: PR title.
        cases: JUnit testcases.
        **kwargs: Passed on to ``run_code``.

    Returns:
        The result string of R09.
    """
    out = run_code(title, TEST_CHANGES, junit=[junit(cases)], **kwargs)
    return out.status("R09")


class FeatureTestsPrTests(PrefetchedCase):
    """A ``tests`` PR for F04: every F04 test must fail."""

    def test_all_failing_passes(self):
        """When every F04 test fails, R09 passes."""
        self.assertEqual(r09(FEATURE_TESTS, tests(FAIL, *F04)), "pass")

    def test_passing_test_fails(self):
        """A passing F04 test fails R09."""
        cases = tests(FAIL, F04[0]) + tests(PASS, F04[1])
        self.assertEqual(r09(FEATURE_TESTS, cases), "fail")

    def test_error_counts_as_failing(self):
        """A test with an error is a failing test."""
        self.assertEqual(r09(FEATURE_TESTS, tests(ERROR, *F04)), "pass")

    def test_skipped_test_fails(self):
        """A skipped test cannot stand in for a failing one."""
        cases = tests(FAIL, F04[0]) + tests(SKIP, F04[1])
        self.assertEqual(r09(FEATURE_TESTS, cases), "fail")

    def test_every_status_of_a_single_test(self):
        """Only failure and error satisfy R09."""
        statuses = (FAIL, ERROR, PASS, SKIP)
        results = parallel(lambda s: r09(FEATURE_TESTS, tests(s, F04[0])), statuses)
        self.assertEqual(results, ["pass", "pass", "fail", "fail"])

    def test_no_feature_tests_fails(self):
        """With no test of F04 at all, the must-fail set is empty and R09 fails."""
        out = run_code(FEATURE_TESTS, TEST_CHANGES, junit=[junit(tests(FAIL, "test_f05_t01_x"))])
        self.assert_rule(out, "R09", "fail")
        self.assert_exit(out, 1)

    def test_empty_junit_fails(self):
        """A report with no testcases leaves nothing to fail."""
        self.assertEqual(r09(FEATURE_TESTS, []), "fail")

    def test_other_features_tests_are_not_judged(self):
        """A passing test of another feature does not fail R09."""
        cases = tests(FAIL, *F04) + tests(PASS, "test_f05_t01_other")
        self.assertEqual(r09(FEATURE_TESTS, cases), "pass")

    def test_bug_tests_are_not_judged(self):
        """A passing bug test does not fail R09 of a feature PR."""
        cases = tests(FAIL, *F04) + tests(PASS, "test_b12_x")
        self.assertEqual(r09(FEATURE_TESTS, cases), "pass")

    def test_parameterized_test_needs_every_instance_failing(self):
        """Each parameter instance of an F04 test counts as a test."""
        cases = tests(FAIL, "test_f04_t01_a[1]") + tests(PASS, "test_f04_t01_a[2]")
        self.assertEqual(r09(FEATURE_TESTS, cases), "fail")

    def test_tag_matching_ignores_case_and_dashes(self):
        """F04-T01 and f04_t01 are tests of the same feature F04."""
        cases = tests(FAIL, "test_F04-T01_a") + tests(PASS, "test_f04_t02_b")
        self.assertEqual(r09(FEATURE_TESTS, cases), "fail")

    def test_feature_id_must_match_exactly(self):
        """A test of F040 is not a test of F04."""
        cases = tests(FAIL, *F04) + tests(PASS, "test_f040_t01_a")
        self.assertEqual(r09(FEATURE_TESTS, cases), "pass")

    def test_googletest_names_count(self):
        """A GoogleTest name with a suite prefix is read by its own name."""
        cases = tests(FAIL, "ExportCsv.F04_T01_WritesHeader") + tests(PASS, "ExportCsv.F04_T02_X")
        self.assertEqual(r09(FEATURE_TESTS, cases), "fail")

    def test_tests_across_two_files_are_all_judged(self):
        """A passing F04 test in the second --junit file fails R09."""
        out = run_code(
            FEATURE_TESTS, TEST_CHANGES,
            junit=[junit(tests(FAIL, F04[0])), junit(tests(PASS, F04[1]))],
        )
        self.assert_rule(out, "R09", "fail")


class BugTestPrTests(PrefetchedCase):
    """A ``test`` PR (bug A) for B12: every B12 test must fail."""

    def test_all_failing_passes(self):
        """When every B12 test fails, R09 passes."""
        self.assertEqual(r09(BUG_TEST, tests(FAIL, *B12)), "pass")

    def test_passing_test_fails(self):
        """A passing B12 test fails R09."""
        cases = tests(FAIL, B12[0]) + tests(PASS, B12[1])
        self.assertEqual(r09(BUG_TEST, cases), "fail")

    def test_skipped_test_fails(self):
        """A skipped B12 test fails R09."""
        self.assertEqual(r09(BUG_TEST, tests(SKIP, *B12)), "fail")

    def test_no_bug_tests_fails(self):
        """With no B12 test, R09 fails."""
        self.assertEqual(r09(BUG_TEST, tests(FAIL, "test_f04_t01_x")), "fail")

    def test_other_bug_numbers_are_not_judged(self):
        """B120 is another bug than B12, and a passing test of it is ignored."""
        cases = tests(FAIL, *B12) + tests(PASS, "test_b120_x")
        self.assertEqual(r09(BUG_TEST, cases), "pass")

    def test_feature_tests_are_not_judged(self):
        """A passing feature test does not fail R09 of a bug PR."""
        cases = tests(FAIL, *B12) + tests(PASS, "test_f04_t01_x")
        self.assertEqual(r09(BUG_TEST, cases), "pass")


class SkipTests(PrefetchedCase):
    """R09 applies only to ``tests`` and ``test`` PRs."""

    @classmethod
    def setUpClass(cls):
        """Builds a junit report with passing tests of F04 and B12."""
        cls.text = junit(tests(PASS, *F04, *B12))

    def test_other_kinds_skip(self):
        """Every other kind skips R09, even with passing tests of the feature."""
        def run(title):
            """Runs the code command for one PR title."""
            return run_code(title, {"src/a.py": "x = 1\n"}, junit=[self.text])

        outs = parallel(run, list(OTHER_KINDS.values()))
        for kind, out in zip(OTHER_KINDS, outs):
            with self.subTest(kind=kind):
                self.assert_rule(out, "R09", "skip")

    def test_without_junit_skips(self):
        """Without --junit, R09 skips even for a tests PR."""
        out = run_code(FEATURE_TESTS, TEST_CHANGES)
        self.assert_rule(out, "R09", "skip")
        self.assert_clean(out)

    def test_without_junit_skips_for_bug_test_pr(self):
        """Without --junit, R09 skips for a bug test PR too."""
        self.assert_rule(run_code(BUG_TEST, TEST_CHANGES), "R09", "skip")

    def test_title_that_does_not_parse_does_not_apply_r09(self):
        """A title that matches no pattern is no tests PR, so R09 does not fail."""
        out = run_code("not a title", TEST_CHANGES, junit=[self.text])
        self.assertNotEqual(out.status("R09"), "fail", out.describe())


if __name__ == "__main__":
    unittest.main()
