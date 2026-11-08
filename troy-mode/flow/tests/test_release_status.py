"""Status in F08 (F08 design 3.2, 3.3, 4, 5, 6, 11.1; interface note sections 1 to 3).

The version test plan before a version's features go on, the release and its
steps, the release PR after every other open PR, waiting for Troy, the
record of Troy's acceptance, the tag, the retrospective, patch releases, the
``versions`` and ``release`` keys, and the gh calls status makes for them.

Planted bugs of F08 design 11.2 caught here:

- "the version test plan not asked for before a version's first feature":
  ``VersionPlanTests.test_missing_plan_comes_before_the_first_stage`` and
  ``test_next_versions_plan_comes_before_its_first_feature``.
- "the plan's feature list not compared": ``VersionPlanTests.test_plan_with_fewer_features``,
  ``test_plan_with_more_features``, ``test_requirement_change_asks_for_the_plan_again``, and
  ``ReleaseTests.test_release_object_when_ready`` (``plan_matches``).
- "a release offered with a feature not accepted":
  ``ReleaseTests.test_no_release_while_a_feature_is_not_accepted``.
- "the release PR continued before a bug's PR": ``ReleasePrOrderTests``.
- "a patch allowed after a later version's implementation merged":
  ``PatchTests.test_later_versions_implementation_blocks_the_patch``,
  ``test_later_versions_mock_blocks_the_patch``,
  ``test_squashed_later_code_blocks_by_its_subject``, and
  ``test_open_patch_release_names_the_later_code``.
"""

import re
import unittest
from dataclasses import replace

from flow_helpers import (
    F01, F02, F03, PROGRESS, Fakes, FlowCase, Project, accepted_plan_files, base_files,
    base_step, bug_branch, bug_step, bug_title, change_step, comments, fake_status_runs, issue,
    merged_pr, pack_words, parallel, plan_title, plugin_checks_files, pr, progress_fields,
    record_acceptance_step, record_title, release_pr, release_step, release_title, stage_pr,
    stage_step, stages, subject_commits, tests_title, version_plan_files, version_plan_path,
    version_tests_step,
)

LIST_ARGS = ["pr", "list", "--state", "open", "--limit", "100", "--json",
             "number,title,headRefName,url"]
MERGED_ARGS = ["pr", "list", "--state", "merged", "--limit", "200", "--json",
               "number,title,url,mergeCommit"]
RELEASE_ARGS = ["release", "list", "--limit", "100", "--json", "tagName"]
ISSUE_ARGS = ["issue", "list", "--label", "bug", "--state", "open", "--limit", "100", "--json",
              "number,title,url"]

F03V2 = replace(F03, version="v0.2")
THREE = (F01, F02, F03V2)
PLAN1 = version_plan_path("v0.1")
PLAN2 = version_plan_path("v0.2")
CURRENT = plugin_checks_files()
TAG = "v0.1.0"
RELEASE_BRANCH = "troy-mode/release-v0.1.0"
TYPO = "[docs] Fix a typo in the README"
CRASH = "Crash on empty history"
MOCK_F03 = "[F03 3/6 mock] Count characters"
PASSED = "Release test, run 1: passed\n\nv0.1-S01 passed.\nv0.1-S03 passed."
FAILED = "Release test, run 1: failed\n\nv0.1-S01 failed.\n\nFailed tests:\n- x::y"
WAITING = "Waiting for Troy: accept v0.1.0"
RETRO = "Retrospective: v0.1.0\n\nNothing repeated in two or more PRs."


def files_of(features=THREE, plans: bool = True, drop=()) -> dict:
    """Base files with the plugin's troy-check copy, so ``checks.outdated`` is false.

    Args:
        features: The features table.
        plans: Whether each version gets a matching plan.
        drop: Paths to leave out.

    Returns:
        Paths mapped to content.
    """
    files = base_files(features, extra=CURRENT, plans=plans)
    for path in drop:
        files.pop(path)
    return files


BASE = base_step(files_of())
ACCEPTED = [BASE, *stages(F01, 6), *stages(F02, 6)]
TESTED = ACCEPTED + [version_tests_step("v0.1")]
ACCEPTED_PLAN = accepted_plan_files("v0.1", ["F01", "F02"], [TAG])
RELEASED = TESTED + [release_step(TAG, ACCEPTED_PLAN)]
DONE_FAKES = dict(releases=[TAG], merged=[merged_pr(40, release_title(TAG))],
                  comments={40: comments(RETRO)})


def python_rests() -> list:
    """The Python pack's steps after ``<mamba> run <target>``, before troy-check."""
    return [["ruff", "check"], ["ruff", "format", "--check"], ["mypy"],
            ["coverage", "run", "-m", "pytest", "--junitxml=reports/junit.xml", "||", "true"],
            ["coverage", "xml", "-o", "reports/coverage.xml"]]


def troy_check_words(title: str) -> list:
    """The Python troy-check step's words after the target, sorted, without --worktree."""
    return sorted(["python", ".troy-mode/checks/troy_check.py", "code", "--base", "origin/main",
                   "--title", title, "--junit", "reports/junit.xml", "--coverage",
                   "reports/coverage.xml"])


def named(problems, text: str) -> bool:
    """Whether one problem sentence holds the text."""
    return any(text in str(problem) for problem in problems)


def names_number(problems, number: int) -> bool:
    """Whether one problem sentence holds the number as a whole number."""
    pattern = re.compile(rf"(?<!\d){number}(?!\d)")
    return any(pattern.search(str(problem)) for problem in problems)


