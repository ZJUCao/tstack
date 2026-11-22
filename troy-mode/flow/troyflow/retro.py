"""retro: the evidence for a version's retrospective, grouped (F08 design 7, D76).

It reads the PRs merged since the previous version's tag, F07's comments on
them, the bugs fixed in that time, and the hooks.log lines, and groups the
findings by the rule ID or checklist item each one names. A group seen in two
or more PRs is a repeated problem. It changes nothing.

F07 D261 to D263 add each commit that failed CI in the author's files with no
attempt comment counting it, in its role's attempt group (ci.py).
"""

import datetime
import json
import re

from . import ci, github
from . import repo as git
from .errors import FlowError
from .nextstep import title_task
from .repo import MAIN, Repo
from .stages import parse_subject, plain
from .versions import is_patch, parse_tag, release_tag

RULE_ID = re.compile(r"\b([RP]\d{2})\b")
FINDING = re.compile(r"^\s*\d+[.)]\s+(.+)$")
_MARKER = re.compile(r"^(?:\*\*|\*|\[(?:non-)?blocking\]|\((?:non-)?blocking\)|"
                     r"(?:non-)?blocking:)\s*", re.IGNORECASE)
_ITEM = re.compile(r"[A-Za-z][A-Za-z0-9 -]*")
_TIME = "%Y-%m-%dT%H:%M:%SZ"


def check_tag(tag: str) -> str:
    """Checks --tag: vMAJOR.MINOR.PATCH.

    Raises:
        FlowError: It is not of that form.
    """
    if parse_tag(tag) is None:
        raise FlowError(f"--tag {tag!r} is not a tag of the form vMAJOR.MINOR.PATCH")
    return tag


def finding_key(text: str) -> tuple[str, str] | None:
    """The group of one review finding: its first rule ID, or its checklist item.

    Returns:
        (key, kind), kind "rule" or "item", or None when the finding names neither.
    """
    rule = RULE_ID.search(text)
    if rule:
        return rule.group(1), "rule"
    rest = text.strip()
    while True:
        stripped = _MARKER.sub("", rest, count=1)
        if stripped == rest:
            break
        rest = stripped
    if ":" not in rest:
        return None
    label = rest.split(":", 1)[0].replace("*", "").replace("`", "").strip()
    words = label.split()
    if not 1 <= len(words) <= 4 or not _ITEM.fullmatch(label):
        return None
    return " ".join(words).lower(), "item"


def comment_entries(body: str) -> tuple[list[dict], list[str]]:
    """Reads one comment's evidence.

    Returns:
        Entries with key, kind, and text, and the findings that name no group.
        Troy's comments, and F07's other comments, give nothing.
    """
    lines = (body or "").strip().split("\n")
    first = lines[0].strip() if lines else ""
    rest = [line.rstrip("\r") for line in lines[1:]]
    review = github.REVIEW.match(first)
    if review and review.group(3) == "changes-requested":
        entries, loose = [], []
        for line in rest:
            match = FINDING.match(line)
            if not match:
                continue
            text = match.group(1).strip()
            key = finding_key(text)
            if key:
                entries.append({"key": key[0], "kind": key[1], "text": text})
            else:
                loose.append(text)
        return entries, loose
    attempt = github.ATTEMPT.match(first)
    if attempt:
        text = "\n".join(rest).strip()
        rules = list(dict.fromkeys(RULE_ID.findall(text)))
        if rules:
            return [{"key": r, "kind": "rule", "text": text} for r in rules], []
        return [{"key": f"{attempt.group(1)} attempt failed", "kind": "attempt",
                 "text": text}], []
    if github.ESCALATION.match(first):
        return [{"key": first, "kind": "escalation", "text": "\n".join(rest).strip()}], []
    return [], []


