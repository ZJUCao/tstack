"""Shared fixtures for the troy-check unit tests.

The tests build throwaway git repositories, commit a pull request's changes
on a branch, and run ``troy_check.py`` as a subprocess. Nothing here imports
the implementation: only the command-line interface is used.
"""

from __future__ import annotations

import atexit
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union

from builders import (  # noqa: F401  (re-exported for the tests)
    DEFAULT_CONFIG, EMAIL, EN_BODY, ZH_BODY, doc_pair, doc_text, lines,
    make_config, pr_body,
)
from outcome import CheckTestCase, Outcome  # noqa: F401
from parallel import parallel  # noqa: F401
CHECKER = Path(__file__).resolve().parents[1] / "troy_check.py"
CONFIG_PATH = ".troy-mode/config.toml"
OTHER_EMAIL = "someone@example.test"
GITHUB_COMMITTER_EMAIL = "noreply@github.com"
PR_RULES = ("R01", "R02", "R03", "R12", "R16", "R19", "R20")
Content = Union[str, bytes, None]

_SCRATCH = tempfile.TemporaryDirectory(prefix="troycheck-scratch-")
atexit.register(_SCRATCH.cleanup)
_GLOBAL_CONFIG = Path(_SCRATCH.name) / "gitconfig"
# No background maintenance or gc: since git 2.47 it runs detached after a
# commit and can leave a lock file appear or vanish while a template is copied.
_GLOBAL_CONFIG.write_text("[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n", encoding="utf-8")
_TEMPLATES: dict = {}
_LOCK = threading.Lock()

_DROPPED_ENV = (
    "GITHUB_ACTIONS",
    "GITHUB_STEP_SUMMARY",
    "PYTHONUTF8",
    "PYTHONIOENCODING",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
)


def base_env(extra: Optional[Mapping[str, str]] = None) -> dict:
    """Builds an environment that isolates git from the user's machine.

    Args:
        extra: Variables that override or extend the isolated defaults.

    Returns:
        A new environment dictionary for a subprocess.
    """
    env = dict(os.environ)
    for name in _DROPPED_ENV:
        env.pop(name, None)
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(_GLOBAL_CONFIG),
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": EMAIL,
            "GIT_COMMITTER_NAME": "Test Committer",
            "GIT_COMMITTER_EMAIL": EMAIL,
        }
    )
    env.update(extra or {})
    return env


def run_git(cwd: Path, *args: str, env: Optional[dict] = None) -> str:
    """Runs git and raises when it fails.

    Args:
        cwd: Directory to run in.
        *args: Arguments after ``git``.
        env: Environment to use. Defaults to ``base_env()``.

    Returns:
        Standard output of the command.

    Raises:
        RuntimeError: If git exits with a non-zero code.
    """
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        env=env if env is not None else base_env(),
        capture_output=True,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout


def write_file(root: Path, rel: str, content: Union[str, bytes]) -> None:
    """Writes a file as UTF-8 with LF line endings, creating folders.

    Args:
        root: Repository root.
        rel: Path relative to the root, with ``/`` separators.
        content: Text or raw bytes to write.
    """
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
        return
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)



def _template_repo(base_files: Mapping[str, Content], config: Optional[str]) -> Path:
    """Returns a cached repository holding only the base commit on main.

    Args:
        base_files: Files of the base commit.
        config: Text of ``.troy-mode/config.toml``, or None for no file.

    Returns:
        Path of a template repository that callers copy, never modify.
    """
    with _LOCK:
        return _locked_template(base_files, config)


def _locked_template(base_files: Mapping[str, Content], config: Optional[str]) -> Path:
    """Builds or returns a cached template. The caller holds ``_LOCK``.

    Args:
        base_files: Files of the base commit.
        config: Text of ``.troy-mode/config.toml``, or None for no file.

    Returns:
        Path of the template repository.
    """
    key = repr((sorted(base_files.items()), config))
    if key in _TEMPLATES:
        return _TEMPLATES[key]
    root = Path(_SCRATCH.name) / "templates" / f"t{len(_TEMPLATES)}"
    root.mkdir(parents=True)
    run_git(root, "init", "-q", "-b", "main")
    with open(root / ".git" / "config", "a", encoding="utf-8", newline="\n") as handle:
        handle.write("[core]\n\tautocrlf = false\n[commit]\n\tgpgsign = false\n")
    files = dict(base_files)
    if config is not None:
        files[CONFIG_PATH] = config
    if not files:
        files[".gitkeep"] = ""
    for rel, content in files.items():
        write_file(root, rel, content)
    run_git(root, "add", "-A")
    run_git(root, "commit", "-q", "-m", "Base commit")
    _TEMPLATES[key] = root
    return root


