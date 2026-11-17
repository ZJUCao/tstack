"""The language packs troy-init installs (design sections 5.2 and 5.3).

Each pack lives in tstack's troy-mode/lang/<name>/ (F03). This module
says where each of its files lands in a project and who owns it there.
"""

from dataclasses import dataclass

from .errors import InitError


@dataclass(frozen=True)
class Pack:
    """What the language step writes for one language.

    Attributes:
        name: The pack's folder and [lang] name, "python" or "cpp".
        title: The language's name in the PR title.
        lock: The lock file the step compiles (design 5.4).
        manifest: Each series member's file the lock is compiled from.
        compile_args: uv pip compile's options after the manifests.
        filled: Project path to pack file, for files that belong to the
            project once written. {{environment}} is filled in.
        copied: Project path to pack file, for the files troy-init copies
            whole and owns (design 4.6).
        build_file: The project's build file, created from new_build_file
            when it is missing.
        new_build_file: The pack file a new project's build file starts from.
        gitignore: Lines the step adds to .gitignore.
    """

    name: str
    title: str
    lock: str
    manifest: str
    compile_args: tuple[str, ...]
    filled: dict[str, str]
    copied: dict[str, str]
    build_file: str
    new_build_file: str
    gitignore: tuple[str, ...]

    def source(self, pack_file: str) -> str:
        """The plugin path of one of the pack's files."""
        return f"troy-mode/lang/{self.name}/{pack_file}"

    @property
    def commit_title(self) -> str:
        """The language step's PR title and commit subject (design 7, step 5)."""
        return f"[rules] Add the {self.title} pack"


PACKS = {
    "python": Pack(
        name="python",
        title="Python",
        lock="requirements-dev.lock",
        manifest="pyproject.toml",
        compile_args=("--extra", "dev", "--universal"),
        filled={"environment.yml": "environment.yml"},
        copied={},
        build_file="pyproject.toml",
        new_build_file="pyproject-project.toml",
        gitignore=("reports/", ".coverage", "__pycache__/", ".mypy_cache/", ".pytest_cache/",
                   ".ruff_cache/"),
    ),
    "cpp": Pack(
        name="cpp",
        title="C/C++",
        lock="requirements-tools.lock",
        manifest="requirements-tools.in",
        compile_args=("--universal", "--python-version", "3.13"),
        filled={"environment.yml": "environment.yml",
                "requirements-tools.in": "requirements-tools.in"},
        copied={
            "CMakePresets.json": "CMakePresets.json",
            "cmake/troy.cmake": "cmake/troy.cmake",
            ".clang-format": ".clang-format",
            ".clang-tidy": ".clang-tidy",
            "include/troy/not_implemented.h": "include/troy/not_implemented.h",
            ".troy-mode/lang/cpp/Doxyfile": "Doxyfile",
        },
        build_file="CMakeLists.txt",
        new_build_file="CMakeLists-project.txt",
        gitignore=("build/", "reports/"),
    ),
}


def get_pack(name: str) -> Pack:
    """Returns the pack for a language name.

    Raises:
        InitError: tstack has no pack for that language.
    """
    try:
        return PACKS[name]
    except KeyError:
        raise InitError(f"tstack has no language pack named {name!r}") from None
