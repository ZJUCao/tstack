"""Running work group (F07 design 6.2, 7 problem 5, and 14.1; F05 design 6.1, D231).

``check-run`` and ``snapshot`` read the role records that F05's hooks keep in
``<git dir>/troy-mode/agents/<agent_id>.json``. The tests write the records
by hand with the keys of the build's interface note: ``agent_id``,
``agent_type``, ``session``, ``started``, ``stopped``, ``background``, and
``paths``. A record is open while ``stopped`` is null or ``background`` holds
a task; a record without the new keys, as an earlier plugin wrote it, is
closed. ``check-run`` counts only an open record of the run's roles made at or
after the snapshot's ``time``; ``snapshot`` refuses with any open record.
Both give a problem of kind ``running`` and list the agent IDs in ``stop``.

Planted bugs of F07 design 14.2 (F05's D231 adds) and the tests that catch them:

- "a record that is not stopped counted as closed":
  ``CheckRunTests.test_open_record_that_has_not_stopped``.
- "a record from before the snapshot counted":
  ``CheckRunTests.test_record_made_before_the_snapshot_gives_none``.
- "``snapshot`` passing with an open record":
  ``SnapshotTests.test_open_record_of_another_role_refuses``,
  ``test_stopped_record_with_a_task_refuses``, and
  ``test_dirty_tree_and_open_record_give_both``.
- "``running`` setting ``escalate``": ``CheckRunTests.test_open_record_that_has_not_stopped``
  and ``test_running_and_scope_problems_together``.
- "the ``running`` problem given an undo": the same two.

F05 design 13.2's "a record without the new fields counted as open" (D231) is caught by
``CheckRunTests.test_record_without_the_new_keys_counts_as_closed`` and
``SnapshotTests.test_closed_and_old_records_let_the_snapshot_pass``.

``RunningSkillTests`` checks the entry skill's section "Running a role" (F07 14.1).
"""

import json
import re
import shutil
import unittest

from flow_helpers import Fakes, problem_kinds, run_engine
from test_entry_skill import SKILL, section, sentences, split_skill
from test_snapshot_check import RunCase, shifted

SOURCE = {"src/wordcount/count.py": '"""Count."""\n'}
# The agent ID of the pilot's probe (F05 design 6.1).
AGENT = "a526a34195938cd47"
TASK = "bbbnne1ji"


def agents_folder(project):
    """The folder of F05's role records in the clone's git folder."""
    return project.git_dir() / "troy-mode" / "agents"


def write_raw(project, name, text):
    """Writes a file into the records folder with the exact text given."""
    folder = agents_folder(project)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(text.encode("utf-8"))


def write_record(project, agent_id, role, started, stopped=None, background=(),
                 session="s1"):
    """Writes a role record with the keys of the interface note and returns it.

    Args:
        project: The clone.
        agent_id: The agent ID, also the file name.
        role: The role, such as ``developer``; ``agent_type`` is ``tstack:troy-<role>``.
        started: ``started``, ``YYYY-MM-DDTHH:MM:SSZ``.
        stopped: ``stopped``, or None while the role runs.
        background: ``background``, the task IDs.
        session: ``session``.

    Returns:
        The record.
    """
    record = {"agent_id": agent_id, "agent_type": f"tstack:troy-{role}", "session": session,
              "started": started, "stopped": stopped, "background": list(background),
              "paths": {}}
    write_raw(project, f"{agent_id}.json", json.dumps(record))
    return record


class RunningCase(RunCase):
    """One shared clone, put back to its first state, with no record, before every test."""

    def setUp(self):
        """Resets the clone as RunCase does and removes the records folder."""
        super().setUp()
        folder = agents_folder(self.project)
        if folder.exists():
            shutil.rmtree(folder)

    def assert_running(self, report, ids):
        """Asserts exactly these ``running`` problems and the sorted IDs in ``stop``.

        Args:
            report: The report.
            ids: The agent IDs.
        """
        self.assertEqual(report.get("stop"), sorted(ids), json.dumps(report)[:3000])
        running = [p for p in report["problems"] if p.get("kind") == "running"]
        self.assertEqual(sorted(p.get("agent_id") for p in running), sorted(ids))
        for problem in running:
            self.assertIn("path", problem)
            self.assertIsNone(problem["path"])
            self.assertIsInstance(problem.get("message"), str)
            self.assertNotEqual(problem["message"].strip(), "")


