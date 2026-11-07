---
name: troy-init
description: Make this folder a troy-mode project, add its language pack, or bring troy-mode's files in it up to date. Runs troy-init's engine and takes its result through one [rules] PR, which it merges once the checks pass. Use only when Troy types /troy-pstack:troy-init.
disable-model-invocation: true
---

# troy-init

troy-init turns a folder into a troy-mode project and keeps troy-mode's files in it current. troy-pstack's F06 design (`docs/troy-mode/design/F06-troy-init.md`) is the source for every step below. Talk to Troy in Troy's language.

| Troy types | Step | Engine command |
| --- | --- | --- |
| `/troy-pstack:troy-init` | Setup | `setup --email <address>` |
| `/troy-pstack:troy-init lang python` or `lang cpp` | Language step | `lang python` or `lang cpp` |
| `/troy-pstack:troy-init upgrade` | Upgrade | `upgrade` |

## The engine

The engine is `${CLAUDE_PLUGIN_ROOT}/troy-mode/init/troy_init.py`. Run it from the project's root with Python 3.11 or newer: `python` on Windows, `python3` elsewhere. It uses the standard library only.

- It changes files and the repository's git config only. It never commits, pushes, or calls GitHub. You do those, in the PR flow below.
- `--dry-run --json` checks and plans without changing anything. The JSON report lists each path with its action, the `conflicts` and `problems` that stop the step, the exact paths to `stage`, the `executable` paths among them, the `email` check, and `next_steps`.
- Exit code 0: done, or a dry run found nothing in the way. 1: stopped before changing anything; the report says why. 2: the engine could not run; show Troy its error.
- `--replace <path>` lets the engine overwrite one file it did not write. Pass it only for files Troy said yes to.
- `--email` is the commit email in Troy's global CLAUDE.md (`~/.claude/CLAUDE.md`), for example `148482542+ZJUCao@users.noreply.github.com`. If it names none, ask Troy.

## Before the engine runs

