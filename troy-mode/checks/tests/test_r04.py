"""Tests for R04: function length (F03 design section 6)."""

import unittest

from prefetch import PrefetchedCase
from shape_builders import (
    edit_line, func, klass, line_of, module,
)
from shape_runs import IMPL, TESTS, has_detail, run_py

SHORT = func("short", extra="    marker = 1\n")


def long_doc(count):
    """Builds a docstring of ``count`` extra lines."""
    return "Summary.\n" + "\n".join(f"Detail {i}." for i in range(count))


class LimitTests(PrefetchedCase):
    """Covers how body lines are counted and the 50-line limit."""

    def test_exactly_50_code_lines_pass(self):
        """A function with exactly 50 code lines passes."""
        out = run_py({"src/a.py": func("long", code=50)})
        self.assert_rule(out, "R04", "pass")
        self.assert_exit(out, 0)

    def test_51_code_lines_fail_with_path_and_def_line(self):
        """51 code lines fail, and details name the file and the def line."""
        text = module(SHORT, func("long", code=51))
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R04", "fail")
        self.assert_exit(out, 1)
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "def long")), out.describe())
        self.assertFalse(has_detail(out, "R04", "src/a.py", line_of(text, "def short")))

    def test_blank_comment_and_docstring_lines_are_not_counted(self):
        """Blank, comment-only, and docstring lines do not count as code."""
        text = func("long", code=50, doc=long_doc(20), blank=30, comment=30)
        self.assert_rule(run_py({"src/a.py": text}), "R04", "pass")

    def test_body_lines_hold_comments_between_code(self):
        """Comment-only lines in the middle of the body are not code."""
        extra = "    # first\n\n" + "    # second\n" * 10
        text = func("long", code=50, extra=extra)
        self.assert_rule(run_py({"src/a.py": text}), "R04", "pass")

    def test_trailing_comment_does_not_hide_a_code_line(self):
        """A code line that ends in a comment still counts."""
        extra = "    tail = 1  # trailing\n"
        text = func("long", code=50, extra=extra)
        self.assert_rule(run_py({"src/a.py": text}), "R04", "fail")

    def test_async_function_is_checked(self):
        """An async def over the limit fails."""
        text = func("long", code=51, is_async=True)
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R04", "fail")
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "async def long")))

    def test_method_is_checked(self):
        """A method over the limit fails."""
        text = klass("C", func("method", code=51, indent=4))
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R04", "fail")
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "def method")))

    def test_classes_have_no_limit(self):
        """A class with 200 code lines in short methods passes."""
        methods = "\n".join(func(f"m{i}", code=20, indent=4) for i in range(10))
        text = klass("C", methods)
        self.assert_rule(run_py({"src/a.py": text}), "R04", "pass")

    def test_nested_function_counts_toward_the_enclosing_one(self):
        """An outer function that holds 56 code lines in all fails."""
        inner = func("inner", code=25, indent=4)
        text = func("outer", code=30, extra=inner)
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R04", "fail")
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "def outer")))
        self.assertFalse(has_detail(out, "R04", "src/a.py", line_of(text, "def inner")))

    def test_nested_function_within_the_limit_passes(self):
        """An outer function with about 40 code lines in all passes."""
        text = func("outer", code=20, extra=func("inner", code=19, indent=4))
        self.assert_rule(run_py({"src/a.py": text}), "R04", "pass")

    def test_long_nested_function_fails_with_its_own_line(self):
        """A 60-line inner function is reported with its own def line too."""
        text = func("outer", code=1, extra=func("inner", code=60, indent=4))
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R04", "fail")
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "def outer")))
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "def inner")))

    def test_every_long_function_is_reported(self):
        """Long functions in two files are all reported."""
        a = module(func("one", code=51), func("two", code=60))
        out = run_py({"src/a.py": a, "src/b.py": func("three", code=70)})
        self.assert_rule(out, "R04", "fail")
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(a, "def one")))
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(a, "def two")))
        self.assertTrue(has_detail(out, "R04", "src/b.py"))

    def test_configured_limit_is_used(self):
        """The limit comes from [limits] function_lines."""
        limits = {"function_lines": 10}
        ok = run_py({"src/a.py": func("f", code=10)}, limits=limits)
        bad = run_py({"src/a.py": func("f", code=11)}, limits=limits)
        self.assert_rule(ok, "R04", "pass")
        self.assert_rule(bad, "R04", "fail")

    def test_larger_configured_limit_allows_more_lines(self):
        """Raising function_lines to 80 lets a 70-line function pass."""
        out = run_py({"src/a.py": func("f", code=70)}, limits={"function_lines": 80})
        self.assert_rule(out, "R04", "pass")


