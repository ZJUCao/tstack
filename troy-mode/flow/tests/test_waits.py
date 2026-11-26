"""Waits for Troy (F18 design 4.1 to 4.3, 13.1 "Waits"; part 1 contract sections 1, 2, 10).

Only the steps of the list W1 to W11 wait for Troy, and each wait names its ID: ``status
--waiting`` takes ``--wait <ID>`` and refuses a wait without a listed ID, the comments under
``Waiting for Troy:`` and ``Escalation:`` carry a ``Wait: W<n>`` line, and ``status`` gives
the ID in ``wait``, ``waiting_on_troy``, each open PR, and each team's waiting PR. An older
comment without the line still waits, as ``unlisted``. A CI failure outside the authors'
files is re-run once, so ``gh run list`` asks for each run's ``attempt`` and ``ci_failures``
says whether a failure is a re-run's.

Planted bugs of design 13.2 caught here:

- "a wait recorded without an ID": ``WaitOptionRefusalTests.test_waiting_without_wait_is_refused``
  and ``test_refusal_leaves_no_progress_file``.
- "an unlisted ID accepted": ``WaitOptionRefusalTests.test_unknown_ids_are_refused`` and
  ``WaitTableTests.test_is_listed_takes_exactly_the_eleven_ids``.
"""

import json
import unittest

import test_ci_attempts as ci_cases
from flow_helpers import (
    F01, F05, PROGRESS, FlowCase, Project, base_files, base_step, comments, fake_status_runs,
    option_value, parallel, progress_fields, stage_pr, stages,
)
from stops_helpers import (
    WAIT_IDS, engine_module, escalation, review, waiting,
)
from teams2_helpers import SIX, TeamFakes, TeamsCase, add_team, write_plan

STEPS = [base_step(), *stages(F01, 2)]          # F01's stage 3 is next
DESIGN_STEPS = [base_step()]                    # F01's stage 1 is next
REQUEST = "approve PR #41"
OLD_TEXT = "Approve the F01 design in chat"
NAMES = (
    ("W1", "approval", "The requirements, or a change of them"),
    ("W2", "approval", "The architecture"),
    ("W3", "approval", "PR 1 and PR 2 of the first features, and the question after them"),
    ("W4", "approval", "The version: Troy's device test and acceptance"),
    ("W5", "approval", "Rules"),
    ("W6", "escalation", "A change of the requirements or the architecture"),
    ("W7", "escalation", "An author's work still fails"),
    ("W8", "escalation", "A new third-party dependency"),
    ("W9", "escalation", "An action outside troy-mode's rights"),
    ("W10", "escalation", "A refusal troy-mode must not work around"),
    ("W11", "escalation", "A fault in troy-mode's own checks"),
)


