"""Rework after a requirement change, and the change's approval (F07 design 5.1, 11.2, 14.1).

A feature is in rework while its Status cell starts "Needs rework" and no
stage of it has merged since the newest ``[docs] Change the requirements:``
commit (part 2 note, "In rework"). A stage PR opened before the change asks
for AR4 first. A change Troy merged on GitHub keeps a minor version, and
status asks to record his approval.

Planted bug of design 14.2 caught here: "a redo that leaves the later stages
counted" also shows in ``InReworkTests.test_a_redo_ends_the_rework``.
"""

import unittest
from dataclasses import replace

from flow_helpers import (
    CHANGE_PREFIX, F01, F02, PROGRESS, RECORD_REQUIREMENTS, REQUIREMENTS, TWO, FlowCase,
    Project, base_files, base_step, change_step, parallel, pr, progress_fields, progress_issues,
    record_step, requirements_files, rework, stage_pr, stage_step, stages, status_runs, step,
)

DOCS = "[docs] Add cases to the F01 test plan"


def history(*groups, files=None) -> list:
    """A project's first commit followed by the given steps.

    Args:
        *groups: Steps or lists of steps, in order.
        files: The first commit's files, or None for ``base_files()``.

    Returns:
        The steps, oldest first.
    """
    steps = [base_step(files)]
    for group in groups:
        steps.extend(group if isinstance(group, list) else [group])
    return steps


def merged_of(report: dict, feature_id: str) -> list:
    """The ``merged`` list of one feature in a status report."""
    return next(f["merged"] for f in report["features"] if f["id"] == feature_id)


def rework_change(feature=F01, summary: str = "Count blank lines", version: str = "2.0",
                  pr_number=None):
    """A change commit that marks one of F01 and F02 "Needs rework", approved in chat (2.0).

    Args:
        feature: The feature marked; the other keeps "Not started".
        summary: The change's summary, also named in the Status cell.
        version: The requirements' version after the change.
        pr_number: A squash PR number, or None.

    Returns:
        The step.
    """
    features = tuple(rework(f, summary) if f.id == feature.id else f for f in TWO)
    return change_step(summary, features, version, pr_number)


