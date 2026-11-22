"""Command-line interface: options, the commands, and the report (F07, F08, F09 3.1, F12 5.1).

F07 D204 adds wait-checks, the wait for a pushed head's CI checks before a merge.
F07 D264 to D267 add costs, a feature's or a version's role runs and their cost.
"""

import argparse
import json
import sys

from troycheck.gitio import GitError

from . import acceptversion, approve, brief, costs, issuesync, realreport, realrun, \
    releasetest, retro, rulerow, runs, series, skips, status, textcheck, waitchecks
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


def _seconds(text: str) -> float:
    """Parses a time option: a number of seconds, 0 or more."""
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds") from None
    if not value >= 0 or value == float("inf"):
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds, 0 or more")
    return value


def _common(parser: argparse.ArgumentParser) -> None:
    """Adds --repo and --json."""
    parser.add_argument("--repo", help="the project folder (default: the current folder)")
    parser.add_argument("--json", action="store_true", help="print the JSON report")


def build_parser() -> argparse.ArgumentParser:
    """Builds the parser for F07's nine commands, F08's four, F09's two, and F12's one."""
    parser = _Parser(prog="troy_flow.py", description="troy-mode's flow engine.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    cmd = sub.add_parser("status", help="the state, the next action, and the progress file")
    cmd.add_argument("--write-progress", action="store_true")
    cmd.add_argument("--waiting", help="what waits on Troy; an empty text clears it")
    cmd.add_argument("--note", action="append", help="a note for the progress file")
    cmd = sub.add_parser("brief", help="the brief for one role run")
    cmd.add_argument("--task", required=True)
    cmd.add_argument("--item")
    cmd.add_argument("--title", help="the PR title, for a bug PR, a side PR, or a redo")
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
    cmd = sub.add_parser("check-skips", help="local failures that are only skipped tests (D69)")
    cmd.add_argument("--report", required=True, help="troy-check code's JSON report")
    cmd.add_argument("--junit", action="append", required=True, help="a JUnit XML file")
    sub.add_parser("series", help="plan the series lock after a dependency change (D66)")
    cmd = sub.add_parser("release-test", help="the release test's report and comment (F08)")
    cmd.add_argument("--version", required=True, help="the version, for example v0.1")
    cmd.add_argument("--junit", action="append", required=True, help="a JUnit XML file")
    cmd.add_argument("--real-run", help="the JSON report of real-run --all (F12)")
    cmd = sub.add_parser("accept-version", help="record Troy's acceptance of a version (F08)")
    cmd.add_argument("--tag", required=True, help="the tag, for example v0.1.0")
    cmd.add_argument("--notes-file", required=True, help="Troy's notes")
    cmd.add_argument("--date")
    cmd = sub.add_parser("release-notes", help="write the tag's changelog section (F08)")
    cmd.add_argument("--tag", required=True)
    cmd.add_argument("--out", required=True)
    cmd = sub.add_parser("retro", help="gather the evidence for a retrospective (F08)")
    cmd.add_argument("--tag", required=True)
    sub.add_parser("rule-id", help="the next free P ID, the P rules, and their baselines (F09)")
    cmd = sub.add_parser("rule-row", help="write one P row into the rules table (F09)")
    cmd.add_argument("--id", required=True, help="the P ID, for example P01")
    cmd.add_argument("--rule-file", required=True, help="the row's cells and change-log text")
    cmd.add_argument("--retire", action="store_true", help="retire the rule")
    cmd.add_argument("--date")
    cmd = sub.add_parser("real-run", help="run the prototypes on the real program (F12)")
    which = cmd.add_mutually_exclusive_group(required=True)
    which.add_argument("--item", help="the feature being accepted")
    which.add_argument("--all", action="store_true", help="every accepted feature (release)")
    cmd.add_argument("--keep", action="store_true", help="keep the scratch folder")
    cmd = sub.add_parser("wait-checks", help="wait for every CI check of a PR's head (D204)")
    cmd.add_argument("--pr", required=True, help="the PR number")
    cmd.add_argument("--sha", required=True, help="the full commit ID that was pushed")
    cmd.add_argument("--timeout", type=_seconds, help="seconds to wait at most (540)")
    cmd.add_argument("--interval", type=_seconds, help="seconds between reads (15)")
    cmd.add_argument("--settle", type=_seconds, help="seconds a pass must hold (30)")
    cmd = sub.add_parser("issues", help="the changes to troy-mode's issues (F15)")
    cmd.add_argument("--device-test-scenarios",
                     help="a patch release's scenarios for its checklist, separated by commas")
    cmd = sub.add_parser("costs", help="a feature's or a version's role runs and cost (D264)")
    cmd.add_argument("--item", help="the feature, bug, or other item, for example F04")
    cmd.add_argument("--tag", help="the version's tag, for example v0.1.0")
    cmd.add_argument("--until", help="count up to this ISO 8601 time instead")
    cmd.add_argument("--transcripts", action="append",
                     help="a transcript folder to read instead of this project's")
    for name in ("status", "brief", "snapshot", "check-run", "approve", "check-text",
                 "check-skips", "series", "release-test", "accept-version", "release-notes",
                 "retro", "rule-id", "rule-row", "real-run", "issues", "wait-checks", "costs"):
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
    if report["command"] == "rule-id" and report.get("ok"):
        lines.append(f"next      {report['next_id']}")
        lines += [f"rule      {r['id']}{' (retired)' if r['retired'] else ''}: "
                  f"{len(r['baseline'])} baseline lines" for r in report["rules"]]
        if report.get("waiting_on_troy"):
            lines.append(f"waiting   {report['waiting_on_troy']}")
    if report["command"] == "real-run":
        lines.append(f"result    {realreport.result_line(report)}")
        if report.get("label"):
            lines.append(f"label     {report['label']}: {report['label_reason']}")
        if report.get("files"):
            lines.append(f"report    {report['files']['md']}")
    if report["command"] == "wait-checks":
        lines.append(f"result    {report['result']}")
    if report["command"] == "costs":
        lines.append(f"cost      {report['line']}")
    if report["command"] == "issues":
        lines += [f"label     {item['command']}" for item in report.get("labels", [])]
        lines += [f"action    {item['command']}" for item in report.get("actions", [])]
        lines += [f"skipped   {item}" for item in report.get("skipped", [])]
    for key in ("run", "stage", "stop"):
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
            "check-text": textcheck.run_check_text, "check-skips": skips.run_check_skips,
            "series": series.run_series, "release-test": releasetest.run_release_test,
            "accept-version": acceptversion.run_accept_version,
            "release-notes": acceptversion.run_release_notes, "retro": retro.run_retro,
            "rule-id": rulerow.run_rule_id, "rule-row": rulerow.run_rule_row,
            "real-run": realrun.run_real_run, "issues": issuesync.run_issues,
            "wait-checks": waitchecks.run_wait_checks, "costs": costs.run_costs}


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
