"""Shared fixtures for the F18 part 2 tests, spot checks (F18 design 7, 8, 9, 13.1, 13.2).

Written from F18 design version 1.0 and the part 2 contract before the code exists.
Black-box, as part 1's tests are: the engine runs as a subprocess through ``flow_helpers``,
on clones of bare origins, with the fake gh. Only ``troyflow.spot`` (``sample``, its
constants, and ``plugin_hash``) and ``troyexam.instructions`` (the expected hash of E3) are
imported, as the contract's preamble allows.

What this module adds:

- A chain of features, each with a hard dependency on the one before, so exactly one
  feature is ready at a time and the home checkout's ``next`` stays a ``stage`` (no team
  plan), with a Chinese requirements mirror whose features table names them.
- ``[flow]`` config text with ``spot_checks`` and ``spot_check_every`` (contract 1, 3).
- Comments with URLs and times: an Architect review with its ``Risky:`` line, a ruling at
  round 3, attempts, the spot check comment, TM8's real-run ruling, notes, and overturns.
- Issues as ``gh issue list --state all`` gives them: progress issues and closed ideas.
- A clone whose origin also holds PR branches (PR 1's head branch, for the interface mark).
- The role exam's case logs for E3 and the expected instruction hash (contract 6).
- Runners for ``status`` and ``issues``, one clone per case, side by side.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence

from flow_helpers import (
    ENGINE, LOGIN, PLUGIN_ROOT, PROJECT, REPO_URL, REQUIREMENTS_ZH, WORK_BRANCH, Fakes, Feature,
    FlowCase, Outcome, Project, Step, base_env, base_files, custom_design, front_matter, git,
    new_dir,
    origin_repo, parallel, step, write_file,
)
from stops_helpers import MERGE_FINDINGS, comment_url, engine_module, ruling, three_rounds, timed

APPROVALS_TITLE = "[rules] Set the features Troy approves"
SPOT_HEADING = "Spot check for Troy: review after the merge"
SPOT_LINE = "What to decide is in the summary at the top of the description."
SPOT_COMMENT = f"{SPOT_HEADING}\n\n{SPOT_LINE}"
TM_HEADING = "Test Manager ruling, real run"
OFF_BRANCH = "troy-mode/spot-checks-off"
CACHE = "troy-mode/spot.json"
EVIDENCE_CASES = ("if-example-format", "if-error-rules", "ar-design-review", "ar-error-review",
                  "tm-plan-expected")
DEFAULT_ROOT = "D:\\Troy\\troy-mode-work"
WAIT_W3 = "Waiting for Troy: approve this PR\n\nWait: W3\n\n" + SPOT_LINE
ARCH, IF, CR, TM = "Architect", "Interface Designer", "Code Reviewer", "Test Manager"
# flow_helpers' fast-import gives step k (counted from 1) the time 1762470000 + 60 * k.
_FIRST_COMMIT = 1762470000
_TIME = "%Y-%m-%dT%H:%M:%SZ"
OLD_TIME = "2025-11-01T08:00:00Z"   # before every commit of an origin built here
NEW_TIME = "2026-11-21T08:00:00Z"   # after every commit of an origin built here
ZH_STATUS = {"Not started": "未开始"}


# ------------------------------------------------------------------ features

def chain(count: int, versions: Optional[Mapping[int, str]] = None) -> tuple:
    """Features F01 to F<count>, each with a hard dependency on the one before.

    Args:
        count: How many features.
        versions: Feature number mapped to its Version cell; ``v0.1`` for the rest.

    Returns:
        The features, in order (the order line follows the table).
    """
    items = []
    for number in range(1, count + 1):
        hard = (f"F{number - 1:02d}",) if number > 1 else ()
        version = (versions or {}).get(number, "v0.1")
        items.append(Feature(f"F{number:02d}", f"Step {number}", hard=hard, version=version))
    return tuple(items)


CHAIN = chain(10)


def feat(number: int) -> Feature:
    """Feature F<number> of ``CHAIN``."""
    return CHAIN[number - 1]


def zh_name(feature: Feature) -> str:
    """A feature's Chinese name, for example ``第3步``."""
    return f"第{int(feature.id[1:])}步"


