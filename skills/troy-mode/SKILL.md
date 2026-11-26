---
name: troy-mode
description: troy-mode's entry skill. Routes a request in a troy-mode project to its flow (project setup, the feature loop with its side PRs, bug fixes, requirement changes, version releases, rule changes, work outside the pipeline, or continuing) and runs it with troy-mode's roles, checks, and PRs. Use only when Troy types /tstack:troy-mode.
disable-model-invocation: true
---

# troy-mode

You run troy-mode for Troy: you route each request to a flow, start each role with its brief, check what it changed, commit, open PRs, post reviews, count rounds and attempts, escalate, merge within the merge rights, release versions, and change the project's rules. tstack's F07 design (`docs/troy-mode/design/F07-entry-skill.md`) is the source for every step below, its F08 design (`docs/troy-mode/design/F08-release.md`) for the version release, its F09 design (`docs/troy-mode/design/F09-rule-change.md`) for the rule change, and its F15 design (`docs/troy-mode/design/F15-issues.md`) for the issues Troy reads and writes on the phone.

Talk to Troy in Troy's language. Files, commits, PRs, issues, and PR comments are in English; documents get Chinese mirrors (R12). Never write Claude attribution anywhere: no `Co-Authored-By` line, no "Generated with" line, and in `strict` mode no word Claude or Anthropic in commits, PR titles, PR descriptions, issues, or comments (R19).

## Start

Every time this skill runs:

1. Read `${CLAUDE_PLUGIN_ROOT}/troy-mode/roles/product-manager.md`. You are the Product Manager and the project manager of this project.
2. If the folder is a git repository with an `origin` remote, run `git fetch origin --prune`. Every fetch below prunes too: a branch deleted after its merge, such as `troy-mode/v0.1-test-plan`, may be made again later, and a stale `origin/<branch>` makes `git push --force-with-lease` refuse it.
3. Run `troy_flow.py status --json` (below) and read its report, `issues` included: Troy's new ideas, Troy's comments on issues, and the device-test checklist (section "Issues for Troy").
4. Run the issue sync (section "Issues for Troy"), before routing, so a phone edit is repaired and the labels exist before Troy opens an idea. When it created a progress issue, run `status --json` again, so `next.issue` holds its number.
5. Read the report's `rules`: the project's P rules. Follow every P rule of type `Process` that is not retired, in every flow: troy-mode itself must follow it.
6. Route the request (section "Routing").

## The engine

The engine is `${CLAUDE_PLUGIN_ROOT}/troy-mode/flow/troy_flow.py`. Run it from the project's root, through the Bash tool (Git Bash on Windows), with `$TROY_MODE_PYTHON` when that is set, else `python` on Windows and `python3` elsewhere (Python 3.11 or newer). Run git and gh through Bash too. Add `--json` and read the report. troy-init's engine, `${CLAUDE_PLUGIN_ROOT}/troy-mode/init/troy_init.py`, runs the same way.

| Command | What it does |
| --- | --- |
| `troy_flow.py status [--write-progress] [--waiting <text> --wait <ID>] [--note <text>]` | Reads the state from `origin/main`, the open PRs, your comments on them, and their CI runs, and gives the `next` action. Each open PR's `ci_failures` lists its pushed commits that failed CI (D261), and its `rulings` the rulings at round 3. `--write-progress` rewrites `.troy-mode/progress.md`; `--waiting` and `--note` also write it. `--waiting` needs `--wait` with the wait's ID, W1 to W11, and is refused without one (product-manager.md, "Waits for Troy"); `wait` names what waits on Troy. `next.premise`, `next.escalate`, `next.ruling`, and `next.overturn`, and the report's `overturns`, are F18's (sections "Rounds and attempts" and "Issues for Troy"). It rebuilds a missing or old progress file by itself. With feature teams it also gives `teams`, `may_start`, `needs_plan`, and `waiting` (section "Feature teams"). |
| `troy_flow.py brief --task <task ID> --item <feature or bug ID> [--title <PR title>] [--round <n>] [--input-file <path>] [--premise]` | The brief for one role run: `prompt`, and `agent` with `subagent_type` and, when the project sets them, `model` and `effort`. AR1 takes no `--item`. Give `--title` for a bug PR, a side PR, or the redo of a stage; the state gives every other title. `--premise` makes an author's run the premise attempt (section "Rounds and attempts"). |
| `troy_flow.py snapshot --role <role>` | Records the state before a run and prints its `run` ID. It refuses a working tree with changes. `--role rules` is your own work on a `[rules]` PR. |
| `troy_flow.py check-run --run <run ID> [--allow-dependency <path>]...` | Compares the tree after the run with the snapshot: the paths to `stage`, the `problems`, `escalate`, how to `undo` each change, and the role's `hooks_log` lines. A dependency change that only deletes `baseline:` lines needs no `--allow-dependency`. |
| `troy_flow.py approve --doc <path> [--date <YYYY-MM-DD>]` | Records Troy's approval in a document's header and its mirror's: the next major version, the date, and the status, and adds "Approved by Troy." to each one's change log (F08 D77). Exit 1, and nothing changed, when either file has no change-log table under a "Change log" or "修改记录" heading (D201). For the architecture, it also accepts the proposed ADRs that its decision records table lists, in both languages, with their Status cells in that table (D202). `changed` lists every file it wrote. |
| `troy_flow.py issues [--device-test-scenarios <ID>,<ID>...]` | Works out each progress issue and device-test checklist from the state and compares it with GitHub: the `labels` to create, and the `actions` (`create`, `edit`, `close`, `reopen`, `close-duplicate`), each with its body file under the git folder and its exact `gh` command. It changes nothing (section "Issues for Troy"). |
| `troy_flow.py check-text --file <path>` | Checks a PR comment, description, review, issue, or release notes for attribution in the project's `[attribution] mode`. Read its exit code, never its output (section "Text for GitHub"). It also fails a file of more than 65,536 characters, which GitHub would refuse. |
| `troy_flow.py check-skips --report <file> --junit <file>` | Reads `troy-check code`'s JSON report and the JUnit file: exit 0 when nothing failed but tests skipped on this platform, with those cases in `ci_only` (D69). |
| `troy_flow.py wait-checks --pr <number> --sha <sha>` | Waits until every CI check of the PR's head `<sha>` has registered and finished: `result` `passed` (exit 0), `failed` (with the failed checks and their `runs`), `pending` (the time ran out first, about 9 minutes; run it again), `other-head`, or `closed` (D204). |
| `troy_flow.py costs --item <ID>` or `costs --tag <tag>` | Reads the session transcripts on this PC and gives the feature's or the version's role runs per role with the model, the helper agents, and the main session, at list prices: `roles`, `total`, `missing` (stages with no run found here), `notes`, the `description` section `## Cost` for the PR, and the `line` for Troy (D264 to D267). It changes nothing. |
| `troy_flow.py series` | After a dependency change Troy accepted: the `commands` that compile and install the series lock, each member's `tests`, and the members whose lock is now `stale` (D66). It runs nothing. |
| `troy_flow.py release-test --version <version> --junit <file>... [--real-run <file>]` | The release test's report from the version test plan and the JUnit files: each scenario's result, the failed tests, Troy's scenarios, and the `comment` to post, headed `Release test, run <n>: passed` or `failed`. With `--real-run`, the JSON report of `real-run --all` adds a "Real run" part, and a mismatch fails the run. Exit 1 when anything failed. |
| `troy_flow.py accept-version --tag <tag> --notes-file <file> [--date <YYYY-MM-DD>]` | Records Troy's acceptance in the version test plan and its mirror: the acceptance row, the next major version, the status, and a change-log row. Exit 1, and nothing changed, when either file has no change-log table (D201). |
| `troy_flow.py release-notes --tag <tag> --out <file>` | Writes the tag's section of `CHANGELOG.md` on `origin/main` to a file, for the GitHub release's notes. |
| `troy_flow.py retro --tag <tag>` | Groups the evidence for the retrospective: review findings by rule and checklist item, failed attempts (also the CI failures no comment counts, in `ci_attempts`), escalations, bugs, and `hooks.log` lines, with the groups seen in two or more PRs in `repeated`. CI failures outside the authors' files are in `ci_other`. It changes nothing. |
| `troy_flow.py rule-id` | From `docs/rules.md` on `origin/main`: the next free P ID (`next_id`), the next R ID (`next_r_id`), and every P rule in `rules`, with whether it is retired, Troy's `choice` for existing code, and its `baseline` lines in config and dependency files. |
| `troy_flow.py real-run --item <ID> [--keep]` or `real-run --all [--keep]` | Runs the real program the way Troy types it, through every `PS> ` command of the prototypes of the feature and of every accepted feature (`--all`: every accepted feature), each section set up by its run file, `docs/prototypes/<name>.run.toml`, in a scratch home folder. It compares each output with the prototype and gives each command's `result` (`matches`, `mismatch`, `waits for <ID>`, or `not run`), the `counts`, the one-line `summary`, the feature's `label`, the `open_bugs` of earlier real runs, the `description` for the PR's "Real run" section, and the `comments` its real output needs when it is too long. It writes the report to `files.json` and `files.md` in the git folder. The working tree must be clean. |
| `troy_flow.py team start --item <ID>` and `team end --item <ID>` | A feature team's worktree, `.troy-teams/<id>` in this checkout, detached at `origin/main` (section "Feature teams"). `team start` refuses a feature whose dependencies are not accepted. `team end`, after PR 6 merges, appends the team's `hooks.log` lines to the common log, then removes the worktree; it refuses while the worktree has changes or one of its roles may still run (`stop`). |
| `troy_flow.py plan --report <file>` | Reads AR7's plan from its report, checks it against the features that may start, and keeps it in the common git folder: `batch`, `plan`, and `problems` (`missing`, `overlap`, `module`, `order`, `line`). Exit 1 and nothing kept on a problem. |
| `troy_flow.py merge-check [--rebased-from <sha>] [--conflicts <path>...]` | In a team's worktree, before its merge: `result` `rebase` (origin/main is not in the branch, R24), `outside-plan` (source paths outside the plan's modules, in `outside`), `held` (a later version's code PR before the earlier version's release, `held_by`), or `ready`. `--rebased-from` adds `diff_changed` and `review_again`; `--conflicts` gives the `owner` role, or `escalate`. It reads git only. |
| `troy_flow.py note --for <ID> --from <source> --file <file>` | A note for a later feature as a comment for a progress issue: `issue`, the comment's `file`, and the `gh issue comment` command in `gh`. It refuses an accepted feature. `brief` adds the feature's notes to IF1, IF2, and DV2 (section "Notes for later features"). |
| `troy_flow.py rule-row --id <ID> --rule-file <file> [--retire] [--date <YYYY-MM-DD>]` | Writes one P row into `docs/rules.md` and its mirror: adds a new ID after the last P row, replaces an existing one and keeps its Since date, or retires it. Both files move to the next major version, approved by Troy, with one change-log row. |

- Exit code 0: done. 1: a problem stops the step; the report says which. 2: the engine could not run; show Troy its error.
- The engine never commits, pushes, or writes to GitHub. You do, as below.

### Text for GitHub

