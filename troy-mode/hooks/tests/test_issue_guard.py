"""F15's gh guard additions (F15 design 10.2, 13.1 "Hooks"; F15 interface note section 6).

On top of tstack issue #65's posting check (F05 design 8.2 as #65 widens
it, tested in test_posting_guard.py), the main session's ``gh issue close``
and ``gh issue reopen`` have their ``--comment``/``-c`` text checked for
attribution (R19), and ``gh label create`` and ``gh label edit`` their
``--description``/``-d`` text. ``gh issue delete`` and ``gh label delete``
are refused for every caller in a troy-mode project.

Conventions follow test_posting_guard.py: each option in its ``--x v``,
``--x=v``, ``-x v``, and ``-xv`` forms; each refusal runs alone and checks
its one new log line; silent calls run in parallel in a second project whose
log no test reads.

Planted bug of F15 design 13.2 caught here: "``gh issue close --comment`` let
through unchecked": ``PostingTests.test_bad_text_is_refused_in_every_form``.
"""

import shlex
import unittest

from hook_helpers import (
    ATTRIBUTION_LINE, CR, DEV, MAIN, TRAILER, HookTestCase, Project, bash_call, make_config,
    run_many, start_call,
)

STRICT_TEXT = "Works with Claude."
CLEAN_TEXT = "F02 is next again."
LABEL_IDEA = "An idea or change for troy-mode to take in / 交给 troy-mode 的想法或改动"
TOKEN = "TROYCOMMENT-7d2e91"
# F15's table: the command name, a call with its other arguments, and its text option.
POSTING = (
    ("gh issue close", "gh issue close 3", ("--comment", "-c")),
    ("gh issue reopen", "gh issue reopen 3", ("--comment", "-c")),
    ("gh label create", "gh label create idea --color FBCA04", ("--description", "-d")),
    ("gh label edit", "gh label edit idea", ("--description", "-d")),
)
DELETES = (("gh issue delete 3", "gh issue delete"),
           ("gh issue delete 3 --yes", "gh issue delete"),
           ("gh label delete idea", "gh label delete"),
           ("gh label delete idea --yes", "gh label delete"))


def posting_cases(text: str, long_only: bool = False) -> list:
    """``(command, name)`` for each command of F15's table, in each option form."""
    value = shlex.quote(text)
    cases = []
    for name, base, (long, short) in POSTING:
        forms = (f"{long} {value}", f"{long}={value}", f"{short} {value}", f"{short}{value}")
        for form in forms[:1] if long_only else forms:
            cases.append((f"{base} {form}", name))
    return cases


class IssueGuardCase(HookTestCase):
    """Strict and trailers projects for refusals, and a copy of each for silent calls."""

    @classmethod
    def setUpClass(cls):
        """Builds the projects and starts two roles in the strict one."""
        cls.project = Project()
        cls.quiet = Project()
        cls.trailers = Project(config=make_config(mode="trailers"))
        cls.trailers_quiet = Project(config=make_config(mode="trailers"))
        for project in (cls.project, cls.quiet, cls.trailers, cls.trailers_quiet):
            cls.addClassCleanup(project.close)
        run_many([start_call(cls.project, caller) for caller in (DEV, CR)])
        run_many([start_call(cls.quiet, caller) for caller in (DEV, CR)])

    def check_silent(self, commands, caller=MAIN, project=None):
        """Every command passes with no output, run in parallel."""
        project = project or self.quiet
        outs = run_many([bash_call(project, caller, command) for command in commands])
        for command, out in zip(commands, outs):
            with self.subTest(command=command, caller=caller.label):
                self.assert_silent(out, msg=command)

    def assert_refused_by(self, command, name, rule="attribution", caller=MAIN, project=None,
                          fragments=("R19",)):
        """One refusal naming the command, and its one log line with the rule and name."""
        project = project or self.project
        before = len(project.log_lines())
        out = bash_call(project, caller, command).run()
        self.assert_denied(out, *fragments, *((name,) if name else ()), msg=command)
        lines = project.log_lines()[before:]
        self.assertEqual(1, len(lines), f"{command!r}: expected one new log line: {lines}")
        expected = {"rule": rule, "decision": "deny", "agent_id": caller.agent_id,
                    "event": "PreToolUse", "tool": "Bash"}
        if name:
            expected["subcommand"] = name
        self.assertEqual(expected, {k: lines[0].get(k) for k in expected}, command)


