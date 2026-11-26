"""Attempts from failed CI runs (F07 design 8.5, D261 to D263, tstack issue #73).

A PR's pushed commits each count at most one attempt: the newest run of each
workflow on a commit decides, and a commit counts only when a step that runs
a check on the repository's files failed. An attempt comment already counts
the commit its `Commit:` line names; a comment without one counts the PR's
newest pushed commit at the time it was posted, when that commit had failed
by then and nothing else counts it. Every gh call here is read-only.
"""

import datetime
import re
from dataclasses import dataclass, field

from . import github
from .repo import Repo

RUN_FIELDS = ("databaseId,headBranch,headSha,status,conclusion,createdAt,updatedAt,workflowName,"
              "attempt")
# The steps that run a check on the repository's files (D262): troy-check's job
# (F02 section 8) and each step of a language pack's job after "Install from
# the lock" (F03). Any other failed step lies outside the author's files.
CHECK_STEPS = frozenset({
    "Run troy-check",
    "Lint and format", "Types", "Tests", "Coverage report", "Run troy-check code",
    "Configure and build", "Format and lint changed files", "Doc comments",
})
# troy-mode's own jobs: troy-check's (F02) and the language pack's (F03). A step
# of any other job, such as one of a workflow troy-mode did not write, is not a
# check of the author's files, whatever its name.
CHECK_JOBS = frozenset({"troy-mode checks", "troy-mode code checks"})
VERSION_LIMIT = 1000
_COMMIT_LINE = re.compile(r"^Commit: ([0-9a-fA-F]{7,40})\s*$", re.M)
_ROLES = {"AR": "Architect", "IF": "Interface Designer", "TM": "Test Manager",
          "DV": "Developer", "TE": "Test Engineer", "CR": "Code Reviewer",
          "PM": "Product Manager"}


@dataclass
class Failure:
    """One pushed commit whose counting runs failed.

    Attributes:
        commit: The head commit as gh gave it.
        first: When the commit's first run was created, its push time.
        runs: The failed counting runs' IDs.
        steps: Each failed step as "<job> / <step>".
        author: A check step failed, so the failure lies in the author's files.
        failed_at: When the first of its failed runs finished.
        counted: An attempt comment counts it.
        attempt: The attempt number an author failure not counted takes.
        rerun: One of its failed runs is a re-run that failed again (gh's `attempt`
            2 or more), so a failure outside the authors' files is not re-run
            twice (F18 design 4.3).
    """

    commit: str
    first: datetime.datetime
    runs: list[int] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    author: bool = False
    failed_at: datetime.datetime | None = None
    counted: bool = False
    attempt: int | None = None
    rerun: bool = False

    def entry(self) -> dict:
        """The report's ci_failures entry."""
        return {"commit": self.commit, "runs": self.runs, "steps": self.steps,
                "author": self.author, "counted": self.counted, "attempt": self.attempt,
                "rerun": self.rerun}


@dataclass
class Count:
    """A PR's attempts from its comments and its CI runs.

    Attributes:
        attempts: The highest comment number plus each author failure not counted.
        failures: Every failed commit, oldest push first.
    """

    attempts: int = 0
    failures: list[Failure] = field(default_factory=list)


def when(text) -> datetime.datetime | None:
    """Parses one of gh's ISO 8601 times, or returns None."""
    try:
        moment = datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=datetime.timezone.utc)


def role_of(task: str | None) -> str:
    """Names the role of a task by its first two letters, "Author" without one."""
    return _ROLES.get((task or "")[:2], "Author")


def branch_runs(repo: Repo, branch: str) -> list[dict]:
    """Lists the pull request runs of one head branch (design 8.5)."""
    return github.gh_list(repo, "run", "list", "--branch", branch, "--event", "pull_request",
                          "--limit", "100", "--json", RUN_FIELDS)


def version_runs(repo: Repo, since: datetime.datetime | None) -> list[dict]:
    """Lists the pull request runs created since a day, in one call, for retro."""
    args = ["run", "list", "--event", "pull_request", "--limit", str(VERSION_LIMIT),
            "--json", RUN_FIELDS]
    if since is not None:
        # GitHub's "<day>..*" means on or after that day. It needs no ">",
        # which a Windows batch file would take as a redirection.
        args += ["--created", f"{since.date().isoformat()}..*"]
    return github.gh_list(repo, *args)


def runs_of(pr: dict, runs: list[dict]) -> list[dict]:
    """Keeps the runs of a PR's head branch made while the PR was open (D261)."""
    opened = when(pr.get("createdAt")) if pr.get("createdAt") else None
    ended = pr.get("mergedAt") or pr.get("closedAt")
    ended = when(ended) if ended else None
    kept = []
    for run in runs:
        if run.get("headBranch") != pr.get("headRefName") or not run.get("headSha"):
            continue
        made = when(run.get("createdAt"))
        if made is None or (opened and made < opened) or (ended and made > ended):
            continue
        kept.append(run)
    return kept


