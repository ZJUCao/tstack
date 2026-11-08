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

    def test_only_rule_change_is_not_built(self):
        """``not built yet`` names the rule change (F09), and nothing else.

        F07 allowed the version release here too; F08 builds it (F08 note,
        section 12), so a "not built" line names the Rule change flow or F09.
        """
        lines = [line for line in self.body.split("\n") if "not built" in line.lower()]
        self.assertTrue(any("not built yet" in line.lower() and "rule change" in line.lower()
                            for line in lines), self.body[:2000])
        for line in lines:
            with self.subTest(line=line):
                lower = line.lower()
                self.assertTrue("rule change" in lower or "f09" in lower, line)
                self.assertNotIn("version release", lower)
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


def routing_rows(body: str) -> list:
    """The routing table's rows, as lists of trimmed cells.

    Args:
        body: The skill's text after the front matter.

    Returns:
        The rows of the first table under ``## Routing``, header and separator left out.
    """
    lines = body.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == "## Routing"), None)
    if start is None:
        return []
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.strip().startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return [row for row in rows[2:] if row]


class VersionReleaseSkillTests(unittest.TestCase):
    """F08's texts in the entry skill (F08 design 5, interface note section 12)."""

    COMMANDS = ("release-test", "accept-version", "release-notes", "retro")
    TITLES = ("[docs] Add the <version> test plan", "[<version> tests] <summary>",
              "[docs] Release <tag>", "[docs] Record Troy's acceptance of <tag>")
    HEADINGS = ("Release test, run <n>:", "Release test by Troy, run <n>:",
                "Waiting for Troy: accept <tag>", "Retrospective: <tag>",
                "Bug deferred by Troy: #<n>")

    @classmethod
    def setUpClass(cls):
        """Reads SKILL.md once; an empty text when it does not exist yet."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.body = split_skill(text)[1]

    def test_names_every_new_engine_command(self):
        """Each command of F08 design 3.1 as ``troy_flow.py <command>``."""
        for command in self.COMMANDS:
            with self.subTest(command=command):
                self.assertRegex(self.body, re.escape(f"troy_flow.py {command}") + r"(?![\w-])")

    def test_names_the_release_titles(self):
        """The test plan, version tests, release, and record titles."""
        for title in self.TITLES:
            with self.subTest(title=title):
                self.assertIn(title, self.body)

    def test_names_the_github_release_with_its_target(self):
        """``gh release create`` on one line with ``--target`` (D73)."""
        lines = [line for line in self.body.split("\n") if "gh release create" in line]
        self.assertTrue(any("--target" in line for line in lines), lines)

    def test_names_the_comment_headings(self):
        """F08's comment headings (design 5.5 to 5.8 and 7)."""
        for heading in self.HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, self.body)

    def test_names_the_version_tests_folder(self):
        """``version-tests/``, where TE5's tests live (design 5.3)."""
        self.assertIn("version-tests/", self.body)

    def test_release_routing_row_is_built(self):
        """The "release v0.1" row routes to the Version release and does not say "not built"."""
        rows = [row for row in routing_rows(self.body) if "release v0.1" in row[0]]
        self.assertEqual(len(rows), 1, routing_rows(self.body))
        text = " | ".join(rows[0])
        self.assertIn("Version release", text)
        self.assertNotIn("not built", text.lower())

    def test_rule_routing_row_is_still_not_built(self):
        """The "add a rule" row still says the Rule change flow is not built (F09)."""
        rows = [row for row in routing_rows(self.body) if "add a rule" in row[0]]
        self.assertEqual(len(rows), 1, routing_rows(self.body))
        text = " | ".join(rows[0])
        self.assertIn("Rule change", text)
        self.assertIn("not built", text.lower())


if __name__ == "__main__":
    unittest.main()
