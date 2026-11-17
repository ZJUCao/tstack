"""Posting guard group (F05 design 8.2, 10, 13.1 "Posting guard (D200)", and D200).

For the main session, the PreToolUse hook checks the text of every gh command
that posts text to GitHub before it runs: the option values, every heredoc in
the call, and the contents of each named file, with troy-check's attribution
rules in the project's [attribution] mode. A failure is refused with rule
attribution, and the reason names R19, the command, and the first line that
fails. The log line holds the command name and no text or file path. The hook
fails closed on text it cannot see. Subagents keep the gh refusal of design
7.3.

The tests are written from the design (version 1.2) before the code exists.

Conventions, beyond those of hook_helpers.py.

1. "Bad" text in a strict project holds the bare word Claude (STRICT_TEXT,
   strict.md, strict.json), which only strict mode refuses. Trailers tests use
   the "Generated with" line or a Co-Authored-By trailer (attrib.md,
   attrib.json), which both modes refuse.
2. Every refused case has a passing twin with clean text (CLEAN_TEXT,
   clean.md, clean.json), so a hook that refuses every post fails.
3. Files are named relative to the input cwd, the project root, unless a test
   says otherwise. No path in a passing case holds a strict-mode word except
   where a test puts one there on purpose (the claude/ folders).
4. Each refusal runs alone and checks its one new log line: rule
   attribution, decision deny, no agent_id, and the command name in
   subcommand. Calls that must be silent run in parallel (run_many) in a
   second project whose log no test reads, because parallel hook runs append
   to one log file at once.
5. A refusal's reason must hold "R19" and the command name, as design 8.2's
   "The refusal" says. Fail-closed refusals share rule attribution and are
   held to the same two fragments.

Planted bugs (design 13.2) and the tests that catch them. Each test also
names its bug in its docstring.

- comment missing from the posting table:
  PostingFormTests.test_bad_text_is_refused_in_every_form,
  StdinTests.test_bad_heredoc_on_stdin_is_refused,
  StdinTests.test_92_shape_is_refused.
- -F not read: PostingFormTests.test_bad_text_is_refused_in_every_form
  (-F file) and test_gh_api_write_with_bad_text_is_refused (-F key=value and
  -F key=@file); NeverPathsTests.test_bad_file_at_a_clean_path_is_refused.
- The path scanned instead of the contents:
  NeverPathsTests.test_clean_file_in_a_folder_named_claude_passes and
  test_bad_file_at_a_clean_path_is_refused.
- A missing file allowed: FailClosedTests.test_missing_or_unreadable_file_is_refused.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -p "test_posting_guard.py" -v
"""

import shlex
import unittest

from hook_helpers import (
    ATTRIBUTION_LINE, MAIN, SCRATCH, SECRET, TRAILER, HookTestCase, Project, bash_call,
    make_config, q, remove_tree, role, run_many, start_call, unique, write_file,
)

STRICT_TEXT = "Works with Claude."
CLEAN_TEXT = "Count words."

# Files every test project holds, beside the base files.
FILES = {
    "clean.md": "## Why\n\nCount words.\n",
    "strict.md": "## Why\n\nWorks with Claude.\n",
    "attrib.md": f"## Why\n\nCount words.\n\n{ATTRIBUTION_LINE}\n",
    "clean.json": '{"body": "Count words."}\n',
    "strict.json": '{"body": "Works with Claude."}\n',
    "attrib.json": '{"body": "Count words. ' + ATTRIBUTION_LINE + '"}\n',
    "claude/clean.md": "## Why\n\nCount words.\n",
    "claude/clean.json": '{"body": "Count words."}\n',
    "notes/only-in-notes.md": "Count words.\n",
    "notes/only-in-notes-bad.md": "Works with Claude.\n",
    # The comment of ZJUCao/recipe-menu#92: it held a word strict mode refuses.
    "c.md": "The parser change looks right.\nAsk Claude to rerun the tests.\n",
    "lines.md": "Count words.\nThe second line names Claude.\nThe third line names Anthropic.\n",
}

