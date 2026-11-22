"""The second round end to end through troy_exam.py (F16 design 7.2, 8.2, 10.2, 10.3, 11.5).

Each scenario runs ``python troy-mode/exam/troy_exam.py`` as test_exam_cli.py
does: a Scenario's work root, CLAUDE_CONFIG_DIR, and stand-in CLI in temp
folders, ``--repo`` the shared fake tstack checkout, and the case dv-small
(the Developer's DV1 on F01). Before the exam starts, each scenario writes
cases/<case>.tsv in its work root: base runs that the exam reuses (the base
commit's instruction hash, this CLI, an hour old), and runs it never reuses
(another hash), which set the case's median. The stand-in's "versions" knob
makes the head's first runs fail at the judge, or one case's runs cost more,
whatever order the exam runs them in. One stand-in run costs what its plan
says; one judge pass costs $0.50. The scenarios are independent, so they run
side by side in a thread pool, started when the first test class needs one.

The scenarios and their figures:

- round: a target like exam 2026-11-19-8. The base's 5 runs are reused
  (recorded at $0.20, 1 of 5 passed), the case's median is $0.04, so the
  first round is $2.20 and the guard before version 1.8 stopped at $3.30. The
  head's runs cost $0.30 and pass 3 of 5, so the target rule asks for a
  second round: 5 x $0.20 + 5 x $0.30 + $2.00 = $4.50, which moves the guard's
  estimate to $6.70. The old guard stopped it partway (6 of its 10 runs,
  two at a time) and recorded "not fixed", as in exam -8. Now all 10 run,
  the head passes 8 of 10 against the base's 6, and the rule says "fixed".
- line: two cases. dv-small's base runs are reused at $4.00 (5 of 5 passed),
  its head's runs cost $4.80 and pass 3 of 5, so the not-worse rule asks for
  a second round of 5 x $4.00 + 5 x $4.80 + $2.00 = $46.00. dv-wide's base
  runs are reused at $0.40 (0 of 5 passed), its head's cost $0.30, and it
  passes in the first round. The first round is $26.00, under $60, and it
  spends $26.50. Spent plus $46.00 is $72.50, above $60, so the exam waits for
  Troy before any second-round run; the estimate is $26.00 + $46.00 = $72.00
  and the whole $74.00. `resume` refuses; `resume --yes` approves $72.50 and
  finishes: dv-small 10 of 10 against 8 of 10, not worse.
- guard: runs cost $2.00 against a case's median of $0.10, the base
  measured: a first round of $3.00 and a guard of $4.50. One job at a time,
  three runs start, and the exam waits for Troy. `resume --stop` ends it:
  failed, "no verdict".
- start: the base reused at $15.00, so the first round is $77.00 and the
  whole $229.00. Without --yes the exam waits before it starts; `--yes
  --stop` and a bare `resume` are refused; `resume --yes` starts it with
  $229.00 approved.
- yes: the same log, `run --yes`: $229.00 approved.
- stopstart: the same log, dv-small as a target, waiting before it starts;
  `resume --stop` ends it with no run, "no verdict" and not "not fixed".
- reruns: the base's first run is void three times (a changed brief), so
  its reruns run out and the case ends with 4 base runs that count: "no
  verdict", not "worse".
- prove: `prove` with runs at $5.00 against $5.40: its guard waits like the
  exam's, after two runs.

Planted bugs of design 10.3 caught here (and in test_exam_budget.py):

- "the second round's estimate leaving out the base's runs when its first 5
  were reused": RoundTests.test_the_second_rounds_estimate_from_each_versions_own_runs
  and test_the_guard_holds_the_first_round_and_this_round;
  LineTests.test_the_exam_waits_before_the_second_round ($26.50 spent plus
  $26.00 stays under $60) and test_only_the_asked_round_joins_the_estimate.
- "the guard counting every case's second round from the start":
  GuardWaitTests.test_the_exam_waits_after_three_runs (5 runs start against
  a guard of 1.5 x $6.00) and test_the_saved_state_waits_at_the_guard;
  RoundTests.test_the_guard_holds_the_first_round_and_this_round;
  LineTests.test_only_the_asked_round_joins_the_estimate;
  StartWaitTests.test_resume_yes_starts_it_with_the_whole_approved and
  RunYesTests.test_run_yes_approves_the_whole (an estimate of $77.00, not $229.00).
- "a reused run counted at $0 in its version's median":
  RoundTests.test_the_second_rounds_estimate_from_each_versions_own_runs and
  test_the_guard_holds_the_first_round_and_this_round;
  LineTests.test_the_exam_waits_before_the_second_round and
  test_only_the_asked_round_joins_the_estimate.
- "the second round's judge pass left out":
  RoundTests.test_the_second_rounds_estimate_from_each_versions_own_runs and
  test_the_second_rounds_judge_pass_is_in_its_estimate;
  LineTests.test_only_the_asked_round_joins_the_estimate and test_the_waiting_report.
- "`resume` going on without `--yes`": LineTests.test_resume_without_a_flag_refuses
  and StartWaitTests.test_resume_without_a_flag_refuses.
- "a case cut short shown as "worse" (or "not fixed")":
  GuardWaitTests.test_the_case_cut_short_has_no_verdict (a not-worse case
  stopped by Troy), StopBeforeStartTests.test_the_target_shows_no_verdict (a
  target stopped by Troy), and RerunsTests.test_the_case_has_no_verdict (a
  not-worse case whose reruns ran out).
"""

