"""Where a project's own pack files differ from the plugin's pack (design section 6).

Upgrade never changes the config's [lang] table, environment.yml, the
appended pyproject.toml tables, CMakeLists.txt, or requirements-tools.in:
they belong to the project once written. It only reports where they differ
from the pack tstack would install now, for Troy to take into a rules PR.
"""

import tomllib
from collections.abc import Iterator
from pathlib import Path

from .lang import CMAKE_INCLUDE, INCLUDE_LINE, project_text
from .packs import Pack, get_pack
from .plugin import Plugin
from .setup import CONFIG_PATH


def _flatten(data: dict, prefix: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], object]]:
    """Yields every leaf of a TOML table with its dotted key path."""
    for key, value in data.items():
        if isinstance(value, dict):
            yield from _flatten(value, (*prefix, key))
        else:
            yield (*prefix, key), value


def _lookup(data: dict, path: tuple[str, ...]) -> object:
    """Returns the value at a dotted key path, or None when it is missing."""
    node: object = data
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def _lang_table(plugin: Plugin, pack: Pack, config: dict) -> list[tuple[str, str]]:
    """Compares the config's [lang] keys that the pack sets, other than the project's own."""
    environment = str(config.get("lang", {}).get("environment", ""))
    text = plugin.text(pack.source("config.toml")).replace("{{environment}}", environment)
    wanted = tomllib.loads(text).get("lang", {})
    have = config.get("lang", {})
    keys = [k for k, v in wanted.items() if k not in ("environment", "series") and have.get(k) != v]
    if not keys:
        return []
    return [(CONFIG_PATH, f"[lang] {', '.join(keys)} differ from {plugin.name}'s {pack.title} "
                          f"pack {plugin.version}.")]


def _filled_files(plugin: Plugin, repo: Path, pack: Pack, environment: str) -> list[tuple]:
    """Compares environment.yml and requirements-tools.in with the pack's files."""
    found = []
    for dest, name in pack.filled.items():
        wanted = plugin.text(pack.source(name)).replace("{{environment}}", environment)
        have = project_text(repo, dest)
        if have is None:
            found.append((dest, "is missing."))
        elif dest.endswith(".in"):
            lines = {line.strip() for line in have.split("\n")}
            missing = [line.strip() for line in wanted.split("\n")
                       if line.strip() and not line.startswith("#") and line.strip() not in lines]
            if missing:
                found.append((dest, f"lacks {', '.join(missing)}, which {plugin.name}'s pack "
                                    f"{plugin.version} lists."))
        elif have != wanted:
            found.append((dest, f"differs from {plugin.name}'s {pack.title} pack {plugin.version}."))
    return found


def _build_file(plugin: Plugin, repo: Path, pack: Pack) -> list[tuple[str, str]]:
    """Compares the project's build file with what the pack needs from it."""
    have = project_text(repo, pack.build_file)
    if have is None:
        return [(pack.build_file, "is missing.")]
    if pack.name == "cpp":
        if CMAKE_INCLUDE.search(have):
            return []
        return [(pack.build_file, f"does not include the C/C++ pack: {INCLUDE_LINE}")]
    try:
        data = tomllib.loads(have)
    except tomllib.TOMLDecodeError as exc:
        return [(pack.build_file, f"cannot be read: {exc}")]
    wanted = tomllib.loads(plugin.text(pack.source("pyproject.toml")))
    keys = [".".join(path) for path, value in _flatten(wanted) if _lookup(data, path) != value]
    if not keys:
        return []
    return [(pack.build_file, f"{', '.join(keys)} differ from {plugin.name}'s Python pack "
                              f"{plugin.version}.")]


def pack_differences(plugin: Plugin, repo: Path, lang: str) -> list[tuple[str, str]]:
    """Lists where the project's own pack files differ from the plugin's pack.

    Args:
        plugin: The plugin.
        repo: The project's root.
        lang: The installed pack.

    Returns:
        (path, message) pairs, empty when nothing differs.
    """
    pack = get_pack(lang)
    try:
        config = tomllib.loads(project_text(repo, CONFIG_PATH) or "")
    except tomllib.TOMLDecodeError:
        config = {}
    environment = str(config.get("lang", {}).get("environment", ""))
    return (_lang_table(plugin, pack, config) + _filled_files(plugin, repo, pack, environment)
            + _build_file(plugin, repo, pack))