# Design 8.2's posting table: the command name, a call with its other
# arguments, its text options as (long, short), and its file option.
POSTING = (
    ("gh pr create", "gh pr create", (("--title", "-t"), ("--body", "-b")),
     ("--body-file", "-F")),
    ("gh pr edit", "gh pr edit 7", (("--title", "-t"), ("--body", "-b")), ("--body-file", "-F")),
    ("gh issue create", "gh issue create", (("--title", "-t"), ("--body", "-b")),
     ("--body-file", "-F")),
    ("gh issue edit", "gh issue edit 3", (("--title", "-t"), ("--body", "-b")),
     ("--body-file", "-F")),
    ("gh pr comment", "gh pr comment 5", (("--body", "-b"),), ("--body-file", "-F")),
    ("gh issue comment", "gh issue comment 3", (("--body", "-b"),), ("--body-file", "-F")),
    ("gh pr review", "gh pr review 5 --comment", (("--body", "-b"),), ("--body-file", "-F")),
    ("gh pr merge", "gh pr merge 5 --squash", (("--subject", "-t"), ("--body", "-b")),
     ("--body-file", "-F")),
    ("gh release create", "gh release create v1.0", (("--title", "-t"), ("--notes", "-n")),
     ("--notes-file", "-F")),
    ("gh release edit", "gh release edit v1.0", (("--title", "-t"), ("--notes", "-n")),
     ("--notes-file", "-F")),
)

API_POST = "gh api -X POST repos/o/r/issues/1/comments"

# gh api calls that post nothing: a GET with no fields (design 7.3 and 8.2).
API_READS = (
    "gh api repos/o/r/pulls",
    "gh api -X GET repos/o/r/issues/1/comments",
    "gh api --method GET repos/o/r/issues/1/comments --jq '.[].body'",
    "gh api --paginate repos/o/r/pulls --jq '.[].number'",
)


def option_forms(long, short, value):
    """Returns an option's --x v, --x=v, -x v, and -xv forms (design 8.2)."""
    v = shlex.quote(value)
    return (f"{long} {v}", f"{long}={v}", f"{short} {v}", f"{short}{v}")


def posting_cases(text, file, long_only=False):
    """Returns (command, name) for each posting command, text option, and form.

    Args:
        text: The value of each text option.
        file: The file each body or notes file option names.
        long_only: Only the --x v form.

    Returns:
        A list of (command, command name).
    """
    cases = []
    for name, base, text_options, file_option in POSTING:
        for option in (*text_options, file_option):
            value = file if option == file_option else text
            forms = option_forms(*option, value)
            for form in forms[:1] if long_only else forms:
                cases.append((f"{base} {form}", name))
    return cases


def api_cases(text, file, data, long_only=False):
    """Returns (command, "gh api") for gh api writes with the text in each place.

    Args:
        text: The value of the -f and -F fields.
        file: The file a -F body=@file field names.
        data: The file --input names.
        long_only: Only the --x v form of each option.

    Returns:
        A list of (command, "gh api").
    """
    field = "body=" + shlex.quote(text)
    file_field = "body=@" + shlex.quote(file)
    forms = []
    for long, short, value in (("--raw-field", "-f", field), ("--field", "-F", field),
                               ("--field", "-F", file_field)):
        four = (f"{long} {value}", f"{long}={value}", f"{short} {value}", f"{short}{value}")
        forms += four[:1] if long_only else four
    inputs = (f"--input {shlex.quote(data)}", f"--input={shlex.quote(data)}")
    forms += inputs[:1] if long_only else inputs
    cases = [(f"{API_POST} {form}", "gh api") for form in forms]
    if not long_only:
        query = ('mutation { addComment(input: {subjectId: "I_1", body: "' + text +
                 '"}) { clientMutationId } }')
        cases += [
            (f"gh api repos/o/r/issues/1/comments -f {field}", "gh api"),
            (f"gh api -XPOST repos/o/r/issues/1/comments -f {field}", "gh api"),
            (f"gh api --method PATCH repos/o/r/issues/comments/9 -f {field}", "gh api"),
            (f"gh api --method=POST repos/o/r/issues -f title={shlex.quote(text)} "
             "-f body='Count words.'", "gh api"),
            (f"gh api graphql -f query={shlex.quote(query)}", "gh api"),
        ]
    return cases


