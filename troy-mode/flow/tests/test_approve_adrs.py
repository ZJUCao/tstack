"""approve accepts the architecture's ADRs (F07 design 3.1, 8.6, 14.1, and 16, D202).

From tstack issue #47: in the F11 pilot, approving the architecture changed
only its header and change log. Its decision records table and the Status
section of each ADR, in both languages, still said "Proposed", and AR1 ran a
second time only to change the words. Since D202, ``approve`` of the
architecture (``--doc`` naming either file of the pair) also accepts every
ADR that a decision records table of the pair lists and that is still
proposed in either of its files. Each of the ADR's two files gets the
approved header, with no change-log row, and each file that is proposed gets
the Status line "Accepted. Troy accepted it on <date> by approving
`docs/architecture.md`." or its Chinese form, keeping any text after the
word. The row's Status cell in each architecture file becomes ``Accepted``
or ``已接受``. ADRs already accepted or superseded, and ADRs the table does
not list, stay byte for byte. A listed ADR without both files, with a file
that has no header, or whose files' versions differ refuses the approval:
exit 1, one problem naming the ADR, and nothing written.

Every case compares every file under ``docs/`` with the text expected, built
from the input by exact replacements, so a stray change anywhere fails. A
replacement that does not apply to the input raises ``ValueError``, so a bad
fixture shows as an error, never as a failure of the engine.

Planted bugs of F07 design 14.2 (D202) caught here:

- "an accepted ADR left proposed in its mirror":
  ``AcceptTests.test_pilot_three_proposed_adrs_are_accepted``,
  ``test_approve_from_the_mirror``, ``StatusLineTests.test_proposed_only_in_the_mirror``,
  and ``test_every_proposed_word_in_any_case``.
- "its header left as it was": ``AcceptTests.test_pilot_three_proposed_adrs_are_accepted``,
  ``StatusLineTests.test_proposed_only_in_the_mirror`` (the header of a file whose
  Status line is already accepted is raised too), and ``test_text_after_the_word_is_kept``
  (1.2 becomes 2.0).
- "an ADR that is already accepted raised again":
  ``LeftAloneTests.test_already_accepted_adr_is_left_alone``,
  ``test_superseded_adr_is_left_alone``, and ``test_nothing_proposed_gives_no_adrs``.
- "the architecture's table cell left as it was":
  ``AcceptTests.test_pilot_three_proposed_adrs_are_accepted`` and every test of
  ``TableTests``.
- "an ADR the architecture does not list accepted":
  ``LeftAloneTests.test_adr_not_listed_is_left_alone``, ``test_none_row_lists_nothing``,
  ``test_requirements_approval_leaves_adrs_alone``, and
  ``TableTests.test_fenced_example_table_is_not_the_decision_records``.
- "a refused ADR that still lets the architecture be written": every test of
  ``RefusalTests``.
- "any document accepts ADRs", which survived the first pass:
  ``LeftAloneTests.test_feature_design_with_decision_records_leaves_adrs_alone``.
"""

import json
import unittest

from flow_helpers import FlowCase, Project, base_step, crlf, front_matter

DAY = "2026-11-18"
# front_matter's default ``updated``, the day every input file was last changed.
OLD_DAY = "2026-11-01"
LANGS = ("en", "zh-CN")
ARCH = "docs/architecture.md"
ARCH_ZH = "docs/architecture.zh-CN.md"
REQ = "docs/requirements.md"
REQ_ZH = "docs/requirements.zh-CN.md"
EN_LINE = f"Accepted. Troy accepted it on {DAY} by approving `docs/architecture.md`."
ZH_LINE = f"已接受。Troy 于 {DAY} 批准 `docs/architecture.md`，接受了这条记录。"
EN_DRAFT = "Draft. Waiting for Troy's approval."
ZH_DRAFT = "草稿，等待 Troy 批准。"
EN_LOG = "| 0.1 | 2026-11-01 | First draft. |\n"
ZH_LOG = "| 0.1 | 2026-11-01 | 初稿。 |\n"
REQ_LOG = "| 1.2 | 2026-11-05 | Fixed a typo. |\n"
REQ_LOG_ZH = "| 1.2 | 2026-11-05 | 修正笔误。 |\n"
EN_HEAD = "| ADR | Title | Status |\n| --- | --- | --- |\n"
ZH_HEAD = "| ADR | 标题 | 状态 |\n| --- | --- | --- |\n"
# ADR ID mapped to its slug, its English title, and its Chinese title.
ADRS = {
    "ADR-0001": ("toml", "Use TOML for the config", "配置用 TOML"),
    "ADR-0002": ("one-cli", "One command-line entry point", "只有一个命令行入口"),
    "ADR-0003": ("utf8", "Read every file as UTF-8", "所有文件按 UTF-8 读取"),
    "ADR-0004": ("cache", "Cache the counts per file", "按文件缓存计数"),
    "ADR-0009": ("tomli-w", "Write TOML with tomli-w", "用 tomli-w 写 TOML"),
}


def swap(text: str, old: str, new: str) -> str:
    """Replaces a part that occurs exactly once.

    Args:
        text: The text.
        old: The part to replace.
        new: Its replacement.

    Returns:
        The new text.

    Raises:
        ValueError: ``old`` does not occur exactly once (a bad fixture).
    """
    if text.count(old) != 1:
        raise ValueError(f"{old!r} occurs {text.count(old)} times")
    return text.replace(old, new)


def adr_path(adr_id: str, lang: str = "en") -> str:
    """An ADR file's path: ``docs/adr/<ID>-<slug>.md`` or its ``.zh-CN.md`` mirror."""
    suffix = ".md" if lang == "en" else ".zh-CN.md"
    return f"docs/adr/{adr_id}-{ADRS[adr_id][0]}{suffix}"


def adr_paths(*ids: str) -> list:
    """The ADRs' files in the report's order: each ID's English file, then its mirror."""
    return [adr_path(adr_id, lang) for adr_id in ids for lang in LANGS]