class InReworkTests(FlowCase):
    """When a feature is in rework, and the ``rework`` action (part 2 note, next)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per history, side by side."""
        upper = replace(F01, status="NEEDS REWORK (Count blank lines)")
        other = replace(F01, status="In progress")
        cls.outs = status_runs({
            "rework": (history(stages(F01, 3), rework_change()), []),
            "upper case": (history(stages(F01, 3), change_step(features=(upper, F02))), []),
            "squashed change": (history(stages(F01, 3), rework_change(pr_number=20)), []),
            "other status": (history(stages(F01, 3), change_step(features=(other, F02))), []),
            "no change commit": (history(stages(F01, 3), files=base_files((rework(F01), F02))),
                                 []),
            "redo merged": (history(stages(F01, 3), rework_change(), stage_step(F01, 1)), []),
            "newer change": (history(stages(F01, 3), rework_change(), stage_step(F01, 1),
                                     rework_change(summary="Count tabs", version="3.0")), []),
            "no stage merged": (history(rework_change()), []),
            "not the next feature": (history(stages(F01, 2), rework_change(F02)), []),
            "after an accepted feature": (history(stages(F01, 6), stages(F02, 2),
                                                  rework_change(F02)), []),
        })

    def test_feature_in_rework_asks_for_ar4(self):
        """F01 with 1 to 3 merged and marked "Needs rework" after the change: AR4 at stage 4."""
        report = self.report_of(self.outs["rework"])
        self.assertEqual(report["features"][0]["status"], "Needs rework (Count blank lines)")
        self.assertEqual(merged_of(report, "F01"), [1, 2, 3])
        self.assert_next(report, action="rework", item="F01", stage=4, task="AR4")

    def test_status_is_compared_in_lower_case(self):
        """"NEEDS REWORK (...)" counts too."""
        self.assert_next(self.report_of(self.outs["upper case"]), action="rework", item="F01",
                         stage=4, task="AR4")

    def test_squashed_change_commit_counts(self):
        """A change subject with `` (#20)`` is a change commit."""
        self.assert_next(self.report_of(self.outs["squashed change"]), action="rework",
                         item="F01", stage=4, task="AR4")

    def test_other_status_is_not_rework(self):
        """A change commit without "Needs rework" in F01's cell: the loop goes on with TE1."""
        self.assert_next(self.report_of(self.outs["other status"]), action="stage", item="F01",
                         stage=4, task="TE1", title=F01.title(4), branch=F01.branch(4),
                         merged_by="f07")

    def test_status_without_a_change_commit_is_not_rework(self):
        """"Needs rework" in the cell but no change commit on origin/main: no rework."""
        self.assert_next(self.report_of(self.outs["no change commit"]), action="stage",
                         item="F01", stage=4, task="TE1", title=F01.title(4),
                         branch=F01.branch(4), merged_by="f07")

    def test_a_redo_ends_the_rework(self):
        """The redo of stage 1 merged after the change: ``[1]``, and the test plan is next."""
        report = self.report_of(self.outs["redo merged"])
        self.assertEqual(merged_of(report, "F01"), [1])
        self.assert_next(report, action="stage", item="F01", stage=2, task="TM1",
                         title=F01.title(2), branch=F01.branch(2), merged_by="troy")

    def test_a_newer_change_starts_rework_again(self):
        """A second change after the redo: F01 is in rework again, at its stage 2."""
        report = self.report_of(self.outs["newer change"])
        self.assertEqual(merged_of(report, "F01"), [1])
        self.assert_next(report, action="rework", item="F01", stage=2, task="AR4")

    def test_feature_with_nothing_merged_starts_normally(self):
        """In rework but no stage merged: no ``rework`` action, stage 1 is next."""
        self.assert_next(self.report_of(self.outs["no stage merged"]), action="stage",
                         item="F01", stage=1, task="IF1", title=F01.title(1),
                         branch=F01.branch(1), merged_by="troy")

    def test_only_the_next_feature_counts(self):
        """F02 in rework while F01 is not accepted: F01's stage 3 is next."""
        self.assert_next(self.report_of(self.outs["not the next feature"]), action="stage",
                         item="F01", stage=3, task="DV1", title=F01.title(3),
                         branch=F01.branch(3), merged_by="f07")

    def test_next_feature_after_an_accepted_one(self):
        """F01 accepted and F02 in rework with 1 and 2 merged: AR4 for F02 at stage 3."""
        self.assert_next(self.report_of(self.outs["after an accepted feature"]),
                         action="rework", item="F02", stage=3, task="AR4")


STALE_NEXT = dict(action="rework", item="F01", stage=3, task="AR4", pr=7, title=F01.title(3),
                  branch=F01.branch(3))
CONTINUE_NEXT = dict(action="continue-pr", item="F01", stage=3, task="DV1", pr=7,
                     title=F01.title(3), branch=F01.branch(3), merged_by="f07")


def stale_run(case):
    """Clones the origin, adds the PR's remote-tracking branch if asked, and runs status.

    Args:
        case: ``(steps, prs, ref_at)``; ``ref_at`` is the commit (a revision
            of the clone) the branch ``origin/troy-mode/f01-3-mock`` is made on,
            with one commit on top, or None for no such branch.

    Returns:
        The outcome.
    """
    steps, prs, ref_at = case
    project = Project(steps)
    if ref_at is not None:
        parent = project.git("rev-parse", ref_at).strip()
        tree = project.git("rev-parse", f"{parent}^{{tree}}").strip()
        tip = project.git("commit-tree", tree, "-p", parent, "-m", F01.title(3)).strip()
        project.git("update-ref", f"refs/remotes/origin/{F01.branch(3)}", tip)
    return project.status(prs=prs)


