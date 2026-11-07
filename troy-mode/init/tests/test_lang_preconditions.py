"""Preconditions group (F06 design 5.1): each stops the language step and changes nothing.

A stopped step exits 1, leaves every file and the git config as they were,
and runs no `mamba env create` and no `mamba run`. Usage errors exit 2.
Most cases share one set-up project, which shared_lang_project() puts back
to its setup commit before each test.
"""

import os
import shutil
import unittest

from init_helpers import (
    CONFIG, DATE, ENGINE_REL, PROJECT, RECORD, SCRATCH, WORKFLOW, InitCase, Project, new_dir,
    read_text, replace_in, run_python, shared_plugin,
)
from lang_helpers import (
    APPROVED, ARCHITECTURE, CPP_COPIED, INCLUDE_LINE, LANG_DATE, LOCKS, OWN_TEXT, FakeMamba,
    architecture, expected_environment, git_only_path, lang_project, pack_text, run_lang,
    shared_lang_project,
)

TROY_CODE_JOB = ("\n  troy-code:\n    name: our own code checks\n    runs-on: ubuntu-24.04\n"
                 "    steps:\n      - run: echo ours\n")
CPP_CREATED = ("environment.yml", "requirements-tools.in", *CPP_COPIED)


class LangStopCase(InitCase):
    """Runs the language step expecting it to stop, with a fake mamba watching."""

    @classmethod
    def setUpClass(cls):
        """Uses the plugin with git hooks."""
        cls.plugin = shared_plugin(hooks=True)

    def stopped(self, project: Project, lang: str = "python", *extra: str,
                fake: FakeMamba = None) -> dict:
        """Runs the step, asserts exit 1 and no change, and returns the report.

        With a fake mamba, the step runs without --no-env and the fake must
        see no env create and no run call.
        """
        before = project.snapshot()
        if fake is not None:
            fake.clear()
            extra = (*extra, "--mamba", str(fake.path))
        report = self.report_of(run_lang(project, self.plugin, lang, *extra,
                                         no_env=fake is None), 1)
        self.assert_unchanged(before, project.snapshot())
        self.assertEqual(report["command"], "lang")
        if fake is not None:
            self.assertLessEqual(set(fake.kinds()), {"list"}, fake.argvs())
        return report

    def problems(self, report: dict) -> str:
        """The report's problems as one text, after checking there is at least one."""
        self.assertNotEqual(report["problems"], [])
        return " ".join(report["problems"])

    def conflict_paths(self, report: dict) -> list:
        """The paths of the report's conflicts, sorted."""
        return sorted(item["path"] for item in report["conflicts"])


