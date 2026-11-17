"""``check-text``'s length check (F15 design 10.1, 13.1 "check-text"; interface note section 5).

GitHub refuses an issue body or a comment over 65,536 characters, so
``check-text`` fails on a file of more, counted as characters of the decoded
text, not bytes. Planted bug of design 13.2 caught here: "``check-text``'s
length check off by one": ``LengthTests.test_one_character_over_fails`` and
``test_exactly_the_limit_passes``.
"""

import json
import unittest

from flow_helpers import F01, Fakes, FlowCase, Project, base_step, stages

LIMIT = 65536


class LengthTests(FlowCase):
    """Files around the limit, in ASCII and in Chinese."""

    @classmethod
    def setUpClass(cls):
        """One clone whose config at HEAD sets ``strict``."""
        cls.project = Project([base_step(), *stages(F01, 1)])

    def check(self, text: str, name: str):
        """Writes the text, without a final line break, and runs ``check-text`` on it."""
        path = self.project.tmp / name
        path.write_bytes(text.encode("utf-8"))
        return self.project.run("check-text", "--file", str(path), fakes=Fakes(fail=True))

    def assert_too_long(self, out) -> None:
        """Exit 1 with one problem that says ``characters`` and ``65,536``."""
        report = self.report_of(out, 1, "check-text")
        self.assertEqual(len(report["problems"]), 1, report["problems"])
        problem = json.dumps(report["problems"][0], ensure_ascii=False)
        self.assertIn("characters", problem)
        self.assertIn("65,536", problem)

    def test_one_character_over_fails(self):
        """Planted bug "off by one": 65,537 characters fail, ASCII or Chinese."""
        self.assert_too_long(self.check("a" * (LIMIT + 1), "ascii-over.md"))
        self.assert_too_long(self.check("字" * (LIMIT + 1), "chinese-over.md"))

    def test_exactly_the_limit_passes(self):
        """Pair: 65,536 characters pass, ASCII or Chinese."""
        for name, text in (("ascii-limit.md", "a" * LIMIT), ("chinese-limit.md", "字" * LIMIT)):
            with self.subTest(file=name):
                report = self.report_of(self.check(text, name), 0, "check-text")
                self.assertEqual(report["problems"], [])

    def test_bytes_do_not_count(self):
        """30,000 Chinese characters (90,000 bytes) pass: the limit is in characters."""
        text = "字" * 30000
        self.assertGreater(len(text.encode("utf-8")), LIMIT)
        report = self.report_of(self.check(text, "chinese-bytes.md"), 0, "check-text")
        self.assertEqual(report["problems"], [])

    def test_attribution_check_is_unchanged(self):
        """A long clean file with one line naming Claude: the attribution problem, line 2."""
        text = "a" * 1000 + "\nReviewed with Claude.\n"
        report = self.report_of(self.check(text, "attribution.md"), 1, "check-text")
        self.assertEqual([p.get("line") for p in report["problems"]], [2])


if __name__ == "__main__":
    unittest.main()
