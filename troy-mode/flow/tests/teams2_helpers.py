"""Shared fixtures for the F20 part 2 tests (F20 design 3.4 to 3.12, 4, 8.1; part 2 contract).

Written from F20 design version 1.3 and the part 2 contract, sections P1 to P9,
before the code exists. Black-box, as F07's tests are: the engine runs as a
subprocess through ``flow_helpers.run_engine``, on clones of bare origins.

What this module adds to ``flow_helpers``:

- ``TeamFakes``: the fake gh of ``flow_helpers`` that also serves an open PR's
  description (``body``), both inside ``gh pr list --state open`` entries and
  for ``gh pr view <n> --json <fields>``, so a change PR's ``Affects:`` line
  can be read however the engine asks for it (contract P2).
- Team worktrees made by hand as ``team start`` makes them (part 1a),
  role records, the plan file ``<common git folder>/troy-mode/plan.json``
  written in the contract's shape (P1), and a private origin a test may push to.
- An architecture with a module table in section 3 (the table troy-check
  reads for R07), for ``plan``'s module check and ``merge-check``'s plan check.

Contract corrections from the coordinator, applied here and in the tests:
every next entry keys its kind as ``action`` (with every key of F07's next
entry, unset ones null), and ``plan``/``team-start`` add ``items``; a feature
with a merged stage and no team worktree is under way in the home checkout and
stays out of ``may_start`` and ``needs_plan``; the home ``next`` is replaced only
where today's rule gives a stage 1 (or a team feature's entry); and
``merge-check``'s ``outside-plan`` checks source paths only, never tests.
"""

from __future__ import annotations

import itertools
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence

import flow_helpers
from flow_helpers import (
    CHANGE_PREFIX, FIVE, NEXT_KEYS, PROJECT, WORK_BRANCH, Fakes, Feature, FlowCase, Outcome,
    Project, front_matter, git, new_dir, origin_repo, pr, write_file,
)

TEAMS = ".troy-teams"
EXCLUDE_LINE = "/.troy-teams/"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
F06 = Feature("F06", "Sort output")
SIX = (*FIVE, F06)
KEYS = NEXT_KEYS
_NAMES = itertools.count(1)

# ----------------------------------------------------------------- fake gh

_VIEW_OLD = ('        found = {"comments": data.get("comments", {}).get(args[2], []),\n'
             '                 "reviews": data.get("reviews", {}).get(args[2], [])}\n')
_VIEW_NEW = _VIEW_OLD + (
    '        for entry in data.get("prs", []) + data.get("all_prs", []):\n'
    '            if str(entry.get("number")) == args[2]:\n'
    '                for key, value in entry.items():\n'
    '                    found.setdefault(key, value)\n'
    '        found.setdefault("body", "")\n')
if _VIEW_OLD not in flow_helpers._FAKE_SOURCE:
    raise RuntimeError("flow_helpers' fake gh changed: teams2_helpers cannot add PR bodies")
_TEAM_SOURCE = flow_helpers._FAKE_SOURCE.replace(_VIEW_OLD, _VIEW_NEW)


def _launcher(folder: Path, name: str, log: Path, data: Path) -> Path:
    """Writes the fake gh with PR bodies: a POSIX script, or a ``.bat`` on Windows.

    Args:
        folder: The folder that goes first on the PATH.
        name: ``gh``.
        log: The call log.
        data: The JSON file the fake answers from.

    Returns:
        The launcher's path.
    """
    source = (_TEAM_SOURCE.replace("@LOG@", repr(str(log))).replace("@DATA@", repr(str(data)))
              .replace("@KIND@", repr(name)))
    if os.name == "nt":
        script = folder / f"fake_{name}.py"
        script.write_text(source, encoding="utf-8")
        path = folder / f"{name}.bat"
        path.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n'
                        "exit /b %ERRORLEVEL%\r\n", encoding="utf-8")
        return path
    path = folder / name
    path.write_text(f"#!{sys.executable}\n{source}", encoding="utf-8")
    path.chmod(0o755)
    return path


