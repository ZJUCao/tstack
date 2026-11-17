# benny: not ported (TODO)

tstack does not ship benny. This file records what benny is upstream, why it does not run in Claude Code, and how it could be rebuilt. Upstream source: [pstack/automations/benny](https://github.com/cursor/plugins/tree/main/pstack/automations/benny) (pstack 0.15.36, MIT, Lauren Tan).

## What benny does upstream

benny is two Cursor Automations that share one Slack issue channel.

1. **Triage.** It starts on each new top-level report in the source channel. It reads the thread and attachments, classifies the report (bug, performance, feature request, question or feedback, reroute), and traces the likely owning layer. It dedupes against the tracker, updates a confident duplicate, and creates a ticket only for a clear new bug. It posts exactly one reply in the thread, ending in `[benny:bug]`, `[benny:performance]`, or `[benny:other]`.
2. **Reproduce and fix.** It waits for a trusted bug or performance marker in the same thread. It stops if someone already owns the fix, and verifies an existing PR instead of competing with it. It reproduces the exact symptom twice through the real UI with a control adapter and a feature map, and captures screenshots, video, and a state cross-check. After a confirmed repro it may try one bounded root-cause fix and open a **draft** PR, only when before-and-after proof passes.

Shared rules: the channel and thread coordinates never change during a run, benny never posts a root message, only the coordinator posts to Slack (subagents are read-only), every gate fails closed, and benny never merges or deploys.

## Why it is not ported

Every step leans on Cursor-only machinery:

| benny needs | Cursor provides | Claude Code status |
| --- | --- | --- |
| A Slack "new top-level message" trigger | Cursor Automations triggers | No built-in Slack trigger |
| Creating and editing the automations | Cursor's built-in `/automate` and the Automations editor | None |
| Shared skills in the target repo | `.cursor/settings.json` → `plugins.pstack.enabled` | Install tstack instead (see below) |
| Slack read, thread post, file download, edit | Cursor's Slack actions (`prefer_cursor_actions`) | A Slack MCP server, or a bot token in the runner |
| Per-role model slugs | Cursor's model matrix | `opus` / `sonnet` / `haiku` via the `Agent` tool |

## How it could be rebuilt

Pick one trigger. The rest of the design carries over.

### Option A: GitHub Actions with Claude Code (fits a solo project best)

Use GitHub Issues as the intake channel instead of Slack.

- `triage.yml` runs on `issues: opened`. It checks out the repo, installs tstack, and runs Claude Code headless (`claude -p`, or Anthropic's `anthropics/claude-code-action`) with the triage instructions. It answers with one issue comment and one label: `benny:bug`, `benny:performance`, or `benny:other`.
- `reproduce.yml` runs on `issues: labeled` when the label is `benny:bug` or `benny:performance`. It drives the app through the project's own verify skill (make one with `/tstack:create-verification-skill`), attaches evidence as workflow artifacts, and may open a draft PR with `gh pr create --draft`.
- Secrets live in GitHub Actions secrets (`ANTHROPIC_API_KEY`). Give the workflow only `issues: write`, `contents: write`, and `pull-requests: write`. Never allow merge or deploy.

### Option B: a scheduled Claude Code agent (keeps Slack)

- Run Claude Code on a schedule: Claude Code's `/schedule` (cloud routines on a cron), or Windows Task Scheduler / cron calling `claude -p --plugin-dir <tstack>`.
- Each run reads the source channel through a Slack MCP server, keeps a state file of processed message timestamps so a rerun is idempotent, and replies in threads only.
- The repro run is the same as Option A, but it reads the marker from the Slack thread instead of a label.

## Porting checklist

1. Copy upstream `automations/benny/skills/` here and read every file before it ships.
2. Replace each Cursor-only step: the `/automate` flow, `.cursor/automations/benny/` paths (use `.claude/benny/` or `automations/benny/`), `.cursor/settings.json` plugin enabling, Cursor Slack actions, and model slugs.
3. Keep user configuration outside the pack, for example `.claude/benny/config.yaml`, adapted from upstream's `templates/configuration.example.yaml`. Keep secrets out of the repo.
4. Use the project's verify skill and `docs/feature-map.md` as the control adapter and feature map.
5. Keep every safety rule: thread-only replies, one poster, draft PRs only, fail closed, immutable coordinates.
6. Test with a harmless report first, and check that every reply lands in the original thread or issue.

For the voice-assistant project, Option A fits its existing rules: a misunderstood request first becomes an eval scenario in `evals/scenarios/`, and a code bug first becomes a failing test.