import json
import re
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from exam_helpers import (CASE_ID, CLI_VERSION, HAIKU, MOCK_BRANCH, SONNET, Scenario, new_dir,
                          role_plan, shared_checkout, write_file, write_small_case)
from troyexam.instructions import GitTree, instruction_hash

LOG_FIELDS = ("exam", "run", "time", "side", "case_version", "instructions", "cli", "models",
              "effort", "status", "passed", "cost", "minutes")
OTHER = "f" * 64                   # an instruction hash no commit has: rows never reused
WIDE = "dv-wide"                   # the line scenario's second case
WIDE_BRANCH = "troy-mode/f01-3-wide"
HEAD = "head-one"                  # the marker of the checkout's head in the stand-in
BASE = "none"                      # the base's agent file has no marker
WAITING = "waiting for Troy"
JUDGE_COST = 2.00                  # the design's judge pass in an estimate
JUDGE_SPENT = 0.50                 # what one stand-in judge pass costs

_LOCK = threading.Lock()
_FUTURES: dict = {}


# ------------------------------------------------------------------ helpers

def full_hash(ref: str) -> str:
    """The instruction hash of a commit of the fake checkout."""
    return instruction_hash(GitTree(shared_checkout().path, ref))


def costs(total: float) -> dict:
    """Stand-in costs per model that add up to total: $0.01 of haiku, the rest sonnet."""
    return {HAIKU: 0.01, SONNET: round(total - 0.01, 6)}


def log_rows(count: int, cost: float, passed, instructions: str, side: str = "base",
             name: str = "old") -> list:
    """Rows of a case's log, an hour old, with this CLI, the stand-in's models, and high effort.

    Args:
        count: How many rows.
        cost: Each row's cost.
        passed: True or False for every row, or a number: the first that many pass.
        instructions: The rows' instruction hash; the base's makes them reusable.
        side: "base" or "head".
        name: The start of each row's run ID.
    """
    when = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for n in range(count):
        ok = passed if isinstance(passed, bool) else n < passed
        rows.append({"exam": "2026-11-20-1", "run": f"{name}{n + 1}", "time": when, "side": side,
                     "case_version": "1", "instructions": instructions, "cli": CLI_VERSION,
                     "models": f"{HAIKU},{SONNET}", "effort": "high", "status": "ok",
                     "passed": "true" if ok else "false", "cost": f"{cost:.2f}",
                     "minutes": "2.0"})
    return rows


def write_log(root: Path, case_id: str, rows: list) -> None:
    """Writes cases/<case ID>.tsv in a work root."""
    lines = ["\t".join(LOG_FIELDS)] + ["\t".join(str(r[f]) for f in LOG_FIELDS) for r in rows]
    write_file(root / "cases", f"{case_id}.tsv", "\n".join(lines) + "\n")


def state_of(folder: Path) -> dict:
    """An exam's saved state.json."""
    return json.loads((folder / "state.json").read_text(encoding="utf-8"))


def lines_of(text: str) -> list:
    """Lines without CR."""
    return text.replace("\r\n", "\n").split("\n")


def table_rows(text: str) -> list:
    """The case rows of a "Role exam" section."""
    return [line for line in lines_of(text) if line.startswith("| ")
            and not line.startswith("| Case ") and not line.startswith("| ---")]


def report_of(proc) -> dict:
    """A command's --json report, or {} when its output is not JSON."""
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {}


def markers(scene: Scenario) -> list:
    """The version of each role call, in call order."""
    return [call["marker"] for call in scene.cli.calls("role")]


def snapshot(scene: Scenario, exam: Path) -> dict:
    """The state and the stand-in's call counts at this moment."""
    return {"state": state_of(exam) if exam is not None and (exam / "state.json").is_file()
            else {}, "roles": scene.cli.claims("role"), "judges": scene.cli.claims("judge"),
            "markers": markers(scene)}


