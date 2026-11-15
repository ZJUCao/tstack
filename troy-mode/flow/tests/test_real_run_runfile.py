"""Run files (F12 design 4, 15.1; interface note section 5).

Three projects of F02, each run once, side by side:

- ``bad``: F01's prototypes, each with one mistake in its run file, a
  prototype without a run file, one without a transcript, a listed file
  that is missing, and F02's good prototype, which still runs;
- ``good``: every way a section starts (the default copy, ``mkdir``, and
  ``setup``; ``previous``; ``empty``; a table of its own; a single file),
  ``replace``, ``write``, ``delete``, a replaced command, ``skip`` marks,
  and ``files``. The copied folder has a file in the working tree that git
  ignores, which must not be copied;
- ``worktree``: a copied file whose working-tree text differs from HEAD's
  while ``git status`` stays clean (``git update-index --skip-worktree``).

Planted bug of design 15.2 caught here:

- "a copy from the working tree in place of HEAD":
  ``GoodRunFileTests.test_default_start_copies_only_what_head_tracks`` and
  ``WorktreeCopyTests.test_copy_has_heads_text``.
"""

import unittest

from flow_helpers import parallel
from realrun_helpers import (
    EXAMPLE_DATA, RealProject, RealRunCase, block, calls, command_of, commands_of, history,
    new_log, problems_of, project_files, prototype_of, run_file, run_file_path, section_of,
)

COPY_EXAMPLE = "[start]\ncopy = [{ from = \"tests/data/example\", to = '<home>\\data' }]"
SAY_HI = "## Say\n\n" + block("PS> sample say hi", "hi") + "\nA saved file:\n\n" + block(
    "hi", info="text")
# Prototype name: (run file, the one problem kind, the replace count or None).
BAD = {
    "top-key": (run_file("[colours]\nred = 1"), "run-file", None),
    "section-key": (run_file('[sections."Say"]\ncolour = "red"'), "run-file", None),
    "bad-toml": (run_file("[paths\n'C:\\Users\\Troy' = "), "run-file", None),
    "wrong-type": (run_file("[start]\nmkdir = '<home>\\data'"), "run-file", None),
    "run-path": (run_file("[start]\nmkdir = ['C:\\Temp\\data']"), "run-file", None),
    "leaves-scratch": (run_file("[start]\nmkdir = ['<home>\\..\\..\\outside']"), "run-file",
                       None),
    "unknown-section": (run_file('[sections."No such heading"]\nstart = "empty"'),
                        "unknown-section", None),
    "unknown-command": (run_file('[sections."Say"]\nskip = [{ typed = "sample say nothing", '
                                 'reason = "opens an editor" }]'), "unknown-command", None),
    "copy-ignored": (run_file("[start]\ncopy = [{ from = \"scratchdata\", to = '<home>\\data' }]"),
                     "copy-untracked", None),
    "copy-missing": (run_file("[start]\ncopy = [{ from = \"no/such/folder\", "
                              "to = '<home>\\data' }]"), "copy-untracked", None),
    "replace-zero": (run_file(COPY_EXAMPLE, "[sections.\"Say\"]\nreplace = [{ file = "
                              "'<home>\\data\\a.txt', text = \"absent\", with = \"x\" }]"),
                     "replace-count", 0),
    "replace-two": (run_file(COPY_EXAMPLE, "[sections.\"Say\"]\nreplace = [{ file = "
                             "'<home>\\data\\b\\c.txt', text = \"alpha\", with = \"x\" }]"),
                    "replace-count", 2),
    "unknown-later": (run_file('[sections."Say"]\nlater = [{ feature = "F09" }]'),
                      "unknown-later-feature", None),
    "missing-block": (run_file("[sections.\"Say\"]\nfiles = [{ path = '<home>\\x.md', "
                               "block = 2 }]"), "missing-block", None),
}
NO_RUN_FILE = "docs/prototypes/F01-no-run-file.md"
NO_TRANSCRIPT = "docs/prototypes/F01-example-data.md"
MISSING = "docs/prototypes/F01-missing.md"
GOOD = "docs/prototypes/F02-good.md"


