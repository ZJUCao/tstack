"""Tests of the C/C++ pack's files and its sample (F03 design 9 and 10, D25, F06 5.6 and 8).

The pack's files are checked against the design. The sample's CI workflow
is checked against the pack's CI job, so the sample runs the same steps a
project runs.
"""

import json
import os
import re
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from pack_helpers import (CODE_GUARD, LOOK_FOR_CODE, PINNED, SAMPLE_EMAIL, SAMPLE_ONLY_STEPS,
                          TROY_MODE, WORKFLOWS, bash_path, git, git_bytes, lf_bytes, pack_patterns,
                          pack_workflow, parse_config, run_build, run_step_script, setup_paths,
                          sha256_lf, step_blocks, steps, uses)

PACK = TROY_MODE / "lang" / "cpp"
SAMPLE = TROY_MODE / "samples" / "cpp"
SAMPLE_WORKFLOW = WORKFLOWS / "troy-cpp-sample.yml"
DESIGN_TITLE = "[F01 1/6 design] Count words in a text"
SETUP_TITLE = "[docs] Set up textstats with troy-mode"
COPIED = ("CMakePresets.json", "cmake/troy.cmake", ".clang-format", ".clang-tidy",
          "include/troy/not_implemented.h", ".troy-mode/lang/cpp/Doxyfile")


def text(name: str) -> str:
    """Reads a pack file."""
    return (PACK / name).read_text(encoding="utf-8")


def settings(name: str) -> dict[str, str]:
    """Reads "KEY = value" lines of a Doxyfile-style file."""
    return {m.group(1): m.group(2).strip()
            for line in text(name).splitlines() if (m := re.match(r"^(\w+)\s*=\s*(.*)$", line))}


def is_code(path: str) -> bool:
    """Whether a path is under the C/C++ pack's roots: src/, or include/ but not include/troy/."""
    return path.startswith("src/") or (path.startswith("include/")
                                       and not path.startswith("include/troy/"))


