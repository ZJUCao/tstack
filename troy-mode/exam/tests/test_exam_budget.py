"""Budget group (F16 design 10.2, 10.3, 14.1): the estimate, the $60 line, and the guard.

The estimate is the median cost of each case's recorded runs times the runs
to make, plus the judge passes; up to $60 the exam starts without asking;
it starts no new run once it has spent 1.5 times the estimate. The per-run
cap, the pause at a usage limit, and resume run end to end in
test_exam_cli.py (MainExamTests, ResumeTests, BudgetLineTests, BudgetGuardTests).

The second round of design 10.3 (tstack #92, D241 to D243): MORE runs of each
version, all new, plus one judge pass (second_round); the whole, every case's
first and second round at the case's median (whole); a version's own cost,
the median of its runs or the case's median without any (own_cost); the line
against the approved amount (needs_approval); and the guard extended by each
second round a rule asks for (Guard.extend). The figures are the design's
own, from exams 2026-11-19-8 and 2026-11-19-10. The new names are read from
the module inside each test, so the tests of the names that existed before
still run while the new names are missing. The second round end to end is
in test_exam_second_round.py.

Planted bugs of design 14.2 caught here:

- "the estimate counting the role's cost but not the judge's":
  EstimateTests.test_judge_passes_are_counted and test_the_designs_one_developer_case.
- "the budget guard ignoring reused runs": EstimateTests.test_reused_runs_cost_nothing,
  test_reuse_keeps_an_exam_under_the_line, and NewRunsTests.

Planted bugs of design 10.3 caught here:

- "the second round's estimate leaving out the base's runs when its first 5
  were reused": WholeTests.test_the_designs_exam_8, test_the_designs_exam_10,
  and test_reused_base_runs_are_new_in_the_second_round;
  SecondRoundTests.test_every_run_of_both_versions_is_new.
- "the second round's judge pass left out":
  SecondRoundTests.test_the_judge_pass_is_counted, test_the_designs_figures_by_own_cost,
  and test_the_designs_exam_8_at_the_cases_median; WholeTests.test_the_designs_exam_8.
"""

import unittest

from exam_helpers import new_dir
from troyexam import budget
from troyexam.budget import (ASK_ABOVE, JUDGE_COST, ROLE_MEDIAN, STOP_FACTOR, Guard, Planned,
                             estimate, median_cost, needs_approval, new_runs)
from troyexam.reuse import append_log, read_log


def planned(needed=10, reused=0, judge_passes=1, median=1.0, judge=2.0, case="dv-x",
            role="developer") -> Planned:
    """One case's plan."""
    return Planned(case=case, role=role, needed=needed, reused=reused, judge_passes=judge_passes,
                   median=median, judge=judge)


class ConstantTests(unittest.TestCase):
    """The figures of design 10.2 and 2.2."""

    def test_constants(self):
        """$60, 1.5 times, and a $2 judge pass before any is recorded."""
        self.assertEqual(ASK_ABOVE, 60.0)
        self.assertEqual(STOP_FACTOR, 1.5)
        self.assertEqual(JUDGE_COST, 2.00)

    def test_role_medians(self):
        """Section 2.2's medians, the Code Reviewer's with its helper agent."""
        self.assertEqual(ROLE_MEDIAN, {"developer": 0.28, "test-engineer": 0.39,
                                       "code-reviewer": 2.63, "test-manager": 2.21,
                                       "architect": 2.94, "interface-designer": 3.39})


