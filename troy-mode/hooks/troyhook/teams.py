"""Feature teams: which checkout a role's call belongs to (F20 design 3.2 and 3.3).

A team works in a linked worktree <home>/.troy-teams/<id>. The Agent tool
cannot start a role there, and a hook's cwd is always the session's folder,
so a role learns its checkout from one sentence of its brief, which the hook
reads from the role's transcript at its first call. The role's record then
lives in the team worktree's git folder and names the team and the worktree.
"""

import json
import os
import re

from . import records
from .paths import WINDOWS, to_native
from .project import Project

TEAMS_FOLDER = ".troy-teams"
SENTENCE = re.compile(r"You work for team (F\d+) in the checkout `([^`]+)`")
_TEAM_FOLDER = re.compile(r"f\d+")
TEAM, HOME, UNKNOWN = "team", "home", "unknown"
UNKNOWN_REASON = ("troy-mode: The hook could not read your brief, so it cannot tell which team's "
                  "checkout you work in, and it refuses calls that change files. Report `failed` "
                  "and say so. (F20 design 3.2)")


def _key(path: str) -> str:
    """Makes a path comparable: absolute, real, and without case on Windows."""
    path = os.path.realpath(os.path.abspath(path))
    return path.lower() if WINDOWS else path


def _first_line(path: str) -> str | None:
    """Reads a small file's first line, or None."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.readline().strip()
    except OSError:
        return None


def common_dir(project: Project) -> str:
    """Returns the git folder the repository's worktrees share."""
    common = _first_line(os.path.join(project.git_dir, "commondir"))
    if not common:
        return project.git_dir
    return os.path.realpath(os.path.join(project.git_dir, common))


def git_dirs(project: Project) -> list[str]:
    """Returns every git folder of the repository: the common one, then each worktree's."""
    common = common_dir(project)
    found = [common]
    base = os.path.join(common, "worktrees")
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        folder = os.path.join(base, name)
        if os.path.isdir(folder):
            found.append(folder)
    return found


def state_dirs(project: Project) -> list[str]:
    """Returns <git folder>/troy-mode for every git folder of the repository."""
    return [os.path.join(folder, "troy-mode") for folder in git_dirs(project)]


class Team:
    """A team's worktree.

    Attributes:
        id: The feature ID, for example "F08".
        root: The worktree's real path.
        git_dir: The worktree's own git folder.
    """

    __slots__ = ("id", "root", "git_dir")

    def __init__(self, team_id: str, root: str, git_dir: str):
        """Stores the team's ID and folders."""
        self.id, self.root, self.git_dir = team_id, root, git_dir

    def project(self) -> Project:
        """Returns the worktree as a project, so every check runs on it."""
        return Project(self.root, self.git_dir)

    def state_dir(self) -> str:
        """Returns the worktree's <git folder>/troy-mode."""
        return os.path.join(self.git_dir, "troy-mode")


def team_worktrees(project: Project) -> list[Team]:
    """Lists the repository's team worktrees, from git's own worktree records.

    A team worktree is a linked worktree whose folder is .troy-teams/<id>,
    with <id> an F ID in lower case.
    """
    found = []
    for folder in git_dirs(project)[1:]:
        dot_git = _first_line(os.path.join(folder, "gitdir"))
        if not dot_git:
            continue
        root = os.path.dirname(os.path.realpath(dot_git))
        name, parent = os.path.basename(root), os.path.basename(os.path.dirname(root))
        if parent == TEAMS_FOLDER and _TEAM_FOLDER.fullmatch(name):
            found.append(Team(name.upper(), root, folder))
    return found


def team_at(project: Project, path: str) -> Team | None:
    """Returns the team worktree that holds a path, or None."""
    key = _key(path)
    for team in team_worktrees(project):
        root = _key(team.root)
        if key == root or key.startswith(root + os.sep):
            return team
    return None


def find_record(project: Project, agent_id: str) -> tuple[str, dict] | None:
    """Finds a role's record in any git folder of the repository.

    Returns:
        The git folder that holds it and the record, or None.
    """
    for folder in git_dirs(project):
        path = records.path_of(os.path.join(folder, "troy-mode"), agent_id)
        try:
            record = records.read(path)
        except (OSError, ValueError):
            continue
        if record is not None:
            return folder, record
    return None


