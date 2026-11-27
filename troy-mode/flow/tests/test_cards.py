"""The card table and the briefs it changes (F17 design 4.1, 10, 12.2; step 1 contract 1, 2, 5).

Written from F17 design 1.0 and the step 1 contract before the code exists.
``troyflow.cards`` holds one row per task and card: the task ID, the card's ``SKILL.md`` under
``skills/``, and troy-mode's one fixed line. For a brief of a task with rows, ``brief`` adds
each card's absolute POSIX path to Read first, after the brief's own entries and before the
premise card, and ``Apply `<name>`: <line>`` to the Task field, after every sentence the
engine adds today and before the premise text. A row whose card is missing refuses the brief
with a ``card: `` problem. Every other brief is byte for byte what it was.

Fixtures. ``CardsModuleTests`` imports the module from the engine folder, as
``stops_helpers.engine_module`` does. The engine runs as a subprocess, so the briefs with rows
come from a scratch plugin copy: ``troy-mode/flow``, ``checks``, ``init``, ``hooks``,
``.claude-plugin``, and the premise card copied into a temp folder, two test cards written to
its ``skills/``, and the copy's ``ROWS`` assignment replaced by ``TEST_ROWS``, which also holds
a row whose card the copy does not have. The copy and this repository's engine brief the same
clone, ``stops_helpers.brief_project()``, so each brief with rows is compared with the same
brief without them. ``EmptyTableBriefTests`` compares this repository's briefs with those of
a copy of its engine whose table is empty.

Planted bugs of design 12.2 (PR 1) caught here:

- "A card added to every task's brief": ``CardBriefTests.test_other_tasks_are_unchanged``
  and, once the table has rows, ``EmptyTableBriefTests.test_briefs_equal_an_empty_table``.
- "the path left relative": ``CardBriefTests.test_cards_follow_the_briefs_own_entries`` and
  ``CardsModuleTests.test_absolute_is_a_posix_path_in_the_plugin``.
- "the line added twice": ``CardBriefTests.test_two_rows_keep_table_order`` and
  ``test_sentences_follow_todays_text``.
- "a missing card accepted": ``CardBriefTests.test_a_missing_card_is_refused`` and
  ``CardsModuleTests.test_problems_name_each_missing_card``.
- "the premise card left out": ``CardBriefTests.test_cards_come_before_the_premise_card``.

On the engine before step 1 (``origin/main``, ``ed51f81``) every test failed because
``troyflow.cards`` was missing, except the comparison of briefs, which step 1's build first ran
against ``origin/main``'s engine and which passed there by design.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import threading
import unittest
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Optional

from flow_helpers import (
    PLUGIN_ROOT, Fakes, FlowCase, Outcome, Project, base_env, new_dir, parallel,
    same_path, write_file,
)
from stops_helpers import (
    BUG_A, REFACTOR, RULE_TEST_FIX, TEST_FIX, brief_project, brief_steps, engine_module,
    read_first_items, rules_project, task_field,
)
from teams2_helpers import add_team

ENGINE = "troy-mode/flow/troy_flow.py"
ZETA = "skills/zeta-card/SKILL.md"
ALPHA = "skills/alpha-card/SKILL.md"
MISSING = "skills/no-such-card/SKILL.md"
PREMISE_CARD = "skills/principle-attack-the-premise/SKILL.md"
# The copy's table: (task, path, line), in table order. TE1's two rows sit apart and are not
# in name order, so a sorted or a first-only lookup shows. IF1 has a card that exists and one
# that does not.
TEST_ROWS = (
    ("TE1", ZETA, "Check your case's own texts exactly, and nothing that another feature adds."),
    ("CR1", ALPHA, "Read each test against its case's row in the plan."),
    ("TE1", ALPHA, "Name the result that would break each test."),
    ("DV1", ZETA, "Keep each mock body to the one raise."),
    ("TM2", ALPHA, "Say which test checks less than its case promises."),
    ("IF1", ALPHA, "Write each example as a user types it."),
    ("IF1", MISSING, "This card is not in the plugin."),
)
# What the copy needs to start troy_flow.py and brief a project (contract 5).
COPIED = ("troy-mode/flow", "troy-mode/checks", "troy-mode/init", "troy-mode/hooks",
          ".claude-plugin")
# What a full copy of the engine needs for every brief; its tests are left out.
ARCHIVED = (*COPIED, "troy-mode/templates", "agents", "docs/troy-mode/requirements.md",
            "skills/principle-attack-the-premise")
PROJECTS = {"briefs": brief_project, "rules": rules_project}
# The briefs the copy renders: a name mapped to (clone, task, item, title, premise).
CARD_BRIEFS = {
    "TE1": ("briefs", "TE1", "F05", None, False),
    "TE1 premise": ("briefs", "TE1", "F05", None, True),
    "CR1": ("briefs", "CR1", "F01", None, False),
    "DV1": ("briefs", "DV1", "F04", None, False),
    "TM2": ("briefs", "TM2", "F05", None, False),
    "IF1": ("briefs", "IF1", "F02", None, False),
    "DV2": ("briefs", "DV2", "F01", None, False),
    "DV2 premise": ("briefs", "DV2", "F01", None, True),
    "TE3": ("briefs", "TE3", "F01", TEST_FIX, False),
    "TM1": ("briefs", "TM1", "F03", None, False),
    "AR2": ("briefs", "AR2", "F02", None, False),
}
NO_ROWS = ("DV2", "DV2 premise", "TE3", "TM1", "AR2")
# Every author and reviewer brief of the premise tests, and two with --premise, for the
# comparison with an empty table.
MAIN_BRIEFS = (
    ("briefs", "IF1", "F02", None, False), ("briefs", "IF2", "F02", None, False),
    ("briefs", "TM1", "F03", None, False), ("briefs", "TM7", "v0.1", None, False),
    ("briefs", "DV1", "F04", None, False), ("briefs", "DV2", "F01", None, False),
    ("briefs", "DV3", "B12", None, False), ("briefs", "DV4", "F01", None, False),
    ("rules", "DV5", "P01", REFACTOR, False), ("briefs", "TE1", "F05", None, False),
    ("briefs", "TE2", "B13", BUG_A, False), ("briefs", "TE3", "F01", TEST_FIX, False),
    ("briefs", "TE4", "F01", TEST_FIX, False), ("briefs", "TE5", "v0.1", None, False),
    ("rules", "TE6", "P01", RULE_TEST_FIX, False), ("briefs", "AR1", None, None, False),
    ("briefs", "AR2", "F02", None, False), ("briefs", "AR5", "F01", None, False),
    ("briefs", "AR8", "F01", None, False), ("briefs", "CR1", "F01", None, False),
    ("briefs", "IF3", "F03", None, False), ("briefs", "TM2", "F05", None, False),
    ("briefs", "TM4", "F01", None, False),
    ("briefs", "DV2", "F01", None, True), ("briefs", "TE1", "F05", None, True),
)
_REAL: dict = {}
_FAKES: dict = {}
_LOCK = threading.Lock()


# ------------------------------------------------------------------ fixtures

def posix(path) -> str:
    """A path's resolved POSIX form, as the engine writes a plugin path."""
    return Path(path).resolve().as_posix()


