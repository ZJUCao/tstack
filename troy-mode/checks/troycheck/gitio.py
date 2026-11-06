"""Read-only access to the git repository under check.

Every call goes through the git command line. Diffs run with external diff
drivers and text conversion turned off, so no command configured for the
repository ever runs.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(Exception):
    """Raised when a git command fails or the folder is not a repository."""


@dataclass(frozen=True)
class Change:
    """One changed path between two commits.

    Attributes:
        status: First letter of git's status: "A", "M", "D", "R", "C", or "T".
        path: The path at the newer commit, or the deleted path for "D".
        old_path: The path at the older commit for a rename or copy, else None.
    """

    status: str
    path: str
    old_path: str | None = None


@dataclass(frozen=True)
class Commit:
    """One commit in the PR.

    Attributes:
        sha: Full commit ID.
        author_email: Author email.
        committer_email: Committer email.
        message: Full commit message.
    """

    sha: str
    author_email: str
    committer_email: str
    message: str


@dataclass(frozen=True)
class LineCount:
    """Changed line counts for one path, from git diff --numstat.

    Attributes:
        path: The path at the newer commit.
        added: Added lines, or None for a binary file.
        deleted: Deleted lines, or None for a binary file.
    """

    path: str
    added: int | None
    deleted: int | None


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Runs one git command in the repository.

    Args:
        repo: Repository root.
        *args: Arguments after "git".
        check: Raise GitError when git exits with a non-zero code.

    Returns:
        The finished process, with stdout and stderr as bytes.

    Raises:
        GitError: git is missing, or it failed and check is True.
    """
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    except OSError as exc:
        raise GitError(f"cannot run git: {exc}") from exc
    if check and proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise GitError(f"git {' '.join(args)} failed: {err}")
    return proc


def _text(proc: subprocess.CompletedProcess) -> str:
    """Decodes a git process's stdout as UTF-8."""
    return proc.stdout.decode("utf-8", "replace")


def repo_root(start: Path) -> Path:
    """Finds the top-level folder of the repository that contains start.

    Args:
        start: Any folder inside the repository.

    Returns:
        The repository root.

    Raises:
        GitError: start is not inside a git repository.
    """
    if not start.is_dir():
        raise GitError(f"{start} is not a folder")
    proc = run_git(start, "rev-parse", "--show-toplevel", check=False)
    if proc.returncode != 0:
        raise GitError(f"{start} is not inside a git repository")
    return Path(_text(proc).strip())


def resolve(repo: Path, ref: str) -> str:
    """Turns a ref into a full commit ID.

    Args:
        repo: Repository root.
        ref: A branch, tag, or commit ID.

    Returns:
        The full commit ID.

    Raises:
        GitError: The ref names no commit.
    """
    proc = run_git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    if proc.returncode != 0:
        raise GitError(f"{ref!r} is not a commit")
    return _text(proc).strip()


def merge_base(repo: Path, base: str, head: str) -> str:
    """Finds the merge base of two commits.

    Args:
        repo: Repository root.
        base: The target branch's commit.
        head: The PR's last commit.

    Returns:
        The merge-base commit ID.

    Raises:
        GitError: The commits share no history.
    """
    proc = run_git(repo, "merge-base", base, head, check=False)
    if proc.returncode != 0:
        raise GitError(f"{base} and {head} have no common history")
    return _text(proc).strip()


def commits(repo: Path, start: str, end: str) -> list[Commit]:
    """Lists the commits reachable from end but not from start.

    Args:
        repo: Repository root.
        start: The merge base.
        end: The PR's last commit.

    Returns:
        The commits, newest first, merge commits included.
    """
    fmt = "--format=%H%x00%ae%x00%ce%x00%B%x1e"
    out = _text(run_git(repo, "log", "--no-show-signature", fmt, f"{start}..{end}"))
    result = []
    for record in out.split("\x1e"):
        record = record.lstrip("\n")
        if not record:
            continue
        sha, author, committer, message = record.split("\x00", 3)
        result.append(Commit(sha, author, committer, message))
    return result


def changes(repo: Path, start: str, end: str) -> list[Change]:
    """Lists the paths changed between two commits, with renames detected.

    Args:
        repo: Repository root.
        start: The older commit.
        end: The newer commit.

    Returns:
        One Change per changed path.
    """
    out = _text(run_git(repo, "diff", "--no-ext-diff", "--no-textconv", "--name-status",
                        "-z", "--find-renames", start, end))
    tokens = out.split("\x00")
    result, i = [], 0
    while i < len(tokens) and tokens[i]:
        status = tokens[i][0]
        if status in ("R", "C"):
            result.append(Change(status, tokens[i + 2], tokens[i + 1]))
            i += 3
        else:
            result.append(Change(status, tokens[i + 1]))
            i += 2
    return result


def _count(text: str) -> int | None:
    """Parses one numstat count, where "-" marks a binary file."""
    return None if text == "-" else int(text)