class PostingTestCase(HookTestCase):
    """Runs main-session Bash calls and checks refusals and their log lines.

    Refusals run one at a time in ``project``, so each new log line can be
    read. Calls that must be silent run in parallel in ``quiet``, a copy
    whose log no test reads: a wrong refusal there cannot spoil another
    test's log.
    """

    project = None
    quiet = None

    @classmethod
    def make_project(cls, mode="strict"):
        """Builds a project in the attribution mode, with FILES, removed after the class."""
        project = Project(config=make_config(mode=mode))
        cls.addClassCleanup(project.close)
        for rel, content in FILES.items():
            project.write(rel, content)
        return project

    @classmethod
    def setUpClass(cls):
        """Builds a strict project for refusals and one for silent calls."""
        cls.project = cls.make_project()
        cls.quiet = cls.make_project()

    def run_main(self, command, project=None):
        """Runs one main-session Bash PreToolUse call."""
        return bash_call(project or self.project, MAIN, command).run()

    def check_silent(self, commands, project=None):
        """Asserts that every command is silent, running them in parallel."""
        project = project or self.quiet
        outs = run_many([bash_call(project, MAIN, c) for c in commands])
        for command, out in zip(commands, outs):
            with self.subTest(command=command):
                self.assert_silent(out, msg=command)

    def check_refused(self, cases, project=None):
        """Asserts each (command, name) is refused with R19 and name, and logged once."""
        for command, name in cases:
            with self.subTest(command=command):
                self.assert_refused_by(command, name, project)

    def assert_refused_by(self, command, name, project=None, rule="attribution"):
        """Asserts one main-session refusal with R19 and name, and its one log line."""
        project = project or self.project
        before = len(project.log_lines())
        out = self.run_main(command, project)
        self.assert_denied(out, "R19", name, msg=command)
        lines = project.log_lines()[before:]
        self.assertEqual(1, len(lines), f"{command!r}: expected one new log line: {lines}")
        expected = {"rule": rule, "subcommand": name, "decision": "deny", "agent_id": None,
                    "event": "PreToolUse", "tool": "Bash"}
        self.assertEqual(expected, {k: lines[0].get(k) for k in expected}, command)


