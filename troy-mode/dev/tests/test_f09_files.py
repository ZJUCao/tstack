"""Text tests of the files F09 changes besides the engine (F09 design 7, 8; interface note 9, 11).

- The reviewers' line about P rules of type Review in AR2, TM2, and CR1.
- The Developer's and the Test Engineer's rule about a baselined file they
  change, outside their Tasks section, and ``baseline:`` in DV5 and TE6.
- The rules template's guidance about P rows, in both languages.
- The templates README's PR kinds row for ``[P01 test-fix]``, in both languages.

The task headings themselves (AR6, DV5, TE6) are checked by ``test_roles.py``.

Run from the repository root:
python -m unittest discover -s troy-mode/dev/tests -v
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "troy-mode" / "templates"
AGENTS = REPO / "agents"


def read(path: Path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def section(text: str, heading: str, level: int = 2) -> str:
    """The text under a heading, up to the next heading of the same or a higher level.

    Fenced code blocks are skipped when looking for the end, so a ``#`` line
    inside one does not end the section.

    Args:
        text: The document.
        heading: The heading's exact title, without the ``#`` signs.
        level: The heading's level.

    Returns:
        The section's lines after the heading, or "" when there is no such heading.
    """
    lines = text.split("\n")
    marker = "#" * level + " " + heading
    start = next((i for i, line in enumerate(lines) if line.strip() == marker), None)
    if start is None:
        return ""
    found, fence = [], False
    for line in lines[start + 1:]:
        if re.match(r"^ {0,3}(```|~~~)", line):
            fence = not fence
        match = None if fence else re.match(r"^(#{1,6}) ", line)
        if match and len(match.group(1)) <= level:
            break
        found.append(line)
    return "\n".join(found)


def without_section(text: str, heading: str, level: int = 2) -> str:
    """The text with one section (its heading and body) removed."""
    body = section(text, heading, level)
    marker = "#" * level + " " + heading
    if not body and marker not in text.split("\n"):
        return text
    return text.replace(marker + "\n" + body, "", 1)


def table_rows(text: str) -> list:
    """The cells of every Markdown table row in a text, separator rows left out."""
    rows = []
    for line in text.split("\n"):
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                rows.append(cells)
    return rows


def comment_before(text: str, heading: str) -> str:
    """The last HTML comment that ends before a heading line and after the previous heading.

    Args:
        text: The document.
        heading: The heading line, for example ``## 3. Change log``.

    Returns:
        The comment's text, from ``<!--`` to ``-->``, or "" when there is none.
    """
    lines = text.split("\n")
    if heading not in lines:
        return ""
    before = "\n".join(lines[:lines.index(heading)])
    previous = max((m.end() for m in re.finditer(r"(?m)^#{1,6} .*$", before)), default=0)
    comments = re.findall(r"<!--.*?-->", before[previous:], flags=re.S)
    return comments[-1] if comments else ""


class AgentTextTests(unittest.TestCase):
    """The role files as F09 changes them (interface note section 9)."""

    def task(self, agent: str, heading: str) -> str:
        """The text of one task subsection of an agent file, failing when it is missing."""
        text = section(read(AGENTS / agent), heading, 3)
        self.assertNotEqual(text.strip(), "", f"{agent}: no '### {heading}'")
        return text

    def test_reviewers_check_the_review_rules_that_name_them(self):
        """AR2, TM2, and CR1 each say they check the P rules of type Review whose Enforced by
        names their role."""
        cases = (("troy-architect.md", "AR2 Design review"),
                 ("troy-test-manager.md", "TM2 Test review"),
                 ("troy-code-reviewer.md", "CR1 Review"))
        for agent, heading in cases:
            text = self.task(agent, heading)
            for words in ("type Review", "Enforced by"):
                with self.subTest(agent=agent, words=words):
                    self.assertIn(words, text)

    def test_authors_remove_the_baseline_line_of_a_file_they_change(self):
        """The Developer and the Test Engineer name the baseline line outside their Tasks."""
        for agent in ("troy-developer.md", "troy-test-engineer.md"):
            with self.subTest(agent=agent):
                text = read(AGENTS / agent)
                self.assertNotEqual(section(text, "Tasks").strip(), "", f"{agent}: no Tasks")
                outside = without_section(text, "Tasks")
                self.assertNotEqual(outside, text)
                self.assertIn("baseline line", outside.lower())

    def test_cleanup_tasks_name_the_baseline_comment(self):
        """DV5 and TE6 name ``baseline:``."""
        self.assertIn("baseline:", self.task("troy-developer.md", "DV5 Cleanup"))
        self.assertIn("baseline:", self.task("troy-test-engineer.md", "TE6 Test cleanup"))

    def test_new_tasks_have_text_under_tasks(self):
        """AR6 has text, and DV5 and TE6 are under their roles' Tasks sections."""
        self.task("troy-architect.md", "AR6 Rule enforcement")
        for agent, heading in (("troy-developer.md", "DV5 Cleanup"),
                               ("troy-test-engineer.md", "TE6 Test cleanup")):
            with self.subTest(agent=agent):
                self.assertIn(f"### {heading}", section(read(AGENTS / agent), "Tasks"))


class RulesTemplateTests(unittest.TestCase):
    """The rules template's guidance describes P rows (F09 design 8; note section 11)."""

    CASES = {
        "rules.md": ("## 3. Change log", ("Retired on", "baseline: P01")),
        "rules.zh-CN.md": ("## 3. 修改记录", ("停用", "baseline: P01")),
    }

    def test_guidance_before_the_change_log_names_retired_rows_and_the_baseline(self):
        """The comment before the change log names a retired row and ``baseline: P01``."""
        for name, (heading, words) in self.CASES.items():
            comment = comment_before(read(TEMPLATES / name), heading)
            for word in words:
                with self.subTest(template=name, word=word):
                    self.assertTrue(comment.startswith("<!-- template:"), comment[:200])
                    self.assertIn(word, comment)

    def test_r_rows_are_unchanged(self):
        """Both templates hold the rows R01 to R23, in order (R22 from F14, R23 from tstack #64)."""
        for name in self.CASES:
            with self.subTest(template=name):
                ids = re.findall(r"(?m)^\| (R\d{2}) \|", read(TEMPLATES / name))
                self.assertEqual(ids, [f"R{n:02d}" for n in range(1, 24)])


class TemplatesReadmeTests(unittest.TestCase):
    """The PR kinds table lists the rule's test cleanup PR (F09 design 8, F01)."""

    def test_pr_kinds_have_the_rule_test_fix_row(self):
        """One row of the PR kinds table holds ``[P01 test-fix]``, in both languages.

        The note says the row's "first cell"; the table's first column is the
        kind's name and the second its title example, so any cell counts.
        """
        for name, heading in (("README.md", "6. PR kinds"), ("README.zh-CN.md", "6. PR 类型")):
            with self.subTest(readme=name):
                rows = table_rows(section(read(TEMPLATES / name), heading))
                self.assertTrue(rows, f"{name}: no PR kinds table")
                found = [row for row in rows if any("[P01 test-fix]" in cell for cell in row)]
                self.assertEqual(len(found), 1, rows)
                self.assertEqual(len(found[0]), len(rows[0]), found[0])


if __name__ == "__main__":
    unittest.main()