def zh_requirements(features: Sequence[Feature]) -> str:
    """The Chinese requirements mirror with a features table (requirements template 4)."""
    rows = [f"| {item.id} | {zh_name(item)} | {', '.join(item.hard) or '无'} "
            f"| {', '.join(item.soft) or '无'} | {item.version} "
            f"| {ZH_STATUS.get(item.status, item.status)} |" for item in features]
    return (front_matter("requirements", "zh-CN", "1.0", "requirements.md")
            + f"# {PROJECT} 需求\n\n## 1. 目标\n\n统计文本文件中的单词数。\n\n## 4. 功能点\n\n"
            "| 编号 | 功能 | 硬依赖 | 软依赖 | 版本 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")


def progress_title(feature: Feature) -> str:
    """A progress issue's title, for example ``F03 第3步 / Step 3``."""
    return f"{feature.id} {zh_name(feature)} / {feature.name}"


# ------------------------------------------------------------------ config

def flow(approves: Optional[int] = None, spot: Optional[bool] = None,
         every: Optional[int] = None) -> str:
    """A ``[flow]`` table with the keys given (contract 1).

    Args:
        approves: ``troy_approves_first``, or None to leave it out.
        spot: ``spot_checks``, or None to leave it out.
        every: ``spot_check_every``, or None to leave it out.

    Returns:
        The TOML text.
    """
    lines = ["[flow]"]
    if approves is not None:
        lines.append(f"troy_approves_first = {approves}")
    if spot is not None:
        lines.append(f"spot_checks = {'true' if spot else 'false'}")
    if every is not None:
        lines.append(f"spot_check_every = {every}")
    return "\n".join(lines) + "\n"


def spot_files(features: Sequence[Feature] = CHAIN, config: str = "",
               extra: Optional[Mapping] = None, **kwargs) -> dict:
    """``base_files`` with a ``[flow]`` table and a Chinese mirror that names the features.

    Args:
        features: The features table.
        config: Raw TOML appended to the config, such as ``flow(...)``.
        extra: More files, which replace the defaults of the same path.
        **kwargs: Passed on to ``base_files``, such as ``order``.

    Returns:
        Paths mapped to content.
    """
    files = base_files(features, config_extra=config, **kwargs)
    files[REQUIREMENTS_ZH] = zh_requirements(features)
    files.update(extra or {})
    return files


INTERFACE_2 = "### 2.1 `count_parts`\n\n```python\ndef count_parts(text: str) -> int\n```\n"
CHANGED_3 = "### 3.1 `count` of F01\n\nIt now counts blank lines too.\n"


def custom_design_files(feature: Feature, section3: str) -> dict:
    """A feature's design pair: the English one with an interface in section 2 and the given
    section 3 (``## 3. Changes to existing interfaces``), and a short mirror."""
    return {feature.design: custom_design(feature, INTERFACE_2, section3=section3),
            f"{feature.folder}/design.zh-CN.md": f"# {feature.id} {zh_name(feature)}：接口设计\n"}


def answer_step(number: int = 1) -> Step:
    """A merged ``[rules] Set the features Troy approves`` PR (D62's answer, design 7.4)."""
    return step(APPROVALS_TITLE, {"docs/approvals.md": f"Troy's answer {number}.\n"})


def step_time(index: int, seconds: int = 0) -> str:
    """The committer time of step ``index`` (counted from 0) of an origin without merges.

    Args:
        index: The step's place in the steps given to ``origin_repo``.
        seconds: Seconds to add, which may be negative.

    Returns:
        A GitHub time stamp.
    """
    moment = datetime.fromtimestamp(_FIRST_COMMIT + 60 * (index + 1) + seconds, timezone.utc)
    return moment.strftime(_TIME)


# ------------------------------------------------------------------ marks

def mark(by: str, reason: str, pr: Optional[int] = None, url: Optional[str] = None) -> dict:
    """One risky mark (contract 4)."""
    return {"by": by, "reason": reason, "pr": pr, "url": url}


# ------------------------------------------------------------------ comments

def curl(number: int, index: int) -> str:
    """The URL ``thread`` gives the comment at ``index`` on PR ``number``."""
    return comment_url(number, number * 100 + index)


def thread(number: int, *bodies: str, day: int = 0) -> list:
    """Comments on PR ``number``, one minute apart, each with its URL (``curl``)."""
    return [timed(body, index, curl(number, index), day) for index, body in enumerate(bodies)]


