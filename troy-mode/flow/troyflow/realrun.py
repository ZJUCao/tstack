"""real-run: replays the prototypes' transcripts on the real program (F12 design 5).

It picks the prototypes from the requirements at HEAD, runs each in a new
scratch folder (realexec), compares the output with the prototype, decides
the feature's label, and writes the report and the PR evidence (realreport).
It never commits, pushes, or writes to GitHub (F07 D57), and writes nothing
outside the scratch folder but its report in the git folder.
"""

import json
import platform
import posixpath
import re
import tempfile
import tomllib
from datetime import datetime
from pathlib import Path

from . import github, realreport
from . import repo as git
from .errors import FlowError
from .realexec import NOT_RUN, Item, Run, env_python_version, remove, run_prototype
from .requirements import FEATURE_ID, parse_features
from .stages import merged_stages

RAN_FOR_REAL = "Ran for real on Troy's PC"
PASSES_TESTS = "Passes tests on main"
REQUIREMENTS = "docs/requirements.md"
PROTOTYPES = "docs/prototypes"


def _cells(line: str) -> list[str]:
    """Splits one Markdown table row into trimmed cells without backticks."""
    return [c.strip().replace("`", "").strip() for c in line.strip().strip("|").split("|")]


def _file_cell(cell: str) -> str:
    """The repository path in a File cell: a path, or a Markdown link's target."""
    link = re.search(r"\]\(([^)\s]+)\)", cell)
    if link:
        return posixpath.normpath(posixpath.join(posixpath.dirname(REQUIREMENTS), link.group(1)))
    return cell.strip().removeprefix("./")


def prototype_table(text: str | None) -> list[Item] | None:
    """Reads the requirements' prototypes table: Prototype, Feature, and File (design 5.2).

    Returns:
        One item per row, or None when there is no such table.
    """
    lines = (text or "").replace("\r\n", "\n").split("\n")
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        names = [c.lower() for c in _cells(line)]
        if not all(n in names for n in ("prototype", "feature", "file")):
            continue
        feature, path = names.index("feature"), names.index("file")
        items = []
        for row in lines[index + 2:]:
            if not row.strip().startswith("|"):
                break
            cells = _cells(row)
            if max(feature, path) < len(cells) and cells[path]:
                items.append(Item(_file_cell(cells[path]), FEATURE_ID.findall(cells[feature])))
        return items
    return None


def choose(repo, table: list[Item] | None, wanted: set[str]) -> list[Item]:
    """The prototypes to run: rows that name a wanted feature, or the file names (design 5.2)."""
    if table is not None:
        return [i for i in table if i.file.endswith(".md") and wanted & set(i.features)]
    names = sorted(git.files(repo, "HEAD", PROTOTYPES))
    found = []
    for fid in sorted(wanted):
        pattern = re.compile(rf"{re.escape(PROTOTYPES)}/{fid}-[^/]*\.md")
        found += [Item(n, [fid]) for n in names if pattern.fullmatch(n)]
    return found


def _scripts(repo) -> dict[str, str]:
    """The console scripts of pyproject.toml's [project.scripts] at HEAD."""
    text = git.read(repo, "HEAD", "pyproject.toml")
    try:
        data = tomllib.loads(text) if text else {}
    except tomllib.TOMLDecodeError:
        return {}
    project = data.get("project")
    scripts = project.get("scripts") if isinstance(project, dict) else None
    return {k: v for k, v in scripts.items() if isinstance(v, str)} \
        if isinstance(scripts, dict) else {}


def _accepted(repo) -> set[str]:
    """Features whose PR 6 is in HEAD's history."""
    subjects = [s for _, s in git.log(repo, "HEAD")]
    return {fid for fid, done in merged_stages(subjects).items() if 6 in done}


def _counts(entries: list[dict]) -> dict:
    """Counts results: matches, mismatch, waits, and not run. A file check counts too."""
    counts = {"matches": 0, "mismatch": 0, "waits": 0, "not_run": 0}
    for entry in entries:
        result = entry["result"]
        counts["waits" if result.startswith("waits for") else
               "not_run" if result == NOT_RUN else result] += 1
    return counts


def _label(item: str, commands: list[dict], mine: list[dict], failed: bool) -> tuple:
    """The feature's label and why (design 9, D109)."""
    if failed:
        return None, "The run has mismatches or problems, so the feature is not accepted yet."
    own = [c for c in commands if c["own"]]
    if not own:
        if mine:
            return PASSES_TESTS, f"Every command of {item}'s own prototypes waits for a later " \
                                 "feature."
        return PASSES_TESTS, f"{item} has no transcript of its own."
    stopped = [c for c in own if c["result"] != "matches"]
    if stopped:
        first = stopped[0]
        return PASSES_TESTS, f"{len(stopped)} of {item}'s own commands did not run, for " \
                             f"example {first['typed']!r}: {first['reason'] or first['result']}."
    return RAN_FOR_REAL, f"All {len(own)} of {item}'s own commands ran on Troy's PC and matched."


def _next_number(folder: Path, stem: str) -> int:
    """The next free run number of a report's name."""
    taken = [int(m.group(1)) for p in folder.glob(f"{stem}-*.json")
             if (m := re.fullmatch(re.escape(stem) + r"-(\d+)\.json", p.name))]
    return max(taken, default=0) + 1


