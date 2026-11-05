---
troy-doc: "{{feature-id}}-test-plan"
lang: "en"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "Draft. Being aligned with the Interface Designer."
mirror: "test-plan.zh-CN.md"
---

# {{feature-id}} {{feature-name}}: test plan

<!-- template: The Test Manager writes this for PR 2, from the interface design only, never from code. Each case tests behavior a caller can observe. Write None for a section, field, or table that has nothing to hold. Remove every template comment and every {{marker}} before the document merges. -->

## 1. Feature

- ID and name: {{feature-id}} {{feature-name}}
- Design: [design.md](design.md)

## 2. Cases

<!-- template: Level is unit, functional, integration, or performance. Case IDs are {{feature-id}}-T01, {{feature-id}}-T02, and so on. The Test Engineer tags each test with the feature ID (R10). -->

| ID | Level | Interface | What it tests | Setup and input | Expected result |
| --- | --- | --- | --- | --- | --- |
| {{feature-id}}-T01 | {{level}} | `{{interface-name}}` | {{behavior}} | {{setup-and-input}} | {{expected-result}} |

## 3. Performance cases

<!-- template: Only for interfaces with a performance target (R14). They run after implementation, on a fixed machine. Write None in place of the table if there are none. -->

| ID | Target | Machine | Margin | Baseline |
| --- | --- | --- | --- | --- |
| {{feature-id}}-T{{nn}} | PT{{nn}} | {{machine}} | {{margin}} | {{baseline, or First run}} |

## 4. Not tested

<!-- template: Write None in place of the table if everything in the design is tested. -->

| What | Why |
| --- | --- |
| {{item}} | {{reason}} |

## 5. Alignment with the Interface Designer

<!-- template: One row per question. After round 3 without agreement, troy-mode escalates to Troy (R17). -->

| Round | Question | Answer |
| --- | --- | --- |
| 1 | {{question}} | {{answer}} |

## 6. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | First draft. |
