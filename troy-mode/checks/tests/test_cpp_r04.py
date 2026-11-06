"""Tests for R04 with the C/C++ adapter: function length (F03 design section 6)."""

import unittest

from cpp_builders import (
    CPP_EXTENSIONS, IMPL, TESTS, cclass, cfunc, cmodule, detail_text, run_cpp, stmts,
)
from prefetch import PrefetchedCase
from shape_builders import edit_line
from shape_runs import has_detail

SHORT = cfunc("Short", code=0, extra="  int marker = 1;\n")
LONG = cfunc("Long", code=60)


def r04(text, path="src/a.cpp", **kwargs):
    """Runs the checker on one new file and returns the outcome."""
    return run_cpp({path: text}, **kwargs)


class LimitTests(PrefetchedCase):
    """Covers how body lines are counted and the 50-line limit."""

    def test_exactly_50_body_lines_pass(self):
        """A function with exactly 50 code lines passes."""
        out = r04(cfunc("F", code=50))
        self.assert_rule(out, "R04", "pass")
        self.assert_exit(out, 0)

    def test_51_body_lines_fail_naming_path_function_and_count(self):
        """51 code lines fail, and the detail names the file and function."""
        out = r04(cmodule(SHORT, cfunc("Long", code=51)))
        self.assert_rule(out, "R04", "fail")
        self.assert_exit(out, 1)
        self.assertTrue(has_detail(out, "R04", "src/a.cpp"), out.describe())
        text = detail_text(out, "R04")
        self.assertIn("Long", text)
        self.assertIn("51", text)
        self.assertNotIn("Short", text)

    def test_the_count_in_the_detail_is_the_body_line_count(self):
        """A 53-line body is reported as 53."""
        out = r04(cfunc("Long", code=53))
        self.assertIn("53", detail_text(out, "R04"), out.describe())

    def test_blank_and_comment_only_lines_are_not_counted(self):
        """Blank lines, // lines, and block comments do not count as code."""
        block = "  /*\n   * Long text.\n   */\n  /* one */\n  /** doc */\n  /// doc\n"
        out = r04(cfunc("F", code=50, blank=30, comment=30, extra=block * 5))
        self.assert_rule(out, "R04", "pass")

    def test_trailing_comment_does_not_hide_a_code_line(self):
        """A code line that ends in a comment still counts."""
        out = r04(cfunc("F", code=50, extra="  int tail = 1;  // trailing\n"))
        self.assert_rule(out, "R04", "fail")

    def test_code_after_a_block_comment_on_the_same_line_counts(self):
        """A line that holds /* c */ and then code is a code line."""
        out = r04(cfunc("F", code=50, extra="  /* c */ int tail = 1;\n"))
        self.assert_rule(out, "R04", "fail")

    def test_multi_line_signature_is_not_counted(self):
        """Signature lines are outside the body, so 50 body lines pass."""
        params = "int a,\n           int b,\n           int c,\n           int d"
        self.assert_rule(r04(cfunc("Add", code=50, params=params)), "R04", "pass")
        self.assert_rule(r04(cfunc("Add", code=51, params=params)), "R04", "fail")

    def test_opening_brace_on_its_own_line(self):
        """The brace line is not a body line, whatever the brace style."""
        self.assert_rule(r04(cfunc("F", code=50, allman=True)), "R04", "pass")
        self.assert_rule(r04(cfunc("F", code=51, allman=True)), "R04", "fail")

    def test_initializer_list_braces_do_not_open_the_body(self):
        """The body opens at the brace that matches the closing brace."""
        head = "class Foo {\n public:\n  Foo();\n  int a_;\n  int b_;\n};\n\n"
        for count, expected in ((50, "pass"), (51, "fail")):
            with self.subTest(count=count):
                ctor = f"Foo::Foo()\n    : a_{{1}},\n      b_{{2}} {{\n{stmts(count)}}}\n"
                self.assert_rule(r04(head + ctor), "R04", expected)

    def test_initializer_list_on_the_signature_line(self):
        """An in-class constructor with braces in its initializer list."""
        for count, expected in ((50, "pass"), (51, "fail")):
            with self.subTest(count=count):
                ctor = f"  Foo() : a_{{1}}, b_{{2}} {{\n{stmts(count, 4)}  }}\n"
                text = cclass("Foo", ctor + "  int a_;\n  int b_;\n")
                self.assert_rule(r04(text), "R04", expected)

    def test_one_line_functions_have_no_body_lines(self):
        """A body that opens and closes on one line counts 0 lines."""
        many = "int One() { " + "".join(f"int a{i} = {i}; " for i in range(80)) + "}\n"
        text = many + "int Two() { return 2; }\nint Three() {}\n"
        out = r04(text, limits={"function_lines": 1})
        self.assert_rule(out, "R04", "pass")

    def test_one_body_line_counts_one(self):
        """With the limit at 1, one body line passes and two fail."""
        limits = {"function_lines": 1}
        self.assert_rule(r04(cfunc("F", code=1), limits=limits), "R04", "pass")
        self.assert_rule(r04(cfunc("F", code=2), limits=limits), "R04", "fail")

    def test_braces_in_strings_chars_and_comments_do_not_count(self):
        """Quoted and commented braces neither open nor close the body."""
        tricky = (
            '  const char* a = "}";\n  const char* b = "{";\n  char c = \'}\';\n'
            "  // }\n  /* } */\n  /*\n   * {\n   */\n"
        )
        self.assert_rule(r04(cfunc("F", code=47, extra=tricky)), "R04", "pass")
        self.assert_rule(r04(cfunc("F", code=48, extra=tricky)), "R04", "fail")

    def test_a_brace_in_a_string_near_the_end_does_not_open_the_body(self):
        """A "{" in a string just before the closing brace is not the body's opening."""
        text = ("/// Does it.\nint F() {\n" + stmts(50)
                + '  const char* s = "{";\n  return 0;\n}\n')
        out = r04(text)
        self.assert_rule(out, "R04", "fail")
        self.assertIn("52", detail_text(out, "R04"))

    def test_lambda_lines_count_toward_the_enclosing_function(self):
        """A lambda is not a function of its own, and its lines are the outer's."""
        lam = "  auto g = [](int x) {\n" + stmts(30, 4) + "  };\n"
        out = r04(cfunc("Outer", code=25, extra=lam))
        self.assert_rule(out, "R04", "fail")
        text = detail_text(out, "R04")
        self.assertIn("Outer", text)
        self.assertIn("57", text)
        small = r04(cfunc("Outer", code=10, extra="  auto g = [](int x) {\n" + stmts(10, 4) + "  };\n"))
        self.assert_rule(small, "R04", "pass")

    def test_declarations_without_a_body_are_not_functions(self):
        """Prototypes and a long pure-virtual interface do not count."""
        text = "int Declared(int a);\nclass I {\n public:\n  virtual int G() = 0;\n};\n"
        self.assert_rule(r04(text + cfunc("Fine", code=3)), "R04", "pass")

    def test_every_long_function_is_reported(self):
        """Long functions in two files are all reported, short ones are not."""
        a = cmodule(cfunc("One", code=51), cfunc("Two", code=60), SHORT)
        out = run_cpp({"src/a.cpp": a, "src/b.cpp": cfunc("Three", code=70)})
        text = detail_text(out, "R04")
        for name in ("One", "Two", "Three"):
            self.assertIn(name, text, out.describe())
        self.assertNotIn("Short", text)
        self.assertTrue(has_detail(out, "R04", "src/b.cpp"))

    def test_configured_limit_is_used(self):
        """The limit comes from [limits] function_lines."""
        limits = {"function_lines": 10}
        self.assert_rule(r04(cfunc("F", code=10), limits=limits), "R04", "pass")
        self.assert_rule(r04(cfunc("F", code=11), limits=limits), "R04", "fail")