def bad_path(name: str) -> str:
    """The prototype path of one bad run file."""
    return f"docs/prototypes/F01-{name}.md"


def bad_project() -> RealProject:
    """The project of bad run files, with an ignored ``scratchdata/`` folder in its tree."""
    files = dict(EXAMPLE_DATA)
    rows = []
    for name, (text, _, _) in BAD.items():
        files[bad_path(name)] = f"# {name}\n\n" + SAY_HI
        files[run_file_path(bad_path(name))] = text
        rows.append((name, "F01", bad_path(name)))
    files[NO_RUN_FILE] = "# No run file\n\n" + SAY_HI
    files[NO_TRANSCRIPT] = "# Example data\n\nSeven recipes and a week menu.\n\n" + block(
        "name = \"mapo tofu\"", info="toml")
    files[GOOD] = "# Good\n\n## Say\n\n" + block("PS> sample say good", "good")
    files[run_file_path(GOOD)] = run_file()
    rows += [("No run file", "F01", NO_RUN_FILE), ("Example data", "F01", f"`{NO_TRANSCRIPT}`"),
             ("Missing", "F01", MISSING), ("Good", "F02", GOOD)]
    project = RealProject(history(project_files(rows=rows, files=files, ignore="scratchdata/\n")))
    project.write("scratchdata/a.txt", "only in the working tree\n")
    return project


SETUP = "docs/prototypes/F02-setup.md"
LISTED = ["a.txt", "b/", "b/c.txt", "setup.txt", "shopping/"]
REASON_NEXT = "next is 2026-W47 on the prototype's date, 10 November 2026"
SETUP_TEXT = (
    "# Setup\n\n## Default start\n\n"
    + block("PS> sample ls menu", *LISTED, "PS> sample write menu/added.txt added")
    + "\n## Previous\n\n"
    + block("PS> sample ls menu", "a.txt", "added.txt", *LISTED[1:])
    + "\n## Fresh again\n\n" + block("PS> sample ls menu", *LISTED)
    + "\n## Empty\n\n" + block("PS> sample ls .")
    + "\n## Custom start\n\n" + block("PS> sample ls .", "other/", "other/x.txt")
    + "\n## Single file\n\n" + block("PS> Get-Content one.txt", "麻婆豆腐：郫县豆瓣酱 2 勺")
    + "\n## Edits\n\n"
    + block("PS> Get-Content menu/a.txt", "麻婆豆腐：豆瓣酱 2 勺",
            "PS> sample ls menu", "a.txt", "b/", "new.txt", "setup.txt", "shopping/",
            "PS> Get-Content menu/new.txt", "written")
    + "\n## Replaced command\n\n" + block("PS> sample say next week", "2026-W47")
    + "\n## Skipped\n\n"
    + block("PS> sample say before", "before", "PS> sample say skipped", "skipped",
            "PS> sample say after", "after")
    + "\n## Skipped section\n\n"
    + block("PS> sample say keys", "keys", "PS> sample say more keys", "more keys")
    + "\n## Saved\n\n" + block("PS> sample write menu/shopping/list.md eggs and tofu")
    + "\nThe saved list:\n\n" + block("eggs and tofu", info="markdown")
)
SETUP_RUN = run_file(
    "[start]\ncopy = [{ from = \"tests/data/example\", to = '<home>\\menu' }]\n"
    "mkdir = ['<home>\\menu\\shopping']\nsetup = [\"sample write menu/setup.txt from setup\"]",
    '[sections."Previous"]\nstart = "previous"',
    '[sections."Empty"]\nstart = "empty"',
    "[sections.\"Custom start\"]\nstart = { mkdir = ['<home>\\other'], "
    "setup = [\"sample write other/x.txt custom\"] }",
    "[sections.\"Single file\"]\nstart = { copy = [{ from = \"tests/data/example/a.txt\", "
    "to = '<home>\\one.txt' }] }",
    "[sections.\"Edits\"]\nreplace = [{ file = '<home>\\menu\\a.txt', text = \"郫县豆瓣酱\", "
    "with = \"豆瓣酱\" }]\nwrite = [{ file = '<home>\\menu\\new.txt', text = \"written\\n\" }]\n"
    "delete = ['<home>\\menu\\b\\c.txt']",
    '[sections."Replaced command"]\ncommands = [{ typed = "sample say next week", '
    f'run = "sample say 2026-W47", reason = "{REASON_NEXT}" }}]',
    '[sections."Skipped"]\nskip = [{ typed = "sample say skipped", reason = "opens an editor" }]',
    '[sections."Skipped section"]\nstart = "empty"\nskip = [{ reason = "reads keys" }]',
    "[sections.\"Saved\"]\nfiles = [{ path = '<home>\\menu\\shopping\\list.md', block = 1 }]",
)


