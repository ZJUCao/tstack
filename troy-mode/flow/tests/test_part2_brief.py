"""Brief in part 2 (F07 design 3.1, 6.1, 8.6 D69, 8.7, 11.1, 11.2, 14.1; part 2 note, brief).

Every row of the note's "Allowed tasks" table, with allowed and refused
tasks, ``--title`` and its checks, the derived title of a bug's PR B, the
bug's Read first, the ``Item:`` line, the checks of the code tasks, and the
Task line of D69.

Planted bugs of design 14.2 caught here:

- "a code task without ``--worktree``": ``AllowedTasksTests.test_code_tasks_check_with_the_title``
  and ``ChecksTests.test_dv3_runs_the_python_steps_with_worktree``.
- "a fixed bug given a brief": ``RefusedTests.test_fixed_bug_refuses_every_task``.
- "PR B offered before PR A merged" (for briefs): ``AllowedTasksTests`` row "bug A", where DV3
  is refused.
"""

import json
import re
import unittest

from flow_helpers import (
    ARCHITECTURE, ARCHITECTURE_ZH, F01, F02, REQUIREMENTS, RULES, FlowCase, Project, base_files,
    base_step, bug_step, bug_title, change_step, custom_design, custom_design_step,
    option_value, pack_words, parallel, rework, split_command, stage_step, stages,
    troy_check_step,
)

D69 = ("A test that the test plan runs only on another platform is skipped here, and "
       "troy-check code reports it under R09 or R10; CI checks it, so name it in your report "
       "and do not count it as a failure.")
CODE_TASKS = frozenset(("DV1", "DV2", "DV3", "DV4", "TE1", "TE2", "TE3", "TE4", "TM2", "TM3",
                        "TM4", "CR1"))
WORKTREE_TASKS = frozenset(("DV1", "DV2", "DV3", "DV4", "TE1", "TE2", "TE3", "TE4"))
ROLE_OF = {"AR": "architect", "IF": "interface-designer", "TM": "test-manager",
           "DV": "developer", "TE": "test-engineer", "CR": "code-reviewer"}
FIELDS = ("Task: ", "Item: ", "Read first:", "Input:", "Round: ", "Checks to run:")
PREFIX = "/scratch/troy-env"
NO_APPROVALS = "[flow]\ntroy_approves_first = 0\n"
CRASH = "Crash on empty history"
TEST_FIX_F01 = "[F01 test-fix] Wrong count in F01-T01"
DOCS_F01 = "[docs] Add cases to the F01 test plan"
B12_TEST = bug_title("B12", "test", CRASH)
B12_FIX = bug_title("B12", "fix", CRASH)
B12_TEST_FIX = "[B12 test-fix] Wrong fixture in the B12 test"
B12_DOCS = "[docs] Explain the empty history case"
SKIP = object()
_PROJECTS: dict = {}


def shared(name: str) -> Project:
    """A clone shared by the tests that only read it, built on first use.

    Args:
        name: ``stage1`` to ``stage5`` (F01's current stage, no bug),
            ``accepted`` (F01 accepted, F02 at stage 3), ``bugB`` (B12's PR A
            merged as a squash, no mock merged yet), ``fixed`` (B12's PR A and
            PR B merged), ``rework`` (F01's 1 to 3 merged, then a change that
            marks it), ``skipped`` (F01's 1 and 2 merged, a design without an
            interface), ``nolang`` (no ``[lang]``, B12's PR A merged), or
            ``cppbug`` (the C/C++ pack, B12's PR A merged).

    Returns:
        The clone. Tests must not change it.
    """
    if name not in _PROJECTS:
        test_b12 = bug_step("B12", "test", CRASH)
        if name.startswith("stage"):
            steps = [base_step(), *stages(F01, int(name[-1]) - 1)]
        elif name == "accepted":
            steps = [base_step(), *stages(F01, 6), *stages(F02, 2)]
        elif name == "bugB":
            steps = [base_step(), *stages(F01, 2), bug_step("B12", "test", CRASH, pr=31)]
        elif name == "fixed":
            steps = [base_step(), *stages(F01, 2), test_b12, bug_step("B12", "fix", CRASH)]
        elif name == "rework":
            steps = [base_step(), *stages(F01, 3), change_step(features=(rework(F01), F02))]
        elif name == "skipped":
            design = custom_design(F01, "None. The change adds no interface.\n")
            steps = [base_step(base_files(config_extra=NO_APPROVALS)),
                     custom_design_step(F01, design), stage_step(F01, 2)]
        elif name == "nolang":
            steps = [base_step(base_files(lang=None)), *stages(F01, 2), test_b12]
        elif name == "cppbug":
            steps = [base_step(base_files(lang="cpp")), test_b12]
        else:
            raise KeyError(name)
        _PROJECTS[name] = Project(steps)
    return _PROJECTS[name]


