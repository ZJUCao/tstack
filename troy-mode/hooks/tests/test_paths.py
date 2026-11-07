"""Paths group (F05 design 5.2, D42, and 13.1).

Each role against each path class and pattern, ignored paths, the .git
folder, paths outside the repository (temp folder, scratchpad, home folder),
path forms (backslashes, drive letter case, Git Bash forms, ..), and the
config read from HEAD.
"""

import os
import unittest
from pathlib import Path

from hook_helpers import (
    CONFIG_PATH, CR, DEV, EXPLORE, FOO, GP, HOOK_TEMP, IS_WINDOWS, OTHER_TYPES, PAD,
    PACK_DEPENDENCIES, ROLE_NAMES, SCRATCH, SYSTEM_TEMP, TE, HookTestCase, Project,
    git_bash_form, home_pad, home_probe, make_config, other, role, run_many, start_call,
    write_call,
)

A, I, T, D, E = "architect", "interface-designer", "test-manager", "developer", "test-engineer"

# (repository path, its troy-check class, the roles whose scope holds it).
# Classes come from troy-check's built-in [paths] plus the Python pack's
# (hook_helpers.make_config). The roles come from F04 design section 3.
PATH_TABLE = (
    ("src/pkg/app.py", "source", {D}),
    ("src/pkg/new_module.py", "source", {D}),
    ("scripts/release.sh", "source", {D}),
    ("Makefile", "source", {D}),
    ("tests/test_app.py", "tests", {E}),
    ("tests/data/sample.json", "tests", {E}),
    ("test/helpers.py", "tests", {E}),
    ("src/pkg/test_inline.py", "tests", {E}),
    ("src/pkg/inline_test.py", "tests", {E}),
    ("src/conftest.py", "tests", {E}),
    ("pyproject.toml", "dependencies", {D, E}),
    ("requirements-dev.lock", "dependencies", {D, E}),
    ("environment.yml", "dependencies", {D, E}),
    ("docs/architecture.md", "docs", {A}),
    ("docs/architecture.zh-CN.md", "docs", {A}),
    ("docs/architecture/overview.md", "docs", set()),
    ("archive/docs/architecture.md", "docs", set()),
    ("docs/adr/0001-storage.md", "docs", {A}),
    ("docs/adr/2026/0002-cache.md", "docs", {A}),
    ("docs/features/F01/design.md", "docs", {A, I}),
    ("docs/features/F01/design.zh-CN.md", "docs", {A, I}),
    ("docs/features/F01/notes/design.md", "docs", set()),
    ("docs/features/F01/test-plan.md", "docs", {T}),
    ("docs/features/F01/test-plan.zh-CN.md", "docs", {T}),
    ("docs/versions/v1.0/test-plan.md", "docs", {T}),
    ("docs/test-plan.md", "docs", set()),
    ("docs/requirements.md", "docs", set()),
    ("README.md", "docs", set()),
    ("src/pkg/README.md", "docs", set()),
    ("LICENSE", "docs", set()),
    ("docs/rules.md", "config", set()),
    ("docs/rules.zh-CN.md", "config", set()),
    (".troy-mode/config.toml", "config", set()),
    (".troy-mode/progress.md", "config", set()),
    (".github/workflows/ci.yml", "config", set()),
    (".gitignore", "config", set()),
    (".gitattributes", "config", set()),
)

# One row per class and per role pattern, for the subagents that are not roles.
OTHER_ROWS = ("src/pkg/app.py", "tests/test_app.py", "pyproject.toml", "docs/architecture.md",
              "docs/adr/0001-storage.md", "docs/features/F01/design.md",
              "docs/features/F01/test-plan.md", "docs/versions/v1.0/test-plan.md", "README.md",
              ".troy-mode/config.toml")


