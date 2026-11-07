"""Plugin files group (F05 design section 9, D45, and 13.1).

A PreToolUse call on Read, Glob, or Grep gets ``allow`` when it is in a
troy-mode project and its path lies inside CLAUDE_PLUGIN_ROOT, and nothing
otherwise. The hook reads CLAUDE_PLUGIN_ROOT from its environment on each
call (contract section 6); the tests point it at a fake installed plugin
folder.
"""

import os
import unittest
from pathlib import Path

from hook_helpers import (
    DEV, GP, IS_WINDOWS, MAIN, PLUGIN_ROOT, HookTestCase, Project, read_call, start_call,
    write_file,
)

SKILL = PLUGIN_ROOT / "skills" / "technical-writing" / "SKILL.md"
TEMPLATE = PLUGIN_ROOT / "troy-mode" / "templates" / "design.md"
# Paths outside the plugin root that a careless check could take for inside:
# a sibling version folder that shares the root's name as a prefix, an older
# version of the same plugin, and a path that leaves the root with "..".
SIBLING = Path(str(PLUGIN_ROOT) + "-other") / "skills" / "technical-writing" / "SKILL.md"
OLD_VERSION = PLUGIN_ROOT.parent / "8.0.0" / "skills" / "technical-writing" / "SKILL.md"
ESCAPE = os.path.join(str(PLUGIN_ROOT), "..", "8.0.0", "skills", "technical-writing", "SKILL.md")


class PluginReadTests(HookTestCase):
    """Reads inside CLAUDE_PLUGIN_ROOT are allowed; all others get nothing."""

    @classmethod
    def setUpClass(cls):
        """Writes the plugin files and builds a troy-mode and a plain project."""
        for path in (SKILL, TEMPLATE, SIBLING, OLD_VERSION):
            write_file(path.parent, path.name, "# File\n")
        cls.project = Project()
        cls.plain = Project(troy_mode=False)
        cls.addClassCleanup(cls.project.close)
        cls.addClassCleanup(cls.plain.close)
        start_call(cls.project, DEV).run()

    def test_read_inside_the_plugin_root_is_allowed(self):
        """Read, Glob, and Grep inside the root get allow, for a role and the main session."""
        cases = ((DEV, "Read", SKILL), (DEV, "Read", TEMPLATE), (MAIN, "Read", SKILL),
                 (GP, "Read", SKILL), (DEV, "Glob", PLUGIN_ROOT / "skills"),
                 (DEV, "Grep", PLUGIN_ROOT / "troy-mode"))
        for caller, tool, path in cases:
            with self.subTest(caller=caller.label, tool=tool, path=str(path)):
                self.assert_allowed_read(read_call(self.project, caller, path, tool=tool).run())

    def test_read_outside_the_plugin_root_gets_nothing(self):
        """A sibling folder, an older version, a .. escape, and a project file get nothing.

        Planted bug caught: a plugin read allowed outside CLAUDE_PLUGIN_ROOT (13.2).
        """
        cases = (("Read", SIBLING), ("Read", OLD_VERSION), ("Read", ESCAPE),
                 ("Read", self.project.path("README.md")), ("Glob", PLUGIN_ROOT.parent),
                 ("Grep", Path(str(PLUGIN_ROOT) + "-other")))
        for tool, path in cases:
            with self.subTest(tool=tool, path=str(path)):
                self.assert_silent(read_call(self.project, DEV, path, tool=tool).run())

    def test_read_in_a_project_outside_troy_mode_gets_nothing(self):
        """The same plugin file read from a project without .troy-mode/ gets nothing."""
        self.assert_silent(read_call(self.plain, DEV, SKILL).run())
        self.assert_silent(read_call(self.plain, MAIN, SKILL).run())

    def test_read_without_plugin_root_gets_nothing(self):
        """With CLAUDE_PLUGIN_ROOT unset, nothing is allowed."""
        self.assert_silent(read_call(self.project, DEV, SKILL, plugin_root=None).run())

    def test_plugin_root_is_read_on_each_call(self):
        """A new plugin version folder works as soon as CLAUDE_PLUGIN_ROOT names it."""
        old_root = OLD_VERSION.parents[2]
        self.assert_allowed_read(read_call(self.project, DEV, OLD_VERSION,
                                           plugin_root=old_root).run())
        self.assert_silent(read_call(self.project, DEV, SKILL, plugin_root=old_root).run())

    @unittest.skipUnless(IS_WINDOWS, "Windows path forms")
    def test_windows_forms_inside_the_root_are_allowed(self):
        """Forward slashes and a different case still lie inside the root on Windows."""
        for path in (SKILL.as_posix(), str(SKILL).upper(), str(SKILL).lower()):
            with self.subTest(path=path):
                self.assert_allowed_read(read_call(self.project, DEV, path).run())


if __name__ == "__main__":
    unittest.main()
