"""Language step group (F06 design 5.2, 5.3, and 5.5): the files the step writes.

Each class sets up a project whose origin/main holds an approved
architecture, makes the setup commit, and runs `lang ... --no-env` once; the
tests only read the result. The environment and the lock are tested in
test_lang_env.py, and the preconditions in test_lang_preconditions.py.
"""

import datetime
import tomllib
import unittest

from init_helpers import (
    CONFIG, DATE, PROGRESS, PROJECT, RECORD, REPORT_KEYS, WORKFLOW, InitCase, changed_paths,
    make_plugin, plugin_version, sha256_lf, shared_plugin,
)
from lang_helpers import (
    BUILD_FILES, CPP_COPIED, ENVIRONMENT_KEYS, GITIGNORE_LINES, INCLUDE_LINE, LANG_DATE,
    LANG_REPORT_KEYS, LOCKS, TITLES, crlf_lang, expected_environment, expected_new_cmakelists,
    expected_new_pyproject, expected_workflow, join_parts, lang_actions, lang_owned,
    lang_project, lang_stage, lang_values, pack_text, parse_config_with_troy_check, run_lang,
    shared_lang_project, split_lang_table,
)
from rules_helpers import nonblank_lines as nonblank_lines_of

OWN_PYPROJECT = (
    '[build-system]\nrequires = ["hatchling>=1.25"]\nbuild-backend = "hatchling.build"\n\n'
    '[project]\nname = "habit-tracker"\nversion = "0.3.0"\nrequires-python = ">=3.13"\n'
    'dependencies = ["rich>=13"]\n\n[project.scripts]\nhabits = "habit_tracker.cli:main"\n\n'
    '[tool.black]\nline-length = 88\n\n'
    '[tool.hatch.build.targets.wheel]\npackages = ["src/habit_tracker"]\n'
)
OWN_CMAKELISTS = ("cmake_minimum_required(VERSION 3.28)\nproject(habit LANGUAGES CXX)\n"
                  "include(cmake/troy.cmake)\n\nadd_executable(habit src/main.cc)\n")
PY_LEGACY_FILES = {
    "tests/test_old.py": "def test_old():\n    assert True\n",
    "lib/thing_test.py": "def test_thing():\n    assert True\n",
    "conftest.py": "",
    "tests/helpers.py": "VALUE = 1\n",
    "src/habit_tracker/__init__.py": "",
}
PY_LEGACY = ["conftest.py", "lib/thing_test.py", "tests/test_new.py", "tests/test_old.py"]
CPP_LEGACY_FILES = {
    "tests/old_test.cc": "int main() { return 0; }\n",
    "src/x_test.cpp": "int main() { return 0; }\n",
    "tests/test_tool.py": "",
    "src/main.cc": "int main() { return 0; }\n",
}
CPP_LEGACY = ["src/x_test.cpp", "tests/old_test.cc"]


def gitignore_patterns(text: str) -> list:
    """The non-blank lines of a .gitignore that are not comments."""
    return [line for line in nonblank_lines_of(text) if not line.startswith("#")]


class LangRunCase(InitCase):
    """One language step run in a set-up project, and checks shared by its tests."""

    LANG = "python"
    plugin = None
    project = None
    out = None

    @classmethod
    def run_step(cls, *extra: str, base_files=None, repo_option: bool = True, **lang_args):
        """Sets up a project, keeps what the step may change, and runs the step once."""
        cls.plugin = cls.plugin or shared_plugin(hooks=True)
        cls.project = lang_project(cls.plugin, base_files=base_files)
        cls.prepare()
        cls.before = cls.project.snapshot()
        cls.out = run_lang(cls.project, cls.plugin, cls.LANG, *extra, repo_option=repo_option,
                           **lang_args)
        cls.after = cls.project.snapshot()

    @classmethod
    def prepare(cls) -> None:
        """Changes the set-up project before the step runs (nothing by default)."""

    def report(self) -> dict:
        """The step's JSON report, after checking it exited 0."""
        return self.report_of(self.out, 0)

    def text_before(self, path: str) -> str:
        """A file's text before the step ran."""
        return self.before.files[path].decode("utf-8").replace("\r\n", "\n")


