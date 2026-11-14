# F13 design: mode guard

| | |
| --- | --- |
| Feature | F13 in [requirements 1.33](../requirements.md#72-feature-list) |
| Version | 1.0 |
| Date | 2026-11-14 |
| Status | Approved by Troy on 2026-11-14, with D121 to D126. |
| Source of truth | This English file. [`F13-mode-guard.zh-CN.md`](F13-mode-guard.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F13 keeps poteto-mode out of troy-mode projects. Requirements 3.2 says to choose the mode by project: troy-mode in a troy-mode project, poteto-mode elsewhere. F13 makes that choice hold when Troy types the wrong command. It delivers:

1. **One hook entry** in the plugin's `hooks/hooks.json`. In a project with a `.troy-mode/` folder, it refuses `/poteto-mode` and `/no-comments`, typed with or without the plugin prefix, before the skill's text reaches Claude. Troy sees a message that says to use `/troy-pstack:troy-mode` instead (sections 3 to 7).
2. **Tests** for the hook, and the updates to F05's `hooks.json` test (section 11).
3. **One sentence** under the README's "troy-mode or poteto-mode" table, and one row in the guide's problems table in English and Chinese (section 9).

**Why.** In a troy-mode project, poteto-mode clashes with troy-mode in five ways:

1. Its `poteto-agent` delegates write code, and F05's hooks refuse their writes, because only the six roles may write there (F05 D40).
2. The main session would write code itself, around the role reviews and R08.
3. `/no-comments` starts the `comment-sicko` agent, which deletes doc comments that R05 requires.
4. Its PRs mix stages, which breaks R01 and R02.
5. Its shipping and autopilot playbooks merge design PRs that Troy must approve (R18).

CI catches the PR rules whichever mode made the change (requirements 3.2), but only after the work is done. The guard stops it before any work starts.

F13 changes no upstream file: `poteto-mode`, `no-comments`, `poteto-agent`, and `comment-sicko` stay as they are (requirements section 8). Outside troy-mode projects, troy-pstack itself included, both commands work as before.

The facts about Claude Code in this design come from its hooks and skills documentation on 2026-11-14 and from the trial in section 3.2, run with Claude Code 2.1.321, the version the desktop app bundles.

## 2. Location

```text
hooks/
  hooks.json                  gains a UserPromptExpansion entry (section 7.1)
troy-mode/
  hooks/
    troyhook/
      events.py               gains the UserPromptExpansion handler (section 7.2)
      modeguard.py            the guarded names and the message (sections 4 and 6)
    tests/
      test_mode_guard.py      unit tests (section 11.1)
      test_hooks_json.py      updated for the new entry (section 9)
README.md                     one sentence in "troy-mode or poteto-mode" (section 9)
docs/troy-mode/guide/
  08-reference.md             one row in "Problems", and its Chinese mirror (section 9)
.claude-plugin/
  plugin.json                 the next minor version (section 7.4)
```

`hooks.json` and the event name are fixed by Claude Code. `modeguard.py` sits inside `troyhook`, whose module names do not start with `troy-` (F05 section 2).

## 3. The mechanism

### 3.1 What Claude Code offers

Two hook events see a command that Troy types:

| Event | When it runs | What it gets | Matcher |
| --- | --- | --- | --- |
| `UserPromptSubmit` | For every prompt, before Claude sees it. Also for scheduled tasks, background subagent reports, and messages from other sessions. | `prompt`: the line as typed, for example `/poteto-mode build X`. | None. It runs for every prompt. |
| `UserPromptExpansion` | When a typed command expands into a skill's or command's text, before it reaches Claude. | `command_name`, `command_args`, `command_source`, `expansion_type`, and `prompt`. | On `command_name`. |

- Either event blocks with `{"decision": "block", "reason": "..."}` on stdout, or with exit code 2 and the reason on stderr. The prompt then never reaches Claude, and Troy sees the reason.
- A typed `/skill` does not run a `PreToolUse` hook for the `Skill` tool. That hook runs only when Claude itself calls the tool.
- `poteto-mode` and `no-comments` both set `disable-model-invocation: true`, so Claude cannot start them through the `Skill` tool. Only Troy can, by typing them.

### 3.2 The trial

On 2026-11-14 a scratch probe plugin logged every `UserPromptSubmit`, `UserPromptExpansion`, and `PreToolUse` input for `Skill` and `Agent`, and blocked the two commands when a mode file said so. Nested `claude -p` sessions loaded it next to troy-pstack from this branch (`--plugin-dir`), on haiku with one turn. Two scratch git repositories in the session's scratchpad served as projects: one with a `.troy-mode/` folder and one without. No GitHub repository was touched.

| Run | Troy types | Project | Probe | What happened |
| --- | --- | --- | --- | --- |
| 1 | `/no-comments` | troy-mode | Logs only | `UserPromptSubmit` got `prompt` `/no-comments`. `UserPromptExpansion` got `command_name` `troy-pstack:no-comments`, `command_source` `plugin`, `command_args` empty, and `prompt` `/troy-pstack:no-comments`. Then the skill ran. |
| 2 | `/no-comments` | troy-mode | `UserPromptExpansion` blocks with JSON | Blocked. No turn ran and the cost was 0. The message was shown (section 6). |
| 3 | `/troy-pstack:no-comments` | troy-mode | As run 2 | Blocked, the same way. |
| 4 | `/poteto-mode build the export feature` | troy-mode | As run 2 | `command_name` `troy-pstack:poteto-mode`, `command_args` `build the export feature`. Blocked. |
| 5 | `/troy-pstack:poteto-mode build the export feature` | troy-mode | `UserPromptExpansion` blocks with exit code 2 | Blocked, but the message also showed the hook's command line and "This hook comes from the f13-probe@inline plugin." |
| 6 | `/poteto-mode build the export feature` | troy-mode | `UserPromptSubmit` blocks with JSON | Blocked. The result said `prompt_kept: false`. |
| 7 | `/poteto-mode build the export feature`, sent as stream-json input, the way the desktop app talks to the CLI | troy-mode | As run 2 | Blocked, the same way as run 4. |
| 8 | `/poteto-mode say hi in two words` | Not troy-mode | As run 2 | Not blocked. The skill ran. |
| 9 | `/troy-pstack:bro hello there` | troy-mode | As run 2, with the matcher of section 7.1 | The `UserPromptExpansion` hook did not start. The skill ran. |
| 10 | `/troy-pstack:troy-mode status` | troy-mode | As run 9 | The hook did not start. troy-mode ran. |
| 11 | `/POTETO-MODE hi` | troy-mode | As run 2 | Not a command, so nothing expanded. Claude got the text and ran no skill. |
| 12 | `   /poteto-mode hi`, with leading spaces | troy-mode | As run 2 | Not a command either. Claude searched for poteto-mode's `SKILL.md` on its own. |
| 13 | "Load the poteto-mode skill with the Skill tool, then say hi." | troy-mode | Logs only | Claude called `Skill` with `poteto-mode`. Claude Code refused the call for `disable-model-invocation` before any `PreToolUse` hook started. |

So:

- **It fires, and it sees the command.** `UserPromptExpansion` runs for both commands, with and without the prefix, and gives the full name `troy-pstack:<name>` whichever form Troy typed.
- **It blocks, and Troy sees why.** A blocked command costs nothing, because no turn runs. JSON gives a clean message; exit code 2 adds the hook's command line to it.
- **The matcher filters.** The hook starts only for the two commands. Other commands, troy-mode's own included, and plain prompts do not start it.
- **The desktop app's path works.** Stream-json input behaves the same as `-p` text.

One trap for later trials: Git Bash rewrote the argument `/no-comments` into `D:/Program Files/Git/no-comments` before `claude.exe` saw it. The trial script sets `MSYS_NO_PATHCONV=1`.

### 3.3 The choice (D121)

The guard is a `UserPromptExpansion` hook with a matcher on `command_name`:

- It sees the resolved command, so it needs no parsing of what Troy typed, and a bare name and a prefixed name look the same.
- Its matcher keeps it from starting for anything else. Every other prompt and command, in every project, pays nothing.
- `UserPromptSubmit` would start Python for every prompt in every project, about 77 ms each (section 7.3). It would read text, so it would also have to tell a command from a message from another session that quotes one.

A skill's own instructions cannot do this job: the skills are upstream and stay unedited.

## 4. The list (D122)

| Command | Why it is on the list |
| --- | --- |
| `poteto-mode` | The five clashes of section 1. |
| `no-comments` | Clash 3: it deletes doc comments that R05 requires. poteto-mode runs it before every review. |

The matcher accepts any plugin prefix or none: `^([^:]+:)?(poteto-mode|no-comments)$`. So it keeps working after F19 renames the plugin to `tstack`, and it also covers a copy of upstream pstack or a personal skill with the same name.

**Not on the list:**

- **Other pstack skills**, such as `arena`, `swarm`, `tdd`, `figure-it-out`, `how`, `why`, and `interrogate`. They are tools rather than a way of working. troy-mode borrows some of them (requirements 4.1, F17), and none merges PRs. Where they start a writing subagent, F05's hooks already make it read-only (D40).
- **The agents `poteto-agent` and `comment-sicko`.** Claude could start them without the commands, but in a troy-mode project F05 D40 already refuses every write by a subagent that is not a role. A refusal at their start would only give an earlier message.
- **Built-in commands** such as `/simplify` and `/code-review`. They are Claude Code's own, and troy-mode's Code Reviewer runs `/code-review`.

## 5. Refuse, with no override (D123)

The guard refuses. It does not warn and let the command run, because then poteto-mode's instructions would still drive the session, and all five clashes would happen anyway.

It has no override, not even on a throwaway experiment branch (requirements 5.9):

- Requirements 3.2 already routes questions and experiments in a troy-mode project to troy-mode's light path, which opens no PR.
- An override in F13 alone would not make poteto-mode work in the project. F05's hooks would still refuse every write by `poteto-agent`, so poteto-mode would half-work.
- To try poteto-mode on an idea, Troy works in a folder that is not a troy-mode project, for example a scratch copy of the code without `.troy-mode/`.

## 6. The message (D124)

The reason names the command as Claude Code resolved it, gives the clash in one clause, and points to `/troy-pstack:troy-mode`. It has an English line and a Chinese line, because the hook cannot know which language Troy is using, and only Troy reads it.

For `poteto-mode`:

```text
troy-mode: /troy-pstack:poteto-mode is off here. This project uses troy-mode (it has a .troy-mode folder), and poteto-mode's way of working breaks troy-mode's rules: only troy-mode's roles write code, each PR holds one stage, and Troy approves the designs. Type /troy-pstack:troy-mode and your request instead. It also handles questions and experiments, which open no PR.
troy-mode：这里停用 /troy-pstack:poteto-mode。本项目使用 troy-mode（有 .troy-mode 文件夹），而 poteto-mode 的工作方式会破坏 troy-mode 的规则：只有 troy-mode 的角色写代码，每个 PR 只放一个阶段，设计要 Troy 批准。请改用 /troy-pstack:troy-mode 加上你的请求。提问和试验也用它，不开 PR。
```

For `no-comments`, the clash after "and" is "/no-comments deletes doc comments that troy-mode's rule R05 requires", and in Chinese "而 /no-comments 会删除 troy-mode 规则 R05 要求的文档注释". The rest is the same.

Claude Code puts its own line above the reason and the typed command below it. The trial showed it like this, here with the reason shortened:

```text
UserPromptExpansion operation blocked by hook:
troy-mode: /troy-pstack:poteto-mode is off here. ...
troy-mode：这里停用 /troy-pstack:poteto-mode。...

Original prompt: /troy-pstack:poteto-mode build the export feature
```

The command's name in the message is `command_name` with a `/` in front. The name in "Type ... instead" comes from `troyhook`'s plugin prefix constant, so F19's rename changes it with the rest of the hooks.

## 7. How it is built (D125)

### 7.1 The `hooks.json` entry

`hooks/hooks.json` gains a sixth event:

```json
"UserPromptExpansion": [
  {
    "matcher": "^([^:]+:)?(poteto-mode|no-comments)$",
    "hooks": [
      {
        "type": "command",
        "shell": "bash",
        "command": "<the same interpreter pick as the other entries> ... troy_hook.py UserPromptExpansion",
        "timeout": 10
      }
    ]
  }
]
```

- The command is the other entries' command with the event name changed, so the interpreter pick, `TROY_MODE_PYTHON`, and the missing-Python rule stay the same (F05 section 10).
- The matcher is a regular expression on `command_name`, anchored at both ends, so `troy-pstack:no-comments-extra` or `my-poteto-mode` does not match.
- `"timeout": 10`, like every other entry.
- The `description` field names F13 next to F05.

### 7.2 The handler

`troyhook/events.py` gains `user_prompt_expansion` in its handler table, and `troyhook/modeguard.py` holds the guarded names, the two clauses, and the message:

1. **The gate.** `main()` already finds the project from the input's `cwd` (F05 section 4). Outside a troy-mode project, the hook exits with code 0 and prints nothing, and the command runs.
2. **The check.** The handler reads `command_name`, drops the part before the first `:` when there is one, and compares the rest with `poteto-mode` and `no-comments`. It checks again although the matcher already filtered, so a mistake in the matcher cannot block another command, and the tests can feed it inputs directly. Anything else returns nothing.
3. **The refusal.** For a guarded name, it prints `{"decision": "block", "reason": <message>}` and exits with code 0. JSON, not exit code 2, because exit code 2 adds the hook's command line to what Troy sees (section 3.2, run 5).

**Errors.** The caller is always the main session, so F05 D39's rule for the main session applies: an error inside the hook prints a notice on stderr and exits with code 1, which Claude Code treats as a non-blocking error, and the command runs. When no Python 3.11 or newer exists, the `hooks.json` command exits with code 2 in a troy-mode project, as every F05 entry does, so the command is blocked with the "no Python" message. Either way, nothing outside troy-mode projects is blocked.

**No log line.** The guard writes nothing to `hooks.log` (F05 section 10). Troy sees the refusal on screen. F07's check after a run counts main-session lines as the Product Manager's, and F08's retrospective counts every line, so a line here would show up as a mistake of troy-mode's own.

### 7.3 Speed

The hook starts only when Troy types one of the two commands. The trial timed the `hooks.json` command form, through Git Bash, Python, the `troyhook` imports, and the gate, 20 times per project on Troy's PC: median 77 ms, at most 85 ms, in a troy-mode project and outside one. That is under the 200 ms target of requirements section 8. Every other prompt pays 0 ms.

### 7.4 Plugin version

F13 changes what projects get, so its PR raises the plugin's minor version (F10 design section 6): 0.2.0 becomes 0.3.0, or the next free minor version if F12's or F14's build raised it first. The pilot gets the guard whenever Troy next updates the plugin. It needs no pause: troy-mode never types the two commands.

## 8. What the guard can and cannot catch

It catches Troy typing `/poteto-mode` or `/no-comments`, with or without a prefix, from the CLI or the desktop app, in any folder of a troy-mode project, a worktree included.

It does not catch:

- **Text that is not a command.** A line with spaces before the `/`, or "work in poteto style" in a sentence, expands nothing. Claude cannot load either skill itself (run 13), but it can read the skill's file and imitate it, as run 12 began to do. F05's hooks still refuse every write by `poteto-agent` and `comment-sicko`, and CI still enforces R01, R02, R05, and R19.
- **A project without `.troy-mode/`.** That is the design: there poteto-mode is the right choice (requirements 3.2).

## 9. Changes to earlier features

- **F05.** `hooks.json` gains the entry of section 7.1. `test_hooks_json.py` expects six events, with the `UserPromptExpansion` matcher of section 7.1. F05's design stays as approved; this design records the new entry.
- **F10.** The README's "troy-mode or poteto-mode" table gains one sentence below it: "In a troy-mode project, a hook refuses `/poteto-mode` and `/no-comments` and points to troy-mode (F13)." The guide's `08-reference.md` gains a row in "Problems": "`/poteto-mode` or `/no-comments` was refused", with "Use `/troy-pstack:troy-mode <request>`; to try poteto-mode, use a folder that is not a troy-mode project." Its Chinese mirror gains the same row.
- **F19.** The rename changes `troyhook`'s plugin prefix constant, which the message uses. The matcher needs no change.
- **F16.** troy-mode reads poteto-mode's `eval` and `hillclimb` playbooks as files (requirements 4.1). The guard refuses only the typed commands, so F16 is not affected.

## 10. How F13 maps to the requirements

| Requirement | Where F13 covers it |
| --- | --- |
| F13 row: a hook refuses `/poteto-mode` and `/no-comments` typed by Troy | Sections 3.3, 4, and 7 |
| F13 row: it says to use troy-mode instead | Section 6 |
| F13 row: first check that a hook can see a typed slash command | Section 3.2 |
| 3.2: troy-mode in a troy-mode project, poteto-mode elsewhere | Sections 5 and 8 |
| Section 8: hooks exit at once outside troy-mode projects | Sections 3.3 and 7.2 |
| Section 8: under 200 ms per call | Section 7.3 |
| Section 8 and section 9: no upstream file edited | Sections 1 and 3.3 |

## 11. How F13 is checked (D126)

### 11.1 Tests

A separate agent writes `test_mode_guard.py` from this design before the handler exists, with `unittest` and the helpers of F05's tests: a temporary git repository and a hook input on stdin. `troy-checks-tests.yml` already runs the hooks suite on Linux and Windows for every PR that changes `hooks/` or `troy-mode/hooks/`.

| Group | Cases include |
| --- | --- |
| Refused | `troy-pstack:poteto-mode` and `troy-pstack:no-comments`, with and without `command_args`, in the project root, a subfolder, and a worktree: JSON with `decision` `block`, exit code 0. `tstack:poteto-mode`, `pstack:no-comments`, and a bare `poteto-mode` are refused too. |
| Message | Names the command with a `/`, holds the clause for that command, points to `/troy-pstack:troy-mode`, and has the English and the Chinese line. |
| Let through | No `.troy-mode/`: exit 0, nothing printed. Not a git repository. `troy-pstack:troy-mode`, `troy-pstack:bro`, `troy-pstack:poteto-help`, `troy-pstack:poteto-mode-extra`, `troy-pstack:no-comment`, and an empty or missing `command_name`. |
| Errors | An exception in the handler prints a notice on stderr, exits with code 1, and prints nothing on stdout. Input that is not JSON exits 1. |
| No log | A refusal leaves `hooks.log` unchanged. |
| `hooks.json` | Six events. The `UserPromptExpansion` group has the matcher of section 7.1, timeout 10, no `if` rule, and a command that names `troy_hook.py UserPromptExpansion`. The matcher, compiled as a regular expression, matches each refused name and none of the let-through names. |

### 11.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail: the gate skipped, an unanchored match, the prefix kept so a bare name passes, `no-comments` left out, exit code 2 in place of JSON, the error path blocking, a log line written, and a matcher without `^`. The counts go in the PR description.

### 11.3 Trial

Before the F13 PR opens, the trial of section 3.2 runs again with the built hook in place of the probe: troy-pstack loaded from the PR branch with `--plugin-dir`, in the same two scratch repositories, with `MSYS_NO_PATHCONV=1`. Expected: runs 2 to 4 and 7 are refused with the message of section 6, and runs 8 to 10 are not. The `hooks.json` command is timed 20 times per project, and the medians go in the PR description. No GitHub repository is needed.

### 11.4 Status

| When | F13's status in requirements 7.2 |
| --- | --- |
| The F13 PR merges after a passing trial | Runs on a sample project: in a trial on a scratch project, the hook refused `/poteto-mode` and `/no-comments`, with and without the prefix, and let other commands and other projects through. |
| A real project runs with that plugin version | Used on a real project: the hook was on in every session of the project. The status says how many commands it refused, none included. |

The status update is its own PR.

## 12. Not in F13

- Changing `poteto-mode`, `no-comments`, `poteto-agent`, `comment-sicko`, or `poteto-help` (requirements section 9).
- Refusing the two agents at their start, or other pstack skills (section 4).
- An override for experiments (section 5).
- Catching text that imitates poteto-mode without the command (section 8).
- The plugin rename (F19).

## 13. Decisions for Troy

D101 to D120 and D131 onward belong to the F12 and F14 designs, which are written at the same time, so F13 uses D121 to D130. Troy accepted every recommended answer on 2026-11-14.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D121 | How does the hook see a command Troy types? | A: a `UserPromptExpansion` hook with a matcher on `command_name`, which the trial proved (sections 3.2 and 3.3). B: a `UserPromptSubmit` hook that reads the typed text. C: no hook, only a note in troy-mode's documents. | A. It gets the resolved name whichever form Troy typed, and it starts only for the two commands, so nothing else pays for it. B starts Python for every prompt in every project and has to parse text. C relies on memory, which troy-mode exists to avoid. |
| D122 | Which commands are refused? | A: `poteto-mode` and `no-comments` only, from any plugin or none (section 4). B: as A, plus other pstack skills such as `arena`, `swarm`, and `tdd`. C: as A, plus refusing the agents `poteto-agent` and `comment-sicko` when Claude starts them. | A. These two carry poteto-mode's way of working. The other skills are tools that troy-mode borrows or could borrow, and F05 already makes the two agents read-only in a troy-mode project. Any prefix keeps the guard working after the rename to `tstack`. |
| D123 | Refuse or warn, and is there an override? | A: refuse, with no override (section 5). B: refuse, but allow on branches named `experiment/*`. C: warn and let the command run. | A. troy-mode already handles experiments without a PR (requirements 3.2). With B or C, F05's hooks would still refuse poteto-agent's writes, so poteto-mode would half-work. For a real poteto-mode experiment, Troy uses a folder that is not a troy-mode project. |
| D124 | What does the message say, and in which language? | A: the text of section 6: the command, the clash in one clause, and `/troy-pstack:troy-mode`, in English and Chinese. B: the same in English only, like F05's messages. | A. Only Troy reads it, and the hook cannot know which language Troy is using. Two lines cost nothing. |
| D125 | How is it built? | A: one `UserPromptExpansion` entry in `hooks/hooks.json` that runs `troy_hook.py`, a small `troyhook/modeguard.py`, F05's gate and error rule, JSON output, and no `hooks.log` line (section 7). B: as A, plus a `hooks.log` line for each refusal. C: a separate script with its own gate. | A. It reuses F05's interpreter pick, gate, errors, and tests. A log line would make F07's check after a run and F08's retrospective count Troy's own command as troy-mode's mistake. C would duplicate the gate. |
| D126 | How is F13 checked, and when does its status move? | A: unit tests from this design by a separate agent, planted bugs, and this design's trial again with the built hook (section 11). Status after merge: "Runs on a sample project". B: unit tests only, status "Written". | A. The trial costs a few cents, needs no GitHub repository, and proves the built hook as this design's trial proved the probe. |

Requirements 1.33 records the approved changes:

- The F13 row says what F13 builds: the `UserPromptExpansion` hook (D121), the two commands from any plugin prefix (D122), refusal with no override (D123), the message in English and Chinese (D124), the build on F05's hook with no `hooks.log` line (D125), and the checks (D126).
- Section 3.2 says that the guard refuses the two commands with or without a plugin prefix (D122), and that it has no override, so a poteto-mode experiment needs a folder that is not a troy-mode project (D123).
- Section 5.9 says that a throwaway branch does not turn the guard off (D123).

## 14. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-14 | First draft, with the trial of section 3.2. |
| 1.0 | 2026-11-14 | Approved by Troy with D121 to D126, every recommended answer. |
