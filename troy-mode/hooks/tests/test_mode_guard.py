"""Mode guard group (F13 design sections 4 to 7 and 11.1).

In a troy-mode project, ``troy_hook.py UserPromptExpansion`` refuses the typed
commands ``poteto-mode`` and ``no-comments``, under any plugin prefix or none,
with ``{"decision": "block", "reason": <message>}`` on stdout and exit code 0.
It lets every other command through silently, and outside a troy-mode project
it is silent for every command. An error inside the handler only warns (exit
code 1), and a refusal writes no ``hooks.log`` line.

The tests are written from the F13 design (version 1.0) and its interface
contract before the handler exists. They are black-box through
``troy_hook.py`` (``hook_helpers.run_hook``), except where the contract allows
the implementation's names: ``troyhook.scopes.PLUGIN_PREFIX`` builds the
expected message, ``troyhook.modeguard.GUARDED`` is read once, and the error
path runs ``troyhook.events.main`` in a subprocess with a ``troyhook.modeguard``
function replaced by one that raises (contract 5). The hooks.json entry is
tested in test_hooks_json.py, which reuses this module's name lists.

Conventions, beyond those of hook_helpers.py.

1. The input has Claude Code's shape for the event (contract 1):
   ``expansion_type`` ``slash_command``, ``command_name``, ``command_args``,
   ``command_source`` ``plugin``, and ``prompt``, the command line as Claude
   Code resolved it. It is the main session's: no ``agent_id``.
2. Refused is exit code 0, stdout exactly ``{"decision": "block", "reason":
   <the message of contract 4>}`` with no other key, and nothing on stderr.
   Let through is hook_helpers' "silent".
3. "Without command_args" is tested both as an empty string, as the trial saw
   it, and as a missing key.
4. Inputs whose ``command_name`` is let through still carry a ``prompt`` or
   ``command_args`` that names a guarded command where that is natural, so a
   hook that reads the typed text in place of ``command_name`` fails.

Planted bugs (design 11.2) and the tests that catch them. Each test also
names its bug in its docstring.

- The gate skipped:
  OutsideTroyModeTests.test_guarded_commands_are_let_through_without_troy_mode
  and test_guarded_commands_are_let_through_outside_git;
  ErrorTests.test_raising_check_is_silent_outside_troy_mode;
  test_hooks_json.HooksJsonRunTests.test_user_prompt_expansion_command_is_silent_outside_troy_mode.
- An unanchored match:
  TroyModeProjectTests.test_names_that_contain_a_guarded_name_are_let_through.
- The prefix kept so a bare name passes:
  TroyModeProjectTests.test_bare_names_are_refused and
  test_other_plugin_prefixes_are_refused;
  MessageTests.test_message_names_the_command_as_given_with_a_slash.
- no-comments left out:
  TroyModeProjectTests.test_prefixed_commands_are_refused_in_the_project_root
  and test_bare_names_are_refused; ModuleTests.test_guarded_names; and,
  when it is left out of the matcher,
  test_hooks_json.HooksJsonTests.test_user_prompt_expansion_entry and
  test_user_prompt_expansion_matcher_matches_only_the_guarded_names.
- Exit code 2 in place of JSON:
  TroyModeProjectTests.test_prefixed_commands_are_refused_in_the_project_root
  (and every other refused case);
  test_hooks_json.HooksJsonRunTests.test_user_prompt_expansion_command_refuses_in_troy_mode.
- The error path blocking:
  ErrorTests.test_raising_message_only_warns and test_raising_check_only_warns;
  for an input that names a subagent,
  test_raising_check_only_warns_even_with_an_agent_id.
- A log line written:
  NoLogTests.test_refusal_leaves_the_log_unchanged and
  test_refusal_creates_no_log.
- A matcher without ^:
  test_hooks_json.HooksJsonTests.test_user_prompt_expansion_matcher_matches_only_the_guarded_names,
  test_user_prompt_expansion_entry, and test_matchers_and_if_rules.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -p "test_mode_guard.py" -v
"""

import importlib
import json
import subprocess
import sys
import unittest

