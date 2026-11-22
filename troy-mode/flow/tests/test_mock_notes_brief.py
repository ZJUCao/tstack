"""The mock-note text on the Task line of DV1, DV2, and CR1 (F07 design 6.4, 14.1; D205 to D207).

``brief`` adds a fixed text, chosen by ``[lang] name`` in the config at HEAD, to the Task line
after the task's own sentence, and only for a feature's stage PR, the redo of a stage in rework
included: DV1 and CR1 at PR 3 get the rule for the notes and its check, with the pack's
sentences; DV2 and CR1 at PR 5 get the deletion and its check, the same for both languages.
CR1 at PR 4, every other task, a side PR, a bug, a version, and a rule get no text.

Planted bugs of design 14.2 (D205 to D207) caught here:

- "CR1 at PR 4 given PR 3's text": ``NoTextTests.test_other_cases_hold_no_text`` (rows
  "CR1 at PR 4" and "CR1 at PR 4 in rework").
- "CR1 in a test-fix side PR given PR 5's text": ``NoTextTests.test_other_cases_hold_no_text``
  (row "CR1 in a test-fix side PR").
- "CR1 at PR 3 given PR 5's text": ``StageTextTests.test_no_other_text`` and
  ``test_pr3_reviews_do_not_ask_to_delete``.
- "the Python sentences in a C/C++ brief":
  ``StageTextTests.test_cpp_briefs_hold_no_python_sentence``.
- "the redo of PR 3 given no text": ``StageTextTests.test_text_appears_once`` (rows "DV1 on the
  redo of PR 3" and "CR1 on the redo of PR 3").

``HeadConfigTests`` checks that the text follows ``[lang] name`` at HEAD, not in the working tree.
"""

import unittest
from dataclasses import replace

from flow_helpers import (
    CONFIG, F01, F02, F03, FlowCase, Project, base_files, base_step, bug_step, bug_title,
    change_step, config_text, parallel, rework, stages,
)
from rule_helpers import rules_step