def _range(state_log: list[tuple[str, str]], tag: str) -> tuple[list[tuple[str, str]],
                                                                str | None, str | None]:
    """The commits of the tag's range, the previous version's tag, and its commit."""
    commits = [(i, sha, release_tag(plain(s))) for i, (sha, s) in enumerate(state_log)]
    commits = [c for c in commits if c[2] and parse_tag(c[2])]
    own = next((c for c in commits if c[2] == tag), None)
    if own is None:
        raise LookupError(tag)
    previous = next((c for c in commits if c[0] > own[0] and not is_patch(c[2])), None)
    end = previous[0] if previous else len(state_log)
    return (state_log[own[0]:end], previous[2] if previous else None,
            previous[1] if previous else None)


def _commit_time(repo: Repo, sha: str) -> datetime.datetime:
    """The committer time of a commit, in UTC."""
    text = git.git(repo, "show", "-s", "--format=%cI", sha).strip()
    return datetime.datetime.fromisoformat(text).astimezone(datetime.timezone.utc)


def _hooks(repo: Repo, since: datetime.datetime | None) -> list[dict]:
    """The hooks.log lines at or after a time (all without one), as parsed JSON."""
    try:
        lines = (repo.state_dir() / "hooks.log").read_text(
            encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    found = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or not entry.get("rule"):
            continue
        if since is not None:
            try:
                when = datetime.datetime.strptime(str(entry.get("time", "")), _TIME).replace(
                    tzinfo=datetime.timezone.utc)
            except ValueError:
                continue
            if when < since:
                continue
        found.append(entry)
    return found


def _group(groups: dict, entry: dict, pr: dict | None, heading: str) -> None:
    """Adds one entry to its group."""
    group = groups.setdefault(entry["key"], {"key": entry["key"], "kind": entry["kind"],
                                             "prs": [], "count": 0, "evidence": []})
    group["count"] += 1
    if pr is not None and pr["number"] not in group["prs"]:
        group["prs"].append(pr["number"])
    group["evidence"].append({"pr": pr["number"] if pr else None,
                              "url": pr.get("url") if pr else None,
                              "heading": heading, "text": entry["text"]})


def _sorted_groups(groups: dict) -> list[dict]:
    """Sorts groups: repeated first, then more PRs, then a higher count, then the key."""
    for group in groups.values():
        group["prs"].sort()
        many = group["count"] if group["kind"] == "hooks" else len(group["prs"])
        group["repeated"] = many >= 2
    return sorted(groups.values(), key=lambda g: (not g["repeated"], -len(g["prs"]),
                                                  -g["count"], g["key"]))


def run_retro(args) -> tuple[dict, int]:
    """Gathers and groups the evidence for a version's retrospective.

    Args:
        args: Parsed options: tag and repo.

    Returns:
        The report and the exit code: 1 when the tag has no release commit on
        origin/main.
    """
    tag = check_tag(args.tag)
    repo = git.need_repo(args.repo)
    report = {"command": "retro", "ok": False, "notes": [], "problems": [], "tag": tag}
    log = git.log(repo, MAIN) if git.commit_of(repo, MAIN) else []
    try:
        commits, previous, previous_sha = _range(log, tag)
    except LookupError:
        report["problems"] = [f"{tag} has no [docs] Release {tag} commit on origin/main."]
        return report, 1
    shas = {sha for sha, _ in commits}
    subjects = {plain(s) for _, s in commits}
    prs, merged = [], {}
    for pr in github.merged_prs(repo):
        merge = pr.get("mergeCommit") if isinstance(pr.get("mergeCommit"), dict) else None
        oid = str(merge.get("oid")) if merge else None
        if (oid and oid in shas) or (not oid and plain(str(pr.get("title") or "")) in subjects):
            prs.append({"number": int(pr.get("number", 0)), "title": pr.get("title"),
                        "url": pr.get("url")})
            merged[int(pr.get("number", 0))] = pr
    prs.sort(key=lambda p: p["number"])
    groups: dict = {}
    loose = []
    runs = _ci_runs(repo, [merged[p["number"]] for p in prs], report["notes"]) if prs else None
    ci_attempts, ci_other = [], []
    for pr in prs:
        timed = github.timed_comments(repo, pr["number"])
        for _, body in timed:
            heading = github.heading(body)
            entries, unkeyed = comment_entries(body)
            for entry in entries:
                _group(groups, entry, pr, heading)
            loose += [{"pr": pr["number"], "heading": heading, "text": t} for t in unkeyed]
        if runs is not None:
            _ci_evidence(repo, pr, merged[pr["number"]], runs, timed, groups,
                         (ci_attempts, ci_other), report["notes"])
    since = _commit_time(repo, previous_sha) if previous_sha else None
    for line in _hooks(repo, since):
        _group(groups, {"key": f"hooks.log: {line['rule']}", "kind": "hooks",
                        "text": json.dumps(line, ensure_ascii=False)}, None, "hooks.log")
    ordered = _sorted_groups(groups)
    report.update(ok=True, previous=previous, prs=prs, groups=ordered,
                  repeated=[g["key"] for g in ordered if g["repeated"]], ungrouped=loose,
                  bugs=_bugs(repo, [s for _, s in commits]), ci_attempts=ci_attempts,
                  ci_other=ci_other)
    return report, 0


def _ci_runs(repo: Repo, prs: list[dict], notes: list[str]) -> list[dict] | None:
    """Lists the CI runs of the range's PRs in one call (F07 design 8.5), or None.

    The call starts from the day the oldest PR opened. When gh cannot list the
    runs, retro counts attempts from the comments only and says so.
    """
    opened = [moment for moment in (ci.when(p.get("createdAt")) for p in prs
                                    if p.get("createdAt")) if moment is not None]
    try:
        runs = ci.version_runs(repo, min(opened) if opened else None)
    except FlowError as exc:
        notes.append(f"The CI runs could not be read ({exc}); attempts count the comments "
                     "only.")
        return None
    if len(runs) >= ci.VERSION_LIMIT:
        notes.append(f"gh listed {ci.VERSION_LIMIT:,} CI runs, its limit; attempts from older "
                     "runs may be missing.")
    return runs


def _ci_evidence(repo: Repo, pr: dict, merged: dict, runs: list[dict],
                 timed: list[tuple[str, str]], groups: dict, found: tuple[list, list],
                 notes: list[str]) -> None:
    """Adds one PR's CI failures that no comment counts (F07 D261 to D263).

    An author failure joins its role's attempt group and ci_attempts; a
    failure outside the author's files goes to ci_other only.
    """
    try:
        counted = ci.pr_count(repo, merged, runs, timed)
    except FlowError as exc:
        notes.append(f"The CI runs of PR #{pr['number']} could not be read ({exc}); its "
                     "attempts count the comments only.")
        return
    role = ci.role_of(title_task(str(pr.get("title") or ""))[0])
    for failure in counted.failures:
        item = {"pr": pr["number"], "url": pr.get("url"), "commit": failure.commit,
                "runs": failure.runs, "steps": failure.steps}
        if not failure.author:
            found[1].append(item)
        elif not failure.counted:
            found[0].append({**item, "role": role})
            _group(groups, {"key": f"{role} attempt failed", "kind": "attempt",
                            "text": "; ".join(failure.steps)}, pr, f"CI: {failure.commit[:7]}")


def _bugs(repo: Repo, subjects: list[str]) -> list[dict]:
    """The bugs fixed in the range, oldest first, each with its issue."""
    found = []
    for subject in reversed(subjects):
        parsed = parse_subject(subject)
        if not parsed or parsed.kind != "fix" or not (parsed.id or "").startswith("B"):
            continue
        if any(b["id"] == parsed.id for b in found):
            continue
        number = int(parsed.id[1:])
        issue = github.issue(repo, number)
        found.append({"id": parsed.id, "issue": number, "summary": parsed.summary,
                      "title": issue.get("title"), "url": issue.get("url")})
    return found
