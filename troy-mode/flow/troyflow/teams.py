"""team start and team end: a feature team's worktree (F20 design 3.1 and 4).

A team works in the linked worktree <home>/.troy-teams/<id>, detached at
origin/main when it starts. When the feature is accepted, its hooks.log lines
go to the common git folder's log, so the retrospective keeps them, and the
worktree is removed (D269). Part 1a starts a feature once its dependencies
are accepted; the Architect's plan and open changes come with part 2.
"""

import os
from pathlib import Path

from troycheck import gitio
from troyhook import locks
from troyhook import records as agents

from . import repo as git
from .errors import FlowError
from .repo import MAIN, Repo
from .requirements import parse_features
from .stages import merged_stages

TEAMS_FOLDER = ".troy-teams"
REQUIREMENTS = "docs/requirements.md"
EXCLUDE_LINE = f"/{TEAMS_FOLDER}/"


def _problem(kind: str, message: str) -> dict:
    """Builds one problem of the report."""
    return {"kind": kind, "message": message}


def _git_text(folder: Path, *args: str) -> str:
    """Runs git in a folder and returns its stdout."""
    return gitio.run_git(folder, *args).stdout.decode("utf-8", "replace")


def _key(path) -> str:
    """Makes a path comparable: real, and without case on Windows."""
    text = os.path.realpath(str(path))
    return text.lower() if os.name == "nt" else text


def common_dir(repo: Repo) -> Path:
    """Returns the git folder the repository's worktrees share."""
    return Path(_git_text(repo.root, "rev-parse", "--path-format=absolute",
                          "--git-common-dir").strip())


def worktrees(repo: Repo) -> list[Path]:
    """Lists the folders of the repository's worktrees, from git worktree list."""
    text = _git_text(repo.root, "worktree", "list", "--porcelain")
    return [Path(line[len("worktree "):]) for line in text.splitlines()
            if line.startswith("worktree ")]


def team_worktree(repo: Repo, item: str) -> Path | None:
    """Returns the team worktree of a feature, wherever it is, or None."""
    name = item.lower()
    return next((path for path in worktrees(repo)
                 if path.name.lower() == name and path.parent.name == TEAMS_FOLDER), None)


def _accepted(merged: dict[str, set[int]], fid: str) -> bool:
    """Tells whether a feature's 6/6 is merged on origin/main."""
    return 6 in merged.get(fid, set())


def _start_problems(repo: Repo, item: str) -> list[dict]:
    """Lists what stops a team from starting (F20 design 3.5, part 1a)."""
    if git.commit_of(repo, MAIN) is None:
        return [_problem("no-main", f"{MAIN} does not exist: fetch it first.")]
    features = parse_features(git.read(repo, MAIN, REQUIREMENTS)) or []
    feature = next((f for f in features if f.id == item), None)
    if feature is None:
        return [_problem("unknown", f"{item} is not in the features table on {MAIN}.")]
    merged = merged_stages(git.subjects(repo, MAIN))
    problems = []
    if _accepted(merged, item):
        problems.append(_problem("accepted", f"{item} is already accepted on {MAIN}."))
    for dep in [*feature.hard, *feature.soft]:
        if not _accepted(merged, dep):
            problems.append(_problem("dependency", f"{item} depends on {dep}, which is not "
                                     f"accepted on {MAIN} yet."))
    found = team_worktree(repo, item)
    if found is not None:
        problems.append(_problem("exists", f"team {item} already has its worktree {found}."))
    return problems


def _exclude(repo: Repo) -> None:
    """Adds /.troy-teams/ to the repository's info/exclude once."""
    path = common_dir(repo) / "info" / "exclude"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if EXCLUDE_LINE in (line.strip() for line in text.splitlines()):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    sep = "" if not text or text.endswith("\n") else "\n"
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{sep}{EXCLUDE_LINE}\n")


def start(repo: Repo, item: str) -> tuple[dict, int]:
    """Creates a team's worktree, detached at origin/main (F20 design 3.1)."""
    report = {"command": "team", "action": "start", "ok": False, "item": item,
              "worktree": None, "problems": _start_problems(repo, item), "notes": []}
    if report["problems"]:
        return report, 1
    folder = repo.root / TEAMS_FOLDER / item.lower()
    _exclude(repo)
    gitio.run_git(repo.root, "worktree", "add", "--detach", str(folder), MAIN)
    report.update(ok=True, worktree=os.path.realpath(folder))
    return report, 0


def _end_problems(repo: Repo, item: str, folder: Path, state: Path) -> tuple[list[dict], list]:
    """Lists what stops a team's worktree from going, and the agents still open."""
    problems = []
    merged = merged_stages(git.subjects(repo, MAIN)) if git.commit_of(repo, MAIN) else {}
    if not _accepted(merged, item):
        problems.append(_problem("not-accepted", f"{item} is not accepted on {MAIN}: its "
                                 "worktree stays until PR 6 merges."))
    changed = _git_text(folder, "status", "--porcelain", "--untracked-files=all").strip()
    if changed:
        problems.append(_problem("changes", f"team {item}'s worktree has changes: "
                                 f"{', '.join(line[3:] for line in changed.splitlines())}."))
    stop = [agents.agent_of(os.path.basename(path), record)
            for path, record in agents.read_all(str(state)) if agents.is_open(record)]
    if stop:
        problems.append(_problem("running", f"roles of team {item} may still run: "
                                 f"{', '.join(stop)}. End each with TaskStop first."))
    return problems, stop


def _archive(path: Path, lines: list[str]) -> None:
    """Appends a team's log lines to the common log under its lock (F20 design 3.3).

    Raises:
        OSError: The log cannot be written; the worktree then stays.
    """
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with locks.held(str(path)), open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(line + "\n" for line in lines))


def end(repo: Repo, item: str) -> tuple[dict, int]:
    """Archives a team's log lines and removes its worktree (F20 design 3.1, D269)."""
    report = {"command": "team", "action": "end", "ok": False, "item": item, "worktree": None,
              "problems": [], "notes": [], "archived": 0}
    folder = team_worktree(repo, item)
    if folder is None:
        report["problems"] = [_problem("missing", f"team {item} has no worktree.")]
        return report, 1
    report["worktree"] = os.path.realpath(folder)
    state = Path(_git_text(folder, "rev-parse", "--absolute-git-dir").strip()) / "troy-mode"
    problems, stop = _end_problems(repo, item, folder, state)
    if problems:
        report.update(problems=problems, stop=stop)
        return report, 1
    source = state / "hooks.log"
    lines = source.read_text(encoding="utf-8").splitlines() if source.is_file() else []
    lines = [line for line in lines if line.strip()]
    _archive(common_dir(repo) / "troy-mode" / "hooks.log", lines)
    gitio.run_git(repo.root, "worktree", "remove", str(folder))
    report.update(ok=True, archived=len(lines))
    return report, 0


def run_team(args) -> tuple[dict, int]:
    """Runs team start or team end for one feature.

    Raises:
        FlowError: The folder is not a repository, or the item is not an F ID.
    """
    item = (args.item or "").strip().upper()
    if not item.startswith("F") or not item[1:].isdigit():
        raise FlowError(f"{args.item!r} is not a feature ID such as F08")
    repo = git.need_repo(args.repo)
    return (start if args.action == "start" else end)(repo, item)
