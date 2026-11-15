"""Cases added after the planted bugs of F12 design 15.2 that the first tests missed.

Three projects of F02, each run once, side by side:

- ``more``: ``Get-Content`` of a prototype path that the path map covers and
  of one it does not, and a ``files`` check of a section's second block;
- ``first``: a run file whose first section starts from the previous one;
- ``slow``: a command that runs past the time limit of 60 seconds (design 5.4);
- ``changes``: three runs of one prototype, first without a run file, then
  with one, then with a changed one, as PR 6 runs it (design 3, 8).

Planted bugs caught here:

- "the Get-Content path not mapped": ``MoreTests.test_get_content_of_a_mapped_path``;
- "the first section may start from the previous one":
  ``FirstSectionTests.test_first_section_cannot_start_from_the_previous_one``;
- "files compared with the first block": ``MoreTests.test_files_names_the_second_block``;
- "the time limit not a mismatch": ``SlowTests.test_time_limit``.

The trial on ``ZJUCao/troy-mode-trial`` found that a run file written after
the first run, which only showed which run files were missing, was listed
as changed after the first run; ``ChangesTests`` checks the fix.
"""

import time
import unittest

from flow_helpers import parallel
from realrun_helpers import (
    RealProject, RealRunCase, block, command_of, history, markdown_part, problems_of,
    project_files, prototype_of, run_file, run_file_path,
)

MORE = "docs/prototypes/F02-more.md"
MORE_TEXT = (
    "# Prototype: more\n\n## Mapped path\n\n"
    + block('PS> sample write "notes.txt" first line',
            "PS> Get-Content C:\\Users\\Troy\\notes.txt", "first line",
            "PS> Get-Content D:\\Secret\\notes.txt", "first line")
    + "\n## Two blocks\n\n"
    + block("PS> sample write out/saved.md second text")
    + "\nAn example that is not the saved file:\n\n" + block("first text", info="markdown")
    + "\nThe saved file:\n\n" + block("second text", info="markdown")
)
MORE_RUN = run_file("[paths]\n'C:\\Users\\Troy' = '<home>'",
                    "[sections.\"Two blocks\"]\nfiles = [{ path = '<home>\\out\\saved.md', "
                    "block = 2 }]")
FIRST = "docs/prototypes/F02-first.md"
FIRST_TEXT = ("# Prototype: first\n\n## One\n\n" + block("PS> sample say one", "one")
              + "\n## Two\n\n" + block("PS> sample say two", "two"))
FIRST_RUN = run_file('[sections."One"]\nstart = "previous"')
SLOW = "docs/prototypes/F02-slow.md"
SLOW_TEXT = ("# Prototype: slow\n\n## Slow\n\n"
             + block("PS> sample sleep 90", "started", "woke up")
             + "\n## After\n\n" + block("PS> sample say after", "after"))

CHANGE = "docs/prototypes/F02-change.md"
CHANGE_TEXT = "# Prototype: change\n\n## Say\n\n" + block("PS> sample say hi", "hi")

_RUNS: dict = {}


def change_runs() -> list:
    """Runs one project three times: no run file, a run file, then a changed run file."""
    rows = [("change", "F02", CHANGE)]
    project = RealProject(history(project_files(rows=rows, files={CHANGE: CHANGE_TEXT})))
    outs = [project.real_run("--item", "F02")]
    project.commit("Add the run file", {run_file_path(CHANGE): run_file()})
    outs.append(project.real_run("--item", "F02"))
    project.commit("Change the run file", {run_file_path(CHANGE): run_file("# changed")})
    outs.append(project.real_run("--item", "F02"))
    return outs


def runs() -> dict:
    """Builds the three projects and runs ``real-run --item F02`` on each, side by side, once.

    Returns:
        Each name mapped to ``(outcome, seconds the run took)``.
    """
    if _RUNS:
        return _RUNS
    cases = {"more": {MORE: MORE_TEXT, run_file_path(MORE): MORE_RUN},
             "first": {FIRST: FIRST_TEXT, run_file_path(FIRST): FIRST_RUN},
             "slow": {SLOW: SLOW_TEXT, run_file_path(SLOW): run_file()}}

    def run(name):
        """Builds one project and runs the engine, timing it."""
        if name == "changes":
            return change_runs(), 0.0
        files = cases[name]
        rows = [(path.rsplit("/", 1)[1], "F02", path) for path in files if path.endswith(".md")]
        project = RealProject(history(project_files(rows=rows, files=files)))
        start = time.monotonic()
        out = project.real_run("--item", "F02")
        return out, time.monotonic() - start
    names = list(cases) + ["changes"]
    _RUNS.update(zip(names, parallel(run, names)))
    return _RUNS


