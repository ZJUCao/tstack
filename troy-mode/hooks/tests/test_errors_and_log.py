"""Errors and log group (F05 design section 10, D39, D200, and 13.1).

An error inside the hook refuses a subagent's call and only warns for the
main session, except while checking a main-session gh command that posts
text, which is refused with rule error (D200). Every refusal and block
appends one JSON line to
``<git dir>/troy-mode/hooks.log`` with the keys of contract section 4 and
never the command text.
"""

import unittest

from hook_helpers import (
    ATTRIBUTION_LINE, DEV, ERROR_PREFIX, INVALID_CONFIG, LOG_DECISIONS, LOG_KEYS, LOG_RULES,
    LOG_TIME, MAIN, SECRET, SESSION, HookTestCase, Project, bash_call, post_call, role,
    skill_call, start_call, stop_call, unique, write_call,
)

# Main-session gh commands that post text the strict mode refuses (design 8.2).
POSTING_WITH_CLAUDE = ("gh pr create --title 'Add x' --body 'Works with Claude.'",
                       "gh pr comment 5 --body 'Works with Claude.'")


class ErrorTests(HookTestCase):
    """D39: an error refuses a subagent's call and warns the main session; D200: posts are refused."""

    @classmethod
    def setUpClass(cls):
        """Builds a project whose committed config is invalid, and a valid one."""
        cls.broken = Project(config=INVALID_CONFIG)
        cls.valid = Project()
        cls.addClassCleanup(cls.broken.close)
        cls.addClassCleanup(cls.valid.close)

    def test_error_refuses_a_role_call(self):
        """With an invalid config, the Developer's write to source is refused with the error.

        Planted bug caught: a role's call allowed on an exception (13.2).
        """
        out = write_call(self.broken, DEV, self.broken.path("src/pkg/app.py")).run()
        self.assert_error_refusal(out)
        self.assert_last_log(self.broken, rule="error", decision="deny",
                             agent_id=DEV.agent_id, event="PreToolUse", tool="Write")

    def test_same_role_call_passes_with_a_valid_config(self):
        """Pair: the same write is silent in a project with a valid config."""
        self.assert_silent(write_call(self.valid, DEV, self.valid.path("src/pkg/app.py")).run())

    def test_error_refuses_a_main_session_posting_command(self):
        """With an invalid config, the main session's gh pr create and gh pr comment are refused.

        Design 10's exception (D200): rule error in the log, a deny decision.
        The texts hold the word Claude, so the hook needs the config's
        attribution mode to decide (design 8.2).
        """
        for command in POSTING_WITH_CLAUDE:
            with self.subTest(command=command):
                before = len(self.broken.log_lines())
                out = bash_call(self.broken, MAIN, command).run()
                self.assert_error_refusal(out, msg=command)
                lines = self.broken.log_lines()[before:]
                self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
                self.assertEqual(("error", "deny", None, "PreToolUse", "Bash"),
                                 (lines[0]["rule"], lines[0]["decision"], lines[0]["agent_id"],
                                  lines[0]["event"], lines[0]["tool"]))

    def test_same_main_session_call_is_decided_with_a_valid_config(self):
        """Pair: with a valid strict config the same calls are refused for R19, not an error."""
        for command in POSTING_WITH_CLAUDE:
            with self.subTest(command=command):
                out = bash_call(self.valid, MAIN, command).run()
                self.assert_denied(out, "R19", msg=command)
                self.assertFalse(out.reason.startswith(ERROR_PREFIX), out.describe())

    def test_error_does_not_refuse_other_main_session_calls(self):
        """Pair: with the same invalid config, other main-session calls still only warn at most.

        A commit message and a gh read are not posts, so the D200 exception
        does not apply: the call is silent, or warns with exit 1 and a notice
        on stderr (D39), and is never refused or logged.
        """
        before = len(self.broken.log_lines())
        for command in ("git commit -m 'Works with Claude.'", "gh pr view 5 --json body",
                        "gh api repos/o/r/issues/1/comments"):
            with self.subTest(command=command):
                out = bash_call(self.broken, MAIN, command).run()
                if out.code == 0:
                    self.assert_silent(out, msg=command)
                else:
                    self.assert_main_error(out, msg=command)
        self.assertEqual(before, len(self.broken.log_lines()), self.broken.log_text())