from hook_helpers import (
    BASE_FILES, CHECKS, DEV, ERROR_PREFIX, GP, HOOK, HOOKS_DIR, MAIN, NEUTRAL, Call, HookRun,
    HookTestCase, Project, has_git_ancestor, hook_env, hook_input, plain_folder, remove_tree,
    run_many, unique, write_call,
)

EVENT = "UserPromptExpansion"


def troyhook_module(name):
    """Imports a troyhook module in this process (contract 5).

    sys.path gets troy-mode/hooks and troy-mode/checks, as troy_hook.py sets
    it.

    Args:
        name: The module's full name, for example ``troyhook.scopes``.

    Returns:
        The module.
    """
    for folder in (CHECKS, HOOKS_DIR):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    return importlib.import_module(name)


PLUGIN_PREFIX = troyhook_module("troyhook.scopes").PLUGIN_PREFIX
# T of contract 4: the command the message points to.
TROY_MODE_COMMAND = "/" + PLUGIN_PREFIX + "troy-mode"

# ---------------------------------------------------------------------------
# Names (design section 4, contract section 3).
# ---------------------------------------------------------------------------

PREFIXED = ("troy-pstack:poteto-mode", "troy-pstack:no-comments")
OTHER_PREFIXES = ("tstack:poteto-mode", "tstack:no-comments", "pstack:poteto-mode",
                  "pstack:no-comments")
BARE = ("poteto-mode", "no-comments")
REFUSED = PREFIXED + OTHER_PREFIXES + BARE

# Other commands, troy-mode's own and the tools design section 4 leaves off
# the list.
OTHER_COMMANDS = ("troy-pstack:troy-mode", "troy-pstack:bro", "troy-pstack:arena",
                  "code-review")
# Near misses: one letter off, another skill, or another case (contract 3:
# case-sensitive).
NEAR_MISSES = ("troy-pstack:no-comment", "troy-pstack:poteto-help", "troy-pstack:POTETO-MODE",
               "troy-pstack:No-Comments", "POTETO-MODE")
# Names that hold a guarded name with text before or after it, or after a
# second prefix (contract 3: only the part before the first ":" is dropped).
CONTAINS_GUARDED = ("troy-pstack:poteto-mode-extra", "troy-pstack:no-comments-extra",
                    "my-poteto-mode", "troy-pstack:my-no-comments", "a:b:poteto-mode",
                    "a:b:no-comments")
LET_THROUGH = OTHER_COMMANDS + NEAR_MISSES + CONTAINS_GUARDED

# command_args forms: with arguments, empty (as the trial saw it), and missing.
ARG_FORMS = ("build the export feature", "", None)
MISSING = object()

# ---------------------------------------------------------------------------
# The message (design section 6, contract section 4).
# ---------------------------------------------------------------------------

EN_LINE = ("troy-mode: {N} is off here. This project uses troy-mode (it has a .troy-mode "
           "folder), and {C}. Type {T} and your request instead. It also handles questions "
           "and experiments, which open no PR.")
ZH_LINE = ("troy-mode：这里停用 {N}。本项目使用 troy-mode（有 .troy-mode 文件夹），而 {C}。"
           "请改用 {T} 加上你的请求。提问和试验也用它，不开 PR。")
EN_CLAUSE = {
    "poteto-mode": ("poteto-mode's way of working breaks troy-mode's rules: only troy-mode's "
                    "roles write code, each PR holds one stage, and Troy approves the designs"),
    "no-comments": "/no-comments deletes doc comments that troy-mode's rule R05 requires",
}
ZH_CLAUSE = {
    "poteto-mode": ("poteto-mode 的工作方式会破坏 troy-mode 的规则：只有 troy-mode 的角色写代码，"
                    "每个 PR 只放一个阶段，设计要 Troy 批准"),
    "no-comments": "/no-comments 会删除 troy-mode 规则 R05 要求的文档注释",
}


def guarded_rest(command_name):
    """Returns the name after the first ":", or the whole name (contract 3)."""
    return command_name.split(":", 1)[1] if ":" in command_name else command_name


