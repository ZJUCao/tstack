"""Test results from JUnit XML, and the IDs carried in test names (F03 design 4.1)."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"

_CASE = re.compile(r"(?i)^(f\d{2,3})[-_]t(\d{2})(?![0-9])")
_BUG = re.compile(r"(?i)^(b[1-9]\d*)(?![0-9])")
_PARAMS = re.compile(r"\[.*\]$")


class ReportError(Exception):
    """Raised when a JUnit file is missing or is not valid XML."""


@dataclass(frozen=True)
class JUnitCase:
    """One test from a JUnit report.

    Attributes:
        name: The testcase name as reported.
        classname: The testcase classname, or "".
        file: The testcase file attribute, or "".
        outcome: PASSED, FAILED (failure or error), or SKIPPED.
    """

    name: str
    classname: str
    file: str
    outcome: str

    @property
    def label(self) -> str:
        """A readable identifier for reports."""
        return f"{self.classname}::{self.name}" if self.classname else self.name


@dataclass(frozen=True)
class IdTag:
    """The ID a test name carries.

    Attributes:
        feature: Feature ID such as "F04", or None.
        case: Case ID such as "F04-T07", or None.
        bug: Bug ID such as "B12", or None.
    """

    feature: str | None = None
    case: str | None = None
    bug: str | None = None


def own_name(name: str) -> str:
    """Strips a test name down to the part its author chose.

    Removes a bracketed parameter suffix, everything up to the last "." (the
    GoogleTest suite name), and a leading "test_" or "test".

    Args:
        name: The JUnit testcase name.

    Returns:
        The test's own name.
    """
    name = _PARAMS.sub("", name)
    name = name.rsplit(".", 1)[-1]
    lowered = name.lower()
    for prefix in ("test_", "test"):
        if lowered.startswith(prefix):
            return name[len(prefix):]
    return name


def tag_of(name: str) -> IdTag | None:
    """Reads the case ID or bug ID at the start of a test's own name.

    Args:
        name: The JUnit testcase name.

    Returns:
        The tag, or None when the name starts with no ID.
    """
    own = own_name(name)
    case = _CASE.match(own)
    if case:
        feature = case.group(1).upper()
        return IdTag(feature=feature, case=f"{feature}-T{case.group(2)}")
    bug = _BUG.match(own)
    if bug and (len(own) == bug.end() or own[bug.end()] in "-_"):
        return IdTag(bug=bug.group(1).upper())
    return None


def _outcome(case: ET.Element) -> str:
    """Finds a testcase element's outcome from its children and its status.

    CTest marks a test that did not run only with status="notrun" or
    status="disabled", without a <skipped> child. A failed CTest test has a
    <failure> child.
    """
    status = case.get("status", "")
    if case.find("failure") is not None or case.find("error") is not None:
        return FAILED
    if case.find("skipped") is not None or status in ("notrun", "disabled", "skipped"):
        return SKIPPED
    return PASSED


def read_junit(path: Path) -> list[JUnitCase]:
    """Reads every testcase from one JUnit XML file.

    Args:
        path: The file written by the test runner.

    Returns:
        The tests in file order.

    Raises:
        ReportError: The file is missing or is not valid XML.
    """
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError as exc:
        raise ReportError(f"JUnit file not found: {path}") from exc
    except (ET.ParseError, OSError) as exc:
        raise ReportError(f"JUnit file {path} cannot be read: {exc}") from exc
    return [JUnitCase(c.get("name", ""), c.get("classname", ""), c.get("file", ""), _outcome(c))
            for c in root.iter("testcase")]


def legacy_path(test: JUnitCase) -> str:
    """Returns the path used to match [tests] legacy patterns.

    Args:
        test: A test result.

    Returns:
        The file attribute when the runner wrote one, else the classname
        with "." replaced by "/".
    """
    if test.file:
        return test.file.replace("\\", "/")
    return test.classname.replace(".", "/")
