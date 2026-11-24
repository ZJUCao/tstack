"""The engine command `note`, and the notes that `status` and the progress issues show (tstack #67).

`note` renders a note for a later feature as a comment for a progress issue
and gives the `gh issue comment` command; the skill checks the text and
posts it (F07 design 6.6, D284 and D285). `status` lists each feature's
notes and marks a late one (D287), and the target's progress issue counts
them (F15 design 4.2). This module is not imported by brief.
"""

import secrets
import shlex
from pathlib import Path

from troycheck.titles import parse_title

from . import issuedata, notes
from . import repo as git
from .errors import FlowError
from .repo import MAIN
from .requirements import parse_features, parse_order
from .stages import feature_stage, merged_stages, plain

# Under <git dir>/troy-mode, which repo.state_dir() gives.
NOTES_FOLDER = "flow/notes"


def _issue_of(found: dict[str, list[issuedata.Issue]], fid: str | None) -> int | None:
    """A feature's progress issue: its open one, else its newest closed one."""
    group = found.get(fid or "", [])
    opened = [i for i in group if i.open]
    if opened:
        return opened[0].number
    return group[-1].number if group else None


def _source_feature(prs: list[dict], source: str) -> str | None:
    """The feature that a "#<n>, ..." source's PR is about, from its title, or None."""
    head = source.split(",", 1)[0].strip()
    if not head.startswith("#") or not head[1:].isdigit():
        return None
    pr = next((p for p in prs if int(p.get("number", 0)) == int(head[1:])), None)
    if pr is None:
        return None
    title = plain(str(pr.get("title") or ""))
    stage = feature_stage(title)
    if stage:
        return stage[0]
    parsed = parse_title(title)
    return parsed.id if parsed and parsed.id and parsed.id.startswith("F") else None


def _next_feature(order: list[str], merged: dict[str, set[int]]) -> str | None:
    """The first feature of the order whose accept stage has not merged."""
    return next((fid for fid in order if 6 not in merged.get(fid, set())), None)


def run_note(args) -> tuple[dict, int]:
    """Renders a note for a later feature (design 6.6).

    Args:
        args: Parsed options: for_id, source, file, and repo.

    Returns:
        The report and the exit code: 0, or 1 when a problem stops it.

    Raises:
        FlowError: Not a repository, an unreadable file, or gh failing.
    """
    repo = git.need_repo(args.repo)
    report = {"command": "note", "ok": False, "notes": [], "problems": [],
              "target": args.for_id, "source": (args.source or "").strip()}
    try:
        text = Path(args.file).read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise FlowError(f"cannot read {args.file}: {exc}") from exc
    source = report["source"]
    if not source or "\n" in source:
        report["problems"].append("--from must be one line that says where the note comes from, "
                                  "such as \"#57, Code Reviewer, round 1\" or \"Troy, in chat\".")
    if not text:
        report["problems"].append(f"{args.file} holds no text for the note.")
    requirements = git.read(repo, MAIN, "docs/requirements.md")
    features = parse_features(requirements) or []
    ids = [f.id for f in features]
    merged = merged_stages([s for _, s in git.log(repo, MAIN)]) if git.commit_of(repo, MAIN) \
        else {}
    if args.for_id not in ids:
        report["problems"].append(f"{args.for_id} is not in the features table of "
                                  "docs/requirements.md on origin/main.")
    elif 6 in merged.get(args.for_id, set()):
        report["problems"].append(f"{args.for_id} is accepted: a change to an accepted feature is "
                                  "a requirement change that becomes a new feature (F07 D65), "
                                  "not a note.")
    if report["problems"]:
        return report, 1
    issues = issuedata.read_issues(repo)
    if issues.skipped:
        report["problems"].append("The repository has issues turned off, so no progress issue "
                                  "can hold the note.")
        return report, 1
    if issues.error:
        raise FlowError(f"cannot read the issues: {issues.error}")
    found = issues.marked(issuedata.PROGRESS)
    prs = issuedata.read_prs(repo)
    order = parse_order(requirements) or ids
    candidates = [_source_feature(prs, source), args.for_id, _next_feature(order, merged)]
    number = next((n for n in (_issue_of(found, c) for c in candidates if c) if n), None)
    if number is None:
        report["problems"].append("No progress issue can hold the note: the source feature, "
                                  f"{args.for_id}, and the next feature have none yet. Run the "
                                  "issue sync first.")
        return report, 1
    folder = repo.state_dir() / NOTES_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"note-{args.for_id}-{secrets.token_hex(4)}.md"
    path.write_text(f"Note for {args.for_id}, from {source}\n\n{text}\n", encoding="utf-8",
                    newline="\n")
    report.update(ok=True, issue=number, file=str(path),
                  gh=f"gh issue comment {number} --body-file {shlex.quote(str(path))}")
    return report, 0


# --------------------------------------------------------------------------- status and issues


def all_notes(issues) -> list[notes.Note]:
    """Every note on the progress issues that the engine read, oldest first."""
    if issues is None or not issues.readable:
        return []
    return notes.collect((i.number, i.body, i.comment_items) for i in issues.items)


def _opened(prs: list[dict], fid: str, stage: int) -> str | None:
    """When the feature's PR of a stage first opened: the earliest createdAt, or None."""
    times = [str(p.get("createdAt") or "") for p in prs
             if feature_stage(plain(str(p.get("title") or ""))) == (fid, stage)]
    times = [t for t in times if t]
    return min(times) if times else None


def feature_notes(state, messages: list[str]) -> list[dict]:
    """status's feature_notes: each feature's notes and what each may have missed (D287).

    Args:
        state: The project's state, with its issues and every PR read.
        messages: The report's notes; a line is added for each late note.
    """
    found = all_notes(state.issues)
    if not found:
        return []
    prs = state.all_prs or []
    order = [f.id for f in state.features or []]
    entries = []
    for fid in order:
        mine = notes.for_feature(found, fid)
        if not mine or 6 in state.merged.get(fid, set()):
            continue
        design, impl = _opened(prs, fid, 1), _opened(prs, fid, 5)
        items = []
        for note in mine:
            late = []
            if design and note.created > design:
                late.append("design")
            if impl and note.created > impl:
                late.append("implementation")
            items.append({"issue": note.issue, "url": note.url, "source": note.source,
                          "created": note.created, "late": late})
            if late:
                parts = " and the ".join(late)
                messages.append(f"The note for {fid} from {note.source} came after {fid}'s "
                                f"{'PR 5' if len(late) == 2 else 'PR 1'} opened, so the "
                                f"{parts} may not hold it: decide what it needs "
                                f"({note.url}).")
        entries.append({"id": fid, "notes": items})
    return entries


def progress_line(issues, fid: str) -> tuple[str, str] | None:
    """The progress issue's notes line, Chinese and English, or None without notes (F15 4.2)."""
    mine = notes.for_feature(all_notes(issues), fid)
    if not mine:
        return None
    links = [f"[#{note.issue}]({note.url})" for note in mine]
    return (f"备注：{len(mine)} 条（{'、'.join(links)}）",
            f"Notes from earlier work: {len(mine)} ({', '.join(links)})")
