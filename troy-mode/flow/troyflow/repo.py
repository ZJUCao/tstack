"""Read-only git access for the engine, through troy-check's gitio."""

from dataclasses import dataclass
from pathlib import Path

from troycheck import gitio
from troycheck.config import CONFIG_PATH, Config, ConfigError, parse_config

from .errors import FlowError

MAIN = "origin/main"


@dataclass(frozen=True)
class Repo:
    """A checkout.

    Attributes:
        root: The working tree's top folder.
        git_dir: The checkout's own git directory (a worktree's, for a worktree).
    """

    root: Path
    git_dir: Path

    def state_dir(self) -> Path:
        """Returns <git dir>/troy-mode, where the hooks and the engine keep their files."""
        return self.git_dir / "troy-mode"


def _text(proc) -> str:
    """Decodes a finished git process's stdout."""
    return proc.stdout.decode("utf-8", "replace")


def find_repo(path: str | None) -> Repo | None:
    """Finds the checkout that holds a folder.

    Args:
        path: The --repo folder, or None for the current folder.

    Returns:
        The checkout, or None when the folder is not inside a git repository.

    Raises:
        FlowError: The folder does not exist.
    """
    start = Path(path) if path else Path.cwd()
    if not start.is_dir():
        raise FlowError(f"{start} is not a folder")
    proc = gitio.run_git(start, "rev-parse", "--show-toplevel", "--absolute-git-dir",
                         check=False)
    if proc.returncode != 0:
        return None
    lines = _text(proc).strip().split("\n")
    return Repo(Path(lines[0].strip()), Path(lines[1].strip()))


def need_repo(path: str | None) -> Repo:
    """Finds the checkout like find_repo, for commands that need one.

    Raises:
        FlowError: The folder is not inside a git repository.
    """
    repo = find_repo(path)
    if repo is None:
        raise FlowError(f"{path or Path.cwd()} is not inside a git repository")
    return repo


def git(repo: Repo, *args: str) -> str:
    """Runs a git command that must succeed and returns its stdout.

    Raises:
        FlowError: git fails.
    """
    try:
        return _text(gitio.run_git(repo.root, *args))
    except gitio.GitError as exc:
        raise FlowError(str(exc)) from exc


def commit_of(repo: Repo, ref: str) -> str | None:
    """Returns the commit ID a ref names, or None when it names none."""
    proc = gitio.run_git(repo.root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}",
                         check=False)
    return _text(proc).strip() if proc.returncode == 0 else None


def branch(repo: Repo) -> str | None:
    """Returns the current branch's name, or None when HEAD is detached."""
    proc = gitio.run_git(repo.root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    return _text(proc).strip() if proc.returncode == 0 else None


def read(repo: Repo, ref: str, path: str) -> str | None:
    """Reads a file as it is in a commit, or None when it is not there."""
    return gitio.read_blob(repo.root, ref, path)


def exists(repo: Repo, ref: str, path: str) -> bool:
    """Tells whether a path exists in a commit."""
    return gitio.run_git(repo.root, "cat-file", "-e", f"{ref}:{path}", check=False).returncode == 0


def subjects(repo: Repo, ref: str) -> list[str]:
    """Lists the subject lines of every commit reachable from a ref, newest first."""
    try:
        return gitio.subjects(repo.root, ref)
    except gitio.GitError as exc:
        raise FlowError(str(exc)) from exc


def folders(repo: Repo, ref: str, parent: str) -> list[str]:
    """Lists the folder names directly inside a folder of a commit, sorted."""
    proc = gitio.run_git(repo.root, "ls-tree", "-d", "-z", "--name-only", ref, "--",
                         parent.rstrip("/") + "/", check=False)
    if proc.returncode != 0:
        return []
    return sorted(p.rsplit("/", 1)[-1] for p in _text(proc).split("\0") if p)


def files(repo: Repo, ref: str, folder: str) -> list[str]:
    """Lists every file under a folder of a commit."""
    try:
        return gitio.list_files(repo.root, ref, folder)
    except gitio.GitError as exc:
        raise FlowError(str(exc)) from exc


def read_many(repo: Repo, ref: str, paths: list[str]) -> dict[str, str]:
    """Reads many files of one commit; missing files are left out."""
    try:
        return gitio.read_blobs(repo.root, ref, paths)
    except gitio.GitError as exc:
        raise FlowError(str(exc)) from exc


def config_at(repo: Repo, ref: str) -> Config:
    """Reads .troy-mode/config.toml as committed in a commit.

    A missing file, or a ref that names no commit, gives the defaults.

    Raises:
        FlowError: The committed config is not valid.
    """
    text = read(repo, ref, CONFIG_PATH) if commit_of(repo, ref) else None
    try:
        return parse_config(text)
    except ConfigError as exc:
        raise FlowError(f"{CONFIG_PATH} at {ref}: {exc}") from exc


def changed_paths(repo: Repo) -> list[tuple[str, str]]:
    """Lists the working tree's changes that git does not ignore.

    Returns:
        Pairs of git's two-letter porcelain code and the path, both paths of a
        rename or copy included, sorted by path.
    """
    entries = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").split("\0")
    found, i = {}, 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        found[path] = code
        if code[0] in "RC" and i < len(entries):
            found[entries[i]] = code
            i += 1
    return sorted(((code, path) for path, code in found.items()), key=lambda pair: pair[1])
