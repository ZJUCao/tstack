"""Background work group (F05 design 6.1, D231 and D232, and 13.1; tstack issue #49).

Claude Code moves a command past the Bash tool's time limit to the
background and gives the hooks its task ID. The hooks keep a role's record
until that work ends: PostToolUse adds the task to ``background``,
SubagentStop sets ``stopped`` and keeps only the tasks that its
``background_tasks`` lists as running shells, the main session's TaskStop and
SessionEnd close records, and every call of a role that has already stopped
is refused with rule ``stopped``. A woken role's stop does no change
detection and never blocks.

The record's keys and the output and log details the design leaves open come
from the build's interface note: ``agent_id``, ``agent_type``, ``session``,
``started``, ``stopped``, ``background``, and ``paths``; times as
``YYYY-MM-DDTHH:MM:SSZ``; ``stopped`` means a non-empty string; a record
without the new keys is not stopped for the hooks. Many tests write records
by hand with ``role_record`` and ``Project.write_record``; the others drive
SubagentStart, PostToolUse, and SubagentStop as Claude Code would.

Where the design gives a text in quotes, the test requires that text: the
``additionalContext`` of a recorded task (``background_notice``) and the
reason of rule ``stopped`` (``STOPPED_REASON``).

Planted bugs (design 13.2, D231 and D232's change) and the tests that catch
them. Each test also names its bug in its docstring.

- ``backgroundTaskId`` missed for PowerShell:
  PostToolUseTests.test_powershell_background_task_is_recorded_and_named.
- A main-session command recorded:
  PostToolUseTests.test_main_session_and_other_subagents_record_nothing.
- ``background`` kept without reading ``background_tasks``:
  StopTests.test_stop_keeps_only_the_running_shells_it_recorded and
  test_stop_with_nothing_left_running_writes_no_line;
  WokenRoleTests.test_woken_role_stop_keeps_only_its_running_tasks.
- ``stopped`` set on a blocked stop: StopTests.test_blocked_stop_sets_nothing;
  test_changes.SubagentStopTests.test_stop_blocks_once_then_lets_the_role_stop.
- SubagentStart overwriting a stopped record:
  StartTests.test_start_of_a_stopped_agent_keeps_its_record_byte_for_byte and
  test_start_after_a_real_stop_keeps_the_record;
  WokenRoleTests.test_woken_role_stop_with_another_roles_changes_in_the_tree.
- A stopped role's Bash allowed: StoppedRoleTests.test_stopped_role_calls_are_refused
  and test_role_stopped_by_its_own_stop_is_refused;
  WokenRoleTests.test_woken_role_stop_with_another_roles_changes_in_the_tree.
- Change detection at a woken role's stop:
  WokenRoleTests.test_woken_role_stop_with_another_roles_changes_in_the_tree and
  test_woken_role_stop_keeps_only_its_running_tasks.
- TaskStop with an agent ID leaving the record open:
  TaskStopTests.test_main_session_task_stop_of_an_agent_closes_its_record and
  test_main_session_task_stop_keeps_an_earlier_stopped_time.
- A subagent's TaskStop closing a record:
  TaskStopTests.test_role_and_other_subagent_task_stop_close_nothing.
- SessionEnd closing another session's records:
  SessionEndTests.test_session_end_closes_only_the_ending_sessions_records.
- A record without the new fields counted as open: "open" is F07's reading of
  a record, so the engine's tests catch it:
  troy-mode/flow/tests/test_running_work.py
  CheckRunTests.test_record_without_the_new_keys_counts_as_closed and
  SnapshotTests.test_closed_and_old_records_let_the_snapshot_pass. Here,
  OldRecordTests checks the hooks' side: such a role is not refused, and its
  stop adds the keys.
- The command text in the ``background`` line:
  StopTests.test_stop_keeps_only_the_running_shells_it_recorded.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -p "test_background_work.py" -v
"""

import json
import unittest
from datetime import datetime, timedelta, timezone

from hook_helpers import (
    BACKGROUND_LOG_KEYS, FOO, GP, HOOKS_JSON, LOG_KEYS, LOG_TIME, MAIN, PLUGIN_ROOT, SECRET,
    SESSION, STOPPED_REASON, TIME_FORMAT, HookTestCase, Project, background_response, bash_call,
    post_call, read_call, role, role_record, session_end_call, shell_task, skill_call,
    start_call, stop_call, subagent_task, task_stop_call, unique, write_call, write_file,
)

# The task ID the probe of CLI 2.1.328 logged (design 6.1, probe 1).
TASK = "bbbnne1ji"
# A stopped time from an earlier stop, which TaskStop and SessionEnd keep.
OLD_STOPPED = "2026-11-21T01:02:03Z"
SKILL_FILE = PLUGIN_ROOT / "skills" / "technical-writing" / "SKILL.md"
SCOPE_TOOLS = {"Bash", "PowerShell", "Edit", "Write", "NotebookEdit", "Skill", "TaskStop"}


