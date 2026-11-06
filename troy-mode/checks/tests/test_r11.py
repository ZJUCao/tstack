"""Tests for R11: coverage of changed lines in impl and fix PRs (design 5)."""

import unittest
from pathlib import Path

from code_helpers import run_code
from helpers import make_config, parallel
from prefetch import PrefetchedCase
from reports import branch, cobertura, hits

IMPL = "[F04 5/6 impl] Export history as CSV"
FIX = "[B12 B/B fix] Crash on empty history"
SRC = "src/mod.py"
ALL = range(1, 11)


def code_text(count=10, replace=None):
    """Builds a source file of numbered assignment lines.

    Args:
        count: Number of lines.
        replace: Line number mapped to replacement text.

    Returns:
        The file text.
    """
    replace = replace or {}
    return "".join(f"{replace.get(i, f'v{i} = {i}')}\n" for i in range(1, count + 1))


def new_file(report, title=IMPL, path=SRC, text=None, **kwargs):
    """Runs R11 on a PR that adds one 10-line source file.

    Args:
        report: Cobertura text, or None for no coverage option.
        title: PR title.
        path: Path of the new file.
        text: File text. Defaults to ten numbered lines.
        **kwargs: Passed on to ``run_code``.

    Returns:
        The outcome of the run.
    """
    kwargs.setdefault("coverage", [] if report is None else [report])
    return run_code(title, {path: text or code_text()}, **kwargs)


def lines_report(covered, path=SRC, extra=None):
    """Builds a report where the first ``covered`` lines of 1..10 are hit.

    Args:
        covered: Number of covered lines out of ten.
        path: Report filename.
        extra: Line specs that replace or add entries.

    Returns:
        Cobertura text.
    """
    spec = hits(range(1, covered + 1), range(covered + 1, 11))
    spec.update(extra or {})
    return cobertura({path: spec})


class LineCoverageTests(PrefetchedCase):
    """Covered executable changed lines against the 90 percent limit."""

    def test_full_coverage_passes(self):
        """Ten of ten changed lines covered passes, and the run is clean."""
        out = new_file(lines_report(10))
        self.assert_rule(out, "R11", "pass")
        self.assert_clean(out)

    def test_exactly_ninety_percent_passes(self):
        """The limit is inclusive: 9 of 10 passes."""
        self.assert_rule(new_file(lines_report(9)), "R11", "pass")

    def test_below_ninety_percent_fails(self):
        """8 of 10 fails R11 with exit code 1."""
        out = new_file(lines_report(8))
        self.assert_rule(out, "R11", "fail")
        self.assert_exit(out, 1)

    def test_no_line_covered_fails(self):
        """A new file that never runs fails."""
        self.assert_rule(new_file(lines_report(0)), "R11", "fail")

    def test_hits_above_zero_count_as_covered(self):
        """Any positive hit count is covered, however large."""
        spec = {i: (500,) for i in ALL}
        self.assert_rule(new_file(cobertura({SRC: spec})), "R11", "pass")

    def test_only_listed_lines_are_executable(self):
        """Lines the report does not list are not executable: 4 of 4 passes."""
        spec = hits([1, 2, 3, 4])
        self.assert_rule(new_file(cobertura({SRC: spec})), "R11", "pass")

    def test_only_changed_lines_count(self):
        """Uncovered lines that the PR did not touch do not matter."""
        base = {SRC: code_text()}
        changes = {SRC: code_text(replace={3: "v3 = 33", 4: "v4 = 44"})}
        spec = hits([3, 4], [1, 2, 5, 6, 7, 8, 9, 10])
        out = run_code(IMPL, changes, base_files=base, coverage=[cobertura({SRC: spec})])
        self.assert_rule(out, "R11", "pass")

    def test_modified_lines_must_be_covered(self):
        """Modified lines count as changed: 1 of 2 covered fails."""
        base = {SRC: code_text()}
        changes = {SRC: code_text(replace={3: "v3 = 33", 4: "v4 = 44"})}
        spec = hits(ALL, [])
        spec[4] = (0,)
        out = run_code(IMPL, changes, base_files=base, coverage=[cobertura({SRC: spec})])
        self.assert_rule(out, "R11", "fail")

    def test_appended_lines_count(self):
        """Lines added to an existing file are changed lines."""
        base = {SRC: code_text(10)}
        changes = {SRC: code_text(15)}
        spec = hits(range(1, 11), range(11, 16))
        out = run_code(IMPL, changes, base_files=base, coverage=[cobertura({SRC: spec})])
        self.assert_rule(out, "R11", "fail")

    def test_deleted_lines_are_not_changed_lines(self):
        """A PR that only deletes a line has no changed line and passes."""
        base = {SRC: code_text(10)}
        changes = {SRC: code_text(10).replace("v5 = 5\n", "")}
        spec = hits([], range(1, 10))
        out = run_code(IMPL, changes, base_files=base, coverage=[cobertura({SRC: spec})])
        self.assert_rule(out, "R11", "pass")

    def test_no_executable_changed_lines_passes(self):
        """Changed lines that the report does not list leave nothing to cover."""
        out = new_file(cobertura({SRC: hits([], [50, 51])}))
        self.assert_rule(out, "R11", "pass")
        self.assert_rule(new_file(cobertura({SRC: {}})), "R11", "pass")

    def test_limits_come_from_config(self):
        """``[limits] line_coverage`` replaces the 90 percent default."""
        strict = make_config(limits={"line_coverage": 100})
        loose = make_config(limits={"line_coverage": 50})
        outs = parallel(
            lambda c: new_file(lines_report(9 if c is strict else 5), config=c), [strict, loose]
        )
        self.assertEqual([o.status("R11") for o in outs], ["fail", "pass"])

    def test_line_limit_boundary_with_custom_value(self):
        """With ``line_coverage = 50``, 4 of 10 fails and 5 of 10 passes."""
        config = make_config(limits={"line_coverage": 50})
        outs = parallel(lambda n: new_file(lines_report(n), config=config), [4, 5])
        self.assertEqual([o.status("R11") for o in outs], ["fail", "pass"])


