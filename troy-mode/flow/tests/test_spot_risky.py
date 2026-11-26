"""Risky marks on PR 1 and PR 2 (F18 design 7.2, 13.1 "Spot checks"; part 2 contract 2, 4, 5).

A PR 1 or PR 2 is risky when the engine, the Architect, or Troy marks it. The engine marks
PR 1 when its design's section 3 lists a changed interface, when its review loop needed a
ruling at round 3, or when its attempts reached 3; PR 2 takes PR 1's marks and adds its own
ruling and premise marks. The Architect marks PR 1 with AR2's ``Risky: <reason>`` line in
its review comment, the newest such line deciding, ``Risky: no`` marking nothing. Troy
marks a feature with a note whose text starts with ``Risky:``. Marks are computed whether
spot checks are on or not; ``status`` gives them as ``open_prs[].risky`` and ``next.risky``.
The spot check comment and TM8's real-run ruling are troy-mode's own headings (contract 2).

Planted bugs of design 13.2 caught here:

- "PR 2 without PR 1's mark": ``EngineMarkTests.test_pr2_takes_pr1s_ruling``,
  ``test_merged_design_marks_stage_2`` and ``OrderTests.test_marks_in_order``.
- "a risky PR merged" (``merged_by`` f07 despite marks):
  ``EngineMarkTests.test_ruling_on_an_open_pr1``, ``test_premise_on_an_open_pr1``, and
  ``TroyMarkTests.test_note_marks_the_next_stage``.
- "``Risky: no`` read as a mark": ``ArchitectMarkTests.test_risky_no_marks_nothing`` and
  ``test_newest_line_decides``.
- "a Troy note marking nothing": ``TroyMarkTests.test_note_marks_the_next_stage`` and
  ``test_notes_oldest_first``.
"""

import unittest

from flow_helpers import base_step, stages, step
from spot_helpers import (
    CHAIN, CHANGED_3, CR, IF, ISSUE_LABELS, NEW_TIME, OLD_TIME, SPOT_COMMENT, TM, Case, SpotCase,
    all_listed, answer_step, arch_review, attempts, common_git, curl, custom_design_files, feat,
    flow, issue_comment, mark, note, progress_issue, ruled, run_case, run_cases, spot_files,
    stage_numbers, stage_open, thread, tm_ruling,
)
from stops_helpers import MERGE_FINDINGS, ruling

F1, F2 = feat(1), feat(2)
STEPS = [base_step(spot_files(CHAIN, flow(1, True, 2))), *stages(F1, 6), answer_step()]
CHANGED = CHANGED_3
NO_CHANGE = {
    "None": "None\n",
    "none.": "none.\n",
    "comment, then None.": "<!-- List each changed interface of an accepted feature. -->\nNone.\n",
    "comment over lines": "<!-- List each changed interface\nof an accepted feature. -->\n",
    "empty": "",
    # Added by F18 part 2's build after its trial: F10's design wrote "None." and then why.
    "None, then why": "None. F03 is a new feature, and no existing interface changes.\n",
}
PR1 = stage_open(21, F2, 1)
PR2 = stage_open(22, F2, 2)
PM7_MERGE = {"ruler": "Product Manager", "task": "PM7", "result": "merge"}
RULING_21 = mark("engine", "ruling", 21, curl(21, 3))
NOTE_URL = "https://github.com/ZJUCao/wordcount/issues/8#issuecomment-801"


def design_files(section3: str) -> dict:
    """F02's design, with an interface in section 2 and the given section 3."""
    return custom_design_files(F2, section3)


def branch_case(section3: str) -> Case:
    """F02's PR 1 open, its head branch on the origin holding a design."""
    return Case(STEPS, {"prs": [PR1], "all_prs": all_listed([PR1])},
                branches={F2.branch(1): (F2.title(1), design_files(section3))})


