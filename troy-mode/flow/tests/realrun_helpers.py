"""Shared fixtures for the F12 real-run tests (F12 design 15.1; F12 interface note).

A project here is a ``flow_helpers`` clone whose requirements hold a features
table and, unless a test leaves it out, a prototypes table (requirements
template 3.1). Its prototypes are Markdown files with ``PS> `` transcripts,
each with a run file beside it. Two programs run the transcripts:

- ``sample``, named in the run files' ``[programs]`` as ``build/sample``: a
  launcher in the clone's ignored ``build/`` folder, where a built program
  would be (a ``.bat`` that runs this Python on Windows, which the note's
  PATHEXT rule allows, and an executable script with a shebang elsewhere);
- ``wordcount``, the console script of ``pyproject.toml``, found in a fake
  environment folder that ``TROY_MODE_ENV_PREFIX`` names. Its launcher and
  the folder's ``python`` run this Python too. Its code is
  ``src/wordcount/cli.py`` at HEAD, which the launcher reaches only through
  the ``PYTHONPATH`` the engine sets.

Both run the same sample program, which writes UTF-8 bytes to the buffers
of the standard streams, so its output does not depend on Python's encoding
variables. When ``SAMPLE_LOG`` is set, it appends each call (its arguments
and its working folder) to that file, so a test can tell which commands ran
and where. The engine, ``troy_flow.py real-run``, runs as a subprocess;
nothing here imports it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Optional, Sequence

from flow_helpers import (
    F01, F02, F03, GITIGNORE, REQUIREMENTS, WORK_BRANCH, Fakes, FlowCase, Outcome, Project,
    base_files, base_step, new_dir, requirements_text, stages,
)

THREE = (F01, F02, F03)
CONSOLE = "wordcount"
CONSOLE_TARGET = "wordcount.cli:main"
PROGRAM = "sample"
PROGRAM_PATH = "build/sample"
PROGRAMS = f'[programs]\n{PROGRAM} = "{PROGRAM_PATH}"\n'
HOME_MAP = "[paths]\n'C:\\Users\\Troy' = '<home>'\n"
LABEL_RAN = "Ran for real on Troy's PC"
LABEL_TESTS = "Passes tests on main"
PIPES_SENTENCE = "Through pipes, not a console (F12 design section 10)."
DESCRIPTION_PARTS = ("Result", "Commands", "Adaptations", "Changes", "Points at later features",
                     "Not proven", "Real output")
PYTHON_VARIABLES = ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONLEGACYWINDOWSSTDIO", "PYTHONHOME",
                    "PYTHONSTARTUP")
EXAMPLE_DATA = {
    "tests/data/example/a.txt": "麻婆豆腐：郫县豆瓣酱 2 勺\n",
    "tests/data/example/b/c.txt": "alpha beta alpha\n",
}

# The sample program's table: each Chinese character takes two columns, so the
# spaces after it are fewer than after the same number of Latin letters.
TABLE_LINES = ("菜名" + " " * 8 + "份量" + " " * 2 + "做法",
               "麻婆豆腐" + " " * 4 + "2" + " " * 5 + "炒",
               "番茄炒蛋" + " " * 4 + "3" + " " * 5 + "炒",
               "tofu soup" + " " * 3 + "10" + " " * 4 + "煮")
# The second row as a program that gives each character one column would print it.
NARROW_ROW = "麻婆豆腐" + " " * 8 + "2" + " " * 5 + "炒"

_SAMPLE_SOURCE = r'''"""The sample program of the F12 real-run tests.

