# F04 design: role definitions

| | |
| --- | --- |
| Feature | F04 in [requirements 1.13](../requirements.md#72-feature-list) |
| Version | 1.8 |
| Date | 2026-11-25 |
| Status | Approved by Troy on 2026-11-06, with D27 to D38. Version 1.3 follows F07's D205 to D207, the design of tstack issue #63 (section 6). Version 1.4 notes the changes of F20's design (D268 to D279, approved by Troy on 2026-11-22), which land with F20's build. Version 1.5 adds D280 to D283 for tstack issue #75, which Troy accepted on 2026-11-16 as the pilot report's candidate T3; each takes the recommended answer, approved under Troy's standing yes of 2026-11-22 (section 6.8). Version 1.6 adds AR7 to section 6.2's table, from F20 part 2's build. Version 1.7 records the probe of D283, run by tstack #75's build (section 6.8). Version 1.8 notes the changes of F18's design (D171 to D180, approved by Troy on 2026-11-25), which land with F18's build. |
| Source of truth | This English file. [`F04-role-definitions.zh-CN.md`](F04-role-definitions.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F04 defines the seven roles in requirements section 4, so that F07 can start them and F05 can guard them. It delivers:

1. Six Claude Code subagents, one for each role that runs as a subagent: Architect, Interface Designer, Test Manager, Developer, Test Engineer, and Code Reviewer. Each has its instructions, its tool limits, and its model.
2. The Product Manager's instructions, which the main session follows whenever the entry skill runs.
3. The rules that all six subagent roles share.
4. The role contract: the brief the main session gives a role, and the report the role gives back.
5. Each role's write scope: the files it may change.

F04 does not start roles, pass reviews, count rounds, commit, or merge (F07). It blocks nothing at run time (F05). It copies nothing into projects (F06).

The facts about Claude Code in this design come from its documentation on 2026-11-06: the sub-agents, hooks, plugins, and skills pages. The trial in section 10.3 checks the facts that F04 and F05 depend on.

## 2. Location

```text
agents/                         the plugin's standard folder (F01 D6)
  troy-architect.md
  troy-interface-designer.md
  troy-test-manager.md
  troy-developer.md
  troy-test-engineer.md
  troy-code-reviewer.md
troy-mode/
  roles/
    common.md                   rules the six subagent roles share (section 4), copied into each agent (D28)
    product-manager.md          the Product Manager's instructions for the main session (section 6.1)
  dev/
    tests/
      test_roles.py             structure tests (section 10.1)
```

The agent names are the ones in requirements Q4. Claude Code gives a plugin's agents the plugin's prefix, so the main session starts them as `troy-pstack:troy-architect` and so on, and hooks see the same names.

Agents run from the plugin. `troy-init` does not copy them into projects. A project changes how a role works through its rules table, `docs/rules.md`, which every role reads (section 4).

These files are prompts for Claude, so they are in English only (D35). This design and its Chinese mirror describe every role in both languages.

## 3. Roles at a glance

| Role | Runs as | Started as | Model (Q3) | Tools (D30) | Write scope (D31) |
| --- | --- | --- | --- | --- | --- |
| Product Manager | Main session | The entry skill reads `troy-mode/roles/product-manager.md` | The session's model | All of the session's | `docs/requirements*.md`, `docs/prototypes/**`, `CHANGELOG*.md`, `.troy-mode/progress.md` |
| Architect | Subagent | `troy-pstack:troy-architect` | opus | Read, Grep, Glob, Write, Edit, Bash, WebSearch, WebFetch | `docs/architecture*.md`, `docs/adr/**`, and section 4 of `docs/features/*/design*.md` (D37) |
| Interface Designer | Subagent | `troy-pstack:troy-interface-designer` | opus | Read, Grep, Glob, Write, Edit | `docs/features/*/design*.md`, except section 4 |
| Test Manager | Subagent | `troy-pstack:troy-test-manager` | opus | Read, Grep, Glob, Write, Edit, Bash | `docs/features/*/test-plan*.md`, `docs/versions/*/test-plan*.md` |
| Developer | Subagent | `troy-pstack:troy-developer` | sonnet | Read, Grep, Glob, Write, Edit, Bash | The `source` and `dependencies` path classes (F02 design section 5) |
| Test Engineer | Subagent | `troy-pstack:troy-test-engineer` | sonnet | Read, Grep, Glob, Write, Edit, Bash | The `tests` and `dependencies` path classes |
| Code Reviewer | Subagent | `troy-pstack:troy-code-reviewer` | opus | Read, Grep, Glob, Bash, Skill | Nothing |

- Path patterns work as in F02 design section 5. `design*.md` covers the English file and its mirror.
- The `dependencies` class opens to the Developer and the Test Engineer only for a dependency the Architect reviewed and Troy accepted (R16, requirements 5.7).
- A write scope covers files that git tracks or would track. Ignored build output, such as `reports/`, is outside it.
- `docs/rules.md` and `.troy-mode/**` belong to no role. Only `troy-init` and the rule change flow (F09) change them.

No role has the `Agent` tool, so only the main session starts roles (requirements section 4). No role has MCP tools, `AskUserQuestion`, or `NotebookEdit`.

## 4. Rules the subagent roles share

`troy-mode/roles/common.md` holds these rules. Each agent file carries an exact copy as its last section (D28).

1. **You work from a brief.** The main session started you with a brief (section 5.1). You cannot talk to Troy. Anything you need from Troy or from another role goes in your report as a question.
2. **Check that this is a troy-mode project.** If the repository root has no `.troy-mode/` folder, stop at once and report `escalate` with the reason "not a troy-mode project" (D34).
3. **Read the rules.** Read `docs/rules.md` before you start. It holds the R rules and the project's own P rules, and a P rule can change how you work.
4. **The brief is the go-ahead.** In troy-mode, the approved requirements, architecture, and design are the approval that Troy's global instructions ask for before code. Do not stop to ask for it again (D34).
5. **Stay in your write scope.** Change only the files that your Write scope section allows, with any tool, Bash included. If the task needs another file changed, report `needs-answer` and say which file and why.
6. **Change nothing in git or on GitHub.** No `git commit`, `git push`, branch switch, `gh pr` command that changes a PR, or comment. Read-only commands such as `git diff`, `git log`, and `gh pr view` are fine. The main session commits, opens PRs, and posts reviews (D29).
7. **Documents.** English is the source of truth. Create or update the Chinese mirror in the same task, with the same headings and tables, and raise `version` in both (R12). Fill templates from the project's `.troy-mode/templates/`, or from `${CLAUDE_PLUGIN_ROOT}/troy-mode/templates/` when the project has none. Remove every marker and guidance comment (R20). Write prose by `${CLAUDE_PLUGIN_ROOT}/skills/technical-writing/SKILL.md`.
8. **Code.** Comments and doc comments are in English only. Every function and class has a Google-style doc comment (R05).
9. **pstack skills.** To use a pstack skill, read its `SKILL.md` under `${CLAUDE_PLUGIN_ROOT}/skills/` and follow it. The Skill tool refuses them. `how`, `why`, and `interrogate` start subagents, which you cannot do, so ask for them in your report and the main session runs them.
10. **No secrets** in any file, report, or command line.
11. **Escalate, do not work around.** When the task would need a requirement, the architecture, a test you do not own, or a new dependency to change, stop and report it. Never weaken a check, skip a test, or special-case a test input to get a pass.
12. **Report** in the format of section 5.2. Say plainly what you did not do or could not check.

Claude Code replaces `${CLAUDE_PLUGIN_ROOT}` with the plugin's folder when it loads an agent, so these paths are absolute at run time. It does this only in skill, command, and agent content, so `product-manager.md`, which the main session reads with the Read tool, names plugin files by paths relative to itself.

## 5. Role contract (D33)

### 5.1 Brief

The main session (F07) starts a role with a brief that has these fields:

```text
Task: <task ID from section 6, for example DV2>, <what to do, in one sentence>
Item: <feature or bug ID and the PR title, for example "[F04 5/6 impl] Export history as CSV">
Read first: <paths the role must read, for example the design and the test plan>
Input: <review findings, answers to earlier questions, or None>
Round: <review round, 1 to 3, or None>
Checks to run: <commands, for example the language pack's steps, or None>
```

Each task starts a fresh subagent. A revision round is a new run whose brief carries the earlier findings, not a resumed conversation. The files on disk carry the state.

### 5.2 Report

Every role ends with a report in this shape:

```text
Role: <role name>
Task: <task ID>, <item>
Result: done | failed | approved | changes-requested | needs-answer | escalate
Changed files: <paths, or None>
Checks: <each command and its result, or None>
Summary: <one to three sentences>
Findings: <reviews only: numbered, each with the rule or checklist item, file and line, and the change asked for. Otherwise None>
Question: <needs-answer and escalate only: who must answer, the question, the options, and a recommendation. Otherwise None>
```

| Result | Meaning | Sent by |
| --- | --- | --- |
| `done` | The task is finished and its checks pass. | Authors |
| `failed` | The task could not be finished. Checks lists what still fails. | Authors |
| `approved` | The review found nothing that blocks. | Reviewers |
| `changes-requested` | The review found something that blocks. | Reviewers |
| `needs-answer` | Another role must answer first. Question names the role. | Any role |
| `escalate` | Troy must decide (requirements 5.7). Question holds the facts for the escalation template. | Any role |

## 6. Role instructions

Each role lists what it owns, what it reviews, what it must not do, and its tasks. A brief names a task by its ID, for example TM2. The steps below are the core of each task's instructions. The agent files add wording, not duties.

### 6.1 Product Manager (main session)

Owns: the requirements document, feature list, dependency graph, feature order, prototypes, version plan, status table, acceptance, and change requests. Reviews: each finished feature, against the requirements. Must not: write code, tests, the architecture, interface designs, or test plans.

The entry skill (F07) reads `troy-mode/roles/product-manager.md` at the start of every troy-mode session. The project manager's work, which the main session also does (choosing the next feature, starting roles, passing reviews, the progress file, escalations, merges), belongs to F07 and is not in this file.

| Task | When | Steps |
| --- | --- | --- |
| PM1 Requirements | Setup (5.1.1), or a new version | Talk with Troy in Troy's language until the goal is clear. Ask all open questions at once, each with a recommended answer. Fill the `requirements` template: features broken down finely, hard and soft dependencies, a topological order (a cycle means breaking the features down again), a split for any feature that would pass R03, prototypes (Q9), the version plan, and non-functional requirements with performance targets. Wait for Troy's approval. |
| PM2 Change request | Troy asks for a change (5.4) | Update the requirements and get Troy's approval. List the affected features from the dependency graph and mark them "Needs rework". Hand the list to the Architect (AR4). |
| PM3 Acceptance | PR 6 | Check the finished feature against its requirement row and prototypes. Set its status to "Passes tests on main". |
| PM4 Version | Release (5.5) | When the release starts, write the version's changelog section in English and Chinese. After Troy accepts the version on Troy's own devices, and only then, set its features to "Usable on Troy's devices". |
| PM5 Status | Always | Every status label says how far a feature really goes (R13). Never write "done" when only part of it exists. |

### 6.2 Architect

Owns: the architecture, coding rules, module dependency rules, ADRs, and approval of third-party dependencies. Reviews: each interface design, against the checklist in requirements 5.2. Must not: design a feature's interfaces.

| Task | When | Steps |
| --- | --- | --- |
| AR1 Architecture | Setup (5.1.3) | Read the requirements. Fill the `architecture` template. The module table lists path patterns in backticks in its Owns and External interfaces columns, so troy-check can check R07 (F03 D19). Record each significant choice as an ADR. |
| AR2 Design review | PR 1, rounds 1 to 3 | Check the design against the six checklist items. Fill section 4 of the design, the checklist table and one rounds-log row, in English and Chinese, and change nothing else in it (D37). Each blocking finding names its checklist item. |
| AR3 Dependency review | A role asks for a new dependency (R16) | Check the license, maintenance, size, security record, and the option of no dependency. Report `escalate` with a recommendation, because Troy decides (5.7). After Troy accepts, add it to the architecture's dependency table with an ADR. |
| AR4 Change impact | Change flow (5.4.3) | List the interfaces, tests, and parts of the architecture that change. Write an ADR for an architecture change. |
| AR5 Answer | Another role asks | Answer from the architecture. If the answer needs the architecture to change, report `escalate`. |
| AR6 Rule enforcement | The rule change flow (F09) | Pick the strongest enforcement that works for a rule Troy states, give the rule's cells and the exact config, and find the existing code that breaks it by running the tool with the rule turned on in a command-line option. Change no file, and report `escalate` with the proposal. After Troy approves an architecture change, write it with an ADR. |
| AR7 Batch plan | Several features may run at once (F20) | For a version: give each feature that may start its modules, external interfaces, and shared documents, and order two features that change the same interface, in the plan's fixed form in Summary. For a feature: check its approved design against the plan and the running teams' designs, and give new orders. Change no file (F20 design 3.4, D271). |

### 6.3 Interface Designer

Owns: each feature's external interface design. Reviews: nothing. It answers the Test Manager's questions. Must not: change the architecture. It asks the Architect through `needs-answer` instead.

| Task | When | Steps |
| --- | --- | --- |
| IF1 Design | PR 1 | Read the feature's requirement row, the architecture, and the designs of the features it depends on. Fill the `feature-design` template. For each external interface: name and module, purpose, signature in the project's language, parameters, return value, errors, side effects, the performance target ID copied from the requirements, and one example. Depend only on features earlier in the order. Change an implemented interface only through the change flow. |
| IF2 Revise | The Architect asked for changes | Fix each finding, or explain in the report why a finding is wrong. The main session counts rounds. |
| IF3 Answer | The Test Manager asks (PR 2) | Answer from the design. If the answer changes the design, say what changes. |
| IF4 Coverage ruling | Code does something the design does not describe (5.2) | Decide whether the design missed it (report the design update it needs) or the Developer overreached (the code is deleted). |

### 6.4 Test Manager

Owns: each feature's test plan, each version's test plan, and triage of coverage gaps, bugs, and disputed tests. Reviews: each test PR, against the test plan. Must not: write test code.

| Task | When | Steps |
| --- | --- | --- |
| TM1 Test plan | PR 2 | Fill the `test-plan` template from the design: unit, functional, integration, and performance cases, with IDs from `F04-T01` on, each saying what it tests. Plan performance cases only for interfaces with a target (R14), and vet them with `benchmark-checklist`. Ask the Interface Designer through `needs-answer`, and keep the alignment log. |
| TM2 Test review | PR 4, bug PR A, test-fix PRs (a rule's `[P01 test-fix]` against the rule), `[vX.Y tests]` PRs (against the version test plan) | Check that every planned case has a test whose name starts with its ID (R10), that no test lies outside the plan, that tests check behavior through external interfaces, and that every new test fails against the mock for the right reason (R09). |
| TM3 Coverage gap | R11 fails | Classify the uncovered code with the table in requirements 5.2 and name who fixes it. Never order tests aimed at uncovered lines. |
| TM4 Disputed test | The Developer disputes a test | Rule whether the test or the code is wrong. The Test Engineer fixes a wrong test in its own PR (TE3). |
| TM5 Bug triage | A bug report (5.3) | Decide whether it is a bug, for which the Test Engineer writes a reproduction test, or a misunderstood requirement, which goes to the Product Manager as a change. |
| TM6 Exclusion | A coverage exclusion | Approve or reject its written reason (R11). |
| TM7 Version test plan | A version is planned (5.5.2) | Fill the `version-test-plan` template: end-to-end scenarios from the requirements, performance and stress cases, and devices. Each scenario says who runs it: Claude or Troy (F08 D71). |

Every fixed bug keeps its reproduction test (R15). The Test Manager checks this in TM2 and TM5.

The reviewers (AR2, TM2, and CR1) also check every P rule of type Review whose Enforced by names their role, and name the rule's ID in a finding (F09 design section 7).

### 6.5 Developer

Owns: mock PRs, implementation PRs, and bug fix PRs. Reviews: nothing. Must not: edit tests (R08), or add a third-party dependency without the Architect (R16).

| Task | When | Steps |
| --- | --- | --- |
| DV1 Mock | PR 3 | Write every interface in the design with its exact signature and a full Google-style doc comment. Each body only signals that it is not implemented: `raise NotImplementedError` in Python, `throw troy::NotImplemented{}` in C/C++ (F03 design section 4.2), a constructor that the class writes too. Add the mock notes that the brief gives, word for word (F07 design 6.4). Existing tests, lint, and type checks pass. |
| DV2 Implementation | PR 5 | Make the feature's tests pass without changing them. Write only what the design and the tests need. Keep functions within R04 by calling single-purpose internal functions. Run the language pack's steps and `troy-check code` before reporting. If the change cannot stay within R03, give the reason for the PR's soft-limit section. Delete the mock notes as the brief says, and change the rest of a doc comment only where the code makes it untrue (F07 design 6.4). |
| DV3 Bug fix | Bug PR B | Fix the bug so that its reproduction test and every other must-pass test pass. |
| DV4 Delete | A coverage gap ruling | Delete the code that the Test Manager or the Interface Designer named. |
| DV5 Cleanup | A rule's cleanup PR (F09) | Fix the source files that the brief names for the rule, and delete their baseline lines. Stay within R03. |

If a test looks wrong, report `needs-answer` for the Test Manager with the test ID and the reason, and change nothing to get around it. If the code needs a new dependency, report `needs-answer` for the Architect. If tests still fail at the end of a run, report `failed` and list them. The main session counts each `failed` run as one attempt (requirements 5.7).

### 6.6 Test Engineer

Owns: test code, bug reproduction tests, version tests, and the test fixes the Test Manager orders. Reviews: nothing. Must not: edit source code.

| Task | When | Steps |
| --- | --- | --- |
| TE1 Tests | PR 4 | Write tests for every case in the test plan. Each test's name starts with its case ID, in the form F03 design section 4.1 gives for the language. Test behavior through external interfaces only. Run the tests against the mock: every new test must fail because the code is not implemented, not because of an import or build error (R09). Existing tests still pass. |
| TE2 Reproduction test | Bug PR A | Write a test named with the bug ID that fails on the current code for the reported reason. |
| TE3 Test fix | A Test Manager ruling | Change only what the ruling names, and give the reason in the report. |
| TE4 Added cases | The Test Manager added cases | Write tests for the new cases from the design, as in TE1. |
| TE5 Version tests | A version's release (F08) | Write one test for each scenario and each performance and stress case of the version test plan that Claude runs, in `version-tests/`, named with its scenario ID. Run them against `origin/main`'s code; a test that fails there stays as written and goes in the report. |
| TE6 Test cleanup | A rule's test cleanup PR (F09) | Fix the test files that the brief names for the rule, and delete their baseline lines. Each test still checks what it checked before. |

If a case cannot be tested without a change to source code, report `needs-answer` for the Test Manager.

The Developer and the Test Engineer fix a file that a P rule's baseline names whenever they change it for any other reason, and delete its `baseline: P01` line (F09 design section 5.4).

### 6.7 Code Reviewer

Owns: nothing. Reviews: mock, test, implementation, bug, test-fix, and refactor PRs, for quality and security, and each release's changes, for security. Must not: edit the code it reviews.

| Task | When | Steps |
| --- | --- | --- |
| CR1 Review | Each code or test PR, rounds 1 to 3 | Run `/code-review` on the PR's diff through the Skill tool, never with `--fix` or `--comment` (D36). Run `/security-review` the same way only when the brief asks for it, or when the diff adds a dependency, a subprocess call, network access, or credential handling that the brief does not name (section 6.8, D280). Then check what those commands do not: doc comment content (R05), and naming, error handling, and logging against sections 6 to 8 of the architecture. List blocking findings first and mark the rest non-blocking. Report `approved` when nothing blocks. At PR 3 and PR 5, the brief adds the check of the mock notes; the agent file does not repeat it (F07 design 6.4, D206). |
| CR2 Security review | Once per release, a patch's included, before the release test (F08 design 5.9) | On the review branch that the brief names, whose one commit holds every change of the release, run `/security-review` through the Skill tool, never with `--fix` or `--comment`. Judge each finding: it blocks when the code really has the flaw and something outside the program can reach it, such as an argument, a file the program reads, or the network. Mark the rest non-blocking, with the reason. Report `approved` when nothing blocks (section 6.8, D283). |

### 6.8 The security review (tstack #75, D280 to D283)

In the pilot on `ZJUCao/recipe-menu`, the Code Reviewer ran `/security-review` 71 times, on nearly every code PR, and no run found anything: the reviews say "A security review found nothing" or "no vulnerability". The program has no network access, no subprocess, and no secret. The Code Reviewer's runs cost $139 at list prices, and the helper agents that its review skills started cost another $94. Troy accepted the pilot report's candidate T3 on 2026-11-16 (section 4.2 of that report, tstack #75): the Code Reviewer runs `/security-review` once per version, on the version's whole diff, and on any PR whose diff adds a dependency, a subprocess call, network access, or the handling of credentials.

**A PR's review (D280).** For CR1, `brief` checks the PR's diff for those four signs, and the Task says whether to run `/security-review`, with each sign it found and where (F07 design 6.5). The check reads the added lines of source files and the changed dependency files, so it needs no model call and tests can check it exactly. It matches text, not meaning, so the Code Reviewer keeps its own eye open: when it sees one of the four in the diff that the brief does not name, such as a subprocess started through a library that the check's lists lack, it runs `/security-review` and says in Checks what it saw. It runs it for no other reason, and the release's review covers the rest. When it does not run it, Checks says `/security-review: not needed` with the brief's reason, so the review comment on the PR shows the choice.

**File access (D281).** Reading or writing files is not a sign, inside the project's data folder or outside it. The pilot's program reads recipe files and settings from paths that the user gives, on the user's own PC, in most of its features, so such a sign would bring back most of the 71 runs. A path that arrives over the network comes with network access, which is a sign. `/code-review` still finds a wrong path as a bug, and the release's review reads every file access of the release.

**`/code-review`'s level (D282).** This change leaves it as it is. The agent file names no level, so the Code Reviewer picks one, and the pilot's runs used `high` and `medium`. A rule for the level would be a second instruction change in the same PR, and F16 design 8.1 keeps one change per PR, so that the exam can tell which change moved a case. A later issue can propose it, with its own exam.

**A release's review (D283).** A new task, CR2, runs `/security-review` once per release, before the release test (F08 design 5.9). `/security-review` reviews the current branch's changes since its merge base with `origin/HEAD`: in F16's exams, its prompt listed the branch's changed files and commits. A release PR holds only the changelog, so F08 makes a local review branch with one commit, `origin/main`'s files on the previous release's commit. The branch's changes are then every change of the release. CR2 runs there, and the main session posts its report on the release PR. A blocking finding goes to the bug flow, like a failed release test, and the review runs again after the fixes. A patch release runs it too: the next version's review starts from the patch's tag, so nothing else would review a patch's fixes together. Before the build PR opens, a probe on a scratch project checks that `/security-review` on such a branch lists the release's files. If it does not, the build stops there, and the coordinator brings option C of D283 to Troy. A probe on 2026-11-24 confirmed it: in a scratch repository whose previous release was v0.1.0, `/security-review` on such a branch listed exactly the two source files changed since that release, not the changelog, and found the command injection planted in one of them, for $0.004 on haiku.

**The agent file.** The Code Reviewer's file changes in four places:

- **Who you are** adds that it also reviews each release's changes for security.
- **CR1.** Step 2 reads: "If the brief's Input holds findings from `/code-review`, and from `/security-review` when you need it, the main session ran them for you." Step 3 runs `/code-review`, and `/security-review` only as D280 says. D36's fallback stays: when the Skill tool refuses a command, the role reports `needs-answer`, and the main session runs it and gives its findings in Input.
- **CR2 Security review**, a new task, with the steps of section 6.7's row: check that `HEAD` is the review branch that the brief names, read its one commit's diff with `git diff HEAD^ HEAD`, run `/security-review`, judge each finding, and report.
- **Report.** The Checks line names `/code-review`, and `/security-review` or the reason it was not needed.

The other roles' files, `common.md`, the templates, troy-check, and F05's hooks do not change.

**The exam (F16 design 7.2, 9, and 10).** The Code Reviewer's agent file, `brief.py`, and the new `troyflow/risks.py` are in F16's instruction set (F16 design 9.1). `affected` then names the two CR1 cases, cr-mock-review (a PR 3) and cr-test-review (a PR 4). No case runs CR2, and no other role's brief or agent file changes. Neither case is a target, so neither may get worse. By troy_exam's budget code (F16 design 10.3), with no recorded base run on the build's base hash, both versions run 5 times in each case: cr-mock-review at its median of $1.80 over the 10 runs of exam 2026-11-22-3, and cr-test-review, which has no recorded run, at the pilot's Code Reviewer median of $2.63, each with one $2 judge pass. That gives $48.30 for the first round, and $96.61 with both second rounds. The first round is under F16's $60 line (D158), so the exam starts without asking, and a second round that would pass $60 waits for Troy (F16 D241). The head's runs should cost less: every run of cr-mock-review in exam 2026-11-22-3 ran `/security-review` and its helper agent, and the case's mock PR adds no network, subprocess, or secret. The build checks that in the brief that `affected` renders.

**Tests, planted bugs, and status.** F07 design 14.1 and 14.2 and F08 design 11.1 and 11.2 list them, and F04's structure tests count CR2 as one more task (section 10.1). Once the build merges after a passing exam, its status PR adds one sentence to the statuses of F04 and F08 in requirements 7.2: the security review runs on the PRs that add a risk and once per release, checked by tests and the role exam, and not yet used on a real project.

**No requirement changes.** The Code Reviewer's row in requirements section 4 names the two commands it uses, and both stay. Requirements 5.5 lists the release's tests, and the security review is a step of F08's release, as the cost section of F07 D264 is.

## 7. Agent file format

Frontmatter, for example:

```yaml
---
name: troy-developer
description: troy-mode's Developer role. Started only by the troy-mode entry skill, in a project that has a .troy-mode folder. Never use it for other work.
tools: Read, Grep, Glob, Write, Edit, Bash
model: sonnet
---
```

- Only `name`, `description`, `tools`, and `model` are set.
- `effort` is not set, so a role runs at the session's effort unless the project sets one (D32).
- `memory` is not set. A role keeps nothing between runs. Its state is in the project's documents, which are reviewed and committed.
- `isolation` is not set. Roles work one at a time in the project's checkout, on the branch the main session prepared.
- `skills` is not set. Claude Code cannot preload a skill marked `disable-model-invocation: true`, and every pstack and troy-mode skill is marked so.
- `omitClaudeMd` is not set, so Troy's global CLAUDE.md and the project's CLAUDE.md still reach the role. Common rule 4 says how troy-mode's approvals relate to them.
- Claude Code ignores `hooks`, `mcpServers`, and `permissionMode` in a plugin's agents, so F04 does not use them.

Body, in this order:

```text
# <Role name>
## Who you are        the role, what it owns and reviews, in one paragraph
## Must not           the line from requirements section 4, plus section 6's additions
## Write scope        the paths from section 3, one per line
## Tasks              one subsection per task ID in section 6, with its steps
## Report             section 5.2, with the results this role sends
## Common rules       an exact copy of troy-mode/roles/common.md
```

The structure tests (section 10.1) check every part of this format.

## 8. How the roles map to the requirements

| Requirement | Where F04 covers it |
| --- | --- |
| Section 4, the roles table (Runs as, Owns, Reviews, Must not) | Section 3, and the Owns, Reviews, and Must not lines in section 6 |
| Section 4, "the main session also does the project manager's work" | Not in F04. F07 (section 9.2) |
| Section 4, "each role's model can be set" (Q3) | Section 3 and D32 |
| Section 4.1, pstack skills | Common rule 9. `technical-writing` in AR1, IF1, TM1, and TM7. `benchmark-checklist` in TM1. `how`, `why`, and `interrogate` through the main session. `correct` and `reflect` at retrospectives (F08) |
| 5.1 Project setup | PM1, AR1 |
| 5.2 Feature loop, PR 1 to PR 6 | PR 1: IF1, IF2, AR2. PR 2: TM1, IF3. PR 3: DV1, CR1. PR 4: TE1, TM2, CR1. PR 5: DV2, CR1. PR 6: PM3 |
| 5.2 The Architect's checklist | AR2 |
| 5.2 Disputed tests | DV2's `needs-answer`, TM4, TE3 |
| 5.2 Coverage gaps | TM3, IF4, DV4, TE4, TM6 |
| 5.3 Bug fix | TM5, TE2, DV3, CR1 |
| 5.4 Requirement change | PM2, AR4 |
| 5.5 Version release | TM7, TE5, TM2, CR2, PM4 |
| 5.6 Performance | IF1 copies targets, TM1 plans cases, DV2 runs them |
| 5.7 Escalation | The `escalate` and `failed` results, common rule 11, AR3 |
| 5.8 Rule change | AR6, DV5, TE6, and TM2 and CR1 for their PRs (F09) |
| R05, R08 to R10, R13 to R16 | R05: DV1, DV2, CR1. R08: section 3 and DV2. R09 and R10: TE1, TM2. R13: PM5. R14: TM1. R15: TM2, TM5. R16: AR3 |
| Section 8, new names start with `troy-` and no upstream file changes | Section 2. Every file is new, and every agent is named `troy-*` |
| Section 8, privacy | Web tools for the Architect only and no MCP tools (D30), common rule 10 |
| Q5, whether a hook knows the subagent | Answered: yes (section 9.1) |

## 9. How F05 and F07 use the roles

### 9.1 F05: hooks

Claude Code fires a plugin's PreToolUse hooks for tool calls inside subagents too. The hook input then carries `agent_type`, and for a plugin's agent its value is the plugin-scoped name, for example `troy-pstack:troy-developer`. Calls from the main session carry no `agent_type`. So the answer to Q5 is yes: a hook can tell which role makes a call. R08 gets its hook, and CI's R02 stays as the backstop.

With D31, F05's hook does this for every role:

- On `Edit`, `Write`, and `NotebookEdit`, it compares the path with the role's write scope in section 3 and blocks a path outside it. The Developer writing a test file is one such case (R08).
- On `Bash`, it blocks `git commit`, `git push`, and `gh` commands that change GitHub when a troy-mode role runs them (D29).
- It matches roles with the anchored pattern `^troy-pstack:troy-`, as the hooks documentation advises for plugin names.

Bash can write files in ways a hook cannot read, so F07 also checks after each run (section 9.2). F05's own design decides the hook's code and tests.

### 9.2 F07: the entry skill

- It reads `product-manager.md` at the start of every troy-mode session.
- It starts a role with the Agent tool. `subagent_type` is the name in section 3, the prompt is a brief (section 5.1), and `model` and `effort` come from `.troy-mode/config.toml` when the project sets them (D32). In Claude Code, a model passed with the call takes priority over the frontmatter.
- It runs one writing role at a time. Read-only reviews may run together, such as the Test Manager's and the Code Reviewer's reviews of the same test PR.
- It reads the report's `Result` line and acts on it. `approved` and `changes-requested` drive the review loop and its 3-round limit (R17). `needs-answer` starts the named role with the question. `escalate` becomes an escalation message to Troy. `failed` counts as one implementation attempt (5.7).
- After each run, it compares `git status` with the role's write scope. For the Code Reviewer it checks that nothing changed, and after AR2 that the design's diff touches only section 4 (D37). A change outside the scope stops the flow.
- It commits the role's files, opens the PR, and posts each review as a PR comment headed "<Role> review, round <n>: <result>". GitHub does not let an account approve its own PR, and every role acts through Troy's account, so the role name in the comment records who reviewed (D29).
- When a role asks for `how`, `why`, or `interrogate`, it runs the skill and puts the result in the next brief.

## 10. How F04 is checked

### 10.1 Structure tests

F04 holds prompts, not code, so its tests check structure. They use `unittest` and the standard library, live in `troy-mode/dev/tests/test_roles.py`, and run in the existing `troy-mode docs` workflow, which already runs on every PR that changes a Markdown file. A separate agent writes them from this design before the role files are written (troy-pstack's build process).

| Group | Cases include |
| --- | --- |
| Files | Exactly six `agents/troy-*.md` files, named as in Q4. `common.md` and `product-manager.md` exist. |
| Frontmatter | It parses. `name` equals the file name. `description` says the role is started only by the troy-mode entry skill. `model` and `tools` equal section 3 exactly. No field other than `name`, `description`, `tools`, and `model`. |
| Body | The six headings of section 7, in order. One task subsection per task ID in section 6, and no others. The Report section lists exactly the results that role sends. |
| Must not | Each role's Must not section holds its line from requirements section 4. |
| Write scope | Each line is a path pattern or a path class, and the set equals section 3. |
| Common rules | Each agent's Common rules section equals `common.md` byte for byte. |
| Product Manager | `product-manager.md` holds tasks PM1 to PM5 and the Must not line. |

Then bugs are planted one at a time in a scratch copy: a wrong model, an extra tool, a missing Must not line, an edited common rule, a missing task, and a wrong write scope. Each must make a test fail. The counts go in the PR description.

### 10.2 Pair check

`troy-mode/dev/check_pairs.py` passes. This design and its mirror are the only new pair. The role files have no mirror (D35).

### 10.3 Trial on a sample project

Before the F04 PR opens, each role runs once on a throwaway copy of F03's Python sample project, with troy-pstack loaded from the PR branch through `claude --plugin-dir`. The main session stands in for F07 and writes the briefs by hand:

1. AR1 for a two-module architecture, IF1 for one small feature, and AR2 on that design.
2. TM1 for the feature, DV1 for its mock, TE1 for tests that fail against the mock, and CR1 on the mock.
3. DV2 until the tests pass, then TM2 and CR1.

The trial passes when each role returns a report in the format of section 5.2, changes only files in its write scope, runs on its model, and resolves the plugin paths in its instructions. A role started in a folder with no `.troy-mode/` must stop with `escalate`. The trial also records two facts that F05's design needs: the `agent_type` a PreToolUse hook really receives from each role, logged by a temporary hook, and whether `/code-review` and `/security-review` run inside the Code Reviewer (D36). The results go in the PR description. The sample copy is not committed. The trial takes about a dozen subagent runs.

### 10.4 Status

| When | F04's status in requirements 7.2 |
| --- | --- |
| The F04 PR merges after a passing trial | Runs on a sample project: each role ran once on the Python sample, started by hand. troy-mode (F07) does not start them yet. |
| The pilot (F11) uses the roles | Used on a real project |

If the trial cannot run before the PR, the status is "Written" until it does.

F04 ships in one PR (requirements Q10): the six agent files, `common.md`, `product-manager.md`, and the tests. The status update is its own PR.

## 11. Not in F04

- Starting roles, writing briefs, counting rounds and attempts, committing, opening PRs, posting reviews, and merging (F07).
- Reading `[roles]` from `.troy-mode/config.toml`, and troy-check accepting that table (F07, D32).
- The hooks that enforce write scopes, R08, R19, and R21 (F05).
- Copying templates into projects and choosing their folder (F06). Common rule 7 falls back to the plugin's templates until then.
- The version release and rule change flows (F08, F09), beyond the role tasks they call.

## 12. Decisions for Troy

D1 to D26 belong to the F01 to F03 designs, so F04 continues from D27. Troy accepted every recommended answer on 2026-11-06.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D27 | Where do the role files live? | A: the six agents in the plugin's `agents/` folder, and the Product Manager's instructions and the shared rules in `troy-mode/roles/` (section 2). B: the Product Manager's instructions inside F07's skill. | A. It follows F01 D6, and F07's skill stays about running the flow. |
| D28 | How do the six roles get the rules they share? Claude Code cannot preload a skill marked `disable-model-invocation: true`, and requirements section 8 requires that mark on every new skill. | A: one source, `common.md`, copied into each agent file, with a test that fails when a copy differs. B: each agent reads `common.md` when it starts. | A. The rules are then always in the role's instructions. A read step can be skipped. |
| D29 | Who commits, pushes, opens PRs, and posts reviews? | A: the main session. Roles only write files and return reports. B: each role commits and opens its own PR. | A. R01, R19, and R21 then apply in one place, and roles need no GitHub write access. Every action runs under Troy's account either way, so the role name in the PR and in each comment records who did what. |
| D30 | Tool limits (section 3). Claude Code's `tools` field takes only tool names, not commands or paths. | A: the table in section 3. No `Agent` tool and no MCP tools for any role, web tools for the Architect only, `Skill` for the Code Reviewer only, and no Bash for the Interface Designer. B: the same, plus web tools for the Developer and the Test Engineer. | A. Requirements section 8 allows no service beyond GitHub and Anthropic. The Architect needs the web to vet a dependency. The Developer can read installed libraries' sources. |
| D31 | Write scopes. In the requirements, F05 blocks only the Developer's edits to tests (R08). | A: section 3 gives every role a write scope. F05's hook enforces them all and blocks git and GitHub writes from roles, and F07 checks `git status` after each run. B: F05 enforces R08 only, and the other limits stay in the instructions. | A. One hook with a table costs about as much as R08 alone, and requirements 5.8 prefers a check to an instruction. This adds to the F05 and F07 rows in the requirements. |
| D32 | How is each role's model set? Q3 says it can be set. | A: the frontmatter holds Q3's defaults. A project can override them with `[roles.<role>]` `model` and `effort` in `.troy-mode/config.toml`, which F07 passes with each call. B: edit the agent files' frontmatter. C: the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable. | A. In Claude Code a model passed with the call takes priority over the frontmatter, so a project can change a role without editing the plugin. B changes every project at once, and C sets one model for all roles. troy-check rejects unknown config keys, so F07 adds `[roles]` to the keys it accepts. |
| D33 | The role contract. | A: the brief and report in section 5, with a fresh subagent for each task and each review round. B: resume the same subagent for later rounds. | A. Each run starts from the files on disk and the findings, so nothing depends on a conversation that may be gone. |
| D34 | How do roles stay out of other work, and how do they read Troy's global CLAUDE.md, which asks for a requirements document and Troy's go-ahead before code? | A: each description says the role is started only by the troy-mode entry skill, and each role first checks for `.troy-mode/` (common rule 2). CLAUDE.md stays loaded, and common rule 4 says troy-mode's approved documents are that go-ahead. B: also set `omitClaudeMd` and drop CLAUDE.md. | A. An agent cannot be limited to "only when Troy types it" the way a skill can, so the description and the marker check do that job. CLAUDE.md also holds Troy's commit and privacy rules, which the roles should keep. |
| D35 | Do the role files get Chinese mirrors? Requirements 5.8 step 3 says the role instructions are updated "in English and Chinese". | A: English only. Requirements 5.8 step 3 changes to say that the rules table is in English and Chinese and the role instructions are in English. B: mirrors in a `troy-mode/roles/zh-CN/` folder. | A. Claude reads these files, not Troy. A `.zh-CN.md` file in `agents/` would load as a seventh agent. This design's Chinese mirror already describes every role. This changes a requirement. |
| D36 | The Code Reviewer runs `/code-review` and `/security-review`. Claude Code's documentation does not say whether `/code-review`, which starts its own subagents, works inside a subagent. | A: the Code Reviewer runs both through the Skill tool. If the trial (section 10.3) shows they do not work there, the main session runs both on the diff and gives their findings to the Code Reviewer, which judges them and writes the verdict. B: drop the commands and use a written checklist. | A. Both outcomes keep the tools the requirement names, and you need not decide again after the trial. |
| D37 | Where does the Architect record its design review? The `feature-design` template has an Architect review section, section 4. | A: the Architect writes section 4 of the design and nothing else in it. B: the Architect only reports, and the Interface Designer copies the review into section 4. | A. The review record stays in the reviewer's own words. F05 and F07 check paths, not sections, so after each AR2 run F07 also checks that the design's diff touches only section 4. |
| D38 | How is F04 checked, and when does its status move? | A: structure tests and planted bugs, plus a trial of every role on the Python sample before the PR opens (section 10). Status after merge: "Runs on a sample project". B: structure tests only. Status "Written", and the roles first run under F07. | A. A prompt that never ran says little about whether it works. The trial also settles two facts F05 needs. It costs about a dozen subagent runs. |

Requirements 1.13 records the approved changes:

- The answer to Q5: a hook can tell which role makes a call (section 9.1).
- The F05 row: every role's write scope, and a block on git and GitHub writes from roles (D31).
- The F07 row: the scope check after each run (D31), and the `[roles]` table in `.troy-mode/config.toml` (D32).
- Section 4: each role's model is set in its agent file and can be overridden per project (D32).
- 5.8 step 3: role instructions are in English only (D35).

D39 to D279 belong to later designs, so the design of tstack issue #75 takes D280 to D283. Each takes the recommended answer, approved under Troy's standing yes of 2026-11-22.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D280 | tstack issue #75 (the pilot report's candidate T3, which Troy accepted on 2026-11-16): the Code Reviewer runs `/security-review` on a PR only when its diff adds a dependency, a subprocess call, network access, or the handling of credentials. Who decides that a diff adds one? | A: `brief`'s check on the PR's diff decides, from lists per language pack in `troyflow/risks.py`, and the Task names each sign it found; the Code Reviewer also runs it when it sees one of the four that the brief does not name, and says so in Checks (section 6.8, F07 design 6.5). B: the check alone; the Code Reviewer never adds one. C: the Code Reviewer alone, from the four kinds in its agent file. | A, approved under Troy's standing yes of 2026-11-22. A check is exact, needs no model call, and tests can check it, and requirements 5.8 prefers a check to an instruction. Its lists match text, so B would leave a risk written in a form the lists lack until the release's review. C leaves the choice to the role that ran the review on nearly every PR of the pilot, and no exam case would show its choices drifting. |
| D281 | Does reading files outside the project's data folder count as a sign? | A: no. File access is not a sign, inside the data folder or outside it, and the release's review reads it (section 6.8). B: yes, when the Code Reviewer sees a path that comes from outside the program, such as an argument, a setting, or an environment variable. C: yes, every new file-system call in a source file. | A, approved under Troy's standing yes of 2026-11-22. The pilot's program reads recipe files and settings from paths that the user gives in most of its features, so B and C would bring back most of the 71 runs. A path that arrives over the network already brings the network sign, and `/code-review` still finds a wrong path as a bug. |
| D282 | Does `/code-review`'s level per stage change at the same time? The pilot's runs used `high` and `medium`. | A: no. The agent file names no level, as now, and a later issue can propose one, with its own exam (section 6.8). B: `medium` at every stage. C: `high` at PR 5 and on bug fixes, `medium` at PR 3 and PR 4. | A, approved under Troy's standing yes of 2026-11-22. B or C would be a second instruction change in the same PR, and F16 design 8.1 keeps one change per PR, so that the exam can tell which change moved a case. |
| D283 | How does the review once per release run? A release PR holds only the changelog, and `/security-review` reviews the current branch's changes since its merge base with `origin/HEAD`. | A: a new task, CR2, before the release test of every release, a patch's included. The main session makes a local review branch whose one commit puts `origin/main`'s files on the previous release's commit, CR2 runs `/security-review` there, and its report goes on the release PR. A blocking finding goes to the bug flow, and the review runs again after the fixes (F08 design 5.9). B: CR1 on the release PR, with the release's diff named in Input. `/security-review` would then see the changelog only, so the Code Reviewer reads the release's diff itself. C: CR2 without the Skill tool: the brief lists the kinds of flaw to look for, and the Code Reviewer reads `git diff <previous tag>...origin/main` itself. | A, approved under Troy's standing yes of 2026-11-22. It runs Claude Code's own `/security-review`, which the requirements' role row names, on exactly the release's changes, and the branch never leaves Troy's PC. B and C put the role's own reading in place of the command, which nothing has measured. If the build's probe finds that `/security-review` does not review that commit, the build stops and the coordinator brings C to Troy. |

D280 to D283 change no requirement (section 6.8).

## 13. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-06 | First draft. |
| 1.0 | 2026-11-06 | Approved by Troy with D27 to D38, every recommended answer. |
| 1.1 | 2026-11-08 | From F08 design section 9: TE5 writes the version tests (section 6.6); TM7 says who runs each scenario, and TM2 also reviews `[vX.Y tests]` PRs (section 6.4); PM4 drafts the changelog when the release starts and sets the statuses after Troy accepts (section 6.1). |
| 1.2 | 2026-11-08 | From F09 design sections 7 and 8: AR6 picks a rule's enforcement (section 6.2), DV5 and TE6 clean up the code and tests that a rule's baseline names (sections 6.5 and 6.6), the reviewers also check the Review-type P rules that name them, and the Developer and the Test Engineer fix a baselined file they change. The structure tests count the new tasks. |
| 1.3 | 2026-11-22 | From F07 design 6.4, D205 to D207 (tstack #63): DV1 adds the mock notes that the brief gives and a written constructor only signals too, DV2 deletes the notes, and CR1's brief checks them at PR 3 and PR 5 while its agent file stays as it is (sections 6.5 and 6.7). |
| 1.4 | 2026-11-22 | F20's design (D268 to D279, approved by Troy on 2026-11-22) adds the Architect's task AR7, Batch plan, with a plan run and a check run, and takes the shared documents out of the write scopes within a team (sections 3 and 6.2). The changes land with F20's build. |
| 1.5 | 2026-11-23 | D280 to D283, from tstack issue #75, which Troy accepted on 2026-11-16, approved under Troy's standing yes of 2026-11-22: CR1 runs `/security-review` only when `brief`'s check finds that the PR adds a dependency, a subprocess call, network access, or credential handling, or the Code Reviewer sees one that the check missed; file access is no sign; `/code-review`'s level stays as it is; and the new task CR2 reviews each release's changes on a local review branch before the release test. No requirement changes (sections 6.7, 6.8, 8, and 12). |
| 1.6 | 2026-11-23 | From F20 design 3.4 and D271: the Architect's AR7, Batch plan, joins section 6.2's table (F20 part 2's build). |
| 1.7 | 2026-11-24 | tstack #75's build: the probe of D283 showed that `/security-review` on a review branch reviews every change since the previous release (section 6.8). |
| 1.8 | 2026-11-25 | F18's design (D171 to D180, approved by Troy on 2026-11-25): the Product Manager's instructions gain the section "Waits for Troy" with the waits W1 to W11, and PM7, a ruling at round 3 on the Architect's own review, and PM3 and PM6 answer from the approved documents; the Architect gains AR8, a ruling at round 3, and a `Risky:` line in AR2's report (F18 design sections 4, 5, and 7.2). The changes land with F18's build. |
