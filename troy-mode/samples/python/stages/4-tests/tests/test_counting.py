"""Tests of F01 Word counts: textstats.counting."""

import pytest

from textstats.counting import count_words, top_words


def test_f01_t01_case_does_not_matter() -> None:
    """F01-T01: the same word in a different case is the same word."""
    assert count_words("The cat saw the CAT") == {"the": 2, "cat": 2, "saw": 1}


def test_f01_t02_punctuation_splits_words() -> None:
    """F01-T02: punctuation splits words, and an apostrophe inside a word does not."""
    assert count_words("Don't stop, don't!") == {"don't": 2, "stop": 1}
    assert count_words("42 ...") == {}


def test_f01_t03_most_frequent_first() -> None:
    """F01-T03: most frequent first, equal counts in alphabetical order, at most n."""
    counts = {"b": 2, "a": 2, "c": 3, "d": 1}
    assert top_words(counts, 3) == [("c", 3), ("a", 2), ("b", 2)]


def test_f01_t04_n_below_one_is_rejected() -> None:
    """F01-T04: n below 1 raises ValueError."""
    with pytest.raises(ValueError, match="at least 1"):
        top_words({"a": 1}, 0)
