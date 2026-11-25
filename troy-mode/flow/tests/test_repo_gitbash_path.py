"""A ``--repo`` path in Git Bash's form (F20 design 4, D290; sections 8.1, 8.2, 10).

Written from F20 design version 1.5 before the code exists. On Windows only, when the
``--repo`` folder does not exist as given and its path starts with exactly one ``/``,
the engine tries the folder Git Bash means: the output of ``cygpath -w <path>`` when
``cygpath`` is on the ``PATH``, and otherwise ``/c/rest`` read as ``C:\\rest`` (any drive
letter, either case; ``/c`` alone is the drive's root). A folder that exists as given is
used as given. A folder that is missing after the conversion is refused with the
"is not a folder" error that names the path as given. Other systems read the path as given.

The in-process cases call ``troyflow.repo.find_repo`` and ``need_repo`` (``find_repo``
returns a ``Repo`` or None outside a repository and raises ``FlowError`` for a missing
folder); the end-to-end cases run ``troy_flow.py status --repo <path> --json`` as a
subprocess with ``MSYS_NO_PATHCONV=1`` in its environment.

Planted bugs caught here (design 8.2, D290):

- A converted path used when the path as given exists:
  ``AsGivenTests.test_existing_folder_with_a_leading_slash_is_used_as_given``.
- The conversion run on another system: ``OtherSystemTests``.
- ``cygpath`` ignored when it is on the PATH: ``CygpathTests.test_fake_cygpath_output_is_used``
  and ``test_real_cygpath_reads_tmp``.
- A drive letter left out of the mapping: ``DriveMappingTests.test_the_repositorys_own_drive``
  (the letter is the real one, so a fixed ``c`` fails on any other drive) and
  ``test_upper_case_letter``.
- A missing folder accepted after the conversion: ``MissingTests``.
"""

import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

from flow_helpers import PLUGIN_ROOT, SCRATCH, Fakes, git, new_dir, run_engine, same_path

for _folder in ("init", "hooks", "checks", "flow"):
    sys.path.insert(0, str(PLUGIN_ROOT / "troy-mode" / _folder))

from troyflow import repo as repo_module  # noqa: E402
from troyflow.errors import FlowError  # noqa: E402

ON_WINDOWS = os.name == "nt"


def make_repo(prefix: str = "gb repo") -> Path:
    """A new git repository (with a space in its folder name) in the scratch area."""
    folder = new_dir(prefix)
    git(folder, "init", "-q", "-b", "main")
    (folder / "README.md").write_bytes(b"# gitbash\n")
    git(folder, "add", "README.md")
    git(folder, "commit", "-q", "-m", "Initial commit")
    return folder


def git_bash_form(folder: Path, upper: bool = False) -> str:
    """The ``/c/rest`` form of a real Windows folder, built from its own drive and path."""
    resolved = os.path.abspath(str(folder))
    drive, rest = os.path.splitdrive(resolved)
    letter = drive[0].upper() if upper else drive[0].lower()
    return "/" + letter + rest.replace("\\", "/")


def path_without_cygpath() -> str:
    """The current PATH without any folder that holds a ``cygpath``."""
    kept = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if entry and any(os.path.exists(os.path.join(entry, name))
                         for name in ("cygpath", "cygpath.exe", "cygpath.bat", "cygpath.cmd")):
            continue
        kept.append(entry)
    return os.pathsep.join(kept)


def fake_cygpath(folder: Path, answer: str, code: int = 0) -> Path:
    """A fake ``cygpath`` that logs its arguments and prints ``answer``.

    Args:
        folder: A new folder for the fake, to put first on the PATH.
        answer: The line it prints.

    Returns:
        The log file (one JSON list of arguments per call; absent until it is called).
    """
    log = folder / "cygpath.log"
    script = folder / "fake_cygpath.py"
    script.write_text(
        "import json, sys\n"
        f"with open({str(log)!r}, 'a', encoding='utf-8') as out:\n"
        "    out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        f"sys.stdout.write({answer!r} + '\\n' if {answer!r} else '')\n"
        f"sys.exit({code})\n", encoding="utf-8")
    if ON_WINDOWS:
        launcher = folder / "cygpath.cmd"
        launcher.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n'
                            "exit /b %ERRORLEVEL%\r\n", encoding="utf-8")
    else:
        launcher = folder / "cygpath"
        launcher.write_text(f"#!{sys.executable}\n{script.read_text(encoding='utf-8')}",
                            encoding="utf-8")
        launcher.chmod(0o755)
    return log


