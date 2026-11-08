"""Skill group (F07 design 2, 4, 8.1, 14.1): ``skills/troy-mode/SKILL.md``."""

import re
import unittest

from flow_helpers import PLUGIN_ROOT

SKILL = PLUGIN_ROOT / "skills/troy-mode/SKILL.md"
ENGINE_PATH = "${CLAUDE_PLUGIN_ROOT}/troy-mode/flow/troy_flow.py"
PM_PATH = "${CLAUDE_PLUGIN_ROOT}/troy-mode/roles/product-manager.md"
COMMANDS = ("status", "brief", "snapshot", "check-run", "approve", "check-text", "check-skips",
            "series")
FLOWS = ("Project setup", "Feature loop", "Bug fix", "Requirement change",
         "Work outside the pipeline", "Continue", "Upgrade", "Version release", "Rule change")
STAGE_TITLES = ("[<ID> 1/6 design] <name>", "[<ID> 2/6 test-plan] <name>",
                "[<ID> 3/6 mock] <name>", "[<ID> 4/6 tests] <name>", "[<ID> 5/6 impl] <name>",
                "[<ID> 6/6 accept] <name>")
GIT_TEXTS = ("git switch --detach", "gh pr merge <number> --rebase --delete-branch "
             "--match-head-commit", "gh pr checks <number> --watch", "git fetch origin")
PART2_TITLES = ("[B<n> A/B test] <summary>", "[B<n> B/B fix] <summary>",
                "[<ID> test-fix] <summary>", "[docs] Change the requirements: <summary>")
PART2_TEXTS = ("Fixes #<n>", "gh issue create", "--label bug", "gh pr close",
               "--allow-dependency")


def split_skill(text: str) -> tuple:
    """Splits SKILL.md into its front matter fields and the text after it.

    Args:
        text: The whole file.

    Returns:
        A dict of the top-level front matter keys and the body text.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return {}, text
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip().strip("\"'")
    return fields, "\n".join(lines[end + 1:])


class EntrySkillTests(unittest.TestCase):
    """The skill Troy types for all work in a troy-mode project."""

    @classmethod
    def setUpClass(cls):
        """Reads SKILL.md once; an empty text when it does not exist yet."""
        cls.text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.fields, cls.body = split_skill(cls.text)

    def test_front_matter_names_troy_mode(self):
        """The front matter's name is troy-mode."""
        self.assertEqual(self.fields.get("name"), "troy-mode")

    def test_runs_only_when_troy_types_it(self):
        """``disable-model-invocation: true`` (requirements section 8)."""
        self.assertEqual(self.fields.get("disable-model-invocation"), "true")

    def test_has_a_description(self):
        """The front matter has a description that is not empty."""
        self.assertNotEqual(self.fields.get("description", ""), "")

    def test_names_the_engine_and_the_product_manager(self):
        """The engine and the Product Manager's instructions by their plugin paths (design 2)."""
        for text in (ENGINE_PATH, PM_PATH):
            with self.subTest(text=text):
                self.assertIn(text, self.body)

    def test_names_every_engine_command(self):
        """Each command of design 3.1 as ``troy_flow.py <command>``."""
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assertRegex(self.body, re.escape(f"troy_flow.py {command}") + r"(?![\w-])")

    def test_names_every_flow(self):
        """Each flow of the routing table (design 4)."""
        for flow in FLOWS:
            with self.subTest(flow=flow):
                self.assertIn(flow, self.body)

    def test_names_the_six_stage_titles(self):
        """The PR titles of design 8.1."""
        for title in STAGE_TITLES:
            with self.subTest(title=title):
                self.assertIn(title, self.body)

    def test_names_the_merge_steps(self):
        """Detach, merge with the head check, watch the checks, and fetch (design 8.6)."""
        for text in GIT_TEXTS:
            with self.subTest(text=text):
                self.assertIn(text, self.body)

    def test_names_the_part_two_titles(self):
        """The bug, test-fix, and change PR titles (design 8.7, 11.1, 11.2)."""
        for title in PART2_TITLES:
            with self.subTest(title=title):
                self.assertIn(title, self.body)

    def test_names_the_part_two_commands(self):
        """The issue, the closing line, closing a stale PR, and allowing a dependency."""
        for text in PART2_TEXTS:
            with self.subTest(text=text):
                self.assertIn(text, self.body)

    def test_only_release_and_rule_change_are_not_built(self):
        """``not built yet`` names the version release and the rule change, and nothing else."""
        lines = [line for line in self.body.split("\n") if "not built" in line.lower()]
        self.assertTrue(any("not built yet" in line.lower() for line in lines), self.body[:2000])
        for line in lines:
            with self.subTest(line=line):
                lower = line.lower()
                self.assertTrue("release" in lower or "rule change" in lower, line)
                self.assertNotIn("bug fix", lower)
                self.assertNotIn("requirement change", lower)

    def test_bug_fix_and_requirement_change_are_built(self):
        """No line about the bug fix or the requirement change says it is not built."""
        for line in self.body.split("\n"):
            lower = line.lower()
            if "bug fix" in lower or "requirement change" in lower:
                with self.subTest(line=line):
                    self.assertNotIn("not built", lower)

    def test_no_longer_part_one_of_two(self):
        """Part 2 completes the skill: it no longer says it is part 1 of 2."""
        self.assertNotEqual(self.body, "")
        self.assertNotIn("part 1 of 2", self.body.lower())


if __name__ == "__main__":
    unittest.main()