class WaitTableTests(unittest.TestCase):
    """``troyflow.waits``: the eleven IDs, ``is_listed``, and ``wait_of`` (contract 1)."""

    @classmethod
    def setUpClass(cls):
        """Imports the module once; a missing module fails each test, not the class."""
        try:
            cls.waits = engine_module("waits")
        except AssertionError as exc:
            cls.waits, cls.missing = None, str(exc)

    def module(self):
        """The module, or a failure that names why it could not be imported."""
        if self.waits is None:
            self.fail(self.missing)
        return self.waits

    def test_ids_kinds_and_names_in_order(self):
        """W1 to W11 in order: W1 to W5 approvals, W6 to W11 escalations, with their names."""
        found = [(key, *value) for key, value in self.module().WAITS.items()]
        self.assertEqual(found, [tuple(row) for row in NAMES])

    def test_unlisted_is_its_own_word(self):
        """``UNLISTED`` is ``unlisted``."""
        self.assertEqual(self.module().UNLISTED, "unlisted")

    def test_is_listed_takes_exactly_the_eleven_ids(self):
        """Planted bug "an unlisted ID accepted": only W1 to W11 are listed."""
        waits = self.module()
        for wait in WAIT_IDS:
            with self.subTest(wait=wait):
                self.assertIs(waits.is_listed(wait), True)
        for text in ("W0", "W12", "w3", "W03", "W", "unlisted", "", "3"):
            with self.subTest(text=text):
                self.assertIs(waits.is_listed(text), False)

    def test_wait_of_reads_the_line_under_both_headings(self):
        """``Wait: W3`` under ``Waiting for Troy:``, ``Wait: W8`` under ``Escalation:``, and a
        line after blank lines, with spaces around it, all give their IDs."""
        waits = self.module()
        cases = {
            waiting(wait="W3"): "W3",
            escalation("a new dependency: requests", "W8"): "W8",
            "Waiting for Troy: accept v0.1.0\n\n\n   Wait: W4   \n\nThe checklist is #9.": "W4",
            "Escalation: gh pr merge was refused\nWait: W10": "W10",
        }
        for body, wait in cases.items():
            with self.subTest(body=body):
                self.assertEqual(waits.wait_of(body), wait)

    def test_wait_of_without_a_listed_line_is_unlisted(self):
        """No ``Wait:`` line, an unknown ID, more after the ID, or the line not first: unlisted."""
        waits = self.module()
        for body in (waiting(), escalation("three review rounds without agreement"),
                     waiting(wait="W12"), waiting(wait="w3"), waiting(wait="W3 (approval)"),
                     "Waiting for Troy: approve this PR\n\nWhat to decide is at the top.\n"
                     "Wait: W3"):
            with self.subTest(body=body):
                self.assertEqual(waits.wait_of(body), "unlisted")

    def test_wait_of_other_comments_is_none(self):
        """A review, an attempt, Troy's own words, and a heading inside a line wait for nothing."""
        waits = self.module()
        for body in (review("Architect", 1, "approved") + "\n\nWait: W3",
                     "Developer attempt 1: failed\n\nWait: W7",
                     "Please approve.\nWait: W3",
                     "Note: Waiting for Troy: approve this PR\nWait: W3"):
            with self.subTest(body=body):
                self.assertIsNone(waits.wait_of(body))


REFUSED = {
    "missing": ("--waiting", OLD_TEXT),
    "W12": ("--waiting", REQUEST, "--wait", "W12"),
    "W0": ("--waiting", REQUEST, "--wait", "W0"),
    "w3": ("--waiting", REQUEST, "--wait", "w3"),
    "X": ("--waiting", REQUEST, "--wait", "X"),
    "unlisted": ("--waiting", REQUEST, "--wait", "unlisted"),
    "wait alone": ("--wait", "W3"),
    "wait with empty text": ("--waiting", "", "--wait", "W3"),
}


class WaitOptionRefusalTests(FlowCase):
    """``--waiting`` needs ``--wait`` with a listed ID, and nothing is written (contract 2)."""

    @classmethod
    def setUpClass(cls):
        """Writes one progress file, copies it into a clone per case, and runs each refusal."""
        seed = Project(STEPS)
        seed.status()
        cls.before = seed.read_bytes(PROGRESS)

        def run(options):
            """One clone with the seed's progress file, and the refused status."""
            project = Project(STEPS)
            project.write(PROGRESS, cls.before)
            return project.status(*options), project.read_bytes(PROGRESS)
        names = list(REFUSED)
        cls.outs = dict(zip(names, parallel(run, [REFUSED[name] for name in names])))
        fresh = Project(STEPS)
        cls.fresh = (fresh.status("--waiting", OLD_TEXT), fresh.exists(PROGRESS))

    def assert_refused(self, name: str) -> None:
        """Exit 1, one problem of kind ``wait`` with a message, and the file unchanged."""
        out, after = self.outs[name]
        report = self.report_of(out, 1, "status")
        self.assertEqual([p.get("kind") for p in report["problems"]], ["wait"], out.describe())
        message = report["problems"][0].get("message")
        self.assertIsInstance(message, str, report)
        self.assertNotEqual(message.strip(), "", report)
        self.assertEqual(after, self.before, "the progress file changed")

    def test_waiting_without_wait_is_refused(self):
        """Planted bug "a wait recorded without an ID": ``--waiting <text>`` alone."""
        self.assert_refused("missing")

    def test_unknown_ids_are_refused(self):
        """Planted bug "an unlisted ID accepted": W12, W0, w3, X, and ``unlisted``."""
        for name in ("W12", "W0", "w3", "X", "unlisted"):
            with self.subTest(wait=name):
                self.assert_refused(name)

    def test_wait_without_waiting_is_refused(self):
        """``--wait W3`` alone, and with ``--waiting ""``: the same refusal."""
        for name in ("wait alone", "wait with empty text"):
            with self.subTest(case=name):
                self.assert_refused(name)

    def test_refusal_leaves_no_progress_file(self):
        """Planted bug "a wait recorded without an ID": in a tree with no progress file, the
        refused ``--waiting`` writes none."""
        out, exists = self.fresh
        report = self.report_of(out, 1, "status")
        self.assertEqual([p.get("kind") for p in report["problems"]], ["wait"])
        self.assertFalse(exists, "the refused status wrote the progress file")


