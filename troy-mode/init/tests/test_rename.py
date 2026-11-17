"""Rename group (F19 design 5.1, 8, and 11.1, D195): troy-init after the plugin became tstack.

troy-init reads the plugin's name from plugin.json, as it reads the version,
and its change-log rows and text reports use both. Upgrade also rewrites two
comment lines that setup and the language step wrote before F19, in
.troy-mode/config.toml and pyproject.toml, but only when a line is exactly
what troy-init wrote (design 8). After the rename, setup and the language
step write the new lines themselves, so these tests write the old line into
the project to stand for a project set up by version 0.5.0.

F19 planted bugs (design 11.3) caught here:

- "the upgrade rewriting an edited comment line":
  CommentLineUpgradeTest.test_edited_lines_are_left_alone_and_listed and
  test_each_file_is_judged_on_its_own.
- "troy-init's change-log line with a fixed name":
  RenamedPluginTest.test_upgrade_change_log_rows_name_the_plugin_and_its_version.
- "plugin.json's name left": RenamedPluginTest.test_upgrade_change_log_rows_name_tstack.
"""

import json
import re
import unittest
from pathlib import Path

from init_helpers import (
    CONFIG, DATE, EMAIL, RULES, InitCase, Project, lf, make_plugin, plugin_version, read_text,
    set_name, setup_project, shared_plugin, write_text,
)
from lang_helpers import lang_done, reset_project
from rules_helpers import NEW_VERSION, apply_upgrade_changes, change_log_rows

OLD = "troy" + "-pstack"  # the plugin's name before tstack (F19 design 4.1)
OLD_NAME = re.compile(r"troy[-_ ]?pstack", re.IGNORECASE)
PYPROJECT = "pyproject.toml"
OTHER_NAME = "otherstack"

# Design 8: the fixed table of the two comment lines, as (old line, new line).
LINES = {
    CONFIG: (f"# Set by the language pack (troy-mode/lang/ in {OLD}), for example:",
             "# Set by the language pack (troy-mode/lang/ in tstack), for example:"),
    PYPROJECT: (f"# troy-check is checked in {OLD}, not in the project.",
                "# troy-check is checked in tstack, not in the project."),
}
OLD_LINES = {path: pair[0] for path, pair in LINES.items()}
NEW_LINES = {path: pair[1] for path, pair in LINES.items()}
# Lines someone changed that still name the old plugin; the second in another case.
EDITED_LINES = {
    CONFIG: f"# Set by the language pack (troy-mode/lang/ in {OLD}), e.g.:",
    PYPROJECT: f"# troy-check is checked in {OLD.title()}, not here.",
}
# Design 5.1: troy-init's change-log rows, by rules file.
ROW_TEXT = {"docs/rules.md": "troy-mode's rules brought up to {name} {version}.",
            "docs/rules.zh-CN.md": "troy-mode 的规则更新到 {name} {version}。"}
SIMULATED = "[rules] Write the comment lines as version 0.5.0 left them"


def put_line(project: Project, path: str, line: str, crlf: bool = False) -> None:
    """Puts one line in place of the file's comment line, old or new, and sets line endings.

    Args:
        project: The project.
        path: CONFIG or PYPROJECT.
        line: The line to write in place of whichever of the two lines is there.
        crlf: Whether to write the whole file with CRLF line endings.
    """
    text = project.read(path)
    old, new = LINES[path]
    lines = text.split("\n")
    found = [i for i, item in enumerate(lines) if item in (old, new)]
    if len(found) != 1:
        raise AssertionError(f"{path} holds the comment line {len(found)} times, not once")
    lines[found[0]] = line
    data = "\n".join(lines).encode("utf-8")
    (project.root / path).write_bytes(data.replace(b"\n", b"\r\n") if crlf else data)


def commit_lines(project: Project, lines: dict, crlf: bool = False) -> dict:
    """Writes the lines into their files, commits them, and returns each file's bytes."""
    for path, line in lines.items():
        put_line(project, path, line, crlf)
    project.git("add", "--", *lines)
    project.git("commit", "-q", "--allow-empty", "-m", SIMULATED)
    return {path: project.read_bytes(path) for path in lines}


def change_cell(row: str) -> str:
    """The Change cell of a change-log row ``| version | date | change |``."""
    return row.strip().strip("|").split("|")[2].strip()


def new_rows(before: str, after: str) -> list:
    """The change-log rows a rules file gained."""
    old = change_log_rows(before)
    return [row for row in change_log_rows(after) if row not in old]


def without_key(plugin: Path, key: str) -> None:
    """Removes one key from a plugin's plugin.json."""
    data = json.loads(read_text(plugin, ".claude-plugin/plugin.json"))
    del data[key]
    write_text(plugin, ".claude-plugin/plugin.json", json.dumps(data, indent=2) + "\n")


