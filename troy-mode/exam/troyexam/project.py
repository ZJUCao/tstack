"""One run's project, origin, and plugin copy (design 4.2 and 6.1).

The project's history holds the start commit and its ancestors only, fetched
from a mirror by commit ID, so no later commit, review, or fix can be read. Its
origin is a bare repository beside it, seeded by fetching, never by a push.
"""

import hashlib
import io
import os
import random
import shutil
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path

from . import PLUGIN_NAME
from .blinding import random_letters
from .cases import Case
from .errors import ExamError
from .paths import Layout, repository_name

HOOKS_PATH = ".troy-mode/checks/git-hooks"
# Folders of tstack that are not role instructions and name the exam; the copy leaves them out.
NOT_COPIED = ("docs/", ".github/", "troy-mode/dev/", "troy-mode/exam/")
_IDENTITY = ("-c", "user.name=troy-mode", "-c", "user.email=troy-mode@localhost")


def git(cwd: Path, *args: str, data: bytes | None = None, check: bool = True) -> str:
    """Runs git in cwd and gives its output.

    Raises:
        ExamError: git failed and check is true.
    """
    proc = subprocess.run(["git", *args], cwd=str(cwd), input=data, capture_output=True)
    if check and proc.returncode:
        raise ExamError(f"git {' '.join(args)} in {cwd}: "
                        f"{proc.stderr.decode('utf-8', errors='replace').strip()}")
    return proc.stdout.decode("utf-8", errors="replace")


@dataclass
class RunFolder:
    """The folders of one run.

    Attributes:
        root: runs/<six letters>.
        project: root/<repository name>.
        origin: root/<repository name>.git.
        plugin: root/tstack.
        bin: root/bin, first on the run's PATH.
    """

    root: Path
    project: Path
    origin: Path
    plugin: Path
    bin: Path


def source_url(repository: str) -> str:
    """Where a mirror is cloned from: a local folder as is, else GitHub."""
    if Path(repository).is_dir():
        return str(Path(repository))
    return f"https://github.com/{repository}.git"


def _has_commit(repo: Path, commit: str) -> bool:
    """Tells whether a repository holds a commit."""
    proc = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
                          capture_output=True)
    return proc.returncode == 0


def ensure_mirror(layout: Layout, repository: str, commit: str) -> Path:
    """Gives a bare mirror of the start repository that holds the commit.

    Raises:
        ExamError: The commit cannot be found even after a fetch.
    """
    mirror = layout.mirror(repository)
    if not mirror.is_dir():
        mirror.parent.mkdir(parents=True, exist_ok=True)
        git(mirror.parent, "clone", "--mirror", "--quiet", source_url(repository), str(mirror))
    if not _has_commit(mirror, commit):
        git(mirror, "fetch", "--quiet", "origin", check=False)
        if not _has_commit(mirror, commit):
            git(mirror, "fetch", "--quiet", "origin", commit, check=False)
    if not _has_commit(mirror, commit):
        raise ExamError(f"{repository} has no commit {commit}")
    git(mirror, "config", "uploadpack.allowAnySHA1InWant", "true")
    return mirror


def new_run_folder(layout: Layout, repository: str, rng: random.Random | None = None) -> RunFolder:
    """Creates runs/<six letters>, a name not used yet."""
    layout.runs.mkdir(parents=True, exist_ok=True)
    name = repository_name(repository)
    while True:
        root = layout.runs / random_letters(rng)
        try:
            root.mkdir()
            break
        except FileExistsError:
            continue
    return RunFolder(root, root / name, root / f"{name}.git", root / PLUGIN_NAME, root / "bin")


def _commit_patch(project: Path, patch: Path, title: str) -> None:
    """Applies a patch to the index, commits it without hooks, and refreshes the working tree."""
    git(project, "apply", "--cached", "--whitespace=nowarn", str(patch))
    git(project, *_identity(project), "commit", "--quiet", "--no-verify", "-m", title)
    git(project, "reset", "--quiet", "--hard", "HEAD")


def _identity(project: Path) -> tuple[str, ...]:
    """The start commit's author as the committer of the start patch."""
    out = git(project, "log", "-1", "--format=%an%n%ae", check=False).splitlines()
    if len(out) == 2 and out[0] and out[1]:
        return ("-c", f"user.name={out[0]}", "-c", f"user.email={out[1]}")
    return _IDENTITY


