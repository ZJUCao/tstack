"""F18's state beyond one PR: Troy's overturns, and the rulings of merged PRs (F18 design 5.3).

An overturn opens with troy-mode's `Overturn: <link to the ruling>` comment on
the feature's progress issue and ends with `Overturn carried out: <link>` once
the PRs that carry it out have merged. While it is open, the feature, and its
team, stop before their next stage.

The progress issue shows each ruling of the feature's PRs, merged ones too.
A merged PR's comments no longer change before a ruling, so its rulings are
read once per checkout and kept in the common git folder.
"""

import json
from pathlib import Path

from . import github, issuedata, teams
from .errors import FlowError
from .issuedata import PROGRESS

CACHE = "troy-mode/rulings.json"


def overturns(state) -> list[dict]:
    """Every overturn on a progress issue, oldest first: item, issue, ruling link, and done.

    Returns:
        [] when the issues were not read.
    """
    return from_issues(state.issues)


def from_issues(issues) -> list[dict]:
    """The overturns of the progress issues read, as `overturns` gives them."""
    if not isinstance(issues, issuedata.Issues) or not issues.readable:
        return []
    found = []
    for item, group in issues.marked(PROGRESS).items():
        for issue in group:
            for comment in issue.comment_items:
                body = str(comment.get("body") or "").replace("\r\n", "\n")
                first = github.heading(body)
                done = github.OVERTURN_DONE.match(first)
                if done:
                    for entry in found:
                        if (entry["issue"] == issue.number and not entry["done"]
                                and entry["ruling"] == done.group(1).strip()):
                            entry["done"] = True
                    continue
                opened = github.OVERTURN.match(first)
                if opened:
                    found.append({"item": item, "issue": issue.number,
                                  "ruling": opened.group(1).strip(), "done": False,
                                  "_time": str(comment.get("createdAt") or "")})
    found.sort(key=lambda entry: (entry["_time"], entry["issue"]))
    return [{key: value for key, value in entry.items() if key != "_time"} for entry in found]


def open_overturn(found: list[dict], fid: str | None) -> dict | None:
    """The feature's oldest overturn not yet carried out, or None."""
    return next((entry for entry in found if entry["item"] == fid and not entry["done"]), None)


def held(state) -> set[str]:
    """The features an open overturn holds (F20 `held` reason `overturn`)."""
    return {entry["item"] for entry in overturns(state) if not entry["done"]}


def _cache_path(repo) -> Path:
    """The cache file in the common git folder."""
    return teams.common_dir(repo) / CACHE


def _load(path: Path) -> dict:
    """The kept rulings by PR number, {} when the file is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def merged_rulings(repo, numbers: list[int]) -> dict[int, list[dict]]:
    """The rulings of merged PRs, each with the URL of its comment (design 5.3).

    Args:
        repo: The repository.
        numbers: The merged PRs to look at.

    Returns:
        Each PR's rulings, oldest first, as {"ruling": ..., "url": ...}. A PR not
        kept yet is read through gh once and kept; a failed read is not kept.
    """
    if not numbers:
        return {}
    try:
        path = _cache_path(repo)
    except (FlowError, OSError):
        path = None
    kept = _load(path) if path else {}
    found, changed = {}, False
    for number in numbers:
        key = str(number)
        if key not in kept:
            try:
                items = github.comment_items(repo, number)
            except FlowError:
                continue
            notes = github.read_comments([i["body"] for i in items], [i["url"] for i in items])
            kept[key] = [{"ruling": r, "url": u} for r, u in zip(notes.rulings, notes.ruling_urls)]
            changed = True
        found[number] = kept[key]
    if changed and path is not None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(kept, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
        except OSError:
            pass
    return found