def pr1_case(*bodies: str, issues=None) -> Case:
    """F02's PR 1 open with its comments (no head branch on the origin)."""
    kwargs = {"prs": [PR1], "comments": {21: thread(21, *bodies)}, "all_prs": all_listed([PR1])}
    if issues is not None:
        kwargs.update(all_issues=issues, labels=list(ISSUE_LABELS))
    return Case(STEPS, kwargs)


def pr2_case(pr1_bodies=(), pr2_bodies=(), merged_design=None, issues=None, **more) -> Case:
    """F02's PR 1 merged (#21), with its comments, and PR 2 open (#22) with its own."""
    steps = [*STEPS, step(F2.title(1), design_files(merged_design)) if merged_design is not None
             else stages(F2, 1)[0]]
    kwargs = {"prs": [PR2], "comments": {21: thread(21, *pr1_bodies), 22: thread(22, *pr2_bodies)},
              "all_prs": all_listed([PR2], [(21, F2.title(1))]), **more}
    if issues is not None:
        kwargs.update(all_issues=issues, labels=list(ISSUE_LABELS))
    return Case(steps, kwargs)


def note_issue(*notes: tuple) -> list:
    """F02's progress issue #8 with ``(cid, body, created)`` comments."""
    return [progress_issue(8, F2, [issue_comment(8, cid, body, created)
                                   for cid, body, created in notes])]


CASES = {
    "interface on the branch": branch_case(CHANGED),
    **{f"no change: {name}": branch_case(text) for name, text in NO_CHANGE.items()},
    "no branch": Case(STEPS, {"prs": [PR1], "all_prs": all_listed([PR1])}),
    "interface merged": Case([*STEPS, step(F2.title(1), design_files(CHANGED))],
                             {"all_prs": all_listed((), [(21, F2.title(1))])}),
    "interface merged, PR 2 open": pr2_case(merged_design=CHANGED),
    "ruling": pr1_case(*ruled()),
    "ruling due": pr1_case(*ruled()[:3]),
    "PR 2 after a ruled PR 1": pr2_case(ruled()),
    "PR 2's own ruling": pr2_case((), ruled("Architect", IF)),
    "premise": pr1_case(*attempts(IF, 1, 2, 3)),
    "two attempts": pr1_case(*attempts(IF, 1, 2)),
    "stage 3 ruled": Case([*STEPS, *stages(F2, 2)],
                          {"prs": [stage_open(23, F2, 3)],
                           "comments": {23: thread(23, *ruled("Architect", CR))},
                           "all_prs": all_listed([stage_open(23, F2, 3)],
                                                 [(21, F2.title(1)), (22, F2.title(2))])}),
    "risky reason": pr1_case(arch_review(1, "approved", "a stored data format changes")),
    "risky no": pr1_case(arch_review(1, "approved", "no")),
    "risky No.": pr1_case(arch_review(1, "approved", "No.")),
    "risky NO": pr1_case(arch_review(1, "approved", "NO")),
    "newest no": pr1_case(arch_review(1, "changes-requested", "network access"),
                          arch_review(2, "approved", "no")),
    "newest reason": pr1_case(arch_review(1, "changes-requested", "no"),
                              arch_review(2, "approved", "a subprocess runs")),
    "later review without the line": pr1_case(
        arch_review(1, "changes-requested", "network access"), arch_review(2, "approved")),
    "trimmed": pr1_case(arch_review(1, "approved", "   credentials are read   ")),
    "not the Architect's": pr1_case(
        "Code Reviewer review, round 1: approved\n\n1. None\n\nRisky: network access",
        "Risky: Troy thinks it is risky."),
    "Architect line on PR 2": pr2_case((), [arch_review(1, "approved", "network access")]),
    "note": Case(STEPS, {"all_issues": note_issue(
        (801, note("F02", "Risky: it renames Troy's files"), NEW_TIME)),
        "labels": list(ISSUE_LABELS)}),
    "two notes": Case(STEPS, {"all_issues": [
        progress_issue(7, F1, [issue_comment(7, 701, note("F02", "Risky: it reads credentials",
                                                          "#11, Architect, round 1"),
                                             "2026-11-20T08:00:00Z")], state="CLOSED"),
        *note_issue((801, note("F02", "Risky: it renames Troy's files"), NEW_TIME),
                    (802, note("F02", "\n\nRisky:   it deletes the cache  "),
                     "2026-11-22T08:00:00Z"))], "labels": list(ISSUE_LABELS)}),
    "not risky notes": Case(STEPS, {"all_issues": note_issue(
        (801, note("F02", "Name the option --lines."), OLD_TIME),
        (802, note("F03", "Risky: another feature's note"), NEW_TIME),
        (803, "Risky: a comment that is no note", NEW_TIME),
        (804, note("F02", "It is not Risky: really"), NEW_TIME)),
        "labels": list(ISSUE_LABELS)}),
    "spot heading": pr1_case(arch_review(1), SPOT_COMMENT),
    "real-run ruling": Case([*STEPS, *stages(F2, 5)], {
        "prs": [stage_open(26, F2, 6)],
        "comments": {26: thread(26, tm_ruling(("bug", "the total is off by one"),
                                              ("requirement", "a total per folder"),
                                              ("later F05", "watch folders")))},
        "all_prs": all_listed([stage_open(26, F2, 6)], stage_numbers(F2, 5, 20))}),
    "order": pr2_case([arch_review(1, "changes-requested", "network access"),
                       arch_review(2, "changes-requested"), arch_review(3, "changes-requested"),
                       ruling("Product Manager", "merge", *MERGE_FINDINGS)],
                      attempts(TM, 1, 2, 3), merged_design=CHANGED,
                      issues=note_issue((801, note("F02", "Risky: Troy asked"), NEW_TIME))),
}


