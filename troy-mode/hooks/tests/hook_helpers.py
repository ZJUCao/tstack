"""Shared fixtures for the troy-mode hook tests (F05 design section 13.1).

The tests are written from the F05 design (version 1.0) and the interface
contract that fixes the details the design leaves to the Developer: the
subcommand names, the input and output JSON, the reason fragments, the log
format, the record path, and the scope table's module. They are black-box:
each test builds a small git repository in a temporary folder, feeds
``troy_hook.py <Event>`` one hook input on stdin, and checks stdout, stderr,
the exit code, and the files the contract names. Only the scope table test
imports the implementation (``troyhook.scopes``), as the contract allows.

Conventions. Where the design and the contract leave a detail open, the
tests require the following.

1. Silent. "No opinion" is exit code 0 with stdout and stderr both empty
   (contract 2). Every call the hooks let through without a plugin-read
   ``allow`` must be silent: a hook never prints ``allow`` for a write, a
   shell command, or a skill, because that would skip Claude Code's
   permission prompt.
2. Refused. A PreToolUse refusal is exit code 0 and stdout holding exactly
   one JSON object whose ``hookSpecificOutput`` has ``hookEventName``
   ``PreToolUse``, ``permissionDecision`` ``deny``, and a non-empty
   ``permissionDecisionReason``. A block is exit code 0 and
   ``{"decision": "block", "reason": <non-empty>}``. Reasons are checked
   only for the fragments of contract section 3.
3. The hook process runs in a neutral working folder that is in no
   repository, so the hook must use the input's ``cwd``. Claude Code's Bash
   tool also reports its own current folder in ``cwd``.
4. Temp folder. Every hook run gets ``TMPDIR``, ``TEMP``, and ``TMP`` set to
   one folder: by default ``HOOK_TEMP``, a private folder that holds no test
   repository. A test that needs the project itself to lie in the temp
   folder points the three at the project's parent folder. On Linux and
   macOS ``/tmp`` is a temp folder too, so the default repositories, which
   live under the system temp folder, already lie in a temp folder there.
5. Home folder. "Outside the repository and refused" uses a folder under
   ``Path.home()`` that does not exist and is never created. Tests that need
   it skip when the home folder lies in a temp folder.
6. Scratchpad. ``scratchpad_dir`` is either ``PAD`` (a real folder beside
   ``HOOK_TEMP``) or a folder under the home folder that is never created,
   so the scratchpad rule is tested on Linux too, where ``PAD`` lies in
   ``/tmp``.
7. Paths in shell commands are written with ``/`` separators
   (``Path.as_posix()``) and quoted with ``shlex.quote``. Windows-only tests
   also use Git Bash forms such as ``/c/Users/...``. A Git Bash ``/tmp/...``
   path is tested with the hook's temp variables set to the system temp
   folder, where Git Bash's ``/tmp`` points.
8. Scratch repositories are real repositories made with ``git init`` and
   one commit. The tests do not cover ``git init`` or ``git clone`` into a
   new folder, which the design leaves open.
9. Project fixture. Unless a test says otherwise, the project has a
   committed ``.troy-mode/config.toml`` with the Python pack's ``[paths]``
   and ``[attribution] mode = "strict"``, the four git hook files committed
   in ``.troy-mode/checks/git-hooks/``, ``core.hooksPath`` set to that
   folder, and branch ``feature`` checked out. So the hooks-off guard of
   design 8.2 never decides a test that is about something else, and a
   scratch repository commit passes although the scratch repository itself
   has no ``core.hooksPath`` (13.1: "``git -C <temp> commit`` passes").
10. Callers. The main session's input has no ``agent_id`` and no
    ``agent_type``. Every subagent's input has an ``agent_id``. Roles that
    run calls in parallel get their start record from ``SubagentStart``
    first, so no two hook processes create the same record at once.
11. Body files for ``gh pr create --body-file`` are named relative to the
    input ``cwd``.
12. SessionStart prints nothing when ``core.hooksPath`` is already
    ``.troy-mode/checks/git-hooks`` and the hook files are present. It
    prints ``additionalContext`` when it sets the value, when it finds
    another value, and when hook files are missing; the text itself is not
    checked.
13. SubagentStop letting a role stop prints no ``"decision": "block"``.
14. The rule of a refusal is checked through the ``rule`` key of the last
    log line where a test says so (contract 4). The log of a normal
    repository is ``.git/troy-mode/hooks.log`` and role records are
    ``.git/troy-mode/agents/<agent_id>.json``.
15. Windows-only cases (backslashes, drive letter case, Git Bash forms, case
    differences, ``<temp>-other``) use ``skipUnless(os.name == "nt")``. The
    ``/tmp`` and ``/tmp-other`` cases run on every platform: on Windows they
    are Git Bash forms (convention 7), and ``/tmp-other`` is no temp folder
    under any reading of it.
16. Parallel runs. Table-driven tests run their hook calls in parallel
    threads (``run_many``); each call is its own process, and only calls
    that leave the working tree unchanged run together.

Planted bugs (design 13.2) and the tests that catch them. Each test also
names its bug in its docstring.

- The Developer's scope with the tests class:
  test_scope_table.ScopeTableTests.test_table_equals_f04_section_3 and
  test_table_equals_agent_files;
  test_paths.RoleMatrixTests.test_each_role_against_each_path_class_and_pattern;
  test_callers.CallerTests.test_each_role_is_recognized_by_its_scope;
  test_changes.PostToolUseTests.test_new_test_file_blocks_and_names_it.
- An unanchored role pattern:
  test_callers.CallerTests.test_role_name_with_text_before_or_after_is_not_a_role
  and test_other_subagents_may_change_nothing_in_the_repository.
- No ignore check:
  test_paths.IgnoredAndGitFolderTests.test_ignored_paths_are_allowed;
  test_callers.CallerTests.test_other_subagents_may_write_ignored_files.
- A temp folder test that accepts /tmp-other (or <temp>-other):
  test_paths.OutsideRepositoryTests.test_tmp_other_is_refused and
  test_sibling_of_temp_folder_is_refused_on_windows;
  test_commands.ScratchRepositoryTests.test_tmp_other_is_not_scratch and
  test_sibling_of_the_temp_folder_is_not_scratch_on_windows.
- commit in the allowed git commands:
  test_commands.GitCommandTests.test_other_git_commands_are_refused;
  test_commands.ShellFormTests.test_refused_commands_inside_every_form.
- A scratch repository test that accepts the project:
  test_commands.ProjectInTempCommandTests.test_git_writes_in_the_project_are_refused;
  test_commands.ScratchRepositoryTests.test_project_is_not_a_scratch_repository (Linux);
  test_paths.ProjectInTempTests.test_out_of_scope_path_in_a_project_in_temp_is_refused.
- pre-push reading the local ref in place of the remote one:
  troy-mode/checks/tests/test_git_hooks.py PrePushTests
  test_local_main_pushed_to_another_branch_passes and
  test_updating_remote_main_is_refused.
- A role's call allowed on an exception:
  test_errors_and_log.ErrorTests.test_error_refuses_a_role_call;
  test_paths.ConfigFromHeadTests.test_invalid_committed_config_refuses_a_role.
- SubagentStop never blocking, and stop_hook_active ignored:
  test_changes.SubagentStopTests.test_stop_blocks_once_then_lets_the_role_stop
  (its first and its second stop).
- The config read from the working tree:
  test_paths.ConfigFromHeadTests.test_uncommitted_config_edit_does_not_widen_a_scope,
  test_staged_config_edit_does_not_widen_a_scope,
  test_broken_working_tree_config_is_not_read, and
  test_invalid_committed_config_refuses_a_role.
- A plugin read allowed outside CLAUDE_PLUGIN_ROOT:
  test_plugin_files.PluginReadTests.test_read_outside_the_plugin_root_gets_nothing.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -v
"""

