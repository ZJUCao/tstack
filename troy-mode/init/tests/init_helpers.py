"""Shared fixtures for the troy-init unit tests (F06 design section 11.1).

The tests build throwaway git repositories, each cloned from a local bare
``origin``, run ``troy_init.py`` from a copy of the plugin (the fake plugin),
and compare what it wrote with the plugin's own files. Nothing here imports
the engine: only its command line and its JSON report are used.
"""

from __future__ import annotations

import atexit
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
ENGINE_REL = "troy-mode/init/troy_init.py"
EMAIL = "148482542+ZJUCao@users.noreply.github.com"
OTHER_EMAIL = "someone@example.com"
DATE = "2026-11-07"
UPGRADE_DATE = "2026-11-20"
PROJECT = "habit-tracker"
BRANCH = "troy-mode/init"
SETUP_TITLE = "[rules] Set up troy-mode"

CONFIG = ".troy-mode/config.toml"
RECORD = ".troy-mode/install.toml"
PROGRESS = ".troy-mode/progress.md"
WORKFLOW = ".github/workflows/troy-mode.yml"
PR_TEMPLATE = ".github/pull_request_template.md"
RULES = ("docs/rules.md", "docs/rules.zh-CN.md")
HOOKS_DIR = ".troy-mode/checks/git-hooks"
HOOK_NAMES = ("commit-msg", "pre-commit", "pre-merge-commit", "pre-push")
HOOK_TEXT = b"#!/bin/sh\nexit 0\n"
NOT_IMPLEMENTED_H = "include/troy/not_implemented.h"
REPORT_KEYS = ("command", "ok", "dry_run", "changed", "version", "actions", "conflicts",
               "problems", "stage", "executable", "hooks_path", "email", "differences",
               "notes", "next_steps")

_CACHE_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_DROPPED_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                "GIT_COMMON_DIR", "GIT_CEILING_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_COUNT",
                "GIT_CONFIG_PARAMETERS", "PYTHONUTF8", "PYTHONIOENCODING", "CLAUDE_PLUGIN_ROOT",
                "GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "MAMBA_EXE")

_SCRATCH = tempfile.TemporaryDirectory(prefix="troyinit-", ignore_cleanup_errors=True)
atexit.register(_SCRATCH.cleanup)
SCRATCH = Path(_SCRATCH.name)
_GLOBAL_CONFIG = SCRATCH / "gitconfig"
_GLOBAL_CONFIG.write_text("", encoding="utf-8")
_COUNTER = itertools.count(1)
_ORIGINS: dict = {}
_PLUGINS: dict = {}


def new_dir(prefix: str) -> Path:
    """Creates a new empty folder in the scratch area."""
    path = SCRATCH / f"{prefix}{next(_COUNTER)}"
    path.mkdir()
    return path


def base_env(extra: Optional[Mapping[str, str]] = None) -> dict:
    """Builds an environment that isolates git from the machine's config."""
    env = {k: v for k, v in os.environ.items() if k not in _DROPPED_ENV}
    env.update({
        "GIT_CONFIG_GLOBAL": str(_GLOBAL_CONFIG), "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": EMAIL,
        "GIT_COMMITTER_NAME": "Test Committer", "GIT_COMMITTER_EMAIL": EMAIL,
        "GIT_TERMINAL_PROMPT": "0", "PYTHONDONTWRITEBYTECODE": "1",
    })
    env.update(extra or {})
    return env


def git_proc(cwd: Path, *args: str, env_extra=None) -> subprocess.CompletedProcess:
    """Runs git and returns the finished process, whatever its exit code."""
    return subprocess.run(["git", *args], cwd=str(cwd), env=base_env(env_extra),
                          capture_output=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL, check=False)


def git(cwd: Path, *args: str, env_extra=None) -> str:
    """Runs git, raises when it fails, and returns its standard output."""
    proc = git_proc(cwd, *args, env_extra=env_extra)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}: {proc.stderr}")
    return proc.stdout