def apply(path: str, line: str) -> str:
    """The Task field's sentence for one row, from the contract: ``Apply `<name>`: <line>``."""
    return f"Apply `{path.split('/')[1]}`: {line}"


def rows_of(task: str) -> list:
    """TEST_ROWS of one task, as ``(path, line)`` in table order."""
    return [(path, line) for name, path, line in TEST_ROWS if name == task]


def brief_args(spec: tuple, repo: Optional[Path] = None) -> list:
    """The options of one brief: ``(clone, task, item, title, premise)``."""
    name, task, item, title, premise = spec
    args = ["brief", "--task", task] + (["--item", item] if item else [])
    args += (["--title", title] if title else []) + (["--premise"] if premise else [])
    return args + ["--repo", str(repo or PROJECTS[name]().root), "--json"]


def shared_fakes() -> Fakes:
    """One set of fakes for every run, so the ``mamba`` the checks name is the same in each."""
    with _LOCK:
        if "fakes" not in _FAKES:
            _FAKES["fakes"] = Fakes()
        return _FAKES["fakes"]


def run_with(engine: Path, args: list, cwd: Path) -> Outcome:
    """Runs one plugin copy's ``troy_flow.py`` with the shared fakes, as ``run_engine`` does."""
    proc = subprocess.run([sys.executable, str(engine), *args], cwd=str(cwd),
                          env=base_env(shared_fakes().path_env()), capture_output=True,
                          stdin=subprocess.DEVNULL, timeout=180, check=False)
    stdout = proc.stdout.decode("utf-8", "replace")
    try:
        report = json.loads(stdout)
    except ValueError:
        report = None
    return Outcome(proc.returncode, stdout, proc.stderr.decode("utf-8", "replace"), report)


