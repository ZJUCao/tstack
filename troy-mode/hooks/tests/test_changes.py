"""Changes group (F05 design section 6, D41, and 13.1).

For roles, the hook compares the working tree with the role's starting state
after each Bash, PowerShell, or Skill call and at SubagentStop. The tests
make the changes themselves, as a role's Bash command would, and then send
the PostToolUse or SubagentStop input. Each test gets its own repository.

D231 (design 6.1, step 2): the hook no longer deletes a role's record when
it lets the role stop. It sets ``stopped`` and keeps the record, so the
tests that asserted the deletion now assert the kept, stopped record.
"""

import unittest

from hook_helpers import (
    FOO, GP, LOG_TIME, MAIN, HookTestCase, Project, bash_call, post_call, role,
    start_call, stop_call, unique,
)

TEST_BODY = "def test_new():\n    assert True\n"


class ChangeTestCase(HookTestCase):
    """Gives each test a fresh project and a Developer with a unique agent ID."""

    def setUp(self):
        """Builds the project; the test starts the role when it needs to."""
        self.project = Project()
        self.addCleanup(self.project.close)
        self.dev = role("developer", unique("-"))

    def start(self, caller=None):
        """Sends SubagentStart for a role and checks that its record exists."""
        caller = caller or self.dev
        start_call(self.project, caller).run()
        self.assertTrue(self.project.record_path(caller.agent_id).is_file(),
                        f"no start record for {caller.agent_id}")

    def post(self, caller=None, tool="Bash"):
        """Sends PostToolUse for a caller and returns the run."""
        return post_call(self.project, caller or self.dev, tool=tool).run()

    def assert_stopped_record(self, caller=None):
        """Asserts that the role's record is kept with ``stopped`` set (design 6.1, D231)."""
        caller = caller or self.dev
        record = self.project.read_record(caller.agent_id)
        self.assertIsNotNone(record, f"the record of {caller.agent_id} was deleted at the stop")
        self.assertRegex(record.get("stopped") or "", LOG_TIME,
                         f"the stop did not set stopped: {record}")


