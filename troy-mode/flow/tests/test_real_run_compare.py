"""Comparing the real output with the prototype (F12 design 5.6, 15.1; interface note section 7).

Three projects of F02, each run once, side by side:

- ``match``: line ends (a prototype stored with CRLF), spaces at line ends,
  blank lines at the end, ``...``, exit codes, both streams, and Chinese
  columns, all of which match;
- ``mismatch``: columns off by the width of Chinese characters, a wrong exit
  code, a ``...`` that cannot match, text that is not UTF-8, runs of spaces,
  and a saved file, each a mismatch with its diff;
- ``paths``: the path map in both directions and longest first.

Planted bugs of design 15.2 caught here:

- "exit codes not compared": ``MismatchTests.test_wrong_exit_code_is_a_mismatch``.
- "``...`` not handled": ``MatchTests.test_dots_match_any_number_of_lines``.
- "the path map applied one way only": ``PathMapTests.test_command_paths_are_mapped_longest_first``
  (prototype to run path) and ``test_output_paths_are_mapped_back`` (run path to prototype).
"""

import os
import unittest

from flow_helpers import new_dir, parallel
from realrun_helpers import (
    NARROW_ROW, TABLE_LINES, RealProject, RealRunCase, block, command_of, commands_of, diff_lines,
    history, project_files, run_file, run_file_path,
)

WINDOWS = os.name == "nt"
MATCH = "docs/prototypes/F02-compare.md"
CRLF_PROTO = "docs/prototypes/F02-crlf.md"
MISMATCH = "docs/prototypes/F02-mismatch.md"
PATHS = "docs/prototypes/F02-paths.md"

MATCH_TEXT = (
    "# Compare\n\n## Chinese columns\n\n" + block("PS> sample table", *TABLE_LINES)
    + "\n## Trailing spaces and blank lines\n\n"
    + block("PS> sample trailing", "x", "y",
            "PS> sample say spaced", "spaced" + " " * 3 + "\t",
            "PS> sample say last", "last", "", "")
    + "\n## Dots\n\n"
    + block("PS> sample lines 1 10", "row 01", "...", "row 10",
            "PS> sample lines 1 2", "row 01", "...", "row 02",
            "PS> sample lines 1 3", "...", "row 03",
            "PS> sample lines 4 6", "row 04", "...")
    + "\n## Exit codes\n\n"
    + block("PS> sample fail 3 broken", "broken", "PS> $LASTEXITCODE", "3",
            "PS> sample fail 4 quiet", "quiet")
    + "\n## Streams\n\n"
    + block("PS> sample both out-text err-text", "out-text", "err-text",
            "PS> sample err only-err", "only-err",
            "PS> sample say only-out", "only-out",
            "PS> sample write quiet.txt nothing")
)
CRLF_TEXT = ("# Line ends\n\n## CRLF\n\n"
             + block("PS> sample crlf", "first", "second", "PS> sample say plain", "plain")
             ).replace("\n", "\r\n")

MISMATCH_TEXT = (
    "# Mismatches\n\n## Columns\n\n"
    + block("PS> sample table", TABLE_LINES[0], NARROW_ROW, *TABLE_LINES[2:])
    + "\n## Exit code\n\n"
    + block("PS> sample fail 2 broken", "broken", "PS> $LASTEXITCODE", "1")
    + "\n## Dots\n\n" + block("PS> sample lines 1 3", "row 01", "...", "row 09")
    + "\n## Not UTF-8\n\n" + block("PS> sample bytes", "café")
    + "\n## Spaces between words\n\n" + block('PS> sample say "a   b"', "a b")
    + "\n## Control\n\n" + block("PS> sample say fine", "fine")
    + "\n## Saved file\n\n" + block("PS> sample write saved.md actual text")
    + "\nThe file:\n\n" + block("expected text", info="markdown")
)
MISMATCH_RUN = run_file("[sections.\"Saved file\"]\n"
                        "files = [{ path = '<home>\\saved.md', block = 1 }]")

