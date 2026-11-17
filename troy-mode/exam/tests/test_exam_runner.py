"""The run group, its pieces (F16 design 11.3, 11.5, probes A and A2, 14.1).

The command line of section 11.3 with tstack's names; the driver prompt
holds the brief exactly; a mangled brief voids the run (brief_arrived); the
cost is read per model (read_stream); the report is found in
SubagentHandback or the last message (parse_role, role_report); the run's
folders are deleted (cleanup); a process left behind is found and ended
(processes_with, end_tree). test_exam_cli.py runs the same through
troy_exam.py with the stand-in CLI.
"""

import json
import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

from exam_helpers import (HAIKU, SONNET, assistant_line, git, make_repo, new_dir, same_path,
                          text_block, tool_result, tool_use, user_line, wait_until, word_hits,
                          write_file)
from troyexam import AGENT_PREFIX, INSTALLED_OFF
from troyexam.errors import ExamError
from troyexam.runner import (BEGIN, END, SESSION_VARIABLES, brief_arrived, brief_between,
                             child_env, cleanup, cli_command, cli_version, command_line,
                             driver_prompt, end_tree, find_cli, processes_with)
from troyexam.transcript import (config_dir, folder_key, parse_role, read_role, read_stream,
                                 role_report, session_dir)

BRIEF = ("Task: DV1, write the mock of F01's interfaces.\n"
         "Item: F01, [F01 3/6 mock] Count words\n"
         "Read first:\n- docs/rules.md\n- docs/features/F01-count-words/design.md\n"
         "Input: None\nRound: None\n"
         "Checks to run:\n- 'mamba' run -p 'C:\\envs\\x' ruff check\n"
         "- python .troy-mode/checks/troy_check.py code --title '[F01 3/6 mock] Count words' "
         "--base origin/main\n")
REPORT = ("Role: Developer\nTask: DV1, F01\nResult: done\nChanged files: src/wordcount/f01.py\n"
          "Checks: None\nSummary: The mock is written.\nFindings: None\nQuestion: None\n")


class FindCliTests(unittest.TestCase):
    """find_cli: TROY_EXAM_CLI, else the newest bundled claude.exe (design 11.3)."""

    def test_the_variable_names_the_cli(self):
        """An existing file named by TROY_EXAM_CLI."""
        path = write_file(new_dir("cli"), "standin.py", "print(1)\n")
        self.assertTrue(same_path(find_cli({"TROY_EXAM_CLI": str(path)}), path))

    def test_a_missing_file_named_by_the_variable_raises(self):
        """TROY_EXAM_CLI must exist."""
        missing = new_dir("cli") / "nothing.exe"
        with self.assertRaises(ExamError):
            find_cli({"TROY_EXAM_CLI": str(missing)})

    def test_the_newest_bundled_version_by_number(self):
        """2.1.325 beats 2.1.9 and 2.1.30: versions compare as numbers, not as text."""
        local = new_dir("appdata")
        for account, version in (("claude_aaa", "2.1.9"), ("claude_aaa", "2.1.30"),
                                 ("claude_bbb", "2.1.325"), ("claude_bbb", "2.0.999")):
            write_file(local, f"Claude-Data/{account}/claude-code/{version}/h{version}/claude.exe",
                       b"MZ")
        found = find_cli({"LOCALAPPDATA": str(local)})
        expected = local / "Claude-Data/claude_bbb/claude-code/2.1.325/h2.1.325/claude.exe"
        self.assertTrue(same_path(found, expected), found)

    def test_no_cli_raises(self):
        """No variable and no bundled CLI: ExamError."""
        with self.assertRaises(ExamError):
            find_cli({"LOCALAPPDATA": str(new_dir("appdata"))})


