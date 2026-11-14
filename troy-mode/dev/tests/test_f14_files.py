"""Text tests of the files F14 changes besides troy-check and the engine (F14 design 3, 5, 6, 7, 8).

- The new template ``summary-for-troy.md``: its headings, reply lines, and fixed texts.
- R22 in the rules template and its mirror.
- ``[summary] max_chars = 2000`` in ``config.default.toml``.
- The For Troy report field of the three authors, and the tasks that write the summary.
- The Architect's seventh checklist item, and its row in the design template's section 4.
- The entry skill's Waiting comment line and its ``gh pr edit --body-file`` step.
- The PR template, the templates README, the Product Manager, and the guide pages.
- The plugin's next minor version.

Run from the repository root:
python -m unittest discover -s troy-mode/dev/tests -v
"""

import json
import re
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "troy-mode" / "templates"
AGENTS = REPO / "agents"
GUIDE = REPO / "docs" / "troy-mode" / "guide"
SUMMARY_TEMPLATE = TEMPLATES / "summary-for-troy.md"

ZH_HEADING = "## 给 Troy 的摘要"
EN_HEADING = "## Summary for Troy"
ZH_PARTS = ("### 对你有什么变化", "### 需要你决定的事", "### 风险")
EN_PARTS = ("### What changes for you", "### What you decide", "### Risks")
EN_REPLY = ('Reply "all as recommended" (全按推荐) to take every recommendation, or give the '
            "number and the option you want.")
ZH_REPLY = "回复「全按推荐」即可全部采用推荐，或写出编号和你选的方案。"
FIXED_TEXTS = ("Nothing to decide.", "没有需要你决定的事。", "None found.", "没有发现风险。")
FOR_TROY = "For Troy"
CHECKLIST_ITEM = ("The summary for Troy says what the design says, and lists every point Troy "
                  "decides.")
WAITING_LINE = "What to decide is in the summary at the top of the description."
SUMMARY_WORDS = re.compile(r"summary[ -]for[ -]troy", re.IGNORECASE)

# The report fields of each author before F14 (agents/*.md at the approved design's commit).
# F14 adds For Troy after them (design 5.2).
BASE_FIELDS = ("Role", "Task", "Result", "Changed files", "Checks", "Summary", "Findings",
               "Question")
AUTHORS = ("troy-interface-designer.md", "troy-test-manager.md", "troy-architect.md")
# The task subsections that return a summary (design 5.1, 7).
SUMMARY_TASKS = (("troy-interface-designer.md", "IF1 Design"),
                 ("troy-interface-designer.md", "IF2 Revise"),
                 ("troy-test-manager.md", "TM1 Test plan"),
                 ("troy-architect.md", "AR1 Architecture"))
# The design template's section 4 review table had six item rows before F14.
BASE_REVIEW_ROWS = 6


