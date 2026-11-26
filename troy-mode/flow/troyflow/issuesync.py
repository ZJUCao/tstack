"""The issues command: what each progress issue and checklist should be, and the changes that
make it so (F15 design 3.2, 4, 6, 8, and 9).

The engine reads GitHub and never writes to it. It rebuilds each body from the
state, compares it with the issue, writes the bodies that must be posted to
files, and reports the exact gh command for each change. The main session
checks each file with check-text and runs the commands (D141).

F18 adds a wait's ID to the "Waiting for you" line, a line per ruled PR, and a
line per overturn (F18 design 5.3 and 8).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import github, issuedata, notecmd, releases, spot, stops, waits
from . import repo as git
from .errors import FlowError
from .issuedata import CHECKLIST, IDEA, PROGRESS, Issue, Issues
from .issuetext import FEATURE_STATES, MAX_BODY, PR_STATES, SKIPPED_MOCK, Box, ChecklistFacts, \
    ProgressFacts, Scenario, checklist_body, checklist_title, overturn_texts, progress_body, \
    progress_title, review_texts, ruling_texts, waiting_texts
from .realrun import prototype_table
from .repo import MAIN
from .requirements import FEATURE_ID
from .stages import feature_stage, parse_subject, plain
from .state import REQUIREMENTS, State, next_feature, read_state
from .versions import is_patch, parse_plan, parse_tag, plan_path, tables

LABELS = (
    (IDEA, "FBCA04", "An idea or change for troy-mode to take in / 交给 troy-mode 的想法或改动"),
    (PROGRESS, "1D76DB", "A feature's progress, kept by troy-mode / 功能进度，由 troy-mode 维护"),
    (CHECKLIST, "0E8A16",
     "What Troy tests on Troy's devices for a release / 发布前 Troy 在自己设备上测的项目"),
)
REQUIREMENTS_ZH = "docs/requirements.zh-CN.md"
IDEA_TEMPLATE = ".github/ISSUE_TEMPLATE/idea.md"
_SAFE = re.compile(r"[A-Za-z0-9_./:=@%+,-]+")
_BIG_X = re.compile(r"(?m)^- \[X\] ")
_ORDER = {"close-duplicate": 0, "reopen": 1, "create": 2, "edit": 2, "close": 3}


def quote(word: str) -> str:
    """Quotes one word for a POSIX shell: as is when safe, else in single quotes."""
    if word and _SAFE.fullmatch(word):
        return word
    return "'" + word.replace("'", "'\\''") + "'"


def command(argv: list[str]) -> str:
    """The gh command line for an argv."""
    return " ".join(["gh"] + [quote(word) for word in argv])


def same(old: str, new: str) -> bool:
    """Compares two titles or bodies, ignoring CRLF, trailing white space, and [X] for [x]."""
    def norm(text: str) -> str:
        return _BIG_X.sub("- [x] ", text.replace("\r\n", "\n")).rstrip()

    return norm(old) == norm(new)


@dataclass
class Wanted:
    """What one issue should be.

    Attributes:
        kind: "progress" or "device-test".
        item: The feature ID or the tag.
        state: "open", "closed", or None when the issue should be left alone.
        reason: The reason to close: "completed" or "not planned".
        title: The title.
        body: The body, or None when no issue should be created or edited.
        new_run: A checklist rebuilt for a new release test run.
    """

    kind: str
    item: str
    state: str | None
    reason: str | None = None
    title: str = ""
    body: str | None = None
    new_run: bool = False


@dataclass
class Sync:
    """The facts a sync needs besides the state.

    Attributes:
        state: The project's state.
        issues: Every issue read.
        prs: Every PR, open, merged, and closed.
        url: The repository's URL, such as https://github.com/o/r.
        scenarios: The scenarios given with --device-test-scenarios, or None.
        problems: Problems found while building bodies.
    """

    state: State
    issues: Issues
    prs: list[dict]
    url: str
    scenarios: list[str] | None = None
    problems: list[str] = field(default_factory=list)
    _cache: dict = field(default_factory=dict)

    def blob(self, path: str) -> str:
        """A link to a file on main."""
        return f"{self.url}/blob/main/{path}"

    def zh_features(self) -> dict[str, tuple[str, str]]:
        """Each feature's Chinese name and Status cell from the requirements' mirror."""
        if "zh" not in self._cache:
            self._cache["zh"] = zh_features(git.read(self.state.repo, MAIN, REQUIREMENTS_ZH))
        return self._cache["zh"]

    def kept(self, kind: str) -> dict[str, Issue]:
        """The issue kept for each item: the lowest number among those with its marker."""
        if kind not in self._cache:
            self._cache[kind] = {item: found[0] for item, found
                                 in self.issues.marked(kind).items()}
        return self._cache[kind]


def zh_features(text: str | None) -> dict[str, tuple[str, str]]:
    """Reads the Chinese features table: ID to (name, status)."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    for _, header, rows in tables(lines):
        if "编号" in header and "功能" in header:
            name, status = header.index("功能"), header.index("状态") if "状态" in header else None
            found = {}
            for row in rows:
                fid = row[header.index("编号")] if header.index("编号") < len(row) else ""
                if FEATURE_ID.fullmatch(fid):
                    found[fid] = (" ".join(row[name].split()) if name < len(row) else "",
                                  row[status] if status is not None and status < len(row) else "")
            return found
    return {}


