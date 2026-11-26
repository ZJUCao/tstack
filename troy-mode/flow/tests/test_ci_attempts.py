"""Attempts from CI (tstack issue #73).

The design: F07 design 8.4, 8.5 "Attempts from CI", 8.6 "A failing CI check",
the 14.1 row "Attempts from CI (D261 to D263)", 14.2, and D261 to D263; F08
design 7 step 1, the 11.1 row "Notes and retro", and 11.2; and the #73
interface note, which fixes the gh calls, the report keys, and the fake gh.

In the pilot, CI failed on four pushes in the Interface Designer's files
(ZJUCao/recipe-menu#52 twice and #59 twice) and one attempt comment was
posted, so the retrospective saw one failed attempt. ``status`` now also reads
each open PR's CI runs (``gh run list --branch``), and ``retro`` the runs of
the version's merged PRs (one ``gh run list --created``). A pushed commit
counts at most once, decided by the newest run of each workflow on it, and
only when a check step failed (``troyflow.ci.CHECK_STEPS``). A comment counts
the commit its ``Commit:`` line names or, without the line, the newest pushed
commit when it was posted, if that commit had already failed. A PR's attempts
are the highest comment number plus each failed commit that no comment counts.

The fake gh serves the runs, newest first as gh lists them, and the jobs of
every failed run. Times are minutes after ``OPENED``, when the PR opened.

Planted bugs of F07 design 14.2 (D261 to D263) caught here:

- "each failed run counted instead of each commit": ``OncePerCommitTests``.
- "an older run of a workflow counted beside a newer one":
  ``NewestRunTests.test_newer_pass_clears_an_older_failure`` and
  ``test_newer_run_still_running_clears_an_older_failure``.
- "a cancelled run counted as failed": ``UnfinishedRunTests.test_cancelled_run_counts_nothing``.
- "runs from before the PR opened kept": ``RunWindowTests`` and
  ``RetroCountTests.test_reused_branch_keeps_each_prs_runs``.
- "a checkout failure counted as the author's":
  ``AuthorStepTests.test_checkout_failure_is_not_the_authors``.
- "a ``Commit:`` line ignored": ``CommitLineTests``.
- "a comment without one counting a commit that failed after it was posted":
  ``CommentTimeTests.test_comment_before_the_failure_finished_counts_nothing``.
- "one comment counting two commits": ``CommitLineTests.test_one_comment_counts_one_commit``
  and ``CommentTimeTests.test_comment_counts_only_the_newest_pushed_commit``.
- "the CI count added to the number of comments instead of the highest number":
  ``CountTests.test_count_is_the_highest_number_plus_the_failures``.
- "a failing ``gh run list`` stopping ``status``": ``GhFailureTests``.

Planted bugs of F08 design 11.2 (F07 D261 to D263) caught here:

- "a CI failure that a comment counts counted again in ``retro``":
  ``RetroCountTests.test_failure_a_comment_counts_is_not_added``.
- "a checkout failure grouped as an attempt":
  ``RetroCountTests.test_checkout_failure_is_in_ci_other_only``.
"""

import hashlib
import importlib
import re
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from flow_helpers import (
    F01, F02, LOGIN, PLUGIN_ROOT, PROJECT, Fakes, FlowCase, Project, Step, base_step, bug_step,
    fake_status_runs, issue, option_value, parallel, release_step, stage_step, stages, step,
    subject_commits, version_tests_step,
)
from test_entry_skill import SKILL, section, split_skill

# ------------------------------------------------------------- workflows

CHECKS_WORKFLOW = PLUGIN_ROOT / "troy-mode/checks/workflow.yml"
PACK_JOBS = PLUGIN_ROOT / "troy-mode/lang"
WORKFLOW = "troy-mode checks"        # the name of troy-mode/checks/workflow.yml
CHECK_JOB = "troy-mode checks"       # troy-check's job (F02 section 8)
CODE_JOB = "troy-mode code checks"   # the language pack's job (F03)
CHECKOUT = "Run actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
MICROMAMBA = "Run mamba-org/setup-micromamba@f457c30a868e4760d3a6fcea5f25dc655b8edf39"
FOREIGN_WORKFLOW = "Deploy docs"     # a workflow troy-mode did not write
FOREIGN_JOB = "deploy"
FOREIGN_STEPS = ("Set up job", CHECKOUT, "Tests", "Publish", "Complete job")
PYTHON_CHECKS = ("Lint and format", "Types", "Tests", "Coverage report", "Run troy-check code")
CPP_CHECKS = ("Configure and build", "Format and lint changed files", "Tests", "Coverage report",
              "Doc comments", "Run troy-check code")
_SETUP = ("Set up job", CHECKOUT, "Look for code", MICROMAMBA, "Install from the lock")
_TEARDOWN = ("Post " + MICROMAMBA, "Post " + CHECKOUT, "Complete job")
_CHECK_JOB_STEPS = ("Set up job", CHECKOUT, "Run troy-check", "Post " + CHECKOUT, "Complete job")
JOB_STEPS = {
    "python": {CHECK_JOB: _CHECK_JOB_STEPS, CODE_JOB: _SETUP + PYTHON_CHECKS + _TEARDOWN},
    "cpp": {CHECK_JOB: _CHECK_JOB_STEPS, CODE_JOB: _SETUP + CPP_CHECKS + _TEARDOWN},
}
RUN_FIELDS = {"databaseId", "headBranch", "headSha", "status", "conclusion", "createdAt",
              "updatedAt", "workflowName"}
MERGED_FIELDS = {"number", "title", "url", "mergeCommit", "headRefName", "createdAt", "mergedAt"}
_STEP_NAME = re.compile(r"^\s*- name: (.+?)\s*$")


def step_names(path) -> list:
    """The ``- name:`` lines of a workflow file's steps, in order.

    Args:
        path: The workflow file.

    Returns:
        The step names; steps with only ``uses:`` have none.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    return [match.group(1) for match in map(_STEP_NAME.match, lines) if match]


def pack_check_steps(pack: str) -> list:
    """The named steps after ``Install from the lock`` in a pack's job (D262).

    Args:
        pack: The pack's folder under ``troy-mode/lang``, such as ``python``.

    Returns:
        The step names, in order.
    """
    names = step_names(PACK_JOBS / pack / "workflow-job.yml")
    return names[names.index("Install from the lock") + 1:]


def load_ci():
    """Imports ``troyflow.ci`` with the paths ``troy_flow.py`` sets up.

    Returns:
        The module.

    Raises:
        AssertionError: It cannot be imported (the engine has no ``ci`` module yet).
    """
    flow = PLUGIN_ROOT / "troy-mode/flow"
    for folder in (flow.parent / "init", flow.parent / "hooks", flow.parent / "checks", flow):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        return importlib.import_module("troyflow.ci")
    except ImportError as exc:
        raise AssertionError(f"troyflow.ci cannot be imported: {exc}") from exc


# ------------------------------------------------------------- times and IDs

OPENED = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
DAY = 1440


def when(minutes: float) -> str:
    """A time as gh prints it, minutes after ``OPENED``, such as ``2026-11-10T09:05:00Z``."""
    return (OPENED + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(label: str, first: str = "") -> str:
    """A full commit ID made from a label.

    Args:
        label: Text that makes the ID.
        first: Hexadecimal digits that replace the ID's first digits, to fix
            its prefix or its sort order.

    Returns:
        40 lower-case hexadecimal digits.
    """
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()
    return first + digest[len(first):]


def pr_url(number: int) -> str:
    """A PR's URL."""
    return f"https://github.com/{LOGIN}/{PROJECT}/pull/{number}"


