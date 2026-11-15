"""Runs one prototype's sections in the scratch folder (F12 design 4.2, 5.3 to 5.6).

Each section starts from its run file's start, runs its commands in order in
one state, and compares each command's output with the prototype's. The
programs run the way Troy types them: the project's console scripts from its
environment, with this checkout's code, in a scratch home folder.
"""

import json
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import repo as git
from .checksteps import PREFIX_VARIABLE, find_mamba
from .realcompare import PathMap, decode, diff, lines_of, matches, normalize, spellings
from .runfile import RunFile, RunFileError, Start, check_against, parse_run_file
from .transcript import Prototype, classify, read_prototype, split_words

TIME_LIMIT = 60
NOT_RUN = "not run"
INSTALL_FIX = "uv pip install -e . --no-deps"
# Variables that a plain PowerShell does not set and that change how Python writes text.
PYTHON_VARIABLES = ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONLEGACYWINDOWSSTDIO", "PYTHONHOME",
                    "PYTHONSTARTUP")
PYCACHE = ".pycache"
OTHER = ("a pipeline, a redirection, or a command that is not a program of this project; the "
         "real run does not run it (F12 design 5.3)")
# One line, because a .bat launcher of python cuts a -c argument at its first line break.
_LOCATION = ("import importlib, sys; m = importlib.import_module(sys.argv[1]); "
             "print(getattr(m, '__file__', None) or list(getattr(m, '__path__', ['']))[0]); "
             "print(sys.version.split()[0])")
_FLAGS = re.IGNORECASE if os.name == "nt" else 0


@dataclass
class Item:
    """One prototype to run: its repository path and the features of its Feature cell."""

    file: str
    features: list[str]


@dataclass
class Run:
    """The state of one real run, shared by every prototype."""

    repo: object
    item: str | None
    accepted: set[str]
    known: set[str]
    scripts: dict[str, str]
    config: object
    scratch: Path
    notes: list[str]
    problems: list[dict] = field(default_factory=list)
    out_of_date: list[dict] = field(default_factory=list)
    prefix: Path | None = None
    env_error: str | None = None
    env_name: str | None = None
    python: str | None = None
    located: dict[str, str | None] = field(default_factory=dict)
    blobs: dict[str, dict[str, bytes]] = field(default_factory=dict)
    used: set[str] = field(default_factory=set)
    hidden: list[tuple[str, str]] = field(default_factory=list)

    def problem(self, kind: str, message: str, **where) -> None:
        """Records a problem once."""
        entry = {"kind": kind, "message": message}
        entry.update({k: v for k, v in where.items() if v is not None})
        if entry not in self.problems:
            self.problems.append(entry)

    def hide(self, text: str) -> str:
        """Shows the checkout's and the environment's folders by name, so no local path shows."""
        for real, shown in self.hidden:
            text = re.sub(re.escape(real), lambda _m, s=shown: s, text, flags=_FLAGS)
        return text

    def add_hidden(self, folder: Path, shown: str) -> None:
        """Adds a folder's spellings to those that evidence shows by name."""
        try:
            found = spellings(folder) if folder.exists() else [str(folder)]
        except OSError:
            found = [str(folder)]
        self.hidden = sorted(self.hidden + [(s, shown) for s in found],
                             key=lambda pair: len(pair[0]), reverse=True)


@dataclass
class Place:
    """Where one prototype runs: the path map, the base environment, and its run file."""

    pathmap: PathMap
    env: dict
    runfile: RunFile
    names: set[str]
    where: dict = field(default_factory=dict)


# ------------------------------------------------------------------ programs


def with_extension(path: Path) -> Path | None:
    """Finds a program file: on Windows, the path with each PATHEXT extension first."""
    if os.name != "nt":
        return path if path.is_file() else None
    extensions = [e for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if e]
    for candidate in [path.with_name(path.name + e.lower()) for e in extensions]:
        if candidate.is_file():
            return candidate
    return path if path.is_file() and path.suffix else None


