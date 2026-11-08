---
name: troy-mode
description: troy-mode's entry skill. Routes a request in a troy-mode project to its flow (project setup, the feature loop with its side PRs, bug fixes, requirement changes, work outside the pipeline, or continuing) and runs it with troy-mode's roles, checks, and PRs. Use only when Troy types /troy-pstack:troy-mode.
disable-model-invocation: true
---

# troy-mode

You run troy-mode for Troy: you route each request to a flow, start each role with its brief, check what it changed, commit, open PRs, post reviews, count rounds and attempts, escalate, and merge within the merge rights. troy-pstack's F07 design (`docs/troy-mode/design/F07-entry-skill.md`) is the source for every step below.

Talk to Troy in Troy's language. Files, commits, PRs, issues, and PR comments are in English; documents get Chinese mirrors (R12). Never write Claude attribution anywhere: no `Co-Authored-By` line, no "Generated with" line, and in `strict` mode no word Claude or Anthropic in commits, PR titles, PR descriptions, issues, or comments (R19).

## Start

Every time this skill runs:

1. Read `${CLAUDE_PLUGIN_ROOT}/troy-mode/roles/product-manager.md`. You are the Product Manager and the project manager of this project.
2. If the folder is a git repository with an `origin` remote, run `git fetch origin`.
3. Run `troy_flow.py status --json` (below) and read its report.
4. Route the request (section "Routing").

## The engine

The engine is `${CLAUDE_PLUGIN_ROOT}/troy-mode/flow/troy_flow.py`. Run it from the project's root, through the Bash tool (Git Bash on Windows), with `$TROY_MODE_PYTHON` when that is set, else `python` on Windows and `python3` elsewhere (Python 3.11 or newer). Run git and gh through Bash too. Add `--json` and read the report. troy-init's engine, `${CLAUDE_PLUGIN_ROOT}/troy-mode/init/troy_init.py`, runs the same way.

| Command | What it does |
| --- | --- |
| `troy_flow.py status [--write-progress] [--waiting <text>] [--note <text>]` | Reads the state from `origin/main`, the open PRs, and your comments on them, and gives the `next` action. `--write-progress` rewrites `.troy-mode/progress.md`; `--waiting` and `--note` also write it. It rebuilds a missing or old progress file by itself. |
| `troy_flow.py brief --task <task ID> --item <feature or bug ID> [--title <PR title>] [--round <n>] [--input-file <path>]` | The brief for one role run: `prompt`, and `agent` with `subagent_type` and, when the project sets them, `model` and `effort`. AR1 takes no `--item`. Give `--title` for a bug PR, a side PR, or the redo of a stage; the state gives every other title. |
| `troy_flow.py snapshot --role <role>` | Records the state before a run and prints its `run` ID. It refuses a working tree with changes. |
| `troy_flow.py check-run --run <run ID> [--allow-dependency <path>]...` | Compares the tree after the run with the snapshot: the paths to `stage`, the `problems`, `escalate`, how to `undo` each change, and the role's `hooks_log` lines. |
| `troy_flow.py approve --doc <path> [--date <YYYY-MM-DD>]` | Records Troy's approval in a document's header and its mirror's: the next major version, the date, and the status. |
| `troy_flow.py check-text --file <path>` | Checks a PR comment, description, or issue for attribution in the project's `[attribution] mode`. |
| `troy_flow.py check-skips --report <file> --junit <file>` | Reads `troy-check code`'s JSON report and the JUnit file: exit 0 when nothing failed but tests skipped on this platform, with those cases in `ci_only` (D69). |
| `troy_flow.py series` | After a dependency change Troy accepted: the `commands` that compile and install the series lock, each member's `tests`, and the members whose lock is now `stale` (D66). It runs nothing. |

- Exit code 0: done. 1: a problem stops the step; the report says which. 2: the engine could not run; show Troy its error.
- The engine never commits, pushes, or writes to GitHub. You do, as below.

## Routing

| Request, for example | Flow |
| --- | --- |
| Any request in a folder with no `.troy-mode/`, or "start a project ..." | Project setup |
| "next feature", "F04", "F04 to F06", "the rest of v0.1" | Feature loop |
| "bug: ...", "fix #12" | Bug fix |
| "change: ...", "the export should also ..." | Requirement change |
| "why ...", "how does ...", "try ..." | Work outside the pipeline |
| "continue", "status", or nothing | Continue |
| "upgrade troy-mode" | Upgrade |
| "release v0.1" | Version release: not built yet (F08) |
| "add a rule ..." | Rule change: not built yet (F09) |

