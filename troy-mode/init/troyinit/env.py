"""The series environment and its lock (design section 5.4, D51).

On Troy's PC the language step follows the pack README's setup: create the
series environment with mamba when it is missing, compile the lock with the
environment's uv from every member's manifest, and install the lock.
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .errors import InitError
from .packs import Pack

_OUTPUT_LINES = 40


@dataclass
class EnvPlan:
    """The environment work of one language step.

    Attributes:
        name: The environment's name.
        prefix: The folder to create it in (--env-prefix), or None for a named one.
        series: The series' member folders, this project as ".".
        lock: The lock file to compile.
        skipped: True with --no-env.
        mamba: mamba's path, or None when it was not needed or not found.
        exists: Whether the environment existed before the step, None when skipped.
        commands: The mamba commands to run, each a full argv.
        checks: The read-only mamba commands planning ran, such as env list.
    """

    name: str
    prefix: str | None
    series: list[str]
    lock: str
    skipped: bool
    mamba: str | None = None
    exists: bool | None = None
    commands: list[list[str]] = field(default_factory=list)
    checks: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """The report's environment entry."""
        return {"name": self.name, "prefix": self.prefix, "series": list(self.series),
                "lock": self.lock, "skipped": self.skipped, "exists": self.exists,
                "commands": [list(c) for c in self.checks + self.commands]}


def find_mamba(option: str | None) -> str | None:
    """Finds mamba: --mamba, then the PATH, then $MAMBA_EXE (design 5.4).

    Args:
        option: The --mamba value, or None.

    Returns:
        mamba's path, or None when none of them names an existing program.
    """
    if option:
        return option if Path(option).is_file() else shutil.which(option)
    found = shutil.which("mamba")
    if found:
        return found
    exe = os.environ.get("MAMBA_EXE")
    return exe if exe and Path(exe).is_file() else None


def _env_vars() -> dict[str, str]:
    """The environment for mamba and uv: uv copies files (design 5.4)."""
    return {**os.environ, "UV_LINK_MODE": "copy"}


def _run(command: list[str], cwd: Path) -> str:
    """Runs one mamba command and returns its output.

    Raises:
        InitError: The command cannot start or exits with a non-zero code.
    """
    try:
        proc = subprocess.run(command, cwd=str(cwd), env=_env_vars(), capture_output=True,
                              stdin=subprocess.DEVNULL, check=False)
    except OSError as exc:
        raise InitError(f"cannot run {' '.join(command)}: {exc}") from exc
    output = (proc.stdout + proc.stderr).decode("utf-8", "replace")
    if proc.returncode != 0:
        tail = "\n".join(output.strip().splitlines()[-_OUTPUT_LINES:])
        raise InitError(f"{' '.join(command)} exited with code {proc.returncode}:\n{tail}")
    return output


def _named_env_exists(mamba: str, name: str, cwd: Path, checks: list[list[str]]) -> bool:
    """Asks mamba whether an environment with this name exists.

    Args:
        mamba: mamba's path.
        name: The environment's name.
        cwd: The folder to run in.
        checks: The commands run so far; this one is added.

    Raises:
        InitError: mamba fails or prints something that is not its JSON list.
    """
    command = [mamba, "env", "list", "--json"]
    checks.append(command)
    output = _run(command, cwd)
    try:
        start = output.index("{")
        envs = json.loads(output[start:output.rindex("}") + 1])["envs"]
    except (ValueError, KeyError, TypeError) as exc:
        raise InitError(f"cannot read mamba env list --json: {exc}") from exc
    return any(Path(str(env)).name == name for env in envs)


def manifests(pack: Pack, series: list[str]) -> list[str]:
    """The manifest of each series member, in series order (design 5.4)."""
    found = []
    for member in series:
        member = member.replace("\\", "/").rstrip("/")
        found.append(pack.manifest if member in (".", "") else f"{member}/{pack.manifest}")
    return found


def plan_env(pack: Pack, repo: Path, env: EnvPlan, mamba_option: str | None,
             look: bool = True) -> list[str]:
    """Finds mamba, checks whether the environment exists, and plans the commands.

    Args:
        pack: The language pack.
        repo: The project's root, where the commands run.
        env: The environment to plan; filled in place.
        mamba_option: The --mamba value, or None.
        look: False when the step is stopped anyway: only find mamba.

    Returns:
        Problems that stop the step: mamba was not found.

    Raises:
        InitError: mamba cannot list its environments.
    """
    if env.skipped:
        return []
    env.mamba = find_mamba(mamba_option)
    if not env.mamba:
        where = f"at {mamba_option}" if mamba_option else "on the PATH or in $MAMBA_EXE"
        return [f"mamba was not found {where}. Pass --mamba <path>, or --no-env to write the "
                "files only."]
    if not look:
        return []
    if env.prefix:
        target = ["-p", env.prefix]
        env.exists = (Path(env.prefix) / "conda-meta").is_dir()
    else:
        target = ["-n", env.name]
        env.exists = _named_env_exists(env.mamba, env.name, repo, env.checks)
    uv = [env.mamba, "run", *target, "uv", "pip"]
    if not env.exists:
        env.commands.append([env.mamba, "env", "create", "-y", "-f", "environment.yml", *target])
    env.commands.append([*uv, "compile", *manifests(pack, env.series), *pack.compile_args,
                         "-o", env.lock])
    env.commands.append([*uv, "install", "-r", env.lock])
    return []


def run_env(repo: Path, env: EnvPlan) -> None:
    """Runs the planned commands: create, compile the lock, and install it.

    Args:
        repo: The project's root.
        env: The planned environment work.

    Raises:
        InitError: A command fails, or uv wrote no lock.
    """
    for command in env.commands:
        print(f"troy-init: running {' '.join(command)}", file=sys.stderr, flush=True)
        _run(command, repo)
        if command[-2:] == ["-o", env.lock] and not (repo / env.lock).is_file():
            raise InitError(f"{' '.join(command)} wrote no {env.lock}")
