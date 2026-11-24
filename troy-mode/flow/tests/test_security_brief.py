"""The security review in the briefs: CR1's risk check and CR2 (tstack #75; F04 D280 to D283).

Written from the build contract for tstack #75 (sections A and B) and the designs it cites
(F04 design 6.7 and 6.8, F07 design 6.5, 14.1, and 14.2, F08 design 5.9) before the code
exists. Black-box, as F07's brief tests are: ``troy_flow.py brief ... --json`` runs as a
subprocess, and the tests read its report and prompt.

Contract A, CR1's Task line. Every CR1 brief's Task line holds exactly one of three
sentences, after the task's own sentence, the team sentence, and the mock-note text, and
before the platform-skip sentence (D69): the signs found in the diff from
``git merge-base origin/main HEAD`` to ``HEAD``, the "not needed" sentence, or the review
for a pack the check has no lists for. No other task's brief holds either.

- ``ContextTests``: every CR1 context (PR 3, 4, and 5, the redo of PR 3, a test-fix side PR,
  a bug's PR A and PR B, a version tests PR, a rule's two cleanup PRs) holds the sentence
  once, in its place; the other tasks hold none.
- ``PythonSignTests`` and ``CppSignTests``: each sign of the two packs, with its place, and
  text that is no sign.
- ``DependencyTests``: dependency files, and CMake files only with a line that names a
  package.
- ``DiffTests``: added lines only, committed changes only, line numbers of the new file, the
  path classes from the config at HEAD.
- ``ListTests``: up to three places, ", and <n> more", the kinds in order and joined.
- ``MergeBaseTests``: the diff starts at the merge base after ``origin/main`` moved on.
- ``TeamWorktreeTests``: a team's brief reads the diff of its worktree.
- ``UnknownPackTests``: a pack the check does not know.

Contract B, CR2's brief: ``Cr2BriefTests`` and ``Cr2RefusalTests``.

Planted bugs of F07 design 14.2 (F04 D280 to D283) caught here:

- "a deleted line counted as a sign": ``DiffTests.test_added_lines_only`` (row "deleted
  lines").
- "a test file's subprocess call counted": ``DiffTests.test_path_classes`` (row "a test
  file").
- "a CMake line that adds the project's own file counted as a dependency":
  ``DependencyTests`` (row "CMake: the project's own file").
- "the C/C++ lists used for a Python project": ``PythonSignTests`` (every Python-only sign,
  such as ``import subprocess``) and ``CppSignTests.test_python_lists_not_used_for_cpp``.
- "the diff taken from origin/main rather than from the merge base": ``MergeBaseTests``.
- "the sentence left out of a bug's CR1 brief": ``ContextTests`` (rows "CR1 in a bug's
  test PR" and "CR1 in a bug's fix PR").
- "CR2 briefed off the review branch": ``Cr2RefusalTests``.

Run from the repository root:
python -B -m unittest discover -s troy-mode/flow/tests -p "test_security_brief.py" -v
"""

import json
import os
import subprocess
import sys
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Optional, Sequence

from flow_helpers import (
    ARCHITECTURE, CONFIG, ENGINE, F01, F02, F03, REQUIREMENTS, RULES, SCRATCH, WORK_BRANCH,
    Fakes, FlowCase, Outcome, Project, accepted_plan_files, base_env, base_files, base_step,
    bug_step, bug_title, change_step, config_text, git, new_dir, origin_repo, parallel,
    release_step, rework, run_engine, stages, subject_commits, version_tests_step, write_file,
)
from rule_helpers import rules_step
from test_mock_notes_brief import CR1_PR3_CPP, CR1_PR3_PY, CR1_PR5

# ---------------------------------------------------------------- the sentences

# Contract A: the sentence when the check finds no sign, word for word.
NO_SIGN = ("troy-mode's check finds no dependency, subprocess call, network access, or "
           "credential handling that the diff adds, so `/security-review` is not needed, unless "
           "you see one of those four that the check missed.")
# The start of the two sentences that ask for the review.
RUN_PREFIX = "Run `/security-review` too, because "
SIGNS_PREFIX = RUN_PREFIX + "the diff adds "
# The platform-skip sentence that ends a code task's Task line (F07 D69).
D69 = ("A test that the test plan runs only on another platform is skipped here, and "
       "troy-check code reports it under R09 or R10; CI checks it, so name it in your report "
       "and do not count it as a failure.")
# The four kinds of contract A, in their order.
DEP = "a dependency change"
SUB = "a subprocess call"
NET = "network access"
CRED = "credential handling"


def unknown_pack(name: str) -> str:
    """Contract A's sentence for a language pack the check has no lists for."""
    return f"{RUN_PREFIX}troy-mode's check has no lists for the language pack {name}."


def part(kind: str, places: Sequence[str], more: int = 0) -> str:
    """One kind with its places, as ``<kind> (<place>, <place>, and <n> more)``."""
    tail = f", and {more} more" if more else ""
    return f"{kind} ({', '.join(places)}{tail})"


def signs(*parts: str) -> str:
    """The sentence for the signs found: kinds joined as "X", "X and Y", or "X, Y, and Z"."""
    if len(parts) == 1:
        text = parts[0]
    elif len(parts) == 2:
        text = f"{parts[0]} and {parts[1]}"
    else:
        text = ", ".join(parts[:-1]) + ", and " + parts[-1]
    return f"{SIGNS_PREFIX}{text}."


def task_line(prompt: str) -> str:
    """The prompt's ``Task:`` line, or "" when there is none."""
    return next((line for line in prompt.split("\n") if line.startswith("Task: ")), "")


def security_sentence(line: str) -> Optional[str]:
    """The security sentence of a Task line: from its start up to D69 or the line's end.

    Args:
        line: The Task line.

    Returns:
        The sentence, or None when the line holds none of the three.
    """
    starts = [line.find(text) for text in (RUN_PREFIX, NO_SIGN) if text in line]
    if not starts:
        return None
    start = min(starts)
    end = line.find(" " + D69, start)
    return line[start:] if end == -1 else line[start:end]


def markers(prompt: str) -> int:
    """How many security sentences of contract A the prompt holds."""
    return prompt.count(RUN_PREFIX) + prompt.count(NO_SIGN)


# ---------------------------------------------------------------- fixtures

F03V2 = replace(F03, version="v0.2")
THREE = (F01, F02, F03V2)
TAG = "v0.1.0"
CRASH = "Crash on empty history"
MOCK_SUBJECT = F01.title(3)
TEST_FIX_F01 = "[F01 test-fix] Wrong count in F01-T01"
B12_TEST = bug_title("B12", "test", CRASH)
REFACTOR = "[refactor] Apply P01 to counting"
RULE_TEST_FIX = "[P01 test-fix] Apply P01 to tests"
PROBE_PY = "src/wordcount/probe.py"
PROBE_CPP = "src/app/probe.cpp"
PYPROJECT = "pyproject.toml"
PYPROJECT_TEXT = '[project]\nname = "wordcount"\nversion = "0.1.0"\n'

LEGACY = "src/wordcount/legacy.py"
LEGACY_TEXT = ('"""Legacy helpers."""\n\nimport subprocess\n\n\ndef run(args):\n'
               '    """Runs a command."""\n    return subprocess.run(args, check=False)\n')
TABLE = "src/wordcount/table.py"
TABLE_TEXT = ('"""Tables."""\n\n\ndef width(cells):\n    """The widest cell."""\n'
              "    return max(len(c) for c in cells)\n")

# The C/C++ pack's [paths] table (troy-mode/lang/cpp/config.toml), so that CMake files are
# dependencies and *_test.cc files are tests.
CPP_PATHS = ('[paths]\n'
             'config = [".clang-format", ".clang-tidy", "include/troy/not_implemented.h"]\n'
             'tests = ["**/*_test.cc", "**/*_test.cpp"]\n'
             'dependencies = ["CMakeLists.txt", "**/CMakeLists.txt", "cmake/**", '
             '"CMakePresets.json", "environment.yml", "requirements*.lock", '
             '"requirements*.in"]\nlock = ["requirements*.lock"]\n')
