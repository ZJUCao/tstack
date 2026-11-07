"""The install record, .troy-mode/install.toml (design section 4.6)."""

import json
import tomllib
from dataclasses import dataclass, field

from .errors import InitError

INSTALL_PATH = ".troy-mode/install.toml"
_HEADER = (
    "# troy-init's install record (F06 design 4.6). troy-init rewrites it at each\n"
    "# step. Upgrade compares the [files] hashes with the files, to tell a file\n"
    "# nobody changed from one someone edited. Do not edit it by hand.\n"
)


@dataclass
class Install:
    """What troy-init installed in a project.

    Attributes:
        version: The troy-pstack version of the last step.
        commit: The troy-pstack commit, when the plugin was a git checkout.
        steps: The date of each step by name: "setup", "lang", "upgrade".
        lang: The language pack, or None before the language step.
        files: SHA-256 (LF form) of every file troy-init owns, by path.
    """

    version: str
    commit: str | None = None
    steps: dict[str, str] = field(default_factory=dict)
    lang: str | None = None
    files: dict[str, str] = field(default_factory=dict)


def _string(value: str) -> str:
    """Quotes a TOML basic string; JSON's escapes are valid TOML."""
    return json.dumps(value, ensure_ascii=False)


def render(install: Install) -> str:
    """Writes the record as TOML text."""
    lines = [_HEADER, "[plugin]", f"version = {_string(install.version)}"]
    if install.commit:
        lines.append(f"commit = {_string(install.commit)}")
    lines += ["", "[steps]"]
    lines += [f"{name} = {_string(date)}" for name, date in install.steps.items()]
    if install.lang:
        lines += ["", "[lang]", f"name = {_string(install.lang)}"]
    lines += ["", "[files]"]
    lines += [f"{_string(path)} = {_string(digest)}" for path, digest in sorted(install.files.items())]
    return "\n".join(lines) + "\n"


def parse(text: str) -> Install:
    """Reads the record.

    Raises:
        InitError: The text is not valid TOML or lacks the plugin version.
    """
    try:
        data = tomllib.loads(text)
        files = data.get("files", {})
        version = data["plugin"]["version"]
    except (tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise InitError(f"{INSTALL_PATH} cannot be read: {exc}") from exc
    if not isinstance(files, dict) or not all(isinstance(v, str) for v in files.values()):
        raise InitError(f"{INSTALL_PATH} has a [files] table that is not path = hash")
    return Install(version=str(version), commit=data["plugin"].get("commit"),
                   steps=dict(data.get("steps", {})), lang=data.get("lang", {}).get("name"),
                   files=dict(files))