def arch_review(number: int, result: str = "approved", risky: Optional[str] = None,
                finding: str = "Naming: rename count() to count_words().") -> str:
    """An Architect review comment, with AR2's ``Risky:`` line after the findings.

    Args:
        number: The round.
        result: The review's result.
        risky: The value after ``Risky:``, or None for a review without the line.
        finding: The one finding.

    Returns:
        The body.
    """
    body = f"Architect review, round {number}: {result}\n\n1. {finding}"
    return body + (f"\n\nRisky: {risky}" if risky is not None else "")


def ruled(ruler: str = "Product Manager", reviewer: str = ARCH) -> list:
    """Three rounds asking for changes, then a ruling ``merge`` (index 3)."""
    return [*three_rounds(reviewer), ruling(ruler, "merge", *MERGE_FINDINGS)]


def attempts(role: str, *numbers: int) -> list:
    """A role's attempt comments with these numbers."""
    return [f"{role} attempt {n}: failed\n\nruff: {n} errors" for n in numbers]


def tm_ruling(*lines: tuple) -> str:
    """TM8's ``Test Manager ruling, real run`` comment with ``(kind, text)`` lines."""
    return TM_HEADING + "\n\n" + "\n".join(
        f"{index}. {kind}: {text}" for index, (kind, text) in enumerate(lines, start=1))


def note(target: str, text: str, source: str = "Troy, in chat") -> str:
    """A note comment on a progress issue (F07 section 6.6)."""
    return f"Note for {target}, from {source}\n\n{text}\n"


def overturn(link: str) -> str:
    """F07's ``Overturn: <link>`` comment (part 1)."""
    return f"Overturn: {link}\n\nTroy overturned it: the other side wins."


def link_to(number: int, comment: int = 900) -> str:
    """A link to a comment on PR ``number``, as an ``Overturn:`` comment names it."""
    return comment_url(number, comment)


# ------------------------------------------------------------------ PRs

def pr_url(number: int) -> str:
    """A PR's URL."""
    return f"{REPO_URL}/pull/{number}"


def open_pr(number: int, title: str, branch: Optional[str] = None) -> dict:
    """An entry of ``gh pr list --state open``."""
    return {"number": number, "title": title, "headRefName": branch or f"troy-mode/pr-{number}",
            "url": pr_url(number)}


def stage_open(number: int, feature: Feature, stage: int) -> dict:
    """An open stage PR on the stage's branch."""
    return open_pr(number, feature.title(stage), feature.branch(stage))


def listed(number: int, title: str, state: str = "MERGED") -> dict:
    """An entry of ``gh pr list --state all``."""
    return {"number": number, "title": title, "state": state, "url": pr_url(number),
            "createdAt": "2026-11-10T08:00:00Z"}


def all_listed(opened: Sequence[Mapping] = (), merged: Sequence[tuple] = ()) -> list:
    """``gh pr list --state all``: the open PRs as ``OPEN``, then ``(number, title)`` merged."""
    return ([listed(item["number"], item["title"], "OPEN") for item in opened]
            + [listed(number, title) for number, title in merged])


def stage_numbers(feature: Feature, upto: int, base: int) -> list:
    """``(number, title)`` of a feature's merged stages 1 to ``upto``, numbered base + stage."""
    return [(base + n, feature.title(n)) for n in range(1, upto + 1)]


# ------------------------------------------------------------------ issues

def issue_url(number: int) -> str:
    """An issue's URL."""
    return f"{REPO_URL}/issues/{number}"


def issue_comment(issue: int, cid: int, body: str, created: str = NEW_TIME) -> dict:
    """One comment of ``gh issue list --json comments``, with its URL."""
    return {"author": {"login": LOGIN}, "body": body, "createdAt": created,
            "url": f"{issue_url(issue)}#issuecomment-{cid}"}


def gh_issue(number: int, title: str, body: str, labels: Sequence[str],
             found: Sequence[Mapping] = (), state: str = "OPEN",
             reason: Optional[str] = None) -> dict:
    """One issue of ``gh issue list --state all``."""
    return {"number": number, "title": title, "labels": [{"name": n} for n in labels],
            "body": body, "comments": [dict(c) for c in found], "url": issue_url(number),
            "createdAt": "2026-11-02T00:00:00Z", "state": state, "stateReason": reason,
            "author": {"login": LOGIN}}