class PostToolUseTests(ChangeTestCase):
    """Design 6 step 2: changes outside the scope are reported after each call."""

    def test_new_test_file_blocks_and_names_it(self):
        """A Developer that creates a test file through Bash is blocked, told to delete it."""
        self.start()
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_blocked(self.post(), "tests/test_new.py", "delete")

    def test_after_deleting_the_file_nothing_blocks(self):
        """Pair: once the role deletes the file it created, the next call is silent."""
        self.start()
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_blocked(self.post(), "tests/test_new.py")
        self.project.delete("tests/test_new.py")
        self.assert_silent(self.post())

    def test_changed_tracked_file_blocks_with_git_restore(self):
        """A tracked test file the Developer changed is named with git restore -- <path>."""
        self.start()
        self.project.write("tests/test_app.py", TEST_BODY)
        self.assert_blocked(self.post(), "tests/test_app.py", "git restore -- tests/test_app.py")

    def test_after_git_restore_nothing_blocks(self):
        """Pair: after git restore, the next call is silent."""
        self.start()
        self.project.write("tests/test_app.py", TEST_BODY)
        self.assert_blocked(self.post(), "tests/test_app.py")
        self.project.git("restore", "--", "tests/test_app.py")
        self.assert_silent(self.post())

    def test_deleted_tracked_file_blocks(self):
        """A tracked test file the Developer deleted has left the list and is named."""
        self.start()
        self.project.delete("tests/test_app.py")
        self.assert_blocked(self.post(), "tests/test_app.py", "git restore -- tests/test_app.py")

    def test_file_already_changed_is_found_by_its_hash(self):
        """A test file changed before the start and changed again by the role is named."""
        self.project.write("tests/test_app.py", "def test_run():\n    assert 1\n")
        self.start()
        self.assert_silent(self.post(), "unchanged since the start:")
        self.project.write("tests/test_app.py", "def test_run():\n    assert 2\n")
        self.assert_blocked(self.post(), "tests/test_app.py")

    def test_changes_inside_the_scope_are_not_reported(self):
        """Source and dependency changes by the Developer are silent, and never named."""
        self.start()
        self.project.write("src/pkg/new_module.py", "X = 1\n")
        self.project.write("src/pkg/app.py", "def run():\n    return 2\n")
        self.project.write("pyproject.toml", "[project]\nname = \"sample2\"\n")
        self.assert_silent(self.post())
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_blocked(self.post(), "tests/test_new.py",
                            absent=("src/pkg/new_module.py", "src/pkg/app.py", "pyproject.toml"))

    def test_files_in_a_new_folder_are_named_one_by_one(self):
        """New files in a new folder are listed by path, not by folder."""
        self.start()
        self.project.write("tests/unit/test_a.py", TEST_BODY)
        self.project.write("tests/unit/test_b.py", TEST_BODY)
        self.assert_blocked(self.post(), "tests/unit/test_a.py", "tests/unit/test_b.py")

    def test_ignored_files_are_not_changes(self):
        """Ignored build output is not listed by git status, so it is silent."""
        self.start()
        self.project.write("reports/junit.xml", "<testsuites/>\n")
        self.project.write("src/pkg/__pycache__/app.cpython-313.pyc", b"\x00\x01")
        self.assert_silent(self.post())
        self.project.write("docs/requirements.md", "# Changed\n")
        self.assert_blocked(self.post(), "docs/requirements.md", absent=("reports/junit.xml",))

    def test_skill_and_powershell_calls_are_checked(self):
        """PostToolUse for Skill and PowerShell compares the working tree too."""
        self.start()
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_blocked(self.post(tool="Skill"), "tests/test_new.py")
        self.assert_blocked(self.post(tool="PowerShell"), "tests/test_new.py")

    def test_config_change_is_reported(self):
        """A role's change to .troy-mode/ or the rules is outside every scope."""
        self.start()
        self.project.write(".troy-mode/progress.md", "# Progress\n")
        self.project.write("docs/rules.md", "# Rules, changed\n")
        self.assert_blocked(self.post(), ".troy-mode/progress.md", "docs/rules.md")


class ScopeByRoleTests(ChangeTestCase):
    """Change detection uses each role's own scope."""

    def test_code_reviewer_any_change_blocks(self):
        """The Code Reviewer's scope is empty, so a new source file blocks."""
        reviewer = role("code-reviewer", unique("-"))
        self.start(reviewer)
        self.project.write("src/pkg/fix.py", "X = 1\n")
        self.assert_blocked(self.post(reviewer), "src/pkg/fix.py", "delete")

    def test_test_engineer_tests_pass_and_source_blocks(self):
        """The Test Engineer's new test is silent; its source change is named alone."""
        engineer = role("test-engineer", unique("-"))
        self.start(engineer)
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_silent(self.post(engineer))
        self.project.write("src/pkg/app.py", "def run():\n    return 3\n")
        self.assert_blocked(self.post(engineer), "src/pkg/app.py", absent=("tests/test_new.py",))

    def test_architect_pattern_scope(self):
        """The Architect's architecture change is silent; a requirements change blocks."""
        architect = role("architect", unique("-"))
        self.start(architect)
        self.project.write("docs/architecture.md", "# Architecture, changed\n")
        self.project.write("docs/adr/0001-storage.md", "# ADR 1\n")
        self.assert_silent(self.post(architect))
        self.project.write("docs/requirements.md", "# Changed\n")
        self.assert_blocked(self.post(architect), "docs/requirements.md",
                            absent=("docs/architecture.md", "docs/adr/0001-storage.md"))