def label(job: str, step_name: str) -> str:
    """A failed step as ``ci_failures`` names it: ``<job> / <step>``."""
    return f"{job} / {step_name}"


LINT = label(CODE_JOB, "Lint and format")
TROY_CHECK = label(CHECK_JOB, "Run troy-check")
CHECKOUT_STEPS = [label(CHECK_JOB, CHECKOUT), label(CODE_JOB, CHECKOUT)]

# --------------------------------------------------------------- run views


def job(name: str, steps: Sequence[str], failed: Optional[str] = None,
        how: str = "failure") -> dict:
    """One job of ``gh run view --json jobs``, as GitHub ends it.

    Args:
        name: The job's name.
        steps: Its step names, in order.
        failed: The step that ended the job, or None for a job that passed.
        how: That step's conclusion: ``failure``, or ``cancelled`` for a
            step that a timeout ended.

    Returns:
        The job: its conclusion is ``failure`` when a step ended it. The
        steps after that one are ``skipped``, except the ``Post`` steps and
        ``Complete job``, which always run.
    """
    entries, after = [], False
    for number, step_name in enumerate(steps, start=1):
        if step_name == failed:
            conclusion, after = how, True
        elif after and not (step_name.startswith("Post ") or step_name == "Complete job"):
            conclusion = "skipped"
        else:
            conclusion = "success"
        entries.append({"name": step_name, "status": "completed", "conclusion": conclusion,
                        "number": number})
    return {"name": name, "status": "completed",
            "conclusion": "failure" if failed else "success", "steps": entries}


def troy_view(failures: dict, pack: str = "python", how: str = "failure") -> dict:
    """The jobs of a run of troy-mode's workflow, troy-check's job and the pack's.

    Args:
        failures: Job name mapped to the step that failed in it; the other job passed.
        pack: ``python`` or ``cpp``.
        how: The failed steps' conclusion.

    Returns:
        The answer of ``gh run view <id> --json jobs``.
    """
    return {"jobs": [job(name, steps, failures.get(name), how)
                     for name, steps in JOB_STEPS[pack].items()]}


def code_failure(step_name: str, pack: str = "python", how: str = "failure") -> dict:
    """troy-mode's run with one step of the pack's job failed."""
    return troy_view({CODE_JOB: step_name}, pack, how)


def check_failure() -> dict:
    """troy-mode's run with ``Run troy-check`` failed in troy-check's job."""
    return troy_view({CHECK_JOB: "Run troy-check"})


def checkout_failure() -> dict:
    """troy-mode's run with the checkout failed in both jobs (the pilot's #87)."""
    return troy_view({CHECK_JOB: CHECKOUT, CODE_JOB: CHECKOUT})


def foreign_failure() -> dict:
    """A run of a workflow troy-mode did not write, failed in a step named ``Tests``."""
    return {"jobs": [job(FOREIGN_JOB, FOREIGN_STEPS, "Tests")]}


# -------------------------------------------------------------------- runs

NUMBER, TITLE, BRANCH = 7, F01.title(3), F01.branch(3)


@dataclass
class Run:
    """One workflow run of ``gh run list``, and its jobs.

    Attributes:
        id: The ``databaseId``.
        commit: The ``headSha``.
        at: Its ``createdAt``, in minutes after ``OPENED``.
        conclusion: ``failure``, ``success``, ``cancelled``, or "" while it runs.
        status: ``completed``, ``in_progress``, or ``queued``.
        workflow: The ``workflowName``.
        branch: The ``headBranch``.
        took: Minutes from ``createdAt`` to ``updatedAt``.
        view: The answer of ``gh run view <id> --json jobs``, or None for a
            failure in ``Lint and format``.
    """

    id: int
    commit: str
    at: float
    conclusion: str = "failure"
    status: str = "completed"
    workflow: str = WORKFLOW
    branch: str = BRANCH
    took: float = 5
    view: Optional[dict] = None

    def listed(self) -> dict:
        """The run as ``gh run list --json`` prints it."""
        return {"databaseId": self.id, "headBranch": self.branch, "headSha": self.commit,
                "status": self.status, "conclusion": self.conclusion,
                "createdAt": when(self.at), "updatedAt": when(self.at + self.took),
                "workflowName": self.workflow}

    def jobs(self) -> dict:
        """The answer of ``gh run view <id> --json jobs``."""
        return self.view if self.view is not None else code_failure("Lint and format")


def ci_answers(runs: Sequence[Run]) -> dict:
    """The fake gh's ``runs`` and ``run_views`` for some runs.

    Args:
        runs: The runs, in any order.

    Returns:
        ``runs``, newest first as gh lists them, and ``run_views`` for every failed run.
    """
    newest_first = sorted(runs, key=lambda run: (run.at, run.id), reverse=True)
    return {"runs": [run.listed() for run in newest_first],
            "run_views": {run.id: run.jobs() for run in runs if run.conclusion == "failure"}}


def open_pr(number: int, title: str, branch: str, opened: float = 0) -> dict:
    """One entry of ``gh pr list --state open --json number,title,headRefName,url,createdAt``."""
    return {"number": number, "title": title, "headRefName": branch, "url": pr_url(number),
            "createdAt": when(opened)}


def posted(at: float, body: str) -> dict:
    """A comment on a PR, posted ``at`` minutes after ``OPENED`` through Troy's account."""
    return {"author": {"login": LOGIN}, "body": body, "createdAt": when(at)}


def attempt(number: int, *lines: str, role: str = "Developer") -> str:
    """The body of F07's attempt comment: the heading, a blank line, then the lines."""
    return "\n".join([f"{role} attempt {number}: failed", "", *lines])


def failure(commit: str, runs: Sequence[int], steps: Sequence[str], author: bool = True,
            counted: bool = False, attempt_number: Optional[int] = None) -> dict:
    """One expected entry of an open PR's ``ci_failures`` (note section 3)."""
    # F18 part 1 (contract 10) adds rerun: false here, since these runs give no attempt.
    return {"commit": commit, "runs": list(runs), "steps": list(steps), "author": author,
            "counted": counted, "attempt": attempt_number, "rerun": False}


def normal(entries):
    """Entries with their ``runs`` and ``steps`` lists sorted, since the note fixes no order there.

    Args:
        entries: A list of dicts, or anything else, which is returned as it is.

    Returns:
        The entries in the same order, each with the same keys.
    """
    if not isinstance(entries, list):
        return entries
    return [{key: sorted(value) if key in ("runs", "steps") and isinstance(value, list)
             else value for key, value in entry.items()} if isinstance(entry, dict) else entry
            for entry in entries]


# ------------------------------------------------------------------ status

STATUS_STEPS = [base_step()] + stages(F01, 2)
C0, C1, C2, C3 = (sha(f"commit {n}", f"c{n}") for n in range(4))


def status_case(runs: Sequence[Run] = (), comments: Sequence[dict] = (), **fakes) -> tuple:
    """One open PR, #7 ``[F01 3/6 mock] Count words``, opened at ``OPENED``.

    Args:
        runs: The runs of its branch.
        comments: Its comments, oldest first.
        **fakes: More ``Fakes`` keywords, such as ``fail_calls``.

    Returns:
        ``(steps, fakes keyword arguments)`` for ``fake_status_runs``.
    """
    kwargs = {"prs": [open_pr(NUMBER, TITLE, BRANCH)], "comments": {NUMBER: list(comments)}}
    kwargs.update(ci_answers(runs))
    kwargs.update(fakes)
    return STATUS_STEPS, kwargs