class CommentLineCase(InitCase):
    """Assertions on the two comment lines after an upgrade."""

    def difference_paths(self, report: dict) -> set:
        """The paths the report's differences name."""
        return {item["path"] for item in report["differences"]}

    def assert_rewritten(self, project: Project, report: dict, path: str, before: bytes) -> None:
        """Only the old line became the new one; the file is edited and staged, not listed."""
        old, new = LINES[path]
        self.assertEqual(before.count(old.encode("utf-8")), 1, f"{path}: the premise")
        after = project.read_bytes(path)
        self.assertEqual(after, before.replace(old.encode("utf-8"), new.encode("utf-8")))
        self.assertIsNone(OLD_NAME.search(after.decode("utf-8")), f"{path} names the old plugin")
        self.assertEqual(self.actions_of(report).get(path), "edit")
        self.assertIn(path, report["stage"])
        self.assertIn(path, project.status_paths())
        self.assertNotIn(path, self.difference_paths(report))

    def assert_left_alone(self, project: Project, report: dict, path: str, before: bytes,
                          listed: bool) -> None:
        """The file keeps every byte and is not staged; listed says whether differences name it."""
        self.assertEqual(project.read_bytes(path), before)
        self.assertIn(self.actions_of(report).get(path), (None, "keep"))
        self.assertNotIn(path, report["stage"])
        self.assertEqual(path in self.difference_paths(report), listed,
                         f"{path} in differences: {report['differences']}")


class CommentLineUpgradeTest(CommentLineCase):
    """Upgrade of a Python project whose two comment lines are set per test (design 8)."""

    @classmethod
    def setUpClass(cls):
        """Adds the Python pack with 0.1.0; the upgrade goes to the next version."""
        cls.old = make_plugin(hooks=True, version="0.1.0")
        cls.plugin = make_plugin(hooks=True, version=NEW_VERSION)
        cls.project, _, _ = lang_done(cls.old, "python")
        cls.lang_sha = cls.project.git("rev-parse", "HEAD").strip()

    def upgraded(self, lines: dict, crlf: bool = False) -> tuple:
        """Writes the lines on the language commit, commits, and upgrades.

        Returns:
            The project, each file's bytes before the upgrade, and the report.
        """
        project = self.project
        reset_project(project, self.lang_sha)
        before = commit_lines(project, lines, crlf)
        return project, before, self.report_of(project.upgrade(self.plugin), 0)

    def test_exact_old_lines_are_rewritten_and_staged(self):
        """Each file holding the old line exactly gets the new line and nothing else changes."""
        project, before, report = self.upgraded(OLD_LINES)
        for path in LINES:
            with self.subTest(path=path):
                self.assert_rewritten(project, report, path, before[path])

    def test_exact_old_lines_in_crlf_files_are_rewritten_and_keep_crlf(self):
        """In CRLF files the old line, compared without its \\r, is rewritten; CRLF stays."""
        project, before, report = self.upgraded(OLD_LINES, crlf=True)
        for path in LINES:
            with self.subTest(path=path):
                self.assertEqual(before[path].count(b"\n"), before[path].count(b"\r\n"))
                self.assert_rewritten(project, report, path, before[path])
                after = project.read_bytes(path)
                self.assertEqual(after.count(b"\n"), after.count(b"\r\n"), "a line lost its CR")

    def test_edited_lines_are_left_alone_and_listed(self):
        """A line someone changed, still naming the old plugin in any case, stays and is listed.

        F19 planted bug caught: the upgrade rewriting an edited comment line.
        """
        project, before, report = self.upgraded(EDITED_LINES)
        for path in LINES:
            with self.subTest(path=path):
                self.assert_left_alone(project, report, path, before[path], listed=True)

    def test_new_lines_get_no_action_or_difference(self):
        """Files that already hold the new lines are kept, unstaged, and not listed."""
        project, before, report = self.upgraded(NEW_LINES)
        for path in LINES:
            with self.subTest(path=path):
                self.assert_left_alone(project, report, path, before[path], listed=False)

    def test_each_file_is_judged_on_its_own(self):
        """An exact config line is rewritten; an edited pyproject.toml line stays and is listed.

        F19 planted bug caught: the upgrade rewriting an edited comment line.
        """
        lines = {CONFIG: OLD_LINES[CONFIG], PYPROJECT: EDITED_LINES[PYPROJECT]}
        project, before, report = self.upgraded(lines)
        self.assert_rewritten(project, report, CONFIG, before[CONFIG])
        self.assert_left_alone(project, report, PYPROJECT, before[PYPROJECT], listed=True)


class CommentLineWithoutPackTest(CommentLineCase):
    """Upgrade of a project with no language pack, so it has no pyproject.toml."""

    def test_config_line_is_rewritten_and_a_missing_pyproject_gets_nothing(self):
        """The config's exact old line is rewritten; no pyproject.toml is made, named, or listed."""
        project = setup_project(make_plugin(hooks=True, version="0.1.0"))
        before = commit_lines(project, {CONFIG: OLD_LINES[CONFIG]})
        self.assertEqual(project.files(PYPROJECT), {}, "the premise: no pyproject.toml")
        report = self.report_of(project.upgrade(make_plugin(hooks=True, version=NEW_VERSION)), 0)
        self.assert_rewritten(project, report, CONFIG, before[CONFIG])
        self.assertEqual(project.files(PYPROJECT), {})
        self.assertNotIn(PYPROJECT, self.actions_of(report))
        self.assertNotIn(PYPROJECT, report["stage"])
        self.assertNotIn(PYPROJECT, self.difference_paths(report))


