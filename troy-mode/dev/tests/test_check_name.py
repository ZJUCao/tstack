"""Tests for check_name.py, the check that living text no longer names the old plugin.

F19 design 11.2: check_name.py reads every file ``git ls-files`` lists that is
UTF-8 text, and prints ``<path>:<line number>: <the line, stripped>`` for each
line that names the plugin's name before tstack, in any spelling and case.
It skips a line when the file is one of its history files (``HISTORY``), when
the line lies in a Markdown change-log section or is the Status row of a
Markdown file's header table, when the line also names tstack, or when the
old name appears only in GitHub issue or PR links. Exit code 0 means nothing
was found, 1 that a line was, and 2 that the script could not run.

Each test builds a small git repository, adds files to the index, and runs
the script as a subprocess, as test_check_pairs.py does. HISTORY is read by
loading the script as a module. The fixtures build the old name from pieces,
so no line of this file names it.

F19 planted bugs (design 11.3) caught here: the name check missing a
capitalized old name (SpellingTests.test_every_spelling_and_case_is_found) or
a Chinese mirror
(MarkdownTests.test_chinese_mirror_living_text_is_found_and_its_change_log_skipped);
a stray old command in a guide page (RunTests.test_the_repository_passes).
"""

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_name.py"
REPO = Path(__file__).resolve().parents[3]
OLD = "troy" + "-pstack"  # the plugin's name before tstack; fixtures build lines from it
OWNER_URL = "https://github.com/ZJUCao/"
FINDING = re.compile(r"^(.+?):(\d+): (.*)$")
_DROPPED_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CEILING_DIRECTORIES",
                "PYTHONIOENCODING", "PYTHONUTF8")
_MODULE: dict = {}


def md(*lines: str) -> str:
    """Joins lines into a text, so line N is the Nth argument."""
    return "\n".join(lines) + "\n"


def _env(extra: dict | None = None) -> dict:
    """Builds an environment that isolates git from the user's settings."""
    env = {k: v for k, v in os.environ.items() if k not in _DROPPED_ENV}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    env.update(extra or {})
    return env


def run_script(*args: str, cwd: Path | None = None,
               env: dict | None = None) -> subprocess.CompletedProcess:
    """Runs check_name.py with the arguments."""
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env or _env(),
                          cwd=str(cwd) if cwd else None, check=False)


def findings(out: subprocess.CompletedProcess) -> list:
    """The finding lines of a run's stdout, as (path, line number, text)."""
    found = []
    for line in out.stdout.splitlines():
        match = FINDING.match(line)
        if match:
            found.append((match.group(1), int(match.group(2)), match.group(3)))
    return found


def history() -> tuple:
    """check_name.HISTORY, loading the script as a module once."""
    if "module" not in _MODULE:
        spec = importlib.util.spec_from_file_location("check_name_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MODULE["module"] = module
    return _MODULE["module"].HISTORY


def tracked_files() -> set:
    """The paths git ls-files lists in the real repository."""
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"], capture_output=True,
                         check=True, env=_env())
    return set(out.stdout.decode("utf-8").split("\0")) - {""}


class NameRepo:
    """A temporary git repository whose files are in the index."""

    def __init__(self, files: dict) -> None:
        """Creates the repository and adds the files to the index.

        Args:
            files: Repository paths mapped to text, or to bytes written as they are.
        """
        self._tmp = tempfile.TemporaryDirectory(prefix="names-")
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        empty = Path(self._tmp.name) / "empty-gitconfig"
        empty.write_text("", encoding="utf-8")
        self.env = _env({"GIT_CONFIG_GLOBAL": str(empty)})
        self.git("init", "-q", "-b", "main")
        for rel, content in files.items():
            self.write(rel, content)
        self.git("add", "-A")

    def write(self, rel: str, content) -> None:
        """Writes a file in the working tree, text as UTF-8 with LF endings."""
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def git(self, *args: str) -> None:
        """Runs git inside the repository."""
        subprocess.run(["git", "-C", str(self.root), *args], check=True, env=self.env,
                       capture_output=True)

    def check(self) -> subprocess.CompletedProcess:
        """Runs check_name.py on the repository."""
        return run_script("--repo", str(self.root), env=self.env)

    def close(self) -> None:
        """Deletes the temporary folder."""
        self._tmp.cleanup()


class NameCase(unittest.TestCase):
    """Runs the check on small repositories."""

    def run_names(self, files: dict) -> subprocess.CompletedProcess:
        """Builds a repository with the files and checks it."""
        repo = NameRepo(files)
        self.addCleanup(repo.close)
        return repo.check()

    def assert_clean(self, files: dict) -> None:
        """Asserts exit code 0 and no finding."""
        out = self.run_names(files)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(findings(out), [], out.stdout)

    def assert_found(self, files: dict, expected: list) -> None:
        """Asserts exit code 1 and exactly the expected findings, in any order."""
        out = self.run_names(files)
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
        self.assertEqual(sorted(findings(out)), sorted(expected), out.stdout)