class LangStopsInASetUpProjectTest(LangStopCase):
    """Preconditions and conflicts checked in the shared set-up project (design 5.1)."""

    def setUp(self):
        """Puts the shared project back to its setup commit."""
        self.project = shared_lang_project(self.plugin)

    def tearDown(self):
        """Leaves the shared project at its setup commit for the next test."""
        shared_lang_project(self.plugin)

    def test_lang_stops_when_a_pack_is_installed(self):
        """After one language step, a second one stops, for either language."""
        self.report_of(run_lang(self.project, self.plugin, "python"), 0)
        self.assertIn("[lang]", read_text(self.project.root, RECORD))
        for lang in ("python", "cpp"):
            with self.subTest(lang=lang):
                self.problems(self.stopped(self.project, lang))

    def test_lang_stops_when_the_config_lang_table_has_a_key(self):
        """A [lang] table with any key counts as an installed pack."""
        replace_in(self.project.root, CONFIG, "\n[lang]\n", '\n[lang]\nseries = ["."]\n')
        self.assertNotIn("[lang]", read_text(self.project.root, RECORD))
        self.problems(self.stopped(self.project, "cpp"))

    def test_lang_stops_below_the_repository_root(self):
        """--repo pointing at a folder inside the repository, not its root, exits 1."""
        before = self.project.snapshot()
        args = ["lang", "python", "--no-env", "--date", LANG_DATE, "--json",
                "--repo", self.project.root / "docs"]
        out = run_python(self.plugin / ENGINE_REL, args, self.project.tmp)
        self.problems(self.report_of(out, 1))
        self.assert_unchanged(before, self.project.snapshot())

    def test_lang_stops_when_no_mamba_is_found(self):
        """Without --no-env, a PATH without mamba and no MAMBA_EXE stop the step."""
        folder = git_only_path()
        if shutil.which("mamba", path=folder):
            self.skipTest(f"{folder} holds a mamba")
        before = self.project.snapshot()
        out = run_lang(self.project, self.plugin, "python", no_env=False,
                       env_extra={"PATH": folder})
        self.assertIn("mamba", self.problems(self.report_of(out, 1)).lower())
        self.assert_unchanged(before, self.project.snapshot())

    def test_lang_stops_without_origin_main(self):
        """An origin whose main is not fetched stops the step."""
        sha = self.project.git("rev-parse", "refs/remotes/origin/main").strip()
        self.project.git("update-ref", "-d", "refs/remotes/origin/main")
        try:
            self.problems(self.stopped(self.project, fake=FakeMamba()))
        finally:
            self.project.git("update-ref", "refs/remotes/origin/main", sha)

    def test_lang_stops_when_pyproject_has_a_pack_table(self):
        """A pyproject.toml that already has a table the pack adds stops the step and names it."""
        cases = {
            "tool.ruff": '[project]\nname = "x"\n\n[tool.ruff]\nline-length = 88\n',
            "project.optional-dependencies": '[project]\nname = "x"\n\n'
                                             '[project.optional-dependencies]\ndocs = ["mkdocs"]\n',
        }
        for table, text in cases.items():
            with self.subTest(table=table):
                self.project.write("pyproject.toml", text)
                self.assertIn(table, self.problems(self.stopped(self.project)))

    def test_lang_stops_when_cmakelists_lacks_the_include(self):
        """A CMakeLists.txt without include(cmake/troy.cmake) stops the step with the line."""
        for text in ("cmake_minimum_required(VERSION 3.28)\nproject(x CXX)\n",
                     "project(x CXX)\ninclude(cmake/other.cmake)\n"):
            with self.subTest(text=text):
                self.project.write("CMakeLists.txt", text)
                self.assertIn(INCLUDE_LINE, self.problems(self.stopped(self.project, "cpp")))

    def test_lang_accepts_every_form_of_the_include(self):
        """Letter case, spaces, quotes, and the source-folder prefixes all count."""
        forms = ("INCLUDE(cmake/troy.cmake)", "include( cmake/troy.cmake )",
                 'include("cmake/troy.cmake")', "include(${CMAKE_SOURCE_DIR}/cmake/troy.cmake)",
                 "include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/troy.cmake)")
        for form in forms:
            with self.subTest(form=form):
                self.project.write("CMakeLists.txt", f"project(x CXX)\n{form}\n")
                out = run_lang(self.project, self.plugin, "cpp", "--dry-run")
                self.assertEqual(self.actions_of(self.report_of(out, 0))["CMakeLists.txt"], "keep")

    def test_lang_stops_on_a_workflow_it_cannot_extend(self):
        """A missing workflow, one with a troy-code job, or a key after jobs: stops the step."""
        original = self.project.read(WORKFLOW)
        cases = {"missing": None, "troy-code job": original.rstrip("\n") + "\n" + TROY_CODE_JOB,
                 "key after jobs": original.rstrip("\n") + "\nconcurrency:\n  group: checks\n"}
        for case, text in cases.items():
            with self.subTest(case=case):
                if text is None:
                    (self.project.root / WORKFLOW).unlink()
                else:
                    self.project.write(WORKFLOW, text)
                try:
                    self.problems(self.stopped(self.project))
                finally:
                    self.project.write(WORKFLOW, original)

    def test_lang_python_stops_on_an_existing_environment_file(self):
        """An existing environment.yml is a conflict and keeps its content."""
        self.project.write("environment.yml", OWN_TEXT)
        report = self.stopped(self.project, fake=FakeMamba())
        self.assertEqual(self.conflict_paths(report), ["environment.yml"])
        self.assertEqual(self.project.read("environment.yml"), OWN_TEXT)

    def test_lang_cpp_stops_on_each_existing_file_it_creates(self):
        """Each C/C++ file the step creates is a conflict when it exists, and keeps its content."""
        for path in CPP_CREATED:
            self.project.write(path, OWN_TEXT)
        report = self.stopped(self.project, "cpp")
        self.assertEqual(self.conflict_paths(report), sorted(CPP_CREATED))
        for path in CPP_CREATED:
            with self.subTest(path=path):
                self.assertEqual(self.project.read(path), OWN_TEXT)

    def test_lang_stops_on_an_existing_lock_when_it_compiles_one(self):
        """Without --no-env the lock is created, so an existing lock is a conflict."""
        fake = FakeMamba()
        for lang in ("python", "cpp"):
            with self.subTest(lang=lang):
                self.project.write(LOCKS[lang], OWN_TEXT)
                try:
                    report = self.stopped(self.project, lang, fake=fake)
                    self.assertEqual(self.conflict_paths(report), [LOCKS[lang]])
                finally:
                    (self.project.root / LOCKS[lang]).unlink()

    def test_lang_keeps_an_existing_lock_with_no_env(self):
        """With --no-env no lock is compiled, so an existing lock is no conflict."""
        self.project.write(LOCKS["python"], OWN_TEXT)
        report = self.report_of(run_lang(self.project, self.plugin, "python", "--dry-run"), 0)
        self.assertEqual(report["conflicts"], [])
        self.assertNotIn(LOCKS["python"], report["stage"])
        self.assertIn(self.actions_of(report).get(LOCKS["python"]), (None, "keep"))

    def test_lang_replace_lets_one_file_through_while_another_conflicts(self):
        """--replace names one existing file; another existing file still stops the step."""
        self.project.write(".clang-format", OWN_TEXT)
        self.project.write(".clang-tidy", OWN_TEXT)
        report = self.stopped(self.project, "cpp", "--replace", ".clang-format")
        self.assertEqual(self.conflict_paths(report), [".clang-tidy"])

    def test_lang_replace_overwrites_each_named_file(self):
        """Each file named with --replace gets the pack's content, with action replace."""
        self.project.write(".clang-format", OWN_TEXT)
        self.project.write("environment.yml", OWN_TEXT)
        out = run_lang(self.project, self.plugin, "cpp", "--replace", ".clang-format",
                       "--replace", "environment.yml")
        report = self.report_of(out, 0)
        actions = self.actions_of(report)
        self.assertEqual((actions[".clang-format"], actions["environment.yml"]),
                         ("replace", "replace"))
        self.assertEqual(self.project.read(".clang-format"),
                         pack_text(self.plugin, "cpp", ".clang-format"))
        self.assertEqual(self.project.read("environment.yml"),
                         expected_environment(self.plugin, "cpp"))
        self.assertLessEqual({".clang-format", "environment.yml"}, set(report["stage"]))


