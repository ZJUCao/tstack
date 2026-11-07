"""The next action, decided from the state (F07 design sections 4, 8, and 10).

The first rule that holds wins. The skill holds the judgment about what to do
with it; this module only reads the exact rules.
"""

from . import repo as git
from .repo import MAIN
from .requirements import approved, doc_version
from .stages import AUTHOR_TASK, branch, current_stage, feature_stage, parse_subject, title
from .state import ARCHITECTURE, REQUIREMENTS, SETUP_TITLE, State, is_approved, next_feature, \
    pr_entry

ASK_TITLE = "[rules] Set the features Troy approves"
_KEYS = ("action", "item", "stage", "task", "title", "branch", "pr", "merged_by", "doc")


def _next(action: str, **values) -> dict:
    """Builds a next entry with every key, the ones not given null or 0."""
    entry = {key: values.get(key) for key in _KEYS}
    entry["action"] = action
    entry["rounds"] = values.get("rounds", 0)
    entry["attempts"] = values.get("attempts", 0)
    return entry


def _record(doc: str, slug: str, **values) -> dict:
    """The next entry for a [docs] PR that records Troy's approval of a document."""
    return _next("record-approval", doc=doc, title=f"[docs] Record Troy's approval of {doc}",
                 branch=f"troy-mode/approve-{slug}", merged_by="f07", **values)


def _pr_next(state: State, pr: dict) -> dict:
    """The next entry for continuing an open PR."""
    entry = pr_entry(state, pr)
    found = feature_stage(entry["title"] or "")
    return _next("continue-pr", pr=entry["number"], title=entry["title"], branch=entry["branch"],
                 item=entry["item"], stage=entry["stage"],
                 task=AUTHOR_TASK.get(found[1]) if found else None,
                 merged_by=entry["merged_by"], rounds=entry["rounds"], attempts=entry["attempts"])


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
    stage = current_stage(state.merged.get(fid, set()))
    stage_title = title(fid, stage, feature.name)
    return _next("stage", item=fid, stage=stage, task=AUTHOR_TASK[stage], title=stage_title,
                 branch=branch(fid, stage), merged_by=state.merged_by(stage_title),
                 attempts=attempts)


def decide(state: State, attempts: int = 0) -> tuple[dict, list[str]]:
    """Decides the next action.

    Args:
        state: The project's state.
        attempts: Attempts counted in the carried notes, for the next stage.

    Returns:
        The next entry and notes about the choice.
    """
    notes = []
    current = [pr for pr in state.prs if parse_subject(str(pr.get("title") or ""))]
    setup_open = any(pr.get("title") == SETUP_TITLE for pr in current)
    if state.repo is None or not state.origin or (not state.installed and not setup_open):
        return _next("setup", title=SETUP_TITLE, branch="troy-mode/init", merged_by="f07"), notes
    if current:
        if len(current) > 1:
            notes.append(f"{len(current)} troy-mode PRs are open; PR #{current[0]['number']} "
                         "comes first. troy-mode works on one PR at a time.")
        entry = _pr_next(state, current[0])
        entry["attempts"] = max(entry["attempts"], attempts)
        return entry, notes
    found = _setup_next(state)
    if found:
        return found, notes
    if state.order_problems:
        return _next("order-problem"), notes
    found = _approval_records(state)
    if found:
        return found, notes
    if _ask_due(state):
        return _next("ask-approvals", title=ASK_TITLE, branch="troy-mode/approvals",
                     merged_by="f07"), notes
    return _stage_next(state, attempts), notes
