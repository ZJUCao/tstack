"""The rule state from git: P rules, baseline lines, choices, and the cleanup (F09 design 3.2).

The rules live in docs/rules.md on origin/main, a rule change in progress is
an open [rules] PR, Troy's choice for existing code is in the rules table's
change log, and the cleanup still to do is the baseline lines left.
"""

import re
from dataclasses import dataclass, field

from . import baseline, repo as git
from .nextentry import make
from .repo import MAIN, Repo
from .ruletable import P_ID, TableState, choice, next_id, number, read_table
from .stages import parse_subject

RULES = "docs/rules.md"
RULES_ZH = "docs/rules.zh-CN.md"
_APPLY = re.compile(r"Apply (P\d{2,3}) to \S")
_ARCHITECTURE = re.compile(r"Change the architecture for (P\d{2,3})")
_RULES_PR = re.compile(r"(?:Add|Change|Retire) (P\d{2,3})\b")


@dataclass
class RuleState:
    """The rules of one commit.

    Attributes:
        table: The English rules table's state, or None without one.
        lines: The baseline lines by P ID, once read.
    """

    table: TableState | None = None
    lines: dict[str, list[dict]] = field(default_factory=dict)

    def next_id(self) -> str | None:
        """Returns the next free P ID, or None without a rules table."""
        return next_id("P", self.table.ids()) if self.table else None

    def next_r_id(self) -> str | None:
        """Returns the next R ID, or None without a rules table."""
        return next_id("R", self.table.r_ids) if self.table else None

    def entries(self) -> list[dict]:
        """Returns each P row with its choice and baseline lines, in table order."""
        if self.table is None:
            return []
        return [{"id": row["id"], "rule": row["rule"], "type": row["type"],
                 "enforced_by": row["enforced_by"], "since": row["since"],
                 "retired": row["retired"], "choice": choice(self.table.log, row["id"]),
                 "baseline": self.lines.get(row["id"], [])} for row in self.table.rows]

    def unknown(self) -> list[str]:
        """Describes the baseline lines whose P ID has no row."""
        ids = set(self.table.ids()) if self.table else set()
        return [f"{entry['path']} line {entry['line']} holds baseline: {rule_id}, which is no "
                f"P rule of {RULES}." for rule_id, found in sorted(self.lines.items())
                if rule_id not in ids for entry in found]

    def files_of(self, rule_id: str) -> list[str]:
        """Returns the files that hold a rule's baseline lines, sorted."""
        return sorted({entry["path"] for entry in self.lines.get(rule_id, [])})


def read_rules(repo: Repo, ref: str = MAIN, lines: str = "rows") -> RuleState:
    """Reads the rules of a commit.

    Args:
        repo: The checkout.
        ref: The commit, origin/main by default.
        lines: When to read the baseline lines: "always", "rows" (only when
            the table has a P row), or "never".

    Returns:
        The rule state; empty when the commit or its rules table is missing.
    """
    if git.commit_of(repo, ref) is None:
        return RuleState()
    state = RuleState(read_table(git.read(repo, ref, RULES)))
    wanted = lines == "always" or (lines == "rows" and state.table and state.table.rows)
    if wanted:
        state.lines = baseline.find(repo, ref)
    return state


def cleanup_rule(entries: list[dict]) -> dict | None:
    """The next entry for a rule's cleanup (design 3.2), or None.

    A rule that is not retired, whose newest change-log row says "fixed by
    cleanup PRs", and whose baseline lines remain, is cleaned up next, the
    lowest P number first.
    """
    due = [e for e in entries
           if not e["retired"] and e["choice"] == "cleanup" and e["baseline"]]
    if not due:
        return None
    first = min(due, key=lambda e: number(e["id"]))
    return make("cleanup", item=first["id"], merged_by="f07")


def pr_rule(title: str) -> tuple[str, str | None] | None:
    """Reads the rule and the author task of an open PR of the rule flow.

    Returns:
        (P ID, task) for "[refactor] Apply P01 to ..." (DV5), "[P01 test-fix]
        ..." (TE6), "[docs] Change the architecture for P01" (AR6), and
        "[rules] Add|Change|Retire P01, ..." (no task); else None.
    """
    parsed = parse_subject(title)
    if parsed is None:
        return None
    if parsed.kind == "test-fix" and P_ID.fullmatch(parsed.id or ""):
        return parsed.id, "TE6"
    patterns = {"refactor": (_APPLY, "DV5"), "docs": (_ARCHITECTURE, "AR6"),
                "rules": (_RULES_PR, None)}
    if parsed.kind not in patterns:
        return None
    pattern, task = patterns[parsed.kind]
    found = pattern.match(parsed.summary)
    return (found.group(1), task) if found else None
