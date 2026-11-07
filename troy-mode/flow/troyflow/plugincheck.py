"""The project's copy of troy-check compared with the plugin's (F07 design 5.1).

[roles], [flow], and troy-check code --worktree need the copy that F07 part 1
brings, and troy-init's upgrade brings it into a project.
"""

from pathlib import Path

from troyinit.errors import InitError
from troyinit.plugin import CHECKS_DEST, load_plugin, owned_sources, read_source

from . import repo as git
from .errors import FlowError
from .repo import MAIN, Repo

PLUGIN_ROOT = Path(__file__).resolve().parents[3]


def _wanted() -> dict[str, str]:
    """The plugin's troy-check as the project's paths and LF text."""
    try:
        sources = owned_sources(load_plugin(PLUGIN_ROOT))
        return {path: read_source(source).decode("utf-8", "replace")
                for path, source in sources.items() if path.startswith(CHECKS_DEST + "/")}
    except InitError as exc:
        raise FlowError(str(exc)) from exc


def compare(repo: Repo) -> dict:
    """Compares .troy-mode/checks/ on origin/main with the plugin's troy-check.

    Args:
        repo: The checkout.

    Returns:
        {"outdated": bool, "differs": sorted paths that differ, are missing
        from the project, or exist only in the project}.
    """
    wanted = _wanted()
    present = [p for p in git.files(repo, MAIN, CHECKS_DEST) if "/__pycache__/" not in p
               and not p.endswith(".pyc")]
    have = git.read_many(repo, MAIN, sorted(set(present) | set(wanted)))
    differs = sorted(p for p in set(present) | set(wanted)
                     if have.get(p, None) is None or p not in wanted
                     or have[p].replace("\r\n", "\n") != wanted[p])
    return {"outdated": bool(differs), "differs": differs}
