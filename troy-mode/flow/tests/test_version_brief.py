"""Briefs for a version item (F08 design 4, 5.3, 11.1; interface note sections 6 and 9).

TM7 writes the version test plan, TE5 the version tests, and TE3, TM2, CR1,
TM4, and AR5 work on a ``[vX.Y tests]`` PR. The tests check the allowed and
refused tasks, the title, Read first, and the checks with the release
command for Python and C/C++.
"""

import unittest
from dataclasses import replace

from flow_helpers import (
    ARCHITECTURE, F01, F02, F03, REQUIREMENTS, RULES, Fakes, FlowCase, Project, base_files,
    base_step, option_value, pack_words, parallel, plan_title, stages, tests_title,
    troy_check_step, version_plan_files, version_plan_path,
)

F03V2 = replace(F03, version="v0.2")
THREE = (F01, F02, F03V2)
PLAN1 = version_plan_path("v0.1")
PLAN2 = version_plan_path("v0.2")
PROTOTYPE = "docs/prototypes/main-screen.md"
FIELDS = ("Task: ", "Item: ", "Read first:", "Input:", "Round: ", "Checks to run:")
ROLE_OF = {"TM": "test-manager", "TE": "test-engineer", "CR": "code-reviewer", "AR": "architect"}
ALLOWED = ("TM7", "TE5", "TE3", "TM2", "CR1", "TM4", "AR5")
REFUSED = ("TE1", "DV1", "DV2", "DV3", "TM1", "IF1", "TE2", "TM5", "AR4", "PM4")
CODE_TASKS = ("TE5", "TE3", "TM2", "CR1", "TM4")
WORKTREE_TASKS = ("TE5", "TE3")
TESTS_TITLE = tests_title("v0.1")
PY_RELEASE = ["pytest", "version-tests", "--junitxml=reports/version-junit.xml", "||", "true"]
CPP_RELEASE = [["cmake", "--preset", "coverage", "-DTROY_VERSION_TESTS=ON"],
               ["cmake", "--build", "--preset", "coverage"],
               ["ctest", "--preset", "coverage", "-L", "version", "--output-junit",
                "$PWD/reports/version-junit.xml", "||", "true"]]
TROY_ONLY = version_plan_files("v0.1", ["F01", "F02"], scenarios=[
    ("v0.1-S01", "Count on Troy's laptop", "Troy", "Run wc notes.txt", "Prints the count")],
    perf=[])
_PROJECTS: dict = {}


def shared(name: str) -> Project:
    """A clone shared by the tests that only read it, built on first use.

    Args:
        name: ``planned`` (plans for v0.1 and v0.2, a prototype, F01 and F02
            accepted), ``unplanned`` (no plan, no prototype), ``troyonly``
            (v0.1's plan has no scenario Claude runs), or ``cpp`` (as
            ``planned``, with the C/C++ pack).

    Returns:
        The clone. Tests must not change it.
    """
    if name not in _PROJECTS:
        prototype = {PROTOTYPE: "# Main screen\n"}
        if name == "planned":
            files = base_files(THREE, extra=prototype)
        elif name == "unplanned":
            files = base_files(THREE, plans=False)
        elif name == "troyonly":
            files = base_files(THREE, extra=TROY_ONLY)
        elif name == "cpp":
            files = base_files(THREE, lang="cpp", extra=prototype)
        else:
            raise KeyError(name)
        _PROJECTS[name] = Project([base_step(files), *stages(F01, 6), *stages(F02, 6)])
    return _PROJECTS[name]


def brief(case) -> object:
    """Runs ``brief --task <task> --item <item> [--title <title>] --json``.

    Args:
        case: ``(clone name, task, item, title or None)``.

    Returns:
        The outcome.
    """
    name, task, item, title = case
    args = ["brief", "--task", task, "--item", item]
    if title is not None:
        args += ["--title", title]
    return shared(name).run(*args)


