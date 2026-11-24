"""The release step ``security-review`` in ``status`` (tstack #75; F08 design 3.2, 3.3, 5.9).

Written from the build contract for tstack #75 (section C) and F08 design 3.1 to 3.3, 5.8,
5.9, 11.1, and 11.2 before the code exists. Black-box: ``troy_flow.py status --json`` runs
as a subprocess with a fake gh that serves the open release PR and its comments.

- ``StepTests``: with an open release PR, ``security-review`` until a review approved,
  ``bugs`` after one that requested changes while an open bug Troy has not deferred is left,
  then ``security-review`` again; after an approval the steps of today; a patch release too.
- ``ReviewObjectTests``: ``release.review`` at the step: the run number, the base (the
  newest release commit of any tag, or the root commit), its tag, the branch, and the
  commands, with ``git remote set-head origin --auto`` only when ``origin/HEAD`` is missing;
  null at every other step.
- ``CommentTests``: ``release.security`` from the comments, oldest first, and the heading
  never counted as Troy's comment.

Planted bugs of F08 design 11.2 (F04 D280 to D283) caught here:

- "the review's base taken from the previous version's tag instead of the previous release
  commit of any tag": ``ReviewObjectTests.test_base_is_the_newest_release_commit``.
- "the review asked for again after it approved":
  ``StepTests.test_no_second_review_after_an_approval``.
- "the release test offered before the review": ``StepTests.test_review_comes_first``.
- "a patch release without it": ``StepTests.test_patch_release_gets_the_review``.

Run from the repository root:
python -B -m unittest discover -s troy-mode/flow/tests -p "test_security_release.py" -v
"""

import unittest
from dataclasses import replace
from typing import Mapping, Optional, Sequence

from flow_helpers import (
    ANY, F01, F02, F03, Fakes, FlowCase, Outcome, Project, accepted_plan_files, base_files,
    base_step, bug_step, comments, issue, merged_pr, origin_repo, parallel, release_pr,
    release_step, release_title, stages, subject_commits, version_tests_step,
)

F03V2 = replace(F03, version="v0.2")
THREE = (F01, F02, F03V2)
TAG = "v0.1.0"
PATCH = "v0.1.1"
NEXT = "v0.2.0"
CRASH = "Crash on empty history"
RELEASE_BRANCH = f"troy-mode/release-{TAG}"

BASE = base_step(base_files(THREE))
ACCEPTED = [BASE, *stages(F01, 6), *stages(F02, 6)]
TESTED = ACCEPTED + [version_tests_step("v0.1")]
RELEASED = TESTED + [release_step(TAG, accepted_plan_files("v0.1", ["F01", "F02"], [TAG]))]
PATCHED = RELEASED + [bug_step("B14", "test", "Bug B14"), bug_step("B14", "fix", "Bug B14")]
LATER = PATCHED + [release_step(PATCH, accepted_plan_files("v0.1", ["F01", "F02"], [TAG, PATCH]),
                                pr=61),
                   *stages(F03V2, 6), version_tests_step("v0.2")]

RETRO = "Retrospective: v0.1.0\n\nNothing repeated in two or more PRs."
PASSED = "Release test, run 1: passed\n\nv0.1-S01 passed.\nv0.1-S03 passed."
FAILED = "Release test, run 1: failed\n\nv0.1-S01 failed.\n\nFailed tests:\n- x::y"
WAITING = "Waiting for Troy: accept v0.1.0"
ACCEPTED_BY_TROY = "Release test by Troy, run 1: accepted\n\nTroy: it works on my laptop."
TROY_NOTE = "Please look at the config reader first."


def review(run: int, result: str) -> str:
    """A security review comment of F08 design 5.9: the heading, then the findings."""
    findings = "None." if result == "approved" else "1. Blocking: src/wordcount/x.py:3."
    return f"Security review, run {run}: {result}\n\nFindings: {findings}"


def security(*pairs) -> list:
    """``release.security`` entries from ``(run, result)`` pairs."""
    return [{"run": run, "result": result} for run, result in pairs]


def review_branch(tag: str) -> str:
    """The local review branch of a release (F08 design 5.9)."""
    return f"troy-mode/{tag}-security"


def commit_tree(base: str, tag: str) -> str:
    """The command that makes the review commit, as contract C gives it."""
    return f'git commit-tree "origin/main^{{tree}}" -p {base} -m "Security review of {tag}"'


def switch(tag: str) -> str:
    """The command that puts the checkout on the review commit, ``<commit>`` written as is."""
    return f"git switch -c {review_branch(tag)} <commit>"


def released_fakes(**more) -> dict:
    """v0.1.0 tagged, its release PR #40 merged with its retrospective."""
    fakes = {"releases": [TAG], "merged": [merged_pr(40, release_title(TAG))],
             "comments": {40: comments(RETRO)}}
    fakes.update(more)
    return fakes


