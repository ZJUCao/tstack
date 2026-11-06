"""Tests for the order and exit codes of ``code`` results with R04 to R07."""

import unittest

from builders import lines, pr_body
from prefetch import PrefetchedCase
from shape_builders import func, klass, std_base
from shape_runs import IMPL, run_py

ORDER = ["R04", "R05", "R06", "R07", "R09", "R10", "R11"]
CLEAN = {"src/a.py": klass("C", func("m", indent=4))}


def rule_order(outcome):
    """Returns the rule IDs of a report in report order."""
    return [r["rule"] for r in outcome.report["results"] if r["rule"] in ORDER]


class OrderTests(PrefetchedCase):
    """Covers where R04 to R07 sit in the report."""

    def test_results_come_in_rule_order_with_a_language(self):
        """R04, R05, R06, R07, R09, R10, R11, each exactly once."""
        out = run_py(CLEAN)
        self.assertEqual(rule_order(out), ORDER, out.describe())

    def test_results_come_in_rule_order_without_a_language(self):
        """Skipped rules keep their place."""
        out = run_py(CLEAN, name=None)
        self.assertEqual(rule_order(out), ORDER, out.describe())

    def test_results_come_in_rule_order_when_rules_fail(self):
        """A failing R06 and R04 do not change the order."""
        bad = {"src/a.py": func("long", code=60) + lines(500, "x = 1")}
        out = run_py(bad)
        self.assertEqual(rule_order(out), ORDER, out.describe())

    def test_each_new_rule_has_message_and_details(self):
        """R04 to R07 entries carry a string message and a details list."""
        out = run_py(CLEAN)
        for rule in ORDER[:4]:
            with self.subTest(rule=rule):
                entry = out.rule(rule)
                self.assertIsInstance(entry["message"], str)
                self.assertIsInstance(entry["details"], list)


class StatusTests(PrefetchedCase):
    """Covers results and exit codes of whole runs."""

    def test_clean_python_pr_passes_every_new_rule(self):
        """A short documented function passes R04, R05, R06, and R07 skips."""
        out = run_py(CLEAN)
        for rule in ("R04", "R05", "R06"):
            with self.subTest(rule=rule):
                self.assert_rule(out, rule, "pass")
        self.assert_rule(out, "R07", "skip")
        self.assert_clean(out)

    def test_clean_pr_with_a_module_map_passes_r07(self):
        """With a map and a lawful import R07 passes too."""
        base = std_base()
        out = run_py({"ui/main.py": "from store.api import get\n"}, base)
        self.assert_rule(out, "R07", "pass")
        self.assert_clean(out)

    def test_without_a_language_only_r06_runs(self):
        """R04, R05, and R07 skip; R06 passes; the run is clean."""
        out = run_py(CLEAN, std_base(), name=None)
        for rule in ("R04", "R05", "R07"):
            with self.subTest(rule=rule):
                self.assert_rule(out, rule, "skip")
        self.assert_rule(out, "R06", "pass")
        self.assert_clean(out)

    def test_cpp_language_skips_the_python_rules(self):
        """In part two, name = cpp skips R04, R05, and R07; R06 runs."""
        out = run_py({"src/a.cpp": lines(501, "int x;")}, std_base(), name="cpp")
        for rule in ("R04", "R05", "R07"):
            with self.subTest(rule=rule):
                self.assert_rule(out, rule, "skip")
        self.assert_rule(out, "R06", "fail")
        self.assert_exit(out, 1)

    def test_a_failing_rule_makes_ok_false_and_exit_1(self):
        """One failing rule among passing ones gives exit code 1."""
        out = run_py({"src/a.py": func("long", code=60)})
        self.assert_rule(out, "R04", "fail")
        self.assert_rule(out, "R05", "pass")
        self.assert_rule(out, "R06", "pass")
        self.assert_exit(out, 1)
        self.assertFalse(out.report["ok"], out.describe())

    def test_a_warning_does_not_fail_the_run(self):
        """R06 warn with a reason still exits with 0."""
        out = run_py({"src/a.py": lines(501, "x = 1")}, body=pr_body("Split later."))
        self.assert_rule(out, "R06", "warn")
        self.assert_exit(out, 0)
        self.assertTrue(out.report["ok"], out.describe())

    def test_rules_fail_independently(self):
        """A missing docstring fails R05 only, not R04 or R06."""
        out = run_py({"src/a.py": func("f", doc=None)})
        self.assert_rule(out, "R04", "pass")
        self.assert_rule(out, "R05", "fail")
        self.assert_rule(out, "R06", "pass")

    def test_title_that_does_not_parse_still_runs_the_shape_rules(self):
        """The shape rules do not depend on the PR kind."""
        out = run_py({"src/a.py": func("long", code=60)}, title="whatever")
        self.assert_rule(out, "R04", "fail")


if __name__ == "__main__":
    unittest.main()
