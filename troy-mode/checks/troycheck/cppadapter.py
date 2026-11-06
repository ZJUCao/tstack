"""The C/C++ adapter: functions, comments, and includes of one file (F03 design 6 and 7).

lizard finds the functions and their line ranges. troy-check's own scanner
finds comments, string and character literals, and #include lines.
"""

import re
from dataclasses import dataclass

from .pyadapter import Unit

EXTENSIONS = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")
_INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"\n]*)"')
_RAW_PREFIXES = ("R", "u8R", "uR", "UR", "LR")
_TOKEN_TAIL = re.compile(r"[A-Za-z0-9_.']*$")
_IDENT_TAIL = re.compile(r"[A-Za-z0-9_]*$")
_RAW_DELIMITER = re.compile(r'[^\s()\\"]{0,16}\(')


class AdapterError(Exception):
    """Raised when the C/C++ adapter cannot run because lizard is missing."""


def require_lizard():
    """Imports lizard, which finds C and C++ functions.

    Returns:
        The lizard module.

    Raises:
        AdapterError: lizard is not installed for this Python.
    """
    try:
        import lizard  # noqa: PLC0415  (only C/C++ projects need it)
    except ImportError as exc:
        raise AdapterError(
            "C/C++ projects need lizard. Run troy-check with the project environment's "
            "Python, where requirements-tools.lock installs it.") from exc
    return lizard


@dataclass
class Scan:
    """What the scanner finds in one file.

    Attributes:
        mask: The file's lines with comments blanked and literal contents
            replaced by "_", so every column stays where it was.
        comments: (line, text) for every line that holds comment text.
        code: Lines that hold code: not blank and not only comments.
        includes: (line, path) for every #include "path" outside comments.
    """

    mask: list[str]
    comments: list[tuple[int, str]]
    code: set[int]
    includes: list[tuple[int, str]]


@dataclass
class CppFile:
    """What the checks need from one C or C++ file.

    Attributes:
        units: Every function lizard finds. code_lines counts body lines.
        texts: (line, text) for every comment line, doc comments included.
        includes: (line, path) for every #include "path".
    """

    units: list[Unit]
    texts: list[tuple[int, str]]
    includes: list[tuple[int, str]]


class _Scanner:
    """Walks a C or C++ file once, character by character."""

    def __init__(self, source: str) -> None:
        """Starts a scan of the given text."""
        self.src = source
        self.i = 0
        self.line = 1
        self.out: list[str] = []
        self.comment: dict[int, list[str]] = {}

    def emit(self, kind: str) -> None:
        """Copies the current character to the mask as code, comment, or literal."""
        ch = self.src[self.i]
        self.i += 1
        if ch == "\n":
            self.out.append(ch)
            self.line += 1
        elif kind == "comment":
            self.out.append(" ")
            self.comment.setdefault(self.line, []).append(ch)
        else:
            self.out.append("_" if kind == "literal" else ch)

    def peek(self, offset: int = 0) -> str:
        """Returns the character at the given offset from the current one, or ""."""
        index = self.i + offset
        return self.src[index] if index < len(self.src) else ""

    def run(self) -> None:
        """Scans the whole file."""
        while self.i < len(self.src):
            ch, nxt = self.peek(), self.peek(1)
            if ch == "/" and nxt == "/":
                self.line_comment()
            elif ch == "/" and nxt == "*":
                self.block_comment()
            elif ch == '"':
                self.string()
            elif ch == "'" and not self.digit_separator():
                self.quoted("'")
            else:
                self.emit("code")

    def line_comment(self) -> None:
        """Scans a // comment, which a backslash at the line's end continues."""
        while self.i < len(self.src) and self.peek() != "\n":
            if self.peek() == "\\" and self.peek(1) == "\n":
                self.emit("comment")
            self.emit("comment")

    def block_comment(self) -> None:
        """Scans a /* */ comment; an unterminated one runs to the end of the file."""
        self.emit("comment")
        self.emit("comment")
        while self.i < len(self.src):
            if self.peek() == "*" and self.peek(1) == "/":
                self.emit("comment")
                self.emit("comment")
                return
            self.emit("comment")

    def digit_separator(self) -> bool:
        """Tells whether the current ' separates digits, as in 1'000'000."""
        token = _TOKEN_TAIL.search(self.src, max(0, self.i - 64), self.i).group()
        if not token:
            return False
        return token[0].isdigit() or (token[0] == "." and token[1:2].isdigit())

    def string(self) -> None:
        """Scans a string literal, raw or not."""
        prefix = _IDENT_TAIL.search(self.src, max(0, self.i - 8), self.i).group()
        delimiter = _RAW_DELIMITER.match(self.src, self.i + 1)
        if prefix in _RAW_PREFIXES and delimiter:
            end = ")" + delimiter.group()[:-1] + '"'
            close = self.src.find(end, delimiter.end())
            stop = len(self.src) if close < 0 else close + len(end) - 1
            self.emit("code")
            while self.i < stop:
                self.emit("literal")
            if self.i < len(self.src):
                self.emit("code")
            return
        self.quoted('"')

    def quoted(self, quote: str) -> None:
        """Scans a "..." or '...' literal; a line end without a closing quote ends it."""
        self.emit("code")
        while self.i < len(self.src) and self.peek() != "\n":
            if self.peek() == quote:
                self.emit("code")
                return
            if self.peek() == "\\" and self.peek(1):
                self.emit("literal")
            self.emit("literal")


