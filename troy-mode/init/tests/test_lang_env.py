"""Environment group (F06 design 5.4, D51): mamba, the series environment, and the lock.

A fake mamba records every call (its arguments, working folder, and
UV_LINK_MODE) and writes the lock that `uv pip compile -o` names. No test
runs the real mamba, uses the network, or creates an environment.
"""

import os
import shutil
import unittest

from init_helpers import PROJECT, InitCase, changed_paths, new_dir, shared_plugin
from lang_helpers import (
    FAKE_LOCK, LIST_ARGS, LOCKS, FakeMamba, compile_args, create_args, env_list, git_only_path,
    install_args, lang_actions, lang_project, lang_stage, masked, run_lang, same_path,
    shared_lang_project,
)

PY_LOCK = LOCKS["python"]
CPP_LOCK = LOCKS["cpp"]
NAMED = ["-n", PROJECT]
PREFIXED = ["-p", "<prefix>"]


class EnvCase(InitCase):
    """Checks shared by the environment tests."""

    def assert_commands(self, report: dict, fake: FakeMamba, expected: list,
                        prefix=None) -> None:
        """The report's commands start with the fake's path and match the expected arguments."""
        commands = report["environment"]["commands"]
        for command in commands:
            self.assertTrue(os.path.samefile(command[0], fake.path), command)
        self.assertEqual([masked(command[1:], prefix) for command in commands], expected)

    def assert_calls(self, fake: FakeMamba, expected: list, prefix=None) -> None:
        """The fake saw exactly the expected calls, in order."""
        self.assertEqual([masked(argv, prefix) for argv in fake.argvs()], expected)


class EnvNamedExistsTest(EnvCase):
    """A named environment that env list already shows: no create (design 5.4 step 1)."""

    @classmethod
    def setUpClass(cls):
        """Runs lang python once with the fake first on the PATH."""
        cls.plugin = shared_plugin(hooks=True)
        cls.fake = FakeMamba(envs=env_list("other", PROJECT))
        cls.project = lang_project(cls.plugin)
        cls.before = cls.project.snapshot()
        env = {**cls.fake.path_env(), "UV_LINK_MODE": "hardlink", "FAKE_MAMBA_MARKER": "passed"}
        cls.out = run_lang(cls.project, cls.plugin, "python", no_env=False, env_extra=env)
        cls.after = cls.project.snapshot()
        cls.expected = [LIST_ARGS, compile_args("python", NAMED, ["pyproject.toml"]),
                        install_args("python", NAMED)]

    def test_env_lists_compiles_and_installs_without_creating(self):
        """The calls are env list, the compile, and the install from the lock."""
        self.report_of(self.out, 0)
        self.assert_calls(self.fake, self.expected)

    def test_env_report_names_the_commands_it_ran(self):
        """environment names the environment, says it exists, and lists each full argv."""
        environment = self.report_of(self.out, 0)["environment"]
        self.assertEqual({key: environment[key] for key in
                          ("name", "prefix", "series", "lock", "skipped", "exists")},
                         {"name": PROJECT, "prefix": None, "series": ["."], "lock": PY_LOCK,
                          "skipped": False, "exists": True})
        self.assert_commands(self.report_of(self.out, 0), self.fake, self.expected)

    def test_env_commands_run_in_the_project_with_uv_link_mode_copy(self):
        """Every call runs in the project root, with UV_LINK_MODE=copy and the rest passed on."""
        self.report_of(self.out, 0)
        calls = self.fake.calls()
        self.assertEqual(len(calls), 3)
        for call in calls:
            with self.subTest(argv=call["argv"]):
                self.assertTrue(same_path(call["cwd"], self.project.root), call["cwd"])
                self.assertEqual(call["uv_link_mode"], "copy")
                self.assertEqual(call["marker"], "passed")

    def test_env_writes_the_project_files_before_compiling(self):
        """environment.yml and pyproject.toml exist when the compile runs."""
        self.report_of(self.out, 0)
        compiles = [call for call in self.fake.calls() if "compile" in call["argv"]]
        self.assertEqual(len(compiles), 1)
        self.assertLessEqual({"environment.yml", "pyproject.toml"}, set(compiles[0]["present"]))

    def test_env_keeps_the_compiled_lock_and_stages_it(self):
        """The lock uv wrote stays, has action create, and is staged with the other files."""
        report = self.report_of(self.out, 0)
        self.assertEqual(self.project.read(PY_LOCK), FAKE_LOCK)
        self.assertEqual(self.actions_of(report), lang_actions("python", lock=True))
        self.assertEqual(report["stage"], lang_stage("python", lock=True))
        self.assertEqual(changed_paths(self.before, self.after), lang_stage("python", lock=True))