def run_spec(engine: Path, spec: tuple) -> Outcome:
    """One brief of a clone of PROJECTS, run from the folder that holds the clone."""
    return run_with(engine, brief_args(spec), PROJECTS[spec[0]]().tmp)


def real_runs(specs) -> dict:
    """This repository's engine on each spec, run once per process and kept."""
    specs = list(specs)
    missing = [s for s in dict.fromkeys(specs) if s not in _REAL]
    for spec, out in zip(missing, parallel(lambda s: run_spec(PLUGIN_ROOT / ENGINE, s),
                                           missing)):
        _REAL[spec] = out
    return {spec: _REAL[spec] for spec in specs}


def as_real(report: Optional[dict], root: Path) -> Optional[dict]:
    """A copy's report with the copy's plugin folder written as this repository's."""
    if report is None:
        return None
    return json.loads(json.dumps(report).replace(posix(root), posix(PLUGIN_ROOT)))


def plugin_copy() -> Path:
    """Copies what the engine needs, the premise card, and the two test cards to a temp folder."""
    root = new_dir("cardplugin").resolve() / "tstack"
    for part in COPIED:
        shutil.copytree(PLUGIN_ROOT / part, root / part,
                        ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
    write_file(root, PREMISE_CARD, (PLUGIN_ROOT / PREMISE_CARD).read_bytes())
    write_file(root, ZETA, "---\nname: zeta-card\n---\n\n# Zeta card\n")
    write_file(root, ALPHA, "---\nname: alpha-card\n---\n\n# Alpha card\n")
    return root


def set_rows(root: Path, rows) -> Optional[str]:
    """Replaces the copy's module-level ``ROWS`` assignment with rows.

    Args:
        root: The plugin copy.
        rows: ``(task, path, line)`` triples, written as ``Row(task=, path=, line=)``.

    Returns:
        None, or why the copy's table cannot be set.
    """
    path = root / "troy-mode/flow/troyflow/cards.py"
    if not path.is_file():
        return "troy-mode/flow/troyflow/cards.py is not in the engine (F17 step 1 contract 1)"
    source = path.read_text(encoding="utf-8")
    try:
        module = ast.parse(source)
    except SyntaxError as exc:
        return f"troyflow/cards.py does not parse: {exc}"

    def is_rows(node) -> bool:
        """Whether a module-level statement assigns ROWS."""
        if isinstance(node, ast.AnnAssign):
            return isinstance(node.target, ast.Name) and node.target.id == "ROWS"
        return isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "ROWS" for t in node.targets)
    found = [node for node in module.body if is_rows(node)]
    if len(found) != 1:
        return f"troyflow/cards.py assigns ROWS {len(found)} times at module level, not once"
    lines = source.splitlines(keepends=True)
    table = "ROWS = (\n" + "".join(f"    Row(task={t!r}, path={p!r}, line={x!r}),\n"
                                   for t, p, x in rows) + ")\n"
    node = found[0]
    path.write_bytes(("".join(lines[:node.lineno - 1]) + table
                      + "".join(lines[node.end_lineno:])).encode("utf-8"))
    return None