class MedianTests(unittest.TestCase):
    """median_cost: from the case's recorded runs, or the role's median."""

    def test_median_of_non_void_rows(self):
        """Void runs do not count; an even count takes the middle two."""
        rows = [{"status": "ok", "cost": 1.0}, {"status": "ok", "cost": 3.0},
                {"status": "cap", "cost": 2.0}, {"status": "void", "cost": 100.0}]
        self.assertAlmostEqual(median_cost(rows, "developer"), 2.0)
        rows.append({"status": "ok", "cost": 4.0})
        self.assertAlmostEqual(median_cost(rows, "developer"), 2.5)

    def test_no_rows_gives_the_roles_median(self):
        """Before any run is recorded."""
        self.assertAlmostEqual(median_cost([], "interface-designer"), 3.39)
        self.assertAlmostEqual(median_cost([{"status": "void", "cost": 9.0}], "developer"), 0.28)

    def test_rows_read_from_a_case_log(self):
        """The costs a log holds as text."""
        path = new_dir("blog") / "dv-x.tsv"
        for run, cost, status in (("r1", 0.5, "ok"), ("r2", 1.5, "ok"), ("r3", 0.9, "ok"),
                                  ("r4", 50.0, "void")):
            append_log(path, {"exam": "2026-11-18-1", "run": run, "time": "2026-11-18T09:30:00Z",
                              "side": "base", "case_version": 1, "instructions": "a" * 64,
                              "cli": "2.1.325", "models": "m", "effort": "high",
                              "status": status, "passed": True, "cost": cost, "minutes": 1.0})
        self.assertAlmostEqual(median_cost(read_log(path), "developer"), 0.9)


class NewRunsTests(unittest.TestCase):
    """new_runs: reused runs are not made again (design 8.2, 10.2)."""

    def test_new_runs(self):
        """needed minus reused, never below 0."""
        self.assertEqual(new_runs(10, 0), 10)
        self.assertEqual(new_runs(10, 5), 5)
        self.assertEqual(new_runs(5, 10), 0)
        self.assertEqual(new_runs(10, 10), 0)


class EstimateTests(unittest.TestCase):
    """estimate (design 10.2)."""

    def test_judge_passes_are_counted(self):
        """10 runs at $1 plus one $2 judge pass is $12."""
        self.assertAlmostEqual(estimate([planned()]), 12.0)
        self.assertAlmostEqual(estimate([planned(judge_passes=2)]), 14.0)

    def test_reused_runs_cost_nothing(self):
        """5 of 10 reused: $5 plus $2."""
        self.assertAlmostEqual(estimate([planned(reused=5)]), 7.0)
        self.assertAlmostEqual(estimate([planned(needed=5, reused=5)]), 2.0)

    def test_cases_add_up(self):
        """Two cases of different roles."""
        plan = [planned(needed=10, reused=5, median=0.28, judge=2.0),
                planned(case="if-x", role="interface-designer", needed=10, reused=0,
                        median=3.39, judge=2.5)]
        self.assertAlmostEqual(estimate(plan), 5 * 0.28 + 2.0 + 10 * 3.39 + 2.5)

    def test_the_designs_one_developer_case(self):
        """Design 10.1: one Developer case, head only, base reused: about $2 to $3."""
        amount = estimate([planned(needed=10, reused=5, median=ROLE_MEDIAN["developer"],
                                   judge=JUDGE_COST)])
        self.assertAlmostEqual(amount, 5 * 0.28 + 2.0)
        self.assertGreaterEqual(amount, 2.0)
        self.assertLessEqual(amount, 3.5)

    def test_reuse_keeps_an_exam_under_the_line(self):
        """10 runs at $10 with 5 reused is $52, under $60; without reuse it would ask."""
        self.assertAlmostEqual(estimate([planned(reused=5, median=10.0)]), 52.0)
        self.assertFalse(needs_approval(estimate([planned(reused=5, median=10.0)])))
        self.assertTrue(needs_approval(estimate([planned(reused=0, median=10.0)])))


class ApprovalTests(unittest.TestCase):
    """needs_approval: above $60 the session asks Troy."""

    def test_the_line(self):
        """$60 starts without asking; $60.01 asks."""
        self.assertFalse(needs_approval(0.0))
        self.assertFalse(needs_approval(60.0))
        self.assertTrue(needs_approval(60.01))
        self.assertTrue(needs_approval(250.0))


