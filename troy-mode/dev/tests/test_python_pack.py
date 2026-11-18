"""Tests of the Python pack's files and of build_sample.py (F03 design 8 and 10, F06 5.6 and 8).

The pack's files are checked against the design. The sample's CI workflow
is checked against the pack's CI job, so the sample runs the same steps a
project runs. build_sample.py runs as a subprocess, as CI runs it.

D214 planted bugs (F03 design 8.2) caught here: docs/ missing from the
pack's [tool.ruff] extend-exclude, a bare docs in its place, .troy-mode
dropped, or the list moved to exclude, which replaces ruff's defaults
(PackFileTests.test_ruff_leaves_out_troy_mode_and_docs, and in the built
sample BuildSampleTests.test_built_sample_ruff_leaves_out_docs_and_the_design_example);
the sample design's example formatted, so its CI no longer shows that ruff
leaves docs/ out (SampleDesignTests.test_sample_design_has_an_example_ruff_would_format).
"""

import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import tokenize
import tomllib
import unittest
from pathlib import Path

from pack_helpers import (CODE_GUARD, DEV, LOOK_FOR_CODE, PINNED, SAMPLE_EMAIL,
                          SAMPLE_ONLY_STEPS, TROY_MODE, WORKFLOWS, bash_path, git, git_bytes,
                          lf_bytes, pack_patterns, pack_workflow, parse_config, run_build,
                          run_step_script, setup_paths, sha256_lf, step_blocks, steps, uses)

PACK = TROY_MODE / "lang" / "python"
SAMPLE = TROY_MODE / "samples" / "python"
SAMPLE_WORKFLOW = WORKFLOWS / "troy-python-sample.yml"
DESIGN_TITLE = "[F01 1/6 design] Count words in a text"
SETUP_TITLE = "[docs] Set up textstats with troy-mode"
DESIGN_PATH = "docs/features/F01-word-counts/design.md"
SAMPLE_DESIGN = SAMPLE / "stages" / "1-design" / DESIGN_PATH
# D214 (F03 design 8.2): what the pack's ruff leaves out. docs/ with its slash
# is relative to the project root; a bare docs would also leave out src/<pkg>/docs.
RUFF_EXCLUDES = [".troy-mode", "docs/"]
_PYTHON_BLOCK = re.compile(r"(?ms)^```python[ \t]*\n(.*?)^```[ \t]*$")
_ANY_BLOCK = re.compile(r"(?ms)^```.*?^```[ \t]*$")


def python_blocks(text: str) -> list[str]:
    """The code of each fenced ```python block of a Markdown text."""
    return _PYTHON_BLOCK.findall(text)


def restyled_strings(code: str) -> list[str]:
    """The string literals that ruff's default format turns into double quotes.

    That is a literal in single quotes with no double quote in it, which ruff
    rewrites with double quotes. f-strings are left out.
    """
    found = []
    for token in tokenize.generate_tokens(io.StringIO(code).readline):
        if token.type == tokenize.STRING:
            body = token.string.lstrip("rRbBuU")
            if body.startswith("'") and '"' not in body:
                found.append(token.string)
    return found


def ruff_excludes(pyproject: str) -> tuple[list[str], bool]:
    """A pyproject.toml's [tool.ruff] extend-exclude, sorted, and whether it sets exclude."""
    ruff = tomllib.loads(pyproject).get("tool", {}).get("ruff", {})
    return sorted(ruff.get("extend-exclude", [])), "exclude" in ruff


