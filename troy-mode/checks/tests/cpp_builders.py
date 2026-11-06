"""Builders and run helpers for the C/C++ adapter tests.

The functions here produce C++ source text, module tables, and CTest JUnit
text, and run ``troy_check.py code`` on a throwaway repository with
``[lang] name = "cpp"``. Nothing here imports the implementation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Iterable, Mapping, Optional, Sequence, Tuple

from builders import make_config
from code_helpers import check_code, code_sandbox, write_report
from helpers import CHECKER, Content, Outcome, Sandbox, base_env
from prefetch import prefetchable
from shape_builders import Mod, arch_doc
from shape_runs import IMPL, TESTS  # noqa: F401  (re-exported for the tests)

TEST_GLOBS = ("**/*_test.cc", "**/*_test.cpp")
MISSING_LOG = "<missing log>"
CPP_EXTENSIONS = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")
NT = os.name == "nt"


def cpp_config(
    name: Optional[str] = "cpp",
    include_dirs: Optional[Sequence[str]] = None,
    limits: Optional[Mapping[str, int]] = None,
    tests: Sequence[str] = TEST_GLOBS,
) -> str:
    """Builds a config for a C/C++ project.

    Args:
        name: Value of ``[lang] name``, or None to leave ``[lang]`` out.
        include_dirs: Value of ``[lang] include_dirs``, or None to leave it out.
        limits: Mapping of ``[limits]`` keys to integers.
        tests: Patterns added to ``[paths] tests``.

    Returns:
        The config text.
    """
    extra = f'[lang]\nname = "{name}"\n' if name else ""
    if name and include_dirs is not None:
        quoted = ", ".join(f'"{d}"' for d in include_dirs)
        extra += f"include_dirs = [{quoted}]\n"
    paths = {"tests": list(tests)} if tests else None
    return make_config(paths=paths, limits=limits, extra=extra)


def _expand(text: str, sandbox: Sandbox) -> str:
    """Replaces the root placeholders of a warning log.

    ``{ROOT_POSIX}`` is the repository root with forward slashes and
    ``{ROOT_WIN}`` the root with backslashes. ``{TMP_POSIX}`` is the folder
    that holds the repository.

    Args:
        text: The log text.
        sandbox: The sandbox that owns the repository.

    Returns:
        The text with the placeholders replaced.
    """
    root = sandbox.root
    return (
        text.replace("{ROOT_POSIX}", root.as_posix())
        .replace("{ROOT_WIN}", str(root).replace("/", "\\"))
        .replace("{TMP_POSIX}", sandbox.tmp.as_posix())
    )


def _doc_args(sandbox: Sandbox, doc_warnings: Optional[str]) -> list:
    """Builds the ``--doc-warnings`` arguments.

    Args:
        sandbox: The sandbox.
        doc_warnings: Log text, ``MISSING_LOG`` for a path that does not
            exist, or None for no option.

    Returns:
        The extra command-line arguments.
    """
    if doc_warnings is None:
        return []
    if doc_warnings == MISSING_LOG:
        return ["--doc-warnings", str(sandbox.tmp / "absent" / "doxygen.log")]
    path = write_report(sandbox, _expand(doc_warnings, sandbox), "log")
    return ["--doc-warnings", str(path)]


def _run_without_site(sandbox: Sandbox, title: str, extra: Sequence[str]) -> Outcome:
    """Runs the checker with ``-S`` so that site-packages is not importable.

    Args:
        sandbox: The sandbox.
        title: PR title.
        extra: Extra command-line arguments.

    Returns:
        The outcome of the run.
    """
    args = ["code", "--base", "main", "--head", "feature", "--title", title]
    args += ["--repo", str(sandbox.root), "--json", *extra]
    env = base_env()
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [sys.executable, "-S", str(CHECKER), *args],
        cwd=str(sandbox.tmp),
        env=env,
        capture_output=True,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    try:
        report = json.loads(proc.stdout)
    except ValueError:
        report = None
    return Outcome(proc.returncode, proc.stdout, proc.stderr, report)


def run_cpp(
    changes: Mapping[str, Content],
    base_files: Optional[Mapping[str, Content]] = None,
    title: str = IMPL,
    include_dirs: Optional[Sequence[str]] = None,
    limits: Optional[Mapping[str, int]] = None,
    doc_warnings: Optional[str] = None,
    junit: Sequence[str] = (),
    history: Sequence[str] = (),
    name: Optional[str] = "cpp",
    no_site: bool = False,
    body: Optional[str] = None,
) -> Outcome:
    """Runs ``troy_check.py code`` on a one-commit PR with a C/C++ config.

    Args:
        changes: Paths mapped to new content for the PR commit.
        base_files: Files of the base commit.
        title: PR title.
        include_dirs: Value of ``[lang] include_dirs``, or None for none.
        limits: Mapping of ``[limits]`` keys to integers.
        doc_warnings: Text of the Doxygen warning log (see ``_expand`` for
            placeholders), ``MISSING_LOG``, or None for no option.
        junit: JUnit report texts.
        history: Subjects of commits on main before the PR.
        name: Value of ``[lang] name``.
        no_site: Whether to run Python with ``-S``.
        body: PR description text.

    Returns:
        The outcome of the run.
    """
    config = cpp_config(name, include_dirs, limits)
    sandbox = code_sandbox(title, changes, base_files, config=config, history=history)
    try:
        extra = _doc_args(sandbox, doc_warnings)
        if no_site:
            return _run_without_site(sandbox, title, extra)
        return check_code(sandbox, title, junit=list(junit), body=body, extra_args=extra)
    finally:
        sandbox.close()


run_cpp = prefetchable(run_cpp)


def detail_text(outcome: Outcome, rule: str) -> str:
    """Joins the detail entries of a rule into one searchable text.

    Args:
        outcome: The outcome of a run.
        rule: Rule ID.

    Returns:
        The details as JSON lines, with non-ASCII characters kept.
    """
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in outcome.details(rule))


def stmts(count: int, indent: int = 2, prefix: str = "v") -> str:
    """Builds ``count`` distinct code lines.

    Args:
        count: Number of lines.
        indent: Number of leading spaces.
        prefix: Variable name prefix.

    Returns:
        The lines, each ending in a line feed.
    """
    pad = " " * indent
    return "".join(f"{pad}int {prefix}{i} = {i};\n" for i in range(count))


def cfunc(
    name: str = "F",
    code: int = 3,
    ret: str = "int",
    params: str = "",
    doc: Optional[str] = "/// Does it.",
    indent: int = 0,
    extra: str = "",
    blank: int = 0,
    comment: int = 0,
    allman: bool = False,
    prefix: str = "",
) -> str:
    """Builds a function definition.

    Args:
        name: Function name as written, for example ``Foo::Decl``.
        code: Number of code lines in the body.
        ret: Return type text.
        params: Parameter list text, which may span lines.
        doc: Doc comment line above the function, or None for none.
        indent: Number of leading spaces of the definition.
        extra: Raw lines (already indented) added before the code lines.
        blank: Number of blank lines added after the code.
        comment: Number of comment-only lines added after the code.
        allman: Whether the opening brace stands on its own line.
        prefix: Text written before the return type, for example ``inline``.

    Returns:
        The definition, ending in a line feed.
    """
    pad = " " * indent
    head = f"{pad}{prefix + ' ' if prefix else ''}{ret} {name}({params})"
    out = [f"{pad}{doc}\n"] if doc is not None else []
    out.append(f"{head}\n{pad}{{\n" if allman else f"{head} {{\n")
    out.append(extra)
    out.append(stmts(code, indent + 2))
    out.append("\n" * blank)
    out.append(f"{pad}  // note\n" * comment)
    out.append(f"{pad}}}\n")
    return "".join(out)


def cclass(name: str = "Foo", body: str = "", doc: Optional[str] = "/// A class.") -> str:
    """Builds a class definition with a public section.

    Args:
        name: Class name.
        body: Raw text of the members, already indented by 2 spaces.
        doc: Doc comment line above the class, or None for none.

    Returns:
        The definition, ending in a line feed.
    """
    head = f"{doc}\n" if doc is not None else ""
    return f"{head}class {name} {{\n public:\n{body}}};\n"


def cmodule(*chunks: str) -> str:
    """Joins definitions with a blank line between them.

    Args:
        *chunks: Texts that each end in a line feed.

    Returns:
        The file text.
    """
    return "\n".join(chunks)


def ctest_xml(cases: Iterable[Tuple[str, str]]) -> str:
    """Builds a JUnit file in the format CTest writes for GoogleTest.

    Args:
        cases: ``(name, status)`` pairs. ``fail`` adds a ``<failure>`` child
            and every status is written into the ``status`` attribute.

    Returns:
        The XML text, with a ``<testsuite>`` root and tab indentation.
    """
    items = list(cases)
    failures = sum(1 for _, status in items if status == "fail")
    rows = []
    for name, status in items:
        child = '\t\t<failure message="Failed"/>\n' if status == "fail" else ""
        rows.append(
            f'\t<testcase name="{name}" classname="{name}" time="0.0166814" '
            f'status="{status}">\n{child}\t\t<properties/>\n'
            "\t\t<system-out>...</system-out>\n\t</testcase>\n"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<testsuite name="(empty)" tests="{len(items)}" failures="{failures}" '
        'disabled="0" skipped="0" hostname="" time="0" timestamp="2026-11-06T02:05:03">\n'
        + "".join(rows)
        + "</testsuite>\n"
    )


CORE = Mod("core", ["src/core/**"], ["src/core/api.h"])
STORE = Mod("store", ["src/store/**"], ["src/store/api.h"], ["core"])
UI = Mod("ui", ["src/ui/**"], ["src/ui/api.h"], ["store"])
STD_MODS = (CORE, STORE, UI)


def cpp_base(mods: Sequence[Mod] = STD_MODS) -> dict:
    """Builds the base files of a small three-module C++ project.

    Args:
        mods: Rows of the architecture table.

    Returns:
        Paths mapped to text, including ``docs/architecture.md``. Each module
        has ``api.h`` and ``internal.h`` under ``src/<module>/``. The folder
        ``src/tools/`` holds a header that belongs to no module.
    """
    files = {"docs/architecture.md": arch_doc(mods), "src/tools/helper.h": "#pragma once\n"}
    for name in ("core", "store", "ui"):
        files[f"src/{name}/api.h"] = "#pragma once\n"
        files[f"src/{name}/internal.h"] = "#pragma once\n"
    return files


def run_arch(
    changes: Mapping[str, Content],
    extra: Optional[Mapping[str, Content]] = None,
    mods: Sequence[Mod] = STD_MODS,
    title: str = IMPL,
    include_dirs: Optional[Sequence[str]] = ("src",),
    drop: Sequence[str] = (),
    name: Optional[str] = "cpp",
) -> Outcome:
    """Runs ``code`` on the three-module C++ project with some changes.

    Args:
        changes: Paths mapped to new content for the PR commit.
        extra: Files added to the base commit.
        mods: Rows of the architecture table in the base commit.
        title: PR title.
        include_dirs: Value of ``[lang] include_dirs``, or None to leave it out.
        drop: Paths of the standard base files to leave out.
        name: Value of ``[lang] name``.

    Returns:
        The outcome of the run.
    """
    base = {k: v for k, v in cpp_base(mods).items() if k not in drop}
    base.update(extra or {})
    return run_cpp(changes, base, title, include_dirs=include_dirs, name=name)
