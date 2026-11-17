"""Budget group (F16 design 10.2, 14.1): the estimate, the $60 line, and the stop.

The estimate is the median cost of each case's recorded runs times the runs
to make, plus the judge passes; up to $60 the exam starts without asking;
it starts no new run once it has spent 1.5 times the estimate. The per-run
cap, the pause at a usage limit, and resume run end to end in
test_exam_cli.py (MainExamTests, ResumeTests, BudgetLineTests, BudgetStopTests).

Planted bugs of design 14.2 caught here:

- "the estimate counting the role's cost but not the judge's":
  EstimateTests.test_judge_passes_are_counted and test_the_designs_one_developer_case.
- "the budget guard ignoring reused runs": EstimateTests.test_reused_runs_cost_nothing,
  test_reuse_keeps_an_exam_under_the_line, and NewRunsTests.
"""

import unittest

from exam_helpers import new_dir
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


if __name__ == "__main__":
    unittest.main()
