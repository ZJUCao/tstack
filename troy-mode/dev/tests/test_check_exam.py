"""Tests for check_exam.py, the CI check that a role instruction change carries its exam (F16 9.4).

Assumed interface (the design fixes the behavior, not the names; these tests
fix them, from the contract's suggestion):

- ``check_exam.main(argv) -> int`` reads the GitHub event JSON named by
  ``--event <path>``, or else by the GITHUB_EVENT_PATH variable, and uses its
  ``pull_request.body`` (None is an empty body), ``pull_request.base.sha``,
  and ``pull_request.head.sha``, in the git repository ``--repo <path>``
  (default: the current folder). It returns 0 to pass and 1 to fail. Run as
  a script, its exit code is that value (troy-docs.yml runs
  ``python3 troy-mode/dev/check_exam.py`` with no arguments).
- It compares ``troyexam.instructions.instruction_hash`` at the merge base of
  base and head with the hash at head. Equal means the PR changes no file of
  the instruction set, and the check passes (design 9.4 step 1). Otherwise the
  description must hold a "## Role exam" section, outside fenced code blocks,
  whose ``Instructions:`` equals the first 12 characters of the head's hash
  and whose ``Result:`` is ``passed``, ``no case affected``, or
  ``failed, accepted by Troy ...`` (step 2).
- ``check_exam.parse_section(body) -> dict | None``: the section's
  ``"result"`` and ``"instructions"`` values, or None when the body has no
  such section outside a fenced code block. CRLF bodies, as GitHub stores
  edited descriptions, read like LF ones.
- ``check_exam.result_ok(text) -> bool``: whether a Result value lets the PR merge.

Planted bug of design 14.2 caught here: "check_exam.py accepting a stale hash"
(MainTests.test_a_stale_hash_fails).
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

DEV = Path(__file__).resolve().parents[1]
REPO_ROOT = DEV.parents[1]
SCRIPT = DEV / "check_exam.py"
for _folder in (DEV, REPO_ROOT / "troy-mode" / "exam"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import check_exam  # noqa: E402  (after the path setup)
from troyexam.instructions import GitTree, instruction_hash, short_hash  # noqa: E402
from troyexam.report import block  # noqa: E402

_DROPPED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CEILING_DIRECTORIES",
            "GITHUB_EVENT_PATH", "PYTHONIOENCODING", "PYTHONUTF8")
SKILL = ("# troy-mode\n\n## Start\n\nStart.\n\n## Running a role\n\nRole text.\n\n"
         "### The report\n\nReport text.\n\n## The summary for Troy\n\nSummary text.\n\n"
         "## Feature loop\n\nLoop text.\n")
FILES = {
    "README.md": "# tstack\n",
    "agents/troy-developer.md": "# Developer\n\nWrite the mock.\n",
    "troy-mode/roles/common.md": "# Common rules\n\n1. Read the rules.\n",
    "troy-mode/templates/feature-design.md": "# Design\n",
    "troy-mode/flow/troyflow/__init__.py": 'PLUGIN_PREFIX = "tstack:"\n',
    "troy-mode/flow/troyflow/brief.py": "from . import PLUGIN_PREFIX\n",
    "skills/troy-mode/SKILL.md": SKILL,
}


def _env() -> dict:
    """An environment that isolates git from the machine's settings."""
    env = {k: v for k, v in os.environ.items() if k not in _DROPPED}
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    return env


def git(cwd: Path, *args: str) -> str:
    """Runs git with a test identity and returns its output; raises when it fails."""
    proc = subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                           "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
                          cwd=str(cwd), env=_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout


def commit(repo: Path, files: dict, message: str) -> str:
    """Writes files, commits them, and returns the commit's ID."""
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


