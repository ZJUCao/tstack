"""The report, its files, the evidence, and the exit codes (F12 design 5.7, 8, 15.1; note 1, 8).

A project of F02 runs twice in a row: first with a fake gh that lists open
bug issues, then with ``--keep`` and a gh that fails. A second project has
a command whose output passes the description's limit, so it moves into
the report's comments. Bad options exit 2.
"""

import json
import platform
import sys
import tempfile
import unittest
from pathlib import Path

from flow_helpers import (
    CHECKS_SOURCE, Fakes, F02, issue, new_dir, parallel, run_engine, same_path,
)
from realrun_helpers import (
    DESCRIPTION_PARTS, HOME_MAP, PIPES_SENTENCE, TABLE_LINES, RealProject, RealRunCase, block,
    command_of, default_env, history, markdown_part, project_files, remove_tree, run_file,
    run_file_path,
)

if str(CHECKS_SOURCE) not in sys.path:
    sys.path.insert(0, str(CHECKS_SOURCE))
from troycheck.attribution import find_attribution  # noqa: E402  (after the path setup)

REPORT = "docs/prototypes/F02-report.md"
OLD = "docs/prototypes/F01-old.md"
REASON = "next is 2026-W47 on the prototype's date, 10 November 2026"
TYPED = ("sample say hello", "sample table", "sample fail 3 broken", "sample where ..",
         "sample say next week")
REPORT_TEXT = (
    "# Report\n\n## Say\n\n" + block("PS> sample say hello", "hello", "PS> sample table",
                                     *TABLE_LINES)
    + "\n## Exit\n\n" + block("PS> sample fail 3 broken", "broken", "PS> $LASTEXITCODE", "3")
    + "\n## Where\n\n" + block("PS> sample where ..", "<scratch>")
    + "\n## Week\n\n" + block("PS> sample say next week", "2026-W47")
)
REPORT_RUN = run_file(HOME_MAP, '[sections."Week"]\ncommands = [{ typed = "sample say next week", '
                                f'run = "sample say 2026-W47", reason = "{REASON}" }}]')
FILES = {REPORT: REPORT_TEXT, run_file_path(REPORT): REPORT_RUN,
         OLD: "# Earlier feature\n\n## Old\n\n" + block("PS> sample say old", "old"),
         run_file_path(OLD): run_file()}
ROWS = [("Report", "F02", REPORT), ("Old", "F01", OLD)]
ISSUES = [issue(7, "Real run of F02: wrong count"), issue(8, "Real run of F01: old output"),
          issue(9, "Fix the table"), issue(10, "Real run of F020: other feature")]

LONG = "docs/prototypes/F02-long.md"
LONG_LINES = 2000


def long_line(number: int) -> str:
    """One line of ``sample long``."""
    return "long output line %05d %s" % (number, "." * 24)


LONG_TEXT = "# Long output\n\n## Long\n\n" + block(f"PS> sample long {LONG_LINES}", long_line(1),
                                                   "...", long_line(LONG_LINES))

_RUNS: dict = {}


def runs() -> dict:
    """Builds both projects and runs them once: the report project twice in a row.

    Returns:
        ``report`` (the clone), ``first`` and ``second`` (its outcomes),
        ``fakes`` (the first run's), and ``long`` (the long project's outcome).
    """
    if _RUNS:
        return _RUNS

    def report_runs():
        """The report project's two runs, in order."""
        project = RealProject(history(project_files(rows=ROWS, files=FILES)))
        fakes = Fakes(issues=ISSUES)
        first = project.real_run("--item", "F02", fakes=fakes)
        second = project.real_run("--item", "F02", "--keep")
        return {"report": project, "first": first, "second": second, "fakes": fakes}

    def long_run():
        """The long project's run."""
        files = {LONG: LONG_TEXT, run_file_path(LONG): run_file()}
        project = RealProject(history(project_files(rows=[("Long", "F02", LONG)], files=files)))
        return {"long": project.real_run("--item", "F02")}
    for found in parallel(lambda job: job(), [report_runs, long_run]):
        _RUNS.update(found)
    return _RUNS


