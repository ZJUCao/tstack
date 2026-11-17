"""Checks that text outside the history no longer names the plugin's old name (F19 design 11.2).

Usage:
    python troy-mode/dev/check_name.py [--repo PATH]

The plugin was renamed to tstack in version 0.6.0. This reads every text file
git tracks and reports each line that names its old name, which the pattern
``troy[-_ ]?pstack`` matches in any case, unless one of these holds:

1. The file is in HISTORY: the designs approved before F19's build merged,
   the F19 design itself, and the pilot report, in both languages.
2. In a Markdown file, the line lies in a change-log section: under a heading
   whose text after its number is exactly "Change log" or "修改记录", up to
   the next heading of the same or a higher level. Headings inside fenced
   code blocks do not count.
3. In a Markdown file, the line is the "| Status |" or "| 状态 |" row of the
   document's header table, its first table.
4. The line also names tstack, so it talks about the rename.
5. The old name appears only in links to the repository's issues and pull
   requests, which D197 keeps as they are.

This is tstack's own tool. It is not copied into projects.

Exit codes: 0 when nothing is found, 1 when a line names the old name, and 2
when the script cannot run.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

_DESIGNS = (
    "F01-templates", "F02-checks", "F03-language-packs", "F04-role-definitions", "F05-hooks",
    "F06-troy-init", "F07-entry-skill", "F08-release", "F09-rule-change", "F10-docs",
    "F11-pilot", "F12-real-run", "F13-mode-guard", "F14-summary", "F15-issues",
    "F16-role-exam", "F19-rename",
)
HISTORY: tuple[str, ...] = tuple(
    f"docs/troy-mode/design/{name}{suffix}" for name in _DESIGNS for suffix in (".md", ".zh-CN.md")
) + ("docs/troy-mode/pilot/recipe-menu-v0.1.md", "docs/troy-mode/pilot/recipe-menu-v0.1.zh-CN.md")

OLD_NAME = re.compile(r"troy[-_ ]?pstack", re.IGNORECASE)
NEW_NAME = re.compile(r"\btstack\b", re.IGNORECASE)
_LINK = re.compile(r"https?://github\.com/ZJUCao/troy[-_ ]?pstack/(?:issues|pull)/\d+",
                   re.IGNORECASE)
_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_NUMBER = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
_LOG_TITLES = ("Change log", "修改记录")
_STATUS_ROW = re.compile(r"^\|\s*(?:Status|状态)\s*\|")


class RepoError(Exception):
    """Raised when the folder is not a git repository."""


def tracked_files(repo: Path) -> list[str]:
    """Lists the files git tracks in the repository.

    Args:
        repo: Repository root.

    Returns:
        Repository paths with "/" separators.

    Raises:
        RepoError: The folder is not inside a git repository.
    """
    try:
        proc = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], capture_output=True)
    except OSError as exc:
        raise RepoError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        raise RepoError(f"{repo} is not a git repository")
    return [p for p in proc.stdout.decode("utf-8").split("\x00") if p]


def read_text(path: Path) -> str | None:
    """Reads a file as UTF-8 text, or None for a binary or missing file."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _history_lines(lines: list[str]) -> set[int]:
    """Finds the Markdown lines that rules 2 and 3 keep: change logs and the header Status row.

    Args:
        lines: The document's lines without line endings.

    Returns:
        0-based indexes of the lines that may keep the old name.
    """
    kept: set[int] = set()
    in_fence = False
    log_level = None
    table = "before"
    for index, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            heading = _HEADING.match(line)
            if heading:
                level = len(heading.group(1))
                if log_level is not None and level <= log_level:
                    log_level = None
                if _NUMBER.sub("", heading.group(2)) in _LOG_TITLES:
                    log_level = level
        if log_level is not None:
            kept.add(index)
        if not in_fence and line.startswith("|"):
            if table == "before":
                table = "first"
            if table == "first" and _STATUS_ROW.match(line):
                kept.add(index)
        elif table == "first":
            table = "after"
    return kept


def names_old(line: str) -> bool:
    """True when a line names the old name outside the rules 4 and 5 allow.

    Args:
        line: One line of text.
    """
    if NEW_NAME.search(line):
        return False
    return bool(OLD_NAME.search(_LINK.sub("", line)))


def check_file(rel: str, text: str) -> list[str]:
    """Lists the findings in one file's text.

    Args:
        rel: The repository path, with "/" separators.
        text: The file's text.

    Returns:
        One "path:line: text" entry per line that names the old name.
    """
    lines = [line.rstrip("\r") for line in text.split("\n")]
    kept = _history_lines(lines) if rel.lower().endswith(".md") else set()
    return [f"{rel}:{index + 1}: {line.strip()}" for index, line in enumerate(lines)
            if index not in kept and names_old(line)]


def check_repo(repo: Path) -> tuple[int, list[str]]:
    """Checks every tracked text file outside the history.

    Args:
        repo: Repository root.

    Returns:
        The number of files read and the findings.

    Raises:
        RepoError: The folder is not a git repository.
    """
    files, findings = 0, []
    history = set(HISTORY)
    for rel in tracked_files(repo):
        if rel in history:
            continue
        text = read_text(repo / rel)
        if text is None:
            continue
        files += 1
        findings += check_file(rel, text)
    return files, findings


def main(argv: list[str] | None = None) -> int:
    """Runs the check and prints one line per finding.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        0 when nothing is found, 1 when a line names the old name, 2 when the
        script cannot run.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check that living text uses the name tstack.")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]),
                        help="repository root (default: the one holding this script)")
    args = parser.parse_args(argv)
    try:
        files, findings = check_repo(Path(args.repo))
    except RepoError as exc:
        print(f"check_name: error: {exc}", file=sys.stderr)
        return 2
    for line in findings:
        print(line)
    print(f"check_name: {files} files checked, {len(findings)} lines name the old plugin.",
          file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
