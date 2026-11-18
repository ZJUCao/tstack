"""``wait-checks`` (F07 design 3.1, 8.6 "Waiting for the checks", 14.1; D204, tstack issue #68).

In the pilot (ZJUCao/recipe-menu#47) a PR merged right after a push:
``gh pr checks --watch`` said that no checks were reported, because GitHub
had not registered the workflow yet, and the merge chained after it with
``;`` ran anyway. ``wait-checks --pr <n> --sha <sha>`` waits until every
check of that head has registered and finished, and reports ``passed``,
``failed``, ``pending``, ``other-head``, or ``closed`` with its exit code
(the #68 interface note). The fake gh serves ``gh pr view <n> --json
headRefOid,state,statusCheckRollup`` from a list of answers, one per poll,
the last one repeated. Every case runs once, side by side, on one clone,
with ``--interval 0`` or ``0.1`` and small ``--settle`` and ``--timeout``.

Planted bugs of design 14.2 for D204 caught here:

- "no check counted as a pass": ``TimeoutTests.test_no_check_ever_is_pending`` and
  ``AppearTests.test_no_check_then_pending_then_passed``.
- "a pending check counted as finished": ``TimeoutTests.test_running_check_is_pending``,
  ``FailureTests.test_each_unfinished_status_waits``, and
  ``RerunTests.test_run_not_started_is_pending``.
- "the head not compared": ``HeadTests.test_other_head_until_the_timeout`` and
  ``test_other_head_then_the_pushed_head``.
- "an older run of a check counted": ``RerunTests.test_newer_success_counts`` and
  ``test_newer_failure_counts``.
- "no settling": ``SettleTests.test_late_pending_workflow_is_waited_for``,
  ``test_late_passed_workflow_is_read_twice``, and ``test_settle_longer_than_the_timeout``.
- "``SKIPPED`` counted as a failure": ``FailureTests.test_skipped_and_neutral_pass``.
- "a commit status ignored": every test of ``StatusTests``, most plainly
  ``test_failed_status_beside_a_passed_run_fails``.
- "a failure reported before every check has finished":
  ``FailureTests.test_failure_waits_for_every_check``.
- "the timeout ignored": ``TimeoutTests.test_timeout_ends_the_wait`` and the other
  ``pending`` tests, which need the run to end on its own.
- "one failing gh call ending the wait": ``GhFailureTests.test_one_failing_call_is_retried``
  and ``test_failures_not_in_a_row_go_on``.
"""

import hashlib
import subprocess
import time
import unittest
from dataclasses import dataclass
from typing import Optional

from flow_helpers import (LOGIN, PROJECT, Fakes, FlowCase, Outcome, Project, base_step,
                          failing_call, new_dir, parallel, run_engine, same_path)

PR = 7
SHA = hashlib.sha1(b"the pushed head").hexdigest()
OTHER = hashlib.sha1(b"the head before the push").hexdigest()
SHA256 = hashlib.sha256(b"the pushed head").hexdigest()
VIEW_ARGS = ["pr", "view", str(PR), "--json", "headRefOid,state,statusCheckRollup"]
WORKFLOW = "troy-mode checks"
RULES_WORKFLOW = "project rules"
T0 = "2026-11-12T10:00:00Z"
T1 = "2026-11-12T10:05:00Z"
STATUS_URL = "https://example.com/1"
FAST = ("--interval", "0", "--settle", "0", "--timeout", "20")
SHORT = ("--interval", "0.1", "--settle", "0", "--timeout", "1")
RUN_LIMIT = 60
CHECK_KEYS = ("name", "workflow", "state", "url")
FAILING = ("FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE")
UNFINISHED = ("IN_PROGRESS", "QUEUED", "WAITING", "PENDING", "REQUESTED")
MISSING = object()


def run_url(run_id: int, job: int = 1) -> str:
    """A check run's ``detailsUrl`` in GitHub Actions."""
    return f"https://github.com/{LOGIN}/{PROJECT}/actions/runs/{run_id}/job/{job}"


