"""The next action, decided from the state (F07 design sections 4, 8, 10, and 11, F08 3.3,
F09 3.2).

The first rule that holds wins. The skill holds the judgment about what to do
with it; this module only reads the exact rules.
"""

import re

from troycheck.frontmatter import version_key

from . import releases, rulestate
from . import repo as git
from .nextentry import make
from .repo import MAIN
from .requirements import approved, doc_version
from .rework import change_index
from .stages import AUTHOR_TASK, KIND_TASK, branch, feature_stage, parse_subject, plain, title
from .state import ARCHITECTURE, REQUIREMENTS, SETUP_TITLE, State, is_approved, next_feature, \
    pr_entry

ASK_TITLE = "[rules] Set the features Troy approves"
RECORD_REQUIREMENTS = f"[docs] Record Troy's approval of {REQUIREMENTS}"
_next = make
PLAN_TITLE = re.compile(r"\[docs\] (?:Add|Update) the (v\d+\.\d+) test plan")


def _record(doc: str, slug: str, **values) -> dict:
    """The next entry for a [docs] PR that records Troy's approval of a document."""
    return _next("record-approval", doc=doc, title=f"[docs] Record Troy's approval of {doc}",
                 branch=f"troy-mode/approve-{slug}", merged_by="f07", **values)


def _is_release(pr: dict) -> bool:
    """Tells whether an open PR is a release PR, "[docs] Release vX.Y.Z" (F08 design 5.4)."""
    return releases.release_tag(plain(str(pr.get("title") or ""))) is not None


def _pr_order(pr: dict) -> tuple[int, int]:
    """Sorts open PRs: side PRs, then feature stage PRs, then release PRs, each by number.

    A side PR comes before the stage PR it interrupts (F07 design 5.1, 8.7), and
    a release PR waits for every other PR, such as a bug's (F08 design 3.3).
    """
    if _is_release(pr):
        group = 2
    else:
        group = 1 if feature_stage(str(pr.get("title") or "")) is not None else 0
    return (group, int(pr.get("number", 0)))


def _pr_next(state: State, pr: dict) -> dict:
    """The next entry for continuing an open PR."""
    entry = pr_entry(state, pr)
    found = feature_stage(entry["title"] or "")
    task = AUTHOR_TASK.get(found[1]) if found else KIND_TASK.get(entry["kind"] or "")
    item = entry["item"]
    plan = PLAN_TITLE.fullmatch(plain(entry["title"] or ""))
    if plan:
        task, item = "TM7", plan.group(1)
    elif entry["kind"] == "version-tests":
        summary = parse_subject(entry["title"] or "").summary
        task = "TE3" if summary.startswith("Fix ") else "TE5"
    rule = rulestate.pr_rule(entry["title"] or "")
    if rule:
        item, task = rule
    return _next("continue-pr", pr=entry["number"], title=entry["title"], branch=entry["branch"],
                 item=item, stage=entry["stage"], task=task,
                 merged_by=entry["merged_by"], rounds=entry["rounds"], attempts=entry["attempts"])


def _stale_rework(state: State, pr: dict) -> dict | None:
    """The rework entry for a stage PR opened before a requirement change, or None.

    The PR's feature is in rework, and its branch on origin is missing or does
    not hold the newest change commit, so AR4 must name the stage to redo
    before the PR goes on (design 11.2).
    """
    found = feature_stage(str(pr.get("title") or ""))
    if not found or not state.in_rework(found[0]):
        return None
    head = str(pr.get("headRefName") or "")
    ref = f"refs/remotes/origin/{head}"
    change = state.change_commit()
    if head and change and git.commit_of(state.repo, ref) and git.is_ancestor(state.repo, change,
                                                                             ref):
        return None
    return _next("rework", item=found[0], stage=state.current(found[0]), task="AR4",
                 pr=int(pr.get("number", 0)), title=pr.get("title"), branch=pr.get("headRefName"))


def _setup_next(state: State) -> dict | None:
    """The next entry for the requirements, the architecture, and the pack, or None."""
    if state.docs.get(REQUIREMENTS) is None:
        return _next("requirements", title="[docs] Add the requirements", doc=REQUIREMENTS,
                     branch="troy-mode/requirements", merged_by="troy")
    if not is_approved(state, REQUIREMENTS):
        return _record(REQUIREMENTS, "requirements")
    if state.docs.get(ARCHITECTURE) is None:
        return _next("architecture", title="[docs] Add the architecture", doc=ARCHITECTURE,
                     branch="troy-mode/architecture", merged_by="troy")
    if not is_approved(state, ARCHITECTURE):
        return _record(ARCHITECTURE, "architecture")
    if not state.lang:
        return _next("language", merged_by="f07")
    return None


