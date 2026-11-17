"""End to end through troy_exam.py with a stand-in CLI (F16 design 6, 7, 8, 9.2, 10, 11, 14.1).

Every scenario runs ``python troy-mode/exam/troy_exam.py`` as a subprocess
with TROY_EXAM_ROOT, CLAUDE_CONFIG_DIR, and TROY_EXAM_CLI (standin_cli.py)
in temp folders, ``--repo`` a fake tstack checkout (exam_helpers.Checkout:
this repository's role files and engine, a base commit, and heads that
change the Developer's agent file, brief.py, the harness, or the case), and
``--env`` an empty folder. The case, dv-small, is the Developer's DV1 on a
troy-mode project at F01's stage 3. No model is called and nothing reaches
the network. The scenarios are independent, so they run side by side in a
thread pool, started when the first test class needs one.

Groups of design 14.1 covered here: Blinding (no exam word in a built run;
the two versions' role-visible texts differ only by random letters; the
judge's folder), The run (the command line, the brief, a mangled brief, the
cost per model, the report, the folders deleted), Reuse (the base's runs
reused by the next exam), Budget (the per-run cap, the $60 line, the stop at
1.5 times, the pause at a usage limit, and resume), Comparison (a void run is
not counted), and The instruction set (affected).

Planted bugs of design 14.2 caught here:

- "the judge's folder holding the key":
  MainExamTests.test_judge_folder_holds_only_rubric_and_outputs.
- "a label that names its version": MainExamTests.test_judge_labels_are_r_numbers.
- "a later commit reachable in the case's origin": MainExamTests.test_no_later_commit_in_the_run.
- "the brief compared without the agent file":
  AffectedTests.test_an_agent_file_change_affects_the_case and
  RoleInputsTests.test_the_agent_file_is_an_input.
"""

import json
import os
import sys
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from exam_helpers import (CASE_ID, CLI_VERSION, HAIKU, JUDGE_RUBRIC, MOCK_BRANCH, SONNET,
                          Scenario, find_entries, git, new_dir, role_plan, run_records, same_path,
                          shared_checkout, word_hits, write_file, write_small_case)
from troyexam import INSTALLED_OFF
from troyexam.cases import load_case
from troyexam.ghstub import OFFLINE
from troyexam.instructions import GitTree, instruction_hash, short_hash
from troyexam.paths import Layout
from troyexam.project import build_project, copy_plugin, ensure_mirror, new_run_folder

UNIVERSAL = ("U1", "U2", "U3", "U4", "U5", "U6", "U7")
LOG_FIELDS = ("exam", "run", "time", "side", "case_version", "instructions", "cli", "models",
              "effort", "status", "passed", "cost", "minutes")
SCHEMA = {"type": "object", "properties": {"sets": {"type": "array", "items": {
    "type": "object", "properties": {
        "label": {"type": "string"},
        "criteria": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "integer"}, "pass": {"type": "boolean"},
            "evidence": {"type": "string"}}, "required": ["id", "pass", "evidence"]}}},
    "required": ["label", "criteria"]}}}, "required": ["sets"]}
ROW = "| dv-small | Developer | 5 of 5 | 5 of 5 | not worse |"

_LOCK = threading.Lock()
_FUTURES: dict = {}


def full_hash(ref: str) -> str:
    """The instruction hash of a commit of the fake checkout."""
    return instruction_hash(GitTree(shared_checkout().path, ref))


def new_exam(scene: Scenario, before: list) -> Path:
    """The exam folder that appeared since the listing before."""
    found = [p for p in scene.results() if p not in before]
    return found[-1] if found else None


def lines_of(text: str) -> list:
    """Lines without CR."""
    return text.replace("\r\n", "\n").split("\n")


# ---------------------------------------------------------------- scenarios

def scene_main(checkout) -> dict:
    """E1: base and head of a Developer case, then E2 on the same work root.

    E2 measures a second head on the same base. Its base runs come from E1's
    log; its first two role calls mangle the brief, its fifth hits the usage
    limit (the exam pauses), and after the pause the plan changes so the
    judge misgrades its first pass, and resume finishes the exam.
    """
    main = Scenario(role_plan(later=checkout.start.later))
    proc = main.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID)
    exams = main.results()
    exam = exams[-1] if exams else None
    out = {"main": main, "proc": proc, "exam": exam}
    if exam is not None:
        out["block"] = main.exam("block", exam.name)
        out["report"] = main.exam("report", exam.name)
    second = Scenario(role_plan(later=checkout.start.later,
                                calls={"1": {"brief": "mangle"}, "2": {"brief": "mangle"},
                                       "5": {"result": "limit"}}), root=main.root)
    before = second.results()
    first = second.exam("run", "--base", checkout.base, "--head", checkout.head2, "--case",
                        CASE_ID, "--jobs", "1")
    exam2 = new_exam(second, before)
    out.update(second=second, first=first, exam2=exam2,
               paused_claims=second.cli.claims("role"),
               paused_judges=second.cli.claims("judge"))
    second.cli.set_plan(role_plan(later=checkout.start.later, judge={"misgrade": [1]}))
    if exam2 is not None:
        out["resume"] = second.exam("resume", exam2.name)
        out["block2"] = second.exam("block", exam2.name)
    return out