# --------------------------------------------------------------------------- progress issues


def _stage_prs(sync: Sync, fid: str) -> dict:
    """The feature's PRs: merged stage numbers, closed ones, and side PRs (design 4.2)."""
    merged, closed, side = {}, [], []
    for pr in sync.prs:
        title = str(pr.get("title") or "")
        found = feature_stage(title)
        state = str(pr.get("state") or "").upper()
        number = int(pr.get("number", 0))
        if found and found[0] == fid:
            if state == "MERGED":
                merged[found[1]] = max(merged.get(found[1], 0), number)
            elif state == "CLOSED":
                closed.append((number, plain(title)))
            continue
        parsed = parse_subject(title)
        if parsed and parsed.id == fid and parsed.stage is None:
            side.append((number, plain(title), state))
    return {"merged": merged, "closed": closed, "side": side}


def _open_stage(state: State, fid: str) -> dict | None:
    """The feature's open stage PR, with its comments read, or None."""
    for pr in state.prs:
        found = feature_stage(str(pr.get("title") or ""))
        if found and found[0] == fid:
            return pr
    return None


def _last_heading(notes: github.Comments) -> dict | None:
    """The open PR's last review or attempt heading (design 4.2)."""
    last = notes.last or ""
    review = github.REVIEW.match(last)
    if review:
        return {"role": review.group(1), "round": int(review.group(2)),
                "result": review.group(3)}
    attempt = github.ATTEMPT.match(last)
    if attempt:
        return {"role": attempt.group(1), "attempt": int(attempt.group(2))}
    return dict(notes.reviews[-1]) if notes.reviews else None


def _waiting(pr: dict | None) -> tuple[str, str]:
    """What waits on Troy for the feature, from its open stage PR (design 4.2).

    A wait with a listed ID starts with it (F18 design 4.2).
    """
    if pr is None or not pr["notes"].waiting:
        return waiting_texts("nothing", None)
    number, last = int(pr.get("number", 0)), pr["notes"].last or ""
    if github.ESCALATION.match(last):
        texts = waiting_texts("escalation", number, last.split(":", 1)[1].strip())
    else:
        question = last.split(":", 1)[1].strip()
        texts = (waiting_texts("approve", number) if question == "approve this PR"
                 else waiting_texts("question", number, question))
    wait = pr["notes"].wait
    if waits.is_listed(wait):
        return f"{wait}，{texts[0]}", f"{wait}, {texts[1]}"
    return texts


def _boxes(sync: Sync, fid: str, prs: dict, open_pr: dict | None) -> list[Box]:
    """The six stage lines (design 4.2)."""
    state = sync.state
    merged = state.merged.get(fid, set())
    skips = state.skips_mock(fid)
    open_stage = feature_stage(str(open_pr.get("title") or ""))[1] if open_pr else None
    boxes = []
    for stage in range(1, 7):
        if stage in merged:
            number = prs["merged"].get(stage)
            zh, en = PR_STATES["MERGED"]
            boxes.append(Box(stage, True, f"#{number}，{zh}" if number else zh,
                             f"#{number}, {en}" if number else en))
        elif stage == 3 and skips:
            boxes.append(Box(stage, True, *SKIPPED_MOCK))
        elif stage == open_stage:
            number = int(open_pr.get("number", 0))
            zh, en = f"#{number}，进行中", f"#{number}, open"
            heading = _last_heading(open_pr["notes"])
            if heading:
                review = review_texts(heading)
                zh, en = f"{zh}。{review[0]}", f"{en}. {review[1]}"
            boxes.append(Box(stage, False, zh, en))
        else:
            boxes.append(Box(stage, False))
    return boxes