CPP_CONFIG = config_text("cpp").replace('[paths]\ndependencies = ["pyproject.toml"]\n', CPP_PATHS)
CMAKE = "CMakeLists.txt"
CMAKE_TEXT = ("cmake_minimum_required(VERSION 3.25)\nproject(wordcount CXX)\n"
              "find_package(fmt REQUIRED)\nadd_subdirectory(src/app)\n")
SUB_CMAKE = "src/app/CMakeLists.txt"
SUB_CMAKE_TEXT = "add_library(app main.cpp)\n"
DEPS_CMAKE = "cmake/deps.cmake"
DEPS_CMAKE_TEXT = "# The project's packages.\n"
PRESETS = "CMakePresets.json"
PRESETS_TEXT = '{\n  "version": 6\n}\n'

PY_EXTRA = {LEGACY: LEGACY_TEXT, TABLE: TABLE_TEXT}
CPP_EXTRA = {CONFIG: CPP_CONFIG, CMAKE: CMAKE_TEXT, SUB_CMAKE: SUB_CMAKE_TEXT,
             DEPS_CMAKE: DEPS_CMAKE_TEXT, PRESETS: PRESETS_TEXT,
             "src/app/main.cpp": "// Main.\n\nint main() { return 0; }\n"}

# The histories of origin/main. "py" and "cpp" put F01 at stage 3 (its mock PR).
ORIGINS = {
    "py": [base_step(base_files(extra=PY_EXTRA)), *stages(F01, 2)],
    "cpp": [base_step(base_files(lang="cpp", extra=CPP_EXTRA)), *stages(F01, 2)],
    "py4": [base_step(), *stages(F01, 3)],
    "py5": [base_step(), *stages(F01, 4)],
    "rework": [base_step(), *stages(F01, 3), change_step(features=(rework(F01), F02))],
    "bug": [base_step(), *stages(F01, 2), bug_step("B12", "test", CRASH)],
    "version": [base_step(base_files(THREE)), *stages(F01, 6), *stages(F02, 6),
                *stages(F03V2, 4)],
    "rule": [rules_step(), *stages(F01, 2)],
}
_SHARED: dict = {}


def shared_fakes() -> Fakes:
    """The one set of fakes every brief of this file uses; a brief makes no gh call."""
    if "fakes" not in _SHARED:
        _SHARED["fakes"] = Fakes(fail=True)
    return _SHARED["fakes"]


def build_origins(names: Sequence[str]) -> None:
    """Builds the bare origins before runs start side by side."""
    shared_fakes()
    for name in sorted(set(names)):
        origin_repo(ORIGINS[name])


def py_probe(line: str) -> str:
    """A Python source file whose third line is the given line."""
    return f'"""Probe."""\n\n{line}\n'


def cpp_probe(line: str) -> str:
    """A C/C++ source file whose third line is the given line."""
    return f"// Probe.\n\n{line}\n"


def numbered(total: int, lines: dict) -> str:
    """A Python file of ``total`` lines: the given lines by number, filler lines elsewhere."""
    return "".join(lines.get(n, f"x{n} = {n}") + "\n" for n in range(1, total + 1))


def commit(files: dict, subject: str = MOCK_SUBJECT) -> tuple:
    """One commit on the work branch, as ``Case.commits`` holds it."""
    return ((subject, files),)


@dataclass(frozen=True)
class Case:
    """One brief on a clone of an origin, after commits on the work branch.

    Attributes:
        label: The case's name.
        origin: A key of ``ORIGINS``.
        commits: ``(subject, files)`` pairs committed in order; None content deletes.
        expected: The security sentence the Task line must hold.
        setup: Called with the clone after the commits, or None.
        task: The task ID.
        item: The item.
        title: The ``--title`` value, or None.
    """

    label: str
    origin: str
    commits: tuple = ()
    expected: str = NO_SIGN
    setup: Optional[Callable] = None
    task: str = "CR1"
    item: str = "F01"
    title: Optional[str] = None


def run_case(case: Case) -> Outcome:
    """Clones the case's origin, makes its commits and setup, and runs its brief."""
    project = Project(ORIGINS[case.origin])
    for subject, files in case.commits:
        project.commit(subject, files)
    if case.setup is not None:
        case.setup(project)
    args = ["brief", "--task", case.task, "--item", case.item]
    if case.title is not None:
        args += ["--title", case.title]
    return project.run(*args, fakes=shared_fakes())


def run_cases(cases: Sequence[Case]) -> dict:
    """Runs every case side by side and maps each label to its outcome."""
    build_origins([case.origin for case in cases])
    labels = [case.label for case in cases]
    if len(labels) != len(set(labels)):
        raise AssertionError("two cases share a label")
    return dict(zip(labels, parallel(run_case, cases)))


class SecurityCase(FlowCase):
    """Runs a table of cases once and checks the security sentence of each."""

    CASES: Sequence[Case] = ()

    @classmethod
    def setUpClass(cls):
        """Runs the class's cases side by side."""
        cls.outs = run_cases(cls.CASES)

    def prompt_of(self, label: str, task: str = "CR1") -> str:
        """The prompt of one case's brief, which must succeed for the task asked."""
        report = self.report_of(self.outs[label], 0, "brief")
        prompt = report.get("prompt") or ""
        self.assertTrue(task_line(prompt).startswith(f"Task: {task}, "), prompt)
        return prompt

    def assert_sentence(self, label: str, expected: str) -> None:
        """Asserts that the CR1 Task line holds exactly the expected sentence, before D69."""
        prompt = self.prompt_of(label)
        line = task_line(prompt)
        self.assertEqual(security_sentence(line), expected, line)
        self.assertEqual(markers(prompt), 1, prompt)
        self.assertTrue(line.endswith(f" {expected} {D69}"), line)

    def check_table(self) -> None:
        """Asserts each case's expected sentence."""
        for case in self.CASES:
            with self.subTest(case=case.label):
                self.assert_sentence(case.label, case.expected)


# ---------------------------------------------------------------- contexts

SHELL_PY = {"src/wordcount/shell.py": '"""Shell."""\n\nimport subprocess\n'}
SHELL_CPP = {"src/app/shell.cpp": '// Shell.\n\nint rc = system("ls");\n'}
SHELL_PY_SENTENCE = signs(part(SUB, ["src/wordcount/shell.py:3"]))
SHELL_CPP_SENTENCE = signs(part(SUB, ["src/app/shell.cpp:3"]))

# (label, origin, item, --title or None, the mock-note text before the sentence or None)
CR1_CONTEXTS = [
    ("CR1 at PR 3", "py", "F01", None, CR1_PR3_PY),
    ("CR1 at PR 3, C/C++", "cpp", "F01", None, CR1_PR3_CPP),
    ("CR1 at PR 4", "py4", "F01", None, None),
    ("CR1 at PR 5", "py5", "F01", None, CR1_PR5),
    ("CR1 on the redo of PR 3", "rework", "F01", F01.title(3), CR1_PR3_PY),
    ("CR1 in a test-fix side PR", "py5", "F01", TEST_FIX_F01, None),
    ("CR1 in a bug's test PR", "py", "B12", B12_TEST, None),
    ("CR1 in a bug's fix PR", "bug", "B12", None, None),
    ("CR1 in a version's tests PR", "version", "v0.1", None, None),
    ("CR1 in a rule's refactor PR", "rule", "P01", REFACTOR, None),
    ("CR1 in a rule's test-fix PR", "rule", "P01", RULE_TEST_FIX, None),
]
# (label, origin, task, item, --title or None): tasks whose briefs hold no sentence.
OTHER_TASKS = [
    ("DV1 at PR 3", "py", "DV1", "F01", None),
    ("AR5 at PR 3", "py", "AR5", "F01", None),
    ("DV1 at PR 3, C/C++", "cpp", "DV1", "F01", None),
    ("TE1 at PR 4", "py4", "TE1", "F01", None),
    ("TM2 at PR 4", "py4", "TM2", "F01", None),
    ("DV2 at PR 5", "py5", "DV2", "F01", None),
    ("TM3 at PR 5", "py5", "TM3", "F01", None),
    ("TM4 at PR 5", "py5", "TM4", "F01", None),
    ("TE3 in a test-fix side PR", "py5", "TE3", "F01", TEST_FIX_F01),
    ("TM2 in a test-fix side PR", "py5", "TM2", "F01", TEST_FIX_F01),
    ("TE2 in a bug's test PR", "py", "TE2", "B12", B12_TEST),
    ("TM2 in a bug's test PR", "py", "TM2", "B12", B12_TEST),
    ("DV3 in a bug's fix PR", "bug", "DV3", "B12", None),
    ("TE5 for v0.1", "version", "TE5", "v0.1", None),
    ("TM2 in a version's tests PR", "version", "TM2", "v0.1", None),
    ("TM7 for v0.1", "version", "TM7", "v0.1", None),
    ("TM8 for v0.1", "version", "TM8", "v0.1", None),
    ("DV5 in a rule's refactor PR", "rule", "DV5", "P01", REFACTOR),
    ("TE6 in a rule's test-fix PR", "rule", "TE6", "P01", RULE_TEST_FIX),
    ("TM2 in a rule's test-fix PR", "rule", "TM2", "P01", RULE_TEST_FIX),
]