def only_exam(scene: Scenario):
    """The scenario's one exam folder, or None."""
    found = scene.results()
    return found[-1] if found else None


def slot_costs(state: dict, case_id: str, side: str) -> list:
    """A case's planned slot costs of one side, sorted; -1.0 for a slot without one."""
    found = []
    for slot in state.get("plan", []):
        if slot.get("case") == case_id and slot.get("side") == side:
            cost = slot.get("cost")
            found.append(round(float(cost), 2) if cost is not None else -1.0)
    return sorted(found)


# ---------------------------------------------------------------- scenarios

def scene_round(checkout) -> dict:
    """A target like exam 2026-11-19-8, whose second round the old guard would have stopped."""
    plan = role_plan(role={"costs": costs(0.30)},
                     versions={HEAD: {"calls": {"1": {"tidy": False}, "2": {"tidy": False}}}})
    scene = Scenario(plan)
    write_log(scene.root, CASE_ID,
              log_rows(5, 0.20, 1, full_hash(checkout.base))
              + log_rows(6, 0.04, True, OTHER, side="head", name="older"))
    proc = scene.exam("run", "--base", checkout.base, "--head", checkout.head,
                      "--case", CASE_ID, "--fixes", CASE_ID)
    exam = only_exam(scene)
    out = {"scene": scene, "proc": proc, "exam": exam, "end": snapshot(scene, exam)}
    if exam is not None:
        out["block"] = scene.exam("block", exam.name)
    return out


def scene_line(checkout) -> dict:
    """Two cases; one asks for a second round that takes the exam above $60 (the line)."""
    cases = new_dir("lcases")
    write_small_case(cases / CASE_ID, checkout.start)
    write_small_case(cases / WIDE, checkout.start, case_id=WIDE, branch=WIDE_BRANCH)
    plan = role_plan(role={"costs": costs(4.80)},
                     versions={f"{HEAD}@{MOCK_BRANCH}": {"calls": {"1": {"tidy": False},
                                                                   "2": {"tidy": False}}},
                               f"{HEAD}@{WIDE_BRANCH}": {"every": {"costs": costs(0.30)}}})
    scene = Scenario(plan)
    base_hash = full_hash(checkout.base)
    write_log(scene.root, CASE_ID, log_rows(5, 4.00, True, base_hash))
    write_log(scene.root, WIDE, log_rows(5, 0.40, False, base_hash))
    first = scene.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID,
                       "--case", WIDE, "--cases", str(cases), "--json")
    exam = only_exam(scene)
    out = {"scene": scene, "first": first, "exam": exam, "wait": snapshot(scene, exam)}
    if exam is None:
        return out
    out["plain"] = scene.exam("resume", exam.name)
    out["after_plain"] = snapshot(scene, exam)
    out["yes"] = scene.exam("resume", exam.name, "--yes")
    out["end"] = snapshot(scene, exam)
    out["block"] = scene.exam("block", exam.name)
    return out


def scene_guard(checkout) -> dict:
    """Runs at $2.00 against a case's median of $0.10: the guard waits, then --stop."""
    scene = Scenario(role_plan(role={"costs": costs(2.00)}))
    write_log(scene.root, CASE_ID, log_rows(5, 0.10, True, OTHER))
    first = scene.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID,
                       "--jobs", "1")
    exam = only_exam(scene)
    out = {"scene": scene, "first": first, "exam": exam, "wait": snapshot(scene, exam)}
    if exam is None:
        return out
    out["stop"] = scene.exam("resume", exam.name, "--stop")
    out["end"] = snapshot(scene, exam)
    out["block"] = scene.exam("block", exam.name)
    return out


def scene_start(checkout) -> dict:
    """A first round of $77 waits before it starts; refusals; then resume --yes."""
    scene = Scenario(role_plan())
    write_log(scene.root, CASE_ID, log_rows(5, 15.00, True, full_hash(checkout.base)))
    first = scene.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID,
                       "--json")
    exam = only_exam(scene)
    out = {"scene": scene, "first": first, "exam": exam, "wait": snapshot(scene, exam)}
    if exam is None:
        return out
    out["both"] = scene.exam("resume", exam.name, "--yes", "--stop")
    out["after_both"] = snapshot(scene, exam)
    out["plain"] = scene.exam("resume", exam.name)
    out["after_plain"] = snapshot(scene, exam)
    out["yes"] = scene.exam("resume", exam.name, "--yes")
    out["end"] = snapshot(scene, exam)
    return out


