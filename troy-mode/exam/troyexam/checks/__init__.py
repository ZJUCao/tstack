"""The checks by script: the universal checks U1 to U7 and the case checks (design 4.3)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CheckResult:
    """One criterion's grade.

    Attributes:
        passed: True when the criterion holds.
        evidence: One sentence on why.
    """

    passed: bool
    evidence: str


@dataclass
class RunContext:
    """What the checks read of one run, or of one anchor.

    Attributes:
        case: The case.
        project: The project after the run.
        start: The commit the run started from.
        report: The role's report, or None.
        transcript: The role's transcript, or None (an anchor has none).
        hooks_log: The run's hooks.log lines.
        check_run: `troy_flow.py check-run --json` output against the run's snapshot.
        leftovers: Command lines of processes the runner ended after the session.
        agent_file: The role's agent file in the version under test.
        brief_checks: The brief's Checks to run.
        mirror: The start repository's mirror.
        work: A scratch folder for the checks.
        env_run: Runs a shell command in a folder with the project's environment.
    """

    case: object
    project: Path
    start: str
    report: str | None = None
    transcript: object = None
    hooks_log: list = field(default_factory=list)
    check_run: dict | None = None
    leftovers: list = field(default_factory=list)
    agent_file: str = ""
    brief_checks: list = field(default_factory=list)
    mirror: Path | None = None
    work: Path | None = None
    env_run: Callable | None = None


from . import case as _case  # noqa: E402  (the modules import CheckResult from here)
from . import universal as _universal  # noqa: E402

UNIVERSAL = ("U1", "U2", "U3", "U4", "U5", "U6", "U7")
# The universal checks a run must pass; the others are reported as notes (design 4.3).
UNIVERSAL_MUSTS = ("U1", "U2", "U3", "U6", "U7")
# U4 and U5 are notes while the hooks that fix them are pending (tstack#64 and #49); each
# becomes a must in the PR that lands its hook. Troy approved this on 2026-11-18.
UNIVERSAL_NOTES = ("U4", "U5")
_UNIVERSAL_CHECKS = {"U1": _universal.u1_report, "U2": _universal.u2_check_run,
                     "U3": _universal.u3_line_ends, "U4": _universal.u4_stdin_python,
                     "U5": _universal.u5_leftovers, "U6": _universal.u6_rules_read,
                     "U7": _universal.u7_git_changes}
CHECKS: dict[str, Callable] = {
    "pack_steps_pass": _case.pack_steps_pass,
    "ruff_format_blocks": _case.ruff_format_blocks,
    "mock_bodies_only_raise": _case.mock_bodies_only_raise,
    "no_mock_notes_left": _case.no_mock_notes_left,
    "tests_fail_on_mock": _case.tests_fail_on_mock,
    "tests_pass_on_pilot": _case.tests_pass_on_pilot,
    "tests_fail_on_mutants": _case.tests_fail_on_mutants,
    "result_is": _case.result_is,
    "changed_only": _case.changed_only,
}


def universal(ctx: RunContext) -> dict[str, CheckResult]:
    """Runs U1 to U7; every one is a must."""
    return {name: _guarded(check, ctx) for name, check in _UNIVERSAL_CHECKS.items()}


def case_checks(ctx: RunContext) -> dict[str, CheckResult]:
    """Runs the case's check criteria, by criterion ID."""
    return {c.id: _guarded(CHECKS[c.check], ctx, c.args)
            for c in ctx.case.criteria if c.check is not None}


def grade(ctx: RunContext) -> dict[str, CheckResult]:
    """Runs the universal checks and the case's checks by script."""
    return {**universal(ctx), **case_checks(ctx)}


def _guarded(check, ctx, *args) -> CheckResult:
    """Runs one check; a check that crashes fails, with the error as its evidence."""
    try:
        return check(ctx, *args)
    except Exception as exc:  # a broken run must not stop the exam
        return CheckResult(False, f"the check could not run: {type(exc).__name__}: {exc}")
