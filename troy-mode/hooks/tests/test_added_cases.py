"""Tests added after the trial and the planted bugs (F05 design 7.1, 7.2, 8.2, 10).

The test writer wrote every other file here from design 1.0 before the code
existed. These came later:

- The trial of design 13.3: the Test Manager made its scratch copy with
  DST=$(mktemp -d <temp>/name-XXXXXX) and cd "$DST", so the hook follows a
  variable set earlier in the same command to a literal path or to the folder
  "mktemp -d" makes (design 1.1, section 7.1). Every other variable is
  unknown, and a git write in an unknown folder counts as one in the project.
- Planted bugs that survived the first run: the log keeping words it does not
  know, a case difference only in folders that do not exist yet, and a PR
  body given on stdin through a heredoc.
- Guard spellings the test writer flagged: lower-case core.hookspath and
  combined short flags such as commit -nm.
"""

import unittest

from hook_helpers import (
    ATTRIBUTION_LINE, DEV, HOOK_TEMP, IS_WINDOWS, MAIN, PAD, SECRET, TM, HookTestCase, Project,
    bash_call, q, run_many, scratch_repo, start_call, unique, write_call,
)


class VariableScratchTests(HookTestCase):
    """Variables that name a scratch repository, and variables that do not."""

    @classmethod
    def setUpClass(cls):
        """Builds a project, a scratch repository in temp, and the roles' start records."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        cls.scratch = scratch_repo(HOOK_TEMP)
        run_many([start_call(cls.project, c) for c in (DEV, TM)])

    def outs(self, commands, caller=TM):
        """Runs one Bash call per command for the caller."""
        return run_many([bash_call(self.project, caller, c) for c in commands])

    def test_mktemp_folder_and_literal_variables_are_scratch(self):
        """A mktemp -d folder in temp, or a variable holding a scratch path, may commit.

        Planted bug caught: variables not followed (the trial's TM2 refusal).
        """
        temp, scratch = HOOK_TEMP.as_posix(), q(self.scratch)
        commands = (
            'D=$(mktemp -d); cd "$D" && git init -q && git add -A && git commit -qm x',
            f'DST=$(mktemp -d "{temp}/tm2-XXXXXX"); cd "$DST"; git init -q; git commit -qm x',
            'D=$(mktemp -d -t copy.XXXXXX); git -C "$D" init && git -C "$D" commit -m x',
            f'export D=$(mktemp -d -p {q(HOOK_TEMP)}); cd "${{D}}" && git commit -m x',
            f'S={scratch}; cd "$S" && git commit -m x',
            f'S={scratch}; T="$S"; git -C "$T" commit -m x',
        )
        for caller in (TM, DEV):
            for out, command in zip(self.outs(commands, caller), commands):
                with self.subTest(caller=caller.label, command=command):
                    self.assert_silent(out)

    def test_push_from_a_mktemp_folder_is_refused(self):
        """git push stays refused in a mktemp folder: a clone can push into the project."""
        out, = self.outs(('D=$(mktemp -d); cd "$D" && git init -q && git push',))
        self.assert_denied(out, "git push")

    def test_unknown_or_project_variables_count_as_the_project(self):
        """A variable the text cannot resolve, or one in the project, is not scratch.

        Planted bugs caught: mktemp's folder taken as temp whatever its -p or
        template says, and unknown variables taken as scratch.
        """
        project = q(self.project.root)
        commands = (
            'cd "$SOMEWHERE" && git commit -m x',
            f'cd "${{PREFIX}}"{q(self.scratch)} && git commit -m x',
            'D=$(pwd); cd "$D" && git commit -m x',
            f'D={project}; cd "$D" && git commit -m x',
            'D=$(mktemp -d tmp.XXXXXX); cd "$D" && git commit -m x',
            f'D=$(mktemp -d -p {project}); git -C "$D" commit -m x',
            'D=$(mktemp); cd "$D" && git commit -m x',
            'D=$(mktemp -d); D=$(pwd); cd "$D" && git commit -m x',
            'D=$(mktemp -d); GIT_DIR="$D/.git" git commit -m x',
        )
        for out, command in zip(self.outs(commands), commands):
            with self.subTest(command=command):
                self.assert_denied(out, "git commit")


class GuardSpellingTests(HookTestCase):
    """Guard spellings: git config keys ignore case, and short flags combine (design 8.2)."""

    @classmethod
    def setUpClass(cls):
        """Builds a project with the git hooks on."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)

    def test_lower_case_hooks_path_and_combined_n_are_refused(self):
        """-c core.hookspath= in any case, and commit -nm or -anm, skip the hooks."""
        commands = ("git -c core.hookspath=/dev/null commit -m x",
                    "git -c CORE.HOOKSPATH=/dev/null status",
                    "git commit -nm x", "git commit -anm x", "git config core.HooksPath x")
        outs = run_many([bash_call(self.project, MAIN, c) for c in commands])
        for out, command in zip(outs, commands):
            with self.subTest(command=command):
                self.assert_denied(out)

    def test_option_values_that_look_like_n_pass(self):
        """A message of "-n", or -n after "--", is not --no-verify."""
        commands = ("git commit -m -n", "git commit -m 'x' -- -n",
                    "git commit --author 'A <a@b>' -m x")
        outs = run_many([bash_call(self.project, MAIN, c) for c in commands])
        for out, command in zip(outs, commands):
            with self.subTest(command=command):
                self.assert_silent(out)


class LogVocabularyTests(HookTestCase):
    """A secret typed where a subcommand belongs never reaches the log (design 10)."""

    @classmethod
    def setUpClass(cls):
        """Builds a project and the Developer's start record."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        run_many([start_call(cls.project, DEV)])

    def test_unknown_subcommand_words_are_logged_as_a_question_mark(self):
        """git <secret> and gh <secret> are refused and logged without the secret."""
        outs = run_many([bash_call(self.project, DEV, f"git {SECRET} -m x"),
                         bash_call(self.project, DEV, f"gh pr {SECRET}")])
        for out in outs:
            self.assert_denied(out)
        text = self.project.log_text()
        self.assertNotIn(SECRET, text)
        subcommands = [line["subcommand"] for line in self.project.log_lines()]
        self.assertIn("git ?", subcommands)
        self.assertIn("gh pr ?", subcommands)


@unittest.skipUnless(IS_WINDOWS, "Windows compares paths without case")
class CaseOnlyInMissingFoldersTests(HookTestCase):
    """Case differs only in folders that do not exist yet, so realpath cannot fix it."""

    @classmethod
    def setUpClass(cls):
        """Builds a project."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)

    def test_missing_scratchpad_in_another_case_still_holds_the_path(self):
        """A write to <pad> in lower case is inside a scratchpad named in upper case."""
        name = unique("NewPad")
        pad = PAD / name
        target = PAD / name.lower() / "notes.txt"
        out = write_call(self.project, DEV, str(target), scratchpad=str(pad)).run()
        self.assert_silent(out)
        out = write_call(self.project, DEV, str(PAD / (name + "x") / "notes.txt"),
                         scratchpad=str(pad)).run()
        self.assert_denied(out, "needs-answer")


class StdinBodyTests(HookTestCase):
    """A PR body given on stdin through a heredoc is checked for R19 (design 8.2)."""

    @classmethod
    def setUpClass(cls):
        """Builds a project on a branch."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)

    def test_body_file_from_a_heredoc_on_stdin(self):
        """--body-file - with an attribution heredoc is refused; a clean one passes."""
        bad = ("gh pr create --title 'Add counting' --body-file - <<'EOF'\n"
               f"Counts words.\n\n{ATTRIBUTION_LINE}\nEOF")
        good = "gh pr create --title 'Add counting' --body-file - <<'EOF'\nCounts words.\nEOF"
        refused, passed = run_many([bash_call(self.project, MAIN, bad),
                                    bash_call(self.project, MAIN, good)])
        self.assert_denied(refused, "R19")
        self.assert_silent(passed)