def context_commit(origin: str) -> tuple:
    """The work branch's commit in a context clone: one subprocess call in a source file."""
    return commit(SHELL_CPP if origin == "cpp" else SHELL_PY, "[F01 3/6 mock] Count words")


class ContextTests(SecurityCase):
    """Contract A: every CR1 brief gets the sentence once, in its place; no other task's does.

    Each clone's work branch adds one subprocess call, so a brief that holds the sentence
    holds the signs sentence, whatever the task.
    """

    CASES = ([Case(label, origin, context_commit(origin),
                   SHELL_CPP_SENTENCE if origin == "cpp" else SHELL_PY_SENTENCE,
                   item=item, title=title)
              for label, origin, item, title, _ in CR1_CONTEXTS]
             + [Case(label, origin, context_commit(origin), task=task, item=item, title=title)
                for label, origin, task, item, title in OTHER_TASKS])

    def test_every_cr1_brief_holds_the_signs_sentence_once(self):
        """Feature stages 3 to 5, the redo of PR 3, a test-fix side PR, a bug's PR A and PR B,
        a version tests PR, and a rule's two cleanup PRs: the sentence, once, before D69.

        Planted bug caught: "the sentence left out of a bug's CR1 brief".
        """
        for label, origin, _, _, _ in CR1_CONTEXTS:
            with self.subTest(case=label):
                expected = SHELL_CPP_SENTENCE if origin == "cpp" else SHELL_PY_SENTENCE
                self.assert_sentence(label, expected)

    def test_sentence_follows_the_task_sentence_and_the_mock_notes(self):
        """The Task line is the task's own sentence, the mock-note text when there is one,
        the security sentence, then D69, each once."""
        for label, origin, _, _, notes in CR1_CONTEXTS:
            with self.subTest(case=label):
                line = task_line(self.prompt_of(label))
                expected = SHELL_CPP_SENTENCE if origin == "cpp" else SHELL_PY_SENTENCE
                where = line.find(expected)
                self.assertGreater(where, 0, line)
                before = line[:where]
                self.assertTrue(before.startswith("Task: CR1, review the PR "), line)
                self.assertTrue(before.endswith(". "), line)
                if notes is not None:
                    self.assertTrue(before.endswith(f" {notes} "), line)
                    self.assertEqual(line.count(notes), 1, line)
                self.assertEqual(line.count(D69), 1, line)

    def test_other_tasks_hold_no_sentence(self):
        """Authors, the Test Manager, TM7, TM8, and the rule's authors: neither sentence."""
        for label, _, task, _, _ in OTHER_TASKS:
            with self.subTest(case=label):
                prompt = self.prompt_of(label, task)
                self.assertEqual(markers(prompt), 0, prompt)
                self.assertNotIn("troy-mode's check", prompt)


# ---------------------------------------------------------------- Python signs

# (label, the probe's third line, kind)
PY_SIGNS = [
    ("import subprocess", "import subprocess", SUB),
    ("import pty", "import pty", SUB),
    ("import subprocess as", "import subprocess as sp", SUB),
    ("import a, b", "import os, subprocess", SUB),
    ("from subprocess import", "from subprocess import run", SUB),
    ("subprocess. anywhere", 'result = subprocess.run(["ls"], check=False)', SUB),
    ("os.system(", 'os.system("ls")', SUB),
    ("os.popen(", 'pipe = os.popen("ls")', SUB),
    ("os.execv(", 'os.execv("/bin/ls", ["ls"])', SUB),
    ("os.execlp(", 'os.execlp("ls", "ls")', SUB),
    ("os.spawnlp(", 'pid = os.spawnlp(os.P_WAIT, "ls", "ls")', SUB),
    ("os.posix_spawn(", 'pid = os.posix_spawn("/bin/ls", ["ls"], {})', SUB),
    ("os.posix_spawnp(", 'pid = os.posix_spawnp("ls", ["ls"], {})', SUB),
    ("from os import system", "from os import system", SUB),
    ("from os import popen among others", "from os import getcwd, popen", SUB),
    ("from os import execvp", "from os import execvp", SUB),
    ("from os import spawnv", "from os import spawnv", SUB),
    ("from os import posix_spawnp", "from os import posix_spawnp", SUB),
    ("asyncio.create_subprocess_exec", 'proc = asyncio.create_subprocess_exec("ls")', SUB),
    ("asyncio.create_subprocess_shell", 'proc = asyncio.create_subprocess_shell("ls")', SUB),
    ("subprocess. in a comment", "# Never call subprocess.run here.", SUB),
    ("subprocess. in a string", 'HELP = "Uses subprocess.run under the hood."', SUB),
    ("import socket", "import socket", NET),
    ("import ssl", "import ssl", NET),
    ("import http.client", "import http.client", NET),
    ("from http import", "from http import client", NET),
    ("import urllib.request", "import urllib.request", NET),
    ("from urllib.parse import", "from urllib.parse import urlparse", NET),
    ("import urllib3", "import urllib3", NET),
    ("import ftplib", "import ftplib", NET),
    ("import smtplib", "import smtplib", NET),
    ("import poplib", "import poplib", NET),
    ("import imaplib", "import imaplib", NET),
    ("import xmlrpc.client", "import xmlrpc.client", NET),
    ("import socketserver", "import socketserver", NET),
    ("import webbrowser", "import webbrowser", NET),
    ("import requests", "import requests", NET),
    ("import requests as", "import requests as rq", NET),
    ("import httpx", "import httpx", NET),
    ("import aiohttp", "import aiohttp", NET),
    ("import websockets", "import websockets", NET),
    ("import grpc", "import grpc", NET),
    ("import paramiko", "import paramiko", NET),
    ("import a, b with a network module", "import json, socket", NET),
    ("asyncio.open_connection", 'reader, writer = asyncio.open_connection("localhost", 80)',
     NET),
    ("asyncio.start_server", 'server = asyncio.start_server(handle, "localhost", 80)', NET),
    ("import getpass", "import getpass", CRED),
    ("import keyring", "import keyring", CRED),
    ("import netrc", "import netrc", CRED),
    ("import secrets", "import secrets", CRED),
    ("a name with password", 'user_password = ""', CRED),
    ("a name with PASSWD", 'PASSWD = ""', CRED),
    ("a name with passphrase", "passphrase = ask()", CRED),
    ("a name with credential", "creds = load_credentials()", CRED),
    ("a name with secret", 'client_secret = ""', CRED),
    ("a name with API_KEY", 'API_KEY = ""', CRED),
    ("a name with apikey", 'apikey = ""', CRED),
    ("a name with access_token", 'access_token = ""', CRED),
    ("a name with auth_token in mixed case", "MyAuth_Token = None", CRED),
    ("a name with private_key", "private_key = None", CRED),
    ("password in a comment", "# The password stays on this PC.", CRED),
    ("passphrase in a string", 'PROMPT = "Enter the passphrase:"', CRED),
]
PY_NO_SIGN = ('"""Probe."""\n\nimport os\nimport json, re\nimport tokenize\n'
              "from os import path, getcwd\n\n\ndef tokens_of(text):\n"
              "    token = next(iter(text))\n"
              '    with open(os.path.join(getcwd(), "notes.txt"), encoding="utf-8") as handle:\n'
              "        return token, tokenize, handle.read()\n")


