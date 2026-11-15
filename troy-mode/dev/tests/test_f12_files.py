"""Text tests of the files F12 changes besides the engine (F12 design 9, 12, 13; note section 11).

- The new label in ``templates/README.md`` section 5 and its mirror, between
  "Passes tests on main" and "Usable on Troy's devices".
- The label in the requirements template's Status comment, in both languages.
- TM8 in the Test Manager's agent file, and PM3 in the Product Manager's role.
- The entry skill's real run, TM8, the comment heading, the bug title, and the
  release test's ``--real-run``.
- The guide pages 03, 05, 07, and 08, and their mirrors.
- The plugin's next minor version.

Run from the repository root:
python -m unittest discover -s troy-mode/dev/tests -p test_f12_files.py -v
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "troy-mode" / "templates"
GUIDE = REPO / "docs" / "troy-mode" / "guide"

LABEL = "Ran for real on Troy's PC"
LABEL_ZH = "在 Troy 的电脑上真跑过"
TM8_KINDS = ("bug", "prototype", "requirement", "later", "setup", "console")
SKILL_TEXTS = ("real-run --item", "real-run --all", "TM8", "Real run output, part <n>",
               "Real run of <ID>:", "--real-run")


def read(path: Path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def section(text: str, heading: str, level: int = 2) -> str:
    """The text under a heading, up to the next heading of the same or a higher level.

    Fenced code blocks are skipped when looking for the end.

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
    found, fence = [], False
    for line in lines[start + 1:]:
        if re.match(r"^ {0,3}(```|~~~)", line):
            fence = not fence
        match = None if fence else re.match(r"^(#{1,6}) ", line)
        if match and len(match.group(1)) <= level:
            break
        found.append(line)
    return "\n".join(found)


def tables(text: str) -> list:
    """The Markdown tables of a text, each a list of rows of cells, separator rows left out."""
    found, current = [], []
    for line in text.split("\n") + [""]:
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                current.append(cells)
        elif current:
            found.append(current)
            current = []
    return found


class LabelTests(unittest.TestCase):
    """The new status label in the templates README and its mirror (design 9, 12)."""

    CASES = (("README.md", "5. Feature status labels", "Passes tests on main", LABEL,
              "Usable on Troy's devices"),
             ("README.zh-CN.md", "5. 功能状态标签", "在 main 上通过测试", LABEL_ZH,
              "在 Troy 的设备上可用"))

    def test_label_row_sits_between_the_two_labels(self):
        """The row comes right after "Passes tests on main" and right before "Usable on
        Troy's devices", with a "Set when" cell."""
        for name, heading, before, label, after in self.CASES:
            with self.subTest(readme=name):
                found = tables(section(read(TEMPLATES / name), heading))
                self.assertTrue(found, f"{name}: no table in section {heading}")
                labels = [row[0] for row in found[0]]
                for text in (before, label, after):
                    self.assertEqual(labels.count(text), 1, labels)
                self.assertEqual(labels.index(label), labels.index(before) + 1, labels)
                self.assertEqual(labels.index(after), labels.index(label) + 1, labels)
                row = found[0][labels.index(label)]
                self.assertEqual(len(row), 2, row)
                self.assertNotEqual(row[1], "", row)

    def test_english_row_says_when(self):
        """The English row's cell names the real run and PR 6 (design 9)."""
        found = tables(section(read(TEMPLATES / "README.md"), "5. Feature status labels"))
        self.assertTrue(found)
        row = next((row for row in found[0] if row[0] == LABEL), None)
        self.assertIsNotNone(row, found[0])
        self.assertRegex(row[1], re.compile(r"real run", re.IGNORECASE))
        self.assertIn("PR 6", row[1])


