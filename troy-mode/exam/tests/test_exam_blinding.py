"""Blinding group (F16 design 6.1, 6.2, 14.1): exam words, random letters, and the judge.

The end-to-end side of this group (no exam word in a built run's paths,
branch, variables, Input, or stand-in messages; the two versions'
role-visible texts differing only by random letters; the judge's folder in a
real exam) is in test_exam_cli.py. This file tests the pieces.

Planted bugs of design 14.2 caught here:

- "the judge's folder holding the key": JudgeFolderTests.test_only_the_rubric_and_the_outputs
  (and test_exam_cli.MainExamTests.test_judge_folder_holds_only_rubric_and_outputs).
- "a label that names its version": LabelTests.test_labels_are_r_numbers_that_name_nothing
  (and test_exam_cli.MainExamTests.test_judge_labels_are_shuffled_r_numbers).
"""

import json
import random
import re
import sys
import unittest
from pathlib import Path

from exam_helpers import EXAM_WORDS, new_dir, word_hits
from troyexam import AGENT_PREFIX, INSTALLED_OFF, SUBAGENT_ROLES
from troyexam.blinding import EXAM_WORDS as CODE_WORDS
from troyexam.blinding import exam_words, random_letters
from troyexam.errors import ExamError
from troyexam.judge import (anchors_ok, assign_labels, build_folder, command_line, judge_prompt,
                            parse_verdict, schema)
from troyexam.runner import driver_prompt

SCHEMA = {"type": "object", "properties": {"sets": {"type": "array", "items": {
    "type": "object", "properties": {
        "label": {"type": "string"},
        "criteria": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "integer"}, "pass": {"type": "boolean"},
            "evidence": {"type": "string"}}, "required": ["id", "pass", "evidence"]}}},
    "required": ["label", "criteria"]}}}, "required": ["sets"]}


class ExamWordsTests(unittest.TestCase):
    """exam_words (design 6.1, contract blinding.py)."""

    def test_the_list_is_the_designs(self):
        """The fifteen words, in the design's order; test and benchmark are not among them."""
        self.assertEqual(tuple(CODE_WORDS), EXAM_WORDS)
        self.assertNotIn("test", CODE_WORDS)
        self.assertNotIn("benchmark", CODE_WORDS)

    def test_each_word_is_found(self):
        """Each word on its own is found, case-insensitively."""
        for word in EXAM_WORDS:
            with self.subTest(word=word):
                self.assertEqual(exam_words(f"the {word} here"), [word])
                self.assertEqual(exam_words(word.upper()), [word])

    def test_endings(self):
        """The word plus s, es, d, ed, r, rs, er, ers, or ing, and ing after a dropped e."""
        cases = {"evals": "eval", "evaled": "eval", "exams": "exam", "examer": "exam",
                 "traps": "trap", "judged": "judge", "judges": "judge", "judging": "judge",
                 "rubrics": "rubric", "graded": "grade", "grader": "grade", "graders": "grade",
                 "grading": "grade", "scores": "score", "scored": "score", "scoring": "score",
                 "compared": "compare", "comparing": "compare", "experiments": "experiment",
                 "candidates": "candidate", "variants": "variant", "arenas": "arena",
                 "baselines": "baseline", "hillclimbing": "hillclimb", "sandboxes": "sandbox"}
        for text, word in cases.items():
            with self.subTest(text=text):
                self.assertEqual(exam_words(text), [word])

    def test_words_inside_longer_words_are_not_found(self):
        """examples, upgrade, evaluate, trapped, and the like hold nothing."""
        for text in ("examples", "upgrade", "evaluate", "examine", "trapped", "entrap",
                     "scoreboard", "comparison", "variation", "sandboxing2x", "testing",
                     "benchmark", "benchmarks", "tests", "test plan", "recipe-menu",
                     "troy-mode/f05-3-mock", "tstack"):
            with self.subTest(text=text):
                expected = ["sandbox"] if text == "sandboxing2x" else []
                self.assertEqual(exam_words(text), expected)

    def test_separators_and_camel_case(self):
        """Anything but a letter separates, and so does a lower-to-upper change."""
        for text in ("examFolder", "my_exam_dir", "x-eval-1", "eval1", "path/to/Rubric.md",
                     "SANDBOX_ROOT", "runGrader"):
            with self.subTest(text=text):
                self.assertEqual(len(exam_words(text)), 1, text)
        self.assertEqual(exam_words("examFolder"), ["exam"])
        self.assertEqual(exam_words("runGrader"), ["grade"])

    def test_order_and_each_once(self):
        """Design order, then extra, each word once."""
        self.assertEqual(exam_words("score the eval, then the eval again"), ["eval", "score"])
        self.assertEqual(exam_words("alpha side, sandbox", extra=["alpha", "omega"]),
                         ["sandbox", "alpha"])
        self.assertEqual(exam_words("nothing here", extra=["alpha"]), [])

    def test_extra_words_are_the_version_labels(self):
        """The labels the exam gives the two versions are refused too (design 6.1)."""
        self.assertEqual(exam_words("folder for the sidea run", extra=["sidea", "sideb"]),
                         ["sidea"])
        self.assertEqual(exam_words("folder for the SIDEB run", extra=["sidea", "sideb"]),
                         ["sideb"])
        self.assertEqual(exam_words("folder for the sidec run", extra=["sidea", "sideb"]), [])

    def test_matches_this_files_reading_of_the_rule(self):
        """On a mixed text, the code and the tests' own rule agree."""
        text = ("Grading of examFolder/variant_1 with BASELINE.txt, examples, upgrade, "
                "benchmark-checklist, tests/test_x.py, and a sandboxed run")
        self.assertEqual(exam_words(text), word_hits(text))
        self.assertEqual(word_hits(text), ["exam", "grade", "variant", "baseline", "sandbox"])