def transcript_path(data: dict) -> str | None:
    """Returns the role's own transcript file, from the hook input (F20 design section 2)."""
    given = data.get("agent_transcript_path")
    if isinstance(given, str) and given:
        return given
    main, session, agent = (data.get(key) for key in ("transcript_path", "session_id", "agent_id"))
    if not all(isinstance(value, str) and value for value in (main, session, agent)):
        return None
    return os.path.join(os.path.dirname(main), session, "subagents", f"agent-{agent}.jsonl")


def _texts(value) -> list[str]:
    """Collects the strings of a decoded JSON value."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _texts(item)]
    if isinstance(value, list):
        return [text for item in value for text in _texts(item)]
    return []


def brief_team(data: dict) -> tuple[str, str] | None:
    """Reads the team sentence from the role's brief, the first line of its transcript.

    Returns:
        The team ID and the checkout the sentence names, or None when the
        brief has no such sentence.

    Raises:
        OSError: The transcript cannot be read.
        ValueError: Its first line is not a JSON object.
    """
    path = transcript_path(data)
    if path is None:
        raise OSError("the hook input names no transcript")
    with open(path, encoding="utf-8") as handle:
        first = json.loads(handle.readline())
    if not isinstance(first, dict):
        raise ValueError("the transcript's first line is not a JSON object")
    for text in _texts(first):
        match = SENTENCE.search(text)
        if match:
            return match.group(1), match.group(2)
    return None


def _valid(project: Project, team_id: str, checkout: str) -> Team | None:
    """Returns the team worktree a brief's sentence names, when it is one of this repository."""
    if not os.path.isabs(checkout):
        return None
    team = next((t for t in team_worktrees(project) if _key(t.root) == _key(checkout)), None)
    return team if team and team.id == team_id else None


def place(ctx) -> str:
    """Moves a role's call to its checkout (F20 design 3.2 and 3.3).

    The role's record decides first, wherever it is; else its brief. A team
    role's call then works on the team's worktree: ctx.project, ctx.cwd, and
    ctx.team change. The home checkout's role keeps the call as it is.

    Returns:
        TEAM, HOME, or UNKNOWN when the brief cannot be read while the
        repository has a team worktree.
    """
    home = ctx.project
    found = find_record(home, ctx.caller.agent_id)
    if found is not None:
        folder, record = found
        worktree = record.get("worktree")
        if isinstance(worktree, str) and worktree:
            _move(ctx, Team(str(record.get("team") or ""), worktree, folder))
            return TEAM
        return HOME
    try:
        named = brief_team(ctx.data)
    except (OSError, ValueError):
        return UNKNOWN if team_worktrees(home) else HOME
    team = _valid(home, *named) if named else None
    if team is None:
        return HOME
    _move(ctx, team)
    return TEAM


def _move(ctx, team: Team) -> None:
    """Points the call at a team's worktree."""
    ctx.home, ctx.team = ctx.project, team
    ctx.project = team.project()
    ctx.cwd = os.path.realpath(team.root)
    ctx.forget()


def open_agents(team: Team) -> list[str]:
    """Lists the agent IDs of a team's open records (F05 design 6.1)."""
    return [records.agent_of(os.path.basename(path), record)
            for path, record in records.read_all(team.state_dir()) if records.is_open(record)]


def busy_team(project: Project, path: str) -> tuple[Team, list[str]] | None:
    """Returns the team worktree that holds a path while one of its records is open."""
    team = team_at(project, path)
    if team is None:
        return None
    agents = open_agents(team)
    return (team, agents) if agents else None


def rooted(command: str, root: str, powershell: bool) -> str | None:
    """Gives a team role's command that starts in its worktree, or None when it already does."""
    if powershell:
        return f"Set-Location -LiteralPath '{root.replace(chr(39), chr(39) * 2)}'; {command}"
    match = re.match(r"\s*cd\s+(\"([^\"]*)\"|'([^']*)'|(\S+))\s*(&&|;)", command)
    if match:
        target = next(group for group in match.groups()[1:4] if group is not None)
        if _key(to_native(target, root)) == _key(root):
            return None
    return f'cd "{root}" && {command}'