def _feature_state(state: State, fid: str) -> str:
    """accepted, in progress, or not started."""
    merged = state.merged.get(fid, set())
    if 6 in merged:
        return "accepted"
    if merged or _open_stage(state, fid):
        return "in progress"
    return "not started"


def _deps(sync: Sync, feature) -> list[tuple[str, str]]:
    """The dependency lines, each with its progress issue when one exists."""
    kept = sync.kept(PROGRESS)
    found = []
    for dep in dict.fromkeys(feature.hard + feature.soft):
        zh, en = FEATURE_STATES[_feature_state(sync.state, dep)]
        issue = kept.get(dep)
        found.append((f"{dep}（#{issue.number}，{zh}）" if issue else f"{dep}（{zh}）",
                      f"{dep} (#{issue.number}, {en})" if issue else f"{dep} ({en})"))
    return found


def _docs(sync: Sync, fid: str) -> list[tuple[str, str, str]]:
    """Links to the feature's documents on main: requirements, design, test plan, prototypes."""
    repo = sync.state.repo
    docs = []
    req_zh = REQUIREMENTS_ZH if REQUIREMENTS_ZH in _main_files(sync, "docs") else REQUIREMENTS
    docs.append(("requirements", sync.blob(req_zh), sync.blob(REQUIREMENTS)))
    folder = sync.state.feature_folder(fid)
    if folder:
        names = set(git.files(repo, MAIN, folder))
        for kind in ("design", "test-plan"):
            path = f"{folder}/{kind}.md"
            if path in names:
                mirror = f"{folder}/{kind}.zh-CN.md"
                docs.append((kind, sync.blob(mirror if mirror in names else path),
                             sync.blob(path)))
    for path in _prototypes(sync, fid):
        docs.append(("prototype", sync.blob(path), sync.blob(path)))
    return docs


def _main_files(sync: Sync, folder: str) -> set[str]:
    """Every file under a folder of origin/main, read once."""
    key = f"files:{folder}"
    if key not in sync._cache:
        sync._cache[key] = set(git.files(sync.state.repo, MAIN, folder))
    return sync._cache[key]


def _prototypes(sync: Sync, fid: str) -> list[str]:
    """The feature's prototypes: the requirements' prototypes table, else by file name."""
    if "table" not in sync._cache:
        sync._cache["table"] = prototype_table(git.read(sync.state.repo, MAIN, REQUIREMENTS))
    table = sync._cache["table"]
    names = _main_files(sync, "docs/prototypes")
    if table is not None:
        return [item.file for item in table if fid in item.features and item.file in names]
    pattern = re.compile(rf"docs/prototypes/{fid}-[^/]*\.md")
    return sorted(n for n in names if pattern.fullmatch(n) and not n.endswith(".zh-CN.md"))


def _extra(sync: Sync, fid: str, prs: dict) -> list[tuple[str, str]]:
    """Side PRs, real-run bugs, and stage PRs closed without merging (design 4.2)."""
    lines = []
    if prs["side"]:
        lines.append(("附带 PR：" + "；".join(f"#{n} {t}（{PR_STATES.get(s, (s, s))[0]}）"
                                            for n, t, s in prs["side"]),
                      "Side PRs: " + "; ".join(f"#{n} {t} ({PR_STATES.get(s, (s, s))[1]})"
                                               for n, t, s in prs["side"])))
    lines += _ruling_lines(sync, fid)
    lines += [overturn_texts(entry["ruling"], entry["done"])
              for entry in stops.from_issues(sync.issues) if entry["item"] == fid]
    lines += spot.progress_lines(sync.state, fid)
    bugs = [i for i in sync.issues.items if i.title.startswith(f"Real run of {fid}:")]
    if bugs:
        lines.append(("实际运行发现的 bug：" + "；".join(
                          f"#{i.number} {i.title}（{'未解决' if i.open else '已解决'}）" for i in bugs),
                      "Real-run bugs: " + "; ".join(
                          f"#{i.number} {i.title} ({'open' if i.open else 'closed'})" for i in bugs)))
    noted = notecmd.progress_line(sync.issues, fid)
    if noted:
        lines.append(noted)
    if prs["closed"]:
        lines.append(("关闭未合并的 PR：" + "；".join(f"#{n} {t}" for n, t in prs["closed"]),
                      "Closed without merging: " + "; ".join(f"#{n} {t}" for n, t in prs["closed"])))
    return lines