def adr_text(adr_id: str, lang: str = "en", line=None, version: str = "0.1", status=None,
             before: str = "", heading=None) -> str:
    """An ADR file in the shape of F01's ``adr`` template.

    Its Context section starts with a line that begins with the proposed
    word (``Proposed choices`` or ``提议中的格式``), which no approval may change.

    Args:
        adr_id: The ADR's ID, a key of ``ADRS``.
        lang: ``en`` or ``zh-CN``.
        line: The Status line, or None for ``Proposed.`` (``提议中。``).
        version: The front matter's version.
        status: The front matter's status, or None for the template's
            ``Proposed.`` (``提议中。``).
        before: Text between the Status heading's blank line and the Status line.
        heading: The Status heading, or None for ``## 1. Status`` (``## 1. 状态``).

    Returns:
        The file's text.
    """
    slug, title, title_zh = ADRS[adr_id]
    english = lang == "en"
    proposed = "Proposed." if english else "提议中。"
    mirror = f"{adr_id}-{slug}.zh-CN.md" if english else f"{adr_id}-{slug}.md"
    head = front_matter(adr_id, lang, version, mirror, status or proposed)
    line = proposed if line is None else line
    if english:
        return head + (f"# {adr_id}: {title}\n\n{heading or '## 1. Status'}\n\n{before}{line}\n\n"
                       "## 2. Context\n\nProposed choices were TOML, JSON, and INI.\n\n"
                       "## 3. Decision\n\nWe do what the title says.\n\n"
                       "## 4. Options considered\n\n| Option | Pros | Cons |\n| --- | --- | --- |\n"
                       "| TOML | The standard library reads it. | No writer. |\n\n"
                       "## 5. Consequences\n\nNone.\n\n"
                       "## 6. Related\n\n- Features: F01\n- Rules: None\n")
    return head + (f"# {adr_id}：{title_zh}\n\n{heading or '## 1. 状态'}\n\n{before}{line}\n\n"
                   "## 2. 背景\n\n提议中的格式有 TOML、JSON 和 INI。\n\n"
                   "## 3. 决定\n\n照标题做。\n\n"
                   "## 4. 考虑过的方案\n\n| 方案 | 优点 | 缺点 |\n"
                   "| --- | --- | --- |\n| TOML | 标准库能读。 | 不能写。 |\n\n"
                   "## 5. 影响\n\n无。\n\n"
                   "## 6. 相关\n\n- 功能：F01\n- 规则：无\n")


def accepted_adr(adr_id: str, lang: str = "en") -> str:
    """An ADR file that Troy accepted earlier: ``Accepted.`` (``已接受。``) at version 1.0."""
    english = lang == "en"
    return adr_text(adr_id, lang, "Accepted." if english else "已接受。", "1.0",
                    "Approved by Troy on 2026-11-05" if english else "Troy 已于 2026-11-05 批准")


def raised(text: str, lang: str, old: str = "0.1", new: str = "1.0", status=None) -> str:
    """The text with its front matter's version, updated, and status as ``approve`` sets them.

    Args:
        text: The file's text.
        lang: ``en`` or ``zh-CN``.
        old: The version before.
        new: The next major version.
        status: The status before, or None for ``Proposed.`` (``提议中。``).

    Returns:
        The new text.
    """
    english = lang == "en"
    if status is None:
        status = "Proposed." if english else "提议中。"
    approved = f"Approved by Troy on {DAY}" if english else f"Troy 已于 {DAY} 批准"
    text = swap(text, f'version: "{old}"', f'version: "{new}"')
    text = swap(text, f'updated: "{OLD_DAY}"', f'updated: "{DAY}"')
    return swap(text, f'status: "{status}"', f'status: "{approved}"')


def accept(text: str, lang: str, line=None, rest: str = "", old: str = "0.1",
           new: str = "1.0") -> str:
    """A proposed ADR file as ``approve`` leaves it: header raised and Status line accepted.

    Args:
        text: The file's text.
        lang: ``en`` or ``zh-CN``.
        line: The old Status line, or None for ``Proposed.`` (``提议中。``).
        rest: The text that follows the accepted line after one space, or empty.
        old: The version before.
        new: The next major version.

    Returns:
        The new text.
    """
    english = lang == "en"
    line = line if line is not None else ("Proposed." if english else "提议中。")
    accepted = (EN_LINE if english else ZH_LINE) + (f" {rest}" if rest else "")
    return swap(raised(text, lang, old, new), f"\n{line}\n", f"\n{accepted}\n")


def row(adr_id: str, cell: str, lang: str = "en") -> str:
    """One row of the decision records table: the ID, the title, and the Status cell."""
    return f"| {adr_id} | {ADRS[adr_id][1 if lang == 'en' else 2]} | {cell} |\n"


def table(lang: str, *rows: str) -> str:
    """The decision records table with the template's header and the rows."""
    return (EN_HEAD if lang == "en" else ZH_HEAD) + "".join(rows)