class CliTests(unittest.TestCase):
    """cli_command and cli_version (contract runner.py)."""

    def test_a_python_stand_in_runs_with_this_python(self):
        """[sys.executable, path] for .py, [path] otherwise."""
        stand_in = Path("/x/standin.py")
        self.assertEqual(cli_command(stand_in), [sys.executable, str(stand_in)])
        exe = Path("C:/Claude-Data/a/claude-code/2.1.325/h/claude.exe")
        self.assertEqual(cli_command(exe), [str(exe)])

    def test_version_from_the_bundle_folder(self):
        """.../claude-code/<version>/<hash>/claude.exe gives <version>, without running it."""
        exe = Path("C:/Claude-Data/a/claude-code/2.1.325/0a1b2c/claude.exe")
        self.assertEqual(cli_version(exe), "2.1.325")

    def test_version_from_the_cli_itself(self):
        """Otherwise the first word of `<cli> --version`."""
        path = write_file(new_dir("cli"), "standin.py",
                          "import sys\nprint('2.1.330 (Claude Code)')\n")
        self.assertEqual(cli_version(path), "2.1.330")


class DriverPromptTests(unittest.TestCase):
    """driver_prompt and brief_between (design 11.3, probe A2)."""

    def test_the_brief_comes_back_exactly(self):
        """The text between BEGIN and END is the brief without its last newline."""
        prompt = driver_prompt("developer", "sonnet", "high", BRIEF)
        self.assertEqual(brief_between(prompt), BRIEF[:-1])
        lines = prompt.split("\n")
        self.assertIn(BEGIN, lines)
        self.assertIn(END, lines)
        self.assertEqual((BEGIN, END), ("BEGIN", "END"))

    def test_quotes_backslashes_and_unicode_survive(self):
        """A brief with quotes, backticks, backslashes, $, and Chinese text is copied as is."""
        brief = 'Input: "a\\b" is `x`, $HOME and 修改记录\nRound: 2\n'
        self.assertEqual(brief_between(driver_prompt("code-reviewer", "opus", "max", brief)),
                         brief[:-1])

    def test_the_prompt_names_the_agent_call(self):
        """subagent_type tstack:troy-<role>, the model, the effort, run_in_background false."""
        prompt = driver_prompt("test-manager", "opus", "max", BRIEF)
        self.assertIn(AGENT_PREFIX + "test-manager", prompt)
        self.assertIn("tstack:troy-test-manager", prompt)
        self.assertIn("opus", prompt)
        self.assertIn("max", prompt)
        self.assertIn("run_in_background", prompt)
        self.assertIn("false", prompt.lower())
        self.assertIn("Agent", prompt)

    def test_no_exam_word(self):
        """The driver's own words hold none (design 6.1)."""
        outside = driver_prompt("developer", "sonnet", "high", BRIEF).replace(BRIEF[:-1], "")
        self.assertEqual(word_hits(outside), [])


class CommandLineTests(unittest.TestCase):
    """command_line: section 11.3's command with tstack's names."""

    def test_the_designs_command(self):
        """Every option of 11.3, in order, with the cap to two decimals."""
        cli = Path("C:/Claude-Data/a/claude-code/2.1.325/h/claude.exe")
        plugin = Path("C:/work/runs/qhzwtd/tstack")
        session = "4f6c1d2e-0000-4000-8000-000000000001"
        self.assertEqual(command_line(cli, "DRIVER", plugin, session, 2.5), [
            str(cli), "-p", "DRIVER", "--model", "haiku", "--plugin-dir", str(plugin),
            "--settings", '{"enabledPlugins":{"tstack@tstack":false}}',
            "--permission-mode", "auto", "--permission-prompts", "none",
            "--allowedTools", "Agent", "--output-format", "stream-json", "--verbose",
            "--session-id", session, "--max-budget-usd", "2.50"])

    def test_sonnet_driver_and_a_stand_in(self):
        """The retry after a mangled brief uses a sonnet main session (11.5)."""
        cli = Path("/x/standin.py")
        line = command_line(cli, "P", Path("/w/tstack"), "s", 35, driver_model="sonnet")
        self.assertEqual(line[:2], [sys.executable, str(cli)])
        self.assertEqual(line[line.index("--model") + 1], "sonnet")
        self.assertEqual(line[line.index("--settings") + 1], INSTALLED_OFF)
        self.assertEqual(line[-2:], ["--max-budget-usd", "35.00"])


