"""Run helpers for the code-shape tests (R04 to R07)."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from builders import make_config
from code_helpers import run_code
from helpers import Content
from outcome import Outcome

IMPL = "[F04 5/6 impl] Change"
TESTS = "[F04 4/6 tests] Change"


def lang_config(
    name: Optional[str] = "python",
    roots: Optional[Sequence[str]] = None,
    limits: Optional[Mapping[str, int]] = None,
) -> str:
    """Builds a config with a ``[lang]`` section.

    Args:
        name: Value of ``[lang] name``, or None to leave it out.
        roots: Value of ``[lang] source_roots``, or None to leave it out.
        limits: Mapping of ``[limits]`` keys to integers.

    Returns:
        The config text.
    """
    extra = ""
    if name is not None or roots is not None:
        extra = "[lang]\n"
        if name is not None:
            extra += f'name = "{name}"\n'
        if roots is not None:
            quoted = ", ".join(f'"{r}"' for r in roots)
            extra += f"source_roots = [{quoted}]\n"
    return make_config(limits=limits, extra=extra)


def run_py(
    changes: Mapping[str, Content],
    base_files: Optional[Mapping[str, Content]] = None,
    title: str = IMPL,
    name: Optional[str] = "python",
    roots: Optional[Sequence[str]] = None,
    limits: Optional[Mapping[str, int]] = None,
    body: Optional[str] = None,
) -> Outcome:
    """Runs ``troy_check.py code`` on a one-commit PR with a Python config.

    Args:
        changes: Paths mapped to new content for the PR commit.
        base_files: Files of the base commit.
        title: PR title.
        name: Value of ``[lang] name``, or None for no language.
        roots: Value of ``[lang] source_roots``, or None for the default.
        limits: Mapping of ``[limits]`` keys to integers.
        body: PR description text.

    Returns:
        The outcome of the run.
    """
    config = lang_config(name, roots, limits)
    return run_code(title, changes, base_files, config=config, body=body)


def has_detail(outcome: Outcome, rule: str, path: str, line: Optional[int] = None) -> bool:
    """Tells whether a rule's details name a path, and optionally a line.

    Args:
        outcome: The outcome of a run.
        rule: Rule ID.
        path: Expected ``path`` of a detail entry.
        line: Expected ``line`` of the same entry, or None for any line.

    Returns:
        True if one detail entry matches.
    """
    for detail in outcome.details(rule):
        if detail.get("path") == path and (line is None or detail.get("line") == line):
            return True
    return False