def arch_text(lang: str, records: str, heading=None, extra: str = "",
              approved_in: str = "ADR-0001") -> str:
    """The architecture or its mirror at 0.1, in the shape of F01's template.

    Section 5 starts a line with the proposed word, and section 9's table
    names an ADR in its last column; neither lists an ADR.

    Args:
        lang: ``en`` or ``zh-CN``.
        records: The decision records table, ending with a newline.
        heading: The decision records heading, or None for ``## 11. Decision records``
            (``## 11. 决策记录``).
        extra: Text at the end of section 1, ending with a blank line.
        approved_in: The ADR that section 9's table names.

    Returns:
        The document text.
    """
    english = lang == "en"
    mirror = "architecture.zh-CN.md" if english else "architecture.md"
    head = front_matter("architecture", lang, "0.1", mirror, EN_DRAFT if english else ZH_DRAFT)
    if english:
        return head + ("# wordcount architecture\n\n## 1. Context and constraints\n\n"
                       "- Runs on Windows and Linux.\n\n" + extra
                       + "## 5. Data model\n\nProposed changes to the data model need an ADR.\n\n"
                       "## 9. Third-party dependencies\n\n"
                       "| Name | Version | License | Why | Approved in |\n"
                       "| --- | --- | --- | --- | --- |\n"
                       f"| tomli | 2.0.1 | MIT | Reads TOML. | {approved_in} |\n\n"
                       f"{heading or '## 11. Decision records'}\n\n"
                       "Each record is a file under `docs/adr/`.\n\n" + records
                       + "\n## 12. Change log\n\n| Version | Date | Change |\n| --- | --- | --- |\n"
                       + EN_LOG)
    return head + ("# wordcount 总体架构\n\n## 1. 背景和约束\n\n- 在 Windows 和 Linux 上运行。\n\n"
                   + extra + "## 5. 数据模型\n\n提议中的数据模型改动需要一条 ADR。\n\n"
                   "## 9. 第三方依赖\n\n| 名称 | 版本 | 许可证 | 理由 | 批准记录 |\n"
                   "| --- | --- | --- | --- | --- |\n"
                   f"| tomli | 2.0.1 | MIT | 读 TOML。 | {approved_in} |\n\n"
                   f"{heading or '## 11. 决策记录'}\n\n每条记录是 `docs/adr/` 下的一个文件。\n\n"
                   + records
                   + "\n## 12. 修改记录\n\n| 版本 | 日期 | 修改 |\n| --- | --- | --- |\n" + ZH_LOG)


def approved_arch(text: str, lang: str, cells=()) -> str:
    """An architecture file as ``approve`` leaves it.

    Args:
        text: The file's text.
        lang: ``en`` or ``zh-CN``.
        cells: ``(old row, new row)`` pairs of the decision records table.

    Returns:
        The text with the header raised to 1.0, the change-log row "Approved by
        Troy." (``Troy 批准。``) after the last row, and the rows replaced.
    """
    english = lang == "en"
    text = raised(text, lang, status=EN_DRAFT if english else ZH_DRAFT)
    log, row_text = ((EN_LOG, f"| 1.0 | {DAY} | Approved by Troy. |\n") if english
                     else (ZH_LOG, f"| 1.0 | {DAY} | Troy 批准。 |\n"))
    text = swap(text, log, log + row_text)
    for old, new in cells:
        text = swap(text, old, new)
    return text


def cell_change(adr_id: str, lang: str = "en") -> tuple:
    """A template row's change from ``Proposed`` (``提议中``) to ``Accepted`` (``已接受``)."""
    if lang == "en":
        return row(adr_id, "Proposed"), row(adr_id, "Accepted")
    return row(adr_id, "提议中", lang), row(adr_id, "已接受", lang)


def proposed_pair(*ids: str) -> dict:
    """The architecture pair whose decision records list the ADRs, in this order, as proposed."""
    return {ARCH: arch_text("en", table("en", *(row(i, "Proposed") for i in ids))),
            ARCH_ZH: arch_text("zh-CN", table("zh-CN", *(row(i, "提议中", "zh-CN") for i in ids)))}


def approved_pair(files: dict, *ids: str) -> dict:
    """The architecture pair approved, with the template rows of the IDs accepted."""
    return {ARCH: approved_arch(files[ARCH], "en", [cell_change(i) for i in ids]),
            ARCH_ZH: approved_arch(files[ARCH_ZH], "zh-CN", [cell_change(i, "zh-CN") for i in ids])}


def proposed_adrs(*ids: str) -> dict:
    """Both files of each ADR, proposed at 0.1."""
    return {adr_path(i, lang): adr_text(i, lang) for i in ids for lang in LANGS}


def accepted_adrs(files: dict, *ids: str) -> dict:
    """Both files of each proposed ADR as ``approve`` leaves them."""
    return {adr_path(i, lang): accept(files[adr_path(i, lang)], lang)
            for i in ids for lang in LANGS}


def requirements(lang: str) -> str:
    """The requirements or their mirror at 1.2, with a change log (D201)."""
    if lang == "en":
        return (front_matter("requirements", "en", "1.2", "requirements.zh-CN.md")
                + "# wordcount requirements\n\n## 1. Goal\n\nCount words.\n\n"
                "## 14. Change log\n\n| Version | Date | Change |\n| --- | --- | --- |\n" + REQ_LOG)
    return (front_matter("requirements", "zh-CN", "1.2", "requirements.md")
            + "# wordcount 需求\n\n## 1. 目标\n\n统计单词。\n\n"
            "## 14. 修改记录\n\n| 版本 | 日期 | 修改 |\n| --- | --- | --- |\n" + REQ_LOG_ZH)


def approved_requirements(text: str, lang: str) -> str:
    """The requirements raised to 2.0, with their change-log row (F08 D77)."""
    english = lang == "en"
    text = raised(text, lang, "1.2", "2.0", "Draft. In review." if english else "草稿，审查中。")
    log, change = (REQ_LOG, "Approved by Troy.") if english else (REQ_LOG_ZH, "Troy 批准。")
    return swap(text, log, log + f"| 2.0 | {DAY} | {change} |\n")


def problem_text(problem) -> str:
    """A problem as text: a string as it is, anything else as JSON."""
    return problem if isinstance(problem, str) else json.dumps(problem, ensure_ascii=False)


