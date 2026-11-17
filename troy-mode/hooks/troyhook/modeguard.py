"""The mode guard: poteto-mode's commands are off in a troy-mode project (F13 design).

Claude Code's UserPromptExpansion event gives the command it resolved, such
as ``tstack:poteto-mode``, whether Troy typed the prefix or not. The
guard refuses ``poteto-mode`` and ``no-comments`` from any plugin prefix or
none (D122), with no override (D123), and lets every other command through.
"""

from .scopes import PLUGIN_PREFIX

GUARDED = ("poteto-mode", "no-comments")

# The clash of each command, in English and Chinese (design section 6, D124).
_CLAUSES = {
    "poteto-mode": (
        "poteto-mode's way of working breaks troy-mode's rules: only troy-mode's roles write "
        "code, each PR holds one stage, and Troy approves the designs",
        "poteto-mode 的工作方式会破坏 troy-mode 的规则：只有 troy-mode 的角色写代码，"
        "每个 PR 只放一个阶段，设计要 Troy 批准",
    ),
    "no-comments": (
        "/no-comments deletes doc comments that troy-mode's rule R05 requires",
        "/no-comments 会删除 troy-mode 规则 R05 要求的文档注释",
    ),
}


def guarded(command_name) -> str | None:
    """Gives the guarded name a command resolves to.

    Args:
        command_name: The input's command_name; any value.

    Returns:
        ``poteto-mode`` or ``no-comments`` when the name, without the part up
        to its first ``:``, is one of them; None otherwise.
    """
    if not isinstance(command_name, str):
        return None
    name = command_name.split(":", 1)[-1]
    return name if name in GUARDED else None


def message(command_name: str) -> str:
    """Builds the refusal for a guarded command (design section 6).

    Args:
        command_name: The command as Claude Code resolved it, shown with a ``/``.

    Returns:
        An English line and a Chinese line that name the command, give its
        clash, and point to troy-mode.
    """
    english, chinese = _CLAUSES[guarded(command_name)]
    shown = "/" + command_name
    mode = "/" + PLUGIN_PREFIX + "troy-mode"
    return (f"troy-mode: {shown} is off here. This project uses troy-mode (it has a .troy-mode "
            f"folder), and {english}. Type {mode} and your request instead. It also handles "
            "questions and experiments, which open no PR.\n"
            f"troy-mode：这里停用 {shown}。本项目使用 troy-mode（有 .troy-mode 文件夹），"
            f"而 {chinese}。请改用 {mode} 加上你的请求。提问和试验也用它，不开 PR。")


def check(command_name) -> dict | None:
    """Decides one expanded command.

    Args:
        command_name: The input's command_name; any value.

    Returns:
        The block output for a guarded command, or None to let it through.
    """
    if guarded(command_name) is None:
        return None
    return {"decision": "block", "reason": message(command_name)}
