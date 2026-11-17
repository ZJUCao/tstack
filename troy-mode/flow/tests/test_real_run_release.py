"""The real run at the release test, and TM8's brief (F12 design 7.1, 11; note sections 9, 10).

A release project has F01 and F02 accepted, v0.1's test plan, and a
prototype for each feature. ``real-run --all`` and ``real-run --item F02``
run on it, and ``real-run --all`` on a copy whose F02 prototype mismatches.
``release-test --real-run`` then reads those reports, a report of an older
commit, and files that are no real-run report. TM8's brief is asked for at
stage 6, at an earlier stage, for an accepted feature, and for a version
(with both features accepted and v0.1's plan on ``origin/main``).
"""

import json
import re
import unittest

from flow_helpers import (
    F01, F02, TWO, Fakes, FlowCase, Project, base_files, base_step, new_dir, parallel,
    release_pr, same_path, stages, write_junit,
)
from realrun_helpers import (
    RealProject, RealRunCase, block, history, project_files, run_file, run_file_path,
)

A = "docs/prototypes/F01-a.md"
B = "docs/prototypes/F02-b.md"
ROWS = [("A", "F01", A), ("B", "F02", B)]


def release_files(b_output: str) -> dict:
    """The release project's prototypes; F02's shows ``b_output`` for ``sample say b``."""
    return {A: "# Prototype A\n\n## A\n\n" + block("PS> sample say a", "a"),
            run_file_path(A): run_file(),
            B: "# Prototype B\n\n## B\n\n" + block("PS> sample say b", b_output),
            run_file_path(B): run_file()}


JUNIT = [("version-tests.test_v0_1", "test_v0_1_s01_counts_words", "passed"),
         ("", "Version.V0_1_S03_LargeFile", "passed")]
MISMATCH = {"prototype": B, "section": "B", "typed": "sample say b"}

_STATE: dict = {}


def state() -> dict:
    """Runs the real runs, then every release test, once.

    Returns:
        ``reports`` (real-run name to report), ``outs`` (release-test case
        to outcome), and ``later`` (release-test of an older report after a
        new commit).
    """
    if _STATE:
        return _STATE

    def build(b_output):
        """A release project, both features accepted."""
        files = project_files(features=TWO, rows=ROWS, files=release_files(b_output))
        return RealProject(history(files, accepted=(F01, F02), current=()))

    def release_runs():
        """``--all`` then ``--item F02`` on the matching project."""
        project = build("b")
        return project, project.real_run("--all"), project.real_run("--item", "F02")

    def mismatch_run():
        """``--all`` on the project whose F02 prototype is wrong."""
        project = build("not b")
        return project, project.real_run("--all")
    (release, all_out, item_out), (wrong, wrong_out) = parallel(
        lambda job: job(), [release_runs, mismatch_run])
    reports = {"all": all_out.report, "item": item_out.report, "mismatch": wrong_out.report}
    for name, out in (("all", all_out), ("item", item_out), ("mismatch", wrong_out)):
        assert out.report is not None and out.report.get("files"), (name, out.describe())
    folder = new_dir("release")
    junit = write_junit(folder, "version.xml", JUNIT)
    not_json = folder / "not-json.json"
    not_json.write_bytes(b"Release test notes, not JSON.\n")
    other = folder / "status.json"
    other.write_bytes(json.dumps({"command": "status", "ok": True, "notes": [],
                                  "problems": []}).encode("utf-8"))
    cases = {
        "plain": (release, None),
        "all": (release, reports["all"]["files"]["json"]),
        "item": (release, reports["item"]["files"]["json"]),
        "mismatch": (wrong, reports["mismatch"]["files"]["json"]),
        "not json": (release, str(not_json)),
        "other command": (release, str(other)),
        "missing": (release, str(folder / "missing.json")),
    }

    def release_test(name):
        """Runs release-test for one case."""
        project, report = cases[name]
        extra = ["--real-run", report] if report else []
        return project.run("release-test", "--version", "v0.1", "--junit", junit, *extra,
                           fakes=Fakes([release_pr(30, "v0.1.0")]))
    names = list(cases)
    outs = dict(zip(names, parallel(release_test, names)))
    release.commit("[docs] Note the release", {"README.md": "# wordcount\n\nReleased.\n"})
    later = release.run("release-test", "--version", "v0.1", "--junit", junit, "--real-run",
                        reports["all"]["files"]["json"], fakes=Fakes([release_pr(30, "v0.1.0")]))
    _STATE.update(reports=reports, outs=outs, later=later)
    return _STATE


