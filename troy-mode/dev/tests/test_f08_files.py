"""Text tests of the files F08 changes besides the engine (F08 design 9; interface note 13).

- The "Run by" columns of the ``version-test-plan`` template, in both languages.
- The templates README's PR kinds row for ``[v0.1 tests]``, in both languages.
- ``troy_add_version_test``, ``TROY_VERSION_TESTS``, and the ``version`` label in the
  C/C++ pack's ``cmake/troy.cmake``.
- The release command in both packs' READMEs and their mirrors.
- TE5, TM7's "Run by", and TM2's ``[vX.Y tests]`` PR in the agent files.

Run from the repository root:
python -m unittest discover -s troy-mode/dev/tests -v
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "troy-mode" / "templates"
LANG = REPO / "troy-mode" / "lang"
AGENTS = REPO / "agents"
TESTS_TITLE = "[v0.1 tests] End-to-end and stress tests"


def read(path: Path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def section(text: str, heading: str, level: int = 2) -> str:
    """The text under a heading, up to the next heading of the same or a higher level.

    Args:
        text: The document.
        heading: The heading's exact title, without the ``#`` signs.
        level: The heading's level.

    Returns:
        The section's lines after the heading, or "" when there is no such heading.
    """
    lines = text.split("\n")
    marker = "#" * level + " " + heading
    start = next((i for i, line in enumerate(lines) if line.strip() == marker), None)
    if start is None:
        return ""
    found = []
    for line in lines[start + 1:]:
        match = re.match(r"^(#{1,6}) ", line)
        if match and len(match.group(1)) <= level:
            break
        found.append(line)
    return "\n".join(found)


def table_rows(text: str) -> list:
    """The cells of every Markdown table row in a text, separator rows left out."""
    rows = []
    for line in text.split("\n"):
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                rows.append(cells)
    return rows


def row_after(text: str, header: str) -> Optional[list]:
    """The cells of the first data row after a header line, or None."""
    lines = text.split("\n")
    if header not in lines:
        return None
    index = lines.index(header)
    if index + 2 >= len(lines):
        return None
    return [cell.strip() for cell in lines[index + 2].strip().strip("|").split("|")]


class VersionTestPlanTemplateTests(unittest.TestCase):
    """The scenarios and the performance tables say who runs each one (D71)."""

    CASES = {
        "version-test-plan.md": ("| ID | Scenario | Run by | Steps | Expected result |",
                                 "| ID | Target | Load | Duration | Machine | Run by |"),
        "version-test-plan.zh-CN.md": ("| 编号 | 场景 | 由谁运行 | 步骤 | 预期结果 |",
                                       "| 编号 | 指标 | 负载 | 持续时间 | 机器 | 由谁运行 |"),
    }

    def test_tables_have_the_run_by_column(self):
        """Each header is in its template, and the template row under it has as many cells."""
        for name, headers in self.CASES.items():
            text = read(TEMPLATES / name)
            for header in headers:
                with self.subTest(template=name, header=header):
                    self.assertIn(header, text.split("\n"))
                    row = row_after(text, header)
                    self.assertIsNotNone(row, text)
                    self.assertEqual(len(row), header.count("|") - 1, row)


class TemplatesReadmeTests(unittest.TestCase):
    """The PR kinds table lists the version tests PR (F08 design 9, F01)."""

    def test_pr_kinds_have_the_version_tests_row(self):
        """``[v0.1 tests] End-to-end and stress tests`` is a title example, in both languages."""
        for name, heading in (("README.md", "6. PR kinds"), ("README.zh-CN.md", "6. PR 类型")):
            with self.subTest(readme=name):
                rows = table_rows(section(read(TEMPLATES / name), heading))
                self.assertTrue(rows, f"{name}: no PR kinds table")
                titles = [row[1].strip("`") for row in rows if len(row) >= 3]
                self.assertIn(TESTS_TITLE, titles)


class CmakeVersionTestTests(unittest.TestCase):
    """``cmake/troy.cmake`` builds version tests only on request (F08 design 5.3, 9)."""

    @classmethod
    def setUpClass(cls):
        """Reads troy.cmake once."""
        cls.text = read(LANG / "cpp" / "cmake" / "troy.cmake")

    def test_defines_troy_add_version_test(self):
        """A ``function(troy_add_version_test ...)`` beside ``troy_add_test``."""
        self.assertRegex(self.text, r"(?m)^\s*function\(\s*troy_add_version_test\b")
        self.assertRegex(self.text, r"(?m)^\s*function\(\s*troy_add_test\b")

    def test_reads_troy_version_tests(self):
        """The switch is ``TROY_VERSION_TESTS``, and the tests get the label ``version``."""
        code = "\n".join(line for line in self.text.split("\n")
                         if not line.lstrip().startswith("#"))
        self.assertIn("TROY_VERSION_TESTS", code)
        self.assertRegex(code, r'\bLABELS\s+"?version"?(?=[\s)])')

    def test_switch_holds_for_one_configure_run(self):
        """A ``-D`` value stays in CMake's cache unless the file removes or resets it."""
        self.assertRegex(self.text, r"unset\(\s*TROY_VERSION_TESTS\s+CACHE\s*\)"
                                    r"|set\(\s*TROY_VERSION_TESTS\b[^)]*\bCACHE\b[^)]*\bFORCE\b")


