"""Upgrade group (F06 design 6, D54): one upgrade to the next plugin version, read by every test.

The project is set up with version 0.1.0, gets P01 and P02 in its rules
table, and is upgraded to a plugin with the changes of apply_upgrade_changes.
"""

import tomllib
import unittest

from init_helpers import (
    CONFIG, DATE, RECORD, RULES, UPGRADE_DATE, WORKFLOW, InitCase, make_plugin, owned_files,
    read_text, setup_project, sha256_lf,
)
from rules_helpers import (
    CHANGE_LOG_ROW, CHANGED_CHECK, CHANGED_HOOK, CHANGED_TEMPLATE, DROPPED_TEMPLATE,
    KEPT_TEMPLATE, NEW_PATTERN, NEW_TEMPLATE, NEW_VERSION, P_ROWS, R22, ROW, RULE_TEMPLATES,
    UPGRADE_STAGE, add_rows_after, apply_upgrade_changes, change_log_rows, front_matter,
    row_since, rule_rows,
)


def rest_of_table(text: str) -> list:
    """The non-blank lines of a rules file apart from rows, change log rows, version, and date."""
    return [line for line in text.split("\n")
            if line.strip() and not ROW.match(line) and not CHANGE_LOG_ROW.match(line)
            and not line.startswith(("version:", "updated:"))]


