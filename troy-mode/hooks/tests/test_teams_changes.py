"""Teams group, part 1a: file tools, changes, records across worktrees, and team-busy.

Written from F20 design version 1.1 (sections 3.2 and 3.3) and the part 1a contract,
sections A4 (file tools), A5, A7, and A8, before the code exists. The fixtures are
test_teams_hooks.py's.

- A4: a team role's Edit, Write, and NotebookEdit are checked against its worktree,
  with the config at the worktree's HEAD and the shared documents out of every scope;
  the home checkout and other teams' worktrees are refused; a home role's write in a
  team's worktree names the team.
- A5: a team role's change detection runs in its worktree; changes in the home
  checkout or in another team's worktree never reach it; an unknown role's
  PostToolUse and SubagentStop print and write nothing.
- A7: the main session's TaskStop, SessionEnd, and SessionStart act on every git
  folder of the repository.
- A8: the main session's git writes and file writes in a team worktree whose git
  folder holds an open record are refused with rule ``team-busy``.

Planted bugs of design 8.2 (part 1a) caught in this file:

- A team role's Write into the home checkout allowed:
  FileToolTests.test_write_in_the_home_checkout_or_another_team_is_refused.
- Change detection run in the home checkout:
  ChangeTests.test_home_and_other_team_changes_are_never_reported and
  test_change_outside_the_scope_in_the_worktree_blocks_with_its_relative_path.
- A record looked up only in the home checkout's git folder:
  MainSessionRecordTests.test_task_stop_with_an_agent_id_closes_a_team_record and
  test_task_stop_with_a_task_id_removes_it_from_the_team_record.
- SessionEnd closing only the home checkout's records:
  MainSessionRecordTests.test_session_end_closes_the_sessions_records_in_every_git_folder.
- team-busy checking only the main session's cd and not -C:
  TeamBusyTests.test_git_writes_with_dash_c_in_a_busy_worktree_are_refused.

Planted bugs named here: the team's config read at the home checkout's HEAD,
FileToolTests.test_config_comes_from_the_worktree_head; the shared documents left in a
team's scope, FileToolTests.test_shared_documents_are_out_of_every_team_scope;
SessionStart cleaning only the home git folder, MainSessionRecordTests.test_session_
start_cleans_every_git_folder; team-busy for a closed record or another team,
TeamBusyTests.test_the_same_calls_pass_once_the_records_are_closed and
test_the_same_calls_pass_in_a_team_that_is_not_busy.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -p "test_teams_*.py" -v
"""

import unittest

from hook_helpers import (
    HOOK_TEMP, LOG_TIME, MAIN, PAD, TIME_FORMAT, home_probe, q, run_git, run_many, shell_task,
    write_file,
)
from test_teams_hooks import (
    FILE_TOOLS, OLD_STOPPED, WIDE_CONFIG, TeamCase, log_entry, new_role, set_age, team_record,
    utc_now,
)

TEST_BODY = "def test_new():\n    assert True\n"
DAY = 24 * 60 * 60
# The git subcommands of contract A8 that write, each with arguments.
GIT_WRITES = (
    "add -A", "commit -m 'Add x'", "switch -c troy-mode/f08-3-mock", "checkout -b side",
    "restore src/pkg/app.py", "reset --hard", "rebase origin/main", "merge main", "stash",
    "stash push -m wip", "clean -fd", "rm src/pkg/app.py", "mv README.md README.txt",
    "cherry-pick abc1234", "am fix.mbox", "apply fix.patch",
)
GIT_READS = ("status", "diff", "log --oneline -3", "stash list", "stash show")