class TeamFakes(Fakes):
    """``flow_helpers.Fakes`` whose gh also serves each open PR's ``body``.

    An open PR entry may carry ``body``. ``gh pr list --state open`` prints the
    entries as given; ``gh pr view <n> --json <fields>`` answers the fields
    asked for from the comments, the reviews, and the PR's own entry, with
    ``body`` "" when the entry has none. ``gh pr list --state all`` gives the
    open PRs with their bodies too, unless ``all_prs`` is passed.
    """

    def __init__(self, prs: Sequence[Mapping] = (), comments: Optional[Mapping] = None,
                 **kwargs) -> None:
        """Writes the launchers and the answers, then replaces gh with the body-serving one."""
        if "all_prs" not in kwargs:
            kwargs["all_prs"] = ([{**dict(item), "state": "OPEN"} for item in prs]
                                 + [{"number": item["number"], "title": item["title"],
                                     "state": "MERGED", "url": item.get("url", "")}
                                    for item in kwargs.get("merged", ())])
        super().__init__(prs, comments, **kwargs)
        self.gh = _launcher(self.folder, "gh", self._gh_log, self._data)


def change_pr(number: int, summary: str, affects: Optional[Sequence[str]]) -> dict:
    """An open ``[docs] Change the requirements: <summary>`` PR with its description.

    Args:
        number: The PR number.
        summary: The title's summary.
        affects: The IDs of the description's ``Affects:`` line, or None for no line.

    Returns:
        The ``gh pr list`` entry with ``body``.
    """
    body = "## Summary for Troy\n\nThe change adds a count of blank lines.\n\n"
    if affects is not None:
        body += f"Affects: {', '.join(affects)}\n\n"
    body += "## Checks\n\nNone yet.\n"
    entry = pr(number, CHANGE_PREFIX + summary, "troy-mode/change-requirements")
    entry["body"] = body
    return entry


def with_body(entry: Mapping, body: str) -> dict:
    """A ``gh pr list`` entry with a description."""
    return {**dict(entry), "body": body}


# --------------------------------------------------------------- documents

MODULES = (
    ("counter", ("src/wordcount/counter/**",), ("src/wordcount/counter/__init__.py",), ()),
    ("cli", ("src/wordcount/cli/**",), ("src/wordcount/cli/__init__.py",), ("counter",)),
    ("watcher", ("src/wordcount/watcher/**",), ("src/wordcount/watcher/__init__.py",),
     ("counter",)),
    ("report", ("src/wordcount/report/**",), ("src/wordcount/report/__init__.py",),
     ("counter",)),
)


def architecture_with_modules(modules: Sequence = MODULES, version: str = "1.0") -> str:
    """The English architecture with the module table under ``## 3.`` (F03 design 7, R07).

    Args:
        modules: Rows ``(name, owns patterns, interface patterns, may depend on)``.
        version: The front matter's version.

    Returns:
        The document text.
    """
    def cell(patterns) -> str:
        """Backticked patterns joined by commas."""
        return ", ".join(f"`{p}`" for p in patterns)
    rows = "".join(f"| {name} | {cell(owns)} | {cell(interfaces)} | "
                   f"{', '.join(deps) or 'None'} |\n"
                   for name, owns, interfaces, deps in modules)
    return (front_matter("architecture", "en", version, "architecture.zh-CN.md")
            + f"# {PROJECT} architecture\n\n## 1. Overview\n\nA command-line tool.\n\n"
            "## 2. Language\n\nPython.\n\n## 3. Modules\n\n"
            "| Module | Owns | External interfaces | May depend on |\n"
            "| --- | --- | --- | --- |\n" + rows
            + "\n## 4. Data model\n\nText in, counts out.\n")


# ------------------------------------------------------------------- teams