class WaitOptionTests(FlowCase):
    """A listed wait is recorded, carried, and cleared; a carried text gives its ID (contract 2)."""

    def test_listed_wait_is_recorded_carried_and_cleared(self):
        """``--waiting "approve PR #41" --wait W3``: the file's line and the report name W3; a
        later status carries it; ``--waiting ""`` clears it."""
        project = Project(STEPS)
        first = self.report_of(project.status("--waiting", REQUEST, "--wait", "W3"))
        self.assertEqual((first.get("waiting_on_troy"), first.get("wait")),
                         ("W3, approve PR #41", "W3"))
        self.assertIn("- Waiting on Troy: W3, approve PR #41\n", project.read(PROGRESS))
        second = self.report_of(project.status())
        self.assertEqual((second.get("waiting_on_troy"), second.get("wait")),
                         ("W3, approve PR #41", "W3"))
        third = self.report_of(project.status("--waiting", ""))
        self.assertEqual((third.get("waiting_on_troy"), third.get("wait")), (None, None))
        self.assertEqual(progress_fields(project.read(PROGRESS))["Waiting on Troy"], "Nothing")

    def test_carried_text_gives_its_id_or_unlisted(self):
        """A file whose line starts ``W5, ``: ``wait`` W5; an older line, or ``W12, ``, gives
        ``unlisted``; the text is carried as the file has it."""
        seed = Project(STEPS)
        seed.status()
        text = seed.read(PROGRESS)
        self.assertIn("- Waiting on Troy: Nothing\n", text)
        cases = {"W5, pick the rules to keep": "W5", OLD_TEXT: "unlisted",
                 "W12, something else": "unlisted"}

        def run(line):
            """A clone whose progress file waits on the line, and a plain status."""
            project = Project(STEPS)
            project.write(PROGRESS, text.replace("- Waiting on Troy: Nothing\n",
                                                 f"- Waiting on Troy: {line}\n"))
            return project.status()
        lines = list(cases)
        for line, out in zip(lines, parallel(run, lines)):
            with self.subTest(line=line):
                report = self.report_of(out)
                self.assertEqual((report.get("waiting_on_troy"), report.get("wait")),
                                 (line, cases[line]))

    def test_nothing_waits(self):
        """No ``--waiting``, no waiting PR, no carried text: ``wait`` is null."""
        report = self.report_of(Project(STEPS).status())
        self.assertEqual((report.get("wait", "missing"), report["waiting_on_troy"]), (None, None))