class VersionPlanTests(FlowCase):
    """``version-test-plan`` (D70, note 3.2 rules 10 and 11)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        fewer = version_plan_files("v0.1", ["F01"])
        more = version_plan_files("v0.1", ["F01", "F02", "F03"])
        reordered = version_plan_files("v0.1", ["F02", "F01"])
        moved = (F01, replace(F02, version="v0.2"), F03V2)
        cls.outs = fake_status_runs({
            "no plan": ([base_step(files_of(plans=False))], {}),
            "no plan, mid feature": ([base_step(files_of(plans=False)), *stages(F01, 3)], {}),
            "fewer": ([base_step({**files_of(), **fewer})], {}),
            "more": ([base_step({**files_of(), **more})], {}),
            "reordered": ([base_step({**files_of(), **reordered})], {}),
            "other version missing": ([base_step(files_of(drop=(PLAN2,)))], {}),
            "moved": ([BASE, *stages(F01, 6), change_step("Move F02 to v0.2", moved, "2.0")],
                      {}),
            "next version missing": (
                [base_step(files_of(drop=(PLAN2,))), *stages(F01, 6), *stages(F02, 6),
                 version_tests_step("v0.1"), release_step(TAG, ACCEPTED_PLAN)], DONE_FAKES),
            "accepted without plan": ([base_step(files_of(plans=False)), *stages(F01, 6),
                                       *stages(F02, 6)], {}),
            "open plan PR": ([base_step(files_of(plans=False))],
                             {"prs": [pr(34, plan_title("v0.1"), "troy-mode/v0.1-test-plan")]}),
            "open update PR": ([base_step({**files_of(), **fewer})],
                               {"prs": [pr(36, plan_title("v0.1", True),
                                           "troy-mode/v0.1-test-plan")]}),
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def assert_plan(self, name: str, version: str = "v0.1", update: bool = False) -> None:
        """Asserts that the case's next action is TM7's plan for the version."""
        self.assert_next(self.report(name), action="version-test-plan", item=version,
                         task="TM7", title=plan_title(version, update),
                         branch=f"troy-mode/{version}-test-plan", merged_by="f07",
                         doc=version_plan_path(version))

    def test_missing_plan_comes_before_the_first_stage(self):
        """Planted bug "plan not asked for": no plan, F01 not started: TM7 adds v0.1's plan."""
        self.assert_plan("no plan")
        self.assertEqual(self.report("no plan")["next_feature"], "F01")

    def test_missing_plan_stops_a_feature_in_progress(self):
        """F01 at stage 4 and no plan (the trial's upgrade case, design 11.3 step 3): TM7 first."""
        self.assert_plan("no plan, mid feature")

    def test_plan_with_fewer_features(self):
        """Planted bug "feature list not compared": the plan lists F01 only: TM7 updates it."""
        self.assert_plan("fewer", update=True)

    def test_plan_with_more_features(self):
        """The plan lists F03 too, which belongs to v0.2: TM7 updates it."""
        self.assert_plan("more", update=True)

    def test_feature_lists_are_compared_as_sets(self):
        """``F02, F01`` matches the table's F01 and F02: F01's design is next, Troy merges it."""
        report = self.report("reordered")
        self.assert_next(report, action="stage", item="F01", stage=1, task="IF1",
                         title=F01.title(1), branch=F01.branch(1), merged_by="troy")
        self.assertEqual(report["versions"][0]["plan_features"], ["F02", "F01"])
        self.assertIs(report["versions"][0]["plan_matches"], True)

    def test_only_the_next_features_version_counts(self):
        """v0.2 has no plan, but F01 of v0.1 is next and its plan matches: stage 1 of F01."""
        report = self.report("other version missing")
        self.assert_next(report, action="stage", item="F01", stage=1, task="IF1",
                         title=F01.title(1), branch=F01.branch(1), merged_by="troy")
        self.assertEqual([(v["version"], v["plan"], v["plan_matches"])
                          for v in report["versions"]],
                         [("v0.1", PLAN1, True), ("v0.2", None, False)])
        self.assertIsNone(report["versions"][1]["plan_features"])

    def test_requirement_change_asks_for_the_plan_again(self):
        """F02 moved to v0.2: v0.1 is F01 alone, accepted, and its plan still lists F02."""
        report = self.report("moved")
        self.assert_plan("moved", update=True)
        self.assertEqual(report["versions"][0]["features"], ["F01"])
        self.assertEqual(report["versions"][0]["plan_features"], ["F01", "F02"])
        self.assertEqual(report["release"]["tag"], TAG)
        self.assertIs(report["release"]["plan_matches"], False)

    def test_next_versions_plan_comes_before_its_first_feature(self):
        """Planted bug "plan not asked for": v0.1 released; F03 of v0.2 waits for v0.2's plan."""
        report = self.report("next version missing")
        self.assert_plan("next version missing", "v0.2")
        self.assertEqual(report["next_feature"], "F03")

    def test_release_without_a_plan_asks_for_it(self):
        """Every feature of v0.1 accepted, no plan: TM7's plan, not the release."""
        report = self.report("accepted without plan")
        self.assert_plan("accepted without plan")
        self.assertTrue(named(report["release"]["problems"], PLAN1), report["release"])

    def test_open_plan_prs_are_continued_by_tm7(self):
        """An open ``Add`` or ``Update`` plan PR is continued, with TM7 and the version."""
        self.assert_next(self.report("open plan PR"), action="continue-pr", pr=34, item="v0.1",
                         task="TM7", title=plan_title("v0.1"), branch="troy-mode/v0.1-test-plan",
                         merged_by="f07")
        self.assert_next(self.report("open update PR"), action="continue-pr", pr=36,
                         item="v0.1", task="TM7", title=plan_title("v0.1", True),
                         branch="troy-mode/v0.1-test-plan", merged_by="f07")