from __future__ import annotations

import atexit
import itertools
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence, Union

# ---------------------------------------------------------------------------
# Locations in tstack.
# ---------------------------------------------------------------------------

TESTS = Path(__file__).resolve().parent
HOOKS_DIR = TESTS.parent
TROY_MODE = HOOKS_DIR.parent
REPO = TROY_MODE.parent
HOOK = HOOKS_DIR / "troy_hook.py"
HOOKS_JSON = REPO / "hooks" / "hooks.json"
CHECKS = TROY_MODE / "checks"
AGENTS = REPO / "agents"

# ---------------------------------------------------------------------------
# Fixed values.
# ---------------------------------------------------------------------------

EMAIL = "troy@example.test"
OTHER_EMAIL = "someone@example.test"
SESSION = "session-f05-tests"
CONFIG_PATH = ".troy-mode/config.toml"
HOOKS_PATH = ".troy-mode/checks/git-hooks"
GIT_HOOK_NAMES = ("commit-msg", "pre-commit", "pre-merge-commit", "pre-push")
# A secret-like token for the log tests. Not any provider's real format.
SECRET = "TROYSECRET-4f1d9a7c2e8b"
LOG_KEYS = frozenset({"time", "session", "agent_id", "agent_type", "event", "tool", "rule",
                      "paths", "subcommand", "decision"})
LOG_RULES = frozenset({"scope", "changes", "git", "gh", "skill", "no-verify", "hooks-path",
                       "hooks-off", "pr-from-main", "attribution", "unparsed", "error",
                       "gh-delete",  # gh-delete: F15 interface note section 6
                       "python-stdin"})  # python-stdin: F05 design 8.3 (D223)
LOG_DECISIONS = frozenset({"deny", "block", "stop"})
LOG_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ERROR_PREFIX = "troy-mode hook error"
ATTRIBUTION_LINE = "\U0001f916 Generated with [Claude Code](https://claude.com/claude-code)"
TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"
WORKERS = min(8, os.cpu_count() or 2)
IS_WINDOWS = os.name == "nt"

# The Python pack's [paths] (troy-mode/lang/python/config.toml).
PACK_TESTS = ("**/test_*.py", "**/*_test.py", "**/conftest.py")
PACK_DEPENDENCIES = ("pyproject.toml", "environment.yml", "requirements*.lock")

# ---------------------------------------------------------------------------
# Scratch folders. Everything lives under one temporary folder.
# ---------------------------------------------------------------------------