def expected_message(command_name):
    """Builds the reason of contract 4 for a refused name.

    Args:
        command_name: The input's ``command_name``, prefix and all.

    Returns:
        The English line and the Chinese line joined by one line break.
    """
    rest = guarded_rest(command_name)
    lines = []
    for template, clauses in ((EN_LINE, EN_CLAUSE), (ZH_LINE, ZH_CLAUSE)):
        line = template.replace("{C}", clauses[rest])
        lines.append(line.replace("{N}", "/" + command_name).replace("{T}", TROY_MODE_COMMAND))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hook runs.
# ---------------------------------------------------------------------------


def expansion_input(cwd, name=MISSING, args="", prompt=None):
    """Builds a UserPromptExpansion input in Claude Code's shape (contract 1).

    Args:
        cwd: The input's ``cwd``.
        name: ``command_name``: any JSON value, or MISSING to leave the key out.
        args: ``command_args``, or None to leave the key out.
        prompt: ``prompt``; by default ``/<name>`` and the arguments.

    Returns:
        The input dictionary.
    """
    payload = hook_input(EVENT, cwd, MAIN, expansion_type="slash_command",
                         command_source="plugin")
    if name is not MISSING:
        payload["command_name"] = name
    if args is not None:
        payload["command_args"] = args
    if prompt is None:
        prompt = f"/{name}" + (f" {args}" if args else "")
    payload["prompt"] = prompt
    return payload


def expansion(cwd, name=MISSING, args="", prompt=None):
    """Returns a Call for one UserPromptExpansion input (see expansion_input)."""
    return Call(EVENT, expansion_input(cwd, name, args, prompt))


# Runs troyhook.events.main in a subprocess after replacing one
# troyhook.modeguard function with one that raises (contract 5). argv: the
# checks folder, the hooks folder, and the function's name, or "" for none.
_HARNESS = """
import sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
import troyhook.modeguard as modeguard
from troyhook import events
if sys.argv[3]:
    def planted(*args, **kwargs):
        raise RuntimeError("planted error in modeguard." + sys.argv[3])
    setattr(modeguard, sys.argv[3], planted)
sys.exit(events.main(["UserPromptExpansion"]))
"""


def run_patched(payload, target):
    """Runs the hook in-process in a child Python whose modeguard.<target> raises.

    Args:
        payload: The hook input.
        target: ``message``, ``check``, or "" to replace nothing.

    Returns:
        The run's result.
    """
    proc = subprocess.run(
        [sys.executable, "-I", "-c", _HARNESS, str(CHECKS), str(HOOKS_DIR), target],
        input=json.dumps(payload), cwd=str(NEUTRAL), env=hook_env(), capture_output=True,
        encoding="utf-8", errors="replace", timeout=120, check=False)
    return HookRun(proc.returncode, proc.stdout, proc.stderr, EVENT, payload)


def run_raw(text):
    """Runs ``troy_hook.py UserPromptExpansion`` with raw text on stdin."""
    proc = subprocess.run([sys.executable, str(HOOK), EVENT], input=text, cwd=str(NEUTRAL),
                          env=hook_env(), capture_output=True, encoding="utf-8",
                          errors="replace", timeout=120, check=False)
    return HookRun(proc.returncode, proc.stdout, proc.stderr, EVENT, {"stdin": text})


class GuardTestCase(HookTestCase):
    """Assertions on UserPromptExpansion runs."""

    @staticmethod
    def label(out):
        """Names the input of a run for failure messages."""
        payload = out.payload
        return (f" command_name={payload.get('command_name', '<missing>')!r}"
                f" command_args={payload.get('command_args', '<missing>')!r}"
                f" prompt={payload.get('prompt')!r} cwd={payload.get('cwd')}")

    def assert_refused(self, out):
        """Asserts contract 2's refusal with contract 4's exact message.

        Exit code 0, stdout exactly one JSON object with only ``decision``
        ``block`` and ``reason``, and nothing on stderr.
        """
        where = self.label(out) + out.describe()
        self.assertEqual(0, out.code, "expected exit code 0 with the JSON block" + where)
        try:
            data = json.loads(out.stdout)
        except ValueError:
            data = None
        self.assertIsInstance(data, dict, "stdout is not exactly one JSON object" + where)
        expected = {"decision": "block", "reason": expected_message(out.payload["command_name"])}
        self.assertEqual(expected, data, where)
        self.assertEqual("", out.stderr.strip(), "expected nothing on stderr" + where)

    def assert_let_through(self, out):
        """Asserts the silent let-through of contract 2."""
        self.assert_silent(out, self.label(out))

    def check_all(self, calls, assertion):
        """Runs calls in parallel and applies the assertion to each, in subtests."""
        for out in run_many(calls):
            payload = out.payload
            with self.subTest(command_name=payload.get("command_name", "<missing>"),
                              command_args=payload.get("command_args", "<missing>"),
                              cwd=payload.get("cwd")):
                assertion(out)