class RenamedPluginTest(InitCase):
    """troy-init takes the plugin's name from plugin.json (design 5.1)."""

    def upgrade_rows(self, plugin: Path) -> dict:
        """Sets up with 0.1.0, upgrades with the plugin, and returns each rules file's new rows."""
        project = setup_project(make_plugin(hooks=True, version="0.1.0"))
        before = {path: project.read(path) for path in RULES}
        self.report_of(project.upgrade(plugin), 0)
        return {path: new_rows(before[path], project.read(path)) for path in RULES}

    def assert_rows(self, rows: dict, name: str, version: str) -> None:
        """Each rules file gained one row whose Change cell names the plugin and version."""
        for path in RULES:
            with self.subTest(path=path):
                self.assertEqual(len(rows[path]), 1, rows[path])
                expected = ROW_TEXT[path].format(name=name, version=version)
                self.assertEqual(change_cell(rows[path][0]), expected)

    def test_upgrade_change_log_rows_name_the_plugin_and_its_version(self):
        """A plugin.json named otherstack gives rows that name otherstack and its version.

        F19 planted bug caught: troy-init's change-log line with a fixed name.
        """
        plugin = make_plugin(hooks=True, name=OTHER_NAME)
        apply_upgrade_changes(plugin)
        self.assert_rows(self.upgrade_rows(plugin), OTHER_NAME, NEW_VERSION)

    def test_upgrade_change_log_rows_name_tstack(self):
        """With the repository's own plugin.json, the rows name tstack (design 8).

        F19 planted bug caught: plugin.json's name left.
        """
        plugin = make_plugin(hooks=True)
        apply_upgrade_changes(plugin)
        self.assert_rows(self.upgrade_rows(plugin), "tstack", NEW_VERSION)

    def test_setup_text_report_names_the_plugin_and_its_version(self):
        """Without --json, setup's report starts with "troy-init setup, <name> <version>"."""
        plugin = make_plugin(hooks=True, name=OTHER_NAME)
        out = Project().run(plugin, "setup", "--email", EMAIL, "--date", DATE)
        self.assertEqual(out.code, 0, out.describe())
        first = (out.stdout.splitlines() or [""])[0]
        self.assertEqual(first, f"troy-init setup, {OTHER_NAME} {plugin_version(plugin)}")

    def test_upgrade_text_report_names_the_plugin_and_its_version(self):
        """Without --json, upgrade's report starts with "troy-init upgrade, <name> <version>"."""
        project = setup_project(make_plugin(hooks=True, version="0.1.0"))
        plugin = make_plugin(hooks=True, version=NEW_VERSION, name=OTHER_NAME)
        out = project.run(plugin, "upgrade", "--date", "2026-11-20")
        self.assertEqual(out.code, 0, out.describe())
        first = (out.stdout.splitlines() or [""])[0]
        self.assertEqual(first, f"troy-init upgrade, {OTHER_NAME} {NEW_VERSION}")

    def test_plugin_json_without_a_usable_name_stops_like_one_without_a_version(self):
        """No name, an empty one, a number, or null stops setup as a missing version does.

        Each run exits with the missing version's code, which is not 0, says
        why, and leaves the project as it was.
        """
        no_version = make_plugin(hooks=True)
        without_key(no_version, "version")
        project = Project()
        before = project.snapshot()
        expected = project.setup(no_version)
        self.assertIn(expected.code, (1, 2), expected.describe())
        self.assert_unchanged(before, project.snapshot())
        no_name = make_plugin(hooks=True)
        without_key(no_name, "name")
        plugins = {"missing": no_name}
        for label, value in (("empty", ""), ("number", 42), ("null", None)):
            plugins[label] = make_plugin(hooks=True)
            set_name(plugins[label], value)
        for label, plugin in plugins.items():
            with self.subTest(name=label):
                project = Project()
                before = project.snapshot()
                out = project.setup(plugin)
                self.assertEqual(out.code, expected.code, out.describe())
                self.assertNotEqual((out.stdout + out.stderr).strip(), "")
                self.assert_unchanged(before, project.snapshot())

    def test_a_new_project_names_no_old_plugin(self):
        """After setup and the Python step, no file in the project names the old plugin.

        Design 8: the files troy-init writes into projects carry the new text,
        so a new project has nothing for a code search to find.
        """
        project, _, _ = lang_done(shared_plugin(hooks=True), "python")
        found = []
        for path, data in sorted(project.files().items()):
            try:
                text = lf(data).decode("utf-8")
            except UnicodeDecodeError:
                continue
            found += [f"{path}:{number}: {line.strip()}"
                      for number, line in enumerate(text.split("\n"), 1) if OLD_NAME.search(line)]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
