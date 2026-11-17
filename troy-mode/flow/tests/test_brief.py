"""Brief group (F07 design 3.2, 6.1, 14.1): ``troy_flow.py brief``.

Planted bugs of design 14.2 caught here:

- "``[roles]`` read from the working tree":
  ``RolesTests.test_roles_are_read_at_head_not_from_the_working_tree`` and
  ``test_roles_added_only_in_the_working_tree_change_nothing``.
- "effort passed when unset": ``RolesTests.test_model_and_effort_come_from_roles`` (the
  Developer has a model and no effort) and ``test_unset_role_gets_neither``.

After F19 (design 5.1 and 11.1), every brief's ``subagent_type`` is ``tstack:troy-<role>``.
F19's planted bug "the engine's subagent_type left" is caught by
``TaskRoleTests.test_each_task_names_its_role_and_subagent`` (all six roles) and by every
other test that compares a report's ``agent``.
"""

import unittest

from flow_helpers import (
    ARCHITECTURE, ARCHITECTURE_ZH, CONFIG, F01, F02, REQUIREMENTS, RULES, WORK_BRANCH, Fakes,
    FlowCase, Project, base_files, base_step, config_text, design_text, option_value, pack_words,
    parallel, same_path, split_command, stages, step, troy_check_step,
)

ROLES = ('[roles.developer]\nmodel = "opus"\n\n[roles.code-reviewer]\neffort = "medium"\n\n'
         '[roles.architect]\nmodel = "opus"\neffort = "max"\n')
ROLE_OF = {"AR": "architect", "IF": "interface-designer", "TM": "test-manager",
           "DV": "developer", "TE": "test-engineer", "CR": "code-reviewer"}
FIELDS = ("Task: ", "Item: ", "Read first:", "Input:", "Round: ", "Checks to run:")
PREFIX = "/scratch/troy-env"
_PROJECTS: dict = {}


def shared(name: str) -> Project:
    """A clone shared by the tests that only read it, built on first use.

    Args:
        name: ``stage1`` to ``stage5`` (F01's current stage), ``second-mock``
            (F01 accepted, F02 at stage 3), ``cpp``, ``nolang``, or ``roles``
            (each with F01 at stage 3).

    Returns:
        The clone. Tests must not change it.
    """
    if name not in _PROJECTS:
        if name.startswith("stage"):
            steps = [base_step(), *stages(F01, int(name[-1]) - 1)]
        elif name == "second-mock":
            steps = [base_step(), *stages(F01, 6), *stages(F02, 2)]
        elif name == "cpp":
            steps = [base_step(base_files(lang="cpp")), *stages(F01, 2)]
        elif name == "nolang":
            steps = [base_step(base_files(lang=None)), *stages(F01, 2)]
        else:
            steps = [base_step(base_files(config_extra=ROLES)), *stages(F01, 2)]
        _PROJECTS[name] = Project(steps)
    return _PROJECTS[name]


def brief(project: Project, task: str, item: str = "F01", *extra: str, fakes=None,
          env_extra=None):
    """Runs ``brief --task <task> [--item <item>] --json`` on a clone.

    Args:
        project: The clone.
        task: The task ID.
        item: The feature ID, or "" to leave ``--item`` out.
        *extra: More options.
        fakes: The fakes, or None for a gh that fails on every call.
        env_extra: More environment variables.

    Returns:
        The outcome.
    """
    args = ["brief", "--task", task, *(["--item", item] if item else []), *extra]
    return project.run(*args, fakes=fakes, env_extra=env_extra)


def run_briefs(cases) -> list:
    """Runs several briefs side by side on shared clones.

    Args:
        cases: ``(clone name, task, item, extra options)`` tuples.

    Returns:
        The outcomes, in the order of the cases.
    """
    for name in sorted({case[0] for case in cases}):
        shared(name)
    return parallel(lambda case: brief(shared(case[0]), case[1], case[2], *case[3]), cases)


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


def troy_check_words(title: str, worktree: bool) -> list:
    """The Python troy-check step's words after the target, sorted.

    Args:
        title: The PR title.
        worktree: Whether ``--worktree`` is expected.

    Returns:
        The sorted words.
    """
    words = ["python", ".troy-mode/checks/troy_check.py", "code", "--base", "origin/main",
             "--title", title, "--junit", "reports/junit.xml", "--coverage",
             "reports/coverage.xml"]
    return sorted(words + (["--worktree"] if worktree else []))