def scene_yes(checkout) -> dict:
    """The same $77 first round with run --yes."""
    scene = Scenario(role_plan())
    write_log(scene.root, CASE_ID, log_rows(5, 15.00, True, full_hash(checkout.base)))
    proc = scene.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID,
                      "--yes", "--json")
    exam = only_exam(scene)
    return {"scene": scene, "proc": proc, "exam": exam, "end": snapshot(scene, exam)}


def scene_stop_start(checkout) -> dict:
    """A target waiting before it starts, ended by resume --stop."""
    scene = Scenario(role_plan())
    write_log(scene.root, CASE_ID, log_rows(5, 15.00, True, full_hash(checkout.base)))
    first = scene.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID,
                       "--fixes", CASE_ID)
    exam = only_exam(scene)
    out = {"scene": scene, "first": first, "exam": exam, "wait": snapshot(scene, exam)}
    if exam is None:
        return out
    out["stop"] = scene.exam("resume", exam.name, "--stop")
    out["end"] = snapshot(scene, exam)
    out["block"] = scene.exam("block", exam.name)
    return out


def scene_reruns(checkout) -> dict:
    """The base's first run is void three times, so its reruns run out; one job at a time."""
    mangle = {"brief": "mangle"}
    scene = Scenario(role_plan(versions={BASE: {"calls": {"1": mangle, "2": mangle,
                                                          "3": mangle}}}))
    proc = scene.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID,
                      "--jobs", "1")
    exam = only_exam(scene)
    out = {"scene": scene, "proc": proc, "exam": exam, "end": snapshot(scene, exam)}
    if exam is not None:
        out["block"] = scene.exam("block", exam.name)
    return out


def scene_prove(checkout) -> dict:
    """prove with runs at $5.00 against an estimate of $5.40, one job at a time."""
    scene = Scenario(role_plan(role={"costs": costs(5.00)}))
    proc = scene.exam("prove", CASE_ID, "--ref", checkout.base, "--jobs", "1")
    exam = only_exam(scene)
    return {"scene": scene, "proc": proc, "exam": exam, "end": snapshot(scene, exam)}


SCENES = {"round": scene_round, "line": scene_line, "guard": scene_guard, "start": scene_start,
          "yes": scene_yes, "stopstart": scene_stop_start, "reruns": scene_reruns,
          "prove": scene_prove}


def scenario(name: str) -> dict:
    """A scenario's outcome, starting every scenario side by side on first use."""
    with _LOCK:
        if not _FUTURES:
            checkout = shared_checkout()
            pool = ThreadPoolExecutor(max_workers=len(SCENES))
            for key, func in SCENES.items():
                _FUTURES[key] = pool.submit(func, checkout)
            pool.shutdown(wait=False)
    return _FUTURES[name].result()


class SceneTest(unittest.TestCase):
    """Shared checks of the classes below."""

    NAME = ""

    @classmethod
    def setUpClass(cls):
        """Runs (or waits for) the class's scenario."""
        cls.out = scenario(cls.NAME)
        cls.scene = cls.out["scene"]

    def describe(self, key: str) -> str:
        """One command's output and the stand-in's errors, for messages."""
        proc = self.out.get(key)
        return self.scene.describe(proc) if proc is not None else f"no {key} command ran"

    def exam_name(self) -> str:
        """The exam's ID; fails when no exam folder was made."""
        self.assertIsNotNone(self.out["exam"], self.describe("first" if "first" in self.out
                                                             else "proc"))
        return self.out["exam"].name

    def assertAmount(self, value, expected: float, msg=None):
        """A dollar figure that is present and equal to the cent."""
        self.assertIsNotNone(value, msg or f"no figure where ${expected:.2f} was expected")
        self.assertAlmostEqual(float(value), expected, places=2, msg=msg)

    def assertWaits(self, snap: dict, why: str):
        """The saved state waits for Troy for this reason."""
        state = snap["state"]
        self.assertEqual(state.get("status"), WAITING, json.dumps(state)[:2000])
        self.assertEqual((state.get("waiting") or {}).get("why"), why, state.get("waiting"))

    def assertMentionsBothFlags(self, proc):
        """The output tells Troy to use --yes or --stop."""
        text = proc.stdout + proc.stderr
        self.assertIn("--yes", text)
        self.assertIn("--stop", text)


# --------------------------------------------------------------------- tests