def lf(data: bytes) -> bytes:
    """Replaces CRLF with LF."""
    return data.replace(b"\r\n", b"\n")


def sha256_lf(data: bytes) -> str:
    """The install record's hash: SHA-256 of the bytes with CRLF made LF."""
    return hashlib.sha256(lf(data)).hexdigest()


def write_text(root: Path, rel: str, text: str) -> None:
    """Writes UTF-8 text with LF line endings, creating folders."""
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def read_text(root: Path, rel: str) -> str:
    """Reads a UTF-8 file with CRLF made LF."""
    return lf((Path(root) / rel).read_bytes()).decode("utf-8")


def replace_in(root: Path, rel: str, old: str, new: str) -> None:
    """Replaces the one occurrence of a text in a file, failing if it is not there once."""
    text = read_text(root, rel)
    if text.count(old) != 1:
        raise AssertionError(f"{rel} holds {old!r} {text.count(old)} times, not once")
    write_text(root, rel, text.replace(old, new))


def tree_files(folder: Path) -> dict:
    """Every file under a folder, by relative path with '/', skipping caches."""
    files = {}
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if path.is_file() and not _CACHE_NAMES & set(rel.parts) and path.suffix != ".pyc":
            files[rel.as_posix()] = path.read_bytes()
    return files


# ----------------------------------------------------------------- fake plugin

def _copy_ignore(top: Path):
    """Returns a copytree filter dropping caches, and tests/ at the top only."""
    def ignore(folder: str, names: list) -> list:
        at_top = Path(folder) == top
        return [n for n in names if n in _CACHE_NAMES or n.endswith(".pyc")
                or (at_top and n == "tests")]
    return ignore


def make_plugin(hooks: bool = True, version: Optional[str] = None, crlf: bool = False) -> Path:
    """Copies the parts of the plugin the engine reads into a new folder.

    Args:
        hooks: Whether troy-mode/checks/git-hooks/ holds the fake hooks.
        version: A version to write into plugin.json, or None to keep it.
        crlf: Whether to turn the checks' and templates' line endings into
            CRLF, as a Windows checkout with core.autocrlf would.

    Returns:
        The fake plugin's root. It is not a git checkout.
    """
    root = new_dir("plugin") / "troy-pstack"
    (root / ".claude-plugin").mkdir(parents=True)
    shutil.copyfile(PLUGIN_ROOT / ".claude-plugin/plugin.json", root / ".claude-plugin/plugin.json")
    for rel in ("troy-mode/init", "troy-mode/checks", "troy-mode/templates", "troy-mode/lang"):
        source = PLUGIN_ROOT / rel
        if source.is_dir():
            shutil.copytree(source, root / rel, ignore=_copy_ignore(source))
    hooks_dir = root / "troy-mode/checks/git-hooks"
    shutil.rmtree(hooks_dir, ignore_errors=True)
    if hooks:
        hooks_dir.mkdir(parents=True)
        for name in HOOK_NAMES:
            (hooks_dir / name).write_bytes(HOOK_TEXT)
            (hooks_dir / name).chmod(0o755)
    if version:
        set_version(root, version)
    if crlf:
        for folder in ("troy-mode/checks", "troy-mode/templates"):
            for path in (root / folder).rglob("*"):
                if path.is_file():
                    path.write_bytes(lf(path.read_bytes()).replace(b"\n", b"\r\n"))
    return root


def shared_plugin(hooks: bool = True) -> Path:
    """A fake plugin shared by every test in this process. Never modify it."""
    if hooks not in _PLUGINS:
        _PLUGINS[hooks] = make_plugin(hooks=hooks)
    return _PLUGINS[hooks]


def plugin_version(plugin: Path) -> str:
    """The version in a plugin's plugin.json."""
    return json.loads(read_text(plugin, ".claude-plugin/plugin.json"))["version"]


