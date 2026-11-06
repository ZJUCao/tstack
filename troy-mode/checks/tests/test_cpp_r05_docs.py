"""Tests for R05 part (a) with the C/C++ adapter: Doxygen's warning log (design 6 and 9.3)."""

import unittest

from cpp_builders import MISSING_LOG, NT, IMPL, TESTS, detail_text, run_cpp
from prefetch import PrefetchedCase
from shape_builders import edit_line
from shape_runs import has_detail

WARN = "Member F (function) of namespace n is not documented."
TEXT = (
    "/// First.\n"            # 1
    "int First() {\n"          # 2
    "  int a = 1;\n"           # 3
    "  return a;\n"            # 4
    "}\n"                      # 5
    "\n"                       # 6
    "/// Second.\n"            # 7
    "int Second() {\n"         # 8
    "  int b = 2;\n"           # 9
    "  return b;\n"            # 10
    "}\n"                      # 11
)
EDITED = edit_line(TEXT, "int b = 2;", "int b = 3;")


def warning(path, line, text=WARN):
    """Builds one warning line of a Doxygen log."""
    return f"{path}:{line}: warning: {text}\n"


def new_file(log, **kwargs):
    """Runs the checker on a PR that adds src/a.cpp, with a warning log."""
    return run_cpp({"src/a.cpp": TEXT}, doc_warnings=log, **kwargs)


def edited_file(log, **kwargs):
    """Runs the checker on a PR that edits only line 9 of src/a.cpp."""
    return run_cpp({"src/a.cpp": EDITED}, {"src/a.cpp": TEXT}, doc_warnings=log, **kwargs)


class ReportTests(PrefetchedCase):
    """Covers warnings that fail R05."""

    def test_relative_path_on_a_changed_line_fails_with_the_text(self):
        """The detail names the file, the line, and the warning text."""
        out = new_file(warning("src/a.cpp", 2))
        self.assert_rule(out, "R05", "fail")
        self.assert_exit(out, 1)
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())
        self.assertIn("is not documented", detail_text(out, "R05"))

    def test_paths_with_dot_dot_segments_are_normalized(self):
        """A path that goes up and back down, as symlinks and short names can, still matches."""
        for form in ("src/../src/a.cpp", "{ROOT_POSIX}/src/../src/a.cpp"):
            with self.subTest(path=form):
                out = new_file(warning(form, 2))
                self.assert_rule(out, "R05", "fail")
                self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())

    def test_relative_path_forms(self):
        """Forward slashes, backslashes, and a leading dot all name the file."""
        for form in ("src/a.cpp", "src\\a.cpp", "./src/a.cpp", ".\\src\\a.cpp"):
            with self.subTest(path=form):
                out = new_file(warning(form, 2))
                self.assert_rule(out, "R05", "fail")
                self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())

    def test_absolute_path_with_forward_slashes(self):
        """A POSIX-style absolute path inside the repository is resolved."""
        out = new_file(warning("{ROOT_POSIX}/src/a.cpp", 2))
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())

    @unittest.skipUnless(NT, "needs a Windows-style repository root")
    def test_absolute_path_with_backslashes(self):
        """A Windows-style absolute path inside the repository is resolved."""
        out = new_file(warning("{ROOT_WIN}\\src\\a.cpp", 2))
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())

    def test_changed_line_of_an_edited_file_fails(self):
        """A warning on the one edited line of an existing file fails."""
        out = edited_file(warning("src/a.cpp", 9))
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 9), out.describe())

    def test_every_warning_on_changed_lines_is_listed(self):
        """Warnings in two files, and two in one file, are all named."""
        log = warning("src/a.cpp", 2) + warning("src/a.cpp", 8) + warning("src/b.cpp", 2)
        out = run_cpp({"src/a.cpp": TEXT, "src/b.cpp": TEXT}, doc_warnings=log)
        for path, line in (("src/a.cpp", 2), ("src/a.cpp", 8), ("src/b.cpp", 2)):
            self.assertTrue(has_detail(out, "R05", path, line), out.describe())

    def test_warning_in_a_tests_class_file_fails(self):
        """Changed files of the tests class are checked too."""
        out = run_cpp({"src/a_test.cc": TEXT}, title=TESTS,
                      doc_warnings=warning("src/a_test.cc", 2))
        self.assert_rule(out, "R05", "fail")

    def test_warning_in_a_header_fails(self):
        """A changed header is a changed C/C++ file."""
        out = run_cpp({"include/a.h": TEXT}, doc_warnings=warning("include/a.h", 2))
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "include/a.h", 2), out.describe())

    def test_continuation_lines_do_not_make_more_warnings(self):
        """Indented lines after a warning belong to it."""
        log = warning("src/a.cpp", 2) + "  The following parameter is not documented:\n    parameter 'x'\n"
        out = new_file(log)
        self.assert_rule(out, "R05", "fail")
        self.assertEqual(len(out.details("R05")), 1, out.describe())
        self.assertIn("parameter 'x'", detail_text(out, "R05"))


