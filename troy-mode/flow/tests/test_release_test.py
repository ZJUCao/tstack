"""release-test (F08 design 3.1, 5.5, 11.1; interface note sections 1, 2, and 4).

The tests read the version test plan on origin/main and JUnit files that
they write themselves, and check each scenario's result, the run's result,
the failed and skipped tests, Troy's scenarios, the run number, the comment,
and the exit codes.

Planted bugs of F08 design 11.2 caught here:

- "a scenario without a test counted as passing":
  ``ReleaseTestTests.test_claude_scenario_without_a_test_fails_the_run`` and
  ``test_a_longer_id_is_not_a_match``.
- "a skipped test counted as failing":
  ``ReleaseTestTests.test_everything_passes`` (a skipped regression test) and
  ``test_skipped_regression_test_alone_does_not_fail``.
"""

import sys
import unittest

from flow_helpers import (
    CHECKS_SOURCE, Fakes, FlowCase, Project, base_files, base_step, comments, new_dir, parallel, pr,
    release_pr, run_engine, version_plan_files, version_plan_path, write_junit,
)

if str(CHECKS_SOURCE) not in sys.path:
    sys.path.insert(0, str(CHECKS_SOURCE))
from troycheck.attribution import find_attribution  # noqa: E402  (after the path setup)

LIST_ARGS = ["pr", "list", "--state", "open", "--limit", "100", "--json",
             "number,title,headRefName,url,createdAt"]
PLAN = version_plan_path("v0.1")
DEVICES = (("Troy's PC", "Windows 11", "Claude"), ("Troy's laptop", "macOS 15", "Troy"),
           ("Troy's phone", "Android 16", "Troy"))
SCENARIOS = (("v0.1-S01", "Count words and lines", "Claude", "Run wc on a file of three words",
              "Prints 3 words"),
             ("v0.1-S02", "Count on Troy's laptop", "Troy",
              "Open a terminal and run wc notes.txt", "Prints the count"))
PERF = (("v0.1-S03", "PT01", "10 MB file", "1 run", "Troy's PC", "claude"),
        ("v0.1-S04", "PT02", "1000 files", "10 minutes", "Troy's phone", "Troy"))
RICH_PLAN = version_plan_files("v0.1", ["F01", "F02"], scenarios=SCENARIOS, perf=PERF,
                               devices=DEVICES)

PY = "version-tests.test_v0_1"
S01_A = (PY, "test_v0_1_s01_counts_words_and_lines")
S01_B = (PY, "test_V0-1-S01_twice[big]")
S010 = (PY, "test_v0_1_s010_not_s01")
S03 = ("", "Version.V0_1_S03_LargeFile")
F01_T01 = ("tests.test_f01", "test_f01_t01_counts")
F02_T01 = ("tests.test_f02", "test_f02_t01_counts_lines")
B12 = ("tests.test_b12", "test_b12_empty_history")


def label(case: tuple) -> str:
    """A JUnit case's label: ``classname::name``, or the name without a classname."""
    return f"{case[0]}::{case[1]}" if case[0] else case[1]


S01_LABELS = sorted([label(S01_A), label(S01_B)])
RUNS_BEFORE = comments(
    "Release test, run 1: failed\n\nv0.1-S01 failed.",
    "Release test by Troy, run 7: failed\n\nTroy: the laptop prints 0.",
    "Release test, run 2: failed\n\nv0.1-S03 failed.",
    "I think Release test, run 9: passed is still to come.",
    "Note:\nRelease test, run 5: passed")
OPEN_PRS = [release_pr(29, "v0.2.0"), release_pr(30, "v0.1.0"), release_pr(31, "v0.1.1")]


def fakes_with_runs() -> Fakes:
    """Release PRs #29 (v0.2.0), #30 (v0.1.0), and #31 (v0.1.1); #30 has runs 1 and 2."""
    return Fakes(OPEN_PRS, {30: RUNS_BEFORE, 31: comments("Release test, run 4: passed")})