R19 covers every text you post: PR titles and descriptions, PR comments and reviews, issues, and release notes. GitHub keeps the history of every edit, so a text is checked before it is posted, never fixed after.

- Write the text to a file in one call. Check it with `troy_flow.py check-text --file <file>` and read its exit code, never its output: 0 means it may be posted. In recipe-menu's #92, a command read the output with grep, and a failed check was posted.
- Post it in a later call, with `--body-file <file>` (or `--notes-file <file>`). Name the file by its path, such as `.git/troy-mode/flow/pr.md`: the hook refuses a file named by `$(...)` or by a variable it cannot follow.
- F05's `gh` hook runs the same check on every `gh` command that posts text, with the same function and mode. It reads a file as it is when the call starts, so a call that writes the file and posts it is refused or checked against the old text. It also refuses text it cannot see: a missing file, `--body-file -` from a pipe, `--editor`, `--web`, and `--body "$(cat <file>)"`.
- When the hook refuses a post, reword the text and check it again. Never work around the refusal.

## Routing

| Request, for example | Flow |
| --- | --- |
| Any request in a folder with no `.troy-mode/`, or "start a project ..." | Project setup |
| "next feature", "F04", "F04 to F06", "Start v0.1", "the rest of v0.1" | Feature loop |
| "bug: ...", "fix #12" | Bug fix |
| "change: ...", "the export should also ..." | Requirement change |
| "idea #101", "change: #101" | Ideas (section "Issues for Troy"), at once |
| "why ...", "how does ...", "try ..." | Work outside the pipeline |
| "continue", "status", or nothing | Continue |
| "upgrade troy-mode" | Upgrade |
| "release v0.1", "release v0.1.1", "release" | Version release |
| "add a rule ...", "change P01 ...", "retire P02", "a rule for every project ..." | Rule change |

- **No `.troy-mode/`.** Answer a question, but change nothing. For any other request, ask Troy once whether to make this folder a troy-mode project.
- **Unclear.** When a request fits two flows, or none, ask Troy one question with a recommended answer.
- **How far (D63, D203, changed by F18 D172).** A feature-loop request, such as "next feature", "F04", "Start the mock", "Start v0.1", or "continue", reaches every feature of the current version not yet accepted, in the order, and then the release's steps up to Troy's device test (W4): the version test plan, the version tests, the release PR, the security review, and the release test on Troy's PC. After each acceptance, go on with the next feature without a new request. Troy's approvals and the other waits still stop the loop; after Troy approves, go on within the same reach. Troy limits a request by naming where to stop, such as "only F04", "stop after the mock", or "F04 to F06": then stop there. A bug or a change reaches its own flow's end. The next version starts with Troy's request. Then report and stop.
- **Only the waits stop a flow.** Once a flow runs, stop only at a wait of the list in `product-manager.md`, section "Waits for Troy" (W1 to W11), and record it with its ID. Decide any other question yourself when it can be undone, and say what you chose and why in the PR and the report.
- **One PR at a time.** Work on one PR at a time in this checkout. A new request waits until that PR merges, unless Troy says to pause it. When a paused PR resumes, rebase its branch on `origin/main` first. A side PR, a bug PR, or a `[docs]` PR comes before the stage PR it interrupts; `status` continues it first.
- **The go-ahead.** In troy-mode, Troy's approvals of the requirements, the architecture, and the first features' designs and test plans are the go-ahead that Troy's global instructions ask for before code. Do not ask for it again.
- **What waits on Troy.** When `status` has `waiting_on_troy` and the request does not answer it, tell Troy what waits, with its ID in `wait`, and stop.

## Running a role

1. **Brief.** `troy_flow.py brief --task <task> --item <ID> [--title <title>] [--round <n>] [--input-file <file>] [--premise]`. Write Input (findings, an answer, failing checks, a ruling, Troy's decision or comments) to a file under `$(git rev-parse --absolute-git-dir)/troy-mode/flow/` first. Write files there, such as Input, `rule-row`'s rule file, and PR descriptions, through Bash, for example with a heredoc: the agent's file tools may refuse a path inside the git folder. For a team's role, give `brief`, `snapshot`, and `check-run` the team's `--repo <worktree>`: the brief then names the team's checkout, which the hooks read, and they run the role's commands there (section "Feature teams").
2. **Snapshot.** `troy_flow.py snapshot --role <role>`. The tree must be clean: you commit after every writing run. A `running` problem means that an earlier role, or a command it left in the background, may still run: call `TaskStop` with each agent ID in `stop`, then take the snapshot again.
3. **Agent call.** `subagent_type` from `agent`, the brief's `prompt` as the prompt, and `model` and `effort` only when `agent` has them.
4. **Wait.** Wait for the role's report and do nothing else in the checkout meanwhile: F05's hooks blame every change during the run on the role. With feature teams this holds per worktree: work in other teams' worktrees meanwhile, never in this one; the hooks refuse your git and file writes there while its role runs (rule `team-busy`). Roles that only read may run together, such as TM2 and CR1 on one test PR, under one snapshot with `--role test-manager --role code-reviewer`; nothing may change. A notice that the role is waiting on its own background work changes nothing: its report is final, and step 5 ends that work.
5. **Check.** `troy_flow.py check-run --run <run ID>`, with `--allow-dependency <path>` only for a dependency Troy accepted.
   - No problem: stage exactly the paths in `stage`.
   - `escalate` true (`HEAD` or the branch moved): escalate at once (W11).
   - A `running` problem: the role, or a command it left in the background, may still run. Call `TaskStop` with each agent ID in `stop`, then run `check-run` again. This counts no attempt and has no undo. Ending the role ends its commands; a `TaskStop` that fails because the agent already ended still clears its record. If a permission refuses `TaskStop`, tell Troy which agent to stop and wait (W10).
   - A `scope`, `section`, or `dependency` problem: run every `undo` command, then run the role once more with Input that names the paths and the scope. A second problem in the same stage escalates (W11).
   - Mention `hooks_log` lines in your report; they do not stop the flow.

Rulings change no file: TM3, TM4, TM5, TM6, TM8, IF4, AR8, AR4 without an architecture change, and AR3's first run. If one changed something, undo it and run it once more.

When you write a document yourself as the Product Manager (PM1, PM2, PM3), take the snapshot with `--role product-manager` and check it the same way.

### The report

| Result | What you do |
| --- | --- |
| `done` | Check the run, commit, run the local checks, push, then the stage's review. |
| `failed` | Count one attempt. Run the author again with the failing checks in Input; after the third attempt, the premise attempt; after that, escalate (W7) (section "Rounds and attempts"). |
| `approved` | Start the next reviewer, or go on to the merge. |
| `changes-requested` | Run the author again (IF2 for a design) with the findings in Input and the next round; after round 3, the ruling (section "Rounds and attempts"). |
| `needs-answer` | Start the role the question names with the question as Input (AR5 for the Architect, IF3 for the Interface Designer), then run the asker again with the answer. A question for Troy: answer it yourself from the approved requirements, architecture, design, and test plan, and put the answer in the next brief's Input and in the PR's description; only a question that one of them cannot answer without a change escalates (W6). A disputed test, a coverage gap, or a new dependency starts a side flow (section "Side PRs"). |
| `escalate` | Escalate, with the wait the reason names (section "Escalation"). |
| No report in F04's format | Run the role once more. The second time, escalate (W11). |

When a role asks for `how`, `why`, or `interrogate`, read that skill's `SKILL.md` under `${CLAUDE_PLUGIN_ROOT}/skills/`, follow it, and put the result in the next brief's Input.

## The summary for Troy

The description of every interface design (PR 1), test plan (PR 2), requirements, and architecture PR opens with the summary for Troy, in Chinese and then English, from `.troy-mode/templates/summary-for-troy.md`: what changes for Troy as a user, each point Troy decides with a recommendation, and the risks, in plain words. This holds whoever merges the PR. troy-check's R22 checks its shape, its length (`[summary] max_chars`, 2,000 characters in each language by default), and that it holds no internal IDs (tstack's F14 design, `docs/troy-mode/design/F14-summary.md`).

1. **Who writes it.** The role that writes the document, in its report's `For Troy` field: IF1 and IF2 for a design, TM1 for a test plan, AR1 for the architecture, and AR6 or AR4 for an architecture change. The engine's brief asks for it in those tasks; for AR4, Input asks (section "Requirement change"). You write the requirements' summary yourself, as the Product Manager (PM1, PM2). Never write the summary of another role's document: that would mean reading the whole document here.
2. **The description.** The report's For Troy block first, unchanged, then Why, What, Checks, and Soft-limit reason.
3. **Read it once** against the template's plain-words rules. You may reword a sentence to make it plainer, but never change what a point, an option, or a recommendation says. A change of meaning goes back to the author as a round.
4. **Local checks.** `troy-check pr --body-file` runs R22. A failure goes back to the author as Input and counts as an attempt, and so does a report with no For Troy block.
5. **AR2** gets the design's summary in its brief's Input, for the checklist's seventh item.
6. **After each revision**, put the new summary in place of the old one: `gh pr edit <number> --body-file <file>`. CI runs again on the edit.
7. **When several PRs wait for Troy at once**, as feature teams make them, ask about all of them in one message, each with its summary (section "Feature teams"). **When the PR waits for Troy**, post `Waiting for Troy: approve this PR` with two lines under it: `Wait: W<n>` (W1 for the requirements or a change of them, W2 for the architecture, W3 for PR 1 and PR 2), then "What to decide is in the summary at the top of the description." Then send Troy the summary in chat, in the language Troy writes in, as the description has it, with the PR's link.

Troy's reply works as section "Merging" says. "全按推荐", "all as recommended", or "approved" approves the PR with every recommendation: record the approval, and say in the description's What that Troy took every recommendation. A reply that picks another option, such as "2: option 2", asks for changes: the author revises, as a round, and the PR waits for Troy again.

## Feature loop

`status` gives the next stage in `next` (`action` `stage`), or the open PR to continue (`continue-pr`). The stage before must have merged on `origin/main`, and `status` only names a stage when it has.

| PR | Title | Author | Reviewers | Local checks before each push | Merged by |
| --- | --- | --- | --- | --- | --- |
| 1 | `[<ID> 1/6 design] <name>` | IF1, then IF2 for each revision | AR2 | `troy-check pr` | Troy for the first features, else you |
| 2 | `[<ID> 2/6 test-plan] <name>` | TM1, with IF3 for its questions | None. At most 3 rounds of questions. | `troy-check pr` | As PR 1 |
| 3 | `[<ID> 3/6 mock] <name>` | DV1 | CR1 | `troy-check pr`, the pack's steps, `troy-check code` | You |
| 4 | `[<ID> 4/6 tests] <name>` | TE1 | TM2 and CR1, together | As PR 3 | You |
| 5 | `[<ID> 5/6 impl] <name>` | DV2 | CR1 | As PR 3, plus the feature's performance cases on Troy's PC when it has a target | You |
| 6 | `[<ID> 6/6 accept] <name>` | PM3, yourself, with the real run (section "PR 6: the real run") | None. TM8 rules on each mismatch. | `troy-check pr`, `real-run` | You |