class RoleMatrixTests(HookTestCase):
    """Each role and each other subagent against each path class and pattern."""

    @classmethod
    def setUpClass(cls):
        """Builds one project and starts each role once."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        run_many([start_call(cls.project, role(name)) for name in ROLE_NAMES])

    def test_each_role_against_each_path_class_and_pattern(self):
        """A role may write exactly the paths its scope holds (F04 section 3, R08).

        Planted bug caught: the Developer's scope with the tests class (13.2),
        at tests/test_app.py and the other tests rows.
        """
        cases = [(name, row) for name in ROLE_NAMES for row in PATH_TABLE]
        outs = run_many([write_call(self.project, role(name), self.project.path(row[0]))
                         for name, row in cases])
        for (name, (rel, cls, allowed)), out in zip(cases, outs):
            with self.subTest(role=name, path=rel):
                if name in allowed:
                    self.assert_silent(out)
                else:
                    self.assert_denied(out, rel, cls, "needs-answer")

    def test_table_has_allowed_and_refused_rows_for_every_role(self):
        """Every role but the Code Reviewer has a silent row, and every role a refused one."""
        for name in ROLE_NAMES:
            allowed = [rel for rel, _, roles in PATH_TABLE if name in roles]
            refused = [rel for rel, _, roles in PATH_TABLE if name not in roles]
            self.assertTrue(refused, name)
            self.assertEqual(name == "code-reviewer", not allowed, name)

    def test_other_subagents_against_each_class(self):
        """Subagents that are not roles may write no tracked or trackable path."""
        callers = [other(t) for t in OTHER_TYPES]
        classes = {rel: cls for rel, cls, _ in PATH_TABLE}
        cases = [(c, rel) for c in callers for rel in OTHER_ROWS]
        outs = run_many([write_call(self.project, c, self.project.path(rel)) for c, rel in cases])
        for (caller, rel), out in zip(cases, outs):
            with self.subTest(agent_type=caller.agent_type, path=rel):
                self.assert_denied(out, rel, classes[rel], "needs-answer")

    def test_edit_and_notebook_edit_are_checked_like_write(self):
        """Edit uses file_path and NotebookEdit notebook_path; both get the same scope."""
        cases = (("Edit", "tests/test_app.py", False), ("Edit", "src/pkg/app.py", True),
                 ("NotebookEdit", "tests/explore.ipynb", False),
                 ("NotebookEdit", "src/pkg/explore.ipynb", True))
        for tool, rel, allowed in cases:
            with self.subTest(tool=tool, path=rel):
                out = write_call(self.project, DEV, self.project.path(rel), tool=tool).run()
                if allowed:
                    self.assert_silent(out)
                else:
                    self.assert_denied(out, rel, "tests", "needs-answer")

    def test_utf8_path_is_named_in_the_reason(self):
        """A path with Chinese letters is read as UTF-8 and named back unchanged."""
        rel = "tests/数据/test_统计.py"
        out = write_call(self.project, DEV, self.project.path(rel)).run()
        self.assert_denied(out, rel, "tests", "needs-answer")
        self.assert_silent(write_call(self.project, DEV, self.project.path("src/统计.py")).run())


class IgnoredAndGitFolderTests(HookTestCase):
    """Ignored paths are allowed for every subagent; the .git folder is refused."""

    @classmethod
    def setUpClass(cls):
        """Builds one project whose .gitignore ignores reports/, build/, and caches."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        run_many([start_call(cls.project, c) for c in (DEV, TE, CR)])

    def test_ignored_paths_are_allowed(self):
        """reports/, build/, __pycache__, and tests/.cache/ are allowed (F04 common rule 5).

        Planted bug caught: no ignore check (13.2). The Code Reviewer and
        general-purpose may change nothing else, so without git check-ignore
        these writes would be refused.
        """
        paths = ("reports/junit.xml", "build/lib/out.so", "src/pkg/__pycache__/app.cpython-313.pyc",
                 "tests/.cache/state.json")
        cases = [(c, rel) for c in (DEV, CR, GP, EXPLORE, FOO) for rel in paths]
        outs = run_many([write_call(self.project, c, self.project.path(rel)) for c, rel in cases])
        for (caller, rel), out in zip(cases, outs):
            with self.subTest(caller=caller.label, path=rel):
                self.assert_silent(out)

    def test_tracked_paths_beside_the_ignored_ones_are_refused(self):
        """Pair: the same callers are refused a tracked path next to an ignored one."""
        cases = ((DEV, "tests/test_app.py", "tests"), (CR, "src/pkg/app.py", "source"),
                 (GP, "src/pkg/app.py", "source"), (TE, "src/pkg/app.py", "source"))
        for caller, rel, cls in cases:
            with self.subTest(caller=caller.label, path=rel):
                out = write_call(self.project, caller, self.project.path(rel)).run()
                self.assert_denied(out, rel, cls, "needs-answer")

    def test_git_folder_is_refused(self):
        """A path in .git is refused for every subagent, the role records included."""
        paths = (".git/config", ".git/hooks/pre-commit", ".git/info/exclude",
                 f".git/troy-mode/agents/{DEV.agent_id}.json", ".git/troy-mode/hooks.log")
        cases = [(c, rel) for c in (DEV, TE, GP) for rel in paths]
        outs = run_many([write_call(self.project, c, self.project.path(rel)) for c, rel in cases])
        for (caller, rel), out in zip(cases, outs):
            with self.subTest(caller=caller.label, path=rel):
                self.assert_denied(out)