def environment(run: Run) -> Path | None:
    """Finds the project's environment once: TROY_MODE_ENV_PREFIX, else mamba (design 5.4)."""
    if run.prefix is not None or run.env_error is not None:
        return run.prefix
    name = run.config.lang.get("environment")
    given = os.environ.get(PREFIX_VARIABLE)
    if given:
        run.prefix, run.env_name = Path(given), name or Path(given).name
    elif not name:
        run.env_error = "the config at HEAD has no [lang] environment"
    else:
        run.prefix, run.env_error = _from_mamba(run, name)
        run.env_name = name
    if run.prefix is not None:
        run.add_hidden(run.prefix, "<environment>")
    return run.prefix


def _from_mamba(run: Run, name: str) -> tuple[Path | None, str | None]:
    """Finds a named environment in `mamba env list --json`."""
    try:
        proc = subprocess.run([find_mamba(run.notes), "env", "list", "--json"],
                              capture_output=True, timeout=TIME_LIMIT)
        data = json.loads(proc.stdout.decode("utf-8", "replace"))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return None, f"mamba env list failed: {exc}"
    folders = [Path(p) for p in data.get("envs", []) if isinstance(p, str)]
    if name == "base" and data.get("root_prefix"):
        return Path(data["root_prefix"]), None
    found = next((f for f in folders if f.name == name), None)
    return (found, None) if found else (None, f"mamba lists no environment named {name}")


def _env_python(prefix: Path) -> Path | None:
    """The environment's Python."""
    return with_extension(prefix / "python") if os.name == "nt" \
        else with_extension(prefix / "bin" / "python")


def env_python_version(run: Run) -> str | None:
    """The Python version of the project's environment, for the report, or None."""
    prefix = environment(run)
    python = _env_python(prefix) if prefix is not None else None
    if python is None:
        return None
    try:
        proc = subprocess.run([str(python), "-c", "import sys; print(sys.version.split()[0])"],
                              capture_output=True, stdin=subprocess.DEVNULL, timeout=TIME_LIMIT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    version = proc.stdout.decode("utf-8", "replace").strip()
    return version if proc.returncode == 0 and version else None


def _program(run: Run, place: Place, name: str, env: dict) -> list[str] | None:
    """Finds a program; records a problem and returns None when it cannot start."""
    programs = place.runfile.programs
    if name in programs:
        found = with_extension(run.repo.root / programs[name])
        if found is None:
            run.problem("program-not-found", f"{name}: {programs[name]} does not exist in the "
                                             "checkout; build it first", program=name)
        return [str(found)] if found else None
    prefix = environment(run)
    if prefix is None:
        run.problem("environment", f"no environment for {name}: {run.env_error}. Set "
                                   f"{PREFIX_VARIABLE}, or create the environment (F06 design "
                                   "5.4).", program=name)
        return None
    folder = prefix / "Scripts" if os.name == "nt" else prefix / "bin"
    found = with_extension(folder / name)
    if found is None:
        run.problem("program-not-found", f"{name} is not installed in the environment "
                                         f"{run.env_name}: run `{INSTALL_FIX}` in it",
                    program=name, fix=INSTALL_FIX)
        return None
    return [str(found)] if _located(run, place, name, env) else None


def _located(run: Run, place: Place, name: str, env: dict) -> bool:
    """Checks once that a console script's package lies inside this checkout (design 5.4)."""
    package = run.scripts[name].split(":", 1)[0].split(".", 1)[0].strip()
    if package in run.located:
        return run.located[package] is None
    python = _env_python(run.prefix)
    message = None
    if python is None:
        message = f"the environment {run.env_name} has no python to check where {package} lies"
    else:
        try:
            proc = subprocess.run([str(python), "-c", _LOCATION, package], capture_output=True,
                                  stdin=subprocess.DEVNULL, env=env, cwd=place.pathmap.home,
                                  timeout=TIME_LIMIT)
            out = proc.stdout.decode("utf-8", "replace").splitlines()
            if proc.returncode != 0 or len(out) < 2:
                err = proc.stderr.decode("utf-8", "replace").strip()[-300:]
                message = f"{name}: the environment's python could not import {package}: {err}"
            else:
                run.python = out[1].strip()
                if not _inside(Path(out[0].strip()), run.repo.root):
                    message = f"{name} runs {package} from {out[0].strip()}, which is not inside " \
                              "this checkout"
        except (OSError, subprocess.TimeoutExpired) as exc:
            message = f"cannot run the environment's python: {exc}"
    run.located[package] = message
    if message:
        run.problem("code-location", message, program=name)
    return message is None


def _inside(path: Path, root: Path) -> bool:
    """Tells whether a path lies inside a folder."""
    try:
        Path(os.path.realpath(path)).relative_to(os.path.realpath(root))
        return True
    except ValueError:
        return False


def base_env(run: Run, activate: bool) -> dict:
    """The environment every command of a prototype starts from (design 5.4)."""
    env = {k: v for k, v in os.environ.items() if k.upper() not in PYTHON_VARIABLES}
    home = run.scratch / "home"
    roots = run.config.lang.get("source_roots") or []
    env["PYTHONPATH"] = os.pathsep.join(str(run.repo.root / r) for r in roots)
    env["PYTHONPYCACHEPREFIX"] = str(run.scratch / PYCACHE)
    env["HOME"] = env["USERPROFILE"] = str(home)
    env["APPDATA"] = str(home / "AppData" / "Roaming")
    env["LOCALAPPDATA"] = str(home / "AppData" / "Local")
    if os.name == "nt":
        env["HOMEDRIVE"], env["HOMEPATH"] = os.path.splitdrive(str(home))
    else:
        env.update(XDG_CONFIG_HOME=str(home / ".config"),
                   XDG_DATA_HOME=str(home / ".local" / "share"),
                   XDG_CACHE_HOME=str(home / ".cache"),
                   XDG_STATE_HOME=str(home / ".local" / "state"))
    prefix = environment(run) if activate else None
    if prefix is not None:
        folders = [prefix, prefix / "Library" / "mingw-w64" / "bin",
                   prefix / "Library" / "usr" / "bin", prefix / "Library" / "bin",
                   prefix / "Scripts", prefix / "bin"] if os.name == "nt" else [prefix / "bin"]
        key = next((k for k in env if k.upper() == "PATH"), "PATH")
        env[key] = os.pathsep.join([str(f) for f in folders] + [env.get(key, "")])
    return env


# ------------------------------------------------------------------ the scratch folder


def remove(path: Path) -> None:
    """Deletes a file or folder, read-only ones too."""
    def retry(func, target, _info):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, onerror=retry)
    elif path.exists() or path.is_symlink():
        os.chmod(path, stat.S_IWRITE)
        path.unlink()


