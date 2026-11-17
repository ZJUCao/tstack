"""One handler per Claude Code hook event, and the error rule of D39 (design 3, 10)."""

import json
import os
import sys

from .project import HOOKS_PATH, Project, find_project
from .scopes import MAIN, ROLE, caller_of


class Context:
    """One hook call: its input, project, and caller, with facts read once.

    Attributes:
        event: The event name from the command line.
        data: The hook input.
        project: The troy-mode project the call is in.
        caller: Who makes the call.
        tool: The tool name, or None for events without a tool.
        cwd: The real path of the input's cwd.
    """

    def __init__(self, event: str, data: dict, project: Project):
        """Builds the context from the parsed hook input."""
        self.event, self.data, self.project = event, data, project
        self.caller = caller_of(data)
        tool = data.get("tool_name")
        self.tool = tool if isinstance(tool, str) else None
        self.cwd = os.path.realpath(str(data.get("cwd") or os.getcwd()))
        self._cache: dict = {}

    def tool_input(self) -> dict:
        """Returns the tool input, or an empty dict."""
        value = self.data.get("tool_input")
        return value if isinstance(value, dict) else {}

    def _once(self, key: str, load):
        """Computes a fact the first time it is asked for."""
        if key not in self._cache:
            self._cache[key] = load()
        return self._cache[key]

    def config(self):
        """Returns the project config as committed at HEAD."""
        from . import gitstate  # noqa: PLC0415

        return self._once("config", lambda: gitstate.config_at_head(self.project))

    def temp_folders(self) -> list[str]:
        """Returns the folders outside the repository where writes are allowed."""
        from .paths import temp_folders  # noqa: PLC0415

        scratchpad = self.data.get("scratchpad_dir")
        return self._once("temps", lambda: temp_folders(
            str(scratchpad) if scratchpad else None, self.cwd))

    def hooks_off(self) -> str | None:
        """Says why the troy-mode git hooks are off, or None when they are on."""
        return self._once("hooks_off", lambda: hooks_off_reason(self.project))


def hooks_off_reason(project: Project) -> str | None:
    """Says why the troy-mode git hooks are off, or None when they are on (8.1)."""
    from . import gitstate  # noqa: PLC0415

    value = gitstate.hooks_path(project)
    if not gitstate.hooks_on(value):
        state = "unset" if value is None else f"set to {value}"
        return (f"the troy-mode git hooks are off: core.hooksPath is {state}, not {HOOKS_PATH}. "
                "A new session turns them on when core.hooksPath is unset; otherwise ask Troy "
                f"to run `git config core.hooksPath {HOOKS_PATH}`.")
    missing = project.missing_hooks()
    if missing:
        return (f"the troy-mode git hooks are off: {', '.join(missing)} missing from "
                f"{HOOKS_PATH} (core.hooksPath). Restore them with troy-init.")
    return None


def _deny(ctx: Context, refusal) -> dict:
    """Logs a PreToolUse refusal and builds its output."""
    from . import log  # noqa: PLC0415

    log.write(ctx, refusal.rule, "deny", refusal.paths, refusal.subcommand)
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": refusal.reason}}


def _block(ctx: Context, refusal) -> dict:
    """Logs a PostToolUse or SubagentStop block and builds its output."""
    from . import log  # noqa: PLC0415

    log.write(ctx, refusal.rule, "block", refusal.paths, refusal.subcommand)
    return {"decision": "block", "reason": refusal.reason}


def _plugin_read(ctx: Context) -> dict | None:
    """Allows a read inside CLAUDE_PLUGIN_ROOT (design section 9, D45)."""
    from .paths import inside, to_native  # noqa: PLC0415

    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    tool_input = ctx.tool_input()
    raw = tool_input.get("file_path") or tool_input.get("path")
    if not raw and ctx.tool == "Glob":
        raw = _glob_base(str(tool_input.get("pattern") or ""))
    if not root or not raw:
        return None
    if not inside(to_native(str(raw), ctx.cwd), to_native(root, ctx.cwd)):
        return None
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "allow",
        "permissionDecisionReason": "troy-mode: reading the plugin's own files is allowed "
                                    "(F05 D45)."}}


