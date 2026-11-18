"""wait-checks: wait until every CI check of a PR's pushed head has finished (F07 D204).

Right after a push, GitHub may not have registered the workflow yet, and
`gh pr checks --watch` then reports no checks and ends. In the pilot
(ZJUCao/recipe-menu#47) a merge chained after it ran before CI had reported.
wait-checks reads the PR's head and its checks in one read-only gh call, waits
while no check has reported or any check runs, and reports pass or fail.
"""

import re
import time

from . import repo as git
from .errors import FlowError
from .github import gh_object

FIELDS = "headRefOid,state,statusCheckRollup"
SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
PASSED = {"SUCCESS", "NEUTRAL", "SKIPPED"}
STATUS_PASSED = {"SUCCESS"}
STATUS_PENDING = {"PENDING", "EXPECTED"}
GH_FAILURES = 3
# gh gives a run that has not started the zero time, 0001-01-01T00:00:00Z.
NOT_STARTED = "0001-01-01"
_RUN = re.compile(r"/actions/runs/(\d+)")


def _number(text: str) -> int:
    """Parses --pr: a whole number of 1 or more."""
    if not text.isdigit() or int(text) < 1:
        raise FlowError(f"--pr {text!r} is not a PR number")
    return int(text)


def _seconds(value: float | None, default: float) -> float:
    """Returns a time option, already checked by the parser, or its default."""
    return default if value is None else value


def check_of(item: dict) -> dict:
    """Reads one entry of statusCheckRollup: a check run or a commit status.

    Returns:
        name, workflow, state ("pending", "passed", or "failed"), and url.
    """
    if item.get("__typename") == "StatusContext":
        state = str(item.get("state") or "").upper()
        result = ("passed" if state in STATUS_PASSED else
                  "pending" if state in STATUS_PENDING or not state else "failed")
        return {"name": str(item.get("context") or ""), "workflow": "", "state": result,
                "url": item.get("targetUrl") or "", "started": None}
    status = str(item.get("status") or "").upper()
    conclusion = str(item.get("conclusion") or "").upper()
    if status != "COMPLETED":
        result = "pending"
    else:
        result = "passed" if conclusion in PASSED else "failed"
    started = str(item.get("startedAt") or "")
    return {"name": str(item.get("name") or ""), "workflow": str(item.get("workflowName") or ""),
            "state": result, "url": item.get("detailsUrl") or "",
            "started": None if not started or started.startswith(NOT_STARTED) else started}


def newest(items: list) -> list[dict]:
    """Keeps the newest check of each workflow and name: an edit reruns the checks.

    A check that has not started counts as newer than one that has; among
    equals, the later entry wins.
    """
    found: dict[tuple, tuple] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        check = check_of(item)
        key = (check["workflow"], check["name"])
        order = (check["started"] is None, check["started"] or "", index)
        if key not in found or order > found[key][0]:
            found[key] = (order, check)
    return [found[key][1] for key in sorted(found)]


def read_pr(repo, number: int) -> dict:
    """Reads the PR's head, its state, and its checks."""
    return gh_object(repo, "pr", "view", str(number), "--json", FIELDS)


def run_wait_checks(args) -> tuple[dict, int]:
    """Waits for every check of --sha on PR --pr, and reports the result (D204).

    Returns:
        The report and the exit code: 0 when every check passed, 1 when a
        check failed, the head is another commit, the PR is closed, or the
        timeout ended first (`result` says which).

    Raises:
        FlowError: Bad options, no repository, or gh failing three polls in a row.
    """
    number = _number(args.pr)
    sha = args.sha.strip().lower()
    if not SHA.fullmatch(sha):
        raise FlowError(f"--sha {args.sha!r} is not a full commit ID")
    timeout = _seconds(args.timeout, 540.0)
    interval = _seconds(args.interval, 15.0)
    settle = _seconds(args.settle, 30.0)
    repo = git.need_repo(args.repo)
    report = {"command": "wait-checks", "ok": False, "notes": [], "problems": [], "pr": number,
              "sha": sha, "result": "pending", "head": None, "checks": [], "failed": [],
              "runs": [], "polls": 0}
    start = time.monotonic()
    failures, passed_since, seen = 0, None, None
    while True:
        try:
            data = read_pr(repo, number)
            failures = 0
        except FlowError as exc:
            failures += 1
            if failures >= GH_FAILURES:
                raise
            report["notes"].append(f"gh failed, tried again: {exc}")
            data = None
        report["polls"] += 1
        if data is not None:
            outcome = _judge(report, data, sha)
            if outcome in ("closed", "failed"):
                return _finish(report, outcome)
            if outcome == "passed":
                key = tuple((c["workflow"], c["name"], c["state"]) for c in report["checks"])
                now = time.monotonic()
                if key != seen:
                    seen, passed_since = key, now
                elif now - passed_since >= settle:
                    return _finish(report, "passed")
            else:
                seen, passed_since = None, None
        if time.monotonic() - start >= timeout:
            return _finish(report, "other-head" if report["head"] not in (None, sha) else
                           "pending")
        time.sleep(interval)


def _judge(report: dict, data: dict, sha: str) -> str:
    """Reads one poll into the report and says what it shows."""
    report["head"] = str(data.get("headRefOid") or "").lower() or None
    if str(data.get("state") or "OPEN").upper() != "OPEN":
        report["state"] = str(data.get("state"))
        return "closed"
    if report["head"] != sha:
        report["checks"] = []
        return "other-head"
    rollup = data.get("statusCheckRollup")
    checks = newest(rollup if isinstance(rollup, list) else [])
    report["checks"] = [{k: c[k] for k in ("name", "workflow", "state", "url")} for c in checks]
    if not checks or any(c["state"] == "pending" for c in checks):
        return "pending"
    return "failed" if any(c["state"] == "failed" for c in checks) else "passed"


def _finish(report: dict, result: str) -> tuple[dict, int]:
    """Fills in the result, the failed checks, their runs, and the problem."""
    report["result"] = result
    failed = [c for c in report["checks"] if c["state"] == "failed"]
    report["failed"] = [c["name"] for c in failed]
    report["runs"] = sorted({int(m.group(1)) for c in failed
                             for m in [_RUN.search(c["url"])] if m})
    if result == "passed":
        report["ok"] = True
        return report, 0
    sha = report["sha"]
    if result == "failed":
        message = f"Checks failed on {sha}: {', '.join(report['failed'])}."
    elif result == "closed":
        message = f"PR #{report['pr']} is {report.get('state', 'closed').lower()}, not open."
    elif result == "other-head":
        message = f"PR #{report['pr']}'s head is {report['head']}, not {sha}."
    elif not report["checks"]:
        message = f"No check has reported on {sha} yet."
    else:
        running = [c["name"] for c in report["checks"] if c["state"] == "pending"]
        message = (f"Checks still running on {sha}: {', '.join(running)}." if running else
                   f"The checks on {sha} passed, but the time ran out before they had settled.")
    report["problems"] = [message]
    return report, 1