TROY_ONLY = version_plan_files("v0.1", ["F01", "F02"], scenarios=[
    ("v0.1-S01", "Count on Troy's laptop", "Troy", "Run wc notes.txt", "Prints the count")],
    perf=[])
PERF_ONLY = version_plan_files("v0.1", ["F01", "F02"], scenarios=[
    ("v0.1-S01", "Count on Troy's laptop", "Troy", "Run wc notes.txt", "Prints the count")])
OLDER = dict(CURRENT)
OLDER[".troy-mode/checks/troycheck/titles.py"] = (OLDER[".troy-mode/checks/troycheck/titles.py"]
                                                  + b"# An older copy.\n")


class ReleaseTests(FlowCase):
    """``release`` and its steps before the release PR (design 5.1 to 5.3, note rule 10)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        cls.outs = fake_status_runs({
            "ready": (ACCEPTED, {}),
            "tested": (TESTED, {}),
            "squashed tests": (ACCEPTED + [version_tests_step("v0.1", pr=44)], {}),
            "other version's tests": (ACCEPTED + [version_tests_step("v0.2")], {}),
            "troy only": ([base_step({**files_of(), **TROY_ONLY}), *stages(F01, 6),
                           *stages(F02, 6)], {}),
            "perf only": ([base_step({**files_of(), **PERF_ONLY}), *stages(F01, 6),
                           *stages(F02, 6)], {}),
            "not accepted": ([BASE, *stages(F01, 6), *stages(F02, 5)], {}),
            "open PR and bug": (ACCEPTED, {"prs": [pr(57, TYPO, "troy-mode/typo")],
                                           "issues": [issue(71, "Crash on an empty file")]}),
            "later code": (ACCEPTED + stages(F03V2, 3), {}),
            "outdated": ([base_step(base_files(THREE, extra=OLDER)), *stages(F01, 6),
                          *stages(F02, 6)], {}),
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def test_release_once_every_feature_is_accepted(self):
        """F01 and F02 accepted: the release of v0.1.0 starts with TE5's version tests."""
        self.assert_next(self.report("ready"), action="release", step="version-tests",
                         item="v0.1", tag=TAG, task="TE5", title=tests_title("v0.1"),
                         branch="troy-mode/v0.1-tests", merged_by="f07")

    def test_release_object_when_ready(self):
        """Every key of ``release`` for a version that is ready (note 3.3)."""
        self.assertEqual(self.report("ready")["release"], {
            "version": "v0.1", "tag": TAG, "patch": False, "features": ["F01", "F02"],
            "accepted": True, "plan": PLAN1, "plan_features": ["F01", "F02"],
            "plan_matches": True, "claude_scenarios": ["v0.1-S01", "v0.1-S03"],
            "troy_scenarios": ["v0.1-S02"], "tests_merged": False, "pr": None, "runs": [],
            "deferred": [], "open_bugs": [], "checks": [], "problems": []})

    def test_release_pr_after_the_version_tests(self):
        """A ``[v0.1 tests]`` commit on origin/main: PM4 opens the release PR next."""
        for name in ("tested", "squashed tests"):
            with self.subTest(case=name):
                report = self.report(name)
                self.assert_next(report, action="release", step="release-pr", item="v0.1",
                                 tag=TAG, task="PM4", title=release_title(TAG),
                                 branch=RELEASE_BRANCH, merged_by="f07")
                self.assertIs(report["release"]["tests_merged"], True)

    def test_tests_of_another_version_do_not_count(self):
        """A ``[v0.2 tests]`` commit leaves v0.1's version tests to write."""
        report = self.report("other version's tests")
        self.assertEqual(report["next"]["step"], "version-tests")
        self.assertIs(report["release"]["tests_merged"], False)

    def test_no_version_tests_when_troy_runs_every_scenario(self):
        """A plan with no scenario Claude runs: no ``version-tests`` step."""
        report = self.report("troy only")
        self.assert_next(report, action="release", step="release-pr", item="v0.1", tag=TAG,
                         task="PM4", title=release_title(TAG), branch=RELEASE_BRANCH,
                         merged_by="f07")
        self.assertEqual((report["release"]["claude_scenarios"],
                          report["release"]["troy_scenarios"]), ([], ["v0.1-S01"]))

    def test_a_performance_case_claude_runs_needs_version_tests(self):
        """Troy runs every end-to-end scenario, Claude the performance case: TE5 writes it."""
        report = self.report("perf only")
        self.assertEqual(report["next"]["step"], "version-tests")
        self.assertEqual(report["release"]["claude_scenarios"], ["v0.1-S03"])

    def test_no_release_while_a_feature_is_not_accepted(self):
        """Planted bug "release with a feature not accepted": F02 at stage 6 is next instead."""
        report = self.report("not accepted")
        self.assert_next(report, action="stage", item="F02", stage=6, task="PM3",
                         title=F02.title(6), branch=F02.branch(6), merged_by="f07")
        release = report["release"]
        self.assertEqual((release["tag"], release["accepted"], release["open_bugs"]),
                         (TAG, False, []))
        self.assertTrue(named(release["problems"], "F02"), release["problems"])
        self.assertFalse(named(release["problems"], "F01"), release["problems"])

    def test_problems_name_open_prs_and_bugs(self):
        """An open docs PR is continued; the release's problems name it and the open bug."""
        report = self.report("open PR and bug")
        self.assert_next(report, action="continue-pr", pr=57, title=TYPO,
                         branch="troy-mode/typo", merged_by="f07")
        release = report["release"]
        self.assertTrue(names_number(release["problems"], 57), release["problems"])
        self.assertTrue(names_number(release["problems"], 71), release["problems"])
        self.assertEqual(len(release["problems"]), 2, release["problems"])
        self.assertEqual(release["open_bugs"], [issue(71, "Crash on an empty file")])

    def test_later_versions_code_is_a_problem_but_not_the_next_action(self):
        """F03 (v0.2) has a merged mock: a problem naming it; the release still goes on."""
        report = self.report("later code")
        self.assertEqual((report["next"]["action"], report["next"]["step"]),
                         ("release", "version-tests"))
        self.assertTrue(named(report["release"]["problems"], MOCK_F03),
                        report["release"]["problems"])
        self.assertFalse(named(report["release"]["problems"], "[F03 2/6 test-plan]"),
                         report["release"]["problems"])

    def test_outdated_troy_check_is_a_problem(self):
        """An older copy of troy-check: a problem that names troy-init's upgrade."""
        problems = self.report("outdated")["release"]["problems"]
        self.assertTrue(any("upgrade" in str(p).lower() for p in problems), problems)


