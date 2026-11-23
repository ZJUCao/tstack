"""Feature teams in status: the teams, what may start, and what waits (F20 design 3.5, 3.8, 3.12).

Teams mode holds when the repository has a team worktree or two or more
features are dependency-ready. Then status lists each team's next action,
the features that may start, those that need the Architect's plan, and the
PRs that wait for Troy, the one that holds up the most features first. The
home checkout's next action leaves the teams' PRs out and starts teams in
place of a feature's stage.
"""

import dataclasses
import os
import re

from troyhook import records

from . import github, teams
from . import plan as batchplan
from .errors import FlowError
from .nextentry import make
from .nextstep import _pr_next
from .rework import is_change
from .stages import AUTHOR_TASK, branch, parse_subject, title

_AFFECTS = re.compile(r"^\s*Affects:\s*(.+?)\s*$", re.M)
_ID = re.compile(r"F\d+")


def worktrees(state) -> list[tuple[str, str, str]]:
    """Lists the team worktrees: ID, real path, and git folder, by ID."""
    found = []
    for path in teams.worktrees(state.repo):
        if path.parent.name == teams.TEAMS_FOLDER and re.fullmatch(r"f\d+", path.name.lower()):
            root = os.path.realpath(path)
            git_dir = teams._git_text(path, "rev-parse", "--absolute-git-dir").strip()
            found.append((path.name.upper(), root, git_dir))
    return sorted(found)


def _accepted(state, fid: str) -> bool:
    """Tells whether a feature's 6/6 is merged."""
    return 6 in state.merged.get(fid, set())


def ready(state) -> list[str]:
    """The dependency-ready features, in the requirements' order."""
    return [f.id for f in state.features or [] if not _accepted(state, f.id)
            and all(_accepted(state, dep) for dep in [*f.hard, *f.soft])]


def affected(state) -> set[str]:
    """The features that an open requirement change's Affects line names (F20 design 3.9)."""
    found = set()
    for pr in state.prs:
        if is_change(str(pr.get("title") or "")):
            for line in _AFFECTS.findall(_body(state, pr)):
                found.update(_ID.findall(line))
    return found


def _body(state, pr: dict) -> str:
    """A PR's description: from its list entry when it has one, else read through gh."""
    if isinstance(pr.get("body"), str):
        return pr["body"]
    try:
        data = github._gh(state.repo, "pr", "view", str(pr.get("number")), "--json", "body")
    except FlowError:
        return ""
    return str(data.get("body") or "") if isinstance(data, dict) else ""


def _met(state, order: dict) -> bool:
    """Tells whether a plan order is met: its feature's stage merged, or the feature accepted."""
    merged = state.merged.get(order["after"], set())
    return order["stage"] in merged or 6 in merged


def orders_met(state, kept: dict | None, fid: str) -> bool:
    """Tells whether every order of the plan on a feature is met."""
    orders = (kept or {}).get("orders") or []
    return all(_met(state, o) for o in orders if o.get("feature") == fid)


def _team_prs(state, fid: str) -> list[dict]:
    """The open PRs whose title's item is the feature, lowest number first."""
    found = []
    for pr in state.prs:
        parsed = parse_subject(str(pr.get("title") or ""))
        if parsed is not None and parsed.id == fid:
            found.append(pr)
    return sorted(found, key=lambda pr: int(pr.get("number", 0)))


def _stage_entry(state, fid: str) -> dict:
    """The next stage of a team's feature, or its team-end once accepted."""
    feature = state.feature(fid)
    stage = state.current(fid)
    if stage is None or feature is None:
        return make("team-end", item=fid)
    stage_title = title(fid, stage, feature.name)
    return make("stage", item=fid, stage=stage, task=AUTHOR_TASK[stage], title=stage_title,
                branch=branch(fid, stage), merged_by=state.merged_by(stage_title))


def _running(git_dir: str) -> list[str]:
    """The agent IDs of the open role records in a team worktree's git folder."""
    return [records.agent_of(os.path.basename(path), record)
            for path, record in records.read_all(os.path.join(git_dir, "troy-mode"))
            if records.is_open(record)]


