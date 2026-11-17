"""One whole role run, from a fresh project to its saved record (design 4.2, 6.1, 11.3, 11.5)."""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import AGENT_PREFIX, PLUGIN_NAME
from .cases import Case
from .checks import UNIVERSAL_MUSTS, RunContext, grade
from .errors import ExamError
from .ghstub import write_gh
from .instructions import glob_match
from .paths import Layout
from .project import build_project, copy_plugin, git, new_run_folder
from .runner import (added_variables, blind_problems, brief_arrived, child_env, cleanup,
                     command_line, driver_prompt, new_session_id, run_session)
from .transcript import projects_key_dir, read_role, read_stream, role_report, session_dir

TIME = "%Y-%m-%dT%H:%M:%SZ"


@dataclass
class RunSpec:
    """What one run needs.

    Attributes:
        case: The case.
        side: "base" or "head".
        commit: The tstack commit whose roles run.
        instructions: That commit's instruction hash.
        layout: The work root.
        repo: The tstack checkout.
        mirror: The start repository's mirror.
        env_prefix: The case's environment.
        cli: The CLI.
        cli_version: Its version.
        out: The folder for this run's results.
        run_id: The run's ID.
        python: The Python for hooks and the gh stand-in.
        parent_env: The exam's own environment.
        driver_model: The main session's model.
    """

    case: Case
    side: str
    commit: str
    instructions: str
    layout: Layout
    repo: Path
    mirror: Path
    env_prefix: Path
    cli: Path
    cli_version: str
    out: Path
    run_id: str
    python: str
    parent_env: Mapping[str, str]
    driver_model: str = "haiku"


def env_runner(prefix: Path, base_env: Mapping[str, str]):
    """Runs shell commands with the environment's programs first on the PATH and PYTHONPATH=<cwd>/src."""
    prefix = Path(prefix)
    bins = [prefix, prefix / "Library" / "bin", prefix / "Scripts"] if os.name == "nt" \
        else [prefix / "bin"]
    named = base_env.get("CLAUDE_CODE_GIT_BASH_PATH")
    bash = named if named and Path(named).is_file() else (shutil.which("bash") or "bash")

    def run(command: str, cwd: Path) -> tuple[int, str]:
        env = dict(base_env)
        path_name = next((n for n in env if n.upper() == "PATH"), "PATH")
        env[path_name] = os.pathsep.join(str(b) for b in bins) + os.pathsep + env.get(path_name, "")
        env["PYTHONPATH"] = str(Path(cwd) / "src")
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run([bash, "-c", command], cwd=str(cwd), env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=3600)
        return proc.returncode, proc.stdout + proc.stderr
    return run


