"""Tests for R01's subject check: the commit subject equals the PR title (D17)."""

import unittest

from helpers import CheckTestCase, Sandbox, parallel
from prefetch import PrefetchedCase, run_pr

TITLE = "[docs] Update notes"
CHANGE = {"docs/a.md": "a\n"}


class SubjectTests(PrefetchedCase):
    """The first line of the single commit's message against the title."""

    def test_equal_subject_passes(self):
        """A commit whose subject is the title passes R01 and the run is clean."""
        out = run_pr(TITLE, CHANGE, message=TITLE)
        self.assert_rule(out, "R01", "pass")
        self.assert_clean(out)

    def test_helper_default_message_is_the_title(self):
        """The test helpers commit with the title as message unless told otherwise."""
        self.assert_rule(run_pr(TITLE, CHANGE), "R01", "pass")

    def test_different_subject_fails(self):
        """A subject that differs from the title fails R01 with exit code 1."""
        out = run_pr(TITLE, CHANGE, message="[docs] Something else")
        self.assert_rule(out, "R01", "fail")
        self.assert_exit(out, 1)
        self.assertFalse(out.report["ok"], out.describe())

    def test_only_the_subject_line_counts(self):
        """Lines after the subject are ignored, so a body is allowed."""
        out = run_pr(TITLE, CHANGE, message=f"{TITLE}\n\nWhy this changed.\nMore text.")
        self.assert_rule(out, "R01", "pass")

    def test_title_in_the_body_is_not_the_subject(self):
        """The title on a later line does not make up for another subject."""
        out = run_pr(TITLE, CHANGE, message=f"Other\n\n{TITLE}")
        self.assert_rule(out, "R01", "fail")

    def test_trailing_whitespace_is_ignored(self):
        """Trailing whitespace on the title is stripped before comparing."""
        out = run_pr(TITLE + "   ", CHANGE, message=TITLE)
        self.assert_rule(out, "R01", "pass")

    def test_comparison_is_case_sensitive(self):
        """A subject that differs only in letter case fails."""
        out = run_pr(TITLE, CHANGE, message=TITLE.upper())
        self.assert_rule(out, "R01", "fail")

    def test_inner_spacing_matters(self):
        """Only trailing whitespace is stripped; inner spaces still differ."""
        out = run_pr(TITLE, CHANGE, message="[docs]  Update notes")
        self.assert_rule(out, "R01", "fail")

    def test_non_ascii_subject_passes(self):
        """A Chinese title equal to the subject passes."""
        title = "[docs] 更新中文文档"
        self.assert_rule(run_pr(title, CHANGE, message=title), "R01", "pass")

    def test_feature_stage_titles_are_compared_whole(self):
        """The whole title, brackets included, must equal the subject."""
        title = "[F04 5/6 impl] Export history as CSV"
        outs = parallel(
            lambda m: run_pr(title, {"src/a.py": "x = 1\n"}, message=m),
            [title, "Export history as CSV"],
        )
        self.assert_rule(outs[0], "R01", "pass")
        self.assert_rule(outs[1], "R01", "fail")

    def test_other_rules_do_not_depend_on_the_subject(self):
        """A subject mismatch fails only R01 for an otherwise valid PR."""
        out = run_pr(TITLE, CHANGE, message="Other subject")
        for rule in ("R02", "R12", "R19", "R20"):
            with self.subTest(rule=rule):
                self.assertNotEqual(out.status(rule), "fail", out.describe())


class CommitCountTests(CheckTestCase):
    """The one-commit rule next to the subject check."""

    def test_two_commits_still_fail_when_subjects_match(self):
        """The one-commit rule is unchanged by the subject check."""
        with Sandbox() as sb:
            sb.branch()
            sb.commit(CHANGE, message=TITLE)
            sb.commit({"docs/b.md": "b\n"}, message=TITLE)
            out = sb.check_pr(TITLE)
        self.assert_rule(out, "R01", "fail")


if __name__ == "__main__":
    unittest.main()
