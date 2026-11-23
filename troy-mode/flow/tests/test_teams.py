"""Teams group, part 1a, engine side (F20 design 3.1, 3.3, 4, 8.1; part 1a contract B).

Written from F20 design version 1.1 and the part 1a contract, sections B1 to B3,
before the code exists. Black-box, as F07's tests are: each test clones a bare origin
built by flow_helpers, runs ``troy_flow.py team <start|end> --item <ID> --repo <clone>
--json`` or ``snapshot``/``check-run --repo <team worktree> --json``, and checks the
report, the exit code, git's worktrees, ``.git/info/exclude``, and the files under
the git folders.

- The report of ``team`` has ``command`` ``team``, ``action``, ``ok``, ``item``,
  ``worktree`` (an absolute path or null), ``problems`` (each with ``kind`` and
  ``message``), and ``notes``; ``team end`` adds ``archived`` and, for ``running``,
  ``stop``. Exit 0 when done, 1 when a problem stops it, 2 when the engine cannot run.
- ``team end`` tests need ``origin/main`` to gain the feature's ``6/6 accept`` after
  the worktree exists. They use a private bare origin per test (``TeamClone``), push
  the acceptance commit there, and fetch, so the engine sees it whether it fetches
  or not.
- The ``team end`` and ``snapshot``/``check-run`` tests make the team worktree by hand,
  as ``team start`` does (``git worktree add --detach <home>/.troy-teams/<id>
  origin/main`` and the exclude line), so they do not depend on ``team start``.
- Role records are written by hand with the keys of F05 design 6.1 (as
  test_running_work.py does) into the git folder the test names.

Planted bugs of design 8.2 (part 1a) caught here:

- ``snapshot`` of team A refusing for team B's record:
  TeamRunTests.test_snapshot_passes_while_another_teams_record_is_open and
  test_records_of_the_home_checkout_and_the_teams_are_apart.
- ``team end`` removing the worktree before it archives the log:
  EndTests.test_archives_the_log_then_removes_the_worktree.
- A stale lock never taken over (for ``team end``'s append):
  EndTests.test_stale_lock_on_the_common_log_is_taken_over.

Planted bugs named here: the exclude line written for every team,
StartTests.test_exclude_line_is_written_once_for_two_teams; the worktree made at the
local HEAD or acceptance read from local commits, StartTests.test_start_makes_the_
worktree_detached_at_origin_main and test_only_origin_main_is_read; a soft dependency
ignored, StartTests.test_dependency_without_acceptance_is_named; ``check-run`` of a team
reading the home checkout's status, TeamRunTests.test_check_run_lists_only_its_worktrees_
changes; ``hooks_log`` of a team reading the home log, TeamRunTests.test_hooks_log_holds_
only_this_teams_lines.

Run from the repository root:
python -m unittest discover -s troy-mode/flow/tests -p "test_teams.py" -v
"""

import json
import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flow_helpers import (
    F01, F02, F05, FIVE, PROJECT, REQUIREMENTS, WORK_BRANCH, Fakes, Feature, FlowCase,
    Project, base_files, base_step, git, git_proc, hooks_line, new_dir, origin_repo,
    problem_kinds, requirements_text, run_engine, same_path, stages, write_file,
)

TEAMS = ".troy-teams"
EXCLUDE_LINE = "/.troy-teams/"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
F06 = Feature("F06", "Sort output")
# F01 accepted, F02 at 2/6: F03 (soft on F01) and F05 may start, F04 (hard on F02) may not.
ORIGIN_A = (base_step(base_files(FIVE)), *stages(F01, 6), *stages(F02, 2))
# F01 at 5/6: F02 (hard on F01) and F03 (soft on F01) may not start, F05 may.
ORIGIN_B = (base_step(base_files(FIVE)), *stages(F01, 5))
# F05 at 5/6, for team end: its 6/6 lands on the private origin after the worktree exists.
ORIGIN_C = (base_step(base_files(FIVE)), *stages(F05, 5))
ACCEPT_F05 = "[F05 6/6 accept] Watch folders (#46)"


def team_path(project: Project, item: str) -> Path:
    """``<home>/.troy-teams/<id>``, the ID in lower case."""
    return project.root / TEAMS / item.lower()


