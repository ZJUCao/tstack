"""Cases: one role task in a project state of the pilot, and what grades it (design 4.1)."""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import SUBAGENT_ROLES
from .errors import ExamError

REVIEW_TASKS = ("AR2", "TM2", "CR1")
_PREFIX_ROLE = {"AR": "architect", "IF": "interface-designer", "TM": "test-manager",
                "DV": "developer", "TE": "test-engineer", "CR": "code-reviewer"}
# F04's task IDs (troyflow.brief.ALL_TASKS), written out here so the exam's
# validation does not depend on the engine version under test.
F04_TASKS = ("AR1", "AR2", "AR3", "AR4", "AR5", "AR6", "IF1", "IF2", "IF3", "IF4",
             "TM1", "TM2", "TM3", "TM4", "TM5", "TM6", "TM7", "TM8",
             "DV1", "DV2", "DV3", "DV4", "DV5",
             "TE1", "TE2", "TE3", "TE4", "TE5", "TE6", "CR1")
_ITEM = re.compile(r"^(\d+)\.\s+(.*)$")


@dataclass
class Criterion:
    """One criterion of a case: a check by script or a judge criterion.

    Attributes:
        id: The criterion's ID.
        check: The check's name, or None for a judge criterion.
        judge: The 1-based number of the rubric's criterion, or None.
        must: True when a run fails without it.
        args: The table's other keys, passed to the check.
    """

    id: str
    check: str | None
    judge: int | None
    must: bool
    args: dict = field(default_factory=dict)


@dataclass
class Start:
    """The project state a run starts from (design 4.2).

    Attributes:
        repository: "owner/name" on GitHub, or a local folder (tests).
        commit: The start commit: origin/main of the run.
        branch: The branch the role works on.
        pilot: The pilot's PRs of the mistake.
        title: The commit subject of start.patch, for a review case.
        pr: The PR number that the gh stand-in reports.
    """

    repository: str
    commit: str
    branch: str
    pilot: list[str]
    title: str | None = None
    pr: int = 1


@dataclass
class RunSettings:
    """How each run of the case runs.

    Attributes:
        model: The role's model.
        effort: The role's effort.
        minutes: The time limit of one run.
        max_cost: The cap of one run, in dollars at list prices.
    """

    model: str
    effort: str
    minutes: int
    max_cost: float


@dataclass
class Case:
    """A case of the exam.

    Attributes:
        id: The case ID, also its folder's name.
        version: Rises whenever the case's files change.
        role: The role, one of SUBAGENT_ROLES.
        task: The F04 task ID.
        item: The brief's --item.
        title: The brief's --title, or None.
        round: The brief's --round, or None.
        start: The start of each run.
        run: The run settings.
        criteria: The case's own criteria.
        judge_files: Project files after the run that the judge sees for each run.
        judge_diff: The paths of a run's diff that the judge sees; empty for all.
        judge_shared: Start files that the judge sees once.
        folder: The case's folder.
    """

    id: str
    version: int
    role: str
    task: str
    item: str
    title: str | None
    round: int | None
    start: Start
    run: RunSettings
    criteria: list[Criterion]
    judge_files: list[str]
    judge_diff: list[str]
    judge_shared: list[str]
    folder: Path

    @property
    def rubric_path(self) -> Path:
        """rubric.md."""
        return self.folder / "rubric.md"

    @property
    def input_path(self) -> Path | None:
        """input.md, or None when the case has no Input."""
        path = self.folder / "input.md"
        return path if path.is_file() else None

    @property
    def start_patch(self) -> Path | None:
        """start.patch, or None."""
        path = self.folder / "start.patch"
        return path if path.is_file() else None

    @property
    def mutants(self) -> list[Path]:
        """The mutants, sorted by name."""
        folder = self.folder / "mutants"
        return sorted(folder.glob("*.patch")) if folder.is_dir() else []

    def anchor(self, kind: str) -> Path:
        """anchors/<kind>, kind "fail" or "pass"."""
        return self.folder / "anchors" / kind

    def input_text(self) -> str | None:
        """The Input, or None."""
        path = self.input_path
        return path.read_text(encoding="utf-8") if path else None

    def judge_criteria(self) -> list[Criterion]:
        """The criteria the judge grades."""
        return [c for c in self.criteria if c.judge is not None]


def _need(table: dict, key: str, where: str):
    """Reads a key that must be there."""
    if key not in table:
        raise ExamError(f"{where}: {key} is missing")
    return table[key]