class GuardTests(unittest.TestCase):
    """Guard: no new run once spending reaches 1.5 times the estimate."""

    def test_stop_at_one_and_a_half_times(self):
        """Estimate $10: runs start until $15 is spent."""
        guard = Guard(10.0)
        self.assertEqual(guard.spent, 0)
        self.assertTrue(guard.may_start())
        guard.add(8.0)
        guard.add(6.5)
        self.assertEqual(guard.spent, 14.5)
        self.assertTrue(guard.may_start())
        guard.add(0.5)
        self.assertEqual(guard.spent, 15.0)
        self.assertFalse(guard.may_start())

    def test_one_turn_can_overshoot(self):
        """A run that passes its cap by a turn (probe C) still stops the next one."""
        guard = Guard(4.8)
        guard.add(20.0)
        self.assertFalse(guard.may_start())


# ------------------------------------------------- the second round (10.3)

# Exam 2026-11-19-8 (design 10.3): the base's 5 runs reused, the case's median
# $0.668 (5 head runs and a $2 judge pass make $5.34), the base's runs $0.61 and
# the head's $0.77 by their own median, $5.17 spent in the first round.
EXAM_8_MEDIAN = 0.668
# Exam 2026-11-19-10: the case's median $0.716 ($5.58), own costs $0.75 and
# $1.26, $10.65 spent in the first round.
EXAM_10_MEDIAN = 0.716


class MoreTests(unittest.TestCase):
    """MORE: the runs of each version in a second round (design 7.2)."""

    def test_five_more_runs_of_each_version(self):
        """5 more runs with each version."""
        self.assertEqual(budget.MORE, 5)


class SecondRoundTests(unittest.TestCase):
    """second_round: 5 new runs of each version at its own cost, plus one judge pass (10.3)."""

    def test_every_run_of_both_versions_is_new(self):
        """$1 a run: 5 base runs, 5 head runs, and a $2 judge pass make $12."""
        self.assertAlmostEqual(budget.second_round(1.0, 1.0, 1), 12.0)

    def test_each_version_at_its_own_cost(self):
        """The base's cost counts 5 times and the head's 5 times, each on its own."""
        self.assertAlmostEqual(budget.second_round(2.0, 0.0, 0), 10.0)
        self.assertAlmostEqual(budget.second_round(0.0, 2.0, 0), 10.0)
        self.assertAlmostEqual(budget.second_round(3.0, 1.0, 0), 20.0)

    def test_the_judge_pass_is_counted(self):
        """One pass at JUDGE_COST by default; another price or count when given."""
        self.assertAlmostEqual(budget.second_round(0.0, 0.0, 1), JUDGE_COST)
        self.assertAlmostEqual(budget.second_round(1.0, 1.0, 1)
                               - budget.second_round(1.0, 1.0, 0), 2.0)
        self.assertAlmostEqual(budget.second_round(1.0, 1.0, 2), 14.0)
        self.assertAlmostEqual(budget.second_round(1.0, 1.0, 1, judge=3.0), 13.0)
        self.assertAlmostEqual(budget.second_round(1.0, 1.0, 1, 2.5), 12.5)

    def test_the_designs_figures_by_own_cost(self):
        """D242 B: $8.90 in exam -8 ($0.61 and $0.77), $12.05 in exam -10 ($0.75 and $1.26)."""
        self.assertAlmostEqual(budget.second_round(0.61, 0.77, 1), 8.90, places=6)
        self.assertAlmostEqual(budget.second_round(0.75, 1.26, 1), 12.05, places=6)

    def test_the_designs_exam_8_at_the_cases_median(self):
        """D242 A: both versions at the case's median, $8.68 in -8 and $9.16 in -10."""
        self.assertAlmostEqual(budget.second_round(EXAM_8_MEDIAN, EXAM_8_MEDIAN, 1), 8.68,
                               places=6)
        self.assertAlmostEqual(budget.second_round(EXAM_10_MEDIAN, EXAM_10_MEDIAN, 1), 9.16,
                               places=6)

    def test_the_designs_option_c(self):
        """D242 C, never below the case's median, is the caller's choice: $9.19 in -8."""
        self.assertAlmostEqual(budget.second_round(max(0.61, EXAM_8_MEDIAN),
                                                   max(0.77, EXAM_8_MEDIAN), 1), 9.19, places=6)


