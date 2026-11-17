# 9. Changing troy-mode

| | |
| --- | --- |
| Version | 0.2 |
| Date | 2026-11-16 |
| Source of truth | This English file. [`09-changing-troy-mode.zh-CN.md`](09-changing-troy-mode.zh-CN.md) is the Chinese mirror. |

This page is for work on troy-mode itself, in tstack: by you, or by a Claude Code session you start there. troy-mode's own pipeline does not run here. tstack has its own process, kept on this page so every session finds it ([F10 design D92](../design/F10-docs.md#11-decisions-for-troy)).

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
| tstack's own tools | `troy-mode/dev/`: `check_pairs.py`, `check_links.py`, `check_name.py`, `check_exam.py`, `build_sample.py`, and the sample projects' tests |
| The role exam | `troy-mode/exam/`: `troy_exam.py`, its engine, and its cases (section 9.7) |

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

Use the `tstack` mamba environment's Python, `D:\miniforge3\envs\tstack\python.exe`. Until that environment exists, the `troy-pstack` environment holds the same packages and works the same for tstack ([F19 design section 6.4](../design/F19-rename.md#64-the-mamba-env-d196)). Never use the system Python 3.14, which hides missing imports that CI's Python catches, and never create a `.venv`. With that Python as `python`, run each suite from the repository's root:

```bash
python -m unittest discover -s troy-mode/checks/tests
python -m unittest discover -s troy-mode/init/tests
python -m unittest discover -s troy-mode/hooks/tests
python -m unittest discover -s troy-mode/flow/tests
python -m unittest discover -s troy-mode/exam/tests
python -m unittest discover -s troy-mode/dev/tests
python troy-mode/dev/check_pairs.py
python troy-mode/dev/check_links.py
python troy-mode/dev/check_name.py
```

Each suite must print "Ran N tests" and OK. Do not add `-t`. `check_pairs.py` checks that each English document and its mirror have the same headings, tables, code blocks, markers, and version. `check_links.py` checks that every relative link and anchor in `README.md` and `docs/troy-mode/` resolves. `check_name.py` checks that text outside the history, such as approved designs and change logs, no longer names the plugin's old name ([F19 design section 11.2](../design/F19-rename.md#112-the-name-check)). CI runs all of these on GitHub; the Windows tests job takes about 20 to 25 minutes, and its limit is 45.

## 9.4 Trials

A trial runs troy-mode in nested `claude -p` sessions on your PC, with tstack loaded from the PR branch, on the private repository `ZJUCao/troy-mode-trial`. Your answers are given in the sessions' prompts.

