"""R11: line and branch coverage of changed lines, from Cobertura XML (F03 design 5)."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .classify import classify
from .context import PrContext
from .gitio import added_lines, read_blob
from .report import FAIL, PASS, SKIP, WARN, Detail, Result, outcome

COVERED_KINDS = ("impl", "fix")
_EXCLUSION = re.compile(
    r"(?i:pragma[:\s]?\s*no\s*cover)|GCOVR_EXCL_(?:LINE|START|BR_LINE)|LCOV_EXCL_(?:LINE|START|BR_LINE)")
_REASON = re.compile(r"(?i)reason:\s*\S")
_CONDITION = re.compile(r"\((\d+)/(\d+)\)")


class CoverageError(Exception):
    """Raised when a coverage report is missing or is not valid XML."""


@dataclass
class LineHits:
    """Coverage of one line.

    Attributes:
        hits: Times the line ran.
        branches_covered: Branch outcomes taken from this line.
        branches_total: Branch outcomes possible from this line.
    """

    hits: int = 0
    branches_covered: int = 0
    branches_total: int = 0


def _repo_path(filename: str, sources: list[str], repo: Path) -> str | None:
    """Turns a report's file name into a repository path, or None if outside the repo."""
    root = repo.resolve()
    candidates = [filename] + [f"{s.rstrip('/')}/{filename}" for s in sources]
    inside = []
    for name in candidates:
        path = Path(name)
        path = (path if path.is_absolute() else root / path).resolve()
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if path.exists():
            return rel
        inside.append(rel)
    return inside[0] if inside else None


def _merge_line(target: dict[int, LineHits], element: ET.Element) -> None:
    """Adds one <line> element's numbers to the file's line table."""
    number = int(element.get("number", "0"))
    hits = int(float(element.get("hits", "0")))
    line = target.setdefault(number, LineHits())
    line.hits = max(line.hits, hits)
    condition = _CONDITION.search(element.get("condition-coverage", ""))
    if element.get("branch") == "true" and condition:
        line.branches_covered = max(line.branches_covered, int(condition.group(1)))
        line.branches_total = max(line.branches_total, int(condition.group(2)))


def read_cobertura(path: Path, repo: Path) -> dict[str, dict[int, LineHits]]:
    """Reads a Cobertura XML report.

    Args:
        path: The report file.
        repo: Repository root, used to resolve the report's file names.

    Returns:
        Line coverage by repository path and line number.

    Raises:
        CoverageError: The file is missing or is not valid XML.
    """
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError as exc:
        raise CoverageError(f"coverage report not found: {path}") from exc
    except (ET.ParseError, OSError) as exc:
        raise CoverageError(f"coverage report {path} cannot be read: {exc}") from exc
    sources = [s.text.strip().replace("\\", "/") for s in root.iter("source") if s.text]
    result: dict[str, dict[int, LineHits]] = {}
    for cls in root.iter("class"):
        name = _repo_path(cls.get("filename", "").replace("\\", "/"), sources, repo)
        lines = cls.find("lines")
        if name is None or lines is None:
            continue
        table = result.setdefault(name, {})
        for element in lines.findall("line"):
            _merge_line(table, element)
    return result


def _exclusion_fails(ctx: PrContext, changed: dict[str, set[int]]) -> list[Detail]:
    """Finds exclusion comments on changed lines that give no reason."""
    fails = []
    for path, numbers in changed.items():
        lines = (read_blob(ctx.repo, ctx.head, path) or "").splitlines()
        for number in sorted(numbers):
            text = lines[number - 1] if number <= len(lines) else ""
            if _EXCLUSION.search(text) and not _REASON.search(text):
                fails.append(Detail(path, number, "coverage exclusion without \"reason:\""))
    return fails


def _ranges(numbers: list[int]) -> str:
    """Formats sorted line numbers as compact ranges, for example "3-5, 9"."""
    parts, start = [], None
    for i, n in enumerate(numbers):
        start = n if start is None else start
        if i + 1 == len(numbers) or numbers[i + 1] != n + 1:
            parts.append(str(n) if start == n else f"{start}-{n}")
            start = None
    return ", ".join(parts)


