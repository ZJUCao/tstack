"""The exam's command line (design 11.2)."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import climb
from .errors import ExamError
from .paths import Layout, work_root

EXIT_ERROR = 2
HERE = Path(__file__).resolve().parent


class _Parser(argparse.ArgumentParser):
    """A parser that raises ExamError in place of exiting."""

    def error(self, message: str):
        """Raises ExamError with argparse's message."""
        raise ExamError(message)


def _jobs(text: str) -> int:
    """Parses --jobs: 1 or more."""
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"{text!r} is not a whole number of 1 or more")
    return int(text)


def build_parser() -> argparse.ArgumentParser:
    """The parser of the seven commands."""
    parser = _Parser(prog="troy_exam.py", description="troy-mode's role exam.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    cmd = sub.add_parser("affected", help="the cases a change affects, with no model call")
    cmd.add_argument("--base", required=True)
    cmd.add_argument("--head")
    cmd = sub.add_parser("run", help="the exam of a change: old against new")
    cmd.add_argument("--base", required=True)
    cmd.add_argument("--head")
    cmd.add_argument("--fixes", action="append", help="a case the change fixes")
    cmd.add_argument("--jobs", type=_jobs, default=2)
    cmd.add_argument("--case", action="append", help="run this case, affected or not")
    cmd.add_argument("--yes", action="store_true", help="Troy's yes for an estimate above $60")
    cmd = sub.add_parser("prove", help="prove cases: their anchors and five runs")
    cmd.add_argument("cases", nargs="+")
    cmd.add_argument("--ref", help="the version whose roles run (default: origin/main)")
    cmd.add_argument("--anchors", action="store_true", help="grade only the anchors")
    cmd.add_argument("--jobs", type=_jobs, default=2)
    for name in ("resume", "report", "block"):
        cmd = sub.add_parser(name)
        cmd.add_argument("exam")
    cmd = sub.add_parser("log", help="add a row to a hillclimb's decision log")
    cmd.add_argument("name")
    for option in ("--id", "--hypothesis", "--change", "--before", "--after", "--gate", "--verdict"):
        cmd.add_argument(option, required=True)
    cmd.add_argument("--delta")
    cmd.add_argument("--note", default="")
    for name, choice in sub.choices.items():
        choice.add_argument("--repo", help="the tstack checkout (default: the one holding troy_exam.py)")
        choice.add_argument("--cases", dest="cases_dir", help="the cases folder")
        choice.add_argument("--json", action="store_true")
        if name in ("run", "prove", "affected", "resume"):
            choice.add_argument("--env", help="use this environment prefix as is")
    return parser


def _repo_root(args) -> Path:
    """The tstack checkout: --repo, else the one holding troy_exam.py."""
    return Path(args.repo).resolve() if args.repo else HERE.parent.parent.parent


def _affected(args, layout: Layout, env: dict) -> tuple[dict, int]:
    """Lists the cases a change affects."""
    from .affected import affected
    from .cases import load_cases
    from .exam import resolve
    from .project import git
    repo = Path(args.repo_path)
    head = resolve(repo, args.head or "HEAD")
    base = git(repo, "merge-base", resolve(repo, args.base), head).strip()
    found = affected(repo, base, head, load_cases(Path(args.cases_path)), layout,
                     dict(env, TROY_MODE_ENV_PREFIX=args.env or env.get("TROY_MODE_ENV_PREFIX", "")))
    hit = [r for r in found if r["affected"]]
    return {"command": "affected", "ok": True, "base": base, "head": head, "cases": found,
            "affected": [r["case"] for r in hit],
            "result": "no case affected" if not hit else f"{len(hit)} affected"}, 0


def _saved(args, layout: Layout) -> dict:
    """An exam's saved state."""
    path = layout.result(args.exam) / "state.json"
    if not path.is_file():
        raise ExamError(f"no exam {args.exam} in {layout.results}")
    return json.loads(path.read_text(encoding="utf-8"))


def _report_cmd(args, layout: Layout, env: dict) -> tuple[dict, int]:
    """Prints an exam's report."""
    state = _saved(args, layout)
    path = layout.result(args.exam) / "report.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return {"command": "report", "ok": True, "exam": args.exam, "status": state.get("status"),
            "text": text}, 0


def _block_cmd(args, layout: Layout, env: dict) -> tuple[dict, int]:
    """Prints an exam's PR section."""
    from .report import block
    state = _saved(args, layout)
    if "summary" not in state:
        raise ExamError(f"exam {args.exam} has not finished ({state.get('status')})")
    return {"command": "block", "ok": True, "exam": args.exam, "text": block(state["summary"])}, 0


def _log_cmd(args, layout: Layout, env: dict) -> tuple[dict, int]:
    """Adds a hillclimb row."""
    row = {"id": args.id, "hypothesis": args.hypothesis, "change": args.change,
           "before": args.before, "after": args.after, "gate": args.gate, "verdict": args.verdict,
           "note": args.note}
    try:
        row["delta"] = args.delta if args.delta is not None else str(int(args.after) - int(args.before))
    except ValueError:
        row["delta"] = ""
    try:
        climb.add_row(layout.climb_log(args.name), row)
    except ValueError as exc:
        raise ExamError(str(exc)) from exc
    return {"command": "log", "ok": True, "log": str(layout.climb_log(args.name))}, 0


def _text(report: dict) -> str:
    """A report for a person."""
    if report.get("text") is not None:
        return report["text"]
    if report.get("block"):
        return report["block"]
    lines = [f"troy-exam {report['command']}: {'ok' if report.get('ok') else 'stopped'}"]
    if report["command"] == "affected":
        for row in report["cases"]:
            lines.append(f"{row['case']:<20} {'affected' if row['affected'] else 'not affected'}"
                         + (f": {'; '.join(row['why'])}" if row["why"] else ""))
        lines.append(f"result    {report['result']}")
    for key in ("exam", "estimate", "status", "log"):
        if report.get(key) is not None:
            lines.append(f"{key:<9} {report[key]}")
    lines += [f"problem   {p}" for p in report.get("problems", [])]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    """Runs one command.

    Returns:
        0 when done (run: passed), 1 when the exam failed, 2 when it could not run.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    env = dict(os.environ)
    try:
        args = build_parser().parse_args(argv)
        args.repo_path = _repo_root(args)
        args.cases_path = Path(args.cases_dir).resolve() if args.cases_dir \
            else args.repo_path / "troy-mode" / "exam" / "cases"
        layout = Layout(work_root(env))
        from . import exam
        commands = {"affected": _affected, "run": exam.run_exam, "prove": exam.prove,
                    "resume": exam.resume, "report": _report_cmd, "block": _block_cmd,
                    "log": _log_cmd}
        report, code = commands[args.command](args, layout, env)
    except (ExamError, OSError) as exc:
        print(f"troy-exam: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    else:
        sys.stdout.write(_text(report))
    return code
