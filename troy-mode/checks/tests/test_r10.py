"""Tests for R10: test tags and which tests may fail (design 4.2)."""

import unittest
from pathlib import Path

from code_helpers import run_code
from helpers import CONFIG_PATH, make_config, parallel
from prefetch import PrefetchedCase
from reports import ERROR, FAIL, PASS, SKIP, Case, junit, tests

ACCEPT_F04 = "[F04 6/6 accept] Export history as CSV"
FIX_B12 = "[B12 B/B fix] Crash on empty history"
DOCS = "[docs] Notes"
F04 = "test_f04_t01_a"
F05 = "test_f05_t01_b"
B12 = "test_b12_crash"
B13 = "test_b13_other"
A_CHANGE = {"src/a.py": "x = 1\n"}


def r10(title, cases, history=(), **kwargs):
    """Runs ``code`` for a PR with one junit report and returns the outcome.

    Args:
        title: PR title.
        cases: JUnit testcases.
        history: Subjects of commits on main before the PR.
        **kwargs: Passed on to ``run_code``.

    Returns:
        The outcome of the run.
    """
    return run_code(title, A_CHANGE, history=history, junit=[junit(cases)], **kwargs)


class AcceptedAndFixedTests(PrefetchedCase):
    """Tests of accepted features and fixed bugs must pass in every PR."""

    def test_accepted_feature_must_pass(self):
        """A failing test of an accepted feature fails R10."""
        out = r10(DOCS, tests(FAIL, F04), history=[ACCEPT_F04])
        self.assert_rule(out, "R10", "fail")
        self.assert_exit(out, 1)

    def test_accepted_feature_passing_is_fine(self):
        """A passing test of an accepted feature passes R10."""
        out = r10(DOCS, tests(PASS, F04), history=[ACCEPT_F04])
        self.assert_rule(out, "R10", "pass")
        self.assert_clean(out)

    def test_error_skip_and_failure_all_count_as_not_passing(self):
        """Failure, error, and skipped must-pass tests all fail R10."""
        outs = parallel(lambda s: r10(DOCS, tests(s, F04), history=[ACCEPT_F04]), (FAIL, ERROR, SKIP))
        for status, out in zip((FAIL, ERROR, SKIP), outs):
            with self.subTest(status=status):
                self.assert_rule(out, "R10", "fail")

    def test_fixed_bug_must_pass(self):
        """A failing test of a fixed bug fails R10."""
        out = r10(DOCS, tests(FAIL, B12), history=[FIX_B12])
        self.assert_rule(out, "R10", "fail")

    def test_fixed_bug_passing_is_fine(self):
        """A passing test of a fixed bug passes."""
        self.assert_rule(r10(DOCS, tests(PASS, B12), history=[FIX_B12]), "R10", "pass")

    def test_unaccepted_feature_may_fail(self):
        """A failing test of a feature that is not accepted is allowed."""
        out = r10(DOCS, tests(FAIL, F05), history=[ACCEPT_F04])
        self.assert_rule(out, "R10", "pass")

    def test_unfixed_bug_may_fail(self):
        """A failing test of a bug that is not fixed is allowed."""
        out = r10(DOCS, tests(FAIL, B13), history=[FIX_B12])
        self.assert_rule(out, "R10", "pass")

    def test_unaccepted_may_also_be_skipped_or_error(self):
        """Any non-passing status of an unaccepted feature's test is allowed."""
        for status in (ERROR, SKIP):
            with self.subTest(status=status):
                self.assert_rule(r10(DOCS, tests(status, F05)), "R10", "pass")

    def test_no_history_means_nothing_is_accepted(self):
        """Without accept commits, even F04 tests may fail."""
        self.assert_rule(r10(DOCS, tests(FAIL, F04)), "R10", "pass")

    def test_stage_commits_other_than_accept_do_not_accept(self):
        """Impl, tests, and unrelated subjects do not accept F04."""
        history = ["[F04 5/6 impl] Export", "[F04 4/6 tests] Tests", "[B12 A/B test] Test"]
        out = r10(DOCS, tests(FAIL, F04) + tests(FAIL, B12), history=history)
        self.assert_rule(out, "R10", "pass")

    def test_subject_must_start_with_the_accept_marker(self):
        """A subject that only mentions the marker does not accept the feature."""
        history = [f"Revert {ACCEPT_F04}", "Notes\n\n" + ACCEPT_F04]
        out = r10(DOCS, tests(FAIL, F04), history=history)
        self.assert_rule(out, "R10", "pass")

    def test_deep_history_counts(self):
        """An accept commit several commits back is still found."""
        history = [ACCEPT_F04] + [f"[docs] Later {i}" for i in range(4)]
        self.assert_rule(r10(DOCS, tests(FAIL, F04), history=history), "R10", "fail")

    def test_commit_after_the_merge_base_does_not_count(self):
        """An accept that landed on main after the PR branched is not in its history."""
        out = r10(DOCS, tests(FAIL, F04), moved_on=[ACCEPT_F04])
        self.assert_rule(out, "R10", "pass")

    def test_bug_number_matches_whole_id(self):
        """Fixing B12 does not fix B120 or B1."""
        cases = tests(FAIL, "test_b120_x", "test_b1_y")
        self.assert_rule(r10(DOCS, cases, history=[FIX_B12]), "R10", "pass")

    def test_feature_number_matches_whole_id(self):
        """Accepting F04 does not accept F040."""
        out = r10(DOCS, tests(FAIL, "test_f040_t01_x"), history=[ACCEPT_F04])
        self.assert_rule(out, "R10", "pass")

    def test_three_digit_feature_ids(self):
        """A three-digit feature ID is accepted and matched."""
        accept = "[F123 6/6 accept] Big feature"
        out = r10(DOCS, tests(FAIL, "test_f123_t01_x"), history=[accept])
        self.assert_rule(out, "R10", "fail")

    def test_tags_match_ignoring_case_and_dashes(self):
        """A test tagged F04-T01 belongs to feature F04 whatever its spelling."""
        for name in ("test_F04-T01_x", "F04_T01_X", "test_f04_t01"):
            with self.subTest(name=name):
                out = r10(DOCS, tests(FAIL, name), history=[ACCEPT_F04])
                self.assert_rule(out, "R10", "fail")

    def test_googletest_name_in_accepted_feature_must_pass(self):
        """A GoogleTest name is read by its own name for the policy as well."""
        out = r10(DOCS, tests(FAIL, "ExportCsv.F04_T01_WritesHeader"), history=[ACCEPT_F04])
        self.assert_rule(out, "R10", "fail")


