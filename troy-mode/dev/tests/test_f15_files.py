"""Text tests of the files F15 adds besides the engine (F15 design 8, 11, 12, 13.1; note section 8).

- ``idea-issue.md``: GitHub's issue template, its front matter exactly, and two
  comment lines that ask for the idea, in both languages.
- ``progress-issue.md`` and ``device-test-issue.md``: the bodies' shapes,
  Chinese first, with a ``template:`` comment, the boxes in the Chinese part.
- A row for each in the templates README and its mirror.
- The plugin's next minor version.

Run from the repository root:
python -m unittest discover -s troy-mode/dev/tests -p test_f15_files.py -v
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "troy-mode" / "templates"
DETAILS = "<details><summary>English</summary>"
IDEA_FIELDS = {"name": "Idea / 想法",
               "about": "An idea or change for troy-mode to take in / 交给 troy-mode 的想法或改动",
               "labels": "idea"}
CJK = re.compile(r"[一-鿿]")
BOX = re.compile(r"^\s*- \[[ xX]\]")


def read(path: Path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def section(text: str, heading: str) -> str:
    """The text under a ``## `` heading, up to the next ``## `` or ``# `` heading."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == f"## {heading}"), None)
    if start is None:
        return ""
    found = []
    for line in lines[start + 1:]:
        if re.match(r"^#{1,2} ", line):
            break
        found.append(line)
    return "\n".join(found)


def table_rows(text: str) -> list:
    """The rows of the Markdown tables of a text, as lists of cells, separators left out."""
    rows = []
    for line in text.split("\n"):
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                rows.append(cells)
    return rows


class IdeaTemplateTests(unittest.TestCase):
    """``troy-mode/templates/idea-issue.md`` (design 5.1, 8.2, 11; note section 8)."""

    @classmethod
    def setUpClass(cls):
        """Reads the template once and splits off its front matter."""
        cls.text = read(TEMPLATES / "idea-issue.md")
        lines = cls.text.split("\n")
        cls.fields, cls.rest = {}, []
        if lines and lines[0] == "---" and "---" in lines[1:]:
            end = lines.index("---", 1)
            for line in lines[1:end]:
                key, _, value = line.partition(":")
                cls.fields[key.strip()] = value.strip().strip("\"'")
            cls.rest = lines[end + 1:]

    def test_front_matter_is_exact(self):
        """``name``, ``about``, and ``labels``, and nothing else."""
        self.assertEqual(self.fields, IDEA_FIELDS)

    def test_two_comment_lines_in_both_languages(self):
        """After the front matter: two HTML comment lines, one Chinese, one English."""
        lines = [line for line in self.rest if line.strip()]
        self.assertEqual(len(lines), 2, lines)
        for line in lines:
            with self.subTest(line=line):
                self.assertRegex(line.strip(), r"^<!--.*-->$")
        self.assertEqual(sum(bool(CJK.search(line)) for line in lines), 1, lines)


class BodyTemplateTests(unittest.TestCase):
    """``progress-issue.md`` and ``device-test-issue.md`` (design 4.2, 6.2, 11)."""

    MARKERS = {"progress-issue.md": "<!-- troy-mode: progress ",
               "device-test-issue.md": "<!-- troy-mode: device-test "}

    def test_shapes(self):
        """A ``template:`` comment, the marker, Chinese first, the boxes in the Chinese part."""
        for name, marker in self.MARKERS.items():
            with self.subTest(template=name):
                text = read(TEMPLATES / name)
                self.assertIn("<!-- template:", text)
                self.assertIn(marker, text)
                self.assertEqual(text.count(DETAILS), 1)
                chinese, english = text.split(DETAILS, 1)
                self.assertRegex(chinese, CJK)
                self.assertTrue([line for line in chinese.split("\n") if BOX.match(line)])
                self.assertFalse([line for line in english.split("\n") if BOX.match(line)])
                self.assertIn("</details>", english)

    def test_progress_shape_names_the_six_stages(self):
        """The six stage names in both languages, in order."""
        text = read(TEMPLATES / "progress-issue.md")
        chinese, _, english = text.partition(DETAILS)
        for part, names in ((chinese, ("接口设计", "测试计划", "模拟", "测试", "实现", "验收")),
                            (english, ("Interface design", "Test plan", "Mock", "Tests",
                                       "Implementation", "Acceptance"))):
            positions = [part.find(f"{n}/6 {name}") for n, name in enumerate(names, 1)]
            self.assertTrue(all(p >= 0 for p in positions), positions)
            self.assertEqual(positions, sorted(positions))

    def test_checklist_shape_ends_with_the_accept_box(self):
        """The accept box ``我接受`` is the last box."""
        chinese = read(TEMPLATES / "device-test-issue.md").partition(DETAILS)[0]
        boxes = [line for line in chinese.split("\n") if BOX.match(line)]
        self.assertTrue(boxes)
        self.assertIn("我接受", boxes[-1])


class ReadmeTests(unittest.TestCase):
    """The templates README and its mirror list the three (design 11, F01 row)."""

    def test_readme_rows(self):
        """One row of section 1's table for each new template, in both languages."""
        for name, heading in (("README.md", "1. Templates"), ("README.zh-CN.md", "1. 模板")):
            rows = table_rows(section(read(TEMPLATES / name), heading))
            for template in ("idea-issue.md", "progress-issue.md", "device-test-issue.md"):
                with self.subTest(readme=name, template=template):
                    found = [row for row in rows if any(template in cell for cell in row)]
                    self.assertEqual(len(found), 1, rows)

    def test_idea_row_names_its_path_in_the_project(self):
        """The idea template's row names ``.github/ISSUE_TEMPLATE/idea.md``."""
        for name, heading in (("README.md", "1. Templates"), ("README.zh-CN.md", "1. 模板")):
            with self.subTest(readme=name):
                rows = table_rows(section(read(TEMPLATES / name), heading))
                found = [row for row in rows if any("idea-issue.md" in cell for cell in row)]
                self.assertTrue(found and ".github/ISSUE_TEMPLATE/idea.md" in " ".join(found[0]),
                                found)


class PluginVersionTests(unittest.TestCase):
    """F15's build raises the plugin's minor version (design 12, D149)."""

    def test_version_is_the_next_minor(self):
        """``0.x.0`` with x at least 7: F19 took 0.6.0 before F15."""
        version = json.loads(read(REPO / ".claude-plugin" / "plugin.json"))["version"]
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
        self.assertIsNotNone(match, version)
        major, minor, patch = (int(part) for part in match.groups())
        self.assertEqual((major, patch), (0, 0), version)
        self.assertGreaterEqual(minor, 7, version)


if __name__ == "__main__":
    unittest.main()