def scene_line(checkout) -> dict:
    """E3: recorded runs at $10 make an estimate of $102, above $60, without --yes."""
    scene = Scenario(role_plan())
    log = scene.root / "cases" / f"{CASE_ID}.tsv"
    rows = ["\t".join(LOG_FIELDS)]
    for n in range(5):
        rows.append("\t".join(["2026-11-01-1", f"old{n}", "2026-11-01T10:00:00Z", "base", "1",
                               "0" * 64, "2.1.300", f"{HAIKU},{SONNET}", "high", "ok", "True",
                               "10.0", "3.0"]))
    write_file(log.parent, log.name, "\n".join(rows) + "\n")
    proc = scene.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID)
    return {"scene": scene, "proc": proc}


def scene_stop(checkout) -> dict:
    """E5: each run costs $20 against an estimate of $4.80, one job at a time."""
    scene = Scenario(role_plan(role={"costs": {HAIKU: 0.5, SONNET: 19.5}}))
    proc = scene.exam("run", "--base", checkout.base, "--head", checkout.head, "--case", CASE_ID,
                      "--jobs", "1")
    return {"scene": scene, "proc": proc}


def scene_affected(checkout) -> dict:
    """affected for four heads, then an exam of the refactor and its section."""
    scene = Scenario(role_plan())
    out = {"scene": scene}
    for name, head in (("agent", checkout.head), ("refactor", checkout.refactor),
                       ("harness", checkout.harness), ("case", checkout.case_change)):
        out[name] = scene.exam("affected", "--base", checkout.base, "--head", head, "--json")
    before = scene.results()
    out["run"] = scene.exam("run", "--base", checkout.base, "--head", checkout.refactor)
    exam = new_exam(scene, before)
    out["exam"] = exam
    if exam is not None:
        out["block"] = scene.exam("block", exam.name)
    hit_cases = new_dir("hitcases")
    write_small_case(hit_cases / "dv-hit", checkout.start, case_id="dv-hit",
                     branch="troy-mode/f01-3-sandbox")
    hit = Scenario(role_plan())
    out["hit_scene"] = hit
    out["hit"] = hit.exam("run", "--base", checkout.base, "--head", checkout.head, "--case",
                          "dv-hit", "--cases", str(hit_cases))
    return out


def scene_prove(checkout) -> dict:
    """prove --anchors with a right judge and an always wrong one; then E3 and E5."""
    good = Scenario(role_plan())
    proc = good.exam("prove", CASE_ID, "--anchors", "--ref", checkout.base)
    bad = Scenario(role_plan(judge={"misgrade": list(range(1, 9))}))
    bad_proc = bad.exam("prove", CASE_ID, "--anchors", "--ref", checkout.base)
    return {"good": good, "proc": proc, "bad": bad, "bad_proc": bad_proc,
            "line": scene_line(checkout), "stop": scene_stop(checkout)}


SCENES = {"main": scene_main, "affected": scene_affected, "prove": scene_prove}


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


# --------------------------------------------------------------------- tests