class BriefFieldsTests(FlowCase):
    """F04's six brief fields, for the Interface Designer's IF1."""

    @classmethod
    def setUpClass(cls):
        """Runs IF1 for F01 at stage 1 once."""
        cls.out = brief(shared("stage1"), "IF1")

    def setUp(self):
        """Every test reads the one report."""
        self.report = self.report_of(self.out, 0, "brief")
        self.lines = self.report["prompt"].split("\n")

    def test_prompt_has_the_six_fields_in_order(self):
        """Task, Item, Read first, Input, Round, and Checks to run, in that order (F04 5.1)."""
        found = []
        for prefix in FIELDS:
            index = next((i for i, line in enumerate(self.lines) if line.startswith(prefix)), None)
            self.assertIsNotNone(index, f"no line starts {prefix!r}:\n{self.report['prompt']}")
            found.append(index)
        self.assertEqual(found, sorted(found), self.report["prompt"])
        task_line = next(line for line in self.lines if line.startswith("Task: "))
        self.assertTrue(task_line.startswith("Task: IF1"), task_line)
        item_line = next(line for line in self.lines if line.startswith("Item: "))
        self.assertIn("F01", item_line)
        self.assertIn("[F01 1/6 design] Count words", item_line)

    def test_if1_leaves_no_marker_in_section_four(self):
        """IF1's task names the design's path and keeps section 4 free of template markers.

        Added after the trial (design 14.3, step 4): the Interface Designer left
        section 4's template markers for the Architect, so troy-check pr failed
        R20 on the design until AR2 filled the section in.
        """
        task_line = next(line for line in self.lines if line.startswith("Task: "))
        self.assertIn("docs/features/F01-count-words/design.md", task_line)
        self.assertIn("Section 4", task_line)
        self.assertIn('"Not reviewed yet."', task_line)

    def test_empty_fields_say_none(self):
        """No input, no round, and no checks are each written as None."""
        for line in ("Input: None", "Round: None", "Checks to run: None"):
            self.assertIn(line, self.lines, self.report["prompt"])

    def test_report_fields(self):
        """Task, role, item, stage, title, and an agent without model or effort."""
        report = self.report
        self.assertEqual((report["task"], report["role"], report["item"], report["stage"]),
                         ("IF1", "interface-designer", "F01", 1))
        self.assertEqual(report["title"], "[F01 1/6 design] Count words")
        self.assertEqual(report["agent"], {"subagent_type": "tstack:troy-interface-designer"})
        self.assertEqual((report["input"], report["round"], report["checks"]), (None, None, []))

    def test_read_first_before_the_feature_has_documents(self):
        """Without a design or test plan at HEAD: rules, requirements, and architecture."""
        self.assertEqual(self.report["read_first"], [RULES, REQUIREMENTS, ARCHITECTURE])
        self.assertTrue(any(line.startswith(f"- {REQUIREMENTS}") and "F01" in line
                            for line in self.lines), self.report["prompt"])
        for path in (RULES, ARCHITECTURE):
            self.assertTrue(any(line.startswith(f"- {path}") for line in self.lines), path)


class TaskRoleTests(FlowCase):
    """Each part 1 task gets its role, subagent, stage, and title (F04 section 6)."""

    def test_each_task_names_its_role_and_subagent(self):
        """AR, IF, TM, DV, TE, and CR tasks at their stages."""
        cases = [("stage1", "IF1"), ("stage1", "IF2"), ("stage1", "AR2"), ("stage1", "AR5"),
                 ("stage2", "TM1"), ("stage2", "IF3"), ("stage3", "DV1"), ("stage3", "CR1"),
                 ("stage4", "TE1"), ("stage4", "TM2"), ("stage4", "CR1"), ("stage5", "DV2"),
                 ("stage5", "CR1")]
        outs = run_briefs([(name, task, "F01", ()) for name, task in cases])
        for (name, task), out in zip(cases, outs):
            with self.subTest(task=task, project=name):
                report = self.report_of(out)
                stage = int(name[-1])
                role = ROLE_OF[task[:2]]
                self.assertEqual((report["task"], report["role"], report["item"], report["stage"]),
                                 (task, role, "F01", stage))
                self.assertEqual(report["title"], F01.title(stage))
                self.assertEqual(report["agent"], {"subagent_type": f"tstack:troy-{role}"})

    def test_ar1_has_no_item(self):
        """AR1 writes the architecture: no item or stage; it reads rules and requirements."""
        report = self.report_of(brief(shared("stage1"), "AR1", ""))
        self.assertEqual((report["role"], report["item"], report["stage"]),
                         ("architect", None, None))
        self.assertEqual(report["title"], "[docs] Add the architecture")
        self.assertEqual(report["read_first"], [RULES, REQUIREMENTS])
        self.assertEqual(report["checks"], [])


