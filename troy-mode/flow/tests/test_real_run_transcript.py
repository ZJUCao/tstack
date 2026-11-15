"""Reading a prototype's transcripts (F12 design 5.3, 15.1; interface note section 4).

One prototype of F02, the feature being accepted, holds prompts,
``$LASTEXITCODE`` (in its own block too), ``$env:`` lines, ``Get-Content``,
lines that are not run, blank lines at the end of an output, a block above
any heading, a repeated heading, blocks that are not transcripts (one of
them compared through ``files``), and blocks fenced with tildes and with four
backticks. One engine run serves every test.
"""

import unittest

from flow_helpers import F02
from realrun_helpers import (
    RealProject, RealRunCase, block, command_of, commands_of, every_command, history,
    project_files, prototype_of, run_file, run_file_path, section_of,
)

PROTO = "docs/prototypes/F02-transcript.md"
ECHO = "sample echo \"two words\" 'single quoted' plain   spaced"
TEXT = (
    block("PS> sample say before any heading", "before any heading")
    + "\n# Transcript rules\n\nThe commands of the transcript tests.\n\n"
    + "## Say and echo\n\n"
    + block("PS> sample say hello world", "hello world",
            f"PS> {ECHO}", "[two words]", "[single quoted]", "[plain]", "[spaced]", "",
            'PS> sample echo "x;y"', "[x;y]", "", "")
    + "\n## Exit codes\n\n"
    + block("PS> sample fail 3 broken", "broken", "PS> $LASTEXITCODE", "3",
            "PS> sample code 5 fine", "fine")
    + "\nThe exit code of the last command, in a block of its own:\n\n"
    + block("PS> $lastexitcode", "5")
    + "\n## Variables\n\n"
    + block('PS> $env:MENU_COLOR = "blue"', "PS> $env:MENU_SIZE = 'big'",
            "PS> sample env MENU_COLOR MENU_SIZE", "MENU_COLOR=blue", "MENU_SIZE=big")
    + "\n## Variables again\n\n"
    + block("PS> sample env MENU_COLOR MENU_SIZE", "MENU_COLOR is not set",
            "MENU_SIZE is not set")
    + "\n## Files\n\n"
    + block('PS> sample write "my notes.txt" first line', 'PS> Get-Content "my notes.txt"',
            "first line", "PS> sample write out/saved.md saved text")
    + "\nThe saved file:\n\n"
    + block("saved text", info="markdown")
    + "\nAn older run, which is not a transcript:\n\n"
    + block("Output of an older version:", "PS> sample say not run", "not run", info="text")
    + "\n## Lines that are not run\n\n"
    + block("PS> sample say piped | Select-Object -First 1",
            "PS> sample say saved > out.txt",
            "PS> sample say one; sample say two",
            "PS> cd somewhere",
            "PS> notepad notes.txt")
    + "\n## Notes\n\nA section with settings and no transcript:\n\n"
    + block('lang = "zh-CN"', "PS> sample say in toml", info="toml")
    + "\n## Say and echo\n\n"
    + block("", "PS> sample say after a blank line", "after a blank line")
    + "\n"
    + block("PS> sample say tilde fence", "tilde fence", fence="~~~")
    + "\n"
    + block("PS> sample say four backticks", "four backticks", fence="````")
)
RUN = run_file("[sections.\"Files\"]\nfiles = [{ path = '<home>\\out\\saved.md', block = 1 }]",
               '[sections."Say and echo (2)"]\nstart = "empty"')
OTHER_LINES = ("sample say piped | Select-Object -First 1", "sample say saved > out.txt",
               "sample say one; sample say two", "cd somewhere", "notepad notes.txt")
HEADINGS = ("", "Say and echo", "Exit codes", "Variables", "Variables again", "Files",
            "Lines that are not run", "Say and echo (2)")


def line_number(typed: str) -> int:
    """The 1-based line of the prototype that holds ``PS> <typed>``."""
    return TEXT.split("\n").index(f"PS> {typed}") + 1