class MainExamTests(unittest.TestCase):
    """E1: one Developer case, base and head measured, every run passing."""

    @classmethod
    def setUpClass(cls):
        """Runs (or waits for) the main scenario."""
        cls.out = scenario("main")
        cls.scene = cls.out["main"]
        cls.checkout = shared_checkout()
        cls.roles = cls.scene.cli.calls("role")
        cls.judges = cls.scene.cli.calls("judge")
        cls.records = run_records(cls.out["exam"]) if cls.out["exam"] else []

    def describe(self) -> str:
        """The exam's output for messages."""
        return self.scene.describe(self.out["proc"])

    def test_the_exam_passes(self):
        """Exit 0: base 5 of 5, head 5 of 5, not worse."""
        self.assertEqual(self.out["proc"].returncode, 0, self.describe())
        self.assertIsNotNone(self.out["exam"], self.describe())
        self.assertRegex(self.out["exam"].name, r"^\d{4}-\d{2}-\d{2}-\d+$")

    def test_ten_role_runs_five_per_version_alternating(self):
        """5 runs of each version; the first five calls hold both (design 8.1)."""
        markers = [call["marker"] for call in self.roles]
        self.assertEqual(sorted(markers), ["head-one"] * 5 + ["none"] * 5, self.describe())
        self.assertEqual(set(markers[:5]), {"none", "head-one"}, markers)

    def test_each_run_has_the_designs_command_line(self):
        """Section 11.3 with tstack's names, a new session ID, and the case's cap."""
        sessions = set()
        for call in self.roles:
            with self.subTest(call=call["index"]):
                argv = call["argv"]
                plugin = argv[argv.index("--plugin-dir") + 1]
                session = argv[argv.index("--session-id") + 1]
                self.assertEqual(argv, [
                    "-p", argv[1], "--model", "haiku", "--plugin-dir", plugin,
                    "--settings", INSTALLED_OFF, "--permission-mode", "auto",
                    "--permission-prompts", "none", "--allowedTools", "Agent",
                    "--output-format", "stream-json", "--verbose", "--session-id", session,
                    "--max-budget-usd", "1.25"])
                self.assertEqual(Path(plugin).name, "tstack")
                self.assertRegex(Path(plugin).parent.name, r"^[a-z]{6}$")
                self.assertTrue(same_path(Path(plugin).parent.parent, self.scene.root / "runs"))
                self.assertEqual(str(uuid.UUID(session)), session.lower())
                sessions.add(session)
        self.assertEqual(len(sessions), 10)

    def test_the_session_runs_in_the_runs_project(self):
        """The CLI's folder is <run folder>/wordcount on the case's branch."""
        for call in self.roles:
            with self.subTest(call=call["index"]):
                plugin = Path(call["argv"][call["argv"].index("--plugin-dir") + 1])
                self.assertTrue(same_path(Path(call["cwd"]).parent, plugin.parent))
                self.assertEqual(Path(call["cwd"]).name, "wordcount")
                self.assertEqual(call["branch"], MOCK_BRANCH)
                self.assertIn("wordcount.git", call["run_root"])
                self.assertIn("tstack", call["run_root"])

    def test_the_driver_prompt_holds_the_brief(self):
        """The engine's DV1 brief for F01, the same in every run (design 11.3)."""
        briefs = {call["brief"] for call in self.roles}
        self.assertEqual(len(briefs), 1, briefs)
        brief = briefs.pop()
        self.assertTrue(brief.startswith("Task: DV1"), brief)
        self.assertIn("Item: F01, [F01 3/6 mock] Count words", brief)
        self.assertIn("Read first:", brief)
        self.assertIn("Checks to run:", brief)
        self.assertIn(self.scene.env_prefix.name, brief)
        for call in self.roles:
            self.assertIn("tstack:troy-developer", call["argv"][1])

    def test_the_sessions_environment(self):
        """Parent session variables and exam variables dropped; the run's variables set."""
        for call in self.roles:
            with self.subTest(call=call["index"]):
                env = call["env"]
                for name in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID",
                             "TROY_EXAM_ROOT", "TROY_EXAM_CLI", "MY_RUBRIC_HOME", "TSX_NOTE"):
                    self.assertNotIn(name, env)
                cwd = Path(call["cwd"])
                self.assertTrue(same_path(env["TROY_MODE_ENV_PREFIX"], self.scene.env_prefix))
                self.assertTrue(same_path(env["TROY_MODE_PYTHON"], sys.executable))
                self.assertTrue(same_path(env["PYTHONPATH"], cwd / "src"))
                self.assertTrue(same_path(env["UV_CACHE_DIR"], self.scene.root / "uv-cache"))
                self.assertEqual(env["MSYS_NO_PATHCONV"], "1")
                self.assertTrue(same_path(env["PATH"].split(os.pathsep)[0], cwd.parent / "bin"))
                self.assertTrue(same_path(env["CLAUDE_CONFIG_DIR"], self.scene.config))

    def test_the_role_sees_no_exam_word(self):
        """Paths, branch, variables, the prompt, the folder names, and gh's messages (6.1)."""
        for call in self.roles:
            with self.subTest(call=call["index"]):
                texts = [call["cwd"], call["branch"], call["argv"][1], *call["run_root"],
                         call["argv"][call["argv"].index("--plugin-dir") + 1]]
                texts += [f"{k}={v}" for k, v in call["env"].items()]
                for name in ("view", "checks", "comment", "api"):
                    texts += [str(x) for x in call["gh"][name]]
                hits = {text: word_hits(text) for text in texts if word_hits(text)}
                self.assertEqual(hits, {})

    def test_the_gh_stand_in_is_first_on_the_path(self):
        """gh pr view answers from the branch; gh pr comment and gh api are refused (4.2)."""
        for call in self.roles:
            with self.subTest(call=call["index"]):
                gh = call["gh"]
                self.assertIsNotNone(gh["found"])
                self.assertTrue(same_path(Path(gh["found"]).parent, Path(call["cwd"]).parent
                                          / "bin"))
                self.assertEqual(gh["view"][0], 0, gh["view"])
                self.assertEqual(json.loads(gh["view"][1]),
                                 {"number": 1, "headRefName": MOCK_BRANCH})
                self.assertEqual(gh["checks"][0], 1)
                self.assertEqual((gh["comment"][0], gh["comment"][1]), (1, ""))
                self.assertEqual(gh["comment"][2].replace("\r\n", "\n"), OFFLINE)
                self.assertEqual(gh["api"][0], 1)

    def test_no_later_commit_in_the_run(self):
        """The pilot's later commit cannot be read in the project or its origin (4.2, 14.2)."""
        for call in self.roles:
            with self.subTest(call=call["index"]):
                self.assertNotEqual(call["later_in_project"], 0)
                self.assertNotEqual(call["later_in_origin"], 0)

    def test_the_two_versions_differ_only_by_random_letters(self):
        """A base run's and a head run's command line, variables, and gh output (6.1)."""
        def normal(call) -> str:
            """The call's role-visible texts with its letters and session ID replaced."""
            argv = call["argv"]
            letters = Path(argv[argv.index("--plugin-dir") + 1]).parent.name
            session = argv[argv.index("--session-id") + 1]
            data = json.dumps({"argv": argv, "env": call["env"], "cwd": call["cwd"],
                               "branch": call["branch"], "gh": call["gh"],
                               "run_root": call["run_root"]}, sort_keys=True)
            return data.replace(letters, "XXXXXX").replace(session, "SESSION")
        base = [c for c in self.roles if c["marker"] == "none"]
        head = [c for c in self.roles if c["marker"] == "head-one"]
        self.assertTrue(base and head, self.describe())
        self.assertEqual(normal(base[0]), normal(head[0]))

    def test_run_records(self):
        """Ten run.json files: the version, the hash, the CLI, the models, cost per model."""
        self.assertEqual(len(self.records), 10, self.describe())
        commits = {"base": self.checkout.base, "head": self.checkout.head}
        for record in self.records:
            with self.subTest(run=record.get("run")):
                side = record["side"]
                self.assertIn(side, commits)
                self.assertEqual((record["case"], record["case_version"]), (CASE_ID, 1))
                self.assertEqual(record["commit"], commits[side])
                self.assertEqual(record["instructions"], full_hash(commits[side]))
                self.assertEqual((record["cli"], record["effort"]), (CLI_VERSION, "high"))
                self.assertEqual(set(record["models"]), {HAIKU, SONNET})
                self.assertEqual(record["status"], "ok")
                self.assertIs(record["passed"], True)
                self.assertAlmostEqual(record["cost"], 0.045, places=6)
                self.assertEqual(set(record["costs"]), {HAIKU, SONNET})
                self.assertAlmostEqual(record["costs"][HAIKU], 0.003, places=6)
                self.assertAlmostEqual(record["costs"][SONNET], 0.042, places=6)
                self.assertTrue(record["time"].endswith("Z"), record["time"])
                self.assertLessEqual(set(UNIVERSAL), set(record["criteria"]))
                for name, value in record["criteria"].items():
                    self.assertIs(value["passed"], True, f"{name}: {value}")
        self.assertEqual(len({r["run"] for r in self.records}), 10)
        self.assertEqual(sorted(r["side"] for r in self.records), ["base"] * 5 + ["head"] * 5)

    def test_reports_were_found_in_the_handback_and_in_the_last_message(self):
        """Half the runs end with SubagentHandback, half with a text; U1 passes in all."""
        self.assertEqual({call["report_how"] for call in self.roles}, {"handback", "text"})
        self.assertTrue(all(r["criteria"]["U1"]["passed"] for r in self.records))

    def test_the_case_log(self):
        """cases/dv-small.tsv: a header and one row per run (design 8.2, 11.1).

        E2 runs on the same work root before these tests read the log, so only
        E1's rows are counted here; E2's are checked below.
        """
        path = self.scene.root / "cases" / f"{CASE_ID}.tsv"
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
        self.assertEqual(lines[0], "\t".join(LOG_FIELDS))
        rows = [dict(zip(LOG_FIELDS, line.split("\t"))) for line in lines[1:]]
        rows = [row for row in rows if row["exam"] == self.out["exam"].name]
        self.assertEqual(len(rows), 10)
        hashes = {"base": full_hash(self.checkout.base), "head": full_hash(self.checkout.head)}
        for row in rows:
            self.assertEqual(row["instructions"], hashes[row["side"]])
            self.assertEqual((row["cli"], row["effort"], row["status"]),
                             (CLI_VERSION, "high", "ok"))

    def test_the_runs_folders_are_deleted(self):
        """runs/ and the CLI's projects/ folders are empty after the exam (11.3)."""
        runs = self.scene.root / "runs"
        self.assertEqual(sorted(runs.iterdir()) if runs.is_dir() else [], [])
        projects = self.scene.config / "projects"
        self.assertEqual(sorted(projects.iterdir()) if projects.is_dir() else [], [])
        for call in self.roles:
            self.assertFalse(Path(call["transcript_folder"]).exists())

    def test_results_hold_the_report_summary_and_transcripts(self):
        """report.md, summary.json, and the runs' transcripts are kept (11.1)."""
        exam = self.out["exam"]
        self.assertTrue((exam / "report.md").is_file())
        self.assertIsInstance(json.loads((exam / "summary.json").read_text(encoding="utf-8")),
                              dict)
        self.assertGreaterEqual(len(list(exam.rglob("*.jsonl"))), 10)
        report = self.out["report"]
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertIn(CASE_ID, report.stdout)

    def test_the_block(self):
        """The PR's section (design 9.3) for this exam."""
        block = self.out["block"]
        self.assertEqual(block.returncode, 0, block.stderr)
        lines = lines_of(block.stdout.strip())
        self.assertEqual(lines[:2], ["## Role exam", ""])
        self.assertIn("Result: passed", lines)
        self.assertIn(f"Instructions: {short_hash(full_hash(self.checkout.head))}", lines)
        self.assertIn("Cases: 1 run, 0 not affected", lines)
        runs = [line for line in lines if line.startswith("Runs: ")]
        self.assertEqual(len(runs), 1, lines)
        self.assertRegex(runs[0], r"^Runs: 10, 0 of them reused from the base; \$\d+\.\d\d; "
                                  r"\d+ h \d\d min$")
        self.assertIn("| Case | Role | Base | Head | Result |", lines)
        self.assertIn(ROW, lines)
        report = [line for line in lines if line.startswith("Report: ")]
        self.assertEqual(len(report), 1)
        self.assertTrue(same_path(report[0][len("Report: "):], self.out["exam"] / "report.md"))

    def test_one_judge_pass_with_its_command_line(self):
        """One judge session for the case: opus, three tools, the schema, no plugin (11.4)."""
        self.assertEqual(len(self.judges), 1, self.describe())
        argv = self.judges[0]["argv"]
        schema_text = argv[argv.index("--json-schema") + 1]
        self.assertEqual(json.loads(schema_text), SCHEMA)
        self.assertEqual(argv, ["-p", argv[1], "--model", "opus", "--effort", "high",
                                "--tools", "Read,Glob,Grep", "--settings", INSTALLED_OFF,
                                "--json-schema", schema_text, "--output-format", "json",
                                "--max-budget-usd", argv[-1]])
        self.assertRegex(argv[-1], r"^\d+\.\d\d$")
        self.assertIn("rubric.md", argv[1])

    def test_judge_folder_holds_only_rubric_and_outputs(self):
        """No key, brief, agent file, transcript, model name, or cost (6.2, 14.2)."""
        judge = self.judges[0]
        files = judge["files"]
        self.assertIn("rubric.md", files)
        self.assertEqual(judge["contents"]["rubric.md"].replace("\r\n", "\n"), JUDGE_RUBRIC)
        for name in files:
            with self.subTest(file=name):
                parts = name.split("/")
                if name != "rubric.md":
                    self.assertRegex(parts[0], r"^R\d{2}$")
                self.assertNotIn("key", parts[-1].lower())
                self.assertFalse(name.endswith(".jsonl"))
                text = judge["contents"][name]
                for word in ("sonnet", "haiku", "opus", "claude-", "costUSD", "total_cost",
                             "anchor", "Read first:", "BEGIN", '"type": "assistant"',
                             "## Report", "Common rules"):
                    self.assertNotIn(word, text)
                for record in self.records:
                    if len(str(record["run"])) >= 6:
                        self.assertNotIn(str(record["run"]), text)
        keys = [p for p in self.out["exam"].rglob("key.json")]
        self.assertTrue(keys, "no key.json in the results folder")
        judge_folder = Path(judge["cwd"]).resolve()
        for key in keys:
            self.assertNotIn(judge_folder, key.resolve().parents)
        mapping = json.loads(keys[0].read_text(encoding="utf-8"))
        self.assertEqual(sorted(mapping), judge["labels"])
        self.assertEqual(set(mapping.values()) - {"anchor-fail", "anchor-pass"},
                         {r["run"] for r in self.records})

    def test_judge_labels_are_r_numbers(self):
        """Ten runs and two anchors under R01 to R12, none naming its version (6.2, 14.2)."""
        labels = self.judges[0]["labels"]
        self.assertEqual(labels, [f"R{i:02d}" for i in range(1, 13)])
        self.assertTrue(all(name.startswith("R") for name in self.judges[0]["files"]
                            if name != "rubric.md"))

    def test_judge_sees_placeholders_not_paths(self):
        """The run's project and plugin paths are written <project> and <plugin> (6.2)."""
        contents = "\n".join(self.judges[0]["contents"].values())
        for call in self.roles:
            plugin = call["argv"][call["argv"].index("--plugin-dir") + 1]
            for path in (call["cwd"], plugin):
                self.assertNotIn(path, contents)
                self.assertNotIn(path.replace("\\", "/"), contents)
        self.assertIn("<project>", contents)
        self.assertIn("<plugin>", contents)