class BranchCoverageTests(PrefetchedCase):
    """Branch outcomes on changed lines against the 80 percent limit."""

    def with_branches(self, *conditions, config=None):
        """Runs R11 with all lines hit and branch data on the first lines.

        Args:
            *conditions: ``(covered, total)`` pairs for lines 1, 2, and so on.
            config: Config text, or None for the default.

        Returns:
            R11's result string.
        """
        extra = {i + 1: (1, branch(c, t)) for i, (c, t) in enumerate(conditions)}
        kwargs = {} if config is None else {"config": config}
        return new_file(lines_report(10, extra=extra), **kwargs).status("R11")

    def test_all_outcomes_taken_passes(self):
        """Two of two outcomes passes."""
        self.assertEqual(self.with_branches((2, 2)), "pass")

    def test_half_the_outcomes_fails(self):
        """One of two outcomes is 50 percent and fails."""
        self.assertEqual(self.with_branches((1, 2)), "fail")

    def test_exactly_eighty_percent_passes(self):
        """Four of five outcomes is exactly 80 percent and passes."""
        self.assertEqual(self.with_branches((4, 5)), "pass")

    def test_seventy_five_percent_fails(self):
        """Three of four outcomes is below the limit."""
        self.assertEqual(self.with_branches((3, 4)), "fail")

    def test_outcomes_add_up_over_lines(self):
        """The ratio is over all outcomes: 7 of 8 passes although one line is at 50 percent."""
        self.assertEqual(self.with_branches((2, 2), (2, 2), (2, 2), (1, 2)), "pass")

    def test_outcomes_add_up_and_can_fail(self):
        """The ratio over lines can fail: 3 of 4 over two lines."""
        self.assertEqual(self.with_branches((2, 2), (1, 2)), "fail")

    def test_unchanged_branch_lines_are_ignored(self):
        """Branches on lines the PR did not touch do not count."""
        base = {SRC: code_text()}
        changes = {SRC: code_text(replace={3: "v3 = 33"})}
        spec = hits(ALL)
        spec[8] = (1, branch(0, 2))
        out = run_code(IMPL, changes, base_files=base, coverage=[cobertura({SRC: spec})])
        self.assert_rule(out, "R11", "pass")

    def test_branch_failure_is_independent_of_line_coverage(self):
        """Full line coverage does not save poor branch coverage."""
        self.assertEqual(self.with_branches((0, 2), (0, 2)), "fail")

    def test_good_branches_do_not_save_poor_line_coverage(self):
        """Full branch coverage does not save poor line coverage."""
        extra = {1: (1, branch(2, 2))}
        out = new_file(lines_report(5, extra=extra))
        self.assert_rule(out, "R11", "fail")

    def test_limit_comes_from_config(self):
        """``[limits] branch_coverage`` replaces the 80 percent default."""
        strict = make_config(limits={"branch_coverage": 100})
        loose = make_config(limits={"branch_coverage": 50})
        results = parallel(lambda c: self.with_branches((1, 2), config=c), [strict, loose])
        self.assertEqual(results, ["fail", "pass"])

    def test_no_branches_passes_the_branch_part(self):
        """Without branch data on changed lines the branch part passes."""
        self.assertEqual(self.with_branches(), "pass")


