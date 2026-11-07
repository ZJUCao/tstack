# troy-mode requirements

| | |
| --- | --- |
| Version | 1.15 |
| Date | 2026-11-06 |
| Status | Approved by Troy on 2026-11-05. Later versions add what Troy approved the same day: F01 design D1 and D2 (1.1), the answers to Q1 and Q9 (1.2), and F02 design D10, D11, and D14 plus the Python environment rule (1.3). Version 1.4 updates F02's status, and 1.5 adds the EN/ZH pair check to troy-pstack's CI. Version 1.6 records the F03 design decisions Troy approved: D15, D16, D17, and D20. Version 1.7 adds Troy's rule R21, and 1.8 to 1.12 update F03's status. Version 1.13 records the F04 design decisions Troy approved: D31, D32, and D35, and the answer to Q5, and 1.14 updates F04's status. Version 1.15 records the F05 design decisions Troy approved: D40, D41, D44, and D45. No question is open. |
| Source of truth | This English file. [`requirements.zh-CN.md`](requirements.zh-CN.md) is the Chinese mirror. |

## 1. Goal

troy-mode is Troy's own workflow for Claude Code. It takes a software project from requirements to a released version through a fixed pipeline of roles. Each role works in its own context. A different role reviews its output. Automated checks enforce the rules, so the rules do not depend on Claude remembering them.

It fixes four problems that appear when Claude builds a project in one long conversation:

- Requirements stay implicit and drift.
- Tests are written after the code and shaped to match it.
- Changes are large and hard to review.
- Written rules are forgotten partway through.

troy-mode ships as new files inside the troy-pstack plugin. It changes no upstream pstack file and does not change how poteto-mode behaves.

## 2. User

- One user, Troy, a solo developer.
- Uses Claude Code in the desktop app (Code tab) and in the CLI, on Windows 11.
- Keeps projects on GitHub, mostly in private repositories.
- Reads and writes English and Chinese.

## 3. How Troy uses it

### 3.1 Commands

| Command | When |
| --- | --- |
| `/troy-pstack:troy-mode <request>` | Any work in a troy-mode project: start a project, build the next feature, fix a bug, change a requirement, release a version, or investigate something. |
| `/troy-pstack:troy-init` | Once per project, to add troy-mode's files and checks to it. |

The names are proposals (open question Q4).

### 3.2 troy-mode or poteto-mode

Choose by project, not by task.

| Situation | Use |
| --- | --- |
| A troy-mode project, any change that lands on `main` | troy-mode |
| A troy-mode project, investigating or trying an idea | troy-mode. It takes a light path with no PR pipeline and borrows pstack skills such as `how` and `why`. |
| A project that does not use troy-mode, or a one-off script | poteto-mode when the task needs rigor |
| A quick question or a small edit | No mode |

In a troy-mode project, CI enforces the PR rules whichever mode made the change.

### 3.3 Where Troy takes part

Only these steps wait for Troy's approval:

1. Each project's requirements document.
2. Each project's overall architecture.
3. The interface design PR and the test plan PR of the first features (Q2). Troy approves them by merging them.
4. Each version, by testing it on Troy's own devices.
5. Every escalation (section 5.7).

Troy follows progress in the progress file and in the feature status table of the requirements document.

### 3.4 Interaction prototypes

These are text mocks. Real wording will differ.

**Prototype A. Starting a project.**

```text
Troy: /troy-pstack:troy-mode I want a small habit tracker for my phone and laptop.
PM:   Your goal as I understand it: log daily habits on two devices and see streaks.
      Before I write the requirements I need these answers.
      1. Must the two devices sync, or is each one separate?
      2. Does it work offline?
      3. ...
Troy: (answers)
PM:   Requirements draft written. docs/requirements.md (English) and
      docs/requirements.zh-CN.md (Chinese mirror).
      14 features. The dependency graph has no cycle. Order: F01, F02, F04, F03, ...
      Prototypes: docs/prototypes/F06-today-screen.html.
      Version plan: v0.1 = F01 to F06, v0.2 = F07 to F14.
      Waiting for your approval.
Troy: Approved.
Architect: Architecture draft written in docs/architecture.md. Waiting for your approval.
```

