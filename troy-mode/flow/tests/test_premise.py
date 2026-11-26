"""The premise attempt (F18 design 6, 13.1 "Premise"; part 1 contract section 5).

After an author's third failed attempt, ``status`` gives ``next.premise`` true, and F07
runs the author once more with ``brief --premise``: the fixed text of
``troyflow.premise`` at the end of the Task line, and the premise card last in Read first.
Attempts count from comments, from CI (F07 D261), or from the progress file's notes before
a PR exists. A fourth failure, with no escalation after it, gives ``escalate`` W7.

Planted bugs of design 13.2 caught here:

- "the premise flag at attempt 2 or 4": ``PremiseStatusTests.test_two_attempts_are_no_premise``
  and ``test_four_attempts_escalate``, ``NotesPremiseTests``.
- "the premise text added twice or to a reviewer": ``PremiseBriefTests.test_text_once_at_the_end``
  and ``test_reviewers_are_refused``.
- "the fourth failure not escalated": ``PremiseStatusTests.test_four_attempts_escalate``,
  ``test_ci_failures_count_toward_the_escalation``, and
  ``NotesPremiseTests.test_flag_follows_the_notes_before_a_pr``.

``PremiseBriefTests.test_brief_without_the_flag_is_unchanged`` passes on today's engine: a
brief without ``--premise`` must stay as it is.
"""

import unittest

import test_ci_attempts as ci_cases
from flow_helpers import (
    F01, F05, Fakes, FlowCase, Project, base_files, base_step, fake_status_runs, parallel,
    same_path, stage_pr, stages,
)
from stops_helpers import (
    BUG_A, CARD, REFACTOR, RULE_TEST_FIX, TEST_FIX, attempt, brief_project, engine_module,
    escalation, in_order, read_first_items, rules_project, task_field,
)
from teams2_helpers import SIX, TeamFakes, TeamsCase, add_team

STEPS = [base_step(), *stages(F01, 2)]          # F01's mock, stage 3
DEV = "Developer"


def pr_case(*bodies: str) -> tuple:
    """F01's open mock PR #43 with its comments, oldest first."""
    return STEPS, {"prs": [stage_pr(43, F01, 3)], "comments": {43: in_order(*bodies)}}


def attempts(*numbers: int) -> list:
    """The Developer's attempt comments with these numbers."""
    return [attempt(DEV, n, f"mypy: {n} errors") for n in numbers]


def ci_case(failed: int) -> tuple:
    """PR #7 (F01's mock) with a number of pushed commits that failed CI in the author's files,
    and no attempt comment (D261)."""
    runs = [ci_cases.Run(100 + n, ci_cases.sha(f"commit {n}"), 10 * n)
            for n in range(1, failed + 1)]
    return ci_cases.status_case(runs)


ESCALATED = escalation("the Developer's mock still fails after a premise attempt", "W7")
CASES = {
    "two": pr_case(*attempts(1, 2)),
    "three": pr_case(*attempts(1, 2, 3)),
    "four": pr_case(*attempts(1, 2, 3, 4)),
    "five": pr_case(*attempts(1, 2, 3, 4, 5)),
    "four, escalated": pr_case(*attempts(1, 2, 3, 4), ESCALATED),
    "escalated before four": pr_case(*attempts(1, 2, 3), ESCALATED, *attempts(4)),
    "ci three": ci_case(3),
    "ci four": ci_case(4),
}


class PremiseStatusTests(FlowCase):
    """``next.premise`` and ``next.escalate`` for an open PR (contract 5)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case, side by side."""
        cls.outs = fake_status_runs(CASES)

    def mock_next(self, name: str, number: int = 43, **expected) -> None:
        """Asserts ``continue-pr`` of F01's mock PR with the given keys."""
        report = self.report_of(self.outs[name][0], 0, "status")
        self.assert_next(report, action="continue-pr", pr=number, item="F01", stage=3,
                         task="DV1", title=F01.title(3), branch=F01.branch(3), merged_by="f07",
                         **expected)

    def test_two_attempts_are_no_premise(self):
        """Planted bug "the premise flag at attempt 2": two failures, no premise."""
        self.mock_next("two", attempts=2, premise=False)

    def test_three_attempts_ask_for_the_premise(self):
        """Three failures: ``premise`` true, nothing escalated yet."""
        self.mock_next("three", attempts=3, premise=True)

    def test_four_attempts_escalate(self):
        """Planted bugs "the premise flag at attempt 4" and "the fourth failure not escalated":
        four or five failures: no premise, ``escalate`` W7."""
        self.mock_next("four", attempts=4, premise=False, escalate="W7")
        self.mock_next("five", attempts=5, premise=False, escalate="W7")

    def test_escalation_after_the_fourth_ends_the_escalate(self):
        """An ``Escalation:`` after attempt 4: ``escalate`` null, and the PR waits for Troy."""
        self.mock_next("four, escalated", attempts=4, premise=False)
        self.assertIs(self.outs["four, escalated"][0].report["open_prs"][0]["waiting_for_troy"],
                      True)

    def test_escalation_before_the_newest_attempt_does_not_count(self):
        """An escalation, then attempt 4: the newest attempt has none after it, so W7."""
        self.mock_next("escalated before four", attempts=4, premise=False, escalate="W7")

    def test_ci_failures_count_toward_the_premise(self):
        """Three failed commits with no attempt comment (D261): ``premise`` true."""
        self.mock_next("ci three", number=7, attempts=3, premise=True)

    def test_ci_failures_count_toward_the_escalation(self):
        """Planted bug "the fourth failure not escalated": four failed commits: W7."""
        self.mock_next("ci four", number=7, attempts=4, premise=False, escalate="W7")