class OutsideRepositoryTests(HookTestCase):
    """Paths outside the repository: temp folder and scratchpad allowed, else refused (D42)."""

    @classmethod
    def setUpClass(cls):
        """Builds one project."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        start_call(cls.project, DEV).run()

    def write(self, path, caller=DEV, **kwargs):
        """Runs a Write PreToolUse call for a path given as text."""
        return write_call(self.project, caller, path, **kwargs).run()

    def test_temp_folder_is_allowed(self):
        """A file in the hook's temp folder is allowed for a role and another subagent."""
        target = HOOK_TEMP / "copy" / "src" / "pkg" / "app.py"
        self.assert_silent(self.write(str(target)))
        self.assert_silent(self.write(str(target), caller=GP))
        self.assert_silent(self.write(str(HOOK_TEMP / "notes.txt"), caller=CR))

    def test_home_folder_is_refused(self):
        """Pair: a file in the home folder, outside every temp folder, is refused."""
        probe = home_probe()
        if probe is None:
            self.skipTest("the home folder lies in a temp folder")
        out = self.write(str(probe))
        self.assert_denied(out, str(probe), "needs-answer")
        self.assert_denied(self.write(str(probe), caller=GP), "needs-answer")

    @unittest.skipUnless(IS_WINDOWS, "a sibling of the temp folder is in /tmp on Linux")
    def test_sibling_of_temp_folder_is_refused_on_windows(self):
        """<temp>-other shares the temp folder's name as a prefix and is refused.

        Planted bug caught: a temp folder test that accepts /tmp-other (13.2),
        in its Windows form: a prefix test on the temp folder's path.
        """
        sibling = Path(str(HOOK_TEMP) + "-other") / "notes.txt"
        self.assert_denied(self.write(str(sibling)), str(sibling), "needs-answer")
        self.assert_silent(self.write(str(HOOK_TEMP / "notes.txt")))

    def test_tmp_other_is_refused(self):
        """/tmp-other is not /tmp: refused, while /tmp itself is allowed.

        On Windows these are Git Bash forms; the hook's temp variables are the
        system temp folder, where Git Bash's /tmp points (convention 7), and
        /tmp-other is no temp folder under any reading.
        Planted bug caught: a temp folder test that accepts /tmp-other (13.2).
        """
        def write(path):
            return write_call(self.project, DEV, path, temp=SYSTEM_TEMP).run()

        named = () if IS_WINDOWS else ("/tmp-other/notes.txt",)
        self.assert_denied(write("/tmp-other/notes.txt"), *named, "needs-answer")
        self.assert_denied(write("/tmpfiles/notes.txt"), "needs-answer")
        self.assert_silent(write("/tmp/troyhook-probe/notes.txt"))

    def test_scratchpad_is_allowed(self):
        """The session's scratchpad is allowed, and refused when the input names no scratchpad."""
        pad = home_pad()
        if pad is None:
            self.skipTest("the home folder lies in a temp folder")
        target = pad / "copy" / "notes.txt"
        self.assert_silent(self.write(str(target), scratchpad=pad))
        self.assert_denied(self.write(str(target)), "needs-answer")

    def test_sibling_of_scratchpad_is_refused(self):
        """<scratchpad>-other is outside the scratchpad."""
        pad = home_pad()
        if pad is None:
            self.skipTest("the home folder lies in a temp folder")
        sibling = Path(str(pad) + "-other") / "notes.txt"
        self.assert_denied(self.write(str(sibling), scratchpad=pad), "needs-answer")
        self.assert_silent(self.write(str(pad / "notes.txt"), scratchpad=pad))

    def test_real_scratchpad_folder_is_allowed(self):
        """A scratchpad folder that exists, outside the hook's temp folder, is allowed."""
        self.assert_silent(self.write(str(PAD / "notes.txt"), scratchpad=PAD))

    @unittest.skipUnless(IS_WINDOWS, "PAD lies in /tmp on Linux")
    def test_real_scratchpad_folder_needs_the_input_on_windows(self):
        """Pair: without scratchpad_dir the same folder is refused on Windows."""
        self.assert_denied(self.write(str(PAD / "notes.txt")), "needs-answer")

    def test_dotdot_out_of_the_repository_into_temp(self):
        """<repo>/../../hooktemp/x resolves into the temp folder and is allowed."""
        rel = os.path.relpath(HOOK_TEMP, self.project.root)
        target = os.path.join(str(self.project.root), rel, "notes.txt")
        self.assertIn("..", target)
        self.assert_silent(self.write(target))


