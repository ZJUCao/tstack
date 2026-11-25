"""The program, its environment, and safety (F12 design 5.4, 5.5, 15.1; note sections 5, 6).

Five projects of F02, each run once, side by side:

- ``env``: the user folders, the unset Python variables (set in the
  engine's own environment), the working folder, the run file's
  ``[environment]`` and ``$env:``, the environment first on ``PATH`` (a
  decoy ``envtool`` comes first on the engine's ``PATH``), the console
  script with this checkout's code, ``PYTHONPYCACHEPREFIX``, and standard
  input; the run changes nothing in the clone and deletes its scratch folder;
- ``elsewhere``: the environment's ``python`` finds the package in another
  checkout, so the code-location check fails;
- ``no environment``: no ``TROY_MODE_ENV_PREFIX`` and a ``mamba`` that fails;
- ``safety``: unmapped absolute paths in a command, a ``$env:`` line, a
  setup command, and ``[environment] set``; a failing setup; programs that
  are not found;
- ``dirty``: an untracked file, so nothing runs.

Planted bugs of design 15.2 caught here:

- "``PYTHONUTF8`` passed through": ``EnvTests.test_python_text_variables_are_removed``.
- "an unmapped absolute path run": ``SafetyTests.test_unmapped_path_in_a_command_is_not_run``.
"""

import json
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from flow_helpers import Fakes, new_dir, parallel, same_path
from realrun_helpers import (
    CONSOLE, PROGRAMS, PYTHON_VARIABLES, TABLE_LINES, FakeEnv, RealProject, RealRunCase,
    add_decoy, block, calls, command_of, commands_of, history, new_log, other_checkout,
    problems_of, project_files, run_file, run_file_path,
)

WINDOWS = os.name == "nt"
ENV = "docs/prototypes/F02-env.md"
HOMES = ["HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"]
HOMES += ["HOMEDRIVE+HOMEPATH"] if WINDOWS else ["XDG_CONFIG_HOME", "XDG_DATA_HOME",
                                                  "XDG_CACHE_HOME", "XDG_STATE_HOME"]
HOME_LINES = ["HOME: home", "USERPROFILE: home", "APPDATA: home/AppData/Roaming",
              "LOCALAPPDATA: home/AppData/Local"]
HOME_LINES += (["HOMEDRIVE+HOMEPATH: home"] if WINDOWS else
               ["XDG_CONFIG_HOME: home/.config", "XDG_DATA_HOME: home/.local/share",
                "XDG_CACHE_HOME: home/.cache", "XDG_STATE_HOME: home/.local/state"])
PYTHON_ENV = f"{CONSOLE} env " + " ".join(PYTHON_VARIABLES)
ENV_TEXT = (
    "# Environment\n\n## Home folders\n\n"
    + block(f"PS> {CONSOLE} homes " + " ".join(HOMES), *HOME_LINES)
    + "\n## Working folder\n\n"
    + block("PS> sample where .", "<scratch>" + os.sep + "home", "PS> sample where ..", "<scratch>")
    + "\n## Python variables\n\n"
    + block(f"PS> {PYTHON_ENV}", *[f"{name} is not set" for name in PYTHON_VARIABLES])
    + "\n## Run file variables\n\n"
    + block("PS> sample env MENU_LANG TROY_SAMPLE_GONE TROY_SAMPLE_KEPT",
            "MENU_LANG=zh", "TROY_SAMPLE_GONE is not set", "TROY_SAMPLE_KEPT=kept",
            'PS> $env:MENU_LANG = "en"', "PS> sample env MENU_LANG", "MENU_LANG=en")
    + "\n## Environment first\n\n" + block("PS> sample run envtool", "envtool from the environment")
    + "\n## Console script\n\n" + block(f"PS> {CONSOLE} table", *TABLE_LINES)
    + "\n## Cache\n\n"
    + block("PS> sample in-scratch PYTHONPYCACHEPREFIX",
            "PYTHONPYCACHEPREFIX: inside the scratch folder")
    + "\n## Standard input\n\n" + block("PS> sample stdin", "stdin: 0 bytes")
)
ENV_RUN = run_file('[environment]\nunset = ["TROY_SAMPLE_GONE"]\nset = { MENU_LANG = "zh" }')


