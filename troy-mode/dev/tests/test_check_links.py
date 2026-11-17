"""Tests for check_links.py, the link check for tstack's troy-mode documents.

Each test builds a small git repository, adds Markdown files to the index,
and runs the script as a subprocess. Exit code 0 means every link resolves,
1 means at least one link is broken, and 2 means the script could not run.
A broken link is printed as `<file>:<line>: <message>`, and the last line of
stdout is `<n> files checked, <m> broken links.`
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_links.py"

SUMMARY = re.compile(r"^(\d+) files? checked, (\d+) broken links?\.$")
BROKEN_LINE = re.compile(r"^([^:]+):(\d+): ")


def md(*lines: str) -> str:
    """Joins lines into Markdown text, so line N is the Nth argument."""
    return "\n".join(lines) + "\n"


B_MD = md("# B", "", "## Goal", "", "Text.")

C_MD = md(
    "# 中文",
    "",
    "## 7.2 功能列表",
    "",
    "## 说明：用法（简版）、注意，结束",
    "",
    "## 7.3 F10：文档",
)

R_MD = md("# R", "", "## Notes", "", "## Notes", "", "### Notes")

P_MD = md(
    "# F10 design: tstack's plug-in documentation",
    "",
    "## 7.2 Feature list",
    "",
    "## Q&A",
    "",
    "## a - b",
    "",
    "## What's new? (v2.0)",
    "",
    "## snake_case and kebab-case",
    "",
    "## Closing hashes ##",
    "",
    "   ## Indented heading",
)

H_MD = md(
    "# H",
    "",
    "## Shown",
    "",
    "```md",
    "## Hidden",
    "```",
    "",
    "~~~",
    "## Also hidden",
    "~~~",
)

A = "docs/troy-mode/a.md"


def _env() -> dict:
    """Builds an environment that isolates git from the user's settings."""
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


class LinkRepo:
    """A temporary git repository holding Markdown files."""

    def __init__(self, files: dict, untracked: dict | None = None) -> None:
        """Creates the repository, adds the files to the index, then writes the untracked ones.

        Args:
            files: Repository paths mapped to their text (or bytes); added to the index.
            untracked: Repository paths mapped to their text; written to disk only.
        """
        self._tmp = tempfile.TemporaryDirectory(prefix="links-")
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        empty = self.root / "empty-gitconfig"
        empty.write_text("", encoding="utf-8")
        self.env = {**_env(), "GIT_CONFIG_GLOBAL": str(empty)}
        self.git("init", "-q", "-b", "main")
        self.git("config", "core.autocrlf", "false")
        self._write(files)
        self.git("add", "-A")
        self._write(untracked or {})

    def _write(self, files: dict) -> None:
        """Writes files under the repository folder with LF line endings."""
        for rel, text in files.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(text, bytes):
                path.write_bytes(text)
            else:
                path.write_text(text, encoding="utf-8", newline="\n")

    def git(self, *args: str) -> None:
        """Runs git inside the repository folder."""
        subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                       env=self.env, capture_output=True)

    def check(self) -> subprocess.CompletedProcess:
        """Runs check_links.py on the repository."""
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo)],
                              capture_output=True, text=True, encoding="utf-8", env=self.env)

    def check_from_inside(self) -> subprocess.CompletedProcess:
        """Runs check_links.py without --repo, from the repository folder."""
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=str(self.repo),
                              capture_output=True, text=True, encoding="utf-8", env=self.env)

    def close(self) -> None:
        """Deletes the temporary folder."""
        self._tmp.cleanup()