def check_run(name: str, conclusion: str = "SUCCESS", status: str = "COMPLETED",
              workflow: str = WORKFLOW, started=T0, run_id: int = 101, job: int = 1) -> dict:
    """One ``CheckRun`` entry of ``statusCheckRollup``.

    Args:
        name: The check's (job's) name.
        conclusion: The conclusion once completed; "" while it is not.
        status: ``COMPLETED``, ``IN_PROGRESS``, ``QUEUED``, and so on.
        workflow: The ``workflowName``.
        started: The ``startedAt`` text, None for null, or ``MISSING`` to leave it out.
        run_id: The Actions run ID in ``detailsUrl``.
        job: The job ID in ``detailsUrl``.

    Returns:
        The entry.
    """
    done = status == "COMPLETED"
    entry = {"__typename": "CheckRun", "name": name, "workflowName": workflow, "status": status,
             "conclusion": conclusion if done else "", "detailsUrl": run_url(run_id, job)}
    if started is not MISSING:
        entry["startedAt"] = started
    if done:
        entry["completedAt"] = T1
    return entry


def status(context: str, state: str, url: str = STATUS_URL) -> dict:
    """One ``StatusContext`` entry (a commit status) of ``statusCheckRollup``."""
    return {"__typename": "StatusContext", "context": context, "state": state, "targetUrl": url}


def view(*checks: dict, head: str = SHA, state: str = "OPEN", rollup: bool = True) -> dict:
    """One answer of ``gh pr view <n> --json headRefOid,state,statusCheckRollup``.

    Args:
        *checks: The rollup's entries.
        head: The ``headRefOid``.
        state: ``OPEN``, ``MERGED``, or ``CLOSED``.
        rollup: False to leave ``statusCheckRollup`` out, as right after a push.

    Returns:
        The answer.
    """
    answer = {"headRefOid": head, "state": state}
    if rollup:
        answer["statusCheckRollup"] = list(checks)
    return answer


def counted(name: str, state: str, url: str, workflow: str = WORKFLOW) -> dict:
    """One entry the report's ``checks`` should hold."""
    return {"name": name, "workflow": workflow, "state": state, "url": url}


PASSED = view(check_run("troy-check"))
RUNNING = check_run("unit-tests", status="IN_PROGRESS", run_id=102)
PASSED_TWO = view(check_run("troy-check"), check_run("rules", workflow=RULES_WORKFLOW, run_id=201))


@dataclass(frozen=True)
class Case:
    """One ``wait-checks`` run.

    Attributes:
        answers: The checks views the fake gh serves, in order, the last repeated.
        options: The timing options.
        pr: The ``--pr`` value, or None to leave it out.
        sha: The ``--sha`` value, or None to leave it out.
        json: Whether to pass ``--json``.
        plain: Whether to run in a folder that is no git repository.
    """

    answers: tuple
    options: tuple = FAST
    pr: Optional[str] = str(PR)
    sha: Optional[str] = SHA
    json: bool = True
    plain: bool = False


@dataclass
class Run:
    """A finished case.

    Attributes:
        out: The engine's outcome.
        fakes: The fakes it ran with, holding the gh calls.
        seconds: How long the run took, startup included.
        root: The folder given as ``--repo``.
    """

    out: Outcome
    fakes: Fakes
    seconds: float
    root: object


def bad(**kwargs) -> Case:
    """A case with options the engine must refuse before any gh call."""
    return Case((PASSED,), **kwargs)


