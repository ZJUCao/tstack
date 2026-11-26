"""The project config file, .troy-mode/config.toml (design section 7).

Every key is optional. Path lists add to the built-in patterns and never
replace them. An unknown key or a wrong type is an error, so a typo never
turns a rule off silently.
"""

import tomllib
from dataclasses import dataclass, field

CONFIG_PATH = ".troy-mode/config.toml"

BUILTIN_PATHS: dict[str, list[str]] = {
    "config": [".troy-mode/**", ".github/**", "docs/rules.md", "docs/rules.zh-CN.md",
               ".gitignore", ".gitattributes", ".editorconfig"],
    "dependencies": [],
    "tests": ["tests/**", "test/**", "version-tests/**"],
    "docs": ["docs/**", "**/*.md", "LICENSE*"],
    "lock": [],
    "generated": [],
    "allow_markers": [],
}

ATTRIBUTION_MODES = ("strict", "trailers")
LANGUAGES = ("python", "cpp")
# The roles that [roles.<role>] may set, and the efforts the Agent tool takes
# (F04 design D32, F07 design 3.2).
ROLES = ("architect", "interface-designer", "test-manager", "developer", "test-engineer",
         "code-reviewer")
ROLE_KEYS = ("model", "effort")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
APPROVES_FIRST_DEFAULT = 3
# F18 D176, D179: one feature in this many after the approved ones is a spot check.
SPOT_CHECK_EVERY_DEFAULT = 3
# R22: the most characters in each language of the summary for Troy (F14 design 3.3).
SUMMARY_MAX_CHARS_DEFAULT = 2000
# How many days hooks.log keeps its lines (F05 design D219).
HOOKS_LOG_DAYS_DEFAULT = 30

LIMIT_DEFAULTS = {
    "source_lines": 500,
    "source_files": 5,
    "line_coverage": 90,
    "branch_coverage": 80,
    "function_lines": 50,
    "file_lines": 500,
}

_SCHEMA: dict[str, dict[str, type]] = {
    "identity": {"commit_email": str},
    "paths": {key: list for key in BUILTIN_PATHS},
    "limits": {key: int for key in LIMIT_DEFAULTS},
    "attribution": {"mode": str},
    "tests": {"legacy": list},
    "lang": {"name": str, "source_roots": list, "include_dirs": list, "environment": str,
             "series": list},
    "summary": {"max_chars": int},
    "hooks": {"log_days": int},
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
        limits: Every limit by name, defaults filled in (R03, R04, R06, R11).
        legacy_tests: Patterns for test files allowed to carry no ID (R10).
        lang: The [lang] table as written, for the language adapters.
        roles: The [roles.<role>] tables as written: model and effort by
            role, for troy-mode's entry skill (F07 design 3.2).
        troy_approves_first: [flow] troy_approves_first, the number of
            features whose PR 1 and PR 2 Troy approves (F07 design D62).
        spot_checks: [flow] spot_checks, whether spot checks replace Troy's
            approvals of later PR 1 and PR 2 (F18 design D179).
        spot_check_every: [flow] spot_check_every, one feature in this many
            after the approved ones is sampled (F18 design D176).
        summary_max_chars: [summary] max_chars, R22's limit on each language
            of the summary for Troy (F14 design 3.3).
        hooks_log_days: [hooks] log_days, how many days the hooks' log keeps
            its lines (F05 design D219).
    """

    commit_email: str | None
    paths: dict[str, list[str]]
    source_lines: int
    source_files: int
    attribution_mode: str
    limits: dict[str, int] = field(default_factory=lambda: dict(LIMIT_DEFAULTS))
    legacy_tests: list[str] = field(default_factory=list)
    lang: dict = field(default_factory=dict)
    roles: dict[str, dict[str, str]] = field(default_factory=dict)
    troy_approves_first: int = APPROVES_FIRST_DEFAULT
    spot_checks: bool = False
    spot_check_every: int = SPOT_CHECK_EVERY_DEFAULT
    summary_max_chars: int = SUMMARY_MAX_CHARS_DEFAULT
    hooks_log_days: int = HOOKS_LOG_DAYS_DEFAULT


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


def _validate_roles(roles) -> None:
    """Raises ConfigError for a [roles] table that breaks F07 design 3.2."""
    if not isinstance(roles, dict):
        raise ConfigError("[roles] must be a table")
    for role, values in roles.items():
        if role not in ROLES or not isinstance(values, dict):
            raise ConfigError(f"unknown role {role!r} in [roles]; roles are {', '.join(ROLES)}")
        for key, value in values.items():
            if key not in ROLE_KEYS:
                raise ConfigError(f"unknown key {key!r} in [roles.{role}]")
            if not isinstance(value, str) or not value.strip():
                raise ConfigError(f"[roles.{role}] {key} must be a string that is not empty")
        effort = values.get("effort")
        if effort is not None and effort not in EFFORTS:
            raise ConfigError(f"[roles.{role}] effort must be one of {', '.join(EFFORTS)}")


def _whole(value) -> bool:
    """Tells whether a TOML value is a whole number, not a boolean."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_flow(flow) -> None:
    """Raises ConfigError for a [flow] table that breaks F07 design D62 or F18 design D179."""
    if not isinstance(flow, dict):
        raise ConfigError("[flow] must be a table")
    for key, value in flow.items():
        if key == "troy_approves_first":
            if not _whole(value) or value < 0:
                raise ConfigError("[flow] troy_approves_first must be a whole number of 0 or more")
        elif key == "spot_checks":
            if not isinstance(value, bool):
                raise ConfigError("[flow] spot_checks must be true or false")
        elif key == "spot_check_every":
            if not _whole(value) or value < 2:
                raise ConfigError("[flow] spot_check_every must be a whole number of 2 or more")
        else:
            raise ConfigError(f"unknown key {key!r} in [flow]")


def _validate(data: dict) -> None:
    """Raises ConfigError for unknown sections or keys and wrong types."""
    for section, values in data.items():
        if section == "roles":
            _validate_roles(values)
            continue
        if section == "flow":
            _validate_flow(values)
            continue
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
    name = data.get("lang", {}).get("name")
    if name is not None and name not in LANGUAGES:
        raise ConfigError(f"[lang] name must be one of {', '.join(LANGUAGES)}")


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
    flow = data.get("flow", {})
    paths = {key: BUILTIN_PATHS[key] + list(extra.get(key, [])) for key in BUILTIN_PATHS}
    limits = {**LIMIT_DEFAULTS, **data.get("limits", {})}
    return Config(
        commit_email=data.get("identity", {}).get("commit_email"),
        paths=paths,
        source_lines=limits["source_lines"],
        source_files=limits["source_files"],
        attribution_mode=data.get("attribution", {}).get("mode", "strict"),
        limits=limits,
        legacy_tests=list(data.get("tests", {}).get("legacy", [])),
        lang=dict(data.get("lang", {})),
        roles={role: dict(values) for role, values in data.get("roles", {}).items()},
        troy_approves_first=flow.get("troy_approves_first", APPROVES_FIRST_DEFAULT),
        spot_checks=flow.get("spot_checks", False),
        spot_check_every=flow.get("spot_check_every", SPOT_CHECK_EVERY_DEFAULT),
        summary_max_chars=data.get("summary", {}).get("max_chars", SUMMARY_MAX_CHARS_DEFAULT),
        hooks_log_days=data.get("hooks", {}).get("log_days", HOOKS_LOG_DAYS_DEFAULT),
    )
