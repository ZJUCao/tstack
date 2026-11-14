"""Tests for R22: the summary for Troy at the top of the PR description (F14 design 3, 6.1, 9.1).

R22 runs inside ``troy_check.py pr`` and depends only on the PR title, the
description, and ``[summary] max_chars`` in the merge-base commit's config.
So each config gets one shared sandbox, and every case is one ``check_pr``
call on it with its own title and description. The calls of a test class
run side by side (``prefetch``).

Lines of the description are counted from its first line, 1-based, as R20
counts them. The summaries are built from the example of design 3.5.

Planted bugs of design 9.2 and the tests that catch them:

- the length counted in bytes: ``LengthTests.test_chinese_part_counts_characters_not_bytes``;
- the limit read from the PR's own commit: ``ConfigTests.test_pr_cannot_raise_its_own_limit``;
- the order of the two parts not checked: ``OrderTests.test_english_first_fails``;
- the count of items not compared: ``DecisionTests.test_unequal_numbers_of_items_fail``;
- IDs searched inside inline code: ``IdTests.test_ids_in_code_pass``;
- ``\\b`` at an ID's edge, so that ``见R03`` passes:
  ``IdTests.test_id_next_to_chinese_or_markup_fails``;
- the ``docs`` prefixes not matched: ``KindTests.test_kinds_that_need_one_fail_without_it``.

Planted in the build, not in design 9.2: an ID pattern with the wrong number of
digits (a rule with one, a decision with four, a role task with two), caught
by ``IdTests.test_lookalikes_pass``.
"""

import re
import threading
import unittest

from helpers import CONFIG_PATH, EMAIL, Sandbox, make_config, pr_body, pr_sandbox
from prefetch import PrefetchedCase, prefetchable, run_pr

DESIGN = "[F04 1/6 design] Search recipes"
NEEDS_SUMMARY = (
    DESIGN,
    "[F04 2/6 test-plan] Search recipes",
    "[docs] Add the requirements",
    "[docs] Change the requirements: x",
    "[docs] Add the architecture",
    "[docs] Change the architecture for P01",
)
NO_SUMMARY = (
    "[F04 3/6 mock] x",
    "[F04 4/6 tests] x",
    "[F04 5/6 impl] x",
    "[F04 6/6 accept] x",
    "[F04 test-fix] x",
    "[B12 A/B test] x",
    "[B12 B/B fix] x",
    "[v0.1 tests] x",
    "[refactor] x",
    "[rules] Change the architecture for P01",
    "[docs] Release v0.1",
    "[docs] Update notes",
    "[docs] Update the architecture notes",
    "[docs] Add cases to the F04 test plan",
    "[docs] Record Troy's approval of docs/architecture.md",
    "Search recipes",
)

ZH_TITLE = "## 给 Troy 的摘要"
EN_TITLE = "## Summary for Troy"
ZH_HEADINGS = ("### 对你有什么变化", "### 需要你决定的事", "### 风险")
EN_HEADINGS = ("### What changes for you", "### What you decide", "### Risks")
ZH_REPLY = "回复「全按推荐」即可全部采用推荐，或写出编号和你选的方案。"
EN_REPLY = ('Reply "all as recommended" (全按推荐) to take every recommendation, or give the '
            "number and the option you want.")
ZH_NOTHING = "没有需要你决定的事。"
EN_NOTHING = "Nothing to decide."

ZH_CHANGE = ("你可以输入 `recipe-menu search 词...` 来找菜谱。它列出名称、食材或标签里包含你给的"
             "每一个词的菜谱，中英文都行，英文不分大小写，每一行还写明词是在哪里找到的。帮助里多一行 "
             "`search`。别的命令都不变。")
ZH_ITEMS = (
    "1. **原型里没有的新提示。** 例如 `2 recipes match \"葱\" and \"quick\".` 和 "
    "`没有菜谱匹配“lamb”。`。推荐：照写的接受，它们和原型里的句子是同一种说法。",
    "2. **输入空词，比如 `search \"\"`。** 方案 1：报错，提示你写一个词。方案 2：当作什么都没找到。"
    "推荐：方案 1，因为打错字不该看起来像“没有这个菜”。",
)
ZH_RISKS = ("- 速度：1,000 个菜谱时，`search` 在你的电脑上大约要 0.8 秒，离 1 秒的上限不远。以后哪次"
            "改动让它变慢，会先单独提速。\n"
            "- `search` 不查菜谱的编号，所以拼错的编号，比如 `tomato-eggs`，什么也找不到。")
EN_CHANGE = ("You can type `recipe-menu search WORD...` to find recipes. It lists the recipes whose "
             "name, ingredients, or tags hold every word you give, in English or Chinese, with "
             "English capitals ignored, and each row says where the word was found. The help gains "
             "a line for `search`. No other command changes.")
