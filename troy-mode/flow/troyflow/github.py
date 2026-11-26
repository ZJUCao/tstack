"""Open PRs and F07's comments on them, read through gh (F07 design 5.1 and 8.4).

F15 adds the headings troy-mode writes on issues, Troy's PR reviews, and the
generic list and object reads its issue module uses (F15 design 3.3 and 8.4).
F18 adds a wait's ID, the rulings at a review loop's round 3, and Troy's
overturns (F18 design 4.2 and 5.3).

The engine only reads GitHub. Every call here is read-only.
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field

from . import notes, waits
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
# CR2's report on a release PR (F08 design 5.9).
SECURITY = re.compile(r"^Security review, run ([1-9][0-9]*): (approved|changes-requested)$")
# troy-mode's headings on issues (F15 design 8.4).
IDEA = re.compile(r"^Idea: (requirement change|bug|rule|answered|later|in the requirements)")
REPLY = re.compile(r"^Reply to Troy")
DEVICE_RUN = re.compile(r"^Device test, run ([1-9][0-9]*): ready$")
# F18's headings: a ruling at a review loop's round 3 on a PR, and Troy's
# overturn of one on a progress issue, with its end (F18 design 5.3, D174).
RULING = re.compile(r"^(Architect|Product Manager) ruling, round ([1-9][0-9]*): "
                    r"(merge|fix|fixed|not fixed)$")
RULING_LINE = re.compile(r"^\s*(\d+)\.\s+(fix|does not block|fixed|not fixed):\s*(.+?)\s*$")
OVERTURN = re.compile(r"^Overturn: (\S.*)$")
OVERTURN_DONE = re.compile(r"^Overturn carried out: (\S.*)$")
RULER_TASK = {"Architect": "AR8", "Product Manager": "PM7"}
_COMMIT = re.compile(r"^Commit tested: ([0-9a-f]{7,40})\s*$", re.M)
_OWN = (REVIEW, ATTEMPT, ESCALATION, WAITING, RELEASE_RUN, TROY_RUN, RETROSPECTIVE, DEFERRED,
        SECURITY, IDEA, REPLY, DEVICE_RUN, RULING, OVERTURN_DONE, OVERTURN)


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
        security: The security reviews, oldest first: run and result (F08 design 5.9).
        wait: The wait ID of F07's last comment while it waits or escalates,
            "unlisted" without a listed one, else None (F18 D171).
        rulings: Every ruling, oldest first: ruler, round, result, and findings (D174).
        ruling_urls: Each ruling comment's URL, in the same order, when known.
        ruling: The ruling of a loop whose round 3 requested changes: ruler, task,
            and the newest result after that round, None before one is posted
            (F18 design 5.1). None for any other loop.
        escalated_since_attempt: An escalation comes after the newest attempt comment.
        escalated_since_ruling: An escalation comes after the newest ruling.
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
    security: list[dict] = field(default_factory=list)
    wait: str | None = None
    rulings: list[dict] = field(default_factory=list)
    ruling_urls: list[str | None] = field(default_factory=list)
    ruling: dict | None = None
    escalated_since_attempt: bool = False
    escalated_since_ruling: bool = False


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


def read_ruling(body: str) -> dict | None:
    """Reads a ruling comment: ruler, round, result, and each finding's verdict (D174)."""
    found = RULING.match(heading(body))
    if not found:
        return None
    findings = []
    for line in (body or "").replace("\r\n", "\n").split("\n")[1:]:
        item = RULING_LINE.match(line)
        if item:
            findings.append({"number": int(item.group(1)), "verdict": item.group(2),
                             "reason": item.group(3)})
    return {"ruler": found.group(1), "round": int(found.group(2)), "result": found.group(3),
            "findings": findings}


