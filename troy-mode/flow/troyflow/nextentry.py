"""The next entry of a status report: one action and its keys (F07 design 5, F08 design 3.3)."""

KEYS = ("action", "item", "stage", "task", "title", "branch", "pr", "merged_by", "doc", "step",
        "tag", "commit", "issue", "ideas")


def make(action: str, **values) -> dict:
    """Builds a next entry with every key, the ones not given null, rounds and attempts 0."""
    entry = {key: values.get(key) for key in KEYS}
    entry["action"] = action
    entry["rounds"] = values.get("rounds", 0)
    entry["attempts"] = values.get("attempts", 0)
    return entry