def team_entry(state, team: tuple[str, str, str], kept: dict | None, changing: set[str]) -> dict:
    """One team's status entry (F20 design 3.12)."""
    fid, root, git_dir = team
    prs = _team_prs(state, fid)
    nxt = _pr_next(state, prs[0]) if prs else _stage_entry(state, fid)
    held = None
    if nxt["action"] == "stage":
        if fid in changing:
            held = "change"
        elif not orders_met(state, kept, fid):
            held = "plan"
    return {"id": fid, "worktree": root, "stage": state.current(fid),
            "pr": int(prs[0]["number"]) if prs else None, "running": _running(git_dir),
            "held": held, "next": nxt}


def _holds(state, fid: str, kept: dict | None) -> list[str]:
    """The features that wait for a feature: by dependency, or by a plan order."""
    found = [f.id for f in state.features or [] if fid in [*f.hard, *f.soft]]
    found += [o["feature"] for o in (kept or {}).get("orders") or []
              if o.get("after") == fid and o["feature"] not in found]
    return found


def waiting(state, kept: dict | None) -> list[dict]:
    """The PRs that wait for Troy, the one that holds up the most features first (Q23)."""
    found = []
    for pr in state.prs:
        if not pr["notes"].waiting:
            continue
        parsed = parse_subject(str(pr.get("title") or ""))
        item = parsed.id if parsed else None
        holds = _holds(state, item, kept) if item else []
        found.append({"pr": int(pr.get("number", 0)), "title": pr.get("title"), "item": item,
                      "url": pr.get("url"), "holds": holds})
    return sorted(found, key=lambda entry: (-len(entry["holds"]), entry["pr"]))


def compute(state) -> dict:
    """The teams part of status; empty lists outside teams mode."""
    empty = {"mode": False, "teams": [], "may_start": [], "needs_plan": [], "waiting": []}
    if state.repo is None or not state.origin:
        return empty
    found = worktrees(state)
    candidates = ready(state)
    if not found and len(candidates) < 2:
        return empty
    kept = batchplan.load(state.repo)
    changing = affected(state)
    ids = {fid for fid, _, _ in found}
    planned = set((kept or {}).get("features", {}))
    # A feature with a merged stage and no team worktree is under way in the home
    # checkout, which goes on with it there.
    free = [fid for fid in candidates if fid not in ids and not state.merged.get(fid)]
    return {"mode": True,
            "teams": [team_entry(state, team, kept, changing) for team in found],
            "may_start": [fid for fid in free if fid in planned and fid not in changing
                          and orders_met(state, kept, fid)],
            "needs_plan": [fid for fid in free if fid not in planned],
            "waiting": waiting(state, kept)}


def without_teams(state, part: dict):
    """A copy of the state without the PRs of the teams' features, for the home's next action."""
    ids = {team["id"] for team in part["teams"]}
    kept = [pr for pr in state.prs
            if (parse_subject(str(pr.get("title") or "")) or _NoItem).id not in ids]
    return dataclasses.replace(state, prs=kept)


class _NoItem:
    """Stands for a title that names no item."""

    id = None


def _home_under_way(state, ids: set[str]) -> dict | None:
    """The next stage of the first feature in the order that is under way in the home checkout."""
    for fid in state.order or []:
        merged = state.merged.get(fid, set())
        if fid not in ids and merged and 6 not in merged:
            return _stage_entry(state, fid)
    return None


def home_next(entry: dict, part: dict, state=None) -> dict:
    """The home checkout's next action in teams mode (F20 design 3.6).

    A team's feature is never the home's work. A feature under way in the home
    checkout (a stage merged, no team worktree) goes on there; a feature not
    started becomes a team's.
    """
    if not part["mode"] or entry.get("action") != "stage":
        return entry
    ids = {team["id"] for team in part["teams"]}
    if entry.get("item") not in ids and entry.get("stage") != 1:
        return entry
    under_way = _home_under_way(state, ids) if state is not None else None
    if under_way is not None:
        return under_way
    if part["needs_plan"]:
        return {**make("plan"), "items": part["needs_plan"]}
    if part["may_start"]:
        return {**make("team-start"), "items": part["may_start"]}
    return make("teams")
