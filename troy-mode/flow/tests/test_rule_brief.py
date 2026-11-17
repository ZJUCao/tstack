"""Briefs for a rule item (F09 design 5, 7, 10.1; interface note section 7).

``brief --item`` takes a P ID (a project rule) or an R ID (a rule for every
troy-mode project, or a change to an R rule). AR6 picks the enforcement, DV5
and TE6 write the cleanup PRs, and CR1, TM2, and AR5 work on them. The
tests check every row of the note's table of allowed tasks, the stops, the
titles, Read first, the checks, and the Task line's phrases.
"""

import os
import unittest

from flow_helpers import (
    ARCHITECTURE, CONFIG, F01, PLUGIN_ROOT, REQUIREMENTS, RULES, Fakes, FlowCase, Project,
    option_value, pack_words, parallel, troy_check_step,
)
from rule_helpers import (
    DEFAULT_LOG, P01, P02, P03, PYPROJECT, WORKFLOW, log_row, rules_step,
)

D69 = ("A test that the test plan runs only on another platform is skipped here, and "
       "troy-check code reports it under R09 or R10; CI checks it, so name it in your report "
       "and do not count it as a failure.")
ROLE_OF = {"AR": "architect", "DV": "developer", "TE": "test-engineer", "CR": "code-reviewer",
           "TM": "test-manager"}
FIELDS = ("Task: ", "Item: ", "Read first:", "Input:", "Round: ", "Checks to run:")
CODE_TASKS = frozenset(("DV5", "TE6", "CR1", "TM2"))
WORKTREE_TASKS = frozenset(("DV5", "TE6"))
PREFIX = "/scratch/troy-env"
REFACTOR = "[refactor] Apply P01 to counting"
TEST_FIX = "[P01 test-fix] Apply P01 to tests"
TEST_FIX_P02 = "[P02 test-fix] Apply P02 to tests"
DOCS_P01 = "[docs] Change the architecture for P01"
DOCS_P04 = "[docs] Change the architecture for P04"
RETIRED = (P01, P02, P03.retired("2026-11-10"))
RETIRED_LOG = DEFAULT_LOG + (log_row("5.0", "2026-11-10", "Retired P03, approved by Troy.",
                                     "停用 P03，Troy 批准。"),)
CLANG = {".clang-tidy": "Checks: '-*,bugprone-*'\n", ".clang-format": "BasedOnStyle: Google\n"}
RULE_READ = [RULES, REQUIREMENTS, ARCHITECTURE]
AR6_READ = RULE_READ + [PYPROJECT, CONFIG, WORKFLOW]
PLUGIN_READ = [f"{PLUGIN_ROOT.as_posix()}/docs/troy-mode/requirements.md",
               f"{PLUGIN_ROOT.as_posix()}/troy-mode/templates/rules.md",
               f"{PLUGIN_ROOT.as_posix()}/troy-mode/checks/troycheck/",
               f"{PLUGIN_ROOT.as_posix()}/agents/"]
_PROJECTS: dict = {}


def shared(name: str) -> Project:
    """A clone shared by the tests that only read it, built on first use.

    Args:
        name: ``rules`` (P01 by cleanup PRs with baseline lines in the
            workflow and pyproject.toml, P02 with lines in the workflow, P03
            retired; F01 not started), ``cpp`` (the same rules, the C/C++
            pack, ``.clang-tidy`` and ``.clang-format``, no project
            workflow), ``nolang`` (no ``[lang]``), or ``norules`` (no
            ``docs/rules.md``).

    Returns:
        The clone. Tests must not change it.
    """
    if name not in _PROJECTS:
        if name == "rules":
            steps = [rules_step(RETIRED, RETIRED_LOG)]
        elif name == "cpp":
            steps = [rules_step(RETIRED, RETIRED_LOG, lang="cpp",
                                extra={**CLANG, WORKFLOW: None})]
        elif name == "nolang":
            steps = [rules_step(RETIRED, RETIRED_LOG, lang=None)]
        elif name == "norules":
            steps = [rules_step(extra={RULES: None, "docs/rules.zh-CN.md": None})]
        else:
            raise KeyError(name)
        _PROJECTS[name] = Project(steps)
    return _PROJECTS[name]


