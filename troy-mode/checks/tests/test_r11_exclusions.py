"""Tests for R11 exclusion comments: each one needs a reason on its line (D18)."""

import unittest

from code_helpers import run_code
from helpers import parallel
from prefetch import PrefetchedCase
from reports import cobertura, hits
from test_r11 import IMPL, code_text

PY = "src/mod.py"
CPP = "src/mod.cpp"
EXCLUDED_LINE = 5
NEEDS_REASON = {
    "pragma": (PY, "x = 1  # pragma: no cover"),
    "pragma upper case": (PY, "x = 1  # PRAGMA: NO COVER"),
    "pragma mixed case": (PY, "x = 1  # Pragma: No Cover"),
    "gcovr line": (CPP, "int x = 1;  // GCOVR_EXCL_LINE"),
    "gcovr start": (CPP, "// GCOVR_EXCL_START"),
    "lcov line": (CPP, "int x = 1;  // LCOV_EXCL_LINE"),
    "lcov start": (CPP, "// LCOV_EXCL_START"),
}
NO_REASON_NEEDED = {
    "gcovr stop": (CPP, "// GCOVR_EXCL_STOP"),
    "lcov stop": (CPP, "// LCOV_EXCL_STOP"),
}


def with_marker(path, marker, reason=None, base=False):
    """Runs R11 on a PR whose file holds one exclusion marker on line 5.

    Every other line is covered, and the marker line is not in the report,
    as a coverage tool leaves out excluded lines.

    Args:
        path: Path of the source file.
        marker: The full text of line 5, including the marker.
        reason: Text appended after the marker, or None.
        base: Whether the marker line already exists in the base commit and
            the PR changes line 8 instead.

    Returns:
        The outcome of the run.
    """
    text = marker if reason is None else f"{marker}  reason: {reason}"
    spec = hits([n for n in range(1, 11) if n != EXCLUDED_LINE])
    coverage = [cobertura({path: spec})]
    if base:
        before = code_text(replace={EXCLUDED_LINE: text})
        after = code_text(replace={EXCLUDED_LINE: text, 8: "v8 = 88"})
        return run_code(IMPL, {path: after}, base_files={path: before}, coverage=coverage)
    return run_code(IMPL, {path: code_text(replace={EXCLUDED_LINE: text})}, coverage=coverage)


class ExclusionTests(PrefetchedCase):
    """Exclusion comments on changed lines."""

    def test_marker_without_reason_fails(self):
        """Each marker without ``reason:`` fails R11."""
        cases = list(NEEDS_REASON.items())
        outs = parallel(lambda item: with_marker(*item[1]), cases)
        for (label, _), out in zip(cases, outs):
            with self.subTest(marker=label):
                self.assert_rule(out, "R11", "fail")
                self.assert_exit(out, 1)

    def test_failure_names_the_path_and_line(self):
        """The failure points at the file and the line of the marker."""
        out = with_marker(PY, "x = 1  # pragma: no cover")
        located = [(d["path"], d["line"]) for d in out.details("R11")]
        self.assertIn((PY, EXCLUDED_LINE), located, out.describe())

    def test_marker_with_reason_passes(self):
        """Each marker with ``reason:`` on the same line passes."""
        cases = list(NEEDS_REASON.items())
        outs = parallel(lambda item: with_marker(*item[1], reason="a full disk cannot be tested"), cases)
        for (label, _), out in zip(cases, outs):
            with self.subTest(marker=label):
                self.assert_rule(out, "R11", "pass")
                self.assert_clean(out)

    def test_stop_markers_need_no_reason(self):
        """STOP markers close a region and carry no reason."""
        cases = list(NO_REASON_NEEDED.items())
        outs = parallel(lambda item: with_marker(*item[1]), cases)
        for (label, _), out in zip(cases, outs):
            with self.subTest(marker=label):
                self.assert_rule(out, "R11", "pass")

    def test_reason_must_be_on_the_same_line(self):
        """A reason on the next line does not count."""
        text = code_text(replace={EXCLUDED_LINE: "x = 1  # pragma: no cover", 6: "# reason: later"})
        spec = hits([n for n in range(1, 11) if n != EXCLUDED_LINE])
        out = run_code(IMPL, {PY: text}, coverage=[cobertura({PY: spec})])
        self.assert_rule(out, "R11", "fail")

    def test_unchanged_marker_without_reason_is_ignored(self):
        """Only exclusions on changed lines are checked."""
        out = with_marker(PY, "x = 1  # pragma: no cover", base=True)
        self.assert_rule(out, "R11", "pass")

    def test_marker_in_a_changed_line_of_a_modified_file_fails(self):
        """A marker added to an existing file by the PR is a changed line."""
        before = code_text()
        after = code_text(replace={EXCLUDED_LINE: "x = 1  # pragma: no cover"})
        spec = hits([n for n in range(1, 11) if n != EXCLUDED_LINE])
        out = run_code(IMPL, {PY: after}, base_files={PY: before}, coverage=[cobertura({PY: spec})])
        self.assert_rule(out, "R11", "fail")

    def test_two_markers_are_both_reported(self):
        """Every marker without a reason is listed by line."""
        replace = {3: "x = 1  # pragma: no cover", 7: "y = 2  # pragma: no cover"}
        spec = hits([1, 2, 4, 5, 6, 8, 9, 10])
        out = run_code(IMPL, {PY: code_text(replace=replace)}, coverage=[cobertura({PY: spec})])
        self.assert_rule(out, "R11", "fail")
        lines = {d["line"] for d in out.details("R11")}
        self.assertTrue({3, 7} <= lines, out.describe())

    def test_marker_with_reason_does_not_hide_other_uncovered_lines(self):
        """A reasoned exclusion only excuses its own line."""
        text = code_text(replace={EXCLUDED_LINE: "x = 1  # pragma: no cover  reason: ok"})
        spec = hits([1, 2, 3], [4, 6, 7, 8, 9, 10])
        out = run_code(IMPL, {PY: text}, coverage=[cobertura({PY: spec})])
        self.assert_rule(out, "R11", "fail")


if __name__ == "__main__":
    unittest.main()
