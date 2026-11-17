"""Ideas (F15 design 5.1, 5.2, 9; 13.1 "Ideas"; interface note sections 1 to 3).

``status`` lists Troy's open idea issues in ``issues.ideas``, marks each
``new`` until troy-mode answers under a heading and again after Troy
writes, and gives the ``ideas`` action only at a natural stop.

Planted bugs of design 13.2 caught here:

- "an unlabeled issue not counted as an idea" and "a ``bug`` issue counted as
  one": ``WhichIssuesTests.test_ideas_are_labeled_idea_or_unlabeled``.
- "the ``ideas`` action between two stages": ``WhenTests.test_never_between_stages``.
"""

import unittest
from dataclasses import replace

from flow_helpers import (
    F01, F02, F03, FIVE, NEXT_KEYS, TWO, base_step, pr, release_title, stage_pr, stage_step,
    stages,
)
from issues_helpers import (
    ALL_LABELS, COMMIT1, IssuesCase, checklist_issue, gh_issue, passed, progress_marker,
    project_files, release_fakes, release_steps, released_steps, status_run, status_runs_with,
    waiting, zh_change_step,
)

TYPO = "[docs] Fix a typo in the README"
IDEA_BODY = "Please add a --lines option to wordcount, in a new version v0.3."
TEMPLATE = ".github/ISSUE_TEMPLATE/idea.md"
TEXT_LINE = "Take in Troy's new ideas as the Product Manager (PM6): #101, #102."
ISSUES_KEYS = {"error", "skipped", "ideas", "troy_comments", "device_test", "pending",
               "template"}


def idea(number: int = 101, labels=("idea",), comment_bodies=(), state: str = "OPEN") -> dict:
    """An idea issue of Troy's."""
    return gh_issue(number, f"Idea {number}", IDEA_BODY, labels, comment_bodies, state)


def base(features=TWO, **kwargs):
    """The first commit, with a Chinese mirror that has a features table."""
    return base_step(project_files(features, **kwargs))


def with_ideas(*issues, **more) -> dict:
    """Fakes keyword arguments serving the issues, with every F15 label present."""
    return {"all_issues": list(issues), "labels": list(ALL_LABELS), **more}


ONE = with_ideas(idea())
UNVERSIONED = (replace(F01, version="-"), replace(F02, version="Later"))
REWORK = replace(F01, status="Needs rework (Count blank lines)")


class IdeasCase(IssuesCase):
    """Helpers for reading ``issues`` and ``next`` in a status report."""

    def issues_of(self, out) -> dict:
        """The report's ``issues`` object, with exactly the note's keys."""
        report = self.report_of(out, 0, "status")
        self.assertEqual(set(report.get("issues") or {}), ISSUES_KEYS, report.get("issues"))
        return report["issues"]

    def assert_ideas_action(self, report: dict, numbers: list) -> None:
        """``next`` is the ``ideas`` action of PM6 with these new ideas."""
        nxt = report["next"]
        self.assertEqual(sorted(nxt), sorted(NEXT_KEYS), nxt)
        self.assertEqual((nxt["action"], nxt["task"], nxt["ideas"]), ("ideas", "PM6", numbers),
                         nxt)


class WhichIssuesTests(IdeasCase):
    """Which open issues are ideas (design 5.1; note section 2)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once with one issue of each kind."""
        issues = [
            idea(101), idea(102, labels=()), idea(103, labels=("bug",)),
            idea(104, labels=("progress",)), idea(105, labels=("device-test",)),
            idea(106, labels=("idea", "bug")), idea(107, labels=("question",)),
            idea(108, state="CLOSED"),
            gh_issue(109, "F01 数单词 / Count words", progress_marker("F01") + "\nOld.\n"),
            checklist_issue(110, "v0.1.0"),
        ]
        cls.outs = status_runs_with({"kinds": ([base()], with_ideas(*issues))})

    def test_ideas_are_labeled_idea_or_unlabeled(self):
        """Planted bugs "unlabeled not counted" and "a bug counted": #101 and #102 only."""
        issues = self.issues_of(self.outs["kinds"][0])
        self.assertEqual([entry["number"] for entry in issues["ideas"]], [101, 102])
        self.assertIsNone(issues["error"])
        self.assertIsNone(issues["skipped"])

    def test_idea_entry_holds_the_issue(self):
        """An idea's entry: number, title, URL, label names, body, ``new``, and comments."""
        entry = self.issues_of(self.outs["kinds"][0])["ideas"][0]
        self.assertEqual(entry, {"number": 101, "title": "Idea 101",
                                 "url": "https://github.com/ZJUCao/wordcount/issues/101",
                                 "labels": ["idea"], "body": IDEA_BODY, "new": True,
                                 "comments": []})

    def test_new_ideas_give_the_action_before_the_first_stage(self):
        """F01 not started: the ``ideas`` action with both new ideas, and only reads."""
        out, fakes, _ = self.outs["kinds"]
        self.assert_ideas_action(self.report_of(out, 0, "status"), [101, 102])
        self.assert_read_only(fakes)


