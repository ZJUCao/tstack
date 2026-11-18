"""Upgrade group (F06 design 6, D54) for a project that has a language pack.

Each project is set up and given its language step with one plugin version,
both commits made, and then upgraded on its own branch.

D214 planted bugs (F03 design 8.2) caught here, for a project whose language
step ran before D214 (UpgradeBeforeD214Test): the plugin's pack without
docs/, so upgrade has nothing to report; upgrade not reporting the
list-valued tool.ruff.extend-exclude; and upgrade editing pyproject.toml.
"""

import re
import tomllib
import unittest
from pathlib import Path

from init_helpers import (
    CONFIG, DATE, RECORD, UPGRADE_DATE, WORKFLOW, InitCase, Project, make_plugin, read_text,
    replace_in, set_version, sha256_lf, shared_plugin, write_text,
)
from lang_helpers import (
    LANG_DATE, RUFF_EXCLUDES, expected_workflow, lang_done, lang_owned, pack_text, reset_project,
    ruff_excludes,
)
from rules_helpers import NEW_VERSION

LOCAL_NOTE = "# A setting this project added by hand.\n"
VERSION_LINE = "# Version 0.2.0.\n"
PYTHON_PYPROJECT = "troy-mode/lang/python/pyproject.toml"
BEFORE_D214 = 'extend-exclude = [".troy-mode"]'
RUFF_KEY = "tool.ruff.extend-exclude"
_EXTEND_EXCLUDE = re.compile(r"(?ms)^extend-exclude[ \t]*=[ \t]*\[.*?\]")


def append_to(plugin: Path, rel: str, text: str) -> None:
    """Adds text at the end of one of a plugin's files."""
    write_text(plugin, rel, read_text(plugin, rel).rstrip("\n") + "\n" + text)


def next_cpp_plugin() -> Path:
    """The plugin's next version with C/C++ pack changes.

    .clang-format and the pack's job changed, environment.yml gains a tool,
    and requirements-tools.in gains a requirement.
    """
    plugin = make_plugin(hooks=True)
    set_version(plugin, NEW_VERSION)
    append_to(plugin, "troy-mode/lang/cpp/.clang-format", VERSION_LINE)
    append_to(plugin, "troy-mode/lang/cpp/workflow-job.yml", "      " + VERSION_LINE)
    append_to(plugin, "troy-mode/lang/cpp/environment.yml", "  - gdb\n")
    append_to(plugin, "troy-mode/lang/cpp/requirements-tools.in", "cmakelang>=0.6\n")
    return plugin


def next_python_plugin() -> Path:
    """The plugin's next version with Python pack changes.

    F02's workflow and the pack's job changed, environment.yml gains a tool,
    a pyproject.toml setting has a new value, and [lang] source_roots grew.
    """
    plugin = make_plugin(hooks=True)
    set_version(plugin, NEW_VERSION)
    append_to(plugin, "troy-mode/checks/workflow.yml", VERSION_LINE)
    append_to(plugin, "troy-mode/lang/python/workflow-job.yml", "      " + VERSION_LINE)
    append_to(plugin, "troy-mode/lang/python/environment.yml", "  - git\n")
    replace_in(plugin, "troy-mode/lang/python/pyproject.toml", "line-length = 100",
               "line-length = 120")
    replace_in(plugin, "troy-mode/lang/python/config.toml", 'source_roots = ["src"]',
               'source_roots = ["src", "lib"]')
    return plugin


def before_d214_plugin() -> Path:
    """Version 0.1.0 as it was before D214: the Python pack's ruff leaves out .troy-mode only.

    Only the pack's extend-exclude line is rewritten, so every other setting
    is the plugin's own.
    """
    plugin = make_plugin(hooks=True, version="0.1.0")
    text = read_text(plugin, PYTHON_PYPROJECT)
    found = len(_EXTEND_EXCLUDE.findall(text))
    if found != 1:
        raise AssertionError(f"{PYTHON_PYPROJECT} sets extend-exclude {found} times, not once")
    write_text(plugin, PYTHON_PYPROJECT, _EXTEND_EXCLUDE.sub(lambda _: BEFORE_D214, text))
    return plugin


