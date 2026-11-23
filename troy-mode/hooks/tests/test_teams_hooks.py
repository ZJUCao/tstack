"""Teams group, part 1a: the team from the brief, SubagentStart, and rooting (F20 design 3.2).

Written from F20 design version 1.1 (sections 2, 3.1 to 3.3, 8.1, 8.2, 8.4) and the
part 1a contract, section A, before the code exists. The tests are black-box, as
F05's are: each builds a hook ``Project`` (hook_helpers), adds team worktrees with
``git worktree add --detach <home>/.troy-teams/<id> HEAD`` and the line
``/.troy-teams/`` in ``.git/info/exclude``, as ``team start`` does, writes a role's
transcript by hand, and feeds ``troy_hook.py`` one input.

Fixtures (shared with test_teams_changes.py and test_teams_locks.py):

- A role's transcript is ``<folder of transcript_path>/<session_id>/subagents/
  agent-<agent_id>.jsonl`` (contract A1). Each repository gets its own folder for
  ``transcript_path``, so no test sees another's transcripts. The first line is a
  JSON user message whose ``content`` holds the brief, a string or text blocks.
- Callers get hex agent IDs like Claude Code's. ``team_role`` writes a brief with the
  team sentence, ``home_role`` one without it, and ``unknown_role`` none at all.
- A team's records and log are in ``<worktree's git folder>/troy-mode/``, found with
  ``git rev-parse --absolute-git-dir`` in the worktree.
- Rooted output (contract A4): exactly ``{"hookSpecificOutput": {"hookEventName":
  "PreToolUse", "updatedInput": {...}}}``. The path in ``cd "<path>"`` and in
  ``Set-Location -LiteralPath '<path>'`` may use either slash; it must name the
  worktree's real path.
- A role whose first call writes its record makes that call alone, before any calls
  in parallel (hook_helpers convention 10), since SubagentStart no longer writes it.

Planted bugs of design 8.2 (part 1a) caught in this file:

- The team read from ``cwd`` instead of the brief:
  TeamFromBriefTests.test_first_call_records_the_team_in_the_worktree_git_folder and
  test_brief_as_text_blocks.
- A team sentence that names any folder accepted:
  TeamFromBriefTests.test_sentence_naming_another_folder_gives_no_team.
- SubagentStart still writing a record into the home checkout:
  StartTests.test_start_with_a_team_worktree_writes_no_record.
- The rooting skipped for PowerShell: RootingTests.test_powershell_is_rooted_with_set_location
  and test_powershell_doubles_a_single_quote_in_the_path.
- A Glob with a path rewritten:
  RootingTests.test_glob_and_grep_with_a_path_or_an_absolute_pattern_are_unchanged.
- A record looked up only in the home checkout's git folder:
  TeamFromBriefTests.test_record_in_a_team_git_folder_is_found_by_agent_id;
  test_teams_changes.MainSessionRecordTests.

The file tools of contract A4 (and "a team role's Write into the home checkout
allowed") are in test_teams_changes.FileToolTests.

Planted bugs named here: the transcript searched as raw JSON text (Windows backslashes
doubled), TeamFromBriefTests.test_windows_forms_of_the_path_name_the_same_worktree; a
team role's refusal logged in the home checkout,
RootingTests.test_refused_call_of_a_team_role_has_no_updated_input.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -p "test_teams_*.py" -v
"""

from __future__ import annotations

import json
import os
import re
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from hook_helpers import (
    IS_WINDOWS, LOG_TIME, MAIN, PACK_DEPENDENCIES, PLUGIN_ROOT, SCRATCH, SESSION, STOPPED_REASON,
    TIME_FORMAT, Call, Caller, HookRun, HookTestCase, Project, background_response, make_config,
    post_call, pre_call, remove_tree, role_record, run_git, session_call, session_end_call,
    start_call, stop_call, task_stop_call, unique, write_file,
)

TEAMS = ".troy-teams"
EXCLUDE_LINE = "/.troy-teams/"
BASH_ROOT = re.compile(r'cd "([^"]+)" && (.*)', re.DOTALL)
PS_ROOT = re.compile(r"Set-Location -LiteralPath '((?:[^']|'')*)'; (.*)", re.DOTALL)
UNREADABLE = "could not read your brief"
OUTSIDE = "You work in the checkout"
STARTED = "2026-11-22T01:00:00Z"
OLD_STOPPED = "2026-11-22T01:05:00Z"
WIDE_CONFIG = make_config(dependencies=PACK_DEPENDENCIES + ("tests/data/**",))
FILE_TOOLS = ("Write", "Edit", "NotebookEdit")


def team_sentence(team: str, path) -> str:
    """The brief's team sentence of design 3.2 and contract A1."""
    return (f"You work for team {team} in the checkout `{path}`: every path in this brief is "
            "inside it, read and write files only there, and your commands start there.")


def brief(sentence: Optional[str] = None) -> str:
    """A role brief whose Task line holds the sentence, when one is given."""
    task = "Task: DV1, Mock. Write the mock of the feature's interfaces."
    if sentence:
        task += " " + sentence
    return task + "\n\nInput: none.\n\nRead first: docs/features/F08/design.md\n"


def norm(path) -> str:
    """A path made absolute and real, without case on Windows."""
    return os.path.normcase(os.path.realpath(os.path.abspath(str(path))))