def _reset(scratch: Path) -> None:
    """Empties the scratch folder and makes an empty home."""
    for child in scratch.iterdir():
        if child.name != PYCACHE:
            remove(child)
    (scratch / "home").mkdir()


def tracked(run: Run, source: str) -> dict[str, bytes]:
    """The files git tracks at HEAD under a folder, or the file itself, with their bytes."""
    if source in run.blobs:
        return run.blobs[source]
    root = str(run.repo.root)
    proc = subprocess.run(["git", "-C", root, "ls-tree", "-r", "-z", "HEAD", "--", source],
                          capture_output=True)
    entries = []
    for entry in proc.stdout.decode("utf-8", "replace").split("\0"):
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob" and (path == source
                                                       or path.startswith(source + "/")):
            entries.append((parts[2], path))
    found: dict[str, bytes] = {}
    if entries:
        batch = subprocess.run(["git", "-C", root, "cat-file", "--batch"], capture_output=True,
                               input="".join(f"{sha}\n" for sha, _ in entries).encode())
        data, at = batch.stdout, 0
        for _, path in entries:
            head_end = data.index(b"\n", at)
            size = int(data[at:head_end].split()[2])
            found[path] = data[head_end + 1:head_end + 1 + size]
            at = head_end + 1 + size + 1
    run.blobs[source] = found
    return found


def _write(path: Path, data: bytes) -> None:
    """Writes a file and the folders above it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _map_text(place: Place, text: str) -> tuple[str | None, str | None]:
    """Maps a typed text to the run's folders; returns it, or the absolute path not covered."""
    marked = place.pathmap.to_marks(text)
    stray = place.pathmap.unmapped(marked)
    if stray:
        return None, stray
    return place.pathmap.from_marks(marked), None


def _map_words(place: Place, text: str) -> tuple[list[str] | None, str | None]:
    """Splits a command line into words, then maps each word to the run's folders.

    Splitting first keeps a run folder whose name holds spaces in one word.

    Returns:
        The words, or None and the first absolute path the path map does not cover.
    """
    words = []
    for word in split_words(text):
        mapped, stray = _map_text(place, word)
        if stray:
            return None, stray
        words.append(mapped)
    return words, None


