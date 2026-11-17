"""Old against new: the pass rules of design 7.2 and their exact chances.

A case runs 5 times with each version. When the first 5 do not settle it, it
runs 5 more with each, and the 10 decide.
"""

from collections.abc import Iterable
from math import comb

FIRST = 5
SECOND = 10


def not_worse(base: int, head: int, runs: int) -> str:
    """The rule for a case the PR does not name.

    Args:
        base: Runs the base passed.
        head: Runs the head passed.
        runs: Runs per version so far, 5 or 10.

    Returns:
        "pass", "more" (run 5 more with each version), or "fail".
    """
    if runs <= FIRST:
        return "pass" if head >= base - 1 else "more"
    return "fail" if head <= base - 3 else "pass"


def target(base: int, head: int, runs: int) -> str:
    """The rule for a case the PR fixes (a target).

    Args:
        base: Runs the base passed.
        head: Runs the head passed.
        runs: Runs per version so far, 5 or 10.

    Returns:
        "pass", "more", or "fail".
    """
    if runs <= FIRST:
        if head >= 4 and head > base:
            return "pass"
        if head == 3 or (head >= 4 and head <= base):
            return "more"
        return "fail"
    return "pass" if head >= 8 and head > base else "fail"


def decide(kind: str, base: int, head: int, runs: int) -> str:
    """Applies the rule of kind, "target" or "not-worse"."""
    return (target if kind == "target" else not_worse)(base, head, runs)


def counts(runs: Iterable[dict]) -> tuple[int, int]:
    """Counts the runs that pass and the runs that count.

    A void run does not count (design 7.1). A run that hit its cap or its time
    limit counts as failed (11.5).

    Returns:
        (passed, counted).
    """
    passed = counted = 0
    for run in runs:
        if run.get("status") == "void":
            continue
        counted += 1
        if run.get("status") in ("ok", None) and run.get("passed") is True:
            passed += 1
    return passed, counted


def _pmf(p: float) -> list[float]:
    """The chance of 0 to 5 passes in 5 runs that each pass with chance p."""
    return [comb(FIRST, k) * p ** k * (1 - p) ** (FIRST - k) for k in range(FIRST + 1)]


def _chance(rule, p_base: float, p_head: float, want: str) -> float:
    """The exact chance that rule ends in want, with the second round when it says "more"."""
    base, head = _pmf(p_base), _pmf(p_head)
    total = 0.0
    for b in range(FIRST + 1):
        for h in range(FIRST + 1):
            first = rule(b, h, FIRST)
            chance = base[b] * head[h]
            if first == "more":
                total += chance * sum(base[b2] * head[h2]
                                      for b2 in range(FIRST + 1) for h2 in range(FIRST + 1)
                                      if rule(b + b2, h + h2, SECOND) == want)
            elif first == want:
                total += chance
    return total


def case_fails_chance(p_base: float, p_head: float) -> float:
    """The chance that a case the PR does not name fails, for runs that pass with these chances."""
    return _chance(not_worse, p_base, p_head, "fail")


def target_passes_chance(p_base: float, p_head: float) -> float:
    """The chance that a target passes, for runs that pass with these chances."""
    return _chance(target, p_base, p_head, "pass")


def result_word(kind: str, outcome: str) -> str:
    """The word of the PR section's Result column (design 9.3)."""
    if kind == "target":
        return "fixed" if outcome == "pass" else "not fixed"
    return "not worse" if outcome == "pass" else "worse"
