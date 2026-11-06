"""Tests for R19: commit identity and Claude attribution (design 6.6)."""

import unittest

from helpers import (
    EMAIL, GITHUB_COMMITTER_EMAIL, OTHER_EMAIL, CheckTestCase, Sandbox,
    make_config, parallel, pr_body, pr_sandbox, run_pr,
)

TITLE = "[docs] Update notes"
CHANGE = {"docs/a.md": "a\n"}
TRAILERS = make_config(mode="trailers")
ALWAYS_BAD = [
    "Co-Authored-By: Claude Opus <someone@example.test>",
    "Co-Authored-By: Helper <bot@anthropic.com>",
    "Generated with Claude Code",
    "See https://claude.com/claude-code for details",
    "See https://claude.ai/code/session_123",
    "Sent via noreply@anthropic.com",
]


class IdentityTests(CheckTestCase):
    """Author and committer emails."""

    def test_matching_emails_pass(self):
        """Author and committer with the configured email pass."""
        out = run_pr(TITLE, CHANGE)
        self.assert_rule(out, "R19", "pass")
        self.assert_clean(out)

    def test_wrong_author_email_fails(self):
        """An author email other than commit_email fails."""
        out = run_pr(TITLE, CHANGE, author=OTHER_EMAIL)
        self.assert_rule(out, "R19", "fail")
        self.assert_exit(out, 1)

    def test_wrong_committer_email_fails(self):
        """A committer email other than commit_email fails."""
        out = run_pr(TITLE, CHANGE, committer=OTHER_EMAIL)
        self.assert_rule(out, "R19", "fail")

    def test_github_web_committer_is_allowed(self):
        """GitHub's noreply address may be the committer."""
        out = run_pr(TITLE, CHANGE, committer=GITHUB_COMMITTER_EMAIL)
        self.assert_rule(out, "R19", "pass")

    def test_github_noreply_is_not_allowed_as_author(self):
        """The GitHub exception covers the committer, not the author."""
        out = run_pr(TITLE, CHANGE, author=GITHUB_COMMITTER_EMAIL)
        self.assert_rule(out, "R19", "fail")

    def test_real_noreply_address_as_commit_email_works(self):
        """The email from the global instructions is a normal commit_email."""
        email = "148482542+ZJUCao@users.noreply.github.com"
        out = run_pr(TITLE, CHANGE, config=make_config(email=email), author=email,
                     committer=email)
        self.assert_rule(out, "R19", "pass")

    def test_every_commit_is_checked(self):
        """A bad author on the second of two commits fails R19."""
        with Sandbox() as sb:
            sb.branch()
            sb.commit(CHANGE, message="First")
            sb.commit({"docs/b.md": "b\n"}, message="Second", author=OTHER_EMAIL)
            out = sb.check_pr(TITLE)
        self.assert_rule(out, "R19", "fail")
        self.assert_rule(out, "R01", "fail")

    def test_attribution_in_second_commit_message_fails(self):
        """Every commit message is scanned, not only the last."""
        with Sandbox() as sb:
            sb.branch()
            sb.commit(CHANGE, message="First\n\nGenerated with Claude Code")
            sb.commit({"docs/b.md": "b\n"}, message="Second")
            out = sb.check_pr(TITLE)
        self.assert_rule(out, "R19", "fail")

    def test_no_commit_email_configured_warns(self):
        """Without commit_email the email check is a warning that says so."""
        out = run_pr(TITLE, CHANGE, config=make_config(email=None, mode="strict"))
        self.assert_rule(out, "R19", "warn")
        self.assert_clean(out)

    def test_no_commit_email_still_checks_attribution(self):
        """Attribution is checked even when no email is configured."""
        out = run_pr(TITLE, CHANGE, config=make_config(email=None),
                     message="Fix\n\nGenerated with Claude Code")
        self.assert_rule(out, "R19", "fail")


