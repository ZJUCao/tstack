"""Baseline lines: today's violations a rule PR exempts, one line per file (F09 D81).

A baseline line holds the comment "baseline:" and a P ID, in the tool's own
config, such as an entry of ruff's per-file-ignores in pyproject.toml. Cleanup
PRs delete them one by one, and check-run lets a dependency change through
when it only deletes such lines (design 3.1 and 5.4).
"""

import re

from troycheck.classify import classify

from . import repo as git
from .repo import Repo

MARKER = re.compile(r"baseline:[ \t]*(P\d{2,3})(?![0-9])")
SEARCHED_CLASSES = ("config", "dependencies")
CONFIG_FILE = ".troy-mode/config.toml"


def searched(path: str, paths: dict) -> bool:
    """Tells whether a file can hold baseline lines.

    Config and dependency files do, except Markdown files and troy-mode's own
    copies under .troy-mode/, of which only the config holds project settings.
    """
    if path.endswith(".md"):
        return False
    if path.startswith(".troy-mode/") and path != CONFIG_FILE:
        return False
    return classify(path, paths) in SEARCHED_CLASSES


def all_files(repo: Repo, ref: str) -> list[str]:
    """Lists every file of a commit."""
    out = git.git(repo, "ls-tree", "-r", "--name-only", "-z", ref)
    return [path for path in out.split("\0") if path]


def find(repo: Repo, ref: str) -> dict[str, list[dict]]:
    """Finds the baseline lines of a commit, by P ID.

    Returns:
        For each P ID, its lines as {"path", "line", "text"}, sorted by path
        and then line; line counts from 1.
    """
    paths = git.config_at(repo, ref).paths
    wanted = [p for p in all_files(repo, ref) if searched(p, paths)]
    found: dict[str, list[dict]] = {}
    for path, text in sorted(git.read_many(repo, ref, wanted).items()):
        for number, line in enumerate(text.split("\n"), start=1):
            match = MARKER.search(line)
            if match:
                found.setdefault(match.group(1), []).append(
                    {"path": path, "line": number, "text": line.rstrip("\r")})
    return found


def only_deletes_baseline(repo: Repo, head: str, path: str) -> bool:
    """Tells whether the working tree's change to a file only deletes baseline lines.

    git's diff of the file against the snapshot's head, which applies the
    checkout's line-ending conversion, must delete one or more lines, each a
    baseline line, and add none. A new or deleted file never passes.
    """
    if not git.exists(repo, head, path) or not (repo.root / path).is_file():
        return False
    out = git.git(repo, "diff", "--no-color", "--no-ext-diff", "--no-renames", "-U0", head,
                  "--", path)
    deleted, in_hunks = 0, False
    for line in out.split("\n"):
        if line.startswith("@@"):
            in_hunks = True
        elif not in_hunks or line.startswith("\\"):
            continue
        elif line.startswith("+"):
            return False
        elif line.startswith("-"):
            if not MARKER.search(line[1:]):
                return False
            deleted += 1
    return deleted > 0
