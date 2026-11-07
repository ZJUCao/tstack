"""The gate: is a call inside a troy-mode project? (design section 4)

The gate reads only the file system, so a call outside troy-mode projects
costs no git process.
"""

import os

MARKER = ".troy-mode"
HOOKS_PATH = ".troy-mode/checks/git-hooks"
HOOK_NAMES = ("commit-msg", "pre-commit", "pre-merge-commit", "pre-push")


class Project:
    """A troy-mode project's checkout.

    Attributes:
        root: The real path of the folder that holds .git and .troy-mode.
        git_dir: The real path of the checkout's git directory: .git, or the
            folder a worktree's .git file names.
    """

    __slots__ = ("root", "git_dir")

    def __init__(self, root: str, git_dir: str):
        """Stores the checkout's folders."""
        self.root, self.git_dir = root, git_dir

    def state_dir(self) -> str:
        """Returns the folder for the hooks' own files: <git dir>/troy-mode."""
        return os.path.join(self.git_dir, "troy-mode")

    def hooks_dir(self) -> str:
        """Returns the folder that holds the project's git hooks."""
        return os.path.join(self.root, *HOOKS_PATH.split("/"))

    def missing_hooks(self) -> list[str]:
        """Lists the git hook files that are not in the project's hooks folder."""
        folder = self.hooks_dir()
        return [name for name in HOOK_NAMES if not os.path.isfile(os.path.join(folder, name))]

    def branch(self) -> str | None:
        """Reads the current branch from the HEAD file, without git.

        Returns:
            The branch name, or None for a detached or unreadable HEAD.
        """
        try:
            with open(os.path.join(self.git_dir, "HEAD"), encoding="utf-8") as handle:
                head = handle.read().strip()
        except OSError:
            return None
        prefix = "ref: refs/heads/"
        return head[len(prefix):] if head.startswith(prefix) else None


def _git_dir(root: str, dot_git: str) -> str:
    """Finds the git directory from a checkout's .git folder or file."""
    if os.path.isdir(dot_git):
        return dot_git
    try:
        with open(dot_git, encoding="utf-8") as handle:
            line = handle.readline().strip()
    except OSError:
        return dot_git
    if not line.startswith("gitdir:"):
        return dot_git
    return os.path.realpath(os.path.join(root, line[len("gitdir:"):].strip()))


def find_project(cwd: str) -> Project | None:
    """Walks up from cwd to the nearest checkout and tells whether it is troy-mode's.

    Args:
        cwd: The folder from the hook input.

    Returns:
        The project when the nearest folder that holds .git (a folder, or a
        file in a worktree) also holds a .troy-mode folder; None otherwise.
    """
    path = os.path.realpath(cwd)
    while True:
        dot_git = os.path.join(path, ".git")
        if os.path.exists(dot_git):
            if os.path.isdir(os.path.join(path, MARKER)):
                return Project(path, _git_dir(path, dot_git))
            return None
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent
