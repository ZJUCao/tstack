"""Briefs for a rule item: AR6, DV5, TE6, and their reviews (F09 design 5 and 7).

A P ID is a project rule; an R ID is a rule for every troy-mode project, or
a change to an R rule (design 5.6 and 6). The rule state comes from
docs/rules.md on origin/main.
"""

from dataclasses import dataclass, field
from pathlib import Path

from . import repo as git, summary
from .repo import MAIN
from .rulestate import RULES, RuleState, read_rules
from .ruletable import P_ID, R_ID

PLUGIN = Path(__file__).resolve().parents[3]
PACK_CONFIG = ("pyproject.toml", ".clang-tidy", ".clang-format", ".troy-mode/config.toml",
               ".github/workflows/project-rules.yml")
PLUGIN_FILES = ("docs/troy-mode/requirements.md", "troy-mode/templates/rules.md",
                "troy-mode/checks/troycheck/", "agents/")
FIRST_TASKS = ("AR6",)
DOCS_TASKS = ("AR6", "AR5")
REFACTOR_TASKS = ("DV5", "CR1", "AR5")
TEST_FIX_TASKS = ("TE6", "TM2", "CR1", "AR5")

_PROPOSAL = (
    "Name the strongest level that works and why no stronger one does: the architecture, a "
    "check of a tool the language pack already runs or a troy-check limit in "
    ".troy-mode/config.toml, a step without an environment in "
    ".github/workflows/project-rules.yml, or a Review or Process row in the rules table, never "
    "a test. Give the rule's text, type, and Enforced by for docs/rules.md in English and "
    "Chinese, the exact change to each config file or to the architecture, and the existing "
    "code that breaks the rule: run the tool on the whole repository with the rule turned on in "
    "a command-line option, through `{run}`, never by editing a config, and list the files and "
    "the count; for a review rule, read the code. ")
SENTENCES = {
    "AR6": "propose how to enforce the project rule in Input as {item}. " + _PROPOSAL
           + "When the tool has no per-file exemption in a config or dependency file, say so: "
           "the cleanup PRs then come first and the rule gets no baseline. For fixing the "
           "existing code now, list the cleanup PRs you expect, at most 5 files each and within "
           "R03: each fixes its files and deletes their baseline lines in the same commit, "
           "since a [refactor] or test-fix PR may change dependency files. Change no file, and "
           "report escalate with the proposal in Question, because Troy decides.",
    "DV5": "fix the source files that Input names so that they follow {item} in docs/rules.md, "
           "and in the same change delete each one's `baseline: {item}` line from {baseline}. "
           "Change nothing else, and stay within R03 (500 changed lines in 5 files).",
    "TE6": "fix the test files that Input names so that they follow {item} in docs/rules.md, "
           "and in the same change delete each one's `baseline: {item}` line from {baseline}. "
           "Each test still checks what it checked before; change nothing else.",
    "TM2": "review the test changes of {title} against {item} in docs/rules.md: each changed "
           "test still checks what it checked before and follows {item}, and its "
           "`baseline: {item}` line is gone.",
    "CR1": "review the PR {title}: each changed file follows {item} in docs/rules.md, its "
           "`baseline: {item}` line is gone, and nothing else changed.",
}
DOCS_SENTENCES = {
    "AR6": "write the architecture change for {item} that Troy approved, as Input says, in "
           "docs/architecture.md and its mirror, with an ADR in both languages, and report done. "
           + summary.SENTENCE,
}
R_SENTENCES = {
    "AR6": "propose how to enforce the rule for every troy-mode project in Input, as {item} of "
           "troy-mode's rules. As for a project rule: " + _PROPOSAL + "Also name each "
           "troy-pstack file that changes, which you read in the plugin folder: requirements "
           "section 6 with the new R row, the rules template, troy-check with a check and its "
           "tests, or a role's agent file; and say whether existing projects' code would break "
           "the rule when troy-init's upgrade brings it. Change no file, and report escalate "
           "with the proposal in Question, because Troy decides.",
}


@dataclass
class RuleContext:
    """What a rule item allows.

    Attributes:
        problems: What stops the brief.
        allowed: The tasks this context allows.
        why: The problem when the task is not allowed.
        title: The PR title, or None.
        kind: "first", "docs", "refactor", "test-fix", or "every-project".
        files: The files on origin/main that hold the rule's baseline lines.
    """

    problems: list[str]
    allowed: tuple[str, ...] = ()
    why: str = ""
    title: str | None = None
    kind: str = ""
    files: list[str] = field(default_factory=list)