class FileToolTests(TeamCase):
    """Contract A4: Edit, Write, and NotebookEdit of team roles and home roles."""

    def test_write_in_its_worktree_is_checked_by_scope(self):
        """In its worktree the Developer may change source, not tests; refusals go to its log."""
        repo = self.make_repo()
        dev, te, cr = (repo.team_role(n) for n in ("developer", "test-engineer", "code-reviewer"))
        for caller in (dev, te, cr):
            repo.first_call(caller)
        tree = repo.tree()
        for tool in FILE_TOOLS:
            with self.subTest(tool=tool):
                name = "src/pkg/x.ipynb" if tool == "NotebookEdit" else "src/pkg/app.py"
                self.assert_silent(repo.write(dev, tree / name, tool=tool).run())
                test = "tests/x.ipynb" if tool == "NotebookEdit" else "tests/test_app.py"
                self.assert_denied(repo.write(dev, tree / test, tool=tool).run(), test, "tests",
                                   "needs-answer")
                last = self.last_line(repo, repo.team_state())
                self.assertEqual(("scope", [test]), (last.get("rule"), last.get("paths")))
        self.assert_silent(repo.write(te, tree / "tests/test_app.py").run())
        self.assert_denied(repo.write(cr, tree / "src/pkg/app.py").run(), "src/pkg/app.py")
        self.assert_nothing_at_home(repo)

    def test_config_comes_from_the_worktree_head(self):
        """A team's scopes come from the config committed at its worktree's HEAD.

        f08 commits a dependencies pattern for tests/data/**; f09 only writes it; the
        home checkout commits it after the worktrees exist in a second repository.

        Planted bug named here: the team's config read at the home checkout's HEAD.
        """
        repo = self.make_repo(teams=("f08", "f09"))
        write_file(repo.tree("f08"), ".troy-mode/config.toml", WIDE_CONFIG)
        run_git(repo.tree("f08"), "add", "-A")
        run_git(repo.tree("f08"), "-c", "core.hooksPath=/dev/null", "commit", "-q", "--no-verify",
                "-m", "Widen")
        write_file(repo.tree("f09"), ".troy-mode/config.toml", WIDE_CONFIG)
        fixture = "tests/data/fixture.json"
        self.assert_silent(repo.write(repo.team_role("developer", "f08"),
                                      repo.tree("f08") / fixture).run())
        self.assert_denied(repo.write(repo.team_role("developer", "f09"),
                                      repo.tree("f09") / fixture).run(), fixture, "tests")
        self.assert_denied(repo.write(repo.home_role("developer"), repo.home / fixture).run(),
                           fixture, "tests")
        later = self.make_repo()
        later.project.write(".troy-mode/config.toml", WIDE_CONFIG)
        later.project.commit_all("Widen at home")
        self.assert_denied(later.write(later.team_role("developer"), later.tree() / fixture).run(),
                           fixture, "tests")
        self.assert_silent(later.write(later.home_role("developer"), later.home / fixture).run())

    def test_shared_documents_are_out_of_every_team_scope(self):
        """In a team, the requirements, the architecture, ADRs, and version test plans are refused.

        Each refusal has rule scope. The Architect's and Test Manager's own design and
        test plan paths stay allowed (D277).

        Planted bug named here: the shared documents left in a team's scope.
        """
        repo = self.make_repo()
        cases = {
            "architect": ("docs/architecture.md", "docs/architecture.zh-CN.md",
                          "docs/adr/0001-storage.md", "docs/requirements.md"),
            "test-manager": ("docs/versions/v1.0/test-plan.md", "docs/requirements.zh-CN.md"),
            "interface-designer": ("docs/requirements.md",),
            "developer": ("docs/requirements.md", "docs/architecture.md"),
            "test-engineer": ("docs/requirements.md",),
        }
        callers = {name: repo.team_role(name) for name in cases}
        for caller in callers.values():
            repo.first_call(caller)
        pairs = [(name, rel) for name, paths in cases.items() for rel in paths]
        outs = run_many([repo.write(callers[name], repo.tree() / rel) for name, rel in pairs])
        for (name, rel), out in zip(pairs, outs):
            with self.subTest(role=name, path=rel):
                self.assert_denied(out, rel)
        rules = {line.get("rule") for line in repo.log_lines(repo.team_state())}
        self.assertEqual({"scope"}, rules)
        for name, rel in (("architect", "docs/features/F08/design.md"),
                          ("test-manager", "docs/features/F08/test-plan.md")):
            with self.subTest(role=name, path=rel, allowed=True):
                self.assert_silent(repo.write(callers[name], repo.tree() / rel).run())

    def test_shared_documents_stay_open_in_the_home_checkout(self):
        """Pair: home roles may still change the architecture, ADRs, and version test plans."""
        repo = self.make_repo()
        for name, rel in (("architect", "docs/architecture.md"),
                          ("architect", "docs/adr/0001-storage.md"),
                          ("test-manager", "docs/versions/v1.0/test-plan.md")):
            with self.subTest(role=name, path=rel):
                self.assert_silent(repo.write(repo.home_role(name), repo.home / rel).run())

    def test_worktree_git_file_and_git_folders_are_refused(self):
        """The worktree's ``.git`` file, its git folder, and the common one are refused."""
        repo = self.make_repo()
        dev = repo.team_role("developer")
        repo.first_call(dev)
        for path in (repo.tree() / ".git", repo.tree_git_dir() / "troy-mode" / "agents" / "x.json",
                     repo.tree_git_dir() / "HEAD", repo.project.git_dir / "config"):
            with self.subTest(path=str(path)):
                self.assert_denied(repo.write(dev, path).run())

    def test_write_in_the_home_checkout_or_another_team_is_refused(self):
        """A team role's write in the home checkout or in team f09's worktree: rule scope.

        The reason says ``You work in the checkout <worktree>``, and the line goes to the
        team's log.

        Planted bug caught: a team role's Write into the home checkout allowed (8.2).
        """
        repo = self.make_repo(teams=("f08", "f09"))
        dev = repo.team_role("developer")
        repo.first_call(dev)
        targets = (repo.home / "src/pkg/app.py", repo.home / "README.md",
                   repo.tree("f09") / "src/pkg/app.py")
        for target in targets:
            for tool in FILE_TOOLS:
                with self.subTest(path=str(target), tool=tool):
                    out = repo.write(dev, target, tool=tool).run()
                    self.assert_names_checkout(out, repo.tree())
                    self.assertEqual("scope", self.last_line(repo, repo.team_state()).get("rule"))
        self.assert_nothing_at_home(repo)

    def test_temp_folder_and_scratchpad_are_allowed(self):
        """A team role may write in the temp folder and the scratchpad, not in the home folder."""
        repo = self.make_repo()
        dev = repo.team_role("developer")
        repo.first_call(dev)
        self.assert_silent(repo.write(dev, HOOK_TEMP / "copy" / "notes.txt").run())
        self.assert_silent(repo.write(dev, PAD / "notes.txt", scratchpad=PAD).run())
        probe = home_probe()
        if probe is not None:
            self.assert_denied(repo.write(dev, probe).run())

    def test_home_role_write_in_a_team_worktree_names_the_team(self):
        """A home role's write inside a team's worktree: rule scope, ``belongs to team F08``."""
        repo = self.make_repo(teams=("f08", "f09"))
        dev = repo.home_role("developer")
        repo.first_call(dev)
        for team in ("f08", "f09"):
            for tool in FILE_TOOLS:
                with self.subTest(team=team, tool=tool):
                    out = repo.write(dev, repo.tree(team) / "src/pkg/app.py", tool=tool).run()
                    self.assert_denied(out, f"belongs to team {team.upper()}")
                    self.assertEqual("scope", self.last_line(repo, repo.home_state()).get("rule"))
        self.assert_silent(repo.write(dev, repo.home / "src/pkg/app.py").run())


