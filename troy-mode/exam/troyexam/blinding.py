"""Words that would tell a role it runs in an exam (design 6.1).

The runner checks every text the exam adds, a folder, a file name, a branch, a
variable, an Input, and the gh stand-in's messages, before a run starts.
"test" and "benchmark" are troy-mode's own words, so they are allowed.
"""

import random
import re
import string
from collections.abc import Iterable

EXAM_WORDS = ("eval", "exam", "trap", "judge", "rubric", "grade", "score", "compare",
              "experiment", "candidate", "variant", "arena", "baseline", "hillclimb", "sandbox")
# The labels the exam gives the two versions (design 6.1).
LABELS = ("base", "head")
_ENDINGS = ("", "s", "es", "d", "ed", "r", "rs", "er", "ers", "ing")
_TOKEN = re.compile(r"[A-Za-z]+")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")


def _tokens(text: str) -> set[str]:
    """Splits text into lower-case tokens of letters, also at a lower-to-upper change."""
    found = set()
    for run in _TOKEN.findall(text):
        found.update(part.lower() for part in _CAMEL.split(run) if part)
    return found


def _forms(word: str) -> set[str]:
    """The word and its forms with one ending ("grade": "grades", "graded", "grading", ...)."""
    word = word.lower()
    forms = {word + ending for ending in _ENDINGS}
    if word.endswith("e"):
        forms.add(word[:-1] + "ing")
    return forms


def exam_words(text: str, extra: Iterable[str] = ()) -> list[str]:
    """Lists the exam words, then the extra words, that the text holds.

    Args:
        text: Any text the exam adds to a run.
        extra: More words to refuse, such as the labels of the two versions.

    Returns:
        Each word that some token of the text equals, alone or with one ending,
        once, in the order of EXAM_WORDS and then extra.
    """
    tokens = _tokens(text)
    hits = []
    for word in (*EXAM_WORDS, *extra):
        if word not in hits and tokens & _forms(word):
            hits.append(word)
    return hits


def random_letters(rng: random.Random | None = None, n: int = 6) -> str:
    """Returns n lower-case letters that hold no exam word or label, even inside a longer word."""
    rng = rng or random.SystemRandom()
    while True:
        letters = "".join(rng.choice(string.ascii_lowercase) for _ in range(n))
        if not any(word in letters for word in (*EXAM_WORDS, *LABELS)):
            return letters