It writes UTF-8 bytes to the buffers of the standard streams, so what it
prints does not depend on Python's encoding variables.
"""
import json
import os
import shutil
import subprocess
import sys

TABLE = @TABLE@


def out(text):
    """Writes text to the standard output as UTF-8."""
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()


def err(text):
    """Writes text to the standard error as UTF-8."""
    sys.stderr.buffer.write(text.encode("utf-8"))
    sys.stderr.buffer.flush()


def log(args):
    """Appends the call to the file SAMPLE_LOG names, when it is set."""
    path = os.environ.get("SAMPLE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"argv": args, "cwd": os.getcwd()}) + "\n")


def inside(value, base):
    """The path of value relative to base, with /, or None when it lies outside."""
    try:
        rel = os.path.relpath(os.path.realpath(value), os.path.realpath(base))
    except ValueError:
        return None
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        return None
    return rel.replace(os.sep, "/")


def listing(folder):
    """Every folder (with a trailing /) and file under a folder, relative, sorted."""
    found = []
    for root, dirs, files in os.walk(folder):
        rel = os.path.relpath(root, folder)
        prefix = "" if rel == "." else rel.replace(os.sep, "/") + "/"
        found += [prefix + name + "/" for name in dirs]
        found += [prefix + name for name in files]
    return sorted(found)


def short_path(path):
    """The Windows short (8.3) spelling of an existing path."""
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    size = ctypes.windll.kernel32.GetShortPathNameW(path, buffer, 32768)
    return buffer.value if size else path


def write(path, text):
    """Writes text as UTF-8, making the folders first."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(text.encode("utf-8"))


def show_list(folder):
    """Prints a folder's listing, or fails when it is no folder."""
    if not os.path.isdir(folder):
        err("no such folder: " + folder + "\n")
        return 2
    out("".join(entry + "\n" for entry in listing(folder)))
    return 0