class ChildEnvTests(unittest.TestCase):
    """child_env: the session's environment (design 11.3)."""

    def setUp(self):
        """A parent environment as a nested Claude session would see it."""
        self.project = Path("C:/work/runs/qhzwtd/wordcount")
        self.bin = Path("C:/work/runs/qhzwtd/bin")
        self.root = Path("C:/work")
        self.parent = {name: "1" for name in SESSION_VARIABLES}
        self.parent.update({"PATH": os.pathsep.join(["/usr/bin", "/bin"]), "HOME": "/home/t",
                            "TROY_EXAM_ROOT": "C:/work", "TROY_EXAM_CLI": "C:/cli.py",
                            "MY_SCORE_FILE": "x", "NOTE": "C:/sandbox/one", "KEEP_ME": "yes"})

    def env(self, **extra):
        """child_env of the parent plus extra variables."""
        return child_env({**self.parent, **extra}, python="C:/py/python.exe",
                         env_prefix="C:/work/envs/wordcount-ab12", project=self.project,
                         bin_dir=self.bin, work_root=self.root)

    def test_session_variables_are_dropped(self):
        """CLAUDECODE, CLAUDE_CODE_ENTRYPOINT, CLAUDE_CODE_SESSION_ID, and the others."""
        env = self.env()
        self.assertTrue({"CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID"}
                        <= set(SESSION_VARIABLES))
        for name in SESSION_VARIABLES:
            self.assertNotIn(name, env)

    def test_exam_variables_and_exam_words_are_dropped(self):
        """TROY_EXAM_*, and any variable whose name or value holds an exam word."""
        env = self.env()
        for name in ("TROY_EXAM_ROOT", "TROY_EXAM_CLI", "MY_SCORE_FILE", "NOTE"):
            self.assertNotIn(name, env)
        for name, value in env.items():
            self.assertEqual(word_hits(name) + word_hits(value), [], name)

    def test_other_variables_are_kept(self):
        """An unrelated variable passes through."""
        env = self.env()
        self.assertEqual((env["KEEP_ME"], env["HOME"]), ("yes", "/home/t"))

    def test_the_runs_variables(self):
        """Python, the environment prefix, PYTHONPATH, uv's cache, and MSYS_NO_PATHCONV."""
        env = self.env()
        self.assertEqual(env["TROY_MODE_PYTHON"], "C:/py/python.exe")
        self.assertEqual(env["TROY_MODE_ENV_PREFIX"], "C:/work/envs/wordcount-ab12")
        self.assertEqual(Path(env["PYTHONPATH"]), self.project / "src")
        self.assertEqual(Path(env["UV_CACHE_DIR"]), self.root / "uv-cache")
        self.assertEqual(env["MSYS_NO_PATHCONV"], "1")

    def test_path_starts_with_the_gh_stand_in(self):
        """bin first, then the parent's PATH."""
        env = self.env()
        self.assertEqual(env["PATH"], str(self.bin) + os.pathsep + self.parent["PATH"])

    def test_defaults_and_kept_values(self):
        """Git Bash and MAMBA_ROOT_PREFIX: kept when the parent sets them, else Troy's."""
        env = self.env()
        self.assertEqual(env["CLAUDE_CODE_GIT_BASH_PATH"], r"D:\Program Files\Git\bin\bash.exe")
        self.assertEqual(env["MAMBA_ROOT_PREFIX"], r"D:\miniforge3")
        env = self.env(CLAUDE_CODE_GIT_BASH_PATH="E:/Git/bin/bash.exe",
                       MAMBA_ROOT_PREFIX="E:/mamba")
        self.assertEqual(env["CLAUDE_CODE_GIT_BASH_PATH"], "E:/Git/bin/bash.exe")
        self.assertEqual(env["MAMBA_ROOT_PREFIX"], "E:/mamba")