class StatusCiCase(FlowCase):
    """Runs ``status --json`` once per case of ``cases()``, side by side, and reads the PRs."""

    @classmethod
    def cases(cls) -> dict:
        """The cases: a name mapped to ``(steps, fakes keyword arguments)``."""
        return {}

    @classmethod
    def setUpClass(cls):
        """Runs every case once."""
        cls.outs = fake_status_runs(cls.cases())

    def report(self, name: str) -> dict:
        """A case's report, which must exit 0 with ``ok`` true."""
        return self.report_of(self.outs[name][0], 0, "status")

    def pr_entry(self, name: str, number: int = NUMBER) -> dict:
        """A case's ``open_prs`` entry of one PR."""
        report = self.report(name)
        found = [entry for entry in report["open_prs"] if entry.get("number") == number]
        self.assertEqual(len(found), 1, report["open_prs"])
        return found[0]

    def assert_ci(self, name: str, attempts: int, failures: list, number: int = NUMBER) -> None:
        """Asserts a PR's ``ci_failures``, in order, and its ``attempts``."""
        entry = self.pr_entry(name, number)
        self.assertEqual(normal(entry.get("ci_failures")), normal(failures), entry)
        self.assertEqual(entry.get("attempts"), attempts, entry)


class OncePerCommitTests(StatusCiCase):
    """At most one attempt per pushed commit (design 8.5 "At most one attempt", D261)."""

    @classmethod
    def cases(cls) -> dict:
        """One run with two failed jobs, two failed runs of one commit, two failed commits."""
        both = troy_view({CHECK_JOB: "Run troy-check", CODE_JOB: "Tests"})
        return {
            "two jobs": status_case([Run(101, C1, 5, view=both)]),
            "two runs": status_case([Run(101, C1, 5), Run(102, C1, 12)]),
            "two commits": status_case([Run(101, C1, 5), Run(102, C2, 20),
                                        Run(103, C3, 40, "success")]),
            "two workflows": status_case([Run(101, C1, 5),
                                          Run(102, C1, 5, workflow=FOREIGN_WORKFLOW,
                                              view=foreign_failure())]),
        }

    def test_two_failed_jobs_of_one_run_count_once(self):
        """Both jobs of a run failed in a check step: one entry with both steps, 1 attempt."""
        self.assert_ci("two jobs", 1, [failure(
            C1, [101], [TROY_CHECK, label(CODE_JOB, "Tests")], attempt_number=1)])

    def test_two_failed_runs_of_one_commit_count_once(self):
        """The workflow ran twice on one commit (after an edit of the description) and failed
        both times: 1 attempt, and only the newer run is the commit's counting run."""
        self.assert_ci("two runs", 1, [failure(C1, [102], [LINT], attempt_number=1)])

    def test_two_failed_workflows_of_one_commit_count_once(self):
        """troy-mode's workflow and another one both failed on one commit: one entry with both
        runs, and 1 attempt, not one per failed run (design 14.2, "each failed run counted
        instead of each commit"; added after the planted bugs found the gap)."""
        self.assert_ci("two workflows", 1, [failure(
            C1, [101, 102], [LINT, label(FOREIGN_JOB, "Tests")], attempt_number=1)])

    def test_each_failed_commit_counts(self):
        """Two failed pushes, then one that passed: 2 attempts, one entry per failed commit."""
        self.assert_ci("two commits", 2, [failure(C1, [101], [LINT], attempt_number=1),
                                          failure(C2, [102], [LINT], attempt_number=2)])


class NewestRunTests(StatusCiCase):
    """Only the newest run of each workflow on a commit counts, as in ``wait-checks`` (D261)."""

    @classmethod
    def cases(cls) -> dict:
        """An older failure with a newer pass, the reverse, and a newer run still running."""
        return {
            "newer pass": status_case([Run(101, C1, 5), Run(102, C1, 12, "success")]),
            "newer failure": status_case([Run(101, C1, 5, "success"), Run(102, C1, 12)]),
            "newer running": status_case([Run(101, C1, 5), Run(102, C1, 12, "", "in_progress")]),
        }

    def test_newer_pass_clears_an_older_failure(self):
        """A failed run, then a passing run of the same workflow on the commit: nothing counts."""
        self.assert_ci("newer pass", 0, [])

    def test_newer_failure_counts_after_an_older_pass(self):
        """A passing run, then a failed run of the same workflow on the commit: 1 attempt."""
        self.assert_ci("newer failure", 1, [failure(C1, [102], [LINT], attempt_number=1)])

    def test_newer_run_still_running_clears_an_older_failure(self):
        """A failed run, then a run of the same workflow still running: nothing counts."""
        self.assert_ci("newer running", 0, [])


class UnfinishedRunTests(StatusCiCase):
    """A commit whose runs were cancelled, or are still running, counts nothing (D261)."""

    @classmethod
    def cases(cls) -> dict:
        """A cancelled run, a run in progress, and a queued run."""
        return {
            "cancelled": status_case([Run(101, C1, 5, "cancelled")]),
            "in progress": status_case([Run(101, C1, 5, "", "in_progress")]),
            "queued": status_case([Run(101, C1, 5, "", "queued")]),
        }

    def test_cancelled_run_counts_nothing(self):
        """Planted bug "a cancelled run counted as failed": no entry, 0 attempts."""
        self.assert_ci("cancelled", 0, [])

    def test_running_run_counts_nothing(self):
        """A run in progress or queued: no entry, 0 attempts."""
        for name in ("in progress", "queued"):
            with self.subTest(case=name):
                self.assert_ci(name, 0, [])


class RunWindowTests(StatusCiCase):
    """A PR keeps only its branch's runs created at or after it opened (D261)."""

    @classmethod
    def cases(cls) -> dict:
        """A failed run of the same branch half an hour before the PR opened."""
        return {"before open": status_case([Run(101, C1, -30), Run(102, C2, 5, "success")])}

    def test_run_from_before_the_pr_opened_is_left_out(self):
        """Planted bug "runs from before the PR opened kept": no entry, 0 attempts."""
        self.assert_ci("before open", 0, [])


