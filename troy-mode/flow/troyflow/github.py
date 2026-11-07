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
    """

    reviews: list[dict] = field(default_factory=list)
    rounds: int = 0
    attempts: int = 0
    troy: list[str] = field(default_factory=list)
    last: str | None = None
    waiting: bool = False
    escalated: bool = False


def heading(body: str) -> str:
    """Returns a comment's first line, trimmed."""
    lines = (body or "").strip().split("\n")
    return lines[0].strip() if lines else ""


def is_f07(body: str) -> bool:
    """Tells whether a comment starts with one of F07's fixed headings (design 8.4)."""
    first = heading(body)
    return any(p.match(first) for p in (REVIEW, ATTEMPT, ESCALATION, WAITING))


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
    last = result.last or ""
    result.escalated = not result.troy and bool(ESCALATION.match(last))
    result.waiting = not result.troy and bool(ESCALATION.match(last) or WAITING.match(last))
    return result


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
