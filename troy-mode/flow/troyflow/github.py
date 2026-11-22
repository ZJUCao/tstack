"""Open PRs and F07's comments on them, read through gh (F07 design 5.1 and 8.4).

F15 adds the headings troy-mode writes on issues, Troy's PR reviews, and the
generic list and object reads its issue module uses (F15 design 3.3 and 8.4).

The engine only reads GitHub. Every call here is read-only.
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field

from .errors import FlowError
from .repo import Repo
from .versions import SCENARIO_ID

ROLE_NAMES = ("Architect", "Interface Designer", "Test Manager", "Developer", "Test Engineer",
              "Code Reviewer", "Product Manager")
_ROLE = "|".join(ROLE_NAMES)
REVIEW = re.compile(rf"^({_ROLE}) review, round ([1-9][0-9]*): "
                    r"(approved|changes-requested|needs-answer|escalate)$")
ATTEMPT = re.compile(rf"^({_ROLE}) attempt ([1-9][0-9]*): failed$")
ESCALATION = re.compile(r"^Escalation: .+$")
WAITING = re.compile(r"^Waiting for Troy: .+$")
# F08's comments on a release PR (F08 design 5.5 to 5.8 and 7).
RELEASE_RUN = re.compile(r"^Release test, run ([1-9][0-9]*): (passed|failed)$")
TROY_RUN = re.compile(r"^Release test by Troy, run ([1-9][0-9]*): "
                      r"(accepted|failed|not accepted)$")
RETROSPECTIVE = re.compile(r"^Retrospective: (v\d+\.\d+\.\d+)$")
DEFERRED = re.compile(r"^Bug deferred by Troy: #([1-9][0-9]*)$")
# troy-mode's headings on issues (F15 design 8.4).
IDEA = re.compile(r"^Idea: (requirement change|bug|rule|answered|later|in the requirements)")
REPLY = re.compile(r"^Reply to Troy")
DEVICE_RUN = re.compile(r"^Device test, run ([1-9][0-9]*): ready$")
_COMMIT = re.compile(r"^Commit tested: ([0-9a-f]{7,40})\s*$", re.M)
_OWN = (REVIEW, ATTEMPT, ESCALATION, WAITING, RELEASE_RUN, TROY_RUN, RETROSPECTIVE, DEFERRED,
        IDEA, REPLY, DEVICE_RUN)


@dataclass
class Comments:
    """What F07's comments and Troy's say about one PR (design 8.3 to 8.5).

    Attributes:
        reviews: Every review heading, oldest first: role, round, and result.
        rounds: The highest review round, 0 without one.
        attempts: The highest attempt number, 0 without one.
        troy: Troy's comments after F07's last comment.
        last: The first line of F07's last comment, or None.
        waiting: F07's last comment waits for Troy, and Troy has not answered.
        escalated: The same, for an escalation.
        runs: The release test records, oldest first: by ("claude" or
            "troy"), run, and result (F08 design 5.5 and 5.6).
        deferred: Issue numbers of the bugs Troy deferred (F08 D74).
        retrospectives: The tags of the Retrospective comments.
        commits: The commit each passed release test run names, by run (F15 6.2).
        troy_failed: The scenario IDs each failed run of Troy's names, by run (F15 6.3).
    """

    reviews: list[dict] = field(default_factory=list)
    rounds: int = 0
    attempts: int = 0
    troy: list[str] = field(default_factory=list)
    last: str | None = None
    waiting: bool = False
    escalated: bool = False
    runs: list[dict] = field(default_factory=list)
    deferred: list[int] = field(default_factory=list)
    retrospectives: list[str] = field(default_factory=list)
    commits: dict[int, str] = field(default_factory=dict)
    troy_failed: dict[int, list[str]] = field(default_factory=dict)


def heading(body: str) -> str:
    """Returns a comment's first line, trimmed."""
    lines = (body or "").strip().split("\n")
    return lines[0].strip() if lines else ""


def is_f07(body: str) -> bool:
    """Tells whether a comment starts with one of F07's or F08's fixed headings (design 8.4)."""
    first = heading(body)
    return any(p.match(first) for p in _OWN)


def attempt_number(text: str) -> int:
    """Returns the attempt number of an attempt heading, or 0 for any other text."""
    match = ATTEMPT.match(heading(text))
    return int(match.group(2)) if match else 0


def read_comments(bodies: list[str]) -> Comments:
    """Counts rounds and attempts, and finds what waits on Troy, from a PR's comments.

    Args:
        bodies: The comments' bodies, oldest first.

    Returns:
        What the comments say. Troy's comments never count as rounds or attempts.
    """
    result = Comments()
    for body in bodies:
        first = heading(body)
        if not is_f07(body):
            result.troy.append(body)
            continue
        result.troy, result.last = [], first
        review = REVIEW.match(first)
        if review:
            result.reviews.append({"role": review.group(1), "round": int(review.group(2)),
                                   "result": review.group(3)})
            result.rounds = max(result.rounds, int(review.group(2)))
        result.attempts = max(result.attempts, attempt_number(first))
        _read_release(result, first, body)
    last = result.last or ""
    result.escalated = not result.troy and bool(ESCALATION.match(last))
    result.waiting = not result.troy and bool(ESCALATION.match(last) or WAITING.match(last))
    return result