class ResumeTests(unittest.TestCase):
    """E2: the base's runs reused, two mangled briefs, a usage limit, and resume."""

    @classmethod
    def setUpClass(cls):
        """Runs (or waits for) the main scenario, whose second half is this one."""
        cls.out = scenario("main")
        cls.scene = cls.out["second"]
        cls.checkout = shared_checkout()
        cls.roles = cls.scene.cli.calls("role")

    def describe(self, key: str = "first") -> str:
        """One command's output."""
        return self.scene.describe(self.out[key])

    def test_the_exam_pauses_at_the_usage_limit(self):
        """Exit 2 after the fifth call, with no judge pass yet (11.5)."""
        self.assertEqual(self.out["first"].returncode, 2, self.describe())
        self.assertIsNotNone(self.out["exam2"])
        self.assertEqual(self.out["paused_claims"], 5, self.describe())
        self.assertEqual(self.out["paused_judges"], 0)

    def test_the_bases_runs_were_reused(self):
        """Every role call ran the head: the base's five runs came from E1 (8.2)."""
        self.assertTrue(self.roles, self.describe())
        self.assertEqual({call["marker"] for call in self.roles}, {"head-two"})

    def test_a_mangled_brief_runs_again_then_on_sonnet(self):
        """Calls 1 and 2 changed the brief; the third try had a sonnet main session (11.5)."""
        by_index = {call["index"]: call for call in self.roles}
        model = {i: c["argv"][c["argv"].index("--model") + 1] for i, c in by_index.items()}
        self.assertEqual(model[1], "haiku")
        self.assertEqual(model[3], "sonnet")
        self.assertEqual(by_index[1]["brief"], by_index[3]["brief"])

    def test_resume_finishes_the_exam(self):
        """Three more runs, a judge pass voided by its anchors and one more, then a pass."""
        resume = self.out["resume"]
        self.assertEqual(resume.returncode, 0, self.describe("resume"))
        self.assertEqual(self.scene.cli.claims("role"), 8)
        self.assertEqual(self.scene.cli.claims("judge"), 2)
        judges = self.scene.cli.calls("judge")
        self.assertEqual([j["inverted"] for j in judges], [True, False])

    def test_a_void_run_is_recorded_and_not_counted(self):
        """run.json of a void run has passed null; the head still counts 5 of 5 (7.1)."""
        records = run_records(self.out["exam2"])
        void = [r for r in records if r["status"] == "void"]
        self.assertTrue(void, [r["status"] for r in records])
        self.assertTrue(all(r["passed"] is None for r in void))
        lines = lines_of(self.out["block2"].stdout)
        self.assertIn(ROW, lines)
        self.assertIn("Result: passed", lines)

    def test_the_block_names_the_reused_runs(self):
        """The Runs line says five came from the base."""
        runs = [line for line in lines_of(self.out["block2"].stdout) if line.startswith("Runs: ")]
        self.assertEqual(len(runs), 1, self.out["block2"].stdout)
        self.assertIn("5 of them reused from the base", runs[0])
        self.assertIn(f"Instructions: {short_hash(full_hash(self.checkout.head2))}",
                      lines_of(self.out["block2"].stdout))

    def test_the_case_log_gains_the_heads_runs(self):
        """Five more ok rows of the second head."""
        path = self.scene.root / "cases" / f"{CASE_ID}.tsv"
        rows = [dict(zip(LOG_FIELDS, line.split("\t")))
                for line in path.read_text(encoding="utf-8").splitlines()[1:] if line]
        head2 = full_hash(self.checkout.head2)
        mine = [r for r in rows if r["instructions"] == head2 and r["status"] == "ok"]
        self.assertEqual(len(mine), 5)
        self.assertEqual({r["side"] for r in mine}, {"head"})