class ChangeTests(TeamCase):
    """Contract A5: change detection, background tasks, and the stop of a team role."""

    def test_change_outside_the_scope_in_the_worktree_blocks_with_its_relative_path(self):
        """A team Developer's new test file in its worktree blocks with the worktree-relative path.

        The block's log line goes to the team's log; the home checkout's log stays empty.

        Planted bug caught: change detection run in the home checkout (8.2).
        """
        repo = self.make_repo()
        dev = repo.team_role("developer")
        repo.first_call(dev)
        write_file(repo.tree(), "tests/test_new.py", TEST_BODY)
        self.assert_blocked(repo.post(dev).run(), "tests/test_new.py", "delete",
                            absent=(".troy-teams",))
        last = self.last_line(repo, repo.team_state())
        self.assertEqual(("changes", "block", ["tests/test_new.py"]),
                         (last.get("rule"), last.get("decision"), last.get("paths")))
        self.assert_nothing_at_home(repo)

    def test_tracked_file_changed_in_the_worktree_names_git_restore(self):
        """A changed tracked test file in the worktree is named with ``git restore -- <path>``."""
        repo = self.make_repo()
        dev = repo.team_role("developer")
        repo.first_call(dev)
        write_file(repo.tree(), "tests/test_app.py", TEST_BODY)
        self.assert_blocked(repo.post(dev).run(), "git restore -- tests/test_app.py")

    def test_home_and_other_team_changes_are_never_reported(self):
        """Changes in the home checkout and in team f09's worktree never reach team f08's role.

        Its PostToolUse and its stop are silent, and its record is stopped.

        Planted bug caught: change detection run in the home checkout (8.2).
        """
        repo = self.make_repo(teams=("f08", "f09"))
        dev = repo.team_role("developer")
        repo.first_call(dev)
        repo.project.write("tests/test_home.py", TEST_BODY)
        repo.project.write("docs/requirements.md", "# Changed at home\n")
        write_file(repo.tree("f09"), "tests/test_other.py", TEST_BODY)
        write_file(repo.tree("f09"), "docs/architecture.md", "# Changed by f09\n")
        write_file(repo.tree(), "src/pkg/new_module.py", "X = 1\n")
        self.assert_silent(repo.post(dev).run())
        self.assert_silent(repo.stop(dev, tasks=[]).run())
        record = self.record_of(repo, repo.team_state(), dev.agent_id)
        self.assertRegex(record.get("stopped") or "", LOG_TIME, record)
        for state in repo.states().values():
            self.assertEqual([], repo.log_lines(state), state)

    def test_home_role_is_not_blamed_for_a_teams_change(self):
        """A home Developer is not told of a change in a team's worktree; a home change blocks."""
        repo = self.make_repo()
        dev = repo.home_role("developer")
        repo.first_call(dev)
        write_file(repo.tree(), "tests/test_team.py", TEST_BODY)
        self.assert_silent(repo.post(dev).run())
        repo.project.write("tests/test_home.py", TEST_BODY)
        self.assert_blocked(repo.post(dev).run(), "tests/test_home.py", absent=("test_team.py",))

    def test_shared_document_change_blocks_a_team_role(self):
        """A team Architect's change to the architecture or an ADR blocks; its design does not.

        Pair: the home Architect's same change is silent.
        """
        repo = self.make_repo()
        architect = repo.team_role("architect")
        repo.first_call(architect)
        write_file(repo.tree(), "docs/architecture.md", "# Changed\n")
        write_file(repo.tree(), "docs/adr/0001-storage.md", "# ADR 1\n")
        write_file(repo.tree(), "docs/features/F08/design.md", "# F08 design\n")
        self.assert_blocked(repo.post(architect).run(), "docs/architecture.md",
                            "docs/adr/0001-storage.md", absent=("docs/features/F08/design.md",))
        home = repo.home_role("architect")
        repo.first_call(home)
        repo.project.write("docs/architecture.md", "# Changed at home\n")
        self.assert_silent(repo.post(home).run())

    def test_background_task_goes_to_the_team_record(self):
        """A team role's background command goes into its record in the team's git folder."""
        repo = self.make_repo()
        te = repo.team_role("test-engineer")
        repo.first_call(te)
        out = repo.post(te, task="bbbnne1ji").run()
        self.assertEqual(0, out.code, out.describe())
        self.assertIn("bbbnne1ji", out.stdout, out.describe())
        self.assertEqual(["bbbnne1ji"],
                         self.record_of(repo, repo.team_state(), te.agent_id).get("background"))
        self.assert_nothing_at_home(repo)

    def test_subagent_stop_marks_the_team_record_stopped(self):
        """The stop blocks once for a change outside the scope, then marks the team record stopped.

        Both log lines, the block and the stop's ``changes`` line, go to the team's log.
        """
        repo = self.make_repo()
        dev = repo.team_role("developer")
        repo.first_call(dev)
        write_file(repo.tree(), "tests/test_new.py", TEST_BODY)
        self.assert_blocked(repo.stop(dev).run(), "tests/test_new.py")
        self.assertIsNone(self.record_of(repo, repo.team_state(), dev.agent_id).get("stopped"))
        self.assert_not_blocked(repo.stop(dev, active=True).run())
        record = self.record_of(repo, repo.team_state(), dev.agent_id)
        self.assertRegex(record.get("stopped") or "", LOG_TIME, record)
        self.assertEqual([("changes", "block"), ("changes", "stop")],
                         [(line.get("rule"), line.get("decision"))
                          for line in repo.log_lines(repo.team_state())])
        self.assert_nothing_at_home(repo)

    def test_unknown_role_post_and_stop_print_and_write_nothing(self):
        """A role with no transcript and no record: PostToolUse and SubagentStop are silent.

        Changes lie in the home checkout and in the worktree, and a command moved to
        the background; still no record and no log line appear anywhere.
        """
        repo = self.make_repo()
        dev = repo.unknown_role("developer")
        repo.project.write("tests/test_home.py", TEST_BODY)
        write_file(repo.tree(), "tests/test_team.py", TEST_BODY)
        self.assert_silent(repo.post(dev).run())
        self.assert_silent(repo.post(dev, task="t-unknown").run())
        self.assert_silent(repo.stop(dev, tasks=[shell_task("t-unknown")]).run())
        for state in repo.states().values():
            self.assertEqual([], repo.record_names(state), state)
            self.assertEqual([], repo.log_lines(state), state)