class PostingFormTests(PostingTestCase):
    """Each posting command of design 8.2, in each option form, in strict and trailers mode."""

    @classmethod
    def setUpClass(cls):
        """Builds strict projects and trailers projects."""
        super().setUpClass()
        cls.trailers = cls.make_project("trailers")
        cls.trailers_quiet = cls.make_project("trailers")

    def test_bad_text_is_refused_in_every_form(self):
        """A strict-mode word in each title, body, subject, notes, or file option is refused.

        Planted bugs caught: comment missing from the posting table; -F not read.
        """
        self.check_refused(posting_cases(STRICT_TEXT, "strict.md"))

    def test_clean_text_passes_in_every_form(self):
        """Pair: the same commands with clean text and a clean file are silent."""
        self.check_silent([c for c, _ in posting_cases(CLEAN_TEXT, "clean.md")])

    def test_gh_api_write_with_bad_text_is_refused(self):
        """gh api with a method or fields: bad -f, -F, -F key=@file, and --input text is refused.

        Planted bug caught: -F not read.
        """
        self.check_refused(api_cases(STRICT_TEXT, "strict.md", "strict.json"))

    def test_gh_api_write_with_clean_text_passes(self):
        """Pair: the same gh api writes with clean values and files are silent."""
        self.check_silent([c for c, _ in api_cases(CLEAN_TEXT, "clean.md", "clean.json")])

    def test_gh_api_get_passes(self):
        """A gh api GET with no fields posts nothing and is silent."""
        self.check_silent(API_READS)

    def test_strict_word_passes_in_trailers_mode(self):
        """In trailers mode, the bare word Claude in any posted text is silent."""
        cases = (posting_cases(STRICT_TEXT, "strict.md", long_only=True) +
                 api_cases(STRICT_TEXT, "strict.md", "strict.json", long_only=True))
        self.check_silent([c for c, _ in cases], self.trailers_quiet)

    def test_attribution_line_is_refused_in_trailers_mode(self):
        """In trailers mode, the "Generated with" line, a trailer, and attrib files are refused."""
        cases = (posting_cases(ATTRIBUTION_LINE, "attrib.md", long_only=True) +
                 api_cases(ATTRIBUTION_LINE, "attrib.md", "attrib.json", long_only=True))
        cases += [
            ("gh pr comment 5 --body " + shlex.quote(f"Count words.\n\n{TRAILER}"),
             "gh pr comment"),
            ("gh issue create --title 'Add x' -b " + shlex.quote(f"Count words.\n\n{TRAILER}"),
             "gh issue create"),
            (f"{API_POST} -f body=" + shlex.quote(TRAILER), "gh api"),
        ]
        self.check_refused(cases, self.trailers)

    def test_reason_names_r19_the_command_and_the_first_failing_line(self):
        """The reason holds R19, the command name, and the text of the first line that fails."""
        out = self.run_main("gh pr comment 5 --body-file lines.md")
        self.assert_denied(out, "R19", "gh pr comment", "The second line names Claude.")
        body = shlex.quote("Count words.\nThe second line thanks Anthropic.\n"
                           "The third line names Claude.")
        out = self.run_main(f"gh issue comment 3 --body {body}")
        self.assert_denied(out, "R19", "gh issue comment", "The second line thanks Anthropic.")

    def test_commands_with_no_text_pass(self):
        """gh pr merge --rebase and gh pr review --approve post no text and are silent."""
        self.check_silent(("gh pr merge 5 --rebase --delete-branch --match-head-commit abc123",
                           "gh pr review 5 --approve",
                           "gh pr merge 5 --squash --auto",
                           "gh pr edit 7 --add-label bug",
                           "gh pr view 5 --json body"))

    def test_same_commands_with_bad_text_are_refused(self):
        """Pair: gh pr merge with a bad subject and gh pr review with a bad body are refused."""
        self.assert_refused_by("gh pr merge 5 --rebase --delete-branch --subject "
                               "'Works with Claude.'", "gh pr merge")
        self.assert_refused_by("gh pr review 5 --approve --body 'Works with Claude.'",
                               "gh pr review")

    def test_other_repository_is_checked(self):
        """gh issue create --repo or -R for another repository with bad text is refused."""
        self.assert_refused_by("gh issue create --repo other/repo --title 'Works with Claude.' "
                               "--body 'Count words.'", "gh issue create")
        self.assert_refused_by("gh issue create -R other/repo --title 'Add x' "
                               "--body-file strict.md", "gh issue create")
        self.assert_refused_by("gh pr comment 5 --repo other/repo --body 'Works with Claude.'",
                               "gh pr comment")

    def test_other_repository_with_clean_text_passes(self):
        """Pair: the same commands for another repository with clean text are silent."""
        self.check_silent(("gh issue create --repo other/repo --title 'Add x' "
                           "--body 'Count words.'",
                           "gh issue create -R other/repo --title 'Add x' --body-file clean.md",
                           "gh pr comment 5 --repo other/repo --body 'Count words.'"))


