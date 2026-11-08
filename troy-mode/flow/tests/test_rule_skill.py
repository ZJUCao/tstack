"""The rule change flow in the entry skill (F09 design 4 to 8, 10.1; interface note section 10).

``skills/troy-mode/SKILL.md`` gains the section "Rule change": it routes
"add a rule" there, names the engine's new commands, the role tasks, the PR
titles, the baseline comment, the issue for a rule for every project, the
two phrases of Troy's choice, and the action ``cleanup``. Its Start section
reads the P rows of type Process.
"""

import re
import unittest

from test_entry_skill import SKILL, routing_rows, split_skill

TEXTS = ("troy_flow.py rule-id", "troy_flow.py rule-row", "snapshot --role rules", "AR6", "DV5",
         "TE6", "[rules] Add", "[rules] Change", "[rules] Retire", "[refactor] Apply",
         "test-fix] Apply", "[docs] Change the architecture for", "baseline: P",
         "gh issue create --repo", "Existing code: fixed by cleanup PRs.",
         "Existing code: fixed when touched.")


def section(body: str, title: str) -> str:
    """The text under a level-2 heading, up to the next level-1 or level-2 heading.

    Args:
        body: The skill's text after the front matter.
        title: The heading's title, without ``## ``.

    Returns:
        The section's text, or "" when there is no such heading.
    """
    lines = body.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == f"## {title}"), None)
    if start is None:
        return ""
    found = []
    for line in lines[start + 1:]:
        if re.match(r"^#{1,2} ", line):
            break
        found.append(line)
    return "\n".join(found)


class RuleChangeSkillTests(unittest.TestCase):
    """F09's texts in the entry skill."""

    @classmethod
    def setUpClass(cls):
        """Reads SKILL.md once; an empty text when it does not exist yet."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.body = split_skill(text)[1]

    def test_has_the_rule_change_section(self):
        """A level-2 heading ``## Rule change`` with text under it."""
        self.assertIn("## Rule change", self.body.split("\n"))
        self.assertNotEqual(section(self.body, "Rule change").strip(), "")

    def test_routing_sends_rule_requests_here(self):
        """The routing rows for "add a rule", "change P01", and "retire" name the Rule change.

        The "add a rule" row is checked in ``test_entry_skill``; here every
        row whose request names a rule change routes to the same flow.
        """
        rows = [row for row in routing_rows(self.body)
                if re.search(r"add a rule|\bchange P\d|\bretire P\d", row[0])]
        self.assertTrue(rows, routing_rows(self.body))
        for row in rows:
            with self.subTest(request=row[0]):
                self.assertIn("Rule change", " | ".join(row))

    def test_names_the_commands_tasks_titles_and_phrases(self):
        """Each text of the note's section 10."""
        for text in TEXTS:
            with self.subTest(text=text):
                self.assertIn(text, self.body)

    def test_new_commands_are_whole_words(self):
        """``troy_flow.py rule-id`` and ``rule-row`` as commands, not as parts of longer words."""
        for command in ("rule-id", "rule-row"):
            with self.subTest(command=command):
                self.assertRegex(self.body, re.escape(f"troy_flow.py {command}") + r"(?![\w-])")

    def test_names_the_cleanup_action(self):
        """The action ``cleanup`` (from ``status``), not only the words "cleanup PRs"."""
        self.assertRegex(self.body, r"`cleanup`|\baction\s+`?cleanup\b|\bcleanup`?\s+action\b")

    def test_start_reads_the_process_rules(self):
        """The Start section names the P rows (P rules) of type Process, on one line."""
        start = section(self.body, "Start")
        self.assertNotEqual(start.strip(), "", "no '## Start' section")
        lines = [line for line in start.split("\n")
                 if re.search(r"\bP (rows?|rules?)\b", line) and "Process" in line]
        self.assertTrue(lines, start)


if __name__ == "__main__":
    unittest.main()