class PythonSignTests(SecurityCase):
    """Contract A, Python: each sign in an added line of a source file, with its place."""

    CASES = ([Case(f"Python: {label}", "py", commit({PROBE_PY: py_probe(line)}),
                   signs(part(kind, [f"{PROBE_PY}:3"])))
              for label, line, kind in PY_SIGNS]
             + [Case("Python: no sign", "py", commit({PROBE_PY: PY_NO_SIGN}))])

    def test_each_sign_with_its_place(self):
        """``import``, ``from ... import``, calls, names, comments, and strings: one kind each,
        at ``src/wordcount/probe.py:3``.

        Planted bug caught: "the C/C++ lists used for a Python project".
        """
        for label, _, kind in PY_SIGNS:
            with self.subTest(case=label):
                self.assert_sentence(f"Python: {label}", signs(part(kind, [f"{PROBE_PY}:3"])))

    def test_text_that_is_no_sign(self):
        """``os`` alone, ``os.path``, ``tokenize``, ``token``, and reading a file: no sign."""
        self.assert_sentence("Python: no sign", NO_SIGN)


# ---------------------------------------------------------------- C/C++ signs

# (label, the probe's third line, kind)
CPP_SIGNS = [
    ("system(", 'int rc = system("ls");', SUB),
    ("std::system(", 'int rc = std::system("ls");', SUB),
    ("system with spaces before (", 'int rc = system ("ls");', SUB),
    ("popen(", 'FILE* pipe = popen("ls", "r");', SUB),
    ("_popen(", 'FILE* pipe = _popen("ls", "r");', SUB),
    ("_wpopen(", 'FILE* pipe = _wpopen(L"ls", L"r");', SUB),
    ("execl(", 'execl("/bin/ls", "ls", nullptr);', SUB),
    ("execle(", 'execle("/bin/ls", "ls", nullptr, environ);', SUB),
    ("execlp(", 'execlp("ls", "ls", nullptr);', SUB),
    ("execv(", 'execv("/bin/ls", argv);', SUB),
    ("execve(", 'execve("/bin/ls", argv, environ);', SUB),
    ("execvp(", "execvp(argv[0], argv);", SUB),
    ("execvpe(", "execvpe(argv[0], argv, environ);", SUB),
    ("fork(", "pid_t child = fork();", SUB),
    ("vfork(", "pid_t child = vfork();", SUB),
    ("posix_spawn(", 'posix_spawn(&pid, "/bin/ls", nullptr, nullptr, argv, environ);', SUB),
    ("posix_spawnp(", 'posix_spawnp(&pid, "ls", nullptr, nullptr, argv, environ);', SUB),
    ("CreateProcessW(", "CreateProcessW(nullptr, line, nullptr, nullptr, FALSE, 0, nullptr, "
                        "nullptr, &startup, &info);", SUB),
    ("CreateProcessAsUserW(", "CreateProcessAsUserW(user, nullptr, line, nullptr, nullptr, "
                              "FALSE, 0, nullptr, nullptr, &startup, &info);", SUB),
    ("ShellExecuteW(", 'ShellExecuteW(nullptr, L"open", L"notes.txt", nullptr, nullptr, '
                       "SW_SHOW);", SUB),
    ("ShellExecuteExW(", "ShellExecuteExW(&execute);", SUB),
    ("WinExec(", 'WinExec("notepad", SW_SHOW);', SUB),
    ("#include <spawn.h>", "#include <spawn.h>", SUB),
    ("#include <boost/process.hpp>", "#include <boost/process.hpp>", SUB),
    ("#include <boost/process/child.hpp>", "#include <boost/process/child.hpp>", SUB),
    ("system( in a comment", '// Never call system("ls") here.', SUB),
    ("#include <sys/socket.h>", "#include <sys/socket.h>", NET),
    ("#include <netinet/in.h>", "#include <netinet/in.h>", NET),
    ("#include <netinet/tcp.h>", "#include <netinet/tcp.h>", NET),
    ("#include <arpa/inet.h>", "#include <arpa/inet.h>", NET),
    ("#include <netdb.h>", "#include <netdb.h>", NET),
    ("#include <winsock.h>", "#include <winsock.h>", NET),
    ("#include <winsock2.h>", "#include <winsock2.h>", NET),
    ("#include <ws2tcpip.h>", "#include <ws2tcpip.h>", NET),
    ("#include <curl/curl.h>", "#include <curl/curl.h>", NET),
    ('#include "curl/curl.h"', '#include "curl/curl.h"', NET),
    ("#include <boost/asio.hpp>", "#include <boost/asio.hpp>", NET),
    ("#include <boost/asio/ip/tcp.hpp>", "#include <boost/asio/ip/tcp.hpp>", NET),
    ("#include <asio.hpp>", "#include <asio.hpp>", NET),
    ('#include "asio.hpp"', '#include "asio.hpp"', NET),
    ("getaddrinfo(", "int rc = getaddrinfo(host, port, &hints, &found);", NET),
    ("WSAStartup(", "int rc = WSAStartup(MAKEWORD(2, 2), &data);", NET),
    ("a name with api_key", "std::string api_key = read_key();", CRED),
    ("a name with PASSWORD", 'const char* PASSWORD_VAR = "APP_PASSWORD";', CRED),
    ("a name with access_token", "std::string access_token;", CRED),
    ("a name with private_key", "auto private_key = load();", CRED),
    ("secret in a comment", "// The secret stays on this PC.", CRED),
]
CPP_NO_SIGN = ("// Probe.\n\n#include <string>\n#include <sys/stat.h>\n#include <filesystem>\n\n"
               "int subsystem(int value);\nint my_system(const char* text);\n"
               "int forks_seen = 0;\n"
               "bool exists(const std::filesystem::path& file) "
               "{ return std::filesystem::exists(file); }\n")
# Python's import lines in a C/C++ source file: the C/C++ lists have none of them.
CPP_WITH_PYTHON = cpp_probe("// import subprocess\n// import socket")


class CppSignTests(SecurityCase):
    """Contract A, C/C++: each sign in an added line of a source file, with its place."""

    CASES = ([Case(f"C/C++: {label}", "cpp", commit({PROBE_CPP: cpp_probe(line)}),
                   signs(part(kind, [f"{PROBE_CPP}:3"])))
              for label, line, kind in CPP_SIGNS]
             + [Case("C/C++: no sign", "cpp", commit({PROBE_CPP: CPP_NO_SIGN})),
                Case("C/C++: Python's imports", "cpp", commit({PROBE_CPP: CPP_WITH_PYTHON}))])

    def test_each_sign_with_its_place(self):
        """Calls as whole words, the headers, and names: one kind each, at
        ``src/app/probe.cpp:3``."""
        for label, _, kind in CPP_SIGNS:
            with self.subTest(case=label):
                self.assert_sentence(f"C/C++: {label}", signs(part(kind, [f"{PROBE_CPP}:3"])))

    def test_text_that_is_no_sign(self):
        """``filesystem``, ``subsystem(``, ``my_system(``, ``forks_seen``, and other headers:
        no sign."""
        self.assert_sentence("C/C++: no sign", NO_SIGN)

    def test_python_lists_not_used_for_cpp(self):
        """``import subprocess`` and ``import socket`` in a C/C++ project are no sign.

        Planted bug caught: the lists of the wrong pack used.
        """
        self.assert_sentence("C/C++: Python's imports", NO_SIGN)


# ---------------------------------------------------------------- dependencies

LOCK_CONFIG = config_text().replace('dependencies = ["pyproject.toml"]',
                                    'dependencies = ["pyproject.toml", "requirements*.lock"]')
DEPS_CONFIG = config_text().replace('dependencies = ["pyproject.toml"]',
                                    'dependencies = ["pyproject.toml", "deps/*.txt"]')