PATHS_RUN = run_file(
    "[paths]\n'C:\\Users\\Troy' = '<home>'\n"
    "'C:\\Users\\Troy\\OneDrive\\menu' = '<scratch>\\cloud\\menu'\n'D:\\Data' = '<home>\\data'",
    "[start]\nmkdir = ['<scratch>\\cloud\\menu', '<home>\\OneDrive\\menu', '<home>\\data']",
    "[sections.\"Paths\"]\nwrite = ["
    "{ file = '<scratch>\\cloud\\menu\\from-cloud.txt', text = \"cloud\\n\" }, "
    "{ file = '<home>\\OneDrive\\menu\\from-home.txt', text = \"home\\n\" }]")
CLOUD = "C:\\Users\\Troy\\OneDrive\\menu"
# Commands and the output each must show after the path map, on every system.
COMMON_PATHS = ((f"sample ls {CLOUD}", ["from-cloud.txt"]),
                ("sample where ..", ["<scratch>"]),
                ("sample where ../outside", ["<scratch>" + os.sep + "outside"]))
# On Windows the prototype's own spellings come back exactly.
WINDOWS_PATHS = (("sample where data", ["D:\\Data"]),
                 ("sample where .", ["C:\\Users\\Troy"]),
                 (f"sample where-in {CLOUD}", [CLOUD]),
                 ("sample where-posix data", ["D:/Data"]),
                 ("sample where-upper data", ["D:\\Data"]),
                 ("sample where-long data", ["D:\\Data"]),
                 ("sample where-short data", ["D:\\Data"]))
# "Subpaths" starts afresh: the default start makes the folders, and only "Paths" writes files.
WINDOWS_SUBPATHS = ((f"sample write-in {CLOUD}\\sub new.txt fresh", []),
                    (f"sample ls {CLOUD}", ["sub/", "sub/new.txt"]))
# Elsewhere a run path is spelled with "/", and the note gives the prototype path
# with "/" for such a spelling; either spelling of the prototype path is accepted.
POSIX_PATHS = (("sample where data", ("D:/Data", "D:\\Data")),
               (f"sample where-in {CLOUD}",
                ("C:/Users/Troy/OneDrive/menu", "C:\\Users\\Troy\\OneDrive\\menu")))


def paths_text() -> str:
    """The paths prototype for this system."""
    if WINDOWS:
        lines = [x for typed, real in COMMON_PATHS + WINDOWS_PATHS for x in (f"PS> {typed}", *real)]
        sub = [x for typed, real in WINDOWS_SUBPATHS for x in (f"PS> {typed}", *real)]
        return ("# Path map\n\n## Paths\n\n" + block(*lines)
                + "\n## Subpaths\n\n" + block(*sub))
    lines = [x for typed, real in COMMON_PATHS for x in (f"PS> {typed}", *real)]
    lines += [x for typed, real in POSIX_PATHS for x in (f"PS> {typed}", real[0])]
    return "# Path map\n\n## Paths\n\n" + block(*lines)


_RUNS: dict = {}


def runs() -> dict:
    """Builds the three projects and runs ``real-run --item F02`` on each, side by side, once."""
    if _RUNS:
        return _RUNS
    cases = {
        "match": {MATCH: MATCH_TEXT, run_file_path(MATCH): run_file(),
                  CRLF_PROTO: CRLF_TEXT, run_file_path(CRLF_PROTO): run_file()},
        "mismatch": {MISMATCH: MISMATCH_TEXT, run_file_path(MISMATCH): MISMATCH_RUN},
        "paths": {PATHS: paths_text(), run_file_path(PATHS): PATHS_RUN},
    }
    rows = {name: [(path.rsplit("/", 1)[1], "F02", path) for path in files
                   if path.endswith(".md")] for name, files in cases.items()}
    # A temporary folder with a long name, so the scratch folder has a short spelling too.
    long_temp = str(new_dir("a long folder name for the scratch "))
    temp = {"TEMP": long_temp, "TMP": long_temp, "TMPDIR": long_temp}

    def run(name):
        """Builds one project and runs the engine on it."""
        project = RealProject(history(project_files(rows=rows[name], files=cases[name])))
        return project.real_run("--item", "F02", env_extra=temp if name == "paths" else None)
    names = list(cases)
    _RUNS.update(zip(names, parallel(run, names)))
    return _RUNS


