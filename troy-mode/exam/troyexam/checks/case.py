"""The case checks of design 4.3, by name. Each takes the run's context and the criterion's args."""

import ast
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from ..instructions import glob_match
from . import CheckResult

_TEST_PATH = re.compile(r"(^|/)(tests?|version-tests)/(.*/)?test_[^/]*\.py$|(^|/)test_[^/]*\.py$")
_SUPPORT_TEST = re.compile(r"(^|/)(tests?|version-tests)/")
_FENCE = re.compile(r"(?ms)^[ \t]*```[ \t]*(python|py)[ \t]*\n(.*?)^[ \t]*```[ \t]*$")


def _git(project: Path, *args: str) -> str:
    """Runs git in the project; "" when it fails."""
    proc = subprocess.run(["git", "-C", str(project), *args], capture_output=True)
    return proc.stdout.decode("utf-8", errors="replace") if proc.returncode == 0 else ""


def changed_paths(project: Path, start: str) -> list[str]:
    """Every path the run changed against start: modified, deleted, or new."""
    paths = set(_git(project, "diff", "--name-only", "--no-renames", start).splitlines())
    paths.update(_git(project, "ls-files", "--others", "--exclude-standard").splitlines())
    return sorted(p for p in paths if p)


def _read_at(project: Path, start: str, path: str) -> str | None:
    """A file's text at start, or None when it did not exist."""
    proc = subprocess.run(["git", "-C", str(project), "show", f"{start}:{path}"], capture_output=True)
    return proc.stdout.decode("utf-8", errors="replace") if proc.returncode == 0 else None


def report_result(report: str | None) -> str | None:
    """The report's Result value."""
    match = re.search(r"(?m)^\s*Result:[ \t]*(.*)$", report or "")
    return match.group(1).strip().strip("`*. ") if match else None


def result_is(ctx, args: dict) -> CheckResult:
    """The report's Result is the one the case names."""
    want, got = args.get("want"), report_result(ctx.report)
    if got == want:
        return CheckResult(True, f"Result is {want}")
    return CheckResult(False, f"Result is {got!r}, not {want!r}")


def changed_only(ctx, args: dict) -> CheckResult:
    """The run changed only the paths the case names."""
    globs = list(args.get("paths", []))
    outside = [p for p in changed_paths(ctx.project, ctx.start)
               if not any(glob_match(p, g) for g in globs)]
    if outside:
        return CheckResult(False, f"the run changed {outside[0]}, which the case does not name"
                                  + (f" (and {len(outside) - 1} more)" if len(outside) > 1 else ""))
    return CheckResult(True, "the run changed only the named paths")


def _is_test(path: str) -> bool:
    """Tells whether a path is a test or test support file."""
    return bool(_TEST_PATH.search(path) or _SUPPORT_TEST.search(path)) or path.endswith("conftest.py")


