"""Write scopes for Edit, Write, and NotebookEdit (design section 5)."""

from troycheck.classify import classify
from troycheck.globs import matches_any

from . import gitstate
from .verdict import Refusal
from .paths import WINDOWS, inside, relative, to_native
from .scopes import describe

NEEDS_ANSWER = "If the task needs this file changed, stop and report `needs-answer`."


def allows(scope: dict, rel: str, paths: dict[str, list[str]]) -> tuple[bool, str]:
    """Tells whether a write scope holds a repository path (design 5.1).

    No role may change a config path, whatever its scope says.

    Args:
        scope: A value of scopes.SCOPES, or scopes.NOTHING.
        rel: The repository path with "/" separators.
        paths: The path classes from the config at HEAD.

    Returns:
        Whether the path is in the scope, and its class.
    """
    cls = classify(rel, paths)
    if cls == "config":
        return False, cls
    return cls in scope["classes"] or matches_any(rel, list(scope["patterns"])), cls


def _in_dot_git(rel: str) -> bool:
    """Tells whether a repository path lies in the .git folder or is the .git file."""
    first = rel.split("/", 1)[0]
    return (first.lower() if WINDOWS else first) == ".git"


def check_write(ctx, raw: str) -> Refusal | None:
    """Checks the path of a subagent's Edit, Write, or NotebookEdit call (design 5.2).

    Args:
        ctx: The hook call (events.Context).
        raw: The tool's path as given.

    Returns:
        A refusal, or None when the path is allowed.
    """
    path = to_native(raw, ctx.cwd)
    project, scope = ctx.project, ctx.caller.scope()
    rel = relative(path, project.root)
    if inside(path, project.git_dir) or (rel is not None and _in_dot_git(rel)):
        shown = rel if rel is not None else path
        return Refusal("scope", f"{shown} is inside the git folder, which no subagent may "
                       f"change. {NEEDS_ANSWER}", paths=(shown,))
    if rel is not None:
        allowed, cls = allows(scope, rel, ctx.config().paths)
        if allowed or gitstate.is_ignored(project, rel):
            return None
        return Refusal("scope", f"{rel} is in the {cls} path class, outside your write scope: "
                       f"{describe(scope)}. {NEEDS_ANSWER}", paths=(rel,))
    if any(inside(path, folder) for folder in ctx.temp_folders()):
        return None
    shown = raw if raw == path else f"{raw} ({path})"
    return Refusal("scope", f"{shown} is outside the repository, the temp folder, and the "
                   f"scratchpad. Your write scope: {describe(scope)}. {NEEDS_ANSWER}",
                   paths=(path,))
