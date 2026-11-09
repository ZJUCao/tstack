"""The language step: the language pack and its CI job (design section 5).

lang_files() builds every file the step writes, without the preconditions of
section 5.1, so troy-pstack's build_sample.py sets its samples up exactly as
troy-init sets up a project (design section 8). plan_lang() adds the
preconditions, the conflicts, and the environment work of section 5.4.
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .checkslib import matches_any, parse_header, version_key
from .env import EnvPlan, plan_env
from .errors import InitError
from .fill import add_lines, check_filled, fill_lang
from .gitops import current_branch, git, is_root, ref_exists
from .install import INSTALL_PATH, Install, parse, render
from .packs import Pack, get_pack
from .plan import (
    FileAction, Plan, edited_bytes, exists, file_hash, lf_bytes, read_project_file,
)
from .plugin import WORKFLOW_DEST, Plugin, pack_job, read_source
from .setup import CONFIG_PATH, GITIGNORE
from .workflow import append_job, workflow_problems

ARCHITECTURE = "docs/architecture.md"
_TABLE = re.compile(r"^\[([^\[\]]+)\][ \t]*$", re.MULTILINE)
CMAKE_INCLUDE = re.compile(
    r'^[ \t]*include[ \t]*\([ \t]*"?(?:\$\{CMAKE_(?:CURRENT_)?SOURCE_DIR\}/)?cmake/troy\.cmake"?'
    r"[ \t]*\)", re.IGNORECASE | re.MULTILINE)
INCLUDE_LINE = "include(cmake/troy.cmake)"


@dataclass
class LangOptions:
    """What the language step fills in.

    Attributes:
        language: The pack, "python" or "cpp".
        project: The project's name, for a new build file.
        environment: The series environment's name.
        series: The series' member folders, this project as ".".
        package: Python only: the package under src/.
        date: The date written into the install record.
        replace: Paths the step may overwrite although it did not write them.
        no_env: Create no environment and compile no lock.
        env_prefix: Create the environment in this folder, not a named one.
        mamba: The --mamba value, or None.
    """

    language: str
    project: str
    environment: str
    series: list[str]
    package: str | None
    date: str
    replace: list[str] = field(default_factory=list)
    no_env: bool = False
    env_prefix: str | None = None
    mamba: str | None = None


@dataclass
class LangFiles:
    """The language step's files and what is in their way.

    Attributes:
        actions: One action per file, sorted by path.
        problems: Files whose content stops the step (design 5.2 and 5.3).
        legacy: Existing test files listed in [tests] legacy (design 5.5).
    """

    actions: list[FileAction]
    problems: list[str]
    legacy: list[str]


def project_text(repo: Path, path: str) -> str | None:
    """Reads a project file as LF text, or None when it does not exist."""
    raw = read_project_file(repo, path)
    return None if raw is None else raw.decode("utf-8", "replace").replace("\r\n", "\n")


def _edited(repo: Path, path: str, text: str) -> bytes:
    """The bytes of a project file's new text, in the line endings it has now."""
    return edited_bytes(text, read_project_file(repo, path))


def _pack_config(plugin: Plugin, pack: Pack, options: LangOptions) -> dict:
    """The pack's config fragment, with the environment and series filled in."""
    relative = pack.source("config.toml")
    text = plugin.text(relative).replace("{{environment}}", options.environment)
    try:
        data = tomllib.loads(check_filled(text, relative))
    except tomllib.TOMLDecodeError as exc:
        raise InitError(f"{relative} is not valid TOML: {exc}") from exc
    values = dict(data.get("lang", {}))
    values["environment"], values["series"] = options.environment, list(options.series)
    return {"lang": values, "tests": data.get("paths", {}).get("tests", [])}


def existing_tests(repo: Path, patterns: list[str]) -> list[str]:
    """Lists the project's test files that match the pack's patterns (design 5.5).

    Args:
        repo: The project's root.
        patterns: The pack's [paths] tests patterns.

    Returns:
        Tracked and untracked, not ignored, files outside .troy-mode/, sorted.
    """
    out = git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z").stdout
    paths = {p for p in out.split("\0") if p and not p.startswith(".troy-mode/")}
    return sorted(p for p in paths if matches_any(p, patterns))