def background_notice(task_id):
    """The additionalContext of design 6.1, hooks step 1, for one task."""
    return (f"troy-mode: this command now runs in the background as task {task_id}. "
            "You cannot stop it, and the main session stops it after your report, so do not "
            "wait for its result. Say in your report what you could not check.")


def utc_now():
    """The current UTC time, to the second."""
    return datetime.now(timezone.utc).replace(microsecond=0)


class BackgroundCase(HookTestCase):
    """Gives each test a fresh project and a Test Engineer with a unique agent ID."""

    def setUp(self):
        """Builds the project; the test starts the roles it needs."""
        self.project = Project()
        self.addCleanup(self.project.close)
        self.te = role("test-engineer", unique("-"))

    def start(self, caller=None, session=SESSION):
        """Sends SubagentStart for a role and returns its record."""
        caller = caller or self.te
        start_call(self.project, caller, session=session).run()
        return self.record(caller)

    def record(self, caller=None):
        """Returns a role's record, failing when its file is missing."""
        caller = caller or self.te
        record = self.project.read_record(caller.agent_id)
        self.assertIsNotNone(record, f"the record of {caller.agent_id} is missing")
        return record

    def write_record(self, caller, **fields):
        """Writes a record by hand (see role_record) and returns it."""
        record = role_record(caller, **fields)
        self.project.write_record(caller.agent_id, record)
        return record

    def post_background(self, task_id, caller=None, tool="Bash"):
        """Sends PostToolUse for a shell call that Claude Code moved to the background."""
        command = "Start-Sleep -Seconds 600" if tool == "PowerShell" else "python -m pytest -q"
        return post_call(self.project, caller or self.te, tool=tool, command=command,
                         tool_response=background_response(task_id)).run()

    def stop(self, caller=None, tasks=None, active=False, session=SESSION):
        """Sends SubagentStop with ``background_tasks`` (left out when tasks is None)."""
        return stop_call(self.project, caller or self.te, active=active, session=session,
                         background_tasks=tasks).run()

    def log_count(self):
        """The number of log lines so far."""
        return len(self.project.log_lines())

    def new_lines(self, before):
        """The log lines written after the first ``before`` lines."""
        return self.project.log_lines()[before:]

    def assert_time_since(self, text, since, msg=""):
        """Asserts a ``YYYY-MM-DDTHH:MM:SSZ`` time between ``since`` and now (2 s leeway)."""
        self.assertIsInstance(text, str, f"{msg} expected a time, got {text!r}")
        self.assertRegex(text, LOG_TIME, msg)
        moment = datetime.strptime(text, TIME_FORMAT).replace(tzinfo=timezone.utc)
        self.assertGreaterEqual(moment, since - timedelta(seconds=2), f"{msg} {text} is too early")
        self.assertLessEqual(moment, utc_now() + timedelta(seconds=2), f"{msg} {text} is too late")

    def assert_running_record(self, record, background=()):
        """Asserts a record whose role still runs: ``stopped`` null, and the given tasks."""
        self.assertIn("stopped", record, f"no stopped key: {record}")
        self.assertIsNone(record["stopped"], f"stopped is set: {record}")
        self.assertEqual(list(background), record.get("background"), f"background: {record}")

    def assert_background_notice(self, out, task_id, blocked=False):
        """Asserts PostToolUse's additionalContext for a recorded task (design 6.1, step 1).

        Args:
            out: The run.
            task_id: The task the text must name.
            blocked: Whether the same answer also blocks for a change outside
                the scope (interface note, event 2).
        """
        self.assertEqual(0, out.code, "expected exit code 0" + out.describe())
        self.assertEqual("", out.stderr.strip(), "expected nothing on stderr" + out.describe())
        data = out.data()
        self.assertIsNotNone(data, "expected one JSON object on stdout" + out.describe())
        specific = data.get("hookSpecificOutput")
        self.assertIsInstance(specific, dict, "no hookSpecificOutput" + out.describe())
        self.assertEqual("PostToolUse", specific.get("hookEventName"), out.describe())
        text = specific.get("additionalContext")
        self.assertIsInstance(text, str, "no additionalContext" + out.describe())
        self.assertIn(background_notice(task_id), text, out.describe())
        if not blocked:
            self.assertNotEqual("block", data.get("decision"), "unexpected block" + out.describe())


