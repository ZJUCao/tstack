"""check-skips (F07 design 3.1, 8.6 with D69, 14.1; part 2 note, check-skips).

The reports are troy-check's own: the tests build R09 and R10 with
``troycheck.testpolicy.check_r09`` and ``check_r10`` from JUnit files read by
``troycheck.junit.read_junit``, and write them with
``troycheck.report.render_json``. Only the results of other rules, and one
message troy-check never writes, are made by hand.

Planted bug of design 14.2 caught here: "``check-skips`` passing a failure
that is not a skip": ``CheckSkipsTests.test_one_detail_that_is_not_a_skip_fails`` and the
other exit-1 tests.
"""

import json
import sys
import unittest
from types import SimpleNamespace
from xml.sax.saxutils import quoteattr

from flow_helpers import CHECKS_SOURCE, FlowCase, Project, base_step, git, new_dir, parallel

if str(CHECKS_SOURCE) not in sys.path:
    sys.path.insert(0, str(CHECKS_SOURCE))

from troycheck.junit import read_junit  # noqa: E402  (after the path setup)
from troycheck.report import FAIL, PASS, Detail, Result, render_json  # noqa: E402
from troycheck.testpolicy import RunData, check_r09, check_r10  # noqa: E402
from troycheck.titles import parse_title  # noqa: E402

TESTS_TITLE = "[F01 4/6 tests] Count words"
IMPL_TITLE = "[F01 5/6 impl] Count words"
FIX_TITLE = "[B12 B/B fix] Crash on empty history"
COUNT = "tests.test_count"
T01 = (COUNT, "test_f01_t01_counts")
T02 = (COUNT, "test_f01_t02_counts_lines")
T03 = (COUNT, "test_f01_t03_empty_file")
T17 = (COUNT, "test_f01_t17_unreadable_file")
T17_LABEL = f"{COUNT}::test_f01_t17_unreadable_file"
T03_LABEL = f"{COUNT}::test_f01_t03_empty_file"
F02_T05 = ("tests.test_lines", "test_f02_t05_counts_lines")
F02_LABEL = "tests.test_lines::test_f02_t05_counts_lines"
B12_TEST = ("tests.test_b12", "test_b12_empty_history")
B5_TEST = ("tests.test_b5", "test_b5_two_files")
LEGACY_LABEL = "tests.legacy.test_old::test_reads_stdin"
R05_FAIL = Result("R05", FAIL, "1 public function lacks a doc comment.",
                  [Detail("src/wordcount/f01.py", 3, "count has no doc comment")])
BEFORE = (Result("R04", PASS, "Every function is short enough."),
          Result("R05", PASS, "Every public name has a doc comment."))
AFTER = (Result("R11", PASS, "Coverage meets the limits."),)


def junit(folder, name: str, cases) -> str:
    """Writes a JUnit file and returns its path.

    Args:
        folder: The folder to write in.
        name: The file name.
        cases: Tuples ``(classname, name, outcome)`` or ``(classname, name,
            outcome, file)``; classname "" for none; outcome ``passed``,
            ``failed``, ``skipped``, or ``notrun`` (CTest's status).

    Returns:
        The path, as text.
    """
    parts = ['<?xml version="1.0" encoding="utf-8"?>\n<testsuites>\n<testsuite name="run">\n']
    for case in cases:
        classname, test, outcome = case[:3]
        attrs = (f" classname={quoteattr(classname)}" if classname else "")
        attrs += f" name={quoteattr(test)}"
        if len(case) > 3:
            attrs += f" file={quoteattr(case[3])}"
        if outcome == "notrun":
            attrs += ' status="notrun"'
        body = {"failed": '<failure message="assert 1 == 2"/>',
                "skipped": '<skipped message="runs on Linux only"/>'}.get(outcome, "")
        parts.append(f"<testcase{attrs}>{body}</testcase>\n")
    parts.append("</testsuite>\n</testsuites>\n")
    path = folder / name
    path.write_bytes("".join(parts).encode("utf-8"))
    return str(path)


