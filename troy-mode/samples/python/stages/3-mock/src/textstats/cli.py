"""Command line: prints the most frequent words of a text file."""


def main(argv: list[str] | None = None) -> int:
    """Prints one "word count" line for each of the most frequent words.

    Usage: textstats PATH [--top N], with N 10 by default.

    Args:
        argv: Arguments after the program name. Defaults to sys.argv[1:].

    Returns:
        The exit code, 0.
    """
    raise NotImplementedError