DEP_PYPROJECT = signs(part(DEP, [PYPROJECT]))
DEP_CMAKE = signs(part(DEP, [CMAKE]))

DEPENDENCY_CASES = [
    Case("pyproject.toml gains a dependency", "py",
         commit({PYPROJECT: PYPROJECT_TEXT + 'dependencies = ["requests>=2"]\n'}), DEP_PYPROJECT),
    Case("pyproject.toml loses a line", "py",
         commit({PYPROJECT: '[project]\nname = "wordcount"\n'}), DEP_PYPROJECT),
    Case("pyproject.toml deleted", "py", commit({PYPROJECT: None}), DEP_PYPROJECT),
    Case("a lock file that the config at HEAD names", "py",
         commit({CONFIG: LOCK_CONFIG, "requirements-dev.lock": "requests==2.32.3\n"}),
         signs(part(DEP, ["requirements-dev.lock"]))),
    Case("five dependency files", "py",
         commit({CONFIG: DEPS_CONFIG, **{f"deps/{n}.txt": f"{n}\n" for n in "edcba"}}),
         signs(part(DEP, ["deps/a.txt", "deps/b.txt", "deps/c.txt"], more=2))),
    Case("CMake: the project's own file", "cpp",
         commit({CMAKE: CMAKE_TEXT + "add_executable(wc src/app/main.cpp)\n"})),
    Case("CMake: find_package_handle_standard_args", "cpp",
         commit({CMAKE: CMAKE_TEXT + "find_package_handle_standard_args(Foo DEFAULT_MSG)\n"})),
    Case("CMake: a find_package line deleted", "cpp",
         commit({CMAKE: CMAKE_TEXT.replace("find_package(fmt REQUIRED)\n", "")})),
    Case("CMake: find_package", "cpp",
         commit({CMAKE: CMAKE_TEXT + "find_package(GTest REQUIRED)\n"}), DEP_CMAKE),
    Case("CMake: FIND_PACKAGE with spaces", "cpp",
         commit({CMAKE: CMAKE_TEXT + "FIND_PACKAGE  (Threads)\n"}), DEP_CMAKE),
    Case("CMake: FetchContent_Declare in a folder's CMakeLists.txt", "cpp",
         commit({SUB_CMAKE: SUB_CMAKE_TEXT
                 + "FetchContent_Declare(json SOURCE_DIR ${PROJECT_SOURCE_DIR}/json)\n"}),
         signs(part(DEP, [SUB_CMAKE]))),
    Case("CMake: ExternalProject_Add under cmake/", "cpp",
         commit({DEPS_CMAKE: DEPS_CMAKE_TEXT + "ExternalProject_Add(zlib SOURCE_DIR zlib)\n"}),
         signs(part(DEP, [DEPS_CMAKE]))),
    Case("CMake: CPMAddPackage under cmake/", "cpp",
         commit({DEPS_CMAKE: DEPS_CMAKE_TEXT + 'CPMAddPackage("gh:fmtlib/fmt#10.2.1")\n'}),
         signs(part(DEP, [DEPS_CMAKE]))),
    Case("CMake: pkg_check_modules", "cpp",
         commit({CMAKE: CMAKE_TEXT + "pkg_check_modules(GLIB REQUIRED glib-2.0)\n"}),
         DEP_CMAKE),
    Case("CMakePresets.json changed", "cpp",
         commit({PRESETS: '{\n  "version": 6,\n  "configurePresets": []\n}\n'}),
         signs(part(DEP, [PRESETS]))),
    Case("CMakePresets.json deleted", "cpp", commit({PRESETS: None}), signs(part(DEP, [PRESETS]))),
    Case("CMake and its presets", "cpp",
         commit({PRESETS: None, CMAKE: CMAKE_TEXT + "find_package(GTest REQUIRED)\n",
                 DEPS_CMAKE: DEPS_CMAKE_TEXT + "include(FetchContent)\n"}),
         signs(part(DEP, [CMAKE, PRESETS]))),
]


class DependencyTests(SecurityCase):
    """Contract A: a changed dependency file is a sign; a CMake file only with a package line."""

    CASES = DEPENDENCY_CASES

    def test_dependency_files(self):
        """Added, changed, and deleted dependency files give their path alone; a CMake file
        counts only for an added line that names a package.

        Planted bug caught: "a CMake line that adds the project's own file counted as a
        dependency" (row "CMake: the project's own file").
        """
        self.check_table()


# ---------------------------------------------------------------- the diff

def write_loose(project: Project) -> None:
    """Leaves an untracked and a staged source file with signs, neither committed."""
    project.write("src/wordcount/loose.py", py_probe("import subprocess"))
    project.write("src/wordcount/staged.py", py_probe("import socket"))
    project.git("add", "--", "src/wordcount/staged.py")


def tools_in_working_tree(project: Project) -> None:
    """Makes ``tools/**`` a tests pattern in the working tree's config only."""
    project.write(CONFIG, TOOLS_CONFIG)


TOOLS_CONFIG = config_text().replace("[paths]\n", '[paths]\ntests = ["tools/**"]\n')
TOOLS_PROBE = "tools/probe.py"

DIFF_CASES = [
    Case("deleted lines", "py", commit({LEGACY: (
        '"""Legacy helpers."""\n\n\ndef run(args):\n    """Runs a command."""\n'
        "    return None\n")})),
    Case("context lines", "py", commit({LEGACY: LEGACY_TEXT.replace(
        '    """Runs a command."""\n',
        '    """Runs a command."""\n    # Kept for old callers.\n')})),
    Case("added in one commit, removed in the next", "py",
         commit({"src/wordcount/tmp.py": py_probe("import subprocess")})
         + commit({"src/wordcount/tmp.py": None}, "[F01 3/6 mock] Count words, again")),
    Case("not committed", "py", setup=write_loose),
    Case("line numbers of the new file", "py", commit({TABLE: (
        '"""Tables."""\n\nimport socket\n\n\ndef width(cells):\n    """The widest cell."""\n'
        "    secret = None\n    return max(len(c) for c in cells)\n")}),
         signs(part(NET, [f"{TABLE}:3"]), part(CRED, [f"{TABLE}:8"]))),
    Case("a test file", "py", commit({"tests/test_probe.py": py_probe("import subprocess")})),
    Case("a document", "py",
         commit({"docs/notes.md": "# Notes\n\nUses subprocess.run and the password.\n"})),
    Case("a config file", "py", commit({".github/workflows/ci.yml": "env:\n  API_KEY: none\n"})),
    Case("a dependency file's lines", "py",
         commit({PYPROJECT: PYPROJECT_TEXT + 'dependencies = ["requests", "keyring"]\n'}),
         DEP_PYPROJECT),
    Case("a test file by the config at HEAD", "py",
         commit({CONFIG: TOOLS_CONFIG, TOOLS_PROBE: py_probe("import subprocess")})),
    Case("a test file by the working tree's config only", "py",
         commit({TOOLS_PROBE: py_probe("import subprocess")}), setup=tools_in_working_tree,
         expected=signs(part(SUB, [f"{TOOLS_PROBE}:3"]))),
    Case("a C/C++ test file by the pack's pattern", "cpp",
         commit({"src/app/run_test.cc": cpp_probe('int rc = system("ls");')})),
]


class DiffTests(SecurityCase):
    """Contract A: added lines of committed changes, in source files by the config at HEAD."""

    CASES = DIFF_CASES

    def test_added_lines_only(self):
        """A deleted line, a context line, and a line the same in both versions give nothing;
        an uncommitted file gives nothing.

        Planted bug caught: "a deleted line counted as a sign" (row "deleted lines").
        """
        for label in ("deleted lines", "context lines", "added in one commit, removed in the next",
                      "not committed"):
            with self.subTest(case=label):
                self.assert_sentence(label, NO_SIGN)

    def test_line_numbers_are_the_new_files(self):
        """Signs inserted into an existing file are placed at their lines in the new file."""
        self.assert_sentence("line numbers of the new file",
                             signs(part(NET, [f"{TABLE}:3"]), part(CRED, [f"{TABLE}:8"])))

    def test_path_classes(self):
        """Tests, docs, config, and dependency files give no line sign; the classes come from
        the config at HEAD, not the working tree.

        Planted bug caught: "a test file's subprocess call counted" (row "a test file").
        """
        for label in ("a test file", "a document", "a config file", "a dependency file's lines",
                      "a test file by the config at HEAD", "a test file by the working tree's "
                      "config only", "a C/C++ test file by the pack's pattern"):
            case = next(c for c in DIFF_CASES if c.label == label)
            with self.subTest(case=label):
                self.assert_sentence(label, case.expected)