def progress_issue(number: int, feature: Feature, found: Sequence[Mapping] = (),
                   state: str = "OPEN") -> dict:
    """A progress issue whose body is out of date (its marker and one old line)."""
    body = f"<!-- troy-mode: progress {feature.id} -->\nOld text.\n"
    return gh_issue(number, f"{feature.id} old title", body, ("progress",), found, state,
                    "COMPLETED" if state == "CLOSED" else None)


def closed_idea(number: int, found: Sequence[Mapping] = ()) -> dict:
    """A closed idea issue, which F15 no longer counts as a new idea."""
    return gh_issue(number, f"Idea {number}", "Please change how the count works.", ("idea",),
                    found, "CLOSED", "COMPLETED")


def overturn_issue(number: int, link: str, created: str = NEW_TIME) -> dict:
    """A closed idea issue with one ``Overturn: <link>`` comment."""
    return closed_idea(number, [issue_comment(number, number * 10, overturn(link), created)])


ISSUE_LABELS = ("bug", "idea", "progress", "device-test")


# ------------------------------------------------------------------ clones

class BranchProject(Project):
    """A clone whose own origin also holds PR branches, each one commit on ``main``."""

    def __init__(self, steps: Sequence[Step], branches: Mapping[str, tuple]) -> None:
        """Copies the cached origin, pushes each branch to it, and clones it.

        Args:
            steps: The history of ``origin/main``.
            branches: Branch name mapped to ``(subject, files)``.
        """
        folder = new_dir("spotorigin")
        self.origin = folder / "origin.git"
        git(folder, "clone", "-q", "--bare", str(origin_repo(steps)), str(self.origin))
        git(folder, "clone", "-q", str(self.origin), "side")
        side = folder / "side"
        for branch, (subject, files) in branches.items():
            git(side, "switch", "-q", "-c", branch, "origin/main")
            for rel, content in files.items():
                write_file(side, rel, content)
            git(side, "add", "-A")
            git(side, "commit", "-q", "-m", subject)
            git(side, "push", "-q", "origin", f"{branch}:{branch}")
            git(side, "switch", "-q", "--detach", "origin/main")
        self.tmp = new_dir("spotcase")
        self.root = self.tmp / PROJECT
        git(self.tmp, "clone", "-q", str(self.origin), PROJECT)
        self.git("switch", "-q", "-c", WORK_BRANCH, "origin/main")


def common_git(project: Project) -> Path:
    """The repository's common git folder."""
    return Path(project.git("rev-parse", "--path-format=absolute", "--git-common-dir").strip())


# ------------------------------------------------------------------ running

@dataclass
class Case:
    """One engine run on its own clone.

    Attributes:
        steps: The history of ``origin/main``.
        fakes: The fake gh's answers (``Fakes`` keyword arguments).
        extra: More options after the command.
        command: ``status`` or ``issues``.
        env: More environment variables.
        branches: PR branches the origin also holds, as for ``BranchProject``.
    """

    steps: Sequence[Step]
    fakes: Mapping = field(default_factory=dict)
    extra: Sequence[str] = ()
    command: str = "status"
    env: Optional[Mapping[str, str]] = None
    branches: Optional[Mapping[str, tuple]] = None


def run_case(case: Case) -> tuple:
    """Builds the case's clone and runs the command with ``--json``.

    Returns:
        ``(outcome, fakes, project)``.
    """
    fakes = Fakes(**dict(case.fakes))
    project = BranchProject(case.steps, case.branches) if case.branches else Project(case.steps)
    return project.run(case.command, *case.extra, fakes=fakes, env_extra=case.env), fakes, project


def run_cases(cases: Mapping[str, Case], workers: int = 8) -> dict:
    """Runs each case on its own clone, side by side; name mapped to ``run_case``'s result."""
    names = list(cases)
    return dict(zip(names, parallel(run_case, [cases[n] for n in names], workers)))