class OutputTests(NameCase):
    """What a finding looks like, and the exit codes 0 and 1."""

    def test_clean_repository_passes(self):
        """Files that never name the old plugin pass with no finding."""
        self.assert_clean({"README.md": md("# Sample", "", "Install tstack."),
                           "src/app.py": md("NAME = 'tstack'")})

    def test_a_finding_names_the_path_the_line_and_the_stripped_text(self):
        """A finding is <path>:<line>: <text> with the path from the repository root."""
        text = md("# Guide", "", "Text.", f"   Install {OLD} first.   ")
        self.assert_found({"docs/guide/a.md": text},
                          [("docs/guide/a.md", 4, f"Install {OLD} first.")])

    def test_a_line_with_two_mentions_is_one_finding(self):
        """Each line is reported once, however often it names the old plugin."""
        self.assert_found({"notes.txt": md(f"{OLD} and {OLD}")},
                          [("notes.txt", 1, f"{OLD} and {OLD}")])

    def test_findings_in_several_files(self):
        """Every file with a finding is reported."""
        self.assert_found({"a.txt": md("ok", f"a {OLD}"), "b/c.txt": md(f"c {OLD}")},
                          [("a.txt", 2, f"a {OLD}"), ("b/c.txt", 1, f"c {OLD}")])


class SpellingTests(NameCase):
    """troy[-_ ]?pstack in any case (design 11.2)."""

    def test_every_spelling_and_case_is_found(self):
        """A hyphen, an underscore, a space, or nothing between the two parts, in any case.

        F19 planted bug caught: the name check missing a capitalized name.
        """
        spellings = (OLD, "Troy" + "-pstack", "TROY" + "-PSTACK", "troy" + "_pstack",
                     "troy" + " pstack", "Troy" + "Pstack")
        lines = []
        for spelling in spellings:
            lines += [f"Uses {spelling} here.", "clean"]
        self.assert_found({"notes.txt": md(*lines)},
                          [("notes.txt", 2 * i + 1, f"Uses {s} here.")
                           for i, s in enumerate(spellings)])

    def test_other_names_are_not_found(self):
        """pstack, troy-mode, troy-stack, a doubled separator, and tstack are not the old name."""
        self.assert_clean({"notes.txt": md("pstack", "troy-mode", "troy-stack",
                                           "troy" + "--pstack", "tstack", "poteto-mode")})


class FileTests(NameCase):
    """Which files are read (design 11.2)."""

    def test_non_markdown_files_are_read_and_have_no_headings(self):
        """In a .py or .toml file a "# Change log" comment is no heading, so later lines count."""
        files = {"tool.py": md(f"# {OLD} hooks", f'NAME = "{OLD}"'),
                 "config.toml": md("# Change log", f"# {OLD} 0.5.0"),
                 "table.txt": md(f"| Status | {OLD} |")}
        self.assert_found(files, [("tool.py", 1, f"# {OLD} hooks"),
                                  ("tool.py", 2, f'NAME = "{OLD}"'),
                                  ("config.toml", 2, f"# {OLD} 0.5.0"),
                                  ("table.txt", 1, f"| Status | {OLD} |")])

    def test_untracked_files_are_not_read(self):
        """A file git ls-files does not list is not checked."""
        repo = NameRepo({"README.md": md("# Clean")})
        self.addCleanup(repo.close)
        repo.write("new.md", md(f"Uses {OLD}."))
        out = repo.check()
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(findings(out), [])

    def test_files_with_a_nul_byte_or_not_utf8_are_skipped(self):
        """A file with a NUL byte or bytes that are not UTF-8 is skipped; plain text is read."""
        name = OLD.encode("utf-8")
        files = {"data.bin": b"head\x00\n" + name + b"\n",
                 "latin.txt": b"caf\xe9 " + name + b"\n",
                 "plain.txt": md(f"Uses {OLD}.")}
        self.assert_found(files, [("plain.txt", 1, f"Uses {OLD}.")])

    def test_history_files_are_skipped_and_other_designs_are_read(self):
        """Approved designs and the pilot report keep the old name; a later design does not."""
        text = md("# Design", "", f"The trial saw {OLD}:poteto-mode.")
        kept = ("docs/troy-mode/design/F13-mode-guard.md",
                "docs/troy-mode/design/F13-mode-guard.zh-CN.md",
                "docs/troy-mode/design/F19-rename.md",
                "docs/troy-mode/pilot/recipe-menu-v0.1.md")
        files = {path: text for path in kept}
        files["docs/troy-mode/design/F20-later.md"] = text
        self.assert_found(files, [("docs/troy-mode/design/F20-later.md", 3,
                                   f"The trial saw {OLD}:poteto-mode.")])


