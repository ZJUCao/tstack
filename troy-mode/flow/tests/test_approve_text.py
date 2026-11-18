"""Approve and text group (F07 design 8.4, 8.6, 14.1): ``approve`` and ``check-text``.

Since D201 (F07 design 16, tstack issue #46), ``approve`` refuses a pair in
which either file has no change-log table, so the requirements pair here
holds a change log in both languages, and an approval also adds its row
there (F08 D77). ``test_approve_change_log`` tests the row and the refusal
in detail.

Planted bug of design 14.2 caught here: "``approve`` raising only the English
file": ``ApproveTests.test_approve_raises_both_languages``,
``test_approve_from_the_mirror``, and ``test_next_major_from_a_minor_version``.
"""

import unittest
from datetime import date

from flow_helpers import (
    CONFIG, F01, Fakes, FlowCase, Project, base_step, config_text, crlf, design_text,
    front_matter, stages,
)

EN = "docs/requirements.md"
ZH = "docs/requirements.zh-CN.md"
EN_STATUS = 'status: "Draft. In review."'
ZH_STATUS = 'status: "草稿，审查中。"'
UPDATED = 'updated: "2026-11-01"'
EN_LOG_ROW = "| 0.1 | 2026-11-01 | First draft. |\n"
ZH_LOG_ROW = "| 0.1 | 2026-11-01 | 初稿。 |\n"


def pair(version: str = "0.3", zh_version=None, zh_log: bool = True) -> dict:
    """The requirements and their mirror, each with a body that repeats the header lines.

    The body holds the same ``version``, ``updated``, and ``status`` lines in
    a fenced block, so only the front matter's lines may change, and then a
    change log with one row (D201: ``approve`` needs one in both files).

    Args:
        version: The English version.
        zh_version: The Chinese version, or None for the same.
        zh_log: Whether the mirror has its change log.

    Returns:
        Paths mapped to text.
    """
    sample = f'```yaml\nversion: "{version}"\n{UPDATED}\n{EN_STATUS}\n```\n'
    en = (front_matter("requirements", "en", version, "requirements.zh-CN.md")
          + "# wordcount requirements\n\nA header looks like this:\n\n" + sample
          + "\n## 2. Change log\n\n| Version | Date | Change |\n| --- | --- | --- |\n"
          + EN_LOG_ROW)
    zh = (front_matter("requirements", "zh-CN", zh_version or version, "requirements.md")
          + "# wordcount 需求\n\n文件头的样子：\n\n" + sample)
    if zh_log:
        zh += "\n## 2. 修改记录\n\n| 版本 | 日期 | 修改 |\n| --- | --- | --- |\n" + ZH_LOG_ROW
    return {EN: en, ZH: zh}


def approved(text: str, old_version: str, new_version: str, day: str, chinese: bool) -> str:
    """The text with only the first version, updated, and status lines changed, and the
    change log's row "Approved by Troy." (``Troy 批准。``) after its last row (F08 D77)."""
    status = f'status: "Troy 已于 {day} 批准"' if chinese else f'status: "Approved by Troy on {day}"'
    text = text.replace(f'version: "{old_version}"', f'version: "{new_version}"', 1)
    text = text.replace(UPDATED, f'updated: "{day}"', 1)
    text = text.replace(ZH_STATUS if chinese else EN_STATUS, status, 1)
    last, change = (ZH_LOG_ROW, "Troy 批准。") if chinese else (EN_LOG_ROW, "Approved by Troy.")
    if text.count(last) != 1:
        raise AssertionError(f"{last!r} occurs {text.count(last)} times")
    return text.replace(last, last + f"| {new_version} | {day} | {change} |\n")


