"""Checks that every English document in tstack matches its Chinese mirror.

Usage:
    python troy-mode/dev/check_pairs.py [--repo PATH]

For every tracked ``X.zh-CN.md``, ``X.md`` must exist, and the pair must have:

- The same headings (level and section number), the same table column
  counts, and the same number of code blocks.
- The same version. A document with a visible header table has matching
  "| Version |" and "| 版本 |" rows, and the mirror's "同步自英文版 X" note names
  that version. A document with front matter has the same troy-doc and
  version, lang "en" and "zh-CN", and mirror and mirror-of naming the same
  document.
- The same fill-in markers ({{...}}) outside HTML comments and inline code.

This is tstack's own tool. It is not copied into projects; there,
troy-check's R12 does this job.

Exit codes: 0 when every pair matches, 1 when there is a problem, and 2 when
the script cannot run.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

_HEADING = re.compile(r"^(#{1,6})\s+(\d+(?:\.\d+)*\.?)?")
_FENCE = re.compile(r"^\s*(```|~~~)")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_MARKER = re.compile(r"\{\{[^{}\n]+\}\}")
_EN_VERSION = re.compile(r"^\| Version \| ([^|]+?) \|\s*$", re.MULTILINE)
_ZH_VERSION = re.compile(r"^\| 版本 \| ([^|]+?) \|\s*$", re.MULTILINE)
_SYNC_NOTE = re.compile(r"同步自英文版 (\S+?)（")


class RepoError(Exception):
    """Raised when the folder is not a git repository."""


@dataclass
class Outline:
    """The shape of a document, read outside code blocks.

    Attributes:
        headings: (level, section number) per heading, in order.
        tables: Column count of each table's first row, in order.
        code_blocks: Number of fenced code blocks.
        markers: Fill-in markers outside HTML comments and inline code.
    """

    headings: list[tuple[int, str]] = field(default_factory=list)
    tables: list[int] = field(default_factory=list)
    code_blocks: int = 0
    markers: set[str] = field(default_factory=set)


def tracked_markdown(repo: Path) -> list[str]:
    """Lists the Markdown files git tracks in the repository.

    Args:
        repo: Repository root.

    Returns:
        Repository paths with "/" separators.

    Raises:
        RepoError: The folder is not inside a git repository.
    """
    proc = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "--", "*.md"],
                          capture_output=True)
    if proc.returncode != 0:
        raise RepoError(f"{repo} is not a git repository")
    return [p for p in proc.stdout.decode("utf-8").split("\x00") if p]


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Separates YAML front matter from the rest of a document.

    Args:
        text: The whole file.

    Returns:
        The front matter values with quotes removed (empty when there is no
        front matter), and the text after it.
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 3)
    if end < 0:
        return {}, text
    fields = {}
    for line in text[4:end].split("\n"):
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"')
    return fields, text[end + 5:]


def _markers(line: str) -> set[str]:
    """Finds fill-in markers in a line outside inline code."""
    return set(_MARKER.findall(_INLINE_CODE.sub("", line)))


def outline(body: str) -> Outline:
    """Reads a document's headings, tables, code blocks, and markers.

    Args:
        body: Document text after any front matter.

    Returns:
        The document's outline.
    """
    result = Outline()
    in_fence = in_table = False
    for line in _COMMENT.sub("", body).split("\n"):
        if _FENCE.match(line):
            result.code_blocks += 0 if in_fence else 1
            in_fence, in_table = not in_fence, False
            continue
        if in_fence:
            result.markers |= set(_MARKER.findall(line))
            continue
        heading = _HEADING.match(line)
        if heading:
            result.headings.append((len(heading.group(1)), (heading.group(2) or "").rstrip(".")))
        is_row = line.lstrip().startswith("|")
        if is_row and not in_table:
            result.tables.append(line.replace("\\|", "").strip().count("|") - 1)
        in_table = is_row
        result.markers |= _markers(line)
    return result


def _first(pattern: re.Pattern, text: str) -> str | None:
    """Returns the first group of the first match, or None."""
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def table_version_problems(en_text: str, zh_text: str) -> list[str]:
    """Compares the visible version rows and the mirror's sync note.

    Args:
        en_text: The English document.
        zh_text: The Chinese mirror.

    Returns:
        Problems found. Empty when the English document has no version row.
    """
    en_version = _first(_EN_VERSION, en_text)
    if en_version is None:
        return []
    problems = []
    zh_version = _first(_ZH_VERSION, zh_text)
    if zh_version != en_version:
        problems.append(f"version {en_version}, but the mirror's 版本 row says {zh_version}")
    note = _first(_SYNC_NOTE, zh_text)
    if note != en_version:
        problems.append(f"version {en_version}, but the mirror's sync note says {note}")
    return problems


def front_matter_problems(en: dict[str, str], zh: dict[str, str]) -> list[str]:
    """Compares the front matter of a pair.

    Args:
        en: English front matter values.
        zh: Chinese front matter values.

    Returns:
        Problems found. Empty when the English document has no troy-doc.
    """
    if "troy-doc" not in en:
        return []
    problems = [f"{key} {en.get(key)!r}, but the mirror says {zh.get(key)!r}"
                for key in ("troy-doc", "version") if en.get(key) != zh.get(key)]
    if en.get("lang") != "en" or zh.get("lang") != "zh-CN":
        problems.append(f"lang should be en and zh-CN, not {en.get('lang')} and {zh.get('lang')}")
    mirror = en.get("mirror", "")
    if not mirror.endswith(".zh-CN.md") or mirror[:-len(".zh-CN.md")] + ".md" != zh.get("mirror-of"):
        problems.append(f"mirror {mirror!r} and mirror-of {zh.get('mirror-of')!r} disagree")
    return problems


def outline_problems(en: Outline, zh: Outline) -> list[str]:
    """Compares the outlines of a pair.

    Args:
        en: Outline of the English document.
        zh: Outline of the Chinese mirror.

    Returns:
        Problems found.
    """
    problems = []
    if en.headings != zh.headings:
        diff = next((i for i, (a, b) in enumerate(zip(en.headings, zh.headings)) if a != b),
                    min(len(en.headings), len(zh.headings)))
        problems.append(f"headings differ from heading {diff + 1} on "
                        f"({len(en.headings)} in English, {len(zh.headings)} in the mirror)")
    if en.tables != zh.tables:
        problems.append(f"table columns differ: {en.tables} vs {zh.tables}")
    if en.code_blocks != zh.code_blocks:
        problems.append(f"code blocks differ: {en.code_blocks} vs {zh.code_blocks}")
    missing = sorted(en.markers - zh.markers)
    if missing:
        problems.append(f"markers missing from the mirror: {', '.join(missing)}")
    return problems


def compare(repo: Path, en_path: str, zh_path: str) -> list[str]:
    """Checks one English document against its mirror.

    Args:
        repo: Repository root.
        en_path: Path of the English document.
        zh_path: Path of the Chinese mirror.

    Returns:
        Problems found, each prefixed with the English path.
    """
    en_text = (repo / en_path).read_text(encoding="utf-8").replace("\r\n", "\n")
    zh_text = (repo / zh_path).read_text(encoding="utf-8").replace("\r\n", "\n")
    en_fm, en_body = split_front_matter(en_text)
    zh_fm, zh_body = split_front_matter(zh_text)
    problems = table_version_problems(en_text, zh_text)
    problems += front_matter_problems(en_fm, zh_fm)
    problems += outline_problems(outline(en_body), outline(zh_body))
    return [f"{en_path}: {p}" for p in problems]


def check_repo(repo: Path) -> tuple[int, list[str]]:
    """Checks every pair in the repository.

    Args:
        repo: Repository root.

    Returns:
        The number of pairs checked and the problems found.
    """
    tracked = set(tracked_markdown(repo))
    problems, pairs = [], 0
    for zh_path in sorted(p for p in tracked if p.endswith(".zh-CN.md")):
        en_path = zh_path[:-len(".zh-CN.md")] + ".md"
        if en_path not in tracked:
            problems.append(f"{zh_path}: no English document {en_path}")
            continue
        pairs += 1
        problems += compare(repo, en_path, zh_path)
    return pairs, problems


def main(argv: list[str] | None = None) -> int:
    """Runs the check and prints one line per problem.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        0 when every pair matches, 1 when there is a problem, 2 when the
        script cannot run.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check EN/ZH document pairs.")
    parser.add_argument("--repo", default=".", help="repository root (default: .)")
    args = parser.parse_args(argv)
    try:
        pairs, problems = check_repo(Path(args.repo))
    except (RepoError, OSError, UnicodeDecodeError) as exc:
        print(f"check_pairs: error: {exc}", file=sys.stderr)
        return 2
    for line in problems:
        print(line)
    print(f"{pairs} pairs checked, {len(problems)} problems.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