def common_git(project: Project) -> Path:
    """The repository's common git folder (``git rev-parse --git-common-dir``)."""
    return Path(project.git("rev-parse", "--path-format=absolute", "--git-common-dir").strip())


def git_dir_of(tree: Path) -> Path:
    """A checkout's own git folder."""
    return Path(git(tree, "rev-parse", "--absolute-git-dir").strip())


def team_path(project: Project, item: str) -> Path:
    """``<home>/.troy-teams/<id>``, the ID in lower case."""
    return project.root / TEAMS / item.lower()


def add_team(project: Project, item: str) -> Path:
    """Makes a team's worktree by hand, as ``team start`` does (part 1a), and returns it."""
    exclude = common_git(project) / "info" / "exclude"
    lines = exclude.read_text(encoding="utf-8").splitlines() if exclude.exists() else []
    if EXCLUDE_LINE not in lines:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text("\n".join(lines + [EXCLUDE_LINE]) + "\n", encoding="utf-8")
    tree = team_path(project, item)
    project.git("worktree", "add", "-q", "--detach", str(tree), "origin/main")
    return tree


def stamp(seconds: float = 0) -> str:
    """The UTC time now, moved by some seconds, as ``YYYY-MM-DDTHH:MM:SSZ``."""
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime(TIME_FORMAT)


def write_record(git_dir: Path, agent_id: str, role: str, started: str, stopped=None,
                 background=(), worktree=None) -> dict:
    """Writes a role record (F05 design 6.1, F20 3.3) into a git folder and returns it."""
    record = {"agent_id": agent_id, "agent_type": f"tstack:troy-{role}", "session": "s1",
              "started": started, "stopped": stopped, "background": list(background),
              "paths": {}}
    if worktree is not None:
        record.update(team=Path(worktree).name.upper(), worktree=str(worktree))
    folder = git_dir / "troy-mode" / "agents"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{agent_id}.json").write_text(json.dumps(record), encoding="utf-8")
    return record


def plan_path(project: Project) -> Path:
    """``<common git folder>/troy-mode/plan.json`` (contract P1)."""
    return common_git(project) / "troy-mode" / "plan.json"


def plan_entry(modules=("counter",), interfaces=(), documents=()) -> dict:
    """One feature of ``plan.json``."""
    return {"modules": list(modules), "interfaces": list(interfaces),
            "documents": list(documents)}


def write_plan(project: Project, ids: Sequence[str], orders: Sequence[tuple] = (),
               entries: Optional[Mapping[str, dict]] = None) -> dict:
    """Writes ``plan.json`` in the contract's shape, at origin/main, and returns it.

    Args:
        project: The clone.
        ids: The features with a feature line; each gets its own interface.
        orders: ``(feature, after, stage)`` triples.
        entries: Features whose entry the test chooses, replacing the default.

    Returns:
        The data written.
    """
    features = {fid: plan_entry(("counter",), (f"{fid.lower()}_api",)) for fid in ids}
    features.update(entries or {})
    data = {"commit": project.git("rev-parse", "origin/main").strip(), "features": features,
            "orders": [{"feature": f, "after": a, "stage": s} for f, a, s in orders]}
    path = plan_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


def team_commit(project: Project, tree: Path, title: str, files: Mapping[str, str],
                base: str = "origin/main") -> str:
    """Commits files on a new branch in a worktree, made from ``base``; returns the commit.

    Args:
        project: The clone.
        tree: The worktree.
        title: The commit's subject, the PR title (R01).
        files: Paths mapped to content.
        base: The commit the branch starts at.

    Returns:
        The new HEAD's full ID.
    """
    branch = f"troy-mode/t{next(_NAMES)}"
    git(tree, "switch", "-q", "-c", branch, base)
    for rel, content in files.items():
        write_file(tree, rel, content)
    git(tree, "add", "-A")
    git(tree, "commit", "-q", "-m", title)
    return git(tree, "rev-parse", "HEAD").strip()


