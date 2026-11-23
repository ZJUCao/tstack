"""Teams group, part 1a: the log and record locks (F20 design 2, 3.3, D270; contract A6).

Written from F20 design version 1.1 and the part 1a contract, section A6, before the
code exists. The fixtures are test_teams_hooks.py's.

Every append to ``hooks.log``, and SessionStart's rewrite of it, holds
``hooks.log.lock`` in the same folder, and every read-change-save of a record holds
``<record path>.lock``: created exclusively, tried every 10 ms for up to a second, taken
over when more than 10 seconds old, and removed afterwards; after a second without it
the write goes ahead.

- Several hook processes at once (3 or 4 workers started together, each making 20
  calls one after another) keep every log line and every background task.
- A stale lock file (an hour old) is taken over and removed, so the call is not
  delayed. A fresh lock file that nobody releases delays a call by about a second,
  and the line or task is still written.

Delays are measured against the same call made twice without a lock just before: a
fresh lock must add at least 0.7 s and at most 3.5 s, and a stale one less than 3.5 s (its
take-over is proved by the lock file being gone).

Planted bugs of design 8.2 (part 1a) caught in this file:

- The log append without the lock:
  LogLockTests.test_fresh_log_lock_delays_about_a_second_and_still_writes and
  test_concurrent_refusals_keep_every_line.
- A stale lock never taken over: LogLockTests.test_stale_log_lock_is_taken_over and
  test_session_start_takes_the_log_lock;
  RecordLockTests.test_stale_record_lock_is_taken_over_by_every_update.

Planted bug named here: a record update without the lock,
RecordLockTests.test_fresh_record_lock_delays_about_a_second_and_still_records and
test_concurrent_background_tasks_keep_every_task.

Run from the repository root:
python -m unittest discover -s troy-mode/hooks/tests -p "test_teams_*.py" -v
"""

import threading
import time
import unittest
from pathlib import Path

from hook_helpers import MAIN, Call
from test_teams_hooks import TeamCase, TeamRepo, log_entry, new_role, set_age, team_record

LOG_LOCK = "hooks.log.lock"
CALLS = 20
STALE = 60 * 60
DAY = 24 * 60 * 60
MIN_DELAY = 0.7
MAX_DELAY = 3.5