class RigidRandom(random.Random):
    """A Random whose draws spell given letters, through random() and getrandbits() alike."""

    def __init__(self, text: str) -> None:
        """Stores the letters to spell, then repeats ``q``."""
        self._letters = list(text)
        super().__init__(0)

    def _next(self) -> int:
        """The next letter's index in a-z."""
        letter = self._letters.pop(0) if self._letters else "q"
        return ord(letter) - ord("a")

    def random(self) -> float:
        """A float that picks the next letter from a 26-letter sequence."""
        return (self._next() + 0.5) / 26

    def getrandbits(self, k: int) -> int:
        """Bits that pick the next letter for _randbelow(26)."""
        return self._next() % (1 << k)


class RandomLettersTests(unittest.TestCase):
    """random_letters (design 4.2 step 7, contract)."""

    def test_six_lower_case_letters(self):
        """Six by default, n when asked; with or without a generator."""
        self.assertRegex(random_letters(), r"^[a-z]{6}$")
        self.assertRegex(random_letters(random.Random(3)), r"^[a-z]{6}$")
        self.assertRegex(random_letters(random.Random(3), n=9), r"^[a-z]{9}$")

    def test_no_exam_word_as_a_substring_over_many_draws(self):
        """2000 draws, none holding an exam word anywhere."""
        rng = random.Random(1234)
        for _ in range(2000):
            letters = random_letters(rng)
            self.assertFalse([w for w in EXAM_WORDS if w in letters], letters)

    def test_a_draw_that_spells_an_exam_word_is_not_returned(self):
        """When the generator first spells "evalqq", another name comes back."""
        for spelled in ("evalqq", "qtrapq", "examqq"):
            with self.subTest(spelled=spelled):
                letters = random_letters(RigidRandom(spelled + "zzzzzzzzzzzz"))
                self.assertRegex(letters, r"^[a-z]{6}$")
                self.assertFalse([w for w in EXAM_WORDS if w in letters], letters)


