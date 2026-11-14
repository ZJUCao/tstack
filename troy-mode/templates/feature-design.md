---
troy-doc: "{{feature-id}}-design"
lang: "en"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "Draft. In Architect review."
mirror: "design.zh-CN.md"
---

# {{feature-id}} {{feature-name}}: interface design

<!-- template: The Interface Designer writes this for PR 1. Design external interfaces only, meaning what other code calls. Internal functions are the Developer's choice. Write None for a section, field, or table that has nothing to hold. Remove every template comment and every {{marker}} before the document merges. -->

## 1. Feature

- ID and name: {{feature-id}} {{feature-name}}
- Requirement: [docs/requirements.md](../../requirements.md#4-features)
- Hard dependencies: {{feature-ids, or None}}
- Soft dependencies: {{feature-ids, or None}}

## 2. Interfaces

<!-- template: One subsection per external interface. Copy the whole subsection for each one and number them 2.1, 2.2, and so on. An interface is whatever other modules or users call: a function, a class, a command-line command, an HTTP endpoint, or a screen. For a command-line command, the signature is its usage line, the parameters are its arguments and options, and the return value is its exit code and output. Design the outermost surface. The functions behind it are the Developer's choice. -->

### 2.1 `{{interface-name}}`

- Module: {{module from docs/architecture.md section 3}}
- Purpose: {{one or two sentences}}

Signature:

```{{language}}
{{signature}}
```

Parameters:

| Name | Type | Meaning | Constraints |
| --- | --- | --- | --- |
| {{name}} | {{type}} | {{meaning}} | {{constraints}} |

- Return value: {{type and meaning, or None}}

Errors:

| Error | When |
| --- | --- |
| {{error}} | {{condition}} |

- Side effects: {{side-effects, or None}}
- Performance target: {{PT ID from the requirements, or None}}

Example:

```{{language}}
{{usage-example}}
```

## 3. Changes to existing interfaces

<!-- template: Write None, or list each change with a link to the merged [docs] PR that approved it in the requirements (troy-mode change flow). -->

{{changes, or None}}

## 4. Architect review

| Item | Result | Note |
| --- | --- | --- |
| Fits the module layout and the data model | {{Pass or Fail}} | {{note}} |
| Follows the error handling and naming conventions | {{Pass or Fail}} | {{note}} |
| Does not duplicate an existing interface | {{Pass or Fail}} | {{note}} |
| Depends only on features earlier in the order | {{Pass or Fail}} | {{note}} |
| Adds no hidden coupling between modules | {{Pass or Fail}} | {{note}} |
| Changes an implemented interface only through the change flow | {{Pass or Fail}} | {{note}} |
| The summary for Troy says what the design says, and lists every point Troy decides | {{Pass or Fail}} | {{note}} |

<!-- template: One row per review round. After round 3 without agreement, troy-mode escalates to Troy (R17). -->

| Round | Issue | Resolution |
| --- | --- | --- |
| 1 | {{issue}} | {{resolution}} |

## 5. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | First draft. |
