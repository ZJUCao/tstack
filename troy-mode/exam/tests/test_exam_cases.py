"""Cases group (F16 design 4.1, 5.2, 14.1): case.toml, rubric.md, and the twelve cases.

Every case.toml parses; it names a role and a task of F04; its rubric has 3
to 6 criteria; its checks exist; its anchors and patches exist. The unit
tests write their own case folders. RealCasesTests loads the twelve cases of
design 5.2 from troy-mode/exam/cases, which the build writes, and checks each
one both with cases.problems() and with this file's own reading of the
design's rules (the agent files' task headings, the design's check names,
and the exam words), so a gap in problems() does not hide a bad case.
"""

import unittest
from pathlib import Path

from exam_helpers import (CASES_DIR, DESIGN_CHECKS, ROLE_PREFIX, RUBRIC3, agent_tasks, case_data,
                          new_dir, rubric, rubric_count, word_hits, write_case, write_file)
from troyexam import SUBAGENT_ROLES
from troyexam.cases import (REVIEW_TASKS, Criterion, load_case, load_cases, problems,
                            rubric_criteria, task_role)
from troyexam.checks import CHECKS
from troyexam.errors import ExamError

# Design 5.2: case ID -> (role, task).
TWELVE = {
    "dv-mock-notes": ("developer", "DV1"),
    "dv-impl-notes": ("developer", "DV2"),
    "te-plan-asserts": ("test-engineer", "TE1"),
    "te-helper-docs": ("test-engineer", "TE6"),
    "if-example-format": ("interface-designer", "IF1"),
    "if-error-rules": ("interface-designer", "IF1"),
    "ar-design-review": ("architect", "AR2"),
    "ar-error-review": ("architect", "AR2"),
    "tm-plan-expected": ("test-manager", "TM1"),
    "tm-test-review": ("test-manager", "TM2"),
    "cr-mock-review": ("code-reviewer", "CR1"),
    "cr-test-review": ("code-reviewer", "CR1"),
}
# Design 5.2's "Graded mainly by" column: the checks each case must use.
GRADED_BY = {
    "dv-mock-notes": {"mock_bodies_only_raise"},
    "dv-impl-notes": {"no_mock_notes_left", "pack_steps_pass"},
    "te-plan-asserts": {"tests_fail_on_mock", "tests_pass_on_pilot", "tests_fail_on_mutants"},
    "if-example-format": {"ruff_format_blocks"},
    "ar-design-review": {"result_is"},
    "ar-error-review": {"result_is"},
    "tm-test-review": {"result_is"},
    "cr-mock-review": {"result_is"},
    "cr-test-review": {"result_is"},
}
# Design 5.2: the cases graded by the judge (a judge criterion is required).
JUDGED = ("dv-mock-notes", "dv-impl-notes", "te-helper-docs", "if-error-rules",
          "ar-design-review", "ar-error-review", "tm-plan-expected", "tm-test-review",
          "cr-mock-review", "cr-test-review")
REVIEW_PATCH = ("diff --git a/docs/a.md b/docs/a.md\nnew file mode 100644\n--- /dev/null\n"
                "+++ b/docs/a.md\n@@ -0,0 +1 @@\n+A\n")