def main(argv=None):
    """Runs one sample command; returns the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    log(args)
    if not args:
        err("usage: sample <command> [arguments]\n")
        return 64
    cmd, rest = args[0], args[1:]
    if cmd == "say":
        out(" ".join(rest) + "\n")
    elif cmd == "echo":
        out("".join("[" + arg + "]\n" for arg in rest))
    elif cmd == "table":
        out("".join(line + "\n" for line in TABLE))
    elif cmd == "lines":
        out("".join("row %02d\n" % n for n in range(int(rest[0]), int(rest[1]) + 1)))
    elif cmd == "long":
        out("".join("long output line %05d %s\n" % (n, "." * 24)
                    for n in range(1, int(rest[0]) + 1)))
    elif cmd == "code":
        if rest[1:]:
            out(" ".join(rest[1:]) + "\n")
        return int(rest[0])
    elif cmd == "fail":
        err(" ".join(rest[1:]) + "\n")
        return int(rest[0])
    elif cmd == "err":
        err(" ".join(rest) + "\n")
    elif cmd == "both":
        err(rest[1] + "\n")
        out(rest[0] + "\n")
    elif cmd == "trailing":
        out("x  \t\ny\t \r\n\n  \n\n")
    elif cmd == "crlf":
        out("first\r\nsecond\r\n")
    elif cmd == "bytes":
        sys.stdout.buffer.write(b"caf\xe9\n")
        sys.stdout.buffer.flush()
    elif cmd == "env":
        for name in rest:
            value = os.environ.get(name)
            out(name + ("=" + value if value is not None else " is not set") + "\n")
    elif cmd == "homes":
        for name in rest:
            if name == "HOMEDRIVE+HOMEPATH":
                drive, path = os.environ.get("HOMEDRIVE"), os.environ.get("HOMEPATH")
                value = drive + path if drive is not None and path is not None else None
            else:
                value = os.environ.get(name)
            if value is None:
                out(name + ": not set\n")
                continue
            rel = inside(value, os.getcwd())
            if rel is None:
                out(name + ": outside the working folder\n")
            else:
                out(name + ": home" + ("" if rel == "." else "/" + rel) + "\n")
    elif cmd == "in-scratch":
        scratch = os.path.dirname(os.path.abspath(os.getcwd()))
        for name in rest:
            value = os.environ.get(name)
            where = inside(value, scratch) if value else None
            out(name + (": inside the scratch folder" if where not in (None, ".")
                        else ": not inside the scratch folder") + "\n")
    elif cmd == "write":
        write(rest[0], " ".join(rest[1:]) + "\n")
    elif cmd == "write-in":
        write(os.path.join(rest[0], rest[1]), " ".join(rest[2:]) + "\n")
    elif cmd == "cat":
        with open(rest[0], "rb") as handle:
            sys.stdout.buffer.write(handle.read())
        sys.stdout.buffer.flush()
    elif cmd == "cat-in":
        with open(os.path.join(rest[0], rest[1]), "rb") as handle:
            sys.stdout.buffer.write(handle.read())
        sys.stdout.buffer.flush()
    elif cmd == "ls":
        return show_list(rest[0])
    elif cmd == "ls-env":
        return show_list(os.environ.get(rest[0], ""))
    elif cmd == "where":
        out(os.path.abspath(rest[0]) + "\n")
    elif cmd == "where-posix":
        out(os.path.abspath(rest[0]).replace("\\", "/") + "\n")
    elif cmd == "where-upper":
        out(os.path.abspath(rest[0]).upper() + "\n")
    elif cmd == "where-long":
        out(os.path.realpath(rest[0]) + "\n")
    elif cmd == "where-short":
        out(short_path(os.path.abspath(rest[0])) + "\n")
    elif cmd == "where-in":
        out(os.path.abspath(os.path.join(*rest)) + "\n")
    elif cmd == "run":
        found = shutil.which(rest[0])
        if found is None:
            err(rest[0] + " is not on the PATH\n")
            return 3
        proc = subprocess.run([found, *rest[1:]], capture_output=True,
                              stdin=subprocess.DEVNULL, check=False)
        sys.stdout.buffer.write(proc.stdout)
        sys.stdout.buffer.flush()
        return proc.returncode
    elif cmd == "stdin":
        data = sys.stdin.buffer.read() if sys.stdin is not None else b""
        out("stdin: %d bytes\n" % len(data))
    elif cmd == "sleep":
        import time
        out("started\n")
        sys.stdout.buffer.flush()
        time.sleep(float(rest[0]))
        out("woke up\n")
    else:
        err("unknown command: " + cmd + "\n")
        return 64
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
SAMPLE_SOURCE = _SAMPLE_SOURCE.replace("@TABLE@", repr(TABLE_LINES))


# ------------------------------------------------------------- launchers

def _bat(path: Path, lines: Sequence[str]) -> Path:
    """Writes a Windows batch file that runs the lines and keeps the last exit code.

    Args:
        path: The ``.bat`` file.
        lines: The commands after ``@echo off``.

    Returns:
        The path.
    """
    body = "@echo off\r\n" + "".join(line + "\r\n" for line in lines)
    path.write_bytes((body + "exit /b %ERRORLEVEL%\r\n").encode("utf-8"))
    return path


def _sh(path: Path, lines: Sequence[str]) -> Path:
    """Writes an executable POSIX shell script.

    Args:
        path: The script.
        lines: Its lines after the ``#!/bin/sh`` line.

    Returns:
        The path.
    """
    path.write_bytes(("#!/bin/sh\n" + "".join(line + "\n" for line in lines)).encode("utf-8"))
    path.chmod(0o755)
    return path


def install_sample(root: Path) -> Path:
    """Writes the ``sample`` program into a clone's ignored ``build/`` folder.

    Args:
        root: The clone's working tree.

    Returns:
        The launcher: ``build/sample.bat`` on Windows, ``build/sample`` elsewhere.
    """
    build = Path(root) / "build"
    build.mkdir(exist_ok=True)
    if os.name == "nt":
        (build / "sample_prog.py").write_bytes(SAMPLE_SOURCE.encode("utf-8"))
        return _bat(build / "sample.bat", [f'"{sys.executable}" "%~dp0sample_prog.py" %*'])
    path = build / "sample"
    path.write_bytes(f"#!{sys.executable}\n{SAMPLE_SOURCE}".encode("utf-8"))
    path.chmod(0o755)
    return path


def other_checkout() -> Path:
    """A folder outside every clone holding another copy of the ``wordcount`` package.

    Returns:
        The folder; its ``src/wordcount`` is the package.
    """
    folder = new_dir("other-checkout")
    package = folder / "src" / "wordcount"
    package.mkdir(parents=True)
    (package / "__init__.py").write_bytes(b'"""Another checkout."""\n')
    (package / "cli.py").write_bytes(SAMPLE_SOURCE.encode("utf-8"))
    return folder


def _venv_python(prefix: Path) -> Optional[Path]:
    """Puts a real ``python.exe`` for this Python into a folder (Windows).

    It is the redirector of a venv made with ``--without-pip``, with its
    ``pyvenv.cfg`` beside it, so any ``-c`` code reaches Python unchanged,
    which a batch file's ``%*`` does not promise (a line break ends it).

    Args:
        prefix: The folder that gets ``python.exe``.

    Returns:
        The ``python.exe``, or None when no working venv could be made.
    """
    seed = new_dir("venv") / "v"
    made = subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(seed)],
                          capture_output=True, stdin=subprocess.DEVNULL, check=False)
    launcher = seed / "Scripts" / "python.exe"
    if made.returncode != 0 or not launcher.is_file():
        return None
    shutil.copy2(launcher, prefix / "python.exe")
    shutil.copy2(seed / "pyvenv.cfg", prefix / "pyvenv.cfg")
    probe = subprocess.run([str(prefix / "python.exe"), "-c", "import sys\nprint(len(sys.argv))"],
                           capture_output=True, stdin=subprocess.DEVNULL, check=False)
    if probe.returncode != 0 or probe.stdout.strip() != b"1":
        (prefix / "python.exe").unlink()
        return None
    return prefix / "python.exe"


class FakeEnv:
    """A fake environment folder for ``TROY_MODE_ENV_PREFIX`` (interface note, section 6).

    It holds a launcher for each console script, the environment's ``python``,
    and ``envtool``, which prints where it was found. Every launcher runs
    this Python. The console script launcher imports ``wordcount.cli``, so it
    works only with the checkout's source root on ``PYTHONPATH``.

    On Windows, the environment's ``python`` is a real ``python.exe`` when a
    venv can be made, else a ``.bat``; the one of an environment that finds
    the package elsewhere is always a ``.bat``, which puts the other
    checkout first on ``PYTHONPATH``.

    Attributes:
        prefix: The environment folder.
        scripts: Where console scripts live: ``Scripts`` on Windows, ``bin`` elsewhere.
        python: The environment's ``python`` launcher.
    """

    def __init__(self, consoles: Sequence[str] = (CONSOLE,),
                 elsewhere: Optional[Path] = None) -> None:
        """Writes the launchers.

        Args:
            consoles: The console scripts the environment has.
            elsewhere: A folder whose ``src`` the environment's ``python`` puts
                first on ``PYTHONPATH``, as an editable install of another
                checkout would find its package; None for none.
        """
        self.prefix = new_dir("env")
        windows = os.name == "nt"
        self.scripts = self.prefix / ("Scripts" if windows else "bin")
        self.scripts.mkdir()
        exe = sys.executable
        code = "import sys; from wordcount.cli import main; sys.exit(main())"
        for name in consoles:
            if windows:
                _bat(self.scripts / f"{name}.bat", [f'"{exe}" -c "{code}" %*'])
            else:
                _sh(self.scripts / name, [f"exec \"{exe}\" -c '{code}' \"$@\""])
        if windows:
            first = ([f'set "PYTHONPATH={Path(elsewhere) / "src"};%PYTHONPATH%"']
                     if elsewhere else [])
            real = None if elsewhere else _venv_python(self.prefix)
            self.python = real or _bat(self.prefix / "python.bat", [*first, f'"{exe}" %*'])
            _bat(self.scripts / "envtool.bat", ["echo envtool from the environment"])
        else:
            first = ([f'PYTHONPATH="{Path(elsewhere) / "src"}${{PYTHONPATH:+:$PYTHONPATH}}"',
                      "export PYTHONPATH"] if elsewhere else [])
            self.python = _sh(self.scripts / "python", [*first, f'exec "{exe}" "$@"'])
            _sh(self.scripts / "envtool", ['echo "envtool from the environment"'])

    def env_extra(self) -> dict:
        """The variable that points the engine at this environment."""
        return {"TROY_MODE_ENV_PREFIX": str(self.prefix)}


_DEFAULT_ENV: list = []


def default_env() -> FakeEnv:
    """The shared fake environment with the ``wordcount`` console script; never change it."""
    if not _DEFAULT_ENV:
        _DEFAULT_ENV.append(FakeEnv())
    return _DEFAULT_ENV[0]


def add_decoy(fakes: Fakes) -> None:
    """Puts an ``envtool`` into the fakes' folder, which is first on the engine's PATH.

    Args:
        fakes: The fakes whose folder gets the decoy.
    """
    if os.name == "nt":
        _bat(fakes.folder / "envtool.bat", ["echo envtool from elsewhere on the PATH"])
    else:
        _sh(fakes.folder / "envtool", ['echo "envtool from elsewhere on the PATH"'])


# ------------------------------------------------------------- documents

def block(*lines: str, fence: str = "```", info: str = "powershell") -> str:
    """A fenced block of a prototype.

    Args:
        *lines: The block's lines.
        fence: The fence, such as three backticks or tildes.
        info: The info string after the opening fence.

    Returns:
        The block, with a newline after the closing fence.
    """
    return f"{fence}{info}\n" + "".join(line + "\n" for line in lines) + f"{fence}\n"


def run_file(*parts: str, programs: bool = True) -> str:
    """A run file: ``[programs]`` with ``sample``, then the given TOML parts.

    Args:
        *parts: TOML text, each starting with a table header.
        programs: Whether to name ``sample`` in ``[programs]``.

    Returns:
        The TOML text.
    """
    return (PROGRAMS if programs else "") + "".join("\n" + part.strip("\n") + "\n"
                                                    for part in parts)


def run_file_path(prototype: str) -> str:
    """The run file of a prototype: ``.md`` replaced by ``.run.toml`` (note section 3)."""
    return prototype[:-3] + ".run.toml"


def requirements_with(features: Sequence = THREE, rows: Optional[Sequence] = (),
                      version: str = "1.0") -> str:
    """The requirements with a features table and, unless ``rows`` is None, a prototypes table.

    Args:
        features: The features table's rows.
        rows: The prototypes table's rows ``(Prototype, Feature, File)``, or
            None for requirements without the table.
        version: The front matter's version.

    Returns:
        The document text.
    """
    text = requirements_text(features, version=version)
    if rows is None:
        return text
    table = ("| Prototype | Feature | File |\n| --- | --- | --- |\n"
             + "".join(f"| {name} | {feature} | {path} |\n" for name, feature, path in rows))
    section = ("## 3. How users interact with it\n\nEach command has a prototype.\n\n"
               "### 3.1 Prototypes\n\n" + table + "\n")
    return text.replace("## 4. Features\n", section + "## 4. Features\n", 1)


def pyproject_text(consoles: Sequence[str] = (CONSOLE,)) -> str:
    """``pyproject.toml`` with each console script pointing at ``wordcount.cli:main``.

    Args:
        consoles: The console script names.

    Returns:
        The TOML text.
    """
    scripts = "".join(f'{name} = "{CONSOLE_TARGET}"\n' for name in consoles)
    return f'[project]\nname = "wordcount"\nversion = "0.1.0"\n\n[project.scripts]\n{scripts}'


def project_files(features: Sequence = THREE, rows: Optional[Sequence] = (),
                  files: Optional[Mapping] = None, ignore: str = "",
                  consoles: Sequence[str] = (CONSOLE,)) -> dict:
    """The first commit of a project with prototypes, run files, and the sample program.

    Args:
        features: The features table's rows.
        rows: The prototypes table's rows, or None for no table.
        files: More files (prototypes, run files, data), which replace defaults.
        ignore: More ``.gitignore`` lines.
        consoles: The console scripts of ``pyproject.toml``.

    Returns:
        Paths mapped to content.
    """
    extra = {
        REQUIREMENTS: requirements_with(features, rows),
        "pyproject.toml": pyproject_text(consoles),
        ".gitignore": GITIGNORE + "build/\n" + ignore,
        "src/wordcount/cli.py": SAMPLE_SOURCE,
    }
    extra.update(files or {})
    return base_files(features, extra=extra)


def history(files: Mapping, accepted: Sequence = (F01,), current: Sequence = (F02,)) -> list:
    """The steps of ``origin/main``: the first commit, accepted features, then features at stage 6.

    Args:
        files: The first commit's files.
        accepted: Features whose six stages merged.
        current: Features whose stages 1 to 5 merged, so PR 6 is next.

    Returns:
        The steps.
    """
    steps = [base_step(dict(files))]
    for feature in accepted:
        steps += stages(feature, 6)
    for feature in current:
        steps += stages(feature, 5)
    return steps


# ---------------------------------------------------------------- running

_DEFAULT = object()


class RealProject(Project):
    """A clone with the ``sample`` program installed in its ignored ``build/`` folder."""

    def __init__(self, steps: Sequence, branch: Optional[str] = WORK_BRANCH,
                 sample: bool = True) -> None:
        """Clones the origin built from the steps and installs ``sample``.

        Args:
            steps: The history of ``origin/main``.
            branch: The branch to make from ``origin/main``, or None for main.
            sample: Whether to install the sample program.
        """
        super().__init__(steps, branch)
        if sample:
            install_sample(self.root)

    def real_run(self, *args: str, env=_DEFAULT, fakes: Optional[Fakes] = None,
                 env_extra: Optional[Mapping[str, str]] = None,
                 log: Optional[Path] = None) -> Outcome:
        """Runs ``real-run <args> --repo <clone> --json``.

        Args:
            *args: The options, such as ``--item F02``.
            env: The fake environment, or None for no ``TROY_MODE_ENV_PREFIX``;
                by default the shared one.
            fakes: The fakes on the PATH, or None for a gh that fails on every call.
            env_extra: More environment variables.
            log: A file for the sample program's call log, or None.

        Returns:
            The outcome.
        """
        env = default_env() if env is _DEFAULT else env
        extra = dict(env.env_extra()) if env is not None else {}
        if log is not None:
            extra["SAMPLE_LOG"] = str(log)
        extra.update(env_extra or {})
        return self.run("real-run", *args, fakes=fakes, env_extra=extra)

    def report_folder(self) -> Path:
        """``<git dir>/troy-mode/flow``, where the engine writes its reports."""
        return self.git_dir() / "troy-mode" / "flow"

    def all_status(self) -> list:
        """``git status`` with untracked and ignored files, as sorted lines."""
        out = self.git("status", "--porcelain=v1", "--untracked-files=all", "--ignored")
        return sorted(line for line in out.splitlines() if line)


def calls(log: Path) -> list:
    """The sample program's recorded calls, oldest first: dicts with argv and cwd."""
    if not Path(log).exists():
        return []
    return [json.loads(line) for line in Path(log).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def new_log(prefix: str = "log") -> Path:
    """A path for a sample call log in a new folder; the file does not exist yet."""
    return new_dir(prefix) / "calls.jsonl"


# ---------------------------------------------------------------- reading

def prototype_of(report: dict, path: str) -> dict:
    """The report's entry of one prototype.

    Raises:
        AssertionError: There is not exactly one.
    """
    found = [p for p in report.get("prototypes") or [] if p.get("file") == path]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} entries for {path} in "
                             f"{[p.get('file') for p in report.get('prototypes') or []]}")
    return found[0]


