"""Which prototypes run, own commands, ``later`` marks, and the label (F12 design 5.2, 6, 9).

Seven projects, each run once, side by side. F01 is accepted, F02 is at
stage 6, and F03 is not started, unless a case says otherwise. Prototypes
that must not run hold a command whose prototype output is wrong, so
running them would fail the run, and the sample program's call log shows
what ran.

Planted bugs of design 15.2 caught here:

- "the label given with a skipped command of the feature's own":
  ``LabelTests.test_skipped_own_command_gives_passes_tests``.
- "a ``later`` mark that still counts once its feature is accepted":
  ``TableTests.test_mark_for_the_item_runs_and_is_own`` (the item) and
  ``AllTests.test_mark_for_an_accepted_feature_runs`` (an accepted feature).
"""

import unittest

from flow_helpers import F01, F02, base_step, parallel, stage_step, stages
from realrun_helpers import (
    LABEL_RAN, LABEL_TESTS, RealProject, RealRunCase, block, calls, command_of, history,
    new_log, problems_of, project_files, prototype_of, run_file, run_file_path,
)

ZERO = {"matches": 0, "mismatch": 0, "waits": 0, "not_run": 0}


def says(*words: str) -> list:
    """Prompt and output lines of ``sample say <word>`` for each word."""
    return [x for word in words for x in (f"PS> sample say {word}", word)]


def wrong(word: str) -> list:
    """A command whose prototype output differs from what the program prints."""
    return [f"PS> sample say {word}", f"not {word}"]


def proto(title: str, *sections) -> str:
    """A prototype with one transcript per section.

    The first heading is ``Prototype: <title>``, so it never repeats a
    section's heading (a repeat would make that section ``<heading> (2)``).

    Args:
        title: The first heading's name.
        *sections: ``(heading, lines)`` pairs; lines of None give a section
            whose block is not a transcript.

    Returns:
        The Markdown text.
    """
    text = f"# Prototype: {title}\n"
    for heading, lines in sections:
        body = block(*lines) if lines is not None else block("name = \"tofu\"", info="toml")
        text += f"\n## {heading}\n\n" + body
    return text


LIST = "docs/prototypes/F01-list.md"
EXAMPLE = "docs/prototypes/F01-example-data.md"
COUNT = "docs/prototypes/F02-count.md"
SCREEN = "docs/prototypes/F02-screen.html"
SHARED = "docs/prototypes/shared.md"
LATER = "docs/prototypes/F03-later.md"
EXTRA = "docs/prototypes/F02-extra.md"
LIST_MARKS = ('[sections."List"]\nlater = [{ feature = "F03", typed = "sample say later" }, '
              '{ feature = "F02", typed = "sample say f02" }, '
              '{ feature = "F01", typed = "sample say old" }]')
TABLE_FILES = {
    LIST: proto("List", ("List", says("list", "later", "f02", "old"))),
    run_file_path(LIST): run_file(LIST_MARKS),
    EXAMPLE: proto("Example data", ("Recipes", None)),
    COUNT: proto("Count", ("Count", says("count")), ("Search", says("search"))),
    run_file_path(COUNT): run_file('[sections."Search"]\nlater = [{ feature = "F03" }]'),
    SCREEN: "<html><body>PS> sample say screen</body></html>\n",
    SHARED: proto("Shared", ("Both", says("shared"))),
    run_file_path(SHARED): run_file(),
    LATER: proto("Later", ("Later", wrong("f03"))),
    run_file_path(LATER): run_file(),
    EXTRA: proto("Extra", ("Extra", wrong("extra"))),
    run_file_path(EXTRA): run_file(),
}
TABLE_ROWS = [("List", "F01", LIST), ("Example data", "F01", EXAMPLE),
              ("Count", "F02", f"`{COUNT}`"), ("Screen", "F02", SCREEN),
              ("Shared", "F01, F02", SHARED), ("Later", "F03", LATER)]

FALLBACK_FILES = {
    "docs/prototypes/F01-a.md": proto("A", ("A", says("a"))),
    "docs/prototypes/F01-a.run.toml": run_file(),
    "docs/prototypes/F02-b.md": proto("B", ("B", says("b"))),
    "docs/prototypes/F02-b.run.toml": run_file(),
    "docs/prototypes/F03-c.md": proto("C", ("C", wrong("c"))),
    "docs/prototypes/F03-c.run.toml": run_file(),
    "docs/prototypes/notes.md": proto("Notes", ("Notes", wrong("notes"))),
    "docs/prototypes/notes.run.toml": run_file(),
}