def burst(groups: list) -> list:
    """Runs groups of calls at once, one thread per group, each group's calls in order.

    Every thread waits at a barrier first, so the hook processes start together.

    Args:
        groups: Lists of calls.

    Returns:
        The runs, group after group.
    """
    barrier = threading.Barrier(len(groups))
    results: list = [None] * len(groups)

    def work(index: int, calls: list) -> None:
        """Runs one group."""
        barrier.wait()
        results[index] = [call.run() for call in calls]

    threads = [threading.Thread(target=work, args=(i, calls)) for i, calls in enumerate(groups)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return [out for group in results for out in group]


def timed(call: Call) -> tuple:
    """Runs a call and returns ``(run, seconds)``."""
    began = time.perf_counter()
    out = call.run()
    return out, time.perf_counter() - began


def baseline(make_call) -> float:
    """The shorter of two runs of a fresh call, with no lock in the way."""
    return min(timed(make_call())[1] for _ in range(2))


def lock_files(folder: Path) -> list:
    """Every ``*.lock`` file under a folder, as sorted names."""
    return sorted(p.name for p in folder.rglob("*.lock")) if folder.is_dir() else []


def make_lock(path: Path, age: float = 0) -> Path:
    """Writes an empty lock file, an ``age`` seconds old."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    if age:
        set_age(path, age)
    return path


class LockCase(TeamCase):
    """A repository with team f08 and a started team Developer."""

    def setUp(self):
        """Builds the repository and makes the Developer's first call."""
        self.repo = self.make_repo()
        self.dev = self.repo.team_role("developer")
        self.repo.first_call(self.dev)

    def refusal(self, name: str = "notes.py") -> Call:
        """The Developer's write into the home checkout, refused and logged in the team's log."""
        return self.repo.write(self.dev, self.repo.home / "src" / "pkg" / name)

    def assert_delay(self, took: float, base: float, fresh: bool, msg: str = "") -> None:
        """Asserts about a second's delay over the baseline for a fresh lock, else none."""
        delay = took - base
        if fresh:
            self.assertGreaterEqual(delay, MIN_DELAY,
                                    f"{msg} no wait for a fresh lock: {delay:.2f} s")
            self.assertLessEqual(delay, MAX_DELAY, f"{msg} waited too long: {delay:.2f} s")
        else:
            # A stale lock's take-over is proved by the lock file being gone; the timing
            # only guards against a hang, so a slow CI runner cannot make it flaky.
            self.assertLess(delay, MAX_DELAY, f"{msg} a stale lock was waited for: {delay:.2f} s")


class LogLockTests(LockCase):
    """The log lock: concurrent appends, a stale lock, a fresh lock, and SessionStart."""

    def test_concurrent_refusals_keep_every_line(self):
        """Four workers make 20 refused calls each at once: 80 lines, each a JSON object.

        No lock file is left behind.

        Planted bug caught: the log append without the lock (8.2).
        """
        groups = [[self.refusal(f"w{w}_{i}.py") for i in range(CALLS)] for w in range(4)]
        for out in burst(groups):
            self.assert_denied(out)
        lines = self.repo.log_lines(self.repo.team_state())
        self.assertEqual(4 * CALLS, len(lines), f"{4 * CALLS - len(lines)} lines lost")
        self.assertEqual([], [line for line in lines if "unreadable" in line])
        self.assertEqual({("scope", self.dev.agent_id)},
                         {(line.get("rule"), line.get("agent_id")) for line in lines})
        self.assertEqual([], lock_files(self.repo.team_state()))

    def test_stale_log_lock_is_taken_over(self):
        """A lock an hour old beside the team's log and the home log is taken over and removed.

        The refused call is not delayed, and its line is written.

        Planted bug caught: a stale lock never taken over (8.2).
        """
        repo = self.repo
        cases = {"team log": (repo.team_state(), self.refusal),
                 "home log": (repo.home_state(),
                              lambda: repo.bash(MAIN, "git commit --no-verify -m 'Add x'"))}
        for name, (state, make_call) in cases.items():
            with self.subTest(log=name):
                base = baseline(make_call)
                lock = make_lock(state / LOG_LOCK, STALE)
                before = len(repo.log_lines(state))
                out, took = timed(make_call())
                self.assert_denied(out)
                self.assertEqual(before + 1, len(repo.log_lines(state)))
                self.assertFalse(lock.exists(), "the stale lock is still there")
                self.assert_delay(took, base, fresh=False, msg=name)

    def test_fresh_log_lock_delays_about_a_second_and_still_writes(self):
        """A fresh lock that nobody releases: the call waits about a second, then writes its line.

        Planted bug caught: the log append without the lock (8.2).
        """
        base = baseline(self.refusal)
        lock = make_lock(self.repo.team_state() / LOG_LOCK)
        self.addCleanup(lambda: lock.unlink() if lock.exists() else None)
        before = len(self.repo.log_lines(self.repo.team_state()))
        out, took = timed(self.refusal())
        self.assert_denied(out)
        self.assertEqual(before + 1, len(self.repo.log_lines(self.repo.team_state())))
        self.assert_delay(took, base, fresh=True)

    def test_session_start_takes_the_log_lock(self):
        """SessionStart's rewrite: stale locks are taken over; a fresh one delays it about a second.

        Each log holds a line 40 days old and one a day old; the old line goes either way.

        Planted bug caught: a stale lock never taken over (8.2).
        """
        repo = self.repo

        def fill() -> None:
            """Writes an old and a new line into the home log and the team's log."""
            for state in (repo.home_state(), repo.team_state()):
                state.mkdir(parents=True, exist_ok=True)
                (state / "hooks.log").write_text(log_entry(40 * DAY, "old") + "\n"
                                                 + log_entry(DAY, "new") + "\n", encoding="utf-8")

        def kept() -> list:
            """The agent IDs left in both logs."""
            return [[line.get("agent_id") for line in repo.log_lines(state)]
                    for state in (repo.home_state(), repo.team_state())]

        fill()
        locks = [make_lock(state / LOG_LOCK, STALE)
                 for state in (repo.home_state(), repo.team_state())]
        self.assertEqual(0, repo.session_start().run().code)
        self.assertEqual([["new"], ["new"]], kept())
        self.assertEqual([False, False], [lock.exists() for lock in locks])
        base = baseline(repo.session_start)
        fill()
        lock = make_lock(repo.home_state() / LOG_LOCK)
        self.addCleanup(lambda: lock.unlink() if lock.exists() else None)
        out, took = timed(repo.session_start())
        self.assertEqual(0, out.code, out.describe())
        self.assertEqual([["new"], ["new"]], kept())
        self.assert_delay(took, base, fresh=True, msg="SessionStart")


class RecordLockTests(LockCase):
    """The record lock: concurrent updates, a stale lock at every update, and a fresh lock."""

    def record_lock(self, caller, state=None) -> Path:
        """``<record path>.lock`` of a role's record."""
        state = state or self.repo.team_state()
        return Path(str(TeamRepo.record_path(state, caller.agent_id)) + ".lock")

    def test_concurrent_background_tasks_keep_every_task(self):
        """Three workers send 20 PostToolUse calls each at once, each with a task: all 60 kept.

        Planted bug named here: a record update without the lock.
        """
        te = self.repo.team_role("test-engineer")
        self.repo.first_call(te)
        tasks = [[f"w{w}-t{i:02d}" for i in range(CALLS)] for w in range(3)]
        outs = burst([[self.repo.post(te, task=task) for task in group] for group in tasks])
        for out in outs:
            self.assertEqual(0, out.code, out.describe())
        record = self.record_of(self.repo, self.repo.team_state(), te.agent_id)
        wanted = sorted(task for group in tasks for task in group)
        self.assertEqual(wanted, sorted(record.get("background") or []),
                         f"{len(set(wanted) - set(record.get('background') or []))} tasks lost")
        self.assertEqual([], lock_files(self.repo.team_state()))

    def test_stale_record_lock_is_taken_over_by_every_update(self):
        """Making a record, PostToolUse, SubagentStop, TaskStop, and SessionEnd: stale locks taken.

        Each update lands, and the lock file is gone afterwards.

        Planted bug caught: a stale lock never taken over (8.2).
        """
        repo = self.repo

        def making():
            """A team role's first call makes its record."""
            role = repo.team_role("developer")
            lock = make_lock(self.record_lock(role), STALE)
            repo.first_call(role)
            return lock, self.record_of(repo, repo.team_state(), role.agent_id) is not None

        def started(name="test-engineer"):
            """A team role that has made its first call, and its stale record lock."""
            role = repo.team_role(name)
            repo.first_call(role)
            return role, make_lock(self.record_lock(role), STALE)

        def post():
            """PostToolUse adds a task."""
            role, lock = started()
            repo.post(role, task="t-stale").run()
            record = self.record_of(repo, repo.team_state(), role.agent_id)
            return lock, record["background"] == ["t-stale"]

        def stop():
            """SubagentStop marks the record stopped."""
            role, lock = started()
            repo.stop(role, tasks=[]).run()
            return lock, bool(self.record_of(repo, repo.team_state(), role.agent_id).get("stopped"))

        def task_stop():
            """The main session's TaskStop closes the record."""
            role, lock = started()
            repo.task_stop(role.agent_id).run()
            return lock, bool(self.record_of(repo, repo.team_state(), role.agent_id).get("stopped"))

        def session_end():
            """SessionEnd closes the ending session's record."""
            role = new_role("developer")
            session = f"session-{role.agent_id}"
            repo.write_record(repo.team_state(), team_record(role, repo.tree(), session=session))
            lock = make_lock(self.record_lock(role), STALE)
            repo.session_end(session).run()
            return lock, bool(self.record_of(repo, repo.team_state(), role.agent_id).get("stopped"))

        for name, case in (("making it", making), ("PostToolUse", post), ("SubagentStop", stop),
                           ("TaskStop", task_stop), ("SessionEnd", session_end)):
            with self.subTest(update=name):
                lock, landed = case()
                self.assertTrue(landed, f"{name}: the record was not updated")
                self.assertFalse(lock.exists(), f"{name}: the stale lock is still there")

    def test_fresh_record_lock_delays_about_a_second_and_still_records(self):
        """A fresh record lock: PostToolUse waits about a second, then records the task.

        Planted bug named here: a record update without the lock.
        """
        te = self.repo.team_role("test-engineer")
        self.repo.first_call(te)
        count = iter(range(100))
        base = baseline(lambda: self.repo.post(te, task=f"base-{next(count)}"))
        lock = make_lock(self.record_lock(te))
        self.addCleanup(lambda: lock.unlink() if lock.exists() else None)
        out, took = timed(self.repo.post(te, task="t-fresh"))
        self.assertEqual(0, out.code, out.describe())
        self.assertIn("t-fresh", self.record_of(self.repo, self.repo.team_state(), te.agent_id)
                      .get("background") or [])
        self.assert_delay(took, base, fresh=True)


if __name__ == "__main__":
    unittest.main()
