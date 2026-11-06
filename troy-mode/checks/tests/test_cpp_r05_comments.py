"""Tests for R05 part (b) with the C/C++ adapter: no CJK in comments (design D23)."""

import unittest

from cpp_builders import TESTS, cfunc, run_cpp
from prefetch import PrefetchedCase
from shape_builders import ALLOWED_TEXT, CJK, edit_line, line_of
from shape_runs import has_detail

HAN = CJK["ideograph"]
EMPTY_LOG = ""


def src(*rows):
    """Joins rows into a file text that ends in a line feed."""
    return "\n".join(rows) + "\n"


def body(*rows):
    """Wraps rows in a documented function and returns the file text."""
    inner = "".join(f"  {row}\n" for row in rows)
    return "/// Does it.\nint F() {\n" + inner + "  return 0;\n}\n"


def check(text, path="src/a.cpp", log=None, **kwargs):
    """Runs the checker on one new file."""
    return run_cpp({path: text}, doc_warnings=log, **kwargs)


class CommentKindTests(PrefetchedCase):
    """Covers each kind of comment that can hold CJK text."""

    def test_each_comment_form_fails_on_its_line(self):
        """//, ///, /* */, and /** */ comments are all read."""
        forms = {
            "line": f"// note {HAN} end",
            "doc line": f"/// note {HAN} end",
            "block": f"/* note {HAN} end */",
            "doc block": f"/** note {HAN} end */",
            "bang": f"//! note {HAN} end",
        }
        for label, row in forms.items():
            with self.subTest(form=label):
                text = src("int x;", row, "int y;")
                out = check(text)
                self.assert_rule(out, "R05", "fail")
                self.assert_exit(out, 1)
                self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())

    def test_trailing_comments_are_read(self):
        """A comment after code on the same line fails."""
        for tail in (f"// {HAN}", f"/* {HAN} */"):
            with self.subTest(tail=tail):
                out = check(src("int x = 1;  " + tail))
                self.assert_rule(out, "R05", "fail")
                self.assertTrue(has_detail(out, "R05", "src/a.cpp", 1), out.describe())

    def test_multi_line_block_comment_flags_the_line_with_the_text(self):
        """Only the line of a block comment that holds CJK text is named."""
        text = src("/**", " * Fine line.", f" * Bad {HAN} line.", " * Fine again.", " */", "int x;")
        out = check(text)
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 3), out.describe())
        self.assertFalse(has_detail(out, "R05", "src/a.cpp", 2))
        self.assertFalse(has_detail(out, "R05", "src/a.cpp", 4))

    def test_block_comment_opener_inside_a_line_comment_is_just_text(self):
        """A /* inside // does not start a block that hides later lines."""
        text = src("// start /*", f"// {HAN}", "int x;")
        out = check(text)
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())

    def test_comments_inside_function_bodies_are_read(self):
        """A comment inside a body fails like any other."""
        out = check(body(f"// {HAN}"))
        self.assert_rule(out, "R05", "fail")

    def test_every_listed_character_class_fails(self):
        """Each Unicode range of the design fails on its own comment line."""
        for name, char in CJK.items():
            with self.subTest(range=name):
                text = src("int x;", f"// note {char} end")
                out = check(text)
                self.assert_rule(out, "R05", "fail")
                self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())

    def test_allowed_characters_pass(self):
        """Accented letters, arrows, and symbols are not CJK."""
        for name, text in ALLOWED_TEXT.items():
            with self.subTest(text=name):
                out = check(src(f"/// Does {text}.", "int x;", f"// {text}"), log=EMPTY_LOG)
                self.assert_rule(out, "R05", "pass")

    def test_header_and_c_files_are_read(self):
        """CJK in a .h and a .c file fails."""
        for path in ("include/a.h", "src/a.c", "src/a.hpp"):
            with self.subTest(path=path):
                out = check(src(f"// {HAN}"), path=path)
                self.assert_rule(out, "R05", "fail")
                self.assertTrue(has_detail(out, "R05", path, 1), out.describe())

    def test_tests_class_files_are_read(self):
        """CJK in a *_test.cc file fails."""
        out = check(src(f"// {HAN}"), path="src/a_test.cc", title=TESTS)
        self.assert_rule(out, "R05", "fail")