class FileSelectionTests(PrefetchedCase):
    """Covers which changed files R04 looks at."""

    def test_tests_class_files_are_checked(self):
        """A long function in a tests-class .py file fails."""
        out = run_py({"tests/test_a.py": func("test_long", code=51)}, title=TESTS)
        self.assert_rule(out, "R04", "fail")
        self.assertTrue(has_detail(out, "R04", "tests/test_a.py"))

    def test_docs_class_python_file_is_ignored(self):
        """A .py file under docs/ is in the docs class and is not checked."""
        out = run_py({"docs/example.py": func("f", code=60)}, title="[docs] Example")
        self.assertIn(out.status("R04"), ("pass", "skip"), out.describe())

    def test_non_python_source_file_is_ignored(self):
        """A source file that is not .py is not read by the Python adapter."""
        out = run_py({"src/tool.txt": func("f", code=60)})
        self.assertIn(out.status("R04"), ("pass", "skip"), out.describe())

    def test_deleted_file_is_not_checked(self):
        """Deleting a file with a long function passes."""
        base = {"src/a.py": func("long", code=60)}
        out = run_py({"src/a.py": None, "src/b.py": "X = 1\n"}, base)
        self.assert_rule(out, "R04", "pass")

    def test_nothing_to_check_passes(self):
        """A PR that changes no Python file passes."""
        out = run_py({"src/data.json": "{}\n"})
        self.assertIn(out.status("R04"), ("pass", "skip"), out.describe())
        self.assert_exit(out, 0)


class TouchTests(PrefetchedCase):
    """Covers the rule that only touched functions are checked (Q6)."""

    LONG = func("long", code=60)
    BASE = {"src/a.py": module(LONG, SHORT)}

    def change(self, old, new, title=IMPL):
        """Runs the checker after editing one line of the base file."""
        text = edit_line(self.BASE["src/a.py"], old, new)
        return run_py({"src/a.py": text}, self.BASE, title)

    def test_long_function_not_touched_is_ignored(self):
        """A long function that the PR does not touch passes (Q6)."""
        out = self.change("marker = 1", "marker = 2")
        self.assert_rule(out, "R04", "pass")
        self.assert_exit(out, 0)

    def test_touching_a_body_line_fails(self):
        """Changing one line inside the long function fails it."""
        out = self.change("v5 = 5", "v5 = 55")
        self.assert_rule(out, "R04", "fail")
        text = self.BASE["src/a.py"]
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "def long")))
        self.assertFalse(has_detail(out, "R04", "src/a.py", line_of(text, "def short")))

    def test_touching_the_last_line_fails(self):
        """Changing the last line of the long function fails it."""
        out = self.change("v59 = 59", "v59 = 0")
        self.assert_rule(out, "R04", "fail")

    def test_touching_the_def_line_fails(self):
        """Renaming the long function touches it."""
        out = self.change("def long():", "def longer():")
        self.assert_rule(out, "R04", "fail")

    def test_touching_a_decorator_line_fails(self):
        """The range starts at the first decorator, so a decorator edit counts."""
        long = func("long", code=60, decorators=["first", "second"])
        base = {"src/a.py": module(long, SHORT)}
        text = edit_line(base["src/a.py"], "@first", "@primary")
        out = run_py({"src/a.py": text}, base)
        self.assert_rule(out, "R04", "fail")
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "def long")))

    def test_adding_a_line_to_a_short_function_that_grows_long_fails(self):
        """A function pushed over the limit by the PR fails."""
        base = {"src/a.py": func("f", code=50)}
        out = run_py({"src/a.py": func("f", code=51)}, base)
        self.assert_rule(out, "R04", "fail")

    def test_adding_a_short_function_next_to_a_long_one_passes(self):
        """New code after an untouched long function does not touch it."""
        text = module(self.LONG, SHORT, func("fresh"))
        out = run_py({"src/a.py": text}, self.BASE)
        self.assert_rule(out, "R04", "pass")

    def test_editing_the_line_after_the_long_function_passes(self):
        """A change just after the long function's last line is outside it."""
        base = {"src/a.py": module(self.LONG, "X = 1\n")}
        out = run_py({"src/a.py": module(self.LONG, "X = 2\n")}, base)
        self.assert_rule(out, "R04", "pass")

    def test_touched_long_method_fails_but_untouched_sibling_is_ignored(self):
        """Only the touched method of a class is reported."""
        body = func("old", code=60, indent=4) + "\n" + func("new", code=2, indent=4)
        base = {"src/a.py": klass("C", body)}
        text = edit_line(base["src/a.py"], "v1 = 1", "v1 = 9")
        out = run_py({"src/a.py": text}, base)
        self.assert_rule(out, "R04", "fail")
        self.assertTrue(has_detail(out, "R04", "src/a.py", line_of(text, "def old")))
        self.assertFalse(has_detail(out, "R04", "src/a.py", line_of(text, "def new")))

    def test_touching_a_test_function_in_a_tests_file(self):
        """The Q6 rule holds for files of the tests class too."""
        long = func("test_long", code=60)
        base = {"tests/test_a.py": module(long, SHORT)}
        text = edit_line(base["tests/test_a.py"], "marker = 1", "marker = 2")
        out = run_py({"tests/test_a.py": text}, base, TESTS)
        self.assert_rule(out, "R04", "pass")


class LanguageTests(PrefetchedCase):
    """Covers when the Python adapter is on."""

    LONG = {"src/a.py": func("long", code=60)}

    def test_without_a_language_r04_is_skipped(self):
        """No [lang] name means skip, even for a long function."""
        out = run_py(self.LONG, name=None)
        self.assert_rule(out, "R04", "skip")
        self.assert_exit(out, 0)

    def test_cpp_language_skips_r04_in_part_two(self):
        """The C/C++ adapter does not exist yet, so R04 is skipped."""
        out = run_py(self.LONG, name="cpp")
        self.assert_rule(out, "R04", "skip")

    def test_python_language_runs_r04(self):
        """With name = python the same file fails."""
        self.assert_rule(run_py(self.LONG), "R04", "fail")


if __name__ == "__main__":
    unittest.main()