CASES = {
    # No check yet, then a pass.
    "appear": Case((view(rollup=False), view(), view(RUNNING),
                    view(check_run("unit-tests", run_id=102)))),
    # Settling.
    "late pending": Case((PASSED, view(check_run("troy-check"), check_run(
        "rules", status="IN_PROGRESS", workflow=RULES_WORKFLOW, run_id=201)), PASSED_TWO,
        PASSED_TWO)),
    "late passed": Case((PASSED, PASSED_TWO)),
    "never settles": Case((PASSED,), ("--interval", "0.1", "--settle", "5", "--timeout", "1")),
    "settle time": Case((PASSED,), ("--interval", "0", "--settle", "1", "--timeout", "20")),
    # Failures.
    "failure": Case((view(check_run("troy-check", "FAILURE", run_id=555, job=9), RUNNING),
                     view(check_run("troy-check", "FAILURE", run_id=555, job=9),
                          check_run("unit-tests", run_id=102)))),
    "runs": Case((view(check_run("lint", "FAILURE", run_id=300, job=1),
                       check_run("unit-tests", "FAILURE", run_id=120, job=2),
                       check_run("build", "TIMED_OUT", run_id=300, job=3),
                       check_run("docs", run_id=999, job=4),
                       status("ci/other", "FAILURE")),)),
    "skipped neutral": Case((view(check_run("troy-check"), check_run("unit-tests", "SKIPPED"),
                                  check_run("rules", "NEUTRAL", workflow=RULES_WORKFLOW)),)),
    # Reruns of a workflow for the same head.
    "rerun success": Case((view(check_run("unit-tests", "SUCCESS", started=T1, run_id=402),
                                check_run("unit-tests", "FAILURE", started=T0, run_id=401)),)),
    "rerun failure": Case((view(check_run("unit-tests", "FAILURE", started=T1, run_id=402),
                                check_run("unit-tests", "SUCCESS", started=T0, run_id=401)),)),
    "rerun queued": Case((view(check_run("unit-tests", status="QUEUED", started=MISSING,
                                         run_id=402),
                               check_run("unit-tests", started=T0, run_id=401)),), SHORT),
    "rerun queued null": Case((view(check_run("unit-tests", status="QUEUED", started=None,
                                              run_id=402),
                                    check_run("unit-tests", started=T0, run_id=401)),), SHORT),
    "rerun queued zero time": Case((view(check_run("unit-tests", status="QUEUED",
                                                   started="0001-01-01T00:00:00Z", run_id=402),
                                         check_run("unit-tests", started=T0, run_id=401)),),
                                   SHORT),
    "tie success last": Case((view(check_run("unit-tests", "FAILURE", run_id=401),
                                   check_run("unit-tests", "SUCCESS", run_id=402)),)),
    "tie failure last": Case((view(check_run("unit-tests", "SUCCESS", run_id=401),
                                   check_run("unit-tests", "FAILURE", run_id=402)),)),
    "two workflows": Case((view(check_run("unit-tests", run_id=401),
                                check_run("unit-tests", "FAILURE", workflow=RULES_WORKFLOW,
                                          run_id=402)),)),
    # Commit statuses.
    "status success": Case((view(status("ci/other", "SUCCESS")),)),
    "status pending": Case((view(check_run("troy-check"), status("ci/other", "PENDING")),),
                           SHORT),
    "status expected": Case((view(check_run("troy-check"), status("ci/other", "EXPECTED")),),
                            SHORT),
    "status failure": Case((view(status("ci/other", "FAILURE")),)),
    "status error": Case((view(status("ci/other", "ERROR")),)),
    "status beside run": Case((view(check_run("troy-check"), status("ci/other", "FAILURE")),)),
    # The head.
    "other head": Case((view(check_run("troy-check"), head=OTHER),), SHORT),
    "other head first": Case((view(check_run("troy-check"), head=OTHER), PASSED)),
    "upper sha": Case((PASSED,), sha=SHA.upper()),
    "sha256": Case((view(check_run("troy-check"), head=SHA256),), sha=SHA256),
    "merged": Case((view(check_run("troy-check"), state="MERGED"),)),
    "closed": Case((view(check_run("troy-check"), state="CLOSED"),)),
    # The timeout.
    "no check": Case((view(),), SHORT),
    "running": Case((view(check_run("troy-check"), RUNNING),), SHORT),
    "timeout 0 running": Case((view(RUNNING),), ("--interval", "0", "--settle", "0",
                                                  "--timeout", "0")),
    "timeout 0 failed": Case((view(check_run("unit-tests", "FAILURE", run_id=102)),),
                             ("--interval", "0", "--settle", "0", "--timeout", "0")),
    # gh failing.
    "gh fails once": Case((failing_call(), PASSED)),
    "gh fails": Case((failing_call(),)),
    "gh fails twice twice": Case((failing_call(), failing_call(), view(RUNNING), failing_call(),
                                  failing_call(), PASSED)),
    # The text report.
    "text ok": Case((PASSED,), json=False),
    "text stopped": Case((view(check_run("troy-check", "FAILURE", run_id=555)),), json=False),
    # Options the engine refuses.
    "pr 0": bad(pr="0"),
    "pr x": bad(pr="x"),
    "pr negative": bad(pr="-1"),
    "no pr": bad(pr=None),
    "short sha": bad(sha=SHA[:39]),
    "long sha": bad(sha=SHA + "a"),
    "non-hex sha": bad(sha=SHA[:39] + "g"),
    "no sha": bad(sha=None),
    "negative timeout": bad(options=("--interval", "0", "--settle", "0", "--timeout", "-1")),
    "interval abc": bad(options=("--interval", "abc", "--settle", "0", "--timeout", "1")),
    "negative settle": bad(options=("--interval", "0", "--settle", "-0.5", "--timeout", "1")),
    "plain folder": Case((PASSED,), plain=True),
}
for _status in UNFINISHED:
    CASES[f"unfinished {_status}"] = Case((
        view(check_run("troy-check", "FAILURE", run_id=555),
             check_run("unit-tests", status=_status, run_id=102)),
        view(check_run("troy-check", "FAILURE", run_id=555), check_run("unit-tests", run_id=102))))