class LinkTestCase(unittest.TestCase):
    """Shared helpers for running check_links.py and reading its output."""

    def setUp(self):
        """A missing script is a failure, never a skip."""
        self.assertTrue(SCRIPT.is_file(), f"script not found: {SCRIPT}")

    def make_repo(self, files: dict, untracked: dict | None = None) -> LinkRepo:
        """Builds a repository that is deleted after the test."""
        repo = LinkRepo(files, untracked)
        self.addCleanup(repo.close)
        return repo

    def run_links(self, files: dict, untracked: dict | None = None) -> subprocess.CompletedProcess:
        """Builds a repository with the files and checks it."""
        return self.make_repo(files, untracked).check()

    def split_output(self, out: subprocess.CompletedProcess) -> tuple[list, re.Match]:
        """Returns the broken-link lines and the parsed summary line."""
        lines = out.stdout.splitlines()
        while lines and not lines[-1].strip():
            lines.pop()
        self.assertTrue(lines, f"no summary line\nstdout:\n{out.stdout}\nstderr:\n{out.stderr}")
        summary = SUMMARY.match(lines[-1])
        self.assertIsNotNone(summary, f"last line is not the summary: {lines[-1]!r}\n{out.stderr}")
        for line in lines[:-1]:
            self.assertRegex(line, BROKEN_LINE, f"not a <file>:<line>: line\n{out.stdout}")
        return lines[:-1], summary

    def assert_clean(self, out: subprocess.CompletedProcess, files_checked: int) -> None:
        """Asserts exit code 0, no line but the summary, and the number of files read."""
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        broken, summary = self.split_output(out)
        self.assertEqual(broken, [], out.stdout)
        self.assertEqual(int(summary.group(1)), files_checked, out.stdout)
        self.assertEqual(int(summary.group(2)), 0, out.stdout)

    def assert_broken(self, out: subprocess.CompletedProcess, broken: list, ok: list) -> list:
        """Asserts exit code 1 and exactly the expected broken-link lines.

        Args:
            out: The script's result.
            broken: (file, line, target) for each link that must be reported.
            ok: (file, line) that must not be reported: valid control links next to
                the broken ones, and broken links that must be ignored.

        Returns:
            The broken-link lines, in output order.
        """
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
        lines, summary = self.split_output(out)
        reported = [(m.group(1), int(m.group(2))) for m in map(BROKEN_LINE.match, lines)]
        self.assertEqual(sorted(reported), sorted((f, n) for f, n, _ in broken), out.stdout)
        for file, number, target in broken:
            line = next(x for x in lines if x.startswith(f"{file}:{number}:"))
            self.assertIn(target, line)
        for file, number in ok:
            self.assertFalse([x for x in lines if x.startswith(f"{file}:{number}:")],
                             f"valid link reported\n{out.stdout}")
        for file in {f for f, _ in reported}:
            numbers = [n for f, n in reported if f == file]
            self.assertEqual(numbers, sorted(numbers), f"lines out of order\n{out.stdout}")
        self.assertEqual(int(summary.group(2)), len(broken), out.stdout)
        return lines