def d214_plugin() -> Path:
    """The plugin under test, as the next version, with its own Python pack unchanged."""
    plugin = make_plugin(hooks=True)
    set_version(plugin, NEW_VERSION)
    return plugin


def leaf_keys(data: dict, prefix: str = "") -> list:
    """Every leaf of a TOML table as a dotted key, as upgrade's report names them."""
    keys = []
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        keys += leaf_keys(value, dotted + ".") if isinstance(value, dict) else [dotted]
    return keys


def upgraded(old: Path, new: Path, lang: str, *extra: str) -> tuple:
    """Sets up and adds the pack with the old plugin, then upgrades with the new one.

    Returns:
        The project, its files before the upgrade, and the upgrade's outcome.
    """
    project, _, _ = lang_done(old, lang)
    project.git("switch", "-q", "-c", f"troy-mode/upgrade-{NEW_VERSION}")
    before = project.snapshot()
    return project, before, project.upgrade(new, *extra)


class UpgradeAfterLangNothingToChangeTest(InitCase):
    """Upgrade with the plugin version a project with a pack already has."""

    def test_upgrade_after_a_language_step_changes_nothing(self):
        """Exit 0, changed false, empty stage and differences, and no file changes."""
        plugin = shared_plugin(hooks=True)
        for lang in ("python", "cpp"):
            with self.subTest(lang=lang):
                project, before, out = upgraded(plugin, plugin, lang)
                report = self.report_of(out, 0)
                self.assertIs(report["changed"], False)
                self.assertEqual(report["stage"], [])
                self.assertEqual(report["executable"], [])
                self.assertEqual(report["differences"], [])
                self.assertEqual(report["conflicts"], [])
                self.assert_unchanged(before, project.snapshot())


class UpgradeCppPackTest(InitCase):
    """Upgrade of a C/C++ project to a plugin whose pack changed."""

    @classmethod
    def setUpClass(cls):
        """Adds the pack with 0.1.0 and upgrades to the next version once."""
        cls.old = make_plugin(hooks=True, version="0.1.0")
        cls.plugin = next_cpp_plugin()
        cls.project, cls.before, cls.out = upgraded(cls.old, cls.plugin, "cpp")

    def report(self) -> dict:
        """The upgrade's JSON report, after checking it exited 0."""
        return self.report_of(self.out, 0)

    def old_text(self, path: str) -> bytes:
        """A file's bytes before the upgrade."""
        return self.before.files[path]

    def test_upgrade_cpp_stages_exactly_the_changed_files(self):
        """The changed pack file, the rebuilt workflow, and the install record."""
        report = self.report()
        self.assertIs(report["changed"], True)
        self.assertEqual(report["conflicts"], [])
        self.assertEqual(report["stage"], sorted([".clang-format", WORKFLOW, RECORD]))
        self.assertEqual(self.project.status_paths(), set(report["stage"]))

    def test_upgrade_replaces_an_unchanged_pack_file(self):
        """.clang-format, unchanged since the language step, gets the plugin's new version."""
        self.assertEqual(self.actions_of(self.report())[".clang-format"], "replace")
        self.assertEqual(self.project.read(".clang-format"),
                         pack_text(self.plugin, "cpp", ".clang-format"))
        self.assertTrue(self.project.read(".clang-format").endswith(VERSION_LINE))

    def test_upgrade_keeps_a_pack_file_the_plugin_did_not_change(self):
        """.clang-tidy equals the plugin's and is kept."""
        report = self.report()
        self.assertEqual(self.actions_of(report)[".clang-tidy"], "keep")
        self.assertNotIn(".clang-tidy", report["stage"])

    def test_upgrade_rebuilds_the_workflow_with_the_new_pack_job(self):
        """The workflow is F02's workflow and the plugin's new C/C++ job."""
        self.assertEqual(self.actions_of(self.report())[WORKFLOW], "replace")
        self.assertEqual(self.project.read_bytes(WORKFLOW).decode("utf-8"),
                         expected_workflow(self.plugin, "cpp"))

    def test_upgrade_reports_but_never_changes_the_project_files(self):
        """environment.yml and requirements-tools.in differ from the pack's, stay, and are named."""
        report = self.report()
        for path in ("environment.yml", "requirements-tools.in", "CMakeLists.txt", CONFIG):
            with self.subTest(path=path):
                self.assertEqual(self.project.read_bytes(path), self.old_text(path))
                self.assertNotIn(path, report["stage"])
        paths = sorted(item["path"] for item in report["differences"])
        self.assertEqual(paths, ["environment.yml", "requirements-tools.in"])

    def test_upgrade_record_keeps_the_pack_and_the_steps(self):
        """The record has the new version, all three dates, the pack, and the new hashes."""
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(self.actions_of(self.report())[RECORD], "edit")
        self.assertEqual(record["plugin"]["version"], NEW_VERSION)
        self.assertEqual(record["steps"],
                         {"setup": DATE, "lang": LANG_DATE, "upgrade": UPGRADE_DATE})
        self.assertEqual(record["lang"]["name"], "cpp")
        self.assertEqual(sorted(record["files"]), sorted(lang_owned(self.plugin, "cpp")))
        for path, digest in record["files"].items():
            with self.subTest(path=path):
                self.assertEqual(digest, sha256_lf(self.project.read_bytes(path)))