class AuthorStepTests(StatusCiCase):
    """A failure counts only in a check step on the repository's files (design 8.5, D262)."""

    @classmethod
    def cases(cls) -> dict:
        """One failed commit per step, for both packs, and the failures outside the author's."""
        cases = {
            "checkout": status_case([Run(101, C1, 5, view=checkout_failure())]),
            "look for code": status_case([Run(101, C1, 5, view=code_failure("Look for code"))]),
            "micromamba": status_case([Run(101, C1, 5, view=code_failure(MICROMAMBA))]),
            "install": status_case([Run(101, C1, 5,
                                        view=code_failure("Install from the lock"))]),
            "foreign": status_case([Run(101, C1, 5, workflow=FOREIGN_WORKFLOW,
                                        view=foreign_failure()),
                                    Run(102, C1, 5, "success")]),
            "timed out": status_case([Run(101, C1, 5, view=code_failure("Tests",
                                                                         how="cancelled"))]),
            "checkout and comment": status_case(
                [Run(101, C1, 5, view=checkout_failure())],
                [posted(12, attempt(1, "The checkout failed: Repository not found."))]),
            "troy-check": status_case([Run(101, C1, 5, view=check_failure())]),
        }
        for pack, names in (("python", PYTHON_CHECKS), ("cpp", CPP_CHECKS)):
            for name in names:
                cases[f"{pack}: {name}"] = status_case([Run(101, C1, 5,
                                                            view=code_failure(name, pack))])
        return cases

    def assert_outside(self, name: str, steps: list) -> None:
        """Asserts one failed commit outside the author's files: no attempt, ``attempt`` null."""
        self.assert_ci(name, 0, [failure(C1, [101], steps, author=False)])

    def test_checkout_failure_is_not_the_authors(self):
        """Planted bug "a checkout failure counted as the author's" (the pilot's #87)."""
        self.assert_outside("checkout", CHECKOUT_STEPS)

    def test_look_for_code_failure_is_not_the_authors(self):
        """``Look for code`` comes before ``Install from the lock``: no attempt."""
        self.assert_outside("look for code", [label(CODE_JOB, "Look for code")])

    def test_environment_setup_failure_is_not_the_authors(self):
        """The micromamba setup step: no attempt."""
        self.assert_outside("micromamba", [label(CODE_JOB, MICROMAMBA)])

    def test_install_from_the_lock_failure_is_not_the_authors(self):
        """``Install from the lock`` itself is not a check step: no attempt."""
        self.assert_outside("install", [label(CODE_JOB, "Install from the lock")])

    def test_failure_in_a_workflow_troy_mode_did_not_write_is_not_the_authors(self):
        """A step named ``Tests`` failed in another workflow, troy-mode's passed: no attempt."""
        self.assert_outside("foreign", [label(FOREIGN_JOB, "Tests")])

    def test_step_ended_by_a_timeout_is_not_the_authors(self):
        """The job failed with its step ``cancelled`` by a timeout: no failed step, no attempt."""
        self.assert_outside("timed out", [])

    def test_comment_does_not_count_a_failure_outside_the_authors_files(self):
        """A comment after a checkout failure: ``counted`` stays false; the comment's 1 counts."""
        self.assert_ci("checkout and comment", 1, [failure(C1, [101], CHECKOUT_STEPS,
                                                           author=False)])

    def test_troy_check_step_is_the_authors(self):
        """``Run troy-check`` in troy-check's job: an attempt, numbered 1."""
        self.assert_ci("troy-check", 1, [failure(C1, [101], [TROY_CHECK], attempt_number=1)])

    def test_each_python_check_step_is_the_authors(self):
        """Each step of the Python pack's job after ``Install from the lock``: an attempt."""
        for name in PYTHON_CHECKS:
            with self.subTest(step=name):
                self.assert_ci(f"python: {name}", 1, [failure(
                    C1, [101], [label(CODE_JOB, name)], attempt_number=1)])

    def test_each_cpp_check_step_is_the_authors(self):
        """Each step of the C/C++ pack's job after ``Install from the lock``: an attempt."""
        for name in CPP_CHECKS:
            with self.subTest(step=name):
                self.assert_ci(f"cpp: {name}", 1, [failure(
                    C1, [101], [label(CODE_JOB, name)], attempt_number=1)])


class CommitLineTests(StatusCiCase):
    """A comment counts the failed commit its ``Commit:`` line names (design 8.4, 8.5, D261).

    In the first three cases a passing commit was pushed before the comment,
    so only the ``Commit:`` line can count the failed one.
    """

    @classmethod
    def cases(cls) -> dict:
        """The line with the full ID, a 7-digit prefix, a prefix in upper case, and no match."""
        then_pass = [Run(101, C1, 5), Run(102, C2, 20, "success")]

        def line(text: str) -> list:
            """One attempt comment at minute 30 with the given ``Commit:`` value."""
            return [posted(30, attempt(1, f"Commit: {text}", "", "ruff check: 2 errors"))]

        return {
            "full": status_case(then_pass, line(C1)),
            "prefix": status_case(then_pass, line(C1[:7])),
            "upper": status_case(then_pass, line(C1[:7].upper())),
            "no match": status_case([Run(101, C1, 5)], [
                posted(12, attempt(1, "Commit: 0000000", "", "ruff check: 2 errors"))]),
            "two failed": status_case([Run(101, C1, 5), Run(102, C2, 20)], line(C1[:7])),
        }

    def test_full_commit_id_counts_its_commit(self):
        """Planted bug "a Commit: line ignored": the full ID counts C1, so 1 attempt in all."""
        self.assert_ci("full", 1, [failure(C1, [101], [LINT], counted=True)])

    def test_seven_digit_prefix_counts_its_commit(self):
        """Planted bug "a Commit: line ignored": the first 7 digits count C1 too."""
        self.assert_ci("prefix", 1, [failure(C1, [101], [LINT], counted=True)])

    def test_prefix_in_upper_case_counts_its_commit(self):
        """The prefix matches without regard to case (note section 4)."""
        self.assert_ci("upper", 1, [failure(C1, [101], [LINT], counted=True)])

    def test_line_that_matches_nothing_does_not_fall_back(self):
        """A ``Commit:`` line naming no failed commit: the comment does not count C1 by its
        time, though C1 was the newest commit and had failed; C1 takes number 2."""
        self.assert_ci("no match", 2, [failure(C1, [101], [LINT], attempt_number=2)])

    def test_one_comment_counts_one_commit(self):
        """Planted bug "one comment counting two commits": the line names C1, posted after C2
        failed too; C2 stays uncounted and takes number 2."""
        self.assert_ci("two failed", 2, [failure(C1, [101], [LINT], counted=True),
                                         failure(C2, [102], [LINT], attempt_number=2)])


class CommentTimeTests(StatusCiCase):
    """A comment without a ``Commit:`` line counts the newest pushed commit when it was posted,
    only when that commit's failure had finished and no other comment counts it (D261)."""

    @classmethod
    def cases(cls) -> dict:
        """C1's run starts at minute 5 and fails at minute 10; C2's starts at minute 20."""
        local = attempt(1, "ruff check: 2 errors")
        return {
            "after": status_case([Run(101, C1, 5)], [posted(12, local)]),
            "before finished": status_case([Run(101, C1, 5)], [posted(8, local)]),
            "newest only": status_case([Run(101, C1, 5), Run(102, C2, 20)], [posted(30, local)]),
            "newer push": status_case([Run(101, C1, 5), Run(102, C2, 20, "success")],
                                      [posted(30, local)]),
            "already counted": status_case([Run(101, C1, 5), Run(102, C2, 20)], [
                posted(30, attempt(1, f"Commit: {C2}", "", "mypy: 1 error")),
                posted(35, attempt(2, "mypy: 2 errors"))]),
        }

    def test_comment_after_the_failure_counts_it(self):
        """Posted at minute 12, after C1 failed at minute 10: C1 is counted, 1 attempt in all."""
        self.assert_ci("after", 1, [failure(C1, [101], [LINT], counted=True)])

    def test_comment_before_the_failure_finished_counts_nothing(self):
        """Planted bug "a comment ... counting a commit that failed after it was posted":
        posted at minute 8, while C1's run still ran; C1 takes number 2."""
        self.assert_ci("before finished", 2, [failure(C1, [101], [LINT], attempt_number=2)])

    def test_comment_counts_only_the_newest_pushed_commit(self):
        """Planted bug "one comment counting two commits": after C1 and C2 failed, the
        comment counts C2, the newest, and C1 takes number 2."""
        self.assert_ci("newest only", 2, [failure(C1, [101], [LINT], attempt_number=2),
                                          failure(C2, [102], [LINT], counted=True)])

    def test_comment_after_a_newer_push_counts_nothing(self):
        """C2, which passed, was the newest pushed commit when the comment came: C1 is not
        counted and takes number 2."""
        self.assert_ci("newer push", 2, [failure(C1, [101], [LINT], attempt_number=2)])

    def test_comment_does_not_count_a_commit_another_comment_counts(self):
        """Attempt 1's line counts C2; attempt 2, posted while C2 was still the newest, counts
        nothing, and does not move on to C1, which takes number 3."""
        self.assert_ci("already counted", 3, [failure(C1, [101], [LINT], attempt_number=3),
                                              failure(C2, [102], [LINT], counted=True)])