def same_path(first, second) -> bool:
    """Whether two paths name the same place."""
    return norm(first) == norm(second)


def utc_now() -> datetime:
    """The current UTC time, to the second."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def new_role(name: str) -> Caller:
    """A role caller with a fresh hex agent ID, like Claude Code's."""
    return Caller(f"tstack:troy-{name}", "a" + uuid.uuid4().hex[:16], name)


def tool_input_for(tool: str, path) -> dict:
    """The tool input of Write, Edit, or NotebookEdit for a path."""
    if tool == "NotebookEdit":
        return {"notebook_path": str(path), "new_source": "x = 1\n"}
    if tool == "Edit":
        return {"file_path": str(path), "old_string": "a", "new_string": "b"}
    return {"file_path": str(path), "content": "x = 1\n"}


def set_age(path: Path, seconds: float) -> None:
    """Sets a file's times to the given number of seconds ago."""
    moment = datetime.now(timezone.utc).timestamp() - seconds
    os.utime(path, (moment, moment))


def log_entry(age_seconds: float, agent_id: Optional[str], rule: str = "scope") -> str:
    """One hooks.log line, as JSON text, whose time is the given number of seconds ago."""
    moment = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return json.dumps({"time": moment.strftime(TIME_FORMAT), "session": "s1",
                       "agent_id": agent_id, "agent_type": "tstack:troy-developer",
                       "event": "PreToolUse", "tool": "Write", "rule": rule,
                       "paths": ["tests/test_app.py"], "subcommand": None, "decision": "deny"})


