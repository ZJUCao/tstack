"""Progress group (F07 design 5.2, 14.1): ``.troy-mode/progress.md`` from ``status``.

The file follows F01's ``progress`` template, in English, with no template
marker, and status rebuilds it when it is missing or out of date.
"""

import re
import unittest

from flow_helpers import (
    F01, PROGRESS, PROGRESS_FIELDS, FlowCase, Project, base_files, base_step, comments,
    progress_fields, progress_issues, stage_pr, stages, step,
)

CJK = re.compile(r"[　-〿㐀-鿿＀-￯]")


def stage_three_project() -> Project:
    """A clone whose origin/main has F01's stages 1 and 2, so stage 3 is next."""
    return Project([base_step(), *stages(F01, 2)], branch=F01.branch(3))


def rebuilt_note(report: dict) -> bool:
    """Whether a note says that the progress file was rebuilt."""
    return any("progress" in note.lower() and "rebuilt" in note.lower()
               for note in report["notes"])


class ProgressShapeTests(FlowCase):
    """The progress file for an open mock PR with one review."""

    @classmethod
    def setUpClass(cls):
        """Runs ``status --write-progress`` once with PR #7 open."""
        cls.project = stage_three_project()
        review = "Code Reviewer review, round 1: changes-requested\n\n1. Naming."
        cls.out = cls.project.status("--write-progress", prs=[stage_pr(7, F01, 3)],
                                     comments_by_pr={7: comments(review)})
        cls.raw = cls.project.read_bytes(PROGRESS) if cls.project.exists(PROGRESS) else b""
        cls.text = cls.raw.decode("utf-8")

    def test_report_says_the_file_was_written(self):
        """``progress`` names the file, written in this run, and rebuilt because it was missing."""
        report = self.report_of(self.out)
        self.assertEqual(report["progress"], {"path": PROGRESS, "written": True, "rebuilt": True})

    def test_lines_follow_the_template(self):
        """A ``# Progress`` heading and the template's eight fields, in its order."""
        lines = self.text.split("\n")
        self.assertEqual(lines[0], "# Progress", self.text)
        found = [m.group(1) for m in (re.match(r"^- ([A-Za-z ]+):", line) for line in lines) if m]
        self.assertEqual(found, list(PROGRESS_FIELDS), self.text)

    def test_file_is_english_with_lf_and_no_marker(self):
        """LF line endings, no ``{{`` marker, no template comment, and no Chinese text."""
        self.assertNotEqual(self.raw, b"")
        self.assertNotIn(b"\r", self.raw)
        self.assertNotIn("{{", self.text)
        self.assertNotIn("<!-- template:", self.text)
        self.assertIsNone(CJK.search(self.text), self.text)

    def test_field_values(self):
        """The fields name the version, the feature, stage 3, PR #7, and nothing waiting."""
        fields = progress_fields(self.text)
        self.assertTrue(fields["Current version"].startswith("v0.1"), fields)
        self.assertEqual(fields["Current feature"], "F01 Count words")
        self.assertRegex(fields["Stage"], r"^3\b")
        for text in ("#7", "[F01 3/6 mock] Count words",
                     "https://github.com/ZJUCao/wordcount/pull/7"):
            self.assertIn(text, fields["Open PRs"])
        self.assertEqual(fields["Waiting on Troy"], "Nothing")
        self.assertEqual(fields["Open issues"], "None")
        self.assertEqual(progress_issues(self.text), [])
        self.assertRegex(fields["Last updated"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


class RebuildTests(FlowCase):
    """When status writes the file, and when it leaves it alone (design 5.2)."""

    def test_missing_file_is_rebuilt_with_a_note(self):
        """Plain status in a tree without the file writes it and says it rebuilt it."""
        project = stage_three_project()
        report = self.report_of(project.status())
        self.assertEqual((report["progress"]["written"], report["progress"]["rebuilt"]),
                         (True, True))
        self.assertTrue(rebuilt_note(report), report["notes"])
        self.assertEqual(progress_fields(project.read(PROGRESS))["Open PRs"], "None")

    def test_up_to_date_file_is_left_alone(self):
        """A second plain status finds the file current: not written, not rebuilt, no note."""
        project = stage_three_project()
        self.report_of(project.status())
        before = project.read_bytes(PROGRESS)
        report = self.report_of(project.status())
        self.assertEqual((report["progress"]["written"], report["progress"]["rebuilt"]),
                         (False, False))
        self.assertFalse(rebuilt_note(report), report["notes"])
        self.assertEqual(project.read_bytes(PROGRESS), before)

    def test_out_of_date_file_is_rebuilt(self):
        """A file whose Next action differs is rewritten, with the rebuilt note."""
        project = stage_three_project()
        self.report_of(project.status())
        text = project.read(PROGRESS)
        action = progress_fields(text)["Next action"]
        project.write(PROGRESS, text.replace(f"- Next action: {action}",
                                             "- Next action: Something else entirely."))
        report = self.report_of(project.status())
        self.assertEqual((report["progress"]["written"], report["progress"]["rebuilt"]),
                         (True, True))
        self.assertTrue(rebuilt_note(report), report["notes"])
        self.assertEqual(progress_fields(project.read(PROGRESS))["Next action"], action)

    def test_write_progress_rewrites_a_current_file(self):
        """``--write-progress`` on a current file writes it without calling it rebuilt."""
        project = stage_three_project()
        self.report_of(project.status())
        report = self.report_of(project.status("--write-progress"))
        self.assertEqual((report["progress"]["written"], report["progress"]["rebuilt"]),
                         (True, False))

    def test_no_file_outside_a_troy_mode_tree(self):
        """A tree without .troy-mode/ never gets the file, even with ``--write-progress``."""
        project = Project([step("Initial commit", {"README.md": "# wordcount\n"})])
        report = self.report_of(project.status("--write-progress"))
        self.assertEqual((report["progress"]["written"], report["progress"]["rebuilt"]),
                         (False, False))
        self.assertFalse(project.exists(".troy-mode"))

    def test_before_a_feature_is_next(self):
        """While the requirements are missing, Current version and Current feature are None."""
        project = Project([base_step(base_files(requirements=None, architecture=None))])
        self.report_of(project.status())
        fields = progress_fields(project.read(PROGRESS))
        self.assertEqual((fields["Current version"], fields["Current feature"]), ("None", "None"))


class CarryTests(FlowCase):
    """Notes and the waiting text carried from the old file (interface note, Carried)."""

    def test_notes_are_kept_in_order_and_counted(self):
        """``--note`` adds after the carried notes, and attempt notes count for next.attempts."""
        project = stage_three_project()
        first = self.report_of(project.status("--note", "Developer attempt 1: failed"))
        self.assertEqual(first["next"]["attempts"], 1)
        second = self.report_of(project.status("--note", "Developer attempt 2: failed",
                                               "--note", "ruff is slow on Windows"))
        self.assertEqual(second["next"]["attempts"], 2)
        third = self.report_of(project.status())
        self.assertEqual(third["next"]["attempts"], 2)
        self.assertEqual(progress_issues(project.read(PROGRESS)),
                         ["Developer attempt 1: failed", "Developer attempt 2: failed",
                          "ruff is slow on Windows"])

    def test_notes_are_dropped_when_the_stage_changes(self):
        """A file written for another stage keeps none of its notes."""
        project = stage_three_project()
        self.report_of(project.status("--note", "Developer attempt 1: failed"))
        text = project.read(PROGRESS)
        stage = progress_fields(text)["Stage"]
        project.write(PROGRESS, text.replace(f"- Stage: {stage}", "- Stage: 2 of 6. Test plan."))
        report = self.report_of(project.status())
        self.assertIs(report["progress"]["rebuilt"], True)
        self.assertEqual(report["next"]["attempts"], 0)
        new = project.read(PROGRESS)
        self.assertEqual(progress_issues(new), [])
        self.assertEqual(progress_fields(new)["Open issues"], "None")

    def test_waiting_text_is_set_carried_and_cleared(self):
        """``--waiting`` sets the text, a later status keeps it, and ``--waiting ""`` clears it."""
        project = stage_three_project()
        text = "Approve the F01 design in chat"
        first = self.report_of(project.status("--waiting", text))
        self.assertEqual(first["waiting_on_troy"], text)
        self.assertEqual(progress_fields(project.read(PROGRESS))["Waiting on Troy"], text)
        second = self.report_of(project.status())
        self.assertEqual(second["waiting_on_troy"], text)
        third = self.report_of(project.status("--waiting", ""))
        self.assertIsNone(third["waiting_on_troy"])
        self.assertEqual(progress_fields(project.read(PROGRESS))["Waiting on Troy"], "Nothing")

    def test_troys_reply_on_the_pr_ends_a_carried_wait(self):
        """A wait written while PR #7 waited is not carried once Troy replies on the PR.

        Added after the test writer found that a carried "PR #7: Waiting for
        Troy" text would outlive Troy's reply. While the current work has an
        open PR, its comments alone say whether it waits on Troy.
        """
        project = stage_three_project()
        bodies = ("Code Reviewer review, round 1: approved\n\nNone",
                  "Waiting for Troy: approve this PR")
        first = self.report_of(project.status("--write-progress", prs=[stage_pr(7, F01, 3)],
                                              comments_by_pr={7: comments(*bodies)}))
        self.assertEqual(first["waiting_on_troy"], "PR #7: Waiting for Troy: approve this PR")
        self.assertIn("Waiting for Troy", progress_fields(project.read(PROGRESS))["Waiting on Troy"])
        replied = comments(*bodies, "Looks good, go on.")
        second = self.report_of(project.status(prs=[stage_pr(7, F01, 3)],
                                               comments_by_pr={7: replied}))
        self.assertIsNone(second["waiting_on_troy"])
        self.assertEqual(second["open_prs"][0]["troy_comments"], ["Looks good, go on."])
        self.assertEqual(progress_fields(project.read(PROGRESS))["Waiting on Troy"], "Nothing")

    def test_attempts_take_the_higher_of_pr_and_notes(self):
        """A PR with attempt 1 and a note with attempt 2: next.attempts is 2, the PR's stays 1."""
        project = stage_three_project()
        by_pr = {7: comments("Developer attempt 1: failed\n\nmypy: 1 error")}
        report = self.report_of(project.status("--note", "Developer attempt 2: failed",
                                               prs=[stage_pr(7, F01, 3)], comments_by_pr=by_pr))
        self.assertEqual(report["open_prs"][0]["attempts"], 1)
        self.assertEqual(report["next"]["attempts"], 2)


if __name__ == "__main__":
    unittest.main()