class RefusalTests(FlowCase):
    """Options the engine cannot use (exit 2) and briefs it refuses (exit 1)."""

    def test_bad_options_exit_two(self):
        """Unknown tasks, a missing or extra item, a bad round, or an unreadable input file."""
        project = shared("stage3")
        bad = project.tmp / "bad-input.txt"
        bad.write_bytes(b"\xff\xfe\x00 not utf-8 \xc3\x28\n")
        cases = {
            "unknown task": ("XX1", "F01", ()),
            "task number F04 does not have": ("DV9", "F01", ()),
            "no item for DV1": ("DV1", "", ()),
            "item given with AR1": ("AR1", "F01", ()),
            "round zero": ("DV1", "F01", ("--round", "0")),
            "round negative": ("DV1", "F01", ("--round", "-1")),
            "round not a number": ("DV1", "F01", ("--round", "two")),
            "input not UTF-8": ("DV1", "F01", ("--input-file", str(bad))),
            "input missing": ("DV1", "F01", ("--input-file", str(project.tmp / "nope.txt"))),
        }
        outs = run_briefs([("stage3", *case) for case in cases.values()])
        for label, out in zip(cases, outs):
            with self.subTest(case=label):
                self.assert_exit(out, 2)

    def test_invalid_config_at_head_exits_two(self):
        """A config at HEAD that troy-check rejects stops the engine."""
        project = Project([base_step(), *stages(F01, 2)])
        project.commit("[rules] Break the config", {CONFIG: config_text(extra="[bogus]\nx = 1\n")})
        self.assert_exit(brief(project, "DV1"), 2)

    def test_part_two_tasks_at_stage_three(self):
        """Part 2 tasks at F01's stage 3 (part 2 note, "Part 1 tests that part 2 changes").

        TM4, IF4, TM3, TM6, and DV4 belong to stage 5; DV3, TE2, and TM5 to a
        bug; TE3 and TE4 need a test-fix title; TM7 is F08's. AR3 and AR4 are
        now allowed at any stage.
        """
        refused = ("TM4", "IF4", "TM3", "TM6", "DV4", "DV3", "TE2", "TM5", "TE3", "TE4", "TM7")
        allowed = ("AR3", "AR4")
        tasks = refused + allowed
        for task, out in zip(tasks, run_briefs([("stage3", t, "F01", ()) for t in tasks])):
            with self.subTest(task=task):
                if task in refused:
                    report = self.report_of(out, 1, "brief")
                    self.assertNotEqual(report["problems"], [])
                    self.assertFalse(report.get("prompt"), "a refused task has no brief")
                else:
                    report = self.report_of(out, 0, "brief")
                    self.assertEqual((report["task"], report["role"], report["item"],
                                      report["stage"]), (task, "architect", "F01", 3))
                    self.assertEqual(report["checks"], [])

    def test_product_manager_tasks_are_refused(self):
        """PM1 to PM5 run in the main session, so they get no brief."""
        tasks = ("PM1", "PM2", "PM3", "PM4", "PM5")
        for task, out in zip(tasks, run_briefs([("stage3", t, "F01", ()) for t in tasks])):
            with self.subTest(task=task):
                report = self.report_of(out, 1)
                self.assertNotEqual(report["problems"], [])

    def test_unknown_feature_is_refused(self):
        """An item that is not in the features table on origin/main."""
        report = self.report_of(brief(shared("stage3"), "DV1", "F09"), 1)
        self.assertNotEqual(report["problems"], [])

    def test_accepted_feature_is_refused(self):
        """A feature whose stage 6 merged has no stage left."""
        report = self.report_of(brief(shared("second-mock"), "CR1", "F01"), 1)
        self.assertNotEqual(report["problems"], [])

    def test_task_of_another_stage_is_refused(self):
        """At stage 3, only DV1, CR1, and AR5 belong to the stage."""
        codes = {"IF1": 1, "IF2": 1, "AR2": 1, "TM1": 1, "IF3": 1, "TE1": 1, "TM2": 1, "DV2": 1,
                 "DV1": 0, "CR1": 0, "AR5": 0}
        outs = run_briefs([("stage3", task, "F01", ()) for task in codes])
        for (task, code), out in zip(codes.items(), outs):
            with self.subTest(task=task):
                self.report_of(out, code)

    def test_code_task_without_a_language_is_refused(self):
        """No ``[lang] name`` at HEAD: code tasks are refused, AR5 is not."""
        project = shared("nolang")
        for task in ("DV1", "CR1"):
            with self.subTest(task=task):
                self.report_of(brief(project, task), 1)
        self.report_of(brief(project, "AR5"), 0)