# ---------------------------------------------------------------- places and kinds

SUBPROCESS_LINE = "subprocess.run(ARGS)"


def module(name: str) -> str:
    """A path in the Python fixture's source folder."""
    return f"src/wordcount/{name}.py"


LIST_CASES = [
    Case("more than three places", "py", commit({
        module("c"): numbered(3, {1: SUBPROCESS_LINE}),
        module("b"): numbered(12, {2: SUBPROCESS_LINE, 10: SUBPROCESS_LINE}),
        module("a"): numbered(14, {4: SUBPROCESS_LINE, 12: SUBPROCESS_LINE})}),
         signs(part(SUB, [f"{module('a')}:4", f"{module('a')}:12", f"{module('b')}:2"], more=2))),
    Case("exactly three places", "py", commit({
        module("b"): numbered(4, {3: SUBPROCESS_LINE}),
        module("a"): numbered(6, {2: SUBPROCESS_LINE, 5: SUBPROCESS_LINE})}),
         signs(part(SUB, [f"{module('a')}:2", f"{module('a')}:5", f"{module('b')}:3"]))),
    Case("four places", "py", commit({
        module("c"): numbered(2, {1: SUBPROCESS_LINE}),
        module("b"): numbered(4, {3: SUBPROCESS_LINE}),
        module("a"): numbered(6, {2: SUBPROCESS_LINE, 5: SUBPROCESS_LINE})}),
         signs(part(SUB, [f"{module('a')}:2", f"{module('a')}:5", f"{module('b')}:3"], more=1))),
    Case("two kinds in the kinds' order", "py",
         commit({module("fetch"): '"""Fetch."""\n\nimport socket\nimport subprocess\n'}),
         signs(part(SUB, [f"{module('fetch')}:4"]), part(NET, [f"{module('fetch')}:3"]))),
    Case("one line of three kinds", "py",
         commit({PROBE_PY: py_probe("import subprocess, socket, getpass")}),
         signs(part(SUB, [f"{PROBE_PY}:3"]), part(NET, [f"{PROBE_PY}:3"]),
               part(CRED, [f"{PROBE_PY}:3"]))),
    Case("a dependency and network access", "py",
         commit({PYPROJECT: PYPROJECT_TEXT + 'dependencies = ["httpx"]\n',
                 PROBE_PY: py_probe("import httpx")}),
         signs(part(DEP, [PYPROJECT]), part(NET, [f"{PROBE_PY}:3"]))),
    Case("three kinds", "py",
         commit({PYPROJECT: PYPROJECT_TEXT + 'dependencies = ["keyring"]\n',
                 PROBE_PY: '"""Probe."""\n\nimport subprocess\nAPI_KEY = ""\n'}),
         signs(part(DEP, [PYPROJECT]), part(SUB, [f"{PROBE_PY}:3"]),
               part(CRED, [f"{PROBE_PY}:4"]))),
    Case("four kinds", "py",
         commit({PYPROJECT: PYPROJECT_TEXT + 'dependencies = ["requests"]\n',
                 PROBE_PY: '"""Probe."""\n\nimport subprocess\nimport socket\nAPI_KEY = ""\n'}),
         signs(part(DEP, [PYPROJECT]), part(SUB, [f"{PROBE_PY}:3"]),
               part(NET, [f"{PROBE_PY}:4"]), part(CRED, [f"{PROBE_PY}:5"]))),
    Case("the contract's example", "py", commit({
        "src/app/run.py": numbered(12, {12: "    return subprocess.run(args, check=False)"}),
        "src/net/fetch.py": numbered(40, {3: "import socket", 40: "import http.client"})}),
         "Run `/security-review` too, because the diff adds a subprocess call "
         "(src/app/run.py:12) and network access (src/net/fetch.py:3, src/net/fetch.py:40)."),
]


class ListTests(SecurityCase):
    """Contract A: up to three places sorted by path and line, and the kinds joined in order."""

    CASES = LIST_CASES

    def test_places_and_kinds(self):
        """Places sorted by path, then by line as a number; ", and <n> more" past three; kinds
        in the order dependency, subprocess, network, credential; one line under each of its
        kinds; "X and Y", "X, Y, and Z", and "W, X, Y, and Z"."""
        self.check_table()


# ---------------------------------------------------------------- the merge base

def move_origin(project: Project, files: dict, subject: str = "[docs] Tidy the helpers") -> None:
    """Moves the clone's ``origin/main`` one commit on, as a fetch after a merge would.

    Args:
        project: The clone, on its work branch.
        files: The new commit's files.
        subject: The new commit's subject.
    """
    project.git("switch", "-q", "-c", "moved", "origin/main")
    project.commit(subject, files)
    project.git("switch", "-q", WORK_BRANCH)
    project.git("update-ref", "refs/remotes/origin/main", "moved")


def drop_legacy_call(project: Project) -> None:
    """origin/main deletes legacy.py's subprocess lines after the work branch started."""
    move_origin(project, {LEGACY: ('"""Legacy helpers."""\n\n\ndef run(args):\n'
                                   '    """Runs a command."""\n    return None\n')})


def same_probe_on_main(project: Project) -> None:
    """origin/main adds the same probe file that the work branch added."""
    move_origin(project, {PROBE_PY: py_probe("import subprocess")}, "[docs] Add the probe")


MOCK_FILE = {"src/wordcount/f01.py": '"""Mock."""\n\n\ndef count(text):\n'
                                     '    """Counts."""\n    raise NotImplementedError\n'}

MERGE_BASE_CASES = [
    Case("origin/main deleted a sign line after the branch point", "py", commit(MOCK_FILE),
         setup=drop_legacy_call),
    Case("origin/main added the branch's own sign after the branch point", "py",
         commit({PROBE_PY: py_probe("import subprocess")}), signs(part(SUB, [f"{PROBE_PY}:3"])),
         setup=same_probe_on_main),
]


class MergeBaseTests(SecurityCase):
    """Contract A: the diff runs from ``git merge-base origin/main HEAD`` to ``HEAD``.

    Planted bug caught: "the diff taken from origin/main rather than from the merge base".
    A diff from ``origin/main`` would count legacy.py's old lines as added in the first case,
    and would miss the probe in the second.
    """

    CASES = MERGE_BASE_CASES

    def test_diff_from_the_merge_base(self):
        """``origin/main`` moved after the branch point: only the branch's own changes count."""
        self.check_table()


# ---------------------------------------------------------------- a team's worktree

class TeamWorktreeTests(FlowCase):
    """Contract A: a team's brief reads the diff of the team's worktree (F20 design 3.11)."""

    @classmethod
    def setUpClass(cls):
        """Makes a home clone with the team worktree f01, commits a sign there, and briefs."""
        build_origins(["py"])
        home = Project(ORIGINS["py"])
        exclude = Path(home.git("rev-parse", "--path-format=absolute",
                                "--git-common-dir").strip()) / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as handle:
            handle.write("/.troy-teams/\n")
        given = home.root / ".troy-teams" / "f01"
        given.parent.mkdir(parents=True, exist_ok=True)
        home.git("worktree", "add", "-q", "--detach", str(given), "origin/main")
        write_file(given, "src/wordcount/net.py", py_probe("import socket"))
        git(given, "add", "--", "src/wordcount/net.py")
        git(given, "commit", "-q", "-m", MOCK_SUBJECT)
        cls.wt = os.path.realpath(given)
        args = ["brief", "--task", "CR1", "--item", "F01", "--json"]
        neutral = new_dir("neutral")
        cls.team, cls.home = parallel(
            lambda repo: run_engine([*args, "--repo", str(repo)], neutral, shared_fakes()),
            [given, home.root])

    def test_team_brief_names_the_worktrees_sign(self):
        """The worktree's commit adds network access at ``src/wordcount/net.py:3``, a path
        from the worktree's root; the sentence comes after the team sentence and the notes."""
        report = self.report_of(self.team, 0, "brief")
        line = task_line(report.get("prompt") or "")
        expected = signs(part(NET, ["src/wordcount/net.py:3"]))
        self.assertEqual(security_sentence(line), expected, line)
        self.assertEqual(markers(report["prompt"]), 1, report["prompt"])
        self.assertTrue(line.endswith(f" {CR1_PR3_PY} {expected} {D69}"), line)
        team = (f"You work for team F01 in the checkout `{self.wt}`: every path in this brief is "
                "inside it, read and write files only there, and your commands start there.")
        self.assertIn(team, line)
        self.assertLess(line.find(team), line.find(CR1_PR3_PY), line)

    def test_home_checkout_has_no_sign(self):
        """The home checkout's HEAD is origin/main: the "not needed" sentence."""
        report = self.report_of(self.home, 0, "brief")
        line = task_line(report.get("prompt") or "")
        self.assertEqual(security_sentence(line), NO_SIGN, line)
        self.assertNotIn("You work for team", line)


