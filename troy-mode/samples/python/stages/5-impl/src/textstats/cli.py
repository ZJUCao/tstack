"""Command line: prints the most frequent words of a text file."""

import argparse
import sys
from pathlib import Path

from textstats.counting import count_words, top_words


def main(argv: list[str] | None = None) -> int:
    """Prints one "word count" line for each of the most frequent words.

    Usage: textstats PATH [--top N], with N 10 by default.

    Args:
        argv: Arguments after the program name. Defaults to sys.argv[1:].

    Returns:
        The exit code, 0.
    """
    parser = argparse.ArgumentParser(
        prog="textstats", description="Prints the most frequent words of a text file."
    )
    parser.add_argument("path", type=Path, help="the text file to read")
    parser.add_argument("--top", type=int, default=10, help="how many words to print")
    args = parser.parse_args(argv)
    counts = count_words(args.path.read_text(encoding="utf-8"))
    for word, count in top_words(counts, args.top):
        sys.stdout.write(f"{word} {count}\n")
    return 0
