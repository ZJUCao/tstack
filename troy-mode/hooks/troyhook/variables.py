"""Variables a command line sets for itself (design section 7.1).

The F05 trial's Test Manager made its scratch folder with
DST=$(mktemp -d <temp>/name-XXXXXX) and then ran cd "$DST". So the parser
follows a variable set earlier in the same command line to a literal path,
or to the new folder "mktemp -d" makes, and treats every other variable as
unknown.
"""

import os
import re

from .lexer import Word
from .paths import temp_dir, to_native

NEW_FOLDER = "troy-mktemp-folder"
_REFERENCE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
_NOT_LITERAL = frozenset("$`*?[")
_ABSOLUTE = re.compile(r"^(?:[/\\~]|[A-Za-z]:[/\\])")


def expand(word: Word, known: dict[str, str]) -> Word:
    """Puts known variables into a word.

    Args:
        word: A word from the lexer.
        known: Values of the variables set earlier in the command line.

    Returns:
        A literal word when every expansion in it was a known variable;
        otherwise the word unchanged.
    """
    if word.literal or word.subs:
        return word
    missing = []

    def put(match: re.Match) -> str:
        """Gives one variable's value, noting an unknown one."""
        value = known.get(match.group(1) or match.group(2))
        if value is None:
            missing.append(match.group(0))
            return match.group(0)
        return value

    text = _REFERENCE.sub(put, word.value)
    if missing or _NOT_LITERAL & set(text):
        return word
    return Word(text, word.raw, True)


def value_of(word: Word, known: dict[str, str], cwd: str | None) -> str | None:
    """Works out what an assignment word NAME=value stores.

    Args:
        word: The assignment word.
        known: Values of the variables set earlier in the command line.
        cwd: The folder the command runs in, or None when unknown.

    Returns:
        The value, or None when the text alone cannot tell it.
    """
    text = word.value.partition("=")[2]
    if word.subs:
        whole = len(word.subs) == 1 and text.startswith("$(") and text.endswith(")")
        return _mktemp_folder(word.subs[0], known, cwd) if whole else None
    if word.literal:
        return text
    expanded = expand(Word(text, text, False), known)
    return expanded.value if expanded.literal else None


def _mktemp_folder(tokens: list, known: dict[str, str], cwd: str | None) -> str | None:
    """Gives a path inside the folder "mktemp -d" creates its folder in, or None.

    GNU mktemp puts the folder in -p DIR or --tmpdir=DIR, in the temp folder
    for -t, --tmpdir, or no template, and else beside the template.
    """
    words = [expand(token, known) for token in tokens if isinstance(token, Word)]
    if not words or re.split(r"[/\\]", words[0].value)[-1].lower() not in ("mktemp",
                                                                          "mktemp.exe"):
        return None
    flags, template, folder, i = set(), None, None, 1
    while i < len(words):
        value = words[i].value
        if value == "-p" and i + 1 < len(words):
            folder, i = words[i + 1], i + 1
        elif value.startswith("--tmpdir="):
            folder = Word(value.split("=", 1)[1], value, words[i].literal)
        elif value in ("--tmpdir", "--directory"):
            flags.add("t" if value == "--tmpdir" else "d")
        elif value.startswith("-") and not value.startswith("--"):
            flags |= set(value[1:])
        elif not value.startswith("-"):
            template = words[i]
        i += 1
    if "d" not in flags:
        return None
    if folder is not None:
        base = folder.value if folder.literal else None
    elif "t" in flags or template is None:
        base = temp_dir()
    else:
        base = (os.path.dirname(template.value) or ".") if template.literal else None
    if base is None or (cwd is None and not _ABSOLUTE.match(base)):
        return None
    return os.path.join(to_native(base, cwd or "."), NEW_FOLDER)
