"""R07: module dependencies from the architecture's module table (F03 design 7).

The table under "## 3." in docs/architecture.md, read at the merge base, is
the module map. Python imports are read with the Python adapter, and C/C++
#include "..." lines with the C/C++ adapter's scanner.
"""

import posixpath
import re
from dataclasses import dataclass, field

from .context import PrContext
from .cppadapter import EXTENSIONS
from .cppadapter import scan as scan_cpp
from .gitio import list_files, read_blob, read_blobs
from .globs import matches_any
from .pyadapter import Import, ParseError, analyze
from .report import FAIL, PASS, SKIP, Detail, Result
from .shape import lang_skip

ARCHITECTURE = "docs/architecture.md"
COLUMNS = ("Module", "Owns", "External interfaces", "May depend on")
_PATTERN = re.compile(r"`([^`]+)`")
_SECTION = re.compile(r"^##\s+3\.")


@dataclass
class Module:
    """One row of the module table.

    Attributes:
        name: Module name.
        owns: Path patterns of the module's files.
        interfaces: Path patterns of the files other modules may import.
        deps: Names of the modules it may import.
    """

    name: str
    owns: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)


def _cells(line: str) -> list[str]:
    """Splits a Markdown table row into stripped cells."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _deps(cell: str) -> list[str]:
    """Reads the May depend on cell: module names separated by commas, or None."""
    if cell.strip().rstrip(".") in ("", "None", "无"):
        return []
    return [d.strip().strip("`") for d in cell.split(",") if d.strip()]


def _table_rows(lines: list[str]) -> tuple[list[str] | None, list[list[str]]]:
    """Finds the header and rows of the first table in section 3."""
    start = next((i for i, line in enumerate(lines) if _SECTION.match(line)), None)
    header, rows = None, []
    for line in lines[start + 1:] if start is not None else []:
        if line.startswith("## "):
            break
        if not line.lstrip().startswith("|"):
            if rows:
                break
            continue
        cells = _cells(line)
        if header is None:
            header = cells
        elif not all(set(c) <= set("-: ") for c in cells):
            rows.append(cells)
    return header, rows


def parse_table(text: str) -> list[Module] | None:
    """Reads the module table from the architecture document.

    Args:
        text: The text of docs/architecture.md.

    Returns:
        The modules, or None when section 3 has no table with the four columns.
    """
    header, rows = _table_rows(text.replace("\r\n", "\n").split("\n"))
    if header is None or any(name not in header for name in COLUMNS):
        return None
    at = {name: header.index(name) for name in COLUMNS}
    return [Module(row[at["Module"]].strip("` "), _PATTERN.findall(row[at["Owns"]]),
                   _PATTERN.findall(row[at["External interfaces"]]), _deps(row[at["May depend on"]]))
            for row in rows if len(row) >= len(header)]


def module_of(path: str, modules: list[Module]) -> Module | None:
    """Finds the module that owns a path, or None."""
    return next((m for m in modules if matches_any(path, m.owns)), None)


def _first(candidates: list[str], files: set[str]) -> str | None:
    """Returns the first candidate path that exists, normalized."""
    for name in candidates:
        path = posixpath.normpath(name)
        if path in files:
            return path
    return None


def _bases(importer: str, imp: Import, roots: list[str]) -> list[str]:
    """Lists the folders an import is resolved from."""
    if imp.level:
        base = posixpath.dirname(importer)
        for _ in range(imp.level - 1):
            base = posixpath.dirname(base)
        return [base]
    return ["" if r in (".", "./", "") else r.strip("/") for r in roots]


def resolve(importer: str, imp: Import, roots: list[str], files: set[str]) -> list[str]:
    """Resolves an import to repository files.

    Args:
        importer: Path of the importing file.
        imp: The import statement.
        roots: [lang] source_roots.
        files: Every file at the head.

    Returns:
        The imported repository files; empty for a third-party import.
    """
    module_path = imp.module.replace(".", "/")
    for base in _bases(importer, imp, roots):
        prefix = posixpath.join(base, module_path) if module_path else base
        own = [prefix + ".py", posixpath.join(prefix, "__init__.py")] if module_path \
            else [posixpath.join(prefix, "__init__.py")]
        names = imp.names or [None]
        hits = [(_first([posixpath.join(prefix, n) + ".py",
                         posixpath.join(prefix, n, "__init__.py")], files) if n else None)
                or _first(own, files) for n in names]
        found = sorted({h for h in hits if h})
        if found:
            return found
    return []


def resolve_include(importer: str, target: str, include_dirs: list[str],
                    files: set[str]) -> str | None:
    """Resolves #include "target" to a repository file.

    Args:
        importer: Path of the including file.
        target: The path between the quotes.
        include_dirs: [lang] include_dirs, tried after the importer's folder.
        files: Every file at the head.

    Returns:
        The first existing repository file, or None for an outside header.
    """
    bases = [posixpath.dirname(importer)] + [d.strip("/") for d in include_dirs]
    for base in bases:
        path = posixpath.normpath(posixpath.join(base, target))
        if path in files:
            return path
    return None


def _targets(ctx: PrContext, path: str, text: str, files: set[str]) -> list[tuple[int, str]]:
    """Lists (line, imported repository file) for one file in the project's language.

    Raises:
        ParseError: A Python file cannot be parsed.
    """
    if ctx.config.lang.get("name") == "cpp":
        dirs = list(ctx.config.lang.get("include_dirs", []))
        found = [(line, resolve_include(path, name, dirs, files))
                 for line, name in scan_cpp(text).includes]
        return [(line, target) for line, target in found if target]
    roots = list(ctx.config.lang.get("source_roots", ["."]))
    return [(imp.line, target) for imp in analyze(text).imports
            for target in resolve(path, imp, roots, files)]


def _extensions(ctx: PrContext) -> tuple[str, ...]:
    """Returns the code file extensions of the project's language."""
    return EXTENSIONS if ctx.config.lang.get("name") == "cpp" else (".py",)


def _components(graph: dict[str, set[str]]) -> list[set[str]]:
    """Finds the groups of nodes that reach each other (cycles of two or more)."""
    reach = {n: set() for n in graph}
    for node in graph:
        stack = list(graph[node])
        while stack:
            nxt = stack.pop()
            if nxt not in reach[node] and nxt in graph:
                reach[node].add(nxt)
                stack.extend(graph[nxt])
    groups = {frozenset({n} | {m for m in reach[n] if n in reach.get(m, set())}) for n in graph}
    return [set(g) for g in groups if len(g) > 1 or next(iter(g)) in reach[next(iter(g))]]


def _table_fails(modules: list[Module]) -> list[Detail]:
    """Finds unknown module names and cycles in the declared dependencies."""
    names = {m.name for m in modules}
    fails = [Detail(ARCHITECTURE, None, f"{m.name} may depend on unknown module {d}")
             for m in modules for d in m.deps if d not in names]
    graph = {m.name: {d for d in m.deps if d in names} for m in modules}
    fails += [Detail(ARCHITECTURE, None, "May depend on forms a cycle: " + ", ".join(sorted(g)))
              for g in _components(graph)]
    return fails


def _import_edges(ctx: PrContext, modules: list[Module],
                  changed: set[str]) -> tuple[list, list[Detail]]:
    """Reads every import between modules at the head.

    Returns:
        (edges, fails): edges as (from, to, path, line, target) and parse
        failures of changed files.
    """
    files = set(list_files(ctx.repo, ctx.head, "."))
    owned = [p for p in sorted(files) if p.endswith(_extensions(ctx)) and module_of(p, modules)]
    edges, fails = [], []
    for path, text in read_blobs(ctx.repo, ctx.head, owned).items():
        source = module_of(path, modules)
        try:
            targets = _targets(ctx, path, text, files)
        except ParseError as exc:
            if path in changed:
                fails.append(Detail(path, None, f"cannot be parsed as Python: {exc}"))
            continue
        for line, target in targets:
            dest = module_of(target, modules)
            if dest is not None and dest.name != source.name:
                edges.append((source, dest, path, line, target))
    return edges, fails


def _edge_fails(edges: list, changed: set[str]) -> list[Detail]:
    """Checks imports from changed files against May depend on and External interfaces."""
    fails = []
    for source, dest, path, line, target in edges:
        if path not in changed:
            continue
        if dest.name not in source.deps:
            fails.append(Detail(path, line, f"module {source.name} may not depend on {dest.name}"))
        if not matches_any(target, dest.interfaces):
            fails.append(Detail(path, line, f"imports {target}, which is not an external "
                                            f"interface of {dest.name}"))
    return fails


def _cycle_fails(edges: list, changed: set[str]) -> list[Detail]:
    """Finds import cycles between modules that include an import from a changed file."""
    graph: dict[str, set[str]] = {}
    for source, dest, *_ in edges:
        graph.setdefault(source.name, set()).add(dest.name)
        graph.setdefault(dest.name, set())
    fails = []
    for group in _components(graph):
        inside = [e for e in edges if e[0].name in group and e[1].name in group and e[2] in changed]
        if inside:
            fails.append(Detail(inside[0][2], inside[0][3],
                                "import cycle between modules " + ", ".join(sorted(group))))
    return fails


def check_r07(ctx: PrContext) -> Result:
    """Checks module dependencies against the architecture's module table (R07).

    Args:
        ctx: The PR under check.

    Returns:
        SKIP without an adapter or a module table. FAIL for a forbidden
        dependency, an import of another module's internals, an unknown or
        cyclic declared dependency, or an import cycle through a changed file.
    """
    skip = lang_skip(ctx, "R07")
    if skip:
        return skip
    text = read_blob(ctx.repo, ctx.base, ARCHITECTURE)
    modules = parse_table(text) if text else None
    if not modules:
        return Result("R07", SKIP, f"No module table in {ARCHITECTURE}.")
    changed = {c.path for c in ctx.changes if c.status != "D" and c.path.endswith(_extensions(ctx))}
    edges, fails = _import_edges(ctx, modules, changed)
    fails = _table_fails(modules) + fails + _edge_fails(edges, changed) + _cycle_fails(edges, changed)
    if fails:
        return Result("R07", FAIL, f"{len(fails)} module dependency problems.", fails)
    checked = sum(1 for e in edges if e[2] in changed)
    return Result("R07", PASS, f"{checked} imports between modules from changed files follow the table.")