class NotesPremiseTests(FlowCase):
    """Before a PR exists, the attempts come from the progress file's notes (contract 5)."""

    def test_flag_follows_the_notes_before_a_pr(self):
        """Notes of attempts 1 and 2: no premise; 3: premise; 4: W7; then a wait recorded
        with ``--wait W7``: nothing more to escalate."""
        project = Project(STEPS)
        stage = dict(action="stage", item="F01", stage=3, task="DV1", title=F01.title(3),
                     branch=F01.branch(3), merged_by="f07")
        second = self.report_of(project.status("--note", "Developer attempt 1: failed",
                                               "--note", "Developer attempt 2: failed"))
        self.assert_next(second, attempts=2, premise=False, **stage)
        third = self.report_of(project.status("--note", "Developer attempt 3: failed"))
        self.assert_next(third, attempts=3, premise=True, **stage)
        fourth = self.report_of(project.status("--note", "Developer attempt 4: failed"))
        self.assert_next(fourth, attempts=4, premise=False, escalate="W7", **stage)
        waited = self.report_of(project.status(
            "--waiting", "the Developer's mock still fails after a premise attempt",
            "--wait", "W7"))
        self.assert_next(waited, attempts=4, premise=False, **stage)


AUTHORS = {
    "IF1": ("briefs", "F02", None),
    "IF2": ("briefs", "F02", None),
    "TM1": ("briefs", "F03", None),
    "TM7": ("briefs", "v0.1", None),
    "DV1": ("briefs", "F04", None),
    "DV2": ("briefs", "F01", None),
    "DV3": ("briefs", "B12", None),
    "DV4": ("briefs", "F01", None),
    "DV5": ("rules", "P01", REFACTOR),
    "TE1": ("briefs", "F05", None),
    "TE2": ("briefs", "B13", BUG_A),
    "TE3": ("briefs", "F01", TEST_FIX),
    "TE4": ("briefs", "F01", TEST_FIX),
    "TE5": ("briefs", "v0.1", None),
    "TE6": ("rules", "P01", RULE_TEST_FIX),
    "AR1": ("briefs", None, None),
}
REVIEWERS = {
    "AR2": ("briefs", "F02", None),
    "AR5": ("briefs", "F01", None),
    "AR8": ("briefs", "F01", None),
    "CR1": ("briefs", "F01", None),
    "IF3": ("briefs", "F03", None),
    "TM2": ("briefs", "F05", None),
    "TM4": ("briefs", "F01", None),
}
PROJECTS = {"briefs": brief_project, "rules": rules_project}


def run_brief(spec: tuple):
    """Runs one brief: ``(task, clone name, item or None, title or None, premise)``."""
    task, name, item, title, premise = spec
    args = ["brief", "--task", task] + (["--item", item] if item else [])
    args += (["--title", title] if title else []) + (["--premise"] if premise else [])
    return PROJECTS[name]().run(*args, fakes=Fakes())