class RiskyCase(SpotCase):
    """Runs every case once, side by side."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case."""
        if not RiskyCase.outs:
            RiskyCase.outs = run_cases(CASES)

    def stage1_next(self, name: str, **expected) -> None:
        """Asserts ``next`` about F02's PR 1 #21."""
        keys = {"pr": 21, "item": "F02", "stage": 1, "task": "IF1", "title": F2.title(1),
                "branch": F2.branch(1)}
        self.assert_next(self.report(name), **{**keys, **expected})

    def stage2_next(self, name: str, **expected) -> None:
        """Asserts ``next`` about F02's stage 2."""
        self.assert_next(self.report(name), item="F02", stage=2, task="TM1", title=F2.title(2),
                         branch=F2.branch(2), **expected)


class EngineMarkTests(RiskyCase):
    """The engine's marks: interface, ruling, and premise (contract 4, marks 1 to 3)."""

    def test_interface_on_pr1s_branch(self):
        """Section 3 of the design on PR 1's head branch lists a changed interface."""
        self.assertEqual(self.risky_of("interface on the branch", 21),
                         [mark("engine", "interface", 21)])

    def test_no_interface_mark_without_a_change(self):
        """Section 3 ``None``, ``none.``, an HTML comment and ``None.``, a comment over two
        lines, or nothing: no mark."""
        for name in NO_CHANGE:
            with self.subTest(section3=name):
                self.assertEqual(self.risky_of(f"no change: {name}", 21), [])

    def test_no_interface_mark_without_the_design(self):
        """PR 1's head branch is not on the origin: the design cannot be read, no mark."""
        self.assertEqual(self.risky_of("no branch", 21), [])

    def test_merged_design_marks_stage_2(self):
        """Planted bug "PR 2 without PR 1's mark": PR 1 merged with section 3 listing a change
        on origin/main: stage 2's entry carries the mark, and Troy merges."""
        self.stage2_next("interface merged", action="stage", merged_by="troy", spot="none",
                         risky=[mark("engine", "interface", 21)])

    def test_open_pr2_takes_the_interface_mark(self):
        """PR 2 open after that PR 1: PR 2's entry and ``next`` carry PR 1's mark."""
        self.assertEqual(self.risky_of("interface merged, PR 2 open", 22),
                         [mark("engine", "interface", 21)])
        self.stage2_next("interface merged, PR 2 open", action="continue-pr", pr=22,
                         merged_by="troy", spot="none", risky=[mark("engine", "interface", 21)])

    def test_ruling_on_an_open_pr1(self):
        """Planted bug "a risky PR merged": PR 1 ruled at round 3: the ruling mark with the
        ruling's URL, and Troy merges."""
        self.assertEqual(self.risky_of("ruling", 21), [RULING_21])
        self.stage1_next("ruling", action="continue-pr", merged_by="troy", rounds=3,
                         ruling=PM7_MERGE, spot="none", risky=[RULING_21])

    def test_ruling_due_marks_the_pr(self):
        """Round 3 asks for changes and waits for a ruling: marked, with no URL yet; ``next``
        is the ``ruling`` action, whose ``spot`` is null and ``risky`` empty."""
        self.assertEqual(self.risky_of("ruling due", 21), [mark("engine", "ruling", 21)])
        self.stage1_next("ruling due", action="ruling", task="PM7", merged_by="troy", rounds=3,
                         ruling={**PM7_MERGE, "result": None}, spot=None, risky=[])

    def test_pr2_takes_pr1s_ruling(self):
        """Planted bug "PR 2 without PR 1's mark": PR 1 merged after a ruling, PR 2 open: PR 2
        carries PR 1's ruling mark, with PR 1's number, and Troy merges it."""
        self.assertEqual(self.risky_of("PR 2 after a ruled PR 1", 22), [RULING_21])
        self.stage2_next("PR 2 after a ruled PR 1", action="continue-pr", pr=22,
                         merged_by="troy", spot="none", risky=[RULING_21])

    def test_pr2s_own_ruling(self):
        """PR 2's own ruling at round 3: its mark with PR 2's number."""
        self.assertEqual(self.risky_of("PR 2's own ruling", 22),
                         [mark("engine", "ruling", 22, curl(22, 3))])

    def test_premise_on_an_open_pr1(self):
        """Planted bug "a risky PR merged": three failed attempts: the premise mark."""
        self.assertEqual(self.risky_of("premise", 21), [mark("engine", "premise", 21)])
        self.stage1_next("premise", action="continue-pr", merged_by="troy", attempts=3,
                         premise=True, spot="none", risky=[mark("engine", "premise", 21)])

    def test_two_attempts_mark_nothing(self):
        """Two failed attempts: no mark, and F07 merges."""
        self.assertEqual(self.risky_of("two attempts", 21), [])
        self.stage1_next("two attempts", action="continue-pr", merged_by="f07", attempts=2,
                         spot="none", risky=[])

    def test_other_stages_have_no_marks(self):
        """PR 3 after a ruling: ``risky`` empty and ``spot`` null; it is not a PR 1 or 2."""
        entry = self.open_entry("stage 3 ruled", 23)
        self.assertEqual((entry.get("risky", "missing"), entry.get("spot", "missing")),
                         ([], None))