def brief(project: Project, task: str, item: str, title=None, env_extra=None):
    """Runs ``brief --task <task> --item <item> [--title <title>] --json`` on a clone.

    Args:
        project: The clone.
        task: The task ID.
        item: The feature or bug ID.
        title: The ``--title`` value, or None to leave it out.
        env_extra: More environment variables.

    Returns:
        The outcome.
    """
    args = ["brief", "--task", task, "--item", item]
    if title is not None:
        args += ["--title", title]
    return project.run(*args, env_extra=env_extra)


def run_briefs(cases) -> list:
    """Runs several briefs side by side on shared clones.

    Args:
        cases: ``(clone name, item, title or None, task)`` tuples.

    Returns:
        The outcomes, in the order of the cases.
    """
    for name in sorted({case[0] for case in cases}):
        shared(name)
    return parallel(lambda case: brief(shared(case[0]), case[3], case[1], case[2]), cases)


def python_rests(install: bool) -> list:
    """The Python pack's steps after ``<mamba> run <target>``, without troy-check's step.

    Args:
        install: Whether the editable install of the first mock comes first.

    Returns:
        The word lists, in order.
    """
    rests = [["uv", "pip", "install", "-e", ".", "--no-deps"]] if install else []
    return rests + [["ruff", "check"], ["ruff", "format", "--check"], ["mypy"],
                    ["coverage", "run", "-m", "pytest", "--junitxml=reports/junit.xml", "||",
                     "true"],
                    ["coverage", "xml", "-o", "reports/coverage.xml"]]


def line_of(report: dict, prefix: str) -> str:
    """The prompt's first line that starts with a prefix, or "" when there is none."""
    lines = (report.get("prompt") or "").split("\n")
    return next((line for line in lines if line.startswith(prefix)), "")


def problems_text(report: dict) -> str:
    """The report's problems as one text, for searching."""
    return json.dumps(report.get("problems"), ensure_ascii=False)


# (label, clone, item, title, allowed tasks, refused tasks, stage, title in the report)
ROWS = [
    ("stage 1", "stage1", "F01", None, ("IF1", "IF2", "AR2", "AR5", "AR3", "AR4"),
     ("TM1", "DV1", "TE3", "TM4", "DV3", "TM5", "IF4"), 1, F01.title(1)),
    ("stage 2", "stage2", "F01", None, ("TM1", "IF3", "AR5", "AR3", "AR4"),
     ("IF1", "IF2", "DV1", "TM2", "TM6"), 2, F01.title(2)),
    ("stage 3", "stage3", "F01", None, ("DV1", "CR1", "AR5", "AR3", "AR4"),
     ("TE1", "TM2", "IF4", "DV4", "DV3", "TE2"), 3, F01.title(3)),
    ("stage 4", "stage4", "F01", None, ("TE1", "TM2", "CR1", "AR5", "AR3", "AR4"),
     ("DV1", "DV2", "TE2", "TE3", "TM3", "TM1"), 4, F01.title(4)),
    ("stage 5", "stage5", "F01", None,
     ("DV2", "CR1", "AR5", "AR3", "AR4", "TM3", "TM4", "TM6", "IF4", "DV4"),
     ("TE1", "DV1", "TE4", "TE3", "TM5", "DV3", "TM2"), 5, F01.title(5)),
    ("accepted", "accepted", "F01", None, ("AR4",), ("AR5", "AR3", "CR1", "IF1", "DV2"),
     None, None),
    ("feature test-fix", "stage5", "F01", TEST_FIX_F01,
     ("TE3", "TE4", "TM2", "CR1", "AR3", "AR5"), ("DV2", "TM1", "IF2", "TE1", "AR4", "DV4"),
     5, TEST_FIX_F01),
    ("feature docs", "stage5", "F01", DOCS_F01,
     ("TM1", "IF2", "AR2", "IF3", "AR3", "AR4", "AR5"), ("DV2", "IF1", "TE3", "CR1", "TM6"),
     5, DOCS_F01),
    ("bug A", "stage3", "B12", None, ("TM5", "AR3", "AR5"),
     ("DV3", "TE3", "TM4", "DV1", "IF1", "AR4"), None, None),
    ("bug A test", "stage3", "B12", B12_TEST, ("TE2", "TM2", "CR1", "AR3", "AR5"),
     ("DV3", "TM5", "TE3", "TM4"), None, B12_TEST),
    ("bug A docs", "stage3", "B12", B12_DOCS, ("AR3", "AR5"), ("TM5", "TE2"), None, B12_DOCS),
    ("bug B", "bugB", "B12", None, ("DV3", "CR1", "TM4", "AR3", "AR5"),
     ("TE2", "TM5", "TE3", "DV1", "TM2"), None, B12_FIX),
    ("bug B fix", "bugB", "B12", B12_FIX, ("DV3", "CR1", "TM4", "AR3", "AR5"),
     ("TE2", "TE3", "TM2", "TM5"), None, B12_FIX),
    ("bug B test-fix", "bugB", "B12", B12_TEST_FIX, ("TE3", "TM2", "CR1", "AR3", "AR5"),
     ("DV3", "TE4", "TM4", "TE2"), None, B12_TEST_FIX),
    ("bug B docs", "bugB", "B12", B12_DOCS, ("AR3", "AR5"), ("TM1", "IF2", "DV3", "CR1"),
     None, B12_DOCS),
]