def _config_action(repo: Path, values: dict, legacy: list[str]) -> tuple[FileAction | None, list]:
    """Fills the config's [lang] table and [tests] legacy."""
    text = project_text(repo, CONFIG_PATH)
    if text is None:
        return None, [f"{CONFIG_PATH} is missing. Run setup first."]
    text = fill_lang(text, values, legacy)
    return FileAction(CONFIG_PATH, "edit", _edited(repo, CONFIG_PATH, text)), []


def _held_tables(text: str, fragment: str) -> list[str]:
    """The fragment's tables that a pyproject.toml text already holds."""
    data = tomllib.loads(text)
    held = []
    for name in _TABLE.findall(fragment):
        node = data
        for key in name.strip().split("."):
            node = node.get(key.strip()) if isinstance(node, dict) else None
        if node is not None:
            held.append(f"[{name.strip()}]")
    return held


def _pyproject_action(plugin: Plugin, repo: Path, pack: Pack,
                      options: LangOptions) -> tuple[FileAction | None, list]:
    """Creates pyproject.toml, or appends the pack's tables to it (design 5.2)."""
    tables = plugin.text(pack.source("pyproject.toml"))
    current = project_text(repo, pack.build_file)
    if current is None:
        start = plugin.text(pack.source(pack.new_build_file))
        start = start.replace("{{project-name}}", options.project)
        start = check_filled(start.replace("{{package}}", options.package or ""),
                             pack.new_build_file)
        first, action = start, "create"
    else:
        try:
            held = _held_tables(current, tables)
        except tomllib.TOMLDecodeError as exc:
            return None, [f"pyproject.toml is not valid TOML: {exc}"]
        if held:
            return None, [f"pyproject.toml already holds {', '.join(held)}, which the Python "
                          "pack adds. Move those settings out, or merge them by hand."]
        first, action = current, "append"
    text = first.rstrip("\n") + "\n\n" + tables
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return None, [f"pyproject.toml would not be valid TOML with the pack's tables: {exc}"]
    return FileAction(pack.build_file, action, _edited(repo, pack.build_file, text)), []


def _cmake_action(plugin: Plugin, repo: Path, pack: Pack,
                  options: LangOptions) -> tuple[FileAction | None, list]:
    """Creates CMakeLists.txt, or checks that it includes the pack (design 5.3)."""
    current = project_text(repo, pack.build_file)
    if current is None:
        text = plugin.text(pack.source(pack.new_build_file))
        text = check_filled(text.replace("{{project-name}}", options.project),
                            pack.new_build_file)
        return FileAction(pack.build_file, "create", lf_bytes(text)), []
    if CMAKE_INCLUDE.search(current):
        return FileAction(pack.build_file, "keep"), []
    return None, [f"CMakeLists.txt does not include the C/C++ pack. Add this line right after "
                  f"project(): {INCLUDE_LINE}"]


def _workflow_action(plugin: Plugin, repo: Path, pack: Pack) -> tuple[FileAction | None, list]:
    """Adds the pack's job under jobs: in the workflow."""
    current = project_text(repo, WORKFLOW_DEST)
    if current is None:
        return None, [f"{WORKFLOW_DEST} is missing. Run upgrade to bring it back."]
    problems = [f"{WORKFLOW_DEST} {p}" for p in workflow_problems(current)]
    if problems:
        return None, problems
    text = append_job(current, pack_job(plugin, pack.name))
    return FileAction(WORKFLOW_DEST, "edit", _edited(repo, WORKFLOW_DEST, text)), []


def _pack_files(plugin: Plugin, pack: Pack, options: LangOptions) -> list[FileAction]:
    """The pack's files that are filled in or copied whole."""
    actions = []
    for dest, name in pack.filled.items():
        text = plugin.text(pack.source(name)).replace("{{environment}}", options.environment)
        actions.append(FileAction(dest, "create", lf_bytes(check_filled(text, name))))
    for dest, name in pack.copied.items():
        actions.append(FileAction(dest, "create", read_source(plugin.root / pack.source(name)),
                                  owned=True))
    if not options.no_env:
        actions.append(FileAction(pack.lock, "create", generated=True))
    return actions