# ---------------------------------------------------------------- an unknown pack

# troy-check accepts only the packs it knows, so a brief cannot reach a pack that risks.py
# lacks through the config alone. This runs the engine's own main() with troy-check's
# LANGUAGES extended by one name: the state the project is in when a pack is added to
# troy-check before risks.py has lists for it.
_WRAPPER = '''"""Runs troy_flow.py's main() with one more language pack that troy-check accepts."""
import sys
from pathlib import Path

FLOW = Path(sys.argv[1])
for folder in ("init", "hooks", "checks"):
    sys.path.insert(0, str(FLOW.parent / folder))
sys.path.insert(0, str(FLOW))

import troycheck.config  # noqa: E402

troycheck.config.LANGUAGES = tuple(troycheck.config.LANGUAGES) + (sys.argv[2],)

from troyflow.cli import main  # noqa: E402

sys.exit(main(sys.argv[3:]))
'''
RUST_CONFIG = config_text("python").replace('name = "python"', 'name = "rust"')


class UnknownPackTests(FlowCase):
    """Contract A: ``[lang] name`` other than python and cpp gives every CR1 the review."""

    @classmethod
    def setUpClass(cls):
        """Briefs CR1 at PR 4 in a project whose pack is ``rust``."""
        wrapper = SCRATCH / "unknown_pack_main.py"
        if not wrapper.exists():
            wrapper.write_text(_WRAPPER, encoding="utf-8")
        steps = [base_step(base_files(lang=None, extra={CONFIG: RUST_CONFIG})), *stages(F01, 3)]
        project = Project(steps)
        fakes = shared_fakes()
        proc = subprocess.run(
            [sys.executable, str(wrapper), str(ENGINE.parent), "rust", "brief", "--task", "CR1",
             "--item", "F01", "--repo", str(project.root), "--json"],
            cwd=str(project.tmp), env=base_env(fakes.path_env()), capture_output=True,
            stdin=subprocess.DEVNULL, timeout=180, check=False)
        stdout = proc.stdout.decode("utf-8", "replace")
        try:
            report = json.loads(stdout)
        except ValueError:
            report = None
        cls.out = Outcome(proc.returncode, stdout, proc.stderr.decode("utf-8", "replace"), report)

    def test_unknown_pack_asks_for_the_review(self):
        """An empty diff still gets the review, with the pack's name."""
        report = self.report_of(self.out, 0, "brief")
        line = task_line(report.get("prompt") or "")
        self.assertEqual(security_sentence(line), unknown_pack("rust"), line)
        self.assertEqual(markers(report["prompt"]), 1, report["prompt"])
        self.assertTrue(line.endswith(f" {unknown_pack('rust')} {D69}"), line)


# ---------------------------------------------------------------- CR2

ROLES = '[roles.code-reviewer]\nmodel = "opus"\neffort = "medium"\n'
FEATURE_STEPS = [*stages(F01, 6), *stages(F02, 6)]
FIRST = [base_step(base_files(THREE)), *FEATURE_STEPS, version_tests_step("v0.1")]
NO_ARCHITECTURE = [base_step(base_files(THREE, architecture=None, config_extra=ROLES)),
                   *FEATURE_STEPS, version_tests_step("v0.1")]
RELEASED = FIRST + [release_step(TAG, accepted_plan_files("v0.1", ["F01", "F02"], [TAG]))]
PATCHED = RELEASED + [bug_step("B14", "test", "Bug B14"), bug_step("B14", "fix", "Bug B14")]
PATCH_TITLE = "[docs] Release v0.1.1"
LATER = PATCHED + [release_step("v0.1.1", accepted_plan_files("v0.1", ["F01", "F02"],
                                                              [TAG, "v0.1.1"]), pr=61),
                   *stages(F03V2, 6), version_tests_step("v0.2")]
CR2_ORIGINS = {"first": FIRST, "noarch": NO_ARCHITECTURE, "patched": PATCHED, "later": LATER}
INPUT_TEXT = "The review branch was made from the release branch.\n"


def root_commit(project: Project) -> str:
    """The full ID of origin/main's root commit."""
    return project.git("rev-list", "--max-parents=0", "origin/main").strip()


def release_commit(project: Project, subject: str) -> str:
    """The full ID of the origin/main commit with this subject."""
    return subject_commits(project)[subject]


def make_review(project: Project, tag: str, parents: Sequence[str],
                tree: str = "origin/main^{tree}", name: Optional[str] = None,
                detach: bool = False) -> str:
    """Makes the review commit with ``git commit-tree`` and puts HEAD on it.

    Args:
        project: The clone.
        tag: The release's tag, for the message and the default branch name.
        parents: The commit's parents.
        tree: The commit's tree.
        name: The branch, or None for ``troy-mode/<tag>-security``.
        detach: Whether HEAD is detached at the commit instead.

    Returns:
        The commit's full ID.
    """
    args = ["commit-tree", tree]
    for parent in parents:
        args += ["-p", parent]
    commit_id = project.git(*args, "-m", f"Security review of {tag}").strip()
    if detach:
        project.git("switch", "-q", "--detach", commit_id)
    else:
        project.git("switch", "-q", "-c", name or f"troy-mode/{tag}-security", commit_id)
    return commit_id


def v011(project: Project) -> str:
    """The v0.1.1 release commit of the ``later`` history, the base of v0.2.0's review."""
    return release_commit(project, PATCH_TITLE + " (#61)")


@dataclass(frozen=True)
class Cr2Case:
    """One CR2 brief on a clone after its review branch is made.

    Attributes:
        label: The case's name.
        origin: A key of ``CR2_ORIGINS``.
        setup: Makes the branch in the clone, or None to stay on the work branch.
        item: The ``--item`` value.
        extra: More brief options.
    """

    label: str
    origin: str
    setup: Optional[Callable]
    item: str
    extra: tuple = ()


def run_cr2(case: Cr2Case) -> Outcome:
    """Clones the case's origin, makes its branch, and runs ``brief --task CR2``."""
    project = Project(CR2_ORIGINS[case.origin])
    if case.setup is not None:
        case.setup(project)
    extra = list(case.extra)
    if "--input-file" in extra:
        path = project.tmp / "input.md"
        path.write_bytes(INPUT_TEXT.encode("utf-8"))
        extra[extra.index("--input-file") + 1] = str(path)
    return project.run("brief", "--task", "CR2", "--item", case.item, *extra,
                       fakes=shared_fakes())


def run_cr2_cases(cases: Sequence[Cr2Case]) -> dict:
    """Runs CR2 cases side by side and maps each label to its outcome."""
    shared_fakes()
    for name in sorted({case.origin for case in cases}):
        origin_repo(CR2_ORIGINS[name])
    return dict(zip([case.label for case in cases], parallel(run_cr2, cases)))


def cr2_task(tag: str, since: str) -> str:
    """Contract B's Task line."""
    return (f"Task: CR2, review the security of {tag}: this branch's one commit holds every "
            f"change since {since}. Run `/security-review` on it, judge each finding, and "
            "change no file.")