def _glob_base(pattern: str) -> str | None:
    """Gives the folder an absolute Glob pattern starts in, before its first wildcard."""
    import re  # noqa: PLC0415

    if not re.match(r"^(?:/|[A-Za-z]:[/\\])", pattern):
        return None
    parts = re.split(r"[/\\]", pattern)
    fixed = []
    for part in parts:
        if any(char in part for char in "*?[{"):
            break
        fixed.append(part)
    return "/".join(fixed) or "/"


def _pre_check(ctx: Context):
    """Runs the PreToolUse checks for Edit, Write, NotebookEdit, Bash, PowerShell, and Skill."""
    from . import commands  # noqa: PLC0415

    tool_input = ctx.tool_input()
    if ctx.tool in ("Edit", "Write", "NotebookEdit"):
        raw = tool_input.get("file_path") or tool_input.get("notebook_path")
        if ctx.caller.kind == MAIN or not raw:
            return None
        from .writes import check_write  # noqa: PLC0415

        return check_write(ctx, str(raw))
    if ctx.tool in ("Bash", "PowerShell"):
        return commands.check_command(ctx, str(tool_input.get("command") or ""),
                                      ctx.tool == "PowerShell")
    if ctx.tool == "Skill":
        return commands.check_skill(ctx, tool_input)
    return None


def pre_tool_use(ctx: Context) -> dict | None:
    """PreToolUse: plugin reads, write scopes, commands, skills, and guards."""
    if ctx.tool in ("Read", "Glob", "Grep"):
        return _plugin_read(ctx)
    if ctx.caller.kind == ROLE:
        from .changes import ensure_record  # noqa: PLC0415

        ensure_record(ctx.project, ctx.caller)
    refusal = _pre_check(ctx)
    return _deny(ctx, refusal) if refusal else None


def post_tool_use(ctx: Context) -> dict | None:
    """PostToolUse: reports a role's changes outside its scope after a shell or skill call."""
    if ctx.caller.kind != ROLE or ctx.tool not in ("Bash", "PowerShell", "Skill"):
        return None
    from . import changes  # noqa: PLC0415
    from .verdict import Refusal  # noqa: PLC0415

    left = changes.out_of_scope(ctx)
    if not left:
        return None
    return _block(ctx, Refusal("changes", changes.reason(left, ctx.caller, at_stop=False),
                               paths=tuple(path for path, _ in left)))


def subagent_start(ctx: Context) -> None:
    """SubagentStart: records a role's starting state."""
    if ctx.caller.kind == ROLE:
        from .changes import write_record  # noqa: PLC0415

        write_record(ctx.project, ctx.caller)


def subagent_stop(ctx: Context) -> dict | None:
    """SubagentStop: blocks a role's stop once while changes outside its scope remain."""
    if ctx.caller.kind != ROLE:
        return None
    from . import changes, log  # noqa: PLC0415
    from .verdict import Refusal  # noqa: PLC0415

    left = changes.out_of_scope(ctx)
    paths = tuple(path for path, _ in left)
    if left and not ctx.data.get("stop_hook_active"):
        return _block(ctx, Refusal("changes", changes.reason(left, ctx.caller, at_stop=True),
                                   paths=paths))
    if left:
        log.write(ctx, "changes", "stop", paths)
    changes.delete_record(ctx.project, ctx.caller)
    return None


def session_start(ctx: Context) -> dict | None:
    """SessionStart: cleans old files and turns on the git hooks in a fresh clone (8.1)."""
    from . import gitstate, log  # noqa: PLC0415

    log.clean(ctx.project)
    value = gitstate.hooks_path(ctx.project)
    notes = []
    if value is None and os.path.isdir(ctx.project.hooks_dir()):
        gitstate.set_hooks_path(ctx.project)
        notes.append(f"troy-mode turned on its git hooks: core.hooksPath was unset and is now "
                     f"{HOOKS_PATH}.")
    elif not gitstate.hooks_on(value):
        state = "unset" if value is None else f"set to {value}"
        notes.append(f"The troy-mode git hooks are off: core.hooksPath is {state}, and troy-mode "
                     "leaves it. Commits, merges, and pushes are refused until it is "
                     f"{HOOKS_PATH}.")
    missing = ctx.project.missing_hooks()
    if missing:
        notes.append(f"The troy-mode git hooks are incomplete: {', '.join(missing)} missing from "
                     f"{HOOKS_PATH}. Commits, merges, and pushes are refused until troy-init "
                     "restores them.")
    if not notes:
        return None
    return {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                   "additionalContext": " ".join(notes)}}