class MoreTests(RealRunCase):
    """Get-Content through the path map (design 5.3, 5.5) and a section's second block (4.2)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.out = runs()["more"][0]

    def setUp(self):
        """The unmapped path is a problem, so the run exits 1."""
        self.report = self.real_report(self.out, 1)

    def test_get_content_of_a_mapped_path(self):
        """``C:\\Users\\Troy\\notes.txt`` is ``<home>\\notes.txt`` in the run, which the
        program wrote, so the file prints and matches."""
        self.assert_command(command_of(self.report, MORE, "Get-Content C:\\Users\\Troy\\notes.txt"),
                            "matches", real=["first line"])

    def test_get_content_of_an_unmapped_path_is_refused(self):
        """``D:\\Secret`` is outside the path map: not read, and an ``unmapped-path`` problem."""
        entry = command_of(self.report, MORE, "Get-Content D:\\Secret\\notes.txt")
        self.assert_not_run(entry)
        self.assertEqual(len(problems_of(self.report, "unmapped-path")), 1, self.report["problems"])

    def test_files_names_the_second_block(self):
        """``block = 2`` compares the file with the section's second block that is not a
        transcript, not the first."""
        entries = [c for s in prototype_of(self.report, MORE)["sections"]
                   if s["heading"] == "Two blocks" for c in s["commands"] if c["kind"] == "file"]
        self.assertEqual(len(entries), 1, entries)
        self.assert_command(entries[0], "matches", expected=["second text"],
                            real=["second text"])


class FirstSectionTests(RealRunCase):
    """The first section has no previous one to go on from (note section 5)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.out = runs()["first"][0]

    def test_first_section_cannot_start_from_the_previous_one(self):
        """A ``run-file`` problem, and none of the prototype's commands runs."""
        report = self.real_report(self.out, 1)
        self.assertEqual([p["kind"] for p in report["problems"]], ["run-file"])
        for typed in ("sample say one", "sample say two"):
            with self.subTest(typed=typed):
                self.assert_not_run(command_of(report, FIRST, typed))


class SlowTests(RealRunCase):
    """A command over the time limit of 60 seconds (design 5.4; note sections 6 and 7)."""

    @classmethod
    def setUpClass(cls):
        """Runs the three projects once."""
        cls.out, cls.seconds = runs()["slow"]

    def test_time_limit(self):
        """The command is stopped after 60 seconds, well before its 90 seconds of sleep, and is
        a mismatch whose reason names the time limit; the next section still runs."""
        report = self.real_report(self.out, 1)
        entry = command_of(report, SLOW, "sample sleep 90")
        self.assert_command(entry, "mismatch", exit=None)
        self.assertIn("60 seconds", entry["reason"])
        self.assertNotIn("woke up", entry["real"])
        self.assertLess(self.seconds, 85)
        self.assert_command(command_of(report, SLOW, "sample say after"), "matches")


class ChangesTests(RealRunCase):
    """The Changes part lists run files changed after the first run that had them (design 8)."""

    @classmethod
    def setUpClass(cls):
        """Runs the projects once."""
        cls.outs = runs()["changes"][0]

    def changes(self, index: int, code: int) -> str:
        """The Changes part of one run's description."""
        return markdown_part(self.real_report(self.outs[index], code)["description"], "Changes")

    def test_first_run(self):
        """The first run, without a run file, says that it is the first run."""
        self.assertIn("Run files changed after the first run: this is the first run.",
                      self.changes(0, 1))

    def test_a_new_run_file_is_not_a_change(self):
        """A run file that the first run did not have is new, not changed after the first run."""
        self.assertIn("Run files changed after the first run: None.", self.changes(1, 0))

    def test_a_changed_run_file_is_listed(self):
        """The run file changed after the run that first had it, so it is listed."""
        self.assertIn(f"Run files changed after the first run: `{run_file_path(CHANGE)}`.",
                      self.changes(2, 0))


if __name__ == "__main__":
    unittest.main()
