"""Brief group, part 1b: a team's brief names its checkout (F20 design 3.2, 3.11, 4, 8.1, 8.4).

Written from the part 1b contract and F20 design version 1.1 before the code exists.
Black-box, as F07's brief tests are: ``troy_flow.py brief ... --json`` runs as a
subprocess and the tests read its report and prompt.

Fixtures. Each fixture builds a bare origin with flow_helpers and clones it twice into
folders named ``tally``: ``ref``, a plain clone whose repository has no team worktree,
and ``home``, the home checkout. The team worktree ``<home>/.troy-teams/f08`` is made by
hand, as ``team start`` makes it: ``git worktree add --detach <home>/.troy-teams/f08
origin/main`` and ``/.troy-teams/`` in the common git folder's ``info/exclude``. The
features table holds F01 and F08; F08 has no dependency. Every engine run shares one set
of fakes, so the ``mamba`` that the checks name is the same in every brief.

- ``py3``: Python, ``source_roots = ["src"]``, ``environment = "wordcount"``; F08's PR 1
  and PR 2 merged and B12's PR A merged, no mock merged yet (DV1's first mock).
- ``py4`` and ``py5``: the same config, F08 at PR 4 or PR 5.
- ``roots5``: ``source_roots = ["lib", "app"]`` and ``environment = "wc-series"``, PR 5.
- ``bare3``: ``[lang]`` with neither ``source_roots`` nor ``environment``, PR 3.
- ``cpp3``: the C/C++ pack without ``environment``, PR 3.

The old brief is the plain clone's (``ref``). A team brief must equal it with only the
contract's changes made, and every other checkout must equal it byte for byte.
``NormalCheckoutTests.test_reference_is_the_old_brief`` pins the reference itself to the
old format, so a change that reaches every brief cannot hide behind the comparison.

Contract items and the tests that check them:

1. The team sentence: ``TeamSentenceTests``.
2. Read first: ``ReadFirstTests``.
3. ``PYTHONPATH`` for Python: ``PythonPathTests`` and ``WorktreeHeadTests``.
4. C/C++: ``CppChecksTests``.
5. The environment's name: ``EnvironmentTests``.
6. DV1's first-mock install: ``FirstMockInstallTests``.
7. The report's ``team`` key: ``ReportTests``, and ``NormalCheckoutTests`` for its absence.
8. The hooks of part 1a place the role: ``HookPlacementTests``.

``WholeBriefTests`` checks that nothing else of the brief changes, with ``--repo`` and
from the current folder, and ``NormalCheckoutTests`` that a normal clone, the home
checkout, a linked worktree outside ``.troy-teams/``, a linked worktree under
``.troy-teams/`` whose name is no team ID, and a plain clone in a folder named
``.troy-teams/f08`` give the old brief byte for byte.

Planted bugs (design 8.2 and the part 1b brief) caught here:

- The sentence added to non-team briefs: ``NormalCheckoutTests`` (every test) and
  ``ReportTests.test_reference_reports_have_no_team_key``.
- The sentence after the mock-note text:
  ``TeamSentenceTests.test_dv1_sentence_comes_before_the_notes_and_the_platform_sentence``
  and ``test_sentence_follows_the_task_sentence_in_every_brief``.
- The team ID not upper-cased: ``TeamSentenceTests.test_team_id_is_the_folder_name_in_upper_
  case``, ``ReportTests.test_team_key_names_the_team_and_the_worktree``, and
  ``HookPlacementTests``.
- A relative Read first path left: ``ReadFirstTests.test_every_path_is_absolute_in_the_
  worktree`` and ``test_folder_keeps_its_trailing_separator``.
- The annotation dropped: ``ReadFirstTests.test_annotation_after_the_path_is_kept``.
- ``PYTHONPATH`` missing for Python: ``PythonPathTests.test_every_python_check_starts_with_
  pythonpath``; ``PYTHONPATH`` left out of a team's checks (design 8.2) is the same bug.
- ``PYTHONPATH`` added for C/C++: ``CppChecksTests.test_cpp_checks_are_as_before``.
- ``source_roots`` ignored: ``PythonPathTests.test_custom_source_roots_joined_by_pathsep``
  and ``WorktreeHeadTests``.
- ``os.pathsep`` not used: ``PythonPathTests.test_custom_source_roots_joined_by_pathsep``.
- The environment's name taken from the worktree's folder:
  ``EnvironmentTests.test_unset_environment_uses_the_main_checkouts_folder_name``.
- The editable install left as ``-e .``:
  ``FirstMockInstallTests.test_dv1_installs_the_main_checkout``.
- The report's ``team`` key in a normal brief: ``ReportTests.test_reference_reports_have_
  no_team_key`` and ``NormalCheckoutTests``.

Run from the repository root:
python -m unittest discover -s troy-mode/flow/tests -p "test_team_brief.py" -v
"""

import json
import os
import re
import shlex
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from typing import Optional
from unittest import mock

from flow_helpers import (
    CONFIG, F01, PLUGIN_ROOT, WORK_BRANCH, Fakes, Feature, FlowCase, Outcome, Project, base_env,
    base_files, base_step, bug_step, config_text, git, new_dir, origin_repo, parallel,
    run_engine, same_path, stages,
)
from test_mock_notes_brief import CR1_PR3_CPP, CR1_PR3_PY, CR1_PR5, DV1_CPP, DV1_PY, DV2_TEXT
from test_security_brief import NO_SIGN, RUN_PREFIX

F08 = Feature("F08", "Merge reports")
FEATURES = (F01, F08)
TEAMS = ".troy-teams"
EXCLUDE_LINE = "/.troy-teams/"
TEAM_FOLDER = "f08"
TEAM_ID = "F08"
HOME_NAME = "tally"
CRASH = "Crash on empty history"
TEST_FIX = "[F08 test-fix] Wrong count in F08-T01"
DOCS_PLAN = "[docs] Add cases to the F08 test plan"
INSTALL = "uv pip install -e . --no-deps"
DV1_OWN = "Task: DV1, write the mock of F08's interfaces."
HOOK = PLUGIN_ROOT / "troy-mode" / "hooks" / "troy_hook.py"
SESSION = "session-f20-part1b"
BASH_ROOT = re.compile(r'cd "([^"]+)" && (.*)', re.DOTALL)
SEP = os.sep
# The platform-skip sentence of a code task's Task line (F07 D69).
D69 = ("A test that the test plan runs only on another platform is skipped here, and "
       "troy-check code reports it under R09 or R10; CI checks it, so name it in your report "
       "and do not count it as a failure.")
