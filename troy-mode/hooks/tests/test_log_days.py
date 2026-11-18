"""Log days group (F05 design sections 3, 10, and 13.1, decision D219).

SessionStart keeps hooks.log lines for ``[hooks] log_days`` days of the
committed ``.troy-mode/config.toml``, 30 when the key, the table, or the file
is missing. A line whose ``time`` lies more than ``log_days`` times 24 hours
before now is removed, an unreadable line is removed, and the other lines
stay in their order. Role records are still removed when their file is more
than one day old, whatever ``log_days`` says. With an invalid committed
config, SessionStart removes no log line, still removes old records, still
turns on the git hooks, exits 0, and prints ``additionalContext`` that names
``hooks.log``.

Ages keep a margin of about an hour from each boundary, never the exact
second. The troy-check side (``parse_config`` and ``config.default.toml``) is
in ``troy-mode/checks/tests/test_config_f05.py``.

Planted bugs (design 13.2, D219) and the tests that catch them:

- The cutoff one day off:
  ConfiguredDaysTests.test_seven_days_keeps_an_hour_under_and_removes_an_hour_over
  (both directions); DefaultDaysTests.test_default_boundary_is_30_days and
  test_no_hooks_table_keeps_29_days_and_removes_31 (a day short).
- The default ignored, so only a day is kept:
  DefaultDaysTests (every test); ConfigFromHeadTests
  test_uncommitted_log_days_edit_is_not_read.
- Role records kept for log_days:
  RecordTests.test_old_records_are_removed_whatever_log_days_says.
- A log_days of 0 accepted:
  InvalidConfigTests.test_invalid_config_removes_no_log_line (0 days would
  remove every line); RoleCallTests.test_bad_log_days_refuses_a_role_write.
- The config read from the working tree: ConfigFromHeadTests (every test but
  test_new_commit_of_log_days_is_read).
- An invalid config stopping SessionStart before it turns on the git hooks:
  InvalidConfigTests.test_invalid_config_still_sets_an_unset_hooks_path and
  test_invalid_config_still_removes_old_records.
"""

import json
import os
import time
import unittest
from datetime import datetime, timedelta, timezone

from hook_helpers import (
    CONFIG_PATH, DEV, HOOKS_PATH, INVALID_CONFIG, HookTestCase, Project, make_config, run_many,
    session_call, write_call, write_file,
)

HOUR = 60 * 60
DAY = 24 * HOUR

# Invalid committed configs: each D219 config error, and one unrelated to [hooks].
INVALID = {
    "log_days 0": "[hooks]\nlog_days = 0\n",
    "log_days -1": "[hooks]\nlog_days = -1\n",
    "log_days true": "[hooks]\nlog_days = true\n",
    "log_days false": "[hooks]\nlog_days = false\n",
    "log_days 1.5": "[hooks]\nlog_days = 1.5\n",
    "log_days a string": '[hooks]\nlog_days = "30"\n',
    "unknown key in [hooks]": "[hooks]\nlog_days = 30\nkeep_records = 5\n",
    "unknown table": INVALID_CONFIG,
}


def log_line(age_seconds, agent_id):
    """Returns one log line whose time is the given number of seconds ago."""
    moment = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return json.dumps({"time": moment.strftime("%Y-%m-%dT%H:%M:%SZ"), "session": "s1",
                       "agent_id": agent_id, "agent_type": "tstack:troy-developer",
                       "event": "PreToolUse", "tool": "Write", "rule": "scope",
                       "paths": ["tests/test_app.py"], "subcommand": None, "decision": "deny"})


def days_config(days):
    """Returns a full config whose [hooks] table sets log_days to the given text."""
    return make_config(extra=f"[hooks]\nlog_days = {days}\n")


def write_log(project, lines):
    """Writes hooks.log with the given lines, one per line, LF endings."""
    write_file(project.root, ".git/troy-mode/hooks.log", "\n".join(lines) + "\n")


def kept_ids(project):
    """Returns the agent_id of each non-blank log line, in order.

    A line that is not a JSON object gives ``unreadable: <line>``, so a test
    sees an unreadable line that was kept instead of failing on it.
    """
    ids = []
    for line in project.log_text().splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except ValueError:
            data = None
        ids.append(data.get("agent_id") if isinstance(data, dict) else f"unreadable: {line}")
    return ids


