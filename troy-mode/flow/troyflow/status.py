"""The status command: the state, the next action, and the progress file (F07 design 5).

F08 adds the versions, the release state, and the release's next actions
(F08 design 3.2 and 3.3). F09 adds the P rules and the cleanup action (F09
design 3.2). F15 adds the issues part and the ideas action (F15 design 3.3).
F07 D261 to D263 count each open PR's attempts from its CI runs too (ci.py).
"""

from . import github, issuesync, nextstep, notecmd, progress, releases, teamstate
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
    "all-accepted": "Every feature is accepted and every version is released.",
    "teams": "Go on with each team's next action (teams).",
}
_STEPS = {
    "version-tests": "start TE5 for the version tests: {title}.",
    "release-pr": "open {title} with the changelog section (PM4).",
    "security-review": "make the review branch {branch}, run CR2's security review there, and "
                       "post its report on PR #{pr}.",
    "release-test": "run the release test on Troy's PC and post its report on PR #{pr}.",
    "troy-test": "Troy tests the version on Troy's devices and accepts it (PR #{pr}).",
    "accept": "Troy accepted. Set the statuses (PM4), run accept-version, and merge PR #{pr}.",
    "bugs": "fix bug {item} through the bug flow, then run the release test again.",
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
    if action == "bug":
        return f"Open PR B of {entry['item']} with DV3: {entry['title']}."
    if action == "version-test-plan":
        return f"Start TM7 for the {entry['item']} test plan: {entry['title']}."
    if action == "release" and entry["step"] == "troy-test" and entry.get("issue"):
        return (f"Release {entry['tag']}: Troy tests the version on Troy's devices with "
                f"checklist #{entry['issue']} and accepts it (PR #{entry['pr']}).")
    if action == "release":
        return f"Release {entry['tag']}: " + _STEPS[entry["step"]].format(**entry)
    if action == "ideas":
        return ("Take in Troy's new ideas as the Product Manager (PM6): "
                + ", ".join(f"#{n}" for n in entry["ideas"] or []) + ".")
    if action == "record-acceptance":
        return f"Record Troy's acceptance of {entry['tag']} in {entry['title']}."
    if action == "tag":
        return f"Create the GitHub release {entry['tag']} on {entry['commit']}."
    if action == "retro":
        return (f"Run the retrospective of {entry['tag']} and post it on PR #{entry['pr']} "
                "(retro).")
    if action == "cleanup":
        return (f"Clean up {entry['item']}: fix the files its baseline lines name, at most 5 a "
                f"PR, in [refactor] Apply {entry['item']} to <area> (DV5) or "
                f"[{entry['item']} test-fix] Apply {entry['item']} to tests (TE6).")
    if action == "plan":
        return (f"Run AR7 to plan the batch ({', '.join(entry['items'])}), then keep its plan "
                "with plan --report.")
    if action == "team-start":
        return f"Start a team for each of {', '.join(entry['items'])} with team start."
    if action == "team-end":
        return f"{entry['item']} is accepted: run team end --item {entry['item']}."
    if action == "rework":
        text = (f"{entry['item']} needs rework after a requirement change: run AR4, then redo "
                "the earliest stage it names.")
        if entry.get("pr"):
            text += (f" PR #{entry['pr']} was opened before the change: close it unmerged when "
                     "that stage is at or before its own, else rebase it.")
        return text
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
    if entry["action"] == "rework":
        return f"{stage} of 6. Needs rework after a requirement change."
    if stage is None:
        if entry["action"] == "continue-pr":
            return f"none. PR #{entry['pr']} is open."
        if entry["action"] in ("bug", "version-test-plan", "release", "record-acceptance",
                               "tag", "retro", "cleanup", "ideas"):
            return f"none. {action_text(entry)}"
        return f"setup. {action_text(entry)}"
    text = f"{stage} of 6. {stage_name(stage).capitalize()}"
    pr = next((p for p in prs if p["number"] == entry.get("pr")), None)
    if pr is None:
        return f"{text}, no PR yet."
    last = pr["reviews"][-1] if pr["reviews"] else None
    review = f" {last['role']} review, round {last['round']}: {last['result']}." if last else ""
    return f"{text} PR #{pr['number']} is open.{review}"


def build_view(state: State, entry: dict, prs: list[dict], waiting: str | None,
               part: dict | None = None) -> View:
    """Builds the progress file's fields from the state and the next action."""
    feature = _current_feature(state, entry)
    version = "None"
    if feature and feature.version:
        same = [f.id for f in state.features or [] if f.version == feature.version]
        version = f"{feature.version} ({', '.join(same)})"
    elif entry.get("item") in state.versions:
        version = f"{entry['item']} ({', '.join(state.versions[entry['item']])})"
    open_prs = "; ".join(f"#{p['number']} {p['title']} ({p['url']})" for p in prs) or "None"
    view = View({
        "Current version": version,
        "Current feature": f"{feature.id} {feature.name}" if feature else "None",
        "Stage": _stage_text(entry, prs),
        "Open PRs": open_prs,
        "Waiting on Troy": waiting or "Nothing",
        "Next action": action_text(entry),
    })
    if part and part["mode"]:
        _team_view(state, view, part)
    return view


def _team_view(state: State, view: View, part: dict) -> None:
    """Adds the teams block of Prototype E to the progress file (F20 design 3.12)."""
    view.values["Teams"] = str(len(part["teams"]))
    for team in part["teams"]:
        feature = state.feature(team["id"])
        name = f"{team['id']} {feature.name}" if feature else team["id"]
        stage = "accepted" if team["stage"] is None else f"stage {team['stage']} of 6"
        view.teams.append(f"{name}: {stage}. {action_text(team['next'])}")
    if part["may_start"]:
        view.values["May start"] = ", ".join(part["may_start"])
    if part["needs_plan"]:
        view.values["Needs a plan"] = ", ".join(part["needs_plan"])


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


def _progress(args, state: State, entry: dict, prs: list[dict], report: dict,
              part: dict) -> None:
    """Rebuilds or rewrites the progress file when it is due (design 5.2)."""
    view = build_view(state, entry, prs, None, part)
    old = progress.read(state.repo.root) if state.marker else None
    carried = old if old is not None and progress.same_work(old, view) else None
    notes = (carried.notes if carried else []) + list(args.note or [])
    attempts = max([github.attempt_number(n) for n in notes] + [0])
    entry["attempts"] = max(entry["attempts"], attempts)
    waiting = _waiting(args, state, entry, carried)
    report["waiting_on_troy"] = waiting
    view = build_view(state, entry, prs, waiting, part)
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
    state = read_state(args.repo, with_ci=True)
    if state.repo is not None and state.origin:
        issuesync.load(state)
    part = teamstate.compute(state)
    if part["mode"]:
        entry, notes = nextstep.decide(teamstate.without_teams(state, part))
        entry = teamstate.home_next(entry, part, state)
    else:
        entry, notes = nextstep.decide(state)
    notes.extend(state.notes)
    prs = [pr_entry(state, pr) for pr in state.prs]
    report = {
        "command": "status", "ok": True, "notes": notes, "problems": [],
        "repo": str(state.repo.root) if state.repo else None, "branch": state.branch,
        "project": _project(state), "checks": state.checks,
        "troy_approves_first": state.approves_first, "order": state.order or [],
        "order_problems": state.order_problems,
        "features": [feature_entry(state, f) for f in state.features or []],
        "next_feature": next_feature(state), "open_prs": prs, "bugs": state.bugs,
        "rules": state.rules,
        "versions": releases.version_entries(state) if state.origin else [],
        "release": releases.release_entry(state) if state.origin else None,
        "issues": issuesync.status_part(state),
        "waiting_on_troy": None,
        "next": entry, "progress": {"path": progress.PATH, "written": False, "rebuilt": False},
        "teams": part["teams"], "may_start": part["may_start"],
        "needs_plan": part["needs_plan"], "waiting": part["waiting"],
    }
    if report["release"] is not None and entry.get("step") == "release-test":
        report["release"]["checks"] = releases.release_checks(state, entry["title"], notes)
    report["feature_notes"] = notecmd.feature_notes(state, notes)
    if report["release"] is not None and entry.get("step") == "security-review":
        found = releases.target(state)
        report["release"]["review"] = releases.review_entry(state, found[0], found[1])
    if state.installed and report["issues"]["template"] is False:
        notes.append(f"{issuesync.IDEA_TEMPLATE} is missing on origin/main: 'upgrade "
                     "troy-mode' brings it. Until then an issue with no label is an idea.")
    if state.checks["outdated"]:
        notes.append("The project's troy-check differs from the plugin's. troy-init's upgrade "
                     "brings it up to date; [roles], [flow], and troy-check code --worktree "
                     "need it.")
    if state.repo is not None:
        _progress(args, state, entry, prs, report, part)
    return report, 0