class PathFormTests(HookTestCase):
    """Relative paths, .., links, and Windows forms are normalized (design 5.2 step 1)."""

    @classmethod
    def setUpClass(cls):
        """Builds one project and starts the Developer."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        start_call(cls.project, DEV).run()

    def check(self, path, allowed, cwd=None, cls="tests", rel="tests/test_app.py", **kwargs):
        """Asserts the Developer's Write of a path is silent or refused as a tests path."""
        out = write_call(self.project, DEV, path, cwd=cwd, **kwargs).run()
        if allowed:
            self.assert_silent(out, f"{path}:")
        else:
            self.assert_denied(out, rel, cls, "needs-answer", msg=f"{path}:")

    def test_dotdot_inside_the_repository(self):
        """src/../tests/x is a tests path; tests/../src/x is a source path."""
        root = str(self.project.root)
        self.check(os.path.join(root, "src", "..", "tests", "test_app.py"), False)
        self.check(os.path.join(root, "tests", "..", "src", "pkg", "app.py"), True)

    def test_relative_path_is_made_absolute_against_cwd(self):
        """With cwd in src, ../tests/test_app.py is refused and pkg/app.py is allowed."""
        cwd = self.project.path("src")
        self.check("../tests/test_app.py", False, cwd=cwd)
        self.check("pkg/app.py", True, cwd=cwd)

    def test_link_into_tests_is_resolved(self):
        """A link in src that points at tests/ is resolved before the class is found."""
        link = self.project.path("src/tests_link")
        try:
            os.symlink(self.project.path("tests"), link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"cannot make a link here: {exc}")
        self.addCleanup(link.unlink)
        # The name matches no tests pattern, so only resolving the link makes it a tests path.
        self.check(str(link / "data_linked.json"), False, rel="tests/data_linked.json")
        self.check(str(self.project.path("src/pkg/app.py")), True)

    @unittest.skipUnless(IS_WINDOWS, "Windows path forms")
    def test_backslashes_and_forward_slashes(self):
        """C:\\...\\tests\\x and C:/.../tests/x are the same path."""
        root = str(self.project.root)
        self.check(root + "\\tests\\test_app.py", False)
        self.check(root.replace("\\", "/") + "/tests/test_app.py", False)
        self.check(root + "\\src\\pkg\\app.py", True)
        self.check(root.replace("\\", "/") + "/src/pkg/app.py", True)
        self.check(root + "/src\\pkg/app.py", True)

    @unittest.skipUnless(IS_WINDOWS, "Windows drive letters")
    def test_drive_letter_case(self):
        """c:\\... and C:\\... are the same repository."""
        root = str(self.project.root)
        lower = root[0].lower() + root[1:]
        upper = root[0].upper() + root[1:]
        for base in (lower, upper):
            with self.subTest(base=base[:3]):
                self.check(base + "\\tests\\test_app.py", False)
                self.check(base + "\\src\\pkg\\app.py", True)

    @unittest.skipUnless(IS_WINDOWS, "Windows compares paths without case")
    def test_case_differences_in_the_repository_path(self):
        """An upper-case repository path is still inside the repository."""
        root = str(self.project.root).upper()
        self.check(root + "\\tests\\test_app.py", False)
        self.check(root + "\\src\\pkg\\app.py", True)

    @unittest.skipUnless(IS_WINDOWS, "Windows compares paths without case")
    def test_case_change_does_not_hide_an_existing_test_file(self):
        """TESTS\\TEST_APP.PY names the existing tests/test_app.py and is refused."""
        out = write_call(self.project, DEV, str(self.project.root) + "\\TESTS\\TEST_APP.PY").run()
        self.assert_denied(out, "needs-answer")

    @unittest.skipUnless(IS_WINDOWS, "Git Bash path forms")
    def test_git_bash_form_inside_the_repository(self):
        """/c/Users/.../repo/tests/x is the repository's tests path."""
        base = git_bash_form(self.project.root)
        self.check(base + "/tests/test_app.py", False)
        self.check(base + "/src/pkg/app.py", True)

    @unittest.skipUnless(IS_WINDOWS, "Git Bash path forms")
    def test_git_bash_form_of_temp_and_home(self):
        """/c/.../hooktemp/x is the temp folder; the Git Bash form of home is refused."""
        out = write_call(self.project, DEV, git_bash_form(HOOK_TEMP) + "/notes.txt").run()
        self.assert_silent(out)
        probe = home_probe()
        if probe is not None:
            out = write_call(self.project, DEV, git_bash_form(probe)).run()
            self.assert_denied(out, "needs-answer")

    @unittest.skipUnless(IS_WINDOWS, "Git Bash /tmp")
    def test_git_bash_tmp_is_the_temp_folder(self):
        """/tmp/x in Git Bash is the user's temp folder, so it is allowed.

        The hook's temp variables are the system temp folder here, where Git
        Bash's /tmp points (convention 7).
        """
        out = write_call(self.project, DEV, "/tmp/troyhook-probe/notes.txt",
                         temp=SYSTEM_TEMP).run()
        self.assert_silent(out)

    @unittest.skipUnless(IS_WINDOWS, "Windows compares paths without case")
    def test_temp_folder_case_differences(self):
        """An upper-case temp folder path is still the temp folder."""
        out = write_call(self.project, DEV, str(HOOK_TEMP).upper() + "\\NOTES.TXT").run()
        self.assert_silent(out)


