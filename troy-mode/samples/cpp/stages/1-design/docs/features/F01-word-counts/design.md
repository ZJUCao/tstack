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
| `CountWords` | counting | `std::map<std::string, int> CountWords(std::string_view text)` | Maps each word, in lowercase, to how often it occurs. A word is ASCII letters, with apostrophes allowed between letters. |
| `TopWords` | counting | `std::vector<std::pair<std::string, int>> TopWords(const std::map<std::string, int>& counts, int n)` | Lists up to n words, most frequent first, equal counts in alphabetical order. Throws `std::invalid_argument` when n is less than 1. |
| `Run` | cli | `int Run(const std::vector<std::string>& args, std::ostream& out, std::ostream& err)` | `textstats PATH [--top N]` prints one `word count` line per word, 10 words by default, and returns 0. A file that cannot be read prints a message on err and returns 1. |
