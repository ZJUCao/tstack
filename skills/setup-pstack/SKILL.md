---
name: setup-pstack
description: Configure which Claude models troy-pstack uses per role and at what reasoning budget. Detects the models the Agent tool accepts and writes an always-loaded rule that overrides the skill defaults. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing troy-pstack's model choices.
---

# Setup troy-pstack

In Claude Code, read [the Claude Code adapter](../../docs/harness/claude-code.md) once per session before you follow this skill. It maps the Cursor names in pstack skills to Claude Code.

Write `~/.claude/rules/troy-pstack-models.md`, a rule that sets troy-pstack's model per role. Claude Code loads every `.md` file in `~/.claude/rules/` into each new session, so the rule is always in context. Upstream pstack writes `~/.cursor/rules/pstack-models.mdc` with Cursor model slugs instead. This skill replaces that with Claude Code values.

A role value is `<model> <effort>`, such as `opus xhigh`, or the alias `inherit-parent`. `<model>` is one of the `model` values the `Agent` tool accepts (`opus`, `sonnet`, `haiku`, `fable`), and its family is that same word. `<effort>` is one of the `effort` values (`low`, `medium`, `high`, `xhigh`, `max`). Treat an old `auto` value as `inherit-parent`.

## Steps

### 1. Detect available models

Read the `Agent` tool schema in this session. The detected models are its `model` values, and the detected efforts are its `effort` values. That is the dependable source. If the schema has no `model` or no `effort` field, say so, and write only `inherit-parent` values. Never write a model you have not confirmed is available. `inherit-parent` is always valid even though it is not a detected model.

### 2. Load current state

The default role-to-model mapping is the rule shape shown in step 5 below. If `~/.claude/rules/troy-pstack-models.md` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer AskQuestion over free text. Offer these four options with these exact labels, and name the current budget when the rule records one. With no rule, say that `large` matches the skill defaults.

- `unlimited — max reasoning`
- `large — xhigh reasoning`
- `medium — high reasoning`
- `small — medium reasoning`

**(b) Apply it.** Build the working table from the skill defaults, and on a re-run keep any role you changed by family, list, or alias (`inherit-parent`). `unlimited`, `large`, `medium`, and `small` set the effort of every real value, panel entries included, to `max`, `xhigh`, `high`, or `medium`. The effort is the last token, on the ladder `max` > `xhigh` > `high` > `medium` > `low`. If the target effort is not a detected effort, use the highest detected effort below it. `inherit-parent` does not change. So `unlimited` turns `opus xhigh` into `opus max`, and `small` turns `sonnet xhigh` into `sonnet medium`. `large` keeps the defaults.

**(c) Show the roles and confirm.** Show every role with its value, marking any model not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models plus `inherit-parent` (this role runs on the session model) as the options. Prefer AskQuestion over free text. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena runs one judge. It tries only values from a family other than the parent's, in list order, so order it by preference. An `inherit-parent` value never judges. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

Say plainly what the defaults cost. Upstream gives code work to a fast non-Claude model. troy-pstack gives it to `sonnet` and keeps `opus` for judgment, prose, and the hardest changes. A panel of `opus` and `sonnet` doubles the subagents on each review, so a user on a tight plan may prefer the `medium` or `small` budget, or a one-entry panel.

### 4. Validate

Every model written must be in the detected set, and every effort must be a detected effort. `inherit-parent` always passes. If a chosen value is not available, stop and ask again.

### 5. Write the rule

Write `~/.claude/rules/troy-pstack-models.md` with no frontmatter, so Claude Code loads it in every session. Write the comment lines, a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels poteto-mode uses. Overwrite the whole file so re-runs stay idempotent. Never put the role lines in `CLAUDE.md` or `AGENTS.md`. Shape:

```
# troy-pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# A value is `<model> <effort>` for the Agent tool. `inherit-parent` runs the role on the session model (omit Agent `model`). Alias entries in a panel list still count toward its fan-out.
# budget: large (xhigh)
feature, refactoring: sonnet xhigh
bug-fix: sonnet xhigh
perf-issue: sonnet xhigh
hillclimb: sonnet xhigh
judgment and prose: opus xhigh
hardest tasks: opus xhigh
how explorer: sonnet xhigh
how explainer: opus xhigh
why investigators: sonnet xhigh
why synthesizer: opus xhigh
reflect tooling: sonnet xhigh
reflect judgment, divergent, synthesizer: opus xhigh
arena runners: opus xhigh, sonnet xhigh
arena cross-judge pool: opus xhigh, sonnet xhigh
swarm workers: sonnet xhigh
architect runners: opus xhigh, sonnet xhigh
interrogate reviewers: opus xhigh, sonnet xhigh
```

### 6. Confirm

Tell the user the rule was written and that it applies to new sessions. Re-running this skill updates it.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` or `verify` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /troy-pstack:create-verification-skill." On yes, read `<pstack>/skills/create-verification-skill/SKILL.md` and follow it. On no, move on without pushing.

### 8. Offer a formal verification skill (optional)

Check whether the project already has a formal verification skill (a project skill that runs a model checker, a proof, or another verifier against the code). If not, offer once: "want a formal verification skill, so agents can prove a key property of your code holds in every case in scope, not only the cases tests reach? I can generate one with /troy-pstack:create-formal-verification-skill." On yes, read `<pstack>/skills/create-formal-verification-skill/SKILL.md` and follow it. On no, move on without pushing.