def set_version(plugin: Path, version: str) -> None:
    """Writes a new version into a plugin's plugin.json."""
    data = json.loads(read_text(plugin, ".claude-plugin/plugin.json"))
    data["version"] = version
    write_text(plugin, ".claude-plugin/plugin.json", json.dumps(data, indent=2) + "\n")


# -------------------------------------------------------- expected file sets

def expected_checks(plugin: Path) -> dict:
    """Setup's copy of troy-check: project path to LF content."""
    skip = {"workflow.yml", "config.default.toml"}
    return {f".troy-mode/checks/{rel}": lf(data)
            for rel, data in tree_files(plugin / "troy-mode/checks").items()
            if rel not in skip and not rel.startswith("tests/")}


def expected_templates(plugin: Path) -> dict:
    """Setup's copy of the templates: project path to LF content."""
    return {f".troy-mode/templates/{rel}": lf(data)
            for rel, data in tree_files(plugin / "troy-mode/templates").items()}


def owned_files(plugin: Path) -> dict:
    """Every file troy-init owns (install record [files]): path to LF content."""
    files = {**expected_checks(plugin), **expected_templates(plugin)}
    files[WORKFLOW] = lf((plugin / "troy-mode/checks/workflow.yml").read_bytes())
    files[PR_TEMPLATE] = lf((plugin / "troy-mode/templates/pull-request.md").read_bytes())
    return files


def hook_paths(plugin: Path) -> list:
    """The project paths of the plugin's git hooks, sorted."""
    folder = plugin / "troy-mode/checks/git-hooks"
    return sorted(f"{HOOKS_DIR}/{rel}" for rel in tree_files(folder)) if folder.is_dir() else []


def setup_stage(plugin: Path, gitignore: bool = True) -> list:
    """The sorted paths setup stages in a project with no troy-mode files."""
    paths = set(owned_files(plugin)) | {CONFIG, RECORD, *RULES}
    if gitignore:
        paths.add(".gitignore")
    return sorted(paths)


def pack_patterns(plugin: Path) -> dict:
    """Every pack's [paths] patterns by list name, plus the D49 header."""
    patterns: dict = {}
    for path in sorted((plugin / "troy-mode/lang").glob("*/config.toml")):
        paths = tomllib.loads(read_text(path.parent, path.name)).get("paths", {})
        for key, values in paths.items():
            patterns.setdefault(key, set()).update(values)
    patterns.setdefault("config", set()).add(NOT_IMPLEMENTED_H)
    return patterns


def pr_body(why: str, what: str) -> str:
    """A PR description with the PR template's sections filled in."""
    return (f"## Why\n\n{why}\n\n## What\n\n{what}\n\n## Checks\n\n"
            "troy-check pr ran on the branch before the push.\n\n## Soft-limit reason\n\nNone\n")


SETUP_BODY = pr_body("Turn this folder into a troy-mode project, so every later PR is checked.",
                     "The config, troy-check and its git hooks, the templates, the rules table, "
                     "the PR template, and the CI workflow.")


# ------------------------------------------------------------------ projects

@dataclass
class Outcome:
    """A finished engine or troy-check run."""

    code: int
    stdout: str
    stderr: str
    report: Optional[dict]

    def describe(self) -> str:
        """The run's output, for assertion messages."""
        return f"exit {self.code}\nstdout:\n{self.stdout[-4000:]}\nstderr:\n{self.stderr[-4000:]}"


def run_python(script: Path, args: Sequence, cwd: Path, env_extra=None) -> Outcome:
    """Runs a Python script and parses a JSON report when --json is passed."""
    args = [str(a) for a in args]
    proc = subprocess.run([sys.executable, str(script), *args], cwd=str(cwd),
                          env=base_env(env_extra), capture_output=True,
                          stdin=subprocess.DEVNULL, timeout=180, check=False)
    stdout = proc.stdout.decode("utf-8", "replace")
    report = None
    if "--json" in args:
        try:
            report = json.loads(stdout)
        except ValueError:
            report = None
    return Outcome(proc.returncode, stdout, proc.stderr.decode("utf-8", "replace"), report)


