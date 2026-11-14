"""R22: the summary for Troy at the top of a PR description (F14 design 6.1)."""

import re
from dataclasses import dataclass, field

from .context import PrContext
from .report import FAIL, PASS, SKIP, Detail, Result

ZH = "zh-CN"
EN = "en"
HEADINGS = {ZH: "## 给 Troy 的摘要", EN: "## Summary for Troy"}
NAMES = {ZH: "Chinese", EN: "English"}
PARTS = {
    ZH: ("### 对你有什么变化", "### 需要你决定的事", "### 风险"),
    EN: ("### What changes for you", "### What you decide", "### Risks"),
}
DECIDE = 1
NOTHING = {ZH: "没有需要你决定的事。", EN: "Nothing to decide."}
RECOMMENDED = {ZH: ("推荐：", "推荐:"), EN: ("Recommended:",)}
DOCS_SUMMARIES = ("Add the requirements", "Change the requirements", "Add the architecture",
                  "Change the architecture")

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(`+)(?!`).+?(?<!`)\1(?!`)")
_ITEM = re.compile(r"^\d+\.(?:\s|$)")
_CHINESE = re.compile("[㐀-䶿一-鿿豈-﫿\U00020000-\U0003134f]")
# Internal IDs (design 6.1). An ID matches only with no ASCII letter or digit
# right before or after it, so "F10" and "PR03X" do not match and "见R03" does.
_ID_KINDS = (
    ("rule", r"[RP]\d{2}"),
    ("decision", r"D\d{1,3}"),
    ("open question", r"Q\d{1,2}"),
    ("test case", r"[FB]\d+-T\d+"),
    ("scenario", r"v\d+(?:\.\d+)+-S\d+"),
    ("ADR", r"ADR-\d+"),
    ("performance target", r"PT\d+"),
    ("role task", r"(?:AR|IF|TM|DV|TE|CR|PM)\d"),
)
_ID = re.compile("(?<![A-Za-z0-9])(?:" + "|".join(f"(?P<k{i}>{pattern})" for i, (_, pattern)
                                                  in enumerate(_ID_KINDS)) + ")(?![A-Za-z0-9])")


@dataclass
class Line:
    """One line of the description.

    Attributes:
        number: 1-based line number in the description.
        text: The line without its line ending.
        code: True inside a fenced code block, fences included.
    """

    number: int
    text: str
    code: bool


@dataclass
class Part:
    """One language's summary: the lines under its ## heading.

    Attributes:
        lang: ZH or EN.
        lines: The lines after the ## heading, up to the next ## heading.
        sections: (### heading, its lines) pairs, in order.
    """

    lang: str
    lines: list[Line]
    sections: list[tuple[Line, list[Line]]] = field(default_factory=list)


def needs_summary(ctx: PrContext) -> bool:
    """Tells whether the PR's title asks for a summary (design 6.1, D132).

    Args:
        ctx: The PR under check.

    Returns:
        True for a design or test plan PR, and for a [docs] PR that adds or
        changes the requirements or the architecture.
    """
    title = ctx.title
    if title is None:
        return False
    if title.kind in ("design", "test-plan"):
        return True
    return title.kind == "docs" and title.summary.startswith(DOCS_SUMMARIES)


def read_lines(body: str) -> list[Line]:
    """Splits a description into lines and marks those in fenced code blocks.

    Args:
        body: The PR description, with any line endings.

    Returns:
        The lines, numbered from 1.
    """
    lines, fence = [], None
    for number, text in enumerate(body.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1):
        if fence is None:
            match = _FENCE.match(text)
            fence = match.group(1) if match else None
            lines.append(Line(number, text, fence is not None))
            continue
        lines.append(Line(number, text, True))
        if _closes(text, fence):
            fence = None
    return lines


def _closes(text: str, fence: str) -> bool:
    """Tells whether a line closes the fenced code block that `fence` opened."""
    match = _FENCE.match(text)
    return (match is not None and match.group(1)[0] == fence[0]
            and len(match.group(1)) >= len(fence) and not text.strip().strip(fence[0]))


def _is_h2(line: Line) -> bool:
    """Tells whether a line is a ## heading outside code."""
    return not line.code and line.text.startswith("## ")


def _is_h3(line: Line) -> bool:
    """Tells whether a line is a ### heading outside code."""
    return not line.code and line.text.startswith("### ")


def find_part(lines: list[Line], lang: str) -> Part | None:
    """Finds one language's summary by its ## heading.

    Args:
        lines: The description's lines.
        lang: ZH or EN.

    Returns:
        The part, or None when the description has no such heading.
    """
    start = next((i for i, line in enumerate(lines)
                  if _is_h2(line) and line.text.rstrip() == HEADINGS[lang]), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if _is_h2(lines[i])), len(lines))
    part = Part(lang, lines[start + 1:end])
    for line in part.lines:
        if _is_h3(line):
            part.sections.append((line, []))
        elif part.sections:
            part.sections[-1][1].append(line)
    return part


def _text(lines: list[Line]) -> str:
    """Joins lines with blank space at both ends removed."""
    return "\n".join(line.text for line in lines).strip()


def check_order(lines: list[Line]) -> list[str]:
    """The Order check: the Chinese heading first, then the English heading."""
    first = next((line for line in lines if line.text.strip()), None)
    if first is None or first.text.rstrip() != HEADINGS[ZH]:
        return [f"Order: the description must start with \"{HEADINGS[ZH]}\"."]
    following = next((line for line in lines if _is_h2(line) and line.number > first.number),
                     None)
    if following is None or following.text.rstrip() != HEADINGS[EN]:
        return [f"Order: the next ## heading after \"{HEADINGS[ZH]}\" must be "
                f"\"{HEADINGS[EN]}\"."]
    return []


