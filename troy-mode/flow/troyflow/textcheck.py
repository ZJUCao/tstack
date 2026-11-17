"""The check of a PR comment before F07 posts it (F07 design 8.4, R19).

F15 adds the length check: GitHub refuses an issue or comment body of more than
65,536 characters (F15 design 10.1).
"""

from pathlib import Path

from troycheck.attribution import find_attribution

from . import repo as git
from .errors import FlowError

MAX_CHARS = 65_536


def run_check_text(args) -> tuple[dict, int]:
    """Checks a text file with troy-check's attribution rules in the project's mode.

    Args:
        args: Parsed options: file and repo.

    Returns:
        The report and the exit code: 1 with one problem per line that
        carries attribution.

    Raises:
        FlowError: The file cannot be read, or the config at HEAD is invalid.
    """
    try:
        text = Path(args.file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FlowError(f"cannot read {args.file}: {exc}") from exc
    repo = git.find_repo(args.repo)
    mode = git.config_at(repo, "HEAD").attribution_mode if repo else "strict"
    lines = text.splitlines() or [""]
    problems = [{"line": n, "message": f"line {n} carries attribution: "
                                       f"{lines[min(n, len(lines)) - 1].strip()[:80]}"}
                for n in find_attribution(text, mode)]
    if len(text) > MAX_CHARS:
        problems.append({"line": 0, "message": f"the text holds {len(text):,} characters; "
                                               f"GitHub takes at most {MAX_CHARS:,}"})
    report = {"command": "check-text", "ok": not problems, "mode": mode, "problems": problems,
              "notes": []}
    return report, 1 if problems else 0