class DriverPromptBlindingTests(unittest.TestCase):
    """The driver prompt holds no exam word for any role (design 6.1, 11.3)."""

    def test_no_exam_word_for_any_role(self):
        """Each of the six roles, with a brief that holds none either."""
        brief = "Task: DV1, write the mock.\nItem: F01\nInput: None\n"
        for role in SUBAGENT_ROLES:
            with self.subTest(role=role):
                prompt = driver_prompt(role, "sonnet", "high", brief)
                self.assertEqual(word_hits(prompt), [])
                self.assertIn(AGENT_PREFIX + role, prompt)


class LabelTests(unittest.TestCase):
    """assign_labels (design 6.2)."""

    ITEMS = ("base-r1", "base-r2", "head-r1", "head-r2", "anchor-fail", "anchor-pass")

    def test_labels_are_r_numbers_that_name_nothing(self):
        """R01 to R06, each item once, and no label holds any part of an item's name."""
        labels = assign_labels(list(self.ITEMS), random.Random(5))
        self.assertEqual(sorted(labels), [f"R{i:02d}" for i in range(1, 7)])
        self.assertEqual(sorted(labels.values()), sorted(self.ITEMS))
        for label in labels:
            self.assertRegex(label, r"^R\d{2}$")
            for word in ("base", "head", "anchor", "fail", "pass"):
                self.assertNotIn(word, label.lower())

    def test_labels_are_shuffled(self):
        """Over 20 generators, the order of the items under R01.. is not always the same."""
        orders = set()
        for seed in range(20):
            labels = assign_labels(list(self.ITEMS), random.Random(seed))
            orders.add(tuple(labels[key] for key in sorted(labels)))
        self.assertGreater(len(orders), 1)
        self.assertTrue(any(order != self.ITEMS for order in orders))

    def test_twelve_items_get_twelve_labels(self):
        """Ten runs and two anchors: R01 to R12."""
        items = [f"run{i}" for i in range(10)] + ["anchor-fail", "anchor-pass"]
        labels = assign_labels(items, random.Random(1))
        self.assertEqual(sorted(labels), [f"R{i:02d}" for i in range(1, 13)])


class JudgeFolderTests(unittest.TestCase):
    """build_folder: the rubric and the outputs, nothing else (design 6.2)."""

    def test_only_the_rubric_and_the_outputs(self):
        """rubric.md and <label>/<file>; no key, brief, agent file, transcript, model, or cost."""
        folder = new_dir("jfold") / "panel"
        project = r"C:\work\runs\qhzwtd\wordcount"
        plugin = r"C:\work\runs\qhzwtd\tstack"
        outputs = {
            "R01": {"diff.patch": "diff --git a/src/x.py b/src/x.py\n+X = 1\n",
                    "report.md": f"Checks: ran in {project}\nSummary: done.\n",
                    "files/src/x.py": "X = 1\n"},
            "R02": {"diff.patch": "", "report.md": f"Read {plugin}/skills/a/SKILL.md and "
                                                   f"{project.replace(chr(92), '/')}/docs.\n"}}
        replacements = {project: "<project>", project.replace("\\", "/"): "<project>",
                        plugin: "<plugin>", plugin.replace("\\", "/"): "<plugin>"}
        build_folder(folder, "1. A criterion.\n2. B.\n3. C.\n", outputs, replacements)
        files = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())
        self.assertEqual(files, ["R01/diff.patch", "R01/files/src/x.py", "R01/report.md",
                                 "R02/diff.patch", "R02/report.md", "rubric.md"])
        self.assertEqual((folder / "rubric.md").read_text(encoding="utf-8"),
                         "1. A criterion.\n2. B.\n3. C.\n")
        r01 = (folder / "R01" / "report.md").read_text(encoding="utf-8")
        r02 = (folder / "R02" / "report.md").read_text(encoding="utf-8")
        self.assertEqual(r01, "Checks: ran in <project>\nSummary: done.\n")
        self.assertEqual(r02, "Read <plugin>/skills/a/SKILL.md and <project>/docs.\n")
        self.assertEqual((folder / "R01" / "files" / "src" / "x.py").read_text(encoding="utf-8"),
                         "X = 1\n")


