"""Command-line interface: option parsing and the pr, code, and commit subcommands."""

import argparse
import sys
from pathlib import Path

from . import gitio
from .attribution import check_commit, check_r19, clean_commit_message
from .classify import ALLOWED
from .config import CONFIG_PATH, ConfigError, parse_config
from .context import PrContext
from .covreport import check_r11
from .cppadapter import AdapterError
from .gitio import GitError
from .modules import check_r07
from .markers import check_r20
from .mirrors import check_r12
from .pr_rules import check_r01, check_r02, check_r16
from .report import Result, is_ok, render_json, render_text, write_github_outputs
from .shape import check_r04, check_r05, check_r06, load_code
from .size import check_r03
from .summary import check_r22
from .testpolicy import check_r09, check_r10, load_run
from .titles import describe, parse_title
from .worktree import worktree_commit

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_ERROR = 2

PR_CHECKS = (check_r01, check_r02, check_r03, check_r12, check_r16, check_r19, check_r20,
             check_r22)


class UsageError(Exception):
    """Raised when an input file named on the command line cannot be read."""


def _add_pr_options(parser: argparse.ArgumentParser) -> None:
    """Adds the options that the pr and code subcommands share."""
    parser.add_argument("--base", required=True, help="target branch or commit")
    parser.add_argument("--head", help="the PR's last commit (default HEAD)")
    parser.add_argument("--title", required=True, help="the PR title")
    parser.add_argument("--body-file", help="UTF-8 file with the PR description")
    parser.add_argument("--repo", help="repository root (default: from the current folder)")
    parser.add_argument("--json", action="store_true", help="print the JSON report")


def build_parser() -> argparse.ArgumentParser:
    """Builds the parser for every subcommand (F02 design 3, F03 design 3).

    Returns:
        The argument parser. It exits with code 2 on bad options.
    """
    parser = argparse.ArgumentParser(prog="troy-check", description="troy-mode's checks.")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_pr_options(sub.add_parser("pr", help="check a whole PR"))
    code = sub.add_parser("code", help="check the language rules for a PR")
    _add_pr_options(code)
    code.add_argument("--junit", action="append", default=[], help="JUnit XML from the tests")
    code.add_argument("--coverage", action="append", default=[], help="Cobertura XML coverage")
    code.add_argument("--doc-warnings", help="C/C++ only: Doxygen's warning log (R05)")
    code.add_argument("--worktree", action="store_true",
                      help="check the working tree as if it were committed on HEAD")
    commit = sub.add_parser("commit", help="check one commit before it is made (R19)")
    message = commit.add_mutually_exclusive_group(required=True)
    message.add_argument("--message-file", help="file with the commit message")
    message.add_argument("--message", help="the commit message")
    commit.add_argument("--email", help="author email (default: from git var GIT_AUTHOR_IDENT)")
    commit.add_argument("--repo", help="repository root (default: from the current folder)")
    commit.add_argument("--json", action="store_true", help="print the JSON report")
    return parser


def _read_text(path: str | Path) -> str:
    """Reads a UTF-8 file named on the command line, raising UsageError on failure."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError(f"cannot read {path}: {exc}") from exc


def _root(repo: str | None) -> Path:
    """Finds the repository root from --repo or the current folder."""
    return gitio.repo_root(Path(repo) if repo else Path.cwd())


def build_pr_context(args: argparse.Namespace) -> PrContext:
    """Gathers everything the PR checks need.

    The config is read from the merge-base commit, so a PR cannot loosen the
    rules that judge it.

    Args:
        args: Parsed options of the pr subcommand.

    Returns:
        The PR context.
    """
    root = _root(args.repo)
    head = gitio.resolve(root, args.head or "HEAD")
    base = gitio.merge_base(root, gitio.resolve(root, args.base), head)
    config = parse_config(gitio.read_blob(root, base, CONFIG_PATH))
    body = _read_text(args.body_file) if args.body_file else None
    return PrContext(root, base, head, args.title, parse_title(args.title), body, config,
                     gitio.changes(root, base, head), gitio.commits(root, base, head))


def _emit(command: str, title: dict | None, header: list[str], results: list[Result],
          as_json: bool) -> int:
    """Prints the report and returns the exit code.

    In JSON mode, GitHub annotations go to stderr so stdout stays valid JSON.
    """
    text = render_text(header, results)
    if as_json:
        sys.stdout.write(render_json(command, title, results))
        write_github_outputs(text, results, sys.stderr)
    else:
        sys.stdout.write(text)
        write_github_outputs(text, results, sys.stdout)
    return EXIT_OK if is_ok(results) else EXIT_FAIL


def run_pr(args: argparse.Namespace) -> int:
    """Runs every PR check and prints the report.

    Args:
        args: Parsed options of the pr subcommand.

    Returns:
        0 when nothing fails, 1 otherwise.
    """
    ctx = build_pr_context(args)
    results = [check(ctx) for check in PR_CHECKS]
    allowed = list(ALLOWED[ctx.title.kind]) if ctx.title else []
    header = [f"troy-check pr: {args.title}", describe(ctx.title, allowed)]
    title = ctx.title.to_dict() if ctx.title else None
    return _emit("pr", title, header, results, args.json)


def run_code(args: argparse.Namespace) -> int:
    """Runs the language rules for a PR and prints the report (F03).

    With --worktree, the working tree is checked as a commit on top of HEAD
    (F07 design 12, D60).

    Args:
        args: Parsed options of the code subcommand.

    Returns:
        0 when nothing fails, 1 otherwise.
    """
    if args.worktree:
        args.head = worktree_commit(_root(args.repo), args.title)
    ctx = build_pr_context(args)
    files = load_code(ctx)
    run = load_run(ctx, args.junit)
    results = [check_r04(ctx, files), check_r05(ctx, files, args.doc_warnings),
               check_r06(ctx), check_r07(ctx), check_r09(ctx, run), check_r10(ctx, run),
               check_r11(ctx, args.coverage)]
    allowed = list(ALLOWED[ctx.title.kind]) if ctx.title else []
    header = [f"troy-check code: {args.title}", describe(ctx.title, allowed)]
    title = ctx.title.to_dict() if ctx.title else None
    return _emit("code", title, header, results, args.json)


def run_commit(args: argparse.Namespace) -> int:
    """Checks one commit message and author email, and prints the report.

    Args:
        args: Parsed options of the commit subcommand.

    Returns:
        0 when nothing fails, 1 otherwise.
    """
    root = _root(args.repo)
    config_file = root / CONFIG_PATH
    config = parse_config(_read_text(config_file) if config_file.is_file() else None)
    raw = _read_text(args.message_file) if args.message_file is not None else args.message
    email = args.email if args.email is not None else gitio.author_email(root)
    result = check_commit(config, clean_commit_message(raw), email)
    return _emit("commit", None, ["troy-check commit"], [result], args.json)


def _utf8_stdio() -> None:
    """Makes stdout and stderr UTF-8 whatever the console code page."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Runs troy-check.

    Args:
        argv: Command-line arguments without the program name.

    Returns:
        0 when no rule fails, 1 when one fails, and 2 when the tool cannot
        run: bad options, not a git repository, a git error, an invalid
        config file, or a C/C++ project without lizard.
    """
    _utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "worktree", False) and args.head is not None:
        parser.error("--worktree checks the working tree on top of HEAD; leave out --head")
    try:
        commands = {"pr": run_pr, "code": run_code, "commit": run_commit}
        return commands[args.command](args)
    except (GitError, ConfigError, UsageError, AdapterError) as exc:
        print(f"troy-check: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
