"""One role run, non-interactively (design 11.3 and 11.5).

A haiku main session that belongs to the runner starts the role as a
foreground subagent with the engine's brief, so the role runs under the
plugin's hooks and write scope, as in a real troy-mode session (probe A2).
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import AGENT_PREFIX, CLI_VARIABLE, INSTALLED_OFF
from .blinding import LABELS, exam_words
from .errors import ExamError

SESSION_VARIABLES = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID",
                     "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_MESSAGING_SOCKET",
                     "CLAUDE_CODE_HOST_SESSION_ID", "CLAUDE_PID")
BEGIN, END = "BEGIN", "END"
GIT_BASH = r"D:\Program Files\Git\bin\bash.exe"
MAMBA_ROOT = r"D:\miniforge3"


def find_cli(env: Mapping[str, str]) -> Path:
    """The CLI: CLI_VARIABLE, else the newest bundled claude.exe under %LOCALAPPDATA%\\Claude-Data.

    Raises:
        ExamError: No CLI is found.
    """
    named = env.get(CLI_VARIABLE)
    if named:
        if not Path(named).is_file():
            raise ExamError(f"{CLI_VARIABLE} names {named}, which does not exist")
        return Path(named)
    local = env.get("LOCALAPPDATA") or os.path.join(str(Path.home()), "AppData", "Local")
    found = []
    for exe in Path(local, "Claude-Data").glob("*/claude-code/*/*/claude.exe"):
        version = exe.parent.parent.name
        if re.fullmatch(r"\d+(\.\d+)*", version):
            found.append((tuple(int(p) for p in version.split(".")), exe.stat().st_mtime, exe))
    if not found:
        raise ExamError(f"no claude.exe under {local}\\Claude-Data; set {CLI_VARIABLE}")
    return max(found)[2]


def cli_command(cli: Path) -> list[str]:
    """How to start the CLI: a stand-in .py through this Python, else the program itself."""
    return [sys.executable, str(cli)] if str(cli).endswith(".py") else [str(cli)]


def cli_version(cli: Path) -> str:
    """The CLI's version: its <version> folder, else the first word of `--version`."""
    parts = Path(cli).parts
    if len(parts) >= 4 and parts[-4] == "claude-code":
        return parts[-3]
    proc = subprocess.run([*cli_command(cli), "--version"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)
    words = proc.stdout.split()
    return words[0] if words else "unknown"


def driver_prompt(role: str, model: str, effort: str, brief: str) -> str:
    """The main session's prompt: one Agent call with the brief copied exactly, then the report."""
    return (f'Call the Agent tool exactly once, with subagent_type "{AGENT_PREFIX}{role}", '
            f'model "{model}", effort "{effort}", run_in_background false, and as its prompt the '
            f"text between the lines {BEGIN} and {END}, copied exactly, every character and line. "
            "Do nothing else before or after. Then reply with the agent's report, unchanged.\n"
            f"{BEGIN}\n{brief.rstrip(chr(10)).rstrip(chr(13))}\n{END}")


def brief_between(prompt: str) -> str:
    """The text between the BEGIN and END lines of a driver prompt."""
    lines = prompt.replace("\r\n", "\n").split("\n")
    start = lines.index(BEGIN)
    end = len(lines) - 1 - lines[::-1].index(END)
    return "\n".join(lines[start + 1:end])


def command_line(cli: Path, prompt: str, plugin_dir: Path, session_id: str, max_cost: float,
                 driver_model: str = "haiku") -> list[str]:
    """The command line of one run (design 11.3), with the tstack names."""
    return [*cli_command(cli), "-p", prompt, "--model", driver_model,
            "--plugin-dir", str(plugin_dir), "--settings", INSTALLED_OFF,
            "--permission-mode", "auto", "--permission-prompts", "none",
            "--allowedTools", "Agent", "--output-format", "stream-json", "--verbose",
            "--session-id", session_id, "--max-budget-usd", f"{max_cost:.2f}"]


def child_env(parent: Mapping[str, str], *, python: str, env_prefix: str, project: Path,
              bin_dir: Path, work_root: Path) -> dict[str, str]:
    """The run's environment: no tie to the parent session, no exam word, and the run's variables."""
    env = {}
    for name, value in parent.items():
        if name in SESSION_VARIABLES or name.startswith("TROY_EXAM_"):
            continue
        if exam_words(name) or exam_words(value):
            continue
        env[name] = value
    path_name = next((n for n in parent if n.upper() == "PATH"), "PATH")
    env.pop(path_name, None)
    env.update({
        "CLAUDE_CODE_GIT_BASH_PATH": parent.get("CLAUDE_CODE_GIT_BASH_PATH") or GIT_BASH,
        "TROY_MODE_PYTHON": python, "TROY_MODE_ENV_PREFIX": str(env_prefix),
        "PYTHONPATH": str(Path(project) / "src"),
        "MAMBA_ROOT_PREFIX": parent.get("MAMBA_ROOT_PREFIX") or MAMBA_ROOT,
        "UV_CACHE_DIR": str(Path(work_root) / "uv-cache"), "MSYS_NO_PATHCONV": "1",
        path_name: str(bin_dir) + os.pathsep + parent.get(path_name, ""),
    })
    return env


def added_variables(env: Mapping[str, str], project: Path) -> dict[str, str]:
    """The variables the runner sets, for the blinding check."""
    names = ("CLAUDE_CODE_GIT_BASH_PATH", "TROY_MODE_PYTHON", "TROY_MODE_ENV_PREFIX", "PYTHONPATH",
             "MAMBA_ROOT_PREFIX", "UV_CACHE_DIR", "MSYS_NO_PATHCONV")
    return {n: env[n] for n in names if n in env}


def brief_arrived(transcript, brief: str) -> bool:
    """Tells whether the role's first message is the brief, CRLF and outer whitespace aside.

    A last line END, the driver prompt's own marker that the main session sometimes copies
    after the brief, is not a change to the brief.
    """
    def norm(text: str) -> str:
        return (text or "").replace("\r\n", "\n").strip()
    if transcript is None:
        return False
    first, want = norm(transcript.first_message), norm(brief)
    return first in (want, f"{want}\n{END}")


def processes_with(text: str) -> list[tuple[int, str]]:
    """Other processes whose command line holds text."""
    found = []
    mine = {os.getpid(), os.getppid()}
    if os.name == "nt":
        script = ("Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | "
                  "ConvertTo-Json -Compress")
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=120)
        try:
            rows = json.loads(proc.stdout or "[]")
        except ValueError:
            rows = []
        rows = rows if isinstance(rows, list) else [rows]
        lowered = text.lower()
        for row in rows:
            line = row.get("CommandLine") or ""
            if lowered in line.lower() and row.get("ProcessId") not in mine:
                found.append((int(row["ProcessId"]), line))
        return found
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            line = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if text in line and int(entry.name) not in mine:
            found.append((int(entry.name), line.strip()))
    return found


