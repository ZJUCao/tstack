"""The git commands troy-init needs: reading state and setting git config."""

import os
import subprocess
from pathlib import Path

from .errors import InitError


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Runs one git command in the repository.

    Args:
        repo: The folder to run in.
        *args: Arguments after "git".
        check: Raise InitError when git exits with a non-zero code.

    Returns:
        The finished process, with text output.

    Raises:
        InitError: git is missing, or it failed and check is True.
    """
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", check=False)
    except OSError as exc:
        raise InitError(f"cannot run git: {exc}") from exc
    if check and proc.returncode != 0:
        raise InitError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def toplevel(folder: Path) -> Path | None:
    """Returns the root of the git repository holding folder, or None if there is none."""
    if not folder.is_dir():
        return None
    proc = git(folder, "rev-parse", "--show-toplevel", check=False)
    return Path(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip() else None


def is_root(folder: Path, top: Path) -> bool:
    """True when folder is the repository root top."""
    return os.path.samefile(folder, top)


def current_branch(repo: Path) -> str | None:
    """Returns the checked-out branch's short name, or None on a detached HEAD."""
    proc = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def has_remote(repo: Path, name: str) -> bool:
    """True when the repository has a remote with this name."""
    return name in git(repo, "remote").stdout.split()


def ref_exists(repo: Path, ref: str) -> bool:
    """True when the full ref name exists, for example refs/remotes/origin/main."""
    return git(repo, "rev-parse", "--verify", "--quiet", ref, check=False).returncode == 0


def config_get(repo: Path, key: str) -> str | None:
    """Returns git's effective value for a config key, or None when unset."""
    proc = git(repo, "config", "--get", key, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def config_set(repo: Path, key: str, value: str) -> None:
    """Sets a config key in the repository's own config (.git/config).

    Raises:
        InitError: git fails.
    """
    git(repo, "config", "--local", key, value)