ALL_A = "docs/prototypes/F01-a.md"
ALL_B = "docs/prototypes/F02-b.md"
ALL_C = "docs/prototypes/F03-c.md"
ALL_FILES = {
    ALL_A: proto("A", ("A", says("a", "needs f02"))),
    run_file_path(ALL_A): run_file('[sections."A"]\nlater = [{ feature = "F02", '
                                   'typed = "sample say needs f02" }]'),
    ALL_B: proto("B", ("B", says("b")), ("Search", says("search"))),
    run_file_path(ALL_B): run_file('[sections."Search"]\nlater = [{ feature = "F03" }]'),
    ALL_C: proto("C", ("C", wrong("c"))),
    run_file_path(ALL_C): run_file(),
}
ALL_ROWS = [("A", "F01", ALL_A), ("B", "F02", ALL_B), ("C", "F03", ALL_C)]

OWN = "docs/prototypes/F02-own.md"
OLD = "docs/prototypes/F01-old.md"
OLD_FILES = {OLD: proto("Old", ("Old", says("old"))), run_file_path(OLD): run_file()}
LABEL_CASES = {
    "skip": {OWN: proto("Own", ("Own", says("one", "two"))),
             run_file_path(OWN): run_file('[sections."Own"]\nskip = [{ typed = "sample say two", '
                                          'reason = "opens an editor" }]')},
    "wait": {OWN: proto("Own", ("Own", says("one", "two"))),
             run_file_path(OWN): run_file('[sections."Own"]\nlater = [{ feature = "F03" }]')},
    "no transcript": {OWN: proto("Own", ("Data", None))},
    "pipe": {OWN: proto("Own", ("Own", says("one") + ["PS> sample say two | Out-Host"])),
             run_file_path(OWN): run_file()},
}

_RUNS: dict = {}


def runs() -> dict:
    """Builds every project and runs the engine on each, side by side, once.

    Returns:
        Each case name mapped to ``(project, outcome, call log)``.
    """
    if _RUNS:
        return _RUNS
    cases = {
        "table": (history(project_files(rows=TABLE_ROWS, files=TABLE_FILES)), ("--item", "F02")),
        "fallback": (history(project_files(rows=None, files=FALLBACK_FILES)), ("--item", "F02")),
        "all": ([base_step(project_files(rows=ALL_ROWS, files=ALL_FILES)), *stages(F01, 6),
                 *stages(F02, 5), stage_step(F02, 6, style="squash", pr=46)], ("--all",)),
    }
    for name, files in LABEL_CASES.items():
        rows = [("Old", "F01", OLD), ("Own", "F02", OWN)]
        cases[name] = (history(project_files(rows=rows, files={**OLD_FILES, **files})),
                       ("--item", "F02"))

    def run(name):
        """Builds one project and runs the engine with a call log."""
        steps, args = cases[name]
        project = RealProject(steps)
        log = new_log(name.replace(" ", "-"))
        return project, project.real_run(*args, log=log), log
    names = list(cases)
    _RUNS.update(zip(names, parallel(run, names)))
    return _RUNS


def argvs(log) -> list:
    """The sample program's argument lists, in order."""
    return [call["argv"] for call in calls(log)]