# The quote blocks of design 6.4, word for word: the single backticks and the
# double-backtick spans are part of the text.
DV1_PY = (
    "Where the mock does less than a doc comment says, add the mock's note as a paragraph of its "
    "own, after the description and before Args, Attributes, Returns, and Raises. Use these "
    "sentences word for word: `The mock raises ``NotImplementedError``.` for a function or method "
    "whose body only raises; `The mock's constructor raises ``NotImplementedError``.` in the doc "
    "comment of a class that writes its own constructor, besides the constructor's own note; "
    "`The mock leaves out the constructor's checks.` for a class whose constructor Python "
    "generates, such as a dataclass's, when the design has that constructor check its arguments, "
    "or `The mock keeps the values as given and leaves out the constructor's checks.` when it "
    "also changes them, for example by sorting; and, for a body that the design itself gives the "
    "mock, one sentence that says all it does, such as `The mock reads no file, writes nothing, "
    "raises nothing, and gives 0.` Every other body only raises, a constructor that the class "
    "writes too, and a generated constructor gets no `__post_init__`. A note never points "
    "elsewhere: no \"these\", \"this\", \"above\", or \"below\". The description and the sections "
    "describe the implementation as the design gives it, for example \"The constructor checks its "
    "values, as Raises gives them.\", so that PR 5 has only the notes to delete."
)
DV1_CPP = (
    "Where the mock does less than a doc comment says, add the mock's note as a paragraph of its "
    "own, after the description and before Args, Attributes, Returns, and Raises. Use these "
    "sentences word for word: `The mock throws ``troy::NotImplemented``.` for a function or "
    "method whose body only throws; `The mock's constructor throws ``troy::NotImplemented``.` in "
    "the doc comment of a class that writes its own constructor, besides the constructor's own "
    "note; and, for a body that the design itself gives the mock, one sentence that says all it "
    "does, such as `The mock reads no file, writes nothing, throws nothing, and returns 0.` Every "
    "other body only throws, a constructor's too. A note never points elsewhere: no \"these\", "
    "\"this\", \"above\", or \"below\". The description and the sections describe the "
    "implementation as the design gives it, for example \"The constructor checks its values, as "
    "Raises gives them.\", so that PR 5 has only the notes to delete."
)
CR1_PR3_PY = (
    "Check the mock's notes. Every stub, and every class whose constructor does less in the mock "
    "than in the design, has one, as a paragraph of its own after the description. Each is one of "
    "these sentences, word for word: `The mock raises ``NotImplementedError``.` for a body that "
    "only raises; `The mock's constructor raises ``NotImplementedError``.` for a class that "
    "writes its own constructor; `The mock leaves out the constructor's checks.`, or `The mock "
    "keeps the values as given and leaves out the constructor's checks.` when the constructor "
    "also changes them, for a class whose constructor Python generates; or one sentence that says "
    "all that a body given by the design does. No other sentence says what only the mock does."
)
CR1_PR3_CPP = (
    "Check the mock's notes. Every stub, and every class whose constructor does less in the mock "
    "than in the design, has one, as a paragraph of its own after the description. Each is one of "
    "these sentences, word for word: `The mock throws ``troy::NotImplemented``.` for a body that "
    "only throws; `The mock's constructor throws ``troy::NotImplemented``.` for a class that "
    "writes its own constructor; or one sentence that says all that a body given by the design "
    "does. No other sentence says what only the mock does."
)
DV2_TEXT = (
    "Delete every paragraph of the feature's doc comments that starts with \"The mock\". Change "
    "the rest of those doc comments only where a sentence is not true of the code you write."
)
CR1_PR5 = (
    "Check that no paragraph of the feature's doc comments starts with \"The mock\", and that "
    "every other change to those doc comments makes them true of the code."
)
TEXTS = {"DV1_PY": DV1_PY, "DV1_CPP": DV1_CPP, "CR1_PR3_PY": CR1_PR3_PY,
         "CR1_PR3_CPP": CR1_PR3_CPP, "DV2": DV2_TEXT, "CR1_PR5": CR1_PR5}

# The sentences of design 6.4's table (D205), by pack.
PY_SENTENCES = (
    "The mock raises ``NotImplementedError``.",
    "The mock's constructor raises ``NotImplementedError``.",
    "The mock leaves out the constructor's checks.",
    "The mock keeps the values as given and leaves out the constructor's checks.",
)
CPP_SENTENCES = (
    "The mock throws ``troy::NotImplemented``.",
    "The mock's constructor throws ``troy::NotImplemented``.",
)
# Words of one pack's text that the other pack's brief must never hold.
PY_ONLY = ("NotImplementedError", "__post_init__", "Python generates", "The mock raises",
           "constructor raises", "raises nothing", "leaves out the constructor's checks",
           "keeps the values as given")
CPP_ONLY = ("troy::NotImplemented", "throw", "returns 0.")
# Parts of the four texts that a brief without text must not hold.
MARKERS = (*PY_SENTENCES, *CPP_SENTENCES, "The mock reads no file", "mock's note",
           "Where the mock does less than a doc comment says", "\"The mock\"")

F03V2 = replace(F03, version="v0.2")
CRASH = "Crash on empty history"
TEST_FIX_F01 = "[F01 test-fix] Wrong count in F01-T01"
B12_TEST = bug_title("B12", "test", CRASH)
REFACTOR = "[refactor] Apply P01 to counting"
_PROJECTS: dict = {}