def exclude_file(project: Project) -> Path:
    """The common git folder's ``info/exclude``."""
    return project.root / ".git" / "info" / "exclude"


def exclude_lines(project: Project) -> list:
    """The exclude file's lines, or None when it does not exist."""
    path = exclude_file(project)
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else None


def worktree_paths(project: Project) -> list:
    """The paths ``git worktree list --porcelain`` gives, the home checkout first."""
    out = project.git("worktree", "list", "--porcelain")
    return [line[len("worktree "):] for line in out.splitlines() if line.startswith("worktree ")]


def registered(project: Project, path: Path) -> bool:
    """Whether git lists a worktree at the path."""
    return any(same_path(item, path) for item in worktree_paths(project))


def git_dir_of(tree: Path) -> Path:
    """A checkout's own git folder."""
    return Path(git(tree, "rev-parse", "--absolute-git-dir").strip())


def add_team(project: Project, item: str) -> Path:
    """Makes a team's worktree by hand, as ``team start`` does, and returns it."""
    lines = exclude_lines(project) or []
    if EXCLUDE_LINE not in lines:
        exclude_file(project).parent.mkdir(parents=True, exist_ok=True)
        exclude_file(project).write_text("\n".join(lines + [EXCLUDE_LINE]) + "\n", encoding="utf-8")
    tree = team_path(project, item)
    project.git("worktree", "add", "-q", "--detach", str(tree), "origin/main")
    return tree


def stamp(seconds: float = 0) -> str:
    """The UTC time now, moved by some seconds, as ``YYYY-MM-DDTHH:MM:SSZ``."""
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime(TIME_FORMAT)


def shifted(time_text: str, seconds: int) -> str:
    """A ``YYYY-MM-DDTHH:MM:SSZ`` time moved by some seconds."""
    when = datetime.strptime(time_text, TIME_FORMAT).replace(tzinfo=timezone.utc)
    return (when + timedelta(seconds=seconds)).strftime(TIME_FORMAT)


def write_record(git_dir: Path, agent_id: str, role: str, started: str, stopped=None,
                 background=(), session: str = "s1", worktree=None) -> dict:
    """Writes a role record (F05 design 6.1) into a git folder and returns it."""
    record = {"agent_id": agent_id, "agent_type": f"tstack:troy-{role}", "session": session,
              "started": started, "stopped": stopped, "background": list(background),
              "paths": {}}
    if worktree is not None:
        record.update(team=Path(worktree).name.upper(), worktree=str(worktree))
    folder = git_dir / "troy-mode" / "agents"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{agent_id}.json").write_text(json.dumps(record), encoding="utf-8")
    return record


def log_path(git_dir: Path) -> Path:
    """``<git folder>/troy-mode/hooks.log``."""
    return git_dir / "troy-mode" / "hooks.log"


def write_log(git_dir: Path, lines) -> bytes:
    """Writes a hooks.log of JSON lines and returns its bytes."""
    path = log_path(git_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(line) + "\n" for line in lines).encode("utf-8")
    path.write_bytes(data)
    return data


def log_bytes(git_dir: Path):
    """A hooks.log's bytes, or None when it does not exist."""
    path = log_path(git_dir)
    return path.read_bytes() if path.exists() else None


class TeamClone(Project):
    """A clone of a private bare origin, which a test may push to."""

    def __init__(self, steps) -> None:
        """Copies the cached origin of the steps into a new bare origin and clones it."""
        folder = new_dir("teamorigin")
        self.origin = folder / "origin.git"
        git(folder, "clone", "-q", "--bare", str(origin_repo(steps)), str(self.origin))
        self.tmp = new_dir("teamcase")
        self.root = self.tmp / PROJECT
        git(self.tmp, "clone", "-q", str(self.origin), PROJECT)
        self.git("switch", "-q", "-c", WORK_BRANCH, "origin/main")

    def land(self, subject: str, files: dict) -> None:
        """Pushes one commit onto the origin's main from a side clone, then fetches."""
        side = new_dir("land")
        git(side, "clone", "-q", str(self.origin), "c")
        for rel, content in files.items():
            write_file(side / "c", rel, content)
        git(side / "c", "add", "-A")
        git(side / "c", "commit", "-q", "-m", subject)
        git(side / "c", "push", "-q", "origin", "HEAD:main")
        self.git("fetch", "-q", "origin")