- **No `.troy-mode/`.** Answer a question, but change nothing. For any other request, ask Troy once whether to make this folder a troy-mode project.
- **Version release, Rule change.** Say which flow it is and that it is not built yet. Change nothing.
- **Unclear.** When a request fits two flows, or none, ask Troy one question with a recommended answer.
- **How far (D63).** One feature, one bug, or one change, unless the request names more, such as "F04 to F06" or "the rest of v0.1". Then report and stop.
- **One PR at a time.** Work on one PR at a time in this checkout. A new request waits until that PR merges, unless Troy says to pause it. When a paused PR resumes, rebase its branch on `origin/main` first. A side PR, a bug PR, or a `[docs]` PR comes before the stage PR it interrupts; `status` continues it first.
- **The go-ahead.** In troy-mode, Troy's approvals of the requirements, the architecture, and the first features' designs and test plans are the go-ahead that Troy's global instructions ask for before code. Do not ask for it again.
- **What waits on Troy.** When `status` has `waiting_on_troy` and the request does not answer it, tell Troy what waits and stop.

## Running a role

1. **Brief.** `troy_flow.py brief --task <task> --item <ID> [--title <title>] [--round <n>] [--input-file <file>]`. Write Input (findings, an answer, failing checks, a ruling, Troy's decision or comments) to a file under `$(git rev-parse --absolute-git-dir)/troy-mode/flow/` first.
2. **Snapshot.** `troy_flow.py snapshot --role <role>`. The tree must be clean: you commit after every writing run.
3. **Agent call.** `subagent_type` from `agent`, the brief's `prompt` as the prompt, and `model` and `effort` only when `agent` has them.
4. **Wait.** Wait for the role's report and do nothing else in the checkout meanwhile: F05's hooks blame every change during the run on the role. Roles that only read may run together, such as TM2 and CR1 on one test PR, under one snapshot with `--role test-manager --role code-reviewer`; nothing may change.
5. **Check.** `troy_flow.py check-run --run <run ID>`, with `--allow-dependency <path>` only for a dependency Troy accepted.
   - No problem: stage exactly the paths in `stage`.
   - `escalate` true (`HEAD` or the branch moved): escalate at once.
   - A `scope`, `section`, or `dependency` problem: run every `undo` command, then run the role once more with Input that names the paths and the scope. A second problem in the same stage escalates.
   - Mention `hooks_log` lines in your report; they do not stop the flow.

Rulings change no file: TM3, TM4, TM5, TM6, IF4, AR4 without an architecture change, and AR3's first run. If one changed something, undo it and run it once more.

When you write a document yourself as the Product Manager (PM1, PM2, PM3), take the snapshot with `--role product-manager` and check it the same way.

### The report

| Result | What you do |
| --- | --- |
| `done` | Check the run, commit, run the local checks, push, then the stage's review. |
| `failed` | Count one attempt. Run the author again with the failing checks in Input, or escalate after the third attempt. |
| `approved` | Start the next reviewer, or go on to the merge. |
| `changes-requested` | Run the author again (IF2 for a design) with the findings in Input and the next round, or escalate after round 3. |
| `needs-answer` | Start the role the question names with the question as Input (AR5 for the Architect, IF3 for the Interface Designer), then run the asker again with the answer. A question for Troy goes to Troy. A disputed test, a coverage gap, or a new dependency starts a side flow (section "Side PRs"). |
| `escalate` | Escalate. |
| No report in F04's format | Run the role once more. The second time, escalate. |

When a role asks for `how`, `why`, or `interrogate`, read that skill's `SKILL.md` under `${CLAUDE_PLUGIN_ROOT}/skills/`, follow it, and put the result in the next brief's Input.

## Feature loop

`status` gives the next stage in `next` (`action` `stage`), or the open PR to continue (`continue-pr`). The stage before must have merged on `origin/main`, and `status` only names a stage when it has.

| PR | Title | Author | Reviewers | Local checks before each push | Merged by |
| --- | --- | --- | --- | --- | --- |
| 1 | `[<ID> 1/6 design] <name>` | IF1, then IF2 for each revision | AR2 | `troy-check pr` | Troy for the first features, else you |
| 2 | `[<ID> 2/6 test-plan] <name>` | TM1, with IF3 for its questions | None. At most 3 rounds of questions. | `troy-check pr` | As PR 1 |
| 3 | `[<ID> 3/6 mock] <name>` | DV1 | CR1 | `troy-check pr`, the pack's steps, `troy-check code` | You |
| 4 | `[<ID> 4/6 tests] <name>` | TE1 | TM2 and CR1, together | As PR 3 | You |
| 5 | `[<ID> 5/6 impl] <name>` | DV2 | CR1 | As PR 3, plus the feature's performance cases on Troy's PC when it has a target | You |
| 6 | `[<ID> 6/6 accept] <name>` | PM3, yourself | None | `troy-check pr` | You |

`<name>` is the feature's name in the requirements; `next.title` and `next.branch` give the title and the branch (`troy-mode/f04-3-mock`). `next.merged_by` says whether Troy approves it. When `continue-pr` names a PR whose `task` is null (a test fix or a `[docs]` PR), read its description and your comments on it to find its author.

### One stage

1. **Branch.** `git fetch origin`, then `git switch -c <branch> origin/main`. Never check out `main`: in a worktree, `main` is often checked out elsewhere.
2. **Author.** Run the stage's author (section "Running a role"). For PM3, check the feature against its requirement row and prototypes, set its status to "Passes tests on main" in both languages, and raise the requirements' `version` by one minor step in both, with `updated`.
3. **Commit.** `git add -- <path>` for exactly the paths in `stage`. The first run makes the commit, whose subject is the PR title (R01): `git commit -m "<title>"`. Later runs amend it with `git commit --amend --no-edit`, so the PR keeps one commit. The git hooks check R19.
4. **Local checks**, on the commit (section "Local checks"). A failure goes back to the author as Input and counts as an attempt.
5. **PR.** Write the description from `.github/pull_request_template.md`: Why (the feature's goal), What (the stage's output, with IDs), Checks (what ran and the results), and Soft-limit reason (from the Developer's report, or None), with the template comment removed. Check it with `troy_flow.py check-text --file <file>`. Push with `git push --force-with-lease -u origin <branch>`. The first time, as its own command: `gh pr create --base main --head <branch> --title "<title>" --body-file <file>`. Later pushes: `gh pr edit <number> --body-file <file>`.
6. **Reviews.** Run each reviewer on the PR and post its report as a comment (section "Comments"). AR2 also writes section 4 of the design, so check, commit with `--amend`, check, and push after it as after an author. `changes-requested` sends the findings to the author as the next round. Pass Troy's comments on the PR (`troy_comments` in `status`) to the author as Input.
7. **Merge** (section "Merging").
8. **Progress.** After every step (each role run, commit, push, review, merge, and escalation) run `troy_flow.py status --write-progress`.

### Local checks

- Always: `python .troy-mode/checks/troy_check.py pr --base origin/main --title "<title>" --body-file <description file>`.
- For a PR with code or tests (PR 3 to 5, bug PRs, test fixes), also the pack's steps from the author's brief `checks`, with `troy-check code` run without `--worktree`, with `--json`, and its output saved: `... troy_check.py code ... > reports/troy-check.json`. Then run `troy_flow.py check-skips --report reports/troy-check.json --junit reports/junit.xml`.
  - Exit 0: the checks passed. When `ci_only` is not empty, the only failures were tests the test plan runs on another platform (D69): count no attempt, list those cases in the description's Checks section as "skipped here, checked by CI", and merge only on CI's result, as always.
  - Exit 1: the `problems` go back to the author as Input, and the run counts as an attempt.

### Rounds and attempts

- **Rounds (R17).** A round is one run of the stage's reviewers. On PR 4 a `changes-requested` from either reviewer fails the round. If round 3 still ends in `changes-requested`, escalate. On PR 2 a round is one question to the Interface Designer and its answer; the test plan's alignment log records each. `status` counts rounds from your comments (`rounds`), so a new session counts on.
- **Attempts (D64).** An attempt is an author run that reports `failed`, a `done` whose local checks fail, or a CI failure in the author's files. Each stage allows 3; after the third, escalate. A revision whose checks pass is a round, not an attempt. With a PR, post `<Role> attempt <n>: failed`. Before the PR exists, record it with `troy_flow.py status --note "<Role> attempt <n>: failed"`. `status` gives the count in `next.attempts`.

### Comments

Post every review, failed attempt, escalation, and request to Troy as a PR comment whose first line is one of these headings:

- `<Role> review, round <n>: <result>`, for example `Architect review, round 2: changes-requested`, then the findings;
- `<Role> attempt <n>: failed`, then the failing checks;
- `Escalation: <trigger>`, then the escalation message in English;
- `Waiting for Troy: approve this PR`.

Every role acts through Troy's account, so the heading records who did what. A comment without one of these headings is Troy's. Write each comment to a file, check it with `troy_flow.py check-text --file <file>`, then post it with `gh pr comment <number> --body-file <file>`.

### Merging

Merge a PR only when every review of the stage ended in `approved`, the local checks passed on the pushed commit (or `check-skips` left only `ci_only` cases), `gh pr checks <number> --watch`, run once, ends with every check passing, and the merge rights allow it (`merged_by` is `f07`). Right after a push, GitHub may not have registered the workflow yet, and `gh pr checks` then says that no checks are reported: run it again; that is still the same wait. Then:

1. `git switch --detach`
2. `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>`, with the full commit ID you pushed
3. `git fetch origin`
4. `troy_flow.py status --write-progress`

Detach first, so that `gh` does not try to check out `main` before it deletes the branch.

- **A failing check.** Give the author the failing log (`gh run view <run ID> --log-failed`) as Input; the run counts as an attempt. When the failure lies outside the author's files, such as in the workflow or on the runner, stop and tell Troy.
- **A refused merge.** If the agent's permissions refuse `gh pr merge`, stop and tell Troy which permission to add. Never work around a refusal.

**Troy's approval (D61).** When `merged_by` is `troy` (PR 1 and PR 2 of the first `troy_approves_first` features, the requirements, the architecture, and a requirement change), post `Waiting for Troy: approve this PR`, run `troy_flow.py status --waiting "<what>"`, tell Troy with the PR's link, and stop. Troy replies in chat or merges on GitHub.

- **Troy approves in chat.** Run `troy_flow.py approve --doc <document>` (the design for PR 1, the test plan for PR 2, `docs/requirements.md`, or `docs/architecture.md`). It changes only header fields, so no role runs. Stage both files, amend the commit, run the local checks, push, wait for the checks, and merge.
- **Troy asks for changes.** The author revises, as a round.
- **Troy merged on GitHub.** The document's approval is not recorded, and `status` gives `record-approval`: on `next.branch`, run `approve --doc <next.doc>`, commit as `next.title` (`[docs] Record Troy's approval of <document>`), check, open the PR, and merge it yourself.

**After the first features (D62).** When `status` gives `ask-approvals`, ask Troy once whether to go on approving PR 1 and PR 2 of later features, and how many. Record the answer in `.troy-mode/config.toml`'s `[flow] troy_approves_first`, with a comment line above it that names the decision and its date, in a `[rules] Set the features Troy approves` PR, and merge it. This is the only config change you make.

## Side PRs

A side PR interrupts a stage (design 8.7). First amend the author's work so far into the stage branch's commit, without pushing it, so the tree is clean. Then finish the side PR, switch back to the stage branch, run `git rebase origin/main`, and run the stage's author again with the side PR's result in Input.

Side PR titles and branches: a test fix is `[<ID> test-fix] <summary>` on `troy-mode/<id>-test-fix`; a `[docs]` side PR names what it adds, such as `[docs] Add cases to the F04 test plan`, on `troy-mode/<id>-docs`. `<ID>` is the feature or the bug. Give every run of a side PR its title with `brief --title`, so its checks name the right PR. You merge every side PR (`merged_by` `f07`).

### Disputed test

The Developer (DV2, or DV3 on a bug) reports `needs-answer` for the Test Manager about a test.

1. TM4 rules, with the question in Input.
2. **The code is wrong:** run the Developer again with the ruling.
3. **The test is wrong:** on `troy-mode/<id>-test-fix`, TE3 changes only what the ruling names, with `--title "[<ID> test-fix] <summary>"`. Commit, check, open the PR (Why: the ruling; What: the change and its reason), run TM2 and CR1 together on it, and merge. Then go back to the stage.

### Coverage gap

R11 fails in the local checks or in the Developer's report. TM3 classifies the uncovered code, with R11's details in Input:

- **Code nothing needs:** DV4 deletes it in the same PR.
- **A case the test plan missed:** on `troy-mode/<id>-docs`, TM1 adds the cases with `--title "[docs] Add cases to the <ID> test plan"`; open and merge that PR. Then TE4 writes their tests in `[<ID> test-fix] <summary>`, reviewed by TM2 and CR1. Then go back to the stage.
- **Behavior not in the design:** IF4 rules. The design missed it: IF2 updates the design in a `[docs]` PR, AR2 reviews it, and the missed cases follow as above. The Developer overreached: DV4 deletes the code.
- **Code that cannot be tested in practice:** run the Developer again to exclude those lines with a written reason; TM6 approves or rejects the reason. A rejection goes back to TM3's other answers, or escalates.

### New dependency (R16)

An author reports `needs-answer` for the Architect about a new third-party dependency.

1. AR3 reviews it and reports `escalate` with a recommendation. Escalate to Troy (section "Escalation").
2. **Troy accepts:** on `troy-mode/<id>-docs`, AR3 runs again with Troy's decision in Input and `--title "[docs] Accept the dependency <name>"`; it adds the dependency and an ADR to the architecture. Open and merge that PR. Back on the stage branch, run the author again with the decision; `check-run` gets `--allow-dependency <path>` for each dependency file the decision covers, such as `pyproject.toml`. Then the series lock (D66): run `troy_flow.py series`, run its `commands`, then each member's `tests.commands` in its `tests.cwd`. Stage the new lock with the author's files. A member whose tests fail stops the flow: escalate. The PR description lists the members in `stale`, whose lock is now out of date; open no PR in them.
3. **Troy refuses:** run the author again with the decision: do without the dependency. `check-run` gets no `--allow-dependency`.

## Bug fix

1. **Issue.** When Troy names an issue ("fix #12"), read it with `gh issue view <n>`. Otherwise open one: write the report in English to a file, check it with `troy_flow.py check-text`, and run `gh issue create --label bug --title "<summary>" --body-file <file>`. The issue's number gives the bug ID: issue 12 is `B12`.
2. **Triage.** TM5, with the issue in Input (`brief --task TM5 --item B12`). A misunderstood requirement goes to the requirement change flow: tell Troy, with a recommendation. A bug goes on.
3. **PR A.** On `troy-mode/b12-test`, TE2 writes the reproduction test with `--title "[B<n> A/B test] <summary>"` (the issue's summary). Its local checks show that B12's tests fail (R09). Open the PR (Why: the issue's link; What: the test), run TM2 and CR1 together with the same `--title`, and merge.
4. **PR B.** `status` now gives `bug` with `next.title` (`[B<n> B/B fix] <summary>`) and `next.branch` (`troy-mode/b12-fix`), so a new session finishes the bug too. DV3 fixes it (`brief --task DV3 --item B12`); B12's tests must pass. The description's Why says `Fixes #<n>`, so GitHub closes the issue when you merge. CR1 reviews it, and you merge.

A dispute or a new dependency during a bug runs as in section "Side PRs", with the bug ID as `<ID>`.

## Requirement change

1. **PM2.** On `troy-mode/change-<slug>` from `origin/main`, under a snapshot with `--role product-manager`, update `docs/requirements.md` and its mirror:
   - the requirement itself;
   - each affected feature that is not yet accepted: Status `Needs rework (<the change>)`;
   - each affected feature that is accepted (D65): keep its status and add a new feature for the change, with the next free ID, a short name, a hard dependency on the old one, and Status `Not started`; put it in the topological order right after the features it depends on and before the features not started yet, unless Troy says otherwise, and in the version plan;
   - raise `version` by one minor step in both, with `updated`, and add a change log row.

   Commit as `[docs] Change the requirements: <summary>`, run `troy-check pr`, open the PR, and wait for Troy's approval (section "Merging"). A Feature cell keeps to the feature's short name.
2. **AR4.** For each affected feature, run AR4 with the change in Input (`brief --task AR4 --item <ID>`). When AR4 reports an architecture change, escalate it with AR4's ADR as the recommendation; on Troy's yes, put the ADR in a `[docs]` PR and merge it.
3. **A feature not yet accepted** goes back to the earliest stage AR4 names. When its open PR's stage is at or after that stage, close it unmerged: `gh pr close <number>`. Then run that stage again with its usual title and branch, giving the title with `brief --title` (a redo; the engine allows it while the feature is in rework). When the feature's implementation has merged and its tests change, start at stage 3 at the latest: R09 needs every test of the feature to fail against a mock. Once the redo merges, `status` goes on from there.
4. **An accepted feature** gets its new feature through the feature loop. Put AR4's list into each brief's Input:
   - IF1: section 2 holds only new interfaces, or says there are none (no subsection); section 3 lists the changed interfaces.
   - TM1: name the old cases that the change retires, and move them from the old feature's test plan to its "Not tested" section with the reason, in both languages, in the same PR.
   - TE1: delete the retired tests and add the new cases, which fail against the current code (R09).
   - When section 2 adds no interface, `status` skips PR 3 and goes from PR 2 to PR 4.

When `status` gives `rework` (a new session, or a stage PR opened before the change, in `next.pr`), run AR4 for `next.item` and go on from step 3.

## Escalation

Escalate when a review loop reaches 3 rounds without agreement, a change needs the requirements or the architecture to change, an author's work still fails after 3 attempts, a new third-party dependency is needed (AR3's `escalate`), a run moved `HEAD` or the branch or broke its scope twice, or an action is irreversible and outside your rights. Your rights: push your own branches with `--force-with-lease`; open, edit, comment on, close, and merge your own PRs within R18; open bug issues; and delete your own branches after their PR merges. Anything else asks Troy.

Write the message in Troy's language, in the shape of `.troy-mode/templates/escalation.md` (Prototype C): where it stopped, why, the facts with links, the options, and a recommendation. Post it in English on the open PR as `Escalation: <trigger>`; when no PR is open yet, post it on the bug's issue if there is one, else only in chat. Run `troy_flow.py status --waiting "<what>"`, and stop. When Troy answers, in this session or a new one, put the decision into the next brief's Input and go on.

## Project setup

`status` gives the step to do next; a project that already has some steps resumes at the first missing one.

1. **Setup** (`next.action` `setup`). When Troy says yes, read `${CLAUDE_PLUGIN_ROOT}/skills/troy-init/SKILL.md` and follow it: troy-init's engine `setup --email <address>` with `--dry-run --json` first, Troy's two questions (whether to create the private GitHub repository, and whether to replace files troy-init did not write) in one message, and its PR flow. Its step 8 already detaches before the merge and ends with `git fetch origin`.
2. **Requirements** (`requirements`), after the setup PR merges, so troy-check checks them. Work as the Product Manager (PM1) under a snapshot with `--role product-manager`, on the branch `troy-mode/requirements`. In the features table, the Feature cell holds only the feature's short name, such as `Export history as CSV`: it becomes every PR title and the feature's folder name. Describe the feature in the requirements' other sections. Open `[docs] Add the requirements`, and get Troy's approval as section "Merging" says.
3. **Architecture** (`architecture`). Run AR1 (`brief --task AR1`) on `troy-mode/architecture`, then open `[docs] Add the architecture`, approved the same way. The message that asks Troy for this approval also asks the language step's question: which series the project belongs to, if any.
4. **Language step** (`language`). The language comes from the architecture's tech stack. Create the branch `troy-mode/lang-<name>` from `origin/main` first, then run troy-init's engine `lang <python|cpp>` with `--dry-run --json`, then without `--dry-run`, and take it through troy-init's PR flow. Add `--env-prefix "$TROY_MODE_ENV_PREFIX"` when that variable is set, and `--mamba <path>` when mamba is not on the PATH or in `$MAMBA_EXE`.
5. **Next.** Report, and go on to the first feature only if the request asked for it.

## Upgrade

Create the branch `troy-mode/upgrade-<version>` from `origin/main`, then run troy-init's engine `upgrade` with `--dry-run --json`, and take it through troy-init's PR flow. When it has nothing to change, run `git switch --detach origin/main`, delete the branch, and tell Troy. `status` says when the project's troy-check is older than the plugin's (`checks.outdated`): `[roles]`, `[flow]`, and `troy-check code --worktree` need the new copy.

## Work outside the pipeline

Answer questions and investigations here, following `how` or `why` (read their `SKILL.md`) when they fit, and start no role. An experiment runs on a throwaway branch `troy-mode/try-<slug>` made from `origin/main`, or in a scratch folder. Never push it or open a PR from it. Code worth keeping goes through a requirement change and the feature loop.

## Continue

Run `status` and report where the project stands. When something waits on Troy, say what. Otherwise go on with `next`, as far as the request reaches (D63): `continue-pr`, `stage`, `record-approval`, `bug` (PR B of a bug), `rework` (AR4 after a requirement change), and the setup steps.

## Reports

Report each stage to Troy in Troy's language, in the shape of Prototype B, for example:

```text
Next in order is F04 "Export history as CSV". It depends on F02 and F03, both accepted.
  [1/6] Interface design PR #41 is open. The Architect approved it in round 2.
        You approve this one (feature 2 of your first 3). Waiting for you.
```

Say plainly what you did not do or could not check.