class ReadFirstTests(FlowCase):
    """Read first, by task, from the files at HEAD (design 6.1)."""

    def test_feature_documents_and_dependency_designs(self):
        """F02's design and test plan, then the design of F01, which it depends on."""
        report = self.report_of(brief(shared("second-mock"), "DV1", "F02"))
        self.assertEqual(report["read_first"], [
            RULES, REQUIREMENTS, ARCHITECTURE, F02.design, F02.plan, F01.design])
        lines = report["prompt"].split("\n")
        self.assertTrue(any(line.startswith(f"- {REQUIREMENTS}") and "F02" in line
                            for line in lines), report["prompt"])

    def test_dependency_design_not_at_head_is_left_out(self):
        """F02 before F01 has a design: F01's design is not listed."""
        report = self.report_of(brief(shared("stage1"), "IF1", "F02"))
        self.assertEqual(report["read_first"], [RULES, REQUIREMENTS, ARCHITECTURE])

    def test_feature_folder_is_found_by_its_id(self):
        """A design in ``docs/features/F02-line-counting/`` is found by the ``F02-`` prefix."""
        folder = "docs/features/F02-line-counting"
        design = step("[F02 1/6 design] Count lines",
                      {f"{folder}/design.md": design_text(F02),
                       f"{folder}/design.zh-CN.md": design_text(F02, lang="zh-CN")})
        report = self.report_of(brief(Project([base_step(), design]), "TM1", "F02"))
        self.assertEqual(report["read_first"], [RULES, REQUIREMENTS, ARCHITECTURE,
                                                f"{folder}/design.md"])

    def test_rules_and_requirements_stay_when_missing_at_head(self):
        """Missing at HEAD, rules and requirements are still listed; the architecture is not."""
        project = Project([base_step(), *stages(F01, 2)])
        project.commit("[docs] Remove files", {RULES: None, ARCHITECTURE: None,
                                                ARCHITECTURE_ZH: None})
        report = self.report_of(brief(project, "DV1"))
        self.assertEqual(report["read_first"][:2], [RULES, REQUIREMENTS])
        self.assertNotIn(ARCHITECTURE, report["read_first"])


