"""Command-line interface: options, the six commands, and the report (F07 design 3.1)."""

import argparse
import json
import sys

from troycheck.gitio import GitError

from . import approve, brief, runs, status, textcheck
from .errors import FlowError

EXIT_ERROR = 2


class _Parser(argparse.ArgumentParser):
    """An argument parser that raises FlowError in place of exiting, so errors go one way."""

    def error(self, message: str):
        """Raises FlowError with argparse's message."""
        raise FlowError(message)


def _positive(text: str) -> int:
    """Parses --round: a whole number of 1 or more."""
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"{text!r} is not a whole number of 1 or more")
    return int(text)


def _common(parser: argparse.ArgumentParser) -> None:
    """Adds --repo and --json."""
    parser.add_argument("--repo", help="the project folder (default: the current folder)")
    parser.add_argument("--json", action="store_true", help="print the JSON report")


def build_parser() -> argparse.ArgumentParser:
    """Builds the parser for the six commands (design 3.1)."""
    parser = _Parser(prog="troy_flow.py", description="troy-mode's flow engine.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    cmd = sub.add_parser("status", help="the state, the next action, and the progress file")
    cmd.add_argument("--write-progress", action="store_true")
    cmd.add_argument("--waiting", help="what waits on Troy; an empty text clears it")
    cmd.add_argument("--note", action="append", help="a note for the progress file")
    cmd = sub.add_parser("brief", help="the brief for one role run")
    cmd.add_argument("--task", required=True)
    cmd.add_argument("--item")
    cmd.add_argument("--round", type=_positive)
    cmd.add_argument("--input-file")
    cmd = sub.add_parser("snapshot", help="record the state before a role run")
    cmd.add_argument("--role", action="append", required=True, choices=runs.ROLES)
    cmd = sub.add_parser("check-run", help="check a role run against its snapshot")
    cmd.add_argument("--run", required=True)
    cmd.add_argument("--allow-dependency", action="append")
    cmd = sub.add_parser("approve", help="record Troy's approval in a document's header")
    cmd.add_argument("--doc", required=True)
    cmd.add_argument("--date")
    cmd = sub.add_parser("check-text", help="check a PR comment for attribution (R19)")
    cmd.add_argument("--file", required=True)
    for name in ("status", "brief", "snapshot", "check-run", "approve", "check-text"):
        _common(sub.choices[name])
    return parser


def _text(report: dict) -> str:
    """Renders a report as text for a person."""
    if report["command"] == "brief" and report.get("ok"):
        agent = ", ".join(f"{k}={v}" for k, v in report["agent"].items())
        return f"Agent: {agent}\n\n{report['prompt']}"
    lines = [f"troy-flow {report['command']}: {'ok' if report['ok'] else 'stopped'}"]
    if report["command"] == "status":
        lines.append(f"next      {status.action_text(report['next'])}")
        if report.get("waiting_on_troy"):
            lines.append(f"waiting   {report['waiting_on_troy']}")
    for key in ("run", "stage"):
        if report.get(key):
            lines.append(f"{key:<9} {report[key]}")
    lines += [f"problem   {p if isinstance(p, str) else p.get('message')}"
              for p in report.get("problems", [])]
    lines += [f"note      {n}" for n in report.get("notes", [])]
    return "\n".join(lines) + "\n"


def _utf8_stdio() -> None:
    """Makes stdout and stderr UTF-8 whatever the console code page."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


COMMANDS = {"status": status.run_status, "brief": brief.build, "snapshot": runs.snapshot,
            "check-run": runs.check_run, "approve": approve.run_approve,
            "check-text": textcheck.run_check_text}


def main(argv: list[str]) -> int:
    """Runs one command.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        0 when done, 1 when a problem stops the step, and 2 when the engine
        could not run.
    """
    _utf8_stdio()
    try:
        args = build_parser().parse_args(argv)
        report, code = COMMANDS[args.command](args)
    except (FlowError, GitError, OSError) as exc:
        print(f"troy-flow: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(_text(report))
    return code