def good_project() -> RealProject:
    """The project of good run files; the copied folder has an ignored file in its tree."""
    files = dict(EXAMPLE_DATA)
    files.update({SETUP: SETUP_TEXT, run_file_path(SETUP): SETUP_RUN})
    project = RealProject(history(project_files(rows=[("Setup", "F02", SETUP)], files=files,
                                                ignore="tests/data/example/*.local\n")))
    project.write("tests/data/example/ignored.local", "ignored by git\n")
    return project


COPY = "docs/prototypes/F02-copy.md"


def worktree_project() -> RealProject:
    """A project whose copied ``a.txt`` differs in the working tree, hidden from git status."""
    files = dict(EXAMPLE_DATA)
    files[COPY] = "# Copy\n\n## Copied file\n\n" + block("PS> Get-Content data/a.txt",
                                                         "麻婆豆腐：郫县豆瓣酱 2 勺")
    files[run_file_path(COPY)] = run_file(COPY_EXAMPLE)
    project = RealProject(history(project_files(rows=[("Copy", "F02", COPY)], files=files)))
    project.git("update-index", "--skip-worktree", "tests/data/example/a.txt")
    project.write("tests/data/example/a.txt", "changed in the working tree only\n")
    return project


_RUNS: dict = {}


def runs() -> dict:
    """Builds the three projects and runs ``real-run --item F02`` on each, side by side, once.

    Returns:
        Each name mapped to ``(project, outcome, call log)``.
    """
    if _RUNS:
        return _RUNS
    builders = {"bad": bad_project, "good": good_project, "worktree": worktree_project}

    def run(name):
        """Builds one project and runs the engine with a call log."""
        project = builders[name]()
        log = new_log(name)
        return project, project.real_run("--item", "F02", log=log), log
    names = list(builders)
    _RUNS.update(zip(names, parallel(run, names)))
    return _RUNS


