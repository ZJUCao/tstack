"""Tests for R06: source file size, a soft limit (F03 design section 6)."""

import unittest

from builders import lines, pr_body
from prefetch import PrefetchedCase
from shape_runs import IMPL, TESTS, has_detail, run_py

BIG = lines(501, "x = 1")


class LimitTests(PrefetchedCase):
    """Covers the 500-line limit and the Soft-limit reason."""

    def test_500_lines_pass(self):
        """A file of exactly 500 lines passes."""
        out = run_py({"src/a.py": lines(500, "x = 1")})
        self.assert_rule(out, "R06", "pass")
        self.assert_exit(out, 0)

    def test_501_lines_without_reason_fail(self):
        """501 lines fail and the details name the file."""
        out = run_py({"src/a.py": BIG})
        self.assert_rule(out, "R06", "fail")
        self.assert_exit(out, 1)
        self.assertTrue(has_detail(out, "R06", "src/a.py"), out.describe())

    def test_501_lines_with_reason_warn(self):
        """With a reason the result is a warning and the run is clean."""
        out = run_py({"src/a.py": BIG}, body=pr_body("Splits next week."))
        self.assert_rule(out, "R06", "warn")
        self.assert_clean(out)
        self.assertTrue(has_detail(out, "R06", "src/a.py"), out.describe())

    def test_blank_and_comment_lines_count(self):
        """The limit counts every line, comments and blank lines included."""
        text = "# comment\n" * 250 + "\n" * 251
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R06", "fail")

    def test_missing_or_empty_reasons_fail(self):
        """None, None., 无, an empty section, and no section mean no reason."""
        bodies = [pr_body(None), pr_body(""), pr_body("None"), pr_body("None."),
                  pr_body("无"), "## Why\n\nBecause.\n", None]
        for body in bodies:
            with self.subTest(body=body):
                out = run_py({"src/a.py": BIG}, body=body)
                self.assert_rule(out, "R06", "fail")

    def test_real_reasons_warn(self):
        """Any real sentence counts as a reason."""
        for reason in ("Splits storage.py.", "None of it can move yet.", "拆分。"):
            with self.subTest(reason=reason):
                out = run_py({"src/a.py": BIG}, body=pr_body(reason))
                self.assert_rule(out, "R06", "warn")

    def test_configured_limit_is_used(self):
        """The limit comes from [limits] file_lines."""
        limits = {"file_lines": 100}
        ok = run_py({"src/a.py": lines(100, "x = 1")}, limits=limits)
        bad = run_py({"src/a.py": lines(101, "x = 1")}, limits=limits)
        self.assert_rule(ok, "R06", "pass")
        self.assert_rule(bad, "R06", "fail")


class SelectionTests(PrefetchedCase):
    """Covers which files R06 looks at and when it runs."""

    def test_any_extension_in_the_source_class_is_checked(self):
        """The limit is language-independent: C and JavaScript files count."""
        for path in ("src/big.c", "src/big.js", "src/big.hpp", "tool/big"):
            with self.subTest(path=path):
                out = run_py({path: lines(501, "int x;")})
                self.assert_rule(out, "R06", "fail")
                self.assertTrue(has_detail(out, "R06", path), out.describe())

    def test_r06_runs_without_a_language(self):
        """R06 needs no adapter."""
        out = run_py({"src/a.py": BIG}, name=None)
        self.assert_rule(out, "R06", "fail")

    def test_r06_runs_for_cpp(self):
        """R06 also runs when the language is cpp."""
        out = run_py({"src/a.cpp": lines(501, "int x;")}, name="cpp")
        self.assert_rule(out, "R06", "fail")

    def test_tests_class_files_are_not_checked(self):
        """A long test file is outside R06."""
        out = run_py({"tests/test_big.py": BIG}, title=TESTS)
        self.assertIn(out.status("R06"), ("pass", "skip"), out.describe())

    def test_docs_class_files_are_not_checked(self):
        """A long document is outside R06."""
        out = run_py({"docs/big.md": lines(900, "text")}, title="[docs] Big")
        self.assertIn(out.status("R06"), ("pass", "skip"), out.describe())

    def test_unchanged_big_file_is_not_checked(self):
        """An old file over the limit passes when the PR does not touch it."""
        out = run_py({"src/b.py": "x = 1\n"}, {"src/a.py": lines(600, "x = 1")})
        self.assert_rule(out, "R06", "pass")
        self.assert_exit(out, 0)

    def test_small_edit_of_a_big_file_is_checked(self):
        """Touching one line of an old oversized file fails it (Q6)."""
        base = {"src/a.py": lines(600, "x = 1")}
        out = run_py({"src/a.py": lines(599, "x = 1") + "x = 2\n"}, base)
        self.assert_rule(out, "R06", "fail")
        self.assertTrue(has_detail(out, "R06", "src/a.py"), out.describe())

    def test_deleted_big_file_is_not_checked(self):
        """Deleting an oversized file passes."""
        out = run_py({"src/a.py": None, "src/b.py": "x = 1\n"}, {"src/a.py": lines(600, "x = 1")})
        self.assert_rule(out, "R06", "pass")

    def test_shrinking_a_big_file_below_the_limit_passes(self):
        """The file is measured as it is at the head."""
        out = run_py({"src/a.py": lines(400, "x = 1")}, {"src/a.py": lines(600, "x = 1")})
        self.assert_rule(out, "R06", "pass")

    def test_every_big_file_is_listed(self):
        """Two oversized files are both named."""
        out = run_py({"src/a.py": BIG, "src/b.c": lines(502, "int x;"), "src/c.py": "x = 1\n"})
        self.assert_rule(out, "R06", "fail")
        self.assertTrue(has_detail(out, "R06", "src/a.py"))
        self.assertTrue(has_detail(out, "R06", "src/b.c"))
        self.assertFalse(has_detail(out, "R06", "src/c.py"))

    def test_small_files_pass_and_title_is_irrelevant(self):
        """A normal PR passes R06."""
        out = run_py({"src/a.py": "x = 1\n"}, title=IMPL)
        self.assert_rule(out, "R06", "pass")


if __name__ == "__main__":
    unittest.main()