class NameTests(PrefetchedCase):
    """Covers the function names that lizard reports."""

    def cases(self):
        """Builds one file per kind of function, each with 51 body lines.

        Returns:
            A mapping of a case name to the file text and the expected name.
        """
        body = stmts(51, 4)
        decl = "class Foo {\n public:\n  int Decl();\n};\n\n"
        return {
            "free function": (cfunc("Max", code=51), "Max"),
            "template": (
                "template <typename T>\nT Max(T a, T b) {\n" + stmts(51) + "}\n", "Max"),
            "method inside class": (
                cclass("Foo", f"  int Get() const {{\n{body}  }}\n"), "Foo::Get"),
            "method outside class": (decl + cfunc("Foo::Decl", code=51), "Foo::Decl"),
            "constructor": (
                cclass("Foo", f"  Foo() {{\n{body}  }}\n"), "Foo::Foo"),
            "namespace function": (
                f"namespace ns {{\nint Free() {{\n{stmts(51)}}}\n}}  // namespace ns\n",
                "ns::Free"),
        }

    def test_each_kind_is_named_as_lizard_names_it(self):
        """The detail of a failing function holds lizard's name."""
        for label, (text, name) in self.cases().items():
            with self.subTest(case=label):
                out = r04(text)
                self.assert_rule(out, "R04", "fail")
                self.assertIn(name, detail_text(out, "R04"), out.describe())

    def test_template_line_is_not_part_of_the_range(self):
        """A change to the template line alone does not touch the function."""
        old = "template <typename T>\nT Max(T a, T b) {\n" + stmts(60) + "}\n"
        new = old.replace("template <typename T>", "template <class T>")
        out = run_cpp({"src/a.cpp": new}, {"src/a.cpp": old})
        self.assert_rule(out, "R04", "pass")

    def test_name_line_of_a_template_is_part_of_the_range(self):
        """A change to the line with the function's name touches it."""
        old = "template <typename T>\nT Max(T a, T b) {\n" + stmts(60) + "}\n"
        new = old.replace("T Max(T a, T b)", "T Max(T b, T a)")
        out = run_cpp({"src/a.cpp": new}, {"src/a.cpp": old})
        self.assert_rule(out, "R04", "fail")