The session copies the PR's head with `git archive` into a folder named `tstack` in its scratchpad, so that the hooks' Read rule `Read(//**/tstack/**)` matches it, and loads it with `--plugin-dir` and a Windows path such as `C:/...`; a Git Bash path such as `/c/...` silently loads nothing. Each nested session also gets `--settings '{"enabledPlugins":{"tstack@tstack":false}}'`, which turns your installed copy off for that session only, so that two copies of the plugin never run together ([F19 design section 3](../design/F19-rename.md#3-probes)).

You gave a standing permission for this on 2026-11-08, and extended it to the name tstack on 2026-11-16, as an `autoMode.allow` rule in tstack's `.claude/settings.local.json` ([F08 design section 11.3](../design/F08-release.md#113-trial-d78)): nested `claude -p` sessions that load tstack may create branches, issues, and PRs, and merge PRs, in `ZJUCao/troy-mode-trial`, without asking. It does not cover:

- any other repository;
- pushing `main`;
- creating or deleting a repository.

If a trial is refused anyway, the session tells you and does not work around it.

## 9.5 Who merges tstack's PRs

Your standing permissions of 2026-11-06:

- **Code PRs** that build a design you approved are merged by the session as soon as every check passes.
- **Status PRs**, which change only status labels, versions, and change-log rows in the requirements, are merged once their checks pass.
- **Designs and requirement changes** are merged by the session after you approve their content in chat. A draft whose questions are still open is never merged.
- **PR branches** may be amended and force-pushed, to keep one commit per PR.

The session merges with `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>`, only when every check passes. Nobody commits on `main` or pushes `main`. tstack's `.claude/settings.local.json` allows `gh pr merge` and denies any `git push` line that mentions `main`, so the push and `gh pr create --base main` run as separate commands. A refused merge is reported to you, never worked around.

## 9.6 A new plugin version

Claude Code updates an installed plugin only when `version` in `.claude-plugin/plugin.json` rises ([F10 design section 6](../design/F10-docs.md#6-the-plugin-version-d89)). So a tstack PR that changes what projects get, such as troy-check, the templates, the packs, the skills, or the roles, raises the version:

- the patch number for a fix, such as 0.2.0 to 0.2.1;
- the minor number for a feature, such as 0.2.0 to 0.3.0.

After it merges, update the installed plugin as [section 1.3](01-install.md#13-update-after-a-new-plugin-version) says: pull tstack's main checkout, update the marketplace and the plugin with the bundled CLI, and restart Claude Code. Each project then takes in the new version with `/tstack:troy-mode upgrade troy-mode`, whose PR title names the version ([section 8.6](08-reference.md#86-problems)). The pilot (F11) relies on this to bring fixes into its project ([F11 design](../design/F11-pilot.md)).

## 9.7 The role exam

A change to the instructions that roles follow passes the role exam before it merges ([F16 design](../design/F16-role-exam.md)). The exam runs the roles on scratch copies of the pilot's project states, once with the PR's base and once with its head, and a fresh session that did not do the task grades the outputs blind.

**Which PRs.** A PR that changes a file of the instruction set: `agents/troy-*.md`, `troy-mode/roles/common.md`, `troy-mode/flow/troyflow/brief.py` and the engine modules it imports, `troy-mode/templates/`, the skills that roles read (`skills/technical-writing/` and `skills/benchmark-checklist/`), the sections "Running a role" and "The summary for Troy" of `skills/troy-mode/SKILL.md`, and the exam's own cases and code in `troy-mode/exam/`. CI's docs job refuses such a PR until its description holds the exam's section with the head's instruction hash ([F16 design section 9](../design/F16-role-exam.md#9-which-changes-must-pass-and-the-pr-d157)).

**How to start it.** From the PR's worktree, with the `tstack` environment's Python:

```bash
python troy-mode/exam/troy_exam.py affected --base origin/main
python troy-mode/exam/troy_exam.py run --base origin/main
```

`affected` lists the cases that the change touches, with no model call. `run` estimates the cost, runs each affected case 5 times with each version, has the judge grade every run, compares the two versions, and writes the report. It reuses the base's runs of the last 14 days when nothing they depend on changed. It takes minutes to hours, so the session waits for it in the background. A PR that fixes a case names it with `--fixes <case>`. After a usage limit, `troy_exam.py resume <exam ID>` goes on.

**The budget.** Up to $60 at list prices, the exam starts without asking. Above that, the session shows you the estimate, the cases, and the time, and starts only on your yes. The exam starts no new run once it has spent 1.5 times its estimate, runs at most two role runs at a time, and gives each run a cap.

**What goes in the PR.** `troy_exam.py block <exam ID>` prints the "Role exam" section, and the session pastes it into the PR's description. Its `Instructions` line must match the PR's head, so a later push that changes the instruction set needs the exam again. A failed exam is not run again on the same head: the head changes, or you accept the failure in chat, and the section then says `failed, accepted by Troy on <date>: <reason>`.

**Where its files live.** `D:\Troy\troy-mode-work` holds the mirrors of the pilot's repository, one environment for each start, each run's scratch project while it runs, the results with every report, and each case's runs. `TROY_EXAM_ROOT` names another folder.