class AllowedTasksTests(FlowCase):
    """The part 2 note's "Allowed tasks" table, row by row."""

    @classmethod
    def setUpClass(cls):
        """Runs one brief per allowed and refused task of every row, side by side."""
        cases, cls.allowed, cls.refused = [], [], []
        for label, clone, item, title, allowed, refused, stage, want_title in ROWS:
            for task in allowed:
                cls.allowed.append((label, item, task, stage, want_title, len(cases)))
                cases.append((clone, item, title, task))
            for task in refused:
                cls.refused.append((label, task, len(cases)))
                cases.append((clone, item, title, task))
        cls.outs = run_briefs(cases)

    def each_allowed(self, check, only=None) -> None:
        """Calls a check on the report of every allowed task, each in its own subtest.

        Args:
            check: A function of ``(label, item, task, stage, title, report)``
                that asserts; the report must already have exit 0.
            only: A function of ``(label, item, task)`` that picks the cases,
                or None for all.
        """
        for label, item, task, stage, want_title, index in self.allowed:
            if only is not None and not only(label, item, task):
                continue
            with self.subTest(row=label, task=task):
                report = self.report_of(self.outs[index], 0, "brief")
                check(label, item, task, stage, want_title, report)

    def test_allowed_tasks_get_a_brief(self):
        """Each allowed task: its role, subagent, item, stage, and title, and the six fields."""
        def check(label, item, task, stage, want_title, report):
            """Asserts the report's keys and the order of the prompt's fields."""
            role = ROLE_OF[task[:2]]
            self.assertEqual((report["task"], report["role"], report["item"], report["stage"]),
                             (task, role, item, stage))
            self.assertEqual(report["agent"], {"subagent_type": f"troy-pstack:troy-{role}"})
            if not (label.startswith("stage") and task == "AR4"):
                self.assertEqual(report["title"], want_title)
            lines = report["prompt"].split("\n")
            found = [next((i for i, line in enumerate(lines) if line.startswith(p)), None)
                     for p in FIELDS]
            self.assertNotIn(None, found, report["prompt"])
            self.assertEqual(found, sorted(found), report["prompt"])
            self.assertTrue(line_of(report, "Task: ").startswith(f"Task: {task}"),
                            line_of(report, "Task: "))
        self.each_allowed(check)

    def test_other_tasks_are_refused(self):
        """Each task the row does not allow: exit 1, a problem, and no brief."""
        for label, task, index in self.refused:
            with self.subTest(row=label, task=task):
                report = self.report_of(self.outs[index], 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"), "a refused task has no brief")

    def test_item_line_holds_the_id_and_the_title(self):
        """``Item: <ID>, <title>``, or the ID alone when the title is null."""
        def check(label, item, task, stage, want_title, report):
            """Asserts the Item line from the report's own title."""
            want = f"Item: {item}, {report['title']}" if report["title"] else f"Item: {item}"
            self.assertEqual(line_of(report, "Item: "), want)
        self.each_allowed(check)

    def test_code_tasks_check_with_the_title(self):
        """Planted bug "a code task without --worktree": troy-check gets the brief's title, and
        ``--worktree`` exactly for DV1 to DV4 and TE1 to TE4.

        ``ROWS`` allows each of the twelve code tasks in at least one row.
        """
        def check(label, item, task, stage, want_title, report):
            """Asserts the troy-check step of one code task."""
            self.assertGreater(len(report["checks"]), 1, report["checks"])
            words = troy_check_step(report["checks"])
            self.assertEqual(words[1:3], [".troy-mode/checks/troy_check.py", "code"])
            self.assertEqual(option_value(words, "--title"), report["title"])
            self.assertEqual("--worktree" in words, task in WORKTREE_TASKS, words)
            self.assertNotIn("Checks to run: None", report["prompt"].split("\n"))
        self.each_allowed(check, lambda label, item, task: task in CODE_TASKS)

    def test_tm2_on_a_bug_reviews_against_the_bug_report(self):
        """A bug has no test plan: TM2 on PR A checks the tests against the bug report.

        On a feature's tests PR and on a test fix, TM2 still reviews against the test plan.
        """
        def check(label, item, task, stage, want_title, report):
            """Asserts which document TM2's Task line names."""
            task_line = line_of(report, "Task: ")
            if label == "bug A test":
                self.assertIn("bug report", task_line)
                self.assertNotIn("test plan", task_line.split(". A test that")[0])
            else:
                self.assertIn("against its test plan", task_line)
        self.each_allowed(check, lambda label, item, task: task == "TM2")

    def test_other_tasks_have_no_checks(self):
        """TM1, TM5, TM6, IF*, and AR* run no checks."""
        def check(label, item, task, stage, want_title, report):
            """Asserts that the brief has no checks."""
            self.assertEqual(report["checks"], [])
            self.assertIn("Checks to run: None", report["prompt"].split("\n"))
        self.each_allowed(check, lambda label, item, task: task not in CODE_TASKS)

    def test_task_line_tells_code_tasks_about_platform_skips(self):
        """D69: every code task's Task line holds the sentence; no other task's names it."""
        def check(label, item, task, stage, want_title, report):
            """Asserts the Task line's D69 sentence, or its absence."""
            task_line = line_of(report, "Task: ")
            if task in CODE_TASKS:
                self.assertIn(D69, task_line)
            else:
                self.assertNotIn("another platform", task_line)
        self.each_allowed(check)

    def test_bug_reads_rules_requirements_and_architecture(self):
        """A bug's Read first, and its requirements line names no feature's row."""
        def check(label, item, task, stage, want_title, report):
            """Asserts a bug brief's Read first."""
            self.assertEqual(report["read_first"], [RULES, REQUIREMENTS, ARCHITECTURE])
            line = line_of(report, f"- {REQUIREMENTS}")
            self.assertNotEqual(line, "", report["prompt"])
            self.assertIsNone(re.search(r"F\d{2,3}", line), line)
        self.each_allowed(check, lambda label, item, task: item.startswith("B"))

    def test_feature_side_pr_reads_the_feature_documents(self):
        """A feature's test-fix or docs brief reads as part 1 says for the feature."""
        def check(label, item, task, stage, want_title, report):
            """Asserts a feature side PR's Read first."""
            self.assertEqual(report["read_first"],
                             [RULES, REQUIREMENTS, ARCHITECTURE, F01.design, F01.plan])
            self.assertTrue(any(line.startswith(f"- {REQUIREMENTS}") and "F01" in line
                                for line in report["prompt"].split("\n")), report["prompt"])
        self.each_allowed(check, lambda label, item, task: label in ("feature test-fix",
                                                                     "feature docs"))


class TitleTests(FlowCase):
    """``--title``: parsed by troy-check, and checked against the item and the stage."""

    EXIT_2 = {
        "no bracket": ("stage3", "F01", "Count words", "DV1"),
        "double space": ("stage3", "F01", "[F01 3/6 mock]  Count words", "DV1"),
        "stage name of another stage": ("stage3", "F01", "[F01 3/6 design] Count words", "DV1"),
        "stage 7": ("stage3", "F01", "[F01 7/6 mock] Count words", "DV1"),
        "lower-case ID": ("stage3", "F01", "[f01 3/6 mock] Count words", "DV1"),
        "bug ID with a leading zero": ("bugB", "B12", "[B012 B/B fix] Crash on empty history",
                                       "DV3"),
        "no summary": ("stage3", "F01", "[docs]", "AR5"),
    }
    EXIT_1 = {
        "rules title for a feature": ("stage3", "F01", "[rules] Set the features Troy approves",
                                      "AR5"),
        "refactor title for a feature": ("stage3", "F01", "[refactor] Split the counter", "DV1"),
        "bug title for a feature": ("stage3", "F01", B12_FIX, "CR1"),
        "stage title for a bug": ("bugB", "B12", F01.title(3), "CR1"),
        "rules title for a bug": ("bugB", "B12", "[rules] Set the features Troy approves",
                                  "AR5"),
        "stage title of another feature": ("stage3", "F01", "[F02 3/6 mock] Count lines",
                                           "DV1"),
        "test-fix of another feature": ("stage5", "F01",
                                        "[F02 test-fix] Wrong count in F02-T01", "TE3"),
        "fix of another bug": ("bugB", "B12", bug_title("B13", "fix", CRASH), "DV3"),
        "test of another bug": ("stage3", "B12", bug_title("B13", "test", CRASH), "TE2"),
        "summary not the feature's name": ("stage3", "F01", "[F01 3/6 mock] Count all words",
                                           "DV1"),
        "redo outside rework": ("stage3", "F01", F01.title(1), "IF1"),
        "redo of the mock outside rework": ("stage5", "F01", F01.title(3), "DV1"),
        "stage above the current one": ("stage3", "F01", F01.title(4), "TE1"),
        "stage above the current one in rework": ("rework", "F01", F01.title(5), "DV2"),
        "test-fix before the tests merged": ("stage4", "F01", TEST_FIX_F01, "TE3"),
        "fix title in step A": ("stage3", "B12", B12_FIX, "DV3"),
        "test-fix title in step A": ("stage3", "B12", B12_TEST_FIX, "TE3"),
        "test title in step B": ("bugB", "B12", B12_TEST, "TE2"),
    }
    ALLOWED = {
        "current stage title": (("stage3", "F01", F01.title(3), "DV1"), 3, F01.title(3)),
        "redo of the design in rework": (("rework", "F01", F01.title(1), "IF1"), 1,
                                         F01.title(1)),
        "redo of the mock in rework": (("rework", "F01", F01.title(3), "DV1"), 3, F01.title(3)),
        "current stage in rework": (("rework", "F01", None, "TE1"), 4, F01.title(4)),
        "AR4 in rework": (("rework", "F01", None, "AR4"), 4, SKIP),
        "docs title for an accepted feature": (
            ("accepted", "F01", "[docs] Update the F01 design notes", "AR3"), None,
            "[docs] Update the F01 design notes"),
    }

    @classmethod
    def setUpClass(cls):
        """Runs every title case side by side."""
        cases = (list(cls.EXIT_2.values()) + list(cls.EXIT_1.values())
                 + [case for case, _, _ in cls.ALLOWED.values()])
        outs = iter(run_briefs(cases))
        cls.exit_2 = {label: next(outs) for label in cls.EXIT_2}
        cls.exit_1 = {label: next(outs) for label in cls.EXIT_1}
        cls.allowed = {label: next(outs) for label in cls.ALLOWED}

    def test_title_troy_check_cannot_parse_exits_two(self):
        """A ``--title`` that troy-check's parser rejects: the engine cannot run."""
        for label, out in self.exit_2.items():
            with self.subTest(case=label):
                self.assert_exit(out, 2)

    def test_title_that_does_not_fit_is_refused(self):
        """Wrong kind, wrong ID, wrong summary, a redo outside rework, a stage too high."""
        for label, out in self.exit_1.items():
            with self.subTest(case=label):
                report = self.report_of(out, 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"), "a refused brief has no prompt")

    def test_titles_that_fit(self):
        """The current stage's title; in rework, a redo stage; a docs title when accepted."""
        for label, (case, stage, title) in self.ALLOWED.items():
            with self.subTest(case=label):
                report = self.report_of(self.allowed[label], 0, "brief")
                self.assertEqual((report["task"], report["item"], report["stage"]),
                                 (case[3], case[1], stage))
                if title is not SKIP:
                    self.assertEqual(report["title"], title)

    def test_redo_of_the_mock_checks_with_its_title(self):
        """The redo's DV1: Python steps without the install (a mock merged), its own title."""
        report = self.report_of(self.allowed["redo of the mock in rework"])
        checks = report["checks"]
        rests = python_rests(False)
        self.assertEqual(len(checks), len(rests) + 1, checks)
        self.assertEqual([pack_words(c)[2] for c in checks[:-1]], rests)
        words = troy_check_step(checks)
        self.assertEqual(option_value(words, "--title"), F01.title(3))
        self.assertIn("--worktree", words)


class SkippedMockBriefTests(FlowCase):
    """A skipped mock gives stage 4 and TE1 in brief too (D65, part 2 note)."""

    def test_tests_come_after_the_test_plan(self):
        """TE1 is F01's stage 4 task; DV1 is refused."""
        te1, dv1 = run_briefs([("skipped", "F01", None, "TE1"), ("skipped", "F01", None, "DV1")])
        report = self.report_of(te1, 0, "brief")
        self.assertEqual((report["stage"], report["title"]), (4, F01.title(4)))
        self.assertNotEqual(self.report_of(dv1, 1)["problems"], [])


class ChecksTests(FlowCase):
    """The checks of part 2's code tasks (part 2 note, brief, Checks)."""

    @classmethod
    def setUpClass(cls):
        """Runs the cases side by side."""
        cls.cases = {
            "TE2 without a title": ("stage3", "B12", None, "TE2"),
            "TM2 without a title": ("stage3", "B12", None, "TM2"),
            "CR1 without a title": ("stage3", "B12", None, "CR1"),
            "DV3 without a language": ("nolang", "B12", None, "DV3"),
            "CR1 without a language": ("nolang", "B12", B12_FIX, "CR1"),
            "AR5 without a language": ("nolang", "B12", None, "AR5"),
            "DV3": ("bugB", "B12", None, "DV3"),
            "TM4": ("bugB", "B12", None, "TM4"),
            "DV3 in C/C++": ("cppbug", "B12", None, "DV3"),
        }
        names = list(cls.cases)
        outs = run_briefs([cls.cases[name] for name in names])
        cls.outs = dict(zip(names, outs))
        cls.prefixed = brief(shared("bugB"), "DV3", "B12",
                             env_extra={"TROY_MODE_ENV_PREFIX": PREFIX})

    def test_code_task_without_a_title_names_the_option(self):
        """Bug step A has no title: TE2, TM2, and CR1 are refused with a problem naming --title."""
        for name in ("TE2 without a title", "TM2 without a title", "CR1 without a title"):
            with self.subTest(case=name):
                report = self.report_of(self.outs[name], 1, "brief")
                self.assertIn("--title", problems_text(report))
                self.assertFalse(report.get("prompt"))

    def test_code_task_without_a_language_is_refused(self):
        """No ``[lang] name`` at HEAD: DV3 and CR1 refused, the problem says so; AR5 runs."""
        for name in ("DV3 without a language", "CR1 without a language"):
            with self.subTest(case=name):
                report = self.report_of(self.outs[name], 1, "brief")
                self.assertIn("lang", problems_text(report).lower())
                self.assertNotIn("--title", problems_text(report))
        self.report_of(self.outs["AR5 without a language"], 0, "brief")

    def test_dv3_runs_the_python_steps_with_worktree(self):
        """DV3: the Python steps without the install (it is not the first mock), then
        troy-check with ``--worktree`` and PR B's derived title."""
        report = self.report_of(self.outs["DV3"])
        checks = report["checks"]
        rests = python_rests(False)
        self.assertEqual(len(checks), len(rests) + 1, checks)
        for command, rest in zip(checks, rests):
            _, target, words = pack_words(command)
            self.assertEqual((target, words), (["-n", "wordcount"], rest), command)
        words = troy_check_step(checks)
        self.assertEqual(option_value(words, "--title"), B12_FIX)
        self.assertEqual(option_value(words, "--base"), "origin/main")
        self.assertIn("--worktree", words)

    def test_tm4_checks_without_worktree(self):
        """TM4 rules on a disputed test and checks the commit: no ``--worktree``."""
        report = self.report_of(self.outs["TM4"])
        self.assertEqual([pack_words(c)[2] for c in report["checks"][:-1]], python_rests(False))
        words = troy_check_step(report["checks"])
        self.assertNotIn("--worktree", words)
        self.assertEqual(option_value(words, "--title"), B12_FIX)

    def test_cpp_bug_fix_starts_with_cmake(self):
        """DV3 in a C/C++ project: cmake first, no uv, troy-check with Doxygen and --worktree."""
        report = self.report_of(self.outs["DV3 in C/C++"])
        self.assertEqual(pack_words(report["checks"][0])[2], ["cmake", "--preset", "coverage"])
        for command in report["checks"]:
            self.assertNotIn("uv", split_command(command), command)
        words = troy_check_step(report["checks"])
        self.assertEqual(option_value(words, "--doc-warnings"), "reports/doxygen.log")
        self.assertEqual(option_value(words, "--title"), B12_FIX)
        self.assertIn("--worktree", words)

    def test_env_prefix_sets_the_target(self):
        """With ``TROY_MODE_ENV_PREFIX``, DV3's steps run ``-p <prefix>``."""
        report = self.report_of(self.prefixed)
        self.assertNotEqual(report["checks"], [])
        for command in report["checks"]:
            with self.subTest(command=command):
                self.assertEqual(pack_words(command)[1], ["-p", PREFIX])


class RefusedTests(FlowCase):
    """Tasks part 2 still refuses (part 2 note, brief, Options and exit codes)."""

    @classmethod
    def setUpClass(cls):
        """Runs the refused cases side by side."""
        cls.tm7 = [("stage3", "F01", None, "TM7"), ("stage5", "F01", None, "TM7"),
                   ("bugB", "B12", None, "TM7")]
        cls.pm = [("bugB", "B12", None, f"PM{n}") for n in range(1, 6)]
        cls.fixed = [("fixed", "B12", None, task)
                     for task in ("DV3", "CR1", "AR3", "AR5", "TM5", "TE2", "TM4")]
        cls.fixed += [("fixed", "B12", B12_FIX, "DV3"), ("fixed", "B12", B12_DOCS, "AR3"),
                      ("fixed", "B12", B12_TEST_FIX, "TE3")]
        outs = iter(run_briefs(cls.tm7 + cls.pm + cls.fixed))
        cls.tm7_outs = [next(outs) for _ in cls.tm7]
        cls.pm_outs = [next(outs) for _ in cls.pm]
        cls.fixed_outs = [next(outs) for _ in cls.fixed]

    def assert_refused(self, cases, outs) -> None:
        """Each case: exit 1, a problem, no prompt."""
        for case, out in zip(cases, outs):
            with self.subTest(case=case):
                report = self.report_of(out, 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"))

    def test_tm7_needs_a_version_item(self):
        """TM7, the version test plan, takes a version item (F08 note, section 9).

        F07 refused TM7 as not built and named F08 in the problem. F08 builds
        TM7 for ``--item vX.Y``, so a feature or bug item is still refused,
        and the problem no longer has to name F08.
        """
        self.assert_refused(self.tm7, self.tm7_outs)

    def test_product_manager_tasks_run_in_the_main_session(self):
        """PM1 to PM5 get no brief for a bug item either."""
        self.assert_refused(self.pm, self.pm_outs)

    def test_fixed_bug_refuses_every_task(self):
        """Planted bug "a fixed bug given a brief": PR A and PR B merged, nothing is left."""
        self.assert_refused(self.fixed, self.fixed_outs)


class BugReadFirstTests(FlowCase):
    """A bug's Read first leaves out an architecture that is not at HEAD."""

    def test_without_an_architecture_at_head(self):
        """Rules and requirements only."""
        project = Project([base_step(), *stages(F01, 2), bug_step("B12", "test", CRASH)])
        project.commit("[docs] Remove the architecture", {ARCHITECTURE: None,
                                                          ARCHITECTURE_ZH: None})
        report = self.report_of(brief(project, "AR5", "B12"), 0, "brief")
        self.assertEqual(report["read_first"], [RULES, REQUIREMENTS])
        self.assertEqual(line_of(report, "Item: "), f"Item: B12, {B12_FIX}")


if __name__ == "__main__":
    unittest.main()
