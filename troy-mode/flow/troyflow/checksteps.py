"""The checks a brief asks a role to run (F07 design 6.1, F03 sections 8.3 and 9.4).

Each pack step runs in the project's environment through `mamba run`. Authors
of code and tests also check their own work with `troy-check code --worktree`
(D60), because they cannot commit.
"""

import os
import shlex
import shutil
from pathlib import Path

from .errors import FlowError
from .stages import feature_stage

# Tasks that run the pack's steps and troy-check code, and the authors among
# them, which check their own uncommitted work with --worktree (D60).
CODE_TASKS = ("DV1", "DV2", "DV3", "DV4", "TE1", "TE2", "TE3", "TE4", "TE5", "TM2", "TM3",
              "TM4", "CR1")
WORKTREE_TASKS = ("DV1", "DV2", "DV3", "DV4", "TE1", "TE2", "TE3", "TE4", "TE5")
# What a code task's brief says about a test that runs on another platform only (D69).
PLATFORM_SKIP = ("A test that the test plan runs only on another platform is skipped here, and "
                 "troy-check code reports it under R09 or R10; CI checks it, so name it in your "
                 "report and do not count it as a failure.")
PREFIX_VARIABLE = "TROY_MODE_ENV_PREFIX"
TROY_CHECK = "python .troy-mode/checks/troy_check.py code --base origin/main --title {title} " \
             "--junit reports/junit.xml --coverage reports/coverage.xml"

_PYTHON = (
    "ruff check",
    "ruff format --check",
    "mypy",
    "coverage run -m pytest --junitxml=reports/junit.xml",
    "coverage xml -o reports/coverage.xml",
)
_CPP = (
    "cmake --preset coverage",
    "cmake --build --preset coverage",
    "clang-format --dry-run --Werror <changed C/C++ files>",
    "clang-tidy -p build/coverage --quiet <changed source files>",
    "cmake -E make_directory reports",
    "ctest --preset coverage --output-junit \"$PWD/reports/junit.xml\"",
    "gcovr --root . --filter 'include/' --filter 'src/' --exclude-throw-branches "
    "--exclude-unreachable-branches --cobertura reports/coverage.xml build/coverage",
    "doxygen .troy-mode/lang/cpp/Doxyfile",
)
# The release command: the version tests, which run on Troy's PC at release
# only (F08 design 5.3 and 5.5). TROY_VERSION_TESTS holds for one configure.
_PYTHON_RELEASE = ("pytest version-tests --junitxml=reports/version-junit.xml",)
_CPP_RELEASE = (
    "cmake --preset coverage -DTROY_VERSION_TESTS=ON",
    "cmake --build --preset coverage",
    "ctest --preset coverage -L version --output-junit \"$PWD/reports/version-junit.xml\"",
)
# Steps whose exit code is ignored: troy-check decides which failures are
# allowed, and a failing version test is a finding of the release test.
_IGNORE_EXIT = ("coverage run -m pytest", "ctest ", "pytest version-tests")


def read_input(path: str | None) -> str | None:
    """Reads the --input-file text, or None without one.

    Raises:
        FlowError: The file cannot be read as UTF-8.
    """
    if path is None:
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FlowError(f"cannot read {path}: {exc}") from exc


def find_mamba(notes: list[str]) -> str:
    """Finds mamba as troy-init does: the PATH, then $MAMBA_EXE (F06 design 5.4)."""
    found = shutil.which("mamba")
    if found:
        return found
    exe = os.environ.get("MAMBA_EXE")
    if exe and Path(exe).is_file():
        return exe
    notes.append("mamba is not on the PATH and $MAMBA_EXE is not set; the checks name it as "
                 "mamba.")
    return "mamba"


def run_prefix(config, folder_name: str, notes: list[str]) -> str:
    """Builds `<mamba> run -n <environment>`, or `-p <prefix>` with TROY_MODE_ENV_PREFIX."""
    mamba = shlex.quote(find_mamba(notes))
    prefix = os.environ.get(PREFIX_VARIABLE)
    if prefix:
        return f"{mamba} run -p {shlex.quote(prefix)}"
    environment = config.lang.get("environment")
    if not environment:
        environment = folder_name
        notes.append(f"The config at HEAD has no [lang] environment; the checks use {folder_name}.")
    return f"{mamba} run -n {shlex.quote(environment)}"


def first_mock(subjects: list[str]) -> bool:
    """Tells whether no feature has merged a mock on origin/main yet."""
    return not any((feature_stage(s) or ("", 0))[1] == 3 for s in subjects)


def _commands(run: str, pack) -> list[str]:
    """Prefixes each step with `<mamba> run ...`, with `|| true` where the exit code is ignored."""
    return [f"{run} {step}" + (" || true" if step.startswith(_IGNORE_EXIT) else "")
            for step in pack]


def release_command(config, folder_name: str, notes: list[str]) -> list[str]:
    """The pack's release command: the version tests into reports/version-junit.xml."""
    run = run_prefix(config, folder_name, notes)
    pack = _PYTHON_RELEASE if config.lang.get("name") == "python" else _CPP_RELEASE
    return _commands(run, pack)


def release_test_steps(config, title: str, subjects: list[str], folder_name: str,
                       notes: list[str]) -> list[str]:
    """The release test's commands (F08 design 5.5).

    The pack's steps, troy-check code with the release PR's title on the
    commit, and the release command.
    """
    return (steps("CR1", config, title, subjects, folder_name, notes)
            + release_command(config, folder_name, []))


def steps(task: str, config, title: str, subjects: list[str], folder_name: str,
          notes: list[str], version_tests: bool = False) -> list[str]:
    """Lists the checks for one task.

    Args:
        task: The task ID.
        config: The config at HEAD.
        title: The PR title, for troy-check code.
        subjects: origin/main's subjects, to find the project's first mock.
        folder_name: The checkout folder's name, the environment when none is set.
        notes: Notes for the report; this adds to them.
        version_tests: The task works on a version's tests, so the release
            command follows (F08 design 5.3).

    Returns:
        The commands, empty for tasks that write or review documents.
    """
    if task not in CODE_TASKS:
        return []
    run = run_prefix(config, folder_name, notes)
    lang = config.lang.get("name")
    pack = list(_PYTHON if lang == "python" else _CPP)
    if lang == "python" and task == "DV1" and first_mock(subjects):
        pack.insert(0, "uv pip install -e . --no-deps")
    commands = _commands(run, pack)
    rules = TROY_CHECK.format(title=shlex.quote(title))
    if lang != "python":
        rules += " --doc-warnings reports/doxygen.log"
    if task in WORKTREE_TASKS:
        rules += " --worktree"
    commands.append(f"{run} {rules}")
    if version_tests:
        commands += release_command(config, folder_name, [])
    return commands
