# F05 design: hooks

| | |
| --- | --- |
| Feature | F05 in [requirements 1.15](../requirements.md#72-feature-list) |
| Version | 1.6 |
| Date | 2026-11-22 |
| Status | Approved by Troy on 2026-11-06, with D39 to D46. Version 1.1 records the facts the trial of section 13.3 settled. Version 1.2 adds D200, which Troy approved on 2026-11-16 as tstack issue #65. Version 1.3 adds D219, which Troy approved on 2026-11-18 as tstack issue #66. Version 1.4 adds D223, which Troy approved on 2026-11-16 as tstack issue #64. Version 1.5 adds D231, D232, and D234, which Troy approved on 2026-11-21 as tstack issue #49 (section 6.1). Version 1.6 notes the changes of F20's design (D268 to D279, approved by Troy on 2026-11-22), which land with F20's build. |
| Source of truth | This English file. [`F05-hooks.zh-CN.md`](F05-hooks.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F05 makes the rules that a role or Claude could break by mistake fail at the moment they are broken, not only later in CI. It delivers:

1. **Claude Code hooks**, shipped in the plugin. In a troy-mode project they:
   - keep each role inside its write scope (F04 design D31), with the Developer's edits to tests (R08) as one case;
   - keep every other subagent read-only;
   - allow roles only read-only git and GitHub commands, and only the skills they need;
   - stop Claude from skipping the git hooks, from opening a PR from `main` (R21), and from posting a PR, comment, review, issue, or release note whose text carries attribution (R19, D200);
   - stop every caller from running Python that reads its program from standard input (R23, D223);
   - keep a command that a role leaves running in the background from changing the tree after the role's report: they record it so that F07 ends it, and refuse every call of a role that has already stopped (section 6.1, D231, D232);
   - let roles read the plugin's own files without a permission rule.
2. **Git hooks**, shipped in troy-check's folder, which troy-init copies into each project. They refuse a commit that breaks R19, a commit on `main`, and a push to `main` (R21), whoever runs git.
3. **A local log** of every block, which F07 reads after each role run and F08's retrospective reads for a whole version (D219).

Every hook exits at once outside troy-mode projects (requirements section 8).

F05 does not copy files into projects (F06). It does not start roles or check `git status` after a run (F07). It does not check PRs (F02 and F03 in CI).

**What the hooks can and cannot catch.** They catch the mistakes of a cooperative role and Claude's habits, such as an attribution line or a commit on `main`. They do not stop a determined bypass: Bash can change files in ways no hook sees, and code run by a test can do anything. CI's R02 and R19 and F07's check after each run stay as the backstops.

The facts about Claude Code in this design come from its documentation on 2026-11-06 (the hooks, permissions, plugins, and sub-agents pages) and from the F04 trial (PR 15). The trial in section 13.3 checks the facts that the documentation leaves open.

## 2. Location

```text
hooks/
  hooks.json                  the plugin's hook config, in the plugin's standard folder (F01 D6)
troy-mode/
  hooks/
    troy_hook.py              entry point, one subcommand per hook event
    troyhook/                 internal modules (the Developer's choice)
    tests/                    unit tests (section 13.1)
  checks/
    git-hooks/                copied into projects with the rest of troy-check (F02 D8)
      commit-msg
      pre-commit
      pre-merge-commit
      pre-push
    tests/
      test_git_hooks.py       git hook tests (section 13.1)
```

- The Claude Code hooks use Python 3.11 or newer and the standard library only, like troy-check (F02 D7). They import troy-check's path classes, patterns, config reader, and attribution rules from the plugin's own `troy-mode/checks/`, so the hooks and CI classify paths the same way.
- `hooks.json` and the git hook names are fixed by Claude Code and git, so they cannot start with `troy-`. Every other new name does.
- Each `hooks.json` command runs in Git Bash (`"shell": "bash"`). It picks the interpreter with shell builtins only, so no extra process starts: `$TROY_MODE_PYTHON` when it is set, else `python` on Windows and `python3` elsewhere. On Windows, `python3` is often the Microsoft Store stub. Then it runs `troy_hook.py <event>`.
- The git hooks are POSIX `sh` scripts with LF line endings and the executable bit. Only `commit-msg` needs Python, which it picks the same way.

## 3. Hook events

| Event | Matcher | What it does |
| --- | --- | --- |
| `SessionStart` | All | Turns on the project's git hooks when `core.hooksPath` is unset (section 8.1). Removes role records older than a day, and log lines older than `[hooks] log_days` days, 30 by default (section 10, D219). |
| `SubagentStart` | `^troy-pstack:troy-` | Records the role's starting state for change detection (section 6). Keeps the record of a role that has already stopped as it is (section 6.1). |
| `PreToolUse` | `Bash\|PowerShell\|Edit\|Write\|NotebookEdit\|Skill\|TaskStop` | Checks file paths against the write scope (section 5), git, GitHub, and skill commands (section 7), the R19 and R21 guards (section 8.2), and R23's Python check (section 8.3). Refuses every call of a role that has already stopped, and closes a role's record when the main session stops it with `TaskStop` (section 6.1). |
| `PreToolUse` | `Read`, with `"if": "Read(//**/troy-pstack/**)"` | Allows reads of the plugin's own files (section 9). |
| `PreToolUse` | `Glob\|Grep` | Allows searches of the plugin's own files (section 9). |
| `PostToolUse` | `Bash\|PowerShell\|Skill` | For roles: reports changes outside the write scope that the call made (section 6), and records a command that Claude Code moved to the background (section 6.1). |
| `SubagentStop` | `^troy-pstack:troy-` | For roles: keeps the role working until it undoes changes outside its scope, once (section 6). Then marks the role stopped and keeps the commands it left running (section 6.1). |
| `SessionEnd` | All | Closes the records of the ending session's roles (section 6.1). |

- Matchers on `SubagentStart` and `SubagentStop` match `agent_type`, an unanchored regular expression, so the pattern starts with `^`.
- Each entry has `"timeout": 10`. Claude Code's default is 600 seconds, and a timed-out `PreToolUse` hook lets the call go ahead.
- A hook blocks with JSON on stdout and exit code 0: `permissionDecision: "deny"` with a reason for `PreToolUse`, and `decision: "block"` with a reason for `PostToolUse` and `SubagentStop`. Claude Code shows the reason to Claude.
- Claude Code checks deny and ask rules in settings whatever a hook returns, so a hook's `allow` never overrides them.

## 4. Who is calling

**The gate.** Each event first walks up from the input's `cwd` to the nearest folder that holds `.git` (a folder, or a file in a worktree). The call is in a troy-mode project when that folder has a `.troy-mode/` folder. Otherwise the hook exits with code 0 and prints nothing.

**Callers.** In a troy-mode project the hook sorts each call into one of three callers (D40):

| Caller | How it is recognized | Files | git and GitHub | Skills | Change detection |
| --- | --- | --- | --- | --- | --- |
| Main session | No `agent_id` in the input | Not limited | Writes allowed, with the R19 and R21 guards of section 8.2 | Any | None |
| Role | `agent_type` matches `^troy-pstack:troy-(architect\|interface-designer\|test-manager\|developer\|test-engineer\|code-reviewer)$` | The role's write scope (section 5) | Read-only (section 7) | `code-review` and `security-review` only | Yes (section 6) |
| Other subagent | Any other `agent_id`: `general-purpose` forks such as `/code-review`'s, Explore, or an unknown `troy-pstack:troy-*` name | Nothing in the repository except ignored files (section 5) | Read-only (section 7) | As for roles | None |

- The main session is the Product Manager and the project manager at once, and the hook cannot tell which is acting. So F05 does not limit its files. F07 keeps the Product Manager to its scope.
- The F04 trial showed that `/code-review` runs as a fork whose calls carry `agent_type` `general-purpose`. A hook that matched only `^troy-pstack:troy-` would leave those calls unchecked. Making every other subagent read-only covers them without knowing their parent, which Claude Code does not report.

## 5. Write scopes

### 5.1 Table

The scopes are those of F04 design section 3. `troyhook` holds them as a table, and a test keeps that table equal to the Write scope section of each agent file.

| Role | May change |
| --- | --- |
| Architect | `docs/architecture*.md`, `docs/adr/**`, `docs/features/*/design*.md` |
| Interface Designer | `docs/features/*/design*.md` |
| Test Manager | `docs/features/*/test-plan*.md`, `docs/versions/*/test-plan*.md` |
| Developer | The `source` and `dependencies` path classes |
| Test Engineer | The `tests` and `dependencies` path classes |
| Code Reviewer | Nothing |
| Other subagent | Nothing |

- The Architect may change only section 4 of a design. Hooks see paths, not sections, so F07 checks the section after each AR2 run (F04 D37).
- The `dependencies` class stays open to the Developer and the Test Engineer at the hook. Whether the Architect reviewed the dependency and Troy accepted it is for CI's R16 flag and for F07, which knows the brief.
- No role may change `docs/rules*.md`, `.troy-mode/**`, `.github/**`, or any other `config` path.

### 5.2 Checking a path

For `Edit`, `Write`, and `NotebookEdit`, the hook checks the tool's path before the call:

1. **Normalize.** Make it absolute against `cwd`, resolve `..` and links, turn Git Bash forms such as `/c/Users/...` and `/tmp/...` into real paths, and compare without case on Windows.
2. **Inside the repository:**
   1. A path in the `.git` folder is refused.
   2. A path that git ignores (`git check-ignore`) is allowed, as F04's common rule 5 says. Build output and caches live there.
   3. Otherwise troy-check's `classify` gives the path's class, with the `[paths]` table of `.troy-mode/config.toml` as committed at `HEAD`. An uncommitted edit of the config cannot widen a scope. The path is allowed when the caller's scope holds its class or one of its patterns matches.
3. **Outside the repository** (D42): allowed in the system temp folder (Python's `tempfile.gettempdir()`, and `/tmp` on Linux and macOS) and in the session's scratchpad (`scratchpad_dir` in the hook input). Refused anywhere else. The F04 trial's Test Manager made its scratch copies in the temp folder, which stays allowed. The hook only lets these writes through: Claude Code's own permissions still apply, and in a session where nobody can approve a prompt they refuse `Write` outside the project. The F05 trial showed this, so a role makes its scratch copies with Bash, as the F04 trial's Test Manager did.

A refusal tells the caller the path, its class, its write scope, and what to do: "If the task needs this file changed, stop and report `needs-answer`."

## 6. Changes made through Bash (D41)

The F04 trial showed that the Developer and the Test Engineer write most files through Bash heredocs. A hook cannot read a write target out of every shell command, so for roles F05 compares the working tree instead.

1. **Start.** At `SubagentStart`, the hook records the role's starting state in `<git dir>/troy-mode/agents/<agent_id>.json`: every path that `git status --porcelain=v1 -z --untracked-files=all` lists, with a SHA-256 hash of its content. If that record is missing, the role's first `PreToolUse` call makes it.
2. **After each shell or skill call.** At `PostToolUse` for `Bash`, `PowerShell`, and `Skill`, the hook takes the same snapshot. A path is changed when it is new in the list, has left it, or has a different hash. Changed paths outside the role's scope (section 5) make the hook answer `decision: "block"` with the list and the way back: `git restore -- <path>` for a tracked file, and deleting a file the role created. The command has already run, so this is feedback, not prevention.
3. **At the end.** At `SubagentStop`, the hook checks again. If changes outside the scope remain and `stop_hook_active` is false, it blocks the stop with the same list, so the role undoes them. If `stop_hook_active` is true, the role already had its chance: the hook lets it stop, logs the paths, and F07's check after the run stops the flow. It then marks the record stopped and keeps it (section 6.1).

`Skill` is in the `PostToolUse` matcher because a forked skill, such as `/code-review`, works while the role waits. The fork's own changes then show up as the role's.

- **Assumption.** Nothing else changes the checkout while a role runs. F07 runs one writing role at a time and waits for it (F04 section 9.2). If something else writes, the hook blames the role, which fails safe. In the pilot, a command that an earlier role had left running in the background broke this assumption. Section 6.1 keeps it.
- **Other subagents get no change detection.** They may run in the background beside the main session, and the main session's own edits would then be blamed on them. They get the checks before each call only.
- **Not seen.** Bash writes outside the repository, and changes inside the `.git` folder.
- **Cost.** One `git status` and the hashes of the changed files per role shell call: about 50 ms on Troy's PC for a small project.

### 6.1 Work a role leaves running (D231, D232)

**What the pilot showed.** tstack issue #49 names a Developer run of `ZJUCao/recipe-menu#12` that hung in the background for 11.5 hours. Its transcript shows that the run itself ended after 3 minutes. One of its commands, a `python -` heredoc, passed the Bash tool's 120-second limit, and Claude Code moved the command to the background instead of stopping it. The Developer tried to stop it, but subagents have no `TaskStop` tool ("No such tool available"). It reported, and the main session went on. 11.5 hours later the command ended and wrote its old edit, 33 duplicate lines, during F03's Test Engineer run, and `check-run` blamed the Test Engineer. The two Python processes of 2026-11-13 came about the same way: Test Engineer commands moved to the background, which ended on their own about 40 minutes after the report.

In `ZJUCao/recipe-menu`'s three session transcripts, 52 of 331 role runs had a command moved to the background, most of them by the 120-second limit, and in 19 the command still ran when the role reported. It still happens with the current CLI. On 2026-11-21, with Claude Code 2.1.328, a Test Manager's hung command ran for 2 hours after its report. The permission classifier refused the Test Manager's `taskkill` ("Destructive or Unwanted Actions"), and the main session left the task running. When the command ended, Claude Code woke the Test Manager. F05's `SubagentStart` hook took a new record of the tree, which by then held the running Developer's edits, and at the Test Manager's next stop the `SubagentStop` hook told it to `git restore` three of the Developer's files. The Test Manager declined.

**What Claude Code does.** From the pilot's desktop transcripts, and from probes on 2026-11-21 with the bundled CLI 2.1.328 in nested `claude -p` sessions. The probes ran in a scratch git project with a plugin that logged every hook input and a haiku worker, and cost $0.09.

| Fact | Evidence |
| --- | --- |
| In the desktop app, the Agent tool has no `run_in_background` parameter, and every role runs as a background agent. With `claude -p`, the parameter exists. | 327 of the 331 role calls in `ZJUCao/recipe-menu`'s transcripts, CLI 2.1.317 to 2.1.328, returned "Async agent launched"; the other 4 have no result there. Probe 1. |
| A command past the Bash tool's time limit moves to the background as a task with an ID. The `PostToolUse` input then holds `tool_response.backgroundTaskId` and `timedOutAfterMs`. | Probe 1 |
| The `SubagentStop` and `Stop` inputs list the session's running `background_tasks`: `id`, `type` (`subagent` or `shell`), `status`, and a shell's `command`. They do not say which agent started a shell. | Probes 1 and A |
| A subagent's command keeps running after the subagent's final response. When it ends, Claude Code wakes the subagent: `SubagentStart` and `SubagentStop` fire again with the same `agent_id`. | Probe A; the pilot on 2026-11-11 and 2026-11-21 |
| A subagent can stop its own command only when its tools include `TaskStop`. Then a `SubagentStop` block that names the task makes it do so. | Probes F and G; the pilot on 2026-11-10 |
| The main session's `TaskStop` with the command's task ID ends the command and its child processes, and wakes the subagent. With the subagent's agent ID, it ends the subagent and its commands, and does not wake it. | Probes B and C |
| When the session exits, Claude Code ends its background commands and their child processes. | Probe D |
| The desktop app tells the main session: "This agent stopped with background work of its own still running. It may resume on its own when that work completes or reports". | Notices for the 19 role runs above |
| With `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, the Agent tool runs the subagent in the foreground, and a command past its time limit is stopped (exit code 143) instead of moved. Not tried in the desktop app. | Probe E |
| With `claude -p`, a background command is stopped after 10 minutes. The desktop app showed no such limit: one ran for 2 hours. | Probe 1; the pilot on 2026-11-21 |

So the issue's first fix, roles in the foreground, is not possible in the desktop app, where troy-mode runs. Nor can today's records tell whether a role's work still runs. The hook deletes a role's record at its first stop, so the pilot's leftover command had none. A role that a usage limit or a closed session ended keeps its record for a day, although nothing runs. A process list is not needed either: Claude Code tracks each such command as a task, and gives the hooks its ID.

**The record (D231).** `<git dir>/troy-mode/agents/<agent_id>.json` keeps, besides the starting state of section 6:

| Field | Meaning |
| --- | --- |
| `session` | The `session_id` of `SubagentStart`, which is the main session's. |
| `started` | When the record was made, in UTC. |
| `stopped` | When the role stopped for good, or null while it runs. |
| `background` | The task IDs of the role's commands that Claude Code moved to the background and that may still run. |

A record is **open** while `stopped` is null, or while `background` holds a task. A record without these fields, written by an earlier plugin, counts as closed.

**The hooks (D231).**

1. **A command moves to the background.** At a role's `PostToolUse` for `Bash` or `PowerShell`, the hook adds `tool_response.backgroundTaskId` to `background`. A call with `run_in_background` should report its task the same way; the probes did not try one, and the build's trial checks it (section 13.3). The hook also tells the role, in `additionalContext`: "troy-mode: this command now runs in the background as task <ID>. You cannot stop it, and the main session stops it after your report, so do not wait for its result. Say in your report what you could not check."
2. **The role stops.** When `SubagentStop` lets a role stop (section 6, step 3), the hook sets `stopped` and keeps in `background` only the tasks that the input's `background_tasks` lists as running shells. If any remain, it writes one log line with rule `background`, decision `stop`, and the task IDs in `tasks` (section 10). It no longer deletes the record.
3. **The main session stops a task.** At the main session's `PreToolUse` for `TaskStop`, a `task_id` that is a record's agent ID closes that record: the hook sets `stopped` and empties `background`. A `task_id` in a record's `background` is removed from it. The hook prints nothing, so the call goes on. Because the hook closes the record before the call, a `TaskStop` of a task that no longer runs, which fails, still clears a stale record.
4. **The session ends.** `SessionEnd` closes every record whose `session` is the ending session's, since Claude Code ends the session's background commands as it exits (probe D).
5. **The day's limit.** `SessionStart` still removes records more than a day old (section 10).

**A role that has already stopped (D232).** When Claude Code wakes a role whose record is stopped:

- `SubagentStart` keeps its record as it is.
- `PreToolUse` refuses each of its calls (`Bash`, `PowerShell`, `Edit`, `Write`, `NotebookEdit`, and `Skill`) with rule `stopped`: "Your run has ended and your report was delivered. Do nothing more, and end your turn."
- `SubagentStop` does no change detection and never blocks. It only updates `background` from its input.

Its reads (`Read`, `Glob`, and `Grep`) are not refused, since they change nothing. troy-mode never sends a stopped role a new message: a revision is a fresh run (F07 section 6.1).

**F07's part.** `check-run` and `snapshot` read the records (F07 section 7). `check-run` refuses while a record of the run's roles is open, and `snapshot` while any record is open. Each names the agent IDs, and the entry skill ends each with `TaskStop`. Probe C showed that this ends the role's commands without waking the role. In a role exam, `check-run` runs after the role's session has exited, when `SessionEnd` has already closed its records, so the new problem never changes U2's grade (F16 section 4.3).

**The role exam (F16).** What each option of D231 changes in F16's instruction set (F16 section 9.1), and what its exam costs. The estimates come from `troy_exam.py`'s own budget code: the recorded runs in `D:\Troy\troy-mode-work\cases\`, and the pilot's medians for cases with none. No exam ran. `main`'s instruction hash `67c8098d051d` has no recorded base run, so every base run would be measured fresh.

| Option | Instruction-set files it changes | Cases that run | Estimate |
| --- | --- | --- | --- |
| A | The entry skill's section "Running a role" | None: no case's Input changes, so `affected` finds none (F16 section 9.2) | $0 |
| B | The same. The hooks and `runs.py` are outside the set. | None | $0 |
| C | B, and the agent files of the five roles that have Bash, whose `tools` gain `TaskStop`. With a common rule "stop every command you start before you report", also `common.md`, which every agent file copies. | The ten cases of those five roles, or all twelve with `common.md` | $188.93, or $258.73 with `common.md`. Above $60, so Troy says yes first (F16 section 10.2). |
| D | None: troy-init's settings change | None | $0 |

A change to U5 (D233) changes `troy-mode/exam/troyexam/`, after which every case's anchors are proved again: $40.00 by the estimate. tstack issue #64's proof of the same kind cost $11.46. Troy chose B and kept U5 a note, so the build's role exam runs no case.

**Changes to other features.** F07's sections 6.2 and 7, and the entry skill's section "Running a role" (F07 design version 1.10). F10's guide: the reference row on "a file changed that no running role was working on" becomes a row on `check-run`'s `running` problem. troy-init and the projects' files do not change: the hooks and the records are the plugin's and the git folder's.

**Not covered.**

- A process that leaves Claude Code's process tree, for example through `start`, `Start-Process`, or `setsid`. Session exit does not end it, and no record names it. F16's U5 reports such a process in exams (F16 section 4.3, D233).
- Background commands of other subagents, such as `/code-review`'s fork. They get no record (section 4).
- A Claude Code process that ends without `SessionEnd`, for example when it is killed. Its records stay open until `TaskStop` or the day's limit clears them.

## 7. git, GitHub, and skills for subagents (D43)

### 7.1 Reading a command

For `Bash` and `PowerShell`, the hook splits the command into simple commands:

- It splits at `;`, `&&`, `||`, `|`, `&`, line breaks, and parentheses, and reads `$(...)` and backticks as commands of their own.
- It reads the string after `bash -c`, `sh -c`, and `eval` as a command.
- It skips leading variable assignments and the wrappers `command`, `env`, `exec`, `nohup`, `time`, `timeout`, and `xargs`, each with its options. `timeout` also drops its duration, the first word after its options. A command that came through `xargs` is marked as such, because `xargs` adds words to it (section 8.3).
- Since `timeout` is a wrapper (D223), the checks of sections 7.2 and 8.2 see `timeout 60 git push` as `git push`. Before, `timeout` hid the git command from them.
- It drops the body of every heredoc, so text such as "git commit" inside a file being written is not a command.
- It remembers each `cd <literal path>` for the commands after it. A path may also come from a variable set earlier in the same command, to a literal path or to the folder `mktemp -d` makes. The F05 trial's Test Manager made its scratch copy with `DST=$(mktemp -d <temp folder>/name-XXXXXX)` and `cd "$DST"`. Any other variable is unknown, and a git command in an unknown folder counts as one in the project.
- It reads `git`, `git.exe`, and paths ending in either the same way, and likewise `gh`.

If the command cannot be split, for example because a quote is unbalanced, a subagent's call is refused when its text matches a git write or a `gh` write anywhere. PowerShell syntax is read the same way, at best effort.

### 7.2 git

A subagent may run these git commands:

| Kind | Commands |
| --- | --- |
| Always | `status`, `diff`, `log`, `show`, `blame`, `grep`, `rev-parse`, `rev-list`, `ls-files`, `ls-tree`, `cat-file`, `merge-base`, `describe`, `shortlog`, `for-each-ref`, `show-ref`, `name-rev`, `check-ignore`, `check-attr`, `var`, `diff-tree`, `diff-index`, `diff-files`, `count-objects`, `archive`, `fetch`, `ls-remote`, `version`, `help` |
| Listing forms only | `branch` and `tag` with no name to create, `remote` with no subcommand or with `-v`, `get-url`, or `show`, `config` with `--get`, `--get-all`, `--get-regexp`, `--list`, or one key and no value, `stash list` and `stash show`, `worktree list`, `reflog` and `reflog show` |
| Working tree only | `restore` without `--staged`, `-S`, `--source`, or `-s`. A role uses it to undo a change outside its scope (section 6). |

- Every other git command is refused: `commit`, `push`, `add`, `rm`, `mv`, `reset`, `stash` with changes, `switch`, `checkout`, `merge`, `rebase`, `cherry-pick`, `revert`, `am`, `apply`, `clean`, `tag` and `branch` that create or delete, `config` that sets, `worktree add`, `update-ref`, and the rest. A refused call quotes common rule 6: the main session commits, opens PRs, and posts reviews.
- **Scratch repositories.** A git command whose repository lies in the temp folder or the scratchpad (named by `-C`, `--git-dir`, `--work-tree`, `GIT_DIR`, `GIT_WORK_TREE`, or an earlier `cd`, each with a path section 7.1 can follow) may do anything except `push`. The Test Manager can then commit a scratch copy and run `troy-check code` on it to check R09. A clone of the project can push into the project, so `push` stays refused.
- Global options before the subcommand, such as `-C`, `-c`, `--no-pager`, and `--git-dir`, are read and skipped. `-c core.hooksPath=...` is refused for every caller (section 8.2).

### 7.3 GitHub CLI

A subagent may run `gh pr view`, `gh pr diff`, `gh pr list`, `gh pr checks`, `gh pr status`, `gh issue view`, `gh issue list`, `gh issue status`, `gh repo view`, `gh run view`, `gh run list`, `gh release view`, `gh release list`, `gh search`, `gh status`, `gh auth status`, and `gh api` with no method other than `GET` and no `-f`, `-F`, `--field`, `--raw-field`, or `--input`. Every other `gh` command is refused.

### 7.4 Skills

A subagent's `Skill` call is allowed only for `code-review` and `security-review` (with or without a plugin prefix), and only when its arguments hold neither `--fix` nor `--comment`. This enforces F04's D36: the Code Reviewer reviews and changes nothing. The input field names of `Skill` are not documented. The trial (section 13.3) showed them: `skill` holds the name, and `args` holds the arguments and is left out when there are none.

## 8. R19, R21, and R23 (D44, D223)

### 8.1 Git hooks

| Git hook | Rule | Refuses |
| --- | --- | --- |
| `commit-msg` | R19 | A message or author email that `troy_check.py commit --message-file "$1"` fails (F02 design 3.2). It runs the project's own copy of troy-check, with the project's attribution mode. |
| `pre-commit` | R21 | A commit while the current branch is `main`. |
| `pre-merge-commit` | R21 | A merge commit while the current branch is `main`. |
| `pre-push` | R21 | A push that updates or deletes `refs/heads/main` on the remote, read from the lines git passes on standard input. |

- They apply to every commit in the clone, Troy's own from a terminal included. Troy can still skip them with `--no-verify`. Claude cannot (section 8.2).
- `commit-msg` refuses the commit when it finds no Python 3.11 or newer, because R19 then cannot be checked.
- **Turning them on.** Git runs them when `core.hooksPath` is `.troy-mode/checks/git-hooks`. troy-init sets it at setup (F06). A fresh clone does not have it, so the `SessionStart` hook sets it when it is unset and tells Claude so in `additionalContext`. When it holds another value, the hook leaves it and tells Claude that the troy-mode git hooks are off.
- Detached `HEAD`, rebases, and cherry-picks on `main` do not run `pre-commit`. `pre-push` still stops them from reaching `main`. Troy's GitHub plan has no branch protection (F02 D14), so `pre-push` is the last local gate and CI the last gate.

### 8.2 Claude Code guards

For every caller in a troy-mode project, the main session included, the `PreToolUse` hook refuses:

- `git commit` with `--no-verify` or `-n`, and `git push`, `git merge`, `git am`, or `git rebase` with `--no-verify`. `git push -n` is a dry run and stays allowed.
- `-c core.hooksPath=...` before any git subcommand, and `git config` that sets or unsets `core.hooksPath`.
- `git commit`, `git merge`, and `git push` while `core.hooksPath` is not `.troy-mode/checks/git-hooks` or the hook files are missing. The reason says how to turn them on.
- `gh pr create` from `main`: with `--head main` or `-H main`, or with no `--head` while the current branch is `main` (R21).
For the main session, the same hook checks the text of every `gh` command that posts text to GitHub, before it runs (R19, D200). Subagents stay refused for every `gh` write (section 7.3).

| Commands | Text it reads |
| --- | --- |
| `gh pr create`, `gh pr edit`, `gh issue create`, `gh issue edit` | `--title`/`-t`, `--body`/`-b`, `--body-file`/`-F` |
| `gh pr comment`, `gh issue comment`, `gh pr review` | `--body`/`-b`, `--body-file`/`-F` |
| `gh pr merge` | `--subject`/`-t`, `--body`/`-b`, `--body-file`/`-F` |
| `gh release create`, `gh release edit` | `--title`/`-t`, `--notes`/`-n`, `--notes-file`/`-F` |
| `gh api` with a method other than `GET`, or with fields | The values of `-f`/`--raw-field` and `-F`/`--field`, the file named by `-F key=@file`, and the `--input` file |

- **What is checked.** Each option takes its `--x v`, `--x=v`, `-x v`, and `-xv` forms. The text is the option values, every heredoc in the call, and the contents of each named file, read relative to the folder the command runs in. `troycheck.attribution.find_attribution` checks it in the project's `[attribution] mode` as committed at `HEAD`, as `check-text` does. A `gh` command with no text to post, such as `gh pr merge --rebase` or `gh pr review --approve`, passes. A command for another repository (`--repo`) is checked the same way.
- **The refusal.** Rule `attribution`. The reason names R19, the command, and the first line that fails. The log line holds the command name, such as `gh pr comment`, and never the text or a file's path (section 10).
- **Fail closed.** The hook also refuses, with rule `attribution`, a posting command:
  - whose body, notes, or input file is missing or unreadable, or is named by a word the hook cannot resolve (an unknown variable, or a relative path after a `cd` it cannot follow);
  - with `--body-file -`, `--notes-file -`, `--input -`, or `-F key=@-` and no heredoc in the call, because a pipe is text the hook cannot see;
  - with `--editor`/`-e` or `--web`/`-w`, because the text is then written where the hook cannot see it;
  - whose text option holds an unknown variable or a command substitution other than `cat` of a heredoc, such as `--body "$(cat c.md)"`, because the hook cannot see that text either.

  A main-session call that cannot be split and whose text holds a posting `gh` command is refused with rule `unparsed` (section 7.1). An error while checking a posting command refuses it with rule `error` (section 10).
- **Never paths.** The hook never scans file paths or the whole command line: a scratchpad path can itself hold a word that strict mode refuses, and scanning paths would refuse every post from it.
- **Known limit.** A file is checked as it is when the call starts. A call that rewrites the body file and posts it in the same line is checked against the old text, or refused when the file does not exist yet. The troy-mode skill says to write the file in an earlier call. The hook does not tie a heredoc to the command it feeds, so a pipe into `--body-file -` passes when the same call holds another heredoc, which is checked. `gh api` with `-X GET` and fields counts as a post, as the table says.
- This catches the "Generated with Claude Code" line before the PR exists, and the #92 shape, where a comment was posted after a failed `check-text`, before GitHub holds the text and its edit history.

### 8.3 Python that reads its program from standard input (R23, D223)

For every caller in a troy-mode project, the main session included, the `PreToolUse` hook refuses a `Bash` or `PowerShell` command that runs Python with its program read from standard input. Such a run can hang at Python's interactive prompt until the shell tool's time limit. In `ZJUCao/recipe-menu`'s two session transcripts, 168 Python runs read their program from standard input and 39 of them hit the 120-second limit. Every such run fed by nothing or by `/dev/null` hung, and the warning in every brief did not prevent it (tstack issue #64).

**The programs.** After the unwrapping of section 7.1, a simple command whose program is `python`, `python3`, `python3.N`, or `py`, with or without a path and `.exe`. The runners `mamba run`, `micromamba run`, `conda run`, `uv run`, and `pixi run` are removed first, with their options, and the program after them is checked. A program held in a variable that section 7.1 cannot resolve is not checked.

**The arguments, read left to right:**

| Argument | Result |
| --- | --- |
| `-`, or `--` followed by `-` | Refused, as `python -` |
| `-i`, alone or in a flag group such as `-ui` | Refused, as `python -i` |
| `-c` or `-m`, alone, in a flag group such as `-Bc`, or with its value attached such as `-mpytest` | Allowed |
| `-W`, `-X`, or `--check-hash-based-pycs` | Skipped with its value: the rest of the word, such as `-Xutf8`, or else the next word |
| `-V`, `--version`, `-h`, `-?`, or an option that starts with `--help` | Allowed |
| Any other option | Skipped |
| The first word that is not an option | The script: allowed |
| Nothing of the above by the end | Refused, as `python` with no script, unless the command came through `xargs`, which adds its own words to it |

- A flag group is read letter by letter, left to right, each letter as the option of that letter, and the letters after `c`, `m`, `W`, or `X` are that option's value. So `-ic` refuses, because `i` comes first, `-ci` allows, since it runs the program `i`, and `-VV` allows.
- `--` ends the options: the word after it is the script. So `python -- x.py` allows, and `python --` alone refuses.
- For `py`, the first argument may be the launcher's own. `-0`, `-0p`, `--list`, and `--list-paths` allow, and a version selector such as `-3`, `-3.13`, `-3.13-64`, or `-V:3.13` is skipped.
- What feeds standard input does not matter: a heredoc, a pipe, `/dev/null`, a file, or nothing. The check is about where the program comes from, and it needs only the words, so a redirection the parser drops changes nothing. Python with a script file, `-c`, or `-m` may still read data from a pipe or `/dev/null`. None of the 257 such runs in the transcripts hung, and the main session reads `troy_flow.py`'s output that way, with `| python -X utf8 -c "..."`.
- Text inside a heredoc body, such as `python -` in a file being written, is not a command (section 7.1).
- A command that cannot be split (section 7.1) is not checked for R23.

**The refusal.** Rule `python-stdin`, decision `deny`. The reason:

```text
R23: `python -` makes Python read its program from standard input, and such a run can hang at Python's interactive prompt. Write the script to a file in the scratchpad (<scratchpad folder>) and run that file with the project's Python (`[lang] environment` <name>), for example `python -X utf8 <file>`. Python with a script file, `-c`, or `-m` may still read data from a pipe or `/dev/null`.
```

- The form it names is `python -`, `python -i`, or `python` with no script, whatever the program's own name or path. A line with several such commands names the first one only. A refused git or `gh` command in the same line keeps its own reason, in the order of the line, and the first refusal gives the log line's rule.
- The scratchpad's folder is named when the hook input gives `scratchpad_dir`, and the environment when the config at `HEAD` sets `[lang] environment`. Otherwise each part in parentheses is left out. A config that cannot be read only leaves out the environment: the command is still refused.
- The log line holds the rule and the decision, no subcommand, and never the command text (section 10).
- The refusal starts as soon as the plugin updates, before troy-init's upgrade adds R23 to a project's rules table, so the reason stands on its own.

**Not seen.** CI, the git hooks, `hooks.json`'s own commands, and the tests' subprocess calls do not pass through the Bash tool, so the hook never sees them. No file of an existing project holds such a command (`ZJUCao/recipe-menu`: none), so R23 needs no baseline and no cleanup.

## 9. Plugin files (D45)

The F04 trial showed that a role cannot read the plugin's own files, such as `skills/technical-writing/SKILL.md`, in a session where nobody can approve a permission prompt. Troy would also see a prompt for each such read.

A `PreToolUse` hook on `Read`, `Glob`, and `Grep` answers `allow` when the call is in a troy-mode project and its path lies inside `CLAUDE_PLUGIN_ROOT`, which Claude Code exports to plugin hooks. It prints nothing for any other path or project.

- The `if` rule `Read(//**/troy-pstack/**)` keeps the hook from starting for reads elsewhere. It matches both an installed plugin (`~/.claude/plugins/cache/<marketplace>/troy-pstack/<version>/`) and a checkout loaded with `--plugin-dir`.
- The trial showed that the rule filters only `Read`. With `Read|Glob|Grep` under one `if`, `Glob` and `Grep` calls in the plugin folder never reached the hook, and Claude Code refused them for want of a permission. So `Glob` and `Grep` run the hook without the `if`, as this section planned, and each pays the gate's cost (section 10).
- The installed path changes with every plugin version. The hook reads `CLAUDE_PLUGIN_ROOT` each time, so it needs no update.
- So troy-init (F06) writes no permission rule.

## 10. Errors, speed, and the log

**Errors (D39).** Any error inside `troy_hook.py`, such as an unreadable config or a git failure, is caught. For a role or another subagent, the call is refused with the error. For the main session, the hook prints a notice on stderr and exits with code 1, which Claude Code treats as a non-blocking error, so the main session can still repair the project. One exception (D200): an error while checking a `gh` command that posts text (section 8.2), such as an invalid config, refuses the main session's call with rule `error`, because text posted to GitHub keeps its edit history. Every other main-session call still only warns. `SessionStart` does not treat an invalid config as an error: it keeps every log line, turns on the git hooks, and exits with code 0 (D219, the log paragraph below). When no Python 3.11 or newer exists, the call is blocked in a troy-mode project and let through elsewhere: the `hooks.json` command tests `$CLAUDE_PROJECT_DIR/.troy-mode` with a shell builtin and exits with code 2 or 0 when the interpreter is missing, and `troy_hook.py` checks the version before it imports anything else. `onFailure: "block"` is not used, because it would also block calls outside troy-mode projects.

**Speed.** Measured on Troy's PC on 2026-11-06: Python starts in 40 to 65 ms, bash in about 25 ms, and a git command takes 40 to 50 ms.

| Call | Work | Estimate |
| --- | --- | --- |
| Any project outside troy-mode | bash, Python, the gate | 70 to 90 ms |
| A role's `Write` or `Edit` | Plus the config at `HEAD`, and `git check-ignore` for a path outside the scope | 120 to 170 ms |
| A role's shell call, after it ends | Plus `git status` and hashes | 120 to 170 ms |
| A `Read` outside a `troy-pstack` folder | None. The `if` rule skips the hook. | 0 ms |
| A `Glob` or `Grep` anywhere | bash, Python, the gate, and the plugin path test | 70 to 90 ms |

All are under the 200 ms target of requirements section 8. The hooks keep the config's text in the git folder, keyed by `HEAD`'s commit ID, so most calls read it without a git process. The trial measured every hook kind 20 times: the medians are 74 to 151 ms (the F05 PR has the table).

**Log.** Every refusal and block appends one JSON line to `<git dir>/troy-mode/hooks.log`: time, session, agent ID, agent type, event, tool, rule, the paths or git subcommand, and the decision. It never holds a command line or file content, so a secret typed in a command cannot reach it. R23's refusal (section 8.3) has rule `python-stdin` and no subcommand. A role that stops with commands still in the background gets a line with rule `background`, decision `stop`, and their task IDs in a `tasks` field, never their command text; a call of a role that has already stopped is refused with rule `stopped` (section 6.1). The git folder is never committed. F07 reads the log after each role run (section 12).

**How long the log keeps its lines (D219).** F08's retrospective (`retro --tag`, F08 section 7) counts the log lines since the previous version's tag, and a version can take many days: six in the pilot. So `SessionStart` keeps log lines for a number of days set in the project config:

```toml
[hooks]
log_days = 30   # how many days hooks.log keeps its lines
```

- **The value.** `[hooks] log_days` in `.troy-mode/config.toml`, read as committed at `HEAD` (section 5.2), like every other config read of the hooks. It is a whole number of 1 or more, and 30 when the key, the table, or the file is missing. `[hooks]` has no other key.
- **A bad value.** A `log_days` of 0, below 0, `true` or `false`, a decimal, or a string is a config error, and so is an unknown key in `[hooks]`. troy-check stops with exit code 2, as for any other config error (F02 section 7), and a role's hook call is refused (section 10, D39).
- **Which lines go.** At each `SessionStart`, a line whose `time` lies more than `log_days` times 24 hours before now is removed. A line exactly `log_days` days old stays. A line whose time cannot be read is removed, as before. The other lines stay, in their order.
- **Role records.** The records of section 6 are still removed when their file is more than one day old, whatever `log_days` says.
- **A config that is not valid.** `SessionStart` then removes no log line, still removes the old role records, still turns on the git hooks (section 8.1), and exits with code 0. Its `additionalContext` says that the committed config is not valid and that `hooks.log` was not cleaned. So a broken config never costs a log line and never stops the git hooks from being turned on.

A version that takes longer than `log_days` loses its earliest lines from the retrospective; the project then raises `log_days` in a `[rules]` PR. The log holds one short line per refusal and no text (above), so 30 days of it stays small.

## 11. How F05 maps to the requirements

| Requirement | Where F05 covers it |
| --- | --- |
| F05 row: marker-folder gate | Section 4, the gate |
| F05 row and F04 D31: each role's write scope, R08 among them | Sections 5 and 6 |
| F05 row and F04 D31: no git or GitHub writes by roles | Section 7 |
| F05 row: commits that break R19 | Section 8.1 (`commit-msg`) and 8.2 (PR titles and descriptions) |
| Section 6, R19: PR comments and reviews, issues, and release notes, checked before they are posted (D200) | Section 8.2 (every `gh` command that posts text) and section 10 (an error refuses the post) |
| F05 row: commits on `main` and pushes of `main` (R21) | Section 8.1 (`pre-commit`, `pre-merge-commit`, `pre-push`), and 8.2 for `gh pr create` |
| Section 6, R23, and the F05 row: Python never reads its program from standard input (D223) | Section 8.3, for every caller, and section 7.1 for `timeout` and `xargs` |
| F05 row, as D231 and D232 change it: commands a role leaves running in the background, and roles that have already stopped | Section 6.1 |
| Section 8, hooks exit at once outside troy-mode projects | Section 4, the gate, and section 9's `if` rule |
| Section 8, speed under 200 ms per call | Section 10 |
| Section 8, privacy | The log holds no command lines (section 10) |
| Section 8, new names start with `troy-` | Section 2. `hooks.json` and the git hook names are fixed by Claude Code and git |
| F04 D36, the Code Reviewer never runs `--fix` or `--comment` | Section 7.4 |

## 12. How F06 and F07 use F05

**F06.** troy-init copies troy-check's folder, `git-hooks/` included, into `.troy-mode/checks/`, and sets `core.hooksPath` at setup. It writes no permission rule for plugin files (section 9).

**F07.**

- It runs one writing role at a time and waits for it, so section 6 can blame changes on the right role.
- It ends a role's leftover work before it stages the run's changes and before the next run: `check-run` and `snapshot` refuse while a role's record is open, and the skill stops each named agent with `TaskStop` (section 6.1, D231).
- After each run, it keeps its own `git status` check (F04 section 9.2) as the backstop, adds that `HEAD` and the branch did not change, and reads the role's lines in `hooks.log`. Paths a role left outside its scope stop the flow.
- It commits, pushes, and opens PRs from the main session, so the git hooks of section 8.1 check every commit and push it makes.
- **troy-check code.** It reads commits only, and roles cannot commit (section 7), so a Developer that runs `troy-check code` during DV2 checks the previous commit, not its own work. The F04 trial showed this. F07 runs it after committing, or troy-check gains a working-tree mode. That is F07's design.

## 13. How F05 is checked

### 13.1 Tests

Tests use `unittest` and the standard library. A separate agent writes them from this design before the hooks exist (troy-pstack's build process). Each test builds a small git repository in a temporary folder and feeds `troy_hook.py` a hook input on stdin. The tests live in `troy-mode/hooks/tests/` and `troy-mode/checks/tests/test_git_hooks.py`. `troy-checks-tests.yml` runs them on Linux and Windows for every PR that changes `hooks/`, `troy-mode/hooks/`, `troy-mode/checks/`, or `agents/`.

| Group | Cases include |
| --- | --- |
| Gate | No `.troy-mode/`: every event exits 0 and prints nothing. `cwd` in a subfolder of a troy-mode project. Not a git repository. |
| Callers | Main session, each role, an unknown `troy-pstack:troy-*` name, `general-purpose`, `Explore`. A role name with text before or after it is not a role. |
| Scope table | Equals F04 section 3 and the Write scope section of each agent file. |
| Paths | Each role against each path class and pattern. An ignored path is allowed. `.git/` is refused. Temp folder and scratchpad allowed, home folder refused. Backslashes, drive letter case, Git Bash paths, and `..`. A config edit that is not committed does not widen a scope. An invalid config refuses a role's call. |
| Commands | Each allowed git and `gh` command passes, and each refused one is refused, alone and inside `;`, `&&`, `\|`, line breaks, `( )`, `$( )`, backticks, `bash -c`, and with variable assignments or `timeout` in front. A heredoc that holds "git commit" passes, also when the heredoc feeds a script file that is then run. Scratch repositories: `git -C <temp> commit` and `cd <temp> && git commit` pass, `git -C <temp> push` is refused. `gh api` with `GET` passes, with `-X POST` or `-f` it is refused. An unbalanced quote around a git write is refused. |
| Skills | `code-review` passes, with `--fix` or `--comment` it is refused, another skill is refused. The main session may run any skill. |
| Changes | A Developer creates a test file through Bash: `PostToolUse` blocks and names it. After `git restore` or deleting it, nothing blocks. A file that was already changed and changes again is found by its hash. Changes inside the scope are not reported. `SubagentStop` blocks once and then lets the role stop. A missing start record is made at the first call. |
| Guards | `--no-verify` and `commit -n` are refused, `push -n` passes. `-c core.hooksPath=` and `git config core.hooksPath` are refused. A commit while `core.hooksPath` is unset is refused. `gh pr create` on `main` and with `--head main` is refused, on a branch it passes. A PR body with "Generated with Claude Code" is refused. The word Claude in `trailers` mode passes. |
| Posting guard (D200) | Each posting command of section 8.2, in its long, short, and `=` forms, refused with a bad title, body, notes, or file and passed with a clean one; a strict-mode word passes in `trailers` mode. The #92 shape, `check-text ... \| grep -q ok; gh pr comment ...`, refused. A heredoc on stdin checked. `--body-file -` from a pipe refused. A missing file refused. A clean file in a folder whose name is a strict-mode word passes. `gh api -X POST` with `-f`, `-F key=@file`, or `--input` refused with bad text, and a `GET` passes. `gh issue create --repo` for another repository checked. `--editor` and `--web` refused. `--body "$(cat <file>)"` refused, `--body "$(cat <<'EOF' ...)"` checked. An unsplittable posting call from the main session refused. A check error refuses a posting command and only warns for others. The log line holds the command name and no text. Subagents still get the `gh` refusal of section 7.3. |
| Python from standard input (D223) | Each refused form of section 8.3 (`python -`, `python3 -`, `python -- -`, `python -i x.py`, `-i` in a flag group, `python` with no script, `-W` and `-X` with a value and no script, and `py -3.13 -`), for the main session, a role, and another subagent, and inside `&&`, `;`, `\|`, `$( )`, `bash -c`, `timeout`, `mamba run`, `uv run`, and PowerShell's `@'...'@ \| python -`. Allowed: `python x.py < /dev/null`, `\| python -c "..."`, `python -m pytest`, `--version`, `py -0p`, `xargs python`, and `python -` as text inside a heredoc body. Silent outside troy-mode. The reason names R23, the form, and the fix, with the scratchpad and the environment when they are known. The log line has rule `python-stdin`, decision `deny`, no subcommand, and no command text. `timeout 60 git push` is refused for a subagent. |
| Background work (D231, D232) | A role's `PostToolUse` for `Bash` and for `PowerShell` with `tool_response.backgroundTaskId` adds the task to `background` and answers with `additionalContext` that names it. Without it, the record does not change. The main session's and another subagent's calls record nothing. A `SubagentStop` that lets the role stop sets `stopped` and keeps only the tasks that `background_tasks` lists as running shells, and writes one `background` line with the task IDs and no command text. With none running, it writes no line. A blocked stop sets nothing. `SubagentStart` of a stopped agent leaves its record as it was. A stopped role's `Bash`, `PowerShell`, `Edit`, `Write`, `NotebookEdit`, and `Skill` calls are refused with rule `stopped`, its reads pass, and its stop does no change detection and never blocks, even with another role's changes in the tree (the shape of 2026-11-21). The main session's `TaskStop` with an agent ID closes that record, with a task ID removes the task, with an unknown ID changes nothing, and prints nothing in each case. A subagent's `TaskStop` closes nothing. `SessionEnd` closes the ending session's records and no other. A record without the new fields counts as closed. `hooks.json` has `TaskStop` in the `PreToolUse` matcher and a `SessionEnd` entry. |
| Plugin files | A read inside `CLAUDE_PLUGIN_ROOT` in a troy-mode project gets `allow`. Outside it, or in another project, nothing is printed. |
| Errors and log | An exception refuses a role's call and only warns for the main session. Each refusal writes one log line without the command text. |
| SessionStart | Unset `core.hooksPath` is set. Another value is left and reported. Missing hook files are reported. Old records are removed. |
| Log days (D219) | With no `[hooks]` table, a line 29 days old stays and one 31 days old is removed. With `log_days = 7`, a line an hour under 7 days old stays and one an hour over is removed; with `log_days = 1`, a line 2 days old is removed. A role record 2 days old is removed whatever `log_days` says, and one an hour old stays. An unreadable line is removed. Kept lines keep their order. An uncommitted edit of `log_days` is not read. `log_days` of 0, -1, `true`, 1.5, `"30"`, and an unknown `[hooks]` key are config errors for troy-check; 1 and 365 parse. With an invalid committed config, `SessionStart` exits 0, removes no log line, removes the old record, sets an unset `core.hooksPath`, and prints `additionalContext`. `config.default.toml` sets `log_days = 30`. |
| `hooks.json` | It parses. Its events, matchers, and timeouts are those of section 3, and its commands name existing scripts. |
| Git hooks | Real commits in a temporary repository with `core.hooksPath` set: a commit on `main` is refused, a good commit on a branch passes, an attribution trailer is refused, a wrong `--author` email is refused, a merge commit on `main` is refused. `pre-push` is run directly with lines on stdin: updating or deleting `refs/heads/main` is refused, a branch or a tag passes. No test runs `git push` to a `main` branch, not even in a scratch repository. |

### 13.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: the Developer's scope with the `tests` class, an unanchored role pattern, no ignore check, a temp folder test that accepts `/tmp-other`, `commit` in the allowed git commands, a scratch repository test that accepts the project, `pre-push` reading the local ref in place of the remote one, a role's call allowed on an exception, `SubagentStop` never blocking, `stop_hook_active` ignored, the config read from the working tree, and a plugin read allowed outside `CLAUDE_PLUGIN_ROOT`. D200's change adds: `comment` missing from the posting table, `-F` not read, the path scanned instead of the contents, and a missing file allowed. D219's change adds: the cutoff one day off, the default ignored (a day kept), role records kept for `log_days`, a `log_days` of 0 accepted, the config read from the working tree, and an invalid config stopping `SessionStart` before it turns on the git hooks. D223's change adds: `python3 -` missed, the `--` `-` form missed, `-i` inside a flag group missed, `-W` not skipping its value, `py -3.13` not skipped, `timeout` not unwrapped, `xargs` not exempt, the main session not checked, and the log line holding command text. D231 and D232's change adds: `backgroundTaskId` missed for `PowerShell`, a main-session command recorded, `background` kept without reading `background_tasks`, `stopped` set on a blocked stop, `SubagentStart` overwriting a stopped record, a stopped role's `Bash` allowed, change detection at a woken role's stop, `TaskStop` with an agent ID leaving the record open, a subagent's `TaskStop` closing a record, `SessionEnd` closing another session's records, a record without the new fields counted as open, and the command text in the `background` line. The counts go in the PR description.

### 13.3 Trial on a sample project

Before the F05 PR opens, the hooks run in nested `claude -p` sessions on a throwaway copy of F03's Python sample, with troy-pstack loaded from the PR branch through `--plugin-dir`, in `acceptEdits` mode, and with no Read rule for the plugin folder. `build_sample.py` gains the copy of `git-hooks/` into the sample, as troy-init will do. The main session writes each brief by hand:

1. **Probes.** The Developer gets a brief that lists actions to try and to report one by one: write a test file with Write, write one with a Bash heredoc, `git commit`, `gh pr comment`, write into the home folder, write into the temp folder, and read a plugin file. Expected: refused, blocked after the call, refused, refused, refused, allowed, allowed. At the end, `SubagentStop` keeps it working until the second test file is gone.
2. **Normal runs.** The Test Engineer's TE1 writes tests through Bash, and the Developer's DV2 runs the tests, with no block. The Test Manager's TM2 commits a scratch copy in the temp folder, with no block. The Code Reviewer's CR1 runs `/code-review` and `/security-review`, with no block. A probe asking for `/code-review --fix` is refused.
3. **Main session.** A commit on `main` is refused by `pre-commit`. A commit on a branch with a Claude trailer is refused by `commit-msg`. `git commit --no-verify` is refused. `gh pr create` on `main` is refused before it runs. A fresh clone gets `core.hooksPath` from `SessionStart`. No trial pushes `main`, even to a scratch repository. The unit tests cover `pre-push`.
4. **Outside troy-mode.** In a folder with no `.troy-mode/`, no hook prints anything.
5. **Facts.** The trial logs the `Skill` tool's input fields, whether a hook's `deny` holds in `acceptEdits` mode, and whether the `if` rule filters `Glob` and `Grep`. If a fact differs from this design, the design is updated in the same PR.
6. **Speed.** Each hook kind runs 20 times on Troy's PC. The medians go in the PR description and must be under 200 ms.

The trial takes about eight role runs. The sample copy is not committed.

**D231 and D232 (D234).** Before the build's PR opens, the hooks and the engine run in nested `claude -p` sessions of the bundled CLI on a throwaway copy of F03's Python sample. tstack loads from the PR branch through `--plugin-dir` with the installed plugin off, and `BASH_DEFAULT_TIMEOUT_MS` is 5 seconds, so that a role's test command moves to the background:

1. A Test Engineer run reports while its test command still runs. `check-run` gives the `running` problem with the agent ID. The main session's `TaskStop` of that ID ends the command, and `check-run` and `snapshot` then pass.
2. In a second run, the command ends on its own after the report. The woken role's calls are refused with rule `stopped`, and its record closes.
3. A third session exits while the command runs, and `SessionEnd` closes the record.
4. A role's `run_in_background` call is recorded like a timed-out one, or the design is updated in the same PR.

It takes about four role runs, under $5. Two facts only the desktop app shows: the notice that a role waits on its own background work, and whether auto mode lets the main session's `TaskStop` through. The first real run checks them.

### 13.4 Status

| When | F05's status in requirements 7.2 |
| --- | --- |
| The F05 PR merges after a passing trial | Runs on a sample project: the hooks blocked every probe in a trial on the Python sample, with roles started by hand. troy-mode (F07) does not start roles yet. |
| The pilot (F11) runs with the hooks | Used on a real project |

If the trial cannot run before the PR, the status is "Written" until it does. F05 ships in one PR: `hooks/hooks.json`, `troy-mode/hooks/`, `troy-mode/checks/git-hooks/`, the tests, the workflow change, and the `build_sample.py` change. The status update is its own PR.

## 14. Not in F05

- Copying the git hooks into projects and setting `core.hooksPath` at setup (F06).
- Checking `git status`, `HEAD`, and the branch after each role run, checking that the Architect changed only section 4, and running `troy-check code` after a commit (F07).
- Deciding whether a dependency change was approved (F07, with CI's R16 flag).
- R21's troy-check branch check in CI, which fails a PR whose head branch is `main` (a later change to F02).
- Limiting the main session's files to the Product Manager's scope (F07).

## 15. Decisions for Troy

D1 to D38 belong to the F01 to F04 designs, so F05 continues from D39.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D39 | How are the hooks built, and what happens when one fails? | A: Python 3.11 and the standard library, reusing troy-check's modules from the plugin. `hooks/hooks.json` in the plugin's standard folder. An error refuses a subagent's call and only warns for the main session (section 10). B: shell scripts only. C: errors always let the call go ahead, which is Claude Code's default. | A. It matches F02 D7, and the hooks then classify paths exactly as CI does. Failing closed for subagents keeps a crash from turning the scopes off, and the main session stays free to repair the project. |
| D40 | Which callers do the hooks limit? The F04 trial showed that `/code-review`'s fork reaches hooks as `general-purpose`, and Claude Code does not name a subagent's parent. | A: roles get their write scopes. Every other subagent in a troy-mode project is read-only. The main session is not limited in its files (section 4). B: only the six roles are limited, and other subagents are free. C: other subagents inherit the scope of the role that is running, tracked in a state file. | A. It covers `/code-review`'s fork without guessing its parent, and in troy-mode only the main session and the roles change files. Its cost: a subagent the main session starts for a write task in a troy-mode project is refused, and the main session does that task itself. C depends on start and stop events that can go missing. |
| D41 | How do the hooks see what a role changes through Bash? The F04 trial's Test Engineer and Developer wrote through Bash. | A: check Write and Edit before the call, and compare the working tree with the role's starting state after each shell or skill call and when it stops. The stop is blocked once until the role undoes the changes (section 6). B: read write targets out of each command, such as `>` and `cp`. C: Write and Edit only, with F07's check after the run as the backstop. | A. `git status` sees every change to the repository, however it was made. B misses most forms of writing, and C would leave the Developer's usual way of writing unchecked until the run ends. |
| D42 | Do paths outside the repository count as outside a write scope? The F04 trial's Test Manager made scratch copies in the temp folder. | A: allowed in the temp folder and the session's scratchpad, refused anywhere else (section 5.2). B: everything outside the repository is allowed. C: everything outside is refused. | A. Scratch copies keep working, and a role cannot change another project or Troy's settings through Write or Edit. C would stop the Test Manager from checking R09 against the mock. |
| D43 | What may subagents run in git and the GitHub CLI? | A: a list of read-only commands. Any git command in a scratch repository in the temp folder, except `push`. Only `code-review` and `security-review` among skills, without `--fix` or `--comment` (section 7). B: a list of refused commands, with everything else allowed. | A. A new git or `gh` subcommand is then refused until someone adds it, instead of allowed until someone notices. The scratch repository rule lets the Test Manager commit a copy to check R09. |
| D44 | How are R19 and R21 enforced for commits and pushes? Reading a commit message out of a shell command is unreliable. | A: git hooks in troy-check's folder (`commit-msg`, `pre-commit`, `pre-merge-commit`, `pre-push`), turned on by `core.hooksPath`, which troy-init sets and `SessionStart` repairs in a fresh clone. Claude Code hooks refuse `--no-verify` and `core.hooksPath` changes, and check `gh pr create` and `gh pr edit` for R19 and R21 (section 8). B: Claude Code hooks only, reading messages and branches out of the commands. | A. Git hands its hooks the exact message, author, and pushed refs, so nothing is guessed. They also cover Troy's own terminal commits in a troy-mode project, which R21 asks for. Troy can still skip them with `--no-verify`, and Claude cannot. |
| D45 | How do roles read the plugin's own files, such as `technical-writing/SKILL.md`, in a session where nobody can approve a prompt? The F04 trial's IF1 failed on this. | A: a `PreToolUse` hook allows `Read`, `Glob`, and `Grep` inside `CLAUDE_PLUGIN_ROOT` in troy-mode projects, so troy-init writes no permission (section 9). B: troy-init writes `Read(<plugin folder>/**)` into the project's `.claude/settings.local.json`. C: Troy adds `Read(~/.claude/plugins/**)` to the user settings once. | A. The plugin's folder changes with every version, so a written rule goes stale, and `settings.local.json` is missing in every new worktree and clone. The hook reads the current folder each time and grants reads only. |
| D46 | How is F05 checked, and when does its status move? | A: unit tests and planted bugs, plus a trial with probes on the Python sample before the PR opens (section 13). Status after merge: "Runs on a sample project". B: unit tests only, status "Written". | A. The trial settles the facts the documentation leaves open (the `Skill` input, `deny` in `acceptEdits` mode, the `if` rule for `Glob` and `Grep`) and measures the speed on Windows. It costs about eight role runs. |
| D200 | How is text that the main session posts to GitHub checked? A review comment on `ZJUCao/recipe-menu#92` was posted although `check-text` had failed on it, and GitHub keeps the history of every edit. From tstack issue #65, the rule proposal of recipe-menu's v0.1.0 retrospective. D161 to D199 are kept for F17 to F19, so this decision takes D200. | The levels the Architect weighed in the issue: the project's architecture; lint, troy-check, or a `project-rules.yml` job in CI; a Review or Process row; or F05's `PreToolUse` `gh` guard. And whether to widen R19 or add a new R row. | F05's `gh` guard, Hard, and R19 widened to PR comments and reviews, issues, and release notes, with no new R row. The guard checks the text of every `gh` command that posts it, for the main session, with `check-text`'s function and mode, and fails closed on text it cannot read and on check errors (sections 8.2 and 10). The hook is the only level that runs before the text leaves the machine, for every caller. The other levels read the repository or run in CI after GitHub already holds the text and its edit history, and a Review row in effect exists: #92 shows it followed in form and failed in effect. Approved by Troy on 2026-11-16 with the Architect's recommendations (AR6: A2, B1, C). |
| D219 | How long does `hooks.log` keep its lines? F08's retrospective and F11's report count hook blocks over a whole version, which took six days in the pilot, while `SessionStart` removed log lines older than a day. So the v0.1.0 retrospective of `ZJUCao/recipe-menu` could see at most the last day's lines, and a block that repeated across the version could not reach a rule proposal. From tstack issue #66. This batch gives F05 D219 to D222. | A: keep the lines for a number of days set in the config, `[hooks] log_days`, 30 by default, and keep removing role records after a day. B: keep the lines until the next version's tag. C: `check-run` copies each role run's log lines into the flow state, which `retro` reads. | A. The hook needs no tags or flow state, so `SessionStart` stays one file read and one config read. 30 days covers the pilot's six-day version with room to spare, and a project with longer versions raises the number. B would make the hook read tags and F08's release state. C would change F07's and F08's state, and would leave out the main session's blocks, which no role run holds. Role records stay at one day, because a record only matters while its role runs. A bad value is a config error, and an invalid config keeps every line (section 10). Approved by Troy on 2026-11-18 with the recommendation. |
| D223 | How is Python that reads its program from standard input stopped? An agent or the main session ran Python that way 168 times in `ZJUCao/recipe-menu`'s two session transcripts, and 39 of those runs hung at Python's prompt until the 120-second limit. The warning in every brief did not prevent it. From tstack issue #64, the rule proposal of recipe-menu's v0.1.0 retrospective. This batch gives F05 D223 to D230. | The levels the Architect weighed in the issue: the architecture, lint, CI, troy-check's limits, or `project-rules.yml`; permission deny rules; or F05's `PreToolUse` hook for every caller, with a new R row. And how much to refuse: every Python fed by a heredoc, a pipe, or `/dev/null`, as the retrospective's words read, or only Python whose program comes from standard input. | F05's hook, for every caller, with a new Hard row, R23, and the narrower reading: only `python -`, `python -i`, and Python with no script, `-c`, or `-m` are refused, whatever feeds standard input (section 8.3). A command leaves no trace in a commit or PR, so the architecture, lint, CI, and troy-check cannot see it, and deny rules match only a command's prefix: they miss full paths, `cd ... &&`, and wrappers, which make up most of the hangs. The hook sees each command before it starts, the level R08, R19, and R21 already use, and it checks the main session too, which caused 2 of the 7 time-outs in the session that built F11 to F13. The narrower reading refuses none of the 257 runs with a script, `-c`, or `-m` that read a pipe or `/dev/null` and finished, 237 of them the main session's reads of `troy_flow.py` output. `timeout` joins the wrappers of section 7.1, which also lets the git and `gh` checks see `timeout 60 git push`. Approved by Troy on 2026-11-16 with the Architect's recommendations (AR6: Q1 A, Q2 A, Q3 A) and the narrower reading. |
| D231 | How does troy-mode keep a command that a role leaves running from changing the tree during a later run? In the pilot, every such case was a role's command that Claude Code moved to the background at the Bash tool's 120-second limit. It ran on after the role's report, and the role could not stop it. In the desktop app, roles cannot run in the foreground (section 6.1). The issue's candidates were roles in the foreground or a stop before `check-run`, `snapshot` refusing while a role still runs, and roles stopping every process they start. From tstack issue #49. This batch takes D231 to D240: D231, D232, and D234 are F05's, and D233, on the role exam's U5, is F16's. | A: the entry skill only. When the notice says that a role waits on its own background work, the main session ends the role with `TaskStop` before `check-run`. B: A, and a check. The hooks record each role command that moved to the background and keep the role's record until the command ends or is stopped. `check-run` and `snapshot` refuse while a record is open, and name the agent ID to stop (section 6.1, F07 section 7). C: B, and roles end their own commands: the five roles that have Bash get `TaskStop`, and `SubagentStop` keeps a role working, once, until it stops them. D: turn Claude Code's background tasks off in troy-mode projects, with `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` in a settings file that troy-init writes, so that a command past its time limit is stopped and every role runs in the foreground. | B. Requirements 5.8 prefers a check to an instruction. On 2026-11-21 the main session read the notice and still left the task running, so A alone could repeat that. B uses the task IDs that Claude Code itself gives the hooks, so it needs no process list, which the classifier refused on Windows, and no guess about which agent started a command. Its one escape for a stale record is the same `TaskStop`. It changes no role's instructions, so its role exam affects no case and costs nothing. C would end a command earlier, but the main session's check is still needed for a role that does not, and C costs a role exam of ten cases with fresh base runs, $188.93, for no further safety. D is untried in the desktop app, changes every session in the project, Troy's own included, and rests on a setting of Claude Code's that may change. Approved by Troy on 2026-11-21 with the recommendation ("全按推荐"). |
| D232 | What do the hooks do with a role that Claude Code wakes after its report, when a command it left running ends or is stopped? On 2026-11-21, the `SubagentStart` hook took a fresh record of such a Test Manager while the Developer's edits were in the tree, and the `SubagentStop` hook then told it to `git restore` three of the Developer's files. From tstack issue #49. | A: treat the role as finished. Keep its stopped record, refuse its calls that can change anything with rule `stopped`, and skip change detection at its stop (section 6.1). B: keep today's behavior, a fresh record and change detection. C: as A, but refuse its reads too. | A. A stopped role's report is already delivered, and troy-mode never sends it a new message, so it has nothing left to do. Refusing its calls keeps it from changing the tree while another role runs, and skipping change detection keeps the hook from blaming the other role's work on it. B leaves the hazard of 2026-11-21, where one `git restore` would have destroyed live work. Reads change nothing, so C would only add refusals. Approved by Troy on 2026-11-21 with the recommendation ("全按推荐"). |
| D234 | How is the change of D231 and D232 checked, and when does its status move? From tstack issue #49. | A: tests from this design by a separate agent, planted bugs, and a trial in nested `claude -p` sessions on a copy of F03's Python sample (section 13.3), about four role runs and under $5. The statuses of F05 and F07 call the change "Runs on a sample project" after the trial, and "Used on a real project" once a real run has ended a leftover command. B: tests and planted bugs only, with the status "Written" until a real run. | A. The probes ran in a scratch project with a probe plugin, not with tstack's hooks and a real role. The trial checks that the two fit, and that a `run_in_background` call reports its task as a timed-out command does. Approved by Troy on 2026-11-21 with the recommendation ("全按推荐"). |

Requirements 1.15 records the approved change: the F05 row describes the hooks as sections 4 to 9 build them, including the git hooks, read-only subagents, the check after shell calls, and plugin reads. Requirements 1.46 records D200: R19 in section 6 and the F05 row. D219 changes no requirement text: the F05 row says that a local log records each block, which still holds, and only its status names issue #66. Requirements 1.50 records D223: the new row R23 in section 6, and the F05 row.

Requirements 1.52 records D231 and D232 in two rows of section 7.2:

- The F05 row gains, after its sentence on R23: "They record each command that a role leaves running in the background, so that troy-mode ends it before the next run, and refuse every call of a role that has already stopped (D231, D232)."
- The F07 row's "checks after each run that the role changed only files in its write scope (D31)" gains ", and that nothing the role started still runs, which it then ends (F05 design D231)".

No R row changes: the check belongs to troy-mode's own check after each run (F07 design D59), which no R row names either. D234 and F16's D233 change no requirement text.

## 16. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-06 | First draft. |
| 1.0 | 2026-11-06 | Approved by Troy with D39 to D46, every recommended answer. |
| 1.1 | 2026-11-07 | Facts from the trial of section 13.3: the `if` rule filters only `Read`, so `Glob` and `Grep` get their own entry without it (sections 3, 9, and 10). Claude Code's own permissions refuse `Write` outside the project in a session nobody can approve, so roles make scratch copies with Bash (section 5.2). The trial's Test Manager named its scratch folder with a `mktemp -d` variable, so section 7.1 also follows variables set to a literal path or to `mktemp -d` earlier in the same command (sections 7.1 and 7.2). The `Skill` input fields (section 7.4). The measured medians (section 10). |
| 1.2 | 2026-11-17 | D200, from tstack issue #65, approved by Troy on 2026-11-16: the main session's `gh` commands that post text are checked before they run, and fail closed (sections 1, 8.2, 10, 11, 13.1, 13.2, and 15). |
| 1.3 | 2026-11-18 | D219, from tstack issue #66, approved by Troy on 2026-11-18: `hooks.log` keeps its lines for `[hooks] log_days` days, 30 by default, and role records are still removed after a day (sections 1, 3, 10, 13.1, 13.2, and 15). Section 15's table no longer breaks before D200. |
| 1.4 | 2026-11-20 | D223, from tstack issue #64, approved by Troy on 2026-11-16: every caller's Python that reads its program from standard input is refused before it starts, as the new rule R23, and `timeout` joins the wrappers that section 7.1 removes, with a mark for commands that come through `xargs` (sections 1, 3, 7.1, 8, 8.3, 10, 11, 13.1, 13.2, and 15). |
| 1.5 | 2026-11-21 | D231, D232, and D234, from tstack issue #49, approved by Troy on 2026-11-21 ("全按推荐"): the pilot's leftover work was a role's command that Claude Code moved to the background, not a hung role. The hooks record such commands, keep a role's record until its work ends, close it at the main session's `TaskStop` and at `SessionEnd`, and refuse every call of a role that has already stopped. Facts from the pilot's transcripts and from probes with CLI 2.1.328 (sections 1, 3, 6, 6.1, 10, 11, 12, 13.1, 13.2, 13.3, and 15). |
| 1.6 | 2026-11-22 | F20's design (D268 to D279, approved by Troy on 2026-11-22): the hooks learn a role's team from its brief, run its commands in the team's worktree, keep its record and log lines in that worktree's git folder, lock log appends and record updates, refuse the main session's writes in a team's worktree while one of its roles runs (rule `team-busy`), and take the shared documents out of a team's write scopes; `SubagentStart` no longer writes a role's record (sections 3, 4, 5, 6, 6.1, and 10). The changes land with F20's build. |
