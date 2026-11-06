"""Tests for R01: the PR has exactly one commit."""

import unittest

from helpers import CheckTestCase, Sandbox, run_pr


class R01Tests(CheckTestCase):
    """Counts commits from the merge base to the head."""

    def test_one_commit_passes(self):
        """A single commit passes."""
        out = run_pr("[docs] One", {"docs/a.md": "a\n"})
        self.assert_rule(out, "R01", "pass")

    def test_two_commits_fail_and_are_listed(self):
        """Two commits fail, and the details list commits."""
        with Sandbox() as sb:
            sb.branch()
            sb.commit({"docs/a.md": "a\n"}, message="First")
            sb.commit({"docs/b.md": "b\n"}, message="Second")
            out = sb.check_pr("[docs] Two")
        self.assert_rule(out, "R01", "fail")
        self.assertTrue(out.details("R01"), out.describe())
        self.assert_exit(out, 1)
        self.assertFalse(out.report["ok"])

    def test_merge_commit_counts(self):
        """A merge commit counts, so a merge of a one-commit branch fails."""
        with Sandbox() as sb:
            sb.branch("side")
            sb.commit({"docs/s.md": "s\n"}, message="Side")
            sb.checkout("main")
            sb.branch("feature")
            sb.merge("side")
            out = sb.check_pr("[docs] Merge")
        self.assert_rule(out, "R01", "fail")

    def test_base_that_moved_on_still_counts_from_merge_base(self):
        """Commits that landed on the base after branching are not counted."""
        with Sandbox() as sb:
            sb.branch()
            sb.commit({"docs/a.md": "a\n"}, message="Mine")
            sb.checkout("main")
            sb.commit({"docs/other.md": "o\n"}, message="Landed meanwhile")
            out = sb.check_pr("[docs] Mine")
        self.assert_rule(out, "R01", "pass")

    def test_base_given_as_commit_sha_works(self):
        """The base may be a commit SHA instead of a branch name."""
        with Sandbox() as sb:
            sha = sb.git("rev-parse", "main").strip()
            sb.branch()
            sb.commit({"docs/a.md": "a\n"})
            out = sb.check_pr("[docs] Sha", base=sha)
        self.assert_rule(out, "R01", "pass")


if __name__ == "__main__":
    unittest.main()