class PythonChecksTests(FlowCase):
    """The Python pack's steps in the project's environment (design 6.1, D60)."""

    def assert_python_checks(self, report: dict, install: bool, worktree: bool) -> None:
        """Asserts the order and words of every Python step and the target ``-n wordcount``.

        Args:
            report: The brief report.
            install: Whether the editable install comes first.
            worktree: Whether troy-check gets ``--worktree``.
        """
        checks = report["checks"]
        expected = python_rests(install)
        self.assertEqual(len(checks), len(expected) + 1, checks)
        for command, rest in zip(checks, expected):
            _, target, words = pack_words(command)
            self.assertEqual(target, ["-n", "wordcount"], command)
            self.assertEqual(words, rest, command)
        _, target, words = pack_words(checks[-1])
        self.assertEqual(target, ["-n", "wordcount"], checks[-1])
        self.assertEqual(sorted(words), troy_check_words(report["title"], worktree), checks[-1])
        self.assertEqual(words[:3], ["python", ".troy-mode/checks/troy_check.py", "code"])

    def test_python_steps_in_order(self):
        """DV2: ruff, format, mypy, pytest under coverage, the XML, and troy-check --worktree."""
        report = self.report_of(brief(shared("stage5"), "DV2"))
        self.assert_python_checks(report, install=False, worktree=True)

    def test_first_mock_installs_the_project_first(self):
        """DV1 of the project's first mock starts with ``uv pip install -e . --no-deps``."""
        report = self.report_of(brief(shared("stage3"), "DV1"))
        self.assert_python_checks(report, install=True, worktree=True)

    def test_later_mock_does_not_install(self):
        """DV1 of a second feature's mock, after a mock merged: no editable install."""
        report = self.report_of(brief(shared("second-mock"), "DV1", "F02"))
        self.assert_python_checks(report, install=False, worktree=True)

    def test_worktree_and_install_by_task(self):
        """``--worktree`` for DV1, DV2, and TE1 only; the install for the first DV1 only."""
        cases = [("stage3", "DV1", True, True), ("stage3", "CR1", False, False),
                 ("stage4", "TE1", True, False), ("stage4", "TM2", False, False),
                 ("stage4", "CR1", False, False), ("stage5", "DV2", True, False),
                 ("stage5", "CR1", False, False)]
        outs = run_briefs([(case[0], case[1], "F01", ()) for case in cases])
        for (name, task, worktree, install), out in zip(cases, outs):
            with self.subTest(task=task, project=name):
                report = self.report_of(out)
                self.assert_python_checks(report, install=install, worktree=worktree)
                words = troy_check_step(report["checks"])
                self.assertEqual(option_value(words, "--title"), F01.title(int(name[-1])))

    def test_document_tasks_have_no_checks(self):
        """AR1, AR2, AR5, IF1, IF2, IF3, and TM1 run no checks."""
        cases = [("stage1", "AR2", "F01"), ("stage1", "IF1", "F01"), ("stage1", "IF2", "F01"),
                 ("stage1", "AR5", "F01"), ("stage2", "TM1", "F01"), ("stage2", "IF3", "F01"),
                 ("stage1", "AR1", "")]
        outs = run_briefs([(name, task, item, ()) for name, task, item in cases])
        for (name, task, item), out in zip(cases, outs):
            with self.subTest(task=task):
                report = self.report_of(out)
                self.assertEqual(report["checks"], [])
                self.assertIn("Checks to run: None", report["prompt"].split("\n"))

    def test_checks_are_listed_in_the_prompt(self):
        """Each check is one ``- <command>`` line under Checks to run."""
        report = self.report_of(brief(shared("stage5"), "DV2"))
        lines = report["prompt"].split("\n")
        self.assertNotIn("Checks to run: None", lines)
        for command in report["checks"]:
            self.assertIn(f"- {command}", lines)

    def test_env_prefix_sets_the_target(self):
        """With ``TROY_MODE_ENV_PREFIX`` set, every step runs ``-p <prefix>``, none ``-n``."""
        out = brief(shared("stage5"), "DV2", env_extra={"TROY_MODE_ENV_PREFIX": PREFIX})
        report = self.report_of(out)
        self.assertNotEqual(report["checks"], [])
        for command in report["checks"]:
            with self.subTest(command=command):
                _, target, _ = pack_words(command)
                self.assertEqual(target, ["-p", PREFIX])

    def test_mamba_is_found_on_the_path_and_never_run(self):
        """``<mamba>`` is the mamba that ``PATH`` finds, and the engine does not run it."""
        fakes = Fakes(fail=True)
        report = self.report_of(brief(shared("stage5"), "DV2", fakes=fakes))
        program, _, _ = pack_words(report["checks"][0])
        self.assertTrue(same_path(program, fakes.mamba), program)
        self.assertEqual(fakes.mamba_calls(), [])
        self.assertEqual(fakes.gh_calls(), [])


class CppChecksTests(FlowCase):
    """The C/C++ pack's steps (design 6.1, interface note)."""

    def test_cmake_comes_first_and_troy_check_reads_doxygen(self):
        """DV1: ``cmake --preset coverage`` first, no uv, and troy-check with the Doxygen log."""
        report = self.report_of(brief(shared("cpp"), "DV1"))
        _, target, words = pack_words(report["checks"][0])
        self.assertEqual(target, ["-n", "wordcount"])
        self.assertEqual(words, ["cmake", "--preset", "coverage"])
        for command in report["checks"]:
            self.assertNotIn("uv", split_command(command), command)
        words = troy_check_step(report["checks"])
        self.assertEqual(option_value(words, "--doc-warnings"), "reports/doxygen.log")
        self.assertEqual(option_value(words, "--title"), F01.title(3))
        self.assertIn("--worktree", words)

    def test_reviewer_runs_troy_check_without_worktree(self):
        """CR1 in a C/C++ project runs troy-check on the commit, without ``--worktree``."""
        report = self.report_of(brief(shared("cpp"), "CR1"))
        self.assertNotIn("--worktree", troy_check_step(report["checks"]))


