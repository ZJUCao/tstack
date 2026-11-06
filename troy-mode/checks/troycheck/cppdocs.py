"""R05 for C and C++: Doxygen's warnings and English-only comments (F03 design 9.3).

Doxygen finds the declarations without a doc comment. troy-check keeps the
warnings that fall on changed lines, and checks the language of changed
comment lines itself.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from .context import PrContext
from .report import FAIL, PASS, SKIP, Detail, Result

_WARNING = re.compile(r"^(?P<file>\S.*?):(?P<line>\d+): warning: (?P<text>.*)$")


@dataclass
class DocWarning:
    """One warning from Doxygen's log.

    Attributes:
        path: Repository path of the file, or None when it is outside the repository.
        line: The warning's line.
        text: The warning, continuation lines joined with spaces.
    """

    path: str | None
    line: int
    text: str


def repo_path(name: str, repo: Path) -> str | None:
    """Turns a file name from the log into a repository path.

    Args:
        name: Absolute, or relative to the repository root, with / or \\.
        repo: The repository root.

    Returns:
        The repository path with / separators, or None outside the repository.
    """
    root = repo.resolve()
    path = Path(name.replace("\\", "/"))
    full = (path if path.is_absolute() else root / path).resolve()
    try:
        return full.relative_to(root).as_posix()
    except ValueError:
        return None


def read_doc_log(log: Path, repo: Path) -> list[DocWarning]:
    """Reads Doxygen's warning log, written with WARN_FORMAT "$file:$line: $text".

    Lines that start with whitespace continue the warning before them. Other
    lines that do not look like a warning are ignored.

    Raises:
        OSError: The log cannot be read.
    """
    warnings: list[DocWarning] = []
    current = None
    for raw in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw[:1] in (" ", "\t"):
            if current is not None and raw.strip():
                current.text += " " + raw.strip()
            continue
        match = _WARNING.match(raw)
        current = None
        if match:
            current = DocWarning(repo_path(match["file"], repo), int(match["line"]),
                                 match["text"].strip())
            warnings.append(current)
    return warnings


def check_r05_cpp(ctx: PrContext, files, log: str | None, cjk_fails: list[Detail]) -> Result:
    """Checks doc comments and comment language in changed C and C++ code (R05).

    Args:
        ctx: The PR under check.
        files: The analyzed changed C and C++ files (shape.CodeFiles).
        log: The --doc-warnings path, or None.
        cjk_fails: Changed comment lines with Chinese, Japanese, or Korean text.

    Returns:
        FAIL for a Doxygen warning on a changed line, a CJK comment, or a
        log that cannot be read. Without a log, SKIP unless a comment fails.
    """
    fails = list(files.errors) + cjk_fails
    if log is None:
        if fails:
            return Result("R05", FAIL, f"{len(fails)} comment problems.", fails)
        return Result("R05", SKIP, "No Doxygen warning log given (--doc-warnings). Only the "
                                   "language of comments was checked.")
    try:
        warnings = read_doc_log(Path(log), ctx.repo)
    except OSError as exc:
        fails.append(Detail(None, None, f"cannot read the Doxygen warning log {log}: {exc}"))
        return Result("R05", FAIL, "The Doxygen warning log cannot be read.", fails)
    fails += [Detail(w.path, w.line, f"Doxygen: {w.text}") for w in warnings
              if w.path in files.analyzed and w.line in files.changed.get(w.path, set())]
    if fails:
        return Result("R05", FAIL, f"{len(fails)} doc comment problems.", fails)
    return Result("R05", PASS, f"{len(files.analyzed)} changed files: no Doxygen warning on a "
                               "changed line, and comments in English.")
