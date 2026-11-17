"""Builds a sample project's git repository for tstack's CI (F03 design 10).

Usage:
    python troy-mode/dev/build_sample.py build python --pr tests --out DIR
    python troy-mode/dev/build_sample.py verify python --pr tests --report FILE
    python troy-mode/dev/build_sample.py verify python --pr design --no-code

build sets the sample up with troy-init's own functions (F06 design 8):
setup's files, then the language step's, without their preconditions and
without the environment, on top of the sample's base folder. It does not
turn the git hooks on. Then it makes one commit per stage up to the PR's
commit, which goes on a branch named pr. It prints BASE_SHA, HEAD_SHA,
PR_TITLE, and PR_BODY, the values a pull_request event gives the pack's CI
job, and writes them to the file named by GITHUB_ENV when that is set.

verify compares a troy-check --json report with the results the sample
expects for that PR. With --no-code, it checks instead that the sample
expects the pack's code steps to be skipped on that PR (F06 design D50).

Exit codes: 0 on success, 1 when verify finds a difference, and 2 when the
script cannot run.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

TROY_MODE = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = TROY_MODE.parent
sys.path.insert(0, str(TROY_MODE / "init"))

from troyinit.errors import InitError  # noqa: E402  (import after the path setup)
from troyinit.lang import LangOptions, lang_files  # noqa: E402
from troyinit.plan import FileAction, Plan, apply  # noqa: E402
from troyinit.plugin import load_plugin  # noqa: E402
from troyinit.setup import SetupOptions, setup_files  # noqa: E402

SAMPLE_EMAIL = "sample@example.invalid"
PR_BODY = "## Why\n\nA stage of the sample's F01.\n\n## Soft-limit reason\n\nNone\n"
_UNFILLED = re.compile(r"(?<!\$)\{\{[^}]*\}\}")
_IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")
_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "troy-mode sample",
    "GIT_AUTHOR_EMAIL": SAMPLE_EMAIL,
    "GIT_COMMITTER_NAME": "troy-mode sample",
    "GIT_COMMITTER_EMAIL": SAMPLE_EMAIL,
}


class SampleError(Exception):
    """Raised when the sample cannot be built or checked."""


def load_sample(lang: str) -> tuple[Path, dict]:
    """Reads a sample's sample.toml.

    Args:
        lang: The language pack, for example "python".

    Returns:
        The sample's folder and its settings.

    Raises:
        SampleError: The sample does not exist or its settings cannot be read.
    """
    folder = TROY_MODE / "samples" / lang
    try:
        with (folder / "sample.toml").open("rb") as handle:
            return folder, tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SampleError(f"cannot read the {lang} sample: {exc}") from exc


def pr_index(sample: dict, pr: str) -> int:
    """Finds the position of the PR's commit in the sample's commits.

    Raises:
        SampleError: No commit is marked with that PR name.
    """
    for index, commit in enumerate(sample["commits"]):
        if commit.get("pr") == pr:
            return index
    names = [c["pr"] for c in sample["commits"] if "pr" in c]
    raise SampleError(f"no PR named {pr}; the sample has {', '.join(names)}")


def git(repo: Path, *args: str) -> str:
    """Runs git in the repository without background maintenance.

    Raises:
        SampleError: git fails.
    """
    command = ["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0", *args]
    env = {**os.environ, **_GIT_IDENTITY}
    proc = subprocess.run(command, cwd=repo, env=env, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SampleError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def fill(text: str, environment: str, source: str) -> str:
    """Fills the environment marker of a pack file.

    Raises:
        SampleError: Another fill-in marker is left. ${{ }} expressions of
            GitHub workflows are not markers.
    """
    text = text.replace("{{environment}}", environment)
    left = _UNFILLED.search(text)
    if left:
        raise SampleError(f"{source} has the unfilled marker {left.group(0)}")
    return text


def _write(repo: Path, command: str, actions: list[FileAction]) -> list[str]:
    """Writes troy-init's planned files into the sample. Returns the git hooks."""
    apply(repo, Plan(command, "sample", actions=actions))
    return [a.path for a in actions if a.executable and a.action != "keep"]


def install(lang: str, sample: dict, repo: Path) -> list[str]:
    """Sets the sample up as troy-init's setup and language step would (F06 design 8).

    Args:
        lang: The language pack.
        sample: The sample's settings.
        repo: The sample's repository, holding its base folder.

    Returns:
        The git hook paths, to stage with their executable bit.

    Raises:
        SampleError: troy-init's functions fail, or the base folder clashes
            with the language pack.
    """
    date = datetime.date.today().isoformat()
    project = sample["project"]
    try:
        plugin = load_plugin(PLUGIN_ROOT)
        hooks = _write(repo, "setup", setup_files(plugin, repo,
                                                  SetupOptions(project, SAMPLE_EMAIL, date)))
        package = project.replace("-", "_") if lang == "python" else None
        options = LangOptions(lang, project, sample["environment"], ["."], package, date,
                              no_env=True)
        files = lang_files(plugin, repo, options)
        if files.problems:
            raise SampleError("; ".join(files.problems))
        _write(repo, "lang", files.actions)
    except InitError as exc:
        raise SampleError(f"troy-init cannot set the sample up: {exc}") from exc
    return hooks


