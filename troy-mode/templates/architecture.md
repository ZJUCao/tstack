---
troy-doc: "architecture"
lang: "en"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "Draft. Waiting for Troy's approval."
mirror: "architecture.zh-CN.md"
---

# {{project-name}} architecture

<!-- template: The Architect writes this after Troy approves the requirements. It covers what crosses features. Each feature's interfaces go in that feature's design, not here. When Troy approves, set version to "1.0". Write None for a section, field, or table that has nothing to hold. Remove every template comment and every {{marker}} before the document merges. -->

## 1. Context and constraints

<!-- template: The non-functional requirements that shape the design. Link each one to its place in docs/requirements.md. -->

- {{constraint}}

## 2. Tech stack

| Part | Choice | Why |
| --- | --- | --- |
| {{part}} | {{choice}} | {{reason}} |

## 3. Modules

<!-- template: One row per module. troy-check reads this table for R07, so keep the paths exact. Owns lists the module's files as path patterns in backticks, then what the module is responsible for. External interfaces lists, as path patterns in backticks, the only files other modules may import. May depend on lists the only modules it may import, or None. -->

| Module | Owns | External interfaces | May depend on |
| --- | --- | --- | --- |
| {{module}} | {{path patterns, then responsibility}} | {{interface path patterns}} | {{modules, or None}} |

## 4. Dependency rules

<!-- template: The graph must have no cycle. F03's dependency checker (R07) is configured from this section, so use the module names from section 3 exactly. -->

```mermaid
flowchart TD
  {{module-a}} --> {{module-b}}
```

- {{rule}}

## 5. Data model

<!-- template: Entities, their fields and types, and how they relate. -->

{{data-model}}

## 6. Error handling

<!-- template: How errors are represented, where they are caught, and what users see. -->

{{error-handling}}

## 7. Logging

<!-- template: What is logged, at which level, where logs go, and what is never logged. -->

{{logging}}

## 8. Naming and coding rules

<!-- template: Only rules that add to R04 to R07 in docs/rules.md. A rule a tool can check also goes into docs/rules.md as a project rule (P01, P02, and so on). -->

- {{rule}}

## 9. Third-party dependencies

<!-- template: Every dependency needs the Architect's approval (R16), recorded in an ADR. -->

| Name | Version | License | Why | Approved in |
| --- | --- | --- | --- | --- |
| {{name}} | {{version}} | {{license}} | {{reason}} | ADR-{{NNNN}} |

## 10. Test setup

- Test runner: {{runner}}
- How tests are tagged with feature and bug IDs (R10): {{tagging}}
- How changed-code coverage is measured (R11): {{coverage-tool}}

## 11. Decision records

| ADR | Title | Status |
| --- | --- | --- |
| ADR-{{NNNN}} | {{title}} | {{status}} |

## 12. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | First draft. |