def calls(log: Path) -> list:
    """The argument lists a fake cygpath was called with."""
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]


def with_path(first: Path = None, rest: str = None) -> dict:
    """Environment changes: PATH with ``first`` (a folder) in front of ``rest`` (default: current)."""
    rest = os.environ.get("PATH", "") if rest is None else rest
    return {"PATH": (str(first) + os.pathsep + rest) if first is not None else rest}


def refused_naming(case: unittest.TestCase, given: str, func) -> None:
    """Asserts that ``func(given)`` raises FlowError saying "not a folder" and naming ``given``."""
    with case.assertRaises(FlowError) as caught:
        func(given)
    message = str(caught.exception)
    case.assertIn("is not a folder", message)
    case.assertTrue(names(given, message), message)


def as_today(given: str) -> str:
    """The path as today's error prints it: the given path with backslashes (Path's form)."""
    return given.replace("/", "\\")


def names(given: str, text: str) -> bool:
    """Whether ``text`` names ``given``, as typed or as today's refusal prints it (``\\c\\x``)."""
    return given in text or as_today(given) in text


@unittest.skipUnless(ON_WINDOWS, "D290 reads Git Bash paths on Windows only")
class DriveMappingTests(unittest.TestCase):
    """``/c/rest`` as ``C:\\rest`` when there is no ``cygpath`` on the PATH."""

    def setUp(self):
        self.repo = make_repo()
        patcher = mock.patch.dict(os.environ, {"PATH": path_without_cygpath()})
        patcher.start()
        self.addCleanup(patcher.stop)
        if shutil.which("cygpath"):
            self.skipTest("cygpath could not be taken off the PATH")

    def test_the_repositorys_own_drive(self):
        """The folder's own drive letter (lower case) maps back to the real repository."""
        found = repo_module.find_repo(git_bash_form(self.repo))
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, self.repo), found.root)

    def test_upper_case_letter(self):
        """``/C/...`` reads like ``/c/...``."""
        found = repo_module.find_repo(git_bash_form(self.repo, upper=True))
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, self.repo), found.root)

    def test_need_repo_reads_it_too(self):
        """``need_repo`` goes through the same reading."""
        found = repo_module.need_repo(git_bash_form(self.repo))
        self.assertTrue(same_path(found.root, self.repo), found.root)

    def test_subfolder_of_the_repository(self):
        """A subfolder in Git Bash's form finds its repository's root."""
        sub = self.repo / "src dir"
        sub.mkdir()
        found = repo_module.find_repo(git_bash_form(sub))
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, self.repo), found.root)

    def test_drive_alone_is_the_drives_root(self):
        """``/c`` alone is ``C:\\``: it exists, so no refusal."""
        letter = os.path.splitdrive(os.path.abspath(str(self.repo)))[0][0].lower()
        try:
            found = repo_module.find_repo("/" + letter)
        except FlowError as error:
            self.fail(f"/{letter} was refused: {error}")
        if found is not None:
            self.assertEqual(os.path.normcase(str(found.root)).rstrip("\\")[:2],
                             letter + ":")

    def test_drive_root_is_not_read_as_a_folder_of_the_current_drive(self):
        """``/c`` is not ``\\c`` on the current drive (which does not exist)."""
        letter = os.path.splitdrive(os.path.abspath(str(self.repo)))[0][0].lower()
        self.assertFalse(os.path.exists("/" + letter), "pick a drive letter that is no folder")
        repo_module.find_repo("/" + letter)

    def test_end_to_end_status(self):
        """``status --repo /c/...`` with MSYS_NO_PATHCONV=1 reports the real repository."""
        given = git_bash_form(self.repo)
        fakes = Fakes(fail=True)
        out = run_engine(["status", "--repo", given, "--json"], SCRATCH, fakes,
                         {"MSYS_NO_PATHCONV": "1"})
        self.assertEqual(out.code, 0, out.describe())
        self.assertIsNotNone(out.report, out.describe())
        self.assertIsNotNone(out.report["repo"], out.describe())
        self.assertTrue(same_path(out.report["repo"], self.repo), out.describe())
        self.assertEqual(out.report["branch"], "main")