class LoadTests(unittest.TestCase):
    """load_case and load_cases read case.toml (design 4.1, contract cases.py)."""

    def write(self, data, **kwargs) -> Path:
        """Writes a case folder named after the case's ID."""
        return write_case(new_dir("cases") / data["id"], data, **kwargs)

    def test_the_design_example_parses_field_by_field(self):
        """Design 4.1's case.toml for dv-mock-notes gives every field its value."""
        folder = self.write(case_data("dv-mock-notes"))
        case = load_case(folder)
        self.assertEqual((case.id, case.version, case.role, case.task, case.item),
                         ("dv-mock-notes", 1, "developer", "DV1", "F05"))
        self.assertEqual((case.start.repository, case.start.commit, case.start.branch),
                         ("ZJUCao/recipe-menu", "b966872", "troy-mode/f05-3-mock"))
        self.assertEqual(case.start.pilot, ["#36", "#42", "#55", "#57", "#67", "#81", "#88"])
        self.assertIsNone(case.start.title)
        self.assertEqual(case.start.pr, 1)
        self.assertEqual((case.run.model, case.run.effort, case.run.minutes),
                         ("sonnet", "high", 45))
        self.assertAlmostEqual(case.run.max_cost, 2.50)
        self.assertEqual(case.criteria, [
            Criterion(id="stub-bodies", check="mock_bodies_only_raise", judge=None, must=True,
                      args={}),
            Criterion(id="notes-true", check=None, judge=1, must=True, args={})])
        self.assertIsNone(case.title)
        self.assertIsNone(case.round)
        self.assertEqual(case.judge_files, [])
        self.assertEqual(Path(case.folder).resolve(), folder.resolve())

    def test_other_criterion_keys_go_into_args(self):
        """want and paths are a check's arguments; must false makes a note."""
        data = case_data("ar-sample", role="architect", task="AR2", criteria=[
            {"id": "result", "check": "result_is", "must": True, "want": "changes-requested"},
            {"id": "only", "check": "changed_only", "must": False,
             "paths": ["docs/**", "src/*.py"]}])
        case = load_case(self.write(data, start_patch=REVIEW_PATCH))
        self.assertEqual(case.criteria[0].args, {"want": "changes-requested"})
        self.assertEqual(case.criteria[1].args, {"paths": ["docs/**", "src/*.py"]})
        self.assertIs(case.criteria[1].must, False)

    def test_optional_keys_are_read(self):
        """title, round, [start] title and pr, and [judge] files (contract)."""
        data = case_data("cr-sample", role="code-reviewer", task="CR1",
                         title="[F05 3/6 mock] Load recipes", round=2)
        data["start"] = dict(data["start"], title="[F05 3/6 mock] Load recipes", pr=36)
        data["judge"] = {"files": ["src/**/*.py", "docs/features/*/design.md"]}
        case = load_case(self.write(data, start_patch=REVIEW_PATCH))
        self.assertEqual((case.title, case.round), ("[F05 3/6 mock] Load recipes", 2))
        self.assertEqual((case.start.title, case.start.pr), ("[F05 3/6 mock] Load recipes", 36))
        self.assertEqual(case.judge_files, ["src/**/*.py", "docs/features/*/design.md"])

    def test_a_folder_without_case_toml_raises(self):
        """No case.toml: ExamError."""
        folder = new_dir("cases") / "dv-none"
        folder.mkdir()
        with self.assertRaises(ExamError):
            load_case(folder)

    def test_unreadable_toml_raises(self):
        """case.toml that is not TOML: ExamError."""
        folder = new_dir("cases") / "dv-bad"
        write_file(folder, "case.toml", 'id = "dv-bad"\nversion = \n[start\n')
        with self.assertRaises(ExamError):
            load_case(folder)

    def test_each_missing_key_raises(self):
        """A case.toml that lacks a required key: ExamError, key by key."""
        keys = [("id",), ("version",), ("role",), ("task",), ("item",), ("start",),
                ("start", "repository"), ("start", "commit"), ("start", "branch"), ("run",),
                ("run", "model"), ("run", "effort"), ("run", "minutes"), ("run", "max_cost")]
        for path in keys:
            with self.subTest(missing=".".join(path)):
                data = case_data("dv-miss")
                if len(path) == 1:
                    del data[path[0]]
                else:
                    data[path[0]] = {k: v for k, v in data[path[0]].items() if k != path[1]}
                folder = write_case(new_dir("cases") / "dv-miss", data)
                with self.assertRaises(ExamError):
                    load_case(folder)

    def test_load_cases_reads_every_case_folder_sorted_by_id(self):
        """Subfolders with case.toml, sorted by ID; other folders and files are skipped."""
        root = new_dir("caseroot")
        for case_id in ("dv-b", "dv-a", "dv-c"):
            write_case(root / case_id, case_data(case_id))
        (root / "notes").mkdir()
        write_file(root, "README.txt", "not a case\n")
        self.assertEqual([case.id for case in load_cases(root)], ["dv-a", "dv-b", "dv-c"])