class ArchitectMarkTests(RiskyCase):
    """AR2's ``Risky:`` line in the Architect's review comments (contract 2 and 4, mark 4)."""

    def test_risky_reason_marks_the_pr(self):
        """``Risky: a stored data format changes``: the Architect's mark, with the review's URL."""
        self.assertEqual(self.risky_of("risky reason", 21),
                         [mark("architect", "a stored data format changes", 21, curl(21, 0))])

    def test_risky_no_marks_nothing(self):
        """Planted bug "``Risky: no`` read as a mark": ``no``, ``No.``, and ``NO``."""
        for name in ("risky no", "risky No.", "risky NO"):
            with self.subTest(case=name):
                self.assertEqual(self.risky_of(name, 21), [])

    def test_newest_line_decides(self):
        """Planted bug "``Risky: no`` read as a mark": a reason, then ``no`` in round 2:
        nothing; ``no``, then a reason: the newer reason, with round 2's URL."""
        self.assertEqual(self.risky_of("newest no", 21), [])
        self.assertEqual(self.risky_of("newest reason", 21),
                         [mark("architect", "a subprocess runs", 21, curl(21, 1))])

    def test_review_without_the_line_keeps_the_one_before(self):
        """Round 2 has no ``Risky:`` line: round 1's reason still marks the PR."""
        self.assertEqual(self.risky_of("later review without the line", 21),
                         [mark("architect", "network access", 21, curl(21, 0))])

    def test_value_is_trimmed(self):
        """Spaces around the value are dropped."""
        self.assertEqual(self.risky_of("trimmed", 21),
                         [mark("architect", "credentials are read", 21, curl(21, 0))])

    def test_only_the_architects_reviews_count(self):
        """A Code Reviewer's review and Troy's comment with a ``Risky:`` line mark nothing."""
        self.assertEqual(self.risky_of("not the Architect's", 21), [])

    def test_pr2_has_no_architect_mark_of_its_own(self):
        """A ``Risky:`` line on PR 2: the Architect does not review PR 2, so no mark."""
        self.assertEqual(self.risky_of("Architect line on PR 2", 22), [])