NEW_CASES = {
    "no comment": (),
    "Troy's comment": ("It should count blank lines too.",),
    "answered": ("It should count blank lines too.",
                 "Idea: later\n\nThis waits for v0.3, as the idea says."),
    "Troy wrote again": ("It should count blank lines too.",
                         "Idea: later\n\nThis waits for v0.3, as the idea says.",
                         "Please do it now."),
}


class NewTests(IdeasCase):
    """``new`` until troy-mode's heading comment, and again after Troy writes (note 3)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per idea's comments, side by side."""
        cls.outs = status_runs_with({name: ([base()], with_ideas(idea(comment_bodies=bodies)))
                                     for name, bodies in NEW_CASES.items()})

    def entry(self, name: str) -> dict:
        """The one idea's entry."""
        ideas = self.issues_of(self.outs[name][0])["ideas"]
        self.assertEqual([entry["number"] for entry in ideas], [101], ideas)
        return ideas[0]

    def test_new_flags(self):
        """New without comments and with Troy's; not after ``Idea: later``; new again after."""
        expected = {"no comment": True, "Troy's comment": True, "answered": False,
                    "Troy wrote again": True}
        for name, new in expected.items():
            with self.subTest(case=name):
                self.assertIs(self.entry(name)["new"], new)

    def test_comments_say_who_wrote_them(self):
        """Each comment is Troy's or troy-mode's, by its heading, oldest first."""
        self.assertEqual(self.entry("Troy wrote again")["comments"], [
            {"by": "troy", "body": NEW_CASES["Troy wrote again"][0]},
            {"by": "troy-mode", "body": NEW_CASES["Troy wrote again"][1]},
            {"by": "troy", "body": NEW_CASES["Troy wrote again"][2]}])

    def test_answered_idea_gives_no_action(self):
        """Pair: no new idea: F01's first stage is next, not ``ideas``."""
        report = self.report_of(self.outs["answered"][0], 0, "status")
        self.assert_next(report, action="stage", item="F01", stage=1, task="IF1",
                         title=F01.title(1), branch=F01.branch(1), merged_by="troy")

    def test_troy_writing_again_gives_the_action(self):
        """Troy's comment after the answer: ``ideas`` again."""
        self.assert_ideas_action(self.report_of(self.outs["Troy wrote again"][0], 0, "status"),
                                 [101])


def accepted_unversioned() -> list:
    """Both features accepted, with Version cells that name no version."""
    return [base(UNVERSIONED), *stages(F01, 6), *stages(F02, 6)]


class WhenTests(IdeasCase):
    """The ``ideas`` action only at a natural stop (design 5.2; note section 3)."""

    @classmethod
    def setUpClass(cls):
        """Runs status with one new idea in each state, side by side."""
        open_release = release_fakes(passed(1, COMMIT1), waiting(), all_issues=[idea()])
        cls.outs = status_runs_with({
            "first stage": ([base()], ONE),
            "version test plan": ([base(plans=False)], ONE),
            "version tests": (release_steps(tested=False), ONE),
            "release PR": (release_steps(), ONE),
            "all accepted": (accepted_unversioned(), ONE),
            "ask approvals": ([base(FIVE), *stages(F01, 6), *stages(F02, 6), *stages(F03, 6)],
                              ONE),
            "stage 2": ([base(), stage_step(F01, 1)], ONE),
            "stage 4": ([base(), *stages(F01, 3)], ONE),
            "open stage PR": ([base(), *stages(F01, 2)],
                              with_ideas(idea(), prs=[stage_pr(43, F01, 3)])),
            "open docs PR": ([base()], with_ideas(idea(), prs=[pr(57, TYPO, "troy-mode/typo")])),
            "open release PR": (release_steps(), open_release),
            "rework": ([base(), *stages(F01, 3),
                        zh_change_step("Count blank lines", (REWORK, F02),
                                       statuses={"F01": "需要返工（数空行）"})], ONE),
            "record approval": ([base(), stage_step(F01, 1, design="0.4")], ONE),
            "tag": (released_steps(), ONE),
        })

    def report(self, name: str) -> dict:
        """The case's status report, exit 0, with idea #101 read and new."""
        out, fakes, _ = self.outs[name]
        ideas = self.issues_of(out)["ideas"]
        self.assertEqual([(e["number"], e["new"]) for e in ideas], [(101, True)])
        self.assert_read_only(fakes)
        return out.report

    def test_at_each_natural_stop(self):
        """Before the first stage, a version test plan, a release not started, approvals,
        and "every feature accepted": ``ideas`` (design 5.2)."""
        for name in ("first stage", "version test plan", "version tests", "release PR",
                     "all accepted", "ask approvals"):
            with self.subTest(case=name):
                self.assert_ideas_action(self.report(name), [101])

    def test_never_between_stages(self):
        """Planted bug "the ideas action between two stages": stage 2 and stage 4 go on."""
        self.assert_next(self.report("stage 2"), action="stage", item="F01", stage=2,
                         task="TM1", title=F01.title(2), branch=F01.branch(2),
                         merged_by="troy")
        self.assert_next(self.report("stage 4"), action="stage", item="F01", stage=4,
                         task="TE1", title=F01.title(4), branch=F01.branch(4), merged_by="f07")

    def test_never_during_an_open_pr(self):
        """An open stage PR or docs PR is continued first."""
        self.assert_next(self.report("open stage PR"), action="continue-pr", pr=43, item="F01",
                         stage=3, task="DV1", title=F01.title(3), branch=F01.branch(3),
                         merged_by="f07")
        self.assert_next(self.report("open docs PR"), action="continue-pr", pr=57, title=TYPO,
                         branch="troy-mode/typo", merged_by="f07")

    def test_never_during_an_open_release(self):
        """The open release PR waits for Troy's test: the release goes on."""
        self.assert_next(self.report("open release PR"), action="release", step="troy-test",
                         item="v0.1", tag="v0.1.0", pr=30, title=release_title("v0.1.0"),
                         branch="troy-mode/release-v0.1.0", merged_by="f07")

    def test_never_for_work_already_started(self):
        """Rework, a record of Troy's approval, and a tag go on (note section 3)."""
        expected = {"rework": "rework", "record approval": "record-approval", "tag": "tag"}
        for name, action in expected.items():
            with self.subTest(case=name):
                nxt = self.report(name)["next"]
                self.assertEqual((nxt["action"], nxt["ideas"]), (action, None), nxt)