class TeamCase(FlowCase):
    """Engine runs and assertions for the team tests. It has no tests of its own."""

    def team(self, project: Project, action: str, item: str, fakes=None, json_report=True,
             repo=None):
        """Runs ``team <action> --item <ID> --repo <clone>``."""
        args = ["team", action, "--item", item, "--repo", repo or project.root]
        if json_report:
            args.append("--json")
        return run_engine(args, project.tmp, fakes)

    def team_report(self, out, code: int, action: str, item: str) -> dict:
        """Asserts the exit code and the team report's keys (contract B), and returns it."""
        report = self.report_of(out, code, "team")
        self.assertEqual(action, report.get("action"), out.describe())
        self.assertEqual(item, report.get("item"), out.describe())
        self.assertIn("worktree", report, out.describe())
        if report["worktree"] is not None:
            self.assertIsInstance(report["worktree"], str)
            self.assertTrue(os.path.isabs(report["worktree"]), report["worktree"])
        for problem in report["problems"]:
            self.assertIsInstance(problem.get("kind"), str, problem)
            self.assertIsInstance(problem.get("message"), str, problem)
            self.assertTrue(problem["message"].strip(), problem)
        return report

    def assert_kinds(self, report: dict, kinds) -> None:
        """Asserts the problems' kinds, sorted."""
        self.assertEqual(sorted(kinds), sorted(p["kind"] for p in report["problems"]),
                         json.dumps(report)[:3000])

    def assert_nothing_made(self, project: Project, item: str, exclude_before) -> None:
        """Asserts no worktree for the item, no folder, and an unchanged exclude file."""
        tree = team_path(project, item)
        self.assertFalse(registered(project, tree), worktree_paths(project))
        self.assertFalse(tree.exists(), tree)
        self.assertEqual(exclude_before, exclude_lines(project))