class LogTests(HookTestCase):
    """Design 10: one log line per refusal or block, with the contract's keys."""

    def setUp(self):
        """Builds a fresh project so each test sees only its own log lines."""
        self.project = Project()
        self.addCleanup(self.project.close)
        self.dev = role("developer", unique("-"))
        start_call(self.project, self.dev).run()

    def one_new_line(self, before):
        """Asserts that exactly one line was added and returns it."""
        lines = self.project.log_lines()
        self.assertEqual(before + 1, len(lines), f"expected one new log line: {lines}")
        line = lines[-1]
        self.assertEqual(LOG_KEYS, set(line), f"log keys: {line}")
        self.assertRegex(line["time"], LOG_TIME)
        self.assertIn(line["rule"], LOG_RULES)
        self.assertIn(line["decision"], LOG_DECISIONS)
        self.assertIsInstance(line["paths"], list)
        return line

    def test_git_refusal_writes_one_line_without_the_command(self):
        """A role's git commit refusal logs rule git and git commit, and not the message."""
        before = len(self.project.log_lines())
        command = f"git commit -m 'Add counting {SECRET}'"
        out = bash_call(self.project, self.dev, command).run()
        self.assert_denied(out, "git commit")
        line = self.one_new_line(before)
        self.assertEqual({"session": SESSION, "agent_id": self.dev.agent_id,
                          "agent_type": self.dev.agent_type, "event": "PreToolUse",
                          "tool": "Bash", "rule": "git", "paths": [],
                          "subcommand": "git commit", "decision": "deny"},
                         {k: v for k, v in line.items() if k != "time"})
        text = self.project.log_text()
        self.assertNotIn(SECRET, text)
        self.assertNotIn("Add counting", text)

    def test_scope_refusal_logs_the_path(self):
        """A write-scope refusal logs rule scope and the repository path."""
        before = len(self.project.log_lines())
        out = write_call(self.project, self.dev, self.project.path("tests/test_app.py")).run()
        self.assert_denied(out, "tests/test_app.py")
        line = self.one_new_line(before)
        self.assertEqual(("scope", ["tests/test_app.py"], None, "Write", "deny"),
                         (line["rule"], line["paths"], line["subcommand"], line["tool"],
                          line["decision"]))

    def test_gh_refusal_logs_the_subcommand_only(self):
        """A gh pr comment refusal logs gh pr comment, and not the comment's body."""
        before = len(self.project.log_lines())
        out = bash_call(self.project, self.dev,
                        f"gh pr comment 7 --body 'Token {SECRET} looks wrong'").run()
        self.assert_denied(out, "gh pr comment")
        line = self.one_new_line(before)
        self.assertEqual(("gh", "gh pr comment"), (line["rule"], line["subcommand"]))
        self.assertNotIn(SECRET, self.project.log_text())

    def test_skill_refusal_logs_the_skill(self):
        """A refused skill logs rule skill and skill <name>, not its arguments."""
        before = len(self.project.log_lines())
        out = skill_call(self.project, self.dev, "code-review", f"--comment {SECRET}").run()
        self.assert_denied(out, "code-review")
        line = self.one_new_line(before)
        self.assertEqual(("skill", "skill code-review"), (line["rule"], line["subcommand"]))
        self.assertNotIn(SECRET, self.project.log_text())

    def test_main_session_refusal_logs_nulls_for_the_agent(self):
        """A main-session --no-verify refusal logs null agent_id and agent_type."""
        before = len(self.project.log_lines())
        out = bash_call(self.project, MAIN, f"git commit --no-verify -m '{SECRET}'").run()
        self.assert_denied(out)
        line = self.one_new_line(before)
        self.assertEqual((None, None, "no-verify"),
                         (line["agent_id"], line["agent_type"], line["rule"]))
        self.assertNotIn(SECRET, self.project.log_text())

    def test_attribution_refusal_logs_no_pr_text(self):
        """An R19 refusal logs rule attribution, and neither the title nor the body."""
        before = len(self.project.log_lines())
        command = (f"gh pr create --title 'Add {SECRET}' "
                   f"--body 'Body {SECRET}.\n\n{ATTRIBUTION_LINE}'")
        self.assert_denied(bash_call(self.project, MAIN, command).run(), "R19")
        line = self.one_new_line(before)
        self.assertEqual("attribution", line["rule"])
        text = self.project.log_text()
        self.assertNotIn(SECRET, text)
        self.assertNotIn("Generated with", text)

    def test_unparsed_refusal_logs_no_command(self):
        """A refused command that cannot be split logs rule unparsed and no command text."""
        before = len(self.project.log_lines())
        out = bash_call(self.project, self.dev, f'git commit -m "{SECRET}').run()
        self.assert_denied(out)
        line = self.one_new_line(before)
        self.assertEqual("unparsed", line["rule"])
        self.assertNotIn(SECRET, self.project.log_text())

    def test_change_block_logs_the_paths(self):
        """A PostToolUse block logs rule changes, the paths, and decision block."""
        before = len(self.project.log_lines())
        self.project.write("tests/test_new.py", "def test_x():\n    pass\n")
        out = post_call(self.project, self.dev, command=f"echo {SECRET} > tests/test_new.py").run()
        self.assert_blocked(out, "tests/test_new.py")
        line = self.one_new_line(before)
        self.assertEqual(("changes", ["tests/test_new.py"], "block", "PostToolUse"),
                         (line["rule"], line["paths"], line["decision"], line["event"]))
        self.assertNotIn(SECRET, self.project.log_text())

    def test_stop_block_logs_one_line(self):
        """A SubagentStop block logs one line with decision block."""
        self.project.write("tests/test_new.py", "def test_x():\n    pass\n")
        before = len(self.project.log_lines())
        self.assert_blocked(stop_call(self.project, self.dev).run(), "tests/test_new.py")
        line = self.one_new_line(before)
        self.assertEqual(("changes", "block", "SubagentStop"),
                         (line["rule"], line["decision"], line["event"]))

    def test_allowed_calls_write_no_line(self):
        """Pair: silent calls add no log line."""
        before = len(self.project.log_lines())
        for out in (bash_call(self.project, self.dev, "git status").run(),
                    write_call(self.project, self.dev, self.project.path("src/pkg/app.py")).run(),
                    bash_call(self.project, MAIN, "git commit -m 'Add x'").run(),
                    post_call(self.project, self.dev).run()):
            self.assert_silent(out)
        self.assertEqual(before, len(self.project.log_lines()))


if __name__ == "__main__":
    unittest.main()