class TableTests(RealRunCase):
    """The prototypes table at HEAD, own commands, and marks (design 5.2, 6)."""

    @classmethod
    def setUpClass(cls):
        """Runs every project once."""
        cls.project, cls.out, cls.log = runs()["table"]

    def setUp(self):
        """Every command that runs matches."""
        self.report = self.real_report(self.out, 0)

    def test_runs_the_items_and_the_accepted_features_prototypes(self):
        """F01's and F02's Markdown prototypes, and the shared one; not F03's, the HTML, or a
        file the table does not list."""
        self.assertEqual(sorted(p["file"] for p in self.report["prototypes"]),
                         sorted([LIST, EXAMPLE, COUNT, SHARED]))
        ran = argvs(self.log)
        for argv in (["say", "f03"], ["say", "extra"], ["say", "screen"]):
            self.assertNotIn(argv, ran)

    def test_feature_cells(self):
        """Each prototype's features come from its Feature cell; backticks around a path work."""
        self.assertEqual(prototype_of(self.report, SHARED)["features"], ["F01", "F02"])
        self.assertEqual(prototype_of(self.report, COUNT)["features"], ["F02"])
        self.assertEqual(prototype_of(self.report, LIST)["features"], ["F01"])

    def test_prototype_without_a_transcript_needs_no_run_file(self):
        """``example-data.md``: no transcript, no run file, no problem."""
        entry = prototype_of(self.report, EXAMPLE)
        self.assertEqual((entry["transcript"], entry["run_file"]), (False, None))
        self.assertEqual(problems_of(self.report, prototype=EXAMPLE), [])

    def test_mark_for_a_feature_not_accepted_waits(self):
        """A mark naming F03 makes the command wait; it does not run and is not own."""
        for path, typed in ((LIST, "sample say later"), (COUNT, "sample say search")):
            with self.subTest(typed=typed):
                entry = command_of(self.report, path, typed)
                self.assert_command(entry, "waits for F03", own=False, real=None, exit=None)
        self.assertNotIn(["say", "later"], argvs(self.log))
        self.assertNotIn(["say", "search"], argvs(self.log))

    def test_mark_for_the_item_runs_and_is_own(self):
        """Planted bug "a later mark that still counts once its feature is accepted": the mark
        names F02, the item, so the command runs, must match, and is own."""
        self.assert_command(command_of(self.report, LIST, "sample say f02"), "matches", own=True)

    def test_mark_for_an_accepted_feature_runs(self):
        """A mark naming F01, accepted, runs normally; F01's commands are not F02's own."""
        self.assert_command(command_of(self.report, LIST, "sample say old"), "matches", own=False)

    def test_out_of_date_marks(self):
        """Marks naming the item or an accepted feature are listed as out of date."""
        found = sorted((m.get("prototype"), m.get("section"), m.get("feature"), m.get("typed"))
                       for m in self.report["out_of_date"])
        self.assertEqual(found, [(LIST, "List", "F01", "sample say old"),
                                 (LIST, "List", "F02", "sample say f02")])

    def test_own_commands(self):
        """Own: the item's prototypes and the shared one, and the command whose mark names F02."""
        own = {(path, typed): command_of(self.report, path, typed)["own"]
               for path, typed in ((LIST, "sample say list"), (COUNT, "sample say count"),
                                   (SHARED, "sample say shared"))}
        self.assertEqual(own, {(LIST, "sample say list"): False,
                               (COUNT, "sample say count"): True,
                               (SHARED, "sample say shared"): True})

    def test_counts_and_label(self):
        """All: 5 match and 2 wait. Own: 3 match. Every own command ran and matched."""
        self.assertEqual(self.report["counts"]["all"],
                         {"matches": 5, "mismatch": 0, "waits": 2, "not_run": 0})
        self.assertEqual(self.report["counts"]["own"], {**ZERO, "matches": 3})
        self.assertEqual((self.report["item"], self.report["all"]), ("F02", False))
        self.assertEqual(self.report["label"], LABEL_RAN)

    def test_unknown_feature(self):
        """``--item F07``, not in the features table: exit 1 with ``unknown-feature``."""
        report = self.real_report(self.project.real_run("--item", "F07"), 1)
        self.assertIn("unknown-feature", [p.get("kind") for p in report["problems"]])


class FallbackTests(RealRunCase):
    """Without a prototypes table: ``docs/prototypes/<ID>-*.md`` (design 5.2)."""

    @classmethod
    def setUpClass(cls):
        """Runs every project once."""
        cls.project, cls.out, cls.log = runs()["fallback"]

    def test_file_names_choose_the_prototypes(self):
        """F01's and F02's files run, with their IDs as Feature; F03's and ``notes.md`` do not."""
        report = self.real_report(self.out, 0)
        found = sorted((p["file"], tuple(p["features"])) for p in report["prototypes"])
        self.assertEqual(found, [("docs/prototypes/F01-a.md", ("F01",)),
                                 ("docs/prototypes/F02-b.md", ("F02",))])
        self.assertEqual(sorted(argvs(self.log)), [["say", "a"], ["say", "b"]])
        self.assertEqual(report["counts"]["own"], {**ZERO, "matches": 1})
        self.assertEqual(report["label"], LABEL_RAN)


