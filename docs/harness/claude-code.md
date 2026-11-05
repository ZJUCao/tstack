# troy-pstack in Claude Code

troy-pstack is a fork of Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack) 0.15.36. Its skills keep upstream's Cursor names so that upstream changes still merge cleanly. Read this file once per session, then map each Cursor name in a skill with the tables below.

- `<pstack>` means the troy-pstack plugin folder, the one that holds `skills/` and `docs/`. When Claude Code loads a skill it shows the skill's base directory, `<pstack>/skills/<name>`, so `<pstack>` is two levels up from it.
- When a skill says "pstack", it means troy-pstack, unless it talks about Lauren's upstream project.
- If a Cursor field has no row, drop it and say so. Never pass a field or value the tool schema rejects.

## Tools

| Cursor | Claude Code |
| --- | --- |
| `Task` | `Agent` |
| `AskQuestion` | `AskUserQuestion`. In `-p` mode it is absent, so ask in plain text. |
| Open a todolist | Use the session's task-list tool (`TodoWrite`, or `TaskCreate` and `TaskUpdate`). Otherwise keep the list in your reply and update it at each phase. |
| Run another pstack skill (`/name` or "the **name** skill") | `Read` `<pstack>/skills/<name>/SKILL.md` and follow it. Every troy-pstack skill but `setup-pstack` sets `disable-model-invocation: true`, so the `Skill` tool refuses it. When you tell the user to type it, write `/troy-pstack:<name>`. |
| `Grep`, `Glob` | `Bash` with `rg` when the session has no `Grep` or `Glob`. |

## Subagent fields

| Cursor | Claude Code |
| --- | --- |
| `subagent_type: generalPurpose` | `subagent_type: "general-purpose"` |
| `poteto-agent`, `comment-sicko` | `troy-pstack:poteto-agent`, `troy-pstack:comment-sicko` |
| `readonly: true` | `subagent_type: "Explore"`. It keeps `Bash`, so the brief also says "do not edit files", and you check `git status` afterward. |
| `readonly: false` | `general-purpose`. It keeps the session's MCP servers. |
| `environment: "cloud"` | `isolation: "worktree"`. Name the branch or commit the worker checks out. Use `isolation: "remote"` only when the `Agent` tool offers it and the user asked for cloud work. |
| `environment: "local"` | Omit. |
| `cloud_base_branch: <b>` | Tell the worker to check out `<b>` first. |
| `run_in_background: true` | Omit. Subagents run in the background by default and notify you when they finish. |
| `resume` | Spawn a new agent and paste the earlier result into its brief. |
| `file_attachments` | List the paths in the brief. |
| A template or brief a skill tells you to pass verbatim | Pass it verbatim, then add one line: "Cursor names in this brief map to Claude Code through `<pstack>/docs/harness/claude-code.md`; read it first." Give the absolute path. |
| "readonly strips MCP" | A Cursor fact. Claude Code's `Explore` keeps MCP tools. Follow the instruction anyway. |

## Models

Claude Code's `Agent` tool takes `model` (`opus`, `sonnet`, `haiku`, or `fable`) and `effort` (`low`, `medium`, `high`, `xhigh`, or `max`). A model's **family** is that alias, so `opus` and `sonnet` are two families. Upstream pstack routes code to Grok and judgment to Claude Opus. troy-pstack maps them like this:

| Cursor slug in a skill | Claude Code |
| --- | --- |
| `claude-<family>-<version>-<effort>[-fast]`, such as `claude-opus-5-5-xhigh` | `model: "<family>"` and `effort: "<effort>"`, so `model: "opus"`, `effort: "xhigh"`. |
| `grok-<version>-<effort>[-fast]`, such as `grok-4.7-xhigh-fast` | `model: "sonnet"` and `effort: "<effort>"`. Sonnet takes upstream's fast code-model seat. |
| Any other non-Claude slug (`gpt-*`, `gemini-*`, `composer-*`) | `model: "sonnet"` with the slug's effort, and say so. |
| A `-fast` suffix | Drop it. Fast mode in Claude Code is a session toggle (`/fast`), not a subagent field. |
| `auto` or `inherit-parent` | Omit `model`, so the agent runs on the session model. |
| A role value `<model> <effort>` from the model rule, such as `opus high` | `model: "opus"` and `effort: "high"`. |
| "Families go by prefix" (`claude-*`, `grok-*`, `composer-*`) | Families go by the mapped `model` value. A `grok-*` slug counts as the `sonnet` family. |
| "fast or standard speed" for a subagent | Ignore. Claude Code subagents have one speed, so only the model and effort change. |

So the upstream panel pair "Opus and Grok" becomes "Opus and Sonnet". Those are two families, which keeps every "use a family other than the parent's" rule working. Both come from one vendor, so weigh their agreement as somewhat less independent than upstream's cross-vendor panels.

