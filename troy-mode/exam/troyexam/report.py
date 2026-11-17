"""The PR's "Role exam" section and the report on Troy's PC (design 9.3)."""

import json
from pathlib import Path

from .instructions import short_hash


def role_title(role: str) -> str:
    """"interface-designer" -> "Interface Designer"."""
    return " ".join(part.capitalize() for part in role.split("-"))


def duration(minutes: float) -> str:
    """Minutes as "1 h 05 min"."""
    total = int(round(minutes))
    return f"{total // 60} h {total % 60:02d} min"


def block(summary: dict) -> str:
    """The section for the PR description, in design 9.3's shape."""
    lines = ["## Role exam", "", f"Result: {summary['result']}",
             f"Instructions: {short_hash(summary['instructions'])}",
             f"Cases: {summary['cases_run']} run, {summary['cases_not_affected']} not affected",
             f"Runs: {summary['runs']}, {summary['reused']} of them reused from the base; "
             f"${summary['cost']:.2f}; {duration(summary['minutes'])}"]
    rows = summary.get("rows") or []
    if rows:
        lines += ["", "| Case | Role | Base | Head | Result |", "| --- | --- | --- | --- | --- |"]
        for row in rows:
            base = row["base"] if isinstance(row["base"], str) else f"{row['base']} of {row['of']}"
            head = row["head"] if isinstance(row["head"], str) else f"{row['head']} of {row['of']}"
            lines.append(f"| {row['case']} | {role_title(row['role'])} | {base} | {head} | "
                         f"{row['result']} |")
    lines += ["", f"Report: {summary['report']}"]
    return "\n".join(lines) + "\n"


def write_report(folder: Path, summary: dict, details: list[str]) -> Path:
    """Writes summary.json and report.md into the exam's results folder."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False),
                                         encoding="utf-8")
    text = [f"# Role exam {summary.get('exam', '')}", "", block(summary).rstrip("\n"), ""]
    text += details
    path = folder / "report.md"
    path.write_text("\n".join(text) + "\n", encoding="utf-8", newline="\n")
    return path
