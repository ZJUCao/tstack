"""costs (F07 design 3.1, 8.8, D264 to D267, 14.1, 14.2; F08 design 5.7, 11.1, 11.2).

tstack issue #74's interface note fixes what the design leaves to the build:
the command line, the transcript file shapes, the prices file, what is
counted, and the JSON report. Each test writes transcript folders in the
scratch area (session files, subagent files, and their meta files), and runs
``troy_flow.py costs ... --json`` on a clone of a bare origin built by
``flow_helpers``. A test price table goes through ``TROY_MODE_PRICES``, and
``CLAUDE_CONFIG_DIR`` names a scratch folder, so no test reads Troy's real
transcripts or depends on the real price table (except the tests that check
that table and that it is the default).

The test price table, in dollars per million tokens (input, output, cache
read, 5-minute write, 1-hour write): Opus 5.5 1 / 10 / 0.10 / 2 / 4, its fast
table 6 / 60 / 0.60 / 12 / 24; Sonnet 5.5 0.50 / 5 / 0.05 / 1 / 2 with no fast
table; ``claude-haiku-4-5-20251001`` 0.20 / 4 / 0.02 / 0.40 / 0.80; a web
search 0.05. So 1,000 Opus output tokens cost one cent, and 2,000 Sonnet
output tokens one cent. Every value differs from the real table.

Planted bugs of F07 design 14.2 (D264 to D267) caught here:

- "a message's repeated records counted again": ``PricingTests.test_repeated_records_count_once``
  and ``RunKindsTests.test_main_session``.
- "a 1-hour cache write priced as a 5-minute one": ``PricingTests.test_one_hour_write`` and
  ``test_both_writes``.
- "fast speed priced as standard": ``PricingTests.test_fast_speed`` and
  ``test_fast_table_for_every_kind``.
- "an unpriced model counted at zero without a word": ``PricingTests.test_unpriced_model_listed``
  and ``test_unpriced_total_reads_at_least``.
- "a helper counted as a role run of its own": ``RunKindsTests.test_helper_is_not_a_role_run``.
- "a run of another item counted": ``RunKindsTests.test_run_of_another_item_left_out``.
- "main-session messages after the end counted":
  ``AcceptWindowTests.test_main_messages_after_accept_left_out`` and
  ``TagTests.test_version_ends_at_its_release_commit``.
- "a worktree's folder not read": ``DiscoveryTests.test_git_worktree_folder_read`` and
  ``test_desktop_worktree_folder_read``.
- "a model ID in the description": ``RunKindsTests.test_description_and_line_hold_no_claude``.
- "the price note given at any difference": ``CostStateTests.test_no_note_within_one_percent``.

F08 design 11.2: "a version's cost counted from the previous version's tag
instead of the previous release commit of any tag":
``TagTests.test_version_counts_from_the_patch_release``.
"""

import itertools
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence

from flow_helpers import (
    ENGINE, F01, F02, F03, F04, PLUGIN_ROOT, TWO, Fakes, FlowCase, Outcome, Project, base_env,
    base_files, base_step, bug_step, bug_title, commit_time, new_dir, parallel, release_step,
    stage_step, stages, subject_commits, tests_title, version_tests_step,
)

PRICES_FILE = PLUGIN_ROOT / "troy-mode/flow/prices.toml"
SKILL = PLUGIN_ROOT / "skills/troy-mode/SKILL.md"
OPUS = "claude-opus-5-5"
SONNET = "claude-sonnet-5-5"
HAIKU_DATED = "claude-haiku-4-5-20251001"
UNKNOWN = "claude-x-9"
# Output tokens that cost one cent in the test table.
CENT_TOKENS = {OPUS: 1000, SONNET: 2000, HAIKU_DATED: 2500}
IF = "tstack:troy-interface-designer"
DV = "tstack:troy-developer"
HEADER = "| Who | Runs | Model | Cost |"
HELPERS_ROW = "Helper agents of the roles"
OTHERS_ROW = "Other agents of the main session"
MAIN_ROW = "Main session"
NOT_MEASURED = "Not measured: no transcript of this project was found on this PC."
BASE_TIME = 1794000000  # 2026-11-06 UTC, a fixed time after the seed commits (2025-11-06)
FIVE_KEYS = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")

PRICES_TOML = """\
as_of = "2026-01-02"
source = "https://example.com/pricing"
web_search = 0.05

[models."claude-opus-5-5"]
input = 1.00
output = 10.00
cache_read = 0.10
cache_write_5m = 2.00
cache_write_1h = 4.00

[models."claude-opus-5-5".fast]
input = 6.00
output = 60.00
cache_read = 0.60
cache_write_5m = 12.00
cache_write_1h = 24.00

[models."claude-sonnet-5-5"]
input = 0.50
output = 5.00
cache_read = 0.05
cache_write_5m = 1.00
cache_write_1h = 2.00

[models."claude-haiku-4-5-20251001"]
input = 0.20
output = 4.00
cache_read = 0.02
cache_write_5m = 0.40
cache_write_1h = 0.80
"""
TEST_PRICES = new_dir("prices") / "prices.toml"
TEST_PRICES.write_bytes(PRICES_TOML.encode("utf-8"))
EMPTY_CONFIG = new_dir("claude-config")
(EMPTY_CONFIG / "projects").mkdir()
_IDS = itertools.count(1)


# ------------------------------------------------------------------ records