class RoundTests(SceneTest):
    """A target like exam -8: the second round runs to its end and the rule decides (10.3)."""

    NAME = "round"

    def test_the_second_round_runs_to_its_end(self):
        """5 head runs, then 5 more of each version: 15 role runs, none cut short."""
        proc = self.out["proc"]
        self.assertEqual(self.out["end"]["roles"], 15, self.describe("proc"))
        self.assertEqual(sorted(self.out["end"]["markers"]), [HEAD] * 10 + [BASE] * 5)
        self.assertEqual(proc.returncode, 0, self.describe("proc"))

    def test_the_rule_decides(self):
        """The head passes 8 of 10 against 6 of 10: "fixed", the rule's word."""
        block = self.out.get("block")
        self.assertIsNotNone(block, self.describe("proc"))
        self.assertEqual(block.returncode, 0, self.scene.describe(block))
        self.assertIn("Result: passed", lines_of(block.stdout))
        self.assertEqual(table_rows(block.stdout),
                         ["| dv-small | Developer | 6 of 10 | 8 of 10 | fixed |"], block.stdout)

    def test_the_second_rounds_estimate_from_each_versions_own_runs(self):
        """5 x $0.20 (the reused runs as recorded) + 5 x $0.30 (the head's) + $2.00 = $4.50.

        $3.50 means the base's reused runs were left out or counted at $0;
        $2.50 means the judge pass was left out; $2.40 is the case's median.
        """
        info = self.out["end"]["state"].get("cases", {}).get(CASE_ID, {})
        self.assertIsNotNone(info.get("second"), info)
        self.assertAmount(info["second"], 4.50)

    def test_the_second_rounds_judge_pass_is_in_its_estimate(self):
        """The second round's estimate is its ten slots plus one $2.00 judge pass.

        Its slots are every base slot (the base's first 5 runs were reused) and
        the head's slots after its first 5, which cost the case's $0.04 each.
        """
        state = self.out["end"]["state"]
        second = state.get("cases", {}).get(CASE_ID, {}).get("second")
        self.assertIsNotNone(second, state.get("cases"))
        base, head = slot_costs(state, CASE_ID, "base"), slot_costs(state, CASE_ID, "head")
        self.assertEqual((len(base), len(head)), (5, 10), state.get("plan"))
        runs = sum(base) + sum(head) - 5 * 0.04
        self.assertAmount(second - runs, JUDGE_COST)

    def test_a_reused_run_keeps_its_recorded_cost(self):
        """Each reused base run costs nothing now and keeps the $0.20 its log row records."""
        reused = self.out["end"]["state"].get("cases", {}).get(CASE_ID, {}).get("reused", [])
        self.assertEqual(len(reused), 5, reused)
        for run in reused:
            with self.subTest(run=run.get("run")):
                self.assertEqual(run.get("cost"), 0.0)
                self.assertAmount(run.get("recorded_cost"), 0.20)

    def test_the_slots_carry_their_estimates(self):
        """First-round head slots at the case's $0.04; second-round slots at each version's own."""
        state = self.out["end"]["state"]
        self.assertEqual(slot_costs(state, CASE_ID, "head"), [0.04] * 5 + [0.30] * 5,
                         state.get("plan"))
        self.assertEqual(slot_costs(state, CASE_ID, "base"), [0.20] * 5, state.get("plan"))

    def test_the_guard_holds_the_first_round_and_this_round(self):
        """Estimate $2.20 + $4.50 = $6.70; the whole $2.20 + $2.40 = $4.60; $60 approved."""
        state = self.out["end"]["state"]
        self.assertAmount(state.get("estimate"), 6.70)
        self.assertAmount(state.get("whole"), 4.60)
        self.assertAmount(state.get("approved"), 60.0)

    def test_the_second_round_has_its_own_judge_pass(self):
        """Two judge passes; the second grades all 15 new runs and both anchors."""
        judges = self.scene.cli.calls("judge")
        self.assertEqual(len(judges), 2, self.describe("proc"))
        self.assertEqual(len(judges[1]["labels"]), 17)


