"""R09 and R10: which tests must fail and which must pass (F03 design 4.2).

Accepted features and fixed bugs come from the merge base's history. Each
PR has one commit whose subject is its title (R01), so "[F04 6/6 accept]"
and "[B12 B/B fix]" subjects on main record them. A rule's test cleanup PR,
"[P01 test-fix] ...", is "any other kind": it has no test plan (F09 design 8).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from .context import PrContext
from .gitio import list_files, read_blob, subjects
from .globs import compile_pattern, matches_any
from .junit import FAILED, PASSED, IdTag, JUnitCase, ReportError, legacy_path, read_junit, tag_of
from .report import FAIL, PASS, SKIP, Detail, Result, outcome

_ACCEPT = re.compile(r"^\[(F\d{2,3}) 6/6 accept\] ")
_FIX = re.compile(r"^\[(B[1-9]\d*) B/B fix\] ")
_PLAN_CASE = re.compile(r"^\|\s*(F\d{2,3}-T\d{2})\s*\|")
MUST_FAIL_KINDS = ("tests", "test")
PLAN_KINDS = ("tests", "impl", "accept", "test-fix")


@dataclass
class RunData:
    """Everything the test rules need from the test run.

    Attributes:
        given: True when at least one --junit path was given.
        tests: Every test read from the reports.
        errors: One message per report that could not be read.
        accepted: Features accepted at the merge base.
        fixed: Bugs fixed at the merge base.
    """

    given: bool
    tests: list[JUnitCase] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    accepted: set[str] = field(default_factory=set)
    fixed: set[str] = field(default_factory=set)


def load_run(ctx: PrContext, junit_paths: list[str]) -> RunData:
    """Reads the JUnit reports and the merge base's history.

    Args:
        ctx: The PR under check.
        junit_paths: Paths given with --junit.

    Returns:
        The test run. Unreadable reports become messages in errors.
    """
    run = RunData(given=bool(junit_paths))
    for path in junit_paths:
        try:
            run.tests += read_junit(Path(path))
        except ReportError as exc:
            run.errors.append(str(exc))
    for subject in subjects(ctx.repo, ctx.base):
        accept, fix = _ACCEPT.match(subject), _FIX.match(subject)
        if accept:
            run.accepted.add(accept.group(1))
        if fix:
            run.fixed.add(fix.group(1))
    return run


def must_fail(tag: IdTag, ctx: PrContext) -> bool:
    """Tells whether a test must fail against the mock in this PR (R09)."""
    title = ctx.title
    if title is None or title.kind not in MUST_FAIL_KINDS:
        return False
    return (title.kind == "tests" and tag.feature == title.id) or \
           (title.kind == "test" and tag.bug == title.id)


def must_pass(tag: IdTag | None, ctx: PrContext, run: RunData) -> bool:
    """Tells whether a test must pass in this PR (R10).

    Untagged legacy tests, tests of accepted features and fixed bugs, and
    the tests of the feature or bug this PR implements must pass.
    """
    if tag is None:
        return True
    if must_fail(tag, ctx):
        return False
    if tag.feature in run.accepted or tag.bug in run.fixed:
        return True
    title = ctx.title
    if title is None:
        return False
    if title.kind in ("impl", "accept") and tag.feature == title.id:
        return True
    return title.kind == "fix" and tag.bug == title.id


def check_r09(ctx: PrContext, run: RunData) -> Result:
    """Checks that every new test fails against the mock (R09).

    Args:
        ctx: The PR under check.
        run: The test run.

    Returns:
        SKIP for PRs that add no new tests or when no report was given.
        FAIL when the reports cannot be read, when no test of the PR's
        feature or bug exists, or when one of them does not fail.
    """
    if ctx.title is None or ctx.title.kind not in MUST_FAIL_KINDS:
        return Result("R09", SKIP, "Not a test PR.")
    if not run.given:
        return Result("R09", SKIP, "No JUnit report given.")
    if run.errors:
        return Result("R09", FAIL, "The test reports cannot be read.",
                      [Detail(None, None, e) for e in run.errors])
    targets = [t for t in run.tests if (tag := tag_of(t.name)) and must_fail(tag, ctx)]
    if not targets:
        return Result("R09", FAIL, f"No test of {ctx.title.id} was found.")
    wrong = [Detail(None, None, f"{t.label} {t.outcome} against the mock")
             for t in targets if t.outcome != FAILED]
    if wrong:
        return Result("R09", FAIL, f"{len(wrong)} of {len(targets)} new tests do not fail.", wrong)
    return Result("R09", PASS, f"All {len(targets)} tests of {ctx.title.id} fail against the mock.")


def _untagged_problem(test: JUnitCase, ctx: PrContext) -> Detail | None:
    """Reports a test without an ID unless it is in a legacy file."""
    path = legacy_path(test)
    if matches_any(path, ctx.config.legacy_tests) or matches_any(path + ".py", ctx.config.legacy_tests):
        return None
    return Detail(None, None, f"{test.label} has no case ID or bug ID at the start of its name")


def _run_fails(ctx: PrContext, run: RunData) -> list[Detail]:
    """Finds unreadable reports, untagged tests, and must-pass tests that did not pass."""
    fails = [Detail(None, None, e) for e in run.errors]
    for test in run.tests:
        tag = tag_of(test.name)
        if tag is None:
            problem = _untagged_problem(test, ctx)
            if problem:
                fails.append(problem)
                continue
        if must_pass(tag, ctx, run) and test.outcome != PASSED:
            fails.append(Detail(None, None, f"{test.label} {test.outcome} but must pass"))
    return fails


def _plan_cases(ctx: PrContext, feature: str) -> tuple[str | None, set[str]]:
    """Finds the feature's test plan at the head and the case IDs in its tables."""
    pattern = compile_pattern(f"docs/features/{feature}-*/test-plan.md")
    for path in list_files(ctx.repo, ctx.head, "docs/features"):
        if pattern.fullmatch(path):
            text = read_blob(ctx.repo, ctx.head, path) or ""
            cases = {m.group(1) for line in text.splitlines() if (m := _PLAN_CASE.match(line))}
            return path, cases
    return None, set()