class KindTests(PrefetchedCase):
    """The table of section 4.2: what each PR kind must pass."""

    def test_tests_pr_lets_its_feature_fail(self):
        """In a tests PR for F04, F04 tests may fail."""
        out = r10("[F04 4/6 tests] Tests", tests(FAIL, F04))
        self.assert_rule(out, "R10", "pass")

    def test_tests_pr_still_needs_accepted_tests_to_pass(self):
        """A tests PR for F04 fails when an accepted feature's test fails."""
        out = r10("[F04 4/6 tests] Tests", tests(FAIL, F04, "test_f03_t01_x"), history=["[F03 6/6 accept] X"])
        self.assert_rule(out, "R10", "fail")

    def test_bug_test_pr_lets_its_bug_fail(self):
        """In a test PR for B12, B12 tests may fail."""
        out = r10("[B12 A/B test] Crash", tests(FAIL, B12))
        self.assert_rule(out, "R10", "pass")

    def test_impl_pr_needs_its_feature_to_pass(self):
        """In an impl PR for F04, a failing F04 test fails R10."""
        out = r10("[F04 5/6 impl] Export", tests(FAIL, F04))
        self.assert_rule(out, "R10", "fail")

    def test_impl_pr_with_passing_tests_passes(self):
        """In an impl PR, passing F04 tests pass, and another feature may fail."""
        out = r10("[F04 5/6 impl] Export", tests(PASS, F04) + tests(FAIL, F05))
        self.assert_rule(out, "R10", "pass")

    def test_impl_pr_skipped_feature_test_fails(self):
        """A skipped F04 test cannot hide behind a skip in an impl PR."""
        out = r10("[F04 5/6 impl] Export", tests(SKIP, F04))
        self.assert_rule(out, "R10", "fail")

    def test_accept_pr_needs_its_feature_to_pass(self):
        """In an accept PR for F04, a failing F04 test fails R10."""
        out = r10(ACCEPT_F04, tests(FAIL, F04))
        self.assert_rule(out, "R10", "fail")
        self.assert_rule(r10(ACCEPT_F04, tests(PASS, F04)), "R10", "pass")

    def test_fix_pr_needs_its_bug_to_pass(self):
        """In a fix PR for B12, a failing B12 test fails R10."""
        out = r10(FIX_B12, tests(FAIL, B12))
        self.assert_rule(out, "R10", "fail")
        self.assert_rule(r10(FIX_B12, tests(PASS, B12) + tests(FAIL, B13)), "R10", "pass")

    def test_other_kinds_only_need_accepted_tests(self):
        """In a docs PR, an unaccepted feature's failing test is allowed."""
        self.assert_rule(r10(DOCS, tests(FAIL, F04)), "R10", "pass")

    def test_test_fix_pr_does_not_need_its_feature_to_pass(self):
        """A test-fix PR is an 'other' kind, so F04 tests may still fail."""
        self.assert_rule(r10("[F04 test-fix] Fix a case", tests(FAIL, F04)), "R10", "pass")

    def test_refactor_pr_needs_accepted_tests_to_pass(self):
        """A refactor PR must keep accepted tests passing."""
        out = r10("[refactor] Tidy", tests(FAIL, F04), history=[ACCEPT_F04])
        self.assert_rule(out, "R10", "fail")


