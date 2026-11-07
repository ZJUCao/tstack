"""Errors that stop the engine with exit code 2 (design section 3.3)."""


class InitError(Exception):
    """Raised when the engine cannot run: a git error or a broken plugin file."""