class AdrCase(FlowCase):
    """A clone in which ``approve`` runs on the architecture pair and its ADRs."""

    def setUp(self):
        """A fresh clone for each test, since approve writes files."""
        self.project = Project([base_step()])

    def put(self, files: dict, crlf_paths=()) -> None:
        """Writes files into the working tree.

        Args:
            files: Paths mapped to LF text, or None to delete the file.
            crlf_paths: The paths written with CRLF line endings.
        """
        for rel, text in files.items():
            if text is None:
                self.project.remove(rel)
            else:
                self.project.write(rel, crlf(text) if rel in crlf_paths else text)

    def tree(self) -> dict:
        """Every file under ``docs/``, as its path mapped to its bytes."""
        root = self.project.root
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted((root / "docs").rglob("*")) if path.is_file()}

    def approve(self, doc: str = ARCH):
        """Runs ``approve --doc <doc> --date <DAY> --json`` on the clone."""
        return self.project.run("approve", "--doc", doc, "--date", DAY)

    def assert_tree(self, expected: dict) -> None:
        """Asserts that the files under ``docs/`` are exactly the expected ones, byte for byte.

        Args:
            expected: Paths mapped to bytes.
        """
        after = self.tree()
        self.assertEqual(sorted(after), sorted(expected), "the files under docs/")
        for rel in sorted(expected):
            self.assertEqual(after[rel].decode("utf-8"), expected[rel].decode("utf-8"), rel)

    def accepted_run(self, files: dict, changes: dict, crlf_paths=(), doc: str = ARCH) -> dict:
        """Writes the files, runs ``approve``, and asserts exit 0 and every file under ``docs/``.

        Args:
            files: Paths mapped to LF text, or None to delete the file.
            changes: The paths approve changes, mapped to their expected LF text.
                Every other file must stay byte for byte as it was.
            crlf_paths: The paths written, and expected, with CRLF line endings.
            doc: The ``--doc`` path.

        Returns:
            The report.
        """
        self.put(files, crlf_paths)
        before = self.tree()
        report = self.report_of(self.approve(doc), 0, "approve")
        expected = dict(before)
        for rel, text in changes.items():
            expected[rel] = crlf(text) if rel in crlf_paths else text.encode("utf-8")
        self.assert_tree(expected)
        return report

    def assert_report(self, report: dict, *ids: str) -> None:
        """Asserts ``changed`` and ``adrs`` for an architecture approval.

        ``changed`` holds the architecture pair first, in either order, then
        each accepted ADR's English file and mirror, in ID order; ``adrs``
        holds the accepted IDs in ID order.

        Args:
            report: The report.
            *ids: The accepted IDs, in ID order.
        """
        changed = report.get("changed")
        self.assertIsInstance(changed, list, report)
        self.assertEqual(sorted(changed[:2]), [ARCH, ARCH_ZH], changed)
        self.assertEqual(changed[2:], adr_paths(*ids), changed)
        self.assertEqual(report.get("adrs"), list(ids), report)


class AcceptTests(AdrCase):
    """The pilot's case: every listed ADR proposed, and each accepted in both languages."""

    def test_pilot_three_proposed_adrs_are_accepted(self):
        """Planted bugs "left proposed in its mirror", "its header left as it was", and "the
        table cell left as it was": three ADRs listed and proposed. Each ADR file gets 1.0,
        the date, the approved status, and its new Status line; each row's cell becomes
        Accepted (已接受); the architecture gets its header and change-log row as before."""
        ids = ("ADR-0001", "ADR-0002", "ADR-0003")
        files = {**proposed_pair(*ids), **proposed_adrs(*ids)}
        changes = {**approved_pair(files, *ids), **accepted_adrs(files, *ids)}
        report = self.accepted_run(files, changes)
        self.assert_report(report, *ids)
        self.assertEqual(report.get("version"), {"from": "0.1", "to": "1.0"})
        self.assertEqual(sorted(report.get("change_log") or []), [ARCH, ARCH_ZH])

    def test_approve_from_the_mirror(self):
        """Planted bug "left proposed in its mirror": ``--doc docs/architecture.zh-CN.md``
        gives the same files and the same report."""
        ids = ("ADR-0001", "ADR-0002", "ADR-0003")
        files = {**proposed_pair(*ids), **proposed_adrs(*ids)}
        changes = {**approved_pair(files, *ids), **accepted_adrs(files, *ids)}
        report = self.accepted_run(files, changes, doc=ARCH_ZH)
        self.assert_report(report, *ids)

    def test_report_lists_adrs_in_id_order(self):
        """Rows in the order 0003, 0001, 0002: ``adrs`` and ``changed`` follow the IDs."""
        files = {**proposed_pair("ADR-0003", "ADR-0001", "ADR-0002"),
                 **proposed_adrs("ADR-0001", "ADR-0002", "ADR-0003")}
        ids = ("ADR-0001", "ADR-0002", "ADR-0003")
        changes = {**approved_pair(files, *ids), **accepted_adrs(files, *ids)}
        self.assert_report(self.accepted_run(files, changes), *ids)

    def test_crlf_files_keep_crlf(self):
        """The English architecture and both files of ADR-0001 are CRLF, the rest LF: each file
        keeps its line endings, the changed lines included."""
        ids = ("ADR-0001", "ADR-0002")
        files = {**proposed_pair(*ids), **proposed_adrs(*ids)}
        changes = {**approved_pair(files, *ids), **accepted_adrs(files, *ids)}
        crlf_paths = {ARCH, adr_path("ADR-0001"), adr_path("ADR-0001", "zh-CN")}
        report = self.accepted_run(files, changes, crlf_paths)
        self.assert_report(report, *ids)