class BudgetLineTests(unittest.TestCase):
    """E3: above $60 the exam shows its estimate and starts nothing without --yes (10.2)."""

    @classmethod
    def setUpClass(cls):
        """Runs (or waits for) the scenario."""
        cls.out = scenario("prove")["line"]
        cls.scene = cls.out["scene"]

    def test_exit_2_with_the_estimate_and_no_run(self):
        """$102: ten runs at the recorded median of $10 plus a $2 judge pass."""
        proc = self.out["proc"]
        self.assertEqual(proc.returncode, 2, self.scene.describe(proc))
        self.assertIn("102", proc.stdout + proc.stderr)
        self.assertEqual(self.scene.cli.claims("role"), 0)
        self.assertEqual(self.scene.cli.claims("judge"), 0)
        runs = self.scene.root / "runs"
        self.assertEqual(sorted(runs.iterdir()) if runs.is_dir() else [], [])


class BudgetStopTests(unittest.TestCase):
    """E5: no new run once spending reaches 1.5 times the estimate (10.2)."""

    @classmethod
    def setUpClass(cls):
        """Runs (or waits for) the scenario."""
        cls.out = scenario("prove")["stop"]
        cls.scene = cls.out["scene"]

    def test_one_run_then_stop(self):
        """$20 spent against a $7.20 limit: the exam starts no second run and does not pass."""
        proc = self.out["proc"]
        self.assertEqual(self.scene.cli.claims("role"), 1, self.scene.describe(proc))
        self.assertIn(proc.returncode, (1, 2), self.scene.describe(proc))


