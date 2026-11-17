"""What the CLI writes: the role's transcript and the session's stream-json (design 11.3, probes A and A2)."""

import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import AGENT_PREFIX
from .errors import ExamError

HANDBACK = "SubagentHandback"
_MESSAGE_TYPES = ("user", "assistant")


def config_dir(env: Mapping[str, str]) -> Path:
    """The CLI's configuration folder: $CLAUDE_CONFIG_DIR, else ~/.claude."""
    folder = env.get("CLAUDE_CONFIG_DIR")
    return Path(folder) if folder else Path.home() / ".claude"


def folder_key(path: str) -> str:
    """The CLI's folder name for a project: every character but an ASCII letter or digit becomes "-"."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def session_dir(env: Mapping[str, str], project: Path, session_id: str) -> Path:
    """<config dir>/projects/<folder key>/<session ID>, found by the session ID, never by a search."""
    return config_dir(env) / "projects" / folder_key(str(project)) / session_id


@dataclass
class ToolCall:
    """One tool call of the role.

    Attributes:
        name: The tool, such as "Bash" or "Read".
        input: The tool's input.
        denied: A permission or a hook refused the call.
    """

    name: str
    input: dict
    denied: bool = False


@dataclass
class RoleTranscript:
    """The role's side of a run.

    Attributes:
        first_message: The first message the role got: the brief.
        calls: Its tool calls, in order.
        texts: Its text blocks, in order.
        handback: The SubagentHandback message, or None.
        agent_type: The agent type from the .meta.json.
        model: The model from the .meta.json.
        events: ("call", i) and ("text", j) in transcript order.
    """

    first_message: str
    calls: list[ToolCall] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    handback: str | None = None
    agent_type: str | None = None
    model: str | None = None
    events: list[tuple[str, int]] = field(default_factory=list)


def _content_text(content) -> str:
    """The text of a message's content: a string, or its text blocks joined."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content
                       if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _result_text(block: dict) -> str:
    """The text of a tool_result block."""
    content = block.get("content")
    if isinstance(content, list):
        return " ".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return str(content or "")


def parse_role(lines: Iterable[str], meta: dict | None) -> RoleTranscript:
    """Reads a role's transcript lines; only user and assistant messages count."""
    result = RoleTranscript(first_message="")
    by_id: dict[str, int] = {}
    first_seen = False
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("type") not in _MESSAGE_TYPES \
                or entry.get("isMeta"):
            continue
        message = entry.get("message") or {}
        content = message.get("content")
        if entry["type"] == "user" and not first_seen:
            first_seen = True
            result.first_message = _content_text(content)
            continue
        if not isinstance(content, list):
            if entry["type"] == "assistant" and isinstance(content, str) and content:
                result.events.append(("text", len(result.texts)))
                result.texts.append(content)
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if entry["type"] == "assistant" and kind == "text" and block.get("text"):
                result.events.append(("text", len(result.texts)))
                result.texts.append(block["text"])
            elif entry["type"] == "assistant" and kind == "tool_use":
                call = ToolCall(str(block.get("name", "")), dict(block.get("input") or {}))
                by_id[str(block.get("id"))] = len(result.calls)
                result.events.append(("call", len(result.calls)))
                result.calls.append(call)
                if call.name == HANDBACK:
                    result.handback = str(call.input.get("message", ""))
            elif entry["type"] == "user" and kind == "tool_result":
                index = by_id.get(str(block.get("tool_use_id")))
                text = _result_text(block)
                refused = bool(entry.get("toolDenialKind")) or (
                    bool(block.get("is_error")) and "denied" in text.lower())
                if index is not None and refused:
                    result.calls[index].denied = True
    meta = meta or {}
    result.agent_type, result.model = meta.get("agentType"), meta.get("model")
    return result


def _read_meta(path: Path) -> dict:
    """Reads an agent's .meta.json; {} when it is missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def read_role(subagents: Path, agent_type: str | None = None) -> RoleTranscript:
    """Reads the role's transcript under <session>/subagents.

    Args:
        subagents: The folder.
        agent_type: The role's agent type, to pick it when helpers left transcripts too.

    Raises:
        ExamError: No transcript, or none of the role.
    """
    files = sorted(Path(subagents).glob("agent-*.jsonl")) if Path(subagents).is_dir() else []
    if not files:
        raise ExamError(f"no role transcript in {subagents}")
    metas = {f: _read_meta(f.with_suffix(".meta.json")) for f in files}
    chosen = files[0] if len(files) == 1 else None
    for f in files:
        kind = metas[f].get("agentType") or ""
        if (agent_type and kind == agent_type) or (not agent_type and kind.startswith(AGENT_PREFIX)):
            chosen = f
            break
    if chosen is None:
        raise ExamError(f"no transcript of {agent_type or 'a role'} in {subagents}")
    with open(chosen, encoding="utf-8", errors="replace") as handle:
        return parse_role(handle, metas[chosen])


def role_report(transcript: RoleTranscript) -> str | None:
    """The role's report: its SubagentHandback message, else its last text, else None."""
    if transcript.handback:
        return transcript.handback
    return transcript.texts[-1] if transcript.texts else None


@dataclass
class StreamResult:
    """The session's last result event.

    Attributes:
        found: A result event was read.
        total_cost: total_cost_usd.
        costs: The cost of each model ID, from modelUsage.
        is_error: is_error.
        subtype: subtype, such as "success" or "error_max_budget_usd".
        text: The result's text.
        session_id: The session ID.
        limit_hit: The session stopped at a usage limit.
        cap_hit: The session stopped at --max-budget-usd.
    """

    found: bool = False
    total_cost: float = 0.0
    costs: dict = field(default_factory=dict)
    is_error: bool = False
    subtype: str | None = None
    text: str | None = None
    session_id: str | None = None
    limit_hit: bool = False
    cap_hit: bool = False


def read_stream(lines: Iterable[str]) -> StreamResult:
    """Reads stream-json output: the last result event decides."""
    last = None
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("type") == "result":
            last = entry
    if last is None:
        return StreamResult()
    usage = last.get("modelUsage") or {}
    costs = {model: float((data or {}).get("costUSD") or 0.0) for model, data in usage.items()}
    text = last.get("result") if isinstance(last.get("result"), str) else None
    lowered = (text or "").lower()
    return StreamResult(found=True, total_cost=float(last.get("total_cost_usd") or 0.0),
                        costs=costs, is_error=bool(last.get("is_error")),
                        subtype=last.get("subtype"), text=text, session_id=last.get("session_id"),
                        limit_hit="hit your" in lowered and "limit" in lowered,
                        cap_hit=last.get("subtype") == "error_max_budget_usd")


def projects_key_dir(env: Mapping[str, str], project: Path) -> Path:
    """<config dir>/projects/<folder key>: everything the CLI kept for the project."""
    return config_dir(env) / "projects" / folder_key(str(project))


def same_path(first: str, second: str) -> bool:
    """Compares two paths as the system does, in any slash style or drive form."""
    def norm(path: str) -> str:
        text = path.replace("\\", "/")
        match = re.match(r"^/([A-Za-z])/(.*)$", text)
        if match:
            text = f"{match.group(1)}:/{match.group(2)}"
        text = os.path.normpath(text).replace("\\", "/")
        return text.lower() if os.name == "nt" or re.match(r"^[A-Za-z]:", text) else text
    return norm(first) == norm(second)
