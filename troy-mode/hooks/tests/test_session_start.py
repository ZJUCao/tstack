"""SessionStart group (F05 design sections 3 and 8.1, and 13.1).

SessionStart turns the project's git hooks on when core.hooksPath is unset,
leaves another value and reports it, reports missing hook files, and removes
role records and log lines older than a day (records by file time, log lines
by their time field, contract section 4).
"""

import json
import os
import time
import unittest
from datetime import datetime, timedelta, timezone

from hook_helpers import (
    GIT_HOOK_NAMES, HOOKS_PATH, HookTestCase, Project, session_call, write_file,
)

DAY = 24 * 60 * 60


def log_line(age_seconds, agent_id):
    """Returns one log line whose time is the given number of seconds ago."""
    moment = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return json.dumps({"time": moment.strftime("%Y-%m-%dT%H:%M:%SZ"), "session": "s1",
                       "agent_id": agent_id, "agent_type": "tstack:troy-developer",
                       "event": "PreToolUse", "tool": "Write", "rule": "scope",
                       "paths": ["tests/test_app.py"], "subcommand": None, "decision": "deny"})


class HooksPathTests(HookTestCase):
    """Design 8.1: SessionStart and core.hooksPath."""

    def test_unset_hooks_path_is_set_and_reported(self):
        """With core.hooksPath unset, it becomes .troy-mode/checks/git-hooks, with a notice."""
        project = Project(hooks_on=False)
        self.addCleanup(project.close)
        self.assertIsNone(project.hooks_path())
        self.assert_context(session_call(project).run())
        self.assertEqual(HOOKS_PATH, project.hooks_path())

    def test_set_from_a_subfolder(self):
        """cwd in a subfolder of the project still sets the project's core.hooksPath."""
        project = Project(hooks_on=False)
        self.addCleanup(project.close)
        self.assert_context(session_call(project, cwd=project.path("src/pkg")).run())
        self.assertEqual(HOOKS_PATH, project.hooks_path())

    def test_another_value_is_left_and_reported(self):
        """With core.hooksPath set to another folder, it stays, and a notice is printed."""
        project = Project(hooks_on=False)
        self.addCleanup(project.close)
        project.git("config", "core.hooksPath", ".githooks")
        self.assert_context(session_call(project).run())
        self.assertEqual(".githooks", project.hooks_path())

    def test_missing_hook_files_are_reported(self):
        """With core.hooksPath right but the hook files gone, a notice is printed."""
        project = Project()
        self.addCleanup(project.close)
        for name in GIT_HOOK_NAMES:
            project.delete(f"{HOOKS_PATH}/{name}")
        self.assert_context(session_call(project).run())
        self.assertEqual(HOOKS_PATH, project.hooks_path())

    def test_hooks_already_on_is_silent(self):
        """Pair: with core.hooksPath right and the files present, nothing is printed."""
        project = Project()
        self.addCleanup(project.close)
        self.assert_silent(session_call(project).run())
        self.assertEqual(HOOKS_PATH, project.hooks_path())


class CleanupTests(HookTestCase):
    """Design 3: records and log lines older than a day are removed."""

    def test_old_records_are_removed_and_recent_ones_kept(self):
        """A record two days old is deleted; one an hour old stays."""
        project = Project()
        self.addCleanup(project.close)
        old = write_file(project.root, ".git/troy-mode/agents/agent-old.json", "{}\n")
        recent = write_file(project.root, ".git/troy-mode/agents/agent-recent.json", "{}\n")
        now = time.time()
        os.utime(old, (now - 2 * DAY, now - 2 * DAY))
        os.utime(recent, (now - 3600, now - 3600))
        session_call(project).run()
        self.assertFalse(old.exists(), "a record older than a day was kept")
        self.assertTrue(recent.exists(), "a recent record was removed")

    def test_old_log_lines_are_removed_and_recent_ones_kept(self):
        """Log lines older than a day go; a line an hour old and one from now stay, in order."""
        project = Project()
        self.addCleanup(project.close)
        lines = [log_line(3 * DAY, "agent-oldest"), log_line(DAY + 600, "agent-old"),
                 log_line(3600, "agent-recent"), log_line(0, "agent-now")]
        write_file(project.root, ".git/troy-mode/hooks.log", "\n".join(lines) + "\n")
        session_call(project).run()
        kept = [line["agent_id"] for line in project.log_lines()]
        self.assertEqual(["agent-recent", "agent-now"], kept)

    def test_cleanup_happens_while_hooks_are_set(self):
        """Cleanup also runs when SessionStart sets core.hooksPath in the same call."""
        project = Project(hooks_on=False)
        self.addCleanup(project.close)
        old = write_file(project.root, ".git/troy-mode/agents/agent-old.json", "{}\n")
        now = time.time()
        os.utime(old, (now - 2 * DAY, now - 2 * DAY))
        self.assert_context(session_call(project).run())
        self.assertFalse(old.exists())


if __name__ == "__main__":
    unittest.main()