class CheckRunTests(RunningCase):
    """Problem 5 of design 7: a record of the run's roles, made since the snapshot, is open."""

    def test_open_record_that_has_not_stopped(self):
        """A Developer run whose record is not stopped: ``running``, exit 1, no stage, no undo.

        The run changed a source file, which ``check-run`` would stage without
        the record. After the main session's TaskStop, the hook has closed the
        record, and ``check-run`` run again stages the change.

        Planted bugs caught: a record that is not stopped counted as closed,
        ``running`` setting ``escalate``, and the ``running`` problem given an
        undo (14.2).
        """
        snap = self.snapshot("developer")
        record = write_record(self.project, AGENT, "developer", shifted(snap["time"], 5))
        self.apply(SOURCE)
        report = self.report_of(self.check(snap["run"]), 1, "check-run")
        self.assertEqual(problem_kinds(report), [("running", None)])
        self.assert_running(report, [AGENT])
        self.assertIs(report["escalate"], False)
        self.assertEqual(report["stage"], [])
        self.assertEqual(report["undo"], [])
        record.update(stopped=shifted(snap["time"], 30), background=[])
        write_raw(self.project, f"{AGENT}.json", json.dumps(record))
        again = self.report_of(self.check(snap["run"]), 0, "check-run")
        self.assert_passes(again, SOURCE)
        self.assertEqual(again.get("stop"), [])

    def test_stopped_record_with_a_task_in_background(self):
        """A stopped record whose ``background`` holds a task is still open: ``running``."""
        snap = self.snapshot("test-engineer")
        write_record(self.project, AGENT, "test-engineer", shifted(snap["time"], 5),
                     stopped=shifted(snap["time"], 180), background=[TASK])
        self.apply({"tests/test_count.py": '"""Tests."""\n'})
        report = self.report_of(self.check(snap["run"]), 1, "check-run")
        self.assertEqual(problem_kinds(report), [("running", None)])
        self.assert_running(report, [AGENT])
        self.assertIs(report["escalate"], False)
        self.assertEqual((report["stage"], report["undo"]), ([], []))

    def test_record_started_at_the_snapshot_time_counts(self):
        """A record whose ``started`` equals the snapshot's ``time`` is the run's (at or after)."""
        snap = self.snapshot("developer")
        write_record(self.project, AGENT, "developer", snap["time"])
        report = self.report_of(self.check(snap["run"]), 1, "check-run")
        self.assert_running(report, [AGENT])

    def test_closed_record_gives_none(self):
        """Pair: the same record stopped, with nothing in ``background``, passes."""
        snap = self.snapshot("developer")
        write_record(self.project, AGENT, "developer", shifted(snap["time"], 5),
                     stopped=shifted(snap["time"], 60))
        self.apply(SOURCE)
        report = self.report_of(self.check(snap["run"]), 0, "check-run")
        self.assert_passes(report, SOURCE)
        self.assertEqual(report.get("stop"), [])

    def test_another_roles_open_record_gives_none(self):
        """An open Test Engineer record made during a Developer run is not this run's."""
        snap = self.snapshot("developer")
        write_record(self.project, AGENT, "test-engineer", shifted(snap["time"], 5),
                     background=[TASK])
        self.apply(SOURCE)
        report = self.report_of(self.check(snap["run"]), 0, "check-run")
        self.assert_passes(report, SOURCE)
        self.assertEqual(report.get("stop"), [])

    def test_record_made_before_the_snapshot_gives_none(self):
        """Open records of the run's role whose ``started`` is an hour before the snapshot pass.

        One has not stopped, the other stopped with a task in ``background``.

        Planted bug caught: a record from before the snapshot counted (14.2).
        """
        snap = self.snapshot("developer")
        write_record(self.project, "before-1", "developer", shifted(snap["time"], -3600))
        write_record(self.project, "before-2", "developer", shifted(snap["time"], -3600),
                     stopped=shifted(snap["time"], -3000), background=[TASK])
        self.apply(SOURCE)
        report = self.report_of(self.check(snap["run"]), 0, "check-run")
        self.assert_passes(report, SOURCE)
        self.assertEqual(report.get("stop"), [])

    def test_record_without_the_new_keys_counts_as_closed(self):
        """A record of the run's role in the earlier plugin's shape gives no ``running`` problem.

        F05 planted bug caught: a record without the new fields counted as open (F05 13.2).
        """
        snap = self.snapshot("developer")
        write_raw(self.project, f"{AGENT}.json",
                  json.dumps({"agent_type": "tstack:troy-developer", "paths": {}}))
        write_raw(self.project, "old-2.json",
                  json.dumps({"agent_id": "old-2", "agent_type": "tstack:troy-developer",
                              "paths": {}}))
        self.apply(SOURCE)
        report = self.report_of(self.check(snap["run"]), 0, "check-run")
        self.assert_passes(report, SOURCE)
        self.assertEqual(report.get("stop"), [])

    def test_running_and_scope_problems_together(self):
        """With a scope problem as well, ``undo`` holds the scope path only, and no escalation.

        Planted bugs caught: ``running`` setting ``escalate``, and the
        ``running`` problem given an undo (14.2).
        """
        snap = self.snapshot("developer")
        write_record(self.project, AGENT, "developer", shifted(snap["time"], 5))
        self.apply({"tests/test_new.py": '"""New."""\n'})
        report = self.report_of(self.check(snap["run"]), 1, "check-run")
        self.assertEqual(problem_kinds(report), [("running", None), ("scope", "tests/test_new.py")])
        self.assert_running(report, [AGENT])
        self.assertIs(report["escalate"], False)
        self.assertEqual(report["stage"], [])
        self.assertEqual([entry.get("path") for entry in report["undo"]], ["tests/test_new.py"])

    def test_every_open_record_of_the_run_roles_is_listed_sorted(self):
        """Two reviews under one snapshot, both still running: two problems, ``stop`` sorted."""
        snap = self.snapshot("test-manager", "code-reviewer")
        write_record(self.project, "b-reviewer", "code-reviewer", shifted(snap["time"], 5))
        write_record(self.project, "a-manager", "test-manager", shifted(snap["time"], 6),
                     stopped=shifted(snap["time"], 60), background=[TASK])
        report = self.report_of(self.check(snap["run"]), 1, "check-run")
        self.assertEqual(problem_kinds(report), [("running", None), ("running", None)])
        self.assert_running(report, ["a-manager", "b-reviewer"])

    def test_agent_id_from_the_file_name(self):
        """A record without ``agent_id`` is named by its file name (interface note)."""
        snap = self.snapshot("developer")
        write_raw(self.project, "c0ffee.json",
                  json.dumps({"agent_type": "tstack:troy-developer", "session": "s1",
                              "started": shifted(snap["time"], 5), "stopped": None,
                              "background": [], "paths": {}}))
        report = self.report_of(self.check(snap["run"]), 1, "check-run")
        self.assert_running(report, ["c0ffee"])

    def test_background_line_is_listed_with_the_running_problem(self):
        """The role's ``background`` line in ``hooks.log`` is listed, and problem 5 names the agent.

        Design 7: a background line says that the role stopped with a command
        still running. It has an eleventh key, ``tasks`` (F05 design 10).
        """
        snap = self.snapshot("developer")
        write_record(self.project, AGENT, "developer", shifted(snap["time"], 5),
                     stopped=shifted(snap["time"], 60), background=[TASK])
        line = {"time": shifted(snap["time"], 60), "session": "s1", "agent_id": AGENT,
                "agent_type": "tstack:troy-developer", "event": "SubagentStop", "tool": None,
                "rule": "background", "paths": [], "subcommand": None, "decision": "stop",
                "tasks": [TASK]}
        log = self.project.git_dir() / "troy-mode" / "hooks.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes((json.dumps(line) + "\n").encode("utf-8"))
        report = self.report_of(self.check(snap["run"]), 1, "check-run")
        self.assert_running(report, [AGENT])
        self.assertEqual(report["hooks_log"], [line])