def scan(source: str) -> Scan:
    """Finds the comments, code lines, and includes of a C or C++ file.

    Args:
        source: The file's text.

    Returns:
        The scan of the file.
    """
    scanner = _Scanner(source)
    scanner.run()
    mask = "".join(scanner.out).split("\n")
    lines = source.split("\n")
    includes = []
    for number, text in enumerate(mask, 1):
        match = _INCLUDE.match(text)
        if match:
            includes.append((number, lines[number - 1][match.start(1):match.end(1)]))
    comments = sorted((n, "".join(chars)) for n, chars in scanner.comment.items())
    code = {n for n, text in enumerate(mask, 1) if text.strip()}
    return Scan(mask, comments, code, includes)


def _opening_line(mask: list[str], start: int, end: int) -> int:
    """Finds the line of the { that matches the last } on the end line.

    Returns:
        That line, or start when no matching brace is found.
    """
    column = mask[end - 1].rfind("}") if end <= len(mask) else -1
    if column < 0:
        return start
    depth = 0
    for number in range(end, start - 1, -1):
        text = mask[number - 1]
        stop = column if number == end else len(text) - 1
        for ch in reversed(text[:stop + 1]):
            depth += (ch == "}") - (ch == "{")
            if depth == 0 and ch == "{":
                return number
    return start


def body_lines(found: Scan, start: int, end: int) -> int:
    """Counts the code lines strictly between a function body's braces (R04).

    Args:
        found: The file's scan.
        start: The function's first line, as lizard reports it.
        end: The line of its closing brace.

    Returns:
        The number of lines between the brace lines that hold code.
    """
    opening = _opening_line(found.mask, start, end)
    return sum(1 for number in range(opening + 1, end) if number in found.code)


def analyze(path: str, source: str) -> CppFile:
    """Reads one C or C++ file.

    Args:
        path: The file's path. lizard picks its reader by the extension.
        source: The file's text.

    Returns:
        Its functions, comment lines, and includes.

    Raises:
        AdapterError: lizard is not installed.
    """
    lizard = require_lizard()
    found = scan(source)
    info = lizard.analyze_file.analyze_source_code(path, source)
    units = [Unit("function", f.name, f.start_line, f.start_line, f.end_line,
                  code_lines=body_lines(found, f.start_line, f.end_line), has_doc=True)
             for f in info.function_list]
    return CppFile(units, found.comments, found.includes)