def iso(seconds: float) -> str:
    """A transcript timestamp, ``YYYY-MM-DDTHH:MM:SS.000Z``, in UTC."""
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def seconds_of(text: str) -> float:
    """Seconds since the epoch of an ISO 8601 time such as ``2026-11-12T14:03:00Z``."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def tokens(inp: int = 0, out: int = 0, read: int = 0, w5: int = 0, w1: int = 0, web: int = 0,
           speed: str = "standard", split: bool = True) -> dict:
    """An assistant message's ``usage``.

    Args:
        inp: Input tokens.
        out: Output tokens.
        read: Cache read tokens.
        w5: 5-minute cache write tokens.
        w1: 1-hour cache write tokens.
        web: Web search requests.
        speed: ``standard`` or ``fast``.
        split: Whether ``cache_creation`` splits the writes; without it,
            ``cache_creation_input_tokens`` is ``w5 + w1``.

    Returns:
        The usage.
    """
    usage = {"input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": read,
             "cache_creation_input_tokens": w5 + w1,
             "server_tool_use": {"web_search_requests": web, "web_fetch_requests": 0},
             "service_tier": "standard", "speed": speed}
    if split:
        usage["cache_creation"] = {"ephemeral_5m_input_tokens": w5,
                                   "ephemeral_1h_input_tokens": w1}
    return usage


def user(when: float, text: str, as_list: bool = False) -> dict:
    """A ``user`` record whose content is a text or a list of text blocks."""
    content = [{"type": "text", "text": text}] if as_list else text
    return {"type": "user", "timestamp": iso(when), "uuid": f"u-{next(_IDS):06d}",
            "message": {"role": "user", "content": content}}


def assistant(when: float, usage: Optional[dict], model: str = OPUS, copies: int = 1,
              sidechain: Optional[bool] = None) -> list:
    """The records of one assistant message: one per content block, same ID and usage.

    Args:
        when: The records' time.
        usage: The usage, or None for a record without one.
        model: The message's model.
        copies: How many records repeat the message.
        sidechain: ``isSidechain`` when given; else the file's default.

    Returns:
        The records.
    """
    msg_id = f"msg_{next(_IDS):06d}"
    records = []
    for n in range(copies):
        message = {"id": msg_id, "type": "message", "role": "assistant", "model": model,
                   "content": [{"type": "text", "text": f"Part {n + 1}."}]}
        if usage is not None:
            message["usage"] = dict(usage)
        record = {"type": "assistant", "timestamp": iso(when), "uuid": f"u-{next(_IDS):06d}",
                  "message": message}
        if sidechain is not None:
            record["isSidechain"] = sidechain
        records.append(record)
    return records


def spend(when: float, cents: int, model: str = OPUS) -> list:
    """One assistant message of output tokens that cost ``cents`` in the test table."""
    return assistant(when, tokens(out=cents * CENT_TOKENS[model]), model)


def model_usage(cost: float, inp: int = 0, out: int = 0, read: int = 0, w5: int = 0, w1: int = 0,
                web: int = 0) -> dict:
    """One model's entry of a ``cost-state`` record's ``modelUsage``."""
    return {"inputTokens": inp, "outputTokens": out, "cacheReadInputTokens": read,
            "cacheCreationEphemeral5mInputTokens": w5,
            "cacheCreationEphemeral1hInputTokens": w1, "webSearchRequests": web,
            "costUSD": cost}


def cost_state(models: Mapping[str, dict]) -> dict:
    """A ``cost-state`` record of the desktop app (D266)."""
    return {"type": "cost-state", "totalCostUSD": round(sum(m["costUSD"] for m in models.values()),
                                                        2),
            "modelUsage": dict(models)}


def brief(item: str, title: str, task: str = "IF1") -> str:
    """A role run's first message, in the brief's format (F07 design 6.1)."""
    return (f"Task: {task}, Write the stage's output.\nItem: {item}, {title}\nRead first:\n"
            "- docs/requirements.md\nInput: None\nRound: None\nChecks to run: None\n")


def _flatten(records: Sequence) -> list:
    """Records as a flat list: a list of records is spread, a text is a raw line."""
    flat = []
    for item in records:
        flat.extend(item if isinstance(item, list) else [item])
    return flat


class Transcripts:
    """One project transcript folder: ``<session ID>.jsonl`` files and their subagents.

    Attributes:
        root: The folder.
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        """Uses the folder given, or a new one in the scratch area."""
        self.root = Path(root) if root is not None else new_dir("transcripts")
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write(path: Path, records: Sequence, defaults: Mapping) -> None:
        """Writes JSON lines; dict records get the defaults they lack, texts go as they are."""
        lines = []
        for record in _flatten(records):
            if isinstance(record, str):
                lines.append(record)
                continue
            record = dict(record)
            for key, value in defaults.items():
                if key == "isSidechain" and record.get("type") not in ("user", "assistant"):
                    continue
                record.setdefault(key, value)
            lines.append(json.dumps(record))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    def session(self, sid: str, *records, mtime: Optional[float] = None) -> Path:
        """Writes the main session's file ``<sid>.jsonl``.

        Args:
            sid: The session ID.
            *records: Records, lists of records, or raw lines.
            mtime: The file's modification time, or None to leave it.

        Returns:
            The file.
        """
        path = self.root / f"{sid}.jsonl"
        self._write(path, records, {"sessionId": sid, "isSidechain": False})
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def agent(self, sid: str, aid: str, agent_type: str, *records, parent: Optional[str] = None,
              depth: Optional[int] = None, description: str = "A task") -> Path:
        """Writes a subagent's ``agent-<aid>.jsonl`` and ``agent-<aid>.meta.json``.

        Args:
            sid: The session it ran in.
            aid: The agent ID.
            agent_type: The meta file's ``agentType``.
            *records: Records, lists of records, or raw lines.
            parent: The ``parentAgentId``, or None.
            depth: The ``spawnDepth``; default 1, or 2 with a parent.
            description: The meta file's ``description``.

        Returns:
            The transcript file.
        """
        folder = self.root / sid / "subagents"
        path = folder / f"agent-{aid}.jsonl"
        self._write(path, records, {"sessionId": sid, "isSidechain": True, "agentId": aid})
        meta = {"agentType": agent_type, "description": description,
                "spawnDepth": depth if depth is not None else (1 if parent is None else 2)}
        if parent is not None:
            meta["parentAgentId"] = parent
        (folder / f"agent-{aid}.meta.json").write_bytes(json.dumps(meta).encode("utf-8"))
        return path

    def role_run(self, sid: str, aid: str, agent_type: str, start: float, item: str, title: str,
                 cents: int, model: str = OPUS, task: str = "IF1", as_list: bool = False) -> Path:
        """A role run: its brief at ``start``, then one message that costs ``cents``."""
        return self.agent(sid, aid, agent_type, user(start, brief(item, title, task), as_list),
                          spend(start + 5, cents, model), description=f"{task} {item}")

    def plain_agent(self, sid: str, aid: str, agent_type: str, start: float, cents: int,
                    parent: Optional[str] = None, depth: Optional[int] = None) -> Path:
        """An agent that is not a role: a prompt at ``start``, then one message."""
        return self.agent(sid, aid, agent_type, user(start, "Find the files that read the config."),
                          spend(start + 5, cents), parent=parent, depth=depth)


