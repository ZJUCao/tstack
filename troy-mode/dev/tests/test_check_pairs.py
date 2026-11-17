"""Tests for check_pairs.py, the EN/ZH mirror check for tstack's own documents.

Each test builds a small git repository, adds document pairs, and runs the
script as a subprocess. Exit code 0 means every pair matches, 1 means at
least one problem, and 2 means the script could not run.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_pairs.py"

EN_TABLE = """# Thing

| | |
| --- | --- |
| Version | 1.2 |
| Date | 2026-11-05 |

## 1. Goal

Text.

### 1.1 Detail

| A | B |
| --- | --- |
| 1 | 2 |

```text
code
```
"""

ZH_TABLE = """# 东西

> 本文件是 [`x.md`](x.md) 的中文镜像，同步自英文版 1.2（2026-11-05）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 1.2 |
| 日期 | 2026-11-05 |

## 1. 目标

文字。

### 1.1 细节

| 甲 | 乙 |
| --- | --- |
| 1 | 2 |

```text
code
```
"""

EN_FRONT = """---
troy-doc: "{{feature-id}}-design"
lang: "en"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "Draft."
mirror: "design.zh-CN.md"
---

# {{feature-id}} design

<!-- template: Fill in {{marker}} values. Write `{{` and `}}` around names. -->

## 1. Feature

- ID: {{feature-id}}
"""

ZH_FRONT = """---
troy-doc: "{{feature-id}}-design"
lang: "zh-CN"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "草稿。"
mirror-of: "design.md"
---

# {{feature-id}} 设计

<!-- template: 填写 {{标记}}。名字两边写 `{{` 和 `}}`。 -->

## 1. 功能

- 编号：{{feature-id}}
"""


def _env() -> dict:
    """Builds an environment that isolates git from the user's settings."""
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return env


class PairRepo:
    """A temporary git repository holding document pairs."""

    def __init__(self, files: dict) -> None:
        """Creates the repository and adds the files to the index.

        Args:
            files: Repository paths mapped to their text.
        """
        self._tmp = tempfile.TemporaryDirectory(prefix="pairs-")
        self.root = Path(self._tmp.name)
        empty = self.root / "empty-gitconfig"
        empty.write_text("", encoding="utf-8")
        self.env = {**_env(), "GIT_CONFIG_GLOBAL": str(empty)}
        self.git("init", "-q", "-b", "main")
        for rel, text in files.items():
            path = self.root / "repo" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        self.git("add", "-A")

    def git(self, *args: str) -> None:
        """Runs git inside the repository folder."""
        (self.root / "repo").mkdir(exist_ok=True)
        subprocess.run(["git", "-C", str(self.root / "repo"), *args], check=True,
                       env=self.env, capture_output=True)

    def check(self) -> subprocess.CompletedProcess:
        """Runs check_pairs.py on the repository."""
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.root / "repo")],
                              capture_output=True, text=True, encoding="utf-8", env=self.env)

    def close(self) -> None:
        """Deletes the temporary folder."""
        self._tmp.cleanup()