def engine_variables() -> dict:
    """Variables the engine itself gets, which the commands must not see as they are."""
    found = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHONLEGACYWINDOWSSTDIO": "1",
             "PYTHONSTARTUP": str(new_dir("startup") / "startup.py"),
             "TROY_SAMPLE_GONE": "present", "TROY_SAMPLE_KEPT": "kept",
             "MENU_LANG": "from-the-engine"}
    if sys.prefix == sys.base_prefix:
        # Right for this Python, so the engine starts; the commands must not get it.
        found["PYTHONHOME"] = sys.base_prefix
    return found


WHERE = "docs/prototypes/F02-where.md"
WHERE_TEXT = ("# Where\n\n## Console\n\n" + block(f"PS> {CONSOLE} say console", "console")
              + "\n## Program\n\n" + block("PS> sample say program", "program"))

SAFETY = "docs/prototypes/F02-safety.md"
ENV_SET = "docs/prototypes/F02-env-set.md"
UNMAPPED = ["sample say D:\\Private\\menu", "sample say \\\\server\\share\\menu"]
SLASH = "sample say /srv/menu"
SAFETY_TEXT = (
    "# Safety\n\n## Mapped\n\n"
    + block("PS> sample write-in D:\\OneDrive\\menu note.txt hello",
            "PS> sample cat-in D:\\OneDrive\\menu note.txt", "hello")
    + "\n## Unmapped command\n\n"
    + block(*[x for typed in UNMAPPED for x in (f"PS> {typed}", typed.split(" ", 2)[2])],
            f"PS> {SLASH}", "/srv/menu", "PS> sample say after", "after")
    + "\n## Unmapped variable\n\n"
    + block('PS> $env:MENU_DATA = "D:\\Private\\data"', "PS> sample say still", "still")
    + "\n## Unmapped setup\n\n" + block("PS> sample say never", "never")
    + "\n## Setup fails\n\n" + block("PS> sample say skipped by setup", "skipped by setup")
    + "\n## Missing programs\n\n"
    + block("PS> menu say x", "x", "PS> gone say y", "y")
    + "\n## After\n\n" + block("PS> sample say fine", "fine")
)
SAFETY_RUN = (
    PROGRAMS + 'gone = "build/nothing"\n'
    + "\n[paths]\n'C:\\Users\\Troy' = '<home>'\n"
    + "'D:\\OneDrive\\menu' = '<scratch>\\OneDrive\\menu'\n"
    + "\n[start]\nmkdir = ['<scratch>\\OneDrive\\menu']\n"
    + '\n[sections."Unmapped setup"]\nstart = { setup = ["sample say E:\\\\Secret"] }\n'
    + '\n[sections."Setup fails"]\nstart = { setup = ["sample fail 3 setup broke"] }\n')
ENV_SET_TEXT = "# Environment table\n\n## Set\n\n" + block("PS> sample env MENU_HOME",
                                                            "MENU_HOME=D:\\Private")
ENV_SET_RUN = run_file("[environment]\nset = { MENU_HOME = 'D:\\Private' }")

DIRTY = "docs/prototypes/F02-dirty.md"

_RUNS: dict = {}


def runs() -> dict:
    """Builds the five projects and runs ``real-run --item F02`` on each, side by side, once.

    Returns:
        Each name mapped to ``(project, outcome, call log, status before the run)``.
    """
    if _RUNS:
        return _RUNS
    env_fakes = Fakes(fail=True)
    add_decoy(env_fakes)
    cases = {
        "env": ({ENV: ENV_TEXT, run_file_path(ENV): ENV_RUN}, (CONSOLE,), "default",
                engine_variables(), env_fakes),
        "elsewhere": ({WHERE: WHERE_TEXT, run_file_path(WHERE): run_file()}, (CONSOLE,),
                      FakeEnv(elsewhere=other_checkout()), None, None),
        "no environment": ({WHERE: WHERE_TEXT, run_file_path(WHERE): run_file()}, (CONSOLE,),
                           None, None, None),
        "safety": ({SAFETY: SAFETY_TEXT, run_file_path(SAFETY): SAFETY_RUN,
                    ENV_SET: ENV_SET_TEXT, run_file_path(ENV_SET): ENV_SET_RUN},
                   (CONSOLE, "menu"), "default", None, None),
        "dirty": ({DIRTY: "# Dirty\n\n## Say\n\n" + block("PS> sample say hi", "hi"),
                   run_file_path(DIRTY): run_file()}, (CONSOLE,), "default", None, None),
    }

    def run(name):
        """Builds one project and runs the engine with a call log."""
        files, consoles, env, extra, fakes = cases[name]
        rows = [(path.rsplit("/", 1)[1], "F02", path) for path in files if path.endswith(".md")]
        project = RealProject(history(project_files(rows=rows, files=files, consoles=consoles)))
        if name == "dirty":
            project.write("notes.txt", "not committed\n")
        before = project.all_status()
        log = new_log(name.replace(" ", "-"))
        kwargs = {} if env == "default" else {"env": env}
        out = project.real_run("--item", "F02", log=log, env_extra=extra, fakes=fakes, **kwargs)
        return project, out, log, before
    names = list(cases)
    _RUNS.update(zip(names, parallel(run, names)))
    return _RUNS


