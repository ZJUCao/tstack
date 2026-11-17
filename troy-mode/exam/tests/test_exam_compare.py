"""Comparison group (F16 design 7.1, 7.2, 14.1): the pass mark and its chances.

Every branch of section 7.2 at 5 and at 10 runs, checked against a table this
file builds from the design's words; a void run is not counted; and the
exact chances of the table in 7.2, computed from the rule's own code, equal
both the design's rounded figures and this file's own exact computation.

Planted bugs of design 14.2 caught here:

- "the not-worse rule off by one": NotWorseTests (every pair at 5 and at 10)
  and ChanceTests.test_not_worse_chances_are_exact.
- "the target rule passing at a tie": TargetTests.test_ties_never_pass and
  ChanceTests.test_target_chances_are_exact.
"""

import unittest
from math import comb

import exam_helpers  # noqa: F401  (puts troyexam on the import path, as in the other modules)
from troyexam.compare import (case_fails_chance, counts, not_worse, result_word, target,
                              target_passes_chance)


def expected_not_worse(base: int, head: int, runs: int) -> str:
    """Design 7.2, "Not worse", in this file's own words."""
    if runs == 5:
        return "pass" if base - head <= 1 else "more"
    return "fail" if base - head >= 3 else "pass"


def expected_target(base: int, head: int, runs: int) -> str:
    """Design 7.2, "A target", in this file's own words."""
    if runs == 5:
        if head >= 4 and head > base:
            return "pass"
        if head == 3 or (head >= 4 and head <= base):
            return "more"
        return "fail"
    return "pass" if head >= 8 and head > base else "fail"


def exact(rule, want: str, p_base: float, p_head: float) -> float:
    """The chance that a rule ends in want: 5 runs each, then 5 more each on "more"."""
    def pmf(k: int, p: float) -> float:
        """The binomial chance of k passes in 5."""
        return comb(5, k) * p ** k * (1 - p) ** (5 - k)
    total = 0.0
    for b in range(6):
        for h in range(6):
            first = pmf(b, p_base) * pmf(h, p_head)
            outcome = rule(b, h, 5)
            if outcome == "more":
                for b2 in range(6):
                    for h2 in range(6):
                        if rule(b + b2, h + h2, 10) == want:
                            total += first * pmf(b2, p_base) * pmf(h2, p_head)
            elif outcome == want:
                total += first
    return total


class NotWorseTests(unittest.TestCase):
    """The not-worse rule (design 7.2)."""

    def test_every_pair_at_five_runs(self):
        """pass when the head passes at most one run fewer, else 5 more runs."""
        for base in range(6):
            for head in range(6):
                with self.subTest(base=base, head=head):
                    self.assertEqual(not_worse(base, head, 5), expected_not_worse(base, head, 5))

    def test_every_pair_at_ten_runs(self):
        """fail only when the head passes three or more fewer of 10."""
        for base in range(11):
            for head in range(11):
                with self.subTest(base=base, head=head):
                    self.assertEqual(not_worse(base, head, 10), expected_not_worse(base, head, 10))

    def test_the_edges(self):
        """The lines where the outcome changes."""
        self.assertEqual(not_worse(5, 4, 5), "pass")
        self.assertEqual(not_worse(5, 3, 5), "more")
        self.assertEqual(not_worse(2, 5, 5), "pass")
        self.assertEqual(not_worse(10, 8, 10), "pass")
        self.assertEqual(not_worse(10, 7, 10), "fail")
        self.assertEqual(not_worse(4, 2, 10), "pass")
        self.assertEqual(not_worse(4, 1, 10), "fail")


class TargetTests(unittest.TestCase):
    """The target rule (design 7.2)."""

    def test_every_pair_at_five_runs(self):
        """pass at 4 or 5 and more than the base; more at 3, or at a tie or below; else fail."""
        for base in range(6):
            for head in range(6):
                with self.subTest(base=base, head=head):
                    self.assertEqual(target(base, head, 5), expected_target(base, head, 5))

    def test_every_pair_at_ten_runs(self):
        """pass at 8 or more of 10 and more than the base, else fail."""
        for base in range(11):
            for head in range(11):
                with self.subTest(base=base, head=head):
                    self.assertEqual(target(base, head, 10), expected_target(base, head, 10))

    def test_ties_never_pass(self):
        """A head that passes no more than the base is not a fix (design 14.2)."""
        self.assertEqual(target(4, 4, 5), "more")
        self.assertEqual(target(5, 5, 5), "more")
        self.assertEqual(target(5, 4, 5), "more")
        self.assertEqual(target(8, 8, 10), "fail")
        self.assertEqual(target(9, 9, 10), "fail")
        self.assertEqual(target(10, 10, 10), "fail")

    def test_the_edges(self):
        """4 of 5 above the base passes; 2 of 5 fails at once; 8 of 10 above passes."""
        self.assertEqual(target(3, 4, 5), "pass")
        self.assertEqual(target(0, 5, 5), "pass")
        self.assertEqual(target(0, 3, 5), "more")
        self.assertEqual(target(0, 2, 5), "fail")
        self.assertEqual(target(7, 8, 10), "pass")
        self.assertEqual(target(2, 7, 10), "fail")


