"""Which cases a change affects, with no model call (design 9.2).

For each case the engine of each version renders the brief in the case's
project, and the role's agent file and the plugin files it reads are compared.
A case whose inputs are the same in both versions is not affected.
"""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from .cases import Case
from .instructions import glob_match, skills_in
from .paths import Layout
from .project import build_project, copy_plugin, ensure_mirror, git, new_run_folder
from .runner import cleanup
from .runrole import brief_args, flow, write_input

HARNESS = "troy-mode/exam/troyexam/**"
CASES = "troy-mode/exam/cases"
TEMPLATES = "troy-mode/templates/"
PROJECT_TEMPLATES = ".troy-mode/templates"


def reads_template(rel: str, plugin: Path, project: Path, prompt: str) -> bool:
    """Tells whether a role reads the plugin's copy of a template (design 9.2, F06 design D294).

    Roles fill templates from the project's copy (F04 common rule 7), so the plugin's
    copy counts only when the project has none of that file, or when the brief names
    the plugin's copy by its path, as the rule change brief does.
    """
    if not (project / PROJECT_TEMPLATES / rel.removeprefix(TEMPLATES)).is_file():
        return True
    return (plugin / rel).as_posix() in prompt


def role_inputs(case: Case, plugin: Path, project: Path, env: Mapping[str, str]) -> dict[str, str]:
    """What the role would get from one plugin copy: the brief, its agent file, and the plugin files it reads.

    The skills compared are only those that the role's agent file, common.md, or its own
    brief names, so a skill's change affects only the cases that read it (F17 design D163).
    The templates compared are only those the role reads from the plugin (reads_template).
    """
    input_file = write_input(case, project)
    report = flow(sys.executable, plugin, project, env, *brief_args(case, input_file))
    if input_file is not None:
        input_file.unlink()
    inputs = {"brief": report.get("prompt") if report.get("ok") else f"problems: {report.get('problems')}"}
    agent = plugin / "agents" / f"troy-{case.role}.md"
    inputs["agent"] = agent.read_text(encoding="utf-8") if agent.is_file() else ""
    common = plugin / "troy-mode" / "roles" / "common.md"
    common_text = common.read_text(encoding="utf-8") if common.is_file() else ""
    prompt = report.get("prompt") or ""
    folders = [TEMPLATES] + skills_in(inputs["agent"], common_text, prompt)
    for path in sorted(p for p in plugin.rglob("*") if p.is_file()):
        rel = path.relative_to(plugin).as_posix()
        if rel.startswith(TEMPLATES) and not reads_template(rel, plugin, project, prompt):
            continue
        if any(rel.startswith(folder) for folder in folders):
            inputs[rel] = path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8", errors="replace")
    return inputs


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
