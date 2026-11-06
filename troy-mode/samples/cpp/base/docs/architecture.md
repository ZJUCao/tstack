---
troy-doc: "architecture"
lang: "en"
version: "1.0"
updated: "2026-11-06"
status: "Sample. Holds only what troy-check reads."
---

# textstats architecture

textstats in C++ is troy-pstack's sample C/C++ project. Its documents hold only what `troy-check code` reads, so they have no Chinese mirrors.

## 1. Overview

A command-line tool that prints the most frequent words of a text file.

## 2. Layout

Public headers are in `include/textstats`, sources and internal headers in `src`, and tests in `tests`.

## 3. Modules

| Module | Owns | External interfaces | May depend on |
| --- | --- | --- | --- |
| counting | `include/textstats/counting.h`, `src/counting.cc`. Counts the words of a text. | `include/textstats/counting.h` | None |
| cli | `src/cli.h`, `src/cli.cc`, `src/main.cc`. Reads a text file and prints its most frequent words. | `src/cli.h` | counting |