def _gitignore_action(repo: Path, pack: Pack) -> FileAction:
    """Adds the pack's lines to .gitignore."""
    text, action = add_lines(project_text(repo, GITIGNORE), list(pack.gitignore))
    content = None if action == "keep" else _edited(repo, GITIGNORE, text)
    return FileAction(GITIGNORE, action, content)


def _install_action(plugin: Plugin, repo: Path, pack: Pack, actions: list[FileAction],
                    date: str) -> tuple[FileAction | None, list]:
    """Records the step, the pack, and the hashes of the files it owns (design 4.6)."""
    raw = read_project_file(repo, INSTALL_PATH)
    if raw is None:
        return None, [f"{INSTALL_PATH} is missing. Run setup first."]
    install = parse(raw.decode("utf-8", "replace"))
    files = dict(install.files)
    current = read_project_file(repo, WORKFLOW_DEST)
    # An edited workflow keeps its old hash, so upgrade still sees the edit.
    unedited = current is not None and file_hash(current) == files.get(WORKFLOW_DEST)
    for item in actions:
        if item.owned or (item.path == WORKFLOW_DEST and unedited):
            files[item.path] = file_hash(item.content or b"")
    record = Install(plugin.version, plugin.commit, {**install.steps, "lang": date}, pack.name,
                     files)
    return FileAction(INSTALL_PATH, "edit", edited_bytes(render(record), raw)), []


def lang_files(plugin: Plugin, repo: Path, options: LangOptions) -> LangFiles:
    """Builds every file the language step writes, without the preconditions of 5.1.

    Args:
        plugin: The plugin to copy from.
        repo: The project's root, after setup.
        options: The language, names, and series to fill in.

    Returns:
        The actions, the problems found in the project's own files, and the
        existing tests listed as legacy.

    Raises:
        InitError: A plugin file cannot be read, or the config cannot be filled.
    """
    pack = get_pack(options.language)
    values = _pack_config(plugin, pack, options)
    legacy = existing_tests(repo, values["tests"])
    build = _pyproject_action if pack.name == "python" else _cmake_action
    results = [_config_action(repo, values["lang"], legacy),
               build(plugin, repo, pack, options), _workflow_action(plugin, repo, pack)]
    actions = [a for a, _ in results if a] + _pack_files(plugin, pack, options)
    actions.append(_gitignore_action(repo, pack))
    problems = [p for _, found in results for p in found]
    if not problems:
        record, found = _install_action(plugin, repo, pack, actions, options.date)
        problems += found
        actions += [record] if record else []
    return LangFiles(sorted(actions, key=lambda a: a.path), problems, legacy)


def _architecture_problem(repo: Path) -> str | None:
    """Checks that Troy approved the architecture on origin/main (design 5.1)."""
    if not ref_exists(repo, "refs/remotes/origin/main"):
        return "origin/main does not exist here. Run git fetch origin first."
    proc = git(repo, "show", f"origin/main:{ARCHITECTURE}", check=False)
    if proc.returncode != 0:
        return (f"{ARCHITECTURE} is not on origin/main yet. The language step comes after Troy "
                "approves the architecture.")
    header = parse_header(proc.stdout)
    version = header.fields.get("version") if header else None
    key = version_key(version or "")
    if key is None or key < (1, 0):
        return (f"{ARCHITECTURE} on origin/main has version {version!r}. Troy approves it by "
                "raising it to 1.0; the language step waits for that.")
    return None


def _installed_pack(repo: Path) -> str | None:
    """Names the pack already installed, from the install record or the config."""
    raw = read_project_file(repo, INSTALL_PATH)
    install = parse(raw.decode("utf-8", "replace")) if raw is not None else None
    if install and install.lang:
        return install.lang
    text = project_text(repo, CONFIG_PATH)
    try:
        lang = tomllib.loads(text).get("lang", {}) if text else {}
    except tomllib.TOMLDecodeError as exc:
        raise InitError(f"{CONFIG_PATH} is not valid TOML: {exc}") from exc
    return str(lang.get("name", "unnamed")) if lang else None