def _execute(place: Place, argv: list[str], env: dict) -> tuple:
    """Runs one program; returns its output, error output, exit code, and a time-out flag."""
    try:
        proc = subprocess.Popen(argv, cwd=place.pathmap.home, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=os.name != "nt")
    except OSError as exc:
        return b"", f"The program could not start: {exc.strerror or exc}".encode(), None, False
    try:
        out, err = proc.communicate(timeout=TIME_LIMIT)
        return out, err, proc.returncode, False
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = b"", b""
        return out, err, None, True


def _kill_tree(proc: subprocess.Popen) -> None:
    """Stops a program and every process it started, such as a launcher's Python."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        import signal  # POSIX only: the program runs in its own process group.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    proc.kill()


# ------------------------------------------------------------------ starting a section


class Stop(Exception):
    """Stops a section before its commands: its start failed. The problem is recorded."""


def _start(run: Run, place: Place, start: Start, env: dict) -> None:
    """Copies, makes folders, and runs setup commands.

    Raises:
        Stop: A setup command is no program, holds an unmapped path, cannot
            start, or does not exit with 0.
    """
    for source, target in start.copy:
        base = place.pathmap.real(target)
        for path, data in tracked(run, source).items():
            rel = path[len(source):].lstrip("/")
            _write(base.joinpath(*rel.split("/")) if rel else base, data)
    for folder in start.mkdir:
        place.pathmap.real(folder).mkdir(parents=True, exist_ok=True)
    for command in start.setup:
        if classify(command, place.names).kind != "program":
            _stop(run, place, "setup-failed", f"setup command {command!r} is not a program of "
                                              "this project")
        words, stray = _map_words(place, command)
        if stray:
            _stop(run, place, "unmapped-path", f"setup command {command!r} holds {stray}, an "
                                               "absolute path the path map does not cover")
        program = _program(run, place, words[0], env)
        if program is None:
            raise Stop(f"setup command {command!r} could not start; see the problems")
        run.used.add(words[0])
        out, err, code, late = _execute(place, program + words[1:], env)
        if late or code != 0:
            tail = run.hide(place.pathmap.to_prototype(decode(err or out)[0])).strip()[-300:]
            _stop(run, place, "setup-failed", f"setup command {command!r} "
                  f"{'timed out' if late else f'exited with {code}'}: {tail}")


def _stop(run: Run, place: Place, kind: str, message: str, **extra) -> None:
    """Records a problem of the section and stops it."""
    run.problem(kind, message, **place.where, **extra)
    raise Stop(message)


def _edit(run: Run, place: Place, plan) -> None:
    """Applies a section's replace, write, and delete edits, in that order.

    Raises:
        Stop: A replace text is not found exactly once, or a file is missing.
    """
    for target, old, new in plan.replace:
        path = place.pathmap.real(target)
        try:
            text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            _stop(run, place, "setup-failed", f"replace cannot read {target.text}: {exc}")
        count = text.count(old)
        if count != 1:
            _stop(run, place, "replace-count", f"replace finds {old!r} {count} times in "
                                               f"{target.text}; it must occur exactly once",
                  count=count)
        path.write_bytes(text.replace(old, new).encode("utf-8"))
    for target, text in plan.write:
        _write(place.pathmap.real(target), text.encode("utf-8"))
    for target in plan.delete:
        path = place.pathmap.real(target)
        if not path.exists():
            _stop(run, place, "setup-failed", f"delete names {target.text}, which does not "
                                              "exist")
        remove(path)


def _prepare(run: Run, place: Place, plan, env: dict) -> None:
    """Starts a section: the scratch folder, the environment, the start, and the edits.

    Raises:
        Stop: The start or an edit failed.
    """
    for name in place.runfile.unset:
        for key in [k for k in env if k.upper() == name.upper()]:
            del env[key]
    for name, value in place.runfile.set.items():
        mapped, stray = _map_text(place, value)
        if stray:
            _stop(run, place, "unmapped-path", f"[environment] set {name} holds {stray}, an "
                                               "absolute path the path map does not cover")
        env[name] = mapped
    if plan.start != "previous":
        _reset(run.scratch)
        start = place.runfile.start if plan.start == "default" else \
            Start() if plan.start == "empty" else plan.start
        _start(run, place, start, env)
    _edit(run, place, plan)


# ------------------------------------------------------------------ commands


def _entry(line, kind: str, own: bool) -> dict:
    """A command entry of the report, before it runs."""
    return {"line": line.number if line else None, "kind": kind,
            "typed": line.typed if line else "", "run": line.typed if line else "",
            "expected": list(line.output) if line else [], "real": None, "expected_exit": None,
            "exit": None, "result": NOT_RUN, "reason": "", "diff": "", "streams": "none",
            "own": own, "replaced": None}


def _compare(run: Run, place: Place, entry: dict, out: bytes, err: bytes, code: int | None,
             late: bool) -> None:
    """Compares a command's real output and exit code with the prototype's (design 5.6)."""
    out_text, out_ok = decode(out)
    err_text, err_ok = decode(err)
    joiner = "\n" if out_text and err_text and not out_text.endswith("\n") else ""
    real = lines_of(run.hide(place.pathmap.to_prototype(out_text + joiner + err_text)))
    expected = normalize(entry["expected"])
    entry["real"], entry["exit"] = real, code
    entry["streams"] = "both" if out and err else "stdout" if out else "stderr" if err else "none"
    reasons = []
    if late:
        reasons.append(f"it did not finish within {TIME_LIMIT} seconds")
    if not (out_ok and err_ok):
        reasons.append("its output is not UTF-8")
    if not matches(expected, real):
        reasons.append("its output differs from the prototype")
    if entry["expected_exit"] is not None and code != entry["expected_exit"]:
        reasons.append(f"its exit code is {code}, where the prototype shows "
                       f"{entry['expected_exit']}")
    notes = ["it writes to both standard output and standard error, so their order on screen "
             "is not proven"] if entry["streams"] == "both" else []
    entry["result"] = "mismatch" if reasons else "matches"
    entry["reason"] = "; ".join(reasons + notes)
    entry["diff"] = diff(expected, real) if reasons else ""


def _unmapped(run: Run, place: Place, entry: dict, stray: str) -> None:
    """Refuses a command that holds an absolute path the path map does not cover."""
    entry["reason"] = f"it holds {stray}, an absolute path the path map does not cover"
    run.problem("unmapped-path", entry["reason"], typed=entry["typed"], **place.where)


def _run_program(run: Run, place: Place, entry: dict, text: str, env: dict) -> None:
    """Runs one program command and compares it."""
    words, stray = _map_words(place, text)
    if stray:
        _unmapped(run, place, entry, stray)
        return
    run.used.add(words[0])
    program = _program(run, place, words[0], env)
    if program is None:
        entry["reason"] = f"{words[0]} could not start; see the problems"
        return
    out, err, code, late = _execute(place, program + words[1:], env)
    _compare(run, place, entry, out, err, code, late)


def _get_content(run: Run, place: Place, entry: dict, path_text: str) -> None:
    """Prints a file of the run, as Get-Content does, and compares it."""
    mapped, stray = _map_text(place, path_text)
    if stray:
        _unmapped(run, place, entry, stray)
        return
    path = Path(mapped)
    if not path.is_absolute():
        path = place.pathmap.home / path
    try:
        data = path.read_bytes()
    except OSError:
        shown = run.hide(place.pathmap.to_prototype(str(path)))
        message = f"Get-Content: Cannot find path '{shown}' because it does not exist."
        _compare(run, place, entry, b"", message.encode("utf-8"), None, False)
        return
    _compare(run, place, entry, data, b"", None, False)


def _set_env(run: Run, place: Place, env: dict, name: str, value: str) -> bool:
    """Applies a `$env:NAME = "value"` line; returns False when its value holds a stray path."""
    mapped, stray = _map_text(place, value)
    if stray:
        run.problem("unmapped-path", f"$env:{name} holds {stray}, an absolute path the path map "
                                     "does not cover", typed=f"$env:{name}", **place.where)
        return False
    for key in [k for k in env if k.upper() == name.upper()]:
        del env[key]
    if mapped:
        env[name] = mapped
    return True


def _steps(section, names: set[str]) -> list[tuple]:
    """The section's lines with their kinds; each $LASTEXITCODE goes to the program before it."""
    steps, last = [], None
    for line in section.lines:
        kind = classify(line.typed, names)
        if kind.kind == "exit":
            if last is not None and line.output and re.fullmatch(r"-?\d+", line.output[0].strip()):
                last[2]["exit"] = int(line.output[0].strip())
            continue
        step = (line, kind, {"exit": None})
        if kind.kind == "program":
            last = step
        steps.append(step)
    return steps