class TeamRepo:
    """A hook Project with team worktrees, transcripts, and call builders.

    Attributes:
        project: The home checkout's Project.
        home: The home checkout's root.
        transcripts: The folder of every input's ``transcript_path``.
        trees: Team folder name (``f08``) mapped to the worktree's real path.
    """

    def __init__(self, teams=("f08",), parent: Optional[Path] = None, **kwargs) -> None:
        """Copies a Project and adds a team worktree for each name."""
        self.project = Project(parent=parent, **kwargs)
        self.home = self.project.root
        self.transcripts = (SCRATCH / unique("transcripts")).resolve()
        self.transcripts.mkdir(parents=True)
        self.trees: dict = {}
        for team in teams:
            self.add_team(team)

    def close(self) -> None:
        """Deletes the repository and the transcripts."""
        self.project.close()
        remove_tree(self.transcripts)

    def exclude(self) -> None:
        """Adds ``/.troy-teams/`` to ``.git/info/exclude`` unless it is there."""
        path = self.project.git_dir / "info" / "exclude"
        path.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if EXCLUDE_LINE not in text.splitlines():
            if text and not text.endswith("\n"):
                text += "\n"
            path.write_text(text + EXCLUDE_LINE + "\n", encoding="utf-8")

    def add_worktree(self, path: Path) -> Path:
        """Adds a detached linked worktree at HEAD and returns its real path."""
        self.project.git("worktree", "add", "-q", "--detach", str(path), "HEAD")
        return Path(path).resolve()

    def add_team(self, team: str) -> Path:
        """Adds ``<home>/.troy-teams/<team>`` as ``team start`` would."""
        self.exclude()
        self.trees[team] = self.add_worktree(self.home / TEAMS / team)
        return self.trees[team]

    def tree(self, team: str = "f08") -> Path:
        """A team's worktree."""
        return self.trees[team]

    def tree_git_dir(self, team: str = "f08") -> Path:
        """A team worktree's own git folder."""
        return Path(run_git(self.tree(team), "rev-parse", "--absolute-git-dir")).resolve()

    def home_state(self) -> Path:
        """``<home git folder>/troy-mode``."""
        return self.project.git_dir / "troy-mode"

    def team_state(self, team: str = "f08") -> Path:
        """``<team git folder>/troy-mode``."""
        return self.tree_git_dir(team) / "troy-mode"

    def states(self) -> dict:
        """Every git folder's ``troy-mode`` folder, by ``home`` and team name."""
        found = {"home": self.home_state()}
        found.update({team: self.team_state(team) for team in self.trees})
        return found

    @staticmethod
    def record_path(state: Path, agent_id: str) -> Path:
        """A record's file in a ``troy-mode`` folder."""
        return state / "agents" / f"{agent_id}.json"

    def read_record(self, state: Path, agent_id: str) -> Optional[dict]:
        """A record, or None when its file does not exist."""
        path = self.record_path(state, agent_id)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_record(self, state: Path, record, name: Optional[str] = None) -> Path:
        """Writes a record by hand: a dict as JSON, or the exact text given."""
        text = record if isinstance(record, str) else json.dumps(record) + "\n"
        path = state / "agents" / f"{name or record['agent_id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    @staticmethod
    def record_names(state: Path) -> list:
        """The sorted names of the record files in a ``troy-mode`` folder."""
        folder = state / "agents"
        return sorted(p.name for p in folder.glob("*.json")) if folder.is_dir() else []

    @staticmethod
    def log_lines(state: Path) -> list:
        """A ``hooks.log``'s lines, parsed; a line that is not an object gives ``unreadable``."""
        path = state / "hooks.log"
        if not path.is_file():
            return []
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except ValueError:
                data = None
            lines.append(data if isinstance(data, dict) else {"unreadable": line})
        return lines

    def transcript_file(self, caller: Caller, session: str = SESSION) -> Path:
        """``<folder of transcript_path>/<session_id>/subagents/agent-<agent_id>.jsonl``."""
        return self.transcripts / session / "subagents" / f"agent-{caller.agent_id}.jsonl"

    def write_transcript(self, caller: Caller, text: Optional[str] = None,
                         raw: Optional[str] = None, blocks: bool = False, session: str = SESSION,
                         path: Optional[Path] = None) -> Path:
        """Writes a role's transcript: the brief as the first line, then a reply.

        Args:
            caller: The role.
            text: The brief.
            raw: The file's exact text instead.
            blocks: Whether ``content`` is a list of text blocks.
            session: The session ID of the folder.
            path: Another file to write instead of the usual one.

        Returns:
            The file.
        """
        target = path or self.transcript_file(caller, session)
        target.parent.mkdir(parents=True, exist_ok=True)
        if raw is None:
            if blocks:
                head, _, rest = text.partition("\n\n")
                content = [{"type": "text", "text": head}, {"type": "text", "text": rest}]
            else:
                content = text
            first = {"parentUuid": None, "isSidechain": True, "agentId": caller.agent_id,
                     "sessionId": session, "type": "user",
                     "message": {"role": "user", "content": content},
                     "uuid": str(uuid.uuid4()), "timestamp": "2026-11-22T01:00:00.000Z"}
            second = {"isSidechain": True, "agentId": caller.agent_id, "type": "assistant",
                      "message": {"role": "assistant",
                                  "content": [{"type": "text", "text": "Reading the design."}]}}
            raw = json.dumps(first) + "\n" + json.dumps(second) + "\n"
        target.write_bytes(raw.encode("utf-8"))
        return target

    def team_role(self, name: str, team: str = "f08", blocks: bool = False) -> Caller:
        """A role whose brief names a team's worktree."""
        caller = new_role(name)
        self.write_transcript(caller, brief(team_sentence(team.upper(), self.tree(team))),
                              blocks=blocks)
        return caller

    def home_role(self, name: str) -> Caller:
        """A role whose brief has no team sentence."""
        caller = new_role(name)
        self.write_transcript(caller, brief())
        return caller

    @staticmethod
    def unknown_role(name: str) -> Caller:
        """A role with no transcript at all."""
        return new_role(name)

    def fix(self, call: Call, session: str = SESSION) -> Call:
        """Points the input's ``transcript_path`` into this repository's folder."""
        call.payload["transcript_path"] = str(self.transcripts / f"{session}.jsonl")
        return call

    def pre(self, caller: Caller, tool: str, tool_input: dict, **kwargs) -> Call:
        """A PreToolUse call with this repository's transcripts."""
        return self.fix(pre_call(self.project, caller, tool, dict(tool_input), **kwargs),
                        kwargs.get("session", SESSION))

    def bash(self, caller: Caller, command: str, tool: str = "Bash", **kwargs) -> Call:
        """A Bash or PowerShell PreToolUse call."""
        tool_input = {"command": command}
        if tool == "Bash":
            tool_input["description"] = "Run a command"
        return self.pre(caller, tool, tool_input, **kwargs)

    def write(self, caller: Caller, path, tool: str = "Write", **kwargs) -> Call:
        """A Write, Edit, or NotebookEdit PreToolUse call."""
        return self.pre(caller, tool, tool_input_for(tool, path), **kwargs)

    def first_call(self, caller: Caller) -> HookRun:
        """The role's first call, ``ls``, which makes its record."""
        return self.bash(caller, "ls").run()

    def post(self, caller: Caller, task: Optional[str] = None, tool: str = "Bash",
             session: str = SESSION) -> Call:
        """A PostToolUse call, with a command moved to the background when a task is given."""
        response = background_response(task) if task else None
        return self.fix(post_call(self.project, caller, tool=tool, session=session,
                                  tool_response=response), session)

    def stop(self, caller: Caller, active: bool = False, tasks=None,
             session: str = SESSION) -> Call:
        """A SubagentStop call that names the role's own transcript."""
        call = self.fix(stop_call(self.project, caller, active=active, session=session,
                                  background_tasks=tasks), session)
        call.payload["agent_transcript_path"] = str(self.transcript_file(caller, session))
        return call

    def start(self, caller: Caller, session: str = SESSION) -> Call:
        """A SubagentStart call."""
        return self.fix(start_call(self.project, caller, session=session), session)

    def task_stop(self, task_id: str, caller: Caller = MAIN) -> Call:
        """A main-session TaskStop call."""
        return self.fix(task_stop_call(self.project, caller, task_id))

    def session_end(self, session: str = SESSION) -> Call:
        """A SessionEnd call."""
        return self.fix(session_end_call(self.project, session=session), session)

    def session_start(self) -> Call:
        """A SessionStart call."""
        return self.fix(session_call(self.project))


def team_record(caller: Caller, worktree: Optional[Path], team: str = "F08", **fields) -> dict:
    """A record to write by hand; with a worktree it holds ``team`` and ``worktree``."""
    record = role_record(caller, **fields)
    if worktree is not None:
        record["team"] = team
        record["worktree"] = str(worktree)
    return record


