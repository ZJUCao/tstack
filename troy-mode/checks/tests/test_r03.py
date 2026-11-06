"""Tests for R03: source PR size (design section 6.3)."""

import unittest

from helpers import (
    CheckTestCase, lines, make_config, parallel, pr_body, pr_sandbox, run_pr,
)

IMPL = "[F04 5/6 impl] Change"


def many_files(count, size=1):
    """Builds ``count`` small source files, each ``size`` lines long."""
    return {f"src/f{i}.py": lines(size) for i in range(count)}


class LineLimitTests(CheckTestCase):
    """Covers the 500-line and 5-file limits."""

    def test_500_lines_pass(self):
        """Exactly 500 changed lines pass."""
        out = run_pr(IMPL, {"src/a.py": lines(500)})
        self.assert_rule(out, "R03", "pass")
        self.assert_clean(out)

    def test_501_lines_without_reason_fails(self):
        """501 changed lines fail without a reason."""
        out = run_pr(IMPL, {"src/a.py": lines(501)})
        self.assert_rule(out, "R03", "fail")
        self.assert_exit(out, 1)

    def test_added_and_deleted_lines_both_count(self):
        """Replacing 300 lines with 300 others is 600 changed lines."""
        out = run_pr(
            IMPL, {"src/a.py": lines(300, "new")}, base_files={"src/a.py": lines(300, "old")}
        )
        self.assert_rule(out, "R03", "fail")

    def test_replacing_250_lines_is_exactly_500(self):
        """250 added plus 250 deleted lines is 500 and passes."""
        out = run_pr(
            IMPL, {"src/a.py": lines(250, "new")}, base_files={"src/a.py": lines(250, "old")}
        )
        self.assert_rule(out, "R03", "pass")

    def test_deleting_501_lines_fails(self):
        """Deleted lines count as changed lines."""
        out = run_pr(IMPL, {"src/a.py": None}, base_files={"src/a.py": lines(501)})
        self.assert_rule(out, "R03", "fail")

    def test_pure_rename_counts_no_lines(self):
        """A rename without edits counts 0 lines in 1 file."""
        out = run_pr(
            "[refactor] Move", base_files={"src/a.py": lines(600, "code")},
            renames=[("src/a.py", "src/b.py")],
        )
        self.assert_rule(out, "R03", "pass")

    def test_configured_line_limit_is_used(self):
        """The limit comes from [limits] source_lines."""
        config = make_config(limits={"source_lines": 100})
        passing = run_pr(IMPL, {"src/a.py": lines(100)}, config=config)
        failing = run_pr(IMPL, {"src/a.py": lines(101)}, config=config)
        self.assert_rule(passing, "R03", "pass")
        self.assert_rule(failing, "R03", "fail")

    def test_configured_file_limit_is_used(self):
        """The limit comes from [limits] source_files."""
        config = make_config(limits={"source_files": 2})
        passing = run_pr(IMPL, many_files(2), config=config)
        failing = run_pr(IMPL, many_files(3), config=config)
        self.assert_rule(passing, "R03", "pass")
        self.assert_rule(failing, "R03", "fail")