EN_ITEMS = (
    "1. **New messages that no prototype shows.** For example `2 recipes match \"葱\" and "
    "\"quick\".` and `没有菜谱匹配“lamb”。`. Recommended: accept them as written, because they "
    "follow the prototype's sentences.",
    "2. **An empty word, such as `search \"\"`.** Option 1: an error that asks you for a word. "
    "Option 2: it finds nothing. Recommended: option 1, because a typing mistake should not look "
    "like \"no such recipe\".",
)
EN_RISKS = ("- Speed: with 1,000 recipes, `search` takes about 0.8 seconds on your PC, close to its "
            "1-second limit. If a later change slows it down, a speed fix comes first, in its own "
            "PR.\n"
            "- `search` does not look at recipe IDs, so a mistyped ID such as `tomato-eggs` finds "
            "nothing.")
# Counted by design 3.3, the example of design 3.5 has these lengths.
ZH_EXAMPLE_LENGTH = 491
EN_EXAMPLE_LENGTH = 1137

EN_FILL = "Plain words for you to read. "
ZH_FILL = "这是一句写给你看的普通的话。"
LIMIT_3000 = "[summary]\nmax_chars = 3000\n"
LIMIT_1000 = "[summary]\nmax_chars = 1000\n"


def decide(items, reply: str) -> str:
    """The text under a decide heading: the numbered items, a blank line, and the reply line."""
    return "\n".join(items) + "\n\n" + reply


ZH = ((ZH_HEADINGS[0], ZH_CHANGE), (ZH_HEADINGS[1], decide(ZH_ITEMS, ZH_REPLY)),
      (ZH_HEADINGS[2], ZH_RISKS))
EN = ((EN_HEADINGS[0], EN_CHANGE), (EN_HEADINGS[1], decide(EN_ITEMS, EN_REPLY)),
      (EN_HEADINGS[2], EN_RISKS))
REST = pr_body("None")


def language(title: str, sections) -> str:
    """One language's summary: its ``##`` heading, then each ``###`` heading and its text.

    Args:
        title: The ``##`` heading line.
        sections: ``(### heading line, text)`` pairs; an empty text leaves the part empty.

    Returns:
        The text, ending with a line feed.
    """
    lines = [title, ""]
    for heading, text in sections:
        lines += [heading, ""]
        if text:
            lines += [text, ""]
    return "\n".join(lines)


def body(zh=ZH, en=EN, rest: str = REST, before: str = "") -> str:
    """A description: optional text, the Chinese part, the English part, then the rest.

    Args:
        zh: The Chinese part's sections.
        en: The English part's sections.
        rest: The PR template's sections after the summary.
        before: Text placed before the Chinese heading.

    Returns:
        The description.
    """
    return before + language(ZH_TITLE, zh) + "\n" + language(EN_TITLE, en) + "\n" + rest


def swap(sections, index: int, text=None, heading=None) -> tuple:
    """The sections with one section's text or heading replaced."""
    items = list(sections)
    old_heading, old_text = items[index]
    items[index] = (old_heading if heading is None else heading,
                    old_text if text is None else text)
    return tuple(items)


def add(sections, index: int, paragraph: str) -> tuple:
    """The sections with a paragraph added at the end of one section's text."""
    return swap(sections, index, sections[index][1] + "\n\n" + paragraph)


def part_length(sections) -> int:
    """A part's length as design 3.3 counts it: code points after its heading, stripped."""
    return len(language("##", sections).split("\n", 1)[1].strip())