class LeftAloneTests(AdrCase):
    """ADRs that are not proposed, or not listed, stay byte for byte (D202)."""

    def test_already_accepted_adr_is_left_alone(self):
        """Planted bug "already accepted raised again": ADR-0001, accepted at 1.0 in both
        files, and its Accepted (已接受) cells stay; ADR-0002 in the same table is accepted."""
        files = {ARCH: arch_text("en", table("en", row("ADR-0001", "Accepted"),
                                             row("ADR-0002", "Proposed"))),
                 ARCH_ZH: arch_text("zh-CN", table("zh-CN", row("ADR-0001", "已接受", "zh-CN"),
                                                   row("ADR-0002", "提议中", "zh-CN"))),
                 **{adr_path("ADR-0001", lang): accepted_adr("ADR-0001", lang) for lang in LANGS},
                 **proposed_adrs("ADR-0002")}
        changes = {**approved_pair(files, "ADR-0002"), **accepted_adrs(files, "ADR-0002")}
        self.assert_report(self.accepted_run(files, changes), "ADR-0002")

    def test_superseded_adr_is_left_alone(self):
        """Planted bug "already accepted raised again": ADR-0001, superseded by ADR-0002, and
        its cells stay; ADR-0002, proposed, is accepted."""
        superseded = {
            adr_path("ADR-0001"): adr_text("ADR-0001", "en", "Superseded by ADR-0002.", "1.0",
                                           "Approved by Troy on 2026-11-05"),
            adr_path("ADR-0001", "zh-CN"): adr_text("ADR-0001", "zh-CN", "已被 ADR-0002 取代。",
                                                    "1.0", "Troy 已于 2026-11-05 批准"),
        }
        files = {ARCH: arch_text("en", table("en", row("ADR-0001", "Superseded by ADR-0002"),
                                             row("ADR-0002", "Proposed"))),
                 ARCH_ZH: arch_text("zh-CN", table(
                     "zh-CN", row("ADR-0001", "已被 ADR-0002 取代", "zh-CN"),
                     row("ADR-0002", "提议中", "zh-CN"))),
                 **superseded, **proposed_adrs("ADR-0002")}
        changes = {**approved_pair(files, "ADR-0002"), **accepted_adrs(files, "ADR-0002")}
        self.assert_report(self.accepted_run(files, changes), "ADR-0002")

    def test_adr_not_listed_is_left_alone(self):
        """Planted bug "an ADR the architecture does not list accepted": ADR-0009, proposed
        under ``docs/adr/`` and named in section 1 and in section 9's table but not in the
        decision records, stays byte for byte; the listed ADR-0001 is accepted."""
        files = {ARCH: arch_text("en", table("en", row("ADR-0001", "Proposed")),
                                 extra="ADR-0009 is still a draft for a later feature.\n\n",
                                 approved_in="ADR-0009"),
                 ARCH_ZH: arch_text("zh-CN", table("zh-CN", row("ADR-0001", "提议中", "zh-CN")),
                                    extra="ADR-0009 仍是后续功能的草稿。\n\n",
                                    approved_in="ADR-0009"),
                 **proposed_adrs("ADR-0001", "ADR-0009")}
        changes = {**approved_pair(files, "ADR-0001"), **accepted_adrs(files, "ADR-0001")}
        self.assert_report(self.accepted_run(files, changes), "ADR-0001")

    def test_nothing_proposed_gives_no_adrs(self):
        """Planted bug "already accepted raised again": every listed ADR accepted, so only the
        architecture pair changes; ``changed`` holds the pair alone and ``adrs`` is []."""
        ids = ("ADR-0001", "ADR-0002")
        files = {ARCH: arch_text("en", table("en", *(row(i, "Accepted") for i in ids))),
                 ARCH_ZH: arch_text("zh-CN", table("zh-CN",
                                                   *(row(i, "已接受", "zh-CN") for i in ids))),
                 **{adr_path(i, lang): accepted_adr(i, lang) for i in ids for lang in LANGS}}
        changes = approved_pair(files)
        report = self.accepted_run(files, changes)
        self.assert_report(report)
        self.assertEqual(len(report.get("changed") or []), 2, report)

    def test_none_row_lists_nothing(self):
        """Planted bug "an ADR the architecture does not list accepted": a table whose only
        row is None (无) lists nothing, so the proposed ADR-0001, named in section 9 only,
        stays byte for byte, and ``adrs`` is []."""
        files = {ARCH: arch_text("en", EN_HEAD + "| None | None | None |\n"),
                 ARCH_ZH: arch_text("zh-CN", ZH_HEAD + "| 无 | 无 | 无 |\n"),
                 **proposed_adrs("ADR-0001")}
        self.assert_report(self.accepted_run(files, approved_pair(files)))

    def approve_requirements(self) -> dict:
        """Approves the requirements while the architecture lists two proposed ADRs.

        Asserts exit 0, the requirements pair raised to 2.0 with its rows,
        every other file under ``docs/`` byte for byte, and ``changed`` holding
        the requirements pair only.

        Returns:
            The report.
        """
        ids = ("ADR-0001", "ADR-0002")
        files = {**proposed_pair(*ids), **proposed_adrs(*ids),
                 REQ: requirements("en"), REQ_ZH: requirements("zh-CN")}
        changes = {REQ: approved_requirements(files[REQ], "en"),
                   REQ_ZH: approved_requirements(files[REQ_ZH], "zh-CN")}
        report = self.accepted_run(files, changes, doc=REQ)
        self.assertEqual(sorted(report.get("changed") or []), [REQ, REQ_ZH], report)
        return report

    def test_requirements_approval_leaves_adrs_alone(self):
        """Control, and planted bug "an ADR the architecture does not list accepted": approving
        the requirements changes them as before and no architecture or ADR file."""
        self.approve_requirements()

    def test_other_document_reports_no_adrs(self):
        """For a document that is not the architecture, ``adrs`` is []."""
        self.assertEqual(self.approve_requirements().get("adrs"), [])

    def test_feature_design_with_decision_records_leaves_adrs_alone(self):
        """Planted bug "any document accepts ADRs" (a survivor of the first pass): a feature
        design whose own decision records table lists a proposed ADR, as the pilot's F05
        design proposed ADR-0008, is approved as before, and the ADR stays byte for byte."""
        design, design_zh = "docs/features/F05/design.md", "docs/features/F05/design.zh-CN.md"
        log = "## 12. Change log\n\n| Version | Date | Change |\n| --- | --- | --- |\n" + EN_LOG
        log_zh = "## 12. 修改记录\n\n| 版本 | 日期 | 修改 |\n| --- | --- | --- |\n" + ZH_LOG
        files = {
            design: (front_matter("F05-design", "en", "0.1", "design.zh-CN.md")
                     + "# F05 design\n\n## 9. Decision records\n\n"
                     + table("en", row("ADR-0004", "Proposed")) + "\n" + log),
            design_zh: (front_matter("F05-design", "zh-CN", "0.1", "design.md")
                        + "# F05 设计\n\n## 9. 决策记录\n\n"
                        + table("zh-CN", row("ADR-0004", "提议中", "zh-CN")) + "\n" + log_zh),
            **proposed_adrs("ADR-0004"),
        }
        changes = {}
        for rel, lang, old_log, change in ((design, "en", EN_LOG, "Approved by Troy."),
                                           (design_zh, "zh-CN", ZH_LOG, "Troy 批准。")):
            draft = "Draft. In review." if lang == "en" else "草稿，审查中。"
            changes[rel] = swap(raised(files[rel], lang, status=draft), old_log,
                                old_log + f"| 1.0 | {DAY} | {change} |\n")
        report = self.accepted_run(files, changes, doc=design)
        self.assertEqual(sorted(report.get("changed") or []), sorted([design, design_zh]))
        self.assertEqual(report.get("adrs"), [], report)


