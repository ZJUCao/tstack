"""Tests for the ``[flow]`` keys F18 adds: ``spot_checks`` and ``spot_check_every``.

F18 design 7.4 and 9 (troy-check, F02), part 2 contract section 1. ``spot_checks`` is a TOML
boolean, false by default; ``spot_check_every`` a whole number of 2 or more, 3 by default.
Any other value is a config error with a fixed message, so troy-check stops with exit code
2. An old ``[flow]`` table with only ``troy_approves_first``, an empty one, and none still
parse. ``config.default.toml`` describes both keys in comments only.

Planted bugs of design 13.2 caught here:

- "the old ``[flow]`` table refused by the new reader":
  ``ParseSpotTests.test_old_tables_still_parse`` and
  ``CommitSpotTests.test_commit_accepts_every_valid_table``.
- "``spot_check_every = 1`` accepted" and "``spot_checks = "true"`` accepted":
  ``ParseSpotTests.test_bad_values_raise_with_their_message`` and
  ``CommitSpotTests.test_commit_reports_each_error``.

``ParseSpotTests.test_unknown_keys_still_raise`` passes on today's reader: any other key of
``[flow]`` is refused as before.
"""

import sys
import tomllib
import unittest
from pathlib import Path

from helpers import EMAIL, CheckTestCase, Sandbox, make_config, parallel

CHECKS = Path(__file__).resolve().parents[1]
SPOT_MESSAGE = "[flow] spot_checks must be true or false"
EVERY_MESSAGE = "[flow] spot_check_every must be a whole number of 2 or more"

VALID = {
    "on": ("[flow]\nspot_checks = true\n", True, 3, 3),
    "off": ("[flow]\nspot_checks = false\n", False, 3, 3),
    "every two": ("[flow]\nspot_check_every = 2\n", False, 2, 3),
    "every ten": ("[flow]\nspot_checks = true\nspot_check_every = 10\n", True, 10, 3),
    "all three keys": ("[flow]\ntroy_approves_first = 5\nspot_checks = true\n"
                       "spot_check_every = 4\n", True, 4, 5),
    "old table": ("[flow]\ntroy_approves_first = 3\n", False, 3, 3),
    "old table, count 0": ("[flow]\ntroy_approves_first = 0\n", False, 3, 0),
    "empty table": ("[flow]\n", False, 3, 3),
    "no table": ("", False, 3, 3),
}
BAD_SPOT = {
    "text true": '[flow]\nspot_checks = "true"\n',
    "number 1": "[flow]\nspot_checks = 1\n",
    "number 0": "[flow]\nspot_checks = 0\n",
    "text false": '[flow]\nspot_checks = "false"\n',
}
BAD_EVERY = {
    "one": "[flow]\nspot_check_every = 1\n",
    "zero": "[flow]\nspot_check_every = 0\n",
    "negative": "[flow]\nspot_check_every = -2\n",
    "boolean": "[flow]\nspot_check_every = true\n",
    "decimal": "[flow]\nspot_check_every = 2.5\n",
    "whole decimal": "[flow]\nspot_check_every = 3.0\n",
    "text": '[flow]\nspot_check_every = "3"\n',
}
UNKNOWN = {"spot_check": "[flow]\nspot_check = true\n",
           "every_spot_check": "[flow]\nevery_spot_check = 3\n"}


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