def make_record(project, agent_id, age_seconds):
    """Writes a role record whose file time is the given number of seconds ago."""
    path = write_file(project.root, f".git/troy-mode/agents/{agent_id}.json", "{}\n")
    moment = time.time() - age_seconds
    os.utime(path, (moment, moment))
    return path


def record_ids(project):
    """Returns the sorted agent IDs of the role records left in the git folder."""
    folder = project.git_dir / "troy-mode" / "agents"
    if not folder.is_dir():
        return []
    return sorted(path.stem for path in folder.glob("*.json"))


class LogDaysCase(HookTestCase):
    """Shared steps: a project with a log, one SessionStart, and the kept lines."""

    def project(self, **kwargs):
        """Returns a new Project that is deleted after the test."""
        project = Project(**kwargs)
        self.addCleanup(project.close)
        return project

    def kept_after_start(self, project, lines):
        """Writes the log, runs SessionStart, and returns (the run, the kept agent IDs)."""
        write_log(project, lines)
        out = session_call(project).run()
        self.assertEqual(0, out.code, "SessionStart failed" + out.describe())
        return out, kept_ids(project)


class DefaultDaysTests(LogDaysCase):
    """Design 10: with no log_days, lines are kept for 30 days."""

    def test_no_hooks_table_keeps_29_days_and_removes_31(self):
        """No [hooks] table: a line 29 days old stays, one 31 days old goes.

        Planted bugs caught: the default ignored (a day kept), and a default one
        day short. A line 2 days old also stays, which the old one-day rule removed.
        """
        project = self.project()
        _, kept = self.kept_after_start(project, [
            log_line(31 * DAY, "agent-31d"), log_line(29 * DAY, "agent-29d"),
            log_line(2 * DAY, "agent-2d"), log_line(HOUR, "agent-1h")])
        self.assertEqual(["agent-29d", "agent-2d", "agent-1h"], kept)

    def test_default_boundary_is_30_days(self):
        """No [hooks] table: an hour under 30 days stays, an hour over 30 days goes.

        Planted bug caught: the cutoff one day off (29 or 31 days by default).
        """
        project = self.project()
        _, kept = self.kept_after_start(project, [
            log_line(30 * DAY + HOUR, "agent-over"), log_line(30 * DAY - HOUR, "agent-under")])
        self.assertEqual(["agent-under"], kept)

    def test_empty_hooks_table_keeps_30_days(self):
        """An empty [hooks] table is the default: 29 days stays, 31 days goes."""
        project = self.project(config=make_config(extra="[hooks]\n"))
        _, kept = self.kept_after_start(project, [
            log_line(31 * DAY, "agent-31d"), log_line(29 * DAY, "agent-29d"),
            log_line(2 * DAY, "agent-2d")])
        self.assertEqual(["agent-29d", "agent-2d"], kept)

    def test_missing_config_file_keeps_30_days(self):
        """A troy-mode project with no committed config file keeps 30 days too."""
        project = self.project(config=None)
        self.assertFalse(project.path(CONFIG_PATH).exists())
        _, kept = self.kept_after_start(project, [
            log_line(31 * DAY, "agent-31d"), log_line(29 * DAY, "agent-29d"),
            log_line(2 * DAY, "agent-2d")])
        self.assertEqual(["agent-29d", "agent-2d"], kept)

    def test_lines_are_removed_while_hooks_are_set(self):
        """Log cleanup also runs when SessionStart sets an unset core.hooksPath in the same call."""
        project = self.project(hooks_on=False)
        self.assertIsNone(project.hooks_path())
        write_log(project, [log_line(31 * DAY, "agent-31d"), log_line(29 * DAY, "agent-29d")])
        self.assert_context(session_call(project).run())
        self.assertEqual(HOOKS_PATH, project.hooks_path())
        self.assertEqual(["agent-29d"], kept_ids(project))