class PairTests(unittest.TestCase):
    """Behavior of check_pairs.py."""

    def run_pairs(self, files: dict) -> subprocess.CompletedProcess:
        """Builds a repository with the files and checks it."""
        repo = PairRepo(files)
        self.addCleanup(repo.close)
        return repo.check()

    def assert_problem(self, files: dict, path: str) -> None:
        """Asserts exit code 1 and a problem line naming the path."""
        out = self.run_pairs(files)
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
        self.assertIn(path, out.stdout)

    def test_matching_table_pair_passes(self):
        """A pair with the same structure and version passes."""
        out = self.run_pairs({"d/x.md": EN_TABLE, "d/x.zh-CN.md": ZH_TABLE})
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_matching_front_matter_pair_passes(self):
        """Template markers in guidance comments and code spans may differ."""
        out = self.run_pairs({"t/feature-design.md": EN_FRONT,
                              "t/feature-design.zh-CN.md": ZH_FRONT})
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_english_without_mirror_is_ignored(self):
        """Most Markdown files have no mirror, and that is fine."""
        out = self.run_pairs({"README.md": "# Readme\n\n## A\n"})
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_mirror_without_english_fails(self):
        """A Chinese mirror needs its English document."""
        self.assert_problem({"d/x.zh-CN.md": ZH_TABLE}, "d/x.zh-CN.md")

    def test_heading_level_differs_fails(self):
        """Heading levels must match."""
        zh = ZH_TABLE.replace("### 1.1 细节", "## 1.1 细节")
        self.assert_problem({"d/x.md": EN_TABLE, "d/x.zh-CN.md": zh}, "d/x.md")

    def test_heading_number_differs_fails(self):
        """Section numbers must match."""
        zh = ZH_TABLE.replace("### 1.1 细节", "### 1.2 细节")
        self.assert_problem({"d/x.md": EN_TABLE, "d/x.zh-CN.md": zh}, "d/x.md")

    def test_missing_section_fails(self):
        """A section added in English only is caught."""
        en = EN_TABLE + "\n## 2. More\n\nText.\n"
        self.assert_problem({"d/x.md": en, "d/x.zh-CN.md": ZH_TABLE}, "d/x.md")

    def test_heading_inside_code_block_is_ignored(self):
        """Lines in fenced code blocks are not headings."""
        en = EN_TABLE.replace("code\n", "# not a heading\n")
        out = self.run_pairs({"d/x.md": en, "d/x.zh-CN.md": ZH_TABLE})
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_table_columns_differ_fails(self):
        """Table column counts must match."""
        zh = ZH_TABLE.replace("| 甲 | 乙 |\n| --- | --- |\n| 1 | 2 |",
                              "| 甲 | 乙 | 丙 |\n| --- | --- | --- |\n| 1 | 2 | 3 |")
        self.assert_problem({"d/x.md": EN_TABLE, "d/x.zh-CN.md": zh}, "d/x.md")

    def test_code_block_count_differs_fails(self):
        """A code block missing from the mirror is caught."""
        zh = ZH_TABLE.replace("```text\ncode\n```\n", "")
        self.assert_problem({"d/x.md": EN_TABLE, "d/x.zh-CN.md": zh}, "d/x.md")

    def test_version_row_differs_fails(self):
        """The version rows must match."""
        zh = ZH_TABLE.replace("| 版本 | 1.2 |", "| 版本 | 1.1 |")
        self.assert_problem({"d/x.md": EN_TABLE, "d/x.zh-CN.md": zh}, "d/x.md")

    def test_sync_note_version_differs_fails(self):
        """The mirror's sync note names the English version it matches."""
        zh = ZH_TABLE.replace("同步自英文版 1.2", "同步自英文版 1.1")
        self.assert_problem({"d/x.md": EN_TABLE, "d/x.zh-CN.md": zh}, "d/x.md")

    def test_missing_sync_note_fails(self):
        """A table-style mirror must have the sync note."""
        zh = "\n".join(line for line in ZH_TABLE.split("\n") if "同步自英文版" not in line)
        self.assert_problem({"d/x.md": EN_TABLE, "d/x.zh-CN.md": zh}, "d/x.md")

    def test_front_matter_version_differs_fails(self):
        """Front matter versions must match."""
        zh = ZH_FRONT.replace('version: "0.1"', 'version: "0.2"')
        self.assert_problem({"t/a.md": EN_FRONT, "t/a.zh-CN.md": zh}, "t/a.md")

    def test_front_matter_doc_id_differs_fails(self):
        """Front matter troy-doc values must match."""
        zh = ZH_FRONT.replace('troy-doc: "{{feature-id}}-design"', 'troy-doc: "other"')
        self.assert_problem({"t/a.md": EN_FRONT, "t/a.zh-CN.md": zh}, "t/a.md")

    def test_front_matter_lang_wrong_fails(self):
        """The English file says en and the mirror says zh-CN."""
        zh = ZH_FRONT.replace('lang: "zh-CN"', 'lang: "en"')
        self.assert_problem({"t/a.md": EN_FRONT, "t/a.zh-CN.md": zh}, "t/a.md")

    def test_front_matter_pointers_disagree_fails(self):
        """mirror and mirror-of name the same document."""
        zh = ZH_FRONT.replace('mirror-of: "design.md"', 'mirror-of: "other.md"')
        self.assert_problem({"t/a.md": EN_FRONT, "t/a.zh-CN.md": zh}, "t/a.md")

    def test_marker_missing_from_mirror_fails(self):
        """A fill-in marker in the English text must also be in the mirror."""
        en = EN_FRONT + "- Name: {{feature-name}}\n"
        self.assert_problem({"t/a.md": en, "t/a.zh-CN.md": ZH_FRONT}, "t/a.md")

    def test_not_a_repository_exits_two(self):
        """A folder outside git cannot be checked."""
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run([sys.executable, str(SCRIPT), "--repo", tmp],
                                 capture_output=True, text=True, encoding="utf-8",
                                 env={**_env(), "GIT_CEILING_DIRECTORIES": str(Path(tmp).parent)})
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
