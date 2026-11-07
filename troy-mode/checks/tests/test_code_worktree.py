"""Tests for ``troy-check code --worktree`` (F07 design 12, D60).

``--worktree`` checks the working tree as if it were committed on top of
HEAD, and leaves the index, the refs, the working tree, and the stash as they
were. Planted bug of F07 design 14.2 caught here: "``--worktree`` leaving a
staged file in the index": ``WorktreeTests.test_index_is_unchanged``.
"""

import os
import unittest
from pathlib import Path

from code_helpers import check_code
from helpers import CheckTestCase, Sandbox, make_config, run_checker
from reports import PASS, junit, tests

TITLE = "[F04 5/6 impl] Count words in files"
CONFIG = make_config(extra='[lang]\nname = "python"\nsource_roots = ["src"]\n')
DOCUMENTED = '"""Module."""\n\n\ndef {name}():\n    """Does it."""\n    return 1\n'
UNDOCUMENTED = '"""Module."""\n\n\ndef {name}():\n    return 1\n'
BASE = {
    ".gitignore": "build/\n",
    "src/pkg/__init__.py": '"""Package."""\n',
    "src/pkg/keep.py": DOCUMENTED.format(name="keep"),
    "src/pkg/old.py": DOCUMENTED.format(name="old"),
    "tests/test_pkg.py": '"""Tests."""\n\n\ndef test_f04_t01_counts():\n    """Counts."""\n',
}
FRESH = "src/pkg/fresh.py"
STAGED = "src/pkg/staged.py"
KEEP = "src/pkg/keep.py"
OLD = "src/pkg/old.py"
IGNORED = "build/gen.py"
JUNIT = junit(tests(PASS, "test_f04_t01_counts", file="tests/test_pkg.py"))


def tree_files(root) -> dict:
    """Every working-tree file outside ``.git``: path with ``/`` mapped to bytes."""
    found = {}
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in names:
            path = Path(folder) / name
            found[path.relative_to(root).as_posix()] = path.read_bytes()
    return found


def git_state(sandbox: Sandbox) -> dict:
    """Everything ``--worktree`` must leave as it was.

    Args:
        sandbox: The repository.

    Returns:
        The index, staged changes, refs, HEAD, reflog, status, stash, and files.
    """
    return {
        "index": sandbox.git("ls-files", "--stage"),
        "staged": sandbox.git("diff", "--cached", "--name-status"),
        "refs": sandbox.git("for-each-ref"),
        "head": sandbox.git("rev-parse", "HEAD"),
        "branch": sandbox.git("symbolic-ref", "HEAD"),
        "reflog": sandbox.git("reflog", "--format=%H %gs"),
        "status": sandbox.git("status", "--porcelain=v1", "--untracked-files=all"),
        "stash": sandbox.git("stash", "list"),
        "files": tree_files(sandbox.root),
    }