for _conclusion in FAILING:
    CASES[f"conclusion {_conclusion}"] = Case((view(check_run("troy-check"), check_run(
        "unit-tests", _conclusion, run_id=777)),))
REFUSED = ("pr 0", "pr x", "pr negative", "no pr", "short sha", "long sha", "non-hex sha",
           "no sha", "negative timeout", "interval abc", "negative settle", "plain folder")
GH_FAILING = ("gh fails once", "gh fails", "gh fails twice twice")

_RUNS: dict = {}


def start(project: Project, case: Case) -> Run:
    """Runs ``wait-checks`` for one case with its own fakes.

    Args:
        project: The shared clone, never changed.
        case: The case.

    Returns:
        The finished run; a run still going after ``RUN_LIMIT`` seconds gets exit code -1.
    """
    fakes = Fakes(check_views={PR: list(case.answers)})
    root = new_dir("plain") if case.plain else project.root
    args = ["wait-checks"]
    if case.pr is not None:
        args += ["--pr", case.pr]
    if case.sha is not None:
        args += ["--sha", case.sha]
    args += [*case.options, "--repo", root]
    if case.json:
        args.append("--json")
    began = time.monotonic()
    try:
        out = run_engine(args, root if case.plain else project.tmp, fakes, timeout=RUN_LIMIT)
    except subprocess.TimeoutExpired:
        out = Outcome(-1, "", f"still running after {RUN_LIMIT} seconds", None)
    return Run(out, fakes, time.monotonic() - began, root)


def runs() -> dict:
    """Builds one clone and runs every case on it, side by side, once."""
    if _RUNS:
        return _RUNS
    project = Project([base_step()])
    names = list(CASES)
    results = parallel(lambda name: start(project, CASES[name]), names)
    _RUNS.update(zip(names, results))
    return _RUNS


class WaitCase(FlowCase):
    """Assertions shared by the ``wait-checks`` tests."""

    def run_of(self, name: str) -> Run:
        """The finished run of one case."""
        return runs()[name]

    def report(self, name: str, result: str, sha: str = SHA) -> dict:
        """Asserts the exit code, ``result``, ``pr``, ``sha``, and the problems, and returns
        the report.

        ``passed`` exits 0 with no problem; every other result exits 1 with exactly one
        problem, a string.

        Args:
            name: The case.
            result: The expected ``result``.
            sha: The expected ``sha``, in lower case.

        Returns:
            The report.
        """
        run = self.run_of(name)
        code = 0 if result == "passed" else 1
        report = self.report_of(run.out, code, "wait-checks")
        self.assertEqual(report.get("result"), result, run.out.describe())
        self.assertEqual(report.get("pr"), PR, run.out.describe())
        self.assertEqual(report.get("sha"), sha, run.out.describe())
        if code == 0:
            self.assertEqual(report["problems"], [], run.out.describe())
        else:
            self.assertEqual(len(report["problems"]), 1, run.out.describe())
            self.assertIsInstance(report["problems"][0], str, run.out.describe())
        return report

    def problem(self, report: dict) -> str:
        """The one problem of a report that stopped."""
        return report["problems"][0]

    def calls(self, name: str) -> list:
        """The argument lists of the case's gh calls."""
        return self.run_of(name).fakes.gh_argvs()

    def assert_checks(self, report: dict, *expected: dict) -> None:
        """Asserts the counted checks, in any order, by their four keys."""
        checks = report.get("checks")
        self.assertIsInstance(checks, list, report)
        got = sorted(({key: c.get(key) for key in CHECK_KEYS} for c in checks),
                     key=lambda c: (str(c["workflow"]), str(c["name"])))
        want = sorted(expected, key=lambda c: (c["workflow"], c["name"]))
        self.assertEqual(got, want, report)

    def assert_failed(self, report: dict, names, run_ids) -> None:
        """Asserts ``failed`` (any order) and ``runs`` (sorted, unique integers)."""
        self.assertIsInstance(report.get("failed"), list, report)
        self.assertEqual(sorted(report["failed"]), sorted(names), report)
        self.assertEqual(report.get("runs"), list(run_ids), report)