class StatusLineTests(AdrCase):
    """The Status line of each proposed ADR file, and only of a proposed one (D202)."""

    def test_proposed_only_in_the_mirror(self):
        """Planted bugs "left proposed in its mirror" and "its header left as it was":
        ADR-0001 says Accepted. in English and 提议中。 in its mirror, ADR-0002 the other way
        round. Both are accepted: both headers raised, the proposed file's line changed, the
        other file's line kept, and only the cells that start with a proposed word changed."""
        files = {ARCH: arch_text("en", table("en", row("ADR-0001", "Accepted"),
                                             row("ADR-0002", "Proposed"))),
                 ARCH_ZH: arch_text("zh-CN", table("zh-CN", row("ADR-0001", "提议中", "zh-CN"),
                                                   row("ADR-0002", "已接受", "zh-CN"))),
                 adr_path("ADR-0001"): adr_text("ADR-0001", "en", "Accepted."),
                 adr_path("ADR-0001", "zh-CN"): adr_text("ADR-0001", "zh-CN"),
                 adr_path("ADR-0002"): adr_text("ADR-0002", "en"),
                 adr_path("ADR-0002", "zh-CN"): adr_text("ADR-0002", "zh-CN", "已接受。")}
        changes = {
            ARCH: approved_arch(files[ARCH], "en", [cell_change("ADR-0002")]),
            ARCH_ZH: approved_arch(files[ARCH_ZH], "zh-CN", [cell_change("ADR-0001", "zh-CN")]),
            adr_path("ADR-0001"): raised(files[adr_path("ADR-0001")], "en"),
            adr_path("ADR-0001", "zh-CN"): accept(files[adr_path("ADR-0001", "zh-CN")], "zh-CN"),
            adr_path("ADR-0002"): accept(files[adr_path("ADR-0002")], "en"),
            adr_path("ADR-0002", "zh-CN"): raised(files[adr_path("ADR-0002", "zh-CN")], "zh-CN"),
        }
        self.assert_report(self.accepted_run(files, changes), "ADR-0001", "ADR-0002")

    def test_text_after_the_word_is_kept(self):
        """Planted bug "its header left as it was" (1.2 becomes 2.0): "Proposed. Supersedes
        ADR-0002." and "提议中，取代 ADR-0002。" keep the text after the word and its
        punctuation, after one space; so do "Proposed: ..." and "提议中：..."."""
        lines = {"ADR-0001": (("Proposed: until the pilot ends.", "until the pilot ends."),
                              ("提议中：试点结束前有效。", "试点结束前有效。")),
                 "ADR-0003": (("Proposed. Supersedes ADR-0002.", "Supersedes ADR-0002."),
                              ("提议中，取代 ADR-0002。", "取代 ADR-0002。"))}
        versions = {"ADR-0001": ("0.1", "1.0"), "ADR-0003": ("1.2", "2.0")}
        files = proposed_pair("ADR-0001", "ADR-0003")
        changes = approved_pair(files, "ADR-0001", "ADR-0003")
        for adr_id, by_lang in lines.items():
            old, new = versions[adr_id]
            for lang, (line, rest) in zip(LANGS, by_lang):
                text = adr_text(adr_id, lang, line, old)
                files[adr_path(adr_id, lang)] = text
                changes[adr_path(adr_id, lang)] = accept(text, lang, line, rest, old, new)
        self.assert_report(self.accepted_run(files, changes), "ADR-0001", "ADR-0003")

    def test_comment_and_blank_line_before_the_status_line(self):
        """``## Status`` (``### 1. 状态``), a blank line, an HTML comment that holds the word,
        and a blank line before the status line: the comment stays, the line changes."""
        befores = {"en": "<!-- Proposed until Troy approves the architecture. -->\n\n",
                   "zh-CN": "<!-- 提议中，直到 Troy 批准总体架构。 -->\n\n"}
        headings = {"en": "## Status", "zh-CN": "### 1. 状态"}
        files = proposed_pair("ADR-0001")
        changes = approved_pair(files, "ADR-0001")
        for lang in LANGS:
            text = adr_text("ADR-0001", lang, before=befores[lang], heading=headings[lang])
            files[adr_path("ADR-0001", lang)] = text
            changes[adr_path("ADR-0001", lang)] = accept(text, lang)
        self.assert_report(self.accepted_run(files, changes), "ADR-0001")

    def test_every_proposed_word_in_any_case(self):
        """Planted bug "left proposed in its mirror": English ``proposed``, ``PROPOSED.``, and
        ``Proposed.``; Chinese ``已提议。``, ``提议``, ``Proposed.``, and ``PROPOSED`` are all
        proposed, and so are the Chinese cells 已提议, 提议, Proposed, and 提议中."""
        words = {"ADR-0001": ("proposed", "已提议。", "已提议"),
                 "ADR-0002": ("PROPOSED.", "提议", "提议"),
                 "ADR-0003": ("Proposed.", "Proposed.", "Proposed"),
                 "ADR-0004": ("Proposed.", "PROPOSED", "提议中")}
        ids = tuple(words)
        zh_rows = [row(i, cell, "zh-CN") for i, (_, _, cell) in words.items()]
        files = {ARCH: arch_text("en", table("en", *(row(i, "Proposed") for i in ids))),
                 ARCH_ZH: arch_text("zh-CN", table("zh-CN", *zh_rows))}
        changes = {ARCH: approved_arch(files[ARCH], "en", [cell_change(i) for i in ids]),
                   ARCH_ZH: approved_arch(files[ARCH_ZH], "zh-CN",
                                          [(old, row(i, "已接受", "zh-CN"))
                                           for i, old in zip(ids, zh_rows)])}
        for adr_id, (en_line, zh_line, _) in words.items():
            for lang, line in zip(LANGS, (en_line, zh_line)):
                text = adr_text(adr_id, lang, line)
                files[adr_path(adr_id, lang)] = text
                changes[adr_path(adr_id, lang)] = accept(text, lang, line)
        self.assert_report(self.accepted_run(files, changes), *ids)