# (label, clone, task, item, --title or None, the key of the text in TEXTS)
WITH_TEXT = [
    ("DV1 at PR 3, Python", "py3", "DV1", "F01", None, "DV1_PY"),
    ("DV1 at PR 3 with its title, Python", "py3", "DV1", "F01", F01.title(3), "DV1_PY"),
    ("CR1 at PR 3, Python", "py3", "CR1", "F01", None, "CR1_PR3_PY"),
    ("DV1 at PR 3, C/C++", "cpp3", "DV1", "F01", None, "DV1_CPP"),
    ("CR1 at PR 3, C/C++", "cpp3", "CR1", "F01", None, "CR1_PR3_CPP"),
    ("DV2 at PR 5, Python", "py5", "DV2", "F01", None, "DV2"),
    ("CR1 at PR 5, Python", "py5", "CR1", "F01", None, "CR1_PR5"),
    ("DV2 at PR 5, C/C++", "cpp5", "DV2", "F01", None, "DV2"),
    ("CR1 at PR 5, C/C++", "cpp5", "CR1", "F01", None, "CR1_PR5"),
    ("DV1 on the redo of PR 3", "rework", "DV1", "F01", F01.title(3), "DV1_PY"),
    ("CR1 on the redo of PR 3", "rework", "CR1", "F01", F01.title(3), "CR1_PR3_PY"),
]
# (label, clone, task, item, --title or None)
WITHOUT_TEXT = [
    ("CR1 at PR 4", "py4", "CR1", "F01", None),
    ("TE1 at PR 4", "py4", "TE1", "F01", None),
    ("TM2 at PR 4", "py4", "TM2", "F01", None),
    ("CR1 at PR 4 in rework", "rework", "CR1", "F01", None),
    ("CR1 in a test-fix side PR", "py5", "CR1", "F01", TEST_FIX_F01),
    ("TE3 in a test-fix side PR", "py5", "TE3", "F01", TEST_FIX_F01),
    ("TM2 in a test-fix side PR", "py5", "TM2", "F01", TEST_FIX_F01),
    ("CR1 in a bug's test PR", "py3", "CR1", "B12", B12_TEST),
    ("CR1 in a bug's fix PR", "bug", "CR1", "B12", None),
    ("DV3 in a bug's fix PR", "bug", "DV3", "B12", None),
    ("CR1 in a bug's fix PR, C/C++", "cppbug", "CR1", "B12", None),
    ("DV3 in a bug's fix PR, C/C++", "cppbug", "DV3", "B12", None),
    ("IF1 at PR 1", "py1", "IF1", "F01", None),
    ("TM1 at PR 2", "py2", "TM1", "F01", None),
    ("AR5 at PR 3", "py3", "AR5", "F01", None),
    ("AR3 at PR 3", "py3", "AR3", "F01", None),
    ("AR4 at PR 3", "py3", "AR4", "F01", None),
    ("AR5 at PR 5", "py5", "AR5", "F01", None),
    ("TM3 at PR 5", "py5", "TM3", "F01", None),
    ("TM4 at PR 5", "py5", "TM4", "F01", None),
    ("IF4 at PR 5", "py5", "IF4", "F01", None),
    ("DV4 at PR 5", "py5", "DV4", "F01", None),
    ("TM6 at PR 5", "py5", "TM6", "F01", None),
    ("CR1 in a version's tests PR", "version", "CR1", "v0.1", None),
    ("CR1 in a rule's refactor PR", "rule", "CR1", "P01", REFACTOR),
    ("DV5 in a rule's refactor PR", "rule", "DV5", "P01", REFACTOR),
]