class BriefArrivedTests(unittest.TestCase):
    """brief_arrived: the role's first message must equal the brief (design 4.3, 11.5)."""

    def transcript(self, first: str):
        """A transcript whose first message is the text."""
        return parse_role([user_line(first)], None)

    def test_the_same_brief_arrived(self):
        """Exactly the brief."""
        self.assertTrue(brief_arrived(self.transcript(BRIEF), BRIEF))

    def test_line_ends_and_outer_whitespace_do_not_matter(self):
        """CRLF against LF, and whitespace at either end."""
        self.assertTrue(brief_arrived(self.transcript(BRIEF.replace("\n", "\r\n")), BRIEF))
        self.assertTrue(brief_arrived(self.transcript("\n  " + BRIEF.strip() + "  \n\n"), BRIEF))

    def test_a_changed_brief_did_not_arrive(self):
        """One word changed, a line dropped, a sentence added, or a summary."""
        for first in (BRIEF.replace("DV1", "DV2"), BRIEF.replace("Round: None\n", ""),
                      BRIEF + "Please be careful.\n", "Write the F01 mock.",
                      BRIEF.replace("'C:\\envs\\x'", "'C:/envs/x'"), f"{BEGIN}\n{BRIEF}",
                      BRIEF.rstrip() + f"\n{END}\n{END}", BRIEF.rstrip() + f" {END}"):
            with self.subTest(first=first[:40]):
                self.assertFalse(brief_arrived(self.transcript(first), BRIEF))

    def test_the_end_line_after_the_brief_does_not_matter(self):
        """The trial's main session copied the END line of its prompt after the brief, 3 times in 60.

        The line is the driver prompt's marker, not a change to the brief, so the run counts.
        """
        self.assertTrue(brief_arrived(self.transcript(BRIEF.rstrip() + f"\n{END}"), BRIEF))
        self.assertTrue(brief_arrived(self.transcript(BRIEF.rstrip() + f"\r\n{END}\r\n"), BRIEF))


