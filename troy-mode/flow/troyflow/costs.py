"""costs: a feature's or a version's role runs and their cost (F07 design 8.8, D264 to D267).

It reads the session transcripts that Claude Code keeps on this PC, ties each
role run to the item its brief names, and prices every assistant message at
the list prices of prices.toml. It reads git and the transcripts only: no gh
call, and it writes nothing. tstack issue #74.
"""

import datetime
import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import repo as git
from .errors import FlowError
from .repo import MAIN, Repo
from .requirements import parse_features
from .stages import feature_stage, plain
from .versions import is_patch, parse_tag, release_tag, versions_of

PRICES_FILE = Path(__file__).resolve().parent.parent / "prices.toml"
PRICES_ENV = "TROY_MODE_PRICES"  # another prices file, for tests
ROLES = {"troy-architect": "Architect", "troy-interface-designer": "Interface Designer",
         "troy-test-manager": "Test Manager", "troy-developer": "Developer",
         "troy-test-engineer": "Test Engineer", "troy-code-reviewer": "Code Reviewer"}
ORDER = list(ROLES.values())
PRICE_KEYS = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")
_ITEM = re.compile(r"^Item: ([^,\s]+)(?:,[ \t]*(.*?))?[ \t]*$", re.M)
_SLUG = re.compile(r"[^A-Za-z0-9]")
_SUFFIX = re.compile(r"\[[^\]]*\]$")  # such as "[1m]", the context size, priced the same
_DESKTOP = "--claude-worktrees-"
_CHECK = 0.01  # the share by which the desktop app's figure may differ (D266)


@dataclass
class Message:
    """One priced assistant message.

    Attributes:
        moment: When it was written.
        model: The model's ID.
        usage: The usage the API reported.
    """

    moment: datetime.datetime
    model: str
    usage: dict


@dataclass
class Transcript:
    """One session file or subagent file.

    Attributes:
        key: The file's ID: the session ID or the agent ID.
        start: Its first record's time, or None.
        end: Its last record's time, or None.
        messages: Its assistant messages, each once.
        first_text: The text of its first user record.
        cost_states: Its `cost-state` records, in order.
    """

    key: str
    start: datetime.datetime | None = None
    end: datetime.datetime | None = None
    messages: list[Message] = field(default_factory=list)
    first_text: str = ""
    cost_states: list[dict] = field(default_factory=list)


@dataclass
class Agent:
    """One subagent run.

    Attributes:
        transcript: Its transcript.
        folder: Its subagents folder, which holds its parent's file too.
        role: The role's name, or None for another agent.
        parent: The agent ID of the agent that started it, or None.
        item: The item its brief names, or None.
        title: The PR title its brief names, or None.
        under: The role run it belongs to: itself, or the role run above it.
    """

    transcript: Transcript
    folder: Path
    role: str | None
    parent: str | None
    item: str | None = None
    title: str | None = None
    under: "Agent | None" = None


def when(text) -> datetime.datetime | None:
    """Parses an ISO 8601 time, such as a transcript's timestamp, or returns None."""
    try:
        moment = datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=datetime.timezone.utc)


def slug(path: str) -> str:
    """The transcript folder name of a working folder (design 8.8)."""
    return _SLUG.sub("-", path)


def _worktrees(repo: Repo) -> list[str]:
    """The main checkout's path first, then every other worktree's, as git prints them."""
    try:
        text = git.git(repo, "worktree", "list", "--porcelain")
    except FlowError:
        text = ""
    paths = [line[len("worktree "):].strip() for line in text.splitlines()
             if line.startswith("worktree ")]
    return paths or [str(repo.root)]


def folders(repo: Repo, given: list[str] | None) -> list[Path]:
    """The transcript folders to read: the given ones, else this project's (D264)."""
    if given:
        return [Path(p) for p in given]
    config = os.environ.get("CLAUDE_CONFIG_DIR")
    projects = (Path(config) if config else Path.home() / ".claude") / "projects"
    paths = _worktrees(repo)
    main = slug(paths[0])
    names = [main] + [slug(p) for p in paths[1:]]
    try:
        names += sorted(n for n in os.listdir(projects) if n.startswith(main + _DESKTOP))
    except OSError:
        pass
    found = []
    for name in dict.fromkeys(names):
        if (projects / name).is_dir():
            found.append(projects / name)
    return found


