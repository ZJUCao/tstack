"""The batch plan: AR7's plan of the features that may run at once (F20 design 3.4, D271).

AR7 gives the plan in its report's Summary as one fenced block: a line per
feature with the modules, interfaces, and shared documents it touches, and a
line per order, such as "F10 after F08 1/6". `plan --report` parses it, checks
it against the features that may start, and keeps it in the common git folder.
"""

import json
import re
from pathlib import Path

from troycheck.modules import parse_table

from . import repo as git
from . import teams
from .repo import MAIN, Repo
from .requirements import parse_features
from .stages import merged_stages

REQUIREMENTS = "docs/requirements.md"
ARCHITECTURE = "docs/architecture.md"
FILE = "plan.json"
_FENCE = re.compile(r"^\s*(```|~~~)")
_FEATURE = re.compile(r"^(F\d+) modules: (.*?); interfaces: (.*?); documents: (.*)$")
_ORDER = re.compile(r"^(F\d+) after (F\d+) ([1-6])/6$")


def _problem(kind: str, message: str) -> dict:
    """Builds one problem of the report."""
    return {"kind": kind, "message": message}


def _names(cell: str) -> list[str]:
    """Reads a comma-separated list, or none for an empty one."""
    cell = cell.strip()
    if cell.lower() == "none" or not cell:
        return []
    return [name.strip().strip("`") for name in cell.split(",") if name.strip()]


def _blocks(text: str) -> list[list[str]]:
    """Lists the lines of each fenced block of a report."""
    blocks, inside = [], None
    for line in text.replace("\r\n", "\n").split("\n"):
        if _FENCE.match(line):
            if inside is None:
                inside = []
            else:
                blocks.append(inside)
                inside = None
        elif inside is not None:
            inside.append(line)
    return blocks


def _is_plan_line(line: str) -> bool:
    """Tells whether a line is a feature line or an order line."""
    return bool(_FEATURE.match(line.strip()) or _ORDER.match(line.strip()))


def parse(text: str) -> tuple[dict | None, list[dict]]:
    """Reads the plan from a report: the first fenced block that holds a plan line.

    Returns:
        The plan ({"features": {...}, "orders": [...]}) or None, and the problems.
    """
    block = next((b for b in _blocks(text) if any(_is_plan_line(line) for line in b)), None)
    if block is None:
        return None, [_problem("no-plan", "The report has no fenced block with a plan line, "
                               "such as `F08 modules: cli; interfaces: none; documents: none`.")]
    features, orders, problems = {}, [], []
    for raw in block:
        line = raw.strip()
        if not line:
            continue
        found, order = _FEATURE.match(line), _ORDER.match(line)
        if found:
            features[found.group(1)] = {"modules": _names(found.group(2)),
                                        "interfaces": _names(found.group(3)),
                                        "documents": _names(found.group(4))}
        elif order:
            orders.append({"feature": order.group(1), "after": order.group(2),
                           "stage": int(order.group(3))})
        else:
            problems.append(_problem("line", f"Not a plan line: {line!r}."))
    return {"features": features, "orders": orders}, problems


def batch(repo: Repo) -> list[str]:
    """The dependency-ready features on origin/main, in the requirements' order."""
    features = parse_features(git.read(repo, MAIN, REQUIREMENTS)) or []
    merged = merged_stages(git.subjects(repo, MAIN))
    accepted = {fid for fid, stages in merged.items() if 6 in stages}
    return [f.id for f in features if f.id not in accepted
            and all(dep in accepted for dep in [*f.hard, *f.soft])]


def _cycle(orders: list[dict]) -> list[str] | None:
    """Returns the features of a cycle in the orders, or None."""
    after: dict[str, set[str]] = {}
    for order in orders:
        after.setdefault(order["feature"], set()).add(order["after"])
    state: dict[str, int] = {}

    def visit(node: str, path: list[str]) -> list[str] | None:
        state[node] = 1
        for nxt in sorted(after.get(node, ())):
            if state.get(nxt) == 1:
                return path + [node, nxt]
            if state.get(nxt) is None:
                found = visit(nxt, path + [node])
                if found:
                    return found
        state[node] = 2
        return None

    for node in sorted(after):
        if state.get(node) is None:
            found = visit(node, [])
            if found:
                return found
    return None


def _ordered(orders: list[dict], one: str, other: str) -> bool:
    """Tells whether an order joins two features, in either direction."""
    return any({o["feature"], o["after"]} == {one, other} for o in orders)


def check(repo: Repo, plan: dict, ready: list[str]) -> list[dict]:
    """Checks a parsed plan against the batch and the architecture (F20 design 3.4)."""
    problems, features, orders = [], plan["features"], plan["orders"]
    for fid in ready:
        if fid not in features:
            problems.append(_problem("missing", f"{fid} may start but has no feature line."))
    for fid in features:
        if fid not in ready:
            problems.append(_problem("not-ready", f"{fid} is not a feature that may start: it "
                                     "is accepted, or a feature it depends on is not."))
    for order in orders:
        text = f"`{order['feature']} after {order['after']} {order['stage']}/6`"
        for fid in (order["feature"], order["after"]):
            if fid not in ready:
                problems.append(_problem("not-ready", f"The order {text} names {fid}, which is "
                                         "not a feature that may start."))
            if fid not in features:
                problems.append(_problem("order", f"The order {text} names {fid}, which has no "
                                         "feature line."))
    cycle = _cycle(orders)
    if cycle:
        problems.append(_problem("order", f"The orders make a cycle: {' -> '.join(cycle)}."))
    modules = parse_table(git.read(repo, MAIN, ARCHITECTURE) or "")
    if modules is not None:
        known = {m.name for m in modules}
        for fid, entry in features.items():
            for name in entry["modules"]:
                if name not in known:
                    problems.append(_problem("module", f"{fid} names the module {name!r}, which "
                                             "the architecture's module table does not have."))
    ids = sorted(features)
    for i, one in enumerate(ids):
        for other in ids[i + 1:]:
            shared = sorted(set(features[one]["interfaces"]) & set(features[other]["interfaces"]))
            if shared and not _ordered(orders, one, other):
                problems.append(_problem("overlap", f"{one} and {other} both change "
                                         f"{', '.join(shared)}, and no order puts one after "
                                         "the other."))
    return problems


def path(repo: Repo) -> Path:
    """Returns <common git folder>/troy-mode/plan.json."""
    return teams.common_dir(repo) / "troy-mode" / FILE


def load(repo: Repo) -> dict | None:
    """Reads the kept plan, or None when there is none or it cannot be read."""
    try:
        data = json.loads(path(repo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("features"), dict) else None


def run_plan(args) -> tuple[dict, int]:
    """Parses, checks, and keeps AR7's plan (F20 design 3.4)."""
    repo = git.need_repo(args.repo)
    text = Path(args.report).read_text(encoding="utf-8")
    ready = batch(repo) if git.commit_of(repo, MAIN) else []
    plan, problems = parse(text)
    if plan is not None:
        problems += check(repo, plan, ready)
    report = {"command": "plan", "ok": not problems, "problems": problems, "batch": ready,
              "plan": plan, "notes": []}
    if problems:
        return report, 1
    kept = {"commit": git.commit_of(repo, MAIN), **plan}
    target = path(repo)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(kept, indent=2) + "\n", encoding="utf-8", newline="\n")
    report["path"] = str(target)
    return report, 0
