"""The series lock after an accepted dependency change (F07 design 8.7, D66).

F07 compiles the lock from every member's manifest with troy-init's functions
(F06 design 5.4), installs it in the shared environment, and runs each member's
tests there (F03 design 8.1). This module only plans: the skill runs the
commands, and the engine writes nothing. uv gets troy-init's cache folder when
UV_CACHE_DIR is not set (F06 design 5.4, D213).
"""

import shlex
from pathlib import Path

from troyinit.env import manifests
from troyinit.errors import InitError
from troyinit.packs import get_pack

from . import checksteps, repo as git

# Each pack's tests, run in a member's folder.
MEMBER_TESTS = {
    "python": ("python -m pytest -q",),
    "cpp": ("cmake --preset coverage", "cmake --build --preset coverage",
            "ctest --preset coverage"),
}


def _read_lf(path: Path) -> bytes | None:
    """Reads a file with CRLF made LF, or None when it is missing."""
    try:
        return path.read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return None


def _member(repo, member: str, lock: str, own: bytes | None, run: str, lang: str) -> dict:
    """Builds one members entry: whether it exists, whether its lock is stale, its tests."""
    path = member.replace("\\", "/").rstrip("/") or "."
    if path == ".":
        return {"path": ".", "this": True, "exists": True, "stale": False, "tests": None}
    folder = repo.root / path
    exists = folder.is_dir()
    other = _read_lf(folder / lock) if exists else None
    return {"path": path, "this": False, "exists": exists,
            "stale": other is None or other != own,
            "tests": {"cwd": path, "commands": [f"{run} {c}" for c in MEMBER_TESTS[lang]]}}


def run_series(args) -> tuple[dict, int]:
    """Plans the series lock: the commands, each member's tests, and the stale members.

    Args:
        args: Parsed options: repo.

    Returns:
        The report and the exit code: 1 when the config has no pack or a member
        folder is missing.

    Raises:
        FlowError: Not a repository, or an invalid config at HEAD.
    """
    repo = git.need_repo(args.repo)
    config = git.config_at(repo, "HEAD")
    report = {"command": "series", "ok": False, "notes": [], "problems": [], "lang": None,
              "lock": None, "commands": [], "members": [], "stale": []}
    name = config.lang.get("name")
    if not name:
        report["problems"].append("The config at HEAD has no [lang] name, so there is no lock.")
        return report, 1
    try:
        pack = get_pack(name)
    except InitError as exc:
        report["problems"].append(str(exc))
        return report, 1
    run = checksteps.run_prefix(config, repo.root.name, report["notes"])
    series = list(config.lang.get("series") or ["."])
    sources = " ".join(shlex.quote(m) for m in manifests(pack, series))
    options = " ".join(shlex.quote(o) for o in pack.compile_args)
    env = checksteps.uv_variables()
    report.update(lang=name, lock=pack.lock, commands=[
        f"{env} {run} uv pip compile {sources} {options} -o {pack.lock}",
        f"{env} {run} uv pip install -r {pack.lock}",
    ])
    own = _read_lf(repo.root / pack.lock)
    for member in series:
        entry = _member(repo, member, pack.lock, own, run, name)
        report["members"].append(entry)
        if not entry["exists"]:
            report["problems"].append(f"The series member {entry['path']} does not exist, so its "
                                      "tests cannot run.")
        if entry["stale"]:
            report["stale"].append(entry["path"])
    report["ok"] = not report["problems"]
    return report, 0 if report["ok"] else 1
