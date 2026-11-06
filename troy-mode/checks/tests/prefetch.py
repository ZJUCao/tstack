"""Runs the checker invocations of a whole test class concurrently.

Every checker run costs a process start and a few git calls, so running
them one by one is slow on Windows. A test class that inherits
``PrefetchedCase`` is run once in a *collect* pass before its real run.
In that pass, calls to a ``prefetchable`` function only record their
arguments and return a stub, and all assertions are switched off. After the
pass, every recorded call runs in a thread pool and its result is cached.
The real run then finds each result in the cache.

Test methods must therefore be deterministic and free of side effects other
than calls to ``prefetchable`` functions.
"""

from __future__ import annotations

import functools
import unittest
from typing import Callable, List, Optional, Tuple

import helpers
from outcome import CheckTestCase, Outcome
from parallel import parallel

_CACHE: dict = {}
_PENDING: Optional[List[Tuple]] = None
WORKERS = 16


class _Loose(dict):
    """A dictionary whose missing keys yield another empty one."""

    def __missing__(self, key):
        """Returns an empty loose dictionary for any missing key.

        Args:
            key: The missing key.

        Returns:
            A new empty ``_Loose``.
        """
        return _Loose()


class _StubOutcome(Outcome):
    """An outcome returned during the collect pass, safe to query."""

    def __init__(self) -> None:
        """Creates an empty successful outcome."""
        super().__init__(0, "", "", _Loose())

    def rule(self, rule: str) -> dict:
        """Returns an empty entry for any rule.

        Args:
            rule: Rule ID.

        Returns:
            A loose dictionary.
        """
        return _Loose(result="stub", details=[])

    def details(self, rule: str) -> list:
        """Returns no details."""
        return []

    def paths(self, rule: str) -> list:
        """Returns no paths."""
        return []


def prefetchable(func: Callable) -> Callable:
    """Wraps a function that returns an ``Outcome`` so it can be prefetched.

    Args:
        func: A deterministic function of plain, ``repr``-able arguments.

    Returns:
        A function with the same signature that reads and fills the cache.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Returns the cached outcome, records the call, or runs it."""
        key = (func.__name__, repr(args), repr(sorted(kwargs.items())))
        if key in _CACHE:
            return _CACHE[key]
        if _PENDING is not None:
            _PENDING.append((key, func, args, kwargs))
            return _StubOutcome()
        outcome = func(*args, **kwargs)
        _CACHE[key] = outcome
        return outcome

    return wrapper


run_pr = prefetchable(helpers.run_pr)


def _collect(test_class: type) -> List[Tuple]:
    """Runs every test method with assertions off and records the calls.

    Args:
        test_class: The test case class.

    Returns:
        The recorded calls, without duplicates.
    """
    global _PENDING
    _PENDING = []
    for name in unittest.TestLoader().getTestCaseNames(test_class):
        case = test_class(name)
        for attr in dir(case):
            if attr.startswith("assert"):
                setattr(case, attr, lambda *args, **kwargs: None)
        try:
            getattr(case, name)()
        except Exception:  # noqa: BLE001  (the collect pass ignores all errors)
            pass
        finally:
            case.doCleanups()
    found, _PENDING = _PENDING, None
    return list({item[0]: item for item in found}.values())


def warm(test_class: type) -> None:
    """Collects and runs the checker calls of a test class concurrently.

    Args:
        test_class: The test case class.
    """
    calls = [item for item in _collect(test_class) if item[0] not in _CACHE]

    def run(item):
        """Runs one recorded call."""
        return item[1](*item[2], **item[3])

    for item, outcome in zip(calls, parallel(run, calls, workers=WORKERS)):
        _CACHE[item[0]] = outcome


class PrefetchedCase(CheckTestCase):
    """A test case base class whose checker runs are prefetched together."""

    @classmethod
    def setUpClass(cls) -> None:
        """Warms the cache for every test method of the class."""
        super().setUpClass()
        warm(cls)