def check_parts(part: Part) -> list[str]:
    """The Parts check: exactly the three ### headings, in order, each with text."""
    found = [heading.text.rstrip() for heading, _ in part.sections]
    expected = list(PARTS[part.lang])
    if found != expected:
        return [f"Parts: the {NAMES[part.lang]} part must have exactly the headings "
                f"{', '.join(expected)}, in that order; it has {', '.join(found) or 'none'}."]
    empty = [heading.text.rstrip() for heading, body in part.sections if not _text(body)]
    if empty:
        return [f"Parts: no text under {', '.join(empty)} in the {NAMES[part.lang]} part."]
    return []


def check_length(part: Part, limit: int) -> list[str]:
    """The Length check: at most `limit` characters, Markdown included (design 3.3)."""
    count = len(_text(part.lines))
    if count > limit:
        return [f"Length: the {NAMES[part.lang]} part has {count:,} characters; the limit is "
                f"{limit:,}."]
    return []


def _section(part: Part, index: int) -> list[Line] | None:
    """The lines under one of the three expected ### headings, or None."""
    for heading, body in part.sections:
        if heading.text.rstrip() == PARTS[part.lang][index]:
            return body
    return None


def decision_items(body: list[Line]) -> list[str]:
    """Splits the decide section into its numbered items.

    Args:
        body: The lines under the decide heading.

    Returns:
        Each item's text: its numbered line and the lines after it, up to the
        next numbered item.
    """
    items: list[list[str]] = []
    for line in body:
        if not line.code and _ITEM.match(line.text):
            items.append([line.text])
        elif items:
            items[-1].append(line.text)
    return ["\n".join(item) for item in items]


def _items(count: int) -> str:
    """Returns "item" or "items" for a count."""
    return "item" if count == 1 else "items"


def check_decisions(parts: dict[str, Part]) -> list[str]:
    """The Decisions check: a recommendation per item, or the nothing text; equal counts."""
    problems, counts = [], {}
    for lang, part in parts.items():
        body = _section(part, DECIDE)
        if body is None or not _text(body):
            continue
        items = decision_items(body)
        counts[lang] = len(items)
        marks = RECOMMENDED[lang]
        missing = [str(n) for n, item in enumerate(items, 1)
                   if not any(mark in item for mark in marks)]
        if missing:
            problems.append(f"Decisions: no \"{marks[0]}\" in {_items(len(missing))} "
                            f"{', '.join(missing)} of the {NAMES[lang]} part.")
        if not items and _text(body) != NOTHING[lang]:
            problems.append(f"Decisions: the {NAMES[lang]} part has no numbered item, so its "
                            f"text must be \"{NOTHING[lang]}\"")
    if len(counts) == 2 and counts[ZH] != counts[EN]:
        problems.append(f"Decisions: the Chinese part has {counts[ZH]} numbered "
                        f"{_items(counts[ZH])} and the English part {counts[EN]}.")
    return problems


def check_chinese(part: Part) -> list[str]:
    """The Chinese check: each ### part of the Chinese summary holds a Chinese character."""
    bare = [heading.text.rstrip() for heading, body in part.sections
            if not _CHINESE.search(_text(body))]
    if bare:
        return [f"Chinese: no Chinese character under {', '.join(bare)}."]
    return []


def find_ids(part: Part) -> list[tuple[int, str, str]]:
    """Finds internal IDs outside inline code and code blocks.

    Args:
        part: One language's summary.

    Returns:
        (line number, ID, kind) for each ID, in order.
    """
    found = []
    for line in part.lines:
        if line.code:
            continue
        for match in _ID.finditer(_INLINE_CODE.sub(" ", line.text)):
            kind = _ID_KINDS[int(match.lastgroup[1:])][0]
            found.append((line.number, match.group(0), kind))
    return found


def check_r22(ctx: PrContext) -> Result:
    """Checks the summary for Troy that opens the PR's description (R22).

    Args:
        ctx: The PR under check.

    Returns:
        SKIP for a PR that needs no summary or has no description, FAIL with
        one detail per failing check (one per ID for the IDs check), and PASS
        otherwise.
    """
    if not needs_summary(ctx):
        return Result("R22", SKIP, "Not a PR that needs a summary.")
    if ctx.body is None:
        return Result("R22", SKIP, "No description given, so the summary is not checked.")
    lines = read_lines(ctx.body)
    limit = ctx.config.summary_max_chars
    problems = check_order(lines)
    parts = {lang: part for lang in (ZH, EN) if (part := find_part(lines, lang)) is not None}
    for part in parts.values():
        problems += check_parts(part)
        problems += check_length(part, limit)
    problems += check_decisions(parts)
    if ZH in parts:
        problems += check_chinese(parts[ZH])
    fails = [Detail(None, None, problem) for problem in problems]
    for part in parts.values():
        fails += [Detail(None, number, f"PR description line {number}: IDs: {found} is an "
                         f"internal ID ({kind}). Name the thing instead.")
                  for number, found, kind in find_ids(part)]
    if fails:
        return Result("R22", FAIL, f"The summary for Troy breaks {len(fails)} "
                      f"{'check' if len(fails) == 1 else 'checks'}.", fails)
    return Result("R22", PASS, f"The summary for Troy is in place, within {limit:,} characters "
                  "in each language.")