class FileSelectionTests(PrefetchedCase):
    """Covers which changed files R04 looks at."""

    def test_every_c_and_cpp_extension_is_checked(self):
        """Each extension of the design is read by the adapter."""
        for ext in CPP_EXTENSIONS:
            with self.subTest(ext=ext):
                out = r04(cfunc("F", code=51, params="void"), path=f"src/a{ext}")
                self.assert_rule(out, "R04", "fail")
                self.assertTrue(has_detail(out, "R04", f"src/a{ext}"), out.describe())

    def test_header_function_is_checked(self):
        """An inline function in a .h file is read."""
        text = cfunc("F", code=51, prefix="inline")
        self.assert_rule(r04(text, path="include/f.h"), "R04", "fail")

    def test_c_file_is_checked(self):
        """A C function in a .c file is read."""
        text = cfunc("f", code=51, params="void", prefix="static")
        self.assert_rule(r04(text, path="src/f.c"), "R04", "fail")

    def test_tests_class_files_are_checked(self):
        """A long function in a *_test.cc file and under tests/ fails."""
        for path in ("src/a_test.cc", "tests/helper.cc"):
            with self.subTest(path=path):
                out = r04(cfunc("TestLong", code=51), path=path, title=TESTS)
                self.assert_rule(out, "R04", "fail")
                self.assertTrue(has_detail(out, "R04", path), out.describe())

    def test_docs_class_cpp_file_is_ignored(self):
        """A .cpp file under docs/ is in the docs class."""
        out = r04(LONG, path="docs/example.cpp", title="[docs] Example")
        self.assertIn(out.status("R04"), ("pass", "skip"), out.describe())

    def test_other_files_are_ignored_by_the_cpp_adapter(self):
        """A .txt file and a .py file are not C/C++ sources."""
        for path in ("src/tool.txt", "src/tool.py", "src/Makefile"):
            with self.subTest(path=path):
                out = r04(LONG, path=path)
                self.assertIn(out.status("R04"), ("pass", "skip"), out.describe())

    def test_deleted_file_is_not_checked(self):
        """Deleting a file with a long function passes."""
        out = run_cpp({"src/a.cpp": None, "src/b.cpp": "int x;\n"}, {"src/a.cpp": LONG})
        self.assert_rule(out, "R04", "pass")

    def test_nothing_to_check_passes(self):
        """A PR that changes no C/C++ file passes."""
        out = run_cpp({"src/data.json": "{}\n"})
        self.assertIn(out.status("R04"), ("pass", "skip"), out.describe())
        self.assert_exit(out, 0)


