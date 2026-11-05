---
troy-doc: "requirements"
lang: "en"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "Draft. Waiting for Troy's approval."
mirror: "requirements.zh-CN.md"
---

# {{project-name}} requirements

<!-- template: The Product Manager fills this in after talking with Troy until the requirements are clear. Write short declarative sentences. When Troy approves, set version to "1.0". Write None for a section, field, or table that has nothing to hold. Remove every template comment and every {{marker}} before the document merges. -->

## 1. Goal

<!-- template: What the project does and the problem it solves, in two to four sentences. -->

{{goal}}

## 2. Users

<!-- template: Who uses it, on which devices, and how often. -->

{{users}}

## 3. How users interact with it

<!-- template: The main flows, step by step. Every screen or command that matters gets a prototype. A prototype is a clickable HTML wireframe. In a command-line project it may instead be a Markdown file with a terminal session transcript: the commands typed and the output shown. -->

{{interaction}}

### 3.1 Prototypes

| Prototype | Feature | File |
| --- | --- | --- |
| {{prototype-name}} | {{feature-id}} | `docs/prototypes/{{feature-id}}-{{slug}}.{{html or md}}` |

## 4. Features

<!-- template: Break features down finely. Each feature's implementation must fit in one source PR (R03: at most 500 changed lines in at most 5 files). A hard dependency means the feature cannot be built without the other one. A soft dependency means it can be built against the other one's mock. Separate several dependencies in one cell with commas. Status is one of: Not started, Passes tests on main, Usable on Troy's devices, Needs rework (name the change). -->

| ID | Feature | Hard dependencies | Soft dependencies | Version | Status |
| --- | --- | --- | --- | --- | --- |
| {{feature-id}} | {{feature}} | {{feature-ids, or None}} | {{feature-ids, or None}} | {{version}} | Not started |

## 5. Dependency graph and order

<!-- template: Draw hard dependencies as solid arrows and soft dependencies as dashed arrows. Both kinds count. The graph must have no cycle, and the order must respect every arrow. A cycle means the breakdown is wrong. Move the shared part into its own feature and draw the graph again. -->

```mermaid
flowchart LR
  {{feature-id}} --> {{feature-id}}
  {{feature-id}} -.-> {{feature-id}}
```

Topological order: {{F01, F02, ...}}

## 6. Version plan

<!-- template: Group consecutive features in the order into versions. Each version must be usable on its own. Name versions vMAJOR.MINOR, for example v0.1. -->

| Version | Features | What makes it usable on its own |
| --- | --- | --- |
| {{version}} | {{feature-ids}} | {{reason}} |

## 7. Non-functional requirements

<!-- template: Speed, privacy, hardware limits, platforms, languages, offline use, and anything else that is not a feature. -->

- {{requirement}}

### 7.1 Performance targets

<!-- template: Only targets that can be measured. Write "None" in place of the table if there are none. -->

| ID | Target | How it is measured | Features |
| --- | --- | --- | --- |
| PT{{nn}} | {{target}} | {{method}} | {{feature-ids}} |

## 8. Out of scope

- {{item}}

## 9. Open questions

| ID | Question | Proposal | Decision |
| --- | --- | --- | --- |
| Q{{n}} | {{question}} | {{proposal}} | Open |

## 10. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | First draft. |