class StartTests(TeamCase):
    """Contract B1: ``team start``."""

    def test_start_makes_the_worktree_detached_at_origin_main(self):
        """The worktree is ``<home>/.troy-teams/f05``, detached at origin/main, not at local HEAD.

        The exclude file gains ``/.troy-teams/`` once, the home checkout's status and
        branch do not change, and gh is never called.

        Planted bug named here: the worktree made at the local HEAD.
        """
        project = Project(ORIGIN_A)
        local = project.commit("Local work", {"notes.md": "# Notes\n"})
        fakes = Fakes(fail=True)
        report = self.team_report(self.team(project, "start", "F05", fakes), 0, "start", "F05")
        tree = team_path(project, "F05")
        self.assertTrue(same_path(report["worktree"], tree), report["worktree"])
        self.assertTrue(registered(project, tree), worktree_paths(project))
        self.assertEqual(project.git("rev-parse", "origin/main").strip(),
                         git(tree, "rev-parse", "HEAD").strip())
        self.assertNotEqual(0, git_proc(tree, "symbolic-ref", "-q", "HEAD").returncode,
                            "the worktree is not detached")
        self.assertEqual("", git(tree, "status", "--porcelain", "--untracked-files=all"))
        self.assertEqual((local, WORK_BRANCH), (project.head(), project.branch()))
        self.assertEqual([], project.status_lines())
        self.assertEqual(1, exclude_lines(project).count(EXCLUDE_LINE))
        self.assertEqual([], fakes.gh_calls())

    def test_exclude_line_is_written_once_for_two_teams(self):
        """Two teams started: both worktrees, one exclude line, a clean home status.

        Planted bug named here: the exclude line written for every team.
        """
        project = Project(ORIGIN_A)
        for item in ("F05", "F03"):
            with self.subTest(item=item):
                self.team_report(self.team(project, "start", item), 0, "start", item)
                self.assertTrue(registered(project, team_path(project, item)))
        self.assertEqual(1, exclude_lines(project).count(EXCLUDE_LINE))
        self.assertEqual([], project.status_lines())

    def test_exclude_file_is_created_when_missing(self):
        """With no ``info/exclude``, ``team start`` creates it with the line."""
        project = Project(ORIGIN_A)
        if exclude_file(project).exists():
            exclude_file(project).unlink()
        self.team_report(self.team(project, "start", "F05"), 0, "start", "F05")
        self.assertEqual(1, exclude_lines(project).count(EXCLUDE_LINE))
        self.assertEqual([], project.status_lines())

    def test_exclude_line_already_there_is_kept_once(self):
        """An exclude file that already has the line keeps its other lines and the line once."""
        project = Project(ORIGIN_A)
        exclude_file(project).write_text("# mine\n*.tmp\n/.troy-teams/\n", encoding="utf-8")
        self.team_report(self.team(project, "start", "F05"), 0, "start", "F05")
        lines = exclude_lines(project)
        self.assertEqual(1, lines.count(EXCLUDE_LINE))
        self.assertIn("# mine", lines)
        self.assertIn("*.tmp", lines)

    def test_problems_stop_and_make_nothing(self):
        """``unknown``, ``accepted``, and ``dependency``: exit 1, worktree null, nothing made."""
        project = Project(ORIGIN_A)
        before = exclude_lines(project)
        for item, kind, named in (("F99", "unknown", "F99"), ("F01", "accepted", "F01"),
                                  ("F04", "dependency", "F02")):
            with self.subTest(item=item):
                report = self.team_report(self.team(project, "start", item), 1, "start", item)
                self.assert_kinds(report, [kind])
                self.assertIn(named, report["problems"][0]["message"])
                self.assertIsNone(report["worktree"])
                self.assert_nothing_made(project, item, before)

    def test_dependency_without_acceptance_is_named(self):
        """With F01 at 5/6, F02 (hard) and F03 (soft) are refused, naming F01; F05 starts.

        Planted bug named here: a soft dependency ignored.
        """
        project = Project(ORIGIN_B)
        before = exclude_lines(project)
        for item in ("F02", "F03"):
            with self.subTest(item=item):
                report = self.team_report(self.team(project, "start", item), 1, "start", item)
                self.assert_kinds(report, ["dependency"])
                self.assertIn("F01", report["problems"][0]["message"])
                self.assert_nothing_made(project, item, before)
        self.team_report(self.team(project, "start", "F05"), 0, "start", "F05")

    def test_existing_team_worktree_is_refused(self):
        """A second start of F05: ``exists``, exit 1; the worktree and one exclude line stay."""
        project = Project(ORIGIN_A)
        self.team_report(self.team(project, "start", "F05"), 0, "start", "F05")
        tree = team_path(project, "F05")
        write_file(tree, "src/wordcount/wip.py", '"""Work in progress."""\n')
        report = self.team_report(self.team(project, "start", "F05"), 1, "start", "F05")
        self.assert_kinds(report, ["exists"])
        self.assertTrue(registered(project, tree))
        self.assertTrue((tree / "src/wordcount/wip.py").is_file())
        self.assertEqual(1, exclude_lines(project).count(EXCLUDE_LINE))

    def test_only_origin_main_is_read(self):
        """Local commits change nothing: F02's local 6/6 does not free F04, a local F06 is unknown.

        Planted bug named here: acceptance read from local commits.
        """
        project = Project(ORIGIN_A)
        project.commit("[F02 6/6 accept] Count lines",
                       {REQUIREMENTS: requirements_text((*FIVE, F06)),
                        f"{F02.folder}/acceptance.md": "# F02 accepted\n"})
        before = exclude_lines(project)
        report = self.team_report(self.team(project, "start", "F04"), 1, "start", "F04")
        self.assert_kinds(report, ["dependency"])
        self.assertIn("F02", report["problems"][0]["message"])
        report = self.team_report(self.team(project, "start", "F06"), 1, "start", "F06")
        self.assert_kinds(report, ["unknown"])
        self.assert_nothing_made(project, "F06", before)

    def test_repo_subfolder_puts_the_worktree_under_the_top_folder(self):
        """``--repo <home>/src`` makes the worktree under the home checkout's top folder."""
        project = Project(ORIGIN_A)
        out = self.team(project, "start", "F05", repo=project.root / "src")
        report = self.team_report(out, 0, "start", "F05")
        self.assertTrue(same_path(report["worktree"], team_path(project, "F05")))
        self.assertTrue(registered(project, team_path(project, "F05")))

    def test_text_output_and_bad_arguments(self):
        """Without ``--json`` the exit codes hold; a missing ``--item`` or action exits 2."""
        project = Project(ORIGIN_A)
        self.assert_exit(self.team(project, "start", "F05", json_report=False), 0)
        self.assert_exit(self.team(project, "start", "F05", json_report=False), 1)
        self.assert_exit(run_engine(["team", "start", "--repo", project.root, "--json"],
                                    project.tmp), 2)
        self.assert_exit(run_engine(["team", "stop", "--item", "F05", "--repo", project.root,
                                     "--json"], project.tmp), 2)