def code_report(repo, title: str, junits, legacy=(), accepted=(), before=BEFORE,
                after=AFTER) -> dict:
    """troy-check code's JSON report, with R09 and R10 from troy-check's own functions.

    Args:
        repo: An empty git repository, where troy-check finds no test plan.
        title: The PR title.
        junits: The JUnit paths.
        legacy: ``[tests] legacy`` patterns.
        accepted: Features accepted at the merge base.
        before: Results reported before R09.
        after: Results reported after R10.

    Returns:
        The parsed report.
    """
    ctx = SimpleNamespace(title=parse_title(title), title_text=title, repo=repo, head="HEAD",
                          base="HEAD", config=SimpleNamespace(legacy_tests=list(legacy)))
    tests = [test for path in junits for test in read_junit(path)]
    run = RunData(given=True, tests=tests, accepted=set(accepted))
    results = [*before, check_r09(ctx, run), check_r10(ctx, run), *after]
    return json.loads(render_json("code", ctx.title.to_dict(), results))


class CheckSkipsTests(FlowCase):
    """Whether the only local failures are tests skipped on this platform (D69)."""

    @classmethod
    def setUpClass(cls):
        """Builds the JUnit files and reports, then runs check-skips on each, side by side."""
        cls.project = Project([base_step()])
        folder = new_dir("skips")
        repo = new_dir("emptyrepo")
        git(repo, "init", "-q")
        files = {
            "r09": [(*T01, "failed"), (*T17, "skipped")],
            "r10": [(*T01, "passed"), ("", T17[1], "skipped")],
            "passing": [(*T01, "passed"), (*F02_T05, "skipped")],
            "both": [(*T01, "failed"), (*T17, "skipped"), (*F02_T05, "skipped")],
            "mix": [(*T01, "failed"), (*T02, "passed"), (*T17, "skipped")],
            "no F01": [(*B5_TEST, "passed")],
            "T17 passed": [(*T01, "failed"), (*T17, "passed")],
            "bug": [(*B12_TEST, "skipped")],
            "legacy": [(*T01, "passed"),
                       ("tests.legacy.test_old", "test_reads_stdin", "skipped",
                        "tests/legacy/test_old.py")],
            "ctest": [("", "WordCount.F01_T01_Counts", "passed"),
                      ("", "WordCount.F01_T17_UnreadableFile", "notrun")],
            "params": [(COUNT, T17[1] + "[posix]", "skipped"),
                       (COUNT, T17[1] + "[root]", "skipped"), (*T03, "skipped"),
                       (*T01, "passed")],
            "first": [(*T01, "passed"), (*T17, "skipped")],
            "second": [(*T03, "skipped"), (*F02_T05, "skipped")],
        }
        j = {name: junit(folder, name.replace(" ", "-") + ".xml", cases)
             for name, cases in files.items()}
        wrong_rule = code_report(repo, TESTS_TITLE, [j["r09"]])
        wrong_rule["results"] = [
            {"rule": "R09", "result": "pass", "message": "All 2 tests fail.", "details": []},
            {"rule": "R10", "result": "fail", "message": "1 problems in 2 tests.",
             "details": [{"path": None, "line": None,
                          "message": f"{T17_LABEL} skipped against the mock"}]}]
        reports = {
            "passing": (code_report(repo, IMPL_TITLE, [j["passing"]]), [j["passing"]]),
            "only R09": (code_report(repo, TESTS_TITLE, [j["r09"]]), [j["r09"]]),
            "only R10": (code_report(repo, IMPL_TITLE, [j["r10"]]), [j["r10"]]),
            "R09 and R10": (code_report(repo, TESTS_TITLE, [j["both"]], accepted={"F02"}),
                            [j["both"]]),
            "mix": (code_report(repo, TESTS_TITLE, [j["mix"]]), [j["mix"]]),
            "other rule": (code_report(repo, TESTS_TITLE, [j["r09"]],
                                       before=(BEFORE[0], R05_FAIL)), [j["r09"]]),
            "no details": (code_report(repo, TESTS_TITLE, [j["no F01"]]), [j["no F01"]]),
            "not skipped here": (code_report(repo, TESTS_TITLE, [j["r09"]]), [j["T17 passed"]]),
            "bug": (code_report(repo, FIX_TITLE, [j["bug"]]), [j["bug"]]),
            "legacy": (code_report(repo, IMPL_TITLE, [j["legacy"]], legacy=["tests/legacy/**"]),
                       [j["legacy"]]),
            "ctest": (code_report(repo, IMPL_TITLE, [j["ctest"]]), [j["ctest"]]),
            "params": (code_report(repo, IMPL_TITLE, [j["params"]]), [j["params"]]),
            "two files": (code_report(repo, IMPL_TITLE, [j["first"], j["second"]]),
                          [j["first"], j["second"]]),
            "wrong rule": (wrong_rule, [j["r09"]]),
        }
        runs = {}
        for name, (data, junits) in reports.items():
            path = folder / (name.replace(" ", "-") + ".json")
            path.write_bytes(json.dumps(data, indent=2).encode("utf-8"))
            args = ["--report", str(path)]
            for junit_path in junits:
                args += ["--junit", junit_path]
            runs[name] = args
        cls.report_path = str(folder / "only-R09.json")
        cls.junit_path = j["r09"]
        cls.folder = folder
        names = list(runs)
        outs = parallel(lambda name: cls.project.run("check-skips", *runs[name]), names)
        cls.outs = dict(zip(names, outs))

    def result(self, name: str, code: int) -> dict:
        """Asserts the exit code and the common keys, and returns the report."""
        return self.report_of(self.outs[name], code, "check-skips")

    def assert_keys(self, report: dict, failed, ci_only, skipped, problems=()) -> None:
        """Asserts ``failed``, ``ci_only``, ``skipped``, and ``problems`` exactly."""
        self.assertEqual(report["failed"], list(failed))
        self.assertEqual(report["ci_only"], list(ci_only))
        self.assertEqual(report["skipped"], list(skipped))
        self.assertEqual(report["problems"], list(problems))

    def test_passing_troy_check(self):
        """Nothing failed: exit 0, no CI-only case; a skip that explains nothing is listed."""
        self.assert_keys(self.result("passing", 0), [], [], [F02_LABEL])

    def test_only_r09_skips(self):
        """R09 fails only on a test skipped here: exit 0, its case ID is CI's to check."""
        self.assert_keys(self.result("only R09", 0), ["R09"], ["F01-T17"], [T17_LABEL])

    def test_only_r10_skips_and_a_label_without_classname(self):
        """R10 fails only on a skipped test without a classname: its label is its name."""
        self.assert_keys(self.result("only R10", 0), ["R10"], ["F01-T17"],
                         ["test_f01_t17_unreadable_file"])

    def test_r09_and_r10_skips_together(self):
        """Both rules fail only on skips: ``failed`` in report order, ``ci_only`` sorted."""
        self.assert_keys(self.result("R09 and R10", 0), ["R09", "R10"], ["F01-T17", "F02-T05"],
                         [T17_LABEL, F02_LABEL])

    def test_one_detail_that_is_not_a_skip_fails(self):
        """Planted bug "check-skips passing a failure that is not a skip": a test that passed
        against the mock is a problem, while the skip is still CI's."""
        self.assert_keys(self.result("mix", 1), ["R09"], ["F01-T17"], [T17_LABEL],
                         [{"rule": "R09",
                           "message": f"{COUNT}::test_f01_t02_counts_lines passed against "
                                      "the mock"}])

    def test_another_rule_failing_fails(self):
        """R05 fails beside a skip: one problem with R05's message."""
        self.assert_keys(self.result("other rule", 1), ["R05", "R09"], ["F01-T17"], [T17_LABEL],
                         [{"rule": "R05", "message": "1 public function lacks a doc comment."}])

    def test_failing_r09_without_details_fails(self):
        """R09 fails with no detail ("No test of F01 was found."): one problem with that message."""
        self.assert_keys(self.result("no details", 1), ["R09"], [], [],
                         [{"rule": "R09", "message": "No test of F01 was found."}])

    def test_detail_about_a_test_not_skipped_in_these_files_fails(self):
        """The JUnit file given here has the test passing: the skip detail explains nothing."""
        self.assert_keys(self.result("not skipped here", 1), ["R09"], [], [],
                         [{"rule": "R09", "message": f"{T17_LABEL} skipped against the mock"}])

    def test_skip_message_of_the_other_rule_explains_nothing(self):
        """R10 explains only with "skipped but must pass"; R09's wording under R10 is a problem."""
        self.assert_keys(self.result("wrong rule", 1), ["R10"], [], [T17_LABEL],
                         [{"rule": "R10", "message": f"{T17_LABEL} skipped against the mock"}])

    def test_bug_test_is_named_by_its_bug_id(self):
        """PR B with B12's test skipped here: ``ci_only`` holds B12."""
        self.assert_keys(self.result("bug", 0), ["R10"], ["B12"], [f"tests.test_b12::"
                                                                   "test_b12_empty_history"])

    def test_test_without_an_id_is_named_by_its_label(self):
        """A legacy test without an ID, skipped here: ``ci_only`` holds its label."""
        self.assert_keys(self.result("legacy", 0), ["R10"], [LEGACY_LABEL], [LEGACY_LABEL])

    def test_ctest_test_that_did_not_run_is_skipped(self):
        """CTest's ``status="notrun"`` is a skip; the case ID comes from the test's own name."""
        self.assert_keys(self.result("ctest", 0), ["R10"], ["F01-T17"],
                         ["WordCount.F01_T17_UnreadableFile"])

    def test_case_ids_are_sorted_without_repeats(self):
        """Two parametrized runs of F01-T17 and one of F01-T03: each ID once, sorted."""
        self.assert_keys(self.result("params", 0), ["R10"], ["F01-T03", "F01-T17"],
                         [f"{T17_LABEL}[posix]", f"{T17_LABEL}[root]", T03_LABEL])

    def test_two_junit_files_in_order(self):
        """Skipped tests from two files, in file order; only those R10 names count for CI."""
        self.assert_keys(self.result("two files", 0), ["R10"], ["F01-T03", "F01-T17"],
                         [T17_LABEL, T03_LABEL, F02_LABEL])