def _functions(source: str) -> dict[str, ast.AST]:
    """Every function and method of a module by its qualified name."""
    found: dict[str, ast.AST] = {}

    def walk(node, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[prefix + child.name] = child
                walk(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + ".")
    walk(ast.parse(source), "")
    return found


def _body_without_doc(node) -> list:
    """A function's statements after its docstring."""
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def _only_raises(node) -> bool:
    """Tells whether a body is one `raise NotImplementedError` with or without a call."""
    body = _body_without_doc(node)
    if len(body) != 1 or not isinstance(body[0], ast.Raise):
        return False
    exc = body[0].exc
    if isinstance(exc, ast.Call):
        exc = exc.func
    return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"


def mock_bodies_only_raise(ctx, args: dict) -> CheckResult:
    """Every new or changed function of the changed source files only raises NotImplementedError."""
    checked = 0
    for path in changed_paths(ctx.project, ctx.start):
        full = Path(ctx.project) / path
        if not path.endswith(".py") or _is_test(path) or not full.is_file():
            continue
        try:
            after = _functions(full.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            return CheckResult(False, f"{path} does not parse: {exc.msg}")
        before_text = _read_at(ctx.project, ctx.start, path)
        before = {}
        if before_text is not None:
            try:
                before = _functions(before_text)
            except SyntaxError:
                before = {}
        for name, node in after.items():
            old = before.get(name)
            if old is not None and ast.dump(ast.Module(_body_without_doc(old), [])) == \
                    ast.dump(ast.Module(_body_without_doc(node), [])):
                continue
            checked += 1
            if not _only_raises(node):
                return CheckResult(False, f"{path}: {name} does more than raise NotImplementedError")
    return CheckResult(True, f"all {checked} new or changed bodies only raise NotImplementedError")


def _docstrings(source: str) -> list[str]:
    """Every docstring of a module: the module's, its classes', and its functions'."""
    tree = ast.parse(source)
    found = []
    for node in [tree, *ast.walk(tree)]:
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=True)
            if doc:
                found.append(doc)
    return found


def no_mock_notes_left(ctx, args: dict) -> CheckResult:
    """No paragraph of a doc comment in the project's source starts with "The mock"."""
    globs = list(args.get("paths", []))
    files = _git(ctx.project, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    for path in sorted(set(files)):
        if not path.endswith(".py") or _is_test(path):
            continue
        if globs and not any(glob_match(path, g) for g in globs):
            continue
        full = Path(ctx.project) / path
        if not full.is_file():
            continue
        try:
            docs = _docstrings(full.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for doc in docs:
            for paragraph in re.split(r"\n\s*\n", doc):
                if paragraph.strip().startswith("The mock"):
                    return CheckResult(False, f"{path} keeps a mock note: "
                                              f"{paragraph.strip().splitlines()[0][:100]!r}")
    return CheckResult(True, "no doc comment paragraph starts with \"The mock\"")


def ruff_format_blocks(ctx, args: dict) -> CheckResult:
    """Every python block of the Markdown files the run changed passes `ruff format --check`."""
    work = Path(ctx.work) / "blocks"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    where: dict[str, str] = {}
    for path in changed_paths(ctx.project, ctx.start):
        full = Path(ctx.project) / path
        if not path.endswith(".md") or not full.is_file():
            continue
        text = full.read_text(encoding="utf-8").replace("\r\n", "\n")
        for match in _FENCE.finditer(text):
            name = f"block{len(where) + 1:03d}.py"
            (work / name).write_text(match.group(2), encoding="utf-8", newline="\n")
            where[name] = f"{path}:{text[:match.start()].count(chr(10)) + 1}"
    if not where:
        return CheckResult(True, "the run changed no python block")
    config = Path(ctx.project) / "pyproject.toml"
    command = f'ruff format --check --config "{config.as_posix()}" "{work.as_posix()}"'
    code, output = ctx.env_run(command, Path(ctx.project))
    if code == 0:
        return CheckResult(True, f"ruff format accepts all {len(where)} python blocks")
    bad = [where[n] for n in where if n in output]
    return CheckResult(False, f"ruff format would change {len(bad) or 'some'} block(s), first at "
                              f"{bad[0] if bad else 'an unknown place'}")


def pack_steps_pass(ctx, args: dict) -> CheckResult:
    """Every command of the brief's Checks to run exits 0 when run again after the run."""
    if not ctx.brief_checks:
        return CheckResult(True, "the brief has no checks to run")
    skipped = 0
    for command in ctx.brief_checks:
        code, output = ctx.env_run(command, Path(ctx.project))
        if code != 0 and "troy_check.py code" in command and only_platform_skips(output):
            skipped = output.count("skipped but must pass")
            continue
        if code != 0:
            tail = output.strip().splitlines()[-1][:120] if output.strip() else ""
            return CheckResult(False, f"{command[:80]!r} exited {code}: {tail}")
    note = (f"; troy-check code failed only on {skipped} test(s) that run on another platform "
            "(F07 design D69)") if skipped else ""
    return CheckResult(True, f"all {len(ctx.brief_checks)} checks of the brief pass{note}")


def only_platform_skips(output: str) -> bool:
    """Tells whether troy-check code failed only on R10 tests skipped here.

    The brief says such a test runs on another platform and is not a failure
    (F07 design D69), as `troy_flow.py check-skips` decides in a real run.
    """
    failing = re.findall(r"(?m)^fail\s+(R\d+)\b", output)
    if failing != ["R10"]:
        return False
    block = re.search(r"(?m)^fail\s+R10\b.*\n((?:[ \t]+\S.*\n?)*)", output)
    entries = [line.strip() for line in (block.group(1) if block else "").splitlines() if line.strip()]
    return bool(entries) and all(line.endswith("skipped but must pass") for line in entries)


def junit_results(path: Path) -> dict[str, str]:
    """Reads JUnit XML: test ID -> "passed", "failed", "error", or "skipped"."""
    results: dict[str, str] = {}
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return results
    for case in root.iter("testcase"):
        name = f"{case.get('classname', '')}::{case.get('name', '')}".strip(":")
        kinds = {child.tag for child in case}
        if "error" in kinds:
            results[name] = "error"
        elif "failure" in kinds:
            results[name] = "failed"
        elif "skipped" in kinds:
            results[name] = "skipped"
        else:
            results[name] = "passed"
    return results


def new_tests(ctx) -> list[str]:
    """The test files the run added or changed."""
    return [p for p in changed_paths(ctx.project, ctx.start)
            if _TEST_PATH.search(p) and (Path(ctx.project) / p).is_file()]


def _run_tests(ctx, folder: Path, files: list[str], name: str) -> dict[str, str]:
    """Runs pytest on files in folder, with its src first on the import path; gives the results."""
    report = Path(ctx.work) / f"{name}.xml"
    report.unlink(missing_ok=True)
    targets = " ".join(f'"{f}"' for f in files)
    command = (f'python -m pytest -p no:cacheprovider -q --junitxml="{report.as_posix()}" {targets}')
    ctx.env_run(command, folder)
    return junit_results(report)


def _pilot_checkout(ctx, commit: str) -> Path:
    """A checkout of the pilot's commit under work/pilot, with the run's new tests copied in."""
    folder = Path(ctx.work) / "pilot"
    ready = subprocess.run(["git", "-C", str(folder), "rev-parse", "--verify", "--quiet", "HEAD"],
                           capture_output=True).returncode == 0 if (folder / ".git").exists() else False
    if not ready:
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        full = subprocess.run(["git", "--git-dir", str(ctx.mirror), "rev-parse", f"{commit}^{{commit}}"],
                              capture_output=True, text=True, check=True).stdout.strip()
        # LF in the working tree, so that the mutant patches apply on any system.
        for args in (("init", "--quiet"), ("config", "core.autocrlf", "false"),
                     ("fetch", "--quiet", "--no-tags", str(ctx.mirror), full),
                     ("checkout", "--quiet", "--detach", "FETCH_HEAD")):
            subprocess.run(["git", "-C", str(folder), *args], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(folder), "checkout", "--quiet", "--", "."], capture_output=True)
    for path in new_tests(ctx) + [p for p in changed_paths(ctx.project, ctx.start)
                                   if _is_test(p) and (Path(ctx.project) / p).is_file()]:
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(ctx.project) / path, target)
    return folder


def tests_fail_on_mock(ctx, args: dict) -> CheckResult:
    """Every new test fails against the mock, and none by an import or collection error (R09)."""
    files = new_tests(ctx)
    if not files:
        return CheckResult(False, "the run added no test")
    results = _run_tests(ctx, Path(ctx.project), files, "mock")
    if not results:
        return CheckResult(False, "pytest reported no test")
    errors = [t for t, r in results.items() if r == "error"]
    if errors:
        return CheckResult(False, f"{errors[0]} errors against the mock instead of failing")
    passing = [t for t, r in results.items() if r != "failed"]
    if passing:
        return CheckResult(False, f"{passing[0]} does not fail against the mock ({results[passing[0]]})")
    return CheckResult(True, f"all {len(results)} new tests fail against the mock")


def tests_pass_on_pilot(ctx, args: dict) -> CheckResult:
    """The new tests pass on the pilot's implementation of the feature."""
    files = new_tests(ctx)
    if not files:
        return CheckResult(False, "the run added no test")
    folder = _pilot_checkout(ctx, args["commit"])
    results = _run_tests(ctx, folder, files, "pilot")
    if not results:
        return CheckResult(False, "pytest reported no test on the pilot's code")
    bad = [t for t, r in results.items() if r not in ("passed", "skipped")]
    if bad:
        return CheckResult(False, f"{bad[0]} {results[bad[0]]} on the pilot's code")
    return CheckResult(True, f"all {len(results)} new tests pass on the pilot's code")


def tests_fail_on_mutants(ctx, args: dict) -> CheckResult:
    """Each mutant of the pilot's code makes at least one new test fail."""
    files = new_tests(ctx)
    if not files:
        return CheckResult(False, "the run added no test")
    survivors = []
    for mutant in ctx.case.mutants:
        folder = _pilot_checkout(ctx, args["commit"])
        applied = subprocess.run(["git", "-C", str(folder), "apply", "--whitespace=nowarn", str(mutant)],
                                 capture_output=True)
        if applied.returncode:
            return CheckResult(False, f"mutant {mutant.name} does not apply")
        results = _run_tests(ctx, folder, files, f"mutant-{mutant.stem}")
        if not any(r in ("failed", "error") for r in results.values()):
            survivors.append(mutant.name)
        subprocess.run(["git", "-C", str(folder), "checkout", "--quiet", "--", "."], capture_output=True)
    if survivors:
        return CheckResult(False, f"no new test fails on mutant {survivors[0]}"
                                  + (f" (and {len(survivors) - 1} more)" if len(survivors) > 1 else ""))
    return CheckResult(True, f"each of the {len(ctx.case.mutants)} mutants makes a new test fail")