class MarkdownTests(NameCase):
    """Change-log sections and the header table's Status row (design 11.2, rules 2 and 3)."""

    def test_change_log_section_is_skipped(self):
        """Rows under "## 2. Change log" are skipped; a line in a living section is found."""
        text = md("# Doc", "", "## 1. Goal", "", f"Uses {OLD}.", "", "## 2. Change log", "",
                  "| Version | Date | Change |", "| --- | --- | --- |",
                  f"| 1.0 | 2026-11-01 | Named {OLD}. |")
        self.assert_found({"d/x.md": text}, [("d/x.md", 5, f"Uses {OLD}.")])

    def test_change_log_heading_without_a_number_counts(self):
        """A heading "## Change log" with no section number opens a change-log section too."""
        self.assert_clean({"d/x.md": md("# Doc", "", "## Change log", "", f"| 1.0 | {OLD} |")})

    def test_chinese_mirror_living_text_is_found_and_its_change_log_skipped(self):
        """In x.zh-CN.md a living line is found and the rows under "## 2. 修改记录" are skipped.

        F19 planted bug caught: the name check missing a Chinese mirror.
        """
        text = md("# 文档", "", "## 1. 目标", "", f"使用 {OLD}。", "", "## 2. 修改记录", "",
                  f"| 1.0 | 2026-11-01 | 命名为 {OLD}。 |")
        self.assert_found({"d/x.md": md("# Doc"), "d/x.zh-CN.md": text},
                          [("d/x.zh-CN.md", 5, f"使用 {OLD}。")])

    def test_change_log_ends_at_the_next_heading_of_the_same_or_a_higher_level(self):
        """A lower heading stays in the change log; the same level or a higher one ends it."""
        same = md("# Doc", "", "## 3. Change log", "", f"| 1.0 | {OLD} |", "",
                  "### 3.1 Older", "", f"Old {OLD} entry.", "", "## 4. After", "",
                  f"After {OLD}.")
        higher = md("## Part", "", "### Change log", "", f"Log {OLD}.", "", "## Next", "",
                    f"Next {OLD}.")
        self.assert_found({"d/same.md": same, "d/higher.md": higher},
                          [("d/same.md", 13, f"After {OLD}."), ("d/higher.md", 9, f"Next {OLD}.")])

    def test_only_a_heading_that_is_exactly_change_log_counts(self):
        """Headings that only contain the words, or say something else, open no change log."""
        text = md("# Doc", "", "## 2. Change log notes", "", f"a {OLD}", "", "## 3. Changes", "",
                  f"b {OLD}", "", "## 4. 在修改记录里记录批准", "", f"c {OLD}")
        self.assert_found({"d/x.md": text}, [("d/x.md", 5, f"a {OLD}"), ("d/x.md", 9, f"b {OLD}"),
                                             ("d/x.md", 13, f"c {OLD}")])

    def test_a_heading_inside_a_code_fence_is_not_a_heading(self):
        """A fenced "## Change log" opens nothing, and a fenced "## Next" ends nothing.

        Lines inside a fence in a living section are still read.
        """
        opens = md("# Doc", "", "```text", "## Change log", f"run {OLD}", "```", "",
                   f"After {OLD}.")
        ends = md("## 5. Change log", "", "```text", "## Next", "```", "",
                  f"Still the log {OLD}.")
        self.assert_found({"d/opens.md": opens, "d/ends.md": ends},
                          [("d/opens.md", 5, f"run {OLD}"), ("d/opens.md", 8, f"After {OLD}.")])

    def test_status_row_of_the_header_table_is_skipped(self):
        """The first table's | Status | or | 状态 | row is skipped; the same row later is found."""
        en = md("# F20 design", "", "| | |", "| --- | --- |", "| Version | 1.0 |",
                f"| Status | Approved; {OLD} was the plugin. |", "", "## 1. Notes", "",
                "| Field | Value |", "| --- | --- |", f"| Status | {OLD} in a later table |")
        zh = md("# F20 设计", "", "| | |", "| --- | --- |", "| 版本 | 1.0 |",
                f"| 状态 | 已批准；当时插件叫 {OLD}。 |", "", "## 1. 说明", "",
                "| 字段 | 值 |", "| --- | --- |", f"| 状态 | 后面的表里的 {OLD} |")
        self.assert_found({"d/f20.md": en, "d/f20.zh-CN.md": zh},
                          [("d/f20.md", 12, f"| Status | {OLD} in a later table |"),
                           ("d/f20.zh-CN.md", 12, f"| 状态 | 后面的表里的 {OLD} |")])