class BadInputTests(FlowCase):
    """Inputs check-skips cannot read: exit 2 (part 2 note, check-skips)."""

    def test_bad_inputs_exit_two(self):
        """Missing options, missing or unreadable files, and a report without a results list."""
        project = Project([base_step()])
        folder = new_dir("badskips")
        good_junit = junit(folder, "good.xml", [(*T01, "failed"), (*T17, "skipped")])
        good = folder / "good.json"
        good.write_bytes(json.dumps({"command": "code", "ok": True, "title": None,
                                     "results": []}).encode("utf-8"))
        texts = {"not-json.json": b"{ not json", "list.json": b"[]",
                 "no-results.json": b'{"command": "code", "ok": true}',
                 "results-object.json": b'{"command": "code", "results": {"rule": "R09"}}',
                 "broken.xml": b'<testsuites><testcase name="x"'}
        for name, data in texts.items():
            (folder / name).write_bytes(data)
        cases = {
            "no --report": ["--junit", good_junit],
            "no --junit": ["--report", str(good)],
            "report missing": ["--report", str(folder / "nope.json"), "--junit", good_junit],
            "report not JSON": ["--report", str(folder / "not-json.json"), "--junit", good_junit],
            "report a list": ["--report", str(folder / "list.json"), "--junit", good_junit],
            "report without results": ["--report", str(folder / "no-results.json"),
                                       "--junit", good_junit],
            "results not a list": ["--report", str(folder / "results-object.json"),
                                   "--junit", good_junit],
            "JUnit missing": ["--report", str(good), "--junit", str(folder / "nope.xml")],
            "JUnit not XML": ["--report", str(good), "--junit", str(folder / "broken.xml")],
        }
        names = list(cases)
        outs = parallel(lambda name: project.run("check-skips", *cases[name]), names)
        for name, out in zip(names, outs):
            with self.subTest(case=name):
                self.assert_exit(out, 2)
        good_out = project.run("check-skips", "--report", str(good), "--junit", good_junit)
        self.assert_keys_of_good(good_out)

    def assert_keys_of_good(self, out) -> None:
        """The same files, read correctly, pass: an empty results list fails nothing."""
        report = self.report_of(out, 0, "check-skips")
        self.assertEqual((report["failed"], report["ci_only"], report["skipped"]),
                         ([], [], [T17_LABEL]))


if __name__ == "__main__":
    unittest.main()
