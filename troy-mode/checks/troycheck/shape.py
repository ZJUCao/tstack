"""R04, R05, and R06: function length, doc comments, and file length (F03 design 6).

Following Q6, only functions that touch a changed line and only changed
files are checked.
"""

import re
from dataclasses import dataclass, field

from .classify import classify
from .context import PrContext
from .gitio import added_lines, read_blobs
from .pyadapter import ParseError, PyFile, Unit, analyze
from .report import FAIL, PASS, SKIP, WARN, Detail, Result
from .size import soft_limit_reason

CJK = re.compile("[ᄀ-ᇿ　-〿぀-ヿ㐀-䶿一-鿿"
                 "가-힯豈-﫿＀-￯\U00020000-\U0002a6df]")
CODE_CLASSES = ("source", "tests")


@dataclass
class CodeFiles:
    """The changed code files of a PR, read and analyzed once.

    Attributes:
        changed: Changed line numbers by path.
        analyzed: The adapter's view of each file that parsed.
        errors: One failing detail per file that did not parse.
    """

    changed: dict[str, set[int]] = field(default_factory=dict)
    analyzed: dict[str, PyFile] = field(default_factory=dict)
    errors: list[Detail] = field(default_factory=list)


def lang_skip(ctx: PrContext, rule: str) -> Result | None:
    """Returns a SKIP result when no adapter exists for the project's language.

    Args:
        ctx: The PR under check.
        rule: The rule ID to report.

    Returns:
        A SKIP result, or None when the Python adapter applies.
    """
    name = ctx.config.lang.get("name")
    if name is None:
        return Result(rule, SKIP, "No [lang] name in .troy-mode/config.toml.")
    if name != "python":
        return Result(rule, SKIP, "The C/C++ adapter comes in F03 part 4.")
    return None


def load_python(ctx: PrContext) -> CodeFiles:
    """Reads and analyzes the changed Python files in the source and tests classes.

    Args:
        ctx: The PR under check.

    Returns:
        The analyzed files and their changed lines.
    """
    paths = [c.path for c in ctx.changes if c.status != "D" and c.path.endswith(".py")
             and classify(c.path, ctx.config.paths) in CODE_CLASSES]
    files = CodeFiles(changed=added_lines(ctx.repo, ctx.base, ctx.head, paths))
    for path, text in sorted(read_blobs(ctx.repo, ctx.head, paths).items()):
        try:
            files.analyzed[path] = analyze(text)
        except ParseError as exc:
            files.errors.append(Detail(path, None, f"cannot be parsed as Python: {exc}"))
    return files


def _touched(unit: Unit, lines: set[int]) -> bool:
    """Tells whether a function or class contains a changed line."""
    return any(unit.start <= n <= unit.end for n in lines)


def check_r04(ctx: PrContext, files: CodeFiles | None) -> Result:
    """Checks that changed functions have at most the allowed body code lines (R04).

    Args:
        ctx: The PR under check.
        files: The analyzed changed files, or None without an adapter.

    Returns:
        SKIP without an adapter, FAIL per function over the limit, else PASS.
    """
    skip = lang_skip(ctx, "R04")
    if skip or files is None:
        return skip or Result("R04", SKIP, "No adapter.")
    limit = ctx.config.limits["function_lines"]
    fails, count = list(files.errors), 0
    for path, py in files.analyzed.items():
        for unit in py.units:
            if unit.kind != "function" or not _touched(unit, files.changed.get(path, set())):
                continue
            count += 1
            if unit.code_lines > limit:
                fails.append(Detail(path, unit.line,
                                    f"{unit.name} has {unit.code_lines} code lines, over {limit}"))
    if fails:
        return Result("R04", FAIL, f"{len(fails)} functions are too long.", fails)
    return Result("R04", PASS, f"{count} changed functions, all within {limit} code lines.")


def _doc_fails(path: str, py: PyFile, lines: set[int]) -> list[Detail]:
    """Finds missing docstrings and CJK text in one file's changed parts."""
    fails = [Detail(path, u.line, f"{u.kind} {u.name} has no docstring")
             for u in py.units if _touched(u, lines) and not u.has_doc]
    cjk_lines = sorted({n for n, text in py.texts if n in lines and CJK.search(text)})
    fails += [Detail(path, n, "comment or docstring holds Chinese, Japanese, or Korean text")
              for n in cjk_lines]
    return fails


def check_r05(ctx: PrContext, files: CodeFiles | None) -> Result:
    """Checks doc comments and English-only comments in changed code (R05).

    Args:
        ctx: The PR under check.
        files: The analyzed changed files, or None without an adapter.

    Returns:
        SKIP without an adapter. FAIL for a changed function or class with no
        docstring, or a changed comment or docstring line with CJK text.
    """
    skip = lang_skip(ctx, "R05")
    if skip or files is None:
        return skip or Result("R05", SKIP, "No adapter.")
    fails = list(files.errors)
    for path, py in files.analyzed.items():
        fails += _doc_fails(path, py, files.changed.get(path, set()))
    if fails:
        return Result("R05", FAIL, f"{len(fails)} doc comment problems.", fails)
    return Result("R05", PASS, f"{len(files.analyzed)} changed files have doc comments in English.")


def _line_count(text: str) -> int:
    """Counts the lines of a file, a last line without a newline included."""
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def check_r06(ctx: PrContext) -> Result:
    """Checks changed source files against the file length limit (R06, soft).

    Args:
        ctx: The PR under check.

    Returns:
        SKIP when no source file changed. Over the limit, WARN with a
        soft-limit reason and FAIL without one. PASS otherwise.
    """
    paths = [c.path for c in ctx.changes
             if c.status != "D" and classify(c.path, ctx.config.paths) == "source"]
    if not paths:
        return Result("R06", SKIP, "No source files changed.")
    limit = ctx.config.limits["file_lines"]
    texts = read_blobs(ctx.repo, ctx.head, paths)
    over = [Detail(p, None, f"{n} lines, over {limit}")
            for p, t in sorted(texts.items()) if (n := _line_count(t)) > limit]
    if not over:
        return Result("R06", PASS, f"{len(paths)} changed source files, all within {limit} lines.")
    reason = soft_limit_reason(ctx.body)
    if reason:
        first = reason.splitlines()[0]
        return Result("R06", WARN, f"{len(over)} files over {limit} lines. Reason given: \"{first}\"",
                      over)
    return Result("R06", FAIL, f"{len(over)} files over {limit} lines. No soft-limit reason given.",
                  over)