class PostToolUseTests(BackgroundCase):
    """Design 6.1, hooks step 1: a role's command that moved to the background is recorded."""

    def test_bash_background_task_is_recorded_and_named(self):
        """A role's Bash call with backgroundTaskId: the record gains the task, the text names it.

        The role is not stopped, and the recording writes no log line.
        """
        self.start()
        before = self.log_count()
        self.assert_background_notice(self.post_background(TASK), TASK)
        self.assert_running_record(self.record(), [TASK])
        self.assertEqual(before, self.log_count(), self.project.log_text())

    def test_powershell_background_task_is_recorded_and_named(self):
        """A role's PowerShell call with backgroundTaskId is recorded and named the same way.

        Planted bug caught: backgroundTaskId missed for PowerShell (13.2).
        """
        self.start()
        out = self.post_background("ps7task", tool="PowerShell")
        self.assert_background_notice(out, "ps7task")
        self.assert_running_record(self.record(), ["ps7task"])

    def test_each_task_is_added_once_in_order(self):
        """Two tasks are kept in the order they came, and a repeated ID is not added again."""
        self.start()
        for task in ("task-a", "task-b", "task-a"):
            with self.subTest(task=task):
                self.assert_background_notice(self.post_background(task), task)
        self.assertEqual(["task-a", "task-b"], self.record().get("background"))

    def test_without_a_background_task_the_record_does_not_change(self):
        """A finished command, no or a non-object tool_response, and an empty ID change nothing.

        Each call is silent, as before D231, since the tree has no change.
        """
        self.start()
        before = self.record()
        missing = post_call(self.project, self.te)
        del missing.payload["tool_response"]
        text = post_call(self.project, self.te)
        text.payload["tool_response"] = f"Command running in background with ID: {TASK}"
        cases = {
            "finished": post_call(self.project, self.te),
            "no tool_response": missing,
            "tool_response is text": text,
            "empty backgroundTaskId": post_call(self.project, self.te,
                                                tool_response=background_response("")),
        }
        for name, call in cases.items():
            with self.subTest(case=name):
                self.assert_silent(call.run())
                self.assertEqual(before, self.record())

    def test_main_session_and_other_subagents_record_nothing(self):
        """The main session's and other subagents' background commands write and change no record.

        Each call is silent. Before any role starts, no record appears; with a
        running role, its record does not change.

        Planted bug caught: a main-session command recorded (13.2).
        """
        callers = ((MAIN, "main-task"), (GP, "gp-task"), (FOO, "foo-task"))
        for caller, task in callers:
            with self.subTest(caller=caller.label, role_running=False):
                out = post_call(self.project, caller,
                                tool_response=background_response(task)).run()
                self.assert_silent(out)
                self.assertEqual({}, self.project.record_files())
        self.start()
        files = sorted(self.project.record_files())
        before = self.record()
        for caller, task in callers:
            with self.subTest(caller=caller.label, role_running=True):
                out = post_call(self.project, caller,
                                tool_response=background_response(task)).run()
                self.assert_silent(out)
        self.assertEqual(files, sorted(self.project.record_files()))
        self.assertEqual(before, self.record())

    def test_the_same_response_from_a_role_is_recorded(self):
        """Pair of the test above: the same response from the role is recorded."""
        self.start()
        self.assert_background_notice(self.post_background("main-task"), "main-task")
        self.assertEqual(["main-task"], self.record().get("background"))

    def test_skill_call_records_nothing(self):
        """A role's Skill call records no task and stays silent (interface note, event 2)."""
        self.start()
        before = self.record()
        out = post_call(self.project, self.te, tool="Skill",
                        tool_response=background_response("skill-task")).run()
        self.assert_silent(out)
        self.assertEqual(before, self.record())

    def test_background_task_and_a_change_outside_the_scope_in_one_answer(self):
        """One JSON object holds design 6's block and the additionalContext (interface note)."""
        self.start()
        self.project.write("src/pkg/app.py", "def run():\n    return 5\n")
        out = self.post_background(TASK)
        self.assert_blocked(out, "src/pkg/app.py")
        self.assert_background_notice(out, TASK, blocked=True)
        self.assertEqual([TASK], self.record().get("background"))


