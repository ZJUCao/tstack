"""Tests for the JUnit XML that CTest writes for GoogleTest (design 4.1 and 4.2)."""

import unittest

from cpp_builders import ctest_xml, run_cpp
from prefetch import PrefetchedCase

TESTS_PR = "[F01 4/6 tests] Tests for adds"
IMPL_PR = "[F01 5/6 impl] Adds"
ACCEPT_F01 = "[F01 6/6 accept] Adds numbers"
DOCS = "[docs] Notes"
ADDS = "Probe.F01_T01_Adds"
FAILS = "Probe.F01_T02_Fails"
CHANGE = {"src/a_test.cc": "int x;\n"}


def run(title, cases, history=()):
    """Runs the checker with one CTest report in a C/C++ project."""
    return run_cpp(CHANGE, title=title, junit=[ctest_xml(cases)], history=history)


class FailureAndPassTests(PrefetchedCase):
    """Covers how the status attribute and the failure element are read."""

    def test_status_fail_with_a_failure_element_counts_as_failed(self):
        """In a tests PR for F01, two failing CTest cases pass R09."""
        out = run(TESTS_PR, [(ADDS, "fail"), (FAILS, "fail")])
        self.assert_rule(out, "R09", "pass")

    def test_status_run_counts_as_passed(self):
        """A passing F01 case in a tests PR fails R09."""
        out = run(TESTS_PR, [(ADDS, "run"), (FAILS, "fail")])
        self.assert_rule(out, "R09", "fail")
        self.assert_exit(out, 1)

    def test_the_trimmed_real_report_in_an_impl_pr(self):
        """One passing and one failing F01 case fail R10 in an impl PR."""
        out = run(IMPL_PR, [(ADDS, "run"), (FAILS, "fail")])
        self.assert_rule(out, "R10", "fail")

    def test_all_passing_in_an_impl_pr_passes_r10(self):
        """Every F01 case passing satisfies an impl PR."""
        out = run(IMPL_PR, [(ADDS, "run"), (FAILS, "run")])
        self.assert_rule(out, "R10", "pass")
        self.assert_exit(out, 0)

    def test_accepted_feature_failing_case_fails_r10_in_any_pr(self):
        """History accepts F01, so a failing case fails R10 in a docs PR."""
        out = run(DOCS, [(ADDS, "fail")], history=[ACCEPT_F01])
        self.assert_rule(out, "R10", "fail")

    def test_accepted_feature_passing_case_is_fine(self):
        """The same history with a passing case passes R10."""
        out = run(DOCS, [(ADDS, "run")], history=[ACCEPT_F01])
        self.assert_rule(out, "R10", "pass")

    def test_unaccepted_feature_may_fail_in_a_docs_pr(self):
        """With no acceptance in history a failing case is allowed."""
        out = run(DOCS, [(ADDS, "fail")])
        self.assert_rule(out, "R10", "pass")


class TagTests(PrefetchedCase):
    """Covers how a ``Suite.Name`` test is tagged."""

    def test_suite_dot_case_is_tagged_f01_t01(self):
        """Probe.F01_T01_Adds belongs to F01 whatever the suite is called."""
        out = run(DOCS, [(ADDS, "run")])
        self.assert_rule(out, "R10", "pass")

    def test_other_suite_names_are_ignored_for_the_tag(self):
        """The suite part never counts, only the case's own name."""
        for name in ("Probe.F01_T01_Adds", "ExportCsv.F01_T01_Adds", "A.B.F01_T01_Adds"):
            with self.subTest(name=name):
                out = run(TESTS_PR, [(name, "fail")])
                self.assert_rule(out, "R09", "pass")

    def test_tag_is_read_through_r09(self):
        """A passing F02 case does not count against the F01 tests PR."""
        out = run(TESTS_PR, [(ADDS, "fail"), ("Probe.F02_T01_Other", "run")])
        self.assert_rule(out, "R09", "pass")

    def test_a_suite_with_an_id_but_a_name_without_one_is_untagged(self):
        """Only the case's own name holds the ID."""
        out = run(DOCS, [("F01_T01.Adds", "run")])
        self.assert_rule(out, "R10", "fail")

    def test_name_without_an_id_fails_r10(self):
        """A passing case with no ID fails R10 for its name."""
        out = run(DOCS, [("Probe.Adds", "run")])
        self.assert_rule(out, "R10", "fail")

    def test_bug_id_is_tagged(self):
        """Probe.B12_EmptyHistory is a bug test and needs no feature ID."""
        out = run(DOCS, [("Probe.B12_EmptyHistory", "run")])
        self.assert_rule(out, "R10", "pass")

    def test_dash_and_case_spelling_match_the_ctest_name(self):
        """F01-T01 in a CTest name is the same case as F01_T01."""
        out = run(TESTS_PR, [("Probe.f01-t01_adds", "run")])
        self.assert_rule(out, "R09", "fail")


class NotRunTests(PrefetchedCase):
    """Covers cases CTest did not run: they are not passing."""

    def test_notrun_and_disabled_do_not_satisfy_a_must_fail_test(self):
        """In a tests PR a case that did not run cannot stand in for a failure."""
        for status in ("notrun", "disabled"):
            with self.subTest(status=status):
                out = run(TESTS_PR, [(ADDS, status), (FAILS, "fail")])
                self.assert_rule(out, "R09", "fail")

    def test_notrun_and_disabled_do_not_satisfy_a_must_pass_test(self):
        """In an impl PR a case that did not run cannot count as passing."""
        for status in ("notrun", "disabled"):
            with self.subTest(status=status):
                out = run(IMPL_PR, [(ADDS, "run"), (FAILS, status)])
                self.assert_rule(out, "R10", "fail")

    def test_notrun_case_of_an_accepted_feature_fails_r10(self):
        """A skipped accepted test cannot hide behind the status attribute."""
        for status in ("notrun", "disabled"):
            with self.subTest(status=status):
                out = run(DOCS, [(ADDS, status)], history=[ACCEPT_F01])
                self.assert_rule(out, "R10", "fail")

    def test_notrun_case_of_an_unaccepted_feature_is_allowed(self):
        """A feature still in progress may have cases that do not run."""
        out = run(DOCS, [(ADDS, "notrun")])
        self.assert_rule(out, "R10", "pass")


if __name__ == "__main__":
    unittest.main()