class WholeTests(unittest.TestCase):
    """whole: the first round plus every case's second round at the case's median (10.2, 10.3)."""

    def test_the_designs_exam_8(self):
        """Base reused, $0.668: the first round $5.34, the whole $14.02."""
        plan = [planned(needed=10, reused=5, median=EXAM_8_MEDIAN)]
        self.assertAlmostEqual(estimate(plan), 5.34, places=6)
        self.assertAlmostEqual(budget.whole(plan), 14.02, places=6)

    def test_the_designs_exam_10(self):
        """Base reused, $0.716: the first round $5.58, the whole $14.74."""
        plan = [planned(needed=10, reused=5, median=EXAM_10_MEDIAN)]
        self.assertAlmostEqual(estimate(plan), 5.58, places=6)
        self.assertAlmostEqual(budget.whole(plan), 14.74, places=6)

    def test_reused_base_runs_are_new_in_the_second_round(self):
        """Reuse lowers the first round only: the second round adds $12 either way."""
        reused = [planned(reused=5)]
        measured = [planned(reused=0)]
        self.assertAlmostEqual(budget.whole(reused), 7.0 + 12.0)
        self.assertAlmostEqual(budget.whole(measured), 12.0 + 12.0)
        self.assertAlmostEqual(budget.whole(reused) - estimate(reused),
                               budget.whole(measured) - estimate(measured))

    def test_cases_add_up(self):
        """Two cases, each with its own median, judge price, and judge passes."""
        plan = [planned(needed=10, reused=5, median=0.28, judge=2.0),
                planned(case="if-x", role="interface-designer", needed=10, reused=0,
                        median=3.39, judge=2.5, judge_passes=1),
                planned(case="dv-y", needed=10, reused=0, median=1.0, judge_passes=0)]
        second = (10 * 0.28 + 2.0) + (10 * 3.39 + 2.5) + (10 * 1.0)
        self.assertAlmostEqual(budget.whole(plan), estimate(plan) + second, places=6)

    def test_a_case_with_no_judge_criteria(self):
        """No judge pass in either round: 10 runs at $1, then 10 more."""
        self.assertAlmostEqual(budget.whole([planned(judge_passes=0)]), 20.0)

    def test_an_empty_plan(self):
        """Nothing to run costs nothing."""
        self.assertAlmostEqual(budget.whole([]), 0.0)

    def test_the_whole_is_shown_but_the_line_is_the_first_round(self):
        """D241 A: a first round of $52 starts without asking although its whole is $154."""
        plan = [planned(reused=5, median=10.0)]
        self.assertAlmostEqual(estimate(plan), 52.0)
        self.assertAlmostEqual(budget.whole(plan), 52.0 + 102.0)
        self.assertFalse(needs_approval(estimate(plan)))


class OwnCostTests(unittest.TestCase):
    """own_cost: the median of a version's runs, or the case's median without any (D242 B)."""

    def test_the_median_of_the_costs(self):
        """An odd count takes the middle one; an even count the mean of the middle two."""
        self.assertAlmostEqual(budget.own_cost([0.9, 0.5, 1.5], 9.0), 0.9)
        self.assertAlmostEqual(budget.own_cost([1.0, 4.0, 2.0, 3.0], 9.0), 2.5)
        self.assertAlmostEqual(budget.own_cost([1.26], 0.716), 1.26)

    def test_no_runs_give_the_fallback(self):
        """A version with no run that counts takes the case's median."""
        self.assertAlmostEqual(budget.own_cost([], 0.668), 0.668)
        self.assertAlmostEqual(budget.own_cost((), 2.21), 2.21)

    def test_the_fallback_is_not_a_floor(self):
        """Runs cheaper than the case's median count at their own cost (D242 B, not C)."""
        self.assertAlmostEqual(budget.own_cost([0.61, 0.61, 0.61], 0.668), 0.61)

    def test_a_zero_cost_is_a_cost(self):
        """Runs recorded at $0 count at $0; only an empty list falls back."""
        self.assertAlmostEqual(budget.own_cost([0.0, 0.0, 1.0], 5.0), 0.0)