def read_comments(bodies: list[str], urls: list[str | None] | None = None) -> Comments:
    """Counts rounds and attempts, and finds what waits on Troy, from a PR's comments.

    Args:
        bodies: The comments' bodies, oldest first.
        urls: Each comment's URL, in the same order, when known.

    Returns:
        What the comments say. Troy's comments never count as rounds or
        attempts, and neither does a ruling.
    """
    result = Comments()
    marks = {"review": {}, "attempt": -1, "escalation": -1, "ruling": []}
    for index, body in enumerate(bodies):
        first = heading(body)
        if notes.is_note(body):
            continue
        if not is_f07(body):
            result.troy.append(body)
            continue
        result.troy, result.last = [], first
        result.wait = waits.wait_of(body)
        review = REVIEW.match(first)
        if review:
            result.reviews.append({"role": review.group(1), "round": int(review.group(2)),
                                   "result": review.group(3)})
            result.rounds = max(result.rounds, int(review.group(2)))
            marks["review"][int(review.group(2))] = index
        if attempt_number(first):
            marks["attempt"] = index
        if ESCALATION.match(first):
            marks["escalation"] = index
        ruling = read_ruling(body)
        if ruling:
            result.rulings.append(ruling)
            result.ruling_urls.append(urls[index] if urls and index < len(urls) else None)
            marks["ruling"].append((index, ruling))
        result.attempts = max(result.attempts, attempt_number(first))
        _read_release(result, first, body)
    last = result.last or ""
    result.escalated = not result.troy and bool(ESCALATION.match(last))
    result.waiting = not result.troy and bool(ESCALATION.match(last) or WAITING.match(last))
    if not result.waiting:
        result.wait = None
    result.escalated_since_attempt = marks["escalation"] > marks["attempt"]
    result.ruling = _round_three(result.reviews, marks)
    if marks["ruling"]:
        result.escalated_since_ruling = marks["escalation"] > marks["ruling"][-1][0]
    return result


def _round_three(reviews: list[dict], marks: dict) -> dict | None:
    """The ruling of a loop whose round 3 or later requested changes, else None (D173).

    The Product Manager rules on the Architect's own review (PM7), the
    Architect on every other loop (AR8). The result is the newest ruling after
    the last review of that round, None while none is posted.
    """
    top = max((review["round"] for review in reviews), default=0)
    asked = [review for review in reviews
             if review["round"] == top and review["result"] == "changes-requested"]
    if top < 3 or not asked:
        return None
    ruler = "Product Manager" if any(r["role"] == "Architect" for r in asked) else "Architect"
    after = [ruling for index, ruling in marks["ruling"] if index > marks["review"][top]]
    return {"ruler": ruler, "task": RULER_TASK[ruler],
            "result": after[-1]["result"] if after else None}


def _read_release(result: Comments, first: str, body: str = "") -> None:
    """Records an F08 comment's release run, deferred bug, security review, or retrospective."""
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
    security = SECURITY.match(first)
    if security:
        result.security.append({"run": int(security.group(1)), "result": security.group(2)})
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


def comment_items(repo: Repo, number: int) -> list[dict]:
    """Reads a PR's comments and its reviews that have a body, oldest first.

    Each item has `time`, `body`, and `url` (None when gh gave none). A
    "Comment" review is how a reply from the phone may arrive (F15 design 7, D145).
    """
    data = _gh(repo, "pr", "view", str(number), "--json", "comments,reviews")
    data = data if isinstance(data, dict) else {}
    items = [{"time": str(c.get("createdAt", "")), "body": str(c.get("body", "")),
              "url": c.get("url") or None}
             for c in data.get("comments") or [] if isinstance(c, dict)]
    items += [{"time": str(r.get("submittedAt", "")), "body": str(r.get("body", "")),
               "url": r.get("url") or None}
              for r in data.get("reviews") or [] if isinstance(r, dict)
              and str(r.get("body") or "").strip()]
    items.sort(key=lambda item: item["time"])
    return items


def timed_comments(repo: Repo, number: int) -> list[tuple[str, str]]:
    """Reads a PR's comments and its reviews that have a body, as (time, body), oldest first.

    The times let attempts from CI be matched to comments (F07 design 8.5).
    """
    return [(item["time"], item["body"]) for item in comment_items(repo, number)]


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