_TMP = tempfile.TemporaryDirectory(prefix="troyhook-", ignore_cleanup_errors=True)
atexit.register(_TMP.cleanup)
SCRATCH = Path(_TMP.name).resolve()
SYSTEM_TEMP = Path(tempfile.gettempdir()).resolve()
HOOK_TEMP = SCRATCH / "hooktemp"
PAD = SCRATCH / "pad"
NEUTRAL = SCRATCH / "neutral"
REPOS = SCRATCH / "repos"
TEMPLATES = SCRATCH / "templates"
# An installed plugin's cache folder, as F19 design 5.2 names it:
# ~/.claude/plugins/cache/tstack/tstack/<version>.
PLUGIN_ROOT = SCRATCH / "plugins" / "cache" / "tstack" / "tstack" / "9.9.9"
for _folder in (HOOK_TEMP, PAD, NEUTRAL, REPOS, TEMPLATES, PLUGIN_ROOT):
    _folder.mkdir(parents=True, exist_ok=True)
_GLOBAL_CONFIG = SCRATCH / "gitconfig"
# No background maintenance or gc, which could change a repository while a
# test reads it.
_GLOBAL_CONFIG.write_text("[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n"
                          "[init]\n\tdefaultBranch = main\n", encoding="utf-8")
_COUNTER = itertools.count(1)
_TEMPLATE_CACHE: dict = {}

_DROPPED_ENV = (
    "GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "PYTHONUTF8", "PYTHONIOENCODING",
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "TROY_MODE_PYTHON",
)

Content = Union[str, bytes]


def unique(prefix: str) -> str:
    """Returns a name that no other call in this run returns.

    Args:
        prefix: Start of the name.

    Returns:
        The prefix followed by a counter.
    """
    return f"{prefix}{next(_COUNTER)}"


def base_env(extra: Optional[Mapping[str, str]] = None) -> dict:
    """Builds an environment that isolates git from the user's machine.

    It follows troy-mode/checks/tests/helpers.py: no system config, a private
    global config, a fixed author and committer, and no GIT_DIR or similar.

    Args:
        extra: Variables that override or extend the isolated defaults.

    Returns:
        A new environment dictionary for a subprocess.
    """
    env = dict(os.environ)
    for name in _DROPPED_ENV:
        env.pop(name, None)
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(_GLOBAL_CONFIG),
        "GIT_AUTHOR_NAME": "Test Author",
        "GIT_AUTHOR_EMAIL": EMAIL,
        "GIT_COMMITTER_NAME": "Test Committer",
        "GIT_COMMITTER_EMAIL": EMAIL,
    })
    env.update(extra or {})
    return env


def run_git(cwd: Path, *args: str, check: bool = True) -> str:
    """Runs git in a test repository.

    Args:
        cwd: Folder to run in.
        *args: Arguments after ``git``.
        check: Raise when git fails.

    Returns:
        Standard output, stripped of the final line break.

    Raises:
        RuntimeError: git failed and check is true.
    """
    proc = subprocess.run(["git", *args], cwd=str(cwd), env=base_env(), capture_output=True,
                          encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                          check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}: {proc.stderr}")
    return proc.stdout.rstrip("\n")


def write_file(root: Path, rel: str, content: Content) -> Path:
    """Writes a file as UTF-8 with LF line endings, creating folders.

    Args:
        root: Base folder.
        rel: Path relative to the root, with ``/`` separators.
        content: Text or raw bytes.

    Returns:
        The file's path.
    """
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    return path


def remove_tree(path: Path) -> None:
    """Deletes a folder, read-only git objects included, ignoring failures."""
    def fix(func, target, *_):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            pass

    if not Path(path).exists():
        return
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=fix)
        else:
            shutil.rmtree(path, onerror=fix)
    except OSError:
        pass


def toml_list(values: Iterable[str]) -> str:
    """Returns a TOML array of strings."""
    return "[" + ", ".join(json.dumps(v) for v in values) + "]"


def make_config(email: Optional[str] = EMAIL, mode: Optional[str] = "strict",
                tests: Sequence[str] = PACK_TESTS,
                dependencies: Sequence[str] = PACK_DEPENDENCIES, extra: str = "") -> str:
    """Builds the text of a ``.troy-mode/config.toml``.

    Args:
        email: ``[identity] commit_email``, or None to leave it out.
        mode: ``[attribution] mode``, or None to leave it out.
        tests: ``[paths] tests`` patterns added to the built-in ones.
        dependencies: ``[paths] dependencies`` patterns.
        extra: Raw TOML appended at the end.

    Returns:
        The TOML text.
    """
    parts = []
    if email is not None:
        parts.append(f"[identity]\ncommit_email = {json.dumps(email)}\n")
    parts.append(f"[paths]\ntests = {toml_list(tests)}\n"
                 f"dependencies = {toml_list(dependencies)}\n")
    if mode is not None:
        parts.append(f"[attribution]\nmode = {json.dumps(mode)}\n")
    if extra:
        parts.append(extra)
    return "\n".join(parts)


DEFAULT_CONFIG = make_config()
INVALID_CONFIG = "[bogus]\nx = 1\n"