class AffectedTests(unittest.TestCase):
    """affected (design 9.2) and an exam that affects nothing (14.3 step 4)."""

    @classmethod
    def setUpClass(cls):
        """Runs (or waits for) the scenario."""
        cls.out = scenario("affected")
        cls.scene = cls.out["scene"]
        cls.checkout = shared_checkout()

    def entry(self, key: str) -> dict:
        """dv-small's entry of one affected report."""
        proc = self.out[key]
        self.assertEqual(proc.returncode, 0, self.scene.describe(proc))
        entries = [e for e in find_entries(json.loads(proc.stdout))
                   if e.get("case") == CASE_ID and "affected" in e]
        self.assertTrue(entries, proc.stdout)
        self.assertEqual(len({bool(e["affected"]) for e in entries}), 1, proc.stdout)
        return entries[0]

    def test_an_agent_file_change_affects_the_case(self):
        """The brief is the same; the agent file is not (design 14.2)."""
        self.assertIs(self.entry("agent")["affected"], True)

    def test_a_refactor_that_renders_the_same_brief_affects_nothing(self):
        """A comment at the end of brief.py."""
        self.assertIs(self.entry("refactor")["affected"], False)

    def test_a_harness_change_affects_every_case(self):
        """troy-mode/exam/troyexam changed; "why" names the harness."""
        entry = self.entry("harness")
        self.assertIs(entry["affected"], True)
        why = " ".join(entry["why"]).lower()
        self.assertTrue("harness" in why or "troyexam" in why, entry["why"])

    def test_a_case_change_affects_that_case(self):
        """Its rubric changed."""
        self.assertIs(self.entry("case")["affected"], True)

    def test_an_exam_with_no_case_affected(self):
        """Exit 0 at no cost: no role run, no judge, and the section says so."""
        proc = self.out["run"]
        self.assertEqual(proc.returncode, 0, self.scene.describe(proc))
        self.assertEqual(self.scene.cli.claims("role"), 0)
        self.assertEqual(self.scene.cli.claims("judge"), 0)
        self.assertIsNotNone(self.out["exam"])
        lines = lines_of(self.out["block"].stdout)
        self.assertIn("Result: no case affected", lines)
        self.assertIn(f"Instructions: {short_hash(full_hash(self.checkout.refactor))}", lines)
        self.assertIn("Cases: 0 run, 1 not affected", lines)
        self.assertTrue(any(line.startswith("Runs: 0, 0 of them reused from the base")
                            for line in lines), lines)

    def test_a_blinding_hit_refuses_to_start(self):
        """A case branch holding "sandbox": exit 2 and no run (design 6.1)."""
        proc, hit = self.out["hit"], self.out["hit_scene"]
        self.assertEqual(proc.returncode, 2, hit.describe(proc))
        self.assertEqual(hit.cli.claims("role"), 0)