def release_case(*bodies: str, issues=(), prs=None, steps=TESTED) -> tuple:
    """A status case with the open release PR #30 and its comments.

    Args:
        *bodies: The release PR's comments, oldest first.
        issues: The open bug issues.
        prs: The open PRs, or None for the release PR alone.
        steps: The history.

    Returns:
        ``(steps, fakes keyword arguments)``.
    """
    return (steps, {"prs": prs if prs is not None else [release_pr(30, TAG)],
                    "comments": {30: comments(*bodies)}, "issues": list(issues)})


RELEASE_PR_NEXT = dict(action="release", item="v0.1", tag=TAG, pr=30, title=release_title(TAG),
                       branch=RELEASE_BRANCH, merged_by="f07")


class ReleasePrTests(FlowCase):
    """The steps once the release PR is open, from F08's comments (note 3.2 rule 10, 3.3)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        troy_reply = "Looks fine so far, still testing on the laptop."
        accepted = "Release test by Troy, run 1: accepted\n\nTroy: it works on my laptop."
        cls.outs = fake_status_runs({
            "open": release_case(),
            "passed": release_case(PASSED, WAITING),
            "replied": release_case(PASSED, WAITING, troy_reply),
            "accepted": release_case(PASSED, WAITING, accepted),
            "failed with bugs": release_case(FAILED, issues=[issue(15, "Wrong total"),
                                                             issue(12, CRASH)]),
            "troy failed": release_case(PASSED, WAITING, "Release test by Troy, run 1: failed\n\n"
                                        "Troy: the laptop prints 0.", issues=[issue(17, "Zero")]),
            "deferred": release_case(FAILED, "Bug deferred by Troy: #12",
                                     issues=[issue(12, CRASH)]),
            "fixed": release_case(FAILED),
            "not accepted": release_case(PASSED, WAITING, "Release test by Troy, run 1: not "
                                         "accepted\n\nTroy: F02 is not what I wanted."),
            "rerun": release_case(FAILED, "Release test, run 2: passed\n\nAll passed."),
            "cpp": release_case(steps=[base_step(base_files(THREE, lang="cpp", extra=CURRENT)),
                                       *stages(F01, 6), *stages(F02, 6),
                                       version_tests_step("v0.1")]),
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def test_open_release_pr_without_a_run_needs_the_release_test(self):
        """Release PR #30 without a record: the release test, with the PR's title and branch."""
        report = self.report("open")
        self.assert_next(report, step="release-test", **RELEASE_PR_NEXT)
        self.assertEqual((report["release"]["pr"], report["release"]["runs"]), (30, []))

    def test_release_test_checks_for_python(self):
        """The pack's steps, troy-check on the release PR's title without --worktree, then
        the release command (note 6)."""
        checks = self.report("open")["release"]["checks"]
        self.assertEqual(len(checks), 7, checks)
        for command, rest in zip(checks, python_rests()):
            _, target, words = pack_words(command)
            self.assertEqual((target, words), (["-n", "wordcount"], rest), command)
        _, target, words = pack_words(checks[5])
        self.assertEqual(sorted(words), troy_check_words(release_title(TAG)), checks[5])
        self.assertEqual(pack_words(checks[6])[1:],
                         (["-n", "wordcount"], ["pytest", "version-tests",
                                                "--junitxml=reports/version-junit.xml", "||",
                                                "true"]))

    def test_release_test_checks_for_cpp(self):
        """C/C++: cmake first, troy-check with the release PR's title, then the three steps."""
        checks = self.report("cpp")["release"]["checks"]
        self.assertEqual(pack_words(checks[0])[2], ["cmake", "--preset", "coverage"])
        self.assertEqual([pack_words(c)[2] for c in checks[-3:]], [
            ["cmake", "--preset", "coverage", "-DTROY_VERSION_TESTS=ON"],
            ["cmake", "--build", "--preset", "coverage"],
            ["ctest", "--preset", "coverage", "-L", "version", "--output-junit",
             "$PWD/reports/version-junit.xml", "||", "true"]])
        words = pack_words(checks[-4])[2]
        self.assertEqual(words[:3], ["python", ".troy-mode/checks/troy_check.py", "code"])
        self.assertEqual(words[words.index("--title") + 1], release_title(TAG))
        self.assertNotIn("--worktree", words)

    def test_passing_run_waits_for_troy(self):
        """Run 1 passed and F08 asked Troy: Troy's test, and status waits on Troy."""
        report = self.report("passed")
        self.assert_next(report, step="troy-test", **RELEASE_PR_NEXT)
        self.assertEqual(report["waiting_on_troy"], "PR #30: Waiting for Troy: accept v0.1.0")
        entry = report["open_prs"][0]
        self.assertEqual((entry["waiting_for_troy"], entry["troy_comments"]), (True, []))
        self.assertEqual(report["release"]["runs"],
                         [{"by": "claude", "run": 1, "result": "passed"}])
        self.assertEqual(report["release"]["checks"], [])

    def test_troys_reply_ends_the_wait_but_not_the_step(self):
        """A comment of Troy's after the request: no longer waiting, still Troy's test."""
        report = self.report("replied")
        self.assert_next(report, step="troy-test", **RELEASE_PR_NEXT)
        self.assertIsNone(report["waiting_on_troy"])
        self.assertEqual(report["open_prs"][0]["troy_comments"],
                         ["Looks fine so far, still testing on the laptop."])

    def test_troys_acceptance_goes_to_pm4(self):
        """``Release test by Troy, run 1: accepted``: PM4 sets the statuses, then the merge."""
        report = self.report("accepted")
        self.assert_next(report, step="accept", task="PM4", **RELEASE_PR_NEXT)
        self.assertEqual(report["open_prs"][0]["troy_comments"], [])
        self.assertEqual(report["release"]["runs"], [
            {"by": "claude", "run": 1, "result": "passed"},
            {"by": "troy", "run": 1, "result": "accepted"}])

    def test_failed_run_with_open_bugs_goes_to_triage(self):
        """Run 1 failed and bugs #15 and #12 are open: TM5 on B12, the lowest."""
        report = self.report("failed with bugs")
        self.assert_next(report, action="release", step="bugs", item="B12", tag=TAG, pr=30,
                         task="TM5", title=release_title(TAG), branch=RELEASE_BRANCH,
                         merged_by="f07")
        self.assertEqual(sorted(b["number"] for b in report["release"]["open_bugs"]), [12, 15])

    def test_troys_failed_test_with_a_bug_goes_to_triage(self):
        """Troy's run 1 failed and bug #17 is open: TM5 on B17."""
        report = self.report("troy failed")
        self.assert_next(report, action="release", step="bugs", item="B17", tag=TAG, pr=30,
                         task="TM5", title=release_title(TAG), branch=RELEASE_BRANCH,
                         merged_by="f07")

    def test_deferred_bug_does_not_stop_the_release_test(self):
        """Troy deferred #12, the only open bug: the release test runs again."""
        report = self.report("deferred")
        self.assert_next(report, step="release-test", **RELEASE_PR_NEXT)
        self.assertEqual(report["release"]["deferred"], [12])
        self.assertFalse(names_number(report["release"]["problems"], 12),
                         report["release"]["problems"])
        self.assertEqual(report["open_prs"][0]["troy_comments"], [])

    def test_failed_run_without_open_bugs_runs_again(self):
        """Run 1 failed and every bug is fixed: the release test again."""
        self.assert_next(self.report("fixed"), step="release-test", **RELEASE_PR_NEXT)

    def test_not_accepted_without_bugs_runs_again(self):
        """Troy did not accept and no bug is open: the release test again (note rule 10)."""
        report = self.report("not accepted")
        self.assert_next(report, step="release-test", **RELEASE_PR_NEXT)
        self.assertEqual(report["release"]["runs"][-1],
                         {"by": "troy", "run": 1, "result": "not accepted"})

    def test_the_last_record_decides(self):
        """Run 1 failed, run 2 passed: Troy's test."""
        report = self.report("rerun")
        self.assertEqual(report["next"]["step"], "troy-test")
        self.assertEqual(report["release"]["runs"], [
            {"by": "claude", "run": 1, "result": "failed"},
            {"by": "claude", "run": 2, "result": "passed"}])


