"""What a step will do to a project, and doing it (design section 3.3).

A step first builds a Plan without touching the project. Only when the plan
has no problem and no conflict, and the run is not a dry run, does apply()
write it. So a stopped step changes nothing.
"""

import hashlib
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import InitError
from .gitops import config_set

ACTIONS = ("create", "replace", "append", "edit", "delete", "keep")
# Paths troy-init writes but never stages: the progress file is local (Q8).
LOCAL_ONLY = (".troy-mode/progress.md",)


def lf_bytes(text: str) -> bytes:
    """Encodes text as UTF-8 with LF line endings."""
    return text.replace("\r\n", "\n").encode("utf-8")


def edited_bytes(text: str, original: bytes | None) -> bytes:
    """Encodes the new text of a file edited in place, with the file's line endings.

    A Windows checkout with core.autocrlf has CRLF endings. A file troy-init
    edits keeps them, so the edit is the only change in the working tree; a
    file that does not exist yet gets LF, as every file troy-init creates.

    Args:
        text: The file's new text, with LF or CRLF endings.
        original: The file's bytes before the edit, or None when it is new.
    """
    data = lf_bytes(text)
    if original is not None and b"\r\n" in original:
        return data.replace(b"\n", b"\r\n")
    return data


def file_hash(data: bytes) -> str:
    """SHA-256 of a file's bytes with CRLF turned into LF.

    A Windows checkout with core.autocrlf has CRLF endings, so hashing the LF
    form lets upgrade tell an unchanged file from an edited one there too.
    """
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def read_project_file(repo: Path, path: str) -> bytes | None:
    """Reads a project file's bytes, or None when it does not exist.

    Raises:
        InitError: The path exists but cannot be read.
    """
    target = repo / path
    if not target.exists():
        return None
    try:
        return target.read_bytes()
    except OSError as exc:
        raise InitError(f"cannot read {target}: {exc}") from exc


@dataclass
class FileAction:
    """One file a step creates, changes, deletes, or keeps.

    Attributes:
        path: Repository path with "/" separators.
        action: One of ACTIONS.
        content: The bytes to write: LF endings, or for an edit or append the
            endings the file has (edited_bytes); None for delete and keep.
        owned: True for a file troy-init owns, whose hash goes into the record.
        executable: True for a git hook, staged with --chmod=+x.
        generated: True for a file a tool writes after apply(), such as the
            lock uv compiles (design 5.4); apply() leaves it alone.
    """

    path: str
    action: str
    content: bytes | None = None
    owned: bool = False
    executable: bool = False
    generated: bool = False


@dataclass
class Plan:
    """Everything a step will do and report.

    Attributes:
        command: "setup", "lang", or "upgrade".
        version: The plugin's version.
        plugin: The plugin's name, for the text report.
        actions: One entry per file.
        conflicts: (path, reason) for files in the way.
        problems: Failed preconditions.
        git_config: Keys and values to set in the repository's git config.
        hooks_path: What core.hooksPath is set to, or None.
        email: Setup's commit email check, or None.
        differences: (path, message) for files upgrade leaves alone.
        notes: Free-text notes for the report.
        next_steps: What the caller does next.
        extra: Report keys only one step has, such as the language step's.
        env: The language step's environment work (design 5.4), or None.
    """

    command: str
    version: str
    plugin: str = ""
    actions: list[FileAction] = field(default_factory=list)
    conflicts: list[tuple[str, str]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    git_config: dict[str, str] = field(default_factory=dict)
    hooks_path: str | None = None
    email: dict | None = None
    differences: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    env: Any = None

    @property
    def blocked(self) -> bool:
        """True when a precondition failed or a file is in conflict."""
        return bool(self.problems or self.conflicts)

    @property
    def changed(self) -> bool:
        """True when at least one file is created, changed, or deleted."""
        return any(a.action != "keep" for a in self.actions)

    def stage(self) -> list[str]:
        """The sorted paths to git add: every changed file except local ones."""
        return sorted(a.path for a in self.actions
                      if a.action != "keep" and a.path not in LOCAL_ONLY)

    def executable(self) -> list[str]:
        """The staged paths to add with --chmod=+x."""
        return sorted(a.path for a in self.actions if a.executable and a.action != "keep"
                      and a.action != "delete")


def _write(target: Path, item: FileAction) -> None:
    """Writes one file's bytes, and the executable bit for a git hook."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(item.content or b"")
    if item.executable:
        mode = target.stat().st_mode
        target.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def apply(repo: Path, plan: Plan) -> None:
    """Writes a plan's files and git config into the project.

    Args:
        repo: The repository root.
        plan: A plan with no problem and no conflict.

    Raises:
        InitError: A file cannot be written, or git fails.
    """
    if plan.blocked:
        raise InitError("a stopped plan cannot be applied")
    for item in plan.actions:
        target = repo / item.path
        try:
            if item.action == "delete":
                target.unlink(missing_ok=True)
            elif item.action != "keep" and not item.generated:
                _write(target, item)
        except OSError as exc:
            raise InitError(f"cannot write {target}: {exc}") from exc
    for key, value in plan.git_config.items():
        config_set(repo, key, value)


def exists(repo: Path, path: str) -> bool:
    """True when a repository path exists as a file, folder, or link."""
    return os.path.lexists(repo / path)


@dataclass
class Saved:
    """A project's files as they were before a step wrote them.

    Attributes:
        files: Each path the step touches and its old bytes, None if missing.
        folders: Folders that did not exist yet, deepest first.
    """

    files: dict[str, bytes | None]
    folders: list[Path]


def save(repo: Path, plan: Plan) -> Saved:
    """Records the files a plan touches, so restore() can put them back.

    Raises:
        InitError: A file cannot be read.
    """
    files, folders = {}, set()
    for item in plan.actions:
        if item.action == "keep":
            continue
        files[item.path] = read_project_file(repo, item.path)
        parent = (repo / item.path).parent
        while parent != repo and not parent.exists():
            folders.add(parent)
            parent = parent.parent
    return Saved(files, sorted(folders, key=lambda p: len(p.parts), reverse=True))


def restore(repo: Path, saved: Saved) -> None:
    """Puts the files back as save() found them, and removes the new folders.

    Raises:
        InitError: A file cannot be written.
    """
    for path, content in saved.files.items():
        target = repo / path
        try:
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(content)
        except OSError as exc:
            raise InitError(f"cannot restore {target}: {exc}") from exc
    for folder in saved.folders:
        try:
            folder.rmdir()
        except OSError:
            pass