class EnvTests(RealRunCase):
    """What each command runs with (design 5.4; note section 6)."""

    @classmethod
    def setUpClass(cls):
        """Runs the five projects once."""
        cls.project, cls.out, cls.log, cls.before = runs()["env"]

    def setUp(self):
        """Every command matches."""
        self.report = self.real_report(self.out, 0)

    def cmd(self, typed: str) -> dict:
        """The one command entry with this typed line."""
        return command_of(self.report, ENV, typed)

    def test_user_folders_point_into_home(self):
        """HOME, USERPROFILE, APPDATA, LOCALAPPDATA, and HOMEDRIVE+HOMEPATH on Windows or the
        XDG folders elsewhere, all in the home folder, which is the working folder."""
        self.assert_command(self.cmd(f"{CONSOLE} homes " + " ".join(HOMES)), "matches",
                            real=HOME_LINES)

    def test_working_folder_is_home_in_the_scratch_folder(self):
        """The command runs in ``<scratch>/home``."""
        self.assert_command(self.cmd("sample where ."), "matches",
                            real=["<scratch>" + os.sep + "home"])
        self.assert_command(self.cmd("sample where .."), "matches", real=["<scratch>"])

    def test_python_text_variables_are_removed(self):
        """Planted bug "PYTHONUTF8 passed through": the engine has PYTHONUTF8,
        PYTHONIOENCODING, and the rest; no command sees them."""
        self.assert_command(self.cmd(PYTHON_ENV), "matches",
                            real=[f"{name} is not set" for name in PYTHON_VARIABLES])

    def test_environment_table_then_env_lines(self):
        """``unset`` removes, ``set`` adds over the engine's value, and ``$env:`` comes last;
        other variables pass through."""
        self.assert_command(self.cmd("sample env MENU_LANG TROY_SAMPLE_GONE TROY_SAMPLE_KEPT"),
                            "matches", real=["MENU_LANG=zh", "TROY_SAMPLE_GONE is not set",
                                             "TROY_SAMPLE_KEPT=kept"])
        self.assert_command(self.cmd("sample env MENU_LANG"), "matches", real=["MENU_LANG=en"])

    def test_environment_folders_come_first_on_path(self):
        """``envtool`` is found in the environment, not in the folder first on the engine's PATH."""
        self.assert_command(self.cmd("sample run envtool"), "matches",
                            real=["envtool from the environment"])

    def test_console_script_runs_this_checkouts_code(self):
        """The console script, from the environment, imports ``src/`` through PYTHONPATH."""
        self.assert_command(self.cmd(f"{CONSOLE} table"), "matches", kind="program",
                            real=list(TABLE_LINES))

    def test_cache_prefix_and_standard_input(self):
        """PYTHONPYCACHEPREFIX lies in the scratch folder; standard input is empty."""
        self.assert_command(self.cmd("sample in-scratch PYTHONPYCACHEPREFIX"), "matches")
        self.assert_command(self.cmd("sample stdin"), "matches", real=["stdin: 0 bytes"])

    def test_scratch_folder_is_temporary_and_deleted(self):
        """Commands ran in a ``home`` folder in the system's temporary folder, deleted after."""
        temp = os.path.normcase(os.path.realpath(tempfile.gettempdir()))
        folders = {call["cwd"] for call in calls(self.log)}
        self.assertNotEqual(folders, set())
        for folder in folders:
            with self.subTest(folder=folder):
                self.assertEqual(Path(folder).name, "home")
                real = os.path.normcase(os.path.realpath(folder))
                self.assertTrue(real.startswith(temp + os.sep), (real, temp))
                self.assertFalse(Path(folder).exists())
        self.assertIsNone(self.report["scratch"])

    def test_nothing_changes_in_the_clone(self):
        """``git status`` with ignored files is the same; the reports are in the git folder."""
        self.assertEqual(self.project.all_status(), self.before)
        folder = self.project.report_folder()
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         ["real-run-F02-1.json", "real-run-F02-1.md"])


