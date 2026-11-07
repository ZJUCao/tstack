"""The git facts the hooks need, each read with one git process.

Every call goes through troy-check's gitio, which runs git with "-C <root>".
"""

import hashlib
import json
import os
import re

from troycheck import gitio
from troycheck.config import CONFIG_PATH, Config, parse_config

from .project import HOOKS_PATH, Project


_SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


def _read_line(path: str) -> str | None:
    """Reads the first line of a small file, or None when it cannot be read."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.readline().strip()
    except OSError:
        return None


def _common_dir(project: Project) -> str:
    """Finds the git directory that worktrees share: the commondir file, else the git dir."""
    common = _read_line(os.path.join(project.git_dir, "commondir"))
    return os.path.join(project.git_dir, common) if common else project.git_dir


def head_commit(project: Project) -> str | None:
    """Reads HEAD's commit ID from git's files, without starting git.

    Returns:
        The commit ID, or None when HEAD is unborn or the refs cannot be read
        this way (for example a reftable repository).
    """
    head = _read_line(os.path.join(project.git_dir, "HEAD"))
    if not head or not head.startswith("ref: "):
        return head if head and _SHA.fullmatch(head) else None
    ref, common = head[5:], _common_dir(project)
    for base in (project.git_dir, common):
        sha = _read_line(os.path.join(base, *ref.split("/")))
        if sha and _SHA.fullmatch(sha):
            return sha
    try:
        with open(os.path.join(common, "packed-refs"), encoding="utf-8") as handle:
            for line in handle:
                sha, _, name = line.strip().partition(" ")
                if name == ref and _SHA.fullmatch(sha):
                    return sha
    except OSError:
        pass
    return None


def _config_text(project: Project) -> str | None:
    """Reads the config's text at HEAD, through a cache keyed by HEAD's commit ID.

    The cache saves a git process on most calls. A new commit changes the ID,
    so the cache never serves another commit's config.
    """
    sha = head_commit(project)
    cache = os.path.join(project.state_dir(), "config-cache.json")
    if sha:
        try:
            with open(cache, encoding="utf-8") as handle:
                cached = json.load(handle)
            if cached.get("head") == sha:
                return cached.get("text")
        except (OSError, ValueError, AttributeError):
            pass
    text = gitio.read_blob(project.root, "HEAD", CONFIG_PATH)
    if sha:
        try:
            os.makedirs(project.state_dir(), exist_ok=True)
            with open(cache, "w", encoding="utf-8", newline="\n") as handle:
                json.dump({"head": sha, "text": text}, handle)
        except OSError:
            pass
    return text


def config_at_head(project: Project) -> Config:
    """Reads .troy-mode/config.toml as committed at HEAD (design 5.2).

    An uncommitted edit of the config cannot widen a scope. A missing file,
    or a repository with no commit yet, gives the built-in defaults.

    Raises:
        ConfigError: The committed config is not valid.
    """
    return parse_config(_config_text(project))


def is_ignored(project: Project, rel: str) -> bool:
    """Tells whether git ignores a repository path (git check-ignore).

    Raises:
        GitError: git fails.
    """
    proc = gitio.run_git(project.root, "check-ignore", "-q", "--", rel, check=False)
    if proc.returncode not in (0, 1):
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise gitio.GitError(f"git check-ignore failed: {err}")
    return proc.returncode == 0


def hooks_path(project: Project) -> str | None:
    """Reads core.hooksPath, or None when it is unset."""
    proc = gitio.run_git(project.root, "config", "--get", "core.hooksPath", check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace").strip()


def hooks_on(value: str | None) -> bool:
    """Tells whether a core.hooksPath value turns on the troy-mode git hooks."""
    return value is not None and value.replace("\\", "/").rstrip("/") == HOOKS_PATH


def set_hooks_path(project: Project) -> None:
    """Sets core.hooksPath to the troy-mode git hooks in the local config."""
    gitio.run_git(project.root, "config", "--local", "core.hooksPath", HOOKS_PATH)


def _digest(root: str, rel: str) -> str | None:
    """Hashes a file's content: None when it is gone, "dir" for a folder entry."""
    full = os.path.join(root, rel)
    if os.path.isdir(full):
        return "dir"
    try:
        with open(full, "rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except FileNotFoundError:
        return None
    except OSError:
        return "unreadable"


def snapshot(project: Project) -> dict[str, list]:
    """Lists every changed or untracked path with a hash of its content (design 6).

    Returns:
        A map from repository path to [status code, hash]. The status code is
        git's two letters, "??" for an untracked file.

    Raises:
        GitError: git fails.
    """
    out = gitio.run_git(project.root, "--no-optional-locks", "status", "--porcelain=v1", "-z",
                        "--untracked-files=all").stdout
    entries = out.split(b"\0")
    result: dict[str, list] = {}
    i = 0
    while i < len(entries):
        entry = entries[i].decode("utf-8", "replace")
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:].rstrip("/")
        result[path] = [code, _digest(project.root, path)]
        if code[0] in "RC" and i < len(entries):
            source = entries[i].decode("utf-8", "replace")
            i += 1
            result[source] = [code, _digest(project.root, source)]
    return result