`<name>` is the feature's name in the requirements; `next.title` and `next.branch` give the title and the branch (`troy-mode/f04-3-mock`). `next.merged_by` says whether Troy approves it. When `continue-pr` names a PR whose `task` is null (a test fix or a `[docs]` PR), read its description and your comments on it to find its author.

### One stage

1. **Branch.** `git fetch origin --prune`, then `git switch -c <branch> origin/main`. Never check out `main`: in a worktree, `main` is often checked out elsewhere.
2. **Author.** Run the stage's author (section "Running a role"). For PM3, follow section "PR 6: the real run".
3. **Commit.** `git add -- <path>` for exactly the paths in `stage`. The first run makes the commit, whose subject is the PR title (R01): `git commit -m "<title>"`. Later runs amend it with `git commit --amend --no-edit`, so the PR keeps one commit. The git hooks check R19.
4. **Local checks**, on the commit (section "Local checks"). A failure goes back to the author as Input and counts as an attempt.
5. **PR.** Write the description from `.github/pull_request_template.md`: for PR 1 and PR 2, the author's summary for Troy first (section "The summary for Troy"), then Why, which starts with `Progress: #<next.issue>` (PR 6: `Closes #<next.issue>`) and then gives the feature's goal, What (the stage's output, with IDs), Checks (what ran and the results), and Soft-limit reason (from the Developer's report, or None), with the template comment removed. Check it with `troy_flow.py check-text --file <file>`. Push with `git push --force-with-lease -u origin <branch>`. The first time, as its own command: `gh pr create --base main --head <branch> --title "<title>" --body-file <file>`. Later pushes: `gh pr edit <number> --body-file <file>`, with the author's new summary after a revision.
6. **Reviews.** Run each reviewer on the PR and post its report as a comment (section "Comments"). AR2 gets the design's summary for Troy in Input. AR2 also writes section 4 of the design, so check, commit with `--amend`, check, and push after it as after an author. `changes-requested` sends the findings to the author as the next round. Pass Troy's comments on the PR (`troy_comments` in `status`) to the author as Input. When a report says what a later feature, or a later stage of this one, must take, record it as a note (section "Notes for later features").
7. **Merge** (section "Merging").
8. **Progress.** After every step (each role run, commit, push, review, merge, and escalation) run `troy_flow.py status --write-progress`.

### PR 6: the real run

PR 6 is yours, as the Product Manager (PM3). Before the feature is accepted, run the real program the way Troy types it, through every command of the prototypes of this feature and of every accepted feature, and put the real output and its comparison in the PR (F12 design). The engine runs and compares; you write the run files and act on the Test Manager's rulings, so you never judge your own prototypes.