def section_of(report: dict, path: str, heading: str) -> dict:
    """The report's entry of one section of a prototype.

    Raises:
        AssertionError: There is not exactly one.
    """
    sections = prototype_of(report, path).get("sections") or []
    found = [s for s in sections if s.get("heading") == heading]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} sections {heading!r} in {path}: "
                             f"{[s.get('heading') for s in sections]}")
    return found[0]


def commands_of(report: dict, path: str, heading: Optional[str] = None) -> list:
    """The command entries of a prototype, or of one of its sections, in order."""
    if heading is not None:
        return list(section_of(report, path, heading).get("commands") or [])
    return [c for s in prototype_of(report, path).get("sections") or []
            for c in s.get("commands") or []]


def command_of(report: dict, path: str, typed: str, heading: Optional[str] = None,
               kind: Optional[str] = None) -> dict:
    """The one command entry of a prototype with this typed line.

    Args:
        report: The report.
        path: The prototype.
        typed: The ``typed`` value.
        heading: The section, or None for any.
        kind: The ``kind``, or None for any.

    Raises:
        AssertionError: There is not exactly one.
    """
    found = [c for c in commands_of(report, path, heading) if c.get("typed") == typed
             and (kind is None or c.get("kind") == kind)]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} commands {typed!r} in {path} {heading!r}: "
                             f"{[c.get('typed') for c in commands_of(report, path, heading)]}")
    return found[0]