class ProjectInTempTests(HookTestCase):
    """A project that lies in the temp folder is judged by its write scope, not the temp rule.

    The hook's temp variables point at the project's parent folder, so on
    every platform the project and a scratch repository both lie in temp.
    Planted bug caught: a scratch repository test that accepts the project
    (13.2), here for paths; test_commands.ProjectInTempCommandTests covers git.
    """

    @classmethod
    def setUpClass(cls):
        """Builds a project inside a folder that serves as the temp folder."""
        cls.temp = SCRATCH / "projtemp-paths"
        cls.temp.mkdir(exist_ok=True)
        cls.project = Project(parent=cls.temp)
        cls.addClassCleanup(cls.project.close)
        start_call(cls.project, DEV).run()

    def write(self, caller, path):
        """Runs a Write call with the project's parent as temp folder."""
        return write_call(self.project, caller, path, temp=self.temp).run()

    def test_out_of_scope_path_in_a_project_in_temp_is_refused(self):
        """The Developer's test file and the Code Reviewer's source file stay refused."""
        self.assert_denied(self.write(DEV, self.project.path("tests/test_app.py")),
                           "tests/test_app.py", "tests", "needs-answer")
        self.assert_denied(self.write(CR, self.project.path("src/pkg/app.py")),
                           "src/pkg/app.py", "source", "needs-answer")
        self.assert_denied(self.write(DEV, self.project.path(".git/config")))
        self.assert_denied(self.write(DEV, self.project.path(CONFIG_PATH)), CONFIG_PATH,
                           "config")

    def test_in_scope_and_outside_paths_are_allowed(self):
        """Pair: the Developer's source file and a file beside the project in temp are silent."""
        self.assert_silent(self.write(DEV, self.project.path("src/pkg/app.py")))
        self.assert_silent(self.write(DEV, self.temp / "scratch-notes.txt"))