class StaleStagePrTests(FlowCase):
    """A stage PR opened before the change asks for AR4 (design 11.2, part 2 note)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per case, side by side."""
        changed = history(stages(F01, 2), rework_change())
        twice = history(stages(F01, 2), rework_change(),
                        rework_change(summary="Count tabs", version="3.0"))
        mock = [stage_pr(7, F01, 3)]
        cases = {
            "no remote branch": (changed, mock, None),
            "branch before the change": (changed, mock, "origin/main~1"),
            "branch with the change": (changed, mock, "origin/main"),
            "branch with an older change only": (twice, mock, "origin/main~1"),
            "feature not in rework": (history(stages(F01, 2), change_step()), mock, None),
            "side PR first": (changed, mock + [pr(9, DOCS, "troy-mode/f01-docs")], None),
        }
        names = list(cases)
        cls.outs = dict(zip(names, parallel(stale_run, [cases[n] for n in names])))

    def test_pr_without_a_remote_branch_asks_for_ar4(self):
        """No ``origin/troy-mode/f01-3-mock`` at all: the PR may be stale, so AR4 first."""
        self.assert_next(self.report_of(self.outs["no remote branch"]), **STALE_NEXT)

    def test_branch_made_before_the_change_asks_for_ar4(self):
        """The PR's branch does not contain the change commit: AR4 first."""
        self.assert_next(self.report_of(self.outs["branch before the change"]), **STALE_NEXT)

    def test_branch_with_the_change_is_continued(self):
        """The PR's branch contains the change commit (rebased): DV1 goes on."""
        self.assert_next(self.report_of(self.outs["branch with the change"]), **CONTINUE_NEXT)

    def test_branch_must_contain_the_newest_change(self):
        """A branch with the first change but not the second: AR4 first."""
        self.assert_next(self.report_of(self.outs["branch with an older change only"]),
                         **STALE_NEXT)

    def test_feature_not_in_rework_is_continued(self):
        """A change that does not mark F01: its stage PR is continued even without a branch."""
        self.assert_next(self.report_of(self.outs["feature not in rework"]), **CONTINUE_NEXT)

    def test_side_pr_comes_before_the_stale_stage_pr(self):
        """A docs PR open beside the stale stage PR is continued first."""
        self.assert_next(self.report_of(self.outs["side PR first"]), action="continue-pr",
                         pr=9, title=DOCS, branch="troy-mode/f01-docs", merged_by="f07")


RECORD_NEXT = dict(action="record-approval", doc=REQUIREMENTS, title=RECORD_REQUIREMENTS,
                   branch="troy-mode/approve-requirements", merged_by="f07")
STAGE3_NEXT = dict(action="stage", item="F01", stage=3, task="DV1", title=F01.title(3),
                   branch=F01.branch(3), merged_by="f07")


