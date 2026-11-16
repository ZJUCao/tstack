# F19 design: rename to tstack

| | |
| --- | --- |
| Feature | F19 in [requirements 1.40](../requirements.md#72-feature-list) |
| Version | 1.0 |
| Date | 2026-11-16 |
| Status | Approved by Troy on 2026-11-16, with D191 to D199. |
| Source of truth | This English file. [`F19-rename.zh-CN.md`](F19-rename.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F19 renames the plugin `troy-pstack` to `tstack`, Troy's own stack, as Lauren Tan's `pstack` is named after poteto (requirements F19 row, Q4, and change log 1.32). It delivers:

1. **One build PR** that changes every living mention of the name: the plugin's identity, the prefix of its commands and agents, the hook matchers, the files troy-init writes into projects, the documents, the tests, and CI (sections 4 and 5).
2. **A name check** in CI that keeps the old name out of living text (section 11.2).
3. **The steps outside the repository**, in order: the GitHub repository, a new local folder, the marketplace, Troy's installed plugin, the mamba environment, and the existing projects (sections 6 to 8).

Commands become `/tstack:troy-mode` and `/tstack:troy-init`. The names inside stay: skills, agents after the prefix, the marker folder `.troy-mode/`, the plugin's folders, troy-check, troy-init, and the engine (section 4.2). The README and the plugin descriptions say that most skills come from Lauren Tan's pstack under its MIT license, and that troy-mode is Troy's own work (section 4.3).

The facts in this design come from the repository at `3a14119` (plugin 0.5.0, requirements 1.38), from Troy's PC on 2026-11-16, and from the probes of section 3, run with Claude Code 2.1.325, the version the desktop app bundles.

## 2. Where the name is today

### 2.1 In the repository

`git grep -i -E "troy[-_ ]?pstack"` at `3a14119` finds 931 mentions on 749 lines in 157 of the 561 tracked files. Every one is spelled `troy-pstack`; there is no `troy_pstack` or `troy pstack`.

| Kind | Lines | Files | Where | What F19 does |
| --- | --- | --- | --- | --- |
| Plugin identity | 6 | 3 | `.claude-plugin/plugin.json` (name and a keyword), `.claude-plugin/marketplace.json` (the marketplace's name, its description, and the plugin's name), `LICENSE` (the line for Troy's modifications) | New names and credit (sections 4.1 and 4.3) |
| Model rule | 15 | 11 | `~/.claude/rules/troy-pstack-models.md`, named in `setup-pstack`, eight other skills, the README, the upstream guide, and the adapter | `tstack-models.md` (section 4.1) |
| npm scope | 3 | 3 | `@troy-pstack/poteto-mode-tools` and `@troy-pstack/statechart` in two `package.json` files and `bun.lock` | `@tstack/...` |
| Hook matchers and paths | 3 | 1 | `hooks/hooks.json`: two `^troy-pstack:troy-` matchers and the Read rule `Read(//**/troy-pstack/**)` | Section 5.2 |
| Agent names in code | 4 | 3 | `troyhook/scopes.py` (`PLUGIN_PREFIX`, `ROLE_PATTERN`), `troyflow/brief.py` (`subagent_type`), `troyflow/runs.py` (the `hooks.log` match) | One constant per package (section 5.1) |
| Files written into projects | 6 | 5 | The plugin's sources of `.troy-mode/checks/troy_check.py`, `.github/workflows/troy-mode.yml`, `.troy-mode/config.toml`, the Python pack's `pyproject.toml`, and troy-init's change-log line in `docs/rules.md` | New text; projects get it by upgrade (section 8) |
| Code comments and messages | 39 | 19 | Docstrings and messages in troy-init, the engine, the hooks, and the dev tools | New name |
| Command and agent names in text | 107 | 29 | `/troy-pstack:<skill>` and `troy-pstack:<agent>` in the README, both guides, `skills/troy-init`, `skills/poteto-help`, and the adapter | `/tstack:` and `tstack:` |
| Other living text | 153 | 54 | The README, the upstream guide `docs/guide/`, the adapter, troy-mode's guide, skill and playbook text, the roles' shared rules and their six copies in `agents/`, the pack READMEs, and the samples | New name (section 5.3) |
| Requirements | 50 | 2 | Living sections, the header's Status row, and the change log | Living text changes, history stays (section 9) |
| Approved designs | 268 | 28 | F01 to F14, in both languages | Stay (section 9) |
| Tests | 82 | 20 | Hooks 56, engine 19, dev tools 4, troy-init 2, troy-check 1 | Section 11.1 |
| CI | 10 | 3 | `troy-python-sample.yml` and `troy-cpp-sample.yml` check the plugin out into a folder `troy-pstack`; `troy-docs.yml` names it in a comment and a step | Section 5.4 |
| mamba env | 3 | 1 | `troy-mode/dev/environment.yml`: `name: troy-pstack` and its comments | Section 6.4 |

### 2.2 Outside the repository

| Place | What names troy-pstack | Section |
| --- | --- | --- |
| GitHub | The private repository `ZJUCao/troy-pstack`, described as "Personal fork of Lauren Tan's pstack (MIT)", with PRs up to #62. No branch protection, and auto-merge is off. | 6.1 |
| Local folder | `D:\Troy\Projects\troy-pstack`: the main checkout on `main`, 9 worktrees in `.claude/worktrees/`, and the git-ignored `.claude/settings.local.json` with Troy's permission rules and the standing trial permission, whose text names troy-pstack. | 6.2 |
| Marketplace | `~/.claude/plugins/known_marketplaces.json` and `extraKnownMarketplaces` in `~/.claude/settings.json`: a `directory` source `troy-pstack` at that folder. | 6.3 |
| Installed plugin | `troy-pstack@troy-pstack` 0.5.0 at user scope, in `~/.claude/plugins/installed_plugins.json` and `enabledPlugins`, with cache folders `~/.claude/plugins/cache/troy-pstack/troy-pstack/0.2.0` and `0.5.0`. | 7 |
| Project memory | `C:\Users\Troy\.claude\projects\D--Troy-Projects-troy-pstack\memory`, keyed by the folder's path. Its notes name the folder, the plugin, and the env. | 6.2 |
| mamba env | `D:\miniforge3\envs\troy-pstack` (F03 design D26). | 6.4 |
| Model rule | `~/.claude/rules/` does not exist: `/setup-pstack` has never run, so no rule file moves. | 4.1 |
| Notes and sessions | The side-session notes, session briefs, and desktop sessions whose folders are worktrees of that folder. | 6.2 |

### 2.3 In projects

A code search on `ZJUCao/recipe-menu` and on `ZJUCao/troy-mode-trial` finds the same six files in each:

| File | What it says | Who owns it | What upgrade does today |
| --- | --- | --- | --- |
| `.troy-mode/checks/troy_check.py` | "See docs/troy-mode/design/F02-checks.md in troy-pstack" | troy-init | Replaces it when nobody edited it |
| `.github/workflows/troy-mode.yml` | "Design: ... in troy-pstack." | troy-init | Replaces it when nobody edited it |
| `.troy-mode/config.toml` | "# Set by the language pack (troy-mode/lang/ in troy-pstack), for example:" | The project | Never edits it; lists differences (F06 design D54) |
| `pyproject.toml` | "# troy-check is checked in troy-pstack, not in the project." | The project | Never edits it; lists differences |
| `docs/rules.md` | The change-log row "troy-mode's rules brought up to troy-pstack 0.5.0." | troy-init writes its rows | Adds a row |
| `docs/rules.zh-CN.md` | The same row in Chinese | troy-init writes its rows | Adds a row |

The pilot's `.claude/settings.local.json` holds three allow rules, none of which names troy-pstack, and troy-init writes no permission rule (F05 design D45). Each clone's `troy-mode/hooks.log`, in its git folder, holds lines whose `agent_type` is, for example, `troy-pstack:troy-developer`.

## 3. Probes

On 2026-11-16, nested `claude -p` sessions on haiku, with at most 3 turns, ran in a scratch git repository with a `.troy-mode/` folder, in this session's scratchpad. The renamed plugin was a copy of this branch in which only `plugin.json`'s `name` was `tstack`, loaded with `--plugin-dir`. `TROY_MODE_PYTHON` pointed at a stand-in that logged each hook call with its `CLAUDE_PLUGIN_ROOT` and input, and ran nothing. No GitHub repository, installed plugin, marketplace, or setting changed. The whole cost was under $0.10.

| Probe | Setup | What happened |
| --- | --- | --- |
| 1 | The copy in a folder named `tstack`, given to `--plugin-dir` as a Git Bash path `/c/...` with `MSYS_NO_PATHCONV=1` | The copy did not load: the init event listed only `troy-pstack@troy-pstack`. `--plugin-dir` needs a Windows path, such as `C:/...`. |
| 2 | As probe 1, with a Windows path. Troy's installed plugin on, as in every session. Prompt: `/poteto-mode reply with the single word ok`. | Both plugins loaded: `tstack@inline` and `troy-pstack@troy-pstack`. The agents included `troy-pstack:troy-architect` and `tstack:troy-architect`, and so on for each role. The bare `/poteto-mode` resolved to `tstack:poteto-mode`, and the `UserPromptExpansion` hooks of both plugins ran for it. The installed plugin's `path` and its hooks' `CLAUDE_PLUGIN_ROOT` were `D:\Troy\Projects\troy-pstack`, the folder itself, not a cache folder. |
| 3 | The copy in a folder named `copy-of-plugin`, with `--settings '{"enabledPlugins":{"troy-pstack@troy-pstack":false}}'`. Prompt: one `Agent` call with `subagent_type` `tstack:troy-code-reviewer`. | Only `tstack@inline` loaded. Its agents and commands were named `tstack:...`, from `plugin.json`, whatever the folder's name. Its hooks' `CLAUDE_PLUGIN_ROOT` was the folder given. The subagent ran, and the copy's unchanged `SubagentStart` matcher `^troy-pstack:troy-` did not start its hook. Afterwards Troy's `~/.claude/settings.json` still had `"troy-pstack@troy-pstack": true`. |
| 4 | Today's `troy_hook.py`, run directly with a `PreToolUse` `Write` of `docs/architecture.md` in the scratch troy-mode project | From `troy-pstack:troy-architect`: allowed, because the file is in the Architect's scope. From `tstack:troy-architect`: denied, "outside your write scope: nothing in the repository except files git ignores". |

So:

- **Names come from `plugin.json`.** The folder's name does not matter to agent or command names.
- **Never both plugins on.** With both enabled, each plugin's hooks treat the other plugin's roles as unknown subagents and refuse their writes (F05 design D40), and both mode guards run. Troy's move turns troy-pstack off before tstack starts (section 7), and the build's trial turns it off for its sessions with `--settings` (section 11.4).
- **Every matcher changes together.** An old matcher skips the renamed roles without any message.
- **The installed plugin runs from its folder.** In 2.1.325, a plugin from a `directory` marketplace runs in place: the init event's path and the hooks' `CLAUDE_PLUGIN_ROOT` are `D:\Troy\Projects\troy-pstack`, although `installed_plugins.json` names a cache folder. So every session runs that folder's working tree, today `main` at `3a14119`. Moving the folder takes the plugin away from every running session, and pulling the F19 build into it would change the hooks of running sessions while their agents keep the old names. The guide says that Claude Code "installs a plugin as a copy" (guide 1.3, from F10 design section 6). The build's trial checks this again, and the build corrects the guide if probe 2 holds.

## 4. The new names

### 4.1 Identity

| Thing | Today | After F19 |
| --- | --- | --- |
| Plugin name, in `plugin.json` | `troy-pstack` | `tstack` |
| Marketplace name, in `marketplace.json` | `troy-pstack` | `tstack` (D193) |
| Install ID | `troy-pstack@troy-pstack` | `tstack@tstack` |
| Commands | `/troy-pstack:troy-mode`, `/troy-pstack:troy-init`, `/troy-pstack:poteto-mode`, and so on | `/tstack:troy-mode`, `/tstack:troy-init`, `/tstack:poteto-mode`, and so on |
| Agents | `troy-pstack:troy-architect` and the other roles, `troy-pstack:poteto-agent`, `troy-pstack:comment-sicko` | `tstack:troy-architect` and the other roles, `tstack:poteto-agent`, `tstack:comment-sicko` |
| Version | 0.5.0 | 0.6.0, or the next free minor version (D193) |
| Model rule | `~/.claude/rules/troy-pstack-models.md` | `~/.claude/rules/tstack-models.md` |
| npm scope of the bun helpers | `@troy-pstack/` | `@tstack/` |
| GitHub repository | `ZJUCao/troy-pstack` | `ZJUCao/tstack` (D191) |
| Local folder | `D:\Troy\Projects\troy-pstack` | `D:\Troy\Projects\tstack` (D192) |
| mamba env | `troy-pstack` | `tstack` (D196) |

### 4.2 What stays

- Every skill's name: `troy-mode`, `troy-init`, `setup-pstack`, `poteto-mode`, `poteto-help`, and the rest. `setup-pstack` is upstream's name.
- Every agent's name after the prefix: the six `troy-*` roles, `poteto-agent`, and `comment-sicko`.
- The marker folder `.troy-mode/`, the folders inside the plugin (`troy-mode/`, `skills/`, `agents/`, `hooks/`, `docs/`), troy-check, troy-init, `troy_flow.py`, and the `troy_mode` names in code.
- `<pstack>` in the adapter still means the plugin's folder.
- The names `pstack`, `poteto-mode`, `poteto-agent`, and `poteto-help`, which credit Lauren Tan.

### 4.3 The credit

`plugin.json`'s description, and the plugin's entry in `marketplace.json`:

> tstack, Troy's own stack for Claude Code. Most of its skills, principles, playbooks, and subagent workflows come from Lauren Tan's pstack 0.15.36, used under its MIT license. troy-mode, the workflow from requirements to released versions, is Troy's own work. Not affiliated with or endorsed by Lauren Tan or Cursor.

The marketplace's description becomes "Troy's personal Claude Code plugins. Currently one: tstack." The keyword `tstack` replaces `troy-pstack`, and `pstack-fork` stays.

The README opens with:

> tstack is Troy's own stack for Claude Code, named the way Lauren Tan's pstack is named after poteto. It was called troy-pstack until version 0.5.0. Most of its skills, playbooks, agents, and guide pages are Lauren Tan's work from pstack, used under the MIT License. troy-mode is Troy's own work.

The rest of the README's credit stays: the "Not affiliated" note, the paragraph on Lauren Tan's MIT license, and the troy-mode note (F10 design D88). `LICENSE` keeps Lauren Tan's copyright and permission notice unchanged, and its line for Troy becomes "Copyright (c) 2026 Troy (modifications made in tstack, formerly troy-pstack)".

## 5. Inside the repository

### 5.1 One name per package

- **Hooks.** `troyhook/scopes.py` holds `PLUGIN_PREFIX = "tstack:"`, and builds `ROLE_PATTERN` from it with `re.escape`, so the name is written once. `modeguard.py` already takes `/tstack:troy-mode` for its message from `PLUGIN_PREFIX` (F13 design section 6).
- **Engine.** One constant `PLUGIN_PREFIX = "tstack:"` in `troyflow`, which `brief.py` and `runs.py` import in place of their two literals.
- **troy-init.** It reads `name` from `plugin.json`, as it already reads `version`, and its change-log line and messages use it: "troy-mode's rules brought up to tstack 0.6.0."
- **A test** checks that `plugin.json`, `marketplace.json`, `hooks.json`, and both constants agree (section 11.1).

Not chosen: the hooks reading `plugin.json` on every call. It would add a file read and a way to fail to every hook call, for a name that changes once.

The role match stays exact: only `tstack:troy-<role>` is a role. A match that accepts any prefix, like the mode guard's (F13 design D122), would let another plugin's `x:troy-developer` write source code, which F05's impostor tests forbid.

### 5.2 `hooks/hooks.json`

| Entry | Today | After F19 |
| --- | --- | --- |
| `SubagentStart` matcher | `^troy-pstack:troy-` | `^tstack:troy-` |
| `SubagentStop` matcher | `^troy-pstack:troy-` | `^tstack:troy-` |
| `PreToolUse` `Read`, its `if` rule | `Read(//**/troy-pstack/**)` | `Read(//**/tstack/**)` |
| `UserPromptExpansion` matcher | `^([^:]+:)?(poteto-mode\|no-comments)$` | Unchanged (F13 design D122) |

The `if` rule only keeps the hook from starting for reads outside a folder of that name; the hook itself still checks `CLAUDE_PLUGIN_ROOT` (F05 design section 9). After D192, the plugin runs from `D:\Troy\Projects\tstack` (probe 2), so `Read(//**/tstack/**)` matches it, its worktrees in `D:\Troy\Projects\tstack\.claude\worktrees\`, and a cache folder `~/.claude/plugins/cache/tstack/tstack/<version>/`. A checkout in a folder with another name, such as the old folder, gets no plugin reads without a permission rule. So the build's trial loads its copy from a folder named `tstack` (section 11.4).

### 5.3 Text

Every living mention (section 9) becomes `tstack`. Most of it is a plain replacement. These need more:

- **Install.** The README and guide section 1.2 say `/plugin marketplace add D:/Troy/Projects/tstack` and `/plugin install tstack@tstack`. Guide section 1.3 gains "Moving from troy-pstack", with the steps of section 7.
- **Problems.** The guide's problems table (guide section 8.6) gains a row: "Right after the rename, every role's write is refused as outside its scope." The fix: "troy-pstack is still installed or enabled. Uninstall it and restart (section 1.3)."
- **Work on tstack.** Guide sections 9.3 and 9.4: the env path `D:\miniforge3\envs\tstack\python.exe`, and the trial's `--settings` flag and folder named `tstack` (section 11.4).
- **Rule proposals.** In `skills/troy-mode/SKILL.md`, `gh issue create --repo <owner>/<name>`, where both come from the plugin folder's `origin` remote, in place of `<owner>/troy-pstack`.
- **Upstream files.** In the files that come from pstack (`docs/guide/`, the adapter `docs/harness/claude-code.md`, `poteto-help`, `setup-pstack`, the playbooks, `automations/benny/TODO.md`), only the lines that the fork already adapted for its name change. These lines already differ from upstream, so the README's upstream merge steps keep working unchanged (requirements section 8).

### 5.4 CI

- `troy-python-sample.yml` and `troy-cpp-sample.yml` check the plugin out into `tstack/` and run `tstack/troy-mode/dev/build_sample.py`.
- `troy-docs.yml` gains a step that runs `check_name.py` (section 11.2), and loses its path filter, so it runs on every PR. Its job takes about 30 seconds. Running on every PR also lets it become a required check later, when branch protection comes.
- No workflow or job is renamed, so the checks keep their names on PRs. CI builds no env named `troy-pstack`: the sample jobs take the sample's own `environment.yml`.

### 5.5 Plugin version (D193)

F19 changes what projects get, so its PR raises the minor version (F10 design D89): 0.5.0 becomes 0.6.0, or the next free minor version if another build raised it first. The version continues troy-pstack's. Each project's `.troy-mode/install.toml` records 0.5.0, and its `docs/rules.md` change log names the versions, so an upgrade to 0.6.0 reads as the next step.

## 6. Outside the repository

### 6.1 The GitHub repository (D191)

`ZJUCao/troy-pstack` is renamed `ZJUCao/tstack`, in the quiet window after the build PR merges (section 7). GitHub then sends old web links, `git fetch` and `git push`, and API calls to the new name, as long as no new repository takes the old one. Issues, PRs, CI history, and the links in change logs, such as `https://github.com/ZJUCao/troy-pstack/pull/57`, keep working.

- Troy renames it in the repository's settings, or says yes in chat at that time and a session runs `gh repo rename tstack --repo ZJUCao/troy-pstack --yes`. It reaches outside this PC, so it always needs Troy.
- The repository's description becomes "tstack: Troy's own stack for Claude Code. Most skills come from Lauren Tan's pstack (MIT); troy-mode is Troy's own work."
- Each clone then sets its remote, once per folder: `git remote set-url origin git@github.com:ZJUCao/tstack.git`.

### 6.2 The local folder (D192)

A new clone at `D:\Troy\Projects\tstack` takes over, and the old folder stays as it is until nothing uses it:

1. `git clone git@github.com:ZJUCao/tstack.git D:\Troy\Projects\tstack`, after section 6.1, then check `git config user.email`.
2. Copy the git-ignored `.claude\settings.local.json` from the old folder into the new one. Troy rewrites its standing trial permission to name tstack. Troy pastes it in, because the auto-mode classifier refuses the agent editing that rule.
3. Copy the project memory, `C:\Users\Troy\.claude\projects\D--Troy-Projects-troy-pstack\memory`, to `C:\Users\Troy\.claude\projects\D--Troy-Projects-tstack\memory`, the key Claude Code derives from the new path. The first session in the new folder updates the notes' folder, plugin, and env names.
4. The marketplace moves to the new folder (section 7).
5. Nobody pulls `main` in the old folder again. The old plugin runs from it until Troy restarts Claude Code (probe 2), and its 9 worktrees and their sessions keep working until then. When no session needs it, and `git worktree list` there shows no branch with unpushed work, Troy deletes the old folder. That is Troy's step, at any later time.

Not chosen:

- **Rename the folder in place.** The moment it moves, every running session loses its plugin: the hooks' `exec python ... troy_hook.py` finds no file, Python exits with code 2, and Claude Code treats that as a block of every call the hooks match, in every project. Every session would have to stop first, `git worktree repair` would fix the 9 worktrees, and archived sessions would lose their folders.
- **Keep the folder's name.** The plugin runs from this folder, so the Read `if` rule would have to keep matching `troy-pstack`, and the docs would name a folder called troy-pstack that holds tstack.

### 6.3 The marketplace

The marketplace is named `tstack`, a `directory` source at `D:\Troy\Projects\tstack`. Section 7 adds it with the CLI, which also records it in `~/.claude/settings.json`.

### 6.4 The mamba env (D196)

`troy-mode/dev/environment.yml` names the env `tstack`. In the quiet window, Troy, or a session on Troy's yes, creates it from the new folder:

```powershell
$env:MAMBA_ROOT_PREFIX = 'D:\miniforge3'
$env:UV_LINK_MODE = 'copy'
D:\miniforge3\Library\bin\mamba.exe env create -f D:\Troy\Projects\tstack\troy-mode\dev\environment.yml
D:\miniforge3\envs\tstack\Library\bin\uv.exe pip install --python D:\miniforge3\envs\tstack\python.exe -r D:\Troy\Projects\tstack\troy-mode\dev\requirements-dev.lock
```

Until then, sessions keep using `D:\miniforge3\envs\troy-pstack\python.exe`, which holds the same packages. The old env is removed with the old folder: `mamba env remove -n troy-pstack`. CI needs nothing (section 5.4).

## 7. Troy's move (D194)

The move happens in one quiet window after the build PR merges, when no session is working. Sessions started before the restart in step 6 keep troy-pstack until then.

| Step | What | Who |
| --- | --- | --- |
| 1 | Rename the GitHub repository (section 6.1). | Troy, or a session on Troy's yes |
| 2 | Clone the new folder, copy its local settings and the memory (section 6.2). | A session on Troy's yes; Troy pastes the trial permission |
| 3 | Create the env `tstack` (section 6.4). This step may also come later. | A session on Troy's yes |
| 4 | Swap the plugin, with the commands below. | Troy, or a session on Troy's yes |
| 5 | If `~/.claude/settings.json` still has a `troy-pstack` key under `extraKnownMarketplaces` or `enabledPlugins`, remove it. | Troy |
| 6 | Restart Claude Code: quit the desktop app and open it again. | Troy |
| 7 | Check: in a new session in a troy-mode project, `/tstack:troy-mode status` runs, and the command list offers no `/troy-pstack:` command. | Troy |
| 8 | Upgrade the projects (section 8). | Troy types the request |

`claude` is not on PowerShell's PATH, so step 4 uses the CLI that the desktop app bundles. Its version folder changes with app updates; on 2026-11-16 it was `2.1.325\806e0a45e6f5`:

```powershell
$cli = 'C:\Users\Troy\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.325\806e0a45e6f5\claude.exe'
& $cli plugin uninstall troy-pstack@troy-pstack
& $cli plugin marketplace remove troy-pstack
& $cli plugin marketplace add D:\Troy\Projects\tstack
& $cli plugin install tstack@tstack
& $cli plugin list
& $cli plugin marketplace list
```

`plugin list` must show `tstack@tstack` at 0.6.0, enabled, and no troy-pstack; `marketplace list` must show `tstack` and no `troy-pstack`. The uninstall comes first, so the two plugins never run together in a new session (section 3).

**The way back**, while the old folder exists: uninstall `tstack@tstack`, remove the marketplace `tstack`, add the old folder's marketplace, install `troy-pstack@troy-pstack`, and restart. A project that was already upgraded then has a newer troy-check than the plugin, and `status` asks for an upgrade, which brings back the 0.5.0 files.

## 8. Existing projects (D195)

Each project moves with `/tstack:troy-mode upgrade troy-mode`, at a natural stop with no stage PR open, as for every plugin version (F14 design D137):

- `ZJUCao/troy-mode-trial` moves in the build's trial, through the copy, before Troy's move (section 11.4).
- `ZJUCao/recipe-menu` moves when Troy types the request there after the move.

Until its upgrade, a project keeps working with tstack: its committed files name no agent or command, and `status` says that its troy-check differs from the plugin's, as after any new version.

The upgrade PR, `[rules] Upgrade troy-mode to 0.6.0`, changes each file of section 2.3:

| File | Change |
| --- | --- |
| `.troy-mode/checks/troy_check.py` | Replaced, as a file troy-init owns that nobody edited |
| `.github/workflows/troy-mode.yml` | Replaced, the same way |
| `.troy-mode/config.toml` | Its one comment line rewritten, only when the line is exactly what troy-init wrote |
| `pyproject.toml` | The same, for its one comment line |
| `docs/rules.md` and its mirror | A new change-log row, "troy-mode's rules brought up to tstack 0.6.0."; the earlier rows keep troy-pstack |
| `.troy-mode/install.toml` | Version 0.6.0 |

The rewrite of the two comment lines is new in troy-init's upgrade, and narrow. A fixed table holds the two old lines and their new lines, compared with the line's trailing carriage return removed. A line anyone changed is left alone, and the upgrade report lists it as a difference. Nothing else in `config.toml` or `pyproject.toml` changes, as F06 design D54 requires.

**What does not change.** `hooks.log` lines already written keep the old names. Nothing depends on them: F07's check after a run reads only the lines since the run's snapshot, which come after the restart, and F08's retrospective groups the lines by rule, not by agent. Git history and merged PR text keep the old name too.

After the upgrade, a code search for `troy-pstack` in a project finds only the older rows of `docs/rules.md` and its mirror.

## 9. What keeps the old name (D197)

The rule: text that says what tstack is or does now uses the new names. Text that records what happened keeps the names of its time.

These keep the old name:

- **Approved designs.** F01 to F14, and any later design approved before F19's build merges. They record decisions and trials as they were: F13's trial saw `command_name` `troy-pstack:poteto-mode`. Their versions, sync notes, and approvals stay. This design links the old names to the new ones.
- **Change logs.** The change-log section of every document, and the requirements' header Status row, which summarizes the versions.
- **The pilot's records.** The pilot report and F11's other records.
- **Links and history.** PR and issue links, git history, and the text of merged PRs.
- **Notes and memory outside the repository.** A session updates them when it next uses them (section 6.2), not in F19's PR.
- **Projects' rules tables.** The older rows of `docs/rules.md` in each project (section 8).

The README's opening and `LICENSE` say "formerly troy-pstack" (section 4.3).

Everything else changes, in the one build PR: the README, both guides, the adapter, the skills, the agents, the roles, the templates, troy-check, troy-init, the engine, the hooks, the tests, CI, the samples, the pack READMEs, `environment.yml`, and the requirements outside their header Status row and change log. The name check of section 11.2 keeps it that way.

## 10. Changes to earlier features

| Feature | Change |
| --- | --- |
| F02 Checks | The text in `troy_check.py`, `workflow.yml`, and `config.default.toml`. |
| F03 Language packs | The Python pack's `pyproject.toml` comment, the pack READMEs, and the samples. The env becomes `tstack`, still a series of one named after the project (F03 design D26). |
| F04 Roles | `troy-mode/roles/common.md` and its exact copy at the end of each of the six agent files, and the Architect's rule-proposal task. |
| F05 Hooks | The matchers and the `if` rule (section 5.2), `PLUGIN_PREFIX` and `ROLE_PATTERN` (section 5.1), and their tests. |
| F06 troy-init | The plugin's name from `plugin.json`, the change-log line and messages, and the rewrite of the two comment lines in upgrade (section 8). |
| F07 Entry skill | The briefs' `subagent_type` and the run check's `hooks.log` match, through the engine's constant. Command names in `SKILL.md`. |
| F09 Rule change | The repository of a rule proposal's issue comes from the plugin folder's `origin` (section 5.3). |
| F10 Docs | The README, both guides, and the plugin descriptions (section 4.3). The guide's install, move, and problems rows, and its sentence on copies if the trial confirms probe 2. |
| F13 Mode guard | The message's `/tstack:troy-mode`, through `PLUGIN_PREFIX`, as F13 design section 9 foresaw. The matcher stays. |

No upstream pstack line changes beyond those the fork already adapted for its name (section 5.3).

## 11. How F19 is checked (D198)

### 11.1 Tests

A separate agent changes and adds the tests from this design before the code changes. Each literal `troy-pstack:` in the tests becomes `tstack:`. New cases include:

| Suite | Cases include |
| --- | --- |
| Hooks | `tstack:troy-<role>` is a role with its write scope. `troy-pstack:troy-<role>` is now an unknown subagent and read-only, as in probe 4. The impostors `xtstack:troy-developer`, `tstack:troy-developer-2`, and `my-tstack:troy-test-engineer` are not roles. `hooks.json` has the matchers and the `if` rule of section 5.2. The helpers' fake installed root is `.../cache/tstack/tstack/<version>`. |
| Mode guard | The message points to `/tstack:troy-mode`. `troy-pstack:poteto-mode` and `tstack:poteto-mode` are both refused. |
| Engine | Briefs give `tstack:troy-<role>`. The run check counts `hooks.log` lines of `tstack:` roles and not those of `troy-pstack:` roles. |
| troy-init | The change-log line names `tstack` and the version from `plugin.json`. Each comment line is rewritten when it is exact, also with CRLF, and left alone and listed when edited. |
| Dev tools | `test_plugin_name.py`: `plugin.json`, `marketplace.json`, the `hooks.json` matchers and `if` rule, `troyhook`'s `PLUGIN_PREFIX`, and the engine's constant all say `tstack`. The tests of `check_name.py`. |

The suites of troy-check, troy-init, the engine, the dev tools, and the hooks pass on Linux and Windows.

### 11.2 The name check

`troy-mode/dev/check_name.py` reads every tracked text file and reports each line that names the old plugin (`troy-pstack`, `troy_pstack`, or `troy pstack`, in any case), unless one of these holds:

1. The file is in the tool's list of history files: the designs approved before F19's build merges, this design, and the pilot report.
2. The line lies in a change-log section: under a heading whose text after its number is exactly `Change log` or `修改记录`, up to the next heading of the same or a higher level.
3. The line is the `| Status |` or `| 状态 |` row of a document's header table.
4. The line also names `tstack`, so it talks about the rename.

It exits with 0 when it finds nothing, 1 when it finds a line, and 2 when it cannot run, like `check_pairs.py`. Each finding names the file and line. `troy-docs.yml` runs it on every PR (section 5.4).

### 11.3 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test or the name check fail: `ROLE_PATTERN` still on the old prefix; one `SubagentStart` or `SubagentStop` matcher left; the `if` rule left; the engine's `subagent_type` left; the run check's `hooks.log` match left; the guard's message pointing to `/troy-pstack:troy-mode`; `plugin.json`'s or `marketplace.json`'s name left; a stray `/troy-pstack:troy-mode` in a guide page; the upgrade rewriting an edited comment line; troy-init's change-log line with a fixed name; `environment.yml`'s name left; and the name check missing a capitalized `Troy-pstack` or a Chinese mirror. The counts go in the build PR's description.

### 11.4 Trial

Before the build PR opens, the renamed plugin runs on a real project:

- **The plugin.** `git archive` of the PR's head into `<scratchpad>/trial/tstack`, a folder named `tstack` so that the `if` rule matches, loaded with `--plugin-dir` and a Windows path.
- **The old plugin off.** `--settings '{"enabledPlugins":{"troy-pstack@troy-pstack":false}}'` for each nested session only, as probe 3 proved. Troy's settings do not change.
- **The project.** A fresh clone of `ZJUCao/troy-mode-trial`, with `MSYS_NO_PATHCONV=1` and the nested-session setup of earlier trials (guide section 9.4).
- **The permission.** The standing trial permission names troy-pstack. Troy updates its wording to cover tstack and a scratch copy of it before the trial.

The runs:

1. The init event lists `tstack@inline` and no `troy-pstack`, and the roles are `tstack:troy-*`.
2. `/tstack:troy-mode upgrade troy-mode` opens `[rules] Upgrade troy-mode to 0.6.0`. Its checks pass, troy-init merges it, and a code search then finds `troy-pstack` only in the older rows of `docs/rules.md` and its mirror.
3. `/tstack:troy-mode continue`, with the answer to the `troy_approves_first` question given in advance. The Test Manager, `tstack:troy-test-manager`, writes F02's test plan. Its writes are allowed, it reads plugin files with no permission rule, the check after the run passes, the new `hooks.log` lines say `tstack:`, and the session stops at "Waiting for Troy".
4. `/poteto-mode hi` is refused, and the message points to `/tstack:troy-mode`.
5. Probe 4 again with the built hook: `tstack:troy-architect` is allowed and `troy-pstack:troy-architect` is denied.
6. Probe 2's finding again, read-only: where the installed plugin runs from. The answer decides the guide's sentence on copies (section 10).

The trial costs a few dollars, most of it the Test Manager's run. The build PR's description gives the results and the trial repository's state after them.

### 11.5 Status

| When | F19's status in requirements 7.2 |
| --- | --- |
| The build PR merges after a passing trial | Runs on a sample project: the trial upgraded `ZJUCao/troy-mode-trial` to tstack 0.6.0 and ran a role under the new names, with troy-pstack turned off. Troy's PC still runs troy-pstack. |
| Troy's move is done, and the pilot upgraded and ran a role under tstack | Used on a real project: Troy's PC runs tstack 0.6.0, and `ZJUCao/recipe-menu` upgraded to it and ran troy-mode under the new names. |

The status updates are their own PRs.

## 12. When it runs (D199)

1. **Wait.** The build starts when these have merged: the F11 wrap-up's PRs (the guide fixes, the pilot report, and the final status), the F15 design PR, and every other open troy-pstack PR, and no session is building in the repository. The build changes about 130 files, so any PR open beside it would conflict.
2. **Build.** One session, one PR with one commit, with the tests, the name check, the planted bugs, and the trial of section 11.
3. **Merge** when every check passes.
4. **Move.** Troy's quiet window, the same day if Troy can (sections 6 and 7). Then the pilot's upgrade, at its next natural stop.
5. **Status.** The status PRs, from the new folder.
6. **After.** Only then does a second project adopt troy-mode (the F19 row). Designs written before the build merges keep their names (section 9). Later designs and builds use the new ones.

## 13. How F19 maps to the requirements

| Requirement | Where F19 covers it |
| --- | --- |
| F19 row: `troy-pstack` becomes `tstack` | Sections 4.1 and 5 |
| F19 row: commands become `/tstack:troy-mode` and `/tstack:troy-init` | Section 4.1 |
| F19 row and Q4: skill, agent, and folder names inside stay | Section 4.2 |
| F19 row: the hooks' agent-name match | Sections 5.1 and 5.2 |
| F19 row: the tests | Section 11.1 |
| F19 row: the documents | Sections 5.3 and 9 |
| F19 row: the GitHub repository | Section 6.1 |
| F19 row: the README and plugin descriptions credit Lauren Tan's pstack and say troy-mode is Troy's own | Section 4.3 |
| F19 row: one PR, after the pilot's v0.1 release and before a second project | Section 12 |
| Section 8: no upstream file edited, upstream merges stay easy | Section 5.3 |
| Section 8: Language, CI checks | Sections 5.4 and 11.2 |
| Section 8: Python environments | Section 6.4 |

## 14. Not in F19

- Renaming skills, agents after the prefix, the plugin's folders, `.troy-mode/`, troy-check, troy-init, or `setup-pstack`.
- Editing approved designs or change logs (section 9).
- Rewriting the git history of the repository or of projects (requirements section 9).
- Deleting the old folder, the old env, or old cache folders. Troy does that later.
- A hook that notices a second troy-mode plugin. Section 7's checks and the guide's problems row cover it.
- Updating the memory and notes outside the repository in the build PR.

## 15. Decisions for Troy

F19 uses D191 to D199. Troy accepted every recommended answer on 2026-11-16, and agreed to reword the standing trial permission to cover tstack before the build's trial (section 11.4).

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D191 | Does the GitHub repository `ZJUCao/troy-pstack` become `ZJUCao/tstack`? | A: rename it in the quiet window after the build PR merges. Troy renames it in its settings, or says yes in chat and a session runs `gh repo rename`. Its description changes, and each clone sets its remote (section 6.1). B: keep the repository's name, and rename only the plugin. C: a new repository `ZJUCao/tstack`, with the old one archived. | A. GitHub forwards old links, clones, and API calls, so nothing breaks, and the repository then matches the plugin. B keeps the old name in every clone URL and link. C splits the issues and PRs that the change logs link to. |
| D192 | What happens to the folder `D:\Troy\Projects\troy-pstack`? | A: a new clone at `D:\Troy\Projects\tstack` becomes the marketplace, with the local settings and the project memory copied. The old folder stays untouched, with `main` never pulled again, until no session needs it; then Troy deletes it (section 6.2). B: rename the folder in place and repair its 9 worktrees, with every session stopped. C: keep the folder's name. | A. The installed plugin runs from this folder (probe 2), so moving it under running sessions would block their tool calls. A new clone lets them finish. B needs a moment when nothing runs, and archived sessions lose their folders. C keeps a folder named troy-pstack, which the hooks' Read rule would have to keep matching. |
| D193 | What are the marketplace's name and the plugin's version? | A: marketplace `tstack`, install ID `tstack@tstack`; version 0.6.0, or the next free minor version when the build merges (section 5.5). B: keep the marketplace `troy-pstack`, so the ID is `tstack@troy-pstack`. C: start tstack at 1.0.0. | A. The marketplace has to be added again for the new folder anyway, so its name can change at no cost. A minor step continues each project's version history from 0.5.0. 1.0.0 would claim a stability that nobody has decided. |
| D194 | How does Troy's PC move from `troy-pstack@troy-pstack` 0.5.0 to tstack? | A: section 7's steps in one quiet window: uninstall troy-pstack first, remove its marketplace, add the new folder's marketplace, install `tstack@tstack`, check with `plugin list`, and restart Claude Code. B: install tstack first and remove troy-pstack later. C: as A, but disable troy-pstack instead of uninstalling it, for a quicker way back. | A. With both on, each plugin's hooks refuse the other's role writes (probes 2 and 4), so they must never run together, and B lets them. C keeps a marketplace pointing at a folder that will be deleted; section 7 gives a way back while the old folder exists. |
| D195 | How do existing projects move? | A: `/tstack:troy-mode upgrade troy-mode` in each, at a natural stop: `ZJUCao/troy-mode-trial` in the build's trial, `ZJUCao/recipe-menu` after Troy's move. The upgrade replaces the files troy-init owns, adds a `rules.md` row, and rewrites the two comment lines in `config.toml` and `pyproject.toml` only when they are unchanged (section 8). B: as A, but the two comment lines stay. C: as A, with the comment lines edited by hand. | A. After the upgrade, a code search finds the old name only in the history rows of `docs/rules.md`. The rewrite touches one known line per file and never a line anyone changed. B leaves two comments that name a plugin that no longer exists. C depends on remembering. |
| D196 | What is the mamba env called? | A: `tstack`, created from `environment.yml` in the quiet window. `troy-pstack` stays until the old folder goes, and is removed then (section 6.4). B: keep `troy-pstack`. | A. An env is named after its series, and this series is now tstack (F03 design D26, requirements section 8). Creating it takes a few minutes, CI does not use it, and the old env keeps working meanwhile. |
| D197 | Which text keeps the old name? | A: history keeps it: designs approved before the build merges, change logs, the requirements' header Status row, the pilot report, links, git history, and notes outside the repository. The README and `LICENSE` say "formerly troy-pstack". Everything else changes (section 9). B: change every mention, the approved designs included, each with a new version. C: change only the plugin's identity, matchers, code, and tests, and no document. | A. Records stay true to what happened, such as F13's trial seeing `troy-pstack:poteto-mode`, and everything that Troy or a role reads to work uses the new names. B rewrites 268 lines in 28 approved designs and makes their trial records claim what never ran. C leaves the guides telling Troy to type commands that no longer exist. |
| D198 | How is the build checked? | A: tests changed and added from this design by a separate agent; the name check `check_name.py` in CI on every PR, and a test that the names agree; planted bugs; and a trial on `ZJUCao/troy-mode-trial` with a copy of the PR in a folder named `tstack` and troy-pstack turned off for the trial's sessions: the upgrade, one role run, the guard, and probe 4 again (section 11). B: as A without the name check, with a one-off search in the PR description. C: tests and planted bugs only. | A. A rename fails by missing a mention somewhere. Only a check on every PR keeps sessions, whose notes are full of the old name, from bringing it back. The trial proves on a real project, for a few dollars, that roles still write and read plugin files under the new names. |
| D199 | When does the build run? | A: after the F11 wrap-up's PRs (guide fixes, pilot report, final status), the F15 design PR, and every other open troy-pstack PR have merged, with no session building in the repository. Troy's move follows the same day if possible, and a second project adopts troy-mode only after it (section 12). B: start now and rebase over the other PRs at the end. C: also wait for the builds of F15 to F18. | A. The build changes about 130 files, so any PR open beside it conflicts, and B would resolve those conflicts by hand. C delays the rename for nothing: later features are simply built under the new name. |

Requirements 1.40 records the approved changes:

- The F19 row says what F19 builds, citing D191 to D199: the repository renamed (D191), the new folder (D192), the marketplace `tstack` and the next minor version (D193), Troy's move with troy-pstack uninstalled first (D194), the projects' upgrade with the two comment lines (D195), the env `tstack` (D196), the history that keeps the old name (D197), the checks and the trial (D198), and the order (D199).
- Section 8, Language: CI also checks that living text no longer names the old plugin (`troy-mode/dev/check_name.py`, D198).
- Every other mention in the requirements changes in the build PR, with the rest of the rename, so that the rename stays one PR.

## 16. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-16 | First draft, with the probes of section 3. |
| 1.0 | 2026-11-16 | Approved by Troy with D191 to D199, every recommended answer. |