E1, E2, E3 = sha("push 1", "e"), sha("push 2", "9"), sha("push 3", "2")


class CountTests(StatusCiCase):
    """The count: the highest comment number plus each failed commit no comment counts, which
    takes the next number in push order (design 8.5 "The count", D263)."""

    @classmethod
    def cases(cls) -> dict:
        """Comments "attempt 1" and "attempt 3" before a failure; three failed pushes."""
        return {
            "highest": status_case([Run(100, C0, 2, "success"), Run(101, C1, 20)], [
                posted(10, attempt(1, "ruff check: 2 errors")),
                posted(12, attempt(3, "mypy: 1 error"))]),
            # E1 to E3 sort in the reverse of their push order.
            "push order": status_case([Run(101, E1, 5), Run(102, E2, 20), Run(103, E3, 40)], [
                posted(30, attempt(1, f"Commit: {E2}", "", "pytest: 1 failed"))]),
        }

    def test_count_is_the_highest_number_plus_the_failures(self):
        """Planted bug "the CI count added to the number of comments": attempt 1 and attempt 3
        (posted while a passing commit was the newest) and one uncounted failure give 4."""
        self.assert_ci("highest", 4, [failure(C1, [101], [LINT], attempt_number=4)])

    def test_uncounted_failures_take_numbers_in_push_order(self):
        """E2 counted by its line; E1 and E3 take 2 and 3, oldest pushed first, 3 in all."""
        self.assert_ci("push order", 3, [failure(E1, [101], [LINT], attempt_number=2),
                                         failure(E2, [102], [LINT], counted=True),
                                         failure(E3, [103], [LINT], attempt_number=3)])

    def test_next_attempts_equal_the_prs_attempts(self):
        """``continue-pr`` takes the PR's count, CI failures included, for ``next.attempts``."""
        nxt = self.report("push order")["next"]
        self.assertEqual((nxt.get("action"), nxt.get("pr"), nxt.get("attempts")),
                         ("continue-pr", NUMBER, 3), nxt)


class GhFailureTests(StatusCiCase):
    """When gh cannot list the runs, ``status`` adds a note and counts the comments only
    (design 8.5, note section 3)."""

    @classmethod
    def cases(cls) -> dict:
        """``gh run list`` fails, and ``gh run view`` fails."""
        failed = [Run(101, C1, 5)]
        return {
            "run list": status_case(failed, [posted(12, attempt(1, "ruff check: 2 errors"))],
                                    fail_calls=[["run", "list"]]),
            "run view": status_case(failed, [posted(2, attempt(1, "ruff check: 2 errors"))],
                                    fail_calls=[["run", "view"]]),
        }

    def assert_comments_only(self, name: str) -> None:
        """Exit 0 with ``ok``, a note naming the CI runs and the PR, and 1 attempt, no failures."""
        report = self.report(name)
        found = [note for note in report["notes"] if "CI runs" in note and f"#{NUMBER}" in note]
        self.assertNotEqual(found, [], report["notes"])
        self.assert_ci(name, 1, [])

    def test_failing_run_list_adds_a_note_and_counts_the_comments(self):
        """Planted bug "a failing gh run list stopping status"."""
        self.assert_comments_only("run list")

    def test_failing_run_view_adds_a_note_and_counts_the_comments(self):
        """A failing ``gh run view`` is handled the same way."""
        self.assert_comments_only("run view")


PILOT_52 = (sha("pilot 52 push 1"), sha("pilot 52 push 2"))
PILOT_59 = tuple(sha(f"pilot 59 push {n}") for n in range(1, 5))
PILOT_87 = sha("pilot 87 push 1")
GUIDE = ("[docs] Add the usage guide", "troy-mode/usage-guide")


class PilotStatusTests(StatusCiCase):
    """The pilot's PRs as open PRs (design 8.5 and 14.4, D261): 2 on #52, 2 on #59, and no
    attempt for the checkout failure on #87."""

    @classmethod
    def cases(cls) -> dict:
        """#52: two failed pushes, no comment. #59: a failed push with no comment, a failed
        push and then a comment without a ``Commit:`` line, then two passing pushes. #87: a
        checkout failure."""
        b52, b59 = F01.branch(1), F02.branch(1)
        a1, a2 = PILOT_52
        b1, b2, b3, b4 = PILOT_59
        runs = [Run(521, a1, 5, branch=b52, view=check_failure()),
                Run(522, a2, 20, branch=b52, view=check_failure()),
                Run(591, b1, 5, branch=b59, view=check_failure()),
                Run(592, b2, 20, branch=b59, view=check_failure()),
                Run(593, b3, 40, "success", branch=b59),
                Run(594, b4, 60, "success", branch=b59),
                Run(871, PILOT_87, 5, branch=GUIDE[1], view=checkout_failure())]
        kwargs = {"prs": [open_pr(52, F01.title(1), b52), open_pr(59, F02.title(1), b59),
                          open_pr(87, *GUIDE)],
                  "comments": {59: [posted(27, attempt(1, "troy-check pr: 1 problem",
                                                       role="Interface Designer"))]}}
        kwargs.update(ci_answers(runs))
        return {"pilot": ([base_step()], kwargs)}

    def test_pilot_prs_count_two_attempts_each(self):
        """#52 and #59 each count 2 attempts, where the comments alone gave 0 and 1."""
        report = self.report("pilot")
        found = {entry["number"]: entry.get("attempts") for entry in report["open_prs"]}
        self.assertEqual((found.get(52), found.get(59)), (2, 2), report["open_prs"])

    def test_pilot_second_pr_numbers_the_missed_comment(self):
        """#59: the comment counts its second push; the first takes number 2."""
        b1, b2 = PILOT_59[:2]
        self.assert_ci("pilot", 2, [failure(b1, [591], [TROY_CHECK], attempt_number=2),
                                    failure(b2, [592], [TROY_CHECK], counted=True)], number=59)

    def test_pilot_checkout_failure_counts_no_attempt(self):
        """#87: the checkout failure is listed with ``author`` false, and counts nothing."""
        self.assert_ci("pilot", 0, [failure(PILOT_87, [871], CHECKOUT_STEPS, author=False)],
                       number=87)


class StatusGhCallTests(StatusCiCase):
    """The read-only gh calls ``status`` makes for CI (note section 1)."""

    @classmethod
    def cases(cls) -> dict:
        """C1: a failure, then a pass. C2: a failure. C3: cancelled."""
        return {"calls": status_case([Run(101, C1, 5), Run(102, C1, 12, "success"),
                                      Run(103, C2, 20), Run(104, C3, 30, "cancelled")])}

    def argvs(self) -> list:
        """The case's gh calls, after checking that status exited 0."""
        self.report("calls")
        return self.outs["calls"][1].gh_argvs()

    def test_open_pr_list_asks_for_the_creation_time(self):
        """``gh pr list --state open`` asks for ``createdAt`` too."""
        calls = [argv for argv in self.argvs()
                 if argv[:2] == ["pr", "list"] and option_value(argv, "--state") == "open"]
        self.assertEqual(len(calls), 1, calls)
        self.assertIn("createdAt", (option_value(calls[0], "--json") or "").split(","))

    def test_run_list_reads_the_prs_branch(self):
        """One ``gh run list`` per open PR, for its head branch and pull_request runs only."""
        calls = [argv for argv in self.argvs() if argv[:2] == ["run", "list"]]
        self.assertEqual(len(calls), 1, calls)
        argv = calls[0]
        self.assertEqual((option_value(argv, "--branch"), option_value(argv, "--event"),
                          option_value(argv, "--limit")), (BRANCH, "pull_request", "100"), argv)
        fields = set((option_value(argv, "--json") or "").split(","))
        self.assertLessEqual(RUN_FIELDS, fields, argv)

    def test_run_view_reads_the_jobs_of_failed_runs_only(self):
        """``gh run view <id> --json jobs`` for C2's failed run, and none for the passing and
        cancelled runs."""
        calls = [argv for argv in self.argvs() if argv[:2] == ["run", "view"]]
        viewed = {argv[2] for argv in calls}
        self.assertIn("103", viewed, calls)
        self.assertLessEqual(viewed, {"101", "103"}, calls)
        for argv in calls:
            with self.subTest(argv=argv):
                self.assertIn("jobs", (option_value(argv, "--json") or "").split(","))


