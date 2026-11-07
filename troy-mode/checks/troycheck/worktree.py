"""The working tree as a commit, for troy-check code --worktree (F07 design 12, D60).

Roles cannot commit, so an author checks its own work with --worktree. The
commit is built from a temporary index outside the working tree, with HEAD as
its parent. No ref moves, and neither the real index nor the working tree
changes. Only git objects that no ref points to are written.
"""

import os
import subprocess
import tempfile
from pathlib import Path

from .gitio import GitError

# commit-tree needs an identity. The commit is never kept, and no check of
# troy-check code reads its author, so a fixed one is enough.
_IDENTITY = {
    "GIT_AUTHOR_NAME": "troy-check", "GIT_AUTHOR_EMAIL": "troy-check@localhost",
    "GIT_COMMITTER_NAME": "troy-check", "GIT_COMMITTER_EMAIL": "troy-check@localhost",
}


def _git(repo: Path, env: dict, *args: str, stdin: bytes | None = None) -> str:
    """Runs one git command with its own environment and returns its stdout.

    Raises:
        GitError: git is missing or fails.
    """
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, env=env,
                              input=stdin)
    except OSError as exc:
        raise GitError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise GitError(f"git {' '.join(args)} failed: {err}")
    return proc.stdout.decode("utf-8", "replace").strip()


def worktree_commit(repo: Path, message: str) -> str:
    """Builds a commit of the working tree on top of HEAD, without moving anything.

    New files count and ignored files do not, as with `git add -A`.

    Args:
        repo: Repository root.
        message: The commit message, for example the PR title.

    Returns:
        The new commit's ID.

    Raises:
        GitError: HEAD has no commit, or a git command fails.
    """
    with tempfile.TemporaryDirectory(prefix="troy-check-worktree-") as folder:
        env = {**os.environ, **_IDENTITY, "GIT_INDEX_FILE": os.path.join(folder, "index")}
        _git(repo, env, "read-tree", "HEAD")
        _git(repo, env, "add", "-A", "--", ".")
        tree = _git(repo, env, "write-tree")
        return _git(repo, env, "commit-tree", tree, "-p", "HEAD", stdin=message.encode("utf-8"))
