"""Spot checks: the sample, risky marks, turning them off, and the evidence (F18 design 7).

With `[flow] spot_checks` on, F07 merges PR 1 and PR 2 of the features after
the first `troy_approves_first` too. Troy reviews one feature in
`spot_check_every` after the merge (the sample), and a PR marked risky waits
for Troy before its merge (D176, D177). An overturn of a sampled PR, or of a
ruling on a PR 1 or PR 2, turns them off at once (D179). The evidence E1 to E3
says whether troy-mode recommends them (D178).

This module is not imported by brief, so it is outside F16's instruction set.
"""

import json
import os
import re
import sys
import tomllib
from datetime import datetime
from pathlib import Path

from troycheck.config import CONFIG_PATH, ConfigError, parse_config

from . import github, issuedata, notecmd, teams
from . import repo as git
from .errors import FlowError
from .repo import MAIN
from .sections import blocks
from .stages import feature_stage, plain
from .versions import parse_tag, release_tag

SPOT_HEADING = "Spot check for Troy: review after the merge"
TM_RULING_HEADING = "Test Manager ruling, real run"
ASK_TITLE = "[rules] Set the features Troy approves"
OFF_BRANCH = "troy-mode/spot-checks-off"
CACHE = "troy-mode/spot.json"
# The exam cases of the roles behind PR 1 and PR 2 (F18 design 7.3, E3).
EVIDENCE_CASES = ("if-example-format", "if-error-rules", "ar-design-review", "ar-error-review",
                  "tm-plan-expected")
EXAM_ROOT_VARIABLE = "TROY_EXAM_ROOT"
EXAM_ROOT_DEFAULT = r"D:\Troy\troy-mode-work"
E1_COUNT = 6
E3_RUNS, E3_PASSES = 5, 4
_STAGES = (1, 2)
_PULL = re.compile(r"/pull/([1-9][0-9]*)(?![0-9])")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_NONE = re.compile(r"none(?:\.|$)", re.I)
# The plugin folders that hold F16's instruction set (troyexam.instructions.FIXED,
# BRIEF, SKILL, and the skills the agent files name).
_INSTRUCTION_FOLDERS = ("agents", "skills", "troy-mode/roles", "troy-mode/templates",
                        "troy-mode/exam/cases", "troy-mode/exam/troyexam",
                        "troy-mode/flow/troyflow")


def sample(order: list[str], approves_first: int, every: int) -> list[str]:
    """The sampled features: one in `every` after the first `approves_first`, by order (D176).

    Args:
        order: The features in the requirements' topological order.
        approves_first: [flow] troy_approves_first.
        every: [flow] spot_check_every, 2 or more.

    Returns:
        The sampled IDs in order: with 3 approved and every 3, the 6th, 9th, ...
    """
    later = list(order)[max(approves_first, 0):]
    return [fid for count, fid in enumerate(later, 1) if every > 0 and count % every == 0]


# --------------------------------------------------------------------------- risky marks


def lists_change(design: str | None) -> bool:
    """Tells whether a design's section 3 lists a change to an existing interface (D177).

    The text of the section, without its heading and HTML comments, is not
    empty and is not "None", alone or as a first sentence that an explanation
    follows ("None. F10 is a new feature ..."), as the trial's designs write it.
    """
    for heading, block in blocks(design or ""):
        if heading.startswith("## 3."):
            body = _HTML_COMMENT.sub("", block.split("\n", 1)[1] if "\n" in block else "")
            body = body.strip()
            return bool(body) and not _NONE.match(body)
    return False


def _design(repo, ref: str, fid: str) -> str | None:
    """The feature's design.md at a ref, or None when it cannot be read."""
    if git.commit_of(repo, ref) is None:
        return None
    names = [name for name in git.folders(repo, ref, "docs/features")
             if name.startswith(fid + "-")]
    return git.read(repo, ref, f"docs/features/{names[0]}/design.md") if names else None


def _cache_path(repo) -> Path | None:
    """The cache of merged PRs' facts in the common git folder, or None."""
    try:
        return teams.common_dir(repo) / CACHE
    except (FlowError, OSError):
        return None


