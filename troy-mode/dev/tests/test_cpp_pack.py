"""Tests of the C/C++ pack's files and its sample (F03 design 9 and 10, D25).

The pack's files are checked against the design. The sample's CI workflow
is checked against the pack's CI job, so the sample runs the same steps a
project runs.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path

from pack_helpers import (PINNED, SAMPLE_ONLY_STEPS, TROY_MODE, WORKFLOWS, git, parse_config,
                          run_build, steps, uses)

PACK = TROY_MODE / "lang" / "cpp"
SAMPLE = TROY_MODE / "samples" / "cpp"
SAMPLE_WORKFLOW = WORKFLOWS / "troy-cpp-sample.yml"


def text(name: str) -> str:
    """Reads a pack file."""
    return (PACK / name).read_text(encoding="utf-8")


def settings(name: str) -> dict[str, str]:
    """Reads "KEY = value" lines of a Doxyfile-style file."""
    return {m.group(1): m.group(2).strip()
            for line in text(name).splitlines() if (m := re.match(r"^(\w+)\s*=\s*(.*)$", line))}


class PackFileTests(unittest.TestCase):
    """The pack's files hold what F03 design section 9 says."""

    def test_pack_has_the_files_of_design_section_2(self) -> None:
        """The pack holds the design's files plus the tool requirements."""
        names = {p.relative_to(PACK).as_posix() for p in PACK.rglob("*") if p.is_file()}
        self.assertEqual({"README.md", "README.zh-CN.md", "environment.yml", "CMakePresets.json",
                          "cmake/troy.cmake", "Doxyfile", ".clang-format", ".clang-tidy",
                          "config.toml", "workflow-job.yml", "include/troy/not_implemented.h",
                          "requirements-tools.in"}, names)

    def test_environment_has_the_build_tools_but_no_compiler_or_googletest(self) -> None:
        """mamba installs the tools of 9.2; GoogleTest comes from CMake (D25)."""
        lines = [line.strip() for line in text("environment.yml").splitlines()
                 if line.strip() and not line.startswith("#")]
        self.assertEqual(['name: "{{environment}}"', "channels:", "- conda-forge", "dependencies:",
                          "- python=3.13", "- uv", "- cmake", "- ninja", "- doxygen",
                          "- clang-format=23", "- clang-tools=23"], lines)

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
        self.assertEqual(7, len(pack))
        self.assertEqual(pack, sample)
        self.assertEqual(uses(PACK / "workflow-job.yml"), uses(SAMPLE_WORKFLOW))


class SampleTests(unittest.TestCase):
    """The C++ sample's lock and its built repository."""

    def test_lock_pins_the_tools(self) -> None:
        """The sample's lock pins gcovr and lizard."""
        lock = (SAMPLE / "base" / "requirements-tools.lock").read_text(encoding="utf-8")
        self.assertIn("uv pip compile requirements-tools.in --universal", lock)
        for tool in ("gcovr", "lizard"):
            self.assertRegex(lock, rf"(?m)^{tool}==\d")

    def test_build_installs_the_pack_like_troy_init(self) -> None:
        """The first commit holds troy-check and every pack file at its place."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            proc = run_build("build", "cpp", "--pr", "impl", "--out", str(repo))
            self.assertEqual(0, proc.returncode, proc.stderr)
            files = git(repo, "ls-tree", "-r", "--name-only", "main~4").splitlines()
            environment = (repo / "environment.yml").read_text(encoding="utf-8")
        for path in (".troy-mode/checks/troy_check.py", ".troy-mode/config.toml",
                     ".troy-mode/lang/cpp/Doxyfile", "CMakePresets.json", "cmake/troy.cmake",
                     ".clang-format", ".clang-tidy", "include/troy/not_implemented.h",
                     "requirements-tools.in", "requirements-tools.lock",
                     ".github/workflows/troy-mode.yml"):
            self.assertIn(path, files)
        self.assertIn('name: "textstats-cpp"', environment)
        self.assertEqual("[F01 5/6 impl] Count words in a text", json.loads(proc.stdout)["PR_TITLE"])


if __name__ == "__main__":
    unittest.main()
