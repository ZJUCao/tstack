"""release-test: the release test's report and its comment (F08 design 5.5, D71).

It reads the version test plan on origin/main and the JUnit files of the
regression and the version tests, matches each scenario to its tests by ID,
and writes the comment F08 posts on the release PR. The run passes when no
test failed and every scenario Claude runs has a passing test. With
--real-run, it also reads the report of `real-run --all`, and a mismatch or
problem there fails the run (F12 design 11, D112).
"""

import json
from pathlib import Path

from troycheck.junit import FAILED, PASSED, SKIPPED, JUnitCase, ReportError, own_name, read_junit

from . import github
from . import repo as git
from .errors import FlowError
from .repo import MAIN
from .stages import plain
from .versions import RUN_BY, VERSION, Scenario, devices, norm_id, parse_plan, parse_tag, \
    plan_path, release_tag


def check_version(text: str) -> str:
    """Checks --version: vMAJOR.MINOR.

    Raises:
        FlowError: It is not of that form.
    """
    if not VERSION.fullmatch(text):
        raise FlowError(f"--version {text!r} is not a version of the form vMAJOR.MINOR")
    return text


def read_tests(paths: list[str]) -> list[JUnitCase]:
    """Reads every JUnit file.

    Raises:
        FlowError: A file is missing or is not valid XML.
    """
    tests: list[JUnitCase] = []
    for path in paths:
        try:
            tests += read_junit(Path(path))
        except ReportError as exc:
            raise FlowError(str(exc)) from exc
    return tests


def matches(scenario_id: str, test: JUnitCase) -> bool:
    """Tells whether a test's own name starts with a scenario's ID (interface note 2)."""
    want, name = norm_id(scenario_id), norm_id(own_name(test.name))
    return name.startswith(want) and not name[len(want):len(want) + 1].isdigit()


def scenario_result(tests: list[JUnitCase]) -> str:
    """A Claude scenario's result from its tests: failed, passed, skipped, or missing."""
    outcomes = {t.outcome for t in tests}
    if FAILED in outcomes:
        return "failed"
    if PASSED in outcomes:
        return "passed"
    return "skipped" if outcomes else "missing"


def _release_pr(repo, version: str, notes: list[str]) -> tuple[int | None, int]:
    """Finds the open release PR of the version and the next run number."""
    prs = [pr for pr in github.open_prs(repo)
           if (tag := release_tag(plain(str(pr.get("title") or ""))))
           and parse_tag(tag)[0] == version]
    if not prs:
        notes.append(f"No open release PR for {version} was found; post the comment when it "
                     "exists.")
        return None, 1
    number = int(prs[0].get("number", 0))
    runs = github.read_comments(github.comments(repo, number)).runs
    done = [r["run"] for r in runs if r["by"] == "claude"]
    return number, max(done, default=0) + 1


def _entry(plan, scenario: Scenario, tests: list[JUnitCase]) -> dict:
    """One scenario of the report."""
    own = [t for t in tests if matches(scenario.id, t)] if scenario.run_by == "Claude" else []
    return {"id": scenario.id, "run_by": scenario.run_by,
            "scenario": scenario.cell("scenario") or scenario.cell("target"),
            "steps": scenario.cell("steps"), "expected": scenario.cell("expected result"),
            "devices": devices(plan, scenario), "tests": [t.label for t in own],
            "result": scenario_result(own) if scenario.run_by == "Claude" else None}


def read_real_run(path: str, commit: str) -> dict:
    """Reads the JSON report of `real-run --all` for the release test (F12 design 11).

    Args:
        path: The report file.
        commit: The commit the release test checks, HEAD.

    Returns:
        The counts, the mismatches, the problems, and whether it passed.

    Raises:
        FlowError: The file cannot be read as a real-run report.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise FlowError(f"cannot read the real-run report {path}: {exc}") from exc
    counts = data.get("counts") if isinstance(data, dict) else None
    if not isinstance(data, dict) or data.get("command") != "real-run" \
            or not isinstance(counts, dict) or not isinstance(counts.get("all"), dict):
        raise FlowError(f"{path} is not the JSON report of real-run")
    mismatches = [{"prototype": p.get("file"), "section": s.get("heading"),
                   "typed": c.get("typed")}
                  for p in data.get("prototypes", []) for s in p.get("sections", [])
                  for c in s.get("commands", []) if c.get("result") == "mismatch"]
    problems = [p.get("message", str(p)) if isinstance(p, dict) else str(p)
                for p in data.get("problems", [])]
    if not data.get("all"):
        problems.append("The real run was not run with --all, so it did not run every accepted "
                        "feature's prototypes.")
    if data.get("commit") != commit:
        problems.append(f"The real run checked {str(data.get('commit'))[:7]}, not the commit "
                        f"tested, {commit[:7]}.")
    return {"file": path, "counts": data["counts"]["all"], "mismatches": mismatches,
            "problems": problems, "passed": not mismatches and not problems}


def _real_run_part(real: dict) -> list[str]:
    """The comment's "Real run" part: the counts, then each mismatch and problem."""
    counts = real["counts"]
    lines = ["", f"Real run: {counts.get('matches', 0)} commands match, "
                 f"{counts.get('mismatch', 0)} do not match, {counts.get('waits', 0)} wait for "
                 f"a later feature, {counts.get('not_run', 0)} did not run."]
    lines += [f"- Mismatch: {m['prototype']}, {m['section']}: {m['typed']}"
              for m in real["mismatches"]]
    lines += [f"- Problem: {p}" for p in real["problems"]]
    return lines