class PythonLangTest(LangRunCase):
    """lang python in a project with no pyproject.toml, run from inside the project."""

    @classmethod
    def setUpClass(cls):
        """Runs the Python step once without --repo."""
        cls.run_step(repo_option=False)

    def test_lang_exits_zero_with_an_ok_report(self):
        """The step exits 0 and reports the language with no conflict or problem."""
        report = self.report()
        self.assertEqual(report["command"], "lang")
        self.assertEqual(report["language"], "python")
        self.assertIs(report["dry_run"], False)
        self.assertIs(report["changed"], True)
        self.assertEqual(report["version"], plugin_version(self.plugin))
        self.assertEqual((report["conflicts"], report["problems"]), ([], []))

    def test_lang_report_has_every_interface_key(self):
        """The report holds part 1's keys with lang's values, and language, legacy, environment."""
        report = self.report()
        self.assertLessEqual(set(REPORT_KEYS) | set(LANG_REPORT_KEYS), set(report))
        self.assertIsNone(report["hooks_path"])
        self.assertIsNone(report["email"])
        self.assertEqual(report["differences"], [])
        self.assertEqual(report["executable"], [])

    def test_lang_report_describes_the_skipped_environment(self):
        """With --no-env, environment names the defaults, is skipped, and ran nothing."""
        environment = self.report()["environment"]
        self.assertEqual(sorted(environment), sorted(ENVIRONMENT_KEYS))
        self.assertEqual(environment, {
            "name": PROJECT, "prefix": None, "series": ["."], "lock": LOCKS["python"],
            "skipped": True, "exists": None, "commands": []})

    def test_lang_lists_each_file_with_its_action(self):
        """Exactly the files of the interface's Python table, with their actions."""
        self.assertEqual(self.actions_of(self.report()), lang_actions("python"))

    def test_lang_stages_every_written_file(self):
        """stage is the sorted list of every path whose action is not keep."""
        self.assertEqual(self.report()["stage"], lang_stage("python"))

    def test_lang_changes_exactly_the_staged_files(self):
        """No other file changes, the progress file included, and git config stays."""
        self.report()
        self.assertEqual(changed_paths(self.before, self.after), lang_stage("python"))
        self.assertEqual(self.before.config, self.after.config)
        self.assertEqual(self.project.status_paths(), set(lang_stage("python")))

    def test_lang_next_steps_name_the_commit_subject(self):
        """next_steps names the commit subject of the language step's PR."""
        self.assertIn(TITLES["python"], " ".join(self.report()["next_steps"]))

    def test_lang_fills_the_lang_table(self):
        """[lang] gets the pack's name and source roots, the environment, and the series."""
        self.report()
        data = tomllib.loads(self.project.read(CONFIG))
        self.assertEqual(data["lang"], lang_values("python"))

    def test_lang_config_passes_troy_check_parser(self):
        """troy-check's parser accepts the config and reads the [lang] table."""
        self.report()
        config = parse_config_with_troy_check(self.project.read(CONFIG))
        self.assertEqual(config.lang, lang_values("python"))
        self.assertEqual(config.legacy_tests, [])

    def test_lang_config_changes_nothing_outside_the_lang_table(self):
        """Every line before [lang] and every table after it are as setup wrote them."""
        self.report()
        before = split_lang_table(self.text_before(CONFIG))
        after = split_lang_table(self.project.read(CONFIG))
        self.assertEqual(after[0], before[0])
        self.assertEqual(after[2], before[2])
        self.assertEqual(tomllib.loads(self.project.read(CONFIG))["tests"], {"legacy": []})

    def test_lang_config_keeps_the_lang_comments_before_the_keys(self):
        """[lang] keeps the default file's comment lines, and its four keys follow them."""
        self.report()
        old = [line for line in split_lang_table(self.text_before(CONFIG))[1] if line.strip()]
        new = [line for line in split_lang_table(self.project.read(CONFIG))[1] if line.strip()]
        comments = [line for line in new if line.startswith("#")]
        keys = [line for line in new if not line.startswith("#")]
        self.assertNotEqual(old, [])
        self.assertTrue(all(line.startswith("#") for line in old), old)
        remaining = iter(comments)
        self.assertEqual([line for line in old if line not in remaining], [], "a comment is lost")
        self.assertEqual(new, comments + keys)
        self.assertEqual(len(keys), 4, new)

    def test_lang_writes_the_pack_environment_with_its_name(self):
        """environment.yml is the pack's file with the project's name as the environment."""
        self.report()
        self.assertEqual(self.project.read_bytes("environment.yml").decode("utf-8"),
                         expected_environment(self.plugin, "python"))
        self.assertIn(f'name: "{PROJECT}"', self.project.read("environment.yml"))

    def test_lang_creates_pyproject_from_the_new_pack_file(self):
        """pyproject.toml is pyproject-project.toml filled in, then the pack's tables."""
        self.report()
        self.assertEqual(self.project.read_bytes("pyproject.toml").decode("utf-8"),
                         expected_new_pyproject(self.plugin))

    def test_lang_created_pyproject_names_project_and_package(self):
        """The created pyproject.toml is valid TOML with the name, version, and package."""
        self.report()
        data = tomllib.loads(self.project.read("pyproject.toml"))
        self.assertEqual(data["build-system"],
                         {"requires": ["hatchling>=1.25"], "build-backend": "hatchling.build"})
        project = {key: data["project"][key]
                   for key in ("name", "version", "requires-python", "dependencies")}
        self.assertEqual(project, {"name": PROJECT, "version": "0.1.0",
                                   "requires-python": ">=3.13", "dependencies": []})
        self.assertEqual(data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"],
                         ["src/habit_tracker"])

    def test_lang_created_pyproject_holds_the_pack_tables(self):
        """The pack's tables in pyproject.toml equal the pack's fragment."""
        self.report()
        data = tomllib.loads(self.project.read("pyproject.toml"))
        fragment = tomllib.loads(pack_text(self.plugin, "python", "pyproject.toml"))
        self.assertEqual(data["project"]["optional-dependencies"],
                         fragment["project"]["optional-dependencies"])
        for tool, settings in fragment["tool"].items():
            with self.subTest(tool=tool):
                self.assertEqual(data["tool"][tool], settings)

    def test_lang_adds_the_pack_job_to_the_workflow(self):
        """The workflow is F02's workflow, a blank line, and the pack's job."""
        self.report()
        self.assertEqual(self.project.read_bytes(WORKFLOW).decode("utf-8"),
                         expected_workflow(self.plugin, "python"))

    def test_lang_workflow_keeps_the_troy_check_job_under_jobs(self):
        """Both jobs sit under jobs:, troy-check first."""
        self.report()
        lines = self.project.read(WORKFLOW).split("\n")
        self.assertIn("jobs:", lines)
        jobs = [line for line in lines[lines.index("jobs:"):]
                if line.startswith("  ") and not line.startswith("   ") and line.endswith(":")]
        self.assertEqual(jobs, ["  troy-check:", "  troy-code:"])

    def test_lang_adds_the_python_lines_to_gitignore(self):
        """.gitignore keeps setup's line and gains the Python pack's lines."""
        self.report()
        old = gitignore_patterns(self.text_before(".gitignore"))
        new = gitignore_patterns(self.project.read(".gitignore"))
        self.assertEqual(old, [PROGRESS])
        self.assertEqual(new[:len(old)], old)
        self.assertEqual(sorted(new[len(old):]), sorted(GITIGNORE_LINES["python"]))

    def test_lang_record_names_the_pack_and_both_steps(self):
        """The install record keeps the version and setup date and adds the lang step and pack."""
        self.report()
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(record["plugin"]["version"], plugin_version(self.plugin))
        self.assertEqual(record["steps"], {"setup": DATE, "lang": LANG_DATE})
        self.assertEqual(record["lang"]["name"], "python")

    def test_lang_record_covers_exactly_the_owned_files(self):
        """[files] is setup's owned files; the build files, config, and lock are not in it."""
        self.report()
        files = tomllib.loads(self.project.read(RECORD))["files"]
        self.assertEqual(sorted(files), sorted(lang_owned(self.plugin, "python")))
        for path in ("environment.yml", "pyproject.toml", CONFIG, LOCKS["python"]):
            self.assertNotIn(path, files)

    def test_lang_record_hashes_the_new_workflow(self):
        """The workflow's hash is the new workflow's, and every hash matches its file."""
        self.report()
        files = tomllib.loads(self.project.read(RECORD))["files"]
        old = tomllib.loads(self.text_before(RECORD))["files"]
        self.assertEqual(files[WORKFLOW], sha256_lf(self.project.read_bytes(WORKFLOW)))
        self.assertNotEqual(files[WORKFLOW], old[WORKFLOW])
        for path, digest in files.items():
            with self.subTest(path=path):
                self.assertEqual(digest, sha256_lf(self.project.read_bytes(path)))

    def test_lang_writes_only_lf_line_endings(self):
        """No file the step writes contains a CRLF."""
        for path in self.report()["stage"]:
            with self.subTest(path=path):
                self.assertNotIn(b"\r\n", self.project.read_bytes(path))

    def test_lang_lists_no_legacy_tests_in_a_new_project(self):
        """A project with no tests has an empty legacy list in the report and the config."""
        self.assertEqual(self.report()["legacy"], [])


