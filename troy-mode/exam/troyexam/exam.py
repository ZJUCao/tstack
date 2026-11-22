"""The exam of a PR, a case's proof, and resuming either (design 4.5, 7, 8, 10.2, 10.3, 11.2).

Each run's record is saved as it ends, and state.json says what is planned,
so `resume` goes on after a usage limit, a time-out, or a stop. An exam that
waits for Troy, before it starts, before a second round above the approved
amount, or at the guard, goes on only with `resume --yes` (design 10.3).
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

from . import budget, compare, reuse
from .cases import Case, load_cases
from .checks import UNIVERSAL_MUSTS, case_checks
from .errors import ExamError
from .instructions import GitTree, instruction_hash
from .judge import JUDGE_CAP, anchors_ok, assign_labels, build_folder, filter_diff, run_judge
from .paths import Layout, repository_name
from .project import ensure_mirror, git, lock_key
from .report import block, role_title, write_report
from .runner import cleanup, cli_version
from .runrole import RunSpec, anchor_context, run_role, write_record

FIRST = compare.FIRST
MAX_RERUNS = 2
UNSAFE = ("limit",)
WAITING = "waiting for Troy"
TOO_FEW = "too few runs that count"


def new_exam_id(results: Path, today: str | None = None) -> str:
    """<YYYY-MM-DD>-<n>, the next free n in results/."""
    today = today or time.strftime("%Y-%m-%d")
    n = 1
    while (Path(results) / f"{today}-{n}").exists():
        n += 1
    return f"{today}-{n}"


def resolve(repo: Path, ref: str) -> str:
    """The full commit ID of a ref."""
    return git(repo, "rev-parse", f"{ref}^{{commit}}").strip()


class Exam:
    """One exam's state and the work of each stage.

    Attributes:
        folder: results/<exam ID>.
        state: The saved state, as in state.json.
        layout: The work root.
        repo: The tstack checkout.
        cases: The cases of the exam by ID.
    """

    def __init__(self, folder: Path, state: dict, layout: Layout, env: dict):
        """Wraps a state; nothing runs yet."""
        self.folder, self.state, self.layout, self.env = folder, state, layout, env
        self.repo = Path(state["repo"])
        every = {c.id: c for c in load_cases(Path(state["cases_dir"]))}
        self.cases = {cid: every[cid] for cid in state["cases"]}
        self.lock = threading.Lock()
        self.guard = budget.Guard(state.get("estimate", 0.0))
        self.guard.spent = state.get("spent", 0.0)
        self.cli = Path(state["cli"])
        self.paused = False
        self.waiting = False

    # -------------------------------------------------------------- state
    def save(self) -> None:
        """Writes state.json."""
        with self.lock:
            self.state["spent"] = round(self.guard.spent, 6)
            self.state["estimate"] = round(self.guard.estimate, 6)
            self.folder.mkdir(parents=True, exist_ok=True)
            (self.folder / "state.json").write_text(json.dumps(self.state, indent=1), encoding="utf-8")

    def run_dir(self, run_id: str) -> Path:
        """results/<exam>/runs/<run ID>."""
        return self.folder / "runs" / run_id

    def record(self, run_id: str) -> dict | None:
        """A run's saved record, or None."""
        path = self.run_dir(run_id) / "run.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def runs_of(self, cid: str, side: str) -> list[dict]:
        """The case's finished runs of one side, reused ones included, in plan order."""
        found = list(self.state["cases"][cid].get("reused", [])) if side == "base" else []
        for slot in self.state["plan"]:
            if slot["case"] == cid and slot["side"] == side:
                rec = self.final_record(slot)
                if rec is not None and rec["status"] not in UNSAFE:
                    found.append(rec)
        return found

    def final_record(self, slot: dict) -> dict | None:
        """The last attempt's record of a planned slot."""
        last = None
        for attempt in range(MAX_RERUNS + 1):
            rec = self.record(slot["id"] + (f"-r{attempt}" if attempt else ""))
            if rec is None:
                break
            last = rec
        return last

    # -------------------------------------------------------------- runs
    def env_prefix(self, case: Case) -> Path:
        """The case's environment prefix."""
        return Path(self.state["envs"][case.id])

    def _spec(self, slot: dict, run_id: str, driver: str) -> RunSpec:
        """The RunSpec of one attempt."""
        case = self.cases[slot["case"]]
        side = slot["side"]
        return RunSpec(case=case, side=side, commit=self.state[f"{side}_commit"],
                       instructions=self.state[f"{side}_hash"], layout=self.layout, repo=self.repo,
                       mirror=Path(self.state["mirrors"][case.id]), env_prefix=self.env_prefix(case),
                       cli=self.cli, cli_version=self.state["cli_version"], out=self.run_dir(run_id),
                       run_id=run_id, python=sys.executable, parent_env=self.env, driver_model=driver)

    def _attempt(self, slot: dict) -> tuple[str, str] | None:
        """The next attempt of a slot: (run ID, driver model), or None when it is settled."""
        driver = "haiku"
        for attempt in range(MAX_RERUNS + 1):
            run_id = slot["id"] + (f"-r{attempt}" if attempt else "")
            rec = self.record(run_id)
            if rec is None or rec["status"] in UNSAFE:
                return run_id, driver
            if rec["status"] != "void":
                return None
            driver = "sonnet" if str(rec.get("reason", "")).startswith("brief") else driver
        return None

    def _one(self, slot: dict, run_id: str, driver: str) -> dict:
        """Runs one attempt; a run that cannot start becomes a void record."""
        try:
            rec = run_role(self._spec(slot, run_id, driver))
        except ExamError as exc:
            if str(exc).startswith("blinding"):
                raise
            spec = self._spec(slot, run_id, driver)
            rec = {"run": run_id, "case": slot["case"], "side": slot["side"], "status": "void",
                   "reason": str(exc), "cost": 0.0, "costs": {}, "models": [], "passed": None,
                   "case_version": spec.case.version, "instructions": spec.instructions,
                   "cli": spec.cli_version, "effort": spec.case.run.effort,
                   "time": time.strftime(reuse.TIME, time.gmtime()), "minutes": 0.0}
            write_record(spec.out, rec)
        return rec

    def execute(self, jobs: int) -> None:
        """Runs every unsettled slot, base and head alternating, at most jobs at a time."""
        pending = list(self.state["plan"])
        running: dict = {}
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            while pending or running:
                while pending and len(running) < jobs and not self.paused:
                    slot = pending[0]
                    nxt = self._attempt(slot)
                    if nxt is None:
                        pending.pop(0)
                        continue
                    if not self.guard.may_start():
                        # The guard waits for Troy; it never decides a case (D243).
                        self.waiting = True
                        pending.clear()
                        break
                    pending.pop(0)
                    running[pool.submit(self._one, slot, *nxt)] = slot
                if not running:
                    break
                done, _ = wait(list(running), return_when=FIRST_COMPLETED)
                for future in done:
                    slot = running.pop(future)
                    rec = future.result()
                    with self.lock:
                        self.guard.add(float(rec.get("cost") or 0.0))
                    if rec["status"] == "limit":
                        self.paused = True
                    elif rec["status"] == "void" and self._attempt(slot) is not None:
                        pending.insert(0, slot)
                    self.save()

    # -------------------------------------------------------------- judge
    def _anchor_grades(self, case: Case) -> dict:
        """Grades both anchors by script once, with their files for the judge."""
        cached = self.state["cases"][case.id].get("anchors")
        if cached:
            return cached
        grades = {}
        for kind in ("fail", "pass"):
            work = self.folder / "anchors" / case.id / kind
            ctx, root = anchor_context(case, self.layout, Path(self.state["mirrors"][case.id]),
                                       self.env_prefix(case), kind, self.env, work / "work",
                                       engine=self.repo)
            try:
                results = case_checks(ctx)
                files = {}
                from .instructions import glob_match
                for path in git(ctx.project, "ls-files", "--cached", "--others",
                                "--exclude-standard").splitlines():
                    if any(glob_match(path, g) for g in case.judge_files) and (ctx.project / path).is_file():
                        files[f"files/{path}"] = (ctx.project / path).read_text(encoding="utf-8",
                                                                               errors="replace")
            finally:
                cleanup([root])
            grades[kind] = {"criteria": {k: {"passed": v.passed, "evidence": v.evidence}
                                         for k, v in results.items()}, "files": files}
        self.state["cases"][case.id]["anchors"] = grades
        self.save()
        return grades

    def _outputs(self, case: Case, rec: dict | None, kind: str | None) -> dict[str, str]:
        """The files of one run or anchor that the judge sees."""
        if kind is not None:
            folder = case.anchor(kind)
            files = dict(self.state["cases"][case.id]["anchors"][kind]["files"])
        else:
            folder = self.run_dir(rec["run"])
            files = {}
            files_dir = folder / "files"
            if files_dir.is_dir():
                for path in files_dir.rglob("*"):
                    if path.is_file():
                        files[f"files/{path.relative_to(files_dir).as_posix()}"] = \
                            path.read_text(encoding="utf-8", errors="replace")
        diff = (folder / "diff.patch").read_text(encoding="utf-8", errors="replace") \
            if (folder / "diff.patch").is_file() else ""
        report = (folder / "report.md").read_text(encoding="utf-8", errors="replace") \
            if (folder / "report.md").is_file() else ""
        return {"diff.patch": filter_diff(diff, case.judge_diff), "report.md": report, **files}

    def _shared(self, case: Case) -> dict[str, str]:
        """The files every run shares: the change under review and the start files the rubric names."""
        shared = {}
        if case.start_patch is not None:
            shared["change.patch"] = case.start_patch.read_text(encoding="utf-8", errors="replace")
        mirror = Path(self.state["mirrors"][case.id])
        for path in case.judge_shared:
            proc = subprocess.run(["git", "--git-dir", str(mirror), "show",
                                   f"{case.start.commit}:{path}"], capture_output=True)
            if proc.returncode == 0:
                shared[path] = proc.stdout.decode("utf-8", errors="replace")
        return shared

    def judge(self, case: Case, records: list[dict], label_seed: int) -> dict | None:
        """One judge pass over the records and both anchors; None when the anchors were misgraded.

        Returns:
            label -> criterion number -> (pass, evidence), with "key" mapping labels to items.
        """
        rubric = case.rubric_path.read_text(encoding="utf-8")
        from .cases import rubric_criteria
        count = len(rubric_criteria(rubric))
        items = [r["run"] for r in records] + ["anchor-fail", "anchor-pass"]
        key = assign_labels(items, random.Random(label_seed))
        by_run = {r["run"]: r for r in records}
        outputs = {label: (self._outputs(case, None, item.split("-", 1)[1]) if item.startswith("anchor-")
                           else self._outputs(case, by_run[item], None))
                   for label, item in key.items()}
        n = len(self.state["cases"][case.id].setdefault("judge_passes", []))
        folder = self.folder / "judge" / f"{case.id}-{n + 1}"
        build_folder(folder, rubric, outputs, {}, self._shared(case))
        # The key stays in the results folder, outside the judge's folder (design 6.2).
        keys = self.folder / "keys" / f"{case.id}-{n + 1}"
        keys.mkdir(parents=True, exist_ok=True)
        (keys / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
        verdict, cost = run_judge(self.cli, folder, count, list(key), self.env, JUDGE_CAP)
        with self.lock:
            self.guard.add(cost)
        musts = [c.judge for c in case.criteria if c.judge is not None and c.must]
        anchors = self.state["cases"][case.id]["anchors"]
        overall = {}
        for label, item in key.items():
            judged = all(verdict[label][m][0] for m in musts)
            if item.startswith("anchor-"):
                kind = item.split("-", 1)[1]
                scripts = all(v["passed"] for cid, v in anchors[kind]["criteria"].items()
                              if any(c.id == cid and c.must for c in case.criteria))
            else:
                scripts = True
            overall[label] = judged and scripts
        good = anchors_ok(overall, key)
        self.state["cases"][case.id]["judge_passes"].append(
            {"folder": folder.name, "cost": cost, "anchors_ok": good,
             "verdict": {label: {str(k): list(v) for k, v in grades.items()} for label, grades in verdict.items()},
             "key": key})
        self.save()
        return {"verdict": verdict, "key": key} if good else None

    def grade_case(self, case: Case, records: list[dict], anchors_only_pass: bool = False) -> bool:
        """Judges a case's runs: one pass, once more after a misgraded anchor (design 6.2).

        Returns:
            False when the case stops as "rubric unclear".
        """
        info = self.state["cases"][case.id]
        self._anchor_grades(case)
        if not case.judge_criteria():
            for rec in records:
                if rec.get("passed") is None:
                    rec["passed"] = self._scripts_ok(case, rec)
                    write_record(self.run_dir(rec["run"]), rec)
            return True
        pending = [r for r in records if r["status"] == "ok" and r.get("passed") is None]
        if not pending and info.get("judged"):
            return True
        # Every run of both versions in one pass, on one scale (design 6.2).
        judged = [r for r in records if r["status"] == "ok"]
        result = None
        for attempt in range(2):
            result = self.judge(case, judged, label_seed=hash((case.id, len(records), attempt)) & 0xFFFF)
            if result is not None:
                break
        if result is None:
            self.state["cases"][case.id]["unclear"] = True
            self.save()
            return False
        musts = [c.judge for c in case.criteria if c.judge is not None and c.must]
        for label, item in result["key"].items():
            if item.startswith("anchor-"):
                continue
            rec = next(r for r in judged if r["run"] == item)
            rec["judge"] = {str(k): list(v) for k, v in result["verdict"][label].items()}
            rec["passed"] = self._scripts_ok(case, rec) and all(
                result["verdict"][label][m][0] for m in musts)
            write_record(self.run_dir(rec["run"]), rec)
        if anchors_only_pass:
            second = None
            for attempt in range(2):
                second = self.judge(case, [], label_seed=hash((case.id, "anchors", attempt)) & 0xFFFF)
                if second is not None:
                    break
            if second is None:
                self.state["cases"][case.id]["unclear"] = True
                self.save()
                return False
        info["judged"] = True
        self.save()
        return True

    @staticmethod
    def _scripts_ok(case: Case, rec: dict) -> bool:
        """Tells whether a run passed every universal check and every must check by script."""
        criteria = rec.get("criteria") or {}
        musts = [c.id for c in case.criteria if c.must and c.check is not None]
        names = [*UNIVERSAL_MUSTS, *musts]
        return rec.get("status") == "ok" and all(criteria.get(n, {}).get("passed") for n in names)


def _start_state(args, layout: Layout, env: dict, command: str) -> tuple[Path, dict]:
    """Makes the results folder and the parts of state that every command shares."""
    exam_id = new_exam_id(layout.results)
    folder = layout.result(exam_id)
    folder.mkdir(parents=True)
    from .runner import find_cli
    cli = find_cli(env)
    state = {"exam": exam_id, "command": command, "repo": str(Path(args.repo_path)),
             "cases_dir": str(Path(args.cases_path)), "cli": str(cli), "cli_version": cli_version(cli),
             "jobs": int(getattr(args, "jobs", 2) or 2), "status": "running", "plan": [], "cases": {},
             "envs": {}, "mirrors": {}, "estimate": 0.0, "spent": 0.0,
             "started": time.strftime(reuse.TIME, time.gmtime())}
    return folder, state


def _prepare_case(state: dict, case: Case, layout: Layout, env_override: str | None) -> None:
    """Records the case's mirror and environment."""
    mirror = ensure_mirror(layout, case.start.repository, case.start.commit)
    state["mirrors"][case.id] = str(mirror)
    state["envs"][case.id] = env_override or str(_ensure_case_env(layout, case, mirror))


def _ensure_case_env(layout: Layout, case: Case, mirror: Path) -> Path:
    """The environment of a case's start, created from the start's files when missing."""
    from .project import ensure_env
    with tempfile.TemporaryDirectory(dir=layout.root) as tmp:
        folder = Path(tmp) / repository_name(case.start.repository)
        folder.mkdir()
        for name in ("environment.yml", "requirements-dev.lock"):
            proc = subprocess.run(["git", "--git-dir", str(mirror), "show",
                                   f"{case.start.commit}:{name}"], capture_output=True)
            if proc.returncode == 0:
                (folder / name).write_bytes(proc.stdout)
        return ensure_env(layout, case.start.repository, folder)


def _expected_models(rows: list[dict], cli: str) -> list[str] | None:
    """The model IDs of the case's newest run with this CLI; None without one."""
    same = [r for r in rows if r.get("cli") == cli and r.get("status") != "void" and r.get("models")]
    if not same:
        return None
    return sorted(reuse.models_of(max(same, key=lambda r: r.get("time", ""))))


def plan_slots(cid: str, side: str, start: int, count: int, cost: float = 0.0) -> list[dict]:
    """Slots <case>-<side>-<nn> numbered from start, each with its estimated cost."""
    return [{"id": f"{cid}-{side}-{n:02d}", "case": cid, "side": side, "cost": round(cost, 6)}
            for n in range(start + 1, start + count + 1)]


def interleave(slots: list[dict]) -> list[dict]:
    """Orders slots so that base and head runs alternate, case by case."""
    base = [s for s in slots if s["side"] == "base"]
    head = [s for s in slots if s["side"] == "head"]
    out = []
    while base or head:
        if base:
            out.append(base.pop(0))
        if head:
            out.append(head.pop(0))
    return out


def run_exam(args, layout: Layout, env: dict) -> tuple[dict, int]:
    """The exam of a PR (design 8.1): affected cases, estimate, runs, judge, comparison, report."""
    from .affected import affected
    repo = Path(args.repo_path)
    head = resolve(repo, args.head or "HEAD")
    base = git(repo, "merge-base", resolve(repo, args.base), head).strip()
    every = {c.id: c for c in load_cases(Path(args.cases_path))}
    unknown = [c for c in (args.case or []) + (args.fixes or []) if c not in every]
    if unknown:
        raise ExamError(f"no case named {unknown[0]}")
    folder, state = _start_state(args, layout, env, "run")
    state.update(base_commit=base, head_commit=head,
                 base_hash=instruction_hash(GitTree(repo, base)),
                 head_hash=instruction_hash(GitTree(repo, head)), fixes=list(args.fixes or []))
    if args.case:
        chosen, not_affected = list(dict.fromkeys(args.case)), []
    else:
        found = affected(repo, base, head, list(every.values()), layout,
                         dict(env, TROY_MODE_ENV_PREFIX=args.env or ""))
        state["affected"] = found
        chosen = [r["case"] for r in found if r["affected"]]
        not_affected = [r["case"] for r in found if not r["affected"]]
    state["not_affected"] = not_affected
    if not chosen:
        return _finish_none(folder, state, len(not_affected))
    now = datetime.now(timezone.utc)
    plan, slots = [], []
    for cid in chosen:
        case = every[cid]
        _prepare_case(state, case, layout, args.env)
        rows = reuse.read_log(layout.case_log(cid))
        models = _expected_models(rows, state["cli_version"])
        reused = [] if models is None else reuse.reusable_runs(
            [r for r in rows if r.get("side") == "base"], case_version=case.version,
            instructions=state["base_hash"], cli=state["cli_version"], models=models,
            effort=case.run.effort, now=now)[:FIRST]
        kind = "target" if cid in state["fixes"] else "not-worse"
        median = budget.median_cost(rows, case.role)
        state["cases"][cid] = {"kind": kind, "reused": [_row_record(r) for r in reused],
                               "stage": "runs", "median": median}
        slots += (plan_slots(cid, "base", 0, FIRST - len(reused), median)
                  + plan_slots(cid, "head", 0, FIRST, median))
        plan.append(budget.Planned(cid, case.role, 2 * FIRST, len(reused),
                                   1 if case.judge_criteria() else 0, median))
    state["plan"] = interleave(slots)
    # Two totals: the first round, and the whole with every case's second round (10.3).
    state["estimate"] = round(budget.estimate(plan), 2)
    state["whole"] = round(budget.whole(plan), 2)
    # The $60 line applies to the first round; Troy's yes covers the whole (D241).
    state["approved"] = state["whole"] if args.yes else budget.ASK_ABOVE
    exam = Exam(folder, state, layout, env)
    if budget.needs_approval(state["estimate"]) and not args.yes:
        return _wait(exam, "start")
    exam.save()
    return continue_exam(exam)


def _row_record(row: dict) -> dict:
    """A reused tsv row as a run record; it costs nothing now, and keeps its recorded cost."""
    try:
        recorded = float(row.get("cost"))
    except (TypeError, ValueError):
        recorded = None
    return {"run": row.get("run"), "status": row.get("status"), "passed": row.get("passed") == "true",
            "cost": 0.0, "recorded_cost": recorded, "reused": True, "exam": row.get("exam")}


def _version_cost(exam: "Exam", cid: str, side: str) -> float:
    """A version's cost per run from its runs that count in this exam (D242).

    A reused run counts at its recorded cost; without any run, the case's median.
    """
    costs = []
    for rec in exam.runs_of(cid, side):
        if rec.get("status") == "void":
            continue
        cost = rec.get("recorded_cost") if rec.get("reused") else rec.get("cost")
        if cost is not None:
            costs.append(float(cost))
    info = exam.state["cases"][cid]
    return budget.own_cost(costs, info.get("median", budget.ROLE_MEDIAN[exam.cases[cid].role]))


def _left(exam: "Exam") -> float:
    """The estimate of what is left: each unsettled slot, and one judge pass per open case."""
    state = exam.state
    left = 0.0
    for slot in state["plan"]:
        if exam._attempt(slot) is not None:
            left += float(slot.get("cost", state["cases"][slot["case"]].get("median", 0.0)))
    for cid, info in state["cases"].items():
        if info.get("stage") != "done" and exam.cases[cid].judge_criteria():
            left += budget.JUDGE_COST
    return left


def _wait(exam: "Exam", why: str, asked: float = 0.0) -> tuple[dict, int]:
    """Saves the exam as waiting for Troy, and reports what is spent and what is left (10.3)."""
    state = exam.state
    spent, left = exam.guard.spent, _left(exam)
    state["status"] = WAITING
    state["waiting"] = {"why": why, "spent": round(spent, 2), "left": round(left, 2)}
    exam.save()
    again = f"Troy must say yes: `troy_exam.py resume {state['exam']} --yes`, or end it with `--stop`"
    if why == "start":
        problem = (f"the estimate ${state['estimate']:.2f} (${state.get('whole', 0.0):.2f} with every "
                   f"second round) is above ${budget.ASK_ABOVE:.0f}; {again}")
    elif why == "line":
        problem = (f"a second round would take the exam to ${spent + asked:.2f}, above the approved "
                   f"${state.get('approved', budget.ASK_ABOVE):.2f}; {again}")
    else:
        problem = (f"the exam has spent ${spent:.2f}, {budget.STOP_FACTOR} times its estimate "
                   f"${exam.guard.estimate:.2f}, and ${left:.2f} is left; {again}")
    return {"command": state["command"], "ok": False, "exam": state["exam"], "status": WAITING,
            "why": why, "spent": round(spent, 2), "left": round(left, 2),
            "estimate": round(exam.guard.estimate, 2), "whole": state.get("whole"),
            "cases": list(state["cases"]), "problems": [problem]}, 2


def continue_exam(exam: "Exam") -> tuple[dict, int]:
    """Runs what is left of an exam, judges, compares, and reports; also the body of resume."""
    state = exam.state
    while True:
        exam.execute(state["jobs"])
        if exam.paused:
            state["status"] = "paused"
            exam.save()
            return _paused(exam)
        if exam.waiting:
            return _wait(exam, "guard")
        more, asked = [], 0.0
        for cid, info in state["cases"].items():
            if info.get("stage") == "done":
                continue
            case = exam.cases[cid]
            records = [r for r in exam.runs_of(cid, "base") + exam.runs_of(cid, "head")
                       if not r.get("reused")]
            try:
                clear = exam.grade_case(case, records, anchors_only_pass=(state["command"] == "prove"))
            except ExamError as exc:
                if str(exc).startswith("limit"):
                    state["status"] = "paused"
                    exam.save()
                    return _paused(exam)
                raise
            if not clear:
                info.update(stage="done", outcome="fail", why="rubric unclear")
                continue
            if state["command"] == "prove":
                info["stage"] = "done"
                continue
            base_pass, base_n = compare.counts(exam.runs_of(cid, "base"))
            head_pass, head_n = compare.counts(exam.runs_of(cid, "head"))
            runs = min(base_n, head_n)
            wanted = compare.SECOND if info.get("stage") == "more" else FIRST
            if runs < wanted:
                # Too few runs that count, since reruns ran out: no verdict (10.3).
                _no_verdict(info, exam, cid, TOO_FEW)
                continue
            outcome = compare.decide(info["kind"], base_pass, head_pass, runs)
            if outcome == "more" and runs < compare.SECOND and info.get("stage") != "more":
                info["stage"] = "more"
                # The second round from each version's own runs (D242): all its runs are new.
                base_cost, head_cost = _version_cost(exam, cid, "base"), _version_cost(exam, cid, "head")
                info["second"] = round(budget.second_round(base_cost, head_cost,
                                                           1 if case.judge_criteria() else 0), 6)
                asked += info["second"]
                more += (plan_slots(cid, "base", FIRST, budget.MORE, base_cost)
                         + plan_slots(cid, "head", FIRST, budget.MORE, head_cost))
                continue
            if outcome == "more":
                outcome = "fail"
            info.update(stage="done", outcome=outcome, base=base_pass, head=head_pass, of=runs)
        exam.save()
        if not more:
            break
        state["plan"] += interleave(more)
        # The guard counts the second rounds asked for, and no others (D243).
        exam.guard.extend(asked)
        exam.save()
        if budget.needs_approval(exam.guard.spent + asked, state.get("approved", budget.ASK_ABOVE)):
            return _wait(exam, "line", asked)
    return _report(exam)


def _no_verdict(info: dict, exam: "Exam", cid: str, why: str) -> None:
    """Ends a case with no verdict, counting the runs that have a grade on each side (10.3)."""
    graded = {}
    for side in ("base", "head"):
        runs = [r for r in exam.runs_of(cid, side)
                if r.get("status") != "ok" or r.get("passed") is not None]
        graded[side] = compare.counts(runs)
    (base_pass, base_n), (head_pass, head_n) = graded["base"], graded["head"]
    info.update(stage="done", outcome="fail", no_verdict=True, why=why, base=base_pass,
                head=head_pass, of=min(base_n, head_n), base_of=base_n, head_of=head_n)


def stop_exam(exam: "Exam") -> tuple[dict, int]:
    """Ends an exam with the runs it has, on Troy's `resume --stop` (10.3)."""
    for cid, info in exam.state["cases"].items():
        if info.get("stage") != "done":
            _no_verdict(info, exam, cid, "stopped by Troy")
    exam.state.pop("waiting", None)
    return _report(exam)


def _paused(exam: Exam) -> tuple[dict, int]:
    """The report of a paused exam."""
    return {"command": exam.state["command"], "ok": False, "exam": exam.state["exam"],
            "status": "paused", "problems": [f"paused at a usage limit; run `troy_exam.py resume "
                                             f"{exam.state['exam']}` later"]}, 2


def _finish_none(folder: Path, state: dict, not_affected: int) -> tuple[dict, int]:
    """The report of an exam whose change affects no case."""
    summary = {"exam": state["exam"], "result": "no case affected", "instructions": state["head_hash"],
               "cases_run": 0, "cases_not_affected": not_affected, "runs": 0, "reused": 0,
               "cost": 0.0, "minutes": 0.0, "rows": [], "report": str(folder / "report.md")}
    state["status"] = "done"
    state["summary"] = summary
    (folder / "state.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
    write_report(folder, summary, ["No case is affected: every case's brief, agent file, and plugin "
                                   "files are the same in both versions."])
    return {"command": "run", "ok": True, "exam": state["exam"], "summary": summary,
            "block": block(summary)}, 0


def _report(exam: Exam) -> tuple[dict, int]:
    """Writes the report and gives the command's result."""
    state = exam.state
    rows, details, runs, reused, minutes = [], [], 0, 0, 0.0
    passed_all = True
    for cid, info in state["cases"].items():
        case = exam.cases[cid]
        records = exam.runs_of(cid, "base") + exam.runs_of(cid, "head")
        runs += len(records)
        reused += sum(1 for r in records if r.get("reused"))
        minutes += sum(float(r.get("minutes") or 0) for r in records)
        if state["command"] == "prove":
            rows.append(_prove_row(exam, case, info))
            passed_all &= info.get("proved", False)
        else:
            outcome = info.get("outcome", "fail")
            passed_all &= outcome == "pass"
            row = {"case": cid, "role": case.role, "base": info.get("base", 0),
                   "head": info.get("head", 0), "of": info.get("of", FIRST)}
            if info.get("why") == "rubric unclear":
                row["result"] = "rubric unclear"
            elif info.get("no_verdict"):
                # The guard or Troy cut it short: never the rule's word (10.3).
                row.update(base=f"{info.get('base', 0)} of {info.get('base_of', 0)}",
                           head=f"{info.get('head', 0)} of {info.get('head_of', 0)}",
                           result="no verdict")
            else:
                row["result"] = compare.result_word(info["kind"], outcome)
            rows.append(row)
        details += _case_details(exam, case, records)
        _log_rows(exam, case, records)
    hash_key = "base_hash" if state["command"] == "prove" else "head_hash"
    summary = {"exam": state["exam"], "result": "passed" if passed_all else "failed",
               "instructions": state[hash_key], "cases_run": len(state["cases"]),
               "cases_not_affected": len(state.get("not_affected", [])), "runs": runs,
               "reused": reused, "cost": round(exam.guard.spent, 2),
               "minutes": _elapsed(state), "rows": rows, "report": str(exam.folder / "report.md")}
    state["summary"], state["status"] = summary, "done"
    exam.save()
    write_report(exam.folder, summary, details)
    return {"command": state["command"], "ok": passed_all, "exam": state["exam"], "summary": summary,
            "block": block(summary)}, 0 if passed_all else 1


def _elapsed(state: dict) -> float:
    """Minutes since the exam started."""
    start = reuse.parse_time(state.get("started", ""))
    return round((datetime.now(timezone.utc) - start).total_seconds() / 60, 1) if start else 0.0


def _prove_row(exam: Exam, case: Case, info: dict) -> dict:
    """A proof's row: the anchors' grades, the pass count on main, and whether the trap is live."""
    anchors = info.get("anchors", {})
    passes = info.get("judge_passes", [])
    fail_ok = pass_ok = bool(passes) or not case.judge_criteria()
    if passes:
        fail_ok = pass_ok = all(p["anchors_ok"] for p in passes[-2:])
    musts = [c.id for c in case.criteria if c.must and c.check is not None]
    scripts_fail = any(not anchors.get("fail", {}).get("criteria", {}).get(m, {}).get("passed", True)
                       for m in musts)
    scripts_pass = all(anchors.get("pass", {}).get("criteria", {}).get(m, {}).get("passed", False)
                       for m in musts)
    if not case.judge_criteria():
        fail_ok, pass_ok = scripts_fail, scripts_pass
    else:
        pass_ok = pass_ok and scripts_pass
    passed, counted = compare.counts(exam.runs_of(case.id, "base"))
    proved = fail_ok and pass_ok and not info.get("unclear")
    live = counted > 0 and passed < counted
    info.update(proved=proved, live=live, base=passed, of=counted)
    word = ("proved, live" if live else "proved, not live") if proved else "not proved"
    if counted == 0:
        word = "anchors proved" if proved else "anchors not proved"
    if info.get("unclear"):
        word = "rubric unclear"
    return {"case": case.id, "role": case.role, "base": passed, "head": "-", "of": counted or FIRST,
            "result": word}


def _case_details(exam: Exam, case: Case, records: list[dict]) -> list[str]:
    """The report's section of one case: each run's status, criteria that failed, and cost."""
    lines = [f"## {case.id} ({role_title(case.role)}, {case.task})", ""]
    info = exam.state["cases"][case.id]
    for kind in ("fail", "pass"):
        grades = info.get("anchors", {}).get(kind, {}).get("criteria", {})
        failed = [k for k, v in grades.items() if not v["passed"]]
        lines.append(f"- anchor {kind}: scripts {'fail ' + ', '.join(failed) if failed else 'pass'}")
    for p in info.get("judge_passes", []):
        lines.append(f"- judge pass {p['folder']}: anchors {'graded right' if p['anchors_ok'] else 'misgraded'}, "
                     f"${p['cost']:.2f}")
    for rec in records:
        failed = [k for k, v in (rec.get("criteria") or {}).items() if not v.get("passed")]
        judge_failed = [k for k, v in (rec.get("judge") or {}).items() if not v[0]]
        lines.append(f"- {rec['run']}: {rec.get('status')}, passed {rec.get('passed')}, "
                     f"${float(rec.get('cost') or 0):.2f}, {float(rec.get('minutes') or 0):.1f} min"
                     + (f"; failed {', '.join(failed)}" if failed else "")
                     + (f"; judge failed {', '.join(judge_failed)}" if judge_failed else "")
                     + (f"; {rec.get('reason')}" if rec.get("reason") else ""))
    return lines + [""]


def _log_rows(exam: Exam, case: Case, records: list[dict]) -> None:
    """Adds this exam's new runs to cases/<case ID>.tsv, once."""
    logged = set(exam.state.setdefault("logged", []))
    for rec in records:
        if rec.get("reused") or rec["run"] in logged or rec.get("status") == "limit":
            continue
        if rec.get("status") == "ok" and rec.get("passed") is None:
            # Never graded, as when Troy stopped the exam: not a failed run to reuse.
            continue
        reuse.append_log(exam.layout.case_log(case.id), {
            "exam": exam.state["exam"], "run": rec["run"], "time": rec.get("time"),
            "side": rec.get("side"), "case_version": rec.get("case_version"),
            "instructions": rec.get("instructions"), "cli": rec.get("cli"),
            "models": rec.get("models") or [], "effort": rec.get("effort"), "status": rec.get("status"),
            "passed": bool(rec.get("passed")), "cost": rec.get("cost"), "minutes": rec.get("minutes")})
        logged.add(rec["run"])
    exam.state["logged"] = sorted(logged)


def prove(args, layout: Layout, env: dict) -> tuple[dict, int]:
    """Proves cases (design 4.5): the anchors, and five runs on the ref unless --anchors."""
    repo = Path(args.repo_path)
    every = {c.id: c for c in load_cases(Path(args.cases_path))}
    unknown = [c for c in args.cases if c not in every]
    if unknown:
        raise ExamError(f"no case named {unknown[0]}")
    ref = resolve(repo, args.ref or "origin/main")
    folder, state = _start_state(args, layout, env, "prove")
    state.update(base_commit=ref, base_hash=instruction_hash(GitTree(repo, ref)), head_commit=ref,
                 head_hash=instruction_hash(GitTree(repo, ref)))
    slots, plan = [], []
    for cid in dict.fromkeys(args.cases):
        case = every[cid]
        _prepare_case(state, case, layout, args.env)
        rows = reuse.read_log(layout.case_log(cid))
        median = budget.median_cost(rows, case.role)
        state["cases"][cid] = {"kind": "prove", "reused": [], "stage": "runs", "median": median}
        if not args.anchors:
            slots += plan_slots(cid, "base", 0, FIRST, median)
        plan.append(budget.Planned(cid, case.role, 0 if args.anchors else FIRST, 0,
                                   2 if case.judge_criteria() else 0, median))
    state["plan"] = slots
    # A proof has no second round; its guard waits for Troy like the exam's (10.3).
    state["estimate"] = state["whole"] = round(budget.estimate(plan), 2)
    state["approved"] = budget.ASK_ABOVE
    exam = Exam(folder, state, layout, env)
    exam.save()
    return continue_exam(exam)


def resume(args, layout: Layout, env: dict) -> tuple[dict, int]:
    """Goes on with a paused or stopped exam; one that waits for Troy needs --yes or --stop (10.3)."""
    yes, stop = bool(getattr(args, "yes", False)), bool(getattr(args, "stop", False))
    if yes and stop:
        raise ExamError("--yes and --stop do not go together")
    folder = layout.result(args.exam)
    path = folder / "state.json"
    if not path.is_file():
        raise ExamError(f"no exam {args.exam} in {layout.results}")
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("status") == "done":
        summary = state["summary"]
        return {"command": "resume", "ok": summary["result"] != "failed", "exam": args.exam,
                "summary": summary, "block": block(summary)}, 0 if summary["result"] != "failed" else 1
    waits = state.get("status") == WAITING
    if waits and not (yes or stop):
        raise ExamError(f"exam {args.exam} waits for Troy; go on with `resume {args.exam} --yes` "
                        f"(Troy's yes) or end it with `resume {args.exam} --stop`")
    exam = Exam(folder, state, layout, env)
    if stop:
        return stop_exam(exam)
    if waits:
        why = (state.get("waiting") or {}).get("why", "start")
        if why == "start":
            # Troy's yes before the start covers the whole (D241).
            state["approved"] = state.get("whole", state.get("estimate", 0.0))
        else:
            total = exam.guard.spent + _left(exam)
            state["approved"] = exam.guard.estimate = total
        state.pop("waiting", None)
    state["status"] = "running"
    return continue_exam(exam)
