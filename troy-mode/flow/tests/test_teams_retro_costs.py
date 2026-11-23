"""retro and costs with teams (F20 design 3.3, 3.12, 4, 5, 8.1; part 2 contract P6, P7).

Written from F20 design version 1.3 and the part 2 contract before the code exists.

- P6: ``retro`` reads the hooks.log lines of the common git folder's
  ``troy-mode/hooks.log`` and of every worktree's ``troy-mode/hooks.log``, each line
  once. The home checkout's git folder is the common git folder, so reading it as a
  worktree too must not count its lines twice.
- P7: ``costs --item`` shares each main-session message in equal parts among the
  items whose run window (first role run's start to the accept commit, or now) holds
  the message's time, so the items' main-session figures add up to the main
  session's cost in that time.

The costs tests write their own transcript folders and price table (the same shapes
as test_costs.py, copied here so this file stands alone): Opus 5.5 at $10 per million
output tokens, so 1,000 output tokens cost one cent.

Planted bugs caught here:

- ``retro`` reading only the home log: ``RetroTests.test_every_worktrees_log_is_read``.
- A log line counted twice: ``RetroTests.test_common_log_lines_count_once``.
- The main session's cost counted in full for each feature (design 8.2):
  ``SharedMainTests.test_two_items_share_their_overlap`` and
  ``test_three_items_share_in_equal_parts``.
- A finished item's window kept open: ``SharedMainTests.test_two_items_share_their_overlap``
  (F03 alone after F02's accept commit).
"""

import itertools
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from flow_helpers import (
    ENGINE, F01, F02, F03, F05, FIVE, Fakes, FlowCase, Outcome, Project, base_env, base_files,
    base_step, commit_time, hooks_line, merged_pr, new_dir, parallel, release_step, stages,
    subject_commits, version_tests_step, write_file,
)
from teams2_helpers import add_team, git_dir_of

# ------------------------------------------------------------------ retro

RETRO_STEPS = ([base_step(base_files((F01,)))] + stages(F01, 6)
               + [version_tests_step("v0.1"), release_step("v0.1.0")])


def utc(seconds: int) -> str:
    """A hooks.log time, ``YYYY-MM-DDTHH:MM:SSZ``, in UTC."""
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_text(lines) -> str:
    """A hooks.log of JSON lines."""
    return "".join(json.dumps(line) + "\n" for line in lines)


class RetroTests(FlowCase):
    """``retro --tag v0.1.0`` with a team worktree and another linked worktree (P6)."""

    @classmethod
    def setUpClass(cls):
        """Home log: two ``scope`` lines. F05's team: three ``scope`` and one ``team``.
        A plain linked worktree: one ``bash``. Every line falls inside v0.1.0's window."""
        cls.project = Project(RETRO_STEPS)
        shas = subject_commits(cls.project)
        merged = [merged_pr(n, item.subject, shas[item.subject])
                  for n, item in enumerate(RETRO_STEPS, start=1)]
        first = commit_time(cls.project, shas[RETRO_STEPS[0].subject])
        dev, te = "tstack:troy-developer", "tstack:troy-test-engineer"
        home = [hooks_line(utc(first + 5), dev, "h1", "scope"),
                hooks_line(utc(first + 6), dev, "h2", "scope", "tests/h.py")]
        team = [hooks_line(utc(first + 10), dev, "t1", "scope", "tests/t.py"),
                hooks_line(utc(first + 11), dev, "t1", "scope", "docs/t.md"),
                hooks_line(utc(first + 12), te, "t2", "scope", "src/wordcount/t.py"),
                hooks_line(utc(first + 13), te, "t2", "team", "README.md")]
        other = [hooks_line(utc(first + 20), None, None, "bash", "src/x.py")]
        tree = add_team(cls.project, "F05")
        plain = cls.project.tmp / "wordcount-wt"
        cls.project.git("worktree", "add", "-q", "--detach", str(plain), "origin/main")
        write_file(cls.project.root / ".git", "troy-mode/hooks.log", log_text(home))
        write_file(git_dir_of(tree), "troy-mode/hooks.log", log_text(team))
        write_file(git_dir_of(plain), "troy-mode/hooks.log", log_text(other))
        cls.out = cls.project.run("retro", "--tag", "v0.1.0", fakes=Fakes(merged=merged))

    def hooks_groups(self) -> dict:
        """The report's ``hooks.log:`` groups: key mapped to count."""
        report = self.report_of(self.out, 0, "retro")
        return {g["key"]: g["count"] for g in report["groups"] if g.get("kind") == "hooks"}

    def test_every_worktrees_log_is_read(self):
        """The team's ``team`` line and the other worktree's ``bash`` line count.

        Planted bug caught: retro reading only the home log.
        """
        groups = self.hooks_groups()
        self.assertEqual(1, groups.get("hooks.log: team"), groups)
        self.assertEqual(1, groups.get("hooks.log: bash"), groups)

    def test_common_log_lines_count_once(self):
        """``scope``: the home log's two and the team's three, five in all.

        Planted bug caught: a log line counted twice (the common git folder read as
        the home checkout's git folder too).
        """
        self.assertEqual(5, self.hooks_groups().get("hooks.log: scope"), self.hooks_groups())

    def test_repeated_lists_the_hooks_groups_seen_twice(self):
        """``hooks.log: scope`` is repeated; the single ``team`` and ``bash`` lines are not."""
        report = self.report_of(self.out, 0, "retro")
        self.assertIn("hooks.log: scope", report["repeated"])
        self.assertNotIn("hooks.log: team", report["repeated"])
        self.assertNotIn("hooks.log: bash", report["repeated"])