def brief(case, env_extra=None, fakes=None):
    """Runs ``brief --task <task> --item <item> [--title <title>] --json``.

    Args:
        case: ``(clone name, item, title or None, task)``.
        env_extra: More environment variables.
        fakes: The fakes, or None for a gh that fails on every call.

    Returns:
        The outcome.
    """
    name, item, title, task = case
    args = ["brief", "--task", task, "--item", item]
    if title is not None:
        args += ["--title", title]
    return shared(name).run(*args, env_extra=env_extra, fakes=fakes)


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
    """The Python pack's steps after ``<mamba> run <target>``, before troy-check (no install)."""
    return [["ruff", "check"], ["ruff", "format", "--check"], ["mypy"],
            ["coverage", "run", "-m", "pytest", "--junitxml=reports/junit.xml", "||", "true"],
            ["coverage", "xml", "-o", "reports/coverage.xml"]]


def troy_check_words(title: str, worktree: bool) -> list:
    """The Python troy-check step's words after the target, sorted."""
    words = ["python", ".troy-mode/checks/troy_check.py", "code", "--base", "origin/main",
             "--title", title, "--junit", "reports/junit.xml", "--coverage",
             "reports/coverage.xml"]
    return sorted(words + (["--worktree"] if worktree else []))


# (label, clone, item, title, allowed tasks, refused tasks, title in the report)
ROWS = [
    ("P01 without a title", "rules", "P01", None, ("AR6",),
     ("AR5", "DV5", "TE6", "CR1", "TM2", "AR3", "AR4", "DV1", "TE1", "IF1", "TM1", "TM7",
      "PM1"), None),
    ("next free P04", "rules", "P04", None, ("AR6",), ("AR5", "DV5", "CR1", "TE6"), None),
    ("P01 docs", "rules", "P01", DOCS_P01, ("AR6", "AR5"), ("DV5", "TE6", "CR1", "TM2"),
     DOCS_P01),
    ("P04 docs", "rules", "P04", DOCS_P04, ("AR6", "AR5"), ("DV5", "TE6", "CR1", "TM2"),
     DOCS_P04),
    ("P01 refactor", "rules", "P01", REFACTOR, ("DV5", "CR1", "AR5"),
     ("TE6", "TM2", "AR6", "DV1", "DV2", "TE3"), REFACTOR),
    ("P01 test-fix", "rules", "P01", TEST_FIX, ("TE6", "TM2", "CR1", "AR5"),
     ("DV5", "AR6", "TE3", "TE4", "DV2"), TEST_FIX),
    ("P02 test-fix", "rules", "P02", TEST_FIX_P02, ("TE6", "TM2"), ("DV5",), TEST_FIX_P02),
    ("R03, a row", "rules", "R03", None, ("AR6",), ("AR5", "DV5", "TE6", "CR1", "TM2"), None),
    ("next R ID", "rules", "R23", None, ("AR6",), ("TM2", "AR5"), None),
    ("P01 without a rules file", "norules", "P01", None, ("AR6",), ("DV5",), None),
]


