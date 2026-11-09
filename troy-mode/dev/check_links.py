"""Checks the relative links and anchors in troy-pstack's README and troy-mode documents.

Usage:
    python troy-mode/dev/check_links.py [--repo PATH]

It reads ``README.md`` and every tracked ``*.md`` under ``docs/troy-mode/``
(F10 design section 9.1), and checks each link outside fenced code blocks,
inline code, and HTML comments:

- A link to a file, relative to the linking file's folder, or to the
  repository root when it starts with "/", must name a file git tracks. A
  link to a folder must name a folder that holds a tracked file.
- An anchor, as in ``../requirements.md#72-feature-list`` or ``#troy-mode``,
  must match a heading of the target Markdown file under GitHub's rules:
  lowercase, punctuation other than "-" and "_" removed, Chinese characters
  kept, spaces turned into "-", and "-1", "-2" added to repeated headings.
- Links with a scheme, such as ``https:`` or ``mailto:``, are not checked.

This is troy-pstack's own tool. It is not copied into projects.

Exit codes: 0 when every link resolves, 1 when one does not, and 2 when the
script cannot run.
"""

import argparse
import posixpath
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_CLOSING_HASHES = re.compile(r"(?:^|[ \t]+)#+$")
_TARGET = r"(<[^<>\n]*>|[^\s()<>]*(?:\([^\s()]*\)[^\s()<>]*)*)"
_TITLE = r"""(?:\s+(?:"[^"]*"|'[^']*'|\([^()]*\)))?"""
_INLINE = re.compile(r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*" + _TARGET + _TITLE + r"\s*\)")
_DEFINITION = re.compile(r"^ {0,3}\[[^\[\]]+\]:[ \t]*(<[^<>]*>|\S+)")
_LINK_TEXT = re.compile(r"!?\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\([^()]*\)")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_SCOPE = "docs/troy-mode/"


class RepoError(Exception):
    """Raised when the folder is not a git repository or git fails."""


def _git(repo: Path, *args: str) -> str:
    """Runs git in the repository and returns its output.

    Raises:
        RepoError: git is missing or exits with an error.
    """
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                              text=True, encoding="utf-8")
    except OSError as exc:
        raise RepoError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        raise RepoError(proc.stderr.strip() or f"git {args[0]} failed")
    return proc.stdout


def tracked_files(repo: Path) -> tuple[Path, set[str]]:
    """Finds the repository root and the paths git tracks.

    Args:
        repo: A folder inside the repository.

    Returns:
        The root, and every tracked path with "/" separators.

    Raises:
        RepoError: The folder is not inside a git repository.
    """
    root = Path(_git(repo, "rev-parse", "--show-toplevel").strip())
    paths = {p for p in _git(root, "ls-files", "-z").split("\0") if p}
    return root, paths


def folders_of(paths: set[str]) -> set[str]:
    """Every folder that holds at least one of the paths, at any depth, and "." for the root."""
    found = {"."}
    for path in paths:
        parent = posixpath.dirname(path)
        while parent:
            found.add(parent)
            parent = posixpath.dirname(parent)
    return found


def _mask_code(line: str) -> str:
    """Replaces each inline code span with spaces of the same length."""
    return _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), line)


def _cut_comments(line: str, masked: str, in_comment: bool) -> tuple[str, str, bool]:
    """Removes HTML comments from a line, which may start or end in an earlier or later line.

    Comment markers inside inline code do not count: they are looked for in
    the masked line, and the same parts are cut from both lines.

    Returns:
        The line and its masked form without comments, and whether a comment
        is still open at the line's end.
    """
    if in_comment:
        end = masked.find("-->")
        if end < 0:
            return "", "", True
        line, masked = line[end + 3:], masked[end + 3:]
    while True:
        start = masked.find("<!--")
        if start < 0:
            return line, masked, False
        end = masked.find("-->", start + 4)
        if end < 0:
            return line[:start], masked[:start], True
        line, masked = line[:start] + line[end + 3:], masked[:start] + masked[end + 3:]


def prose_lines(text: str) -> list[tuple[int, str, str]]:
    """Splits a document into the lines that are neither code blocks nor comments.

    A fence opens with three or more backticks or tildes, at any indentation
    so that fences in list items count, and closes with a run of the same
    character at least as long and nothing after it.

    Returns:
        (line number, text, text with inline code blanked) for each line
        outside fenced code blocks, with HTML comments removed.
    """
    lines, fence, in_comment = [], None, False
    for number, line in enumerate(text.split("\n"), start=1):
        match = _FENCE.match(line)
        if fence:
            run = match.group(1) if match else ""
            if run and run[0] == fence[0] and len(run) >= len(fence) and not match.group(2).strip():
                fence = None
            continue
        if match and not in_comment and not (match.group(1)[0] == "`" and "`" in match.group(2)):
            fence = match.group(1)
            continue
        line, masked, in_comment = _cut_comments(line, _mask_code(line), in_comment)
        lines.append((number, line, masked))
    return lines


