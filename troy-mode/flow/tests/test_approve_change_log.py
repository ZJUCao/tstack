"""approve's change-log row (F08 design 8, D77, 11.1; interface note section 7; F07 D201).

``approve`` changes the header as in F07 and adds one row to each file's
change log: the new version, the date, and "Approved by Troy." or
"Troy 批准。".

When either file of the pair has no change-log table, ``approve`` exits 1
and changes neither file (F07 design 8.6 and 16, D201, from tstack issue
#46): ``MissingChangeLogTests``. Before D201 it added the row to the file
that had a table and exited 0 with a note, so the pilot's approval was
recorded in English only: its mirror headed the change log ``变更记录``,
not ``修改记录``.

Planted bugs caught here:

- F08 design 11.2, "``approve`` without the change-log row":
  ``ChangeLogRowTests.test_row_in_both_languages`` and
  ``test_row_goes_into_the_change_log_table_only``.
- F07 design 14.2 (D201), "the note with exit 0 kept": every test of
  ``MissingChangeLogTests``.
- D201, "the mirror written before the English file's table is checked":
  ``MissingChangeLogTests.test_english_without_a_change_log_is_refused``,
  ``test_english_heading_with_none_and_no_table_is_refused``,
  ``test_neither_file_with_a_change_log_is_refused``, and
  ``test_the_file_with_a_table_is_not_written``.
- D201, "the check made on the English file only":
  ``MissingChangeLogTests.test_mirror_with_another_heading_is_refused``,
  ``test_mirror_without_a_change_log_is_refused``,
  ``test_mirror_heading_with_none_and_no_table_is_refused``, and
  ``test_the_file_with_a_table_is_not_written``.
"""

import itertools
import unittest

from flow_helpers import FlowCase, Project, base_step, crlf, front_matter

EN = "docs/requirements.md"
ZH = "docs/requirements.zh-CN.md"
DAY = "2026-11-08"
EN_LAST = "| 1.2 | 2026-11-05 | Fixed a typo. |\n"
ZH_LAST = "| 1.2 | 2026-11-05 | 修正笔误。 |\n"
EN_ROW = f"| 2.0 | {DAY} | Approved by Troy. |\n"
ZH_ROW = f"| 2.0 | {DAY} | Troy 批准。 |\n"
# The two change-log headings a D201 problem names (interface note for #46).
HEADINGS = ("Change log", "修改记录")


def english(log_heading: str = "## 14. Change log", log: bool = True) -> str:
    """Requirements at 1.2 whose body holds a fenced change log before the real one.

    Args:
        log_heading: The change log's heading line.
        log: Whether the document has a change log section with a table.

    Returns:
        The document text.
    """
    text = (front_matter("requirements", "en", "1.2", "requirements.zh-CN.md")
            + "# wordcount requirements\n\n## 1. Goal\n\nCount words.\n\n"
            "A change log looks like this:\n\n"
            "```markdown\n## 14. Change log\n\n| Version | Date | Change |\n| --- | --- | --- |\n"
            "| 9.9 | 2020-01-01 | Inside a fence. |\n```\n\n")
    if log:
        text += (f"{log_heading}\n\n| Version | Date | Change |\n| --- | --- | --- |\n"
                 "| 0.1 | 2026-11-01 | First draft. |\n| 1.1 | 2026-11-03 | Added F02. |\n"
                 + EN_LAST + "\n")
    return text + ("## 15. Glossary\n\n| Term | Meaning |\n| --- | --- |\n"
                   "| word | A run of letters. |\n")


def chinese(log: bool = True) -> str:
    """The Chinese mirror at 1.2, with ``## 14. 修改记录`` and a glossary after it.

    Args:
        log: Whether the document has a change log section with a table.

    Returns:
        The document text.
    """
    text = (front_matter("requirements", "zh-CN", "1.2", "requirements.md")
            + "# wordcount 需求\n\n## 1. 目标\n\n统计单词。\n\n")
    if log:
        text += ("## 14. 修改记录\n\n| 版本 | 日期 | 修改 |\n| --- | --- | --- |\n"
                 "| 0.1 | 2026-11-01 | 初稿。 |\n| 1.1 | 2026-11-03 | 加入 F02。 |\n"
                 + ZH_LAST + "\n")
    return text + "## 15. 术语\n\n| 术语 | 含义 |\n| --- | --- |\n| 单词 | 一串字母。 |\n"


