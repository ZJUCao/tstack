"""The estimate, Troy's $60 line, and the guard while an exam runs (design 10.2)."""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

# Median cost of one run of each role in the pilot (design 2.2); the Code
# Reviewer's includes its helper agent.
ROLE_MEDIAN = {"developer": 0.28, "test-engineer": 0.39, "code-reviewer": 2.63,
               "test-manager": 2.21, "architect": 2.94, "interface-designer": 3.39}
# One judge pass, before any is recorded.
JUDGE_COST = 2.00
ASK_ABOVE = 60.0
STOP_FACTOR = 1.5


def median_cost(rows: Sequence[dict], role: str) -> float:
    """The median cost of the recorded runs that are not void; the pilot's median without any."""
    costs = []
    for row in rows:
        if row.get("status") == "void":
            continue
        try:
            costs.append(float(row.get("cost")))
        except (TypeError, ValueError):
            continue
    return statistics.median(costs) if costs else ROLE_MEDIAN[role]


def new_runs(needed: int, reused: int) -> int:
    """The runs to make when some of the needed runs are reused."""
    return max(0, needed - reused)


@dataclass
class Planned:
    """One case's share of an exam.

    Attributes:
        case: The case ID.
        role: The case's role.
        needed: Runs the comparison needs, of both versions.
        reused: Of those, runs reused from the base (design 8.2).
        judge_passes: Judge passes planned for the case.
        median: The median cost of one of its runs.
        judge: The cost of one judge pass.
    """

    case: str
    role: str
    needed: int
    reused: int
    judge_passes: int
    median: float
    judge: float = JUDGE_COST


def estimate(plan: Sequence[Planned]) -> float:
    """The exam's estimate: each run to make at its median, plus each judge pass."""
    return sum(new_runs(p.needed, p.reused) * p.median + p.judge_passes * p.judge for p in plan)


def needs_approval(amount: float) -> bool:
    """Tells whether Troy must say yes before the exam starts: above $60."""
    return amount > ASK_ABOVE


class Guard:
    """Stops new runs once the exam has spent 1.5 times its estimate.

    Attributes:
        estimate: The exam's estimate.
        spent: What its runs and judge passes have cost so far.
    """

    def __init__(self, estimate: float):
        """Starts with nothing spent."""
        self.estimate = estimate
        self.spent = 0.0

    def add(self, cost: float) -> None:
        """Counts one run's or one judge pass's cost."""
        self.spent += cost

    def may_start(self) -> bool:
        """Tells whether a new run may start."""
        return self.spent < STOP_FACTOR * self.estimate