def shared(name: str) -> Project:
    """A clone shared by the tests, built on first use; tests must not change it.

    Args:
        name: ``py1`` to ``py5`` (Python, F01's current stage), ``cpp3`` and
            ``cpp5`` (the C/C++ pack, F01 at stage 3 or 5), ``rework`` (F01's
            stages 1 to 3 merged, then a change that marks it for rework),
            ``bug`` and ``cppbug`` (F01 at stage 3 and B12's PR A merged, in
            Python or C/C++), ``version`` (F01 and F02 accepted for v0.1, F03 of
            v0.2 at stage 5), or ``rule`` (the rules fixture, F01 at stage 3).

    Returns:
        The clone.
    """
    if name not in _PROJECTS:
        cpp = base_step(base_files(lang="cpp"))
        test_b12 = bug_step("B12", "test", CRASH)
        if name.startswith("py"):
            steps = [base_step(), *stages(F01, int(name[-1]) - 1)]
        elif name.startswith("cpp") and name[-1].isdigit():
            steps = [cpp, *stages(F01, int(name[-1]) - 1)]
        elif name == "rework":
            steps = [base_step(), *stages(F01, 3), change_step(features=(rework(F01), F02))]
        elif name == "bug":
            steps = [base_step(), *stages(F01, 2), test_b12]
        elif name == "cppbug":
            steps = [cpp, *stages(F01, 2), test_b12]
        elif name == "version":
            steps = [base_step(base_files((F01, F02, F03V2))), *stages(F01, 6), *stages(F02, 6),
                     *stages(F03V2, 4)]
        elif name == "rule":
            steps = [rules_step(), *stages(F01, 2)]
        else:
            raise KeyError(name)
        _PROJECTS[name] = Project(steps)
    return _PROJECTS[name]


def brief(case):
    """Runs ``brief --task <task> --item <item> [--title <title>] --json`` for one case.

    Args:
        case: ``(label, clone, task, item, title or None, ...)``.

    Returns:
        The outcome.
    """
    _, name, task, item, title = case[:5]
    args = ["brief", "--task", task, "--item", item]
    if title is not None:
        args += ["--title", title]
    return shared(name).run(*args)


def task_line(prompt: str) -> str:
    """The prompt's ``Task:`` line, or "" when there is none."""
    return next((line for line in prompt.split("\n") if line.startswith("Task: ")), "")


class MockNoteCase(FlowCase):
    """Runs the cases' briefs once and reads their prompts."""

    CASES: list = []

    @classmethod
    def setUpClass(cls):
        """Builds the clones, then runs every case's brief side by side."""
        for name in sorted({case[1] for case in cls.CASES}):
            shared(name)
        outs = parallel(brief, cls.CASES)
        cls.outs = dict(zip([case[0] for case in cls.CASES], outs))

    def prompt_of(self, label: str, task: str) -> str:
        """The prompt of one case's brief, which must succeed for the task asked.

        Args:
            label: The case's label.
            task: The task the brief must be for.

        Returns:
            The prompt.
        """
        report = self.report_of(self.outs[label], 0, "brief")
        prompt = report.get("prompt") or ""
        self.assertTrue(task_line(prompt).startswith(f"Task: {task}, "), prompt)
        return prompt


