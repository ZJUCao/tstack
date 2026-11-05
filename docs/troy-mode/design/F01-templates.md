# F01 design: templates and rules table

| | |
| --- | --- |
| Feature | F01 in [requirements 1.1](../requirements.md#72-feature-list) |
| Version | 1.1 |
| Date | 2026-11-05 |
| Status | Approved by Troy on 2026-11-05, with D1 to D6 |
| Source of truth | This English file. [`F01-templates.zh-CN.md`](F01-templates.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F01 delivers five things that later features build on:

1. Document templates that `troy-init` copies into a project.
2. The document header that pairs an English document with its Chinese mirror (R12).
3. The rules table, seeded from requirements section 6.
4. The ID formats and the feature status labels (R10, R13).
5. The PR title format and the PR description template (D1).

F01 does not copy templates into projects (F06), check headers (F02), or fill templates (the roles, F04 and F07). It contains no code.

This design covers only what other features and roles depend on: file locations, names, header fields, sections, ID formats, and labels.

## 2. Location in troy-pstack

All troy-mode files that are not skills, agents, or hooks live in one new top-level folder. Later features add `checks/` (F02) and `lang/` (F03) beside `templates/`.

```text
troy-mode/
  templates/
    requirements.md          requirements.zh-CN.md
    architecture.md          architecture.zh-CN.md
    feature-design.md        feature-design.zh-CN.md
    test-plan.md             test-plan.zh-CN.md
    version-test-plan.md     version-test-plan.zh-CN.md
    adr.md                   adr.zh-CN.md
    changelog.md             changelog.zh-CN.md
    rules.md                 rules.zh-CN.md
    progress.md
    escalation.md
    pull-request.md
    README.md                README.zh-CN.md
```

`templates/README.md` lists each template, where it lands in a project, and which role fills it. It also holds the ID formats (section 6), the status labels (section 7), and the PR kinds (section 5.11), so roles have one place to look them up.

## 3. Where each template lands in a project

| Template | Path in the project | Mirror | Written by | Changed in |
| --- | --- | --- | --- | --- |
| `requirements` | `docs/requirements.md` | Yes | Product Manager | Setup, change flow, PR 6, version acceptance |
| `architecture` | `docs/architecture.md` | Yes | Architect | Setup, change flow |
| `feature-design` | `docs/features/<feature-id>-<slug>/design.md` | Yes | Interface Designer | PR 1 |
| `test-plan` | `docs/features/<feature-id>-<slug>/test-plan.md` | Yes | Test Manager | PR 2, test fixes |
| `version-test-plan` | `docs/versions/<version>/test-plan.md` | Yes | Test Manager | Version planning, version acceptance |
| `adr` | `docs/adr/ADR-<NNNN>-<slug>.md` | Yes | Architect | Any architecture decision |
| `changelog` | `CHANGELOG.md` | Yes | Product Manager | Version release |
| `rules` | `docs/rules.md` | Yes | troy-mode | Setup, rule change flow |
| `progress` | `.troy-mode/progress.md` | No | Main session | Every stage. Local and git-ignored (Q8). |
| `escalation` | None. It is the shape of a chat message. | No | Main session | Each escalation |
| `pull-request` | `.github/pull_request_template.md`. GitHub fills it into every new PR. | No. PRs are in English. | Whoever opens the PR | Every PR |

The Chinese mirror of `<name>.md` is `<name>.zh-CN.md` in the same folder. `<slug>` is lowercase words joined by hyphens, for example `F04-export-csv`.

## 4. Document header

Every document with a mirror starts with YAML front matter. GitHub renders it as a table, so people see it, and F02's checks parse it. Every value is quoted, so scripts read each one as a string. The Chinese mirror is created in the same PR as the English document, from version 0.1 on.

English document:

```yaml
---
troy-doc: "requirements"
lang: "en"
version: "1.0"
updated: "2026-11-05"
status: "Approved by Troy on 2026-11-05"
mirror: "requirements.zh-CN.md"
---
```

Chinese mirror:

```yaml
---
troy-doc: "requirements"
lang: "zh-CN"
version: "1.0"
updated: "2026-11-05"
status: "Troy 已于 2026-11-05 批准"
mirror-of: "requirements.md"
---
```

| Field | Meaning |
| --- | --- |
| `troy-doc` | Document ID, unique in the project. Examples: `requirements`, `architecture`, `F04-design`, `F04-test-plan`, `v0.2-test-plan`, `ADR-0003`, `changelog`, `rules`. |
| `lang` | `en` or `zh-CN`. |
| `version` | `"MAJOR.MINOR"`, quoted. Every content change raises MINOR by one. When Troy approves a document, it moves to the next MAJOR with MINOR 0. |
| `updated` | Date of the last content change, `YYYY-MM-DD`. |
| `status` | One line in the document's language. |
| `mirror` | English only. File name of the Chinese mirror. |
| `mirror-of` | Chinese only. File name of the English document. |

What F02 checks against this header (R12):

- An English document changed in a PR has a higher `version` than on `main`.
- Its mirror is changed in the same PR and has the same `troy-doc` and `version`.
- `mirror` and `mirror-of` point at each other.

## 5. Template contents

Each template holds the section headings below, fill-in markers, and short guidance. A fill-in marker is any text between `{{` and `}}`, for example `{{feature-id}}`. Guidance is an HTML comment that starts with `template:`. Both must be gone before the document merges (proposal D2). A section, field, or table with nothing to hold says None.

### 5.1 `requirements`

1. Goal.
2. Users.
3. How users interact with it, including the list of prototypes in `docs/prototypes/`.
4. Features. Table columns: ID, Feature, Hard dependencies, Soft dependencies, Version, Status.
5. Dependency graph (Mermaid) and topological order.
6. Version plan. Table columns: Version, Features, What makes it usable on its own.
7. Non-functional requirements, with a performance target table. Columns: ID, Target, How it is measured, Features it applies to.
8. Out of scope.
9. Open questions. Columns: ID, Question, Proposal, Decision.
10. Change log.

### 5.2 `architecture`

1. Context and constraints, with links to the non-functional requirements.
2. Tech stack. Columns: Part, Choice, Why.
3. Modules. Columns: Module, Owns, External interfaces, May depend on.
4. Dependency rules, as a Mermaid graph and a list. F03's dependency checker (R07) is configured from this section.
5. Data model.
6. Error handling.
7. Logging.
8. Naming and coding rules that add to R04 to R07.
9. Third-party dependencies. Columns: Name, Version, License, Why, Approved in (ADR ID).
10. Test setup: test runner, how tests are tagged with IDs (R10), how coverage is measured (R11).
11. Decision records: a list of ADRs.
12. Change log.

### 5.3 `feature-design` (PR 1)

1. Feature: ID, name, link to its row in the requirements, hard and soft dependencies.
2. Interfaces. One subsection per external interface, with:
   - Name and module.
   - Purpose, in one or two sentences.
   - Signature, in a code block in the project's language.
   - Parameters. Columns: Name, Type, Meaning, Constraints.
   - Return value.
   - Errors. Columns: Error, When.
   - Side effects, or "None".
   - Performance target ID from the requirements, or "None".
   - One usage example.
3. Changes to existing interfaces, or "None". Any change links to its change request (5.4).
4. Architect review. A checklist table (Item, Result, Note) with the six items in requirements 5.2, and a rounds log (Round, Issue, Resolution).
5. Change log.

### 5.4 `test-plan` (PR 2)

1. Feature and a link to its design.
2. Cases. Columns: ID, Level (unit, functional, integration, or performance), Interface, What it tests, Setup and input, Expected result.
3. Performance cases: target ID, machine, margin, baseline.
4. Not tested, with the reason for each.
5. Alignment log with the Interface Designer. Columns: Round, Question, Answer.
6. Change log.

### 5.5 `version-test-plan`

1. Version and its features.
2. End-to-end scenarios, taken from the requirements. Columns: ID, Scenario, Steps, Expected result.
3. Performance and stress cases. Columns: ID, Target ID, Load, Duration, Machine.
4. Devices. Columns: Device, Operating system, Run by.
5. Acceptance record. Columns: Date, Result, Troy's notes.
6. Change log.

### 5.6 `adr`

1. Title and ID.
2. Status: Proposed, Accepted, or Superseded by another ADR.
3. Context.
4. Decision.
5. Options considered. Columns: Option, Pros, Cons.
6. Consequences.
7. Related features and rules.

### 5.7 `changelog`

One section per version, newest first, headed `vMAJOR.MINOR.PATCH (YYYY-MM-DD)`. Each section has Added, Changed, and Fixed lists. Every item names its feature or bug ID.

### 5.8 `rules`

A table with columns ID, Rule, Type, Enforced by, Scope, Since. Type is Hard, Soft, Review, or Process, defined as in requirements section 6. Scope is `troy-mode` for rules from troy-pstack and `project` for this project's own rules. The template ships with R01 to R19 copied from requirements section 6.

### 5.9 `progress`

English only, because it is a working file the main session rewrites at every stage. Fields:

- Current version and its features.
- Current feature and stage (1 to 6, or bug A or B).
- Open PRs, with links.
- Waiting on Troy.
- Open issues.
- Next action.
- Last updated.

### 5.10 `escalation`

The fields of an escalation message. troy-mode writes it in the language Troy uses in the session.

- Stopped at: feature and stage.
- Why: which trigger in requirements 5.7.
- Facts: what each side says, with links.
- Options: each with its consequences.
- Recommendation and the reason.

### 5.11 `pull-request` (D1)

**Title.** `[<ID> <stage>] <summary>`, or `[<kind>] <summary>` for PRs that belong to no feature or bug. F02 reads the kind from the title. F02's design decides exactly which paths each kind may touch.

| Kind | Title example | Holds |
| --- | --- | --- |
| Feature PR 1 | `[F04 1/6 design] Export history as CSV` | Documents |
| Feature PR 2 | `[F04 2/6 test-plan] Export history as CSV` | Documents |
| Feature PR 3 | `[F04 3/6 mock] Export history as CSV` | Source |
| Feature PR 4 | `[F04 4/6 tests] Export history as CSV` | Tests |
| Feature PR 5 | `[F04 5/6 impl] Export history as CSV` | Source |
| Feature PR 6 | `[F04 6/6 accept] Export history as CSV` | Documents |
| Bug PR A | `[B12 A/B test] Crash on empty history` | Tests |
| Bug PR B | `[B12 B/B fix] Crash on empty history` | Source |
| Test fix | `[F04 test-fix] Wrong expected date format in F04-T03` | Tests |
| Documents | `[docs] Requirements change for offline mode` | Documents |
| Rule change | `[rules] Add P01, no global state` | Rules table and check config |
| Refactor | `[refactor] Split storage.py` | Source |

**Description sections.**

1. Why. The goal, in one or two sentences.
2. What. The change, with the IDs it covers.
3. Checks. What ran and the result.
4. Soft-limit reason. Why the PR passes R03 or R06, or "None".

## 6. ID formats

| Thing | Format | Example |
| --- | --- | --- |
| Feature | `F` and two digits (three once there are more than 99) | `F04` |
| Test case | Feature ID, `-T`, two digits | `F04-T07` |
| Bug | `B` and the GitHub issue number (proposal D3) | `B12` |
| End-to-end scenario | Version, `-S`, two digits | `v0.2-S03` |
| Performance target | `PT` and two digits | `PT02` |
| ADR | `ADR-` and four digits | `ADR-0003` |
| troy-mode rule | `R` and two digits | `R11` |
| Project rule | `P` and two digits | `P01` |
| Open question | `Q` and a number | `Q4` |

R10 tags each test with a feature ID or a bug ID in these formats. F03 decides how each language attaches the tag.

## 7. Feature status labels

The features table in a project's requirements changes only in PR 6, at version acceptance, and through the change flow, because R02 keeps documents out of source and test PRs. The stage in between lives in the progress file.

| Label | Set when |
| --- | --- |
| Not started | The requirements are approved. |
| Passes tests on main | PR 6 merges. The feature's tests are now must-pass. |
| Usable on Troy's devices | Troy accepts the version that contains it. |
| Needs rework | An approved change affects it. The label names the change. |

## 8. How F01 is checked

F01 has no code, so its check is a review:

- Every template marked "Yes" in section 3, and the README, has a Chinese mirror with the same headings and the same table columns, in the same order.
- Every template with a mirror starts with the header from section 4.
- One sample project folder, outside the repository, gets the `requirements` and `feature-design` templates filled in for a toy feature, to confirm the templates are usable. The sample is not committed.

From F02 on, scripts check headers and mirrors automatically.

## 9. Decisions for Troy

Troy approved all six proposals on 2026-11-05.

| ID | Decision | Proposal |
| --- | --- | --- |
| D1 | F02 has to know each PR's stage (R02) and read a soft-limit reason (R03). Nothing in the requirements says where that comes from. | Add PR title and description templates to F01. Title: `[F04 3/6 mock] <summary>` or `[B12 A/B test] <summary>`. Description sections: Why, What, Checks, Soft-limit reason. This adds to F01's scope, so it needs your approval. |
| D2 | A merged document could still contain template markers. | F02 rejects a PR whose documents contain `{{` markers or `template:` comments. This adds a check to F02's scope. |
| D3 | Requirements 5.3 uses bug IDs but does not say where bugs are recorded. | GitHub issues with the label `bug`. Bug ID is `B` plus the issue number. |
| D4 | Language of the progress file. | English only (section 5.9). |
| D5 | Header format. | YAML front matter (section 4) instead of the visible table that `docs/troy-mode/requirements.md` uses. troy-pstack's own documents keep their current format, because troy-pstack is not a troy-mode project. |
| D6 | Location of troy-mode files in the plugin. | One top-level `troy-mode/` folder (section 2). Only skills, agents, and hooks go in the plugin's standard folders. |

## 10. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-05 | First draft. |
| 1.0 | 2026-11-05 | Approved by Troy with D1 to D6. Adds the PR template (section 5.11) and the Chinese README. |
| 1.1 | 2026-11-05 | Fixes from a trial fill of the requirements and feature-design templates. Every front matter value is quoted. The mirror is created with the English document. A marker is any text in double braces. Empty parts say None. |