class ParseSpotTests(unittest.TestCase):
    """``troycheck.config.parse_config`` reads ``spot_checks`` and ``spot_check_every``."""

    @classmethod
    def setUpClass(cls):
        """Imports the config module once."""
        cls.module = import_config_module()

    def test_default_constant_is_3(self):
        """``SPOT_CHECK_EVERY_DEFAULT`` is the integer 3."""
        self.assertEqual(getattr(self.module, "SPOT_CHECK_EVERY_DEFAULT", "missing"), 3)
        self.assertIs(type(self.module.SPOT_CHECK_EVERY_DEFAULT), int)

    def test_values_are_read(self):
        """Each valid table gives its ``spot_checks``, ``spot_check_every``, and count."""
        for label, (text, spot, every, count) in VALID.items():
            with self.subTest(config=label):
                try:
                    config = self.module.parse_config(config_of(text))
                except self.module.ConfigError as exc:
                    self.fail(f"a valid table refused: {exc}")
                found =(getattr(config, "spot_checks", "missing"),
                         getattr(config, "spot_check_every", "missing"),
                         config.troy_approves_first)
                self.assertEqual(found, (spot, every, count))
                self.assertIs(type(config.spot_checks), bool)
                self.assertIs(type(config.spot_check_every), int)

    def test_old_tables_still_parse(self):
        """Planted bug "the old ``[flow]`` table refused": only ``troy_approves_first``, an
        empty ``[flow]``, no ``[flow]``, and no file: spot checks off, every 3."""
        for text in (config_of(VALID["old table"][0]), config_of("[flow]\n"), config_of(""),
                     None):
            with self.subTest(text=text):
                config = self.module.parse_config(text)
                self.assertEqual((getattr(config, "spot_checks", "missing"),
                                  getattr(config, "spot_check_every", "missing")), (False, 3))

    def test_bad_values_raise_with_their_message(self):
        """Planted bugs "``spot_check_every = 1`` accepted" and "``spot_checks = "true"``
        accepted": each bad value raises ``ConfigError`` with the contract's message."""
        for table, message in ((BAD_SPOT, SPOT_MESSAGE), (BAD_EVERY, EVERY_MESSAGE)):
            for label, text in table.items():
                with self.subTest(config=label):
                    with self.assertRaises(self.module.ConfigError) as caught:
                        self.module.parse_config(config_of(text))
                    self.assertEqual(str(caught.exception), message)

    def test_unknown_keys_still_raise(self):
        """Any other key in ``[flow]``: ``unknown key '<key>' in [flow]``."""
        for key, text in UNKNOWN.items():
            with self.subTest(key=key):
                with self.assertRaises(self.module.ConfigError) as caught:
                    self.module.parse_config(config_of(text))
                self.assertEqual(str(caught.exception), f"unknown key '{key}' in [flow]")


class CommitSpotTests(CheckTestCase):
    """``commit`` reads the working tree's config with the same rules (contract 1)."""

    def test_commit_accepts_every_valid_table(self):
        """Planted bug "the old ``[flow]`` table refused": each valid table exits 0."""
        texts = [text for text, *_ in VALID.values()]
        for label, out in zip(VALID, parallel(commit_outcome, texts)):
            with self.subTest(config=label):
                self.assert_exit(out, 0)

    def test_commit_reports_each_error(self):
        """Planted bugs "every 1 accepted" and "``"true"`` accepted": exit 2, and the message
        on standard error as every config error is reported."""
        cases = {**{label: (text, SPOT_MESSAGE) for label, text in BAD_SPOT.items()},
                 **{label: (text, EVERY_MESSAGE) for label, text in BAD_EVERY.items()}}
        outs = parallel(commit_outcome, [text for text, _ in cases.values()])
        for (label, (_, message)), out in zip(cases.items(), outs):
            with self.subTest(config=label):
                self.assert_exit(out, 2)
                self.assertIn(f"troy-check: error: {message}", out.stderr)


class DefaultConfigSpotTests(unittest.TestCase):
    """``config.default.toml`` describes both keys in comments (contract 1 and 8)."""

    @classmethod
    def setUpClass(cls):
        """Reads the default config and the config module."""
        cls.text = (CHECKS / "config.default.toml").read_bytes().decode("utf-8")
        cls.lines = [line.strip() for line in cls.text.replace("\r\n", "\n").split("\n")]
        cls.module = import_config_module()

    def test_keys_are_commented_after_the_count(self):
        """``# spot_checks = false`` and ``# spot_check_every = 3`` come after
        ``# troy_approves_first = 3``, with comment lines that explain them in between."""
        wanted = ("# troy_approves_first = 3", "# spot_checks = false", "# spot_check_every = 3")
        self.assertEqual([line for line in wanted if line not in self.lines], [])
        count =self.lines.index("# troy_approves_first = 3")
        spot = self.lines.index("# spot_checks = false")
        every = self.lines.index("# spot_check_every = 3")
        self.assertLess(count, spot)
        self.assertLess(count, every)
        between = [line for line in self.lines[count + 1:max(spot, every)]
                   if line.startswith("#") and "=" not in line]
        self.assertTrue(any("spot" in line.lower() for line in between), between)

    def test_still_parses_with_everything_commented_out(self):
        """The file parses, sets no flow key, and gives the defaults."""
        data = tomllib.loads(self.text)
        self.assertEqual(data.get("flow", {}), {})
        config = self.module.parse_config(self.text)
        self.assertEqual((config.troy_approves_first, getattr(config, "spot_checks", "missing"),
                          getattr(config, "spot_check_every", "missing")), (3, False, 3))


if __name__ == "__main__":
    unittest.main()