class RequirementsTemplateTests(unittest.TestCase):
    """The Status comment of the requirements template lists the label (design 9, 12)."""

    def test_status_comment_lists_the_label(self):
        """The comment that lists the Status values names the new label, in both languages."""
        cases = (("requirements.md", "Status is one of", LABEL),
                 ("requirements.zh-CN.md", "状态只能是", LABEL_ZH))
        for name, marker, label in cases:
            with self.subTest(template=name):
                comments = re.findall(r"<!--.*?-->", read(TEMPLATES / name), flags=re.S)
                found = [c for c in comments if marker in c]
                self.assertEqual(len(found), 1, f"{name}: one comment with {marker!r}")
                self.assertIn(label, found[0])


class RoleTests(unittest.TestCase):
    """TM8 for the Test Manager and PM3 for the Product Manager (design 7.1, 12)."""

    def test_tm8_section(self):
        """``### TM8 Real-run mismatches`` names the six kinds and changes no file."""
        text = section(read(REPO / "agents" / "troy-test-manager.md"),
                       "TM8 Real-run mismatches", 3)
        self.assertNotEqual(text.strip(), "", "no '### TM8 Real-run mismatches'")
        for kind in TM8_KINDS:
            with self.subTest(kind=kind):
                self.assertRegex(text, rf"`{kind}|\b{kind}\b")
        self.assertRegex(text, re.compile(r"change[s]? no file", re.IGNORECASE))

    def test_tm8_comes_after_tm7(self):
        """The task subsections stay in order."""
        text = read(REPO / "agents" / "troy-test-manager.md")
        self.assertLess(text.find("### TM7 "), text.find("### TM8 Real-run mismatches"))
        self.assertGreaterEqual(text.find("### TM7 "), 0)

    def test_pm3_runs_the_real_run(self):
        """PM3 names ``real-run``, the run file, TM8, and ``label``."""
        text = section(read(REPO / "troy-mode" / "roles" / "product-manager.md"),
                       "PM3 Acceptance", 3)
        self.assertNotEqual(text.strip(), "", "no '### PM3 Acceptance'")
        for word in ("real-run", ".run.toml", "TM8", "label"):
            with self.subTest(word=word):
                self.assertIn(word, text)


class EntrySkillTests(unittest.TestCase):
    """The entry skill's real run, TM8, and release test (design 12, F07 entry skill row)."""

    def test_skill_names_the_real_run(self):
        """``real-run --item`` and ``--all``, TM8, the comment heading, the bug title, and
        ``--real-run``."""
        text = read(REPO / "skills" / "troy-mode" / "SKILL.md")
        for words in SKILL_TEXTS:
            with self.subTest(text=words):
                self.assertIn(words, text)


class GuideTests(unittest.TestCase):
    """The guide pages of design 12 (F10 guide row), in both languages."""

    def test_pages_name_the_real_run(self):
        """03, 05, and 08 and their mirrors name ``real-run``."""
        for page in ("03-features", "05-release", "08-reference"):
            for name in (f"{page}.md", f"{page}.zh-CN.md"):
                with self.subTest(page=name):
                    self.assertIn("real-run", read(GUIDE / name))

    def test_taking_part_names_the_label(self):
        """07 names the label, and its mirror the Chinese label."""
        self.assertIn(LABEL, read(GUIDE / "07-taking-part.md"))
        self.assertIn(LABEL_ZH, read(GUIDE / "07-taking-part.zh-CN.md"))

    def test_reference_names_the_run_file_and_the_comment_heading(self):
        """08 names the run file and the heading of the real output comments."""
        text = read(GUIDE / "08-reference.md")
        self.assertIn(".run.toml", text)
        self.assertIn("Real run output, part", text)


class PluginVersionTests(unittest.TestCase):
    """The build raises the plugin's minor version (design 13, D113; note section 11)."""

    def test_version_is_a_minor_raise(self):
        """``0.x.0`` with x at least 4 (F14 took 0.3.0, F13 may take 0.4.0 first)."""
        version = json.loads(read(REPO / ".claude-plugin" / "plugin.json"))["version"]
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
        self.assertIsNotNone(match, version)
        major, minor, patch = (int(part) for part in match.groups())
        self.assertEqual((major, patch), (0, 0), version)
        self.assertGreaterEqual(minor, 4, version)


if __name__ == "__main__":
    unittest.main()
