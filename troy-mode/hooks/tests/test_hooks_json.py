"""hooks.json group (F05 design sections 2, 3, and 10, and 13.1; contract section 8).

hooks/hooks.json parses; its six events, matchers, and timeouts are those of
F05 design section 3 and F13 design 7.1; and its commands name existing
scripts. The commands are also run in bash, where one is found, to check that
they reach troy_hook.py, and that a missing Python blocks in a troy-mode
project and passes elsewhere (D39).

F13 (design sections 7.1, 9, and 11.1) adds the sixth event,
UserPromptExpansion: one group whose matcher, applied with Python's re.search
because Claude Code tests a matcher unanchored, matches every name
test_mode_guard.py refuses and none it lets through. The F13 planted bugs
these tests catch are listed in test_mode_guard.py.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from hook_helpers import (
    DEV, HOOKS_JSON, MAIN, NEUTRAL, REPO, SCRATCH, HookRun, HookTestCase, Project, hook_env,
    hook_input, write_call,
)
from test_mode_guard import LET_THROUGH, REFUSED

# Design section 3 (version 1.1): (event, matcher, has the if rule). The trial
# of design 13.3 showed that the if rule filters only Read, so Glob|Grep has
# its own entry without it, as design section 9 planned. F13 design 7.1 adds
# UserPromptExpansion.
GUARD_EVENT = "UserPromptExpansion"
GUARD_MATCHER = "^([^:]+:)?(poteto-mode|no-comments)$"
EXPECTED = (
    ("SessionStart", None, False),
    ("SubagentStart", "^troy-pstack:troy-", False),
    ("PreToolUse", "Bash|PowerShell|Edit|Write|NotebookEdit|Skill", False),
    ("PreToolUse", "Read", True),
    ("PreToolUse", "Glob|Grep", False),
    ("PostToolUse", "Bash|PowerShell|Skill", False),
    ("SubagentStop", "^troy-pstack:troy-", False),
    (GUARD_EVENT, GUARD_MATCHER, False),
)
SCOPE_TOOLS = {"Bash", "PowerShell", "Edit", "Write", "NotebookEdit", "Skill"}
READ_TOOLS = {"Read", "Glob", "Grep"}
IF_RULE = "Read(//**/troy-pstack/**)"
PLUGIN_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"']+)")


def if_rule(group, hook):
    """Returns the if rule of one hook entry, or None.

    The contract puts it on the hook object; its placement is being
    confirmed against the Claude Code documentation, so this is the one
    place to change if it moves.
    """
    del group
    return hook.get("if")


def tool_set(matcher):
    """Splits a tool matcher into its alternatives."""
    return set(matcher.split("|"))


def find_bash():
    """Finds bash: Git Bash on Windows (never WSL's bash), bash elsewhere."""
    if os.name != "nt":
        return shutil.which("bash")
    proc = subprocess.run(["git", "--exec-path"], capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    git_root = Path(proc.stdout.strip()).parents[2]
    for rel in ("usr/bin/bash.exe", "bin/bash.exe"):
        if (git_root / rel).is_file():
            return str(git_root / rel)
    return None


class HooksJsonTests(unittest.TestCase):
    """The file's structure."""

    @classmethod
    def setUpClass(cls):
        """Parses hooks/hooks.json."""
        cls.data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))

    def groups(self):
        """Lists (event, group) pairs in file order."""
        return [(event, group) for event, groups in self.data["hooks"].items()
                for group in groups]

    def test_top_level_shape(self):
        """The file holds hooks and, optionally, a description."""
        self.assertIsInstance(self.data, dict)
        self.assertIn("hooks", self.data)
        self.assertLessEqual(set(self.data), {"description", "hooks"})
        self.assertIsInstance(self.data["hooks"], dict)

    def found(self):
        """Lists (event, matcher or None, if rule or None) for every group."""
        result = []
        for event, group in self.groups():
            self.assertEqual(1, len(group["hooks"]), f"{event}: one hook per group")
            matcher = group.get("matcher")
            result.append((event, None if matcher in ("", "*") else matcher,
                           if_rule(group, group["hooks"][0])))
        return result

    def test_events_are_those_of_design_section_3(self):
        """Exactly the six events, one group each, and three for PreToolUse (F13 7.1 and 9)."""
        counts = {event: len(groups) for event, groups in self.data["hooks"].items()}
        self.assertEqual(6, len(counts), f"events: {sorted(counts)}")
        self.assertEqual({e for e, _, _ in EXPECTED}, set(counts))
        for event in ("SessionStart", "SubagentStart", "PostToolUse", "SubagentStop",
                      GUARD_EVENT):
            self.assertEqual(1, counts[event], event)
        self.assertEqual(3, counts["PreToolUse"], "the scope, Read, and Glob|Grep entries")

    def test_matchers_and_if_rules(self):
        """Each group has the matcher of F05 design 3 or F13 7.1, and no if rule but the read one.

        Planted bug caught: a UserPromptExpansion matcher without ^ (F13 11.2).
        """
        found = self.found()
        for event, matcher, _ in EXPECTED:
            if event == "PreToolUse":
                continue
            with self.subTest(event=event):
                match = [f for f in found if f[0] == event]
                self.assertEqual(1, len(match), f"groups found: {found}")
                if matcher is not None and not matcher.startswith("^"):
                    self.assertEqual(tool_set(matcher), tool_set(match[0][1] or ""))
                else:
                    self.assertEqual(matcher, match[0][1])
                self.assertIsNone(match[0][2], f"{event} has an if rule")

    def test_pretooluse_scope_and_read_entries(self):
        """PreToolUse: the scope entry and Glob|Grep without if, Read with it (design 1.1, 3, 9)."""
        pre = [(m, rule) for event, m, rule in self.found() if event == "PreToolUse"]
        self.assertTrue(all(m for m, _ in pre), f"PreToolUse groups need matchers: {pre}")
        scope = [(m, rule) for m, rule in pre if tool_set(m) == SCOPE_TOOLS]
        self.assertEqual(1, len(scope), f"PreToolUse groups: {pre}")
        self.assertIsNone(scope[0][1], "the scope entry has an if rule")
        reads = [(tool_set(m), rule) for m, rule in pre if tool_set(m) != SCOPE_TOOLS]
        union = set().union(*(tools for tools, _ in reads)) if reads else set()
        self.assertEqual(READ_TOOLS, union, f"read entries: {reads}")
        self.assertEqual(sum(len(tools) for tools, _ in reads), len(union),
                         f"a read tool is in two entries: {reads}")
        self.assertEqual(sorted([({"Read"}, IF_RULE), ({"Glob", "Grep"}, None)], key=str),
                         sorted(reads, key=str))

    def test_each_hook_is_a_bash_command_with_a_ten_second_timeout(self):
        """type command, shell bash, timeout 10, and a one-line command."""
        for event, group in self.groups():
            hook = group["hooks"][0]
            with self.subTest(event=event, matcher=group.get("matcher")):
                self.assertEqual("command", hook.get("type"))
                self.assertEqual("bash", hook.get("shell"))
                self.assertEqual(10, hook.get("timeout"))
                self.assertIsInstance(hook.get("command"), str)
                self.assertNotIn("\n", hook["command"])

    def test_commands_run_troy_hook_with_their_event(self):
        """Each command runs ${CLAUDE_PLUGIN_ROOT}/troy-mode/hooks/troy_hook.py <its event>."""
        for event, group in self.groups():
            command = group["hooks"][0]["command"]
            with self.subTest(event=event):
                self.assertRegex(command, r"\$\{CLAUDE_PLUGIN_ROOT\}/troy-mode/hooks/"
                                          r"troy_hook\.py[\"']?\s+" + event + r"\b")
                others = {e for e, _, _ in EXPECTED} - {event}
                for other in others:
                    self.assertNotRegex(command, r"troy_hook\.py[\"']?\s+" + other + r"\b")

    def test_commands_pick_the_interpreter_as_design_section_2_says(self):
        """TROY_MODE_PYTHON first, else python or python3 by OSTYPE; the project test for D39."""
        for event, group in self.groups():
            command = group["hooks"][0]["command"]
            with self.subTest(event=event):
                self.assertIn("TROY_MODE_PYTHON", command)
                self.assertIn("OSTYPE", command)
                self.assertRegex(command, r"\bpython3\b")
                self.assertRegex(command, r"\bpython\b(?!3)")
                self.assertRegex(command, r"\$\{?CLAUDE_PROJECT_DIR\}?/\.troy-mode")

    def guard_group(self):
        """Returns the one UserPromptExpansion group."""
        groups = self.data["hooks"].get(GUARD_EVENT)
        self.assertIsInstance(groups, list, f"hooks.json has no {GUARD_EVENT} entry")
        self.assertEqual(1, len(groups), f"{GUARD_EVENT}: one group")
        return groups[0]

    def test_user_prompt_expansion_entry(self):
        """F13 7.1: the design's matcher, one bash command hook, timeout 10, and no if rule.

        Planted bugs caught: a matcher without ^, and no-comments left out of
        the matcher (F13 11.2).
        """
        group = self.guard_group()
        self.assertEqual(GUARD_MATCHER, group.get("matcher"))
        self.assertNotIn("if", group)
        self.assertEqual(1, len(group.get("hooks", [])), f"{GUARD_EVENT}: one hook")
        hook = group["hooks"][0]
        self.assertEqual({"type": "command", "shell": "bash", "timeout": 10},
                         {key: hook.get(key) for key in ("type", "shell", "timeout")})
        self.assertNotIn("if", hook)
        self.assertRegex(hook.get("command", ""),
                         r"\$\{CLAUDE_PLUGIN_ROOT\}/troy-mode/hooks/troy_hook\.py[\"']?\s+"
                         r"UserPromptExpansion$")

    def test_user_prompt_expansion_command_equals_the_others(self):
        """F13 7.1: the command is every other entry's command with the event word changed.

        So the interpreter pick, TROY_MODE_PYTHON, and the missing-Python rule
        stay F05's (F05 section 10).
        """
        def generic(command, event):
            """Replaces the event word after troy_hook.py with a placeholder."""
            return re.sub(r"(troy_hook\.py[\"']?\s+)" + re.escape(event) + r"\b",
                          lambda match: match.group(1) + "<event>", command)

        guard = generic(self.guard_group()["hooks"][0]["command"], GUARD_EVENT)
        self.assertIn("<event>", guard, "the command does not name UserPromptExpansion")
        for event, group in self.groups():
            if event == GUARD_EVENT:
                continue
            with self.subTest(event=event, matcher=group.get("matcher")):
                self.assertEqual(generic(group["hooks"][0]["command"], event), guard)

    def test_user_prompt_expansion_matcher_matches_only_the_guarded_names(self):
        """F13 11.1: re.search with the file's matcher hits each refused name and no other.

        Claude Code tests a matcher unanchored (JavaScript RegExp.test), so
        this uses re.search, not re.fullmatch (F13 contract 6).

        Planted bugs caught: a matcher without ^ (my-poteto-mode and
        a:b:poteto-mode match it); no-comments left out of the matcher (F13
        11.2).
        """
        matcher = re.compile(self.guard_group().get("matcher") or "")
        for name in REFUSED:
            with self.subTest(refused=name):
                self.assertIsNotNone(matcher.search(name), f"{matcher.pattern} misses {name}")
        for name in LET_THROUGH + ("",):
            with self.subTest(let_through=name):
                self.assertIsNone(matcher.search(name), f"{matcher.pattern} matches {name!r}")

    def test_description_names_f05_and_f13(self):
        """The top-level description names F13 next to F05 (F13 7.1)."""
        description = self.data.get("description", "")
        self.assertRegex(description, r"\bF05\b")
        self.assertRegex(description, r"\bF13\b")

    def test_commands_name_existing_scripts(self):
        """Every ${CLAUDE_PLUGIN_ROOT}/<path> in a command exists in troy-pstack."""
        for event, group in self.groups():
            command = group["hooks"][0]["command"]
            paths = PLUGIN_PATH.findall(command)
            with self.subTest(event=event):
                self.assertTrue(paths, command)
                for rel in paths:
                    self.assertTrue((REPO / rel).is_file(), f"{rel} does not exist")