class EndTests(TeamCase):
    """Contract B2: ``team end``."""

    def setUp(self):
        """A private clone with F05 at 5/6, its team worktree, and a common log of two lines."""
        self.project = TeamClone(ORIGIN_C)
        self.tree = add_team(self.project, "F05")
        self.team_git = git_dir_of(self.tree)
        self.home_git = self.project.root / ".git"
        self.old = [hooks_line(stamp(-600), None, None, path="docs/a.md"),
                    hooks_line(stamp(-300), "tstack:troy-developer", "a0", path="tests/b.py")]
        self.common = write_log(self.home_git, self.old)
        self.lines = [hooks_line(stamp(-200), "tstack:troy-developer", "a1", path="tests/x.py"),
                      hooks_line(stamp(-100), "tstack:troy-test-engineer", "a2",
                                 path="src/wordcount/y.py"),
                      hooks_line(stamp(-50), "tstack:troy-developer", "a1", rule="git")]

    def accept(self):
        """Lands F05's ``6/6 accept`` (a squash subject) on the origin's main."""
        self.project.land(ACCEPT_F05, {f"{F05.folder}/acceptance.md": "# F05 accepted\n"})

    def assert_refused(self, kind: str) -> dict:
        """Runs ``team end``, asserts exit 1 with one problem, nothing removed or appended."""
        report = self.team_report(self.team(self.project, "end", "F05"), 1, "end", "F05")
        self.assert_kinds(report, [kind])
        self.assertTrue(registered(self.project, self.tree))
        self.assertTrue(self.tree.is_dir())
        self.assertEqual(self.common, log_bytes(self.home_git))
        return report

    def test_missing_team_is_reported(self):
        """No worktree for F03, or only a plain folder at ``.troy-teams/f03``: ``missing``."""
        report = self.team_report(self.team(self.project, "end", "F03"), 1, "end", "F03")
        self.assert_kinds(report, ["missing"])
        (team_path(self.project, "F03") / "src").mkdir(parents=True)
        report = self.team_report(self.team(self.project, "end", "F03"), 1, "end", "F03")
        self.assert_kinds(report, ["missing"])
        self.assertEqual(self.common, log_bytes(self.home_git))

    def test_not_accepted_refuses_and_changes_nothing(self):
        """F05 without its 6/6 on origin/main: ``not-accepted``; the team's log is kept too."""
        team_log = write_log(self.team_git, self.lines)
        self.assert_refused("not-accepted")
        self.assertEqual(team_log, log_bytes(self.team_git))

    def test_changes_refuse_the_end(self):
        """An untracked, a changed, a staged, or a deleted file in the worktree: ``changes``."""
        self.accept()
        write_log(self.team_git, self.lines)
        cases = {
            "untracked": lambda: write_file(self.tree, "notes.txt", "x\n"),
            "untracked in a new folder": lambda: write_file(self.tree, "src/wordcount/new/x.py",
                                                            "x = 1\n"),
            "changed": lambda: write_file(self.tree, "README.md", "# changed\n"),
            "staged": lambda: (write_file(self.tree, "src/wordcount/s.py", "s = 1\n"),
                               git(self.tree, "add", "src/wordcount/s.py")),
            "deleted": lambda: (self.tree / "README.md").unlink(),
        }
        for name, change in cases.items():
            with self.subTest(change=name):
                change()
                self.assert_refused("changes")
                git(self.tree, "reset", "-q", "--hard")
                git(self.tree, "clean", "-q", "-fd")

    def test_open_record_refuses_with_running(self):
        """Records not stopped, or stopped with a task: ``running``, IDs sorted in ``stop``."""
        self.accept()
        write_record(self.team_git, "b-te", "test-engineer", stamp(-60), stopped=stamp(-30),
                     background=["bbbnne1ji"], worktree=self.tree)
        write_record(self.team_git, "a-dev", "developer", stamp(-60), worktree=self.tree)
        write_record(self.team_git, "c-done", "developer", stamp(-90), stopped=stamp(-80),
                     worktree=self.tree)
        report = self.assert_refused("running")
        self.assertEqual(["a-dev", "b-te"], report.get("stop"))

    def test_archives_the_log_then_removes_the_worktree(self):
        """Accepted, clean, records closed: the team's lines follow the common log's, then it goes.

        ``archived`` is 3, the worktree's folder and git folder are gone, and git no
        longer lists it.

        Planted bug caught: team end removing the worktree before it archives the log (8.2).
        """
        self.accept()
        write_log(self.team_git, self.lines)
        write_record(self.team_git, "c-done", "developer", stamp(-90), stopped=stamp(-80),
                     worktree=self.tree)
        report = self.team_report(self.team(self.project, "end", "F05"), 0, "end", "F05")
        self.assertEqual(3, report.get("archived"))
        text = log_bytes(self.home_git).decode("utf-8")
        self.assertEqual(self.old + self.lines,
                         [json.loads(line) for line in text.splitlines() if line.strip()])
        self.assertFalse(self.tree.exists(), self.tree)
        self.assertFalse(self.team_git.exists(), self.team_git)
        self.assertFalse(registered(self.project, self.tree), worktree_paths(self.project))

    def test_ignored_files_do_not_stop_the_end(self):
        """``__pycache__`` and ``reports/`` in the worktree, ignored by git: the end goes ahead."""
        self.accept()
        write_file(self.tree, "src/wordcount/__pycache__/f05.cpython-313.pyc", b"\x00\x01")
        write_file(self.tree, "reports/junit.xml", "<testsuites/>\n")
        self.team_report(self.team(self.project, "end", "F05"), 0, "end", "F05")
        self.assertFalse(self.tree.exists(), self.tree)
        self.assertFalse(registered(self.project, self.tree))

    def test_end_without_a_team_log_archives_nothing(self):
        """No team log: ``archived`` 0 and the common log unchanged."""
        self.accept()
        report = self.team_report(self.team(self.project, "end", "F05"), 0, "end", "F05")
        self.assertEqual(0, report.get("archived"))
        self.assertEqual(self.common, log_bytes(self.home_git))
        self.assertFalse(self.tree.exists())

    def test_stale_lock_on_the_common_log_is_taken_over(self):
        """A lock an hour old beside the common log is taken over: lines appended, lock gone.

        Planted bug caught: a stale lock never taken over (8.2).
        """
        self.accept()
        write_log(self.team_git, self.lines)
        lock = log_path(self.home_git).with_name("hooks.log.lock")
        lock.write_bytes(b"")
        old = time.time() - 3600
        os.utime(lock, (old, old))
        report = self.team_report(self.team(self.project, "end", "F05"), 0, "end", "F05")
        self.assertEqual(3, report.get("archived"))
        self.assertFalse(lock.exists(), "the stale lock is still there")
        text = log_bytes(self.home_git).decode("utf-8")
        self.assertEqual(5, len([line for line in text.splitlines() if line.strip()]))


