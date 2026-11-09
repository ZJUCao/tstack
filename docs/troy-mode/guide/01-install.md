# 1. Install

| | |
| --- | --- |
| Version | 0.1 |
| Date | 2026-11-09 |
| Source of truth | This English file. [`01-install.zh-CN.md`](01-install.zh-CN.md) is the Chinese mirror. |

troy-mode ships inside the troy-pstack plugin. You install the plugin once, give each project one permission, and choose models only if the defaults do not suit you.

## 1.1 What your PC needs

| What | Why |
| --- | --- |
| Claude Code, in the desktop app or the CLI | troy-mode is a Claude Code skill. |
| Git for Windows, with Git Bash | troy-mode runs its engines, git, and gh through the Bash tool, which is Git Bash on Windows. |
| `gh`, signed in to your GitHub account | troy-mode opens PRs, comments on them, and merges them with `gh`. `gh auth status` must pass. |
| Python 3.11 or newer | troy-mode's engines and hooks use only the standard library. They run `python` on Windows and `python3` elsewhere, or the program in `TROY_MODE_PYTHON` when you set it. |
| Miniforge, for Python projects | The language step creates the project's environment with mamba. The environment holds Python 3.13 and uv, and uv installs every package from the project's lock. troy-mode never creates a `.venv` ([requirements section 8](../requirements.md#8-non-functional-requirements)). |

- **mamba.** troy-init looks for mamba on the PATH, then in `MAMBA_EXE`, and troy-mode can pass the language step `--mamba` with its path ([troy-init skill](../../../skills/troy-init/SKILL.md)). The checks troy-mode runs in the feature loop look only on the PATH and in `MAMBA_EXE` ([F07 design section 6.1](../design/F07-entry-skill.md#61-the-brief)). On your PC mamba is not on Git Bash's PATH, so set `MAMBA_EXE` to `D:\miniforge3\Library\bin\mamba.exe`, and `MAMBA_ROOT_PREFIX` to the Miniforge folder, `D:\miniforge3`, in the environment Claude Code starts in.
- **No Python found.** In a troy-mode project, the hooks stop with "troy-mode: no Python 3.11 or newer found; set TROY_MODE_PYTHON". Set `TROY_MODE_PYTHON` to a Python 3.11 or newer.
- **C/C++ projects** get CMake, Ninja, and the clang tools from their mamba environment. The compiler comes from outside it: on your PC, the MSYS2 GCC on the PATH ([C/C++ pack's README](../../../troy-mode/lang/cpp/README.md)). The feature loop does not work for C/C++ yet: a test PR registers its tests in `CMakeLists.txt`, which counts as a dependency file, so troy-mode undoes every Test Engineer run there. A small fix to troy-mode comes before the first C/C++ project ([F11 design section 3.3](../design/F11-pilot.md#33-cc-and-the-f07-fix)).

## 1.2 Install troy-pstack

troy-pstack's folder is both the plugin and a one-plugin marketplace. In Claude Code, type:

```text
/plugin marketplace add D:/Troy/Projects/troy-pstack
/plugin install troy-pstack@troy-pstack
```

Claude Code puts the plugin's name in front of its skills and agents. So you type `/troy-pstack:troy-mode` and `/troy-pstack:troy-init`, and the roles are the agents `troy-pstack:troy-architect`, `troy-pstack:troy-interface-designer`, `troy-pstack:troy-test-manager`, `troy-pstack:troy-developer`, `troy-pstack:troy-test-engineer`, and `troy-pstack:troy-code-reviewer`.

To see that troy-mode is there, open a new session: `/troy-pstack:troy-mode` and `/troy-pstack:troy-init` are among the commands Claude Code offers ([F11 design section 2](../design/F11-pilot.md#2-prerequisites)). The plugin's version must be 0.2.0 or newer: that is the first version that documents troy-mode for use.

## 1.3 Update after a new plugin version

Claude Code installs a plugin as a copy, and it updates the copy only when the plugin's version rises ([F10 design section 6](../design/F10-docs.md#6-the-plugin-version-d89)). The marketplace is troy-pstack's own folder, so an update copies what that folder holds: first bring its checkout to the newest `main`. After a troy-pstack PR raises the version, run this and restart Claude Code:

```text
claude plugin update troy-pstack@troy-pstack
```

A project you already set up keeps its own copy of troy-check, the templates, and the workflow. To bring it to the new version, type `/troy-pstack:troy-mode upgrade troy-mode` in the project ([reference: an older copy](08-reference.md#86-problems)).

## 1.4 The merge permission

troy-mode merges its own PRs within its rights (R18). Claude Code's auto mode may still refuse `gh pr merge` as a merge without review. troy-mode then stops and tells you which permission to add ([F07 design section 8.6](../design/F07-entry-skill.md#86-merging-r18-f02-d14)). To avoid that stop, add this line to the project's `.claude/settings.local.json` before you start:

```json
{ "permissions": { "allow": ["Bash(gh pr merge *)"] } }
```

If the file already exists, add `"Bash(gh pr merge *)"` to its `allow` list. The file is git-ignored and yours, so troy-init does not write it. It lets troy-mode merge any PR in that project without a prompt. troy-mode's rights still limit it to the PRs it may merge: it never merges a PR that waits for your approval ([section 7.2](07-taking-part.md#72-what-troy-mode-does-alone)).

## 1.5 Models and effort

Each role runs as a subagent with its own model. The Product Manager is the main session.

| Role | Runs as | Model |
| --- | --- | --- |
| Product Manager | The main session | The session's model |
| Architect | `troy-pstack:troy-architect` | opus |
| Interface Designer | `troy-pstack:troy-interface-designer` | opus |
| Test Manager | `troy-pstack:troy-test-manager` | opus |
| Developer | `troy-pstack:troy-developer` | sonnet |
| Test Engineer | `troy-pstack:troy-test-engineer` | sonnet |
| Code Reviewer | `troy-pstack:troy-code-reviewer` | opus |

Every role runs with the session's effort. To change a role in one project, add a `[roles.<role>]` table to the project's `.troy-mode/config.toml` ([F07 design section 3.2](../design/F07-entry-skill.md#32-model-and-effort-f04-d32)). For example, to run the Developer on opus with high effort:

```toml
[roles.developer]
model = "opus"
effort = "high"
```

- `<role>` is `architect`, `interface-designer`, `test-manager`, `developer`, `test-engineer`, or `code-reviewer`.
- `model` is a name the Agent tool accepts, such as `opus` or `sonnet`. `effort` is `low`, `medium`, `high`, `xhigh`, or `max`. Leave a key out to keep the default.
- The change lands in its own `[rules]` PR, because `.troy-mode/config.toml` is a config file (R02). You make that PR yourself: troy-mode changes the config only in troy-init's steps, in the rule change flow, and to record how many features you approve ([section 3.4](03-features.md#34-after-the-first-features)), and no flow sets `[roles]`. On a branch from `origin/main`, edit the file, commit with a title such as `[rules] Set the Developer's model and effort`, push, and open the PR. The trial's PR [#5](https://github.com/ZJUCao/troy-mode-trial/pull/5), `[rules] Set the Code Reviewer's effort`, is such a PR.
- Merge it once its checks pass. troy-mode reads `[roles]` from the commit it works on, so roles started on branches made after the merge use the new values.
- The project's troy-check must be new enough to accept `[roles]`. If it is older, troy-check refuses the key, and `status` says that an upgrade brings it up to date ([reference: an older copy](08-reference.md#86-problems)).
