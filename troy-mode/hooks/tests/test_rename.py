"""Rename group (F19 design sections 3, 5.1, and 11.1): the roles are tstack:troy-<role>.

F19 renames the plugin to tstack, so its roles reach the hooks as
``tstack:troy-<role>``. The same names under the plugin's old prefix are now
unknown subagents: read-only, with no write scope, and not checked after
their calls (F05 design section 4). Probe 4 of F19 design section 3 is the
first test here: the Architect writing docs/architecture.md.

The tests are black-box through ``troy_hook.py``, except ScopesModuleTests,
which reads ``troyhook.scopes.PLUGIN_PREFIX`` and ``ROLE_PATTERN`` (F19 design
5.1; F05 contract 5 lets the tests import troyhook.scopes).

F19 planted bugs (design 11.3) caught in this suite:

- ROLE_PATTERN still on the old prefix:
  RoleNameTests.test_probe_4_the_architecture_is_written_only_under_tstack,
  test_old_prefix_roles_may_not_write_in_their_old_scopes, and
  ScopesModuleTests.test_role_pattern_matches_exactly_the_six_tstack_roles;
  also test_callers.CallerTests.test_each_role_is_recognized_by_its_scope and
  test_paths.RoleMatrixTests.test_each_role_against_each_path_class_and_pattern.
- One SubagentStart or SubagentStop matcher left on the old prefix:
  test_hooks_json.HooksJsonTests.test_matchers_and_if_rules,
  test_subagent_matchers_match_only_tstack_roles, and
  test_no_entry_names_the_old_plugin.
- The Read if rule left: test_hooks_json.HooksJsonTests.test_pretooluse_scope_and_read_entries
  and test_no_entry_names_the_old_plugin.
- The guard's message pointing to the old command: test_mode_guard.MessageTests
  and ModuleTests.test_plugin_prefix_is_tstack.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -p "test_rename.py" -v
"""

import importlib
import re
import sys
import unittest

from hook_helpers import (
    CHECKS, HOOKS_DIR, OLD_PREFIX, ROLE_NAMES, HookTestCase, Project, bash_call, old_role,
    post_call, role, run_many, start_call, stop_call, unique, write_call,
)

TEST_BODY = "def test_new():\n    assert True\n"

# For each role with a write scope: a tracked path in that scope and its class.
IN_SCOPE = {
    "architect": ("docs/architecture.md", "docs"),
    "interface-designer": ("docs/features/F01/design.md", "docs"),
    "test-manager": ("docs/features/F01/test-plan.md", "docs"),
    "developer": ("src/pkg/app.py", "source"),
    "test-engineer": ("tests/test_app.py", "tests"),
}


def scopes_module():
    """Imports troyhook.scopes with troy-mode/hooks and troy-mode/checks on sys.path."""
    for folder in (CHECKS, HOOKS_DIR):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    return importlib.import_module("troyhook.scopes")