class CountTests(unittest.TestCase):
    """counts: void runs are not counted; a cap or a time-out counts as failed (7.1, 11.5)."""

    def test_counts(self):
        """2 passed of 5 counted, out of 7 records."""
        runs = [{"status": "ok", "passed": True}, {"status": "ok", "passed": False},
                {"status": "void", "passed": None}, {"status": "cap", "passed": False},
                {"status": "timeout", "passed": None}, {"status": "ok", "passed": True},
                {"status": "void", "passed": None}]
        self.assertEqual(counts(runs), (2, 5))

    def test_no_run(self):
        """(0, 0)."""
        self.assertEqual(counts([]), (0, 0))

    def test_a_cap_never_passes(self):
        """Even a record that says passed: a run that hit its cap failed."""
        self.assertEqual(counts([{"status": "cap", "passed": True},
                                 {"status": "timeout", "passed": True}]), (0, 2))


class ChanceTests(unittest.TestCase):
    """The chances of design 7.2's table, from the rule's own code."""

    def test_not_worse_chances_match_the_design(self):
        """4.5%, 1.6%, 60%, and 27%."""
        self.assertAlmostEqual(case_fails_chance(0.8, 0.8), 0.045, delta=0.0005)
        self.assertAlmostEqual(case_fails_chance(0.9, 0.9), 0.016, delta=0.0005)
        self.assertAlmostEqual(case_fails_chance(0.8, 0.4), 0.60, delta=0.005)
        self.assertAlmostEqual(case_fails_chance(0.8, 0.6), 0.27, delta=0.005)

    def test_target_chances_match_the_design(self):
        """17% and 95%."""
        self.assertAlmostEqual(target_passes_chance(0.5, 0.5), 0.17, delta=0.005)
        self.assertAlmostEqual(target_passes_chance(0.5, 0.9), 0.95, delta=0.006)

    def test_not_worse_chances_are_exact(self):
        """Equal to this file's exact sum over the rule, at four pairs and more."""
        for p_base, p_head in ((0.8, 0.8), (0.9, 0.9), (0.8, 0.4), (0.8, 0.6), (0.7, 0.5),
                               (1.0, 1.0), (0.5, 0.0)):
            with self.subTest(p_base=p_base, p_head=p_head):
                self.assertAlmostEqual(case_fails_chance(p_base, p_head),
                                       exact(expected_not_worse, "fail", p_base, p_head),
                                       places=9)

    def test_target_chances_are_exact(self):
        """Equal to this file's exact sum over the rule."""
        for p_base, p_head in ((0.5, 0.5), (0.5, 0.9), (0.2, 0.8), (0.9, 0.9), (0.0, 1.0)):
            with self.subTest(p_base=p_base, p_head=p_head):
                self.assertAlmostEqual(target_passes_chance(p_base, p_head),
                                       exact(expected_target, "pass", p_base, p_head),
                                       places=9)

    def test_whole_exam_figures(self):
        """Two cases fail a harmless change about 1 time in 10, twelve about 4 in 10 (7.2)."""
        one = case_fails_chance(0.8, 0.8)
        self.assertAlmostEqual(1 - (1 - one) ** 2, 0.09, delta=0.01)
        self.assertAlmostEqual(1 - (1 - one) ** 12, 0.43, delta=0.03)


class ResultWordTests(unittest.TestCase):
    """The Result column of the PR section (design 9.3)."""

    def test_words(self):
        """fixed, not fixed, not worse, worse."""
        self.assertEqual(result_word("target", "pass"), "fixed")
        self.assertEqual(result_word("target", "fail"), "not fixed")
        self.assertEqual(result_word("not-worse", "pass"), "not worse")
        self.assertEqual(result_word("not-worse", "fail"), "worse")


if __name__ == "__main__":
    unittest.main()