# ------------------------------------------------------------------ costs

PRICES_TOML = """\
as_of = "2026-01-02"
source = "https://example.com/pricing"
web_search = 0.05

[models."claude-opus-5-5"]
input = 1.00
output = 10.00
cache_read = 0.10
cache_write_5m = 2.00
cache_write_1h = 4.00
"""
OPUS = "claude-opus-5-5"
IF = "tstack:troy-interface-designer"
TEST_PRICES = new_dir("p2prices") / "prices.toml"
TEST_PRICES.write_bytes(PRICES_TOML.encode("utf-8"))
EMPTY_CONFIG = new_dir("p2config")
(EMPTY_CONFIG / "projects").mkdir()
_IDS = itertools.count(1)
# F01 and F02 accepted; F03 and F05 are not, so their windows run to now.
COST_STEPS = (base_step(base_files(FIVE)), *stages(F01, 6), *stages(F02, 6))


def iso(seconds: float) -> str:
    """A transcript timestamp, ``YYYY-MM-DDTHH:MM:SS.000Z``, in UTC."""
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def user(when: float, text: str) -> dict:
    """A ``user`` record."""
    return {"type": "user", "timestamp": iso(when), "uuid": f"u-{next(_IDS):06d}",
            "message": {"role": "user", "content": text}}


def spend(when: float, cents: int) -> dict:
    """One Opus assistant message of output tokens that cost ``cents``."""
    usage = {"input_tokens": 0, "output_tokens": cents * 1000, "cache_read_input_tokens": 0,
             "cache_creation_input_tokens": 0,
             "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0},
             "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
             "service_tier": "standard", "speed": "standard"}
    message = {"id": f"msg_{next(_IDS):06d}", "type": "message", "role": "assistant",
               "model": OPUS, "content": [{"type": "text", "text": "Done."}], "usage": usage}
    return {"type": "assistant", "timestamp": iso(when), "uuid": f"u-{next(_IDS):06d}",
            "message": message}


def brief(item: str, title: str, task: str = "IF1") -> str:
    """A role run's first message, in the brief's format (F07 design 6.1)."""
    return (f"Task: {task}, Write the stage's output.\nItem: {item}, {title}\nRead first:\n"
            "- docs/requirements.md\nInput: None\nRound: None\nChecks to run: None\n")


