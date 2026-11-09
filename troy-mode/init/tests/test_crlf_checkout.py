"""troy-init in a Windows checkout (F06 design 4.2 and 6): core.autocrlf=true gives CRLF files.

Git for Windows checks text files out with CRLF line endings. troy-init must
read those files as it reads LF ones, and a file it edits in place keeps its
CRLF endings, while a file it creates gets LF. Each class clones a project
with core.autocrlf=true and runs one step on it.
"""

import tomllib
import unittest

from init_helpers import (
    CONFIG, RECORD, RULES, UPGRADE_DATE, WORKFLOW, InitCase, Project, make_plugin,
    setup_project, shared_plugin,
)
from lang_helpers import lang_project, run_lang
from rules_helpers import (
    NEW_VERSION, P_ROWS, R22, UPGRADE_STAGE, add_rows_after, apply_upgrade_changes,
    change_log_rows, front_matter, rule_rows,
)

AUTOCRLF = ["core.autocrlf=true"]
OWN_GITIGNORE = "dist/\n*.log\n"
OWN_PYPROJECT = '[project]\nname = "habit-tracker"\nversion = "0.1.0"\n'


def only_crlf(data: bytes) -> bool:
    """True when the bytes have line breaks and every one of them is CRLF."""
    return data.count(b"\n") > 0 and data.count(b"\n") == data.count(b"\r\n")


class CrlfCase(InitCase):
    """Assertions about line endings."""

    def assert_crlf(self, project: Project, paths) -> None:
        """Every named file has CRLF line endings only."""
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(only_crlf(project.read_bytes(path)), f"{path} is not all CRLF")

    def assert_lf(self, project: Project, paths) -> None:
        """No named file contains a CRLF."""
        for path in paths:
            with self.subTest(path=path):
                self.assertNotIn(b"\r\n", project.read_bytes(path))