class ReportTests(RealRunCase):
    """The report's fields and files (design 5.7; note section 8)."""

    @classmethod
    def setUpClass(cls):
        """Runs both projects once."""
        found = runs()
        cls.project, cls.fakes = found["report"], found["fakes"]
        cls.first, cls.second = found["first"], found["second"]

    @classmethod
    def tearDownClass(cls):
        """Deletes the scratch folder the second run kept."""
        report = cls.second.report or {}
        remove_tree(report.get("scratch"))

    def setUp(self):
        """Both runs are clean."""
        self.report = self.real_report(self.first, 0)
        self.kept = self.real_report(self.second, 0)

    def test_item_commit_and_base(self):
        """The item, ``all``, HEAD's full ID, and ``origin/main``'s full ID."""
        self.assertEqual((self.report["item"], self.report["all"]), (F02.id, False))
        self.assertEqual(self.report["commit"], self.project.head())
        self.assertEqual(self.report["base"], self.project.git("rev-parse", "origin/main").strip())

    def test_program_system_and_date(self):
        """The environment's prefix and Python version; the system and the date are named."""
        program = self.report["program"]
        self.assertTrue(same_path(program["prefix"], default_env().prefix), program)
        self.assertEqual(program["python"], platform.python_version())
        for key in ("system", "date"):
            with self.subTest(key=key):
                self.assertIsInstance(self.report[key], str)
                self.assertNotEqual(self.report[key].strip(), "")

    def test_counts_label_and_commands(self):
        """Six commands match, five of them F02's own; F02 ran for real."""
        self.assertEqual(self.report["counts"]["all"],
                         {"matches": 6, "mismatch": 0, "waits": 0, "not_run": 0})
        self.assertEqual(self.report["counts"]["own"],
                         {"matches": 5, "mismatch": 0, "waits": 0, "not_run": 0})
        self.assertEqual(self.report["label"], "Ran for real on Troy's PC")
        entry = command_of(self.report, REPORT, "sample fail 3 broken")
        self.assert_command(entry, "matches", expected=["broken"], real=["broken"],
                            expected_exit=3, exit=3, own=True, streams="stderr")

    def test_report_files_are_numbered_in_the_git_folder(self):
        """``real-run-F02-1`` then ``-2``, JSON and Markdown, in ``<git dir>/troy-mode/flow``."""
        folder = self.project.report_folder()
        for report, number in ((self.report, 1), (self.kept, 2)):
            with self.subTest(run=number):
                self.assertTrue(same_path(report["files"]["json"],
                                          folder / f"real-run-F02-{number}.json"), report["files"])
                self.assertTrue(same_path(report["files"]["md"],
                                          folder / f"real-run-F02-{number}.md"), report["files"])
                self.assertTrue(Path(report["files"]["md"]).is_file())
                self.assertIn("Real run", Path(report["files"]["md"]).read_text(encoding="utf-8"))

    def test_json_file_is_the_printed_report(self):
        """The JSON file holds the report that ``--json`` printed."""
        written = json.loads(Path(self.report["files"]["json"]).read_text(encoding="utf-8"))
        for key in ("commit", "counts", "prototypes", "label", "description", "open_bugs"):
            with self.subTest(key=key):
                self.assertEqual(written.get(key), self.report[key])

    def test_open_bugs_of_the_item(self):
        """Open bug issues titled ``Real run of F02:``; not F01's, F020's, or another title."""
        self.assertEqual([bug["number"] for bug in self.report["open_bugs"]], [7])
        self.assertEqual(self.report["open_bugs"][0]["title"], "Real run of F02: wrong count")
        calls = self.fakes.gh_argvs()
        self.assertIn(["issue", "list"], [argv[:2] for argv in calls])
        self.assertTrue(all(len(argv) > 1 and argv[1] in ("list", "view") for argv in calls),
                        f"real-run only reads GitHub: {calls}")

    def test_open_bugs_null_when_gh_fails(self):
        """A gh that fails gives ``open_bugs`` null and a note; the run goes on."""
        self.assertIsNone(self.kept["open_bugs"])
        self.assertNotEqual(self.kept["notes"], [])

    def test_scratch_kept_only_with_keep(self):
        """Without ``--keep`` the scratch folder is gone (null); with it, it stays."""
        self.assertIsNone(self.report["scratch"])
        self.assertIsInstance(self.kept["scratch"], str)
        self.assertTrue((Path(self.kept["scratch"]) / "home").is_dir(), self.kept["scratch"])

    def test_comments_empty_for_a_short_run(self):
        """A short run puts everything in the description."""
        self.assertEqual(self.report["comments"], [])