# --------------------------------------------------------- the check steps

class CheckStepsTests(unittest.TestCase):
    """``troyflow.ci.CHECK_STEPS`` follows troy-mode's own workflow files (D262, note 3)."""

    def test_check_steps_follow_the_workflow_files(self):
        """The named steps after ``Install from the lock`` in each pack's job, and
        ``Run troy-check`` of troy-check's workflow."""
        packs = sorted(path.parent.name for path in PACK_JOBS.glob("*/workflow-job.yml"))
        self.assertIn("Run troy-check", step_names(CHECKS_WORKFLOW))
        expected = {"Run troy-check"}.union(*(pack_check_steps(pack) for pack in packs))
        ci = load_ci()
        self.assertIsInstance(ci.CHECK_STEPS, frozenset)
        self.assertEqual(set(ci.CHECK_STEPS), expected)

    def test_setup_steps_are_not_check_steps(self):
        """The checkout, ``Look for code``, the setup, the lock install, and GitHub's own steps."""
        ci = load_ci()
        for name in ("Look for code", "Install from the lock", CHECKOUT, MICROMAMBA,
                     "Set up job", "Complete job"):
            with self.subTest(step=name):
                self.assertNotIn(name, ci.CHECK_STEPS)

    def test_this_files_step_names_follow_the_workflow_files(self):
        """The check steps these tests fail on are the packs' own (keeps the fixtures true)."""
        self.assertEqual(pack_check_steps("python"), list(PYTHON_CHECKS))
        self.assertEqual(pack_check_steps("cpp"), list(CPP_CHECKS))


# ---------------------------------------------------------------- the skill

class SkillTests(unittest.TestCase):
    """The entry skill's merge step posts the missed comment (design 8.6, 14.1, D263)."""

    @classmethod
    def setUpClass(cls):
        """Cuts the section "Merging" out of SKILL.md."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.merging = section(split_skill(text)[1], "### Merging")

    def test_merge_step_reads_ci_failures(self):
        """The merge step reads the pushed commit in ``ci_failures``."""
        self.assertIn("ci_failures", self.merging)

    def test_merge_step_posts_the_commit_line(self):
        """The merge step posts the attempt comment with its ``Commit:`` line."""
        self.assertIn("Commit:", self.merging)


# -------------------------------------------------------------------- retro

MERGED_AFTER = 360            # minutes from a merged PR's createdAt to its mergedAt
TEST_PLAN_BRANCH = "troy-mode/v0.1-test-plan"


@dataclass
class Merged:
    """One merged PR of a retro history; its place in the list is its slot (one day each).

    Attributes:
        number: The PR number.
        step: Its commit on ``origin/main`` (a rebase merge).
        branch: Its ``headRefName``.
    """

    number: int
    step: Step
    branch: str


def at_slot(slot: int, minutes: float = 0) -> float:
    """Minutes after ``OPENED`` of a time in a slot: the slot's PR opens at minute 0."""
    return slot * DAY + minutes


def merged_entry(number: int, title: str, oid: Optional[str], branch: str, slot: int) -> dict:
    """One entry of ``gh pr list --state merged`` with the fields of note section 1."""
    return {"number": number, "title": title, "url": pr_url(number),
            "mergeCommit": {"oid": oid} if oid else None, "headRefName": branch,
            "createdAt": when(at_slot(slot)), "mergedAt": when(at_slot(slot, MERGED_AFTER))}


def retro_fakes(project: Project, prs: Sequence[Merged], runs: Sequence[Run],
                comments: Optional[dict] = None, extra: Sequence[dict] = (), **fakes) -> Fakes:
    """Fakes that serve a retro history's merged PRs, their comments, and their runs.

    Args:
        project: The clone, whose ``origin/main`` holds each PR's commit.
        prs: The merged PRs, in slot order.
        runs: Every run.
        comments: PR number mapped to its comments.
        extra: More merged PRs, not on ``origin/main``.
        **fakes: More ``Fakes`` keywords.

    Returns:
        The fakes.
    """
    shas = subject_commits(project)
    merged = [merged_entry(pr.number, pr.step.subject, shas[pr.step.subject], pr.branch, slot)
              for slot, pr in enumerate(prs)] + list(extra)
    return Fakes(merged=merged, comments=comments, **ci_answers(runs), **fakes)


COUNT_PRS = [
    Merged(50, base_step(), "troy-mode/init"),
    Merged(51, step("[docs] Add the v0.1 test plan", {"docs/notes/plan-1.md": "# Plan 1\n"}),
           TEST_PLAN_BRANCH),
    Merged(52, stage_step(F01, 1), F01.branch(1)),
    Merged(53, stage_step(F01, 2), F01.branch(2)),
    Merged(54, stage_step(F01, 3), F01.branch(3)),
    Merged(55, stage_step(F01, 4), F01.branch(4)),
    Merged(56, stage_step(F01, 5), F01.branch(5)),
    Merged(59, stage_step(F02, 1), F02.branch(1)),
    Merged(60, stage_step(F01, 6), F01.branch(6)),
    Merged(61, step("[docs] Update the v0.1 test plan", {"docs/notes/plan-2.md": "# Plan 2\n"}),
           TEST_PLAN_BRANCH),
    Merged(62, step("[docs] Fix a typo in the README", {"README.md": "# wordcount\n\nCounts.\n"}),
           "troy-mode/readme-typo"),
    Merged(63, release_step("v0.1.0"), "troy-mode/release-v0.1.0"),
]
SLOT = {pr.number: slot for slot, pr in enumerate(COUNT_PRS)}
HEAD = {pr.number: pr.branch for pr in COUNT_PRS}
# Each merged PR's pushes, by name.
R = {name: sha(f"retro {name}") for name in (
    "51 closed", "51 fail", "51 pass", "52 fail 1", "52 fail 2", "52 pass", "53 checkout",
    "53 pass", "54 fail", "54 pass", "55 fail", "55 pass", "56 pass", "59 fail 1", "59 fail 2",
    "59 pass", "61 fail", "61 pass", "61 later", "62 fail", "62 pass")}


def count_run(run_id: int, name: str, number: int, minutes: float, conclusion: str = "failure",
              view: Optional[dict] = None) -> Run:
    """A run of PR ``number``'s branch, ``minutes`` after that PR opened."""
    return Run(run_id, R[name], at_slot(SLOT[number], minutes), conclusion,
               branch=HEAD[number], view=view)