class ApprovedLineTests(unittest.TestCase):
    """needs_approval(amount, approved): above the approved amount, Troy must say yes (D241 A)."""

    def test_one_argument_is_the_60_line(self):
        """Without an approved amount, the line is $60."""
        self.assertFalse(budget.needs_approval(60.0))
        self.assertTrue(budget.needs_approval(60.01))

    def test_the_approved_amount(self):
        """Above the amount asks; at it or below does not."""
        self.assertTrue(budget.needs_approval(70.5, 60.0))
        self.assertFalse(budget.needs_approval(229.0, 229.0))
        self.assertTrue(budget.needs_approval(229.01, 229.0))
        self.assertFalse(budget.needs_approval(100.0, approved=229.0))
        self.assertTrue(budget.needs_approval(14.07, approved=14.02))

    def test_the_designs_exams_do_not_ask(self):
        """-8: $5.17 spent plus $8.90 is $14.07; -10: $10.65 plus $12.05, $22.70; under $60."""
        self.assertFalse(budget.needs_approval(5.17 + budget.second_round(0.61, 0.77, 1)))
        self.assertFalse(budget.needs_approval(10.65 + budget.second_round(0.75, 1.26, 1)))


class GuardExtendTests(unittest.TestCase):
    """Guard.extend: a second round's estimate joins the guard once a rule asks for it (D243)."""

    def test_extend_adds_to_the_estimate(self):
        """$10 and then $6: no run starts from $24 on, 1.5 times $16."""
        guard = Guard(10.0)
        guard.extend(6.0)
        self.assertAlmostEqual(guard.estimate, 16.0)
        guard.add(23.5)
        self.assertTrue(guard.may_start())
        guard.add(0.5)
        self.assertFalse(guard.may_start())

    def test_extend_keeps_what_is_spent(self):
        """Extending changes the estimate only."""
        guard = Guard(10.0)
        guard.add(7.25)
        guard.extend(4.0)
        self.assertEqual(guard.spent, 7.25)
        self.assertAlmostEqual(guard.estimate, 14.0)

    def test_each_round_asked_for_adds_once(self):
        """Two cases' second rounds, asked for one after the other."""
        guard = Guard(10.0)
        guard.extend(4.0)
        guard.extend(6.0)
        self.assertAlmostEqual(guard.estimate, 20.0)

    def test_the_designs_exam_8(self):
        """Before 1.8 the guard stopped at $8.01; with the round's $8.90 it moves to $21.36."""
        guard = Guard(5.34)
        guard.add(8.02)
        self.assertFalse(guard.may_start())
        guard.extend(budget.second_round(0.61, 0.77, 1))
        self.assertAlmostEqual(guard.estimate, 14.24, places=6)
        self.assertTrue(guard.may_start())
        guard.add(10.71 - 8.02)
        self.assertTrue(guard.may_start())
        guard.add(21.35 - 10.71)
        self.assertTrue(guard.may_start())
        guard.add(0.02)
        self.assertFalse(guard.may_start())

    def test_the_designs_exam_10(self):
        """Before 1.8 the guard stopped the round at $8.37; with $12.05 it is $26.45."""
        guard = Guard(5.58)
        guard.add(10.65)
        self.assertFalse(guard.may_start())
        guard.extend(budget.second_round(0.75, 1.26, 1))
        self.assertAlmostEqual(guard.estimate, 17.63, places=6)
        self.assertTrue(guard.may_start())
        guard.add(18.18 - 10.65)
        self.assertTrue(guard.may_start())
        guard.add(26.46 - 18.18)
        self.assertFalse(guard.may_start())


if __name__ == "__main__":
    unittest.main()