class StopTests(BackgroundCase):
    """Design 6.1, hooks step 2: the stop sets ``stopped`` and keeps the running shells."""

    def test_stop_keeps_only_the_running_shells_it_recorded(self):
        """Only the role's tasks listed as running shells stay; one background line names them.

        The record holds shell-a, shell-done, sub-1, shell-gone, and shell-b.
        background_tasks lists the role itself and sub-1 as subagents,
        shell-done as completed, shell-other (not the role's) and shell-a and
        shell-b as running shells, and leaves out shell-gone. So shell-a and
        shell-b stay, in the record's order. The stop is silent, the record is
        kept with stopped set, and the one background line holds the task IDs
        and none of the commands or descriptions.

        Planted bugs caught: background kept without reading background_tasks,
        and the command text in the background line (13.2).
        """
        self.start()
        for task in ("shell-a", "shell-done", "sub-1", "shell-gone", "shell-b"):
            self.assert_background_notice(self.post_background(task), task)
        tasks = [
            subagent_task(self.te.agent_id),
            subagent_task("sub-1"),
            shell_task("shell-b", command=f"python -m pytest -q -k {SECRET}",
                       description=f"Run the slow tests {SECRET}"),
            shell_task("shell-done", status="completed"),
            shell_task("shell-other", command=f"sleep 600 # {SECRET}"),
            shell_task("shell-a", command=f"python long_check.py --token {SECRET}",
                       description=f"Long check {SECRET}"),
        ]
        before = self.log_count()
        since = utc_now()
        self.assert_silent(self.stop(tasks=tasks))
        record = self.record()
        self.assertEqual(["shell-a", "shell-b"], record.get("background"))
        self.assert_time_since(record.get("stopped"), since, "stopped:")
        lines = self.new_lines(before)
        self.assertEqual(1, len(lines), f"expected one background line: {lines}")
        line = lines[0]
        self.assertEqual(BACKGROUND_LOG_KEYS, set(line), f"log keys: {line}")
        self.assertRegex(line["time"], LOG_TIME)
        self.assertEqual({"session": SESSION, "agent_id": self.te.agent_id,
                          "agent_type": self.te.agent_type, "event": "SubagentStop",
                          "tool": None, "rule": "background", "paths": [], "subcommand": None,
                          "decision": "stop", "tasks": ["shell-a", "shell-b"]},
                         {k: v for k, v in line.items() if k != "time"})
        text = self.project.log_text()
        for fragment in (SECRET, "pytest", "long_check", "sleep 600", "Long check",
                         "slow tests"):
            self.assertNotIn(fragment, text, f"the log holds {fragment!r}")

    def test_stop_with_nothing_left_running_writes_no_line(self):
        """With no task left running, the stop sets stopped, empties background, and logs nothing.

        The task is listed as completed, background_tasks is empty, missing, or
        not a list (which counts as empty).

        Planted bug caught: background kept without reading background_tasks (13.2).
        """
        cases = {"completed": lambda task: [shell_task(task, status="completed")],
                 "empty list": lambda task: [],
                 "no background_tasks": lambda task: None,
                 "not a list": lambda task: shell_task(task)}
        for name, tasks_for in cases.items():
            with self.subTest(case=name):
                caller = role("test-engineer", unique("-"))
                task = f"{caller.agent_id}-task"
                self.start(caller)
                self.assert_background_notice(self.post_background(task, caller), task)
                before = self.log_count()
                since = utc_now()
                self.assert_silent(self.stop(caller, tasks=tasks_for(task)))
                record = self.record(caller)
                self.assertEqual([], record.get("background"))
                self.assert_time_since(record.get("stopped"), since, "stopped:")
                self.assertEqual([], self.new_lines(before))

    def test_blocked_stop_sets_nothing(self):
        """A stop blocked for a change outside the scope leaves the record as it was.

        stopped stays null and background keeps its task, although
        background_tasks lists none. The only log line is the block's.

        Planted bug caught: stopped set on a blocked stop (13.2).
        """
        self.start()
        self.assert_background_notice(self.post_background(TASK), TASK)
        self.project.write("src/pkg/app.py", "def run():\n    return 7\n")
        before = self.record()
        count = self.log_count()
        self.assert_blocked(self.stop(tasks=[]), "src/pkg/app.py")
        self.assertEqual(before, self.record())
        self.assert_running_record(self.record(), [TASK])
        lines = self.new_lines(count)
        self.assertEqual([("changes", "block")],
                         [(line["rule"], line["decision"]) for line in lines])

    def test_stop_after_its_chance_logs_the_changes_then_the_background(self):
        """With stop_hook_active and changes left: the changes line, then the background line."""
        self.start()
        self.assert_background_notice(self.post_background(TASK), TASK)
        self.project.write("src/pkg/app.py", "def run():\n    return 8\n")
        self.assert_blocked(self.stop(tasks=[shell_task(TASK)]), "src/pkg/app.py")
        count = self.log_count()
        since = utc_now()
        self.assert_not_blocked(self.stop(tasks=[shell_task(TASK)], active=True))
        record = self.record()
        self.assertEqual([TASK], record.get("background"))
        self.assert_time_since(record.get("stopped"), since, "stopped:")
        lines = self.new_lines(count)
        self.assertEqual([("changes", "stop", ["src/pkg/app.py"]), ("background", "stop", [])],
                         [(line["rule"], line["decision"], line["paths"]) for line in lines])
        self.assertEqual([TASK], lines[1].get("tasks"))
        self.assertNotIn("tasks", lines[0], "only a background line has tasks")