def user_prompt_expansion(ctx: Context) -> dict | None:
    """UserPromptExpansion: refuses poteto-mode's commands, with no log line (F13 design 7.2)."""
    from . import modeguard  # noqa: PLC0415

    return modeguard.check(ctx.data.get("command_name"))


HANDLERS = {
    "SessionStart": session_start,
    "SubagentStart": subagent_start,
    "PreToolUse": pre_tool_use,
    "PostToolUse": post_tool_use,
    "SubagentStop": subagent_stop,
    "UserPromptExpansion": user_prompt_expansion,
}

# Events whose errors only warn, whoever the caller is: Troy's own typed
# commands must never be blocked by a hook error (F13 design 7.2).
_WARN_ONLY = ("SessionStart", "SubagentStart", "UserPromptExpansion")


def _posting_call(ctx: Context) -> str | None:
    """Names the gh command that posts text in a main-session shell call, if any (D200)."""
    if ctx.event != "PreToolUse" or ctx.tool not in ("Bash", "PowerShell"):
        return None
    try:
        from .commands import post_in_text  # noqa: PLC0415

        return post_in_text(str(ctx.tool_input().get("command") or ""))
    except Exception:  # noqa: BLE001  (the error rule must not fail itself)
        return "gh"


def _on_error(ctx: Context, exc: Exception) -> tuple[dict | None, int]:
    """Applies D39: refuse a subagent's call, only warn for the main session.

    D200's exception: a main-session call that posts text to GitHub is refused,
    because the hook could not check the text and GitHub keeps every edit.
    """
    from .verdict import Refusal  # noqa: PLC0415

    message = f"troy-mode hook error: {type(exc).__name__}: {exc}"
    posting = _posting_call(ctx) if ctx.caller.kind == MAIN else None
    if posting:
        return _deny(ctx, Refusal("error", message + f". `{posting}` posts text to GitHub that "
                                  "the hook cannot check now, so the call is refused (F05 "
                                  "D200). Fix the error, for example the config, and try "
                                  "again.", posting)), 0
    if ctx.caller.kind == MAIN or ctx.event in _WARN_ONLY:
        sys.stderr.write(message + "\n")
        return None, 1
    refusal = Refusal("error", message + ". The call is refused because the hook cannot "
                      "check it (F05 D39). Report this in your report.")
    if ctx.event == "PreToolUse":
        return _deny(ctx, refusal), 0
    if ctx.event == "SubagentStop" and ctx.data.get("stop_hook_active"):
        from . import log  # noqa: PLC0415

        log.write(ctx, "error", "stop")
        return None, 0
    return _block(ctx, refusal), 0


def _read_input() -> dict | None:
    """Reads the hook input from stdin; None when it is not a JSON object."""
    raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def main(argv: list[str]) -> int:
    """Runs one hook event.

    Args:
        argv: The command-line arguments: the event name.

    Returns:
        The exit code: 0, or 1 for a main-session error (non-blocking).
    """
    event = argv[0] if argv else ""
    data = _read_input()
    if data is None:
        sys.stderr.write("troy-mode hook error: the hook input is not a JSON object\n")
        return 1
    project = find_project(str(data.get("cwd") or os.getcwd()))
    if project is None:
        return 0
    ctx = Context(event, data, project)
    try:
        handler = HANDLERS.get(event)
        if handler is None:
            raise ValueError(f"unknown hook event {event!r}")
        output, code = handler(ctx), 0
    except Exception as exc:  # noqa: BLE001  (D39: every error is caught)
        output, code = _on_error(ctx, exc)
    if output:
        sys.stdout.write(json.dumps(output))
        sys.stdout.flush()
    return code