class CardsCase(FlowCase):
    """Reads the engine's ``troyflow.cards``, or fails each test with the reason it cannot."""

    module = None
    missing = None

    @classmethod
    def load_cards(cls) -> None:
        """Imports ``troyflow.cards`` once, keeping the import error for the tests."""
        try:
            cls.module, cls.missing = engine_module("cards"), None
        except AssertionError as exc:
            cls.module, cls.missing = None, str(exc)

    def cards(self):
        """The module, or a failure that names why it could not be imported."""
        if self.module is None:
            self.fail(self.missing)
        return self.module


# ------------------------------------------------------------------ the module

class CardsModuleTests(CardsCase):
    """``troyflow.cards``: Row, ROWS, PLUGIN, and the five functions (contract 1)."""

    @classmethod
    def setUpClass(cls):
        """Imports the module."""
        cls.load_cards()

    def row(self, task: str, path: str, line: str = "A line."):
        """A Row made by keyword."""
        return self.cards().Row(task=task, path=path, line=line)

    def test_row_is_a_frozen_dataclass(self):
        """Row's fields are task, path, and line, in that order, and a row cannot change."""
        cards = self.cards()
        self.assertTrue(is_dataclass(cards.Row))
        self.assertEqual([f.name for f in fields(cards.Row)], ["task", "path", "line"])
        row = cards.Row("TE1", "skills/principle-x/SKILL.md", "A line.")
        self.assertEqual((row.task, row.path, row.line),
                         ("TE1", "skills/principle-x/SKILL.md", "A line."))
        with self.assertRaises(FrozenInstanceError):
            row.line = "Another line."

    def test_rows_is_a_tuple_of_rows(self):
        """ROWS is a tuple, and each of its entries is a Row."""
        cards = self.cards()
        self.assertIsInstance(cards.ROWS, tuple)
        for row in cards.ROWS:
            with self.subTest(row=row):
                self.assertIsInstance(row, cards.Row)

    def test_plugin_is_the_repository_root(self):
        """PLUGIN is the plugin root, three folders above troyflow, as premise.py's."""
        cards = self.cards()
        self.assertIsInstance(cards.PLUGIN, Path)
        self.assertTrue(same_path(cards.PLUGIN, PLUGIN_ROOT),
                        f"{cards.PLUGIN} is not {PLUGIN_ROOT}")

    def test_name_is_the_folder(self):
        """name gives the <name> of skills/<name>/SKILL.md."""
        cards = self.cards()
        for name in ("principle-prove-it-works", "principle-test-behavior-not-implementation",
                     "reflect"):
            with self.subTest(name=name):
                self.assertEqual(cards.name(self.row("AR2", f"skills/{name}/SKILL.md")), name)

    def test_rows_for_keeps_table_order(self):
        """rows_for gives a task's rows only, as a list in table order; no row, no entry."""
        cards = self.cards()
        rows = (self.row("TE1", "skills/zeta/SKILL.md"), self.row("TM2", "skills/beta/SKILL.md"),
                self.row("TE1", "skills/alpha/SKILL.md"), self.row("TE3", "skills/gamma/SKILL.md"))
        self.assertEqual(cards.rows_for("TE1", rows), [rows[0], rows[2]])
        self.assertIsInstance(cards.rows_for("TE1", rows), list)
        self.assertEqual(cards.rows_for("TE3", rows), [rows[3]])
        for task in ("DV1", "TE", "TM"):
            with self.subTest(task=task):
                self.assertEqual(cards.rows_for(task, rows), [])

    def test_rows_for_defaults_to_the_table(self):
        """Without rows, rows_for reads ROWS, for every task of F04."""
        cards = self.cards()
        for task in engine_module("brief").ALL_TASKS:
            with self.subTest(task=task):
                self.assertEqual(cards.rows_for(task), [r for r in cards.ROWS if r.task == task])

    def test_absolute_is_a_posix_path_in_the_plugin(self):
        """absolute gives (PLUGIN / path).as_posix(): absolute, with no backslash."""
        cards = self.cards()
        row = self.row("TE1", "skills/principle-x/SKILL.md")
        found = cards.absolute(row)
        self.assertEqual(found, (cards.PLUGIN / row.path).as_posix())
        self.assertNotIn("\\", found)
        self.assertTrue(os.path.isabs(found), found)
        self.assertTrue(same_path(found, PLUGIN_ROOT / row.path), found)

    def test_sentence(self):
        """sentence gives ``Apply `<name>`: <line>``, the contract's example exactly."""
        cards = self.cards()
        row = self.row("AR2", "skills/principle-prove-it-works/SKILL.md",
                       "Apply it to the design file.")
        self.assertEqual(cards.sentence(row),
                         "Apply `principle-prove-it-works`: Apply it to the design file.")

    def test_problems_name_each_missing_card(self):
        """One ``card: `` problem per row of the task whose file is missing, naming its path;
        a card that exists and another task's missing card give none."""
        cards = self.cards()
        lost, gone = "skills/principle-no-such-card/SKILL.md", "skills/principle-gone/SKILL.md"
        rows = (self.row("TE1", PREMISE_CARD), self.row("TE1", lost),
                self.row("TE3", "skills/principle-other-missing/SKILL.md"), self.row("TE1", gone))
        found = cards.problems("TE1", rows)
        self.assertEqual(len(found), 2, found)
        for problem in found:
            with self.subTest(problem=problem):
                self.assertIsInstance(problem, str)
                self.assertTrue(problem.startswith("card: "), problem)
                self.assertNotIn(PREMISE_CARD, problem)
                self.assertNotIn("principle-other-missing", problem)
        self.assertEqual(len([p for p in found if lost in p]), 1, found)
        self.assertEqual(len([p for p in found if gone in p]), 1, found)
        self.assertEqual(len(cards.problems("TE3", rows)), 1)

    def test_problems_empty_when_every_card_exists(self):
        """Every card of the task in the plugin, or no row for it: no problem."""
        cards = self.cards()
        rows = (self.row("TE1", PREMISE_CARD), self.row("TE3", "skills/principle-gone/SKILL.md"))
        self.assertEqual(cards.problems("TE1", rows), [])
        self.assertEqual(cards.problems("DV1", rows), [])