class LiteralTests(PrefetchedCase):
    """Covers text that only looks like a comment."""

    def test_cjk_in_literals_is_fine(self):
        """Strings, characters, wide and raw strings may hold any text."""
        rows = [
            f'const char* a = "{HAN}";',
            f'const char* b = "// {HAN}";',
            f'const char* c = "/* {HAN} */";',
            f"char16_t d = u'{HAN}';",
            f'const wchar_t* e = L"{HAN}";',
            f'const char* f = u8"{HAN}";',
            f'const char* g = "\\"// {HAN}";',
            f'const char* h = R"({HAN} // {HAN} /* {HAN})";',
            f'const char* i = R"x({HAN} )" // {HAN} )x";',
        ]
        out = check(body(*rows), log=EMPTY_LOG)
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_multi_line_raw_string_is_not_a_comment(self):
        """Lines inside a raw string that start with // are text."""
        text = src("/// Does it.", "const char* kText = R\"(", f"// {HAN}", f"/* {HAN}", ")\";")
        out = check(text, log=EMPTY_LOG)
        self.assert_rule(out, "R05", "pass")

    def test_a_comment_after_a_tricky_literal_is_still_a_comment(self):
        """The scanner leaves each literal at the right place."""
        tricky = {
            "double quote in a char": "char q = '\"';",
            "single quote in a string": 'const char* q = "\'";',
            "escaped quote char": "char q = '\\'';",
            "escaped backslash string": 'const char* q = "\\\\";',
            "raw string with quote": 'const char* q = R"(a"b)";',
            "raw string with delimiter": 'const char* q = R"x(a)" b)x";',
            "digit separators": "int q = 1'000'000;",
            "one digit separator": "int q = 1'000;",
            "two strings": 'const char* q = "a" "b";',
        }
        for label, code in tricky.items():
            with self.subTest(case=label):
                text = src(f"{code}  // {HAN}")
                out = check(text)
                self.assert_rule(out, "R05", "fail")
                self.assertTrue(has_detail(out, "R05", "src/a.cpp", 1), out.describe())

    def test_a_backslash_continues_a_line_comment(self):
        """A // comment that ends in a backslash goes on to the next line."""
        text = src("int a = 1;  // note \\", f"    {HAN} more", "int b = 2;")
        out = check(text)
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())

    def test_a_block_comment_after_a_string_is_still_a_comment(self):
        """A /* */ comment that follows a string on the same line is read."""
        text = src(f'const char* q = "x"; /* {HAN} */')
        self.assert_rule(check(text), "R05", "fail")


class ChangedLineTests(PrefetchedCase):
    """Covers the rule that only changed comment lines are judged."""

    OLD = src("/// Does it.", f"// {HAN} old note", "int x = 1;", "int y = 2;")

    def test_cjk_on_an_unchanged_comment_line_is_ignored(self):
        """An old CJK comment passes when the PR changes another line."""
        text = edit_line(self.OLD, "int y = 2;", "int y = 3;")
        out = run_cpp({"src/a.cpp": text}, {"src/a.cpp": self.OLD}, doc_warnings=EMPTY_LOG)
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_cjk_on_an_unchanged_block_comment_line_is_ignored(self):
        """Editing one line of a block comment leaves its other lines alone."""
        old = src("/*", f" * {HAN} old", " * Old two.", " */", "int x;")
        text = edit_line(old, "* Old two.", "* New two.")
        out = run_cpp({"src/a.cpp": text}, {"src/a.cpp": old}, doc_warnings=EMPTY_LOG)
        self.assert_rule(out, "R05", "pass")

    def test_rewriting_the_cjk_comment_in_english_passes(self):
        """The PR that fixes the comment passes."""
        text = edit_line(self.OLD, f"// {HAN} old note", "// English note")
        out = run_cpp({"src/a.cpp": text}, {"src/a.cpp": self.OLD}, doc_warnings=EMPTY_LOG)
        self.assert_rule(out, "R05", "pass")

    def test_changing_the_cjk_comment_line_itself_fails(self):
        """An edit to a CJK comment line keeps it a changed line."""
        text = edit_line(self.OLD, f"// {HAN} old note", f"// {HAN} new note")
        out = run_cpp({"src/a.cpp": text}, {"src/a.cpp": self.OLD}, doc_warnings=EMPTY_LOG)
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", line_of(text, HAN)))


class WithAndWithoutLogTests(PrefetchedCase):
    """Covers how CJK checks combine with the Doxygen log."""

    def test_cjk_fails_without_a_log(self):
        """CJK problems fail R05 even when no log was given."""
        text = body(f"// {HAN}")
        out = check(text)
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", line_of(text, HAN)), out.describe())

    def test_clean_comments_without_a_log_skip(self):
        """With no CJK and no log the result is skip."""
        out = check(body("// English only."))
        self.assert_rule(out, "R05", "skip")
        self.assert_exit(out, 0)

    def test_cjk_fails_with_a_clean_log(self):
        """A log with no warnings does not hide CJK."""
        out = check(body(f"// {HAN}"), log=EMPTY_LOG)
        self.assert_rule(out, "R05", "fail")

    def test_clean_comments_with_a_clean_log_pass(self):
        """No warnings and no CJK pass."""
        out = check(body("// English only."), log=EMPTY_LOG)
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_a_warning_and_cjk_are_both_reported(self):
        """Two kinds of defect on two lines give two detail entries."""
        text = src("/// Fine.", "int F() { return 1; }", f"// {HAN}")
        log = "src/a.cpp:2: warning: Member F is not documented.\n"
        out = check(text, log=log)
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 2), out.describe())
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 3), out.describe())

    def test_cjk_in_a_function_pr_is_found_by_line_in_a_real_file(self):
        """A longer file with a documented function and one CJK line."""
        text = cfunc("Add", code=3) + f"// {HAN}\n"
        out = check(text, log=EMPTY_LOG)
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", line_of(text, HAN)), out.describe())


if __name__ == "__main__":
    unittest.main()
