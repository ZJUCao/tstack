"""Path classes and what each PR kind may change (design section 5, D9)."""

from .globs import matches_any

CLASS_ORDER = ("config", "dependencies", "tests", "docs")

ALLOWED: dict[str, tuple[str, ...]] = {
    "design": ("docs",),
    "test-plan": ("docs",),
    "accept": ("docs",),
    "docs": ("docs",),
    "mock": ("source", "dependencies"),
    "impl": ("source", "dependencies"),
    "fix": ("source", "dependencies"),
    "refactor": ("source", "dependencies"),
    "tests": ("tests", "dependencies"),
    "test": ("tests", "dependencies"),
    "test-fix": ("tests", "dependencies"),
    "version-tests": ("tests", "dependencies"),
    "rules": ("config", "dependencies"),
}

SOURCE_KINDS = ("mock", "impl", "fix", "refactor")


def classify(path: str, paths: dict[str, list[str]]) -> str:
    """Finds the class of a changed path.

    The first class in CLASS_ORDER whose patterns match wins. A path that
    matches none is "source".

    Args:
        path: Repository path with "/" separators.
        paths: Pattern lists by class name, from the config.

    Returns:
        "config", "dependencies", "tests", "docs", or "source".
    """
    for name in CLASS_ORDER:
        if matches_any(path, paths[name]):
            return name
    return "source"