class StartTests(BackgroundCase):
    """SubagentStart: a fresh record for a new agent, and a stopped record kept as it is."""

    def test_new_agent_gets_a_fresh_record(self):
        """The record holds the start's session, started now, stopped null, and background []."""
        since = utc_now()
        out = start_call(self.project, self.te, session="session-new").run()
        self.assertEqual(0, out.code, out.describe())
        record = self.record()
        self.assertEqual("session-new", record.get("session"))
        self.assert_time_since(record.get("started"), since, "started:")
        self.assert_running_record(record, [])
        self.assertEqual((self.te.agent_id, self.te.agent_type),
                         (record.get("agent_id"), record.get("agent_type")))

    def test_first_call_without_a_start_makes_the_same_record(self):
        """Without SubagentStart, the role's first PreToolUse makes a record with the new keys."""
        since = utc_now()
        self.assert_silent(bash_call(self.project, self.te, "ls").run())
        record = self.record()
        self.assertEqual(SESSION, record.get("session"))
        self.assert_time_since(record.get("started"), since, "started:")
        self.assert_running_record(record, [])

    def test_start_of_a_stopped_agent_keeps_its_record_byte_for_byte(self):
        """A stopped record, with a task or without, is left exactly as it was.

        The record is written by hand with its own layout, and another role's
        edit is in the tree, so any rewrite would show.

        Planted bug caught: SubagentStart overwriting a stopped record (13.2).
        """
        self.project.write("src/pkg/app.py", "def run():\n    return 9\n")
        for name, background in (("a task running", ["t9"]), ("nothing running", [])):
            with self.subTest(case=name):
                caller = role("test-manager", unique("-"))
                record = role_record(caller, session="session-old", stopped=OLD_STOPPED,
                                     background=background)
                path = self.project.write_record(caller.agent_id,
                                                 json.dumps(record, indent=3, sort_keys=True))
                raw = path.read_bytes()
                out = start_call(self.project, caller, session="session-new").run()
                self.assertEqual(0, out.code, out.describe())
                self.assertEqual(raw, path.read_bytes())

    def test_start_after_a_real_stop_keeps_the_record(self):
        """A role that stopped through its own SubagentStop keeps its record when woken.

        Planted bug caught: SubagentStart overwriting a stopped record (13.2).
        """
        self.start()
        self.assert_background_notice(self.post_background(TASK), TASK)
        self.assert_silent(self.stop(tasks=[shell_task(TASK)]))
        path = self.project.record_path(self.te.agent_id)
        raw = path.read_bytes()
        self.project.write("src/pkg/app.py", "def run():\n    return 10\n")
        start_call(self.project, self.te).run()
        self.assertEqual(raw, path.read_bytes())


class StoppedRoleTests(BackgroundCase):
    """D232: every call of a stopped role that can change something is refused; reads are not."""

    @classmethod
    def setUpClass(cls):
        """Writes a plugin file for the reads."""
        write_file(SKILL_FILE.parent, SKILL_FILE.name, "# Technical writing\n")

    def calls(self, caller):
        """Calls a running Developer makes silently: (name, call) pairs."""
        project = self.project
        return [
            ("Bash ls", bash_call(project, caller, "ls")),
            ("Bash git status", bash_call(project, caller, "git status")),
            ("PowerShell", bash_call(project, caller, "Get-ChildItem", tool="PowerShell")),
            ("Edit source", write_call(project, caller, project.path("src/pkg/app.py"),
                                       tool="Edit")),
            ("Write source", write_call(project, caller, project.path("src/pkg/new_module.py"))),
            ("NotebookEdit ignored", write_call(project, caller,
                                                project.path("reports/analysis.ipynb"),
                                                tool="NotebookEdit")),
            ("Skill code-review", skill_call(project, caller, "code-review")),
        ]

    def test_a_running_role_makes_these_calls_silently(self):
        """Pair: a Developer that has not stopped makes each of the calls below silently."""
        dev = role("developer", unique("-"))
        self.start(dev)
        for name, call in self.calls(dev):
            with self.subTest(call=name):
                self.assert_silent(call.run())

    def test_stopped_role_calls_are_refused(self):
        """A stopped Developer's Bash, PowerShell, Edit, Write, NotebookEdit, and Skill are refused.

        Each refusal has the design's reason and one log line with rule
        stopped, decision deny, no paths, and no subcommand. The check comes
        before every other one, so a write outside the scope and a git commit
        are refused with rule stopped too. The record does not change.

        Planted bug caught: a stopped role's Bash allowed (13.2).
        """
        dev = role("developer", unique("-"))
        record = self.write_record(dev, stopped=OLD_STOPPED, background=["t1"])
        calls = self.calls(dev) + [
            ("Write outside the scope", write_call(self.project, dev,
                                                   self.project.path("tests/test_new.py"))),
            ("Bash git commit", bash_call(self.project, dev, "git commit -m 'Add x'")),
        ]
        for name, call in calls:
            with self.subTest(call=name):
                before = self.log_count()
                self.assert_denied(call.run(), STOPPED_REASON)
                lines = self.new_lines(before)
                self.assertEqual(1, len(lines), f"expected one log line: {lines}")
                self.assertEqual(LOG_KEYS, set(lines[0]), f"log keys: {lines[0]}")
                self.assertEqual({"session": SESSION, "agent_id": dev.agent_id,
                                  "agent_type": dev.agent_type, "event": "PreToolUse",
                                  "tool": call.payload["tool_name"], "rule": "stopped",
                                  "paths": [], "subcommand": None, "decision": "deny"},
                                 {k: v for k, v in lines[0].items() if k != "time"})
        self.assertEqual(record, self.record(dev))

    def test_role_stopped_by_its_own_stop_is_refused(self):
        """A Developer whose SubagentStop let it stop is refused its next Bash call.

        Planted bug caught: a stopped role's Bash allowed (13.2).
        """
        dev = role("developer", unique("-"))
        self.start(dev)
        self.assert_silent(self.stop(dev, tasks=[]))
        self.assert_denied(bash_call(self.project, dev, "ls").run(), STOPPED_REASON)
        self.assert_last_log(self.project, rule="stopped", decision="deny",
                             agent_id=dev.agent_id, tool="Bash")

    def test_stopped_role_reads_are_not_refused(self):
        """A stopped role's Read, Glob, and Grep behave as before: allow in the plugin, else silent."""
        dev = role("developer", unique("-"))
        self.write_record(dev, stopped=OLD_STOPPED, background=["t1"])
        plugin = (("Read", SKILL_FILE), ("Glob", PLUGIN_ROOT / "skills"),
                  ("Grep", PLUGIN_ROOT / "skills"))
        for tool, path in plugin:
            with self.subTest(tool=tool, place="plugin"):
                self.assert_allowed_read(read_call(self.project, dev, path, tool=tool).run())
        project = (("Read", self.project.path("README.md")), ("Glob", self.project.root),
                   ("Grep", self.project.root))
        for tool, path in project:
            with self.subTest(tool=tool, place="project"):
                self.assert_silent(read_call(self.project, dev, path, tool=tool).run())