class TableTests(AdrCase):
    """The decision records tables: which rows list an ADR, and which cell changes (D202)."""

    def test_link_in_the_first_cell_and_other_spacing(self):
        """Planted bug "the table cell left as it was": rows whose first cell is a link, one
        with no spaces round its cells and one with wide spaces; only the Status cell changes,
        to `` Accepted `` between its pipes, and the rest of each row keeps its spacing."""
        en_rows = ("|[ADR-0002](adr/ADR-0002-one-cli.md)|One command-line entry point|Proposed|\n",
                   "| [ADR-0001](adr/ADR-0001-toml.md) | Use TOML for the config |  Proposed   |\n")
        en_new = ("|[ADR-0002](adr/ADR-0002-one-cli.md)|One command-line entry point| Accepted |\n",
                  "| [ADR-0001](adr/ADR-0001-toml.md) | Use TOML for the config | Accepted |\n")
        zh_rows = ("| [ADR-0001](adr/ADR-0001-toml.zh-CN.md) | 配置用 TOML | 提议中 |\n",
                   "| [ADR-0002](adr/ADR-0002-one-cli.zh-CN.md) | 只有一个命令行入口 | 提议中 |\n")
        zh_new = tuple(text.replace("| 提议中 |", "| 已接受 |") for text in zh_rows)
        files = {ARCH: arch_text("en", "| ADR | Title | Status |\n|---|---|---|\n"
                                 + "".join(en_rows)),
                 ARCH_ZH: arch_text("zh-CN", "| ADR | 标题 | 状态 |\n| :-- | :-- | :-- |\n"
                                    + "".join(zh_rows)),
                 **proposed_adrs("ADR-0001", "ADR-0002")}
        changes = {ARCH: approved_arch(files[ARCH], "en", zip(en_rows, en_new)),
                   ARCH_ZH: approved_arch(files[ARCH_ZH], "zh-CN", zip(zh_rows, zh_new)),
                   **accepted_adrs(files, "ADR-0001", "ADR-0002")}
        self.assert_report(self.accepted_run(files, changes), "ADR-0001", "ADR-0002")

    def test_status_column_before_another_column(self):
        """Planted bug "the table cell left as it was": the Status (状态) column is not the last;
        it changes, and the Notes (备注) column after it, which starts with the word, stays."""
        en_rows = ("| ADR-0001 | Use TOML for the config | Proposed | Proposed by AR1 |\n",
                   "| ADR-0002 | One command-line entry point | Proposed | None |\n")
        zh_rows = ("| ADR-0001 | 提议中 | 配置用 TOML | 提议中，由 AR1 提出 |\n",
                   "| ADR-0002 | 提议中 | 只有一个命令行入口 | 无 |\n")
        en_new = tuple(text.replace("| Proposed |", "| Accepted |", 1) for text in en_rows)
        zh_new = tuple(text.replace("| 提议中 |", "| 已接受 |", 1) for text in zh_rows)
        files = {ARCH: arch_text("en", "| ADR | Title | Status | Notes |\n"
                                 "| --- | --- | --- | --- |\n" + "".join(en_rows)),
                 ARCH_ZH: arch_text("zh-CN", "| ADR | 状态 | 标题 | 备注 |\n"
                                    "| --- | --- | --- | --- |\n" + "".join(zh_rows)),
                 **proposed_adrs("ADR-0001", "ADR-0002")}
        changes = {ARCH: approved_arch(files[ARCH], "en", zip(en_rows, en_new)),
                   ARCH_ZH: approved_arch(files[ARCH_ZH], "zh-CN", zip(zh_rows, zh_new)),
                   **accepted_adrs(files, "ADR-0001", "ADR-0002")}
        self.assert_report(self.accepted_run(files, changes), "ADR-0001", "ADR-0002")

    def test_last_column_without_a_status_header(self):
        """Planted bug "the table cell left as it was": no header says Status (状态), so the
        last column is the Status column; the headings are ``### Decision Records`` and
        ``### 决策记录``, with no number."""
        files = {ARCH: arch_text("en", "| ADR | Title | Where it stands |\n| --- | --- | --- |\n"
                                 + row("ADR-0001", "Proposed"), heading="### Decision Records"),
                 ARCH_ZH: arch_text("zh-CN", "| 编号 | 标题 | 现状 |\n| --- | --- | --- |\n"
                                    + row("ADR-0001", "提议中", "zh-CN"), heading="### 决策记录"),
                 **proposed_adrs("ADR-0001")}
        changes = {**approved_pair(files, "ADR-0001"), **accepted_adrs(files, "ADR-0001")}
        self.assert_report(self.accepted_run(files, changes), "ADR-0001")

    def test_row_only_in_the_chinese_table(self):
        """Planted bug "the table cell left as it was": ADR-0002 is listed in the Chinese table
        only; it is accepted and its Chinese cell changes, while the English table, which has
        no row for it, changes only ADR-0001's cell."""
        files = {ARCH: arch_text("en", table("en", row("ADR-0001", "Proposed"))),
                 ARCH_ZH: arch_text("zh-CN", table("zh-CN", row("ADR-0001", "提议中", "zh-CN"),
                                                   row("ADR-0002", "提议中", "zh-CN"))),
                 **proposed_adrs("ADR-0001", "ADR-0002")}
        changes = {ARCH: approved_arch(files[ARCH], "en", [cell_change("ADR-0001")]),
                   ARCH_ZH: approved_arch(files[ARCH_ZH], "zh-CN",
                                          [cell_change("ADR-0001", "zh-CN"),
                                           cell_change("ADR-0002", "zh-CN")]),
                   **accepted_adrs(files, "ADR-0001", "ADR-0002")}
        self.assert_report(self.accepted_run(files, changes), "ADR-0001", "ADR-0002")

    def test_fenced_example_table_is_not_the_decision_records(self):
        """Planted bug "an ADR the architecture does not list accepted": a fenced example of the
        section, listing ADR-0007 as proposed, comes first; it stays as it was, and the real
        table's ADR-0001 is accepted (ADR-0007 has no files, which would refuse)."""
        extras = {"en": "The decision records look like this:\n\n```markdown\n"
                        "## 11. Decision records\n\n" + EN_HEAD
                        + "| ADR-0007 | An example | Proposed |\n```\n\n",
                  "zh-CN": "决策记录的样子：\n\n```markdown\n## 11. 决策记录\n\n" + ZH_HEAD
                           + "| ADR-0007 | 一个例子 | 提议中 |\n```\n\n"}
        files = {ARCH: arch_text("en", table("en", row("ADR-0001", "Proposed")),
                                 extra=extras["en"]),
                 ARCH_ZH: arch_text("zh-CN", table("zh-CN", row("ADR-0001", "提议中", "zh-CN")),
                                    extra=extras["zh-CN"]),
                 **proposed_adrs("ADR-0001")}
        changes = {**approved_pair(files, "ADR-0001"), **accepted_adrs(files, "ADR-0001")}
        self.assert_report(self.accepted_run(files, changes), "ADR-0001")


