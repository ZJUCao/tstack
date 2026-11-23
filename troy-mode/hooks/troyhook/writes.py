"""Write scopes for Edit, Write, and NotebookEdit (design section 5)."""

import os

from troycheck.classify import classify
from troycheck.globs import matches_any

from . import gitstate, teams
from .verdict import Refusal
from .paths import WINDOWS, inside, relative, to_native
from .scopes import describe

NEEDS_ANSWER = "If the task needs this file changed, stop and report `needs-answer`."


# Documents that only the main session changes while teams run (F20 design 3.3, D277).
SHARED = ("docs/requirements*.md", "docs/architecture*.md", "docs/adr/**", "docs/versions/**")


def allows(scope: dict, rel: str, paths: dict[str, list[str]],
           team: bool = False) -> tuple[bool, str]:
    """Tells whether a write scope holds a repository path (design 5.1).

    No role may change a config path, whatever its scope says, and a team's
    role no shared document (F20 design D277).

    Args:
        scope: A value of scopes.SCOPES, or scopes.NOTHING.
        rel: The repository path with "/" separators.
        paths: The path classes from the config at HEAD.
        team: The caller is a team's role.

    Returns:
        Whether the path is in the scope, and its class.
    """
    cls = classify(rel, paths)
    if cls == "config" or (team and matches_any(rel, list(SHARED))):
        return False, cls
    return cls in scope["classes"] or matches_any(rel, list(scope["patterns"])), cls


def _in_dot_git(rel: str) -> bool:
    """Tells whether a repository path lies in the .git folder or is the .git file."""
    first = rel.split("/", 1)[0]
    return (first.lower() if WINDOWS else first) == ".git"


def _other_team(ctx, path: str) -> Refusal | None:
    """Refuses a path inside a team's worktree that is not the caller's own (F20 design 3.2)."""
    team = getattr(ctx, "team", None)
    owner = teams.team_at(getattr(ctx, "home", None) or ctx.project, path)
    if owner is None or (team is not None and owner.id == team.id):
        return None
    yours = f" You work in the checkout {team.root}. Write the file there." if team else ""
    return Refusal("scope", f"{path} belongs to team {owner.id}, whose roles work in that "
                   f"checkout.{yours} {NEEDS_ANSWER}", paths=(path,))


def _in_repository(ctx, path: str) -> bool:
    """Tells whether a path lies in the home checkout, the main checkout, or a git folder."""
    home = ctx.home
    common = teams.common_dir(home)
    places = [home.root, common, *teams.git_dirs(home)]
    if os.path.basename(common) == ".git":
        places.append(os.path.dirname(common))
    return any(inside(path, place) for place in places)


def check_write(ctx, raw: str) -> Refusal | None:
    """Checks the path of a subagent's Edit, Write, or NotebookEdit call (design 5.2).

    A team's role writes only in its worktree, and never a shared document
    there (F20 design 3.2, D277). No role writes in another team's worktree.

    Args:
        ctx: The hook call (events.Context).
        raw: The tool's path as given.

    Returns:
        A refusal, or None when the path is allowed.
    """
    path = to_native(raw, ctx.cwd)
    project, scope = ctx.project, ctx.caller.scope()
    team = getattr(ctx, "team", None)
    other = _other_team(ctx, path)
    if other:
        return other
    rel = relative(path, project.root)
    if inside(path, project.git_dir) or (rel is not None and _in_dot_git(rel)):
        shown = rel if rel is not None else path
        return Refusal("scope", f"{shown} is inside the git folder, which no subagent may "
                       f"change. {NEEDS_ANSWER}", paths=(shown,))
    if rel is not None:
        if team is not None and matches_any(rel, list(SHARED)):
            return Refusal("scope", f"{rel} is a shared document, which only the main session "
                           f"changes while teams run (F20 design D277). {NEEDS_ANSWER}",
                           paths=(rel,))
        allowed, cls = allows(scope, rel, ctx.config().paths, team is not None)
        if allowed or gitstate.is_ignored(project, rel):
            return None
        return Refusal("scope", f"{rel} is in the {cls} path class, outside your write scope: "
                       f"{describe(scope)}. {NEEDS_ANSWER}", paths=(rel,))
    if team is not None and _in_repository(ctx, path):
        return Refusal("scope", f"{path} is outside your team's checkout. You work in the "
                       f"checkout {team.root}. Write the file there. {NEEDS_ANSWER}",
                       paths=(path,))
    if any(inside(path, folder) for folder in ctx.temp_folders()):
        return None
    shown = raw if raw == path else f"{raw} ({path})"
    return Refusal("scope", f"{shown} is outside the repository, the temp folder, and the "
                   f"scratchpad. Your write scope: {describe(scope)}. {NEEDS_ANSWER}",
                   paths=(path,))
