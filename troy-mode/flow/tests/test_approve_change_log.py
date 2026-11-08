"""approve's change-log row (F08 design 8, D77, 11.1; interface note section 7).

``approve`` changes the header as in F07 and adds one row to each file's
change log: the new version, the date, and "Approved by Troy." or
"Troy 批准。". A file without a change log gets no row.

Planted bug of F08 design 11.2 caught here: "``approve`` without the
change-log row": ``ChangeLogRowTests.test_row_in_both_languages`` and
``test_row_goes_into_the_change_log_table_only``.
"""

import unittest

from flow_helpers import FlowCase, Project, base_step, crlf, front_matter

EN = "docs/requirements.md"
ZH = "docs/requirements.zh-CN.md"
DAY = "2026-11-08"
EN_LAST = "| 1.2 | 2026-11-05 | Fixed a typo. |\n"
ZH_LAST = "| 1.2 | 2026-11-05 | 修正笔误。 |\n"
EN_ROW = f"| 2.0 | {DAY} | Approved by Troy. |\n"
ZH_ROW = f"| 2.0 | {DAY} | Troy 批准。 |\n"


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

    def test_document_without_a_change_log_gets_no_row(self):
        """No change log in either file: only the header changes, and a note says so."""
        en, zh = english(log=False), chinese(log=False)
        report = self.report_of(self.approve(en, zh))
        self.assertEqual(self.project.read(EN), approved(en, False))
        self.assertEqual(self.project.read(ZH), approved(zh, True))
        self.assertEqual(report["change_log"], [])
        self.assertNotEqual(report["notes"], [])

    def test_only_the_file_with_a_change_log_gets_a_row(self):
        """The English file has a change log and the mirror none: one row, in English."""
        en, zh = english(), chinese(log=False)
        report = self.report_of(self.approve(en, zh))
        self.assertEqual(self.project.read(EN),
                         approved(en, False).replace(EN_LAST, EN_LAST + EN_ROW))
        self.assertEqual(self.project.read(ZH), approved(zh, True))
        self.assertEqual(report["change_log"], [EN])

    def test_heading_without_a_table_gets_no_row(self):
        """``## 14. Change log`` followed by ``None.`` and the next section: no row."""
        en = english(log=False).replace("## 15. Glossary", "## 14. Change log\n\nNone.\n\n"
                                                           "## 15. Glossary")
        zh = chinese()
        report = self.report_of(self.approve(en, zh))
        self.assertEqual(self.project.read(EN), approved(en, False))
        self.assertEqual(report["change_log"], [ZH])

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


if __name__ == "__main__":
    unittest.main()
