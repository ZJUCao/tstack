"""The progress file, a view of the state that F07 rewrites (F07 design 5.2, F01 5.9).

It is local, git-ignored, and in English. Losing it loses only the notes and
the attempts counted before their PR existed, which it carries from one
rewrite to the next while the feature and stage stay the same.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

PATH = ".troy-mode/progress.md"
FIELDS = ("Current version", "Current feature", "Stage", "Open PRs", "Waiting on Troy",
          "Open issues", "Next action", "Last updated")
# The lines that say where the project stands. When one differs from the
# state, the file is out of date and is rebuilt. What waits on Troy counts:
# F07's comments on the open PR are part of the state (design 5.1).
STATE_FIELDS = ("Current version", "Current feature", "Stage", "Open PRs", "Waiting on Troy",
                "Next action")


@dataclass
class View:
    """The progress file's fields.

    Attributes:
        values: Each field's one-line text, by field name.
        notes: The Open issues items.
    """

    values: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def render(view: View) -> str:
    """Renders the progress file in the shape of F01's progress template."""
    lines = ["# Progress", ""]
    for name in FIELDS:
        if name == "Open issues" and view.notes:
            lines.append("- Open issues:")
            lines += [f"  - {note}" for note in view.notes]
        elif name == "Open issues":
            lines.append("- Open issues: None")
        else:
            lines.append(f"- {name}: {view.values.get(name, 'None')}")
    return "\n".join(lines) + "\n"


def parse(text: str) -> View:
    """Reads a progress file back into its fields and notes."""
    view, in_issues = View(), False
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("  - ") and in_issues:
            view.notes.append(line[4:].strip())
            continue
        in_issues = False
        if not line.startswith("- "):
            continue
        name, sep, value = line[2:].partition(":")
        if sep and name in FIELDS:
            view.values[name] = value.strip()
            in_issues = name == "Open issues"
    return view


def stage_number(view: View) -> str:
    """Returns the first word of the Stage line, which holds the stage number."""
    words = view.values.get("Stage", "").split()
    return words[0].rstrip(".") if words else ""


def same_work(old: View, new: View) -> bool:
    """Tells whether two views are about the same feature and stage, so notes carry over."""
    return (old.values.get("Current feature") == new.values.get("Current feature")
            and stage_number(old) == stage_number(new))


def is_current(old: View, new: View) -> bool:
    """Tells whether an existing file still says where the project stands."""
    return all(old.values.get(name) == new.values.get(name) for name in STATE_FIELDS)


def read(root: Path) -> View | None:
    """Reads the progress file of a working tree, or None when it is missing."""
    try:
        return parse((root / PATH).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


def write(root: Path, view: View) -> None:
    """Writes the progress file with LF line endings."""
    view.values["Last updated"] = time.strftime("%Y-%m-%d %H:%M")
    with open(root / PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render(view))
