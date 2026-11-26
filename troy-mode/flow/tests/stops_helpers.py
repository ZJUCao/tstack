"""Shared fixtures for the F18 part 1 tests, fewer stops (F18 design 4 to 6, 8, 13.1, 13.2).

Written from F18 design version 1.0 and the part 1 interface contract before the code
exists. Black-box, as F07's tests are: the engine runs as a subprocess through
``flow_helpers``, on clones of bare origins, with the fake gh. Only ``troyflow.waits`` and
``troyflow.premise`` are imported, for the table of waits and the premise text, which the
contract (sections 1 and 5) names as importable.

What this module adds:

- Comment bodies with F07's and F18's fixed headings: reviews, attempts, waits with and
  without the ``Wait: W<n>`` line, escalations, rulings with their numbered findings, and
  the overturn headings of a progress issue (contract sections 1 and 3).
- Timed comments, which may carry a ``url``, as ``gh pr view --json comments`` gives them.
- A project whose features sit at every stage, with a bug at each step and a version, for
  the briefs of every author task and of AR8 (contract sections 5 and 6).
- Readers for a brief's prompt: its Task field and its Read first list.
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from flow_helpers import (
    F01, F02, F03, F04, F05, LOGIN, PLUGIN_ROOT, PROJECT, Feature, Project, base_files,
    base_step, bug_step, stages,
)

F06 = Feature("F06", "Sort output")
F07 = Feature("F07", "Merge counts")
SEVEN = (F01, F02, F03, F04, F05, F06, F07)
CARD = (PLUGIN_ROOT / "skills" / "principle-attack-the-premise" / "SKILL.md").resolve()
TEST_FIX = "[F01 test-fix] Wrong expected count in F01-T01"
DOCS_UPDATE = "[docs] Update the F01 design"
BUG_A = "[B13 A/B test] Wrong count of tabs"
BUG_TEST_FIX = "[B12 test-fix] Fix the reproduction test of B12"
WAIT_IDS = tuple(f"W{n}" for n in range(1, 12))
_BASE = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------ modules

def engine_module(name: str):
    """Imports one ``troyflow`` module with the paths ``troy_flow.py`` sets up.

    Args:
        name: The module's name after ``troyflow.``, such as ``waits``.

    Returns:
        The module.

    Raises:
        AssertionError: It cannot be imported (the engine has no such module yet).
    """
    flow = PLUGIN_ROOT / "troy-mode/flow"
    for folder in (flow.parent / "init", flow.parent / "hooks", flow.parent / "checks", flow):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        return importlib.import_module(f"troyflow.{name}")
    except ImportError as exc:
        raise AssertionError(f"troyflow.{name} cannot be imported: {exc}") from exc


# ------------------------------------------------------------------ comments

def when(minutes: float, day: int = 0) -> str:
    """A GitHub time, some minutes after 09:00 UTC on 2026-11-20 plus some days."""
    moment = _BASE + timedelta(days=day, minutes=minutes)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def pr_url(number: int) -> str:
    """A PR's URL."""
    return f"https://github.com/{LOGIN}/{PROJECT}/pull/{number}"


def comment_url(number: int, comment: int) -> str:
    """The URL of one comment on a PR."""
    return f"{pr_url(number)}#issuecomment-{comment}"


def timed(body: str, minutes: float, url: Optional[str] = None, day: int = 0) -> dict:
    """One comment of ``gh pr view --json comments``, posted through Troy's account.

    Args:
        body: The comment's body.
        minutes: Minutes after 09:00 UTC on 2026-11-20.
        url: The comment's ``url``, or None for a comment without one.
        day: Days after 2026-11-20.

    Returns:
        The comment entry.
    """
    entry = {"author": {"login": LOGIN}, "body": body, "createdAt": when(minutes, day)}
    if url is not None:
        entry["url"] = url
    return entry


def in_order(*bodies: str, urls: Optional[dict] = None) -> list:
    """Comments one minute apart, oldest first; ``urls`` maps a body's index to its url."""
    return [timed(body, index, (urls or {}).get(index)) for index, body in enumerate(bodies)]


def review(role: str, number: int, result: str, *findings: str) -> str:
    """A review comment: ``<Role> review, round <n>: <result>`` and numbered findings."""
    lines = [f"{index}. {text}" for index, text in enumerate(findings, start=1)] or ["None"]
    return f"{role} review, round {number}: {result}\n\n" + "\n".join(lines)


def three_rounds(role: str, last: str = "changes-requested") -> list:
    """A reviewer's rounds 1 and 2 asking for changes and round 3 ending in ``last``."""
    return [review(role, 1, "changes-requested", "Naming: rename count() to count_words()."),
            review(role, 2, "changes-requested", "R05: count_words() has no doc comment."),
            review(role, 3, last, "R05: count_words() still has no doc comment.",
                   "Naming: the module name is vague.")]


def attempt(role: str, number: int, *lines: str) -> str:
    """An attempt comment: ``<Role> attempt <n>: failed`` and the lines under it."""
    return "\n".join([f"{role} attempt {number}: failed", "", *(lines or ("ruff: 2 errors",))])


