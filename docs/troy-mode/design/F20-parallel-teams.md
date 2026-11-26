# F20 design: parallel feature teams

| | |
| --- | --- |
| Feature | F20 in [requirements 1.54](../requirements.md#72-feature-list) |
| Version | 1.8 |
| Date | 2026-11-26 |
| Status | Approved by Troy on 2026-11-22 ("全按推荐"), with D268 to D279, every recommended answer, and with them the estimates of the build's role exam and trial (D271, D279). Version 1.1 records Troy's change of D278 on 2026-11-22 ("现在开始"): F20 lands in three PRs, so that part 1a, which changes no file of the instruction set, runs alongside tstack #63's build. Version 1.2 records three details that part 1a's build settled: `SubagentStart` still writes a role's record while the repository has no team worktree, `team-busy` also refuses `git checkout`, and a writer that waits a second for a lock goes ahead without it. Version 1.3 records what part 1b's build settled: a team's checks take the source folders from `[lang] source_roots`, its environment's fallback name is the main checkout's folder, and DV1's first-mock install in a team installs the main checkout. Version 1.4 records what part 2's build settled: only a shared interface needs an order in the plan, a feature already under way in the home checkout stays there, and `merge-check` checks source paths against the plan's modules. It also records the trial's results (section 8.3). Version 1.5 adds D290, from the trial's follow-up: on Windows the engine reads a `--repo` path in Git Bash's form, approved under Troy's standing yes of 2026-11-22 (section 4). Version 1.6 notes the changes of F18's design (D171 to D180, approved by Troy on 2026-11-25), which land with F18's build. Version 1.7 adds F18 part 1's `overturn` hold and the waits' IDs (section 3.8), and 1.8 part 2's spot checks with teams (section 3.8). |
| Source of truth | This English file. [`F20-parallel-teams.zh-CN.md`](F20-parallel-teams.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F20 lets troy-mode build features that do not depend on each other at the same time, each by its own team, as requirements 5.11 says. Troy approved the requirements on 2026-11-22 (requirements 1.54): one main session coordinates every team and runs every team's roles (Q17), there is no limit on how many teams run (Q18), a feature starts once every feature it depends on is accepted and the Architect's plan lets it (Q19, Q20), each team works in its own git worktree (Q21), whoever finishes first merges first and the others rebase (Q22, R24), a wait stops only its own team (Q23), and changes, rules, and releases stop only the teams they touch (Q24).

This design delivers:

1. **Teams.** An engine command creates a team's worktree and removes it after the feature's acceptance (section 3.1).
2. **A role in its team's worktree.** The brief names the team's checkout, and F05's hooks learn the team from the brief and run the role's commands there (section 3.2).
3. **Hooks and checks per team.** Each team's records and log lines live in its worktree's git folder, and `snapshot` and `check-run` look only at that team (section 3.3).
4. **The batch plan.** A new Architect task, AR7, plans each batch and checks each design against the plan (section 3.4).
5. **The main session's loop** over several teams, with merges in the order the PRs become ready, rebases, and conflicts (sections 3.5 to 3.7).
6. **Waits, changes, rules, releases, and usage limits** with teams (sections 3.8 to 3.10).
7. **The Python series' shared environment and Troy's PC** (section 3.11).
8. **State and progress**: `status`, the progress file, and the progress issues for several features at once (section 3.12).

F20 changes F04, F05, F07, F08, F14, F15, and F16 (section 5). When only one feature may start, troy-mode works as it does today: it runs that feature's roles in the session's own checkout, with no team.

## 2. What the probes showed

The design depends on facts about Claude Code that its documentation leaves open. They were probed on 2026-11-22 with the newest bundled CLI, 2.1.330, in nested `claude -p` sessions, reusing the #49 design's probe plugin (F05 design section 6.1). Each probe ran in a scratch git project with two linked worktrees, a plugin that logged every hook input, and a haiku worker agent. The four sessions cost $0.03 in all. Two more probes ran locally with no model: git's folders in a worktree, and tstack's own hook writes from several processes at once. The first column numbers the three questions: 1, a role in its team's folder; 2, several roles at once; 3, a worktree's git folder.

| # | Question | What happened |
| --- | --- | --- |
| 1 | Can the main session start a subagent in a given folder? | No. The Agent tool's parameters are `description`, `prompt`, `subagent_type`, `model`, `effort`, `run_in_background`, and `isolation` (`worktree` or `remote`), and no folder. The desktop app's Agent tool has the same, without `run_in_background`. |
| 1 | Does a subagent's `cd` carry to its next call? | No. `cd <worktree> && pwd` printed the worktree, and the next `pwd` printed the session's folder again, also when the worktree lay inside the session's folder. The main session's `cd` into the worktree beside the project did not carry over either; Claude Code keeps a main session's `cd` only inside its working folders. |
| 1 | Which `cwd` does a hook get for a subagent's call? | Always the session's folder, even for the call that ran `cd <worktree>`, and for a `Write` into the worktree. A hook cannot learn a role's team from `cwd`. |
| 1 | Can a hook read the role's brief? | Not at `SubagentStart`: its input has no prompt, and the subagent's transcript, `<folder of transcript_path>/<session_id>/subagents/agent-<agent_id>.jsonl`, does not exist yet. From the role's first tool call on, that file exists and its first line is the brief, so a team line in the brief is readable. `SubagentStop`'s input also names the file, as `agent_transcript_path`. |
| 1 | `isolation: "worktree"` | Claude Code made a new worktree for the run, `<session folder>/.claude/worktrees/agent-<id>`, on a new branch `worktree-agent-<id>` from the main session's `HEAD`, and kept it because the run changed a file. The hook's `cwd` was that worktree. It cannot be named or based on a team's branch, so one run's work does not reach the next run. |
| 1 | Can a hook root a role's calls in another folder? | Yes. A `PreToolUse` hook that answered with `hookSpecificOutput.updatedInput`, and no permission decision, changed the role's Bash command to `cd "<worktree>" && <command>`: its `pwd` printed the worktree. A path-less `Glob` given the worktree as `path` found the worktree's file. |
| 2 | Two roles at once | Two background workers of one main session got different `agent_id`s and the same `session_id`, and both hooks' `cwd` was the session's folder. Their hook calls interleaved. Each worker's transcript held its own team line, and each wrote only its own worktree. |
| 2 | Do the hooks' file writes race? | Partly, on Windows. tstack's `records.save` of different records, read by `read_all` meanwhile, never failed: 8 processes, 300 writes each. Appends to one `hooks.log` lost lines: 9 of 600 with 2 processes; with 8, 182 of 2,400 went missing and 7 of the rest could not be read. A read-change-save of one record lost updates even with 2 processes. The config cache, written in place, gave readers half a file, which the hook already catches. |
| 3 | `git rev-parse --git-dir` in a linked worktree | `<main checkout>/.git/worktrees/<name>`, absolute. `--git-common-dir` gives `<main checkout>/.git`. |
| 3 | Does removing a worktree lose its state? | Yes. `git worktree remove` of a clean worktree deleted `.git/worktrees/<name>` with the `troy-mode/` folder in it, records and `hooks.log` included. A worktree with changes is refused without `--force`. Deleting the folder and running `git worktree prune` also deletes the state. |

So a team's role cannot be started in its worktree, and the hooks cannot see from `cwd` which team a call belongs to. They can read the team from the brief from the first call on, and they can make every command run in the team's worktree. Section 3.2 builds on that (D268). The probe scripts stayed on Troy's PC, outside the repository.

## 3. How it works

### 3.1 A team and its worktree (D269)

A **team** is the role runs of one feature, from PR 1 to PR 6, in one git worktree. It runs the feature loop of F07 section 8 unchanged: one writing role at a time within the team, with its own reviews, rounds, attempts, checks, and merges. Roles of different teams run at the same time.

- **The home checkout** is the folder where the main session runs, where Troy typed `/tstack:troy-mode`. It holds no team's work. The main session's own flows run there, one PR at a time as today (F07 section 4): the requirements, the architecture, a requirement change, a rule change, the version test plan, and the release.
- **`team start --item <ID>`** creates the worktree `<home checkout>/.troy-teams/<id>`, where `<id>` is the feature ID in lower case, such as `f08`, detached at `origin/main`. The first time, it adds `/.troy-teams/` to the repository's `.git/info/exclude`, which every worktree shares, so no checkout lists the folder and no project file changes. It refuses a feature that may not start (section 3.5).
- The worktree lies inside the session's folder, so Claude Code treats its files as the project's: roles need no extra working folder or permission to write there. Tools that the main session runs in the home checkout skip it: `.troy-teams` starts with a dot, which pytest skips by default, and ruff and git respect the exclude file.
- In the worktree, each stage's branch is made as today: `git -C <worktree> switch -c troy-mode/f08-3-mock origin/main`.
- **`team end --item <ID>`**, after PR 6 merges, refuses while the worktree has changes or a record of the team is open. It appends the team's `hooks.log` lines to the log in the repository's common git folder (section 3.3), then runs `git worktree remove`. So the retrospective keeps every team's lines although the worktree's git folder goes (Q21).
- **A session in another folder.** `git worktree list` shows every team's worktree from any checkout, so a new session finds the teams wherever they are. When a team's worktree lies outside the new session's folder, `status` says so, and the skill moves it with `git worktree move` into the new home checkout's `.troy-teams/` while its tree is clean and none of its roles runs.

### 3.2 A role in its team's worktree (D268)

The Agent tool cannot start a role in a folder, and the role's `cd` does not last (section 2). So:

1. **The brief names the checkout.** `brief --repo <worktree>`, run for a team's worktree, adds one sentence to the Task line, after the task's own sentence: "You work for team F08 in the checkout `<absolute path>`: every path in this brief is inside it, read and write files only there, and your commands start there." The Read first paths become absolute paths in that checkout. A brief for the home checkout has neither, so it stays as today.
2. **The hook learns the team at the role's first call.** At a role's first hooked call, `PreToolUse` reads the first line of the role's transcript and looks for that sentence. The checkout must be a linked worktree of this repository under `.troy-teams/`, which the hook checks against the `gitdir` files in the common git folder's `worktrees/`. The role's record then holds `team` and `worktree` (section 3.3). While the repository has a team worktree, `SubagentStart` writes no role's record: the transcript does not exist then, and the role has done nothing before its first call, so the first call's state is its starting state. Without a team worktree it writes the record as today, so troy-mode with one team at a time works as before. F05 already makes a missing record at the first call (F05 design section 6).
3. **The hook roots every command in the worktree.** For a team's role, `PreToolUse` answers each `Bash` call with `updatedInput` whose command is `cd "<worktree>" && <command>`, each `PowerShell` call with `Set-Location -LiteralPath '<worktree>'; <command>`, and each `Glob` and `Grep` without a `path` with the worktree as `path`. It gives no permission decision, so Claude Code's own permissions still apply to the new input. A command that already starts with `cd` into the worktree is left alone.
4. **File tools.** `Write`, `Edit`, and `NotebookEdit` are checked against the team's worktree as the repository (F05 section 5.2). A path elsewhere in the project, the home checkout included, is refused: "You work in the checkout <worktree>. Write the file there." The temp folder and the scratchpad stay allowed. Reads are not limited.
5. **No team, while teams run.** A role whose brief has no team sentence works in the home checkout, as roles do today. The main session's own flows use that: AR4, AR6, TM1 for a version, and AR3's write after Troy accepts a dependency (section 3.3). When the hook cannot read the transcript at all, and the repository has a team worktree, it refuses the role's calls that can change anything, with rule `team`: "The hook could not read your brief. Report `failed` and say so." Without team worktrees it falls back to today's behavior.

### 3.3 Hooks and checks per team (D270, D276, D277)

**Records.** A team role's record lives in its worktree's git folder, `<common git folder>/worktrees/<name>/troy-mode/agents/<agent_id>.json`, as Q21 says, and holds two more fields, `team` and `worktree`. A home-checkout role's record lives in the home checkout's git folder, as today. Since a hook's `cwd` is always the session's folder, every hook finds a role's record by its agent ID across the git folders of the repository's worktrees: one listing of `<common git folder>/worktrees/`, with no git process.

- **Change detection** (F05 section 6) runs `git status` in the record's worktree. A team role is never blamed for another team's files, nor for the home checkout's.
- **The main session's `TaskStop`** closes the record of that agent ID wherever it is, and **`SessionEnd`** closes the ending session's records in every worktree's git folder (F05 section 6.1).
- **`SessionStart`** cleans old records and log lines in every worktree's git folder, and in the common git folder's log.
- **A woken role that has already stopped** (F05 D232): `SubagentStart` writes nothing, and the first call finds the stopped record and refuses as today.

**The log.** A team role's refusals go to its worktree's `hooks.log`, and the main session's and home-checkout roles' to the home checkout's, as today. Every append, and `SessionStart`'s rewrite, holds a lock file beside the log, `hooks.log.lock`, made with `O_CREAT | O_EXCL`, tried every 10 ms for up to a second, and taken over when it is more than 10 seconds old. After that second the write goes ahead without the lock, so a lock that nobody releases delays a hook call by about a second and never stops it. A record's read-change-save holds a lock of its own the same way. On Windows a record that another hook process has open cannot be replaced, so a read or a save that finds the file in use tries again for up to two seconds. Probe 2 lost log lines and record updates without it. `team end` appends a team's lines to `<common git folder>/troy-mode/hooks.log` under that lock (section 3.1), and `retro` reads that log and every live worktree's (section 5).

**Snapshots and checks per team.** The engine's commands take the existing `--repo <path>`. `snapshot --repo <worktree>` and `check-run --repo <worktree>` keep their run records in that worktree's git folder and read only that team's role records. So team A's `snapshot` never refuses because a role of team B still runs, and team A's `check-run` never lists team B's changes (Q21). The home checkout's `snapshot` reads only home-checkout records.

**The main session in a team's worktree (D276).** F07 section 6.2 told the main session to do nothing in the checkout while a role runs, because the hooks blame every change on the role. With teams, the main session works in other worktrees meanwhile, so that rule becomes a check. The main session's `PreToolUse` refuses, with rule `team-busy`, a git command that writes (`add`, `commit`, `switch`, `checkout`, `restore`, `reset`, `rebase`, `merge`, `stash`, `clean`, `rm`, `mv`, `cherry-pick`, `am`, `apply`) and a `Write`, `Edit`, or `NotebookEdit`, in a team's worktree while a record of that team is open. It finds the folder the way F05 section 7.1 already does, from `-C`, `--git-dir`, `--work-tree`, and an earlier `cd`, and for file tools from the path. The reason names the team's running agent IDs.

**Shared documents (D277).** Q20 lets only the main session and the Architect's planning step change the requirements' text, the architecture, its ADRs, and the rules table. In a team's worktree the hook therefore takes `docs/requirements*.md`, `docs/architecture*.md`, `docs/adr/**`, and `docs/versions/**` out of every role's write scope, besides `docs/rules*.md` and `.troy-mode/**`, which no role may change today. A team's PR 6 changes its own row of the status table, which the main session writes as the Product Manager, as today. The Architect's writes that touch the architecture, AR3's after Troy accepts a dependency, AR4's, and AR6's, run in the home checkout as the main session's own `[docs]` PR, one at a time, and every team picks them up at its next stage or rebase. An ADR then takes its number when it merges.

### 3.4 The batch plan (D271)

Before a batch of teams starts, the Architect plans it (Q20). A **batch** is every feature that may start at that moment, by its dependencies (section 3.5). The plan is the Architect's new task AR7, with two kinds of run:

- **Plan.** The brief's Input names the batch's features and the teams already running. For each feature, AR7 reads its requirement row, the architecture's module table, and the designs of the features it depends on, and gives: the modules it will touch, by their names in the architecture's module table; the external interfaces it adds or changes; and the shared documents it needs changed. Where two features overlap, it orders them: `F10 after F08 1/6`, so F10 starts once F08's design merges, or `F10 after F08 6/6`, once F08 is accepted. Two features that change the same interface never run at once: one waits at least for the other's design. Features that only share a module may run at once, and the plan names the module, so a rebase there is expected.
- **Check.** After AR2 approves a team's design (PR 1), and before it merges, AR7 compares the design with the plan and with the running teams' merged designs. When the design changes an interface or a shared document that another running feature's plan names, or touches a module outside its own plan, AR7 gives the new order, and the team that must wait stops after its current stage.

AR7 changes no file. Its report's Summary holds the plan as a fenced block in a fixed form, one line per feature and one per order, such as `F08 modules: importer, cli; interfaces: import_csv; documents: none` and `F10 after F08 1/6`. `plan --report <file>` parses it, checks that every feature of the batch has a line and every interface that two features of the batch change has an order between them (a shared module needs none), and keeps it in `<common git folder>/troy-mode/plan.json`. A plan that does not parse goes back to AR7 once, then escalates. The plan is local, like the progress file: in a new clone `status` asks for AR7 again, which costs one Architect run.

### 3.5 Which features start (Q19)

A feature may start when:

1. every feature it depends on, hard or soft, is accepted on `origin/main` (Q19);
2. the plan lets it: every order that names it is met (section 3.4);
3. no requirement change that affects it is open (section 3.9);
4. its version may start: a feature of the next version may run stages 1 and 2 only, until the current version's tag exists (section 3.9).

`status` gives these as `may_start`, in the order of the requirements. With one such feature and no other team running, troy-mode works as today, in the home checkout and with no plan. A feature that has already merged a stage in the home checkout, such as one started before teams, stays there: it is neither planned for a team nor started as one, and the home checkout goes on with it. With two or more, or one beside a running team, the main session runs AR7 for those features, then starts a team for each that the plan lets start, with no limit (Q18). In `ZJUCao/recipe-menu`'s v0.1, this gives 6 batches of at most 4 features (requirements 5.11).

### 3.6 The main session's loop

One main session runs every team (Q17). It keeps the loop short:

1. **Start what can start.** For each team without a running role, it takes the team's next action from `status` and starts it: a role run (F07 section 6), with `brief`, `snapshot`, and `check-run` run with `--repo <worktree>`, or a step of its own, such as a commit, a push, or a merge. Where the Agent tool has `run_in_background`, as in `claude -p`, it passes `true` when two or more teams run, so that the roles run at once. In the desktop app every role already runs in the background.
2. **Wait for the next report.** When a role reports, the main session handles that team's report as F07 section 6.3 says, then goes back to step 1.
3. **Name the folder each time.** The main session runs git and the engine with `git -C <worktree>` and `--repo <worktree>`, never with a bare `cd`, because its `cd` lasts inside its working folders and the next command may belong to another team.

**The main session's context.** The pilot's single main session cost $301 and went through 15 compactions (Q17). With teams, every report reaches the same session. So the engine's team output is one line per team, the skill reads role reports and never whole diffs, the progress file holds what a compaction would lose, and after a compaction the skill runs `status` before anything else. F20's trial measures the main session's share (section 8.3).

### 3.7 Merges, rebases, and conflicts (R24, Q22, D272 to D274)

**First ready, first merged.** A team's PR is ready when every review approved and its local checks passed (F07 section 8.6). Ready PRs merge in the order they became ready (Q22).

**The merge check (D272).** Before it merges, the main session runs `git -C <worktree> fetch origin --prune`, then `merge-check --repo <worktree> --pr <n>`. It reports:

- `rebase` when `origin/main` is not an ancestor of the PR's head (R24);
- `outside-plan` with the paths, when a changed source path lies outside the modules the plan gives the feature (test files belong to no module), by the module table's path patterns, which troy-check already reads for R07 (F03 D19). AR7 then checks the PR's diff before the merge;
- `held` when the feature belongs to the next version, the PR is PR 3 to PR 6, and the current version has no tag yet (Q24, F08 D75);
- `ready` otherwise. The main session then runs `wait-checks` on the head and merges with `gh pr merge --rebase --match-head-commit <sha>` (F07 D204).

**Rebasing (D274).** On `rebase`, the main session runs `git -C <worktree> rebase origin/main`. A PR rebases only when it is about to merge, not after every merge of another team, so each merge of another team costs this PR one CI run at most. After a clean rebase it pushes with `--force-with-lease`, runs the local checks again, and waits for CI on the new head (R24). `merge-check --rebased-from <old head>` then says whether the rebase changed the PR's diff: whether the lines the PR adds and deletes, per file, differ from before, leaving out context lines and line numbers. When they differ and the stage has a Code Reviewer, which is PR 3, PR 4, and PR 5, the Code Reviewer reviews the rebased diff (CR1, the next round). PR 1, PR 2, and PR 6 have no Code Reviewer, so their checks alone run again.

**A conflict (D273).** When the rebase stops on a conflict, the main session lists the conflicting paths, then runs `git rebase --abort`. `merge-check --conflicts <path>...` names the role whose write scope holds every one of them in that stage: the Developer for source, the Test Engineer for tests, the Interface Designer for the design, the Test Manager for the test plan, and the Product Manager for PR 6's status row. Paths that no one role's scope holds escalate (5.7). The stage is then **redone on the new main**: the main session makes the stage's branch again from `origin/main`, and the owning role runs again with Input that holds its old diff and the conflicting paths, and asks for the same change on the new main. The commit, the push with `--force-with-lease` to the same PR, the checks, and the review follow as for any revision. The PR keeps one commit (R01). When the owner is the Product Manager, the main session writes its status row again itself, with a snapshot as F07 section 7 says. A redo counts neither as an attempt nor as a round, because the conflict comes from another team's merge, not from the author's work.

The most common conflict is expected in PR 6: two features accepted one after the other change neighbouring rows of the requirements' status table, and git counts changes to neighbouring lines as one conflict. That redo is the main session's own and costs no role run.

### 3.8 Waits and approvals (Q23)

- A team that waits for Troy, or that escalated, stops. The teams that wait for its feature, by dependency or by the plan, wait too. Every other team goes on.
- `status` gives `waiting`: each PR that waits for Troy, with its team, its summary's link, and the features it holds up, the one that holds up the most first.
- The main session asks Troy in one message about every waiting PR, each with its summary for Troy (F14), as Prototype E shows. Troy answers them together, "全部批准" or "approve all", or one at a time, in chat or on the PRs (F15 design D145). "全按推荐" still takes every recommendation of the PRs it answers.
- An escalation comes in a message of its own (5.7), because each needs its own decision.
- **F18.** Each entry of `waiting` gives its wait's ID, `wait` (F18 design 4.2). An overturn of a ruling holds its feature's team after its current stage PR, with `held` reason `overturn`, until troy-mode posts `Overturn carried out:` on the progress issue; a team affected by a requirement change shows `change` first, and `plan` comes after both (F18 design 5.3 and 7.5). With spot checks on, a risky PR 1 or PR 2 waits like an approval, so it stops only its team and the teams that wait for its feature, and its entry of `waiting` gives its marks in `risky`; a sampled PR stops no team, and the report lists it under "Spot checks, after the merge" (F18 design 7.5).
- Troy may also merge a waiting PR 1 or PR 2 on GitHub. R24 cannot stop that merge from an older base, but such a PR holds only its feature's own documents, and the team's next stage starts from the new `origin/main`.
- `[flow] troy_approves_first` still counts the first features in the order, whichever team builds them (Q23).

### 3.9 Changes, rules, and releases (Q24)

- **A requirement change.** The main session takes in an idea or a change before it starts the next team (F15 D143), and writes it as today (PM2) in the home checkout. The change PR's description gains a line `Affects: F08, F10`, from PM2's list. While that PR is open, `status` holds each affected team after its current stage PR merges, and the other teams go on. After the change merges, the affected teams continue from AR4's result as F07 section 11.2 says.
- **A rule change.** It runs in the home checkout as F09 says, and its PR merges like any other. Every team picks it up when it starts its next stage from `origin/main`, and an open PR picks it up at its rebase (section 3.7), so its checks run with the new rule.
- **A release.** It starts when every feature of the version is accepted, as F08 section 5.2 says. A team of the next version may merge its PR 1 and PR 2 before then. Its PR 3 to PR 6 wait for the version's tag (`held`, section 3.7), so a patch release stays possible (F08 D75).
- **Performance cases.** Before PR 5's performance cases run on Troy's PC (F07 section 8.1), the main session waits until no role of another team runs, and starts none meanwhile, so that their tests do not slow the measurement. The release test runs them again for every feature.

### 3.10 Usage limits and continuing (Q18)

When Troy's 5-hour usage limit stops the session, every team pauses. Its state is in git, on GitHub, and in its worktree, so nothing is lost:

- A new session, or "continue" after the reset, runs `status`, which rebuilds every team from `git worktree list`, the open PRs, the flow records in each worktree's git folder, and the plan.
- A role that the limit cut off leaves an open record. `snapshot` and `check-run` name it as `running`, and the main session ends it with `TaskStop`, which clears a stale record (F05 D231).
- A worktree whose role stopped without a report keeps the run's changes. `check-run` of that run then lists them, and since the role gave no report, F07 section 6.3 applies: the main session undoes the run's own changes and runs the role once more.

### 3.11 Python series and Troy's PC (D275)

A Python series shares one environment (requirements section 8), and DV1's `uv pip install -e . --no-deps` points it at one folder. Two teams' checks would then test the same code (Q20). So each team's checks put the team's own source first on Python's import path: the checks that `brief --repo <worktree>` and the skill's local checks give run with `PYTHONPATH` set to the worktree's source folders, as the config's `[lang] source_roots` names them, `src` by default. A folder on `PYTHONPATH` comes before the editable install's entries, so the team's worktree is what its tests import. The environment and its lock stay one per series. So a team's brief also names the environment by the main checkout's folder when `[lang] environment` is unset, never by the worktree's, and DV1's first-mock install installs the main checkout, `uv pip install -e "<main checkout>" --no-deps`, so the shared environment never points into a worktree that `team end` removes. The build's tests and trial check that `import <package>` gives a file in the team's worktree for the Python pack's build backend.

C and C++ teams each build in their own worktree's build folder, so they share nothing.

### 3.12 State and progress

- **`status`** gains `teams`: for each team, its feature, worktree, stage, open PR, next action, whether a role runs (an open record), and whether it waits for Troy, for another feature, for a change, or for the version's tag. `may_start` and `waiting` are described above. `next` becomes a list with one action per team, plus the home checkout's own action, if any.
- **The progress file** lists every team, its stage, and what each waits for, in the shape of Prototype E. `status --write-progress` writes it in code. F01's `progress` template does not change: every file under `troy-mode/templates/` belongs to F16's instruction set, and a change there would make all twelve exam cases affected (section 6).
- **Progress issues** (F15). Every feature that a team builds has its progress issue, as each feature does today. F15's rule "the next feature" becomes "a feature that may start" (F15 design 4.1), so each batch's issues appear together.
- **Costs** (F07 section 8.8). `costs --item <ID>` shares each main-session message among the features whose teams ran at that moment, in equal parts, so that the features' costs add up to the version's. A feature runs from its first role run to its `accept` commit. `--tag` does not change.

## 4. The engine

New and changed commands of `troy_flow.py` (F07 section 3.1):

| Command | What it does |
| --- | --- |
| `team start --item <ID>` | Creates the team's worktree (section 3.1) when `may_start` holds the feature, and prints its path. |
| `team end --item <ID>` | After PR 6 merges: appends the team's log lines to the common log, then removes the worktree (section 3.1). |
| `plan --report <file>` | Parses AR7's plan, checks it, and keeps it (section 3.4). |
| `merge-check --pr <n> [--rebased-from <sha>] [--conflicts <path>...]` | R24, the plan's modules, the next version's hold, whether a rebase changed the diff, and a conflict's owner (section 3.7). |
| `status` | Adds `teams`, `may_start`, `waiting`, and one next action per team (section 3.12). |
| `brief` | With `--repo <worktree>` of a team: the team sentence, absolute Read first paths, and `PYTHONPATH` in the checks (sections 3.2 and 3.11). |
| `snapshot`, `check-run` | With `--repo <worktree>`: that team's run records and role records only (section 3.3). |
| `retro` | Reads the common git folder's log and every live worktree's log (F08 section 7). |
| `costs` | Shares the main session's messages among the features running at the time (section 3.12). |

The engine still writes only the progress file, the header fields of `approve`, and its records under `<git folder>/troy-mode/`, now also `plan.json` and `.git/info/exclude`'s one line. It never commits, pushes, or writes to GitHub. `team start` and `team end` run `git worktree add` and `git worktree remove`, the first git writes of the engine; the alternative, the skill running them, would leave the exclude line and the log archive to the skill's words.

**A `--repo` path in Git Bash's form (D290).** Git Bash's `$PWD` gives a folder as `/tmp/...` or `/c/...`. Git Bash rewrites such an argument into the Windows form before Python sees it, but not when `MSYS_NO_PATHCONV=1` is set, as the trial's nested sessions had it (section 8.3). Python on Windows then reads `/tmp/x` as `\tmp\x` on the current drive, so every command refused the team's worktree. So on Windows, when the `--repo` folder does not exist as given and its path starts with one `/`, the engine tries the folder that Git Bash means: the output of `cygpath -w <path>` when `cygpath` is on the `PATH`, as it is in Git Bash, and gives an answer, and otherwise `/c/rest` as `C:\rest`, for any drive letter. A folder that exists as given is used as given, and when the converted folder does not exist either, the command still refuses, naming the path as given. Other systems read the path as given.

## 5. Changes to earlier features

Each of these designs gets a change-log row with F20's design. The detailed changes to their sections land with F20's build.

- **F04 (roles).** The Architect gains AR7, Batch plan, with its two kinds of run (section 3.4), in its agent file and in F04 section 6.2. Within a team, the write scopes lose the shared documents of section 3.3 (D277). The brief's fields do not change: the team sentence is part of the Task line (F04 section 5.1).
- **F05 (hooks).** The team from the brief, the rooting of commands, the file-tool check against the team's worktree, records in each worktree's git folder found by agent ID, `TaskStop`, `SessionEnd`, and `SessionStart` over every worktree, the log and record locks, rule `team`, rule `team-busy`, and the shared documents out of a team's scopes (sections 3.2 and 3.3). `SubagentStart` writes no role's record while the repository has a team worktree. F05 section 6's assumption, that nothing else changes the checkout while a role runs, now holds per worktree.
- **F07 (entry skill and engine).** The commands of section 4, `status` and the progress file for several teams, and the skill's loop of section 3.6. Section 6.2's "one writing role at a time" becomes one per team, and its "do nothing in the checkout meanwhile" becomes rule `team-busy`. The merge step gains `merge-check` and the rebase (section 3.7). Section 15's "two features at once" is no longer out of scope.
- **F08 (release).** The release waits for every feature of the version, the next version's code PRs wait for the tag (section 3.9), and `retro` reads every team's log lines (section 3.3).
- **F14 (summary for Troy).** The summaries do not change. The skill's step "When the PR waits for Troy" asks about every waiting PR in one message (section 3.8).
- **F15 (issues).** A progress issue for every feature that may start (section 3.12).
- **F16 (role exam).** The build's exam (section 6).

F01's templates, F02 and F03's checks, F06's troy-init, and the projects' files do not change. The hooks, the engine, and the skill reach a project with the next plugin version.

## 6. The role exam (F16)

F20's build changes these files of F16's instruction set (F16 design 9.1):

| File | Change | Cases it affects |
| --- | --- | --- |
| `agents/troy-architect.md` | AR7 (D271 A) | ar-design-review and ar-error-review: the agent file is part of every Architect case's input |
| `troy-mode/flow/troyflow/brief.py` and the modules it imports | The team sentence, absolute paths, and `PYTHONPATH`, only with a team's `--repo` | None: the cases' projects are not team worktrees, so their briefs render as before |
| The entry skill's sections "Running a role" and "The summary for Troy" | `--repo`, the loop, `team-busy`, and the one message for waiting PRs | None: no case's `input.md` changes (F16 design 9.2) |

No template, `common.md`, or other agent file changes.

**The estimate**, from `troy_exam.py`'s budget code: neither Architect case has a recorded run, and `main`'s instruction hash has no base run, so both versions run fresh at the pilot's Architect median of $2.94 a run, five runs each, plus one judge pass per case at $2.00. The first round is $62.80, and the whole, with each case's second round, $125.60. That is above F16's $60 line (F16 D158). Troy said yes to that estimate on 2026-11-22 with D271; an exam whose spending reaches 1.5 times its estimate still waits for Troy (F16 section 10.2). Under D271 B, no agent file changes, `affected` finds no case, and the exam costs $0. Neither Architect case is a target: both must not get worse.

## 7. How F20 maps to the requirements

| Requirement | Where F20 covers it |
| --- | --- |
| 5.11, Which features run at once; Q19 | Section 3.5 |
| 5.11, A team; F20 row, the engine command that creates the worktree | Section 3.1 |
| 5.11, The main session; Q17, Q18 | Sections 3.5 and 3.6 |
| 5.11, Conflicts between teams; Q20 | Sections 3.3 (shared documents), 3.4, and 3.7 (the merge check) |
| 5.11, Hooks and checks; Q21 | Sections 3.2 and 3.3 |
| 5.11, Merges; R24, Q22 | Section 3.7 |
| 5.11, Usage limits; section 8, Usage limits | Section 3.10 |
| 5.11, Waits; 3.3, 5.7, Q23 | Section 3.8 |
| 5.4, 5.5, 5.8; Q24 | Section 3.9 |
| 5.10, 5.11, Progress; Prototype E | Sections 3.10 and 3.12 |
| 5.11, One team | Sections 1 and 3.5 |
| Section 8, Cost: at most 10% more per feature | Sections 3.6 and 3.12, measured in the trial (section 8.3) |
| Section 8, Troy's PC: performance cases | Section 3.9 |
| Section 8, Code under test; Q20's environment | Section 3.11 |
| Section 9, teams on one PC only | Section 9 |
| Q25, the build order | Section 8.4 |

## 8. How F20 is checked (D279)

### 8.1 Tests

Tests use `unittest` and the standard library, as F05's and F07's do. A separate agent writes them from this design before the code exists. The engine's tests build a temporary repository with a local bare `origin` and real linked worktrees; the hooks' tests feed `troy_hook.py` inputs with a fake transcript file.

| Group | Cases include |
| --- | --- |
| Teams | `team start` makes `.troy-teams/<id>` detached at `origin/main`, writes the exclude line once, and refuses a feature whose dependency is not accepted, whose plan order is not met, or that an open change affects. `team end` refuses with changes or an open record, appends the team's log lines, and removes the worktree. |
| Brief | With a team's `--repo`: the team sentence exactly once in the Task line, absolute Read first paths in the worktree, and `PYTHONPATH` in the checks. With the home checkout: the same brief as before, byte for byte. |
| The team from the brief | The first call reads the transcript's first line and writes the record into the worktree's git folder with `team` and `worktree`. A sentence that names a folder that is not a team worktree of this repository gives no team. An unreadable transcript with a team worktree present refuses with rule `team`; without one it falls back. `SubagentStart` writes no record while a team worktree exists, and writes it as today without one. |
| Rooting | `updatedInput` for Bash with `cd "<worktree>" &&`, for PowerShell with `Set-Location`, and the worktree as `path` for a path-less Glob or Grep; nothing for a home-checkout role or the main session; no permission decision. |
| Paths and changes | A team role's `Write` in its worktree checked by scope; in the home checkout or another team's worktree refused. Change detection in the worktree only: team B's change never reaches team A's role. Shared documents refused in a team, allowed in the home checkout. |
| Records and logs | `TaskStop` closes a record in a team's git folder; `SessionEnd` closes the session's records in every worktree; `SessionStart` cleans every worktree. Concurrent appends from several processes keep every line; a stale lock is taken over; concurrent record updates keep every task. |
| `team-busy` | The main session's `git -C <worktree> commit` and `Write` into a worktree with an open record refused; with the record closed, or in another team's worktree, passed; reads passed. |
| Snapshot and check | Team A's `snapshot` passes while team B's record is open, and refuses while team A's is. `check-run` lists only its worktree's changes. |
| Git Bash paths | On Windows, `brief --repo` and `snapshot --repo` with a worktree given as `/c/...` and as `/tmp/...` read that worktree, through `cygpath` when it is on the `PATH` and through the drive mapping without it; a folder that exists as given is read as given; a missing folder is still refused, naming the path as given. Elsewhere the path is read as given. |
| Plan | A plan block parsed; a missing feature, an unordered overlap of modules or interfaces between running features, and a bad line refused. `may_start` follows the orders `after F08 1/6` and `after F08 6/6`. |
| Merge check | `rebase` when `origin/main` is not an ancestor; `outside-plan` with the paths; `held` for the next version's PR 3 before the tag, and PR 1 passing; a clean rebase with the same added and deleted lines gives no review, one with changed lines gives CR1 for PR 3 to 5 and none for PR 1, 2, and 6; conflict owners for source, tests, design, test plan, the status row, and a mix that escalates. |
| Status and progress | `teams`, `may_start`, `waiting` ordered by the features held, a team held by an open change's `Affects:` line, a team rebuilt from the worktree list after a restart, and the progress file with every team. |
| Costs | A main-session message shared among the features running at that moment; the features' sum equals the version's. |
| Python | With `PYTHONPATH` set by the brief, `import <package>` in the sample environment gives the worktree's file. |

### 8.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: the team read from `cwd` instead of the brief, a team sentence that names any folder accepted, `SubagentStart` still writing a record into the home checkout, the rooting skipped for PowerShell, a `Glob` with a path rewritten, a team role's `Write` into the home checkout allowed, change detection run in the home checkout, a record looked up only in the home checkout's git folder, `SessionEnd` closing only the home checkout's records, the log append without the lock, a stale lock never taken over, `team-busy` checking only the main session's `cd` and not `-C`, `snapshot` of team A refusing for team B's record, `team end` removing the worktree before it archives the log, `merge-check` comparing context lines, a conflict in tests given to the Developer, the next version's PR 3 merged before the tag, `may_start` ignoring an `after F08 1/6` order, the plan accepted with an unordered overlap, the main session's cost counted in full for each feature, and `PYTHONPATH` left out of a team's checks. D290 adds: a converted path used when the path as given exists, the conversion run on another system, `cygpath` ignored when it is on the `PATH`, a drive letter left out of the mapping, and a missing folder accepted after the conversion. The counts go in the PR description.

### 8.3 Trial on a sample project

Before part 2's PR opens, F20 runs in nested `claude -p` sessions of the bundled CLI on `ZJUCao/troy-mode-trial`, with tstack loaded from the PR branch through `--plugin-dir`, as F07's trials did (F07 design 14.3). Troy's `autoMode.allow` rule covers launches that act only on that repository.

1. **A batch.** A requirement change adds two small features that depend only on accepted ones and that both add a command-line option, so they share the `cli` module. The Architect plans the batch, and two teams start, each in its worktree.
2. **At the same time.** The two teams' writing roles run at once. The hooks' logs and `check-run` show that neither team is blamed for the other's files, and that neither team's `snapshot` waits for the other's roles (Q21).
3. **Merges.** The team that finishes a PR first merges first. The other rebases, pushes, and waits for CI again (R24). PR 6's neighbouring status rows conflict, and the main session redoes its row. A change to the shared `cli` module that changes the second PR's diff brings CR1 back.
4. **A pause.** The session is stopped while a role runs, as a usage limit would. A new session with "continue" rebuilds both teams, ends the stale role, and finishes both features.
5. **Facts.** Whether `run_in_background` roles of two teams overlap in `-p`, and the main session's share of the cost per feature against F07's part 1 trial, which built one feature alone.

It takes about 30 role runs: about 13 per feature, three AR7 runs, and a CR1 run after a rebase. At the pilot's median cost per run, about $55 for the roles, plus the main session, so about $85 in all, and a few Actions minutes per PR. Two facts only the desktop app shows: whether auto mode lets the rewritten commands through, and how the app's notices of several background roles reach the main session. The first real run with teams checks them.

**What the trial showed (2026-11-23).** Three nested sessions with a frozen copy of part 2's build on `ZJUCao/troy-mode-trial`, made public by Troy on 2026-11-23 after its private Actions minutes stopped starting jobs. A requirement change added F06, a character count option, beside F05, a line count option, in v0.3. AR7 planned the batch and ordered F05 after F06's design, since both change the `wordcount` command line, and its check ran after each design's review. Both teams then ran at once: 35 of the 37 role runs started in the background. Every PR merged after `merge-check` gave `ready`: the other team's merge made it `rebase` first, two rebases stopped on `cli.py`, whose owner was the Developer, and the stage was redone on the new main, and a rebase that changed the mock's lines brought the Code Reviewer back, while rebases that left a diff's lines alone did not. The real 5-hour usage limit stopped the second session while both teams' roles ran; its exit closed their records, and a new session with "continue" undid the cut-off runs' changes and finished both teams. The archived `hooks.log` holds no line that blames one team for the other's files, and no `team-busy` refusal. Both features were accepted as "Ran for real on Troy's PC", and `team end` removed both worktrees. The trial cost $38.22 at list prices (estimate about $85); `costs` gave F06 $14.45 and F05 $12.58, each with the same $4.89 share of the main session, since their windows overlapped. One follow-up: a `--repo` path in Git Bash's `/tmp/...` form is refused by the engine on Windows, and the session used the Windows form instead. D290 makes the engine accept it (section 4).

### 8.4 Status and order

F20 lands in three PRs (D278), each with one commit and its tests written first:

1. **Part 1a, the base, now.** The hooks of sections 3.2 and 3.3: the team from the brief, the rooting through `updatedInput`, the team's record, the refusal of writes outside the team's worktree, the shared documents out of a team's scopes, and `team-busy`; the log and record locks; the engine's `team start` and `team end`; and per-team `snapshot` and `check-run`. It changes no file of F16's instruction set, so it runs while tstack #63's build holds that set: `check_exam.py` and `troy_exam.py affected` must find the instruction hash unchanged. It can run one team in a worktree, with the brief's sentence and the main session's steps given by hand.
2. **Part 1b, after #63's build merges.** `brief --repo`: the team sentence, absolute Read first paths, and `PYTHONPATH` in the checks (sections 3.2 and 3.11). It changes `brief.py`, so its PR carries a "Role exam" section, which finds no case affected (section 6).
3. **Part 2, after part 1b.** `plan` and AR7, `merge-check`, the skill's loop, waits, changes, releases, `status` and the progress file for several teams, F15's issues, `retro`, `costs`, and the Python environment's check. It carries the role exam of section 6 and the trial of section 8.3.

| When | F20's status in requirements 7.2 |
| --- | --- |
| Part 1a merges | Written, part 1a of 3: the hooks and the engine keep a team's roles in its own worktree, checked by tests and planted bugs. Briefs do not name a team yet, and troy-mode does not run teams. |
| Part 1b merges | Written, part 1b of 3: as part 1a, and a team's brief names its checkout. troy-mode does not run teams yet. |
| Part 2 merges after a passing trial | Runs on a sample project: two teams built two features at the same time on a scratch GitHub project, with rebases, a conflict, and a resume after a stop. Not yet used on a real project. |
| The next real project runs teams | Used on a real project |

Each part's PR updates F20's status itself, since its tests, planted bugs, and, for part 2, the trial run before it opens.

## 9. Not in F20

- Teams on more than one machine or in the cloud, and teams of people (requirements section 9).
- Starting a feature against a soft dependency's mock (Q19 leaves it for later).
- A session of its own for each team (Q17).
- Roles started with `isolation: "worktree"`, since such a worktree cannot hold a team's branch (section 2).
- An environment per team in a Python series, unless Troy chooses D275 B.
- Changes to F01's templates or to troy-init.

## 10. Decisions for Troy

D261 to D267 belong to the designs of tstack #73 and #74, so F20 takes D268 to D279. Troy approved every decision on 2026-11-22 with the recommendation ("全按推荐"). The standing yes for small issues did not cover them, since F20 is a new feature.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D268 | How does a role work in its team's worktree, when the Agent tool has no folder option and the hooks always see the session's folder (section 2)? | A: the brief names the team's checkout; the hook reads it from the role's transcript at the first call, roots every Bash and PowerShell command and path-less Glob and Grep in the worktree through `updatedInput`, and refuses file writes outside it (section 3.2). B: the same brief, but no rooting: the hook refuses every command that does not start with `cd <worktree>`, and the role writes it each time. C: `isolation: "worktree"` for each role run, with the main session carrying each run's work onto the team's branch. D: no worktrees: all teams share the home checkout, and the hooks blame changes by path. | A, approved by Troy on 2026-11-22 ("全按推荐"). The probes show that it works and that the role needs to remember nothing. B costs a refused call whenever a role forgets, and the pilot's roles ran hundreds of commands. C cannot base a run on the team's branch, so every run starts from the main session's commit, and the copying is a new error source. D breaks change detection as soon as two roles write at once, which Q21 rules out. |
| D269 | Where do the teams' worktrees live, and when do they go? | A: `<home checkout>/.troy-teams/<id>`, excluded through `.git/info/exclude`, made by `team start` and removed by `team end` after the feature's acceptance, which first appends the team's log lines to the common log (section 3.1). B: beside the checkout, outside the session's folder. C: as A, but every worktree stays until the version's retrospective. | A, approved by Troy on 2026-11-22 ("全按推荐"). Inside the session's folder, Claude Code treats the worktree as the project's, so roles need no extra permission. The exclude file changes no project file and needs no troy-init upgrade. Archiving the log keeps the retrospective's lines (Q21) and lets the worktrees go: a version of 13 features would otherwise keep 13 checkouts. B needs a working-folder permission in every session. |
| D270 | Where do the hooks keep a team role's record and log lines, and how are concurrent writes kept safe? | A: in the team's worktree's git folder, as Q21 says, found by agent ID across the worktrees for the main session's `TaskStop` and `SessionEnd`; a lock file around each log append and each record update (section 3.3). B: all records and lines in the common git folder, each with a `team` field. C: A without the locks. | A, approved by Troy on 2026-11-22 ("全按推荐"). It is what Q21 approved, teams share no state file, and the lookup is one folder listing. B would change Q21's text. C loses lines: two writers lost 9 of 600 log lines on Troy's PC, and a role's two calls at once can lose a task of D231's record. |
| D271 | How does the Architect plan a batch and check a design against it (Q20)? | A: a new task AR7 in the Architect's agent file, with a plan run and a check run, whose plan `plan` parses and keeps (section 3.4). The role exam then runs ar-design-review and ar-error-review: $62.80 for the first round, $125.60 with second rounds, above the $60 line (section 6). B: AR5, Answer, with the questions and the plan's form in Input; no agent file changes, and the exam costs $0. | A, approved by Troy on 2026-11-22 ("全按推荐"), with Troy's yes to the exam's $62.80, up to $125.60. The plan is a task of its own with a fixed form that the engine reads, and the agent file is where a role's tasks live (F04 common rule 1). With B, the Architect reads "answer from the architecture" and a form that only Input holds, and AR5's Summary is one to three sentences. The exam also shows that AR2's two cases do not get worse with the longer file. |
| D272 | What does the engine check at a merge, besides R24? | A: `merge-check`: the PR holds the latest `origin/main` (R24), every changed source and test path lies in the modules the plan gives the feature, and a next-version code PR waits for the tag (section 3.7). B: R24 and the tag only. | A, approved by Troy on 2026-11-22 ("全按推荐"). The plan's modules are where two teams collide. Checking the PR's paths against them turns Q20's "the engine checks mechanically" into a check of the plan, with the module table's path patterns that R07 already uses, and costs no model call. |
| D273 | How is a rebase conflict resolved (Q22)? | A: redo on the new main: abort the rebase, make the stage's branch again from `origin/main`, and run the role whose scope holds every conflicting path again, with its old diff and the paths as Input; PR 6's status row is the main session's own; a mix of scopes escalates (section 3.7). B: resolve inside the stopped rebase: the role edits the conflict markers, and `snapshot` and `check-run` learn a tree in the middle of a rebase. | A, approved by Troy on 2026-11-22 ("全按推荐"). The tree is clean, so `snapshot`, `check-run`, the hooks, and the one commit work as for any revision. B adds a state that every check would have to know, and a role that cannot run git could not continue the rebase anyway. |
| D274 | When does a PR rebase, and when does it get a second review? | A: only when it is about to merge; the Code Reviewer reviews again when the lines the PR adds and deletes changed, for PR 3 to PR 5; PR 1, 2, and 6 run their checks again only (section 3.7). B: rebase every open PR after each merge. C: review again after every rebase. | A, approved by Troy on 2026-11-22 ("全按推荐"). Rebasing at merge time costs each PR at most one more CI run per merge of another team, where B costs one per open PR at every merge. Comparing added and deleted lines leaves out a rebase that only moved them, which C would review for nothing. Only PR 3 to PR 5 have a Code Reviewer, so Q22's "the Code Reviewer reviews the rebased diff" applies to them. |
| D275 | How does each team test its own code in a Python series' shared environment (Q20)? | A: one environment per series; each team's checks run with `PYTHONPATH` set to its worktree's source folders, which come before the editable install (section 3.11). B: one environment per team, which changes requirements section 8. C: install the team's worktree into the shared environment before each team's checks, one team at a time. | A, approved by Troy on 2026-11-22 ("全按推荐"). It keeps section 8's rule and the series' one lock, and needs no install per team. B needs Troy's change of section 8 and an environment for every team. C serializes the teams' checks and leaves the environment pointing at whichever team ran last. |
| D276 | How is the main session kept from changing a team's worktree while one of its roles runs? | A: rule `team-busy`: the main session's git writes and file writes in that worktree are refused while a record of the team is open (section 3.3). B: the skill's words only, as F07 section 6.2 has today. | A, approved by Troy on 2026-11-22 ("全按推荐"). Requirements 5.8 prefers a check to an instruction. With several teams, the main session switches between worktrees all the time, and one commit in the wrong one would blame a role for the main session's change. The hook already reads `-C` and `cd`. |
| D277 | May a team's roles change the shared documents: the requirements, the architecture, its ADRs, and the version test plans? | A: no. A team's write scopes leave them out; the Architect's writes there (AR3 after Troy accepts, AR4, AR6) run in the home checkout as the main session's own PR (section 3.3). B: yes, and only the plan keeps teams apart. | A, approved by Troy on 2026-11-22 ("全按推荐"). Q20 lets only the main session and the Architect's planning step change them, and the hook can hold that line mechanically. ADR numbers stay serial. A team that needs one of them waits for that PR, as a team waits for any change. |
| D278 | How does F20 land? | A: two PRs: part 1, the hooks and the engine's base; part 2, the loop, AR7, the exam, and the trial. B: one PR. C: three PRs: part 1a, the hooks and the engine's base, which change no file of the instruction set; part 1b, `brief --repo`, after tstack #63's build merges; part 2, the loop, AR7, the exam, and the trial (section 8.4). | C, decided by Troy on 2026-11-22 ("现在开始"), in place of A, which Troy had approved earlier that day ("全按推荐"). Part 1a can then run while tstack #63's build holds the instruction set, and each part is checked on its own by tests and planted bugs. Q10's list of exceptions names F01 to F10 only, so no requirement changes. |
| D279 | How is F20 checked, and when does its status move? | A: tests from this design by a separate agent, planted bugs, and a trial on `ZJUCao/troy-mode-trial` with two teams at once, about 30 role runs and about $85 at list prices; status "Runs on a sample project" after it (section 8). B: tests and planted bugs only, status "Written" until a real project. | A, approved by Troy on 2026-11-22 ("全按推荐"), with Troy's yes to the trial's about $85. Only a real repository shows two teams' roles, CI runs, rebases, and merges at once, and Q21 asks for exactly that trial. Its cost is about one pilot feature. |
| D290 | On Windows, the engine refuses a `--repo` path in Git Bash's form, `/tmp/...` or `/c/...`, when Git Bash passes it on as typed, as it does with `MSYS_NO_PATHCONV=1` (the trial's follow-up, section 8.3). How does the engine read such a path? | A: on Windows only, a `--repo` folder that does not exist as given and starts with one `/` becomes the output of `cygpath -w` when `cygpath` is on the `PATH`, and otherwise `/c/rest` becomes `C:\rest`; the command refuses when that folder does not exist either (section 4). B: the drive mapping only, never `cygpath`. C: no conversion; the refusal names the Windows form to use. | A, approved under Troy's standing yes of 2026-11-22. `cygpath` knows Git Bash's own mounts, such as `/tmp`, which the trial's worktrees were under and no fixed mapping can know, and every shell that gives such a path has it. B still refuses `/tmp/...`, the trial's case. C leaves the main session to retry with another path, which the trial's session had to do by hand. A folder that exists as given keeps its meaning, so no path that works today changes. |

No decision changes the requirements' text. With D271 and D279, Troy said yes on 2026-11-22 to two costs, both spent at build time: the role exam's $62.80 for the first round, up to $125.60 in all, and the trial's about $85. Either still waits for Troy when it runs well over its estimate: the exam at its guard, 1.5 times its estimate (F16 section 10.2), and the trial past about $130.

## 11. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-22 | First draft, with D268 to D279 and the probes of section 2. |
| 1.0 | 2026-11-22 | Approved by Troy with D268 to D279, every recommended answer ("全按推荐"), with the role exam's and the trial's estimates. |
| 1.1 | 2026-11-22 | D278 changed by Troy on 2026-11-22 ("现在开始"): three build PRs, part 1a now, part 1b after tstack #63's build, and part 2 after that; each part's PR updates F20's status (sections 8.4 and 10). |
| 1.2 | 2026-11-22 | What part 1a's build settled: `SubagentStart` keeps writing a role's record while the repository has no team worktree, `team-busy` also refuses `git checkout`, and a writer that waits a second for a lock goes ahead without it (sections 3.2, 3.3, and 5). |
| 1.3 | 2026-11-22 | What part 1b's build settled: the source folders come from `[lang] source_roots`, the environment's fallback name is the main checkout's folder, and DV1's first-mock install in a team installs the main checkout (section 3.11). |
| 1.4 | 2026-11-23 | What part 2's build settled: only an interface that two features change needs an order in the plan (section 3.4), a feature already under way in the home checkout stays there (section 3.5), and `merge-check` checks source paths only (section 3.7); and the trial's results (section 8.3). |
| 1.5 | 2026-11-24 | D290, from the trial's follow-up, approved under Troy's standing yes of 2026-11-22: on Windows, a `--repo` folder that does not exist as given and starts with one `/` is read as Git Bash means it, with `cygpath -w` when it is on the `PATH`, or else as a drive path; a folder that is still missing is refused (sections 4, 8.1, 8.2, 8.3, and 10). No requirement changes. |
| 1.6 | 2026-11-25 | F18's design (D171 to D180, approved by Troy on 2026-11-25): an overturn holds its feature's team after its current stage PR, with `held` reason `overturn`; under spot checks, a risky PR's wait joins the one message and stops only its team, and a sampled PR stops none (section 3.8; F18 design section 7.5). The changes land with F18's build. |
| 1.7 | 2026-11-25 | F18 part 1's build (F18 design 5.3 and 7.5): a team whose feature has an open overturn is held after its current stage PR, with `held` reason `overturn` (after `change`, before `plan`), and each entry of `waiting` gives its wait ID (section 3.8). |
| 1.8 | 2026-11-26 | F18 part 2's build (F18 design 7.5): with spot checks on, a risky PR waits like an approval and its entry of `waiting` gives `risky`; a sampled PR stops no team (section 3.8). |