class WokenRoleTests(BackgroundCase):
    """D232: a woken role's stop does no change detection, never blocks, and updates background."""

    def test_woken_role_stop_with_another_roles_changes_in_the_tree(self):
        """The 2026-11-21 shape: a woken Test Manager is not told to restore the Developer's files.

        The Test Manager stops with a hung command. The Developer starts and
        edits source. The command ends and Claude Code wakes the Test Manager:
        SubagentStart, then more Developer edits. The Test Manager's git
        restore is refused with rule stopped, and its stop is silent, writes no
        log line, keeps stopped, and drops the ended task.

        Planted bugs caught: change detection at a woken role's stop,
        SubagentStart overwriting a stopped record, and a stopped role's Bash
        allowed (13.2).
        """
        tm = role("test-manager", unique("-"))
        dev = role("developer", unique("-"))
        self.start(tm)
        self.assert_background_notice(self.post_background("hung", tm), "hung")
        self.assert_silent(self.stop(tm, tasks=[shell_task("hung")]))
        stopped = self.record(tm).get("stopped")
        self.assertRegex(stopped or "", LOG_TIME)
        self.start(dev)
        self.project.write("src/pkg/app.py", "def run():\n    return 11\n")
        start_call(self.project, tm).run()
        self.project.write("src/pkg/new_module.py", "X = 1\n")
        self.project.write("src/pkg/__init__.py", "# Package.\n")
        restore = bash_call(self.project, tm, "git restore -- src/pkg/app.py").run()
        self.assert_denied(restore, STOPPED_REASON)
        before = self.log_count()
        out = self.stop(tm, tasks=[shell_task("hung", status="completed"),
                                   subagent_task(dev.agent_id, agent_type=dev.agent_type)])
        self.assert_silent(out)
        record = self.record(tm)
        self.assertEqual(stopped, record.get("stopped"))
        self.assertEqual([], record.get("background"))
        self.assertEqual([], self.new_lines(before))
        self.assertTrue(self.project.path("src/pkg/new_module.py").is_file())

    def test_woken_role_stop_keeps_only_its_running_tasks(self):
        """A woken role's stop keeps the record's running shells, keeps stopped, and logs nothing.

        Planted bugs caught: change detection at a woken role's stop, and
        background kept without reading background_tasks (13.2).
        """
        tm = role("test-manager", unique("-"))
        self.write_record(tm, stopped=OLD_STOPPED, background=["t1", "t2", "t3"])
        self.project.write("src/pkg/app.py", "def run():\n    return 12\n")
        before = self.log_count()
        out = self.stop(tm, tasks=[shell_task("t2", status="completed"), shell_task("t1"),
                                   shell_task("t4")])
        self.assert_silent(out)
        record = self.record(tm)
        self.assertEqual(OLD_STOPPED, record.get("stopped"))
        self.assertEqual(["t1"], record.get("background"))
        self.assertEqual([], self.new_lines(before))