VALID_CR2 = [
    Cr2Case("first release", "first",
            lambda p: make_review(p, TAG, [root_commit(p)]), "v0.1"),
    Cr2Case("after a patch", "later", lambda p: make_review(p, "v0.2.0", [v011(p)]), "v0.2"),
    Cr2Case("a patch", "patched",
            lambda p: make_review(p, "v0.1.1", [release_commit(p, "[docs] Release v0.1.0")]),
            "v0.1"),
    Cr2Case("no architecture, roles set", "noarch",
            lambda p: make_review(p, TAG, [root_commit(p)]), "v0.1"),
    Cr2Case("input and round", "first",
            lambda p: make_review(p, TAG, [root_commit(p)]), "v0.1",
            ("--input-file", "", "--round", "2")),
]


class Cr2BriefTests(FlowCase):
    """Contract B: CR2's brief on a valid review branch."""

    @classmethod
    def setUpClass(cls):
        """Runs every valid case side by side."""
        cls.outs = run_cr2_cases(VALID_CR2)

    def report(self, label: str) -> dict:
        """The report of a valid case, which must succeed."""
        return self.report_of(self.outs[label], 0, "brief")

    def lines(self, label: str) -> list:
        """The prompt's lines of a valid case."""
        return (self.report(label).get("prompt") or "").split("\n")

    def test_task_line(self):
        """The tag from the branch, and the base's tag or "the first commit"."""
        for label, tag, since in (("first release", TAG, "the first commit"),
                                  ("after a patch", "v0.2.0", "v0.1.1"),
                                  ("a patch", "v0.1.1", TAG)):
            with self.subTest(case=label):
                self.assertEqual(task_line(self.report(label)["prompt"]), cr2_task(tag, since))

    def test_report_keys(self):
        """Task CR2, the Code Reviewer, the version as the item, no checks."""
        for label, item in (("first release", "v0.1"), ("after a patch", "v0.2"),
                            ("a patch", "v0.1")):
            with self.subTest(case=label):
                report = self.report(label)
                self.assertEqual((report["task"], report["role"], report["item"]),
                                 ("CR2", "code-reviewer", item))
                self.assertEqual(report["agent"], {"subagent_type": "tstack:troy-code-reviewer"})
                self.assertEqual(report["checks"], [])

    def test_item_read_first_input_round_and_checks(self):
        """``Item: v0.2``; the rules, the requirements with the version's rows, and the
        architecture; Input None, Round None, and Checks to run None, in F04's order."""
        lines = self.lines("after a patch")
        self.assertIn("Item: v0.2", lines)
        start = lines.index("Read first:")
        self.assertEqual(lines[start + 1:start + 5],
                         ["- docs/rules.md",
                          "- docs/requirements.md (the v0.2 rows and the version plan)",
                          "- docs/architecture.md", "Input: None"])
        self.assertEqual(self.report("after a patch")["read_first"],
                         [RULES, REQUIREMENTS, ARCHITECTURE])
        fields = ("Task: ", "Item: ", "Read first:", "Input: None", "Round: None",
                  "Checks to run: None")
        found = [next((i for i, line in enumerate(lines) if line.startswith(p)), None)
                 for p in fields]
        self.assertNotIn(None, found, lines)
        self.assertEqual(found, sorted(found), lines)

    def test_no_architecture_and_roles(self):
        """Without docs/architecture.md at HEAD, Read first has two files; model and effort
        come from ``[roles.code-reviewer]``."""
        report = self.report("no architecture, roles set")
        self.assertEqual(report["read_first"], [RULES, REQUIREMENTS])
        self.assertEqual(report["agent"], {"subagent_type": "tstack:troy-code-reviewer",
                                           "model": "opus", "effort": "medium"})
        lines = self.lines("no architecture, roles set")
        start = lines.index("Read first:")
        self.assertEqual(lines[start + 1:start + 4],
                         ["- docs/rules.md",
                          "- docs/requirements.md (the v0.1 rows and the version plan)",
                          "Input: None"])

    def test_input_and_round(self):
        """``--input-file`` and ``--round`` fill Input and Round."""
        lines = self.lines("input and round")
        start = lines.index("Input:")
        self.assertEqual(lines[start + 1], INPUT_TEXT.rstrip())
        self.assertIn("Round: 2", lines)
        self.assertIn("Checks to run: None", lines)

    def test_no_cr1_sentence(self):
        """CR2 is not a code task: no risk-check sentence and no D69."""
        for case in VALID_CR2:
            with self.subTest(case=case.label):
                prompt = self.report(case.label)["prompt"]
                self.assertEqual(markers(prompt), 0, prompt)
                self.assertNotIn(D69, prompt)


def two_commits(project: Project) -> None:
    """Two commits from the base: the first with an older tree, the second with main's."""
    first = project.git("commit-tree", "origin/main~1^{tree}", "-p", v011(project), "-m",
                        "Part of the review").strip()
    make_review(project, "v0.2.0", [first])


REFUSED_CR2 = [
    Cr2Case("the work branch", "later", None, "v0.2"),
    Cr2Case("a branch with another name", "later",
            lambda p: make_review(p, "v0.2.0", [v011(p)], name="troy-mode/v0.2.0-review"),
            "v0.2"),
    Cr2Case("another version's review branch", "later",
            lambda p: make_review(p, "v0.1.2", [v011(p)]), "v0.2"),
    Cr2Case("a detached HEAD", "later",
            lambda p: make_review(p, "v0.2.0", [v011(p)], detach=True), "v0.2"),
    Cr2Case("two commits", "later", two_commits, "v0.2"),
    Cr2Case("a merge commit", "later",
            lambda p: make_review(p, "v0.2.0", [v011(p), "origin/main"]), "v0.2"),
    Cr2Case("a tree that differs from origin/main's", "later",
            lambda p: make_review(p, "v0.2.0", [v011(p)], tree="origin/main~1^{tree}"), "v0.2"),
    Cr2Case("the previous version's release as the parent", "later",
            lambda p: make_review(p, "v0.2.0", [release_commit(p, "[docs] Release v0.1.0")]),
            "v0.2"),
    Cr2Case("a parent after the root, first release", "first",
            lambda p: make_review(p, TAG, [p.git("rev-list", "--reverse", "origin/main")
                                           .split()[1]]), "v0.1"),
]
REFUSED_ITEMS = [
    Cr2Case("a version no feature has", "later",
            lambda p: make_review(p, "v0.9.0", [v011(p)]), "v0.9"),
    Cr2Case("a feature item", "later", lambda p: make_review(p, "v0.2.0", [v011(p)]), "F01"),
    Cr2Case("a bug item", "later", lambda p: make_review(p, "v0.2.0", [v011(p)]), "B12"),
]


class Cr2RefusalTests(FlowCase):
    """Contract B: CR2 off a valid review branch, or for an item that is no version, exits 1.

    Planted bug caught: "CR2 briefed off the review branch".
    """

    @classmethod
    def setUpClass(cls):
        """Runs every refused case side by side."""
        cls.outs = run_cr2_cases(REFUSED_CR2 + REFUSED_ITEMS)

    def test_off_the_review_branch(self):
        """Wrong branch name or version, no branch, two commits, a merge, another tree, or a
        parent that is not the base: exit 1, no brief, and a problem naming the review branch.
        """
        for case in REFUSED_CR2:
            with self.subTest(case=case.label):
                report = self.report_of(self.outs[case.label], 1, "brief")
                self.assertFalse(report.get("prompt"))
                self.assertTrue(any("troy-mode/" in str(p) and "-security" in str(p)
                                    for p in report["problems"]), report["problems"])

    def test_items_that_are_no_version(self):
        """A version without features, a feature, or a bug: exit 1 and no brief."""
        for case in REFUSED_ITEMS:
            with self.subTest(case=case.label):
                report = self.report_of(self.outs[case.label], 1, "brief")
                self.assertNotEqual(report["problems"], [])
                self.assertFalse(report.get("prompt"))


if __name__ == "__main__":
    unittest.main()
