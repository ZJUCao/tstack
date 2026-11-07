# F07 design: the entry skill (troy-mode)

| | |
| --- | --- |
| Feature | F07 in [requirements 1.20](../requirements.md#72-feature-list) |
| Version | 1.1 |
| Date | 2026-11-07 |
| Status | Approved by Troy on 2026-11-07, with D57 to D68. Version 1.1 records the facts the trial of section 14.3 settled for part 1. |
| Source of truth | This English file. [`F07-entry-skill.zh-CN.md`](F07-entry-skill.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F07 is the command Troy types for all work in a troy-mode project, `/troy-pstack:troy-mode <request>` (requirements 3.1). It delivers one skill and the engine behind it. With them, the main session:

1. routes each request to a flow (section 4);
2. runs the flows: project setup (5.1), the feature loop (5.2), bug fixes (5.3), requirement changes (5.4), work outside the pipeline (5.9), and continuing across sessions (5.10);
3. starts each role with its brief and with the model and effort from `.troy-mode/config.toml` (F04 D32), one writing role at a time;
4. checks after each run that the role changed only files in its write scope (F04 D31);
5. commits, opens PRs, posts reviews, counts review rounds and attempts, escalates (5.7), and merges within the merge rights (R17, R18);
6. keeps the progress file.

The version release flow (5.5) and the rule change flow (5.8) are F08 and F09. F07 routes those requests and says that the flow is not built yet. Sections 5.6 (when tests run) and 5.7 (escalation) are not requests. They are steps inside the other flows.

F07 lands in two parts (D67). Part 1 holds routing, setup, the feature loop's main path, work outside the pipeline, and continuing. Part 2 adds the feature loop's side PRs (disputed tests, coverage gaps, and new dependencies), bug fixes, and requirement changes.

The facts about Claude Code come from its documentation and from the F04 to F06 trials. Two of them shape this design. Claude cannot call a skill marked `disable-model-invocation: true`, so F07 runs troy-init's engine itself (F06 section 10) and follows a pstack skill by reading its `SKILL.md`. The Agent tool takes a `model` and an `effort` with each call, and in the desktop app a subagent runs in the background and reports when it ends. The trial (section 14.3) checks both. Part 1's trial confirmed them: every Code Reviewer call carried the `effort` that `[roles]` set and no other role got one, writing roles ran in the foreground so the session waited for each, and in `claude -p` the session went on when background reviews ended.

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
python troy_flow.py brief      --task <task ID> --item <feature or bug ID> [--round <n>]
                               [--input-file <path>] [common options]
python troy_flow.py snapshot   --role <role> [common options]
python troy_flow.py check-run  --run <run ID> [--allow-dependency <path>]... [common options]
python troy_flow.py approve    --doc <path> [--date <YYYY-MM-DD>] [common options]
python troy_flow.py check-text --file <path> [common options]

common options: [--repo <path>] [--json]
```

| Command | What it does |
| --- | --- |
| `status` | Reads the project's state (section 5) and prints it with the next action. `--write-progress` rewrites the progress file from it. |
| `brief` | Prints the brief for one role run (section 6.1) and the Agent tool's parameters: `subagent_type`, `model`, and `effort`. |
| `snapshot` | Records the state before a run (section 7) and prints its run ID. |
| `check-run` | Compares the state after the run with the snapshot (section 7). Prints the paths to stage, the problems, and how to undo each one. |
| `approve` | Records Troy's approval in a document's header and in its mirror's (section 8.6). |
| `check-text` | Checks a PR comment with troy-check's attribution rules, in the project's `[attribution] mode` (R19). |

- The engine reads git, and GitHub through read-only `gh` calls. It writes only the progress file, the header fields that `approve` changes, and its records in `<git dir>/troy-mode/flow/`. It never commits, pushes, or writes to GitHub. The skill does that (F04 D29).
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
| "next feature", "F04", "F04 to F06", "the rest of v0.1" | Feature loop | Section 8 |
| "bug: ...", "fix #12" | Bug fix | Section 11.1 |
| "change: ...", "the export should also ..." | Requirement change | Section 11.2 |
| "why ...", "how does ...", "try ..." | Work outside the pipeline | Section 11.3 |
| "continue", "status", or nothing | Continue | Section 11.4 |
| "upgrade troy-mode" | troy-init's upgrade (F06 section 6) | Section 10 |
| "release v0.1" | Version release (5.5) | Not built: F08 |
| "add a rule ..." | Rule change (5.8) | Not built: F09 |

- In a folder with no `.troy-mode/`, F07 answers a question but changes nothing. For any other request, it asks Troy once whether to make the folder a troy-mode project.
- When a request fits two flows, or none, F07 asks Troy one question with a recommended answer.
- **How far a request goes (D63).** One feature, one bug, or one change, unless the request names more, such as "F04 to F06" or "the rest of v0.1". Then F07 reports and stops.
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
| Review rounds, attempts, and what waits on Troy | F07's own comments on each open PR (section 8.4) |
| Attempts before a PR exists, and notes | The progress file only |

- `status` checks the order line against the dependency columns: every dependency must come earlier. A mismatch stops the feature loop and names the features. Fixing it is a requirement change.
- The next feature is the first in the order with no `accept` commit on `origin/main`.
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
- Commands run through `mamba run -n <environment>`, or `mamba run -p <folder>` when `TROY_MODE_ENV_PREFIX` is set. Trials set it, so they leave no named environment behind. mamba is found the way troy-init finds it (F06 design 5.4).
- A revision is a fresh run of the same task, or of IF2 for a design, with the findings in Input and the next round (F04 D33).

### 6.2 One writing role at a time

1. `snapshot --role <role>`. It refuses when the working tree has changes that git does not ignore. F07 commits after every writing run, so the tree is clean before the next one.
2. The Agent call: `subagent_type` and the brief from `brief`, plus `model` and `effort` when it gives them.
3. F07 waits for the role's report and does nothing else in the checkout meanwhile, because F05 blames every change during the run on the role (F05 section 6). Roles that only read may run together, such as the Test Manager's and the Code Reviewer's reviews of one test PR (F04 section 9.2). One snapshot covers them, and nothing may change.
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

## 7. The check after each run (D59)

`snapshot` records `HEAD`, the branch, and the time in `<git dir>/troy-mode/flow/<run ID>.json`. Because the tree was clean, every change `git status` lists after the run is the run's own. `check-run` looks for these problems:

1. **`HEAD` or the branch changed.** Roles cannot commit or switch branches (F05 section 7), so the hooks failed. F07 stops and escalates at once.
2. **A changed path outside the role's write scope** (F04 section 3). The check uses F05's scope table, troy-check's path classes, and the config at `HEAD`. Ignored paths do not count. For the Code Reviewer, any change is a problem.
3. **After AR2, a change to the design outside its section 4** (F04 D37). `check-run` compares the design and its mirror with `HEAD` section by section.
4. **A changed `dependencies` path not named with `--allow-dependency`.** F07 names only a dependency that Troy accepted (R16, 5.7, section 8.7).

`check-run` also lists the role's lines in `hooks.log` since the snapshot (F05 section 10). They do not stop the flow on their own.

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
2. **Branch.** `git fetch origin`, then `git switch -c <branch> origin/main`. F07 never checks out `main`. In a worktree that the desktop app made, `main` is often checked out in another worktree, and git refuses to check it out twice.
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
- `Developer attempt 2: failed`, then the failing checks;
- `Escalation: <trigger>`, then the message of section 9;
- `Waiting for Troy: approve this PR`.

GitHub does not let an account approve its own PR, and every role acts through Troy's account, so the heading records who did what (F04 D29). A comment without one of these headings is Troy's. F07 reads Troy's comments on an open PR and passes them to the author as Input. It checks each of its own comments with `check-text` before posting it.

### 8.5 Attempts (D64)

An attempt is an author run that reports `failed`, reports `done` while F07's local checks fail, or leads to a CI failure in the author's files. Each stage allows 3 attempts. After the third, F07 escalates (5.7). A revision whose checks pass is a round, not an attempt.

### 8.6 Merging (R18, F02 D14)

F07 merges a PR only when all of these hold:

- every review of the stage ended in `approved`;
- the local checks passed on the pushed commit;
- `gh pr checks <n> --watch`, run once, ends with every check passing. Right after a push, GitHub may not have registered the workflow yet, and the command then says that no checks are reported; running it again is still the same wait (found in the trial);
- the merge rights allow it. PR 1 and PR 2 of the first `troy_approves_first` features in the order wait for Troy (D61, D62). Every other PR is F07's to merge.

F07 then runs `git switch --detach`, `gh pr merge <n> --rebase --delete-branch --match-head-commit <sha>`, `git fetch origin`, and `status --write-progress`. It detaches first so that `gh` does not try to check out `main` before it deletes the branch.

- **A failing CI check.** The author gets the failing log (`gh run view --log-failed`) as Input, and the run counts as an attempt. When the failure lies outside the author's files, such as in the workflow or on the runner, F07 stops and tells Troy.
- **A refused merge.** If Claude Code's permissions refuse `gh pr merge`, F07 stops and tells Troy which permission to add. It never works around a refusal.

**Troy's approval (D61).** When a PR waits for Troy, F07 posts `Waiting for Troy`, tells Troy in chat with the link, and stops. Troy either replies in chat or merges the PR on GitHub.

- On a reply that approves, F07 runs `approve` on the PR's document. The `version` moves to the next major (F01 design section 4), `updated` becomes the date, and the status becomes "Approved by Troy on <date>" and its Chinese form. `approve` changes only these header fields, in both languages, so no role runs for it. F07 amends the commit, pushes, waits for the checks, and merges.
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

In part 1, each case in this section escalates to Troy and says that the side flow is not built yet.

## 9. Escalation (5.7)

| Trigger | How F07 finds it |
| --- | --- |
| A review loop reaches 3 rounds without agreement | Its round count (section 8.3) |
| A change needs the requirements or the architecture to change | A role's `escalate` report, or AR5's answer |
| An author's work still fails after 3 attempts | Its attempt count (section 8.5, D64) |
| A new third-party dependency | AR3's `escalate` report (section 8.7) |
| An irreversible action outside the merge rights | F07 checks before it acts. Its rights: push its own branches with `--force-with-lease`; open, edit, comment on, close, and merge its own PRs within R18; open bug issues; and delete its own branches after their PR merges. Anything else asks Troy. |
| A run changed `HEAD` or the branch, or broke its scope twice | `check-run` (section 7) |

The message follows F01's `escalation` template, in Troy's language: where it stopped, why, the facts with links, the options, and a recommendation (Prototype C). F07 also posts it in English on the open PR, writes "Waiting on Troy" into the progress file, and stops. When Troy answers, in this session or a new one, F07 puts the decision into the next brief's Input and goes on.

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

### 11.2 Requirement change (5.4, part 2, D65)

1. **PM2.** The Product Manager updates the requirements in a `[docs] Change the requirements: <summary>` PR. Troy approves it (section 8.6), and the affected features become "Needs rework".
2. **AR4.** The Architect lists the interfaces, tests, and parts of the architecture that change, with an ADR for an architecture change.
3. **A feature not yet accepted** goes back to the earliest stage that AR4 names. F07 closes the feature's open PR, if it has one, without merging it, and runs the loop from that stage.
4. **An accepted feature** gets a new feature for the change, which PM2 adds with a hard dependency on the old one. Its design lists the changed interfaces in section 3. Its test plan names the old cases that the change retires, and records them in the "Not tested" section of the old feature's test plan. Its tests PR deletes those tests and adds new cases, which fail against the current code (R09). Its mock PR holds only new interfaces, and F07 skips PR 3 when there are none. troy-check needs no change, because every test of the old feature that remains still passes.

Every existing test runs as regression, as on every PR (5.6).

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
| Approve and text | `approve` raises both languages to the next major and writes both status lines. `check-text` refuses attribution in strict mode. |
| troy-check | `[roles]` and `[flow]` are accepted. An unknown role, an unknown key, a wrong effort value, and a negative count are refused. `--worktree` sees new files, skips ignored ones, gives the same results as a real commit, and leaves the index, the refs, and the working tree as they were. |
| Skill | Front matter `name: troy-mode` and `disable-model-invocation: true`. It names every flow of section 4, every engine command, and the stage titles of section 8.1. |

### 14.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: a stage read from the PR title instead of `origin/main`, the order line not checked, PR 2 of the third feature merged by F07, `troy_approves_first` off by one, rounds counted from every comment, `[roles]` read from the working tree, effort passed when unset, a dirty tree accepted by `snapshot`, the Developer's scope with the `tests` class, AR2 allowed to change the whole design, a dependency change allowed without `--allow-dependency`, another role's log lines reported, `approve` raising only the English file, and `--worktree` leaving a staged file in the index. The counts go in the PR description.

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