class ConfiguredDaysTests(LogDaysCase):
    """Design 10: [hooks] log_days sets how many days lines are kept."""

    def test_seven_days_keeps_an_hour_under_and_removes_an_hour_over(self):
        """log_days = 7: a line an hour under 7 days stays, one an hour over goes.

        Planted bugs caught: the cutoff one day off (6 days removes the first line,
        8 days keeps the second), and the default used in place of the value.
        """
        project = self.project(config=days_config(7))
        _, kept = self.kept_after_start(project, [
            log_line(7 * DAY + HOUR, "agent-over"), log_line(7 * DAY - HOUR, "agent-under"),
            log_line(HOUR, "agent-1h")])
        self.assertEqual(["agent-under", "agent-1h"], kept)

    def test_one_day_removes_a_line_two_days_old(self):
        """log_days = 1: lines 2 days and a day and an hour old go; 23 hours and 1 hour stay."""
        project = self.project(config=days_config(1))
        _, kept = self.kept_after_start(project, [
            log_line(2 * DAY, "agent-2d"), log_line(DAY + HOUR, "agent-25h"),
            log_line(DAY - HOUR, "agent-23h"), log_line(HOUR, "agent-1h")])
        self.assertEqual(["agent-23h", "agent-1h"], kept)

    def test_large_log_days_keeps_lines_for_a_year(self):
        """log_days = 365: an hour under 365 days stays, an hour over goes, 100 days stays."""
        project = self.project(config=days_config(365))
        _, kept = self.kept_after_start(project, [
            log_line(365 * DAY + HOUR, "agent-over"), log_line(365 * DAY - HOUR, "agent-under"),
            log_line(100 * DAY, "agent-100d")])
        self.assertEqual(["agent-under", "agent-100d"], kept)


class LineTests(LogDaysCase):
    """Design 10: unreadable lines go, and kept lines keep their order and text."""

    def test_unreadable_lines_are_removed(self):
        """A line that is not JSON, not an object, or has no readable time is removed."""
        project = self.project()
        lines = [log_line(HOUR, "agent-a"),
                 "not json at all",
                 "[1, 2, 3]",
                 json.dumps({"agent_id": "agent-no-time", "decision": "deny"}),
                 json.dumps({"time": "yesterday", "agent_id": "agent-bad-time"}),
                 json.dumps({"time": 12345, "agent_id": "agent-number-time"}),
                 log_line(2 * DAY, "agent-b")]
        _, kept = self.kept_after_start(project, lines)
        self.assertEqual(["agent-a", "agent-b"], kept)

    def test_kept_lines_keep_their_order(self):
        """Kept lines stay in file order, not time order, with their text unchanged."""
        project = self.project()
        lines = [log_line(2 * DAY, "agent-c"), log_line(40 * DAY, "agent-old1"),
                 log_line(10 * DAY, "agent-a"), log_line(35 * DAY, "agent-old2"),
                 log_line(HOUR, "agent-b"), log_line(20 * DAY, "agent-d")]
        _, kept = self.kept_after_start(project, lines)
        self.assertEqual(["agent-c", "agent-a", "agent-b", "agent-d"], kept)
        text_lines = [line for line in project.log_text().splitlines() if line.strip()]
        self.assertEqual([lines[0], lines[2], lines[4], lines[5]], text_lines)


class RecordTests(LogDaysCase):
    """Design 10: role records go after one day, whatever log_days says."""

    CONFIGS = {
        "no [hooks] table": make_config(),
        "log_days 1": days_config(1),
        "log_days 30": days_config(30),
        "log_days 365": days_config(365),
    }

    def test_old_records_are_removed_whatever_log_days_says(self):
        """Records 2 days and 25 hours old go, one an hour old stays, for each log_days.

        Planted bug caught: role records kept for log_days.
        """
        projects = []
        for config in self.CONFIGS.values():
            project = self.project(config=config)
            make_record(project, "agent-2d", 2 * DAY)
            make_record(project, "agent-25h", DAY + HOUR)
            make_record(project, "agent-1h", HOUR)
            projects.append(project)
        outs = run_many([session_call(project) for project in projects])
        for label, project, out in zip(self.CONFIGS, projects, outs):
            with self.subTest(config=label):
                self.assertEqual(0, out.code, out.describe())
                self.assertEqual(["agent-1h"], record_ids(project))

    def test_records_and_lines_use_their_own_ages(self):
        """log_days = 30: a record 2 days old goes while a log line 2 days old stays."""
        project = self.project(config=days_config(30))
        make_record(project, "agent-2d", 2 * DAY)
        make_record(project, "agent-1h", HOUR)
        _, kept = self.kept_after_start(project, [log_line(2 * DAY, "agent-2d")])
        self.assertEqual(["agent-2d"], kept)
        self.assertEqual(["agent-1h"], record_ids(project))


