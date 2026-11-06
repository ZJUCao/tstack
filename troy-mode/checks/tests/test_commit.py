"""Tests for the ``commit`` subcommand (design section 3.2)."""

import tempfile
import unittest
from pathlib import Path

from helpers import (
    CONFIG_PATH, EMAIL, OTHER_EMAIL, CheckTestCase, Sandbox, base_env,
    make_config, run_checker, write_file,
)

BAD_TRAILER = "Fix\n\nCo-Authored-By: Claude <noreply@anthropic.com>"


class CommitTests(CheckTestCase):
    """Checks R19 for one commit before it is made."""

    @classmethod
    def setUpClass(cls):
        """Builds one repository with the default config."""
        cls.sb = Sandbox()
        cls.addClassCleanup(cls.sb.close)

    def test_clean_message_file_passes(self):
        """A clean message file and a matching email pass."""
        out = self.sb.check_commit(file_text="Fix the crash\n", email=EMAIL)
        self.assertEqual(out.report["command"], "commit")
        self.assertIsNone(out.report["title"])
        self.assert_rule(out, "R19", "pass")
        self.assert_clean(out)

    def test_only_r19_is_reported(self):
        """The commit command reports R19 and no other rule."""
        out = self.sb.check_commit(message="Fix", email=EMAIL)
        self.assertEqual([r["rule"] for r in out.report["results"]], ["R19"], out.describe())

    def test_inline_message_is_checked(self):
        """--message works like --message-file."""
        out = self.sb.check_commit(message="Fix the crash", email=EMAIL)
        self.assert_rule(out, "R19", "pass")

    def test_wrong_email_fails(self):
        """An --email other than commit_email fails with exit code 1."""
        out = self.sb.check_commit(message="Fix", email=OTHER_EMAIL)
        self.assert_rule(out, "R19", "fail")
        self.assert_exit(out, 1)
        self.assertFalse(out.report["ok"])

    def test_attribution_in_message_file_fails(self):
        """Claude attribution in the message file fails."""
        out = self.sb.check_commit(file_text=BAD_TRAILER, email=EMAIL)
        self.assert_rule(out, "R19", "fail")
        self.assert_exit(out, 1)

    def test_attribution_in_inline_message_fails(self):
        """Claude attribution in --message fails."""
        out = self.sb.check_commit(message=BAD_TRAILER, email=EMAIL)
        self.assert_rule(out, "R19", "fail")

    def test_chinese_message_file_is_read_as_utf8(self):
        """A UTF-8 message file with Chinese text passes."""
        out = self.sb.check_commit(file_text="修复空历史记录时的崩溃\n", email=EMAIL)
        self.assert_rule(out, "R19", "pass")

    def test_author_email_defaults_to_git_var(self):
        """Without --email the email git would use as author is checked."""
        good = self.sb.check_commit(message="Fix", env_extra={"GIT_AUTHOR_EMAIL": EMAIL})
        bad = self.sb.check_commit(message="Fix", env_extra={"GIT_AUTHOR_EMAIL": OTHER_EMAIL})
        self.assert_rule(good, "R19", "pass")
        self.assert_rule(bad, "R19", "fail")

    def test_email_option_overrides_git_var(self):
        """--email wins over the author identity git would use."""
        out = self.sb.check_commit(message="Fix", email=EMAIL,
                                   env_extra={"GIT_AUTHOR_EMAIL": OTHER_EMAIL})
        self.assert_rule(out, "R19", "pass")

    def test_missing_message_exits_two(self):
        """Without a message option the tool cannot run."""
        out = run_checker(["commit", "--repo", str(self.sb.root)], self.sb.tmp)
        self.assert_exit(out, 2)

    def test_not_a_git_repository_exits_two(self):
        """A folder that is not a git repository gives exit code 2."""
        with tempfile.TemporaryDirectory() as plain:
            env = base_env({"GIT_CEILING_DIRECTORIES": str(Path(plain).parent)})
            args = ["commit", "--message", "Fix", "--email", EMAIL, "--repo", plain]
            self.assert_exit(run_checker(args, Path(plain), env), 2)


class CommitConfigTests(CheckTestCase):
    """The commit command reads the config from the working tree."""

    def test_uncommitted_config_is_used(self):
        """A working-tree config change applies, unlike in pr."""
        with Sandbox() as sb:
            write_file(sb.root, CONFIG_PATH, make_config(email=OTHER_EMAIL))
            new = sb.check_commit(message="Fix", email=OTHER_EMAIL)
            old = sb.check_commit(message="Fix", email=EMAIL)
        self.assert_rule(new, "R19", "pass")
        self.assert_rule(old, "R19", "fail")

    def test_strict_mode_rejects_bare_word(self):
        """In strict mode a bare Claude fails."""
        with Sandbox(config=make_config(mode="strict")) as sb:
            out = sb.check_commit(message="Ask Claude", email=EMAIL)
        self.assert_rule(out, "R19", "fail")

    def test_trailers_mode_allows_bare_word_but_not_trailer(self):
        """In trailers mode a bare word passes and a trailer still fails."""
        with Sandbox(config=make_config(mode="trailers")) as sb:
            word = sb.check_commit(message="Ask Claude", email=EMAIL)
            trailer = sb.check_commit(message=BAD_TRAILER, email=EMAIL)
        self.assert_rule(word, "R19", "pass")
        self.assert_rule(trailer, "R19", "fail")

    def test_no_commit_email_configured_warns(self):
        """Without commit_email the check warns and exits 0."""
        with Sandbox(config=make_config(email=None)) as sb:
            out = sb.check_commit(message="Fix", email=EMAIL)
        self.assert_rule(out, "R19", "warn")
        self.assert_exit(out, 0)

    def test_invalid_config_exits_two(self):
        """An invalid config stops the tool with exit code 2."""
        with Sandbox(config="[bogus]\nx = 1\n") as sb:
            out = sb.check_commit(message="Fix", email=EMAIL)
        self.assert_exit(out, 2)


class HookTests(CheckTestCase):
    """The command works as a git commit-msg hook."""

    def test_message_file_argument_works_without_json(self):
        """A hook run prints text and exits 0 or 1 by the verdict."""
        with Sandbox() as sb:
            write_file(sb.tmp, "good.txt", "Fix\n")
            write_file(sb.tmp, "bad.txt", BAD_TRAILER + "\n")
            env = {"GIT_AUTHOR_EMAIL": EMAIL}
            good = sb.run_checker("commit", "--message-file", str(sb.tmp / "good.txt"),
                                  "--repo", str(sb.root), env_extra=env)
            bad = sb.run_checker("commit", "--message-file", str(sb.tmp / "bad.txt"),
                                 "--repo", str(sb.root), env_extra=env)
        self.assert_exit(good, 0)
        self.assert_exit(bad, 1)
        self.assertIn("R19", bad.stdout)


if __name__ == "__main__":
    unittest.main()