def tree_state(root: Path, skip: Sequence[str] = ()) -> dict:
    """Every folder and file under a folder: path mapped to (bytes, mtime) or None for a folder."""
    state = {}
    for path in sorted(Path(root).rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            state[rel] = None
        elif rel in skip:
            state[rel] = "present"
        else:
            state[rel] = (path.read_bytes(), path.stat().st_mtime_ns)
    return state


# ------------------------------------------------------------------ running

def run_costs(project: Project, *args, transcripts: Sequence[Path] = (),
              config_dir: Optional[Path] = None, prices: Optional[Path] = TEST_PRICES,
              fakes: Optional[Fakes] = None, env: Optional[Mapping] = None) -> Outcome:
    """Runs ``troy_flow.py costs <args> [--transcripts <folder>]... --repo <clone> --json``.

    Args:
        project: The clone.
        *args: The options after ``costs``, such as ``--item F01``.
        transcripts: Folders passed with ``--transcripts``, in order.
        config_dir: ``CLAUDE_CONFIG_DIR``; default an empty scratch folder.
        prices: ``TROY_MODE_PRICES``; None leaves it unset.
        fakes: The fakes first on the PATH; default a gh that fails every call.
        env: More variables; a None value removes one.

    Returns:
        The outcome, with the parsed report.
    """
    argv = ["costs", *[str(a) for a in args]]
    for folder in transcripts:
        argv += ["--transcripts", str(folder)]
    argv += ["--repo", str(project.root), "--json"]
    fakes = fakes if fakes is not None else Fakes(fail=True)
    full = base_env(fakes.path_env())
    changes = {"CLAUDE_CONFIG_DIR": str(config_dir or EMPTY_CONFIG),
               "TROY_MODE_PRICES": str(prices) if prices is not None else None}
    changes.update(env or {})
    for key, value in changes.items():
        if value is None:
            full.pop(key, None)
        else:
            full[key] = value
    proc = subprocess.run([sys.executable, str(ENGINE), *argv], cwd=str(project.tmp), env=full,
                          capture_output=True, stdin=subprocess.DEVNULL, timeout=180, check=False)
    stdout = proc.stdout.decode("utf-8", "replace")
    try:
        report = json.loads(stdout)
    except ValueError:
        report = None
    return Outcome(proc.returncode, stdout, proc.stderr.decode("utf-8", "replace"), report)


def table_rows(description: str) -> list:
    """The Markdown table's body rows as cell lists, without the header and the rule."""
    rows = []
    for line in description.splitlines():
        line = line.strip()
        if not line.startswith("|") or line == HEADER or set(line) <= set("|-: "):
            continue
        rows.append([cell.strip().strip("*").strip() for cell in line.strip("|").split("|")])
    return rows


def money_text(value: float) -> str:
    """Dollars as the description writes them, such as ``$1,092.03``."""
    return f"${value:,.2f}"


class CostsCase(FlowCase):
    """Assertions shared by the costs tests."""

    def costs_report(self, out: Outcome) -> dict:
        """Asserts exit 0 and a costs report with ``ok`` true, and returns it."""
        self.assertEqual(out.code, 0, out.describe())
        self.assertIsInstance(out.report, dict, out.describe())
        self.assertEqual(out.report.get("command"), "costs", out.describe())
        self.assertIs(out.report.get("ok"), True, out.describe())
        return out.report

    def assert_money(self, value, expected: float, msg: Optional[str] = None) -> None:
        """Asserts a dollar figure to the cent."""
        self.assertIsInstance(value, (int, float), msg)
        self.assertAlmostEqual(float(value), expected, places=2, msg=msg)

    def role_rows(self, report: dict) -> list:
        """``roles`` as ``(role, runs, models, cost rounded to cents)`` tuples, in order."""
        return [(r["role"], r["runs"], r["models"], round(float(r["cost"]), 2))
                for r in report["roles"]]

    def group(self, report: dict, key: str, count: str = "runs") -> tuple:
        """``helpers``, ``others``, or ``main`` as ``(count, models, cost rounded to cents)``."""
        part = report[key]
        return part[count], part["models"], round(float(part["cost"]), 2)

    def assert_time(self, text: Optional[str], seconds: float, msg: str = "") -> None:
        """Asserts that an ISO time names the given second."""
        self.assertIsInstance(text, str, msg)
        self.assertAlmostEqual(seconds_of(text), seconds, delta=1, msg=f"{text} {msg}")


# ------------------------------------------------------------------ pricing

PRICING_STEPS = [base_step(base_files(TWO))] + stages(F01, 2)
SESSION_P = "5e550000-0000-4000-8000-0000000000a1"


def pricing_cases(t: float) -> dict:
    """Each pricing case's records for the Developer's run, from time ``t``."""
    every = dict(inp=2_000_000, out=1_000_000, read=10_000_000, w5=1_000_000, w1=1_000_000,
                 web=20)
    return {
        "input": [assistant(t, tokens(inp=1_000_000))],
        "output": [assistant(t, tokens(out=1_000_000))],
        "cache read": [assistant(t, tokens(read=10_000_000))],
        "5-minute write": [assistant(t, tokens(w5=1_000_000))],
        "1-hour write": [assistant(t, tokens(w1=1_000_000))],
        "both writes": [assistant(t, tokens(w5=1_000_000, w1=2_000_000))],
        "no cache_creation": [assistant(t, tokens(w5=3_000_000, split=False))],
        "web search": [assistant(t, tokens(web=20))],
        "every kind": [assistant(t, tokens(**every))],
        "fast": [assistant(t, tokens(out=1_000_000, speed="fast"))],
        "fast every kind": [assistant(t, tokens(inp=1_000_000, out=1_000_000, read=1_000_000,
                                                w5=1_000_000, w1=1_000_000, speed="fast"))],
        "repeated": [assistant(t, tokens(out=1_000_000), copies=3),
                     assistant(t + 10, tokens(out=1_000_000))],
        "sonnet": [assistant(t, tokens(out=1_000_000), SONNET)],
        "dated model": [assistant(t, tokens(out=1_000_000), HAIKU_DATED)],
        "unpriced": [assistant(t, tokens(out=1_000_000)),
                     assistant(t + 10, tokens(out=1_000_000), UNKNOWN, copies=2),
                     assistant(t + 20, tokens(out=500_000), UNKNOWN)],
        "fast without table": [assistant(t, tokens(out=1_000_000)),
                               assistant(t + 10, tokens(out=1_000_000, speed="fast"), SONNET)],
        "synthetic": [assistant(t, tokens(out=1_000_000)),
                      assistant(t + 10, tokens(out=1_000_000), "<synthetic>")],
        "no usage": [assistant(t, tokens(out=1_000_000)), assistant(t + 10, None)],
        "junk": ["this line is not JSON", "",
                 {"type": "summary", "summary": "Pricing", "leafUuid": "u-x"},
                 {"type": "progress", "timestamp": iso(t),
                  "data": {"usage": tokens(out=9_000_000)}},
                 {"type": "system", "timestamp": iso(t), "content": "Compacted."},
                 assistant(t + 10, tokens(out=1_000_000))],
    }


def pricing_folder(records: list, t: float = BASE_TIME) -> Transcripts:
    """A folder with a main session that costs nothing and one Developer run of F01."""
    folder = Transcripts()
    folder.session(SESSION_P, user(t, "Build F01."), assistant(t + 1, tokens()))
    folder.agent(SESSION_P, "adev0100", DV, user(t + 10, brief("F01", F01.title(3), "DV1")),
                 *records)
    return folder


class PricingTests(CostsCase):
    """Token cost (F07 design 8.8 "Token cost", D265): one Developer run per case."""

    @classmethod
    def setUpClass(cls):
        """One folder and one run per case, side by side, and the default table's run."""
        cls.project = Project(PRICING_STEPS)
        cases = pricing_cases(BASE_TIME + 20)
        cls.folders = {name: pricing_folder(records) for name, records in cases.items()}
        names = list(cases)
        outs = parallel(lambda n: run_costs(cls.project, "--item", "F01",
                                            transcripts=[cls.folders[n].root]), names)
        cls.outs = dict(zip(names, outs))
        cls.default_out = run_costs(cls.project, "--item", "F01",
                                    transcripts=[cls.folders["output"].root], prices=None)

    def report(self, name: str) -> dict:
        """One case's report."""
        return self.costs_report(self.outs[name])

    def developer(self, name: str) -> dict:
        """The Developer's entry of one case's ``roles``, which must be its only role."""
        roles = self.report(name)["roles"]
        self.assertEqual([r["role"] for r in roles], ["Developer"], json.dumps(roles))
        return roles[0]

    def assert_case(self, name: str, expected: float) -> None:
        """The Developer's cost and the total are both the expected dollars."""
        self.assert_money(self.developer(name)["cost"], expected, name)
        self.assert_money(self.report(name)["total"], expected, name)

    def test_input(self):
        """Design 8.8: input tokens at the model's ``input`` price (1M at $1)."""
        self.assert_case("input", 1.00)

    def test_output(self):
        """Design 8.8: output tokens at ``output`` (1M at $10)."""
        self.assert_case("output", 10.00)

    def test_cache_read(self):
        """Design 8.8: cache read tokens at ``cache_read`` (10M at $0.10)."""
        self.assert_case("cache read", 1.00)

    def test_five_minute_write(self):
        """Design 8.8: 5-minute cache writes at ``cache_write_5m`` (1M at $2)."""
        self.assert_case("5-minute write", 2.00)

    def test_one_hour_write(self):
        """Planted bug "a 1-hour cache write priced as a 5-minute one": 1M at $4, not $2."""
        self.assert_case("1-hour write", 4.00)

    def test_both_writes(self):
        """Design 8.8: ``cache_creation`` splits the writes (1M at $2 plus 2M at $4)."""
        self.assert_case("both writes", 10.00)

    def test_missing_cache_creation_counts_as_five_minute(self):
        """Note 2: without ``cache_creation``, the writes are 5-minute ones (3M at $2)."""
        self.assert_case("no cache_creation", 6.00)

    def test_web_search(self):
        """Design 8.8 and D265: each web search at the table's ``web_search`` (20 at $0.05)."""
        self.assert_case("web search", 1.00)

    def test_every_kind_summed(self):
        """Note 3: a message's cost sums every kind: 2 + 10 + 1 + 2 + 4 + 1 dollars."""
        self.assert_case("every kind", 20.00)

    def test_fast_speed(self):
        """Planted bug "fast speed priced as standard": ``speed: fast`` output at $60, not $10."""
        self.assert_case("fast", 60.00)

    def test_fast_table_for_every_kind(self):
        """Design 8.8: every kind of a fast message from the ``fast`` table: 6+60+0.6+12+24."""
        self.assert_case("fast every kind", 102.60)

    def test_repeated_records_count_once(self):
        """Planted bug "a message's repeated records counted again": three records of one ID
        and one other message give $20, not $40."""
        self.assert_case("repeated", 20.00)

    def test_second_model_from_its_own_table(self):
        """D265: a Sonnet 5.5 message at Sonnet's price, shown as "Sonnet 5.5"."""
        self.assert_case("sonnet", 5.00)
        self.assertEqual(self.developer("sonnet")["models"], ["Sonnet 5.5"])

    def test_dated_model_id_display_name(self):
        """Note 5: ``claude-haiku-4-5-20251001`` is priced from its table and shows as
        "Haiku 4.5"."""
        self.assert_case("dated model", 4.00)
        self.assertEqual(self.developer("dated model")["models"], ["Haiku 4.5"])

    def test_unpriced_model_listed(self):
        """Planted bug "an unpriced model counted at zero without a word": the model the table
        lacks is in ``unpriced`` with its two messages (one repeated), and is never guessed."""
        self.assert_case("unpriced", 10.00)
        found = [(u.get("model"), u.get("messages")) for u in self.report("unpriced")["unpriced"]]
        self.assertEqual(found, [(UNKNOWN, 2)])

    def test_unpriced_total_reads_at_least(self):
        """Design 8.8: with an unpriced model, the description's total reads "at least"."""
        rows = {row[0]: row for row in table_rows(self.report("unpriced")["description"])}
        self.assertIn("Total", rows, self.report("unpriced")["description"])
        self.assertIn("at least $10.00", rows["Total"][-1])

    def test_fast_without_fast_table_is_unpriced(self):
        """Note 3: a fast message of a model with no ``fast`` table counts as unpriced."""
        self.assert_case("fast without table", 10.00)
        found = self.report("fast without table")["unpriced"]
        self.assertEqual(len(found), 1, json.dumps(found))
        self.assertIn("sonnet-5-5", found[0].get("model", ""))
        self.assertEqual(found[0].get("messages"), 1)

    def test_synthetic_costs_nothing(self):
        """Note 2: a ``<synthetic>`` message costs nothing and is not unpriced."""
        self.assert_case("synthetic", 10.00)
        self.assertEqual(self.report("synthetic")["unpriced"], [])

    def test_record_without_usage_costs_nothing(self):
        """Note 2: an assistant record without ``usage`` costs nothing and is not unpriced."""
        self.assert_case("no usage", 10.00)
        self.assertEqual(self.report("no usage")["unpriced"], [])

    def test_other_records_and_bad_lines_ignored(self):
        """Note 2: lines that are not JSON and records that are not assistant ones are ignored."""
        self.assert_case("junk", 10.00)

    def test_prices_as_of_from_the_table(self):
        """Note 5: ``prices.as_of`` is the table's ``as_of``, here the test table's."""
        self.assertEqual(self.report("output")["prices"]["as_of"], "2026-01-02")

    def test_default_table_is_the_plugins(self):
        """D265 and note 3: without ``TROY_MODE_PRICES``, ``costs`` reads
        ``troy-mode/flow/prices.toml``: 1M Opus 5.5 output tokens at $20."""
        report = self.costs_report(self.default_out)
        self.assert_money(report["total"], 20.00)


# -------------------------------------------------------------- run kinds

RUN_KINDS_STEPS = ([base_step(base_files((F01, F02, F03)))]
                   + [stage_step(F01, 1), stage_step(F01, 2, style="squash", pr=42),
                      stage_step(F01, 3), stage_step(F01, 4, style="squash", pr=44),
                      stage_step(F01, 5)])
S1 = "5e551111-0000-4000-8000-000000000001"
S2 = "5e552222-0000-4000-8000-000000000002"
S3 = "5e553333-0000-4000-8000-000000000003"
T0 = BASE_TIME


def run_kinds_folder() -> Transcripts:
    """Two sessions of F01's runs, an older session, helpers, other agents, and F02's run.

    S1: a main message before the window ($10), two in it ($1, and $0.50 in two
    records), a sidechain record ($20); the Interface Designer (``tstack:``, $1,
    brief as a text) and the Test Manager (no prefix, $2, brief as blocks); an
    other agent before the window ($3), one in it ($0.75), and its child ($0.25).
    S2: a main message ($2); two Developers (``other-plugin:`` $3, ``tstack:``
    $4); a Sonnet Code Reviewer ($0.50); a helper of the second Developer ($1.50)
    and its helper ($0.25); F02's Interface Designer ($8) and its helper ($0.40).
    S3: one main message a day before ($5).
    """
    folder = Transcripts()
    folder.session(S3, user(T0 - 86400, "Plan the project."), spend(T0 - 86390, 500))
    folder.session(S1, user(T0 - 1200, "Start v0.1."), spend(T0 - 1190, 1000),
                   user(T0 - 10, "Go on with F01."), spend(T0 + 100, 100),
                   assistant(T0 + 110, tokens(out=2_000_000), sidechain=True),
                   assistant(T0 + 200, tokens(out=50_000), copies=2))
    folder.role_run(S1, "aif00001", IF, T0, "F01", F01.title(1), 100, task="IF1")
    folder.role_run(S1, "atm00001", "troy-test-manager", T0 + 300, "F01", F01.title(2), 200,
                    task="TM1", as_list=True)
    folder.plain_agent(S1, "aoth0000", "general-purpose", T0 - 600, 300)
    folder.plain_agent(S1, "aoth0001", "tstack:poteto-agent", T0 + 400, 75)
    folder.plain_agent(S1, "aoth0002", "Explore", T0 + 450, 25, parent="aoth0001")
    folder.session(S2, user(T0 + 1000, "Continue F01."), spend(T0 + 1010, 200))
    folder.role_run(S2, "adv00001", "other-plugin:troy-developer", T0 + 1100, "F01",
                    F01.title(3), 300, task="DV1")
    folder.role_run(S2, "adv00002", DV, T0 + 1500, "F01", F01.title(5), 400, task="DV2")
    folder.role_run(S2, "acr00001", "tstack:troy-code-reviewer", T0 + 1800, "F01", F01.title(5),
                    50, SONNET, task="CR1")
    folder.plain_agent(S2, "ahlp0001", "general-purpose", T0 + 1550, 150, parent="adv00002")
    folder.plain_agent(S2, "ahlp0002", "Explore", T0 + 1560, 25, parent="ahlp0001", depth=3)
    folder.role_run(S2, "aif00002", IF, T0 + 2000, "F02", F02.title(1), 800, task="IF1")
    folder.plain_agent(S2, "ahlp0003", "general-purpose", T0 + 2050, 40, parent="aif00002")
    return folder


class RunKindsTests(CostsCase):
    """``--item F01`` before its acceptance: roles, helpers, other agents, the main session
    (design 8.8 "Which runs belong to an item", note 4 and 5)."""

    @classmethod
    def setUpClass(cls):
        """One clone and folder; F01's run with a working gh, and F03's run, which has none."""
        cls.project = Project(RUN_KINDS_STEPS)
        cls.folder = run_kinds_folder()
        cls.fakes = Fakes()
        cls.repo_before = (cls.project.status_lines(), cls.project.head(),
                           tree_state(cls.project.git_dir(), skip=("index",)))
        cls.files_before = tree_state(cls.folder.root)
        cls.started = time.time()
        cls.out, cls.none_out = parallel(
            lambda args: run_costs(cls.project, *args[0], transcripts=[cls.folder.root],
                                   fakes=args[1]),
            [(("--item", "F01"), cls.fakes), (("--item", "F03"), None)])
        cls.finished = time.time()

    def report(self) -> dict:
        """F01's report."""
        return self.costs_report(self.out)

    def test_roles_in_order(self):
        """Note 5: roles in the fixed order, only those with a run, each with its runs, the
        models' display names, and its cost without its helpers."""
        self.assertEqual(self.role_rows(self.report()), [
            ("Interface Designer", 1, ["Opus 5.5"], 1.00),
            ("Test Manager", 1, ["Opus 5.5"], 2.00),
            ("Developer", 2, ["Opus 5.5"], 7.00),
            ("Code Reviewer", 1, ["Sonnet 5.5"], 0.50)])

    def test_role_from_agent_type_with_any_prefix(self):
        """D264: the role is ``agentType``'s part after the last colon: ``troy-test-manager``
        alone and ``other-plugin:troy-developer`` count as well as ``tstack:``."""
        found = {row[0]: row[1] for row in self.role_rows(self.report())}
        self.assertEqual(found.get("Test Manager"), 1)
        self.assertEqual(found.get("Developer"), 2)

    def test_helpers_under_role_runs(self):
        """D264: an agent whose ``parentAgentId`` is a role run is a helper, and so is its own
        helper two levels deep: 2 runs, $1.75."""
        self.assertEqual(self.group(self.report(), "helpers"), (2, ["Opus 5.5"], 1.75))

    def test_helper_is_not_a_role_run(self):
        """Planted bug "a helper counted as a role run of its own": 5 role runs, the
        Developer's 2 without its helpers."""
        rows = self.role_rows(self.report())
        self.assertEqual(sum(row[1] for row in rows), 5)
        self.assertEqual([row[1] for row in rows if row[0] == "Developer"], [2])

    def test_other_agents(self):
        """Design 8.8: agents no role started count as the main session's other agents when
        they start in the window: the second level of one too; the one before it left out."""
        self.assertEqual(self.group(self.report(), "others"), (2, ["Opus 5.5"], 1.00))

    def test_run_of_another_item_left_out(self):
        """Planted bug "a run of another item counted": F02's Interface Designer ($8) and its
        helper ($0.40) are neither role runs, helpers, nor other agents of F01."""
        report = self.report()
        self.assertEqual([r["runs"] for r in report["roles"] if r["role"] == "Interface Designer"],
                         [1])
        self.assertEqual(report["helpers"]["runs"], 2)
        self.assertEqual(report["others"]["runs"], 2)

    def test_runs_across_two_sessions(self):
        """D264: a role run belongs to its brief's item in any session: S1's and S2's runs
        count, and ``sessions`` lists both."""
        report = self.report()
        roles = [r["role"] for r in report["roles"]]
        self.assertIn("Interface Designer", roles)
        self.assertIn("Developer", roles)
        ids = {s.get("id") for s in report["sessions"]}
        self.assertLessEqual({S1, S2}, ids, json.dumps(report["sessions"]))

    def test_main_session(self):
        """Design 8.8: the main session's messages in the window, each once: $1, $0.50 (two
        records), and $2; not the one before the window ($10) or the sidechain record ($20)."""
        self.assertEqual(self.group(self.report(), "main", "sessions"), (2, ["Opus 5.5"], 3.50))

    def test_window_from_first_run_to_now(self):
        """Design 8.8: from the item's first run to the time ``costs`` runs, before the
        acceptance merges."""
        window = self.report()["window"]
        self.assert_time(window["from"], T0)
        to = seconds_of(window["to"])
        self.assertGreaterEqual(to, self.started - 5)
        self.assertLessEqual(to, self.finished + 5)

    def test_total(self):
        """Note 5: the total of roles, helpers, others, and main: 10.50 + 1.75 + 1 + 3.50."""
        self.assert_money(self.report()["total"], 16.75)

    def test_missing_names_merged_stage_without_run(self):
        """D264 and note 5: stage 4, merged with `` (#44)``, has no run; stage 2, merged with
        `` (#42)``, has one."""
        self.assertEqual(self.report()["missing"], ["[F01 4/6 tests] Count words"])

    def test_items_empty_for_an_item(self):
        """Note 5: ``items`` is ``{}`` for ``--item``."""
        self.assertEqual(self.report()["items"], {})

    def test_notes_say_this_pc_only(self):
        """Design 8.8 "Sessions and PCs": a note says the report reads this PC only."""
        self.assertTrue(any("this pc" in note.lower() for note in self.report()["notes"]),
                        self.report()["notes"])

    def test_item_without_run(self):
        """Note 4: no role run of the item: everything 0 and ``window`` null."""
        report = self.costs_report(self.none_out)
        self.assertIsNone(report["window"])
        self.assertEqual(report["roles"], [])
        self.assert_money(report["total"], 0.0)
        self.assert_money(report["main"]["cost"], 0.0)
        self.assertEqual(report["helpers"]["runs"], 0)

    def test_no_gh_call(self):
        """Design 3.1 and note 1: ``costs`` calls no gh and no mamba."""
        self.report()
        self.assertEqual(self.fakes.gh_calls(), [])
        self.assertEqual(self.fakes.mamba_calls(), [])

    def test_repo_unchanged(self):
        """Note 1: the working tree, HEAD, and the git folder are left as they were."""
        self.report()
        after = (self.project.status_lines(), self.project.head(),
                 tree_state(self.project.git_dir(), skip=("index",)))
        self.assertEqual(after, self.repo_before)

    def test_transcripts_unchanged(self):
        """D264: ``costs`` never writes in the transcript folder."""
        self.report()
        self.assertEqual(tree_state(self.folder.root), self.files_before)

    def test_description_starts_with_cost_heading(self):
        """Design 8.8 and note 5: ``description`` is the section ``## Cost``."""
        self.assertTrue(self.report()["description"].startswith("## Cost"),
                        self.report()["description"][:200])

    def test_description_table_header(self):
        """Note 5: the table's header is ``| Who | Runs | Model | Cost |``."""
        lines = [line.strip() for line in self.report()["description"].splitlines()]
        self.assertIn(HEADER, lines)

    def test_description_rows_in_order(self):
        """Note 5: a row per role, then the helpers, the other agents, the main session, and
        the total."""
        who = [row[0] for row in table_rows(self.report()["description"])]
        self.assertEqual(who, ["Interface Designer", "Test Manager", "Developer", "Code Reviewer",
                               HELPERS_ROW, OTHERS_ROW, MAIN_ROW, "Total"])

    def test_description_role_rows(self):
        """Note 5: each role row's runs, model by family and version, and cost."""
        rows = {row[0]: row for row in table_rows(self.report()["description"])}
        self.assertEqual(rows.get("Developer"), ["Developer", "2", "Opus 5.5", "$7.00"])
        self.assertEqual(rows.get("Code Reviewer"), ["Code Reviewer", "1", "Sonnet 5.5", "$0.50"])

    def test_description_group_rows(self):
        """Note 5: the helpers', other agents', main session's, and total's figures."""
        rows = {row[0]: row for row in table_rows(self.report()["description"])}
        self.assertEqual(rows.get(HELPERS_ROW), [HELPERS_ROW, "2", "Opus 5.5", "$1.75"])
        self.assertEqual(rows.get(OTHERS_ROW), [OTHERS_ROW, "2", "Opus 5.5", "$1.00"])
        self.assertEqual(rows[MAIN_ROW][-1], "$3.50")
        self.assertIn("Opus 5.5", rows[MAIN_ROW][2])
        self.assertEqual(rows["Total"][-1], "$16.75")

    def test_description_notes_as_lines(self):
        """Design 8.8: a ``- `` line per note after the table."""
        report = self.report()
        lines = report["description"].splitlines()
        self.assertNotEqual(report["notes"], [])
        for note in report["notes"]:
            with self.subTest(note=note):
                self.assertIn(f"- {note}", lines)

    def test_description_and_line_hold_no_claude(self):
        """Planted bug "a model ID in the description" (R19): neither ``description`` nor
        ``line`` holds "claude" in any case, a backslash, or the transcript folder's name."""
        report = self.report()
        for key in ("description", "line"):
            with self.subTest(key=key):
                self.assertNotIn("claude", report[key].lower())
                self.assertNotIn("\\", report[key])
                self.assertNotIn(self.folder.root.name, report[key])

    def test_line_holds_the_figures(self):
        """Note 5: ``line`` is one sentence with the item, the total, the 5 role runs, and the
        main session's cost."""
        line = self.report()["line"]
        self.assertNotIn("\n", line.strip())
        self.assertIn("F01", line)
        self.assertIn("$16.75", line)
        self.assertIn("$3.50", line)
        self.assertRegex(line, r"(?<![\d.,$])5(?![\d.,])")


# ------------------------------------------------------------ description

SESSION_D = "5e55dddd-0000-4000-8000-0000000000d1"


class DescriptionTests(CostsCase):
    """The description's money format (note 5): a thousands separator and two decimals."""

    @classmethod
    def setUpClass(cls):
        """A Developer run of $1,234.56 and an Interface Designer run of $9.10; no others."""
        cls.project = Project(PRICING_STEPS)
        folder = Transcripts()
        folder.session(SESSION_D, user(T0, "Build F01."), assistant(T0 + 1, tokens()))
        folder.role_run(SESSION_D, "aif00301", IF, T0 + 10, "F01", F01.title(1), 910)
        folder.role_run(SESSION_D, "adv00301", DV, T0 + 100, "F01", F01.title(3), 123456,
                        task="DV1")
        cls.out = run_costs(cls.project, "--item", "F01", transcripts=[folder.root])

    def rows(self) -> dict:
        """The table's rows by their first cell."""
        report = self.costs_report(self.out)
        return {row[0]: row for row in table_rows(report["description"])}

    def test_thousands_separator(self):
        """Note 5: costs written like ``$1,092.03``."""
        self.assertEqual(self.rows()["Developer"][-1], "$1,234.56")

    def test_two_decimals(self):
        """Note 5: costs written like ``$9.10``."""
        self.assertEqual(self.rows()["Interface Designer"][-1], "$9.10")

    def test_total_row(self):
        """Note 5: the total, $1,243.66, in the table and in ``line``."""
        self.assertEqual(self.rows()["Total"][-1], "$1,243.66")
        self.assertIn("$1,243.66", self.costs_report(self.out)["line"])

    def test_no_other_agents_row_without_others(self):
        """Design 8.8: the other agents' row only when there are any."""
        self.assertNotIn(OTHERS_ROW, self.rows())


# --------------------------------------------------------- accept window

ACCEPT_STEPS = [base_step(base_files(TWO))] + stages(F01, 6) + [stage_step(F02, 1)]
SQUASH_STEPS = ([base_step(base_files(TWO))] + stages(F01, 5)
                + [stage_step(F01, 6, style="squash", pr=46), stage_step(F02, 1)])
SESSION_A = "5e55aaaa-0000-4000-8000-0000000000a2"


def accept_folder(accept: float) -> Transcripts:
    """F01's Interface Designer ($1) and the main session around the accept time ``accept``.

    Main: $2 before the accept commit and $40 after it. Other agents: $0.50
    before it, $16 after it.
    """
    folder = Transcripts()
    folder.session(SESSION_A, user(accept - 3000, "Start F01."), spend(accept - 2000, 200),
                   spend(accept + 600, 4000))
    folder.role_run(SESSION_A, "aif00101", IF, accept - 2900, "F01", F01.title(1), 100)
    folder.plain_agent(SESSION_A, "aoth0101", "general-purpose", accept - 1000, 50)
    folder.plain_agent(SESSION_A, "aoth0102", "general-purpose", accept + 700, 1600)
    return folder


class AcceptWindowTests(CostsCase):
    """``--item``'s end: the ``accept`` commit's committer time on origin/main, or
    ``--until`` (design 8.8, note 4)."""

    @classmethod
    def setUpClass(cls):
        """A rebase-merged and a squash-merged acceptance, and ``--until`` on the first."""
        cls.project = Project(ACCEPT_STEPS)
        cls.squash = Project(SQUASH_STEPS)
        cls.accept = commit_time(cls.project, subject_commits(cls.project)[F01.title(6)])
        cls.squash_accept = commit_time(cls.squash,
                                        subject_commits(cls.squash)[F01.title(6) + " (#46)"])
        rebase_folder = accept_folder(cls.accept)
        squash_folder = accept_folder(cls.squash_accept)
        cls.until = cls.accept - 1500
        runs = [(cls.project, rebase_folder, ()), (cls.squash, squash_folder, ()),
                (cls.project, rebase_folder, ("--until", iso(cls.until).replace(".000", "")))]
        cls.out, cls.squash_out, cls.until_out = parallel(
            lambda r: run_costs(r[0], "--item", "F01", *r[2], transcripts=[r[1].root]), runs)

    def test_window_ends_at_accept_commit(self):
        """Design 8.8: the window runs from the first run to the ``[F01 6/6 accept]`` commit's
        committer time, not origin/main's newest commit."""
        window = self.costs_report(self.out)["window"]
        self.assert_time(window["from"], self.accept - 2900)
        self.assert_time(window["to"], self.accept)

    def test_window_ends_at_squashed_accept_commit(self):
        """Note 4: the accept commit's subject may end with `` (#46)``."""
        window = self.costs_report(self.squash_out)["window"]
        self.assert_time(window["to"], self.squash_accept)

    def test_main_messages_after_accept_left_out(self):
        """Planted bug "main-session messages after the end counted": $2, not $42."""
        report = self.costs_report(self.out)
        self.assert_money(report["main"]["cost"], 2.00)
        self.assert_money(report["total"], 3.50)

    def test_other_agents_after_accept_left_out(self):
        """Design 8.8: an other agent that starts after the end is left out."""
        self.assertEqual(self.group(self.costs_report(self.out), "others"),
                         (1, ["Opus 5.5"], 0.50))

    def test_missing_names_stages_one_to_five_only(self):
        """Note 5: stages 2 to 5 merged with no run are missing; stage 6, the main session's
        own, never is."""
        self.assertEqual(self.costs_report(self.out)["missing"],
                         [F01.title(n) for n in (2, 3, 4, 5)])

    def test_until_ends_the_window(self):
        """Design 8.8 and note 4: ``--until`` ends the window: the other agent after it is
        left out."""
        report = self.costs_report(self.until_out)
        self.assert_time(report["window"]["to"], self.until)
        self.assertEqual(report["others"]["runs"], 0)
        self.assert_money(report["main"]["cost"], 2.00)
        self.assert_money(report["total"], 3.00)


# ---------------------------------------------------------------- versions

F02V2 = replace(F02, version="v0.2")
F03V2 = replace(F03, version="v0.2")
F04V3 = replace(F04, version="v0.3")
TAG_STEPS = ([base_step(base_files((F01, F02V2, F03V2, F04V3)))] + stages(F01, 6)
             + [version_tests_step("v0.1"), release_step("v0.1.0"),
                bug_step("B4", "test", "Wrong count"), bug_step("B4", "fix", "Wrong count"),
                release_step("v0.1.1", pr=14, tags=["v0.1.0", "v0.1.1"])]
             + stages(F02V2, 6) + stages(F03V2, 6)
             + [version_tests_step("v0.2"),
                release_step("v0.2.0", tags=["v0.1.0", "v0.1.1", "v0.2.0"]),
                stage_step(F04V3, 1)])
ST1 = "5e55a001-0000-4000-8000-0000000000b1"
ST2 = "5e55a002-0000-4000-8000-0000000000b2"


def tag_folder(r1: float, r2: float, r3: float) -> Transcripts:
    """Runs around the release commits of v0.1.0 (r1), v0.1.1 (r2), and v0.2.0 (r3).

    Before r1: the earliest record (r1 - 100), main $1, F01's Interface
    Designer $2. Between r1 and r2: B4's Developer $4, main $0.50. Between r2
    and r3: main $1.50, F02's Interface Designer $1 and Developer $2 with a
    helper $0.50, the v0.2 tests' Test Engineer $3, an other agent $0.25. After
    r3: main $8, F04's Interface Designer $16.
    """
    folder = Transcripts()
    folder.session(ST1, user(r1 - 100, "Release v0.1."), spend(r1 - 90, 100), spend(r1 + 40, 50))
    folder.role_run(ST1, "aif00201", IF, r1 - 80, "F01", F01.title(1), 200)
    folder.role_run(ST1, "adv00201", DV, r1 + 30, "B4", bug_title("B4", "fix", "Wrong count"),
                    400, task="DV3")
    folder.session(ST2, user(r2 + 20, "Start v0.2."), spend(r2 + 30, 150), spend(r3 + 30, 800))
    folder.role_run(ST2, "aif00202", IF, r2 + 60, "F02", F02V2.title(1), 100)
    folder.role_run(ST2, "adv00202", DV, r2 + 120, "F02", F02V2.title(3), 200, task="DV1")
    folder.plain_agent(ST2, "ahlp0201", "general-purpose", r2 + 130, 50, parent="adv00202")
    folder.role_run(ST2, "ate00201", "tstack:troy-test-engineer", r2 + 300, "v0.2",
                    tests_title("v0.2"), 300, task="TE5")
    folder.plain_agent(ST2, "aoth0201", "general-purpose", r2 + 400, 25)
    folder.role_run(ST2, "aif00203", IF, r3 + 60, "F04", F04V3.title(1), 1600)
    return folder


class TagTests(CostsCase):
    """``--tag`` (design 8.8 "A version", F08 design 5.7 and 11.1 row "Cost", note 4)."""

    @classmethod
    def setUpClass(cls):
        """v0.2.0, the patch v0.1.1, v0.1.0, the unreleased v0.3.0, and v0.3.0 with --until."""
        cls.project = Project(TAG_STEPS)
        shas = subject_commits(cls.project)
        cls.r1 = commit_time(cls.project, shas["[docs] Release v0.1.0"])
        cls.r2 = commit_time(cls.project, shas["[docs] Release v0.1.1 (#14)"])
        cls.r3 = commit_time(cls.project, shas["[docs] Release v0.2.0"])
        folder = tag_folder(cls.r1, cls.r2, cls.r3)
        cls.until = cls.r3 + 45
        cases = {"v0.2.0": ("--tag", "v0.2.0"), "v0.1.1": ("--tag", "v0.1.1"),
                 "v0.1.0": ("--tag", "v0.1.0"), "v0.3.0": ("--tag", "v0.3.0"),
                 "until": ("--tag", "v0.3.0", "--until", iso(cls.until).replace(".000", ""))}
        names = list(cases)
        cls.started = time.time()
        outs = parallel(lambda n: run_costs(cls.project, *cases[n], transcripts=[folder.root]),
                        names)
        cls.finished = time.time()
        cls.outs = dict(zip(names, outs))

    def report(self, name: str) -> dict:
        """One case's report."""
        return self.costs_report(self.outs[name])

    def items(self, name: str) -> dict:
        """One case's ``items``, rounded to cents."""
        return {key: round(float(value), 2) for key, value in self.report(name)["items"].items()}

    def test_version_counts_from_the_patch_release(self):
        """F08 planted bug "counted from the previous version's tag instead of the previous
        release commit of any tag": v0.2.0 starts at v0.1.1's release commit, so B4's run
        stays out."""
        report = self.report("v0.2.0")
        self.assert_time(report["window"]["from"], self.r2)
        self.assertEqual(set(report["items"]), {"F02", "v0.2"})

    def test_version_ends_at_its_release_commit(self):
        """Design 8.8: to the tag's release commit once merged: the main message and F04's run
        after it are left out."""
        report = self.report("v0.2.0")
        self.assert_time(report["window"]["to"], self.r3)
        self.assert_money(report["main"]["cost"], 1.50)

    def test_version_counts_every_run_in_the_window(self):
        """Design 8.8: every role run, helper, and other agent that started in the window:
        8.25 in all."""
        report = self.report("v0.2.0")
        self.assertEqual(self.role_rows(report), [("Interface Designer", 1, ["Opus 5.5"], 1.00),
                                                  ("Developer", 1, ["Opus 5.5"], 2.00),
                                                  ("Test Engineer", 1, ["Opus 5.5"], 3.00)])
        self.assertEqual(self.group(report, "helpers"), (1, ["Opus 5.5"], 0.50))
        self.assertEqual(self.group(report, "others"), (1, ["Opus 5.5"], 0.25))
        self.assert_money(report["total"], 8.25)

    def test_items_by_item_with_helpers(self):
        """Note 5: ``items`` gives each item's role-run cost, helpers included."""
        self.assertEqual(self.items("v0.2.0"), {"F02": 3.50, "v0.2": 3.00})

    def test_missing_names_feature_without_run(self):
        """D264: a feature of the version with no role run, F03, is named in ``missing``."""
        missing = self.report("v0.2.0")["missing"]
        self.assertEqual(len(missing), 1, missing)
        self.assertIn("F03", missing[0])

    def test_patch_counts_from_the_previous_release(self):
        """F08 11.1: a patch counts from the previous release commit to its own."""
        report = self.report("v0.1.1")
        self.assert_time(report["window"]["from"], self.r1)
        self.assert_time(report["window"]["to"], self.r2)
        self.assertEqual(self.items("v0.1.1"), {"B4": 4.00})
        self.assert_money(report["total"], 4.50)

    def test_patch_names_no_missing_feature(self):
        """Note 5: ``missing`` names features only for a version, not a patch."""
        self.assertEqual(self.report("v0.1.1")["missing"], [])

    def test_first_version_from_the_first_record(self):
        """Design 8.8: with no earlier release commit, from the earliest transcript record."""
        report = self.report("v0.1.0")
        self.assert_time(report["window"]["from"], self.r1 - 100)
        self.assert_time(report["window"]["to"], self.r1)
        self.assertEqual(self.items("v0.1.0"), {"F01": 2.00})
        self.assert_money(report["total"], 3.00)

    def test_unreleased_tag_to_now(self):
        """Design 8.8: before the tag's release commit merges, from the newest release commit
        to the time ``costs`` runs."""
        report = self.report("v0.3.0")
        self.assert_time(report["window"]["from"], self.r3)
        to = seconds_of(report["window"]["to"])
        self.assertGreaterEqual(to, self.started - 5)
        self.assertLessEqual(to, self.finished + 5)
        self.assertEqual(self.items("v0.3.0"), {"F04": 16.00})
        self.assert_money(report["total"], 24.00)

    def test_until_ends_the_tag_window(self):
        """Design 8.8: ``--until`` ends a version's window: F04's run after it is left out."""
        report = self.report("until")
        self.assert_time(report["window"]["to"], self.until)
        self.assertEqual(report["roles"], [])
        self.assert_money(report["total"], 8.00)

    def test_description_items_line(self):
        """Note 5: for ``--tag``, a line ``Role runs by item: ...`` follows the table."""
        lines = self.report("v0.2.0")["description"].splitlines()
        found = [line for line in lines if line.startswith("Role runs by item:")]
        self.assertEqual(len(found), 1, lines)
        self.assertIn("F02 $3.50", found[0])
        self.assertIn("v0.2 $3.00", found[0])


# -------------------------------------------------------------- cost-state

COST_STEPS = [base_step(base_files(TWO))] + stages(F01, 1)
FIRST_ID = "0a0a0a0a-0000-4000-8000-0000000000c1"   # sorts first by name
LAST_ID = "9f9f9f9f-0000-4000-8000-0000000000c2"    # sorts last by name
OLD, NEW = 1600000000, 1700000000
# The test table prices these Opus counts at $19.00 and these Sonnet counts at $5.00.
OPUS_COUNTS = dict(inp=1_000_000, out=1_000_000, read=10_000_000, w5=1_000_000, w1=1_000_000,
                   web=20)


def state(opus_cost: float, sonnet_cost: float) -> dict:
    """A cost-state record with the app's Opus and Sonnet figures for the counts above."""
    return cost_state({OPUS: model_usage(opus_cost, **OPUS_COUNTS),
                       SONNET: model_usage(sonnet_cost, out=1_000_000)})


WITHIN = state(19.10, 5.04)          # 0.5% and 0.8%
BEYOND = state(19.10, 5.50)          # Sonnet 10% off
BEYOND_OPUS = state(19.50, 5.04)     # Opus 2.6% off


def cost_folder(sessions: Sequence[tuple]) -> Transcripts:
    """Session files ``(ID, cost-state records, mtime)``, the first with F01's run."""
    folder = Transcripts()
    for n, (sid, records, _mtime) in enumerate(sessions):
        start = BASE_TIME + 1000 * n
        folder.session(sid, user(start, "Go on."), spend(start + 30, 100), *records)
        if n == 0:
            folder.role_run(sid, "aif00401", IF, BASE_TIME + 20, "F01", F01.title(1), 100)
    for sid, _records, mtime in sessions:
        os.utime(folder.root / f"{sid}.jsonl", (mtime, mtime))
    return folder


class CostStateTests(CostsCase):
    """The desktop app's own figure checks the prices (D266, note 5)."""

    CASES = {
        "control": [(FIRST_ID, [], OLD)],
        "beyond": [(FIRST_ID, [BEYOND], OLD)],
        "within": [(FIRST_ID, [WITHIN], OLD)],
        "two control": [(FIRST_ID, [], NEW), (LAST_ID, [], OLD)],
        "newest": [(FIRST_ID, [BEYOND_OPUS, WITHIN], NEW), (LAST_ID, [BEYOND], OLD)],
        "newest last": [(FIRST_ID, [BEYOND], OLD), (LAST_ID, [WITHIN], NEW)],
    }

    @classmethod
    def setUpClass(cls):
        """One folder and run per case, side by side."""
        cls.project = Project(COST_STEPS)
        names = list(cls.CASES)
        folders = {name: cost_folder(cls.CASES[name]) for name in names}
        outs = parallel(lambda n: run_costs(cls.project, "--item", "F01",
                                            transcripts=[folders[n].root]), names)
        cls.outs = dict(zip(names, outs))

    def notes(self, name: str) -> list:
        """One case's notes."""
        return self.costs_report(self.outs[name])["notes"]

    def price_notes(self, name: str, control: str) -> list:
        """The notes of a case that its control, the same files without cost-state, lacks."""
        return [note for note in self.notes(name) if note not in self.notes(control)]

    def test_note_when_a_model_differs_by_more_than_one_percent(self):
        """D266: Sonnet's figure is 10% off the table's price of its counts: one note, naming
        Sonnet 5.5 and not Opus 5.5 (0.5% off), with no model ID."""
        added = self.price_notes("beyond", "control")
        self.assertEqual(len(added), 1, self.notes("beyond"))
        self.assertIn("Sonnet 5.5", added[0])
        self.assertNotIn("Opus 5.5", added[0])
        self.assertNotIn("claude", added[0].lower())

    def test_price_note_in_description(self):
        """Design 8.8: the price note is a ``- `` line of the description."""
        added = self.price_notes("beyond", "control")
        self.assertEqual(len(added), 1, self.notes("beyond"))
        description = self.costs_report(self.outs["beyond"])["description"]
        self.assertIn(f"- {added[0]}", description.splitlines())

    def test_no_note_within_one_percent(self):
        """Planted bug "the price note given at any difference": 0.5% and 0.8% give none."""
        self.assertEqual(self.notes("within"), self.notes("control"))

    def test_last_record_of_the_newest_file(self):
        """Note 5: only the last cost-state record of the most recently modified session file
        counts: an earlier record there and an older file's record give no note."""
        self.assertEqual(self.notes("newest"), self.notes("two control"))

    def test_newest_file_by_modification_time(self):
        """Note 5: the newest file is told by its modification time, not its name."""
        self.assertEqual(self.notes("newest last"), self.notes("two control"))


# ------------------------------------------------------------- discovery

def stages_steps() -> list:
    """A project with F01's first two stages merged."""
    return [base_step(base_files(TWO))] + stages(F01, 2)


def slug_of(path_text: str) -> str:
    """A transcript folder's name: every character but an ASCII letter or digit made ``-``."""
    return re.sub(r"[^A-Za-z0-9]", "-", path_text)


def worktree_paths(project: Project) -> list:
    """The paths ``git worktree list --porcelain`` prints, the main checkout first."""
    out = project.git("worktree", "list", "--porcelain")
    return [line[len("worktree "):] for line in out.splitlines() if line.startswith("worktree ")]


def one_run_folder(root: Path, sid: str, aid: str, agent_type: str, start: float,
                   cents: int) -> Transcripts:
    """A folder with one session and one F01 role run."""
    folder = Transcripts(root)
    folder.session(sid, user(start - 10, "Go on."), assistant(start - 5, tokens()))
    folder.role_run(sid, aid, agent_type, start, "F01", F01.title(1), cents)
    return folder


class DiscoveryTests(CostsCase):
    """Where the transcripts are (D264, note 1)."""

    @classmethod
    def setUpClass(cls):
        """A clone with a ``git worktree add`` worktree, a config folder, a home folder, and
        two folders for ``--transcripts``."""
        cls.project = Project(stages_steps())
        cls.project.git("worktree", "add", "-q", "-b", "troy-mode/wt",
                        str(cls.project.tmp / "wordcount-wt"), "origin/main")
        main_path, wt_path = worktree_paths(cls.project)[:2]
        main_slug = slug_of(main_path)
        cls.config = new_dir("config")
        projects = cls.config / "projects"
        one_run_folder(projects / main_slug, "5e55e001-0000-4000-8000-000000000001", "aif00501",
                       IF, T0, 100)
        one_run_folder(projects / slug_of(wt_path), "5e55e002-0000-4000-8000-000000000002",
                       "atm00501", "tstack:troy-test-manager", T0 + 100, 200)
        one_run_folder(projects / f"{main_slug}--claude-worktrees-agent-x",
                       "5e55e003-0000-4000-8000-000000000003", "adv00501", DV, T0 + 200, 400)
        one_run_folder(projects / f"{main_slug}-old", "5e55e004-0000-4000-8000-000000000004",
                       "acr00501", "tstack:troy-code-reviewer", T0 + 300, 800)
        one_run_folder(projects / f"{main_slug}2--claude-worktrees-y",
                       "5e55e005-0000-4000-8000-000000000005", "ate00501",
                       "tstack:troy-test-engineer", T0 + 400, 1600)
        cls.home = new_dir("home")
        one_run_folder(cls.home / ".claude/projects" / main_slug,
                       "5e55e006-0000-4000-8000-000000000006", "aar00501", "tstack:troy-architect",
                       T0 + 500, 3200)
        named = [one_run_folder(new_dir("named"), "5e55e007-0000-4000-8000-000000000007",
                                "acr00502", "tstack:troy-code-reviewer", T0 + 600, 50),
                 one_run_folder(new_dir("named"), "5e55e008-0000-4000-8000-000000000008",
                                "ate00502", "tstack:troy-test-engineer", T0 + 700, 25)]
        home_env = {"CLAUDE_CONFIG_DIR": "", "USERPROFILE": str(cls.home), "HOME": str(cls.home)}
        runs = [{"config_dir": cls.config},
                {"env": home_env},
                {"config_dir": cls.config, "transcripts": [f.root for f in named]}]
        cls.config_out, cls.home_out, cls.named_out = parallel(
            lambda kw: run_costs(cls.project, "--item", "F01", **kw), runs)

    def roles(self, out: Outcome) -> list:
        """The roles of a run's report, in order."""
        return [r["role"] for r in self.costs_report(out)["roles"]]

    def test_main_checkout_folder_read(self):
        """D264: the main checkout's folder under ``$CLAUDE_CONFIG_DIR/projects``."""
        self.assertIn("Interface Designer", self.roles(self.config_out))

    def test_git_worktree_folder_read(self):
        """Planted bug "a worktree's folder not read": a ``git worktree list`` worktree's."""
        self.assertIn("Test Manager", self.roles(self.config_out))

    def test_desktop_worktree_folder_read(self):
        """D264: a ``<main>--claude-worktrees-<name>`` folder, whose worktree is gone."""
        self.assertIn("Developer", self.roles(self.config_out))

    def test_sibling_folders_not_read(self):
        """Note 1: ``<main>-old`` and ``<main>2--claude-worktrees-y`` belong to no checkout
        of this project."""
        report = self.costs_report(self.config_out)
        self.assertEqual(self.roles(self.config_out),
                         ["Interface Designer", "Test Manager", "Developer"])
        self.assert_money(report["total"], 7.00)

    def test_home_folder_without_config_dir(self):
        """D264: with ``CLAUDE_CONFIG_DIR`` empty, ``.claude/projects`` in the home folder."""
        self.assertEqual(self.role_rows(self.costs_report(self.home_out)),
                         [("Architect", 1, ["Opus 5.5"], 32.00)])

    def test_transcripts_option_reads_only_named_folders(self):
        """D264: ``--transcripts``, given twice, names the folders to read instead."""
        report = self.costs_report(self.named_out)
        self.assertEqual(self.roles(self.named_out), ["Test Engineer", "Code Reviewer"])
        self.assert_money(report["total"], 0.75)


class NoTranscriptTests(CostsCase):
    """No transcript of the project on this PC (design 8.8 "The report", note 1 and 5)."""

    @classmethod
    def setUpClass(cls):
        """A config folder with an empty ``projects`` folder."""
        cls.project = Project(stages_steps())
        cls.out = run_costs(cls.project, "--item", "F01", config_dir=EMPTY_CONFIG)

    def test_exit_zero(self):
        """Design 8.8: ``costs`` exits 0 with no transcript found."""
        self.costs_report(self.out)

    def test_section_says_not_measured(self):
        """Note 5: ``## Cost`` and the sentence "Not measured: ..."."""
        description = self.costs_report(self.out)["description"]
        self.assertTrue(description.startswith("## Cost"), description)
        self.assertIn(NOT_MEASURED, description)


class RefusalTests(CostsCase):
    """Exit 2 when the command line is wrong (design 3.1, note 1); each test also checks the
    control run, ``--item F01`` alone, which exits 0."""

    @classmethod
    def setUpClass(cls):
        """Every case side by side on one clone and one folder."""
        cls.project = Project(stages_steps())
        folder = one_run_folder(new_dir("transcripts"), "5e55f001-0000-4000-8000-000000000001",
                                "aif00601", IF, T0, 100)
        cases = {"control": ("--item", "F01"), "both": ("--item", "F01", "--tag", "v0.1.0"),
                 "neither": (), "bad tag": ("--tag", "v0.1"),
                 "bad until": ("--item", "F01", "--until", "yesterday")}
        names = list(cases)
        outs = parallel(lambda n: run_costs(cls.project, *cases[n], transcripts=[folder.root]),
                        names)
        cls.outs = dict(zip(names, outs))

    def assert_refused(self, name: str) -> None:
        """The control exits 0 and the case exits 2."""
        self.costs_report(self.outs["control"])
        self.assert_exit(self.outs[name], 2)

    def test_item_and_tag_together(self):
        """Note 1: ``--item`` and ``--tag`` together: exit 2."""
        self.assert_refused("both")

    def test_neither_item_nor_tag(self):
        """Note 1: neither ``--item`` nor ``--tag``: exit 2."""
        self.assert_refused("neither")

    def test_tag_without_patch_number(self):
        """Note 1: a ``--tag`` not of the form vMAJOR.MINOR.PATCH: exit 2."""
        self.assert_refused("bad tag")

    def test_bad_until(self):
        """Note 1: an ``--until`` that is not an ISO 8601 time: exit 2."""
        self.assert_refused("bad until")


# ----------------------------------------------------------- price table

class PriceTableTests(unittest.TestCase):
    """The plugin's price table, ``troy-mode/flow/prices.toml`` (D265, note 3)."""

    @classmethod
    def setUpClass(cls):
        """Reads the table once; empty when it does not exist yet."""
        cls.table = tomllib.loads(PRICES_FILE.read_text("utf-8")) if PRICES_FILE.is_file() else {}

    def model(self, model_id: str) -> dict:
        """One model's table, which must exist."""
        models = self.table.get("models", {})
        self.assertIn(model_id, models, sorted(models))
        return models[model_id]

    def assert_prices(self, model_id: str, values: Sequence[float]) -> None:
        """The model's five prices, in the order of ``FIVE_KEYS``."""
        table = self.model(model_id)
        for key, value in zip(FIVE_KEYS, values):
            with self.subTest(model=model_id, key=key):
                self.assertAlmostEqual(float(table.get(key, -1)), value, places=6)

    def test_opus_5_5(self):
        """D265: Opus 5.5 at 4 / 20 / 0.20 / 5 / 8 dollars per million tokens."""
        self.assert_prices("claude-opus-5-5", (4.00, 20.00, 0.20, 5.00, 8.00))

    def test_sonnet_5_5(self):
        """D265: Sonnet 5.5 at 2 / 10 / 0.10 / 2.5 / 4."""
        self.assert_prices("claude-sonnet-5-5", (2.00, 10.00, 0.10, 2.50, 4.00))

    def test_haiku_5_5(self):
        """D265: Haiku 5.5 at 0.10 / 0.50 / 0.01 / 0.125 / 0.20."""
        self.assert_prices("claude-haiku-5-5", (0.10, 0.50, 0.01, 0.125, 0.20))

    def test_web_search(self):
        """D265: a web search at $0.01."""
        self.assertAlmostEqual(float(self.table.get("web_search", -1)), 0.01, places=6)

    def test_as_of_is_a_date(self):
        """D265: ``as_of`` is the date the prices were read."""
        self.assertRegex(str(self.table.get("as_of", "")), r"^\d{4}-\d{2}-\d{2}$")

    def test_every_model_has_five_keys(self):
        """D265: every model table, and every ``fast`` table, has the five prices."""
        models = self.table.get("models", {})
        self.assertNotEqual(models, {})
        for model_id, table in models.items():
            for name, part in ((model_id, table), (f"{model_id}.fast", table.get("fast"))):
                if part is None:
                    continue
                with self.subTest(table=name):
                    for key in FIVE_KEYS:
                        self.assertIsInstance(part.get(key), (int, float), key)

    def test_opus_5_5_has_a_fast_table(self):
        """D265 and note 3: Opus 5.5 has a ``fast`` table."""
        self.assertIsInstance(self.model("claude-opus-5-5").get("fast"), dict)


# ------------------------------------------------------------------ skill

def skill_section(text: str, heading: str) -> str:
    """The text under a heading up to the next heading of the same or a higher level."""
    lines = text.replace("\r\n", "\n").split("\n")
    level = len(heading) - len(heading.lstrip("#"))
    if heading not in lines:
        return ""
    start = lines.index(heading) + 1
    end = len(lines)
    for index in range(start, len(lines)):
        mark = re.match(r"^(#+) ", lines[index])
        if mark and len(mark.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end])


