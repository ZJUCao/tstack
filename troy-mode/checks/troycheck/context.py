"""Everything the PR checks need to know about one PR, gathered once."""

from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .gitio import Change, Commit
from .titles import Title


@dataclass
class PrContext:
    """Inputs shared by all PR checks.

    Attributes:
        repo: Repository root.
        base: The merge-base commit ID. Checks compare it with head.
        head: The PR's last commit ID.
        title_text: The PR title as given.
        title: The parsed title, or None if it matches no PR kind.
        body: The PR description, or None if none was given.
        config: Settings read from the merge-base commit.
        changes: Changed paths between base and head.
        commits: Commits from base to head.
    """

    repo: Path
    base: str
    head: str
    title_text: str
    title: Title | None
    body: str | None
    config: Config
    changes: list[Change]
    commits: list[Commit]

    def changed_paths(self) -> list[str]:
        """Returns every changed path, old and new paths of renames included."""
        paths = []
        for change in self.changes:
            if change.old_path is not None:
                paths.append(change.old_path)
            paths.append(change.path)
        return paths
