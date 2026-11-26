"""Text tests of guide section 3.1 for D203 (F07 design 4 and 16), tstack issue #52.

A feature-loop request that names a version, such as "Start v0.1", reaches that version's
remaining features; the reach ends before the release, which stays its own request. The guide
says so in both languages: the requests table, the paragraph after it, the issue link, and the
version and sync note of the header.

Run from the repository root:
python -m unittest discover -s troy-mode/dev/tests -p "test_version_reach_guide.py" -v
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GUIDE = REPO / "docs" / "troy-mode" / "guide"
EN_FILE = GUIDE / "03-features.md"
ZH_FILE = GUIDE / "03-features.zh-CN.md"
EN_D203 = "../design/F07-entry-skill.md#16-decisions-for-troy"
ZH_D203 = "../design/F07-entry-skill.zh-CN.md#16-需要-troy-决定的事项"
ISSUE_LINK = "https://github.com/ZJUCao/tstack/issues/52"


def read(path: Path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def section_31(text: str) -> str:
    """The text from the ``## 3.1`` heading up to ``## 3.2``, or "" when it is missing."""
    match = re.search(r"^## 3\.1 .*?(?=^## 3\.2 |\Z)", text, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ""


def table_rows(section: str) -> list:
    """The rows of the section's table as lists of trimmed cells (header and rule included)."""
    return [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in section.split("\n") if line.strip().startswith("|")]


def header_cell(text: str, label: str) -> str:
    """The value cell of the header table row labelled ``label``, or "" when it is missing."""
    head = text.split("\n## 3.1", 1)[0]
    for row in table_rows(head):
        if len(row) == 2 and row[0] == label:
            return row[1]
    return ""


class GuideCase:
    """Shared checks; the subclasses set the file and the language's words."""

    FILE = EN_FILE
    ROW_COMMAND = ""
    NOT_YET = ""
    D203_TARGET = ""

    @classmethod
    def setUpClass(cls):
        """Reads the guide file once and cuts section 3.1 out of it."""
        cls.text = read(cls.FILE)
        cls.section = section_31(cls.text)

    def test_section_exists(self):
        """Section 3.1 is found in the file."""
        self.assertNotEqual(self.section, "")

    def test_table_has_the_start_version_row(self):
        """One table row has the Start-version command in its first cell and the words for
        "not yet accepted" in its second cell."""
        rows = [row for row in table_rows(self.section)
                if len(row) == 2 and self.ROW_COMMAND in row[0]]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn(self.NOT_YET, rows[0][1])

    def test_paragraph_links_d203(self):
        """The section has the Markdown link [...D203...](target) with the exact D203 target."""
        pattern = r"\[[^\]]*D203[^\]]*\]\(" + re.escape(self.D203_TARGET) + r"\)"
        self.assertRegex(self.section, pattern)

    def test_paragraph_names_the_release_request(self):
        """The paragraph names the release request `release v0.1` in code font."""
        self.assertIn("`release v0.1`", self.section)


class EnglishGuideTests(GuideCase, unittest.TestCase):
    """D203 and #52 in ``03-features.md``."""

    FILE = EN_FILE
    ROW_COMMAND = "`/tstack:troy-mode Start v0.1`"
    NOT_YET = "not yet accepted"
    D203_TARGET = EN_D203

    def test_issue_link_points_to_tstack(self):
        """The issue link is the Markdown link to ZJUCao/tstack issue 52."""
        self.assertRegex(self.section, r"\[[^\]]*52[^\]]*\]\(" + re.escape(ISSUE_LINK) + r"\)")

    def test_issue_link_is_not_the_old_repository(self):
        """Every link to an issue 52 points to ZJUCao/tstack, none to the repository's old
        name."""
        repositories = re.findall(r"https://github\.com/ZJUCao/([\w.-]+)/issues/52\b",
                                  self.section)
        self.assertEqual(repositories, ["tstack"], repositories)

    def test_header_version_is_0_4(self):
        """The header table's Version is exactly 0.4."""
        # F18 part 1 (D172) moves the reach to Troy's device test: guide 0.4.
        self.assertEqual(header_cell(self.text, "Version"), "0.4")


class ChineseGuideTests(GuideCase, unittest.TestCase):
    """D203 and #52 in ``03-features.zh-CN.md``."""

    FILE = ZH_FILE
    ROW_COMMAND = "`/tstack:troy-mode 开始做 v0.1`"
    NOT_YET = "还没验收"
    D203_TARGET = ZH_D203

    def test_sync_note_says_english_0_4(self):
        """The mirror note before section 3.1 says it syncs from English version 0.4."""
        # F18 part 1 (D172): guide 0.4.
        head = self.text.split("\n## 3.1", 1)[0]
        self.assertRegex(head, r"同步自英文版 0\.4(?![\d.])")

    def test_header_version_is_0_4(self):
        """The header table's 版本 is exactly 0.4."""
        # F18 part 1 (D172): guide 0.4.
        self.assertEqual(header_cell(self.text, "版本"), "0.4")


if __name__ == "__main__":
    unittest.main()
