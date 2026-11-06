"""The Python adapter: functions, classes, comments, and imports of one file.

Uses only ast and tokenize from the standard library (F03 design section 6).
"""

import ast
import io
import tokenize
from dataclasses import dataclass, field

_NOT_CODE = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
             tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER}


class ParseError(Exception):
    """Raised when a file is not valid Python."""


@dataclass
class Unit:
    """A function, method, or class.

    Attributes:
        kind: "function" or "class".
        name: Its name.
        line: The line of its def or class keyword.
        start: Its first line, decorators included.
        end: Its last line.
        code_lines: Code lines in a function's body, docstring excluded.
        has_doc: Whether it has a docstring.
    """

    kind: str
    name: str
    line: int
    start: int
    end: int
    code_lines: int = 0
    has_doc: bool = False


@dataclass
class Import:
    """One import statement.

    Attributes:
        line: Its line.
        module: The module named after "import" or "from", or "" for "from . import x".
        names: The names after "import" in a from-import, else empty.
        level: Number of leading dots in a relative import.
    """

    line: int
    module: str
    names: list[str] = field(default_factory=list)
    level: int = 0


@dataclass
class PyFile:
    """What the checks need from one Python file.

    Attributes:
        units: Every function, method, and class.
        texts: (line, text) for every comment and docstring line.
        imports: Every import statement.
    """

    units: list[Unit]
    texts: list[tuple[int, str]]
    imports: list[Import]


def _docstring_node(node: ast.AST) -> ast.Expr | None:
    """Returns a node's docstring expression, or None."""
    body = getattr(node, "body", None)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        return body[0]
    return None


def _code_lines(source: str, doc_lines: set[int]) -> set[int]:
    """Finds the lines that hold code: not blank, not comments, not docstrings."""
    lines = set()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in _NOT_CODE:
            continue
        span = set(range(tok.start[0], tok.end[0] + 1))
        if tok.type == tokenize.STRING and span <= doc_lines:
            continue
        lines |= span
    return lines


def _comments(source: str) -> list[tuple[int, str]]:
    """Lists every comment with its line."""
    return [(tok.start[0], tok.string)
            for tok in tokenize.generate_tokens(io.StringIO(source).readline)
            if tok.type == tokenize.COMMENT]


def _doc_texts(tree: ast.AST, source_lines: list[str]) -> tuple[set[int], list[tuple[int, str]]]:
    """Finds docstring lines and their text for the module, classes, and functions."""
    lines, texts = set(), []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = _docstring_node(node)
        if doc is None:
            continue
        for number in range(doc.lineno, doc.end_lineno + 1):
            lines.add(number)
            texts.append((number, source_lines[number - 1] if number <= len(source_lines) else ""))
    return lines, texts


def _unit(node: ast.AST, code: set[int]) -> Unit:
    """Builds a Unit from a function or class node; code lines already exclude docstrings."""
    start = min([node.lineno] + [d.lineno for d in node.decorator_list])
    is_class = isinstance(node, ast.ClassDef)
    unit = Unit("class" if is_class else "function", node.name, node.lineno, start,
                node.end_lineno, has_doc=_docstring_node(node) is not None)
    if not is_class:
        body = set(range(node.body[0].lineno, node.end_lineno + 1))
        unit.code_lines = len(body & code)
    return unit


def _imports(tree: ast.AST) -> list[Import]:
    """Lists every import statement in the file."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [Import(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            found.append(Import(node.lineno, node.module or "",
                                [alias.name for alias in node.names], node.level))
    return found


def analyze(source: str) -> PyFile:
    """Reads one Python file.

    Args:
        source: The file's text.

    Returns:
        Its functions, classes, comment and docstring lines, and imports.

    Raises:
        ParseError: The text is not valid Python.
    """
    try:
        tree = ast.parse(source)
        doc_lines, doc_texts = _doc_texts(tree, source.splitlines())
        code = _code_lines(source, doc_lines)
        comments = _comments(source)
    except (SyntaxError, tokenize.TokenError, ValueError) as exc:
        raise ParseError(str(exc)) from exc
    kinds = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    units = [_unit(n, code) for n in ast.walk(tree) if isinstance(n, kinds)]
    units.sort(key=lambda u: u.line)
    return PyFile(units, sorted(comments + doc_texts), _imports(tree))