class FileLimitTests(CheckTestCase):
    """Covers the file count, exclusions and kinds."""

    def test_five_files_pass(self):
        """Five source files pass."""
        self.assert_rule(run_pr(IMPL, many_files(5)), "R03", "pass")

    def test_sixth_file_fails(self):
        """A sixth source file fails without a reason."""
        self.assert_rule(run_pr(IMPL, many_files(6)), "R03", "fail")

    def test_sixth_file_with_reason_warns(self):
        """Six files with a reason warn, and the PR may merge."""
        out = run_pr(IMPL, many_files(6), body=pr_body("Splits storage.py."))
        self.assert_rule(out, "R03", "warn")
        self.assert_clean(out)

    def test_lock_files_count_neither_lines_nor_files(self):
        """Lock files add no lines and no files to the count."""
        config = make_config(paths={"lock": ["uv.lock"]})
        changes = many_files(5)
        changes["uv.lock"] = lines(900, "lock")
        self.assert_rule(run_pr(IMPL, changes, config=config), "R03", "pass")

    def test_generated_files_count_neither_lines_nor_files(self):
        """Generated files add no lines and no files to the count."""
        config = make_config(paths={"generated": ["gen/**"]})
        changes = {f"gen/g{i}.py": lines(100) for i in range(10)}
        changes["src/a.py"] = lines(1)
        self.assert_rule(run_pr(IMPL, changes, config=config), "R03", "pass")

    def test_lock_pattern_does_not_exempt_other_files(self):
        """A file that does not match the lock pattern still counts."""
        config = make_config(paths={"lock": ["uv.lock"]})
        changes = {"src/a.py": lines(501), "uv.lock": lines(5)}
        self.assert_rule(run_pr(IMPL, changes, config=config), "R03", "fail")

    def test_binary_file_counts_zero_lines(self):
        """A large binary file adds no changed lines."""
        changes = {"src/a.py": lines(1), "src/blob.bin": b"\x00\x01\x02\xff" * 50000}
        self.assert_rule(run_pr(IMPL, changes), "R03", "pass")

    def test_limit_applies_to_mock_fix_and_refactor(self):
        """The mock, fix and refactor kinds are limited like impl."""
        titles = ["[F04 3/6 mock] x", "[B12 B/B fix] x", "[refactor] x"]
        outs = parallel(lambda t: run_pr(t, {"src/a.py": lines(501)}), titles)
        for title, out in zip(titles, outs):
            with self.subTest(title=title):
                self.assert_rule(out, "R03", "fail")

    def test_other_kinds_are_skipped(self):
        """Docs, tests and rules PRs skip R03 however large they are."""
        cases = [
            ("[docs] Big", "docs/big.md"),
            ("[F04 1/6 design] Big", "docs/big.md"),
            ("[F04 4/6 tests] Big", "tests/test_big.py"),
            ("[B12 A/B test] Big", "tests/test_big.py"),
        ]
        outs = parallel(lambda c: run_pr(c[0], {c[1]: lines(2000)}), cases)
        for (title, _), out in zip(cases, outs):
            with self.subTest(title=title):
                self.assert_rule(out, "R03", "skip")
                self.assert_clean(out)

    def test_unparsable_title_skips_r03(self):
        """When the title does not parse, R03 is skipped."""
        out = run_pr("whatever", {"src/a.py": lines(900)})
        self.assert_rule(out, "R03", "skip")


class ReasonTests(CheckTestCase):
    """Covers how the Soft-limit reason section is read."""

    @classmethod
    def setUpClass(cls):
        """Builds one over-limit PR shared by all reason cases."""
        cls.sb = pr_sandbox({"src/big.py": lines(501)})
        cls.addClassCleanup(cls.sb.close)

    def check(self, body):
        """Runs the checker on the shared PR with a description."""
        return self.sb.check_pr(IMPL, body=body)

    def test_real_reasons_warn(self):
        """Any real sentence, with or without comments, counts as a reason."""
        reasons = [
            "Splits storage.py.",
            "<!-- why -->\nSplits storage.py.",
            "None of the code can move yet.",
            "拆分存储模块。",
        ]
        outs = parallel(lambda r: self.check(pr_body(r)), reasons)
        for reason, out in zip(reasons, outs):
            with self.subTest(reason=reason):
                self.assert_rule(out, "R03", "warn")
                self.assert_exit(out, 0)

    def test_empty_or_none_reasons_fail(self):
        """Empty text, None, None. and 无 mean no reason."""
        reasons = [None, "", "   ", "None", "None.", "无",
                   "<!-- explain why -->", "<!-- why -->\nNone"]
        outs = parallel(lambda r: self.check(pr_body(r)), reasons)
        for reason, out in zip(reasons, outs):
            with self.subTest(reason=reason):
                self.assert_rule(out, "R03", "fail")
                self.assert_exit(out, 1)

    def test_missing_section_fails(self):
        """A description without the section gives no reason."""
        out = self.check("## Why\n\nBecause.\n")
        self.assert_rule(out, "R03", "fail")

    def test_no_body_file_fails(self):
        """Without --body-file R03 sees no reason."""
        out = self.sb.check_pr(IMPL)
        self.assert_rule(out, "R03", "fail")


if __name__ == "__main__":
    unittest.main()