def slugify(heading: str) -> str:
    """Turns a heading's text into its anchor, before repeated headings are numbered."""
    text = _CODE_SPAN.sub(lambda m: m.group(2), heading)
    text = _LINK_TEXT.sub(lambda m: m.group(1), text).strip().lower()
    kept = "".join(ch for ch in text if ch.isalnum() or ch in " -_"
                   or unicodedata.category(ch).startswith("M"))
    return kept.replace(" ", "-")


def heading_slugs(text: str) -> set[str]:
    """Every anchor that GitHub gives the document's ATX headings, numbering repeats."""
    occurrences: dict[str, int] = {}
    for _, line, _ in prose_lines(text):
        match = _HEADING.match(line)
        if not match:
            continue
        title = _CLOSING_HASHES.sub("", match.group(2) or "").strip()
        base = result = slugify(title)
        while result in occurrences:
            occurrences[base] += 1
            result = f"{base}-{occurrences[base]}"
        occurrences[result] = 0
    return set(occurrences)


def link_targets(masked: str) -> list[str]:
    """The link targets in one line of prose whose inline code is blanked."""
    targets = [m.group(1) for m in _INLINE.finditer(masked)]
    definition = _DEFINITION.match(masked)
    if definition:
        targets.append(definition.group(1))
    return targets


class Checker:
    """Resolves links against the tracked files of one repository."""

    def __init__(self, root: Path, tracked: set[str]) -> None:
        """Keeps the root, the tracked paths, and their folders."""
        self.root = root
        self.tracked = tracked
        self.folders = folders_of(tracked)
        self._slugs: dict[str, set[str]] = {}

    def text(self, path: str) -> str:
        """Reads a tracked file as UTF-8 text with LF line endings.

        Raises:
            OSError, UnicodeDecodeError: The file cannot be read.
        """
        return (self.root / path).read_text(encoding="utf-8").replace("\r\n", "\n")

    def slugs(self, path: str) -> set[str]:
        """The heading anchors of a tracked Markdown file, read once."""
        if path not in self._slugs:
            self._slugs[path] = heading_slugs(self.text(path))
        return self._slugs[path]

    def problem(self, source: str, target: str) -> str | None:
        """Says why a link from source does not resolve, or None when it does."""
        target = target[1:-1] if target.startswith("<") and target.endswith(">") else target
        if _SCHEME.match(target):
            return None
        raw_path, _, raw_anchor = target.partition("#")
        path, anchor = unquote(raw_path.split("?", 1)[0]), unquote(raw_anchor)
        if not path:
            resolved = source
        else:
            base = "" if path.startswith("/") else posixpath.dirname(source)
            resolved = posixpath.normpath(posixpath.join(base, path.lstrip("/")))
        if resolved == ".." or resolved.startswith("../"):
            return "the path leaves the repository"
        if resolved in self.tracked and not path.endswith("/"):
            if anchor and resolved.endswith(".md") and anchor not in self.slugs(resolved):
                return f'no heading "{anchor}" in {resolved}'
            return None
        if resolved in self.folders:
            return None
        if (self.root / resolved).exists():
            return f"{resolved} is not tracked by git"
        return f"no file or folder {resolved}"

    def check_file(self, path: str) -> list[str]:
        """Checks every link of one document and returns a line per broken link."""
        found = []
        for number, _, masked in prose_lines(self.text(path)):
            for target in link_targets(masked):
                reason = self.problem(path, target)
                if reason:
                    found.append(f"{path}:{number}: broken link {target}: {reason}")
        return found


def check_repo(repo: Path) -> tuple[int, list[str]]:
    """Checks README.md and the tracked Markdown files under docs/troy-mode/.

    Args:
        repo: A folder inside the repository.

    Returns:
        The number of files read and one line per broken link.

    Raises:
        RepoError: The folder is not inside a git repository.
        OSError, UnicodeDecodeError: A file cannot be read.
    """
    root, tracked = tracked_files(repo)
    checker = Checker(root, tracked)
    scanned = sorted(p for p in tracked
                     if p == "README.md" or (p.startswith(_SCOPE) and p.endswith(".md")))
    problems = []
    for path in scanned:
        problems += checker.check_file(path)
    return len(scanned), problems


def main(argv: list[str] | None = None) -> int:
    """Runs the check and prints one line per broken link.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        0 when every link resolves, 1 when one does not, 2 when the script
        cannot run.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check the links in troy-mode's documents.")
    parser.add_argument("--repo", default=".", help="repository root (default: .)")
    args = parser.parse_args(argv)
    try:
        files, problems = check_repo(Path(args.repo))
    except (RepoError, OSError, UnicodeDecodeError) as exc:
        print(f"check_links: error: {exc}", file=sys.stderr)
        return 2
    for line in problems:
        print(line)
    print(f"{files} files checked, {len(problems)} broken links.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
