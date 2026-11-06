"""The project config file, .troy-mode/config.toml (design section 7).

Every key is optional. Path lists add to the built-in patterns and never
replace them. An unknown key or a wrong type is an error, so a typo never
turns a rule off silently.
"""

import tomllib
from dataclasses import dataclass

CONFIG_PATH = ".troy-mode/config.toml"

BUILTIN_PATHS: dict[str, list[str]] = {
    "config": [".troy-mode/**", ".github/**", "docs/rules.md", "docs/rules.zh-CN.md",
               ".gitignore", ".gitattributes", ".editorconfig"],
    "dependencies": [],
    "tests": ["tests/**", "test/**"],
    "docs": ["docs/**", "**/*.md", "LICENSE*"],
    "lock": [],
    "generated": [],
    "allow_markers": [],
}

ATTRIBUTION_MODES = ("strict", "trailers")

_SCHEMA: dict[str, dict[str, type]] = {
    "identity": {"commit_email": str},
    "paths": {key: list for key in BUILTIN_PATHS},
    "limits": {"source_lines": int, "source_files": int},
    "attribution": {"mode": str},
}


class ConfigError(Exception):
    """Raised when the config file cannot be read or breaks the schema."""


@dataclass
class Config:
    """Settings for one run of the checks.

    Attributes:
        commit_email: The only allowed author email (R19), or None if unset.
        paths: Pattern lists by name: the five path classes plus "lock",
            "generated", and "allow_markers". Built-in patterns come first.
        source_lines: R03 limit on changed lines in a source PR.
        source_files: R03 limit on changed files in a source PR.
        attribution_mode: "strict" or "trailers" (R19).
    """

    commit_email: str | None
    paths: dict[str, list[str]]
    source_lines: int
    source_files: int
    attribution_mode: str


def _check_value(section: str, key: str, value, expected: type) -> None:
    """Raises ConfigError if one config value has the wrong type."""
    name = f"[{section}] {key}"
    if expected is int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ConfigError(f"{name} must be a positive whole number")
    elif expected is list:
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ConfigError(f"{name} must be a list of strings")
    elif not isinstance(value, expected):
        raise ConfigError(f"{name} must be a string")


def _validate(data: dict) -> None:
    """Raises ConfigError for unknown sections or keys and wrong types."""
    for section, values in data.items():
        if section not in _SCHEMA:
            raise ConfigError(f"unknown section [{section}]")
        if not isinstance(values, dict):
            raise ConfigError(f"[{section}] must be a table")
        for key, value in values.items():
            if key not in _SCHEMA[section]:
                raise ConfigError(f"unknown key {key!r} in [{section}]")
            _check_value(section, key, value, _SCHEMA[section][key])
    mode = data.get("attribution", {}).get("mode", "strict")
    if mode not in ATTRIBUTION_MODES:
        raise ConfigError(f"[attribution] mode must be one of {', '.join(ATTRIBUTION_MODES)}")


def parse_config(text: str | None) -> Config:
    """Builds the settings from the config file's text.

    Args:
        text: Contents of .troy-mode/config.toml, or None when the file does
            not exist. A missing file means all built-in defaults.

    Returns:
        The settings.

    Raises:
        ConfigError: The text is not valid TOML or breaks the schema.
    """
    try:
        data = tomllib.loads(text or "")
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{CONFIG_PATH} is not valid TOML: {exc}") from exc
    _validate(data)
    extra = data.get("paths", {})
    paths = {key: BUILTIN_PATHS[key] + list(extra.get(key, [])) for key in BUILTIN_PATHS}
    limits = data.get("limits", {})
    return Config(
        commit_email=data.get("identity", {}).get("commit_email"),
        paths=paths,
        source_lines=limits.get("source_lines", 500),
        source_files=limits.get("source_files", 5),
        attribution_mode=data.get("attribution", {}).get("mode", "strict"),
    )
