"""Builders for hand-written JUnit and Cobertura XML reports.

These functions only produce text. ``code_helpers`` writes the text to files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence, Tuple
from xml.sax.saxutils import quoteattr

PASS, FAIL, ERROR, SKIP = "pass", "fail", "error", "skip"
_CHILD = {
    FAIL: '<failure message="boom" type="AssertionError">trace</failure>',
    ERROR: '<error message="boom" type="RuntimeError">trace</error>',
    SKIP: '<skipped message="not run"/>',
    PASS: "",
}


@dataclass(frozen=True)
class Case:
    """One JUnit testcase.

    Attributes:
        name: The testcase ``name`` attribute.
        status: ``pass``, ``fail``, ``error``, or ``skip``.
        classname: The ``classname`` attribute.
        file: The ``file`` attribute, or None to leave it out.
    """

    name: str
    status: str = PASS
    classname: str = "tests.test_sample"
    file: Optional[str] = None


def case_xml(case: Case) -> str:
    """Builds the XML of one testcase.

    Args:
        case: The testcase.

    Returns:
        A ``<testcase>`` element.
    """
    attrs = f"classname={quoteattr(case.classname)} name={quoteattr(case.name)}"
    if case.file is not None:
        attrs += f" file={quoteattr(case.file)}"
    return f'<testcase {attrs} time="0.001">{_CHILD[case.status]}</testcase>'


def junit(cases: Iterable[Case]) -> str:
    """Builds a JUnit XML document.

    Args:
        cases: The testcases, in order.

    Returns:
        The XML text.
    """
    items = list(cases)
    body = "\n".join("    " + case_xml(c) for c in items)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<testsuites>\n'
        f'  <testsuite name="suite" tests="{len(items)}">\n{body}\n  </testsuite>\n'
        "</testsuites>\n"
    )


def tests(status: str, *names: str, **kwargs) -> list:
    """Builds several testcases that share a status.

    Args:
        status: Status of every case.
        *names: Testcase names.
        **kwargs: Other ``Case`` fields shared by every case.

    Returns:
        A list of ``Case`` objects.
    """
    return [Case(name, status, **kwargs) for name in names]


# A line spec is (hits,) or (hits, condition_coverage_text).
LineSpec = Tuple
FileSpec = Mapping[int, LineSpec]


def branch(covered: int, total: int) -> str:
    """Builds a ``condition-coverage`` value.

    Args:
        covered: Branch outcomes taken.
        total: All branch outcomes of the line.

    Returns:
        Text such as ``50% (1/2)``.
    """
    return f"{covered * 100 // total}% ({covered}/{total})"


def line_xml(number: int, spec: LineSpec) -> str:
    """Builds one Cobertura ``<line>`` element.

    Args:
        number: The line number.
        spec: ``(hits,)`` or ``(hits, condition_coverage_text)``.

    Returns:
        The element text.
    """
    if len(spec) > 1 and spec[1]:
        extra = f' branch="true" condition-coverage={quoteattr(spec[1])}'
    else:
        extra = ' branch="false"'
    return f'<line number="{number}" hits="{spec[0]}"{extra}/>'


def class_xml(filename: str, lines: FileSpec) -> str:
    """Builds one Cobertura ``<class>`` element.

    Args:
        filename: The class ``filename`` attribute.
        lines: Line number mapped to a line spec.

    Returns:
        The element text.
    """
    rows = "".join(line_xml(n, lines[n]) for n in sorted(lines))
    name = filename.replace("/", ".")
    return (
        f'<class name={quoteattr(name)} filename={quoteattr(filename)} line-rate="0">'
        f"<methods/><lines>{rows}</lines></class>"
    )


def cobertura(files: Mapping[str, FileSpec], sources: Sequence[str] = ()) -> str:
    """Builds a Cobertura XML document.

    Args:
        files: Report filename mapped to its line specs.
        sources: ``<source>`` roots, in order.

    Returns:
        The XML text.
    """
    roots = "".join(f"<source>{s}</source>" for s in sources)
    classes = "".join(class_xml(name, spec) for name, spec in files.items())
    return (
        '<?xml version="1.0" ?>\n<coverage version="7" line-rate="0" branch-rate="0">'
        f'<sources>{roots}</sources><packages><package name="p">'
        f"<classes>{classes}</classes></package></packages></coverage>\n"
    )


def hits(numbers: Iterable[int], missed: Iterable[int] = ()) -> dict:
    """Builds line specs for covered and missed lines.

    Args:
        numbers: Lines that were executed once.
        missed: Lines that were never executed.

    Returns:
        A mapping suitable for ``cobertura``.
    """
    spec = {n: (1,) for n in numbers}
    spec.update({n: (0,) for n in missed})
    return spec