class UpgradePythonPackTest(InitCase):
    """Upgrade of a Python project to a plugin whose workflow and pack changed."""

    @classmethod
    def setUpClass(cls):
        """Adds the pack with 0.1.0 and upgrades to the next version once."""
        cls.old = make_plugin(hooks=True, version="0.1.0")
        cls.plugin = next_python_plugin()
        cls.project, cls.before, cls.out = upgraded(cls.old, cls.plugin, "python")

    def test_upgrade_python_rebuilds_only_the_workflow_and_the_record(self):
        """F02's new workflow and the new pack job form the workflow; nothing else is staged."""
        report = self.report_of(self.out, 0)
        self.assertEqual(report["stage"], sorted([WORKFLOW, RECORD]))
        self.assertEqual(self.actions_of(report)[WORKFLOW], "replace")
        self.assertEqual(self.project.read_bytes(WORKFLOW).decode("utf-8"),
                         expected_workflow(self.plugin, "python"))

    def test_upgrade_reports_config_environment_and_pyproject_differences(self):
        """The config's source_roots, environment.yml, and a pyproject.toml value differ."""
        report = self.report_of(self.out, 0)
        paths = sorted(item["path"] for item in report["differences"])
        self.assertEqual(paths, sorted([CONFIG, "environment.yml", "pyproject.toml"]))
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.project.read_bytes(path), self.before.files[path])

    def test_upgrade_python_record_keeps_the_pack(self):
        """[steps] lang and [lang] name stay; the workflow hash is the new workflow's."""
        self.report_of(self.out, 0)
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(record["lang"]["name"], "python")
        self.assertEqual(record["steps"]["lang"], LANG_DATE)
        self.assertEqual(record["files"][WORKFLOW], sha256_lf(self.project.read_bytes(WORKFLOW)))
        self.assertEqual(sorted(record["files"]), sorted(lang_owned(self.plugin, "python")))


