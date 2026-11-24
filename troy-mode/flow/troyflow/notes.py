"""Notes for later features: troy-mode's "Note for <ID>" comments on progress issues (tstack #67).

A review often finds what a later feature must take. The main session posts
each such note as a comment on a progress issue, so it lives on GitHub with
the rest of the state (F07 design 6.6, D284), and `brief` adds a feature's
notes to the Input of its IF1, IF2, and DV2 runs (D286). brief imports this
module, which makes it part of F16's instruction set, so it reads GitHub
itself rather than through github.py.
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass

from . import repo as git
from .errors import FlowError

NOTE = re.compile(r"^Note for (F\d{2,3}), from (.+)$")
PROGRESS_MARK = re.compile(r"<!-- troy-mode: progress (F\d{2,3}) -->")
# The tasks whose Input gets the feature's notes, with the sentence that ends them (D286).
SENTENCES = {
    "IF1": "Take each note into the design where it applies, and say in your report which ones "
           "you did not take, and why.",
    "IF2": "Take each note into the design where it applies, and say in your report which ones "
           "you did not take, and why.",
    "DV2": "Where a note differs from the approved design, follow the design and say so in your "
           "report.",
}
_FIELDS = "number,body,comments"
_DISABLED = "disabled issues"


@dataclass(frozen=True)
class Note:
    """One note for a later feature.

    Attributes:
        target: The feature it is for.
        source: Where it comes from, such as "#57, Code Reviewer, round 1".
        text: The note's text, without its heading.
        issue: The number of the progress issue it is on.
        url: The comment's URL.
        created: The comment's createdAt.
        order: Sorts notes oldest first: created, issue, place on the issue.
    """

    target: str
    source: str
    text: str
    issue: int
    url: str
    created: str
    order: tuple


def heading(body: str) -> tuple[str, str] | None:
    """The target and the source of a note's first line, or None when the body is no note."""
    first = (body or "").replace("\r\n", "\n").split("\n", 1)[0].strip()
    found = NOTE.fullmatch(first)
    return (found.group(1), found.group(2).strip()) if found and found.group(2).strip() else None


def is_note(body: str) -> bool:
    """Tells whether a comment is a note for a later feature."""
    return heading(body) is not None


def _text(body: str) -> str:
    """A note's text: the lines after its heading, without blank lines around them."""
    rest = body.replace("\r\n", "\n").split("\n", 1)
    return rest[1].strip("\n").rstrip() if len(rest) > 1 else ""


def is_progress(body: str) -> bool:
    """Tells whether an issue's body starts with a progress issue's mark (F15 design 8.1)."""
    first = (body or "").replace("\r\n", "\n").split("\n", 1)[0].strip()
    return PROGRESS_MARK.fullmatch(first) is not None


def collect(issues) -> list["Note"]:
    """Every note on the progress issues, oldest first.

    Args:
        issues: (number, body, comments) for each issue, where comments are
            gh's comment objects with body, url, and createdAt.
    """
    found = []
    for number, body, comments in issues:
        if not is_progress(body):
            continue
        for place, comment in enumerate(c for c in comments or [] if isinstance(c, dict)):
            text = str(comment.get("body") or "")
            parsed = heading(text)
            if parsed is None:
                continue
            created = str(comment.get("createdAt") or "")
            found.append(Note(parsed[0], parsed[1], _text(text), int(number),
                              str(comment.get("url") or ""), created,
                              (created, int(number), place)))
    return sorted(found, key=lambda note: note.order)


def for_feature(notes: list[Note], fid: str) -> list[Note]:
    """The notes for one feature, oldest first."""
    return [note for note in notes if note.target == fid]


def on_github(repo) -> bool:
    """Tells whether origin's configured URL names GitHub, before any insteadOf rewrite."""
    proc = subprocess.run(["git", "-C", str(repo.root), "config", "--get", "remote.origin.url"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode == 0 and "github.com" in proc.stdout


def read(repo) -> list[Note]:
    """Reads every note with one gh call over the repository's issues.

    Returns:
        The notes, oldest first; none when the repository has issues turned off.

    Raises:
        FlowError: gh is missing or fails, or prints no JSON list.
    """
    program = shutil.which("gh")
    if program is None:
        raise FlowError("gh is not on the PATH")
    try:
        proc = subprocess.run([program, "issue", "list", "--state", "all", "--limit", "300",
                               "--json", _FIELDS], cwd=repo.root, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FlowError(f"cannot run gh: {exc}") from exc
    if proc.returncode != 0:
        error = (proc.stderr or proc.stdout).strip()
        if _DISABLED in error.lower():
            return []
        raise FlowError(f"gh issue list failed: {error}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise FlowError(f"gh issue list printed no JSON: {exc}") from exc
    if not isinstance(data, list):
        raise FlowError("gh issue list did not print a list")
    return collect((item.get("number", 0), item.get("body"), item.get("comments"))
                   for item in data if isinstance(item, dict))


def block(fid: str, task: str, notes: list[Note]) -> str:
    """The notes' part of a brief's Input (F07 design 6.6)."""
    lines = [f"Notes for {fid} from earlier work, kept on its progress issues:"]
    for number, note in enumerate(notes, 1):
        lines.append(f"{number}. From {note.source} ({note.url}):")
        lines += [f"   {line}" if line.strip() else "" for line in note.text.split("\n")]
    lines += ["", SENTENCES[task]]
    return "\n".join(lines)


def brief_input(repo, task: str, fid: str, text: str | None) -> str | None:
    """A brief's Input with the feature's notes added, or the Input as it was.

    Args:
        repo: The checkout the brief is for.
        task: The task ID.
        fid: The feature ID of the brief's item.
        text: The Input file's text, or None.

    Raises:
        FlowError: The notes could not be read from GitHub.
    """
    if task not in SENTENCES or not on_github(repo):
        return text
    try:
        mine = for_feature(read(repo), fid)
    except FlowError as exc:
        raise FlowError(f"the notes of {fid} could not be read from GitHub: {exc}") from exc
    if not mine:
        return text
    notes = block(fid, task, mine)
    return f"{text.rstrip()}\n\n{notes}" if text and text.strip() else notes