DESIGN_REVIEW = review("Architect", 1, "approved")
PR_CASES = {
    "W3": (DESIGN_STEPS, 41, 1, (DESIGN_REVIEW, waiting(wait="W3"))),
    "old": (DESIGN_STEPS, 41, 1, (DESIGN_REVIEW, waiting())),
    "W12": (DESIGN_STEPS, 41, 1, (DESIGN_REVIEW, waiting(wait="W12"))),
    "line not first": (DESIGN_STEPS, 41, 1, (
        DESIGN_REVIEW, "Waiting for Troy: approve this PR\n\nWhat to decide is at the top.\n"
                       "Wait: W3")),
    "replied": (DESIGN_STEPS, 41, 1, (DESIGN_REVIEW, waiting(wait="W3"), "全按推荐")),
    "escalation W8": (STEPS, 43, 3, (escalation("a new dependency: requests", "W8"),)),
    "escalation old": (STEPS, 43, 3, (escalation("a new dependency: requests"),)),
    "not waiting": (STEPS, 43, 3, (review("Code Reviewer", 1, "changes-requested",
                                          "Naming: rename count()."),)),
}


class PrWaitTests(FlowCase):
    """The ID of an open PR's wait, from its ``Wait:`` line (design 4.2; contract 2)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case, side by side."""
        cases = {}
        for name, (steps, number, stage, bodies) in PR_CASES.items():
            prs = [stage_pr(number, F01, stage)]
            cases[name] = (steps, {"prs": prs, "comments": {number: list(_comments(bodies))}})
        cls.outs = fake_status_runs(cases)

    def report(self, name: str) -> dict:
        """The case's report, exit 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def entry(self, name: str) -> dict:
        """The case's one open PR entry."""
        prs = self.report(name)["open_prs"]
        self.assertEqual(len(prs), 1, prs)
        return prs[0]

    def test_listed_wait_names_its_id(self):
        """``Wait: W3`` under the approval request: ``wait`` W3 in the report and the PR, and
        ``waiting_on_troy`` starts with it."""
        report = self.report("W3")
        self.assertEqual(report.get("wait"), "W3")
        self.assertEqual(report["waiting_on_troy"], "W3, PR #41: Waiting for Troy: approve this PR")
        self.assertEqual((self.entry("W3")["waiting_for_troy"], self.entry("W3").get("wait")),
                         (True, "W3"))

    def test_escalation_names_its_id(self):
        """``Wait: W8`` under an escalation: W8, and the PR is escalated."""
        report = self.report("escalation W8")
        self.assertEqual(report.get("wait"), "W8")
        self.assertEqual(report["waiting_on_troy"],
                         "W8, PR #43: Escalation: a new dependency: requests")
        entry = self.entry("escalation W8")
        self.assertEqual((entry["escalated"], entry.get("wait")), (True, "W8"))

    def test_comment_without_a_listed_id_is_unlisted(self):
        """An older comment, ``Wait: W12``, or the line not first: still waiting, ``unlisted``."""
        for name in ("old", "W12", "line not first"):
            with self.subTest(case=name):
                report = self.report(name)
                self.assertEqual(report.get("wait"), "unlisted")
                self.assertEqual(report["waiting_on_troy"],
                                 "unlisted, PR #41: Waiting for Troy: approve this PR")
                self.assertEqual((self.entry(name)["waiting_for_troy"],
                                  self.entry(name).get("wait")), (True, "unlisted"))
        report = self.report("escalation old")
        self.assertEqual((report.get("wait"), report["waiting_on_troy"]),
                         ("unlisted", "unlisted, PR #43: Escalation: a new dependency: requests"))

    def test_troys_reply_ends_the_wait_and_its_id(self):
        """Troy's reply after the request: nothing waits, and ``wait`` is null in both places."""
        report = self.report("replied")
        self.assertEqual((report["waiting_on_troy"], report.get("wait", "missing")), (None, None))
        entry = self.entry("replied")
        self.assertEqual((entry["waiting_for_troy"], entry.get("wait", "missing"),
                          entry["troy_comments"]), (False, None, ["全按推荐"]))

    def test_pr_that_does_not_wait_has_no_id(self):
        """A review as the last comment: the PR's ``wait`` and the report's are null."""
        self.assertIsNone(self.entry("not waiting").get("wait", "missing"))
        self.assertIsNone(self.report("not waiting").get("wait", "missing"))