def _plan_warnings(ctx: PrContext, run: RunData) -> list[Detail]:
    """Compares the tests of the PR's feature with its test plan.

    Only a feature's PR has a test plan: a bug's, a version's, or a rule's
    (P ID) test-fix PR has none.
    """
    title = ctx.title
    if title is None or title.kind not in PLAN_KINDS or not (title.id or "").startswith("F"):
        return []
    path, planned = _plan_cases(ctx, title.id)
    if path is None:
        return []
    tested = {tag.case for t in run.tests if (tag := tag_of(t.name)) and tag.feature == title.id}
    warns = [Detail(path, None, f"{case} has no test") for case in sorted(planned - tested)]
    warns += [Detail(None, None, f"{case} has a test but is not in {path}")
              for case in sorted(tested - planned)]
    return warns


def check_r10(ctx: PrContext, run: RunData) -> Result:
    """Checks test IDs and that every test outside the allowed set passes (R10).

    Args:
        ctx: The PR under check.
        run: The test run.

    Returns:
        SKIP when no report was given. FAIL for unreadable reports, tests
        without an ID, and must-pass tests that did not pass. WARN when the
        tests and the feature's test plan disagree. PASS otherwise.
    """
    if not run.given:
        return Result("R10", SKIP, "No JUnit report given.")
    fails, warns = _run_fails(ctx, run), _plan_warnings(ctx, run)
    result = outcome(fails, warns)
    required = sum(must_pass(tag_of(t.name), ctx, run) for t in run.tests)
    messages = {
        FAIL: f"{len(fails)} problems in {len(run.tests)} tests.",
        PASS: f"{len(run.tests)} tests. All {required} that must pass did.",
    }
    message = messages.get(result, f"{len(run.tests)} tests. The tests and the test plan differ.")
    return Result("R10", result, message, fails + warns)
