"""Open PRs and F07's comments on them, read through gh (F07 design 5.1 and 8.4).

The engine only reads GitHub. Every call here is read-only.
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field

from .errors import FlowError
from .repo import Repo

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
_OWN = (REVIEW, ATTEMPT, ESCALATION, WAITING, RELEASE_RUN, TROY_RUN, RETROSPECTIVE, DEFERRED)


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
        _read_release(result, first)
    last = result.last or ""
    result.escalated = not result.troy and bool(ESCALATION.match(last))
    result.waiting = not result.troy and bool(ESCALATION.match(last) or WAITING.match(last))
    return result


def _read_release(result: Comments, first: str) -> None:
    """Records an F08 comment's release run, deferred bug, or retrospective."""
    for pattern, by in ((RELEASE_RUN, "claude"), (TROY_RUN, "troy")):
        match = pattern.match(first)
        if match:
            result.runs.append({"by": by, "run": int(match.group(1)), "result": match.group(2)})
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
    """Lists the repository's open PRs: number, title, head branch, and URL, by number."""
    data = _gh(repo, "pr", "list", "--state", "open", "--limit", "100", "--json",
               "number,title,headRefName,url")
    if not isinstance(data, list):
        raise FlowError("gh pr list did not print a list")
    return sorted((pr for pr in data if isinstance(pr, dict)), key=lambda pr: pr.get("number", 0))


def comments(repo: Repo, number: int) -> list[str]:
    """Reads the bodies of a PR's comments, oldest first."""
    data = _gh(repo, "pr", "view", str(number), "--json", "comments")
    items = data.get("comments", []) if isinstance(data, dict) else []
    items = [c for c in items if isinstance(c, dict)]
    items.sort(key=lambda c: str(c.get("createdAt", "")))
    return [str(c.get("body", "")) for c in items]


def _list(repo: Repo, *args: str) -> list[dict]:
    """Runs a gh list command and returns its JSON list's objects."""
    data = _gh(repo, *args)
    if not isinstance(data, list):
        raise FlowError(f"gh {' '.join(args[:2])} did not print a list")
    return [item for item in data if isinstance(item, dict)]


def merged_prs(repo: Repo) -> list[dict]:
    """Lists merged PRs with their merge commits (F08 design 7), by number."""
    data = _list(repo, "pr", "list", "--state", "merged", "--limit", "200", "--json",
                 "number,title,url,mergeCommit")
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