class TaskStopTests(BackgroundCase):
    """Design 6.1, hooks step 3: the main session's TaskStop closes a record or drops a task."""

    def test_main_session_task_stop_of_an_agent_closes_its_record(self):
        """TaskStop with a role's agent ID sets stopped and empties background, silently.

        Another role's record does not change, and no log line is written.

        Planted bug caught: TaskStop with an agent ID leaving the record open (13.2).
        """
        self.start()
        for task in ("task-a", "task-b"):
            self.assert_background_notice(self.post_background(task), task)
        other = role("developer", unique("-"))
        self.start(other)
        other_before = self.record(other)
        count = self.log_count()
        since = utc_now()
        self.assert_silent(task_stop_call(self.project, MAIN, self.te.agent_id).run())
        record = self.record()
        self.assert_time_since(record.get("stopped"), since, "stopped:")
        self.assertEqual([], record.get("background"))
        self.assertEqual(other_before, self.record(other))
        self.assertEqual([], self.new_lines(count))

    def test_main_session_task_stop_keeps_an_earlier_stopped_time(self):
        """TaskStop of a stopped role with a task keeps its stopped time and empties background.

        Planted bug caught: TaskStop with an agent ID leaving the record open (13.2).
        """
        self.write_record(self.te, stopped=OLD_STOPPED, background=["t1"])
        self.assert_silent(task_stop_call(self.project, MAIN, self.te.agent_id).run())
        record = self.record()
        self.assertEqual(OLD_STOPPED, record.get("stopped"))
        self.assertEqual([], record.get("background"))

    def test_main_session_task_stop_of_a_task_removes_only_that_task(self):
        """TaskStop with a task ID removes it from the record that holds it, and nothing else."""
        self.start()
        for task in ("t1", "t2"):
            self.assert_background_notice(self.post_background(task), task)
        other = role("test-manager", unique("-"))
        other_record = self.write_record(other, stopped=OLD_STOPPED, background=["t3"])
        self.assert_silent(task_stop_call(self.project, MAIN, "t1").run())
        self.assert_running_record(self.record(), ["t2"])
        self.assertEqual(other_record, self.record(other))
        self.assert_silent(task_stop_call(self.project, MAIN, "t3").run())
        self.assertEqual(OLD_STOPPED, self.record(other).get("stopped"))
        self.assertEqual([], self.record(other).get("background"))
        self.assert_running_record(self.record(), ["t2"])

    def test_main_session_task_stop_of_an_unknown_id_changes_no_file(self):
        """TaskStop with an ID no record names is silent and leaves every record and the log."""
        self.start()
        self.assert_background_notice(self.post_background("t1"), "t1")
        self.write_record(role("test-manager", unique("-")), stopped=OLD_STOPPED,
                          background=["t3"])
        files = self.project.record_files()
        log = self.project.log_text()
        self.assert_silent(task_stop_call(self.project, MAIN, "no-such-task").run())
        self.assertEqual(files, self.project.record_files())
        self.assertEqual(log, self.project.log_text())

    def test_role_and_other_subagent_task_stop_close_nothing(self):
        """A role's and another subagent's TaskStop, of an agent or a task, change no record.

        Planted bug caught: a subagent's TaskStop closing a record (13.2).
        """
        self.start()
        self.assert_background_notice(self.post_background("t1"), "t1")
        dev = role("developer", unique("-"))
        self.start(dev)
        before = {self.te.agent_id: self.record(), dev.agent_id: self.record(dev)}
        calls = ((self.te, self.te.agent_id), (self.te, "t1"), (self.te, dev.agent_id),
                 (GP, self.te.agent_id), (GP, "t1"), (FOO, dev.agent_id))
        for caller, task_id in calls:
            with self.subTest(caller=caller.label, task_id=task_id):
                self.assert_silent(task_stop_call(self.project, caller, task_id).run())
        self.assertEqual(before, {self.te.agent_id: self.record(), dev.agent_id: self.record(dev)})


class SessionEndTests(BackgroundCase):
    """Design 6.1, hooks step 4: SessionEnd closes the ending session's records and no other."""

    def test_session_end_closes_only_the_ending_sessions_records(self):
        """The ending session's running and stopped records close; the other session's stay.

        A running record gets stopped now, a stopped one keeps its time, and
        both lose their tasks. The call is silent and writes no log line.

        Planted bug caught: SessionEnd closing another session's records (13.2).
        """
        ending, other_session = "session-ending", "session-other"
        self.start(session=ending)
        self.assert_background_notice(self.post_background("task-a"), "task-a")
        stopped_role = role("developer", unique("-"))
        self.write_record(stopped_role, session=ending, stopped=OLD_STOPPED,
                          background=["task-b"])
        other_running = role("test-manager", unique("-"))
        self.start(other_running, session=other_session)
        self.assert_background_notice(self.post_background("task-c", other_running), "task-c")
        other_stopped = role("code-reviewer", unique("-"))
        self.write_record(other_stopped, session=other_session, stopped=OLD_STOPPED,
                          background=["task-d"])
        others = {c.agent_id: self.record(c) for c in (other_running, other_stopped)}
        count = self.log_count()
        since = utc_now()
        self.assert_silent(session_end_call(self.project, session=ending).run())
        running = self.record()
        self.assert_time_since(running.get("stopped"), since, "stopped:")
        self.assertEqual([], running.get("background"))
        stopped = self.record(stopped_role)
        self.assertEqual((OLD_STOPPED, []), (stopped.get("stopped"), stopped.get("background")))
        self.assertEqual(others, {c.agent_id: self.record(c)
                                  for c in (other_running, other_stopped)})
        self.assertEqual([], self.new_lines(count))

    def test_session_end_without_records_is_silent(self):
        """A troy-mode project with no role record: SessionEnd prints nothing."""
        self.assert_silent(session_end_call(self.project).run())