# Text that the Task line holds after the task's own sentence (contract item 1). CR1's
# security sentence (tstack #75) comes after the team sentence too: the "not needed"
# sentence, or one that starts RUN_PREFIX.
LATER_TEXTS = (DV1_PY, DV1_CPP, CR1_PR3_PY, CR1_PR3_CPP, DV2_TEXT, CR1_PR5, NO_SIGN,
               RUN_PREFIX, D69)

PY_CONFIG = config_text("python")
ROOTS_CONFIG = config_text("python", environment="wc-series").replace(
    'source_roots = ["src"]', 'source_roots = ["lib", "app"]')
BARE_CONFIG = (config_text("python").replace('source_roots = ["src"]\n', "")
               .replace('environment = "wordcount"\n', ""))
CPP_CONFIG = config_text("cpp").replace('environment = "wordcount"\n', "")
CONFIGS = {"py3": PY_CONFIG, "py4": PY_CONFIG, "py5": PY_CONFIG, "roots5": ROOTS_CONFIG,
           "bare3": BARE_CONFIG, "cpp3": CPP_CONFIG}
# [lang] source_roots by fixture, as the team's PYTHONPATH names them; None for C/C++.
ROOTS = {"py3": ("src",), "py4": ("src",), "py5": ("src",), "roots5": ("lib", "app"),
         "bare3": ("src",), "cpp3": None}
# The environment the checks name: the config's, or the main checkout's folder name.
ENVIRONMENTS = {"py3": "wordcount", "py4": "wordcount", "py5": "wordcount",
                "roots5": "wc-series", "bare3": HOME_NAME, "cpp3": HOME_NAME}

# (label, fixture, task, item, --title or None)
TEAM_CASES = [
    ("DV1 at PR 3", "py3", "DV1", "F08", None),
    ("CR1 at PR 3", "py3", "CR1", "F08", None),
    ("AR5 at PR 3", "py3", "AR5", "F08", None),
    ("TM8 for v0.1", "py3", "TM8", "v0.1", None),
    ("CR1 in v0.1's tests PR", "py3", "CR1", "v0.1", None),
    ("DV3 for bug B12", "py3", "DV3", "B12", None),
    ("CR1 for bug B12", "py3", "CR1", "B12", None),
    ("TE1 at PR 4", "py4", "TE1", "F08", None),
    ("TM2 at PR 4", "py4", "TM2", "F08", None),
    ("DV2 at PR 5", "py5", "DV2", "F08", None),
    ("CR1 at PR 5", "py5", "CR1", "F08", None),
    ("TE3 in a test-fix side PR", "py5", "TE3", "F08", TEST_FIX),
    ("TM1 in a [docs] side PR", "py5", "TM1", "F08", DOCS_PLAN),
    ("DV2 with two source roots", "roots5", "DV2", "F08", None),
    ("CR1 with two source roots", "roots5", "CR1", "F08", None),
    ("DV1 without source roots or environment", "bare3", "DV1", "F08", None),
    ("CR1 without source roots or environment", "bare3", "CR1", "F08", None),
    ("DV1, C/C++", "cpp3", "DV1", "F08", None),
    ("CR1, C/C++", "cpp3", "CR1", "F08", None),
]
CASES = {case[0]: case for case in TEAM_CASES}
# Cases also run from the team worktree as the current folder, without --repo.
FOLDER_CASES = ("DV1 at PR 3", "CR1 for bug B12", "AR5 at PR 3")

_FIXTURES: dict = {}
_SHARED: dict = {}
_RUNS: dict = {}


# ------------------------------------------------------------------ fixtures

class Home(Project):
    """A clone of a cached bare origin in a folder of a given name, on ``troy-mode/work``."""

    def __init__(self, steps, root: Optional[Path] = None) -> None:
        """Clones the origin built from the steps.

        Args:
            steps: The history of ``origin/main``, oldest first.
            root: The clone's folder, or None for ``<new folder>/tally``.
        """
        self.origin = origin_repo(steps)
        self.root = root if root is not None else new_dir("teamhome") / HOME_NAME
        self.tmp = self.root.parent
        self.tmp.mkdir(parents=True, exist_ok=True)
        git(self.tmp, "clone", "-q", str(self.origin), self.root.name)
        self.git("switch", "-q", "-c", WORK_BRANCH, "origin/main")


def origin_steps(name: str) -> list:
    """The history of one fixture's ``origin/main``.

    Args:
        name: A key of ``CONFIGS``; its last character is F08's current stage.

    Returns:
        The steps.
    """
    lang = "cpp" if name.startswith("cpp") else "python"
    steps = [base_step(base_files(FEATURES, lang=lang, extra={CONFIG: CONFIGS[name]})),
             *stages(F08, int(name[-1]) - 1)]
    if name == "py3":
        steps.append(bug_step("B12", "test", CRASH))
    return steps