def build(lang: str, pr: str, out: Path) -> dict[str, str]:
    """Builds the sample's repository with the PR's commit on branch pr.

    Args:
        lang: The language pack.
        pr: The PR name in sample.toml, for example "tests".
        out: A folder that does not exist yet or is empty.

    Returns:
        BASE_SHA, HEAD_SHA, PR_TITLE, and PR_BODY.

    Raises:
        SampleError: The sample cannot be built.
    """
    folder, sample = load_sample(lang)
    last = pr_index(sample, pr)
    if out.exists() and any(out.iterdir()):
        raise SampleError(f"{out} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    git(out, "init", "-q", "-b", "main")
    for index, commit in enumerate(sample["commits"][: last + 1]):
        if index == last:
            git(out, "switch", "-q", "-c", "pr")
        shutil.copytree(folder / commit["folder"], out, dirs_exist_ok=True, ignore=_IGNORED)
        hooks = install(lang, sample, out) if index == 0 else []
        git(out, "add", "-A")
        if hooks:
            git(out, "add", "--chmod=+x", "--", *hooks)
        git(out, "commit", "-q", "-m", commit["title"])
    return {
        "BASE_SHA": git(out, "rev-parse", "main"),
        "HEAD_SHA": git(out, "rev-parse", "HEAD"),
        "PR_TITLE": sample["commits"][last]["title"],
        "PR_BODY": PR_BODY,
    }


def write_env(values: dict[str, str], path: Path) -> None:
    """Appends the values to a GITHUB_ENV file, multi-line ones with a delimiter."""
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for name, value in values.items():
            if "\n" in value:
                handle.write(f"{name}<<TROY_SAMPLE_EOF\n{value}\nTROY_SAMPLE_EOF\n")
            else:
                handle.write(f"{name}={value}\n")


def verify(lang: str, pr: str, report_path: Path | None) -> list[str]:
    """Compares a troy-check --json report with the sample's expected results.

    Args:
        lang: The language pack.
        pr: The PR name in sample.toml.
        report_path: The report, or None when the pack's code steps were
            skipped because the PR's head has no code (F06 design D50).

    Returns:
        One line per difference; empty when the report matches.

    Raises:
        SampleError: The report cannot be read.
    """
    _, sample = load_sample(lang)
    commit = sample["commits"][pr_index(sample, pr)]
    if commit.get("no_code", False) != (report_path is None):
        if report_path is None:
            return [f"{pr}: the code steps were skipped, but the sample expects code."]
        return [f"{pr}: the sample expects no code, so the code steps should have been skipped."]
    if report_path is None:
        return []
    expected = commit["expected"]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SampleError(f"cannot read the report {report_path}: {exc}") from exc
    actual = {r["rule"]: r for r in report["results"]}
    problems = []
    for rule in sorted(set(expected) | set(actual)):
        want = expected.get(rule, "not reported")
        got = actual[rule]["result"] if rule in actual else "not reported"
        if want != got:
            message = actual[rule]["message"] if rule in actual else ""
            problems.append(f"{rule}: expected {want}, got {got}. {message}".rstrip())
    return problems


def _parser() -> argparse.ArgumentParser:
    """Builds the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        command = sub.add_parser(name)
        command.add_argument("lang", help="the language pack, for example python")
        command.add_argument("--pr", required=True, help="the PR name in sample.toml")
    sub.choices["build"].add_argument("--out", required=True, type=Path)
    given = sub.choices["verify"].add_mutually_exclusive_group(required=True)
    given.add_argument("--report", type=Path, help="troy-check code's --json report")
    given.add_argument("--no-code", action="store_true",
                       help="the pack's code steps were skipped: the PR's head has no code")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Runs the command line. Returns the exit code."""
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            values = build(args.lang, args.pr, args.out)
            print(json.dumps(values, indent=2))
            if os.environ.get("GITHUB_ENV"):
                write_env(values, Path(os.environ["GITHUB_ENV"]))
            return 0
        problems = verify(args.lang, args.pr, None if args.no_code else args.report)
    except SampleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(problem)
    print("The report matches the sample." if not problems else f"{len(problems)} differences.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