class ApplicabilityTests(PrefetchedCase):
    """R11 runs for impl and fix PRs with --coverage only."""

    def test_fix_pr_is_judged(self):
        """A fix PR with uncovered lines fails; with covered lines it passes."""
        outs = parallel(lambda n: new_file(lines_report(n), title=FIX), [0, 10])
        self.assertEqual([o.status("R11") for o in outs], ["fail", "pass"])

    def test_other_kinds_skip(self):
        """Every other kind skips R11, even with poor coverage."""
        titles = [
            "[F04 1/6 design] D", "[F04 2/6 test-plan] P", "[F04 3/6 mock] M",
            "[F04 4/6 tests] T", "[F04 6/6 accept] A", "[B12 A/B test] T",
            "[F04 test-fix] T", "[docs] D", "[rules] R", "[refactor] R",
        ]
        outs = parallel(lambda t: new_file(lines_report(0), title=t), titles)
        for title, out in zip(titles, outs):
            with self.subTest(title=title):
                self.assert_rule(out, "R11", "skip")

    def test_without_coverage_skips(self):
        """Without --coverage, R11 skips even for an impl PR."""
        out = new_file(None)
        self.assert_rule(out, "R11", "skip")
        self.assert_clean(out)

    def test_missing_coverage_file_fails(self):
        """A --coverage path that does not exist fails R11 with exit code 1."""
        out = new_file(None, coverage=[Path("none.xml")])
        self.assert_rule(out, "R11", "fail")
        self.assert_exit(out, 1)


class ReportPathTests(PrefetchedCase):
    """Report filenames are resolved against the repository."""

    def test_repo_relative_filename(self):
        """A filename that is a repo path is found without any source."""
        self.assert_rule(new_file(lines_report(10)), "R11", "pass")

    def test_filename_relative_to_a_source_root(self):
        """A filename under an absolute ``<source>`` root maps to the repo path."""
        report = cobertura({"mod.py": hits([], ALL)}, sources=["{ROOT}/src"])
        out = new_file(report)
        self.assert_rule(out, "R11", "fail")

    def test_covered_filename_relative_to_a_source_root(self):
        """The same mapping passes when the lines are covered."""
        report = cobertura({"mod.py": hits(ALL)}, sources=["{ROOT}/src"])
        out = new_file(report)
        self.assert_rule(out, "R11", "pass")
        self.assert_clean(out)

    def test_relative_source_root(self):
        """A ``<source>`` root given relative to the repository works."""
        report = cobertura({"mod.py": hits([], ALL)}, sources=["src"])
        self.assert_rule(new_file(report), "R11", "fail")

    def test_first_source_root_may_not_hold_the_file(self):
        """Source roots without the file are skipped."""
        report = cobertura({"mod.py": hits(ALL)}, sources=["other", "src"])
        out = new_file(report)
        self.assert_rule(out, "R11", "pass")

    def test_unmatched_file_is_a_warning_not_a_failure(self):
        """A changed source file that no report lists gives a warning."""
        out = new_file(cobertura({"src/elsewhere.py": hits(ALL)}))
        self.assert_rule(out, "R11", "warn")
        self.assert_exit(out, 0)
        self.assertTrue(out.report["ok"], out.describe())

    def test_unmatched_file_is_named(self):
        """The warning names the unlisted file."""
        out = new_file(cobertura({"src/elsewhere.py": hits(ALL)}))
        self.assertIn(SRC, out.paths("R11"), out.describe())

    def test_failure_wins_over_warning(self):
        """A covered-too-little file fails even when another file is unlisted."""
        changes = {"src/a.py": code_text(), "src/b.py": code_text()}
        out = run_code(IMPL, changes, coverage=[cobertura({"src/a.py": hits([], ALL)})])
        self.assert_rule(out, "R11", "fail")

    def test_unlisted_file_beside_a_covered_one_warns(self):
        """One covered file and one unlisted file give a warning."""
        changes = {"src/a.py": code_text(), "src/b.py": code_text()}
        out = run_code(IMPL, changes, coverage=[cobertura({"src/a.py": hits(ALL)})])
        self.assert_rule(out, "R11", "warn")

    def test_changed_test_files_need_no_coverage(self):
        """Only source files are expected in the report."""
        changes = {SRC: code_text(), "tests/test_mod.py": code_text(), "docs/a.md": "a\n"}
        out = run_code(IMPL, changes, coverage=[cobertura({SRC: hits(ALL)})])
        self.assert_rule(out, "R11", "pass")

    def test_reports_are_combined(self):
        """Files may be spread over several --coverage reports."""
        changes = {"src/a.py": code_text(), "src/b.py": code_text()}
        good = cobertura({"src/a.py": hits(ALL)})
        other = cobertura({"src/b.py": hits(ALL)})
        bad = cobertura({"src/b.py": hits([], ALL)})
        outs = parallel(lambda r: run_code(IMPL, changes, coverage=[good, r]), [other, bad])
        self.assertEqual([o.status("R11") for o in outs], ["pass", "fail"])


if __name__ == "__main__":
    unittest.main()