class ProveTests(unittest.TestCase):
    """prove --anchors: the grading separates the anchors, or the rubric is unclear (4.5, 6.2)."""

    @classmethod
    def setUpClass(cls):
        """Runs (or waits for) the scenario."""
        cls.out = scenario("prove")

    def test_the_anchors_are_told_apart(self):
        """Exit 0 after two separate judge passes over the two anchors, with no role run."""
        good, proc = self.out["good"], self.out["proc"]
        self.assertEqual(proc.returncode, 0, good.describe(proc))
        judges = good.cli.calls("judge")
        self.assertEqual(len(judges), 2, good.describe(proc))
        for judge in judges:
            self.assertEqual(judge["labels"], ["R01", "R02"])
        self.assertEqual(good.cli.claims("role"), 0)

    def test_a_judge_that_misgrades_twice_stops_the_case(self):
        """One more pass after the first miss, then "rubric unclear"."""
        bad, proc = self.out["bad"], self.out["bad_proc"]
        self.assertNotEqual(proc.returncode, 0, bad.describe(proc))
        self.assertEqual(bad.cli.claims("judge"), 2, bad.describe(proc))
        self.assertIn("rubric unclear", (proc.stdout + proc.stderr).lower())


class LogCommandTests(unittest.TestCase):
    """troy_exam.py log: one row of a hillclimb's decision log (design 8.3)."""

    def test_a_row_is_added(self):
        """climb/<name>/decision.tsv with a header and the row; delta is after minus before."""
        scene = Scenario(role_plan())
        proc = scene.exam("log", "notes1", "--id", "1", "--hypothesis",
                          "a fixed sentence, because the notes drifted", "--change", "DV1 brief",
                          "--before", "2", "--after", "5", "--gate", "held", "--verdict", "kept")
        self.assertEqual(proc.returncode, 0, scene.describe(proc))
        path = scene.root / "climb" / "notes1" / "decision.tsv"
        lines = path.read_text(encoding="utf-8").splitlines()
        columns = ("id", "hypothesis", "change", "before", "after", "delta", "gate", "verdict",
                   "note")
        self.assertEqual(lines[0], "\t".join(columns))
        row = dict(zip(columns, lines[1].split("\t") + [""] * 9))
        self.assertEqual((row["id"], row["hypothesis"], row["change"], row["before"],
                          row["after"], row["gate"], row["verdict"]),
                         ("1", "a fixed sentence, because the notes drifted", "DV1 brief", "2",
                          "5", "held", "kept"))
        self.assertEqual(int(row["delta"]), 3)