class RubricAndTaskTests(unittest.TestCase):
    """rubric_criteria and task_role (contract)."""

    def test_rubric_criteria_are_the_numbered_lines(self):
        """Lines starting "1. ", "2. ", ... are the criteria; other lines are not."""
        text = ("# Criteria\n\nRead each output.\n\n1. First thing.\n2. Second thing\n"
                "   continues here.\n3. Third thing.\n\nA note, not 4. a criterion.\n")
        found = rubric_criteria(text)
        self.assertEqual(len(found), 3, found)
        for item, word in zip(found, ("First", "Second", "Third")):
            self.assertIn(word, item)

    def test_rubric_criteria_of_the_helpers_rubric(self):
        """The three-criterion fixture rubric has three."""
        self.assertEqual(len(rubric_criteria(RUBRIC3)), 3)

    def test_task_role_maps_each_f04_prefix(self):
        """AR, IF, TM, DV, TE, and CR name the six subagent roles."""
        expected = {"AR2": "architect", "IF1": "interface-designer", "TM7": "test-manager",
                    "DV1": "developer", "TE6": "test-engineer", "CR1": "code-reviewer"}
        for task, role in expected.items():
            with self.subTest(task=task):
                self.assertEqual(task_role(task), role)

    def test_task_role_of_other_tasks_is_none(self):
        """The Product Manager's tasks and unknown prefixes have no subagent role."""
        for task in ("PM3", "XX1", "", "dv1x"):
            with self.subTest(task=task):
                self.assertIsNone(task_role(task))

    def test_review_tasks(self):
        """The review tasks are AR2, TM2, and CR1."""
        self.assertEqual(set(REVIEW_TASKS), {"AR2", "TM2", "CR1"})


class ProblemsTests(unittest.TestCase):
    """problems() finds each defect of a case on its own (design 14.1, contract)."""

    def check(self, data, **kwargs) -> list:
        """Writes a case folder named after the data's ID and returns its problems."""
        folder = write_case(new_dir("cases") / data["id"], data, **kwargs)
        return problems(load_case(folder))

    def assert_one_defect(self, data, **kwargs) -> None:
        """Asserts that problems() reports something for the case."""
        found = self.check(data, **kwargs)
        self.assertIsInstance(found, list)
        self.assertGreaterEqual(len(found), 1, f"no problem found for {data!r} {kwargs!r}")
        self.assertTrue(all(isinstance(p, str) and p for p in found), found)

    def test_a_valid_case_has_no_problem(self):
        """The design 4.1 example, with a rubric and anchors, is valid."""
        self.assertEqual(self.check(case_data("dv-mock-notes")), [])

    def test_valid_review_and_mutant_cases_have_no_problem(self):
        """A review case with start.patch and a test case with a mutant are valid."""
        review = case_data("cr-sample", role="code-reviewer", task="CR1", criteria=[
            {"id": "result", "check": "result_is", "must": True, "want": "changes-requested"}])
        self.assertEqual(self.check(review, start_patch=REVIEW_PATCH), [])
        tests = case_data("te-sample", role="test-engineer", task="TE1", criteria=[
            {"id": "mutants", "check": "tests_fail_on_mutants", "must": True,
             "commit": "a1b2c3d"}])
        self.assertEqual(self.check(tests, mutants={"one": REVIEW_PATCH}), [])

    def test_an_input_with_only_troy_mode_words_is_valid(self):
        """"test", "examples", and "benchmark" are not exam words (design 6.1)."""
        text = "Write the tests and the examples; the benchmark checklist applies.\n"
        self.assertEqual(self.check(case_data("dv-input"), input_text=text), [])

    def test_id_other_than_the_folder_name(self):
        """The folder is dv-folder, case.toml says dv-other."""
        data = case_data("dv-other")
        folder = write_case(new_dir("cases") / "dv-folder", data)
        self.assertGreaterEqual(len(problems(load_case(folder))), 1)

    def test_version_below_one(self):
        """version 0."""
        self.assert_one_defect(case_data("dv-version", version=0))

    def test_role_that_is_not_a_subagent(self):
        """The Product Manager runs as the main session (design 3)."""
        self.assert_one_defect(case_data("pm-sample", role="product-manager", task="PM3"))

    def test_task_of_another_role(self):
        """TE1 is the Test Engineer's, not the Developer's."""
        self.assert_one_defect(case_data("dv-task", task="TE1"))

    def test_task_that_f04_does_not_have(self):
        """DV9 is not an F04 task."""
        self.assert_one_defect(case_data("dv-nine", task="DV9"))

    def test_rubric_with_too_few_or_too_many_criteria(self):
        """2 and 7 criteria are outside 3 to 6."""
        for count in (2, 7):
            with self.subTest(count=count):
                self.assert_one_defect(case_data(f"dv-rubric{count}"), rubric_text=rubric(count))

    def test_rubric_of_three_and_six_criteria_is_valid(self):
        """3 and 6 criteria are inside the range."""
        for count in (3, 6):
            with self.subTest(count=count):
                self.assertEqual(self.check(case_data(f"dv-edge{count}"),
                                            rubric_text=rubric(count)), [])

    def test_check_name_that_does_not_exist(self):
        """A check criterion must name a check of troyexam.checks.CHECKS."""
        data = case_data("dv-check", criteria=[{"id": "x", "check": "no_such_check",
                                                "must": True}])
        self.assert_one_defect(data)

    def test_judge_number_outside_the_rubric(self):
        """judge = 4 with a three-criterion rubric."""
        data = case_data("dv-judge", criteria=[{"id": "x", "judge": 4, "must": True}])
        self.assert_one_defect(data)

    def test_missing_anchor_files(self):
        """Each of the two anchors needs diff.patch and report.md."""
        for side, name in (("fail", "report.md"), ("pass", "diff.patch"),
                           ("fail", "diff.patch"), ("pass", "report.md")):
            with self.subTest(side=side, name=name):
                case_id = f"dv-anchor-{side}-{name[0]}"
                folder = write_case(new_dir("cases") / case_id, case_data(case_id))
                (folder / "anchors" / side / name).unlink()
                self.assertGreaterEqual(len(problems(load_case(folder))), 1)

    def test_review_task_without_start_patch(self):
        """CR1 is a review task and needs start.patch."""
        data = case_data("cr-nopatch", role="code-reviewer", task="CR1", criteria=[
            {"id": "result", "check": "result_is", "must": True, "want": "changes-requested"}])
        self.assert_one_defect(data)

    def test_mutant_check_without_mutants(self):
        """tests_fail_on_mutants needs at least one mutants/*.patch."""
        data = case_data("te-nomutant", role="test-engineer", task="TE1", criteria=[
            {"id": "mutants", "check": "tests_fail_on_mutants", "must": True,
             "commit": "a1b2c3d"}])
        self.assert_one_defect(data)

    def test_exam_word_in_the_input(self):
        """input.md is role-visible and must hold no exam word (design 6.1)."""
        for text in ("Read the rubric before you start.\n", "This is a trap.\n",
                     "Your work is graded later.\n"):
            with self.subTest(text=text):
                self.assert_one_defect(case_data("dv-word"), input_text=text)