@dataclass
class Totals:
    """Coverage totals over all changed lines.

    Attributes:
        executable: Changed lines the reports list.
        covered: Those that ran.
        branches: Branch outcomes possible on changed lines.
        branches_covered: Those taken.
    """

    executable: int = 0
    covered: int = 0
    branches: int = 0
    branches_covered: int = 0


def _measure(changed: dict[str, set[int]], reports: dict, totals: Totals) -> tuple[list, list]:
    """Adds up coverage of changed lines and lists uncovered lines and unmeasured files."""
    uncovered, warns = [], []
    for path, numbers in sorted(changed.items()):
        table = reports.get(path)
        if table is None:
            if numbers:
                warns.append(Detail(path, None, "not in any coverage report"))
            continue
        executable = sorted(n for n in numbers if n in table)
        missed = [n for n in executable if table[n].hits <= 0]
        totals.executable += len(executable)
        totals.covered += len(executable) - len(missed)
        totals.branches += sum(table[n].branches_total for n in executable)
        totals.branches_covered += sum(table[n].branches_covered for n in executable)
        if missed:
            uncovered.append(Detail(path, missed[0], f"uncovered changed lines: {_ranges(missed)}"))
    return uncovered, warns


def _load_reports(ctx: PrContext, paths: list[str]) -> tuple[dict, list[Detail]]:
    """Reads and merges every coverage report, collecting read errors as details."""
    merged: dict[str, dict[int, LineHits]] = {}
    errors = []
    for path in paths:
        try:
            report = read_cobertura(Path(path), ctx.repo)
        except CoverageError as exc:
            errors.append(Detail(None, None, str(exc)))
            continue
        for name, table in report.items():
            target = merged.setdefault(name, {})
            for number, hits in table.items():
                line = target.setdefault(number, LineHits())
                line.hits = max(line.hits, hits.hits)
                line.branches_covered = max(line.branches_covered, hits.branches_covered)
                line.branches_total = max(line.branches_total, hits.branches_total)
    return merged, errors


def _percent(part: int, whole: int) -> str:
    """Formats a share as a percentage with one decimal, or "n/a" for nothing."""
    return "n/a" if whole == 0 else f"{100 * part / whole:.1f}%"


def check_r11(ctx: PrContext, coverage_paths: list[str]) -> Result:
    """Checks line and branch coverage of the changed source lines (R11).

    Args:
        ctx: The PR under check.
        coverage_paths: Paths given with --coverage.

    Returns:
        SKIP for PRs other than impl and fix, or when no report was given.
        FAIL below the limits, for unreadable reports, or for an exclusion
        without a reason. WARN when a changed file is in no report.
    """
    if ctx.title is None or ctx.title.kind not in COVERED_KINDS:
        return Result("R11", SKIP, "Not an implementation PR.")
    if not coverage_paths:
        return Result("R11", SKIP, "No coverage report given.")
    sources = [c.path for c in ctx.changes
               if c.status != "D" and classify(c.path, ctx.config.paths) == "source"]
    changed = added_lines(ctx.repo, ctx.base, ctx.head, sources)
    reports, fails = _load_reports(ctx, coverage_paths)
    fails += _exclusion_fails(ctx, changed)
    totals = Totals()
    uncovered, warns = _measure(changed, reports, totals)
    limits = ctx.config.limits
    low_lines = totals.covered * 100 < limits["line_coverage"] * totals.executable
    low_branches = totals.branches_covered * 100 < limits["branch_coverage"] * totals.branches
    if low_lines:
        fails += uncovered
    if low_branches:
        fails.append(Detail(None, None, f"branch coverage is below {limits['branch_coverage']}%"))
    message = (f"Changed lines: {_percent(totals.covered, totals.executable)} line "
               f"({totals.covered}/{totals.executable}), "
               f"{_percent(totals.branches_covered, totals.branches)} branch "
               f"({totals.branches_covered}/{totals.branches}).")
    result = outcome(fails, warns)
    return Result("R11", result, message, fails or warns)