class AppearTests(WaitCase):
    """No check right after the push, then a running one, then a pass (design 8.6)."""

    def test_no_check_then_pending_then_passed(self):
        """Planted bug "no check counted as a pass": a missing rollup and an empty one, then a
        running check, then a pass: exit 0 after at least five polls (the pass read twice),
        with the one check, the pushed head, and a call for every poll."""
        report = self.report("appear", "passed")
        self.assertGreaterEqual(report.get("polls"), 5, report)
        self.assertEqual(report.get("polls"), len(self.calls("appear")), report)
        self.assertEqual(report.get("head"), SHA, report)
        self.assert_checks(report, counted("unit-tests", "passed", run_url(102)))
        self.assert_failed(report, [], [])

    def test_only_the_read_only_view_is_called(self):
        """Every gh call is exactly ``pr view 7 --json headRefOid,state,statusCheckRollup``,
        in the repository: no merge and no other call."""
        run = self.run_of("appear")
        calls = run.fakes.gh_calls()
        self.assertGreaterEqual(len(calls), 5, run.out.describe())
        for call in calls:
            with self.subTest(call=call):
                self.assertEqual(call["argv"], VIEW_ARGS)
                self.assertTrue(same_path(call["cwd"], run.root), call)
        self.assertEqual(run.fakes.mamba_calls(), [])


class SettleTests(WaitCase):
    """``passed`` needs all-passed on two polls, ``--settle`` apart, with the same checks."""

    def test_late_pending_workflow_is_waited_for(self):
        """Planted bug "no settling": one passed check, then it and a new running one, then
        both passed twice: passed only at the end, with both checks."""
        report = self.report("late pending", "passed")
        self.assertGreaterEqual(report.get("polls"), 4, report)
        self.assert_checks(report, counted("troy-check", "passed", run_url(101)),
                           counted("rules", "passed", run_url(201), RULES_WORKFLOW))

    def test_late_passed_workflow_is_read_twice(self):
        """One passed check, then it and a new passed one: the new set of checks must be
        read twice too, so at least three polls, with both checks."""
        report = self.report("late passed", "passed")
        self.assertGreaterEqual(report.get("polls"), 3, report)
        self.assert_checks(report, counted("troy-check", "passed", run_url(101)),
                           counted("rules", "passed", run_url(201), RULES_WORKFLOW))

    def test_settle_longer_than_the_timeout(self):
        """Every check passed on every poll but ``--settle 5`` outlasts ``--timeout 1``:
        ``pending``, and the problem says the checks have not ``settled``."""
        report = self.report("never settles", "pending")
        self.assertIn("settled", self.problem(report))
        self.assertLess(self.run_of("never settles").seconds, 30)

    def test_settle_seconds_are_waited(self):
        """``--settle 1``: passed, after at least two polls and at least one second."""
        report = self.report("settle time", "passed")
        self.assertGreaterEqual(report.get("polls"), 2, report)
        self.assertGreaterEqual(self.run_of("settle time").seconds, 1.0)


