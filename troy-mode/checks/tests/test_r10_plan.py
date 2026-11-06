"""Tests for R10's comparison of tests with the feature's test plan (design 4.1)."""

import unittest

from code_helpers import run_code
from helpers import parallel
from prefetch import PrefetchedCase
from reports import FAIL, PASS, junit, tests

PLAN_PATH = "docs/features/F04-export/test-plan.md"
OTHER_PLAN_PATH = "docs/features/F05-import/test-plan.md"
CODE = {"src/a.py": "x = 1\n"}
COMPARED = {
    "tests": "[F04 4/6 tests] Tests",
    "impl": "[F04 5/6 impl] Export",
    "accept": "[F04 6/6 accept] Export",
    "test-fix": "[F04 test-fix] Fix a case",
}
NOT_COMPARED = {
    "design": "[F04 1/6 design] D",
    "test-plan": "[F04 2/6 test-plan] P",
    "mock": "[F04 3/6 mock] M",
    "docs": "[docs] D",
    "refactor": "[refactor] R",
    "rules": "[rules] R",
}


def plan(*ids: str, feature: str = "F04") -> str:
    """Builds a test plan document with a table of cases.

    Args:
        *ids: Case numbers such as ``01``.
        feature: The feature ID.

    Returns:
        The Markdown text.
    """
    rows = "".join(f"| {feature}-T{n} | Does thing {n}. | Unit |\n" for n in ids)
    return (
        f"# Test plan {feature}\n\nIntro text.\n\n"
        f"| Case | Description | Level |\n| --- | --- | --- |\n{rows}\nClosing text.\n"
    )


def names(*ids: str, status: str = PASS) -> list:
    """Builds testcases named after case numbers of F04.

    Args:
        *ids: Case numbers such as ``01``.
        status: Status of every case.

    Returns:
        A list of testcases.
    """
    return tests(status, *[f"test_f04_t{n}_does_thing" for n in ids])


def compare(title, cases, text, path=PLAN_PATH, in_base=False):
    """Runs ``code`` with a plan either in the PR or on main.

    Args:
        title: PR title.
        cases: JUnit testcases.
        text: Plan text, or None for no plan file.
        path: Plan path.
        in_base: Whether the plan is in the base commit instead of the PR.

    Returns:
        The outcome of the run.
    """
    files = {path: text} if text is not None else {}
    changes = dict(CODE) if in_base else {**CODE, **files}
    return run_code(
        title, changes, base_files=files if in_base else None, junit=[junit(cases)]
    )


class PlanComparisonTests(PrefetchedCase):
    """Warnings for planned cases without tests and tests without planned cases."""

    def test_matching_plan_passes(self):
        """When tests and plan list the same cases, R10 passes."""
        out = compare(COMPARED["impl"], names("01", "02"), plan("01", "02"))
        self.assert_rule(out, "R10", "pass")
        self.assert_clean(out)

    def test_planned_case_without_test_warns(self):
        """A case in the plan that has no test is a warning, not a failure."""
        out = compare(COMPARED["impl"], names("01"), plan("01", "02"))
        self.assert_rule(out, "R10", "warn")
        self.assert_exit(out, 0)
        self.assertTrue(out.report["ok"], out.describe())

    def test_test_without_planned_case_warns(self):
        """A test whose case is not in the plan is a warning."""
        out = compare(COMPARED["impl"], names("01", "09"), plan("01"))
        self.assert_rule(out, "R10", "warn")
        self.assert_exit(out, 0)

    def test_both_kinds_of_mismatch_still_warn(self):
        """Missing and extra cases together are still only a warning."""
        out = compare(COMPARED["impl"], names("03"), plan("01"))
        self.assert_rule(out, "R10", "warn")

    def test_failure_wins_over_warning(self):
        """An untagged test fails R10 even when the plan also differs."""
        cases = names("01") + tests(PASS, "test_untagged")
        out = compare(COMPARED["impl"], cases, plan("01", "02"))
        self.assert_rule(out, "R10", "fail")

    def test_no_plan_means_no_comparison(self):
        """Without a plan file, R10 does not warn about any test."""
        out = compare(COMPARED["impl"], names("01", "09"), None)
        self.assert_rule(out, "R10", "pass")

    def test_plan_on_main_is_used(self):
        """A plan that already exists in the base commit is compared too."""
        out = compare(COMPARED["impl"], names("01"), plan("01", "02"), in_base=True)
        self.assert_rule(out, "R10", "warn")

    def test_plan_of_another_feature_is_not_used(self):
        """Only the plan of the PR's own feature is compared."""
        out = compare(COMPARED["impl"], names("01", "09"), plan("01", feature="F05"), OTHER_PLAN_PATH)
        self.assert_rule(out, "R10", "pass")

    def test_parameter_instances_are_one_case(self):
        """Several parameter instances of one test cover one planned case once."""
        cases = tests(PASS, "test_f04_t01_a[1]", "test_f04_t01_a[2]")
        out = compare(COMPARED["impl"], cases, plan("01"))
        self.assert_rule(out, "R10", "pass")

    def test_plan_case_ids_ignore_case_and_dashes(self):
        """F04-T01 in the plan matches f04_t01 and F04-T01 test names."""
        cases = tests(PASS, "test_F04-T01_a", "test_f04_t02_b")
        out = compare(COMPARED["impl"], cases, plan("01", "02"))
        self.assert_rule(out, "R10", "pass")

    def test_googletest_names_are_compared(self):
        """A GoogleTest name covers its planned case."""
        out = compare(COMPARED["impl"], tests(PASS, "ExportCsv.F04_T01_Writes"), plan("01"))
        self.assert_rule(out, "R10", "pass")


class PlanKindTests(PrefetchedCase):
    """The comparison runs for tests, impl, accept, and test-fix only."""

    def test_compared_kinds_warn_on_a_missing_test(self):
        """Each compared kind warns when a planned case has no test."""
        def run(title):
            """Runs one PR kind with a plan that is longer than the tests."""
            return compare(title, names("01"), plan("01", "02"))

        for kind, out in zip(COMPARED, parallel(run, list(COMPARED.values()))):
            with self.subTest(kind=kind):
                self.assert_rule(out, "R10", "warn")

    def test_tests_pr_compares_failing_tests_too(self):
        """In a tests PR the failing tests are compared with the plan."""
        out = compare(COMPARED["tests"], names("01", status=FAIL), plan("01", "02"))
        self.assert_rule(out, "R10", "warn")
        self.assert_exit(out, 0)

    def test_other_kinds_do_not_compare(self):
        """Other kinds ignore the plan, whatever the tests are."""
        def run(title):
            """Runs one PR kind with a plan that differs from the tests."""
            return compare(title, names("09"), plan("01"))

        for kind, out in zip(NOT_COMPARED, parallel(run, list(NOT_COMPARED.values()))):
            with self.subTest(kind=kind):
                self.assert_rule(out, "R10", "pass")

    def test_bug_prs_do_not_compare(self):
        """Titles with a bug ID have no feature, so no plan is compared."""
        titles = ["[B12 A/B test] Crash", "[B12 B/B fix] Crash", "[B12 test-fix] Case"]
        cases = tests(PASS, "test_b12_x")
        outs = parallel(lambda t: compare(t, cases, plan("01")), titles)
        for title, out in zip(titles, outs):
            with self.subTest(title=title):
                self.assertNotEqual(out.status("R10"), "warn", out.describe())


if __name__ == "__main__":
    unittest.main()