def every_command(report: dict) -> list:
    """Every command entry of the report: ``(prototype, heading, entry)`` tuples."""
    return [(p.get("file"), s.get("heading"), c) for p in report.get("prototypes") or []
            for s in p.get("sections") or [] for c in s.get("commands") or []]


def problems_of(report: dict, kind: Optional[str] = None,
                prototype: Optional[str] = None) -> list:
    """The report's problems, by kind and prototype when given."""
    return [p for p in report.get("problems") or [] if isinstance(p, dict)
            and (kind is None or p.get("kind") == kind)
            and (prototype is None or p.get("prototype") == prototype)]


def problem_kinds(report: dict) -> list:
    """The sorted kinds of the report's problems."""
    return sorted(str(p.get("kind")) if isinstance(p, dict) else repr(p)
                  for p in report.get("problems") or [])


def diff_lines(entry: dict) -> list:
    """A command entry's diff as lines, without line ends."""
    return (entry.get("diff") or "").splitlines()


def markdown_part(text: str, title: str) -> str:
    """The text under a ``### <title>`` heading, up to the next ``##`` or ``###`` heading."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == f"### {title}"), None)
    if start is None:
        return ""
    found = []
    for line in lines[start + 1:]:
        if re.match(r"^#{2,3} ", line):
            break
        found.append(line)
    return "\n".join(found)


def path_spellings(path) -> list:
    """The spellings of a local path a text must not hold: as given, real, ``/`` forms.

    On Windows they are lower case, for a check against lower-cased text.
    """
    found = set()
    for value in (str(path), os.path.realpath(str(path))):
        for spelling in (value, value.replace("\\", "/")):
            found.add(spelling.lower() if os.name == "nt" else spelling)
    return sorted(found)


def remove_tree(path) -> None:
    """Deletes a folder the engine kept, ignoring errors."""
    if path:
        shutil.rmtree(str(path), ignore_errors=True)


class RealRunCase(FlowCase):
    """Assertions shared by the F12 tests."""

    def real_report(self, out: Outcome, code: int) -> dict:
        """Asserts the exit code and the common keys of a real-run report, and returns it."""
        return self.report_of(out, code, "real-run")

    def assert_command(self, entry: dict, result: str, **expected) -> None:
        """Asserts a command's result and the other named fields.

        Args:
            entry: The command entry.
            result: The expected ``result``.
            **expected: More field names mapped to their values.
        """
        self.assertEqual(entry.get("result"), result, json.dumps(entry, ensure_ascii=False))
        for key, value in expected.items():
            self.assertEqual(entry.get(key), value,
                             f"{key} of {json.dumps(entry, ensure_ascii=False)}")

    def assert_not_run(self, entry: dict) -> None:
        """Asserts a command did not run: result ``not run``, no real output, no exit code."""
        self.assert_command(entry, "not run", real=None, exit=None)

    def assert_no_local_path(self, text: str, *paths) -> None:
        """Asserts a text holds no spelling of any of the paths."""
        haystack = text.lower() if os.name == "nt" else text
        for path in paths:
            for spelling in path_spellings(path):
                with self.subTest(path=spelling):
                    self.assertNotIn(spelling, haystack)