class MatchTests(RealRunCase):
    """What the five normalizations allow, and the streams (design 5.6)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.out = runs()["match"]

    def setUp(self):
        """Every test reads the clean run's report."""
        self.report = self.real_report(self.out, 0)

    def cmd(self, typed: str, path: str = MATCH) -> dict:
        """The one command entry with this typed line."""
        return command_of(self.report, path, typed)

    def test_every_command_matches(self):
        """Sixteen commands match, and nothing else happens."""
        self.assertEqual(self.report["counts"]["all"],
                         {"matches": 16, "mismatch": 0, "waits": 0, "not_run": 0})
        self.assertEqual(self.report["problems"], [])

    def test_chinese_columns_match_exactly(self):
        """The table, with two columns per Chinese character, matches as printed."""
        self.assert_command(self.cmd("sample table"), "matches", real=list(TABLE_LINES),
                            diff="")

    def test_line_ends_count_the_same(self):
        """CRLF from the program and in the prototype file match LF."""
        self.assert_command(self.cmd("sample crlf", CRLF_PROTO), "matches",
                            real=["first", "second"])
        self.assert_command(self.cmd("sample say plain", CRLF_PROTO), "matches", real=["plain"])

    def test_spaces_at_line_ends_and_blank_lines_at_the_end(self):
        """Spaces and tabs at line ends, and blank lines at the end, on both sides."""
        self.assert_command(self.cmd("sample trailing"), "matches", real=["x", "y"])
        self.assert_command(self.cmd("sample say spaced"), "matches", real=["spaced"])
        self.assert_command(self.cmd("sample say last"), "matches", expected=["last"])

    def test_dots_match_any_number_of_lines(self):
        """Planted bug "``...`` not handled": ``...`` stands for eight, zero, two, and two lines."""
        for typed in ("sample lines 1 10", "sample lines 1 2", "sample lines 1 3",
                      "sample lines 4 6"):
            with self.subTest(typed=typed):
                self.assert_command(self.cmd(typed), "matches")
        self.assertEqual(self.cmd("sample lines 1 10")["real"],
                         [f"row {n:02d}" for n in range(1, 11)])

    def test_exit_codes_are_recorded_and_compared_where_shown(self):
        """With ``$LASTEXITCODE`` the code is compared; without it, only recorded."""
        self.assert_command(self.cmd("sample fail 3 broken"), "matches", expected_exit=3, exit=3)
        self.assert_command(self.cmd("sample fail 4 quiet"), "matches", expected_exit=None,
                            exit=4)

    def test_standard_output_comes_before_standard_error(self):
        """A command that writes its error first still gives its output first, and a note."""
        entry = self.cmd("sample both out-text err-text")
        self.assert_command(entry, "matches", streams="both", real=["out-text", "err-text"])
        self.assertIn("order", entry["reason"].lower())

    def test_streams_of_each_command(self):
        """Standard error alone, standard output alone, and no output."""
        self.assert_command(self.cmd("sample err only-err"), "matches", streams="stderr",
                            real=["only-err"])
        self.assert_command(self.cmd("sample say only-out"), "matches", streams="stdout")
        self.assert_command(self.cmd("sample write quiet.txt nothing"), "matches",
                            streams="none", real=[])