class StageTextTests(MockNoteCase):
    """DV1 and CR1 at PR 3, DV2 and CR1 at PR 5, and the redo of PR 3: their own text."""

    CASES = WITH_TEXT

    def test_text_appears_once(self):
        """Each case's Task line holds its text of design 6.4 exactly once, as does the prompt."""
        for label, _, task, _, _, key in WITH_TEXT:
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                line = task_line(prompt)
                self.assertEqual(line.count(TEXTS[key]), 1, line)
                self.assertEqual(prompt.count(TEXTS[key]), 1, prompt)

    def test_no_other_text(self):
        """No case holds another task's, stage's, or language's text."""
        for label, _, task, _, _, key in WITH_TEXT:
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                for other, text in TEXTS.items():
                    if other != key:
                        self.assertNotIn(text, prompt, f"{other} in {label}")

    def test_text_follows_the_task_sentence(self):
        """The task's own sentence starts the Task line; the text comes after it."""
        for label, _, task, _, _, key in WITH_TEXT:
            with self.subTest(case=label):
                line = task_line(self.prompt_of(label, task))
                where = line.find(TEXTS[key])
                self.assertGreater(where, 0, line)
                before = line[:where]
                self.assertTrue(before.startswith(f"Task: {task}, "), line)
                self.assertTrue(before.rstrip().endswith("."), line)
                end = line.find(". ")
                self.assertNotEqual(end, -1, line)
                self.assertLess(end, where, line)

    def test_dv1_starts_with_its_task_sentence(self):
        """DV1's Task line still starts with "Task: DV1, write the mock of F01's interfaces."."""
        for label, _, task, _, _, _ in WITH_TEXT:
            if task != "DV1":
                continue
            with self.subTest(case=label):
                line = task_line(self.prompt_of(label, task))
                self.assertTrue(line.startswith("Task: DV1, write the mock of F01's interfaces. "),
                                line)

    def test_python_briefs_hold_no_cpp_sentence(self):
        """A Python brief holds its pack's sentences at PR 3 and none of the C/C++ text."""
        for label, clone, task, _, _, key in WITH_TEXT:
            if clone.startswith("cpp"):
                continue
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                if key in ("DV1_PY", "CR1_PR3_PY"):
                    for sentence in PY_SENTENCES:
                        self.assertIn(f"`{sentence}`", task_line(prompt))
                for word in CPP_ONLY:
                    self.assertNotIn(word, prompt)

    def test_cpp_briefs_hold_no_python_sentence(self):
        """A C/C++ brief holds its pack's sentences at PR 3 and none of the Python text."""
        for label, clone, task, _, _, key in WITH_TEXT:
            if not clone.startswith("cpp"):
                continue
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                if key in ("DV1_CPP", "CR1_PR3_CPP"):
                    for sentence in CPP_SENTENCES:
                        self.assertIn(f"`{sentence}`", task_line(prompt))
                for word in PY_ONLY:
                    self.assertNotIn(word, prompt)

    def test_pr5_texts_hold_no_pack_sentence(self):
        """DV2 and CR1 at PR 5 delete the notes and check that none is left; they name no note."""
        for label, _, task, _, _, key in WITH_TEXT:
            if key not in ("DV2", "CR1_PR5"):
                continue
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                for sentence in PY_SENTENCES + CPP_SENTENCES:
                    self.assertNotIn(sentence, prompt)
                self.assertNotIn("Check the mock's notes", prompt)

    def test_pr3_reviews_do_not_ask_to_delete(self):
        """CR1 at PR 3 checks the notes; it does not check that they are gone."""
        for label, _, task, _, _, key in WITH_TEXT:
            if key not in ("CR1_PR3_PY", "CR1_PR3_CPP"):
                continue
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                self.assertNotIn("starts with \"The mock\"", prompt)
                self.assertNotIn("Where the mock does less than a doc comment says", prompt)


class NoTextTests(MockNoteCase):
    """CR1 at PR 4, side PRs, bugs, a version, a rule, and the other tasks: no text."""

    CASES = WITHOUT_TEXT

    def test_other_cases_hold_no_text(self):
        """None of the four texts, and none of their "The mock" sentences, in the prompt."""
        for label, _, task, _, _ in WITHOUT_TEXT:
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                for key, text in TEXTS.items():
                    self.assertNotIn(text, prompt, key)
                for marker in MARKERS:
                    self.assertNotIn(marker, prompt)


class HeadConfigTests(FlowCase):
    """The pack's text is chosen by ``[lang] name`` in the config at HEAD (design 6.4)."""

    def test_working_tree_language_changes_nothing(self):
        """A Python project whose working tree alone says ``cpp``: DV1 gets the Python text."""
        project = Project([base_step(), *stages(F01, 2)])
        project.write(CONFIG, config_text("cpp"))
        out = project.run("brief", "--task", "DV1", "--item", "F01")
        report = self.report_of(out, 0, "brief")
        line = task_line(report.get("prompt") or "")
        self.assertEqual(line.count(DV1_PY), 1, line)
        self.assertNotIn(DV1_CPP, line)
        self.assertNotIn("troy::NotImplemented", line)


if __name__ == "__main__":
    unittest.main()