class EnvNamedMissingTest(EnvCase):
    """A named environment env list does not show is created, here for C/C++."""

    @classmethod
    def setUpClass(cls):
        """Runs lang cpp once with --mamba; env list shows only look-alike environments."""
        cls.plugin = shared_plugin(hooks=True)
        root = new_dir("conda")
        envs = [str(root), str(root / "envs" / f"{PROJECT}-old"),
                str(root / PROJECT / "envs" / "base")]
        cls.fake = FakeMamba(envs=envs)
        cls.project = lang_project(cls.plugin)
        cls.out = run_lang(cls.project, cls.plugin, "cpp", "--mamba", str(cls.fake.path),
                           no_env=False)
        cls.expected = [LIST_ARGS, create_args(NAMED),
                        compile_args("cpp", NAMED, ["requirements-tools.in"]),
                        install_args("cpp", NAMED)]

    def test_env_creates_a_missing_environment_before_compiling(self):
        """Only an exact last folder name counts, so the environment is created first."""
        self.report_of(self.out, 0)
        self.assert_calls(self.fake, self.expected)

    def test_env_creates_from_the_written_environment_file(self):
        """environment.yml and requirements-tools.in exist when create and compile run."""
        self.report_of(self.out, 0)
        for call in self.fake.calls()[1:3]:
            with self.subTest(argv=call["argv"]):
                self.assertLessEqual({"environment.yml", "requirements-tools.in"},
                                     set(call["present"]))

    def test_env_report_says_the_environment_did_not_exist(self):
        """exists is false, and the commands are the four the step ran."""
        report = self.report_of(self.out, 0)
        self.assertIs(report["environment"]["exists"], False)
        self.assertEqual(report["environment"]["lock"], CPP_LOCK)
        self.assert_commands(report, self.fake, self.expected)

    def test_env_keeps_the_cpp_lock_and_stages_it(self):
        """requirements-tools.lock holds what uv wrote and is staged."""
        report = self.report_of(self.out, 0)
        self.assertEqual(self.project.read(CPP_LOCK), FAKE_LOCK)
        self.assertEqual(self.actions_of(report), lang_actions("cpp", lock=True))
        self.assertEqual(report["stage"], lang_stage("cpp", lock=True))


class EnvPrefixTest(EnvCase):
    """--env-prefix: the environment exists when <prefix>/conda-meta is a folder."""

    @classmethod
    def setUpClass(cls):
        """Runs lang python twice in one project: prefix present, then prefix missing."""
        cls.plugin = shared_plugin(hooks=True)
        cls.fake = FakeMamba(envs=env_list(PROJECT))
        cls.present = new_dir("prefix") / "env"
        (cls.present / "conda-meta").mkdir(parents=True)
        cls.missing = new_dir("prefix") / "env"
        cls.runs = {}
        for name, prefix in (("present", cls.present), ("missing", cls.missing)):
            cls.fake.clear()
            out = run_lang(shared_lang_project(cls.plugin), cls.plugin, "python", "--mamba",
                           str(cls.fake.path), "--env-prefix", str(prefix), no_env=False)
            cls.runs[name] = (out, cls.fake.argvs())

    def test_env_prefix_with_conda_meta_is_not_created(self):
        """No env list and no create: only the compile and the install, with -p."""
        out, argvs = self.runs["present"]
        self.report_of(out, 0)
        self.assertEqual([masked(argv, self.present) for argv in argvs],
                         [compile_args("python", PREFIXED, ["pyproject.toml"]),
                          install_args("python", PREFIXED)])

    def test_env_prefix_without_conda_meta_is_created(self):
        """A prefix without conda-meta is created with -p, then compiled and installed."""
        out, argvs = self.runs["missing"]
        self.report_of(out, 0)
        self.assertEqual([masked(argv, self.missing) for argv in argvs],
                         [create_args(PREFIXED), compile_args("python", PREFIXED,
                                                              ["pyproject.toml"]),
                          install_args("python", PREFIXED)])

    def test_env_prefix_report_names_the_absolute_prefix(self):
        """prefix is the absolute path, and exists follows conda-meta."""
        for name, prefix, exists in (("present", self.present, True),
                                     ("missing", self.missing, False)):
            with self.subTest(prefix=name):
                environment = self.report_of(self.runs[name][0], 0)["environment"]
                self.assertTrue(os.path.isabs(environment["prefix"]), environment["prefix"])
                self.assertTrue(same_path(environment["prefix"], prefix), environment["prefix"])
                self.assertIs(environment["exists"], exists)
                self.assertIs(environment["skipped"], False)


