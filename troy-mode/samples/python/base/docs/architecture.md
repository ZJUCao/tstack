---
troy-doc: "architecture"
lang: "en"
version: "1.0"
updated: "2026-11-06"
status: "Sample. Holds only what troy-check reads."
---

# textstats architecture

textstats is tstack's sample Python project. Its documents hold only what `troy-check code` reads, so they have no Chinese mirrors.

## 1. Overview

A command-line tool that prints the most frequent words of a text file.

## 2. Layout

The package is in `src/textstats`, and the tests are in `tests`.

## 3. Modules

| Module | Owns | External interfaces | May depend on |
| --- | --- | --- | --- |
| counting | `src/textstats/counting.py`. Counts the words of a text. | `src/textstats/counting.py` | None |
| cli | `src/textstats/cli.py`. Reads a text file and prints its most frequent words. | None | counting |
