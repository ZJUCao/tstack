"""Shared helpers for the language pack tests (F03 design 8 to 10, F06 design 5.6 and 8).

They read the subset of workflow YAML the packs use, run build_sample.py as
CI runs it, run a workflow step's script with bash, and give access to
troy-check's config parser.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
TROY_MODE = DEV.parent
REPO = TROY_MODE.parent
BUILD = DEV / "build_sample.py"
WORKFLOWS = REPO / ".github" / "workflows"
SAMPLE_ONLY_STEPS = ("Build the sample", "Compare with the expected results")
PINNED = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
_USES = re.compile(r"^\s*(?:- )?uses: (\S+)(.*)$")
LOOK_FOR_CODE = "Look for code"
CODE_GUARD = "steps.code.outputs.found == 'true'"
SAMPLE_EMAIL = "sample@example.invalid"
_CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

sys.path.insert(0, str(TROY_MODE / "checks"))
from troycheck.config import parse_config  # noqa: E402, F401  (re-exported)


def steps(path: Path) -> list[tuple[str, str]]:
    """Reads the (name, run) pairs of a workflow's run steps, in order.

    Handles the subset of YAML the workflows use: "- name:" starts a step,
    and run is one line or a "|" block.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    found, name, index = [], None, 0
    while index < len(lines):
        line = lines[index]
        named = re.match(r"^\s*- name: (.+)$", line)
        if named or re.match(r"^\s*- uses: ", line):
            name = named.group(1) if named else None
        run = re.match(r"^(\s*)run: (.*)$", line)
        if run and name:
            body, indent = run.group(2), len(run.group(1))
            if body == "|":
                block = []
                while index + 1 < len(lines) and (
                        not lines[index + 1].strip()
                        or len(lines[index + 1]) - len(lines[index + 1].lstrip()) > indent):
                    index += 1
                    block.append(lines[index].strip())
                body = "\n".join(block).strip()
            found.append((name, body))
        index += 1
    return found


def uses(path: Path) -> list[tuple[str, str]]:
    """Lists every action a workflow uses, with the comment after it."""
    return [(m.group(1), m.group(2).strip())
            for line in path.read_text(encoding="utf-8").splitlines()
            if (m := _USES.match(line))]


def run_build(*args: str, github_env: Path | None = None) -> subprocess.CompletedProcess:
    """Runs build_sample.py with the given arguments.

    GITHUB_ENV is removed, so a test run in CI never writes to the job's
    environment, unless github_env names a file for it.
    """
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ENV"}
    if github_env is not None:
        env["GITHUB_ENV"] = str(github_env)
    return subprocess.run([sys.executable, str(BUILD), *args], capture_output=True,
                          text=True, encoding="utf-8", check=False, env=env)


def git(repo: Path, *args: str) -> str:
    """Runs a read-only git command in a built sample."""
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout.strip()


def git_bytes(repo: Path, *args: str) -> bytes:
    """Runs a read-only git command in a built sample and returns its raw output."""
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          check=True).stdout


