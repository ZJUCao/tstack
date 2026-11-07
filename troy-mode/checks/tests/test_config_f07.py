"""Tests for the config tables F07 adds: ``[roles]`` and ``[flow]`` (F07 design 3.2, 12)."""

import sys
import tomllib
import unittest
from pathlib import Path

from code_helpers import run_code
from helpers import EMAIL, CheckTestCase, Sandbox, make_config, parallel
from prefetch import PrefetchedCase, run_pr

CHECKS = Path(__file__).resolve().parents[1]
TITLE = "[docs] Notes"
ROLE_NAMES = ("architect", "interface-designer", "test-manager", "developer", "test-engineer",
              "code-reviewer")
EFFORTS = ("low", "medium", "high", "xhigh", "max", "high")

VALID = {
    "developer model and effort": '[roles.developer]\nmodel = "opus"\neffort = "high"\n',
    "reviewer effort only": '[roles.code-reviewer]\neffort = "medium"\n',
    "empty roles table": "[roles]\n",
    "every role, every effort": "".join(
        f'[roles.{role}]\nmodel = "sonnet"\neffort = "{effort}"\n'
        for role, effort in zip(ROLE_NAMES, EFFORTS)),
    "count of three": "[flow]\ntroy_approves_first = 3\n",
    "count of zero": "[flow]\ntroy_approves_first = 0\n",
    "both tables": ('[roles.architect]\nmodel = "opus"\n\n'
                    "[flow]\ntroy_approves_first = 5\n"),
}
INVALID = {
    "unknown role": '[roles.manager]\nmodel = "opus"\n',
    "the Product Manager is not a role here": '[roles.product-manager]\nmodel = "opus"\n',
    "key directly under roles": '[roles]\nmodel = "opus"\n',
    "role that is not a table": '[roles]\ndeveloper = "opus"\n',
    "unknown key of a role": "[roles.developer]\ntemperature = 1\n",
    "unknown key of flow": "[flow]\nother = 1\n",
    "effort extreme": '[roles.developer]\neffort = "extreme"\n',
    "effort capitalized": '[roles.developer]\neffort = "High"\n',
    "effort a number": "[roles.developer]\neffort = 3\n",
    "model a number": "[roles.developer]\nmodel = 4\n",
    "model empty": '[roles.developer]\nmodel = ""\n',
    "negative count": "[flow]\ntroy_approves_first = -1\n",
    "fractional count": "[flow]\ntroy_approves_first = 1.5\n",
    "count as text": '[flow]\ntroy_approves_first = "3"\n',
    "count as a boolean": "[flow]\ntroy_approves_first = true\n",
    "flow that is not a table": "flow = 3\n",
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


class AcceptedTablesTests(PrefetchedCase):
    """``[roles]`` and ``[flow]`` are accepted by ``code`` and ``pr``."""

    def test_code_accepts_every_valid_config(self):
        """``code`` runs cleanly with each valid table, ``troy_approves_first = 0`` included."""
        outs = parallel(lambda text: run_code(TITLE, config=config_of(text)), list(VALID.values()))
        for label, out in zip(VALID, outs):
            with self.subTest(config=label):
                self.assert_clean(out)

    def test_pr_accepts_every_valid_config(self):
        """``pr`` reads the same config without error."""
        outs = parallel(lambda text: run_pr(TITLE, {"docs/a.md": "a\n"}, config=config_of(text)),
                        list(VALID.values()))
        for label, out in zip(VALID, outs):
            with self.subTest(config=label):
                self.assert_clean(out)


class RefusedTablesTests(PrefetchedCase):
    """Unknown roles and keys, wrong efforts, and bad counts still exit with code 2."""

    def test_code_exits_two(self):
        """``code`` stops on each invalid table."""
        outs = parallel(lambda text: run_code(TITLE, config=config_of(text)),
                        list(INVALID.values()))
        for label, out in zip(INVALID, outs):
            with self.subTest(config=label):
                self.assert_exit(out, 2)

    def test_pr_exits_two(self):
        """``pr`` stops on each invalid table."""
        outs = parallel(lambda text: run_pr(TITLE, {"docs/a.md": "a\n"}, config=config_of(text)),
                        list(INVALID.values()))
        for label, out in zip(INVALID, outs):
            with self.subTest(config=label):
                self.assert_exit(out, 2)


class CommitTablesTests(CheckTestCase):
    """``commit`` reads the working tree's config with the same rules."""

    def test_commit_accepts_every_valid_config(self):
        """Each valid table passes ``commit`` with exit code 0."""
        for label, out in zip(VALID, parallel(commit_outcome, list(VALID.values()))):
            with self.subTest(config=label):
                self.assert_exit(out, 0)

    def test_commit_refuses_every_invalid_config(self):
        """Each invalid table stops ``commit`` with exit code 2."""
        for label, out in zip(INVALID, parallel(commit_outcome, list(INVALID.values()))):
            with self.subTest(config=label):
                self.assert_exit(out, 2)


class ParseConfigTests(unittest.TestCase):
    """``troycheck.config.parse_config`` returns ``roles`` and ``troy_approves_first``."""

    @classmethod
    def setUpClass(cls):
        """Imports the config module once."""
        cls.module = import_config_module()

    def test_roles_hold_only_the_keys_set(self):
        """Each role maps to the keys its table sets, and nothing else."""
        config = self.module.parse_config(config_of(
            VALID["developer model and effort"] + VALID["reviewer effort only"]))
        self.assertEqual(config.roles, {"developer": {"model": "opus", "effort": "high"},
                                        "code-reviewer": {"effort": "medium"}})

    def test_defaults_without_the_tables(self):
        """No ``[roles]`` and no ``[flow]``: an empty dict and a count of 3."""
        for text in (None, config_of("")):
            with self.subTest(text=text):
                config = self.module.parse_config(text)
                self.assertEqual(config.roles, {})
                self.assertEqual(config.troy_approves_first, 3)

    def test_count_is_read_as_given(self):
        """0 and 5 are read as whole numbers."""
        for count in (0, 5):
            with self.subTest(count=count):
                config = self.module.parse_config(config_of(
                    f"[flow]\ntroy_approves_first = {count}\n"))
                self.assertEqual(config.troy_approves_first, count)
                self.assertIs(type(config.troy_approves_first), int)

    def test_invalid_tables_raise(self):
        """Every invalid table raises ``ConfigError``."""
        for label, text in INVALID.items():
            with self.subTest(config=label):
                with self.assertRaises(self.module.ConfigError):
                    self.module.parse_config(config_of(text))


class DefaultConfigTests(unittest.TestCase):
    """``config.default.toml`` describes both tables in comments only (F07 design 12)."""

    @classmethod
    def setUpClass(cls):
        """Reads the default config and the config module."""
        cls.text = (CHECKS / "config.default.toml").read_bytes().decode("utf-8")
        cls.module = import_config_module()

    def test_default_config_still_parses_with_no_active_role_or_count(self):
        """It parses, sets no role, and leaves the count at its default."""
        config = self.module.parse_config(self.text)
        self.assertEqual(config.roles, {})
        self.assertEqual(config.troy_approves_first, 3)
        data = tomllib.loads(self.text)
        self.assertEqual(data.get("roles", {}), {})
        self.assertNotIn("troy_approves_first", data.get("flow", {}))

    def test_comments_describe_both_tables(self):
        """Comment lines mention ``[roles.``, ``model``, ``effort``, ``[flow]``, and the count."""
        comments = "\n".join(line for line in self.text.replace("\r\n", "\n").split("\n")
                             if line.lstrip().startswith("#"))
        for word in ("[roles.", "model", "effort", "troy_approves_first"):
            with self.subTest(word=word):
                self.assertIn(word, comments)
        self.assertIn("[flow]", self.text)


if __name__ == "__main__":
    unittest.main()
