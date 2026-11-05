---
troy-doc: "rules"
lang: "en"
version: "1.0"
updated: "{{init-date}}"
status: "Seeded by troy-init from troy-mode."
mirror: "rules.zh-CN.md"
---

# {{project-name}} rules

<!-- template: troy-init fills in {{project-name}} and {{init-date}}. Rules R01 to R19 come from troy-mode. This project's own rules are added below them as P01, P02, and so on, through the rule change flow (troy-mode requirements 5.8). Write None for a section, field, or table that has nothing to hold. Remove every template comment and every {{marker}} before the document merges. -->

## 1. Rule types

- **Hard** blocks the merge.
- **Soft** allows the PR when its description gives a reason.
- **Review** is checked by a role.
- **Process** is followed by troy-mode itself.

## 2. Rules

| ID | Rule | Type | Enforced by | Scope | Since |
| --- | --- | --- | --- | --- | --- |
| R01 | Each PR has exactly one commit. Review fixes amend that commit, or the PR is squash-merged. | Hard | CI | troy-mode | {{init-date}} |
| R02 | Each PR holds one stage's output only: documents, source, or tests. | Hard | CI | troy-mode | {{init-date}} |
| R03 | A source PR changes at most 500 lines (added plus deleted, not counting lock files or generated files) in at most 5 files. Test PRs have no limit. A PR that only splits a file may pass the limit and says so. | Soft | CI | troy-mode | {{init-date}} |
| R04 | A function body has at most 50 lines, not counting comments, doc comments, or blank lines. A complex external interface calls single-purpose internal functions. | Hard | Lint | troy-mode | {{init-date}} |
| R05 | Doc comments follow Google style. Code comments are in English only. | Hard | Lint | troy-mode | {{init-date}} |
| R06 | A source file has at most 500 lines in total, comments included. Larger files are split. | Soft | Lint | troy-mode | {{init-date}} |
| R07 | Modules depend on each other only in the directions the architecture allows, only through external interfaces, and never in a cycle. | Hard | Dependency checker | troy-mode | {{init-date}} |
| R08 | The Developer never edits test files. | Hard | Hook and CI | troy-mode | {{init-date}} |
| R09 | Every new test in a test PR fails against the mock. | Hard | CI | troy-mode | {{init-date}} |
| R10 | Every test is tagged with its feature or bug ID. Tests of features not yet accepted and of bugs not yet fixed count as expected failures. Every other test must pass. | Hard | Test runner config and CI | troy-mode | {{init-date}} |
| R11 | In an implementation PR, the changed code has at least 90% line coverage and 80% branch coverage. 95% is a target, not a gate. An excluded line needs a written reason and the Test Manager's approval. | Hard | CI | troy-mode | {{init-date}} |
| R12 | English documents are the source of truth. A PR that changes an English document also updates its Chinese mirror. The mirror's header names the English version it matches. | Hard | CI | troy-mode | {{init-date}} |
| R13 | A status label says how far a feature really goes, for example "passes tests on main" versus "usable on Troy's devices". | Review | Product Manager | troy-mode | {{init-date}} |
| R14 | Only interfaces with a performance target get performance tests. They run on a fixed machine, with a margin, against the previous baseline. | Review | Test Manager | troy-mode | {{init-date}} |
| R15 | Every fixed bug keeps its reproduction test. | Review | Test Manager | troy-mode | {{init-date}} |
| R16 | A new third-party dependency needs the Architect's approval. | Review | Architect. CI flags every change to dependency files. | troy-mode | {{init-date}} |
| R17 | A review loop stops at 3 rounds and escalates. | Process | troy-mode | troy-mode | {{init-date}} |
| R18 | Troy merges PR 1 and PR 2 of the first 3 features. Claude merges every other PR once its checks and reviews pass. Troy decides when Claude merges everything. | Process | troy-mode | troy-mode | {{init-date}} |
| R19 | Commits use the email in Troy's global CLAUDE.md. Commits and PRs carry no Claude attribution. | Hard | Hook and CI | troy-mode | {{init-date}} |

<!-- template: Add this project's own rules here, one row each, with Scope "project". Example row: | P01 | {{rule}} | {{type}} | {{enforced-by}} | project | {{YYYY-MM-DD}} | -->

## 3. Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | {{init-date}} | Seeded with R01 to R19 from troy-mode. |