class OtherCallerTests(ChangeTestCase):
    """Design 6: the main session and other subagents get no change detection."""

    def test_main_session_and_other_subagents_are_not_checked_after_calls(self):
        """PostToolUse for the main session, general-purpose, and troy-foo is silent."""
        self.start()
        self.project.write("tests/test_new.py", TEST_BODY)
        for caller in (MAIN, GP, FOO):
            with self.subTest(caller=caller.label):
                self.assert_silent(self.post(caller))

    def test_the_same_change_blocks_the_developer(self):
        """Pair: on the same working tree, the Developer is blocked."""
        self.start()
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_blocked(self.post(), "tests/test_new.py")

    def test_unknown_troy_name_may_stop(self):
        """SubagentStop for tstack:troy-foo does not block, whatever changed."""
        self.start()
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_not_blocked(stop_call(self.project, FOO).run())
        self.assert_blocked(stop_call(self.project, self.dev).run(), "tests/test_new.py")


class SubagentStopTests(ChangeTestCase):
    """Design 6 step 3: the stop is blocked once, then the role may stop."""

    def test_stop_blocks_once_then_lets_the_role_stop(self):
        """With changes left, the first stop blocks; with stop_hook_active the role stops.

        Planted bugs caught: SubagentStop never blocking (first stop) and
        stop_hook_active ignored (second stop) (13.2).
        """
        self.start()
        self.project.write("tests/test_new.py", TEST_BODY)
        first = stop_call(self.project, self.dev, active=False).run()
        self.assert_blocked(first, "tests/test_new.py", "delete")
        self.assertTrue(self.project.record_path(self.dev.agent_id).is_file(),
                        "the record must stay while the role keeps working")
        record = self.project.read_record(self.dev.agent_id)
        self.assertIsNone(record.get("stopped"), f"a blocked stop set stopped: {record}")
        second = stop_call(self.project, self.dev, active=True).run()
        self.assert_not_blocked(second)
        self.assert_stopped_record()
        self.assert_last_log(self.project, event="SubagentStop", rule="changes",
                             decision="stop", paths=["tests/test_new.py"],
                             agent_id=self.dev.agent_id)

    def test_stop_after_undoing_the_change_is_silent(self):
        """After the role deletes the file, its stop is silent and the record is kept, stopped."""
        self.start()
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_blocked(stop_call(self.project, self.dev).run(), "tests/test_new.py")
        self.project.delete("tests/test_new.py")
        self.assert_silent(stop_call(self.project, self.dev, active=True).run())
        self.assert_stopped_record()

    def test_stop_without_changes_is_silent(self):
        """A role with only in-scope changes stops silently; its record is kept, stopped."""
        self.start()
        self.project.write("src/pkg/app.py", "def run():\n    return 4\n")
        self.assert_silent(stop_call(self.project, self.dev).run())
        self.assert_stopped_record()


class StartRecordTests(ChangeTestCase):
    """Design 6 step 1: the start record, and the record made at the first call."""

    def test_missing_start_record_is_made_at_the_first_call(self):
        """Without SubagentStart, the role's first PreToolUse makes the record."""
        self.project.write("tests/test_dirty_before.py", TEST_BODY)
        self.assertFalse(self.project.record_path(self.dev.agent_id).exists())
        bash_call(self.project, self.dev, "ls").run()
        self.assertTrue(self.project.record_path(self.dev.agent_id).is_file(),
                        "the first PreToolUse call made no record")
        self.project.write("tests/test_new.py", TEST_BODY)
        self.assert_blocked(self.post(), "tests/test_new.py",
                            absent=("tests/test_dirty_before.py",))

    def test_changes_before_the_start_are_not_blamed(self):
        """Paths already changed when the role starts are not reported."""
        self.project.write("tests/test_dirty_before.py", TEST_BODY)
        self.project.write("docs/requirements.md", "# Changed before\n")
        self.start()
        self.assert_silent(self.post())

    def test_records_are_per_agent(self):
        """Two roles get two records, and one role's stop marks only its own stopped."""
        engineer = role("test-engineer", unique("-"))
        self.start()
        self.start(engineer)
        self.assert_silent(stop_call(self.project, engineer).run())
        self.assert_stopped_record(engineer)
        record = self.project.read_record(self.dev.agent_id)
        self.assertIsNotNone(record, "the other role's record is gone")
        self.assertIsNone(record.get("stopped"), f"the other role's record was stopped: {record}")


if __name__ == "__main__":
    unittest.main()
