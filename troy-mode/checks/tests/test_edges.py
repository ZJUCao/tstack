"""Edge cases the design states that the first test pass left open.

Added after review: zero commits (R01), a binary file in a source PR (R03),
a Chinese mirror deleted alone (R12), and an unreadable --body-file (exit 2).
"""

import unittest

from builders import doc_pair, lines
from helpers import CheckTestCase, Sandbox, run_pr


class EdgeTests(CheckTestCase):
    """Behavior from design sections 3.1, 6.1, 6.3, and 6.4."""

    def test_zero_commits_fail_r01(self):
        """A head equal to the base has zero commits, which is not one."""
        with Sandbox() as sb:
            sb.branch()
            out = sb.check_pr("[docs] Nothing")
        self.assert_rule(out, "R01", "fail")
        self.assert_exit(out, 1)

    def test_binary_file_counts_as_a_file_for_r03(self):
        """A binary file adds no lines but still counts toward the 5-file limit."""
        changes = {f"src/m{i}.py": lines(2) for i in range(5)}
        changes["src/logo.bin"] = bytes(range(256))
        out = run_pr("[F04 5/6 impl] Logo", changes)
        self.assert_rule(out, "R03", "fail")

    def test_binary_file_alone_stays_within_limits(self):
        """A binary file counts 0 lines, so one alone passes R03."""
        out = run_pr("[F04 5/6 impl] Logo", {"src/logo.bin": bytes(range(256)) * 50})
        self.assert_rule(out, "R03", "pass")

    def test_deleting_only_the_chinese_mirror_fails_r12(self):
        """Point 5: a mirror deleted while its English document stays breaks the pair."""
        out = run_pr("[docs] Drop mirror", {"docs/x.zh-CN.md": None}, base_files=doc_pair())
        self.assert_rule(out, "R12", "fail")

    def test_missing_body_file_exits_two(self):
        """A --body-file that cannot be read stops the tool with exit code 2."""
        with Sandbox() as sb:
            sb.branch()
            sb.commit({"docs/a.md": "a\n"})
            out = sb.check_pr("[docs] A", extra_args=["--body-file", str(sb.tmp / "nope.md")])
        self.assert_exit(out, 2)


if __name__ == "__main__":
    unittest.main()
