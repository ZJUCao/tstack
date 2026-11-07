"""Tests for the git hooks in troy-check's folder (F05 design 8.1, D44, and 13.1).

Each test installs troy-check and git-hooks/ into a temporary project the way
troy-init will (contract section 7): troy_check.py, troycheck/, and
git-hooks/ under .troy-mode/checks/, and core.hooksPath set to
.troy-mode/checks/git-hooks. The commit tests make real commits there.
pre-push is run directly with lines on stdin. No test ever runs git push.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

from helpers import EMAIL, OTHER_EMAIL, base_env, make_config, run_git, write_file

CHECKS = Path(__file__).resolve().parents[1]
GIT_HOOKS = CHECKS / "git-hooks"
REPO = CHECKS.parents[1]
NAMES = ("commit-msg", "pre-commit", "pre-merge-commit", "pre-push")
HOOKS_PATH = ".troy-mode/checks/git-hooks"
ZERO = "0" * 40
TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"
_IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")


def find_sh() -> Optional[str]:
    """Finds a POSIX sh: Git for Windows' sh on Windows, sh elsewhere."""
    if os.name != "nt":
        return shutil.which("sh")
    proc = subprocess.run(["git", "--exec-path"], capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    git_root = Path(proc.stdout.strip()).parents[2]
    for rel in ("usr/bin/sh.exe", "bin/sh.exe"):
        if (git_root / rel).is_file():
            return str(git_root / rel)
    return None


class HookProject:
    """A temporary troy-mode project with troy-check and the git hooks turned on.

    Attributes:
        root: The repository's working tree.
        env: The environment git runs in, with TROY_MODE_PYTHON set.
    """

    def __init__(self) -> None:
        """Builds the project with one commit on main, made before the hooks are on."""
        self._tmp = tempfile.TemporaryDirectory(prefix="troyhooks-", ignore_cleanup_errors=True)
        self.root = Path(self._tmp.name).resolve() / "repo"
        self.root.mkdir()
        self.env = base_env({"TROY_MODE_PYTHON": sys.executable})
        self.git("init", "-q", "-b", "main")
        with open(self.root / ".git" / "config", "a", encoding="utf-8", newline="\n") as handle:
            handle.write("[core]\n\tautocrlf = false\n[commit]\n\tgpgsign = false\n")
        checks = self.root / ".troy-mode" / "checks"
        shutil.copytree(CHECKS / "troycheck", checks / "troycheck", ignore=_IGNORED)
        shutil.copy2(CHECKS / "troy_check.py", checks / "troy_check.py")
        shutil.copytree(GIT_HOOKS, checks / "git-hooks", ignore=_IGNORED)
        for name in NAMES:
            (checks / "git-hooks" / name).chmod(0o755)
        write_file(self.root, ".troy-mode/config.toml", make_config(email=EMAIL))
        write_file(self.root, "README.md", "# Sample\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Set up the project")
        self.git("config", "core.hooksPath", HOOKS_PATH)

    def close(self) -> None:
        """Deletes the project."""
        self._tmp.cleanup()

    def git(self, *args: str, extra: Optional[dict] = None,
            check: bool = True) -> subprocess.CompletedProcess:
        """Runs git in the project.

        Args:
            *args: Arguments after git.
            extra: Environment variables to add.
            check: Raise when git fails.

        Returns:
            The finished process.
        """
        env = dict(self.env, **(extra or {}))
        proc = subprocess.run(["git", *args], cwd=str(self.root), env=env, capture_output=True,
                              encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                              timeout=120, check=False)
        if check and proc.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}")
        return proc

    def head(self, ref: str = "HEAD") -> str:
        """Returns the commit a ref names."""
        return self.git("rev-parse", ref).stdout.strip()

    def commit(self, rel: str, message: str, *extra_args: str,
               env: Optional[dict] = None) -> subprocess.CompletedProcess:
        """Writes a file, stages it, and commits it, returning git's result."""
        write_file(self.root, rel, f"{rel}\n")
        self.git("add", rel)
        return self.git("commit", "-q", "-m", message, *extra_args, extra=env, check=False)


