"""Check results and the text, JSON, and GitHub Actions reports built from them."""

import json
import os
from dataclasses import asdict, dataclass, field

PASS = "pass"
WARN = "warn"
FAIL = "fail"
SKIP = "skip"


@dataclass
class Detail:
    """One finding inside a rule result.

    Attributes:
        path: Repository path the finding is about, or None when it is about
            something without a file, such as a commit or the PR description.
        line: 1-based line number, or None.
        message: What is wrong or worth a look.
    """

    path: str | None
    line: int | None
    message: str


@dataclass
class Result:
    """The outcome of one rule.

    Attributes:
        rule: Rule ID, for example "R03".
        result: One of PASS, WARN, FAIL, or SKIP.
        message: One-line summary.
        details: Findings that explain a WARN or FAIL.
    """

    rule: str
    result: str
    message: str
    details: list[Detail] = field(default_factory=list)


def outcome(fails: list[Detail], warns: list[Detail]) -> str:
    """Picks the result for a rule from its failing and warning details.

    Args:
        fails: Details that make the rule fail.
        warns: Details that only need a look.

    Returns:
        FAIL if there is any failing detail, WARN if there is any warning
        detail, and PASS otherwise.
    """
    if fails:
        return FAIL
    return WARN if warns else PASS


def is_ok(results: list[Result]) -> bool:
    """Tells whether no result is a failure.

    Args:
        results: Results of all rules that ran.

    Returns:
        True when no result is FAIL.
    """
    return all(r.result != FAIL for r in results)


def _plural(count: int, word: str) -> str:
    """Formats a count with a noun, adding "s" when the count is not 1."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def summary_line(results: list[Result]) -> str:
    """Builds the last line of the text report.

    Args:
        results: Results of all rules that ran.

    Returns:
        A line such as "Result: fail, 1 failure, 2 warnings."
    """
    fails = sum(r.result == FAIL for r in results)
    warns = sum(r.result == WARN for r in results)
    parts = [PASS if fails == 0 else FAIL]
    if fails:
        parts.append(_plural(fails, "failure"))
    if warns:
        parts.append(_plural(warns, "warning"))
    return "Result: " + ", ".join(parts) + "."


def _detail_text(detail: Detail) -> str:
    """Formats one detail as an indented report line.

    A detail without a path, such as one about a commit or the PR
    description, already says where it is in its message.
    """
    if detail.path is None:
        return "      " + detail.message
    where = detail.path if detail.line is None else f"{detail.path}:{detail.line}"
    return f"      {where}  {detail.message}"


def render_text(header: list[str], results: list[Result]) -> str:
    """Builds the human-readable report.

    Args:
        header: Lines printed before the results, such as the title line.
        results: Results of all rules that ran.

    Returns:
        The report, ending with a newline.
    """
    lines = list(header)
    for res in results:
        lines.append(f"{res.result:<6}{res.rule:<5}{res.message}")
        if res.result in (FAIL, WARN):
            lines.extend(_detail_text(d) for d in res.details)
    lines.append(summary_line(results))
    return "\n".join(lines) + "\n"


def render_json(command: str, title: dict | None, results: list[Result]) -> str:
    """Builds the machine-readable report described in design section 3.3.

    Args:
        command: "pr" or "commit".
        title: The parsed PR title as a dict, or None.
        results: Results of all rules that ran.

    Returns:
        The JSON text, ending with a newline.
    """
    data = {
        "command": command,
        "ok": is_ok(results),
        "title": title,
        "results": [asdict(r) for r in results],
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _escape_data(text: str) -> str:
    """Escapes text for the message part of a GitHub workflow command."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(text: str) -> str:
    """Escapes text for a property value of a GitHub workflow command."""
    return _escape_data(text).replace(":", "%3A").replace(",", "%2C")


def _annotation(level: str, rule: str, detail: Detail) -> str:
    """Formats one GitHub annotation line for a detail."""
    props = []
    if detail.path is not None:
        props.append(f"file={_escape_property(detail.path)}")
        if detail.line is not None:
            props.append(f"line={detail.line}")
    where = " " + ",".join(props) if props else ""
    return f"::{level}{where}::{_escape_data(f'{rule} {detail.message}')}"


def github_annotations(results: list[Result]) -> list[str]:
    """Builds one GitHub annotation per failing or warning detail.

    Args:
        results: Results of all rules that ran.

    Returns:
        Workflow command lines such as "::error file=a.md,line=3::R20 ...".
        A failing or warning result without details gets one line for its
        message.
    """
    lines = []
    for res in results:
        if res.result not in (FAIL, WARN):
            continue
        level = "error" if res.result == FAIL else "warning"
        details = res.details or [Detail(None, None, res.message)]
        lines.extend(_annotation(level, res.rule, d) for d in details)
    return lines


def write_github_outputs(text_report: str, results: list[Result], stream) -> None:
    """Writes annotations and the step summary when running in GitHub Actions.

    Does nothing unless the environment variable GITHUB_ACTIONS is "true".

    Args:
        text_report: The text report, appended to $GITHUB_STEP_SUMMARY.
        results: Results of all rules that ran.
        stream: Where the annotation lines go.
    """
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    for line in github_annotations(results):
        print(line, file=stream)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("```text\n" + text_report + "```\n")
