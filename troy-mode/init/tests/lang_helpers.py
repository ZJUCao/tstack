"""Language-step fixtures for the troy-init unit tests (F06 design 5, 11.1).

A language-step project is cloned from an origin whose main holds an
approved ``docs/architecture.md`` (version "1.0"), set up, and given the
setup commit, as the PR flow leaves it. The expected files are computed from
the fake plugin's own pack files. ``FakeMamba`` stands in for mamba: it
records every call and writes the lock file, so no test reaches the network
or creates a real environment.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence
from unittest import mock

from init_helpers import (
    CONFIG, PLUGIN_ROOT, PROJECT, RECORD, WORKFLOW, Outcome, Project, lf, new_dir, owned_files,
    pr_body, read_text, setup_project, write_text,
)

LANG_DATE = "2026-11-12"
ARCHITECTURE = "docs/architecture.md"
TITLES = {"python": "[rules] Add the Python pack", "cpp": "[rules] Add the C/C++ pack"}
BODIES = {
    "python": pr_body("The architecture is approved, so the project gets its language pack.",
                      "The Python pack: environment.yml, the pyproject.toml tables, the [lang] "
                      "table, and the code checks job."),
    "cpp": pr_body("The architecture is approved, so the project gets its language pack.",
                   "The C/C++ pack: the build settings, the tool settings, the [lang] table, "
                   "and the code checks job."),
}
LOCKS = {"python": "requirements-dev.lock", "cpp": "requirements-tools.lock"}
MANIFESTS = {"python": "pyproject.toml", "cpp": "requirements-tools.in"}
BUILD_FILES = {"python": "pyproject.toml", "cpp": "CMakeLists.txt"}
GITIGNORE_LINES = {
    "python": ["reports/", ".coverage", "__pycache__/", ".mypy_cache/", ".pytest_cache/",
               ".ruff_cache/"],
    "cpp": ["build/", "reports/"],
}
# The C/C++ pack's whole files: project path to path in troy-mode/lang/cpp/.
CPP_COPIED = {
    "CMakePresets.json": "CMakePresets.json",
    "cmake/troy.cmake": "cmake/troy.cmake",
    ".clang-format": ".clang-format",
    ".clang-tidy": ".clang-tidy",
    "include/troy/not_implemented.h": "include/troy/not_implemented.h",
    ".troy-mode/lang/cpp/Doxyfile": "Doxyfile",
}
INCLUDE_LINE = "include(cmake/troy.cmake)"
LANG_REPORT_KEYS = ("language", "legacy", "environment")
ENVIRONMENT_KEYS = ("name", "prefix", "series", "lock", "skipped", "exists", "commands")
FAKE_LOCK = "# A lock written by the tests' fake mamba.\nruff==0.8.0\n"
OWN_TEXT = "# Our own file\n\nWritten before the language step.\n"
# F03 design D214: what the Python pack's ruff leaves out. docs/ with its slash
# is relative to the project root; a bare docs would also leave out src/<pkg>/docs.
RUFF_EXCLUDES = [".troy-mode", "docs/"]


def architecture(version: str = "1.0") -> dict:
    """A docs/architecture.md with the given version, as base files for origin/main."""
    text = ('---\ntroy-doc: "architecture"\nlang: "en"\n'
            f'version: "{version}"\nupdated: "2026-11-06"\n'
            'status: "Approved by Troy on 2026-11-06."\n---\n\n'
            f"# {PROJECT} architecture\n\nOne module.\n")
    return {ARCHITECTURE: text}


APPROVED = architecture("1.0")


def lang_values(lang: str, environment: str = PROJECT, series: Sequence[str] = (".",)) -> dict:
    """The [lang] table the language step writes into the config (interface note)."""
    if lang == "python":
        return {"name": "python", "source_roots": ["src"], "environment": environment,
                "series": list(series)}
    return {"name": "cpp", "include_dirs": ["include", "src"], "environment": environment,
            "series": list(series)}


def pack_dir(plugin: Path, lang: str) -> Path:
    """A pack's folder in a plugin."""
    return plugin / "troy-mode/lang" / lang


def pack_text(plugin: Path, lang: str, rel: str) -> str:
    """A pack file's text with CRLF made LF."""
    return read_text(pack_dir(plugin, lang), rel)


def fill(text: str, values: Mapping[str, str]) -> str:
    """Replaces each {{key}} marker with its value."""
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def join_parts(first: str, second: str) -> str:
    """Joins two files' texts as the language step does."""
    return first.rstrip("\n") + "\n\n" + second