class LangNotReadyTest(LangStopCase):
    """Projects that are not set up, or are on main (design 5.1)."""

    def test_lang_stops_when_the_project_is_not_set_up(self):
        """Without .troy-mode/install.toml the step stops."""
        project = Project(base_files=APPROVED)
        self.assertEqual(project.files(".troy-mode"), {})
        self.problems(self.stopped(project, fake=FakeMamba()))

    def test_lang_stops_on_the_main_branch(self):
        """The step refuses to run while main is checked out."""
        project = Project(base_files=APPROVED)
        self.report_of(project.setup(self.plugin), 0)
        project.git("switch", "-q", "main")
        self.assertEqual(set(project.files(RECORD)), {RECORD})
        self.assertIn("main", self.problems(self.stopped(project)))


class LangArchitectureTest(LangStopCase):
    """docs/architecture.md on origin/main must be at version 1.0 or higher (design 5.1)."""

    def test_lang_stops_without_an_architecture_on_origin_main(self):
        """origin/main without docs/architecture.md stops the step."""
        project = lang_project(self.plugin, approved=False)
        self.assertIn("architecture", self.problems(self.stopped(project, fake=FakeMamba())))

    def test_lang_stops_below_version_one_and_reads_only_origin_main(self):
        """Version 0.9 stops the step, also with a 1.0 copy in the working tree or on the branch."""
        project = lang_project(self.plugin, base_files=architecture("0.9"))
        with self.subTest(copy="origin/main only"):
            self.assertIn("architecture", self.problems(self.stopped(project, "cpp")))
        project.write(ARCHITECTURE, APPROVED[ARCHITECTURE])
        with self.subTest(copy="working tree"):
            self.problems(self.stopped(project))
        project.commit_paths([ARCHITECTURE], "[docs] Approve the architecture")
        with self.subTest(copy="branch"):
            self.problems(self.stopped(project))

    def test_lang_stops_on_a_version_not_in_major_minor_form(self):
        """A version such as "1" is not MAJOR.MINOR and stops the step."""
        project = lang_project(self.plugin, base_files=architecture("1"))
        self.assertIn("architecture", self.problems(self.stopped(project)))

    def test_lang_runs_above_version_one(self):
        """A later approved version, such as 1.3, lets the step run."""
        project = lang_project(self.plugin, base_files=architecture("1.3"))
        report = self.report_of(run_lang(project, self.plugin, "python", "--dry-run"), 0)
        self.assertEqual(report["problems"], [])


