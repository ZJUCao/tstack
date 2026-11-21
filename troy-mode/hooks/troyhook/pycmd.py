"""R23: Python that reads its program from standard input (design section 8.3, D223).

The check reads only a command's words. shell.py has already removed the
wrappers, timeout among them, and marked a command that came through xargs.
This module removes the runners mamba, micromamba, conda, uv, and pixi run,
then reads Python's arguments left to right.
"""

import re

from .shell import program
from .verdict import Refusal

RULE = "python-stdin"
_PYTHON = re.compile(r"^(?:python(?:3(?:\.\d+)?)?|py)$")
# Each runner's options that take the next word as their value.
_CONDA = frozenset({"-n", "--name", "-p", "--prefix", "--cwd"})
_MAMBA = _CONDA | {"-a", "--attach", "--label", "-e", "--env", "-r", "--root-prefix", "--rc-file"}
_RUNNERS = {
    "conda": _CONDA,
    "mamba": _MAMBA,
    "micromamba": _MAMBA,
    "uv": frozenset({"--with", "--with-editable", "--with-requirements", "-p", "--python",
                     "--directory", "--project", "--env-file", "--extra", "--group", "--no-group",
                     "--only-group", "--package", "--index", "--default-index", "-i", "--index-url",
                     "--extra-index-url", "-f", "--find-links", "--index-strategy",
                     "--keyring-provider", "--resolution", "--prerelease", "--exclude-newer",
                     "--link-mode", "-C", "--config-setting", "-P", "--upgrade-package",
                     "--reinstall-package", "--refresh-package", "--no-binary-package",
                     "--no-build-package", "--python-platform", "--cache-dir", "--config-file",
                     "--color", "--allow-insecure-host"}),
    "pixi": frozenset({"--manifest-path", "-e", "--environment", "--color", "--auth-file",
                       "--pypi-keyring-provider", "--concurrent-solves",
                       "--concurrent-downloads"}),
}
# The py launcher's own options, read only as its first argument.
_PY_LISTS = frozenset({"-0", "-0p", "--list", "--list-paths"})
_PY_SELECTOR = re.compile(r"^-(?:\d+(?:\.\d+)*t?(?:-(?:32|64|arm64))?|V:\S+)$")
_FORMS = {"-": "`python -`", "-i": "`python -i`", "": "`python` with no script"}


def _strip_runners(values: list[str]) -> list[str]:
    """Removes "<runner> run" and the runner's options, so the program it runs comes first."""
    while len(values) > 1 and values[1] == "run" and program(values[0]) in _RUNNERS:
        takes, i = _RUNNERS[program(values[0])], 2
        while i < len(values) and values[i].startswith("-"):
            if values[i] == "--":
                i += 1
                break
            i += 2 if values[i] in takes else 1
        values = values[i:]
    return values


def _group(letters: str) -> str:
    """Reads one flag group, letter by letter.

    Returns:
        "-i" to refuse, "allow" for -c, -m, -V, -h, or -?, "value" when the
        next word is the value of -W or -X, or "" to go on.
    """
    for at, letter in enumerate(letters):
        if letter == "i":
            return "-i"
        if letter in "cmVh?":
            return "allow"
        if letter in "WX":
            return "" if at + 1 < len(letters) else "value"
    return ""


def _read_args(args: list[str], xargs: bool) -> str | None:
    """Reads Python's arguments left to right; returns "-", "-i", "", or None to allow."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-":
            return "-"
        if arg == "--":
            if i + 1 < len(args):
                return "-" if args[i + 1] == "-" else None
            break
        if arg.startswith("--"):
            if arg == "--version" or arg.startswith("--help"):
                return None
            i += 2 if arg == "--check-hash-based-pycs" else 1
            continue
        if arg.startswith("-"):
            found = _group(arg[1:])
            if found in ("-i", "allow"):
                return "-i" if found == "-i" else None
            i += 2 if found == "value" else 1
            continue
        return None
    return None if xargs else ""


def stdin_form(values: list[str], xargs: bool = False) -> str | None:
    """Tells how a simple command makes Python read its program from standard input.

    Args:
        values: The command's words, wrappers already removed (shell.py).
        xargs: The command came through xargs, which adds words to it.

    Returns:
        The form the reason names, such as "`python -`", or None when the
        command is not Python reading its program from standard input.
    """
    values = _strip_runners(values)
    if not values or not _PYTHON.match(program(values[0])):
        return None
    args = values[1:]
    if program(values[0]) == "py" and args:
        if args[0] in _PY_LISTS:
            return None
        if _PY_SELECTOR.match(args[0]):
            args = args[1:]
    found = _read_args(args, xargs)
    return None if found is None else _FORMS[found]


def _environment(ctx) -> str | None:
    """The config's [lang] environment at HEAD, or None when unset or unreadable."""
    from troycheck import gitio  # noqa: PLC0415
    from troycheck.config import ConfigError  # noqa: PLC0415

    try:
        value = ctx.config().lang.get("environment")
    except (ConfigError, gitio.GitError, OSError):
        return None
    return value if isinstance(value, str) and value.strip() else None


def reason(form: str, scratchpad: str | None, environment: str | None) -> str:
    """The refusal's text (design 8.3)."""
    where = f" ({scratchpad})" if scratchpad else ""
    env = f" (`[lang] environment` {environment})" if environment else ""
    return (f"R23: {form} makes Python read its program from standard input, and such a run "
            "can hang at Python's interactive prompt. Write the script to a file in the "
            f"scratchpad{where} and run that file with the project's Python{env}, for example "
            "`python -X utf8 <file>`. Python with a script file, `-c`, or `-m` may still read "
            "data from a pipe or `/dev/null`.")


def check_python(ctx, cmd) -> Refusal | None:
    """Refuses Python that reads its program from standard input, for every caller (R23)."""
    form = stdin_form([word.value for word in cmd.words], cmd.xargs)
    if form is None:
        return None
    scratchpad = ctx.data.get("scratchpad_dir")
    return Refusal(RULE, reason(form, str(scratchpad) if scratchpad else None,
                                _environment(ctx)))