class FailureTests(WaitCase):
    """A failure is reported once every check has finished, with its run IDs."""

    def test_failure_waits_for_every_check(self):
        """Planted bug "a failure reported before every check has finished": a failed check
        beside a running one, then both finished: ``failed`` on the second poll, naming the
        failed check, with run 555 from its URL."""
        report = self.report("failure", "failed")
        self.assertEqual(report.get("polls"), 2, report)
        self.assertEqual(len(self.calls("failure")), 2)
        self.assert_failed(report, ["troy-check"], [555])
        self.assertIn("troy-check", self.problem(report))
        self.assert_checks(report, counted("troy-check", "failed", run_url(555, 9)),
                           counted("unit-tests", "passed", run_url(102)))

    def test_each_unfinished_status_waits(self):
        """Planted bug "a pending check counted as finished": beside a failed check, a check
        ``IN_PROGRESS``, ``QUEUED``, ``WAITING``, ``PENDING``, or ``REQUESTED`` is waited for:
        ``failed`` only on the second poll."""
        for state in UNFINISHED:
            with self.subTest(status=state):
                report = self.report(f"unfinished {state}", "failed")
                self.assertEqual(report.get("polls"), 2, report)
                self.assert_failed(report, ["troy-check"], [555])

    def test_runs_are_sorted_and_unique(self):
        """Three failed check runs in runs 300, 120, and 300, a passed one in run 999, and a
        failed status: ``failed`` names all four failures, ``runs`` is ``[120, 300]``."""
        report = self.report("runs", "failed")
        self.assertEqual(report.get("polls"), 1, report)
        self.assert_failed(report, ["build", "ci/other", "lint", "unit-tests"], [120, 300])
        for name in ("build", "ci/other", "lint", "unit-tests"):
            with self.subTest(check=name):
                self.assertIn(name, self.problem(report))

    def test_each_failing_conclusion_fails(self):
        """``FAILURE``, ``CANCELLED``, ``TIMED_OUT``, ``ACTION_REQUIRED``, ``STARTUP_FAILURE``,
        and ``STALE`` beside a passed check: ``failed`` at once, naming that check."""
        for conclusion in FAILING:
            with self.subTest(conclusion=conclusion):
                report = self.report(f"conclusion {conclusion}", "failed")
                self.assertEqual(report.get("polls"), 1, report)
                self.assert_failed(report, ["unit-tests"], [777])
                self.assertIn("unit-tests", self.problem(report))
                self.assert_checks(report, counted("troy-check", "passed", run_url(101)),
                                   counted("unit-tests", "failed", run_url(777)))

    def test_skipped_and_neutral_pass(self):
        """Planted bug "``SKIPPED`` counted as a failure": ``SUCCESS``, ``SKIPPED``, and
        ``NEUTRAL`` all pass."""
        report = self.report("skipped neutral", "passed")
        self.assert_failed(report, [], [])
        self.assert_checks(report, counted("troy-check", "passed", run_url(101)),
                           counted("unit-tests", "passed", run_url(101)),
                           counted("rules", "passed", run_url(101), RULES_WORKFLOW))


class RerunTests(WaitCase):
    """Only the newest run of a check (same workflow and name) counts."""

    def test_newer_success_counts(self):
        """Planted bug "an older run of a check counted": a newer ``SUCCESS`` (listed first)
        beside an older ``FAILURE`` passes, and only the newer run is in ``checks``."""
        report = self.report("rerun success", "passed")
        self.assert_checks(report, counted("unit-tests", "passed", run_url(402)))
        self.assert_failed(report, [], [])

    def test_newer_failure_counts(self):
        """A newer ``FAILURE`` (listed first) beside an older ``SUCCESS`` fails, with the newer
        run's ID only."""
        report = self.report("rerun failure", "failed")
        self.assert_failed(report, ["unit-tests"], [402])
        self.assert_checks(report, counted("unit-tests", "failed", run_url(402)))

    def test_run_not_started_is_pending(self):
        """A newer run that has not started (``startedAt`` missing, null, or gh's zero time
        ``0001-01-01T00:00:00Z``, listed first) beside an older ``SUCCESS``: ``pending`` at the
        timeout, naming the check, with the newer run in ``checks``."""
        for name in ("rerun queued", "rerun queued null", "rerun queued zero time"):
            with self.subTest(case=name):
                report = self.report(name, "pending")
                self.assertIn("unit-tests", self.problem(report))
                self.assertNotIn("No check has reported", self.problem(report))
                self.assert_checks(report, counted("unit-tests", "pending", run_url(402)))

    def test_tie_goes_to_the_later_entry(self):
        """Two runs with the same ``startedAt``: the later entry in the list counts."""
        report = self.report("tie success last", "passed")
        self.assert_checks(report, counted("unit-tests", "passed", run_url(402)))
        report = self.report("tie failure last", "failed")
        self.assert_failed(report, ["unit-tests"], [402])

    def test_same_name_in_another_workflow_counts(self):
        """A check named ``unit-tests`` in another workflow is no rerun: its failure counts."""
        report = self.report("two workflows", "failed")
        self.assert_failed(report, ["unit-tests"], [402])
        self.assert_checks(report, counted("unit-tests", "passed", run_url(401)),
                           counted("unit-tests", "failed", run_url(402), RULES_WORKFLOW))