class EnvSeriesTest(EnvCase):
    """The lock is compiled from every series member's manifest, in series order."""

    @classmethod
    def setUpClass(cls):
        """Runs lang python, then lang cpp, in one project with a series."""
        cls.plugin = shared_plugin(hooks=True)
        cls.fake = FakeMamba(envs=env_list(PROJECT, "series-env"))
        cls.runs = {}
        options = {"python": ["--series", "../core", "--series", "../ui/"],
                   "cpp": ["--series", ".", "--series", "../core", "--environment", "series-env"]}
        for lang, extra in options.items():
            cls.fake.clear()
            out = run_lang(shared_lang_project(cls.plugin), cls.plugin, lang, *extra,
                           no_env=False, env_extra=cls.fake.path_env())
            cls.runs[lang] = (out, cls.fake.argvs())

    def test_env_python_compiles_every_member_and_this_project_last(self):
        """The members' pyproject.toml files come first, with "/", then this project's."""
        out, argvs = self.runs["python"]
        self.report_of(out, 0)
        manifests = ["../core/pyproject.toml", "../ui/pyproject.toml", "pyproject.toml"]
        self.assertEqual(argvs, [LIST_ARGS, compile_args("python", NAMED, manifests),
                                 install_args("python", NAMED)])

    def test_env_cpp_compiles_the_members_in_the_order_given(self):
        """With "." first, this project's requirements-tools.in comes first."""
        out, argvs = self.runs["cpp"]
        self.report_of(out, 0)
        target = ["-n", "series-env"]
        manifests = ["requirements-tools.in", "../core/requirements-tools.in"]
        self.assertEqual(argvs, [LIST_ARGS, compile_args("cpp", target, manifests),
                                 install_args("cpp", target)])

    def test_env_report_lists_the_series(self):
        """environment.series holds the members with this project's place."""
        python = self.report_of(self.runs["python"][0], 0)["environment"]
        cpp = self.report_of(self.runs["cpp"][0], 0)["environment"]
        self.assertEqual(python["series"][0], "../core")
        self.assertEqual(python["series"][-1], ".")
        self.assertEqual(len(python["series"]), 3)
        self.assertEqual((cpp["series"], cpp["name"]), ([".", "../core"], "series-env"))


class EnvNoEnvTest(EnvCase):
    """--no-env runs no mamba command, even with mamba on the PATH and in MAMBA_EXE."""

    def test_no_env_runs_no_mamba_command(self):
        """The fake sees no call, and the report says the environment was skipped."""
        plugin = shared_plugin(hooks=True)
        fake = FakeMamba(envs=env_list(PROJECT))
        project = shared_lang_project(plugin)
        env = {**fake.path_env(), "MAMBA_EXE": str(fake.path)}
        report = self.report_of(run_lang(project, plugin, "python", env_extra=env), 0)
        self.assertEqual(fake.calls(), [])
        self.assertEqual(report["environment"]["commands"], [])
        self.assertIs(report["environment"]["skipped"], True)
        self.assertIsNone(report["environment"]["exists"])
        self.assertNotIn(PY_LOCK, report["stage"])
        self.assertFalse((project.root / PY_LOCK).exists())


