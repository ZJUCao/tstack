"""accept-version (F08 design 3.1, 5.7, 6, 8, 11.1; interface note section 5).

Troy's acceptance in the version test plan and its mirror: the acceptance
row, the next major version, the status, and the change-log row, written
byte for byte in both languages.

When the plan or its mirror has no change-log table, ``accept-version``
exits 1 and changes neither file, before it writes the acceptance row
(F07 D201, from tstack issue #46; F08 design 8): ``ChangeLogRefusalTests``.

Planted bugs caught here:

- F08 design 11.2, "the acceptance row written in English only":
  ``AcceptVersionTests.test_accepts_in_both_languages``,
  ``test_patch_adds_a_row_after_the_first``, and ``test_section_without_a_table_gets_one``.
- F07 design 14.2 (D201), "the note with exit 0 kept", "the mirror written
  before the English file's table is checked", and "the check made on the
  English file only": ``ChangeLogRefusalTests.test_each_case_is_refused_and_nothing_is_written``,
  through its English and its mirror cases.
"""

import itertools
import unittest
from datetime import date

from flow_helpers import (
    Fakes, FlowCase, Project, SCRATCH, base_step, crlf, new_dir, parallel, run_engine,
    version_plan_path, version_plan_text,
)

EN = version_plan_path("v0.1")
ZH = version_plan_path("v0.1", "zh-CN")
FEATURES = ["F01", "F02"]
NOTES = "Works on my laptop.\n\nThe phone is slow | sometimes.  \n"
NOTES_CELL = "Works on my laptop. The phone is slow \\| sometimes."
EN_FIRST = "| 0.1 | 2026-11-08 | First draft. |\n"
ZH_FIRST = "| 0.1 | 2026-11-08 | 初稿。 |\n"
EN_NONE_ROW = "| None | None | None |\n"
ZH_NONE_ROW = "| 无 | 无 | 无 |\n"
EN_LOG = "## 6. Change log\n"
ZH_LOG = "## 6. 修改记录\n"
# The two change-log headings a D201 problem names (interface note for #46).
HEADINGS = ("Change log", "修改记录")


def plan_pair(**kwargs) -> dict:
    """The v0.1 plan and its mirror, as TM7 writes them, with the same arguments.

    Args:
        **kwargs: Passed on to ``version_plan_text`` for both languages.

    Returns:
        Paths mapped to text.
    """
    return {EN: version_plan_text("v0.1", FEATURES, "en", **kwargs),
            ZH: version_plan_text("v0.1", FEATURES, "zh-CN", **kwargs)}


def header(text: str, old: str, new: str, old_status: str, new_status: str,
           day: str, old_day: str = "2026-11-08") -> str:
    """The text with the front matter's version, updated, and status lines changed once."""
    for before, after in ((f'version: "{old}"', f'version: "{new}"'),
                          (f'updated: "{old_day}"', f'updated: "{day}"'),
                          (f'status: "{old_status}"', f'status: "{new_status}"')):
        if before not in text:
            raise AssertionError(f"{before!r} is not in the text")
        text = text.replace(before, after, 1)
    return text


def swap(text: str, old: str, new: str) -> str:
    """Replaces a part that occurs exactly once."""
    if text.count(old) != 1:
        raise AssertionError(f"{old!r} occurs {text.count(old)} times")
    return text.replace(old, new)


def without_log_table(text: str, heading: str, line: str) -> str:
    """The plan with its change log's table replaced by one line, its last section.

    Args:
        text: The plan or its mirror.
        heading: The change log's heading line, ``EN_LOG`` or ``ZH_LOG``.
        line: The line under the heading, ``None.`` or ``无。``.

    Returns:
        The text up to the heading, the heading, and the line.
    """
    if text.count(heading) != 1:
        raise AssertionError(f"{heading!r} occurs {text.count(heading)} times")
    return text.split(heading)[0] + heading + f"\n{line}\n"