class RealCasesTests(unittest.TestCase):
    """The twelve cases of design 5.2 in troy-mode/exam/cases."""

    @classmethod
    def setUpClass(cls):
        """Loads the cases once."""
        cls.cases = {case.id: case for case in load_cases(CASES_DIR)}

    def test_the_twelve_cases_are_there(self):
        """Exactly the case IDs of design 5.2."""
        self.assertEqual(sorted(self.cases), sorted(TWELVE))

    def test_each_case_has_no_problem(self):
        """problems() is empty for every case."""
        for case_id, case in sorted(self.cases.items()):
            with self.subTest(case=case_id):
                self.assertEqual(problems(case), [])

    def test_each_case_has_its_role_and_task(self):
        """Role and task as design 5.2's table says."""
        for case_id, (role, task) in TWELVE.items():
            with self.subTest(case=case_id):
                case = self.cases[case_id]
                self.assertEqual((case.role, case.task), (role, task))
                self.assertIn(task, agent_tasks(role), "not an F04 task of the agent file")
                self.assertTrue(task.startswith(ROLE_PREFIX[role]))

    def test_two_cases_for_each_subagent_role(self):
        """Each of the six roles has two cases, and nothing else has any (design 5.1, 5.2)."""
        roles = [case.role for case in self.cases.values()]
        self.assertEqual(sorted(set(roles)), sorted(SUBAGENT_ROLES))
        for role in SUBAGENT_ROLES:
            with self.subTest(role=role):
                self.assertEqual(roles.count(role), 2)

    def test_each_case_starts_from_the_pilot_repository(self):
        """All start from ZJUCao/recipe-menu (design 5.2), with a version of 1 or more."""
        for case_id, case in sorted(self.cases.items()):
            with self.subTest(case=case_id):
                self.assertEqual(case.start.repository, "ZJUCao/recipe-menu")
                self.assertRegex(case.start.commit, r"^[0-9a-f]{7,40}$")
                self.assertTrue(case.start.branch.startswith("troy-mode/"), case.start.branch)
                self.assertGreaterEqual(case.version, 1)

    def test_rubrics_have_three_to_six_criteria(self):
        """Counted apart from rubric_criteria (eval playbook, design 4.4)."""
        for case_id in sorted(self.cases):
            with self.subTest(case=case_id):
                text = (CASES_DIR / case_id / "rubric.md").read_text(encoding="utf-8")
                self.assertGreaterEqual(rubric_count(text), 3)
                self.assertLessEqual(rubric_count(text), 6)

    def test_checks_are_the_designs_and_judge_numbers_fit(self):
        """Every check criterion names a check of design 4.3 that CHECKS holds."""
        for case_id, case in sorted(self.cases.items()):
            text = (CASES_DIR / case_id / "rubric.md").read_text(encoding="utf-8")
            for criterion in case.criteria:
                with self.subTest(case=case_id, criterion=criterion.id):
                    self.assertTrue((criterion.check is None) != (criterion.judge is None))
                    if criterion.check is not None:
                        self.assertIn(criterion.check, DESIGN_CHECKS)
                        self.assertIn(criterion.check, CHECKS)
                    else:
                        self.assertGreaterEqual(criterion.judge, 1)
                        self.assertLessEqual(criterion.judge, rubric_count(text))

    def test_graded_by_the_designs_checks(self):
        """Each case uses the checks of design 5.2's "Graded mainly by" column."""
        for case_id, needed in GRADED_BY.items():
            with self.subTest(case=case_id):
                names = {c.check for c in self.cases[case_id].criteria if c.check}
                self.assertLessEqual(needed, names)

    def test_judged_cases_have_a_judge_criterion(self):
        """The cases design 5.2 grades by the judge have a judge criterion that is a must."""
        for case_id in JUDGED:
            with self.subTest(case=case_id):
                judged = [c for c in self.cases[case_id].criteria if c.judge is not None]
                self.assertTrue(judged)
                self.assertTrue(any(c.must for c in judged))

    def test_review_cases_want_changes_requested(self):
        """A review case's trap is approving the round-1 head (design 5.1)."""
        for case_id, case in sorted(self.cases.items()):
            if case.task not in ("AR2", "TM2", "CR1"):
                continue
            with self.subTest(case=case_id):
                wants = [c.args.get("want") for c in case.criteria if c.check == "result_is"]
                self.assertEqual(wants, ["changes-requested"])

    def test_review_cases_have_a_patch_and_a_title(self):
        """start.patch holds the round-1 head; [start] title is its commit subject (4.1)."""
        for case_id, case in sorted(self.cases.items()):
            if case.task not in ("AR2", "TM2", "CR1"):
                continue
            with self.subTest(case=case_id):
                patch = CASES_DIR / case_id / "start.patch"
                self.assertTrue(patch.is_file())
                self.assertIn("diff --git ", patch.read_text(encoding="utf-8"))
                self.assertIsInstance(case.start.title, str)
                self.assertTrue(case.start.title.strip())

    def test_the_test_writing_case_has_mutants(self):
        """te-plan-asserts has a mutant per finding of the pilot's round-1 review (5.2)."""
        mutants = sorted((CASES_DIR / "te-plan-asserts" / "mutants").glob("*.patch"))
        self.assertGreaterEqual(len(mutants), 1)
        for path in mutants:
            with self.subTest(mutant=path.name):
                self.assertIn("diff --git ", path.read_text(encoding="utf-8"))

    def test_anchors_exist(self):
        """Each case has the pilot's fail and pass outputs, a diff and a report each.

        A review changes no file, so a review case's diff may be empty; its
        report never is.
        """
        for case_id in sorted(self.cases):
            review = self.cases[case_id].task in ("AR2", "TM2", "CR1")
            for side in ("fail", "pass"):
                for name in ("diff.patch", "report.md"):
                    with self.subTest(case=case_id, file=f"{side}/{name}"):
                        path = CASES_DIR / case_id / "anchors" / side / name
                        self.assertTrue(path.is_file())
                        if not (review and name == "diff.patch"):
                            self.assertGreater(path.stat().st_size, 0)

    def test_inputs_hold_no_exam_word(self):
        """input.md is role-visible: no exam word, by this file's own check (design 6.1)."""
        for case_id in sorted(self.cases):
            path = CASES_DIR / case_id / "input.md"
            if not path.is_file():
                continue
            with self.subTest(case=case_id):
                self.assertEqual(word_hits(path.read_text(encoding="utf-8")), [])

    def test_case_branches_hold_no_exam_word(self):
        """The branch is role-visible too."""
        for case_id, case in sorted(self.cases.items()):
            with self.subTest(case=case_id):
                self.assertEqual(word_hits(case.start.branch), [])


if __name__ == "__main__":
    unittest.main()
