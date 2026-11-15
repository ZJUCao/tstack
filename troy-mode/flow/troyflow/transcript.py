"""Reads a prototype's terminal transcripts (F12 design 5.3).

A transcript is a fenced block whose first line that is not blank starts
with "PS> ". Its section is the nearest heading above it, and every block of
one section runs in order in one state. Other fenced blocks, such as a saved
file, are kept so that a run file's `files` can compare one.
"""

import re
from dataclasses import dataclass, field

PROMPT = "PS> "
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_CLOSING_HASHES = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")
_EXIT = re.compile(r"\$lastexitcode", re.IGNORECASE)
_ENV = re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\"[^\"]*\"|'[^']*')\s*$",
                  re.IGNORECASE)
_GET_CONTENT = re.compile(r"get-content\s+(.+)$", re.IGNORECASE)
_OPERATORS = ("|", ">", "<", ";", "&&", "||")


@dataclass
class Line:
    """One "PS> " line of a transcript and the output under it.

    Attributes:
        number: The line's number in the prototype, from 1.
        typed: The text after "PS> ", without trailing spaces.
        output: The lines after it, up to the next prompt or the block's end,
            without blank lines at the end.
    """

    number: int
    typed: str
    output: list[str]


@dataclass
class Section:
    """One section of a prototype.

    Attributes:
        key: The heading as written, with " (2)" and so on for a repeated one.
        lines: The prompt lines of its transcripts, in order.
        blocks: The text of its other fenced blocks, in order.
    """

    key: str
    lines: list[Line] = field(default_factory=list)
    blocks: list[list[str]] = field(default_factory=list)

    def typed_lines(self) -> set[str]:
        """Returns the set of typed lines, for checking a run file's `typed` values."""
        return {line.typed for line in self.lines}


@dataclass
class Prototype:
    """A prototype read as transcripts.

    Attributes:
        sections: Every section, in order, with or without a transcript.
    """

    sections: list[Section]

    def has_transcript(self) -> bool:
        """Tells whether any section has a transcript."""
        return any(s.lines for s in self.sections)

    def section(self, key: str) -> Section | None:
        """Returns the section with a key, or None."""
        return next((s for s in self.sections if s.key == key), None)


def _heading_text(match: re.Match) -> str:
    """The text of an ATX heading without its closing hashes."""
    text = match.group(2) or ""
    return _CLOSING_HASHES.sub("", text).strip()


def _strip_end(lines: list[str]) -> list[str]:
    """Removes blank lines at the end."""
    end = len(lines)
    while end and not lines[end - 1].strip():
        end -= 1
    return lines[:end]


def _transcript(body: list[tuple[int, str]]) -> list[Line] | None:
    """Reads a fenced block's lines as a transcript, or None when it is not one."""
    first = next((text for _, text in body if text.strip()), None)
    if first is None or not first.startswith(PROMPT):
        return None
    lines: list[Line] = []
    for number, text in body:
        if text.startswith(PROMPT):
            lines.append(Line(number, text[len(PROMPT):].rstrip(), []))
        elif lines:
            lines[-1].output.append(text)
    for line in lines:
        line.output = _strip_end(line.output)
    return lines


def read_prototype(text: str) -> Prototype:
    """Reads a prototype's sections, transcripts, and other fenced blocks.

    Args:
        text: The prototype's Markdown text.

    Returns:
        The prototype. Text before any heading belongs to the section "".
    """
    rows = text.replace("\r\n", "\n").split("\n")
    sections = [Section("")]
    seen: dict[str, int] = {}
    fence: str | None = None
    body: list[tuple[int, str]] = []
    for number, row in enumerate(rows, start=1):
        if fence is not None:
            closing = _FENCE.match(row)
            if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= len(fence) \
                    and not row.strip()[len(closing.group(1)):].strip():
                _add_block(sections[-1], body)
                fence, body = None, []
            else:
                body.append((number, row))
            continue
        opening = _FENCE.match(row)
        if opening:
            fence, body = opening.group(1), []
            continue
        heading = _HEADING.match(row)
        if heading:
            name = _heading_text(heading)
            seen[name] = seen.get(name, 0) + 1
            sections.append(Section(name if seen[name] == 1 else f"{name} ({seen[name]})"))
    if fence is not None:
        _add_block(sections[-1], body)
    if not sections[0].lines and not sections[0].blocks:
        sections.pop(0)
    return Prototype(sections)


def _add_block(section: Section, body: list[tuple[int, str]]) -> None:
    """Adds a fenced block to its section as a transcript or a plain block."""
    lines = _transcript(body)
    if lines is None:
        section.blocks.append([text for _, text in body])
    else:
        section.lines.extend(lines)


def split_words(text: str) -> list[str]:
    """Splits a command line at spaces; "..." and '...' keep text together.

    The quotes are removed, and an empty pair of quotes gives an empty word.
    """
    words: list[str] = []
    current: list[str] = []
    started = False
    quote: str | None = None
    for char in text:
        if quote:
            if char == quote:
                quote = None
            else:
                current.append(char)
        elif char in "\"'":
            quote, started = char, True
        elif char in " \t":
            if started:
                words.append("".join(current))
                current, started = [], False
        else:
            current.append(char)
            started = True
    if started:
        words.append("".join(current))
    return words


def has_operator(text: str) -> bool:
    """Tells whether a line holds a pipe, a redirection, or a command separator outside quotes."""
    quote: str | None = None
    outside: list[str] = []
    for char in text:
        if quote:
            if char == quote:
                quote = None
            outside.append(" ")
        elif char in "\"'":
            quote = char
            outside.append(" ")
        else:
            outside.append(char)
    bare = "".join(outside)
    return any(op in bare for op in _OPERATORS)


@dataclass
class Kind:
    """What a typed line is.

    Attributes:
        kind: "exit", "env", "get-content", "program", or "other".
        name: The variable's name for "env", the program's name for "program".
        value: The variable's value for "env", the path for "get-content".
        words: The arguments after the program's name, for "program".
    """

    kind: str
    name: str = ""
    value: str = ""
    words: list[str] = field(default_factory=list)


def classify(typed: str, programs: set[str]) -> Kind:
    """Tells what a typed line does (design 5.3).

    Args:
        typed: The text after "PS> ".
        programs: The project's program names: console scripts and [programs].

    Returns:
        The line's kind.
    """
    text = typed.strip()
    if _EXIT.fullmatch(text):
        return Kind("exit")
    env = _ENV.fullmatch(text)
    if env:
        return Kind("env", env.group(1), env.group(2)[1:-1])
    if has_operator(text):
        return Kind("other")
    content = _GET_CONTENT.fullmatch(text)
    if content:
        words = split_words(content.group(1))
        return Kind("get-content", value=words[0]) if len(words) == 1 else Kind("other")
    words = split_words(text)
    if words and words[0] in programs:
        return Kind("program", words[0], words=words[1:])
    return Kind("other")
