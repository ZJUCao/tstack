"""Path patterns used by the config file (design section 5).

A pattern matches a whole repository path with "/" separators. "*" matches
within one folder name, "**" matches any number of folders, and "?" matches
one character.
"""

import re
from functools import lru_cache


def _translate(pattern: str) -> str:
    """Turns one path pattern into a regular expression source string."""
    out, i, n = [], 0, len(pattern)
    while i < n:
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("/**", i) and i + 3 == n:
            out.append("(?:/.*)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return "".join(out)


@lru_cache(maxsize=None)
def compile_pattern(pattern: str) -> re.Pattern:
    """Compiles a path pattern.

    Args:
        pattern: A pattern such as "docs/**" or "**/test_*.py".

    Returns:
        A compiled regular expression that must match the whole path.
    """
    return re.compile(_translate(pattern))


def matches_any(path: str, patterns: list[str]) -> bool:
    """Tells whether a path matches at least one pattern.

    Args:
        path: Repository path with "/" separators.
        patterns: Path patterns.

    Returns:
        True if any pattern matches the whole path.
    """
    return any(compile_pattern(p).fullmatch(path) for p in patterns)