class RoleNameTests(HookTestCase):
    """tstack:troy-<role> has its write scope; the old-prefix name has none."""

    @classmethod
    def setUpClass(cls):
        """Builds one project and starts every tstack role once."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        run_many([start_call(cls.project, role(name)) for name in ROLE_NAMES])

    def test_probe_4_the_architecture_is_written_only_under_tstack(self):
        """Probe 4: a Write of docs/architecture.md is allowed for tstack:troy-architect.

        The same Write from the old-prefix Architect is refused as outside
        its write scope, because that name is now an unknown subagent.
        """
        path = self.project.path("docs/architecture.md")
        new, old = run_many([write_call(self.project, role("architect"), path),
                             write_call(self.project, old_role("architect"), path)])
        self.assert_silent(new, "tstack:troy-architect writing docs/architecture.md:")
        self.assert_denied(old, "docs/architecture.md", "docs", "needs-answer",
                           msg="the old-prefix Architect writing docs/architecture.md:")

    def test_old_prefix_roles_may_not_write_in_their_old_scopes(self):
        """Each role with a scope writes its path as tstack:, and is refused with the old prefix."""
        calls, cases = [], []
        for name, (rel, cls) in IN_SCOPE.items():
            calls += [write_call(self.project, role(name), self.project.path(rel)),
                      write_call(self.project, old_role(name), self.project.path(rel))]
            cases.append((name, rel, cls))
        outs = run_many(calls)
        for index, (name, rel, cls) in enumerate(cases):
            with self.subTest(role=name):
                self.assert_silent(outs[2 * index], f"tstack:troy-{name} writing {rel}:")
                self.assert_denied(outs[2 * index + 1], rel, cls, "needs-answer",
                                   msg=f"old-prefix {name} writing {rel}:")

    def test_old_prefix_roles_may_write_ignored_files_and_run_read_only_git(self):
        """Pair: as other subagents, the old-prefix roles may write ignored files and git status.

        They are still refused git commit, which only the main session runs.
        """
        calls = []
        for name in ROLE_NAMES:
            caller = old_role(name)
            calls += [write_call(self.project, caller, self.project.path("reports/out.txt")),
                      bash_call(self.project, caller, "git status"),
                      bash_call(self.project, caller, "git commit -m x")]
        outs = run_many(calls)
        for index, name in enumerate(ROLE_NAMES):
            with self.subTest(role=name):
                self.assert_silent(outs[3 * index], "writing an ignored file:")
                self.assert_silent(outs[3 * index + 1], "git status:")
                self.assert_denied(outs[3 * index + 2], "git commit", "main session")


class OldPrefixChangeTests(HookTestCase):
    """The old-prefix Developer is not checked after its calls, as an unknown subagent."""

    def setUp(self):
        """Builds a fresh project and a started tstack Developer with a unique agent ID."""
        self.project = Project()
        self.addCleanup(self.project.close)
        self.dev = role("developer", unique("-"))
        start_call(self.project, self.dev).run()
        self.assertTrue(self.project.record_path(self.dev.agent_id).is_file(),
                        f"no start record for {self.dev.agent_id}")

    def test_post_tool_use_checks_only_the_tstack_developer(self):
        """A new test file: the old-prefix Developer's PostToolUse is silent, tstack's blocks."""
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_silent(post_call(self.project, old_role("developer", unique("-"))).run())
        self.assert_blocked(post_call(self.project, self.dev).run(), "tests/test_new.py")

    def test_subagent_stop_blocks_only_the_tstack_developer(self):
        """A new test file: the old-prefix Developer may stop, the tstack Developer is blocked."""
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_not_blocked(stop_call(self.project, old_role("developer", unique("-"))).run())
        self.assert_blocked(stop_call(self.project, self.dev).run(), "tests/test_new.py")


class ScopesModuleTests(unittest.TestCase):
    """troyhook.scopes names the plugin once (F19 design 5.1)."""

    @classmethod
    def setUpClass(cls):
        """Imports troyhook.scopes once."""
        cls.scopes = scopes_module()

    def test_plugin_prefix_is_tstack(self):
        """PLUGIN_PREFIX is "tstack:"."""
        self.assertEqual("tstack:", self.scopes.PLUGIN_PREFIX)

    def test_role_pattern_matches_exactly_the_six_tstack_roles(self):
        """ROLE_PATTERN fully matches tstack:troy-<role> for the six roles and nothing else.

        The old-prefix names, the impostors of F19 design 11.1, an unknown
        troy- name, and a name without a prefix do not match (design 5.1: the
        role match stays exact).
        """
        pattern = self.scopes.ROLE_PATTERN
        for name in ROLE_NAMES:
            with self.subTest(role=name):
                self.assertIsNotNone(re.fullmatch(pattern, f"tstack:troy-{name}"))
        others = [OLD_PREFIX + f"troy-{name}" for name in ROLE_NAMES] + [
            "xtstack:troy-developer", "tstack:troy-developer-2", "my-tstack:troy-test-engineer",
            "tstack:troy-foo", "troy-developer", "x:troy-developer", "tstack:poteto-agent"]
        for name in others:
            with self.subTest(other=name):
                self.assertIsNone(re.fullmatch(pattern, name), f"{name} matches ROLE_PATTERN")


if __name__ == "__main__":
    unittest.main()
