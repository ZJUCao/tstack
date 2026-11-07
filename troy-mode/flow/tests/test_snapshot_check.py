"""Snapshot and check group (F07 design 6.2, 7, 14.1): ``snapshot`` and ``check-run``.

Planted bugs of design 14.2 caught here:

- "a dirty tree accepted by ``snapshot``": ``SnapshotTests.test_dirty_tree_is_refused`` and
  ``test_staged_change_makes_the_tree_dirty``.
- "the Developer's scope with the ``tests`` class":
  ``ScopeTests.test_developer_writing_a_test_is_out_of_scope``.
- "AR2 allowed to change the whole design": ``SectionTests`` (every test but the two that pass).
- "a dependency change allowed without ``--allow-dependency``":
  ``DependencyTests.test_dependency_change_needs_allow_dependency``.
- "another role's log lines reported": ``HooksLogTests``.
"""

import json
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flow_helpers import (
    ARCHITECTURE, ARCHITECTURE_ZH, F01, F02, REQUIREMENTS, REQUIREMENTS_ZH, WORK_BRANCH, Fakes,
    FlowCase, Project, base_files, base_step, design_text, git_proc, hooks_line, parallel,
    problem_kinds, run_engine, same_path, split_command, stages,
)

TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DESIGN_ZH = f"{F01.folder}/design.zh-CN.md"
PLAN_ZH = f"{F01.folder}/test-plan.zh-CN.md"
EXTRA = {"src/wordcount/old.py": '"""Old."""\n', "tests/test_base.py": '"""Base tests."""\n'}
EN_ROUND = "| 1 | None | None |\n"
ZH_ROUND = "| 1 | 无 | 无 |\n"
EN_ROUND_2 = EN_ROUND + "| 2 | Naming | Renamed count. |\n"
ZH_ROUND_2 = ZH_ROUND + "| 2 | 命名 | 已改名。 |\n"


def check_project() -> Project:
    """A clone with F01's design and test plan merged, plus source, tests, and a manifest."""
    return Project([base_step(base_files(extra=EXTRA)), *stages(F01, 2)])


def edited(text: str, old: str, new: str) -> str:
    """Replaces the one occurrence of a text, failing if it is not there exactly once."""
    if text.count(old) != 1:
        raise AssertionError(f"{old!r} occurs {text.count(old)} times")
    return text.replace(old, new)


def fresh_role_run(role: str, changes: dict):
    """In a new clone: snapshot for one role, write the changes, and run check-run.

    Args:
        role: The role.
        changes: Paths mapped to new text.

    Returns:
        The check-run outcome, or the snapshot's when the snapshot failed.
    """
    project = check_project()
    snap = project.run("snapshot", "--role", role)
    if snap.code != 0 or not isinstance(snap.report, dict):
        return snap
    for rel, text in changes.items():
        project.write(rel, text)
    return project.run("check-run", "--run", snap.report["run"])


