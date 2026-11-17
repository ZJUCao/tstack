# troy-mode templates

| | |
| --- | --- |
| Version | 1.1 |
| Date | 2026-11-05 |
| Source of truth | This English file. [`README.zh-CN.md`](README.zh-CN.md) is the Chinese mirror. |

`troy-init` copies these templates into a project, and troy-mode's roles fill them in. This README is the reference roles use while they work. [The F01 design](../../docs/troy-mode/design/F01-templates.md) records why each choice was made.

## 1. Templates

| Template | Path in the project | Chinese mirror | Written by | Changed in |
| --- | --- | --- | --- | --- |
| [`requirements`](requirements.md) | `docs/requirements.md` | Yes | Product Manager | Setup, change flow, PR 6, version acceptance |
| [`architecture`](architecture.md) | `docs/architecture.md` | Yes | Architect | Setup, change flow |
| [`feature-design`](feature-design.md) | `docs/features/<feature-id>-<slug>/design.md` | Yes | Interface Designer | PR 1 |
| [`test-plan`](test-plan.md) | `docs/features/<feature-id>-<slug>/test-plan.md` | Yes | Test Manager | PR 2, test fixes |
| [`version-test-plan`](version-test-plan.md) | `docs/versions/<version>/test-plan.md` | Yes | Test Manager | Version planning, version acceptance |
| [`adr`](adr.md) | `docs/adr/ADR-<NNNN>-<slug>.md` | Yes | Architect | Any architecture decision |
| [`changelog`](changelog.md) | `CHANGELOG.md` | Yes | Product Manager | Version release |
| [`rules`](rules.md) | `docs/rules.md` | Yes | troy-mode | Setup, rule change flow |
| [`progress`](progress.md) | `.troy-mode/progress.md` | No | Main session | Every stage. Local and git-ignored. |
| [`escalation`](escalation.md) | None. It is the shape of a chat message. | No | Main session | Each escalation |
| [`pull-request`](pull-request.md) | `.github/pull_request_template.md` | No. PRs are in English. | Whoever opens the PR | Every PR |
| [`summary-for-troy`](summary-for-troy.md) | None. It opens a PR's description. | No. It holds both languages, Chinese first. | The role that writes the document | Every design, test plan, requirements, and architecture PR |
| [`progress-issue`](progress-issue.md) | None. It is the body of a feature's progress issue on GitHub. | No. It holds both languages, Chinese first. | troy-mode's engine (`troy_flow.py issues`), in code; the main session posts it | Every sync, until the feature's acceptance |
| [`device-test-issue`](device-test-issue.md) | None. It is the body of a version's device-test checklist on GitHub. | No. It holds both languages, Chinese first. | troy-mode's engine (`troy_flow.py issues`), in code; Troy ticks it | After a release test passes, and at a new run |
| [`idea-issue`](idea-issue.md) | `.github/ISSUE_TEMPLATE/idea.md` | No. It holds both languages. | Troy, when opening an idea on GitHub | Never; troy-init writes it |

The Chinese mirror of `<name>.md` is `<name>.zh-CN.md` in the same folder. `<slug>` is lowercase words joined by hyphens, for example `F04-export-csv`.

## 2. Markers and guidance

- A fill-in marker is any text between `{{` and `}}`, for example `{{feature-id}}` or `{{feature-ids, or None}}`.
- Guidance is an HTML comment that starts with `template:`.
- A section, field, or table with nothing to hold says None (无 in a Chinese mirror).
- Both must be gone before a document merges. F02 rejects a PR whose documents still hold either one.

## 3. Document header

Every document with a mirror starts with YAML front matter. Every value is quoted, so scripts read each one as a string. The Chinese mirror is created in the same PR as the English document, from version 0.1 on.

| Field | Meaning |
| --- | --- |
| `troy-doc` | Document ID, unique in the project, for example `requirements` or `F04-design`. |
| `lang` | `en` or `zh-CN`. |
| `version` | `"MAJOR.MINOR"`, quoted. Every content change raises MINOR by one. When Troy approves a document, it moves to the next MAJOR with MINOR 0. |
| `updated` | Date of the last content change, `YYYY-MM-DD`. |
| `status` | One line in the document's language. |
| `mirror` | English only. File name of the Chinese mirror. |
| `mirror-of` | Chinese only. File name of the English document. |

A PR that changes an English document raises its `version` and changes the mirror to the same `version` (R12).

## 4. ID formats

| Thing | Format | Example |
| --- | --- | --- |
| Feature | `F` and two digits (three once there are more than 99) | `F04` |
| Test case | Feature ID, `-T`, two digits | `F04-T07` |
| Bug | `B` and the GitHub issue number. Bugs are GitHub issues labeled `bug`. | `B12` |
| End-to-end scenario | Version, `-S`, two digits | `v0.2-S03` |
| Performance target | `PT` and two digits | `PT02` |
| ADR | `ADR-` and four digits | `ADR-0003` |
| troy-mode rule | `R` and two digits | `R11` |
| Project rule | `P` and two digits | `P01` |
| Open question | `Q` and a number | `Q4` |

## 5. Feature status labels

The features table in `docs/requirements.md` changes only in PR 6, at version acceptance, and through the change flow. The stage in between lives in the progress file.

| Label | Set when |
| --- | --- |
| Not started | The requirements are approved. |
| Passes tests on main | PR 6 merges. The feature's tests are now must-pass. |
| Ran for real on Troy's PC | PR 6 merges with a real run in which the feature's own commands ran on Troy's PC and matched, apart from those that wait for a later feature (F12). |
| Usable on Troy's devices | Troy accepts the version that contains it. |
| Needs rework | An approved change affects it. The label names the change. |

## 6. PR kinds

The PR title is `[<ID> <stage>] <summary>`, or `[<kind>] <summary>` for a PR that belongs to no feature or bug.

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
| Rule test cleanup | `[P01 test-fix] Apply P01 to tests` | Tests fixed for a project rule |
| Version tests | `[v0.1 tests] End-to-end and stress tests` | Tests in `version-tests/` |
| Documents | `[docs] Requirements change for offline mode` | Documents |
| Rule change | `[rules] Add P01, no global state` | Rules table and check config |
| Refactor | `[refactor] Split storage.py`, or a rule's cleanup: `[refactor] Apply P01 to storage` | Source |

The description has four sections: Why, What, Checks, and Soft-limit reason. A design, test plan, requirements, or architecture PR opens with the summary for Troy before them, in Chinese and then English (R22).