class ApproveTests(FlowCase):
    """Troy's approval in a document's header and its mirror's (design 8.6)."""

    def setUp(self):
        """A fresh clone for each test, since approve writes files."""
        self.project = Project([base_step()])

    def approve(self, doc: str, *extra: str, fakes=None):
        """Runs ``approve --doc <doc> --json`` on the clone."""
        return self.project.run("approve", "--doc", doc, *extra, fakes=fakes)

    def write(self, files: dict) -> None:
        """Writes files into the working tree."""
        for rel, text in files.items():
            self.project.write(rel, text)

    def test_approve_raises_both_languages(self):
        """Planted bug "only the English file": both headers move to 1.0 with both status lines."""
        files = pair("0.3")
        self.write(files)
        report = self.report_of(self.approve(EN, "--date", "2026-11-07"), 0, "approve")
        self.assertEqual(self.project.read(EN), approved(files[EN], "0.3", "1.0", "2026-11-07",
                                                         False))
        self.assertEqual(self.project.read(ZH), approved(files[ZH], "0.3", "1.0", "2026-11-07",
                                                         True))
        self.assertEqual((report["doc"], report["mirror"]), (EN, ZH))
        self.assertEqual(report["version"], {"from": "0.3", "to": "1.0"})
        self.assertEqual(report["updated"], "2026-11-07")
        self.assertEqual(sorted(report["changed"]), [EN, ZH])

    def test_approve_from_the_mirror(self):
        """Planted bug "only the English file": ``--doc`` naming the mirror changes both files."""
        files = pair("0.5")
        self.write(files)
        report = self.report_of(self.approve(ZH, "--date", "2026-11-09"))
        self.assertEqual(self.project.read(EN), approved(files[EN], "0.5", "1.0", "2026-11-09",
                                                         False))
        self.assertEqual(self.project.read(ZH), approved(files[ZH], "0.5", "1.0", "2026-11-09",
                                                         True))
        self.assertEqual(sorted(report["changed"]), [EN, ZH])

    def test_next_major_from_a_minor_version(self):
        """Planted bug "only the English file": 1.2 becomes 2.0 in both files."""
        files = pair("1.2")
        self.write(files)
        report = self.report_of(self.approve(EN, "--date", "2026-11-07"))
        self.assertEqual(report["version"], {"from": "1.2", "to": "2.0"})
        self.assertEqual(self.project.read(EN), approved(files[EN], "1.2", "2.0", "2026-11-07",
                                                         False))
        self.assertEqual(self.project.read(ZH), approved(files[ZH], "1.2", "2.0", "2026-11-07",
                                                         True))

    def test_line_endings_are_kept(self):
        """A CRLF document stays CRLF; only the three header lines change."""
        files = pair("0.3")
        self.project.write(EN, crlf(files[EN]))
        self.project.write(ZH, files[ZH])
        self.report_of(self.approve(EN, "--date", "2026-11-07"))
        self.assertEqual(self.project.read_bytes(EN),
                         crlf(approved(files[EN], "0.3", "1.0", "2026-11-07", False)))
        self.assertEqual(self.project.read(ZH), approved(files[ZH], "0.3", "1.0", "2026-11-07",
                                                         True))

    def test_feature_design_and_its_mirror(self):
        """A feature design pair, found through ``mirror`` in the same folder.

        The design has a change log, so F08's D77 adds one row to each file's
        change log besides the header (F08 note, section 7). F07 expected
        only the header lines to change.
        """
        en, zh = F01.design, f"{F01.folder}/design.zh-CN.md"
        files = {en: design_text(F01, "0.2"), zh: design_text(F01, "0.2", "zh-CN")}
        self.write(files)
        report = self.report_of(self.approve(en, "--date", "2026-11-07"))
        self.assertEqual(self.project.read(en), approved(files[en], "0.2", "1.0", "2026-11-07",
                                                         False))
        self.assertIn("| 0.1 | 2026-11-01 | First draft. |\n"
                      "| 1.0 | 2026-11-07 | Approved by Troy. |\n", self.project.read(en))
        self.assertEqual(self.project.read(zh), approved(files[zh], "0.2", "1.0", "2026-11-07",
                                                         True))
        self.assertIn("| 0.1 | 2026-11-01 | 初稿。 |\n| 1.0 | 2026-11-07 | Troy 批准。 |\n",
                      self.project.read(zh))
        self.assertEqual(sorted(report["changed"]), sorted([en, zh]))
        self.assertEqual(sorted(report["change_log"]), sorted([en, zh]))

    def test_refusals_change_nothing(self):
        """Different versions, a missing mirror, no front matter, a mirror without a change-log
        table (D201), or no file: exit 1, no change."""
        cases = {
            "versions differ": pair("0.3", "0.2"),
            "mirror missing": {EN: pair("0.3")[EN], ZH: None},
            "no front matter": {EN: "# Notes\n\nNo header.\n", ZH: pair("0.3")[ZH]},
            "mirror without a change log": pair("0.3", zh_log=False),
        }
        for label, files in cases.items():
            with self.subTest(case=label):
                self.project = Project([base_step()])
                for rel, text in files.items():
                    if text is None:
                        self.project.remove(rel)
                    else:
                        self.project.write(rel, text)
                before = {rel: self.project.exists(rel) and self.project.read_bytes(rel)
                          for rel in (EN, ZH)}
                report = self.report_of(self.approve(EN, "--date", "2026-11-07"), 1, "approve")
                self.assertNotEqual(report["problems"], [])
                after = {rel: self.project.exists(rel) and self.project.read_bytes(rel)
                         for rel in (EN, ZH)}
                self.assertEqual(after, before)
        self.report_of(self.approve("docs/no-such-document.md", "--date", "2026-11-07"), 1)

    def test_bad_date_exits_two(self):
        """A date that is not ``YYYY-MM-DD`` exits 2 and changes nothing."""
        files = pair("0.3")
        self.write(files)
        self.assert_exit(self.approve(EN, "--date", "07/11/2026"), 2)
        self.assertEqual(self.project.read(EN), files[EN])
        self.assertEqual(self.project.read(ZH), files[ZH])

    def test_date_defaults_to_today(self):
        """Without ``--date``, ``updated`` and both status lines carry today's date."""
        self.write(pair("0.3"))
        before = date.today().isoformat()
        report = self.report_of(self.approve(EN))
        after = date.today().isoformat()
        self.assertIn(report["updated"], {before, after})
        self.assertIn(f'status: "Approved by Troy on {report["updated"]}"', self.project.read(EN))
        self.assertIn(f'status: "Troy 已于 {report["updated"]} 批准"', self.project.read(ZH))

    def test_approve_never_calls_gh(self):
        """A gh that fails on every call is not called."""
        self.write(pair("0.3"))
        fakes = Fakes(fail=True)
        self.report_of(self.approve(EN, "--date", "2026-11-07", fakes=fakes))
        self.assertEqual(fakes.gh_calls(), [])