class LangUsageErrorsTest(InitCase):
    """The language step exits 2 on bad options and changes nothing (interface note)."""

    @classmethod
    def setUpClass(cls):
        """Uses the shared set-up project, since no case may change it."""
        cls.plugin = shared_plugin(hooks=True)

    def setUp(self):
        """Puts the shared project back to its setup commit."""
        self.project = shared_lang_project(self.plugin)

    def assert_cannot_run(self, *args: str) -> None:
        """Runs the engine, asserts exit 2 with a message and no change."""
        before = self.project.snapshot()
        out = self.project.run(self.plugin, *args)
        self.assertEqual(out.code, 2, out.describe())
        self.assertNotEqual((out.stderr + out.stdout).strip(), "")
        self.assert_unchanged(before, self.project.snapshot())

    def test_lang_exits_2_on_an_unknown_or_missing_language(self):
        """Only python and cpp have packs."""
        for args in (["lang", "rust", "--no-env"], ["lang", "--no-env"]):
            with self.subTest(args=args):
                self.assert_cannot_run(*args, "--json")

    def test_lang_exits_2_on_package_with_cpp(self):
        """--package is for Python only."""
        self.assert_cannot_run("lang", "cpp", "--no-env", "--package", "habits", "--json")

    def test_lang_exits_2_on_a_package_that_is_not_an_identifier(self):
        """A given or derived package that is not a Python identifier is a usage error."""
        for extra in (["--package", "1habits"], ["--package", "habit-tracker"],
                      ["--project-name", "123app"]):
            with self.subTest(extra=extra):
                self.assert_cannot_run("lang", "python", "--no-env", *extra, "--json")

    def test_lang_exits_2_on_no_env_with_mamba_or_prefix(self):
        """--no-env cannot go with --mamba or --env-prefix."""
        prefix = str(self.project.tmp / "env")
        for extra in (["--mamba", str(self.project.tmp / "mamba")], ["--env-prefix", prefix]):
            with self.subTest(extra=extra):
                self.assert_cannot_run("lang", "python", "--no-env", *extra, "--json")

    def test_lang_exits_2_on_a_date_not_in_iso_form(self):
        """A --date that is not YYYY-MM-DD is a usage error, as for setup."""
        self.assert_cannot_run("lang", "python", "--no-env", "--date", "2026/11/12", "--json")


class LangOutsideRepositoryTest(InitCase):
    """The language step outside any git repository."""

    def test_lang_exits_2_outside_a_git_repository(self):
        """A folder that is not in a git repository exits 2 and stays empty."""
        folder = new_dir("plain") / PROJECT
        folder.mkdir()
        args = ["lang", "python", "--no-env", "--date", DATE, "--json", "--repo", folder]
        out = run_python(shared_plugin(hooks=True) / ENGINE_REL, args, folder.parent,
                         {"GIT_CEILING_DIRECTORIES": str(SCRATCH)})
        self.assertEqual(out.code, 2, out.describe())
        self.assertNotEqual(out.stderr.strip(), "")
        self.assertEqual(os.listdir(folder), [])


if __name__ == "__main__":
    unittest.main()
