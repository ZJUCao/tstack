"""merge-check: whether a team's PR may merge now (F20 design 3.7, R24, D272 to D274).

It reads git only. The PR's title is the worktree's HEAD subject (R01). The
result is rebase (origin/main is not in the branch), outside-plan (a source
path lies outside the plan's modules for the feature), held (a later
version's code PR before the earlier version's release), or ready. After a
rebase it says whether the PR's added and deleted lines changed, and for a
rebase that stopped on a conflict, which role's write scope holds the files.
"""

from troycheck.classify import classify
from troycheck.globs import matches_any
from troycheck.modules import parse_table
from troyhook.scopes import SCOPES
from troyhook.writes import allows

from . import plan as batchplan
from . import repo as git
from .errors import FlowError
from .releases import released_tags
from .repo import MAIN, Repo
from .requirements import parse_features
from .runs import PRODUCT_MANAGER
from .stages import feature_stage, parse_subject
from .state import State
from .versions import versions_of

ARCHITECTURE = "docs/architecture.md"
REQUIREMENTS = "docs/requirements.md"
OWNERS = {1: "interface-designer", 2: "test-manager", 3: "developer", 4: "test-engineer",
          5: "developer", 6: "product-manager"}
REVIEWED = (3, 4, 5)


def _outside(repo: Repo, fid: str, notes: list[str]) -> list[str]:
    """The source paths of HEAD's commit outside the plan's modules for the feature."""
    kept = batchplan.load(repo)
    entry = (kept or {}).get("features", {}).get(fid)
    if entry is None:
        notes.append(f"No batch plan names {fid}, so its paths were not checked against one.")
        return []
    modules = parse_table(git.read(repo, MAIN, ARCHITECTURE) or "") or []
    patterns = [p for m in modules if m.name in entry.get("modules", []) for p in m.owns]
    paths = git.config_at(repo, "HEAD").paths
    changed = git.git(repo, "diff", "--name-only", "HEAD^", "HEAD").split()
    return [path for path in changed
            if classify(path, paths) == "source" and not matches_any(path, patterns)]


def _held_by(repo: Repo, fid: str, stage: int | None) -> str | None:
    """The earlier version without a release that holds a later version's code PR (Q24)."""
    if stage is None or stage < 3:
        return None
    features = parse_features(git.read(repo, MAIN, REQUIREMENTS)) or []
    versions = list(versions_of(features))
    own = next((f.version for f in features if f.id == fid), None)
    if own not in versions:
        return None
    state = State(repo=repo, log=git.log(repo, MAIN))
    return next((v for v in versions[:versions.index(own)] if not released_tags(state, v)), None)


def _changes(repo: Repo, commit: str) -> dict[str, list[str]]:
    """The lines a commit adds and deletes, per file, without context or line numbers."""
    text = git.git(repo, "diff", "--no-color", "--unified=0", f"{commit}^", commit)
    found: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            current = line.split(" b/", 1)[-1]
            found[current] = []
        elif line.startswith(("+++", "---", "@@")):
            continue
        elif current is not None and line[:1] in ("+", "-"):
            found[current].append(line)
    return found


def _owner(repo: Repo, stage: int | None, paths: list[str]) -> str | None:
    """The stage's author when its write scope holds every conflicting path (Q22, D273)."""
    role = OWNERS.get(stage or 0)
    if role is None:
        return None
    classes = git.config_at(repo, "HEAD").paths
    for path in paths:
        if role == "product-manager":
            if not matches_any(path, list(PRODUCT_MANAGER)):
                return None
        elif not allows(SCOPES[f"troy-{role}"], path, classes)[0]:
            return None
    return role


def run_merge_check(args) -> tuple[dict, int]:
    """Says whether the worktree's PR may merge now, and what a rebase changed."""
    repo = git.need_repo(args.repo)
    subject = git.git(repo, "log", "-1", "--format=%s", "HEAD").strip()
    parsed = parse_subject(subject)
    found = feature_stage(subject)
    item = parsed.id if parsed else None
    stage = found[1] if found else None
    notes: list[str] = []
    report = {"command": "merge-check", "ok": False, "result": None, "item": item, "stage": stage,
              "title": subject, "outside": [], "held_by": None, "diff_changed": None,
              "review_again": None, "owner": None, "escalate": False, "problems": [],
              "notes": notes}
    main = git.commit_of(repo, MAIN)
    if main is None:
        raise FlowError(f"{MAIN} does not exist: fetch it first")
    if not git.is_ancestor(repo, main, "HEAD"):
        report["result"] = "rebase"
    elif found and (outside := _outside(repo, item, notes)):
        report.update(result="outside-plan", outside=outside)
    elif found and (held := _held_by(repo, item, stage)):
        report.update(result="held", held_by=held)
    else:
        report["result"] = "ready"
    if args.rebased_from:
        changed = _changes(repo, args.rebased_from) != _changes(repo, "HEAD")
        report.update(diff_changed=changed, review_again=changed and stage in REVIEWED)
    if args.conflicts:
        owner = _owner(repo, stage, args.conflicts)
        report.update(owner=owner, escalate=owner is None)
    report["ok"] = report["result"] == "ready"
    return report, 0 if report["ok"] else 1