class PremiseBriefTests(FlowCase):
    """``brief --premise`` for every author task, and its refusal for the others (contract 5)."""

    @classmethod
    def setUpClass(cls):
        """Runs every brief with ``--premise``, and DV2's without, side by side."""
        brief_project()
        rules_project()
        specs = {(task, True): (task, *where, True) for task, where in
                 {**AUTHORS, **REVIEWERS}.items()}
        specs[("DV2", False)] = ("DV2", *AUTHORS["DV2"], False)
        keys = list(specs)
        cls.outs = dict(zip(keys, parallel(run_brief, [specs[k] for k in keys])))
        try:
            cls.text = engine_module("premise").TEXT
        except AssertionError as exc:
            cls.text, cls.missing = None, str(exc)

    def premise_text(self) -> str:
        """``troyflow.premise.TEXT``, or a failure that names why it could not be read."""
        if self.text is None:
            self.fail(self.missing)
        return self.text

    def test_premise_text(self):
        """The fixed text starts ``This is your fourth attempt:`` and names the report's three
        lines."""
        text = self.premise_text()
        self.assertTrue(text.startswith("This is your fourth attempt:"), text)
        for word in ("Premise:", "Check:", "Result:"):
            with self.subTest(word=word):
                self.assertIn(word, text)

    def test_text_once_at_the_end(self):
        """Planted bug "the premise text added twice": for each author task, the Task field
        ends with the text, which is in the prompt once."""
        text = self.premise_text()
        for task in AUTHORS:
            with self.subTest(task=task):
                report = self.report_of(self.outs[(task, True)], 0, "brief")
                self.assertTrue(task_field(report["prompt"]).endswith(text),
                                task_field(report["prompt"])[-400:])
                self.assertEqual(report["prompt"].count(text), 1)

    def test_card_is_read_last(self):
        """For each author task, the premise card is the last Read first entry, in the report
        and in the prompt, as an absolute POSIX path."""
        for task in AUTHORS:
            with self.subTest(task=task):
                report = self.report_of(self.outs[(task, True)], 0, "brief")
                last = report["read_first"][-1]
                self.assertNotIn("\\", last)
                self.assertTrue(same_path(last, CARD), f"{last} is not {CARD}")
                self.assertEqual(read_first_items(report["prompt"])[-1], last)

    def test_reviewers_are_refused(self):
        """Planted bug "the premise text added to a reviewer": a review, an answer, or a
        ruling with ``--premise``: exit 1, one problem that names ``--premise``."""
        for task in REVIEWERS:
            with self.subTest(task=task):
                report = self.report_of(self.outs[(task, True)], 1, "brief")
                self.assertEqual(len(report["problems"]), 1, report["problems"])
                self.assertIsInstance(report["problems"][0], str)
                self.assertIn("--premise", report["problems"][0])

    def test_brief_without_the_flag_is_unchanged(self):
        """DV2 without ``--premise``: no fourth attempt in the prompt, no card in Read first."""
        report = self.report_of(self.outs[("DV2", False)], 0, "brief")
        self.assertNotIn("fourth attempt", report["prompt"])
        self.assertNotIn("principle-attack-the-premise",
                         " ".join(report["read_first"]) + report["prompt"])
        self.assertTrue(task_field(report["prompt"]).startswith(
            "DV2, implement F01 so that its tests pass."), report["prompt"])


class TeamPremiseTests(TeamsCase):
    """With feature teams, each team's ``next`` carries ``premise`` and ``escalate`` too.

    Added after the planted bugs "the premise flag at attempt 2" and "the fourth failure
    not escalated" survived in ``nextentry.attempt_flags``: ``status`` sets both flags again
    for the home checkout's ``next``, but a team's ``next`` has only that function's.
    """

    @classmethod
    def setUpClass(cls):
        """F05's team has its mock PR #53 with 2, 3, or 4 failed attempts, or 4 and an
        escalation after them."""
        def run(bodies):
            project = Project((base_step(base_files(SIX)), *stages(F01, 6), *stages(F05, 2)))
            add_team(project, "F05")
            return project.run("status", fakes=TeamFakes([stage_pr(53, F05, 3)],
                                                         {53: in_order(*bodies)}))
        cases = {"two": [attempt(DEV, n) for n in (1, 2)],
                 "three": [attempt(DEV, n) for n in (1, 2, 3)],
                 "four": [attempt(DEV, n) for n in (1, 2, 3, 4)],
                 "four escalated": [*(attempt(DEV, n) for n in (1, 2, 3, 4)), ESCALATED]}
        cls.outs = dict(zip(cases, parallel(run, list(cases.values()))))

    def flags(self, case: str) -> tuple:
        """F05's team ``next``: attempts, premise, and escalate."""
        entry = self.team(self.report_of(self.outs[case], 0, "status"), "F05").get("next")
        return entry.get("attempts"), entry.get("premise"), entry.get("escalate")

    def test_two_attempts_are_no_premise(self):
        """Two failed attempts: no premise, nothing to escalate."""
        self.assertEqual(self.flags("two"), (2, False, None))

    def test_three_attempts_ask_for_the_premise(self):
        """Three failed attempts: the premise attempt comes next."""
        self.assertEqual(self.flags("three"), (3, True, None))

    def test_four_attempts_escalate(self):
        """Four failed attempts: no premise, escalate W7."""
        self.assertEqual(self.flags("four"), (4, False, "W7"))

    def test_escalation_after_the_fourth_ends_the_escalate(self):
        """An escalation after the fourth attempt answers it."""
        self.assertEqual(self.flags("four escalated"), (4, False, None))


if __name__ == "__main__":
    unittest.main()