class PrivateClone(Project):
    """A clone of a private bare origin, which a test may push to."""

    def __init__(self, steps) -> None:
        """Copies the cached origin of the steps into a new bare origin and clones it."""
        folder = new_dir("p2origin")
        self.origin = folder / "origin.git"
        git(folder, "clone", "-q", "--bare", str(origin_repo(steps)), str(self.origin))
        self.tmp = new_dir("p2case")
        self.root = self.tmp / PROJECT
        git(self.tmp, "clone", "-q", str(self.origin), PROJECT)
        self.git("switch", "-q", "-c", WORK_BRANCH, "origin/main")

    def land(self, subject: str, files: Mapping[str, str]) -> str:
        """Pushes one commit onto the origin's main from a side clone, fetches, returns it."""
        side = new_dir("p2land")
        git(side, "clone", "-q", str(self.origin), "c")
        for rel, content in files.items():
            write_file(side / "c", rel, content)
        git(side / "c", "add", "-A")
        git(side / "c", "commit", "-q", "-m", subject)
        git(side / "c", "push", "-q", "origin", "HEAD:main")
        self.git("fetch", "-q", "origin")
        return self.git("rev-parse", "origin/main").strip()


# ----------------------------------------------------------------- running

def status_of(project: Project, prs: Sequence[Mapping] = (), comments_by_pr=None,
              extra: Sequence[str] = (), fakes: Optional[TeamFakes] = None, **kwargs) -> Outcome:
    """Runs ``status --json`` on the home checkout with a body-serving fake gh."""
    fakes = fakes if fakes is not None else TeamFakes(prs, comments_by_pr, **kwargs)
    return project.run("status", *extra, fakes=fakes)


class TeamsCase(FlowCase):
    """Assertions shared by the part 2 tests. It has no tests of its own."""

    def need(self, report: dict, key: str):
        """Asserts that the report has a key and returns its value."""
        self.assertIsInstance(report, dict)
        self.assertIn(key, report, f"no {key!r} in the report: {json.dumps(report)[:2500]}")
        return report[key]

    def assert_entry(self, entry, action: str, **expected) -> None:
        """Asserts a next entry: its ``action``, every key of F07's entry, and given values.

        Args:
            entry: The entry.
            action: The expected ``action``.
            **expected: Keys mapped to their values; ``step`` is never checked.
        """
        self.assertIsInstance(entry, dict, entry)
        self.assertEqual(action, entry.get("action"), json.dumps(entry))
        for key in KEYS:
            self.assertIn(key, entry, f"next entry without {key!r}: {json.dumps(entry)}")
        for key, value in expected.items():
            self.assertEqual(value, entry.get(key), f"{key} in {json.dumps(entry)}")

    def team(self, report: dict, item: str) -> dict:
        """The ``teams`` entry of one feature."""
        teams = self.need(report, "teams")
        self.assertIsInstance(teams, list, teams)
        found = [t for t in teams if str(t.get("id", "")).upper() == item]
        self.assertEqual(1, len(found), json.dumps(teams)[:3000])
        return found[0]

    def team_ids(self, report: dict) -> list:
        """The IDs of ``teams``, in order, upper case."""
        teams = self.need(report, "teams")
        self.assertIsInstance(teams, list, teams)
        return [str(t.get("id", "")).upper() for t in teams]

    def kinds(self, report: dict) -> list:
        """The sorted kinds of a report's problems, each asserted to have a message."""
        problems = self.need(report, "problems")
        for problem in problems:
            self.assertIsInstance(problem.get("kind"), str, problem)
            self.assertIsInstance(problem.get("message"), str, problem)
            self.assertTrue(problem["message"].strip(), problem)
        return sorted(p["kind"] for p in problems)

    def message_of(self, report: dict, kind: str) -> str:
        """The messages of every problem of one kind, joined."""
        return "\n".join(p.get("message", "") for p in report.get("problems", [])
                         if p.get("kind") == kind)