COUNT_RUNS = [
    # A closed PR used troy-mode/v0.1-test-plan before #51 opened.
    count_run(510, "51 closed", 51, -120, view=check_failure()),
    count_run(511, "51 fail", 51, 5, view=check_failure()),
    count_run(512, "51 pass", 51, 30, "success"),
    count_run(521, "52 fail 1", 52, 5, view=check_failure()),
    count_run(522, "52 fail 2", 52, 20, view=check_failure()),
    count_run(523, "52 pass", 52, 40, "success"),
    count_run(531, "53 checkout", 53, 5, view=checkout_failure()),
    count_run(532, "53 pass", 53, 20, "success"),
    count_run(541, "54 fail", 54, 5),
    count_run(542, "54 pass", 54, 20, "success"),
    count_run(551, "55 fail", 55, 5, view=code_failure("Tests")),
    count_run(552, "55 pass", 55, 20, "success"),
    count_run(561, "56 pass", 56, 5, "success"),
    count_run(591, "59 fail 1", 59, 5, view=check_failure()),
    count_run(592, "59 fail 2", 59, 20, view=check_failure()),
    count_run(593, "59 pass", 59, 40, "success"),
    count_run(611, "61 fail", 61, 5, view=check_failure()),
    count_run(612, "61 pass", 61, 20, "success"),
    # A later PR, not merged, used troy-mode/v0.1-test-plan after #61 merged.
    count_run(613, "61 later", 61, MERGED_AFTER + 120, view=check_failure()),
    count_run(621, "62 fail", 62, 5, view=check_failure()),
    count_run(622, "62 pass", 62, 20, "success"),
]
COUNT_COMMENTS = {
    55: [posted(at_slot(SLOT[55], 12), attempt(1, f"Commit: {R['55 fail'][:7]}", "",
                                               "pytest: 2 failed", role="Test Engineer"))],
    56: [posted(at_slot(SLOT[56], 2), attempt(1, "mypy: 1 error"))],
    59: [posted(at_slot(SLOT[59], 27), attempt(1, "troy-check pr: 1 problem",
                                               role="Interface Designer"))],
}
NEVER_ON_MAIN = {"number": 40, "title": "[docs] Never on main", "url": pr_url(40),
                 "mergeCommit": None, "headRefName": "troy-mode/never",
                 "createdAt": "2026-11-01T08:00:00Z", "mergedAt": "2026-11-01T09:00:00Z"}


def ci_attempt(number: int, role: str, name: str, run_id: int, steps: list) -> dict:
    """One expected entry of retro's ``ci_attempts`` (note section 5)."""
    return {"pr": number, "url": pr_url(number), "role": role, "commit": R[name],
            "runs": [run_id], "steps": steps}


class RetroCountTests(FlowCase):
    """``retro`` counts each PR's CI failures as F07 section 8.5 says (F08 design 7 step 1,
    11.1 "Notes and retro"; F07 D261 to D263).

    One version, v0.1.0, with these merged PRs: #51 and #61 reuse the branch
    ``troy-mode/v0.1-test-plan`` (a closed PR failed on it before #51, a later
    one after #61); #52 and #59 are the pilot's (two failed pushes without a
    comment; a failed push without a comment and one that a comment without a
    ``Commit:`` line counts); #53 failed in the checkout; #54 failed in
    ``Lint and format``; #55's failure is counted by a ``Commit:`` line; #56
    has only a Developer attempt comment for local checks; #62 is a ``[docs]``
    PR. #40 was merged but is not on ``origin/main``.
    """

    @classmethod
    def setUpClass(cls):
        """One clone and one ``retro --tag v0.1.0``."""
        cls.project = Project([pr.step for pr in COUNT_PRS])
        cls.fakes = retro_fakes(cls.project, COUNT_PRS, COUNT_RUNS, COUNT_COMMENTS,
                                [NEVER_ON_MAIN])
        cls.out = cls.project.run("retro", "--tag", "v0.1.0", fakes=cls.fakes)

    def report(self) -> dict:
        """The retro report, which must exit 0."""
        return self.report_of(self.out, 0, "retro")

    def group(self, key: str) -> dict:
        """One group of the report, by key."""
        groups = self.report()["groups"]
        found = [group for group in groups if group["key"] == key]
        self.assertEqual(len(found), 1, [group["key"] for group in groups])
        return found[0]

    def test_ci_attempts_list_each_uncounted_author_failure(self):
        """Each author failure no comment counts, by PR and then push order, with its role."""
        self.assertEqual(normal(self.report().get("ci_attempts")), normal([
            ci_attempt(51, "Test Manager", "51 fail", 511, [TROY_CHECK]),
            ci_attempt(52, "Interface Designer", "52 fail 1", 521, [TROY_CHECK]),
            ci_attempt(52, "Interface Designer", "52 fail 2", 522, [TROY_CHECK]),
            ci_attempt(54, "Developer", "54 fail", 541, [LINT]),
            ci_attempt(59, "Interface Designer", "59 fail 1", 591, [TROY_CHECK]),
            ci_attempt(61, "Test Manager", "61 fail", 611, [TROY_CHECK]),
            ci_attempt(62, "Author", "62 fail", 621, [TROY_CHECK]),
        ]))

    def test_checkout_failure_is_in_ci_other_only(self):
        """Planted bug "a checkout failure grouped as an attempt": #53's failure is in
        ``ci_other`` and in no group."""
        report = self.report()
        self.assertEqual(normal(report.get("ci_other")), normal([
            {"pr": 53, "url": pr_url(53), "commit": R["53 checkout"], "runs": [531],
             "steps": CHECKOUT_STEPS}]))
        heading = f"CI: {R['53 checkout'][:7]}"
        for group in report["groups"]:
            with self.subTest(group=group["key"]):
                self.assertNotIn(53, group["prs"])
                self.assertNotIn(heading, [item["heading"] for item in group["evidence"]])

    def test_failure_a_comment_counts_is_not_added(self):
        """Planted bug "a CI failure that a comment counts counted again": #55's failure is
        counted by its comment's ``Commit:`` line, so its group holds the comment only."""
        attempts = self.report().get("ci_attempts")
        self.assertIsInstance(attempts, list)
        self.assertNotIn(55, [entry.get("pr") for entry in attempts])
        group = self.group("Test Engineer attempt failed")
        self.assertEqual((group["kind"], group["prs"], group["count"], group["repeated"]),
                         ("attempt", [55], 1, False))
        self.assertEqual([item["heading"] for item in group["evidence"]],
                         ["Test Engineer attempt 1: failed"])

    def test_ci_failure_joins_the_roles_attempt_group(self):
        """#54's CI failure and #56's attempt comment share ``Developer attempt failed``,
        seen in two PRs, so it is repeated; the CI entry's heading names its commit."""
        group = self.group("Developer attempt failed")
        self.assertEqual((group["kind"], group["prs"], group["count"], group["repeated"]),
                         ("attempt", [54, 56], 2, True))
        evidence = sorted((item["pr"], item["url"], item["heading"], item["text"])
                          for item in group["evidence"])
        self.assertEqual(evidence, [
            (54, pr_url(54), f"CI: {R['54 fail'][:7]}", LINT),
            (56, pr_url(56), "Developer attempt 1: failed", "mypy: 1 error")])
        self.assertIn("Developer attempt failed", self.report()["repeated"])

    def test_pilot_prs_count_four_interface_designer_attempts(self):
        """#52's two failures, #59's uncounted one, and #59's comment: 4 in two PRs."""
        group = self.group("Interface Designer attempt failed")
        self.assertEqual((group["prs"], group["count"], group["repeated"]), ([52, 59], 4, True))
        headings = sorted(item["heading"] for item in group["evidence"])
        self.assertEqual(headings, sorted([
            f"CI: {R['52 fail 1'][:7]}", f"CI: {R['52 fail 2'][:7]}",
            f"CI: {R['59 fail 1'][:7]}", "Interface Designer attempt 1: failed"]))

    def test_reused_branch_keeps_each_prs_runs(self):
        """#51 and #61 share a branch: each keeps only the failure made while it was open,
        not the closed PR's from before #51 or the later PR's from after #61."""
        found = [(entry.get("pr"), entry.get("commit"))
                 for entry in self.report().get("ci_attempts", []) if entry.get("pr") in (51, 61)]
        self.assertEqual(found, [(51, R["51 fail"]), (61, R["61 fail"])])
        group = self.group("Test Manager attempt failed")
        self.assertEqual((group["prs"], group["count"], group["repeated"]), ([51, 61], 2, True))

    def test_docs_pr_role_is_author(self):
        """A ``[docs]`` PR gives no task, so its failure is grouped as ``Author``."""
        group = self.group("Author attempt failed")
        self.assertEqual((group["kind"], group["prs"], group["count"]), ("attempt", [62], 1))

    def test_merged_list_asks_for_branches_and_times(self):
        """``gh pr list --state merged`` asks for ``headRefName``, ``createdAt``, ``mergedAt``."""
        self.report()
        calls = [argv for argv in self.fakes.gh_argvs()
                 if argv[:2] == ["pr", "list"] and option_value(argv, "--state") == "merged"]
        self.assertEqual(len(calls), 1, calls)
        self.assertLessEqual(MERGED_FIELDS, set((option_value(calls[0], "--json") or "")
                                                .split(",")))

    def test_one_run_list_from_the_oldest_range_prs_date(self):
        """One ``gh run list``, without ``--branch``, ``--created 2026-11-10..*`` (#50's date,
        not #40's, which is not in the range), and ``--limit 1000``."""
        self.report()
        calls = [argv for argv in self.fakes.gh_argvs() if argv[:2] == ["run", "list"]]
        self.assertEqual(len(calls), 1, calls)
        argv = calls[0]
        self.assertIsNone(option_value(argv, "--branch"), argv)
        self.assertEqual((option_value(argv, "--event"), option_value(argv, "--limit"),
                          option_value(argv, "--created")),
                         ("pull_request", "1000", "2026-11-10..*"), argv)
        self.assertLessEqual(RUN_FIELDS, set((option_value(argv, "--json") or "").split(",")))


