"""The troy-pstack plugin that troy-init copies from (design sections 4.2 and 4.6)."""

import json
import os
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import InitError

CHECKS_DEST = ".troy-mode/checks"
TEMPLATES_DEST = ".troy-mode/templates"
HOOKS_DEST = ".troy-mode/checks/git-hooks"
WORKFLOW_DEST = ".github/workflows/troy-mode.yml"
PR_TEMPLATE_DEST = ".github/pull_request_template.md"

# Top-level entries of troy-mode/checks/ that stay in troy-pstack.
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
        version: The version in .claude-plugin/plugin.json.
        commit: The checked-out commit when the root is a git checkout, else None.
    """

    root: Path
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
    """Reads the plugin's version and commit.

    Args:
        root: The plugin's root folder.

    Returns:
        The plugin.

    Raises:
        InitError: plugin.json is missing or has no version.
    """
    manifest = root / ".claude-plugin" / "plugin.json"
    try:
        version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise InitError(f"cannot read the plugin version from {manifest}: {exc}") from exc
    if not isinstance(version, str) or not version:
        raise InitError(f"{manifest} has no version")
    return Plugin(root, version, _git_commit(root))


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


def owned_sources(plugin: Plugin) -> dict[str, Path]:
    """Maps each file troy-init owns in a project to its source in the plugin.

    troy-init owns the files it copies whole (design 4.6): troy-check with its
    git hooks, the templates, the PR template, and the workflow.

    Args:
        plugin: The plugin.

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
    return dict(sorted(sources.items()))


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