class PathTests(LinkTestCase):
    """Links to files and folders must name what git tracks."""

    def test_link_to_tracked_file_passes(self):
        """Sibling, ./, sub/../, ?query, and ../../ links to tracked files resolve."""
        a = md("# A", "", "[b](b.md)", "[b2](./b.md)", "[c](sub/c.md)", "[c2](sub/../b.md)",
               "[q](b.md?plain=1)", "[r](../../README.md)")
        out = self.run_links({"README.md": md("# Readme"), A: a, "docs/troy-mode/b.md": B_MD,
                              "docs/troy-mode/sub/c.md": md("# C", "", "[back](../a.md)")})
        self.assert_clean(out, files_checked=4)

    def test_link_to_missing_file_fails(self):
        """A link to a file that does not exist is broken."""
        a = md("# A", "", "See [gone](gone.md) here.", "See [b](b.md) here.")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 3, "gone.md")], ok=[(A, 4)])

    def test_link_to_untracked_file_fails(self):
        """A file on disk that git does not track is broken."""
        a = md("# A", "", "[n](notes.md)", "[b](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD},
                             untracked={"docs/troy-mode/notes.md": md("# Notes")})
        self.assert_broken(out, [(A, 3, "notes.md")], ok=[(A, 4)])

    def test_link_to_tracked_folder_passes(self):
        """Folders holding tracked files resolve, with or without a trailing slash."""
        a = md("# A", "", "[s](sub)", "[s2](sub/)", "[d](deep)", "[d2](deep/x/)", "[up](../)")
        out = self.run_links({A: a, "docs/troy-mode/sub/c.txt": "c\n",
                              "docs/troy-mode/deep/x/y.md": md("# Y")})
        self.assert_clean(out, files_checked=2)

    def test_link_to_folder_without_tracked_file_fails(self):
        """A folder on disk that holds only untracked files is broken."""
        a = md("# A", "", "[e](empty)", "[e2](empty/)", "[s](sub/)")
        out = self.run_links({A: a, "docs/troy-mode/sub/c.txt": "c\n"},
                             untracked={"docs/troy-mode/empty/notes.txt": "n\n"})
        self.assert_broken(out, [(A, 3, "empty"), (A, 4, "empty/")], ok=[(A, 5)])

    def test_link_up_to_readme_section_passes(self):
        """A guide page reaches the README's section with ../../../README.md#section."""
        x = md("# X", "", "[r](../../../README.md#section)", "[r2](../../../README.md)")
        out = self.run_links({"README.md": md("# Readme", "", "## Section"),
                              "docs/troy-mode/guide/x.md": x})
        self.assert_clean(out, files_checked=2)

    def test_link_up_with_wrong_depth_fails(self):
        """One ../ too few names docs/README.md, which does not exist."""
        x = md("# X", "", "[r](../../README.md#section)", "[r2](../../../README.md#section)")
        out = self.run_links({"README.md": md("# Readme", "", "## Section"),
                              "docs/troy-mode/guide/x.md": x})
        self.assert_broken(out, [("docs/troy-mode/guide/x.md", 3, "../../README.md#section")],
                           ok=[("docs/troy-mode/guide/x.md", 4)])

    def test_link_leaving_repository_fails(self):
        """A path above the repository root is broken, even when the file exists there."""
        a = md("# A", "", "[o](../../../empty-gitconfig)", "[b](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 3, "../../../empty-gitconfig")], ok=[(A, 4)])

    def test_path_starting_with_slash_is_from_repository_root(self):
        """/README.md is at the root; /b.md does not mean the linking file's folder."""
        a = md("# A", "", "[r](/README.md)", "[d](/docs/troy-mode/b.md#goal)", "[x](/b.md)")
        out = self.run_links({"README.md": md("# Readme"), A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 5, "/b.md")], ok=[(A, 3), (A, 4)])

    def test_percent_encoded_path_and_anchor_pass(self):
        """%20 in a path and percent-encoded Chinese in an anchor are decoded."""
        a = md("# A", "", "[f](my%20file.md)",
               "[c](c.md#72-%E5%8A%9F%E8%83%BD%E5%88%97%E8%A1%A8)")
        out = self.run_links({A: a, "docs/troy-mode/my file.md": md("# My file"),
                              "docs/troy-mode/c.md": C_MD})
        self.assert_clean(out, files_checked=3)

    def test_path_case_must_match(self):
        """guide.md does not match a tracked Guide.md, nor Sub/ a tracked sub/."""
        a = md("# A", "", "[g](guide.md)", "[G](Guide.md)", "[s](Sub/)", "[s2](sub/)")
        out = self.run_links({A: a, "docs/troy-mode/Guide.md": md("# Guide"),
                              "docs/troy-mode/sub/c.txt": "c\n"})
        self.assert_broken(out, [(A, 3, "guide.md"), (A, 5, "Sub/")], ok=[(A, 4), (A, 6)])


