"""R19: commit identity and Claude attribution (design section 6.6)."""

import re

from .config import Config
from .context import PrContext
from .report import FAIL, PASS, WARN, Detail, Result, outcome

GITHUB_COMMITTER = "noreply@github.com"

_ALWAYS = [
    re.compile(r"^[ \t]*co-authored-by:.*(claude|anthropic\.com)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"generated with \[?claude code", re.IGNORECASE),
    re.compile(r"claude\.com/claude-code|claude\.ai/code", re.IGNORECASE),
    re.compile(r"noreply@anthropic\.com", re.IGNORECASE),
]
_STRICT = re.compile(r"\b(claude|anthropic)\b", re.IGNORECASE)
_SCISSORS = "# ------------------------ >8 ------------------------"


def find_attribution(text: str, mode: str) -> list[int]:
    """Finds the lines that carry Claude attribution.

    Args:
        text: A commit message, PR title, or PR description.
        mode: "strict" also counts any whole word Claude or Anthropic;
            "trailers" counts only the attribution patterns.

    Returns:
        1-based line numbers with attribution, in order, without repeats.
    """
    found = set()
    patterns = _ALWAYS + ([_STRICT] if mode == "strict" else [])
    for pattern in patterns:
        for match in pattern.finditer(text):
            found.add(text.count("\n", 0, match.start()) + 1)
    return sorted(found)


def clean_commit_message(text: str) -> str:
    """Drops what git strips from a message file: comment lines and the diff below the scissors line."""
    text = text.split(_SCISSORS, 1)[0]
    return "\n".join(line for line in text.splitlines() if not line.startswith("#"))


def _text_details(label: str, text: str, mode: str, keep_line: bool) -> list[Detail]:
    """Builds one detail per attribution line in a piece of text.

    Args:
        label: Where the text comes from, for example "PR title".
        text: The text to scan.
        mode: The attribution mode.
        keep_line: Put the line number in the detail's line field too.

    Returns:
        One detail per line with attribution.
    """
    details = []
    lines = text.splitlines() or [""]
    for line in find_attribution(text, mode):
        snippet = lines[min(line, len(lines)) - 1].strip()[:80]
        details.append(Detail(None, line if keep_line else None,
                              f"{label} line {line} carries attribution: {snippet}"))
    return details


def _identity_details(ctx: PrContext) -> list[Detail]:
    """Checks each commit's author and committer email against the config."""
    email = ctx.config.commit_email
    details = []
    for commit in ctx.commits:
        short = commit.sha[:12]
        if commit.author_email != email:
            details.append(Detail(None, None, f"commit {short} author {commit.author_email}, "
                                              f"expected {email}"))
        if commit.committer_email not in (email, GITHUB_COMMITTER):
            details.append(Detail(None, None, f"commit {short} committer "
                                              f"{commit.committer_email}, expected {email}"))
    return details


def check_r19(ctx: PrContext) -> Result:
    """Checks commit emails and attribution in commits, title, and description (R19).

    Args:
        ctx: The PR under check.

    Returns:
        FAIL for a wrong email or any attribution. WARN when no commit_email
        is configured and nothing else fails. PASS otherwise.
    """
    mode = ctx.config.attribution_mode
    fails, warns = [], []
    if ctx.config.commit_email is None:
        warns.append(Detail(None, None, "No commit_email in .troy-mode/config.toml; "
                                        "commit emails not checked."))
    else:
        fails += _identity_details(ctx)
    for commit in ctx.commits:
        fails += _text_details(f"commit {commit.sha[:12]} message", commit.message, mode, False)
    fails += _text_details("PR title", ctx.title_text, mode, False)
    if ctx.body is not None:
        fails += _text_details("PR description", ctx.body, mode, True)
    result = outcome(fails, warns)
    if result == FAIL:
        return Result("R19", FAIL, f"{len(fails)} problems with commit identity or attribution.",
                      fails)
    if result == WARN:
        return Result("R19", WARN, "No attribution. Commit emails not checked.", warns)
    noun = "commit" if len(ctx.commits) == 1 else "commits"
    return Result("R19", PASS, f"{len(ctx.commits)} {noun} by {ctx.config.commit_email}. "
                               "No attribution.")


def check_commit(config: Config, message: str, email: str) -> Result:
    """Checks one commit before it is made, for the commit subcommand (R19).

    Args:
        config: Settings read from the working tree.
        message: The commit message, already cleaned of comment lines.
        email: The author email git will use.

    Returns:
        FAIL for a wrong email or attribution in the message, WARN when no
        commit_email is configured, and PASS otherwise.
    """
    fails, warns = [], []
    if config.commit_email is None:
        warns.append(Detail(None, None, "No commit_email in .troy-mode/config.toml; "
                                        "email not checked."))
    elif email != config.commit_email:
        fails.append(Detail(None, None, f"author email {email}, expected {config.commit_email}"))
    fails += _text_details("commit message", message, config.attribution_mode, False)
    result = outcome(fails, warns)
    messages = {FAIL: "The commit breaks R19.", WARN: "No attribution. Email not checked.",
                PASS: f"Author {email}. No attribution."}
    return Result("R19", result, messages[result], fails or warns)