class MismatchTests(RealRunCase):
    """What the comparison does not loosen, and the diffs (design 5.6, D104)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.out = runs()["mismatch"]

    def setUp(self):
        """Every test reads the failed run's report."""
        self.report = self.real_report(self.out, 1)

    def cmd(self, typed: str) -> dict:
        """The one command entry with this typed line."""
        return command_of(self.report, MISMATCH, typed)

    def test_counts_and_no_label(self):
        """Six mismatches and two matches; a run with a mismatch gives no label."""
        self.assertEqual(self.report["counts"]["all"],
                         {"matches": 2, "mismatch": 6, "waits": 0, "not_run": 0})
        self.assertIsNone(self.report["label"])
        self.assertEqual(self.report["problems"], [])

    def test_columns_must_match_exactly(self):
        """A row padded as if each Chinese character took one column is a mismatch, with a diff."""
        entry = self.cmd("sample table")
        self.assert_command(entry, "mismatch", real=list(TABLE_LINES))
        lines = diff_lines(entry)
        self.assertEqual([line.rstrip() for line in lines[:2]], ["--- prototype", "+++ real"])
        self.assertIn("-" + NARROW_ROW, lines)
        self.assertIn("+" + TABLE_LINES[1], lines)
        self.assertNotIn("-" + TABLE_LINES[0], lines)

    def test_wrong_exit_code_is_a_mismatch(self):
        """Planted bug "exit codes not compared": the output matches, the code does not."""
        self.assert_command(self.cmd("sample fail 2 broken"), "mismatch", expected_exit=1,
                            exit=2, real=["broken"])

    def test_dots_do_not_hide_a_missing_line(self):
        """``...`` matches lines, not a line the output never has."""
        self.assert_command(self.cmd("sample lines 1 3"), "mismatch")

    def test_text_that_is_not_utf8_is_a_mismatch(self):
        """Bytes that are not UTF-8 are a mismatch whose reason names UTF-8."""
        entry = self.cmd("sample bytes")
        self.assert_command(entry, "mismatch")
        self.assertIn("utf-8", entry["reason"].lower())

    def test_runs_of_spaces_are_not_one_space(self):
        """D104 rejected treating runs of spaces as one."""
        entry = self.cmd('sample say "a   b"')
        self.assert_command(entry, "mismatch", real=["a   b"])
        self.assertIn("-a b", diff_lines(entry))
        self.assertIn("+a   b", diff_lines(entry))

    def test_saved_file_is_compared(self):
        """A ``files`` entry whose file differs from its block is a mismatch, with a diff."""
        found = [c for c in commands_of(self.report, MISMATCH, "Saved file")
                 if c.get("kind") == "file"]
        self.assertEqual(len(found), 1)
        self.assert_command(found[0], "mismatch", expected=["expected text"],
                            real=["actual text"])
        self.assertIn("-expected text", diff_lines(found[0]))
        self.assertIn("+actual text", diff_lines(found[0]))

    def test_matching_commands_have_no_diff(self):
        """Commands that match have result ``matches`` and an empty diff."""
        for typed in ("sample say fine", "sample write saved.md actual text"):
            with self.subTest(typed=typed):
                self.assert_command(self.cmd(typed), "matches", diff="")


class PathMapTests(RealRunCase):
    """The path map in both directions, longest first, in every spelling (design 5.6 item 4)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.out = runs()["paths"]

    def setUp(self):
        """Every test reads the paths run's report; on Windows it must be clean."""
        if WINDOWS:
            self.report = self.real_report(self.out, 0)
        else:
            self.report = self.real_report(self.out, self.out.code)
            self.assertEqual(self.report["problems"], [])

    def cmd(self, typed: str, heading: str = "Paths") -> dict:
        """The one command entry with this typed line."""
        return command_of(self.report, PATHS, typed, heading)

    def test_command_paths_are_mapped_longest_first(self):
        """Planted bug "the path map applied one way only": a prototype folder in a command
        becomes its run folder, the longest prototype path first."""
        self.assert_command(self.cmd(f"sample ls {CLOUD}"), "matches", real=["from-cloud.txt"])

    def test_output_paths_are_mapped_back(self):
        """Planted bug "the path map applied one way only": run paths in the output become
        the prototype's paths, the longest run path first."""
        if WINDOWS:
            for typed, real in WINDOWS_PATHS:
                with self.subTest(typed=typed):
                    self.assert_command(self.cmd(typed), "matches", real=real)
        else:
            for typed, allowed in POSIX_PATHS:
                with self.subTest(typed=typed):
                    real = self.cmd(typed)["real"]
                    self.assertEqual(len(real), 1, real)
                    self.assertIn(real[0], allowed)

    def test_other_spellings_of_the_scratch_folder(self):
        """A path in the scratch folder that the map does not cover shows as ``<scratch>``."""
        for typed, real in COMMON_PATHS[1:]:
            with self.subTest(typed=typed):
                self.assert_command(self.cmd(typed), "matches", real=real)

    @unittest.skipUnless(WINDOWS, "Windows paths below a mapped folder")
    def test_paths_below_a_mapped_folder(self):
        """A path below a prototype folder in a command lands below its run folder."""
        for typed, real in WINDOWS_SUBPATHS:
            with self.subTest(typed=typed):
                self.assert_command(self.cmd(typed, "Subpaths"), "matches", real=real)


if __name__ == "__main__":
    unittest.main()