class ReleaseTestTests(FlowCase):
    """One plan on origin/main, many JUnit files (note section 4)."""

    @classmethod
    def setUpClass(cls):
        """Writes the JUnit files and runs release-test once per case, side by side."""
        cls.project = Project([base_step(base_files(extra=RICH_PLAN))])
        folder = new_dir("junit")
        passing_regression = [(*F01_T01, "passed"), (*F02_T01, "passed"), (*B12, "skipped")]
        files = {
            "regression": passing_regression,
            "version": [(*S01_A, "passed"), (*S01_B, "passed"), (*S010, "passed")],
            "ctest": [(*S03, "passed")],
            "regression failed": [(*F01_T01, "failed"), (*F02_T01, "passed")],
            "regression error": [(*F01_T01, "passed"), (*F02_T01, "error")],
            "version failed": [(*S01_A, "passed"), (*S01_B, "failed")],
            "ctest skipped": [(*S03, "notrun")],
            "only s010": [(*S010, "passed")],
            "regression skipped only": [(*B12, "skipped")],
        }
        cls.paths = {name: write_junit(folder, name.replace(" ", "-") + ".xml", cases)
                     for name, cases in files.items()}
        cases = {
            "pass": ("regression", "version", "ctest"),
            "missing": ("regression", "version"),
            "regression failed": ("regression failed", "version", "ctest"),
            "regression error": ("regression error", "version", "ctest"),
            "version failed": ("regression", "version failed", "ctest"),
            "skipped scenario": ("regression", "version", "ctest skipped"),
            "only s010": ("regression", "only s010", "ctest"),
            "skipped regression": ("regression skipped only", "version", "ctest"),
        }
        cls.fakes = {name: fakes_with_runs() for name in cases}
        cls.fakes["no PR"] = Fakes()
        cases["no PR"] = ("regression", "version", "ctest")

        def run(name):
            """Runs release-test for one case with its own fakes."""
            args = ["release-test", "--version", "v0.1"]
            for junit in cases[name]:
                args += ["--junit", cls.paths[junit]]
            return cls.project.run(*args, fakes=cls.fakes[name])
        names = list(cases)
        cls.outs = dict(zip(names, parallel(run, names)))

    def result(self, name: str, code: int) -> dict:
        """Asserts the exit code and the common keys, and returns the report."""
        return self.report_of(self.outs[name], code, "release-test")

    def scenario(self, report: dict, scenario_id: str) -> dict:
        """The report's entry for one scenario."""
        found = [s for s in report["scenarios"] if s["id"] == scenario_id]
        self.assertEqual(len(found), 1, report["scenarios"])
        return found[0]

    def test_everything_passes(self):
        """Planted bug "a skipped test counted as failing": B12's test skipped here, and the
        run passed with every scenario Claude runs."""
        report = self.result("pass", 0)
        self.assertEqual((report["version"], report["plan"], report["pr"], report["run"]),
                         ("v0.1", PLAN, 30, 3))
        self.assertEqual((report["passed"], report["tests"]), (True, 7))
        self.assertEqual(report["failed_tests"], [])
        self.assertEqual(report["skipped_tests"], [label(B12)])
        self.assertEqual(report["heading"], "Release test, run 3: passed")
        self.assertEqual(report["commit"], self.project.head())

    def test_comment_passes_the_strict_attribution_check(self):
        """F08 posts the comment as it is, so it must pass R19 in strict mode (found in the
        trial: a heading that named the agent failed check-text)."""
        report = self.result("pass", 0)
        self.assertEqual(find_attribution(report["comment"], "strict"), [], report["comment"])

    def test_scenarios_in_plan_order_with_their_tests(self):
        """Each scenario of both tables, in document order, matched by ID (note section 2)."""
        report = self.result("pass", 0)
        self.assertEqual([s["id"] for s in report["scenarios"]],
                         ["v0.1-S01", "v0.1-S02", "v0.1-S03", "v0.1-S04"])
        s01 = self.scenario(report, "v0.1-S01")
        self.assertEqual({k: s01[k] for k in ("run_by", "scenario", "steps", "expected",
                                              "devices", "result")},
                         {"run_by": "Claude", "scenario": "Count words and lines",
                          "steps": "Run wc on a file of three words",
                          "expected": "Prints 3 words", "devices": [], "result": "passed"})
        self.assertEqual(sorted(s01["tests"]), S01_LABELS)
        s03 = self.scenario(report, "v0.1-S03")
        self.assertEqual((s03["run_by"], s03["tests"], s03["result"]),
                         ("Claude", [label(S03)], "passed"))

    def test_troys_scenarios_list_devices_and_steps(self):
        """Troy's scenario uses Troy's devices; Troy's performance case its Machine cell."""
        report = self.result("pass", 0)
        s02 = self.scenario(report, "v0.1-S02")
        self.assertEqual({k: s02[k] for k in ("run_by", "scenario", "steps", "expected",
                                              "devices", "tests", "result")},
                         {"run_by": "Troy", "scenario": "Count on Troy's laptop",
                          "steps": "Open a terminal and run wc notes.txt",
                          "expected": "Prints the count",
                          "devices": ["Troy's laptop (macOS 15)", "Troy's phone (Android 16)"],
                          "tests": [], "result": None})
        s04 = self.scenario(report, "v0.1-S04")
        self.assertEqual((s04["run_by"], s04["devices"], s04["tests"], s04["result"]),
                         ("Troy", ["Troy's phone"], [], None))

    def test_comment_names_commit_scenarios_and_troys_steps(self):
        """The comment starts with the heading and names what Troy and the PR need."""
        report = self.result("pass", 0)
        lines = report["comment"].split("\n")
        self.assertEqual(lines[0], report["heading"])
        body = "\n".join(lines[1:])
        for text in ("v0.1-S01", "v0.1-S02", "v0.1-S03", "v0.1-S04", label(S03),
                     self.project.head()[:7], "Troy's laptop (macOS 15)",
                     "Open a terminal and run wc notes.txt", "Prints the count"):
            with self.subTest(text=text):
                self.assertIn(text, body)

    def test_claude_scenario_without_a_test_fails_the_run(self):
        """Planted bug "a scenario without a test counted as passing": S03 has no test."""
        report = self.result("missing", 1)
        self.assertEqual(self.scenario(report, "v0.1-S03")["result"], "missing")
        self.assertEqual(self.scenario(report, "v0.1-S01")["result"], "passed")
        self.assertIs(report["passed"], False)
        self.assertEqual(report["heading"], "Release test, run 3: failed")
        self.assertEqual(report["failed_tests"], [])
        self.assertNotEqual(report["problems"], [])

    def test_a_longer_id_is_not_a_match(self):
        """``test_v0_1_s010_...`` is not a test of S01, which then has none."""
        report = self.result("only s010", 1)
        self.assertEqual(self.scenario(report, "v0.1-S01")["result"], "missing")
        self.assertEqual(self.scenario(report, "v0.1-S01")["tests"], [])
        self.assertIs(report["passed"], False)

    def test_failed_regression_test_fails_the_run(self):
        """F01-T01 failed in the regression: the run fails, and the test is listed."""
        report = self.result("regression failed", 1)
        self.assertEqual(report["failed_tests"], [label(F01_T01)])
        self.assertEqual([s["result"] for s in report["scenarios"]],
                         ["passed", None, "passed", None])
        self.assertEqual(report["heading"], "Release test, run 3: failed")
        self.assertIn(label(F01_T01), report["comment"])

    def test_error_counts_as_failed(self):
        """A JUnit error is a failed test."""
        report = self.result("regression error", 1)
        self.assertEqual(report["failed_tests"], [label(F02_T01)])

    def test_failing_version_test_fails_its_scenario(self):
        """One of S01's two tests failed: S01 failed, and the test is listed."""
        report = self.result("version failed", 1)
        self.assertEqual(self.scenario(report, "v0.1-S01")["result"], "failed")
        self.assertEqual(report["failed_tests"], [label(S01_B)])

    def test_skipped_scenario_does_not_pass(self):
        """S03's only test did not run (CTest ``notrun``): S03 skipped, so the run fails."""
        report = self.result("skipped scenario", 1)
        self.assertEqual(self.scenario(report, "v0.1-S03")["result"], "skipped")
        self.assertEqual(sorted(report["skipped_tests"]), sorted([label(B12), label(S03)]))
        self.assertEqual(report["failed_tests"], [])

    def test_skipped_regression_test_alone_does_not_fail(self):
        """Planted bug "a skipped test counted as failing": a regression of one skipped test."""
        report = self.result("skipped regression", 0)
        self.assertIs(report["passed"], True)
        self.assertEqual(report["skipped_tests"], [label(B12)])

    def test_without_a_release_pr(self):
        """No open release PR: ``pr`` null, run 1, and a note."""
        report = self.result("no PR", 0)
        self.assertEqual((report["pr"], report["run"]), (None, 1))
        self.assertEqual(report["heading"], "Release test, run 1: passed")
        self.assertNotEqual(report["notes"], [])

    def test_only_the_two_pr_calls(self):
        """release-test lists the open PRs and reads #30's comments, and nothing else.

        F15's note names ``--json comments,reviews`` for status only; a shared
        reader may ask release-test's view for the reviews too, so either field
        list is accepted here.
        """
        self.result("pass", 0)
        calls = self.fakes["pass"].gh_argvs()
        self.assertEqual(calls[0], LIST_ARGS)
        self.assertIn(["pr", "view", "30"], [argv[:3] for argv in calls])
        for argv in calls[1:]:
            with self.subTest(argv=argv):
                self.assertEqual(argv[:2], ["pr", "view"])
                self.assertIn(argv[3:], (["--json", "comments"], ["--json", "comments,reviews"]))
        self.assertEqual(self.fakes["pass"].mamba_calls(), [])