class LineTests(NameCase):
    """Lines about the rename, and links (design 11.2 rule 4, D197)."""

    def test_a_line_that_also_names_tstack_is_skipped(self):
        """A line that names tstack as a word, in any case, talks about the rename."""
        lines = (f"Renamed from {OLD} to tstack.", f"TStack was called {OLD} until 0.5.0.",
                 f"`{OLD}:troy-developer` is now `tstack:troy-developer`.")
        self.assert_clean({"README.md": md(*lines)})

    def test_tstack_inside_another_word_does_not_count(self):
        """xtstack is not the word tstack, so the line is found."""
        self.assert_found({"notes.txt": md(f"xtstack and {OLD}")},
                          [("notes.txt", 1, f"xtstack and {OLD}")])

    def test_issue_and_pr_links_are_skipped(self):
        """The old name only inside issue and PR links is not a finding."""
        repo = f"{OWNER_URL}{OLD}"
        self.assert_clean({"docs/log.md": md(f"See [#57]({repo}/pull/57).", "",
                                             f"Fixed in {repo}/issues/12 and {repo}/pull/3.")})

    def test_other_links_and_bare_mentions_beside_a_link_are_found(self):
        """A link and a bare mention, a file link, a clone URL, and the PR list are found."""
        repo = f"{OWNER_URL}{OLD}"
        lines = (f"See {repo}/issues/12 for the {OLD} plan.", f"Code at {repo}/blob/main/x.md.",
                 f"Clone {repo}.git now.", f"All PRs: {repo}/pulls")
        self.assert_found({"notes.txt": md(*lines)},
                          [("notes.txt", i + 1, line) for i, line in enumerate(lines)])


class RunTests(unittest.TestCase):
    """The real repository, the default repository, and exit code 2."""

    def test_the_repository_passes(self):
        """tstack's own repository names the old plugin only where design 11.2 allows: exit 0.

        F19 planted bug caught: a stray old command in a guide page.
        """
        out = run_script("--repo", str(REPO))
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(findings(out), [], out.stdout)

    def test_default_repository_is_the_one_holding_the_script(self):
        """Without --repo the script checks its own repository, not the current folder's."""
        repo = NameRepo({"planted-name.txt": md(f"Uses {OLD}.")})
        self.addCleanup(repo.close)
        self.assertEqual(repo.check().returncode, 1, "the premise: the planted file is found")
        out = run_script(cwd=repo.root, env=repo.env)
        self.assertNotEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertNotIn("planted-name.txt", out.stdout)

    def test_not_a_repository_exits_two(self):
        """A folder outside git cannot be checked, while a clean repository exits 0.

        The pair keeps the test from passing when the script is missing, since
        Python also exits 2 when it cannot open a script.
        """
        repo = NameRepo({"README.md": md("# Clean")})
        self.addCleanup(repo.close)
        clean = repo.check()
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            out = run_script("--repo", tmp,
                             env=_env({"GIT_CEILING_DIRECTORIES": str(Path(tmp).parent)}))
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)


class HistoryTests(unittest.TestCase):
    """check_name.HISTORY, the files that keep the old name (design 9 and 11.2, D197)."""

    def test_history_is_a_tuple_of_tracked_paths_with_slashes(self):
        """Each entry is a repository path with "/" that git ls-files lists."""
        paths = history()
        self.assertIsInstance(paths, tuple)
        tracked = tracked_files()
        for path in paths:
            with self.subTest(path=path):
                self.assertIsInstance(path, str)
                self.assertNotIn("\\", path)
                self.assertIn(path, tracked)

    def test_history_holds_the_approved_designs_and_the_pilot_report(self):
        """F01 to F16 and F19's design in both languages, and the pilot report and its mirror."""
        design = re.compile(r"^docs/troy-mode/design/(F(0[1-9]|1[0-6])-[^/]+|F19-rename)"
                            r"(\.zh-CN)?\.md$")
        expected = {path for path in tracked_files() if design.match(path)}
        expected |= {"docs/troy-mode/pilot/recipe-menu-v0.1.md",
                     "docs/troy-mode/pilot/recipe-menu-v0.1.zh-CN.md"}
        self.assertEqual(len([p for p in expected if "/design/" in p]), 34, sorted(expected))
        self.assertEqual(sorted(expected - set(history())), [])

    def test_history_holds_no_living_document(self):
        """Every entry is an approved design or a pilot record, never living text (D197)."""
        for path in history():
            with self.subTest(path=path):
                self.assertTrue(path.startswith(("docs/troy-mode/design/F",
                                                 "docs/troy-mode/pilot/")), path)


if __name__ == "__main__":
    unittest.main()