1. **Branch.** As in "One stage". Then run `troy_flow.py real-run --item <ID> --json` once on the clean branch: its `no-run-file` problems name the prototypes that need a run file, and its `open_bugs` the bugs of an earlier real run of this feature (step 4).
2. **Run files.** Take a snapshot with `--role product-manager`. Read `${CLAUDE_PLUGIN_ROOT}/skills/principle-prove-it-works/SKILL.md`. Write the run file of every prototype that needs one, `docs/prototypes/<name>.run.toml` next to `docs/prototypes/<name>.md`, from each section's prose. The transcript is the script; the run file holds only what the prose says in words:
   - `[paths]`: each folder the prototype names and where it is during the run, under `<home>` (the run's home folder) or `<scratch>`, for example `'C:\Users\Troy' = '<home>'`, in TOML literal strings.
   - `[environment]`: `unset` and `set`, for variables such as the program's data folder variable.
   - `[start]`: how every section starts: `copy` a folder git tracks, such as the project's test data that matches the example data (`[{ from = "tests/data/example", to = '<home>\recipe-menu' }]`), `mkdir` for empty folders, and `setup` commands such as `["recipe-menu init"]`. A project with no such folder gets one under `docs/prototypes/data/`.
   - `[programs]`: only a command that is not a console script of the project's Python environment, with the repository path of the built program.
   - `[sections."<heading>"]`, with the heading as written (`"<heading> (2)"` for a repeated one): `start` (`"previous"`, `"empty"`, or a table like `[start]`), `replace` (`[{ file, text, with }]`, a text found exactly once, for a section's mistakes), `write`, `delete`, `commands` (`[{ typed, run, reason }]` for a word that depends on the day, such as `next`, replaced by the week it means on the prototype's date; never edit the output), `later` (`[{ feature }]` or `[{ feature, typed }]` for a command that needs a feature not yet accepted), `skip` (`[{ reason }]` or `[{ typed, reason }]` for a command that reads keys or opens an editor), and `files` (`[{ path, block }]` to compare a file the program writes with the section's n-th fenced block that is not a transcript).

   The first PR 6 after F12 reaches a project writes the run files of the earlier features' prototypes too. Check the run, then commit with the PR title as the subject. Do not push yet.
3. **Run.** `troy_flow.py real-run --item <ID> --json` on the clean tree.
4. **Open bugs.** When `open_bugs` names open `bug` issues titled `Real run of <ID>: ...`, their bug flows come first (section "Bug fix"), and you open no second issue for the same mismatch. A new session that reaches stage 6 runs `real-run` first, so it finds them too.
5. **Mismatches.** Exit 1 with mismatches: TM8 rules on all of them in one run, `brief --task TM8 --item <ID> --input-file <files.md>`, with the report's Markdown file as Input. Act on each ruling:
   - `bug`: write the issue to a file, with the prototype, the section, the command, the commit, the diff, and TM8's Summary, check it with `check-text`, and open it with `gh issue create --label bug --title "Real run of <ID>: <summary>" --body-file <file>`. TM8 has triaged it, so TM5 does not run. Its PR A and PR B are side PRs that interrupt stage 6: this stage's commit waits unpushed, and after PR B merges, rebase the branch on `origin/main` and run again.
   - `prototype`: update the prototype in this PR, and list the change with its design section in the description.
   - `requirement`: the requirement change flow; Troy decides which output stays.
   - `later <ID>`: a `later` mark in the run file.
   - `setup`: fix the run file. The description lists every run file change after the first run.
   - `console`: a `skip` mark with the reason.

   Amend the run file and prototype changes into the commit under a new snapshot, and run again (step 3). The PR shows only the last run. A command that still mismatches on its third run gets the premise attempt, as an author's attempts do (section "Rounds and attempts"), and then escalates (W7).
6. **Problems.** Exit 1 with `problems` only: a run file mistake (`run-file`, `unknown-section`, `unknown-command`, `copy-untracked`, `replace-count`, `unknown-later-feature`, `missing-block`, `unmapped-path`, or `setup-failed`) is yours to fix in the run file; then run again. A problem with the program or its environment (`program-not-found`, `environment`, or `code-location`) escalates (W11), with the problem's `fix` as your recommendation when it gives one.
7. **Acceptance.** Exit 0: set the feature's status from the report's `label` in both languages, "Ran for real on Troy's PC" or "Passes tests on main", and raise the requirements' `version` by one minor step in both, with `updated`. Delete the marks that `out_of_date` lists. Amend. The description's Checks section gets the report's `summary`, and a new section after Checks holds the report's `description`, which starts with `## Real run`. Under its "Points at later features", replace "None." with each hint in the real output that names a command or option of a feature not yet accepted, with that feature. With "Passes tests on main", What says why, from `label_reason`. Then run `troy_flow.py costs --item <ID> --json` (D264 to D267): put its `description`, which starts with `## Cost`, after the "Real run" section, as it is. Then `check-text`, `troy-check pr`, push, open the PR, post each of the report's `comments` (each checked with `check-text`), wait for CI, and merge.

Report it to Troy in the shape of Prototype B, with the cost's `line` in Troy's language, for example:

```text
[6/6] Real run: 41 commands of 6 prototypes match on your PC. 3 wait for F12.
      Acceptance PR #96 merged. F11 status is now "Ran for real on Troy's PC".
      F11 cost $103.20 at list prices: 18 role runs, 5 helper agents, and the main session ($25.32).
      Not yet checked in Windows Terminal itself or on your devices.
```

### Local checks

- Always: `python .troy-mode/checks/troy_check.py pr --base origin/main --title "<title>" --body-file <description file>`.
- For a PR with code or tests (PR 3 to 5, bug PRs, test fixes), also the pack's steps from the author's brief `checks`, with `troy-check code` run without `--worktree`, with `--json`, and its output saved: `... troy_check.py code ... > reports/troy-check.json`. Then run `troy_flow.py check-skips --report reports/troy-check.json --junit reports/junit.xml`.
  - Exit 0: the checks passed. When `ci_only` is not empty, the only failures were tests the test plan runs on another platform (D69): count no attempt, list those cases in the description's Checks section as "skipped here, checked by CI", and merge only on CI's result, as always.
  - Exit 1: the `problems` go back to the author as Input, and the run counts as an attempt.

### Rounds and attempts

- **Rounds (R17).** A round is one run of the stage's reviewers. On PR 4 a `changes-requested` from either reviewer fails the round. On PR 2 a round is one question to the Interface Designer and its answer; the test plan's alignment log records each. `status` counts rounds from your comments (`rounds`), so a new session counts on. When round 3 still ends in `changes-requested`, a ruling decides (below); it never stops for Troy.
- **The ruling at round 3 (F18 D173, D174).** `status` gives `next.action` `ruling` with `next.task` and `next.ruling.ruler`: the Product Manager (PM7, `product-manager.md`) when the loop is the Architect's own review (PR 1, or a `[docs]` design update), else the Architect (AR8: `brief --task AR8 --item <ID> [--title <PR title>]`, with the three rounds' findings and the author's answers in Input).
  1. The ruler gives each open finding of round 3 `fix` or `does not block`, with one sentence of reason. A finding that needs a document changed escalates (W6).
  2. Post the ruling on the PR headed `<Ruler> ruling, round 3: merge` when no finding is `fix`, else `<Ruler> ruling, round 3: fix`, where the ruler is `Architect` or `Product Manager`, then one numbered line per finding: `1. fix: <reason>` or `1. does not block: <reason>`. Add to the description's What: "The <ruler> ruled at round 3 (<link to the comment>): <one line>. Troy can overturn it on the feature's progress issue."
  3. `merge`: go on to the merge. `fix` (`next.action` `ruled-revision`): run the author once more with only the `fix` findings in Input. That run is neither a round nor an attempt, unless its checks fail, which counts an attempt as always. Then the ruler checks only those findings (AR8 with "This is the check after the ruled revision" in Input), and you post `<Ruler> ruling, round 3: fixed` or `not fixed` with one numbered line per finding, `fixed` or `not fixed`.
  4. `fixed`: go on to the merge. `not fixed`: `next.escalate` is W7: escalate (W7).
  5. In your report after the merge, tell Troy in Troy's language what was ruled, with the link, and that Troy can overturn it on the feature's progress issue until the feature's acceptance (section "Issues for Troy").
- **Attempts (D64).** An attempt is an author run that reports `failed`, a `done` whose local checks fail, or a CI failure in the author's files. Each stage allows 3. A revision whose checks pass is a round, not an attempt. With a PR, post `<Role> attempt <n>: failed`. Before the PR exists, record it with `troy_flow.py status --note "<Role> attempt <n>: failed"`. `status` gives the count in `next.attempts`.
- **The premise attempt (F18 D175).** After the third failed attempt, `next.premise` is true: run the author once more, with the three failures in Input and `brief ... --premise`. Its brief makes it write down the premise the three attempts shared, test it with a check that changes no file, then fix or report `escalate`, and start its report's Summary with three lines, `Premise:`, `Check:`, and `Result:`. It counts as attempt 4: when it fails, post `<Role> attempt 4: failed` with those three lines under the failing checks. When it fails, or reports `escalate`, `next.escalate` is W7: escalate (W7), giving the premise, the check, and its result, so Troy starts from the evidence; when the evidence names another wait, such as a new dependency (W8) or the architecture (W6), the escalation names that one. When you are the author yourself (PR 6), read `${CLAUDE_PLUGIN_ROOT}/skills/principle-attack-the-premise/SKILL.md` and follow it before your fourth try.
- **Attempts from CI (D261 to D263).** `status` also counts each pushed commit that failed CI in the author's files, once per commit, unless an attempt comment already counts it. Each open PR's `ci_failures` lists its failed commits: `commit`, `runs`, `steps`, `author`, `counted`, `attempt`, and `rerun`. For every entry with an `attempt` number, post `<Role> attempt <attempt>: failed` with the line `Commit: <commit>` right under the heading and the failed `steps`, before anything else, so the PR shows every attempt; the count stays the same. An entry with `author` false is no attempt (section "Merging").

### Comments

Post every review, failed attempt, escalation, and request to Troy as a PR comment whose first line is one of these headings:

- `<Role> review, round <n>: <result>`, for example `Architect review, round 2: changes-requested`, then the findings;
- `<Role> attempt <n>: failed`, then the failing checks. For a CI failure, the first line under the heading is `Commit: <full commit ID>`, the pushed commit that failed;
- `Escalation: <trigger>`, then the line `Wait: W<n>` (W6 to W11), then the escalation message in English;
- `Waiting for Troy: approve this PR`, with two lines under it, `Wait: W<n>` and "What to decide is in the summary at the top of the description.", or `Waiting for Troy: accept <tag>` on a release PR with `Wait: W4` under it. The `Wait:` line always comes right under a `Waiting for Troy:` or `Escalation:` heading; `status` reads it, and the retrospective lists every wait without one;
- `<Ruler> ruling, round 3: merge`, `fix`, `fixed`, or `not fixed`, then one numbered line per finding (section "Rounds and attempts");
- on an acceptance PR: `Real run output, part <n>`, the real output that does not fit the description (section "PR 6: the real run");
- on a release PR (section "Version release"): `Release test, run <n>: passed` or `failed`, `Release test by Troy, run <n>: accepted`, `failed`, or `not accepted`, `Bug deferred by Troy: #<n>`, and `Retrospective: <tag>`.

Under a review heading, write the findings as the role reports them, one numbered line each, starting with the rule ID or checklist item and a colon, for example `1. R05: src/wc.py:12 ...`, so the retrospective can group them.

On issues, troy-mode's comments use the headings of section "Issues for Troy". Every role acts through Troy's account, so the heading records who did what. A comment without one of these headings is Troy's. Write each comment to a file, check it with `troy_flow.py check-text --file <file>` and read its exit code, then post it in a later call with `gh pr comment <number> --body-file <file>` (section "Text for GitHub").

### Merging

Merge a PR only when every review of the stage ended in `approved`, or a ruling at round 3 ended in `merge` or `fixed` (`next.ruling.result`), the local checks passed on the pushed commit (or `check-skips` left only `ci_only` cases), `wait-checks` reports `passed` for the commit you pushed, and the merge rights allow it (`merged_by` is `f07`). Then:

1. `troy_flow.py wait-checks --pr <number> --sha <sha>`, with the full commit ID you pushed (`git rev-parse HEAD`). Read its exit code and `result` (D204):
   - `passed` (exit 0): go on.
   - `pending`: the time ran out first. Run it again; that is still the same wait. Right after a push GitHub may not have registered the workflow yet, and `wait-checks` waits for that too. If a second run still says "No check has reported", escalate (W11).
   - `failed`: a failing check (below).
   - `other-head` or `closed`: the PR's head is not the commit you pushed, or the PR is no longer open. Stop and find out why before anything else.
2. `git switch --detach`
3. `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>`, with the same full commit ID
4. `git fetch origin --prune`
5. `troy_flow.py status --write-progress`, then the issue sync (section "Issues for Troy")

Run each step as its own command, and the merge only after you have read the wait's exit code: never chain the merge after the wait with `;` (or in any other way on one command line). In the pilot, `gh pr checks --watch; gh pr merge ...` merged a PR before its checks had reported (ZJUCao/recipe-menu#47). Detach first, so that `gh` does not try to check out `main` before it deletes the branch.

- **A failing check.** Run `troy_flow.py status` and find the commit you pushed in the PR's `ci_failures`. With `author` true, the run counts as an attempt: post `<Role> attempt <attempt>: failed` with `Commit: <commit>` and the failed steps (section "Rounds and attempts"), then give the author the failing log (`gh run view <run ID> --log-failed`, for each ID in `wait-checks`' `runs`) as Input. With `author` false, the failure lies outside the author's files, such as in the checkout, the setup, or on the runner, and counts no attempt. When its `rerun` is false, re-run the failed jobs once, `gh run rerun <run ID> --failed` for each ID in `wait-checks`' `runs`, and run `wait-checks` again on the same commit. When `rerun` is true, the re-run failed again: escalate (W11). In the pilot, the one such failure passed on the next run.
- **A refused merge.** If the agent's permissions refuse `gh pr merge`, escalate (W10) with the permission to add. Never work around a refusal.

**Troy's approval (D61).** When `merged_by` is `troy` (PR 1 and PR 2 of the first `troy_approves_first` features, the requirements, the architecture, and a requirement change), post `Waiting for Troy: approve this PR` with its two lines (W1 for the requirements or a change of them, W2 for the architecture, W3 for PR 1 and PR 2), run `troy_flow.py status --waiting "<what>" --wait W<n>`, send Troy the summary for Troy with the PR's link (section "The summary for Troy"), and stop. Troy replies in chat, in a comment or a "Comment" review on the PR, or merges on GitHub. A comment counts as a reply in chat (F15 D145): "全按推荐", "all as recommended", or "approved" approves the PR, and picking another option asks for changes. `status` ends the wait and lists it in `troy_comments`; the description's What then says that Troy approved in a comment.

- **Troy approves in chat.** Run `troy_flow.py approve --doc <document>` (the design for PR 1, the test plan for PR 2, `docs/requirements.md`, or `docs/architecture.md`). It changes only header fields, the change logs, and, for the architecture, the status words of the ADRs it lists (D202), so no role runs. Stage every path in `changed`, amend the commit, run the local checks, push, wait for the checks, and merge. When it exits 1 because a file has no change-log table (D201), it has changed nothing: the document's author adds the table under the template's heading, with the problem as Input, as for a revision; then commit and run `approve` again.
- **Troy asks for changes.** The author revises, as a round.
- **Troy merged on GitHub.** The document's approval is not recorded, and `status` gives `record-approval`: on `next.branch`, run `approve --doc <next.doc>`, stage every path in `changed`, commit as `next.title` (`[docs] Record Troy's approval of <document>`), check, open the PR, and merge it yourself.

**After the first features (D62).** When `status` gives `ask-approvals`, ask Troy once whether to go on approving PR 1 and PR 2 of later features, and how many, and run `troy_flow.py status --waiting "Troy decides on later approvals" --wait W3`. Record the answer in `.troy-mode/config.toml`'s `[flow] troy_approves_first`, with a comment line above it that names the decision and its date, in a `[rules] Set the features Troy approves` PR, and merge it. Apart from troy-init's steps and the rule change flow (section "Rule change"), this is the only config change you make.

## Feature teams

Features that may start at the same time are built at once, each by its own team in its own git worktree (tstack's F20 design, `docs/troy-mode/design/F20-parallel-teams.md`). One team is one feature's role runs, from PR 1 to PR 6, and it runs the feature loop above unchanged. When only one feature may start and no team runs, everything above holds as it is.

### When teams start

1. **Teams mode.** `status` is in teams mode when a team worktree exists or two or more features are dependency-ready. A feature already under way in this checkout stays here.
2. **`next` is `plan`.** Run AR7 for the version: `brief --task AR7 --item <version> --input-file <file>`, with Input listing the features of `items` and the running teams of `teams` with their lines of the plan. Write AR7's report to a file under the git folder and run `plan --report <file>`. A problem goes back to AR7 once, as Input; a second one escalates (W11).
3. **`next` is `team-start`.** For each item, `team start --item <ID>`. Each team's progress issue comes with the next sync.

### The loop

1. **Each team's next action.** For each entry of `teams` with no `running` role and no `held` reason, do its `next` as the feature loop above says, in the team's worktree: `git -C <worktree>` for git and `--repo <worktree>` for the engine, never a bare `cd`, since your `cd` lasts and the next command may belong to another team. A stage's branch is `git -C <worktree> switch -c <branch> origin/main`.
2. **All at once.** Start the next role of every team that has one, then wait for any report, handle that team's report, and go back to step 1. Where the Agent tool has `run_in_background`, as in `claude -p`, pass it as `true` while two or more teams run, so that their roles run at once; in the desktop app every role already runs in the background.
3. **AR7's check.** After AR2 approves a team's design (PR 1), and before it merges, run `brief --task AR7 --item <ID> --title <PR 1 title>` with Input holding the plan (`plan.json` in the common git folder) and the running teams' merged designs. When it gives new lines, keep them with `plan --report`; a team that must wait then stops after its current stage (`held` `plan`).
4. **Short messages.** One line per team event. Read role reports, never whole diffs. After a compaction, run `status` before anything else.
5. **`team-end`.** After PR 6 merges, `team end --item <ID>`. A `running` problem names the agents to end with `TaskStop` first.

### Merging a team's PR

Ready PRs merge in the order they became ready (R24).

1. `git -C <worktree> fetch origin --prune`, then `merge-check --repo <worktree>`.
2. **`rebase`.** `git -C <worktree> rebase origin/main`.
   - **Clean:** push with `--force-with-lease`, run the local checks again, and run `merge-check --repo <worktree> --rebased-from <old head>`. With `review_again`, CR1 reviews the rebased diff as the next round. Wait for CI on the new head, then run `merge-check` again.
   - **A conflict:** list the conflicting paths (`git -C <worktree> diff --name-only --diff-filter=U`), run `git -C <worktree> rebase --abort`, then `merge-check --repo <worktree> --conflicts <path>...`. Make the stage's branch again from `origin/main` (`git -C <worktree> switch -C <branch> origin/main`) and run the `owner` role once more, with Input holding its old diff (`git -C <worktree> show <old head>`) and the paths, asking for the same change on the new main. For `product-manager`, write PR 6's status row again yourself, with a snapshot. With `escalate`, escalate (W11). A redo counts neither as an attempt nor as a round.
3. **`outside-plan`.** Run AR7's check with the PR's diff in Input before the merge.
4. **`held`.** A later version's PR 3 to PR 6 waits for the earlier version's release.
5. **`ready`.** `wait-checks` on the head, then merge as section "Merging" says.
6. **Performance cases.** Before PR 5's performance cases run on Troy's PC, wait until no other team's role runs, and start none meanwhile.

### Waits, changes, and rules

- A team that waits for Troy, or escalated, stops. The teams that wait for its feature wait too; the others go on.
- **An overturn** holds its feature's team after its current stage PR (`held` `overturn`) until it is carried out (section "Issues for Troy"); the other teams go on.
- Ask Troy in one message about every PR in `waiting`, each with its wait ID (`wait`), the one that holds up the most features first, each with its summary and link. Troy answers them together, "全部批准" or "approve all", which approves each listed PR with every recommendation, or one at a time. An escalation comes in a message of its own.
- **A requirement change.** Take it in before you start the next team. The change PR's description has a line `Affects: <IDs>`, from PM2's list; `status` then holds those teams (`held` `change`) once their current stage PR merges, and the others go on.
- **A rule change** runs in this checkout. Every team picks it up at its next stage, and an open PR at its rebase.
- **Shared documents** (the requirements, the architecture, ADRs, and version test plans) change only in this checkout, as your own PRs; the hooks refuse them in a team's worktree. So AR3's write after Troy accepts a dependency, AR4, and AR6 run here, never in a team.

### Usage limits and continuing

When a usage limit stops the session, every team pauses with its state in git, on GitHub, and in its worktree. On "continue", `status` rebuilds every team from its worktree, the open PRs, and the plan. A role that the limit cut off leaves a `running` record: end it with `TaskStop`. When a team's role stopped without a report, undo that run's own changes and run the role once more.

## Notes for later features

A review often finds what a later feature, or a later stage of this one, must take: what to reuse from this feature's module, a rule its design must follow, a timing model for its speed target. Never keep such a note in your own memory or in the progress file. Record it on GitHub, so that it reaches that feature's briefs from any session, PC, or team worktree (F07 design 6.6):

1. Write the note in your own words, in English, to a file under `$(git rev-parse --absolute-git-dir)/troy-mode/flow/`.
2. `troy_flow.py note --for <feature ID> --from "<source>" --file <file>`, where the source is the PR, the role, and the round, such as `#57, Code Reviewer, round 1`, or `Troy, in chat` for a note Troy gives. It refuses an accepted feature: a change to one is a requirement change.
3. Check its `file` with `troy_flow.py check-text --file <file>` and read the exit code, then run its `gh`, a `gh issue comment` on the progress issue it picked.

`brief` then adds the feature's notes to the Input of every IF1, IF2, and DV2 run of that feature, so you never copy them by hand. `status` lists them in `feature_notes`, and a note that came after the feature's PR 1 or PR 5 opened is late: decide whether it needs a design update in a `[docs]` side PR with IF2, a line in the open PR's next round, or nothing, and say so in your report to Troy.

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
- **Code that cannot be tested in practice:** run the Developer again to exclude those lines with a written reason; TM6 approves or rejects the reason. A rejection goes back to TM3's other answers, or escalates (W6).

### New dependency (R16)

An author reports `needs-answer` for the Architect about a new third-party dependency.

1. AR3 reviews it and reports `escalate` with a recommendation. Escalate to Troy (section "Escalation", W8).
2. **Troy accepts:** on `troy-mode/<id>-docs`, AR3 runs again with Troy's decision in Input and `--title "[docs] Accept the dependency <name>"`; it adds the dependency and an ADR to the architecture. Open and merge that PR. Back on the stage branch, run the author again with the decision; `check-run` gets `--allow-dependency <path>` for each dependency file the decision covers, such as `pyproject.toml`. Then the series lock (D66): run `troy_flow.py series`, run its `commands`, then each member's `tests.commands` in its `tests.cwd`. Stage the new lock with the author's files. A member whose tests fail stops the flow: escalate. The PR description lists the members in `stale`, whose lock is now out of date; open no PR in them.
3. **Troy refuses:** run the author again with the decision: do without the dependency. `check-run` gets no `--allow-dependency`.

## Bug fix

1. **Issue.** When Troy names an issue ("fix #12"), read it with `gh issue view <n>`. Otherwise open one: write the report in English to a file, check it with `troy_flow.py check-text`, and run `gh issue create --label bug --title "<summary>" --body-file <file>`. The issue's number gives the bug ID: issue 12 is `B12`.
2. **Triage.** TM5, with the issue in Input (`brief --task TM5 --item B12`). A misunderstood requirement goes to the requirement change flow, whose PR waits for Troy (W1). A bug goes on. A bug from a real run starts at its issue, `Real run of <ID>: <summary>`, which TM8 has triaged, so TM5 does not run for it.
3. **PR A.** On `troy-mode/b12-test`, TE2 writes the reproduction test with `--title "[B<n> A/B test] <summary>"` (the issue's summary). Its local checks show that B12's tests fail (R09). Open the PR (Why: the issue's link; What: the test), run TM2 and CR1 together with the same `--title`, and merge.
4. **PR B.** `status` now gives `bug` with `next.title` (`[B<n> B/B fix] <summary>`) and `next.branch` (`troy-mode/b12-fix`), so a new session finishes the bug too. DV3 fixes it (`brief --task DV3 --item B12`); B12's tests must pass. The description's Why says `Fixes #<n>`, so GitHub closes the issue when you merge. CR1 reviews it, and you merge.

A dispute or a new dependency during a bug runs as in section "Side PRs", with the bug ID as `<ID>`.

## Requirement change

1. **PM2.** On `troy-mode/change-<slug>` from `origin/main`, under a snapshot with `--role product-manager`, update `docs/requirements.md` and its mirror:
   - the requirement itself;
   - each affected feature that is not yet accepted: Status `Needs rework (<the change>)`;
   - each affected feature that is accepted (D65): keep its status and add a new feature for the change, with the next free ID, a short name, a hard dependency on the old one, and Status `Not started`; put it in the topological order right after the features it depends on and before the features not started yet, unless Troy says otherwise, and in the version plan;
   - raise `version` by one minor step in both, with `updated`, and add a change log row.

   Write the summary for Troy of the change (section "The summary for Troy"). Commit as `[docs] Change the requirements: <summary>`, run `troy-check pr`, open the PR with the summary at the top of its description, and wait for Troy's approval (section "Merging"). A Feature cell keeps to the feature's short name. With feature teams, the description also has a line `Affects: <ID>, <ID>` listing the affected features, so `status` holds their teams (section "Feature teams").
2. **AR4.** For each affected feature, run AR4 with the change in Input (`brief --task AR4 --item <ID>`), and add to Input: "If the architecture must change, write the summary for Troy from the summary-for-troy template in your report's For Troy field." When AR4 reports an architecture change, escalate it (W6) with AR4's ADR as the recommendation; on Troy's yes, put the ADR in a `[docs] Change the architecture for <ID>` PR on `troy-mode/<id>-architecture`, with AR4's summary at the top of its description, and merge it.
3. **A feature not yet accepted** goes back to the earliest stage AR4 names. When its open PR's stage is at or after that stage, close it unmerged: `gh pr close <number>`. Then run that stage again with its usual title and branch, giving the title with `brief --title` (a redo; the engine allows it while the feature is in rework). When the feature's implementation has merged and its tests change, start at stage 3 at the latest: R09 needs every test of the feature to fail against a mock. Once the redo merges, `status` goes on from there.
4. **An accepted feature** gets its new feature through the feature loop. Put AR4's list into each brief's Input:
   - IF1: section 2 holds only new interfaces, or says there are none (no subsection); section 3 lists the changed interfaces.
   - TM1: name the old cases that the change retires, and move them from the old feature's test plan to its "Not tested" section with the reason, in both languages, in the same PR.
   - TE1: delete the retired tests and add the new cases, which fail against the current code (R09).
   - When section 2 adds no interface, `status` skips PR 3 and goes from PR 2 to PR 4.

When `status` gives `rework` (a new session, or a stage PR opened before the change, in `next.pr`), run AR4 for `next.item` and go on from step 3.

## Version release

tstack's F08 design (`docs/troy-mode/design/F08-release.md`) is the source for this flow. "Release v0.1", or "continue" when `status` gives `release`, runs it; "release" alone means the version that `status` names in `release.tag`. `status --json` has `versions` (each version's features, plan, released tags, and `patch`) and `release` (the release in progress or due: its tag, plan, release PR, `runs`, `open_bugs`, `deferred`, and `problems`).

### The version test plan (D70)

`status` gives `version-test-plan` before any new stage of a feature whose version has no test plan, or whose plan lists other features than the requirements give that version.

1. On `next.branch` (`troy-mode/v0.1-test-plan`), run TM7: `brief --task TM7 --item v0.1`. It writes `docs/versions/v0.1/test-plan.md` and its mirror; each scenario says in Run by whether Claude runs it, as a version test, or Troy, on a device only Troy has. In PR text and comments, call Claude's scenarios automated scenarios or version tests: R19's strict mode refuses the name.
2. Check the plan yourself as the Product Manager: every feature of the version is in section 1, and every user flow of those features has a scenario. A gap goes back to TM7 as Input. No other role reviews it.
3. Commit as `next.title`: `[docs] Add the <version> test plan`, or `[docs] Update the <version> test plan` when the version's features changed. Run `troy-check pr`, open the PR, and merge it yourself: it is not one of Troy's approvals.

### The release steps

| Step (`next.step`) | What you do | PR | Merged by |
| --- | --- | --- | --- |
| 1. Ready | Read `release.problems` and fix each one first (below) | None | |
| 2. `version-tests` | TE5 writes the tests of the scenarios Claude runs; TM2 and CR1 review them together | `[<version> tests] End-to-end and stress tests` on `troy-mode/<version>-tests` | You |
| 3. `release-pr` | PM4: the changelog section | `[docs] Release <tag>` on `troy-mode/release-<tag>` | You, after Troy accepts |
| 4. `security-review`, then `release-test` | CR2's security review of the release's changes, on a local review branch; then the regression, the version tests, and the real run of every accepted feature's prototypes on Troy's PC; each report goes on the release PR | None | |
| 5. `troy-test` | Troy runs Troy's scenarios on Troy's devices and replies | None | |
| 6. `accept` | PM4 sets the statuses, `accept-version` fills the acceptance record, then the merge | The release PR | You |
| 7. `tag` | A GitHub release on the release PR's merge commit | None | |
| 8. `retro` | The retrospective | None | |

**1. Ready.** Each entry of `release.problems` names its fix:

- A feature of the version is not accepted: tell Troy which, and stop. A release request does not reach the feature loop (D63): Troy asks for the features, such as "the rest of v0.2", and for the release afterwards.
- An open troy-mode PR: `status` continues it first; the release PR always comes last.
- An open `bug` issue: fix it through the bug flow, unless Troy defers it in chat. Record a deferral on the release PR as soon as it exists, as `Bug deferred by Troy: #<n>` followed by Troy's words.
- A mock, tests, implementation, or acceptance PR of a later version's feature merged since the previous release: the tag would hold a feature the version does not include. Escalate (W6) with Troy's options: ship that feature in this version through a requirement change, or release later.
- The test plan is missing or lists other features: TM7 first (above).
- The project's troy-mode files are older than the plugin's: run the upgrade (section "Upgrade") first; the version tests PR needs the new troy-check.

**2. Version tests (D71).** On `next.branch`, run TE5 (`brief --task TE5 --item <version>`). It writes one test per scenario that Claude runs, in `version-tests/`, each named with its scenario ID (`test_v0_1_s01_...`, `TEST(Version, V0_1_S01_...)`), and runs them against `origin/main`'s code. A test that fails there stays as written; its report lists it. Commit as `next.title`, run the local checks of the brief (the pack's steps never collect `version-tests/`, so the release command at the end of the checks runs them), open the PR, and run TM2 and CR1 together with `--item <version>`. Merge it when both approve and CI passes, even when some version tests fail: CI does not run them, and a failing scenario is a finding of the release test. A patch release has no version tests. Every PR of a version's tests is titled `[<version> tests] <summary>`: a wrong version test is fixed later by TE3 in `[<version> tests] Fix <scenario ID>`, on TM4's ruling, with that title in `brief --title`.

**3. Release PR (D72).** On `troy-mode/release-<tag>` from `origin/main`, under a snapshot with `--role product-manager`, do PM4: add the version's section to `CHANGELOG.md` and its mirror from the `changelog` template (create both for the first release), with the version's features and the bugs fixed since the previous release sorted into Added, Changed, and Fixed. A feature that changes an accepted one goes under Changed; a patch lists only Fixed. The section's date is today. Commit as `[docs] Release <tag>`, run `troy-check pr`, and open the PR with Why (the version's line in the version plan), What (the changelog section and the features), and Checks. Every later step comments on this PR, so a new session finds the release where it stopped.