class AttributionTests(CheckTestCase):
    """Claude attribution in messages, titles, and descriptions."""

    @classmethod
    def setUpClass(cls):
        """Builds clean PRs in strict and trailers mode for title/body cases."""
        cls.strict = pr_sandbox(CHANGE, config=make_config(mode="strict"))
        cls.trailers = pr_sandbox(CHANGE, config=TRAILERS)
        cls.addClassCleanup(cls.strict.close)
        cls.addClassCleanup(cls.trailers.close)

    def test_default_mode_is_strict(self):
        """With no mode in the config, a bare word fails."""
        out = run_pr(TITLE, CHANGE, message="Ask Claude about it")
        self.assert_rule(out, "R19", "fail")

    def test_always_forbidden_attribution_fails_in_trailers_mode(self):
        """Attribution lines, links, and addresses fail in every mode."""
        for text in ALWAYS_BAD:
            with self.subTest(text=text):
                out = run_pr(TITLE, CHANGE, config=TRAILERS, message=f"Fix\n\n{text}")
                self.assert_rule(out, "R19", "fail")
                self.assert_exit(out, 1)

    def test_co_authored_by_trailer_fails_in_strict_mode(self):
        """A Co-Authored-By trailer naming Claude fails in strict mode too."""
        out = run_pr(TITLE, CHANGE, message=ALWAYS_BAD[0])
        self.assert_rule(out, "R19", "fail")

    def test_human_co_author_passes(self):
        """A Co-Authored-By trailer for a person is not attribution."""
        message = "Fix\n\nCo-Authored-By: Pat Doe <pat@example.test>"
        configs = [make_config(mode="strict"), TRAILERS]
        outs = parallel(lambda c: run_pr(TITLE, CHANGE, config=c, message=message), configs)
        for config, out in zip(configs, outs):
            with self.subTest(config=config):
                self.assert_rule(out, "R19", "pass")

    def test_bare_word_fails_in_strict_mode(self):
        """Any whole word Claude or Anthropic fails in strict mode."""
        messages = ["Ask Claude about it", "ask claude", "CLAUDE rules", "anthropic docs",
                    "Built with the Anthropic SDK"]
        config = make_config(mode="strict")
        outs = parallel(lambda m: run_pr(TITLE, CHANGE, config=config, message=m), messages)
        for message, out in zip(messages, outs):
            with self.subTest(message=message):
                self.assert_rule(out, "R19", "fail")

    def test_bare_word_passes_in_trailers_mode(self):
        """The same words pass in trailers mode."""
        messages = ["Ask Claude about it", "Built with the Anthropic SDK"]
        outs = parallel(lambda m: run_pr(TITLE, CHANGE, config=TRAILERS, message=m), messages)
        for message, out in zip(messages, outs):
            with self.subTest(message=message):
                self.assert_rule(out, "R19", "pass")

    def test_longer_words_are_not_matches_in_strict_mode(self):
        """Only whole words count, so Claudette and anthropology pass."""
        out = run_pr(TITLE, CHANGE, config=make_config(mode="strict"),
                     message="Thanks Claudette, anthropology notes")
        self.assert_rule(out, "R19", "pass")

    def test_claude_in_title_fails_in_strict_only(self):
        """A bare Claude in the PR title fails in strict mode and passes in trailers."""
        title = "[docs] Document the Claude API"
        self.assert_rule(self.strict.check_pr(title), "R19", "fail")
        self.assert_rule(self.trailers.check_pr(title), "R19", "pass")

    def test_attribution_text_in_title_fails_in_trailers_mode(self):
        """Always-forbidden text in the title fails in every mode."""
        out = self.trailers.check_pr("[docs] Generated with Claude Code")
        self.assert_rule(out, "R19", "fail")

    def test_claude_in_description_fails_in_strict_only(self):
        """A bare Claude in the description fails in strict mode only."""
        body = pr_body() + "\nWritten by Claude.\n"
        self.assert_rule(self.strict.check_pr(TITLE, body=body), "R19", "fail")
        self.assert_rule(self.trailers.check_pr(TITLE, body=body), "R19", "pass")

    def test_attribution_in_description_fails_in_trailers_mode(self):
        """Attribution lines and links in the description fail in every mode."""
        bodies = [
            "\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)",
            "Co-Authored-By: Claude <noreply@anthropic.com>",
            "https://claude.ai/code/abc",
        ]
        for text in bodies:
            with self.subTest(text=text):
                out = self.trailers.check_pr(TITLE, body=pr_body() + "\n" + text + "\n")
                self.assert_rule(out, "R19", "fail")

    def test_clean_title_and_description_pass(self):
        """A clean title and description pass in both modes."""
        for box in (self.strict, self.trailers):
            out = box.check_pr(TITLE, body=pr_body())
            self.assert_rule(out, "R19", "pass")


if __name__ == "__main__":
    unittest.main()