def _text(content) -> str:
    """The text of a user message's content: a string or a list of text blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def read_transcript(path: Path, main: bool) -> Transcript:
    """Reads one transcript file; a line that is not JSON is skipped.

    Args:
        path: The .jsonl file.
        main: A session file: its sidechain records are not the main session's.
    """
    found = Transcript(path.stem.removeprefix("agent-"))
    seen: set[str] = set()
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return found
    with handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            moment = when(record.get("timestamp")) if record.get("timestamp") else None
            if moment is not None:
                found.start = found.start or moment
                found.end = moment
            kind = record.get("type")
            if kind == "cost-state":
                found.cost_states.append(record)
            elif kind == "user" and not found.first_text:
                found.first_text = _text((record.get("message") or {}).get("content"))
            elif kind == "assistant" and not (main and record.get("isSidechain")):
                _add_message(found, seen, record, moment)
    return found


def _add_message(found: Transcript, seen: set[str], record: dict,
                 moment: datetime.datetime | None) -> None:
    """Adds an assistant record's message once (a message repeats per content block)."""
    message = record.get("message") or {}
    usage = message.get("usage")
    model = str(message.get("model") or "")
    if not isinstance(usage, dict) or not model or model.startswith("<") or moment is None:
        return
    key = str(message.get("id") or record.get("requestId") or record.get("uuid") or "")
    if key and key in seen:
        return
    seen.add(key)
    found.messages.append(Message(moment, model, usage))


