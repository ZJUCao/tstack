"""Builders for Python source text and architecture documents.

These functions only produce strings. They never touch git or run the
checker. Line counting helpers let tests find the line of a definition.
"""

from __future__ import annotations

from typing import NamedTuple, Optional, Sequence

CJK = {
    "ideograph": "中",
    "ideograph extension A": "㐀",
    "compatibility ideograph": "豈",
    "ideograph extension B": "\U00020000",
    "hiragana": "あ",
    "katakana": "ア",
    "hangul syllable": "한",
    "hangul jamo": "ᄀ",
    "CJK punctuation": "。",
    "fullwidth comma": "，",
    "halfwidth katakana": "ｱ",
}
ALLOWED_TEXT = {
    "accented letter": "café",
    "arrow": "a → b",
    "smart quotes and dash": "“quoted” — done…",
    "copyright": "© 2026",
}


def code_lines(count: int, indent: int = 4, prefix: str = "v") -> str:
    """Builds ``count`` lines of code, each a distinct assignment.

    Args:
        count: Number of lines.
        indent: Number of leading spaces.
        prefix: Variable name prefix.

    Returns:
        The lines, each ending in a line feed.
    """
    pad = " " * indent
    return "".join(f"{pad}{prefix}{i} = {i}\n" for i in range(count))


def _docstring(text: str, inner: str) -> str:
    """Builds the lines of a docstring.

    Args:
        text: Docstring text. Lines after the first are written as given.
        inner: Indentation of the docstring.

    Returns:
        The docstring lines, each ending in a line feed.
    """
    rows = text.split("\n")
    if len(rows) == 1:
        return f'{inner}"""{text}"""\n'
    out = [f'{inner}"""{rows[0]}\n']
    for row in rows[1:]:
        out.append((f"{inner}{row}" if row else "") + "\n")
    out.append(f'{inner}"""\n')
    return "".join(out)


def func(
    name: str = "f",
    code: int = 3,
    doc: Optional[str] = "Does it.",
    decorators: Sequence[str] = (),
    is_async: bool = False,
    indent: int = 0,
    blank: int = 0,
    comment: int = 0,
    extra: str = "",
) -> str:
    """Builds a function definition.

    Args:
        name: Function name.
        code: Number of code lines in the body.
        doc: Docstring text, or None for no docstring.
        decorators: Decorator texts without the ``@``.
        is_async: Whether to write ``async def``.
        indent: Number of leading spaces of the definition.
        blank: Number of blank lines added after the code.
        comment: Number of comment-only lines added after the code.
        extra: Raw lines (already indented) added before the code lines.

    Returns:
        The definition, ending in a line feed.
    """
    pad = " " * indent
    inner = " " * (indent + 4)
    out = [f"{pad}@{d}\n" for d in decorators]
    out.append(f"{pad}{'async ' if is_async else ''}def {name}():\n")
    if doc is not None:
        out.append(_docstring(doc, inner))
    out.append(extra)
    out.append(code_lines(code, indent + 4))
    out.append("\n" * blank)
    out.append(f"{inner}# note\n" * comment)
    if not code and not extra and doc is None:
        out.append(f"{inner}pass\n")
    return "".join(out)


def klass(name: str = "C", body: str = "", doc: Optional[str] = "A class.") -> str:
    """Builds a class definition.

    Args:
        name: Class name.
        body: Raw text of the members, already indented by 4 spaces.
        doc: Docstring text, or None for no docstring.

    Returns:
        The definition, ending in a line feed.
    """
    head = f"class {name}:\n"
    if doc is not None:
        head += _docstring(doc, "    ")
    return head + (body or ("    pass\n" if doc is None else ""))


def module(*chunks: str) -> str:
    """Joins definitions with two blank lines between them.

    Args:
        *chunks: Texts that each end in a line feed.

    Returns:
        The module text.
    """
    return "\n\n".join(chunks)


