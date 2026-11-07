"""The status command: the state, the next action, and the progress file (F07 design 5)."""

from . import github, nextstep, progress
from .progress import View
from .requirements import approved
from .stages import stage_name
from .state import ARCHITECTURE, REQUIREMENTS, State, feature_entry, next_feature, pr_entry, \
    read_state

_ACTIONS = {
    "setup": "Set up troy-mode with troy-init's engine and merge [rules] Set up troy-mode.",
    "requirements": "Write the requirements as the Product Manager (PM1) and open "
                    "[docs] Add the requirements for Troy's approval.",
    "architecture": "Start the Architect (AR1) and open [docs] Add the architecture for "
                    "Troy's approval.",
    "language": "Run troy-init's language step for the architecture's language.",
    "order-problem": "The topological order breaks a dependency. Fixing it is a requirement "
                     "change; ask Troy.",
    "ask-approvals": "Ask Troy whether to go on approving PR 1 and PR 2 of later features.",
    "all-accepted": "Every feature is accepted. The version release flow (F08) is not built "
                    "yet.",
}


def action_text(entry: dict) -> str:
    """Says the next action in one line, for the progress file and the text report."""
    action = entry["action"]
    if action == "continue-pr":
        return f"Continue PR #{entry['pr']} {entry['title']}."
    if action == "record-approval":
        return f"Record Troy's approval of {entry['doc']} in {entry['title']}."
    if action == "stage":
        return (f"Start {entry['item']} stage {entry['stage']} ({stage_name(entry['stage'])}) "
                f"with {entry['task']}: {entry['title']}.")
    return _ACTIONS[action]


def _current_feature(state: State, entry: dict):
    """Returns the feature the next action is about, or None."""
    if entry.get("item"):
        return state.feature(entry["item"])
    if entry["action"] == "stage":
        return state.feature(next_feature(state))
    return None


def _stage_text(entry: dict, prs: list[dict]) -> str:
    """Builds the Stage line: the stage number first, then what is happening."""
    stage = entry.get("stage")
    if stage is None:
        if entry["action"] == "continue-pr":
            return f"none. PR #{entry['pr']} is open."
        return f"setup. {action_text(entry)}"
    text = f"{stage} of 6. {stage_name(stage).capitalize()}"
    pr = next((p for p in prs if p["number"] == entry.get("pr")), None)
    if pr is None:
        return f"{text}, no PR yet."
    last = pr["reviews"][-1] if pr["reviews"] else None
    review = f" {last['role']} review, round {last['round']}: {last['result']}." if last else ""
    return f"{text} PR #{pr['number']} is open.{review}"


def build_view(state: State, entry: dict, prs: list[dict], waiting: str | None) -> View:
    """Builds the progress file's fields from the state and the next action."""
    feature = _current_feature(state, entry)
    version = "None"
    if feature and feature.version:
        same = [f.id for f in state.features or [] if f.version == feature.version]
        version = f"{feature.version} ({', '.join(same)})"
    open_prs = "; ".join(f"#{p['number']} {p['title']} ({p['url']})" for p in prs) or "None"
    return View({
        "Current version": version,
        "Current feature": f"{feature.id} {feature.name}" if feature else "None",
        "Stage": _stage_text(entry, prs),
        "Open PRs": open_prs,
        "Waiting on Troy": waiting or "Nothing",
        "Next action": action_text(entry),
    })


def _waiting(args, state: State, entry: dict, carried: View | None) -> str | None:
    """Finds what waits on Troy: --waiting, the current PR, or the carried text.

    While the current work has an open PR, its comments alone say whether it
    waits on Troy, so a reply of Troy's on the PR ends the wait.
    """
    if args.waiting is not None:
        return args.waiting or None
    pr = next((p for p in state.prs if p.get("number") == entry.get("pr")), None)
    if pr is not None:
        return f"PR #{entry['pr']}: {pr['notes'].last}" if pr["notes"].waiting else None
    text = carried.values.get("Waiting on Troy") if carried else None
    return text if text and text != "Nothing" else None


def _progress(args, state: State, entry: dict, prs: list[dict], report: dict) -> None:
    """Rebuilds or rewrites the progress file when it is due (design 5.2)."""
    view = build_view(state, entry, prs, None)
    old = progress.read(state.repo.root) if state.marker else None
    carried = old if old is not None and progress.same_work(old, view) else None
    notes = (carried.notes if carried else []) + list(args.note or [])
    attempts = max([github.attempt_number(n) for n in notes] + [0])
    entry["attempts"] = max(entry["attempts"], attempts)
    waiting = _waiting(args, state, entry, carried)
    report["waiting_on_troy"] = waiting
    view = build_view(state, entry, prs, waiting)
    view.notes = notes
    stale = old is None or not progress.is_current(old, view)
    due = args.write_progress or args.waiting is not None or bool(args.note) or stale
    if not state.marker or not due:
        return
    progress.write(state.repo.root, view)
    report["progress"].update(written=True, rebuilt=stale)
    if stale:
        why = "it was missing" if old is None else "it was out of date"
        report["notes"].append(f"Rebuilt {progress.PATH} from git and GitHub: {why}.")


def _doc(state: State, path: str) -> dict:
    """Builds the report's entry for one document on origin/main."""
    version = state.docs.get(path)
    return {"path": path, "version": version, "approved": approved(version)}


def _project(state: State) -> dict:
    """Builds the report's project entry."""
    return {"repository": state.repo is not None, "origin": state.origin,
            "marker": state.marker, "installed": state.installed, "lang": state.lang,
            "requirements": _doc(state, REQUIREMENTS), "architecture": _doc(state, ARCHITECTURE)}


def run_status(args) -> tuple[dict, int]:
    """Reads the state, decides the next action, and keeps the progress file.

    Args:
        args: Parsed options: repo, write_progress, waiting, and note.

    Returns:
        The report and the exit code, 0 whenever the state could be read.
    """
    state = read_state(args.repo)
    entry, notes = nextstep.decide(state)
    prs = [pr_entry(state, pr) for pr in state.prs]
    report = {
        "command": "status", "ok": True, "notes": notes, "problems": [],
        "repo": str(state.repo.root) if state.repo else None, "branch": state.branch,
        "project": _project(state), "checks": state.checks,
        "troy_approves_first": state.approves_first, "order": state.order or [],
        "order_problems": state.order_problems,
        "features": [feature_entry(state, f) for f in state.features or []],
        "next_feature": next_feature(state), "open_prs": prs, "waiting_on_troy": None,
        "next": entry, "progress": {"path": progress.PATH, "written": False, "rebuilt": False},
    }
    if state.checks["outdated"]:
        notes.append("The project's troy-check differs from the plugin's. troy-init's upgrade "
                     "brings it up to date; [roles], [flow], and troy-check code --worktree "
                     "need it.")
    if state.repo is not None:
        _progress(args, state, entry, prs, report)
    return report, 0