class CodeLocationTests(RealRunCase):
    """The check that this checkout's code runs (design 5.4; note section 5)."""

    @classmethod
    def setUpClass(cls):
        """Runs the five projects once."""
        cls.project, cls.out, cls.log, _ = runs()["elsewhere"]

    def test_package_outside_the_checkout_is_a_problem(self):
        """The environment's Python finds ``wordcount`` elsewhere: a problem, and that
        program's commands do not run; other programs' commands do."""
        report = self.real_report(self.out, 1)
        self.assertEqual(len(problems_of(report, "code-location")), 1, report["problems"])
        self.assert_not_run(command_of(report, WHERE, f"{CONSOLE} say console"))
        self.assert_command(command_of(report, WHERE, "sample say program"), "matches")
        self.assertEqual([call["argv"] for call in calls(self.log)], [["say", "program"]])
        self.assertIsNone(report["label"])


class NoEnvironmentTests(RealRunCase):
    """No environment to run console scripts from (note section 5)."""

    def test_no_environment_is_a_problem(self):
        """``TROY_MODE_ENV_PREFIX`` unset and mamba failing: an ``environment`` problem."""
        _, out, log, _ = runs()["no environment"]
        report = self.real_report(out, 1)
        self.assertIn("environment", [p.get("kind") for p in report["problems"]])
        self.assert_not_run(command_of(report, WHERE, f"{CONSOLE} say console"))
        self.assertNotIn(["say", "console"], [call["argv"] for call in calls(log)])


class SafetyTests(RealRunCase):
    """Absolute paths the map does not cover, setup, and missing programs (design 5.5)."""

    @classmethod
    def setUpClass(cls):
        """Runs the five projects once."""
        cls.project, cls.out, cls.log, _ = runs()["safety"]

    def setUp(self):
        """The run has problems, so it exits 1."""
        self.report = self.real_report(self.out, 1)
        self.ran = [call["argv"] for call in calls(self.log)]

    def cmd(self, typed: str, heading: str) -> dict:
        """The one command entry of a section with this typed line."""
        return command_of(self.report, SAFETY, typed, heading)

    def test_mapped_paths_run(self):
        """A prototype path the map covers is run in the scratch folder."""
        self.assert_command(self.cmd("sample write-in D:\\OneDrive\\menu note.txt hello",
                                     "Mapped"), "matches")
        self.assert_command(self.cmd("sample cat-in D:\\OneDrive\\menu note.txt", "Mapped"),
                            "matches", real=["hello"])

    def test_unmapped_path_in_a_command_is_not_run(self):
        """Planted bug "an unmapped absolute path run": a drive path and a network path are
        problems, and only those commands do not run."""
        found = problems_of(self.report, "unmapped-path", SAFETY)
        for typed in UNMAPPED:
            with self.subTest(typed=typed):
                self.assert_not_run(self.cmd(typed, "Unmapped command"))
                self.assertEqual([(p.get("section"), p.get("typed")) for p in found
                                  if p.get("typed") == typed], [("Unmapped command", typed)])
                self.assertNotIn(typed.split(" ")[1:], self.ran)
        self.assert_command(self.cmd("sample say after", "Unmapped command"), "matches")

    def test_word_starting_with_a_slash(self):
        """``/srv/menu`` is an absolute path elsewhere, and a plain word on Windows."""
        entry = self.cmd(SLASH, "Unmapped command")
        if WINDOWS:
            self.assert_command(entry, "matches")
        else:
            self.assert_not_run(entry)
            self.assertTrue([p for p in problems_of(self.report, "unmapped-path", SAFETY)
                             if p.get("typed") == SLASH], self.report["problems"])

    def test_unmapped_env_value_stops_its_section(self):
        """A ``$env:`` line with an unmapped path: a problem, and its section stops."""
        found = [p for p in problems_of(self.report, "unmapped-path", SAFETY)
                 if p.get("section") == "Unmapped variable"]
        self.assertEqual(len(found), 1, self.report["problems"])
        self.assert_not_run(self.cmd("sample say still", "Unmapped variable"))
        self.assertNotIn(["say", "still"], self.ran)

    def test_unmapped_setup_stops_its_section(self):
        """A setup command with an unmapped path is not run, and neither is the section."""
        found = [p for p in problems_of(self.report, "unmapped-path", SAFETY)
                 if p.get("section") == "Unmapped setup"]
        self.assertEqual(len(found), 1, self.report["problems"])
        self.assert_not_run(self.cmd("sample say never", "Unmapped setup"))
        self.assertNotIn(["say", "E:\\Secret"], self.ran)
        self.assertNotIn(["say", "never"], self.ran)

    def test_failing_setup_stops_its_section(self):
        """A setup command that exits with 3: ``setup-failed``; the section does not run."""
        found = problems_of(self.report, "setup-failed", SAFETY)
        self.assertEqual([p.get("section") for p in found], ["Setup fails"])
        self.assertIn(["fail", "3", "setup", "broke"], self.ran)
        self.assert_not_run(self.cmd("sample say skipped by setup", "Setup fails"))

    def test_programs_not_found(self):
        """A console script missing from the environment, with its fix, and a missing
        ``[programs]`` path: problems, and their commands do not run."""
        found = problems_of(self.report, "program-not-found")
        self.assertEqual(len(found), 2, self.report["problems"])
        menu = [p for p in found if "menu" in f"{p.get('typed')} {p.get('message')}"]
        gone = [p for p in found if "gone" in f"{p.get('typed')} {p.get('message')}"
                or "build/nothing" in str(p.get("message"))]
        self.assertEqual(len(menu), 1, found)
        self.assertEqual(len(gone), 1, found)
        # F06 D289: uv's variables come first; UvCacheFixTests pins each state exactly.
        fix = str(menu[0].get("fix"))
        self.assertTrue(fix.startswith("UV_LINK_MODE=copy "), fix)
        self.assertTrue(fix.endswith(" uv pip install -e . --no-deps"), fix)
        self.assertNotEqual(fix, "uv pip install -e . --no-deps")
        for typed in ("menu say x", "gone say y"):
            with self.subTest(typed=typed):
                self.assert_not_run(self.cmd(typed, "Missing programs"))

    def test_later_sections_still_run(self):
        """The last section runs and matches."""
        self.assert_command(self.cmd("sample say fine", "After"), "matches")

    def test_unmapped_path_in_the_environment_table(self):
        """``[environment] set`` with an unmapped path is a problem of that prototype."""
        self.assertEqual(len(problems_of(self.report, "unmapped-path", ENV_SET)), 1,
                         self.report["problems"])


