"""The idea template (F15 design 5.1, 11 "F06 troy-init", 12, 13.1; interface note section 7).

Setup and upgrade write ``.github/ISSUE_TEMPLATE/idea.md`` from the plugin's
``troy-mode/templates/idea-issue.md``, as they write the PR template, under
the same hash rule: upgrade replaces it only when the project's copy is
unchanged since troy-init wrote it, and stops on it otherwise.
"""

import tomllib
import unittest

from init_helpers import (
    IDEA_SOURCE, IDEA_TEMPLATE, RECORD, InitCase, Project, lf, make_plugin, read_text,
    setup_project, sha256_lf, shared_plugin, write_text,
)

OWN_TEXT = "# Our own idea template\n"
LOCAL_NOTE = "\n<!-- A line this project added. -->\n"
NEW_TEMPLATES = ("idea-issue.md", "progress-issue.md", "device-test-issue.md")


def plugin_text(plugin, rel: str) -> bytes:
    """A plugin file's bytes with LF endings, or b"" when it is missing."""
    path = plugin / rel
    return lf(path.read_bytes()) if path.is_file() else b""


class SetupTest(InitCase):
    """Setup writes the idea template and copies the three new templates."""

    @classmethod
    def setUpClass(cls):
        """Runs setup once on a fresh project."""
        cls.plugin = shared_plugin(hooks=True)
        cls.project = Project()
        cls.out = cls.project.setup(cls.plugin)

    def test_plugin_has_the_idea_template(self):
        """The plugin holds ``troy-mode/templates/idea-issue.md``."""
        self.assertTrue((self.plugin / IDEA_SOURCE).is_file())

    def test_setup_writes_the_idea_template(self):
        """``.github/ISSUE_TEMPLATE/idea.md`` is the plugin's file, created and staged."""
        report = self.report_of(self.out, 0)
        self.assertEqual(self.actions_of(report).get(IDEA_TEMPLATE), "create")
        self.assertIn(IDEA_TEMPLATE, report["stage"])
        self.assertNotEqual(plugin_text(self.plugin, IDEA_SOURCE), b"")
        self.assertEqual(lf(self.project.read_bytes(IDEA_TEMPLATE)),
                         plugin_text(self.plugin, IDEA_SOURCE))

    def test_install_record_holds_its_hash(self):
        """The install record's ``[files]`` holds the template with its hash."""
        self.report_of(self.out, 0)
        self.assertTrue((self.project.root / IDEA_TEMPLATE).is_file(), "setup wrote no template")
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(record["files"].get(IDEA_TEMPLATE),
                         sha256_lf(self.project.read_bytes(IDEA_TEMPLATE)))

    def test_setup_copies_the_new_templates(self):
        """The three new templates are copied under ``.troy-mode/templates/``."""
        self.report_of(self.out, 0)
        for name in NEW_TEMPLATES:
            with self.subTest(template=name):
                rel = f".troy-mode/templates/{name}"
                self.assertTrue((self.project.root / rel).is_file(), rel)
                self.assertEqual(lf(self.project.read_bytes(rel)),
                                 plugin_text(self.plugin, f"troy-mode/templates/{name}"))

    def test_existing_idea_template_is_a_conflict(self):
        """A project's own idea template stops setup and keeps its text (F06 design 4.1)."""
        project = Project(base_files={IDEA_TEMPLATE: OWN_TEXT})
        before = project.snapshot()
        report = self.report_of(project.setup(self.plugin), 1)
        self.assertEqual([item["path"] for item in report["conflicts"]], [IDEA_TEMPLATE])
        self.assert_unchanged(before, project.snapshot())


class UpgradeTest(InitCase):
    """Upgrade replaces the idea template only when it is unchanged (F06 design 6)."""

    @classmethod
    def setUpClass(cls):
        """An old plugin, a new one whose idea template changed, and one where it did not."""
        cls.old = make_plugin(hooks=True, version="0.1.0")
        cls.same = make_plugin(hooks=True)
        cls.plugin = make_plugin(hooks=True)
        if (cls.plugin / IDEA_SOURCE).is_file():
            write_text(cls.plugin, IDEA_SOURCE,
                       read_text(cls.plugin, IDEA_SOURCE) + "<!-- New in this version. -->\n")

    def test_new_plugin_changed_the_template(self):
        """The test's own setup: the new plugin's template differs from the old one's."""
        self.assertNotEqual(plugin_text(self.plugin, IDEA_SOURCE), b"")
        self.assertNotEqual(plugin_text(self.plugin, IDEA_SOURCE),
                            plugin_text(self.old, IDEA_SOURCE))

    def test_unchanged_template_is_replaced(self):
        """The project's copy as setup wrote it: replaced with the new plugin's."""
        project = setup_project(self.old)
        report = self.report_of(project.upgrade(self.plugin), 0)
        self.assertEqual(self.actions_of(report).get(IDEA_TEMPLATE), "replace")
        self.assertIn(IDEA_TEMPLATE, report["stage"])
        self.assertEqual(lf(project.read_bytes(IDEA_TEMPLATE)),
                         plugin_text(self.plugin, IDEA_SOURCE))
        record = tomllib.loads(project.read(RECORD))
        self.assertEqual(record["files"].get(IDEA_TEMPLATE),
                         sha256_lf(project.read_bytes(IDEA_TEMPLATE)))

    def test_edited_template_stops_the_upgrade(self):
        """Pair: the project changed its copy: a conflict, exit 1, and nothing changes."""
        project = setup_project(self.old)
        self.assertTrue((project.root / IDEA_TEMPLATE).is_file(), "setup wrote no template")
        project.write(IDEA_TEMPLATE, project.read(IDEA_TEMPLATE) + LOCAL_NOTE)
        project.commit_paths([IDEA_TEMPLATE], "[rules] Change the idea template by hand")
        before = project.snapshot()
        report = self.report_of(project.upgrade(self.plugin), 1)
        self.assertEqual([item["path"] for item in report["conflicts"]], [IDEA_TEMPLATE])
        self.assert_unchanged(before, project.snapshot())

    def test_template_the_plugin_did_not_change_is_kept(self):
        """The same template in the new version: kept and not staged."""
        project = setup_project(self.old)
        report = self.report_of(project.upgrade(self.same), 0)
        self.assertEqual(self.actions_of(report).get(IDEA_TEMPLATE), "keep")
        self.assertNotIn(IDEA_TEMPLATE, report["stage"])

    def test_project_set_up_before_f15_gets_the_template(self):
        """No template and no record of it, as before F15: upgrade creates it (design 12)."""
        project = setup_project(self.old)
        self.assertTrue((project.root / IDEA_TEMPLATE).is_file(), "setup wrote no template")
        project.git("rm", "-q", "--", IDEA_TEMPLATE)
        lines = project.read(RECORD).split("\n")
        project.write(RECORD, "\n".join(line for line in lines if IDEA_TEMPLATE not in line))
        project.commit_paths([RECORD], "[rules] A project set up before F15")
        report = self.report_of(project.upgrade(self.plugin), 0)
        self.assertEqual(self.actions_of(report).get(IDEA_TEMPLATE), "create")
        self.assertEqual(lf(project.read_bytes(IDEA_TEMPLATE)),
                         plugin_text(self.plugin, IDEA_SOURCE))
        record = tomllib.loads(project.read(RECORD))
        self.assertEqual(record["files"].get(IDEA_TEMPLATE),
                         sha256_lf(project.read_bytes(IDEA_TEMPLATE)))


if __name__ == "__main__":
    unittest.main()
