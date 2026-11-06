"""Tests for the config keys F03 adds: ``[tests]``, ``[limits]``, and ``[lang]``."""

import unittest

from code_helpers import run_code
from helpers import EMAIL, CheckTestCase, Sandbox, make_config, parallel
from prefetch import PrefetchedCase, run_pr

TITLE = "[docs] Notes"

VALID = {
    "legacy patterns": '[tests]\nlegacy = ["tests/old/**", "legacy_*.py"]\n',
    "empty legacy": "[tests]\nlegacy = []\n",
    "coverage limits": "[limits]\nline_coverage = 80\nbranch_coverage = 70\n",
    "shape limits": "[limits]\nfunction_lines = 40\nfile_lines = 400\n",
    "python lang": '[lang]\nname = "python"\nsource_roots = ["src"]\n',
    "cpp lang": '[lang]\nname = "cpp"\ninclude_dirs = ["include", "src"]\n',
    "series and environment": '[lang]\nenvironment = "troy-agent-env"\nseries = ["../troy-voice", "."]\n',
    "empty lang lists": "[lang]\nsource_roots = []\ninclude_dirs = []\nseries = []\n",
    "everything": (
        '[tests]\nlegacy = ["old/**"]\n'
        "[limits]\nsource_lines = 500\nsource_files = 5\nline_coverage = 90\n"
        "branch_coverage = 80\nfunction_lines = 50\nfile_lines = 500\n"
        '[lang]\nname = "python"\nsource_roots = ["src"]\ninclude_dirs = ["include"]\n'
        'series = ["."]\nenvironment = "env"\n'
    ),
}
INVALID = {
    "unknown key in tests": "[tests]\nlegacies = []\n",
    "legacy is a string": '[tests]\nlegacy = "tests/**"\n',
    "legacy holds numbers": "[tests]\nlegacy = [1, 2]\n",
    "unknown key in lang": '[lang]\nlanguage = "python"\n',
    "unknown language": '[lang]\nname = "rust"\n',
    "name is a number": "[lang]\nname = 3\n",
    "source_roots is a string": '[lang]\nsource_roots = "src"\n',
    "source_roots holds numbers": "[lang]\nsource_roots = [1]\n",
    "include_dirs is a string": '[lang]\ninclude_dirs = "include"\n',
    "series is a string": '[lang]\nseries = "."\n',
    "series holds numbers": "[lang]\nseries = [1]\n",
    "environment is a number": "[lang]\nenvironment = 5\n",
    "line_coverage zero": "[limits]\nline_coverage = 0\n",
    "line_coverage negative": "[limits]\nline_coverage = -5\n",
    "line_coverage string": '[limits]\nline_coverage = "90"\n',
    "branch_coverage float": "[limits]\nbranch_coverage = 80.5\n",
    "function_lines zero": "[limits]\nfunction_lines = 0\n",
    "function_lines string": '[limits]\nfunction_lines = "50"\n',
    "file_lines negative": "[limits]\nfile_lines = -1\n",
    "file_lines float": "[limits]\nfile_lines = 5.5\n",
    "tests is not a table": 'tests = ["a"]\n',
}


class AcceptedKeysTests(PrefetchedCase):
    """The new keys are valid and no longer exit with code 2."""

    def test_code_accepts_every_valid_config(self):
        """The ``code`` subcommand runs with each valid config."""
        configs = list(VALID.values())
        outs = parallel(lambda text: run_code(TITLE, config=text), configs)
        for label, out in zip(VALID, outs):
            with self.subTest(config=label):
                self.assert_clean(out)

    def test_pr_accepts_every_valid_config(self):
        """The ``pr`` subcommand reads the same config without error."""
        outs = parallel(lambda text: run_pr(TITLE, {"docs/a.md": "a\n"}, config=text), list(VALID.values()))
        for label, out in zip(VALID, outs):
            with self.subTest(config=label):
                self.assert_clean(out)

    def test_new_keys_beside_the_identity_section(self):
        """The new sections combine with the F02 sections."""
        text = make_config(
            limits={"line_coverage": 85},
            paths={"tests": ["t/**"]},
            extra='[lang]\nname = "cpp"\n[tests]\nlegacy = ["old/**"]\n',
        )
        self.assert_clean(run_code(TITLE, config=text))


class CommitConfigTests(CheckTestCase):
    """The commit subcommand reads the same config file."""

    def test_commit_command_accepts_new_keys(self):
        """The ``commit`` subcommand also reads the config and accepts the keys."""
        with Sandbox(config=VALID["everything"]) as sb:
            out = sb.check_commit(message="Fix", email=EMAIL)
        self.assert_exit(out, 0)


class RejectedKeysTests(PrefetchedCase):
    """Wrong types, bad values, and unknown keys still exit with code 2."""

    def test_invalid_configs_exit_two_for_code(self):
        """The ``code`` subcommand stops on each invalid config."""
        outs = parallel(lambda text: run_code(TITLE, config=text), list(INVALID.values()))
        for label, out in zip(INVALID, outs):
            with self.subTest(config=label):
                self.assert_exit(out, 2)

    def test_invalid_configs_exit_two_for_pr(self):
        """The ``pr`` subcommand stops on the same configs."""
        def run(text):
            """Runs the pr command with one config text."""
            return run_pr(TITLE, {"docs/a.md": "a\n"}, config=text)

        for label, out in zip(INVALID, parallel(run, list(INVALID.values()))):
            with self.subTest(config=label):
                self.assert_exit(out, 2)

    def test_old_unknown_keys_still_fail(self):
        """F02's strictness is unchanged for keys F03 did not add."""
        for text in ("[limits]\nsource_lnes = 5\n", "[bogus]\nx = 1\n"):
            with self.subTest(config=text):
                self.assert_exit(run_code(TITLE, config=text), 2)


if __name__ == "__main__":
    unittest.main()