class ChangeApprovalTests(FlowCase):
    """Recording Troy's approval of a change he merged on GitHub (design 11.2, part 2 note)."""

    @classmethod
    def setUpClass(cls):
        """Runs status on one clone per history, side by side."""
        typo = step("[docs] Fix a typo in the requirements", requirements_files(TWO, "2.1"))
        change_title = CHANGE_PREFIX + "Count blank lines"
        cls.outs = status_runs({
            "minor": (history(stages(F01, 2), change_step(version="1.1")), []),
            "squashed minor": (history(stages(F01, 2), change_step(version="1.2", pr=20)), []),
            "minor in rework": (history(stages(F01, 3), rework_change(version="1.1")), []),
            "approved in chat": (history(stages(F01, 2), change_step(version="2.0")), []),
            "recorded": (history(stages(F01, 2), change_step(version="1.1"),
                                 record_step(version="2.0")), []),
            "recorded before a newer change": (
                history(stages(F01, 2), change_step(version="1.1"), record_step(version="2.0"),
                        change_step("Count tabs", version="2.1")), []),
            "version at the change commit": (history(stages(F01, 2), change_step(version="2.0"),
                                                     typo), []),
            "no change commit": (history(stages(F01, 2), files=base_files(requirements="1.3")),
                                 []),
            "open change PR": (history(stages(F01, 2)),
                               [pr(9, change_title, "troy-mode/change-blank-lines")]),
            "open PR first": (history(stages(F01, 2), change_step(version="1.1")),
                              [stage_pr(7, F01, 3)]),
        })

    def test_change_merged_on_github_is_recorded(self):
        """The change left the requirements at 1.1: record Troy's approval, merged by F07."""
        report = self.report_of(self.outs["minor"])
        self.assertEqual(report["project"]["requirements"],
                         {"path": REQUIREMENTS, "version": "1.1", "approved": True})
        self.assert_next(report, **RECORD_NEXT)

    def test_squashed_change_is_recorded(self):
        """A squash subject with `` (#20)`` at 1.2: record it."""
        self.assert_next(self.report_of(self.outs["squashed minor"]), **RECORD_NEXT)

    def test_recording_comes_before_rework(self):
        """F01 in rework after a change at 1.1: record the approval first."""
        self.assert_next(self.report_of(self.outs["minor in rework"]), **RECORD_NEXT)

    def test_change_approved_in_chat_needs_no_record(self):
        """``approve`` raised it to 2.0: nothing to record, the loop goes on."""
        self.assert_next(self.report_of(self.outs["approved in chat"]), **STAGE3_NEXT)

    def test_record_after_the_change_ends_it(self):
        """A record commit newer than the change: nothing to record."""
        self.assert_next(self.report_of(self.outs["recorded"]), **STAGE3_NEXT)

    def test_record_older_than_the_newest_change_does_not_count(self):
        """change 1.1, record 2.0, change 2.1: record again."""
        self.assert_next(self.report_of(self.outs["recorded before a newer change"]),
                         **RECORD_NEXT)

    def test_version_is_read_at_the_newest_change_commit(self):
        """The change made 2.0; a later typo fix made 2.1: nothing to record."""
        self.assert_next(self.report_of(self.outs["version at the change commit"]),
                         **STAGE3_NEXT)

    def test_minor_version_without_a_change_commit_is_not_recorded(self):
        """Requirements at 1.3 with no change commit: nothing to record."""
        self.assert_next(self.report_of(self.outs["no change commit"]), **STAGE3_NEXT)

    def test_open_change_pr_waits_for_troy(self):
        """An open change PR is continued, with no task, and Troy merges it."""
        self.assert_next(self.report_of(self.outs["open change PR"]), action="continue-pr",
                         pr=9, title=CHANGE_PREFIX + "Count blank lines",
                         branch="troy-mode/change-blank-lines", merged_by="troy")

    def test_open_pr_comes_before_the_record(self):
        """``continue-pr`` stays above the change's ``record-approval``."""
        self.assert_next(self.report_of(self.outs["open PR first"]), action="continue-pr", pr=7,
                         item="F01", stage=3, task="DV1", title=F01.title(3),
                         branch=F01.branch(3), merged_by="f07")


class ReworkProgressTests(FlowCase):
    """The progress file during rework (part 2 note, the progress file)."""

    def test_stage_line_starts_with_the_stage_and_notes_are_carried(self):
        """Rework at stage 4: ``4 of 6.`` starts the Stage line, and a note survives a rewrite."""
        project = Project(history(stages(F01, 3), rework_change()))
        first = self.report_of(project.status("--note", "Architect attempt 1: failed"))
        self.assertEqual(first["next"]["action"], "rework")
        fields = progress_fields(project.read(PROGRESS))
        self.assertRegex(fields["Stage"], r"^4 of 6\.")
        self.report_of(project.status("--write-progress"))
        self.assertEqual(progress_issues(project.read(PROGRESS)), ["Architect attempt 1: failed"])


if __name__ == "__main__":
    unittest.main()