class WorktreeTests(CheckTestCase):
    """A working tree with a staged, an untracked, a changed, a deleted, and an ignored file."""

    @classmethod
    def setUpClass(cls):
        """Checks the working tree, then commits the same changes and checks the commit."""
        sandbox = cls.sb = Sandbox(BASE, CONFIG)
        cls.addClassCleanup(sandbox.close)
        sandbox.branch("feature")
        sandbox.commit({"src/pkg/first.py": DOCUMENTED.format(name="first")}, message=TITLE)
        (sandbox.root / KEEP).write_bytes(
            (DOCUMENTED.format(name="keep") + "\n# stashed work\n").encode("utf-8"))
        sandbox.git("stash", "push", "-q", "-m", "earlier work")
        files = {STAGED: UNDOCUMENTED.format(name="staged"),
                 FRESH: UNDOCUMENTED.format(name="fresh"),
                 KEEP: DOCUMENTED.format(name="keep") + "\n\ndef added():\n    return 2\n",
                 IGNORED: UNDOCUMENTED.format(name="generated")}
        for rel, text in files.items():
            path = sandbox.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
        sandbox.git("add", "--", STAGED)
        (sandbox.root / OLD).unlink()
        cls.junit_path = sandbox.tmp / "junit.xml"
        cls.junit_path.write_bytes(JUNIT.encode("utf-8"))
        cls.before = git_state(sandbox)
        cls.out = check_code(sandbox, TITLE, junit=[cls.junit_path], head=None,
                             extra_args=["--worktree"])
        cls.after = git_state(sandbox)
        sandbox.git("add", "-A")
        sandbox.git("commit", "-q", "-m", TITLE)
        cls.real = check_code(sandbox, TITLE, junit=[cls.junit_path], head="HEAD")

    def test_new_and_staged_files_are_checked(self):
        """R05 names the untracked, the staged, and the changed file: nothing else."""
        self.assertEqual(self.out.report["command"], "code", self.out.describe())
        self.assert_rule(self.out, "R05", "fail")
        self.assert_paths(self.out, "R05", [FRESH, KEEP, STAGED])
        self.assert_exit(self.out, 1)

    def test_ignored_files_are_skipped(self):
        """No rule names the ignored file."""
        for entry in self.out.report["results"]:
            for detail in entry.get("details") or []:
                self.assertNotEqual(detail.get("path"), IGNORED, entry)

    def test_results_equal_those_of_a_real_commit(self):
        """The same results and exit code as committing with ``git add -A`` and checking HEAD."""
        self.assertIsInstance(self.real.report, dict, self.real.describe())
        self.assertEqual(self.out.report["results"], self.real.report["results"])
        self.assertEqual(self.out.report["title"], self.real.report["title"])
        self.assertEqual(self.out.code, self.real.code)

    def test_index_is_unchanged(self):
        """Planted bug "leaving a staged file in the index": the index is as it was."""
        self.assertEqual(self.after["index"], self.before["index"])
        self.assertEqual(self.after["staged"], self.before["staged"])
        self.assertNotIn(FRESH, self.after["index"])

    def test_refs_and_head_are_unchanged(self):
        """No ref moved, HEAD is the same branch and commit, and the reflog has no new entry."""
        for key in ("refs", "head", "branch", "reflog"):
            with self.subTest(key=key):
                self.assertEqual(self.after[key], self.before[key])

    def test_working_tree_is_unchanged(self):
        """A staged, an untracked, a changed, and a deleted file stay so, byte for byte."""
        status = self.after["status"].splitlines()
        for line in (f"A  {STAGED}", f"?? {FRESH}", f" M {KEEP}", f" D {OLD}"):
            self.assertIn(line, status)
        self.assertEqual(self.after["status"], self.before["status"])
        self.assertEqual(self.after["files"], self.before["files"])
        self.assertIn(IGNORED, self.after["files"])

    def test_stash_is_unchanged(self):
        """The stash keeps its one earlier entry."""
        self.assertEqual(len(self.after["stash"].splitlines()), 1)
        self.assertEqual(self.after["stash"], self.before["stash"])


class WorktreeOptionTests(CheckTestCase):
    """Where ``--worktree`` is not allowed."""

    @classmethod
    def setUpClass(cls):
        """A repository with one commit on ``feature``."""
        cls.sb = Sandbox(BASE, CONFIG)
        cls.addClassCleanup(cls.sb.close)
        cls.sb.branch("feature")
        cls.sb.commit({"src/pkg/first.py": DOCUMENTED.format(name="first")}, message=TITLE)

    def test_worktree_with_head_exits_two(self):
        """``--worktree`` and ``--head`` together exit 2."""
        out = check_code(self.sb, TITLE, head="feature", extra_args=["--worktree"])
        self.assert_exit(out, 2)

    def test_worktree_alone_runs(self):
        """``--worktree`` without ``--head`` runs on a clean tree and passes."""
        out = check_code(self.sb, TITLE, head=None, extra_args=["--worktree"])
        self.assert_clean(out)

    def test_pr_and_commit_do_not_know_the_option(self):
        """``pr --worktree`` and ``commit --worktree`` are unknown options."""
        root = str(self.sb.root)
        pr_out = run_checker(["pr", "--base", "main", "--title", TITLE, "--repo", root,
                              "--worktree"], self.sb.tmp)
        commit_out = run_checker(["commit", "--message", "Fix", "--repo", root, "--worktree"],
                                 self.sb.tmp)
        self.assert_exit(pr_out, 2)
        self.assert_exit(commit_out, 2)


if __name__ == "__main__":
    unittest.main()
