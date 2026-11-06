"""Tests for R20: no template markers or guidance left (design 6.7)."""

import unittest

from helpers import (
    ZH_BODY, CheckTestCase, doc_pair, make_config, pr_body, pr_sandbox, run_pr,
)

TITLE = "[docs] Update notes"

# (text, is_marker). One document holds all of them so one run covers every case.
CASES = [
    ("Feature: {{feature-id}}", True),
    ("Many: {{feature-ids, or None}}", True),
    ("Spaces inside {{x y}} are fine", True),
    ("$ {{x}} with a space after the dollar", True),
    ("<!-- template: write the why -->", True),
    ("<!--template: tight-->", True),
    ("<!--   template: loose -->", True),
    ("Mixed ${{ github.sha }} and {{real}}", True),
    ("run: echo ${{ github.sha }}", False),
    ("Hello {{ count }}", False),
    ("Hello {{ count}}", False),
    ("Hello {{count }}", False),
    ("int a[2][2] = {{1, 2}, {3, 4}};", False),
    ("${{x}}", False),
    ("<!-- an ordinary comment -->", False),
    ("<!-- see template: elsewhere -->", False),
    ("<!-- templates are handy -->", False),
    ("{{opened here", False),
    ("and closed there}}", False),
    ("```text", False),
    ("Inside code {{code-marker}}", True),
    ("Inside code {{ spaced }}", False),
    ("```", False),
]


def cases_document():
    """Builds the text of the case document and the lines expected to fail."""
    head = ["# Cases", ""]
    text = "\n".join(head + [t for t, _ in CASES]) + "\n"
    expected = [len(head) + i + 1 for i, (_, bad) in enumerate(CASES) if bad]
    return text, expected


class MarkerScanTests(CheckTestCase):
    """Scans changed documents."""

    def test_markers_and_guidance_fail_with_path_and_line(self):
        """Each marker or guidance comment fails with its path and line."""
        text, expected = cases_document()
        out = run_pr(TITLE, {"docs/cases.md": text})
        self.assert_rule(out, "R20", "fail")
        self.assert_exit(out, 1)
        self.assertEqual(sorted({d["line"] for d in out.details("R20")}), expected, out.describe())
        self.assert_paths(out, "R20", ["docs/cases.md"])

    def test_clean_document_passes(self):
        """A document without markers passes."""
        out = run_pr(TITLE, {"docs/a.md": "# A\n\nText ${{ github.sha }}\n"})
        self.assert_rule(out, "R20", "pass")
        self.assert_clean(out)

    def test_marker_in_chinese_mirror_reports_its_path(self):
        """A marker in a mirror fails with the mirror's path."""
        pair = doc_pair(name="x", version="0.1", zh_body=ZH_BODY + "\n{{todo}}\n")
        out = run_pr(TITLE, pair)
        self.assert_rule(out, "R12", "pass")
        self.assert_rule(out, "R20", "fail")
        self.assert_paths(out, "R20", ["docs/x.zh-CN.md"])

    def test_github_and_troy_mode_folders_are_not_scanned(self):
        """Markers in .github/ and .troy-mode/ are ignored, others are not."""
        changes = {
            ".github/pull_request_template.md": "{{summary}}\n<!-- template: x -->\n",
            ".troy-mode/templates/adr.md": "{{adr-id}}\n",
            "docs/guide.md": "a\nb\n{{todo}}\n",
        }
        out = run_pr("[rules] Update", changes)
        self.assert_rule(out, "R20", "fail")
        self.assert_paths(out, "R20", ["docs/guide.md"])

    def test_github_and_troy_mode_folders_alone_pass(self):
        """A PR that only touches the exempt folders passes R20."""
        changes = {".github/pull_request_template.md": "{{summary}}\n",
                   ".troy-mode/templates/adr.md": "{{adr-id}}\n"}
        self.assert_rule(run_pr("[rules] Update", changes), "R20", "pass")

    def test_allow_markers_exempts_listed_documents(self):
        """A document in allow_markers is not scanned, other documents are."""
        config = make_config(paths={"allow_markers": ["docs/tpl.md"]})
        changes = {"docs/tpl.md": "{{kept}}\n", "docs/other.md": "{{found}}\n"}
        out = run_pr(TITLE, changes, config=config)
        self.assert_rule(out, "R20", "fail")
        self.assert_paths(out, "R20", ["docs/other.md"])

    def test_unchanged_document_with_marker_is_not_scanned(self):
        """Only changed documents are scanned."""
        out = run_pr(TITLE, {"docs/new.md": "clean\n"}, base_files={"docs/old.md": "{{x}}\n"})
        self.assert_rule(out, "R20", "pass")

    def test_deleted_document_with_marker_passes(self):
        """Deleting a document that holds a marker is fine."""
        out = run_pr(TITLE, {"docs/old.md": None}, base_files={"docs/old.md": "{{x}}\n"})
        self.assert_rule(out, "R20", "pass")


class DescriptionTests(CheckTestCase):
    """Scans the PR description."""

    @classmethod
    def setUpClass(cls):
        """Builds one clean PR shared by all description cases."""
        cls.sb = pr_sandbox({"docs/a.md": "a\n"})
        cls.addClassCleanup(cls.sb.close)

    def test_marker_in_description_fails_with_line(self):
        """A marker in the description fails and gives its line number."""
        body = "## Why\n\nBecause.\n\nSee {{issue-id}}\n"
        out = self.sb.check_pr(TITLE, body=body)
        self.assert_rule(out, "R20", "fail")
        self.assertEqual([d["line"] for d in out.details("R20")], [5], out.describe())

    def test_guidance_comment_in_description_fails(self):
        """A template guidance comment in the description fails."""
        body = pr_body() + "\n<!-- template: explain why -->\n"
        self.assert_rule(self.sb.check_pr(TITLE, body=body), "R20", "fail")

    def test_marker_in_description_code_block_fails(self):
        """Code blocks in the description are scanned too."""
        body = pr_body() + "\n```\n{{marker}}\n```\n"
        self.assert_rule(self.sb.check_pr(TITLE, body=body), "R20", "fail")

    def test_clean_description_passes(self):
        """A description with lookalikes but no marker passes."""
        body = pr_body() + "\nRun `${{ github.sha }}` and {{ count }}.\n"
        out = self.sb.check_pr(TITLE, body=body)
        self.assert_rule(out, "R20", "pass")

    def test_no_body_file_skips_the_description(self):
        """Without --body-file the description is not scanned."""
        out = self.sb.check_pr(TITLE)
        self.assert_rule(out, "R20", "pass")


if __name__ == "__main__":
    unittest.main()