def _change_record(state: State) -> dict | None:
    """The record entry for a requirement change that Troy merged on GitHub, or None.

    Approving in chat raises the requirements to a new major version inside the
    change commit; a merge on GitHub leaves a minor part (design 11.2).
    """
    index = change_index(state.subjects)
    if index is None:
        return None
    version = doc_version(git.read(state.repo, state.log[index][0], REQUIREMENTS))
    key = version_key(version) if version else None
    if key is None or len(key) < 2 or key[1] == 0:
        return None
    if any(plain(s) == RECORD_REQUIREMENTS for s in state.subjects[:index]):
        return None
    return _record(REQUIREMENTS, "requirements")


def _approval_records(state: State) -> dict | None:
    """The next entry for a PR 1 or PR 2 that Troy merged on GitHub (design 8.6), or None."""
    for stage, name in ((1, "design"), (2, "test-plan")):
        for fid in state.order or []:
            if not state.troy_approves(fid) or stage not in state.merged.get(fid, set()):
                continue
            folder = state.feature_folder(fid)
            doc = f"{folder}/{name}.md" if folder else None
            if doc and not approved(doc_version(git.read(state.repo, MAIN, doc))):
                return _record(doc, f"{fid.lower()}-{name}", item=fid, stage=stage)
    return None


def _bug_next(state: State) -> dict | None:
    """The next entry for PR B of a bug whose PR A merged (design 11.1), or None."""
    for bug in state.bugs:
        if bug["test_merged"] and not bug["fixed"]:
            bid = bug["id"]
            return _next("bug", item=bid, task="DV3", title=f"[{bid} B/B fix] {bug['summary']}",
                         branch=f"troy-mode/{bid.lower()}-fix", merged_by="f07")
    return None


def _rework_next(state: State) -> dict | None:
    """The next entry for the next feature when a requirement change sent it back, or None."""
    fid = next_feature(state)
    if fid is None or not state.merged.get(fid) or not state.in_rework(fid):
        return None
    return _next("rework", item=fid, stage=state.current(fid), task="AR4")


def _ask_due(state: State) -> bool:
    """Tells whether F07 must ask Troy about approving later features (design 8.6, D62)."""
    count, order = state.approves_first, state.order or []
    if count <= 0 or len(order) <= count:
        return False
    last = order[count - 1]
    accept = next((i for i, s in enumerate(state.subjects)
                   if feature_stage(s) == (last, 6)), None)
    if accept is None:
        return False
    return not any(s.startswith(ASK_TITLE) for s in state.subjects[:accept])


def _stage_next(state: State, attempts: int) -> dict:
    """The next entry for the next feature's next stage, or all-accepted."""
    fid = next_feature(state)
    feature = state.feature(fid)
    if fid is None or feature is None:
        return _next("all-accepted")
    stage = state.current(fid)
    stage_title = title(fid, stage, feature.name)
    return _next("stage", item=fid, stage=stage, task=AUTHOR_TASK[stage], title=stage_title,
                 branch=branch(fid, stage), merged_by=state.merged_by(stage_title),
                 attempts=attempts)


def _open_pr_next(state: State, current: list[dict], notes: list[str],
                  attempts: int) -> dict:
    """The next entry when troy-mode PRs are open: the first one in order goes on."""
    if len(current) > 1:
        notes.append(f"{len(current)} troy-mode PRs are open; PR #{current[0]['number']} "
                     "comes first. troy-mode works on one PR at a time.")
    stale = _stale_rework(state, current[0])
    if stale:
        return stale
    entry = _pr_next(state, current[0])
    entry["attempts"] = max(entry["attempts"], attempts)
    return entry


def decide(state: State, attempts: int = 0) -> tuple[dict, list[str]]:
    """Decides the next action.

    Args:
        state: The project's state.
        attempts: Attempts counted in the carried notes, for the next stage.

    Returns:
        The next entry and notes about the choice.
    """
    notes: list[str] = []
    current = sorted((pr for pr in state.prs if parse_subject(str(pr.get("title") or ""))),
                     key=_pr_order)
    setup_open = any(pr.get("title") == SETUP_TITLE for pr in current)
    if state.repo is None or not state.origin or (not state.installed and not setup_open):
        return _next("setup", title=SETUP_TITLE, branch="troy-mode/init", merged_by="f07"), notes
    release_first = bool(current) and _is_release(current[0])
    if current and not release_first:
        return _open_pr_next(state, current, notes, attempts), notes
    found = _setup_next(state)
    if found:
        return found, notes
    if state.order_problems:
        return _next("order-problem"), notes
    for rule in (_change_record, _approval_records, releases.record_rule, releases.tag_rule,
                 _bug_next, _rework_next):
        found = rule(state)
        if found:
            return found, notes
    found = (releases.retro_rule(state, notes)
             or releases.release_rule(state, release_first)
             or rulestate.cleanup_rule(state.rules))
    if found:
        return found, notes
    if _ask_due(state):
        return _next("ask-approvals", title=ASK_TITLE, branch="troy-mode/approvals",
                     merged_by="f07"), notes
    found = releases.plan_rule(state, next_feature(state))
    if found:
        return found, notes
    return _stage_next(state, attempts), notes
