"""The small PR checks: R01 (one commit), R02 (one stage), R16 (dependencies)."""

from .classify import ALLOWED, classify
from .context import PrContext
from .report import FAIL, PASS, WARN, Detail, Result


def _first_line(message: str) -> str:
    """Returns the first line of a commit message."""
    return message.strip().splitlines()[0] if message.strip() else ""


def check_r01(ctx: PrContext) -> Result:
    """Checks that the PR has exactly one commit, whose subject is the PR title (R01).

    The subject must equal the title so that main's history records each
    PR's kind, which the test policy reads (F03 design D17).

    Args:
        ctx: The PR under check.

    Returns:
        PASS for exactly one commit whose subject line equals the title, FAIL
        otherwise, listing the commits.
    """
    count = len(ctx.commits)
    if count == 1:
        subject = _first_line(ctx.commits[0].message).rstrip()
        if subject == ctx.title_text.rstrip():
            return Result("R01", PASS, "1 commit. Its subject is the PR title.")
        return Result("R01", FAIL, "The commit's subject line is not the PR title.",
                      [Detail(None, None, f"subject: {subject}"),
                       Detail(None, None, f"title:   {ctx.title_text.rstrip()}")])
    details = [Detail(None, None, f"{c.sha[:12]} {_first_line(c.message)}") for c in ctx.commits]
    return Result("R01", FAIL, f"{count} commits. A PR has exactly one commit.", details)


def _class_list(classes: set[str]) -> str:
    """Joins class names in a fixed order for messages."""
    order = ["source", "tests", "docs", "config", "dependencies"]
    return ", ".join(name for name in order if name in classes)


def check_r02(ctx: PrContext) -> Result:
    """Checks that every changed path belongs to a class the PR kind may change (R02).

    Args:
        ctx: The PR under check.

    Returns:
        FAIL when the title matches no kind, or once per path the kind may
        not change. PASS otherwise.
    """
    if ctx.title is None:
        return Result("R02", FAIL, "The title matches no PR kind, so its stage is unknown.",
                      [Detail(None, None, f"title: {ctx.title_text}")])
    allowed = ALLOWED[ctx.title.kind]
    paths = ctx.changed_paths()
    classes, details = set(), []
    for path in paths:
        cls = classify(path, ctx.config.paths)
        classes.add(cls)
        if cls not in allowed:
            details.append(Detail(path, None, f"{cls} file, not allowed in a {ctx.title.kind} PR"))
    files = len({c.path for c in ctx.changes})
    if details:
        return Result("R02", FAIL, f"{len(details)} of {len(paths)} paths are not allowed.", details)
    noun = "file" if files == 1 else "files"
    return Result("R02", PASS, f"{files} {noun}, all {_class_list(classes) or 'allowed'}.")


def check_r16(ctx: PrContext) -> Result:
    """Flags changed dependency files for the Architect (R16). Never fails.

    Args:
        ctx: The PR under check.

    Returns:
        WARN listing each changed dependency file, or PASS when there is none.
    """
    patterns = {"dependencies"}
    found = []
    for path in ctx.changed_paths():
        if classify(path, ctx.config.paths) in patterns and path not in found:
            found.append(path)
    if not found:
        return Result("R16", PASS, "No dependency files changed.")
    details = [Detail(path, None, "changed") for path in found]
    return Result("R16", WARN, "Dependency files changed. Needs the Architect's approval.", details)
