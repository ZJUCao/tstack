"""The next entry of a status report: one action and its keys (F07 design 5, F08 design 3.3).

F18 adds `premise`, `escalate`, `ruling`, and `overturn` (F18 design 5, 6, and 8).
"""

KEYS = ("action", "item", "stage", "task", "title", "branch", "pr", "merged_by", "doc", "step",
        "tag", "commit", "issue", "ideas", "escalate", "ruling", "overturn")
# The wait an author's failing work ends in (F18 design 4.1, D175).
STILL_FAILS = "W7"


def make(action: str, **values) -> dict:
    """Builds a next entry with every key, the ones not given null, rounds and attempts 0."""
    entry = {key: values.get(key) for key in KEYS}
    entry["action"] = action
    entry["rounds"] = values.get("rounds", 0)
    entry["attempts"] = values.get("attempts", 0)
    entry["premise"] = False
    return entry


def attempt_flags(entry: dict, escalated: bool) -> dict:
    """Sets `premise` and the attempts' `escalate` from the entry's attempt count (D175).

    Args:
        entry: A next entry, its attempts final.
        escalated: An escalation already answers the newest attempt, so
            nothing new needs to escalate.

    Returns:
        The entry. `premise` is true at exactly 3 attempts: the next author run
        tests the premise. From 4 attempts on, `escalate` is W7 until an
        escalation is recorded.
    """
    entry["premise"] = entry["attempts"] == 3
    if entry["attempts"] >= 4 and not escalated:
        entry["escalate"] = STILL_FAILS
    return entry
