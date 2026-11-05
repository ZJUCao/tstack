---
troy-doc: "{{version}}-test-plan"
lang: "en"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "Draft."
mirror: "test-plan.zh-CN.md"
---

# {{version}} version test plan

<!-- template: The Test Manager writes this when the version is planned, not at the end. Write None for a section, field, or table that has nothing to hold. Remove every template comment and every {{marker}} before the document merges. -->

## 1. Version

- Version: {{version}}
- Features: {{feature-ids}}
- Requirements: [docs/requirements.md](../../requirements.md#6-version-plan)

## 2. End-to-end scenarios

<!-- template: Take each scenario from the user flows in the requirements. IDs are {{version}}-S01, {{version}}-S02, and so on. -->

| ID | Scenario | Steps | Expected result |
| --- | --- | --- | --- |
| {{version}}-S01 | {{scenario}} | {{steps}} | {{expected-result}} |

## 3. Performance and stress cases

<!-- template: Stress tests need the whole system, so they live here and not in feature test plans. Continue the scenario numbering. -->

| ID | Target | Load | Duration | Machine |
| --- | --- | --- | --- | --- |
| {{version}}-S{{nn}} | PT{{nn}} | {{load}} | {{duration}} | {{machine}} |

## 4. Devices

| Device | Operating system | Run by |
| --- | --- | --- |
| {{device}} | {{operating-system}} | {{Troy or Claude}} |

## 5. Acceptance record

<!-- template: Troy fills in or confirms this row on accepting the version. -->

| Date | Result | Troy's notes |
| --- | --- | --- |
| {{YYYY-MM-DD}} | {{Accepted or Not accepted}} | {{notes}} |

## 6. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | First draft. |