def _system() -> str:
    """The system's name and version."""
    return f"{platform.system()} {platform.release()} ({platform.version()})"


def _new_report(args, repo) -> dict:
    """The report's fields before the run."""
    return {"command": "real-run", "ok": False, "notes": [], "problems": [],
            "item": args.item, "all": bool(args.all), "commit": git.commit_of(repo, "HEAD"),
            "base": git.commit_of(repo, git.MAIN), "program": None, "system": _system(),
            "date": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z"),
            "prototypes": [], "counts": None, "summary": "", "label": None, "label_reason": "",
            "out_of_date": [], "open_bugs": None, "run_files": {}, "description": "",
            "comments": [], "files": None, "scratch": None}


def run_real_run(args) -> tuple[dict, int]:
    """Runs the prototypes' transcripts on the real program (design 5).

    Args:
        args: Parsed options: item, all, keep, and repo.

    Returns:
        The report and the exit code: 0 when every command that ran matched
        and there is no problem, 1 otherwise.

    Raises:
        FlowError: Bad options, not a repository, or an invalid config at HEAD.
    """
    if bool(args.item) == bool(args.all):
        raise FlowError("give exactly one of --item <feature ID> and --all")
    if args.item and not FEATURE_ID.fullmatch(args.item):
        raise FlowError(f"--item {args.item!r} is not a feature ID")
    repo = git.need_repo(args.repo)
    config = git.config_at(repo, "HEAD")
    report = _new_report(args, repo)
    dirty = [path for _, path in git.changed_paths(repo)]
    if dirty:
        report["problems"] = [{"kind": "dirty-tree", "message": "The working tree has changes "
                               f"that are not committed: {', '.join(dirty[:5])}. The evidence "
                               "names a commit, so commit or remove them first."}]
        return _finish(repo, report), 1
    requirements = git.read(repo, "HEAD", REQUIREMENTS)
    known = {f.id for f in parse_features(requirements) or []}
    if args.item and args.item not in known:
        report["problems"] = [{"kind": "unknown-feature", "message": f"{args.item} is not in the "
                               f"features table of {REQUIREMENTS} at HEAD."}]
        return _finish(repo, report), 1
    run = Run(repo, args.item, _accepted(repo), known, _scripts(repo), config,
              Path(tempfile.mkdtemp(prefix="troy-real-run-")), report["notes"])
    items = choose(repo, prototype_table(requirements),
                   run.accepted | ({args.item} if args.item else set()))
    try:
        run.add_hidden(repo.root, "<checkout>")
        report["prototypes"] = [run_prototype(run, item) for item in items]
    finally:
        if args.keep:
            report["scratch"] = str(run.scratch)
        else:
            remove(run.scratch)
    return _complete(run, report, items)


def _complete(run: Run, report: dict, items: list[Item]) -> tuple[dict, int]:
    """Counts, labels, and renders the report."""
    commands, mine = [], []
    for proto, item in zip(report["prototypes"], items):
        for section in proto["sections"]:
            commands += section["commands"]
            if run.item in item.features:
                mine += section["commands"]
    report["counts"] = {"all": _counts(commands),
                        "own": _counts([c for c in commands if c["own"]]) if run.item else None}
    report["problems"] = run.problems
    report["out_of_date"] = run.out_of_date
    report["notes"] += [f"The later mark for {m['feature']} in {m['prototype']}, section "
                        f"{m['section']!r}, is out of date: delete it." for m in run.out_of_date]
    failed = bool(run.problems or any(c["result"] == "mismatch" for c in commands))
    if run.item:
        report["label"], report["label_reason"] = _label(run.item, commands, mine, failed)
    if run.scripts and run.python is None:
        run.python = env_python_version(run)
    report["program"] = {"environment": run.env_name,
                         "prefix": str(run.prefix) if run.prefix else None,
                         "python": run.python, "names": sorted(run.used)}
    report["open_bugs"] = _open_bugs(run, report["notes"])
    report["run_files"] = {p["run_file"]: git.git(run.repo, "rev-parse",
                                                  f"HEAD:{p['run_file']}").strip()
                           for p in report["prototypes"] if p["run_file"]}
    report["ok"] = not failed
    report["summary"] = realreport.result_line(report)
    return _finish(run.repo, report), 1 if failed else 0


def _open_bugs(run: Run, notes: list[str]) -> list[dict] | None:
    """Open bug issues of earlier real runs of this feature (design 7.3)."""
    prefix = f"Real run of {run.item}:" if run.item else "Real run of "
    try:
        return [b for b in github.open_bugs(run.repo)
                if str(b.get("title") or "").startswith(prefix)]
    except FlowError as exc:
        notes.append(f"Could not read the open bug issues: {exc}")
        return None


def _finish(repo, report: dict) -> dict:
    """Renders the evidence and writes the report files in the git folder."""
    report["description"], report["comments"] = realreport.description(
        report, realreport.changes(repo, report))
    folder = repo.state_dir() / "flow"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"real-run-{report['item'] or 'all'}"
    number = _next_number(folder, stem)
    paths = {"json": folder / f"{stem}-{number}.json", "md": folder / f"{stem}-{number}.md"}
    report["files"] = {k: str(v) for k, v in paths.items()}
    paths["md"].write_text(realreport.markdown(report), encoding="utf-8", newline="\n")
    paths["json"].write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8", newline="\n")
    return report