def accept_in_clone(files: dict) -> tuple:
    """Writes the files into a new clone and runs ``accept-version`` for v0.1.0 there.

    Args:
        files: Paths mapped to text, or None to delete the path.

    Returns:
        ``(outcome, {path: bytes or False before}, {path: bytes or False after})``.
    """
    project = Project([base_step()])
    for rel, text in files.items():
        if text is None:
            project.remove(rel)
        else:
            project.write(rel, text)
    before = {rel: project.exists(rel) and project.read_bytes(rel) for rel in (EN, ZH)}
    notes = project.tmp / "notes.txt"
    notes.write_bytes(b"Fine.\n")
    out = project.run("accept-version", "--tag", "v0.1.0", "--notes-file", str(notes),
                      "--date", "2026-11-09")
    after = {rel: project.exists(rel) and project.read_bytes(rel) for rel in (EN, ZH)}
    return out, before, after


class AcceptVersionTests(FlowCase):
    """Troy's acceptance written into both files (note section 5)."""

    def setUp(self):
        """A fresh clone for each test, since accept-version writes files."""
        self.project = Project([base_step()])

    def write(self, files: dict) -> None:
        """Writes files into the working tree."""
        for rel, text in files.items():
            self.project.write(rel, text)

    def notes_file(self, text) -> str:
        """Writes Troy's notes to a file outside the clone and returns its path."""
        path = self.project.tmp / "notes.txt"
        path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        return str(path)

    def accept(self, tag: str = "v0.1.0", notes=NOTES, *extra: str, fakes=None):
        """Runs ``accept-version --tag <tag> --notes-file <file> --json``."""
        return self.project.run("accept-version", "--tag", tag, "--notes-file",
                                self.notes_file(notes), *extra, fakes=fakes)

    def test_accepts_in_both_languages(self):
        """Planted bug "English only": the row, version 1.0, status, and change log in both."""
        files = plan_pair()
        self.write(files)
        report = self.report_of(self.accept("v0.1.0", NOTES, "--date", "2026-11-09"), 0,
                                "accept-version")
        en = header(files[EN], "0.1", "1.0", "Draft.", "Accepted by Troy on 2026-11-09",
                    "2026-11-09")
        en = swap(en, EN_NONE_ROW, f"| 2026-11-09 | Accepted as v0.1.0 | {NOTES_CELL} |\n")
        en = swap(en, EN_FIRST, EN_FIRST + "| 1.0 | 2026-11-09 | Accepted by Troy as v0.1.0. |\n")
        zh = header(files[ZH], "0.1", "1.0", "草稿。", "Troy 已于 2026-11-09 验收", "2026-11-09")
        zh = swap(zh, ZH_NONE_ROW, f"| 2026-11-09 | 已验收为 v0.1.0 | {NOTES_CELL} |\n")
        zh = swap(zh, ZH_FIRST, ZH_FIRST + "| 1.0 | 2026-11-09 | Troy 验收为 v0.1.0。 |\n")
        self.assertEqual(self.project.read(EN), en)
        self.assertEqual(self.project.read(ZH), zh)
        self.assertEqual((report["tag"], report["plan"], report["mirror"]), ("v0.1.0", EN, ZH))
        self.assertEqual(report["version"], {"from": "0.1", "to": "1.0"})
        self.assertEqual(report["updated"], "2026-11-09")
        self.assertEqual(sorted(report["changed"]), sorted([EN, ZH]))

    def test_patch_adds_a_row_after_the_first(self):
        """v0.1.1 after v0.1.0: the first row stays, a second follows; 1.0 becomes 2.0."""
        rows = [("2026-11-09", "Accepted as v0.1.0", "None")]
        en_text = version_plan_text("v0.1", FEATURES, "en", doc_version="1.0",
                                    status="Accepted by Troy on 2026-11-09",
                                    updated="2026-11-09", acceptance=rows)
        zh_text = version_plan_text("v0.1", FEATURES, "zh-CN", doc_version="1.0",
                                    status="Troy 已于 2026-11-09 验收", updated="2026-11-09",
                                    acceptance=[("2026-11-09", "已验收为 v0.1.0", "无")])
        self.write({EN: en_text, ZH: zh_text})
        report = self.report_of(self.accept("v0.1.1", "", "--date", "2026-11-20"))
        en_row = "| 2026-11-09 | Accepted as v0.1.0 | None |\n"
        zh_row = "| 2026-11-09 | 已验收为 v0.1.0 | 无 |\n"
        en_log = "| 0.1 | 2026-11-09 | First draft. |\n"
        zh_log = "| 0.1 | 2026-11-09 | 初稿。 |\n"
        en = header(en_text, "1.0", "2.0", "Accepted by Troy on 2026-11-09",
                    "Accepted by Troy on 2026-11-20", "2026-11-20", "2026-11-09")
        en = swap(en, en_row, en_row + "| 2026-11-20 | Accepted as v0.1.1 | None |\n")
        en = swap(en, en_log, en_log + "| 2.0 | 2026-11-20 | Accepted by Troy as v0.1.1. |\n")
        zh = header(zh_text, "1.0", "2.0", "Troy 已于 2026-11-09 验收", "Troy 已于 2026-11-20 验收",
                    "2026-11-20", "2026-11-09")
        zh = swap(zh, zh_row, zh_row + "| 2026-11-20 | 已验收为 v0.1.1 | 无 |\n")
        zh = swap(zh, zh_log, zh_log + "| 2.0 | 2026-11-20 | Troy 验收为 v0.1.1。 |\n")
        self.assertEqual(self.project.read(EN), en)
        self.assertEqual(self.project.read(ZH), zh)
        self.assertEqual(report["version"], {"from": "1.0", "to": "2.0"})

    def test_section_without_a_table_gets_one(self):
        """``None.`` and ``无。`` give way to a table with the row, in each language."""
        files = plan_pair(acceptance="line")
        self.write(files)
        self.report_of(self.accept("v0.1.0", "Fine.", "--date", "2026-11-09"))
        en = header(files[EN], "0.1", "1.0", "Draft.", "Accepted by Troy on 2026-11-09",
                    "2026-11-09")
        en = swap(en, "## 5. Acceptance record\n\nNone.\n",
                  "## 5. Acceptance record\n\n| Date | Result | Troy's notes |\n"
                  "| --- | --- | --- |\n| 2026-11-09 | Accepted as v0.1.0 | Fine. |\n")
        en = swap(en, EN_FIRST, EN_FIRST + "| 1.0 | 2026-11-09 | Accepted by Troy as v0.1.0. |\n")
        zh = header(files[ZH], "0.1", "1.0", "草稿。", "Troy 已于 2026-11-09 验收", "2026-11-09")
        zh = swap(zh, "## 5. 验收记录\n\n无。\n",
                  "## 5. 验收记录\n\n| 日期 | 结果 | Troy 的备注 |\n| --- | --- | --- |\n"
                  "| 2026-11-09 | 已验收为 v0.1.0 | Fine. |\n")
        zh = swap(zh, ZH_FIRST, ZH_FIRST + "| 1.0 | 2026-11-09 | Troy 验收为 v0.1.0。 |\n")
        self.assertEqual(self.project.read(EN), en)
        self.assertEqual(self.project.read(ZH), zh)

    def test_dash_rows_are_removed_and_empty_notes_are_none(self):
        """A ``| - | - | - |`` row goes; empty notes are ``None`` and ``无``."""
        files = plan_pair(acceptance=[("-", "-", "-")])
        self.write(files)
        self.report_of(self.accept("v0.1.0", " \n\n", "--date", "2026-11-09"))
        self.assertIn("| 2026-11-09 | Accepted as v0.1.0 | None |\n", self.project.read(EN))
        self.assertIn("| 2026-11-09 | 已验收为 v0.1.0 | 无 |\n", self.project.read(ZH))
        for rel in (EN, ZH):
            with self.subTest(file=rel):
                self.assertNotIn("| - | - | - |", self.project.read(rel))

    def test_crlf_file_stays_crlf(self):
        """A CRLF plan stays CRLF, its new rows included; the LF mirror stays LF."""
        files = plan_pair()
        self.project.write(EN, crlf(files[EN]))
        self.project.write(ZH, files[ZH])
        self.report_of(self.accept("v0.1.0", "Fine.", "--date", "2026-11-09"))
        en = header(files[EN], "0.1", "1.0", "Draft.", "Accepted by Troy on 2026-11-09",
                    "2026-11-09")
        en = swap(en, EN_NONE_ROW, "| 2026-11-09 | Accepted as v0.1.0 | Fine. |\n")
        en = swap(en, EN_FIRST, EN_FIRST + "| 1.0 | 2026-11-09 | Accepted by Troy as v0.1.0. |\n")
        self.assertEqual(self.project.read_bytes(EN), crlf(en))
        self.assertNotIn(b"\r", self.project.read_bytes(ZH))

    def test_date_defaults_to_today(self):
        """Without ``--date``, the row, the header, and the status carry today's date."""
        self.write(plan_pair())
        before = date.today().isoformat()
        report = self.report_of(self.accept("v0.1.0", "Fine."))
        after = date.today().isoformat()
        self.assertIn(report["updated"], {before, after})
        day = report["updated"]
        self.assertIn(f'status: "Accepted by Troy on {day}"', self.project.read(EN))
        self.assertIn(f"| {day} | 已验收为 v0.1.0 | Fine. |", self.project.read(ZH))

    def test_never_calls_gh(self):
        """A gh that fails on every call is never called."""
        self.write(plan_pair())
        fakes = Fakes(fail=True)
        self.report_of(self.accept("v0.1.0", "Fine.", "--date", "2026-11-09", fakes=fakes))
        self.assertEqual(fakes.gh_calls(), [])


