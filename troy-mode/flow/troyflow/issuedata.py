"""Issues as the engine reads them (F15 design 3.3, 5, 6.3, 7, and 8).

troy-mode's own issues are found by the first line of their body: the
progress issue of a feature and the device-test checklist of a version. Every
other open issue with the idea label, or with no label, is one of Troy's
ideas. troy-mode's comments start with a fixed English heading (design 8.4).
"""

import re
from dataclasses import dataclass, field

from . import github, notes
from .errors import FlowError
from .repo import Repo
from .versions import SCENARIO_ID

PROGRESS_MARK = re.compile(r"<!-- troy-mode: progress (F\d{2,3}) -->")
CHECKLIST_MARK = re.compile(r"<!-- troy-mode: device-test (v\d+\.\d+\.\d+) -->")
SCENARIOS_MARK = re.compile(r"<!-- troy-mode: scenarios ([^ ]*) -->")
PROGRESS, CHECKLIST, IDEA = "progress", "device-test", "idea"
_NOT_IDEA = frozenset({"bug", PROGRESS, CHECKLIST})
TURNED_OFF = "issues are turned off"
ISSUE_FIELDS = "number,title,labels,body,comments,url,createdAt,state,stateReason"
PR_FIELDS = "number,title,state,url,createdAt"
_BOX = re.compile(r"^- \[([ xX])\] \*\*(.+?)\*\*")
_RUN = re.compile(r"第 ([1-9][0-9]*) 轮")
_ACCEPT = "我接受 "
# A spot check's box on a checklist: "**抽查 #<n> <title>**" (F18 design 7.1).
_SAMPLE = re.compile(r"^抽查 #([1-9][0-9]*)")


@dataclass
class Issue:
    """One issue as gh lists it.

    Attributes:
        number: The issue number.
        title: The title.
        url: The issue's URL.
        body: The body, with LF line endings.
        labels: The label names.
        open: Whether the issue is open.
        reason: The state reason of a closed issue, such as "NOT_PLANNED", or None.
        comments: The comments' bodies, oldest first.
        comment_items: gh's comment objects, oldest first, with their url and
            createdAt, for the notes on progress issues (F07 design 6.6).
    """

    number: int
    title: str
    url: str
    body: str
    labels: list[str]
    open: bool
    reason: str | None
    comments: list[str] = field(default_factory=list)
    comment_items: list[dict] = field(default_factory=list)

    def mark(self) -> tuple[str, str] | None:
        """Returns ("progress", "F04") or ("device-test", "v0.1.0") from the first line, or None."""
        first = self.body.split("\n", 1)[0].strip()
        for kind, pattern in ((PROGRESS, PROGRESS_MARK), (CHECKLIST, CHECKLIST_MARK)):
            match = pattern.fullmatch(first)
            if match:
                return kind, match.group(1)
        return None

    def is_idea(self) -> bool:
        """Tells whether an issue is one of Troy's ideas (design 5.1)."""
        if not self.open or self.mark() is not None or _NOT_IDEA & set(self.labels):
            return False
        return not self.labels or IDEA in self.labels


@dataclass
class Issues:
    """Every issue the engine read, or why it could not read them.

    Attributes:
        items: The issues, by number.
        error: The gh error when the issues could not be read, else None.
        skipped: True when the repository has issues turned off.
    """

    items: list[Issue] = field(default_factory=list)
    error: str | None = None
    skipped: bool = False

    @property
    def readable(self) -> bool:
        """Tells whether the issues were read."""
        return self.error is None and not self.skipped

    def marked(self, kind: str) -> dict[str, list[Issue]]:
        """troy-mode's issues of one kind by item, each list by number."""
        found: dict[str, list[Issue]] = {}
        for issue in self.items:
            mark = issue.mark()
            if mark and mark[0] == kind:
                found.setdefault(mark[1], []).append(issue)
        return found

    def ideas(self) -> list[Issue]:
        """Troy's open ideas, by number."""
        return [issue for issue in self.items if issue.is_idea()]


def _labels(value) -> list[str]:
    """Reads gh's labels field: a list of objects with a name, or of names."""
    names = []
    for label in value or []:
        name = label.get("name") if isinstance(label, dict) else label
        if isinstance(name, str):
            names.append(name)
    return names


def _comment_items(value) -> list[dict]:
    """Reads gh's comments field as comment objects, oldest first."""
    items = [c for c in value or [] if isinstance(c, dict)]
    items.sort(key=lambda c: str(c.get("createdAt", "")))
    return items


def _comments(value) -> list[str]:
    """Reads gh's comments field as bodies, oldest first."""
    return [str(c.get("body") or "").replace("\r\n", "\n") for c in _comment_items(value)]