class AllowedTasksTests(FlowCase):
    """The note's table of what each rule item allows, row by row (note section 7)."""

    @classmethod
    def setUpClass(cls):
        """Runs one brief per allowed and refused task of every row, side by side."""
        cases, cls.allowed, cls.refused = [], [], []
        for label, clone, item, title, allowed, refused, want_title in ROWS:
            for task in allowed:
                cls.allowed.append((label, item, task, want_title, len(cases)))
                cases.append((clone, item, title, task))
            for task in refused:
                cls.refused.append((label, task, len(cases)))
                cases.append((clone, item, title, task))
        cls.outs = run_briefs(cases)

    def each_allowed(self, check, only=None) -> None:
        """Calls a check on the report of every allowed task, each in its own subtest.

        Args:
            check: A function of ``(label, item, task, title, report)``.
            only: A function of ``(label, item, task)`` that picks the cases, or None.
        """
        for label, item, task, want_title, index in self.allowed:
            if only is not None and not only(label, item, task):
                continue
            with self.subTest(row=label, task=task):
                check(label, item, task, want_title, self.report_of(self.outs[index], 0, "brief"))

    def test_allowed_tasks_get_a_brief(self):
        """Each allowed task: its role, subagent, item, no stage, the title, the six fields."""
        def check(label, item, task, want_title, report):
            """Asserts the report's keys and the order of the prompt's fields."""
            role = ROLE_OF[task[:2]]
            self.assertEqual((report["task"], report["role"], report["item"], report["stage"],
                              report["title"]), (task, role, item, None, want_title))
            self.assertEqual(report["agent"], {"subagent_type": f"tstack:troy-{role}"})
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
        self.assertTrue(self.allowed)
        self.report_of(self.outs[self.allowed[0][4]], 0, "brief")
        for label, task, index in self.refused:
            with self.subTest(row=label, task=task):
                report = self.report_of(self.outs[index], 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"), "a refused task has no brief")

    def test_item_line_holds_the_id_and_the_title(self):
        """``Item: <ID>, <title>``, or the ID alone when the title is null."""
        def check(label, item, task, want_title, report):
            """Asserts the Item line."""
            want = f"Item: {item}, {want_title}" if want_title else f"Item: {item}"
            self.assertEqual(line_of(report, "Item: "), want)
        self.each_allowed(check)

    def test_code_tasks_check_with_the_title(self):
        """DV5 and TE6 with ``--worktree``, CR1 and TM2 without, all after the Python steps."""
        def check(label, item, task, want_title, report):
            """Asserts the checks of one code task."""
            checks = report["checks"]
            self.assertEqual(len(checks), len(python_rests()) + 1, checks)
            for command, rest in zip(checks, python_rests()):
                self.assertEqual(pack_words(command)[1:], (["-n", "wordcount"], rest), command)
            _, target, words = pack_words(checks[-1])
            self.assertEqual(target, ["-n", "wordcount"])
            self.assertEqual(sorted(words), troy_check_words(want_title, task in WORKTREE_TASKS))
            self.assertEqual(words[:3], ["python", ".troy-mode/checks/troy_check.py", "code"])
            for command in checks:
                self.assertIn(f"- {command}", report["prompt"].split("\n"))
        self.each_allowed(check, lambda label, item, task: task in CODE_TASKS)

    def test_ar6_and_ar5_have_no_checks(self):
        """AR6 and AR5: ``checks`` is [] and the prompt says None."""
        def check(label, item, task, want_title, report):
            """Asserts no checks."""
            self.assertEqual(report["checks"], [])
            self.assertIn("Checks to run: None", report["prompt"].split("\n"))
        self.each_allowed(check, lambda label, item, task: task in ("AR6", "AR5"))

    def test_platform_skip_sentence_for_code_tasks_only(self):
        """DV5, TE6, CR1, and TM2 end their Task line's sentence with D69's; AR6 and AR5 do not."""
        def check(label, item, task, want_title, report):
            """Asserts the D69 sentence, or its absence."""
            task_line = line_of(report, "Task: ")
            if task in CODE_TASKS:
                self.assertIn(D69, task_line)
            else:
                self.assertNotIn("another platform", task_line)
        self.each_allowed(check)


class ReadFirstTests(FlowCase):
    """Read first, by task and title (note section 7)."""

    @classmethod
    def setUpClass(cls):
        """Runs every case side by side."""
        cls.cases = {
            "AR6 on P01": ("rules", "P01", None, "AR6"),
            "AR6 on P04 with a docs title": ("rules", "P04", DOCS_P04, "AR6"),
            "AR5 on P01 with a docs title": ("rules", "P01", DOCS_P01, "AR5"),
            "AR6 in C/C++": ("cpp", "P01", None, "AR6"),
            "AR6 on R03": ("rules", "R03", None, "AR6"),
            "AR6 on R23": ("rules", "R23", None, "AR6"),
            "DV5": ("rules", "P01", REFACTOR, "DV5"),
            "CR1 on the refactor": ("rules", "P01", REFACTOR, "CR1"),
            "AR5 on the refactor": ("rules", "P01", REFACTOR, "AR5"),
            "TE6": ("rules", "P01", TEST_FIX, "TE6"),
            "TM2": ("rules", "P01", TEST_FIX, "TM2"),
            "TE6 on P02": ("rules", "P02", TEST_FIX_P02, "TE6"),
            "AR6 without a rules file": ("norules", "P01", None, "AR6"),
        }
        names = list(cls.cases)
        cls.outs = dict(zip(names, run_briefs([cls.cases[n] for n in names])))

    def read_first(self, name: str) -> list:
        """The Read first of one case, which must have exit code 0."""
        return self.report_of(self.outs[name], 0, "brief")["read_first"]

    def test_ar6_reads_the_packs_config(self):
        """AR6: the rule documents, then pyproject.toml, the config, and the project workflow."""
        for name in ("AR6 on P01", "AR6 on P04 with a docs title"):
            with self.subTest(case=name):
                self.assertEqual(self.read_first(name), AR6_READ)

    def test_ar5_reads_the_rule_documents(self):
        """AR5 with a docs title: the rules, the requirements, and the architecture."""
        self.assertEqual(self.read_first("AR5 on P01 with a docs title"), RULE_READ)

    def test_files_are_listed_only_when_they_exist(self):
        """C/C++: ``.clang-tidy`` and ``.clang-format``, no project workflow; no rules file
        when there is none."""
        self.assertEqual(self.read_first("AR6 in C/C++"),
                         RULE_READ + [PYPROJECT, ".clang-tidy", ".clang-format", CONFIG])
        self.assertEqual(self.read_first("AR6 without a rules file"),
                         [REQUIREMENTS, ARCHITECTURE, PYPROJECT, CONFIG, WORKFLOW])

    def test_r_id_reads_the_plugin_folder(self):
        """AR6 on an R ID: AR6's files, then four plugin paths, absolute with ``/``."""
        for name in ("AR6 on R03", "AR6 on R23"):
            with self.subTest(case=name):
                found = self.read_first(name)
                self.assertEqual(found[:len(AR6_READ)], AR6_READ)
                plugin = found[len(AR6_READ):]
                self.assertEqual(len(plugin), len(PLUGIN_READ), found)
                for got, want in zip(plugin, PLUGIN_READ):
                    self.assertNotIn("\\", got)
                    self.assertEqual(os.path.normcase(got), os.path.normcase(want))
                    self.assertEqual(got.endswith("/"), want.endswith("/"), got)

    def test_cleanup_tasks_read_the_files_with_baseline_lines(self):
        """DV5, CR1, AR5, TE6, and TM2 on P01: the rule documents, then the workflow and
        pyproject.toml, which hold P01's lines, sorted; TE6 on P02: the workflow only."""
        for name in ("DV5", "CR1 on the refactor", "AR5 on the refactor", "TE6", "TM2"):
            with self.subTest(case=name):
                self.assertEqual(self.read_first(name), RULE_READ + [WORKFLOW, PYPROJECT])
        self.assertEqual(self.read_first("TE6 on P02"), RULE_READ + [WORKFLOW])


class PromptTests(FlowCase):
    """The Task line's phrases (note section 7, "Prompt")."""

    @classmethod
    def setUpClass(cls):
        """Runs every case side by side, and AR6 once more with an environment prefix."""
        cls.cases = {
            "AR6 on P01": ("rules", "P01", None, "AR6"),
            "AR6 on P04": ("rules", "P04", None, "AR6"),
            "AR6 with a docs title": ("rules", "P04", DOCS_P04, "AR6"),
            "AR6 on R03": ("rules", "R03", None, "AR6"),
            "DV5": ("rules", "P01", REFACTOR, "DV5"),
            "TE6": ("rules", "P01", TEST_FIX, "TE6"),
            "TE6 on P02": ("rules", "P02", TEST_FIX_P02, "TE6"),
            "TM2": ("rules", "P01", TEST_FIX, "TM2"),
        }
        names = list(cls.cases)
        cls.outs = dict(zip(names, run_briefs([cls.cases[n] for n in names])))
        cls.prefixed = brief(("rules", "P01", None, "AR6"),
                             env_extra={"TROY_MODE_ENV_PREFIX": PREFIX})

    def task_line(self, name: str) -> str:
        """The Task line of one case, which must have exit code 0."""
        return line_of(self.report_of(self.outs[name], 0, "brief"), "Task: ")

    def test_ar6_proposes_and_changes_nothing(self):
        """AR6 on a P ID: the item, a command-line option, escalate, Change no file, and the
        environment's run prefix."""
        for name, item in (("AR6 on P01", "P01"), ("AR6 on P04", "P04")):
            with self.subTest(case=name):
                line = self.task_line(name)
                for text in (item, "command-line option", "escalate", "Change no file",
                             "mamba", "run -n wordcount"):
                    self.assertIn(text, line)

    def test_ar6_prefix_from_the_environment(self):
        """With ``TROY_MODE_ENV_PREFIX``, AR6's Task line runs ``-p <prefix>``."""
        line = line_of(self.report_of(self.prefixed, 0, "brief"), "Task: ")
        self.assertIn(f"run -p {PREFIX}", line)
        self.assertNotIn("run -n wordcount", line)

    def test_ar6_with_a_docs_title_writes_an_adr(self):
        """AR6's second run, with the ``[docs]`` title, names the ADR."""
        self.assertIn("ADR", self.task_line("AR6 with a docs title"))

    def test_ar6_on_an_r_id_names_the_plugin_folder(self):
        """AR6 on an R ID: a rule for every troy-mode project, read in the plugin folder."""
        line = self.task_line("AR6 on R03")
        self.assertIn("every troy-mode project", line)
        self.assertIn("plugin folder", line)

    def test_cleanup_tasks_name_the_baseline(self):
        """DV5 names ``baseline: P01`` and R03; TE6 names ``baseline: P01`` or ``P02``; TM2
        names P01 and the baseline."""
        dv5 = self.task_line("DV5")
        self.assertIn("baseline: P01", dv5)
        self.assertIn("R03", dv5)
        self.assertIn("baseline: P01", self.task_line("TE6"))
        self.assertIn("baseline: P02", self.task_line("TE6 on P02"))
        self.assertNotIn("baseline: P01", self.task_line("TE6 on P02"))
        tm2 = self.task_line("TM2")
        self.assertIn("P01", tm2)
        self.assertIn("baseline", tm2)


class StopTests(FlowCase):
    """Briefs the engine refuses: exit 1, ok false, one problem, no prompt (note section 7)."""

    CASES = {
        "retired P03, AR6": ("rules", "P03", None, "AR6"),
        "retired P03, DV5": ("rules", "P03", "[refactor] Apply P03 to errors", "DV5"),
        "retired P03, TE6": ("rules", "P03", "[P03 test-fix] Apply P03 to tests", "TE6"),
        "retired P03, docs": ("rules", "P03", "[docs] Change the architecture for P03", "AR6"),
        "P07, neither a row nor next": ("rules", "P07", None, "AR6"),
        "R30, neither a row nor next": ("rules", "R30", None, "AR6"),
        "next free P04 with a refactor title": ("rules", "P04", "[refactor] Apply P04 to x",
                                                "DV5"),
        "next free P04 with a test-fix title": ("rules", "P04",
                                                "[P04 test-fix] Apply P04 to tests", "TE6"),
        "refactor summary without Apply": ("rules", "P01", "[refactor] Split counting.py", "DV5"),
        "refactor of another rule": ("rules", "P01", "[refactor] Apply P02 to counting", "DV5"),
        "test-fix of another rule": ("rules", "P01", TEST_FIX_P02, "TE6"),
        "rules title": ("rules", "P01", "[rules] Add P01, no f-strings", "AR6"),
        "stage title": ("rules", "P01", F01.title(3), "DV5"),
        "feature test-fix title": ("rules", "P01", "[F01 test-fix] Wrong count in F01-T01",
                                   "TE6"),
        "AR6 on a feature": ("rules", "F01", None, "AR6"),
        "DV5 on a feature": ("rules", "F01", REFACTOR, "DV5"),
        "TE6 on a feature": ("rules", "F01", None, "TE6"),
        "AR6 on a bug": ("rules", "B12", None, "AR6"),
        "TE6 on a bug": ("rules", "B12", None, "TE6"),
        "AR6 on a version": ("rules", "v0.1", None, "AR6"),
        "DV5 without a language": ("nolang", "P01", REFACTOR, "DV5"),
        "TE6 without a language": ("nolang", "P01", TEST_FIX, "TE6"),
        "CR1 without a language": ("nolang", "P01", REFACTOR, "CR1"),
        "TM2 without a language": ("nolang", "P01", TEST_FIX, "TM2"),
    }
    CONTROLS = {
        "AR6 without a language": ("nolang", "P01", None, "AR6"),
        "DV5 on P01": ("rules", "P01", REFACTOR, "DV5"),
    }

    @classmethod
    def setUpClass(cls):
        """Runs every case and control side by side."""
        names = list(cls.CASES) + list(cls.CONTROLS)
        cases = {**cls.CASES, **cls.CONTROLS}
        cls.outs = dict(zip(names, run_briefs([cases[n] for n in names])))

    def test_controls_get_a_brief(self):
        """AR6 needs no language; DV5 on P01 with its refactor title is allowed."""
        for name in self.CONTROLS:
            with self.subTest(case=name):
                self.report_of(self.outs[name], 0, "brief")

    def test_each_stop_is_refused(self):
        """Each case: exit 1, a problem, and no prompt."""
        self.test_controls_get_a_brief()
        for name in self.CASES:
            with self.subTest(case=name):
                report = self.report_of(self.outs[name], 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"), "a refused brief has no prompt")


class CppAndGhTests(FlowCase):
    """The C/C++ pack's steps for DV5, and no gh call (note section 7, F07)."""

    def test_cpp_cleanup_starts_with_cmake(self):
        """DV5 in a C/C++ project: cmake first, troy-check with Doxygen, the title, and
        ``--worktree``; brief never calls gh or mamba."""
        fakes = Fakes(fail=True)
        report = self.report_of(brief(("cpp", "P01", REFACTOR, "DV5"), fakes=fakes), 0, "brief")
        self.assertEqual(pack_words(report["checks"][0])[2], ["cmake", "--preset", "coverage"])
        words = troy_check_step(report["checks"])
        self.assertEqual(option_value(words, "--doc-warnings"), "reports/doxygen.log")
        self.assertEqual(option_value(words, "--title"), REFACTOR)
        self.assertIn("--worktree", words)
        self.assertEqual(fakes.gh_calls(), [])
        self.assertEqual(fakes.mamba_calls(), [])


if __name__ == "__main__":
    unittest.main()
