"""Tests for the config table F05 adds: ``[hooks] log_days`` (F05 design 10 and 13.1, D219).

``log_days`` is a whole number of 1 or more, 30 when the key, the table, or
the file is missing, and ``[hooks]`` has no other key. A bad value is a config
error, so troy-check stops with exit code 2. ``config.default.toml`` sets
``log_days = 30``. The SessionStart side is in
``troy-mode/hooks/tests/test_log_days.py``.

Planted bug caught here (design 13.2): a ``log_days`` of 0 accepted
(ParseLogDaysTests.test_bad_values_raise and
CommitLogDaysTests.test_commit_refuses_every_invalid_table).
"""

import sys
import tomllib
import unittest
from pathlib import Path

from helpers import EMAIL, CheckTestCase, Sandbox, make_config, parallel

CHECKS = Path(__file__).resolve().parents[1]

VALID = {
    "empty hooks table": ("[hooks]\n", 30),
    "one day": ("[hooks]\nlog_days = 1\n", 1),
    "seven days": ("[hooks]\nlog_days = 7\n", 7),
    "thirty days": ("[hooks]\nlog_days = 30\n", 30),
    "a year": ("[hooks]\nlog_days = 365\n", 365),
}
BAD_VALUES = {
    "zero": "[hooks]\nlog_days = 0\n",
    "below zero": "[hooks]\nlog_days = -1\n",
    "true": "[hooks]\nlog_days = true\n",
    "false": "[hooks]\nlog_days = false\n",
    "a decimal": "[hooks]\nlog_days = 1.5\n",
    "a whole decimal": "[hooks]\nlog_days = 30.0\n",
    "a string": '[hooks]\nlog_days = "30"\n',
}
INVALID = {
    **BAD_VALUES,
    "unknown key in hooks": "[hooks]\nlog_days = 30\nkeep_records = 5\n",
    "unknown key alone": "[hooks]\nkeep = 5\n",
    "hooks that is not a table": "hooks = 30\n",
}


def config_of(text: str) -> str:
    """A full config with the identity section and the given tables."""
    return make_config(extra=text)


def commit_outcome(text: str):
    """Runs ``troy_check.py commit`` in a repository whose config holds the text."""
    with Sandbox(config=config_of(text)) as sandbox:
        return sandbox.check_commit(message="Fix the docs", email=EMAIL)


def import_config_module():
    """Imports ``troycheck.config`` from this plugin's ``troy-mode/checks``."""
    sys.path.insert(0, str(CHECKS))
    try:
        import troycheck.config as module  # pylint: disable=import-outside-toplevel
    finally:
        sys.path.remove(str(CHECKS))
    return module


class ParseLogDaysTests(unittest.TestCase):
    """``troycheck.config.parse_config`` returns ``hooks_log_days``."""

    @classmethod
    def setUpClass(cls):
        """Imports the config module once."""
        cls.module = import_config_module()

    def test_default_constant_is_30(self):
        """``HOOKS_LOG_DAYS_DEFAULT`` is the integer 30."""
        self.assertEqual(self.module.HOOKS_LOG_DAYS_DEFAULT, 30)
        self.assertIs(type(self.module.HOOKS_LOG_DAYS_DEFAULT), int)

    def test_missing_file_or_table_gives_30(self):
        """No file, a config without ``[hooks]``, and an empty ``[hooks]`` all give 30."""
        for label, text in (("no file", None), ("no hooks table", config_of("")),
                            ("empty hooks table", config_of("[hooks]\n"))):
            with self.subTest(config=label):
                config = self.module.parse_config(text)
                self.assertEqual(config.hooks_log_days, 30)
                self.assertIs(type(config.hooks_log_days), int)

    def test_whole_numbers_are_read_as_given(self):
        """1, 7, 30, and 365 are read back as those integers."""
        for label, (text, days) in VALID.items():
            with self.subTest(config=label):
                config = self.module.parse_config(config_of(text))
                self.assertEqual(config.hooks_log_days, days)
                self.assertIs(type(config.hooks_log_days), int)

    def test_bad_values_raise(self):
        """0, -1, true, false, a decimal, and a string raise ``ConfigError`` naming log_days.

        Planted bug caught: a ``log_days`` of 0 accepted.
        """
        for label, text in BAD_VALUES.items():
            with self.subTest(config=label):
                with self.assertRaises(self.module.ConfigError) as caught:
                    self.module.parse_config(config_of(text))
                self.assertIn("log_days", str(caught.exception))

    def test_other_bad_hooks_tables_raise(self):
        """An unknown key in ``[hooks]`` and a ``hooks`` that is not a table raise."""
        for label in ("unknown key in hooks", "unknown key alone", "hooks that is not a table"):
            with self.subTest(config=label):
                with self.assertRaises(self.module.ConfigError):
                    self.module.parse_config(config_of(INVALID[label]))

    def test_other_tables_are_still_read_beside_hooks(self):
        """A ``[hooks]`` table leaves the F07 tables at their defaults."""
        config = self.module.parse_config(config_of("[hooks]\nlog_days = 7\n"))
        self.assertEqual(config.hooks_log_days, 7)
        self.assertEqual(config.troy_approves_first, 3)
        self.assertEqual(config.roles, {})


class DefaultConfigTests(unittest.TestCase):
    """``config.default.toml`` sets ``[hooks] log_days = 30`` (design 13.1)."""

    @classmethod
    def setUpClass(cls):
        """Reads the default config and the config module."""
        cls.text = (CHECKS / "config.default.toml").read_bytes().decode("utf-8")
        cls.module = import_config_module()

    def test_default_config_sets_log_days_to_30(self):
        """The file parses as TOML and its uncommented ``[hooks] log_days`` is the integer 30."""
        data = tomllib.loads(self.text)
        self.assertIn("hooks", data)
        self.assertEqual(data["hooks"].get("log_days"), 30)
        self.assertIs(type(data["hooks"]["log_days"]), int)

    def test_default_config_parses_to_30(self):
        """``parse_config`` of the default config gives ``hooks_log_days`` 30."""
        self.assertEqual(self.module.parse_config(self.text).hooks_log_days, 30)


class CommitLogDaysTests(CheckTestCase):
    """``troy_check.py commit`` reads ``[hooks]`` with the same rules (exit code 2 on errors)."""

    def test_commit_accepts_every_valid_value(self):
        """Each valid ``[hooks]`` table passes ``commit`` with exit code 0."""
        texts = [text for text, _ in VALID.values()]
        for label, out in zip(VALID, parallel(commit_outcome, texts)):
            with self.subTest(config=label):
                self.assert_exit(out, 0)

    def test_commit_refuses_every_invalid_table(self):
        """Each invalid ``[hooks]`` table stops ``commit`` with exit code 2.

        Planted bug caught: a ``log_days`` of 0 accepted.
        """
        for label, out in zip(INVALID, parallel(commit_outcome, list(INVALID.values()))):
            with self.subTest(config=label):
                self.assert_exit(out, 2)


if __name__ == "__main__":
    unittest.main()