def _criterion(table: dict, where: str) -> Criterion:
    """Reads one [[criteria]] table."""
    if not isinstance(table, dict):
        raise ExamError(f"{where}: a criterion is not a table")
    cid = str(_need(table, "id", where))
    check, judge = table.get("check"), table.get("judge")
    if (check is None) == (judge is None):
        raise ExamError(f"{where}: criterion {cid} needs exactly one of check and judge")
    args = {k: v for k, v in table.items() if k not in ("id", "check", "judge", "must")}
    return Criterion(cid, check, int(judge) if judge is not None else None,
                     bool(table.get("must", False)), args)


def load_case(folder: Path) -> Case:
    """Reads a case's case.toml.

    Raises:
        ExamError: The file is missing, is not TOML, or lacks a key.
    """
    folder = Path(folder)
    path = folder / "case.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ExamError(f"{path}: {exc}") from exc
    where = str(path)
    start, run = _need(data, "start", where), _need(data, "run", where)
    judge = data.get("judge", {})
    try:
        return Case(
            id=str(_need(data, "id", where)), version=int(_need(data, "version", where)),
            role=str(_need(data, "role", where)), task=str(_need(data, "task", where)),
            item=str(_need(data, "item", where)), title=data.get("title"),
            round=int(data["round"]) if data.get("round") is not None else None,
            start=Start(str(_need(start, "repository", where)), str(_need(start, "commit", where)),
                        str(_need(start, "branch", where)), list(start.get("pilot", [])),
                        start.get("title"), int(start.get("pr", 1))),
            run=RunSettings(str(_need(run, "model", where)), str(_need(run, "effort", where)),
                            int(_need(run, "minutes", where)), float(_need(run, "max_cost", where))),
            criteria=[_criterion(t, where) for t in data.get("criteria", [])],
            judge_files=list(judge.get("files", [])), judge_diff=list(judge.get("diff", [])),
            judge_shared=list(judge.get("shared", [])), folder=folder)
    except (TypeError, ValueError) as exc:
        raise ExamError(f"{where}: {exc}") from exc


def load_cases(root: Path) -> list[Case]:
    """Reads every case under root, sorted by ID."""
    root = Path(root)
    folders = sorted(p for p in root.iterdir() if (p / "case.toml").is_file()) if root.is_dir() else []
    return sorted((load_case(p) for p in folders), key=lambda c: c.id)


def rubric_criteria(text: str) -> list[str]:
    """The rubric's numbered criteria: each line that starts with "1. ", "2. ", and its lines below."""
    items: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        match = _ITEM.match(line)
        if match:
            items.append(match.group(2).strip())
        elif items and line.startswith((" ", "\t")) and line.strip():
            items[-1] += " " + line.strip()
        elif items and not line.strip():
            continue
        elif items and line.startswith("#"):
            break
    return items


def task_role(task: str) -> str | None:
    """The role whose task this is, by its prefix; None for the Product Manager's or none."""
    return _PREFIX_ROLE.get(task[:2]) if task in F04_TASKS else None


def problems(case: Case) -> list[str]:
    """Lists what makes a case invalid (design 4.1, 14.1); empty when it is valid."""
    from .blinding import exam_words
    from .checks import CHECKS
    found = []
    if case.id != case.folder.name:
        found.append(f"id {case.id!r} differs from its folder {case.folder.name!r}")
    if case.version < 1:
        found.append("version must be 1 or more")
    if case.role not in SUBAGENT_ROLES:
        found.append(f"role {case.role!r} is not a role that runs as a subagent")
    if task_role(case.task) != case.role:
        found.append(f"task {case.task!r} is not an F04 task of {case.role}")
    rubric = rubric_criteria(case.rubric_path.read_text(encoding="utf-8")) \
        if case.rubric_path.is_file() else []
    if not 3 <= len(rubric) <= 6:
        found.append(f"rubric.md has {len(rubric)} criteria, not 3 to 6")
    for criterion in case.criteria:
        if criterion.check is not None and criterion.check not in CHECKS:
            found.append(f"criterion {criterion.id}: no check named {criterion.check!r}")
        if criterion.judge is not None and not 1 <= criterion.judge <= len(rubric):
            found.append(f"criterion {criterion.id}: rubric has no criterion {criterion.judge}")
    for kind in ("fail", "pass"):
        for name in ("diff.patch", "report.md"):
            if not (case.anchor(kind) / name).is_file():
                found.append(f"anchors/{kind}/{name} is missing")
    if case.task in REVIEW_TASKS and case.start_patch is None:
        found.append("a review case needs start.patch")
    if any(c.check == "tests_fail_on_mutants" for c in case.criteria) and not case.mutants:
        found.append("tests_fail_on_mutants needs at least one mutant")
    text = case.input_text()
    if text is not None and exam_words(text):
        found.append(f"input.md holds {', '.join(exam_words(text))}")
    return found