The model rule is `~/.claude/rules/troy-pstack-models.md`. It replaces upstream's `~/.cursor/rules/pstack-models.mdc`. Claude Code loads every `.md` file in `~/.claude/rules/` into each new session, so its role lines are usually in context already. If they are not, read the file. If the file or the role's line is missing, use the skill's default slug and map it with the table above. `setup-pstack` writes this file.

## Paths

| Cursor | Claude Code |
| --- | --- |
| `.cursor/skills/`, `~/.cursor/skills/` | `.claude/skills/`, `~/.claude/skills/` |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json` | `~/.claude/plugins/` (search it recursively), `.claude-plugin/plugin.json` |
| `.cursor/rules/*.mdc`, always-applied rules | `CLAUDE.md`, or `AGENTS.md` when no `CLAUDE.md` exists. Claude Code never reads `.mdc` files. The model rule is the exception. See Models. |
| `https://github.com/cursor/plugins/blob/main/pstack/<path>` | `<pstack>/<path>` when that file exists. troy-pstack ships the skills, the agents, `docs/guide/`, and `README.md`. Read the local copy and never fetch it. It does not ship `automations/`, `assets/`, the guide images, the `make-bot-ui` skill, or `skills/statechart/scripts/test/`. |
| Transcripts in `~/.cursor/projects/<slug>/agent-transcripts/` | `~/.claude/projects/<slug>/<session>.jsonl`. The slug is the workspace path with every character that is not a letter or a digit changed to `-`, so `/Users/you/proj` is `-Users-you-proj` and `D:\Projects\Troy Voice` is `D--Projects-Troy-Voice`. The newest `.jsonl` directly in that folder is the current session. Its `<session>/subagents/` folder holds subagent transcripts. Read only this workspace's folder. Each line is one JSON record. The first user message is the first line with `"type":"user"`, not line one, and its `message.content` is either a string or a list of blocks. |
| "the `agent-transcripts/` directory the system prompt names" | Claude Code's system prompt names no such folder. Use the transcript folder in the row above. |

## Cursor-only features

Claude Code has no Cursor Automations, Bugbot, Cursor cloud agents, or built-in PR tool. When a step needs one and the table gives no replacement, put one line in your reply, `Skipped in Claude Code: <step>. <reason>.`, then go on to the next step. Do not stop, ask, or retry. When a later step needs what the skipped step made, such as a URL or a key, leave a placeholder and name it in the line. A skill that marks a step `**Not ported to Claude Code:**` means the same thing.

| Cursor | Claude Code |
| --- | --- |
| Cursor Automations: routines, `update_state` routine calls, `api2.cursor.sh/automations` webhooks, routine wakes, and `SendToUser` secret requests | Skip with the line. `automations/benny/TODO.md` sketches how to rebuild the one automation pack on GitHub Actions or a scheduled Claude Code agent. |
| Bugbot | Bugbot comments on a GitHub PR are ordinary review threads, so triage them with the forge command that the step gives. For an automated review in Claude Code, run the `/code-review` skill on the diff when the session has it. Skip a step that starts, waits for, or configures Bugbot when the PR has no Bugbot check or comment. |
| Cursor cloud agents | `environment: "cloud"` maps to a worktree, as in Subagent fields. Skip a step that needs the cloud agent itself, such as its dashboard status or its own machine. |
| A built-in PR tool | Use the forge command that the step gives, such as `gh pr create`. That is not a skip, so write no line. |
| Cursor's `/loop` | Claude Code's `/loop`. `/loop 5m <prompt>` repeats on an interval, and `/loop <prompt>` lets the model pace itself. Not a skip. |
| Cursor custom mode (a skill kept on across turns) | None. The user types the skill again, or puts the standing rule in `CLAUDE.md`. |
| Cursor's built-in `create-skill` | Anthropic's `skill-creator` skill when the session has it. Otherwise write `skills/<name>/SKILL.md` with YAML frontmatter `name` and `description`. |
| Cursor's built-in `babysit` or `/autopilot` | None. Use poteto-mode's Babysit playbook. |
| `cursor-team-kit` skills | Not installed. For `deslop`, run Claude Code's `/simplify` skill when the session has it, else `unslop` and `no-comments`. For `control-ui`, use the project's own verify skill (see `create-verification-skill`) or a browser tool the session has. For `control-cli`, use the project's verify skill or run the CLI through `Bash`. |
| Origin (Cursor's forge) | Use GitHub through `gh`. Skip a step that only exists for Origin. |

## Windows

troy-pstack's owner runs Windows. Claude Code's `Bash` tool there is Git Bash, so the `.sh` helpers and the `statechart` launcher run through it. Write paths with forward slashes in `Bash`. A script with a `#!/usr/bin/env bun` line needs Bun on `PATH`. When Bun is missing, say so and do the step by hand instead.