def filler(unit: str, count: int) -> str:
    """Exactly ``count`` characters of repeated text that ends with no space."""
    text = (unit * (count // len(unit) + 1))[:count]
    return text[:-1] + "x" if text.endswith(" ") else text


def sized(sections, total: int, unit: str) -> tuple:
    """The sections with a paragraph of filler added so the part has exactly ``total`` characters.

    Raises:
        ValueError: The fixture could not reach the length (a bug in this file).
    """
    extra = total - part_length(sections) - 2
    result = add(sections, 0, filler(unit, extra))
    if part_length(result) != total:
        raise ValueError(f"sized() built {part_length(result)} characters, not {total}")
    return result


def line_of(text: str, needle: str) -> int:
    """The 1-based number of the first line of a text that holds a needle."""
    return next(i for i, line in enumerate(text.split("\n"), 1) if needle in line)


def crlf(text: str) -> str:
    """The text with CRLF line endings."""
    return text.replace("\n", "\r\n")


# ------------------------------------------------------------------ sandboxes

_BOXES: dict = {}
_BOX_LOCK = threading.Lock()
CHANGES = {"docs/a.md": "a\n"}
MESSAGE = "Change the docs"
BOX_SETUPS = {
    # The base config has no [summary] table: the default limit, 2,000.
    "default": (make_config(), CHANGES),
    "higher": (make_config(extra=LIMIT_3000), CHANGES),
    "lower": (make_config(extra=LIMIT_1000), CHANGES),
    # The PR's own commit raises the limit; the merge base keeps the default.
    "raised": (make_config(), {**CHANGES, CONFIG_PATH: make_config(extra=LIMIT_3000)}),
}


def _build(name: str) -> Sandbox:
    """Builds one shared sandbox.

    ``main-moved``: the feature branch starts from a base with the default
    config, then ``main`` gets a commit that raises the limit, so the merge
    base and ``main``'s tip differ.
    """
    if name != "main-moved":
        config, changes = BOX_SETUPS[name]
        return pr_sandbox(changes, config=config, message=MESSAGE)
    box = Sandbox(config=make_config())
    try:
        box.branch()
        box.commit(CHANGES, message=MESSAGE)
        box.checkout("main")
        box.commit({CONFIG_PATH: make_config(extra=LIMIT_3000)}, message="Raise the limit")
    except Exception:
        box.close()
        raise
    return box


def sandbox(name: str) -> Sandbox:
    """The shared sandbox of a name, built on first use."""
    with _BOX_LOCK:
        if name not in _BOXES:
            _BOXES[name] = _build(name)
        return _BOXES[name]


def tearDownModule():
    """Deletes the shared sandboxes."""
    for box in _BOXES.values():
        box.close()


@prefetchable
def check(box: str, title: str, text):
    """Runs ``troy_check.py pr --json`` on a shared sandbox.

    Args:
        box: The sandbox's name.
        title: The PR title.
        text: The description, or None for no ``--body-file``.

    Returns:
        The outcome.
    """
    return sandbox(box).check_pr(title, body=text)


@prefetchable
def commit_with(config: str):
    """Runs ``troy_check.py commit`` in a repository whose config is the given text."""
    with Sandbox(config=config) as box:
        return box.check_commit(message="Fix the docs", email=EMAIL)


class R22Case(PrefetchedCase):
    """Assertions on R22's result and its details."""

    def assert_r22(self, out, expected: str, details=None) -> None:
        """Asserts R22's result and, when given, its number of details.

        Args:
            out: The outcome.
            expected: ``pass``, ``fail``, or ``skip``.
            details: The exact number of details, ``"some"`` for at least one,
                or None to leave them out.
        """
        self.assert_rule(out, "R22", expected)
        if expected == "fail":
            self.assert_exit(out, 1)
        found = out.details("R22")
        if details == "some":
            self.assertGreaterEqual(len(found), 1, out.describe())
        elif details is not None:
            self.assertEqual(len(found), details, out.describe())

    def assert_names(self, out, ident: str, line: int) -> None:
        """Asserts one failing detail that names an ID and its line.

        The line is the detail's ``line`` or a number in its message, the
        ID's own digits left out.
        """
        self.assert_r22(out, "fail", 1)
        for detail in out.details("R22"):
            message = detail.get("message") or ""
            self.assertIn(ident, message, out.describe())
            rest = message.replace(ident, " ")
            self.assertTrue(detail.get("line") == line
                            or re.search(rf"(?<!\d){line}(?!\d)", rest),
                            f"line {line} is not named\n{out.describe()}")

    def assert_numbers(self, out, *numbers: int) -> None:
        """Asserts that R22's details name each number, with or without a thousands comma."""
        text = " ".join(d.get("message") or "" for d in out.details("R22"))
        for number in numbers:
            digits = str(number)
            pattern = digits if number < 1000 else f"{digits[:-3]},?{digits[-3:]}"
            self.assertRegex(text, rf"(?<!\d){pattern}(?!\d)", out.describe())


class KindTests(R22Case):
    """Which PRs need a summary (design 4, 6.1)."""

    def test_kinds_that_need_one_pass_with_it(self):
        """Design, test plan, requirements, and architecture PRs pass with the example."""
        outs = [check("default", title, body()) for title in NEEDS_SUMMARY]
        for title, out in zip(NEEDS_SUMMARY, outs):
            with self.subTest(title=title):
                self.assert_r22(out, "pass", 0)

    def test_kinds_that_need_one_fail_without_it(self):
        """The same PRs with only the PR template's sections fail."""
        outs = [check("default", title, REST) for title in NEEDS_SUMMARY]
        for title, out in zip(NEEDS_SUMMARY, outs):
            with self.subTest(title=title):
                self.assert_r22(out, "fail", "some")

    def test_other_kinds_skip(self):
        """Every other PR, an unparsable title included, is skipped with or without a summary."""
        outs = [(check("default", title, REST), check("default", title, body()))
                for title in NO_SUMMARY]
        for title, (bare, full) in zip(NO_SUMMARY, outs):
            with self.subTest(title=title):
                self.assert_r22(bare, "skip")
                self.assert_r22(full, "skip")

    def test_no_description_skips(self):
        """Without ``--body-file``, a PR that needs a summary is skipped."""
        outs = [check("default", title, None) for title in NEEDS_SUMMARY]
        for title, out in zip(NEEDS_SUMMARY, outs):
            with self.subTest(title=title):
                self.assert_r22(out, "skip")


class OrderTests(R22Case):
    """The Order check: Chinese heading first, the English heading next (design 3.1, 6.1)."""

    def test_example_passes(self):
        """The summary of design 3.5, before the PR template's sections, passes."""
        self.assert_r22(check("default", DESIGN, body()), "pass", 0)

    def test_blank_lines_before_the_chinese_heading_pass(self):
        """The first line that is not blank is what counts."""
        self.assert_r22(check("default", DESIGN, body(before="\n\n  \n")), "pass", 0)

    def test_english_first_fails(self):
        """The English part before the Chinese part fails."""
        text = language(EN_TITLE, EN) + "\n" + language(ZH_TITLE, ZH) + "\n" + REST
        self.assert_r22(check("default", DESIGN, text), "fail", "some")

    def test_wrong_order_fails(self):
        """Something before the Chinese heading, or another ``##`` heading after its part."""
        zh_only = language(ZH_TITLE, ZH)
        cases = {
            "a line before the Chinese heading": body(before="Summary below.\n\n"),
            "the template's sections first": REST + "\n" + body(rest=""),
            "Why between the parts": zh_only + "\n## Why\n\nBecause.\n\n" + language(EN_TITLE, EN),
            "no English part": zh_only + "\n" + REST,
            "no Chinese part": language(EN_TITLE, EN) + "\n" + REST,
            "the English heading renamed": body().replace(EN_TITLE, "## Summary"),
        }
        outs = [check("default", DESIGN, text) for text in cases.values()]
        for label, out in zip(cases, outs):
            with self.subTest(case=label):
                self.assert_r22(out, "fail", "some")


class PartsTests(R22Case):
    """The Parts and Chinese checks (design 3.2, 6.1)."""

    def test_missing_renamed_or_extra_part_fails_once(self):
        """Each part needs exactly the three headings, in order: one detail each."""
        cases = {
            "English risks missing": body(en=EN[:2]),
            "Chinese risks missing": body(zh=ZH[:2]),
            "English change heading renamed": body(en=swap(EN, 0, heading="### What changes")),
            "Chinese change heading renamed": body(zh=swap(ZH, 0, heading="### 有什么变化")),
            "English parts out of order": body(en=(EN[0], EN[2], EN[1])),
            "Chinese parts out of order": body(zh=(ZH[0], ZH[2], ZH[1])),
            "a fourth English part": body(en=EN + (("### Notes", "Nothing else."),)),
            "a fourth Chinese part": body(zh=ZH + (("### 备注", "没有别的。"),)),
            "English risks with no text": body(en=swap(EN, 2, text="")),
            "English change with no text": body(en=swap(EN, 0, text="")),
        }
        outs = [check("default", DESIGN, text) for text in cases.values()]
        for label, out in zip(cases, outs):
            with self.subTest(case=label):
                self.assert_r22(out, "fail", 1)

    def test_decide_heading_missing_or_chinese_part_empty_fails(self):
        """Faults that may break more than one check fail with at least one detail."""
        cases = {
            "English decide heading renamed": body(en=swap(EN, 1, heading="### Decisions")),
            "Chinese decide heading missing": body(zh=(ZH[0], ZH[2])),
            "Chinese risks with no text": body(zh=swap(ZH, 2, text="")),
        }
        outs = [check("default", DESIGN, text) for text in cases.values()]
        for label, out in zip(cases, outs):
            with self.subTest(case=label):
                self.assert_r22(out, "fail", "some")

    def test_chinese_part_without_a_chinese_character_fails(self):
        """A ``###`` part of the Chinese summary written with no Chinese character fails once."""
        cases = {
            "change in English": body(zh=swap(ZH, 0, text=EN_CHANGE)),
            "risks in English": body(zh=swap(ZH, 2, text="None found.")),
        }
        outs = [check("default", DESIGN, text) for text in cases.values()]
        for label, out in zip(cases, outs):
            with self.subTest(case=label):
                self.assert_r22(out, "fail", 1)

    def test_fixed_none_found_texts_pass(self):
        """``None found.`` and ``没有发现风险。`` are text under the risks headings."""
        text = body(zh=swap(ZH, 2, text="没有发现风险。"), en=swap(EN, 2, text="None found."))
        self.assert_r22(check("default", DESIGN, text), "pass", 0)


class LengthTests(R22Case):
    """The Length check: at most ``max_chars`` code points per part (design 3.3, 6.1)."""

    def test_boundary(self):
        """2,000 characters in a part pass and 2,001 fail, in either language."""
        cases = {
            "English 2000": (body(en=sized(EN, 2000, EN_FILL)), "pass", 0),
            "English 2001": (body(en=sized(EN, 2001, EN_FILL)), "fail", 1),
            "Chinese 2000": (body(zh=sized(ZH, 2000, ZH_FILL)), "pass", 0),
            "Chinese 2001": (body(zh=sized(ZH, 2001, ZH_FILL)), "fail", 1),
            "both 2000": (body(zh=sized(ZH, 2000, ZH_FILL), en=sized(EN, 2000, EN_FILL)),
                          "pass", 0),
        }
        outs = [check("default", DESIGN, case[0]) for case in cases.values()]
        for (label, (_, expected, details)), out in zip(cases.items(), outs):
            with self.subTest(case=label):
                self.assert_r22(out, expected, details)

    def test_failure_gives_the_count_and_the_limit(self):
        """The detail of a 2,001-character part names 2,001 and 2,000."""
        cases = (body(en=sized(EN, 2001, EN_FILL)), body(zh=sized(ZH, 2001, ZH_FILL)))
        outs = [check("default", DESIGN, text) for text in cases]
        for index, out in enumerate(outs):
            with self.subTest(language=("English", "Chinese")[index]):
                self.assert_r22(out, "fail", 1)
                self.assert_numbers(out, 2001, 2000)

    def test_chinese_part_counts_characters_not_bytes(self):
        """A Chinese part of 2,000 characters, most of them Chinese (over 5,000 bytes), passes."""
        sections = sized(ZH, 2000, ZH_FILL)
        size = len(language("##", sections).split("\n", 1)[1].strip().encode("utf-8"))
        if size <= 5000:
            raise ValueError(f"the fixture has only {size} bytes")
        self.assert_r22(check("default", DESIGN, body(zh=sections)), "pass", 0)

    def test_blank_space_at_both_ends_is_not_counted(self):
        """Blank lines around a 2,000-character part do not count."""
        en_part = language(EN_TITLE, sized(EN, 2000, EN_FILL)).replace(
            EN_TITLE + "\n", EN_TITLE + "\n\n   \n\n", 1)
        text = language(ZH_TITLE, ZH) + "\n\n\n" + en_part + "\n \n\n\n" + REST
        self.assert_r22(check("default", DESIGN, text), "pass", 0)

    def test_markdown_is_counted_as_written(self):
        """With a limit of 1,000, the example's English part fails with its count, 1,137.

        Its Chinese part, 491 characters, passes, so there is one detail.
        """
        out = check("lower", DESIGN, body())
        self.assert_r22(out, "fail", 1)
        self.assert_numbers(out, EN_EXAMPLE_LENGTH, 1000)

    def test_the_rest_of_the_description_is_not_counted(self):
        """A Why section of 5,000 characters after a summary that fits passes."""
        rest = REST.replace("Because.", filler(EN_FILL, 5000))
        self.assert_r22(check("default", DESIGN, body(rest=rest)), "pass", 0)


class DecisionTests(R22Case):
    """The Decisions check (design 3.2, 6.1)."""

    def test_item_without_a_recommendation_fails_once(self):
        """An item with no ``Recommended:`` or no ``推荐：`` fails, with one detail."""
        en_items = (EN_ITEMS[0], EN_ITEMS[1].split(" Recommended:")[0])
        en_colon = (EN_ITEMS[0], EN_ITEMS[1].replace("Recommended: option 1",
                                                     "Recommended option 1"))
        zh_items = (ZH_ITEMS[0].split("推荐：")[0], ZH_ITEMS[1])
        cases = {
            "English item without Recommended:": body(en=swap(EN, 1, decide(en_items, EN_REPLY))),
            "English Recommended without a colon": body(en=swap(EN, 1, decide(en_colon,
                                                                              EN_REPLY))),
            "Chinese item without 推荐：": body(zh=swap(ZH, 1, decide(zh_items, ZH_REPLY))),
        }
        outs = [check("default", DESIGN, text) for text in cases.values()]
        for label, out in zip(cases, outs):
            with self.subTest(case=label):
                self.assert_r22(out, "fail", 1)

    def test_ascii_colon_after_chinese_recommendation_passes(self):
        """``推荐:`` with an ASCII colon counts as a recommendation."""
        items = tuple(item.replace("推荐：", "推荐:") for item in ZH_ITEMS)
        self.assert_r22(check("default", DESIGN, body(zh=swap(ZH, 1, decide(items, ZH_REPLY)))),
                        "pass", 0)

    def test_indented_numbered_lines_are_not_items(self):
        """An indented ``1.`` line under an item is not an item, so the counts still match."""
        items = (EN_ITEMS[0], EN_ITEMS[1] + "\n   1. An error that asks you for a word.")
        self.assert_r22(check("default", DESIGN, body(en=swap(EN, 1, decide(items, EN_REPLY)))),
                        "pass", 0)

    def test_unequal_numbers_of_items_fail(self):
        """Two English items and one Chinese item, or none in one language, fail once."""
        cases = {
            "two and one": body(zh=swap(ZH, 1, decide(ZH_ITEMS[:1], ZH_REPLY))),
            "one and two": body(en=swap(EN, 1, decide(EN_ITEMS[:1], EN_REPLY))),
            "nothing and two": body(en=swap(EN, 1, EN_NOTHING)),
        }
        outs = [check("default", DESIGN, text) for text in cases.values()]
        for label, out in zip(cases, outs):
            with self.subTest(case=label):
                self.assert_r22(out, "fail", 1)

    def test_nothing_to_decide_passes(self):
        """The nothing-to-decide text in each language, with no reply line, passes."""
        text = body(zh=swap(ZH, 1, ZH_NOTHING), en=swap(EN, 1, EN_NOTHING))
        self.assert_r22(check("default", DESIGN, text), "pass", 0)

    def test_other_text_without_items_fails(self):
        """No numbered item and a text that is not the nothing-to-decide text fails once."""
        cases = {
            "English": body(zh=swap(ZH, 1, ZH_NOTHING), en=swap(EN, 1, "No points this time.")),
            "Chinese": body(zh=swap(ZH, 1, "这次没有。"), en=swap(EN, 1, EN_NOTHING)),
        }
        outs = [check("default", DESIGN, text) for text in cases.values()]
        for label, out in zip(cases, outs):
            with self.subTest(language=label):
                self.assert_r22(out, "fail", 1)


# (label, language, section index, paragraph added, the ID it holds)
EACH_KIND = [
    ("rule", "en", 0, "The search limit follows R03 now.", "R03"),
    ("project rule", "en", 0, "Your own rule P01 stays as it is.", "P01"),
    ("decision", "en", 0, "This was settled in D61 before.", "D61"),
    ("decision, one digit", "en", 0, "As D1 says, search is new.", "D1"),
    ("decision, three digits", "en", 0, "As D137 says, search is new.", "D137"),
    ("open question", "en", 0, "This answers Q16 for you.", "Q16"),
    ("open question, one digit", "en", 0, "This answers Q4 for you.", "Q4"),
    ("test case", "en", 0, "The check F04-T38 covers it.", "F04-T38"),
    ("test case of a bug", "en", 0, "The check B12-T3 covers it.", "B12-T3"),
    ("scenario", "en", 0, "You try it in v0.1-S23 by hand.", "v0.1-S23"),
    ("ADR", "en", 0, "The choice is in ADR-0004 now.", "ADR-0004"),
    ("performance target", "en", 0, "Search meets PT01 on your PC.", "PT01"),
    ("Architect task", "en", 0, "The design passed AR2 already.", "AR2"),
    ("Interface Designer task", "en", 0, "It came out of IF1 today.", "IF1"),
    ("Test Manager task", "en", 0, "It came out of TM1 today.", "TM1"),
    ("Developer task", "en", 0, "It came out of DV1 today.", "DV1"),
    ("Test Engineer task", "en", 0, "It came out of TE1 today.", "TE1"),
    ("Code Reviewer task", "en", 0, "It came out of CR1 today.", "CR1"),
    ("Product Manager task", "en", 0, "It came out of PM1 today.", "PM1"),
    ("in the Chinese part", "zh", 0, "这一点由 Q16 决定。", "Q16"),
    ("in the English risks", "en", 2, "- The 1-second limit is PT02.", "PT02"),
    ("in the Chinese risks", "zh", 2, "- 速度目标是 PT02。", "PT02"),
]
NEXT_TO = [
    ("right after a Chinese character", "zh", 0, "规则见R03。", "R03"),
    ("right before a Chinese character", "zh", 0, "这在D61里定过。", "D61"),
    ("between Chinese characters", "zh", 0, "用例F04-T38会检查。", "F04-T38"),
    ("in italics", "en", 0, "The rule _R03_ is gone.", "R03"),
    ("in bold", "en", 0, "As **D61** says.", "D61"),
    ("in brackets", "en", 0, "It holds (PT01).", "PT01"),
    ("at the start of a line", "en", 0, "R03 is the old rule.", "R03"),
    ("at the end of a line", "en", 0, "The old rule is R03", "R03"),
]
NOT_IDS = [
    ("feature IDs", "en", "It builds on F10 and F04."),
    ("a bug number", "en", "It fixes #12."),
    ("a version", "en", "It comes in v0.1, then v0.2."),
    ("inside a longer word", "en", "The PR03X file is fine."),
    ("a letter before", "en", "Use xR03 as a name."),
    ("a letter after", "en", "Use R03x as a name."),
    ("a digit before", "en", "Use 1R03 as a name."),
    ("a digit after", "en", "Use R033 as a name."),
    ("3D", "en", "A 3D view of the menu."),
    ("a rule number with one digit", "en", "Size R3 is not a rule."),
    ("a decision number with four digits", "en", "The code D1234 is not a decision."),
    ("an open question with three digits", "en", "Item Q123 is not a question."),
    ("a role task with two digits", "en", "The model IF12 is not a task."),
    ("feature ID in Chinese", "zh", "它基于 F10。"),
]
IN_CODE = [
    ("inline code", "en", "Type `R03` or `F04-T38` or `recipe-menu --rule P01` as shown."),
    ("inline code in Chinese", "zh", "输入 `D61` 或 `ADR-0004` 即可。"),
    ("a fenced code block", "en", "```text\nrecipe-menu search R03 D61 PT01 ADR-0004 IF1\n```"),
    ("a fenced code block in Chinese", "zh", "```\nQ16 v0.1-S23 F04-T38\n```"),
]


def with_paragraph(lang: str, index: int, paragraph: str) -> str:
    """The example's description with a paragraph added to one section of one language."""
    if lang == "zh":
        return body(zh=add(ZH, index, paragraph))
    return body(en=add(EN, index, paragraph))


class IdTests(R22Case):
    """The IDs check (design 3.4, 6.1)."""

    def run_cases(self, cases):
        """Checks the description of each case and returns the outcomes with their texts."""
        texts = [with_paragraph(case[1], case[2], case[3]) for case in cases]
        return [(text, check("default", DESIGN, text)) for text in texts]

    def test_each_kind_of_id_fails_with_its_line(self):
        """Each of the eight kinds, in either part: one detail with the ID and its line."""
        for case, (text, out) in zip(EACH_KIND, self.run_cases(EACH_KIND)):
            label, _, _, paragraph, ident = case
            with self.subTest(case=label):
                self.assert_names(out, ident, line_of(text, paragraph))

    def test_id_next_to_chinese_or_markup_fails(self):
        """Chinese characters, Markdown signs, and line ends are not ASCII letters or digits."""
        for case, (text, out) in zip(NEXT_TO, self.run_cases(NEXT_TO)):
            label, _, _, paragraph, ident = case
            with self.subTest(case=label):
                self.assert_names(out, ident, line_of(text, paragraph))

    def test_lookalikes_pass(self):
        """Feature IDs, bug numbers, versions, and IDs inside longer words are not IDs."""
        outs = [check("default", DESIGN, with_paragraph(lang, 0, text))
                for _, lang, text in NOT_IDS]
        for case, out in zip(NOT_IDS, outs):
            with self.subTest(case=case[0]):
                self.assert_r22(out, "pass", 0)

    def test_ids_in_code_pass(self):
        """IDs in inline code and in fenced code blocks are not checked."""
        outs = [check("default", DESIGN, with_paragraph(lang, 0, text))
                for _, lang, text in IN_CODE]
        for case, out in zip(IN_CODE, outs):
            with self.subTest(case=case[0]):
                self.assert_r22(out, "pass", 0)

    def test_ids_outside_the_summary_pass(self):
        """IDs in Why, What, and Checks are not R22's concern."""
        rest = ("## Why\n\nIt answers Q16 and follows D61 and R03.\n\n## What\n\n"
                "F04-T38 to F04-T40, ADR-0004, and PT01.\n\n## Checks\n\nIF1 and AR2 ran.\n\n"
                "## Soft-limit reason\n\nNone\n")
        self.assert_r22(check("default", DESIGN, body(rest=rest)), "pass", 0)


class ConfigTests(R22Case):
    """``[summary] max_chars`` from the merge-base commit's config (design 3.3, 6.1)."""

    def test_higher_base_limit_lets_a_longer_part_pass(self):
        """With 3,000 at the merge base, 2,500 and 3,000 pass and 3,001 fails, naming 3,000."""
        cases = {
            2500: ("pass", 0),
            3000: ("pass", 0),
            3001: ("fail", 1),
        }
        outs = {size: check("higher", DESIGN, body(en=sized(EN, size, EN_FILL)))
                for size in cases}
        for size, (expected, details) in cases.items():
            with self.subTest(size=size):
                self.assert_r22(outs[size], expected, details)
        self.assert_numbers(outs[3001], 3001, 3000)

    def test_default_limit_without_the_table(self):
        """The same 2,500-character part fails with the base config that has no [summary]."""
        out = check("default", DESIGN, body(en=sized(EN, 2500, EN_FILL)))
        self.assert_r22(out, "fail", 1)
        self.assert_numbers(out, 2500, 2000)

    def test_pr_cannot_raise_its_own_limit(self):
        """A PR whose own commit sets 3,000 is still judged by the merge base's 2,000."""
        out = check("raised", DESIGN, body(en=sized(EN, 2500, EN_FILL)))
        self.assert_r22(out, "fail", 1)
        self.assert_numbers(out, 2500, 2000)

    def test_limit_comes_from_the_merge_base_not_mains_tip(self):
        """``main`` raised the limit after the branch started: the merge base's 2,000 holds."""
        out = check("main-moved", DESIGN, body(en=sized(EN, 2500, EN_FILL)))
        self.assert_r22(out, "fail", 1)
        self.assert_numbers(out, 2500, 2000)

    def test_bad_summary_table_exits_two(self):
        """A bad ``max_chars`` or an unknown key in ``[summary]`` stops pr and commit (exit 2)."""
        bad = {
            "zero": "[summary]\nmax_chars = 0\n",
            "negative": "[summary]\nmax_chars = -1\n",
            "a string": '[summary]\nmax_chars = "2000"\n',
            "a fraction": "[summary]\nmax_chars = 2000.5\n",
            "a boolean": "[summary]\nmax_chars = true\n",
            "an unknown key": "[summary]\nmax_length = 2000\n",
            "an unknown key beside max_chars": "[summary]\nmax_chars = 2000\nextra = 1\n",
        }
        outs = {label: (run_pr(DESIGN, CHANGES, config=make_config(extra=text), body=body()),
                        commit_with(make_config(extra=text)))
                for label, text in bad.items()}
        for label, (pr_out, commit_out) in outs.items():
            with self.subTest(config=label):
                self.assert_exit(pr_out, 2)
                self.assert_exit(commit_out, 2)

    def test_valid_summary_table_is_read(self):
        """``max_chars = 2000`` written out is accepted by pr and commit."""
        config = make_config(extra="[summary]\nmax_chars = 2000\n")
        pr_out = run_pr(DESIGN, CHANGES, config=config, body=body())
        commit_out = commit_with(config)
        self.assert_r22(pr_out, "pass", 0)
        self.assert_exit(commit_out, 0)


class LineEndingTests(R22Case):
    """CRLF line endings in the description give the same result as LF."""

    CASES = {
        "the example": (body(), "pass"),
        "English part of 2,000 characters": (body(en=sized(EN, 2000, EN_FILL)), "pass"),
        "Chinese part of 2,000 characters": (body(zh=sized(ZH, 2000, ZH_FILL)), "pass"),
        "English part of 2,001 characters": (body(en=sized(EN, 2001, EN_FILL)), "fail"),
        "nothing to decide": (body(zh=swap(ZH, 1, ZH_NOTHING), en=swap(EN, 1, EN_NOTHING)),
                              "pass"),
        "an ID": (with_paragraph("en", 0, "This answers Q16 for you."), "fail"),
        "English first": (language(EN_TITLE, EN) + "\n" + language(ZH_TITLE, ZH) + "\n" + REST,
                          "fail"),
    }

    def test_crlf_gives_the_lf_result(self):
        """Same result and same detail lines with either line ending."""
        outs = {label: (check("default", DESIGN, text), check("default", DESIGN, crlf(text)))
                for label, (text, _) in self.CASES.items()}
        for label, (lf_out, crlf_out) in outs.items():
            expected = self.CASES[label][1]
            with self.subTest(case=label):
                self.assert_r22(lf_out, expected)
                self.assert_r22(crlf_out, expected)
                self.assertEqual([d.get("line") for d in crlf_out.details("R22")],
                                 [d.get("line") for d in lf_out.details("R22")],
                                 crlf_out.describe())
                self.assertEqual(len(crlf_out.details("R22")), len(lf_out.details("R22")),
                                 crlf_out.describe())


if __name__ == "__main__":
    unittest.main()