class AllTests(RealRunCase):
    """``--all`` runs every accepted feature's prototypes (design 5.1, 11)."""

    @classmethod
    def setUpClass(cls):
        """Runs every project once."""
        cls.project, cls.out, cls.log = runs()["all"]

    def setUp(self):
        """Every command that runs matches."""
        self.report = self.real_report(self.out, 0)

    def test_accepted_features_only(self):
        """F01 and F02 (accepted by a squash merge) run; F03 does not."""
        self.assertEqual(sorted(p["file"] for p in self.report["prototypes"]),
                         sorted([ALL_A, ALL_B]))
        self.assertNotIn(["say", "c"], argvs(self.log))

    def test_no_label_and_no_own_counts(self):
        """``--all`` decides no label and has no own counts."""
        self.assertIs(self.report["all"], True)
        self.assertIsNone(self.report["label"])
        self.assertIsNone(self.report["counts"]["own"])
        self.assertEqual(self.report["counts"]["all"],
                         {"matches": 3, "mismatch": 0, "waits": 1, "not_run": 0})

    def test_mark_for_an_accepted_feature_runs(self):
        """Planted bug "a later mark that still counts once its feature is accepted": F02 is
        accepted, so its mark no longer counts, and it is listed as out of date."""
        self.assert_command(command_of(self.report, ALL_A, "sample say needs f02"), "matches")
        self.assertEqual([(m.get("prototype"), m.get("feature"), m.get("typed"))
                          for m in self.report["out_of_date"]],
                         [(ALL_A, "F02", "sample say needs f02")])
        self.assert_command(command_of(self.report, ALL_B, "sample say search"), "waits for F03")

    def test_report_file_is_named_all(self):
        """The report is ``real-run-all-1.json``."""
        self.assertTrue(self.report["files"]["json"].replace("\\", "/")
                        .endswith("troy-mode/flow/real-run-all-1.json"),
                        self.report["files"])


class LabelTests(RealRunCase):
    """When F02 gets "Ran for real on Troy's PC" and when "Passes tests on main" (design 9)."""

    @classmethod
    def setUpClass(cls):
        """Runs every project once."""
        cls.runs = runs()

    def report(self, name: str) -> dict:
        """A label case's report; each is a clean run (F01's prototype matches)."""
        report = self.real_report(self.runs[name][1], 0)
        self.assert_command(command_of(report, OLD, "sample say old"), "matches", own=False)
        return report

    def assert_passes_tests(self, report: dict, own: dict) -> None:
        """The label is "Passes tests on main", with a reason, and the own counts."""
        self.assertEqual(report["label"], LABEL_TESTS)
        self.assertIsInstance(report["label_reason"], str)
        self.assertNotEqual(report["label_reason"].strip(), "")
        self.assertEqual(report["counts"]["own"], own)

    def test_skipped_own_command_gives_passes_tests(self):
        """Planted bug "the label given with a skipped command of the feature's own"."""
        report = self.report("skip")
        self.assert_not_run(command_of(report, OWN, "sample say two"))
        self.assert_passes_tests(report, {**ZERO, "matches": 1, "not_run": 1})

    def test_own_commands_that_all_wait_give_passes_tests(self):
        """Every own command waits for F03: no own command ran."""
        report = self.report("wait")
        self.assert_command(command_of(report, OWN, "sample say one"), "waits for F03")
        self.assert_passes_tests(report, ZERO)

    def test_no_transcript_of_its_own_gives_passes_tests(self):
        """F02's prototype has no transcript."""
        report = self.report("no transcript")
        self.assertIs(prototype_of(report, OWN)["transcript"], False)
        self.assert_passes_tests(report, ZERO)

    def test_own_line_that_is_not_run_gives_passes_tests(self):
        """A pipeline in F02's prototype is not run."""
        report = self.report("pipe")
        self.assert_not_run(command_of(report, OWN, "sample say two | Out-Host"))
        self.assert_passes_tests(report, {**ZERO, "matches": 1, "not_run": 1})


if __name__ == "__main__":
    unittest.main()