class MainSessionRecordTests(TeamCase):
    """Contract A7: TaskStop, SessionEnd, and SessionStart over every git folder."""

    def test_task_stop_with_an_agent_id_closes_a_team_record(self):
        """The main session's TaskStop of a team role's agent ID closes its record, silently.

        Planted bug caught: a record looked up only in the home checkout's git folder (8.2).
        """
        repo = self.make_repo()
        te = repo.team_role("test-engineer")
        repo.first_call(te)
        repo.post(te, task="t1").run()
        self.assert_silent(repo.task_stop(te.agent_id).run())
        record = self.record_of(repo, repo.team_state(), te.agent_id)
        self.assertRegex(record.get("stopped") or "", LOG_TIME, record)
        self.assertEqual([], record.get("background"))
        self.assertEqual([], repo.record_names(repo.home_state()))

    def test_task_stop_with_a_task_id_removes_it_from_the_team_record(self):
        """A task ID is removed from whichever record holds it, the team's or the home's.

        Planted bug caught: a record looked up only in the home checkout's git folder (8.2).
        """
        repo = self.make_repo()
        team_te = new_role("test-engineer")
        repo.write_record(repo.team_state(), team_record(team_te, repo.tree(),
                                                         background=["t1", "t2"]))
        home_te = new_role("test-engineer")
        repo.write_record(repo.home_state(), team_record(home_te, None, background=["t3"]))
        self.assert_silent(repo.task_stop("t1").run())
        team = self.record_of(repo, repo.team_state(), team_te.agent_id)
        self.assertEqual((None, ["t2"]), (team.get("stopped"), team.get("background")))
        home = self.record_of(repo, repo.home_state(), home_te.agent_id)
        self.assertEqual(["t3"], home["background"])
        self.assert_silent(repo.task_stop("t3").run())
        home = self.record_of(repo, repo.home_state(), home_te.agent_id)
        self.assertEqual([], home["background"])
        team = self.record_of(repo, repo.team_state(), team_te.agent_id)
        self.assertEqual(["t2"], team["background"])

    def test_session_end_closes_the_sessions_records_in_every_git_folder(self):
        """SessionEnd closes the ending session's records at home, in f08, and in f09; no other's.

        Planted bug caught: SessionEnd closing only the home checkout's records (8.2).
        """
        repo = self.make_repo(teams=("f08", "f09"))
        ending, other = "session-ending", "session-other"
        mine = {
            "home": team_record(new_role("developer"), None, session=ending),
            "f08": team_record(new_role("test-engineer"), repo.tree("f08"), session=ending,
                               background=["t8"]),
            "f09": team_record(new_role("developer"), repo.tree("f09"), "F09", session=ending,
                               stopped=OLD_STOPPED, background=["t9"]),
        }
        states = repo.states()
        for where, record in mine.items():
            repo.write_record(states[where], record)
        theirs = team_record(new_role("developer"), repo.tree("f08"), session=other,
                             background=["t0"])
        repo.write_record(states["f08"], theirs)
        self.assert_silent(repo.session_end(ending).run())
        for where, record in mine.items():
            with self.subTest(where=where):
                now = self.record_of(repo, states[where], record["agent_id"])
                self.assertRegex(now.get("stopped") or "", LOG_TIME, now)
                self.assertEqual([], now.get("background"), now)
        self.assertEqual(OLD_STOPPED, self.record_of(repo, states["f09"], mine["f09"]["agent_id"])
                         ["stopped"])
        self.assertEqual(theirs, self.record_of(repo, states["f08"], theirs["agent_id"]))

    def test_session_start_cleans_every_git_folder(self):
        """SessionStart removes old records and old log lines at home, in f08, and in f09.

        A record file two days old goes and one an hour old stays; a log line 40 days
        old goes and one a day old stays (log_days is 30 by default).

        Planted bug named here: SessionStart cleaning only the home git folder.
        """
        repo = self.make_repo(teams=("f08", "f09"))
        kept = {}
        now = utc_now().strftime(TIME_FORMAT)
        for where, state in repo.states().items():
            old = repo.write_record(state, team_record(new_role("developer"), None))
            set_age(old, 2 * DAY)
            fresh = team_record(new_role("developer"), None, started=now)
            repo.write_record(state, fresh)
            kept[where] = fresh["agent_id"] + ".json"
            log = state / "hooks.log"
            log.write_text(log_entry(40 * DAY, f"old-{where}") + "\n"
                           + log_entry(DAY, f"new-{where}") + "\n", encoding="utf-8")
        self.assertEqual(0, repo.session_start().run().code)
        for where, state in repo.states().items():
            with self.subTest(where=where):
                self.assertEqual([kept[where]], repo.record_names(state))
                self.assertEqual([f"new-{where}"],
                                 [line.get("agent_id") for line in repo.log_lines(state)])