def build_project(case: Case, folder: RunFolder, mirror: Path) -> str:
    """Builds a run's project and its origin (design 4.2, steps 1, 2, 3, and 5).

    Returns:
        The commit the role starts from (HEAD).
    """
    project, commit = folder.project, case.start.commit
    project.mkdir(parents=True)
    git(project, "init", "--quiet")
    git(project, "config", "core.autocrlf", "true")
    git(project, "fetch", "--quiet", "--no-tags", str(mirror), commit)
    full = git(project, "rev-parse", "FETCH_HEAD").strip()
    git(project, "update-ref", "refs/heads/main", full)
    git(project, "symbolic-ref", "HEAD", "refs/heads/main")
    git(project, "reset", "--quiet", "--hard", "main")
    git(project, "checkout", "--quiet", "-b", case.start.branch)
    if case.start_patch is not None:
        _commit_patch(project, case.start_patch, case.start.title or case.title or case.id)
    git(folder.root, "init", "--quiet", "--bare", str(folder.origin))
    refs = ["refs/heads/main:refs/heads/main"]
    if case.start_patch is not None:
        refs.append(f"refs/heads/{case.start.branch}:refs/heads/{case.start.branch}")
    git(folder.origin, "fetch", "--quiet", "--no-tags", str(project), *refs)
    git(folder.origin, "symbolic-ref", "HEAD", "refs/heads/main")
    git(project, "remote", "add", "origin", str(folder.origin))
    git(project, "fetch", "--quiet", "origin")
    git(project, "remote", "set-head", "origin", "main")
    if case.start_patch is not None:
        git(project, "branch", "--quiet", "--set-upstream-to", f"origin/{case.start.branch}")
    git(project, "config", "core.hooksPath", HOOKS_PATH)
    git(project, "reflog", "expire", "--expire=now", "--all", check=False)
    return git(project, "rev-parse", "HEAD").strip()


def copy_plugin(repo: Path, ref: str, dest: Path) -> str:
    """Copies the tstack commit ref into dest with git archive, without NOT_COPIED.

    Returns:
        The full commit ID of ref.
    """
    commit = git(repo, "rev-parse", f"{ref}^{{commit}}").strip()
    proc = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit],
                          capture_output=True)
    if proc.returncode:
        raise ExamError(f"git archive {ref}: {proc.stderr.decode(errors='replace').strip()}")
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        members = [m for m in tar.getmembers()
                   if not any(m.name == p.rstrip("/") or m.name.startswith(p) for p in NOT_COPIED)
                   and not m.name.startswith(("/", "..")) and ".." not in m.name.split("/")]
        tar.extractall(dest, members=members, filter="data")
    return commit


def lock_key(project: Path) -> str:
    """The first 12 hex digits of the hash of environment.yml and requirements-dev.lock."""
    digest = hashlib.sha256()
    for name in ("environment.yml", "requirements-dev.lock"):
        path = project / name
        digest.update(name.encode() + b"\0" + (path.read_bytes().replace(b"\r\n", b"\n")
                                               if path.is_file() else b"") + b"\0")
    return digest.hexdigest()[:12]


def _mamba() -> str:
    """mamba: $MAMBA_EXE, the PATH, or Miniforge's usual place."""
    for candidate in (os.environ.get("MAMBA_EXE"), shutil.which("mamba"),
                      r"D:\miniforge3\Library\bin\mamba.exe"):
        if candidate and Path(candidate).is_file():
            return candidate
    raise ExamError("mamba is not found; set MAMBA_EXE")


def ensure_env(layout: Layout, repository: str, project: Path) -> Path:
    """Gives the environment of a start: envs/<repository>-<lock key>, created once (design 4.2 step 6).

    It is created from the start's environment.yml with mamba, and its packages
    from requirements-dev.lock with uv, with no editable install, so no run
    changes it. Troy's own environments are never touched.
    """
    prefix = layout.envs / f"{repository_name(repository)}-{lock_key(project)}"
    if (prefix / "conda-meta").is_dir():
        return prefix
    layout.envs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MAMBA_ROOT_PREFIX=os.environ.get("MAMBA_ROOT_PREFIX", r"D:\miniforge3"),
               UV_CACHE_DIR=str(layout.root / "uv-cache"), UV_LINK_MODE="copy")
    steps = [[_mamba(), "env", "create", "--yes", "-p", str(prefix), "-f",
              str(project / "environment.yml")]]
    lock = project / "requirements-dev.lock"
    if lock.is_file():
        python = prefix / ("python.exe" if os.name == "nt" else "bin/python")
        steps.append([_mamba(), "run", "-p", str(prefix), "uv", "pip", "install", "--python",
                      str(python), "-r", str(lock)])
    for step in steps:
        proc = subprocess.run(step, cwd=str(project), env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode:
            shutil.rmtree(prefix, ignore_errors=True)
            raise ExamError(f"creating {prefix} failed: {proc.stderr.strip()[-800:]}")
    return prefix
