"""Shared fixtures for the F16 role exam tests (F16 design 14.1).

The tests come from the design and the build's API contract, written before
the code. This module puts the engine's folders on ``sys.path`` as
``troy_exam.py`` does, isolates git from the machine's settings, and builds
the fixtures the groups share: small git repositories, case folders, role
transcripts, fake ``env_run`` functions, JUnit files, a fake tstack checkout,
and the stand-in CLI's scenarios. Nothing here imports ``troyexam`` at import
time; the few helpers that need its classes import them when called.

No helper calls a model or the network. Every folder lives under one scratch
folder in the system temp folder, removed at exit, and no path it makes holds
an exam word (design 6.1), so the runner's blinding check never refuses a
fixture for a reason of the test's own making.
"""

from __future__ import annotations

import atexit
import itertools
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence, Union

TESTS = Path(__file__).resolve().parent
EXAM = TESTS.parent
TROY_MODE = EXAM.parent
REPO = TROY_MODE.parent
EXAM_SCRIPT = EXAM / "troy_exam.py"
CASES_DIR = EXAM / "cases"
AGENTS = REPO / "agents"
FLOW_TESTS = TROY_MODE / "flow" / "tests"
STANDIN = TESTS / "standin_cli.py"

# The folders troy_exam.py puts on sys.path (contract, "Layout"), so the tests
# import troyexam, troyflow, troycheck, troyhook, and troyinit as it does.
for _folder in (TROY_MODE / "init", TROY_MODE / "hooks", TROY_MODE / "checks",
                TROY_MODE / "flow", EXAM):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))
# flow_helpers builds troy-mode projects; appended so this folder's modules win.
if str(FLOW_TESTS) not in sys.path:
    sys.path.append(str(FLOW_TESTS))

NAME = "Test Author"
EMAIL = "test@example.com"
START_NAME = "wordcount"           # the start repository's folder, so its project's name
CLI_VERSION = "2.1.325"            # what the stand-in CLI prints for --version
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-5-20250929"
OPUS = "claude-opus-4-1-20250805"
PASS_MARKER = "kept tidy"          # the stand-in judge passes a report that holds it

# Design 6.1's words, kept here apart from the code's own list, so a test can
# check the code's output with a list the code did not write.
EXAM_WORDS = ("eval", "exam", "trap", "judge", "rubric", "grade", "score", "compare",
              "experiment", "candidate", "variant", "arena", "baseline", "hillclimb", "sandbox")
_ENDINGS = ("", "s", "es", "d", "ed", "r", "rs", "er", "ers", "ing")

# The case checks of design 4.3, by name.
DESIGN_CHECKS = ("pack_steps_pass", "ruff_format_blocks", "mock_bodies_only_raise",
                 "no_mock_notes_left", "tests_fail_on_mock", "tests_pass_on_pilot",
                 "tests_fail_on_mutants", "result_is", "changed_only")
ROLE_PREFIX = {"architect": "AR", "interface-designer": "IF", "test-manager": "TM",
               "developer": "DV", "test-engineer": "TE", "code-reviewer": "CR"}

_DROPPED_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                "GIT_COMMON_DIR", "GIT_CEILING_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_COUNT",
                "GIT_CONFIG_PARAMETERS", "TROY_EXAM_ROOT", "TROY_EXAM_CLI", "TROY_MODE_ENV_PREFIX",
                "CLAUDE_CONFIG_DIR", "CLAUDE_PLUGIN_ROOT", "PYTHONIOENCODING", "PYTHONUTF8",
                "GH_TOKEN", "GITHUB_TOKEN", "GH_HOST", "GH_REPO", "GITHUB_EVENT_PATH")


def word_hits(text: str) -> list:
    """The exam words a text holds, by design 6.1 and the contract's token rule.

    Tokens are runs of letters, split again where a lower-case letter meets an
    upper-case one. A token holds a word when it is the word, or the word plus
    one ending (s, es, d, ed, r, rs, er, ers, ing), or the word with its final
    e dropped and ing added.

    Args:
        text: Any text.

    Returns:
        The words found, in design order, each once.
    """
    tokens = set()
    for run in re.findall(r"[A-Za-z]+", text):
        for part in re.sub(r"([a-z])([A-Z])", r"\1 \2", run).split():
            tokens.add(part.lower())
    found = []
    for word in EXAM_WORDS:
        forms = {word + ending for ending in _ENDINGS}
        if word.endswith("e"):
            forms.add(word[:-1] + "ing")
        if tokens & forms:
            found.append(word)
    return found


