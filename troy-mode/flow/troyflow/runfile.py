"""Reads and checks a prototype's run file (F12 design 4).

A run file is TOML next to its prototype: `docs/prototypes/<name>.run.toml`.
It holds only what the prototype says in words: the path map, the
environment, how each section starts, the programs that are not console
scripts, and the marks of single sections and commands.
"""

import re
import tomllib
from dataclasses import dataclass, field

from .transcript import Prototype

HOME, SCRATCH = "<home>", "<scratch>"
_TOP = {"paths", "environment", "start", "programs", "sections"}
_ENVIRONMENT = {"unset", "set"}
_START = {"copy", "mkdir", "setup"}
_SECTION = {"start", "replace", "write", "delete", "commands", "later", "skip", "files"}
_FEATURE = re.compile(r"F\d{2,3}")


class RunFileError(Exception):
    """A run file mistake, with the problem kind of the interface note."""

    def __init__(self, kind: str, message: str, section: str | None = None,
                 typed: str | None = None, **extra) -> None:
        super().__init__(message)
        self.kind, self.section, self.typed, self.extra = kind, section, typed, extra


@dataclass(frozen=True)
class RunPath:
    """A path of the run: `<home>` or `<scratch>`, then folder names.

    Attributes:
        text: The path as written in the run file.
        home: True when it starts with `<home>`.
        parts: The folder and file names after the placeholder.
    """

    text: str
    home: bool
    parts: tuple[str, ...]


@dataclass
class Start:
    """How a section starts: folders to copy, folders to make, and setup commands."""

    copy: list[tuple[str, RunPath]] = field(default_factory=list)
    mkdir: list[RunPath] = field(default_factory=list)
    setup: list[str] = field(default_factory=list)

    def describe(self) -> str:
        """Says what the start does, in the evidence's words."""
        parts = [f"copy `{source}` to `{target.text}`" for source, target in self.copy]
        parts += [f"make `{p.text}`" for p in self.mkdir]
        parts += [f"run `{c}`" for c in self.setup]
        return ", ".join(parts) or "no files"


@dataclass
class Plan:
    """A section's own table.

    Attributes:
        start: "default", "previous", "empty", or the Start that replaces the default.
        replace: (file, text, with) edits.
        write: (file, text) files to write.
        delete: Files to delete.
        commands: The run line and the reason, by typed line.
        later: (feature, typed or None) marks.
        skip: (reason, typed or None) marks.
        files: (file, block number from 1) comparisons.
    """

    start: object = "default"
    replace: list[tuple[RunPath, str, str]] = field(default_factory=list)
    write: list[tuple[RunPath, str]] = field(default_factory=list)
    delete: list[RunPath] = field(default_factory=list)
    commands: dict[str, tuple[str, str]] = field(default_factory=dict)
    later: list[tuple[str, str | None]] = field(default_factory=list)
    skip: list[tuple[str, str | None]] = field(default_factory=list)
    files: list[tuple[RunPath, int]] = field(default_factory=list)


@dataclass
class RunFile:
    """A checked run file."""

    paths: list[tuple[str, RunPath]] = field(default_factory=list)
    unset: list[str] = field(default_factory=list)
    set: dict[str, str] = field(default_factory=dict)
    start: Start = field(default_factory=Start)
    programs: dict[str, str] = field(default_factory=dict)
    sections: dict[str, Plan] = field(default_factory=dict)

    def plan(self, key: str) -> Plan:
        """Returns a section's plan, or an empty one."""
        return self.sections.get(key) or Plan()