class PythonExistingFilesTest(LangRunCase):
    """lang python in a project with its own pyproject.toml, .gitignore lines, and tests."""

    @classmethod
    def setUpClass(cls):
        """Runs the Python step once, with untracked and ignored test files present."""
        base = {"pyproject.toml": OWN_PYPROJECT, ".gitignore": "build/\nreports/\n.venv/\n",
                **PY_LEGACY_FILES}
        cls.run_step(base_files=base)

    @classmethod
    def prepare(cls) -> None:
        """Adds an untracked test, an ignored one, and one under .troy-mode/."""
        cls.project.write("tests/test_new.py", "def test_new():\n    assert True\n")
        cls.project.write("build/test_generated.py", "")
        cls.project.write(".troy-mode/scratch/test_local.py", "")

    def test_lang_appends_the_pack_tables_to_an_existing_pyproject(self):
        """The project's text stays first, then a blank line and the pack's tables."""
        report = self.report()
        self.assertEqual(self.actions_of(report)["pyproject.toml"], "append")
        self.assertIn("pyproject.toml", report["stage"])
        self.assertEqual(self.project.read_bytes("pyproject.toml").decode("utf-8"),
                         join_parts(OWN_PYPROJECT, pack_text(self.plugin, "python",
                                                             "pyproject.toml")))

    def test_lang_keeps_the_project_tables_of_an_existing_pyproject(self):
        """The result is valid TOML with the project's own tables and the pack's."""
        self.report()
        data = tomllib.loads(self.project.read("pyproject.toml"))
        own = tomllib.loads(OWN_PYPROJECT)
        self.assertEqual(data["build-system"], own["build-system"])
        self.assertEqual({k: v for k, v in data["project"].items() if k != "optional-dependencies"},
                         own["project"])
        self.assertEqual(data["tool"]["black"], own["tool"]["black"])
        self.assertEqual(data["tool"]["hatch"], own["tool"]["hatch"])
        fragment = tomllib.loads(pack_text(self.plugin, "python", "pyproject.toml"))
        self.assertEqual(data["tool"]["ruff"], fragment["tool"]["ruff"])

    def test_lang_lists_existing_tests_as_legacy(self):
        """Tracked and untracked tests matching the pack's patterns are legacy, sorted."""
        report = self.report()
        self.assertEqual(report["legacy"], PY_LEGACY)
        self.assertEqual(tomllib.loads(self.project.read(CONFIG))["tests"]["legacy"], PY_LEGACY)

    def test_lang_legacy_list_passes_troy_check_parser(self):
        """troy-check reads the legacy list from the config."""
        self.report()
        config = parse_config_with_troy_check(self.project.read(CONFIG))
        self.assertEqual(config.legacy_tests, PY_LEGACY)

    def test_lang_legacy_list_changes_only_the_legacy_line(self):
        """Outside [lang] and the legacy line, the config is as setup wrote it."""
        self.report()
        before = split_lang_table(self.text_before(CONFIG))
        after = split_lang_table(self.project.read(CONFIG))
        self.assertEqual((after[0], after[2]), (before[0], before[2]))

    def test_lang_adds_only_the_missing_gitignore_lines(self):
        """Lines the .gitignore already has are not added again."""
        report = self.report()
        self.assertEqual(self.actions_of(report)[".gitignore"], "append")
        old = gitignore_patterns(self.text_before(".gitignore"))
        new = gitignore_patterns(self.project.read(".gitignore"))
        self.assertEqual(old, ["build/", "reports/", ".venv/", PROGRESS])
        self.assertEqual(new[:len(old)], old)
        self.assertEqual(sorted(new[len(old):]),
                         sorted(set(GITIGNORE_LINES["python"]) - {"reports/"}))

    def test_lang_leaves_the_existing_code_and_tests_alone(self):
        """The project's own files keep their content and stay out of stage."""
        report = self.report()
        for path, text in PY_LEGACY_FILES.items():
            with self.subTest(path=path):
                self.assertEqual(self.project.read_bytes(path), text.encode("utf-8"))
                self.assertNotIn(path, report["stage"])