class StdinTests(PostingTestCase):
    """Heredocs, pipes, and command substitutions (design 8.2)."""

    HEREDOCS = (
        ("gh pr comment 5 --body-file - <<'EOF'\nCount words.\n{line}\nEOF", "gh pr comment"),
        ("gh issue comment 3 -F - <<EOF\n{line}\nEOF", "gh issue comment"),
        ("gh release create v1.0 --notes-file - <<'EOF'\n{line}\nEOF", "gh release create"),
        (API_POST + " --input - <<'EOF'\n{{\"body\": \"{line}\"}}\nEOF", "gh api"),
        (API_POST + " -F body=@- <<'EOF'\n{line}\nEOF", "gh api"),
    )
    CAT_HEREDOC = (
        ("gh pr comment 5 --body \"$(cat <<'EOF'\nCount words.\n\n{line}\nEOF\n)\"",
         "gh pr comment"),
        ("gh pr create --title 'Add word counting' --body \"$(cat <<'EOF'\n## Why\n\n{line}\n"
         "EOF\n)\"", "gh pr create"),
    )
    SHAPE_92 = ("python troy_flow.py check-text --file {f} | grep -q ok; "
                "gh pr comment 92 --body-file {f}")

    def test_bad_heredoc_on_stdin_is_refused(self):
        """A --body-file -, --notes-file -, --input -, or -F body=@- heredoc with bad text is refused.

        Planted bug caught: comment missing from the posting table.
        """
        self.check_refused([(c.format(line=STRICT_TEXT), n) for c, n in self.HEREDOCS])

    def test_clean_heredoc_on_stdin_passes(self):
        """Pair: the same heredocs with clean text are silent."""
        self.check_silent([c.format(line=CLEAN_TEXT) for c, _ in self.HEREDOCS])

    def test_pipe_or_redirect_into_a_dash_file_is_refused(self):
        """A - file fed by a pipe or a file redirect, not a heredoc, is refused even when clean."""
        for command, name in (
                ("cat clean.md | gh pr comment 5 --body-file -", "gh pr comment"),
                ("cat clean.md | gh pr comment 5 -F -", "gh pr comment"),
                ("gh pr comment 5 --body-file - < clean.md", "gh pr comment"),
                ("cat clean.md | gh release create v1.0 --notes-file -", "gh release create"),
                ("cat clean.md | gh release edit v1.0 -F -", "gh release edit"),
                (f"cat clean.json | {API_POST} --input -", "gh api"),
                (f"cat clean.md | {API_POST} -F body=@-", "gh api")):
            with self.subTest(command=command):
                self.assert_refused_by(command, name)

    def test_92_shape_is_refused(self):
        """check-text's output read with grep, then gh pr comment with a bad file, is refused.

        Planted bug caught: comment missing from the posting table.
        """
        self.assert_refused_by(self.SHAPE_92.format(f="c.md"), "gh pr comment")

    def test_92_shape_with_a_clean_file_passes(self):
        """Pair: the same line with a clean file is silent."""
        self.check_silent((self.SHAPE_92.format(f="clean.md"),))

    def test_substitution_or_unknown_variable_in_a_text_option_is_refused(self):
        """--body "$(cat file)", backticks, and an unknown variable are refused even when clean."""
        for command, name in (
                ('gh pr comment 5 --body "$(cat clean.md)"', "gh pr comment"),
                ('gh pr comment 5 --body "`cat clean.md`"', "gh pr comment"),
                ("gh issue create --title \"$TITLE\" --body 'Count words.'", "gh issue create"),
                ('gh pr comment 5 --body-file "$BODY_FILE"', "gh pr comment")):
            with self.subTest(command=command):
                self.assert_refused_by(command, name)

    def test_bad_cat_heredoc_substitution_is_refused(self):
        """--body "$(cat <<'EOF' ...)" with a bad line is refused."""
        self.check_refused([(c.format(line=STRICT_TEXT), n) for c, n in self.CAT_HEREDOC])

    def test_clean_cat_heredoc_substitution_passes(self):
        """Pair: the same substitutions with clean text are silent."""
        self.check_silent([c.format(line=CLEAN_TEXT) for c, _ in self.CAT_HEREDOC])

    def test_every_heredoc_in_a_posting_call_is_checked(self):
        """A heredoc that writes a file is text too: a bad one refuses the call's post."""
        self.assert_refused_by("cat > later.md <<'EOF'\nWorks with Claude.\nEOF\n"
                               "gh pr comment 5 --body-file clean.md", "gh pr comment")

    def test_heredoc_without_a_post_or_with_clean_text_passes(self):
        """Pair: the bad heredoc alone, and a clean heredoc before the post, are silent."""
        self.check_silent(("cat > later.md <<'EOF'\nWorks with Claude.\nEOF",
                           "cat > later.md <<'EOF'\nCount words.\nEOF\n"
                           "gh pr comment 5 --body-file clean.md"))