class DescriptionTests(RealRunCase):
    """The "Real run" section for the PR description (design 8; note section 8)."""

    @classmethod
    def setUpClass(cls):
        """Runs both projects once."""
        found = runs()
        cls.project, cls.first, cls.second = found["report"], found["first"], found["second"]

    def setUp(self):
        """Reads the first run's description."""
        self.report = self.real_report(self.first, 0)
        self.text = self.report["description"]

    def part(self, title: str) -> str:
        """One ``###`` part of the description."""
        found = markdown_part(self.text, title)
        self.assertNotEqual(found.strip(), "", f"no part {title!r}:\n{self.text}")
        return found

    def test_heading_and_parts_in_order(self):
        """``## Real run`` first, then the seven ``###`` parts in order."""
        self.assertEqual(self.text.split("\n")[0], "## Real run")
        parts = [line[4:].strip() for line in self.text.split("\n") if line.startswith("### ")]
        self.assertEqual(parts, list(DESCRIPTION_PARTS))

    def test_header_names_the_commit_and_the_pipes(self):
        """The commit's short ID and the sentence about pipes."""
        self.assertIn(self.project.head()[:7], self.text)
        self.assertIn(PIPES_SENTENCE, self.text)

    def test_no_local_path(self):
        """No spelling of the clone, the environment, Python, or the scratch folder."""
        kept = self.real_report(self.second, 0)
        paths = [self.project.root, default_env().prefix, Path(sys.executable).parent,
                 tempfile.gettempdir(), kept["scratch"]]
        self.assert_no_local_path(self.text, *paths)
        self.assert_no_local_path(kept["description"], *paths)

    def test_passes_the_strict_attribution_check(self):
        """The description is posted as it is, so it passes R19 in strict mode."""
        self.assertEqual(find_attribution(self.text, "strict"), [])
        self.assertNotIn("claude", self.text.lower())
        self.assertNotIn("anthropic", self.text.lower())

    def test_commands_part_has_a_row_per_command(self):
        """Every command as typed appears in the Commands part."""
        commands = self.part("Commands")
        for typed in TYPED + ("sample say old",):
            with self.subTest(typed=typed):
                self.assertIn(typed, commands)

    def test_result_part_has_the_counts(self):
        """The Result part gives the number of matching commands."""
        self.assertRegex(self.part("Result"), r"\b6\b")

    def test_adaptations_list_the_path_map_and_replacements(self):
        """The path map's prototype folder and the replaced command's reason."""
        adaptations = self.part("Adaptations")
        self.assertIn("C:\\Users\\Troy", adaptations)
        self.assertIn(REASON, adaptations)
        self.assertIn("sample say 2026-W47", adaptations)

    def test_not_proven_part(self):
        """What the pipes cannot prove is listed."""
        self.part("Not proven")

    def test_real_output_in_transcript_form(self):
        """Folded per prototype, with ``PS> `` lines, the output after the path map, and
        ``PS> $LASTEXITCODE`` with the real code."""
        output = self.part("Real output")
        self.assertIn("<details>", output)
        lines = output.split("\n")
        self.assertIn("PS> sample say hello", lines)
        self.assertIn("hello", lines)
        self.assertIn(TABLE_LINES[1], lines)
        self.assertIn("<scratch>", lines)
        start = lines.index("PS> sample fail 3 broken")
        rest = lines[start + 1:]
        self.assertIn("broken", rest)
        codes = [rest[i + 1] for i, line in enumerate(rest[:-1]) if line == "PS> $LASTEXITCODE"]
        self.assertTrue(codes, output)
        self.assertEqual(codes[0], "3", output)


class LongOutputTests(RealRunCase):
    """A description over 60,000 characters moves the real output into comments (design 8)."""

    @classmethod
    def setUpClass(cls):
        """Runs both projects once."""
        cls.out = runs()["long"]

    def setUp(self):
        """The long output matches through ``...``."""
        self.report = self.real_report(self.out, 0)

    def test_output_matches_through_dots(self):
        """``sample long 2000`` matches its first line, ``...``, and its last line."""
        entry = command_of(self.report, LONG, f"sample long {LONG_LINES}")
        self.assert_command(entry, "matches")
        self.assertEqual(len(entry["real"]), LONG_LINES)

    def test_real_output_moves_into_numbered_comments(self):
        """Each comment starts ``Real run output, part <n>`` and holds at most 60,000 characters."""
        comments = self.report["comments"]
        self.assertGreaterEqual(len(comments), 2)
        for number, comment in enumerate(comments, start=1):
            with self.subTest(part=number):
                self.assertTrue(comment.startswith(f"Real run output, part {number}"),
                                comment[:200])
                self.assertLessEqual(len(comment), 60000)
                self.assertEqual(find_attribution(comment, "strict"), [])
        joined = "\n".join(comments)
        for number in (1, LONG_LINES // 2, LONG_LINES):
            with self.subTest(line=number):
                self.assertIn(long_line(number), joined)

    def test_description_names_the_comments_and_stays_short(self):
        """The description stays within 60,000 characters and points at the comments."""
        text = self.report["description"]
        self.assertLessEqual(len(text), 60000)
        self.assertIn("Real run output, part 1", markdown_part(text, "Real output"))
        self.assertNotIn(long_line(LONG_LINES // 2), text)


class OptionTests(RealRunCase):
    """Options the engine cannot use exit 2 (note sections 1 and 8)."""

    def test_bad_options_exit_two(self):
        """Neither or both of ``--item`` and ``--all``, an item that is no feature ID, and a
        folder that is no repository."""
        project = runs()["report"]
        cases = {"neither": (), "both": ("--item", "F02", "--all"), "short id": ("--item", "F2"),
                 "no letter": ("--item", "02"), "a bug": ("--item", "B12")}
        names = list(cases)
        outs = parallel(lambda name: project.real_run(*cases[name]), names)
        for name, out in zip(names, outs):
            with self.subTest(case=name):
                self.assert_exit(out, 2)
        plain = new_dir("plain")
        out = run_engine(["real-run", "--item", "F02", "--repo", plain, "--json"], plain,
                         env_extra=default_env().env_extra())
        self.assert_exit(out, 2)


if __name__ == "__main__":
    unittest.main()
