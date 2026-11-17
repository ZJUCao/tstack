"""The judge: a fresh session that grades every run of both versions in one pass (design 6.2, 11.4)."""

import json
import random
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from . import INSTALLED_OFF
from .errors import ExamError
from .instructions import glob_match
from .runner import cli_command

LABEL = "R{:02d}"
JUDGE_CAP = 15.0


def assign_labels(items: Sequence[str], rng: random.Random) -> dict[str, str]:
    """Gives each item a label R01, R02, ... in a shuffled order: label -> item."""
    order = list(items)
    rng.shuffle(order)
    return {LABEL.format(i + 1): item for i, item in enumerate(order)}


def replace_paths(text: str, replacements: Mapping[str, str]) -> str:
    """Writes each real path as its placeholder, in both slash styles, longest first."""
    pairs = []
    for real, placeholder in replacements.items():
        for form in {real, real.replace("\\", "/"), real.replace("/", "\\")}:
            if form:
                pairs.append((form, placeholder))
    for real, placeholder in sorted(pairs, key=lambda p: -len(p[0])):
        text = re.sub(re.escape(real), placeholder, text, flags=re.I)
    return text


def build_folder(folder: Path, rubric: str, outputs: Mapping[str, Mapping[str, str]],
                 replacements: Mapping[str, str], shared: Mapping[str, str] | None = None) -> None:
    """Writes the judge's folder: rubric.md, shared files, and one folder per label, nothing else.

    Args:
        folder: The judge's folder, new or empty.
        rubric: The case's rubric.
        outputs: label -> {relative file name: text}: diff.patch, report.md, files/<path>.
        replacements: real path -> placeholder, such as the project's path -> "<project>".
        shared: relative file name -> text, written once under shared/ (the change under review,
            the files the rubric names).
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "rubric.md").write_text(rubric, encoding="utf-8", newline="\n")
    for name, text in (shared or {}).items():
        target = folder / "shared" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(replace_paths(text, replacements), encoding="utf-8", newline="\n")
    for label, files in outputs.items():
        for name, text in files.items():
            target = folder / label / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(replace_paths(text, replacements), encoding="utf-8", newline="\n")


def schema() -> dict:
    """The verdict's shape: for each label, each criterion's pass and one sentence of evidence."""
    item = {"type": "object", "properties": {"id": {"type": "integer"}, "pass": {"type": "boolean"},
                                             "evidence": {"type": "string"}},
            "required": ["id", "pass", "evidence"]}
    label = {"type": "object", "properties": {"label": {"type": "string"},
                                              "criteria": {"type": "array", "items": item}},
             "required": ["label", "criteria"]}
    return {"type": "object", "properties": {"sets": {"type": "array", "items": label}},
            "required": ["sets"]}


def judge_prompt(labels: Sequence[str], count: int) -> str:
    """The judge's prompt: separate runs of one task, graded by rubric.md only."""
    return ("The folders " + ", ".join(labels) + " in the current folder each hold the output of "
            "a separate run of one task: its diff (diff.patch), its report (report.md), and any "
            "files under files/. The folder shared/, when present, holds material the rubric names, "
            "the same for every run. Read rubric.md, then every output. Grade each output by the "
            f"rubric's criteria 1 to {count} only, each on its own, and on the same scale for every "
            "output. For each label and criterion, give pass or fail and one sentence of evidence "
            "that quotes the output. Do not guess how an output was made, and do not prefer an "
            "output for its length or style.")


def command_line(cli: Path, prompt: str, schema_text: str, max_cost: float) -> list[str]:
    """The judge's command line (design 11.4): opus, high effort, read-only tools, no plugin."""
    return [*cli_command(cli), "-p", prompt, "--model", "opus", "--effort", "high",
            "--tools", "Read,Glob,Grep", "--settings", INSTALLED_OFF, "--json-schema", schema_text,
            "--output-format", "json", "--max-budget-usd", f"{max_cost:.2f}"]


def parse_verdict(output: dict, labels: Sequence[str], count: int) -> dict[str, dict[int, tuple[bool, str]]]:
    """Reads structured_output: label -> criterion number -> (pass, evidence).

    Raises:
        ExamError: A label or a criterion is missing, or the shape is wrong.
    """
    data = output.get("structured_output")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError as exc:
            raise ExamError("the verdict is not JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("sets"), list):
        raise ExamError("the verdict has no sets")
    verdict: dict[str, dict[int, tuple[bool, str]]] = {}
    for entry in data["sets"]:
        if not isinstance(entry, dict):
            continue
        grades = {}
        for item in entry.get("criteria") or []:
            try:
                grades[int(item["id"])] = (bool(item["pass"]), str(item.get("evidence", "")))
            except (KeyError, TypeError, ValueError):
                continue
        verdict[str(entry.get("label"))] = grades
    for label in labels:
        if label not in verdict:
            raise ExamError(f"the verdict has no label {label}")
        missing = [n for n in range(1, count + 1) if n not in verdict[label]]
        if missing:
            raise ExamError(f"the verdict of {label} lacks criterion {missing[0]}")
    return {label: verdict[label] for label in labels}


def anchors_ok(grades: Mapping[str, bool], key: Mapping[str, str]) -> bool:
    """Tells whether the pass anchor passes and the fail anchor fails, by their overall grades."""
    by_item = {item: label for label, item in key.items()}
    passing, failing = by_item.get("anchor-pass"), by_item.get("anchor-fail")
    if passing is None or failing is None:
        return False
    return bool(grades.get(passing)) and not grades.get(failing, True)


def filter_diff(diff: str, globs: Sequence[str]) -> str:
    """Keeps the parts of a git diff whose file matches a glob; all of it without globs."""
    if not globs:
        return diff
    parts = re.split(r"(?m)^(?=diff --git )", diff)
    kept = []
    for part in parts:
        match = re.match(r"diff --git a/(\S+) b/(\S+)", part)
        if match and any(glob_match(match.group(2), g) or glob_match(match.group(1), g) for g in globs):
            kept.append(part)
    return "".join(kept)


def run_judge(cli: Path, folder: Path, count: int, labels: Sequence[str], env: Mapping[str, str],
              max_cost: float = JUDGE_CAP, minutes: float = 60) -> tuple[dict, float]:
    """Runs one judge pass in its folder.

    Returns:
        The verdict and the pass's cost.

    Raises:
        ExamError: The session failed or gave no valid verdict.
    """
    from .runner import GIT_BASH, SESSION_VARIABLES
    text = json.dumps(schema())
    clean = {k: v for k, v in env.items() if k not in SESSION_VARIABLES}
    clean.setdefault("CLAUDE_CODE_GIT_BASH_PATH", GIT_BASH)
    proc = subprocess.run(command_line(cli, judge_prompt(labels, count), text, max_cost),
                          cwd=str(folder), env=clean, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=minutes * 60)
    (folder.parent / f"{folder.name}.out.json").write_text(proc.stdout, encoding="utf-8")
    try:
        output = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
    except ValueError:
        output = {}
    cost = float(output.get("total_cost_usd") or 0.0)
    if not output or output.get("is_error"):
        result = str(output.get("result", ""))[:200]
        if "hit your" in result.lower() and "limit" in result.lower():
            raise ExamError(f"limit: {result}")
        raise ExamError(f"the judge failed: {result or proc.stderr.strip()[-300:]}")
    return parse_verdict(output, labels, count), cost