class RolesTests(FlowCase):
    """Model and effort from ``[roles]`` in the config at HEAD (design 3.2, F04 D32)."""

    def test_model_and_effort_come_from_roles(self):
        """Planted bug "effort passed when unset": each key appears only when the role sets it."""
        project = shared("roles")
        cases = {
            "DV1": {"subagent_type": "tstack:troy-developer", "model": "opus"},
            "CR1": {"subagent_type": "tstack:troy-code-reviewer", "effort": "medium"},
            "AR5": {"subagent_type": "tstack:troy-architect", "model": "opus",
                    "effort": "max"},
        }
        for task, agent in cases.items():
            with self.subTest(task=task):
                self.assertEqual(self.report_of(brief(project, task))["agent"], agent)

    def test_unset_role_gets_neither(self):
        """Planted bug "effort passed when unset": no ``[roles]`` table, no model, no effort."""
        report = self.report_of(brief(shared("stage3"), "DV1"))
        self.assertEqual(report["agent"], {"subagent_type": "tstack:troy-developer"})

    def test_roles_are_read_at_head_not_from_the_working_tree(self):
        """Planted bug "``[roles]`` read from the working tree": an uncommitted edit is ignored."""
        project = Project([base_step(base_files(config_extra=ROLES)), *stages(F01, 2)])
        edited = ('[roles.developer]\nmodel = "sonnet"\neffort = "low"\n\n'
                  '[roles.code-reviewer]\neffort = "medium"\n')
        project.write(CONFIG, config_text(extra=edited))
        report = self.report_of(brief(project, "DV1"))
        self.assertEqual(report["agent"], {"subagent_type": "tstack:troy-developer",
                                           "model": "opus"})
        project.git("commit", "-q", "-a", "-m", "[rules] Set the Developer's model and effort")
        report = self.report_of(brief(project, "DV1"))
        self.assertEqual(report["agent"], {"subagent_type": "tstack:troy-developer",
                                           "model": "sonnet", "effort": "low"})

    def test_roles_added_only_in_the_working_tree_change_nothing(self):
        """Planted bug "``[roles]`` read from the working tree": tree-only roles are not used."""
        project = Project([base_step(), *stages(F01, 2)], branch=WORK_BRANCH)
        project.write(CONFIG, config_text(extra='[roles.developer]\nmodel = "opus"\n'
                                                'effort = "xhigh"\n'))
        report = self.report_of(brief(project, "DV1"))
        self.assertEqual(report["agent"], {"subagent_type": "tstack:troy-developer"})


class InputRoundTests(FlowCase):
    """Input from ``--input-file`` and the review round (design 6.1, F04 D33)."""

    def test_input_and_round_reach_the_brief(self):
        """The findings and round 2 appear in the report and in the prompt."""
        project = shared("stage5")
        findings = project.tmp / "findings-round-1.txt"
        text = "1. R05: src/wordcount/f01.py:3, add a doc comment.\n2. Rename count().\n"
        findings.write_bytes(text.encode("utf-8"))
        report = self.report_of(brief(project, "DV2", "F01", "--round", "2",
                                      "--input-file", str(findings)))
        self.assertEqual(report["round"], 2)
        self.assertEqual(report["input"].rstrip("\n"), text.rstrip("\n"))
        lines = report["prompt"].split("\n")
        self.assertIn("Round: 2", lines)
        self.assertNotIn("Input: None", lines)
        start = next(i for i, line in enumerate(lines) if line.startswith("Input:"))
        after = "\n".join(lines[start:])
        self.assertIn("1. R05: src/wordcount/f01.py:3, add a doc comment.", after)
        self.assertIn("2. Rename count().", after)

    def test_brief_never_calls_gh(self):
        """A gh that fails on every call is never called by brief."""
        fakes = Fakes(fail=True)
        self.report_of(brief(shared("stage3"), "DV1", fakes=fakes))
        self.assertEqual(fakes.gh_calls(), [])


if __name__ == "__main__":
    unittest.main()