class CostSkillTests(unittest.TestCase):
    """The skill runs ``costs`` (F07 design 8.8 "PR 6", F08 design 5.7, note 6)."""

    @classmethod
    def setUpClass(cls):
        """Reads SKILL.md once; an empty text when it does not exist."""
        cls.text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""

    def test_pr6_runs_costs_item(self):
        """Design 8.8 "PR 6": the section "PR 6: the real run" names ``costs --item`` and the
        ``## Cost`` section."""
        section = skill_section(self.text, "### PR 6: the real run")
        self.assertNotEqual(section, "", "no section PR 6: the real run")
        self.assertTrue("costs --item" in section, "PR 6 does not name costs --item")
        self.assertTrue("## Cost" in section, "PR 6 does not name the ## Cost section")

    def test_version_release_runs_costs_tag(self):
        """F08 design 5.7 step 3: the section "Version release" names ``costs --tag`` and the
        ``## Cost`` section."""
        section = skill_section(self.text, "## Version release")
        self.assertNotEqual(section, "", "no section Version release")
        self.assertTrue("costs --tag" in section, "Version release does not name costs --tag")
        self.assertTrue("## Cost" in section, "Version release does not name ## Cost")

    def test_engine_table_lists_costs(self):
        """Note 6: the engine table lists ``troy_flow.py costs``."""
        section = skill_section(self.text, "## The engine")
        self.assertTrue("troy_flow.py costs" in section, "the engine table does not list costs")


if __name__ == "__main__":
    unittest.main()