class CheckTextTests(FlowCase):
    """A PR comment checked with troy-check's attribution rules (R19, design 8.4)."""

    def setUp(self):
        """A fresh clone whose config at HEAD sets ``strict``."""
        self.project = Project([base_step(), *stages(F01, 1)])

    def check_text(self, text: str, fakes=None):
        """Writes the text to a file outside the clone and runs ``check-text`` on it."""
        path = self.project.tmp / "comment.md"
        path.write_bytes(text.encode("utf-8"))
        return self.project.run("check-text", "--file", str(path), fakes=fakes)

    def test_strict_mode_refuses_the_word(self):
        """In strict mode, a line naming Claude is one problem, with its line number."""
        out = self.check_text("Architect review, round 1: approved\n\nReviewed with Claude.\n")
        report = self.report_of(out, 1, "check-text")
        self.assertEqual(report["mode"], "strict")
        self.assertEqual([p["line"] for p in report["problems"]], [3])

    def test_clean_text_passes(self):
        """A comment without attribution passes."""
        report = self.report_of(self.check_text("Developer attempt 1: failed\n\nruff: 2 errors\n"))
        self.assertEqual((report["mode"], report["problems"]), ("strict", []))

    def test_trailers_mode_refuses_only_attribution_lines(self):
        """With ``trailers`` at HEAD, the word passes and a Co-Authored-By trailer does not."""
        self.project.commit("[rules] Use trailers", {CONFIG: config_text(mode="trailers")})
        out = self.check_text("Claude helped.\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
        report = self.report_of(out, 1)
        self.assertEqual(report["mode"], "trailers")
        self.assertEqual([p["line"] for p in report["problems"]], [2])

    def test_mode_is_read_at_head(self):
        """An uncommitted switch to ``trailers`` changes nothing."""
        self.project.write(CONFIG, config_text(mode="trailers"))
        report = self.report_of(self.check_text("Claude helped.\n"), 1)
        self.assertEqual(report["mode"], "strict")

    def test_no_config_means_strict(self):
        """Without a config at HEAD, the mode is strict."""
        self.project.commit("[rules] Remove the config", {CONFIG: None})
        report = self.report_of(self.check_text("Ask Anthropic.\n"), 1)
        self.assertEqual(report["mode"], "strict")
        self.assertEqual([p["line"] for p in report["problems"]], [1])

    def test_unreadable_file_exits_two(self):
        """A missing file or one that is not UTF-8 exits 2."""
        missing = self.project.run("check-text", "--file", str(self.project.tmp / "nope.md"))
        self.assert_exit(missing, 2)
        bad = self.project.tmp / "bad.md"
        bad.write_bytes(b"\xff\xfe bad \xc3\x28\n")
        self.assert_exit(self.project.run("check-text", "--file", str(bad)), 2)

    def test_check_text_never_calls_gh(self):
        """A gh that fails on every call is not called."""
        fakes = Fakes(fail=True)
        self.report_of(self.check_text("Fine.\n", fakes=fakes))
        self.assertEqual(fakes.gh_calls(), [])


if __name__ == "__main__":
    unittest.main()