class PackFileTests(unittest.TestCase):
    """The pack's files hold what F03 design section 9 says."""

    def test_pack_has_the_files_of_design_section_2(self) -> None:
        """The pack holds the design's files, the tool requirements, and the new-project file."""
        names = {p.relative_to(PACK).as_posix() for p in PACK.rglob("*") if p.is_file()}
        self.assertEqual({"README.md", "README.zh-CN.md", "environment.yml", "CMakePresets.json",
                          "cmake/troy.cmake", "Doxyfile", ".clang-format", ".clang-tidy",
                          "config.toml", "workflow-job.yml", "include/troy/not_implemented.h",
                          "requirements-tools.in", "CMakeLists-project.txt"}, names)

    def test_environment_has_the_build_tools_but_no_compiler_or_googletest(self) -> None:
        """mamba installs the tools of 9.2; GoogleTest comes from CMake (D25)."""
        lines = [line.strip() for line in text("environment.yml").splitlines()
                 if line.strip() and not line.startswith("#")]
        self.assertEqual(['name: "{{environment}}"', "channels:", "- conda-forge", "dependencies:",
                          "- python=3.13", "- uv", "- cmake", "- ninja", "- doxygen",
                          "- clang-format=23", "- clang-tools=23", "- clang-23"], lines)

    def test_tool_requirements_name_gcovr_and_lizard(self) -> None:
        """uv installs gcovr and lizard, the pack's Python tools."""
        names = {re.split(r"[<>=]", line)[0] for line in text("requirements-tools.in").splitlines()
                 if line and not line.startswith("#")}
        self.assertEqual({"gcovr", "lizard"}, names)

    def test_config_fragment_is_valid_troy_check_config(self) -> None:
        """The config tables, once filled in, pass troy-check's config validation."""
        config = parse_config(text("config.toml").replace("{{environment}}", "sample-env"))
        self.assertEqual("cpp", config.lang["name"])
        self.assertEqual(["include", "src"], config.lang["include_dirs"])
        self.assertEqual("sample-env", config.lang["environment"])
        for pattern in ("CMakeLists.txt", "**/CMakeLists.txt", "cmake/**", "CMakePresets.json"):
            self.assertIn(pattern, config.paths["dependencies"])
        self.assertIn("**/*_test.cc", config.paths["tests"])
        self.assertIn(".clang-tidy", config.paths["config"])
        self.assertIn("include/troy/not_implemented.h", config.paths["config"])

    def test_new_project_cmakelists_has_the_three_lines(self) -> None:
        """CMakeLists-project.txt sets the minimum version, names the project, and includes troy."""
        lines = [line.strip() for line in text("CMakeLists-project.txt").splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(["cmake_minimum_required(VERSION 3.28)", "project({{project-name}} C CXX)",
                          "include(cmake/troy.cmake)"], lines)
        self.assertEqual({"{{project-name}}"},
                         set(re.findall(r"\{\{[^}]*\}\}", text("CMakeLists-project.txt"))))

    def test_readmes_list_the_new_project_file(self) -> None:
        """Both READMEs' files tables have a row for CMakeLists-project.txt."""
        for name in ("README.md", "README.zh-CN.md"):
            with self.subTest(readme=name):
                rows = [line for line in text(name).splitlines()
                        if re.match(r"^\| \[?`CMakeLists-project\.txt`", line)]
                self.assertEqual(1, len(rows), name)

    def test_cmake_settings(self) -> None:
        """troy.cmake pins GoogleTest, turns off module scans, and adds coverage."""
        cmake = text("cmake/troy.cmake")
        self.assertRegex(cmake, r"googletest-1\.18\.0\.tar\.gz\s+URL_HASH SHA256=[0-9a-f]{64}")
        self.assertIn("set(CMAKE_CXX_SCAN_FOR_MODULES OFF)", cmake)
        self.assertIn("add_compile_options(--coverage -O0)", cmake)
        self.assertLess(cmake.index("FetchContent_MakeAvailable(googletest)"),
                        cmake.index("add_compile_options("),
                        "GoogleTest must be added before the coverage and warning options")
        self.assertIn("gtest_discover_tests(", cmake)

    def test_presets(self) -> None:
        """coverage builds with GCC and gcov; msvc builds without coverage (D22)."""
        presets = json.loads(text("CMakePresets.json"))
        configure = {p["name"]: p for p in presets["configurePresets"]}
        coverage = configure["coverage"]["cacheVariables"]
        self.assertEqual(("Ninja", "g++", "ON", "ON"),
                         (configure["coverage"]["generator"], coverage["CMAKE_CXX_COMPILER"],
                          coverage["TROY_COVERAGE"], coverage["CMAKE_EXPORT_COMPILE_COMMANDS"]))
        self.assertNotIn("TROY_COVERAGE", configure["msvc"].get("cacheVariables", {}))
        for kind in ("buildPresets", "testPresets"):
            self.assertEqual({"coverage", "msvc"}, {p["name"] for p in presets[kind]})

    def test_doxyfile_warns_about_every_undocumented_declaration(self) -> None:
        """Doxygen's settings follow design 9.3 and write the log troy-check reads."""
        doxy = settings("Doxyfile")
        for key in ("WARN_IF_UNDOCUMENTED", "EXTRACT_PRIVATE", "EXTRACT_STATIC",
                    "EXTRACT_ANON_NSPACES"):
            self.assertEqual("YES", doxy[key], key)
        self.assertEqual("reports/doxygen.log", doxy["WARN_LOGFILE"])
        self.assertEqual('"$file:$line: $text"', doxy["WARN_FORMAT"])
        self.assertEqual("include src", doxy["INPUT"])

    def test_format_and_lint_settings(self) -> None:
        """clang-format uses Google style; clang-tidy runs bugprone and performance checks."""
        self.assertIn("BasedOnStyle: Google", text(".clang-format"))
        tidy = text(".clang-tidy")
        for check in ("-*,", "bugprone-*,", "performance-*,"):
            self.assertIn(check, tidy)
        self.assertIn('WarningsAsErrors: "*"', tidy)

    def test_not_implemented_is_the_mock_exception(self) -> None:
        """Mock bodies throw troy::NotImplemented, a std::logic_error (design 4.2)."""
        header = text("include/troy/not_implemented.h")
        self.assertIn("namespace troy {", header)
        self.assertIn("class NotImplemented : public std::logic_error {", header)

    def test_actions_are_pinned_to_commits(self) -> None:
        """Every action in the pack's job and the sample's workflow is pinned to a SHA."""
        for path in (PACK / "workflow-job.yml", SAMPLE_WORKFLOW):
            for action, comment in uses(path):
                with self.subTest(path=path.name, action=action):
                    self.assertRegex(action, PINNED)
                    self.assertRegex(comment, r"^# v\d+\.\d+\.\d+$")

    def test_job_runs_the_commands_of_design_section_9_4(self) -> None:
        """The job builds, formats, lints, tests, measures, checks docs, and runs troy-check."""
        runs = "\n".join(body for _, body in steps(PACK / "workflow-job.yml"))
        for command in ("uv pip install -r requirements-tools.lock", "cmake --preset coverage",
                        "cmake --build --preset coverage", "clang-format --dry-run --Werror",
                        "clang-tidy -p build/coverage", "ctest --preset coverage --output-junit",
                        "--cobertura reports/coverage.xml", "doxygen .troy-mode/lang/cpp/Doxyfile",
                        '/troy_check.py" code', "--doc-warnings reports/doxygen.log"):
            self.assertIn(command, runs)
        self.assertIn("fetch-depth: 0", text("workflow-job.yml"))

    def test_sample_ci_runs_the_same_steps_as_the_pack(self) -> None:
        """The sample's workflow runs the pack's steps unchanged, plus its own two."""
        pack = steps(PACK / "workflow-job.yml")
        sample = [s for s in steps(SAMPLE_WORKFLOW) if s[0] not in SAMPLE_ONLY_STEPS]
        self.assertEqual(8, len(pack))
        self.assertEqual(pack, sample)
        self.assertEqual(uses(PACK / "workflow-job.yml"), uses(SAMPLE_WORKFLOW))


class NoCodeGuardTests(unittest.TestCase):
    """The pack's job skips its code steps until the PR has code (F06 design 5.6, D50)."""

    def test_job_looks_for_code_right_after_checkout(self) -> None:
        """The first step after checkout is Look for code, with id code and no condition."""
        blocks = step_blocks(PACK / "workflow-job.yml")
        self.assertEqual(10, len(blocks))
        self.assertTrue(blocks[0].get("uses", "").startswith("actions/checkout@"), blocks[0])
        self.assertEqual(LOOK_FOR_CODE, blocks[1].get("name"))
        self.assertEqual("code", blocks[1].get("id"))
        self.assertNotIn("if", blocks[1])

    def test_every_later_step_of_the_job_needs_code(self) -> None:
        """Each step after Look for code, uses: steps included, runs only when code was found."""
        blocks = step_blocks(PACK / "workflow-job.yml")
        self.assertEqual(8, len(blocks[2:]))
        self.assertTrue(any("uses" in block for block in blocks[2:]))
        for block in blocks[2:]:
            with self.subTest(step=block.get("name") or block.get("uses")):
                self.assertEqual(CODE_GUARD, block.get("if"))

    def test_look_for_code_lists_src_and_include_but_not_include_troy(self) -> None:
        """The step asks git ls-files about src and include, leaving out include/troy/."""
        script = dict(steps(PACK / "workflow-job.yml"))[LOOK_FOR_CODE]
        for part in ("git ls-files", "src", "include", "include/troy", "found=true",
                     "found=false", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY", "No code yet"):
            with self.subTest(text=part):
                self.assertIn(part, script)

    def test_sample_looks_for_code_after_building_the_sample(self) -> None:
        """In the sample, Look for code follows the build, and every later step but the
        comparison needs code."""
        blocks = step_blocks(SAMPLE_WORKFLOW)
        names = [block.get("name") for block in blocks]
        look = names.index(LOOK_FOR_CODE)
        self.assertEqual("code", blocks[look].get("id"))
        self.assertLess(names.index("Build the sample"), look)
        later = blocks[look + 1:]
        self.assertEqual(9, len(later))
        for block in later:
            with self.subTest(step=block.get("name") or block.get("uses")):
                if block.get("name") == "Compare with the expected results":
                    self.assertNotEqual(CODE_GUARD, block.get("if"))
                else:
                    self.assertEqual(CODE_GUARD, block.get("if"))

    def test_sample_compares_with_and_without_code(self) -> None:
        """The comparison reads found, verifies a report, or verifies with --no-code."""
        compare = next(block for block in step_blocks(SAMPLE_WORKFLOW)
                       if block.get("name") == "Compare with the expected results")
        for part in ("steps.code.outputs.found", "verify cpp --pr", "--report", "--no-code"):
            with self.subTest(text=part):
                self.assertIn(part, compare["text"])

    def test_no_step_runs_exit(self) -> None:
        """No run step calls exit: in the job's login shell, exit reads ~/.bash_logout,
        which fails on the runner and turns exit 0 into 1."""
        for path in (PACK / "workflow-job.yml", SAMPLE_WORKFLOW):
            for block in step_blocks(path):
                with self.subTest(file=path.name, step=block.get("name")):
                    self.assertNotRegex(block["text"], r"(?m)^\s*exit\b")

    def test_sample_matrix_has_the_design_pr(self) -> None:
        """The sample runs the design PR, without code, and the tests and impl PRs."""
        self.assertRegex(SAMPLE_WORKFLOW.read_text(encoding="utf-8"),
                         r"(?m)^\s+pr: \[design, tests, impl\]\s*$")

    @unittest.skipIf(bash_path() is None, "no bash that runs like a runner's")
    def test_look_for_code_runs_on_heads_with_and_without_code(self) -> None:
        """Run with bash: only include/troy/ is no code; a project header or source is."""
        script = dict(steps(PACK / "workflow-job.yml"))[LOOK_FOR_CODE]
        if "${{" in script:
            self.skipTest("the step's script holds a workflow expression")
        pack_only = {"CMakeLists.txt": "project(x C CXX)\n", "cmake/troy.cmake": "",
                     "include/troy/not_implemented.h": "#pragma once\n"}
        cases = ((pack_only, "false"),
                 ({**pack_only, "include/textstats/counting.h": "#pragma once\n"}, "true"),
                 ({**pack_only, "src/main.cc": "int main() { return 0; }\n"}, "true"))
        for files, found in cases:
            with self.subTest(files=sorted(files), found=found):
                output, summary = run_step_script(script, files)
                self.assertEqual([f"found={found}"],
                                 [line for line in output if line.startswith("found=")])
                self.assertEqual(found == "false", "No code yet" in summary, summary)


class SampleSettingsTests(unittest.TestCase):
    """sample.toml after F06 design 8."""

    @classmethod
    def setUpClass(cls) -> None:
        """Reads sample.toml once."""
        cls.sample = tomllib.loads((SAMPLE / "sample.toml").read_text(encoding="utf-8"))

    def test_sample_names_project_and_environment_without_a_pack_table(self) -> None:
        """troy-init's functions install the pack, so sample.toml has no [pack] table."""
        self.assertNotIn("pack", self.sample)
        self.assertEqual("textstats", self.sample["project"])
        self.assertEqual("textstats-cpp", self.sample["environment"])

    def test_sample_marks_the_design_pr_as_having_no_code(self) -> None:
        """The design commit is PR design, with no_code and no expected results."""
        design = [c for c in self.sample["commits"] if c.get("pr") == "design"]
        self.assertEqual(1, len(design))
        self.assertEqual(DESIGN_TITLE, design[0]["title"])
        self.assertIs(True, design[0].get("no_code"))
        self.assertNotIn("expected", design[0])


class SampleTests(unittest.TestCase):
    """The C++ sample's lock and its built repository."""

    @classmethod
    def setUpClass(cls) -> None:
        """Builds the impl PR of the C++ sample once."""
        cls._tmp = tempfile.TemporaryDirectory(prefix="sample-")
        cls.repo = Path(cls._tmp.name) / "repo"
        cls.proc = run_build("build", "cpp", "--pr", "impl", "--out", str(cls.repo))

    @classmethod
    def tearDownClass(cls) -> None:
        """Deletes the built repository."""
        cls._tmp.cleanup()

    def root(self) -> str:
        """The built sample's first commit, after checking the build succeeded."""
        self.assertEqual(0, self.proc.returncode, self.proc.stderr)
        return git(self.repo, "rev-list", "--max-parents=0", "HEAD")

    def show(self, path: str) -> str:
        """A file's text in the first commit, with CRLF made LF."""
        return lf_bytes(git_bytes(self.repo, "show", f"{self.root()}:{path}")).decode("utf-8")

    def test_lock_pins_the_tools(self) -> None:
        """The sample's lock pins gcovr and lizard."""
        lock = (SAMPLE / "base" / "requirements-tools.lock").read_text(encoding="utf-8")
        self.assertIn("uv pip compile requirements-tools.in --universal", lock)
        for tool in ("gcovr", "lizard"):
            self.assertRegex(lock, rf"(?m)^{tool}==\d")

    def test_build_installs_the_pack_like_troy_init(self) -> None:
        """The first commit holds troy-check and every pack file at its place."""
        self.assertEqual(0, self.proc.returncode, self.proc.stderr)
        files = git(self.repo, "ls-tree", "-r", "--name-only", "main~4").splitlines()
        environment = self.show("environment.yml")
        for path in (".troy-mode/checks/troy_check.py", ".troy-mode/config.toml",
                     ".troy-mode/lang/cpp/Doxyfile", "CMakePresets.json", "cmake/troy.cmake",
                     ".clang-format", ".clang-tidy", "include/troy/not_implemented.h",
                     "requirements-tools.in", "requirements-tools.lock",
                     ".github/workflows/troy-mode.yml"):
            self.assertIn(path, files)
        self.assertIn('name: "textstats-cpp"', environment)
        self.assertEqual("[F01 5/6 impl] Count words in a text",
                         json.loads(self.proc.stdout)["PR_TITLE"])

    def test_first_commit_holds_every_file_setup_writes(self) -> None:
        """troy-check, the templates, the record, the config, the rules, PR template, workflow."""
        files = set(git(self.repo, "ls-tree", "-r", "--name-only", self.root()).splitlines())
        self.assertEqual([], sorted(set(setup_paths()) - files))

    def test_first_commit_records_git_hooks_as_executable(self) -> None:
        """git records every hook file in the first commit with mode 100755."""
        listing = git(self.repo, "ls-tree", "-r", self.root(), "--", ".troy-mode/checks/git-hooks")
        modes = {line.split("\t")[1]: line.split()[0] for line in listing.splitlines()}
        self.assertEqual(4, len(modes))
        self.assertEqual({"100755"}, set(modes.values()), modes)

    def test_build_leaves_hooks_off_and_the_progress_file_out(self) -> None:
        """core.hooksPath is unset, and no commit holds .troy-mode/progress.md."""
        self.root()
        proc = subprocess.run(["git", "-C", str(self.repo), "config", "--local", "--get",
                               "core.hooksPath"], capture_output=True, text=True, check=False)
        self.assertEqual(1, proc.returncode, proc.stdout)
        paths = git(self.repo, "log", "--all", "--format=", "--name-only").splitlines()
        self.assertNotIn(".troy-mode/progress.md", paths)

    def test_first_commit_config_is_setup_with_the_lang_table(self) -> None:
        """Every pack's patterns, the sample's email, and [lang] filled for the sample."""
        data = tomllib.loads(self.show(".troy-mode/config.toml"))
        self.assertEqual(SAMPLE_EMAIL, parse_config(self.show(".troy-mode/config.toml"))
                         .commit_email)
        self.assertEqual({"name": "cpp", "include_dirs": ["include", "src"],
                          "environment": "textstats-cpp", "series": ["."]}, data["lang"])
        for key, patterns in pack_patterns().items():
            with self.subTest(key=key):
                self.assertEqual(sorted(patterns), sorted(set(data["paths"][key])))

    def test_first_commit_record_owns_the_copied_pack_files(self) -> None:
        """The install record has [lang] name and the hash of each owned pack file."""
        record = tomllib.loads(self.show(".troy-mode/install.toml"))
        self.assertEqual("cpp", record["lang"]["name"])
        for path in COPIED:
            with self.subTest(path=path):
                self.assertEqual(sha256_lf((self.repo / path).read_bytes()), record["files"][path])
        for path in ("environment.yml", "requirements-tools.in", "CMakeLists.txt"):
            self.assertNotIn(path, record["files"])

    def test_first_commit_rules_and_workflow_are_troy_inits(self) -> None:
        """The rules table names textstats, and the workflow is F02's plus the pack's job."""
        rules = self.show("docs/rules.md")
        self.assertIn("# textstats rules", rules.splitlines())
        self.assertNotIn("{{", rules)
        self.assertEqual(pack_workflow("cpp"), self.show(".github/workflows/troy-mode.yml"))

    def test_first_commit_keeps_the_sample_lock_and_cmakelists(self) -> None:
        """The sample's own lock and CMakeLists.txt are the ones in the first commit."""
        for path in ("requirements-tools.lock", "CMakeLists.txt"):
            with self.subTest(path=path):
                expected = lf_bytes((SAMPLE / "base" / path).read_bytes()).decode("utf-8")
                self.assertEqual(expected, self.show(path))


class BuildDesignPrTests(unittest.TestCase):
    """The design PR: setup and the language step, but no code (F06 design 8)."""

    def test_design_pr_head_has_no_code(self) -> None:
        """No file of the PR's head is under src/, or under include/ but include/troy/."""
        with tempfile.TemporaryDirectory(prefix="sample-") as tmp:
            repo = Path(tmp) / "repo"
            proc = run_build("build", "cpp", "--pr", "design", "--out", str(repo))
            self.assertEqual(0, proc.returncode, proc.stderr)
            files = git(repo, "ls-tree", "-r", "--name-only", "pr").splitlines()
            log = git(repo, "log", "--format=%s", "main").splitlines()
        self.assertEqual(DESIGN_TITLE, json.loads(proc.stdout)["PR_TITLE"])
        self.assertEqual([SETUP_TITLE], log)
        self.assertIn("include/troy/not_implemented.h", files)
        self.assertEqual([], [path for path in files if is_code(path)])

    def test_verify_no_code_passes_on_the_design_pr(self) -> None:
        """verify --no-code exits 0 on the PR sample.toml marks no_code."""
        proc = run_build("verify", "cpp", "--pr", "design", "--no-code")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