def origin_repo(base_files: Optional[Mapping[str, str]] = None) -> Path:
    """A cached bare origin whose main holds one commit with the given files."""
    files = {"README.md": f"# {PROJECT}\n", **(base_files or {})}
    key = repr(sorted(files.items()))
    if key not in _ORIGINS:
        seed = new_dir("seed")
        git(seed, "init", "-q", "-b", "main")
        for rel, text in files.items():
            write_text(seed, rel, text)
        git(seed, "add", "--", *files)
        git(seed, "commit", "-q", "-m", "Initial commit")
        bare = SCRATCH / f"origin{next(_COUNTER)}.git"
        git(SCRATCH, "clone", "-q", "--bare", str(seed), str(bare))
        _ORIGINS[key] = bare
    return _ORIGINS[key]


@dataclass
class Snapshot:
    """A project's working tree (without .git) and its local git config."""

    files: dict
    config: str


def changed_paths(before: Snapshot, after: Snapshot) -> list:
    """The paths added, removed, or changed between two snapshots."""
    paths = set(before.files) | set(after.files)
    return sorted(p for p in paths if before.files.get(p) != after.files.get(p))


class Project:
    """A clone of a bare origin, on a branch made from origin/main."""

    def __init__(self, base_files: Optional[Mapping[str, str]] = None,
                 branch: Optional[str] = BRANCH, source: Optional[Path] = None,
                 clone_config: Sequence[str] = ()) -> None:
        """Clones the origin (or another project) into a new folder named PROJECT."""
        self.tmp = new_dir("case")
        self.root = self.tmp / PROJECT
        options = [arg for item in clone_config for arg in ("-c", item)]
        git(self.tmp, "clone", "-q", *options, str(source or origin_repo(base_files)), PROJECT)
        if branch and source is None:
            self.git("switch", "-q", "-c", branch, "origin/main")

    def git(self, *args: str, email: Optional[str] = None) -> str:
        """Runs git in the project, optionally as author and committer email."""
        extra = {"GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_EMAIL": email} if email else None
        return git(self.root, *args, env_extra=extra)

    def read_bytes(self, rel: str) -> bytes:
        """A file's raw bytes."""
        return (self.root / rel).read_bytes()

    def read(self, rel: str) -> str:
        """A file's text with CRLF made LF."""
        return read_text(self.root, rel)

    def write(self, rel: str, text: str) -> None:
        """Writes a file with LF line endings."""
        write_text(self.root, rel, text)

    def config_value(self, key: str) -> Optional[str]:
        """A local git config value, or None when it is unset."""
        proc = git_proc(self.root, "config", "--local", "--get", key)
        return proc.stdout.strip() if proc.returncode == 0 else None

    def files(self, prefix: str = "") -> dict:
        """Every working-tree file outside .git, by path, optionally under a prefix."""
        found = {}
        for folder, dirs, names in os.walk(self.root):
            if Path(folder) == self.root:
                dirs[:] = [d for d in dirs if d != ".git"]
            for name in names:
                rel = (Path(folder) / name).relative_to(self.root).as_posix()
                if rel.startswith(prefix):
                    found[rel] = (Path(folder) / name).read_bytes()
        return found

    def snapshot(self) -> Snapshot:
        """The whole working tree and `git config --list --local`."""
        return Snapshot(self.files(), self.git("config", "--list", "--local"))

    def run(self, plugin: Path, *args: str, repo_option: bool = True, env_extra=None) -> Outcome:
        """Runs the plugin's engine on this project, with --repo or from inside it."""
        if repo_option:
            args = (*args, "--repo", self.root)
            return run_python(plugin / ENGINE_REL, args, self.tmp, env_extra)
        return run_python(plugin / ENGINE_REL, args, self.root, env_extra)

    def setup(self, plugin: Path, *extra: str, email: Optional[str] = EMAIL,
              date: Optional[str] = DATE, repo_option: bool = True) -> Outcome:
        """Runs `setup --json` with the email and date unless they are None."""
        args = ["setup", *(["--email", email] if email else [])]
        args += ["--date", date] if date else []
        return self.run(plugin, *args, *extra, "--json", repo_option=repo_option)

    def upgrade(self, plugin: Path, *extra: str, date: str = UPGRADE_DATE) -> Outcome:
        """Runs `upgrade --json` with the date."""
        return self.run(plugin, "upgrade", "--date", date, *extra, "--json")

    def commit_report(self, report: dict, subject: str, email: str = EMAIL) -> str:
        """Stages exactly the report's paths (hooks with +x), commits, and returns the SHA."""
        executable = list(report["executable"])
        plain = [p for p in report["stage"] if p not in executable]
        if plain:
            self.git("add", "--", *plain)
        if executable:
            self.git("add", "--chmod=+x", "--", *executable)
        self.git("commit", "-q", "-m", subject, email=email)
        return self.git("rev-parse", "HEAD").strip()

    def commit_paths(self, paths: Sequence[str], message: str) -> None:
        """Stages the named paths and commits them (test preparation only)."""
        self.git("add", "--", *paths)
        self.git("commit", "-q", "-m", message)

    def status_paths(self) -> set:
        """Every path `git status` lists as changed or untracked."""
        out = self.git("status", "--porcelain=v1", "-z", "-uall", "--no-renames")
        return {entry[3:] for entry in out.split("\0") if entry}

    def index_modes(self) -> dict:
        """The mode git records for each staged path."""
        out = self.git("ls-files", "-s", "-z")
        return {entry.split("\t", 1)[1]: entry.split(" ", 1)[0]
                for entry in out.split("\0") if entry}

    def troy_check(self, base: str, title: str, body: str) -> Outcome:
        """Runs the project's own troy_check.py pr with --json."""
        body_file = self.tmp / f"body{next(_COUNTER)}.md"
        body_file.write_bytes(body.encode("utf-8"))
        script = self.root / ".troy-mode/checks/troy_check.py"
        args = ["pr", "--base", base, "--title", title, "--body-file", body_file,
                "--repo", self.root, "--json"]
        return run_python(script, args, self.tmp)