# A CMake project that includes the pack's troy.cmake with a local stand-in for
# GoogleTest, and records which targets troy_add_test and troy_add_version_test
# create. It enables no language, so no compiler is needed.
_PROBE = """cmake_minimum_required(VERSION 3.28)
project(probe NONE)
include("@TROY@")
function(add_executable name)
  message(STATUS "PROBE executable ${name}")
endfunction()
function(target_link_libraries)
endfunction()
function(gtest_discover_tests name)
  list(JOIN ARGN " " args)
  message(STATUS "PROBE discover ${name} ${args}")
endfunction()
troy_add_test(unit_tests u.cpp)
troy_add_version_test(version_tests v.cpp)
"""
_FAKE_GTEST = "add_library(gtest_main INTERFACE)\nadd_library(GTest::gtest_main ALIAS gtest_main)\n"


@unittest.skipUnless(shutil.which("cmake"), "cmake is not on the PATH")
class CmakeVersionTestConfigureTests(unittest.TestCase):
    """Configure runs: version tests only in the run that sets TROY_VERSION_TESTS=ON."""

    @classmethod
    def setUpClass(cls):
        """Writes the probe project and configures it three times: ON, plain, ON again."""
        cls._tmp = tempfile.TemporaryDirectory(prefix="troycmake-", ignore_cleanup_errors=True)
        root = Path(cls._tmp.name)
        (root / "src").mkdir()
        (root / "gtest").mkdir()
        troy = (LANG / "cpp" / "cmake" / "troy.cmake").as_posix()
        (root / "src" / "CMakeLists.txt").write_text(_PROBE.replace("@TROY@", troy),
                                                     encoding="utf-8")
        (root / "gtest" / "CMakeLists.txt").write_text(_FAKE_GTEST, encoding="utf-8")
        base = ["cmake", "-S", str(root / "src"), "-B", str(root / "build"),
                f"-DFETCHCONTENT_SOURCE_DIR_GOOGLETEST={(root / 'gtest').as_posix()}",
                "-DFETCHCONTENT_FULLY_DISCONNECTED=ON"]
        if shutil.which("ninja"):
            base += ["-G", "Ninja"]
        cls.runs = [subprocess.run(base + extra, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                    for extra in (["-DTROY_VERSION_TESTS=ON"], [], ["-DTROY_VERSION_TESTS=ON"])]

    @classmethod
    def tearDownClass(cls):
        """Removes the probe project."""
        cls._tmp.cleanup()

    def probe(self, index: int) -> list:
        """The PROBE lines of one configure run, after checking that it worked."""
        run = self.runs[index]
        self.assertEqual(run.returncode, 0, run.stdout[-2000:] + run.stderr[-2000:])
        return [line.split("PROBE ", 1)[1].strip() for line in run.stdout.splitlines()
                if "PROBE " in line]

    def test_on_builds_version_tests_with_the_label(self):
        """With TROY_VERSION_TESTS=ON both executables exist; only version tests get the label."""
        self.assertEqual(self.probe(0), ["executable unit_tests", "discover unit_tests",
                                         "executable version_tests",
                                         "discover version_tests PROPERTIES LABELS version"])

    def test_next_configure_without_the_switch_builds_none(self):
        """The next configure run without -D builds no version test (the switch is not kept)."""
        self.assertEqual(self.probe(1), ["executable unit_tests", "discover unit_tests"])

    def test_switch_works_again(self):
        """Setting the switch again builds them again."""
        self.assertIn("executable version_tests", self.probe(2))


class PackReadmeTests(unittest.TestCase):
    """Both packs' READMEs and mirrors give the release command (F08 design 5.5, 9)."""

    def test_python_release_command(self):
        """``pytest version-tests --junitxml=reports/version-junit.xml``."""
        for name in ("README.md", "README.zh-CN.md"):
            with self.subTest(readme=name):
                self.assertIn("pytest version-tests --junitxml=reports/version-junit.xml",
                              read(LANG / "python" / name))

    def test_cpp_release_command(self):
        """A build with ``TROY_VERSION_TESTS=ON``, then ``ctest -L version`` into its report."""
        for name in ("README.md", "README.zh-CN.md"):
            text = read(LANG / "cpp" / name)
            for part in ("TROY_VERSION_TESTS=ON", "-L version", "reports/version-junit.xml"):
                with self.subTest(readme=name, part=part):
                    self.assertIn(part, text)


class AgentTextTests(unittest.TestCase):
    """TE5, TM7, and TM2 as F08 changes them (interface note 13)."""

    def task(self, agent: str, heading: str) -> str:
        """The text of one task subsection of an agent file."""
        text = section(read(AGENTS / agent), heading, 3)
        self.assertNotEqual(text.strip(), "", f"{agent}: no '### {heading}'")
        return text

    def test_te5_writes_in_version_tests(self):
        """TE5 names the ``version-tests/`` folder."""
        self.assertIn("version-tests/", self.task("troy-test-engineer.md", "TE5 Version tests"))

    def test_tm7_says_who_runs_each_scenario(self):
        """TM7 names the Run by column."""
        self.assertIn("Run by", self.task("troy-test-manager.md", "TM7 Version test plan"))

    def test_tm2_reviews_version_tests_prs(self):
        """TM2's When line names a ``[vX.Y tests]`` PR."""
        text = self.task("troy-test-manager.md", "TM2 Test review")
        when = [line for line in text.split("\n") if line.startswith("When:")]
        self.assertEqual(len(when), 1, text)
        self.assertRegex(when[0], r"\[v[^\]\s]+ tests\]")


if __name__ == "__main__":
    unittest.main()