class AnchorTests(LinkTestCase):
    """Anchors must match a heading slug of the target Markdown file."""

    def test_anchor_in_same_file_passes(self):
        """#title and #1-goal match the file's own headings."""
        a = md("# Title", "", "## 1. Goal", "", "Back to [top](#title) and [goal](#1-goal).")
        out = self.run_links({A: a})
        self.assert_clean(out, files_checked=1)

    def test_bad_anchor_in_same_file_fails(self):
        """#goal does not match the heading 1. Goal."""
        a = md("# Title", "", "## 1. Goal", "", "[bad](#goal)", "[ok](#1-goal)")
        out = self.run_links({A: a})
        self.assert_broken(out, [(A, 5, "#goal")], ok=[(A, 6)])

    def test_anchor_in_other_file_passes(self):
        """b.md#goal matches a heading in b.md."""
        a = md("# A", "", "[g](b.md#goal)", "[t](b.md#b)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_clean(out, files_checked=2)

    def test_bad_anchor_in_other_file_fails(self):
        """b.md#nope names no heading in b.md."""
        a = md("# A", "", "[n](b.md#nope)", "[g](b.md#goal)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 3, "b.md#nope")], ok=[(A, 4)])

    def test_chinese_heading_anchors_pass(self):
        """Chinese characters stay in the slug and Chinese punctuation is removed."""
        a = md("# A", "", "[t](c.md#中文)", "[l](c.md#72-功能列表)",
               "[s](c.md#说明用法简版注意结束)", "[f](c.md#73-f10文档)")
        out = self.run_links({A: a, "docs/troy-mode/c.md": C_MD})
        self.assert_clean(out, files_checked=2)

    def test_chinese_anchor_without_characters_or_with_punctuation_fails(self):
        """#72- lacks the Chinese words, and the full-width punctuation is not in the slug."""
        a = md("# A", "", "[l](c.md#72-)", "[s](c.md#说明：用法（简版）、注意，结束)",
               "[ok](c.md#72-功能列表)")
        out = self.run_links({A: a, "docs/troy-mode/c.md": C_MD})
        self.assert_broken(out, [(A, 3, "c.md#72-"), (A, 4, "c.md#说明：用法")], ok=[(A, 5)])

    def test_repeated_headings_are_numbered(self):
        """The second and third Notes headings are notes-1 and notes-2."""
        a = md("# A", "", "[n](r.md#notes)", "[n1](r.md#notes-1)", "[n2](r.md#notes-2)")
        out = self.run_links({A: a, "docs/troy-mode/r.md": R_MD})
        self.assert_clean(out, files_checked=2)

    def test_repeated_heading_past_last_fails(self):
        """There are three Notes headings, so notes-3 does not exist."""
        a = md("# A", "", "[n3](r.md#notes-3)", "[n2](r.md#notes-2)")
        out = self.run_links({A: a, "docs/troy-mode/r.md": R_MD})
        self.assert_broken(out, [(A, 3, "r.md#notes-3")], ok=[(A, 4)])

    def test_heading_punctuation_removed_passes(self):
        """Punctuation is removed, spaces become -, and closing hashes are dropped."""
        a = md("# A", "", "[1](p.md#f10-design-tstacks-plug-in-documentation)",
               "[2](p.md#72-feature-list)", "[3](p.md#qa)", "[4](p.md#a---b)",
               "[5](p.md#whats-new-v20)", "[6](p.md#snake_case-and-kebab-case)",
               "[7](p.md#closing-hashes)", "[8](p.md#indented-heading)")
        out = self.run_links({A: a, "docs/troy-mode/p.md": P_MD})
        self.assert_clean(out, files_checked=2)

    def test_heading_punctuation_in_anchor_fails(self):
        """An anchor that keeps the heading's punctuation is broken."""
        a = md("# A", "", "[x](p.md#7.2-feature-list)", "[y](p.md#q&a)",
               "[z](p.md#72-feature-list)")
        out = self.run_links({A: a, "docs/troy-mode/p.md": P_MD})
        self.assert_broken(out, [(A, 3, "p.md#7.2-feature-list"), (A, 4, "p.md#q&a")],
                           ok=[(A, 5)])

    def test_spaces_are_not_collapsed_in_slugs(self):
        """Each space becomes its own -, so two spaces give --."""
        p = md("# P", "", "## Two  spaces")
        a = md("# A", "", "[one](p.md#two-spaces)", "[two](p.md#two--spaces)")
        out = self.run_links({A: a, "docs/troy-mode/p.md": p})
        self.assert_broken(out, [(A, 3, "p.md#two-spaces")], ok=[(A, 4)])

    def test_heading_with_inline_code_passes(self):
        """Code spans in a heading keep their text without the backticks."""
        p = md("# P", "", "### 3.1 The `troy-init` skill", "", "## Run ``check_links.py`` now")
        a = md("# A", "", "[s](p.md#31-the-troy-init-skill)", "[r](p.md#run-check_linkspy-now)")
        out = self.run_links({A: a, "docs/troy-mode/p.md": p})
        self.assert_clean(out, files_checked=2)

    def test_heading_with_link_passes(self):
        """A link in a heading is replaced by its text."""
        p = md("# P", "", "## See [the guide](b.md)")
        a = md("# A", "", "[s](p.md#see-the-guide)")
        out = self.run_links({A: a, "docs/troy-mode/p.md": p, "docs/troy-mode/b.md": B_MD})
        self.assert_clean(out, files_checked=3)

    def test_heading_inside_code_block_makes_no_slug(self):
        """Heading lines inside backtick and tilde fences are not headings."""
        a = md("# A", "", "[h](h.md#hidden)", "[a](h.md#also-hidden)", "[s](h.md#shown)")
        out = self.run_links({A: a, "docs/troy-mode/h.md": H_MD})
        self.assert_broken(out, [(A, 3, "h.md#hidden"), (A, 4, "h.md#also-hidden")],
                           ok=[(A, 5)])

    def test_anchor_on_non_markdown_file_is_not_checked(self):
        """tool.py#L10 and sub#x need only the path; a missing gone.py is still broken."""
        a = md("# A", "", "[t](tool.py#L10)", "[s](sub#anything)", "[s2](sub/#anything)",
               "[g](gone.py#L10)")
        out = self.run_links({A: a, "docs/troy-mode/tool.py": "print('x')\n",
                              "docs/troy-mode/sub/c.txt": "c\n"})
        self.assert_broken(out, [(A, 6, "gone.py#L10")], ok=[(A, 3), (A, 4), (A, 5)])


class IgnoredTests(LinkTestCase):
    """Code, comments, and links with a scheme are never checked."""

    def test_links_in_backtick_fence_are_ignored(self):
        """A broken link inside a ``` fence is not reported; one after it is."""
        a = md("# A", "", "```text", "[a](gone1.md)", "```", "", "[b](gone2.md)", "[c](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 7, "gone2.md")], ok=[(A, 4), (A, 8)])

    def test_links_in_tilde_fence_are_ignored(self):
        """A broken link inside a ~~~ fence is not reported; one after it is."""
        a = md("# A", "", "~~~", "[a](gone1.md)", "~~~", "[b](gone2.md)", "[c](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 6, "gone2.md")], ok=[(A, 4), (A, 7)])

    def test_fence_closes_only_with_same_character_and_length(self):
        """``` does not close a ```` fence, and ``` does not close a ~~~ fence."""
        a = md("# A", "", "````md", "```", "[a](gone1.md)", "```", "[b](gone2.md)", "````",
               "~~~", "```", "[c](gone3.md)", "~~~", "[d](gone4.md)", "[e](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 13, "gone4.md")], ok=[(A, 5), (A, 7), (A, 11), (A, 14)])

    def test_links_in_indented_fence_are_ignored(self):
        """Fences indented by two or three spaces in a list are still fences."""
        a = md("# A", "", "- Step one:", "", "  ```bash", "  cat [a](gone1.md)", "  ```", "",
               "   ~~~", "   [b](gone2.md)", "   ~~~", "", "- [c](gone3.md)", "- [d](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 13, "gone3.md")], ok=[(A, 6), (A, 10), (A, 14)])

    def test_links_in_inline_code_are_ignored(self):
        """Single and double backtick spans hide links; a link beside a span is checked."""
        a = md("# A", "", "Write `[a](gone1.md)` or ``[b](gone2.md)`` in prose.",
               "Then `[c](gone3.md)` and [d](gone4.md) on one line.", "And [e](b.md).")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 4, "gone4.md")], ok=[(A, 3), (A, 5)])

    def test_links_in_html_comment_are_ignored(self):
        """One-line and multi-line HTML comments hide links; a link after them is checked."""
        a = md("# A", "", "<!-- [a](gone1.md) -->", "<!--", "[b](gone2.md)", "-->",
               "[c](gone3.md)", "[d](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 7, "gone3.md")], ok=[(A, 3), (A, 5), (A, 8)])

    def test_links_with_a_scheme_are_ignored(self):
        """https:, http: and mailto: targets are not checked; a relative one is."""
        a = md("# A", "", "[w](https://example.com/missing.md)", "[h](http://example.com/x)",
               "[m](mailto:someone@example.com)", "[r]: https://example.com/ref",
               "[gone](gone.md)", "[ok](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 7, "gone.md")], ok=[(A, 3), (A, 4), (A, 5), (A, 6), (A, 8)])


class LinkFormTests(LinkTestCase):
    """Every form of link is found and checked."""

    def test_reference_definitions_pass(self):
        """Definitions with good targets pass, and uses are not checked themselves."""
        a = md("# A", "", "See [the b file][b] and [goal][g] and [x][undefined].", "",
               "[b]: b.md", "   [g]: b.md#goal")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_clean(out, files_checked=2)

    def test_bad_reference_definition_fails(self):
        """A definition's bad target is reported at the definition's line."""
        a = md("# A", "", "See [one][gone] and [two][ok].", "", "[gone]: gone.md",
               "[ok]: b.md#goal", "[bad-anchor]: b.md#nope")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 5, "gone.md"), (A, 7, "b.md#nope")], ok=[(A, 3), (A, 6)])

    def test_image_target_is_checked(self):
        """An image's target must be tracked like a link's."""
        a = md("# A", "", "![logo](img/logo.png)", "![gone](img/gone.png)")
        out = self.run_links({A: a, "docs/troy-mode/img/logo.png": "png\n"})
        self.assert_broken(out, [(A, 4, "img/gone.png")], ok=[(A, 3)])

    def test_link_with_title_is_checked(self):
        """The title after the target is not part of the path."""
        a = md("# A", "", '[a](b.md "The B file")', '[c](gone.md "Gone file")',
               '[d](b.md#goal "Goal")')
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 4, "gone.md")], ok=[(A, 3), (A, 5)])

    def test_link_in_angle_brackets_is_checked(self):
        """A target in angle brackets may hold spaces."""
        a = md("# A", "", "[a](<my file.md>)", "[b](<gone file.md>)", "[c](<b.md#goal>)")
        out = self.run_links({A: a, "docs/troy-mode/my file.md": md("# My file"),
                              "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 4, "gone file.md")], ok=[(A, 3), (A, 5)])

    def test_four_space_indented_link_is_checked(self):
        """Four-space indented lines are text, as in nested list items."""
        a = md("# A", "", "- Item:", "", "    [g](gone.md)", "    [b](b.md)")
        out = self.run_links({A: a, "docs/troy-mode/b.md": B_MD})
        self.assert_broken(out, [(A, 5, "gone.md")], ok=[(A, 6)])


class ScopeTests(LinkTestCase):
    """Which files are read, the summary, and the exit codes."""

    def test_readme_is_read(self):
        """A broken link in the root README.md is reported."""
        readme = md("# Readme", "", "[x](gone.md)", "[d](docs/troy-mode/a.md)")
        out = self.run_links({"README.md": readme, A: md("# A")})
        self.assert_broken(out, [("README.md", 3, "gone.md")], ok=[("README.md", 4)])

    def test_files_outside_scope_are_not_read(self):
        """Only README.md and *.md under docs/troy-mode/ are read for links."""
        bad = md("# Out", "", "[x](outside-gone.md)")
        out = self.run_links({
            "docs/other.md": bad,
            "troy-mode/notes.md": bad,
            "docs/troy-mode-old/a.md": bad,
            "docs/troy-mode/notes.txt": bad,
            A: md("# A", "", "[x](inside-gone.md)", "[b](b.md)"),
            "docs/troy-mode/b.md": B_MD,
        })
        self.assert_broken(out, [(A, 3, "inside-gone.md")], ok=[(A, 4)])
        self.assertNotIn("outside-gone", out.stdout)

    def test_files_outside_scope_can_be_targets(self):
        """Tracked files outside the scope resolve, and their headings are anchors."""
        a = md("# A", "", "[o](../other.md)", "[h](../other.md#other-heading)",
               "[t](../../troy-mode/tool.py)", "[n](../other.md#nope)")
        out = self.run_links({A: a, "docs/other.md": md("# Other", "", "## Other heading"),
                              "troy-mode/tool.py": "print('x')\n"})
        self.assert_broken(out, [(A, 6, "../other.md#nope")], ok=[(A, 3), (A, 4), (A, 5)])

    def test_untracked_markdown_is_not_read(self):
        """An untracked page under docs/troy-mode/ is not read."""
        out = self.run_links({A: md("# A", "", "[x](gone.md)", "[b](b.md)"),
                              "docs/troy-mode/b.md": B_MD},
                             untracked={"docs/troy-mode/draft.md": md("# D", "", "[x](draft-gone.md)")})
        self.assert_broken(out, [(A, 3, "gone.md")], ok=[(A, 4)])
        self.assertNotIn("draft-gone", out.stdout)
        _, summary = self.split_output(out)
        self.assertEqual(int(summary.group(1)), 2, out.stdout)

    def test_summary_line_counts_files_and_broken_links(self):
        """The last line counts the files read and the broken links found."""
        out = self.run_links({
            "README.md": md("# Readme", "", "[gone](readme-gone.md)"),
            A: md("# A", "", "[b](sub/b.md)", "[gone](a-gone.md)"),
            "docs/troy-mode/sub/b.md": md("# B"),
            "docs/other.md": md("# Other", "", "[gone](other-gone.md)"),
            "docs/troy-mode/c.txt": "[gone](txt-gone.md)\n",
        })
        lines = self.assert_broken(out, [("README.md", 3, "readme-gone.md"),
                                         (A, 4, "a-gone.md")], ok=[(A, 3)])
        self.assertTrue(lines[0].startswith("README.md:3:"), out.stdout)
        self.assertTrue(lines[1].startswith(f"{A}:4:"), out.stdout)
        self.assertEqual(out.stdout.splitlines()[-1], "3 files checked, 2 broken links.")

    def test_default_repo_is_current_folder(self):
        """Without --repo the script checks the current folder."""
        repo = self.make_repo({A: md("# A", "", "[x](gone.md)", "[b](b.md)"),
                               "docs/troy-mode/b.md": B_MD})
        out = repo.check_from_inside()
        self.assert_broken(out, [(A, 3, "gone.md")], ok=[(A, 4)])

    def test_not_a_repository_exits_two(self):
        """A folder outside git cannot be checked."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "plain"
            (folder / "docs" / "troy-mode").mkdir(parents=True)
            (folder / "README.md").write_text(md("# R", "", "[x](gone.md)"), encoding="utf-8")
            empty = Path(tmp) / "empty-gitconfig"
            empty.write_text("", encoding="utf-8")
            env = {**_env(), "GIT_CONFIG_GLOBAL": str(empty), "GIT_CEILING_DIRECTORIES": tmp}
            out = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(folder)],
                                 capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertTrue([x for x in out.stderr.splitlines() if x.startswith("check_links: error:")],
                        out.stderr)

    def test_non_utf8_file_exits_two(self):
        """A page that is not valid UTF-8 cannot be checked."""
        out = self.run_links({A: md("# A"), "docs/troy-mode/bad.md": b"# Bad\n\xff\xfe x\n"})
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertTrue([x for x in out.stderr.splitlines() if x.startswith("check_links: error:")],
                        out.stderr)


if __name__ == "__main__":
    unittest.main()