class TranscriptTests(unittest.TestCase):
    """The role's transcript (design 11.3, probes A and A2, contract transcript.py)."""

    def lines(self) -> list:
        """A transcript with the line types the CLI writes."""
        return [
            user_line(BRIEF),
            json.dumps({"type": "attachment", "attachment": {"type": "skill_listing"}}),
            assistant_line({"type": "thinking", "thinking": "Let me start."},
                           text_block("I read the rules first."),
                           tool_use("Read", {"file_path": "D:/p/docs/rules.md"}, "t1")),
            user_line([tool_result("t1", "rules")]),
            json.dumps({"type": "api-request", "request": {"messages": []}}),
            assistant_line(tool_use("Bash", {"command": "git commit -m x"}, "t2")),
            user_line([tool_result("t2", "refused by a hook", True)], toolDenialKind="hook"),
            assistant_line(tool_use("Bash", {"command": "ruff check"}, "t3")),
            user_line([tool_result("t3", "1 error", True)]),
            user_line("Caveat: meta text.", isMeta=True),
            json.dumps({"type": "api-request-blob", "message": {"content": [
                tool_use("Write", {"file_path": "x"}, "t9"), text_block("repeated")]}}),
            assistant_line(text_block("The mock is written.")),
            assistant_line(tool_use("SubagentHandback", {"message": REPORT}, "t4")),
            "",
        ]

    def test_parse_role(self):
        """First message, calls in order with refusals, texts, the handback, and events."""
        meta = {"agentType": "tstack:troy-developer", "model": "sonnet", "description": "x"}
        t = parse_role(self.lines(), meta)
        self.assertEqual(t.first_message, BRIEF)
        self.assertEqual([c.name for c in t.calls], ["Read", "Bash", "Bash", "SubagentHandback"])
        self.assertEqual([c.denied for c in t.calls], [False, True, False, False])
        self.assertEqual(t.calls[0].input, {"file_path": "D:/p/docs/rules.md"})
        self.assertEqual(t.texts, ["I read the rules first.", "The mock is written."])
        self.assertEqual(t.handback, REPORT)
        self.assertEqual((t.agent_type, t.model), ("tstack:troy-developer", "sonnet"))
        self.assertEqual(t.events, [("text", 0), ("call", 0), ("call", 1), ("call", 2),
                                    ("text", 1), ("call", 3)])

    def test_first_message_as_blocks(self):
        """A first message given as a list of text blocks."""
        t = parse_role([user_line([text_block(BRIEF)])], None)
        self.assertEqual(t.first_message, BRIEF)
        self.assertIsNone(t.agent_type)
        self.assertIsNone(t.handback)

    def test_role_report_prefers_the_handback(self):
        """SubagentHandback's message, else the last text, else None (design 11.3)."""
        self.assertEqual(role_report(parse_role(self.lines(), None)), REPORT)
        no_handback = [line for line in self.lines() if "SubagentHandback" not in line]
        no_handback.append(assistant_line(text_block(REPORT)))
        self.assertEqual(role_report(parse_role(no_handback, None)), REPORT)
        self.assertIsNone(role_report(parse_role([user_line(BRIEF)], None)))

    def test_read_role_finds_the_one_transcript_and_its_meta(self):
        """agent-<ID>.jsonl with agent-<ID>.meta.json beside it."""
        folder = new_dir("subagents")
        write_file(folder, "agent-a1b2c3.jsonl", "\n".join(self.lines()) + "\n")
        write_file(folder, "agent-a1b2c3.meta.json",
                   json.dumps({"agentType": "tstack:troy-developer", "model": "sonnet"}))
        t = read_role(folder)
        self.assertEqual(t.first_message, BRIEF)
        self.assertEqual(t.agent_type, "tstack:troy-developer")
        self.assertEqual(role_report(t), REPORT)

    def test_read_role_without_a_transcript_raises(self):
        """No agent-*.jsonl: ExamError."""
        with self.assertRaises(ExamError):
            read_role(new_dir("subagents"))

    def test_folder_key(self):
        """Every character but ASCII letters and digits becomes a dash."""
        self.assertEqual(folder_key(r"D:\Troy\troy-mode-work\qhzwtd\recipe-menu"),
                         "D--Troy-troy-mode-work-qhzwtd-recipe-menu")
        self.assertEqual(folder_key("/tmp/a b/c_d.e"), "-tmp-a-b-c-d-e")

    def test_config_dir_and_session_dir(self):
        """$CLAUDE_CONFIG_DIR, else ~/.claude; then projects/<key>/<session ID>."""
        config = new_dir("config")
        self.assertEqual(config_dir({"CLAUDE_CONFIG_DIR": str(config)}), config)
        self.assertEqual(config_dir({}), Path.home() / ".claude")
        project = Path("/w/runs/abcdef/wordcount")
        sid = "11111111-2222-4333-8444-555555555555"
        self.assertEqual(session_dir({"CLAUDE_CONFIG_DIR": str(config)}, project, sid),
                         config / "projects" / folder_key(str(project)) / sid)


class StreamTests(unittest.TestCase):
    """read_stream: the result event (design 11.3, probes A2 and C)."""

    def result(self, **fields) -> str:
        """A result event line."""
        event = {"type": "result", "subtype": "success", "is_error": False, "result": REPORT,
                 "session_id": "s1", "total_cost_usd": 0.045,
                 "modelUsage": {HAIKU: {"inputTokens": 9, "costUSD": 0.003},
                                SONNET: {"inputTokens": 99, "costUSD": 0.042}}}
        event.update(fields)
        return json.dumps(event)

    def test_cost_per_model(self):
        """total_cost_usd and modelUsage's costUSD by model ID."""
        lines = [json.dumps({"type": "system", "subtype": "init"}),
                 json.dumps({"type": "assistant", "message": {"content": []}}), self.result(), ""]
        found = read_stream(lines)
        self.assertTrue(found.found)
        self.assertAlmostEqual(found.total_cost, 0.045)
        self.assertEqual(found.costs, {HAIKU: 0.003, SONNET: 0.042})
        self.assertEqual((found.is_error, found.subtype, found.session_id),
                         (False, "success", "s1"))
        self.assertEqual(found.text, REPORT)
        self.assertFalse(found.limit_hit)
        self.assertFalse(found.cap_hit)

    def test_the_last_result_counts(self):
        """A background Agent call gives two result events (probe A): the last one counts."""
        early = self.result(total_cost_usd=0.01, modelUsage={HAIKU: {"costUSD": 0.01}})
        found = read_stream([early, self.result()])
        self.assertAlmostEqual(found.total_cost, 0.045)
        self.assertEqual(set(found.costs), {HAIKU, SONNET})

    def test_no_result_event(self):
        """found is false."""
        self.assertFalse(read_stream([json.dumps({"type": "system", "subtype": "init"})]).found)

    def test_cap_and_limit(self):
        """error_max_budget_usd (probe C), and "You've hit your ... limit"."""
        cap = read_stream([self.result(subtype="error_max_budget_usd", is_error=True,
                                       result=None)])
        self.assertTrue(cap.cap_hit)
        self.assertTrue(cap.is_error)
        limit = read_stream([self.result(is_error=True,
                                         result="You've hit your 5-hour limit \u00b7 resets 3pm")])
        self.assertTrue(limit.limit_hit)
        self.assertFalse(limit.cap_hit)
        other = read_stream([self.result(is_error=True, result="You hit a snag; try again")])
        self.assertFalse(other.limit_hit)