BASE_FILES: dict[str, str] = {
    ".gitignore": "reports/\nbuild/\n__pycache__/\n*.pyc\ntests/.cache/\n",
    "README.md": "# Sample\n",
    "LICENSE": "MIT\n",
    "docs/rules.md": "# Rules\n",
    "docs/requirements.md": "# Requirements\n",
    "docs/architecture.md": "# Architecture\n",
    "docs/features/F01/design.md": "# F01 design\n",
    "docs/features/F01/test-plan.md": "# F01 test plan\n",
    "src/pkg/__init__.py": "",
    "src/pkg/app.py": "def run():\n    return 1\n",
    "tests/test_app.py": "def test_run():\n    assert True\n",
    "pyproject.toml": "[project]\nname = \"sample\"\n",
}
DUMMY_GIT_HOOK = "#!/bin/sh\nexit 0\n"


def _build_template(files: Mapping[str, Content], config: Optional[str], troy_mode: bool,
                    hooks_on: bool, branch: Optional[str]) -> Path:
    """Builds or returns a cached template repository that callers copy.

    Args:
        files: Files of the base commit besides the troy-mode ones.
        config: Text of the committed config, or None for no file.
        troy_mode: Whether the project has ``.troy-mode/`` with the git hooks.
        hooks_on: Whether ``core.hooksPath`` is set to the hooks folder.
        branch: Branch to check out after the base commit on main, or None
            to stay on main.

    Returns:
        The template's path.
    """
    key = repr((sorted((k, v) for k, v in files.items()), config, troy_mode, hooks_on, branch))
    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]
    root = TEMPLATES / unique("t")
    root.mkdir(parents=True)
    run_git(root, "init", "-q", "-b", "main")
    with open(root / ".git" / "config", "a", encoding="utf-8", newline="\n") as handle:
        handle.write("[core]\n\tautocrlf = false\n[commit]\n\tgpgsign = false\n")
    all_files: dict[str, Content] = dict(files)
    if troy_mode:
        for name in GIT_HOOK_NAMES:
            all_files[f"{HOOKS_PATH}/{name}"] = DUMMY_GIT_HOOK
        if config is not None:
            all_files[CONFIG_PATH] = config
    for rel, content in all_files.items():
        path = write_file(root, rel, content)
        if rel.startswith(HOOKS_PATH + "/"):
            path.chmod(0o755)
    run_git(root, "add", "-A")
    run_git(root, "commit", "-q", "-m", "Base commit")
    if branch and branch != "main":
        run_git(root, "checkout", "-q", "-b", branch)
    if hooks_on:
        run_git(root, "config", "core.hooksPath", HOOKS_PATH)
    _TEMPLATE_CACHE[key] = root
    return root


class Project:
    """A throwaway git repository for one test or one test class.

    Attributes:
        root: The working tree, an absolute path with no links.
    """

    def __init__(self, files: Optional[Mapping[str, Content]] = None,
                 config: Optional[str] = DEFAULT_CONFIG, troy_mode: bool = True,
                 hooks_on: bool = True, branch: Optional[str] = "feature",
                 parent: Optional[Path] = None) -> None:
        """Copies a cached template repository into a new folder.

        Args:
            files: Files of the base commit. Defaults to BASE_FILES.
            config: Text of the committed ``.troy-mode/config.toml``.
            troy_mode: Whether the project is a troy-mode project.
            hooks_on: Whether ``core.hooksPath`` is set (troy-mode only).
            branch: Branch checked out, or None for main.
            parent: Folder to create the repository in. Defaults to REPOS.
        """
        template = _build_template(BASE_FILES if files is None else files, config, troy_mode,
                                   hooks_on and troy_mode, branch)
        folder = Path(parent) if parent is not None else REPOS
        folder.mkdir(parents=True, exist_ok=True)
        self.root = (folder / unique("p")).resolve()
        shutil.copytree(template, self.root)

    def close(self) -> None:
        """Deletes the repository."""
        remove_tree(self.root)

    def path(self, rel: str) -> Path:
        """Returns the absolute path of a repository-relative path."""
        return self.root / rel

    def git(self, *args: str, check: bool = True) -> str:
        """Runs git in the repository."""
        return run_git(self.root, *args, check=check)

    def write(self, rel: str, content: Content = "changed\n") -> Path:
        """Writes a file in the working tree."""
        return write_file(self.root, rel, content)

    def delete(self, rel: str) -> None:
        """Deletes a file from the working tree."""
        (self.root / rel).unlink()

    def commit_all(self, message: str = "Change") -> None:
        """Stages everything and commits it, without running git hooks."""
        self.git("add", "-A")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-q", "--no-verify", "-m", message)

    @property
    def git_dir(self) -> Path:
        """The repository's git folder."""
        return self.root / ".git"

    @property
    def log_path(self) -> Path:
        """The hook log of contract section 4."""
        return self.git_dir / "troy-mode" / "hooks.log"

    def record_path(self, agent_id: str) -> Path:
        """The start record of a role (contract section 4)."""
        return self.git_dir / "troy-mode" / "agents" / f"{agent_id}.json"

    def log_text(self) -> str:
        """Returns the whole log, or an empty string when there is none."""
        if not self.log_path.exists():
            return ""
        return self.log_path.read_text(encoding="utf-8")

    def log_lines(self) -> list[dict]:
        """Parses the log, one JSON object per non-blank line."""
        return [json.loads(line) for line in self.log_text().splitlines() if line.strip()]

    def hooks_path(self) -> Optional[str]:
        """Returns the local ``core.hooksPath``, or None when it is unset."""
        value = self.git("config", "--local", "--get", "core.hooksPath", check=False)
        return value or None