class StatusTests(WaitCase):
    """Planted bug "a commit status ignored": statuses count, with ``workflow`` ""."""

    def test_success_passes(self):
        """A ``SUCCESS`` status alone passes and is the one counted check."""
        report = self.report("status success", "passed")
        self.assert_checks(report, counted("ci/other", "passed", STATUS_URL, ""))

    def test_pending_and_expected_wait(self):
        """``PENDING`` or ``EXPECTED`` beside a passed check run: ``pending``, naming the
        status."""
        for name in ("status pending", "status expected"):
            with self.subTest(case=name):
                report = self.report(name, "pending")
                self.assertIn("ci/other", self.problem(report))
                self.assert_checks(report, counted("troy-check", "passed", run_url(101)),
                                   counted("ci/other", "pending", STATUS_URL, ""))

    def test_failure_and_error_fail(self):
        """``FAILURE`` and ``ERROR`` fail, with no run ID from a URL outside Actions."""
        for name in ("status failure", "status error"):
            with self.subTest(case=name):
                report = self.report(name, "failed")
                self.assert_failed(report, ["ci/other"], [])
                self.assertIn("ci/other", self.problem(report))
                self.assert_checks(report, counted("ci/other", "failed", STATUS_URL, ""))

    def test_failed_status_beside_a_passed_run_fails(self):
        """A failed status beside a passed check run fails the wait."""
        report = self.report("status beside run", "failed")
        self.assert_failed(report, ["ci/other"], [])


class HeadTests(WaitCase):
    """The PR's head against ``--sha``, and a PR that is no longer open."""

    def test_other_head_until_the_timeout(self):
        """Planted bug "the head not compared": the head is another commit on every poll,
        with a passed check: ``other-head``, exit 1, the problem naming that head."""
        report = self.report("other head", "other-head")
        self.assertEqual(report.get("head"), OTHER, report)
        self.assertIn(OTHER[:7], self.problem(report))
        self.assertLess(self.run_of("other head").seconds, 30)

    def test_other_head_then_the_pushed_head(self):
        """Another head first, then the pushed head with a passed check: passed, and the
        other head's poll counts toward nothing, so at least three polls."""
        report = self.report("other head first", "passed")
        self.assertGreaterEqual(report.get("polls"), 3, report)
        self.assertEqual(report.get("head"), SHA, report)

    def test_upper_case_sha_is_compared_in_lower_case(self):
        """``--sha`` in upper case: passed, and ``sha`` in lower case."""
        report = self.report("upper sha", "passed")
        self.assertEqual(report.get("head"), SHA, report)

    def test_sixty_four_digit_sha(self):
        """A 64-digit commit ID is accepted and compared."""
        report = self.report("sha256", "passed", sha=SHA256)
        self.assertEqual(report.get("head"), SHA256, report)

    def test_merged_and_closed_stop_at_once(self):
        """A ``MERGED`` or ``CLOSED`` PR: ``closed`` after one poll, the problem saying that
        the PR is not open."""
        for name in ("merged", "closed"):
            with self.subTest(case=name):
                report = self.report(name, "closed")
                self.assertEqual(report.get("polls"), 1, report)
                self.assertEqual(len(self.calls(name)), 1)
                self.assertRegex(self.problem(report), r"(?i)not open")


class TimeoutTests(WaitCase):
    """``--timeout`` ends the wait with ``pending``; one poll always runs."""

    def test_no_check_ever_is_pending(self):
        """Planted bug "no check counted as a pass": no check on any poll: ``pending``, "No
        check has reported", and ``checks`` empty."""
        report = self.report("no check", "pending")
        self.assertIn("No check has reported", self.problem(report))
        self.assertEqual(report.get("checks"), [], report)
        self.assertGreaterEqual(report.get("polls"), 1, report)

    def test_running_check_is_pending(self):
        """Planted bug "a pending check counted as finished": a running check beside a passed
        one until the timeout: ``pending``, naming the running check."""
        report = self.report("running", "pending")
        self.assertIn("unit-tests", self.problem(report))
        self.assertNotIn("No check has reported", self.problem(report))
        self.assert_checks(report, counted("troy-check", "passed", run_url(101)),
                           counted("unit-tests", "pending", run_url(102)))

    def test_timeout_ends_the_wait(self):
        """Planted bug "the timeout ignored": with ``--timeout 1`` every ``pending`` and
        ``other-head`` case ends on its own, within 30 seconds, after a call for each poll."""
        for name in ("no check", "running", "rerun queued", "status pending", "other head"):
            with self.subTest(case=name):
                run = self.run_of(name)
                self.assertNotEqual(run.out.code, -1, run.out.describe())
                self.assertLess(run.seconds, 30)
                report = run.out.report or {}
                self.assertEqual(report.get("polls"), len(run.fakes.gh_argvs()), report)

    def test_timeout_zero_still_polls_once(self):
        """``--timeout 0``: one poll; a running check gives ``pending``, a failed one
        ``failed``."""
        report = self.report("timeout 0 running", "pending")
        self.assertEqual(report.get("polls"), 1, report)
        self.assertEqual(len(self.calls("timeout 0 running")), 1)
        self.assertIn("unit-tests", self.problem(report))
        report = self.report("timeout 0 failed", "failed")
        self.assertEqual(report.get("polls"), 1, report)
        self.assert_failed(report, ["unit-tests"], [102])