class UpgradeCrlfTest(CrlfCase):
    """Upgrade from 0.1.0 in a clone with core.autocrlf=true, then once more."""

    @classmethod
    def setUpClass(cls):
        """Sets up with P rows, clones with CRLF, upgrades, commits, and upgrades again."""
        old = make_plugin(hooks=True, version="0.1.0")
        cls.plugin = make_plugin(hooks=True)
        apply_upgrade_changes(cls.plugin)
        source = setup_project(old)
        for path in RULES:
            source.write(path, add_rows_after(source.read(path), "R21", P_ROWS[path]))
        source.commit_paths(list(RULES), "[rules] Add P01 and P02")
        cls.project = project = Project(source=source.root, clone_config=AUTOCRLF)
        cls.before = {path: project.read_bytes(path) for path in (*RULES, RECORD)}
        project.git("switch", "-q", "-c", f"troy-mode/upgrade-{NEW_VERSION}")
        cls.out = project.upgrade(cls.plugin)
        cls.after = {path: project.read_bytes(path) for path in (*RULES, RECORD)}
        if cls.out.code == 0 and isinstance(cls.out.report, dict):
            cls.sha = project.commit_report(cls.out.report, f"[rules] Upgrade troy-mode to "
                                                           f"{NEW_VERSION}")
            cls.again = project.upgrade(cls.plugin)
        else:
            cls.sha, cls.again = None, None

    def report(self) -> dict:
        """The first upgrade's JSON report, after checking it exited 0."""
        return self.report_of(self.out, 0)

    def test_the_clone_has_crlf_rules_and_record(self):
        """The premise: the checkout gives the rules table and the record CRLF endings."""
        for path, data in self.before.items():
            with self.subTest(path=path):
                self.assertTrue(only_crlf(data), f"{path} is not all CRLF in the clone")

    def test_upgrade_in_a_crlf_checkout_edits_both_rules_files(self):
        """Both rules files are edited and staged, as in an LF checkout."""
        report = self.report()
        actions = self.actions_of(report)
        self.assertEqual([actions[path] for path in RULES], ["edit", "edit"])
        self.assertEqual(report["stage"], UPGRADE_STAGE)

    def test_upgrade_in_a_crlf_checkout_reports_no_rules_difference(self):
        """The rules table is not reported as left alone or as having no version."""
        report = self.report()
        notes = [item for item in report["differences"] if item["path"] in RULES]
        self.assertEqual(notes, [])

    def test_upgrade_in_a_crlf_checkout_raises_the_version(self):
        """Both rules files go from 1.0 to 1.1 and are dated the upgrade day."""
        self.report()
        for path in RULES:
            with self.subTest(path=path):
                fields = front_matter(self.project.read(path))
                self.assertEqual((fields["version"], fields["updated"]), ("1.1", UPGRADE_DATE))

    def test_upgrade_in_a_crlf_checkout_replaces_r_rows_and_keeps_p_rows(self):
        """R22 arrives with the upgrade date, R03 gets its new wording, P rows stay last."""
        self.report()
        wording = {"docs/rules.md": "changes at most 400 lines",
                   "docs/rules.zh-CN.md": "最多改动 400 行"}
        for path in RULES:
            with self.subTest(path=path):
                rows = rule_rows(self.project.read(path))
                by_id = {row[2:5]: row for row in rows}
                self.assertEqual(by_id["R22"], R22[path].replace("{{init-date}}", UPGRADE_DATE))
                self.assertIn(wording[path], by_id["R03"])
                self.assertEqual(rows[-2:], P_ROWS[path])

    def test_upgrade_in_a_crlf_checkout_adds_one_change_log_row(self):
        """Each change log gains one 1.1 row dated the upgrade day."""
        self.report()
        for path in RULES:
            with self.subTest(path=path):
                old = change_log_rows(self.before[path].decode("utf-8").replace("\r\n", "\n"))
                new = change_log_rows(self.project.read(path))
                self.assertEqual(new[:len(old)], old)
                self.assertEqual(len(new), len(old) + 1)
                self.assertTrue(new[-1].startswith(f"| 1.1 | {UPGRADE_DATE} |"), new[-1])

    def test_upgrade_in_a_crlf_checkout_keeps_crlf_in_the_files_it_edits(self):
        """The rules files and the install record keep their CRLF endings."""
        self.report()
        for path, data in self.after.items():
            with self.subTest(path=path):
                self.assertTrue(only_crlf(data), f"{path} lost its CRLF endings")

    def test_upgrade_in_a_crlf_checkout_commits_lf_files(self):
        """git stores the edited files with LF, as for every other file."""
        self.report()
        for path in (*RULES, RECORD):
            with self.subTest(path=path):
                blob = self.project.git("cat-file", "blob", f"{self.sha}:{path}")
                self.assertNotIn("\r", blob)

    def test_upgrade_again_in_a_crlf_checkout_changes_nothing(self):
        """After the upgrade is committed, a second run finds nothing to upgrade."""
        self.report()
        report = self.report_of(self.again, 0)
        self.assertIs(report["changed"], False)
        self.assertEqual(report["stage"], [])
        self.assertEqual([item for item in report["differences"] if item["path"] in RULES], [])


class SetupCrlfTest(CrlfCase):
    """Setup in a clone with core.autocrlf=true whose .gitignore exists."""

    @classmethod
    def setUpClass(cls):
        """Sets up a CRLF clone that has its own .gitignore."""
        cls.plugin = shared_plugin(hooks=True)
        cls.project = Project(base_files={".gitignore": OWN_GITIGNORE}, clone_config=AUTOCRLF)
        cls.gitignore_before = cls.project.read_bytes(".gitignore")
        cls.out = cls.project.setup(cls.plugin)

    def test_setup_in_a_crlf_checkout_appends_to_gitignore_with_crlf(self):
        """The existing .gitignore gets the progress file and stays all CRLF."""
        self.assertTrue(only_crlf(self.gitignore_before))
        report = self.report_of(self.out, 0)
        self.assertEqual(self.actions_of(report)[".gitignore"], "append")
        self.assert_crlf(self.project, [".gitignore"])
        lines = self.project.read(".gitignore").split("\n")
        self.assertEqual(lines[:2], ["dist/", "*.log"])
        self.assertIn(".troy-mode/progress.md", lines)

    def test_setup_in_a_crlf_checkout_creates_files_with_lf(self):
        """The files setup creates are written with LF, as design 4.2 says."""
        report = self.report_of(self.out, 0)
        created = [item["path"] for item in report["actions"] if item["action"] == "create"]
        self.assertIn(CONFIG, created)
        self.assert_lf(self.project, created)