ROLE_PRS = [
    Merged(1, base_step(), "troy-mode/init"),
    Merged(2, stage_step(F01, 1), F01.branch(1)),
    Merged(3, stage_step(F01, 2), F01.branch(2)),
    Merged(4, stage_step(F01, 3), F01.branch(3)),
    Merged(5, stage_step(F01, 4), F01.branch(4)),
    Merged(6, stage_step(F01, 5), F01.branch(5)),
    Merged(7, stage_step(F01, 6), F01.branch(6)),
    Merged(8, bug_step("B4", "test", "Wrong count"), "troy-mode/b4-test"),
    Merged(9, bug_step("B4", "fix", "Wrong count"), "troy-mode/b4-fix"),
    Merged(10, step("[docs] Add the v0.1 test plan", {"docs/notes/plan.md": "# Plan\n"}),
           TEST_PLAN_BRANCH),
    Merged(11, version_tests_step("v0.1"), "troy-mode/v0.1-tests"),
    Merged(12, step("[v0.1 tests] Fix the S01 test",
                    {"version-tests/test_v0_1_fix.py": '"""Fixed."""\n'}),
           "troy-mode/v0.1-tests-fix"),
    Merged(13, step("[refactor] Apply P01 to the parser",
                    {"src/wordcount/parser.py": '"""Parser."""\n'}), "troy-mode/p01-refactor"),
    Merged(14, step("[docs] Explain the README", {"README.md": "# wordcount\n\nExplained.\n"}),
           "troy-mode/readme"),
    Merged(15, release_step("v0.1.0"), "troy-mode/release-v0.1.0"),
]
ROLES = {2: "Interface Designer", 3: "Test Manager", 4: "Developer", 5: "Test Engineer",
         6: "Developer", 7: "Product Manager", 8: "Test Engineer", 9: "Developer",
         10: "Test Manager", 11: "Test Engineer", 12: "Test Engineer", 13: "Developer",
         14: "Author"}


class RetroRoleTests(FlowCase):
    """The role of a CI attempt: the author of the task ``status`` gives for the PR's title
    (F08 design 7 step 1, note section 5). Each PR #2 to #14 has one failure, uncounted."""

    @classmethod
    def setUpClass(cls):
        """One clone and one ``retro --tag v0.1.0``."""
        project = Project([pr.step for pr in ROLE_PRS])
        runs = [Run(number * 10 + 1, sha(f"role {number}"), at_slot(slot, 5),
                    branch=ROLE_PRS[slot].branch, view=check_failure())
                for slot, number in enumerate(pr.number for pr in ROLE_PRS) if number in ROLES]
        fakes = retro_fakes(project, ROLE_PRS, runs,
                            issue_views={4: issue(4, "Words counted twice")})
        cls.out = project.run("retro", "--tag", "v0.1.0", fakes=fakes)

    def test_each_title_gives_its_role(self):
        """Stages 1 to 6, a bug's test and fix, TM7, TE5, TE3, DV5, and a ``[docs]`` PR."""
        report = self.report_of(self.out, 0, "retro")
        found = {entry.get("pr"): entry.get("role") for entry in report.get("ci_attempts", [])}
        for number, role in ROLES.items():
            with self.subTest(pr=number):
                self.assertEqual(found.get(number), role, report.get("ci_attempts"))

    def test_roles_name_the_attempt_groups(self):
        """The failures are grouped as ``<Role> attempt failed``, each with its PRs."""
        report = self.report_of(self.out, 0, "retro")
        found = {group["key"]: group["prs"] for group in report["groups"]
                 if group["kind"] == "attempt"}
        expected: dict = {}
        for number, role in ROLES.items():
            expected.setdefault(f"{role} attempt failed", []).append(number)
        self.assertEqual(found, expected)


class RetroNoteTests(FlowCase):
    """``retro``'s notes about the runs (F07 design 8.5 "The runs", note section 5)."""

    @classmethod
    def setUpClass(cls):
        """``retro --tag v0.1.0`` with 1,000 runs, and with ``gh run list`` failing."""
        prs = [Merged(1, base_step(), "troy-mode/init"),
               Merged(2, release_step("v0.1.0"), "troy-mode/release-v0.1.0")]
        project = Project([pr.step for pr in prs])
        many = [Run(n, sha(f"other {n}"), n / 10, "success", branch="troy-mode/other")
                for n in range(1, 1001)]
        fakes = {"thousand": retro_fakes(project, prs, many),
                 "fails": retro_fakes(project, prs, [Run(11, C1, 5, branch="troy-mode/init")],
                                      fail_calls=[["run", "list"]])}
        names = list(fakes)
        outs = parallel(lambda name: project.run("retro", "--tag", "v0.1.0", fakes=fakes[name]),
                        names)
        cls.outs = dict(zip(names, outs))

    def test_thousand_runs_add_a_note(self):
        """When 1,000 runs come back, older runs may be missing: a note says ``1,000``."""
        report = self.report_of(self.outs["thousand"], 0, "retro")
        self.assertTrue(any("1,000" in note for note in report["notes"]), report["notes"])

    def test_failing_run_list_adds_a_note(self):
        """``gh run list`` fails: exit 0, a note naming the CI runs, and no CI entries."""
        report = self.report_of(self.outs["fails"], 0, "retro")
        self.assertTrue(any("CI runs" in note for note in report["notes"]), report["notes"])
        self.assertEqual((report.get("ci_attempts"), report.get("ci_other")), ([], []))


if __name__ == "__main__":
    unittest.main()