class PostingTests(IssueGuardCase):
    """The text of ``gh issue close``/``reopen`` and ``gh label create``/``edit`` (10.2)."""

    def test_bad_text_is_refused_in_every_form(self):
        """Planted bug "``gh issue close --comment`` let through unchecked": a strict-mode
        word in each command's text option, in each form, is refused with R19."""
        for command, name in posting_cases(STRICT_TEXT):
            with self.subTest(command=command):
                self.assert_refused_by(command, name)

    def test_clean_text_passes_in_every_form(self):
        """Pair: the same commands with clean text are silent."""
        self.check_silent([command for command, _ in posting_cases(CLEAN_TEXT)])

    def test_attribution_lines_are_refused_in_trailers_mode(self):
        """In trailers mode the "Generated with" line and a trailer are still refused."""
        cases = posting_cases(f"Done.\n\n{ATTRIBUTION_LINE}", long_only=True)
        cases += [("gh issue close 3 -c " + shlex.quote(f"Done.\n\n{TRAILER}"),
                   "gh issue close"),
                  ("gh label edit idea -d " + shlex.quote(f"Ideas. {TRAILER}"),
                   "gh label edit")]
        for command, name in cases:
            with self.subTest(command=command):
                self.assert_refused_by(command, name, project=self.trailers)

    def test_bare_word_passes_in_trailers_mode(self):
        """Pair: in trailers mode the bare word Claude is silent."""
        self.check_silent([command for command, _ in posting_cases(STRICT_TEXT, True)],
                          project=self.trailers_quiet)

    def test_commands_without_text_and_f15s_own_pass(self):
        """A reason, a duplicate, a plain reopen, a label color (``-c``), and F15's labels."""
        self.check_silent([
            "gh issue close 3 --reason completed",
            "gh issue close 7 --reason 'not planned'",
            "gh issue close 12 --duplicate-of 7",
            "gh issue reopen 3",
            f"gh label create idea --color FBCA04 --description {shlex.quote(LABEL_IDEA)}",
            "gh label create progress -c 1D76DB -d 'A feature progress, kept by troy-mode'",
            "gh label edit idea --color FBCA04"])

    def test_log_holds_no_comment_text(self):
        """A refused comment's text is not written to the hook log."""
        self.assert_refused_by("gh issue close 3 -c " + shlex.quote(f"{TOKEN} {STRICT_TEXT}"),
                               "gh issue close")
        self.assertNotIn(TOKEN, self.project.log_text())


class DeleteTests(IssueGuardCase):
    """``gh issue delete`` and ``gh label delete`` for every caller (design 10.2; note 6)."""

    def test_main_session_may_not_delete(self):
        """The main session: each delete refused with rule ``gh-delete``."""
        for command, name in DELETES:
            with self.subTest(command=command):
                self.assert_refused_by(command, name, rule="gh-delete", fragments=())

    def test_delete_inside_a_compound_command(self):
        """A delete after ``&&`` is still found."""
        self.assert_refused_by("gh issue list && gh issue delete 3 --yes", "gh issue delete",
                               rule="gh-delete", fragments=())

    def test_roles_may_not_delete(self):
        """The Developer and the Code Reviewer: each delete refused with rule ``gh``."""
        for caller in (DEV, CR):
            for command, name in DELETES:
                with self.subTest(caller=caller.label, command=command):
                    self.assert_refused_by(command, name, rule="gh", caller=caller,
                                           fragments=())

    def test_reading_issues_and_labels_passes(self):
        """Pair: reads pass for the main session, and issue reads for a role."""
        self.check_silent(["gh issue view 3", "gh issue list --label idea", "gh label list",
                           "gh issue list --state all --json number,title"])
        self.check_silent(["gh issue view 3", "gh issue list --state all"], caller=DEV)

    def test_delete_inside_a_line_that_cannot_be_split(self):
        """A main-session call that cannot be split and holds a delete: rule ``unparsed``."""
        for command in ('gh issue delete 3 --yes "unfinished', "echo 'x; gh label delete idea"):
            with self.subTest(command=command):
                self.assert_refused_by(command, None, rule="unparsed", fragments=())


if __name__ == "__main__":
    unittest.main()