def scratch_repo(parent: Path, name: Optional[str] = None) -> Path:
    """Makes a plain git repository with one commit, as a scratch copy.

    Args:
        parent: Folder to create it in, usually a temp folder.
        name: Folder name, or None for a unique one.

    Returns:
        The repository's root.
    """
    root = (Path(parent) / (name or unique("scratch"))).resolve()
    root.mkdir(parents=True)
    run_git(root, "init", "-q", "-b", "main")
    write_file(root, "notes.txt", "scratch\n")
    run_git(root, "add", "-A")
    run_git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "Scratch copy")
    return root


def plain_folder(files: Mapping[str, Content]) -> Path:
    """Makes a folder that is not a git repository.

    Args:
        files: Files to write into it.

    Returns:
        The folder's path.
    """
    root = (SCRATCH / unique("plain")).resolve()
    root.mkdir(parents=True)
    for rel, content in files.items():
        write_file(root, rel, content)
    return root


def has_git_ancestor(path: Path) -> bool:
    """Tells whether a folder or one of its parents holds ``.git``."""
    for folder in (path, *path.parents):
        if (folder / ".git").exists():
            return True
    return False


def is_inside(path: Path, folder: Path) -> bool:
    """Tells whether a path lies inside a folder, without case on Windows."""
    a = os.path.normcase(os.path.abspath(path))
    b = os.path.normcase(os.path.abspath(folder))
    return a == b or a.startswith(b.rstrip("\\/") + os.sep)


def home_probe() -> Optional[Path]:
    """Returns a path under the home folder that is outside every temp folder.

    Returns:
        A path in a folder that does not exist, or None when the home folder
        lies in a temp folder and the tests that need it must skip.
    """
    home = Path.home().resolve()
    for temp in (SYSTEM_TEMP, HOOK_TEMP, Path("/tmp")):
        if is_inside(home, temp):
            return None
    return home / f"troyhook-probe-{uuid.uuid4().hex[:12]}" / "notes.txt"


def home_pad() -> Optional[Path]:
    """Returns a scratchpad folder under the home folder that is never created."""
    probe = home_probe()
    return None if probe is None else probe.parent.parent / f".troyhook-pad-{uuid.uuid4().hex[:12]}"


def q(path: Union[str, Path]) -> str:
    """Quotes a path for a shell command, with ``/`` separators."""
    text = path.as_posix() if isinstance(path, Path) else path
    return shlex.quote(text)


def git_bash_form(path: Path) -> str:
    """Returns the Git Bash form of a Windows path, for example ``/c/Users/x``."""
    text = Path(path).as_posix()
    if len(text) >= 2 and text[1] == ":":
        return "/" + text[0].lower() + text[2:]
    return text


# ---------------------------------------------------------------------------
# Callers.
# ---------------------------------------------------------------------------

ROLE_NAMES = ("architect", "interface-designer", "test-manager", "developer", "test-engineer",
              "code-reviewer")
# The plugin's prefix (F19 design 4.1), and its prefix before F19.
PREFIX = "tstack:"
OLD_PREFIX = "troy-pstack:"  # the plugin's name before tstack (F19 design 4.1)
# Subagents that are not roles (design section 4): an unknown tstack name, the
# fork /code-review runs as, Explore, names with text before or after a role
# name, and a role under the old prefix (F19 design section 3, probe 4).
OTHER_TYPES = ("tstack:troy-foo", "general-purpose", "Explore",
               "xtstack:troy-developer", "tstack:troy-developer-2",
               OLD_PREFIX + "troy-developer")


@dataclass(frozen=True)
class Caller:
    """Who makes a call: the main session, a role, or another subagent.

    Attributes:
        agent_type: The input's ``agent_type``, or None.
        agent_id: The input's ``agent_id``, or None for the main session.
        label: A short name for messages.
    """

    agent_type: Optional[str]
    agent_id: Optional[str]
    label: str


MAIN = Caller(None, None, "main session")


def role(name: str, suffix: str = "") -> Caller:
    """Returns a role caller, for example ``role("developer")``: ``tstack:troy-developer``."""
    return Caller(f"tstack:troy-{name}", f"agent-{name}{suffix}", name)


def old_role(name: str, suffix: str = "") -> Caller:
    """Returns a caller with a role's name under the old prefix: no longer a role (F19)."""
    return Caller(f"{OLD_PREFIX}troy-{name}", f"agent-old-{name}{suffix}", f"old {name}")