def _heads(runs: list[dict]) -> list[tuple[str, datetime.datetime]]:
    """Each head commit with its first run's creation time, oldest first."""
    first: dict[str, datetime.datetime] = {}
    for run in runs:
        made = when(run.get("createdAt"))
        sha = str(run["headSha"])
        if sha not in first or made < first[sha]:
            first[sha] = made
    return sorted(first.items(), key=lambda item: item[1])


def _newest(runs: list[dict]) -> list[dict]:
    """The newest run of each workflow, among one commit's runs."""
    newest: dict[str, dict] = {}
    for run in runs:
        name = str(run.get("workflowName") or "")
        key = (when(run.get("createdAt")), int(run.get("databaseId") or 0))
        old = newest.get(name)
        if old is None or key > (when(old.get("createdAt")), int(old.get("databaseId") or 0)):
            newest[name] = run
    return list(newest.values())


def _failed_steps(repo: Repo, run_id: int) -> tuple[list[str], bool]:
    """The failed steps of one run, and whether one of them is a check step."""
    data = github.gh_object(repo, "run", "view", str(run_id), "--json", "jobs")
    steps, author = [], False
    for job in data.get("jobs") or []:
        if not isinstance(job, dict) or str(job.get("conclusion")).lower() != "failure":
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict) and str(step.get("conclusion")).lower() == "failure":
                steps.append(f"{job.get('name')} / {step.get('name')}")
                author = author or (job.get("name") in CHECK_JOBS
                                    and step.get("name") in CHECK_STEPS)
    return steps, author


def _attempt(run: dict) -> int:
    """A run's attempt number, 1 when gh gives none."""
    try:
        return int(run.get("attempt") or 1)
    except (TypeError, ValueError):
        return 1


def failures(repo: Repo, runs: list[dict]) -> tuple[list[tuple[str, datetime.datetime]],
                                                       list[Failure]]:
    """Finds the PR's failed commits among its runs.

    Returns:
        Every head commit with its push time, oldest first, and the failed
        ones, oldest first.
    """
    heads = _heads(runs)
    found = []
    for sha, first in heads:
        mine = [r for r in runs if str(r["headSha"]) == sha]
        failed = [r for r in _newest(mine) if str(r.get("status")).lower() == "completed"
                  and str(r.get("conclusion")).lower() == "failure"]
        if not failed:
            continue
        failure = Failure(sha, first)
        author_ends = []
        for run in sorted(failed, key=lambda r: when(r.get("createdAt"))):
            steps, author = _failed_steps(repo, int(run["databaseId"]))
            failure.runs.append(int(run["databaseId"]))
            failure.steps += steps
            failure.rerun = failure.rerun or _attempt(run) >= 2
            if author:
                failure.author = True
                author_ends.append(when(run.get("updatedAt")))
        ends = [e for e in author_ends if e is not None]
        failure.failed_at = min(ends) if ends else None
        found.append(failure)
    return heads, found


def count(heads: list[tuple[str, datetime.datetime]], found: list[Failure],
          comments: list[tuple[str, str]]) -> Count:
    """Counts a PR's attempts from its comments and its failed commits (design 8.5).

    Args:
        heads: Every pushed commit with its push time, oldest first.
        found: The failed commits, oldest first.
        comments: The PR's comments as (time, body), oldest first.

    Returns:
        The count, with each failure's counted and attempt set.
    """
    attempts = []
    for moment, body in comments:
        number = github.attempt_number(body)
        if number:
            attempts.append((when(moment), body, number))
    highest = max([number for _, _, number in attempts] + [0])
    authors = [f for f in found if f.author]
    fallback = []
    for moment, body, _ in attempts:
        line = _COMMIT_LINE.search(body.split("\n", 1)[1] if "\n" in body else "")
        if line is None:
            fallback.append(moment)
            continue
        prefix = line.group(1).lower()
        match = next((f for f in authors if not f.counted and f.commit.lower().startswith(prefix)),
                     None)
        if match is not None:
            match.counted = True
    for moment in fallback:
        if moment is None:
            continue
        pushed = [sha for sha, first in heads if first <= moment]
        if not pushed:
            continue
        match = next((f for f in authors if f.commit == pushed[-1]), None)
        if match and not match.counted and match.failed_at and match.failed_at <= moment:
            match.counted = True
    number = highest
    for failure in authors:
        if not failure.counted:
            number += 1
            failure.attempt = number
    return Count(number, found)


def pr_count(repo: Repo, pr: dict, runs: list[dict], comments: list[tuple[str, str]]) -> Count:
    """Counts one PR's attempts from the runs of its head branch and its comments."""
    heads, found = failures(repo, runs_of(pr, runs))
    return count(heads, found, comments)