class TroyModeProjectTests(GuardTestCase):
    """Refused and let through in a troy-mode project: root, subfolder, worktree."""

    @classmethod
    def setUpClass(cls):
        """Builds one troy-mode project and a linked worktree of it."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        cls.sub = cls.project.path("src/pkg")
        cls.worktree = cls.project.root.parent / unique("wt")
        cls.project.git("worktree", "add", "-q", "-b", unique("wt-branch-"), str(cls.worktree))
        cls.addClassCleanup(remove_tree, cls.worktree)

    def test_prefixed_commands_are_refused_in_the_project_root(self):
        """troy-pstack:poteto-mode and troy-pstack:no-comments, with and without command_args.

        Planted bugs caught: no-comments left out (its rows); exit code 2 in
        place of JSON (every row needs exit code 0 and the JSON object).
        """
        calls = [expansion(self.project.root, name, args) for name in PREFIXED
                 for args in ARG_FORMS]
        self.check_all(calls, self.assert_refused)

    def test_prefixed_commands_are_refused_in_a_subfolder(self):
        """From src/pkg, the gate walks up to the project and the commands are refused."""
        calls = [expansion(self.sub, name, args) for name in PREFIXED for args in ARG_FORMS]
        self.check_all(calls, self.assert_refused)

    def test_prefixed_commands_are_refused_in_a_worktree(self):
        """In a linked worktree, where .git is a file, the commands are refused."""
        self.assertTrue((self.worktree / ".git").is_file(), "the worktree has no .git file")
        self.assertTrue((self.worktree / ".troy-mode").is_dir())
        calls = [expansion(self.worktree, name, args) for name in PREFIXED for args in ARG_FORMS]
        self.check_all(calls, self.assert_refused)

    def test_other_plugin_prefixes_are_refused(self):
        """tstack: (after F19) and pstack: (upstream) are refused too (design section 4).

        Planted bug caught: the prefix kept, so only troy-pstack: is refused.
        """
        calls = [expansion(self.project.root, name, args) for name in OTHER_PREFIXES
                 for args in ARG_FORMS[:2]]
        self.check_all(calls, self.assert_refused)

    def test_bare_names_are_refused(self):
        """Bare poteto-mode and no-comments, as a personal skill would be named, are refused.

        Planted bugs caught: the prefix kept so a bare name passes; no-comments
        left out (the bare no-comments rows).
        """
        calls = [expansion(root, name, args) for root in (self.project.root, self.worktree)
                 for name in BARE for args in ARG_FORMS]
        self.check_all(calls, self.assert_refused)

    def test_other_commands_are_let_through(self):
        """Pair: other commands and near misses are silent in the root, a subfolder, a worktree.

        A hook that refuses everything in a troy-mode project fails here.
        """
        calls = [expansion(root, name, args) for root in (self.project.root, self.sub,
                                                          self.worktree)
                 for name in OTHER_COMMANDS + NEAR_MISSES for args in ARG_FORMS[:2]]
        self.check_all(calls, self.assert_let_through)

    def test_names_that_contain_a_guarded_name_are_let_through(self):
        """Pair: poteto-mode-extra, my-poteto-mode, a:b:poteto-mode, and the like are silent.

        The handler compares the rest after the first ":" exactly (design
        7.2, contract 3).

        Planted bug caught: an unanchored match.
        """
        calls = [expansion(root, name, args) for root in (self.project.root, self.sub,
                                                          self.worktree)
                 for name in CONTAINS_GUARDED for args in ARG_FORMS[:2]]
        self.check_all(calls, self.assert_let_through)

    def test_arguments_that_name_a_guarded_command_are_let_through(self):
        """Pair: troy-mode asked about /poteto-mode is silent; only command_name counts (3.3)."""
        args = "compare /poteto-mode and /no-comments with troy-mode"
        calls = [expansion(self.project.root, "troy-pstack:troy-mode", args),
                 expansion(self.project.root, "troy-pstack:bro", "/troy-pstack:poteto-mode")]
        self.check_all(calls, self.assert_let_through)

    def test_missing_empty_or_non_string_command_name_is_let_through(self):
        """Pair: no command_name, an empty one, null, a number, or a list is silent (contract 3).

        Each input's prompt names /troy-pstack:poteto-mode, so a hook that
        falls back to the typed text fails.
        """
        prompt = "/troy-pstack:poteto-mode build the export feature"
        names = (MISSING, "", None, 42, ["troy-pstack:poteto-mode"])
        calls = [expansion(self.project.root, name, "build the export feature", prompt)
                 for name in names]
        self.check_all(calls, self.assert_let_through)


class OutsideTroyModeTests(GuardTestCase):
    """The gate (design 7.2 step 1): outside a troy-mode project nothing is refused."""

    def test_guarded_commands_are_let_through_without_troy_mode(self):
        """In a git repository without .troy-mode/, every refused name is silent.

        Pair of the TroyModeProjectTests refusals. Planted bug caught: the
        gate skipped.
        """
        project = Project(troy_mode=False)
        self.addCleanup(project.close)
        self.assertTrue(project.git_dir.is_dir())
        self.assertFalse(project.path(".troy-mode").exists())
        calls = [expansion(root, name, args) for root in (project.root, project.path("src/pkg"))
                 for name in REFUSED for args in ARG_FORMS[:2]]
        self.check_all(calls, self.assert_let_through)

    def test_guarded_commands_are_let_through_outside_git(self):
        """In a folder with .troy-mode/ but no .git above it, every refused name is silent.

        Planted bug caught: the gate skipped.
        """
        files = dict(BASE_FILES)
        files[".troy-mode/config.toml"] = "[attribution]\nmode = \"strict\"\n"
        root = plain_folder(files)
        if has_git_ancestor(root):
            self.skipTest(f"a parent of {root} holds .git")
        self.assertTrue((root / ".troy-mode").is_dir())
        calls = [expansion(root, name, "build the export feature") for name in REFUSED]
        self.check_all(calls, self.assert_let_through)


class MessageTests(GuardTestCase):
    """The reason of design section 6 and contract section 4, for each refused form."""

    @classmethod
    def setUpClass(cls):
        """Refuses each form once in a troy-mode project and keeps the runs."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        calls = [expansion(cls.project.root, name, "build the export feature")
                 for name in REFUSED]
        cls.outs = dict(zip(REFUSED, run_many(calls)))

    def reason(self, name):
        """Returns the block reason of one form's run, failing if there is none."""
        out = self.outs[name]
        data = out.data()
        self.assertIsInstance(data, dict, "expected one JSON object" + self.label(out) +
                              out.describe())
        self.assertEqual("block", data.get("decision"), self.label(out) + out.describe())
        reason = data.get("reason")
        self.assertIsInstance(reason, str, "no reason" + self.label(out) + out.describe())
        return reason

    def test_message_is_the_contract_text(self):
        """Each form's reason is exactly the text of contract 4, built from PLUGIN_PREFIX."""
        for name in REFUSED:
            with self.subTest(command_name=name):
                self.assertEqual(expected_message(name), self.reason(name))

    def test_message_names_the_command_as_given_with_a_slash(self):
        """Both lines name "/" + command_name, prefix and all, and no other spelling of it.

        Planted bug caught: the prefix kept or replaced, so a bare or a
        tstack: name is shown as /troy-pstack:<name>.
        """
        for name in REFUSED:
            with self.subTest(command_name=name):
                english, chinese = (self.reason(name).split("\n") + ["", ""])[:2]
                self.assertTrue(english.startswith(f"troy-mode: /{name} is off here. "), english)
                self.assertTrue(chinese.startswith(f"troy-mode：这里停用 /{name}。"), chinese)
                rest = guarded_rest(name)
                if name != PLUGIN_PREFIX + rest:
                    self.assertNotIn("/" + PLUGIN_PREFIX + rest, self.reason(name))

    def test_message_holds_its_commands_clause_and_not_the_others(self):
        """poteto-mode gets the way-of-working clause, no-comments the R05 clause, in both lines."""
        for name in REFUSED:
            rest = guarded_rest(name)
            other = "no-comments" if rest == "poteto-mode" else "poteto-mode"
            with self.subTest(command_name=name):
                english, chinese = (self.reason(name).split("\n") + ["", ""])[:2]
                self.assertIn(f", and {EN_CLAUSE[rest]}. ", english)
                self.assertIn(f"而 {ZH_CLAUSE[rest]}。", chinese)
                self.assertNotIn(EN_CLAUSE[other], english)
                self.assertNotIn(ZH_CLAUSE[other], chinese)
                for word in ("R05", "way of working", "工作方式"):
                    if word not in EN_CLAUSE[rest] + ZH_CLAUSE[rest]:
                        self.assertNotIn(word, self.reason(name))

    def test_message_points_to_troy_mode(self):
        """Both lines tell Troy to type /troy-pstack:troy-mode (from PLUGIN_PREFIX) instead."""
        for name in REFUSED:
            with self.subTest(command_name=name):
                english, chinese = (self.reason(name).split("\n") + ["", ""])[:2]
                self.assertIn(f" Type {TROY_MODE_COMMAND} and your request instead. ", english)
                self.assertIn(f"请改用 {TROY_MODE_COMMAND} 加上你的请求。", chinese)

    def test_message_has_an_english_line_and_a_chinese_line(self):
        """Exactly two lines joined by one line break: English first, then Chinese."""
        for name in REFUSED:
            with self.subTest(command_name=name):
                reason = self.reason(name)
                self.assertEqual(reason.strip(), reason, "leading or trailing whitespace")
                self.assertNotIn("\r", reason)
                lines = reason.split("\n")
                self.assertEqual(2, len(lines), reason)
                english, chinese = lines
                self.assertTrue(english.isascii(), f"the English line is not plain ASCII: "
                                                   f"{english}")
                self.assertTrue(english.startswith("troy-mode: "), english)
                self.assertTrue(english.endswith("which open no PR."), english)
                self.assertFalse(chinese.isascii(), chinese)
                self.assertTrue(chinese.startswith("troy-mode："), chinese)
                self.assertTrue(chinese.endswith("不开 PR。"), chinese)
                for mark in ("：", "。", "（", "）", "，"):
                    self.assertIn(mark, chinese, f"no full-width {mark!r}")


