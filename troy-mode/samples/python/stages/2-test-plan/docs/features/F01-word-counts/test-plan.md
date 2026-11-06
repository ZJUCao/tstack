---
troy-doc: "F01-test-plan"
lang: "en"
version: "1.0"
updated: "2026-11-06"
status: "Sample."
---

# F01 Word counts: test plan

## 1. Feature

- ID and name: F01 Word counts
- Design: [design.md](design.md)

## 2. Cases

| ID | Level | Interface | What it tests | Setup and input | Expected result |
| --- | --- | --- | --- | --- | --- |
| F01-T01 | unit | `count_words` | Case does not matter. | `"The cat saw the CAT"` | `{"the": 2, "cat": 2, "saw": 1}` |
| F01-T02 | unit | `count_words` | Punctuation splits words, and an apostrophe inside a word does not. A text without letters has no words. | `"Don't stop, don't!"` and `"42 ..."` | `{"don't": 2, "stop": 1}` and `{}` |
| F01-T03 | unit | `top_words` | Most frequent first, equal counts in alphabetical order, at most n. | `{"b": 2, "a": 2, "c": 3, "d": 1}`, n = 3 | `[("c", 3), ("a", 2), ("b", 2)]` |
| F01-T04 | unit | `top_words` | n below 1 is rejected. | n = 0 | ValueError |
| F01-T05 | functional | `main` | Prints the most frequent words of a file. | A file holding `b a b c b a`, `--top 2` | Prints `b 3` and `a 2`, returns 0 |

## 3. Performance cases

None

## 4. Not tested

None

## 5. Alignment with the Interface Designer

None