class PlanOnOriginMainTests(FlowCase):
    """The plan is read on origin/main, and a bad plan is a problem (note section 4)."""

    @classmethod
    def setUpClass(cls):
        """A clone whose branch drops S03 from the plan, and one with a bad Run by cell."""
        cls.folder = new_dir("junit")
        cls.version = write_junit(cls.folder, "version.xml", [(*S01_A, "passed")])
        cls.branch = Project([base_step(base_files(extra=RICH_PLAN))])
        smaller = version_plan_files("v0.1", ["F01", "F02"], scenarios=SCENARIOS, perf=[],
                                     devices=DEVICES)
        cls.branch.commit("[docs] Drop the performance cases", smaller)
        bad = version_plan_files("v0.1", ["F01", "F02"], scenarios=SCENARIOS + (
            ("v0.1-S05", "Count on the TV", "Someone", "Open the TV", "Shows the count"),),
            perf=[], devices=DEVICES)
        cls.bad = Project([base_step(base_files(extra=bad))])

    def test_scenarios_come_from_origin_main(self):
        """The branch's plan has no S03, origin/main's does: S03 is still missing."""
        out = self.branch.run("release-test", "--version", "v0.1", "--junit", self.version,
                              fakes=Fakes([release_pr(30, "v0.1.0")]))
        report = self.report_of(out, 1, "release-test")
        self.assertEqual([s["id"] for s in report["scenarios"]],
                         ["v0.1-S01", "v0.1-S02", "v0.1-S03", "v0.1-S04"])
        self.assertEqual(report["scenarios"][2]["result"], "missing")

    def test_run_by_neither_claude_nor_troy(self):
        """``Run by`` is "Someone": exit 1, and the problem names the scenario."""
        out = self.bad.run("release-test", "--version", "v0.1", "--junit", self.version,
                           fakes=Fakes([release_pr(30, "v0.1.0")]))
        report = self.report_of(out, 1, "release-test")
        self.assertTrue(any("v0.1-S05" in str(p) for p in report["problems"]),
                        report["problems"])

    def test_version_without_a_plan(self):
        """``--version v0.3`` has no plan on origin/main: exit 1 with a problem."""
        out = self.bad.run("release-test", "--version", "v0.3", "--junit", self.version,
                           fakes=Fakes())
        report = self.report_of(out, 1, "release-test")
        self.assertNotEqual(report["problems"], [])