class ConfigFromHeadTests(LogDaysCase):
    """Design 10 and 5.2: log_days is read from the config as committed at HEAD."""

    def test_uncommitted_log_days_edit_is_not_read(self):
        """log_days = 1 only in the working tree: a line 2 days old stays (30 at HEAD).

        Planted bugs caught: the config read from the working tree, and the
        default ignored (a day kept).
        """
        project = self.project()
        project.write(CONFIG_PATH, days_config(1))
        _, kept = self.kept_after_start(project, [
            log_line(2 * DAY, "agent-2d"), log_line(HOUR, "agent-1h")])
        self.assertEqual(["agent-2d", "agent-1h"], kept)

    def test_staged_log_days_edit_is_not_read(self):
        """A staged but uncommitted log_days = 1 is not HEAD either: 2 days old stays."""
        project = self.project()
        project.write(CONFIG_PATH, days_config(1))
        project.git("add", CONFIG_PATH)
        _, kept = self.kept_after_start(project, [
            log_line(2 * DAY, "agent-2d"), log_line(HOUR, "agent-1h")])
        self.assertEqual(["agent-2d", "agent-1h"], kept)

    def test_uncommitted_raise_of_log_days_is_not_read(self):
        """log_days = 1 at HEAD and 30 in the working tree: a line 2 days old goes.

        Planted bug caught: the config read from the working tree.
        """
        project = self.project(config=days_config(1))
        project.write(CONFIG_PATH, days_config(30))
        _, kept = self.kept_after_start(project, [
            log_line(2 * DAY, "agent-2d"), log_line(HOUR, "agent-1h")])
        self.assertEqual(["agent-1h"], kept)

    def test_invalid_working_tree_config_is_not_read(self):
        """log_days = 0 only in the working tree: lines are cleaned by HEAD's config, silently.

        Planted bug caught: the config read from the working tree.
        """
        project = self.project()
        project.write(CONFIG_PATH, days_config(0))
        out, kept = self.kept_after_start(project, [
            log_line(31 * DAY, "agent-31d"), log_line(29 * DAY, "agent-29d")])
        self.assertEqual(["agent-29d"], kept)
        self.assert_silent(out)

    def test_valid_working_tree_config_does_not_mend_an_invalid_commit(self):
        """log_days = 0 at HEAD and a valid config in the working tree: no line is removed.

        Planted bug caught: the config read from the working tree.
        """
        project = self.project(config=days_config(0))
        project.write(CONFIG_PATH, make_config())
        lines = [log_line(31 * DAY, "agent-31d"), log_line(HOUR, "agent-1h")]
        write_log(project, lines)
        before = project.log_text()
        self.assert_context(session_call(project).run())
        self.assertEqual(before, project.log_text())

    def test_new_commit_of_log_days_is_read(self):
        """After log_days = 1 is committed on top of a used config, a line 2 days old goes.

        The hooks keep the config's text keyed by HEAD's commit (design 10), so a new
        commit must be read again.
        """
        project = self.project()
        _, kept = self.kept_after_start(project, [log_line(2 * DAY, "agent-2d")])
        self.assertEqual(["agent-2d"], kept, "30 days by default before the change")
        project.write(CONFIG_PATH, days_config(1))
        project.commit_all("Set log_days to 1")
        _, kept = self.kept_after_start(project, [
            log_line(2 * DAY, "agent-2d"), log_line(HOUR, "agent-1h")])
        self.assertEqual(["agent-1h"], kept)