class ErrorTests(GuardTestCase):
    """Design 7.2 Errors and F05 D39: an error only warns; the command runs."""

    @classmethod
    def setUpClass(cls):
        """Builds a troy-mode project and a plain one."""
        cls.troy = Project()
        cls.plain = Project(troy_mode=False)
        cls.addClassCleanup(cls.troy.close)
        cls.addClassCleanup(cls.plain.close)

    def assert_warning(self, out):
        """Asserts contract 2's error: exit 1, nothing on stdout, a troy-mode notice on stderr."""
        self.assert_main_error(out, self.label(out))
        self.assertTrue(out.stderr.startswith(ERROR_PREFIX),
                        f"stderr does not start with {ERROR_PREFIX!r}" + self.label(out) +
                        out.describe())

    def test_harness_without_a_planted_error_refuses(self):
        """Pair: the same child program with nothing replaced gives the normal refusal."""
        for name in PREFIXED:
            with self.subTest(command_name=name):
                self.assert_refused(run_patched(expansion_input(self.troy.root, name), ""))

    def test_raising_message_only_warns(self):
        """modeguard.message raising: exit 1, a notice on stderr, nothing on stdout.

        Planted bug caught: the error path blocking.
        """
        for name in PREFIXED:
            with self.subTest(command_name=name):
                out = run_patched(expansion_input(self.troy.root, name, "build it"), "message")
                self.assert_warning(out)

    def test_raising_check_only_warns(self):
        """modeguard.check raising: exit 1, a notice on stderr, nothing on stdout.

        Planted bug caught: the error path blocking.
        """
        for name in PREFIXED:
            with self.subTest(command_name=name):
                out = run_patched(expansion_input(self.troy.root, name, ""), "check")
                self.assert_warning(out)

    def test_raising_check_only_warns_even_with_an_agent_id(self):
        """An input that names a subagent still only warns, and writes no log line (7.2).

        Claude Code sends this event for Troy's own typed commands, so an
        error must never block one, whoever the input names.

        Planted bug caught: the error path blocking for a subagent's input,
        through F05's refusal rule for subagents (D39).
        """
        for caller in (DEV, GP):
            payload = expansion_input(self.troy.root, "troy-pstack:poteto-mode", "build it")
            payload.update(agent_id=caller.agent_id, agent_type=caller.agent_type)
            with self.subTest(agent_type=caller.agent_type):
                self.assert_warning(run_patched(payload, "check"))
                self.assertFalse(self.troy.log_path.exists(),
                                 "an error wrote hooks.log:\n" + self.troy.log_text())

    def test_raising_check_is_silent_outside_troy_mode(self):
        """Outside a troy-mode project the gate answers before the handler runs: silent.

        Planted bug caught: the gate skipped.
        """
        out = run_patched(expansion_input(self.plain.root, "troy-pstack:poteto-mode"), "check")
        self.assert_let_through(out)

    def test_input_that_is_not_a_json_object_exits_1(self):
        """Text that is not JSON, or JSON that is not an object, exits 1 with nothing on stdout."""
        for text in ("/troy-pstack:poteto-mode build", '["troy-pstack:poteto-mode"]',
                     '"troy-pstack:poteto-mode"'):
            with self.subTest(stdin=text):
                self.assert_main_error(run_raw(text))


