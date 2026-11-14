"""The task sentence that asks for the summary for Troy (F14 design 5.1, 5.2, 7).

The engine's task sentences for IF1, IF2, TM1, AR1, and AR6's architecture
change add one sentence, so the role fills the summary-for-troy template in
its report's For Troy field. Tasks that write no summary do not get it: the
reviews and answers, the code tasks, AR6's proposal of a rule, and the
``[docs]`` side-PR variants of TM1 and IF2, which add to a test plan or a
design in a ``[docs]`` PR that R22 skips (F14 design 4, 6.1).
"""

import unittest

from flow_helpers import F01, FlowCase, Project, base_step, parallel, stages

SENTENCE = ("Write the summary for Troy from the summary-for-troy template in your report's "
            "For Troy field.")
DOCS_PLAN = "[docs] Add cases to the F01 test plan"
DOCS_DESIGN = "[docs] Update the F01 design"
DOCS_P01 = "[docs] Change the architecture for P01"
_PROJECTS: dict = {}

# (label, clone, task, item or "", --title or None)
WITH_SUMMARY = [
    ("IF1 writes the design", "stage1", "IF1", "F01", None),
    ("IF2 revises the design", "stage1", "IF2", "F01", None),
    ("TM1 writes the test plan", "stage2", "TM1", "F01", None),
    ("AR1 writes the architecture", "stage1", "AR1", "", None),
    ("AR6 writes the architecture change", "stage1", "AR6", "P01", DOCS_P01),
]
WITHOUT_SUMMARY = [
    ("AR2 reviews the design", "stage1", "AR2", "F01", None),
    ("AR3 reviews a dependency", "stage1", "AR3", "F01", None),
    ("AR4 lists a change's impact", "stage1", "AR4", "F01", None),
    ("AR5 answers", "stage1", "AR5", "F01", None),
    ("IF3 answers the Test Manager", "stage2", "IF3", "F01", None),
    ("DV1 writes the mock", "stage3", "DV1", "F01", None),
    ("CR1 reviews the mock", "stage3", "CR1", "F01", None),
    ("TE1 writes the tests", "stage4", "TE1", "F01", None),
    ("TM2 reviews the tests", "stage4", "TM2", "F01", None),
    ("DV2 implements", "stage5", "DV2", "F01", None),
    ("TM1 in a [docs] side PR", "stage5", "TM1", "F01", DOCS_PLAN),
    ("IF2 in a [docs] side PR", "stage5", "IF2", "F01", DOCS_DESIGN),
    ("AR2 in a [docs] side PR", "stage5", "AR2", "F01", DOCS_PLAN),
    ("AR6 proposes a project rule", "stage1", "AR6", "P01", None),
    ("AR6 proposes a rule for every project", "stage1", "AR6", "R01", None),
    ("AR5 in a rule's architecture PR", "stage1", "AR5", "P01", DOCS_P01),
]


def shared(name: str) -> Project:
    """A clone shared by the tests, built on first use; tests must not change it.

    Args:
        name: ``stage1`` to ``stage5``: F01's current stage, its earlier
            stages merged on ``origin/main``.

    Returns:
        The clone.
    """
    if name not in _PROJECTS:
        _PROJECTS[name] = Project([base_step(), *stages(F01, int(name[-1]) - 1)])
    return _PROJECTS[name]


def brief(case):
    """Runs ``brief --task <task> [--item <item>] [--title <title>] --json`` for one case.

    Args:
        case: ``(label, clone, task, item or "", title or None)``.

    Returns:
        The outcome.
    """
    _, name, task, item, title = case
    args = ["brief", "--task", task]
    if item:
        args += ["--item", item]
    if title is not None:
        args += ["--title", title]
    return shared(name).run(*args)


def task_line(prompt: str) -> str:
    """The prompt's ``Task:`` line, or "" when there is none."""
    return next((line for line in prompt.split("\n") if line.startswith("Task: ")), "")


class SummarySentenceTests(FlowCase):
    """The Task line holds the summary sentence exactly for the tasks of design 5.1."""

    @classmethod
    def setUpClass(cls):
        """Builds the clones, then runs every case's brief side by side."""
        cases = WITH_SUMMARY + WITHOUT_SUMMARY
        for name in sorted({case[1] for case in cases}):
            shared(name)
        outs = parallel(brief, cases)
        cls.outs = dict(zip([case[0] for case in cases], outs))

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

    def test_authoring_tasks_ask_for_the_summary(self):
        """IF1, IF2, TM1, AR1, and AR6's architecture change: the sentence, once, on the Task line."""
        for label, _, task, _, _ in WITH_SUMMARY:
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                line = task_line(prompt)
                self.assertEqual(line.count(SENTENCE), 1, line)
                self.assertEqual(prompt.count(SENTENCE), 1, prompt)

    def test_other_tasks_do_not_ask_for_it(self):
        """Reviews, answers, code tasks, AR6's proposals, and [docs] side PRs: no sentence."""
        for label, _, task, _, _ in WITHOUT_SUMMARY:
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                self.assertNotIn(SENTENCE, prompt)
                self.assertNotIn("summary-for-troy", task_line(prompt))

    def test_docs_side_prs_keep_their_own_sentences(self):
        """The [docs] side-PR variants still add to the plan or design, as before F14."""
        plan = task_line(self.prompt_of("TM1 in a [docs] side PR", "TM1"))
        design = task_line(self.prompt_of("IF2 in a [docs] side PR", "IF2"))
        self.assertIn("add the cases in Input to the test plan of F01", plan)
        self.assertIn("update the interface design of F01", design)

    def test_architecture_change_keeps_its_sentence(self):
        """AR6 with a [docs] title still writes the architecture change, with the sentence added."""
        line = task_line(self.prompt_of("AR6 writes the architecture change", "AR6"))
        self.assertIn("write the architecture change for P01", line)
        self.assertIn(SENTENCE, line)


if __name__ == "__main__":
    unittest.main()