def _children(pid: int) -> list[int]:
    """The direct children of a process, from /proc."""
    found = []
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            fields = (entry / "stat").read_text(errors="replace").rsplit(")", 1)[-1].split()
        except OSError:
            continue
        if len(fields) > 1 and fields[1] == str(pid):
            found.append(int(entry.name))
    return found


def end_tree(pid: int) -> None:
    """Ends a process and its children.

    On POSIX a whole process group is ended only when the process leads its own
    group, which the runner's sessions do; a group shared with the exam itself
    is never ended.
    """
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        return
    import signal
    try:
        group = os.getpgid(pid)
    except OSError:
        return
    if group == pid and group != os.getpgid(0):
        try:
            os.killpg(group, signal.SIGKILL)
            return
        except OSError:
            pass
    for child in _children(pid):
        end_tree(child)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _unlock(func, path, _info) -> None:
    """Makes a read-only file writable and retries its delete, for git's object files on Windows.

    On POSIX a failure is left alone, so the folder stays and cleanup lists it.
    """
    if os.name != "nt" or func not in (os.unlink, os.remove, os.rmdir):
        return
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except OSError:
        pass


def cleanup(paths: Iterable[Path]) -> list[str]:
    """Deletes folders; gives those that are still there."""
    left = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        for _ in range(3):
            shutil.rmtree(path, onerror=_unlock)
            if not path.exists():
                break
            time.sleep(1)
        if path.exists():
            left.append(str(path))
    return left


@dataclass
class Session:
    """What one CLI session left.

    Attributes:
        code: Its exit code, or None when the runner ended it.
        timed_out: It passed its time limit.
        minutes: How long it ran.
        leftovers: Command lines of processes that still ran afterwards.
    """

    code: int | None
    timed_out: bool
    minutes: float
    leftovers: list = field(default_factory=list)


def run_session(command: list[str], cwd: Path, env: Mapping[str, str], minutes: float,
                stdout: Path, stderr: Path, folder: Path) -> Session:
    """Runs one CLI session under its time limit, then ends what it left running in folder."""
    started = time.monotonic()
    flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" \
        else {"start_new_session": True}
    with open(stdout, "wb") as out, open(stderr, "wb") as err:
        proc = subprocess.Popen(command, cwd=str(cwd), env=dict(env), stdin=subprocess.DEVNULL,
                                stdout=out, stderr=err, **flags)
        timed_out = False
        try:
            proc.wait(timeout=minutes * 60)
        except subprocess.TimeoutExpired:
            timed_out = True
            end_tree(proc.pid)
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                pass
    leftovers = []
    for pid, line in processes_with(str(folder)):
        leftovers.append(line)
        end_tree(pid)
    code = None if timed_out else proc.returncode
    return Session(code, timed_out, (time.monotonic() - started) / 60, leftovers)


def blind_problems(texts: Mapping[str, str], names: Mapping[str, str]) -> list[str]:
    """Exam words in the texts the exam adds, and labels in the names a role sees (design 6.1)."""
    problems = []
    for where, text in texts.items():
        for word in exam_words(text):
            problems.append(f"{where} holds {word!r}")
    for where, text in names.items():
        for word in exam_words(text, LABELS):
            problems.append(f"{where} holds {word!r}")
    return sorted(set(problems))


def new_session_id() -> str:
    """A new session ID for --session-id."""
    return str(uuid.uuid4())
