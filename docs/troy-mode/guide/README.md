# troy-mode guide

| | |
| --- | --- |
| Version | 0.1 |
| Date | 2026-11-09 |
| Source of truth | This English file. [`README.zh-CN.md`](README.zh-CN.md) is the Chinese mirror. |

> **troy-mode is Troy's own work.** Troy designed it and built it in this fork. It is not part of Lauren Tan's pstack, and Lauren Tan and Cursor have not reviewed or endorsed it. It reuses pstack skills such as `how`, `why`, `interrogate`, and `correct` without changing them, and it does not change how `poteto-mode` behaves. It is under the same MIT License as the rest of troy-pstack.

troy-mode's parts are the skills `troy-mode` and `troy-init`, the six `troy-*` agents, the hooks in `hooks/hooks.json`, everything under `troy-mode/`, and the documents in `docs/troy-mode/`. The rest of troy-pstack is Lauren Tan's pstack, ported to Claude Code: almost every other skill, playbook, agent, and guide page, such as `poteto-mode` and the guide in `docs/guide/`, is her work, used under the MIT License ([README: credit and license](../../../README.md#credit-and-license)).

## What troy-mode is

troy-mode takes a software project from requirements to a released version through a fixed pipeline of roles. Each role works in its own context, and a different role reviews its output. Automated checks enforce the rules, so the rules do not depend on Claude remembering them ([requirements section 1](../requirements.md#1-goal)).

## The one thing to remember

Type `/troy-pstack:troy-mode` and what you want, in your own words:

```text
/troy-pstack:troy-mode next feature
```

troy-mode works out which flow the request belongs to, runs the roles, opens and merges the PRs, and stops only where it needs you: an approval, a test on your own devices, or an escalation. It talks to you in your language. Everything it writes into the project is in English, with Chinese mirrors for the documents.

## How far it has run

No part of troy-mode is past "Runs on a sample project" yet. The main path of each flow in this guide ran once on the scratch repository `ZJUCao/troy-mode-trial`, a Python project, and the examples quote those runs. Some paths have not run yet: the side PRs for a disputed test and a coverage gap, a dependency that you accept, an approval you give by merging on GitHub, the question after the first features, the Architect writing a project's architecture (the trial's was prepared), a patch release, a failed scenario or a deferred bug at release, changing a rule or adjusting an R rule, a project that already has code, and any C/C++ project. The pilot (F11) is troy-mode's first use on a real project, and this guide's first real reader. The status of each part is in [requirements section 7.2](../requirements.md#72-feature-list).

## Pages

Read them in this order the first time.

| Page | What it covers |
| --- | --- |
| [1. Install](01-install.md) | What your PC needs, installing and updating troy-pstack, the merge permission, and each role's model |
| [2. Start a project](02-start.md) | Setup, the requirements, the architecture, the language step, and a project that already has code |
| [3. Build features](03-features.md) | The feature loop: the six PRs, your approvals, reviews, and side PRs |
| [4. Bugs and changes](04-bugs-and-changes.md) | Fixing a bug, changing a requirement, and questions that open no PR |
| [5. Release a version](05-release.md) | The version test plan, the release test, your test on your devices, and the retrospective |
| [6. Rules](06-rules.md) | Adding, changing, and retiring a rule, and proposing one for every project |
| [7. Where you take part](07-taking-part.md) | The steps that wait for you, escalations, what troy-mode does alone, status labels, and continuing in a new session |
| [8. Reference](08-reference.md) | Every request, PR title, comment heading, file, config key, and rule, and fixes for common problems |
| [9. Changing troy-mode](09-changing-troy-mode.md) | Work on troy-mode itself in troy-pstack |

## Where the details live

This guide says what you type and what you see. How each step works inside is in the requirements and the designs, and the guide links to them instead of repeating them:

- [Requirements](../requirements.md): the goal, the process, the rules R01 to R22, and the feature list.
- [Designs](../design/): one per feature, F01 to F11. [F07](../design/F07-entry-skill.md) is the entry skill and the feature loop, [F08](../design/F08-release.md) the release, and [F09](../design/F09-rule-change.md) the rule change.
- The skills that run it: [`skills/troy-mode/SKILL.md`](../../../skills/troy-mode/SKILL.md) and [`skills/troy-init/SKILL.md`](../../../skills/troy-init/SKILL.md).
