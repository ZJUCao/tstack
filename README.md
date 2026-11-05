# troy-pstack

troy-pstack is Troy's personal Claude Code plugin: a fork of **[pstack](https://github.com/cursor/plugins/tree/main/pstack)** by Lauren Tan ([poteto](https://x.com/poteto)), taken from pstack **0.15.36** (`cursor/plugins` commit `bb68f23`, 2026-11-03). It keeps Lauren's verification-first skills, principles, playbooks, and subagent workflows, and makes them run in Claude Code on Windows.

> **Not affiliated.** troy-pstack is an independent fork. It is not affiliated with, sponsored by, or endorsed by Lauren Tan or Cursor. The names `pstack`, `poteto-mode`, `poteto-agent`, and `poteto-help` are kept only to credit where the work comes from. troy-pstack ships no Cursor logos or branding.

## Credit and license

Almost every skill, playbook, agent, and guide page here is Lauren Tan's work from pstack, used under the MIT License. [`LICENSE`](./LICENSE) keeps her copyright notice and the full permission notice, and adds a line for Troy's modifications, which are under the same license. If you want the original, use upstream pstack, not this fork.

What troy-pstack changes is listed in [How the port works](#how-the-port-works) and in the [skill table](#skill-table).

## Install (local)

In Claude Code:

```
/plugin marketplace add D:/Troy/Projects/troy-pstack
/plugin install troy-pstack@troy-pstack
```

This folder is both the plugin and a one-plugin marketplace (`.claude-plugin/marketplace.json`). To try it for one session without installing, start Claude Code with `claude --plugin-dir D:/Troy/Projects/troy-pstack`.

Claude Code prefixes plugin skills and agents, so type `/troy-pstack:poteto-mode`, `/troy-pstack:setup-pstack`, and so on. The agents are `troy-pstack:poteto-agent` and `troy-pstack:comment-sicko`.

After you edit the plugin, raise `version` in [`.claude-plugin/plugin.json`](./.claude-plugin/plugin.json), then run `claude plugin update troy-pstack@troy-pstack` and restart Claude Code.

## Get started

1. Run `/troy-pstack:setup-pstack`. It reads which models the `Agent` tool accepts, asks for a reasoning budget, and writes `~/.claude/rules/troy-pstack-models.md`. It can also offer to create a project verification skill.
2. Start any task that needs rigor with `/troy-pstack:poteto-mode <task>`. It restates your goal, picks one of its 23 playbooks, and routes to the other skills as the steps need them.
3. Unsure which skill fits? Ask `/troy-pstack:poteto-help <question>`.

The [guide](./docs/guide/README.md) walks through a first real task. It is Lauren's guide, adapted for Claude Code.

## How the port works

troy-pstack starts from the Claude Code copy that upstream already generates (`harness/pstack/claude-code` in `cursor/plugins`), not from a rewrite.

- **Cursor names stay in the skill text.** Skills still say `Task`, `AskQuestion`, `readonly`, Cursor model slugs, and `.cursor/` paths. [`docs/harness/claude-code.md`](./docs/harness/claude-code.md), the adapter, maps each one to Claude Code at run time, and every skill that needs it tells the agent to read it first. This keeps troy-pstack's diff against upstream small, so Lauren's later releases can still be merged.
- **Cursor-only features are adapted or marked.** Where a step needs something only Cursor has, the step now names the Claude Code equivalent (for example Claude Code's `/loop`, `/simplify`, `/code-review`, `skill-creator`, worktree subagents), or it carries an inline `**Not ported to Claude Code:**` marker that says what is missing and why.
- **Models.** Claude Code's `Agent` tool takes only Claude models, so troy-pstack replaces upstream's Grok-plus-Opus matrix. Code delegates, explorers, investigators, and swarm workers use `sonnet`. Judgment, prose, the hardest changes, explainers, and synthesizers use `opus`. Review panels (arena, architect, interrogate) pair `opus` with `sonnet`. `/troy-pstack:setup-pstack` writes these defaults and lets you change any role.
- **Identity.** The plugin, marketplace, model rule, and command prefix are named `troy-pstack`. Skill and agent names stay as upstream has them.
- **Line endings.** Every text file is LF, and [`.gitattributes`](./.gitattributes) keeps it that way, so the shell scripts also run under WSL and macOS.

### Not shipped

| Upstream part | Why |
| --- | --- |
| `make-bot-ui` skill | It only works with Cursor routines (`update_state`, `SendToUser`, `api2.cursor.sh` webhooks) and Grok Bot. |
| `automations/benny/` | It runs on Cursor Automations. [`automations/benny/TODO.md`](./automations/benny/TODO.md) describes how to rebuild it on GitHub Actions or a scheduled Claude Code agent. |
| `assets/logo.png`, `docs/guide/images/*.jpg` | Cursor branding (the guide illustrations use a mascot shaped like the Cursor logo). |
| `skills/statechart/scripts/test/` | A 2.7 MB developer test corpus. The skill does not need it at run time. |
| `.cursor-plugin/plugin.json`, root `plugin.json` | Cursor manifests. Claude Code reads `.claude-plugin/plugin.json`. |

### Windows notes

- `skills/poteto-mode/scripts/watch-pr/watch-pr` (used by the Babysit and Shipping playbooks) needs [Bun](https://bun.sh). Bun is not installed on this machine, so those steps fall back to running `gh pr view` and `gh pr checks` by hand. On its first run the script runs `bun install --frozen-lockfile` in its own folder.
- `skills/statechart/scripts/statechart` runs through Git Bash with Node 24, but its TypeScript hard-codes `/bin/sh` and POSIX process groups, so it does not work on native Windows. Use it under WSL. On first use it installs Java and `tla2tools.jar` through `mise` (sha256-pinned) unless `TLA2TOOLS` and `JAVA` are set.
- `skills/poteto-mode/scripts/worktree-audit.sh` needs `jq` and `rg`. Its newest-chat column now reads Claude Code transcripts, but on Windows it can miss chats from the main checkout.

## Skill table

Legend:

- **as-is**: the file is upstream's text. Any Cursor names in it are mapped at run time by the adapter.
- **adapted**: some lines were changed for Claude Code or for the troy-pstack name.
- **partly not ported**: adapted, and at least one step is marked `**Not ported to Claude Code:**`.
- **not ported**: not shipped.

| Skill | Status | Reason |
| --- | --- | --- |
| `poteto-mode` | partly not ported | Claude model defaults in place of the Grok/Opus matrix, `/simplify` for `deslop`, verify skill for `control-ui`/`control-cli`. In the 23 playbooks, Origin (Cursor's forge) and Cursor cloud-agent URLs are marked not ported. Claude Code's `/loop` replaces Cursor's, and worktree subagents replace cloud VMs. |
| `poteto-help` | adapted | Local install commands, `/troy-pstack:` prefix, local file links, and no Custom Mode. |
| `setup-pstack` | adapted | Rewritten for Claude models: writes `~/.claude/rules/troy-pstack-models.md` with `<model> <effort>` values. |
| `how` | adapted | Model rule path. |
| `why` | adapted | MCP discovery uses Claude Code's `mcp__*` tools. Slack auth goes through `/mcp`. Model rule path. |
| `teach` | partly not ported | Cursor's image-generation tool is marked not ported. It falls back to an MCP image tool or ASCII diagrams. |
| `recall` | as-is | The adapter maps transcript paths and fields. |
| `ketchup` | adapted | Charts come from the session's visualize tool in place of Cursor's `/visualize`. |
| `ketchup-video` | as-is | Needs a local video renderer such as ffmpeg. |
| `bro` | as-is | Plain prompt. |
| `sharpen` | as-is | Plain prompt. |
| `in-your-own-words` | as-is | Plain prompt. |
| `architect` | adapted | Model rule path. |
| `arena` | adapted | Model rule path. The cross-family judge uses `opus` versus `sonnet`. |
| `swarm` | adapted | Model rule path. Cloud workers map to worktree subagents. |
| `interrogate` | as-is | The adapter maps the reviewer panel to `opus` plus `sonnet`. |
| `blast-radius` | as-is | No Cursor-only feature. |
| `automate-me` | adapted | Cursor's built-in `create-skill` becomes Anthropic's `skill-creator`. `AskUserQuestion` limits and the `CLAUDE.md` note for "every turn". |
| `reflect` | adapted | `skill-creator` replaces `create-skill`. Model rule path. |
| `correct` | as-is | No Cursor-only feature. |
| `tdd` | as-is | No Cursor-only feature. |
| `benchmark-checklist` | as-is | No Cursor-only feature. |
| `no-comments` | as-is | The adapter maps `Task` and `comment-sicko`. |
| `typescript-best-practices` | as-is | Claude Code honors its `paths` frontmatter. |
| `figure-it-out` | as-is | The adapter maps the todolist and subagent fields. |
| `show-me-your-work` | adapted | The "different model family" reviewer means a different Claude `model` value. |
| `create-verification-skill` | as-is | The adapter maps `.cursor/skills/` to `.claude/skills/`. |
| `maintain-verification-skill` | as-is | The adapter maps `readonly` and paths. |
| `create-formal-verification-skill` | adapted | Plugin name only. |
| `maintain-formal-verification-skill` | as-is | No Cursor-only feature. |
| `statechart` | adapted | Package renamed, dead test script removed, test corpus not shipped. Needs WSL on Windows. |
| `unslop` | as-is | No Cursor-only feature. |
| `technical-writing` | as-is | No Cursor-only feature. |
| `make-bot-ui` | not ported | Cursor routines and Grok Bot only. |
| 24 `principle-*` skills | as-is | Plain principles. `attack-the-premise`, `boundary-discipline`, `build-the-lever`, `encode-lessons-in-structure`, `exhaust-the-design-space`, `experience-first`, `explain-the-number`, `fix-root-causes`, `foundational-thinking`, `guard-the-context-window`, `laziness-protocol`, `make-operations-idempotent`, `migrate-callers-then-delete-legacy-apis`, `minimize-reader-load`, `model-the-domain`, `never-block-on-the-human`, `outcome-oriented-execution`, `prove-it-works`, `redesign-from-first-principles`, `separate-before-serializing-shared-state`, `sequence-verifiable-units`, `subtract-before-you-add`, `test-behavior-not-implementation`, `type-system-discipline`. |

That is 57 of upstream's 58 skills shipped. Troy chose to keep all of Lauren's personal skills (`poteto-mode`, `poteto-help`, `ketchup`, `ketchup-video`, `bro`, `sharpen`, `in-your-own-words`) under their original names.

### Agents

| Agent | Status | Reason |
| --- | --- | --- |
| `poteto-agent` | adapted | Finds `poteto-mode` under `~/.claude/plugins/` instead of `~/.cursor/plugins/`, reads the adapter, and drops Cursor's `is_background` field. |
| `comment-sicko` | as-is | Plain subagent prompt. |

### Docs

| File | Status | Reason |
| --- | --- | --- |
| `docs/guide/` (11 pages) | partly not ported | Images removed, local install, Claude Code's `/loop`. Cursor Custom Mode, cloud agents, Projects, and benny are marked not ported. |
| `docs/harness/claude-code.md` | adapted | Rewritten as troy-pstack's adapter, with Claude model mapping, Windows notes, and Cursor-only feature table. |

## Make it yours

Lauren's README says it best: `poteto-mode` is her style. Run `/troy-pstack:automate-me` to draft a `troy-mode` skill from your own transcripts, and keep troy-pstack underneath it.

## Pull in upstream changes

1. Sparse-clone `cursor/plugins` with `harness/pstack` checked out.
2. Diff `harness/pstack/claude-code` between commit `bb68f23` (0.15.36) and the new release.
3. Apply that diff here, then rerun the checks in [How the port works](#how-the-port-works): new Cursor-only steps get an adaptation or a `**Not ported to Claude Code:**` marker, and new model slugs are covered by the adapter.
4. Raise `version` in `.claude-plugin/plugin.json`.