def flow(python: str, plugin: Path, project: Path, env: Mapping[str, str], *args: str) -> dict:
    """Runs the plugin copy's troy_flow.py with --json in the project and gives its report."""
    proc = subprocess.run([python, str(plugin / "troy-mode" / "flow" / "troy_flow.py"), *args, "--json"],
                          cwd=str(project), env=dict(env), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        raise ExamError(f"troy_flow.py {args[0]}: {proc.stderr.strip()[-400:]}") from exc


def brief_args(case: Case, input_file: Path | None) -> list[str]:
    """The options of `troy_flow.py brief` for the case."""
    args = ["brief", "--task", case.task, "--item", case.item]
    if case.title:
        args += ["--title", case.title]
    if case.round:
        args += ["--round", str(case.round)]
    if input_file is not None:
        args += ["--input-file", str(input_file)]
    return args


def git_dir(project: Path) -> Path:
    """The project's absolute git folder."""
    return Path(git(project, "rev-parse", "--absolute-git-dir").strip())


def write_input(case: Case, project: Path) -> Path | None:
    """Writes the case's Input under <git dir>/troy-mode/flow/, as the entry skill does."""
    text = case.input_text()
    if text is None:
        return None
    folder = git_dir(project) / "troy-mode" / "flow"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "input.md"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def hooks_lines(project: Path, since: str) -> list[dict]:
    """The hooks.log lines written since the snapshot."""
    path = git_dir(project) / "troy-mode" / "hooks.log"
    found = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return found
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and str(entry.get("time", "")) >= since:
            found.append(entry)
    return found


def placeholders(project: Path, plugin: Path) -> dict[str, str]:
    """The run's real paths and their placeholders, in every form a role may write them."""
    found = {}
    for real, name in ((project, "<project>"), (plugin, "<plugin>")):
        text = str(real)
        found[text] = name
        drive = re.match(r"^([A-Za-z]):[\\/](.*)$", text)
        if drive:
            found["/" + drive.group(1).lower() + "/" + drive.group(2).replace("\\", "/")] = name
    return found


def save_outputs(project: Path, start: str, out: Path, report: str | None, files: list[str],
                 replacements: Mapping[str, str] | None = None) -> None:
    """Saves the run's diff, report, and the files the judge sees, with paths as placeholders."""
    from .judge import replace_paths
    swap = replacements or {}
    git(project, "add", "-A", check=False)
    diff = git(project, "diff", "--cached", "--binary", "--no-renames", start, check=False)
    (out / "diff.patch").write_text(replace_paths(diff, swap), encoding="utf-8", newline="\n")
    (out / "report.md").write_text(replace_paths(report or "", swap), encoding="utf-8",
                                   newline="\n")
    tracked = git(project, "ls-files", check=False).splitlines()
    for path in tracked:
        if any(glob_match(path, pattern) for pattern in files) and (project / path).is_file():
            target = out / "files" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            text = (project / path).read_text(encoding="utf-8", errors="replace")
            target.write_text(replace_paths(text, swap), encoding="utf-8", newline="\n")


def _record(spec: RunSpec, **values) -> dict:
    """A run.json record with the run's fixed fields."""
    record = {"run": spec.run_id, "case": spec.case.id, "case_version": spec.case.version,
              "side": spec.side, "commit": spec.commit, "instructions": spec.instructions,
              "cli": spec.cli_version, "effort": spec.case.run.effort, "models": [],
              "status": "ok", "reason": "", "cost": 0.0, "costs": {}, "minutes": 0.0,
              "time": time.strftime(TIME, time.gmtime()), "criteria": {}, "passed": None,
              "driver_model": spec.driver_model, "left": []}
    record.update(values)
    return record


def write_record(out: Path, record: dict) -> None:
    """Writes run.json."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "run.json").write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")


def run_role(spec: RunSpec) -> dict:
    """Runs the case's role once and saves its record in spec.out (design 11.3).

    Raises:
        ExamError: The run cannot start: the brief does not render, or a blinding check hits.
    """
    case, out = spec.case, spec.out
    out.mkdir(parents=True, exist_ok=True)
    folder = new_run_folder(spec.layout, case.start.repository)
    session_folder = None
    try:
        start = build_project(case, folder, spec.mirror)
        copy_plugin(spec.repo, spec.commit, folder.plugin)
        owner = case.start.repository.split("/")[0] if "/" in case.start.repository else ""
        write_gh(folder.bin, spec.python, {"number": case.start.pr,
                                           "title": case.start.title or case.title or "",
                                           "body": "", "repository": case.start.repository,
                                           "author": owner})
        env = child_env(spec.parent_env, python=spec.python, env_prefix=str(spec.env_prefix),
                        project=folder.project, bin_dir=folder.bin, work_root=spec.layout.root)
        input_file = write_input(case, folder.project)
        texts = {"Input": case.input_text() or "",
                 **{f"gh stand-in {p.name}": p.read_text(encoding="utf-8")
                    for p in folder.bin.iterdir() if p.is_file()}}
        names = {"run folder": str(folder.root), "project": str(folder.project),
                 "branch": case.start.branch, "plugin folder": str(folder.plugin),
                 **{f"variable {k}": f"{k}={v}" for k, v in added_variables(env, folder.project).items()}}
        problems = blind_problems(texts, names)
        if problems:
            raise ExamError("blinding: " + "; ".join(problems))
        brief = flow(spec.python, folder.plugin, folder.project, env, *brief_args(case, input_file))
        if not brief.get("ok"):
            raise ExamError(f"{case.id}: the brief does not render: {brief.get('problems')}")
        if input_file is not None:
            input_file.unlink()
        snap = flow(spec.python, folder.plugin, folder.project, env, "snapshot", "--role", case.role)
        if not snap.get("ok"):
            raise ExamError(f"{case.id}: snapshot failed: {snap.get('problems')}")
        session_id = new_session_id()
        session_folder = projects_key_dir(env, folder.project)
        prompt = driver_prompt(case.role, case.run.model, case.run.effort, brief["prompt"])
        command = command_line(spec.cli, prompt, folder.plugin, session_id, case.run.max_cost,
                               spec.driver_model)
        session = run_session(command, folder.project, env, case.run.minutes,
                              out / "stream.jsonl", out / "stream.err", folder.root)
        return _finish(spec, folder, env, brief, snap, start, session_id, session)
    finally:
        left = cleanup([folder.root] + ([session_folder] if session_folder else []))
        if left:
            path = out / "run.json"
            if path.is_file():
                record = json.loads(path.read_text(encoding="utf-8"))
                record["left"] = left
                write_record(out, record)


def _finish(spec, folder, env, brief, snap, start, session_id, session) -> dict:
    """Reads what the session left, grades it, and writes the record."""
    case, out = spec.case, spec.out
    with open(out / "stream.jsonl", encoding="utf-8", errors="replace") as handle:
        stream = read_stream(handle)
    base = dict(cost=round(stream.total_cost, 6), costs=stream.costs, models=sorted(stream.costs),
                minutes=round(session.minutes, 2), session=session_id)
    if session.timed_out:
        record = _record(spec, status="timeout", reason=f"passed its {case.run.minutes}-minute limit",
                         passed=False, **base)
        write_record(out, record)
        return record
    if stream.limit_hit:
        record = _record(spec, status="limit", reason=stream.text or "usage limit", **base)
        write_record(out, record)
        return record
    if not stream.found or (stream.is_error and not stream.cap_hit):
        record = _record(spec, status="void", reason="the CLI failed or wrote no result", **base)
        write_record(out, record)
        return record
    subagents = session_dir(env, folder.project, session_id) / "subagents"
    try:
        transcript = read_role(subagents, AGENT_PREFIX + case.role)
    except ExamError as exc:
        record = _record(spec, status="void", reason=str(exc), **base)
        write_record(out, record)
        return record
    _copy_transcript(subagents, out)
    if not brief_arrived(transcript, brief["prompt"]):
        record = _record(spec, status="void", reason="brief: the role's first message is not the brief",
                         **base)
        write_record(out, record)
        return record
    report = role_report(transcript)
    check = flow(spec.python, folder.plugin, folder.project, env, "check-run", "--run", snap["run"])
    agent = (folder.plugin / "agents" / f"troy-{case.role}.md").read_text(encoding="utf-8")
    work = out / "work"
    work.mkdir(exist_ok=True)
    ctx = RunContext(case=case, project=folder.project, start=start, report=report,
                     transcript=transcript, hooks_log=hooks_lines(folder.project, snap["time"]),
                     check_run=check, leftovers=session.leftovers,
                     agent_file=agent, brief_checks=list(brief.get("checks") or []),
                     mirror=spec.mirror, work=work, env_run=env_runner(spec.env_prefix, env))
    grades = grade(ctx)
    save_outputs(folder.project, start, out, report, case.judge_files,
                 placeholders(folder.project, folder.plugin))
    shutil.rmtree(work, ignore_errors=True)
    criteria = {k: {"passed": v.passed, "evidence": v.evidence} for k, v in grades.items()}
    status = "cap" if stream.cap_hit else "ok"
    musts = [c.id for c in case.criteria if c.must and c.check is not None]
    scripts_pass = all(criteria[k]["passed"] for k in (*UNIVERSAL_MUSTS, *musts))
    needs_judge = any(c.judge is not None and c.must for c in case.criteria)
    passed = False if status == "cap" or not scripts_pass else (None if needs_judge else True)
    record = _record(spec, status=status, reason="hit its cap" if status == "cap" else "",
                     criteria=criteria, passed=passed, check_run_ok=bool(check.get("ok")), **base)
    write_record(out, record)
    return record


def _copy_transcript(subagents: Path, out: Path) -> None:
    """Keeps the role's transcripts and their meta files in the results."""
    target = out / "transcripts"
    target.mkdir(exist_ok=True)
    for path in subagents.glob("agent-*"):
        shutil.copyfile(path, target / path.name)


def anchor_context(case: Case, layout: Layout, mirror: Path, env_prefix: Path, kind: str,
                   parent_env: Mapping[str, str], work: Path,
                   engine: Path | None = None) -> tuple[RunContext, Path]:
    """Builds the case's project with an anchor's diff applied, for grading by script.

    Args:
        engine: A tstack checkout whose troy_flow.py renders the brief's checks for
            pack_steps_pass; None leaves them empty.

    Returns:
        The context, and the run folder to delete afterwards.
    """
    folder = new_run_folder(layout, case.start.repository)
    start = build_project(case, folder, mirror)
    checks: list[str] = []
    if engine is not None:
        env = dict(parent_env, TROY_MODE_ENV_PREFIX=str(env_prefix))
        input_file = write_input(case, folder.project)
        brief = flow(sys.executable, Path(engine), folder.project, env, *brief_args(case, input_file))
        if input_file is not None:
            input_file.unlink()
        checks = list(brief.get("checks") or []) if brief.get("ok") else []
    patch = case.anchor(kind) / "diff.patch"
    if patch.stat().st_size:
        git(folder.project, "apply", "--cached", "--whitespace=nowarn", str(patch))
        git(folder.project, "checkout-index", "--all", "--force")
        git(folder.project, "reset", "--quiet")
    report = (case.anchor(kind) / "report.md").read_text(encoding="utf-8")
    env = dict(parent_env)
    work.mkdir(parents=True, exist_ok=True)
    ctx = RunContext(case=case, project=folder.project, start=start, report=report,
                     mirror=mirror, work=work, env_run=env_runner(env_prefix, env),
                     brief_checks=checks)
    return ctx, folder.root
