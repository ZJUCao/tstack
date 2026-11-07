"""Errors that stop the engine with exit code 2 (F07 design 3.1, F06 design 3.3)."""


class FlowError(Exception):
    """Raised when the engine cannot run: bad input, a git or gh failure, or a bad config."""