def run_path(text: object, where: str) -> RunPath:
    """Reads a run path: `<home>` or `<scratch>`, then names, with \\ or / between them.

    Raises:
        RunFileError: Not a string, no placeholder, or a path that leaves the scratch folder.
    """
    if not isinstance(text, str):
        raise RunFileError("run-file", f"{where} must be a string")
    for mark, home in ((HOME, True), (SCRATCH, False)):
        if text == mark or text.startswith(mark + "\\") or text.startswith(mark + "/"):
            parts = tuple(p for p in re.split(r"[\\/]", text[len(mark):]) if p not in ("", "."))
            depth, lowest = 0, -1 if home else 0
            for part in parts:
                depth += -1 if part == ".." else 1
                if depth < lowest:
                    raise RunFileError("run-file", f"{where} {text!r} leaves the scratch folder")
            return RunPath(text, home, parts)
    raise RunFileError("run-file", f"{where} {text!r} does not start with {HOME} or {SCRATCH}")


def _keys(table: object, allowed: set[str], where: str) -> dict:
    """Checks that a value is a table with known keys only."""
    if not isinstance(table, dict):
        raise RunFileError("run-file", f"{where} must be a table")
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise RunFileError("run-file", f"{where} has unknown keys: {', '.join(unknown)}")
    return table


def _table(value: object, where: str) -> dict:
    """Checks that a value is a table, with any keys."""
    if not isinstance(value, dict):
        raise RunFileError("run-file", f"{where} must be a table")
    return value


def _strings(value: object, where: str) -> list[str]:
    """Checks a list of strings."""
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise RunFileError("run-file", f"{where} must be a list of strings")
    return value


def _entries(value: object, where: str, need: set[str], may: set[str] = frozenset()) -> list:
    """Checks a list of tables with the needed keys, and the optional ones."""
    if not isinstance(value, list):
        raise RunFileError("run-file", f"{where} must be a list of tables")
    for entry in value:
        _keys(entry, need | set(may), f"an entry of {where}")
        missing = sorted(need - set(entry))
        if missing:
            raise RunFileError("run-file", f"an entry of {where} lacks {', '.join(missing)}")
    return value


def _text(entry: dict, key: str, where: str) -> str:
    """Reads one string value of an entry."""
    value = entry[key]
    if not isinstance(value, str):
        raise RunFileError("run-file", f"{key} in {where} must be a string")
    return value


def read_start(table: object, where: str) -> Start:
    """Reads [start] or a section's start table."""
    data = _keys(table, _START, where)
    start = Start()
    for entry in _entries(data.get("copy", []), f"{where} copy", {"from", "to"}):
        source = _text(entry, "from", f"{where} copy").replace("\\", "/").strip("/")
        if not source or ".." in source.split("/"):
            raise RunFileError("run-file", f"{where} copy from {source!r} is not a repository "
                                           "path")
        start.copy.append((source, run_path(entry["to"], f"{where} copy to")))
    start.mkdir = [run_path(p, f"{where} mkdir") for p in _strings(data.get("mkdir", []),
                                                                    f"{where} mkdir")]
    start.setup = _strings(data.get("setup", []), f"{where} setup")
    return start


def _plan(key: str, table: object) -> Plan:
    """Reads one [sections."<heading>"] table without the prototype."""
    where = f'[sections."{key}"]'
    data = _keys(table, _SECTION, where)
    plan = Plan()
    start = data.get("start")
    if start is None:
        plan.start = "default"
    elif isinstance(start, str):
        if start not in ("previous", "empty"):
            raise RunFileError("run-file", f"{where} start must be \"previous\", \"empty\", or "
                                           "a table", key)
        plan.start = start
    else:
        plan.start = read_start(start, f"{where} start")
    for entry in _entries(data.get("replace", []), f"{where} replace", {"file", "text", "with"}):
        plan.replace.append((run_path(entry["file"], f"{where} replace file"),
                             _text(entry, "text", where), _text(entry, "with", where)))
    for entry in _entries(data.get("write", []), f"{where} write", {"file", "text"}):
        plan.write.append((run_path(entry["file"], f"{where} write file"),
                           _text(entry, "text", where)))
    plan.delete = [run_path(p, f"{where} delete") for p in _strings(data.get("delete", []),
                                                                     f"{where} delete")]
    for entry in _entries(data.get("commands", []), f"{where} commands",
                          {"typed", "run", "reason"}):
        plan.commands[_text(entry, "typed", where).rstrip()] = (
            _text(entry, "run", where), _text(entry, "reason", where))
    for entry in _entries(data.get("later", []), f"{where} later", {"feature"}, {"typed"}):
        typed = _text(entry, "typed", where).rstrip() if "typed" in entry else None
        plan.later.append((_text(entry, "feature", where).strip(), typed))
    for entry in _entries(data.get("skip", []), f"{where} skip", {"reason"}, {"typed"}):
        typed = _text(entry, "typed", where).rstrip() if "typed" in entry else None
        plan.skip.append((_text(entry, "reason", where), typed))
    for entry in _entries(data.get("files", []), f"{where} files", {"path", "block"}):
        block = entry["block"]
        if not isinstance(block, int) or isinstance(block, bool) or block < 1:
            raise RunFileError("run-file", f"block in {where} files must be a whole number of 1 "
                                           "or more", key)
        plan.files.append((run_path(entry["path"], f"{where} files path"), block))
    return plan