def open_release(number: int, tag: str, *bodies: str, issues: Sequence = (),
                 base: Optional[Mapping] = None) -> dict:
    """Fakes keyword arguments for one open release PR with its comments.

    Args:
        number: The release PR's number.
        tag: Its tag.
        *bodies: Its comments, oldest first.
        issues: The open bug issues.
        base: Other fakes keyword arguments to start from.

    Returns:
        The keyword arguments.
    """
    fakes = dict(base or {})
    fakes["prs"] = [release_pr(number, tag)]
    fakes["comments"] = {**dict(fakes.get("comments", {})), number: comments(*bodies)}
    fakes["issues"] = list(issues)
    return fakes


def run_status(case: tuple) -> tuple:
    """Clones one origin, optionally drops ``origin/HEAD``, and runs ``status --json``.

    Args:
        case: ``(steps, fakes keyword arguments, drop origin/HEAD)``.

    Returns:
        ``(outcome, clone)``.
    """
    steps, fakes, drop = case
    project = Project(steps)
    if drop:
        project.git("symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    return project.status(fakes=Fakes(**fakes)), project


def status_cases(cases: Mapping[str, tuple]) -> dict:
    """Runs status for every case side by side.

    Args:
        cases: A name mapped to ``(steps, fakes keyword arguments)`` or ``(steps, fakes
            keyword arguments, drop origin/HEAD)``.

    Returns:
        Each name mapped to ``(outcome, clone)``.
    """
    full = {name: (case[0], case[1], case[2] if len(case) > 2 else False)
            for name, case in cases.items()}
    for steps in {repr(case[0]): case[0] for case in full.values()}.values():
        origin_repo(steps)
    names = list(full)
    return dict(zip(names, parallel(run_status, [full[name] for name in names])))


def first_release(*bodies: str, issues: Sequence = ()) -> tuple:
    """v0.1.0's open release PR #30, the project's first release, with its comments."""
    return TESTED, open_release(30, TAG, *bodies, issues=issues)


def patch_release(*bodies: str, issues: Sequence = ()) -> tuple:
    """v0.1.1's open release PR #60 after v0.1.0 and B14's fix, with its comments."""
    return PATCHED, open_release(60, PATCH, *bodies, issues=issues, base=released_fakes())


def later_release(*bodies: str) -> tuple:
    """v0.2.0's open release PR #50 after v0.1.0 and the patch v0.1.1 (squashed, #61)."""
    base = released_fakes(releases=[TAG, PATCH],
                          merged=[merged_pr(40, release_title(TAG)),
                                  merged_pr(61, release_title(PATCH))])
    return LATER, open_release(50, NEXT, *bodies, base=base)


CASES = {
    "no review": first_release(),
    "no review, origin/HEAD missing": (*first_release(), True),
    "a release test before any review": first_release(PASSED, WAITING),
    "changes requested, bug open": first_release(review(1, "changes-requested"),
                                                 issues=[issue(15, "Wrong total"),
                                                         issue(12, CRASH)]),
    "changes requested, bug deferred": first_release(review(1, "changes-requested"),
                                                     "Bug deferred by Troy: #12",
                                                     issues=[issue(12, CRASH)]),
    "changes requested, bugs fixed": first_release(review(1, "changes-requested")),
    "approved": first_release(review(1, "approved")),
    "approved after changes": first_release(review(1, "changes-requested"),
                                            review(2, "approved")),
    "approved, run failed, bugs fixed": first_release(review(1, "approved"), FAILED),
    "approved, run failed, bug open": first_release(review(1, "approved"), FAILED,
                                                    issues=[issue(12, CRASH)]),
    "approved, run passed": first_release(review(1, "approved"), PASSED, WAITING),
    "approved, Troy accepted": first_release(review(1, "approved"), PASSED, WAITING,
                                             ACCEPTED_BY_TROY),
    "Troy's comment, then a review": first_release(TROY_NOTE, review(1, "changes-requested")),
    "a heading on the second line": first_release("Note:\nSecurity review, run 5: approved"),
    "patch, no review": patch_release(),
    "patch, changes requested": patch_release(review(1, "changes-requested")),
    "patch, approved": patch_release(review(1, "approved")),
    "later version, no review": later_release(),
    "version tests next": (ACCEPTED, {}),
    "release PR next": (TESTED, {}),
}
_RUNS: dict = {}


def runs() -> dict:
    """Runs every case once for the whole file."""
    if not _RUNS:
        _RUNS.update(status_cases(CASES))
    return _RUNS


class SecurityStatusCase(FlowCase):
    """Reads the shared status runs."""

    @classmethod
    def setUpClass(cls):
        """Runs every case once."""
        cls.runs = runs()

    def report(self, name: str) -> dict:
        """The report of one case, which must have exit code 0."""
        out: Outcome = self.runs[name][0]
        return self.report_of(out, 0, "status")

    def clone(self, name: str) -> Project:
        """The clone one case ran in."""
        return self.runs[name][1]


FIRST_NEXT = dict(action="release", item="v0.1", tag=TAG, pr=30, title=release_title(TAG),
                  merged_by="f07")
REVIEW_NEXT = dict(FIRST_NEXT, step="security-review", task="CR2",
                   branch=review_branch(TAG), merged_by=ANY)
PATCH_REVIEW_NEXT = dict(action="release", item="v0.1", tag=PATCH, pr=60,
                         title=release_title(PATCH), step="security-review", task="CR2",
                         branch=review_branch(PATCH), merged_by=ANY)


class StepTests(SecurityStatusCase):
    """Contract C: the step ``security-review`` and the steps around it."""

    def test_review_comes_first(self):
        """An open release PR without a review: ``security-review``, with CR2 on the review
        branch and the release PR's number and title, even after a release test passed.

        Planted bug caught: "the release test offered before the review".
        """
        for name in ("no review", "a release test before any review"):
            with self.subTest(case=name):
                self.assert_next(self.report(name), **REVIEW_NEXT)

    def test_changes_requested_with_an_open_bug_goes_to_the_bugs(self):
        """Run 1 requested changes and bugs #15 and #12 are open: TM5 on B12, as today."""
        self.assert_next(self.report("changes requested, bug open"), step="bugs", item="B12",
                         task="TM5", branch=RELEASE_BRANCH,
                         **{k: v for k, v in FIRST_NEXT.items() if k != "item"})

    def test_review_again_once_the_bugs_are_fixed_or_deferred(self):
        """Run 1 requested changes and no open bug is left that Troy has not deferred: the
        review again."""
        for name in ("changes requested, bugs fixed", "changes requested, bug deferred"):
            with self.subTest(case=name):
                self.assert_next(self.report(name), **REVIEW_NEXT)

    def test_after_an_approval_the_release_test(self):
        """The newest review approved and no run yet: the release test, as today."""
        for name in ("approved", "approved after changes"):
            with self.subTest(case=name):
                self.assert_next(self.report(name), step="release-test", branch=RELEASE_BRANCH,
                                 **FIRST_NEXT)

    def test_no_second_review_after_an_approval(self):
        """Approved, then a failed release test whose bugs are fixed: the release test again,
        not the review.

        Planted bug caught: "the review asked for again after it approved".
        """
        self.assert_next(self.report("approved, run failed, bugs fixed"), step="release-test",
                         branch=RELEASE_BRANCH, **FIRST_NEXT)

    def test_later_steps_as_today(self):
        """After an approval: ``bugs``, ``troy-test``, and ``accept`` as today."""
        self.assert_next(self.report("approved, run failed, bug open"), step="bugs",
                         item="B12", task="TM5", branch=RELEASE_BRANCH,
                         **{k: v for k, v in FIRST_NEXT.items() if k != "item"})
        self.assert_next(self.report("approved, run passed"), step="troy-test",
                         branch=RELEASE_BRANCH, **FIRST_NEXT)
        self.assert_next(self.report("approved, Troy accepted"), step="accept", task="PM4",
                         branch=RELEASE_BRANCH, **FIRST_NEXT)

    def test_patch_release_gets_the_review(self):
        """v0.1.1's release PR: the review first, again after changes, then the release test.

        Planted bug caught: "a patch release without it".
        """
        self.assert_next(self.report("patch, no review"), **PATCH_REVIEW_NEXT)
        self.assert_next(self.report("patch, changes requested"), **PATCH_REVIEW_NEXT)
        self.assert_next(self.report("patch, approved"), action="release", item="v0.1",
                         tag=PATCH, pr=60, title=release_title(PATCH), step="release-test",
                         branch=f"troy-mode/release-{PATCH}", merged_by="f07")

    def test_later_version_gets_the_review(self):
        """v0.2.0's release PR #50 without a review: ``security-review``."""
        self.assert_next(self.report("later version, no review"), action="release",
                         item="v0.2", tag=NEXT, pr=50, title=release_title(NEXT),
                         step="security-review", task="CR2", branch=review_branch(NEXT),
                         merged_by=ANY)


class ReviewObjectTests(SecurityStatusCase):
    """Contract C: ``release.review`` at the step, null elsewhere."""

    def root(self, name: str) -> str:
        """The full ID of the case clone's root commit on origin/main."""
        return self.clone(name).git("rev-list", "--max-parents=0", "origin/main").strip()

    def test_first_release_reviews_from_the_root_commit(self):
        """No release commit: the root commit, no tag, run 1, and the two commands."""
        base = self.root("no review")
        self.assertRegex(base, r"^[0-9a-f]{40}$")
        self.assertEqual(self.report("no review")["release"]["review"], {
            "run": 1, "base": base, "base_tag": None, "branch": review_branch(TAG),
            "commands": [commit_tree(base, TAG), switch(TAG)]})

    def test_set_head_first_when_origin_head_is_missing(self):
        """Without ``refs/remotes/origin/HEAD``: ``git remote set-head origin --auto`` first."""
        base = self.root("no review, origin/HEAD missing")
        self.assertEqual(self.report("no review, origin/HEAD missing")["release"]["review"], {
            "run": 1, "base": base, "base_tag": None, "branch": review_branch(TAG),
            "commands": ["git remote set-head origin --auto", commit_tree(base, TAG),
                         switch(TAG)]})

    def test_next_run_number(self):
        """After run 1 requested changes, the review is run 2."""
        for name in ("changes requested, bugs fixed", "changes requested, bug deferred"):
            with self.subTest(case=name):
                found = self.report(name)["release"]["review"]
                self.assertIsInstance(found, dict, self.report(name)["release"])
                self.assertEqual(found["run"], 2)
                self.assertEqual(found["commands"][-1], switch(TAG))

    def test_patch_reviews_from_the_previous_release(self):
        """v0.1.1: the base is v0.1.0's release commit."""
        base = subject_commits(self.clone("patch, no review"))[release_title(TAG)]
        self.assertEqual(self.report("patch, no review")["release"]["review"], {
            "run": 1, "base": base, "base_tag": TAG, "branch": review_branch(PATCH),
            "commands": [commit_tree(base, PATCH), switch(PATCH)]})
        found = self.report("patch, changes requested")["release"]["review"]
        self.assertEqual((found["run"], found["base"], found["base_tag"]), (2, base, TAG))

    def test_base_is_the_newest_release_commit(self):
        """v0.2.0 after v0.1.0 and v0.1.1: the base is ``[docs] Release v0.1.1 (#61)``.

        Planted bug caught: "the review's base taken from the previous version's tag instead
        of the previous release commit of any tag".
        """
        base = subject_commits(self.clone("later version, no review"))[
            release_title(PATCH) + " (#61)"]
        self.assertEqual(self.report("later version, no review")["release"]["review"], {
            "run": 1, "base": base, "base_tag": PATCH, "branch": review_branch(NEXT),
            "commands": [commit_tree(base, NEXT), switch(NEXT)]})

    def test_null_at_every_other_step(self):
        """``version-tests``, ``release-pr``, ``bugs``, ``release-test``, ``troy-test``, and
        ``accept``: ``release.review`` is null."""
        for name in ("version tests next", "release PR next", "changes requested, bug open",
                     "approved", "approved, run failed, bug open", "approved, run passed",
                     "approved, Troy accepted", "patch, approved"):
            with self.subTest(case=name):
                release = self.report(name)["release"]
                self.assertIn("review", release)
                self.assertIsNone(release["review"])


class CommentTests(SecurityStatusCase):
    """Contract C: ``release.security`` and troy-mode's own heading."""

    def test_security_lists_the_reviews_oldest_first(self):
        """Each review comment's run and result, oldest first; none before the first."""
        cases = {
            "no review": [],
            "changes requested, bug deferred": security((1, "changes-requested")),
            "approved": security((1, "approved")),
            "approved after changes": security((1, "changes-requested"), (2, "approved")),
            "approved, Troy accepted": security((1, "approved")),
            "patch, approved": security((1, "approved")),
        }
        for name, expected in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self.report(name)["release"]["security"], expected)

    def test_release_runs_are_unchanged(self):
        """The release test's records do not include the reviews."""
        self.assertEqual(self.report("approved, Troy accepted")["release"]["runs"], [
            {"by": "claude", "run": 1, "result": "passed"},
            {"by": "troy", "run": 1, "result": "accepted"}])
        self.assertEqual(self.report("approved after changes")["release"]["runs"], [])

    def test_heading_is_never_troys_comment(self):
        """A review comment is troy-mode's own: it is not among Troy's comments, and it ends
        a comment of Troy's before it."""
        for name in ("changes requested, bugs fixed", "approved", "Troy's comment, then a review"):
            with self.subTest(case=name):
                entry = self.report(name)["open_prs"][0]
                self.assertEqual(entry["troy_comments"], [])

    def test_heading_on_the_second_line_is_troys(self):
        """A comment whose first line is not the heading is Troy's, and no review."""
        report = self.report("a heading on the second line")
        self.assertEqual(report["release"]["security"], [])
        self.assertEqual(report["open_prs"][0]["troy_comments"],
                         ["Note:\nSecurity review, run 5: approved"])
        self.assert_next(report, **REVIEW_NEXT)
        self.assertEqual(report["release"]["review"]["run"], 1)


if __name__ == "__main__":
    unittest.main()