class TeamCase(HookTestCase):
    """Repository builders and assertions for the team tests. It has no tests of its own."""

    def make_repo(self, teams=("f08",), **kwargs) -> TeamRepo:
        """A TeamRepo deleted after the test."""
        repo = TeamRepo(teams, **kwargs)
        self.addCleanup(repo.close)
        return repo

    def last_line(self, repo: TeamRepo, state: Path) -> dict:
        """Asserts that a log has a line and returns the last one."""
        lines = repo.log_lines(state)
        self.assertTrue(lines, f"the log in {state} is empty")
        return lines[-1]

    def record_of(self, repo: TeamRepo, state: Path, agent_id: str) -> dict:
        """Asserts that a record exists and returns it."""
        record = repo.read_record(state, agent_id)
        self.assertIsNotNone(record, f"no record of {agent_id} in {state}")
        return record

    def updated_input(self, out: HookRun, msg: str = "") -> dict:
        """Asserts the rooting answer of contract A4 and returns its ``updatedInput``."""
        self.assertEqual(0, out.code, f"{msg} expected exit code 0" + out.describe())
        self.assertEqual("", out.stderr.strip(),
                         f"{msg} expected nothing on stderr" + out.describe())
        data = out.data()
        self.assertIsNotNone(data, f"{msg} expected one JSON object" + out.describe())
        self.assertEqual({"hookSpecificOutput"}, set(data), msg + out.describe())
        specific = data["hookSpecificOutput"]
        self.assertIsInstance(specific, dict, msg + out.describe())
        self.assertNotIn("permissionDecision", specific, msg + out.describe())
        self.assertEqual({"hookEventName", "updatedInput"}, set(specific), msg + out.describe())
        self.assertEqual("PreToolUse", specific["hookEventName"], msg + out.describe())
        self.assertIsInstance(specific["updatedInput"], dict, msg + out.describe())
        return specific["updatedInput"]

    def assert_kept(self, updated: dict, tool_input: dict, changed: str, msg: str = "") -> None:
        """Asserts every key of the original input kept, all but one unchanged."""
        self.assertEqual(set(tool_input) | {changed}, set(updated), msg)
        for key, value in tool_input.items():
            if key != changed:
                self.assertEqual(value, updated[key], f"{msg} key {key}")

    def assert_bash_rooted(self, out: HookRun, tool_input: dict, tree: Path, msg: str = "") -> None:
        """Asserts ``cd "<worktree>" && <original command>`` with every other key kept."""
        updated = self.updated_input(out, msg)
        self.assert_kept(updated, tool_input, "command", msg)
        match = BASH_ROOT.fullmatch(updated["command"])
        self.assertIsNotNone(match, f"{msg} not rooted: {updated['command']!r}")
        self.assertTrue(same_path(match.group(1), tree), f"{msg} {match.group(1)!r} is not {tree}")
        self.assertEqual(tool_input["command"], match.group(2), msg)

    def assert_ps_rooted(self, out: HookRun, tool_input: dict, tree: Path, msg: str = "") -> str:
        """Asserts ``Set-Location -LiteralPath '<worktree>'; <command>``; returns the path."""
        updated = self.updated_input(out, msg)
        self.assert_kept(updated, tool_input, "command", msg)
        match = PS_ROOT.fullmatch(updated["command"])
        self.assertIsNotNone(match, f"{msg} not rooted: {updated['command']!r}")
        self.assertTrue(same_path(match.group(1).replace("''", "'"), tree), msg)
        self.assertEqual(tool_input["command"], match.group(2), msg)
        return match.group(1)

    def assert_search_rooted(self, out: HookRun, tool_input: dict, tree: Path,
                             msg: str = "") -> None:
        """Asserts a Glob or Grep given the worktree as ``path``, the other keys kept."""
        updated = self.updated_input(out, msg)
        self.assert_kept(updated, tool_input, "path", msg)
        self.assertTrue(same_path(updated["path"], tree), f"{msg} path {updated['path']!r}")

    def assert_names_checkout(self, out: HookRun, tree: Path, msg: str = "") -> None:
        """Asserts a scope refusal whose reason says ``You work in the checkout <worktree>``."""
        self.assert_denied(out, OUTSIDE, msg=msg)
        reason = out.reason
        wanted = [f"{OUTSIDE} {form}" for form in (str(tree), tree.as_posix())]
        if IS_WINDOWS:
            reason = reason.lower()
            wanted = [text.lower() for text in wanted]
        self.assertTrue(any(text in reason for text in wanted),
                        f"{msg} the reason does not name {tree}" + out.describe())

    def assert_team_record(self, repo: TeamRepo, caller: Caller, team: str = "f08",
                           since: Optional[datetime] = None) -> dict:
        """Asserts a running role's record in the team's git folder (contract A4)."""
        record = repo.read_record(repo.team_state(team), caller.agent_id)
        self.assertIsNotNone(record, f"no record of {caller.agent_id} in {repo.team_state(team)}")
        self.assertEqual((caller.agent_id, caller.agent_type, SESSION),
                         (record.get("agent_id"), record.get("agent_type"), record.get("session")))
        self.assertIn("stopped", record)
        self.assertIsNone(record["stopped"], record)
        self.assertEqual([], record.get("background"), record)
        self.assertIsInstance(record.get("paths"), dict, record)
        self.assertEqual(team.upper(), record.get("team"), record)
        self.assertIsInstance(record.get("worktree"), str, record)
        self.assertTrue(os.path.isabs(record["worktree"]), record)
        self.assertTrue(same_path(record["worktree"], repo.tree(team)), record)
        self.assertRegex(record.get("started") or "", LOG_TIME)
        if since is not None:
            started = datetime.strptime(record["started"], TIME_FORMAT).replace(tzinfo=timezone.utc)
            self.assertGreaterEqual(started, since - timedelta(seconds=2), record)
        return record

    def assert_home_role(self, repo: TeamRepo, caller: Caller, out: HookRun, msg: str = "") -> None:
        """Asserts a home role's first ``ls``: silent, its record in the home git folder only."""
        self.assert_silent(out, msg)
        record = repo.read_record(repo.home_state(), caller.agent_id)
        self.assertIsNotNone(record, f"{msg} no record in the home git folder")
        self.assertNotIn("worktree", record, f"{msg} {record}")
        self.assertNotIn("team", record, f"{msg} {record}")
        for team in repo.trees:
            self.assertIsNone(repo.read_record(repo.team_state(team), caller.agent_id),
                              f"{msg} a record in team {team}'s git folder")

    def assert_nothing_at_home(self, repo: TeamRepo, msg: str = "") -> None:
        """Asserts no record and no log line in the home checkout's git folder."""
        self.assertEqual([], repo.record_names(repo.home_state()), msg)
        self.assertEqual([], repo.log_lines(repo.home_state()), msg)