def _remove_tree(path: Path) -> None:
    """Deletes a folder, making read-only files (git objects on Windows) writable first."""
    if not path.exists():
        return
    for folder, dirs, files in os.walk(path):
        for name in dirs + files:
            try:
                os.chmod(os.path.join(folder, name), stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            except OSError:
                continue
    shutil.rmtree(path, ignore_errors=True)


SCRATCH = Path(tempfile.mkdtemp(prefix="tsx-"))
atexit.register(_remove_tree, SCRATCH)
if word_hits(str(SCRATCH)):
    raise RuntimeError(f"the temp folder {SCRATCH} holds an exam word {word_hits(str(SCRATCH))}; "
                       "set TMP or TEMP to another folder to run these tests")
_COUNTER = itertools.count(1)

_GLOBAL_CONFIG = SCRATCH / "gitconfig"
_GLOBAL_CONFIG.write_text(f"[user]\n\tname = {NAME}\n\temail = {EMAIL}\n"
                          "[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n"
                          "[init]\n\tdefaultBranch = main\n", encoding="utf-8")
for _name in _DROPPED_ENV:
    os.environ.pop(_name, None)
os.environ.update({"GIT_CONFIG_GLOBAL": str(_GLOBAL_CONFIG), "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_TERMINAL_PROMPT": "0", "PYTHONDONTWRITEBYTECODE": "1"})


# ------------------------------------------------------------------ basics

def new_dir(prefix: str) -> Path:
    """Creates a new empty folder in the scratch folder.

    Args:
        prefix: The start of the folder's name; it must hold no exam word.

    Returns:
        The new folder.
    """
    assert not word_hits(prefix), prefix
    path = SCRATCH / f"{prefix}{next(_COUNTER)}"
    path.mkdir(parents=True)
    return path


def write_file(root: Path, rel: str, content: Union[str, bytes]) -> Path:
    """Writes a file with the exact bytes given, creating its folders.

    Args:
        root: The folder the path is relative to.
        rel: The path, with ``/``.
        content: Text, written as UTF-8 without newline translation, or bytes.

    Returns:
        The file's path.
    """
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return path


def crlf(text: str) -> bytes:
    """Encodes text as UTF-8 with CRLF line ends."""
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


def git_proc(cwd: Path, *args: str, input_bytes: Optional[bytes] = None
             ) -> subprocess.CompletedProcess:
    """Runs git with the tests' own identity and returns the finished process.

    Args:
        cwd: The folder to run in.
        *args: The arguments after ``git``.
        input_bytes: Bytes for standard input, or None.

    Returns:
        The finished process, with text output.
    """
    proc = subprocess.run(["git", "-c", f"user.name={NAME}", "-c", f"user.email={EMAIL}",
                           *[str(a) for a in args]], cwd=str(cwd), capture_output=True,
                          input=input_bytes,
                          stdin=None if input_bytes is not None else subprocess.DEVNULL,
                          check=False)
    return subprocess.CompletedProcess(proc.args, proc.returncode,
                                       proc.stdout.decode("utf-8", "replace"),
                                       proc.stderr.decode("utf-8", "replace"))


def git(cwd: Path, *args: str, input_bytes: Optional[bytes] = None) -> str:
    """Runs git, raises when it fails, and returns its standard output.

    Raises:
        RuntimeError: git exited with a code other than 0.
    """
    proc = git_proc(cwd, *args, input_bytes=input_bytes)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(map(str, args))} failed in {cwd}: {proc.stderr}")
    return proc.stdout


