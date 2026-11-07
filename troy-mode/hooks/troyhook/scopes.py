"""Callers and write scopes (design sections 4 and 5).

SCOPES equals F04 design section 3 and the Write scope section of each
agent file; a test keeps them equal.
"""

import re

PLUGIN_PREFIX = "troy-pstack:"

SCOPES: dict[str, dict[str, tuple[str, ...]]] = {
    "troy-architect": {
        "patterns": ("docs/architecture*.md", "docs/adr/**", "docs/features/*/design*.md"),
        "classes": (),
    },
    "troy-interface-designer": {
        "patterns": ("docs/features/*/design*.md",),
        "classes": (),
    },
    "troy-test-manager": {
        "patterns": ("docs/features/*/test-plan*.md", "docs/versions/*/test-plan*.md"),
        "classes": (),
    },
    "troy-developer": {"patterns": (), "classes": ("source", "dependencies")},
    "troy-test-engineer": {"patterns": (), "classes": ("tests", "dependencies")},
    "troy-code-reviewer": {"patterns": (), "classes": ()},
}

NOTHING: dict[str, tuple[str, ...]] = {"patterns": (), "classes": ()}

ROLE_PATTERN = re.compile(
    r"^troy-pstack:troy-(architect|interface-designer|test-manager|developer|test-engineer"
    r"|code-reviewer)$"
)

MAIN, ROLE, OTHER = "main", "role", "other"


class Caller:
    """Who makes a call (design section 4, D40).

    Attributes:
        kind: MAIN for the main session, ROLE for one of the six roles, and
            OTHER for any other subagent.
        agent_id: The input's agent_id, or None for the main session.
        agent_type: The input's agent_type, or None.
        role: The agent name without the plugin prefix for a role, else None.
    """

    __slots__ = ("kind", "agent_id", "agent_type", "role")

    def __init__(self, kind: str, agent_id: str | None, agent_type: str | None,
                 role: str | None):
        """Stores who makes the call."""
        self.kind, self.agent_id, self.agent_type, self.role = kind, agent_id, agent_type, role

    def scope(self) -> dict[str, tuple[str, ...]]:
        """Returns the caller's write scope; empty for other subagents."""
        return SCOPES[self.role] if self.role else NOTHING


def caller_of(data: dict) -> Caller:
    """Sorts a hook input into one of the three callers.

    Args:
        data: The hook input.

    Returns:
        The caller. A call with no agent_id is the main session's.
    """
    agent_id = data.get("agent_id")
    agent_type = data.get("agent_type")
    if not agent_id:
        return Caller(MAIN, None, agent_type if isinstance(agent_type, str) else None, None)
    if isinstance(agent_type, str) and ROLE_PATTERN.fullmatch(agent_type):
        return Caller(ROLE, str(agent_id), agent_type, agent_type[len(PLUGIN_PREFIX):])
    return Caller(OTHER, str(agent_id), agent_type if isinstance(agent_type, str) else None, None)


def describe(scope: dict[str, tuple[str, ...]]) -> str:
    """Words a write scope for a refusal message.

    Args:
        scope: A value of SCOPES, or NOTHING.

    Returns:
        For example "docs/adr/**, docs/architecture*.md" or "the source and
        dependencies path classes".
    """
    parts = list(scope["patterns"])
    classes = scope["classes"]
    if classes:
        parts.append(f"the {' and '.join(classes)} path classes")
    if not parts:
        return "nothing in the repository except files git ignores"
    return ", ".join(parts)
