"""The two comment lines that named the plugin before tstack (F19 design section 8, D195).

Upgrade never edits a project's config.toml or pyproject.toml otherwise (F06
design D54). These two lines are the exception: troy-init wrote each one, and
each named the plugin by its name before tstack. Upgrade rewrites a line only
when it is exactly what troy-init wrote, compared without a trailing carriage
return, and changes no other byte of the file. A line that names the old name
in any other form stays, and the report lists its file as a difference.
"""

import re
from pathlib import Path

from .plan import FileAction, Plan, read_project_file
from .setup import CONFIG_PATH

OLD_NAME = "troy-pstack"  # the plugin's name until 0.5.0, before tstack
_OLD_PATTERN = re.compile(r"troy[-_ ]?pstack", re.IGNORECASE)
PYPROJECT_PATH = "pyproject.toml"
_NEW_LINES = {
    CONFIG_PATH: "# Set by the language pack (troy-mode/lang/ in tstack), for example:",
    PYPROJECT_PATH: "# troy-check is checked in tstack, not in the project.",
}
# Each file's old line, as troy-init wrote it, and its new line.
COMMENT_LINES: dict[str, tuple[str, str]] = {
    path: (new.replace("tstack", OLD_NAME), new) for path, new in _NEW_LINES.items()
}


def rewrite(text: str, old: str, new: str) -> tuple[str, list[int]]:
    """Rewrites every line that is exactly old.

    Args:
        text: The file's text with its own line endings.
        old: The line troy-init wrote.
        new: Its new form.

    Returns:
        The new text, with each line's ending kept, and the 1-based numbers of
        lines that still name the old name but are not exactly old.
    """
    lines = text.split("\n")
    edited = []
    for number, line in enumerate(lines, start=1):
        body = line[:-1] if line.endswith("\r") else line
        if body == old:
            lines[number - 1] = new + line[len(body):]
        elif _OLD_PATTERN.search(body):
            edited.append(number)
    return "\n".join(lines), edited


def comment_actions(repo: Path, plan: Plan) -> None:
    """Plans the rewrite of the two comment lines, and lists the ones left alone.

    Args:
        repo: The project's root.
        plan: The upgrade's plan, which gets an edit action or a difference.
    """
    for path, (old, new) in COMMENT_LINES.items():
        raw = read_project_file(repo, path)
        if raw is None:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        result, edited = rewrite(text, old, new)
        if result != text:
            plan.actions.append(FileAction(path, "edit", result.encode("utf-8")))
        if edited:
            where = ("line " if len(edited) == 1 else "lines ") + ", ".join(map(str, edited))
            plan.differences.append((path, f"still names {OLD_NAME} on {where}. Upgrade "
                                           "rewrites only the exact comment troy-init wrote, "
                                           "so it left the file alone there."))