class RefusalTests(FlowCase):
    """Exit 1 changes nothing; exit 2 for inputs the engine cannot use (note section 5)."""

    def test_refusals_change_nothing(self):
        """A missing plan or mirror, no header, versions that differ, no acceptance heading."""
        good = plan_pair()
        no_heading = good[EN].replace("## 5. Acceptance record", "## 5. Sign-off")
        cases = {
            "plan missing": {EN: None, ZH: good[ZH]},
            "mirror missing": {EN: good[EN], ZH: None},
            "no header": {EN: "# v0.1 version test plan\n\n## 5. Acceptance record\n\nNone.\n",
                          ZH: good[ZH]},
            "versions differ": {EN: good[EN],
                                ZH: version_plan_text("v0.1", FEATURES, "zh-CN",
                                                      doc_version="0.2")},
            "no acceptance heading": {EN: no_heading, ZH: good[ZH]},
        }
        names = list(cases)
        for name, (out, before, after) in zip(names, parallel(accept_in_clone,
                                                              [cases[n] for n in names])):
            with self.subTest(case=name):
                report = self.report_of(out, 1, "accept-version")
                self.assertNotEqual(report["problems"], [])
                self.assertEqual(after, before)

    def test_bad_inputs_exit_two(self):
        """A bad tag or date, notes that are not UTF-8, and a folder that is no repository."""
        project = Project([base_step()])
        files = plan_pair()
        for rel, text in files.items():
            project.write(rel, text)
        good = project.tmp / "good.txt"
        good.write_bytes(b"Fine.\n")
        bad = project.tmp / "bad.txt"
        bad.write_bytes(b"\xff\xfe not utf-8 \xc3\x28\n")
        day = ["--date", "2026-11-09"]
        cases = {
            "tag without the patch": ["--tag", "v0.1", "--notes-file", str(good), *day],
            "tag without v": ["--tag", "0.1.0", "--notes-file", str(good), *day],
            "tag with a leading zero": ["--tag", "v01.1.0", "--notes-file", str(good), *day],
            "bad date": ["--tag", "v0.1.0", "--notes-file", str(good), "--date", "09/11/2026"],
            "notes not UTF-8": ["--tag", "v0.1.0", "--notes-file", str(bad), *day],
        }
        names = list(cases)
        outs = parallel(lambda n: project.run("accept-version", *cases[n]), names)
        for name, out in zip(names, outs):
            with self.subTest(case=name):
                self.assert_exit(out, 2)
        self.assertEqual({rel: project.read(rel) for rel in (EN, ZH)}, files)
        control = project.run("accept-version", "--tag", "v0.1.0", "--notes-file", str(good),
                              *day)
        self.report_of(control, 0, "accept-version")
        plain = new_dir("plain")
        out = run_engine(["accept-version", "--tag", "v0.1.0", "--notes-file", str(good),
                          "--repo", plain, "--json"], SCRATCH, Fakes(fail=True))
        self.assert_exit(out, 2)