def waiting(text: str = "approve this PR", wait: Optional[str] = None) -> str:
    """A ``Waiting for Troy: <text>`` comment, with ``Wait: <wait>`` as its next line."""
    body = f"Waiting for Troy: {text}"
    if wait is not None:
        body += f"\n\nWait: {wait}"
    return body + "\n\nWhat to decide is at the top of the description."


def escalation(trigger: str, wait: Optional[str] = None, *lines: str) -> str:
    """An ``Escalation: <trigger>`` comment, with ``Wait: <wait>`` as its next line."""
    body = f"Escalation: {trigger}"
    if wait is not None:
        body += f"\n\nWait: {wait}"
    return body + "\n\n" + "\n".join(lines or ("Where it stopped: the checks.",))


def ruling(ruler: str, result: str, *findings: tuple) -> str:
    """A ruling: ``<Ruler> ruling, round 3: <result>`` and one numbered line per finding.

    Args:
        ruler: ``Architect`` or ``Product Manager``.
        result: ``merge``, ``fix``, ``fixed``, or ``not fixed``.
        *findings: ``(verdict, reason)`` pairs.

    Returns:
        The body.
    """
    lines = [f"{index}. {verdict}: {reason}"
             for index, (verdict, reason) in enumerate(findings, start=1)]
    return f"{ruler} ruling, round 3: {result}\n\n" + "\n".join(lines)


def finding(number: int, verdict: str, reason: str) -> dict:
    """One finding of a ruling as ``rulings`` gives it (contract section 4)."""
    return {"number": number, "verdict": verdict, "reason": reason}


FIX_FINDINGS = (("fix", "R05 asks for a doc comment on count_words()."),
                ("does not block", "The module name follows the design's section 2."))
FIXED_FINDINGS = (("fixed", "count_words() has its doc comment now."),)
NOT_FIXED_FINDINGS = (("not fixed", "count_words() still has no doc comment."),)
MERGE_FINDINGS = (("does not block", "R05 does not apply to a private helper."),
                  ("does not block", "The module name follows the design's section 2."))


def overturn_link(number: int = 41, comment: int = 501) -> str:
    """The link to a ruling comment, as an ``Overturn:`` comment names it."""
    return comment_url(number, comment)


def overturn(link: str) -> str:
    """F07's ``Overturn: <link>`` comment on a progress issue (contract section 3)."""
    return f"Overturn: {link}\n\nTroy overturned the ruling: the reviewer's finding stands."


def carried_out(link: str) -> str:
    """F07's ``Overturn carried out: <link>`` comment on a progress issue."""
    return f"Overturn carried out: {link}\n\nThe [docs] design update merged."


# ------------------------------------------------------------------ projects

def brief_steps() -> list:
    """A project whose features sit at each point a brief may be asked for.

    F01 at stage 5 (stages 1 to 4 merged, so a test fix is possible), F02 at stage 1,
    F03 at stage 2, F04 at stage 3, F05 at stage 4, F06 at stage 6, and F07 accepted; bug
    B12 at step B (its PR A merged), and B13 at step A. Every feature is in v0.1, whose
    version test plan has a scenario that Claude runs.
    """
    return [base_step(base_files(SEVEN)), *stages(F01, 4), *stages(F03, 1), *stages(F04, 2),
            *stages(F05, 3), *stages(F06, 5), *stages(F07, 6),
            bug_step("B12", "test", "Crash on empty history")]


_PROJECTS: dict = {}


def brief_project() -> Project:
    """The shared clone of ``brief_steps``, built on first use. Tests must not change it."""
    if "briefs" not in _PROJECTS:
        _PROJECTS["briefs"] = Project(brief_steps())
    return _PROJECTS["briefs"]


def rules_project() -> Project:
    """A clone with P01 fixed by cleanup PRs (F09), for DV5, TE6, and AR8 on a cleanup PR."""
    if "rules" not in _PROJECTS:
        from rule_helpers import DEFAULT_LOG, P01, P02, P03, log_row, rules_step  # noqa: PLC0415
        log = DEFAULT_LOG + (log_row("5.0", "2026-11-10", "Retired P03, approved by Troy.",
                                     "停用 P03，Troy 批准。"),)
        _PROJECTS["rules"] = Project([rules_step((P01, P02, P03.retired("2026-11-10")), log)])
    return _PROJECTS["rules"]


REFACTOR = "[refactor] Apply P01 to counting"
RULE_TEST_FIX = "[P01 test-fix] Apply P01 to tests"


# ------------------------------------------------------------------ prompts

def task_field(prompt: str) -> str:
    """A brief prompt's Task field: the text after ``Task: `` up to the ``Item:`` line."""
    if not prompt.startswith("Task: ") or "\nItem: " not in prompt:
        return ""
    return prompt[len("Task: "):prompt.index("\nItem: ")]


def read_first_items(prompt: str) -> list:
    """A brief prompt's Read first entries, in order, without their ``- ``."""
    lines = prompt.split("\n")
    if "Read first:" not in lines:
        return []
    found = []
    for line in lines[lines.index("Read first:") + 1:]:
        if not line.startswith("- "):
            break
        found.append(line[2:])
    return found