class SnapshotTests(RunningCase):
    """Design 7: ``snapshot`` refuses while any role's record is open, whatever its run."""

    def flow_records(self):
        """The run records in the clone's git folder."""
        folder = self.project.git_dir() / "troy-mode" / "flow"
        return sorted(p.name for p in folder.glob("*.json")) if folder.is_dir() else []

    def refused(self, *roles):
        """Runs ``snapshot`` for the roles, asserts exit 1 and no run, and returns the report."""
        args = ["snapshot"]
        for role in roles:
            args += ["--role", role]
        report = self.report_of(self.project.run(*args), 1, "snapshot")
        self.assertIsNone(report.get("run"), json.dumps(report)[:3000])
        return report

    def test_open_record_of_another_role_refuses(self):
        """An open Test Engineer record from an hour ago, in another session, refuses a Developer
        snapshot.

        The problem's message names the agent and ``TaskStop``, and no run
        record is written.

        Planted bug caught: ``snapshot`` passing with an open record (14.2).
        """
        before = self.flow_records()
        write_record(self.project, AGENT, "test-engineer", "2026-11-20T08:00:00Z",
                     session="another-session")
        report = self.refused("developer")
        self.assertEqual(problem_kinds(report), [("running", None)])
        self.assert_running(report, [AGENT])
        message = report["problems"][0]["message"]
        self.assertIn(AGENT, message)
        self.assertIn("TaskStop", message)
        self.assertEqual(self.flow_records(), before)

    def test_stopped_record_with_a_task_refuses(self):
        """A stopped record that still holds a task in ``background`` refuses the snapshot.

        Planted bug caught: ``snapshot`` passing with an open record (14.2).
        """
        before = self.flow_records()
        write_record(self.project, AGENT, "developer", "2026-11-20T08:00:00Z",
                     stopped="2026-11-20T08:03:00Z", background=[TASK])
        report = self.refused("test-engineer")
        self.assert_running(report, [AGENT])
        self.assertEqual(self.flow_records(), before)

    def test_dirty_tree_and_open_record_give_both(self):
        """A changed file and an open record: both the ``dirty`` and the ``running`` problem.

        Planted bug caught: ``snapshot`` passing with an open record (14.2).
        """
        write_record(self.project, AGENT, "developer", "2026-11-20T08:00:00Z")
        self.project.write("README.md", "# changed\n")
        report = self.refused("developer")
        self.assertEqual(problem_kinds(report), [("dirty", "README.md"), ("running", None)])
        self.assert_running(report, [AGENT])

    def test_every_open_record_is_listed_sorted(self):
        """Two open records of two roles: two problems and both IDs, sorted."""
        write_record(self.project, "b-agent", "developer", "2026-11-20T08:00:00Z")
        write_record(self.project, "a-agent", "test-manager", "2026-11-20T09:00:00Z",
                     stopped="2026-11-20T09:10:00Z", background=[TASK])
        report = self.refused("code-reviewer")
        self.assert_running(report, ["a-agent", "b-agent"])

    def test_closed_and_old_records_let_the_snapshot_pass(self):
        """A closed record, an earlier plugin's record, and files that are not records pass.

        F05 planted bug caught: a record without the new fields counted as open (F05 13.2).
        """
        write_record(self.project, "closed-1", "developer", "2026-11-20T08:00:00Z",
                     stopped="2026-11-20T08:05:00Z")
        write_raw(self.project, "old-1.json",
                  json.dumps({"agent_type": "tstack:troy-developer", "paths": {}}))
        write_raw(self.project, "list.json", "[1, 2]")
        write_raw(self.project, "broken.json", "not JSON")
        report = self.snapshot("developer")
        self.assertIsInstance(report["run"], str)
        self.assertEqual(report.get("stop"), [])

    def test_text_output_names_the_agent_and_task_stop(self):
        """Without ``--json``, a refused snapshot exits 1 and prints the message with the ID."""
        write_record(self.project, AGENT, "developer", "2026-11-20T08:00:00Z")
        out = run_engine(["snapshot", "--role", "developer", "--repo", self.project.root],
                         self.project.tmp, Fakes(fail=True))
        self.assert_exit(out, 1)
        self.assertIn(AGENT, out.stdout + out.stderr)
        self.assertIn("TaskStop", out.stdout + out.stderr)