class TouchTests(PrefetchedCase):
    """Covers the rule that only touched functions are checked."""

    BASE = {"src/a.cpp": cmodule(LONG, SHORT)}

    def change(self, old, new):
        """Runs the checker after editing one line of the base file."""
        text = edit_line(self.BASE["src/a.cpp"], old, new)
        return run_cpp({"src/a.cpp": text}, self.BASE)

    def test_long_function_not_touched_is_ignored(self):
        """A long function that the PR does not touch passes."""
        out = self.change("int marker = 1;", "int marker = 2;")
        self.assert_rule(out, "R04", "pass")
        self.assert_exit(out, 0)

    def test_touching_a_body_line_fails(self):
        """Changing one line inside the long function fails it."""
        out = self.change("int v5 = 5;", "int v5 = 55;")
        self.assert_rule(out, "R04", "fail")
        text = detail_text(out, "R04")
        self.assertIn("Long", text)
        self.assertNotIn("Short", text)

    def test_touching_the_closing_brace_line_fails(self):
        """The range runs to the line of the closing brace."""
        out = self.change("}", "}  // end")
        self.assert_rule(out, "R04", "fail")

    def test_touching_the_name_line_fails(self):
        """Renaming the long function touches it."""
        out = self.change("int Long() {", "int Longer() {")
        self.assert_rule(out, "R04", "fail")

    def test_growing_past_the_limit_fails(self):
        """A function pushed over the limit by the PR fails."""
        out = run_cpp({"src/a.cpp": cfunc("F", code=51)}, {"src/a.cpp": cfunc("F", code=50)})
        self.assert_rule(out, "R04", "fail")

    def test_adding_a_function_next_to_a_long_one_passes(self):
        """New code after an untouched long function does not touch it."""
        out = run_cpp({"src/a.cpp": cmodule(LONG, SHORT, cfunc("Fresh"))}, self.BASE)
        self.assert_rule(out, "R04", "pass")

    def test_touched_long_method_fails_but_untouched_sibling_is_ignored(self):
        """Only the touched method of a class is reported."""
        body = cfunc("Old", code=60, indent=2, doc=None) + cfunc("New", code=2, indent=2, doc=None)
        base = {"src/a.cpp": cclass("Foo", body)}
        text = edit_line(base["src/a.cpp"], "int v1 = 1;", "int v1 = 9;")
        out = run_cpp({"src/a.cpp": text}, base)
        self.assert_rule(out, "R04", "fail")
        self.assertIn("Foo::Old", detail_text(out, "R04"))
        self.assertNotIn("Foo::New", detail_text(out, "R04"))

    def test_touching_a_short_function_in_a_tests_file_ignores_the_long_one(self):
        """The same rule holds for files of the tests class."""
        base = {"src/a_test.cc": cmodule(LONG, SHORT)}
        text = edit_line(base["src/a_test.cc"], "int marker = 1;", "int marker = 2;")
        out = run_cpp({"src/a_test.cc": text}, base, TESTS)
        self.assert_rule(out, "R04", "pass")


class LanguageTests(PrefetchedCase):
    """Covers when the C/C++ adapter is on."""

    def test_cpp_language_runs_r04(self):
        """With name = cpp a long function fails; R04 is no longer skipped."""
        out = r04(LONG)
        self.assert_rule(out, "R04", "fail")
        self.assert_exit(out, 1)

    def test_python_language_does_not_read_cpp_files(self):
        """With name = python a .cpp file is not a source the adapter reads."""
        out = r04(LONG, name="python")
        self.assertIn(out.status("R04"), ("pass", "skip"), out.describe())


if __name__ == "__main__":
    unittest.main()