class IgnoredTests(PrefetchedCase):
    """Covers warnings that R05 leaves out."""

    def test_warning_on_an_unchanged_line_is_ignored(self):
        """Only line 9 changed, so a warning on line 2 passes."""
        out = edited_file(warning("src/a.cpp", 2))
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_warning_on_an_unchanged_file_is_ignored(self):
        """A file the PR does not change is not judged."""
        out = run_cpp({"src/a.cpp": TEXT}, {"src/b.cpp": TEXT},
                      doc_warnings=warning("src/b.cpp", 2))
        self.assert_rule(out, "R05", "pass")

    def test_warning_beyond_the_end_of_the_file_is_ignored(self):
        """A line that is not in the file is not a changed line."""
        self.assert_rule(new_file(warning("src/a.cpp", 99)), "R05", "pass")

    def test_warning_on_a_changed_file_that_is_not_c_or_cpp_is_ignored(self):
        """A changed Python or Markdown file is not read by the C/C++ adapter."""
        changes = {"src/a.py": "x = 1\n", "docs/n.md": "text\n", "src/a.cpp": TEXT}
        log = warning("src/a.py", 1) + warning("docs/n.md", 1)
        self.assert_rule(run_cpp(changes, doc_warnings=log), "R05", "pass")

    def test_warnings_outside_the_repository_are_ignored(self):
        """Paths that lead out of the repository do not name repository files."""
        outside = (
            "/elsewhere/src/a.cpp",
            "C:\\elsewhere\\src\\a.cpp",
            "../src/a.cpp",
            "{ROOT_POSIX}/../src/a.cpp",
            "{ROOT_POSIX}-other/src/a.cpp",
        )
        for path in outside:
            with self.subTest(path=path):
                out = new_file(warning(path, 2))
                self.assert_rule(out, "R05", "pass")

    def test_lines_that_do_not_match_the_format_are_ignored(self):
        """Banner lines and malformed warnings are skipped."""
        log = (
            "Doxygen version 1.9.8\n"
            "warning: no location at all\n"
            "src/a.cpp: warning: no line number\n"
            "src/a.cpp:2 warning: no colon after the line\n"
            "src/a.cpp:two: warning: line is not a number\n"
            "src/a.cpp:2: note: not a warning\n"
            "\n"
            "error: something else\n"
        )
        out = new_file(log)
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_indented_warning_like_line_is_a_continuation(self):
        """A warning-shaped line that starts with a space is not a warning."""
        log = warning("src/a.cpp", 99) + "  " + warning("src/a.cpp", 2)
        self.assert_rule(new_file(log), "R05", "pass")

    def test_empty_log_passes(self):
        """A log with no warnings means every touched definition is documented."""
        out = new_file("")
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_pr_with_no_cpp_file_and_a_log_passes(self):
        """A log is fine when the PR changes no C/C++ file."""
        out = run_cpp({"src/data.json": "{}\n"}, doc_warnings=warning("src/a.cpp", 2))
        self.assert_rule(out, "R05", "pass")


class LogOptionTests(PrefetchedCase):
    """Covers the --doc-warnings option itself."""

    def test_missing_log_fails_and_says_it_cannot_be_read(self):
        """A path that does not exist fails R05."""
        out = new_file(MISSING_LOG)
        self.assert_rule(out, "R05", "fail")
        self.assert_exit(out, 1)
        text = detail_text(out, "R05") + out.rule("R05")["message"]
        self.assertIn("read", text.lower(), out.describe())

    def test_no_log_and_no_cjk_skips_and_says_so(self):
        """Without the option R05 skips, and the message names the log."""
        out = new_file(None)
        self.assert_rule(out, "R05", "skip")
        self.assert_exit(out, 0)
        message = out.rule("R05")["message"].lower()
        self.assertIn("doxygen", message)
        self.assertIn("log", message)

    def test_a_log_alone_does_not_depend_on_the_pr_kind(self):
        """A warning on a changed line fails in a tests PR as well."""
        out = new_file(warning("src/a.cpp", 2), title=TESTS)
        self.assert_rule(out, "R05", "fail")
        out = new_file(warning("src/a.cpp", 2), title=IMPL)
        self.assert_rule(out, "R05", "fail")


if __name__ == "__main__":
    unittest.main()