def line_counts(repo: Path, start: str, end: str) -> list[LineCount]:
    """Counts added and deleted lines per changed path.

    Args:
        repo: Repository root.
        start: The older commit.
        end: The newer commit.

    Returns:
        One LineCount per changed path. Renamed files use their new path.
    """
    out = _text(run_git(repo, "diff", "--no-ext-diff", "--no-textconv", "--numstat",
                        "-z", "--find-renames", start, end))
    tokens = out.split("\x00")
    result, i = [], 0
    while i < len(tokens) and tokens[i]:
        added, deleted, path = tokens[i].split("\t", 2)
        if path:
            i += 1
        else:
            path = tokens[i + 2]
            i += 3
        result.append(LineCount(path, _count(added), _count(deleted)))
    return result


def read_blob(repo: Path, commit: str, path: str) -> str | None:
    """Reads a file as it is in a commit.

    Args:
        repo: Repository root.
        commit: Commit ID.
        path: Repository path with "/" separators.

    Returns:
        The file's text decoded as UTF-8, or None if the file does not exist
        in that commit.
    """
    proc = run_git(repo, "cat-file", "blob", f"{commit}:{path}", check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")


def read_blobs(repo: Path, commit: str, paths: list[str]) -> dict[str, str]:
    """Reads many files of one commit with a single git process.

    Args:
        repo: Repository root.
        commit: Commit ID.
        paths: Repository paths.

    Returns:
        Text by path, decoded as UTF-8. Missing files are left out.
    """
    if not paths:
        return {}
    request = "".join(f"{commit}:{p}\n" for p in paths).encode("utf-8")
    try:
        proc = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"], input=request,
                              capture_output=True)
    except OSError as exc:
        raise GitError(f"cannot run git: {exc}") from exc
    out, pos, result = proc.stdout, 0, {}
    for path in paths:
        end = out.index(b"\n", pos)
        header = out[pos:end].split()
        pos = end + 1
        if len(header) == 3 and header[1] == b"blob":
            size = int(header[2])
            result[path] = out[pos:pos + size].decode("utf-8", "replace")
            pos += size + 1
        elif len(header) == 3:
            pos += int(header[2]) + 1
    return result


def files_containing(repo: Path, commit: str, pattern: str, glob: str) -> list[str]:
    """Lists files in a commit with a line matching a regular expression.

    Args:
        repo: Repository root.
        commit: Commit ID.
        pattern: Extended regular expression for git grep.
        glob: Pathspec that limits the files, for example "*.md".

    Returns:
        Matching repository paths.
    """
    proc = run_git(repo, "grep", "-z", "-l", "-E", "-e", pattern, commit, "--", glob,
                   check=False)
    if proc.returncode not in (0, 1):
        raise GitError("git grep failed: " + proc.stderr.decode("utf-8", "replace"))
    prefix = commit + ":"
    names = [n for n in _text(proc).split("\x00") if n]
    return [n[len(prefix):] if n.startswith(prefix) else n for n in names]


def list_files(repo: Path, commit: str, folder: str) -> list[str]:
    """Lists every file under a folder in a commit.

    Args:
        repo: Repository root.
        commit: Commit ID.
        folder: Repository folder, for example "docs/features".

    Returns:
        Repository paths, empty when the folder does not exist.
    """
    proc = run_git(repo, "ls-tree", "-r", "--name-only", "-z", commit, "--", folder, check=False)
    if proc.returncode != 0:
        return []
    return [p for p in _text(proc).split("\x00") if p]


def subjects(repo: Path, commit: str) -> list[str]:
    """Lists the subject lines of every commit reachable from a commit.

    Args:
        repo: Repository root.
        commit: Commit ID, usually the merge base.

    Returns:
        Subject lines, newest first.
    """
    out = _text(run_git(repo, "log", "--no-show-signature", "--format=%s", commit))
    return [line for line in out.split("\n") if line]


_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def added_lines(repo: Path, start: str, end: str, paths: list[str]) -> dict[str, set[int]]:
    """Finds the lines added or modified in some files between two commits.

    Args:
        repo: Repository root.
        start: The older commit.
        end: The newer commit.
        paths: Paths at the newer commit to look at.

    Returns:
        Line numbers at the newer commit, by path. Files with only deleted
        lines map to an empty set.
    """
    if not paths:
        return {}
    out = _text(run_git(repo, "-c", "core.quotepath=false", "diff", "--no-ext-diff",
                        "--no-textconv", "-U0", "--no-color", "--find-renames", start, end,
                        "--", *paths))
    result: dict[str, set[int]] = {}
    current = None
    for line in out.split("\n"):
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            if current is not None:
                result.setdefault(current, set())
            continue
        hunk = _HUNK.match(line)
        if hunk and current is not None:
            first, count = int(hunk.group(1)), int(hunk.group(2) or "1")
            result[current].update(range(first, first + count))
    return result


def author_email(repo: Path) -> str:
    """Finds the author email git would use for the next commit.

    Args:
        repo: Repository root.

    Returns:
        The email in git var GIT_AUTHOR_IDENT, or "" if it has none.
    """
    ident = _text(run_git(repo, "var", "GIT_AUTHOR_IDENT"))
    match = re.search(r"<([^>]*)>", ident)
    return match.group(1) if match else ""
