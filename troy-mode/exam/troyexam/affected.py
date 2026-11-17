"""Which cases a change affects, with no model call (design 9.2).

For each case the engine of each version renders the brief in the case's
project, and the role's agent file and the plugin files it reads are compared.
A case whose inputs are the same in both versions is not affected.
"""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from .cases import Case
from .instructions import GitTree, glob_match, named_skills
from .paths import Layout
from .project import build_project, copy_plugin, ensure_mirror, git, new_run_folder
from .runner import cleanup
from .runrole import brief_args, flow, write_input

HARNESS = "troy-mode/exam/troyexam/**"
CASES = "troy-mode/exam/cases"


def role_inputs(case: Case, plugin: Path, project: Path, env: Mapping[str, str]) -> dict[str, str]:
    """What the role would get from one plugin copy: the brief, its agent file, and the plugin files it reads."""
    input_file = write_input(case, project)
    report = flow(sys.executable, plugin, project, env, *brief_args(case, input_file))
    if input_file is not None:
        input_file.unlink()
    inputs = {"brief": report.get("prompt") if report.get("ok") else f"problems: {report.get('problems')}"}
    agent = plugin / "agents" / f"troy-{case.role}.md"
    inputs["agent"] = agent.read_text(encoding="utf-8") if agent.is_file() else ""
    folders = ["troy-mode/templates/"] + named_skills(_Folder(plugin))
    for path in sorted(p for p in plugin.rglob("*") if p.is_file()):
        rel = path.relative_to(plugin).as_posix()
        if any(rel.startswith(folder) for folder in folders):
            inputs[rel] = path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8", errors="replace")
    return inputs


class _Folder:
    """A plugin copy as a tree for named_skills."""

    def __init__(self, root: Path):
        """Reads files under root."""
        self.root = root

    def files(self) -> list[str]:
        """The agent files and common.md, the only files named_skills reads."""
        found = [p.relative_to(self.root).as_posix() for p in (self.root / "agents").glob("troy-*.md")]
        common = self.root / "troy-mode" / "roles" / "common.md"
        return found + (["troy-mode/roles/common.md"] if common.is_file() else [])

    def read(self, path: str) -> bytes | None:
        """The file's bytes."""
        full = self.root / path
        return full.read_bytes() if full.is_file() else None


def _changed(repo: Path, base: str, head: str) -> list[str]:
    """The paths that differ between two commits."""
    return git(repo, "diff", "--name-only", "--no-renames", base, head).splitlines()


def affected(repo: Path, base: str, head: str, cases: Sequence[Case], layout: Layout,
             env: Mapping[str, str]) -> list[dict]:
    """Lists, for each case, whether the change from base to head affects it, and why."""
    changed = _changed(repo, base, head)
    harness = any(glob_match(p, HARNESS) for p in changed)
    results = []
    for case in cases:
        why = []
        if harness:
            why.append("the exam's harness changed, so its anchors are proved again")
        own = f"{CASES}/{case.id}/"
        if any(p.startswith(own) for p in changed):
            why.append("the case's own files changed")
        if not why:
            why += _input_changes(repo, base, head, case, layout, env)
        results.append({"case": case.id, "affected": bool(why), "why": why})
    return results


def _input_changes(repo: Path, base: str, head: str, case: Case, layout: Layout,
                   env: Mapping[str, str]) -> list[str]:
    """Renders the case's inputs with both versions and names what differs."""
    mirror = ensure_mirror(layout, case.start.repository, case.start.commit)
    folder = new_run_folder(layout, case.start.repository)
    try:
        build_project(case, folder, mirror)
        found = {}
        for side, ref in (("base", base), ("head", head)):
            plugin = folder.root / side
            copy_plugin(repo, ref, plugin)
            found[side] = role_inputs(case, plugin, folder.project, env)
            cleanup([plugin])
        keys = sorted(set(found["base"]) | set(found["head"]))
        return [f"{key} differs" for key in keys if found["base"].get(key) != found["head"].get(key)]
    finally:
        cleanup([folder.root])