def expected_environment(plugin: Path, lang: str, environment: str = PROJECT) -> str:
    """The pack's environment.yml with the environment's name."""
    return fill(pack_text(plugin, lang, "environment.yml"), {"environment": environment})


def expected_workflow(plugin: Path, lang: str) -> str:
    """F02's workflow followed by the pack's job."""
    return join_parts(read_text(plugin, "troy-mode/checks/workflow.yml"),
                      pack_text(plugin, lang, "workflow-job.yml"))


def expected_new_pyproject(plugin: Path, name: str = PROJECT,
                           package: str = "habit_tracker") -> str:
    """The pyproject.toml the Python step creates when the project has none."""
    first = fill(pack_text(plugin, "python", "pyproject-project.toml"),
                 {"project-name": name, "package": package})
    return join_parts(first, pack_text(plugin, "python", "pyproject.toml"))


def ruff_excludes(pyproject: str) -> tuple:
    """A pyproject.toml's [tool.ruff] extend-exclude, sorted, and whether it sets exclude."""
    ruff = tomllib.loads(pyproject).get("tool", {}).get("ruff", {})
    return sorted(ruff.get("extend-exclude", [])), "exclude" in ruff


def expected_new_cmakelists(plugin: Path, name: str = PROJECT) -> str:
    """The CMakeLists.txt the C/C++ step creates when the project has none."""
    return fill(pack_text(plugin, "cpp", "CMakeLists-project.txt"), {"project-name": name})


def lang_owned(plugin: Path, lang: str) -> dict:
    """Every file troy-init owns after the language step: path to LF content."""
    files = owned_files(plugin)
    files[WORKFLOW] = expected_workflow(plugin, lang).encode("utf-8")
    if lang == "cpp":
        for path, source in CPP_COPIED.items():
            files[path] = lf((pack_dir(plugin, "cpp") / source).read_bytes())
    return files


def lang_actions(lang: str, build: str = "create", gitignore: str = "append",
                 lock: bool = False) -> dict:
    """The language step's actions by path, for a project set up with nothing else."""
    actions = {CONFIG: "edit", "environment.yml": "create", WORKFLOW: "edit",
               ".gitignore": gitignore, RECORD: "edit", BUILD_FILES[lang]: build}
    if lang == "cpp":
        actions["requirements-tools.in"] = "create"
        actions.update({path: "create" for path in CPP_COPIED})
    if lock:
        actions[LOCKS[lang]] = "create"
    return actions


def lang_stage(lang: str, **action_args) -> list:
    """The sorted paths the language step stages: every action but keep."""
    return sorted(path for path, action in lang_actions(lang, **action_args).items()
                  if action != "keep")


def lang_project(plugin: Path, base_files: Optional[Mapping[str, str]] = None,
                 approved: bool = True, **project_args) -> Project:
    """A project set up with the plugin and its setup commit made, ready for the language step."""
    files = {**(APPROVED if approved else {}), **(base_files or {})}
    return setup_project(plugin, base_files=files, **project_args)


def run_lang(project: Project, plugin: Path, lang: str, *extra: str, no_env: bool = True,
             date: Optional[str] = LANG_DATE, repo_option: bool = True,
             env_extra: Optional[Mapping[str, str]] = None) -> Outcome:
    """Runs `lang <lang> --json`, with --no-env and the date unless told otherwise."""
    args = ["lang", lang, *(["--no-env"] if no_env else []), *(["--date", date] if date else [])]
    return project.run(plugin, *args, *extra, "--json", repo_option=repo_option,
                       env_extra=env_extra)


def lang_done(plugin: Path, lang: str, *extra: str,
              base_files: Optional[Mapping[str, str]] = None) -> tuple:
    """A project with the setup commit and the language step's commit on top.

    Returns:
        The project, the setup commit's SHA, and the language step's report.
    """
    project = lang_project(plugin, base_files=base_files)
    base = project.git("rev-parse", "HEAD").strip()
    out = run_lang(project, plugin, lang, *extra)
    if out.code != 0 or not isinstance(out.report, dict):
        raise AssertionError(f"lang {lang} did not succeed:\n{out.describe()}")
    project.commit_report(out.report, TITLES[lang])
    return project, base, out.report


def reset_project(project: Project, to: str = "HEAD") -> None:
    """Puts the branch and working tree back to a commit, keeping ignored files.

    Untracked files are removed, ignored ones such as the progress file stay,
    so a project can be reused after a run that changed files.
    """
    project.git("reset", "-q", "--hard", to)
    project.git("clean", "-q", "-fd")


_SHARED: dict = {}


