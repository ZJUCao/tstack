"""Tests for R05: doc comments and no CJK in comments (F03 design section 6)."""

import unittest

from prefetch import PrefetchedCase
from shape_builders import (
    ALLOWED_TEXT, CJK, edit_line, func, klass, line_of, module,
)
from shape_runs import IMPL, TESTS, has_detail, run_py


def missing_cases():
    """Builds one file per kind of definition that lacks a docstring.

    Returns:
        A mapping of a case name to the file text and the text of the
        line that must be reported.
    """
    method = func("method", doc=None, indent=4)
    dunder = func("__init__", doc=None, indent=4)
    nested = func("outer", extra=func("inner", doc=None, indent=4))
    return {
        "function": (func("f", doc=None), "def f"),
        "async function": (func("f", doc=None, is_async=True), "async def f"),
        "private function": (func("_hidden", doc=None), "def _hidden"),
        "method": (klass("C", method), "def method"),
        "dunder method": (klass("C", dunder), "def __init__"),
        "class": (klass("C", "    x = 1\n", doc=None), "class C"),
        "nested function": (nested, "def inner"),
        "decorated function": (func("f", doc=None, decorators=["deco"]), "def f"),
    }


class MissingDocstringTests(PrefetchedCase):
    """Covers R05 part (a): every touched definition has a docstring."""

    def test_each_missing_docstring_fails_with_path_and_line(self):
        """Functions, methods, classes, and nested ones are all reported."""
        for name, (text, needle) in missing_cases().items():
            with self.subTest(case=name):
                out = run_py({"src/a.py": text})
                self.assert_rule(out, "R05", "fail")
                self.assert_exit(out, 1)
                self.assertTrue(
                    has_detail(out, "R05", "src/a.py", line_of(text, needle)), out.describe()
                )

    def test_documented_definitions_pass(self):
        """Private, nested, dunder, and async definitions with docs pass."""
        inner = func("inner", indent=4)
        body = func("__init__", indent=4) + "\n" + func("_helper", indent=4)
        text = module(klass("C", body), func("outer", extra=inner), func("a", is_async=True))
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_only_the_undocumented_definition_is_reported(self):
        """A documented neighbour is not named in the details."""
        text = module(func("good"), func("bad", doc=None))
        out = run_py({"src/a.py": text})
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, "def bad")))
        self.assertFalse(has_detail(out, "R05", "src/a.py", line_of(text, "def good")))

    def test_docstring_format_is_not_checked(self):
        """Short or oddly styled docstrings pass; ruff checks the format."""
        docs = ["no capital or period", "x", "Summary.\n\nNo sections at all."]
        for doc in docs:
            with self.subTest(doc=doc):
                out = run_py({"src/a.py": func("f", doc=doc)})
                self.assert_rule(out, "R05", "pass")

    def test_single_quoted_docstring_counts(self):
        """Any string that ast reads as the docstring is enough."""
        text = func("f", doc=None, extra="    '''Docs.'''\n")
        self.assert_rule(run_py({"src/a.py": text}), "R05", "pass")

    def test_string_after_a_statement_is_not_a_docstring(self):
        """A string that is not the first statement does not count."""
        text = func("f", doc=None, extra='    x = 1\n    """Late text."""\n')
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, "def f")))

    def test_a_comment_is_not_a_docstring(self):
        """A comment in place of a docstring fails."""
        text = func("f", doc=None, extra="    # Does it.\n")
        self.assert_rule(run_py({"src/a.py": text}), "R05", "fail")

    def test_module_without_definitions_passes(self):
        """A module with no function or class has nothing to document."""
        self.assert_rule(run_py({"src/a.py": "X = 1\nY = X + 1\n"}), "R05", "pass")