def setup_project(plugin: Path, commit: bool = True, **project_args) -> Project:
    """A project set up with the plugin, and the setup commit made unless told not to."""
    project = Project(**project_args)
    out = project.setup(plugin)
    if out.code != 0 or not isinstance(out.report, dict):
        raise AssertionError(f"setup did not succeed:\n{out.describe()}")
    if commit:
        project.commit_report(out.report, SETUP_TITLE)
    return project


def results_by_rule(out: Outcome) -> dict:
    """troy-check's results by rule ID."""
    if not isinstance(out.report, dict):
        raise AssertionError(f"troy-check printed no JSON report:\n{out.describe()}")
    return {item["rule"]: item for item in out.report["results"]}


class InitCase(unittest.TestCase):
    """Assertions shared by the troy-init tests."""

    maxDiff = 20000

    def report_of(self, out: Outcome, code: int = 0) -> dict:
        """Asserts the exit code and a JSON report, and returns the report."""
        self.assertEqual(out.code, code, out.describe())
        self.assertIsInstance(out.report, dict, out.describe())
        self.assertIs(out.report["ok"], code == 0, out.describe())
        return out.report

    def actions_of(self, report: dict) -> dict:
        """The report's actions by path, checking that each path appears once."""
        paths = [item["path"] for item in report["actions"]]
        self.assertEqual(len(paths), len(set(paths)), "a path is listed twice in actions")
        return {item["path"]: item["action"] for item in report["actions"]}

    def assert_unchanged(self, before: Snapshot, after: Snapshot) -> None:
        """Asserts that no file and no local git config changed."""
        self.assertEqual(changed_paths(before, after), [], "the working tree changed")
        self.assertEqual(before.config, after.config, "the local git config changed")
