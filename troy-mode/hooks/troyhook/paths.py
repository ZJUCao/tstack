"""Path handling: normalizing tool and shell paths, and containment (design 5.2)."""

import os
import re

WINDOWS = os.name == "nt"
_DRIVE = re.compile(r"^/([A-Za-z])(?=/|$)")


def temp_dir() -> str:
    """Returns the system temp folder, as Python's tempfile module finds it."""
    import tempfile  # noqa: PLC0415  (imported late: it is slow to import)

    return tempfile.gettempdir()


def _from_git_bash(path: str) -> str:
    """Turns Git Bash forms such as /c/Users/x and /tmp/x into Windows paths.

    Args:
        path: A path as a Git Bash command or a tool may write it.

    Returns:
        The Windows path, or the path unchanged when it is not a Git Bash form.
    """
    slashed = path.replace("\\", "/")
    if slashed == "/tmp" or slashed.startswith("/tmp/"):
        return temp_dir() + slashed[4:]
    match = _DRIVE.match(slashed)
    if match:
        return match.group(1).upper() + ":/" + slashed[3:].lstrip("/")
    return path


def to_native(path: str, base: str) -> str:
    """Makes a path from a tool or a command absolute and real.

    Expands a leading "~", turns Git Bash forms into Windows paths on
    Windows, makes the path absolute against base, and resolves "..", links,
    and the on-disk case of existing folders.

    Args:
        path: The path as written.
        base: The folder a relative path is taken from.

    Returns:
        The absolute real path.
    """
    path = os.path.expanduser(path)
    if WINDOWS:
        path = _from_git_bash(path)
    if not os.path.isabs(path) and not (WINDOWS and path[:1] in "/\\" and path[:2] != "//"):
        path = os.path.join(base, path)
    return os.path.realpath(path)


def _key(path: str) -> str:
    """Returns the form of a path used to compare it: without case on Windows."""
    return os.path.normcase(path)


def inside(path: str, folder: str) -> bool:
    """Tells whether a path is the folder or lies under it.

    Both paths must already be absolute and real (see to_native).

    Args:
        path: The path to test.
        folder: The folder.

    Returns:
        True if path equals folder or is inside it.
    """
    child, parent = _key(path), _key(folder)
    if child == parent:
        return True
    if not parent.endswith(os.sep):
        parent += os.sep
    return child.startswith(parent)


def relative(path: str, root: str) -> str | None:
    """Gives a path relative to a folder, with "/" separators.

    Args:
        path: An absolute real path.
        root: An absolute real folder.

    Returns:
        The relative path ("" for the folder itself), or None when path is
        not inside root.
    """
    if not inside(path, root):
        return None
    return path[len(root):].replace("\\", "/").strip("/")


def temp_folders(scratchpad: str | None, base: str) -> list[str]:
    """Lists the folders outside the repository where writes are allowed (D42).

    Args:
        scratchpad: The session's scratchpad folder from the hook input, or None.
        base: The folder a relative scratchpad path is taken from.

    Returns:
        The real paths of the system temp folder, /tmp on Linux and macOS,
        and the scratchpad.
    """
    folders = [os.path.realpath(temp_dir())]
    if not WINDOWS:
        folders.append(os.path.realpath("/tmp"))
    if scratchpad:
        folders.append(to_native(scratchpad, base))
    return folders