def _ruled_candidates(sync: Sync, fid: str) -> dict[int, tuple[str, str]]:
    """The feature's stage and test-fix PRs, open or merged: number to (state, URL)."""
    found: dict[int, tuple[str, str]] = {}
    for pr in [*sync.prs, *({**p, "state": "OPEN"} for p in sync.state.prs)]:
        title = str(pr.get("title") or "")
        stage = feature_stage(title)
        parsed = parse_subject(title)
        if not ((stage and stage[0] == fid)
                or (parsed and parsed.id == fid and parsed.kind == "test-fix")):
            continue
        state = str(pr.get("state") or "").upper()
        if state in ("OPEN", "MERGED"):
            found[int(pr.get("number", 0))] = (state, str(pr.get("url") or ""))
    return found


def _ruling_lines(sync: Sync, fid: str) -> list[tuple[str, str]]:
    """One line per ruled PR of the feature: its newest result and its first ruling (D174)."""
    candidates = _ruled_candidates(sync, fid)
    if not candidates:
        return []
    opened = {int(pr.get("number", 0)): pr for pr in sync.state.prs}
    merged = stops.merged_rulings(sync.state.repo, sorted(
        number for number, (state, _) in candidates.items()
        if state == "MERGED" and number not in opened))
    lines = []
    for number in sorted(candidates):
        if number in opened:
            notes = opened[number]["notes"]
            pairs = list(zip(notes.rulings, notes.ruling_urls))
        else:
            pairs = [(entry["ruling"], entry["url"]) for entry in merged.get(number, [])]
        if pairs:
            first, url = pairs[0]
            lines.append(ruling_texts(number, first["ruler"], first["round"],
                                      pairs[-1][0]["result"], url or candidates[number][1]))
    return lines


def progress_facts(sync: Sync, feature) -> ProgressFacts:
    """Works out what a feature's progress issue shows (design 4.2)."""
    state, fid = sync.state, feature.id
    prs = _stage_prs(sync, fid)
    open_pr = _open_stage(state, fid)
    zh_name, zh_status = sync.zh_features().get(fid, ("", ""))
    current = state.current(fid)
    status = None
    if feature.status.strip() and feature.status.strip().lower() != "not started":
        status = (zh_status or feature.status, feature.status)
    version = releases.feature_version(state, fid)
    return ProgressFacts(fid, feature.name, zh_name, version, current or 6, _waiting(open_pr),
                         _boxes(sync, fid, prs, open_pr), status, _extra(sync, fid, prs),
                         _deps(sync, feature), _docs(sync, fid))


def _has_stage_pr(sync: Sync, fid: str) -> bool:
    """Tells whether a feature has a stage PR, open or merged (design 4.1)."""
    if sync.state.merged.get(fid) or _open_stage(sync.state, fid):
        return True
    return any((found := feature_stage(str(pr.get("title") or ""))) and found[0] == fid
               and str(pr.get("state") or "").upper() in ("OPEN", "MERGED") for pr in sync.prs)


def _team_features(state: State) -> set[str]:
    """The features that may start, or that have a team, with feature teams (F20 design 3.12)."""
    from .teamstate import compute  # noqa: PLC0415  (teamstate imports nextstep, which needs this)

    part = compute(state)
    return set(part["may_start"]) | {team["id"] for team in part["teams"]}


def wanted_progress(sync: Sync) -> list[Wanted]:
    """What each progress issue should be (design 4.1, 4.4, and 4.5)."""
    state = sync.state
    kept = sync.kept(PROGRESS)
    nxt = next_feature(state)
    teamed = _team_features(state)
    found, known = [], set()
    for feature in state.features or []:
        fid = feature.id
        known.add(fid)
        issue = kept.get(fid)
        title = progress_title(fid, feature.name, sync.zh_features().get(fid, ("", ""))[0])
        if 6 in state.merged.get(fid, set()):
            if issue is None:
                continue
            final = "- [x] 6/6 " in issue.body
            if not final or issue.open:
                body = None if final else progress_body(progress_facts(sync, feature))
                found.append(Wanted(PROGRESS, fid, "closed", "completed", title, body))
            continue
        if fid == nxt or fid in teamed or _has_stage_pr(sync, fid):
            found.append(Wanted(PROGRESS, fid, "open", None, title,
                                progress_body(progress_facts(sync, feature))))
        elif issue is not None and issue.open:
            found.append(Wanted(PROGRESS, fid, "closed", "not planned"))
    for fid, issue in kept.items():
        if fid not in known and issue.open:
            found.append(Wanted(PROGRESS, fid, "closed", "not planned"))
    return found