class BadInputTests(FlowCase):
    """Inputs release-test cannot use: exit 2 (note section 4)."""

    def test_bad_inputs_exit_two(self):
        """A bad version, no JUnit, a missing or broken JUnit, no repository, gh failing."""
        project = Project([base_step(base_files(extra=RICH_PLAN))])
        folder = new_dir("badjunit")
        good = write_junit(folder, "good.xml", [(*S01_A, "passed")])
        broken = folder / "broken.xml"
        broken.write_bytes(b'<testsuites><testcase name="x"')
        open_prs = Fakes([release_pr(30, "v0.1.0")])
        cases = {
            "version without v": (["--version", "0.1", "--junit", good], open_prs),
            "version with a patch": (["--version", "v0.1.0", "--junit", good], open_prs),
            "version without a minor": (["--version", "v0", "--junit", good], open_prs),
            "no --junit": (["--version", "v0.1"], open_prs),
            "JUnit missing": (["--version", "v0.1", "--junit", str(folder / "nope.xml")],
                              open_prs),
            "JUnit not XML": (["--version", "v0.1", "--junit", str(broken)], open_prs),
            "gh fails": (["--version", "v0.1", "--junit", good], Fakes(fail=True)),
        }
        cases["control"] = (["--version", "v0.1", "--junit", good], open_prs)
        names = list(cases)
        outs = parallel(lambda n: project.run("release-test", *cases[n][0], fakes=cases[n][1]),
                        names)
        for name, out in zip(names, outs):
            with self.subTest(case=name):
                if name == "control":
                    # The same inputs, made valid, give a report: S03 has no test.
                    self.report_of(out, 1, "release-test")
                else:
                    self.assert_exit(out, 2)
        plain = new_dir("plain")
        out = run_engine(["release-test", "--version", "v0.1", "--junit", good, "--repo", plain,
                          "--json"], folder, Fakes([pr(30, "[docs] Release v0.1.0")]))
        self.assert_exit(out, 2)


if __name__ == "__main__":
    unittest.main()