class TextReportTests(IdeasCase):
    """The text report's line for the ``ideas`` action (note section 3)."""

    def test_text_line_names_the_new_ideas(self):
        """``Take in Troy's new ideas as the Product Manager (PM6): #101, #102.``"""
        out, _, _ = status_run([base()], with_ideas(idea(101), idea(102, labels=())),
                               json_report=False)
        self.assert_exit(out, 0)
        self.assertIn(TEXT_LINE, out.stdout)


DISABLED = "the 'ZJUCao/wordcount' repository has disabled issues"
BAD_GATEWAY = "HTTP 502: Bad Gateway (https://api.github.com/graphql)"


class UnreadableTests(IdeasCase):
    """When status cannot read the issues (design 9; note section 1, "Failures")."""

    @classmethod
    def setUpClass(cls):
        """Runs status with each new call failing, side by side."""
        cls.outs = status_runs_with({
            "issue list": ([base()], with_ideas(idea(), fail_on=[
                (["issue", "list", "--state", "all"], BAD_GATEWAY)])),
            "PR list": ([base()], with_ideas(idea(), fail_on=[
                (["pr", "list", "--state", "all"], BAD_GATEWAY)])),
            "disabled": ([base()], with_ideas(idea(), fail_on=[
                (["issue", "list", "--state", "all"], DISABLED)])),
        })

    def test_failed_read_is_an_error_and_never_guessed(self):
        """Either call failing: exit 0, the gh error, no ideas, no checklist, no action."""
        for name in ("issue list", "PR list"):
            with self.subTest(case=name):
                issues = self.issues_of(self.outs[name][0])
                self.assertIsInstance(issues["error"], str)
                self.assertIn("502", issues["error"])
                self.assertEqual((issues["ideas"], issues["device_test"], issues["skipped"]),
                                 ([], None, None))
                self.assert_next(self.report_of(self.outs[name][0]), action="stage",
                                 item="F01", stage=1, task="IF1", title=F01.title(1),
                                 branch=F01.branch(1), merged_by="troy")

    def test_issues_turned_off_are_skipped_not_an_error(self):
        """GitHub's "disabled issues": ``skipped``, no error, and the flow goes on."""
        issues = self.issues_of(self.outs["disabled"][0])
        self.assertEqual((issues["skipped"], issues["error"], issues["ideas"]),
                         ("issues are turned off", None, []))
        self.assert_next(self.report_of(self.outs["disabled"][0]), action="stage", item="F01",
                         stage=1, task="IF1", title=F01.title(1), branch=F01.branch(1),
                         merged_by="troy")


class TemplateTests(IdeasCase):
    """``issues.template``: the idea template on origin/main (design 12; note section 3)."""

    @classmethod
    def setUpClass(cls):
        """Runs status with and without the template."""
        with_template = project_files(extra={TEMPLATE: "---\nname: Idea / 想法\n---\n"})
        cls.outs = status_runs_with({"with": ([base_step(with_template)], ONE),
                                     "without": ([base()], ONE)})

    def test_template_present(self):
        """The template on origin/main: true, and no note names it."""
        report = self.report_of(self.outs["with"][0], 0, "status")
        self.assertIs(self.issues_of(self.outs["with"][0])["template"], True)
        self.assertFalse([note for note in report["notes"] if TEMPLATE in note],
                         report["notes"])

    def test_template_missing_is_noted(self):
        """Pair: no template: false, and a note names the file and ``upgrade troy-mode``."""
        report = self.report_of(self.outs["without"][0], 0, "status")
        self.assertIs(self.issues_of(self.outs["without"][0])["template"], False)
        notes = [note for note in report["notes"] if TEMPLATE in note]
        self.assertEqual(len(notes), 1, report["notes"])
        self.assertIn("upgrade troy-mode", notes[0])


if __name__ == "__main__":
    unittest.main()