class NoLogTests(GuardTestCase):
    """Design 7.2 No log line and contract 7: a refusal leaves hooks.log as it was."""

    def setUp(self):
        """Builds a fresh troy-mode project."""
        self.project = Project()
        self.addCleanup(self.project.close)

    def refusals(self):
        """Returns refused calls from the root and a subfolder."""
        return [expansion(root, name, args)
                for root in (self.project.root, self.project.path("src/pkg"))
                for name in PREFIXED + BARE for args in ARG_FORMS[:2]]

    def test_refusal_leaves_the_log_unchanged(self):
        """With one line already in hooks.log, refusals leave its bytes unchanged.

        Planted bug caught: a log line written.
        """
        out = write_call(self.project, DEV, self.project.path("tests/test_new.py")).run()
        self.assert_denied(out, "tests/test_new.py")
        self.assertEqual(1, len(self.project.log_lines()), self.project.log_text())
        before = self.project.log_path.read_bytes()
        self.check_all(self.refusals(), self.assert_refused)
        self.assertEqual(before, self.project.log_path.read_bytes(),
                         "a refusal changed hooks.log:\n" + self.project.log_text())

    def test_refusal_creates_no_log(self):
        """In a project with no hooks.log yet, refusals create none.

        Planted bug caught: a log line written.
        """
        self.assertFalse(self.project.log_path.exists())
        self.check_all(self.refusals(), self.assert_refused)
        self.assertFalse(self.project.log_path.exists(),
                         "a refusal wrote hooks.log:\n" + self.project.log_text())


class ModuleTests(unittest.TestCase):
    """The one constant of contract 5 that a black-box run cannot read."""

    def test_guarded_names(self):
        """troyhook.modeguard.GUARDED is ("poteto-mode", "no-comments") (design section 4).

        Planted bug caught: no-comments left out.
        """
        self.assertEqual(("poteto-mode", "no-comments"),
                         troyhook_module("troyhook.modeguard").GUARDED)


if __name__ == "__main__":
    unittest.main()
