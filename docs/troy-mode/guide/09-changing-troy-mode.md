# 9. Changing troy-mode

| | |
| --- | --- |
| Version | 0.1 |
| Date | 2026-11-09 |
| Source of truth | This English file. [`09-changing-troy-mode.zh-CN.md`](09-changing-troy-mode.zh-CN.md) is the Chinese mirror. |

This page is for work on troy-mode itself, in troy-pstack: by you, or by a Claude Code session you start there. troy-mode's own pipeline does not run here. troy-pstack has its own process, kept on this page so every session finds it ([F10 design D92](../design/F10-docs.md#11-decisions-for-troy)).

## 9.1 Where things live

| What | Where |
| --- | --- |
| Requirements | [`docs/troy-mode/requirements.md`](../requirements.md) and its mirror |
| One design per feature | [`docs/troy-mode/design/`](../design/), `F01-templates.md` to `F11-pilot.md`, each with its mirror |
| This guide | `docs/troy-mode/guide/` |
| The skills | `skills/troy-mode/SKILL.md`, `skills/troy-init/SKILL.md` |
| The roles | `agents/troy-*.md`, and the Product Manager's instructions in `troy-mode/roles/` |
| The hooks | `hooks/hooks.json` and `troy-mode/hooks/` |
| The engines | `troy-mode/checks/` (troy-check), `troy-mode/init/` (troy-init), `troy-mode/flow/` (the entry skill's engine) |
| What projects get | `troy-mode/templates/`, `troy-mode/lang/` (the language packs), `troy-mode/checks/` |
| troy-pstack's own tools | `troy-mode/dev/`: `check_pairs.py`, `check_links.py`, `build_sample.py`, and the sample projects' tests |

Every new skill and agent name starts with `troy-`, troy-mode edits no upstream file, and the only shared files it touches are `README.md`, `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` ([requirements section 8](../requirements.md#8-non-functional-requirements)).

## 9.2 The build process

Each feature of [requirements section 7.2](../requirements.md#72-feature-list) is built one at a time:

1. **Design.** A design document and its mirror, with every open question listed as a decision with a recommended answer, so you can reply "全按推荐" (all as recommended). No code is written before you approve the design and its PR merges. A change to the requirements also needs your OK.
2. **Tests first.** A separate agent writes the tests from the design alone, before the code exists. The build session reviews them for assertions that cannot fail.
3. **Code**, until every suite passes.
4. **Planted bugs.** One at a time, in a scratch copy, each must make a test fail. A bug that survives gets a test. The counts go in the PR description.
5. **One PR, one commit.** Fixes amend that commit.
6. **A trial**, when the design has one, on the scratch repository `ZJUCao/troy-mode-trial` (section 9.4). Facts the trial finds go into the design's change log.
7. **A status PR**, separate, that updates the feature's status in requirements section 7.2 with the labels of requirements section 7.1 and raises the requirements' version in both languages. A label never says more than what ran (R13).

Decision IDs continue across designs: F11's design ends at D100, so the next design starts at D101.

## 9.3 Checks before a push

Use the `troy-pstack` mamba environment's Python, `D:\miniforge3\envs\troy-pstack\python.exe`. Never use the system Python 3.14, which hides missing imports that CI's Python catches, and never create a `.venv`. With that Python as `python`, run each suite from the repository's root:

```bash
python -m unittest discover -s troy-mode/checks/tests
python -m unittest discover -s troy-mode/init/tests
python -m unittest discover -s troy-mode/hooks/tests
python -m unittest discover -s troy-mode/flow/tests
python -m unittest discover -s troy-mode/dev/tests
python troy-mode/dev/check_pairs.py
python troy-mode/dev/check_links.py
```

Each suite must print "Ran N tests" and OK. Do not add `-t`. `check_pairs.py` checks that each English document and its mirror have the same headings, tables, code blocks, markers, and version. `check_links.py` checks that every relative link and anchor in `README.md` and `docs/troy-mode/` resolves. CI runs all of these on GitHub; the Windows tests job takes about 20 to 25 minutes, and its limit is 45.

## 9.4 Trials

A trial runs troy-mode in nested `claude -p` sessions on your PC, with troy-pstack loaded from the PR branch, on the private repository `ZJUCao/troy-mode-trial`. Your answers are given in the sessions' prompts.

You gave a standing permission for this on 2026-11-08, as an `autoMode.allow` rule in troy-pstack's `.claude/settings.local.json` ([F08 design section 11.3](../design/F08-release.md#113-trial-d78)): nested `claude -p` sessions that load troy-pstack may create branches, issues, and PRs, and merge PRs, in `ZJUCao/troy-mode-trial`, without asking. It does not cover:

- any other repository;
- pushing `main`;
- creating or deleting a repository.

If a trial is refused anyway, the session tells you and does not work around it.

## 9.5 Who merges troy-pstack's PRs

Your standing permissions of 2026-11-06:

- **Code PRs** that build a design you approved are merged by the session as soon as every check passes.
- **Status PRs**, which change only status labels, versions, and change-log rows in the requirements, are merged once their checks pass.
- **Designs and requirement changes** are merged by the session after you approve their content in chat. A draft whose questions are still open is never merged.
- **PR branches** may be amended and force-pushed, to keep one commit per PR.

The session merges with `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>`, only when every check passes. Nobody commits on `main` or pushes `main`. troy-pstack's `.claude/settings.local.json` allows `gh pr merge` and denies any `git push` line that mentions `main`, so the push and `gh pr create --base main` run as separate commands. A refused merge is reported to you, never worked around.

## 9.6 A new plugin version

Claude Code updates an installed plugin only when `version` in `.claude-plugin/plugin.json` rises ([F10 design section 6](../design/F10-docs.md#6-the-plugin-version-d89)). So a troy-pstack PR that changes what projects get, such as troy-check, the templates, the packs, the skills, or the roles, raises the version:

- the patch number for a fix, such as 0.2.0 to 0.2.1;
- the minor number for a feature, such as 0.2.0 to 0.3.0.

After it merges, run `claude plugin update troy-pstack@troy-pstack` and restart Claude Code. Each project then takes in the new version with `/troy-pstack:troy-mode upgrade troy-mode`, whose PR title names the version ([section 8.6](08-reference.md#86-problems)). The pilot (F11) relies on this to bring fixes into its project ([F11 design](../design/F11-pilot.md)).