# ------------------------------------------------------------------ briefs with rows

class CardBriefTests(FlowCase):
    """Briefs of a plugin copy whose table holds TEST_ROWS, against the same briefs without them
    (contract 2)."""

    @classmethod
    def setUpClass(cls):
        """Builds the copy, sets its rows, and runs each brief with the copy and with this
        repository's engine, side by side; a team brief of TE1 too."""
        brief_project()
        cls.root = plugin_copy()
        cls.missing = set_rows(cls.root, TEST_ROWS)
        real = real_runs(CARD_BRIEFS.values())
        cls.real = {name: real[spec] for name, spec in CARD_BRIEFS.items()}
        cls.copy, cls.team = {}, {}
        if cls.missing is not None:
            return
        engine = cls.root / ENGINE
        cls.copy = dict(zip(CARD_BRIEFS, parallel(lambda s: run_spec(engine, s),
                                                  list(CARD_BRIEFS.values()))))
        project = Project(brief_steps())
        tree = add_team(project, "F05")
        spec = ("briefs", "TE1", "F05", None, False)
        cls.team = dict(zip(("copy", "real"), parallel(
            lambda e: run_with(e, brief_args(spec, tree), project.tmp),
            [engine, PLUGIN_ROOT / ENGINE])))

    def need_rows(self) -> None:
        """Fails the test when the copy's table could not be set."""
        if self.missing is not None:
            self.fail(self.missing)

    def reports(self, name: str, code: int = 0) -> tuple:
        """The copy's and this repository's reports of one brief, both checked."""
        self.need_rows()
        return (self.report_of(self.copy[name], code, "brief"),
                self.report_of(self.real[name], 0, "brief"))

    def card(self, rel: str) -> str:
        """A card's absolute POSIX path in the copy."""
        return (self.root / rel).as_posix()

    def test_cards_follow_the_briefs_own_entries(self):
        """TE1, CR1, DV1, TM2: the brief's own Read first, then each card's absolute POSIX path,
        in the report and in the prompt."""
        for name in ("TE1", "CR1", "DV1", "TM2"):
            with self.subTest(task=name):
                copy, real = self.reports(name)
                cards = [self.card(path) for path, _ in rows_of(name)]
                self.assertEqual(copy["read_first"], real["read_first"] + cards)
                self.assertEqual(read_first_items(copy["prompt"]),
                                 read_first_items(real["prompt"]) + cards)
                for path in cards:
                    self.assertNotIn("\\", path)
                    self.assertTrue(os.path.isabs(path), path)

    def test_cards_come_before_the_premise_card(self):
        """TE1 with ``--premise``: the cards after the brief's own entries, the premise card
        still last."""
        copy, real = self.reports("TE1 premise")
        cards = [self.card(path) for path, _ in rows_of("TE1")]
        premise = self.card(PREMISE_CARD)
        self.assertTrue(same_path(real["read_first"][-1], PLUGIN_ROOT / PREMISE_CARD),
                        real["read_first"])
        self.assertEqual(copy["read_first"], real["read_first"][:-1] + cards + [premise])
        self.assertEqual(read_first_items(copy["prompt"]),
                         read_first_items(real["prompt"])[:-1] + cards + [premise])

    def test_sentences_follow_todays_text(self):
        """TE1, CR1 (after its risks and the platform skip), DV1 (after the mock notes), and
        TM2: the Task field is today's, then `` Apply `<name>`: <line>`` for each row, once."""
        for name in ("TE1", "CR1", "DV1", "TM2"):
            with self.subTest(task=name):
                copy, real = self.reports(name)
                added = "".join(" " + apply(path, line) for path, line in rows_of(name))
                self.assertEqual(task_field(copy["prompt"]), task_field(real["prompt"]) + added)
                for path, line in rows_of(name):
                    self.assertEqual(copy["prompt"].count(apply(path, line)), 1)

    def test_sentences_come_before_the_premise_text(self):
        """TE1 with ``--premise``: today's Task text, the two sentences, then the premise text,
        which stays last."""
        copy, real = self.reports("TE1 premise")
        _, plain = self.reports("TE1")
        text = engine_module("premise").TEXT
        added = "".join(" " + apply(path, line) for path, line in rows_of("TE1"))
        self.assertEqual(task_field(real["prompt"]), task_field(plain["prompt"]) + " " + text)
        self.assertEqual(task_field(copy["prompt"]),
                         task_field(plain["prompt"]) + added + " " + text)

    def test_two_rows_keep_table_order(self):
        """TE1's rows, zeta-card then alpha-card, apart in the table: both, in that order, each
        once, in Read first and in the Task field."""
        copy, _ = self.reports("TE1")
        zeta, alpha = self.card(ZETA), self.card(ALPHA)
        self.assertEqual(copy["read_first"][-2:], [zeta, alpha])
        self.assertEqual(copy["read_first"].count(zeta), 1)
        self.assertEqual(copy["read_first"].count(alpha), 1)
        field = task_field(copy["prompt"])
        first, second = (apply(path, line) for path, line in rows_of("TE1"))
        self.assertTrue(field.endswith(f" {first} {second}"), field[-500:])
        for sentence in (first, second):
            self.assertEqual(field.count(sentence), 1)

    def test_other_tasks_are_unchanged(self):
        """DV2 (with and without ``--premise``), TE3, TM1, and AR2 have no row: the copy's
        report, its prompt included, equals this repository's."""
        for name in NO_ROWS:
            with self.subTest(brief=name):
                copy, real = self.reports(name)
                self.assertEqual(as_real(copy, self.root), real)

    def test_a_missing_card_is_refused(self):
        """IF1's second card is not in the copy: exit 1, ``ok`` false, and one problem that
        starts ``card: `` and names its path; the card that exists is not named."""
        self.need_rows()
        report = self.report_of(self.copy["IF1"], 1, "brief")
        self.assertIs(report["ok"], False)
        self.assertEqual(len(report["problems"]), 1, report["problems"])
        problem = report["problems"][0]
        self.assertIsInstance(problem, str)
        self.assertTrue(problem.startswith("card: "), problem)
        self.assertIn(MISSING, problem)
        self.assertNotIn(ALPHA, problem)
        self.report_of(self.real["IF1"], 0, "brief")

    def test_team_brief_keeps_the_plugin_path(self):
        """In F05's team worktree, TE1's Read first is the team's own entries, then the cards at
        the plugin's absolute POSIX paths, not rewritten into the worktree."""
        self.need_rows()
        copy = self.report_of(self.team["copy"], 0, "brief")
        real = self.report_of(self.team["real"], 0, "brief")
        self.assertIn("team", real)
        cards = [self.card(path) for path, _ in rows_of("TE1")]
        self.assertEqual(copy["read_first"], real["read_first"] + cards)
        self.assertEqual(read_first_items(copy["prompt"]),
                         read_first_items(real["prompt"]) + cards)