class UpgradeBeforeD214Test(InitCase):
    """A Python project set up before D214, upgraded to the plugin under test (F03 design 8.2).

    Upgrade never changes the appended pyproject.toml tables (F06 design D54),
    so the project keeps its old extend-exclude and is told to take the new one.
    """

    @classmethod
    def setUpClass(cls):
        """Adds the pack with the pre-D214 0.1.0 and upgrades to the plugin under test once."""
        cls.old = before_d214_plugin()
        cls.plugin = d214_plugin()
        cls.project, cls.before, cls.out = upgraded(cls.old, cls.plugin, "python")

    def test_upgrade_names_the_ruff_exclude_list_for_pyproject(self):
        """pyproject.toml is the one difference, and its message names tool.ruff.extend-exclude.

        D214 planted bugs caught: the plugin's pack without docs/, and upgrade
        not reporting a list-valued key. No other key of the pack is named.
        """
        report = self.report_of(self.out, 0)
        self.assertEqual(ruff_excludes(self.before.files["pyproject.toml"].decode("utf-8")),
                         ([".troy-mode"], False), "the premise: the project predates D214")
        messages = {item["path"]: item["message"] for item in report["differences"]}
        self.assertEqual(sorted(messages), ["pyproject.toml"], report["differences"])
        self.assertIn(RUFF_KEY, messages["pyproject.toml"])
        fragment = tomllib.loads(pack_text(self.plugin, "python", "pyproject.toml"))
        for key in leaf_keys(fragment):
            if key != RUFF_KEY:
                with self.subTest(key=key):
                    self.assertNotIn(key, messages["pyproject.toml"])

    def test_upgrade_leaves_the_old_pyproject_byte_for_byte(self):
        """pyproject.toml keeps every byte and its old list, and is neither staged nor changed.

        D214 planted bug caught: upgrade editing pyproject.toml to take the new list.
        """
        report = self.report_of(self.out, 0)
        self.assertEqual(ruff_excludes(pack_text(self.plugin, "python", "pyproject.toml")),
                         (sorted(RUFF_EXCLUDES), False), "the premise: the plugin has D214's list")
        self.assertEqual(self.project.read_bytes("pyproject.toml"),
                         self.before.files["pyproject.toml"])
        self.assertEqual(ruff_excludes(self.project.read("pyproject.toml")),
                         ([".troy-mode"], False))
        self.assertNotIn("pyproject.toml", report["stage"])
        self.assertNotIn("pyproject.toml", self.project.status_paths())


class UpgradePackConflictTest(InitCase):
    """An owned pack file edited since the language step stops upgrade (D54)."""

    @classmethod
    def setUpClass(cls):
        """Builds both plugin versions and one project with the old C/C++ pack."""
        cls.old = make_plugin(hooks=True, version="0.1.0")
        cls.plugin = next_cpp_plugin()
        cls.project, _, _ = lang_done(cls.old, "cpp")
        cls.lang_sha = cls.project.git("rev-parse", "HEAD").strip()

    def edited(self, *paths: str) -> Project:
        """The project, back at its language commit, with the named files edited and committed."""
        project = self.project
        reset_project(project, self.lang_sha)
        for path in paths:
            project.write(path, project.read(path) + LOCAL_NOTE)
        project.commit_paths(list(paths), "[rules] Change the C/C++ settings by hand")
        return project

    def test_upgrade_stops_on_edited_pack_files(self):
        """Edited pack files are conflicts, whether or not the plugin changed them."""
        project = self.edited(".clang-format", ".clang-tidy")
        before = project.snapshot()
        report = self.report_of(project.upgrade(self.plugin), 1)
        self.assertEqual(sorted(item["path"] for item in report["conflicts"]),
                         [".clang-format", ".clang-tidy"])
        self.assert_unchanged(before, project.snapshot())
        self.assertTrue(project.read(".clang-format").endswith(LOCAL_NOTE))

    def test_upgrade_replace_lets_an_edited_pack_file_through(self):
        """--replace names the edited file, which then gets the plugin's version and hash."""
        project = self.edited(".clang-format")
        report = self.report_of(project.upgrade(self.plugin, "--replace", ".clang-format"), 0)
        self.assertEqual(self.actions_of(report)[".clang-format"], "replace")
        content = pack_text(self.plugin, "cpp", ".clang-format")
        self.assertEqual(project.read(".clang-format"), content)
        record = tomllib.loads(project.read(RECORD))
        self.assertEqual(record["files"][".clang-format"], sha256_lf(content.encode("utf-8")))


if __name__ == "__main__":
    unittest.main()
