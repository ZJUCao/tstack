"""The hooks' local log of refusals and blocks (design section 10).

Each line is one JSON object. It never holds a command line, a message, or
file content: only the program and subcommand words, and paths.
"""

import calendar
import json
import os
import time

from .project import Project

DAY = 24 * 60 * 60
_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# The only words a log line's subcommand may hold. Any other word, which
# could be a secret typed where a subcommand belongs, is written as "?".
_KNOWN = frozenset("""
git gh skill
status diff log show blame grep rev-parse rev-list ls-files ls-tree cat-file merge-base
describe shortlog for-each-ref show-ref name-rev check-ignore check-attr var diff-tree
diff-index diff-files count-objects archive fetch ls-remote version help branch tag remote
config stash worktree reflog restore commit push pull add rm mv reset switch checkout merge
rebase cherry-pick revert am apply clean init clone update-ref symbolic-ref update-index
notes gc prune bisect submodule format-patch filter-branch replace sparse-checkout
maintenance bundle repack fsck mergetool difftool range-diff send-email request-pull
pr issue repo run release search auth api workflow gist label secret variable ssh-key
gpg-key codespace cache project ruleset browse extension alias org attestation
view list checks create edit close reopen comment review ready delete develop lock unlock
pin unpin transfer fork sync rename archive unarchive set-default rerun cancel watch
download upload login logout refresh token setup-git enable disable set get
code-review security-review
""".split())


def log_path(project: Project) -> str:
    """Returns <git dir>/troy-mode/hooks.log."""
    return os.path.join(project.state_dir(), "hooks.log")


def _safe(subcommand: str | None) -> str | None:
    """Keeps only known program and subcommand words, so nothing typed reaches the log."""
    if subcommand is None:
        return None
    return " ".join(word if word in _KNOWN else "?" for word in subcommand.split()[:3])


def write(ctx, rule: str, decision: str, paths=(), subcommand: str | None = None,
          tasks=None) -> None:
    """Appends one line for a refusal or block. A log that cannot be written is skipped.

    Args:
        ctx: The hook call (events.Context).
        rule: The rule name, for example "scope".
        decision: "deny", "block", or "stop".
        paths: Paths for the "scope" and "changes" rules.
        subcommand: The program and subcommand words, for example "git commit".
        tasks: For the "background" rule only, the task IDs a role left running
            (design section 6.1). Never their command text.
    """
    entry = {
        "time": time.strftime(_FORMAT, time.gmtime()),
        "session": ctx.data.get("session_id"),
        "agent_id": ctx.caller.agent_id,
        "agent_type": ctx.caller.agent_type,
        "event": ctx.event,
        "tool": ctx.tool,
        "rule": rule,
        "paths": list(paths),
        "subcommand": _safe(subcommand),
        "decision": decision,
    }
    if tasks is not None:
        entry["tasks"] = [str(task) for task in tasks]
    path = log_path(ctx.project)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def _line_time(line: str) -> float:
    """Reads a log line's time as seconds since the epoch; 0 when unreadable."""
    try:
        return calendar.timegm(time.strptime(json.loads(line)["time"], _FORMAT))
    except (ValueError, KeyError, TypeError):
        return 0.0


def clean(project: Project, log_days: int | None) -> None:
    """Removes role records older than a day and log lines older than log_days days.

    Args:
        project: The troy-mode project.
        log_days: [hooks] log_days from the config at HEAD (design section 10,
            D219), or None when that config is not valid: every line then stays.
    """
    now = time.time()
    _remove_old_records(project, now - DAY)
    if log_days is not None:
        _remove_old_lines(project, now - log_days * DAY)


def _remove_old_records(project: Project, cutoff: float) -> None:
    """Removes the role records last changed before the cutoff."""
    agents = os.path.join(project.state_dir(), "agents")
    for name in os.listdir(agents) if os.path.isdir(agents) else []:
        full = os.path.join(agents, name)
        if os.path.isfile(full) and os.path.getmtime(full) < cutoff:
            os.remove(full)


def _remove_old_lines(project: Project, cutoff: float) -> None:
    """Removes the log lines written before the cutoff, and lines with no readable time."""
    path = log_path(project)
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    kept = [line for line in lines if _line_time(line) >= cutoff]
    if len(kept) != len(lines):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(line + "\n" for line in kept))