# ------------------------------------------------------------------ the real table

class RealTableTests(CardsCase):
    """This repository's table: every row names a card that tstack ships (design 4.1, 10)."""

    @classmethod
    def setUpClass(cls):
        """Imports the module."""
        cls.load_cards()

    def test_every_row_names_a_card_in_the_plugin(self):
        """Each row: a task of F04, ``skills/<name>/SKILL.md`` that exists, and a line; and
        ``problems`` is empty for every task."""
        cards = self.cards()
        tasks = engine_module("brief").ALL_TASKS
        for row in cards.ROWS:
            with self.subTest(row=row):
                self.assertIn(row.task, tasks)
                self.assertRegex(row.path, r"^skills/[A-Za-z0-9_.-]+/SKILL\.md$")
                self.assertTrue((PLUGIN_ROOT / row.path).is_file(), row.path)
                self.assertTrue(row.line.strip())
        for task in tasks:
            with self.subTest(task=task):
                self.assertEqual(cards.problems(task), [])


def empty_copy() -> Path:
    """This repository's engine in a temp folder, with its card table emptied."""
    root = new_dir("emptyplugin").resolve() / "tstack"
    for part in ARCHIVED:
        source = PLUGIN_ROOT / part
        if source.is_dir():
            shutil.copytree(source, root / part,
                            ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
        else:
            write_file(root, part, source.read_bytes())
    problem = set_rows(root, ())
    if problem:
        raise AssertionError(problem)
    return root


class EmptyTableBriefTests(FlowCase):
    """A task with no row in the table gets the brief it would get with no table at all
    (contract 2): this repository's engine against a copy of it whose ``ROWS`` is empty.

    Step 1's build first compared these briefs with ``origin/main``'s engine (``ed51f81``), from
    before the table existed, and every one was the same. This form compares within one
    version, so a later change to a brief's text for another reason does not break it. A task
    with a row in this repository's table is left out.
    """

    @classmethod
    def setUpClass(cls):
        """Runs every brief with the emptied copy and with this repository's engine, side by
        side."""
        cls.empty = empty_copy()
        try:
            tasks = {row.task for row in engine_module("cards").ROWS}
        except AssertionError:
            tasks = set()
        cls.specs = [s for s in MAIN_BRIEFS if s[1] not in tasks]
        brief_project()
        rules_project()
        cls.real = real_runs(cls.specs)
        engine = cls.empty / ENGINE
        cls.old = dict(zip(cls.specs, parallel(lambda s: run_spec(engine, s), cls.specs)))

    def test_briefs_equal_an_empty_table(self):
        """Every author and reviewer brief of the premise tests, and two with ``--premise``:
        the same exit code and the same report, its prompt included."""
        for spec in self.specs:
            with self.subTest(brief=spec):
                old, new = self.old[spec], self.real[spec]
                self.assertIsInstance(new.report, dict, new.describe())
                self.assertEqual(new.code, old.code, new.describe())
                self.assertEqual(new.report, as_real(old.report, self.empty))


if __name__ == "__main__":
    unittest.main()