class BadRunFileTests(RealRunCase):
    """Each mistake in a run file is a problem, and only its prototype stops (note section 5)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.project, cls.out, cls.log = runs()["bad"]

    def setUp(self):
        """The run has problems, so it exits 1."""
        self.report = self.real_report(self.out, 1)

    def test_each_mistake_is_its_problem(self):
        """Unknown keys, bad TOML, a wrong type, bad run paths, an unknown section or command,
        a copy of nothing git tracks, a replace text found 0 or 2 times, an unknown later
        feature, and a missing block."""
        for name, (_, kind, _) in BAD.items():
            with self.subTest(prototype=name):
                found = problems_of(self.report, prototype=bad_path(name))
                self.assertEqual(sorted({p.get("kind") for p in found}), [kind], found)
                self.assertTrue(all(str(p.get("message") or "").strip() for p in found), found)

    def test_replace_count_holds_the_number_found(self):
        """``count`` is 0 for a text not found and 2 for a text found twice."""
        for name in ("replace-zero", "replace-two"):
            with self.subTest(prototype=name):
                found = problems_of(self.report, "replace-count", bad_path(name))
                self.assertEqual([p.get("count") for p in found], [BAD[name][2]])

    def test_commands_of_a_bad_run_file_do_not_run(self):
        """Every command of a prototype with a bad run file is ``not run``."""
        for name in BAD:
            with self.subTest(prototype=name):
                entries = commands_of(self.report, bad_path(name))
                self.assertNotEqual(entries, [])
                for entry in entries:
                    self.assert_not_run(entry)

    def test_prototype_without_a_run_file(self):
        """A transcript without a run file is a problem, and its commands do not run."""
        self.assertEqual(len(problems_of(self.report, "no-run-file", NO_RUN_FILE)), 1,
                         self.report["problems"])
        entry = prototype_of(self.report, NO_RUN_FILE)
        self.assertIsNone(entry["run_file"])
        self.assert_not_run(command_of(self.report, NO_RUN_FILE, "sample say hi"))

    def test_prototype_without_a_transcript(self):
        """``example-data.md`` has no transcript: listed, no run file needed, no problem."""
        entry = prototype_of(self.report, NO_TRANSCRIPT)
        self.assertEqual((entry["transcript"], entry["run_file"]), (False, None))
        self.assertEqual(problems_of(self.report, prototype=NO_TRANSCRIPT), [])

    def test_listed_prototype_missing_at_head(self):
        """A row whose file is not at HEAD is a problem that names the file."""
        found = problems_of(self.report, "missing-prototype")
        self.assertEqual(len(found), 1, self.report["problems"])
        self.assertIn(MISSING, f"{found[0].get('prototype')} {found[0].get('message')}")

    def test_other_prototypes_still_run(self):
        """F02's good prototype runs and matches; it is the only command that ran."""
        self.assert_command(command_of(self.report, GOOD, "sample say good"), "matches")
        self.assertEqual(self.report["counts"]["all"]["matches"], 1)
        self.assertEqual([call["argv"] for call in calls(self.log)], [["say", "good"]])