def _marks(plan, typed: str) -> tuple[list[str], str | None]:
    """The later features and the skip reason that apply to one typed line."""
    later = [f for f, t in plan.later if t is None or t == typed]
    skip = next((r for r, t in plan.skip if t == typed), None)
    if skip is None:
        skip = next((r for r, t in plan.skip if t is None), None)
    return later, skip


def _note_marks(run: Run, place: Place, plan, later: list[str], typed: str) -> list[str]:
    """Returns the features a line waits for, and lists the marks that are out of date."""
    waiting = [f for f in later if f not in run.accepted and f != run.item]
    for feature in later:
        if feature in waiting:
            continue
        mark = {"prototype": place.where["prototype"], "section": place.where["section"],
                "feature": feature, "typed": next((t for f, t in plan.later if f == feature
                                                   and (t is None or t == typed)), None)}
        if mark not in run.out_of_date:
            run.out_of_date.append(mark)
    return waiting


def _section(run: Run, item: Item, section, place: Place, broken: str | None) -> dict:
    """Runs one section and returns its part of the report."""
    plan = place.runfile.plan(section.key)
    place.where = {"prototype": item.file, "section": section.key}
    entry = {"heading": section.key, "start": plan.start if isinstance(plan.start, str)
             else "custom", "describe": describe(place.runfile, plan), "env": [], "commands": []}
    env = dict(place.env)
    stop = broken
    if stop is None:
        try:
            _prepare(run, place, plan, env)
        except Stop as exc:
            stop = f"the section could not start: {exc}"
    for line, kind, expect in _steps(section, place.names):
        if kind.kind == "env":
            entry["env"].append({"line": line.number, "name": kind.name, "value": kind.value})
            if stop is None and not _set_env(run, place, env, kind.name, kind.value):
                stop = "a $env: line holds an absolute path the path map does not cover"
            continue
        later, skip = _marks(plan, line.typed)
        waiting = _note_marks(run, place, plan, later, line.typed)
        own = run.item is not None and not waiting and (run.item in later
                                                        or run.item in item.features)
        command = _entry(line, kind.kind if kind.kind in ("program", "get-content") else "other",
                         own)
        command["expected_exit"] = expect["exit"]
        entry["commands"].append(command)
        if line.typed in plan.commands:
            command["run"], command["replaced"] = plan.commands[line.typed]
        if waiting:
            command["result"] = f"waits for {waiting[0]}"
        elif skip is not None:
            command["reason"] = skip
        elif stop is not None:
            command["reason"] = stop
        else:
            _command(run, place, command, kind, env)
    if stop is None:
        own = file_own(run, item, plan)
        entry["commands"] += [_file_check(run, place, section, path, block, own)
                              for path, block in plan.files]
    return entry