class TouchTests(PrefetchedCase):
    """Covers the rule that only touched definitions are checked (Q6)."""

    def test_untouched_function_is_ignored_when_a_sibling_changes(self):
        """Only the function that holds the changed line is checked."""
        base = {"src/a.py": module(func("old", doc=None), func("other", extra="    mark = 1\n"))}
        text = edit_line(base["src/a.py"], "mark = 1", "mark = 2")
        out = run_py({"src/a.py": text}, base)
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_touching_an_undocumented_function_fails(self):
        """Changing a line of an old undocumented function fails it."""
        base = {"src/a.py": module(func("old", doc=None), func("other"))}
        text = edit_line(base["src/a.py"], "v1 = 1", "v1 = 5")
        out = run_py({"src/a.py": text}, base)
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, "def old")))

    def test_adding_the_missing_docstring_passes(self):
        """The PR that adds the docstring fixes the function."""
        base = {"src/a.py": func("old", doc=None)}
        out = run_py({"src/a.py": func("old")}, base)
        self.assert_rule(out, "R05", "pass")

    def test_touching_a_method_touches_its_class(self):
        """A class without a docstring fails when a method inside changes."""
        body = func("m", indent=4)
        base = {"src/a.py": klass("C", body, doc=None)}
        text = edit_line(base["src/a.py"], "v0 = 0", "v0 = 7")
        out = run_py({"src/a.py": text}, base)
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, "class C")))
        self.assertFalse(has_detail(out, "R05", "src/a.py", line_of(text, "def m")))

    def test_untouched_nested_function_is_ignored(self):
        """An undocumented inner function passes when only the outer changes."""
        inner = func("inner", doc=None, indent=4)
        outer = func("outer", extra=inner + "    mark = 1\n")
        text = edit_line(outer, "mark = 1", "mark = 2")
        out = run_py({"src/a.py": text}, {"src/a.py": outer})
        self.assert_rule(out, "R05", "pass")

    def test_touching_a_decorator_touches_the_function(self):
        """Editing a decorator line of an undocumented function fails it."""
        base = {"src/a.py": func("old", doc=None, decorators=["first"])}
        text = edit_line(base["src/a.py"], "@first", "@second")
        out = run_py({"src/a.py": text}, base)
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, "def old")))


class FileSelectionTests(PrefetchedCase):
    """Covers which changed files R05 looks at."""

    BAD = func("f", doc=None, extra=f"    # {CJK['ideograph']}\n")

    def test_tests_class_files_are_checked(self):
        """A test function without a docstring fails."""
        out = run_py({"tests/test_a.py": func("test_x", doc=None)}, title=TESTS)
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "tests/test_a.py"))

    def test_cjk_in_tests_class_files_is_checked(self):
        """A CJK comment in a tests-class file fails."""
        text = func("test_x", extra=f"    # {CJK['ideograph']}\n")
        out = run_py({"tests/test_a.py": text}, title=TESTS)
        self.assert_rule(out, "R05", "fail")

    def test_docs_class_python_file_is_ignored(self):
        """A .py file under docs/ is not checked."""
        out = run_py({"docs/example.py": self.BAD}, title="[docs] Example")
        self.assertIn(out.status("R05"), ("pass", "skip"), out.describe())

    def test_non_python_file_is_ignored(self):
        """A source file that is not .py is not read."""
        out = run_py({"src/tool.txt": self.BAD})
        self.assertIn(out.status("R05"), ("pass", "skip"), out.describe())

    def test_deleted_file_is_not_checked(self):
        """Deleting an undocumented file passes."""
        out = run_py({"src/a.py": None, "src/b.py": "X = 1\n"}, {"src/a.py": self.BAD})
        self.assert_rule(out, "R05", "pass")

    def test_without_a_language_r05_is_skipped(self):
        """No [lang] name means skip."""
        out = run_py({"src/a.py": self.BAD}, name=None)
        self.assert_rule(out, "R05", "skip")
        self.assert_exit(out, 0)

    def test_cpp_language_runs_r05_with_the_cpp_adapter(self):
        """With name = cpp a CJK comment in C++ fails R05 without a Doxygen log."""
        bad = f"// {CJK['ideograph']}\nint x;\n"
        out = run_py({"src/a.cpp": bad}, name="cpp")
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.cpp", 1), out.describe())
        clean = run_py({"src/a.cpp": "// English\nint x;\n"}, name="cpp")
        self.assert_rule(clean, "R05", "skip")