class LineTests(SceneTest):
    """The line: a second round that would pass $60 waits for Troy before it starts (10.3)."""

    NAME = "line"

    def test_the_exam_waits_before_the_second_round(self):
        """Exit 2 after the first round's 10 head runs and 2 judge passes; no base run yet."""
        first = self.out["first"]
        self.assertEqual(first.returncode, 2, self.describe("first"))
        self.assertEqual(self.out["wait"]["roles"], 10, self.describe("first"))
        self.assertEqual(set(self.out["wait"]["markers"]), {HEAD})
        self.assertEqual(self.out["wait"]["judges"], 2)

    def test_the_waiting_report(self):
        """--json: status, why, spent $26.50, left $46.00, estimate $72.00, and the exam."""
        report = report_of(self.out["first"])
        self.assertEqual(report.get("status"), WAITING, self.describe("first"))
        self.assertEqual(report.get("why"), "line")
        self.assertEqual(report.get("exam"), self.exam_name())
        self.assertAmount(report.get("spent"), 26.50)
        self.assertAmount(report.get("left"), 46.00)
        self.assertAmount(report.get("estimate"), 72.00)

    def test_the_saved_state_waits_on_the_line(self):
        """state.json: waiting for Troy, why line, $26.50 spent, $46.00 left, $60 approved."""
        snap = self.out["wait"]
        self.assertWaits(snap, "line")
        waiting = snap["state"]["waiting"]
        self.assertAmount(waiting.get("spent"), 26.50)
        self.assertAmount(waiting.get("left"), 46.00)
        self.assertAmount(snap["state"].get("approved"), 60.0)

    def test_only_the_asked_round_joins_the_estimate(self):
        """$26.00 + dv-small's $46.00 = $72.00; dv-wide asks for none; the whole is $74.00."""
        state = self.out["wait"]["state"]
        cases = state.get("cases", {})
        self.assertAmount(cases.get(CASE_ID, {}).get("second"), 46.00, cases.get(CASE_ID))
        self.assertIsNone(cases.get(WIDE, {}).get("second"), cases.get(WIDE))
        self.assertEqual(cases.get(WIDE, {}).get("outcome"), "pass")
        self.assertAmount(state.get("estimate"), 72.00)
        self.assertAmount(state.get("whole"), 74.00)

    def test_the_second_rounds_slots_wait_at_their_versions_cost(self):
        """dv-small's 5 base slots at $4.00 and its second 5 head slots at $4.80 are planned."""
        state = self.out["wait"]["state"]
        self.assertEqual(slot_costs(state, CASE_ID, "base"), [4.00] * 5, state.get("plan"))
        self.assertEqual(slot_costs(state, CASE_ID, "head"), [4.00] * 5 + [4.80] * 5,
                         state.get("plan"))

    def test_resume_without_a_flag_refuses(self):
        """Exit 2, no run or judge pass, still waiting, and it names --yes and --stop."""
        plain, after = self.out.get("plain"), self.out.get("after_plain")
        self.assertIsNotNone(plain, self.describe("first"))
        self.assertEqual(plain.returncode, 2, self.scene.describe(plain))
        self.assertEqual(after["roles"], self.out["wait"]["roles"])
        self.assertEqual(after["judges"], self.out["wait"]["judges"])
        self.assertWaits(after, "line")
        self.assertMentionsBothFlags(plain)

    def test_resume_yes_finishes_the_exam(self):
        """10 more role runs and a judge pass; both cases not worse; exit 0."""
        yes = self.out.get("yes")
        self.assertIsNotNone(yes, self.describe("first"))
        self.assertEqual(yes.returncode, 0, self.scene.describe(yes))
        self.assertEqual(self.out["end"]["roles"], 20)
        self.assertEqual(self.out["end"]["markers"][10:].count(BASE), 5)
        self.assertEqual(self.out["end"]["judges"], 3)
        self.assertEqual(table_rows(self.out["block"].stdout),
                         ["| dv-small | Developer | 10 of 10 | 8 of 10 | not worse |",
                          "| dv-wide | Developer | 0 of 5 | 5 of 5 | not worse |"],
                         self.out["block"].stdout)

    def test_resume_yes_approves_what_is_spent_and_left(self):
        """Approved and the guard's estimate both become $26.50 + $46.00 = $72.50."""
        state = self.out.get("end", {}).get("state", {})
        self.assertAmount(state.get("approved"), 72.50)
        self.assertAmount(state.get("estimate"), 72.50)