def other(agent_type: Optional[str], suffix: str = "") -> Caller:
    """Returns a subagent caller that is not a role."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", agent_type or "untyped").strip("-").lower()
    return Caller(agent_type, f"agent-{slug}{suffix}", agent_type or "no agent_type")


DEV = role("developer")
TE = role("test-engineer")
ARCH = role("architect")
IFD = role("interface-designer")
TM = role("test-manager")
CR = role("code-reviewer")
GP = other("general-purpose")
EXPLORE = other("Explore")
FOO = other("tstack:troy-foo")

# ---------------------------------------------------------------------------
# Hook runs.
# ---------------------------------------------------------------------------


@dataclass
class HookRun:
    """The result of one ``troy_hook.py`` run.

    Attributes:
        code: Exit code.
        stdout: Standard output.
        stderr: Standard error.
        event: The event the hook ran for.
        payload: The input it got.
    """

    code: int
    stdout: str
    stderr: str
    event: str = ""
    payload: dict = field(default_factory=dict)

    def data(self) -> Optional[dict]:
        """Parses stdout as one JSON object, or returns None."""
        text = self.stdout.strip()
        if not text:
            return None
        try:
            value = json.loads(text)
        except ValueError:
            return None
        return value if isinstance(value, dict) else None

    @property
    def decision(self) -> Optional[str]:
        """``deny``, ``allow``, ``block``, or None."""
        data = self.data() or {}
        specific = data.get("hookSpecificOutput")
        if isinstance(specific, dict) and "permissionDecision" in specific:
            return specific["permissionDecision"]
        return data.get("decision")

    @property
    def reason(self) -> str:
        """The refusal, allow, or block reason, or an empty string."""
        data = self.data() or {}
        specific = data.get("hookSpecificOutput")
        if isinstance(specific, dict) and "permissionDecisionReason" in specific:
            return str(specific["permissionDecisionReason"])
        return str(data.get("reason", ""))

    def describe(self) -> str:
        """Returns the run for assertion messages."""
        tool_input = self.payload.get("tool_input")
        caller = self.payload.get("agent_type") or ("main session" if "agent_id" not in
                                                    self.payload else "agent")
        return (f"\nevent={self.event} caller={caller} tool={self.payload.get('tool_name')} "
                f"input={json.dumps(tool_input, ensure_ascii=False)}\n"
                f"exit={self.code}\n--stdout--\n{self.stdout}\n--stderr--\n{self.stderr}")


def hook_env(temp: Path = HOOK_TEMP, plugin_root: Optional[Path] = PLUGIN_ROOT,
             extra: Optional[Mapping[str, str]] = None) -> dict:
    """Builds the environment of a hook process.

    Args:
        temp: Folder for ``TMPDIR``, ``TEMP``, and ``TMP`` (contract 6).
        plugin_root: ``CLAUDE_PLUGIN_ROOT``, or None to leave it unset.
        extra: More variables.

    Returns:
        The environment.
    """
    env = base_env()
    for name in ("TMPDIR", "TEMP", "TMP"):
        env[name] = str(temp)
    if plugin_root is not None:
        env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env.update(extra or {})
    return env


def run_hook(event: str, payload: dict, temp: Path = HOOK_TEMP,
             plugin_root: Optional[Path] = PLUGIN_ROOT,
             env_extra: Optional[Mapping[str, str]] = None, cwd: Path = NEUTRAL) -> HookRun:
    """Runs ``troy_hook.py <event>`` with the payload on stdin.

    Args:
        event: The hook event name.
        payload: The hook input.
        temp: The hook process's temp folder.
        plugin_root: ``CLAUDE_PLUGIN_ROOT``, or None.
        env_extra: More environment variables.
        cwd: The process's working folder (neutral by default).

    Returns:
        The run's result.
    """
    proc = subprocess.run(
        [sys.executable, str(HOOK), event],
        input=json.dumps(payload, ensure_ascii=False),
        cwd=str(cwd), env=hook_env(temp, plugin_root, env_extra), capture_output=True,
        encoding="utf-8", errors="replace", timeout=120, check=False)
    return HookRun(proc.returncode, proc.stdout, proc.stderr, event, payload)


@dataclass
class Call:
    """One hook run to make, so several can run in parallel.

    Attributes:
        event: The hook event.
        payload: The hook input.
        temp: The hook process's temp folder.
        plugin_root: ``CLAUDE_PLUGIN_ROOT``, or None.
        env_extra: More environment variables.
    """

    event: str
    payload: dict
    temp: Path = HOOK_TEMP
    plugin_root: Optional[Path] = PLUGIN_ROOT
    env_extra: Optional[dict] = None

    def run(self) -> HookRun:
        """Runs the hook."""
        return run_hook(self.event, self.payload, self.temp, self.plugin_root, self.env_extra)


def run_many(calls: Sequence[Call]) -> list[HookRun]:
    """Runs hook calls in parallel and returns their results in order."""
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(lambda call: call.run(), calls))


def _root(project: Union[Project, Path]) -> Path:
    """Returns the root of a Project, or the path itself."""
    return project.root if isinstance(project, Project) else Path(project)


def hook_input(event: str, cwd: Union[str, Path], caller: Caller = MAIN, **fields) -> dict:
    """Builds a hook input in Claude Code's shape (contract section 1).

    Args:
        event: The hook event name.
        cwd: The input's ``cwd``.
        caller: Who makes the call.
        **fields: More keys, such as ``tool_name`` or ``stop_hook_active``.

    Returns:
        The input dictionary.
    """
    data = {"session_id": SESSION, "transcript_path": str(SCRATCH / "transcript.jsonl"),
            "cwd": str(cwd), "hook_event_name": event, "permission_mode": "acceptEdits"}
    if caller.agent_id is not None:
        data["agent_id"] = caller.agent_id
    if caller.agent_type is not None:
        data["agent_type"] = caller.agent_type
    data.update({k: v for k, v in fields.items() if v is not None})
    return data


def pre_call(project: Union[Project, Path], caller: Caller, tool: str, tool_input: dict,
             cwd: Optional[Union[str, Path]] = None, scratchpad: Optional[Path] = None,
             temp: Path = HOOK_TEMP, plugin_root: Optional[Path] = PLUGIN_ROOT,
             session: str = SESSION) -> Call:
    """Builds a PreToolUse call.

    Args:
        project: The project (its root is the default ``cwd``).
        caller: Who makes the call.
        tool: ``tool_name``.
        tool_input: ``tool_input``.
        cwd: The input's ``cwd``, if not the project root.
        scratchpad: ``scratchpad_dir``, or None to leave it out.
        temp: The hook process's temp folder.
        plugin_root: ``CLAUDE_PLUGIN_ROOT``, or None.
        session: ``session_id``.

    Returns:
        The call.
    """
    payload = hook_input("PreToolUse", cwd if cwd is not None else _root(project), caller,
                         tool_name=tool, tool_input=tool_input,
                         scratchpad_dir=str(scratchpad) if scratchpad is not None else None)
    payload["session_id"] = session
    return Call("PreToolUse", payload, temp, plugin_root)


def write_call(project: Union[Project, Path], caller: Caller, path: Union[str, Path],
               tool: str = "Write", **kwargs) -> Call:
    """Builds a PreToolUse call for Write, Edit, or NotebookEdit.

    Args:
        project: The project.
        caller: Who makes the call.
        path: The file path, passed exactly as given.
        tool: ``Write``, ``Edit``, or ``NotebookEdit``.
        **kwargs: Passed on to pre_call.

    Returns:
        The call.
    """
    if tool == "NotebookEdit":
        tool_input = {"notebook_path": str(path), "new_source": "x = 1\n"}
    elif tool == "Edit":
        tool_input = {"file_path": str(path), "old_string": "a", "new_string": "b"}
    else:
        tool_input = {"file_path": str(path), "content": "x = 1\n"}
    return pre_call(project, caller, tool, tool_input, **kwargs)


def bash_call(project: Union[Project, Path], caller: Caller, command: str,
              tool: str = "Bash", **kwargs) -> Call:
    """Builds a PreToolUse call for Bash or PowerShell."""
    tool_input = {"command": command}
    if tool == "Bash":
        tool_input["description"] = "Run a command"
    return pre_call(project, caller, tool, tool_input, **kwargs)


def skill_call(project: Union[Project, Path], caller: Caller, skill: str,
               args: Optional[str] = None, **kwargs) -> Call:
    """Builds a PreToolUse call for Skill (contract: ``skill`` and ``args``)."""
    tool_input = {"skill": skill}
    if args is not None:
        tool_input["args"] = args
    return pre_call(project, caller, "Skill", tool_input, **kwargs)


def read_call(project: Union[Project, Path], caller: Caller, path: Union[str, Path],
              tool: str = "Read", **kwargs) -> Call:
    """Builds a PreToolUse call for Read (``file_path``) or Glob and Grep (``path``)."""
    if tool == "Read":
        tool_input = {"file_path": str(path)}
    elif tool == "Glob":
        tool_input = {"pattern": "**/*.md", "path": str(path)}
    else:
        tool_input = {"pattern": "Write", "path": str(path)}
    return pre_call(project, caller, tool, tool_input, **kwargs)


def post_call(project: Union[Project, Path], caller: Caller, tool: str = "Bash",
              command: str = "python -m pytest -q", session: str = SESSION) -> Call:
    """Builds a PostToolUse call for Bash, PowerShell, or Skill."""
    if tool == "Skill":
        tool_input = {"skill": "code-review"}
    else:
        tool_input = {"command": command}
    payload = hook_input("PostToolUse", _root(project), caller, tool_name=tool,
                         tool_input=tool_input,
                         tool_response={"stdout": "", "stderr": "", "interrupted": False})
    payload["session_id"] = session
    return Call("PostToolUse", payload)


def start_call(project: Union[Project, Path], caller: Caller) -> Call:
    """Builds a SubagentStart call."""
    return Call("SubagentStart", hook_input("SubagentStart", _root(project), caller))


def stop_call(project: Union[Project, Path], caller: Caller, active: bool = False,
              session: str = SESSION) -> Call:
    """Builds a SubagentStop call with ``stop_hook_active``."""
    payload = hook_input("SubagentStop", _root(project), caller, stop_hook_active=active,
                         agent_transcript_path=str(SCRATCH / "agent.jsonl"))
    payload["stop_hook_active"] = active
    payload["session_id"] = session
    return Call("SubagentStop", payload)


def session_call(project: Union[Project, Path], cwd: Optional[Path] = None) -> Call:
    """Builds a SessionStart call."""
    return Call("SessionStart", hook_input("SessionStart", cwd or _root(project), MAIN,
                                           source="startup"))


# ---------------------------------------------------------------------------
# Assertions.
# ---------------------------------------------------------------------------


class HookTestCase(unittest.TestCase):
    """A test case with assertions on hook runs."""

    maxDiff = None

    def assert_silent(self, out: HookRun, msg: str = "") -> None:
        """Asserts "no opinion": exit code 0 and nothing on stdout or stderr."""
        self.assertEqual(0, out.code, f"{msg} expected exit code 0 and no output" + out.describe())
        self.assertEqual("", out.stdout.strip(),
                         f"{msg} expected nothing on stdout" + out.describe())
        self.assertEqual("", out.stderr.strip(),
                         f"{msg} expected nothing on stderr" + out.describe())

    def _decision(self, out: HookRun, expected: str, msg: str) -> dict:
        """Asserts a PreToolUse permission decision and returns hookSpecificOutput."""
        self.assertEqual(0, out.code, f"{msg} expected exit code 0" + out.describe())
        data = out.data()
        self.assertIsNotNone(data, f"{msg} expected one JSON object on stdout" + out.describe())
        specific = data.get("hookSpecificOutput")
        self.assertIsInstance(specific, dict, f"{msg} no hookSpecificOutput" + out.describe())
        self.assertEqual("PreToolUse", specific.get("hookEventName"),
                         f"{msg} wrong hookEventName" + out.describe())
        self.assertEqual(expected, specific.get("permissionDecision"),
                         f"{msg} expected permissionDecision {expected}" + out.describe())
        reason = specific.get("permissionDecisionReason")
        self.assertIsInstance(reason, str, f"{msg} no reason" + out.describe())
        self.assertTrue(reason.strip(), f"{msg} empty reason" + out.describe())
        return specific

    def assert_denied(self, out: HookRun, *fragments: str, msg: str = "") -> None:
        """Asserts a PreToolUse refusal whose reason holds every fragment."""
        reason = self._decision(out, "deny", msg)["permissionDecisionReason"]
        for fragment in fragments:
            self.assertIn(fragment, reason, f"{msg} reason lacks {fragment!r}" + out.describe())

    def assert_allowed_read(self, out: HookRun, msg: str = "") -> None:
        """Asserts the plugin-read ``allow`` of design section 9."""
        self._decision(out, "allow", msg)

    def assert_blocked(self, out: HookRun, *fragments: str, absent: Sequence[str] = (),
                       msg: str = "") -> None:
        """Asserts a PostToolUse or SubagentStop block.

        Args:
            out: The run.
            *fragments: Text the reason must hold.
            absent: Text the reason must not hold.
            msg: Extra text for failure messages.
        """
        self.assertEqual(0, out.code, f"{msg} expected exit code 0" + out.describe())
        data = out.data()
        self.assertIsNotNone(data, f"{msg} expected one JSON object on stdout" + out.describe())
        self.assertEqual("block", data.get("decision"), f"{msg} expected a block" + out.describe())
        reason = data.get("reason")
        self.assertIsInstance(reason, str, f"{msg} no reason" + out.describe())
        self.assertTrue(reason.strip(), f"{msg} empty reason" + out.describe())
        for fragment in fragments:
            self.assertIn(fragment, reason, f"{msg} reason lacks {fragment!r}" + out.describe())
        for fragment in absent:
            self.assertNotIn(fragment, reason, f"{msg} reason names {fragment!r}" + out.describe())

    def assert_not_blocked(self, out: HookRun, msg: str = "") -> None:
        """Asserts exit code 0 and no block decision (convention 13)."""
        self.assertEqual(0, out.code, f"{msg} expected exit code 0" + out.describe())
        if out.stdout.strip():
            data = out.data()
            self.assertIsNotNone(data, f"{msg} stdout is not one JSON object" + out.describe())
            self.assertNotEqual("block", data.get("decision"), f"{msg} unexpected block" +
                                out.describe())

    def assert_error_refusal(self, out: HookRun, msg: str = "") -> None:
        """Asserts a subagent's call refused because of an error (D39)."""
        reason = self._decision(out, "deny", msg)["permissionDecisionReason"]
        self.assertTrue(reason.startswith(ERROR_PREFIX),
                        f"{msg} reason does not start with {ERROR_PREFIX!r}" + out.describe())

    def assert_main_error(self, out: HookRun, msg: str = "") -> None:
        """Asserts a main-session error: exit code 1, a notice on stderr, no stdout."""
        self.assertEqual(1, out.code, f"{msg} expected exit code 1" + out.describe())
        self.assertEqual("", out.stdout.strip(),
                         f"{msg} expected nothing on stdout" + out.describe())
        self.assertTrue(out.stderr.strip(), f"{msg} expected a notice on stderr" + out.describe())

    def assert_context(self, out: HookRun, msg: str = "") -> str:
        """Asserts a SessionStart notice and returns its text."""
        self.assertEqual(0, out.code, f"{msg} expected exit code 0" + out.describe())
        data = out.data()
        self.assertIsNotNone(data, f"{msg} expected one JSON object on stdout" + out.describe())
        specific = data.get("hookSpecificOutput")
        self.assertIsInstance(specific, dict, f"{msg} no hookSpecificOutput" + out.describe())
        self.assertEqual("SessionStart", specific.get("hookEventName"), msg + out.describe())
        text = specific.get("additionalContext")
        self.assertIsInstance(text, str, f"{msg} no additionalContext" + out.describe())
        self.assertTrue(text.strip(), f"{msg} empty additionalContext" + out.describe())
        return text

    def assert_last_log(self, project: Project, msg: str = "", **expected) -> dict:
        """Asserts the values of some keys in the last log line and returns it."""
        lines = project.log_lines()
        self.assertTrue(lines, f"{msg} the log is empty: {project.log_path}")
        last = lines[-1]
        for key, value in expected.items():
            self.assertEqual(value, last.get(key), f"{msg} log key {key}: {last}")
        return last