def common_dir(home: Path) -> Path:
    """The git folder that the repository's worktrees share."""
    return Path(git(home, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())


def add_worktree(home: Path, path: Path) -> Path:
    """Adds a linked worktree detached at ``origin/main`` and returns its path as given."""
    path.parent.mkdir(parents=True, exist_ok=True)
    git(home, "worktree", "add", "-q", "--detach", str(path), "origin/main")
    return path


def add_team(home: Path, name: str = TEAM_FOLDER) -> Path:
    """Makes ``<home>/.troy-teams/<name>`` as ``team start`` does, and returns it as given."""
    exclude = common_dir(home) / "info" / "exclude"
    text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if EXCLUDE_LINE not in text.splitlines():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        sep = "" if not text or text.endswith("\n") else "\n"
        exclude.write_text(f"{text}{sep}{EXCLUDE_LINE}\n", encoding="utf-8")
    return add_worktree(home, home / TEAMS / name)


class Fixture:
    """One origin's plain clone and its home checkout with the team worktree f08.

    Attributes:
        name: The fixture's key.
        ref: The plain clone, whose brief is the old brief.
        home: The home checkout.
        given: The team worktree's path as made, passed to ``--repo``.
        wt: The team worktree's real path, as ``os.path.realpath`` gives it.
        main: The home checkout's real path.
    """

    def __init__(self, name: str) -> None:
        """Builds both clones and the team worktree."""
        steps = origin_steps(name)
        self.name = name
        self.ref = Home(steps)
        self.home = Home(steps)
        self.given = add_team(self.home.root)
        self.wt = os.path.realpath(self.given)
        self.main = os.path.realpath(self.home.root)


def fixture(name: str) -> Fixture:
    """A fixture shared by the tests that only read it, built on first use."""
    if name not in _FIXTURES:
        _FIXTURES[name] = Fixture(name)
    return _FIXTURES[name]


def shared_fakes() -> Fakes:
    """The one set of fakes every engine run of this file uses."""
    if "fakes" not in _SHARED:
        _SHARED["fakes"] = Fakes(fail=True)
    return _SHARED["fakes"]


def neutral() -> Path:
    """A folder in no repository, the current folder of runs that pass ``--repo``."""
    if "neutral" not in _SHARED:
        _SHARED["neutral"] = new_dir("neutral")
    return _SHARED["neutral"]


def brief_run(task: str, item: str, title: Optional[str] = None, repo=None,
              cwd: Optional[Path] = None) -> Outcome:
    """Runs ``brief --task <task> --item <item> [--title <title>] --json``.

    Args:
        task: The task ID.
        item: The item ID.
        title: The ``--title`` value, or None.
        repo: The ``--repo`` folder, or None to run from ``cwd`` without it.
        cwd: The current folder when ``repo`` is None.

    Returns:
        The outcome.
    """
    args = ["brief", "--task", task, "--item", item]
    if title is not None:
        args += ["--title", title]
    if repo is not None:
        args += ["--repo", str(repo)]
    args.append("--json")
    return run_engine(args, cwd if repo is None else neutral(), shared_fakes())


def prepare() -> None:
    """Builds the shared fakes and folder before runs start side by side."""
    shared_fakes()
    neutral()


def team_runs() -> dict:
    """Runs every case's brief on the plain clone and on the team worktree, once.

    Returns:
        ``("ref" | "team" | "folder", label)`` mapped to the outcome.
    """
    if not _RUNS:
        prepare()
        for name in sorted({case[1] for case in TEAM_CASES}):
            fixture(name)
        jobs = []
        for label, name, task, item, title in TEAM_CASES:
            fx = fixture(name)
            jobs.append((("ref", label), (task, item, title), {"repo": fx.ref.root}))
            jobs.append((("team", label), (task, item, title), {"repo": fx.given}))
            if label in FOLDER_CASES:
                jobs.append((("folder", label), (task, item, title), {"cwd": fx.given}))
        outs = parallel(lambda job: brief_run(*job[1], **job[2]), jobs)
        _RUNS.update(zip([job[0] for job in jobs], outs))
    return _RUNS


# ------------------------------------------------------------------- reading

def sentence(path: str) -> str:
    """The team sentence of contract item 1 for team F08 and a checkout."""
    return (f"You work for team {TEAM_ID} in the checkout `{path}`: every path in this brief "
            "is inside it, read and write files only there, and your commands start there.")


def task_line(prompt: str) -> str:
    """The prompt's ``Task:`` line, or "" when there is none."""
    return next((line for line in prompt.split("\n") if line.startswith("Task: ")), "")


def section_lines(prompt: str, which: str) -> list:
    """The ``- `` lines under ``Read first:`` (``read``) or ``Checks to run:`` (``checks``)."""
    found, section = [], None
    for line in prompt.split("\n"):
        if line == "Read first:":
            section = "read"
        elif line == "Checks to run:":
            section = "checks"
        elif not line.startswith("- "):
            section = None
        elif section == which:
            found.append(line)
    return found


def checks_of(prompt: str) -> list:
    """The commands listed under ``Checks to run:``."""
    return [line[2:] for line in section_lines(prompt, "checks")]


def with_team(line: str, path: str) -> str:
    """The Task line with the team sentence right after the task's own sentence."""
    points = [line.find(" " + text) for text in LATER_TEXTS if " " + text in line]
    at = min(points) if points else len(line)
    return line[:at] + " " + sentence(path) + line[at:]


def absolute_line(line: str, wt: str) -> str:
    """A Read first line with its path made absolute in the worktree, the rest kept."""
    path, space, rest = line[2:].partition(" ")
    return f"- {wt}{SEP}{path.replace('/', SEP)}{space}{rest}"


def pythonpath(fx: Fixture) -> Optional[str]:
    """The ``PYTHONPATH`` value of a fixture's team checks, or None for C/C++."""
    roots = ROOTS[fx.name]
    return None if roots is None else os.pathsep.join(f"{fx.wt}{SEP}{root}" for root in roots)


def team_check(fx: Fixture, old: str) -> str:
    """One team check from the old one: the install of item 6 and the prefix of item 3."""
    rest = old.replace(INSTALL, f'uv pip install -e "{fx.main}" --no-deps')
    value = pythonpath(fx)
    return rest if value is None else f'PYTHONPATH="{value}" {rest}'


def team_prompt(fx: Fixture, old: str) -> str:
    """The team brief the contract expects, made from the old brief."""
    lines, section = [], None
    for line in old.split("\n"):
        if line.startswith("Task: "):
            line = with_team(line, fx.wt)
        elif line == "Read first:":
            section = "read"
        elif line == "Checks to run:":
            section = "checks"
        elif not line.startswith("- "):
            section = None
        elif section == "read":
            line = absolute_line(line, fx.wt)
        elif section == "checks":
            line = "- " + team_check(fx, line[2:])
        lines.append(line)
    return "\n".join(lines)


class TeamBriefCase(FlowCase):
    """Reads the shared runs of ``TEAM_CASES``. It has no tests of its own."""

    @classmethod
    def setUpClass(cls):
        """Runs every case once for the whole file."""
        cls.runs = team_runs()

    def pair(self, label: str) -> tuple:
        """The old (plain clone) and team reports of one case, both successful briefs.

        Args:
            label: The case's label.

        Returns:
            ``(old report, team report, fixture)``.
        """
        old = self.report_of(self.runs[("ref", label)], 0, "brief")
        team = self.report_of(self.runs[("team", label)], 0, "brief")
        self.assertIsInstance(old.get("prompt"), str, label)
        self.assertIsInstance(team.get("prompt"), str, label)
        return old, team, fixture(CASES[label][1])

    def labels(self, *fixtures: str) -> list:
        """The labels of the cases of some fixtures, or of every case."""
        return [case[0] for case in TEAM_CASES if not fixtures or case[1] in fixtures]


# ------------------------------------------------------------------ item 1

class TeamSentenceTests(TeamBriefCase):
    """Contract item 1: the team sentence on the Task line."""

    def test_dv1_sentence_comes_before_the_notes_and_the_platform_sentence(self):
        """DV1's Task line: its own sentence, the team sentence, the mock notes, then D69.

        Planted bug caught: the sentence after the mock-note text (and after D69).
        """
        for label, notes in (("DV1 at PR 3", DV1_PY), ("DV1, C/C++", DV1_CPP),
                             ("DV1 without source roots or environment", DV1_PY)):
            with self.subTest(case=label):
                old, team, fx = self.pair(label)
                self.assertEqual(task_line(old["prompt"]), f"{DV1_OWN} {notes} {D69}")
                self.assertEqual(task_line(team["prompt"]),
                                 f"{DV1_OWN} {sentence(fx.wt)} {notes} {D69}")

    def test_sentence_follows_the_task_sentence_in_every_brief(self):
        """Every task, the role's own and the reviewers', a side PR, a bug, and a version.

        The team brief's Task line is the old one with the sentence inserted right
        after the task's own sentence, before any mock-note text and D69.

        Planted bug caught: the sentence after the mock-note text.
        """
        for label in self.labels():
            with self.subTest(case=label):
                old, team, fx = self.pair(label)
                self.assertEqual(task_line(team["prompt"]),
                                 with_team(task_line(old["prompt"]), fx.wt))

    def test_sentence_appears_once_and_only_on_the_task_line(self):
        """The sentence is in the prompt exactly once, and that once is on the Task line."""
        for label in self.labels():
            with self.subTest(case=label):
                _, team, fx = self.pair(label)
                prompt = team["prompt"]
                self.assertEqual(prompt.count("You work for team"), 1, prompt)
                self.assertEqual(prompt.count(sentence(fx.wt)), 1, prompt)
                self.assertIn(sentence(fx.wt), task_line(prompt))

    def test_team_id_is_the_folder_name_in_upper_case(self):
        """The folder ``f08`` gives team F08, for a feature's, a bug's, and a version's brief.

        Planted bug caught: the team ID not upper-cased.
        """
        for label in ("DV1 at PR 3", "CR1 for bug B12", "TM8 for v0.1", "CR1, C/C++"):
            with self.subTest(case=label):
                _, team, fx = self.pair(label)
                line = task_line(team["prompt"])
                self.assertIn(f"You work for team F08 in the checkout `{fx.wt}`:", line)
                self.assertNotIn("team f08", team["prompt"])

    def test_old_briefs_hold_no_sentence(self):
        """The plain clone's briefs, the reference, hold no team sentence.

        Planted bug caught: the sentence added to non-team briefs.
        """
        for label in self.labels():
            with self.subTest(case=label):
                old, _, _ = self.pair(label)
                self.assertNotIn("You work for team", old["prompt"])


# ------------------------------------------------------------------ item 2

class ReadFirstTests(TeamBriefCase):
    """Contract item 2: Read first paths absolute in the worktree."""

    def test_every_path_is_absolute_in_the_worktree(self):
        """Each Read first line is ``<worktree><sep><path with the platform's separators>``.

        Planted bug caught: a relative Read first path left.
        """
        for label in self.labels():
            with self.subTest(case=label):
                old, team, fx = self.pair(label)
                old_lines = section_lines(old["prompt"], "read")
                new_lines = section_lines(team["prompt"], "read")
                self.assertTrue(old_lines, old["prompt"])
                self.assertEqual(new_lines, [absolute_line(line, fx.wt) for line in old_lines])
                for line in new_lines:
                    self.assertTrue(line.startswith(f"- {fx.wt}{SEP}"), line)

    def test_annotation_after_the_path_is_kept(self):
        """The requirements keep ``(the F08 row in section 4)`` or the version's text.

        Planted bug caught: the annotation dropped.
        """
        cases = (("AR5 at PR 3", "(the F08 row in section 4)"),
                 ("DV3 for bug B12", None),
                 ("TM8 for v0.1", "(the v0.1 rows and the version plan)"),
                 ("CR1 at PR 5", "(the F08 row in section 4)"))
        for label, note in cases:
            with self.subTest(case=label):
                old, team, fx = self.pair(label)
                requirements = f"docs{SEP}requirements.md"
                old_line = "- docs/requirements.md" + (f" {note}" if note else "")
                self.assertIn(old_line, section_lines(old["prompt"], "read"))
                new_line = f"- {fx.wt}{SEP}{requirements}" + (f" {note}" if note else "")
                self.assertIn(new_line, section_lines(team["prompt"], "read"))

    def test_folder_keeps_its_trailing_separator(self):
        """TM8's ``docs/prototypes/`` becomes ``<worktree><sep>docs<sep>prototypes<sep>``.

        Planted bug caught: a relative Read first path left (the folder).
        """
        old, team, fx = self.pair("TM8 for v0.1")
        self.assertIn("- docs/prototypes/", section_lines(old["prompt"], "read"))
        self.assertIn(f"- {fx.wt}{SEP}docs{SEP}prototypes{SEP}",
                      section_lines(team["prompt"], "read"))

    def test_feature_documents_are_in_the_worktree(self):
        """AR5's design and test plan of F08 are named in the worktree."""
        _, team, fx = self.pair("AR5 at PR 3")
        lines = section_lines(team["prompt"], "read")
        for rel in (F08.design, F08.plan):
            self.assertIn(f"- {fx.wt}{SEP}{rel.replace('/', SEP)}", lines)


# ------------------------------------------------------------------ item 3

class PythonPathTests(TeamBriefCase):
    """Contract item 3: ``PYTHONPATH`` before every Python check."""

    def test_every_python_check_starts_with_pythonpath(self):
        """Each check is ``PYTHONPATH="<roots in the worktree>" `` and the old command.

        Planted bug caught: PYTHONPATH missing for Python (design 8.2: left out of a
        team's checks).
        """
        python = [label for label in self.labels() if CASES[label][1] != "cpp3"]
        for label in python:
            with self.subTest(case=label):
                old, team, fx = self.pair(label)
                old_checks = checks_of(old["prompt"])
                new_checks = checks_of(team["prompt"])
                self.assertEqual(new_checks, [team_check(fx, check) for check in old_checks])
                for check in new_checks:
                    self.assertTrue(check.startswith(f'PYTHONPATH="{pythonpath(fx)}" '), check)

    def test_default_source_root_is_src(self):
        """``source_roots = ["src"]``, and no ``source_roots`` at all, give ``<worktree><sep>src``.
        """
        for label in ("DV1 at PR 3", "CR1 at PR 5", "DV1 without source roots or environment"):
            with self.subTest(case=label):
                _, team, fx = self.pair(label)
                checks = checks_of(team["prompt"])
                self.assertTrue(checks, team["prompt"])
                for check in checks:
                    self.assertTrue(check.startswith(f'PYTHONPATH="{fx.wt}{SEP}src" '), check)

    def test_custom_source_roots_joined_by_pathsep(self):
        """``source_roots = ["lib", "app"]`` gives both, in order, joined by ``os.pathsep``.

        Planted bugs caught: source_roots ignored; os.pathsep not used.
        """
        for label in ("DV2 with two source roots", "CR1 with two source roots"):
            with self.subTest(case=label):
                _, team, fx = self.pair(label)
                value = f"{fx.wt}{SEP}lib{os.pathsep}{fx.wt}{SEP}app"
                checks = checks_of(team["prompt"])
                self.assertTrue(checks, team["prompt"])
                for check in checks:
                    self.assertTrue(check.startswith(f'PYTHONPATH="{value}" '), check)

    def test_version_tests_release_command_gets_it_too(self):
        """CR1 on a version's tests PR: the release command after the checks starts with it."""
        old, team, fx = self.pair("CR1 in v0.1's tests PR")
        old_last, new_last = checks_of(old["prompt"])[-1], checks_of(team["prompt"])[-1]
        self.assertIn("pytest version-tests", old_last)
        self.assertEqual(new_last, f'PYTHONPATH="{pythonpath(fx)}" {old_last}')

    def test_tasks_without_checks_stay_without(self):
        """AR5, TM8, and TM1 in a [docs] side PR still have ``Checks to run: None``."""
        for label in ("AR5 at PR 3", "TM8 for v0.1", "TM1 in a [docs] side PR"):
            with self.subTest(case=label):
                _, team, _ = self.pair(label)
                self.assertIn("Checks to run: None", team["prompt"].split("\n"))
                self.assertNotIn("PYTHONPATH", team["prompt"])


# ------------------------------------------------------------------ item 4

class CppChecksTests(TeamBriefCase):
    """Contract item 4: C/C++ checks have no ``PYTHONPATH`` and are as before."""

    def test_cpp_checks_are_as_before(self):
        """DV1 and CR1 in a C/C++ team: the checks equal the old ones, word for word.

        Planted bug caught: PYTHONPATH added for C/C++.
        """
        for label in ("DV1, C/C++", "CR1, C/C++"):
            with self.subTest(case=label):
                old, team, _ = self.pair(label)
                old_checks = checks_of(old["prompt"])
                self.assertTrue(old_checks, old["prompt"])
                self.assertEqual(checks_of(team["prompt"]), old_checks)
                self.assertNotIn("PYTHONPATH", team["prompt"])
        old, _, _ = self.pair("DV1, C/C++")
        self.assertIn(" cmake --preset coverage", checks_of(old["prompt"])[0])


# ------------------------------------------------------------------ item 5

class EnvironmentTests(TeamBriefCase):
    """Contract item 5: the environment that ``mamba run -n`` names."""

    def test_unset_environment_uses_the_main_checkouts_folder_name(self):
        """No ``[lang] environment``: ``-n tally``, the home checkout's name, never ``-n f08``.

        Planted bug caught: the environment's name taken from the worktree's folder.
        """
        for label in self.labels("bare3", "cpp3"):
            with self.subTest(case=label):
                old, team, _ = self.pair(label)
                for check in checks_of(old["prompt"]):
                    self.assertIn(f" run -n {HOME_NAME} ", check)
                checks = checks_of(team["prompt"])
                self.assertTrue(checks, team["prompt"])
                for check in checks:
                    self.assertIn(f" run -n {HOME_NAME} ", check)
                    self.assertNotIn(f" -n {TEAM_FOLDER} ", check)

    def test_set_environment_is_used_as_before(self):
        """``environment = "wc-series"`` or ``"wordcount"``: that name, in every check."""
        for label in self.labels("roots5", "py3", "py5"):
            with self.subTest(case=label):
                _, team, fx = self.pair(label)
                for check in checks_of(team["prompt"]):
                    self.assertIn(f" run -n {ENVIRONMENTS[fx.name]} ", check)


# ------------------------------------------------------------------ item 6

class FirstMockInstallTests(TeamBriefCase):
    """Contract item 6: DV1's first-mock install names the main checkout."""

    def test_dv1_installs_the_main_checkout(self):
        """``uv pip install -e "<main checkout's real path>" --no-deps``, not ``-e .``.

        Planted bug caught: the editable install left as ``-e .``.
        """
        for label in ("DV1 at PR 3", "DV1 without source roots or environment"):
            with self.subTest(case=label):
                old, team, fx = self.pair(label)
                old_first = checks_of(old["prompt"])[0]
                self.assertTrue(old_first.endswith(f" {INSTALL}"), old_first)
                checks = checks_of(team["prompt"])
                self.assertTrue(checks, team["prompt"])
                install = f'uv pip install -e "{fx.main}" --no-deps'
                self.assertEqual(checks[0], f'PYTHONPATH="{pythonpath(fx)}" '
                                            + old_first.replace(INSTALL, install))
                for check in checks:
                    self.assertNotIn("install -e . ", check)
                    self.assertNotIn(f'install -e "{fx.wt}"', check)

    def test_no_install_where_the_old_brief_has_none(self):
        """CR1 at PR 3 and DV2 at PR 5 install nothing in a team either."""
        for label in ("CR1 at PR 3", "DV2 at PR 5"):
            with self.subTest(case=label):
                _, team, _ = self.pair(label)
                self.assertNotIn("uv pip install", team["prompt"])


class UvCacheTeamTests(FlowCase):
    """A team's DV1 install keeps the uv variables of F06 design 5.4 (D289).

    Expected: ``PYTHONPATH="..." UV_LINK_MODE=copy UV_CACHE_DIR=<folder> <run> uv pip
    install -e "<main>" --no-deps`` when ``UV_CACHE_DIR`` is unset or empty, and
    ``PYTHONPATH="..." UV_LINK_MODE=copy <run> uv pip install -e "<main>" --no-deps`` when
    it is set. The engine's temp folder is a scratch folder whose name holds a space.

    Planted bug caught: the team rewrite dropping or reordering the uv variables.
    """

    CASES = (("py3", "DV1"), ("bare3", "DV1"), ("cpp3", "DV1"), ("py3", "CR1"))

    @classmethod
    def setUpClass(cls):
        """Runs each brief on the plain clone and the team worktree, in three states."""
        prepare()
        cls.temp = new_dir("temp ")
        cls.cache = cls.temp / "troy-mode-uv-cache"
        cls.user_cache = str(new_dir("user cache") / "uv")
        temp = {"TMPDIR": str(cls.temp), "TEMP": str(cls.temp), "TMP": str(cls.temp)}
        cls.states = {"unset": temp, "empty": {**temp, "UV_CACHE_DIR": ""},
                      "set": {**temp, "UV_CACHE_DIR": cls.user_cache}}
        jobs = [(state, name, task, kind) for state in cls.states for name, task in cls.CASES
                for kind in ("ref", "team")]

        def run(job):
            """Runs one brief with the state's environment."""
            state, name, task, kind = job
            fx = fixture(name)
            repo = fx.ref.root if kind == "ref" else fx.given
            args = ["brief", "--task", task, "--item", "F08", "--repo", str(repo), "--json"]
            return run_engine(args, neutral(), shared_fakes(), cls.states[state])

        for name, _ in cls.CASES:
            fixture(name)
        with mock.patch.dict(os.environ):
            os.environ.pop("UV_CACHE_DIR", None)
            outs = parallel(run, jobs)
        cls.outs = dict(zip(jobs, outs))

    def checks(self, state: str, name: str, task: str, kind: str) -> list:
        """The checks of one successful brief."""
        out = self.outs[(state, name, task, kind)]
        return checks_of(self.report_of(out, 0, "brief")["prompt"])

    def test_team_install_keeps_both_variables_in_order(self):
        """Unset or empty: ``PYTHONPATH`` first, then ``UV_LINK_MODE=copy
        UV_CACHE_DIR=<quoted folder>``, then the run prefix and the main checkout's install."""
        for state in ("unset", "empty"):
            for name in ("py3", "bare3"):
                with self.subTest(state=state, fixture=name):
                    fx = fixture(name)
                    ref = self.checks(state, name, "DV1", "ref")[0]
                    team = self.checks(state, name, "DV1", "team")[0]
                    self.assertTrue(ref.startswith("UV_LINK_MODE=copy UV_CACHE_DIR="), ref)
                    value = shlex.split(ref)[1].partition("=")[2]
                    self.assertTrue(same_path(value, self.cache), f"{value} is not {self.cache}")
                    self.assertIn(" ", value)
                    self.assertTrue(ref.startswith(
                        f"UV_LINK_MODE=copy UV_CACHE_DIR={shlex.quote(value)} "), ref)
                    install = f'uv pip install -e "{fx.main}" --no-deps'
                    self.assertEqual(
                        team, f'PYTHONPATH="{pythonpath(fx)}" '
                              + ref.replace(INSTALL, install))
                    head = (f'PYTHONPATH="{pythonpath(fx)}" UV_LINK_MODE=copy '
                            f'UV_CACHE_DIR={shlex.quote(value)} ')
                    self.assertTrue(team.startswith(head), team)
                    self.assertTrue(team.endswith(f" {install}"), team)

    def test_team_install_with_a_set_value_has_link_mode_alone(self):
        """Set: ``PYTHONPATH="..." UV_LINK_MODE=copy <run> uv pip install -e "<main>"``, no
        cache word and no folder of any kind."""
        for name in ("py3", "bare3"):
            with self.subTest(fixture=name):
                fx = fixture(name)
                ref = self.checks("set", name, "DV1", "ref")[0]
                team = self.checks("set", name, "DV1", "team")[0]
                self.assertTrue(ref.startswith("UV_LINK_MODE=copy "), ref)
                self.assertNotIn("UV_CACHE_DIR", team)
                self.assertNotIn("troy-mode-uv-cache", team)
                self.assertNotIn(self.user_cache, team)
                install = f'uv pip install -e "{fx.main}" --no-deps'
                self.assertEqual(team, f'PYTHONPATH="{pythonpath(fx)}" '
                                       + ref.replace(INSTALL, install))
                self.assertTrue(team.startswith(
                    f'PYTHONPATH="{pythonpath(fx)}" UV_LINK_MODE=copy '), team)
                self.assertTrue(team.endswith(f" {install}"), team)

    def test_other_team_checks_have_no_uv_words(self):
        """Only the install line has them; the team's other checks and a team's C/C++ DV1
        and CR1 have none, in every state."""
        for state in self.states:
            for name, task in self.CASES:
                checks = self.checks(state, name, task, "team")
                self.assertTrue(checks)
                first_is_install = (name, task) in (("py3", "DV1"), ("bare3", "DV1"))
                for index, check in enumerate(checks):
                    if index == 0 and first_is_install:
                        continue
                    with self.subTest(state=state, fixture=name, task=task, index=index):
                        self.assertNotIn("UV_", check)

    def test_team_cpp_dv1_has_none(self):
        """A team's C/C++ DV1 equals the plain clone's brief and has no ``UV_`` word."""
        for state in self.states:
            with self.subTest(state=state):
                team = self.checks(state, "cpp3", "DV1", "team")
                self.assertEqual(team, self.checks(state, "cpp3", "DV1", "ref"))
                self.assertNotIn("UV_", "\n".join(team))


# ------------------------------------------------------------------ item 7

class ReportTests(TeamBriefCase):
    """Contract item 7: the report's ``team`` key."""

    def test_team_key_names_the_team_and_the_worktree(self):
        """Every team brief's report has ``team``: ``{"id": "F08", "worktree": <real path>}``.

        Planted bug caught: the team ID not upper-cased.
        """
        for label in self.labels():
            with self.subTest(case=label):
                _, team, fx = self.pair(label)
                self.assertEqual(team.get("team"), {"id": TEAM_ID, "worktree": fx.wt})

    def test_reference_reports_have_no_team_key(self):
        """The plain clone's reports have no ``team`` key at all.

        Planted bug caught: the report's team key in a normal brief.
        """
        for label in self.labels():
            with self.subTest(case=label):
                old, _, _ = self.pair(label)
                self.assertNotIn("team", old)


# ------------------------------------------------------------------ the whole

class WholeBriefTests(TeamBriefCase):
    """Nothing but the contract's changes, with ``--repo`` or from the current folder."""

    def test_nothing_else_changes(self):
        """The team prompt is the old prompt with items 1, 2, 3, 5, and 6 applied, nothing else.
        """
        for label in self.labels():
            with self.subTest(case=label):
                old, team, fx = self.pair(label)
                self.assertEqual(team["prompt"], team_prompt(fx, old["prompt"]))

    def test_current_folder_is_the_team_worktree(self):
        """Run from the team worktree without ``--repo``: the same report as with ``--repo``."""
        for label in FOLDER_CASES:
            with self.subTest(case=label):
                _, team, _ = self.pair(label)
                here = self.report_of(self.runs[("folder", label)], 0, "brief")
                self.assertEqual(here, team)


# ------------------------------------------------------------- other folders

class NormalCheckoutTests(FlowCase):
    """Every checkout that is not a team worktree gives the old brief, byte for byte."""

    TASKS = (("DV1", "F08"), ("AR5", "F08"), ("TM8", "v0.1"), ("CR1", "B12"))

    @classmethod
    def setUpClass(cls):
        """Builds a home checkout with a team and the other checkouts, then runs the briefs."""
        prepare()
        steps = origin_steps("py3")
        cls.ref = fixture("py3").ref
        home = Home(steps)
        team = add_team(home.root)
        outside = add_worktree(home.root, new_dir("elsewhere") / TEAM_FOLDER)
        scratch = add_worktree(home.root, home.root / TEAMS / "scratch")
        lookalike = Home(steps, root=new_dir("lookalike") / TEAMS / TEAM_FOLDER)
        cls.checkouts = {"plain clone": {"repo": cls.ref.root},
                         "home checkout with a team": {"repo": home.root},
                         "home checkout run from the team's folder":
                             {"repo": home.root, "cwd": team},
                         "linked worktree outside .troy-teams": {"repo": outside},
                         "linked worktree .troy-teams/scratch": {"repo": scratch},
                         "plain clone in a .troy-teams/f08 folder": {"repo": lookalike.root}}
        bare_steps = origin_steps("bare3")
        bare_ref = fixture("bare3").ref
        bare_home = Home(bare_steps)
        add_team(bare_home.root)
        bare_outside = add_worktree(bare_home.root, new_dir("elsewhere") / TEAM_FOLDER)
        jobs = [((name, task, item), (task, item), where)
                for name, where in cls.checkouts.items() for task, item in cls.TASKS]
        jobs += [(("bare " + name, "DV1", "F08"), ("DV1", "F08"), {"repo": repo})
                 for name, repo in (("plain clone", bare_ref.root),
                                    ("home checkout with a team", bare_home.root),
                                    ("linked worktree outside .troy-teams", bare_outside))]

        def run(job):
            """Runs one job's brief, from its folder when it names one."""
            where = dict(job[2])
            cwd = where.pop("cwd", None)
            if cwd is not None:
                args = ["brief", "--task", job[1][0], "--item", job[1][1],
                        "--repo", str(where["repo"]), "--json"]
                return run_engine(args, cwd, shared_fakes())
            return brief_run(*job[1], **where)

        outs = parallel(run, jobs)
        cls.outs = dict(zip([job[0] for job in jobs], outs))

    def old(self, task: str, item: str, prefix: str = "") -> Outcome:
        """The plain clone's run of one task, which must be a successful brief."""
        out = self.outs[(prefix + "plain clone", task, item)]
        report = self.report_of(out, 0, "brief")
        self.assertIsInstance(report.get("prompt"), str, out.describe())
        return out

    def assert_same(self, name: str) -> None:
        """Asserts that one checkout's runs equal the plain clone's, byte for byte."""
        for task, item in self.TASKS:
            with self.subTest(checkout=name, task=task):
                old = self.old(task, item)
                out = self.outs[(name, task, item)]
                self.assertEqual(out.code, 0, out.describe())
                self.assertNotIn("team", out.report or {}, out.describe())
                self.assertEqual(out.report, old.report)
                self.assertEqual(out.stdout, old.stdout)

    def test_reference_is_the_old_brief(self):
        """The plain clone's briefs have the old Task line, Read first, checks, and no team.

        Planted bugs caught: the sentence added to non-team briefs; the report's team key
        in a normal brief.
        """
        dv1 = self.old("DV1", "F08").report
        self.assertEqual(task_line(dv1["prompt"]), f"{DV1_OWN} {DV1_PY} {D69}")
        checks = checks_of(dv1["prompt"])
        self.assertTrue(checks[0].endswith(f" run -n wordcount {INSTALL}"), checks[0])
        ar5 = self.old("AR5", "F08").report
        self.assertEqual(section_lines(ar5["prompt"], "read"),
                         ["- docs/rules.md", "- docs/requirements.md (the F08 row in section 4)",
                          "- docs/architecture.md", f"- {F08.design}", f"- {F08.plan}"])
        tm8 = self.old("TM8", "v0.1").report
        self.assertEqual(section_lines(tm8["prompt"], "read")[-1], "- docs/prototypes/")
        for task, item in self.TASKS:
            with self.subTest(task=task):
                report = self.old(task, item).report
                self.assertNotIn("team", report)
                self.assertNotIn("You work for team", report["prompt"])
                self.assertNotIn("PYTHONPATH", report["prompt"])
                for line in section_lines(report["prompt"], "read"):
                    self.assertTrue(line.startswith("- docs/"), line)

    def test_home_checkout_with_a_team_gives_the_old_brief(self):
        """The home checkout, whose repository has a team worktree, gives the old brief.

        Planted bug caught: the sentence added to non-team briefs.
        """
        self.assert_same("home checkout with a team")

    def test_home_checkout_named_by_repo_from_the_team_folder(self):
        """``--repo <home>`` run from inside the team worktree briefs the home checkout.

        Planted bug caught: the sentence added to non-team briefs.
        """
        self.assert_same("home checkout run from the team's folder")

    def test_linked_worktree_outside_teams_gives_the_old_brief(self):
        """A linked worktree named ``f08`` outside ``.troy-teams/`` is no team.

        Planted bugs caught: the sentence added to non-team briefs; the report's team key
        in a normal brief.
        """
        self.assert_same("linked worktree outside .troy-teams")

    def test_worktree_under_teams_that_is_no_team_id(self):
        """A linked worktree ``.troy-teams/scratch``, whose name is not ``f`` and digits."""
        self.assert_same("linked worktree .troy-teams/scratch")

    def test_plain_clone_in_a_teams_folder(self):
        """A plain clone at ``<folder>/.troy-teams/f08`` is no linked worktree, so no team."""
        self.assert_same("plain clone in a .troy-teams/f08 folder")

    def test_unset_environment_without_a_team_is_as_before(self):
        """No ``[lang] environment``: the home checkout keeps ``-n tally``, and a linked
        worktree ``f08`` outside ``.troy-teams/`` keeps its own folder's name, as before.
        """
        old = self.old("DV1", "F08", prefix="bare ")
        home = self.outs[("bare home checkout with a team", "DV1", "F08")]
        self.assertEqual(home.code, 0, home.describe())
        self.assertEqual(home.stdout, old.stdout)
        outside = self.outs[("bare linked worktree outside .troy-teams", "DV1", "F08")]
        report = self.report_of(outside, 0, "brief")
        self.assertNotIn("team", report)
        expected = old.report["prompt"].replace(f" run -n {HOME_NAME} ",
                                                f" run -n {TEAM_FOLDER} ")
        self.assertNotEqual(expected, old.report["prompt"])
        self.assertEqual(report["prompt"], expected)


# ------------------------------------------------------------ worktree HEAD

class WorktreeHeadTests(FlowCase):
    """Contract item 3: ``source_roots`` from the config at the worktree's HEAD."""

    def test_source_roots_come_from_the_worktrees_head(self):
        """A commit in the team worktree sets ``source_roots = ["lib", "app"]``; the home
        checkout's HEAD keeps ``["src"]``. The team's checks use lib and app.

        Planted bug caught: source_roots ignored (read from the home checkout's HEAD).
        """
        prepare()
        fx = Fixture("py5")
        tree = fx.given
        git(tree, "switch", "-q", "-c", "troy-mode/f08-5-impl")
        config = PY_CONFIG.replace('source_roots = ["src"]', 'source_roots = ["lib", "app"]')
        (tree / CONFIG).write_bytes(config.encode("utf-8"))
        git(tree, "add", "--", CONFIG)
        git(tree, "commit", "-q", "-m", "[rules] Add the lib and app source roots")
        old, out = parallel(lambda repo: brief_run("DV2", "F08", repo=repo), [fx.ref.root, tree])
        old_report = self.report_of(old, 0, "brief")
        report = self.report_of(out, 0, "brief")
        value = f"{fx.wt}{SEP}lib{os.pathsep}{fx.wt}{SEP}app"
        old_checks = checks_of(old_report["prompt"])
        self.assertTrue(old_checks, old_report["prompt"])
        self.assertEqual(checks_of(report["prompt"]),
                         [f'PYTHONPATH="{value}" {check}' for check in old_checks])


# ------------------------------------------------------------------ item 8

def hook_env(temp: Path) -> dict:
    """The environment of a hook process, as the hook tests build it."""
    env = base_env({"TMPDIR": str(temp), "TEMP": str(temp), "TMP": str(temp)})
    for name in ("CLAUDE_PROJECT_DIR", "TROY_MODE_PYTHON"):
        env.pop(name, None)
    return env


def run_hook(event: str, payload: dict) -> subprocess.CompletedProcess:
    """Runs ``troy_hook.py <event>`` with the payload on stdin, from a neutral folder."""
    return subprocess.run([sys.executable, str(HOOK), event],
                          input=json.dumps(payload, ensure_ascii=False), cwd=str(neutral()),
                          env=hook_env(new_dir("hooktemp")), capture_output=True,
                          encoding="utf-8", errors="replace", timeout=120, check=False)


def write_transcript(folder: Path, agent_id: str, prompt: str) -> None:
    """Writes a role's transcript: its brief as the first line's user message, then a reply.

    Args:
        folder: The folder of the input's ``transcript_path``.
        agent_id: The role's agent ID.
        prompt: The brief.
    """
    path = folder / SESSION / "subagents" / f"agent-{agent_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    first = {"parentUuid": None, "isSidechain": True, "agentId": agent_id, "sessionId": SESSION,
             "type": "user", "message": {"role": "user", "content": prompt},
             "uuid": str(uuid.uuid4()), "timestamp": "2026-11-23T01:00:00.000Z"}
    second = {"isSidechain": True, "agentId": agent_id, "type": "assistant",
              "message": {"role": "assistant",
                          "content": [{"type": "text", "text": "Reading the brief."}]}}
    path.write_bytes((json.dumps(first) + "\n" + json.dumps(second) + "\n").encode("utf-8"))