# --------------------------------------------------------------------------- checklists


def _passed_run(pr: dict) -> int | None:
    """The highest passed release test run on a release PR, or None."""
    runs = [r["run"] for r in pr["notes"].runs if r["by"] == "claude" and r["result"] == "passed"]
    return max(runs) if runs else None


def zh_rows(text: str | None) -> tuple[dict[str, dict], list[str]]:
    """Reads a plan mirror: each scenario's Chinese cells by ID, and Troy's devices."""
    rows, devices = {}, []
    lines = (text or "").replace("\r\n", "\n").split("\n")
    for _, header, body in tables(lines):
        if "由谁运行" not in header:
            continue
        for row in body:
            cells = {name: (row[i] if i < len(row) else "") for i, name in enumerate(header)}
            if "编号" in header:
                rows[cells["编号"]] = cells
            elif "设备" in header and cells.get("由谁运行", "").lower() == "troy":
                system = cells.get("操作系统", "")
                devices.append(f"{cells['设备']}（{system}）" if system else cells["设备"])
    return rows, devices


def _raw_cells(line: str) -> list[str]:
    """Splits a table row into trimmed cells, keeping backticks."""
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", inner)]


def raw_rows(text: str | None) -> dict[str, dict]:
    """Each scenario row's cells as written, backticks kept, by ID (design 6.2: "as written")."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    found: dict[str, dict] = {}
    for index, header, rows in tables(lines):
        key = "id" if "id" in header else "编号" if "编号" in header else None
        if key is None:
            continue
        for offset, cells in enumerate(rows):
            raw = _raw_cells(lines[index + 2 + offset])
            if len(raw) == len(cells) and header.index(key) < len(cells):
                found.setdefault(cells[header.index(key)],
                                 {name: raw[i] for i, name in enumerate(header) if i < len(raw)})
    return found


def _scenarios(sync: Sync, version: str, named: list[str] | None,
               ticks: issuedata.Ticks | None) -> list[Scenario]:
    """Troy's scenarios of the version test plan, in both languages (design 6.2)."""
    repo = sync.state.repo
    en_text = git.read(repo, MAIN, plan_path(version))
    plan = sync.state.plans.get(version) or parse_plan(en_text)
    if plan is None:
        return []
    zh_text = git.read(repo, MAIN, plan_path(version).replace(".md", ".zh-CN.md"))
    zh, zh_devices = zh_rows(zh_text)
    en_raw, zh_raw = raw_rows(en_text), raw_rows(zh_text)
    found = []
    for row in plan.by("Troy"):
        if named is not None and row.id not in named:
            continue
        mirror = zh_raw.get(row.id) or zh.get(row.id, {})
        written = en_raw.get(row.id, {})

        def cell(name: str, row=row, written=written) -> str:
            return written.get(name) or row.cell(name)

        if row.performance:
            load, duration = cell("load"), cell("duration")
            zh_load, zh_duration = mirror.get("负载", load), mirror.get("持续时间", duration)
            target, zh_target = cell("target"), mirror.get("指标", cell("target"))
            machine = cell("machine")
            found.append(Scenario(row.id, (zh_target, target),
                                  (mirror.get("机器", machine), machine),
                                  (f"负载：{zh_load}；持续时间：{zh_duration}",
                                   f"Load: {load}; duration: {duration}"),
                                  (zh_target, target)))
        else:
            en_devices = ", ".join(plan.troy_devices)
            found.append(Scenario(row.id, (mirror.get("场景", cell("scenario")),
                                           cell("scenario")),
                                  ("、".join(zh_devices) or en_devices, en_devices),
                                  (mirror.get("步骤", cell("steps")), cell("steps")),
                                  (mirror.get("预期结果", cell("expected result")),
                                   cell("expected result"))))
    for scenario in found:
        scenario.ticked = bool(ticks and ticks.scenarios.get(scenario.id))
    return found


