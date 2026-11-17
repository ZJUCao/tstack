"""F15's texts in the entry skill (F15 design 3.4, 4.3, 8.4, 9, 11; 13.1 "Skill").

The skill names the ``issues`` command, a section "Issues for Troy" with the
steps of design 3.4, and the comment headings of design 8.4.
"""

import re
import unittest

from flow_helpers import PLUGIN_ROOT
from test_entry_skill import split_skill

SKILL = PLUGIN_ROOT / "skills/troy-mode/SKILL.md"
HEADINGS = ("Idea: requirement change", "Idea: bug", "Idea: rule", "Idea: answered",
            "Idea: later", "Idea: in the requirements", "Reply to Troy",
            "Device test, run <n>: ready")


def section_of(body: str, title: str) -> str:
    """The text under the heading with this title, to the next heading of its level or higher.

    Args:
        body: The skill's text after the front matter.
        title: The heading's text without the ``#`` signs.

    Returns:
        The section, or "" when no heading has the title.
    """
    lines = body.split("\n")
    start = next((i for i, line in enumerate(lines)
                  if re.fullmatch(r"#{2,4} " + re.escape(title), line.strip())), None)
    if start is None:
        return ""
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    found = []
    for line in lines[start + 1:]:
        match = re.match(r"^(#{1,6}) ", line)
        if match and len(match.group(1)) <= level:
            break
        found.append(line)
    return "\n".join(found)


class IssuesSkillTests(unittest.TestCase):
    """The skill's part of F15."""

    @classmethod
    def setUpClass(cls):
        """Reads SKILL.md once; an empty text when it does not exist."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.body = split_skill(text)[1]
        cls.section = section_of(cls.body, "Issues for Troy")

    def test_names_the_issues_command(self):
        """``troy_flow.py issues`` (design 3.2), with ``--json`` where the skill runs it."""
        self.assertRegex(self.body, re.escape("troy_flow.py issues") + r"(?![\w-])")
        self.assertRegex(self.section, r"issues[^\n]*--json")

    def test_has_the_issues_for_troy_section(self):
        """A section "Issues for Troy" (design 11)."""
        self.assertNotEqual(self.section.strip(), "")

    def test_apply_step_checks_each_body_by_its_exit_code(self):
        """Design 3.4 step 3: the labels, then check-text on each body file, by exit code."""
        text = self.section
        self.assertIn("labels", text)
        self.assertIn("check-text --file", text)
        self.assertIn("exit code", text)
        lines = [line for line in text.split("\n") if "check-text" in line]
        self.assertTrue(any("exit code" in line for line in lines), lines)

    def test_sync_runs_at_start_and_after_every_step(self):
        """Design 3.4 steps 1 and 2: after ``status`` at the start, and after each
        ``status --write-progress``."""
        self.assertIn("--write-progress", self.section)
        self.assertRegex(self.section.lower(), r"\bstart")

    def test_failures_are_noted_and_the_flow_goes_on(self):
        """Design 3.4 step 4 and section 9: ``Issue sync failed:`` with ``status --note``."""
        self.assertIn("Issue sync failed", self.section)
        self.assertIn("--note", self.section)

    def test_names_the_issue_comment_headings(self):
        """Each heading of design 8.4 that F15 adds."""
        for heading in HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, self.body)

    def test_stage_prs_name_their_progress_issue(self):
        """``Progress: #<n>`` in each stage PR's Why, and ``Closes #<n>`` in PR 6's (4.3)."""
        self.assertIn("Progress: #<n>", self.body)
        self.assertIn("Closes #<n>", self.body)


if __name__ == "__main__":
    unittest.main()