def lang_problems(repo: Path, top: Path) -> list[str]:
    """Checks the preconditions of design section 5.1.

    Args:
        repo: The folder troy-init runs on.
        top: The root of the git repository that holds it.

    Returns:
        One message per condition that does not hold.
    """
    if not is_root(repo, top):
        return [f"{repo} is not the root of its git repository ({top}). Run troy-init there."]
    problems = []
    if not exists(repo, INSTALL_PATH):
        problems.append(f"This project is not set up: {INSTALL_PATH} is missing. Run setup "
                        "first.")
    else:
        installed = _installed_pack(repo)
        if installed:
            problems.append(f"This project already has a language pack ({installed}). A "
                            "project has one pack.")
    architecture = _architecture_problem(repo)
    if architecture:
        problems.append(architecture)
    if current_branch(repo) == "main":
        problems.append("The current branch is main. Create the branch first: "
                        "git switch -c troy-mode/lang-<name> origin/main")
    return problems


def _conflicts(repo: Path, actions: list[FileAction], replace: list[str]) -> list[tuple[str, str]]:
    """Finds existing files the step would create, and lets --replace ones through."""
    conflicts = []
    for item in actions:
        if item.action != "create" or not exists(repo, item.path):
            continue
        if item.path in replace:
            item.action = "replace"
        else:
            conflicts.append((item.path, "exists, and troy-init did not write it. Name it with "
                                         "--replace to overwrite it."))
    return conflicts


def _report_parts(plan: Plan, pack: Pack, env: EnvPlan, legacy: list[str]) -> None:
    """Adds the language step's report keys, notes, and next steps."""
    plan.extra = {"language": pack.name, "legacy": list(legacy), "environment": env.to_dict()}
    if legacy:
        plan.notes.append(f"{len(legacy)} existing test files are listed in [tests] legacy, so "
                          "R10 does not fail their names. They must still pass.")
    if env.skipped:
        plan.notes.append("--no-env: no environment was created and no lock compiled.")
    elif env.mamba and env.exists is not None:
        where = env.prefix or env.name
        plan.notes.append(f"The environment {where} " + ("exists; the step compiles and installs "
                          "the lock." if env.exists else "is created, then the lock is compiled "
                          "and installed."))
    plan.next_steps += [
        "Stage exactly the paths in stage.",
        f"Commit once with the subject {pack.commit_title}, run troy_check.py pr, push the "
        "branch, and open the PR.",
        "The steps that need code (uv pip install -e . --no-deps, cmake --preset coverage) "
        "wait for the first mock.",
    ]


def plan_lang(plugin: Plugin, repo: Path, top: Path, options: LangOptions) -> Plan:
    """Plans the language step without changing the project.

    Args:
        plugin: The plugin to copy from.
        repo: The folder troy-init runs on.
        top: The root of the git repository that holds it.
        options: What the step fills in.

    Returns:
        The plan, with plan.env holding the environment work. It is blocked
        when a precondition fails or a file conflicts.

    Raises:
        InitError: A plugin file cannot be read, or mamba cannot list its
            environments.
    """
    plan = Plan("lang", plugin.version)
    pack = get_pack(options.language)
    plan.env = env = EnvPlan(options.environment, options.env_prefix, list(options.series),
                             pack.lock, options.no_env)
    plan.problems = lang_problems(repo, top)
    legacy: list[str] = []
    if not plan.problems:
        files = lang_files(plugin, repo, options)
        plan.actions, legacy = files.actions, files.legacy
        plan.problems += files.problems
        plan.conflicts = _conflicts(repo, plan.actions, options.replace)
    plan.problems += plan_env(pack, repo, env, options.mamba, look=not plan.blocked)
    _report_parts(plan, pack, env, legacy)
    return plan