def _features_line(sync: Sync, version: str) -> list[tuple[str, str]]:
    """The version's features with their statuses, in both languages."""
    zh = sync.zh_features()
    found = []
    for fid in sync.state.versions.get(version, []):
        feature = sync.state.feature(fid)
        name_zh, status_zh = zh.get(fid, ("", ""))
        status = feature.status if feature else ""
        found.append((f"{fid} {name_zh or feature.name}" + (f"（{status_zh or status}）" if status else ""),
                      f"{fid} {feature.name}" + (f" ({status})" if status else "")))
    return found


def checklist_facts(sync: Sync, tag: str, pr: dict, issue: Issue | None) -> tuple[ChecklistFacts, bool]:
    """Works out the checklist of a release and whether it starts a new run (design 6.2, 6.3)."""
    version = parse_tag(tag)[0]
    notes: github.Comments = pr["notes"]
    run = _passed_run(pr) or 1
    ticks = issuedata.read_ticks(issue.body) if issue is not None else None
    named = None
    if is_patch(tag):
        named = ticks.named if ticks and ticks.named is not None else list(sync.scenarios or [])
    new_run = bool(ticks and ticks.run is not None and ticks.run < run)
    if new_run:
        failed = notes.troy_failed[max(notes.troy_failed)] if notes.troy_failed else []
        ticks.accept = False
        for sid in failed:
            ticks.scenarios[sid] = False
    plan_en, plan_zh = plan_path(version), plan_path(version).replace(".md", ".zh-CN.md")
    facts = ChecklistFacts(tag, run, notes.commits.get(run, ""), int(pr.get("number", 0)),
                           (sync.blob("CHANGELOG.zh-CN.md"), sync.blob("CHANGELOG.md")),
                           (sync.blob(plan_zh), sync.blob(plan_en)), _features_line(sync, version),
                           _scenarios(sync, version, named, ticks),
                           bool(ticks and ticks.accept), named)
    facts.samples = _sample_boxes(sync, version, ticks)
    return facts, new_run


def _sample_boxes(sync: Sync, version: str, ticks: issuedata.Ticks | None) -> list:
    """One box for each sample Troy has not answered, or whose box Troy ticked (F18 7.1)."""
    ticked = ticks.samples if ticks else {}
    return [(entry["number"], entry["title"], bool(ticked.get(entry["number"])))
            for entry in spot.samples(sync.state, version, sync.issues)
            if ticked.get(entry["number"]) or not entry["answered"]]


def wanted_checklists(sync: Sync) -> list[Wanted]:
    """What each checklist should be (design 6.1, 6.3, and 6.5)."""
    state = sync.state
    kept = sync.kept(CHECKLIST)
    found = []
    target = releases.target(state) if state.versions else None
    target_tag = None
    if target is not None and target[1] is not None and _passed_run(target[1]) is not None:
        target_tag, pr = target
        issue = kept.get(target_tag)
        facts, new_run = checklist_facts(sync, target_tag, pr, issue)
        body = checklist_body(facts)
        if len(body) > MAX_BODY:
            facts.short = True
            body = checklist_body(facts)
            sync.problems.append(f"The checklist of {target_tag} would pass {MAX_BODY:,} "
                                 "characters: each scenario's steps are a link to the plan.")
        found.append(Wanted(CHECKLIST, target_tag, "open", None, checklist_title(target_tag), body,
                            new_run))
    released = {c[2] for c in releases.release_commits(state)}
    for tag, issue in kept.items():
        if tag != target_tag and issue.open and tag in released:
            found.append(Wanted(CHECKLIST, tag, "closed", "completed"))
    return found


# --------------------------------------------------------------------------- actions


def _action(action: str, wanted: Wanted, issue: Issue | None, **values) -> dict:
    """Builds one action of the report, without its argv."""
    entry = {"action": action, "kind": wanted.kind, "item": wanted.item,
             "number": issue.number if issue else None, "title": wanted.title or
             (issue.title if issue else ""), "labels": [wanted.kind] if action == "create" else [],
             "body_file": None, "reason": None, "duplicate_of": None, "new_run": False}
    entry.update(values)
    return entry