def _load_cache(path: Path | None) -> dict:
    """The kept facts by PR number, {} when the file is missing or unreadable."""
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache(path: Path | None, kept: dict) -> None:
    """Writes the cache; a failure only costs a read next time."""
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(kept, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except OSError:
        pass


def _facts(comments: github.Comments) -> dict:
    """What a merged PR's comments say for spot checks: marks and E1's facts."""
    return {"rulings": len(comments.rulings),
            "ruling_url": comments.ruling_urls[0] if comments.ruling_urls else None,
            "attempts": comments.attempts, "risky": comments.risky,
            "risky_url": comments.risky_url, "waited": comments.waited,
            "changed": comments.changed}


class Merged:
    """Reads merged PRs' facts once per checkout, keeping them in the common git folder.

    A merged PR's comments before its merge no longer change, and its marks
    and E1's facts come only from those.
    """

    def __init__(self, repo, notes: list[str]):
        """Opens the cache; notes gets a line for each PR that cannot be read."""
        self.repo, self.notes = repo, notes
        self.path = _cache_path(repo)
        self.kept = _load_cache(self.path)
        self.changed = False

    def facts(self, number: int) -> dict | None:
        """A merged PR's facts, or None when its comments cannot be read."""
        key = str(number)
        if key not in self.kept:
            try:
                items = github.comment_items(self.repo, number)
            except FlowError as exc:
                self.notes.append(f"The comments of PR #{number} could not be read ({exc}); its "
                                  "risky marks are not known.")
                return None
            self.kept[key] = _facts(github.read_comments([i["body"] for i in items],
                                                         [i["url"] for i in items]))
            self.changed = True
        return self.kept[key]

    def save(self) -> None:
        """Writes the cache when a PR was read."""
        if self.changed:
            _save_cache(self.path, self.kept)


def _open_pr(state, fid: str, stage: int) -> dict | None:
    """The feature's open PR of a stage, with its comments read, or None."""
    return next((pr for pr in state.prs
                 if feature_stage(str(pr.get("title") or "")) == (fid, stage)), None)


def _merged_number(state, fid: str, stage: int) -> int | None:
    """The highest merged PR of a feature's stage among every PR read, or None."""
    numbers = [int(pr.get("number", 0)) for pr in state.all_prs or []
               if str(pr.get("state") or "").upper() == "MERGED"
               and feature_stage(plain(str(pr.get("title") or ""))) == (fid, stage)]
    return max(numbers) if numbers else None


def _mark(by: str, reason: str, pr: int | None = None, url: str | None = None) -> dict:
    """One risky mark (F18 design 7.2)."""
    return {"by": by, "reason": reason, "pr": pr, "url": url}


def _not_no(value: str | None) -> bool:
    """Tells whether a Risky line's value marks the PR: anything but "no"."""
    return value is not None and value.strip().rstrip(".").strip().lower() != "no"


def _pr_marks(number: int, rulings: bool, ruling_url, attempts: int) -> list[dict]:
    """The engine's ruling and premise marks of one PR."""
    marks = []
    if rulings:
        marks.append(_mark("engine", "ruling", number, ruling_url))
    if attempts >= 3:
        marks.append(_mark("engine", "premise", number))
    return marks


def _open_marks(pr: dict) -> tuple[list[dict], dict | None]:
    """An open PR's ruling and premise marks, and its Architect mark or None."""
    notes: github.Comments = pr["notes"]
    number = int(pr.get("number", 0))
    counted = pr.get("ci")
    attempts = counted.attempts if counted is not None else notes.attempts
    marks = _pr_marks(number, bool(notes.rulings) or notes.ruling is not None,
                      notes.ruling_urls[0] if notes.ruling_urls else None, attempts)
    architect = (_mark("architect", notes.risky.strip(), number, notes.risky_url)
                 if _not_no(notes.risky) else None)
    return marks, architect


def _first_marks(state, fid: str, merged: Merged) -> list[dict]:
    """Stage 1's marks from PR 1 itself: interface, ruling, premise, then the Architect's."""
    pr = _open_pr(state, fid, 1)
    if pr is not None:
        number = int(pr.get("number", 0))
        ref = f"refs/remotes/origin/{pr.get('headRefName') or ''}"
        engine, architect = _open_marks(pr)
        interface = lists_change(_design(state.repo, ref, fid)) if pr.get("headRefName") else False
    else:
        number = _merged_number(state, fid, 1)
        if number is None:
            return []
        interface = lists_change(_design(state.repo, MAIN, fid))
        facts = merged.facts(number)
        engine = _pr_marks(number, bool(facts["rulings"]), facts["ruling_url"],
                           facts["attempts"]) if facts else []
        architect = (_mark("architect", facts["risky"].strip(), number, facts["risky_url"])
                     if facts and _not_no(facts["risky"]) else None)
    marks = [_mark("engine", "interface", number)] if interface else []
    return marks + engine + ([architect] if architect else [])


def _second_own(state, fid: str) -> list[dict]:
    """PR 2's own ruling and premise marks, while it is open."""
    pr = _open_pr(state, fid, 2)
    return _open_marks(pr)[0] if pr is not None else []


def troy_marks(found: list, fid: str) -> list[dict]:
    """Troy's marks: notes for the feature whose text starts with "Risky:" (D177).

    Args:
        found: Every note on the progress issues, from notecmd.all_notes.
        fid: The feature.
    """
    marks = []
    for note in found:
        if note.target != fid:
            continue
        first = next((line.strip() for line in note.text.split("\n") if line.strip()), "")
        if first.startswith("Risky:"):
            marks.append(_mark("troy", first[len("Risky:"):].strip(), None, note.url or None))
    return marks


def _order_marks(marks: list[dict]) -> list[dict]:
    """Engine marks first, then the Architect's, then Troy's, each kept in its order."""
    rank = {"engine": 0, "architect": 1, "troy": 2}
    return sorted(marks, key=lambda mark: rank[mark["by"]])


def _risk(state, notes: list[str]) -> dict[tuple[str, int], list[dict]]:
    """The marks of stage 1 and 2 of every feature whose PR 1 or PR 2 is still to merge."""
    merged = Merged(state.repo, notes)
    written = notecmd.all_notes(state.issues)
    found = {}
    for feature in state.features or []:
        fid = feature.id
        current = state.current(fid)
        if current is None or (current > 2 and _open_pr(state, fid, 1) is None
                               and _open_pr(state, fid, 2) is None):
            continue
        first = _first_marks(state, fid, merged)
        troy = troy_marks(written, fid)
        found[(fid, 1)] = _order_marks(first + troy)
        found[(fid, 2)] = _order_marks(first + _second_own(state, fid) + troy)
    merged.save()
    return found


# --------------------------------------------------------------------------- turning off


def _time(text: str | None) -> datetime | None:
    """Reads an ISO 8601 time, such as GitHub's createdAt or git's %cI; None when unreadable."""
    try:
        when = datetime.fromisoformat(str(text or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo is not None else None


def _turned_on_at(state) -> datetime | None:
    """The committer date of origin/main's newest [rules] Set the features Troy approves."""
    commit = next((sha for sha, subject in state.log if plain(subject).startswith(ASK_TITLE)),
                  None)
    if commit is None:
        return None
    try:
        return _time(git.git(state.repo, "show", "-s", "--format=%cI", commit))
    except FlowError:
        return None


def link_pr(link: str) -> int | None:
    """The PR number a link names, or None."""
    found = _PULL.search(link or "")
    return int(found.group(1)) if found else None


def _titles(state) -> dict[int, str]:
    """Every PR read, open and closed, by number: its plain title."""
    titles = {int(pr.get("number", 0)): plain(str(pr.get("title") or ""))
              for pr in state.all_prs or []}
    titles.update({int(pr.get("number", 0)): plain(str(pr.get("title") or ""))
                   for pr in state.prs})
    return titles


def overturns_on_issues(issues) -> list[dict]:
    """Every `Overturn:` comment on any issue: issue, link, and createdAt, oldest first."""
    if not isinstance(issues, issuedata.Issues) or not issues.readable:
        return []
    found = []
    for issue in issues.items:
        for comment in issue.comment_items:
            first = github.heading(str(comment.get("body") or "").replace("\r\n", "\n"))
            opened = github.OVERTURN.match(first)
            if opened:
                found.append({"issue": issue.number, "link": opened.group(1).strip(),
                              "time": str(comment.get("createdAt") or "")})
    found.sort(key=lambda entry: (entry["time"], entry["issue"]))
    return found


def _counts(entry: dict, since: datetime | None, titles: dict[int, str]) -> bool:
    """Tells whether an overturn turns spot checks off (F18 design 7.4)."""
    when = _time(entry["time"])
    if since is not None and when is not None and when <= since:
        return False
    number = link_pr(entry["link"])
    if number is None or number not in titles:
        return True
    found = feature_stage(titles[number])
    return bool(found) and found[1] in _STAGES


def off_due(state) -> dict | None:
    """While spot checks are set: the overturn that turns them off, or None (D179)."""
    if not state.spot_checks:
        return None
    since, titles = _turned_on_at(state), _titles(state)
    for entry in overturns_on_issues(state.issues):
        if _counts(entry, since, titles):
            return {"issue": entry["issue"], "overturn": entry["link"],
                    "approves_first": len(state.order or [])}
    return None


def load(state, notes: list[str]) -> None:
    """Reads the risky marks and whether an overturn turned spot checks off.

    Call it after the issues and every PR are read (issuesync.load), before
    anything asks merged_by.
    """
    if state.repo is None or not state.origin:
        return
    state.spot_off = off_due(state)
    state.risk = _risk(state, notes)


# --------------------------------------------------------------------------- the report


def report(state) -> dict:
    """The report's `spot` part (F18 design 8)."""
    order = state.order or []
    return {"on": state.spot_on, "configured": state.spot_checks, "every": state.spot_every,
            "approves_first": state.approves_first,
            "sample": sample(order, state.approves_first, state.spot_every)
            if state.spot_checks else [],
            "off_due": dict(state.spot_off) if state.spot_off else None}


def decorate(state, entry: dict) -> dict:
    """Gives a next entry its `spot` and `risky` keys (F18 design 8)."""
    entry["spot"], entry["risky"] = None, []
    item, stage = entry.get("item"), entry.get("stage")
    if entry.get("action") in ("stage", "continue-pr") and item and stage in _STAGES:
        entry["spot"] = state.spot_of(item)
        entry["risky"] = list(state.risk.get((item, stage), []))
    return entry


# --------------------------------------------------------------------------- issues


_REASONS = {"interface": ("设计改动了已有接口", "the design changes an existing interface"),
            "ruling": ("第 3 轮有裁定", "a ruling at round 3"),
            "premise": ("用过前提尝试", "a premise attempt")}


def _reason_texts(mark: dict) -> tuple[str, str]:
    """One mark in the progress issue's Risky line, Chinese and English."""
    number = mark["pr"]
    if mark["by"] == "engine":
        zh, en = _REASONS[mark["reason"]]
    elif mark["by"] == "architect":
        zh, en = f"架构师：{mark['reason']}", f"the Architect: {mark['reason']}"
    else:
        return f"你：{mark['reason']}", f"you: {mark['reason']}"
    return (f"{zh}（#{number}）", f"{en} (#{number})") if number else (zh, en)


def progress_lines(state, fid: str) -> list[tuple[str, str]]:
    """The progress issue's spot check lines, Chinese and English (F18 design 7.1, 7.2)."""
    if not state.spot_on:
        return []
    lines = []
    if state.spot_of(fid) == "sample":
        lines.append(("抽查：这个功能在抽查样本里，设计和测试计划合并后由你复查。",
                      "Spot check: this feature is in the sample; you review its design and "
                      "test plan after they merge."))
    stage = state.current(fid)
    marks = state.risk.get((fid, stage), []) if stage in _STAGES else []
    if marks:
        texts = [_reason_texts(mark) for mark in marks]
        lines.append((f"风险：{'；'.join(t[0] for t in texts)}，合并前等你批准。",
                      f"Risky: {'; '.join(t[1] for t in texts)}; it waits for your approval "
                      "before the merge."))
    return lines


def ever_on(state) -> bool:
    """Tells whether a config on origin/main's history ever set spot checks on."""
    try:
        out = git.git(state.repo, "log", "--format=%H", MAIN, "--", CONFIG_PATH)
    except FlowError:
        return False
    for commit in out.split():
        try:
            if parse_config(git.read(state.repo, commit, CONFIG_PATH)).spot_checks:
                return True
        except (ConfigError, tomllib.TOMLDecodeError):
            continue
    return False


def samples(state, version: str, issues) -> list[dict]:
    """The version's sampled PRs: number, title, and whether Troy answered (F18 design 7.1).

    A sample is a merged PR 1 or PR 2 of the version's features with the spot
    check comment. Troy answers it with a comment on it after that comment, or
    with an overturn that names it.
    """
    if not ever_on(state):
        return []
    ids = set(state.versions.get(version, []))
    named = {link_pr(entry["link"]) for entry in overturns_on_issues(issues)}
    found = []
    for pr in sorted(state.all_prs or [], key=lambda p: int(p.get("number", 0))):
        title = plain(str(pr.get("title") or ""))
        stage = feature_stage(title)
        if (str(pr.get("state") or "").upper() != "MERGED" or not stage
                or stage[0] not in ids or stage[1] not in _STAGES):
            continue
        number = int(pr.get("number", 0))
        try:
            items = github.comment_items(state.repo, number)
        except FlowError:
            continue
        comments = github.read_comments([i["body"] for i in items])
        if comments.spot:
            found.append({"number": number, "title": title, "url": pr.get("url"),
                          "answered": bool(comments.troy_after_spot) or number in named})
    return found


# --------------------------------------------------------------------------- evidence


def _e1(state, merged: Merged) -> dict:
    """E1: Troy's answers to the last 6 waits for PR 1 and PR 2 changed nothing."""
    entry = {"result": "unknown", "prs": [], "changed": []}
    if state.all_prs is None:
        return entry
    candidates = sorted((int(pr.get("number", 0)) for pr in state.all_prs
                         if str(pr.get("state") or "").upper() == "MERGED"
                         and (feature_stage(plain(str(pr.get("title") or ""))) or (0, 0))[1]
                         in _STAGES), reverse=True)
    for number in candidates:
        facts = merged.facts(number)
        if facts and facts["waited"]:
            entry["prs"].append(number)
            if facts["changed"]:
                entry["changed"].append(number)
        if len(entry["prs"]) == E1_COUNT:
            break
    if len(entry["prs"]) == E1_COUNT:
        entry["result"] = "fails" if entry["changed"] else "holds"
    return entry


def _last_version(state) -> str | None:
    """The newest version, in the requirements' order, with an accepted feature."""
    found = None
    for version, ids in state.versions.items():
        if any(6 in state.merged.get(fid, set()) for fid in ids):
            found = version
    return found


def _e2(state) -> dict:
    """E2: no real-run mismatch of the last version came from a design or test plan."""
    version = _last_version(state)
    entry = {"result": "unknown", "version": version, "requirement": []}
    if version is None or state.all_prs is None:
        entry["version"] = None
        return entry
    ids = set(state.versions.get(version, []))
    for pr in sorted(state.all_prs, key=lambda p: int(p.get("number", 0))):
        title = plain(str(pr.get("title") or ""))
        status = str(pr.get("state") or "").upper()
        stage = feature_stage(title)
        tag = release_tag(title)
        accept = status == "MERGED" and stage is not None and stage[1] == 6 and stage[0] in ids
        release = tag is not None and status in ("OPEN", "MERGED") \
            and (parse_tag(tag) or ("", 0))[0] == version
        if not (accept or release):
            continue
        number = int(pr.get("number", 0))
        try:
            items = github.comment_items(state.repo, number)
        except FlowError:
            entry.update(result="unknown", version=None, requirement=[])
            return entry
        comments = github.read_comments([i["body"] for i in items])
        if any(r["kind"] == "requirement" for r in comments.tm_rulings):
            entry["requirement"].append(number)
    entry["result"] = "fails" if entry["requirement"] else "holds"
    return entry


def plugin_root() -> Path:
    """The plugin folder the engine runs from: three levels above troyflow."""
    return Path(__file__).resolve().parents[3]


def _troyexam():
    """Imports troyexam from the plugin's troy-mode/exam folder."""
    folder = str(plugin_root() / "troy-mode" / "exam")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    from troyexam import instructions  # noqa: PLC0415  (only for E3)

    return instructions


class _PluginTree:
    """The plugin's instruction folders on disk, read as troyexam's FolderTree reads them."""

    def __init__(self, root: Path, tree):
        """Wraps a FolderTree of the plugin and lists only the instruction folders."""
        self.root, self.tree = root, tree

    def files(self) -> list[str]:
        """The files under the instruction folders, as FolderTree lists them."""
        found = []
        for folder in _INSTRUCTION_FOLDERS:
            base = self.root / folder
            if base.is_dir():
                found += [f"{folder}/{rel}" for rel in type(self.tree)(base).files()]
        return sorted(found)

    def read(self, path: str) -> bytes | None:
        """The file's bytes, or None."""
        return self.tree.read(path)


def plugin_hash() -> str:
    """The instruction hash of the plugin the engine runs from (F16 design 9.1)."""
    instructions = _troyexam()
    root = plugin_root()
    return instructions.instruction_hash(_PluginTree(root, instructions.FolderTree(root)))


def _case_version(case: str) -> int | None:
    """The case's version in the plugin's case.toml, or None."""
    path = plugin_root() / "troy-mode" / "exam" / "cases" / case / "case.toml"
    try:
        return int(tomllib.loads(path.read_text(encoding="utf-8")).get("version"))
    except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError):
        return None


def _case_rows(path: Path) -> list[dict]:
    """A case log's rows: a tab-separated file with a header line; [] when missing."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if not lines:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:] if line.strip()]


def _case_entry(cases: Path, case: str, digest: str) -> dict:
    """One case's runs on the current instructions and its result (E3)."""
    version = _case_version(case)
    rows = [row for row in _case_rows(cases / f"{case}.tsv")
            if row.get("instructions") == digest and row.get("status") != "void"
            and version is not None and str(row.get("case_version")) == str(version)]
    newest = sorted(rows, key=lambda row: row.get("time", ""), reverse=True)[:E3_RUNS]
    passed = sum(1 for row in newest if row.get("passed") == "true")
    if len(rows) < E3_RUNS:
        result = "no runs"
    else:
        result = "holds" if passed >= E3_PASSES else "fails"
    return {"id": case, "result": result, "runs": len(rows), "passed": passed}


def _e3() -> dict:
    """E3: each case of PR 1's and PR 2's roles passes 4 of 5 on the current instructions."""
    root = os.environ.get(EXAM_ROOT_VARIABLE) or EXAM_ROOT_DEFAULT
    entry = {"result": "unknown", "root": root, "instructions": None, "cases": []}
    try:
        entry["instructions"] = plugin_hash()
    except (ImportError, OSError) as exc:
        entry["error"] = str(exc)
        return entry
    cases = Path(root) / "cases"
    if not cases.is_dir():
        return entry
    entry["cases"] = [_case_entry(cases, case, entry["instructions"]) for case in EVIDENCE_CASES]
    entry["result"] = "holds" if all(c["result"] == "holds" for c in entry["cases"]) else "fails"
    return entry


def evidence(state, notes: list[str]) -> dict:
    """E1 to E3 and whether all three hold (F18 design 7.3, D178)."""
    merged = Merged(state.repo, notes)
    found = {"E1": _e1(state, merged), "E2": _e2(state), "E3": _e3()}
    merged.save()
    found["met"] = all(found[key]["result"] == "holds" for key in ("E1", "E2", "E3"))
    return {"met": found["met"], "E1": found["E1"], "E2": found["E2"], "E3": found["E3"]}
