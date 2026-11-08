# F09 design: the rule change flow

| | |
| --- | --- |
| Feature | F09 in [requirements 1.25](../requirements.md#72-feature-list) |
| Version | 1.1 |
| Date | 2026-11-08 |
| Status | Approved by Troy on 2026-11-08, with D79 to D85. Version 1.1 records Troy's standing permission for trials (section 10.3). |
| Source of truth | This English file. [`F09-rule-change.zh-CN.md`](F09-rule-change.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F09 adds the rule change flow (requirements 5.8) to troy-mode's entry skill (F07). With it, on "add a rule ...", the main session:

1. asks Troy what 5.8 step 1 needs, when the request does not say it: the rule, and whether it is for this project or for every troy-mode project;
2. has the Architect pick the strongest enforcement that works and find the existing code that breaks the rule (5.8 step 2, D79);
3. shows Troy one proposal, whose answer approves the rule and makes 5.8 step 4's choice (D82);
4. for a rule of this project, lands it in one `[rules]` PR with the rules table, the check config, and a baseline of today's violations (5.8 step 3, D80, D81). An architecture change, if the rule needs one, comes first in its own `[docs]` PR. Cleanup PRs come after it when Troy chose to fix the existing code now;
5. for a rule for every project, writes a proposal for troy-pstack and, on Troy's yes, opens an issue there (D83).

F09 also lets a project change or retire its own rules, and adjust a troy-mode rule through a project rule where troy-check's config allows it (D84). F08's retrospective hands the rules Troy picks to this flow.

F04 says that `docs/rules.md` and `.troy-mode/**` belong to no role, and that only troy-init and this flow change them (F04 section 3). F07 D62 left every rule change except its own `[flow]` setting to F09. F09 adds no skill: it extends F07's skill and engine. It lands in one PR, as Q10 says for every feature.

## 2. Location

```text
skills/
  troy-mode/
    SKILL.md                  gains the section "Rule change" (sections 4 to 6)
troy-mode/
  flow/
    troy_flow.py              gains the commands of section 3
    troyflow/                 new modules (the Developer's choice)
    tests/                    unit tests (section 10.1)
```

Section 8 lists the changes to F01, F02, F03, F04, and F07.

## 3. The engine

### 3.1 Commands

```text
python troy_flow.py rule-id   [common options]
python troy_flow.py rule-row  --id <P-ID> --rule-file <path> [--retire] [--date <YYYY-MM-DD>] [common options]
python troy_flow.py snapshot  --role rules [common options]
```

| Command | What it does |
| --- | --- |
| `rule-id` | Reads `docs/rules.md` on `origin/main` and gives the next free P ID, every P row with whether it is retired, and each P rule's baseline lines in config and dependency files (section 5.3). |
| `rule-row` | Writes one P row into `docs/rules.md` and its mirror. A new ID adds the row after the last P row, an existing ID replaces it, and `--retire` marks it retired (section 6). The row's Since cell is the date for a new rule and stays for a changed one. Both files move to the next major version with the status "Approved by Troy on <date>", and get one change-log row (D82). `--rule-file` is a JSON file with the Rule, Type, and Enforced by cells and the change-log text, in English and Chinese. |
| `snapshot --role rules` | A new role for F07's snapshot: the main session's own work on a `[rules]` PR. Its scope is the `config` and `dependencies` path classes, which are what a `[rules]` PR may change (F02 D9). `check-run` then flags any other path. |

- `check-run` gains one rule: a change to a `dependencies` path that only deletes lines holding `baseline: P<nn>` is not a dependency problem. A cleanup run removes its files' baseline lines this way without `--allow-dependency` (section 5.4).
- `status` gains the next action `cleanup` (section 3.2). `brief` learns AR6, DV5, and TE6 (section 7).
- As in F07, the engine never commits, pushes, or writes to GitHub, and its exit codes are F07's.

### 3.2 State and next action

The rule state lives in git and on GitHub (F07 D58):

| What | Read from |
| --- | --- |
| The project's rules | The P rows of `docs/rules.md` on `origin/main` |
| A rule change in progress | An open PR titled `[rules] Add P01, ...`, `[rules] Change P01, ...`, or `[rules] Retire P01, ...`, which F07 continues like any open PR |
| Troy's choice for existing code | The rules table's change-log row for the rule's newest change, which says "Existing code: fixed by cleanup PRs." or "Existing code: fixed when touched." |
| Cleanup still to do | Lines holding `baseline: P01` in config and dependency files on `origin/main` |

`status` gives `next.action` `cleanup` when a rule's newest change-log row says "fixed by cleanup PRs" and its baseline lines remain. The next cleanup PR follows (section 5.4), and a new session finds it the same way. `cleanup` comes after the open PRs and before the feature loop's next stage.

## 4. The flow

### 4.1 Routing

| Request, for example | What F09 does |
| --- | --- |
| "add a rule: no print calls in source", "a rule for this project: ..." | A project rule (section 5) |
| "a rule for every project: ..." | A rule for every project (section 5.6) |
| "change P01 ...", "retire P02" | Section 6 |
| "in this project, R03's limit is 800 lines" | A project rule that adjusts R03 (section 6) |
| The rules Troy picks in F08's retrospective | One at a time, as above |

When the request does not say whether the rule is for this project or every project, F09 asks Troy that one question, recommending this project. A rule for every project changes troy-pstack, which is a bigger step.

### 4.2 Steps

| Step | What happens | Who | PR | Merged by |
| --- | --- | --- | --- | --- |
| 1. Ask | The rule and its scope, if the request does not give them | Main session | None | |
| 2. Enforcement | The strongest level that works, the exact config, and the existing violations | AR6 | None | |
| 3. Proposal | One message to Troy, and Troy's answer | Main session | None | |
| 4. Architecture | Only when the rule needs the architecture to change | AR6's second run | `[docs] Change the architecture for P01` | F07 |
| 5. Rule PR | The rules table, the config, and the baseline | Main session, under `snapshot --role rules` | `[rules] Add P01, <summary>` | F07 |
| 6. Cleanup | Only when Troy chose to fix existing code now | DV5 or TE6, reviewed by CR1, and by TM2 for tests | `[refactor] Apply P01 to <area>`, `[P01 test-fix] Apply P01 to tests` | F07 |

Each PR has one commit whose subject is its title (R01), and F07 merges it when its checks pass (F07 section 8.6). Troy's answer in step 3 is the approval, so no PR of the flow waits for Troy again (D82).

## 5. A project rule

### 5.1 Enforcement (D79, D80)

5.8 step 2 lists four levels, strongest first. In a project, each level lands here:

| Level | What it can be in a project | Where it lands |
| --- | --- | --- |
| Architecture | A module boundary or dependency direction, which R07's checker reads from the architecture. A rule that needs more words than a table cell, written in the architecture's section 8, "Naming and coding rules". | A `[docs]` PR by the Architect, before the rule PR. Troy approves it with the rule. |
| Lint or CI check | A rule of a tool the language pack already runs: ruff or mypy in Python, clang-tidy or clang-format in C/C++. A troy-check limit in `.troy-mode/config.toml`. A step that needs no environment, such as a `git grep` that must find nothing, in the project's own workflow `.github/workflows/project-rules.yml`. | The rule PR |
| Test | Not in F09 for project rules (D80) | None |
| Role instructions | The P row itself, of type Review, naming the role that checks it. Every role reads `docs/rules.md` (F04 common rule 3), and reviewers check the Review rules that name them (section 7). A rule that troy-mode itself must follow is of type Process, and F07 reads those rows at every start. | The rule PR |

The type follows the level: a lint or CI check is Hard, or Soft when it allows a reason as R03 does; role instructions are Review or Process.

**AR6** reads the rule, `docs/rules.md`, the architecture, and the pack's config: `pyproject.toml`, `.clang-tidy`, `.clang-format`, and `.troy-mode/config.toml`. It reports `escalate`, because Troy decides, with the proposal in its Question field:

- the strongest level that works, and why no stronger one does;
- the rule's text for the table, its type, and Enforced by;
- the exact change to each config file, or the architecture change;
- the existing code that breaks the rule: for a check, AR6 runs it on the whole repository and lists the files and the count; for a review rule, it reads the code;
- for "fix it now", the cleanup PRs it expects, each within R03.

AR6 changes no file. It runs the tool through Bash with the rule turned on in a command-line option, never by editing the config. When Troy approves an architecture change, a second AR6 run writes it, with an ADR, as AR3 does for a dependency (F07 section 8.7).

### 5.2 The proposal (D82)

One message to Troy, in Troy's language:

- the rule as the table will say it, in English and Chinese, with its ID from `rule-id`, its type, and Enforced by;
- the enforcement, and why no stronger level works;
- the files the rule PR changes, and the architecture PR, if any;
- the existing code that breaks it, and 5.8 step 4's choice with a recommendation: fix it now in cleanup PRs, or apply the rule only to new and changed code (section 5.4).

Troy's answer approves the rule and makes the choice, or asks for a change. A change runs AR6 again with Troy's words in Input, and F09 shows the new proposal. Nothing is written before Troy approves.

### 5.3 The rule PR

On `troy-mode/rule-p01` from `origin/main`, under `snapshot --role rules`:

1. **Rules table.** The main session writes the row's cells in both languages into a JSON file and runs `rule-row --id P01 --rule-file <file>`. The change-log row names the rule, Troy's approval, and Troy's choice for existing code.
2. **Config.** The main session makes AR6's config change.
3. **Baseline.** When existing code breaks a check, the PR also exempts today's violating files, in the tool's own config: one line per file, each with the comment `baseline: P01`. In Python, these are entries in ruff's `per-file-ignores` in `pyproject.toml`. CI then passes on the PR and on every later PR, while new files must follow the rule at once.
4. **Check.** `check-run`, then stage exactly its paths and commit as `[rules] Add P01, <summary>`.
5. **Local checks.** `troy-check pr`, and the pack's steps when a tool's config changed, so the new rule and its baseline pass before the push.
6. **PR and merge.** The description says Why (Troy's rule, in English), What (the row, the config, and the number of baseline lines), and Checks. F07 pushes, opens the PR, waits for CI, and merges it.

When a tool has no per-file exemption that a `[rules]` PR may change, such as clang-tidy, whose suppressions live in source files, the rule gets no baseline. AR6 says so in the proposal. The cleanup PRs then come first, and the rule PR turns the check on after them. "Only new and changed code" is not offered for such a rule.

### 5.4 Existing code (D81)

- **Fix it now.** After the rule PR, cleanup PRs fix the baselined files, each within R03 and each removing its files' baseline lines in the same commit. Source files go in `[refactor] Apply P01 to <area>`, written by DV5 and reviewed by CR1. Test files go in `[P01 test-fix] Apply P01 to tests`, written by TE6 and reviewed by TM2 and CR1. The main session groups the files into PRs of at most 5 files. `status` gives `cleanup` until no `baseline: P01` line is left (section 3.2). A review rule's cleanup follows AR6's list of files the same way.
- **Only new and changed code.** The baseline stays. When the Developer or the Test Engineer changes a file that the baseline names, it fixes that file for the rule and removes its baseline line, as Q6 does for old code. This part is a written instruction in F04 (section 8), because no check can see whether a change touched a rule's old violations.

### 5.5 What the rule PR may not hold

R02 keeps documents out of a `[rules]` PR, so an architecture change is its own `[docs]` PR before it (section 4.2). Source and tests are never in it either: cleanup comes in its own PRs. A test that enforces a project rule is not part of F09 (D80).

### 5.6 A rule for every project (D83)

A rule for every troy-mode project lives in troy-pstack and ships in a new plugin version (5.8). F09 does not change troy-pstack. It prepares the change for troy-pstack's own process:

1. **AR6** proposes the enforcement as for a project rule, and also names the troy-pstack files that change: requirements section 6 with the new R row, the rules template, troy-check with a check and its tests, or a role's agent file. It says whether existing projects' code would break the rule when the upgrade brings it. AR6 reads these files in the plugin folder.
2. **The proposal** goes to Troy as in section 5.2, and asks whether to open an issue in troy-pstack.
3. **On Troy's yes,** F09 writes the proposal in English to a file, checks it with `check-text`, and runs `gh issue create --repo <owner>/troy-pstack --title "Rule proposal: <summary>" --body-file <file>`. The repository comes from the plugin folder's `origin` remote. Nothing changes in the project now.
4. **Later,** troy-pstack builds the rule through its own design and build process. The new plugin version reaches each project through troy-init's upgrade, which replaces the R rows and troy-check (F06 D54). F07's `status` says when a project's copy is older than the plugin's.

Opening the issue reaches outside the project, so it always needs Troy's yes, as creating a repository does (F06 D52).

## 6. Changing and retiring rules (D84)

- **A P rule changes** through the same steps, with `[rules] Change P01, <summary>`. `rule-row` replaces the row, keeps its Since date, and records the change in the change log. Config and baseline lines change in the same PR.
- **A P rule is retired** with `[rules] Retire P01, <summary>`. `rule-row --retire` keeps the row and starts its Rule cell with "Retired on <date>." Its Enforced by cell becomes "None". The PR removes the rule's config and baseline lines. A retired ID is never used again. A retirement needs no AR6 run: the main session shows Troy what the PR removes, and Troy's yes approves it.
- **An R rule** is troy-mode's, and troy-init's upgrade replaces the R rows (F06 D54), so a project never edits one. Where troy-check's config allows an adjustment, such as R03's limits, R11's coverage limits, or R19's attribution mode, a P row records it, for example "P02: In this project, R03's limit is 800 changed lines.", and the rule PR changes the config. Any other change to an R rule is a rule for every project (section 5.6).
- **`[flow] troy_approves_first`** stays F07's own `[rules]` PR (F07 D62).

## 7. Role tasks (F04)

| Task | Role | When | What it does | PR |
| --- | --- | --- | --- | --- |
| AR6 Rule enforcement | Architect | Step 2, and step 4 after Troy approves an architecture change | Section 5.1. The first run changes nothing. The second writes the architecture change and its ADR. | None, then `[docs] Change the architecture for P01` |
| DV5 Cleanup | Developer | Step 6 | Fixes the source files that the brief names for the rule, and removes their baseline lines. Stays within R03. | `[refactor] Apply P01 to <area>` |
| TE6 Test cleanup | Test Engineer | Step 6 | The same for test files | `[P01 test-fix] Apply P01 to tests` |

- The reviewers (AR2, TM2, and CR1) also check every P rule of type Review whose Enforced by names their role, and name the rule's ID in a finding.
- The Developer and the Test Engineer fix a baselined file that they change for any other reason, and remove its baseline line (section 5.4).
- TE5 belongs to F08's design, so this flow's Test Engineer task is TE6. Both can land in either order.

## 8. Changes to earlier features

- **F01 templates.** The rules template's guidance describes P rows: the ID, a retired row, and the `baseline: P01` comment. The README's PR kinds gain `[P01 test-fix]`. F01's design gets a change-log row.
- **F02 troy-check.** The `test-fix` title takes a P ID, as in `[P01 test-fix] Apply P01 to tests`. F02's design gets a change-log row.
- **F03 `troy-check code`.** For a test-fix PR with a P ID, R10 does not look for a feature's test plan. R09 and R10 treat it as "any other kind". F03's design gets a change-log row.
- **F04 roles.** AR6, DV5, and TE6, and the two rules of section 7. The structure tests count the new tasks. F04's design gets a change-log row.
- **F07 entry skill.** The routing table sends rule requests to F09. The engine gains section 3's commands, the `rules` snapshot role, the baseline rule in `check-run`, and the `cleanup` action. The skill reads the P rows of type Process at every start and follows them. F07's design gets a change-log row.
- **F05 and F06** do not change. The main session's files are not limited by F05's hooks (F05 section 4), and every role in this flow stays in its scope. troy-init's upgrade keeps P rows (F06 D54) and never touches `project-rules.yml`, which troy-init does not own.

F08's design also changes F07's engine and skill. Whichever of F08 and F09 lands second rebases on the first.

## 9. How F09 maps to the requirements

| Requirement | Where F09 covers it |
| --- | --- |
| F09 row: the rule change flow (5.8) | Sections 4 to 6 |
| 5.8 step 1: Troy states the rule and its scope | Sections 4.1 and 4.2 |
| 5.8 step 2: the strongest enforcement that works | Section 5.1 |
| 5.8 step 3: one PR with the rules table, the check config, and the role instructions | Sections 5.3 and 5.5 |
| 5.8 step 4: existing code that breaks the rule | Section 5.4 |
| 5.8: a rule for every project ships in troy-pstack | Section 5.6 |
| 5.5 step 6: rules from the retrospective | Section 4.1 |
| R02: one kind of output per PR | Sections 4.2 and 5.5 |
| R12: the rules table in English and Chinese | Section 3.1, `rule-row` |
| F04 section 3: only troy-init and F09 change the rules table | Sections 3.1 and 5.3 |
| F07 D62: rule changes wait for F09 | Section 6 |

## 10. How F09 is checked

### 10.1 Tests

Tests use `unittest` and the standard library. A separate agent writes them from this design before the code exists, with F07's setup: a temporary git repository with a local bare `origin`, and a fake `gh` that serves PRs and issues from a JSON file and records its calls. They live in `troy-mode/flow/tests/`, and the troy-check and role changes add tests in their own suites.

| Group | Cases include |
| --- | --- |
| Rule IDs | The next free ID after P01 to P03, after a retired P04, and in a table with no P row. Baseline lines found per rule in TOML and YAML files. |
| Rule rows | A new row in both languages, with Since. A replaced row that keeps Since. A retired row. The next major version, the status, and one change-log row in both files. A row whose cells would break the table is refused. |
| Snapshot and check | The `rules` role may change config and dependency files only. A docs, source, or tests path is a scope problem. A dependency change that only deletes `baseline:` lines passes without `--allow-dependency`, and one that also adds or changes a line does not. |
| Status | `cleanup` while "fixed by cleanup PRs" baseline lines remain, none for "fixed when touched", and an open `[rules]` PR continued first. |
| Briefs | AR6, DV5, and TE6: their titles, Read first, and checks. |
| troy-check | `[P01 test-fix]` parses and may change tests and dependencies only. R10 looks for no test plan for a P ID. |
| Roles and skill | AR6, DV5, and TE6 in the agent files and in F04's structure tests. The reviewers' line about Review rules. The skill names the rule flow's steps and reads Process rules. |

### 10.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: a reused retired ID, a row written in English only, Since changed on a changed rule, the version raised by a minor step instead of to the next major, the `rules` role allowed to change docs, a baseline deletion that also adds a line passing `check-run`, `cleanup` given for "fixed when touched", `cleanup` given after the last baseline line is gone, and `[P01 test-fix]` allowed to change source. The counts go in the PR description.

### 10.3 Trial (D85)

Before the PR opens, F09 runs in nested `claude -p` sessions on Troy's PC, with troy-pstack loaded from the PR branch, on `ZJUCao/troy-mode-trial`, as F07's trials did. The trial's prompt gives Troy's answers. It runs under Troy's standing permission for troy-mode trials, which Troy added on 2026-11-08 as an `autoMode.allow` rule in troy-pstack's `.claude/settings.local.json`, which lets nested `claude -p` sessions act on `ZJUCao/troy-mode-trial` without asking. That permission covers no other repository, so the trial opens no issue in troy-pstack (step 6).

1. **Upgrade.** troy-init's upgrade brings the new troy-check, through its own PR.
2. **A lint rule that existing code breaks**, for example "No f-string in an exception message", which ruff's EM102 checks and `counting.py` breaks today. AR6 proposes it, Troy's answer chooses "fix it now", and the rule PR merges with one baseline line. That session ends.
3. **Resume.** A new session gets "continue", finds the cleanup from `status`, and DV5's `[refactor]` PR, reviewed by CR1, fixes the file and removes the baseline line.
4. **A review rule,** for example "Every error message names the file it is about". AR6 finds no tool for it, and the rule PR adds only the row.
5. **Retire** the review rule, with no role run.
6. **A rule for every project.** AR6 names the troy-pstack files. Troy's answer, from the prompt, declines the issue, so nothing is opened in troy-pstack.

It takes about 5 role runs (AR6 three times, DV5, CR1), about $4 to $7 from F07's trials, plus a few minutes of Actions for each of about 5 PRs.

### 10.4 Status

| When | F09's status in requirements 7.2 |
| --- | --- |
| The F09 PR merges after a passing trial | Runs on a sample project: troy-mode added two rules to a scratch GitHub project, one checked by a lint with a baseline and a cleanup PR, one checked in review, retired one, and proposed a rule for every project. Not yet used on a real project. |
| The pilot (F11) adds or changes a rule | Used on a real project |

If the trial cannot run before the PR, the status is "Written" until it does. The status update is its own PR.

## 11. Not in F09

- Tests that enforce a project rule (D80).
- Building a rule for every project in troy-pstack, and opening PRs there (D83).
- Project checks that need the project's environment outside the pack's own job.
- Editing R rows in a project (D84).
- Rules in the other members of a series.

## 12. Decisions for Troy

F08's design ends at D78, so F09 continues from D79. Troy accepted every recommended answer on 2026-11-08.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D79 | Who picks a rule's enforcement and finds the code that breaks it (5.8 step 2)? | A: the Architect, in a new task AR6, which reads the rule, the architecture, and the pack's config, runs the check on the whole repository, and reports a proposal for Troy (section 5.1). B: the main session itself. | A. The Architect owns the coding rules and the module rules (requirements section 4), and an opus run with Bash can run the tool. It costs one role run per rule. |
| D80 | What can enforce a project rule? 5.8 step 2 lists architecture, a lint or CI check, a test, and role instructions. | A: architecture through a `[docs]` PR; a rule of a tool the pack already runs, a troy-check limit, or a step without an environment in the project's own workflow; or a Review or Process row in the rules table. Tests for project rules wait until a real project needs one (section 5.1). B: also tests, with a new `[P01 test]` PR kind, a Test Engineer task, and P IDs in troy-check's R10. | A. Python's and C/C++'s tools cover most code rules, and B adds a PR kind, a role task, and a troy-check change before any project has asked for one. This changes 5.8 step 2 in the requirements to note it. |
| D81 | How does a rule PR deal with existing code that breaks it (5.8 step 4)? | A: the rule PR turns the check on with a baseline of today's violating files, each line marked `baseline: P01`, so CI stays green. "Fix it now" then means cleanup PRs that remove the baseline line by line. "Only new and changed code" keeps the baseline, and authors fix a baselined file when they change it (section 5.4). B: cleanup PRs first, then the rule PR, with no baseline. C: turn the check on and let CI fail until the cleanup is done. | A. The rule protects new code from the day Troy approves it, the cleanup is visible and counted, and both of Troy's choices use one mechanism. B leaves new code unchecked during the cleanup. C blocks every other PR. |
| D82 | How does Troy approve a rule? | A: one proposal message, whose answer approves the rule and makes 5.8 step 4's choice. F07 then writes and merges the PRs without asking again. The rules table moves to the next major version, "Approved by Troy" (section 5.2). B: Troy also approves the rule PR itself. | A. Troy decides once, with every fact in one message, and the PR holds nothing Troy has not seen. It matches how Troy approves requirements in chat (F07 D61). |
| D83 | What does F09 do with a rule for every project? 5.8 says it lives in troy-pstack and ships in a new plugin version. | A: AR6 proposes it with the troy-pstack files that change. On Troy's yes, F09 opens an issue in troy-pstack. troy-pstack builds it through its own process, and projects get it through troy-init's upgrade (section 5.6). B: as A, plus a P rule in the project at once, until the plugin ships the R rule. C: F09 opens a PR in troy-pstack. | A. troy-pstack is built with designs and approvals that F09 cannot run, and the issue keeps the proposal until then. B leaves a P row that the later R row duplicates. C changes the plugin without its design process. |
| D84 | How are rules changed and retired? | A: P rules change or retire through the same flow. A retired row stays, marked "Retired on <date>", and its ID is never reused. A project adjusts an R rule only through a P row and troy-check's config, such as R03's limit. Any other R change is a rule for every project (section 6). B: also let a project edit its R rows. | A. troy-init's upgrade replaces the R rows (F06 D54), so an edited R row would be undone at the next upgrade. A retired row keeps the history readable. |
| D85 | How is F09 tried out, and when does its status move? | A: tests and planted bugs, plus a trial on `ZJUCao/troy-mode-trial` with a lint rule and its cleanup across a session break, a review rule, a retirement, and a rule for every project, with Troy's answers in the trial's prompt (section 10.3). B: the same, on a local bare `origin`, with no CI. Status "Written" until the pilot. | A. Only a real repository shows that the rule PR and its baseline pass CI and merge. It costs about 5 role runs, about $4 to $7, and a few Actions minutes, and runs under Troy's standing permission for trials on that repository. |

Requirements 1.25 records the approved changes:

- The F09 row: the Architect's AR6, what can enforce a project rule, the baseline and cleanup PRs, Troy's approval in one message, rules for every project as an issue in troy-pstack, and changing and retiring rules (D79 to D84).
- 5.8 steps 2 to 4: no tests for a project rule yet, the rules table's row as a project rule's role instruction with an architecture change in its own PR first (D80), and the baseline (D81).
- 5.8, rules for every project: the proposal becomes an issue in troy-pstack on Troy's yes (D83).

## 13. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-08 | First draft. |
| 1.0 | 2026-11-08 | Approved by Troy with D79 to D85, every recommended answer. |
| 1.1 | 2026-11-08 | Section 10.3 and D85: the trial runs under Troy's standing permission for troy-mode trials on `ZJUCao/troy-mode-trial`, which Troy added on 2026-11-08, in place of a yes in chat. A process change of Troy's, not a requirement change. |
