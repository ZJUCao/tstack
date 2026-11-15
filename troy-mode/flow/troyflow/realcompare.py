"""The path map and the comparison of a real run (F12 design 5.5 and 5.6).

The comparison is exact after five normalizations: CRLF and LF are the same
line end, spaces and tabs at the end of a line are ignored, blank lines at
the end are ignored, the path map shows each run path as the prototype's
path, and a prototype line that is exactly "..." matches any number of lines.
"""

import difflib
import os
import re
from pathlib import Path

from .runfile import RunPath

WILDCARD = "..."
SCRATCH_MARK = "<scratch>"
NORMALIZATIONS = (
    "CRLF and LF count as the same line end.",
    "Spaces and tabs at the end of a line are ignored.",
    "Blank lines at the end of a command's output are ignored.",
    "The path map: each run path in the output is shown as the prototype's path, longest "
    "first, in its long and short spellings and with \\ or /.",
    "A prototype line that is exactly ... matches any number of lines.",
)
WINDOWS = os.name == "nt"
_FLAGS = re.IGNORECASE if WINDOWS else 0
_DRIVE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
_UNC = re.compile(r"(?:^|(?<=[\s\"'=,]))\\\\[^\\\s]")
_POSIX_ROOT = re.compile(r"(?:^|(?<=[\s\"'=,]))/")
_TOKEN_END = re.compile(r"[\s\"']")
# A path ends where no letter, digit, _ or - follows, so C:\Users\Troy is not
# found inside C:\Users\Troy2.
_BOUNDARY = r"(?![A-Za-z0-9_\-])"


def _windows_spelling(path: str, long: bool) -> str | None:
    """Returns Windows' long or short spelling of an existing path, or None."""
    if not WINDOWS:
        return None
    import ctypes  # Windows only: the long and short names of the scratch folder.

    function = ctypes.windll.kernel32.GetLongPathNameW if long \
        else ctypes.windll.kernel32.GetShortPathNameW
    size = function(path, None, 0)
    if not size:
        return None
    buffer = ctypes.create_unicode_buffer(size)
    return buffer.value if function(path, buffer, size) else None


def spellings(folder: Path) -> list[str]:
    """Every spelling of an existing folder: as made, resolved, long, and short, with \\ and /."""
    found = {str(folder), os.path.realpath(folder)}
    for long in (True, False):
        other = _windows_spelling(str(folder), long)
        if other:
            found.add(other)
    result = set()
    for text in found:
        text = text.rstrip("\\/") or text
        result.add(text)
        result.add(text.replace("\\", "/"))
        if WINDOWS:
            result.add(text.replace("/", "\\"))
    return sorted(result, key=len, reverse=True)