def read(path: Path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def blank_comments(text: str) -> str:
    """The text with each HTML comment's content replaced by its line breaks.

    Line numbers stay the same, so a heading quoted inside a guidance comment
    is not taken for a heading.
    """
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


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


def report_fields(text: str) -> list:
    """The field names of the one fenced code block in a role file's ``## Report`` section.

    Args:
        text: The role file.

    Returns:
        The names of the lines that start ``<Name>: ``, in order, or [] without a block.
    """
    report = section(text, "Report")
    match = re.search(r"```[a-z]*\n(.*?)\n```", report, flags=re.S)
    if not match:
        return []
    return [m.group(1) for m in re.finditer(r"(?m)^([A-Z][A-Za-z ]*): ", match.group(1))]


class SummaryTemplateTests(unittest.TestCase):
    """``troy-mode/templates/summary-for-troy.md`` (design 3.1, 3.2, 7)."""

    @classmethod
    def setUpClass(cls):
        """Reads the template once."""
        cls.text = read(SUMMARY_TEMPLATE)
        cls.lines = cls.text.split("\n")
        cls.outside = blank_comments(cls.text).split("\n")

    def heading_index(self, heading: str) -> int:
        """The line index of a heading outside the guidance comments, failing when missing."""
        found = [i for i, line in enumerate(self.outside) if line.strip() == heading]
        self.assertEqual(len(found), 1, f"{heading!r} must be one heading line of the template")
        return found[0]

    def test_template_exists(self):
        """The template is a file in ``troy-mode/templates``."""
        self.assertTrue(SUMMARY_TEMPLATE.is_file(), SUMMARY_TEMPLATE)

    def test_headings_chinese_part_first(self):
        """The ``##`` and ``###`` headings: the Chinese part and its three parts, then the English."""
        headings = [line.strip() for line in self.outside if re.match(r"^#{2,3} ", line)]
        self.assertEqual(headings, [ZH_HEADING, *ZH_PARTS, EN_HEADING, *EN_PARTS])

    def test_first_heading_is_the_chinese_part(self):
        """No line outside the guidance comments comes before the Chinese heading but blank ones."""
        start = self.heading_index(ZH_HEADING)
        self.assertEqual([line for line in self.outside[:start] if line.strip()], [])

    def test_reply_lines_are_exact_and_in_their_decide_parts(self):
        """Each language's reply line is a whole line, between its decide and risks headings."""
        cases = ((ZH_REPLY, ZH_PARTS[1], ZH_PARTS[2]), (EN_REPLY, EN_PARTS[1], EN_PARTS[2]))
        for reply, decide, risks in cases:
            with self.subTest(reply=reply):
                found = [i for i, line in enumerate(self.lines) if line.strip() == reply]
                self.assertTrue(found, f"no line is exactly {reply!r}")
                start, end = self.heading_index(decide), self.heading_index(risks)
                self.assertTrue(any(start < i < end for i in found),
                                f"{reply!r} is not between {decide!r} and {risks!r}")

    def test_fixed_texts_in_both_languages(self):
        """The nothing-to-decide and none-found texts, in English and Chinese."""
        for text in FIXED_TEXTS:
            with self.subTest(text=text):
                self.assertIn(text, self.text)


class RulesTemplateTests(unittest.TestCase):
    """The R22 row in ``rules.md`` and ``rules.zh-CN.md`` (design 6.1, 7)."""

    CASES = (("rules.md", "Hard"), ("rules.zh-CN.md", "硬"))

    def rows(self, name: str) -> list:
        """The R rows of a rules template, as lists of cells."""
        return [row for table in tables(read(TEMPLATES / name)) for row in table
                if re.fullmatch(r"R\d{2}", row[0])]

    def test_r_rows_are_r01_to_r22_in_order(self):
        """Both templates hold the rows R01 to R22, in order."""
        for name, _ in self.CASES:
            with self.subTest(template=name):
                self.assertEqual([row[0] for row in self.rows(name)],
                                 [f"R{n:02d}" for n in range(1, 23)])

    def test_r22_is_hard_and_enforced_by_ci(self):
        """R22's Type is Hard (硬) and its Enforced by is CI."""
        for name, hard in self.CASES:
            with self.subTest(template=name):
                row = next((row for row in self.rows(name) if row[0] == "R22"), None)
                self.assertIsNotNone(row, f"{name}: no R22 row")
                self.assertEqual(len(row), 6, row)
                self.assertEqual((row[2], row[3]), (hard, "CI"), row)
                self.assertNotEqual(row[1], "", row)


class DefaultConfigTests(unittest.TestCase):
    """``config.default.toml`` gains ``[summary] max_chars = 2000`` (design 6.1)."""

    def test_summary_max_chars_is_2000(self):
        """The file parses, and ``[summary] max_chars`` is the integer 2000."""
        data = tomllib.loads(read(REPO / "troy-mode" / "checks" / "config.default.toml"))
        self.assertIn("summary", data)
        self.assertEqual(data["summary"].get("max_chars"), 2000)
        self.assertIs(type(data["summary"]["max_chars"]), int)


class AgentTests(unittest.TestCase):
    """The three authors and the Architect's checklist (design 5.1, 5.2, 6.2, 7)."""

    def test_for_troy_is_the_last_report_field(self):
        """Each author's report has its fields from before F14, then For Troy."""
        for name in AUTHORS:
            with self.subTest(agent=name):
                self.assertEqual(report_fields(read(AGENTS / name)), [*BASE_FIELDS, FOR_TROY])

    def test_summary_tasks_name_the_summary(self):
        """IF1, IF2, TM1, and AR1 each name the summary for Troy or the For Troy field."""
        for name, heading in SUMMARY_TASKS:
            with self.subTest(agent=name, task=heading):
                text = section(read(AGENTS / name), heading, 3)
                self.assertNotEqual(text.strip(), "", f"{name}: no '### {heading}'")
                self.assertTrue(SUMMARY_WORDS.search(text) or FOR_TROY in text,
                                f"{name}: '### {heading}' names neither the summary nor For Troy")

    def test_architect_has_the_seventh_checklist_item(self):
        """AR2 lists the seventh item after the sixth, which stays as it was."""
        text = section(read(AGENTS / "troy-architect.md"), "AR2 Design review", 3)
        self.assertIn(CHECKLIST_ITEM, text)
        sixth = "Changes an implemented interface only through the change flow."
        self.assertIn(sixth, text)
        self.assertLess(text.index(sixth), text.index(CHECKLIST_ITEM))


class DesignTemplateTests(unittest.TestCase):
    """The design template's section 4 table gains the seventh row, in both languages (6.2)."""

    CASES = (("feature-design.md", "4. Architect review", "summary"),
             ("feature-design.zh-CN.md", "4. 架构师审查", "摘要"))

    def test_review_table_has_seven_rows_the_last_about_the_summary(self):
        """Seven item rows of three cells; the seventh names the summary."""
        for name, heading, word in self.CASES:
            with self.subTest(template=name):
                found = tables(section(read(TEMPLATES / name), heading))
                self.assertTrue(found, f"{name}: no table in section {heading}")
                header, *rows = found[0]
                self.assertEqual(len(rows), BASE_REVIEW_ROWS + 1, found[0])
                self.assertTrue(all(len(row) == len(header) for row in rows), found[0])
                self.assertIn(word, rows[-1][0].lower())
                self.assertTrue(all(word not in row[0].lower() for row in rows[:-1]), rows)


class EntrySkillTests(unittest.TestCase):
    """The entry skill's steps of design 5.3."""

    @classmethod
    def setUpClass(cls):
        """Reads the skill once."""
        cls.text = read(REPO / "skills" / "troy-mode" / "SKILL.md")

    def test_waiting_comment_line(self):
        """The one line under ``Waiting for Troy: approve this PR``."""
        self.assertIn(WAITING_LINE, self.text)

    def test_revision_replaces_the_summary_with_gh_pr_edit(self):
        """A line names the summary with ``gh pr edit`` and ``--body-file``."""
        lines = [line for line in self.text.split("\n")
                 if "gh pr edit" in line and "--body-file" in line and "summary" in line.lower()]
        self.assertTrue(lines, "no line holds gh pr edit, --body-file, and the summary")


class OtherFilesTests(unittest.TestCase):
    """The PR template, the templates README, and the Product Manager (design 7)."""

    def test_pull_request_template_names_the_summary(self):
        """``pull-request.md`` names the summary for Troy."""
        text = read(TEMPLATES / "pull-request.md")
        self.assertTrue(SUMMARY_WORDS.search(text) or ZH_HEADING[3:] in text,
                        "pull-request.md does not name the summary for Troy")

    def test_readme_lists_the_new_template(self):
        """The templates table of the README and its mirror links ``summary-for-troy.md``."""
        for name, heading in (("README.md", "1. Templates"), ("README.zh-CN.md", "1. 模板")):
            with self.subTest(readme=name):
                found = tables(section(read(TEMPLATES / name), heading))
                self.assertTrue(found, f"{name}: no table in section {heading}")
                rows = [row for row in found[0] if any("summary-for-troy.md" in c for c in row)]
                self.assertEqual(len(rows), 1, found[0])

    def test_product_manager_names_the_summary(self):
        """``roles/product-manager.md`` names the summary for Troy (PM1 and PM2)."""
        text = read(REPO / "troy-mode" / "roles" / "product-manager.md")
        self.assertRegex(text, SUMMARY_WORDS)


class GuideTests(unittest.TestCase):
    """The guide pages of design 7 (F10 Guide row), in both languages."""

    def test_reference_names_r22_and_max_chars(self):
        """``08-reference`` names R22 and ``max_chars``."""
        for name in ("08-reference.md", "08-reference.zh-CN.md"):
            text = read(GUIDE / name)
            for word in ("R22", "max_chars"):
                with self.subTest(page=name, word=word):
                    self.assertIn(word, text)

    def test_pages_name_the_summary(self):
        """02, 03, and 07 in Chinese name the summary; 02 and 07 in English too."""
        cases = (("02-start.zh-CN.md", "摘要"), ("03-features.zh-CN.md", "摘要"),
                 ("07-taking-part.zh-CN.md", "摘要"), ("02-start.md", "summary"),
                 ("07-taking-part.md", "summary"))
        for name, word in cases:
            with self.subTest(page=name):
                self.assertIn(word, read(GUIDE / name).lower())

    def test_taking_part_says_how_to_reply(self):
        """07 gives Troy's reply that takes every recommendation."""
        self.assertIn("全按推荐", read(GUIDE / "07-taking-part.zh-CN.md"))
        english = read(GUIDE / "07-taking-part.md")
        self.assertTrue("all as recommended" in english or "全按推荐" in english)


class PluginVersionTests(unittest.TestCase):
    """The build raises the plugin's minor version above 0.2.0 (design 8, D137)."""

    def test_version_is_a_minor_raise(self):
        """``major.minor.patch`` with major 0, minor 3 or more, and patch 0."""
        version = json.loads(read(REPO / ".claude-plugin" / "plugin.json"))["version"]
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
        self.assertIsNotNone(match, version)
        major, minor, patch = (int(part) for part in match.groups())
        self.assertEqual(major, 0, version)
        self.assertGreaterEqual(minor, 3, version)
        self.assertEqual(patch, 0, version)


if __name__ == "__main__":
    unittest.main()