class RoleInputsTests(unittest.TestCase):
    """role_inputs: what the role would get, the agent file among it (design 9.2)."""

    @classmethod
    def setUpClass(cls):
        """One project of the case and the base's and head's plugin copies."""
        from troyexam.affected import role_inputs
        checkout = shared_checkout()
        layout = Layout(new_dir("riroot"))
        case = load_case(checkout.path / "troy-mode" / "exam" / "cases" / CASE_ID)
        mirror = ensure_mirror(layout, case.start.repository, case.start.commit)
        folder = new_run_folder(layout, case.start.repository)
        build_project(case, folder, mirror)
        prefix = new_dir("rienv")
        env = dict(os.environ, TROY_MODE_ENV_PREFIX=str(prefix))
        cls.base_plugin = new_dir("ribase") / "tstack"
        cls.head_plugin = new_dir("rihead") / "tstack"
        copy_plugin(checkout.path, checkout.base, cls.base_plugin)
        copy_plugin(checkout.path, checkout.head, cls.head_plugin)
        cls.base = role_inputs(case, cls.base_plugin, folder.project, env)
        cls.head = role_inputs(case, cls.head_plugin, folder.project, env)
        cls.project = folder.project

    def test_the_agent_file_is_an_input(self):
        """"agent" holds the version's agent file, which the head changed (14.2)."""
        agent = (self.base_plugin / "agents" / "troy-developer.md").read_text(encoding="utf-8")
        self.assertEqual(self.base["agent"].replace("\r\n", "\n"), agent.replace("\r\n", "\n"))
        self.assertNotEqual(self.base["agent"], self.head["agent"])
        self.assertIn("Marker: head-one", self.head["agent"])

    def test_the_brief_is_the_same_for_both(self):
        """The head changed no brief module."""
        self.assertTrue(self.base["brief"].startswith("Task: DV1"), self.base["brief"][:200])
        self.assertEqual(self.base["brief"], self.head["brief"])

    def test_templates_and_named_skills_are_inputs(self):
        """The files the role reads from the plugin."""
        for path in ("troy-mode/templates/feature-design.md", "skills/technical-writing/SKILL.md"):
            with self.subTest(path=path):
                self.assertIn(path, self.base)
                text = (self.base_plugin / path).read_text(encoding="utf-8")
                self.assertEqual(self.base[path].replace("\r\n", "\n"),
                                 text.replace("\r\n", "\n"))

    def test_no_model_was_needed(self):
        """The project is unchanged by rendering briefs."""
        self.assertEqual(git(self.project, "status", "--porcelain").strip(), "")


if __name__ == "__main__":
    unittest.main()
