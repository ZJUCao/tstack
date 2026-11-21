"""Role records: the starting state and the work a role leaves running (design 6, 6.1).

A record lives in <git dir>/troy-mode/agents/<agent_id>.json. Besides the
starting snapshot of section 6 it holds the session, when it started, when
the role stopped for good, and the task IDs of the role's commands that
Claude Code moved to the background (D231). F07's engine reads the same
records through is_open and read_all.
"""

import json
import os
import re
import time

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FOLDER = "agents"
STOPPED_TOOLS = ("Bash", "PowerShell", "Edit", "Write", "NotebookEdit", "Skill")
STOPPED_REASON = ("troy-mode: Your run has ended and your report was delivered. Do nothing more, "
                  "and end your turn. (F05 design D232)")


def now() -> str:
    """Returns the current UTC time in the records' format."""
    return time.strftime(TIME_FORMAT, time.gmtime())


def folder(state_dir: str) -> str:
    """Returns <git dir>/troy-mode/agents from <git dir>/troy-mode."""
    return os.path.join(state_dir, FOLDER)


def path_of(state_dir: str, agent_id: str) -> str:
    """Returns the file that holds one role's record."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", agent_id)
    return os.path.join(folder(state_dir), f"{safe}.json")


def read(path: str) -> dict | None:
    """Reads one record, or None when the file does not exist.

    Raises:
        ValueError: The file is not a JSON object.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def save(path: str, record: dict) -> None:
    """Writes a record through a temporary file, so no reader sees half of it.

    Raises:
        OSError: The record cannot be written.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(temp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(record, handle)
        for attempt in range(10):
            try:
                os.replace(temp, path)
                return
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.02)
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def fresh(agent_id: str, agent_type: str | None, session, paths: dict) -> dict:
    """Builds the record of a role that starts now."""
    return {"agent_id": agent_id, "agent_type": agent_type,
            "session": session if isinstance(session, str) else None,
            "started": now(), "stopped": None, "background": [], "paths": paths}


def complete(record: dict, agent_id: str, agent_type: str | None, session) -> dict:
    """Gives an earlier plugin's record the fields of D231, as a record of a running role."""
    record.setdefault("agent_id", agent_id)
    record.setdefault("agent_type", agent_type)
    record.setdefault("session", session if isinstance(session, str) else None)
    record.setdefault("started", now())
    record.setdefault("stopped", None)
    record.setdefault("background", [])
    return record


def is_stopped(record: dict | None) -> bool:
    """Tells whether the role stopped for good (D232). An earlier plugin's record has not."""
    return bool(record) and isinstance(record.get("stopped"), str) and bool(record["stopped"])


def tasks(record: dict) -> list[str]:
    """Returns the record's background task IDs."""
    value = record.get("background")
    return [task for task in value if isinstance(task, str)] if isinstance(value, list) else []


def is_open(record: dict) -> bool:
    """Tells whether a role, or a command it left in the background, may still run.

    A record without the fields of D231, as an earlier plugin wrote it, is closed.
    """
    if not isinstance(record, dict):
        return False
    if "stopped" in record and record["stopped"] is None:
        return True
    return bool(tasks(record))


def agent_of(name: str, record: dict) -> str:
    """Returns a record's agent ID: its agent_id, else its file name."""
    value = record.get("agent_id")
    return value if isinstance(value, str) and value else name[:-len(".json")]


def read_all(state_dir: str) -> list[tuple[str, dict]]:
    """Reads every record in the folder; files that are not JSON objects are left out.

    Returns:
        Pairs of the file's path and its record, sorted by file name.
    """
    base = folder(state_dir)
    try:
        names = sorted(name for name in os.listdir(base) if name.endswith(".json"))
    except FileNotFoundError:
        return []
    found = []
    for name in names:
        full = os.path.join(base, name)
        try:
            record = read(full)
        except (OSError, ValueError):
            continue
        if record is not None:
            found.append((full, record))
    return found


def close(record: dict) -> None:
    """Closes a record: the role stopped, and nothing of it runs any more."""
    if not is_stopped(record):
        record["stopped"] = now()
    record["background"] = []


def running_shells(data: dict) -> set[str]:
    """Returns the IDs of the shell tasks that a stop input lists as running."""
    listed = data.get("background_tasks")
    if not isinstance(listed, list):
        return set()
    return {str(task.get("id")) for task in listed
            if isinstance(task, dict) and task.get("type") == "shell"
            and task.get("status") == "running" and task.get("id")}


def stop_task(state_dir: str, task_id: str) -> None:
    """Applies the main session's TaskStop to the records (design 6.1, step 3).

    An agent ID closes that agent's record. A task ID leaves the background
    of the record that holds it.
    """
    for path, record in read_all(state_dir):
        before = json.dumps(record, sort_keys=True)
        if agent_of(os.path.basename(path), record) == task_id:
            close(record)
        elif task_id in tasks(record):
            record["background"] = [task for task in tasks(record) if task != task_id]
        if json.dumps(record, sort_keys=True) != before:
            save(path, record)


def end_session(state_dir: str, session: str) -> None:
    """Closes the records of the roles of a session that ends (design 6.1, step 4)."""
    for path, record in read_all(state_dir):
        if record.get("session") == session and is_open(record):
            close(record)
            save(path, record)
