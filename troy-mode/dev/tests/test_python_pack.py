"""Tests of the Python pack's files and of build_sample.py (F03 design 8 and 10).

The pack's files are checked against the design. The sample's CI workflow
is checked against the pack's CI job, so the sample runs the same steps a
project runs. build_sample.py runs as a subprocess, as CI runs it.
"""

import json
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from pack_helpers import (DEV, PINNED, SAMPLE_ONLY_STEPS, TROY_MODE, WORKFLOWS, git,
                          parse_config, run_build, steps, uses)

PACK = TROY_MODE / "lang" / "python"
SAMPLE = TROY_MODE / "samples" / "python"
SAMPLE_WORKFLOW = WORKFLOWS / "troy-python-sample.yml"


class PackFileTests(unittest.TestCase):
    """The pack's files hold what F03 design section 8 says."""

    def test_pack_has_the_files_of_design_section_2(self) -> None:
        """The pack folder holds the README pair and the four pack files."""
        names = {"README.md", "README.zh-CN.md", "environment.yml", "pyproject.toml",
                 "config.toml", "workflow-job.yml"}
        self.assertEqual(names, {p.name for p in PACK.iterdir()})

    def test_environment_provides_only_python_and_uv(self) -> None:
        """mamba installs Python 3.13 and uv from conda-forge, and nothing else."""
        lines = [line.strip() for line in (PACK / "environment.yml").read_text(
            encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
        self.assertEqual(['name: "{{environment}}"', "channels:", "- conda-forge",
                          "dependencies:", "- python=3.13", "- uv"], lines)

    def test_config_fragment_is_valid_troy_check_config(self) -> None:
        """The config tables, once filled in, pass troy-check's config validation."""
        text = (PACK / "config.toml").read_text(encoding="utf-8")
        config = parse_config(text.replace("{{environment}}", "sample-env"))
        self.assertEqual("python", config.lang["name"])
        self.assertEqual(["src"], config.lang["source_roots"])
        self.assertEqual("sample-env", config.lang["environment"])
        self.assertEqual(["."], config.lang["series"])
        data = tomllib.loads(text)
        self.assertEqual(["**/test_*.py", "**/*_test.py", "**/conftest.py"], data["paths"]["tests"])
        self.assertEqual(["requirements*.lock"], data["paths"]["lock"])
        self.assertIn("requirements*.lock", data["paths"]["dependencies"])

    def test_pyproject_fragment_configures_the_tools(self) -> None:
        """ruff, mypy, pytest, and coverage are set as design section 8.2 says."""
        data = tomllib.loads((PACK / "pyproject.toml").read_text(encoding="utf-8"))
        dev = {re.split(r"[<>=\[]", d)[0] for d in data["project"]["optional-dependencies"]["dev"]}
        self.assertEqual({"coverage", "mypy", "pytest", "ruff"}, dev)
        tool = data["tool"]
        self.assertIn("D", tool["ruff"]["lint"]["select"])
        self.assertEqual("google", tool["ruff"]["lint"]["pydocstyle"]["convention"])
        self.assertIn(".troy-mode", tool["ruff"]["extend-exclude"])
        self.assertTrue(tool["mypy"]["strict"])
        self.assertEqual(["tests"], tool["pytest"]["ini_options"]["testpaths"])
        self.assertEqual("-ra --strict-markers", tool["pytest"]["ini_options"]["addopts"])
        self.assertEqual({"branch": True, "source": ["src"]}, tool["coverage"]["run"])

    def test_actions_are_pinned_to_commits(self) -> None:
        """Every action in the pack's job and the sample's workflow is pinned to a SHA."""
        for path in (PACK / "workflow-job.yml", SAMPLE_WORKFLOW):
            for action, comment in uses(path):
                with self.subTest(path=path.name, action=action):
                    self.assertRegex(action, PINNED)
                    self.assertRegex(comment, r"^# v\d+\.\d+\.\d+$")

    def test_job_runs_the_commands_of_design_section_8_3(self) -> None:
        """The pack's job runs lint, types, tests, coverage, and troy-check code."""
        runs = "\n".join(body for _, body in steps(PACK / "workflow-job.yml"))
        for command in ("ruff check", "ruff format --check", "mypy",
                        "coverage run -m pytest --junitxml=reports/junit.xml",
                        "coverage xml -o reports/coverage.xml", "uv pip install -r requirements-dev.lock",
                        "uv pip install -e . --no-deps", '/troy_check.py" code'):
            self.assertIn(command, runs)
        text = (PACK / "workflow-job.yml").read_text(encoding="utf-8")
        self.assertIn("fetch-depth: 0", text)
        self.assertIn("name: troy-mode code checks", text)

    def test_sample_ci_runs_the_same_steps_as_the_pack(self) -> None:
        """The sample's workflow runs the pack's steps unchanged, plus its own two."""
        pack = steps(PACK / "workflow-job.yml")
        sample = [s for s in steps(SAMPLE_WORKFLOW) if s[0] not in SAMPLE_ONLY_STEPS]
        self.assertEqual(len(pack), 6)
        self.assertEqual(pack, sample)
        self.assertEqual(uses(PACK / "workflow-job.yml"), uses(SAMPLE_WORKFLOW))


class SampleLockTests(unittest.TestCase):
    """The sample's lock file comes from the design's uv command."""

    def test_lock_pins_every_dev_tool(self) -> None:
        """The lock was compiled with the design's command and pins the four tools."""
        text = (SAMPLE / "base" / "requirements-dev.lock").read_text(encoding="utf-8")
        self.assertIn("uv pip compile pyproject.toml --extra dev --universal "
                      "-o requirements-dev.lock", text)
        for tool in ("coverage", "mypy", "pytest", "ruff"):
            self.assertRegex(text, rf"(?m)^{tool}==\d")


class BuildSampleTests(unittest.TestCase):
    """build_sample.py builds the repository a PR of the sample is checked in."""

    @classmethod
    def setUpClass(cls) -> None:
        """Builds the tests PR of the Python sample once for the tests below."""
        cls._tmp = tempfile.TemporaryDirectory(prefix="sample-")
        cls.repo = Path(cls._tmp.name) / "repo"
        cls.proc = run_build("build", "python", "--pr", "tests", "--out", str(cls.repo))

    @classmethod
    def tearDownClass(cls) -> None:
        """Deletes the built repository."""
        cls._tmp.cleanup()

    def test_build_puts_the_pr_on_a_branch_after_the_stages_before_it(self) -> None:
        """main holds the stages before the PR, and branch pr holds the PR's commit."""
        self.assertEqual(0, self.proc.returncode, self.proc.stderr)
        values = json.loads(self.proc.stdout)
        self.assertEqual("[F01 4/6 tests] Count words in a text", values["PR_TITLE"])
        self.assertEqual(git(self.repo, "rev-parse", "main"), values["BASE_SHA"])
        self.assertEqual(git(self.repo, "rev-parse", "pr"), values["HEAD_SHA"])
        self.assertEqual("pr", git(self.repo, "branch", "--show-current"))
        self.assertEqual(["[F01 3/6 mock] Count words in a text",
                          "[F01 2/6 test-plan] Count words in a text",
                          "[F01 1/6 design] Count words in a text",
                          "[docs] Set up textstats with troy-mode"],
                         git(self.repo, "log", "--format=%s", "main").splitlines())
        self.assertEqual(["tests/test_cli.py", "tests/test_counting.py"],
                         git(self.repo, "diff", "--name-only", "main", "pr").splitlines())

    def test_build_installs_the_pack_like_troy_init(self) -> None:
        """The first commit holds troy-check, F02's workflow, and the filled-in pack."""
        files = git(self.repo, "ls-tree", "-r", "--name-only", "main~3").splitlines()
        for path in (".troy-mode/checks/troy_check.py", ".troy-mode/checks/troycheck/cli.py",
                     ".troy-mode/config.toml", ".github/workflows/troy-mode.yml",
                     "environment.yml", "pyproject.toml", "requirements-dev.lock"):
            self.assertIn(path, files)
        self.assertIn('name: "textstats"', (self.repo / "environment.yml").read_text("utf-8"))
        config = parse_config((self.repo / ".troy-mode/config.toml").read_text("utf-8"))
        self.assertEqual("textstats", config.lang["environment"])
        project = tomllib.loads((self.repo / "pyproject.toml").read_text("utf-8"))
        self.assertEqual("textstats", project["project"]["name"])
        self.assertIn("dev", project["project"]["optional-dependencies"])
        workflow = (self.repo / ".github/workflows/troy-mode.yml").read_text("utf-8")
        self.assertIn("  troy-check:", workflow)
        self.assertIn("  troy-code:", workflow)

    def test_build_copies_the_git_hooks_like_troy_init(self) -> None:
        """The first commit holds troy-check's git-hooks folder with the four hooks (F05 13.3)."""
        source = TROY_MODE / "checks" / "git-hooks"
        names = ("commit-msg", "pre-commit", "pre-merge-commit", "pre-push")
        copied = self.repo / ".troy-mode" / "checks" / "git-hooks"
        self.assertTrue(copied.is_dir(), f"{copied} is missing")
        self.assertEqual({p.name for p in source.iterdir() if p.is_file()},
                         {p.name for p in copied.iterdir() if p.is_file()})
        files = git(self.repo, "ls-tree", "-r", "--name-only", "main~3").splitlines()
        for name in names:
            with self.subTest(hook=name):
                self.assertIn(f".troy-mode/checks/git-hooks/{name}", files)
                self.assertEqual((source / name).read_bytes(), (copied / name).read_bytes())

    def test_build_refuses_a_folder_that_is_not_empty(self) -> None:
        """Building into a folder with files in it is an error, exit code 2."""
        proc = run_build("build", "python", "--pr", "impl", "--out", str(self.repo))
        self.assertEqual(2, proc.returncode)
        self.assertIn("is not empty", proc.stderr)

    def test_build_rejects_an_unknown_pr(self) -> None:
        """A PR name that sample.toml does not mark is an error that lists the names."""
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_build("build", "python", "--pr", "accept", "--out", str(Path(tmp) / "r"))
        self.assertEqual(2, proc.returncode)
        self.assertIn("tests, impl", proc.stderr)

    def test_build_writes_the_values_to_github_env(self) -> None:
        """With GITHUB_ENV set, the values go there, PR_BODY with a delimiter."""
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "env"
            proc = run_build("build", "python", "--pr", "impl", "--out", str(Path(tmp) / "r"),
                             github_env=env_file)
            self.assertEqual(0, proc.returncode, proc.stderr)
            text = env_file.read_text(encoding="utf-8")
        self.assertIn("PR_TITLE=[F01 5/6 impl] Count words in a text\n", text)
        self.assertRegex(text, r"(?m)^BASE_SHA=[0-9a-f]{40}$")
        self.assertRegex(text, r"PR_BODY<<(\w+)\n## Why\n(.|\n)*\n\1\n")


class FillTests(unittest.TestCase):
    """Pack files are filled in the way troy-init fills them."""

    def test_unfilled_marker_is_an_error_but_workflow_expressions_are_not(self) -> None:
        """A {{marker}} other than environment stops the build; ${{ }} is GitHub's."""
        sys.path.insert(0, str(DEV))
        import build_sample  # noqa: PLC0415

        text = "name: {{environment}}\nref: ${{ github.sha }}\n"
        self.assertEqual("name: env\nref: ${{ github.sha }}\n",
                         build_sample.fill(text, "env", "x.yml"))
        with self.assertRaisesRegex(build_sample.SampleError, r"x\.yml .*\{\{series\}\}"):
            build_sample.fill("series: {{series}}\n", "env", "x.yml")


class VerifyTests(unittest.TestCase):
    """verify compares a troy-check report with the sample's expected results."""

    def verify(self, results: dict[str, str]) -> subprocess.CompletedProcess:
        """Writes a report with the given results and runs verify on the impl PR."""
        report = {"command": "code", "ok": True, "title": None,
                  "results": [{"rule": r, "result": v, "message": f"{r} said {v}.", "details": []}
                              for r, v in results.items()]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            return run_build("verify", "python", "--pr", "impl", "--report", str(path))

    def expected(self) -> dict[str, str]:
        """Returns the impl PR's expected results from sample.toml."""
        data = tomllib.loads((SAMPLE / "sample.toml").read_text(encoding="utf-8"))
        return next(c["expected"] for c in data["commits"] if c.get("pr") == "impl")

    def test_matching_report_passes(self) -> None:
        """A report with exactly the expected results exits 0."""
        proc = self.verify(self.expected())
        self.assertEqual(0, proc.returncode, proc.stdout)

    def test_a_different_result_fails_with_the_rule_message(self) -> None:
        """A rule with another result exits 1 and names the rule and its message."""
        results = {**self.expected(), "R11": "fail"}
        proc = self.verify(results)
        self.assertEqual(1, proc.returncode)
        self.assertIn("R11: expected pass, got fail. R11 said fail.", proc.stdout)

    def test_missing_and_extra_rules_fail(self) -> None:
        """A rule the report lacks, or one the sample does not expect, is a difference."""
        results = {k: v for k, v in self.expected().items() if k != "R04"}
        results["R99"] = "pass"
        proc = self.verify(results)
        self.assertEqual(1, proc.returncode)
        self.assertIn("R04: expected pass, got not reported.", proc.stdout)
        self.assertIn("R99: expected not reported, got pass.", proc.stdout)


if __name__ == "__main__":
    unittest.main()