class TeamRunTests(TeamCase):
    """Contract B3: ``snapshot`` and ``check-run`` with ``--repo <team worktree>``."""

    def setUp(self):
        """A clone with teams f05 and f03 made by hand."""
        self.project = Project(ORIGIN_A)
        self.trees = {item: add_team(self.project, item) for item in ("F05", "F03")}
        self.gits = {item: git_dir_of(tree) for item, tree in self.trees.items()}
        self.gits["home"] = self.project.root / ".git"

    def snapshot(self, where: str, role: str = "developer"):
        """Runs ``snapshot --role <role> --repo <checkout>``."""
        repo = self.project.root if where == "home" else self.trees[where]
        return run_engine(["snapshot", "--role", role, "--repo", repo, "--json"], self.project.tmp)

    def check(self, where: str, run: str):
        """Runs ``check-run --run <run> --repo <checkout>``."""
        repo = self.project.root if where == "home" else self.trees[where]
        return run_engine(["check-run", "--run", run, "--repo", repo, "--json"], self.project.tmp)

    def flow_records(self, where: str) -> list:
        """The run records' names in a git folder."""
        folder = self.gits[where] / "troy-mode" / "flow"
        return sorted(p.stem for p in folder.glob("*.json")) if folder.is_dir() else []

    def test_snapshot_passes_while_another_teams_record_is_open(self):
        """Team F03's open record does not stop team F05's snapshot; its run record is F05's.

        Planted bug caught: snapshot of team A refusing for team B's record (8.2).
        """
        write_record(self.gits["F03"], "b-dev", "developer", stamp(-60), worktree=self.trees["F03"])
        report = self.report_of(self.snapshot("F05"), 0, "snapshot")
        self.assertEqual([], report.get("stop"))
        self.assertEqual([report["run"]], self.flow_records("F05"))
        self.assertEqual([], self.flow_records("home"))
        self.assertEqual([], self.flow_records("F03"))

    def test_snapshot_refuses_while_its_own_teams_record_is_open(self):
        """Team F05's own open record refuses its snapshot with ``running``."""
        write_record(self.gits["F05"], "a-dev", "developer", stamp(-60), worktree=self.trees["F05"])
        report = self.report_of(self.snapshot("F05"), 1, "snapshot")
        self.assertIsNone(report.get("run"))
        self.assertEqual([("running", None)], problem_kinds(report))
        self.assertEqual(["a-dev"], report.get("stop"))
        self.assertEqual([], self.flow_records("F05"))

    def test_records_of_the_home_checkout_and_the_teams_are_apart(self):
        """A home record does not stop a team's snapshot; a team record does not stop the home's.

        Planted bug caught: snapshot of team A refusing for team B's record (8.2).
        """
        home = write_record(self.gits["home"], "h-dev", "developer", stamp(-60))
        self.report_of(self.snapshot("F05"), 0, "snapshot")
        (self.gits["home"] / "troy-mode" / "agents" / f"{home['agent_id']}.json").unlink()
        write_record(self.gits["F05"], "a-dev", "developer", stamp(-60), worktree=self.trees["F05"])
        self.report_of(self.snapshot("home"), 0, "snapshot")

    def test_check_run_lists_only_its_worktrees_changes(self):
        """Changes in the home checkout and in team F03, and their open records, are not F05's.

        Planted bug named here: check-run of a team reading the home checkout's status.
        """
        snap = self.report_of(self.snapshot("F05"), 0, "snapshot")
        write_file(self.trees["F05"], "src/wordcount/f05_new.py", '"""F05."""\n')
        self.project.write("src/wordcount/home.py", '"""Home."""\n')
        self.project.write("README.md", "# changed at home\n")
        write_file(self.trees["F03"], "src/wordcount/f03_new.py", '"""F03."""\n')
        write_file(self.trees["F03"], "tests/test_f03.py", '"""F03 tests."""\n')
        later = shifted(snap["time"], 5)
        write_record(self.gits["F03"], "b-dev", "developer", later, worktree=self.trees["F03"])
        write_record(self.gits["home"], "h-dev", "developer", later)
        report = self.report_of(self.check("F05", snap["run"]), 0, "check-run")
        self.assertEqual([], report["problems"])
        self.assertEqual(["src/wordcount/f05_new.py"], report["stage"])
        self.assertEqual(["src/wordcount/f05_new.py"], sorted(c["path"] for c in report["changed"]))
        self.assertEqual([], report.get("stop"))

    def test_hooks_log_holds_only_this_teams_lines(self):
        """The same role's lines in F03's and the home checkout's logs are not F05's run's.

        Planted bug named here: hooks_log of a team reading the home log.
        """
        snap = self.report_of(self.snapshot("F05"), 0, "snapshot")
        dev = "tstack:troy-developer"
        mine = hooks_line(shifted(snap["time"], 5), dev, "a1", path="tests/a.py")
        write_log(self.gits["F05"], [mine])
        write_log(self.gits["F03"], [hooks_line(shifted(snap["time"], 6), dev, "b1",
                                                path="tests/b.py")])
        write_log(self.gits["home"], [hooks_line(shifted(snap["time"], 7), dev, "h1",
                                                 path="tests/h.py")])
        report = self.report_of(self.check("F05", snap["run"]), 0, "check-run")
        self.assertEqual([mine], report["hooks_log"])


if __name__ == "__main__":
    unittest.main()