1. Run the step's engine command with `--dry-run --json`. If the folder is not a git repository yet, run `git init -b main` first; nobody commits on `main` locally (R21). Every step stops on `main`, so for the language step and upgrade, create the step's branch first (PR flow step 2) and run the dry run there. At setup in a folder without `origin`, the dry run's problems name the missing `origin` and the branch `main`; PR flow steps 1 and 2 clear them.
2. Collect everything that has no clear default and ask Troy in one message:
   - Setup with no `origin` remote: whether to create the private GitHub repository `<owner>/<project>`, with the owner from `gh api user --jq .login` and the project name from the folder. Creating it is the only step that reaches outside the project, so always ask.
   - Each path in `conflicts`: whether troy-init may replace it. A file Troy keeps stops the step, so say what that means.
   - Language step: which series the project belongs to, if any (the environment's name and the folders of the other members).
3. If the folder already has commits but no `origin`, stop and ask Troy how to publish them. R21 forbids pushing `main`.

Upgrade: when the dry run says `changed` is false, tell Troy there is nothing to upgrade, run `git switch --detach origin/main`, delete the branch, and stop. Open no PR.

## The PR flow

Each step lands as one `[rules]` PR with one commit (design section 7). F07 runs the same steps when it runs the engine itself.

1. **Repository.** If the folder has no `origin` and Troy said yes: `gh repo create <owner>/<project> --private --add-readme`, then `git remote add origin <url>` and `git fetch origin`. Take the URL for the git protocol gh uses (`gh config get git_protocol -h github.com`): `git@github.com:<owner>/<project>.git` for ssh, `https://github.com/<owner>/<project>.git` for https. GitHub makes the first commit on `main`.
2. **Branch.** `git switch -c troy-mode/init origin/main` for setup, `troy-mode/lang-<name>` for the language step, or `troy-mode/upgrade-<version>` for upgrade.
3. **Engine.** Run the step without `--dry-run`, with `--json` and the `--replace` paths Troy approved. If the report's `email` says the address does not match, set it in this repository: `git config user.email <address>`.
4. **Stage.** `git add -- <path>` for exactly the paths in `stage`, then `git add --chmod=+x -- <path>` for those in `executable` (the git hooks; a Windows checkout does not record the executable bit). Never `git add -A` or `git add .`: files that were there before the step stay out of its PR.
5. **Commit.** One commit whose subject is the PR title (R01): `[rules] Set up troy-mode`, `[rules] Add the Python pack`, `[rules] Add the C/C++ pack`, or `[rules] Upgrade troy-mode to <version>`. No attribution: no `Co-Authored-By` line, no "Generated with" line, and no mention of Claude or Anthropic in the commit, the PR title, or the PR description (R19). The git hooks check this when they are on.
6. **Check.** Write the PR description from `.github/pull_request_template.md`: Why, What, Checks, and Soft-limit reason "None", with the template comment removed. Run `python .troy-mode/checks/troy_check.py pr --base origin/main --title "<title>" --body-file <file>`. Stop on any `fail`. At setup, R19 warns that commit emails are not checked, because `origin/main` has no config yet; that is expected.
7. **PR.** `git push -u origin <branch>`. Then, as its own command, `gh pr create --base main --head <branch> --title "<title>" --body-file <file>`.
8. **Merge.** Wait for the checks once with `gh pr checks <number> --watch`. When all pass, run `git switch --detach`, then merge with `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>`, where `<sha>` is the full commit ID you pushed (R18 lets Claude merge every PR except PR 1 and PR 2 of the first features). Detaching first keeps `gh` from checking out `main` before it deletes the branch; in a worktree, `main` is often checked out elsewhere, and git refuses to check it out twice. When a check fails, stop and report it. Then `git fetch origin`, and record the step in `.troy-mode/progress.md`.

## After setup merges

- **Git hooks.** When the report's `hooks_path` is set, the git hooks are on in this clone. In other clones, troy-pstack's `SessionStart` hook turns them on. When it is null, this troy-pstack has no git hooks yet.
- **Required check.** Ask GitHub whether the repository can use branch protection: `gh api repos/<owner>/<project>/branches/main/protection`. A private repository on a free plan answers 403 ("Upgrade to GitHub Pro"); then say that `troy-mode checks` stays optional. Only if it answers 404 "Branch not protected" or 200, ask Troy, and on yes mark `troy-mode checks` as a required status check.
- **Next.** The requirements (Product Manager), or the architecture (Architect) when `docs/requirements.md` already exists.

## Language step

The language step adds the language pack (troy-pstack's F03) and its CI job, after Troy approved the architecture: `docs/architecture.md` on `origin/main` must have `version` 1.0 or higher. The engine checks this and stops otherwise.

- **Engine command.** `lang python` or `lang cpp`, with these options:
  - `--environment <name>`, and one `--series <folder>` for each other member, when Troy says the project belongs to a series, for example `--environment troy-agent-env --series ../troy-voice`. With no series, leave both out: the environment is named after the project.
  - `--mamba <path>` when `mamba` is not on the PATH and `$MAMBA_EXE` is not set, for example Miniforge's `Library\bin\mamba.exe` on Windows. mamba then also needs `MAMBA_ROOT_PREFIX` set to the Miniforge folder.
  - `--env-prefix <folder>` only when Troy wants the environment in a folder rather than a named one. Trials use it, so they leave no named environment behind.
  - `--package <name>` (Python only) when the package under `src/` should not be the project name in snake case.
  - `--project-name <name>` when the name in a new `pyproject.toml` or `CMakeLists.txt` should not be the folder's name.
- **Dry run.** Its `environment` entry says whether the environment exists and lists the mamba commands the step will run: create it when missing, compile the lock with the environment's uv from every member's manifest, and install the lock. Creating an environment downloads Python and the tools and takes a few minutes. Its `legacy` entry lists existing tests that go into `[tests] legacy`, so R10 does not fail their names; tell Troy which.
- **Stops.** The step stops when `pyproject.toml` already holds one of the pack's tables, or `CMakeLists.txt` does not include `cmake/troy.cmake`; the report's `problems` say what to change. Ask Troy before you change the project's own build file.
- **If mamba or uv fails,** the engine exits 2 and has put the project's files back. Show Troy the error. An environment it created stays.
- **PR flow.** As below, with the branch `git switch -c troy-mode/lang-python origin/main` (or `troy-mode/lang-cpp`) and the title `[rules] Add the Python pack` or `[rules] Add the C/C++ pack`. troy-check's R16 warns that dependency files changed; the pack's own tools need no further approval. Until the first mock PR, the pack's CI job finds no code, skips its code steps, and passes with "No code yet" in its summary.
- **After it merges.** The setup steps that need code, `uv pip install -e . --no-deps` (Python) and `cmake --preset coverage` (C/C++), wait for the first mock: F07 puts them into DV1's brief. Other members of a series get the new lock in their own PRs.

## Upgrade

Upgrade replaces troy-mode's own files (troy-check, the templates, the PR template, the workflow) when nobody edited them since troy-init wrote them, creates the files troy-pstack added, and deletes the ones it dropped. An edited file is a conflict: ask Troy whether to replace it. It brings the R rows of `docs/rules.md` and its mirror up to date and keeps the P rows. It never changes `.troy-mode/config.toml` or the build files; show Troy the report's `differences`, which Troy may take into a rules PR.

## Report

Tell Troy, in Troy's language, what the step did and what it did not do, for example:

```text
Setup is done.
  PR #1 "[rules] Set up troy-mode": troy-check passed (R01, R02, R12, R19, R20), merged.
  Git hooks are on. Branch protection is not available on your plan, so the check stays optional.
  Next: the requirements (Product Manager).
```