def actions_for(sync: Sync, wanted: Wanted) -> list[dict]:
    """The changes that make one issue what it should be."""
    issues = sync.issues.marked(wanted.kind).get(wanted.item, [])
    kept = issues[0] if issues else None
    found = [_action("close-duplicate", wanted, other, duplicate_of=kept.number)
             for other in issues[1:] if other.open]
    if wanted.state == "open":
        if kept is None:
            found.append(_action("create", wanted, None, body=wanted.body,
                                 new_run=wanted.new_run))
            return found
        if not kept.open:
            found.append(_action("reopen", wanted, kept))
        if not (same(kept.title, wanted.title) and same(kept.body, wanted.body or "")):
            found.append(_action("edit", wanted, kept, body=wanted.body, new_run=wanted.new_run))
    elif wanted.state == "closed" and kept is not None:
        if wanted.body is not None and not (same(kept.title, wanted.title)
                                            and same(kept.body, wanted.body)):
            found.append(_action("edit", wanted, kept, body=wanted.body))
        if kept.open:
            found.append(_action("close", wanted, kept, reason=wanted.reason))
    return found


def plan(sync: Sync) -> list[dict]:
    """Every change, in order: progress issues by feature, then checklists."""
    found = []
    for wanted in wanted_progress(sync) + wanted_checklists(sync):
        found += sorted(actions_for(sync, wanted), key=lambda a: _ORDER[a["action"]])
    return found


def finish(actions: list[dict], folder: Path | None) -> list[dict]:
    """Writes the body files and adds each action's argv and command."""
    for entry in actions:
        body = entry.pop("body", None)
        if body is not None and folder is not None:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{entry['kind']}-{entry['item']}.md"
            path.write_bytes(body.encode("utf-8"))
            entry["body_file"] = path.as_posix()
        number = str(entry["number"])
        kind = entry["action"]
        if kind == "create":
            argv = ["issue", "create", "--title", entry["title"], "--label", entry["kind"],
                    "--body-file", entry["body_file"] or ""]
        elif kind == "edit":
            argv = ["issue", "edit", number, "--title", entry["title"], "--body-file",
                    entry["body_file"] or ""]
        elif kind == "close":
            argv = ["issue", "close", number, "--reason", entry["reason"]]
        elif kind == "reopen":
            argv = ["issue", "reopen", number]
        else:
            argv = ["issue", "close", number, "--duplicate-of", str(entry["duplicate_of"])]
        entry["argv"] = argv
        entry["command"] = command(argv)
    return actions


def label_entries(existing: set[str]) -> list[dict]:
    """The labels of design 8.1 that the repository lacks, with their create commands."""
    found = []
    for name, color, description in LABELS:
        if name in existing:
            continue
        argv = ["label", "create", name, "--color", color, "--description", description]
        found.append({"name": name, "color": color, "description": description, "argv": argv,
                      "command": command(argv)})
    return found


def guess_url(issues: Issues, prs: list[dict]) -> str:
    """The repository URL from any issue's or PR's URL, or "" when there is none."""
    for url in [i.url for i in issues.items] + [str(pr.get("url") or "") for pr in prs]:
        found = issuedata.repo_url(url)
        if found:
            return found
    return ""


# --------------------------------------------------------------------------- the command


def _scenario_list(text: str | None) -> list[str] | None:
    """Parses --device-test-scenarios: IDs separated by commas."""
    if text is None:
        return None
    return [part.strip() for part in text.split(",") if part.strip()]


def run_issues(args) -> tuple[dict, int]:
    """Works out every change to troy-mode's issues (design 3.2).

    Returns:
        The report and exit code 0 whenever the state and GitHub could be read.

    Raises:
        FlowError: A git or gh read failed.
    """
    state = read_state(args.repo)
    if state.repo is None:
        raise FlowError("not inside a git repository")
    report = {"command": "issues", "ok": True, "notes": [], "problems": [], "repository": None,
              "labels": [], "actions": [], "skipped": []}
    if not state.origin:
        report["skipped"].append("origin/main does not exist yet")
        return report, 0
    info = github.gh_object(state.repo, "repo", "view", "--json", "url,hasIssuesEnabled")
    report["repository"] = str(info.get("url") or "") or None
    if info.get("hasIssuesEnabled") is False:
        report["skipped"].append(issuedata.TURNED_OFF)
        return report, 0
    issues = issuedata.read_issues(state.repo)
    if issues.skipped:
        report["skipped"].append(issuedata.TURNED_OFF)
        return report, 0
    if issues.error:
        raise FlowError(issues.error)
    existing = {str(item.get("name")) for item in github.gh_list(
        state.repo, "label", "list", "--limit", "100", "--json", "name")}
    sync = Sync(state, issues, issuedata.read_prs(state.repo), report["repository"] or "",
                _scenario_list(getattr(args, "device_test_scenarios", None)))
    state.issues, state.all_prs = issues, sync.prs
    spot.load(state, report["notes"])
    report["labels"] = label_entries(existing)
    report["actions"] = finish(plan(sync), state.repo.state_dir() / "flow" / "issues")
    report["problems"] = sync.problems
    return report, 0