def _read_release(result: Comments, first: str, body: str = "") -> None:
    """Records an F08 comment's release run, deferred bug, or retrospective."""
    for pattern, by in ((RELEASE_RUN, "claude"), (TROY_RUN, "troy")):
        match = pattern.match(first)
        if match:
            run, outcome = int(match.group(1)), match.group(2)
            result.runs.append({"by": by, "run": run, "result": outcome})
            commit = _COMMIT.search(body or "")
            if by == "claude" and outcome == "passed" and commit:
                result.commits[run] = commit.group(1)
            if by == "troy" and outcome == "failed":
                rest = (body or "").split("\n", 1)[1] if "\n" in (body or "") else ""
                result.troy_failed[run] = list(dict.fromkeys(
                    m.group(0) for m in SCENARIO_ID.finditer(rest)))
    deferred = DEFERRED.match(first)
    if deferred and int(deferred.group(1)) not in result.deferred:
        result.deferred.append(int(deferred.group(1)))
    retro = RETROSPECTIVE.match(first)
    if retro:
        result.retrospectives.append(retro.group(1))


def _gh(repo: Repo, *args: str):
    """Runs one read-only gh command and returns its JSON output.

    Raises:
        FlowError: gh is missing, fails, or prints something that is not JSON.
    """
    program = shutil.which("gh")
    if program is None:
        raise FlowError("gh is not on the PATH; troy-mode reads PRs through the GitHub CLI")
    try:
        proc = subprocess.run([program, *args], cwd=repo.root, capture_output=True)
    except OSError as exc:
        raise FlowError(f"cannot run gh: {exc}") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise FlowError(f"gh {' '.join(args[:2])} failed: {err}")
    try:
        return json.loads(proc.stdout.decode("utf-8", "replace") or "null")
    except ValueError as exc:
        raise FlowError(f"gh {' '.join(args[:2])} printed no JSON: {exc}") from exc


def open_prs(repo: Repo) -> list[dict]:
    """Lists the repository's open PRs: number, title, head branch, URL, and creation time."""
    data = _gh(repo, "pr", "list", "--state", "open", "--limit", "100", "--json",
               "number,title,headRefName,url,createdAt")
    if not isinstance(data, list):
        raise FlowError("gh pr list did not print a list")
    return sorted((pr for pr in data if isinstance(pr, dict)), key=lambda pr: pr.get("number", 0))


def timed_comments(repo: Repo, number: int) -> list[tuple[str, str]]:
    """Reads a PR's comments and its reviews that have a body, as (time, body), oldest first.

    A "Comment" review is how a reply from the phone may arrive (F15 design 7, D145).
    The times let attempts from CI be matched to comments (F07 design 8.5).
    """
    data = _gh(repo, "pr", "view", str(number), "--json", "comments,reviews")
    data = data if isinstance(data, dict) else {}
    items = [(str(c.get("createdAt", "")), str(c.get("body", "")))
             for c in data.get("comments") or [] if isinstance(c, dict)]
    items += [(str(r.get("submittedAt", "")), str(r.get("body", "")))
              for r in data.get("reviews") or [] if isinstance(r, dict)
              and str(r.get("body") or "").strip()]
    items.sort(key=lambda item: item[0])
    return items


def comments(repo: Repo, number: int) -> list[str]:
    """Reads the bodies of a PR's comments and of its reviews that have a body, oldest first."""
    return [body for _, body in timed_comments(repo, number)]


def gh_object(repo: Repo, *args: str) -> dict:
    """Runs a read-only gh command whose JSON output is an object."""
    data = _gh(repo, *args)
    if not isinstance(data, dict):
        raise FlowError(f"gh {' '.join(args[:2])} did not print an object")
    return data


def gh_list(repo: Repo, *args: str) -> list[dict]:
    """Runs a read-only gh list command and returns its objects."""
    return _list(repo, *args)


def _list(repo: Repo, *args: str) -> list[dict]:
    """Runs a gh list command and returns its JSON list's objects."""
    data = _gh(repo, *args)
    if not isinstance(data, list):
        raise FlowError(f"gh {' '.join(args[:2])} did not print a list")
    return [item for item in data if isinstance(item, dict)]


def merged_prs(repo: Repo) -> list[dict]:
    """Lists merged PRs with their merge commits, head branches, and times (F08 design 7)."""
    data = _list(repo, "pr", "list", "--state", "merged", "--limit", "200", "--json",
                 "number,title,url,mergeCommit,headRefName,createdAt,mergedAt")
    return sorted(data, key=lambda pr: int(pr.get("number", 0)))


def release_tags(repo: Repo) -> set[str]:
    """Lists the tags of the repository's GitHub releases (F08 design 3.2)."""
    return {str(r.get("tagName")) for r in _list(repo, "release", "list", "--limit", "100",
                                                  "--json", "tagName")}


def open_bugs(repo: Repo) -> list[dict]:
    """Lists the open issues labeled bug: number, title, and URL, by number (F08 D74)."""
    data = _list(repo, "issue", "list", "--label", "bug", "--state", "open", "--limit", "100",
                 "--json", "number,title,url")
    return sorted(({"number": int(i.get("number", 0)), "title": i.get("title"),
                    "url": i.get("url")} for i in data), key=lambda i: i["number"])


def issue(repo: Repo, number: int) -> dict:
    """Reads one issue's number, title, and URL."""
    data = _gh(repo, "issue", "view", str(number), "--json", "number,title,url")
    if not isinstance(data, dict):
        raise FlowError(f"gh issue view {number} did not print an object")
    return data