def section(result: str, instructions: str, newline: str = "\n") -> str:
    """A PR description that holds a Role exam section."""
    text = ("Adds the fixed mock-note sentences.\n\n## Role exam\n\n"
            f"Result: {result}\nInstructions: {instructions}\n"
            "Cases: 1 run, 11 not affected\n"
            "Runs: 10, 5 of them reused from the base; $3.10; 0 h 20 min\n\n"
            "| Case | Role | Base | Head | Result |\n| --- | --- | --- | --- | --- |\n"
            "| dv-mock-notes | Developer | 2 of 5 | 5 of 5 | fixed |\n\n"
            "Report: D:\\Troy\\troy-mode-work\\results\\2026-11-20-1\\report.md\n\n"
            "## Notes\n\nNone.\n")
    return text.replace("\n", newline)


class CheckExamCase(unittest.TestCase):
    """A repository with a base and heads that change, or do not change, instructions."""

    @classmethod
    def setUpClass(cls):
        """Builds the repository once."""
        cls._tmp = tempfile.TemporaryDirectory(prefix="chx-", ignore_cleanup_errors=True)
        cls.repo = Path(cls._tmp.name) / "tstack"
        cls.repo.mkdir()
        git(cls.repo, "init", "-q", "-b", "main")
        cls.base = commit(cls.repo, FILES, "Base")

        def branch(name: str, files: dict, start: str = None) -> str:
            """Commits files on a branch made from a commit (default the base)."""
            git(cls.repo, "checkout", "-q", "-B", name, start or cls.base)
            return commit(cls.repo, files, name)

        cls.docs = branch("docs", {"README.md": "# tstack\n\nMore words.\n"})
        cls.agent = branch("agent", {"agents/troy-developer.md":
                                     "# Developer\n\nWrite the mock with fixed notes.\n"})
        cls.main2 = branch("main2", {"troy-mode/templates/feature-design.md": "# Design 2\n"})
        cls.loop = branch("loop", {"skills/troy-mode/SKILL.md":
                                   SKILL.replace("Loop text.", "Loop text, longer.")})
        cls.role = branch("role", {"skills/troy-mode/SKILL.md":
                                   SKILL.replace("Report text.", "Report text, longer.")})
        git(cls.repo, "checkout", "-q", "main")
        cls.events = Path(cls._tmp.name) / "events"
        cls.events.mkdir()
        cls._count = 0

    @classmethod
    def tearDownClass(cls):
        """Removes the repository."""
        cls._tmp.cleanup()

    def short(self, sha: str) -> str:
        """The first 12 characters of a commit's instruction hash."""
        return short_hash(instruction_hash(GitTree(self.repo, sha)))

    def event(self, body, head: str, base: str = None) -> Path:
        """Writes a pull_request event and returns its path."""
        type(self)._count += 1
        path = self.events / f"event{self._count}.json"
        data = {"action": "edited", "pull_request": {
            "number": 90, "body": body, "base": {"ref": "main", "sha": base or self.base},
            "head": {"ref": "claude/x", "sha": head}}}
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def check(self, body, head: str, base: str = None) -> int:
        """check_exam.main on one event, with its output captured."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            return check_exam.main(["--event", str(self.event(body, head, base)),
                                    "--repo", str(self.repo)])


class MainTests(CheckExamCase):
    """main: design 9.4's two rules."""

    def test_the_fixture_changes_what_it_should(self):
        """The agent and role-section heads change the hash; the others do not."""
        base = self.short(self.base)
        self.assertEqual(self.short(self.docs), base)
        self.assertEqual(self.short(self.loop), base)
        self.assertNotEqual(self.short(self.agent), base)
        self.assertNotEqual(self.short(self.role), base)
        self.assertNotEqual(self.short(self.main2), base)

    def test_no_instruction_change_passes_without_a_section(self):
        """A README change needs no exam, whatever the description says."""
        self.assertEqual(self.check("Fixes a typo.", self.docs), 0)
        self.assertEqual(self.check(None, self.docs), 0)
        self.assertEqual(self.check(section("failed", "000000000000"), self.docs), 0)

    def test_another_skill_section_is_not_an_instruction_change(self):
        """SKILL.md's Feature loop is not one of the two role sections (9.1)."""
        self.assertEqual(self.check("", self.loop), 0)

    def test_the_merge_base_is_compared_not_the_bases_tip(self):
        """main moved on with a template change; the PR itself changed only the README."""
        self.assertEqual(self.check("Fixes a typo.", self.docs, base=self.main2), 0)

    def test_an_instruction_change_needs_the_section(self):
        """No section, an empty body, or a null body fails."""
        for body in ("Adds the fixed sentences.", "", None):
            with self.subTest(body=body):
                self.assertEqual(self.check(body, self.agent), 1)

    def test_a_role_section_change_needs_the_section(self):
        """A change to "The report" under "Running a role"."""
        self.assertEqual(self.check("", self.role), 1)
        self.assertEqual(self.check(section("passed", self.short(self.role)), self.role), 0)

    def test_the_heads_hash_and_passed_pass(self):
        """The right hash with passed."""
        self.assertEqual(self.check(section("passed", self.short(self.agent)), self.agent), 0)

    def test_a_stale_hash_fails(self):
        """The section of an earlier push, or of the base, no longer matches (design 14.2)."""
        self.assertEqual(self.check(section("passed", self.short(self.base)), self.agent), 1)
        self.assertEqual(self.check(section("passed", self.short(self.role)), self.agent), 1)

    def test_failed_fails(self):
        """A failed exam that Troy did not accept."""
        self.assertEqual(self.check(section("failed", self.short(self.agent)), self.agent), 1)

    def test_accepted_and_no_case_affected_pass(self):
        """failed, accepted by Troy ..., and no case affected."""
        right = self.short(self.agent)
        accepted = "failed, accepted by Troy on 2026-11-21: the judge misread one report"
        self.assertEqual(self.check(section(accepted, right), self.agent), 0)
        self.assertEqual(self.check(section("no case affected", right), self.agent), 0)

    def test_a_section_in_a_code_block_only_fails(self):
        """A section quoted inside a fence is not the PR's section."""
        body = ("Paste this after the exam:\n\n```text\n## Role exam\n\nResult: passed\n"
                f"Instructions: {self.short(self.agent)}\n```\n")
        self.assertEqual(self.check(body, self.agent), 1)

    def test_a_crlf_description_passes(self):
        """GitHub keeps an edited description with CRLF line ends."""
        body = section("passed", self.short(self.agent), newline="\r\n")
        self.assertEqual(self.check(body, self.agent), 0)

    def test_the_section_block_prints_passes(self):
        """troyexam.report.block's own output, pasted into the description."""
        summary = {"result": "passed", "instructions": instruction_hash(GitTree(self.repo,
                                                                                self.agent)),
                   "cases_run": 2, "cases_not_affected": 10, "runs": 20, "reused": 10,
                   "cost": 14.2, "minutes": 65,
                   "rows": [{"case": "dv-mock-notes", "role": "developer", "base": 2,
                             "head": 5, "of": 5, "result": "fixed"}],
                   "report": r"D:\Troy\troy-mode-work\results\2026-11-20-1\report.md"}
        body = "Adds the sentences.\n\n" + block(summary) + "\n## Test plan\n\nNone.\n"
        self.assertEqual(self.check(body, self.agent), 0)

    def test_the_event_path_variable(self):
        """Without --event, GITHUB_EVENT_PATH names the event (as in CI)."""
        good = self.event(section("passed", self.short(self.agent)), self.agent)
        bad = self.event("No section.", self.agent)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            with mock.patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(good)}):
                self.assertEqual(check_exam.main(["--repo", str(self.repo)]), 0)
            with mock.patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(bad)}):
                self.assertEqual(check_exam.main(["--repo", str(self.repo)]), 1)


