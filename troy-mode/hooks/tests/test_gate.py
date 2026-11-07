"""Gate group (F05 design section 4 and 13.1).

Outside a troy-mode project every event exits 0 and prints nothing, and
writes nothing. Each "nothing" case is paired with the same input in a
troy-mode project, where the hook answers.
"""

import unittest

from hook_helpers import (
    BASE_FILES, CR, DEV, GP, MAIN, PLUGIN_ROOT, HookTestCase, Project, bash_call,
    has_git_ancestor, plain_folder, post_call, read_call, role, session_call, skill_call,
    start_call, stop_call, unique, write_call, write_file,
)

SKILL_FILE = PLUGIN_ROOT / "skills" / "technical-writing" / "SKILL.md"


def answering_calls(root, agent_suffix):
    """Returns PreToolUse calls that a troy-mode project answers, by name.

    Args:
        root: The project root.
        agent_suffix: Makes the agent IDs unique to one project.

    Returns:
        (name, call) pairs.
    """
    dev = role("developer", agent_suffix)
    return [
        ("role writes a test file", write_call(root, dev, root / "tests" / "test_new.py")),
        ("role edits a test file", write_call(root, dev, root / "tests" / "test_app.py",
                                              tool="Edit")),
        ("role git commit", bash_call(root, dev, "git commit -m 'Add x'")),
        ("main session --no-verify", bash_call(root, MAIN, "git commit --no-verify -m 'Add x'")),
        ("other subagent writes source", write_call(root, GP, root / "src" / "pkg" / "app.py")),
        ("role runs another skill", skill_call(root, CR, "simplify")),
        ("plugin read", read_call(root, DEV, SKILL_FILE)),
    ]


class OutsideTroyModeTests(HookTestCase):
    """In a git repository without .troy-mode/, every event is silent."""

    @classmethod
    def setUpClass(cls):
        """Builds a plain project, a troy-mode project, and the plugin file."""
        write_file(SKILL_FILE.parent, SKILL_FILE.name, "# Technical writing\n")
        cls.plain = Project(troy_mode=False)
        cls.troy = Project()
        cls.addClassCleanup(cls.plain.close)
        cls.addClassCleanup(cls.troy.close)

    def test_pretooluse_calls_are_silent_outside_troy_mode(self):
        """Inputs that a troy-mode project refuses or allows get nothing outside it."""
        for name, call in answering_calls(self.plain.root, "-plain"):
            with self.subTest(case=name):
                self.assert_silent(call.run())

    def test_the_same_pretooluse_calls_are_answered_in_troy_mode(self):
        """Pair of the test above: in a troy-mode project each input gets an answer."""
        for name, call in answering_calls(self.troy.root, "-troy"):
            with self.subTest(case=name):
                out = call.run()
                self.assertEqual(0, out.code, out.describe())
                self.assertIn(out.decision, ("deny", "allow"), out.describe())

    def test_session_start_is_silent_and_leaves_hooks_path_unset(self):
        """SessionStart outside troy-mode prints nothing and does not set core.hooksPath."""
        project = Project(troy_mode=False)
        self.addCleanup(project.close)
        self.assert_silent(session_call(project).run())
        self.assertIsNone(project.hooks_path())

    def test_session_start_sets_hooks_path_in_troy_mode(self):
        """Pair: in a troy-mode project with core.hooksPath unset, SessionStart sets it."""
        project = Project(hooks_on=False)
        self.addCleanup(project.close)
        self.assert_context(session_call(project).run())
        self.assertEqual(".troy-mode/checks/git-hooks", project.hooks_path())

    def test_subagent_events_are_silent_and_write_nothing(self):
        """SubagentStart, PostToolUse, and SubagentStop outside troy-mode: no output, no files."""
        project = Project(troy_mode=False)
        self.addCleanup(project.close)
        dev = role("developer", unique("-"))
        self.assert_silent(start_call(project, dev).run())
        project.write("tests/test_new.py", "def test_x():\n    pass\n")
        self.assert_silent(post_call(project, dev).run())
        self.assert_silent(stop_call(project, dev, active=False).run())
        self.assertFalse((project.git_dir / "troy-mode").exists(),
                         "the hook wrote into .git/troy-mode outside a troy-mode project")

    def test_subagent_events_answer_in_troy_mode(self):
        """Pair: the same sequence in a troy-mode project records, blocks, and blocks the stop."""
        project = Project()
        self.addCleanup(project.close)
        dev = role("developer", unique("-"))
        start_call(project, dev).run()
        self.assertTrue(project.record_path(dev.agent_id).is_file(), "no start record")
        project.write("tests/test_new.py", "def test_x():\n    pass\n")
        self.assert_blocked(post_call(project, dev).run(), "tests/test_new.py")
        self.assert_blocked(stop_call(project, dev, active=False).run(), "tests/test_new.py")

    def test_refusals_outside_troy_mode_write_no_log(self):
        """No log file appears outside troy-mode, whatever the input."""
        project = Project(troy_mode=False)
        self.addCleanup(project.close)
        for _, call in answering_calls(project.root, "-nolog"):
            call.run()
        self.assertFalse(project.log_path.exists())