def _comment(heading: str, commit: str, plan_file: str, scenarios: list[dict],
             failed: list[str], skipped: list[str], real: dict | None = None) -> str:
    """Writes the comment F08 posts on the release PR (design 5.5, step 3)."""
    lines = [heading, "", f"Commit tested: {commit}", f"Test plan: {plan_file}", "",
             "Automated scenarios (version tests):"]
    claude = [s for s in scenarios if s["run_by"] == "Claude"]
    for s in claude:
        tests = ", ".join(s["tests"]) if s["tests"] else "no test"
        lines.append(f"- {s['id']} {s['scenario']}: {s['result']} ({tests})")
    if not claude:
        lines.append("- None")
    if real is not None:
        lines += _real_run_part(real)
    lines += ["", "Failed tests:"] + ([f"- {t}" for t in failed] or ["- None"])
    if skipped:
        lines += ["", "Skipped on this platform:"] + [f"- {t}" for t in skipped]
    lines += ["", "Scenarios Troy runs:"]
    troy = [s for s in scenarios if s["run_by"] == "Troy"]
    for s in troy:
        where = ", ".join(s["devices"]) or "Troy's devices"
        lines.append(f"- {s['id']} {s['scenario']}, on {where}. Steps: {s['steps'] or 'None'}. "
                     f"Expected: {s['expected'] or 'None'}.")
    if not troy:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def run_release_test(args) -> tuple[dict, int]:
    """Builds the release test's report from the plan and the JUnit files.

    Args:
        args: Parsed options: version, junit (a list), and repo.

    Returns:
        The report and the exit code: 1 when the plan is missing, a scenario
        names no runner, or anything failed.
    """
    version = check_version(args.version)
    tests = read_tests(args.junit)
    repo = git.need_repo(args.repo)
    path = plan_path(version)
    report = {"command": "release-test", "ok": False, "notes": [], "problems": [],
              "version": version, "plan": path}
    has_main = git.commit_of(repo, MAIN) is not None
    plan = parse_plan(git.read(repo, MAIN, path)) if has_main else None
    if plan is None:
        report["problems"] = [f"{path} is not on origin/main."]
        return report, 1
    odd = [s.id for s in plan.scenarios if s.run_by not in RUN_BY.values()]
    if odd:
        report["problems"] = [f"{sid} says neither Claude nor Troy in its Run by column."
                              for sid in odd]
        return report, 1
    commit = git.commit_of(repo, "HEAD") or ""
    real = read_real_run(args.real_run, commit) if getattr(args, "real_run", None) else None
    pr, run = _release_pr(repo, version, report["notes"])
    scenarios = [_entry(plan, s, tests) for s in plan.scenarios]
    failed = [t.label for t in tests if t.outcome == FAILED]
    skipped = [t.label for t in tests if t.outcome == SKIPPED]
    problems = [f"{t} failed." for t in failed]
    problems += [f"{s['id']} has no passing test: {s['result']}." for s in scenarios
                 if s["run_by"] == "Claude" and s["result"] != "passed"]
    if real is not None:
        problems += [f"Real run mismatch: {m['prototype']}, {m['section']}: {m['typed']}."
                     for m in real["mismatches"]] + [f"Real run: {p}" for p in real["problems"]]
    passed = not problems
    heading = f"Release test, run {run}: {'passed' if passed else 'failed'}"
    report.update(ok=passed, problems=problems, pr=pr, run=run, commit=commit, passed=passed,
                  tests=len(tests), failed_tests=failed, skipped_tests=skipped,
                  scenarios=scenarios, troy_scenarios=[s["id"] for s in scenarios
                                                       if s["run_by"] == "Troy"],
                  heading=heading, real_run=real,
                  comment=_comment(heading, commit, path, scenarios, failed, skipped, real))
    return report, 0 if passed else 1