class InvalidConfigTests(LogDaysCase):
    """Design 10: an invalid committed config never costs a log line or the git hooks."""

    @staticmethod
    def lines():
        """Log lines of several ages, one of them unreadable."""
        return [log_line(40 * DAY, "agent-40d"), log_line(2 * DAY, "agent-2d"),
                "not json at all", log_line(HOUR, "agent-1h")]

    def projects(self, **kwargs):
        """Returns one project per invalid config, each with a log, in INVALID's order."""
        projects = []
        for text in INVALID.values():
            project = self.project(config=make_config(extra=text), **kwargs)
            write_log(project, self.lines())
            projects.append(project)
        return projects

    def test_invalid_config_removes_no_log_line(self):
        """Each invalid config: exit 0, additionalContext, and hooks.log unchanged.

        Planted bug caught: a log_days of 0 accepted (it would remove every line).
        """
        projects = self.projects()
        befores = [project.log_text() for project in projects]
        outs = run_many([session_call(project) for project in projects])
        for label, project, before, out in zip(INVALID, projects, befores, outs):
            with self.subTest(config=label):
                self.assert_context(out)
                self.assertEqual(before, project.log_text())

    def test_invalid_config_context_names_hooks_log(self):
        """With hooks already on, the notice is printed and names hooks.log."""
        projects = self.projects()
        outs = run_many([session_call(project) for project in projects])
        for label, out in zip(INVALID, outs):
            with self.subTest(config=label):
                self.assertIn("hooks.log", self.assert_context(out))

    def test_invalid_config_still_removes_old_records(self):
        """Each invalid config: a record 2 days old goes and one an hour old stays.

        Planted bug caught: an invalid config stopping SessionStart early.
        """
        projects = self.projects()
        for project in projects:
            make_record(project, "agent-2d", 2 * DAY)
            make_record(project, "agent-1h", HOUR)
        outs = run_many([session_call(project) for project in projects])
        for label, project, out in zip(INVALID, projects, outs):
            with self.subTest(config=label):
                self.assert_context(out)
                self.assertEqual(["agent-1h"], record_ids(project))

    def test_invalid_config_still_sets_an_unset_hooks_path(self):
        """Each invalid config with core.hooksPath unset: it is set, and the log is unchanged.

        Planted bug caught: an invalid config stopping SessionStart before it turns
        on the git hooks.
        """
        projects = self.projects(hooks_on=False)
        befores = [project.log_text() for project in projects]
        for project in projects:
            self.assertIsNone(project.hooks_path())
        outs = run_many([session_call(project) for project in projects])
        for label, project, before, out in zip(INVALID, projects, befores, outs):
            with self.subTest(config=label):
                self.assert_context(out)
                self.assertEqual(HOOKS_PATH, project.hooks_path())
                self.assertEqual(before, project.log_text())


class RoleCallTests(LogDaysCase):
    """Design 10: [hooks] is part of the config every hook reads, not only SessionStart."""

    def test_valid_hooks_table_leaves_a_role_write_allowed(self):
        """A committed log_days = 7 does not turn a Developer's source write into an error."""
        project = self.project(config=days_config(7))
        self.assert_silent(write_call(project, DEV, project.path("src/pkg/app.py")).run())

    def test_bad_log_days_refuses_a_role_write(self):
        """A committed log_days = 0 is a config error, so a role's call is refused (D39)."""
        project = self.project(config=days_config(0))
        self.assert_error_refusal(write_call(project, DEV, project.path("src/pkg/app.py")).run())


class SilenceTests(LogDaysCase):
    """Convention 12: with a valid config and hooks on, SessionStart prints nothing."""

    CONFIGS = {
        "no [hooks] table": make_config(),
        "empty [hooks] table": make_config(extra="[hooks]\n"),
        "log_days 7": days_config(7),
    }

    def test_valid_config_stays_silent_while_removing(self):
        """Lines and a record are removed, and the run is silent, for each valid config."""
        projects = []
        for config in self.CONFIGS.values():
            project = self.project(config=config)
            write_log(project, [log_line(40 * DAY, "agent-40d"), "not json at all",
                                log_line(HOUR, "agent-1h")])
            make_record(project, "agent-2d", 2 * DAY)
            projects.append(project)
        outs = run_many([session_call(project) for project in projects])
        for label, project, out in zip(self.CONFIGS, projects, outs):
            with self.subTest(config=label):
                self.assert_silent(out)
                self.assertEqual(["agent-1h"], kept_ids(project))
                self.assertEqual([], record_ids(project))


if __name__ == "__main__":
    unittest.main()
