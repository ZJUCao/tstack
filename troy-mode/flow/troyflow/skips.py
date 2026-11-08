"""Local failures that are only tests skipped on this platform (F07 design 8.6, D69).

A case of the test plan may run on one platform only. troy-check counts a
skipped test as neither failing (R09) nor passing (R10), so the local
troy-check code fails on it while CI, which runs it, passes. This command reads
troy-check's JSON report and the JUnit files and tells the two apart.
"""

import json
from pathlib import Path

from troycheck.junit import SKIPPED, JUnitCase, ReportError, read_junit, tag_of

from .errors import FlowError

# troy-check's own messages for a skipped test (troycheck/testpolicy.py).
SKIP_MESSAGES = {"R09": "{label} skipped against the mock", "R10": "{label} skipped but must pass"}


def _read_report(path: str) -> list[dict]:
    """Reads troy-check's JSON report and returns its results.

    Raises:
        FlowError: The file cannot be read, is not JSON, or has no results list.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise FlowError(f"cannot read the troy-check report {path}: {exc}") from exc
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list) or not all(isinstance(r, dict) for r in results):
        raise FlowError(f"{path} is not a troy-check JSON report: it has no results list")
    return results


def _read_tests(paths: list[str]) -> list[JUnitCase]:
    """Reads every testcase of the JUnit files.

    Raises:
        FlowError: A file is missing or is not valid XML.
    """
    tests = []
    for path in paths:
        try:
            tests += read_junit(Path(path))
        except ReportError as exc:
            raise FlowError(str(exc)) from exc
    return tests


def _id(test: JUnitCase) -> str:
    """The case ID or bug ID a test's name starts with, else its label."""
    tag = tag_of(test.name)
    return (tag.case or tag.bug if tag else None) or test.label


def run_check_skips(args) -> tuple[dict, int]:
    """Tells whether troy-check's only failures are tests skipped on this platform.

    Args:
        args: Parsed options: report and junit (a list).

    Returns:
        The report and the exit code: 0 when nothing but skipped tests failed,
        1 when anything else failed.

    Raises:
        FlowError: The report or a JUnit file cannot be read.
    """
    results = _read_report(args.report)
    skipped = [t for t in _read_tests(args.junit) if t.outcome == SKIPPED]
    explains = {(rule, text.format(label=t.label)): t
                for t in skipped for rule, text in SKIP_MESSAGES.items()}
    failed, problems, used = [], [], {}
    for result in results:
        if result.get("result") != "fail":
            continue
        rule = str(result.get("rule"))
        failed.append(rule)
        details = result.get("details") or []
        if rule not in SKIP_MESSAGES or not details:
            problems.append({"rule": rule, "message": result.get("message")})
            continue
        for detail in details:
            message = detail.get("message") if isinstance(detail, dict) else None
            test = explains.get((rule, message))
            if test is None:
                problems.append({"rule": rule, "message": message})
            else:
                used[test.label] = test
    report = {"command": "check-skips", "ok": not problems, "notes": [], "problems": problems,
              "failed": failed, "ci_only": sorted({_id(t) for t in used.values()}),
              "skipped": [t.label for t in skipped]}
    if report["ok"] and report["ci_only"]:
        report["notes"].append("Only tests skipped on this platform failed; CI checks "
                               f"{', '.join(report['ci_only'])} (D69).")
    return report, 0 if report["ok"] else 1