class HooksJsonRunTests(HookTestCase):
    """The commands run in bash and reach troy_hook.py (design 2 and 10)."""

    @classmethod
    def setUpClass(cls):
        """Finds bash and reads the commands by event."""
        cls.bash = find_bash()
        if cls.bash is None:
            raise unittest.SkipTest("no bash found")
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        cls.commands = {}
        for event, groups in data["hooks"].items():
            cls.commands.setdefault(event, groups[0]["hooks"][0]["command"])
        cls.troy = Project()
        cls.plain = Project(troy_mode=False)
        cls.addClassCleanup(cls.troy.close)
        cls.addClassCleanup(cls.plain.close)
        cls.empty_path = SCRATCH / "empty-path"
        cls.empty_path.mkdir(exist_ok=True)

    def run_command(self, event, payload, project_dir, with_python=True):
        """Runs one hooks.json command in bash with the payload on stdin."""
        extra = {"CLAUDE_PLUGIN_ROOT": REPO.as_posix(),
                 "CLAUDE_PROJECT_DIR": Path(project_dir).as_posix()}
        env = hook_env(extra=extra)
        if with_python:
            env["TROY_MODE_PYTHON"] = sys.executable
        else:
            env.pop("TROY_MODE_PYTHON", None)
            env["PATH"] = str(self.empty_path)
        proc = subprocess.run([self.bash, "-c", self.commands[event]],
                              input=json.dumps(payload), cwd=str(NEUTRAL), env=env,
                              capture_output=True, encoding="utf-8", errors="replace",
                              timeout=120, check=False)
        return HookRun(proc.returncode, proc.stdout, proc.stderr, event, payload)

    def test_every_command_is_silent_outside_troy_mode(self):
        """Each event's command exits 0 and prints nothing for a project without .troy-mode/."""
        for event in self.commands:
            payload = hook_input(event, self.plain.root, DEV, tool_name="Write",
                                 tool_input={"file_path": str(self.plain.path("tests/x.py"))})
            with self.subTest(event=event):
                self.assert_silent(self.run_command(event, payload, self.plain.root))

    def test_pretooluse_command_refuses_in_troy_mode(self):
        """Pair: the PreToolUse command refuses the Developer's test file in a troy-mode project."""
        call = write_call(self.troy, DEV, self.troy.path("tests/test_new.py"))
        out = self.run_command("PreToolUse", call.payload, self.troy.root)
        self.assert_denied(out, "tests/test_new.py", "needs-answer")

    def test_missing_python_blocks_in_troy_mode(self):
        """With no interpreter, the command exits 2 in a troy-mode project (D39)."""
        call = write_call(self.troy, DEV, self.troy.path("src/pkg/app.py"))
        out = self.run_command("PreToolUse", call.payload, self.troy.root, with_python=False)
        self.assertEqual(2, out.code, out.describe())

    def expansion(self, project, name, args="build the export feature"):
        """Builds a UserPromptExpansion input for a typed command (F13 contract 1)."""
        return hook_input(GUARD_EVENT, project.root, MAIN, expansion_type="slash_command",
                          command_name=name, command_args=args, command_source="plugin",
                          prompt=f"/{name} {args}")

    def test_user_prompt_expansion_command_refuses_in_troy_mode(self):
        """F13: the hooks.json command blocks troy-pstack:poteto-mode with JSON and exit code 0.

        Planted bug caught: exit code 2 in place of JSON (F13 11.2).
        """
        payload = self.expansion(self.troy, "troy-pstack:poteto-mode")
        out = self.run_command(GUARD_EVENT, payload, self.troy.root)
        self.assert_blocked(out, "troy-mode: /troy-pstack:poteto-mode is off here. ",
                            "troy-mode：这里停用 /troy-pstack:poteto-mode。",
                            " /troy-pstack:troy-mode ")
        self.assertEqual({"decision", "reason"}, set(out.data()), out.describe())
        self.assertEqual("", out.stderr.strip(), out.describe())

    def test_user_prompt_expansion_command_is_silent_outside_troy_mode(self):
        """Pair: the same input in a project without .troy-mode/ exits 0 and prints nothing.

        Planted bug caught: the gate skipped (F13 11.2).
        """
        payload = self.expansion(self.plain, "troy-pstack:poteto-mode")
        self.assert_silent(self.run_command(GUARD_EVENT, payload, self.plain.root))

    def test_user_prompt_expansion_command_lets_troy_mode_through(self):
        """Pair: troy-pstack:troy-mode in the troy-mode project exits 0 and prints nothing."""
        payload = self.expansion(self.troy, "troy-pstack:troy-mode", "status")
        self.assert_silent(self.run_command(GUARD_EVENT, payload, self.troy.root))

    def test_user_prompt_expansion_without_python_blocks_in_troy_mode_only(self):
        """F13 7.2: with no interpreter, exit 2 in a troy-mode project, 0 and nothing elsewhere."""
        troy = self.run_command(GUARD_EVENT, self.expansion(self.troy, "troy-pstack:no-comments"),
                                self.troy.root, with_python=False)
        self.assertEqual(2, troy.code, troy.describe())
        plain = self.run_command(GUARD_EVENT,
                                 self.expansion(self.plain, "troy-pstack:no-comments"),
                                 self.plain.root, with_python=False)
        self.assertEqual(0, plain.code, plain.describe())
        self.assertEqual("", plain.stdout.strip(), plain.describe())

    def test_missing_python_passes_outside_troy_mode(self):
        """Pair: with no interpreter, the command exits 0 and prints nothing elsewhere."""
        call = write_call(self.plain, DEV, self.plain.path("src/pkg/app.py"))
        out = self.run_command("PreToolUse", call.payload, self.plain.root, with_python=False)
        self.assertEqual(0, out.code, out.describe())
        self.assertEqual("", out.stdout.strip(), out.describe())


if __name__ == "__main__":
    unittest.main()
