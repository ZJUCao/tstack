"""Tests for R12: English documents and their Chinese mirrors (design 6.4)."""

import unittest

from helpers import (
    EN_BODY, ZH_BODY, CheckTestCase, doc_pair, doc_text, lines, parallel, run_pr,
)

TITLE = "[docs] Update documents"
EN = "docs/x.md"
ZH = "docs/x.zh-CN.md"
MORE_EN = EN_BODY + "\nA new paragraph.\n"
MORE_ZH = ZH_BODY + "\n新的段落。\n"


class R12Tests(CheckTestCase):
    """Checks header, pairing, versions and structure of changed documents."""

    def check(self, changes, base=None):
        """Runs a docs PR over an optional base set of documents."""
        return run_pr(TITLE, changes, base_files=base)

    def assert_doc_fail(self, outcome, stem="docs/x"):
        """Asserts that R12 failed and named a path of the document pair."""
        self.assert_rule(outcome, "R12", "fail")
        self.assert_exit(outcome, 1)
        paths = outcome.paths("R12")
        self.assertTrue(any(p.startswith(stem) for p in paths), outcome.describe())

    def raised(self, **kwargs):
        """Returns a pair at version 1.1 with new content, for a base at 1.0."""
        kwargs.setdefault("en_body", MORE_EN)
        kwargs.setdefault("zh_body", MORE_ZH)
        return doc_pair(version="1.1", **kwargs)

    def test_both_files_changed_with_raised_version_pass(self):
        """A raised version in both files passes."""
        out = self.check(self.raised(), doc_pair())
        self.assert_rule(out, "R12", "pass")
        self.assert_clean(out)

    def test_version_not_raised_fails(self):
        """A changed English document with the same version fails."""
        out = self.check(doc_pair(en_body=MORE_EN, zh_body=MORE_ZH), doc_pair())
        self.assert_doc_fail(out)
        self.assertIn(EN, out.paths("R12"))

    def test_lowered_version_fails(self):
        """A lower version is not a raised version."""
        out = self.check(doc_pair(version="0.9", en_body=MORE_EN, zh_body=MORE_ZH), doc_pair())
        self.assert_doc_fail(out)

    def test_version_ten_is_higher_than_nine(self):
        """Versions compare as numbers, so 1.10 is higher than 1.9."""
        out = self.check(doc_pair(version="1.10", en_body=MORE_EN, zh_body=MORE_ZH),
                         doc_pair(version="1.9"))
        self.assert_rule(out, "R12", "pass")

    def test_nine_after_ten_fails(self):
        """Going from 1.10 to 1.9 lowers the version."""
        out = self.check(doc_pair(version="1.9", en_body=MORE_EN, zh_body=MORE_ZH),
                         doc_pair(version="1.10"))
        self.assert_doc_fail(out)

    def test_major_bump_passes(self):
        """Moving from 1.5 to 2.0 raises the version."""
        out = self.check(doc_pair(version="2.0", en_body=MORE_EN, zh_body=MORE_ZH),
                         doc_pair(version="1.5"))
        self.assert_rule(out, "R12", "pass")

    def test_mirror_not_changed_fails(self):
        """Changing only the English file leaves the mirror's version behind."""
        english_only = {EN: self.raised()[EN]}
        self.assert_doc_fail(self.check(english_only, doc_pair()))

    def test_versions_that_differ_fail(self):
        """The two files must carry the same version."""
        out = self.check(doc_pair(version="1.1", zh_version="1.2"), doc_pair())
        self.assert_doc_fail(out)

    def test_different_troy_doc_in_pair_fails(self):
        """The two files must carry the same troy-doc."""
        out = self.check(self.raised(zh_kwargs={"doc_id": "other"}), doc_pair())
        self.assert_doc_fail(out)

    def test_wrong_pointers_fail(self):
        """mirror and mirror-of must point at each other."""
        cases = [
            {"en_kwargs": {"partner": "y.zh-CN.md"}},
            {"zh_kwargs": {"partner": "z.md"}},
        ]
        outs = parallel(lambda k: self.check(self.raised(**k), doc_pair()), cases)
        for kwargs, out in zip(cases, outs):
            with self.subTest(kwargs=kwargs):
                self.assert_doc_fail(out)

    def test_new_english_without_mirror_fails(self):
        """A new English document must arrive with its mirror."""
        new_en = doc_pair(name="new", version="0.1")["docs/new.md"]
        out = self.check({"docs/new.md": new_en})
        self.assert_doc_fail(out, "docs/new")

    def test_new_pair_passes(self):
        """A new English document with its mirror at 0.1 passes."""
        out = self.check(doc_pair(name="new", version="0.1"))
        self.assert_rule(out, "R12", "pass")
        self.assert_clean(out)

    def test_heading_levels_that_differ_fail(self):
        """The mirror must use the same sequence of heading levels."""
        bad_zh = ZH_BODY.replace("## 章节", "### 章节")
        self.assert_doc_fail(self.check(self.raised(zh_body=bad_zh), doc_pair()))

    def test_extra_heading_in_mirror_fails(self):
        """An extra heading in one file breaks the heading sequence."""
        bad_zh = ZH_BODY + "\n## 新章节\n\n文字。\n"
        self.assert_doc_fail(self.check(self.raised(zh_body=bad_zh), doc_pair()))

    def test_table_columns_that_differ_fail(self):
        """The mirror's tables must have the same column counts."""
        bad_zh = ZH_BODY.replace(
            "| 甲 | 乙 |\n| --- | --- |\n| 1 | 2 |",
            "| 甲 | 乙 | 丙 |\n| --- | --- | --- |\n| 1 | 2 | 3 |",
        )
        self.assert_doc_fail(self.check(self.raised(zh_body=bad_zh), doc_pair()))

    def test_code_blocks_are_ignored_in_structure_comparison(self):
        """Headings and tables inside code blocks do not count."""
        code = "\n```text\n# comment\n## also comment\n| a | b | c |\n| - | - | - |\n```\n"
        out = self.check(self.raised(en_body=EN_BODY + code, zh_body=ZH_BODY), doc_pair())
        self.assert_rule(out, "R12", "pass")

    def test_unquoted_values_fail(self):
        """Every header value must be in double quotes."""
        cases = [("version", "1.1"), ("updated", "2026-11-05"), ("troy-doc", "x"), ("lang", "en")]

        def run(case):
            """Checks a pair whose English header has one unquoted value."""
            pair = self.raised(en_kwargs={"raw": {case[0]: case[1]}})
            return self.check(pair, doc_pair())

        for (key, _), out in zip(cases, parallel(run, cases)):
            with self.subTest(key=key):
                self.assert_doc_fail(out)

    def test_unquoted_value_in_mirror_fails(self):
        """The Chinese file's header is checked too."""
        pair = self.raised(zh_kwargs={"raw": {"updated": "2026-11-05"}})
        self.assert_doc_fail(self.check(pair, doc_pair()))

    def test_invalid_headers_fail(self):
        """Missing keys and malformed values fail the header check."""
        cases = {
            "no status": {"omit": ["status"]},
            "no version": {"omit": ["version"]},
            "no updated": {"omit": ["updated"]},
            "no lang": {"omit": ["lang"]},
            "no mirror": {"omit": ["mirror"]},
            "bad lang": {"raw": {"lang": '"fr"'}},
            "short version": {"raw": {"version": '"1"'}},
            "three-part version": {"raw": {"version": '"1.0.0"'}},
            "v prefix": {"raw": {"version": '"v1.0"'}},
            "slash date": {"raw": {"updated": '"2026/11/05"'}},
        }
        def run(kwargs):
            """Checks a new pair whose English header is broken as described."""
            return self.check(doc_pair(name="new", version="0.1", en_kwargs=kwargs))

        for name, out in zip(cases, parallel(run, list(cases.values()))):
            with self.subTest(case=name):
                self.assert_doc_fail(out, "docs/new")

    def test_chinese_header_missing_mirror_of_fails(self):
        """A Chinese document needs mirror-of."""
        pair = doc_pair(name="new", version="0.1", zh_kwargs={"omit": ["mirror-of"]})
        self.assert_doc_fail(self.check(pair), "docs/new")

    def test_chinese_only_fix_passes(self):
        """A translation fix that keeps versions and structure passes."""
        fixed = doc_text("zh-CN", body=ZH_BODY.replace("一些文字", "更正后的文字"))
        out = self.check({ZH: fixed}, doc_pair())
        self.assert_rule(out, "R12", "pass")
        self.assert_clean(out)

    def test_chinese_only_change_that_breaks_structure_fails(self):
        """A Chinese-only change must still match the headings."""
        broken = doc_text("zh-CN", body=ZH_BODY.replace("### 细节", "#### 细节"))
        self.assert_doc_fail(self.check({ZH: broken}, doc_pair()))

    def test_chinese_only_change_with_other_version_fails(self):
        """A Chinese-only change must keep the English version."""
        other = doc_text("zh-CN", version="1.1", body=MORE_ZH)
        self.assert_doc_fail(self.check({ZH: other}, doc_pair()))

    def test_chinese_only_change_with_broken_header_fails(self):
        """A Chinese-only change must keep a valid, quoted header."""
        broken = doc_text("zh-CN", raw={"version": "1.0"})
        self.assert_doc_fail(self.check({ZH: broken}, doc_pair()))

    def test_english_deleted_alone_fails(self):
        """Deleting an English document without its mirror fails."""
        out = self.check({EN: None}, doc_pair())
        self.assert_rule(out, "R12", "fail")

    def test_deleting_both_files_does_not_fail(self):
        """Deleting an English document with its mirror is allowed."""
        out = self.check({EN: None, ZH: None}, doc_pair())
        self.assertNotEqual(out.status("R12"), "fail", out.describe())
        self.assert_clean(out)

    def test_duplicate_troy_doc_with_existing_document_fails(self):
        """A new English document may not reuse another's troy-doc."""
        out = self.check(doc_pair(name="y", doc_id="x", version="0.1"), doc_pair())
        self.assert_rule(out, "R12", "fail")

    def test_duplicate_troy_doc_between_new_documents_fails(self):
        """Two new English documents may not share a troy-doc."""
        changes = {}
        changes.update(doc_pair(name="a", doc_id="dup", version="0.1"))
        changes.update(doc_pair(name="b", doc_id="dup", version="0.1"))
        self.assert_rule(self.check(changes), "R12", "fail")

    def test_templates_under_troy_mode_are_not_documents(self):
        """Copied templates in .troy-mode/ keep their markers without failing R12 (F06)."""
        template = doc_text(doc_id="rules", updated="{{YYYY-MM-DD}}", name="rules")
        out = run_pr("[rules] Set up troy-mode", {".troy-mode/templates/rules.md": template})
        self.assert_rule(out, "R12", "skip")

    def test_template_under_troy_mode_shares_troy_doc_with_a_document(self):
        """A project document may share its troy-doc with a template in .troy-mode/."""
        changes = doc_pair(name="rules", version="1.0")
        changes[".troy-mode/templates/rules.md"] = doc_text(doc_id="rules", name="rules")
        out = self.check(changes)
        self.assert_rule(out, "R12", "pass")
        self.assertEqual([], out.paths("R12"), out.describe())

    def test_no_document_changed_skips(self):
        """A PR that changes no document skips R12."""
        out = self.check({"docs/plain.md": lines(3, "text")})
        self.assert_rule(out, "R12", "skip")

    def test_unrelated_source_pr_skips(self):
        """A source PR with no markdown skips R12."""
        out = run_pr("[F04 5/6 impl] Code", {"src/a.py": "x = 1\n"})
        self.assert_rule(out, "R12", "skip")


if __name__ == "__main__":
    unittest.main()
