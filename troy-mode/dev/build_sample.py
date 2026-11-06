"""Builds a sample project's git repository for troy-pstack's CI (F03 design 10).

Usage:
    python troy-mode/dev/build_sample.py build python --pr tests --out DIR
    python troy-mode/dev/build_sample.py verify python --pr tests --report FILE

build sets the sample up the way troy-init sets up a project: the sample's
base folder, troy-check in .troy-mode/checks, F02's workflow, and the
language pack. Then it makes one commit per stage up to the PR's commit,
which goes on a branch named pr. It prints BASE_SHA, HEAD_SHA, PR_TITLE, and
PR_BODY, the values a pull_request event gives the pack's CI job, and writes
them to the file named by GITHUB_ENV when that is set.

verify compares a troy-check --json report with the results the sample
expects for that PR.

Exit codes: 0 on success, 1 when verify finds a difference, and 2 when the
script cannot run.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

TROY_MODE = Path(__file__).resolve().parents[1]
CHECKS = TROY_MODE / "checks"
PR_BODY = "## Why\n\nA stage of the sample's F01.\n\n## Soft-limit reason\n\nNone\n"
_UNFILLED = re.compile(r"(?<!\$)\{\{[^}]*\}\}")
_IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")
_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "troy-mode sample",
    "GIT_AUTHOR_EMAIL": "sample@example.invalid",
    "GIT_COMMITTER_NAME": "troy-mode sample",
    "GIT_COMMITTER_EMAIL": "sample@example.invalid",
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


def install_pack(lang: str, sample: dict, repo: Path) -> None:
    """Adds troy-check, F02's workflow, and the language pack to the repository."""
    checks = repo / ".troy-mode" / "checks"
    shutil.copytree(CHECKS / "troycheck", checks / "troycheck", ignore=_IGNORED)
    shutil.copy2(CHECKS / "troy_check.py", checks / "troy_check.py")
    workflow = repo / ".github" / "workflows" / "troy-mode.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CHECKS / "workflow.yml", workflow)
    pack = TROY_MODE / "lang" / lang
    for mode in ("copy", "append"):
        for name, target in sample["pack"].get(mode, {}).items():
            text = fill((pack / name).read_text(encoding="utf-8"), sample["environment"], name)
            path = repo / target
            path.parent.mkdir(parents=True, exist_ok=True)
            if mode == "append" and path.exists():
                text = path.read_text(encoding="utf-8").rstrip("\n") + "\n\n" + text
            path.write_text(text, encoding="utf-8", newline="\n")


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
        if index == 0:
            install_pack(lang, sample, out)
        git(out, "add", "-A")
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


def verify(lang: str, pr: str, report_path: Path) -> list[str]:
    """Compares a troy-check --json report with the sample's expected results.

    Returns:
        One line per difference; empty when the report matches.

    Raises:
        SampleError: The report cannot be read.
    """
    _, sample = load_sample(lang)
    expected = sample["commits"][pr_index(sample, pr)]["expected"]
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
    sub.choices["verify"].add_argument("--report", required=True, type=Path)
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
        problems = verify(args.lang, args.pr, args.report)
    except SampleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(problem)
    print("The report matches the sample." if not problems else f"{len(problems)} differences.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