class TeamFromBriefTests(TeamCase):
    """Contract A1 and A2: which checkout a role's call belongs to."""

    def test_first_call_records_the_team_in_the_worktree_git_folder(self):
        """A team role's first Bash call is rooted and writes its record in the team's git folder.

        The record has the usual fields plus team F08 and the worktree's real path, and
        its paths are the worktree's git status, not the home checkout's. Nothing is
        written in the home checkout's git folder.

        Planted bug caught: the team read from cwd instead of the brief (8.2).
        """
        repo = self.make_repo()
        write_file(repo.tree(), "src/pkg/wt_dirty.py", "X = 1\n")
        repo.project.write("docs/home_dirty.md", "# Home\n")
        dev = repo.team_role("developer")
        since = utc_now()
        tool_input = {"command": "ls", "description": "List files"}
        self.assert_bash_rooted(repo.pre(dev, "Bash", tool_input).run(), tool_input, repo.tree())
        record = self.assert_team_record(repo, dev, since=since)
        self.assertEqual({"src/pkg/wt_dirty.py"}, set(record["paths"]))
        self.assert_nothing_at_home(repo)

    def test_brief_as_text_blocks(self):
        """A brief whose content is a list of text blocks gives the team the same way.

        Planted bug caught: the team read from cwd instead of the brief (8.2).
        """
        repo = self.make_repo()
        dev = repo.team_role("developer", blocks=True)
        tool_input = {"command": "ls", "description": "List files"}
        self.assert_bash_rooted(repo.pre(dev, "Bash", tool_input).run(), tool_input, repo.tree())
        self.assert_team_record(repo, dev)
        self.assert_nothing_at_home(repo)

    def test_agent_transcript_path_of_the_input_is_read(self):
        """With ``agent_transcript_path`` in the input, that file is the role's transcript."""
        repo = self.make_repo()
        dev = new_role("developer")
        elsewhere = repo.transcripts / "elsewhere" / "brief.jsonl"
        repo.write_transcript(dev, brief(team_sentence("F08", repo.tree())), path=elsewhere)
        call = repo.bash(dev, "ls")
        call.payload["agent_transcript_path"] = str(elsewhere)
        self.assert_bash_rooted(call.run(), call.payload["tool_input"], repo.tree())
        self.assert_team_record(repo, dev)

    def test_dotdot_in_the_path_is_resolved(self):
        """``<worktree>/src/..`` is the worktree once made real: a team role."""
        repo = self.make_repo()
        dev = new_role("developer")
        repo.write_transcript(dev, brief(team_sentence("F08", str(repo.tree() / "src" / ".."))))
        self.assert_bash_rooted(repo.bash(dev, "ls").run(),
                                {"command": "ls", "description": "Run a command"}, repo.tree())
        self.assert_team_record(repo, dev)

    @unittest.skipUnless(IS_WINDOWS, "Windows paths and case")
    def test_windows_forms_of_the_path_name_the_same_worktree(self):
        """Upper case, forward slashes, and a lower-case drive letter name the worktree.

        The transcript is JSON, so each backslash is doubled in the file and appears
        once after decoding.

        Planted bug named here: the transcript searched as raw JSON text.
        """
        repo = self.make_repo()
        tree = str(repo.tree())
        forms = {"native": tree, "upper case": tree.upper(),
                 "forward slashes": Path(tree).as_posix(),
                 "drive letter": tree[0].lower() + tree[1:]}
        for name, form in forms.items():
            with self.subTest(form=name):
                dev = new_role("developer")
                repo.write_transcript(dev, brief(team_sentence("F08", form)))
                self.assert_bash_rooted(repo.bash(dev, "ls").run(),
                                        {"command": "ls", "description": "Run a command"},
                                        repo.tree())
                self.assert_team_record(repo, dev)

    def test_sentence_naming_another_folder_gives_no_team(self):
        """A sentence that names no team worktree of this repository makes a home role.

        The home checkout, a plain folder under .troy-teams, an ID that does not match
        the folder, a worktree of this repository outside .troy-teams, another
        repository's team worktree, and a folder that does not exist: each role's
        ``ls`` is silent and its record is in the home git folder, without team.

        Planted bug caught: a team sentence that names any folder accepted (8.2).
        """
        repo = self.make_repo()
        plain = repo.home / TEAMS / "f10"
        plain.mkdir(parents=True)
        write_file(plain, "README.md", "# Not a worktree\n")
        outside = repo.add_worktree(SCRATCH / unique("elsewhere") / "f08")
        other = self.make_repo()
        cases = {
            "the home checkout": ("F08", repo.home),
            "a plain folder under .troy-teams": ("F10", plain),
            "an ID that does not match the folder": ("F09", repo.tree()),
            "a worktree outside .troy-teams": ("F08", outside),
            "another repository's team worktree": ("F08", other.tree()),
            "a folder that does not exist": ("F11", repo.home / TEAMS / "f11"),
        }
        for name, (team, path) in cases.items():
            with self.subTest(case=name):
                dev = new_role("developer")
                repo.write_transcript(dev, brief(team_sentence(team, path)))
                self.assert_home_role(repo, dev, repo.first_call(dev), name)
        self.assertEqual([], repo.record_names(other.home_state()))
        self.assertEqual([], repo.record_names(other.team_state()))

    def test_brief_without_the_sentence_is_a_home_role(self):
        """A brief with no team sentence: the role works in the home checkout, as today."""
        repo = self.make_repo()
        dev = repo.home_role("developer")
        self.assert_home_role(repo, dev, repo.first_call(dev))
        self.assert_silent(repo.write(dev, repo.home / "src/pkg/app.py").run())

    def test_unreadable_brief_with_a_team_worktree_refuses_with_rule_team(self):
        """No transcript, or a first line that is not a JSON object: every changing call refused.

        Bash, PowerShell, Edit, Write, NotebookEdit, and Skill are each refused with
        rule team and one log line in the home checkout's log; no record is written
        anywhere. The first-line cases are text, a JSON array, a JSON string, and an
        empty file.
        """
        repo = self.make_repo()
        dev = repo.unknown_role("developer")
        calls = {
            "Bash": repo.bash(dev, "ls"),
            "PowerShell": repo.bash(dev, "Get-ChildItem", tool="PowerShell"),
            "Edit": repo.write(dev, repo.home / "src/pkg/app.py", tool="Edit"),
            "Write": repo.write(dev, repo.tree() / "src/pkg/app.py"),
            "NotebookEdit": repo.write(dev, repo.home / "src/pkg/x.ipynb", tool="NotebookEdit"),
            "Skill": repo.pre(dev, "Skill", {"skill": "code-review"}),
        }
        for tool, call in calls.items():
            with self.subTest(tool=tool):
                before = len(repo.log_lines(repo.home_state()))
                self.assert_denied(call.run(), UNREADABLE)
                lines = repo.log_lines(repo.home_state())[before:]
                self.assertEqual(1, len(lines), lines)
                self.assertEqual(("team", "deny", dev.agent_id, tool),
                                 (lines[0].get("rule"), lines[0].get("decision"),
                                  lines[0].get("agent_id"), lines[0].get("tool")))
        for name, raw in {"text": "not JSON\n", "a JSON array": "[1, 2]\n",
                          "a JSON string": '"Task: DV1"\n', "an empty file": ""}.items():
            with self.subTest(first_line=name):
                role = new_role("developer")
                repo.write_transcript(role, raw=raw)
                self.assert_denied(repo.first_call(role), UNREADABLE)
                self.assertEqual("team", self.last_line(repo, repo.home_state()).get("rule"))
        for state in repo.states().values():
            self.assertEqual([], repo.record_names(state), state)

    def test_unreadable_brief_without_a_team_worktree_falls_back(self):
        """Pair: with no team worktree, the same roles work as today in the home checkout."""
        repo = self.make_repo(teams=())
        dev = repo.unknown_role("developer")
        self.assert_home_role(repo, dev, repo.first_call(dev))
        broken = new_role("developer")
        repo.write_transcript(broken, raw="not JSON\n")
        self.assert_home_role(repo, broken, repo.first_call(broken))
        self.assertEqual([], repo.log_lines(repo.home_state()))

    def test_record_in_a_team_git_folder_is_found_by_agent_id(self):
        """A role with no transcript whose record is in the team's git folder is that team's.

        Its Bash call is rooted, not refused with rule team.

        Planted bug caught: a record looked up only in the home checkout's git folder (8.2).
        """
        repo = self.make_repo(teams=("f08", "f09"))
        dev = repo.unknown_role("developer")
        repo.write_record(repo.team_state("f09"), team_record(dev, repo.tree("f09"), "F09"))
        self.assert_bash_rooted(repo.bash(dev, "ls").run(),
                                {"command": "ls", "description": "Run a command"},
                                repo.tree("f09"))
        self.assert_nothing_at_home(repo)

    def test_record_in_the_home_git_folder_makes_a_home_role(self):
        """A record without worktree in the home git folder wins over the transcript.

        With a team sentence in the brief, or with no transcript, the role's ``ls`` is
        silent and no record appears in the team's git folder (contract A2, step 1).
        """
        repo = self.make_repo()
        with_brief = repo.team_role("developer")
        no_brief = repo.unknown_role("developer")
        for name, caller in (("team sentence", with_brief), ("no transcript", no_brief)):
            with self.subTest(case=name):
                repo.write_record(repo.home_state(), team_record(caller, None))
                self.assert_silent(repo.first_call(caller))
                self.assertIsNone(repo.read_record(repo.team_state(), caller.agent_id))

    def test_main_session_and_other_subagents_are_not_roles(self):
        """The main session's and a general-purpose fork's ``ls`` stay silent with teams present."""
        repo = self.make_repo()
        fork = Caller("general-purpose", "a" + uuid.uuid4().hex[:16], "general-purpose")
        for caller in (MAIN, fork):
            with self.subTest(caller=caller.label):
                self.assert_silent(repo.first_call(caller))
        self.assertEqual([], repo.log_lines(repo.home_state()))