class NotAGitRepositoryTests(HookTestCase):
    """A folder that is not in a git repository gets nothing, even with .troy-mode/."""

    def test_every_event_is_silent_without_git(self):
        """With .troy-mode/ but no .git anywhere above, every event is silent."""
        files = dict(BASE_FILES)
        files[".troy-mode/config.toml"] = "[attribution]\nmode = \"strict\"\n"
        root = plain_folder(files)
        if has_git_ancestor(root):
            self.skipTest(f"a parent of {root} holds .git")
        for name, call in answering_calls(root, "-nogit"):
            with self.subTest(case=name):
                self.assert_silent(call.run())
        self.assert_silent(session_call(root).run())
        self.assert_silent(start_call(root, DEV).run())
        self.assert_silent(post_call(root, DEV).run())
        self.assert_silent(stop_call(root, DEV).run())


class SubfolderAndWorktreeTests(HookTestCase):
    """The gate walks up from cwd, and a worktree's .git file counts."""

    @classmethod
    def setUpClass(cls):
        """Builds one troy-mode project."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)

    def test_cwd_in_a_subfolder_is_inside_the_project(self):
        """From src/pkg, a role's write to a test file and its git commit are refused."""
        sub = self.project.path("src/pkg")
        out = write_call(self.project, DEV, self.project.path("tests/test_app.py"), cwd=sub).run()
        self.assert_denied(out, "tests/test_app.py", "tests", "needs-answer")
        self.assert_denied(bash_call(self.project, DEV, "git commit -m x", cwd=sub).run(),
                           "git commit")

    def test_cwd_in_a_subfolder_allows_the_scope(self):
        """Pair: from src/pkg, the Developer's write to source is silent."""
        sub = self.project.path("src/pkg")
        out = write_call(self.project, DEV, self.project.path("src/pkg/app.py"), cwd=sub).run()
        self.assert_silent(out)

    def test_linked_worktree_is_a_troy_mode_project(self):
        """In a worktree, where .git is a file, the write scope still applies."""
        worktree = self.project.root.parent / unique("wt")
        self.project.git("worktree", "add", "-q", "-b", unique("wt-branch-"), str(worktree))
        refused = write_call(worktree, DEV, worktree / "tests" / "test_app.py").run()
        allowed = write_call(worktree, DEV, worktree / "src" / "pkg" / "app.py").run()
        self.assertTrue((worktree / ".git").is_file())
        self.assert_denied(refused, "tests/test_app.py", "tests", "needs-answer")
        self.assert_silent(allowed)


if __name__ == "__main__":
    unittest.main()