def shared_lang_project(plugin: Path) -> Project:
    """A set-up project shared by tests, put back to its setup commit on every call.

    Tests that use it may change its files and commit on its branch, but not
    its other refs or its git config, unless they put them back.
    """
    if plugin not in _SHARED:
        project = lang_project(plugin)
        _SHARED[plugin] = (project, project.git("rev-parse", "HEAD").strip())
    project, setup_sha = _SHARED[plugin]
    reset_project(project, setup_sha)
    return project


def split_lang_table(text: str) -> tuple:
    """Splits a config into the lines before [lang], the [lang] table's lines, and the rest.

    The legacy line (and its continuation lines, if the list spans several)
    is dropped from the first part, since the language step may change it.
    """
    lines = text.split("\n")
    start = lines.index("[lang]")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")),
               len(lines))
    before, skipping = [], False
    for line in lines[:start]:
        if line.startswith("legacy"):
            skipping = "]" not in line
            continue
        if skipping:
            skipping = "]" not in line
            continue
        before.append(line)
    return before, lines[start + 1:end], lines[end:]


def parse_config_with_troy_check(text: str):
    """Parses a config with troy-check's own parser, imported from troy-mode/checks."""
    checks = str(PLUGIN_ROOT / "troy-mode/checks")
    sys.path.insert(0, checks)
    try:
        from troycheck.config import parse_config  # pylint: disable=import-outside-toplevel
    finally:
        sys.path.remove(checks)
    return parse_config(text)


def crlf_lang(plugin: Path) -> None:
    """Turns every pack file of a fake plugin into CRLF line endings."""
    for path in (plugin / "troy-mode/lang").rglob("*"):
        if path.is_file():
            path.write_bytes(lf(path.read_bytes()).replace(b"\n", b"\r\n"))


def same_path(first, second) -> bool:
    """Whether two paths name the same place, existing or not."""
    def norm(path) -> str:
        return os.path.normcase(os.path.realpath(os.path.abspath(str(path))))
    return norm(first) == norm(second)


def masked(argv: Sequence[str], prefix) -> list:
    """An argv with the path after -p replaced by "<prefix>" once it names the prefix."""
    out = list(argv)
    for index, arg in enumerate(out[:-1]):
        if arg == "-p" and same_path(out[index + 1], prefix):
            out[index + 1] = "<prefix>"
    return out


def git_only_path() -> str:
    """The folder that holds git, to use as a PATH on which mamba cannot be found."""
    found = shutil.which("git")
    if not found:
        raise AssertionError("git is not on the PATH")
    return os.path.dirname(found)


# uv's cache folder in the system temp folder when UV_CACHE_DIR is unset (D213).
UV_CACHE_NAME = "troy-mode-uv-cache"


def temp_env(folder: Path) -> dict:
    """Variables that make tempfile.gettempdir() return the folder in a child process.

    gettempdir() takes the first of TMPDIR, TEMP, and TMP that names a
    writable folder, on every OS, so all three point at it.
    """
    return {"TMPDIR": str(folder), "TEMP": str(folder), "TMP": str(folder)}


@contextlib.contextmanager
def without_env(*names: str):
    """Removes variables from this process's environment for the block, then puts them back.

    The helpers' base_env copies os.environ, so a variable the machine sets
    reaches the engine unless it is removed here.
    """
    with mock.patch.dict(os.environ):
        for name in names:
            os.environ.pop(name, None)
        yield


# ------------------------------------------------------------------ fake mamba

_FAKE_SOURCE = r'''
"""A stand-in for mamba for troy-init's tests. It records each call and never
touches the network."""
import json
import os
import sys
from pathlib import Path

LOG = Path(@LOG@)
SETTINGS = Path(@SETTINGS@)
LOCK_TEXT = @LOCK@
WATCHED = ("environment.yml", "pyproject.toml", "requirements-tools.in")


def kind_of(args):
    """Names the kind of call: list, create, compile, install, or other."""
    if args[:2] == ["env", "list"]:
        return "list"
    if args[:2] == ["env", "create"]:
        return "create"
    if args[:1] == ["run"] and "uv" in args:
        rest = args[args.index("uv") + 1:]
        if rest[:2] == ["pip", "compile"]:
            return "compile"
        if rest[:2] == ["pip", "install"]:
            return "install"
    return "other"


def main():
    """Records the call, then acts as the settings say."""
    args = sys.argv[1:]
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entry = {"argv": args, "cwd": os.getcwd(), "uv_link_mode": os.environ.get("UV_LINK_MODE"),
             "uv_cache_dir": os.environ.get("UV_CACHE_DIR"),
             "marker": os.environ.get("FAKE_MAMBA_MARKER"),
             "present": [name for name in WATCHED if Path(name).is_file()]}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    kind = kind_of(args)
    if kind == settings.get("fail"):
        sys.stderr.write("fake mamba: this call fails on purpose\n")
        return 3
    if kind == "list":
        sys.stdout.write(json.dumps({"envs": settings.get("envs", [])}) + "\n")
    elif kind == "compile" and not settings.get("no_lock"):
        Path(args[args.index("-o") + 1]).write_bytes(LOCK_TEXT.encode("utf-8"))
    return 0


sys.exit(main())
'''