class GhFailureTests(WaitCase):
    """A failing gh call is noted and tried again; three in a row are an engine error."""

    def test_one_failing_call_is_retried(self):
        """Planted bug "one failing gh call ending the wait": one failing call, then a pass:
        passed, with a note, after at least three calls."""
        report = self.report("gh fails once", "passed")
        self.assertNotEqual(report["notes"], [], report)
        self.assertGreaterEqual(len(self.calls("gh fails once")), 3)

    def test_three_failures_in_a_row_exit_2(self):
        """Every call fails: exit 2 after exactly three calls, with a message on stderr."""
        run = self.run_of("gh fails")
        self.assert_exit(run.out, 2)
        self.assertNotEqual(run.out.stderr.strip(), "", run.out.describe())
        self.assertEqual(len(self.calls("gh fails")), 3)

    def test_failures_not_in_a_row_go_on(self):
        """Two failures, a read, and two more failures are never three in a row: passed."""
        report = self.report("gh fails twice twice", "passed")
        self.assertNotEqual(report["notes"], [], report)
        self.assertGreaterEqual(len(self.calls("gh fails twice twice")), 7)


class OptionTests(WaitCase):
    """Bad options and a folder that is no repository: exit 2 and no gh call."""

    def test_bad_options_exit_2_without_gh(self):
        """``--pr`` 0, x, -1, or missing; ``--sha`` too short, too long, not hex, or missing;
        a negative ``--timeout`` or ``--settle``; ``--interval abc``; a folder outside git."""
        for name in REFUSED:
            with self.subTest(case=name):
                run = self.run_of(name)
                self.assert_exit(run.out, 2)
                self.assertNotEqual(run.out.stderr.strip(), "", run.out.describe())
                self.assertEqual(run.fakes.gh_argvs(), [])


class TextReportTests(WaitCase):
    """Without ``--json``: ``troy-flow wait-checks: ok`` or ``stopped`` and a problem line."""

    def lines(self, name: str, code: int) -> list:
        """Asserts the exit code and returns the text report's lines."""
        run = self.run_of(name)
        self.assert_exit(run.out, code)
        lines = run.out.stdout.splitlines()
        self.assertTrue(lines, run.out.describe())
        return lines

    def test_ok(self):
        """A pass: the first line is ``troy-flow wait-checks: ok`` and no line is a problem."""
        lines = self.lines("text ok", 0)
        self.assertEqual(lines[0], "troy-flow wait-checks: ok")
        self.assertEqual([line for line in lines if line.lower().startswith("problem")], [])

    def test_stopped(self):
        """A failure: ``troy-flow wait-checks: stopped`` and a problem line naming the check."""
        lines = self.lines("text stopped", 1)
        self.assertEqual(lines[0], "troy-flow wait-checks: stopped")
        problems = [line for line in lines[1:] if line.lower().startswith("problem")]
        self.assertTrue(problems, lines)
        self.assertIn("troy-check", "\n".join(lines[1:]))


class CallTests(WaitCase):
    """Across every case: gh is only ever asked for the checks view."""

    def test_every_call_is_the_checks_view(self):
        """No case calls gh with anything but the read-only view, or calls mamba."""
        for name, run in runs().items():
            with self.subTest(case=name):
                for argv in run.fakes.gh_argvs():
                    self.assertEqual(argv, VIEW_ARGS)
                self.assertEqual(run.fakes.mamba_calls(), [])

    def test_polls_count_the_calls(self):
        """Where no gh call fails, ``polls`` is the number of gh calls: one per poll."""
        for name, run in runs().items():
            if name in REFUSED or name in GH_FAILING or not CASES[name].json:
                continue
            with self.subTest(case=name):
                report = run.out.report or {}
                self.assertEqual(report.get("polls"), len(run.fakes.gh_argvs()),
                                 run.out.describe())


if __name__ == "__main__":
    unittest.main()
