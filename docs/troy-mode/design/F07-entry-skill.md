# F07 design: the entry skill (troy-mode)

| | |
| --- | --- |
| Feature | F07 in [requirements 1.20](../requirements.md#72-feature-list) |
| Version | 1.19 |
| Date | 2026-11-25 |
| Status | Approved by Troy on 2026-11-07, with D57 to D68. Version 1.1 records the facts the trial of section 14.3 settled for part 1. Version 1.2 records Troy's D69 and the details part 2 settled. Version 1.6 adds D201, which Troy approved on 2026-11-18 as tstack issue #46, 1.7 adds D202, approved the same day as issue #47, 1.8 adds D203, approved the same day as issue #52, and 1.9 adds D204, approved the same day as issue #68. Version 1.10 follows F05's D231, which Troy approved on 2026-11-21 as tstack issue #49 (sections 6.2 and 7). Version 1.11 adds D261 to D263 for tstack issue #73, which Troy accepted on 2026-11-16; each takes the recommended answer, approved under Troy's standing yes of 2026-11-22. Version 1.12 adds D264 to D267 for tstack issue #74, accepted the same day, approved the same way. Version 1.13 adds D205 to D207, the design of tstack issue #63, whose rule Troy accepted on 2026-11-16; its choices follow the recommended options under Troy's standing yes of 2026-11-22, and Troy approved its requirement clauses on 2026-11-22 (section 6.4). Version 1.14 notes the changes of F20's design (D268 to D279, approved by Troy on 2026-11-22), which land with F20's build. Version 1.15 adds the security review's check to CR1's brief and CR2's brief, from F04's D280 to D283 for tstack issue #75, approved under Troy's standing yes of 2026-11-22 (section 6.5). Version 1.16 adds D284 to D287 for tstack issue #67, a problem of the F11 pilot: notes for later features live on GitHub and reach those features' briefs; each takes the recommended answer, approved under Troy's standing yes of 2026-11-22 (section 6.6). Version 1.17 records what tstack #75's build settled (section 6.5), and 1.18 what tstack #67's build and its trial settled (sections 6.6 and 14.4). Version 1.19 adds D288, a hillclimb step on the case dv-impl-notes (F16 design 8.3): DV2's text says how to check the doc comments that PR 5 keeps; it takes the recommended answer, approved under Troy's standing yes of 2026-11-22 (section 6.4). |
| Source of truth | This English file. [`F07-entry-skill.zh-CN.md`](F07-entry-skill.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F07 is the command Troy types for all work in a troy-mode project, `/troy-pstack:troy-mode <request>` (requirements 3.1). It delivers one skill and the engine behind it. With them, the main session:

1. routes each request to a flow (section 4);
2. runs the flows: project setup (5.1), the feature loop (5.2), bug fixes (5.3), requirement changes (5.4), work outside the pipeline (5.9), and continuing across sessions (5.10);
3. starts each role with its brief and with the model and effort from `.troy-mode/config.toml` (F04 D32), one writing role at a time;
4. checks after each run that the role changed only files in its write scope (F04 D31);
5. commits, opens PRs, posts reviews, counts review rounds and attempts, escalates (5.7), and merges within the merge rights (R17, R18);
6. keeps the progress file.

The version release flow (5.5) and the rule change flow (5.8) are F08's and F09's. F07 routes those requests to them. Sections 5.6 (when tests run) and 5.7 (escalation) are not requests. They are steps inside the other flows.

F07 lands in two parts (D67). Part 1 holds routing, setup, the feature loop's main path, work outside the pipeline, and continuing. Part 2 adds the feature loop's side PRs (disputed tests, coverage gaps, and new dependencies), bug fixes, and requirement changes.

The facts about Claude Code come from its documentation and from the F04 to F06 trials. Two of them shape this design. Claude cannot call a skill marked `disable-model-invocation: true`, so F07 runs troy-init's engine itself (F06 section 10) and follows a pstack skill by reading its `SKILL.md`. The Agent tool takes a `model` and an `effort` with each call, and in the desktop app a subagent runs in the background and reports when it ends. The trial (section 14.3) checks both. Part 1's trial confirmed them: every Code Reviewer call carried the `effort` that `[roles]` set and no other role got one, writing roles ran in the foreground so the session waited for each, and in `claude -p` the session went on when background reviews ended. The pilot later showed that the desktop app's Agent tool has no way to start a subagent in the foreground: every role runs in the background there (F05 design section 6.1).

## 2. Location

```text
skills/
  troy-mode/
    SKILL.md                  the skill Troy types (sections 4 to 11)
troy-mode/
  flow/
    troy_flow.py              the engine's entry point (section 3)
    troyflow/                 internal modules (the Developer's choice)
    tests/                    unit tests (section 14.1)
```

- The engine uses Python 3.11 or newer and the standard library only, like troy-check (F02 D7). It imports troy-check's config reader, path classes, title parser, and attribution rules, and F05's write scope table, from the plugin's own folders. F07 then judges paths exactly as the hooks and CI do.
- `SKILL.md` sets `disable-model-invocation: true` (requirements section 8). It names the engine as `${CLAUDE_PLUGIN_ROOT}/troy-mode/flow/troy_flow.py` and the Product Manager's instructions as `${CLAUDE_PLUGIN_ROOT}/troy-mode/roles/product-manager.md`, which it reads first (F04 section 9.2). It runs the engines, git, and gh through the Bash tool: in the trial, a session that picked PowerShell needed a permission that `claude -p` does not grant, and never ran `status`.
- F07 talks to Troy in Troy's language. Files, PRs, and comments are in English, and documents get Chinese mirrors (R12).

## 3. The engine (D57)

### 3.1 Commands

```text
python troy_flow.py status     [--write-progress] [--waiting <text>] [--note <text>] [common options]
python troy_flow.py brief      --task <task ID> --item <feature or bug ID> [--title <PR title>]
                               [--round <n>] [--input-file <path>] [common options]
python troy_flow.py snapshot   --role <role> [common options]
python troy_flow.py check-run  --run <run ID> [--allow-dependency <path>]... [common options]
python troy_flow.py approve    --doc <path> [--date <YYYY-MM-DD>] [common options]
python troy_flow.py check-text --file <path> [common options]
python troy_flow.py check-skips --report <troy-check JSON> --junit <path>... [common options]
python troy_flow.py series     [common options]
python troy_flow.py wait-checks --pr <number> --sha <commit> [--timeout <s>] [--interval <s>]
                               [--settle <s>] [common options]
python troy_flow.py costs      (--item <ID> | --tag <vX.Y.Z>) [--until <time>]
                               [--transcripts <folder>]... [common options]
python troy_flow.py note       --for <feature ID> --from <source> --file <path> [common options]

common options: [--repo <path>] [--json]
```

| Command | What it does |
| --- | --- |
| `status` | Reads the project's state (section 5) and prints it with the next action. `--write-progress` rewrites the progress file from it. It counts each open PR's attempts from F07's comments and from the CI runs of the PR's pushed commits (section 8.5, D261). |
| `brief` | Prints the brief for one role run (section 6.1) and the Agent tool's parameters: `subagent_type`, `model`, and `effort`. `--title` names a PR whose title the state cannot give: a bug PR, a side PR (section 8.7), or the redo of a stage (section 11.2). |
| `snapshot` | Records the state before a run (section 7) and prints its run ID. |
| `check-run` | Compares the state after the run with the snapshot (section 7). Prints the paths to stage, the problems, and how to undo each one. |
| `approve` | Records Troy's approval in a document's header and in its mirror's (section 8.6). For the architecture, it also accepts the ADRs that the architecture lists (D202). |
| `check-text` | Checks a PR comment with troy-check's attribution rules, in the project's `[attribution] mode` (R19). |
| `check-skips` | Reads `troy-check code`'s JSON report and the JUnit files, and says whether the only failures are tests skipped on this platform (section 8.6, D69). |
| `series` | Plans the series lock after an accepted dependency change: the commands that compile and install it, each member's tests, and the members whose lock is now stale (section 8.7, D66). The skill runs the commands. |
| `wait-checks` | Waits until every CI check of the PR's head commit `--sha` has registered and finished, and reports whether all passed (section 8.6, D204). It reads GitHub only. |
| `costs` | Reads Claude Code's transcripts on Troy's PC and gives a feature's or a version's role runs, per role with the model, and their token cost at list prices, with the section for the PR description (section 8.8, D264 to D267). |
| `note` | Renders a note for a later feature as a comment for a progress issue, and gives the issue and the `gh issue comment` command that the skill runs (section 6.6, D284 to D287). |

- The engine reads git, and GitHub through read-only `gh` calls. `costs` also reads Claude Code's transcripts, and never writes there. It writes only the progress file, the header fields that `approve` changes, and its records in `<git dir>/troy-mode/flow/`. It never commits, pushes, or writes to GitHub. The skill does that (F04 D29).
- The exit codes are those of F06 design 3.3: 0 for done, 1 when a problem stops the step and the report says which, and 2 when the engine could not run.

### 3.2 Model and effort (F04 D32)

```toml
[roles.developer]
model = "opus"
effort = "high"

[roles.code-reviewer]
effort = "medium"

[flow]
troy_approves_first = 3
```

- `[roles.<role>]` takes `model`, an alias that the Agent tool accepts, such as `opus` or `sonnet`, and `effort`: `low`, `medium`, `high`, `xhigh`, or `max`. `<role>` is `architect`, `interface-designer`, `test-manager`, `developer`, `test-engineer`, or `code-reviewer`. The Product Manager uses the main session's model (Q3).
- `brief` reads the config at `HEAD`, as F05's hooks do, so an uncommitted edit changes nothing.
- The skill passes `model` and `effort` with the Agent call only when the project sets them. A model passed with the call takes priority over the agent's frontmatter (F04 D32). Without one, the role runs on Q3's default.
- `[flow] troy_approves_first` belongs to D62.
- troy-check rejects unknown config keys, so its config reader learns both tables (section 12). An unknown role, an unknown key, or a wrong effort value still stops troy-check with exit code 2.

## 4. Routing a request

At every start, F07 reads `product-manager.md`, runs `status`, and then picks the flow.

| Request, for example | Flow | Where |
| --- | --- | --- |
| Any request in a folder with no `.troy-mode/`, or "start a project ..." | Project setup | Section 10 |
| "next feature", "F04", "F04 to F06", "Start v0.1", "the rest of v0.1" | Feature loop | Section 8 |
| "bug: ...", "fix #12" | Bug fix | Section 11.1 |
| "change: ...", "the export should also ..." | Requirement change | Section 11.2 |
| "why ...", "how does ...", "try ..." | Work outside the pipeline | Section 11.3 |
| "continue", "status", or nothing | Continue | Section 11.4 |
| "upgrade troy-mode" | troy-init's upgrade (F06 section 6) | Section 10 |
| "release v0.1" | Version release (5.5) | F08 design |
| "add a rule ..." | Rule change (5.8) | F09 design |

- In a folder with no `.troy-mode/`, F07 answers a question but changes nothing. For any other request, it asks Troy once whether to make the folder a troy-mode project.
- When a request fits two flows, or none, F07 asks Troy one question with a recommended answer.
- **How far a request goes (D63, D203).** One feature, one bug, or one change, unless the request names more, such as "F04 to F06". A feature-loop request that names a version, such as "Start v0.1", "v0.1", or "the rest of v0.1", reaches every feature of that version not yet accepted, in the order (D203). Troy's approvals still stop the loop where they do today, and after Troy approves, F07 goes on within the same reach. The reach ends before the version's release, which is its own request ("release v0.1"). Then F07 reports and stops.
- **One PR at a time.** F07 works on one PR at a time in a checkout. A new request waits until that PR merges, unless Troy says to pause it. A paused PR's branch is rebased on `origin/main` when it resumes.
- **The go-ahead.** In troy-mode, the approvals of requirements 3.3 are the go-ahead that Troy's global instructions ask for before code, as F04's common rule 4 says for the roles. F07 does not ask for it again.
- **Reports.** F07 reports each stage to Troy in the shape of Prototype B.

## 5. State (D58)

### 5.1 Where it is read from

| What | Read from |
| --- | --- |
| Setup and the language pack | `.troy-mode/install.toml` on `origin/main` |
| Whether Troy approved the requirements and the architecture | Their `version` on `origin/main`: 1.0 or higher (F01 design section 4) |
| Features, dependencies, order, and versions | `docs/requirements.md` on `origin/main`: the features table, the "Topological order" line, and the version plan |
| The stages a feature has merged | Commit subjects on `origin/main`, such as `[F04 3/6 mock] ...`. R01 makes each subject equal its PR title (F03 D17), and rebase, squash, and merge commits all keep it. |
| Open PRs and their stage | `gh pr list` titles and branches |
| Review rounds, attempts, and what waits on Troy | F07's own comments on each open PR (section 8.4). Attempts also come from the CI runs of the PR's pushed commits (section 8.5, D261). |
| Attempts before a PR exists, and `status --note` lines | The progress file only |
| Notes for later features | troy-mode's `Note for <ID>` comments on the progress issues (section 6.6) |

- `status` checks the order line against the dependency columns: every dependency must come earlier. A mismatch stops the feature loop and names the features. Fixing it is a requirement change.
- The next feature is the first in the order with no `accept` commit on `origin/main`.
- Subjects count in history order. When a stage merges again, as the redo of section 11.2 does, the feature's later stages that merged before it no longer count. A feature's current stage is its lowest stage not merged, and a mock that section 11.2 skips counts as merged.
- Bugs come from the subjects and the open PRs too: `[B12 A/B test]` merged means PR B comes next, and `[B12 B/B fix]` merged means the bug is fixed (section 11.1).
- When more than one troy-mode PR is open, a PR that is not a feature stage, such as a side PR, a bug PR, or a `[docs]` PR, comes before the stage PR it interrupts (section 8.7). Otherwise the lowest number comes first.
- `status` also compares the project's troy-check, in `.troy-mode/checks/`, with the plugin's. When the project's copy is older, it says that troy-init's upgrade brings it up to date. `[roles]`, `[flow]`, and `troy-check code --worktree` need the new copy (section 12).

### 5.2 The progress file

- `.troy-mode/progress.md` stays local, git-ignored (Q8), and in English (F01 D4), in the shape of F01's `progress` template.
- F07 rewrites it with `status --write-progress` after every step: each role run, commit, push, review, merge, and escalation.
- When it is missing or older than the state of section 5.1, `status` builds it again from that state. A new session then continues even in a new clone, or in a worktree that the desktop app just made, where the file never existed (5.10).
- Losing the file loses only the attempts counted before their PR existed, and the notes. `status` says when it rebuilt the file.

## 6. Running a role

### 6.1 The brief

`brief` fills F04's brief fields (F04 design 5.1):

| Field | Filled from |
| --- | --- |
| Task | The task ID and one sentence, for example "DV1, write the mock of F04's interfaces". |
| Item | The feature or bug ID and the PR title. |
| Read first | By task: `docs/rules.md`, the feature's requirement row, the architecture, the feature's design and test plan once they exist, and the designs of the features it depends on. |
| Input | The file given with `--input-file`: review findings, an answer, failing checks, or a decision of Troy's. Otherwise None. |
| Round | The review round, or None. |
| Checks to run | The language pack's steps in the project's environment (F03 sections 8.3 and 9.4). For authors of code and tests, also `troy-check code --worktree` with the PR's title (D60). |

- IF1's Task also says that section 4 is the Architect's and asks for "Not reviewed yet." in it. In the trial, IF1 left section 4's template markers for the Architect, so `troy-check pr` failed R20 on the design until AR2 filled the section in.
- For the first mock, DV1's checks start with the setup steps that need code: `uv pip install -e . --no-deps` for Python and `cmake --preset coverage` for C/C++ (F06 design 5.4).
- At PR 3 and PR 5, the Task of DV1, DV2, and CR1 adds the fixed mock-note text of section 6.4 (tstack #63).
- Every CR1 Task says whether to run `/security-review`, from the check of section 6.5 (tstack #75). CR2's brief is for the review branch of a release (F08 design 5.9).
- The Input of IF1, IF2, and DV2 adds the notes that earlier work left for the feature (section 6.6, tstack #67).
- Commands run through `mamba run -n <environment>`, or `mamba run -p <folder>` when `TROY_MODE_ENV_PREFIX` is set. Trials set it, so they leave no named environment behind. mamba is found the way troy-init finds it when no `--mamba` is given: on the PATH, then in `$MAMBA_EXE` (F06 design 5.4). `brief` has no `--mamba` option.
- A revision is a fresh run of the same task, or of IF2 for a design, with the findings in Input and the next round (F04 D33).

### 6.2 One writing role at a time

1. `snapshot --role <role>`. It refuses when the working tree has changes that git does not ignore, and while a role's work still runs (section 7, problem 5). F07 commits after every writing run, so the tree is clean before the next one.
2. The Agent call: `subagent_type` and the brief from `brief`, plus `model` and `effort` when it gives them.
3. F07 waits for the role's report and does nothing else in the checkout meanwhile, because F05 blames every change during the run on the role (F05 section 6). Roles that only read may run together, such as the Test Manager's and the Code Reviewer's reviews of one test PR (F04 section 9.2). One snapshot covers them, and nothing may change. A notice that the role "is waiting on its own background work" changes nothing here: the report is final, and step 4 ends that work.
4. `check-run --run <run ID>` (section 7).

### 6.3 Acting on the report

| Result | What F07 does |
| --- | --- |
| `done` | `check-run`, commit, local checks, push, then the stage's review (section 8.2). |
| `failed` | Counts one attempt (section 8.5). Runs the author again with the failing checks in Input, or escalates after the third. |
| `approved` | Starts the next reviewer, or goes on to the merge. |
| `changes-requested` | Runs the author again with the findings, as the next round, or escalates after round 3 (section 8.3). |
| `needs-answer` | Starts the role that the question names, with the question as Input, then runs the asker again with the answer. A question for Troy goes to Troy. |
| `escalate` | Escalates (section 9). |
| No report in F04's format | Runs the role once more. A second time, F07 escalates. |

When a role asks for `how`, `why`, or `interrogate`, F07 follows that skill's `SKILL.md` and puts the result in the next brief's Input (F04 common rule 9).

### 6.4 The mock notes (tstack #63, D205 to D207)

In seven mock PRs of the pilot (ZJUCao/recipe-menu #36, #42, #55, #57, #67, #81, and #88), the Code Reviewer asked for changes because a mock note pointed at nothing or said the opposite of the mock. "The mock leaves these checks out." stood before the Raises section it meant, or a stub's doc comment said that it raises or sorts where the mock does not. Troy accepted the rule on 2026-11-16 (ZJUCao/recipe-menu#94, AR6 option A): the briefs give fixed sentences, and no R row is added, since no architecture, tool, troy-check check, or workflow step can judge what a note points at (tstack #63 gives the reasons).

**Where the text goes.** `troyflow/mocknotes.py` holds the text, chosen by `[lang] name` in the config at `HEAD`, as `summary.py` holds the summary sentence. `brief` adds it to the Task line, after the task's own sentence, only for a feature's stage PR, the redo of a stage in rework included (section 11.2). A side PR, a bug, a version, and a rule get none.

| Task | Stage | Text added |
| --- | --- | --- |
| DV1 | PR 3 | The rule for the notes, with the pack's sentences |
| CR1 | PR 3 | The check of the notes, with the pack's sentences |
| DV2 | PR 5 | Delete the notes |
| CR1 | PR 5 | Check that none is left |

CR1 at PR 4 and every other task get no text.

**The sentences** (D205):

| Where | Python | C/C++ |
| --- | --- | --- |
| A function or method whose body only raises | `The mock raises ``NotImplementedError``.` | `The mock throws ``troy::NotImplemented``.` |
| The doc comment of a class that writes its own constructor | `The mock's constructor raises ``NotImplementedError``.` | `The mock's constructor throws ``troy::NotImplemented``.` |
| A class whose constructor the language generates, such as a dataclass, and checks its arguments in the design | `The mock leaves out the constructor's checks.` | None: a constructor that C++ generates cannot check |
| The same, when that constructor also changes them, for example by sorting | `The mock keeps the values as given and leaves out the constructor's checks.` | None |

**DV1's text for Python:**

> Where the mock does less than a doc comment says, add the mock's note as a paragraph of its own, after the description and before Args, Attributes, Returns, and Raises. Use these sentences word for word: `The mock raises ``NotImplementedError``.` for a function or method whose body only raises; `The mock's constructor raises ``NotImplementedError``.` in the doc comment of a class that writes its own constructor, besides the constructor's own note; `The mock leaves out the constructor's checks.` for a class whose constructor Python generates, such as a dataclass's, when the design has that constructor check its arguments, or `The mock keeps the values as given and leaves out the constructor's checks.` when it also changes them, for example by sorting; and, for a body that the design itself gives the mock, one sentence that says all it does, such as `The mock reads no file, writes nothing, raises nothing, and gives 0.` Every other body only raises, a constructor that the class writes too, and a generated constructor gets no `__post_init__`. A note never points elsewhere: no "these", "this", "above", or "below". The description and the sections describe the implementation as the design gives it, for example "The constructor checks its values, as Raises gives them.", so that PR 5 has only the notes to delete.

**DV1's text for C/C++:**

> Where the mock does less than a doc comment says, add the mock's note as a paragraph of its own, after the description and before Args, Attributes, Returns, and Raises. Use these sentences word for word: `The mock throws ``troy::NotImplemented``.` for a function or method whose body only throws; `The mock's constructor throws ``troy::NotImplemented``.` in the doc comment of a class that writes its own constructor, besides the constructor's own note; and, for a body that the design itself gives the mock, one sentence that says all it does, such as `The mock reads no file, writes nothing, throws nothing, and returns 0.` Every other body only throws, a constructor's too. A note never points elsewhere: no "these", "this", "above", or "below". The description and the sections describe the implementation as the design gives it, for example "The constructor checks its values, as Raises gives them.", so that PR 5 has only the notes to delete.

**CR1's text at PR 3 for Python:**

> Check the mock's notes. Every stub, and every class whose constructor does less in the mock than in the design, has one, as a paragraph of its own after the description. Each is one of these sentences, word for word: `The mock raises ``NotImplementedError``.` for a body that only raises; `The mock's constructor raises ``NotImplementedError``.` for a class that writes its own constructor; `The mock leaves out the constructor's checks.`, or `The mock keeps the values as given and leaves out the constructor's checks.` when the constructor also changes them, for a class whose constructor Python generates; or one sentence that says all that a body given by the design does. No other sentence says what only the mock does.

**CR1's text at PR 3 for C/C++:**

> Check the mock's notes. Every stub, and every class whose constructor does less in the mock than in the design, has one, as a paragraph of its own after the description. Each is one of these sentences, word for word: `The mock throws ``troy::NotImplemented``.` for a body that only throws; `The mock's constructor throws ``troy::NotImplemented``.` for a class that writes its own constructor; or one sentence that says all that a body given by the design does. No other sentence says what only the mock does.

**DV2's text** (D207, D288):

> Delete every paragraph of the feature's doc comments that starts with "The mock". Then check each doc comment of the code you write or change against that code, also the sentences you did not change. Fix each sentence that is not true of that code. What the code does includes what the functions it calls do, in any file. A sentence is not true when it names a call, a file access, or an exception that the code does not make. A full list, claimed with words such as "only", "every", or "besides", is also not true when it leaves out one that the code makes. Change nothing else in those doc comments.

**CR1's text at PR 5** (D207):

> Check that no paragraph of the feature's doc comments starts with "The mock", and that every other change to those doc comments makes them true of the code.

DV2's and CR1's PR 5 texts are the same for both languages.

**The agent files.** The Developer's DV1 gains a step: add the mock notes that the brief gives, word for word. Its step 2 adds that a constructor that the class writes only signals too. Its DV2 gains a step: delete the mock notes as the brief says. The headings stay, so `troy-mode/dev/tests/test_roles.py` still passes. The Code Reviewer's agent file does not change (D206).

**What does not change.** The rules templates, troy-check, F05's hooks, and troy-init. The engine and the agent files run from the plugin folder, so the text reaches each project with the next plugin version, without troy-init's upgrade. recipe-menu's `main` has no mock notes left, since every PR 5 removed them. A feature between PR 3 and PR 5 keeps its old notes: DV2 deletes those that start with "The mock", and CR1 at PR 5 catches any other.

**The exam (F16 design 7.2 and 9).** `brief.py`, the new `mocknotes.py`, and the Developer's agent file are part of the instruction set (F16 design 9.1). `affected` then names dv-mock-notes (DV1), dv-impl-notes (DV2), and cr-mock-review (CR1 at PR 3); cr-test-review reviews a PR 4, so it is not affected (D206). The build PR names `Fixes case: dv-mock-notes`, whose trap is live on `main`: its base passed 2 of 5 in exam 2026-11-21-2. The other two cases must not get worse. No recorded base run carries `main`'s hash, so the base runs again. If the head does not reach the target, the rubric stays as it is: the session reports the numbers and proposes a hillclimb step (F16 design 8.3) with its cost.

**D288's hillclimb step.** In exam 2026-11-22-3, dv-impl-notes passed 0 of 5 runs with #63's text and 0 of 5 without it, so D288 is that step. Only DV2's brief differs, so `affected` names dv-impl-notes alone. Its exam, 2026-11-24-4, with `Fixes case: dv-impl-notes`, passed: the base passed 0 of 10 runs and the head 8 of 10, after the second round that the target rule asks for, at $21.79. Every head run passed criterion 1, and the two that failed broke U7: after the checks, they tried `git add -N src` to count R03's lines with a new file, and F05's hook refused it. No base run did that. Criterion 3, a constructor's sentence that stands after Raises, failed in every run of both versions: D288 does not move a true sentence (section 16).

### 6.5 The security review (tstack #75, F04 D280 to D283)

F04 design 6.8 gives the reasons: in the pilot, the Code Reviewer ran `/security-review` on nearly every code PR and found nothing. For CR1, `brief` now checks the PR's diff for four signs, and the Task says whether to run `/security-review`.

**The diff.** From the merge base of `origin/main` and `HEAD` to `HEAD`, in the checkout that `brief` reads, which is the team's worktree when the feature runs as a team (F20 design 3.11). Only added lines count, and only in source files and dependency files: a test that runs the program in a subprocess adds nothing that the program does. A file's class comes from troy-check's patterns and the `[paths]` table of the config at `HEAD`, as for the write scopes (F02 D9).

**The signs.**

| Sign | Found when |
| --- | --- |
| A dependency | A file of the class `dependencies` changed. In a CMake file, `CMakeLists.txt` or one under `cmake/`, only an added line that names a package counts: `find_package`, `FetchContent_Declare`, `ExternalProject_Add`, `CPMAddPackage`, or `pkg_check_modules`, since a C/C++ project also changes `CMakeLists.txt` to add its own files. |
| A subprocess call | An added line of a source file starts a process. Python: the modules `subprocess` and `pty`, `os.system`, `os.popen`, and the calls `os.exec*`, `os.spawn*`, `os.posix_spawn*`, and `asyncio.create_subprocess_*`. C/C++: `system`, `popen`, `_popen`, the `exec*` calls, `fork`, `vfork`, `posix_spawn`, `CreateProcess*`, `ShellExecute*`, and `WinExec`, and the headers `<spawn.h>` and `boost/process`. |
| Network access | An added line of a source file imports a network module or includes a network header. Python: `socket`, `ssl`, `http`, `urllib`, `urllib3`, `ftplib`, `smtplib`, `poplib`, `imaplib`, `xmlrpc`, `socketserver`, `webbrowser`, `requests`, `httpx`, `aiohttp`, `websockets`, `grpc`, and `paramiko`, and the calls `asyncio.open_connection` and `asyncio.start_server`. C/C++: `<sys/socket.h>`, `<netinet/*>`, `<arpa/inet.h>`, `<netdb.h>`, `<winsock2.h>`, `<ws2tcpip.h>`, `<curl/curl.h>`, `boost/asio`, and `<asio.hpp>`, and the calls `getaddrinfo` and `WSAStartup`. |
| Credential handling | An added line of a source file imports `getpass`, `keyring`, `netrc`, or `secrets` (Python), or holds a name that contains `password`, `passwd`, `passphrase`, `credential`, `secret`, `api_key`, `apikey`, `access_token`, `auth_token`, or `private_key`, in any case. |

`troyflow/risks.py` holds the lists, chosen by `[lang] name` in the config at `HEAD`, as `mocknotes.py` holds the mock notes (section 6.4). A comment or a string that names one counts too: a false sign costs one review, and a missed one waits for the release's review. A pack that the module does not know gives every CR1 the review. Its sentence is ``Run `/security-review` too, because troy-mode's check has no lists for the language pack <name>.`` troy-check accepts only `python` and `cpp` today, so a brief reaches it only when troy-check learns a pack before this module does.

**The Task's text.** After the task's own sentence, and after the mock notes' text at PR 3 and PR 5, CR1's Task adds one of two sentences. When the check finds a sign:

> Run `/security-review` too, because the diff adds <signs>.

`<signs>` names each kind found, with up to three places as `path:line`, or the path alone for a dependency file, and "and <n> more" after them, for example "a subprocess call (src/app/run.py:12) and network access (src/net/fetch.py:3, src/net/fetch.py:40)". When it finds none:

> troy-mode's check finds no dependency, subprocess call, network access, or credential handling that the diff adds, so `/security-review` is not needed, unless you see one of those four that the check missed.

Every CR1 brief gets one of them: each stage's, a side PR's, a bug's PRs', a version tests PR's, and a rule's cleanup PRs'. No other task gets either.

**CR2's brief.** `brief --task CR2 --item <vX.Y>` runs only on the review branch of F08 design 5.9: `HEAD` must be a branch `troy-mode/<vX.Y.Z>-security` whose one commit has `origin/main`'s files, on a parent that is the previous release's commit or the first commit. Anywhere else it stops with a problem that names the review branch and what is wrong: another branch or version, more than one commit, files that differ from `origin/main`, or another parent. The Task reads:

> CR2, review the security of <tag>: this branch's one commit holds every change since <the previous tag, or "the first commit">. Run `/security-review` on it, judge each finding, and change no file.

Read first holds `docs/rules.md`, `docs/requirements.md` with the version's rows, and `docs/architecture.md`. Checks to run is None.

### 6.6 Notes for later features (tstack #67, D284 to D287)

In the F11 pilot on `ZJUCao/recipe-menu`, reviews of early features left notes for later ones: what F11 and F13 should take from F06's module, that F12 must group by equality rather than identity, and timing models for the speed targets of F09 and F10. `status --note` keeps a note only while the feature and the stage stay the same (section 5.2), and the progress file is a view rebuilt from git and GitHub (D58), so troy-mode had nowhere to keep them. The pilot's main session kept them in its own memory file for the project folder, with several dozen entries by 2026-11-15, and copied each into the matching IF1 or DV2 brief by hand. A session on another PC, or one without that memory, loses them, and nothing checks that each note reached its brief.

**Where a note lives (D284).** A note is troy-mode's comment on a progress issue (F15 design 4), so it lives on GitHub with the rest of the state (D58):

```markdown
Note for F12, from #57, Code Reviewer, round 1

F12 groups recipes by equality of their names, not by identity: F06's loader makes a new
object for each file, so two files that hold the same recipe give two objects.
```

- The first line is the heading `Note for <feature ID>, from <source>`, which F15 design 8.4 adds to troy-mode's comment headings. The source is the PR, the role, and the round, or `Troy, in chat`. The text below it is in English, since roles read it.
- It goes on the progress issue of the feature whose work it comes from, such as F06's for a review of an F06 PR. A note from chat, or from work outside a feature, such as a bug's or a release's PR, goes on the target's progress issue when it has one, or else on the next feature's, which always has one (F15 design 4.1).
- troy-mode never deletes a progress issue, since F05's guard refuses `gh issue delete` (F15 design 10.2), and a closed one keeps its comments. `status` already reads every issue, open and closed, with its comments (F15 design 3.3), so finding the notes costs no extra call there.
- A note may name the feature it comes from, for its later stages, or any later feature that is not accepted. A note for an accepted feature is a requirement change (D65), so `note` refuses it with a problem that says so.

**Recording a note (D285).** The main session records each note. It reads every role's report already (section 6.3): when a report says what a later feature, or a later stage of this one, must take, the main session writes the note in its own words, in the form above, and runs `note --for <ID> --from <source> --file <text file>`. Troy's notes in chat take the same path. `note` checks the feature, picks the issue, writes the comment's file under `<git dir>/troy-mode/flow/notes/`, and gives the `gh issue comment <n> --body-file <file>` command. The skill checks the file with `check-text` and runs the command, as for every issue post (F15 design 3.4). No role's report format changes, so no agent file and no section of the skill that F16's instruction set holds changes for this.

**Which briefs get them (D286).** `brief` adds the feature's notes to the Input of every IF1, IF2, and DV2 run of that feature: each stage's first run and each later round, a `[docs]` side PR that updates the design (section 8.7), and the redo of a stage in rework (section 11.2). It reads them with one `gh` call over the progress issues and keeps those whose heading names the feature, oldest first. After the Input file's text, or as the whole Input when there is none, it adds:

```text
Notes for F12 from earlier work, kept on its progress issues:
1. From #57, Code Reviewer, round 1 (<link to the comment>):
   <the note's text>
2. From Troy, in chat (<link>):
   <the note's text>
```

and one sentence by task. IF1 and IF2: "Take each note into the design where it applies, and say in your report which ones you did not take, and why." DV2: "Where a note differs from the approved design, follow the design and say so in your report."

- A brief with no note for the feature is exactly as today. So is a brief in a repository whose `origin` is not on GitHub, such as the role exam's scratch projects: it has no progress issue to read, and `brief` makes no `gh` call there.
- When `origin` is on GitHub and `gh` cannot read the issues, `brief` stops with a problem, exit 1, and gives no brief: a brief that silently drops its notes is the pilot's problem again. The main session runs it again once `gh` works. `status` needs `gh` too, so the flow cannot go on without it anyway (F15 design 9).
- Other tasks get no notes. The pilot's notes went to the design and the implementation, and the Test Manager reads the design, which has taken them in.

**Late notes (D287).** `status` gains `notes`: for each feature that is not accepted and has notes, each note's issue, comment link, source, time, and what it can still reach. A note recorded before the feature's PR 1 opened reaches the design and the implementation. One recorded after PR 1 opened is `late` for the design, and one recorded after PR 5 opened is `late` for the implementation too: `brief` still adds it to every later IF2 and DV2 run, but a stage approved without another run never sees it. For each late note, `status` adds a line to its notes, and the main session decides, and says in its report to Troy: a design update in a `[docs]` side PR with IF2 (section 8.7), the note as Input for the open PR's next round, or nothing when the merged work already does what the note asks. The note stays on its issue either way.

**Feature teams (F20).** Notes live on GitHub, not in a checkout, so they fit F20's teams:

- **The right team's briefs.** A team's brief, `brief --repo <worktree>`, reads the notes through `gh` in the team's worktree, which shares the repository's remotes, and keeps the notes for that team's feature. Each team's IF1, IF2, and DV2 get the same notes they would get in the home checkout.
- **After `team end`.** `team end` removes the worktree and its git folder (F20 design 3.1). No note was there: each is a comment on a progress issue, and a feature's progress issue stays after its acceptance. A note that F08's team leaves for F10 still reaches F10's team when it starts later.
- **Who records them.** Only the main session talks to GitHub (F04 D29), and every team's reports reach it, so a note found in any team's review is recorded from the main session's checkout, on the progress issue of the team's feature. Two teams that leave notes for one feature add two comments, read oldest first.
- **Waits.** A late note for a running team's feature stops nothing. `status` shows it with that team, and the main session decides as above.

**The progress issue.** The target's progress issue gains one line, when the feature has notes and the issue exists: "备注：2 条（#31、#40）" with "Notes from earlier work: 2 (#31, #40)" in the English part, each linking its comment (F15 design 4.2). Troy then sees on the phone what waits for each feature.

**What the build settled.** `status`'s list is the key `feature_notes`, since the report's `notes` already holds its messages; each entry gives the feature and its notes, each with `issue`, `url`, `source`, `created`, and `late`. A stage PR opens at the earliest `createdAt` of its PRs, a closed one's included, so the PR list now reads `createdAt`; a note at exactly that time is not late. `note`'s report gives `issue`, `file`, and `gh`, the command with the file's path quoted for a shell. Whether `origin` is on GitHub comes from its configured URL, `remote.origin.url`, before any `insteadOf` rewrite, so an SSH URL counts. A `gh` error that the repository has disabled issues gives no notes rather than a problem. `notes.py` runs `gh` itself rather than through `github.py`, so `github.py` stays out of F16's instruction set.

**What does not change.** `status --note` keeps its job: a line in the progress file's Open issues, kept while the feature and the stage stay the same (section 5.2). The agent files, `common.md`, the templates, and the skill's sections "Running a role" and "The summary for Troy" do not change. The skill gains a section "Notes for later features" that says when to record a note, and its section "One stage" points there.

**The exam (F16 design 9).** `brief.py` and the module it gains, `troyflow/notes.py`, are in F16's instruction set (F16 design 9.1), so the build changes the instruction hash. Every module that `brief` imports joins the set, so `notes.py` keeps its imports few. `affected` renders each case's brief in a scratch project whose `origin` is a local folder, so no brief gains a note, and the expected result is "no case affected", at no cost. If `affected` names a case anyway, the build stops and reports it. By troy_exam's budget code, the IF1 and DV2 cases, if-example-format, if-error-rules, and dv-impl-notes, would cost $79.74 for the first round and $159.47 with their second rounds, which is above F16's $60 line, so that exam would wait for Troy (F16 D158). No F16 case tests notes: the pilot's mistake was the main session's, not a role's (F16 design 3).

## 7. The check after each run (D59)

`snapshot` records `HEAD`, the branch, and the time in `<git dir>/troy-mode/flow/<run ID>.json`. Because the tree was clean, every change `git status` lists after the run is the run's own. `check-run` looks for these problems:

1. **`HEAD` or the branch changed.** Roles cannot commit or switch branches (F05 section 7), so the hooks failed. F07 stops and escalates at once.
2. **A changed path outside the role's write scope** (F04 section 3). The check uses F05's scope table, troy-check's path classes, and the config at `HEAD`. Ignored paths do not count. For the Code Reviewer, any change is a problem.
3. **After AR2, a change to the design outside its section 4** (F04 D37). `check-run` compares the design and its mirror with `HEAD` section by section.
4. **A changed `dependencies` path not named with `--allow-dependency`.** F07 names only a dependency that Troy accepted (R16, 5.7, section 8.7).
5. **A role, or a command it started, still runs** (F05 design section 6.1, D231). A record of the run's roles, made since the snapshot, is open: the role has not stopped, or Claude Code moved one of its commands to the background and it may still run. The problem has kind `running`, and the report's `stop` lists each such agent ID. F07 ends each one with `TaskStop`, then runs `check-run` again. Ending the role ends its commands and does not wake it. A stale record, of a role that a usage limit or a closed session ended, clears the same way: `TaskStop` of an ID that no longer runs fails, and the hook has already closed the record. This problem counts no attempt and has no undo: what the command changed before it ended is the run's own, and the next `check-run` checks it like any other change. If the agent's permissions refuse `TaskStop`, F07 tells Troy which agent to stop and waits.

`snapshot` refuses with the same `running` problem while any role's record is open, whatever its run, and F07 ends each named agent the same way before it takes the snapshot again.

`check-run` also lists the role's lines in `hooks.log` since the snapshot (F05 section 10). They do not stop the flow on their own. A `background` line says that the role stopped with a command still running, and problem 5 names the same agent.

When the main session works as the Product Manager, F07 takes a snapshot with `--role product-manager` and checks the result against that scope (F04 section 3). That keeps the main session's own documents inside the Product Manager's scope (F05 section 4).

On a problem of kind 2, 3, or 4, F07 undoes the changes the report lists: `git restore` for a tracked file, and deleting a file that the run created. The tree was clean at the snapshot, so this loses only the run's own changes. F07 then runs the role once more, with Input that names the paths and the scope. A second problem in the same stage escalates. When there is no problem, F07 stages exactly the paths that `check-run` lists.

## 8. The feature loop (5.2)

### 8.1 Stages

| PR | Title | Author | Reviewers | Local checks before each push | Merged by |
| --- | --- | --- | --- | --- | --- |
| 1 | `[F04 1/6 design] <name>` | IF1, then IF2 for each revision | AR2 | `troy-check pr` | Troy for the first features (D61, D62), else F07 |
| 2 | `[F04 2/6 test-plan] <name>` | TM1, with IF3 for its questions | None. The Interface Designer's answers are the agreement, at most 3 rounds of questions. | `troy-check pr` | As PR 1 |
| 3 | `[F04 3/6 mock] <name>` | DV1 | CR1 | `troy-check pr`, the pack's steps, and `troy-check code` | F07 |
| 4 | `[F04 4/6 tests] <name>` | TE1 | TM2 and CR1, together | As PR 3. `troy-check code` checks R09. | F07 |
| 5 | `[F04 5/6 impl] <name>` | DV2 | CR1 | As PR 3, plus the feature's performance cases on Troy's PC when it has a target (5.6, Q7). `troy-check code` checks R10 and R11. | F07 |
| 6 | `[F04 6/6 accept] <name>` | PM3, in the main session | None | `troy-check pr` | F07 |

`<name>` is the feature's name in the requirements. The branches are `troy-mode/f04-1-design` to `troy-mode/f04-6-accept`. The name must be short, such as "Export history as CSV", because it becomes every PR title and the feature's folder name. In the trial, the Product Manager put a whole sentence in the Feature cell, and the folder's paths passed Windows' path length limit, so plain `git add` failed. The skill tells the Product Manager to keep the cell to the short name.

### 8.2 One stage, step by step

1. **Order.** The stage before it has merged on `origin/main`, and every hard dependency of the feature is accepted. F02 section 11 leaves stage order to F07.
2. **Branch.** `git fetch origin --prune`, then `git switch -c <branch> origin/main`. F07 never checks out `main`. In a worktree that the desktop app made, `main` is often checked out in another worktree, and git refuses to check it out twice.
3. **Author.** A role run (section 6) and its check (section 7).
4. **Commit.** `git add -- <path>` for exactly the paths that `check-run` lists. The first run makes the commit, whose subject is the PR title (R01). Later runs amend it, so the PR keeps one commit. F05's `commit-msg` hook checks R19.
5. **Local checks.** The checks in the table, on the commit. A failure goes back to the author as Input and counts as an attempt.
6. **PR.** `git push --force-with-lease -u origin <branch>`. The first time, `gh pr create --base main --head <branch>` with the title and a description from the PR template: Why (the feature's goal), What (the stage's output, with IDs), Checks (what ran and the results), and Soft-limit reason (from the Developer's report, or None). Later pushes update the description with `gh pr edit`.
7. **Reviews.** Each reviewer runs on the PR, and F07 posts its report as a comment (section 8.4). AR2 also writes section 4 of the design, so F07 checks and amends after it as after an author. `changes-requested` sends the findings to the author as the next round.
8. **Merge** (section 8.6).

### 8.3 Rounds (R17)

A round is one run of the stage's reviewers on the PR. On PR 4, a `changes-requested` from either reviewer fails the round. If round 3 still ends in `changes-requested`, F07 escalates. For PR 2, a round is one question to the Interface Designer and its answer, and the test plan's alignment log records each one (F01 design 5.4). F07 counts rounds from its own comments, so a new session counts on from where the last one stopped.

### 8.4 Comments

F07 posts every review, failed attempt, escalation, and request to Troy as a PR comment that starts with a fixed heading:

- `Architect review, round 2: changes-requested`, then the findings;
- `Developer attempt 2: failed`, then the failing checks. For a failure in CI, the first line under the heading is `Commit: <commit ID>`, the pushed commit that failed (section 8.5, D261);
- `Escalation: <trigger>`, then the message of section 9;
- `Waiting for Troy: approve this PR`.

GitHub does not let an account approve its own PR, and every role acts through Troy's account, so the heading records who did what (F04 D29). A comment without one of these headings is Troy's. F07 reads Troy's comments on an open PR and passes them to the author as Input. It checks each of its own comments with `check-text` before posting it.

### 8.5 Attempts (D64)

An attempt is an author run that reports `failed`, reports `done` while F07's local checks fail, or leads to a CI failure in the author's files. Each stage allows 3 attempts. After the third, F07 escalates (5.7). A revision whose checks pass is a round, not an attempt.

**Attempts from CI (D261 to D263).** A comment can be missed: in the pilot, CI failed on four pushes in the Interface Designer's files, twice on ZJUCao/recipe-menu#52 and twice on #59, and one attempt comment was posted, so the retrospective saw 1 failed attempt (tstack issue #73). `status` therefore also reads the CI runs of each open PR, and `retro` those of each merged PR of the version (F08 section 7):

- **The runs.** `status` lists the workflow runs of the PR's head branch with `gh run list --branch <branch> --event pull_request --limit 100 --json databaseId,headBranch,headSha,status,conclusion,createdAt,updatedAt,workflowName`. `retro` lists the runs of the version's PRs in one call, with `--created <date>..*` (GitHub's form of "on or after", which needs no `>`) and the oldest PR's creation date in place of `--branch`, and `--limit 1000`; when 1,000 runs come back, it notes that older runs may be missing. A PR keeps the runs of its head branch created at or after the PR was opened and, for a merged or closed PR, at or before it merged or closed, so the runs of a later PR that uses the branch name again stay apart (D261).
- **At most one attempt per pushed commit (D261).** The runs are grouped by their head commit. For each workflow, only its newest run on that commit counts, as in `wait-checks`: a run started again by an edit of the description, or a failed job that was re-run and passed, leaves only the newer result. A commit failed when one of those runs concluded `failure`. A commit whose runs were cancelled, or are still running, counts nothing.
- **In the author's files (D262).** For each failed run, `gh run view <run ID> --json jobs` gives the steps that failed. A failed step that runs a check on the repository's files is the author's: `Run troy-check` in troy-check's job (F02 section 8), and every step after `Install from the lock` in the language pack's job (F03): `Lint and format`, `Types`, `Tests`, `Coverage report`, and `Run troy-check code` for Python, and `Configure and build`, `Format and lint changed files`, `Tests`, `Coverage report`, `Doc comments`, and `Run troy-check code` for C/C++. The PR holds only its stage's work, on a `main` whose checks passed, so a check that fails there fails on the author's files. Any other failed step lies outside them: the checkout (the pilot's "Repository not found" on ZJUCao/recipe-menu#87), `Look for code`, the environment's setup, `Install from the lock`, GitHub's own steps, a step that was cancelled or timed out, and every job of a workflow that troy-mode did not write. Such a failure is no attempt. On the PR's newest commit, F07 stops and tells Troy (section 8.6).
- **Already counted (D261).** An attempt comment counts the failed commit that its `Commit:` line names, with 7 to 40 hexadecimal digits matched as a prefix. A comment without that line, such as one for local checks or one posted before this change, counts the PR's newest pushed commit at the time it was posted, when that commit had failed in the author's files by then (its failed run's `updatedAt` is no later than the comment) and no other comment counts it. Every `Commit:` line is matched first, then the other comments, oldest first. The newest pushed commit is the one whose first run started last, since a run starts within seconds of the push.
- **The count.** A PR's attempts are the highest number in its attempt comments, plus each commit that failed in the author's files and that no comment counts. Each such commit takes the next number, in the order the commits were pushed.
- **The comment that was missed (D263).** `status` gives each open PR's failed commits in `ci_failures`, oldest first: `commit`, `runs`, `steps` (each as `<job> / <step>`), `author` (the failure lies in the author's files), `counted` (a comment counts it), and `attempt`, the number that an author failure not yet counted takes, else null. Before it goes on, F07 posts `<Role> attempt <n>: failed` for each one with an `attempt`, with that number, the line `Commit: <commit ID>`, and the failed steps, so the PR shows every attempt and the count stays the same. The role is the stage's author, from the PR's title as `next.task` gives it. `retro` posts nothing: it only counts (F08 section 7).
- **When gh cannot list the runs,** `status` adds a note and counts from the comments only, as before.

### 8.6 Merging (R18, F02 D14)

F07 merges a PR only when all of these hold:

- every review of the stage ended in `approved`;
- the local checks passed on the pushed commit, or failed only on tests skipped on this platform (D69, below);
- `wait-checks --pr <n> --sha <sha>` (D204), with the full commit ID F07 pushed, reports `passed`: every check of that head has registered and finished, and each passed;
- the merge rights allow it. PR 1 and PR 2 of the first `troy_approves_first` features in the order wait for Troy (D61, D62). Every other PR is F07's to merge.

F07 then runs `git switch --detach`, `gh pr merge <n> --rebase --delete-branch --match-head-commit <sha>`, `git fetch origin --prune`, and `status --write-progress`. It detaches first so that `gh` does not try to check out `main` before it deletes the branch. Every fetch prunes: a branch name may come back after its PR merged, such as `troy-mode/v0.1-test-plan` for a plan's update, and a stale `origin/<branch>` makes `git push --force-with-lease` refuse the new branch (found in F08's trial). Each of these is its own command, after F07 has read the wait's exit code: the merge never follows the wait on one command line, chained with `;` or otherwise (D204).

**Waiting for the checks (D204).** `wait-checks` polls `gh pr view <n> --json headRefOid,state,statusCheckRollup` every `--interval` seconds (15) and reads:
- **The head.** While the PR's head is another commit, the wait goes on, since GitHub can lag right after a push. A merged or closed PR ends it with `closed`.
- **No check yet.** Right after a push GitHub may not have registered the workflow, and the rollup is empty. That is still a wait, never a pass (the pilot's ZJUCao/recipe-menu#47).
- **The checks.** Every check run and commit status of the head. When a workflow ran more than once for the same head, for example after `gh pr edit` changed the description, only the newest run of each check counts: one that has not started (no `startedAt`, or gh's zero time `0001-01-01T00:00:00Z`), else the latest start. A check run passes with `SUCCESS`, `NEUTRAL`, or `SKIPPED`; a status passes with `SUCCESS`. Anything still queued or running is pending; anything else failed.
- **Settled.** `passed` needs every check finished and passed on two reads at least `--settle` seconds (30) apart, with the same checks, so a workflow that registers a little later is not missed.
- **Results.** `passed` exits 0. Every other result exits 1 with one problem: `failed` once every check has finished and one failed, with the failed checks in `failed` and their run IDs in `runs` for `gh run view <id> --log-failed`; `pending` when `--timeout` (540 seconds, under the ten minutes one Bash call may take) ends first, with "No check has reported" when none did; `other-head` when the head was still another commit; and `closed`. On `pending`, F07 runs it again, which is the same wait; if a second run still finds no check, F07 stops and tells Troy. A gh call that fails is tried again at the next read; three failures in a row exit 2.

- **A test that runs on another platform only (D69).** A case of the test plan may run on one platform only, such as F01-T17 of the trial, an unreadable file, which runs on Linux and skips on Windows. troy-check counts a skipped test as neither failing (R09) nor passing (R10), so the local `troy-check code` fails on Troy's PC while CI, on Ubuntu, runs the test. When `check-skips` says that the only local failures are such skipped tests, the local checks count as passed: no attempt is counted, the PR description's Checks section lists those cases as checked by CI only, and F07 merges on CI's result, which proves the tests ran. The test plan must say why the case runs on one platform only; TM2 and CR1 check that. Authors' briefs say the same, so an author reports the skip instead of failing on it.
- **A failing CI check.** F07 runs `status` and reads the pushed commit in the PR's `ci_failures` (section 8.5). With `author` true, the run counts as an attempt: F07 posts its comment with the `Commit:` line and the number in `attempt`, then gives the author the failing log (`gh run view --log-failed`) as Input. With `author` false, the failure lies outside the author's files, such as in the workflow or on the runner: F07 stops and tells Troy.
- **A refused merge.** If Claude Code's permissions refuse `gh pr merge`, F07 stops and tells Troy which permission to add. It never works around a refusal.

**Troy's approval (D61).** When a PR waits for Troy, F07 posts `Waiting for Troy`, tells Troy in chat with the link, and stops. Troy either replies in chat or merges the PR on GitHub.

- On a reply that approves, F07 runs `approve` on the PR's document. The `version` moves to the next major (F01 design section 4), `updated` becomes the date, and the status becomes "Approved by Troy on <date>" and its Chinese form. `approve` changes only these header fields, and adds a row "Approved by Troy." to the change log (F08 D77), in both languages, so no role runs for it. When either file of the pair has no change-log table, `approve` changes nothing and exits 1, naming the file (D201): the document's author adds the table in a new run with that problem as Input, and F07 runs `approve` again. F07 amends the commit, pushes, waits for the checks, and merges.
- **The architecture's ADRs (D202).** When the document is the architecture, `approve` also accepts the ADRs that its decision records table lists and that are still proposed, so no Architect run is needed for their status words. An ADR is proposed when the first line of its Status section starts with "Proposed" (Chinese: "提议中", "已提议", "提议", or "Proposed"). For each such ADR, in both languages, `approve` raises the header as for the architecture, with no change-log row since ADRs have none, and writes the Status line "Accepted. Troy accepted it on <date> by approving `docs/architecture.md`." (Chinese "已接受。Troy 于 <date> 批准 `docs/architecture.md`，接受了这条记录。"), keeping any text that followed the word. The row's Status cell in the architecture's table becomes "Accepted" ("已接受"). A listed ADR without exactly one English file under `docs/adr/` and its mirror, each with a troy-doc header, or whose files' versions differ, stops `approve` with exit 1, and nothing is written. The report's `changed` lists every file, and `adrs` the accepted IDs.
- On a reply that asks for changes, the author revises, as a round.
- When Troy merges on GitHub, the document stays below 1.0. F07 then opens and merges `[docs] Record Troy's approval of <document>`, which holds only the change that `approve` makes.

The same steps serve the requirements and the architecture (section 10).

**After the first features (D62).** When the last of the first `troy_approves_first` features is accepted, F07 asks Troy once whether to go on approving PR 1 and PR 2. A `[rules] Set the features Troy approves` PR records the answer in `[flow] troy_approves_first`, and F07 merges it.

### 8.7 Side PRs (part 2)

A side PR interrupts a stage. F07 finishes the side PR, rebases the stage's branch on `origin/main`, and runs the stage's author again.

| Case | Flow | PRs |
| --- | --- | --- |
| Disputed test (5.2) | DV2 reports `needs-answer` for the Test Manager, and TM4 rules. | A wrong test: `[F04 test-fix] <summary>` with TE3, reviewed by TM2 and CR1. Wrong code: DV2 again, with the ruling. |
| Coverage gap (5.2) | R11 fails, and TM3 classifies the uncovered code. | Code nothing needs: DV4 in the same PR. A missed case: the Test Manager adds it in a `[docs]` PR, then TE4 in a `[F04 test-fix]` PR. Behavior not in the design: IF4 rules, then a `[docs]` design update and tests, or DV4. Untestable code: an exclusion with a reason, approved by TM6. |
| New dependency (R16) | A role reports `needs-answer` for the Architect. AR3 reviews it and escalates with a recommendation. | Troy accepts: AR3 records it in the architecture with an ADR, in a `[docs]` PR. The author runs again, and `check-run` allows that dependency file. Then the series lock follows (D66). Troy refuses: the author runs again without it. |

**Series lock (D66).** When a lock file changes, F07 compiles the series lock from every member's manifest with troy-init's functions (F06 design 5.4), installs it in the shared environment, and runs each member's tests there before the merge (F03 design 8.1). The PR description lists the members whose lock is now stale. F07 opens no PR in them.

How part 2 runs these cases:

- **Who writes the side PRs.** Rulings change no file: TM3, TM4, TM6, IF4, and AR3's review. The Test Manager adds missed cases with TM1, the Interface Designer writes a design update with IF2, which AR2 reviews, and the Architect writes the dependency's ADR in AR3's second run, after Troy accepts. Each of these runs gets `brief --title` with its PR's title, so its checks name the right PR.
- **Titles and branches.** A test fix is `[F04 test-fix] <summary>` on `troy-mode/f04-test-fix`. A `[docs]` side PR names what it adds, such as `[docs] Add cases to the F04 test plan`, on `troy-mode/f04-docs`. A bug's side PRs use the bug ID in the same way.
- **The series lock.** `series` lists the commands that compile and install the lock and run each member's tests, with the members whose lock is now stale. F07 runs them after the author's run that `check-run` allowed, and stages the new lock with the author's files.
- **Order.** While a side PR is open, `status` continues it before the stage PR it interrupts (section 5.1).

### 8.8 Role runs and cost (D264 to D267)

In the pilot, v0.1 cost $1,092 at the API's list prices: 263 role runs, 74 helper agents, and the main session, against an estimate of $130 to $235. Nobody saw it until the report after the release, because no step of troy-mode reports cost (tstack issue #74). So the acceptance PR (PR 6) and the release PR (F08 section 5.7) report their feature's or version's role runs and token cost, which `costs` reads from Claude Code's transcripts on Troy's PC:

- **Where the transcripts are (D264).** Claude Code keeps each session as `<session ID>.jsonl` in `<config>/projects/<folder>/`. `<config>` is `$CLAUDE_CONFIG_DIR`, or `.claude` in the home folder, and `<folder>` is the session's working folder with every character other than an ASCII letter or digit turned into `-`: `D:\Troy\Projects\recipe-menu` gives `D--Troy-Projects-recipe-menu`. A subagent's transcript is `<session ID>/subagents/agent-<agent ID>.jsonl`, beside `agent-<agent ID>.meta.json`, whose `agentType` names a role as `<plugin>:troy-<role>` and whose `parentAgentId` names the agent that started a helper. `costs` reads the folder of the main checkout, the folder of each worktree that `git worktree list` gives, and every folder whose name is the main checkout's followed by `--claude-worktrees-`: the desktop app's worktrees, whose transcripts stay after the worktree is gone. `--transcripts`, given once or more, names the folders to read instead. It never writes there.
- **Which runs belong to an item.** A role run belongs to the item that its brief names, in the line `Item: <ID>, <title>` of its transcript's first message (section 6.1), whatever session it ran in. `--item <ID>` sums every run of the item, the helper agents those runs started, and the main session's messages from the start of the item's first run to the end: the time of the feature's `accept` commit on `origin/main` once it has merged, else the time `costs` runs, or `--until`. Agents that are not roles and that no role started, such as a search the main session started, count as the main session's other agents, in the same time. A feature's figure for the main session also holds its work on other things in that time, such as another feature's side PR.
- **A version.** `--tag <vX.Y.Z>` sums everything from the previous `[docs] Release` commit on `origin/main`, of any earlier tag, or from the project's first transcript when there is none, to this tag's release commit once it has merged, else the time `costs` runs, or `--until`: every role run that started in that time, the helpers, the other agents, and the main session's messages. `items` gives the role runs' cost by item.
- **Token cost.** Each assistant message counts once: a transcript repeats a message's record for each of its content blocks, with the same usage, so records are told apart by the message's ID. Its cost is its input, output, cache read, 5-minute cache write, and 1-hour cache write tokens and its web searches, at the list prices of its model (D265), and at the model's fast prices when its `speed` is `fast`. A model the price table lacks is listed in `unpriced` with its tokens and is never guessed; the total then reads "at least". Claude Code's own calls that leave no assistant record, such as a compaction's summary, are not counted. In the pilot this computation gave the pilot report's figure for every role to the cent.
- **Sessions and PCs.** A feature that spans sessions is summed over all of them. A run on another PC leaves its transcript there, so the report says that it reads this PC only and lists each session it read. For `--item` it names each of the feature's stages 1 to 5 merged on `origin/main` for which it found no role run here (it calls no gh, so an open stage is not checked); for `--tag`, each feature of the version with none.
- **The desktop app's own figure (D266).** The desktop app writes `cost-state` records into a session's transcript: its running cost per model since the app started, with the token counts behind it. `costs` prices the newest record's token counts with its table and adds a note when a model's figure differs from the app's by more than 1%: the price table is then out of date.
- **The report.** In JSON: `roles` (each role with its `runs`, `models`, and `cost`), `helpers`, `others`, `main`, `total`, `items`, `window`, `prices` (the table's `as_of`), `sessions`, `unpriced`, `missing`, and `notes`. `description` is the PR description's section `## Cost`: one sentence with the item, the prices' date, the time span, and "this PC's transcripts", then a table with a row per role, the helpers, the other agents when there are any, the main session, and the total, then a line per note. `line` is one sentence for the report to Troy. Neither names a model by its ID nor holds a path, because R19's strict mode refuses the whole word that both contain: a model shows as its family and version, such as "Opus 5.5". `costs` exits 0 whenever it could read, also with no transcript found, which the section then says.
- **PR 6.** Before the acceptance PR's last push, F07 runs `costs --item <ID>` and puts its `description` after the "Real run" section. The report to Troy after the merge adds its `line`, in Troy's language.
- **The summary for Troy (D267)** carries no cost: it opens PR 1, PR 2, the requirements, and the architecture (F14 design), and a feature's cost is known only at its acceptance.

**The price table (D265).** `troy-mode/flow/prices.toml`, in the plugin beside the engine, holds the list prices in US dollars per million tokens. `as_of` is the date they were read from Anthropic's pricing page, and `web_search` the price of one web search. Each `[models."<model ID>"]` table has `input`, `output`, `cache_read`, `cache_write_5m`, and `cache_write_1h`, and a model with a fast mode also a `fast` table with the same keys. A tstack PR updates it when a list price changes or a new model comes, and raises the plugin version (F10 D89). The first table, as of 2026-11-03, holds the current Opus, Sonnet, Haiku, and Fable models; the pilot's `cost-state` records confirm its Opus 5.5, Sonnet 5.5, and Haiku 5.5 prices to the cent.

## 9. Escalation (5.7)

| Trigger | How F07 finds it |
| --- | --- |
| A review loop reaches 3 rounds without agreement | Its round count (section 8.3) |
| A change needs the requirements or the architecture to change | A role's `escalate` report, or AR5's answer |
| An author's work still fails after 3 attempts | Its attempt count (section 8.5, D64) |
| A new third-party dependency | AR3's `escalate` report (section 8.7) |
| An irreversible action outside the merge rights | F07 checks before it acts. Its rights: push its own branches with `--force-with-lease`; open, edit, comment on, close, and merge its own PRs within R18; open bug issues; delete its own branches after their PR merges; and, after Troy accepts a version, create its GitHub release on the release PR's merge commit (F08 section 5.7). Anything else asks Troy. |
| A run changed `HEAD` or the branch, or broke its scope twice | `check-run` (section 7) |

The message follows F01's `escalation` template, in Troy's language: where it stopped, why, the facts with links, the options, and a recommendation (Prototype C). F07 also posts it in English on the open PR, writes "Waiting on Troy" into the progress file, and stops. When no PR is open yet, F07 posts it on the bug's issue if there is one: in part 2's trial, the Developer asked for a dependency before PR B existed, and the escalation went on the issue. When Troy answers, in this session or a new one, F07 puts the decision into the next brief's Input and goes on.

## 10. Project setup (5.1)

1. **Setup.** When the folder has no `.troy-mode/` and Troy says yes, F07 runs troy-init's engine `setup` and the PR flow of F06 section 7, with F06's questions: whether to create the GitHub repository, and whether to replace files that troy-init did not write. Step 8 of that flow follows section 8.6 here: detach before the merge, then `git fetch origin`.
2. **Requirements.** After the setup PR merges, so that troy-check checks the requirements too (F06 section 10). The main session works as the Product Manager (PM1), with a snapshot. The PR is `[docs] Add the requirements`, and Troy approves it as section 8.6 says.
3. **Architecture.** AR1, then `[docs] Add the architecture`, approved the same way. The message that asks Troy for this approval also asks the language step's question: which series the project belongs to.
4. **Language step.** troy-init's engine `lang` with the PR flow. The engine stops on `main` for every step, even a dry run, so F07 creates the branch `troy-mode/lang-<name>` before the dry run (F06 design 1.2). The language comes from the architecture's tech stack.
5. **Next.** F07 reports, and goes on to the first feature only if the request asked for it (D63).

A project that already has some of these steps resumes at the first missing one. **Upgrade** runs the same way: the engine's `upgrade` on a branch made before its dry run. When there is nothing to change, F07 deletes the branch again.

## 11. Other flows

### 11.1 Bug fix (5.3, part 2)

1. Troy reports a bug in chat or names an issue. When there is no issue, F07 opens one with the label `bug`, and its number gives the bug ID (F01 D3).
2. TM5 triages it. A misunderstood requirement goes to the change flow.
3. PR A, `[B12 A/B test] <summary>`: TE2, reviewed by TM2 and CR1. `troy-check code` checks that B12's tests fail (R09).
4. PR B, `[B12 B/B fix] <summary>`: DV3, reviewed by CR1. `troy-check code` checks that B12's tests pass. The description says "Fixes #12", so GitHub closes the issue when F07 merges the PR.

The branches are `troy-mode/b12-test` and `troy-mode/b12-fix`. PR B's title repeats PR A's summary, and after PR A merges, `status` gives PR B as the next action, so a new session finishes the bug. TM5 changes no file. When DV3 disputes a test, TM4 rules and TE3 fixes it in `[B12 test-fix]`, as section 8.7 says for features.

### 11.2 Requirement change (5.4, part 2, D65)

1. **PM2.** The Product Manager updates the requirements in a `[docs] Change the requirements: <summary>` PR. Troy approves it (section 8.6), and the affected features become "Needs rework".
2. **AR4.** The Architect lists the interfaces, tests, and parts of the architecture that change, with an ADR for an architecture change.
3. **A feature not yet accepted** goes back to the earliest stage that AR4 names. F07 closes the feature's open PR, if it has one, without merging it, and runs the loop from that stage.
4. **An accepted feature** gets a new feature for the change, which PM2 adds with a hard dependency on the old one. Its design lists the changed interfaces in section 3. Its test plan names the old cases that the change retires, and records them in the "Not tested" section of the old feature's test plan. Its tests PR deletes those tests and adds new cases, which fail against the current code (R09). Its mock PR holds only new interfaces, and F07 skips PR 3 when there are none. troy-check needs no change, because every test of the old feature that remains still passes.

Every existing test runs as regression, as on every PR (5.6).

How part 2 keeps this state in git (D58):

- **Needs rework.** PM2 marks each affected feature that is not yet accepted "Needs rework (<the change>)" in the Status column. An accepted feature keeps its status, and the new feature's row carries the change. A feature is in rework while its Status says so and no stage of it has merged since the newest `[docs] Change the requirements:` commit. Then `status` asks for AR4, also in a new session.
- **The redo.** The redo PR has the stage's usual title, and `brief --title` with that title accepts a stage before the current one while the feature is in rework. When the redo merges, the stages after it no longer count (section 5.1), so the loop runs on from there. A stage PR opened before the change, whose branch lacks the change commit, makes `status` ask for AR4 before it continues. When the feature's implementation has merged and its tests change, the redo starts at stage 3 at the latest: R09 needs every test of the feature to fail against a mock.
- **The skipped mock.** "No new interfaces" means that section 2 of the new feature's merged design holds no interface subsection. `status` and `brief` then go from PR 2 to PR 4.
- **Troy's approval.** The change PR waits for Troy like the requirements (section 8.6). `approve` raises the requirements to the next major version. When Troy merges it on GitHub instead, its version still has a minor part, and `status` asks for `[docs] Record Troy's approval of docs/requirements.md`.

### 11.3 Work outside the pipeline (5.9)

F07 answers questions and investigations in the main session, following `how` or `why` when they fit, and starts no role. An experiment runs on a throwaway branch `troy-mode/try-<slug>` made from `origin/main`, or in a scratch folder. F07 never pushes it or opens a PR from it. Code worth keeping goes through a requirement change and the feature loop.

### 11.4 Continue (5.10)

F07 runs `status` and reports where the project stands. When something waits on Troy, it says what. Otherwise it goes on with the next action.

## 12. Changes to earlier features

- **troy-check (F02, F03).**
  - The config reader accepts `[roles.<role>]` with `model` and `effort`, and `[flow]` with `troy_approves_first`, a whole number of 0 or more (section 3.2). `config.default.toml` describes both in comments.
  - `troy-check code` gains `--worktree` (D60). It checks the working tree as if it were committed: it builds a commit object from a temporary index outside the working tree, with `HEAD` as its parent, and checks that commit as `--head`. It moves no ref and changes neither the index nor the working tree. It writes only git objects that no ref points to.
  - F02's and F03's designs each get a change-log row. A project gets both changes through troy-init's upgrade.
- **F05's hooks** read the config through troy-check's reader, so they accept the new tables without a change of their own.
- **troy-init's skill (F06).** Step 8 of its PR flow detaches before the merge and ends with `git fetch origin`, in place of `git switch main` and `git pull`, so troy-init also works in a worktree. F06's design gets a change-log row.
- **F04** does not change. `--worktree` reaches the roles through the brief's checks.

F07 adds no workflow step to projects. Its tests run in troy-pstack's `troy-checks-tests.yml` with the default shell. A step that uses `shell: bash -leo pipefail` must never call `exit`, because on the runner `~/.bash_logout` turns `exit 0` into 1 (found in F06 part 2).

## 13. How F07 maps to the requirements

| Requirement | Where F07 covers it |
| --- | --- |
| F07 row: routes each request to a flow (5.1 to 5.10) | Section 4 |
| F07 row: runs the feature loop | Section 8 |
| F07 row: passes reviews between roles | Sections 6.3, 8.2, and 8.4 |
| F07 row: escalates | Section 9 |
| F07 row: applies the merge rights | Section 8.6 |
| F07 row: keeps the progress file | Section 5.2 |
| F07 row and F04 D32: model and effort from `[roles]` | Section 3.2 |
| F07 row and F04 D31: the check after each run | Section 7 |
| 3.3: where Troy takes part | Sections 8.6, 9, and 10 |
| 5.1 Project setup | Section 10 |
| 5.3 Bug fix and 5.4 Requirement change | Sections 11.1 and 11.2 |
| 5.6 When tests run | The local checks in section 8.1, and CI on every PR |
| 5.9 Work outside the pipeline and 5.10 Continuing | Sections 11.3, 11.4, and 5 |
| R01, R02, R17, R18, R19, R21 | R01, R02, and R21: section 8.2. R17: section 8.3. R18: section 8.6. R19: sections 8.2 and 8.4 |
| F02 section 11: stage order | Section 8.2, step 1 |
| F03 design 8.1: a series' lock and tests after a dependency change | Section 8.7 |
| F05 section 12: one writing role at a time, the check after each run, the hooks log, and `troy-check code` | Sections 6.2, 7, and 12 (D60) |
| F06 section 10: running troy-init's engine, the requirements after setup, and DV1's setup steps | Sections 10 and 6.1 |
| Section 8: new skills run only when Troy types them | Section 2 |

## 14. How F07 is checked

### 14.1 Tests

Tests use `unittest` and the standard library. A separate agent writes them from this design before the engine exists. Each test builds a temporary git repository with a local bare `origin`, made with `git clone --bare`, so no test pushes `main`. A fake `gh` on the `PATH` serves PRs and comments from a JSON file and records its calls. The tests live in `troy-mode/flow/tests/`. `troy-checks-tests.yml` runs them on Linux and Windows for every PR that changes `troy-mode/flow/`, `skills/troy-mode/`, `troy-mode/checks/`, or `troy-mode/hooks/`.

| Group | Cases include |
| --- | --- |
| Status | Stages from rebase, squash (with ` (#41)`), and merge-commit subjects. Open PRs. The next feature. An order line that breaks a dependency. Merge rights with `troy_approves_first` at 0, at 3, and past the count. Rounds and attempts from comments, with Troy's comments told apart. A project copy of troy-check older than the plugin's. |
| Progress | The fields of F01's template, in English, with no marker. Rebuilt when missing, with a note. |
| Brief | F04's six fields. Read first by task. The pack's steps for Python and C/C++, `--worktree` for authors, DV1's setup steps for the first mock only, and `TROY_MODE_ENV_PREFIX`. Model and effort from `[roles]` at `HEAD`, not the working tree, and left out when unset. |
| Snapshot and check | A dirty tree refuses a snapshot. Changes inside the scope pass for each role. Problems: a change outside the scope for each role, the Code Reviewer changing anything, AR2 outside section 4, a dependency path without `--allow-dependency`, and a changed `HEAD` or branch. Ignored paths and an allowed dependency pass. The undo steps. Only this role's `hooks.log` lines since the snapshot. The Product Manager's scope. |
| Approve and text | `approve` raises both languages to the next major and writes both status lines. It exits 1 and writes nothing when either file has no change-log table (D201). For the architecture, it accepts the listed ADRs that are proposed, in both languages, with their rows in the architecture's table, and leaves the others alone; a listed ADR without both files refuses (D202). `check-text` refuses attribution in strict mode. |
| troy-check | `[roles]` and `[flow]` are accepted. An unknown role, an unknown key, a wrong effort value, and a negative count are refused. `--worktree` sees new files, skips ignored ones, gives the same results as a real commit, and leaves the index, the refs, and the working tree as they were. |
| Skill | Front matter `name: troy-mode` and `disable-model-invocation: true`. It names every flow of section 4, every engine command, and the stage titles of section 8.1. Its routing gives a request that names a version, such as "Start v0.1", the version's remaining features, and not its release (D203). |
| Part 2 | Bugs from subjects and open PRs, and PR B as the next action. Side PRs before the stage PR. The redo of a stage and the rework that needs AR4. A skipped mock. A change PR merged by Troy, and its approval recorded. Briefs for every part 2 task, by stage, bug step, and title. `check-skips` with only skipped tests failing, and with other failures. `series`' commands and stale members. |
| Running work (F05 D231) | `check-run` with an open record of the run's role, either not stopped or stopped with a task in `background`, gives a `running` problem with the agent ID in `stop`, exit 1, `escalate` false, nothing to stage, and no undo for it. A closed record, another role's record, and a record made before the snapshot give none. `snapshot` refuses with any open record, with the same problem, and gives both problems with a dirty tree as well. A record without the new fields counts as closed. The skill's section "Running a role" names `running`, `TaskStop`, and `check-run` again, and does not ask for roles in the foreground. |
| Attempts from CI (D261 to D263) | A commit that failed in a check step counts once, however many of its runs or jobs failed. Only the newest run of each workflow on a commit counts: a newer passing run clears an older failure. Cancelled and running runs count nothing. A run of the same branch from before the PR opened, or after it merged, is left out. A failure in the checkout, the setup, `Install from the lock`, or a workflow troy-mode did not write is no attempt, and `author` is false. A comment's `Commit:` line, in full or as a 7-digit prefix, counts its commit. A comment without one counts the newest pushed commit when it was posted, only when that commit's failure had finished and no other comment counts it. The count is the highest comment number plus each commit not counted, numbered in push order. `ci_failures` gives each failed commit with its `attempt`. A failing `gh run list` adds a note and counts the comments only. The skill's merge step posts the missed comment with the `Commit:` line. |
| Role runs and cost (D264 to D267) | Folder names from a Windows path and a desktop worktree's path, and `$CLAUDE_CONFIG_DIR`. A role from `agentType`, a helper from `parentAgentId`, other agents. A message's repeated records counted once. Each token kind, web searches, and fast speed priced from a test table; a model not in it listed in `unpriced`. Runs tied to an item by the `Item:` line, across two sessions. `--item`'s time from the first run to the `accept` commit, and to now before it merges; `--tag`'s from the previous release commit of any tag; `--until`. Main-session messages outside the time left out. A stage with no run found named in `missing`. A `cost-state` figure that differs by more than 1% gives a note, and one within 1% none. `description` and `line` hold the figures, no model ID, and no path. No transcript found: exit 0 and a section that says so. The skill's PR 6 step names `costs` and the section. |
| Wait for checks (D204) | No check at first, then a pass; a second workflow that registers late; a failure, reported once every check has finished, with its run IDs; an older failed run of a check beside a newer passing one; a commit status; `SKIPPED` and `NEUTRAL`; another head; a merged PR; the timeout; gh failing once and three times. The skill's merge step names `wait-checks` and never chains the merge with `;`. |
| Mock notes (D205 to D207) | In `test_mock_notes_brief.py`, modelled on `test_summary_brief.py`: the Task line of DV1 in a Python project and in a C/C++ project, of DV2, and of CR1 at PR 3 and at PR 5 holds its text of section 6.4 exactly once, with the pack's sentences, and never the other language's. The redo of PR 3 in rework holds DV1's text. CR1 at PR 4, CR1 in a test-fix side PR, CR1 and DV3 in a bug PR, and the other tasks hold none. |
| Security review (F04 D280 to D283) | In `test_security_brief.py`: each sign for Python and for C/C++ in an added line of a source file, with its place; a deleted line, a context line, and a line of a test file give none; a dependency file gives its sign, and a CMake file only with a line that names a package; up to three places per kind and "and <n> more"; the "not needed" sentence when nothing is found; one sentence in every CR1 brief, after the mock notes' text, and none in another task's; a pack the module does not know gives the review; the diff from the merge base, in a team's worktree too. CR2's brief on a review branch, with its tag and its base, and its problem off it. The Code Reviewer's agent file has CR2, and its CR1 steps run `/security-review` only as the brief or the role's own sign says. |
| Notes for later features (D284 to D287) | In `test_notes.py`, with the fake `gh`: `note` picks the source feature's progress issue, then the target's, then the next feature's; refuses an accepted feature, an unknown one, and a repository with issues turned off; writes the heading and the text, and gives the command. `brief` adds the notes for its feature only, oldest first, with links, to IF1, IF2, and DV2, in each stage's first run, a later round, a `[docs]` side PR, and a redo in rework, after the Input file's text or as the whole Input, with each task's sentence; no other task gets them; a closed progress issue's notes count; a brief with no note, and one whose `origin` is not on GitHub, equal today's and make no `gh` call; a failing `gh` stops the brief with a problem; a team's brief reads them from its worktree. `status` gives `notes`, with a note recorded after PR 1 or PR 5 opened marked late. |

### 14.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: a stage read from the PR title instead of `origin/main`, the order line not checked, PR 2 of the third feature merged by F07, `troy_approves_first` off by one, rounds counted from every comment, `[roles]` read from the working tree, effort passed when unset, a dirty tree accepted by `snapshot`, the Developer's scope with the `tests` class, AR2 allowed to change the whole design, a dependency change allowed without `--allow-dependency`, another role's log lines reported, `approve` raising only the English file, and `--worktree` leaving a staged file in the index. Part 2's include: PR B offered before PR A merged, a stage PR continued before its side PR, a redo that leaves the later stages counted, the mock skipped with an interface in section 2, a code task without `--worktree`, a fixed bug given a brief, `check-skips` passing a failure that is not a skip, and a member's stale lock missed. D201 adds: the note with exit 0 kept, the mirror written before the English file's table is checked, and the check made on the English file only, in `approve`, `accept-version`, and `rule-row`. D202 adds: an accepted ADR left proposed in its mirror, its header left as it was, an ADR that is already accepted raised again, the architecture's table cell left as it was, an ADR the architecture does not list accepted, and a refused ADR that still lets the architecture be written. D204 adds: no check counted as a pass, a pending check counted as finished, the head not compared, an older run of a check counted, no settling, `SKIPPED` counted as a failure, a commit status ignored, a failure reported before every check has finished, the timeout ignored, and one failing gh call ending the wait. F05's D231 adds: a record that is not stopped counted as closed, a record from before the snapshot counted, `snapshot` passing with an open record, `running` setting `escalate`, and the `running` problem given an undo. D261 to D263 add: each failed run counted instead of each commit, an older run of a workflow counted beside a newer one, a cancelled run counted as failed, runs from before the PR opened kept, a checkout failure counted as the author's, a `Commit:` line ignored, a comment without one counting a commit that failed after it was posted, one comment counting two commits, the CI count added to the number of comments instead of the highest number, and a failing `gh run list` stopping `status`. D264 to D267 add: a message's repeated records counted again, a 1-hour cache write priced as a 5-minute one, fast speed priced as standard, an unpriced model counted at zero without a word, a helper counted as a role run of its own, a run of another item counted, main-session messages after the end counted, a worktree's folder not read, a model ID in the description, and the price note given at any difference. D205 to D207 add: CR1 at PR 4 given PR 3's text, CR1 in a test-fix side PR given PR 5's text, CR1 at PR 3 given PR 5's text, the Python sentences in a C/C++ brief, and the redo of PR 3 given no text. F04's D280 to D283 add: a deleted line counted as a sign, a test file's subprocess call counted, a CMake line that adds the project's own file counted as a dependency, the C/C++ lists used for a Python project, the diff taken from `origin/main` rather than from the merge base, the sentence left out of a bug's CR1 brief, and CR2 briefed off the review branch. D284 to D287 add: a note for another feature added to a brief, notes added to TM1's brief, a note on a closed progress issue skipped, a failing `gh` read as no notes, a `gh` call made for a repository whose `origin` is not on GitHub, a note recorded after PR 1 opened not marked late, `note` accepting an accepted feature, and the notes out of order. D288 adds: D207's DV2 text back, a sentence of the new text dropped or a word of it changed, DV2's text at PR 4 too, for Python only, given to DV3, or given twice, and CR1's text at PR 5 given DV2's. The counts go in the PR description.

### 14.3 Trial (D68)

Before each part's PR opens, F07 runs in nested `claude -p` sessions on Troy's PC, with troy-pstack loaded from the PR branch through `--plugin-dir`, on the private scratch repository `ZJUCao/troy-mode-trial`. That repository already holds setup, a 1.0 architecture, and the Python pack, from F06's trial. The environment lives at a scratch prefix through `TROY_MODE_ENV_PREFIX`, and the trial's prompt gives Troy's answers. These sessions reach GitHub, so the trial starts only after Troy says yes in chat. Claude Code's auto mode refuses them otherwise.

Part 1:

1. **Upgrade and roles.** troy-init's upgrade brings the new troy-check into the trial repository, through its own PR. A prepared `[rules]` PR then sets one role's `effort` in `[roles]`.
2. **Outside troy-mode.** A request in an empty folder offers setup and changes nothing.
3. **Requirements.** "Start the project: count words in text files." PM1 writes requirements with two small features. F07 merges them after Troy's approval in chat.
4. **A break.** "Next feature" opens PR 1 of the first feature, which waits for Troy. That session ends.
5. **Resume.** A new session, in a git worktree of a fresh clone with no progress file, gets "continue" and Troy's approval. It rebuilds the state from GitHub, merges PR 1, and takes the feature through PR 2 to PR 6 with green CI.
6. **Routing.** "Release v0.1" and "add a rule" say that the flow is not built. "Why does ..." gets an answer, with no branch and no PR.
7. **Facts.** From the transcripts: the Agent calls carry the model and effort of `[roles]`, F07 waited for each writing role, `gh pr merge --delete-branch` works from a detached worktree, and whether Claude Code's permissions in `-p` mode let `gh pr merge` through. If a fact differs from this design, the design is updated in the same PR.

Part 2 runs a bug through PR A and PR B, a requirement change that reaches the accepted feature through the new feature's PR 1 and PR 2, and a dependency request that Troy refuses. Part 1 takes about 12 role runs and part 2 about 14, plus a few minutes of Actions per PR. The repository stays. Deleting it is Troy's call.

### 14.4 Status

| When | F07's status in requirements 7.2 |
| --- | --- |
| Part 1 merges after a passing trial | Runs on a sample project, part 1 of 2: troy-mode wrote the requirements of a scratch GitHub project and took one feature through its six PRs with green CI, across a session break. Bug fixes, requirement changes, and the loop's side PRs are not built. |
| Part 2 merges after a passing trial | Runs on a sample project: as part 1, plus a bug fix and a requirement change. Not yet used on a real project. |
| The pilot (F11) runs on troy-mode | Used on a real project |

If a trial cannot run before its PR, the status is "Written, part n of 2" until it does. F07 lands in two PRs (D67), each with one commit and its tests written first:

1. **Part 1.** The engine, the troy-check and troy-init changes of section 12, and the skill with routing, setup, the feature loop's main path, work outside the pipeline, and continuing.
2. **Part 2.** The side PRs and the series lock (section 8.7), bug fixes, and requirement changes.

Each status update is its own PR.

The mock notes of section 6.4 add one sentence to F07's status once their build merges after a passing role exam: they passed the role exam on scratch copies of the pilot's states, and have not run on a real project yet. That update is also its own PR.

**Attempts from CI (D261 to D263).** Before the build PR opens, `retro --tag v0.1.0` runs on a fresh clone of `ZJUCao/recipe-menu` in a scratch folder, where gh only reads GitHub. It must count the four failed pushes of #52 and #59 as Interface Designer attempts, with #59's one comment counting one of them, and no attempt for the checkout failure on #87. The build PR then adds one sentence to F07's status in requirements 7.2: attempts are counted from CI runs too, checked on the pilot's PRs, and not yet used while a project runs. For this change the status moves in the build PR rather than in a PR of its own, because every check runs before the build PR opens.

**Role runs and cost (D264 to D267).** Before the build PR opens, `costs` runs on a fresh clone of `ZJUCao/recipe-menu`, with `--transcripts` naming the pilot's transcript folder, which it only reads. `costs --tag v0.1.0 --until 2026-11-16T10:40:00Z`, the end of the pilot report's count, must give that report's table of section 5.2: the same runs per role, and the same cost per role within $1. The build PR then adds one sentence to F07's and F08's statuses: the cost report is checked on the pilot's transcripts and not yet used while a project runs. As for D261 to D263, the status moves in the build PR.

**Notes for later features (D284 to D287).** Before the build PR opens, a short trial on `ZJUCao/troy-mode-trial`, under Troy's standing permission for trials there, records a note for a feature that has not started, then renders its IF1 brief from a team's worktree and from the home checkout, and checks that both hold the note. It runs no role. The trial ran on 2026-11-24: in a local clone of `ZJUCao/troy-mode-trial`, whose features are all accepted, a local-only `origin/main` added a dummy feature F99. `note --for F99 --from "#74, Code Reviewer, round 1"` picked F06's closed progress issue #64, the comment was posted there as a labelled trial note, the IF1 briefs of F99 from the home checkout and from `.troy-teams/f99` both held it, and `status` listed it with `late` empty. The clone needs `core.longpaths` on Windows. Once the build merges, its status PR adds one sentence to the statuses of F07 and F15 in requirements 7.2: notes for later features live on the progress issues and reach those features' design and implementation briefs, checked by tests and a trial, and not yet used on a real project.

## 15. Not in F07

- The version release flow (F08), the rule change flow (F09), troy-pstack's documentation (F10), and the pilot (F11).
- PRs in the other members of a series (D66).
- Roles in parallel worktrees, or two features at once.
- R21's troy-check branch check in CI, a later change to F02.
- The TypeScript/JavaScript pack (Q1).
- Deleting the trial repository.

## 16. Decisions for Troy

F06 ends at D56, so F07 continues from D57.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D57 | How is F07 built? | A: the skill holds the judgment: routing, talking with Troy, reading reports, and writing documents as the Product Manager. An engine that uses the standard library does the exact jobs: the state, the briefs, the check after each run, and approvals in headers (section 3). B: the skill alone, with every step in its instructions. | A. Stage order, merge rights, round counts, and write scopes are exact rules that tests can check, and requirements 5.8 prefers a check to an instruction. It matches F06 D47. |
| D58 | Where does the flow's state live? | A: in git and on GitHub: commit subjects on `main`, open PRs, and F07's comments on them. The progress file is a view that F07 rewrites, and rebuilds when it is missing (section 5). B: in the progress file alone. C: in a committed state file. | A. The desktop app often starts a session in a new worktree, which has no progress file, and a long conversation gets compacted. With A the flow still continues. C needs a PR for each update, which Q8 rejected. |
| D59 | A run changed a file outside the role's scope, and F05's hook did not get it undone. What then? | A: F07 undoes the run's changes, which the clean tree before each run makes safe, and runs the role once more with the paths in Input. A second time in the same stage escalates. A changed `HEAD` or branch escalates at once (section 7). B: stop and escalate at once. | A. Undoing is mechanical and loses nothing that existed before, so Troy is asked only when it happens again. |
| D60 | `troy-check code` reads commits only, and roles cannot commit (F05 section 12). How does an author check R04 to R11 before it reports? | A: `troy-check code --worktree` checks the working tree as if it were a commit (section 12). F07 still runs `troy-check code` on the real commit before each push. B: only F07 runs it, after committing, and sends failures back in a new run. | A. A role run costs far more than a check. With A, the Developer fixes R04, R05, R07, and R11 inside its own run. B adds a run for each finding. |
| D61 | How does Troy approve the requirements, the architecture, and PR 1 and PR 2 of the first features? Requirements 3.3 and R18 say that Troy merges them. | A: Troy replies in chat or merges on GitHub. On a reply, F07 records the approval in the document's header (the next major version) and merges. After a GitHub merge, F07 records the approval in a small `[docs]` PR (section 8.6). B: Troy merges on GitHub only. | A. Approving is Troy's decision, and the click is not. It is also how Troy works in troy-pstack. With B, every approved document needs that follow-up PR, because a merge on GitHub cannot raise its version. This changes 3.3 and R18 in the requirements. |
| D62 | How does F07 know which features are "the first features" (Q2), and what Troy decides after them? | A: `[flow] troy_approves_first = 3` in the config. After the last of those features is accepted, F07 asks Troy once, and a `[rules]` PR records the answer (section 8.6). This is the only config change F07 makes. Other rule changes wait for F09. B: always 3, then F07 merges everything without asking. C: F07 asks before each feature. | A. Q2's "then Troy decides" lands in a file that every session reads, and it changes only when Troy says so. |
| D63 | How far does one request go? | A: one feature, bug, or change, unless the request names more ("F04 to F06", "the rest of v0.1"). B: on through the whole version. | A. Each feature ends at a natural stop where Troy sees the result, and a request can still ask for more. |
| D64 | Requirements 5.7 limits implementation attempts to 3. Other authors, such as the Developer's mock and the Test Engineer's tests, have no limit. | A: every stage allows 3 attempts. An attempt is a `failed` report, a `done` whose checks fail, or a CI failure in the author's files (section 8.5). B: count DV2 only, as 5.7 says now. | A. Without a limit, a stage can loop and spend money until someone notices. This changes 5.7's third trigger to "An author's work still fails its checks after 3 attempts." |
| D65 | How does a requirement change reach a feature that is already accepted? troy-check requires that feature's tests to pass, so its loop cannot simply start again. | A: PM2 adds a new feature for the change, with a hard dependency on the old one. Its tests PR retires the old tests that the change makes wrong and adds new ones, and F07 skips its mock PR when it adds no interface (section 11.2). B: F07 escalates every such change until a later feature designs it. | A. The rules and troy-check stay as they are, and the history shows the change as its own feature. This adds to 5.4 in the requirements. |
| D66 | F03 left a series' lock to F07: after a dependency change, every member's tests run in the shared environment, and the other members get the new lock in their own PRs. How much does F07 do? | A: F07 compiles the lock, installs it, runs every member's tests, and lists the members whose lock is now stale. It opens no PR in other repositories. B: F07 also opens a `[rules]` PR in each member that is a troy-mode project. | A. Nothing happens outside the project without Troy, and no series has a second troy-mode member yet. B can come with the first such series. |
| D67 | How does F07 land? Q10 says one PR per feature. | A: two PRs (section 14.4). Part 1 has routing, setup, the feature loop's main path, and continuing. Part 2 has the side PRs, bug fixes, and requirement changes. B: one PR. C: two PRs by layer, the engine first and the skill second. | A. Part 1 is already usable for setup and features, and each PR stays reviewable. C leaves nothing usable after the first PR. This adds F07 to Q10's exceptions. |
| D68 | How is F07 tried out, and when does its status move? | A: tests and planted bugs, plus a trial of each part on `ZJUCao/troy-mode-trial`, including a session break and a resume in a fresh worktree (section 14.3). B: the same, but on a local bare `origin`, so no PR or CI really runs. Status "Written" until the pilot. | A. Only a real repository shows that reviews, CI, and merges run end to end. It costs about 26 role runs in all and a few Actions minutes, and each part's trial starts only on Troy's yes in chat. |
| D69 | A case of the test plan runs on one platform only, so the local `troy-check code` fails on Troy's PC while CI passes (found in part 1's trial). How does F07 merge? | A: when the only local failures are tests skipped on this platform, F07 counts no attempt, lists those cases in the PR, and merges on CI's result (section 8.6). B: escalate each time. C: forbid such cases; the Test Manager writes every case to run everywhere, or puts it under "Not tested". D: troy-check stops counting a skipped test as a failure. | A, approved by Troy on 2026-11-07. CI passing proves the tests ran. B asks Troy on PR 4 and PR 5 of every such feature. C loses tests of real behavior. D would also pass in CI, so a test skipped everywhere would never be checked. Requirements need no change, because R09 and R10 are CI rules. |
| D201 | In the pilot (ZJUCao/recipe-menu#2), the Chinese requirements named their change log `变更记录` in place of the template's `修改记录`. `approve` found no change-log table there, added the approval row to the English file only, and exited 0 with a note. What do `approve`, `accept-version` (F08), and `rule-row` (F09) do when either file of the pair lacks the change-log table? From tstack issue #46. D70 to D200 belong to later designs, so this decision takes D201. | A: exit 1 and change neither file; the problem names the file and the headings looked for. B: keep the note and exit 0. C: A, and R12 or R20 also checks that a document's section headings match its template in each language. | A, approved by Troy on 2026-11-18. An approval is then recorded in both languages or in neither. `rule-row` already refused such a pair (F09 design 3.3); its problem now names the headings too. C's heading check is not part of this decision. No requirement changes: requirements 3.3 already says that the approval goes into the change log. |
| D202 | In the pilot (ZJUCao/recipe-menu#3), `approve` of the architecture changed only its header and change log. Its decision records table and the Status section of each of its seven ADRs, in both languages, still said "Proposed". The Product Manager's own edit was refused by `check-run`, since the architecture is outside its scope, and AR1 ran a second time only to change the words. From tstack issue #47. | A: `approve --doc docs/architecture.md` also sets the Status of the ADRs that the architecture lists to Accepted, in both languages, and the architecture's own Status cells with them. B: the architecture and ADR templates keep their status only in the front matter, so `approve` is enough. | A, approved by Troy on 2026-11-18. It saves one Architect run per architecture approval with ADRs, and the engine already owns the status words in headers. B would change F01's templates, which F16's role exam measures. Only ADRs still proposed change; accepted and superseded ones stay. ADRs that a feature design proposes are not covered. No requirement changes. |
| D203 | In the pilot, Troy typed "Start v0.1". troy-mode took F01 through its six PRs and stopped with "Next is F02", and Troy then typed one request per feature. The routing table gives "the rest of v0.1" as a request that reaches every feature of the version (D63), but "Start v0.1" also names a version. From tstack issue #52. | A: a feature-loop request that names a version reaches that version's remaining features. B: keep the reach as it is, and the report after a feature's acceptance says how to ask for the rest of the version. | A, approved by Troy on 2026-11-18. Each PR still needs Troy's approval where it does today, so only the number of requests changes. The reach stops before the release, which stays its own request. No requirement changes: D63 lives in this design and the skill. |
| D204 | In the pilot (ZJUCao/recipe-menu#47, 2026-11-12), a PR merged right after a push: `gh pr checks 47 --watch` printed "no checks reported" because GitHub had not registered the workflow yet, and the merge, chained after it with `;`, ran anyway. The pilot's main session then kept a script of its own that waits for the checks of the pushed head. From tstack issue #68. | A: an engine command, `wait-checks --pr <n> --sha <head>`, that waits until every check of that head has registered and finished and reports pass or fail with its exit code; the merge step uses it with `gh pr merge --match-head-commit <head>` and never chains the merge with `;`. B: the skill's merge step names that wait in words and forbids chaining. | A, approved by Troy on 2026-11-18. An exit code is a check, and requirements 5.8 prefers a check to an instruction. Waiting for CI inside a troy-mode project is part of troy-mode's merge step. No requirement changes: R18 already says that troy-mode merges once the checks pass. |
| D205 | Which note does a class's constructor get? tstack #63 gives "The mock leaves out the constructor's checks." and, for a constructor that also changes its values, "The mock keeps the values as given and leaves out the constructor's checks." In F16's trial, exam 2026-11-19-5 used that text: all five head runs then wrote a `UsageError.__init__` that stores its values, which breaks the Developer's step 2 and the must check `mock_bodies_only_raise`. The second sentence is true only of a constructor that the language generates. F16 design 14.6 left this to #63's design. | A: #63's two sentences, for every class. B: #63's two sentences only for a constructor that the language generates, such as a dataclass's; a constructor that the class writes only raises, like every other body, and the class's doc comment gets "The mock's constructor raises ``NotImplementedError``." C: as B, but a class that writes its own constructor gets "The mock leaves out the constructor's checks." D: a mock's constructor may keep its values; DV1's step 2, CR1's mock review, and dv-mock-notes' `mock_bodies_only_raise` change with it. | B, approved under Troy's standing yes of 2026-11-22 for small issues. B's new sentence is true of every constructor that a class writes, whatever it checks or changes; C's says nothing of a sort or a conversion, such as `UsageError`'s values sorted by name. A failed all five runs on this point, and D changes the mock rule and a case. Exam 2026-11-19-8, whose text named a sort, still lost two of seven head runs on `UsageError`: one left the class's doc comment without a note, and one gave `__init__` a body. B's sentence for the class, and "a constructor that the class writes too", aim at both. |
| D206 | Does the Code Reviewer's agent file change? tstack #63 adds to CR1's step 4 "and in a mock or implementation PR, the mock's notes as the brief gives them". The brief already gives the check at PR 3 and PR 5. The agent file is read in every CR1 run, so that line would also make cr-test-review, a review of a PR 4, an affected case (F16 design 9.2). | A: change it as #63 says. B: leave the Code Reviewer's agent file as it is, and let the brief carry the check where it applies. | B, approved under Troy's standing yes of 2026-11-22 for small issues. The line adds nothing that the brief does not say. Leaving it out keeps cr-test-review's ten opus runs, about $31 with their judge pass at the trial's median of $2.95 a run, out of the build's exam: its first round is then about $37 in place of about $68, under the $60 line of F16 D158. The Developer's agent file still changes, since its two cases run anyway. |
| D207 | What may PR 5 change in the feature's doc comments? tstack #63's DV2 text says "change nothing else in those doc comments", and its CR1 text at PR 5 checks "that nothing else in those doc comments changed". But the pilot's own F08 implementation, the pass anchor of the case dv-impl-notes, adds `os.path.isfile` to the probes that a doc comment lists, because the code calls it, and that case's criterion 1 asks for doc comments that are true of the code (R05). | A: as #63 says. B: DV2 deletes the notes, and changes the rest of those doc comments only where a sentence is not true of its code; CR1 at PR 5 checks that no note is left and that every other change makes the doc comments true of the code. | B, approved under Troy's standing yes of 2026-11-22 for small issues; Troy approved the requirement clauses of rows PR 3 and PR 5 as written on 2026-11-22. Under A, a Developer whose code needs a call that the mock's doc comment leaves out must keep a false sentence. DV1 still asks for doc comments that describe the implementation, so PR 5 rarely needs more than the deletion. |
| D261 | tstack issue #73 (the pilot report's candidate T1, which Troy accepted on 2026-11-16): `status` and `retro` count attempts from F07's comments only, and in the pilot CI failed on four pushes in an author's files with one comment posted. Which pushed commits count, and how does a comment already count one? | A: every commit CI ran on for the PR counts at most once, decided by the newest run of each workflow on it; cancelled and running runs count nothing; a comment counts the commit its `Commit:` line names, and a comment without one counts the PR's newest pushed commit when it was posted, if that commit had already failed and no other comment counts it (section 8.5). B: A, but only the `Commit:` line counts. C: every failed run counts, re-runs and runs started by an edit of the description included. D: only the PR's last commit counts. | A, approved under Troy's standing yes of 2026-11-22. One push is one try of the author, so re-runs must not add attempts (against C), and a failure that the author fixed is still an attempt, which D misses: it is exactly the case of #52. B counts the pilot's #59 three times, because its comment came before the `Commit:` line existed, and counts twice whenever the main session forgets the line. A counts the pilot's PRs right: 2 on #52 and 2 on #59. |
| D262 | How is a failed run tied to the author's files, for each pack's job? | A: by the failed step. `Run troy-check`, and each step of the pack's job after `Install from the lock`, runs a check on the repository's files, so its failure is the author's. Any other failed step, such as the checkout, the environment's setup, `Install from the lock`, a cancelled or timed-out step, or a workflow troy-mode did not write, is no attempt, and F07 stops and tells Troy (section 8.5). B: by the log: read `gh run view --log-failed` and look for the paths the PR changed. C: every failed run is an attempt. | A, approved under Troy's standing yes of 2026-11-22. The PR holds only its stage's work on a `main` whose checks passed, so a check step that fails there fails on that work. B misses an implementation that fails tests, since pytest's log names only the test file, which is the Test Engineer's, and it downloads a log for each run. C counts the pilot's "Repository not found" on #87 (guide section 8.6). The step names come from troy-mode's own workflow files, and a test checks the list against them. |
| D263 | Does a failure that `status` counts also get its comment afterwards, so the PR shows it? | A: yes. `status` gives each open PR's failed commits in `ci_failures`, with the attempt number each uncounted one takes; F07 posts `<Role> attempt <n>: failed` with the line `Commit: <commit ID>` before it goes on, and the count stays the same. `retro` posts nothing (section 8.5). B: no. `status` counts it, and the PR shows fewer attempts than the count. | A, approved under Troy's standing yes of 2026-11-22. GitHub holds the flow's state (D58), so Troy, a new session, and the retrospective then read the same attempts from the PR. Numbering the late comment with the count `status` gives keeps the count the same before and after it is posted. `retro` changes nothing (F08 section 3.1), so a merged PR's failures appear only in its report. |

| D264 | tstack issue #74 (the pilot report's candidate T2, which Troy accepted on 2026-11-16): each acceptance PR and release PR gives its role runs and their cost, read from the session transcripts. Where are the transcripts found, and what happens when a feature spans sessions or PCs? | A: `costs` finds them itself, in the transcript folders of the main checkout, its worktrees, and the desktop app's removed worktrees; a role run belongs to the item its brief's `Item:` line names, in any session; sessions are summed; the report says it reads this PC only and names each stage with no run found (section 8.8). B: the skill passes the ID of each session it ran in. C: the main session records each run's tokens as it goes, in the progress file or in a PR comment. | A, approved under Troy's standing yes of 2026-11-22. Nothing has to be remembered: the pilot's version already spans two session files, and B loses a session after every restart. C costs a step after every run, is lost with the progress file, and the Agent tool's result gives no tokens by kind, so its price cannot be right. A run on another PC is rare, since Troy works on one PC, and the stages without a run show where one is missing. |
| D265 | Where does the price table live, and who updates it? | A: `troy-mode/flow/prices.toml` in the plugin: dollars per million tokens for each token kind and model, a fast table where there is a fast mode, the price of a web search, and the date the prices were read; a tstack PR updates it when a list price changes or a new model comes (section 8.8). B: a `[prices]` table in each project's `.troy-mode/config.toml`. C: the engine reads Anthropic's pricing page each time. | A, approved under Troy's standing yes of 2026-11-22. One table serves every project and changes with the engine that reads it, and tests can check it. B needs every project's config updated by hand, and troy-check's config reader would have to learn the table. C needs the network and a page format that can change, and the engine reads nothing but git, GitHub, and the transcripts. |
| D266 | Does the report show the session's own running cost when the desktop app records one? In the pilot it was within 2% of the computed figure. | A: no figure from the app in the PR; `costs` prices the token counts of the newest `cost-state` record with its table and adds a note when a model differs by more than 1%, which means the table is out of date (section 8.8). B: show the app's figure next to the computed one. C: ignore the records. | A, approved under Troy's standing yes of 2026-11-22. The record is one app run's running total across every feature, with no time on it, so it cannot be cut to a feature or a version. As a check of the prices it is exact: the pilot's records give the table's Opus 5.5, Sonnet 5.5, and Haiku 5.5 prices to the cent. |
| D267 | Does F14's summary for Troy carry a one-line cost? | A: no. The cost goes in its own section of the acceptance and release PRs' descriptions, and one line of the report to Troy (section 8.8). B: a line in PR 1's summary with the feature's cost so far, or the last feature's. | A, approved under Troy's standing yes of 2026-11-22. The summary opens PR 1, PR 2, the requirements, and the architecture, not the acceptance or release PR, and a feature's cost is known only at its end. The summary's template and the skill's section "The summary for Troy" are in F16's instruction set, so B would change what roles write and need a role exam. |
| D284 | tstack issue #67, a problem of the F11 pilot: reviews leave notes for later features, and `status --note` keeps a note only while the feature and the stage stay the same. Where do such notes live, so that they reach the right feature's briefs on any PC, in F20's team worktrees, and after `team end`? | A: troy-mode's `Note for <ID>, from <source>` comments on the progress issues: the source feature's, or for a note from chat or from work outside a feature, the target's, else the next feature's (section 6.6). B: a comment on the PR whose review found it. C: one notes issue for the project, with its own label. D: a tracked file per feature, `docs/features/<id>-<slug>/notes.md` and its mirror, landed by `[docs]` PRs. E: `status --note --for <ID>`, kept in the flow state until the feature's stage 1 starts. | A, approved under Troy's standing yes of 2026-11-22. It lives on GitHub with the rest of the state (D58), so a new PC, a new session, a team's worktree, and `team end` lose nothing, and `status` already reads every issue with its comments. B needs every merged PR's comments read, and a note from chat has no PR. C adds a fourth kind of issue and label, which changes the F15 row of the requirements. D needs a PR, a mirror, and CI for each batch of notes, of which the pilot had several dozen, and F20 keeps shared documents out of the teams (D277). E stays on one PC, which is the pilot's problem. |
| D285 | Who records a note, and how? | A: the main session, from any role's report or from Troy in chat, in its own words, with the engine's `note` command, whose comment the skill checks and posts (section 6.6). B: a new report field, `Later:`, in every role's Report section, which the engine reads. C: as A, and the reviewers' agent files ask them to start such a finding with `Later <ID>:`. | A, approved under Troy's standing yes of 2026-11-22. The main session already reads every report, and the pilot's notes came that way. B changes `common.md` and every agent file, so all twelve exam cases would run: $255.43 for the first round by troy_exam's budget code. C changes three agent files, and their six cases would cost $159.30. |
| D286 | Which briefs get a feature's notes? | A: every IF1, IF2, and DV2 run of the feature, in its Input, with a sentence per task; none when the feature has no note (section 6.6). B: the note names its stage, design or implementation, and only that author's brief gets it. C: every author's brief of the feature. | A, approved under Troy's standing yes of 2026-11-22. The pilot copied each note into an IF1 or a DV2 brief. Giving both every note leaves the main session no stage to judge, and DV2's sentence puts the approved design first where they differ. C adds notes that TM1, DV1, and TE1 do not act on. |
| D287 | How does troy-mode see that a note reached its briefs? | A: `status` gives each note with what it can still reach, by when it was recorded against the opening of the feature's PR 1 and PR 5, and marks a late note; the main session decides what a late note needs and tells Troy (section 6.6). B: nothing beyond `brief` adding the notes. C: a late note stops the feature until Troy decides. | A, approved under Troy's standing yes of 2026-11-22. `brief` adds every note it finds, so only a note recorded after a stage's runs can miss it, and A names exactly those. C stops a team for a note that the merged work may already follow. |
| D288 | A hillclimb step on the case dv-impl-notes (F16 design 8.3), which section 6.4 proposes when that case does not pass. D207's DV2 text says to change the rest of the doc comments "only where a sentence is not true of the code you write". In exam 2026-11-22-3, all 10 runs, with and without that text, kept the sentence "Besides the probes ``os.path.isdir`` and ``os.path.lexists``, the call reaches the disk only through ...", which leaves out `os.path.isfile`. The code reaches that probe through a helper in `_listing.py`. How does DV2 get the Developer to check such a sentence? | A: DV2's text says how to check (section 6.4). The Developer checks each doc comment of the code it writes or changes, the sentences it did not change too. What a called function does counts, in any file. A sentence is not true when it names a call, a file access, or an exception that the code does not make, or when a full list ("only", "every", "besides") leaves one out. Nothing else in those doc comments changes. B: the same check as a new step of DV2 in the Developer's agent file, with D207's text as it is. C: as A, and the text also moves a sentence that follows the Args, Attributes, Returns, and Raises sections into the description, the case's criterion 3. | A, approved under Troy's standing yes of 2026-11-22. It makes the sentence that already asks for true doc comments say how to check them, on the Task line, and only dv-impl-notes is affected, so the exam costs about $10, or $20 with a second round. B also affects dv-mock-notes, because the agent file is that case's input too, and leaves the weaker sentence in the brief. C changes what row PR 5 of requirements 5.2 says: the rest of a doc comment changes only where the code makes it untrue. Criterion 3 is not a must. |

D261 to D263 change no requirement: D64 already counts a CI failure in the author's files as an attempt (requirements 5.7). D264 to D267 change no requirement either: the report is part of the acceptance and release steps that F07 and F08 own, as D204's wait is part of the merge. D284 to D287 change none: the notes are state on GitHub (D58) and Input of a brief, and the progress issue keeps its six boxes and its life (F15 D142). D288 changes none: row PR 5 of requirements 5.2 already says that the rest of a doc comment changes only where the code makes it untrue, and D288 says how the Developer finds those places.

D205 to D207 design tstack issue #63, whose rule Troy accepted on 2026-11-16 (ZJUCao/recipe-menu#94, AR6 option A). Requirements 1.55 gives rows PR 3 and PR 5 of its section 5.2 a clause each, and section 6 gets no new row. Troy approved both clauses on 2026-11-22.

F05's D231 (F05 design section 6.1), which Troy approved on 2026-11-21, changes sections 6.2 and 7 and the entry skill's section "Running a role", and adds one clause to the F07 row of requirements 1.52 (F05 design section 15). F07 takes no decision of its own for it.

Requirements 1.20 records the approved changes:

- The F07 row: the engine and the skill, the state in git and on GitHub, the check after each run, `troy-check code --worktree`, and the two parts (D57 to D60, D67).
- 3.3, the merge column of the 5.2 table, and R18: Troy approves in chat or by merging, and troy-mode merges after an approval in chat (D61). R18's row in troy-mode's rules templates changes with it.
- 5.7: the attempt limit for every author (D64).
- 5.4: a change to an accepted feature becomes a new feature (D65).
- Q10: F07 lands in two PRs (D67).

## 17. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-07 | First draft. |
| 1.0 | 2026-11-07 | Approved by Troy with D57 to D68, every recommended answer. |
| 1.1 | 2026-11-07 | Facts from part 1's trial (section 14.3): the Agent calls carry `[roles]` and the session waits for writing roles (section 1); the skill runs the engines, git, and gh through Bash (section 2); IF1 keeps section 4 free of template markers (section 6.1); the feature's name stays short (section 8.1); and `gh pr checks --watch` may need a second start right after a push (section 8.6). |
| 1.2 | 2026-11-07 | Troy's D69: tests that run on another platform only are left to CI (section 8.6). Details part 2 settled: `brief --title`, `check-skips`, and `series` (section 3.1); history order, bugs, and side PRs first in the state (section 5.1); who writes each side PR (section 8.7); bug branches (section 11.1); rework, the redo, the skipped mock, and the change's approval (section 11.2); part 2's tests and planted bugs (sections 14.1 and 14.2). From part 2's trial: an escalation with no open PR goes on the bug's issue (section 9). |
| 1.3 | 2026-11-08 | From F08 design section 9: "release" requests go to F08's version release flow (section 4); `status`, `brief`, and `approve` change as F08 section 3 says, and `approve` adds a change-log row (D77, section 8.6); the rights gain the GitHub release (section 9). From F08's trial: every fetch prunes (sections 8.2 and 8.6). |
| 1.4 | 2026-11-08 | From F09 design section 8: "add a rule" requests go to F09's rule change flow (section 4); the engine gains `rule-id`, `rule-row`, the `rules` snapshot role, a `check-run` rule for dependency changes that only delete `baseline:` lines, and the `cleanup` action; the skill reads the P rows of type Process at every start. |
| 1.5 | 2026-11-09 | Section 6.1: the brief finds mamba on the PATH or in `$MAMBA_EXE` only, as built. Found by F10's facts review, together with two skill sentences and the Product Manager's PM2, which now say what F09 and D65 decided: the rule change flow changes the config too, and an accepted feature keeps its status after a change. |
| 1.6 | 2026-11-18 | D201, from tstack issue #46, approved by Troy on 2026-11-18: `approve`, `accept-version`, and `rule-row` exit 1 and change nothing when either file of the pair has no change-log table (sections 8.6, 14.1, 14.2, and 16). |
| 1.7 | 2026-11-18 | D202, from tstack issue #47, approved by Troy on 2026-11-18: approving the architecture also accepts the ADRs it lists that are still proposed, and their Status cells in its table, in both languages (sections 3.1, 8.6, 14.1, 14.2, and 16). |
| 1.8 | 2026-11-18 | D203, from tstack issue #52, approved by Troy on 2026-11-18: a feature-loop request that names a version, such as "Start v0.1", reaches that version's remaining features, and stops before the release (sections 4, 14.1, and 16). |
| 1.9 | 2026-11-18 | D204, from tstack issue #68, approved by Troy on 2026-11-18: the engine's `wait-checks` waits until every check of the pushed head has registered and finished, and the merge runs on its own after it, never chained with `;` (sections 3.1, 8.6, 14.1, 14.2, and 16). |
| 1.10 | 2026-11-21 | F05's D231, from tstack issue #49, approved by Troy on 2026-11-21: `check-run` and `snapshot` refuse with a `running` problem while a role, or a command it left in the background, still runs, and F07 ends each named agent with `TaskStop`. The desktop app runs every role in the background (sections 1, 6.2, 7, 14.1, 14.2, and 16). |
| 1.11 | 2026-11-22 | D261 to D263, from tstack issue #73, approved under Troy's standing yes of 2026-11-22: `status` and `retro` also count attempts from the CI runs of a PR's pushed commits, at most one per commit, only for a failed check step, and not when a comment already counts it; F07 posts the comment that was missed, with a `Commit:` line (sections 3.1, 5.1, 8.4, 8.5, 8.6, 14.1, 14.2, 14.4, and 16). |
| 1.12 | 2026-11-22 | D264 to D267, from tstack issue #74, approved under Troy's standing yes of 2026-11-22: the engine's `costs` reads the transcripts on Troy's PC and gives a feature's or a version's role runs and their cost at list prices from `prices.toml`, for a `## Cost` section in the acceptance PR and a line in the report to Troy; the desktop app's figure checks the prices; F14's summary carries no cost (sections 3.1, 8.8, 14.1, 14.2, 14.4, and 16). |
| 1.13 | 2026-11-22 | D205 to D207, from tstack issue #63, whose rule Troy accepted on 2026-11-16; the choices follow the recommended options under Troy's standing yes of 2026-11-22, and Troy approved the requirement clauses on 2026-11-22: at PR 3 and PR 5, the Task of DV1, DV2, and CR1 adds fixed mock-note text from the new `mocknotes.py`, chosen by `[lang] name`; a constructor that the class writes only raises and the class's doc comment says so; the Code Reviewer's agent file does not change; and PR 5 changes a doc comment beyond its notes only where the code makes it untrue (sections 6.1, 6.4, 14.1, 14.2, 14.4, and 16). |
| 1.14 | 2026-11-22 | F20's design (D268 to D279, approved by Troy on 2026-11-22): the engine gains `team`, `plan`, and `merge-check`, and `status`, `brief`, `snapshot`, `check-run`, `retro`, and `costs` learn several teams; one writing role at a time per team, the main session's loop over the teams, and merges in the order the PRs become ready, with rebases (R24); section 15's two features at once moves into F20 (sections 3.1, 5, 6.2, 7, 8.6, 8.8, and 15). The changes land with F20's build. |
| 1.15 | 2026-11-23 | F04's D280 to D283, from tstack issue #75, approved under Troy's standing yes of 2026-11-22: `brief` checks a CR1 PR's diff for a dependency, a subprocess call, network access, and credential handling, from lists per pack in the new `troyflow/risks.py`, and CR1's Task says whether to run `/security-review`; CR2's brief runs on a release's review branch (sections 6.1, 6.5, 14.1, and 14.2). |
| 1.16 | 2026-11-23 | D284 to D287, from tstack issue #67, approved under Troy's standing yes of 2026-11-22: a note for a later feature is the main session's `Note for <ID>` comment on a progress issue, made with the new `note` command; `brief` adds a feature's notes to the Input of its IF1, IF2, and DV2 runs, also in a team's worktree and after `team end`; `status` gives the notes and marks a late one (sections 3.1, 5.1, 6.1, 6.6, 14.1, 14.2, 14.4, and 16). |
| 1.17 | 2026-11-24 | What tstack #75's build settled: the sentence for a pack that `risks.py` does not know, and the problems of CR2's brief off the review branch (section 6.5). |
| 1.18 | 2026-11-24 | What tstack #67's build and its trial settled: `status`'s key `feature_notes`, a stage PR's opening from `createdAt`, `note`'s report, the origin read before `insteadOf`, disabled issues as no notes, `notes.py` reading `gh` itself, and the trial's run (sections 6.6 and 14.4). |
| 1.19 | 2026-11-25 | D288, a hillclimb step on the case dv-impl-notes (F16 design 8.3), approved under Troy's standing yes of 2026-11-22: DV2's text has the Developer check each doc comment of the code it writes or changes, the sentences it keeps too, through the functions that code calls, and fix a sentence that names what the code does not do or a full list that leaves something out. No requirement changes (sections 6.4 and 16). |