class CppLangTest(LangRunCase):
    """lang cpp in a project with no CMakeLists.txt, run with --repo."""

    LANG = "cpp"

    @classmethod
    def setUpClass(cls):
        """Runs the C/C++ step once."""
        cls.run_step()

    def test_lang_cpp_exits_zero_with_an_ok_report(self):
        """The step exits 0, names cpp, and reports no conflict or problem."""
        report = self.report()
        self.assertEqual((report["command"], report["language"]), ("lang", "cpp"))
        self.assertEqual((report["conflicts"], report["problems"]), ([], []))
        self.assertEqual(report["executable"], [])
        self.assertEqual(report["environment"]["lock"], LOCKS["cpp"])
        self.assertIs(report["environment"]["skipped"], True)

    def test_lang_cpp_lists_each_file_with_its_action(self):
        """Exactly the files of the interface's C/C++ table, with their actions."""
        self.assertEqual(self.actions_of(self.report()), lang_actions("cpp"))

    def test_lang_cpp_stages_every_written_file(self):
        """stage is sorted, every path but keep, and nothing else changed."""
        report = self.report()
        self.assertEqual(report["stage"], lang_stage("cpp"))
        self.assertEqual(changed_paths(self.before, self.after), lang_stage("cpp"))
        self.assertEqual(self.before.config, self.after.config)

    def test_lang_cpp_next_steps_name_the_commit_subject(self):
        """next_steps names the C/C++ commit subject."""
        self.assertIn(TITLES["cpp"], " ".join(self.report()["next_steps"]))

    def test_lang_cpp_copies_the_pack_files_unchanged(self):
        """Each whole pack file lands at its place with the pack's content, LF."""
        self.report()
        for path, data in lang_owned(self.plugin, "cpp").items():
            if path in CPP_COPIED:
                with self.subTest(path=path):
                    self.assertEqual(self.project.read_bytes(path), data)

    def test_lang_cpp_writes_environment_and_tool_requirements(self):
        """environment.yml is filled in, and requirements-tools.in is the pack's file."""
        self.report()
        self.assertEqual(self.project.read_bytes("environment.yml").decode("utf-8"),
                         expected_environment(self.plugin, "cpp"))
        self.assertEqual(self.project.read_bytes("requirements-tools.in").decode("utf-8"),
                         pack_text(self.plugin, "cpp", "requirements-tools.in"))

    def test_lang_cpp_creates_cmakelists_from_the_new_pack_file(self):
        """CMakeLists.txt is CMakeLists-project.txt with the project's name."""
        self.report()
        self.assertEqual(self.project.read_bytes("CMakeLists.txt").decode("utf-8"),
                         expected_new_cmakelists(self.plugin))

    def test_lang_cpp_created_cmakelists_has_the_three_lines(self):
        """The created file's lines are the minimum version, the project, and the include."""
        self.report()
        lines = [line for line in nonblank_lines_of(self.project.read("CMakeLists.txt"))
                 if not line.startswith("#")]
        self.assertEqual(lines, ["cmake_minimum_required(VERSION 3.28)",
                                 f"project({PROJECT} C CXX)", INCLUDE_LINE])

    def test_lang_cpp_fills_the_lang_table(self):
        """[lang] gets cpp, the include folders, the environment, and the series."""
        self.report()
        self.assertEqual(tomllib.loads(self.project.read(CONFIG))["lang"], lang_values("cpp"))
        config = parse_config_with_troy_check(self.project.read(CONFIG))
        self.assertEqual(config.lang, lang_values("cpp"))

    def test_lang_cpp_config_changes_nothing_outside_the_lang_table(self):
        """Every line before [lang] and every table after it are as setup wrote them."""
        self.report()
        before = split_lang_table(self.text_before(CONFIG))
        after = split_lang_table(self.project.read(CONFIG))
        self.assertEqual((after[0], after[2]), (before[0], before[2]))

    def test_lang_cpp_adds_the_pack_job_to_the_workflow(self):
        """The workflow is F02's workflow, a blank line, and the C/C++ pack's job."""
        self.report()
        self.assertEqual(self.project.read_bytes(WORKFLOW).decode("utf-8"),
                         expected_workflow(self.plugin, "cpp"))

    def test_lang_cpp_adds_build_and_reports_to_gitignore(self):
        """.gitignore keeps setup's line and gains build/ and reports/."""
        self.report()
        new = gitignore_patterns(self.project.read(".gitignore"))
        self.assertEqual(new[0], PROGRESS)
        self.assertEqual(sorted(new[1:]), sorted(GITIGNORE_LINES["cpp"]))

    def test_lang_cpp_record_owns_the_six_copied_pack_files(self):
        """[files] is setup's owned files plus the six copied pack files, with their hashes."""
        self.report()
        record = tomllib.loads(self.project.read(RECORD))
        self.assertEqual(record["lang"]["name"], "cpp")
        self.assertEqual(record["steps"], {"setup": DATE, "lang": LANG_DATE})
        self.assertEqual(sorted(record["files"]), sorted(lang_owned(self.plugin, "cpp")))
        for path in ("environment.yml", "requirements-tools.in", "CMakeLists.txt", CONFIG):
            self.assertNotIn(path, record["files"])
        for path, digest in record["files"].items():
            with self.subTest(path=path):
                self.assertEqual(digest, sha256_lf(self.project.read_bytes(path)))

    def test_lang_cpp_writes_only_lf_line_endings(self):
        """No file the step writes contains a CRLF."""
        for path in self.report()["stage"]:
            with self.subTest(path=path):
                self.assertNotIn(b"\r\n", self.project.read_bytes(path))