class JudgeCallTests(unittest.TestCase):
    """The judge's schema, prompt, command line, and verdict (design 6.2, 11.4)."""

    def test_schema(self):
        """For each label and criterion: pass or fail with evidence."""
        self.assertEqual(schema(), SCHEMA)

    def test_prompt_says_separate_runs_and_rubric_only(self):
        """It names rubric.md, says the outputs are separate runs of one task, names no side."""
        labels = ["R01", "R02", "R03"]
        prompt = judge_prompt(labels, 3)
        self.assertIn("rubric.md", prompt)
        self.assertRegex(prompt.lower(), r"separate")
        for word in ("base", "head", "baseline", "candidate"):
            self.assertIsNone(re.search(rf"\b{word}\b", prompt.lower()), word)

    def test_command_line(self):
        """Opus, high effort, three tools, the installed plugin off, no --plugin-dir."""
        cli = Path("C:/cli/2.1.325/abc/claude.exe")
        text = json.dumps(SCHEMA)
        self.assertEqual(command_line(cli, "PROMPT", text, 3.0), [
            str(cli), "-p", "PROMPT", "--model", "opus", "--effort", "high",
            "--tools", "Read,Glob,Grep", "--settings", INSTALLED_OFF, "--json-schema", text,
            "--output-format", "json", "--max-budget-usd", "3.00"])

    def test_command_line_of_a_python_stand_in(self):
        """A .py CLI runs with this Python."""
        cli = Path("/x/standin.py")
        line = command_line(cli, "P", "{}", 1.5)
        self.assertEqual(line[:2], [sys.executable, str(cli)])
        self.assertNotIn("--plugin-dir", line)
        self.assertEqual(line[-2:], ["--max-budget-usd", "1.50"])

    def verdict(self, sets) -> dict:
        """A judge output with structured_output."""
        return {"type": "result", "structured_output": {"sets": sets}}

    def test_parse_verdict(self):
        """label -> criterion number -> (pass, evidence)."""
        sets = [{"label": "R01", "criteria": [{"id": 1, "pass": True, "evidence": "a"},
                                              {"id": 2, "pass": False, "evidence": "b"}]},
                {"label": "R02", "criteria": [{"id": 2, "pass": True, "evidence": "c"},
                                              {"id": 1, "pass": False, "evidence": "d"}]}]
        found = parse_verdict(self.verdict(sets), ["R01", "R02"], 2)
        self.assertEqual(found, {"R01": {1: (True, "a"), 2: (False, "b")},
                                 "R02": {1: (False, "d"), 2: (True, "c")}})

    def test_a_missing_label_or_criterion_raises(self):
        """Every label and every criterion 1..count must be graded."""
        one = [{"label": "R01", "criteria": [{"id": 1, "pass": True, "evidence": "a"},
                                             {"id": 2, "pass": True, "evidence": "b"}]}]
        with self.assertRaises(ExamError):
            parse_verdict(self.verdict(one), ["R01", "R02"], 2)
        short = [{"label": "R01", "criteria": [{"id": 1, "pass": True, "evidence": "a"}]}]
        with self.assertRaises(ExamError):
            parse_verdict(self.verdict(short), ["R01"], 2)

    def test_anchors_ok(self):
        """True only when the pass anchor passes and the fail anchor fails."""
        key = {"R01": "anchor-fail", "R02": "run-1", "R03": "anchor-pass"}
        self.assertTrue(anchors_ok({"R01": False, "R02": True, "R03": True}, key))
        self.assertTrue(anchors_ok({"R01": False, "R02": False, "R03": True}, key))
        self.assertFalse(anchors_ok({"R01": True, "R02": True, "R03": True}, key))
        self.assertFalse(anchors_ok({"R01": False, "R02": True, "R03": False}, key))
        self.assertFalse(anchors_ok({"R01": True, "R02": True, "R03": False}, key))


if __name__ == "__main__":
    unittest.main()
