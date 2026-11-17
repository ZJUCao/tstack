"""The tstack plugin that troy-init copies from (design sections 4.2 and 4.6)."""

import json
import os
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import InitError
from .packs import get_pack
from .workflow import append_job

CHECKS_DEST = ".troy-mode/checks"
TEMPLATES_DEST = ".troy-mode/templates"
HOOKS_DEST = ".troy-mode/checks/git-hooks"
WORKFLOW_DEST = ".github/workflows/troy-mode.yml"
PR_TEMPLATE_DEST = ".github/pull_request_template.md"
IDEA_TEMPLATE_DEST = ".github/ISSUE_TEMPLATE/idea.md"

# Top-level entries of troy-mode/checks/ that stay in tstack.
_CHECKS_LEFT_OUT = ("tests", "workflow.yml", "config.default.toml")
_CACHE_DIRS = ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
_CACHE_SUFFIXES = (".pyc", ".pyo")
# Packs in the order their patterns are listed in the config (design 4.3).
_PACK_ORDER = ("python", "cpp")


@dataclass(frozen=True)
class Plugin:
    """The plugin folder troy-init runs from.

    Attributes:
        root: The plugin's root folder, which holds .claude-plugin/.
        name: The name in .claude-plugin/plugin.json, which Claude Code puts
            before the plugin's commands and agents (F19 design 5.1).
        version: The version in .claude-plugin/plugin.json.
        commit: The checked-out commit when the root is a git checkout, else None.
    """

    root: Path
    name: str
    version: str
    commit: str | None

    @property
    def checks(self) -> Path:
        """troy-mode/checks/ in the plugin."""
        return self.root / "troy-mode" / "checks"

    @property
    def templates(self) -> Path:
        """troy-mode/templates/ in the plugin."""
        return self.root / "troy-mode" / "templates"

    @property
    def lang(self) -> Path:
        """troy-mode/lang/ in the plugin."""
        return self.root / "troy-mode" / "lang"

    @property
    def has_git_hooks(self) -> bool:
        """True when troy-check ships F05's git hooks."""
        return (self.checks / "git-hooks").is_dir()

    def text(self, relative: str) -> str:
        """Reads a plugin file as UTF-8 text with LF line endings.

        Raises:
            InitError: The file cannot be read.
        """
        path = self.root / relative
        try:
            return path.read_text(encoding="utf-8").replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError) as exc:
            raise InitError(f"cannot read the plugin file {path}: {exc}") from exc


def _git_commit(root: Path) -> str | None:
    """Returns the commit checked out at root, when root is a git checkout's top."""
    def run(*args: str) -> str | None:
        try:
            proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                  text=True, check=False)
        except OSError:
            return None
        return proc.stdout.strip() if proc.returncode == 0 else None

    top = run("rev-parse", "--show-toplevel")
    if not top or not os.path.samefile(top, root):
        return None
    return run("rev-parse", "HEAD")