class MissingReportTests(PrefetchedCase):
    """A missing or broken junit file fails R10; it is not a usage error."""

    def test_missing_file_fails_r10(self):
        """A --junit path that does not exist fails R10 with exit code 1."""
        out = run_code(DOCS, junit=[Path("no-such.xml")])
        self.assert_rule(out, "R10", "fail")
        self.assert_exit(out, 1)

    def test_invalid_xml_fails_r10(self):
        """A file that is not valid XML fails R10 with exit code 1."""
        out = run_code(DOCS, junit=["this is <not xml"])
        self.assert_rule(out, "R10", "fail")
        self.assert_exit(out, 1)

    def test_empty_file_fails_r10(self):
        """An empty file is not valid XML."""
        self.assert_rule(run_code(DOCS, junit=[""]), "R10", "fail")

    def test_one_bad_file_among_good_ones_fails(self):
        """A broken second file fails R10 although the first is fine."""
        out = run_code(DOCS, junit=[junit(tests(PASS, F04)), "<broken"])
        self.assert_rule(out, "R10", "fail")

    def test_without_junit_skips(self):
        """With no --junit at all, R10 skips."""
        out = run_code(DOCS)
        self.assert_rule(out, "R10", "skip")
        self.assert_clean(out)

    def test_tests_pr_with_missing_file_fails_r10(self):
        """A missing file in a tests PR fails R10."""
        changes = {"tests/test_x.py": "x = 1\n"}
        out = run_code("[F04 4/6 tests] T", changes, junit=[Path("none.xml")])
        self.assert_rule(out, "R10", "fail")


LEGACY = '[tests]\nlegacy = ["tests/legacy/**", "old/*.py"]\n'


class LegacyTests(PrefetchedCase):
    """Untagged tests in files matched by ``[tests] legacy``."""

    def run_legacy(self, case, config=None, **kwargs):
        """Runs a docs PR with one case and the legacy config; returns R10's result."""
        text = make_config(extra=LEGACY) if config is None else config
        return r10(DOCS, [case], config=text, **kwargs).status("R10")

    def test_untagged_passing_legacy_test_by_file_passes(self):
        """An untagged passing test whose file matches a pattern passes."""
        case = Case("test_old_behaviour", file="tests/legacy/test_a.py")
        self.assertEqual(self.run_legacy(case), "pass")

    def test_untagged_failing_legacy_test_fails(self):
        """Untagged legacy tests must pass: a failure fails R10."""
        for status in (FAIL, ERROR, SKIP):
            with self.subTest(status=status):
                case = Case("test_old_behaviour", status, file="tests/legacy/test_a.py")
                self.assertEqual(self.run_legacy(case), "fail")

    def test_untagged_test_outside_legacy_fails(self):
        """A file outside the patterns gets no exception."""
        case = Case("test_new_behaviour", file="tests/new/test_a.py")
        self.assertEqual(self.run_legacy(case), "fail")

    def test_without_legacy_config_untagged_fails(self):
        """With no legacy patterns, an untagged test fails."""
        case = Case("test_old_behaviour", file="tests/legacy/test_a.py")
        self.assertEqual(self.run_legacy(case, config=make_config()), "fail")

    def test_single_star_stays_in_one_folder(self):
        """``old/*.py`` matches a file in old/ but not one in a subfolder."""
        near = Case("test_x", file="old/test_a.py")
        far = Case("test_x", file="old/deep/test_a.py")
        results = parallel(self.run_legacy, [near, far])
        self.assertEqual(results, ["pass", "fail"])

    def test_classname_is_used_without_file(self):
        """Without a file attribute, the classname with dots as slashes is matched."""
        case = Case("test_old_behaviour", classname="tests.legacy.test_a.TestOld")
        self.assertEqual(self.run_legacy(case), "pass")

    def test_classname_outside_patterns_fails(self):
        """A classname that maps outside the patterns gets no exception."""
        case = Case("test_new_behaviour", classname="tests.fresh.test_a.TestNew")
        self.assertEqual(self.run_legacy(case), "fail")

    def test_file_wins_over_classname_when_present(self):
        """With a file attribute, a matching classname does not help."""
        case = Case("test_x", classname="tests.legacy.test_a", file="tests/new/test_a.py")
        self.assertEqual(self.run_legacy(case), "fail")

    def test_classname_does_not_win_over_matching_file(self):
        """With a matching file, the classname is not consulted."""
        case = Case("test_x", classname="tests.fresh.test_a", file="tests/legacy/test_a.py")
        self.assertEqual(self.run_legacy(case), "pass")

    def test_tagged_legacy_tests_follow_the_normal_policy(self):
        """A tagged test in a legacy file is judged by its tag, not exempted."""
        case = Case(F04, FAIL, file="tests/legacy/test_a.py")
        result = self.run_legacy(case, history=[ACCEPT_F04])
        self.assertEqual(result, "fail")

    def test_legacy_patterns_come_from_the_merge_base(self):
        """A PR that adds legacy patterns to the config cannot use them."""
        case = Case("test_old", file="tests/legacy/test_a.py")
        out = run_code(
            DOCS, {CONFIG_PATH: make_config(extra=LEGACY)}, junit=[junit([case])]
        )
        self.assert_rule(out, "R10", "fail")


if __name__ == "__main__":
    unittest.main()
