"""The estimate, Troy's $60 line, and the guard while an exam runs (design 10.2, 10.3)."""

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
# Runs of each version in a second round (design 7.2).
MORE = 5


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


def own_cost(costs: Sequence[float], fallback: float) -> float:
    """The median of one version's run costs in this exam; fallback without any (D242)."""
    return statistics.median(costs) if costs else fallback


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
    """The first round's estimate: each run to make at its median, plus each judge pass."""
    return sum(new_runs(p.needed, p.reused) * p.median + p.judge_passes * p.judge for p in plan)


def second_round(base_cost: float, head_cost: float, judge_passes: int,
                 judge: float = JUDGE_COST) -> float:
    """One case's second round: MORE new runs of each version, plus its judge passes (10.3)."""
    return MORE * base_cost + MORE * head_cost + judge_passes * judge


def whole(plan: Sequence[Planned]) -> float:
    """The first round plus every case's second round at the case's median (10.3)."""
    return estimate(plan) + sum(second_round(p.median, p.median, p.judge_passes, p.judge)
                                for p in plan)


def needs_approval(amount: float, approved: float = ASK_ABOVE) -> bool:
    """Tells whether Troy must say yes first: amount above the approved amount, $60 by default."""
    return amount > approved


class Guard:
    """Stops new runs once the exam has spent 1.5 times its estimate.

    The estimate counts the second rounds that the rules have asked for and no
    others (D243): extend() adds one when a rule asks for it.

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

    def extend(self, amount: float) -> None:
        """Adds a second round's estimate to the exam's estimate."""
        self.estimate += amount

    def may_start(self) -> bool:
        """Tells whether a new run may start."""
        return self.spent < STOP_FACTOR * self.estimate