MISSING = "docs/prototypes/F02-missing.md"
MISSING_TEXT = ("# Missing\n\n## Missing programs\n\n"
                + block("PS> menu say x", "x", "PS> gone say y", "y"))
MISSING_RUN = PROGRAMS + 'gone = "build/nothing"\n'
UV_INSTALL = "uv pip install -e . --no-deps"


class UvCacheFixTests(RealRunCase):
    """The fix and message of ``program-not-found`` for a console script (F06 D289).

    ``UV_CACHE_DIR`` is removed from the engine's environment, set empty, or set to a
    user's folder, and the engine's temp folder is a scratch folder whose name holds a space.
    The fix has the real folder, quoted; the message shows ``<uv cache>`` in its place, and
    never the folder's own path.

    Planted bugs of F06 design 11.2 (D289) caught here: "the fix without the variables",
    "the folder's own path in the message", and "a value already set overridden".
    """

    @classmethod
    def setUpClass(cls):
        """Runs a project with one missing console script in each of the three states."""
        cls.temp = new_dir("temp ")
        cls.cache = cls.temp / "troy-mode-uv-cache"
        cls.user_cache = str(new_dir("user cache") / "uv")
        temp = {"TMPDIR": str(cls.temp), "TEMP": str(cls.temp), "TMP": str(cls.temp)}
        cls.states = {"unset": temp, "empty": {**temp, "UV_CACHE_DIR": ""},
                      "set": {**temp, "UV_CACHE_DIR": cls.user_cache}}

        def run(state):
            """Builds one project and runs the engine in the state's environment."""
            files = {MISSING: MISSING_TEXT, run_file_path(MISSING): MISSING_RUN}
            rows = [("F02-missing.md", "F02", MISSING)]
            project = RealProject(history(project_files(rows=rows, files=files,
                                                        consoles=(CONSOLE, "menu"))))
            return project.real_run("--item", "F02", fakes=Fakes(fail=True),
                                    env_extra=cls.states[state])

        names = list(cls.states)
        with mock.patch.dict(os.environ):
            os.environ.pop("UV_CACHE_DIR", None)
            cls.outs = dict(zip(names, parallel(run, names)))

    def menu_problem(self, state: str) -> dict:
        """The one ``program-not-found`` problem of the missing ``menu`` script."""
        report = self.real_report(self.outs[state], 1)
        found = [p for p in problems_of(report, "program-not-found")
                 if "menu" in f"{p.get('typed')} {p.get('message')}"]
        self.assertEqual(len(found), 1, report["problems"])
        return found[0]

    def assert_cache_fix(self, fix: str) -> str:
        """The fix is ``UV_LINK_MODE=copy UV_CACHE_DIR=<quoted folder> uv pip install ...``.

        Returns:
            The folder as the fix spells it.
        """
        words = shlex.split(fix)
        self.assertEqual(words[0], "UV_LINK_MODE=copy", fix)
        name, _, value = words[1].partition("=")
        self.assertEqual(name, "UV_CACHE_DIR", fix)
        self.assertIn(" ", value, "the scratch folder has a space: one quoted word")
        self.assertTrue(same_path(value, self.cache), f"{value} is not {self.cache}")
        self.assertEqual(
            fix, f"UV_LINK_MODE=copy UV_CACHE_DIR={shlex.quote(value)} {UV_INSTALL}")
        return value

    def test_unset_fix_has_both_variables(self):
        """No ``UV_CACHE_DIR``: the fix is ``UV_LINK_MODE=copy UV_CACHE_DIR=<quoted temp
        folder>/troy-mode-uv-cache uv pip install -e . --no-deps``."""
        self.assert_cache_fix(self.menu_problem("unset").get("fix"))

    def test_empty_fix_counts_as_unset(self):
        """An empty ``UV_CACHE_DIR`` gives the same fix as an unset one."""
        self.assert_cache_fix(self.menu_problem("empty").get("fix"))

    def test_set_fix_has_link_mode_alone(self):
        """A set ``UV_CACHE_DIR``: the fix is ``UV_LINK_MODE=copy uv pip install -e .
        --no-deps``, with no cache word and no folder."""
        problem = self.menu_problem("set")
        self.assertEqual(problem.get("fix"), f"UV_LINK_MODE=copy {UV_INSTALL}")
        self.assertNotIn(self.user_cache, json.dumps(problem))
        self.assertNotIn("troy-mode-uv-cache", json.dumps(problem))

    def test_message_shows_the_placeholder_not_the_folder(self):
        """Unset or empty: the message says to run ``UV_LINK_MODE=copy UV_CACHE_DIR=<uv cache>
        uv pip install -e . --no-deps`` in the environment, and holds no spelling of the
        folder."""
        for state in ("unset", "empty"):
            with self.subTest(state=state):
                message = str(self.menu_problem(state).get("message"))
                self.assertIn(f"UV_LINK_MODE=copy UV_CACHE_DIR=<uv cache> {UV_INSTALL}", message)
                self.assertNotIn("troy-mode-uv-cache", message)
                self.assert_no_local_path(message, self.cache, self.temp)

    def test_message_with_a_set_value_has_link_mode_alone(self):
        """A set ``UV_CACHE_DIR``: the message names ``UV_LINK_MODE=copy uv pip install -e .
        --no-deps``, with no ``<uv cache>``, no folder, and not the user's value."""
        message = str(self.menu_problem("set").get("message"))
        self.assertIn(f"UV_LINK_MODE=copy {UV_INSTALL}", message)
        self.assertNotIn("UV_CACHE_DIR", message)
        self.assertNotIn("<uv cache>", message)
        self.assertNotIn(self.user_cache, message)
        self.assertNotIn("troy-mode-uv-cache", message)

    def test_only_the_console_script_has_a_fix_with_variables(self):
        """The missing ``[programs]`` path is a problem without a uv fix."""
        for state in self.states:
            with self.subTest(state=state):
                report = self.real_report(self.outs[state], 1)
                gone = [p for p in problems_of(report, "program-not-found")
                        if "menu" not in f"{p.get('typed')} {p.get('message')}"]
                self.assertEqual(len(gone), 1, report["problems"])
                self.assertNotIn("UV_", json.dumps(gone[0]))


class DirtyTreeTests(RealRunCase):
    """The working tree must be clean (design 5.5; note section 2)."""

    def test_untracked_file_stops_the_run(self):
        """An untracked file: exit 1, ``dirty-tree``, and no command runs."""
        _, out, log, _ = runs()["dirty"]
        report = self.real_report(out, 1)
        self.assertIn("dirty-tree", [p.get("kind") for p in report["problems"]])
        self.assertEqual(calls(log), [])
        self.assertTrue(all(entry.get("result") == "not run"
                            for p in report.get("prototypes") or []
                            for entry in commands_of(report, p["file"])), report["prototypes"])


if __name__ == "__main__":
    unittest.main()