def write_lines(path: Path, records: Sequence[dict], defaults: dict) -> None:
    """Writes JSON lines, each record with the defaults it lacks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps({**defaults, **record}) for record in records) + "\n"
    path.write_bytes(text.encode("utf-8"))


def transcripts(session: str, main: Sequence[dict], runs: Sequence[tuple]) -> Path:
    """A transcript folder: the main session's file and one Interface Designer run per item.

    Args:
        session: The session ID.
        main: The main session's records.
        runs: ``(agent ID, item, start, cents)`` for each role run.

    Returns:
        The folder.
    """
    folder = new_dir("p2transcripts")
    write_lines(folder / f"{session}.jsonl", main, {"sessionId": session, "isSidechain": False})
    for aid, item, start, cents in runs:
        feature = {f.id: f for f in FIVE}[item]
        sub = folder / session / "subagents"
        write_lines(sub / f"agent-{aid}.jsonl",
                    [user(start, brief(item, feature.title(1))), spend(start + 5, cents)],
                    {"sessionId": session, "isSidechain": True, "agentId": aid})
        meta = {"agentType": IF, "description": f"IF1 {item}", "spawnDepth": 1}
        (sub / f"agent-{aid}.meta.json").write_bytes(json.dumps(meta).encode("utf-8"))
    return folder


def run_costs(project: Project, item: str, folder: Path) -> Outcome:
    """Runs ``costs --item <item> --transcripts <folder> --repo <clone> --json``."""
    argv = ["costs", "--item", item, "--transcripts", str(folder), "--repo", str(project.root),
            "--json"]
    env = base_env(Fakes(fail=True).path_env())
    env.update({"CLAUDE_CONFIG_DIR": str(EMPTY_CONFIG), "TROY_MODE_PRICES": str(TEST_PRICES)})
    proc = subprocess.run([sys.executable, str(ENGINE), *argv], cwd=str(project.tmp), env=env,
                          capture_output=True, stdin=subprocess.DEVNULL, timeout=180, check=False)
    stdout = proc.stdout.decode("utf-8", "replace")
    try:
        report: Optional[dict] = json.loads(stdout)
    except ValueError:
        report = None
    return Outcome(proc.returncode, stdout, proc.stderr.decode("utf-8", "replace"), report)


class SharedMainTests(FlowCase):
    """The main session's messages shared among the items running at that time (P7)."""

    @classmethod
    def setUpClass(cls):
        """Three folders around F02's accept commit time ``A``, and their costs runs.

        Two items: F02's run at A-3000 and F03's at A-2000 ($1 each); main $10 at
        A-4000, $1 at A-2500, $2 at A-1000, $4 at A+600.
        Three items: F02 at A-3000, F03 at A-2000, F05 at A-1200; main $1 at A-2500,
        $3 at A-1000, $4 at A+600.
        One item: F02 at A-3000; main $1 at A-2500 and $2 at A-1000.
        """
        cls.project = Project(COST_STEPS)
        accept = commit_time(cls.project, subject_commits(cls.project)[F02.title(6)])
        two = transcripts("5e55c002-0000-4000-8000-0000000000c2", [
            user(accept - 4100, "Start the batch."), spend(accept - 4000, 1000),
            spend(accept - 2500, 100), spend(accept - 1000, 200), spend(accept + 600, 400)],
            [("aif20201", "F02", accept - 3000, 100), ("aif20301", "F03", accept - 2000, 100)])
        three = transcripts("5e55c003-0000-4000-8000-0000000000c3", [
            user(accept - 3100, "Start the batch."), spend(accept - 2500, 100),
            spend(accept - 1000, 300), spend(accept + 600, 400)],
            [("aif30201", "F02", accept - 3000, 100), ("aif30301", "F03", accept - 2000, 100),
             ("aif30501", "F05", accept - 1200, 100)])
        one = transcripts("5e55c001-0000-4000-8000-0000000000c1", [
            user(accept - 3100, "Start F02."), spend(accept - 2500, 100),
            spend(accept - 1000, 200)], [("aif10201", "F02", accept - 3000, 100)])
        runs = {("two", "F02"): two, ("two", "F03"): two, ("three", "F02"): three,
                ("three", "F03"): three, ("three", "F05"): three, ("one", "F02"): one}
        keys = list(runs)
        cls.outs = dict(zip(keys, parallel(lambda k: run_costs(cls.project, k[1], runs[k]),
                                           keys)))

    def main_cost(self, folder: str, item: str) -> float:
        """The main session's figure of one item's report, which must exit 0."""
        out = self.outs[(folder, item)]
        self.assertEqual(0, out.code, out.describe())
        self.assertIsInstance(out.report, dict, out.describe())
        return round(float(out.report["main"]["cost"]), 2)

    def test_two_items_share_their_overlap(self):
        """F02: $1 alone and half of $2; F03: half of $2 and $4 alone after F02's accept.

        Planted bug caught: the main session's cost counted in full for each feature.
        """
        self.assertEqual((2.00, 5.00), (self.main_cost("two", "F02"), self.main_cost("two", "F03")))

    def test_two_items_add_up_to_the_main_session(self):
        """F02's and F03's main-session figures add up to the $7 spent from A-3000 on."""
        self.assertAlmostEqual(7.00, self.main_cost("two", "F02") + self.main_cost("two", "F03"),
                               places=2)

    def test_total_holds_the_share(self):
        """F02's total is its run's $1 and its $2 share of the main session."""
        out = self.outs[("two", "F02")]
        self.assertEqual(0, out.code, out.describe())
        self.assertAlmostEqual(3.00, float(out.report["total"]), places=2)

    def test_three_items_share_in_equal_parts(self):
        """$3 at A-1000 in three windows: $1 each; $4 at A+600 in F03's and F05's: $2 each.

        Planted bug caught: the main session's cost counted in full for each feature.
        """
        found = tuple(self.main_cost("three", item) for item in ("F02", "F03", "F05"))
        self.assertEqual((2.00, 3.00, 3.00), found)
        self.assertAlmostEqual(8.00, sum(found), places=2)

    def test_one_item_running_changes_nothing(self):
        """F02 alone: every main-session message in its window counts in full, $3."""
        self.assertEqual(3.00, self.main_cost("one", "F02"))


if __name__ == "__main__":
    unittest.main()