class ScriptTests(CheckExamCase):
    """check_exam.py as CI runs it: a script whose exit code is the result."""

    def run_script(self, *args: str, cwd: Path = None, event: Path = None):
        """Runs the script with this Python."""
        env = _env()
        if event is not None:
            env["GITHUB_EVENT_PATH"] = str(event)
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(cwd or self.repo),
                              env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", stdin=subprocess.DEVNULL, timeout=120,
                              check=False)

    def test_exit_codes(self):
        """1 for a missing section, 0 for a change with none needed."""
        missing = self.run_script("--event", str(self.event("", self.agent)), "--repo",
                                  str(self.repo))
        self.assertEqual(missing.returncode, 1, missing.stdout + missing.stderr)
        fine = self.run_script("--event", str(self.event("", self.docs)), "--repo",
                               str(self.repo))
        self.assertEqual(fine.returncode, 0, fine.stdout + fine.stderr)

    def test_no_arguments_in_the_repository(self):
        """As troy-docs.yml runs it: the event from the variable, the current folder's repo."""
        event = self.event(section("passed", self.short(self.agent)), self.agent)
        out = self.run_script(cwd=self.repo, event=event)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        stale = self.event(section("passed", self.short(self.base)), self.agent)
        out = self.run_script(cwd=self.repo, event=stale)
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)