class CppExistingFilesTest(LangRunCase):
    """lang cpp in a project with its own CMakeLists.txt, .gitignore lines, and tests."""

    LANG = "cpp"

    @classmethod
    def setUpClass(cls):
        """Runs the C/C++ step once."""
        base = {"CMakeLists.txt": OWN_CMAKELISTS, ".gitignore": "build/\nreports/\n",
                **CPP_LEGACY_FILES}
        cls.run_step(base_files=base)

    def test_lang_cpp_keeps_a_cmakelists_that_includes_troy_cmake(self):
        """An existing CMakeLists.txt with the include is kept, unchanged and not staged."""
        report = self.report()
        self.assertEqual(self.actions_of(report)["CMakeLists.txt"], "keep")
        self.assertNotIn("CMakeLists.txt", report["stage"])
        self.assertEqual(self.project.read_bytes("CMakeLists.txt"), OWN_CMAKELISTS.encode())

    def test_lang_cpp_keeps_a_gitignore_that_has_every_line(self):
        """A .gitignore that already lists build/ and reports/ is kept and not staged."""
        report = self.report()
        self.assertEqual(self.actions_of(report)[".gitignore"], "keep")
        self.assertNotIn(".gitignore", report["stage"])
        self.assertEqual(self.project.read(".gitignore"), self.text_before(".gitignore"))

    def test_lang_cpp_stages_everything_but_the_kept_files(self):
        """stage lists the other files of the step."""
        self.assertEqual(self.report()["stage"],
                         lang_stage("cpp", build="keep", gitignore="keep"))

    def test_lang_cpp_lists_existing_tests_as_legacy(self):
        """Only files matching the C/C++ test patterns are legacy, sorted."""
        report = self.report()
        self.assertEqual(report["legacy"], CPP_LEGACY)
        self.assertEqual(tomllib.loads(self.project.read(CONFIG))["tests"]["legacy"], CPP_LEGACY)