class PathMap:
    """The run file's path map, between the prototype's folders and the run's.

    Attributes:
        scratch: The scratch folder.
        home: The home folder, inside the scratch folder.
        pairs: (prototype path, run path) from the run file's [paths].
    """

    def __init__(self, scratch: Path, pairs: list[tuple[str, RunPath]]) -> None:
        self.scratch = scratch
        self.home = scratch / "home"
        self.pairs = pairs
        self._scratch_spellings = spellings(scratch)

    def real(self, path: RunPath) -> Path:
        """Returns where a run path lies on this computer."""
        base = self.home if path.home else self.scratch
        return Path(os.path.normpath(base.joinpath(*path.parts))) if path.parts else base

    def to_marks(self, text: str) -> str:
        """Shows each prototype path in a typed text as its run path with `<home>` or `<scratch>`.

        Longest prototype path first; `\\` and `/` both match, and case does
        not matter on Windows.
        """
        for proto, target in sorted(self.pairs, key=lambda p: len(p[0]), reverse=True):
            parts = [re.escape(part) for part in re.split(r"[\\/]", proto.rstrip("\\/"))]
            pattern = r"[\\/]".join(parts) + _BOUNDARY
            text = re.sub(pattern, lambda _m, t=target.text: t, text, flags=_FLAGS)
        return text

    def unmapped(self, marked: str) -> str | None:
        """Returns the first absolute path in a text the path map did not cover, or None.

        A drive path or a network path counts on every system, and on POSIX also
        a word that starts with /. The text has gone through to_marks.
        """
        for pattern in (_DRIVE, _UNC) + (() if WINDOWS else (_POSIX_ROOT,)):
            match = pattern.search(marked)
            if match:
                end = _TOKEN_END.search(marked, match.start())
                return marked[match.start():end.start() if end else len(marked)]
        return None

    def from_marks(self, marked: str) -> str:
        """Puts the real folders in place of `<home>` and `<scratch>` in a marked word or value.

        The rest of the word after a mark is the path below it. On POSIX, its
        backslashes become /.
        """
        def place(match: re.Match) -> str:
            base = str(self.home if match.group(1) == "home" else self.scratch)
            rest = match.group(2)
            if not WINDOWS:
                rest = rest.replace("\\", "/")
            elif "/" in rest and "\\" not in rest:
                return base.replace("\\", "/") + rest
            return base + rest
        return re.sub(r"<(home|scratch)>([^\"'<]*)", place, marked)

    def to_prototype(self, text: str) -> str:
        """Shows each run path in real output as the prototype's path, then the scratch folder.

        Every spelling of each run path counts, longest first. A spelling
        with / gets the prototype path with /. Any other spelling of the
        scratch folder becomes `<scratch>`.
        """
        pairs: list[tuple[str, str]] = []
        for proto, target in self.pairs:
            rest = list(target.parts)
            base = ["home"] if target.home else []
            for spelling in self._scratch_spellings:
                sep = "/" if "/" in spelling and "\\" not in spelling else os.sep
                full = sep.join([spelling, *base, *rest]) if base or rest else spelling
                shown = proto.rstrip("\\/")
                pairs.append((full, shown.replace("\\", "/") if sep == "/" and WINDOWS else shown))
        pairs += [(s, SCRATCH_MARK) for s in self._scratch_spellings]
        pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
        for real, shown in pairs:
            text = re.sub(re.escape(real) + _BOUNDARY, lambda _m, s=shown: s, text, flags=_FLAGS)
        return text

    def hide_scratch(self, text: str) -> str:
        """Shows every spelling of the scratch folder as `<scratch>`, for evidence."""
        for spelling in self._scratch_spellings:
            text = re.sub(re.escape(spelling), SCRATCH_MARK, text, flags=_FLAGS)
        return text


def lines_of(text: str) -> list[str]:
    """Splits text into lines: CRLF and LF are the same, trailing spaces and blank lines go."""
    rows = [row.rstrip(" \t") for row in text.replace("\r\n", "\n").split("\n")]
    while rows and not rows[-1]:
        rows.pop()
    return rows


def normalize(rows: list[str]) -> list[str]:
    """Normalizes lines that are already split, such as the prototype's."""
    return lines_of("\n".join(rows))


def matches(expected: list[str], real: list[str]) -> bool:
    """Tells whether real lines match the prototype's, where "..." matches any number of lines."""
    i = j = 0
    star, mark = -1, 0
    while j < len(real):
        if i < len(expected) and expected[i] == WILDCARD:
            star, mark = i, j
            i += 1
        elif i < len(expected) and expected[i] == real[j]:
            i += 1
            j += 1
        elif star >= 0:
            i, mark = star + 1, mark + 1
            j = mark
        else:
            return False
    while i < len(expected) and expected[i] == WILDCARD:
        i += 1
    return i == len(expected)


def diff(expected: list[str], real: list[str]) -> str:
    """A unified diff of the prototype's lines and the real lines."""
    return "\n".join(difflib.unified_diff(expected, real, "prototype", "real", lineterm="")) + "\n"


def decode(data: bytes) -> tuple[str, bool]:
    """Decodes output as UTF-8; returns the text and whether it was valid UTF-8."""
    try:
        return data.decode("utf-8"), True
    except UnicodeDecodeError:
        return data.decode("utf-8", "replace"), False