def _command(run: Run, place: Place, command: dict, kind, env: dict) -> None:
    """Runs one command line, as typed or as its run file replaces it."""
    if command["replaced"] is not None:
        kind = classify(command["run"], place.names)
        command["kind"] = kind.kind if kind.kind in ("program", "get-content") else "other"
    if kind.kind == "program":
        _run_program(run, place, command, command["run"], env)
    elif kind.kind == "get-content":
        _get_content(run, place, command, kind.value)
    else:
        command["reason"] = OTHER


def file_own(run: Run, item: Item, plan) -> bool:
    """Whether a section's file checks are the item's own: no wait for another feature."""
    marks = [f for f, t in plan.later if t is None]
    if any(f not in run.accepted and f != run.item for f in marks):
        return False
    return run.item is not None and (run.item in item.features or run.item in marks)


def _file_check(run: Run, place: Place, section, path, block: int, own: bool) -> dict:
    """Compares a file the program wrote with a fenced block of the section."""
    real = place.pathmap.real(path)
    shown = run.hide(place.pathmap.to_prototype(str(real)))
    entry = _entry(None, "file", own)
    entry.update(typed=f"file {shown}", run=f"file {shown}",
                 expected=list(section.blocks[block - 1]))
    try:
        data = real.read_bytes()
    except OSError:
        entry.update(result="mismatch", real=[], reason="the program wrote no such file",
                     diff=diff(normalize(entry["expected"]), []))
        return entry
    _compare(run, place, entry, data, b"", None, False)
    return entry