def shifted(time_text: str, seconds: int) -> str:
    """A ``YYYY-MM-DDTHH:MM:SSZ`` time moved by some seconds."""
    when = datetime.strptime(time_text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (when + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


class RunCase(FlowCase):
    """One shared clone, put back to its first state before every test."""

    @classmethod
    def setUpClass(cls):
        """Builds the clone and remembers its HEAD."""
        cls.project = check_project()
        cls.base = cls.project.head()

    def setUp(self):
        """Returns to the work branch at the first HEAD, removes every other file and the log."""
        project = self.project
        project.git("switch", "-q", "-f", WORK_BRANCH)
        project.git("reset", "-q", "--hard", self.base)
        project.git("clean", "-q", "-fdx")
        log = project.git_dir() / "troy-mode" / "hooks.log"
        if log.exists():
            log.unlink()

    def snapshot(self, *roles: str, fakes=None) -> dict:
        """Takes a snapshot for the roles and returns its report (exit 0 asserted)."""
        args = ["snapshot"]
        for role in roles:
            args += ["--role", role]
        return self.report_of(self.project.run(*args, fakes=fakes), 0, "snapshot")

    def apply(self, changes: dict) -> None:
        """Writes files (text), or deletes them for None, in the working tree."""
        for rel, content in changes.items():
            if content is None:
                self.project.remove(rel)
            else:
                self.project.write(rel, content)

    def check(self, run: str, *allow: str, fakes=None):
        """Runs ``check-run`` for a run ID with ``--allow-dependency`` paths."""
        args = ["check-run", "--run", run]
        for path in allow:
            args += ["--allow-dependency", path]
        return self.project.run(*args, fakes=fakes)

    def run_role(self, roles, changes: dict, allow=(), code: int = 0) -> dict:
        """Snapshot, changes, and check-run; asserts the exit code and returns the report.

        Args:
            roles: One role name or a tuple of them.
            changes: Paths mapped to new text, None to delete.
            allow: Paths for ``--allow-dependency``.
            code: The expected exit code of check-run.

        Returns:
            The check-run report.
        """
        roles = (roles,) if isinstance(roles, str) else tuple(roles)
        run = self.snapshot(*roles)["run"]
        self.apply(changes)
        return self.report_of(self.check(run, *allow), code, "check-run")

    def assert_passes(self, report: dict, paths) -> None:
        """Asserts no problem, the sorted paths to stage, no undo, and no escalation."""
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["stage"], sorted(paths))
        self.assertEqual(report["undo"], [])
        self.assertIs(report["escalate"], False)


class SnapshotTests(RunCase):
    """The state before a run (design 6.2 step 1, 7)."""

    def records(self) -> list:
        """The run records in the clone's git folder."""
        folder = self.project.git_dir() / "troy-mode" / "flow"
        return sorted(folder.glob("*.json")) if folder.is_dir() else []

    def test_clean_tree_records_the_run(self):
        """A clean tree: the report and the record hold the run, roles, HEAD, branch, and time."""
        report = self.snapshot("developer")
        self.assertIsInstance(report["run"], str)
        self.assertNotEqual(report["run"], "")
        self.assertEqual(report["roles"], ["developer"])
        self.assertEqual(report["head"], self.base)
        self.assertEqual(report["branch"], WORK_BRANCH)
        self.assertRegex(report["time"], TIME)
        path = self.project.git_dir() / "troy-mode" / "flow" / f"{report['run']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        for key in ("run", "roles", "head", "branch", "time"):
            self.assertEqual(record[key], report[key], key)
        self.assertEqual(self.project.status_lines(), [])

    def test_dirty_tree_is_refused(self):
        """Planted bug "a dirty tree accepted": a changed and a new file refuse the snapshot."""
        before = self.records()
        self.project.write("README.md", "# changed\n")
        self.project.write("src/wordcount/new.py", '"""New."""\n')
        report = self.report_of(self.project.run("snapshot", "--role", "developer"), 1, "snapshot")
        self.assertIsNone(report["run"])
        self.assertEqual(problem_kinds(report), [("dirty", "README.md"),
                                                 ("dirty", "src/wordcount/new.py")])
        self.assertEqual(self.records(), before)

    def test_text_report_of_a_dirty_tree_exits_one(self):
        """Without ``--json``, a refused snapshot still exits 1 and writes no record."""
        before = self.records()
        self.project.write("README.md", "# changed\n")
        out = run_engine(["snapshot", "--role", "developer", "--repo", self.project.root],
                         self.project.tmp, Fakes(fail=True))
        self.assert_exit(out, 1)
        self.assertEqual(self.records(), before)

    def test_staged_change_makes_the_tree_dirty(self):
        """Planted bug "a dirty tree accepted": a staged change alone also refuses."""
        self.project.write("src/wordcount/__init__.py", '"""Staged."""\n')
        self.project.git("add", "src/wordcount/__init__.py")
        report = self.report_of(self.project.run("snapshot", "--role", "developer"), 1)
        self.assertEqual(problem_kinds(report), [("dirty", "src/wordcount/__init__.py")])

    def test_ignored_files_leave_the_tree_clean(self):
        """Files git ignores do not make the tree dirty."""
        self.project.write("reports/junit.xml", "<testsuites/>\n")
        self.project.write(".troy-mode/progress.md", "# Progress\n")
        self.snapshot("developer")

    def test_run_ids_are_unique(self):
        """Two snapshots in a row get different run IDs and two records."""
        first = self.snapshot("developer")["run"]
        second = self.snapshot("developer")["run"]
        self.assertNotEqual(first, second)
        names = {path.stem for path in self.records()}
        self.assertTrue({first, second} <= names, names)

    def test_unknown_role_exits_two(self):
        """A role that is not one of F04's seven exits 2."""
        self.assert_exit(self.project.run("snapshot", "--role", "manager"), 2)

    def test_detached_head_has_no_branch(self):
        """A detached HEAD is recorded with a null branch."""
        self.project.git("switch", "-q", "--detach")
        report = self.snapshot("code-reviewer")
        self.assertIsNone(report["branch"])
        self.assertEqual(report["head"], self.base)

    def test_several_roles_for_reviews_together(self):
        """``--role`` repeats for read-only reviews that run together."""
        report = self.snapshot("test-manager", "code-reviewer")
        self.assertEqual(sorted(report["roles"]), ["code-reviewer", "test-manager"])

    def test_worktree_records_in_its_own_git_folder(self):
        """In a worktree, the record goes to that worktree's own git folder."""
        tree = self.project.tmp / f"tree-{self.id().rsplit('.', 1)[-1]}"
        self.project.git("worktree", "add", "-q", "-b", "troy-mode/tree", str(tree), self.base)
        try:
            out = self.project.run("snapshot", "--role", "developer", repo_option=False, cwd=tree)
            report = self.report_of(out)
            git_dir = Path(git_proc(tree, "rev-parse", "--absolute-git-dir").stdout.strip())
            self.assertFalse(same_path(git_dir, self.project.git_dir()))
            self.assertTrue((git_dir / "troy-mode" / "flow" / f"{report['run']}.json").is_file())
            self.assertNotIn(report["run"], {p.stem for p in self.records()})
            self.assertEqual(report["branch"], "troy-mode/tree")
        finally:
            self.project.git("worktree", "remove", "--force", str(tree))
            self.project.git("branch", "-q", "-D", "troy-mode/tree")

    def test_snapshot_and_check_run_never_call_gh(self):
        """A gh that fails on every call is called by neither command."""
        fakes = Fakes(fail=True)
        run = self.snapshot("developer", fakes=fakes)["run"]
        self.report_of(self.check(run, fakes=fakes), 0)
        self.assertEqual(fakes.gh_calls(), [])


class InScopeTests(RunCase):
    """Changes inside each role's write scope pass and are staged (F04 section 3)."""

    def test_architect(self):
        """The architecture, its mirror, and a new ADR."""
        changes = {ARCHITECTURE: self.project.read(ARCHITECTURE) + "More.\n",
                   ARCHITECTURE_ZH: self.project.read(ARCHITECTURE_ZH) + "更多。\n",
                   "docs/adr/0001-use-plain-files.md": "# ADR 1\n"}
        self.assert_passes(self.run_role("architect", changes), changes)

    def test_interface_designer(self):
        """Any part of a design, and a new design of another feature."""
        text = self.project.read(F01.design)
        changes = {F01.design: edited(text, "def count(text: str) -> int",
                                      "def count(text: str, strict: bool) -> int"),
                   F02.design: design_text(F02, "0.1")}
        self.assert_passes(self.run_role("interface-designer", changes), changes)

    def test_test_manager(self):
        """A feature's test plan and a version's test plan."""
        changes = {F01.plan: self.project.read(F01.plan) + "- F01-T02: empty text.\n",
                   "docs/versions/v0.1/test-plan.md": "# v0.1 test plan\n"}
        self.assert_passes(self.run_role("test-manager", changes), changes)

    def test_developer(self):
        """Source files changed, added, and deleted: each is listed with its status and class."""
        changes = {"src/wordcount/__init__.py": '"""Counts words and lines."""\n',
                   "src/wordcount/count.py": '"""Count."""\n', "src/wordcount/old.py": None}
        report = self.run_role("developer", changes)
        self.assert_passes(report, changes)
        self.assertEqual(sorted((c["path"], c["status"], c["class"]) for c in report["changed"]),
                         [("src/wordcount/__init__.py", " M", "source"),
                          ("src/wordcount/count.py", "??", "source"),
                          ("src/wordcount/old.py", " D", "source")])

    def test_test_engineer(self):
        """A new test file and a changed one, in the tests class."""
        changes = {"tests/test_count.py": '"""Tests."""\n',
                   "tests/test_base.py": '"""Base tests, changed."""\n'}
        report = self.run_role("test-engineer", changes)
        self.assert_passes(report, changes)
        self.assertEqual({c["class"] for c in report["changed"]}, {"tests"})

    def test_product_manager(self):
        """The requirements, a prototype, and the changelog (F04 section 3)."""
        changes = {REQUIREMENTS: self.project.read(REQUIREMENTS) + "More.\n",
                   REQUIREMENTS_ZH: self.project.read(REQUIREMENTS_ZH) + "更多。\n",
                   "docs/prototypes/main-screen.md": "# Main screen\n", "CHANGELOG.md": "# 0.1\n"}
        self.assert_passes(self.run_role("product-manager", changes), changes)

    def test_code_reviewer_without_changes(self):
        """A review that changes nothing passes with nothing to stage."""
        report = self.run_role("code-reviewer", {})
        self.assert_passes(report, [])
        self.assertEqual(report["changed"], [])

    def test_ignored_paths_never_count(self):
        """Ignored build output is neither listed nor a problem, even for the Code Reviewer."""
        report = self.run_role("code-reviewer", {"reports/junit.xml": "<testsuites/>\n",
                                                 "__pycache__/x.pyc": "x",
                                                 ".troy-mode/progress.md": "# Progress\n"})
        self.assert_passes(report, [])
        self.assertEqual(report["changed"], [])


class ScopeTests(RunCase):
    """Changes outside a role's write scope are ``scope`` problems (design 7, item 2)."""

    def assert_scope(self, role: str, changes: dict, paths) -> dict:
        """Runs the role, asserts exit 1 with exactly these scope problems, returns the report."""
        report = self.run_role(role, changes, code=1)
        self.assert_scope_report(report, paths)
        return report

    def assert_scope_report(self, report: dict, paths) -> None:
        """Asserts exactly these scope problems, nothing to stage, and no escalation."""
        self.assertEqual(problem_kinds(report), [("scope", p) for p in sorted(paths)])
        self.assertEqual(report["stage"], [])
        self.assertIs(report["escalate"], False)

    def test_developer_writing_a_test_is_out_of_scope(self):
        """Planted bug "the Developer's scope with the tests class": a test file is a problem."""
        self.assert_scope("developer", {"tests/test_count.py": '"""Tests."""\n',
                                        "src/wordcount/count.py": '"""Count."""\n'},
                          ["tests/test_count.py"])

    def test_each_role_outside_its_scope(self):
        """For each role, a path of another role's scope is a problem; its own path is not."""
        cases = {
            "architect": ({"src/wordcount/count.py": "x = 1\n",
                           F01.plan: "# changed\n"}, ["src/wordcount/count.py", F01.plan]),
            "interface-designer": ({ARCHITECTURE: "# changed\n"}, [ARCHITECTURE]),
            "test-manager": ({F01.design: "# changed\n"}, [F01.design]),
            "developer": ({"docs/notes.md": "# Notes\n", "README.md": "# changed\n"},
                          ["README.md", "docs/notes.md"]),
            "test-engineer": ({"src/wordcount/count.py": "x = 1\n",
                               "tests/test_count.py": "x = 1\n"}, ["src/wordcount/count.py"]),
            "code-reviewer": ({"src/wordcount/__init__.py": "x = 1\n", "docs/review.md": "ok\n"},
                              ["docs/review.md", "src/wordcount/__init__.py"]),
            "product-manager": ({ARCHITECTURE: "# changed\n", "src/wordcount/x.py": "x = 1\n",
                                 "docs/prototypes/a.md": "# A\n"},
                                [ARCHITECTURE, "src/wordcount/x.py"]),
        }
        outs = parallel(lambda role: fresh_role_run(role, cases[role][0]), list(cases))
        for (role, (_, paths)), out in zip(cases.items(), outs):
            with self.subTest(role=role):
                self.assert_scope_report(self.report_of(out, 1, "check-run"), paths)

    def test_config_paths_belong_to_no_role(self):
        """The rules, the config folder, and the workflows are outside every scope."""
        changes = {"docs/rules.md": "# changed\n", ".github/workflows/ci.yml": "name: ci\n",
                   ".troy-mode/config.toml": "[attribution]\nmode = \"strict\"\n"}
        roles = ("architect", "interface-designer", "test-manager", "developer", "test-engineer",
                 "product-manager")
        outs = parallel(lambda role: fresh_role_run(role, changes), roles)
        for role, out in zip(roles, outs):
            with self.subTest(role=role):
                self.assert_scope_report(self.report_of(out, 1, "check-run"), list(changes))

    def test_reviews_together_may_change_nothing(self):
        """With two roles at the snapshot, even a path in one's scope is a problem."""
        self.assert_scope(("test-manager", "code-reviewer"),
                          {F01.plan: self.project.read(F01.plan) + "More.\n"}, [F01.plan])
        self.setUp()
        self.assert_passes(self.run_role(("test-manager", "code-reviewer"), {}), [])


class SectionTests(RunCase):
    """Planted bug "AR2 allowed to change the whole design": only section 4 (F04 D37)."""

    def assert_section(self, changes: dict, paths) -> None:
        """Runs the Architect and asserts exactly these ``section`` problems."""
        report = self.run_role("architect", changes, code=1)
        self.assertEqual(problem_kinds(report), [("section", p) for p in sorted(paths)])
        self.assertEqual(report["stage"], [])

    def test_section_four_in_both_languages_passes(self):
        """A new rounds-log row in both files, under the real ``## 4.`` heading, passes."""
        changes = {F01.design: edited(self.project.read(F01.design), EN_ROUND, EN_ROUND_2),
                   DESIGN_ZH: edited(self.project.read(DESIGN_ZH), ZH_ROUND, ZH_ROUND_2)}
        self.assert_passes(self.run_role("architect", changes), changes)

    def test_interface_designer_may_change_any_section(self):
        """The section rule is the Architect's only: IF2 changes sections 2 and 4."""
        text = edited(self.project.read(F01.design), EN_ROUND, EN_ROUND_2)
        text = edited(text, "def count(text: str) -> int", "def count(text: str, n: int) -> int")
        self.assert_passes(self.run_role("interface-designer", {F01.design: text}), [F01.design])

    def test_change_in_section_two(self):
        """A signature change in section 2 is a problem."""
        self.assert_section({F01.design: edited(self.project.read(F01.design),
                                                "def count(text: str) -> int",
                                                "def count(text: str, n: int) -> int")},
                            [F01.design])

    def test_change_inside_a_fenced_block(self):
        """A ``## 4.`` line in a fenced block is section 2's text: changing it is a problem."""
        self.assert_section({F01.design: edited(self.project.read(F01.design),
                                                "## 4. Not a heading inside a fence",
                                                "## 4. Still not a heading")},
                            [F01.design])

    def test_mirror_changed_outside_section_four(self):
        """Section 4 in English but section 2 in Chinese: the mirror is the problem."""
        zh = edited(self.project.read(DESIGN_ZH), "def count(text: str) -> int",
                    "def count(text: str, n: int) -> int")
        self.assert_section({F01.design: edited(self.project.read(F01.design), EN_ROUND,
                                                EN_ROUND_2), DESIGN_ZH: zh}, [DESIGN_ZH])

    def test_front_matter_change(self):
        """The block before the first ``## `` heading is outside section 4."""
        self.assert_section({F01.design: edited(self.project.read(F01.design),
                                                'updated: "2026-11-01"', 'updated: "2026-11-08"')},
                            [F01.design])

    def test_added_section(self):
        """A new ``## 6.`` section is a problem."""
        text = self.project.read(F01.design) + "\n## 6. Notes\n\nMore.\n"
        self.assert_section({F01.design: text}, [F01.design])

    def test_new_design(self):
        """A design that does not exist at HEAD is a problem."""
        self.assert_section({F02.design: design_text(F02, "0.1")}, [F02.design])

    def test_deleted_mirror(self):
        """Deleting a design's mirror is a problem."""
        self.assert_section({DESIGN_ZH: None}, [DESIGN_ZH])


class DependencyTests(RunCase):
    """Dependency files need ``--allow-dependency`` (design 7, item 4; R16)."""

    MANIFEST = '[project]\nname = "wordcount"\nversion = "0.1.0"\ndependencies = ["click"]\n'

    def test_dependency_change_needs_allow_dependency(self):
        """Planted bug "dependency allowed": the Developer and the Test Engineer are stopped."""
        for role in ("developer", "test-engineer"):
            with self.subTest(role=role):
                self.setUp()
                report = self.run_role(role, {"pyproject.toml": self.MANIFEST}, code=1)
                self.assertEqual(problem_kinds(report), [("dependency", "pyproject.toml")])
                self.assertEqual(report["stage"], [])

    def test_allowed_dependency_passes(self):
        """Named with ``--allow-dependency``, the manifest is staged with the source."""
        changes = {"pyproject.toml": self.MANIFEST, "src/wordcount/cli.py": '"""CLI."""\n'}
        report = self.run_role("developer", changes, allow=["pyproject.toml"])
        self.assert_passes(report, changes)

    def test_another_allowed_path_does_not_cover_it(self):
        """Allowing a different dependency file leaves this one a problem."""
        report = self.run_role("developer", {"pyproject.toml": self.MANIFEST},
                               allow=["environment.yml"], code=1)
        self.assertEqual(problem_kinds(report), [("dependency", "pyproject.toml")])

    def test_dependency_outside_the_scope_is_a_scope_problem(self):
        """For the Architect, a manifest is outside the scope, not a dependency question."""
        report = self.run_role("architect", {"pyproject.toml": self.MANIFEST},
                               allow=["pyproject.toml"], code=1)
        self.assertEqual(problem_kinds(report), [("scope", "pyproject.toml")])


class HeadBranchTests(RunCase):
    """A changed HEAD or branch means the hooks failed: escalate (design 7, item 1)."""

    def test_new_commit_escalates(self):
        """A commit during the run is a ``head`` problem, escalated, with nothing to undo."""
        run = self.snapshot("developer")["run"]
        self.project.commit("[F01 3/6 mock] Count words", {"src/wordcount/count.py": "x = 1\n"})
        report = self.report_of(self.check(run), 1)
        self.assertIn(("head", None), problem_kinds(report))
        self.assertIs(report["escalate"], True)
        self.assertEqual((report["stage"], report["undo"]), ([], []))

    def test_switched_branch_escalates(self):
        """A new branch at the same commit is a ``branch`` problem only."""
        run = self.snapshot("developer")["run"]
        self.project.git("switch", "-q", "-c", "troy-mode/elsewhere")
        report = self.report_of(self.check(run), 1)
        self.assertEqual(problem_kinds(report), [("branch", None)])
        self.assertIs(report["escalate"], True)

    def test_detached_head_escalates(self):
        """Detaching HEAD changes the branch to none."""
        run = self.snapshot("developer")["run"]
        self.project.git("switch", "-q", "--detach")
        report = self.report_of(self.check(run), 1)
        self.assertEqual(problem_kinds(report), [("branch", None)])
        self.assertIs(report["escalate"], True)

    def test_unknown_run_exits_two(self):
        """A run ID with no record exits 2."""
        self.assert_exit(self.check("20260101T000000Z-00000000"), 2)


class UndoTests(RunCase):
    """The undo steps: restore what HEAD has, delete what it does not (design 7)."""

    CHANGES = {"src/wordcount/__init__.py": '"""Changed."""\n',
               "tests/test_new.py": '"""New."""\n',
               ARCHITECTURE: "# changed\n", "tests/test_base.py": None}

    def test_undo_lists_every_changed_path(self):
        """One entry per changed path, sorted, with the exact command of the interface note."""
        report = self.run_role("developer", self.CHANGES, code=1)
        restore = "git restore --source=HEAD --staged --worktree -- "
        self.assertEqual(report["undo"], [
            {"path": ARCHITECTURE, "action": "restore", "command": restore + ARCHITECTURE},
            {"path": "src/wordcount/__init__.py", "action": "restore",
             "command": restore + "src/wordcount/__init__.py"},
            {"path": "tests/test_base.py", "action": "restore",
             "command": restore + "tests/test_base.py"},
            {"path": "tests/test_new.py", "action": "delete",
             "command": "rm -f -- tests/test_new.py"},
        ])

    def test_check_run_changes_nothing_and_the_undo_restores_the_tree(self):
        """check-run leaves the run's changes; following the undo makes the tree clean."""
        run = self.snapshot("developer")["run"]
        self.apply(self.CHANGES)
        before = self.project.status_lines()
        report = self.report_of(self.check(run), 1)
        self.assertEqual(self.project.status_lines(), before)
        for entry in report["undo"]:
            words = split_command(entry["command"])
            if entry["action"] == "restore":
                self.assertEqual(words[0], "git")
                self.project.git(*words[1:])
            else:
                self.assertEqual(words[:3], ["rm", "-f", "--"])
                self.project.remove(words[3])
        self.assertEqual(self.project.status_lines(), [])


class HooksLogTests(RunCase):
    """Planted bug "another role's log lines reported": only this role's, since the snapshot."""

    def write_log(self, lines) -> None:
        """Writes ``<git dir>/troy-mode/hooks.log`` from dicts and raw strings."""
        folder = self.project.git_dir() / "troy-mode"
        folder.mkdir(parents=True, exist_ok=True)
        text = "".join((line if isinstance(line, str) else json.dumps(line)) + "\n"
                       for line in lines)
        (folder / "hooks.log").write_bytes(text.encode("utf-8"))

    def test_only_this_roles_lines_since_the_snapshot(self):
        """An older line, another role's line, and the main session's line are left out."""
        snap = self.snapshot("developer")
        dev = "troy-pstack:troy-developer"
        at = hooks_line(snap["time"], dev, "a1", path="tests/a.py")
        later = hooks_line(shifted(snap["time"], 10), dev, "a1", path="tests/b.py")
        self.write_log([
            hooks_line(shifted(snap["time"], -120), dev, "a0", path="tests/old.py"),
            at,
            hooks_line(shifted(snap["time"], 5), "troy-pstack:troy-test-engineer", "a2"),
            hooks_line(shifted(snap["time"], 6), None, None),
            "not a JSON line",
            later,
        ])
        self.project.write("src/wordcount/count.py", '"""Count."""\n')
        report = self.report_of(self.check(snap["run"]), 0)
        self.assertEqual(report["hooks_log"], [at, later])
        self.assertEqual(report["problems"], [])

    def test_product_manager_gets_the_main_sessions_lines(self):
        """For the Product Manager, lines with no agent ID count, a role's line does not."""
        snap = self.snapshot("product-manager")
        main = hooks_line(shifted(snap["time"], 3), None, None, path="docs/architecture.md")
        missing = {k: v for k, v in hooks_line(shifted(snap["time"], 4), None, None).items()
                   if k != "agent_id"}
        self.write_log([
            hooks_line(shifted(snap["time"], -60), None, None),
            main,
            hooks_line(shifted(snap["time"], 5), "troy-pstack:troy-developer", "a1"),
            missing,
        ])
        report = self.report_of(self.check(snap["run"]), 0)
        self.assertEqual(report["hooks_log"], [main, missing])


if __name__ == "__main__":
    unittest.main()
