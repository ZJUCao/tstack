# F16 design: role exam

| | |
| --- | --- |
| Feature | F16 in [requirements 1.42](../requirements.md#72-feature-list) |
| Version | 1.7 |
| Date | 2026-11-21 |
| Status | Approved by Troy on 2026-11-16, with D151 to D160; D152 refined by Troy on 2026-11-18 (section 4.3). Version 1.5 makes U4 a must, as D152 says, in the PR that lands troy-pstack#64's hook. Version 1.6 adds D233, which Troy approved on 2026-11-21 as tstack issue #49: U5 stays a note. |
| Source of truth | This English file. [`F16-role-exam.zh-CN.md`](F16-role-exam.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F16 tests troy-mode's role instructions where the pilot showed that they fail, and keeps a change to them from merging until it has passed that test (requirements F16 row and 4.1). It delivers:

1. **Cases.** A case is one role task in a scratch copy of a project state where the pilot's mistake happened, with the checks and the rubric that grade it (section 4). The first set holds twelve cases, two for each role that runs as a subagent, all taken from `ZJUCao/recipe-menu`'s v0.1 (section 5).
2. **An engine, `troy_exam.py`.** It builds the case projects, runs each role through the bundled CLI non-interactively, grades the runs blind, compares a PR's instructions with its base's, and writes the report and the PR's exam section (sections 6 to 11).
3. **A gate.** A PR that changes a role's instructions carries the exam's result in its description, and a CI check refuses the PR when that result is missing or older than the PR's instructions (section 9). The exam itself runs on Troy's PC only, never in CI.
4. **A hillclimb loop** for improving a role against its cases, one change at a time, with a decision log (section 8.3).

F16 follows two playbooks of `poteto-mode`, which it reads and never changes (requirements 4.1). `eval` gives the blind runs and the judge. `hillclimb` gives the comparison: a harness proved sensitive and then frozen, a baseline before any change, one change per measurement, and keep or revert. Where a playbook assumes something troy-mode does not have, this design says what F16 does instead: the judge uses the same model family as the roles (section 6.2), and the words a role must not see leave out troy-mode's own vocabulary, such as "test plan" (section 6.1).

The facts here come from the repository at `8ddbef0` (plugin 0.5.0, requirements 1.41), the pilot's PRs and review comments on GitHub, the pilot's 353 role and helper transcripts on Troy's PC, read only, and the probes of section 2.3, run with Claude Code 2.1.325, the CLI that the desktop app bundles. F16 lands in one PR (Q10).

## 2. What the pilot and the probes showed

### 2.1 The roles' mistakes

The pilot report names the roles' mistakes in its section 3 (problems 1, 2, 3, 7, 9, 13, 14, 15, 16, and 19) and counts the reviews that requested changes in its section 5.5: the Architect 4, the Test Manager 12, and the Code Reviewer 28. The F11 wrap-up's hand-over note lists them by role. In this design, a bare `#<n>` is a PR of `ZJUCao/recipe-menu`, and troy-pstack's issues always carry its name. Grouped by what can fix them:

| # | Mistake | Who | Recipe-menu PRs | Can role instructions fix it? | In F16 |
| --- | --- | --- | --- | --- | --- |
| 1 | A mock note that points at nothing, or says that a stub raises or sorts when it does not | Developer, DV1 | #36, #42, #55, #57, #67, #81, #88 | Yes: troy-pstack#63 gives the DV1, DV2, and CR1 briefs fixed sentences | dv-mock-notes, dv-impl-notes, cr-mock-review |
| 2 | A test that checks less than its plan case expects, such as the exit code only | Test Engineer, TE1 | #17, #43, #62, #68, #75, #82, #89 | Yes | te-plan-asserts, tm-test-review, cr-test-review |
| 3 | A test support module's doc comment that lists names, which then drift from the code (R05, later the project rule P01) | Test Engineer | #62, #68, #75, #82, and the P01 cleanups #96 to #99 | Yes | te-helper-docs |
| 4 | Python examples in a design that `ruff format --check` rejects | Interface Designer | #9, #52, #59 | Yes, or in the pack instead (troy-pstack#51) | if-example-format, ar-design-review |
| 5 | Errors that the architecture's error handling rules call for, left out of a design | Interface Designer | #14, #20, #52, #71, from the Architect's findings | Yes | if-error-rules, ar-error-review |
| 6 | A test plan's expected result that contradicts the design, found only at the test review | Test Manager, TM1 and TM7 | #68, #75, #92 | Yes | tm-plan-expected |
| 7 | `sed -i` on files with CRLF line ends, which turned them into LF | Architect | #3 | Yes | Universal check U3 |
| 8 | Python that reads its program from standard input, which hung in 39 of 168 runs | Developer, Test Manager, main session | troy-pstack#64 holds the data | A hook will: troy-pstack#64 | Universal check U4 |
| 9 | A process left running after the report, and a background run that outlived its report | Developer, Test Engineer | From #12, seen on #23 | Partly: troy-pstack#49 | Universal check U5 |
| 10 | 变更记录 written for 修改记录, the Architect's status words edited by the Product Manager, a merge before CI reported, `check-text`'s output read with grep, CI failures not counted as attempts | Main session | #2, #3, #47, #92, #52 | No: the engine and the hooks fix them (troy-pstack issues #46, #47, #68, #65, and #73) | None (section 3) |

The probes of section 2.3 found one more, which no PR shows: a Developer run skipped common rule 3, reading `docs/rules.md`, and said so in its report. That becomes universal check U6.

### 2.2 What a role run costs and takes

From the pilot's subagent transcripts, at the list prices of the pilot report. The transcripts run to recipe-menu #99, so they hold a few more runs than the report's table (section 5.2).

| Role | Model | Runs | Minutes, median | Minutes, 90th percentile | Cost per run, median | Cost per run, mean (report 5.2) |
| --- | --- | --- | --- | --- | --- | --- |
| Developer | sonnet | 44 | 2.7 | 23.3 | $0.28 | $0.41 |
| Test Engineer | sonnet | 35 | 4.9 | 19.6 | $0.39 | $1.47 |
| Code Reviewer | opus | 77 | 9.0 | 15.2 | $1.54, plus about $1.09 for its helper agent | $1.91, plus $1.27 for helpers |
| Test Manager | opus | 58 | 8.3 | 34.9 | $2.21 | $4.57 |
| Architect | opus | 33 | 11.5 | 21.1 | $2.94 | $3.29 |
| Interface Designer | opus | 28 | 11.6 | 31.7 | $3.39 | $4.98 |

The mean is above the median because a few long runs cost much more: the 90th percentile of a Test Manager or an Interface Designer run is $11.50. Section 10 estimates the exam from these numbers.

### 2.3 Probes

On 2026-11-16, nested `claude -p` sessions ran in a scratch troy-mode project in this session's scratchpad: a git repository with `.troy-mode/`, a short `docs/rules.md`, one Python file, and a local bare `origin`. The plugin was a `git archive` of this branch in a folder named `troy-pstack`, loaded with `--plugin-dir`, and Troy's installed plugin was turned off for each session with `--settings` (F19 design, probe 3). The task was a DV4 brief: delete one named function. Nothing outside the scratchpad changed, apart from the sessions' own transcripts under `~/.claude/projects/`. The probes cost $0.06 in all.

| Probe | Setup | What happened |
| --- | --- | --- |
| A | A main session on haiku, told to call the Agent tool once with `subagent_type` `troy-pstack:troy-developer`, `model` `haiku`, and the brief copied exactly | The copy loaded as `troy-pstack@inline`, and Troy's plugin did not load. The Agent call's prompt was the brief, byte for byte. The call ran in the background by default, so the session ended its turn, resumed when the role finished, and wrote two `result` events. With only `Agent` allowed, the role's Bash calls were refused. The role's transcript was `~/.claude/projects/<folder key>/<session ID>/subagents/agent-<ID>.jsonl`, next to a `.meta.json` that names `agentType` and the model. |
| A2 | As A, with the role on sonnet, `run_in_background` false, `--permission-mode auto`, and `--permission-prompts none` | One `result` event. The role ran Bash, Read, Edit, and Grep, deleted the function, and handed its report back through a `SubagentHandback` tool call. The hooks' `SubagentStart`, `PreToolUse`, `PostToolUse`, and `SubagentStop` all ran for it. `total_cost_usd` was $0.045, and `modelUsage` split it: $0.003 for the haiku main session and $0.042 for the sonnet role. The report said that the role had not read `docs/rules.md`. |
| B | The brief as the `-p` prompt, with `--agent troy-pstack:troy-developer` | The role ran as the main session, with the agent's tools and the session's model. The hooks saw a main-session caller, so the role's write scope was not checked. |
| C | `--max-budget-usd 0.0001` | The session stopped after its first turn with `error_max_budget_usd` and exit code 1, having spent $0.0019. The cap is checked after each turn, so a run can pass it by one turn. |
| D | A haiku session with `--tools Read,Glob,Grep` and `--json-schema`, in a folder that held a rubric and two labeled diffs | The verdict came back in `structured_output`, in the schema's shape: pass or fail with one sentence of evidence for each criterion and label. It cost $0.004. |

So:

- A role that a cheap main session starts as a subagent runs as it does in a real troy-mode session: with the engine's brief, the agent file, the hooks, and its write scope. `--agent` does not (probe B).
- The brief must be checked to have arrived unchanged, because the main session copies it (probe A).
- Roles run in the foreground, so a run's end is the session's end (probes A and A2).
- Each run's cost, split by model, comes from the `result` event (probe A2).
- `--max-budget-usd` is a ceiling per run that one turn can overshoot, so the exam keeps its own sum (probe C).
- A judge's verdict can be read as data (probe D).

## 3. What the exam covers (D151)

The six roles that run as subagents: the Architect, the Interface Designer, the Test Manager, the Developer, the Test Engineer, and the Code Reviewer. The exam runs each one exactly as the entry skill starts it: the engine's brief from `troy_flow.py brief`, the agent file, the hooks, and the case's model and effort (sections 4 and 11.3).

The Product Manager, which is the main session, gets no cases in this version:

- Its pilot mistakes (section 2.1, row 10) are all being fixed in the engine and the hooks, which unit tests check exactly, and none in its instructions.
- A main-session run needs the whole entry skill: `status` reads GitHub, and approvals wait for Troy. A case would need a GitHub repository, Troy's answers given in advance, and several turns, and the pilot's main session cost $13 to $32 per feature.
- A change to `troy-mode/roles/product-manager.md`, or to the skill's sections that only the main session follows, is checked as today: by its design and a trial on `ZJUCao/troy-mode-trial`.

Requirements 1.41's F16 row said "trap tasks for each role", and requirements section 4 counts the Product Manager as a role. So D151 narrows the row, in requirements 1.42, to "each role that runs as a subagent", and the Product Manager's cases come with a later design, once a main-session case can run without GitHub. That is a requirement change, which Troy approved with D151 on 2026-11-16.

## 4. A case (D152)

### 4.1 Its parts

A case is a folder `troy-mode/exam/cases/<case ID>/`:

| File | What it holds |
| --- | --- |
| `case.toml` | The role, the task, the item, the project state to start from, the model and effort, the limits, and the criteria |
| `rubric.md` | The judge's criteria, 3 to 6 of them (eval playbook), in English. Only the judge reads it. |
| `input.md` | The brief's Input, when the task has one, written as the entry skill writes Input (its section "Running a role"). There is none for a first round. |
| `start.patch` | For a review case: the change of the head that the pilot's round-1 review saw, applied on the start commit |
| `mutants/*.patch` | For a case that writes tests: changes to the pilot's implementation that a test of the plan must catch |
| `anchors/fail/`, `anchors/pass/` | The pilot's own output that its reviewer caught and the output that merged: the diff and the report of each |

`start.patch` keeps the round-1 head in troy-pstack, because GitHub keeps a force-pushed commit only as long as it chooses to. `case.toml` for the first case, with the commit shortened here:

```toml
id = "dv-mock-notes"
version = 1
role = "developer"
task = "DV1"
item = "F05"

[start]
repository = "ZJUCao/recipe-menu"
commit = "b966872"        # the base of the pilot's PR #36, the F05 mock
branch = "troy-mode/f05-3-mock"
pilot = ["#36", "#42", "#55", "#57", "#67", "#81", "#88"]

[run]
model = "sonnet"
effort = "high"
minutes = 45
max_cost = 2.50

[[criteria]]
id = "stub-bodies"
check = "mock_bodies_only_raise"
must = true

[[criteria]]
id = "notes-true"
judge = 1                 # criterion 1 of rubric.md
must = true
```

### 4.2 The project a run starts from

The runner builds a fresh project for every run:

1. **History.** From a mirror of the start repository, cloned from GitHub into the work root and never from the project's own folder, a new repository holds the history up to `start.commit` and nothing later, so no later commit, review, or fix can be read from it. A test checks that no later commit is reachable.
2. **Branch.** `start.branch`, created from the start commit. For a review case, `start.patch` is applied and committed with the PR's title, as the main session would have left it.
3. **origin.** A local bare repository with the same history and its `HEAD` on `main`, so that `origin/main` and `origin/HEAD` exist (`/security-review` needs them), and nothing can reach GitHub.
4. **gh.** A stand-in on the session's PATH answers the read-only PR commands that roles use, `gh pr view`, `gh pr diff`, and `gh pr checks`, from the local branch, and refuses every other command with a "no network" error. No command of a run reaches GitHub.
5. **Checkout.** Troy's git settings apply, `core.autocrlf` true among them, so the working tree has CRLF line ends as in the pilot. `core.hooksPath` is `.troy-mode/checks/git-hooks`, as troy-init sets it.
6. **Environment.** One mamba environment per start repository and lock file, which the runner creates in its own folder from the start commit's `environment.yml` and `requirements-dev.lock`, with no editable install, and which every run shares read-only. Each run sets `TROY_MODE_ENV_PREFIX` to it, so the brief's check commands use it (`checksteps.py`), and `PYTHONPATH` to the run's `src`. Troy's own environments, such as `recipe-menu`, are never touched: an editable install there would point the pilot's environment at a scratch folder.
7. **Folder.** `<work root>\<six random letters>\<repository name>`, for example `D:\Troy\troy-mode-work\qhzwtd\recipe-menu`, next to its origin `...\qhzwtd\recipe-menu.git` and its plugin copy `...\qhzwtd\troy-pstack` (section 6.1).

### 4.3 Criteria

Each run is graded on the universal checks and on the case's own criteria. A criterion is a check, which is a script in `troyexam/checks/` that reads the run's files, or a judge criterion from `rubric.md`. Each criterion is a must or a note. A run passes when every must criterion holds.

The universal checks, on every run, by script:

| ID | Passes when | From |
| --- | --- | --- |
| U1 | The role's last message is a report in its Report section's format, with a valid Result. | F04 design 5.2 |
| U2 | `troy_flow.py check-run`, against a snapshot taken before the run, finds no problem: the role changed only files in its write scope, and HEAD and the branch did not move. | F07 design D59 |
| U3 | No file that the role changed had its line ends changed as git stores it, for example from CRLF to LF. A line end that only the checkout's `core.autocrlf` changes is no change. | Pilot problem 3 |
| U4 | No shell command of the role ran Python that reads its program from standard input. | Pilot problem 14, troy-pstack#64, R23 |
| U5 | No process that the run started is still running after the session has exited. | Pilot problem 7, troy-pstack#49 |
| U6 | The role read `docs/rules.md` before its first change, or before its report when it changes nothing. | Common rule 3, probe A2 |
| U7 | The role tried no git or GitHub command that changes anything, whether or not a hook refused it. | Common rule 6 |

U1, U2, U3, U4, U6, and U7 are must criteria. U5 is a note: it is checked and reported on every run, but it does not fail it. D152 planned to make it a must in the PR that lands troy-pstack#49's hook. That fix, F05 design D231, ends a role's leftover commands from the main session, after the role's report. In an exam, the role's session exits right after the report, and Claude Code ends the session's background commands as it exits (F05 design section 6.1, probe D). So U5 can fail only for a process that has left Claude Code's process tree, which no fix addresses yet, and it stays a note (D233). For the same reason, `check-run`'s new `running` problem never shows in an exam: `SessionEnd` has closed the role's records before the runner calls `check-run`, so U2 grades as before. U4 was a note too, until the PR that landed troy-pstack#64's hook, R23 (F05 design 8.3), made it a must. While that hook was pending, U4 alone would have failed nearly every run of every role and hidden the cases' own traps: in a proof of te-helper-docs on 2026-11-17, all five runs failed U4. Troy approved this on 2026-11-18 (D152).

U4 reads each shell command with R23's own check, the hook's code, so U4 and the hook agree on what reads its program from standard input. U4 counts only the commands that ran: a call that a hook or a permission refused did not run, so it does not fail U4. U7, by contrast, counts every try. Otherwise a role that tries `python -` and is refused would still fail U4, and U4 would again fail nearly every run. A run graded before version 1.5 graded U4 as a note, and it is not reused as a base run afterwards, because the change to `troyexam/` changes the instruction hash (section 8.2).

U4, U6, and U7 read the role's transcript, as the eval playbook asks ("verify the chain from transcripts, not self-report"). U2, U3, and U5 read the project and the process list, and U7 also reads `hooks.log`. One more test is not a criterion but a condition: the role's first message must equal the brief that the engine rendered, apart from a last line `END`, the driver prompt's own marker, which the main session sometimes copies. A run that fails it is void and runs again (section 11.5).

The case's own checks come from a library that the build writes and tests:

| Check | What it does |
| --- | --- |
| `pack_steps_pass` | Runs the brief's Checks to run again, after the run |
| `ruff_format_blocks` | Runs `ruff format --check` with the project's settings on the python code blocks of the documents that the role wrote |
| `mock_bodies_only_raise` | Every body of the feature's interfaces only raises `NotImplementedError` |
| `no_mock_notes_left` | No paragraph of a doc comment starts with "The mock" |
| `tests_fail_on_mock` | Every new test fails against the mock, and not by an import error (R09) |
| `tests_pass_on_pilot` | The new tests pass on the pilot's implementation of the feature, the merge commit of its PR 5 |
| `tests_fail_on_mutants` | Each mutant in `mutants/` makes at least one new test fail |
| `result_is` | The report's Result is the one the case names, such as `changes-requested` |
| `changed_only` | The diff touches only the paths or lines that the case names |

The judge's criteria cover what a script cannot decide: whether a doc comment is true of the mock, whether a review's findings cover the points that the pilot's review found, and whether a finding is false.

### 4.4 The rubric and the anchors

`rubric.md` holds 3 to 6 criteria. Each is a question with pass and fail described in observable terms, for example: "Every sentence of each doc comment is true of the mock's body. A note that points elsewhere, with 'these', 'this', 'above', or 'below', fails." A review case's rubric holds the key: the pilot's round-1 findings that its round-2 change fixed, one per line, which the judge matches against each run's findings. The rubric names no instruction file, no task text, and no version.

The anchors are the pilot's own outputs: the one that failed, which the pilot's reviewer caught, and the one that passed, which merged. They prove that the grading separates the two (section 4.5), and they check the judge in every pass (section 6.2).

### 4.5 Proving a case

A case joins the exam only when `troy_exam.py prove <case>` has proved it, as the hillclimb playbook's step 2 asks: "Build the measurement harness, prove its sensitivity, then freeze it."

1. **The grading separates.** The checks, and the judge in two separate passes, grade the fail anchor as failing and the pass anchor as passing.
2. **The trap is live or not.** Five runs with the instructions on troy-pstack's `main`. If at least one fails, the trap is live, and a later change can show that it fixes it (section 7.2). If all five pass, the case still guards against a change that makes the role worse, but it cannot show a fix.
3. **The record.** `prove` writes the anchors' grades and the five runs into the case's history. They are also the first base runs (section 8.2). The case's `version` rises whenever its files change, which makes all its earlier runs stale.

## 5. Choosing cases (D153)

### 5.1 The rule

A mistake from the pilot becomes a case when:

1. A subagent role made it, in its own work (section 3).
2. Role instructions can prevent it: the agent file, the common rules, the brief, or a template. A mistake that a hook or the engine makes impossible gets a universal check instead (U3 to U7), which watches it until that fix lands and keeps watching after.
3. It repeated: it was seen in two or more PRs, or the retrospective's `retro` grouped it as repeated, or Troy names it.
4. Its project state can be rebuilt from the pilot's history.

A review case comes from the same mistakes. The role reviews the pilot's round-1 head, and the trap is approving it. The pilot's reviewers caught each of these, so the review cases guard what already works, which a change such as troy-pstack#75 (security review once per version) must not break.

Each role has at least two cases and at most four, so one role's exam stays affordable (section 10). The mistakes seen in the most PRs come first, one case per mistake.

### 5.2 The first twelve

All start from `ZJUCao/recipe-menu`. The Start column names the pilot PR whose base, or whose round-1 head, the case starts from.

| Case | Role | Task | Start | The trap, from the pilot | Graded mainly by | Seen in |
| --- | --- | --- | --- | --- | --- | --- |
| dv-mock-notes | Developer | DV1 | The base of #36, the F05 mock | A mock note that points at nothing, stands inside another paragraph, or says that a stub raises or sorts when it does not | `mock_bodies_only_raise`; the judge: every doc comment sentence is true of the mock | #36, #42, #55, #57, #67, #81, #88 |
| dv-impl-notes | Developer | DV2 | The base of #57, the F08 implementation, with the mock's notes in place | A mock note left behind, or a doc comment that still describes the mock or names an exception that the code does not raise | `no_mock_notes_left`, `pack_steps_pass`; the judge: the doc comments match the code | #12, #57, #76 |
| te-plan-asserts | Test Engineer | TE1 | The base of #89, the F13 tests | A test that checks less than its plan case expects, such as the exit code only, or only that a folder exists | `tests_fail_on_mock`, `tests_pass_on_pilot`, and `tests_fail_on_mutants`, with one mutant for each finding of the pilot's round-1 test review | #17, #43, #62, #68, #75, #82, #89 |
| te-helper-docs | Test Engineer | TE6 | The base of #97, a P01 cleanup, with P01 in the project's rules | A support module's doc comment that lists names, or says what the module does not do | The judge, with the Test Manager's round-1 findings as the key | #62, #68, #75, #82, #96 to #99 |
| if-example-format | Interface Designer | IF1 | The base of #59, the F09 design | Python examples that `ruff format --check` rejects: lines over 100 columns, or the other quote style | `ruff_format_blocks` | #9, #52, #59 |
| if-error-rules | Interface Designer | IF1 | The base of #52, the F08 design | Errors that the architecture's error handling rules call for, left out | The judge, with the Architect's round-1 findings 1 to 3 as the key | #14, #20, #52, #71 |
| ar-design-review | Architect | AR2 | #52's round-1 head | Approving that design, whose examples fail `ruff format` and whose failures break architecture 6 | `result_is` changes-requested; the judge: findings 1, 2, and 4 of the key found, and none false | #52 |
| ar-error-review | Architect | AR2 | #71's round-1 head, the F11 design | Approving a design whose failure lines break the error rules | `result_is`; the judge, with the round-1 findings as the key | #14, #20, #71 |
| tm-plan-expected | Test Manager | TM1 | The base of #73, the F11 test plan | An expected result that contradicts the design or the prototype, as F11-T19's did until the test review on #75 | The judge, with the expected results that the pilot corrected later as the key | #68, #75, #92 |
| tm-test-review | Test Manager | TM2 | #89's round-1 head | Approving tests that check less than the plan expects | `result_is`; the judge, with round-1 findings 1 to 4 as the key | #89, and the same mistake in six more PRs |
| cr-mock-review | Code Reviewer | CR1 | #36's round-1 head | Approving a mock whose notes are false | `result_is`; the judge, with round-1 findings 2 and 4 as the key | #36, #55, #88 |
| cr-test-review | Code Reviewer | CR1 | #30's round-1 head, the F04 tests | Missing that `"a\b"` is a backspace where the plan means a backslash | `result_is`; the judge, with round-1 finding 1 as the key | #30 |

If `prove` cannot prove a case from its start, the build takes another PR of the same mistake, and the build PR says so.

### 5.3 Adding, changing, and retiring cases

- **Adding.** A later project, a retrospective's repeated group, a second pilot, or F17's evidence of the same mistake twice proposes a case by the rule of 5.1. Each case is added in its own troy-pstack PR, with `prove`'s record in the PR's exam section (section 9.3). A fifth case for a role replaces the role's case whose trap has stayed dead on `main` longest, and the PR says which.
- **Changing.** A rubric that the judge misreads, or a start that no longer builds, is fixed in its own PR, and the case's version rises, so both versions are measured again.
- **Retiring.** A case is retired only when its role no longer does its task, for example after F04 removes the task.

## 6. A blind run (D154)

### 6.1 What the role sees

The role must not be able to tell that it runs in an exam, which version of its instructions it has, or that other runs exist (eval playbook, "Non-negotiables for blinding").

- **The same start as a real run.** The prompt is the engine's brief for the case project, from `troy_flow.py brief` of the version under test. The agent file, the hooks, and the engine are that version's. The model and effort are the case's. The main session that starts the role belongs to the runner, and its prompt never reaches the role (section 11.3).
- **Two plugin copies, one name.** Each version is a `git archive` of its commit into a folder named `troy-pstack` inside the run's random folder. After F19 the folder is named `tstack`, so that the hooks' Read rule still matches it (F19 design 5.2). The paths a role sees, `${CLAUDE_PLUGIN_ROOT}` among them, differ only by random letters.
- **No exam words.** Nothing the exam adds, whether a folder, a file name, a branch, an environment variable, an Input, or a stand-in's message, holds any of these words: eval, exam, trap, judge, rubric, grade, score, compare, experiment, candidate, variant, arena, baseline, hillclimb, or sandbox, nor the labels that the exam gives the two versions. The runner checks every such text before a run starts, and refuses to start on a hit. The eval playbook also bans "test" and "benchmark". F16 does not, because they belong to troy-mode's own work, its test plans, `tests/` folder, and `benchmark-checklist`, which every real run shows too.
- **Isolated.** Each run has its own folder, session, and project. The runs of the two versions alternate in time. The local origin and the `gh` stand-in give the role nothing later than its start (section 4.2).
- **Graded from what it did.** No prompt asks the role which instructions or files it followed. U4, U6, and U7 read that from its transcript (eval playbook step 6).

What a role can still notice: the project's last commit is days old, and `gh` answers only PR reads. A real run after a pause shows the first too.

### 6.2 What the judge sees

The judge is a fresh session that did not do the task: a `claude -p` session on opus, with no plugin loaded and only the Read, Glob, and Grep tools, in a folder that holds nothing but the rubric and the outputs to grade (section 11.4).

- **Every run of both versions in one pass,** on one scale (eval playbook). There is one judge session per case in each exam.
- **Shuffled labels.** Each run's output sits under a random label, R01 and on, in a random order. The two anchors are two more labels among them. The key that maps the labels to runs stays in the results folder, outside the judge's folder, where `-p` mode does not let it read.
- **Outputs only.** The run's diff, its report, and the files that the rubric names, with the plugin's path written as `<plugin>` and the project's as `<project>`. No brief, no agent file, no transcript, no model name, no cost, and no time.
- **A verdict as data.** `--json-schema` gives the verdict in a fixed shape: for each label and criterion, pass or fail, with one sentence of evidence that quotes the output (probe D).
- **Checked by its anchors.** If the judge fails the pass anchor or passes the fail anchor, the verdict is void and the pass runs once more. A second miss stops the case as "rubric unclear", which fails the exam for that case until a case PR fixes the rubric.

Two limits:

- A report can quote its instructions, for example "the sentences the brief gives", which could hint at a version. The judge's prompt says that the outputs come from separate runs of one task and asks it to grade by the rubric only, and the checks by script, which nothing can bias, decide every criterion they can.
- The eval playbook puts the judge on another model family than the candidates. Here, every run of both versions uses the role's own model, so a family's bias cannot favor one version over the other. And troy-mode uses no service beyond GitHub and Anthropic (requirements section 8, Privacy). So the judge runs on opus for every role.

### 6.3 The session that runs the exam

A troy-pstack session on Troy's PC starts the exam, usually the session that built the change. It knows which version is which, so it does not grade. As the eval playbook's step 7 asks, it reads every output of each case that decides the result, the targets and any case that got worse, and notes in the report where it disagrees with the judge. It never changes a grade. A disagreement means that the rubric is unclear, and the rubric is then fixed in a case PR.

## 7. Runs and the pass mark (D155)

### 7.1 How many runs

Each case runs 5 times with each version. So a model's randomness shows as a pass count, such as "3 of 5", and not as one lucky or unlucky run (hillclimb playbook: "median of N, not a single run"). A run that is void, because the brief did not arrive unchanged, the CLI failed, or the usage limit stopped it, runs again, at most twice, and does not count.

### 7.2 What passes

For each case, the exam compares how many runs the base passed with how many the PR's head passed.

- **Not worse.** A case passes when the head passes at most one run fewer than the base, out of 5. When the head passes two or more fewer, the case runs 5 more times with each version, and it fails only if the head then passes three or more fewer of the 10.
- **A target.** A PR that fixes a case names it, for example `Fixes case: dv-mock-notes`. The case's trap must be live on `main` (section 4.5). The case passes when the head passes at least 4 of 5 runs and more than the base. When the head passes 3 of 5, or 4 or 5 of 5 but no more than the base, the case runs 5 more times with each version, and passes when the head passes at least 8 of 10 and more than the base. Otherwise it fails.
- **The exam passes** when every case it ran passes. The report lists every must criterion that failed in any run, for cases that pass too.

What these rules get wrong, worked out exactly for one case:

| Situation | Chance |
| --- | --- |
| Both versions pass 8 runs in 10 on average, and the case fails anyway | 4.5% |
| Both pass 9 in 10, and the case fails anyway | 1.6% |
| The head drops from 8 in 10 to 4 in 10, and the case fails | 60% |
| The head drops from 8 in 10 to 6 in 10, and the case fails | 27% |
| A target that the change does not help (5 in 10 both), and it passes | 17% |
| A target that the change takes from 5 in 10 to 9 in 10, and it passes | 95% |

So a one-role exam of two cases fails a harmless change about 1 time in 10, and an exam of all twelve cases about 4 times in 10. A failed exam is not run again on the same head to fish for a pass: the head must change, or Troy accepts the failure in chat, and the PR's exam section records "failed, accepted by Troy" with the reason (section 9.3). Ten runs per version halve the false failures and catch three drops in four instead of three in five, at twice the cost (D155, option B).

### 7.3 When it runs

- **On every PR that changes the instruction set** (section 9.1), before it merges.
- **The base's runs** are made when a PR first needs them, and reused while they stay valid (section 8.2). After a merge that changes the instruction set, the next PR measures the new `main`.
- **When a case is added or changed,** by `prove` (section 4.5).
- **When the CLI or a model changes.** The base's runs go stale, so the next exam measures the base again.
- **On request,** for a hillclimb (section 8.3).

## 8. Old against new (D156)

### 8.1 The exam of a PR

The old version is the PR's base, the merge base with `origin/main`. The new version is the PR's head. Both run on the same case projects, the same CLI, the same models, and the same effort, and their runs alternate, so that the time of day and any change in the service hit both. The PR holds one instruction change, as R01's one commit already asks. The hillclimb playbook's "never stack untested changes" means that two unrelated changes to one role go in two PRs.

### 8.2 Reusing the base's runs

The base's runs of a case are reused, and not run again, when all of these match: the case's version, the hash of the base's instruction set (section 9.1), the CLI version, the model IDs that the runs reported in `modelUsage`, and the effort; and the runs are at most 14 days old. Otherwise the base runs again. Its runs then serve every PR on that base. When an exam needs 5 more base runs (section 7.2), it adds them to the reused ones.

### 8.3 A hillclimb

To improve a role, for example to fix troy-pstack#63's mock notes or to try one of F17's principle cards, a session runs the hillclimb playbook with the exam as its frozen harness:

1. **Metric and stop.** The metric is the target case's pass count. The stop rule is the target rule of section 7.2 at 10 runs: at least 8 of 10 and more than the base, with the role's other cases as the regression gate.
2. **The decision log.** `troy_exam.py log` keeps `decision.tsv` in the work root, outside the tree, with one row per attempt: id, hypothesis, change, before, after, delta, gate, verdict (kept or reverted), and note.
3. **One change per attempt.** Each hypothesis names a mechanism, such as "a fixed sentence, because the notes drifted when the Developer wrote its own". It runs as a commit on a scratch branch, measured against the last kept commit with `troy_exam.py run --base <kept> --head <attempt>`. It is kept only when the target moves past the noise of section 7.2 and the gate holds, and is otherwise reverted in full.
4. **The PR.** The kept commits become one instruction change, and the PR's own exam against `origin/main` is the final check.

## 9. Which changes must pass, and the PR (D157)

### 9.1 The instruction set

These files make up a role's instructions. A PR that changes any of them must carry the exam's result:

| Part | Files |
| --- | --- |
| The agent files | `agents/troy-*.md` |
| The common rules | `troy-mode/roles/common.md` |
| The briefs | `troy-mode/flow/troyflow/brief.py` and the modules of `troyflow` that it imports, such as `summary.py`, `checksteps.py`, and `rulebrief.py`, and later `mocknotes.py` (troy-pstack#63) |
| The templates that roles fill | `troy-mode/templates/**` |
| The skills that roles read | Each `skills/<name>/` folder that an agent file or `common.md` names, such as `technical-writing` and `benchmark-checklist`, and F17's principle cards once named |
| The entry skill's role sections | The sections "Running a role" (with "The report") and "The summary for Troy" of `skills/troy-mode/SKILL.md`, which say what Input a role gets |
| The exam itself | `troy-mode/exam/cases/**` and `troy-mode/exam/troyexam/**`, the frozen harness |

The exam's own code holds this list in one place, and both the runner and the CI check read it. The instruction hash is a SHA-256 over the contents of these files, of the two SKILL.md sections, and of the list, in a fixed order.

### 9.2 Affected cases

The set is wide, so the exam first works out which cases a PR affects, without any model call. `troy_exam.py affected --base <ref> --head <ref>` builds each case's project, renders its brief with each version's engine, and compares what the role would get: the brief, the agent file, and the files the role reads from the plugin. A case whose inputs are the same in both versions is not affected and needs no run. A pure refactor of `brief.py` then costs nothing. A change to the cases or to the harness affects the cases it changes, which `prove` runs again, and a harness change proves every case's anchors again (section 4.5).

A change to the entry skill's role sections cannot change a case's brief, because the case's Input is a fixed file. Such a PR also updates every case's `input.md` that the new section would write differently, and those cases then run. If no `input.md` changes, the exam records that no case is affected.

### 9.3 The PR's exam section

`troy_exam.py block <exam ID>` prints the section that goes into the PR description:

```text
## Role exam

Result: passed
Instructions: 3f9c2a1b7e04
Cases: 2 run, 10 not affected
Runs: 20, 10 of them reused from the base; $14.20; 1 h 05 min

| Case | Role | Base | Head | Result |
| --- | --- | --- | --- | --- |
| dv-mock-notes | Developer | 2 of 5 | 5 of 5 | fixed |
| dv-impl-notes | Developer | 4 of 5 | 5 of 5 | not worse |

Report: D:\Troy\troy-mode-work\results\2026-11-20-1\report.md
```

- `Result` is `passed`, `failed`, `failed, accepted by Troy on <date>: <reason>`, or `no case affected`.
- `Instructions` is the first 12 characters of the head's instruction hash.
- The report stays on Troy's PC, with every run's criteria, the judge's verdicts, the label key, the transcripts, and the session's notes from section 6.3. The section names its path. No path may hold a word that R19's strict mode refuses, which is why the work root is not the session's scratchpad (section 11.1).

### 9.4 The CI check

`troy-mode/dev/check_exam.py` runs in troy-pstack's CI on every PR, as a step of `troy-docs.yml`, which runs on every PR once F19 has dropped its path filter (F19 design 5.4). The step reads the PR's description from the event and checks:

1. When the PR changes no file of the instruction set, it passes.
2. Otherwise the description must hold a "Role exam" section whose `Instructions` equals the head's hash and whose `Result` is `passed`, `no case affected`, or `failed, accepted by Troy ...`.

The workflow also runs on the `edited` event, so that pasting the section after a run starts the check again. A new push that changes the instruction set changes the hash, so the old section no longer matches and the exam runs again. The check cannot prove that the runs happened. It keeps a session from forgetting the exam or from merging after a later change, and the report on Troy's PC is the record of the runs.

## 10. Cost, time, and the budget (D158)

### 10.1 Estimates

At the list prices of the pilot report, from section 2.2's per-run costs, with the role runs of the version that needs them and one judge pass per case. The main session that starts each role costs about $0.003 per run (probe A2). Time assumes two runs at a time.

| Exam | Role runs | Cost | Time |
| --- | --- | --- | --- |
| One Developer case, head only (base reused) | 5 | $2 to $3 | 10 min |
| One Interface Designer case, head only | 5 | $18 to $28 | 30 min |
| A one-role change, base reused: two cases | 10 | $3 to $55, by role | 15 min to 1 h |
| A one-role change, base measured too | 20 | $6 to $105, by role | 30 min to 2 h |
| A change to `common.md`, base measured too: all twelve cases | 120 | $250 to $400 | 8 to 10 h |
| The build's trial (section 14.3) | about 70 | $150 to $250 | 4 to 6 h |

A run may stop at a 5-hour usage limit. Every run's result is saved as it ends, and `troy_exam.py resume` goes on from there.

### 10.2 The budget

- **Before it starts,** the exam estimates its cost from each case's recorded runs: the median cost times the planned runs, plus the judge passes.
- **Up to $60** at list prices, the exam starts without asking.
- **Above $60,** the session shows Troy the estimate, the cases, and the time, and starts only on Troy's yes.
- **While it runs,** the exam starts no new run once its spending reaches 1.5 times the estimate, and it reports what is left. Each run has `--max-budget-usd` at three times its role's 90th-percentile cost, for example $2.50 for the Developer and $35 for the Interface Designer, and a time limit, `run.minutes`.
- **At most two runs at a time,** so that an exam uses Troy's allowance slowly and leaves room for Troy's own sessions. Troy can raise it with `--jobs`.
- **The trial's budget** is a cap of $300, which Troy approves with this design (D158).

## 11. Where it lives and how it runs the CLI (D159)

### 11.1 Files

```text
troy-mode/exam/
  troy_exam.py                the command line; standard library only, Python 3.11 or newer, like troy_flow.py
  troyexam/                   the engine: cases, projects, runs, checks, judge, compare, report, the instruction set
    checks/                   the universal checks and the case checks of section 4.3
  cases/<case ID>/            case.toml, rubric.md, input.md, start.patch, mutants/, anchors/
  tests/                      unit tests with a stand-in CLI; they run in CI
troy-mode/dev/check_exam.py   the CI check of section 9.4, with its tests in troy-mode/dev/tests/
```

The work root, outside the repository, is `D:\Troy\troy-mode-work` unless `TROY_EXAM_ROOT` names another folder:

```text
<work root>/
  mirrors/<repository>.git    bare mirrors of the start repositories, fetched when a case needs a newer commit
  envs/<repository>-<lock>/   the environments of section 4.2
  runs/<six letters>/         one run's project, origin, and plugin copy, deleted after its results are saved
  results/<exam ID>/          report.md, summary.json, the key, the judge's folders, and each run's diff, report, criteria, and transcripts
  cases/<case ID>.tsv         each case's runs, which section 8.2 reuses
  climb/<name>/decision.tsv   hillclimb logs (section 8.3)
```

The work root is not the session's scratchpad, whose path holds a word that R19's strict mode refuses, and the report's path goes into PR text. The cases are English only: Claude reads them, as it reads the role files (F04 design D35).

### 11.2 Commands

| Command | What it does |
| --- | --- |
| `troy_exam.py affected --base <ref> [--head <ref>]` | Lists the cases a change affects (section 9.2). No model call. |
| `troy_exam.py run --base <ref> [--head <ref>] [--fixes <case>]... [--jobs <n>] [--case <case>]...` | The exam of section 8.1: estimate, budget, runs, checks, judge, comparison, report. Exit 0 when it passes, 1 when it fails, 2 when it cannot run. |
| `troy_exam.py prove <case>...` | Proves cases (section 4.5). |
| `troy_exam.py resume <exam ID>` | Goes on after a usage limit, a time-out, or a stop. |
| `troy_exam.py report <exam ID>` and `block <exam ID>` | The report, and the PR's section (section 9.3). |
| `troy_exam.py log <name> ...` | Adds a row to a hillclimb's decision log. |

The session that runs `run` waits for it in the background, as for any long command, and is told when it ends.

### 11.3 One role run, non-interactively

The runner starts one `claude -p` session per run, in the run's project folder, like this:

```text
<CLI> -p "<driver prompt>" --model haiku
  --plugin-dir <run folder>/troy-pstack
  --settings '{"enabledPlugins":{"troy-pstack@troy-pstack":false}}'
  --permission-mode auto --permission-prompts none --allowedTools Agent
  --output-format stream-json --verbose --session-id <new UUID>
  --max-budget-usd <cap>  < /dev/null
```

- **The CLI** is `TROY_EXAM_CLI`, or else the newest `claude-code\<version>\<hash>\claude.exe` under `%LOCALAPPDATA%\Claude-Data\`. Its version goes into every result.
- **The environment** drops the variables that tie a child to its parent session (`CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SESSION_ID`, and the others troy-pstack's trials drop), and sets `CLAUDE_CODE_GIT_BASH_PATH`, `TROY_MODE_PYTHON`, `TROY_MODE_ENV_PREFIX`, `PYTHONPATH`, `MAMBA_ROOT_PREFIX`, `UV_CACHE_DIR` in the work root, `MSYS_NO_PATHCONV=1`, and a PATH that starts with the `gh` stand-in.
- **The driver prompt** tells the haiku main session to call the Agent tool once, with `subagent_type` `troy-pstack:troy-<role>`, the case's `model` and `effort`, `run_in_background` false, and as its prompt the brief between two marker lines, copied exactly, and then to reply with the role's report unchanged (probe A2). The entry skill passes `model` and `effort` the same way when a project sets them (F04 design D32). The pilot set none, so its roles ran at the session's effort, which the transcripts do not record. The cases use `high` unless a case says otherwise, and every result records the effort.
- **The installed plugin** is off for that session only, so the two plugins never run together (F19 design D194), and Troy's settings do not change.
- **Permissions** are auto mode, as in Troy's sessions, and nothing can wait for a prompt.
- **Afterwards** the runner reads the `result` event for the cost per model and the exit, and the role's transcript and `.meta.json` under `~/.claude/projects/<folder key>/<session ID>/subagents/`, found by the session ID, never by a search across projects. The role's report is the `SubagentHandback` call's message, or else its last message. It copies what it needs into the results and deletes the run's folder and the `~/.claude/projects/` folder that the run made. If a permission refuses that delete, the report lists the folders left.

### 11.4 The judge's run

```text
<CLI> -p "<judge prompt>" --model opus --effort high --tools Read,Glob,Grep
  --settings '{"enabledPlugins":{"troy-pstack@troy-pstack":false}}'
  --json-schema <schema> --output-format json --max-budget-usd <cap>  < /dev/null
```

It runs in the judge's folder of section 6.2, with no `--plugin-dir`. The verdict is `structured_output` (probe D).

### 11.5 What can go wrong

| Event | What the runner does |
| --- | --- |
| The role's first message is not the brief | The run is void and runs again, then with the main session on sonnet |
| The session exits with an error, or with no `result` event | The run is void and runs again, at most twice |
| "You've hit your limit" | The exam pauses with its results saved; `resume` goes on later |
| `error_max_budget_usd` | The run counts as failed, and the report says that it hit its cap |
| The time limit passes | The runner ends the session's process tree, the run counts as failed, and the report says so |
| A process with the run's folder in its command line is still running after the session exits | The runner ends it, and U5 fails for that run |
| The judge misgrades an anchor | Section 6.2: one more pass, then "rubric unclear" |

## 12. Changes to earlier features

| Feature | Change |
| --- | --- |
| F04 Role definitions | None to the roles. A change to their files from now on passes the exam (section 9.1). |
| F07 Entry skill | None. The exam calls `brief`, `snapshot`, and `check-run` as they are. |
| F10 Docs | The guide's section on work on troy-mode itself (guide section 9) says when the exam runs, how to start it, the budget, and what goes in the PR. |
| troy-pstack's CI | `troy-docs.yml` gains the step of section 9.4 and the `edited` event. The tests job runs the exam's unit tests too. |
| F19 Rename | F16 uses today's names. If F19's build merges first, F16's build uses `tstack`, the folder name `tstack` for the copies, and `tstack:troy-<role>`, as F19's design says. |

## 13. F17, F18, and the first customers

**F17** adds a pstack skill to a role's instructions only when the pilot showed the same mistake twice. The exam turns that into a test: the mistake becomes a case first, by the rule of 5.1, and is proved live on `main`. The skill's PR names that case as its target, and passes when the case passes the target rule and no other case of the role gets worse. A skill whose target stays at the base's level is not added.

**F18** turns Troy's approvals of design and test plan PRs into spot checks once F12 and F16 give evidence. The evidence F16 gives is each case's pass count on each `main`, in `cases/<case ID>.tsv`, so F18's design can cite, for example, "the Interface Designer's cases pass 5 of 5 on main". F18 decides how much evidence is enough.

**The first customers** are the pilot's issues whose fixes change role instructions:

| Issue | What it changes for roles | Cases it runs |
| --- | --- | --- |
| troy-pstack#63, fixed mock-note sentences | The DV1, DV2, and CR1 briefs and the Developer's and the Code Reviewer's agent files | dv-mock-notes and dv-impl-notes as targets, cr-mock-review and cr-test-review |
| troy-pstack#75, security review once per version | The Code Reviewer's agent file | cr-mock-review and cr-test-review, which must not get worse |
| troy-pstack#51, code examples in designs | If its fix is in the Interface Designer's instructions | if-example-format as the target, if-error-rules, ar-design-review |
| troy-pstack#49, background runs | Its fix, F05 design D231, is in the hooks, the engine, and the entry skill's section "Running a role", which changes no case's Input. Only its option C, which Troy did not choose, would have changed the five agent files that have Bash, or `common.md` with them. | None under D231's approved answer, B: `affected` finds no case, at no cost. U5 stays a note (D233). |
| troy-pstack#67, notes for later features | If its fix adds the notes to the IF1 and DV2 briefs' Input | The cases whose Input changes |
| troy-pstack#64, Python that reads its program from standard input | No role instruction, but the PR that lands its hook, R23, makes U4 a must (section 4.3, version 1.5), which changes the exam's own code in `troy-mode/exam/troyexam/`, part of the instruction set (section 9.1) | All twelve, on their anchors, as after any change to the harness (section 4.5) |
| troy-pstack issues #46, #47, #48, #52, #65, #66, #68, #73, and #74 | The engine, the hooks, troy-init, or the guide, not role instructions | None |

## 14. How F16 is checked (D160)

### 14.1 Tests

A separate agent writes the tests from this design before the code, as for every troy-pstack feature. They use `unittest` and the standard library, run on Linux and Windows in CI, and never call a model: a stand-in CLI, a small Python script, reads the arguments, writes canned stream-json and transcripts, and edits the project as a role would.

| Group | Cases include |
| --- | --- |
| Cases | Every `case.toml` parses; it names a role and a task of F04; its rubric has 3 to 6 criteria; its checks exist; its anchors and patches exist. |
| Projects | A project built from a small local start repository holds no commit after the start; origin has `HEAD`; `start.patch` applies; `core.hooksPath` is set; the `gh` stand-in answers `pr view` and refuses `pr comment` and `api`. |
| Blinding | No exam word in any path, branch, variable, Input, or stand-in message of a built run; the two versions' role-visible texts differ only by random letters; the judge's folder holds no key, brief, agent file, transcript, model name, or cost; the labels are shuffled. |
| The run | The command line of section 11.3; the driver prompt holds the brief exactly; a mangled brief voids the run; the cost is read per model; the report is found in `SubagentHandback` or the last message; the run's folders are deleted. |
| Checks | U1 to U7 and each case check, on fixtures that pass and fail, including `python -` with a heredoc, `python3 - < /dev/null`, a CRLF file rewritten as LF, and a transcript that never reads `docs/rules.md`. |
| Comparison | Every branch of section 7.2, at 5 and at 10 runs; a void run is not counted; the exact chances of the table in 7.2 from the rule's own code. |
| Reuse | Section 8.2's conditions, each one breaking reuse on its own. |
| Budget | The estimate, the $60 line, the stop at 1.5 times, the per-run cap, the pause at a usage limit, and `resume`. |
| The instruction set | The hash changes with each listed file and with each of the two SKILL.md sections, and not with other SKILL.md sections; `affected` finds no case for a refactor that renders the same briefs. |
| `check_exam.py` | No instruction file: pass. A section with the right hash and `passed`: pass. A stale hash, a missing section, `failed`, or a section in a code block only: fail. |

### 14.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail: the judge's folder holding the key; a label that names its version; a later commit reachable in the case's origin; the brief compared without the agent file; the not-worse rule off by one; the target rule passing at a tie; the estimate counting the role's cost but not the judge's; the budget guard ignoring reused runs; `check_exam.py` accepting a stale hash; the hash leaving out the templates; U4 missing `python3 -`; U3 missing a CRLF-to-LF change; U6 accepting a read after the first change; reuse with a different CLI version; and the `gh` stand-in letting `gh pr comment` through. The counts go in the build PR's description.

### 14.3 Trial

Before the build PR opens, the exam runs for real on Troy's PC, within the $300 cap of section 10.2:

1. **Prove every case** on troy-pstack's `main`: the anchors, and five runs each, which are also the first base runs. The PR lists each case's grade of its anchors and whether its trap is live.
2. **A planted improvement.** A scratch branch, never merged, that adds troy-pstack#63's sentences to the DV1 brief. Its exam with `--fixes dv-mock-notes` must pass that case. If that case's trap is not live on `main`, this step uses a live case of another role with a fix written for it, and the PR says which.
3. **A planted harm.** A scratch branch that replaces DV1's step 2 with "Implement each body as the design describes it." Its exam must fail dv-mock-notes.
4. **A change that affects nothing.** A scratch branch that reorders two functions of `brief.py` with the same output. `affected` must find no case, and the exam must record `no case affected` at no cost.
5. **The check in CI.** The build PR changes the instruction set, since it adds the cases and the harness, so it carries its own exam section from step 1, and CI's new check passes on it.

The build PR's description gives every step's results, the cost, and the time.

### 14.4 Status

| When | F16's status in requirements 7.2 |
| --- | --- |
| The build PR merges after a passing trial | Runs on a sample project: the exam proved its twelve cases on scratch copies of the pilot's states, and told a planted improvement and a planted harm apart. No instruction change has been gated yet. |
| The first PR that changes role instructions passes the exam and merges | Used on a real project: the exam gated a change to troy-pstack's role instructions. |

The status updates are their own PRs.

### 14.5 When it is built

The build starts after F19's build, which waits for this design PR (F19 design D199), so the build uses the new names. The instruction parts of the first customers (section 13), troy-pstack#63 and troy-pstack#75 first, wait for F16's build and become its first gated PRs. The trial's planted improvement uses troy-pstack#63's text on a scratch branch only, and that issue's real PR follows the build. The fixes that change no role instruction, such as troy-pstack#65, do not wait. troy-pstack#64 waits too, since its PR makes U4 a must in the exam's own code (section 13).

### 14.6 What the trial showed (2026-11-17 to 2026-11-19)

The trial ran on Troy's PC with the bundled CLI 2.1.325, two runs at a time, on scratch copies of the pilot's states built from the GitHub mirror of `ZJUCao/recipe-menu`. By the end of step 2 it had cost $259.35 at list prices.

| Step | What happened |
| --- | --- |
| 1. Prove every case | Exam 2026-11-17-2 ran 5 base runs of 10 cases, and 3 void runs, at instruction hash `8ec2f520cf43`, for $229.95. About $51 of that went to runs that the 5-hour usage limit cut off: the exam paused seven times and resumed each time. It found the four faults below. After their fix, exam 2026-11-19-3 proved all twelve cases' anchors at the final hash `e05e600e117d`, for $12.09. Regraded by script with the fixes, the base runs passed: cr-mock-review, ar-design-review, ar-error-review, and te-helper-docs 0 of 5; tm-test-review and te-plan-asserts 4 of 5. Those six traps are live. cr-test-review and tm-plan-expected passed 5 of 5, so their traps are not live on `main`. |
| 2. A planted improvement | Exam 2026-11-19-5 ($11.57) failed: dv-mock-notes stopped as "rubric unclear", with the base at 0 of 5 and the head at 0 of 5. See below. On 2026-11-19 Troy moved steps 2 and 3 to a follow-up PR rather than raise the cap. |
| 3. A planted harm | Not run here. It needs step 2's case fix, so it moved to the follow-up PR with step 2. |
| 4. A change that affects nothing | Exam 2026-11-19-4: `affected` found no case, and the exam recorded `no case affected` at no cost. |
| 5. The check in CI | The build PR carries exam 2026-11-19-3's section, and `check_exam.py` passes on it. |

**What step 1 changed in the build.**

1. **U3 reads line ends as git stores the files.** The case projects store LF files and check them out with `core.autocrlf true`. A role that wrote a file back with LF changed only the working tree, yet U3 failed 16 runs for it. Now a file fails U3 when its diff against the start differs from the same diff with `--ignore-cr-at-eol`.
2. **A last `END` line after the brief no longer voids a run.** The haiku main session copied the driver prompt's `END` marker after the brief in 3 of 8 ar-design-review runs ($7.61).
3. **Three rubrics now grade their anchors right** (each case is version 2):
   - tm-plan-expected's criterion 2 is a note, because the pilot's merged plan still breaks it in another row.
   - dv-impl-notes' criterion 1 covers the whole doc comment of each changed function, and the judge sees `_creation.py` and the start's `_listing.py`. Round 1 did not change the pilot's false sentence about the probes, so the narrower criterion missed it.
   - dv-mock-notes' criterion 1 grades only the trap of section 5.2: a sort, a check, a conversion, or an error stated as a fact of the mock.

**Why step 2 failed.**

1. **dv-mock-notes' criterion 2, a note in a paragraph of its own, fails the pilot's pass anchor too.** That anchor writes "The mock raises ``NotImplementedError``. The implementation …" in about 12 doc comments. The judge let this pass when it graded the anchors alone, in 4 passes. It failed it in both passes that also held the head runs, whose notes stand alone.
2. **The planted improvement conflicts with the case's script check.** It used troy-pstack#63's sentence "The mock keeps the values as given and leaves out the constructor's checks." All five head runs then wrote a `UsageError.__init__` that stores its values. That breaks the Developer's step 2 and the must check `mock_bodies_only_raise`. The sentence fits a class whose constructor the language generates, such as a dataclass. #63's own design has to settle this.

**Where the trial differed from section 14.3.**

1. The Interface Designer's ten base runs were left out to stay within the cap. The Test Manager's plan runs cost about $11 each, against a role median of $2.21, and the Interface Designer's runs would have added about $100. Its two cases were proved on their anchors only.
2. Step 1's runs are at the old hash. The exam section of the build PR is the anchors' proof at the final hash, as section 4.5 asks after a change to the harness.
3. Steps 2 and 3 did not finish within the cap. Troy chose on 2026-11-19 to move them to a follow-up PR, at about $26 to $31, rather than raise the cap to $350. Until it merges, the exam has not yet shown that it tells a planted improvement and a planted harm apart.

**Follow-ups, not fixed here.**

- The follow-up PR: dv-mock-notes version 3, with a pass anchor whose notes stand alone, then steps 2 and 3 again, and this design's record of them. It merges before the first gated PR, and troy-pstack#63's design settles the constructor sentence.
- The exam section shows "0 of 5" in the Base column for a case proved on its anchors only; it should show "-".
- A run cut by a usage limit keeps its cost but not its result.

### 14.7 Steps 2 and 3 again (2026-11-19 to 2026-11-20)

The follow-up PR ran steps 2 and 3 again after the build merged, on the same PC, CLI, and environment as section 14.6.

It first built dv-mock-notes version 3. Its pass anchor is the pilot's round 2 (`3e53e685`), with each of its 12 mock notes that shared a paragraph with the full behavior moved to a paragraph of its own, by script. The rubric is unchanged. Step 2's base is the follow-up's own commit, at instruction hash `8f76d12a5545`.

| Exam | What | Result | Cost |
| --- | --- | --- | --- |
| 2026-11-19-6 | `prove dv-mock-notes --anchors` | Passed: both judge passes graded the anchors right. | $1.02 |
| 2026-11-19-7 | Step 2, with troy-pstack#63's sentences without "The mock keeps the values as given" | Failed: base 1 of 5, head 0 of 5, "not fixed". | $10.18 |
| 2026-11-19-8 | Step 2, with a sentence for a sort added to the same text | Failed: base 1 of 8, head 4 of 7, "not fixed". | $11.02 |
| 2026-11-19-9 | Step 3, with the improved branch as the base and the harm of section 14.3 on top of it, dv-mock-notes only | Passed, "not worse": base 4 of 5, head 3 of 5. | $10.16 |
| 2026-11-19-10 | Step 3 with a stronger harm, in the brief's DV1 text too | Open: base 4 of 5, head 0 of 5 in the first round. The guard stopped the second round, so the engine's "worse" is not the rule's (below). | $10.65 |

The five exams cost $43.03 in all; Troy had approved about $53.

**What step 2 showed.**

1. **troy-pstack#63's sentences without that clause have no sentence for a sort.** Their only constructor note is "The mock leaves out the constructor's checks."
   - Three head runs still wrote that `Arguments` sorts its pairs, with no note.
   - Two made that sentence true with a `__post_init__` that sorts, which fails the must check `mock_bodies_only_raise`.
2. **With "The mock leaves out the constructor's checks and sort." added,** the first five head runs passed 3 of 5, so the target rule of section 7.2 asked for five more runs of each version.
   - The budget guard stopped that second round at 1.5 times the estimate of $5.34, which had counted only the first round's head runs.
   - By then the head had passed 4 of 7 against the base's 1 of 8. The rule needs 8 of 10, which 4 of 7 can no longer reach, so the result "not fixed" would have been the same.
   - Of the three head runs that failed, one left a check in `UsageError`'s class doc comment with no note. One wrote a `UsageError.__init__` that does more than raise.
   - In the third, the judge failed a true sentence: an enum's own `ValueError`, which the mock has. A base run of exam 2026-11-19-7 had the same kind of sentence, and the judge passed it there.
3. **Every judge pass graded both anchors right,** with the head runs in the same pass. Version 3's anchor removed the cause of section 14.6's scale effect.

So the exam measured the planted improvement, 1 of 8 against 4 of 7, and its target rule refused to call it a fix. No planted text that passes 8 of 10 has been written.

**Why step 3 did not run as section 14.3 says.** dv-mock-notes' base on `main` passes 1 of 8. The not-worse rule of section 7.2 passes any head when the base passes 1 of 5 or fewer, so a planted harm cannot make this case fail on `main`. On 2026-11-19 Troy chose to run step 3 with the improved branch of step 2 as the base and a harm on top of it as the head, for dv-mock-notes only.

**What step 3 showed with the harm of section 14.3** (exam 2026-11-19-9).

- **The improved base passed 4 of 5, and the harmed head 3 of 5,** which the not-worse rule passes in the first round.
- **The planted harm barely changed what the role wrote.** The agent file's DV1 step 2 said "Implement each body as the design describes it." But the brief still asks for the mock and gives notes for bodies that only raise, so 3 of 5 head runs still wrote bodies that only raise. Two head runs wrote a `UsageError.__init__` that does more than raise, against one base run.
- **The judge graded both anchors right.**
- Troy had allowed one hand edit for this exam: if the guard stopped the second round, raise the exam's estimate in its `state.json` from $8.92 to $11.33, which moves the guard from $13.38 to $17. The first round settled the case, so no edit was made.

**What step 3 showed with a stronger harm** (exam 2026-11-19-10). Troy chose one more step 3, with a harm that also changes the brief. Its DV1 text says to write the interfaces with their full bodies, with no `NotImplementedError` and no mock note, and the agent file's DV1 step 2 says "Implement each body as the design describes it." The base is again the improved branch; its five runs were reused from exam 2026-11-19-9.

- **First round: base 4 of 5, head 0 of 5.** Every head run implemented the bodies and failed the must check `mock_bodies_only_raise`. The judge also failed criterion 1 in each, for a sort or a check stated as fact.
- **The harmed runs cost more:** about $1.25 each, against about $0.75 for the improved branch's. One was cut by the usage limit and ran again, which lost $0.91.
- **The judge's first pass misgraded the anchors.** It failed the pass anchor on criterion 2, reading the Raises entry "NotImplementedError: Always, in the mock." as a note in the same paragraph as "The implementation never raises for bad data." Its second pass graded both anchors right, so the case counted (section 6.2).
- **The guard stopped the second round before it began.** The not-worse rule sends 4 of 5 against 0 of 5 to a second round. Because the base runs were reused, the estimate was only $5.58, so the guard stopped new runs at $8.37, and the first round had cost $10.65. The engine then recorded "worse", since too few runs counted. That is the guard's verdict, not the rule's. To pass, the head would have to pass at least 2 more of the next 5 runs than the base, and every harmed run has failed a must check.

**Step 3 with the stronger harm is open.** On 2026-11-20 Troy chose to spend no more on the trial, so the case was not resumed: no hand edit was made, and the second round never ran. The first round is strong evidence that the exam catches a real harm: the improved base passed 4 of 5, and every harmed run failed a must check. But the not-worse rule gave no verdict, and the engine's "worse" comes from the guard.

**What the trial shows so far.** The exam proved all twelve cases on their anchors (section 14.6). It measured a planted improvement, but below its target rule's bar. It did not see a planted harm that barely changed what the role wrote, and it saw a stronger harm without a verdict from its rule. So section 14.4's first row is not met: the trial has not yet shown, by the exam's own rules, that the exam tells a better version from a worse one.

**Follow-ups, not fixed here.**

- **An estimate that counts the not-worse rule's second round,** and a target's, including when the base runs are reused, so that the guard does not stop a comparison the rule has asked for. The guard stopped exams 2026-11-19-8 and 2026-11-19-10. With base runs reused, the estimate is even smaller, while a harmed head can cost more than the base. This is a change to the engine, tstack #92.
- **Criterion 1 of dv-mock-notes** could say that a sentence true of the mock as written passes, such as an enum's own `ValueError`. Criterion 2 could say that a Raises entry is not a paragraph of the description. Both are case changes, for the next PR that changes this case. Done in version 1.7 (tstack #93), before troy-pstack#63's exam: dv-mock-notes is version 4, with both sentences in its rubric. `prove` (exam 2026-11-21-2, $5.25) graded both anchors right in both judge passes. Its five runs with `main`'s role instructions passed 2 of 5, so the trap is live. Two of them say that `Meal(value)` raises `ValueError`, and the judge passed that sentence in both.

## 15. How F16 maps to the requirements

| Requirement | Where F16 covers it |
| --- | --- |
| F16 row: trap tasks for each role that runs as a subagent | Sections 3, 4, and 5; D151 narrowed the row from each role |
| F16 row: run in a scratch project | Section 4.2 |
| F16 row: graded blind by a fresh session that did not do the task and cannot tell which version it grades | Sections 6.2 and 11.4 |
| F16 row: a change to a role's instructions passes the exam before it merges | Sections 7.2 and 9 |
| F16 row: cases from the pilot's real mistakes | Sections 2.1 and 5 |
| F16 row: Troy's PC only, not in CI | Sections 9.4 and 11 |
| F16 row and 4.1: the `eval` and `hillclimb` playbooks | Sections 4.5, 6, 7, and 8 |
| F17 row: each addition passes the role exam first | Section 13 |
| F18 row: F16's evidence | Section 13 |
| Section 8: no service beyond GitHub and Anthropic | Sections 4.2 and 6.2 |
| Section 8: no upstream file edited | Section 11.1: every file is new, and `poteto-mode` is only read |
| Section 8: Cost | Section 10 |

## 16. Not in F16

- Cases for the Product Manager, the main session (section 3).
- Running the exam in CI or in the cloud.
- Changing role instructions. The first customers do that in their own PRs (section 13).
- Changing `poteto-mode`, its playbooks, or the `arena` skill.
- Grading by Troy. Troy reads the report and decides only on a failed exam or a budget above $60.
- Cases from projects other than the pilot's, until such a project exists.

## 17. Decisions for Troy

F16 uses D151 to D160. D161 on is kept for F17, and D171 on for F18. Troy accepted every recommended answer on 2026-11-16. D233 comes from tstack issue #49's design, which takes D231 to D240 (F05 design section 15). Troy accepted its recommended answer on 2026-11-21.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D151 | Which roles does the exam cover? | A: the six roles that run as subagents. The Product Manager's cases come with a later design, once a main-session case can run without GitHub. The F16 row changes to "each role that runs as a subagent" (section 3). B: the six roles plus Product Manager cases now, on `ZJUCao/troy-mode-trial`. C: the six roles, with no promise of Product Manager cases. | A. The main session's pilot mistakes are all being fixed in the engine and the hooks, which unit tests check, and a main-session case needs GitHub, Troy's answers in advance, and several turns, at the cost of a feature. B would make one trial repository the place of every exam run, which cannot run two at once. |
| D152 | What is a case? | A: one role task in a project rebuilt from the pilot's history, with the engine's brief, a fixed Input, the universal checks U1 to U7, the case's own checks, a rubric of 3 to 6 criteria, and the pilot's fail and pass outputs as anchors; proved before it counts (section 4). B: as A, but projects written by hand for each case, without the pilot's history. C: as A, without anchors or proof. | A. The pilot's own states reproduce its mistakes in their real context, with documents of 60,000 characters and more. A hand-written project would be smaller and would not show them. Anchors prove that the grading tells the pilot's fail from its pass, as hillclimb's "prove its sensitivity" asks. Refined by Troy on 2026-11-18: U1, U2, U3, U6, and U7 are musts; U4 and U5 are notes, reported on every run, until the PRs that land troy-pstack#64's and #49's hooks make them musts (section 4.3). U4 is a must since the PR that landed #64's hook (version 1.5); it counts only the commands that ran. For U5, see D233. |
| D153 | How are cases chosen, and how many per role? | A: by section 5.1's rule, from the mistakes a role made that its instructions can prevent and that repeated, two to four per role, starting with the twelve of section 5.2. A mistake that a hook or the engine fixes gets a universal check instead. B: one case per role. C: every review that requested changes, about 45 cases. | A. Two cases per role cover each role's most frequent mistake and one more, and four keep one role's exam affordable. B leaves a role with one measure. C would cost more than $1,000 per full exam. |
| D154 | How is a run blind? | A: the role runs exactly as in a real session, from two plugin copies with the same folder name in random folders, with no exam word in anything the exam adds, a local origin, and a `gh` stand-in. The judge is a fresh opus session with no plugin, which grades every run of both versions in one pass under shuffled labels, sees outputs only, and is checked by the anchors (section 6). B: as A, but the judge grades each version's runs separately. C: no judge: checks by script only. | A. It follows the eval playbook's blinding rules. One pass on one scale keeps the judge from grading the two versions differently. C cannot judge whether a doc comment is true or a review finding is right, which half the cases need. |
| D155 | How many runs, and what score passes? | A: 5 runs per version per case. A case fails only when the head passes 2 or more fewer of 5 and then 3 or more fewer of 10. A target passes at 4 of 5, or 8 of 10, and more than the base. A failed exam is not rerun on the same head; Troy can accept it in chat, with the reason recorded (section 7). B: 10 runs per version, then 10 more when worse. C: 3 runs per version. | A. It costs half of B. It fails a harmless one-role change about 1 time in 10, and catches a drop from 8 to 4 in 10 three times in five. B halves the false failures and catches three drops in four, at twice the cost. C cannot tell 3 of 3 from luck. |
| D156 | How are old and new instructions compared? | A: the PR's base against its head, on the same cases, CLI, models, and effort, with the runs alternating. The base's runs are reused for 14 days while the case, the instruction hash, the CLI, the models, and the effort match. A hillclimb uses the same exam as its frozen harness, with a decision log, one change per attempt, and keep or revert (section 8). B: as A, but the base always runs again. C: compare the head with fixed scores recorded once. | A. Reuse halves the cost of most exams, and the conditions make a stale base run again. B doubles every exam's cost for little gain. C would compare against a model and CLI that may have changed since. |
| D157 | Which changes must pass, and how does the PR show it? | A: the instruction set of section 9.1: agent files, `common.md`, the brief modules, templates, the skills roles read, the entry skill's two role sections, and the exam's own cases and code. `affected` limits the runs to the cases a change touches. The PR's description carries the exam's section with the instruction hash, and a CI step on every PR checks that the hash matches and the result passed (section 9). B: as A, without the CI step. C: only the agent files and `common.md`. | A. A brief or a template changes what a role does as much as its agent file, and the render step makes a wide set cheap. The CI check stops a merge after a later change without a new exam, which troy-pstack's sessions could otherwise do, since they merge green PRs. C misses troy-pstack#63, whose fix is mostly in the briefs. |
| D158 | What may an exam cost, and what does Troy approve? | A: an exam of up to $60 at list prices starts without asking; above that the session asks Troy with the estimate. It stops at 1.5 times the estimate, each run has a cap, two runs at a time, and a usage limit pauses it. The trial's cap is $300 (section 10). B: up to $20 without asking. C: no limit; the report shows the cost. | A. $60 covers every one-role exam whose base is reused, and the Developer's and the Test Engineer's with the base measured too, so Troy is asked only about the larger ones, such as a change to `common.md` at $250 to $400. B would stop for every opus role's exam. C repeats the pilot, whose cost nobody saw until its report. |
| D159 | Where does the exam live, and how does it run the CLI? | A: `troy-mode/exam/` in troy-pstack, with `troy_exam.py` on the standard library, the cases, and unit tests in CI; results, mirrors, and environments in `D:\Troy\troy-mode-work`. Each run is one `claude -p` session of the bundled CLI, whose haiku main session starts the role as a subagent in the foreground, with the plugin copy loaded by `--plugin-dir`, the installed plugin off by `--settings`, auto mode, `--max-budget-usd`, and a known session ID (section 11). B: as A, but the role runs as the session's agent with `--agent`. C: the cases in a repository of their own. | A. Probes A2 and B show that only a subagent runs under the hooks with its write scope, as a real run does. The cases change with the instructions they test, so they belong in the same PR. B skips the write-scope checks that U2 grades. |
| D160 | How is F16 checked, and when is it built? | A: tests from this design by a separate agent, with a stand-in CLI and no model call; planted bugs; and a trial within $300 that proves all twelve cases on `main`, passes a planted improvement, fails a planted harm, and finds nothing for a no-op change (section 14). Built after F19's build. The instruction changes of troy-pstack#63 and troy-pstack#75 wait for it and become its first gated PRs. Status "Runs on a sample project" after the merge. B: as A, but the trial proves only the Developer's and the Code Reviewer's cases, about $35 to $50, and the others are proved at their first exam. C: tests and planted bugs only; status "Written". | A. An exam must first show that it can tell better from worse, or its passes mean nothing, and the twelve proofs are also the base runs that every later exam reuses. B is cheaper now, but the first exam of an opus role then pays its proof, and an unproved case can mislead that exam. |
| D233 | Does U5, "no process that the run started is still running after the session has exited", become a must with troy-pstack#49's fix, as D152 planned? The fix, F05 design D231, ends a role's leftover commands from the main session, after the role's report. In an exam, the session's exit already ends a role's background commands and their child processes (F05 design section 6.1, probe D). From tstack issue #49. | A: U5 stays a note as it is, and section 4.3 says why. B: U5 becomes a must as it is. C: U5 is defined from the transcript as "no command of the role still ran in the background when it reported", a must with D231's option C, which lets a role end its own commands, and a note otherwise. | A. As defined, U5 can fail only for a process that has left Claude Code's process tree. D231 does not prevent that, and no pilot run showed one, so as a must it would fail runs for a mistake that no instruction or hook addresses, which is why D152 kept U4 and U5 notes until their fixes. A changes no exam code and costs nothing. B and C change `troy-mode/exam/troyexam/`, after which every case's anchors are proved again, $40.00 by the estimate. C would measure the pilot's mistake itself, but a role can act on it only with D231's option C. Approved by Troy on 2026-11-21 with the recommendation ("全按推荐"). |

## 18. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-16 | First draft, with the pilot's data and the probes of section 2.3. |
| 1.0 | 2026-11-16 | Approved by Troy with D151 to D160, every recommended answer. D151 narrows the F16 requirement to the roles that run as subagents (requirements 1.42). |
| 1.1 | 2026-11-18 | D152 refined by Troy ("按推荐"): U1, U2, U3, U6, and U7 are musts; U4 and U5 are notes until their hooks land (section 4.3). |
| 1.2 | 2026-11-19 | Facts from the build and its trial: U3 reads line ends as git stores the files, and a last `END` line after the brief does not void a run (section 4.3); the trial's record (14.6). |
| 1.3 | 2026-11-20 | Steps 2 and 3 of the trial, run again in the follow-up PR, and what they showed (14.7): the exam measured a planted improvement below its target rule's bar and did not see a weak planted harm. It saw a stronger harm in its first round, but the guard stopped the second round, so the rule gave no verdict. Section 14.4's first row is not met. dv-mock-notes is version 3, with a constructed pass anchor. |
| 1.4 | 2026-11-20 | troy-pstack#64 waits for F16: the PR that lands its hook makes U4 a must in the exam's own code, which is part of the instruction set (sections 13 and 14.5). Found while F16 was built. |
| 1.5 | 2026-11-20 | U4 is a must: the PR of troy-pstack#64 lands its hook, R23 (F05 design 8.3), as D152 says. U4 reads a command with the hook's own check and counts only the commands that ran, so a try that a hook refused does not fail it. U5 stays a note until #49's hook (sections 4.3 and 13, and D152). |
| 1.6 | 2026-11-21 | D233, from tstack issue #49, approved by Troy on 2026-11-21 ("全按推荐"): U5 stays a note, since the fix, F05 design D231, ends a role's leftover commands from the main session, and an exam's session exit already ends them. The fix affects no case, and `check-run`'s new `running` problem never shows in an exam (sections 4.3, 13, and 17). |
| 1.7 | 2026-11-21 | dv-mock-notes version 4, from tstack issue #93: its rubric's criterion 1 passes a sentence true of the mock as written, such as an enum's own `ValueError`, and criterion 2 says that a Raises entry is not a paragraph of the description. `prove` graded both anchors right, and the trap is live (14.7). |