class ParseTests(unittest.TestCase):
    """parse_section and result_ok."""

    def test_the_designs_section(self):
        """Design 9.3's example."""
        found = check_exam.parse_section(section("passed", "3f9c2a1b7e04"))
        self.assertEqual((found["result"], found["instructions"]), ("passed", "3f9c2a1b7e04"))

    def test_accepted_result_is_kept_whole(self):
        """The date and the reason stay in the value."""
        result = "failed, accepted by Troy on 2026-11-21: flaky case"
        found = check_exam.parse_section(section(result, "3f9c2a1b7e04"))
        self.assertEqual(found["result"], result)

    def test_no_section(self):
        """None without a "## Role exam" heading."""
        self.assertIsNone(check_exam.parse_section("Result: passed\nInstructions: abc\n"))
        self.assertIsNone(check_exam.parse_section(""))

    def test_a_fenced_section_is_ignored(self):
        """Inside ``` or ~~~, the section does not count; one outside does."""
        fenced = ("```text\n## Role exam\n\nResult: passed\nInstructions: aaaaaaaaaaaa\n```\n")
        self.assertIsNone(check_exam.parse_section(fenced))
        tilde = fenced.replace("```text", "~~~").replace("```", "~~~")
        self.assertIsNone(check_exam.parse_section(tilde))
        both = fenced + "\n" + section("no case affected", "bbbbbbbbbbbb")
        found = check_exam.parse_section(both)
        self.assertEqual((found["result"], found["instructions"]),
                         ("no case affected", "bbbbbbbbbbbb"))

    def test_lines_of_other_sections_are_not_read(self):
        """A Result line under another heading after the section."""
        body = section("passed", "cccccccccccc") + "\n## Other\n\nResult: failed\n"
        self.assertEqual(check_exam.parse_section(body)["result"], "passed")

    def test_crlf(self):
        """CRLF reads like LF."""
        found = check_exam.parse_section(section("passed", "dddddddddddd", newline="\r\n"))
        self.assertEqual((found["result"], found["instructions"]), ("passed", "dddddddddddd"))

    def test_result_ok(self):
        """passed, no case affected, and failed accepted by Troy; nothing else."""
        self.assertTrue(check_exam.result_ok("passed"))
        self.assertTrue(check_exam.result_ok("no case affected"))
        self.assertTrue(check_exam.result_ok("failed, accepted by Troy on 2026-11-21: x"))
        for text in ("failed", "", "pending", "failed, rejected by Troy", "not run"):
            with self.subTest(text=text):
                self.assertFalse(check_exam.result_ok(text))


if __name__ == "__main__":
    unittest.main()