class EnvFailureTest(EnvCase):
    """A failing mamba command exits 2 and puts the project back as it was (interface note)."""

    def test_failing_command_exits_2_and_restores_the_project(self):
        """Each failing call stops the step there, names it, and leaves no change behind."""
        plugin = shared_plugin(hooks=True)
        fake = FakeMamba()
        cases = {
            "list": (["list"], ("list",)),
            "create": (["list", "create"], ("create",)),
            "compile": (["list", "create", "compile"], ("compile",)),
            "install": (["list", "create", "compile", "install"], ("install",)),
            "no lock": (["list", "create", "compile"], ("compile", PY_LOCK)),
        }
        for case, (kinds, names) in cases.items():
            with self.subTest(case=case):
                fake.configure(envs=env_list("other"), fail=None if case == "no lock" else case,
                               no_lock=case == "no lock")
                fake.clear()
                project = shared_lang_project(plugin)
                before = project.snapshot()
                out = run_lang(project, plugin, "python", "--mamba", str(fake.path),
                               no_env=False)
                after = project.snapshot()
                self.assertEqual(out.code, 2, out.describe())
                self.assertTrue(any(name in out.stderr for name in names), out.stderr)
                self.assertEqual(fake.kinds(), kinds)
                self.assert_unchanged(before, after)


class EnvMambaLookupTest(EnvCase):
    """mamba comes from --mamba, else the PATH, else $MAMBA_EXE (design 5.4)."""

    @classmethod
    def setUpClass(cls):
        """Uses the shared set-up project, reset before each run."""
        cls.plugin = shared_plugin(hooks=True)
        cls.envs = env_list(PROJECT)

    def run_with(self, *extra: str, env_extra=None) -> dict:
        """Resets the shared project, runs lang python without --no-env, and returns the report."""
        out = run_lang(shared_lang_project(self.plugin), self.plugin, "python", *extra,
                       no_env=False, env_extra=env_extra)
        return self.report_of(out, 0)

    def test_mamba_option_wins_over_path_and_mamba_exe(self):
        """--mamba is used though another mamba is first on the PATH and in MAMBA_EXE."""
        fake, decoy = FakeMamba(envs=self.envs), FakeMamba(envs=self.envs)
        report = self.run_with("--mamba", str(fake.path),
                               env_extra={**decoy.path_env(), "MAMBA_EXE": str(decoy.path)})
        self.assertEqual(decoy.calls(), [])
        self.assertEqual(len(fake.calls()), 3)
        self.assertTrue(os.path.samefile(report["environment"]["commands"][0][0], fake.path))

    def test_path_wins_over_mamba_exe(self):
        """Without --mamba, the mamba first on the PATH is used, not MAMBA_EXE."""
        fake, decoy = FakeMamba(envs=self.envs), FakeMamba(envs=self.envs)
        report = self.run_with(env_extra={**fake.path_env(), "MAMBA_EXE": str(decoy.path)})
        self.assertEqual(decoy.calls(), [])
        self.assertEqual(len(fake.calls()), 3)
        self.assertTrue(os.path.samefile(report["environment"]["commands"][0][0], fake.path))

    def test_mamba_exe_is_used_when_the_path_has_no_mamba(self):
        """With no mamba on the PATH, $MAMBA_EXE is used."""
        folder = git_only_path()
        if shutil.which("mamba", path=folder):
            self.skipTest(f"{folder} holds a mamba")
        fake = FakeMamba(envs=self.envs)
        report = self.run_with(env_extra={"PATH": folder, "MAMBA_EXE": str(fake.path)})
        self.assertEqual(len(fake.calls()), 3)
        self.assertTrue(os.path.samefile(report["environment"]["commands"][0][0], fake.path))


class EnvDryRunTest(EnvCase):
    """A dry run plans the environment's commands but runs no create and no run."""

    def test_env_dry_run_plans_compile_and_install_and_changes_nothing(self):
        """The plan lists the compile and the install; only env list may run."""
        plugin = shared_plugin(hooks=True)
        fake = FakeMamba(envs=env_list(PROJECT))
        project = shared_lang_project(plugin)
        before = project.snapshot()
        out = run_lang(project, plugin, "python", "--dry-run", no_env=False,
                       env_extra=fake.path_env())
        report = self.report_of(out, 0)
        self.assert_unchanged(before, project.snapshot())
        self.assertLessEqual(set(fake.kinds()), {"list"})
        planned = [command[1:] for command in report["environment"]["commands"]]
        self.assertIn(compile_args("python", NAMED, ["pyproject.toml"]), planned)
        self.assertIn(install_args("python", NAMED), planned)
        self.assertIn(PY_LOCK, report["stage"])
        self.assertEqual(self.actions_of(report)[PY_LOCK], "create")


if __name__ == "__main__":
    unittest.main()