def parse_run_file(text: str) -> RunFile:
    """Reads a run file's keys and types, without the prototype.

    Raises:
        RunFileError: Not TOML, an unknown key, a wrong type, or a bad run path.
    """
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise RunFileError("run-file", f"not valid TOML: {exc}") from exc
    _keys(data, _TOP, "the run file")
    run = RunFile()
    paths = _table(data.get("paths", {}), "[paths]")
    run.paths = [(proto, run_path(target, f"[paths] {proto!r}")) for proto, target in paths.items()]
    for proto, _ in run.paths:
        if not proto.strip():
            raise RunFileError("run-file", "[paths] has an empty prototype path")
    env = _keys(data.get("environment", {}), _ENVIRONMENT, "[environment]")
    run.unset = _strings(env.get("unset", []), "[environment] unset")
    values = _table(env.get("set", {}), "[environment] set")
    if not all(isinstance(v, str) for v in values.values()):
        raise RunFileError("run-file", "[environment] set values must be strings")
    run.set = dict(values)
    run.start = read_start(data.get("start", {}), "[start]")
    programs = _table(data.get("programs", {}), "[programs]")
    for name, path in programs.items():
        if not isinstance(path, str) or not path.strip():
            raise RunFileError("run-file", f"[programs] {name} must be a repository path")
    run.programs = dict(programs)
    sections = _table(data.get("sections", {}), "[sections]")
    run.sections = {key: _plan(key, table) for key, table in sections.items()}
    return run


def check_against(run: RunFile, prototype: Prototype, features: set[str]) -> None:
    """Checks a run file against its prototype and the features table.

    Raises:
        RunFileError: A section that does not exist, a `typed` line that is
            not in its section, a `later` feature not in the table, a missing
            block, or a first section that starts from the previous one.
    """
    first = next((s.key for s in prototype.sections if s.lines), None)
    for key, plan in run.sections.items():
        section = prototype.section(key)
        if section is None:
            raise RunFileError("unknown-section", f"[sections.\"{key}\"] names no section of the "
                                                  "prototype", key)
        if plan.start == "previous" and key == first:
            raise RunFileError("run-file", f"the first section, {key!r}, cannot start from the "
                                           "previous one", key)
        typed = section.typed_lines()
        named = list(plan.commands) + [t for _, t in plan.later if t] + \
            [t for _, t in plan.skip if t]
        for line in named:
            if line not in typed:
                raise RunFileError("unknown-command", f"{line!r} is no PS> line of section "
                                                      f"{key!r}", key, line)
        for feature, line in plan.later:
            if not _FEATURE.fullmatch(feature) or feature not in features:
                raise RunFileError("unknown-later-feature", f"later names {feature!r}, which is "
                                                            "not in the features table", key, line)
        for path, block in plan.files:
            if block > len(section.blocks):
                raise RunFileError("missing-block", f"files names block {block} of section "
                                                    f"{key!r}, which has {len(section.blocks)}",
                                   key)