def load_plugin(root: Path) -> Plugin:
    """Reads the plugin's name, version, and commit.

    Args:
        root: The plugin's root folder.

    Returns:
        The plugin.

    Raises:
        InitError: plugin.json is missing or has no name or no version.
    """
    manifest = root / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        name, version = data.get("name"), data["version"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise InitError(f"cannot read the plugin version from {manifest}: {exc}") from exc
    if not isinstance(version, str) or not version:
        raise InitError(f"{manifest} has no version")
    if not isinstance(name, str) or not name:
        raise InitError(f"{manifest} has no name")
    return Plugin(root, name, version, _git_commit(root))


def _files_under(folder: Path) -> list[str]:
    """Lists the files under a folder, relative with "/", without caches."""
    found = []
    for path in folder.rglob("*"):
        parts = path.relative_to(folder).parts
        if any(part in _CACHE_DIRS for part in parts) or path.suffix in _CACHE_SUFFIXES:
            continue
        if path.is_file():
            found.append("/".join(parts))
    return sorted(found)


def owned_sources(plugin: Plugin, lang: str | None = None) -> dict[str, Path]:
    """Maps each file troy-init owns in a project to its source in the plugin.

    troy-init owns the files it copies whole (design 4.6): troy-check with its
    git hooks, the templates, the PR template, the workflow, and the language
    pack's whole files. With a pack, the workflow also holds the pack's job;
    owned_contents() builds it.

    Args:
        plugin: The plugin.
        lang: The installed language pack, or None before the language step.

    Returns:
        Project paths with "/" separators, sorted, and their source files.
    """
    sources = {}
    for relative in _files_under(plugin.checks):
        if relative.split("/")[0] not in _CHECKS_LEFT_OUT:
            sources[f"{CHECKS_DEST}/{relative}"] = plugin.checks / relative
    for relative in _files_under(plugin.templates):
        sources[f"{TEMPLATES_DEST}/{relative}"] = plugin.templates / relative
    sources[WORKFLOW_DEST] = plugin.checks / "workflow.yml"
    sources[PR_TEMPLATE_DEST] = plugin.templates / "pull-request.md"
    sources[IDEA_TEMPLATE_DEST] = plugin.templates / "idea-issue.md"
    if lang:
        pack = get_pack(lang)
        for dest, name in pack.copied.items():
            sources[dest] = plugin.root / pack.source(name)
    return dict(sorted(sources.items()))


def pack_job(plugin: Plugin, lang: str) -> str:
    """The pack's CI job, workflow-job.yml, as text with LF endings."""
    return plugin.text(get_pack(lang).source("workflow-job.yml"))


def owned_contents(plugin: Plugin, lang: str | None = None) -> dict[str, bytes]:
    """Builds what each owned file holds when nobody edited it (design 4.6 and 6).

    Args:
        plugin: The plugin.
        lang: The installed language pack, or None before the language step.

    Returns:
        Project paths, sorted, and their LF bytes. With a pack, the workflow
        is F02's workflow with the pack's job added under jobs:.

    Raises:
        InitError: A plugin file cannot be read.
    """
    contents = {path: read_source(source) for path, source in owned_sources(plugin, lang).items()}
    if lang:
        base = contents[WORKFLOW_DEST].decode("utf-8")
        contents[WORKFLOW_DEST] = append_job(base, pack_job(plugin, lang)).encode("utf-8")
    return contents


def read_source(path: Path) -> bytes:
    """Reads a file to copy, with CRLF turned into LF (every copied file is text).

    Raises:
        InitError: The file cannot be read.
    """
    try:
        return path.read_bytes().replace(b"\r\n", b"\n")
    except OSError as exc:
        raise InitError(f"cannot read the plugin file {path}: {exc}") from exc


def pack_names(plugin: Plugin) -> list[str]:
    """Lists the language packs in the plugin, in config order."""
    found = sorted(p.parent.name for p in plugin.lang.glob("*/config.toml"))
    return [n for n in _PACK_ORDER if n in found] + [n for n in found if n not in _PACK_ORDER]


def pack_patterns(plugin: Plugin) -> dict[str, list[str]]:
    """Collects the [paths] patterns of every language pack (design 4.3, D49).

    Args:
        plugin: The plugin.

    Returns:
        Pattern lists by key, in pack order, without duplicates.

    Raises:
        InitError: A pack's config.toml cannot be read.
    """
    merged: dict[str, list[str]] = {}
    for name in pack_names(plugin):
        relative = f"troy-mode/lang/{name}/config.toml"
        try:
            paths = tomllib.loads(plugin.text(relative)).get("paths", {})
        except tomllib.TOMLDecodeError as exc:
            raise InitError(f"{relative} is not valid TOML: {exc}") from exc
        for key, patterns in paths.items():
            bucket = merged.setdefault(key, [])
            bucket.extend(p for p in patterns if p not in bucket)
    return merged