class CleanupTests(unittest.TestCase):
    """cleanup: the run's folders are deleted, and those left are listed (11.3)."""

    def test_folders_with_git_objects_are_deleted(self):
        """A run folder holding a repository (read-only objects on Windows) goes."""
        folder = new_dir("runf")
        make_repo(folder / "wordcount", {"a.txt": "a\n"})
        git(folder, "clone", "-q", "--bare", str(folder / "wordcount"), str(folder / "w.git"))
        other = new_dir("projf")
        write_file(other, "subagents/agent-1.jsonl", "{}\n")
        self.assertEqual(cleanup([folder, other]), [])
        self.assertFalse(folder.exists())
        self.assertFalse(other.exists())

    def test_a_missing_folder_is_not_left(self):
        """Nothing to delete is not a folder left."""
        self.assertEqual(cleanup([new_dir("gone") / "never"]), [])

    def test_a_folder_that_cannot_be_deleted_is_listed(self):
        """A file held open (Windows) or a read-only folder (POSIX) keeps it."""
        folder = new_dir("stuck")
        inner = folder / "inner"
        path = write_file(inner, "held.txt", "x\n")
        if os.name == "nt":
            handle = open(path, "rb")  # noqa: SIM115  (held open on purpose)
            try:
                left = cleanup([folder])
            finally:
                handle.close()
        else:
            if hasattr(os, "geteuid") and os.geteuid() == 0:
                self.skipTest("root can delete from a read-only folder")
            os.chmod(inner, 0o500)
            try:
                left = cleanup([folder])
            finally:
                os.chmod(inner, 0o700)
        self.assertEqual(len(left), 1, left)
        self.assertTrue(same_path(left[0], folder), left)


class ProcessTests(unittest.TestCase):
    """processes_with and end_tree: a process the run left is found and ended (11.5, U5)."""

    def test_a_left_process_and_its_child_are_found_and_ended(self):
        """A sleeper holding a marker path, with a child holding it too."""
        marker = str(new_dir("left") / f"m{uuid.uuid4().hex[:8]}")
        child_code = ("import subprocess, sys, time; "
                      "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', "
                      "sys.argv[1]]); time.sleep(60)")
        proc = subprocess.Popen([sys.executable, "-c", child_code, marker],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        try:
            self.assertTrue(wait_until(lambda: len(processes_with(marker)) >= 2, 20),
                            processes_with(marker))
            found = processes_with(marker)
            self.assertIn(proc.pid, [pid for pid, _ in found])
            self.assertTrue(all(marker in line for _, line in found), found)
            self.assertNotIn(os.getpid(), [pid for pid, _ in found])
            end_tree(proc.pid)
            self.assertIsNotNone(proc.wait(timeout=20))
            self.assertTrue(wait_until(lambda: processes_with(marker) == [], 20),
                            processes_with(marker))
        finally:
            if proc.poll() is None:
                proc.kill()

    def test_no_process_holds_an_unused_marker(self):
        """An empty list."""
        self.assertEqual(processes_with(f"nothing-{uuid.uuid4().hex}"), [])


if __name__ == "__main__":
    unittest.main()