class FailClosedTests(PostingTestCase):
    """Design 8.2 "Fail closed": text the hook cannot see is refused with rule attribution."""

    def test_missing_or_unreadable_file_is_refused(self):
        """A missing body, notes, or input file, or a folder named as one, is refused.

        Planted bug caught: a missing file allowed.
        """
        for command, name in (
                ("gh pr comment 5 --body-file missing.md", "gh pr comment"),
                ("gh issue create --title 'Add x' -F missing.md", "gh issue create"),
                ("gh release create v1.0 --notes-file missing.md", "gh release create"),
                (f"{API_POST} --input missing.json", "gh api"),
                (f"{API_POST} -F body=@missing.md", "gh api"),
                ("gh pr comment 5 --body-file notes", "gh pr comment")):
            with self.subTest(command=command):
                self.assert_refused_by(command, name)

    def test_existing_clean_files_pass(self):
        """Pair: the same commands naming existing clean files are silent."""
        self.check_silent(("gh pr comment 5 --body-file clean.md",
                           "gh issue create --title 'Add x' -F clean.md",
                           "gh release create v1.0 --notes-file clean.md",
                           f"{API_POST} --input clean.json",
                           f"{API_POST} -F body=@clean.md"))

    def test_editor_and_web_are_refused(self):
        """--editor, -e, --web, and -w write text where the hook cannot see it: refused."""
        for command, name in (
                ("gh pr comment 5 --editor", "gh pr comment"),
                ("gh pr comment 5 -e", "gh pr comment"),
                ("gh issue comment 3 --web", "gh issue comment"),
                ("gh issue comment 3 -w", "gh issue comment"),
                ("gh issue create --title 'Add x' --editor", "gh issue create"),
                ("gh issue create -w", "gh issue create"),
                ("gh pr create --title 'Add x' --web", "gh pr create"),
                ("gh pr create -e", "gh pr create")):
            with self.subTest(command=command):
                self.assert_refused_by(command, name)

    def test_unfollowed_cd_before_a_relative_file_is_refused(self):
        """A relative body file after cd to an unknown variable is refused."""
        self.assert_refused_by('cd "$X" && gh pr comment 5 --body-file clean.md',
                               "gh pr comment")

    def test_file_named_by_an_unknown_variable_is_refused(self):
        """--body-file "$G" with G unknown is refused, even beside a clean file named $G.

        Added after a planted bug survived: reading the word as a literal path.
        """
        self.project.write("$G", "Fix the counter.\n")
        self.assert_refused_by('gh pr comment 5 --body-file "$G"', "gh pr comment")
        self.assert_silent(self.run_main('G=clean.md; gh pr comment 5 --body-file "$G"'))

    def test_file_is_read_in_the_folder_a_literal_cd_names(self):
        """After cd notes, a clean file there is silent and a bad one is refused."""
        self.check_silent(("cd notes && gh pr comment 5 --body-file only-in-notes.md",))
        self.assert_refused_by("cd notes && gh pr comment 5 --body-file only-in-notes-bad.md",
                               "gh pr comment")


class NeverPathsTests(PostingTestCase):
    """Design 8.2 "Never paths": the hook checks file contents, never paths or the command line."""

    @classmethod
    def setUpClass(cls):
        """Adds a scratchpad-like folder outside the project with a claude/ and a notes/ file."""
        super().setUpClass()
        cls.pad = SCRATCH / unique("pad-")
        cls.addClassCleanup(remove_tree, cls.pad)
        cls.pad_clean = write_file(cls.pad, "claude/post.md", "## Why\n\nCount words.\n")
        cls.pad_bad = write_file(cls.pad, "notes/post.md", "## Why\n\nWorks with Claude.\n")

    def test_clean_file_in_a_folder_named_claude_passes(self):
        """A clean file whose path holds the word claude is silent, by relative or absolute path.

        Planted bug caught: the path scanned instead of the contents.
        """
        self.check_silent((
            "gh pr comment 5 --body-file claude/clean.md",
            f"gh pr comment 5 --body-file {q(self.quiet.path('claude/clean.md'))}",
            f"gh pr comment 5 --body-file {q(self.pad_clean)}",
            f"gh issue create --title 'Add x' -F {q(self.pad_clean)}",
            "gh release create v1.0 --notes-file claude/clean.md",
            f"{API_POST} -F body=@claude/clean.md",
            f"{API_POST} --input claude/clean.json",
        ))

    def test_bad_file_at_a_clean_path_is_refused(self):
        """A bad file whose path holds no strict-mode word is refused.

        Planted bugs caught: the path scanned instead of the contents; -F not read.
        """
        self.check_refused((
            (f"gh pr comment 5 --body-file {q(self.pad_bad)}", "gh pr comment"),
            (f"gh issue create --title 'Add x' -F {q(self.pad_bad)}", "gh issue create"),
            ("gh release create v1.0 --notes-file notes/only-in-notes-bad.md",
             "gh release create"),
            (f"{API_POST} -F body=@strict.md", "gh api"),
            (f"{API_POST} --input strict.json", "gh api"),
        ))

    def test_strict_word_outside_the_text_passes(self):
        """A strict-mode word in a repository name or an API endpoint is not text: silent."""
        self.check_silent((
            "gh pr comment 5 --repo o/claude-notes --body 'Count words.'",
            "gh issue create -R o/claude-notes --title 'Add x' --body-file clean.md",
            "gh api -X POST repos/o/claude-notes/issues/1/comments -f body='Count words.'",
        ))

    def test_same_calls_with_bad_text_are_refused(self):
        """Pair: the same calls with a bad body are refused."""
        self.check_refused((
            ("gh pr comment 5 --repo o/claude-notes --body 'Works with Claude.'",
             "gh pr comment"),
            ("gh issue create -R o/claude-notes --title 'Add x' --body-file strict.md",
             "gh issue create"),
            ("gh api -X POST repos/o/claude-notes/issues/1/comments "
             "-f body='Works with Claude.'", "gh api"),
        ))