class StartTests(TeamCase):
    """Contract A3: SubagentStart writes and changes no record while a team worktree exists."""

    def test_start_with_a_team_worktree_writes_no_record(self):
        """A team role, a home role, and a role with no transcript: no record anywhere.

        Planted bug caught: SubagentStart still writing a record into the home checkout (8.2).
        """
        repo = self.make_repo()
        for caller in (repo.team_role("developer"), repo.home_role("test-engineer"),
                       repo.unknown_role("architect")):
            with self.subTest(role=caller.label):
                self.assertEqual(0, repo.start(caller).run().code)
        for name, state in repo.states().items():
            self.assertEqual([], repo.record_names(state), name)

    def test_start_with_a_team_worktree_changes_no_record(self):
        """A stopped record at home and an open one in the team stay byte for byte."""
        repo = self.make_repo()
        stopped = repo.home_role("test-manager")
        home_path = repo.write_record(
            repo.home_state(), json.dumps(role_record(stopped, stopped=OLD_STOPPED), indent=3),
            name=stopped.agent_id)
        running = repo.team_role("developer")
        team_path = repo.write_record(
            repo.team_state(), json.dumps(team_record(running, repo.tree()), indent=3),
            name=running.agent_id)
        before = (home_path.read_bytes(), team_path.read_bytes())
        repo.project.write("src/pkg/app.py", "def run():\n    return 2\n")
        for caller in (stopped, running):
            self.assertEqual(0, repo.start(caller, session="session-new").run().code)
        self.assertEqual(before, (home_path.read_bytes(), team_path.read_bytes()))

    def test_start_without_a_team_worktree_is_as_today(self):
        """Pair: with no team worktree, SubagentStart writes the record at home, as today."""
        repo = self.make_repo(teams=())
        dev = repo.home_role("developer")
        self.assertEqual(0, repo.start(dev).run().code)
        record = repo.read_record(repo.home_state(), dev.agent_id)
        self.assertIsNotNone(record)
        self.assertIsNone(record.get("stopped"))