def run_checker(args: Sequence, cwd: Path, env: Optional[dict] = None) -> Outcome:
    """Runs ``troy_check.py`` as a subprocess.

    Args:
        args: Command-line arguments after the script name.
        cwd: Working directory of the process.
        env: Environment. Defaults to ``base_env()``.

    Returns:
        The outcome, with the JSON report parsed when ``--json`` was given.
    """
    proc = subprocess.run(
        [sys.executable, str(CHECKER), *[str(a) for a in args]],
        cwd=str(cwd),
        env=env if env is not None else base_env(),
        capture_output=True,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    report = None
    if "--json" in args:
        try:
            report = json.loads(proc.stdout)
        except ValueError:
            report = None
    return Outcome(proc.returncode, proc.stdout, proc.stderr, report)


class Sandbox:
    """A throwaway git repository with a base commit on ``main``.

    Attributes:
        tmp: Temporary folder that holds the repository and body files.
        root: The repository working tree.
    """

    def __init__(
        self,
        base_files: Optional[Mapping[str, Content]] = None,
        config: Optional[str] = DEFAULT_CONFIG,
    ) -> None:
        """Copies a cached base repository into a new temporary folder.

        Args:
            base_files: Files of the base commit.
            config: Text of ``.troy-mode/config.toml``, or None for no file.
        """
        self._tmp = tempfile.TemporaryDirectory(prefix="troycheck-")
        self.tmp = Path(self._tmp.name)
        self.root = self.tmp / "repo"
        shutil.copytree(_template_repo(base_files or {}, config), self.root)
        self._counter = itertools.count(1)
        self._default_message = False
        self._identity: dict = {}

    def close(self) -> None:
        """Deletes the temporary folder."""
        self._tmp.cleanup()

    def __enter__(self) -> "Sandbox":
        """Returns the sandbox for use in a ``with`` block."""
        return self

    def __exit__(self, *exc_info) -> None:
        """Deletes the sandbox when the ``with`` block ends."""
        self.close()

    def git(
        self, *args: str, author: Optional[str] = None, committer: Optional[str] = None
    ) -> str:
        """Runs git in the repository with optional identity emails."""
        extra = {}
        if author:
            extra["GIT_AUTHOR_EMAIL"] = author
        if committer:
            extra["GIT_COMMITTER_EMAIL"] = committer
        return run_git(self.root, *args, env=base_env(extra))

    def branch(self, name: str = "feature", start: Optional[str] = None) -> None:
        """Creates and checks out a branch."""
        extra = [start] if start else []
        self.git("checkout", "-q", "-b", name, *extra)

    def checkout(self, name: str) -> None:
        """Checks out an existing branch."""
        self.git("checkout", "-q", name)

    def merge(self, name: str) -> None:
        """Merges a branch with a merge commit, never a fast-forward."""
        self.git("merge", "--no-ff", "-q", "-m", f"Merge {name}", name)
        self._default_message = False

    def commit(
        self,
        changes: Optional[Mapping[str, Content]] = None,
        message: Optional[str] = None,
        author: Optional[str] = None,
        committer: Optional[str] = None,
        renames: Sequence = (),
    ) -> None:
        """Applies changes and commits them.

        Args:
            changes: Paths mapped to new content. None content deletes.
            message: Commit message. None means a placeholder that
                ``check_pr`` replaces by the PR title (R01 compares them).
            author: Author email, or None for the test default.
            committer: Committer email, or None for the test default.
            renames: ``(old, new)`` pairs moved with ``git mv`` first.
        """
        for old, new in renames:
            (self.root / new).parent.mkdir(parents=True, exist_ok=True)
            self.git("mv", old, new)
        for rel, content in (changes or {}).items():
            if content is None:
                (self.root / rel).unlink()
            else:
                write_file(self.root, rel, content)
        self.git("add", "-A")
        self._default_message = message is None
        self._identity = {"author": author, "committer": committer}
        text = "Change" if message is None else message
        self.git("commit", "-q", "-m", text, author=author, committer=committer)

    def _titled_head(self, head: str, title: str) -> str:
        """Returns a head whose subject equals the title, without moving refs.

        When the last commit used the placeholder message, a detached commit
        object with the same tree and parent but the title as message is
        created. This keeps shared sandboxes safe for concurrent checks.

        Args:
            head: The head ref the caller asked for.
            title: The PR title.

        Returns:
            The synthetic commit's SHA, or ``head`` when no change is needed.
        """
        if not self._default_message or not title.strip() or "\n" in title:
            return head
        try:
            sha = self.git("rev-parse", f"{head}^{{commit}}").strip()
            parents = self.git("rev-list", "--parents", "-n", "1", sha).split()[1:]
            if len(parents) != 1:
                return head
            tree = self.git("rev-parse", f"{sha}^{{tree}}").strip()
            return self.git(
                "commit-tree", tree, "-p", parents[0], "-m", title, **self._identity
            ).strip()
        except RuntimeError:
            return head

    def run_checker(
        self,
        *args: str,
        env_extra: Optional[Mapping[str, str]] = None,
        cwd: Optional[Path] = None,
    ) -> Outcome:
        """Runs the checker with the isolated environment."""
        return run_checker(args, cwd or self.tmp, base_env(env_extra))

    def check_pr(
        self,
        title: str,
        body: Optional[str] = None,
        base: str = "main",
        head: Optional[str] = "feature",
        json_report: bool = True,
        from_cwd: Optional[str] = None,
        env_extra: Optional[Mapping[str, str]] = None,
        extra_args: Sequence[str] = (),
    ) -> Outcome:
        """Runs ``troy_check.py pr`` on the repository.

        Args:
            title: PR title.
            body: PR description text, written to a file outside the repo.
            base: Value of ``--base``.
            head: Value of ``--head``, or None to leave it out.
            json_report: Whether to pass ``--json``.
            from_cwd: Folder inside the repo to run from without ``--repo``.
            env_extra: Extra environment variables.
            extra_args: Extra command-line arguments.

        Returns:
            The outcome of the run.
        """
        args = ["pr", "--base", base, "--title", title]
        if head:
            args += ["--head", self._titled_head(head, title)]
        if body is not None:
            body_path = self.tmp / f"body{next(self._counter)}.md"
            write_file(self.tmp, body_path.name, body)
            args += ["--body-file", str(body_path)]
        if from_cwd is None:
            args += ["--repo", str(self.root)]
        if json_report:
            args.append("--json")
        cwd = self.root / from_cwd if from_cwd is not None else self.tmp
        return self.run_checker(*args, *extra_args, env_extra=env_extra, cwd=cwd)

    def check_commit(
        self,
        message: Optional[str] = None,
        file_text: Optional[str] = None,
        email: Optional[str] = None,
        json_report: bool = True,
        env_extra: Optional[Mapping[str, str]] = None,
        extra_args: Sequence[str] = (),
    ) -> Outcome:
        """Runs ``troy_check.py commit`` on the repository.

        Args:
            message: Text for ``--message``.
            file_text: Text written to a file and passed as ``--message-file``.
            email: Value of ``--email``.
            json_report: Whether to pass ``--json``.
            env_extra: Extra environment variables.
            extra_args: Extra command-line arguments.

        Returns:
            The outcome of the run.
        """
        args = ["commit", "--repo", str(self.root)]
        if message is not None:
            args += ["--message", message]
        if file_text is not None:
            write_file(self.tmp, "msg.txt", file_text)
            args += ["--message-file", str(self.tmp / "msg.txt")]
        if email is not None:
            args += ["--email", email]
        if json_report:
            args.append("--json")
        return self.run_checker(*args, *extra_args, env_extra=env_extra)


def pr_sandbox(
    changes: Optional[Mapping[str, Content]] = None,
    base_files: Optional[Mapping[str, Content]] = None,
    config: Optional[str] = DEFAULT_CONFIG,
    message: Optional[str] = None,
    author: Optional[str] = None,
    committer: Optional[str] = None,
    renames: Sequence = (),
) -> Sandbox:
    """Builds a sandbox with a ``feature`` branch holding one PR commit.

    Args:
        changes: Paths mapped to new content. None content deletes.
        base_files: Files of the base commit on ``main``.
        config: Text of ``.troy-mode/config.toml``, or None for no file.
        message: Commit message. None means the placeholder that
            ``check_pr`` swaps for the PR title.
        author: Author email of the PR commit.
        committer: Committer email of the PR commit.
        renames: ``(old, new)`` pairs moved before the changes.

    Returns:
        An open sandbox. The caller closes it.
    """
    sandbox = Sandbox(base_files, config)
    try:
        sandbox.branch()
        sandbox.commit(changes, message, author, committer, renames)
    except Exception:
        sandbox.close()
        raise
    return sandbox


def run_pr(
    title: str,
    changes: Optional[Mapping[str, Content]] = None,
    base_files: Optional[Mapping[str, Content]] = None,
    config: Optional[str] = DEFAULT_CONFIG,
    message: Optional[str] = None,
    body: Optional[str] = None,
    author: Optional[str] = None,
    committer: Optional[str] = None,
    renames: Sequence = (),
    **check_kwargs,
) -> Outcome:
    """Builds a one-commit PR in a fresh repository and checks it.

    Args:
        title: PR title.
        changes: Paths mapped to new content. None content deletes.
        base_files: Files of the base commit on ``main``.
        config: Text of ``.troy-mode/config.toml``, or None for no file.
        message: Commit message. Defaults to the PR title (R01).
        body: PR description text.
        author: Author email of the PR commit.
        committer: Committer email of the PR commit.
        renames: ``(old, new)`` pairs moved before the changes.
        **check_kwargs: Passed on to ``Sandbox.check_pr``.

    Returns:
        The outcome of the run.
    """
    subject = title if message is None else message
    sandbox = pr_sandbox(changes, base_files, config, subject, author, committer, renames)
    try:
        return sandbox.check_pr(title, body=body, **check_kwargs)
    finally:
        sandbox.close()