class FakeMamba:
    """A fake mamba launcher in its own folder, with a call log and settings.

    On POSIX the launcher is an executable script named mamba; on Windows it
    is mamba.bat, which runs the script with this Python.
    """

    def __init__(self, envs: Iterable[str] = (), fail: Optional[str] = None,
                 no_lock: bool = False) -> None:
        """Writes the launcher and its settings into a new folder."""
        self.folder = new_dir("mamba")
        self.log = self.folder / "calls.jsonl"
        self.settings = self.folder / "settings.json"
        self.configure(envs=envs, fail=fail, no_lock=no_lock)
        source = (_FAKE_SOURCE.replace("@LOG@", repr(str(self.log)))
                  .replace("@SETTINGS@", repr(str(self.settings)))
                  .replace("@LOCK@", repr(FAKE_LOCK)))
        if os.name == "nt":
            script = self.folder / "fake_mamba.py"
            script.write_text(source, encoding="utf-8")
            self.path = self.folder / "mamba.bat"
            self.path.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n'
                                 "exit /b %ERRORLEVEL%\r\n", encoding="utf-8")
        else:
            self.path = self.folder / "mamba"
            self.path.write_text(f"#!{sys.executable}\n{source}", encoding="utf-8")
            self.path.chmod(0o755)

    def configure(self, envs: Iterable[str] = (), fail: Optional[str] = None,
                  no_lock: bool = False) -> None:
        """Sets what env list prints, which kind of call fails, and whether compile writes."""
        settings = {"envs": [str(env) for env in envs], "fail": fail, "no_lock": no_lock}
        write_text(self.folder, "settings.json", json.dumps(settings))

    def clear(self) -> None:
        """Forgets the calls recorded so far."""
        if self.log.exists():
            self.log.unlink()

    def calls(self) -> list:
        """Every recorded call, in order.

        Each is a dict with argv, cwd, uv_link_mode, uv_cache_dir (the
        variable UV_CACHE_DIR, None when absent), marker (the variable
        FAKE_MAMBA_MARKER), and present (which of environment.yml,
        pyproject.toml, and requirements-tools.in existed in cwd).
        """
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def argvs(self) -> list:
        """The arguments of every recorded call, without the program name."""
        return [call["argv"] for call in self.calls()]

    def kinds(self) -> list:
        """The kind of each recorded call: list, create, compile, install, or other."""
        kinds = []
        for argv in self.argvs():
            if argv[:2] == ["env", "list"]:
                kinds.append("list")
            elif argv[:2] == ["env", "create"]:
                kinds.append("create")
            elif argv[:1] == ["run"] and "compile" in argv:
                kinds.append("compile")
            elif argv[:1] == ["run"] and "install" in argv:
                kinds.append("install")
            else:
                kinds.append("other")
        return kinds

    def path_env(self, rest: Optional[str] = None) -> dict:
        """An environment whose PATH starts with this fake's folder.

        Args:
            rest: The PATH after the fake's folder, or None for this process's PATH.
        """
        tail = os.environ.get("PATH", "") if rest is None else rest
        return {"PATH": str(self.folder) + (os.pathsep + tail if tail else "")}


def env_list(*names: str) -> list:
    """What env list --json names: a root prefix and one folder per environment name."""
    root = new_dir("conda")
    return [str(root), *(str(root / "envs" / name) for name in names)]


def compile_args(lang: str, target: Sequence[str], manifests: Sequence[str]) -> list:
    """The compile call's arguments (without the program) of interface step 3."""
    if lang == "python":
        tail = ["--extra", "dev", "--universal", "-o", LOCKS[lang]]
    else:
        tail = ["--universal", "--python-version", "3.13", "-o", LOCKS[lang]]
    return ["run", *target, "uv", "pip", "compile", *manifests, *tail]


def install_args(lang: str, target: Sequence[str]) -> list:
    """The install call's arguments (without the program) of interface step 4."""
    return ["run", *target, "uv", "pip", "install", "-r", LOCKS[lang]]


def create_args(target: Sequence[str]) -> list:
    """The create call's arguments (without the program) of interface step 2."""
    return ["env", "create", "-y", "-f", "environment.yml", *target]


LIST_ARGS = ["env", "list", "--json"]