class PackFileTests(unittest.TestCase):
    """The pack's files hold what F03 design section 8 says."""

    def test_pack_has_the_files_of_design_section_2(self) -> None:
        """The pack folder holds the README pair, the four pack files, and the new-project file."""
        names = {"README.md", "README.zh-CN.md", "environment.yml", "pyproject.toml",
                 "config.toml", "workflow-job.yml", "pyproject-project.toml"}
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

    def test_ruff_leaves_out_troy_mode_and_docs(self) -> None:
        """D214: [tool.ruff] extend-exclude is exactly .troy-mode and docs/, and exclude is unset.

        D214 planted bugs caught: docs/ missing, a bare docs, .troy-mode dropped,
        or the list moved to exclude, which would replace ruff's default excludes.
        """
        text = (PACK / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual((sorted(RUFF_EXCLUDES), False), ruff_excludes(text))

    def test_new_project_file_holds_build_system_project_and_wheel(self) -> None:
        """pyproject-project.toml has hatchling, the name, 0.1.0, Python 3.13, and the package."""
        text = (PACK / "pyproject-project.toml").read_text(encoding="utf-8")
        data = tomllib.loads(text)
        self.assertEqual({"build-system", "project", "tool"}, set(data))
        self.assertEqual({"requires": ["hatchling>=1.25"], "build-backend": "hatchling.build"},
                         data["build-system"])
        self.assertEqual({"name": "{{project-name}}", "version": "0.1.0",
                          "requires-python": ">=3.13", "dependencies": []}, data["project"])
        self.assertEqual({"hatch": {"build": {"targets": {"wheel": {
            "packages": ["src/{{package}}"]}}}}}, data["tool"])
        markers = set(re.findall(r"\{\{[^}]*\}\}", text))
        self.assertEqual({"{{project-name}}", "{{package}}"}, markers)

    def test_new_project_file_and_fragment_join_into_one_valid_file(self) -> None:
        """The created pyproject.toml, the two files joined, is valid TOML with both parts."""
        first = (PACK / "pyproject-project.toml").read_text(encoding="utf-8")
        first = first.replace("{{project-name}}", "habit-tracker").replace("{{package}}", "habits")
        joined = first.rstrip("\n") + "\n\n" + (PACK / "pyproject.toml").read_text("utf-8")
        data = tomllib.loads(joined)
        self.assertEqual("habit-tracker", data["project"]["name"])
        self.assertIn("dev", data["project"]["optional-dependencies"])
        self.assertEqual(["src/habits"], data["tool"]["hatch"]["build"]["targets"]["wheel"][
            "packages"])

    def test_readmes_list_the_new_project_file(self) -> None:
        """Both READMEs' files tables have a row for pyproject-project.toml."""
        for name in ("README.md", "README.zh-CN.md"):
            with self.subTest(readme=name):
                rows = [line for line in (PACK / name).read_text("utf-8").splitlines()
                        if re.match(r"^\| \[?`pyproject-project\.toml`", line)]
                self.assertEqual(1, len(rows), name)

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
        self.assertEqual(len(pack), 7)
        self.assertEqual(pack, sample)
        self.assertEqual(uses(PACK / "workflow-job.yml"), uses(SAMPLE_WORKFLOW))


class NoCodeGuardTests(unittest.TestCase):
    """The pack's job skips its code steps until the PR has code (F06 design 5.6, D50)."""

    def test_job_looks_for_code_right_after_checkout(self) -> None:
        """The first step after checkout is Look for code, with id code and no condition."""
        blocks = step_blocks(PACK / "workflow-job.yml")
        self.assertEqual(9, len(blocks))
        self.assertTrue(blocks[0].get("uses", "").startswith("actions/checkout@"), blocks[0])
        self.assertEqual(LOOK_FOR_CODE, blocks[1].get("name"))
        self.assertEqual("code", blocks[1].get("id"))
        self.assertNotIn("if", blocks[1])

    def test_every_later_step_of_the_job_needs_code(self) -> None:
        """Each step after Look for code, uses: steps included, runs only when code was found."""
        blocks = step_blocks(PACK / "workflow-job.yml")
        self.assertEqual(7, len(blocks[2:]))
        self.assertTrue(any("uses" in block for block in blocks[2:]))
        for block in blocks[2:]:
            with self.subTest(step=block.get("name") or block.get("uses")):
                self.assertEqual(CODE_GUARD, block.get("if"))

    def test_look_for_code_lists_src_and_writes_the_output(self) -> None:
        """The step asks git ls-files about src, sets found, and writes No code yet."""
        script = dict(steps(PACK / "workflow-job.yml"))[LOOK_FOR_CODE]
        for text in ("git ls-files", "src", "found=true", "found=false", "GITHUB_OUTPUT",
                     "GITHUB_STEP_SUMMARY", "No code yet"):
            with self.subTest(text=text):
                self.assertIn(text, script)

    def test_sample_looks_for_code_after_building_the_sample(self) -> None:
        """In the sample, Look for code follows the build, and every later step but the
        comparison needs code."""
        blocks = step_blocks(SAMPLE_WORKFLOW)
        names = [block.get("name") for block in blocks]
        look = names.index(LOOK_FOR_CODE)
        self.assertEqual("code", blocks[look].get("id"))
        self.assertLess(names.index("Build the sample"), look)
        later = blocks[look + 1:]
        self.assertEqual(8, len(later))
        for block in later:
            with self.subTest(step=block.get("name") or block.get("uses")):
                if block.get("name") == "Compare with the expected results":
                    self.assertNotEqual(CODE_GUARD, block.get("if"))
                else:
                    self.assertEqual(CODE_GUARD, block.get("if"))

    def test_sample_compares_with_and_without_code(self) -> None:
        """The comparison reads found, verifies a report, or verifies with --no-code."""
        compare = next(block for block in step_blocks(SAMPLE_WORKFLOW)
                       if block.get("name") == "Compare with the expected results")
        for text in ("steps.code.outputs.found", "verify python --pr", "--report", "--no-code"):
            with self.subTest(text=text):
                self.assertIn(text, compare["text"])

    def test_no_step_runs_exit(self) -> None:
        """No run step calls exit: in the job's login shell, exit reads ~/.bash_logout,
        which fails on the runner and turns exit 0 into 1."""
        for path in (PACK / "workflow-job.yml", SAMPLE_WORKFLOW):
            for block in step_blocks(path):
                with self.subTest(file=path.name, step=block.get("name")):
                    self.assertNotRegex(block["text"], r"(?m)^\s*exit\b")

    def test_sample_matrix_has_the_design_pr(self) -> None:
        """The sample runs the design PR, without code, and the tests and impl PRs."""
        text = SAMPLE_WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^\s+pr: \[design, tests, impl\]\s*$")

    @unittest.skipIf(bash_path() is None, "no bash that runs like a runner's")
    def test_look_for_code_runs_on_a_head_with_and_without_code(self) -> None:
        """Run with bash: found=false and No code yet without src, found=true with it."""
        script = dict(steps(PACK / "workflow-job.yml"))[LOOK_FOR_CODE]
        if "${{" in script:
            self.skipTest("the step's script holds a workflow expression")
        cases = (({"docs/architecture.md": "# A\n", "tests/test_cli.py": ""}, "false"),
                 ({"src/textstats/__init__.py": ""}, "true"))
        for files, found in cases:
            with self.subTest(found=found):
                output, summary = run_step_script(script, files)
                self.assertEqual([f"found={found}"],
                                 [line for line in output if line.startswith("found=")])
                self.assertEqual(found == "false", "No code yet" in summary, summary)


class SampleLockTests(unittest.TestCase):
    """The sample's lock file comes from the design's uv command."""

    def test_lock_pins_every_dev_tool(self) -> None:
        """The lock was compiled with the design's command and pins the four tools."""
        text = (SAMPLE / "base" / "requirements-dev.lock").read_text(encoding="utf-8")
        self.assertIn("uv pip compile pyproject.toml --extra dev --universal "
                      "-o requirements-dev.lock", text)
        for tool in ("coverage", "mypy", "pytest", "ruff"):
            self.assertRegex(text, rf"(?m)^{tool}==\d")


class SampleSettingsTests(unittest.TestCase):
    """sample.toml and the sample's folders after F06 design 8."""

    @classmethod
    def setUpClass(cls) -> None:
        """Reads sample.toml once."""
        cls.sample = tomllib.loads((SAMPLE / "sample.toml").read_text(encoding="utf-8"))

    def test_sample_names_project_and_environment_without_a_pack_table(self) -> None:
        """troy-init's functions install the pack, so sample.toml has no [pack] table."""
        self.assertNotIn("pack", self.sample)
        self.assertEqual("textstats", self.sample["project"])
        self.assertEqual("textstats", self.sample["environment"])

    def test_sample_marks_the_design_pr_as_having_no_code(self) -> None:
        """The design commit is PR design, with no_code and no expected results."""
        design = [c for c in self.sample["commits"] if c.get("pr") == "design"]
        self.assertEqual(1, len(design))
        self.assertEqual(DESIGN_TITLE, design[0]["title"])
        self.assertIs(True, design[0].get("no_code"))
        self.assertNotIn("expected", design[0])

    def test_package_init_moved_from_base_to_the_mock_stage(self) -> None:
        """The base has no src/, so the design PR's head has no code."""
        self.assertFalse((SAMPLE / "base" / "src").exists())
        self.assertTrue((SAMPLE / "stages" / "3-mock" / "src" / "textstats" / "__init__.py")
                        .is_file())


class SampleDesignTests(unittest.TestCase):
    """The sample's design holds an example ruff would format, so CI shows D214 at work.

    The tests and impl PRs of the sample run ruff check and ruff format --check
    on a tree that holds this design; they pass only while ruff leaves docs/ out.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Reads the sample's design once."""
        cls.text = SAMPLE_DESIGN.read_text(encoding="utf-8")

    def test_sample_design_has_an_example_ruff_would_format(self) -> None:
        """A ```python block of valid code holds a single-quoted string ruff turns into "...".

        D214 planted bug caught: the example formatted (or dropped), so the
        sample's CI would pass whether or not ruff leaves docs/ out.
        """
        blocks = python_blocks(self.text)
        self.assertTrue(blocks, "the sample's design has no ```python block")
        for code in blocks:
            with self.subTest(code=code):
                ast.parse(code)
        restyled = [s for code in blocks for s in restyled_strings(code)]
        self.assertTrue(restyled, "no string literal in the design's examples is single-quoted")

    def test_sample_design_says_its_examples_are_not_format_checked(self) -> None:
        """Outside its code blocks, the design says examples are not format-checked, naming D214."""
        prose = _ANY_BLOCK.sub("", self.text)
        self.assertIn("not format-checked", prose)
        self.assertIn("D214", prose)

    def test_sample_design_keeps_its_front_matter(self) -> None:
        """The front matter is the one the sample's design had before D214."""
        self.assertTrue(self.text.startswith(
            '---\ntroy-doc: "F01-design"\nlang: "en"\nversion: "1.0"\nupdated: "2026-11-06"\n'
            'status: "Sample."\n---\n'), self.text[:200])


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

    def root(self) -> str:
        """The built sample's first commit, after checking the build succeeded."""
        self.assertEqual(0, self.proc.returncode, self.proc.stderr)
        return git(self.repo, "rev-list", "--max-parents=0", "HEAD")

    def show(self, path: str) -> str:
        """A file's text in the first commit, with CRLF made LF."""
        return lf_bytes(git_bytes(self.repo, "show", f"{self.root()}:{path}")).decode("utf-8")

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
                          DESIGN_TITLE, SETUP_TITLE],
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

    def test_first_commit_holds_every_file_setup_writes(self) -> None:
        """troy-check, the templates, the record, the config, the rules, PR template, workflow."""
        files = set(git(self.repo, "ls-tree", "-r", "--name-only", self.root()).splitlines())
        missing = sorted(set(setup_paths()) - files)
        self.assertEqual([], missing)

    def test_first_commit_records_git_hooks_as_executable(self) -> None:
        """git records every hook file in the first commit with mode 100755."""
        listing = git(self.repo, "ls-tree", "-r", self.root(), "--", ".troy-mode/checks/git-hooks")
        modes = {line.split("\t")[1]: line.split()[0] for line in listing.splitlines()}
        self.assertEqual(4, len(modes))
        self.assertEqual({"100755"}, set(modes.values()), modes)

    def test_build_leaves_hooks_off_and_the_progress_file_out(self) -> None:
        """core.hooksPath is unset, and no commit holds .troy-mode/progress.md."""
        self.root()
        proc = subprocess.run(["git", "-C", str(self.repo), "config", "--local", "--get",
                               "core.hooksPath"], capture_output=True, text=True, check=False)
        self.assertEqual(1, proc.returncode, proc.stdout)
        paths = git(self.repo, "log", "--all", "--format=", "--name-only").splitlines()
        self.assertNotIn(".troy-mode/progress.md", paths)
        self.assertIn(".troy-mode/progress.md", self.show(".gitignore").splitlines())

    def test_first_commit_config_is_setup_with_the_lang_table(self) -> None:
        """Every pack's patterns, the sample's email, and [lang] filled for the sample."""
        data = tomllib.loads(self.show(".troy-mode/config.toml"))
        config = parse_config(self.show(".troy-mode/config.toml"))
        self.assertEqual(SAMPLE_EMAIL, config.commit_email)
        self.assertEqual({"name": "python", "source_roots": ["src"], "environment": "textstats",
                          "series": ["."]}, data["lang"])
        for key, patterns in pack_patterns().items():
            with self.subTest(key=key):
                self.assertEqual(sorted(patterns), sorted(set(data["paths"][key])))

    def test_first_commit_record_names_the_pack_and_hashes_the_files(self) -> None:
        """The install record has [lang] name and the hash of each owned file."""
        record = tomllib.loads(self.show(".troy-mode/install.toml"))
        self.assertEqual("python", record["lang"]["name"])
        self.assertIn("setup", record["steps"])
        self.assertIn(".github/workflows/troy-mode.yml", record["files"])
        for path, digest in record["files"].items():
            with self.subTest(path=path):
                self.assertEqual(digest, sha256_lf((self.repo / path).read_bytes()))

    def test_first_commit_rules_and_workflow_are_troy_inits(self) -> None:
        """The rules table names textstats, and the workflow is F02's plus the pack's job."""
        rules = self.show("docs/rules.md")
        self.assertIn("# textstats rules", rules.splitlines())
        self.assertNotIn("{{", rules)
        self.assertNotIn("<!--", rules)
        self.assertEqual(pack_workflow("python"), self.show(".github/workflows/troy-mode.yml"))

    def test_built_sample_ruff_leaves_out_docs_and_the_design_example(self) -> None:
        """D214 end to end: the tests PR's pyproject.toml, which troy-init's functions append
        to, leaves out docs/, where the design's unformatted example sits for CI's ruff.

        D214 planted bugs caught: docs/ missing or bare, .troy-mode dropped, or exclude set.
        """
        self.root()
        self.assertEqual((sorted(RUFF_EXCLUDES), False),
                         ruff_excludes((self.repo / "pyproject.toml").read_text("utf-8")))
        design = lf_bytes(git_bytes(self.repo, "show", f"pr:{DESIGN_PATH}")).decode("utf-8")
        self.assertTrue([s for code in python_blocks(design) for s in restyled_strings(code)],
                        "the tests PR's design has no example that ruff format would change")

    def test_first_commit_keeps_the_sample_lock(self) -> None:
        """The sample's own committed lock is the one in the first commit."""
        expected = lf_bytes((SAMPLE / "base" / "requirements-dev.lock").read_bytes())
        self.assertEqual(expected.decode("utf-8"), self.show("requirements-dev.lock"))

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
        self.assertIn("design, tests, impl", proc.stderr)

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