def _stop(message: str) -> RuleContext:
    """A context that stops the brief with one problem."""
    return RuleContext([message])


def _r_context(task: str, item: str, parsed, state: RuleState) -> RuleContext:
    """The context of an R ID: AR6's proposal of a rule for every project."""
    known = state.table.r_ids if state.table else []
    following = state.next_r_id() or "R01"
    if item not in known and item != following:
        return _stop(f"{item} is neither an R rule of {RULES} on origin/main nor the next R ID, "
                     f"{following}.")
    if parsed is not None:
        return _stop(f"AR6 proposes a rule for every project ({item}) without a PR: give no "
                     "--title.")
    return RuleContext([], FIRST_TASKS, f"{task} does not belong to a rule for every project; "
                       "only AR6 runs.", None, "every-project")


def _titled(task: str, item: str, parsed, title: str, new: bool,
            state: RuleState) -> RuleContext:
    """The context of a P rule with a --title: its architecture, cleanup, or test cleanup PR."""
    if parsed.kind == "docs":
        return RuleContext([], DOCS_TASKS, f"{task} does not belong to the architecture PR of "
                           f"{item}.", title, "docs")
    if parsed.kind not in ("refactor", "test-fix"):
        return _stop(f"--title {title!r} does not fit rule {item}: give a [refactor] Apply "
                     f"{item} to <area>, [{item} test-fix], or [docs] title.")
    if new:
        return _stop(f"{item} is not in {RULES} on origin/main yet, so it has no cleanup.")
    if parsed.kind == "refactor" and not parsed.summary.startswith(f"Apply {item} to "):
        return _stop(f"--title {title!r} does not start its summary with \"Apply {item} to \".")
    if parsed.kind == "test-fix" and parsed.id != item:
        return _stop(f"--title {title!r} names {parsed.id}, not {item}.")
    allowed = REFACTOR_TASKS if parsed.kind == "refactor" else TEST_FIX_TASKS
    return RuleContext([], allowed, f"{task} does not belong to a {parsed.kind} PR of {item}.",
                       title, parsed.kind, state.files_of(item))


def context(repo, task: str, item: str, parsed, title: str | None) -> RuleContext:
    """Finds what a rule item allows and what stops its brief (design 7)."""
    state = read_rules(repo, MAIN, lines="never")
    if R_ID.fullmatch(item):
        return _r_context(task, item, parsed, state)
    row = state.table.row(item) if state.table else None
    free = state.next_id() or "P01"
    if row is not None and row["retired"]:
        return _stop(f"{item} is retired in {RULES} on origin/main; a retired ID is never used "
                     "again.")
    if row is None and item != free:
        return _stop(f"{item} is neither a rule of {RULES} on origin/main nor the next free ID, "
                     f"{free}.")
    if parsed is None:
        return RuleContext([], FIRST_TASKS, f"{task} needs a [refactor] Apply {item} to <area> "
                           f"or [{item} test-fix] title for rule {item}.", None, "first")
    if parsed.kind in ("refactor", "test-fix") and row is not None:
        state = read_rules(repo, MAIN, lines="always")
    return _titled(task, item, parsed, title, row is None, state)


def read_first(repo, task: str, ctx: RuleContext) -> list[str]:
    """Lists the files a role on a rule item reads first (design 5.1 and 5.4)."""
    paths = [p for p in ("docs/rules.md", "docs/requirements.md", "docs/architecture.md")
             if git.exists(repo, "HEAD", p)]
    if task == "AR6":
        paths += [p for p in PACK_CONFIG if git.exists(repo, "HEAD", p)]
    if task == "AR6" and ctx.kind == "every-project":
        for rel in PLUGIN_FILES:
            full = PLUGIN / rel
            if rel.endswith("/") or full.exists():
                paths.append(full.as_posix() + ("/" if rel.endswith("/") else ""))
    if ctx.kind in ("refactor", "test-fix"):
        paths += [p for p in ctx.files if git.exists(repo, "HEAD", p) and p not in paths]
    return paths


def sentences(ctx: RuleContext) -> dict[str, str]:
    """The task sentences for a rule item's context."""
    if ctx.kind == "every-project":
        return dict(R_SENTENCES)
    if ctx.kind == "docs":
        return dict(DOCS_SENTENCES)
    return dict(SENTENCES)


def is_rule_item(item: str) -> bool:
    """Tells whether an item is a P ID or an R ID."""
    return bool(P_ID.fullmatch(item) or R_ID.fullmatch(item))