class TeamBusyTests(TeamCase):
    """Contract A8: the main session in a team worktree whose git folder holds an open record."""

    def setUp(self):
        """Teams f08, busy with an open Developer record, and f09 with none."""
        self.repo = self.make_repo(teams=("f08", "f09"))
        self.busy = new_role("developer")
        self.record = team_record(self.busy, self.repo.tree("f08"))
        self.repo.write_record(self.repo.team_state("f08"), self.record)

    def tree(self, team="f08"):
        """A team worktree, quoted for a shell command."""
        return q(self.repo.tree(team))

    def assert_busy(self, out, msg=""):
        """Asserts a team-busy refusal that names F08 and the open agent ID."""
        self.assert_denied(out, "F08", self.busy.agent_id, msg=msg)

    def test_git_writes_with_dash_c_in_a_busy_worktree_are_refused(self):
        """Each git write of contract A8 with ``-C <worktree>`` is refused with rule team-busy.

        Planted bug caught: team-busy checking only the main session's cd and not -C (8.2).
        """
        calls = [self.repo.bash(MAIN, f"git -C {self.tree()} {words}") for words in GIT_WRITES]
        for words, out in zip(GIT_WRITES, run_many(calls)):
            with self.subTest(command=words):
                self.assert_busy(out)
        self.repo.bash(MAIN, f"git -C {self.tree()} commit -m 'Add x'").run()
        self.assertEqual("team-busy", self.last_line(self.repo, self.repo.home_state()).get("rule"))

    def test_every_way_of_naming_the_folder(self):
        """``--git-dir``, ``--work-tree``, an earlier ``cd``, a subfolder, PowerShell, ``cwd``."""
        tree = self.repo.tree()
        cases = {
            "--git-dir": self.repo.bash(MAIN, f"git --git-dir={q(tree / '.git')} commit -m x"),
            "--work-tree": self.repo.bash(MAIN, f"git --work-tree={self.tree()} add -A"),
            "cd": self.repo.bash(MAIN, f"cd {self.tree()} && git commit -m x"),
            "subfolder": self.repo.bash(MAIN, f"git -C {q(tree / 'src')} add ."),
            "PowerShell": self.repo.bash(MAIN, f"git -C '{tree}' reset --hard", tool="PowerShell"),
            "cwd": self.repo.bash(MAIN, "git commit -m x", cwd=tree),
        }
        for name, call in cases.items():
            with self.subTest(case=name):
                self.assert_busy(call.run())

    def test_file_writes_in_a_busy_worktree_are_refused(self):
        """The main session's Write, Edit, and NotebookEdit in the busy worktree are refused."""
        for tool in ("Write", "Edit", "NotebookEdit"):
            with self.subTest(tool=tool):
                out = self.repo.write(MAIN, self.repo.tree() / "src/pkg/app.py", tool=tool).run()
                self.assert_busy(out)
                self.assertEqual("team-busy",
                                 self.last_line(self.repo, self.repo.home_state()).get("rule"))

    def test_stopped_record_with_a_task_keeps_the_team_busy(self):
        """A stopped record whose background holds a task is still open: refused."""
        self.record.update(stopped=OLD_STOPPED, background=["t1"])
        self.repo.write_record(self.repo.team_state(), self.record)
        self.assert_busy(self.repo.bash(MAIN, f"git -C {self.tree()} add -A").run())

    def test_reads_and_read_only_git_commands_pass(self):
        """``status``, ``diff``, ``log``, ``stash list``, ``stash show``, and reads are silent."""
        tree = self.repo.tree()
        calls = [self.repo.bash(MAIN, f"git -C {self.tree()} {words}") for words in GIT_READS]
        calls += [self.repo.pre(MAIN, "Read", {"file_path": str(tree / "README.md")}),
                  self.repo.bash(MAIN, f"cat {q(tree / 'README.md')}"),
                  self.repo.pre(MAIN, "Glob", {"pattern": "**/*.py", "path": str(tree)})]
        for call, out in zip(calls, run_many(calls)):
            with self.subTest(input=call.payload["tool_input"]):
                self.assert_silent(out)

    def test_the_same_calls_pass_in_a_team_that_is_not_busy(self):
        """While f08 is busy, the same git writes and file writes in f09 are silent.

        Planted bug named here: team-busy for another team.
        """
        calls = [self.repo.bash(MAIN, f"git -C {self.tree('f09')} {words}")
                 for words in ("add -A", "commit -m 'Add x'", "restore src/pkg/app.py", "stash")]
        calls.append(self.repo.write(MAIN, self.repo.tree("f09") / "src/pkg/app.py"))
        for call, out in zip(calls, run_many(calls)):
            with self.subTest(input=call.payload["tool_input"]):
                self.assert_silent(out)

    def test_the_same_calls_pass_once_the_records_are_closed(self):
        """With f08's record stopped and nothing in background, the same calls are silent.

        Planted bug named here: team-busy for a closed record.
        """
        self.record.update(stopped=OLD_STOPPED, background=[])
        self.repo.write_record(self.repo.team_state(), self.record)
        calls = [self.repo.bash(MAIN, f"git -C {self.tree()} {words}")
                 for words in ("add -A", "commit -m 'Add x'", "switch -c troy-mode/f08-3-mock",
                               "reset --hard", "stash")]
        calls.append(self.repo.write(MAIN, self.repo.tree() / "src/pkg/app.py"))
        for call, out in zip(calls, run_many(calls)):
            with self.subTest(input=call.payload["tool_input"]):
                self.assert_silent(out)

    def test_home_checkout_writes_are_not_team_busy(self):
        """The main session's git writes and Write in the home checkout pass while f08 is busy."""
        calls = [self.repo.bash(MAIN, "git add -A"),
                 self.repo.bash(MAIN, f"git -C {q(self.repo.home)} restore README.md"),
                 self.repo.write(MAIN, self.repo.home / "src/pkg/app.py")]
        for call, out in zip(calls, run_many(calls)):
            with self.subTest(input=call.payload["tool_input"]):
                self.assert_silent(out)


if __name__ == "__main__":
    unittest.main()