@unittest.skipUnless(ON_WINDOWS, "D290 reads Git Bash paths on Windows only")
class CygpathTests(unittest.TestCase):
    """``cygpath -w <path>`` when ``cygpath`` is on the PATH."""

    def test_fake_cygpath_output_is_used(self):
        """A /tmp-style path becomes whatever the fake prints, called as ``cygpath -w <path>``."""
        repo = make_repo()
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, str(repo))
        given = "/gb-fake-mount/some/where"
        with mock.patch.dict(os.environ, with_path(folder)):
            found = repo_module.find_repo(given)
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, repo), found.root)
        self.assertIn(calls(log), ([["-w", given]], [["-w", as_today(given)]]))

    def test_fake_cygpath_wins_over_the_drive_mapping(self):
        """With a ``cygpath`` on the PATH, its answer is used even for ``/c/...``."""
        real = make_repo("gb real")
        other = make_repo("gb other")
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, str(other))
        with mock.patch.dict(os.environ, with_path(folder)):
            found = repo_module.find_repo(git_bash_form(real))
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, other), f"{found.root}: cygpath was ignored")
        self.assertEqual(len(calls(log)), 1)

    def test_failing_cygpath_without_output_falls_back_to_the_drive_mapping(self):
        """A ``cygpath`` that exits 1 and prints nothing gives no answer: ``/c/...`` still maps."""
        repo = make_repo()
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, "", code=1)
        with mock.patch.dict(os.environ, with_path(folder)):
            found = repo_module.find_repo(git_bash_form(repo))
        self.assertEqual(len(calls(log)), 1, "the fake cygpath was not asked")
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, repo), found.root)

    def test_failing_cygpath_output_is_not_used(self):
        """A ``cygpath`` that exits 1 but prints another repository: its output is not used."""
        repo = make_repo("gb real")
        other = make_repo("gb other")
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, str(other), code=1)
        with mock.patch.dict(os.environ, with_path(folder)):
            found = repo_module.find_repo(git_bash_form(repo))
        self.assertEqual(len(calls(log)), 1, "the fake cygpath was not asked")
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, repo),
                        f"{found.root}: a failing cygpath's output was used")

    def test_failing_cygpath_output_of_a_plain_folder_is_not_used(self):
        """A failing ``cygpath`` that prints an existing non-repository folder is not used."""
        repo = make_repo()
        plain = new_dir("gb plain")
        folder = new_dir("fake-bin")
        fake_cygpath(folder, str(plain), code=1)
        with mock.patch.dict(os.environ, with_path(folder)):
            found = repo_module.find_repo(git_bash_form(repo))
        self.assertIsNotNone(found, "the plain folder from a failing cygpath was used")
        self.assertTrue(same_path(found.root, repo), found.root)

    def test_fake_cygpath_end_to_end(self):
        """The engine, run with MSYS_NO_PATHCONV=1 and a fake ``cygpath``, reads its answer."""
        repo = make_repo()
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, str(repo))
        given = "/gb-fake-mount/some/where"
        with mock.patch.dict(os.environ, with_path(folder)):
            out = run_engine(["status", "--repo", given, "--json"], SCRATCH, Fakes(fail=True),
                             {"MSYS_NO_PATHCONV": "1"})
        self.assertEqual(out.code, 0, out.describe())
        self.assertIsNotNone(out.report, out.describe())
        self.assertTrue(same_path(out.report["repo"], repo), out.describe())
        self.assertIn(calls(log), ([["-w", given]], [["-w", as_today(given)]]))

    @unittest.skipUnless(shutil.which("cygpath"), "no cygpath on the PATH")
    def test_real_cygpath_reads_tmp(self):
        """A repository under Git Bash's own /tmp is read through the real ``cygpath``."""
        import subprocess
        tmp = subprocess.run(["cygpath", "-w", "/tmp"], capture_output=True, text=True,
                             check=True).stdout.strip()
        base = Path(tmp)
        if not base.is_dir():
            self.skipTest(f"Git Bash's /tmp ({tmp}) is not a folder")
        name = f"troyflow-gb-{os.getpid()}"
        folder = base / name
        folder.mkdir()
        self.addCleanup(shutil.rmtree, str(folder), ignore_errors=True)
        git(folder, "init", "-q", "-b", "main")
        (folder / "README.md").write_bytes(b"# gitbash\n")
        git(folder, "add", "README.md")
        git(folder, "commit", "-q", "-m", "Initial commit")
        given = f"/tmp/{name}"
        self.assertFalse(os.path.exists(given), "the path must not exist as given")
        found = repo_module.find_repo(given)
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, folder), found.root)
        out = run_engine(["status", "--repo", given, "--json"], SCRATCH, Fakes(fail=True),
                         {"MSYS_NO_PATHCONV": "1"})
        self.assertEqual(out.code, 0, out.describe())
        self.assertTrue(same_path(out.report["repo"], folder), out.describe())

    @unittest.skipUnless(shutil.which("cygpath"), "no cygpath on the PATH")
    def test_real_cygpath_reads_a_drive_form(self):
        """``/c/...`` read with the real ``cygpath`` on the PATH finds the repository."""
        repo = make_repo()
        found = repo_module.find_repo(git_bash_form(repo))
        self.assertIsNotNone(found)
        self.assertTrue(same_path(found.root, repo), found.root)