def comment_lines(report: dict) -> list:
    """The release test comment's lines."""
    return report["comment"].split("\n")


def real_run_line(lines: list) -> int:
    """The index of the line that starts the comment's "Real run:" part, or -1."""
    return next((i for i, line in enumerate(lines) if line.startswith("Real run:")), -1)


class ReleaseRealRunTests(RealRunCase):
    """``release-test --real-run`` (design 11; note section 9)."""

    @classmethod
    def setUpClass(cls):
        """Runs everything once."""
        found = state()
        cls.reports, cls.outs, cls.later = found["reports"], found["outs"], found["later"]

    def result(self, name: str, code: int) -> dict:
        """A release-test case's report, with its exit code."""
        return self.report_of(self.outs[name], code, "release-test")

    def test_real_runs_behind_the_release_test(self):
        """``--all`` and ``--item`` match; the wrong prototype mismatches."""
        self.assertEqual(self.reports["all"]["counts"]["all"],
                         {"matches": 2, "mismatch": 0, "waits": 0, "not_run": 0})
        self.assertEqual(self.reports["mismatch"]["counts"]["all"]["mismatch"], 1)

    def test_without_real_run_as_before(self):
        """No ``--real-run``: no real-run part, and the run passes as before."""
        report = self.result("plain", 0)
        self.assertIsNone(report.get("real_run"))
        self.assertEqual(real_run_line(comment_lines(report)), -1, report["comment"])

    def test_passing_real_run(self):
        """A clean ``--all`` report of HEAD: passed, its counts, and a "Real run:" part after
        the automated scenarios."""
        report = self.result("all", 0)
        self.assertEqual((report["passed"], report["heading"]),
                         (True, "Release test, run 1: passed"))
        real = report["real_run"]
        self.assertTrue(same_path(real["file"], self.reports["all"]["files"]["json"]), real)
        self.assertIs(real["passed"], True)
        self.assertEqual((real["mismatches"], real["problems"]), ([], []))
        self.assertIn(real["counts"], (self.reports["all"]["counts"],
                                       self.reports["all"]["counts"]["all"]))
        lines = comment_lines(report)
        scenario = next(i for i, line in enumerate(lines) if line.startswith("- v0.1-S01"))
        self.assertGreater(real_run_line(lines), scenario, report["comment"])

    def test_mismatch_fails_the_release_test(self):
        """A mismatch in the report: failed, listed, and named in the comment."""
        report = self.result("mismatch", 1)
        self.assertEqual((report["passed"], report["heading"]),
                         (False, "Release test, run 1: failed"))
        real = report["real_run"]
        self.assertIs(real["passed"], False)
        self.assertEqual([{k: m.get(k) for k in MISMATCH} for m in real["mismatches"]],
                         [MISMATCH])
        lines = comment_lines(report)
        start = real_run_line(lines)
        self.assertGreaterEqual(start, 0, report["comment"])
        self.assertTrue(any("sample say b" in line for line in lines[start:]), report["comment"])

    def test_report_not_run_with_all_fails(self):
        """A ``--item`` report is not the release's real run."""
        report = self.result("item", 1)
        self.assertIs(report["passed"], False)
        self.assertIs(report["real_run"]["passed"], False)

    def test_report_of_another_commit_fails(self):
        """After a new commit, the earlier report no longer names HEAD."""
        report = self.report_of(self.later, 1, "release-test")
        self.assertIs(report["passed"], False)
        self.assertIs(report["real_run"]["passed"], False)

    def test_files_that_are_no_real_run_report_exit_two(self):
        """Text that is not JSON, another command's report, and a missing file."""
        for name in ("not json", "other command", "missing"):
            with self.subTest(case=name):
                self.assert_exit(self.outs[name], 2)