class TroyMarkTests(RiskyCase):
    """Troy's ``Risky:`` notes (contract 4, mark 5)."""

    def test_note_marks_the_next_stage(self):
        """Planted bugs "a Troy note marking nothing" and "a risky PR merged": a note for F02
        whose text starts ``Risky:``: F02's stage 1 is marked before its PR exists, with the
        note's URL, and Troy merges it."""
        self.assert_next(self.report("note"), action="stage", item="F02", stage=1, task="IF1",
                         title=F2.title(1), branch=F2.branch(1), merged_by="troy", spot="none",
                         issue=8, risky=[mark("troy", "it renames Troy's files", None, NOTE_URL)])

    def test_notes_oldest_first(self):
        """Planted bug "a Troy note marking nothing": three notes, one on F01's closed issue,
        one after blank lines with spaces around its value: one mark each, oldest first."""
        self.assertEqual(self.nxt("two notes").get("risky", "missing"), [
            mark("troy", "it reads credentials", None,
                 "https://github.com/ZJUCao/wordcount/issues/7#issuecomment-701"),
            mark("troy", "it renames Troy's files", None, NOTE_URL),
            mark("troy", "it deletes the cache", None,
                 "https://github.com/ZJUCao/wordcount/issues/8#issuecomment-802")])

    def test_other_comments_mark_nothing(self):
        """A note without ``Risky:`` first, another feature's note, a comment that is no note,
        and ``Risky:`` later in the line: no mark, and F07 merges."""
        self.assert_next(self.report("not risky notes"), action="stage", item="F02", stage=1,
                         task="IF1", title=F2.title(1), branch=F2.branch(1), merged_by="f07",
                         spot="none", issue=8, risky=[])


class OrderTests(RiskyCase):
    """The marks' order: the engine's (PR 1's, then PR 2's), the Architect's, Troy's."""

    def test_marks_in_order(self):
        """Planted bug "PR 2 without PR 1's mark": PR 1's interface and ruling, PR 2's premise,
        PR 1's Architect line, then Troy's note."""
        expected = [mark("engine", "interface", 21), RULING_21, mark("engine", "premise", 22),
                    mark("architect", "network access", 21, curl(21, 0)),
                    mark("troy", "Troy asked", None, NOTE_URL)]
        self.assertEqual(self.risky_of("order", 22), expected)
        self.stage2_next("order", action="continue-pr", pr=22, merged_by="troy", attempts=3,
                         premise=True, spot="none", issue=8, risky=expected)