def describe(proc: subprocess.CompletedProcess) -> str:
    """Returns a git run's output for assertion messages."""
    return f"\nexit={proc.returncode}\n--stdout--\n{proc.stdout}\n--stderr--\n{proc.stderr}"


class CommitHookTests(unittest.TestCase):
    """pre-commit, commit-msg, and pre-merge-commit with real commits."""

    def setUp(self) -> None:
        """Builds a fresh project for each test."""
        self.project = HookProject()
        self.addCleanup(self.project.close)

    def assert_refused(self, proc: subprocess.CompletedProcess, before: str) -> None:
        """Asserts that git failed and HEAD did not move."""
        self.assertNotEqual(0, proc.returncode, "the commit was not refused" + describe(proc))
        self.assertEqual(before, self.project.head(), "HEAD moved")

    def assert_made(self, proc: subprocess.CompletedProcess, before: str) -> None:
        """Asserts that git succeeded and HEAD moved."""
        self.assertEqual(0, proc.returncode, "the commit was refused" + describe(proc))
        self.assertNotEqual(before, self.project.head(), "HEAD did not move")

    def test_commit_on_main_is_refused(self) -> None:
        """pre-commit refuses a commit while the current branch is main (R21)."""
        before = self.project.head()
        self.assert_refused(self.project.commit("src/a.py", "Add a"), before)

    def test_good_commit_on_a_branch_passes(self) -> None:
        """Pair: on a branch, a clean message by the configured email is committed."""
        self.project.git("checkout", "-q", "-b", "feature")
        before = self.project.head()
        self.assert_made(self.project.commit("src/a.py", "Add a"), before)

    def test_attribution_trailer_is_refused(self) -> None:
        """commit-msg refuses a Co-Authored-By: Claude trailer (R19)."""
        self.project.git("checkout", "-q", "-b", "feature")
        before = self.project.head()
        proc = self.project.commit("src/a.py", f"Add a\n\n{TRAILER}")
        self.assert_refused(proc, before)

    def test_wrong_author_email_is_refused(self) -> None:
        """commit-msg refuses an --author email other than [identity] commit_email (R19)."""
        self.project.git("checkout", "-q", "-b", "feature")
        before = self.project.head()
        proc = self.project.commit("src/a.py", "Add a", "--author", f"Someone <{OTHER_EMAIL}>")
        self.assert_refused(proc, before)

    def test_commit_msg_without_python_refuses(self) -> None:
        """commit-msg refuses the commit when the interpreter it picks does not exist."""
        self.project.git("checkout", "-q", "-b", "feature")
        before = self.project.head()
        missing = str(self.project.root.parent / "no-python" / "python")
        proc = self.project.commit("src/a.py", "Add a", env={"TROY_MODE_PYTHON": missing})
        self.assert_refused(proc, before)

    def test_merge_commit_on_main_is_refused(self) -> None:
        """pre-merge-commit refuses a merge commit while the current branch is main (R21)."""
        self.project.git("checkout", "-q", "-b", "topic")
        main = self.project.head("main")
        self.assert_made(self.project.commit("src/topic.py", "Add topic"), main)
        self.project.git("checkout", "-q", "main")
        before = self.project.head()
        proc = self.project.git("merge", "--no-ff", "-m", "Merge topic", "topic", check=False)
        self.assert_refused(proc, before)

    def test_merge_commit_on_a_branch_passes(self) -> None:
        """Pair: the same merge commit on another branch is made, with two parents."""
        self.project.git("checkout", "-q", "-b", "topic")
        self.project.commit("src/topic.py", "Add topic")
        self.project.git("checkout", "-q", "-b", "feature", "main")
        before = self.project.head()
        proc = self.project.git("merge", "--no-ff", "-m", "Merge topic", "topic", check=False)
        self.assert_made(proc, before)
        parents = self.project.git("rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
        self.assertEqual(3, len(parents))


class PrePushTests(unittest.TestCase):
    """pre-push run directly with the lines git passes on stdin."""

    @classmethod
    def setUpClass(cls) -> None:
        """Builds one project and finds sh."""
        cls.sh = find_sh()
        if cls.sh is None:
            raise unittest.SkipTest("no POSIX sh found")
        cls.project = HookProject()
        cls.addClassCleanup(cls.project.close)
        cls.sha = cls.project.head()

    def push(self, *lines: str) -> subprocess.CompletedProcess:
        """Runs pre-push with the given <local ref> <local sha> <remote ref> <remote sha> lines."""
        hook = self.project.root / HOOKS_PATH / "pre-push"
        return subprocess.run([self.sh, hook.as_posix(), "origin", "https://example.test/r.git"],
                              input="".join(line + "\n" for line in lines),
                              cwd=str(self.project.root), env=self.project.env,
                              capture_output=True, encoding="utf-8", errors="replace",
                              timeout=60, check=False)

    def test_updating_remote_main_is_refused(self) -> None:
        """A line whose remote ref is refs/heads/main is refused, created or updated."""
        s = self.sha
        for line in (f"refs/heads/feature {s} refs/heads/main {s}",
                     f"refs/heads/feature {s} refs/heads/main {ZERO}",
                     f"HEAD {s} refs/heads/main {s}"):
            with self.subTest(line=line):
                self.assertNotEqual(0, self.push(line).returncode)

    def test_deleting_remote_main_is_refused(self) -> None:
        """A deletion of refs/heads/main on the remote is refused."""
        proc = self.push(f"(delete) {ZERO} refs/heads/main {self.sha}")
        self.assertNotEqual(0, proc.returncode, describe(proc))

    def test_main_among_several_lines_is_refused(self) -> None:
        """One main line among branch lines is enough to refuse."""
        s = self.sha
        proc = self.push(f"refs/heads/feature {s} refs/heads/feature {ZERO}",
                         f"refs/heads/feature {s} refs/heads/main {s}")
        self.assertNotEqual(0, proc.returncode, describe(proc))

    def test_branch_and_tag_pass(self) -> None:
        """Pair: a branch, a tag, and a branch whose name starts with main pass."""
        s = self.sha
        for line in (f"refs/heads/feature {s} refs/heads/feature {ZERO}",
                     f"refs/tags/v1.0 {s} refs/tags/v1.0 {ZERO}",
                     f"refs/heads/mainline {s} refs/heads/mainline {ZERO}",
                     f"(delete) {ZERO} refs/heads/old-feature {s}"):
            with self.subTest(line=line):
                proc = self.push(line)
                self.assertEqual(0, proc.returncode, describe(proc))

    def test_local_main_pushed_to_another_branch_passes(self) -> None:
        """The remote ref decides: local main pushed to refs/heads/backup passes.

        Planted bug caught: pre-push reading the local ref in place of the
        remote one (13.2).
        """
        proc = self.push(f"refs/heads/main {self.sha} refs/heads/backup {ZERO}")
        self.assertEqual(0, proc.returncode, describe(proc))

    def test_nothing_to_push_passes(self) -> None:
        """Empty standard input passes."""
        proc = self.push()
        self.assertEqual(0, proc.returncode, describe(proc))


class HookFileTests(unittest.TestCase):
    """The git hook files themselves (design 2 and contract 7)."""

    def test_hooks_are_executable_in_the_index(self) -> None:
        """Each of the four hooks has mode 100755 in troy-pstack's git index."""
        out = run_git(REPO, "ls-files", "-s", "--", "troy-mode/checks/git-hooks")
        modes = {}
        for line in out.splitlines():
            meta, path = line.split("\t", 1)
            modes[path.rsplit("/", 1)[-1]] = meta.split()[0]
        for name in NAMES:
            with self.subTest(hook=name):
                self.assertEqual("100755", modes.get(name), f"index entries: {out}")

    def test_hooks_are_posix_sh_with_lf_line_endings(self) -> None:
        """Each hook starts with #!/bin/sh and holds no CR byte."""
        for name in NAMES:
            with self.subTest(hook=name):
                data = (GIT_HOOKS / name).read_bytes()
                self.assertEqual(b"#!/bin/sh", data.split(b"\n", 1)[0])
                self.assertNotIn(b"\r", data)


if __name__ == "__main__":
    unittest.main()
