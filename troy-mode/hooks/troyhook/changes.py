"""Changes a role makes through the shell or a skill (design section 6, D41).

A role's starting state is a snapshot of git status with content hashes, kept
in its record (records.py). After each shell or skill call, and when the role
stops, the hook takes the same snapshot and reports changed paths outside the
role's write scope.
"""

from . import gitstate, records
from .scopes import Caller, describe
from .writes import allows


def record_path(ctx) -> str:
    """Returns the file that holds the calling role's record."""
    return records.path_of(ctx.project.state_dir(), ctx.caller.agent_id)


def read_record(ctx) -> dict | None:
    """Reads the calling role's record, or None when there is none.

    Raises:
        ValueError: The record is not a JSON object.
    """
    return records.read(record_path(ctx))


def write_record(ctx) -> dict:
    """Records the calling role's starting state and returns the record.

    Raises:
        GitError: git status fails.
        OSError: The record cannot be written.
    """
    record = _fresh(ctx)
    records.save(record_path(ctx), record)
    return record


def _fresh(ctx) -> dict:
    """Builds the calling role's record from its checkout's state now."""
    team = getattr(ctx, "team", None)
    return records.fresh(ctx.caller.agent_id, ctx.caller.agent_type, ctx.data.get("session_id"),
                         gitstate.snapshot(ctx.project), (team.id, team.root) if team else None)


def ensure_record(ctx) -> dict:
    """Returns the role's record, made now when SubagentStart made none.

    Two calls of one role may make it at once, so it is made under the
    record's lock (F20 design 3.3).
    """
    return read_record(ctx) or records.update(record_path(ctx),
                                              lambda found: None if found else _fresh(ctx)) \
        or read_record(ctx)



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
    record = read_record(ctx)
    if record is None:
        write_record(ctx)
        return []
    start = record["paths"]
    now = gitstate.snapshot(ctx.project)
    changed = sorted(p for p in set(start) | set(now)
                     if p not in start or p not in now or start[p][1] != now[p][1])
    if not changed:
        return []
    paths, scope = ctx.config().paths, ctx.caller.scope()
    team = getattr(ctx, "team", None) is not None
    return [(p, _way_back(p, start, now)) for p in changed
            if not allows(scope, p, paths, team)[0]]


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
