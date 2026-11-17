"""The exam's one error type."""


class ExamError(Exception):
    """Stops a command: bad options, a case that does not load, or a run that cannot start."""