class ReleasePrOrderTests(FlowCase):
    """Planted bug "the release PR continued before a bug's PR" (design 3.3, note rule 2)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per set of open PRs, side by side."""
        fix = pr(31, bug_title("B12", "fix", CRASH), bug_branch("B12", "fix"))
        tests_fix = pr(32, tests_title("v0.1", "Fix v0.1-S03"), "troy-mode/v0.1-tests-fix")
        cls.outs = fake_status_runs({
            "bug PR": release_case(FAILED, prs=[release_pr(30, TAG), fix],
                                   issues=[issue(12, CRASH)]),
            "tests fix": release_case(FAILED, prs=[tests_fix, release_pr(30, TAG)]),
            "stage PR": release_case(prs=[release_pr(30, TAG), stage_pr(35, F03V2, 1)]),
            "bug merged": release_case(FAILED, steps=TESTED + [bug_step("B12", "test", CRASH)],
                                       issues=[issue(12, CRASH)]),
            "tests PR": (ACCEPTED, {"prs": [pr(33, tests_title("v0.1"),
                                               "troy-mode/v0.1-tests")]}),
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def test_bug_pr_comes_before_the_release_pr(self):
        """Release PR #30 and PR B #31: PR B is continued by DV3."""
        self.assert_next(self.report("bug PR"), action="continue-pr", pr=31, item="B12",
                         task="DV3", title=bug_title("B12", "fix", CRASH),
                         branch=bug_branch("B12", "fix"), merged_by="f07")

    def test_version_tests_fix_comes_before_the_release_pr(self):
        """``[v0.1 tests] Fix v0.1-S03`` #32 is continued by TE3, for the version."""
        self.assert_next(self.report("tests fix"), action="continue-pr", pr=32, item="v0.1",
                         task="TE3", title=tests_title("v0.1", "Fix v0.1-S03"),
                         branch="troy-mode/v0.1-tests-fix", merged_by="f07")

    def test_stage_pr_comes_before_the_release_pr(self):
        """A stage PR #35 of F03 is continued although release PR #30 has the lower number."""
        self.assert_next(self.report("stage PR"), action="continue-pr", pr=35, item="F03",
                         stage=1, task="IF1", title=F03V2.title(1), branch=F03V2.branch(1),
                         merged_by="troy")

    def test_merged_bug_test_gets_its_fix_before_the_release(self):
        """B12's PR A merged while the release PR waits: PR B is next."""
        self.assert_next(self.report("bug merged"), action="bug", item="B12", task="DV3",
                         title=bug_title("B12", "fix", CRASH), branch="troy-mode/b12-fix",
                         merged_by="f07")

    def test_version_tests_pr_is_continued_by_te5(self):
        """An open ``[v0.1 tests]`` PR: TE5, with the version as the item."""
        self.assert_next(self.report("tests PR"), action="continue-pr", pr=33, item="v0.1",
                         task="TE5", title=tests_title("v0.1"), branch="troy-mode/v0.1-tests",
                         merged_by="f07")


class AfterReleaseTests(FlowCase):
    """``record-acceptance``, ``tag``, and ``retro`` (design 5.7, 7; note rules 4, 5, 8)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        unrecorded = TESTED + [release_step(TAG)]
        open_retro = dict(releases=[TAG], merged=[merged_pr(40, release_title(TAG))],
                          comments={40: comments("Code Reviewer review, round 1: approved")})
        two = (F01, F02)
        cls.outs = fake_status_runs({
            "record": (unrecorded, {}),
            "recorded": (unrecorded + [record_acceptance_step(TAG, ACCEPTED_PLAN)], {}),
            "tag": (RELEASED, {}),
            "squashed": (TESTED + [release_step(TAG, ACCEPTED_PLAN, pr=40)], {}),
            "tag before bug": (RELEASED + [bug_step("B14", "test", CRASH)], {}),
            "retro": (RELEASED, open_retro),
            "bug before retro": (RELEASED + [bug_step("B14", "test", CRASH)], open_retro),
            "retro done": (RELEASED, DONE_FAKES),
            "no merged PR": (RELEASED, dict(releases=[TAG])),
            "all released": ([base_step(files_of(two)), *stages(F01, 6), *stages(F02, 6),
                              version_tests_step("v0.1"), release_step(TAG, ACCEPTED_PLAN)],
                             DONE_FAKES),
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def release_commit(self, name: str, subject: str) -> str:
        """The full ID of the commit with this subject on the case clone's origin/main."""
        return subject_commits(self.outs[name][2])[subject]

    def test_merged_release_without_the_record_asks_pm4(self):
        """Troy merged on GitHub: the plan lacks the acceptance, so PM4 records it first."""
        self.assert_next(self.report("record"), action="record-acceptance", item="v0.1",
                         tag=TAG, task="PM4", title=record_title(TAG),
                         branch="troy-mode/record-v0.1.0", merged_by="f07", doc=PLAN1)

    def test_record_commit_ends_it_and_the_tag_follows(self):
        """After ``[docs] Record Troy's acceptance of v0.1.0``: the tag."""
        self.assert_next(self.report("recorded"), action="tag", item="v0.1", tag=TAG,
                         commit=self.release_commit("recorded", release_title(TAG)))

    def test_tag_names_the_release_commit(self):
        """No GitHub release for v0.1.0: the tag, on the release commit's full ID."""
        commit = self.release_commit("tag", release_title(TAG))
        self.assertRegex(commit, r"^[0-9a-f]{40}$")
        self.assert_next(self.report("tag"), action="tag", item="v0.1", tag=TAG, commit=commit)

    def test_squashed_release_commit_counts(self):
        """``[docs] Release v0.1.0 (#40)`` is v0.1.0's release commit."""
        commit = self.release_commit("squashed", release_title(TAG) + " (#40)")
        self.assert_next(self.report("squashed"), action="tag", item="v0.1", tag=TAG,
                         commit=commit)

    def test_tag_comes_before_a_bug(self):
        """B14's PR A merged after the release: the tag first (rule 5 before rule 6)."""
        self.assertEqual(self.report("tag before bug")["next"]["action"], "tag")

    def test_retro_after_the_tag(self):
        """Tagged, and release PR #40 has no ``Retrospective:`` comment: the retrospective."""
        self.assert_next(self.report("retro"), action="retro", item="v0.1", tag=TAG, pr=40,
                         title=release_title(TAG))

    def test_bug_comes_before_the_retro(self):
        """B14's PR A merged: PR B before the retrospective (rule 6 before rule 8)."""
        self.assert_next(self.report("bug before retro"), action="bug", item="B14", task="DV3",
                         title=bug_title("B14", "fix", CRASH), branch="troy-mode/b14-fix",
                         merged_by="f07")

    def test_retro_comment_ends_the_release(self):
        """With ``Retrospective: v0.1.0`` on #40, v0.2's F03 starts."""
        report = self.report("retro done")
        self.assert_next(report, action="stage", item="F03", stage=1, task="IF1",
                         title=F03V2.title(1), branch=F03V2.branch(1), merged_by="troy")
        self.assertEqual(report["release"]["tag"], "v0.2.0")

    def test_no_merged_release_pr_means_no_retro_and_a_note(self):
        """GitHub lists no merged ``[docs] Release v0.1.0`` PR: no retro, and a note says so."""
        report = self.report("no merged PR")
        self.assertEqual(report["next"]["action"], "stage")
        self.assertTrue(any(TAG in note for note in report["notes"]), report["notes"])

    def test_every_version_released(self):
        """Every feature accepted and v0.1 released, recorded, tagged, and reviewed: done."""
        report = self.report("all released")
        self.assert_next(report, action="all-accepted")
        self.assertIsNone(report["release"])


def fixes(*bugs: str) -> list:
    """PR A and PR B of each bug, in order."""
    return [item for bug in bugs for item in (bug_step(bug, "test", f"Bug {bug}"),
                                              bug_step(bug, "fix", f"Bug {bug}"))]


PATCHED = RELEASED + fixes("B14", "B9")


class PatchTests(FlowCase):
    """Patch releases (D75, note 3.1 ``patch``, 3.3)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        patch_plan = accepted_plan_files("v0.1", ["F01", "F02"], [TAG, "v0.1.1"])
        old_fix = TESTED + fixes("B4") + [release_step(TAG, ACCEPTED_PLAN)]
        cls.outs = fake_status_runs({
            "allowed": (PATCHED, DONE_FAKES),
            "docs of v0.2": (PATCHED + stages(F03V2, 2), DONE_FAKES),
            "blocked": (PATCHED + stages(F03V2, 3), DONE_FAKES),
            "impl": (PATCHED + stages(F03V2, 5), DONE_FAKES),
            "squashed": (PATCHED + stages(F03V2, 2) + [stage_step(F03V2, 3, "squash", 57)],
                         DONE_FAKES),
            "old fix": (old_fix, DONE_FAKES),
            "open patch": (PATCHED + stages(F03V2, 3),
                           {**DONE_FAKES, "prs": [release_pr(60, "v0.1.1")]}),
            "open, no fix": (RELEASED, {**DONE_FAKES, "prs": [release_pr(60, "v0.1.1")]}),
            "patch merged": (PATCHED + [release_step("v0.1.1", patch_plan)], DONE_FAKES),
            "patch tagged": (PATCHED + [release_step("v0.1.1", patch_plan)],
                             {**DONE_FAKES, "releases": [TAG, "v0.1.1"],
                              "merged": [merged_pr(40, release_title(TAG)),
                                         merged_pr(61, release_title("v0.1.1"))]}),
        })

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def test_versions_entries(self):
        """``versions``: v0.1 released with a patch allowed, v0.2 not started (note 3.1)."""
        self.assertEqual(self.report("allowed")["versions"], [
            {"version": "v0.1", "features": ["F01", "F02"], "accepted": True, "plan": PLAN1,
             "plan_features": ["F01", "F02"], "plan_matches": True, "released": [TAG],
             "patch": {"tag": "v0.1.1", "fixes": ["B14", "B9"], "blocked_by": [],
                       "allowed": True}},
            {"version": "v0.2", "features": ["F03"], "accepted": False, "plan": PLAN2,
             "plan_features": ["F03"], "plan_matches": True, "released": [], "patch": None}])

    def test_next_versions_documents_do_not_block(self):
        """F03's design and test plan merged since v0.1.0: the patch is still allowed."""
        patch = self.report("docs of v0.2")["versions"][0]["patch"]
        self.assertEqual((patch["blocked_by"], patch["allowed"]), ([], True))

    def test_later_versions_mock_blocks_the_patch(self):
        """Planted bug "patch allowed after later code": F03's mock merged since v0.1.0."""
        self.assertEqual(self.report("blocked")["versions"][0]["patch"],
                         {"tag": "v0.1.1", "fixes": ["B14", "B9"], "blocked_by": [MOCK_F03],
                          "allowed": False})

    def test_later_versions_implementation_blocks_the_patch(self):
        """Planted bug "patch allowed after later code": F03's mock, tests, and implementation
        merged since v0.1.0 are each listed, oldest first."""
        self.assertEqual(self.report("impl")["versions"][0]["patch"],
                         {"tag": "v0.1.1", "fixes": ["B14", "B9"],
                          "blocked_by": [MOCK_F03, F03V2.title(4), F03V2.title(5)],
                          "allowed": False})

    def test_squashed_later_code_blocks_by_its_subject(self):
        """``[F03 3/6 mock] Count characters (#57)`` is listed without `` (#57)``."""
        patch = self.report("squashed")["versions"][0]["patch"]
        self.assertEqual((patch["blocked_by"], patch["allowed"]), ([MOCK_F03], False))

    def test_fixes_before_the_release_do_not_count(self):
        """B4 was fixed before v0.1.0: no fix since, so no patch."""
        patch = self.report("old fix")["versions"][0]["patch"]
        self.assertEqual(patch, {"tag": "v0.1.1", "fixes": [], "blocked_by": [],
                                 "allowed": False})

    def test_open_patch_release_names_the_later_code(self):
        """Release PR #60 for v0.1.1 with F03's mock merged: a problem names the mock."""
        report = self.report("open patch")
        self.assert_next(report, action="release", step="release-test", item="v0.1",
                         tag="v0.1.1", pr=60, title=release_title("v0.1.1"),
                         branch="troy-mode/release-v0.1.1", merged_by="f07")
        release = report["release"]
        self.assertEqual((release["tag"], release["patch"], release["version"]),
                         ("v0.1.1", True, "v0.1"))
        self.assertTrue(named(release["problems"], MOCK_F03), release["problems"])

    def test_patch_without_fixes_is_a_problem(self):
        """Release PR #60 for v0.1.1 and no fix since v0.1.0: the note's sentence."""
        problems = self.report("open, no fix")["release"]["problems"]
        self.assertIn("No bug fix has merged since v0.1.0.", problems)

    def test_merged_patch_gets_its_tag(self):
        """``[docs] Release v0.1.1`` merged and accepted, no GitHub release yet: its tag."""
        commit = subject_commits(self.outs["patch merged"][2])[release_title("v0.1.1")]
        self.assert_next(self.report("patch merged"), action="tag", item="v0.1", tag="v0.1.1",
                         commit=commit)

    def test_patch_has_no_retrospective(self):
        """v0.1.1 tagged and its PR #61 has no retrospective: none is asked; F03 starts."""
        report = self.report("patch tagged")
        self.assert_next(report, action="stage", item="F03", stage=1, task="IF1",
                         title=F03V2.title(1), branch=F03V2.branch(1), merged_by="troy")
        self.assertEqual(report["versions"][0]["released"], [TAG, "v0.1.1"])
        self.assertEqual(report["versions"][0]["patch"]["tag"], "v0.1.2")


class GhCallTests(FlowCase):
    """The new gh calls happen only when the note's section 1 says."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        cls.outs = fake_status_runs({
            "feature work": ([BASE, *stages(F01, 6), *stages(F02, 5)], {}),
            "ready": (ACCEPTED, {}),
            "released": (RELEASED, DONE_FAKES),
            "release PR": release_case(PASSED, WAITING),
        })

    def calls(self, name: str) -> list:
        """The sorted argument lists of the case's gh calls; the run must be fine."""
        out, fakes, _ = self.outs[name]
        self.report_of(out, 0, "status")
        return sorted(fakes.gh_argvs())

    def test_feature_work_lists_open_prs_only(self):
        """A version not accepted, no release commit: only ``gh pr list --state open``."""
        self.assertEqual(self.calls("feature work"), [LIST_ARGS])

    def test_accepted_version_reads_the_open_bugs(self):
        """Every feature of v0.1 accepted: the open bug issues too, and no release list."""
        self.assertEqual(self.calls("ready"), sorted([LIST_ARGS, ISSUE_ARGS]))

    def test_released_version_reads_releases_and_merged_prs(self):
        """A release commit with a GitHub release: releases, merged PRs, and #40's comments."""
        self.assertEqual(self.calls("released"),
                         sorted([LIST_ARGS, RELEASE_ARGS, MERGED_ARGS,
                                 ["pr", "view", "40", "--json", "comments"]]))

    def test_open_release_pr_reads_its_comments_and_the_bugs(self):
        """The open release PR: its comments and the open bugs; no release commit yet."""
        self.assertEqual(self.calls("release PR"),
                         sorted([LIST_ARGS, ["pr", "view", "30", "--json", "comments"],
                                 ISSUE_ARGS]))

    def test_gh_failure_on_a_new_call_exits_two(self):
        """A failing release list, merged PR list, or bug issue list stops status (exit 2)."""
        cases = {
            "release list": (RELEASED, ["release", "list"]),
            "merged PRs": (RELEASED, ["pr", "list", "--state", "merged"]),
            "bug issues": (ACCEPTED, ["issue", "list"]),
        }

        def run(case):
            """Runs status with one gh call failing."""
            steps, prefix = case
            return Project(steps).status(fakes=Fakes(**DONE_FAKES, fail_calls=[prefix]))
        names = list(cases)
        for name, out in zip(names, parallel(run, [cases[n] for n in names])):
            with self.subTest(call=name):
                self.assert_exit(out, 2)


class ReleaseProgressTests(FlowCase):
    """The progress file for a release action (note 3.4)."""

    def test_stage_line_and_current_version(self):
        """``Stage: none. ...`` and Current version naming v0.1 and its features."""
        project = Project(ACCEPTED)
        out = project.status("--write-progress", fakes=Fakes())
        self.report_of(out, 0, "status")
        fields = progress_fields(project.read(PROGRESS))
        self.assertTrue(fields["Stage"].startswith("none. "), fields["Stage"])
        self.assertNotEqual(fields["Next action"], "")
        self.assertEqual(fields["Stage"], "none. " + fields["Next action"])
        current = fields["Current version"]
        for text in ("v0.1", "F01", "F02"):
            self.assertIn(text, current)
        self.assertNotIn("F03", current)


if __name__ == "__main__":
    unittest.main()
