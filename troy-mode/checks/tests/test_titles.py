"""Tests for PR title parsing (design section 4), seen in the JSON report."""

import unittest

from helpers import CheckTestCase, parallel, pr_sandbox

STAGES = [(1, "design"), (2, "test-plan"), (3, "mock"), (4, "tests"), (5, "impl"), (6, "accept")]


class TitleTests(CheckTestCase):
    """Parses titles of every kind and rejects malformed ones."""

    @classmethod
    def setUpClass(cls):
        """Builds one PR repository shared by all title cases."""
        cls.sb = pr_sandbox({"src/app.py": "x = 1\n"})
        cls.addClassCleanup(cls.sb.close)

    def parsed(self, title):
        """Runs the checker on a title and returns the outcome."""
        out = self.sb.check_pr(title)
        self.assertIsNotNone(out.report, out.describe())
        return out

    def assert_parses(self, title, expected):
        """Asserts that the report's title holds at least the expected fields."""
        out = self.parsed(title)
        actual = out.report["title"]
        self.assertIsNotNone(actual, f"{title!r} did not parse\n" + out.describe())
        for key, value in expected.items():
            self.assertEqual(actual.get(key), value, f"{title!r}\n" + out.describe())

    def assert_all_rejected(self, titles):
        """Asserts that every title fails R02, skips R03, and reports no title."""
        for title, out in zip(titles, parallel(self.parsed, titles)):
            with self.subTest(title=title):
                self.assertIsNone(out.report["title"], f"{title!r}\n" + out.describe())
                self.assert_rule(out, "R02", "fail")
                self.assert_rule(out, "R03", "skip")
                self.assert_exit(out, 1)
                self.assertFalse(out.report["ok"])

    def test_every_feature_stage_parses(self):
        """Each of the six feature stages gives kind, id, stage and summary."""
        titles = [f"[F04 {n}/6 {name}] Export history as CSV" for n, name in STAGES]
        for (number, name), out in zip(STAGES, parallel(self.parsed, titles)):
            with self.subTest(stage=name):
                self.assertEqual(
                    out.report["title"],
                    {"kind": name, "id": "F04", "stage": f"{number}/6",
                     "summary": "Export history as CSV"},
                    out.describe(),
                )

    def test_three_digit_feature_id_parses(self):
        """A feature ID may have three digits."""
        self.assert_parses("[F123 5/6 impl] Big one", {"kind": "impl", "id": "F123"})

    def test_bug_test_title_parses(self):
        """Bug PR A has kind test and stage A/B."""
        self.assert_parses(
            "[B12 A/B test] Crash on empty history",
            {"kind": "test", "id": "B12", "stage": "A/B", "summary": "Crash on empty history"},
        )

    def test_bug_fix_title_parses(self):
        """Bug PR B has kind fix and stage B/B."""
        self.assert_parses(
            "[B12 B/B fix] Crash on empty history",
            {"kind": "fix", "id": "B12", "stage": "B/B", "summary": "Crash on empty history"},
        )

    def test_test_fix_title_takes_feature_or_bug_id(self):
        """A test fix names a feature ID or a bug ID."""
        self.assert_parses("[F04 test-fix] Wrong date format in F04-T03",
                           {"kind": "test-fix", "id": "F04",
                            "summary": "Wrong date format in F04-T03"})
        self.assert_parses("[B12 test-fix] Wrong date", {"kind": "test-fix", "id": "B12"})

    def test_other_kinds_parse(self):
        """The docs, rules and refactor kinds parse with their summaries."""
        cases = [
            ("[docs] Requirements change", "docs", "Requirements change"),
            ("[rules] Add P01, no global state", "rules", "Add P01, no global state"),
            ("[refactor] Split storage.py", "refactor", "Split storage.py"),
        ]
        for title, kind, summary in cases:
            with self.subTest(kind=kind):
                self.assert_parses(title, {"kind": kind, "summary": summary})

    def test_summary_keeps_punctuation_and_brackets(self):
        """The summary is everything after the closing bracket and one space."""
        self.assert_parses("[docs] Fix [x]: 100%, ok?", {"summary": "Fix [x]: 100%, ok?"})

    def test_chinese_summary_survives(self):
        """Non-ASCII summaries are passed through unchanged."""
        self.assert_parses("[docs] 更新中文文档", {"kind": "docs", "summary": "更新中文文档"})

    def test_stage_number_and_name_that_disagree_fail(self):
        """A stage number must go with its own stage name."""
        titles = ["[F04 3/6 impl] x", "[F04 5/6 mock] x", "[F04 1/6 accept] x",
                  "[F04 7/6 impl] x", "[F04 0/6 design] x", "[F04 5/5 impl] x"]
        self.assert_all_rejected(titles)

    def test_missing_summary_fails(self):
        """A title needs at least one non-space character after the bracket."""
        titles = ["[F04 5/6 impl]", "[F04 5/6 impl] ", "[docs]", "[docs] ",
                  "[B12 A/B test]", "[F04 test-fix]"]
        self.assert_all_rejected(titles)

    def test_malformed_ids_fail(self):
        """IDs are F plus 2-3 digits, or B plus digits, in capitals."""
        titles = ["[f04 5/6 impl] x", "[F4 5/6 impl] x", "[F1234 5/6 impl] x",
                  "[X04 5/6 impl] x", "[F04b 5/6 impl] x", "[b12 B/B fix] x",
                  "[B B/B fix] x", "[f04 test-fix] x", "[F4 test-fix] x"]
        self.assert_all_rejected(titles)

    def test_extra_or_missing_spaces_fail(self):
        """Spaces are single, and one space follows the closing bracket."""
        titles = ["[F04  5/6 impl] x", "[F04 5/6  impl] x", "[ F04 5/6 impl] x",
                  "[F04 5/6 impl ] x", "[F04 5/6 impl]x", "[docs]x"]
        self.assert_all_rejected(titles)

    def test_kind_names_are_case_sensitive_and_exact(self):
        """Unknown, wrongly cased or reworded kinds fail."""
        titles = ["[feat] x", "[Docs] x", "[DOCS] x", "[doc] x", "[rules ] x",
                  "docs: x", "Fix a bug", "[F04 5/6 IMPL] x", "[F04 test fix] x",
                  "[F04 TEST-FIX] x"]
        self.assert_all_rejected(titles)

    def test_bug_and_feature_patterns_do_not_mix(self):
        """Bug stages need a bug ID and feature stages need a feature ID."""
        titles = ["[B12 A/B fix] x", "[B12 B/B test] x", "[B12 A/A test] x",
                  "[F04 A/B test] x", "[B12 3/6 mock] x", "[F04 B/B fix] x",
                  "[B12 B/B fix x"]
        self.assert_all_rejected(titles)


if __name__ == "__main__":
    unittest.main()