def read_folder(folder: Path) -> tuple[list[tuple[Path, Transcript]], list[Agent]]:
    """Reads a project transcript folder: its sessions and their subagents."""
    sessions, agents = [], []
    for path in sorted(folder.glob("*.jsonl")):
        sessions.append((path, read_transcript(path, main=True)))
    for meta_path in sorted(folder.glob("*/subagents/agent-*.meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        meta = meta if isinstance(meta, dict) else {}
        path = meta_path.with_name(meta_path.name.removesuffix(".meta.json") + ".jsonl")
        transcript = read_transcript(path, main=False)
        role = ROLES.get(str(meta.get("agentType") or "").rsplit(":", 1)[-1])
        agent = Agent(transcript, meta_path.parent, role,
                      str(meta["parentAgentId"]) if meta.get("parentAgentId") else None)
        found = _ITEM.search(transcript.first_text)
        if found:
            agent.item, agent.title = found.group(1), (found.group(2) or None)
        agents.append(agent)
    _link(agents)
    return sessions, agents


def _link(agents: list[Agent]) -> None:
    """Sets each agent's role run: itself for a role, else the role run above it."""
    by_id = {(a.folder, a.transcript.key): a for a in agents}
    for agent in agents:
        current, hops = agent, 0
        while current is not None and current.role is None and current.parent and hops < 50:
            current, hops = by_id.get((current.folder, current.parent)), hops + 1
        agent.under = current if current is not None and current.role else None


def load_prices() -> dict:
    """Reads the price table: prices.toml, or the file TROY_MODE_PRICES names."""
    path = Path(os.environ.get(PRICES_ENV) or PRICES_FILE)
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise FlowError(f"cannot read the price table {path.name}: {exc}") from exc


def _tokens(usage: dict) -> tuple[int, int, int, int, int, int]:
    """Input, output, cache read, 5-minute write, 1-hour write, and web searches."""
    def number(value) -> int:
        return int(value) if isinstance(value, (int, float)) else 0
    writes = usage.get("cache_creation")
    if isinstance(writes, dict):
        five = number(writes.get("ephemeral_5m_input_tokens"))
        hour = number(writes.get("ephemeral_1h_input_tokens"))
    else:
        five, hour = number(usage.get("cache_creation_input_tokens")), 0
    tools = usage.get("server_tool_use") if isinstance(usage.get("server_tool_use"), dict) else {}
    return (number(usage.get("input_tokens")), number(usage.get("output_tokens")),
            number(usage.get("cache_read_input_tokens")), five, hour,
            number(tools.get("web_search_requests")))


def price(prices: dict, message: Message) -> float | None:
    """The cost of one message in dollars, or None when its model has no price."""
    table = (prices.get("models") or {}).get(_SUFFIX.sub("", message.model))
    if isinstance(table, dict) and message.usage.get("speed") == "fast":
        table = table.get("fast")
    if not isinstance(table, dict) or any(k not in table for k in PRICE_KEYS):
        return None
    tokens = _tokens(message.usage)
    rates = [float(table[k]) for k in PRICE_KEYS]
    return (sum(t * r for t, r in zip(tokens[:5], rates)) / 1_000_000
            + tokens[5] * float(prices.get("web_search", 0)))


def display(model: str) -> str:
    """A model's family and version, such as "Opus 5.5", with no word R19 refuses."""
    parts = _SUFFIX.sub("", model).removeprefix("claude-").split("-")
    if not parts or not parts[0]:
        return model.removeprefix("claude-")
    version = []
    for part in parts[1:]:
        if not (part.isdigit() and len(part) <= 2):
            break
        version.append(part)
    return " ".join([parts[0].capitalize()] + ([".".join(version)] if version else []))


@dataclass
class Tally:
    """Runs, models, and cost of one row of the report."""

    runs: int = 0
    models: set[str] = field(default_factory=set)
    cost: float = 0.0
    unpriced: dict[str, int] = field(default_factory=dict)

    def add(self, prices: dict, messages: list[Message]) -> None:
        """Adds the cost and models of some messages."""
        for message in messages:
            value = price(prices, message)
            self.models.add(display(message.model))
            if value is None:
                self.unpriced[message.model] = self.unpriced.get(message.model, 0) + 1
            else:
                self.cost += value

    def entry(self, **extra) -> dict:
        """The report's entry for this row."""
        return {**extra, "runs": self.runs, "models": sorted(self.models),
                "cost": round(self.cost, 2)}


def _subject_time(repo: Repo, sha: str) -> datetime.datetime:
    """The committer time of a commit, in UTC."""
    text = git.git(repo, "show", "-s", "--format=%cI", sha).strip()
    return datetime.datetime.fromisoformat(text).astimezone(datetime.timezone.utc)


def _accept_time(repo: Repo, log: list[tuple[str, str]], item: str) -> datetime.datetime | None:
    """The time of the newest accept commit of a feature on origin/main, or None."""
    for sha, subject in log:
        if feature_stage(plain(subject)) == (item, 6):
            return _subject_time(repo, sha)
    return None


def _tag_window(repo: Repo, log: list[tuple[str, str]], tag: str
                ) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    """The previous release commit's time and the tag's own release commit's time."""
    own = next((i for i, (_, s) in enumerate(log) if release_tag(plain(s)) == tag), None)
    start_at = own + 1 if own is not None else 0
    previous = next((sha for sha, s in log[start_at:]
                     if release_tag(plain(s)) and release_tag(plain(s)) != tag), None)
    return (_subject_time(repo, previous) if previous else None,
            _subject_time(repo, log[own][0]) if own is not None else None)


def _inside(moment, start, end) -> bool:
    """Tells whether a time lies in [start, end]; a missing bound is open."""
    return moment is not None and (start is None or moment >= start) and \
        (end is None or moment <= end)


def _money(value: float) -> str:
    """Dollars with cents and thousands separators."""
    return f"${value:,.2f}"


def _clock(moment: datetime.datetime | None) -> str:
    """A time for the description, in UTC to the minute."""
    return moment.astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC") \
        if moment else "the start"


def _iso(moment: datetime.datetime | None) -> str | None:
    """A time for the JSON report."""
    return moment.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") \
        if moment else None


def _check_prices(prices: dict, sessions: list[tuple[Path, Transcript]], notes: list[str]) -> None:
    """Compares the newest cost-state record with the price table (D266)."""
    with_states = [(p, t) for p, t in sessions if t.cost_states]
    if not with_states:
        return
    newest = max(with_states, key=lambda pt: pt[0].stat().st_mtime)[1].cost_states[-1]
    usage_by_model = newest.get("modelUsage") if isinstance(newest.get("modelUsage"), dict) else {}
    for model, numbers in sorted(usage_by_model.items()):
        if not isinstance(numbers, dict):
            continue
        app = numbers.get("costUSD")
        usage = {"input_tokens": numbers.get("inputTokens"),
                 "output_tokens": numbers.get("outputTokens"),
                 "cache_read_input_tokens": numbers.get("cacheReadInputTokens"),
                 "cache_creation": {
                     "ephemeral_5m_input_tokens": numbers.get("cacheCreationEphemeral5mInputTokens"),
                     "ephemeral_1h_input_tokens": numbers.get("cacheCreationEphemeral1hInputTokens")},
                 "server_tool_use": {"web_search_requests": numbers.get("webSearchRequests")}}
        ours = price(prices, Message(datetime.datetime.now(datetime.timezone.utc), model, usage))
        if not isinstance(app, (int, float)) or app <= 0:
            continue
        if ours is None:
            notes.append(f"The price table has no price for {display(model)}, which the "
                         "desktop app priced.")
        elif abs(ours - app) > _CHECK * app:
            notes.append(f"The desktop app priced {display(model)} at {_money(app)} where the "
                         f"price table (as of {prices.get('as_of')}) gives {_money(ours)}: the "
                         "price table may be out of date.")


def run_costs(args) -> tuple[dict, int]:
    """Reports a feature's or a version's role runs and their cost at list prices.

    Args:
        args: Parsed options: item, tag, until, transcripts, and repo.

    Returns:
        The report and the exit code, 0 whenever the transcripts could be read.
    """
    if bool(args.item) == bool(args.tag):
        raise FlowError("give exactly one of --item and --tag")
    if args.tag and parse_tag(args.tag) is None:
        raise FlowError(f"--tag {args.tag!r} is not a tag of the form vMAJOR.MINOR.PATCH")
    until = None
    if args.until:
        until = when(args.until)
        if until is None:
            raise FlowError(f"--until {args.until!r} is not an ISO 8601 time")
    repo = git.need_repo(args.repo)
    prices = load_prices()
    sessions, agents = [], []
    for folder in folders(repo, args.transcripts):
        found_sessions, found_agents = read_folder(folder)
        sessions += found_sessions
        agents += found_agents
    log = git.log(repo, MAIN) if git.commit_of(repo, MAIN) else []
    now = datetime.datetime.now(datetime.timezone.utc)
    notes: list[str] = []
    if args.item:
        runs = [a for a in agents if a.role and a.item == args.item]
        start = min((a.transcript.start for a in runs if a.transcript.start), default=None)
        end = until or _accept_time(repo, log, args.item) or now
        mine = [a for a in agents if a.under is not None and a.under in runs]
        if not runs:
            notes.append(f"No role run of {args.item} was found in this PC's transcripts.")
    else:
        start, own = _tag_window(repo, log, args.tag)
        end = until or own or now
        if start is None:
            start = min((t.start for t in [*(t for _, t in sessions),
                                           *(a.transcript for a in agents)] if t.start),
                        default=None)
        runs = None
        mine = [a for a in agents if a.under is not None
                and _inside(a.under.transcript.start, start, end)]
    report = _report(args, prices, sessions, agents, mine, (start, end), runs is not None
                     and not runs, notes)
    report["missing"] = _missing(repo, log, args, mine)
    report["notes"] += [f"Not found here: {title}." for title in report["missing"]]
    _check_prices(prices, sessions, report["notes"])
    report["description"], report["line"] = _texts(report, args)
    return report, 0


def _report(args, prices: dict, sessions, agents: list[Agent], mine: list[Agent],
            window: tuple, nothing: bool, notes: list[str]) -> dict:
    """Builds the report's figures."""
    start, end = window
    roles: dict[str, Tally] = {}
    helpers, others, main = Tally(), Tally(), Tally()
    items: dict[str, float] = {}
    unpriced: dict[str, int] = {}
    if not nothing:
        for agent in mine:
            tally = roles.setdefault(agent.role, Tally()) if agent.role else helpers
            tally.runs += 1
            tally.add(prices, agent.transcript.messages)
            if args.tag and agent.under.item:
                items[agent.under.item] = (items.get(agent.under.item, 0.0)
                                           + _cost(prices, agent.transcript.messages))
        for agent in agents:
            if agent.under is None and _inside(agent.transcript.start, start, end):
                others.runs += 1
                others.add(prices, agent.transcript.messages)
        for _, transcript in sessions:
            inside = [m for m in transcript.messages if _inside(m.moment, start, end)]
            if inside:
                main.runs += 1
                main.add(prices, inside)
    for tally in [*roles.values(), helpers, others, main]:
        for model, count in tally.unpriced.items():
            unpriced[model] = unpriced.get(model, 0) + count
    read = [t for _, t in sessions]
    notes.insert(0, f"Read from the transcripts on this PC only: {len(read)} session"
                    f"{'' if len(read) == 1 else 's'}.")
    total = sum(t.cost for t in [*roles.values(), helpers, others, main])
    return {"command": "costs", "ok": True, "item": args.item, "tag": args.tag,
            "window": None if nothing else {"from": _iso(start), "to": _iso(end)},
            "prices": {"as_of": prices.get("as_of")},
            "roles": [roles[name].entry(role=name) for name in ORDER if name in roles],
            "helpers": helpers.entry(), "others": others.entry(),
            "main": {"sessions": main.runs, "models": sorted(main.models),
                     "cost": round(main.cost, 2)},
            "total": round(total, 2), "items": {k: round(v, 2) for k, v in sorted(items.items())},
            "sessions": [{"id": t.key, "from": _iso(t.start), "to": _iso(t.end)} for t in read],
            "unpriced": [{"model": m, "messages": n} for m, n in sorted(unpriced.items())],
            "notes": notes, "found": bool(read)}


def _cost(prices: dict, messages: list[Message]) -> float:
    """The priced part of some messages' cost."""
    return sum(v for v in (price(prices, m) for m in messages) if v is not None)


def _missing(repo: Repo, log: list[tuple[str, str]], args, mine: list[Agent]) -> list[str]:
    """The merged stages, or the version's features, with no role run found (D264)."""
    if args.item:
        titles = {feature_stage(a.title or "") for a in mine if a.role and a.title}
        missing = []
        for _, subject in reversed(log):
            found = feature_stage(plain(subject))
            if found and found[0] == args.item and 1 <= found[1] <= 5 and found not in titles \
                    and plain(subject) not in missing:
                missing.append(plain(subject))
        return missing
    if is_patch(args.tag):
        return []
    features = parse_features(git.read(repo, MAIN, "docs/requirements.md")) if log else None
    version = parse_tag(args.tag)[0]
    items = {a.under.item for a in mine if a.under and a.under.item}
    return [fid for fid in versions_of(features).get(version, []) if fid not in items]


def _texts(report: dict, args) -> tuple[str, str]:
    """The description's section and the line for Troy (design 8.8)."""
    name = args.item or args.tag
    if not report.pop("found"):
        return ("## Cost\n\nNot measured: no transcript of this project was found on this PC.\n",
                f"No cost was measured for {name}: no transcript was found on this PC.")
    total = _money(report["total"])
    total = f"at least {total}" if report["unpriced"] else total
    runs = sum(r["runs"] for r in report["roles"])
    window = report["window"] or {}
    span = (f"{_clock(when(window['from']) if window.get('from') else None)} to "
            f"{_clock(when(window['to']) if window.get('to') else None)}") if window else "none"
    rows = [f"| {r['role']} | {r['runs']} | {', '.join(r['models'])} | {_money(r['cost'])} |"
            for r in report["roles"]]
    helpers, others, main = report["helpers"], report["others"], report["main"]
    rows.append(f"| Helper agents of the roles | {helpers['runs']} | "
                f"{', '.join(helpers['models'])} | {_money(helpers['cost'])} |")
    if others["runs"]:
        rows.append(f"| Other agents of the main session | {others['runs']} | "
                    f"{', '.join(others['models'])} | {_money(others['cost'])} |")
    sessions = f"{main['sessions']} session{'' if main['sessions'] == 1 else 's'}"
    rows.append(f"| Main session | {sessions} | {', '.join(main['models'])} | "
                f"{_money(main['cost'])} |")
    rows.append(f"| Total | {runs} role run{'' if runs == 1 else 's'} | | {total} |")
    lines = ["## Cost", "",
             f"Role runs of {name} and their token cost at list prices (price table of "
             f"{report['prices']['as_of']}), from the transcripts on this PC, {span}.", "",
             "| Who | Runs | Model | Cost |", "| --- | --- | --- | --- |", *rows]
    if report["items"]:
        lines += ["", "Role runs by item: " + ", ".join(
            f"{k} {_money(v)}" for k, v in report["items"].items()) + "."]
    if report["notes"]:
        lines += [""] + [f"- {_clean(n)}" for n in report["notes"]]
    line = (f"{name} cost {total} at list prices: {runs} role run{'' if runs == 1 else 's'}, "
            f"{helpers['runs']} helper agent{'' if helpers['runs'] == 1 else 's'}, and the main "
            f"session ({_money(main['cost'])}).")
    return "\n".join(lines) + "\n", line


def _clean(text: str) -> str:
    """Keeps a note free of words R19's strict mode refuses and of paths."""
    return re.sub(r"(?i)claude", "", text).replace("\\", "/")