class TranscriptTests(RealRunCase):
    """One run of ``real-run --item F02`` on the transcript prototype (design 5.3)."""

    @classmethod
    def setUpClass(cls):
        """Builds the project and runs the engine once."""
        rows = [("Transcript rules", "F02", PROTO)]
        files = project_files(rows=rows, files={PROTO: TEXT, run_file_path(PROTO): RUN})
        cls.project = RealProject(history(files))
        cls.out = cls.project.real_run("--item", "F02")

    def setUp(self):
        """Every test reads the one report, which must be a clean run."""
        self.report = self.real_report(self.out, 0)

    def cmd(self, typed: str, heading=None, kind=None) -> dict:
        """The one command entry of the prototype with this typed line."""
        return command_of(self.report, PROTO, typed, heading, kind)

    def test_counts(self):
        """Fifteen commands match and the five lines that are not run do not count as failures."""
        self.assertEqual(self.report["counts"]["all"],
                         {"matches": 15, "mismatch": 0, "waits": 0, "not_run": 5})
        self.assertEqual(self.report["problems"], [])

    def test_prototype_entry(self):
        """The prototype has a transcript, its run file, and its Feature cell's ID."""
        entry = prototype_of(self.report, PROTO)
        self.assertEqual((entry["transcript"], entry["run_file"], entry["features"]),
                         (True, run_file_path(PROTO), [F02.id]))

    def test_sections_in_order_with_a_repeated_heading(self):
        """A block above every heading is section ""; the second "Say and echo" is "(2)"."""
        sections = prototype_of(self.report, PROTO)["sections"]
        self.assertEqual([s["heading"] for s in sections if s["commands"]], list(HEADINGS))
        self.assertEqual(self.cmd("sample say before any heading", "")["result"], "matches")
        self.assertEqual([c["typed"] for c in commands_of(self.report, PROTO, "Say and echo (2)")],
                         ["sample say after a blank line", "sample say tilde fence",
                          "sample say four backticks"])

    def test_section_starts(self):
        """The run file's ``start = "empty"`` is reported; other sections start by default."""
        self.assertEqual(section_of(self.report, PROTO, "Say and echo (2)")["start"], "empty")
        self.assertEqual(section_of(self.report, PROTO, "Files")["start"], "default")

    def test_prompt_and_its_output(self):
        """A ``PS> `` line is the input; the lines after it, the expected output."""
        entry = self.cmd("sample say hello world")
        self.assert_command(entry, "matches", kind="program", run="sample say hello world",
                            expected=["hello world"], real=["hello world"],
                            line=line_number("sample say hello world"), replaced=None)

    def test_arguments_split_at_spaces_and_keep_quoted_text(self):
        """Runs of spaces split words; ``"..."`` and ``'...'`` keep text together, unquoted."""
        entry = self.cmd(ECHO)
        self.assert_command(entry, "matches", kind="program",
                            real=["[two words]", "[single quoted]", "[plain]", "[spaced]"])

    def test_a_separator_inside_quotes_is_part_of_an_argument(self):
        """``;`` in quotes does not make the line one that is not run."""
        self.assert_command(self.cmd('sample echo "x;y"'), "matches", kind="program",
                            real=["[x;y]"])

    def test_blank_lines_at_the_end_of_an_output_are_left_out(self):
        """The blank lines before the next prompt and before the fence are not expected."""
        self.assertEqual(self.cmd(ECHO)["expected"],
                         ["[two words]", "[single quoted]", "[plain]", "[spaced]"])
        self.assertEqual(self.cmd('sample echo "x;y"')["expected"], ["[x;y]"])

    def test_last_exit_code_sets_the_expected_code(self):
        """``$LASTEXITCODE`` gives the command before it its expected code, across blocks too."""
        self.assert_command(self.cmd("sample fail 3 broken"), "matches", expected_exit=3, exit=3,
                            expected=["broken"], real=["broken"])
        self.assert_command(self.cmd("sample code 5 fine"), "matches", expected_exit=5, exit=5)
        self.assert_command(self.cmd("sample say hello world"), "matches", expected_exit=None,
                            exit=0)

    def test_env_lines_set_variables_and_are_not_commands(self):
        """``$env:`` with double and single quotes sets the variables; it is no command."""
        self.assert_command(self.cmd("sample env MENU_COLOR MENU_SIZE", "Variables"), "matches",
                            real=["MENU_COLOR=blue", "MENU_SIZE=big"])
        typed = [entry.get("typed") or "" for _, _, entry in every_command(self.report)]
        self.assertFalse([t for t in typed if t.lower().startswith("$env:")], typed)

    def test_env_values_do_not_reach_the_next_section(self):
        """The next section starts without the ``$env:`` values."""
        self.assert_command(self.cmd("sample env MENU_COLOR MENU_SIZE", "Variables again"),
                            "matches", real=["MENU_COLOR is not set", "MENU_SIZE is not set"])

    def test_get_content_prints_a_file_of_the_run(self):
        """``Get-Content`` with a quoted relative path reads the file the program wrote."""
        self.assert_command(self.cmd('Get-Content "my notes.txt"'), "matches",
                            kind="get-content", expected=["first line"], real=["first line"])

    def test_lines_that_are_not_run(self):
        """A pipe, a redirection, ``;``, and words that are no program: not run, with a reason."""
        for typed in OTHER_LINES:
            with self.subTest(typed=typed):
                entry = self.cmd(typed, "Lines that are not run")
                self.assert_not_run(entry)
                self.assertEqual(entry["kind"], "other")
                self.assertIsInstance(entry["reason"], str)
                self.assertNotEqual(entry["reason"].strip(), "")

    def test_blocks_that_are_not_transcripts_are_not_run(self):
        """``PS> `` lines inside text and TOML blocks are no commands."""
        typed = [entry.get("typed") for _, _, entry in every_command(self.report)]
        self.assertNotIn("sample say not run", typed)
        self.assertNotIn("sample say in toml", typed)

    def test_files_compares_a_block_that_is_not_a_transcript(self):
        """``files`` block 1 is the section's first block that is not a transcript."""
        found = [c for c in commands_of(self.report, PROTO, "Files") if c.get("kind") == "file"]
        self.assertEqual(len(found), 1, commands_of(self.report, PROTO, "Files"))
        self.assert_command(found[0], "matches", expected=["saved text"], real=["saved text"])
        kinds = [c["kind"] for c in commands_of(self.report, PROTO, "Files")]
        self.assertEqual(kinds[-1], "file", "files are compared after the section's commands")

    def test_other_fences_and_a_blank_first_line(self):
        """Tildes, four backticks, and a block whose first line is blank are transcripts too."""
        for typed, line in (("sample say after a blank line", "after a blank line"),
                            ("sample say tilde fence", "tilde fence"),
                            ("sample say four backticks", "four backticks")):
            with self.subTest(typed=typed):
                self.assert_command(self.cmd(typed), "matches", real=[line])


if __name__ == "__main__":
    unittest.main()