class GoodRunFileTests(RealRunCase):
    """How sections start and what a run file changes (design 4.2, 4.3; note section 5)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.project, cls.out, cls.log = runs()["good"]

    def setUp(self):
        """Every command that runs matches."""
        self.report = self.real_report(self.out, 0)

    def cmd(self, typed: str, heading: str) -> dict:
        """The one command entry of a section with this typed line."""
        return command_of(self.report, SETUP, typed, heading)

    def test_counts(self):
        """Fourteen commands and the ``files`` check match; the three skipped did not run."""
        self.assertEqual(self.report["counts"]["all"],
                         {"matches": 15, "mismatch": 0, "waits": 0, "not_run": 3})

    def test_default_start_copies_only_what_head_tracks(self):
        """Planted bug "a copy from the working tree in place of HEAD": the copy holds the
        tracked files, the ``mkdir`` folder, and the setup's file, not the ignored one."""
        self.assertEqual(section_of(self.report, SETUP, "Default start")["start"], "default")
        self.assert_command(self.cmd("sample ls menu", "Default start"), "matches", real=LISTED)

    def test_previous_goes_on_from_the_previous_section(self):
        """``previous`` keeps the file the previous section wrote."""
        self.assertEqual(section_of(self.report, SETUP, "Previous")["start"], "previous")
        self.assert_command(self.cmd("sample ls menu", "Previous"), "matches",
                            real=["a.txt", "added.txt", *LISTED[1:]])

    def test_other_sections_start_afresh(self):
        """A later section with the default start does not see that file."""
        self.assert_command(self.cmd("sample ls menu", "Fresh again"), "matches", real=LISTED)

    def test_empty_start_has_no_files(self):
        """``empty``: the home folder is empty, with no AppData folders made."""
        self.assertEqual(section_of(self.report, SETUP, "Empty")["start"], "empty")
        self.assert_command(self.cmd("sample ls .", "Empty"), "matches", real=[])

    def test_a_start_table_replaces_the_default(self):
        """A section's own start table: its folder and setup, and no copy."""
        self.assertEqual(section_of(self.report, SETUP, "Custom start")["start"], "custom")
        self.assert_command(self.cmd("sample ls .", "Custom start"), "matches",
                            real=["other/", "other/x.txt"])

    def test_copy_of_a_single_tracked_file(self):
        """``from`` may name one tracked file."""
        self.assert_command(self.cmd("Get-Content one.txt", "Single file"), "matches")

    def test_replace_write_and_delete(self):
        """The Chinese text is replaced, a file written, and one deleted, after the start."""
        self.assert_command(self.cmd("Get-Content menu/a.txt", "Edits"), "matches",
                            real=["麻婆豆腐：豆瓣酱 2 勺"])
        self.assert_command(self.cmd("sample ls menu", "Edits"), "matches")
        self.assert_command(self.cmd("Get-Content menu/new.txt", "Edits"), "matches",
                            real=["written"])

    def test_replaced_command_runs_the_replacement(self):
        """``commands``: the typed line stays, the replacement runs, and the reason is kept."""
        self.assert_command(self.cmd("sample say next week", "Replaced command"), "matches",
                            run="sample say 2026-W47", replaced=REASON_NEXT, real=["2026-W47"])

    def test_skip_marks(self):
        """A skip of one command and of a whole section: ``not run`` with the mark's reason."""
        self.assert_command(self.cmd("sample say before", "Skipped"), "matches")
        self.assert_command(self.cmd("sample say after", "Skipped"), "matches")
        for typed, heading, reason in (("sample say skipped", "Skipped", "opens an editor"),
                                       ("sample say keys", "Skipped section", "reads keys"),
                                       ("sample say more keys", "Skipped section", "reads keys")):
            with self.subTest(typed=typed):
                entry = self.cmd(typed, heading)
                self.assert_not_run(entry)
                self.assertIn(reason, entry["reason"])
        ran = [call["argv"] for call in calls(self.log)]
        for argv in (["say", "skipped"], ["say", "keys"], ["say", "more", "keys"]):
            self.assertNotIn(argv, ran)

    def test_setup_runs_before_each_default_section(self):
        """The setup command ran for each of the six sections that start by default."""
        ran = [call["argv"] for call in calls(self.log)]
        setups = ran.count(["write", "menu/setup.txt", "from", "setup"])
        self.assertEqual(setups, 6, ran)
        self.assertEqual(ran.count(["write", "other/x.txt", "custom"]), 1, ran)
        typed = [c["typed"] for c in commands_of(self.report, SETUP)]
        self.assertNotIn("sample write menu/setup.txt from setup", typed)

    def test_saved_file_is_compared(self):
        """The ``files`` entry compares the saved list with block 1."""
        found = [c for c in commands_of(self.report, SETUP, "Saved") if c.get("kind") == "file"]
        self.assertEqual(len(found), 1)
        self.assert_command(found[0], "matches", real=["eggs and tofu"])


class WorktreeCopyTests(RealRunCase):
    """The copy comes from HEAD through git, not from the working tree (design 4.3)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.project, cls.out, cls.log = runs()["worktree"]

    def test_tree_looks_clean(self):
        """The changed file is hidden from ``git status``, so the tree counts as clean."""
        self.assertEqual(self.project.status_lines(), [])

    def test_copy_has_heads_text(self):
        """Planted bug "a copy from the working tree in place of HEAD": HEAD's text is copied."""
        report = self.real_report(self.out, 0)
        self.assert_command(command_of(report, COPY, "Get-Content data/a.txt"), "matches",
                            real=["麻婆豆腐：郫县豆瓣酱 2 勺"])


if __name__ == "__main__":
    unittest.main()