class StopKeyTests(RunningCase):
    """Interface note: both reports always have ``stop``, an empty list when nothing runs."""

    def test_reports_always_have_stop(self):
        """A passing and a dirty snapshot, a passing and a scope-problem check-run: ``stop`` []."""
        snap = self.snapshot("developer")
        self.assertEqual(snap.get("stop"), [])
        self.apply(SOURCE)
        passed = self.report_of(self.check(snap["run"]), 0, "check-run")
        self.assertEqual(passed.get("stop"), [])
        dirty = self.report_of(self.project.run("snapshot", "--role", "developer"), 1, "snapshot")
        self.assertEqual(dirty.get("stop"), [])
        self.setUp()
        run = self.snapshot("developer")["run"]
        self.apply({"tests/test_new.py": '"""New."""\n'})
        scope = self.report_of(self.check(run), 1, "check-run")
        self.assertEqual(scope.get("stop"), [])


class RunningSkillTests(unittest.TestCase):
    """The entry skill's section "Running a role" (F07 design 6.2 and 7, interface note)."""

    @classmethod
    def setUpClass(cls):
        """Cuts the section out of SKILL.md; empty when the file or the section is missing."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.section = section(split_skill(text)[1], "## Running a role")
        cls.sentences = sentences(cls.section)

    def test_names_the_running_problem(self):
        """The section names the problem kind ``running``, as a code span."""
        self.assertIn("`running`", self.section)

    def test_names_task_stop(self):
        """The section names ``TaskStop``, with which the main session ends each named agent."""
        self.assertIn("TaskStop", self.section)

    def test_runs_check_run_again(self):
        """A sentence of the section runs ``check-run`` again after the agents are stopped."""
        found = [s for s in self.sentences if "check-run" in s and re.search(r"\bagain\b", s)]
        self.assertTrue(found, self.section)

    def test_handles_the_snapshot_refusal(self):
        """A sentence names ``snapshot`` with ``running``, ``TaskStop``, or taking it again."""
        found = [s for s in self.sentences if "snapshot" in s
                 and ("`running`" in s or "TaskStop" in s or re.search(r"\bagain\b", s))]
        self.assertTrue(found, self.section)

    def test_does_not_ask_for_roles_in_the_foreground(self):
        """The section says nothing of the foreground or ``run_in_background`` (F05 D231)."""
        self.assertNotEqual(self.section, "")
        self.assertNotIn("foreground", self.section.lower())
        self.assertNotIn("run_in_background", self.section)


if __name__ == "__main__":
    unittest.main()