class SubagentPostingTests(PostingTestCase):
    """Subagents keep the gh refusal of design 7.3 for every posting command."""

    @classmethod
    def setUpClass(cls):
        """Builds a strict project and starts a Developer."""
        super().setUpClass()
        cls.dev = role("developer", unique("-post"))
        start_call(cls.project, cls.dev).run()

    def test_posting_commands_are_gh_refusals_for_a_subagent(self):
        """A Developer's gh pr comment, issue create, release create, and api write: rule gh."""
        for command, name in (
                ("gh pr comment 5 --body 'Count words.'", "gh pr comment"),
                ("gh issue create --title 'Add x' --body-file strict.md", "gh issue create"),
                ("gh release create v1.0 --notes 'Count words.'", "gh release create"),
                (f"{API_POST} -f body='Count words.'", "gh api")):
            with self.subTest(command=command):
                before = len(self.project.log_lines())
                out = bash_call(self.project, self.dev, command).run()
                self.assert_denied(out, name, msg=command)
                lines = self.project.log_lines()[before:]
                self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
                self.assertEqual(("gh", name, self.dev.agent_id),
                                 (lines[0]["rule"], lines[0]["subcommand"],
                                  lines[0]["agent_id"]))

    def test_reads_pass_for_a_subagent(self):
        """Pair: the Developer's gh pr view and gh api GET are silent."""
        for command in ("gh pr view 5 --json body", "gh api repos/o/r/pulls"):
            with self.subTest(command=command):
                self.assert_silent(bash_call(self.project, self.dev, command).run())


class PostingLogTests(PostingTestCase):
    """Design 8.2 and 10: a refusal logs the command name, never the text or a file's path."""

    @classmethod
    def setUpClass(cls):
        """Nothing: each test builds its own project."""

    def setUp(self):
        """Builds a fresh strict project with FILES."""
        self.project = Project()
        self.addCleanup(self.project.close)
        for rel, content in FILES.items():
            self.project.write(rel, content)

    def test_refusal_logs_the_command_name_without_text_or_path(self):
        """Refusals log rule attribution and the command name; no text and no file path."""
        folder = f"notes-{SECRET}"
        self.project.write(f"{folder}/body.md", f"Token {SECRET}.\nWorks with Claude.\n")
        for command, name in (
                (f"gh pr comment 5 --body-file {folder}/body.md", "gh pr comment"),
                (f"gh issue create --title 'Add x' --body 'Token {SECRET} works with Claude.'",
                 "gh issue create"),
                (f"gh release create v1.0 --notes-file {folder}/body.md", "gh release create"),
                (f"{API_POST} -F body=@{folder}/body.md", "gh api")):
            with self.subTest(command=command):
                self.assert_refused_by(command, name)
        text = self.project.log_text()
        for fragment in (SECRET, "Works with", "works with", "body.md"):
            self.assertNotIn(fragment, text, f"the log holds {fragment!r}:\n{text}")

    def test_fail_closed_refusal_logs_no_path(self):
        """A missing file's refusal logs the command name and not the file's name."""
        self.assert_refused_by(f"gh pr comment 5 --body-file missing-{SECRET}.md",
                               "gh pr comment")
        self.assertNotIn(SECRET, self.project.log_text())

    def test_clean_posts_write_no_line(self):
        """Pair: silent posts add no log line."""
        for command in ("gh pr comment 5 --body-file clean.md",
                        "gh issue create --title 'Add x' --body 'Count words.'"):
            with self.subTest(command=command):
                self.assert_silent(self.run_main(command), msg=command)
        self.assertEqual([], self.project.log_lines())


if __name__ == "__main__":
    unittest.main()
