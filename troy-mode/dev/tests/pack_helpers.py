"""Shared helpers for the language pack tests (F03 design 8 to 10).

They read the subset of workflow YAML the packs use, run build_sample.py as
CI runs it, and give access to troy-check's config parser.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
TROY_MODE = DEV.parent
REPO = TROY_MODE.parent
BUILD = DEV / "build_sample.py"
WORKFLOWS = REPO / ".github" / "workflows"
SAMPLE_ONLY_STEPS = ("Build the sample", "Compare with the expected results")
PINNED = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
_USES = re.compile(r"^\s*(?:- )?uses: (\S+)(.*)$")

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
