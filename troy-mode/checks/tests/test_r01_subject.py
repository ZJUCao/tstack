"""Tests for R01's subject check: the commit subject equals the PR title (D17)."""

import unittest

from helpers import CheckTestCase, Sandbox, parallel, pr_sandbox
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


def watch_commit_tree(sb, writes, error=None):
    """Makes a sandbox record each ``git commit-tree`` it runs.

    Args:
        sb: The sandbox.
        writes: List that gets the arguments of each ``commit-tree`` run.
        error: Raised instead of running ``commit-tree``, or None to run it.
    """
    real_git = sb.git

    def git(*args, **identity):
        if args[0] == "commit-tree":
            writes.append(args)
            if error is not None:
                raise error
        return real_git(*args, **identity)

    sb.git = git


class SharedSandboxTests(CheckTestCase):
    """Concurrent checks on one sandbox whose commit has the placeholder message."""

    def test_concurrent_checks_write_the_titled_commit_once(self):
        """Six checks of one title run ``git commit-tree`` once between them.

        Git for Windows cannot write one loose object from several processes
        at once ("unable to write file ... Permission denied"), so a shared
        sandbox where each check wrote the same titled commit failed now and
        then (test_r03's ReasonTests on Windows CI).
        """
        writes = []
        with pr_sandbox(CHANGE) as sb:
            watch_commit_tree(sb, writes)
            outs = parallel(lambda _: sb.check_pr(TITLE), range(6))
        self.assertEqual(len(writes), 1, writes)
        for out in outs:
            self.assert_rule(out, "R01", "pass")

    def test_failed_titled_commit_is_raised(self):
        """A git error while writing the titled commit stops the test.

        Checking the branch instead would check the placeholder subject and
        fail R01 with "subject: Change", which hides the real error.
        """
        with pr_sandbox(CHANGE) as sb:
            watch_commit_tree(sb, [], RuntimeError("git commit-tree failed"))
            with self.assertRaises(RuntimeError):
                sb.check_pr(TITLE)


if __name__ == "__main__":
    unittest.main()