class SetupCrlfNewGitignoreTest(CrlfCase):
    """Setup in a clone with core.autocrlf=true that has no .gitignore yet."""

    def test_setup_in_a_crlf_checkout_creates_gitignore_with_lf(self):
        """A .gitignore that setup creates gets LF, though the other files are CRLF."""
        project = Project(clone_config=AUTOCRLF)
        self.assertTrue(only_crlf(project.read_bytes("README.md")))
        report = self.report_of(project.setup(shared_plugin(hooks=True)), 0)
        self.assertEqual(self.actions_of(report)[".gitignore"], "create")
        self.assert_lf(project, [".gitignore"])
        self.assertIn(".troy-mode/progress.md", project.read(".gitignore").split("\n"))


class LangCrlfTest(CrlfCase):
    """The Python language step in a clone with core.autocrlf=true."""

    @classmethod
    def setUpClass(cls):
        """Sets up a project with its own pyproject.toml, clones it with CRLF, runs lang."""
        cls.plugin = shared_plugin(hooks=True)
        source = lang_project(cls.plugin, base_files={"pyproject.toml": OWN_PYPROJECT,
                                                      ".gitignore": OWN_GITIGNORE})
        cls.project = Project(source=source.root, clone_config=AUTOCRLF)
        cls.edited = [CONFIG, WORKFLOW, ".gitignore", RECORD, "pyproject.toml"]
        cls.before = {path: cls.project.read_bytes(path) for path in cls.edited}
        cls.out = run_lang(cls.project, cls.plugin, "python")

    def report(self) -> dict:
        """The language step's JSON report, after checking it exited 0."""
        return self.report_of(self.out, 0)

    def test_the_clone_has_crlf_files(self):
        """The premise: every file the step edits is all CRLF before it runs."""
        for path, data in self.before.items():
            with self.subTest(path=path):
                self.assertTrue(only_crlf(data), f"{path} is not all CRLF in the clone")

    def test_lang_in_a_crlf_checkout_edits_the_files(self):
        """The config, workflow, .gitignore, record, and pyproject.toml are edited in place."""
        actions = self.actions_of(self.report())
        self.assertEqual({path: actions[path] for path in self.edited},
                         {CONFIG: "edit", WORKFLOW: "edit", ".gitignore": "append",
                          RECORD: "edit", "pyproject.toml": "append"})

    def test_lang_in_a_crlf_checkout_fills_the_config_and_workflow(self):
        """The [lang] table names the pack, and the workflow gains the troy-code job."""
        self.report()
        config = tomllib.loads(self.project.read(CONFIG))
        self.assertEqual(config["lang"]["name"], "python")
        self.assertIn("\n  troy-code:", self.project.read(WORKFLOW))
        pyproject = tomllib.loads(self.project.read("pyproject.toml"))
        self.assertEqual(pyproject["project"]["name"], "habit-tracker")
        self.assertIn("ruff", pyproject.get("tool", {}))

    def test_lang_in_a_crlf_checkout_keeps_crlf_in_the_files_it_edits(self):
        """Every file the step edits in place keeps its CRLF endings."""
        self.report()
        self.assert_crlf(self.project, self.edited)

    def test_lang_in_a_crlf_checkout_creates_files_with_lf(self):
        """The files the step creates are written with LF."""
        report = self.report()
        created = [item["path"] for item in report["actions"]
                   if item["action"] == "create" and (self.project.root / item["path"]).exists()]
        self.assertIn("environment.yml", created)
        self.assert_lf(self.project, created)


if __name__ == "__main__":
    unittest.main()