class LangOptionsTest(InitCase):
    """--project-name, --environment, --series, --package, and the default date."""

    @classmethod
    def setUpClass(cls):
        """Uses the plugin with git hooks."""
        cls.plugin = shared_plugin(hooks=True)

    def ran(self, lang: str, *extra: str, date=LANG_DATE):
        """The shared set-up project after one successful language step with the options."""
        project = shared_lang_project(self.plugin)
        self.report_of(run_lang(project, self.plugin, lang, *extra, date=date), 0)
        return project

    def test_lang_uses_project_name_environment_and_series(self):
        """The name, the derived package, the environment, and the series in their places."""
        project = self.ran("python", "--project-name", "TroyVoice", "--environment",
                           "voice-env", "--series", "../core", "--series", ".", "--series",
                           "../ui")
        self.assertEqual(project.read_bytes("pyproject.toml").decode("utf-8"),
                         expected_new_pyproject(self.plugin, "TroyVoice", "troy_voice"))
        self.assertEqual(project.read("environment.yml"),
                         expected_environment(self.plugin, "python", "voice-env"))
        self.assertEqual(tomllib.loads(project.read(CONFIG))["lang"],
                         lang_values("python", "voice-env", ["../core", ".", "../ui"]))

    def test_lang_cpp_uses_project_name_and_adds_this_project_last(self):
        """The name reaches CMakeLists.txt and the environment; "." ends the series."""
        project = self.ran("cpp", "--project-name", "Voice", "--series", "../core",
                           "--series", "../ui")
        cmakelists = project.read("CMakeLists.txt")
        self.assertEqual(cmakelists, expected_new_cmakelists(self.plugin, "Voice"))
        self.assertIn("project(Voice C CXX)", cmakelists.split("\n"))
        self.assertEqual(project.read("environment.yml"),
                         expected_environment(self.plugin, "cpp", "Voice"))
        self.assertEqual(tomllib.loads(project.read(CONFIG))["lang"],
                         lang_values("cpp", "Voice", ["../core", "../ui", "."]))

    def test_lang_package_option_names_the_wheel_package_and_date_defaults_to_today(self):
        """--package replaces the derived package; without --date, lang is dated today."""
        before = datetime.date.today().isoformat()
        project = self.ran("python", "--package", "habits", date=None)
        today = {before, datetime.date.today().isoformat()}
        self.assertEqual(project.read("pyproject.toml"),
                         expected_new_pyproject(self.plugin, PROJECT, "habits"))
        self.assertIn(tomllib.loads(project.read(RECORD))["steps"]["lang"], today)

    def test_lang_derives_the_package_in_snake_case(self):
        """Dots, dashes, and capitals become one snake_case package name."""
        project = self.ran("python", "--project-name", "web.API-v2")
        packages = tomllib.loads(project.read("pyproject.toml"))["tool"]["hatch"]["build"][
            "targets"]["wheel"]["packages"]
        self.assertEqual(packages, ["src/web_api_v2"])
        self.assertEqual(tomllib.loads(project.read("pyproject.toml"))["project"]["name"],
                         "web.API-v2")


