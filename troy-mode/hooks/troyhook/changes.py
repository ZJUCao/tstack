"""Changes a role makes through the shell or a skill (design section 6, D41).

A role's starting state is a snapshot of git status with content hashes. After
each shell or skill call, and when the role stops, the hook takes the same
snapshot and reports changed paths outside the role's write scope.
"""

import json
import os
import re

from . import gitstate
from .project import Project
from .scopes import Caller, describe
from .writes import allows


def record_path(project: Project, agent_id: str) -> str:
    """Returns the file that holds a role's starting state."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", agent_id)
    return os.path.join(project.state_dir(), "agents", f"{safe}.json")


def write_record(project: Project, caller: Caller) -> dict:
    """Records a role's starting state and returns the snapshot.

    Raises:
        GitError: git status fails.
        OSError: The record cannot be written.
    """
    snap = gitstate.snapshot(project)
    path = record_path(project, caller.agent_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"agent_type": caller.agent_type, "paths": snap}, handle)
    return snap


def ensure_record(project: Project, caller: Caller) -> None:
    """Makes the role's record at its first call when SubagentStart made none."""
    if not os.path.isfile(record_path(project, caller.agent_id)):
        write_record(project, caller)


def _read_record(project: Project, caller: Caller) -> dict | None:
    """Reads a role's starting snapshot, or None when there is no record.

    Raises:
        ValueError: The record is not valid JSON.
    """
    try:
        with open(record_path(project, caller.agent_id), encoding="utf-8") as handle:
            return json.load(handle)["paths"]
    except FileNotFoundError:
        return None


def delete_record(project: Project, caller: Caller) -> None:
    """Deletes a role's record when the role stops."""
    try:
        os.remove(record_path(project, caller.agent_id))
    except FileNotFoundError:
        pass


def _way_back(path: str, start: dict, now: dict) -> str:
    """Says how a role undoes its change to one path."""
    if path in start:
        return "it was already changed before you started; undo only your own edit to it"
    if path in now and now[path][0] == "??":
        return "you created it; delete it"
    return f"undo it with `git restore -- {path}`"


def out_of_scope(ctx) -> list[tuple[str, str]]:
    """Lists the role's changes outside its write scope since it started.

    A path is changed when it is new in the snapshot, has left it, or has a
    different hash. When the record is missing, it is made now and nothing
    is reported.

    Args:
        ctx: The hook call (events.Context).

    Returns:
        Pairs of repository path and how to undo the change, sorted by path.
    """
    project, caller = ctx.project, ctx.caller
    start = _read_record(project, caller)
    if start is None:
        write_record(project, caller)
        return []
    now = gitstate.snapshot(project)
    changed = sorted(p for p in set(start) | set(now)
                     if p not in start or p not in now or start[p][1] != now[p][1])
    if not changed:
        return []
    paths, scope = ctx.config().paths, caller.scope()
    return [(p, _way_back(p, start, now)) for p in changed if not allows(scope, p, paths)[0]]


def reason(left: list[tuple[str, str]], caller: Caller, at_stop: bool) -> str:
    """Words the block for changes outside the scope, with the way back for each."""
    scope = describe(caller.scope())
    if at_stop:
        head = f"You are stopping with files changed outside your write scope ({scope}):"
        tail = "Undo these changes, then finish your report."
    else:
        head = f"Your last call changed files outside your write scope ({scope}):"
        tail = "The call has already run. Undo these changes before you go on."
    lines = [f"- {path}: {way}" for path, way in left]
    return "\n".join([head, *lines, tail + " If the task needs them, report `needs-answer`."])
