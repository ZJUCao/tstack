"""Tests of F01 Word counts: the textstats command line."""

from pathlib import Path

import pytest

from textstats.cli import main


def test_f01_t05_prints_most_frequent_words(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F01-T05: main prints a "word count" line per word and returns 0."""
    text = tmp_path / "words.txt"
    text.write_text("b a b c b a", encoding="utf-8")
    assert main([str(text), "--top", "2"]) == 0
    assert capsys.readouterr().out == "b 3\na 2\n"