def describe(runfile: RunFile, plan) -> str:
    """Says how a section started, for the evidence."""
    if plan.start == "previous":
        start = "goes on from the previous section"
    elif plan.start == "empty":
        start = "no files"
    elif plan.start == "default":
        start = runfile.start.describe()
    else:
        start = plan.start.describe()
    edits = [f"replace {old!r} with {new!r} in `{t.text}`" for t, old, new in plan.replace]
    edits += [f"write `{t.text}`" for t, _ in plan.write]
    edits += [f"delete `{t.text}`" for t in plan.delete]
    return "; ".join([start] + edits)


# ------------------------------------------------------------------ one prototype


def _checked(run: Run, item: Item, proto: Prototype, text: str,
             path: str) -> tuple[RunFile, str | None]:
    """Parses and checks a run file; returns it, and the reason nothing runs when it is wrong."""
    try:
        runfile = parse_run_file(text)
        check_against(runfile, proto, run.known)
        starts = [runfile.start] + [p.start for p in runfile.sections.values()
                                    if isinstance(p.start, Start)]
        for source in [s for start in starts for s, _ in start.copy]:
            if not tracked(run, source):
                raise RunFileError("copy-untracked", f"copy from {source!r}: git tracks no file "
                                                     "there at HEAD")
        return runfile, None
    except RunFileError as exc:
        run.problem(exc.kind, f"{path}: {exc}", prototype=item.file, section=exc.section,
                    typed=exc.typed, **exc.extra)
        return RunFile(), f"the run file has a problem: {exc}"


def _needs_environment(proto: Prototype, runfile: RunFile, names: set[str]) -> bool:
    """Tells whether any command or setup of a prototype runs a console script."""
    texts = [line.typed for s in proto.sections for line in s.lines]
    texts += runfile.start.setup + [r for p in runfile.sections.values()
                                    for r, _ in p.commands.values()]
    texts += [c for p in runfile.sections.values() if isinstance(p.start, Start)
              for c in p.start.setup]
    for text in texts:
        kind = classify(text, names)
        if kind.kind == "program" and kind.name not in runfile.programs:
            return True
    return False


def run_prototype(run: Run, item: Item) -> dict:
    """Reads, checks, and runs one prototype; returns its part of the report."""
    entry = {"file": item.file, "features": item.features, "transcript": False,
             "run_file": None, "paths": [], "replaced": [], "sections": []}
    text = git.read(run.repo, "HEAD", item.file)
    if text is None:
        run.problem("missing-prototype", f"{item.file} is in the requirements' prototypes table "
                                         "but not in the commit", prototype=item.file)
        return entry
    proto = read_prototype(text)
    if not proto.has_transcript():
        return entry
    entry["transcript"] = True
    path = item.file[:-len(".md")] + ".run.toml"
    run_text = git.read(run.repo, "HEAD", path)
    if run_text is None:
        runfile, broken = RunFile(), f"{path} does not exist"
        run.problem("no-run-file", f"{item.file} has a transcript but no run file {path}",
                    prototype=item.file)
    else:
        entry["run_file"] = path
        runfile, broken = _checked(run, item, proto, run_text, path)
    names = set(run.scripts) | set(runfile.programs)
    activate = broken is None and _needs_environment(proto, runfile, names)
    place = Place(PathMap(run.scratch, runfile.paths), base_env(run, activate), runfile, names)
    entry["paths"] = [{"prototype": p, "run": t.text} for p, t in runfile.paths]
    entry["replaced"] = [{"section": key, "typed": typed, "run": line, "reason": why}
                         for key, plan in runfile.sections.items()
                         for typed, (line, why) in plan.commands.items()]
    for section in proto.sections:
        if section.lines or runfile.plan(section.key).files:
            entry["sections"].append(_section(run, item, section, place, broken))
    return entry