def commit_files(repo: Path, files: Mapping[str, Union[str, bytes, None]], message: str,
                 executable: Sequence[str] = ()) -> str:
    """Writes files, commits them on the current branch, and returns the commit's ID.

    Args:
        repo: The repository.
        files: Paths mapped to content; None deletes the path.
        message: The commit message.
        executable: Paths to commit with mode 100755.

    Returns:
        The new commit's full ID.
    """
    for rel, content in files.items():
        if content is None:
            git(repo, "rm", "-q", "--", rel)
        else:
            write_file(repo, rel, content)
            git(repo, "add", "--", rel)
    for rel in executable:
        git(repo, "update-index", "--chmod=+x", "--", rel)
    git(repo, "commit", "-q", "--no-verify", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


def make_repo(folder: Path, files: Mapping[str, Union[str, bytes]], message: str = "Start",
              executable: Sequence[str] = ()) -> str:
    """Creates a repository on ``main`` with one commit of the files.

    Args:
        folder: The repository's folder (created).
        files: Paths mapped to content.
        message: The commit message.
        executable: Paths to commit with mode 100755.

    Returns:
        The commit's full ID.
    """
    folder.mkdir(parents=True, exist_ok=True)
    git(folder, "init", "-q", "-b", "main")
    git(folder, "config", "core.autocrlf", "false")
    return commit_files(folder, files, message, executable)


def rev_list_all(repo: Path, bare: bool = False) -> set:
    """Every commit reachable from any ref of a repository."""
    args = ("--git-dir", str(repo)) if bare else ()
    return set(git(repo if not bare else repo.parent, *args, "rev-list", "--all").split())


def object_exists(repo: Path, sha: str, bare: bool = False) -> bool:
    """Whether a repository can read an object, reachable or not."""
    args = ("--git-dir", str(repo)) if bare else ()
    cwd = repo if not bare else repo.parent
    return git_proc(cwd, *args, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def same_path(first, second) -> bool:
    """Whether two paths name the same place."""
    def norm(path) -> str:
        """Normalizes one path."""
        return os.path.normcase(os.path.realpath(os.path.abspath(str(path))))
    return norm(first) == norm(second)


def lf_text(data: Union[str, bytes]) -> str:
    """Text with CRLF made LF."""
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    return text.replace("\r\n", "\n")


# ---------------------------------------------------------------- case folders

RUBRIC3 = ("# Criteria\n\n"
           "1. Every sentence of each doc comment is true of the body. Pass: each one is. "
           "Fail: one is not.\n"
           "2. Each note stands in its own paragraph. Pass: it does. Fail: it does not.\n"
           "3. The report names every changed file. Pass: it does. Fail: one is missing.\n")


def rubric(count: int) -> str:
    """A rubric with the given number of criteria."""
    return "# Criteria\n\n" + "".join(f"{i}. Criterion {i}. Pass: yes. Fail: no.\n"
                                       for i in range(1, count + 1))


def toml_scalar(value) -> str:
    """One TOML value: a string, number, boolean, or list of scalars."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(toml_scalar(v) for v in value) + "]"
    return json.dumps(str(value))


def toml_text(data: Mapping) -> str:
    """Writes a nested mapping as TOML: scalars, then tables, then arrays of tables.

    Args:
        data: Keys to scalars, lists of scalars, mappings (tables), or lists
            of mappings (arrays of tables).

    Returns:
        The TOML text.
    """
    lines = []
    for key, value in data.items():
        if isinstance(value, Mapping) or (isinstance(value, list) and value
                                          and isinstance(value[0], Mapping)):
            continue
        lines.append(f"{key} = {toml_scalar(value)}")
    for key, value in data.items():
        if isinstance(value, Mapping):
            lines.append(f"\n[{key}]")
            lines += [f"{k} = {toml_scalar(v)}" for k, v in value.items()]
    for key, value in data.items():
        if isinstance(value, list) and value and isinstance(value[0], Mapping):
            for table in value:
                lines.append(f"\n[[{key}]]")
                lines += [f"{k} = {toml_scalar(v)}" for k, v in table.items()]
    return "\n".join(lines) + "\n"


def case_data(case_id: str = "dv-sample", **top) -> dict:
    """The design 4.1 example case as a mapping, with top-level keys replaced.

    Args:
        case_id: The case's ID.
        **top: Top-level keys to set or replace (``start``, ``run``, and
            ``criteria`` replace whole tables).

    Returns:
        The mapping for ``toml_text``.
    """
    data = {"id": case_id, "version": 1, "role": "developer", "task": "DV1", "item": "F05",
            "start": {"repository": "ZJUCao/recipe-menu", "commit": "b966872",
                      "branch": "troy-mode/f05-3-mock",
                      "pilot": ["#36", "#42", "#55", "#57", "#67", "#81", "#88"]},
            "run": {"model": "sonnet", "effort": "high", "minutes": 45, "max_cost": 2.50},
            "criteria": [{"id": "stub-bodies", "check": "mock_bodies_only_raise", "must": True},
                         {"id": "notes-true", "judge": 1, "must": True}]}
    data.update(top)
    return data


ANCHOR_DIFF = ("diff --git a/src/wordcount/f01.py b/src/wordcount/f01.py\nnew file mode 100644\n"
               "--- /dev/null\n+++ b/src/wordcount/f01.py\n@@ -0,0 +1 @@\n+X = 1\n")


def write_case(folder: Path, data: Mapping, rubric_text: Optional[str] = RUBRIC3,
               anchors: bool = True, start_patch: Optional[str] = None,
               mutants: Optional[Mapping[str, str]] = None, input_text: Optional[str] = None,
               anchor_reports: Optional[Mapping[str, str]] = None) -> Path:
    """Writes a case folder (design 4.1).

    Args:
        folder: The case folder (created; its name should be the case's ID).
        data: The case.toml mapping.
        rubric_text: rubric.md, or None for none.
        anchors: Whether to write anchors/fail and anchors/pass.
        start_patch: start.patch's text, or None for none.
        mutants: Names mapped to the text of mutants/<name>.patch.
        input_text: input.md's text, or None for none.
        anchor_reports: "fail" and "pass" mapped to report.md texts.

    Returns:
        The folder.
    """
    folder.mkdir(parents=True, exist_ok=True)
    write_file(folder, "case.toml", toml_text(data))
    if rubric_text is not None:
        write_file(folder, "rubric.md", rubric_text)
    if anchors:
        reports = dict(anchor_reports or {})
        for side in ("fail", "pass"):
            write_file(folder, f"anchors/{side}/diff.patch", ANCHOR_DIFF)
            write_file(folder, f"anchors/{side}/report.md",
                       reports.get(side, f"Role: Developer\nResult: done\nSummary: {side}.\n"))
    if start_patch is not None:
        write_file(folder, "start.patch", start_patch)
    for name, text in (mutants or {}).items():
        write_file(folder, f"mutants/{name}.patch", text)
    if input_text is not None:
        write_file(folder, "input.md", input_text)
    return folder


def rubric_count(text: str) -> int:
    """The number of numbered criteria in a rubric, counted apart from the code."""
    return len(re.findall(r"(?m)^\d+\. ", text))


def agent_tasks(role: str) -> set:
    """The F04 task IDs of a role, read from its agent file's "### XXn" headings."""
    text = (AGENTS / f"troy-{role}.md").read_text(encoding="utf-8")
    return set(re.findall(r"(?m)^### ([A-Z]{2}\d+) ", text))


def agent_text(role: str) -> str:
    """A role's real agent file."""
    return (AGENTS / f"troy-{role}.md").read_text(encoding="utf-8")


def report_template(agent: str) -> list:
    """The Report section's ```text block of an agent file, line by line."""
    lines = agent.replace("\r\n", "\n").split("\n")
    start = lines.index("## Report")
    first = next(i for i in range(start, len(lines)) if lines[i].startswith("```text"))
    end = next(i for i in range(first + 1, len(lines)) if lines[i].startswith("```"))
    return lines[first + 1:end]


def valid_report(agent: str, result: Optional[str] = None, task: str = "DV1, F05") -> str:
    """A report that follows an agent file's Report template, built apart from the code.

    Args:
        agent: The agent file's text.
        result: The Result value, or None for the template's first one.
        task: The Task value.

    Returns:
        The report, one line per field.
    """
    out = []
    for line in report_template(agent):
        name, _, value = line.partition(":")
        value = value.strip()
        if name == "Role":
            out.append(f"Role: {value}")
        elif name == "Result":
            out.append(f"Result: {result or value.split('|')[0].strip()}")
        elif name == "Task":
            out.append(f"Task: {task}")
        else:
            out.append(f"{name}: None")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------- transcripts

def tool_use(name: str, input_: Mapping, use_id: str) -> dict:
    """A tool_use block."""
    return {"type": "tool_use", "id": use_id, "name": name, "input": dict(input_)}


def tool_result(use_id: str, content: str = "ok", is_error: bool = False) -> dict:
    """A tool_result block."""
    return {"type": "tool_result", "tool_use_id": use_id, "content": content,
            "is_error": is_error}


def user_line(content, **extra) -> str:
    """A transcript line of type user."""
    return json.dumps({"type": "user", "isSidechain": True, "uuid": f"u{next(_COUNTER)}",
                       "message": {"role": "user", "content": content}, **extra})


def assistant_line(*blocks: Mapping) -> str:
    """A transcript line of type assistant."""
    return json.dumps({"type": "assistant", "isSidechain": True, "uuid": f"a{next(_COUNTER)}",
                       "message": {"role": "assistant", "model": SONNET,
                                   "content": [dict(b) for b in blocks]}})


def text_block(text: str) -> dict:
    """A text block."""
    return {"type": "text", "text": text}


def role_transcript(calls: Sequence = (), first: str = "Task: DV1, write the mock.",
                    texts: Sequence[str] = (), handback: Optional[str] = None,
                    agent_type: str = "tstack:troy-developer", model: str = "sonnet"):
    """A troyexam RoleTranscript built from (name, input) or (name, input, denied) tuples.

    The events list the texts first, then the calls, in order.
    """
    from troyexam.transcript import RoleTranscript, ToolCall
    tool_calls = [ToolCall(name=c[0], input=dict(c[1]), denied=bool(c[2]) if len(c) > 2 else False)
                  for c in calls]
    events = [("text", i) for i in range(len(texts))] + [("call", i)
                                                         for i in range(len(tool_calls))]
    return RoleTranscript(first_message=first, calls=tool_calls, texts=list(texts),
                          handback=handback, agent_type=agent_type, model=model, events=events)


# --------------------------------------------------------------- env_run fakes

class RecordingRun:
    """A fake ``env_run``: records each (command, folder) and answers from a function.

    Attributes:
        calls: The (command, folder) pairs, in order.
    """

    def __init__(self, answer: Optional[Callable[[str, Path], tuple]] = None) -> None:
        """Stores the answer function; the default answers (0, "")."""
        self.calls: list = []
        self._answer = answer or (lambda command, folder: (0, ""))

    def __call__(self, command: str, folder: Path) -> tuple:
        """Records the call and answers."""
        self.calls.append((command, Path(folder)))
        return self._answer(command, Path(folder))


def junit_xml(cases: Mapping[str, str]) -> str:
    """A pytest-style JUnit report.

    Args:
        cases: ``"<classname>::<name>"`` mapped to passed, failed, error, or skipped.

    Returns:
        The XML text.
    """
    rows = []
    for test_id, status in cases.items():
        classname, _, name = test_id.partition("::")
        inner = {"passed": "", "failed": '<failure message="assert 0">assert 0</failure>',
                 "error": '<error message="ImportError">ImportError: no module</error>',
                 "skipped": '<skipped message="skip" type="pytest.skip">skip</skipped>'}[status]
        rows.append(f'<testcase classname="{classname}" name="{name}" time="0.010">{inner}'
                    "</testcase>")
    counts = {s: sum(1 for v in cases.values() if v == s) for s in ("failed", "error", "skipped")}
    return ('<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" '
            f'errors="{counts["error"]}" failures="{counts["failed"]}" '
            f'skipped="{counts["skipped"]}" tests="{len(cases)}" time="0.1">'
            + "".join(rows) + "</testsuite></testsuites>")


_JUNIT = re.compile(r"--junit-?xml(?:=|\s+)(?:'([^']*)'|\"([^\"]*)\"|(\S+))")


def junit_path(command: str) -> Optional[Path]:
    """The JUnit path a pytest command writes, from --junitxml or --junit-xml."""
    match = _JUNIT.search(command)
    if not match:
        return None
    return Path(next(group for group in match.groups() if group is not None))


# ----------------------------------------------------------- the stand-in CLI

class StandIn:
    """A copy of the stand-in CLI with its own plan and call log (contract, last section).

    Attributes:
        folder: The folder that holds the copy, plan.json, and calls/.
        path: The stand-in's path, for TROY_EXAM_CLI.
    """

    def __init__(self, plan: Mapping) -> None:
        """Copies the stand-in and writes its plan."""
        self.folder = new_dir("cli")
        self.path = self.folder / "claude_standin.py"
        shutil.copyfile(STANDIN, self.path)
        self.set_plan(plan)

    def set_plan(self, plan: Mapping) -> None:
        """Replaces the plan the next calls follow."""
        (self.folder / "plan.json").write_text(json.dumps(plan), encoding="utf-8")

    def calls(self, kind: str) -> list:
        """The recorded observations of one kind (role or judge), in call order."""
        log = self.folder / "calls"
        if not log.is_dir():
            return []
        found = []
        for path in sorted(log.glob(f"{kind}-*.json")):
            found.append(json.loads(path.read_text(encoding="utf-8")))
        return found

    def claims(self, kind: str) -> int:
        """How many calls of one kind started, finished or not."""
        log = self.folder / "calls"
        return len(list(log.glob(f"{kind}-*.claim"))) if log.is_dir() else 0

    def errors(self) -> str:
        """Every error the stand-in recorded, for assertion messages."""
        log = self.folder / "calls"
        if not log.is_dir():
            return ""
        return "\n".join(p.read_text(encoding="utf-8") for p in sorted(log.glob("*.error")))


def role_plan(**changes) -> dict:
    """The default stand-in plan: every role run writes the mock and reports done."""
    plan = {"role": {"edit": True, "report": "alternate", "probe": True, "role_model": "sonnet",
                     "costs": {HAIKU: 0.003, SONNET: 0.042}},
            "calls": {}, "judge": {"pass_marker": PASS_MARKER, "misgrade": []}, "later": None}
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(plan.get(key), dict):
            plan[key] = {**plan[key], **value}
        else:
            plan[key] = value
    return plan


# ------------------------------------------------- the fake tstack checkout

# What a plugin copy needs from tstack to render briefs and run snapshot and
# check-run: the engine, troy-check, the hooks, troy-init, the packs, the
# role files, and the skills the roles read.
_COPIED = ("agents", "hooks", ".claude-plugin", "skills/troy-mode", "skills/technical-writing",
           "skills/benchmark-checklist", "troy-mode/flow", "troy-mode/checks", "troy-mode/hooks",
           "troy-mode/init", "troy-mode/lang", "troy-mode/roles", "troy-mode/templates")
CASE_ID = "dv-small"
MOCK_BRANCH = "troy-mode/f01-3-mock"


def _copy_real(dest: Path) -> None:
    """Copies the parts of this checkout a plugin copy needs, without tests or caches."""
    for part in _COPIED:
        source = REPO / part
        for path in sorted(source.rglob("*")):
            rel = path.relative_to(REPO)
            if not path.is_file() or "__pycache__" in rel.parts or path.suffix == ".pyc":
                continue
            if "tests" in rel.parts or (rel.parts[0] == "agents"
                                        and not rel.name.startswith("troy-")):
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


class StartRepo:
    """The start repository of the end-to-end case: a troy-mode project at F01's stage 3.

    Attributes:
        path: The repository (its folder is named ``wordcount``).
        start: The start commit, F01's test plan merged.
        later: A later commit, F01's mock merged, which no run may read.
    """

    def __init__(self) -> None:
        """Builds the repository from flow_helpers' project files."""
        import flow_helpers as fh
        self.path = new_dir("src") / START_NAME
        self.path.mkdir()
        git(self.path, "init", "-q", "-b", "main")
        git(self.path, "config", "core.autocrlf", "false")
        steps = [fh.base_step(), *fh.stages(fh.F01, 2)]
        for item in steps:
            self.start = commit_files(self.path, {k: v for k, v in item.files}, item.subject)
        later = fh.stage_step(fh.F01, 3)
        self.later = commit_files(self.path, {k: v for k, v in later.files}, later.subject)


def small_case(start: StartRepo, case_id: str = CASE_ID, branch: str = MOCK_BRANCH,
               max_cost: float = 1.25) -> dict:
    """The end-to-end case: the Developer's DV1 for F01 on the start repository."""
    return case_data(case_id, item="F01",
                     start={"repository": start.path.as_posix(), "commit": start.start,
                            "branch": branch, "pilot": ["#3"]},
                     run={"model": "sonnet", "effort": "high", "minutes": 10,
                          "max_cost": max_cost},
                     criteria=[{"id": "result", "check": "result_is", "must": True,
                                "want": "done"},
                               {"id": "tidy", "judge": 1, "must": True}])


ANCHOR_PASS = ("Role: Developer\nTask: DV1, F01\nResult: done\n"
               "Changed files: src/wordcount/f01.py\n"
               f"Checks: None\nSummary: {PASS_MARKER}; the mock is written.\nFindings: None\n"
               "Question: None\n")
ANCHOR_FAIL = ("Role: Developer\nTask: DV1, F01\nResult: done\n"
               "Changed files: src/wordcount/f01.py\n"
               "Checks: None\nSummary: the mock is written.\nFindings: None\nQuestion: None\n")
JUDGE_RUBRIC = ("# Criteria\n\n"
                f"1. The report's Summary says the work was {PASS_MARKER}. Pass: it does. "
                "Fail: it does not.\n"
                "2. Changed files names the mock's file. Pass: it does. Fail: it does not.\n"
                "3. The report names no file outside src. Pass: it does not. Fail: it does.\n")


def write_small_case(folder: Path, start: StartRepo, **kwargs) -> Path:
    """Writes the end-to-end case folder with its anchors and rubric."""
    return write_case(folder, small_case(start, **kwargs), rubric_text=JUDGE_RUBRIC,
                      anchor_reports={"pass": ANCHOR_PASS, "fail": ANCHOR_FAIL})


class Checkout:
    """A fake tstack checkout whose commits are the versions the exam compares.

    Attributes:
        path: The repository.
        start: The StartRepo its case starts from.
        base: The base commit (A).
        head: A plus one line in the Developer's agent file (B).
        head2: B plus another line in it (B2).
        refactor: A plus a comment at the end of brief.py, which renders the same briefs (C).
        harness: A plus a change to troy-mode/exam/troyexam (D).
        case_change: A plus a change to the case's rubric (E).
    """

    def __init__(self, start: StartRepo) -> None:
        """Builds the repository and its branches."""
        self.start = start
        self.path = new_dir("plugsrc") / "tstack"
        self.path.mkdir()
        _copy_real(self.path)
        write_file(self.path, "troy-mode/exam/troyexam/__init__.py", '"""Harness, first."""\n')
        write_small_case(self.path / "troy-mode/exam/cases" / CASE_ID, start)
        git(self.path, "init", "-q", "-b", "main")
        git(self.path, "config", "core.autocrlf", "false")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "--no-verify", "-m", "Base")
        self.base = self.rev("HEAD")
        agent = "agents/troy-developer.md"
        text = (self.path / agent).read_text(encoding="utf-8")
        self.head = self._branch("head", {agent: text + "\nMarker: head-one\n"}, "Head")
        self.head2 = self._branch("head", {agent: text + "\nMarker: head-two\n"}, "Head two",
                                  start=self.head)
        brief = "troy-mode/flow/troyflow/brief.py"
        brief_text = (self.path / brief).read_text(encoding="utf-8")
        self.refactor = self._branch("refactor", {brief: brief_text + "# Same output.\n"},
                                     "Refactor")
        self.harness = self._branch("harness", {"troy-mode/exam/troyexam/__init__.py":
                                                '"""Harness, second."""\n'}, "Harness")
        rubric_path = f"troy-mode/exam/cases/{CASE_ID}/rubric.md"
        self.case_change = self._branch("casechange", {rubric_path: JUDGE_RUBRIC
                                                       + "\nOne more line.\n"}, "Case")
        git(self.path, "checkout", "-q", "main")

    def rev(self, ref: str) -> str:
        """A ref's full commit ID."""
        return git(self.path, "rev-parse", ref).strip()

    def _branch(self, name: str, files: Mapping[str, str], message: str,
                start: Optional[str] = None) -> str:
        """Commits files on a branch made from a commit (default the base) and returns it."""
        git(self.path, "checkout", "-q", "-B", name, start or self.base)
        return commit_files(self.path, files, message)


_SHARED: dict = {}


def shared_start() -> StartRepo:
    """The start repository, built once per process."""
    if "start" not in _SHARED:
        _SHARED["start"] = StartRepo()
    return _SHARED["start"]


def shared_checkout() -> Checkout:
    """The fake tstack checkout, built once per process."""
    if "checkout" not in _SHARED:
        _SHARED["checkout"] = Checkout(shared_start())
    return _SHARED["checkout"]


class Scenario:
    """One end-to-end use of troy_exam.py: a work root, a config folder, and a stand-in.

    Attributes:
        folder: The scenario's folder.
        root: TROY_EXAM_ROOT.
        config: CLAUDE_CONFIG_DIR.
        env_prefix: The folder given to --env.
        cli: The stand-in.
        checkout: The fake tstack checkout.
    """

    # Variables a parent Claude session sets, which the runner drops (design 11.3),
    # and variables that hold exam words, which child_env drops (contract).
    PARENT = {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli",
              "CLAUDE_CODE_SESSION_ID": "0f7c3a52-parent", "MY_RUBRIC_HOME": "x",
              "TSX_NOTE": "a/baseline/b"}

    def __init__(self, plan: Mapping, root: Optional[Path] = None,
                 checkout: Optional[Checkout] = None) -> None:
        """Makes the folders and the stand-in."""
        self.folder = new_dir("scene")
        self.root = root or (self.folder / "work")
        self.config = self.folder / "config"
        self.config.mkdir()
        self.env_prefix = self.folder / "envx"
        self.env_prefix.mkdir()
        self.cli = StandIn(plan)
        self.checkout = checkout or shared_checkout()

    def env(self) -> dict:
        """The environment troy_exam.py runs with."""
        env = dict(os.environ)
        env.update(self.PARENT)
        env.update({"TROY_EXAM_ROOT": str(self.root), "TROY_EXAM_CLI": str(self.cli.path),
                    "CLAUDE_CONFIG_DIR": str(self.config)})
        return env

    def exam(self, *args: str, timeout: int = 900) -> subprocess.CompletedProcess:
        """Runs troy_exam.py with --repo and --env, from the scratch folder."""
        words = [str(a) for a in args]
        command = words[0]
        extra = ["--repo", str(self.checkout.path)]
        if command in ("run", "prove", "affected"):
            extra += ["--env", str(self.env_prefix)]
        return subprocess.run([sys.executable, str(EXAM_SCRIPT), *words, *extra],
                              cwd=str(self.folder), env=self.env(), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=timeout, check=False)

    def results(self) -> list:
        """The exam folders under results/, oldest name first."""
        folder = self.root / "results"
        return sorted(p for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else []

    def describe(self, proc: subprocess.CompletedProcess) -> str:
        """A run's output and the stand-in's errors, for assertion messages."""
        return (f"exit {proc.returncode}\nstdout:\n{proc.stdout[-5000:]}\n"
                f"stderr:\n{proc.stderr[-5000:]}\nstand-in errors:\n{self.cli.errors()[-3000:]}")


def run_records(exam_folder: Path) -> list:
    """Every run.json under an exam's results folder."""
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(exam_folder.rglob("run.json"))]


def find_entries(data, key: str = "case") -> list:
    """Every dict in a JSON value that has the key, depth first."""
    found = []
    if isinstance(data, dict):
        if key in data:
            found.append(data)
        for value in data.values():
            found += find_entries(value, key)
    elif isinstance(data, list):
        for value in data:
            found += find_entries(value, key)
    return found


def wait_until(predicate: Callable[[], bool], seconds: float = 10.0) -> bool:
    """Polls a condition until it holds or the time runs out."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.1)
    return predicate()