def _comments(bodies) -> list:
    """Comments one minute apart, all by Troy's account."""
    return comments(*bodies)


class TeamWaitTests(TeamsCase):
    """With feature teams, each entry of ``waiting`` gains ``wait`` (contract 2)."""

    @classmethod
    def setUpClass(cls):
        """Teams for F01 and F05, each with its design PR waiting for Troy."""
        project = Project((base_step(base_files(SIX)),))
        for item in ("F01", "F05"):
            add_team(project, item)
        write_plan(project, ["F01", "F05", "F06"])
        prs = [stage_pr(41, F05, 1), stage_pr(42, F01, 1)]
        by_pr = {41: _comments((DESIGN_REVIEW, waiting(wait="W3"))),
                 42: _comments((DESIGN_REVIEW, waiting()))}
        cls.out = project.run("status", fakes=TeamFakes(prs, by_pr))

    def test_waiting_entries_name_their_ids(self):
        """F01's #42 (holding F02 and F03) waits ``unlisted``; F05's #41 waits W3."""
        report = self.report_of(self.out, 0, "status")
        found = [(w.get("pr"), w.get("item"), w.get("wait")) for w in self.need(report, "waiting")]
        self.assertEqual(found, [(42, "F01", "unlisted"), (41, "F05", "W3")])


RUN_FIELDS = ("databaseId,headBranch,headSha,status,conclusion,createdAt,updatedAt,workflowName,"
              "attempt")


def rerun_case(attempt_number):
    """PR #7 whose commit failed CI in the checkout, outside the authors' files.

    Args:
        attempt_number: The run's ``attempt``, or None for a run that gh gives none.

    Returns:
        ``(steps, fakes keyword arguments)``.
    """
    steps, kwargs = ci_cases.status_case([ci_cases.Run(101, ci_cases.C1, 5,
                                                       view=ci_cases.checkout_failure())])
    runs = [dict(run) for run in kwargs["runs"]]
    if attempt_number is not None:
        for run in runs:
            run["attempt"] = attempt_number
    return steps, {**kwargs, "runs": runs}


class CiRerunTests(FlowCase):
    """A CI failure outside the authors' files is re-run once (design 4.3; contract 10)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case, side by side."""
        cls.outs = fake_status_runs({"re-run failed": rerun_case(2), "first run": rerun_case(1),
                                     "no attempt": rerun_case(None)})

    def failure(self, name: str) -> dict:
        """The case's one ``ci_failures`` entry of PR #7."""
        report = self.report_of(self.outs[name][0], 0, "status")
        failures = report["open_prs"][0]["ci_failures"]
        self.assertEqual(len(failures), 1, json.dumps(failures))
        return failures[0]

    def test_run_list_asks_for_the_attempt(self):
        """``gh run list`` asks for the eight fields of D261 and ``attempt``."""
        calls = [argv for argv in self.outs["first run"][1].gh_argvs()
                 if argv[:2] == ["run", "list"]]
        self.assertEqual(len(calls), 1, calls)
        self.assertEqual(option_value(calls[0], "--json"), RUN_FIELDS)

    def test_failed_rerun_is_marked(self):
        """The failed run is its second attempt: ``rerun`` true, and the failure is not the
        author's."""
        entry = self.failure("re-run failed")
        self.assertEqual((entry.get("rerun"), entry["author"]), (True, False))

    def test_first_failure_is_not_a_rerun(self):
        """Attempt 1, or no ``attempt`` from gh: ``rerun`` false."""
        for name in ("first run", "no attempt"):
            with self.subTest(case=name):
                self.assertIs(self.failure(name).get("rerun", "missing"), False)


if __name__ == "__main__":
    unittest.main()