**Prototype B. The next feature.**

```text
Troy: /troy-pstack:troy-mode next feature
troy-mode: Next in order is F04 "Export history as CSV". It depends on F02 and F03, both accepted.
  [1/6] Interface design PR #41 is open. The Architect approved it in round 2.
        You merge this one (feature 2 of your first 3). Waiting for you.
Troy: Merged.
troy-mode: [2/6] Test plan PR #42 is open. Waiting for you.
Troy: Merged.
troy-mode: [3/6] Mock PR #43 merged. CI green, code review passed.
  [4/6] Test PR #44 merged. 9 new tests. All 9 fail against the mock, as expected.
  [5/6] Implementation PR #45 merged. 9 of 9 new tests pass. 212 existing tests pass.
        Changed-code coverage 94% line, 86% branch. 310 changed lines in 4 files.
  [6/6] Acceptance PR #46 merged. F04 status is now "passes tests on main".
        It has not been checked on your devices yet.
```

**Prototype C. An escalation.**

```text
troy-mode: Stopped on F07. This needs you.
  Why: the Architect rejected the interface design 3 times.
  The disagreement: the Interface Designer wants one sync() call. The Architect wants
  separate push() and pull() calls, so the storage module holds no network code.
  Option A: one sync() call. Simpler for callers. Storage depends on network.
  Option B: push() and pull(). Keeps the module boundary. Callers make two calls.
  Recommendation: B, because the architecture says storage must not depend on network.
```

**Prototype D. The progress file.**

```markdown
# Progress

- Current version: v0.2 (F07 to F14)
- Current feature: F08 Import from CSV
- Stage: 4 of 6. Test PR #48 is in review (Code Reviewer, round 1).
- Waiting on Troy: nothing
- Open issues: F05 has one coverage exclusion (disk-full branch), approved by the Test Manager.
- Last updated: 2026-11-12 14:05
```

## 4. Roles

| Role | Runs as | Owns | Reviews | Must not |
| --- | --- | --- | --- | --- |
| Product Manager | Main session, because only it can talk with Troy | Requirements document, feature list, dependency graph, feature order, prototypes, version plan, status table, acceptance, change requests | Each finished feature, against the requirements | Write code or tests |
| Architect | Subagent | Overall architecture, coding rules, module dependency rules, architecture decision records (ADRs), approval of new third-party dependencies | Each interface design, against a checklist | Design a feature's interfaces itself |
| Interface Designer | Subagent | Each feature's external interface design | Nothing. It answers the Test Manager's questions. | Edit the architecture. It asks the Architect instead. |
| Test Manager | Subagent | Each feature's test plan, each version's test plan, triage of coverage gaps, bugs, and disputed tests | Each test PR, against the test plan | Write test code |
| Developer | Subagent | Mock PRs, implementation PRs, bug fix PRs | Nothing | Edit tests. Add a third-party dependency without the Architect. |
| Test Engineer | Subagent | Test code, bug reproduction tests, test fixes the Test Manager orders | Nothing | Edit source code |
| Code Reviewer | Subagent | Nothing | Mock, test, and implementation PRs, for quality and security, using Claude Code's `/code-review` and `/security-review` | Edit the code it reviews |

The main session also does the project manager's work. It picks the next feature, starts each role, passes reviews between roles, keeps the progress file, and escalates to Troy.

Each role's model is set in its agent file and can be overridden per project in `.troy-mode/config.toml` (Q3, [F04 design](design/F04-role-definitions.md) D32).

### 4.1 pstack skills troy-mode reuses

troy-mode calls these troy-pstack skills where they fit, without changing them.