def run_briefs(cases) -> list:
    """Runs several briefs side by side; builds the clones first."""
    for name in sorted({case[0] for case in cases}):
        shared(name)
    return parallel(brief, cases)


def line_of(report: dict, prefix: str) -> str:
    """The prompt's first line that starts with a prefix, or ""."""
    lines = (report.get("prompt") or "").split("\n")
    return next((line for line in lines if line.startswith(prefix)), "")


def python_rests() -> list:
    """The Python pack's steps after ``<mamba> run <target>``, before troy-check."""
    return [["ruff", "check"], ["ruff", "format", "--check"], ["mypy"],
            ["coverage", "run", "-m", "pytest", "--junitxml=reports/junit.xml", "||", "true"],
            ["coverage", "xml", "-o", "reports/coverage.xml"]]


class VersionTaskTests(FlowCase):
    """Allowed and refused tasks for ``--item v0.1`` (note section 9)."""

    @classmethod
    def setUpClass(cls):
        """Runs every task once on the planned clone, side by side."""
        tasks = ALLOWED + REFUSED
        cls.outs = dict(zip(tasks, run_briefs([("planned", t, "v0.1", None) for t in tasks])))

    def report(self, task: str) -> dict:
        """The report of an allowed task, which must have exit code 0."""
        return self.report_of(self.outs[task], 0, "brief")

    def test_allowed_tasks_get_a_brief(self):
        """Each allowed task: its role, subagent, the version as the item, no stage, a title."""
        titles = {"TM7": plan_title("v0.1", update=True)}
        for task in ALLOWED:
            with self.subTest(task=task):
                report = self.report(task)
                role = ROLE_OF[task[:2]]
                self.assertEqual((report["task"], report["role"], report["item"],
                                  report["stage"]), (task, role, "v0.1", None))
                self.assertEqual(report["agent"], {"subagent_type": f"tstack:troy-{role}"})
                self.assertEqual(report["title"], titles.get(task, TESTS_TITLE))
                self.assertEqual(line_of(report, "Item: "), f"Item: v0.1, {report['title']}")
                found = [next((i for i, line in enumerate(report["prompt"].split("\n"))
                               if line.startswith(p)), None) for p in FIELDS]
                self.assertNotIn(None, found, report["prompt"])
                self.assertEqual(found, sorted(found), report["prompt"])

    def test_other_tasks_are_refused(self):
        """Feature, bug, and Product Manager tasks: exit 1, a problem, and no brief."""
        self.report("TE5")
        for task in REFUSED:
            with self.subTest(task=task):
                report = self.report_of(self.outs[task], 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"))

    def test_read_first_for_the_version_tests(self):
        """Rules, requirements, architecture, the plan, then F01's and F02's designs."""
        for task in ("TE5", "TE3", "TM2", "CR1", "TM4", "AR5"):
            with self.subTest(task=task):
                self.assertEqual(self.report(task)["read_first"],
                                 [RULES, REQUIREMENTS, ARCHITECTURE, PLAN1, F01.design,
                                  F02.design])

    def test_requirements_line_names_the_version_and_its_plan(self):
        """The requirements line names v0.1 and the version plan."""
        line = line_of(self.report("TE5"), f"- {REQUIREMENTS}")
        self.assertIn("v0.1", line)
        self.assertIn("version plan", line.lower())

    def test_tm7_reads_the_test_plans_and_prototypes_too(self):
        """TM7 also reads each feature's test plan and ``docs/prototypes/``."""
        read = self.report("TM7")["read_first"]
        self.assertEqual(read[:4], [RULES, REQUIREMENTS, ARCHITECTURE, PLAN1])
        normalized = [path.rstrip("/") for path in read]
        self.assertEqual(sorted(normalized),
                         sorted([RULES, REQUIREMENTS, ARCHITECTURE, PLAN1, F01.design,
                                 F02.design, F01.plan, F02.plan, "docs/prototypes"]))
        self.assertLess(read.index(F01.design), read.index(F02.design))
        self.assertLess(read.index(F01.plan), read.index(F02.plan))

    def test_tm7_task_names_the_features_and_run_by(self):
        """TM7's Task line names F01, F02, and the Run by column, and not F03."""
        task_line = line_of(self.report("TM7"), "Task: ")
        for text in ("F01", "F02", "Run by"):
            self.assertIn(text, task_line)
        self.assertNotIn("F03", task_line)

    def test_te5_task_names_the_folder_and_the_test_names(self):
        """TE5's Task line names ``version-tests/`` and names that start with the scenario ID."""
        task_line = line_of(self.report("TE5"), "Task: ")
        self.assertIn("version-tests/", task_line)
        self.assertIn("v0_1_s01", task_line.lower())

    def test_tm2_task_checks_the_scenarios(self):
        """TM2's Task line for a version item is about the plan's scenarios."""
        self.assertIn("scenario", line_of(self.report("TM2"), "Task: ").lower())

    def test_document_tasks_have_no_checks(self):
        """TM7 and AR5 run no checks."""
        for task in ("TM7", "AR5"):
            with self.subTest(task=task):
                report = self.report(task)
                self.assertEqual(report["checks"], [])
                self.assertIn("Checks to run: None", report["prompt"].split("\n"))

    def test_code_tasks_check_with_the_release_command(self):
        """The Python steps, troy-check with the title, then the version tests (note 6)."""
        for task in CODE_TASKS:
            with self.subTest(task=task):
                checks = self.report(task)["checks"]
                self.assertEqual(len(checks), 7, checks)
                for command, rest in zip(checks, python_rests()):
                    self.assertEqual(pack_words(command)[1:], (["-n", "wordcount"], rest))
                words = troy_check_step(checks)
                self.assertEqual(words[1:3], [".troy-mode/checks/troy_check.py", "code"])
                self.assertEqual(option_value(words, "--title"), TESTS_TITLE)
                self.assertEqual(option_value(words, "--base"), "origin/main")
                self.assertEqual("--worktree" in words, task in WORKTREE_TASKS, words)
                self.assertEqual(pack_words(checks[-1])[1:], (["-n", "wordcount"], PY_RELEASE))
                self.assertIn(f"- {checks[-1]}", self.report(task)["prompt"].split("\n"))


class VersionTitleTests(FlowCase):
    """``--title`` and the plan's state decide the title, or refuse (note section 9)."""

    @classmethod
    def setUpClass(cls):
        """Runs every case side by side."""
        cls.cases = {
            "TM7 without a plan": ("unplanned", "TM7", "v0.1", None),
            "TM7 with its docs title": ("planned", "TM7", "v0.1", plan_title("v0.1")),
            "TE3 with a fix title": ("planned", "TE3", "v0.1",
                                     tests_title("v0.1", "Fix v0.1-S03")),
            "TE5 for v0.2": ("planned", "TE5", "v0.2", None),
            "TM7 on a plan Troy runs": ("troyonly", "TM7", "v0.1", None),
            "TE5 of another version": ("planned", "TE5", "v0.1", tests_title("v0.2")),
            "TM7 with a tests title": ("planned", "TM7", "v0.1", TESTS_TITLE),
            "TE5 with a docs title": ("planned", "TE5", "v0.1", plan_title("v0.1")),
            "CR1 with a stage title": ("planned", "CR1", "v0.1", F01.title(4)),
            "TM2 with a bug title": ("planned", "TM2", "v0.1",
                                     "[B12 A/B test] Crash on empty history"),
            "TM7 for a version without features": ("planned", "TM7", "v0.3", None),
            "TE5 for a version without features": ("planned", "TE5", "v0.3", None),
            "TE5 without a plan": ("unplanned", "TE5", "v0.1", None),
            "TE5 when Troy runs every scenario": ("troyonly", "TE5", "v0.1", None),
        }
        names = list(cls.cases)
        cls.outs = dict(zip(names, run_briefs([cls.cases[n] for n in names])))

    def test_tm7_without_a_plan_adds_it(self):
        """No plan on origin/main: ``[docs] Add the v0.1 test plan``, and Read first has no
        plan and no prototypes folder."""
        report = self.report_of(self.outs["TM7 without a plan"], 0, "brief")
        self.assertEqual(report["title"], plan_title("v0.1"))
        self.assertEqual(sorted(report["read_first"]),
                         sorted([RULES, REQUIREMENTS, ARCHITECTURE, F01.design, F02.design,
                                 F01.plan, F02.plan]))
        self.assertEqual(report["read_first"][:3], [RULES, REQUIREMENTS, ARCHITECTURE])

    def test_titles_that_fit(self):
        """A ``[docs]`` title for TM7, a ``[v0.1 tests]`` fix title for TE3."""
        for name in ("TM7 with its docs title", "TE3 with a fix title"):
            with self.subTest(case=name):
                report = self.report_of(self.outs[name], 0, "brief")
                self.assertEqual(report["title"], self.cases[name][3])
        words = troy_check_step(self.report_of(self.outs["TE3 with a fix title"])["checks"])
        self.assertEqual(option_value(words, "--title"), tests_title("v0.1", "Fix v0.1-S03"))
        self.assertIn("--worktree", words)

    def test_te5_for_the_next_version(self):
        """v0.2 has a plan with a Claude scenario and F03 has no design yet."""
        report = self.report_of(self.outs["TE5 for v0.2"], 0, "brief")
        self.assertEqual((report["item"], report["title"]), ("v0.2", tests_title("v0.2")))
        self.assertEqual(report["read_first"], [RULES, REQUIREMENTS, ARCHITECTURE, PLAN2])

    def test_tm7_on_a_plan_troy_runs(self):
        """TM7 needs no scenario Claude runs."""
        self.report_of(self.outs["TM7 on a plan Troy runs"], 0, "brief")

    def test_refused(self):
        """Another version's or kind's title, a version without features, TE5 without a plan
        or without a scenario Claude runs: exit 1 and no brief."""
        self.report_of(self.outs["TE3 with a fix title"], 0, "brief")
        for name in ("TE5 of another version", "TM7 with a tests title", "TE5 with a docs title",
                     "CR1 with a stage title", "TM2 with a bug title",
                     "TM7 for a version without features", "TE5 for a version without features",
                     "TE5 without a plan", "TE5 when Troy runs every scenario"):
            with self.subTest(case=name):
                report = self.report_of(self.outs[name], 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"))


class CppVersionBriefTests(FlowCase):
    """The C/C++ pack: cmake first, troy-check with Doxygen, then the release steps."""

    def test_te5_checks(self):
        """TE5 in a C/C++ project ends with the three release steps of note section 6."""
        fakes = Fakes(fail=True)
        report = self.report_of(shared("cpp").run("brief", "--task", "TE5", "--item", "v0.1",
                                                  fakes=fakes), 0, "brief")
        checks = report["checks"]
        self.assertEqual(pack_words(checks[0])[2], ["cmake", "--preset", "coverage"])
        self.assertEqual([pack_words(c)[2] for c in checks[-3:]], CPP_RELEASE)
        words = troy_check_step(checks)
        self.assertEqual(words, pack_words(checks[-4])[2])
        self.assertEqual(option_value(words, "--title"), TESTS_TITLE)
        self.assertEqual(option_value(words, "--doc-warnings"), "reports/doxygen.log")
        self.assertIn("--worktree", words)
        self.assertEqual(fakes.gh_calls(), [])

    def test_cr1_checks_without_worktree(self):
        """CR1 reviews the commit: no ``--worktree``; the release steps still end the list."""
        report = self.report_of(shared("cpp").run("brief", "--task", "CR1", "--item", "v0.1"),
                                0, "brief")
        self.assertNotIn("--worktree", troy_check_step(report["checks"]))
        self.assertEqual([pack_words(c)[2] for c in report["checks"][-3:]], CPP_RELEASE)


if __name__ == "__main__":
    unittest.main()