TM8_KINDS = ("bug", "prototype", "requirement", "later", "setup", "console")
MISMATCHES = ("1. docs/prototypes/F02-b.md, section B, sample say b: prototype shows b, "
              "the program prints not b.\n")


class Tm8BriefTests(FlowCase):
    """TM8 rules on a real run's mismatches (design 7.1; note section 10)."""

    @classmethod
    def setUpClass(cls):
        """Asks for TM8 at stage 6, at stage 3, for an accepted feature, and for v0.1."""
        cls.stage6 = Project([base_step(base_files(TWO)), *stages(F01, 6), *stages(F02, 5)])
        stage3 = Project([base_step(base_files(TWO)), *stages(F01, 6), *stages(F02, 2)])
        cls.input = new_dir("tm8") / "mismatches.txt"
        cls.input.write_bytes(MISMATCHES.encode("utf-8"))
        version = Project([base_step(base_files(TWO)), *stages(F01, 6), *stages(F02, 6)])
        cases = {"stage 6": (cls.stage6, "F02", ["--input-file", str(cls.input)]),
                 "stage 3": (stage3, "F02", []),
                 "accepted": (cls.stage6, "F01", []),
                 "version": (version, "v0.1", ["--input-file", str(cls.input)])}
        names = list(cases)
        outs = parallel(lambda n: cases[n][0].run("brief", "--task", "TM8", "--item",
                                                  cases[n][1], *cases[n][2]), names)
        cls.outs = dict(zip(names, outs))

    def task_line(self, report: dict) -> str:
        """The prompt's Task line."""
        return next((line for line in report["prompt"].split("\n") if line.startswith("Task: ")),
                    "")

    def test_stage_six_brief(self):
        """TM8 for F02 at stage 6: the Test Manager, the stage, the title, and the input."""
        report = self.report_of(self.outs["stage 6"], 0, "brief")
        self.assertEqual((report["task"], report["role"], report["item"], report["stage"]),
                         ("TM8", "test-manager", "F02", 6))
        self.assertEqual(report["title"], F02.title(6))
        self.assertEqual(report["agent"], {"subagent_type": "tstack:troy-test-manager"})
        self.assertEqual(report["input"].rstrip("\n"), MISMATCHES.rstrip("\n"))
        self.assertEqual(report["checks"], [])

    def test_task_line_names_the_six_kinds_and_no_change(self):
        """The Task line names every kind of ruling and says to change no file."""
        line = self.task_line(self.report_of(self.outs["stage 6"], 0, "brief"))
        for kind in TM8_KINDS:
            with self.subTest(kind=kind):
                self.assertRegex(line, rf"\b{kind}\b")
        self.assertIn("Change no file.", line)

    def test_reads_the_prototypes(self):
        """Read first includes ``docs/prototypes/``."""
        report = self.report_of(self.outs["stage 6"], 0, "brief")
        self.assertIn("docs/prototypes", [path.rstrip("/") for path in report["read_first"]])

    def test_refused_before_stage_six_and_after_acceptance(self):
        """F02 at stage 3, and F01 whose PR 6 merged: exit 1, a problem, and no brief."""
        for name in ("stage 3", "accepted"):
            with self.subTest(case=name):
                report = self.report_of(self.outs[name], 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"))

    def test_version_item_for_the_release_test(self):
        """TM8 for v0.1, the release test's real run."""
        report = self.report_of(self.outs["version"], 0, "brief")
        self.assertEqual((report["task"], report["role"], report["item"]),
                         ("TM8", "test-manager", "v0.1"))
        self.assertTrue(re.search(r"\bbug\b", self.task_line(report)), report["prompt"])


if __name__ == "__main__":
    unittest.main()
