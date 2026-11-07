"""The snapshot before a role run and the check after it (F07 design 6.2 and 7, D59).

The tree is clean at the snapshot, so every change git lists after the run is
the run's own. The engine reports what to stage, what is wrong, and how to undo
it; the skill does the staging and the undoing.
"""

import json
import secrets
import shlex
import time
from pathlib import Path

from troycheck.classify import classify
from troycheck.globs import matches_any
from troyhook.scopes import SCOPES
from troyhook.writes import allows

from . import repo as git
from .errors import FlowError
from .repo import Repo
from .sections import outside_section_four

ROLES = ("architect", "interface-designer", "test-manager", "developer", "test-engineer",
         "code-reviewer", "product-manager")
# The Product Manager's scope (F04 section 3). F05 does not limit the main
# session, so F07 does.
PRODUCT_MANAGER = ("docs/requirements*.md", "docs/prototypes/**", "CHANGELOG*.md",
                   ".troy-mode/progress.md")
DESIGNS = "docs/features/*/design*.md"
_TIME = "%Y-%m-%dT%H:%M:%SZ"


def _records(repo: Repo) -> Path:
    """Returns <git dir>/troy-mode/flow, where run records live."""
    return repo.state_dir() / "flow"


def snapshot(args) -> tuple[dict, int]:
    """Records the state before a role run (design 6.2, step 1).

    Args:
        args: Parsed options: role (a list) and repo.

    Returns:
        The report and the exit code: 1, and no record, when the tree is not clean.
    """
    repo = git.need_repo(args.repo)
    roles = list(dict.fromkeys(args.role))
    report = {"command": "snapshot", "ok": False, "notes": [], "problems": [], "run": None,
              "roles": roles}
    dirty = git.changed_paths(repo)
    if dirty:
        report["problems"] = [{"kind": "dirty", "path": path,
                               "message": f"{path} has changes ({code.strip()}); commit or undo "
                                          "them before a role runs."} for code, path in dirty]
        return report, 1
    now = time.gmtime()
    run = time.strftime("%Y%m%dT%H%M%SZ", now) + "-" + secrets.token_hex(4)
    record = {"run": run, "roles": roles, "head": git.commit_of(repo, "HEAD"),
              "branch": git.branch(repo), "time": time.strftime(_TIME, now)}
    folder = _records(repo)
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / f"{run}.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle)
    report.update(ok=True, **record)
    return report, 0


def _load(repo: Repo, run: str) -> dict:
    """Reads a run record.

    Raises:
        FlowError: No record has this run ID.
    """
    path = _records(repo) / f"{Path(run).name}.json"
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        raise FlowError(f"no snapshot with run ID {run!r}") from exc


def _in_scope(roles: list[str], path: str, paths: dict) -> bool:
    """Tells whether one changed path lies in the write scope of the run's role."""
    if len(roles) != 1:
        return False
    role = roles[0]
    if role == "product-manager":
        return matches_any(path, list(PRODUCT_MANAGER))
    return allows(SCOPES[f"troy-{role}"], path, paths)[0]


def _path_problems(repo: Repo, record: dict, changed: list[dict], allowed: set[str],
                   paths: dict) -> list[dict]:
    """Finds scope, section, and dependency problems among the changed paths."""
    problems, roles = [], record["roles"]
    for entry in changed:
        path = entry["path"]
        if not _in_scope(roles, path, paths):
            who = " and ".join(roles)
            problems.append({"kind": "scope", "path": path, "message":
                             f"{path} ({entry['class']}) is outside the write scope of {who}."})
        elif entry["class"] == "dependencies" and path not in allowed:
            problems.append({"kind": "dependency", "path": path, "message":
                             f"{path} is a dependency file, and no --allow-dependency names it "
                             "(R16)."})
        elif roles == ["architect"] and matches_any(path, [DESIGNS]):
            before = git.read(repo, record["head"], path)
            full = repo.root / path
            after = full.read_text(encoding="utf-8", errors="replace") if full.is_file() else None
            for what in outside_section_four(before, after):
                problems.append({"kind": "section", "path": path, "message":
                                 f"The Architect changed {path} outside its section 4: {what}."})
    return problems


def _undo(repo: Repo, record: dict, changed: list[dict]) -> list[dict]:
    """Says how to undo each change of the run: restore from HEAD, or delete."""
    undo = []
    for entry in changed:
        path = entry["path"]
        if git.exists(repo, record["head"], path):
            undo.append({"path": path, "action": "restore", "command":
                         f"git restore --source=HEAD --staged --worktree -- {shlex.quote(path)}"})
        else:
            undo.append({"path": path, "action": "delete",
                         "command": f"rm -f -- {shlex.quote(path)}"})
    return undo


def _hooks_log(repo: Repo, record: dict) -> list[dict]:
    """Lists the hooks.log lines of the run's roles since the snapshot (F05 section 10)."""
    path = repo.state_dir() / "hooks.log"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    types = {f"troy-pstack:troy-{r}" for r in record["roles"] if r != "product-manager"}
    found = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or str(entry.get("time", "")) < record["time"]:
            continue
        main = "product-manager" in record["roles"] and not entry.get("agent_id")
        if main or entry.get("agent_type") in types:
            found.append(entry)
    return found


def check_run(args) -> tuple[dict, int]:
    """Compares the state after a role run with its snapshot (design 7).

    Args:
        args: Parsed options: run, allow_dependency, and repo.

    Returns:
        The report and the exit code: 1 when there is any problem.

    Raises:
        FlowError: No record has the run ID, or git fails.
    """
    repo = git.need_repo(args.repo)
    record = _load(repo, args.run)
    paths = git.config_at(repo, record["head"] or "HEAD").paths
    changed = [{"path": p, "status": code, "class": classify(p, paths)}
               for code, p in git.changed_paths(repo)]
    problems = []
    if git.commit_of(repo, "HEAD") != record["head"]:
        problems.append({"kind": "head", "path": None, "message":
                         "HEAD moved during the run. Roles cannot commit, so the hooks failed."})
    if git.branch(repo) != record["branch"]:
        problems.append({"kind": "branch", "path": None, "message":
                         "The branch changed during the run. Roles cannot switch branches."})
    problems += _path_problems(repo, record, changed, set(args.allow_dependency or []), paths)
    undo_kinds = {"scope", "section", "dependency"}
    report = {"command": "check-run", "ok": not problems, "notes": [], "run": record["run"],
              "roles": record["roles"], "changed": changed, "problems": problems,
              "escalate": any(p["kind"] in ("head", "branch") for p in problems),
              "stage": [] if problems else [c["path"] for c in changed],
              "undo": _undo(repo, record, changed)
              if any(p["kind"] in undo_kinds for p in problems) else [],
              "hooks_log": _hooks_log(repo, record)}
    return report, 1 if problems else 0
