"""Helpers for running ``troy_check.py code`` in throwaway repositories."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union

from helpers import DEFAULT_CONFIG, Content, Outcome, Sandbox, write_file
from prefetch import prefetchable

_COUNTER = itertools.count(1)
Report = Union[str, Path]


def code_sandbox(
    title: str,
    changes: Optional[Mapping[str, Content]] = None,
    base_files: Optional[Mapping[str, Content]] = None,
    config: Optional[str] = DEFAULT_CONFIG,
    history: Sequence[str] = (),
    moved_on: Sequence[str] = (),
) -> Sandbox:
    """Builds a sandbox with base history and a one-commit PR on ``feature``.

    Args:
        title: PR title. It is also the PR commit's message (R01).
        changes: Paths mapped to new content for the PR commit.
        base_files: Files of the first commit on ``main``.
        config: Text of ``.troy-mode/config.toml``, or None for no file.
        history: Subjects of commits added to ``main`` before the PR branches.
        moved_on: Subjects of commits added to ``main`` after the PR branched.

    Returns:
        An open sandbox. The caller closes it.
    """
    sandbox = Sandbox(base_files, config)
    try:
        for subject in history:
            _history_commit(sandbox, subject)
        sandbox.branch()
        sandbox.commit(changes or {"docs/pr.md": "pr\n"}, message=title)
        sandbox.checkout("main")
        for subject in moved_on:
            _history_commit(sandbox, subject)
        sandbox.checkout("feature")
    except Exception:
        sandbox.close()
        raise
    return sandbox


def _history_commit(sandbox: Sandbox, subject: str) -> None:
    """Adds one commit with the given subject to the checked-out branch.

    Args:
        sandbox: The sandbox.
        subject: Commit message.
    """
    sandbox.commit({f"docs/history/h{next(_COUNTER)}.md": "h\n"}, message=subject)


def write_report(sandbox: Sandbox, text: str, suffix: str = "xml") -> Path:
    """Writes a report outside the repository, in the sandbox's temp folder.

    Args:
        sandbox: The sandbox that owns the temp folder.
        text: The report text. ``{ROOT}`` becomes the repository root.
        suffix: File extension.

    Returns:
        The path of the new file. Each call makes a new file.
    """
    rel = f"reports/r{next(_COUNTER)}.{suffix}"
    write_file(sandbox.tmp, rel, text.replace("{ROOT}", str(sandbox.root)))
    return sandbox.tmp / rel


def _as_path(sandbox: Sandbox, report: Report) -> Path:
    """Returns a path for a report given as text or as a path.

    Args:
        sandbox: The sandbox.
        report: XML text (written to a file), or a path. A relative path
            names a file in the sandbox's temp folder, outside the repo.

    Returns:
        The path to pass on the command line.
    """
    if not isinstance(report, Path):
        return write_report(sandbox, report)
    return report if report.is_absolute() else sandbox.tmp / report


def check_code(
    sandbox: Sandbox,
    title: str,
    junit: Sequence[Report] = (),
    coverage: Sequence[Report] = (),
    body: Optional[str] = None,
    base: str = "main",
    head: Optional[str] = "feature",
    json_report: bool = True,
    from_cwd: Optional[str] = None,
    extra_args: Sequence[str] = (),
) -> Outcome:
    """Runs ``troy_check.py code`` on a sandbox.

    Args:
        sandbox: The sandbox.
        title: PR title.
        junit: JUnit reports: text is written to a file, a ``Path`` is used as is.
        coverage: Cobertura reports, given like ``junit``.
        body: PR description text.
        base: Value of ``--base``.
        head: Value of ``--head``, or None to leave it out.
        json_report: Whether to pass ``--json``.
        from_cwd: Folder inside the repo to run from without ``--repo``.
        extra_args: Extra command-line arguments.

    Returns:
        The outcome of the run.
    """
    args = ["code", "--base", base, "--title", title]
    if head:
        args += ["--head", head]
    for report in junit:
        args += ["--junit", str(_as_path(sandbox, report))]
    for report in coverage:
        args += ["--coverage", str(_as_path(sandbox, report))]
    if body is not None:
        args += ["--body-file", str(write_report(sandbox, body, "md"))]
    if from_cwd is None:
        args += ["--repo", str(sandbox.root)]
    if json_report:
        args.append("--json")
    cwd = sandbox.root / from_cwd if from_cwd is not None else sandbox.tmp
    return sandbox.run_checker(*args, *extra_args, cwd=cwd)


def run_code(
    title: str,
    changes: Optional[Mapping[str, Content]] = None,
    base_files: Optional[Mapping[str, Content]] = None,
    config: Optional[str] = DEFAULT_CONFIG,
    history: Sequence[str] = (),
    moved_on: Sequence[str] = (),
    **check_kwargs,
) -> Outcome:
    """Builds a one-commit PR in a fresh repository and runs ``code`` on it.

    Args:
        title: PR title.
        changes: Paths mapped to new content for the PR commit.
        base_files: Files of the first commit on ``main``.
        config: Text of ``.troy-mode/config.toml``, or None for no file.
        history: Subjects of commits added to ``main`` before the PR branches.
        moved_on: Subjects of commits added to ``main`` after the branch point.
        **check_kwargs: Passed on to ``check_code``.

    Returns:
        The outcome of the run.
    """
    sandbox = code_sandbox(title, changes, base_files, config, history, moved_on)
    try:
        return check_code(sandbox, title, **check_kwargs)
    finally:
        sandbox.close()


run_code = prefetchable(run_code)
