"""Filling in the files setup writes from templates (design sections 4.2 to 4.4)."""

import json
import re
import tomllib

from .errors import InitError

_GUIDANCE = re.compile(r"[ \t]*<!--\s*template:.*?-->[ \t]*(?:\n|$)", re.DOTALL)
_MARKER = re.compile(r"(?<!\$)\{\{[^{}\n]+\}\}")
_EMAIL_LINE = re.compile(r"^# commit_email = .*$", re.MULTILINE)
_PROGRESS_LINE = re.compile(r"^- ([^:]+): .*\{\{.*$", re.MULTILINE)
_LINE_WIDTH = 99
_D49_NOTE = (
    "# troy-init filled in the patterns of every language pack, so that a pack's\n"
    "# files already have their classes when the language step's PR is checked\n"
    "# (F06 design D49).\n"
    "#\n"
)


def strip_guidance(text: str) -> str:
    """Removes every <!-- template: ... --> comment and the blank lines it leaves."""
    text = _GUIDANCE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def check_filled(text: str, source: str) -> str:
    """Returns text unchanged, or raises when a fill-in marker is left.

    Raises:
        InitError: A {{marker}} remains, which means the template changed shape.
    """
    left = _MARKER.search(text)
    if left:
        raise InitError(f"{source} still has the marker {left.group(0)} after filling in")
    return text


def toml_list(key: str, items: list[str]) -> str:
    """Formats `key = [...]` as TOML, wrapped under the opening bracket."""
    lead = f"{key} = ["
    lines, line = [], lead
    for index, item in enumerate(items):
        piece = json.dumps(item, ensure_ascii=False) + ("]" if index == len(items) - 1 else ",")
        if line != lead and len(line) + 1 + len(piece) > _LINE_WIDTH:
            lines.append(line)
            line = " " * len(lead) + piece
        else:
            line = line + ("" if line == lead else " ") + piece
    lines.append(line if items else lead + "]")
    return "\n".join(lines)


def _fill_paths(text: str, patterns: dict[str, list[str]]) -> str:
    """Replaces the empty [paths] lists of the default config with the patterns."""
    start = text.find("\n[paths]\n")
    end = text.find("\n[", start + 1)
    if start < 0 or end < 0:
        raise InitError("config.default.toml has no [paths] table")
    section = text[start:end]
    for key, items in patterns.items():
        line = re.compile(rf"^{re.escape(key)} = \[\]$", re.MULTILINE)
        if not line.search(section):
            raise InitError(f"config.default.toml has no empty [paths] {key} list")
        section = line.sub(lambda _: toml_list(key, items), section, count=1)
    section = section.replace("\n[paths]\n", "\n[paths]\n" + _D49_NOTE, 1)
    return text[:start] + section + text[end:]


def fill_config(default: str, email: str, patterns: dict[str, list[str]]) -> str:
    """Builds .troy-mode/config.toml from F02's default file (design 4.3).

    Args:
        default: The text of troy-mode/checks/config.default.toml.
        email: The commit email for R19.
        patterns: Every pack's [paths] patterns by key.

    Returns:
        The default file with commit_email and the patterns filled in, and
        every comment kept.

    Raises:
        InitError: The default file does not have the expected lines.
    """
    if not _EMAIL_LINE.search(default):
        raise InitError("config.default.toml has no '# commit_email = ' line")
    text = _EMAIL_LINE.sub(lambda _: f"commit_email = {json.dumps(email)}", default, count=1)
    text = _fill_paths(text, patterns)
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise InitError(f"the filled-in config is not valid TOML: {exc}") from exc
    return text


def fill_rules(template: str, project: str, date: str, source: str) -> str:
    """Fills in a rules table template (design 4.4).

    Args:
        template: The text of rules.md or rules.zh-CN.md.
        project: The project's name.
        date: The setup date, YYYY-MM-DD.
        source: The template's name, for errors.

    Returns:
        The table with the name and date filled in and no template comment.

    Raises:
        InitError: A marker is left.
    """
    text = template.replace("{{project-name}}", project).replace("{{init-date}}", date)
    return check_filled(strip_guidance(text), source)


def progress_values(date: str, has_requirements: bool) -> dict[str, str]:
    """The progress file's fields right after setup (design 4.2)."""
    next_action = ("architecture (the Architect writes docs/architecture.md)" if has_requirements
                   else "requirements (the Product Manager writes docs/requirements.md)")
    return {
        "Current version": "None yet",
        "Current feature": "None yet",
        "Stage": "setup. troy-init set up troy-mode in this project.",
        "Open PRs": "None",
        "Waiting on Troy": "Nothing",
        "Open issues": "None",
        "Next action": next_action,
        "Last updated": date,
    }


def fill_progress(template: str, values: dict[str, str]) -> str:
    """Fills in the progress template, one "- Field: value" line at a time.

    Raises:
        InitError: A field with a marker has no value, or a marker is left.
    """
    def line(match: re.Match) -> str:
        name = match.group(1)
        if name not in values:
            raise InitError(f"progress.md has the field {name!r}, which setup cannot fill in")
        return f"- {name}: {values[name]}"

    text = _PROGRESS_LINE.sub(line, template)
    return check_filled(strip_guidance(text), "progress.md")


def add_lines(existing: str | None, lines: list[str]) -> tuple[str, str]:
    """Adds lines to a .gitignore that may not exist (design 4.2).

    Args:
        existing: The current text, or None when the file does not exist.
        lines: Lines that must be in the file.

    Returns:
        The new text with LF endings, and the action: "create", "append", or
        "keep".
    """
    if existing is None:
        return "".join(f"{line}\n" for line in lines), "create"
    text = existing.replace("\r\n", "\n")
    present = {line.strip() for line in text.split("\n")}
    missing = [line for line in lines if line not in present]
    if not missing:
        return text, "keep"
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "".join(f"{line}\n" for line in missing), "append"