class LangDryRunTest(InitCase):
    """A dry run plans the language step and changes nothing."""

    def test_lang_dry_run_reports_the_plan_and_changes_nothing(self):
        """The dry run reports the real run's actions and stage; no file or config changes."""
        plugin = shared_plugin(hooks=True)
        for lang in ("python", "cpp"):
            with self.subTest(lang=lang):
                project = shared_lang_project(plugin)
                before = project.snapshot()
                report = self.report_of(run_lang(project, plugin, lang, "--dry-run"), 0)
                self.assertIs(report["dry_run"], True)
                self.assertIs(report["changed"], True)
                self.assertEqual(self.actions_of(report), lang_actions(lang))
                self.assertEqual(report["stage"], lang_stage(lang))
                self.assert_unchanged(before, project.snapshot())


class LangFromCrlfPluginTest(InitCase):
    """The language step from a plugin whose pack files have CRLF line endings."""

    @classmethod
    def setUpClass(cls):
        """Runs both languages once from a CRLF copy of the plugin, keeping the files."""
        cls.plugin = make_plugin(hooks=True, crlf=True)
        crlf_lang(cls.plugin)
        cls.outs, cls.files = {}, {}
        for lang in ("python", "cpp"):
            project = shared_lang_project(cls.plugin)
            cls.outs[lang] = run_lang(project, cls.plugin, lang)
            cls.files[lang] = project.files()

    def test_lang_from_crlf_plugin_writes_only_lf(self):
        """Every file the step writes has LF line endings, though its source has CRLF."""
        self.assertIn(b"\r\n", (self.plugin / "troy-mode/lang/cpp/.clang-tidy").read_bytes())
        for lang, files in self.files.items():
            report = self.report_of(self.outs[lang], 0)
            for path in report["stage"]:
                with self.subTest(lang=lang, path=path):
                    self.assertNotIn(b"\r\n", files[path])

    def test_lang_from_crlf_plugin_writes_the_lf_content(self):
        """The workflow, the environment, and the build file equal their LF versions."""
        for lang, files in self.files.items():
            self.report_of(self.outs[lang], 0)
            expected = {WORKFLOW: expected_workflow(self.plugin, lang),
                        "environment.yml": expected_environment(self.plugin, lang)}
            expected[BUILD_FILES[lang]] = (expected_new_pyproject(self.plugin) if lang == "python"
                                           else expected_new_cmakelists(self.plugin))
            for path, text in expected.items():
                with self.subTest(lang=lang, path=path):
                    self.assertEqual(files[path].decode("utf-8"), text)

    def test_lang_from_crlf_plugin_hashes_the_lf_files(self):
        """The record's hashes match the owned files, which equal the LF pack files."""
        self.report_of(self.outs["cpp"], 0)
        files = self.files["cpp"]
        record = tomllib.loads(files[RECORD].decode("utf-8"))["files"]
        for path, data in lang_owned(self.plugin, "cpp").items():
            with self.subTest(path=path):
                self.assertEqual(files[path], data)
                self.assertEqual(record[path], sha256_lf(data))


if __name__ == "__main__":
    unittest.main()