def to_issue(data: dict) -> Issue:
    """Builds an Issue from one entry of gh issue list."""
    state = str(data.get("state") or "OPEN").upper()
    reason = data.get("stateReason")
    return Issue(int(data.get("number", 0)), str(data.get("title") or ""),
                 str(data.get("url") or ""), str(data.get("body") or "").replace("\r\n", "\n"),
                 _labels(data.get("labels")), state == "OPEN",
                 str(reason).upper() if reason else None, _comments(data.get("comments")),
                 _comment_items(data.get("comments")))


def turned_off(error: str) -> bool:
    """Tells whether a gh error says the repository has issues turned off."""
    return "disabled issues" in error.lower()


def read_issues(repo: Repo) -> Issues:
    """Reads every issue, open and closed, with one gh call (design 3.3).

    Returns:
        The issues; on a gh failure, an Issues with the error, or skipped when
        the repository has issues turned off.
    """
    try:
        data = github.gh_list(repo, "issue", "list", "--state", "all", "--limit", "300",
                              "--json", ISSUE_FIELDS)
    except FlowError as exc:
        if turned_off(str(exc)):
            return Issues(skipped=True)
        return Issues(error=str(exc))
    items = sorted((to_issue(item) for item in data), key=lambda issue: issue.number)
    return Issues(items)


def read_prs(repo: Repo) -> list[dict]:
    """Reads every PR, open, merged, and closed, with one gh call, by number."""
    data = github.gh_list(repo, "pr", "list", "--state", "all", "--limit", "300",
                          "--json", PR_FIELDS)
    return sorted(data, key=lambda pr: int(pr.get("number", 0)))


def by_troy_mode(body: str) -> bool:
    """Tells whether a comment on an issue starts with one of troy-mode's headings (8.4)."""
    return github.is_f07(body)


def troy_since(comments: list[str]) -> list[str]:
    """Troy's comments after troy-mode's last comment, oldest first; all when it never wrote.

    A note for a later feature is neither (F07 design 6.6, F15 design 3.3).
    """
    found: list[str] = []
    for body in comments:
        if notes.is_note(body):
            continue
        found = [] if by_troy_mode(body) else found + [body]
    return found


def is_new(issue: Issue) -> bool:
    """Tells whether an idea waits for troy-mode: no heading comment, or Troy wrote since."""
    if not any(by_troy_mode(body) for body in issue.comments):
        return True
    return bool(troy_since(issue.comments))


def repo_url(url: str) -> str | None:
    """Takes https://github.com/o/r from an issue's or a PR's URL, or None."""
    match = re.match(r"^(https?://[^/]+/[^/]+/[^/]+)/(?:issues|pull)/\d+", url or "")
    return match.group(1) if match else None


@dataclass
class Ticks:
    """What a checklist's body says (design 6.2 and 6.3).

    Attributes:
        scenarios: Each scenario box's ID and whether it is ticked, in body order.
        accept: Whether the accept box is ticked.
        run: The run number in the Chinese header, or None.
        named: The scenario list of a patch release's marker line, or None.
        samples: Each spot check box's PR number and whether it is ticked, in
            body order (F18 design 7.1).
    """

    scenarios: dict[str, bool] = field(default_factory=dict)
    accept: bool = False
    run: int | None = None
    named: list[str] | None = None
    samples: dict[int, bool] = field(default_factory=dict)


def read_ticks(body: str) -> Ticks:
    """Reads a checklist's boxes, run, and patch scenario list."""
    ticks = Ticks()
    english = body.find("<details>")
    for line in (body[:english] if english >= 0 else body).split("\n"):
        stripped = line.strip()
        marker = SCENARIOS_MARK.fullmatch(stripped)
        if marker:
            ticks.named = [s for s in marker.group(1).split(",") if s]
            continue
        if ticks.run is None and stripped.startswith("**"):
            run = _RUN.search(stripped)
            ticks.run = int(run.group(1)) if run else None
        box = _BOX.match(stripped)
        if not box:
            continue
        ticked, text = box.group(1) in "xX", box.group(2)
        if text.startswith(_ACCEPT):
            ticks.accept = ticked
            continue
        sample = _SAMPLE.match(text)
        if sample:
            ticks.samples[int(sample.group(1))] = ticked
            continue
        sid = text.split(" ", 1)[0]
        if SCENARIO_ID.fullmatch(sid):
            ticks.scenarios[sid] = ticked
    return ticks


def device_result(ticks: Ticks) -> str:
    """waiting, ticked, or incomplete (design 3.3); every spot check box counts (F18 7.1)."""
    every = all(ticks.scenarios.values()) and all(ticks.samples.values())
    if ticks.accept and every:
        return "ticked"
    if ticks.accept:
        return "incomplete"
    return "waiting"