def step_blocks(path: Path) -> list[dict[str, str]]:
    """Reads every step under a workflow's "steps:" with its own top-level keys.

    Unlike steps(), it keeps the keys steps() ignores, such as id and if.
    Each step is a dict from each key written at the step's own level (name,
    id, if, uses, run, env, ...) to the rest of that line, plus "text", the
    step's lines joined.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[dict[str, str]] = []
    index = 0
    while index < len(lines):
        header = re.match(r"^(\s*)steps:\s*$", lines[index])
        index += 1
        if not header:
            continue
        base, dash, current = len(header.group(1)), None, None
        while index < len(lines):
            line = lines[index]
            indent = len(line) - len(line.lstrip())
            if line.strip() and not line.lstrip().startswith("#") and indent <= base:
                break
            item = re.match(r"^(\s*)- ([\w-]+):\s?(.*)$", line)
            if item and (dash is None or len(item.group(1)) == dash):
                dash = len(item.group(1))
                current = {item.group(2): item.group(3).strip(), "text": line}
                blocks.append(current)
            elif current is not None:
                current["text"] += "\n" + line
                key = re.match(r"^(\s*)([\w-]+):\s?(.*)$", line)
                if key and dash is not None and len(key.group(1)) == dash + 2:
                    current.setdefault(key.group(2), key.group(3).strip())
            index += 1
    return blocks


def bash_path() -> str | None:
    """Finds a bash that runs scripts as a runner's does, or None.

    On Windows the bash on the PATH may be WSL's, so this takes Git for
    Windows' own bash, next to the git on the PATH.
    """
    if os.name != "nt":
        return shutil.which("bash")
    git_exe = shutil.which("git")
    if not git_exe:
        return None
    # git.exe sits in <Git>/cmd, <Git>/bin, or <Git>/mingw64/bin.
    for root in Path(git_exe).resolve().parents[:3]:
        for candidate in (root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"):
            if candidate.is_file():
                return str(candidate)
    return None


def run_step_script(script: str, files: dict[str, str]) -> tuple[list[str], str]:
    """Runs a step's bash script in a new git repository holding the given files.

    The files are committed, as a checked-out PR head is. GITHUB_OUTPUT and
    GITHUB_STEP_SUMMARY name files, as on a runner. bash comes from
    bash_path(); callers skip when it finds none.

    Returns:
        The lines the script wrote to GITHUB_OUTPUT, and the summary's text.

    Raises:
        AssertionError: The script exits with a code other than 0.
    """
    with tempfile.TemporaryDirectory(prefix="step-") as tmp:
        repo, output, summary = Path(tmp) / "repo", Path(tmp) / "output", Path(tmp) / "summary"
        repo.mkdir()
        output.write_bytes(b"")
        summary.write_bytes(b"")
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_", "GIT_"))}
        env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "Step Test", "GIT_AUTHOR_EMAIL": SAMPLE_EMAIL,
                    "GIT_COMMITTER_NAME": "Step Test", "GIT_COMMITTER_EMAIL": SAMPLE_EMAIL})
        for rel, text in {"README.md": "# Sample\n", **files}.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text, encoding="utf-8")
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "Head"]):
            subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)
        (Path(tmp) / "step.sh").write_text(script + "\n", encoding="utf-8")
        env.update({"GITHUB_OUTPUT": output.as_posix(), "GITHUB_STEP_SUMMARY": summary.as_posix()})
        proc = subprocess.run([bash_path() or "bash", "-eo", "pipefail",
                               (Path(tmp) / "step.sh").as_posix()],
                              cwd=repo, env=env, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise AssertionError(f"the step exited {proc.returncode}: {proc.stderr}")
        return output.read_text(encoding="utf-8").splitlines(), summary.read_text("utf-8")


def lf_bytes(data: bytes) -> bytes:
    """Replaces CRLF with LF."""
    return data.replace(b"\r\n", b"\n")


def sha256_lf(data: bytes) -> str:
    """The install record's hash: SHA-256 of the bytes with CRLF made LF."""
    return hashlib.sha256(lf_bytes(data)).hexdigest()


def tree_paths(folder: Path) -> list[str]:
    """Every file under a folder, by relative path with "/", without caches, sorted."""
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*")
                  if p.is_file() and not _CACHES & set(p.relative_to(folder).parts)
                  and p.suffix != ".pyc")


def setup_paths() -> list[str]:
    """Every path troy-init's setup commits, without the git-ignored progress file."""
    skipped = ("workflow.yml", "config.default.toml")
    checks = [f".troy-mode/checks/{rel}" for rel in tree_paths(TROY_MODE / "checks")
              if rel not in skipped and not rel.startswith("tests/")]
    templates = [f".troy-mode/templates/{rel}" for rel in tree_paths(TROY_MODE / "templates")]
    return sorted([*checks, *templates, ".troy-mode/config.toml", ".troy-mode/install.toml",
                   "docs/rules.md", "docs/rules.zh-CN.md", ".github/pull_request_template.md",
                   ".github/workflows/troy-mode.yml", ".gitignore"])


def pack_patterns() -> dict[str, set[str]]:
    """Every pack's [paths] patterns by list name, plus the D49 header in config."""
    patterns: dict[str, set[str]] = {}
    for path in sorted((TROY_MODE / "lang").glob("*/config.toml")):
        for key, values in tomllib.loads(path.read_text("utf-8")).get("paths", {}).items():
            patterns.setdefault(key, set()).update(values)
    patterns.setdefault("config", set()).add("include/troy/not_implemented.h")
    return patterns


def pack_workflow(lang: str) -> str:
    """F02's workflow followed by a pack's job, as troy-init joins them."""
    first = (TROY_MODE / "checks" / "workflow.yml").read_text("utf-8").replace("\r\n", "\n")
    job = (TROY_MODE / "lang" / lang / "workflow-job.yml").read_text("utf-8")
    return first.rstrip("\n") + "\n\n" + job.replace("\r\n", "\n")
