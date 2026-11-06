"""Word counts of a text."""


def count_words(text: str) -> dict[str, int]:
    """Counts each word of a text, ignoring case and punctuation.

    Args:
        text: Any text.

    Returns:
        Each word, in lowercase, mapped to how often it occurs.
    """
    raise NotImplementedError


def top_words(counts: dict[str, int], n: int) -> list[tuple[str, int]]:
    """Lists the most frequent words.

    Args:
        counts: Word counts from count_words.
        n: How many words to list, at least 1.

    Returns:
        Up to n (word, count) pairs, most frequent first. Equal counts are in
        alphabetical order.

    Raises:
        ValueError: n is less than 1.
    """
    raise NotImplementedError