class ChangeLogRefusalTests(FlowCase):
    """D201 (tstack issue #46): the plan or its mirror without a change-log table.

    ``accept-version`` exits 1 with ``ok`` false and one problem per file
    that has no table, naming the file and both headings, and leaves both
    files byte for byte as they were: no acceptance row, no header change,
    and no change-log row, in either language.
    """

    @classmethod
    def setUpClass(cls):
        """Runs every case side by side, each in its own clone.

        Each case maps to the files it writes and the paths that lack the table.
        """
        good = plan_pair()
        en_none = without_log_table(good[EN], EN_LOG, "None.")
        zh_none = without_log_table(good[ZH], ZH_LOG, "无。")
        cls.cases = {
            "control": ({EN: good[EN], ZH: good[ZH]}, []),
            "mirror headed 变更记录": ({EN: good[EN], ZH: swap(good[ZH], ZH_LOG, "## 6. 变更记录\n")},
                                   [ZH]),
            "mirror without a table": ({EN: good[EN], ZH: zh_none}, [ZH]),
            "English without a table": ({EN: en_none, ZH: good[ZH]}, [EN]),
            "English headed Changes": ({EN: swap(good[EN], EN_LOG, "## 6. Changes\n"),
                                        ZH: good[ZH]}, [EN]),
            "neither with a table": ({EN: en_none, ZH: zh_none}, [EN, ZH]),
        }
        names = list(cls.cases)
        cls.results = dict(zip(names, parallel(accept_in_clone,
                                               [cls.cases[n][0] for n in names])))

    def refused(self):
        """The cases that must be refused, as ``(name, lacking paths, outcome, before, after)``."""
        return [(name, lacking, *self.results[name])
                for name, (_, lacking) in self.cases.items() if lacking]

    def test_control_is_accepted(self):
        """The same pair with both change-log tables: exit 0."""
        self.report_of(self.results["control"][0], 0, "accept-version")

    def test_each_case_is_refused_and_nothing_is_written(self):
        """Every case: exit 1, ok false, and both files byte for byte unchanged, so neither
        holds the acceptance row."""
        self.test_control_is_accepted()
        for name, _, out, before, after in self.refused():
            with self.subTest(case=name):
                self.report_of(out, 1, "accept-version")
                self.assertEqual(after, before)
                for rel in (EN, ZH):
                    text = after[rel].decode("utf-8")
                    self.assertNotIn("Accepted as v0.1.0", text, rel)
                    self.assertNotIn("已验收为 v0.1.0", text, rel)

    def test_problems_name_each_file_and_both_headings(self):
        """One problem per file without the table; each holds its path, ``Change log``, and
        ``修改记录``."""
        for name, lacking, out, _, _ in self.refused():
            with self.subTest(case=name):
                problems = self.report_of(out, 1, "accept-version")["problems"]
                self.assertEqual(len(problems), len(lacking), problems)
                for problem in problems:
                    self.assertIsInstance(problem, str, problems)
                    for heading in HEADINGS:
                        self.assertIn(heading, problem, problems)
                self.assertTrue(any(all(path in problem for path, problem in zip(lacking, order))
                                    for order in itertools.permutations(problems)),
                                f"no problem per path {lacking}: {problems}")


if __name__ == "__main__":
    unittest.main()