class HeadingTests(RiskyCase):
    """The spot check comment and TM8's real-run ruling are troy-mode's headings (contract 2)."""

    def assert_own(self, name: str, number: int, rounds: int) -> None:
        """Neither Troy's comment, nor a wait, nor an escalation; rounds as given, no attempt."""
        entry = self.open_entry(name, number)
        self.assertEqual((entry["troy_comments"], entry["waiting_for_troy"], entry["escalated"],
                          entry["rounds"], entry["attempts"]), ([], False, False, rounds, 0))

    def test_spot_check_comment_is_no_wait(self):
        """``Spot check for Troy: review after the merge`` after a review: no wait, not Troy's."""
        self.assert_own("spot heading", 21, 1)

    def test_real_run_ruling_is_troy_modes(self):
        """``Test Manager ruling, real run`` on the acceptance PR: not Troy's, not a round."""
        self.assert_own("real-run ruling", 26, 0)


class MergedCommentsTests(SpotCase):
    """A merged PR 1's comments are read once, kept in ``troy-mode/spot.json``; a failed read
    keeps nothing and says so (contract 4)."""

    @classmethod
    def setUpClass(cls):
        """Runs status twice in one clone, and twice in another whose first read fails."""
        case = pr2_case(ruled())
        cls.first, cls.fakes, cls.project = run_case(case)
        cls.first_calls = cls.fakes.gh_argvs()
        cls.fakes.clear()
        cls.second = cls.project.run("status", fakes=cls.fakes)
        cls.second_calls = cls.fakes.gh_argvs()
        failing = pr2_case(ruled(), issues_enabled=False, fail_calls=[["pr", "view", "21"]])
        cls.failed, fakes, cls.failed_project = run_case(failing)
        fakes.serve(**{k: v for k, v in failing.fakes.items() if k != "fail_calls"})
        fakes.clear()
        cls.retried = cls.failed_project.run("status", fakes=fakes)
        cls.retried_calls = fakes.gh_argvs()

    @staticmethod
    def views(calls) -> list:
        """The PR numbers of the ``gh pr view`` calls, sorted."""
        return sorted(argv[2] for argv in calls if argv[:2] == ["pr", "view"])

    def risky(self, out) -> object:
        """PR #22's ``risky`` in a status report, exit 0."""
        report = self.report_of(out, 0, "status")
        found = [p for p in report["open_prs"] if p["number"] == 22]
        self.assertEqual(len(found), 1, report["open_prs"])
        return found[0].get("risky", "missing")

    def test_first_run_reads_and_keeps(self):
        """The first run reads #21's comments and writes the cache."""
        self.assertEqual(self.risky(self.first), [RULING_21])
        self.assertIn("21", self.views(self.first_calls))
        self.assertTrue((common_git(self.project) / "troy-mode" / "spot.json").is_file())

    def test_second_run_does_not_read_again(self):
        """The second run views no merged PR and still marks PR 2."""
        self.assertEqual(self.risky(self.second), [RULING_21])
        self.assertEqual(self.views(self.second_calls), ["22"])

    def test_failed_read_is_a_note_and_no_mark(self):
        """``gh pr view 21`` fails: exit 0, no mark from #21, and the report's note."""
        self.assertEqual(self.risky(self.failed), [])
        notes = [n for n in self.failed.report["notes"]
                 if n.startswith("The comments of PR #21 could not be read (")]
        self.assertEqual(len(notes), 1, self.failed.report["notes"])
        self.assertTrue(notes[0].endswith("); its risky marks are not known."), notes[0])

    def test_failed_read_keeps_nothing(self):
        """The next run, with gh working, reads #21 again and marks PR 2."""
        self.assertEqual(self.risky(self.retried), [RULING_21])
        self.assertIn("21", self.views(self.retried_calls))


if __name__ == "__main__":
    unittest.main()
