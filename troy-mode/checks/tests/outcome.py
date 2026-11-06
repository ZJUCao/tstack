"""The result of a checker run and a test case base class with assertions."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class Outcome:
    """The result of one checker run.

    Attributes:
        code: Process exit code.
        stdout: Captured standard output.
        stderr: Captured standard error.
        report: Parsed JSON report, or None when absent or unparsable.
    """

    code: int
    stdout: str
    stderr: str
    report: Optional[dict]

    def describe(self) -> str:
        """Returns the run's output for use in assertion messages."""
        return f"exit={self.code}\n--stdout--\n{self.stdout}\n--stderr--\n{self.stderr}"

    def rule(self, rule: str) -> dict:
        """Returns the single results entry for a rule.

        Args:
            rule: Rule ID such as ``R01``.

        Returns:
            The entry dictionary.

        Raises:
            AssertionError: If there is no report or not exactly one entry.
        """
        if not isinstance(self.report, dict):
            raise AssertionError("no JSON report\n" + self.describe())
        found = [r for r in self.report["results"] if r["rule"] == rule]
        if len(found) != 1:
            raise AssertionError(f"{len(found)} results for {rule}\n" + self.describe())
        return found[0]

    def status(self, rule: str) -> str:
        """Returns ``pass``, ``warn``, ``fail`` or ``skip`` for a rule."""
        return self.rule(rule)["result"]

    def details(self, rule: str) -> list:
        """Returns the detail entries of a rule."""
        return list(self.rule(rule).get("details") or [])

    def paths(self, rule: str) -> list:
        """Returns the paths named in a rule's details, in report order."""
        return [d["path"] for d in self.details(rule) if d.get("path")]


class CheckTestCase(unittest.TestCase):
    """Base class with assertions that print the checker's output."""

    def assert_rule(self, outcome: Outcome, rule: str, expected: str) -> None:
        """Asserts a rule's result."""
        self.assertEqual(outcome.status(rule), expected, outcome.describe())

    def assert_exit(self, outcome: Outcome, code: int) -> None:
        """Asserts the process exit code."""
        self.assertEqual(outcome.code, code, outcome.describe())

    def assert_paths(self, outcome: Outcome, rule: str, expected: Iterable[str]) -> None:
        """Asserts the set of paths in a rule's details."""
        self.assertEqual(
            sorted(set(outcome.paths(rule))), sorted(set(expected)), outcome.describe()
        )

    def assert_clean(self, outcome: Outcome) -> None:
        """Asserts that no rule failed and the exit code is 0."""
        self.assertEqual(outcome.code, 0, outcome.describe())
        self.assertTrue(outcome.report["ok"], outcome.describe())