class UpgradeChangesTest(InitCase):
    """Upgrade from 0.1.0 to the next version with nothing edited in the project."""

    @classmethod
    def setUpClass(cls):
        """Sets up, adds P rows, and runs upgrade once on its own branch."""
        cls.old = make_plugin(hooks=True, version="0.1.0")
        cls.plugin = make_plugin(hooks=True)
        apply_upgrade_changes(cls.plugin)
        cls.project = project = setup_project(cls.old)
        for path in RULES:
            project.write(path, add_rows_after(project.read(path), "R21", P_ROWS[path]))
        project.commit_paths(list(RULES), "[rules] Add P01 and P02")
        cls.before = {path: project.read_bytes(path) for path in (CONFIG, ".gitignore", *RULES)}
        project.git("switch", "-q", "-c", f"troy-mode/upgrade-{NEW_VERSION}")
        cls.out = project.upgrade(cls.plugin)
        cls.status = project.status_paths()

    def report(self) -> dict:
        """The upgrade run's JSON report, after checking it exited 0."""
        return self.report_of(self.out, 0)

    def rules_before(self, path: str) -> str:
        """A rules file as it was before the upgrade."""
        return self.before[path].decode("utf-8")

    def test_upgrade_exits_zero_with_an_ok_report(self):
        """Upgrade exits 0 and reports the new version with no conflict or problem."""
        report = self.report()
        self.assertEqual(report["command"], "upgrade")
        self.assertIs(report["dry_run"], False)
        self.assertIs(report["changed"], True)
        self.assertEqual(report["version"], NEW_VERSION)
        self.assertEqual(report["conflicts"], [])
        self.assertEqual(report["problems"], [])
        self.assertIsNone(report["hooks_path"])
        self.assertIsNone(report["email"])

    def test_upgrade_stages_exactly_the_paths_it_changed(self):
        """stage lists every changed path, deletions included, and git status agrees."""
        self.assertEqual(self.report()["stage"], UPGRADE_STAGE)
        self.assertEqual(self.status, set(UPGRADE_STAGE))

    def test_upgrade_replaces_unchanged_owned_files(self):
        """Owned files whose hash still matches the record get the plugin's new content."""
        actions, new = self.actions_of(self.report()), owned_files(self.plugin)
        for path in (CHANGED_TEMPLATE, CHANGED_CHECK, CHANGED_HOOK, WORKFLOW):
            with self.subTest(path=path):
                self.assertEqual(actions[path], "replace")
                self.assertEqual(self.project.read_bytes(path), new[path])

    def test_upgrade_keeps_an_owned_file_the_plugin_did_not_change(self):
        """An owned file equal to the plugin's is kept and not staged."""
        report = self.report()
        self.assertEqual(self.actions_of(report)[KEPT_TEMPLATE], "keep")
        self.assertNotIn(KEPT_TEMPLATE, report["stage"])
        self.assertEqual(self.project.read_bytes(KEPT_TEMPLATE),
                         owned_files(self.old)[KEPT_TEMPLATE])

    def test_upgrade_creates_and_records_a_new_template(self):
        """A template the plugin added is created and gets a hash in the record."""
        self.assertEqual(self.actions_of(self.report())[NEW_TEMPLATE], "create")
        content = owned_files(self.plugin)[NEW_TEMPLATE]
        self.assertEqual(self.project.read_bytes(NEW_TEMPLATE), content)
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(record["files"][NEW_TEMPLATE], sha256_lf(content))

    def test_upgrade_deletes_a_dropped_template(self):
        """A recorded file the plugin dropped is deleted and leaves the record."""
        self.assertEqual(self.actions_of(self.report())[DROPPED_TEMPLATE], "delete")
        self.assertEqual(self.project.files(DROPPED_TEMPLATE), {})
        self.assertNotIn(DROPPED_TEMPLATE, tomllib.loads(self.project.read(RECORD))["files"])

    def test_upgrade_lists_only_the_replaced_hook_as_executable(self):
        """executable holds the staged hook file, and no unchanged one."""
        self.assertEqual(self.report()["executable"], [CHANGED_HOOK])

    def test_upgrade_replaces_r_rows_and_keeps_their_since_dates(self):
        """Every R row is the template's row, with the Since date the project had."""
        self.report()
        for path, template in RULE_TEMPLATES.items():
            with self.subTest(path=path):
                since = {row[2:5]: row_since(row) for row in rule_rows(self.rules_before(path))}
                template_rows = rule_rows(read_text(self.plugin, f"troy-mode/templates/{template}"))
                expected = [row.replace("{{init-date}}", since.get(row[2:5], UPGRADE_DATE))
                            for row in template_rows]
                actual = [row for row in rule_rows(self.project.read(path)) if row[2] == "R"]
                self.assertEqual(actual, expected)

    def test_upgrade_dates_a_new_rule_with_the_upgrade_date(self):
        """R22, new in the template, has the upgrade date; R01 keeps the setup date."""
        self.report()
        for path in RULES:
            with self.subTest(path=path):
                rows = {row[2:5]: row for row in rule_rows(self.project.read(path))}
                self.assertEqual(rows["R22"], R22[path].replace("{{init-date}}", UPGRADE_DATE))
                self.assertEqual(row_since(rows["R01"]), DATE)

    def test_upgrade_changes_the_text_of_a_changed_r_row(self):
        """R03's new wording from the template replaces the old one."""
        self.report()
        wording = {"docs/rules.md": "changes at most 400 lines",
                   "docs/rules.zh-CN.md": "最多改动 400 行"}
        for path, text in wording.items():
            with self.subTest(path=path):
                rows = {row[2:5]: row for row in rule_rows(self.project.read(path))}
                self.assertIn(text, rows["R03"])

    def test_upgrade_keeps_p_rows_after_the_r_rows_in_order(self):
        """P01 and P02 stay in both tables, right after R22, in their order."""
        self.report()
        expected_ids = [f"R{n:02d}" for n in range(1, 23)] + ["P01", "P02"]
        for path in RULES:
            with self.subTest(path=path):
                rows = rule_rows(self.project.read(path))
                self.assertEqual([row[2:5] for row in rows], expected_ids)
                self.assertEqual(rows[-2:], P_ROWS[path])

    def test_upgrade_raises_the_version_one_minor_step_in_both_languages(self):
        """Both rules files go from version 1.0 to 1.1 and are dated the upgrade day."""
        self.report()
        en, zh = (front_matter(self.project.read(path)) for path in RULES)
        self.assertEqual((en["version"], zh["version"]), ("1.1", "1.1"))
        self.assertEqual((en["updated"], zh["updated"]), (UPGRADE_DATE, UPGRADE_DATE))

    def test_upgrade_adds_a_change_log_row_in_both_languages(self):
        """Each change log keeps its 1.0 row and gains one 1.1 row dated the upgrade day."""
        self.report()
        for path in RULES:
            with self.subTest(path=path):
                old_rows = change_log_rows(self.rules_before(path))
                rows = change_log_rows(self.project.read(path))
                self.assertEqual(len(rows), len(old_rows) + 1)
                self.assertLessEqual(set(old_rows), set(rows))
                new_row = next(row for row in rows if row not in old_rows)
                self.assertRegex(new_row, rf"^\| 1\.1 \| {UPGRADE_DATE} \| \S")

    def test_upgrade_leaves_the_rest_of_the_rules_table_alone(self):
        """Headings, text, and other front matter of both rules files do not change."""
        self.report()
        for path in RULES:
            with self.subTest(path=path):
                self.assertEqual(rest_of_table(self.project.read(path)),
                                 rest_of_table(self.rules_before(path)))

    def test_upgrade_never_changes_the_config(self):
        """config.toml keeps every byte and is not staged."""
        report = self.report()
        self.assertEqual(self.project.read_bytes(CONFIG), self.before[CONFIG])
        self.assertNotIn(CONFIG, report["stage"])
        self.assertIn(self.actions_of(report).get(CONFIG), (None, "keep"))

    def test_upgrade_reports_a_new_pack_pattern_as_a_config_difference(self):
        """differences names config.toml and the pack pattern it lacks."""
        found = [item for item in self.report()["differences"] if item["path"] == CONFIG]
        self.assertNotEqual(found, [])
        self.assertIn(NEW_PATTERN, " ".join(item["message"] for item in found))

    def test_upgrade_leaves_gitignore_alone(self):
        """.gitignore belongs to the project once written."""
        self.assertEqual(self.project.read_bytes(".gitignore"), self.before[".gitignore"])
        self.assertNotIn(".gitignore", self.report()["stage"])

    def test_upgrade_rewrites_the_install_record(self):
        """The record has the new version, both step dates, and the new owned file list."""
        self.assertEqual(self.actions_of(self.report())[RECORD], "edit")
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(record["plugin"]["version"], NEW_VERSION)
        self.assertEqual(record["steps"], {"setup": DATE, "upgrade": UPGRADE_DATE})
        self.assertEqual(sorted(record["files"]), sorted(owned_files(self.plugin)))

    def test_upgrade_record_hashes_match_the_files_after_upgrade(self):
        """Each [files] hash is the SHA-256 of the file as the upgrade left it."""
        self.report()
        record = tomllib.loads(self.project.read(RECORD))
        for path, digest in record["files"].items():
            with self.subTest(path=path):
                self.assertEqual(digest, sha256_lf(self.project.read_bytes(path)))


if __name__ == "__main__":
    unittest.main()