def _existing_root_folder() -> str:
    """A folder directly under the current drive's root, as ``/Name``, or None."""
    root = os.path.abspath(os.sep)
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return None
    for name in names:
        if os.path.isdir(os.path.join(root, name)):
            return "/" + name
    return None


@unittest.skipUnless(ON_WINDOWS, "D290 reads Git Bash paths on Windows only")
class AsGivenTests(unittest.TestCase):
    """A folder that exists as given is used as given."""

    def test_existing_folder_with_a_leading_slash_is_used_as_given(self):
        """``/Name`` exists on the current drive: ``cygpath`` is not asked, its answer not used."""
        given = _existing_root_folder()
        if given is None:
            self.skipTest("no folder under the current drive's root")
        repo = make_repo()
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, str(repo))
        with mock.patch.dict(os.environ, with_path(folder)):
            found = repo_module.find_repo(given)
        self.assertEqual(calls(log), [], "cygpath was run for a folder that exists as given")
        self.assertFalse(found is not None and same_path(found.root, repo),
                         "the converted folder was used")

    def test_existing_folder_with_a_leading_slash_is_used_as_given_without_cygpath(self):
        """The same, with no ``cygpath``: ``/Name`` is not read as a drive path."""
        given = _existing_root_folder()
        if given is None:
            self.skipTest("no folder under the current drive's root")
        with mock.patch.dict(os.environ, {"PATH": path_without_cygpath()}):
            try:
                repo_module.find_repo(given)
            except FlowError as error:
                self.fail(f"{given} exists as given but was refused: {error}")

    def test_windows_form_is_not_converted(self):
        """A drive-letter path that exists never asks ``cygpath``."""
        repo = make_repo()
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, str(make_repo("gb other")))
        with mock.patch.dict(os.environ, with_path(folder)):
            found = repo_module.find_repo(str(repo))
        self.assertTrue(same_path(found.root, repo), found.root)
        self.assertEqual(calls(log), [])