def line_of(text: str, needle: str, nth: int = 1) -> int:
    """Finds the 1-based line number of a line containing a text.

    Args:
        text: The file text.
        needle: Text to look for.
        nth: Which matching line to return, counting from 1.

    Returns:
        The line number.

    Raises:
        ValueError: If there are fewer than ``nth`` matching lines.
    """
    seen = 0
    for number, row in enumerate(text.split("\n"), start=1):
        if needle in row:
            seen += 1
            if seen == nth:
                return number
    raise ValueError(f"{needle!r} not found")


def edit_line(text: str, old: str, new: str) -> str:
    """Replaces the one line whose stripped text equals ``old``.

    Args:
        text: The file text.
        old: Stripped text of the line to change.
        new: Replacement text, put at the same indentation.

    Returns:
        The edited text.

    Raises:
        ValueError: If no line matches.
    """
    rows = text.split("\n")
    for index, row in enumerate(rows):
        if row.strip() == old:
            rows[index] = row[: len(row) - len(row.lstrip())] + new
            return "\n".join(rows)
    raise ValueError(f"{old!r} not found")


class Mod(NamedTuple):
    """One row of the architecture module table.

    Attributes:
        name: Module name.
        owns: Path patterns in the Owns column.
        ext: Path patterns in the External interfaces column.
        deps: Module names in May depend on. Empty means ``None``.
    """

    name: str
    owns: Sequence[str]
    ext: Sequence[str]
    deps: Sequence[str] = ()


def _cell(patterns: Sequence[str], lead: str) -> str:
    """Builds a cell of backticked patterns with a plain-text lead-in.

    Args:
        patterns: Path patterns.
        lead: Text written before the patterns.

    Returns:
        The cell text.
    """
    return lead + ", ".join(f"`{p}`" for p in patterns)


def arch_doc(
    mods: Sequence[Mod],
    heading: str = "## 3. Modules",
    columns: Sequence[str] = ("Module", "Owns", "External interfaces", "May depend on"),
    notes: bool = False,
) -> str:
    """Builds ``docs/architecture.md`` with a module table.

    Args:
        mods: The table rows.
        heading: Heading line above the table.
        columns: Header names in column order.
        notes: Whether to add a ``Notes`` column with plain text.

    Returns:
        The document text.
    """
    names = list(columns) + (["Notes"] if notes else [])
    out = ["# Architecture", "", "## 1. Overview", "", "Text.", "", heading, ""]
    out.append("| " + " | ".join(names) + " |")
    out.append("| " + " | ".join("---" for _ in names) + " |")
    for mod in mods:
        cells = {
            "Module": mod.name,
            "Owns": _cell(mod.owns, "Logic of the module: "),
            "External interfaces": _cell(mod.ext, ""),
            "May depend on": ", ".join(mod.deps) if mod.deps else "None",
            "Notes": "free text",
        }
        out.append("| " + " | ".join(cells[n] for n in names) + " |")
    out += ["", "## 4. Dependency rules", "", "Text.", ""]
    return "\n".join(out)


CORE = Mod("core", ["core/**"], ["core/api.py"])
STORE = Mod("store", ["store/**"], ["store/api.py"], ["core"])
UI = Mod("ui", ["ui/**"], ["ui/api.py"], ["store"])
STD_MODS = (CORE, STORE, UI)


def std_base(mods: Sequence[Mod] = STD_MODS) -> dict:
    """Builds the base files of a small three-module project.

    Args:
        mods: Rows of the architecture table.

    Returns:
        Paths mapped to text, including ``docs/architecture.md``.
    """
    files = {"docs/architecture.md": arch_doc(mods), "scripts/helper.py": "H = 1\n"}
    for name in ("core", "store", "ui"):
        files[f"{name}/api.py"] = "API = 1\n"
        files[f"{name}/internal.py"] = "INTERNAL = 1\n"
    return files