class ConfigFromHeadTests(HookTestCase):
    """The [paths] table is read from .troy-mode/config.toml as committed at HEAD."""

    WIDE = make_config(dependencies=PACK_DEPENDENCIES + ("tests/data/**",))

    def test_committed_pattern_is_used(self):
        """A committed dependencies pattern makes tests/data/x a dependencies path."""
        project = Project(config=self.WIDE)
        self.addCleanup(project.close)
        out = write_call(project, DEV, project.path("tests/data/fixture.json")).run()
        self.assert_silent(out)
        self.assert_silent(write_call(project, TE, project.path("tests/data/fixture.json")).run())

    def test_uncommitted_config_edit_does_not_widen_a_scope(self):
        """The same pattern only in the working tree leaves tests/data/x a tests path.

        Planted bug caught: the config read from the working tree (13.2).
        """
        project = Project()
        self.addCleanup(project.close)
        project.write(CONFIG_PATH, self.WIDE)
        out = write_call(project, DEV, project.path("tests/data/fixture.json")).run()
        self.assert_denied(out, "tests/data/fixture.json", "tests", "needs-answer")

    def test_staged_config_edit_does_not_widen_a_scope(self):
        """A staged but uncommitted edit is not HEAD either."""
        project = Project()
        self.addCleanup(project.close)
        project.write(CONFIG_PATH, self.WIDE)
        project.git("add", CONFIG_PATH)
        out = write_call(project, DEV, project.path("tests/data/fixture.json")).run()
        self.assert_denied(out, "tests/data/fixture.json", "tests", "needs-answer")

    def test_broken_working_tree_config_is_not_read(self):
        """An invalid config in the working tree only does not stop a role's call.

        Planted bug caught: the config read from the working tree (13.2).
        """
        project = Project()
        self.addCleanup(project.close)
        project.write(CONFIG_PATH, "[bogus]\nx = 1\n")
        self.assert_silent(write_call(project, DEV, project.path("src/pkg/app.py")).run())
        self.assert_denied(write_call(project, DEV, project.path("tests/test_app.py")).run(),
                           "tests/test_app.py", "tests")

    def test_invalid_committed_config_refuses_a_role(self):
        """An invalid config at HEAD refuses a role's write with the error (D39)."""
        project = Project(config="[bogus]\nx = 1\n")
        self.addCleanup(project.close)
        project.write(CONFIG_PATH, make_config())
        self.assert_error_refusal(write_call(project, DEV, project.path("src/pkg/app.py")).run())

    def test_pack_patterns_come_from_the_config(self):
        """Without the pack's [paths], src/pkg/test_inline.py and pyproject.toml are source."""
        project = Project(config=make_config(tests=(), dependencies=()))
        self.addCleanup(project.close)
        self.assert_silent(write_call(project, DEV, project.path("src/pkg/test_inline.py")).run())
        self.assert_denied(write_call(project, TE, project.path("src/pkg/test_inline.py")).run(),
                           "src/pkg/test_inline.py", "source")
        self.assert_denied(write_call(project, TE, project.path("pyproject.toml")).run(),
                           "pyproject.toml", "source")

    def test_missing_config_uses_built_in_paths(self):
        """With no config file, the built-in classes still apply (tests/** is tests)."""
        project = Project(config=None)
        self.addCleanup(project.close)
        self.assert_denied(write_call(project, DEV, project.path("tests/test_app.py")).run(),
                           "tests/test_app.py", "tests")
        self.assert_silent(write_call(project, DEV, project.path("src/pkg/app.py")).run())


if __name__ == "__main__":
    unittest.main()
