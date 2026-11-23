"""A feature team's brief: its checkout, absolute paths, and PYTHONPATH (F20 design 3.2, 3.11).

A role cannot be started in a folder, so a team's brief names the team's
worktree in one sentence, which F05's hooks read from the role's transcript.
Its Read first paths are absolute in that worktree, and a Python team's
checks put the worktree's source first on the import path, while the
series keeps one environment (D275).
"""

import os
import re
from pathlib import Path

TEAMS_FOLDER = ".troy-teams"
_TEAM_FOLDER = re.compile(r"f\d+")
SENTENCE = ("You work for team {id} in the checkout `{root}`: every path in this brief is inside "
            "it, read and write files only there, and your commands start there.")
INSTALL = "uv pip install -e . --no-deps"


class Team:
    """The team worktree a brief is for.

    Attributes:
        id: The feature ID, for example "F08".
        root: The worktree's real path, in the platform's form.
        main: The main checkout's real path: the folder that holds the common
            git folder.
    """

    __slots__ = ("id", "root", "main")

    def __init__(self, team_id: str, root: str, main: str):
        """Stores the team's ID and folders."""
        self.id, self.root, self.main = team_id, root, main


def team_of(repo) -> Team | None:
    """Returns the team whose worktree the checkout is, or None for any other checkout.

    A team worktree is a linked worktree whose folder is .troy-teams/<id>.
    """
    root = Path(os.path.realpath(repo.root))
    pointer = Path(repo.git_dir) / "commondir"
    if root.parent.name != TEAMS_FOLDER or not _TEAM_FOLDER.fullmatch(root.name):
        return None
    if not pointer.is_file():
        return None
    common = Path(os.path.realpath(Path(repo.git_dir) / pointer.read_text(encoding="utf-8").strip()))
    return Team(root.name.upper(), str(root), str(common.parent))


def sentence(team: Team) -> str:
    """The Task line's sentence that names the team's checkout (F20 design 3.2)."""
    return SENTENCE.format(id=team.id, root=team.root)


def folder_name(team: Team | None, repo) -> str:
    """The checkout name that names the environment when [lang] environment is unset."""
    return Path(team.main).name if team else Path(repo.root).name


def absolute(team: Team, path: str) -> str:
    """Makes a Read first path absolute in the team's worktree; a folder keeps its separator."""
    parts = [part for part in path.split("/") if part]
    full = os.path.join(team.root, *parts)
    return full + os.sep if path.endswith("/") else full


def checks(team: Team, config, commands: list[str]) -> list[str]:
    """A Python team's checks: PYTHONPATH first, and the editable install from the main checkout."""
    if config.lang.get("name") != "python":
        return commands
    roots = config.lang.get("source_roots") or ["src"]
    folders = [os.path.normpath(absolute(team, root.rstrip("/"))) for root in roots]
    value = os.pathsep.join(folders)
    moved = [command.replace(INSTALL, f'uv pip install -e "{team.main}" --no-deps')
             for command in commands]
    return [f'PYTHONPATH="{value}" {command}' for command in moved]