| Skill | Used for |
| --- | --- |
| `how`, `why` | Understanding existing code during investigations and before design |
| `interrogate` | Adversarial review of a contested design |
| `benchmark-checklist` | Checking performance numbers before trusting them |
| `technical-writing` | Writing requirements, design, and test plan documents |
| `correct`, `reflect` | Turning repeated mistakes into rules and checks after a version |

Where a pstack rule conflicts with a troy-mode rule, troy-mode's rule wins inside a troy-mode project. The comment rule is one example. pstack keeps comments only for a non-obvious reason. troy-mode requires a Google-style doc comment on every function.

## 5. Process

### 5.1 Project setup (once per project)

1. **Requirements.** The Product Manager talks with Troy until the requirements are clear. It writes the requirements document in English with a Chinese mirror. The document holds the goal, users, interaction, non-functional requirements (performance targets included), out of scope, open questions, and these parts:
   - Features, broken down finely, each with an ID.
   - A dependency graph. Each dependency is hard (B cannot be built without A) or soft (B can be built against A's mock).
   - A topological order. A cycle means the breakdown is wrong. The Product Manager breaks it down again, usually by moving the shared part into its own feature.
   - Prototypes.
   - A version plan.

   A feature whose implementation would pass the PR size limit (R03) is split. Troy approves the document.
2. **Init.** `troy-init` adds the marker folder, document templates, the rules table, and the progress file.
3. **Architecture.** The Architect writes the overall architecture: tech stack, modules and the allowed dependency directions between them (no cycles), data model, error handling, logging, naming, and coding rules. Troy approves it.
4. **Checks.** `troy-init` adds the language-specific checks and the CI workflow for the chosen stack.

### 5.2 Feature loop

Features are built one at a time, in topological order. Each feature takes six PRs, merged in order. Each PR has exactly one commit and holds one stage's output only.

```mermaid
flowchart LR
  P1["PR 1<br/>Interface design"] --> P2["PR 2<br/>Test plan"]
  P2 --> P3["PR 3<br/>Mock"]
  P3 --> P4["PR 4<br/>Tests, all fail"]
  P4 --> P5["PR 5<br/>Implementation, all pass"]
  P5 --> P6["PR 6<br/>Acceptance"]
```

| PR | Content | Author | Reviewer | Merge condition | Merged by |
| --- | --- | --- | --- | --- | --- |
| 1 | Interface design (English and Chinese). For each external interface: name, purpose, parameters, return value, errors, and a performance target when the requirements set one. | Interface Designer | Architect, against the checklist below, at most 3 rounds | Document checks pass | Troy for the first features (Q2), then Claude |
| 2 | Test plan (English and Chinese). Unit, functional, integration, and performance cases. Each case says what it tests. | Test Manager | Agreed with the Interface Designer, at most 3 rounds | Document checks pass | Troy for the first features (Q2), then Claude |
| 3 | Mock. Signatures and full Google-style doc comments, no bodies. | Developer | Code Reviewer | Checks pass. Existing tests pass. | Claude |
| 4 | Test code, each test tagged with the feature ID. | Test Engineer | Test Manager (matches the plan) and Code Reviewer | Every new test fails against the mock. Existing tests pass. | Claude |
| 5 | Implementation. | Developer | Code Reviewer | New and existing tests pass. Performance tests pass where a target exists. Coverage meets R11. Size rules hold. | Claude |
| 6 | Acceptance. Status update in English and Chinese. The feature's tests become must-pass. | Product Manager | None | Checks pass | Claude |

**Architect's interface checklist.**

- Fits the module layout and the data model.
- Follows the error handling and naming conventions.
- Does not duplicate an existing interface.
- Depends only on features earlier in the order.
- Adds no hidden coupling between modules.
- Changes an implemented interface only through the change flow (5.4).

**Disputed tests.** The Developer raises it. The Test Manager rules. If the test is wrong, the Test Engineer fixes it in its own test PR and states the reason. A test change never shares a commit with source code.

**Coverage gaps.** When R11 fails, the Test Manager decides what the uncovered code is. Tests are added only from the design, never by aiming at uncovered lines.

| Uncovered code | Cause | Fixed by |
| --- | --- | --- |
| Code nothing needs (an unused branch, a feature written early) | Developer wrote too much | Developer deletes it |
| Behavior in the design that the test plan missed | Incomplete test plan | Test Manager adds cases. Test Engineer adds them in a test PR. |
| Behavior not in the design | Either the design missed it or the Developer overreached | Interface Designer decides. A missed design gets a design update, then tests. Overreach is deleted. |
| Code that cannot be tested in practice (for example a full disk) | Hard to set up | Excluded with a written reason, approved by the Test Manager |

### 5.3 Bug fix

1. The Test Manager triages the report. A misunderstood requirement goes to the Product Manager as a change (5.4).
2. PR A. The Test Engineer adds a test that reproduces the bug, tagged with the bug ID. It fails.
3. PR B. The Developer fixes the bug. The test passes and stays as a regression test.

The Code Reviewer reviews both PRs.

### 5.4 Requirement change

1. Troy asks for the change. The Product Manager updates the requirements document, and Troy approves it.
2. The Product Manager lists the affected features from the dependency graph: the changed feature and every feature that depends on it.
3. The Architect decides which interfaces, tests, and parts of the architecture change. An architecture change gets an ADR.
4. The changes go through the feature loop PRs as usual. All existing tests run as regression.

### 5.5 Version release

1. The version plan groups consecutive features in the order into versions. Each version is usable on its own.
2. The Test Manager writes the version test plan when the version is planned, not at the end.
3. The release test runs end-to-end tests of the user scenarios in the requirements, stress tests, and performance tests, on Troy's devices. Troy accepts the version.
4. Bugs found go through the bug flow (5.3).
5. After acceptance, `main` gets a tag `vMAJOR.MINOR.PATCH` and the changelog is updated in English and Chinese.
6. A retrospective turns problems that repeated during the version into new rules or checks (5.8).

### 5.6 When tests run

| When | What runs | Who |
| --- | --- | --- |
| Each stage | The current feature's tests | Automatic |
| Each PR | All unit, functional, and integration tests, as regression. Target: a few minutes. | CI |
| Each version | End-to-end, performance, and stress tests, on Troy's devices | Test Manager designs, Test Engineer implements, Product Manager and Troy accept |

**Performance.** Targets come from the requirements. The Interface Designer copies them into the interface design. The Test Manager plans performance cases in the test plan. They run after implementation, because a mock always returns at once. Only interfaces with a target get performance tests. Stress tests need the whole system, so they run only at version level.

### 5.7 Escalation

troy-mode stops and asks Troy when:

- A review loop reaches 3 rounds without agreement.
- A change needs the requirements or the architecture to change.
- An implementation still fails its tests after 3 attempts.
- A new third-party dependency is needed. The Architect reviews it first.
- An irreversible action falls outside the merge rights, for example a force push or deleting data.

Each escalation says what stopped, why, the options, and a recommendation (Prototype C).

### 5.8 Adding or changing a rule

1. Troy states the rule and whether it applies to every troy-mode project or to one.
2. troy-mode picks the strongest enforcement that works. In order: an architecture that makes the mistake impossible, a lint or CI check, a test, and last, written role instructions.
3. One PR updates the rules table in English and Chinese, the check config, and the role instructions. Role instructions are prompts for Claude and are in English only (F04 design D35).
4. If existing code breaks the new rule, Troy chooses: fix it all now in separate cleanup PRs, or apply the rule only to new and changed code.

A rule for every project lives in troy-pstack and ships in a new plugin version. A rule for one project lives in that project's rules table.

### 5.9 Work outside the pipeline

Investigations, questions, and experiments in a troy-mode project open no PR to `main`. Experiment code stays on a throwaway branch or folder. Code worth keeping goes through the feature loop.

### 5.10 Continuing across sessions

The progress file (Prototype D) records the current version, feature, stage, open PRs, what waits on Troy, and open issues. A new session reads it first and continues without the old conversation.

## 6. Rules

**Hard** blocks the merge. **Soft** allows the PR when its description gives a reason. **Review** is checked by a role. **Process** is followed by troy-mode itself. Troy's GitHub plan is free, and it has no branch protection for private repositories. So troy-mode's merge step enforces Hard rules: it never merges a PR whose checks fail (F02 design D14).

| ID | Rule | Type | Enforced by |
| --- | --- | --- | --- |
| R01 | Each PR has exactly one commit, and its subject line equals the PR title (F03 design D17). Review fixes amend that commit, or the PR is squash-merged. | Hard | CI |
| R02 | Each PR holds one stage's output only: documents, source, or tests. | Hard | CI |
| R03 | A source PR changes at most 500 lines (added plus deleted, not counting lock files or generated files) in at most 5 files. Test PRs have no limit. A PR that only splits a file may pass the limit and says so. | Soft | CI |
| R04 | A function body has at most 50 lines, not counting comments, doc comments, or blank lines. A complex external interface calls single-purpose internal functions. | Hard | Lint |
| R05 | Doc comments follow Google style. Code comments are in English only. | Hard | Lint |
| R06 | A source file has at most 500 lines in total, comments included. Larger files are split. | Soft | Lint |
| R07 | Modules depend on each other only in the directions the architecture allows, only through external interfaces, and never in a cycle. | Hard | Dependency checker |
| R08 | The Developer never edits test files. | Hard | Hook and CI |
| R09 | Every new test in a test PR fails against the mock. | Hard | CI |
| R10 | Every test is tagged with its case ID or bug ID: the test's own name starts with it, for example `test_f04_t07_writes_header` (F03 design D16). Tests of features not yet accepted and of bugs not yet fixed count as expected failures. Every other test must pass. | Hard | Test runner config and CI |
| R11 | In an implementation PR, the changed code has at least 90% line coverage and 80% branch coverage. 95% is a target, not a gate. An excluded line needs a written reason and the Test Manager's approval. | Hard | CI |
| R12 | English documents are the source of truth. A PR that changes an English document also updates its Chinese mirror. The mirror's header names the English version it matches. | Hard | CI |
| R13 | A status label says how far a feature really goes, for example "passes tests on main" versus "usable on Troy's devices". | Review | Product Manager |
| R14 | Only interfaces with a performance target get performance tests. They run on a fixed machine, with a margin, against the previous baseline. | Review | Test Manager |
| R15 | Every fixed bug keeps its reproduction test. | Review | Test Manager |
| R16 | A new third-party dependency needs the Architect's approval. | Review | Architect. CI flags every change to dependency files. |
| R17 | A review loop stops at 3 rounds and escalates. | Process | troy-mode |
| R18 | Troy merges PR 1 and PR 2 of the first features (Q2). Claude merges every other PR once its checks and reviews pass. Troy decides when Claude merges everything. | Process | troy-mode |
| R19 | Commits use the email in Troy's global CLAUDE.md. Commit messages, PR titles, and PR descriptions carry no Claude attribution and, by default, do not mention Claude or Anthropic at all (F02 design D10). | Hard | Hook and CI |
| R20 | A merged document or PR description holds no template markers or template guidance (F01 design D2, F02 design D11). | Hard | CI |
| R21 | Every change reaches `main` through a PR from its own branch. Never commit on `main`, push `main`, or open a PR from `main`. | Hard | Hook and CI |

## 7. Features

### 7.1 Status labels

| Label | Meaning |
| --- | --- |
| Not started | Nothing exists yet. |
| Written | The files exist but have never run. |
| Runs on a sample project | It ran on a throwaway sample project. |
| Used on a real project | Troy used it on one of their own projects. |

### 7.2 Feature list

The IDs are already in topological order.

| ID | Feature | Depends on | Status |
| --- | --- | --- | --- |
| F01 | Templates and rules table. Templates for the requirements, architecture, interface design, test plan, ADR, progress file, changelog, and escalation message. The English and Chinese pair format with its sync header. The rules table, seeded from section 6. PR title and description templates ([F01 design](design/F01-templates.md) D1). | None | Written |
| F02 | Language-independent checks for R01, R02, R03, R12, R16, R19, and R20, a GitHub Actions workflow that runs them, and a `commit` subcommand that F05's hooks call for R19. The checks read each PR's stage from its title (F01 design D1). R20 rejects documents and PR descriptions that still hold template markers (F01 design D2). R21's check, which fails when the PR's branch is `main`, came after F02 merged and is not built yet. | F01 | Written |
| F03 | Language packs. A language-independent engine in troy-check for R04, R05, R06, R07, R09, R10, and R11, which reads JUnit and Cobertura XML, plus one thin pack per language with its environment, tool config, commands, and CI job ([F03 design](design/F03-language-packs.md) D15). Built in four PRs. Python and C/C++ come first. TypeScript/JavaScript is wanted too, at lower priority (Q1). The Python pack follows the Python environment rule in section 8. | F01 | Runs on a sample project: the Python and C/C++ packs each take their sample project through the pack's CI job, which ends in `troy-check code`. Both pass in troy-pstack's CI on Linux and on Troy's PC. Not yet used on a real project. TypeScript/JavaScript is not started |
| F04 | Role definitions. Six subagents and the Product Manager's instructions for the main session, each with its instructions, tool limits, model, and write scope ([F04 design](design/F04-role-definitions.md)). | F01 | Runs on a sample project: each role ran once on the Python sample, started by hand. troy-mode (F07) does not start them yet. |
| F05 | Hooks. A marker-folder gate so they do nothing outside troy-mode projects. Claude Code hooks in the plugin keep each role inside its write scope, Developer edits to tests (R08) among them. They check Write and Edit before the call, and compare the working tree with the role's starting state after each shell call and when the role stops (F05 design D41). Every other subagent is read-only (D40). Roles may run only read-only git and GitHub commands (F04 design D31) and the skills they need, and may read the plugin's own files without a permission rule (D45). Git hooks in troy-check's folder, turned on by `core.hooksPath`, refuse commits that break R19, commits on `main`, and pushes of `main` (R21), whoever runs git, and Claude cannot skip them (D44). A local log records each block for F07. | F02, F04 | Not started |
| F06 | Project init (`troy-init`). Marker folder, document skeleton, rules table, and progress file. After the architecture is approved, the language pack and the CI workflow. | F01, F02, F03 | Not started |
| F07 | Entry skill (`troy-mode`). Routes each request to a flow (5.1 to 5.10), runs the feature loop, passes reviews between roles, escalates, applies the merge rights, and keeps the progress file. Starts each role with the model and effort in the `[roles]` table of `.troy-mode/config.toml` (F04 design D32), and checks after each run that the role changed only files in its write scope (D31). | F04, F05, F06 | Not started |
| F08 | Version release flow (5.5). | F07 | Not started |
| F09 | Rule change flow (5.8). | F07 | Not started |
| F10 | troy-pstack documentation. A README section, a usage guide in English and Chinese, and a note that troy-mode is Troy's own work. | F07 | Not started |
| F11 | Pilot. Take one small real project through one version with troy-mode. | F08, F09 | Not started |

```mermaid
flowchart LR
  F01 --> F02
  F01 --> F03
  F01 --> F04
  F02 --> F05
  F04 --> F05
  F01 --> F06
  F02 --> F06
  F03 --> F06
  F04 --> F07
  F05 --> F07
  F06 --> F07
  F07 --> F08
  F07 --> F09
  F07 --> F10
  F08 --> F11
  F09 --> F11
```

F02, F03, and F04 depend only on F01, so they can be built in parallel.

## 8. Non-functional requirements

- **No side effects on troy-pstack.** troy-mode edits no upstream file. The only shared files it touches are `README.md`, `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`. Every new skill, agent, and script name starts with `troy-`. Every new skill runs only when Troy types it (`disable-model-invocation: true`). Hooks exit at once outside troy-mode projects.
- **Upstream merges stay easy.** The upstream merge steps in the README keep working unchanged.
- **Platform.** Windows 11 first, through Git Bash and PowerShell. CI runs on GitHub-hosted Linux runners. Scripts also run on macOS and Linux. Files use LF line endings.
- **Speed.** A hook adds no delay Troy notices, with a target under 200 ms per call. The per-PR regression run takes a few minutes.
- **Cost.** Each role's model can be set. Checks also run locally before a push, so CI rarely fails and private-repository Actions minutes last.
- **Privacy.** troy-mode uses no service beyond GitHub and Anthropic. No secret goes into a document, a log, or the progress file.
- **Resumable.** Any new session continues from the progress file.
- **Language.** Documents are written in English with a Chinese mirror. Code and code comments are in English. In troy-pstack, CI checks every PR that changes a document: each English document and its mirror must have the same headings, tables, code blocks, markers, and version (`troy-mode/dev/check_pairs.py`).
- **Python environments.** In a Python project, mamba creates and manages the environment, and uv installs packages into it. Projects that will run together on one platform form a series and share one environment, named after the series. A project in no series has its own. Each series has one lock file, `requirements-dev.lock`, compiled from all members' `pyproject.toml` and committed in each member (F03 design D20). troy-mode never creates a `.venv` folder. F03's Python pack sets this up on Troy's PC and in CI. troy-mode's own checks (F02) use only the standard library and need no environment.
- **Auditable.** Every role's output is a PR or a review comment, so the history shows who changed what.

## 9. Out of scope (version 1)

- Teams: more than one human, or roles assigned to people.
- Hosts other than GitHub.
- Changing upstream pstack skills or poteto-mode.
- Deployment to production, app stores, or servers. troy-mode ends at a tagged, accepted version.
- A graphical dashboard. State lives in Markdown files.
- Languages other than Python, C/C++, and TypeScript/JavaScript (Q1).
- Rewriting the git history of existing projects.

## 10. Open questions

Troy approved this document on 2026-11-05. That approval accepts the proposals for Q2 to Q10. Troy answered Q1 and extended Q9 the same day (version 1.2).

| ID | Question | Proposal |
| --- | --- | --- |
| Q1 | Which languages come first? Each needs its own language pack (F03). | Decided by Troy: Python and C/C++ first. TypeScript/JavaScript is wanted too, at lower priority. |
| Q2 | For how many first features does Troy merge PR 1 and PR 2? | 3 per project. Then Troy decides. |
| Q3 | Which model does each role use? | opus for the Architect, Interface Designer, Test Manager, and Code Reviewer. sonnet for the Developer and Test Engineer. The Product Manager uses the main session's model. |
| Q4 | Names. | `troy-mode`, `troy-init`. Agents `troy-architect`, `troy-interface-designer`, `troy-test-manager`, `troy-developer`, `troy-test-engineer`, `troy-code-reviewer`. Marker folder `.troy-mode/` in the project root. |
| Q5 | R08 needs a hook to know that the Developer is the one editing. Whether Claude Code tells a hook which subagent made a call has to be checked during design. | Answered by the F04 design (section 9.1): it can. The hook input names the subagent in `agent_type`, so a hook enforces R08, and CI's R02 stays as the backstop. |
| Q6 | When an existing project (for example troy-voice) adopts troy-mode, must old code meet the rules? | No. Only new and changed code. Old code is fixed when it is touched. |
| Q7 | Which machine runs performance tests? | Troy's PC, locally, at version release. Not CI, whose runners are too noisy. |
| Q8 | Is the progress file committed? Committing it means a PR for every update, which R01 and R02 make heavy. | Keep it local and git-ignored. The durable state is the status table, which PR 6 updates. |
| Q9 | What format do project prototypes use? | Clickable HTML wireframes in `docs/prototypes/`, plus Mermaid diagrams in the documents. A command-line project may also write a prototype as a Markdown file in `docs/prototypes/` that holds a terminal session transcript (added by Troy in 1.2). |
| Q10 | How is troy-mode itself built? The pipeline does not exist until F07. | One PR per feature (F01 to F10) on troy-pstack, each with one commit. Check scripts are built test-first. The pilot (F11) is the first full run of the pipeline. F03 is the exception: it is built in four PRs (F03 design D15). |

## 11. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-05 | First draft, from Troy's discussion with Claude on 2026-11-05. |
| 1.0 | 2026-11-05 | Approved by Troy. Proposals for Q2 to Q10 accepted. Q1 still open. |
| 1.1 | 2026-11-05 | F01 adds PR title and description templates (D1). F02 reads PR stages from titles and rejects leftover template markers (D2). Both approved by Troy with the F01 design. Wording only: names Troy in place of pronouns. |
| 1.2 | 2026-11-05 | Troy answered Q1: Python and C/C++ first, TypeScript/JavaScript at lower priority. Troy extended Q9: a command-line project may use a Markdown terminal transcript as a prototype. The requirements template follows. |
| 1.3 | 2026-11-05 | Troy approved the F02 design. R19 also forbids mentioning Claude or Anthropic by default (D10). New rule R20 for template markers (D11). Section 6 says troy-mode's merge step enforces Hard rules, because Troy's GitHub plan has no branch protection for private repositories (D14). Troy added the Python environment rule: mamba and uv, no `.venv` (section 8). F01 status: Written. |
| 1.4 | 2026-11-05 | F02 status: Written. Its unit tests pass on Troy's PC. It has not yet run on a project's PRs. |
| 1.5 | 2026-11-05 | Troy asked for the EN/ZH pair check in troy-pstack's CI. Section 8, Language, says what it checks. |
| 1.6 | 2026-11-05 | Troy approved the F03 design. F03 takes R09 and is built in four PRs (D15). R10: a test's name starts with its ID (D16). R01: the commit subject equals the PR title (D17). Section 8: one environment and one lock file per series of projects (D20). |
| 1.7 | 2026-11-05 | Troy added R21: every change reaches `main` through a PR from its own branch. F05's hooks and a troy-check branch check will enforce it; neither is built yet. |
| 1.8 | 2026-11-05 | F03 status: Written, part 1 of 4. Its unit tests pass on Troy's PC. |
| 1.9 | 2026-11-05 | F03 status: Written, parts 1 and 2 of 4. Part 2's unit tests pass on Troy's PC. |
| 1.10 | 2026-11-06 | F03 status: Written, parts 1 to 3 of 4. The Python pack takes its sample project through lint, types, tests, coverage, and `troy-check code` on Troy's PC. |
| 1.11 | 2026-11-06 | F03 status: Written, all 4 parts. The C/C++ pack takes its sample project through build, format, lint, tests, coverage, Doxygen, and `troy-check code` on Troy's PC. |
| 1.12 | 2026-11-06 | F03 status: Runs on a sample project. After part 4 merged, both sample projects pass their pack's CI job in troy-pstack's CI on Linux, as they do on Troy's PC. |
| 1.13 | 2026-11-06 | Troy approved the F04 design. F05 enforces every role's write scope and blocks git and GitHub writes by roles, and F07 checks the scope after each run (D31). Each role's model can be overridden per project (D32). Role instructions are in English only (D35). Q5 is answered: a hook can tell which subagent makes a call. |
| 1.14 | 2026-11-06 | F04 status: Runs on a sample project. In the trial of F04 design 10.3, each role ran once on a copy of the Python sample, started by hand from a brief. troy-mode (F07) does not start them yet. |
| 1.15 | 2026-11-06 | Troy approved the F05 design. The F05 row now describes the hooks as the design builds them: every subagent other than the roles is read-only (D40), changes made through the shell are found by comparing the working tree (D41), git hooks turned on by `core.hooksPath` enforce R19 and R21 for every commit and push (D44), and roles read the plugin's files through a hook rather than a permission rule (D45). |