class GateTests(HookTestCase):
    """Design 4: SessionEnd and TaskStop exit at once outside troy-mode projects."""

    def test_session_end_and_task_stop_outside_troy_mode_change_nothing(self):
        """Outside troy-mode both are silent, and a record in the git folder stays as it was."""
        plain = Project(troy_mode=False)
        self.addCleanup(plain.close)
        te = role("test-engineer", unique("-"))
        path = plain.write_record(te.agent_id, role_record(te, background=["t1"]))
        raw = path.read_bytes()
        self.assert_silent(session_end_call(plain).run())
        self.assert_silent(task_stop_call(plain, MAIN, te.agent_id).run())
        self.assertEqual(raw, path.read_bytes())
        self.assertFalse(plain.log_path.exists())

    def test_the_same_calls_close_the_record_in_troy_mode(self):
        """Pair: in a troy-mode project, the same TaskStop closes the same record."""
        project = Project()
        self.addCleanup(project.close)
        te = role("test-engineer", unique("-"))
        project.write_record(te.agent_id, role_record(te, background=["t1"]))
        self.assert_silent(task_stop_call(project, MAIN, te.agent_id).run())
        record = project.read_record(te.agent_id)
        self.assertRegex(record.get("stopped") or "", LOG_TIME)
        self.assertEqual([], record.get("background"))


class OldRecordTests(BackgroundCase):
    """A record without the new keys, as an earlier plugin wrote it, is not stopped (D231)."""

    def old_record(self, caller):
        """Writes a record in the shape of the plugin before D231."""
        self.project.write_record(caller.agent_id,
                                  {"agent_type": caller.agent_type, "paths": {}})

    def test_role_with_a_record_from_an_earlier_plugin_is_not_refused(self):
        """Its Bash, Write, and Skill calls are silent, and no stopped line is logged."""
        dev = role("developer", unique("-"))
        self.old_record(dev)
        calls = (("Bash", bash_call(self.project, dev, "ls")),
                 ("Write", write_call(self.project, dev, self.project.path("src/pkg/app.py"))),
                 ("Skill", skill_call(self.project, dev, "code-review")))
        for name, call in calls:
            with self.subTest(call=name):
                self.assert_silent(call.run())
        self.assertNotIn("stopped", [line.get("rule") for line in self.project.log_lines()])

    def test_stop_of_a_role_with_an_old_record_adds_the_new_keys(self):
        """Its stop sets stopped and adds session, started, and background."""
        dev = role("developer", unique("-"))
        self.old_record(dev)
        since = utc_now()
        self.assert_silent(self.stop(dev, tasks=[]))
        record = self.record(dev)
        for key in ("session", "started", "stopped", "background"):
            self.assertIn(key, record, f"the stop did not add {key}: {record}")
        self.assert_time_since(record["stopped"], since, "stopped:")
        self.assertEqual([], record["background"])

    def test_background_task_of_a_role_with_an_old_record_is_recorded(self):
        """Such a role's background command is recorded and kept at its stop like any other."""
        self.old_record(self.te)
        self.assert_background_notice(self.post_background(TASK), TASK)
        self.assertEqual([TASK], self.record().get("background"))
        self.assert_silent(self.stop(tasks=[shell_task(TASK)]))
        self.assertEqual([TASK], self.record().get("background"))
        self.assert_last_log(self.project, rule="background", decision="stop", tasks=[TASK])


class HooksJsonTests(unittest.TestCase):
    """Design 3: TaskStop in the scope entry's matcher, and a SessionEnd entry (D231)."""

    @classmethod
    def setUpClass(cls):
        """Parses hooks/hooks.json."""
        cls.data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))

    def test_scope_entry_matcher_has_task_stop(self):
        """The PreToolUse entry for Bash is Bash|PowerShell|Edit|Write|NotebookEdit|Skill|TaskStop."""
        groups = self.data["hooks"].get("PreToolUse", [])
        scope = [g for g in groups if "Bash" in (g.get("matcher") or "").split("|")]
        self.assertEqual(1, len(scope), f"PreToolUse groups: {groups}")
        self.assertEqual(SCOPE_TOOLS, set(scope[0]["matcher"].split("|")))

    def test_session_end_entry(self):
        """One SessionEnd entry: no matcher, a bash command hook, timeout 10, troy_hook.py SessionEnd."""
        groups = self.data["hooks"].get("SessionEnd")
        self.assertIsInstance(groups, list, "hooks.json has no SessionEnd entry")
        self.assertEqual(1, len(groups), "SessionEnd: one group")
        self.assertIn(groups[0].get("matcher"), (None, "", "*"))
        hooks = groups[0].get("hooks", [])
        self.assertEqual(1, len(hooks), "SessionEnd: one hook")
        hook = hooks[0]
        self.assertEqual({"type": "command", "shell": "bash", "timeout": 10},
                         {key: hook.get(key) for key in ("type", "shell", "timeout")})
        self.assertNotIn("if", hook)
        self.assertRegex(hook.get("command", ""),
                         r"\$\{CLAUDE_PLUGIN_ROOT\}/troy-mode/hooks/troy_hook\.py[\"']?\s+"
                         r"SessionEnd$")


if __name__ == "__main__":
    unittest.main()