def approved(text: str, chinese_text: bool) -> str:
    """The text with the front matter's version, updated, and status lines raised to 2.0."""
    status = f'status: "Troy 已于 {DAY} 批准"' if chinese_text else \
        f'status: "Approved by Troy on {DAY}"'
    old_status = 'status: "草稿，审查中。"' if chinese_text else 'status: "Draft. In review."'
    for old, new in (('version: "1.2"', 'version: "2.0"'),
                     ('updated: "2026-11-01"', f'updated: "{DAY}"'), (old_status, status)):
        if old not in text:
            raise AssertionError(f"{old!r} is not in the text")
        text = text.replace(old, new, 1)
    return text


def cells(line: str) -> list:
    """The trimmed cells of one table row."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def swap(text: str, old: str, new: str) -> str:
    """Replaces a part that occurs exactly once."""
    if text.count(old) != 1:
        raise AssertionError(f"{old!r} occurs {text.count(old)} times")
    return text.replace(old, new)


def assert_problems_name(case: FlowCase, problems: list, paths: list) -> None:
    """Asserts one problem per file without a change-log table (D201).

    Each problem is a string that names both headings, ``Change log`` and
    ``修改记录``, and the problems match the paths one to one, each holding
    its file's path as ``docs/...``.

    Args:
        case: The running test.
        problems: The report's problems.
        paths: The paths of the files that have no change-log table.
    """
    case.assertEqual(len(problems), len(paths), problems)
    for problem in problems:
        case.assertIsInstance(problem, str, problems)
        for heading in HEADINGS:
            case.assertIn(heading, problem, problems)
    case.assertTrue(any(all(path in problem for path, problem in zip(paths, order))
                        for order in itertools.permutations(problems)),
                    f"no problem per path {paths}: {problems}")


class ChangeLogRowTests(FlowCase):
    """One row in each change log, after its last row (note section 7)."""

    def setUp(self):
        """A fresh clone for each test, since approve writes files."""
        self.project = Project([base_step()])

    def approve(self, en: str, zh, en_bytes=None):
        """Writes both files and runs ``approve --doc docs/requirements.md --date <DAY>``."""
        self.project.write(EN, en_bytes if en_bytes is not None else en)
        self.project.write(ZH, zh)
        return self.project.run("approve", "--doc", EN, "--date", DAY)

    def test_row_in_both_languages(self):
        """Planted bug "approve without the row": each file gets its row, after 1.2."""
        en, zh = english(), chinese()
        report = self.report_of(self.approve(en, zh), 0, "approve")
        self.assertEqual(self.project.read(EN),
                         approved(en, False).replace(EN_LAST, EN_LAST + EN_ROW))
        self.assertEqual(self.project.read(ZH),
                         approved(zh, True).replace(ZH_LAST, ZH_LAST + ZH_ROW))
        self.assertEqual(sorted(report["change_log"]), sorted([EN, ZH]))
        self.assertEqual(report["version"], {"from": "1.2", "to": "2.0"})

    def test_row_goes_into_the_change_log_table_only(self):
        """The fenced change log and the glossary after the section stay as they were."""
        en = english()
        self.report_of(self.approve(en, chinese()))
        text = self.project.read(EN)
        self.assertEqual(text.count("Approved by Troy."), 1, text)
        self.assertIn("| 9.9 | 2020-01-01 | Inside a fence. |\n```\n", text)
        self.assertIn("| word | A run of letters. |\n", text)
        self.assertTrue(text.endswith("| word | A run of letters. |\n"), text[-200:])

    def test_heading_in_any_case_without_a_number(self):
        """``## CHANGE LOG`` is the change log too."""
        en = english("## CHANGE LOG")
        self.report_of(self.approve(en, chinese()))
        self.assertEqual(self.project.read(EN),
                         approved(en, False).replace(EN_LAST, EN_LAST + EN_ROW))

    def test_wider_table_gets_empty_cells_between(self):
        """A table with an Author column: the version first, the date second, the text last."""
        en = english().replace("| Version | Date | Change |\n| --- | --- | --- |\n| 0.1",
                               "| Version | Date | Author | Change |\n| --- | --- | --- | --- |\n"
                               "| 0.1")
        en = en.replace("| 0.1 | 2026-11-01 | First draft. |",
                        "| 0.1 | 2026-11-01 | Troy | First draft. |")
        en = en.replace("| 1.1 | 2026-11-03 | Added F02. |",
                        "| 1.1 | 2026-11-03 | PM | Added F02. |")
        en = en.replace(EN_LAST, "| 1.2 | 2026-11-05 | PM | Fixed a typo. |\n")
        self.report_of(self.approve(en, chinese()))
        lines = self.project.read(EN).split("\n")
        index = lines.index("| 1.2 | 2026-11-05 | PM | Fixed a typo. |")
        self.assertEqual(cells(lines[index + 1]), ["2.0", DAY, "", "Approved by Troy."])
        self.assertEqual(lines[index + 2], "")

    def test_crlf_row_takes_the_tables_line_ending(self):
        """A CRLF document gets a CRLF row."""
        en = english()
        self.report_of(self.approve(en, chinese(), en_bytes=crlf(en)))
        self.assertEqual(self.project.read_bytes(EN),
                         crlf(approved(en, False).replace(EN_LAST, EN_LAST + EN_ROW)))