class BuildDesignPrTests(unittest.TestCase):
    """The design PR: setup and the language step, but no code (F06 design 8)."""

    @classmethod
    def setUpClass(cls) -> None:
        """Builds the design PR of the Python sample once."""
        cls._tmp = tempfile.TemporaryDirectory(prefix="sample-")
        cls.repo = Path(cls._tmp.name) / "repo"
        cls.proc = run_build("build", "python", "--pr", "design", "--out", str(cls.repo))

    @classmethod
    def tearDownClass(cls) -> None:
        """Deletes the built repository."""
        cls._tmp.cleanup()

    def test_design_pr_sits_on_the_setup_commit(self) -> None:
        """main holds only the setup commit, and branch pr adds the design."""
        self.assertEqual(0, self.proc.returncode, self.proc.stderr)
        self.assertEqual(DESIGN_TITLE, json.loads(self.proc.stdout)["PR_TITLE"])
        self.assertEqual([SETUP_TITLE], git(self.repo, "log", "--format=%s", "main").splitlines())
        self.assertEqual(["docs/features/F01-word-counts/design.md"],
                         git(self.repo, "diff", "--name-only", "main", "pr").splitlines())

    def test_design_pr_head_has_no_code(self) -> None:
        """No file of the PR's head is under src/, though the pack is installed."""
        self.assertEqual(0, self.proc.returncode, self.proc.stderr)
        files = git(self.repo, "ls-tree", "-r", "--name-only", "pr").splitlines()
        self.assertIn("pyproject.toml", files)
        self.assertEqual([], [path for path in files if path.startswith("src/")])


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

    def verify(self, results: dict[str, str], pr: str = "impl") -> subprocess.CompletedProcess:
        """Writes a report with the given results and runs verify on a PR."""
        report = {"command": "code", "ok": True, "title": None,
                  "results": [{"rule": r, "result": v, "message": f"{r} said {v}.", "details": []}
                              for r, v in results.items()]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            return run_build("verify", "python", "--pr", pr, "--report", str(path))

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

    def test_no_code_passes_on_the_design_pr(self) -> None:
        """verify --no-code exits 0 on the PR sample.toml marks no_code."""
        proc = run_build("verify", "python", "--pr", "design", "--no-code")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)

    def test_no_code_fails_on_a_pr_with_code(self) -> None:
        """verify --no-code on the impl PR exits 1 with one line naming the PR."""
        proc = run_build("verify", "python", "--pr", "impl", "--no-code")
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
        lines = [line for line in proc.stdout.splitlines()
                 if line.strip() and not line.endswith(" differences.")]
        self.assertEqual(1, len(lines), proc.stdout)
        self.assertIn("impl", lines[0])

    def test_a_report_fails_on_the_design_pr(self) -> None:
        """A troy-check report on a PR marked no_code is a difference, exit 1."""
        proc = self.verify(self.expected(), pr="design")
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)

    def test_verify_needs_exactly_one_of_report_and_no_code(self) -> None:
        """Neither option, or both, is a usage error, exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text("{}", encoding="utf-8")
            for extra in ([], ["--no-code", "--report", str(path)]):
                with self.subTest(extra=extra):
                    proc = run_build("verify", "python", "--pr", "design", *extra)
                    self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