class CjkTests(PrefetchedCase):
    """Covers R05 part (b): no CJK characters in comments and docstrings."""

    def test_every_listed_character_class_fails_in_a_comment(self):
        """Each Unicode range of the design fails on its own comment line."""
        for name, char in CJK.items():
            with self.subTest(range=name):
                text = func("f", extra=f"    # note {char} end\n")
                out = run_py({"src/a.py": text})
                self.assert_rule(out, "R05", "fail")
                self.assertTrue(
                    has_detail(out, "R05", "src/a.py", line_of(text, char)), out.describe()
                )

    def test_trailing_comment_is_checked(self):
        """A comment after code on the same line fails."""
        text = func("f", extra=f"    x = 1  # {CJK['katakana']}\n")
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, CJK["katakana"])))

    def test_module_level_comment_is_checked(self):
        """A comment outside any function fails."""
        text = f"# {CJK['hangul syllable']}\n" + func("f")
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.py", 1))

    def test_one_line_docstring_is_checked(self):
        """A docstring with a CJK character fails on its line."""
        text = func("f", doc=f"Does {CJK['ideograph']}.")
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, CJK["ideograph"])))

    def test_multi_line_docstring_is_checked(self):
        """A CJK character inside a long docstring fails the file."""
        text = func("f", doc=f"Summary.\n\nDetail {CJK['hiragana']} here.\n")
        out = run_py({"src/a.py": text})
        self.assert_rule(out, "R05", "fail")
        self.assertTrue(has_detail(out, "R05", "src/a.py"))

    def test_class_docstring_is_checked(self):
        """A class docstring with CJK text fails."""
        text = klass("C", "    x = 1\n", doc=f"Holds {CJK['ideograph']}.")
        self.assert_rule(run_py({"src/a.py": text}), "R05", "fail")

    def test_module_docstring_is_checked(self):
        """A module docstring is a docstring too."""
        text = f'"""Module {CJK["ideograph"]}."""\n\n' + func("f")
        self.assert_rule(run_py({"src/a.py": text}), "R05", "fail")

    def test_allowed_characters_pass_in_comments_and_docstrings(self):
        """Accented letters, arrows, and symbols are not CJK."""
        for name, text in ALLOWED_TEXT.items():
            with self.subTest(text=name):
                body = func("f", doc=f"Does {text}.", extra=f"    # {text}\n")
                self.assert_rule(run_py({"src/a.py": body}), "R05", "pass")

    def test_string_literals_may_hold_any_text(self):
        """CJK in strings, including look-alike comments, passes."""
        char = CJK["ideograph"]
        extra = (
            f'    a = "{char}"\n    b = "# {char}"\n'
            f'    c = """\n    {char}\n    """\n    d = f"{{a}}{char}"\n'
        )
        out = run_py({"src/a.py": func("f", extra=extra)})
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_cjk_in_an_unchanged_comment_is_ignored(self):
        """Old CJK comments pass when the PR changes another line."""
        old = func("f", extra=f"    # {CJK['ideograph']}\n    mark = 1\n")
        text = edit_line(old, "mark = 1", "mark = 2")
        out = run_py({"src/a.py": text}, {"src/a.py": old})
        self.assert_rule(out, "R05", "pass")
        self.assert_exit(out, 0)

    def test_cjk_in_an_unchanged_docstring_line_is_ignored(self):
        """An old CJK docstring line passes when only other lines change."""
        doc = f"Summary.\n\nOld {CJK['ideograph']} note.\n\nMore."
        old = func("f", doc=doc)
        text = edit_line(old, "More.", "More text.")
        out = run_py({"src/a.py": text}, {"src/a.py": old})
        self.assert_rule(out, "R05", "pass")

    def test_replacing_the_cjk_comment_passes(self):
        """The PR that rewrites a CJK comment in English passes."""
        old = func("f", extra=f"    # {CJK['ideograph']}\n")
        text = edit_line(old, f"# {CJK['ideograph']}", "# English")
        out = run_py({"src/a.py": text}, {"src/a.py": old})
        self.assert_rule(out, "R05", "pass")

    def test_missing_docstring_and_cjk_are_both_reported(self):
        """Two kinds of defect on two lines give two detail lines."""
        char = CJK["ideograph"]
        text = module(func("bad", doc=None), func("note", extra=f"    # {char}\n"))
        out = run_py({"src/a.py": text})
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, "def bad")))
        self.assertTrue(has_detail(out, "R05", "src/a.py", line_of(text, char)))


if __name__ == "__main__":
    unittest.main()