**4. Security review (tstack #75).** At the step `security-review`, before the release's first release test, CR2 reviews every change since the previous release with `/security-review`. The per-PR reviews ran it only where a PR added a risk (F04 D280 to D283).

1. From the release branch, run each command of `release.review.commands` in order: `git remote set-head origin --auto` when it is there, then `git commit-tree`, which prints a commit ID, then `git switch -c <release.review.branch> <commit>` with that ID. The branch's one commit puts `origin/main`'s files on the previous release commit, so `/security-review` sees all of the release's changes. Never push it.
2. Run CR2 as in "Running a role": `brief --task CR2 --item <version>`, a snapshot with `--role code-reviewer`, the Agent call, and `check-run`.
3. Write the report's findings to a file headed `Security review, run <release.review.run>: approved` or `changes-requested`, check it with `check-text`, and post it on the release PR.
4. `git switch <the release branch>`, then `git branch -D <release.review.branch>`.
5. `changes-requested`: each blocking finding goes to TM5, as in "Failures and bugs". Once the bugs are fixed, `status` gives `security-review` again, as the next run. `approved`: `status` goes on to `release-test`, and the review is not repeated for this release.

**4. Release test.** On the release branch, on Troy's PC:

1. Run every command in `release.checks` (`status` fills it at this step): the pack's steps, `troy-check code` with the release PR's title, and the release command, which writes `reports/version-junit.xml` (Python: `pytest version-tests`; C/C++: a build with `TROY_VERSION_TESTS=ON`, then `ctest -L version`). Performance and stress cases run here. Every regression test must pass, or skip on this platform with CI's result on `main` (`check-skips`, D69).
2. `troy_flow.py real-run --all --json`, on the same commit, after the version tests: the command Troy types, through the prototypes of every accepted feature (F12 design 11). Its JSON report is `files.json`.
3. `troy_flow.py release-test --version <version> --junit reports/junit.xml --junit reports/version-junit.xml --real-run <files.json>`. Write its `comment` to a file, check it with `check-text`, and post it on the release PR. Its first line is `Release test, run <n>: passed` or `failed`; a real run mismatch fails it.
4. A failed run goes to "Failures and bugs" below before Troy is asked to test.

**5. Troy's test.** After a run that passed, run the issue sync: it creates the device-test checklist, one box per scenario Troy runs and the accept box last (F15 D144). Post `Waiting for Troy: accept <tag>` with the line `Wait: W4` on the release PR, run `troy_flow.py status --waiting "Troy tests <tag>" --wait W4`, and tell Troy in Troy's language, with the checklist's link: the commit to test and the release PR's link with the changelog; the scenarios Claude ran, with their results; and each scenario Troy runs, with its device, steps, and expected result (the report's `scenarios` with `run_by` Troy). Then stop. At the next run, `issues.device_test` gives the checklist's `result`: `ticked` (every box ticked, the last one included) is Troy's acceptance: post `Release test by Troy, run <n>: accepted` on the release PR, with Troy's comments on the checklist as Troy's notes, and go on with step 6. `incomplete` (the accept box ticked while a scenario is not): ask Troy which is meant, with `Waiting for Troy: <question>` and `Wait: W4` on the checklist and in chat. A scenario left unticked with a comment of Troy's (`troy_comments`): a failure is recorded as `Release test by Troy, run <n>: failed` with Troy's words; a question or a note gets a `Reply to Troy`. Troy can still reply in chat or as a comment on the release PR; an acceptance given there needs no ticks. Record Troy's reply as a comment `Release test by Troy, run <n>: accepted`, `failed`, or `not accepted`, followed by Troy's words:

- **Accepted**, with any notes: step 6.
- **A scenario failed:** "Failures and bugs". Troy then tests again only the scenarios that failed, unless Troy asks for more (D74).
- **Not accepted** for a reason that is not a bug, such as a feature that is not what Troy wanted: the requirement change flow. The release waits until the changed features are accepted again.

**6. Acceptance and 7. tag (D73).** On Troy's acceptance:

1. PM4, on the release branch under a snapshot with `--role product-manager`: each feature of the version gets the status "Usable on Troy's devices" in both languages (R13), the requirements' `version` rises by one minor step with a change-log row, and the changelog section takes today's date. A patch keeps the features' statuses.
2. After `check-run` of the Product Manager's run has passed and its paths are staged, write Troy's notes, and any bugs Troy deferred, to a file, then run `troy_flow.py accept-version --tag <tag> --notes-file <file>`. Like `approve`, it is the engine's change, outside any role's snapshot: run it after the snapshot's check, never inside it. It adds the acceptance row, raises the plan to the next major version, and adds its change-log row, in both languages.
3. Run `troy_flow.py costs --tag <tag> --json` and put its `description`, which starts with `## Cost`, into the release PR's description after Checks, as it is (D264 to D267). Stage both sets of paths, amend the commit, run the local checks, push, update the description with `gh pr edit`, wait for CI, and merge (section "Merging").
4. `git fetch origin --prune`, then `troy_flow.py release-notes --tag <tag> --out <file>`, then check the notes with `troy_flow.py check-text --file <file>` and read its exit code, then `gh release create <tag> --target <merge commit> --title <tag> --notes-file <file>`, where the merge commit is the full ID of the `[docs] Release <tag>` commit on `origin/main` (`status` gives it as `next.commit` for `tag`). GitHub creates the tag on that commit; nothing is pushed from Troy's PC.
5. Report to Troy, with the cost's `line` from step 3 in Troy's language, and run `troy_flow.py status --write-progress`.

If Troy merges the release PR on GitHub instead, `status` gives `record-acceptance`: on `next.branch`, do step 1 and step 2 with Troy's words, commit as `next.title` (`[docs] Record Troy's acceptance of <tag>`), check, open, and merge it yourself, then step 4. Creating the GitHub release is one of your rights, only after Troy's acceptance and only on the release PR's merge commit.

### Failures and bugs (D74)

After bug fixes, when the release test passes again, the issue sync updates the checklist: its `edit` action has `new_run: true`. Post `Device test, run <n>: ready` on the checklist, naming the scenarios to test again, and tell Troy in chat.

- A real run mismatch goes to TM8 with `real-run`'s Markdown report in Input (`brief --task TM8 --item <version> --input-file <files.md>`), and its rulings are acted on as in section "PR 6: the real run", with each bug's issue titled `Real run of <feature ID>: <summary>`.
- A failed test or scenario, in the release test or in Troy's test, or a blocking finding of the security review, goes to TM5 with the report in Input. A bug gets an issue and the bug flow's PR A and PR B (section "Bug fix"). A wrong version test gets TE3's fix. A misunderstood requirement goes to the requirement change flow.
- `status` gives the step `bugs` with the first open bug issue that Troy has not deferred; the release waits until every open `bug` issue is fixed or deferred.
- After the fixes, PM4 adds the fixed bugs to the changelog section, rebase the release branch on `origin/main`, amend the commit, and push; `status` then gives `release-test` again, and the release test runs as the next run. It runs every version test; Troy tests again only what failed.

### Patch releases (D75)

"Release v0.1.1" releases the bug fixes merged since v0.1.0. Read `versions[].patch` of v0.1: when `fixes` is empty, tell Troy that no fix has merged since the last tag; when `blocked_by` is not empty, a later version's code has merged, so the fixes ship with the next version: say so and stop. Otherwise run steps 1 and 3 to 7: no version test plan, no version tests. The release test runs the same regression and every version test, and Troy tests the scenarios that the fixed bugs touched. The changelog section lists only Fixed, the features keep their statuses, and `accept-version` adds a row for the patch to the version's acceptance record. A patch has no retrospective.

### Retrospective (D76)

After a version's tag, `status` gives `retro` until its release PR has a `Retrospective: <tag>` comment.

1. `troy_flow.py retro --tag <tag>` groups the evidence of the PRs merged since the previous version's tag: the findings of every review that requested changes, by the rule ID or checklist item each one names; every failed attempt, with each commit that failed CI in the author's files and that no comment counts (`ci_attempts`); every escalation; the bugs fixed; and the `hooks.log` lines. `repeated` lists the groups seen in two or more PRs.
2. Read `${CLAUDE_PLUGIN_ROOT}/skills/correct/SKILL.md` and follow its method on each repeated problem: the strongest enforcement that works, and whether it belongs to this project or to every troy-mode project. Write no code: every proposal is a rule for the rule change flow.
3. Send Troy one message: each repeated problem with its evidence and PR links, and each proposal with a recommendation (W5). Add `retro`'s `waits` by ID with their hours, and every `unlisted` wait, which is a stop the list does not allow, and its `rulings`, `premise_attempts`, and `overturns`. When nothing repeated, say so. Post the same report in English on the release PR as `Retrospective: <tag>`, which ends the release.
4. Each rule Troy picks runs through the rule change flow (section "Rule change"), one at a time. List the picked rules in the progress file with `status --note`, so a new session finds those still to do.

## Rule change

tstack's F09 design (`docs/troy-mode/design/F09-rule-change.md`) is the source for this flow. Only troy-init and this flow change `docs/rules.md` and `.troy-mode/**`; no role does.

| Request, for example | What it is |
| --- | --- |
| "add a rule: no print calls in source", "a rule for this project: ..." | A project rule |
| "a rule for every project: ..." | A rule for every project |
| "change P01 ...", "retire P02" | A change or a retirement |
| "in this project, R03's limit is 800 lines" | A project rule that adjusts an R rule |
| The rules Troy picks in a retrospective | One at a time, as above |

When the request does not say whether the rule is for this project or for every troy-mode project, ask Troy that one question and recommend this project: a rule for every project changes tstack, which is a bigger step. Ask in the same message for anything else the rule needs, such as what it covers.

### A project rule

| Step | What happens | Who | PR | Merged by |
| --- | --- | --- | --- | --- |
| 1. Ask | The rule and its scope, when the request does not give them | You | None | |
| 2. Enforcement | The strongest level that works, the exact config, and the existing violations | AR6 | None | |
| 3. Proposal | One message to Troy, and Troy's answer | You | None | |
| 4. Architecture | Only when the rule needs the architecture to change | AR6's second run | `[docs] Change the architecture for <ID>` | You |
| 5. Rule PR | The rules table, the config, and the baseline | You, under `snapshot --role rules` | `[rules] Add <ID>, <summary>` | You |
| 6. Cleanup | Only when Troy chose to fix the existing code now | DV5 or TE6; CR1, and TM2 for tests | `[refactor] Apply <ID> to <area>`, `[<ID> test-fix] Apply <ID> to tests` | You |

Each PR has one commit whose subject is its title (R01). Troy's answer in step 3 is the approval, so no PR of this flow waits for Troy again (D82).

**2. Enforcement (D79, D80).** Run `troy_flow.py rule-id`: `next_id` is the new rule's ID, and `rules` lists the P rules with their `baseline` lines. Run AR6 (`brief --task AR6 --item <ID>`) with Troy's words in Input, under a snapshot with `--role architect`. AR6 changes no file: undo anything it changed and run it once more. It reports `escalate` with the proposal in Question: the strongest level that works and why no stronger one does (the architecture, a check of a tool the pack runs or a troy-check limit, a step without an environment in `.github/workflows/project-rules.yml`, or a Review or Process row), the row's cells in both languages, the config change or the architecture change, the existing code that breaks the rule with the files and the count, the baseline lines, and the cleanup PRs it expects. A test never enforces a project rule (D80).

**3. Proposal (D82).** Send Troy one message, in Troy's language:

- the rule as the table will say it, in English and Chinese, with its ID, its type, and Enforced by;
- the enforcement, and why no stronger level works;
- the files the rule PR changes, and the architecture PR, if any;
- the existing code that breaks it, and the choice, with your recommendation: fix it now in cleanup PRs, or apply the rule only to new and changed code. When the tool has no per-file exemption that a `[rules]` PR may change, such as clang-tidy, whose suppressions live in source files, offer only "fix it now": the cleanup PRs come first, and the rule PR turns the check on after them, with no baseline.

Run `troy_flow.py status --waiting "Troy approves rule <ID>" --wait W5` and stop. Troy's answer approves the rule and makes the choice, or asks for a change: then run AR6 again with Troy's words in Input and show the new proposal. Nothing is written before Troy approves.

**4. Architecture.** Only when the approved enforcement changes the architecture: on `troy-mode/<id>-architecture` from `origin/main`, run AR6 again with `--title "[docs] Change the architecture for <ID>"` and Troy's approval in Input. It writes the change and an ADR in both languages, and the summary for Troy in its report. Commit, run `troy-check pr`, open the PR with that summary at the top of its description, and merge it. R02 keeps documents out of a `[rules]` PR, so this PR comes first.

**5. Rule PR (D80, D81).** On `troy-mode/rule-<id>` from `origin/main` (for example `troy-mode/rule-p01`), run `troy_flow.py snapshot --role rules`. Its scope is the `config` and `dependencies` path classes, which is all a `[rules]` PR may change. Then:

1. **Rules table.** Write the row's cells and the change-log text, each in English and Chinese, to a JSON file under `$(git rev-parse --absolute-git-dir)/troy-mode/flow/`: `{"rule": {"en": "...", "zh-CN": "..."}, "type": {...}, "enforced_by": {...}, "change": {...}}`. The type is `Hard` (硬), `Soft` (软), `Review` (审查), or `Process` (流程). The change-log text names the rule's ID and Troy's approval, and ends with Troy's choice in exactly these words, which `status` reads: `Existing code: fixed by cleanup PRs.` or `Existing code: fixed when touched.` (in Chinese, 已有代码：用清理 PR 修复。 or 已有代码：改到时修复。). Run `troy_flow.py rule-row --id <ID> --rule-file <file>`. It adds the row to `docs/rules.md` and its mirror, moves both to the next major version with "Approved by Troy on <date>", and adds the change-log row.
2. **Config.** Make AR6's config change.
3. **Baseline.** When existing code breaks a check, exempt today's violating files in the tool's own config, one line per file, each with the comment `baseline: <ID>`. In Python these are entries of ruff's `per-file-ignores` in `pyproject.toml`, for example `"src/wordcount/count.py" = ["EM102"]  # baseline: P01`. New files must follow the rule at once. Keep each baseline line on one line, so a cleanup removes it whole.
4. **Check.** `troy_flow.py check-run --run <run ID>`, with `--allow-dependency <path>` for each dependency file the approved config change names, such as `pyproject.toml`. A docs, source, or tests path is a scope problem. Stage exactly the `stage` paths and commit as `[rules] Add <ID>, <summary>`.
5. **Local checks.** `troy-check pr`, and, when a tool's config changed, that tool's steps of the pack in the project's environment, for example `mamba run -n <environment> ruff check` and `ruff format --check`, so the new rule and its baseline pass before the push.
6. **PR and merge.** The description says Why (Troy's rule, in English), What (the row, the config, and the number of baseline lines), and Checks. Check it with `check-text`, push, open the PR, wait for CI, and merge it yourself (section "Merging"). No role reviews it: Troy approved its content in step 3.

A review rule (type Review) needs no config: its rule PR adds only the row, and the reviewers that its Enforced by names check it from then on.

**6. Cleanup (D81).** When Troy chose "fix it now", `status` gives `cleanup`, with the rule in `next.item`, until no `baseline: <ID>` line is left; the report's `rules` entry lists the lines, and a new session finds the cleanup the same way. It comes after the open PRs and before the feature loop's next stage. Group the baselined files into PRs of at most 5 files, each within R03:

- **Source files:** `[refactor] Apply <ID> to <area>` on `troy-mode/<id>-cleanup-<area>`, written by DV5 (`brief --task DV5 --item <ID> --title "<title>"`, with the PR's files in Input) and reviewed by CR1.
- **Test files:** `[<ID> test-fix] Apply <ID> to tests` on `troy-mode/<id>-test-fix`, written by TE6 and reviewed by TM2 and CR1 together.

Each removes its files' baseline lines in the same commit. `check-run` lets a dependency change through without `--allow-dependency` when it only deletes `baseline:` lines. Commit, run the local checks of the brief, open the PR (Why: Troy's choice to fix the existing code now; What: the files and the baseline lines removed), run the reviewers with the same `--title`, and merge. A review rule's cleanup follows AR6's list of files the same way, without baseline lines. When Troy chose "only new and changed code", the baseline stays: the Developer and the Test Engineer fix a baselined file whenever they change it, and remove its line, as their instructions say.

### Changing and retiring rules (D84)

- **A P rule changes** through the same steps, with `[rules] Change <ID>, <summary>` on `troy-mode/rule-<id>-change`. `rule-row` replaces the row, keeps its Since date, and adds the change-log row. Its config and baseline lines change in the same PR.
- **A P rule is retired** with no AR6 run: show Troy the row and the config and baseline lines the PR removes; Troy's yes approves it. On `troy-mode/rule-<id>-retire`, under `snapshot --role rules`, run `rule-row --id <ID> --rule-file <file> --retire`, with only `change` in the file, remove the rule's config and baseline lines, and commit as `[rules] Retire <ID>, <summary>`. The row stays, starting "Retired on <date>.", and its ID is never used again.
- **An R rule** is troy-mode's, and troy-init's upgrade replaces the R rows, so never edit one. Where troy-check's config allows an adjustment, such as R03's limits, R11's coverage limits, or R19's attribution mode, a P row records it, for example "In this project, R03's limit is 800 changed lines.", and the same rule PR changes `.troy-mode/config.toml`. Any other change to an R rule is a rule for every project.
- **`[flow] troy_approves_first`** stays its own `[rules] Set the features Troy approves` PR (section "Merging").

### A rule for every project (D83)

A rule for every troy-mode project lives in tstack and ships in a new plugin version. This flow changes nothing in tstack and nothing in the project:

1. Run AR6 with `--item <R ID>`: `next_r_id` from `rule-id` for a new rule, or the R rule it changes. It proposes the enforcement as for a project rule, names the tstack files that change, which it reads in the plugin folder, and says whether existing projects' code would break the rule when the upgrade brings it.
2. Send Troy the proposal as in step 3 above (W5), and ask whether to open an issue in tstack.
3. Only on Troy's yes: write the proposal in English to a file, check it with `troy_flow.py check-text --file <file>`, and run `gh issue create --repo <owner>/<name> --title "Rule proposal: <summary>" --body-file <file>`. `<owner>/<name>` comes from the plugin folder's `origin` remote: `git -C "${CLAUDE_PLUGIN_ROOT}" remote get-url origin`. Opening it reaches outside the project, so it always needs Troy's yes. When Troy says no, open nothing.
4. tstack builds the rule through its own design and build process, and the project gets it through the upgrade (section "Upgrade"). `status` says when the project's copy is older than the plugin's.

## Issues for Troy

Troy follows and steers the project from the phone through GitHub issues in the project's repository (F15 design). Documents stay in the repository: an issue is a view of the state, or an input from Troy. GitHub sends Troy no notification for troy-mode's writes, which are Troy's own, so still tell Troy in chat what waits.

| Issue | Label | Written by | Exists |
| --- | --- | --- | --- |
| A feature's progress issue | `progress` | You, from `issues` | From the moment the feature is next or has a stage PR, until its acceptance (D142) |
| An idea | `idea`, or no label | Troy, on the phone or the web; you, for an idea from chat that waits | Until the PR that acts on it, or your answer, closes it (D143) |
| A version's device-test checklist | `device-test` | You, from `issues`; Troy ticks it | From the release test that passed until the release PR merges (D144) |

### The sync (D141)

Run it at Start, after `status`, and right after every `troy_flow.py status --write-progress`:

1. `troy_flow.py issues --json`. For a patch release's checklist, add `--device-test-scenarios <ID>,<ID>...` with the scenarios its fixes touched, when the sync first creates it.
2. Run the `command` of each entry in `labels`.
3. For each entry in `actions`, in order: when it has a `body_file`, check it with `troy_flow.py check-text --file <body_file>` and read its exit code; then run its `command` in a later call. A body the engine rendered that fails `check-text` is troy-mode's own error: post nothing for it and tell Troy.
4. An `edit` with `new_run: true` starts a new run of a checklist (section "Failures and bugs").

**When something fails (D147).** A failed label or issue command: run `troy_flow.py status --note "Issue sync failed: <what>"`, say so in your next report to Troy, and go on; the next sync rebuilds the view and tries again. When the agent's permissions refuse a `gh issue` or `gh label` command, tell Troy once which rule to add, such as `Bash(gh issue *)` and `Bash(gh label create *)`, and go on as above; never work around a refusal. `issues.error` in `status`: no idea is acted on and no acceptance is taken from the checklist until the issues can be read; the rest goes on. `issues.skipped` or `skipped` "issues are turned off": do nothing with issues; chat works as before. `issues.template` false: the idea template `.github/ISSUE_TEMPLATE/idea.md` comes with "upgrade troy-mode"; until then an issue with no label is an idea.

Never delete an issue or a label, never change an existing label, and never tick a box of a checklist. An issue never holds a document's text beyond Troy's scenarios, the summary for Troy, code, logs, local paths, or secrets: it links to them.

### Progress issues (D142)

The sync keeps each one: it replaces Troy's edits to its text and reopens it when Troy closes it. The Why section of every stage PR starts with `Progress: #<n>`, and PR 6's with `Closes #<n>`, from `next.issue`, so GitHub lists each stage PR in the issue. Write no comment on a progress issue except a reply to Troy, a note for a later feature, and an overturn's two comments (section "Troy's comments on issues (D145)").

### Troy's comments on issues (D145)

`status` lists them in `issues.troy_comments`. A comment on a progress issue is a message in chat: a question gets a `Reply to Troy` comment; a remark about the open PR goes to that PR's author as Input, as Troy's PR comments do; a new request is handled as an idea. Comments on a checklist: section "Version release", step 5.

**Overturning a ruling (F18 D174).** Until a feature's acceptance, Troy overturns a ruling at round 3 on one of its PRs with a comment on its progress issue, or in chat, saying which side wins. Answer it on the progress issue with a comment headed `Overturn: <link to the ruling>`, with Troy's decision under it, so any session finds it: `status` then lists it in `overturns`, and holds the feature, and its team, after its current stage PR (`next.action` `overturn`, or `held` `overturn`). Carry it out through the flow the ruled stage already has, with Troy's decision as Input, and merge those PRs yourself:

| The ruled PR | How the overturn is carried out |
| --- | --- |
| PR 1, a design | A `[docs]` design update by IF2, reviewed by AR2 (section "Side PRs"); the stages that merged on the old design are redone as in rework when an interface changed |
| PR 2, a test plan | A `[docs]` test plan update by TM1, then a test fix when PR 4 has merged |
| PR 3 or PR 5, code | A bug: PR A's test and PR B's fix (section "Bug fix"), with Troy's decision as the report |
| PR 4, tests | A test fix by TE3, reviewed by TM2 and CR1 |

When they have merged, post `Overturn carried out: <the same link>` on the progress issue, with the PRs, and the feature goes on. After the feature's acceptance, Troy's disagreement is an idea like any other.

### Ideas (D143)

`issues.ideas` lists Troy's open ideas, each `new` until you answer it and again after Troy writes. When `status` gives `ideas`, at a natural stop (never between two stages, during an open PR, or during an open release), or when Troy names one ("idea #101", "change: #101"), do PM6 (`product-manager.md`) for each idea in `next.ideas`, or the one Troy named: read it with its comments, decide what it is, and post a comment whose first line is the heading below, in the language Troy wrote in:

| The idea is | Heading | Then |
| --- | --- | --- |
| A requirement change | `Idea: requirement change` | The change in a sentence or two. Then PM2 with the idea in Input, on `troy-mode/change-<slug>`; the change PR's description says `Closes #<n>` for each idea it takes in, and it waits for Troy's approval (section "Requirement change"). After its merge, comment `Idea: in the requirements` with the new or changed features and their progress issues once they exist. When Troy turns it down, comment `Idea: answered` with Troy's words and close the idea. |
| A bug | `Idea: bug` | `gh issue edit <n> --add-label bug --remove-label idea`: it becomes bug `B<n>` (section "Bug fix") and waits for the bug flow. |
| A rule | `Idea: rule` | The rule change flow (section "Rule change"); its PR says `Closes #<n>`. |
| A question, or something troy-mode will not change | `Idea: answered` | The answer, then `gh issue close <n>`. About troy-mode itself: what Troy can do, such as a rule for every project. |
| Meant for later, as Troy says in it | `Idea: later` | Nothing until Troy comments again or names it. |
| Unclear | `Waiting for Troy: <question>` | One question with a recommended answer. |

Add the `idea` label to an idea that has none when you answer it (`gh issue edit <n> --add-label idea`). Triage asks Troy nothing more than the flows already do. When the request reaches no further (D63), the ideas wait for the next run; the report says how many are open. When Troy closes an idea, do nothing more with it; if a change PR for it is open, close that PR without merging it (`gh pr close <number>`, which Troy can reopen), and say so in your report.

**Ideas from chat.** When Troy gives an idea in chat that you do not act on now, for example while a PR is open, or because Troy says "later", open an idea issue with Troy's words: write it to a file, check it with `check-text`, then `gh issue create --label idea --title "<summary>" --body-file <file>`. A request you act on at once gets no issue.

### Headings on issues (design 8.4)

`Idea: requirement change`, `Idea: bug`, `Idea: rule`, `Idea: answered`, `Idea: later`, `Idea: in the requirements`, `Waiting for Troy: <question>` (with its `Wait: W<n>` line), `Reply to Troy`, `Device test, run <n>: ready`, `Overturn: <link to the ruling>`, and `Overturn carried out: <link to the ruling>`. Answer a comment on an issue in the language Troy wrote it in, under the English heading. Write each comment to a file, check it with `check-text`, then post it in a later call with `gh issue comment <n> --body-file <file>`. Comments on PRs stay in English.

## Escalation

Escalate only for the waits W6 to W11 of `product-manager.md`, section "Waits for Troy": a change needs the requirements or the architecture to change (W6); an author's work still fails after 3 attempts and the premise attempt, or after a ruling it was given (W7); a new third-party dependency is needed, AR3's `escalate` (W8); an action is irreversible and outside your rights (W9); a permission or auto mode refuses a step you need, which you never work around (W10); or troy-mode's own checks find a fault you cannot repair: a run moved `HEAD` or the branch, broke its scope twice, or gave no report twice, AR7's plan failed twice, a rebase conflict across scopes, CI that failed twice outside the authors' files, or no check reported after two waits (W11). A review loop's round 3 is a ruling, not an escalation (section "Rounds and attempts"). Your rights: push your own branches with `--force-with-lease`; open, edit, comment on, close, and merge your own PRs within R18; open bug issues; create the labels `idea`, `progress`, and `device-test` when missing, and never change an existing label; create, edit, close, and reopen progress issues and device-test checklists from the issue sync; comment on, label, and close ideas as section "Issues for Troy" says, and open an idea issue for an idea from chat; delete your own branches after their PR merges; re-run a PR's failed CI jobs once with `gh run rerun <run ID> --failed`; close a change PR whose idea Troy closed; after Troy accepts a version, create its GitHub release on the release PR's merge commit (`gh release create`); and merge the PRs of a rule Troy approved. Opening an issue in tstack for a rule for every project needs Troy's yes each time. Never delete an issue or a label, and never tick a box of a checklist. Anything else escalates (W9).

Write the message in Troy's language, in the shape of `.troy-mode/templates/escalation.md` (Prototype C): where it stopped, why, the facts with links, the options, and a recommendation. Post it in English on the open PR as `Escalation: <trigger>`, with `Wait: W<n>` right under the heading; when no PR is open yet, post it on the bug's issue if there is one, else only in chat. Run `troy_flow.py status --waiting "<what>" --wait W<n>`, and stop. When Troy answers, in this session or a new one, put the decision into the next brief's Input and go on.

## Project setup

`status` gives the step to do next; a project that already has some steps resumes at the first missing one.

1. **Setup** (`next.action` `setup`). When Troy says yes, read `${CLAUDE_PLUGIN_ROOT}/skills/troy-init/SKILL.md` and follow it: troy-init's engine `setup --email <address>` with `--dry-run --json` first, Troy's two questions (whether to create the private GitHub repository, and whether to replace files troy-init did not write) in one message, and its PR flow. Its step 8 already detaches before the merge and ends with `git fetch origin`.
2. **Requirements** (`requirements`), after the setup PR merges, so troy-check checks them. Work as the Product Manager (PM1) under a snapshot with `--role product-manager`, on the branch `troy-mode/requirements`. In the features table, the Feature cell holds only the feature's short name, such as `Export history as CSV`: it becomes every PR title and the feature's folder name. Describe the feature in the requirements' other sections. Open `[docs] Add the requirements` with your summary for Troy at the top of its description (section "The summary for Troy"), and get Troy's approval as section "Merging" says (W1).
3. **Architecture** (`architecture`). Run AR1 (`brief --task AR1`) on `troy-mode/architecture`, then open `[docs] Add the architecture` with AR1's summary for Troy at the top of its description, approved the same way (W2). The message that asks Troy for this approval also asks the language step's question: which series the project belongs to, if any.
4. **Language step** (`language`). The language comes from the architecture's tech stack. Create the branch `troy-mode/lang-<name>` from `origin/main` first, then run troy-init's engine `lang <python|cpp>` with `--dry-run --json`, then without `--dry-run`, and take it through troy-init's PR flow. Add `--env-prefix "$TROY_MODE_ENV_PREFIX"` when that variable is set, and `--mamba <path>` when mamba is not on the PATH or in `$MAMBA_EXE`.
5. **Next.** Report, and go on to the first feature only if the request asked for it.

## Upgrade

Create the branch `troy-mode/upgrade-<version>` from `origin/main`, then run troy-init's engine `upgrade` with `--dry-run --json`, and take it through troy-init's PR flow. When it has nothing to change, run `git switch --detach origin/main`, delete the branch, and tell Troy. `status` says when the project's troy-check is older than the plugin's (`checks.outdated`): `[roles]`, `[flow]`, and `troy-check code --worktree` need the new copy.

## Work outside the pipeline

Answer questions and investigations here, following `how` or `why` (read their `SKILL.md`) when they fit, and start no role. An experiment runs on a throwaway branch `troy-mode/try-<slug>` made from `origin/main`, or in a scratch folder. Never push it or open a PR from it. Code worth keeping goes through a requirement change and the feature loop.

## Continue

Run `status` and report where the project stands. When something waits on Troy, say what. Otherwise go on with `next`, as far as the request reaches (section "Routing"): `continue-pr`, `ruling` and `ruled-revision` (section "Rounds and attempts"), `overturn` (section "Issues for Troy"), `stage`, `record-approval`, `bug` (PR B of a bug), `rework` (AR4 after a requirement change), the setup steps, the version release's `version-test-plan`, `release` (with its `next.step`), `record-acceptance`, `tag`, and `retro` (section "Version release"), `cleanup`, the next cleanup PR of a rule (section "Rule change"), and `ideas`, Troy's new ideas at a natural stop (section "Issues for Troy"). A rule's last cleanup PR finishes that rule change, which is a natural stop too: report, and go on only if the request reaches further. After the last feature of a version is accepted, `release` comes next: a feature-loop request goes on through its steps up to Troy's device test (W4). When `next.escalate` names a wait, escalate with it first.

## Reports

Report each stage to Troy in Troy's language, in the shape of Prototype B, for example:

```text
Next in order is F04 "Export history as CSV". It depends on F02 and F03, both accepted.
  [1/6] Interface design PR #41 is open. The Architect approved it in round 2.
        You approve this one (feature 2 of your first 3). Waiting for you.
```

Say plainly what you did not do or could not check.