class GuardWaitTests(SceneTest):
    """The guard waits for Troy instead of recording a verdict; resume --stop ends it (D243)."""

    NAME = "guard"

    def test_the_exam_waits_after_three_runs(self):
        """$2.00 a run against a guard of 1.5 x $3.00: runs start at $0, $2, $4; exit 2."""
        self.assertEqual(self.out["wait"]["roles"], 3, self.describe("first"))
        self.assertEqual(self.out["first"].returncode, 2, self.describe("first"))

    def test_the_text_report_names_the_figures(self):
        """Without --json the waiting report gives its keys as lines."""
        text = self.out["first"].stdout
        for key, value in (("status", WAITING), ("why", "guard"), ("exam", self.exam_name())):
            with self.subTest(key=key):
                self.assertRegex(text, rf"(?m)^{key}\b[ :]*{re.escape(value)}\s*$")
        for key in ("spent", "left", "estimate"):
            with self.subTest(key=key):
                self.assertRegex(text, rf"(?m)^{key}\b[ :]*\$?\d")

    def test_the_saved_state_waits_at_the_guard(self):
        """Why guard; the estimate is still $3.00; 7 slots at $0.10 and a judge pass left."""
        snap = self.out["wait"]
        self.assertWaits(snap, "guard")
        state = snap["state"]
        self.assertAmount(state.get("estimate"), 3.00)
        self.assertAmount(state["waiting"].get("left"), 2.70)
        spent = state["waiting"].get("spent")
        self.assertIsNotNone(spent, state["waiting"])
        # Three runs at $2.00, and the judge's $0.50 if it graded them before waiting.
        self.assertGreaterEqual(float(spent), 6.0 - 0.005)
        self.assertLessEqual(float(spent), 6.0 + JUDGE_SPENT + 0.005)

    def test_no_verdict_is_recorded_at_the_wait(self):
        """No summary and no outcome for the case while it waits."""
        state = self.out["wait"]["state"]
        self.assertNotIn("summary", state)
        self.assertNotIn("outcome", state.get("cases", {}).get(CASE_ID, {}))

    def test_stop_ends_the_exam_failed(self):
        """resume --stop: exit 1, and no further role run or judge pass."""
        stop = self.out.get("stop")
        self.assertIsNotNone(stop, self.describe("first"))
        self.assertEqual(stop.returncode, 1, self.scene.describe(stop))
        self.assertEqual(self.out["end"]["roles"], self.out["wait"]["roles"])
        self.assertEqual(self.out["end"]["judges"], self.out["wait"]["judges"])

    def test_the_case_cut_short_has_no_verdict(self):
        """block works: Result failed, and the case's Result column says "no verdict"."""
        block = self.out.get("block")
        self.assertIsNotNone(block, self.describe("first"))
        self.assertEqual(block.returncode, 0, self.scene.describe(block))
        self.assertIn("Result: failed", lines_of(block.stdout))
        rows = table_rows(block.stdout)
        self.assertEqual(len(rows), 1, block.stdout)
        self.assertTrue(rows[0].startswith("| dv-small | Developer | "), rows[0])
        self.assertTrue(rows[0].endswith("| no verdict |"), rows[0])

    def test_the_cases_state_says_no_verdict(self):
        """outcome fail, no_verdict true, with a why."""
        info = self.out.get("end", {}).get("state", {}).get("cases", {}).get(CASE_ID, {})
        self.assertEqual(info.get("outcome"), "fail", info)
        self.assertIs(info.get("no_verdict"), True, info)
        self.assertTrue(info.get("why"), info)


class StartWaitTests(SceneTest):
    """Above $60 the exam waits before it starts; Troy's yes covers the whole (D241 A)."""

    NAME = "start"

    def test_the_exam_waits_before_it_starts(self):
        """Exit 2 with no role run and no judge pass."""
        self.assertEqual(self.out["first"].returncode, 2, self.describe("first"))
        self.assertEqual(self.out["wait"]["roles"], 0)
        self.assertEqual(self.out["wait"]["judges"], 0)

    def test_the_report_shows_both_totals(self):
        """--json: why start, the first round $77.00, the whole $229.00, a problem naming both."""
        report = report_of(self.out["first"])
        self.assertEqual(report.get("status"), WAITING, self.describe("first"))
        self.assertEqual(report.get("why"), "start")
        self.assertEqual(report.get("exam"), self.exam_name())
        self.assertAmount(report.get("estimate"), 77.00)
        self.assertAmount(report.get("whole"), 229.00)
        self.assertAmount(report.get("spent"), 0.0)
        self.assertAmount(report.get("left"), 77.00)
        problems = " ".join(report.get("problems") or [])
        self.assertIn("77", problems)
        self.assertIn("229", problems)

    def test_the_saved_state_waits_to_start(self):
        """state.json: why start, estimate $77.00, whole $229.00, $60 approved."""
        snap = self.out["wait"]
        self.assertWaits(snap, "start")
        self.assertAmount(snap["state"].get("estimate"), 77.00)
        self.assertAmount(snap["state"].get("whole"), 229.00)
        self.assertAmount(snap["state"].get("approved"), 60.0)

    def test_yes_and_stop_together_are_refused(self):
        """Exit 2; nothing runs, and the exam still waits."""
        both, after = self.out.get("both"), self.out.get("after_both")
        self.assertIsNotNone(both, self.describe("first"))
        self.assertEqual(both.returncode, 2, self.scene.describe(both))
        self.assertEqual((after["roles"], after["judges"]), (0, 0))
        self.assertWaits(after, "start")
        self.assertNotIn("summary", after["state"])

    def test_resume_without_a_flag_refuses(self):
        """Exit 2, no run, still waiting, and it names --yes and --stop."""
        plain, after = self.out.get("plain"), self.out.get("after_plain")
        self.assertIsNotNone(plain, self.describe("first"))
        self.assertEqual(plain.returncode, 2, self.scene.describe(plain))
        self.assertEqual((after["roles"], after["judges"]), (0, 0))
        self.assertWaits(after, "start")
        self.assertMentionsBothFlags(plain)

    def test_resume_yes_starts_it_with_the_whole_approved(self):
        """5 head runs, exit 0; $229.00 approved; the guard's estimate stays $77.00."""
        yes = self.out.get("yes")
        self.assertIsNotNone(yes, self.describe("first"))
        self.assertEqual(yes.returncode, 0, self.scene.describe(yes))
        self.assertEqual(self.out["end"]["roles"], 5)
        state = self.out["end"]["state"]
        self.assertAmount(state.get("approved"), 229.00)
        self.assertAmount(state.get("estimate"), 77.00)