class RefusalTests(AdrCase):
    """Planted bug "a refused ADR that still lets the architecture be written" (D202).

    The architecture lists ADR-0001, complete and proposed, and ADR-0002,
    whose files are wrong. ``approve`` exits 1 with ``ok`` false and one
    problem that names ADR-0002, and every file under ``docs/`` stays byte
    for byte: the architecture pair and every ADR file, ADR-0001's included.
    """

    def refused(self, changes: dict) -> None:
        """Writes the case and asserts the refusal.

        Args:
            changes: Paths of the case mapped to LF text, or None to delete the
                file, applied over the architecture pair and both proposed ADRs.
        """
        ids = ("ADR-0001", "ADR-0002")
        self.put({**proposed_pair(*ids), **proposed_adrs(*ids), **changes})
        before = self.tree()
        report = self.report_of(self.approve(), 1, "approve")
        problems = report["problems"]
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("ADR-0002", problem_text(problems[0]), problems)
        self.assert_tree(before)

    def test_listed_adr_without_an_english_file(self):
        """ADR-0002 has only its mirror under ``docs/adr/``, or no file at all."""
        cases = {"mirror only": {adr_path("ADR-0002"): None},
                 "no file": {adr_path("ADR-0002"): None, adr_path("ADR-0002", "zh-CN"): None}}
        for name, changes in cases.items():
            with self.subTest(case=name):
                self.project = Project([base_step()])
                self.refused(changes)

    def test_listed_adr_without_a_mirror(self):
        """ADR-0002's English file names a mirror that does not exist."""
        self.refused({adr_path("ADR-0002", "zh-CN"): None})

    def test_two_english_files_for_one_id(self):
        """Two English files start with ``ADR-0002-``."""
        self.refused({"docs/adr/ADR-0002-other.md": adr_text("ADR-0002")})

    def test_adr_file_without_a_header(self):
        """ADR-0002's English file has no front matter, or its mirror's has no version."""
        cases = {"English without front matter": {
                     adr_path("ADR-0002"): "# ADR-0002: One command-line entry point\n\n"
                                           "## 1. Status\n\nProposed.\n"},
                 "mirror without a version": {
                     adr_path("ADR-0002", "zh-CN"): swap(adr_text("ADR-0002", "zh-CN"),
                                                         'version: "0.1"\n', "")}}
        for name, changes in cases.items():
            with self.subTest(case=name):
                self.project = Project([base_step()])
                self.refused(changes)

    def test_adr_versions_differ(self):
        """ADR-0002's English file is at 0.1 and its mirror at 0.2."""
        self.refused({adr_path("ADR-0002", "zh-CN"): adr_text("ADR-0002", "zh-CN", version="0.2")})

    def test_accepted_adr_without_a_mirror(self):
        """ADR-0002 is already accepted in English, and in both tables, and has no mirror:
        refused too, since the checks apply to every listed ADR, proposed or not."""
        self.refused({
            ARCH: arch_text("en", table("en", row("ADR-0001", "Proposed"),
                                        row("ADR-0002", "Accepted"))),
            ARCH_ZH: arch_text("zh-CN", table("zh-CN", row("ADR-0001", "提议中", "zh-CN"),
                                              row("ADR-0002", "已接受", "zh-CN"))),
            adr_path("ADR-0002"): accepted_adr("ADR-0002"),
            adr_path("ADR-0002", "zh-CN"): None})


if __name__ == "__main__":
    unittest.main()