@unittest.skipUnless(ON_WINDOWS, "D290 reads Git Bash paths on Windows only")
class MissingTests(unittest.TestCase):
    """A folder that is missing after the conversion is refused, naming the path as given."""

    def test_missing_drive_form_without_cygpath(self):
        """``/c/<missing>`` without ``cygpath``: refused, naming ``/c/<missing>``."""
        repo = make_repo()
        given = git_bash_form(repo) + "/no-such-folder-d290"
        with mock.patch.dict(os.environ, {"PATH": path_without_cygpath()}):
            refused_naming(self, given, repo_module.find_repo)
            refused_naming(self, given, repo_module.need_repo)

    def test_missing_folder_when_cygpath_prints_a_missing_folder(self):
        """``cygpath`` prints a folder that does not exist: refused, naming the given path."""
        folder = new_dir("fake-bin")
        fake_cygpath(folder, str(folder / "no-such-folder-d290"))
        given = "/gb-fake-mount/missing"
        with mock.patch.dict(os.environ, with_path(folder)):
            refused_naming(self, given, repo_module.find_repo)
            refused_naming(self, given, repo_module.need_repo)

    def test_missing_folder_with_a_real_looking_converted_path(self):
        """The refusal names the Git Bash form, not the converted Windows form."""
        repo = make_repo()
        given = git_bash_form(repo) + "/missing"
        with mock.patch.dict(os.environ, {"PATH": path_without_cygpath()}):
            with self.assertRaises(FlowError) as caught:
                repo_module.find_repo(given)
        message = str(caught.exception)
        self.assertTrue(names(given, message), message)
        self.assertNotIn(os.path.abspath(str(repo)), message, "the converted folder is named")

    def test_double_slash_is_not_converted(self):
        """``//c/...`` (two slashes) is not Git Bash's form: never converted, so refused."""
        repo = make_repo()
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, str(repo))
        given = "/" + git_bash_form(repo)
        with mock.patch.dict(os.environ, with_path(folder)):
            refused_naming(self, given, repo_module.find_repo)
        self.assertEqual(calls(log), [], "cygpath was run for a path that starts with //")
        with mock.patch.dict(os.environ, {"PATH": path_without_cygpath()}):
            refused_naming(self, given, repo_module.find_repo)

    def test_end_to_end_refusal_names_the_path_as_given(self):
        """The engine refuses a missing Git Bash path, naming it as given."""
        repo = make_repo()
        given = git_bash_form(repo) + "/no-such-folder-d290"
        with mock.patch.dict(os.environ, {"PATH": path_without_cygpath()}):
            out = run_engine(["status", "--repo", given, "--json"], SCRATCH, Fakes(fail=True),
                             {"MSYS_NO_PATHCONV": "1"})
        self.assertNotEqual(out.code, 0, out.describe())
        text = out.stdout + out.stderr
        self.assertIn("is not a folder", text)
        self.assertTrue(names(given, text), text)

    def test_end_to_end_refusal_with_cygpath_printing_a_missing_folder(self):
        """The same with a ``cygpath`` on the PATH whose answer is missing too."""
        folder = new_dir("fake-bin")
        fake_cygpath(folder, str(folder / "no-such-folder-d290"))
        given = "/gb-fake-mount/missing"
        with mock.patch.dict(os.environ, with_path(folder)):
            out = run_engine(["status", "--repo", given, "--json"], SCRATCH, Fakes(fail=True),
                             {"MSYS_NO_PATHCONV": "1"})
        self.assertNotEqual(out.code, 0, out.describe())
        text = out.stdout + out.stderr
        self.assertIn("is not a folder", text)
        self.assertTrue(names(given, text), text)


@unittest.skipIf(ON_WINDOWS, "other systems only")
class OtherSystemTests(unittest.TestCase):
    """Other systems read the path as given: no conversion, ``cygpath`` never run."""

    def test_missing_slash_path_is_refused_whatever_cygpath_says(self):
        """A missing ``/...`` folder is refused even with a ``cygpath`` that names a real one."""
        repo = make_repo()
        folder = new_dir("fake-bin")
        log = fake_cygpath(folder, str(repo))
        given = "/gb-fake-mount/missing"
        with mock.patch.dict(os.environ, with_path(folder)):
            refused_naming(self, given, repo_module.find_repo)
        self.assertEqual(calls(log), [], "cygpath was run on a system that is not Windows")

    def test_drive_form_is_not_mapped(self):
        """``/c/rest`` is not read as ``C:\\rest``."""
        given = "/c/gb-no-such-folder-d290"
        with mock.patch.dict(os.environ, {"PATH": path_without_cygpath()}):
            refused_naming(self, given, repo_module.find_repo)

    def test_existing_path_is_used_as_given(self):
        """A real path works as before."""
        repo = make_repo()
        found = repo_module.find_repo(str(repo))
        self.assertTrue(same_path(found.root, repo), found.root)

    def test_end_to_end_refusal(self):
        """The engine refuses a missing ``/...`` folder, naming it."""
        folder = new_dir("fake-bin")
        fake_cygpath(folder, str(make_repo()))
        given = "/gb-fake-mount/missing"
        with mock.patch.dict(os.environ, with_path(folder)):
            out = run_engine(["status", "--repo", given, "--json"], SCRATCH, Fakes(fail=True))
        self.assertNotEqual(out.code, 0, out.describe())
        self.assertTrue(names(given, out.stdout + out.stderr))


if __name__ == "__main__":
    unittest.main()