# --------------------------------------------------------------------------- status


def load(state: State) -> None:
    """Reads the issues and every PR for status, keeping a failure in state.issues (3.3)."""
    issues = issuedata.read_issues(state.repo)
    prs: list[dict] = []
    if issues.readable:
        try:
            prs = issuedata.read_prs(state.repo)
        except FlowError as exc:
            if issuedata.turned_off(str(exc)):
                issues = Issues(skipped=True)
            else:
                issues = Issues(error=str(exc))
    state.issues, state.all_prs = issues, prs


def status_part(state: State) -> dict:
    """The issues part of the status report (design 3.3)."""
    issues: Issues | None = state.issues
    part = {"error": None, "skipped": None, "ideas": [], "troy_comments": [], "device_test": None,
            "pending": 0, "template": None}
    if state.repo is not None and state.origin:
        part["template"] = git.exists(state.repo, MAIN, IDEA_TEMPLATE)
    if issues is None:
        return part
    if issues.skipped:
        part["skipped"] = issuedata.TURNED_OFF
        return part
    if issues.error:
        part["error"] = issues.error
        return part
    part["ideas"] = [{"number": i.number, "title": i.title, "url": i.url, "labels": i.labels,
                      "body": i.body, "new": issuedata.is_new(i),
                      "comments": [{"by": "troy-mode" if issuedata.by_troy_mode(c) else "troy",
                                    "body": c} for c in i.comments]}
                     for i in issues.ideas()]
    for kind in (PROGRESS, CHECKLIST):
        for item, found in issues.marked(kind).items():
            for issue in found:
                bodies = issuedata.troy_since(issue.comments) if issue.open else []
                if bodies:
                    part["troy_comments"].append({"issue": issue.number, "kind": kind,
                                                  "item": item, "bodies": bodies})
    part["troy_comments"].sort(key=lambda c: c["issue"])
    part["device_test"] = device_test(state, issues)
    sync = Sync(state, issues, state.all_prs or [], guess_url(issues, state.all_prs or []))
    try:
        part["pending"] = len(plan(sync))
    except FlowError as exc:
        part["pending"] = None
        part["error"] = f"cannot work out the issue changes: {exc}"
    return part


def open_checklist(state: State, issues: Issues) -> Issue | None:
    """The open checklist of the release target's tag, else the open one with the highest number."""
    found = [i for item, group in issues.marked(CHECKLIST).items() for i in group if i.open]
    if not found:
        return None
    target = releases.target(state) if state.versions else None
    for issue in found:
        if target is not None and issue.mark()[1] == target[0]:
            return issue
    return max(found, key=lambda i: i.number)


def device_test(state: State, issues: Issues) -> dict | None:
    """The open checklist's ticks and result (design 3.3, 6.3)."""
    issue = open_checklist(state, issues)
    if issue is None:
        return None
    ticks = issuedata.read_ticks(issue.body)
    return {"number": issue.number, "tag": issue.mark()[1], "run": ticks.run,
            "scenarios": [{"id": sid, "ticked": on} for sid, on in ticks.scenarios.items()],
            "samples": [{"pr": number, "ticked": on} for number, on in ticks.samples.items()],
            "accept": ticks.accept, "result": issuedata.device_result(ticks)}


def progress_number(state: State, fid: str | None) -> int | None:
    """The feature's progress issue: the open one, else the newest closed one, or None."""
    issues: Issues | None = state.issues
    if not fid or issues is None or not issues.readable:
        return None
    found = issues.marked(PROGRESS).get(fid, [])
    opened = [i for i in found if i.open]
    if opened:
        return opened[0].number
    return found[-1].number if found else None

