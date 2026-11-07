"""Scope table group (F05 design 5.1 and 13.1).

troyhook holds the write scopes as a table, troyhook.scopes.SCOPES (contract
section 5). This test keeps it equal to F04 design section 3 (copied below,
as troy-mode/dev/tests/test_roles.py copies it) and to the Write scope
section of each agent file, read at test time.

Write scope parsing follows test_roles.py convention 9: every non-blank line
is a "- " bullet naming its first backticked token; a line with the words
"path class" names a class, any other line a pattern; "- None" is an empty
scope.
"""

import importlib
import re
import sys
import unittest

from hook_helpers import AGENTS, HOOKS_DIR

PATH_CLASSES = ("config", "dependencies", "tests", "docs", "source")

# F04 design section 3 and F05 design 5.1, version 1.0.
EXPECTED = {
    "troy-architect": {"patterns": {"docs/architecture*.md", "docs/adr/**",
                                    "docs/features/*/design*.md"}, "classes": set()},
    "troy-interface-designer": {"patterns": {"docs/features/*/design*.md"}, "classes": set()},
    "troy-test-manager": {"patterns": {"docs/features/*/test-plan*.md",
                                       "docs/versions/*/test-plan*.md"}, "classes": set()},
    "troy-developer": {"patterns": set(), "classes": {"source", "dependencies"}},
    "troy-test-engineer": {"patterns": set(), "classes": {"tests", "dependencies"}},
    "troy-code-reviewer": {"patterns": set(), "classes": set()},
}

BACKTICKED = re.compile(r"`([^`]+)`")


def load_scopes():
    """Imports troyhook.scopes with troy-mode/hooks on sys.path (contract 5)."""
    if str(HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(HOOKS_DIR))
    return importlib.import_module("troyhook.scopes").SCOPES


def agent_scope(name):
    """Reads one agent file's Write scope section into patterns and classes.

    Args:
        name: The agent file's name without .md, for example troy-developer.

    Returns:
        {"patterns": set, "classes": set}.
    """
    lines = (AGENTS / f"{name}.md").read_text(encoding="utf-8").splitlines()
    inside, bullets = False, []
    for line in lines:
        if line.startswith("## "):
            inside = line.strip() == "## Write scope"
            continue
        if inside and line.strip():
            bullets.append(line.strip())
    scope = {"patterns": set(), "classes": set()}
    if bullets == ["- None"]:
        return scope
    for text in bullets:
        match = BACKTICKED.search(text)
        if match is None:
            raise AssertionError(f"{name}.md: Write scope line names nothing: {text!r}")
        kind = "classes" if "path class" in text else "patterns"
        scope[kind].add(match.group(1))
    return scope


class ScopeTableTests(unittest.TestCase):
    """SCOPES equals F04 section 3 and the agent files.

    Planted bug caught: the Developer's scope with the tests class (13.2),
    by test_table_equals_f04_section_3 and test_table_equals_agent_files.
    """

    @classmethod
    def setUpClass(cls):
        """Imports the table once."""
        cls.scopes = load_scopes()

    def table(self):
        """Returns SCOPES with sets for comparison, checking its shape on the way."""
        self.assertIsInstance(self.scopes, dict)
        result = {}
        for name, value in self.scopes.items():
            with self.subTest(agent=name):
                self.assertIsInstance(value, dict, name)
                self.assertEqual({"patterns", "classes"}, set(value), name)
                self.assertIsInstance(value["patterns"], tuple, name)
                self.assertIsInstance(value["classes"], tuple, name)
                for cls in value["classes"]:
                    self.assertIn(cls, PATH_CLASSES, name)
                self.assertEqual(len(set(value["patterns"])), len(value["patterns"]),
                                 f"{name}: repeated pattern")
                self.assertEqual(len(set(value["classes"])), len(value["classes"]),
                                 f"{name}: repeated class")
            result[name] = {"patterns": set(value["patterns"]), "classes": set(value["classes"])}
        return result

    def test_table_has_the_six_roles(self):
        """SCOPES is keyed by the six agent names without the plugin prefix."""
        self.assertEqual(set(EXPECTED), set(self.scopes))

    def test_table_equals_f04_section_3(self):
        """Each role's patterns and classes are those of F04 design section 3."""
        table = self.table()
        for name, expected in EXPECTED.items():
            with self.subTest(agent=name):
                self.assertEqual(expected, table.get(name))

    def test_table_equals_agent_files(self):
        """Each role's patterns and classes equal its agent file's Write scope section."""
        table = self.table()
        for name in EXPECTED:
            with self.subTest(agent=name):
                self.assertEqual(agent_scope(name), table.get(name), f"agents/{name}.md")

    def test_agent_files_equal_f04_section_3(self):
        """The agent files themselves still hold F04's scopes, so both sides are anchored."""
        for name, expected in EXPECTED.items():
            with self.subTest(agent=name):
                self.assertEqual(expected, agent_scope(name))

    def test_no_role_scope_holds_the_config_class(self):
        """No role may change a config path (design 5.1), so no scope names the class."""
        for name, value in self.table().items():
            with self.subTest(agent=name):
                self.assertNotIn("config", value["classes"])


if __name__ == "__main__":
    unittest.main()
