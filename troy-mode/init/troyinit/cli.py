"""Command-line interface: option parsing and the setup, lang, and upgrade steps."""

import argparse
import datetime
import re
import sys
from pathlib import Path

from .errors import InitError
from .gitops import toplevel
from .plan import Plan, apply
from .plugin import load_plugin
from .report import to_json, to_text
from .setup import SetupOptions, plan_setup
from .upgrade import plan_upgrade

EXIT_OK = 0
EXIT_STOPPED = 1
EXIT_ERROR = 2

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+")


def _date(value: str) -> str:
    """Checks a --date value, YYYY-MM-DD and a real day."""
    try:
        if _DATE.fullmatch(value):
            datetime.date.fromisoformat(value)
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f"not a date in the form YYYY-MM-DD: {value!r}")


def _email(value: str) -> str:
    """Checks an --email value."""
    if not _EMAIL.fullmatch(value):
        raise argparse.ArgumentTypeError(f"not an email address: {value!r}")
    return value


def _add_common(parser: argparse.ArgumentParser) -> None:
    """Adds the options every step takes (design 3.2)."""
    parser.add_argument("--repo", type=Path, help="the project's root (default: this folder)")
    parser.add_argument("--date", type=_date, help="the date written into files (default today)")
    parser.add_argument("--replace", action="append", default=[], metavar="PATH",
                        help="a file troy-init may overwrite although it did not write it")
    parser.add_argument("--dry-run", action="store_true", help="check and plan only")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")


def build_parser() -> argparse.ArgumentParser:
    """Builds the parser for every step (design 3.2).

    Returns:
        The argument parser. It exits with code 2 on bad options.
    """
    parser = argparse.ArgumentParser(prog="troy-init", description="troy-mode project init.")
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="make this folder a troy-mode project")
    setup.add_argument("--project-name", help="default: the repository folder's name")
    setup.add_argument("--email", required=True, type=_email, help="the commit email (R19)")
    _add_common(setup)
    lang = sub.add_parser("lang", help="add a language pack (F06 part 2)")
    lang.add_argument("language", choices=("python", "cpp"))
    for option in ("--environment", "--package", "--mamba", "--env-prefix"):
        lang.add_argument(option)
    lang.add_argument("--series", action="append", default=[])
    lang.add_argument("--no-env", action="store_true")
    _add_common(lang)
    _add_common(sub.add_parser("upgrade", help="bring troy-mode's files up to date"))
    return parser


def _plan(args: argparse.Namespace, repo: Path, top: Path, plugin_root: Path) -> Plan:
    """Plans the step the command line names.

    Raises:
        InitError: The step cannot run.
    """
    plugin = load_plugin(plugin_root)
    date = args.date or datetime.date.today().isoformat()
    replace = [p.replace("\\", "/").removeprefix("./") for p in args.replace]
    if args.command == "setup":
        options = SetupOptions(args.project_name or top.name, args.email, date, replace)
        return plan_setup(plugin, repo, top, options)
    if args.command == "upgrade":
        return plan_upgrade(plugin, repo, top, date, replace)
    raise InitError("the language step is not built yet; it comes with F06 part 2")


def run(args: argparse.Namespace, plugin_root: Path) -> int:
    """Plans the step, applies it unless stopped or a dry run, and prints the report.

    Args:
        args: Parsed options.
        plugin_root: The troy-pstack folder to copy from.

    Returns:
        0 when done, 1 when stopped before changing anything.

    Raises:
        InitError: The step cannot run.
    """
    repo = (args.repo or Path.cwd()).resolve()
    top = toplevel(repo)
    if top is None:
        raise InitError(f"{repo} is not in a git repository")
    plan = _plan(args, repo, top, plugin_root)
    if not plan.blocked and not args.dry_run:
        apply(repo, plan)
    sys.stdout.write(to_json(plan, args.dry_run) if args.json else to_text(plan, args.dry_run))
    return EXIT_STOPPED if plan.blocked else EXIT_OK


def _utf8_stdio() -> None:
    """Makes stdout and stderr UTF-8 whatever the console code page."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None, plugin_root: Path | None = None) -> int:
    """Runs troy-init's engine.

    Args:
        argv: Command-line arguments without the program name.
        plugin_root: The troy-pstack folder to copy from. Default: the one
            that holds this engine.

    Returns:
        0 when done or a dry run found nothing in the way, 1 when stopped
        before changing anything, and 2 when the engine cannot run: bad
        options, not a git repository, or a git error.
    """
    _utf8_stdio()
    args = build_parser().parse_args(argv)
    try:
        return run(args, plugin_root or PLUGIN_ROOT)
    except InitError as exc:
        print(f"troy-init: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
