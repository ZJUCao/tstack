"""Tests for a missing lizard: the C/C++ adapter needs it, the Python one does not."""

import unittest

from cpp_builders import cfunc, run_cpp
from prefetch import PrefetchedCase
from shape_builders import func

CPP = {"src/a.cpp": cfunc("F", code=3)}
PY = {"src/a.py": func("f", code=3)}


class LizardMissingTests(PrefetchedCase):
    """Runs the checker with ``python -S`` so site-packages is not importable."""

    def test_cpp_project_exits_2_and_names_lizard(self):
        """Without lizard a C/C++ project is a configuration error."""
        out = run_cpp(CPP, no_site=True)
        self.assert_exit(out, 2)
        self.assertIn("lizard", out.stderr.lower(), out.describe())

    def test_cpp_project_with_a_long_function_still_exits_2(self):
        """The missing tool is reported before any rule result."""
        out = run_cpp({"src/a.cpp": cfunc("F", code=60)}, no_site=True)
        self.assert_exit(out, 2)
        self.assertIn("lizard", out.stderr.lower(), out.describe())

    def test_cpp_project_with_no_cpp_change_exits_2_too(self):
        """The check is on the project's language, not on the changed files."""
        out = run_cpp({"docs/note.md": "text\n"}, no_site=True, title="[docs] Note")
        self.assert_exit(out, 2)
        self.assertIn("lizard", out.stderr.lower(), out.describe())

    def test_the_same_run_with_lizard_does_not_exit_2(self):
        """Control: with site-packages the same PR runs and passes."""
        out = run_cpp(CPP)
        self.assert_exit(out, 0)
        self.assert_rule(out, "R04", "pass")

    def test_python_project_never_needs_lizard(self):
        """A Python project runs without site-packages, with exit 0 or 1."""
        out = run_cpp(PY, name="python", no_site=True)
        self.assertIn(out.code, (0, 1), out.describe())
        self.assert_rule(out, "R04", "pass")

    def test_python_project_with_a_failing_rule_exits_1_without_lizard(self):
        """A rule failure is exit 1, not the exit 2 of a missing tool."""
        out = run_cpp({"src/a.py": func("f", doc=None)}, name="python", no_site=True)
        self.assert_exit(out, 1)
        self.assert_rule(out, "R05", "fail")


if __name__ == "__main__":
    unittest.main()