def run_without(project: Project, args: Sequence[str], fakes: Fakes, drop: str) -> Outcome:
    """Runs the engine with ``--json`` and ``--repo`` in an environment without one variable."""
    env = base_env(fakes.path_env())
    env.pop(drop, None)
    proc = subprocess.run([sys.executable, str(ENGINE), *args, "--repo", str(project.root),
                           "--json"], cwd=str(project.tmp), env=env, capture_output=True,
                          stdin=subprocess.DEVNULL, timeout=180, check=False)
    stdout = proc.stdout.decode("utf-8", "replace")
    try:
        report = json.loads(stdout)
    except ValueError:
        report = None
    return Outcome(proc.returncode, stdout, proc.stderr.decode("utf-8", "replace"), report)


# ------------------------------------------------------------------ the role exam (E3)

LOG_FIELDS = ("exam", "run", "time", "side", "case_version", "instructions", "cli", "models",
              "effort", "status", "passed", "cost", "minutes")


def case_version(case_id: str) -> int:
    """A case's ``version`` in the plugin's ``troy-mode/exam/cases/<id>/case.toml``."""
    path = PLUGIN_ROOT / "troy-mode" / "exam" / "cases" / case_id / "case.toml"
    return int(tomllib.loads(path.read_bytes().decode("utf-8"))["version"])


def expected_hash() -> str:
    """``troyexam.instructions.instruction_hash(FolderTree(<plugin root>))``."""
    exam = str(PLUGIN_ROOT / "troy-mode" / "exam")
    if exam not in sys.path:
        sys.path.insert(0, exam)
    from troyexam.instructions import FolderTree, instruction_hash  # noqa: PLC0415
    return instruction_hash(FolderTree(PLUGIN_ROOT))


def log_row(time: str, passed: bool, instructions: str, version: int,
            status: str = "ok") -> dict:
    """One row of a case log, ``cases/<case ID>.tsv``."""
    return {"exam": "2026-11-20-1", "run": f"r-{time}", "time": time, "side": "head",
            "case_version": str(version), "instructions": instructions, "cli": "2.1.0",
            "models": "claude-opus", "effort": "high", "status": status,
            "passed": "true" if passed else "false", "cost": "2.50", "minutes": "11"}


def write_logs(root: Path, logs: Mapping[str, Sequence[Mapping]]) -> Path:
    """Writes ``<root>/cases/<case>.tsv`` for each case: the header line, then the rows."""
    folder = Path(root) / "cases"
    folder.mkdir(parents=True, exist_ok=True)
    for case_id, rows in logs.items():
        lines = ["\t".join(LOG_FIELDS)] + ["\t".join(str(row[f]) for f in LOG_FIELDS)
                                            for row in rows]
        (folder / f"{case_id}.tsv").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return Path(root)


def at_minute(minute: int) -> str:
    """A run's ``time``, some minutes after 10:00 UTC on 2026-11-20."""
    return f"2026-11-20T{10 + minute // 60:02d}:{minute % 60:02d}:00Z"


# ------------------------------------------------------------------ assertions

def spot_module():
    """``troyflow.spot``, or an AssertionError that says why it cannot be imported."""
    return engine_module("spot")


class SpotCase(FlowCase):
    """Assertions shared by the part 2 tests. It has no tests of its own."""

    outs: dict = {}

    def report(self, name: str) -> dict:
        """The case's status report, exit 0."""
        return self.report_of(self.outs[name][0], 0, "status")

    def spot(self, name: str):
        """The case's ``spot`` report key, which must be present."""
        report = self.report(name)
        self.assertTrue("spot" in report, f"no 'spot' in the report: {sorted(report)}")
        return report["spot"]

    def open_entry(self, name: str, number: int) -> dict:
        """The ``open_prs`` entry of one PR."""
        found = [p for p in self.report(name)["open_prs"] if p.get("number") == number]
        self.assertEqual(len(found), 1, self.report(name)["open_prs"])
        return found[0]

    def risky_of(self, name: str, number: int):
        """The ``risky`` of one open PR, ``"missing"`` without the key."""
        return self.open_entry(name, number).get("risky", "missing")

    def feature_spots(self, name: str) -> list:
        """``(id, spot)`` of each ``features`` entry, ``"missing"`` without the key."""
        return [(f["id"], f.get("spot", "missing")) for f in self.report(name)["features"]]

    def nxt(self, name: str) -> dict:
        """The case's ``next``."""
        return self.report(name)["next"]


def env_root(root: Path) -> dict:
    """``TROY_EXAM_ROOT`` set to a folder."""
    return {"TROY_EXAM_ROOT": str(root)}


def lf_text(path: Path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""