class RootingTests(TeamCase):
    """Contract A4: a team role's Bash, PowerShell, Glob, and Grep run in its worktree."""

    @classmethod
    def setUpClass(cls):
        """One repository with teams f08 and f09 for every test of the class."""
        cls.repo = TeamRepo(("f08", "f09"))
        cls.addClassCleanup(cls.repo.close)

    def started_role(self, name="developer", team="f08"):
        """A team role that has made its first call."""
        caller = self.repo.team_role(name, team)
        self.repo.first_call(caller)
        return caller

    def test_bash_is_rooted_with_every_key_kept(self):
        """``cd "<worktree>" && <command>``, no permission decision, every other key unchanged."""
        dev = self.started_role()
        commands = ("ls", "python -m pytest -q", "git status && git diff --stat",
                    'echo "a b" | wc -c', "cat <<'EOF' > notes.txt\nline\nEOF")
        for command in commands:
            with self.subTest(command=command):
                tool_input = {"command": command, "description": "Run the tests",
                              "timeout": 600000, "run_in_background": False}
                out = self.repo.pre(dev, "Bash", tool_input).run()
                self.assert_bash_rooted(out, tool_input, self.repo.tree())

    def test_powershell_is_rooted_with_set_location(self):
        """``Set-Location -LiteralPath '<worktree>'; <command>`` with every other key kept.

        Planted bug caught: the rooting skipped for PowerShell (8.2).
        """
        dev = self.started_role()
        for command in ("Get-ChildItem", "git status; Get-Location"):
            with self.subTest(command=command):
                tool_input = {"command": command, "description": "List", "timeout": 120000}
                out = self.repo.pre(dev, "PowerShell", tool_input).run()
                self.assert_ps_rooted(out, tool_input, self.repo.tree())

    def test_powershell_doubles_a_single_quote_in_the_path(self):
        """A worktree path with ``'`` is quoted with the quote doubled.

        Planted bug caught: the rooting skipped for PowerShell (8.2).
        """
        repo = self.make_repo(parent=SCRATCH / unique("o'neil-"))
        dev = repo.team_role("developer")
        tool_input = {"command": "Get-ChildItem"}
        quoted = self.assert_ps_rooted(repo.pre(dev, "PowerShell", tool_input).run(), tool_input,
                                       repo.tree())
        self.assertIn("''", quoted)

    def test_command_that_already_starts_in_the_worktree_is_left_alone(self):
        """``cd "<wt>"``, ``cd '<wt>'``, or ``cd <wt>``, then ``&&`` or ``;``: nothing printed."""
        dev = self.started_role()
        tree = self.repo.tree().as_posix()
        for cd in (f'cd "{tree}"', f"cd '{tree}'", f"cd {tree}"):
            for joint in (" && ", "; "):
                with self.subTest(command=cd + joint + "ls"):
                    self.assert_silent(self.repo.bash(dev, cd + joint + "ls").run())

    def test_command_that_starts_elsewhere_is_rooted(self):
        """``cd src && ls`` and ``cd <other team> && ls`` are rooted like any other command."""
        dev = self.started_role()
        for command in ("cd src && ls", f'cd "{self.repo.tree("f09").as_posix()}" && ls', "pwd"):
            with self.subTest(command=command):
                tool_input = {"command": command, "description": "Run a command"}
                self.assert_bash_rooted(self.repo.pre(dev, "Bash", tool_input).run(), tool_input,
                                        self.repo.tree())

    def test_refused_call_of_a_team_role_has_no_updated_input(self):
        """git commit, git push, and ``python -`` are refused as today, logged in the team's log.

        Planted bug named here: a team role's refusal logged in the home checkout.
        """
        repo = self.make_repo()
        dev = repo.team_role("developer")
        repo.first_call(dev)
        cases = (("git commit -m 'Add x'", "git"), ("git push origin HEAD", "git"),
                 ("python - <<'EOF'\nprint(1)\nEOF", "python-stdin"))
        for command, rule in cases:
            with self.subTest(command=command):
                out = repo.bash(dev, command).run()
                self.assert_denied(out)
                self.assertNotIn("updatedInput", out.data()["hookSpecificOutput"])
                last = self.last_line(repo, repo.team_state())
                self.assertEqual((rule, "deny"), (last.get("rule"), last.get("decision")))
        self.assert_nothing_at_home(repo)

    def test_stopped_team_record_refuses_every_changing_call(self):
        """A stopped record in the team's git folder: rule stopped, logged in the team's log."""
        repo = self.make_repo()
        dev = repo.unknown_role("developer")
        record = team_record(dev, repo.tree(), stopped=OLD_STOPPED, background=["t1"])
        repo.write_record(repo.team_state(), record)
        calls = (repo.bash(dev, "ls"), repo.bash(dev, "Get-ChildItem", tool="PowerShell"),
                 repo.write(dev, repo.tree() / "src/pkg/app.py"),
                 repo.write(dev, repo.tree() / "src/pkg/app.py", tool="Edit"),
                 repo.write(dev, repo.tree() / "src/pkg/x.ipynb", tool="NotebookEdit"),
                 repo.pre(dev, "Skill", {"skill": "code-review"}))
        for call in calls:
            with self.subTest(tool=call.payload["tool_name"]):
                self.assert_denied(call.run(), STOPPED_REASON)
                self.assertEqual("stopped", self.last_line(repo, repo.team_state()).get("rule"))
        self.assertEqual(record, repo.read_record(repo.team_state(), dev.agent_id))
        self.assert_nothing_at_home(repo)

    def test_path_less_glob_and_grep_get_the_worktree(self):
        """A Glob or Grep with no path, or an empty one, gets the worktree as ``path``."""
        dev = self.started_role()
        cases = (("Glob", {"pattern": "**/*.py"}), ("Glob", {"pattern": "**/*.md", "path": ""}),
                 ("Grep", {"pattern": "def run", "output_mode": "content", "-n": True}),
                 ("Grep", {"pattern": "import", "path": "", "glob": "*.py"}))
        for tool, tool_input in cases:
            with self.subTest(tool=tool, tool_input=tool_input):
                out = self.repo.pre(dev, tool, tool_input).run()
                self.assert_search_rooted(out, tool_input, self.repo.tree())

    def test_glob_and_grep_with_a_path_or_an_absolute_pattern_are_unchanged(self):
        """A path, the worktree as path, or an absolute pattern: silent; the plugin: allow.

        Planted bug caught: a Glob with a path rewritten (8.2).
        """
        dev = self.started_role()
        home, tree = self.repo.home, self.repo.tree()
        silent = (("Glob", {"pattern": "**/*.py", "path": str(home)}),
                  ("Glob", {"pattern": "**/*.py", "path": str(tree / "src")}),
                  ("Glob", {"pattern": home.as_posix() + "/src/**/*.py"}),
                  ("Grep", {"pattern": "def run", "path": str(home / "src")}))
        for tool, tool_input in silent:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assert_silent(self.repo.pre(dev, tool, tool_input).run())
        plugin = {"pattern": "**/*.md", "path": str(PLUGIN_ROOT / "skills")}
        self.assert_allowed_read(self.repo.pre(dev, "Glob", plugin).run())

    def test_glob_of_a_home_role_the_main_session_and_an_unknown_role_is_unchanged(self):
        """A path-less Glob of a home role, the main session, or an unknown role is silent."""
        for caller in (self.repo.home_role("developer"), MAIN,
                       self.repo.unknown_role("developer")):
            with self.subTest(caller=caller.label):
                self.assert_silent(self.repo.pre(caller, "Glob", {"pattern": "**/*.py"}).run())
                self.assert_silent(self.repo.pre(caller, "Grep", {"pattern": "def run"}).run())


if __name__ == "__main__":
    unittest.main()