class MissingChangeLogTests(FlowCase):
    """D201 (tstack issue #46): either file without a change-log table refuses the approval.

    ``approve`` exits 1 with ``ok`` false and one problem per file that has
    no table, naming the file and both headings, and leaves both files byte
    for byte as they were: no header change and no row, in either language.
    """

    def setUp(self):
        """A fresh clone for each test, since a wrong approve writes files."""
        self.project = Project([base_step()])

    def write_and_approve(self, en: str, zh: str):
        """Writes both files and runs ``approve`` on them.

        Args:
            en: The English file's text.
            zh: The mirror's text.

        Returns:
            ``(outcome, {path: bytes before the run}, {path: bytes after it})``.
        """
        self.project.write(EN, en)
        self.project.write(ZH, zh)
        before = {rel: self.project.read_bytes(rel) for rel in (EN, ZH)}
        out = self.project.run("approve", "--doc", EN, "--date", DAY)
        after = {rel: self.project.read_bytes(rel) for rel in (EN, ZH)}
        return out, before, after

    def refused(self, en: str, zh: str, lacking: list) -> dict:
        """Asserts that ``approve`` refuses the pair and writes neither file.

        Args:
            en: The English file's text.
            zh: The mirror's text.
            lacking: The paths of the files that have no change-log table.

        Returns:
            The report.
        """
        out, before, after = self.write_and_approve(en, zh)
        report = self.report_of(out, 1, "approve")
        for rel in (EN, ZH):
            self.assertEqual(after[rel], before[rel], f"{rel} changed")
        assert_problems_name(self, report["problems"], lacking)
        return report

    def test_mirror_with_another_heading_is_refused(self):
        """The pilot's case: the mirror heads its change log ``## 14. 变更记录``, not
        ``修改记录``, so it has no change-log table; one problem, for the mirror."""
        zh = swap(chinese(), "## 14. 修改记录", "## 14. 变更记录")
        self.refused(english(), zh, [ZH])

    def test_mirror_without_a_change_log_is_refused(self):
        """The English file has a change log and the mirror none: one problem, for the mirror,
        and no row in English (before D201 the English file got the row)."""
        self.refused(english(), chinese(log=False), [ZH])

    def test_mirror_heading_with_none_and_no_table_is_refused(self):
        """The mirror's ``## 14. 修改记录`` holds ``无。`` and no table: one problem, for it."""
        zh = swap(chinese(log=False), "## 15. 术语", "## 14. 修改记录\n\n无。\n\n## 15. 术语")
        self.refused(english(), zh, [ZH])

    def test_english_without_a_change_log_is_refused(self):
        """Only a fenced example change log in English, a real one in the mirror: one problem,
        for the English file, and no row in the mirror."""
        self.refused(english(log=False), chinese(), [EN])

    def test_english_heading_with_none_and_no_table_is_refused(self):
        """``## 14. Change log`` followed by ``None.`` and the next section: one problem, for
        the English file (before D201 only the mirror got the row)."""
        en = swap(english(log=False), "## 15. Glossary",
                  "## 14. Change log\n\nNone.\n\n## 15. Glossary")
        self.refused(en, chinese(), [EN])

    def test_neither_file_with_a_change_log_is_refused(self):
        """No change log in either file: two problems, one naming each file, and no header
        change (before D201 the header changed and a note said so)."""
        self.refused(english(log=False), chinese(log=False), [EN, ZH])

    def test_the_file_with_a_table_is_not_written(self):
        """When only its partner lacks the table, the file that has one keeps version 1.2 and
        gets no row: the English file when the mirror is bad, the mirror when English is."""
        cases = {
            "mirror bad": (english(), swap(chinese(), "## 14. 修改记录", "## 14. 变更记录"), EN,
                           "Approved by Troy"),
            "English bad": (english(log=False), chinese(), ZH, "Troy 批准"),
        }
        for name, (en, zh, good, approval) in cases.items():
            with self.subTest(case=name):
                out, before, after = self.write_and_approve(en, zh)
                self.assert_exit(out, 1)
                self.assertEqual(after[good], before[good], f"{good} changed")
                text = after[good].decode("utf-8")
                self.assertIn('version: "1.2"', text)
                self.assertNotIn(approval, text)


if __name__ == "__main__":
    unittest.main()
