---
troy-doc: "F01-design"
lang: "en"
version: "1.0"
updated: "2026-11-06"
status: "Sample."
---

# F01 Word counts: design

## 1. Interfaces

| Interface | Module | Signature | Behavior |
| --- | --- | --- | --- |
| `count_words` | counting | `count_words(text: str) -> dict[str, int]` | Maps each word, in lowercase, to how often it occurs. A word is letters, with apostrophes allowed between letters. |
| `top_words` | counting | `top_words(counts: dict[str, int], n: int) -> list[tuple[str, int]]` | Lists up to n words, most frequent first, equal counts in alphabetical order. Raises ValueError when n is less than 1. |
| `main` | cli | `main(argv: list[str] \| None = None) -> int` | `textstats PATH [--top N]` prints one `word count` line per word, 10 words by default, and returns 0. |