class RunYesTests(SceneTest):
    """run --yes: Troy's yes covers the whole (D241 A)."""

    NAME = "yes"

    def test_run_yes_approves_the_whole(self):
        """Exit 0 after 5 head runs; approved = whole = $229.00; estimate $77.00."""
        self.assertEqual(self.out["proc"].returncode, 0, self.describe("proc"))
        self.assertEqual(self.out["end"]["roles"], 5)
        state = self.out["end"]["state"]
        self.assertAmount(state.get("whole"), 229.00)
        self.assertAmount(state.get("approved"), 229.00)
        self.assertAmount(state.get("estimate"), 77.00)


class StopBeforeStartTests(SceneTest):
    """resume --stop on a target waiting before it starts: no run, "no verdict" (10.3)."""

    NAME = "stopstart"

    def test_stop_ends_it_with_no_run(self):
        """Exit 1, with no role run or judge pass at any point."""
        stop = self.out.get("stop")
        self.assertIsNotNone(stop, self.describe("first"))
        self.assertEqual(self.out["first"].returncode, 2, self.describe("first"))
        self.assertEqual(stop.returncode, 1, self.scene.describe(stop))
        self.assertEqual((self.out["end"]["roles"], self.out["end"]["judges"]), (0, 0))

    def test_the_target_shows_no_verdict(self):
        """Result failed; the row says "no verdict", not "not fixed"."""
        block = self.out.get("block")
        self.assertIsNotNone(block, self.describe("first"))
        self.assertEqual(block.returncode, 0, self.scene.describe(block))
        self.assertIn("Result: failed", lines_of(block.stdout))
        rows = table_rows(block.stdout)
        self.assertEqual(len(rows), 1, block.stdout)
        self.assertTrue(rows[0].endswith("| no verdict |"), rows[0])


class RerunsTests(SceneTest):
    """A case whose reruns ran out ends with too few runs: "no verdict", not "worse" (7.2, 10.3)."""

    NAME = "reruns"

    def test_the_reruns_run_out(self):
        """Three void tries of one base run and 9 more runs: 12 role runs, and the exam fails."""
        self.assertEqual(self.out["end"]["roles"], 12, self.describe("proc"))
        self.assertEqual(self.out["end"]["markers"].count(BASE), 7)
        self.assertEqual(self.out["proc"].returncode, 1, self.describe("proc"))

    def test_the_case_has_no_verdict(self):
        """Result failed; the row says "no verdict"; the case's state says no_verdict."""
        block = self.out.get("block")
        self.assertIsNotNone(block, self.describe("proc"))
        self.assertIn("Result: failed", lines_of(block.stdout))
        rows = table_rows(block.stdout)
        self.assertEqual(len(rows), 1, block.stdout)
        self.assertTrue(rows[0].endswith("| no verdict |"), rows[0])
        info = self.out["end"]["state"].get("cases", {}).get(CASE_ID, {})
        self.assertEqual(info.get("outcome"), "fail", info)
        self.assertIs(info.get("no_verdict"), True, info)


class ProveGuardTests(SceneTest):
    """prove has no second round, and its guard waits like the exam's (10.3)."""

    NAME = "prove"

    def test_prove_waits_at_the_guard(self):
        """$5.00 a run against 1.5 x $5.40: two runs, then exit 2, why guard."""
        self.assertEqual(self.out["end"]["roles"], 2, self.describe("proc"))
        self.assertEqual(self.out["proc"].returncode, 2, self.describe("proc"))
        self.assertWaits(self.out["end"], "guard")

    def test_proves_whole_is_its_estimate(self):
        """5 runs at the Developer's $0.28 and two $2.00 judge passes: $5.40, no second round."""
        state = self.out["end"]["state"]
        self.assertAmount(state.get("estimate"), 5.40)
        self.assertAmount(state.get("whole"), 5.40)


if __name__ == "__main__":
    unittest.main()