class HookPlacementTests(FlowCase):
    """Contract item 8: a team brief, read by the hooks of part 1a, places its role."""

    def test_team_brief_places_the_role_in_the_team(self):
        """The first PreToolUse of a role whose transcript holds a team brief: the record is
        in the team worktree's git folder with ``team`` and ``worktree``, none is at home,
        and its Bash command is rooted in the worktree. For DV1 and for CR1 on a bug.

        Planted bug caught: the team ID not upper-cased (the hook then finds no team).
        """
        prepare()
        fx = Fixture("py3")
        transcripts = new_dir("transcripts")
        tree_git = Path(git(fx.given, "rev-parse", "--absolute-git-dir").strip())
        home_git = Path(git(fx.home.root, "rev-parse", "--absolute-git-dir").strip())
        for task, item in (("DV1", "F08"), ("CR1", "B12")):
            with self.subTest(task=task):
                report = self.report_of(brief_run(task, item, repo=fx.given), 0, "brief")
                agent_id = "a" + uuid.uuid4().hex[:16]
                write_transcript(transcripts, agent_id, report["prompt"])
                tool_input = {"command": "ls", "description": "List files"}
                payload = {"session_id": SESSION,
                           "transcript_path": str(transcripts / f"{SESSION}.jsonl"),
                           "cwd": str(fx.home.root), "hook_event_name": "PreToolUse",
                           "permission_mode": "acceptEdits", "agent_id": agent_id,
                           "agent_type": report["agent"]["subagent_type"],
                           "tool_name": "Bash", "tool_input": tool_input}
                proc = run_hook("PreToolUse", payload)
                shown = f"\nexit {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
                self.assertEqual(proc.returncode, 0, shown)
                try:
                    data = json.loads(proc.stdout) if proc.stdout.strip() else None
                except ValueError:
                    data = None
                self.assertIsInstance(data, dict, "no rooted command" + shown)
                specific = data.get("hookSpecificOutput") or {}
                command = (specific.get("updatedInput") or {}).get("command", "")
                match = BASH_ROOT.fullmatch(command)
                self.assertIsNotNone(match, f"not rooted: {command!r}" + shown)
                self.assertTrue(same_path(match.group(1), fx.wt), command)
                self.assertEqual(match.group(2), "ls")
                path = tree_git / "troy-mode" / "agents" / f"{agent_id}.json"
                self.assertTrue(path.is_file(), f"no record in {tree_git}" + shown)
                record = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(record.get("team"), TEAM_ID, record)
                self.assertIsInstance(record.get("worktree"), str, record)
                self.assertTrue(same_path(record["worktree"], fx.wt), record)
                self.assertFalse((home_git / "troy-mode" / "agents" / f"{agent_id}.json")
                                 .exists(), "a record in the home checkout's git folder")


if __name__ == "__main__":
    unittest.main()
