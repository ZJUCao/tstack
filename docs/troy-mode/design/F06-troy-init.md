# F06 design: project init (troy-init)

| | |
| --- | --- |
| Feature | F06 in [requirements 1.16](../requirements.md#72-feature-list) |
| Version | 1.7 |
| Date | 2026-11-28 |
| Status | Approved by Troy on 2026-11-06, with D47 to D56. Troy approved the R12 change of section 8 on 2026-11-07. Version 1.5 adds D213, which Troy approved on 2026-11-18 as tstack issue #48. Version 1.6 adds D289, the follow-up of D213 for the engine's other uv commands, approved under Troy's standing yes of 2026-11-22. Version 1.7 adds D291 to D295, R21's branch rule on GitHub (requirements 1.71), which Troy approved on 2026-11-28: D293 as B, R21's ruleset only, and the others as recommended. |
| Source of truth | This English file. [`F06-troy-init.zh-CN.md`](F06-troy-init.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F06 turns a folder into a troy-mode project and keeps troy-mode's files in it current. It delivers one skill, `/troy-pstack:troy-init`, and the engine behind it, with three steps:

1. **Setup** (requirements 5.1 step 2): the marker folder with the config, troy-check and its git hooks, the templates, and the progress file; the rules table; the PR template; and the CI workflow with troy-check's job.
2. **Language step** (5.1 step 4), after Troy approves the architecture: the language pack from F03 and its CI job.
3. **Upgrade** (F02 D8): troy-mode's own files brought to the plugin's current version.

Each step lands as one `[rules]` PR with one commit. troy-init opens it and merges it once its checks pass (D53). Before setup's PR, and before an upgrade's when it is missing, troy-init also adds R21's branch rule on GitHub where GitHub allows it (section 4.7).

F06 does not write requirements, architecture, or any other project document (the roles, F04). It does not start roles or run the feature loop (F07). It writes no permission rule for the plugin's files, because F05's hook allows those reads (F05 D45).

## 2. Location

```text
skills/
  troy-init/
    SKILL.md                  the skill Troy types (section 3.1)
troy-mode/
  init/
    troy_init.py              the engine's entry point (section 3.2)
    troyinit/                 internal modules (the Developer's choice)
    tests/                    unit tests (section 11.1)
```

- The engine uses Python 3.11 or newer and the standard library only, like troy-check (F02 D7).
- `SKILL.md` sets `disable-model-invocation: true`, as requirements section 8 asks, so it runs only when Troy types it. F07 cannot call such a skill, so F07 runs the engine directly (section 10).
- The skill names the engine as `${CLAUDE_PLUGIN_ROOT}/troy-mode/init/troy_init.py`. Claude Code replaces `${CLAUDE_PLUGIN_ROOT}` in a plugin skill's text.

## 3. Commands

### 3.1 The skill

| Command | Step |
| --- | --- |
| `/troy-pstack:troy-init` | Setup |
| `/troy-pstack:troy-init lang python` or `lang cpp` | Language step |
| `/troy-pstack:troy-init upgrade` | Upgrade |

The skill runs the engine with `--dry-run --json` first. Every step stops on `main` (sections 4.1 and 5.1), so for the language step and upgrade the skill creates the step's branch (section 7, step 2) before the dry run, and deletes it again when upgrade has nothing to change. At setup in a folder without `origin`, the dry run's problems name the missing `origin` and the branch; section 7's first two steps clear them. It asks Troy, in one message and in Troy's language, only what has no clear default: whether to create the private GitHub repository, with R21's branch rule where Troy's plan allows it (D52, D292), whether to add R21's branch rule to a repository that already exists (D291), whether to replace a file troy-init did not write (D48), and the environment's series for the language step. It then runs the engine, takes the result through the PR flow of section 7, and reports what it did and what it did not do.

### 3.2 The engine

```text
python troy_init.py setup   [--project-name <name>] --email <address> [common options]
python troy_init.py lang    (python | cpp) [--project-name <name>] [--environment <name>]
                            [--series <folder>]... [--package <name>] [--mamba <path>]
                            [--env-prefix <path>] [--no-env] [common options]
python troy_init.py upgrade [common options]
python troy_init.py branch-rule [--rules <file>] [--rulesets <file>] [--repo <path>] [--json]

common options: [--repo <path>] [--date <YYYY-MM-DD>] [--replace <path>]... [--dry-run] [--json]
```

| Option | Meaning |
| --- | --- |
| `--project-name` | The name in the rules table and the build files. Default: the repository folder's name. |
| `--email` | The commit email for R19. The skill passes the one in Troy's global CLAUDE.md. |
| `--environment`, `--series` | The mamba environment and the folders of the series' members (F03 design 8.1). Default: the project name, and `.`. |
| `--package` | Python only: the package under `src/`. Default: the project name in snake case. |
| `--mamba` | mamba's path, when it is not on the PATH or in `$MAMBA_EXE`. |
| `--env-prefix` | Create the environment at this folder in place of a named one. Trials use it, so they leave no named environment behind. |
| `--no-env` | Create no environment and compile no lock. Tests and `build_sample.py` use it. |
| `--date` | The date written into the files. Default: today. |
| `--replace` | A path troy-init may overwrite although it did not write it (D48). |
| `--dry-run` | Check and plan only. Nothing changes. |
| `--json` | Print the report as JSON. |
| `--rules` | `branch-rule` only: a file with GitHub's answer about the rules in force on `main` (section 4.7). Without it, no rule is on yet. |
| `--rulesets` | `branch-rule` only: a file with GitHub's list of the repository's rulesets (section 4.7). Without it, the repository has none. |

The engine changes files and the repository's git config only. It never commits, pushes, or calls GitHub: the main session does that (F04 D29). `branch-rule` changes nothing: it reads GitHub's answer from a file the skill saved, and says which rulesets the skill should add (section 4.7).

### 3.3 Report and exit codes

The report lists each path with its action (`create`, `replace`, `append`, `edit`, `delete`, or `keep`), every conflict, and the next steps. With `--json`, it also lists the exact paths to stage.

| Exit code | Meaning |
| --- | --- |
| 0 | Done, or a dry run found nothing in the way. |
| 1 | Stopped before changing anything: a precondition does not hold, or a file is in conflict. The report says which. |
| 2 | The engine could not run: bad options, not a git repository, or a git error. |

## 4. Setup

### 4.1 Before it starts

Setup stops unless:

- the folder is the root of a git repository, with an `origin` remote whose `main` branch exists and has been fetched. The skill makes `origin` a GitHub repository (D52). The engine does not care where it lives, so tests can use a local one;
- the current branch is not `main` (the PR flow creates `troy-mode/init` from `origin/main` first);
- the repository has no `.troy-mode/` folder yet (otherwise use `upgrade`);
- no file setup would write exists, unless it is named with `--replace` (D48).

Setup can run before or after the Product Manager writes the requirements. It never touches `docs/requirements*.md`, and the PR flow stages only setup's own files, so documents written before setup stay out of its PR.

### 4.2 Files

| Path in the project | From troy-pstack | Notes |
| --- | --- | --- |
| `.troy-mode/config.toml` | `troy-mode/checks/config.default.toml` | Filled in as section 4.3 says. |
| `.troy-mode/checks/` | `troy-mode/checks/`, without `tests/`, `workflow.yml`, `config.default.toml`, and caches | troy-check and F05's `git-hooks/`. |
| `.troy-mode/templates/` | `troy-mode/templates/` | Every template and the README, in both languages, unchanged. Roles fill them from here (F04 common rule 7). |
| `.troy-mode/install.toml` | Written by setup | Section 4.6. |
| `.troy-mode/progress.md` | `troy-mode/templates/progress.md`, filled in | Local and git-ignored (Q8). Stage "setup", next action "requirements" or "architecture". |
| `docs/rules.md`, `docs/rules.zh-CN.md` | `troy-mode/templates/rules.md` and its mirror | Section 4.4. |
| `.github/workflows/troy-mode.yml` | `troy-mode/checks/workflow.yml` | troy-check's job. The language step adds the pack's job. |
| `.github/pull_request_template.md` | `troy-mode/templates/pull-request.md` | Unchanged. R20 does not scan `.github/`. |
| `.gitignore` | Lines added | `.troy-mode/progress.md`. The file is created when it does not exist. |

- Every path is in the `config` class of F02's built-in patterns, so the setup PR is a valid `[rules]` PR.
- Files troy-init creates are written with LF line endings. A file it edits in place, such as an existing `.gitignore`, keeps the line endings it has in the working tree: in a Windows checkout with `core.autocrlf`, that is CRLF, and git still commits LF.
- The git hook scripts are staged with `git add --chmod=+x`, because a Windows checkout does not record the executable bit.

### 4.3 The config

`.troy-mode/config.toml` is F02's commented default file, with these values filled in:

```toml
[identity]
commit_email = "148482542+ZJUCao@users.noreply.github.com"

[paths]
# The patterns of every language pack, so that a pack's files already have
# their classes when the language step's PR is checked (F06 design D49).
config = [".clang-format", ".clang-tidy", "include/troy/not_implemented.h"]
dependencies = ["pyproject.toml", "environment.yml", "requirements*.lock", "requirements*.in",
                "CMakeLists.txt", "**/CMakeLists.txt", "cmake/**", "CMakePresets.json"]
tests = ["**/test_*.py", "**/*_test.py", "**/conftest.py", "**/*_test.cc", "**/*_test.cpp"]
lock = ["requirements*.lock"]
```

- `commit_email` comes from `--email`. When the repository's `git config user.email` differs, the report says so and the skill sets the repository's own `user.email` to it, so the next commit passes R19.
- The `[lang]` table stays as the default file's comments until the language step.
- **Why every pack's patterns (D49).** troy-check reads the path classes from the PR's merge base, so a PR cannot loosen the rules that judge it (F02 design 3.1). Without these patterns, the language step's `pyproject.toml` or `CMakePresets.json` would be `source` at its merge base, and a `[rules]` PR may not change source (R02). A Python project's config then also names C/C++ files, which it does not have.

### 4.4 The rules table

Setup fills in the project's name and the date, and removes every template comment, in `docs/rules.md` and its mirror. Both keep `version` "1.0". The setup commit then passes R12 and R20.

### 4.5 git and GitHub settings

- **Git hooks.** Setup sets `core.hooksPath` to `.troy-mode/checks/git-hooks` when that folder exists (F05 D44). In other clones, F05's `SessionStart` hook sets it.
- **Branch rule.** Before the setup PR, the skill adds R21's ruleset on `main` where GitHub allows it (section 4.7).
- **No required check (D293).** troy-init no longer marks `troy-mode checks` as required on GitHub. The step that version 1.6 ran after the setup PR merged, which asked GitHub whether classic branch protection was available and then offered to mark the check required (F02 D14), goes. troy-mode's merge step still merges a PR only when its checks pass (R18, F02 D14).

Nothing else in git or GitHub changes.

### 4.6 The install record

`.troy-mode/install.toml` records the troy-pstack version from `.claude-plugin/plugin.json`, the troy-pstack commit when the plugin folder is a git checkout, the date of each step, the language pack, and a `[files]` table with the SHA-256 hash of every file troy-init owns. troy-init owns the files it copies whole: troy-check, the templates, the PR template, the workflow, and the pack's whole files. Upgrade uses the hashes to tell an unchanged file from one someone edited (D54). `config.toml`, the rules table, `.gitignore`, and the build files belong to the project once written.

### 4.7 R21's branch rule (D291 to D293)

R21 says every change reaches `main` through a PR. The git hooks refuse a commit on `main` and a push of `main` in every clone where they are on (F05 D44). On GitHub, Troy decided on 2026-11-28 that a branch rule, not a CI check, enforces it, because a CI check runs only on PRs and cannot see a direct push (requirements 1.71).

**What GitHub gets.** One repository ruleset, the same as the one Troy's session added by hand to `ZJUCao/recipe-menu` on 2026-11-28 (id 28299856) (D293):

| Field | Value |
| --- | --- |
| Name | `R21: main only through PRs` |
| Target and enforcement | `branch`, `active` |
| Bypass actors | None |
| Condition | `~DEFAULT_BRANCH`, so it follows `main` |
| Rules | `deletion`; `non_fast_forward`; `pull_request` with 0 approvals, and no code owner review, last-push approval, stale-review dismissal, or required thread resolution |

- The body is a plugin file, `troy-mode/init/rulesets/r21.json`. It is not copied into the project.
- With no bypass actor, Troy cannot push `main` either, although Troy is the repository's admin. Only Troy changes or removes a ruleset, in GitHub's settings.
- Every merge method stays allowed. troy-mode merges by rebase (section 7, step 8), and Troy may merge on GitHub.
- It requires no status check (section 4.5).
- GitHub fills in the parameters a body leaves out with its defaults. recipe-menu's ruleset shows `require_extra_approval_for_unattributed_changes` as true, which was not in the request that created it.

**Where GitHub allows it (D292).** GitHub enforces rulesets on public repositories on every plan, and on private ones only with a paid plan such as Pro, which the GitHub Education pack includes. Classic branch protection comes with the same plans. troy-init cannot read the plan, because gh's token lacks the `user` scope, and the plan can change: on 2026-11-07 the then-private `ZJUCao/troy-mode-trial` answered the probe below with 403 (F10 guide, `02-start.md`), and on 2026-11-28 two of Troy's private repositories answered it with 404. So the skill asks GitHub for each repository: `gh api repos/<owner>/<project>/branches/main/protection` answers 403 with a message that names the plan, such as "Upgrade to GitHub Pro or make this repository public", where the plan has no branch protection, and 404 "Branch not protected" or 200 where it has.

**A repository that already has rulesets.** troy-init adds its ruleset beside them, and never changes or deletes one. GitHub applies every active ruleset together, so a stricter rule that is already there still holds: one that requires an approval, for example, makes troy-mode's merges wait for that approval. A ruleset that is not in force, such as one with enforcement `disabled`, changes nothing and stays as it is. On 2026-11-28, `ZJUCao/troy-voice` had such a ruleset, "protect", created on 2026-11-06. The skill's question lists the repository's rulesets.

**The engine's part.** `troy_init.py branch-rule --rules <file> --rulesets <file> --json` reads two answers of GitHub: `gh api repos/<owner>/<project>/rules/branches/main`, the rules in force on `main` from every active ruleset, and `gh api repos/<owner>/<project>/rulesets`, every ruleset of the repository with its name and enforcement. It reports:

- `r21`: true when the rules in force hold `deletion`, `non_fast_forward`, and `pull_request`, from any ruleset, so a rule Troy added by hand counts;
- `existing`: the repository's rulesets, each with its ID, name, and enforcement;
- `add`: when `r21` is false, R21's ruleset, with its name and its body's absolute path;
- `held`: when `r21` is false and a ruleset of the repository already has R21's name, for example one that Troy turned off, R21's ruleset goes here and not to `add`. troy-init never adds a second ruleset of that name and never turns the existing one on; the report names it for Troy.

Without `--rules`, `r21` is false, and without `--rulesets`, `existing` is empty. A file that is not a JSON list is exit code 2. The engine calls no one; the skill runs `gh`.

**The skill's part.** At setup and at upgrade, in step 1 of the PR flow (section 7), before the step's branch and PR:

1. **Probe.** `gh api repos/<owner>/<project>/branches/main/protection`. A 403 whose message names the plan ends this part, with no question: the skill says that GitHub's plan has no branch rules for this private repository, so R21 rests on the local hooks. On any answer other than 404 or 200, it reports GitHub's message and goes on without the rule.
2. **Read.** Both answers of the engine's part, saved to files in the git dir, then `branch-rule --rules <file> --rulesets <file> --json`. When `add` is empty, the rule is already on: report that, name any `held` ruleset, and skip the rest. When a read fails, report GitHub's message and go on without the rule.
3. **Ask.** Troy's yes comes from the one message of section 3.1. For a new repository, D52's question covers it (D292). For an existing one, the skill asks whether to add R21's ruleset to `main` of `<owner>/<project>`, says what it does, and lists `existing`, which stay as they are. On no, it goes on without the rule.
4. **Add.** For the entry of `add`: `gh api -X POST repos/<owner>/<project>/rulesets --input <body>`, with the body named by its absolute path, so that F05's hook can read it before the call (F05 D200). A 403 that names the plan ends this part with item 1's message. On any other error, it reports GitHub's message and goes on without the rule.
5. **Check.** It reads the rules again, as in item 2, and reports the rule as on only when `add` is now empty. When GitHub accepted a ruleset that is not in force, it reports that with the ruleset's link and leaves it to Troy.

When the agent's permissions refuse a call, for example when auto mode denies the POST, the skill stops and asks Troy. It never works around a refusal: no other API call, no settings page, no `--admin` merge. troy-init never changes or deletes a ruleset, never adds a bypass actor, and never uses classic branch protection. The language step does not look at the rules.

**F05's hook.** In the main session, the hook lets a `gh api` call that changes GitHub through when the text it sends passes R19's check (F05 D200). With `--input <file>`, that text is the file, here a JSON body with no attribution. At setup the project has no `.troy-mode/` yet, so the hook does nothing. Subagents may run only read-only `gh` commands, and no role runs this step.

## 5. Language step

### 5.1 Before it starts

The language step stops unless:

- setup is done and no pack is installed;
- `docs/architecture.md` on `origin/main` has a `version` of 1.0 or higher, which means Troy approved it (F01 design section 4);
- the language has a pack (F03): `python` or `cpp`;
- the current branch is not `main`, and no file the step would write exists, unless it is named with `--replace`.

### 5.2 Python

| Path | Action |
| --- | --- |
| `.troy-mode/config.toml` | The `[lang]` table gets the pack's values: `name`, `source_roots`, `environment`, and `series`. `[tests] legacy` lists existing tests (section 5.5). |
| `environment.yml` | The pack's file, with the environment's name. |
| `pyproject.toml` | When it exists, the pack's tables are appended. When it does not, it is created from a new pack file, `pyproject-project.toml` (`[build-system]` with hatchling, `[project]` with the name, version 0.1.0, Python 3.13 or newer, and no dependencies, and the wheel's package `src/<package>`), followed by the pack's tables. |
| `requirements-dev.lock` | Compiled (section 5.4). |
| `.github/workflows/troy-mode.yml` | The pack's `workflow-job.yml` added under `jobs:`. |
| `.gitignore` | `reports/`, `.coverage`, `__pycache__/`, and the caches of mypy, pytest, and ruff. |

The step stops when `pyproject.toml` already holds a table that the pack's tables add, such as `[tool.ruff]`, and lists the tables.

### 5.3 C/C++

| Path | Action |
| --- | --- |
| `.troy-mode/config.toml` | The `[lang]` table gets `name`, `include_dirs`, `environment`, and `series`. `[tests] legacy` lists existing tests. |
| `environment.yml`, `requirements-tools.in` | The pack's files, with the environment's name. |
| `requirements-tools.lock` | Compiled (section 5.4). |
| `CMakePresets.json`, `cmake/troy.cmake`, `.clang-format`, `.clang-tidy`, `include/troy/not_implemented.h` | Copied. |
| `.troy-mode/lang/cpp/Doxyfile` | Copied. |
| `CMakeLists.txt` | When it exists, the step checks that it includes `cmake/troy.cmake` and stops with the line to add if not. When it does not, it is created from a new pack file (`cmake_minimum_required(VERSION 3.28)`, `project(<name> C CXX)`, and `include(cmake/troy.cmake)`). |
| `.github/workflows/troy-mode.yml` | The pack's job added under `jobs:`. |
| `.gitignore` | `build/` and `reports/`. |

### 5.4 Environment and lock (D51)

On Troy's PC, the language step follows the pack README's setup:

1. It creates the series environment with `mamba env create -f environment.yml` when it does not exist. mamba comes from `--mamba`, the PATH, or `$MAMBA_EXE`.
2. It compiles the lock with that environment's uv, from the manifests of every member of the series, and writes it into this project. uv runs with `UV_LINK_MODE=copy`, and with the cache folder of the next paragraph.
3. It installs the lock into the environment.

**uv's cache folder (D213).** uv's default cache can be closed to the step: in the desktop app's sandbox, the pilot's first lock compile failed because uv could not write it (tstack issue #48). So when `UV_CACHE_DIR` is not set, or is empty, every mamba and uv command of this section runs with `UV_CACHE_DIR` set to the folder `troy-mode-uv-cache` in the system temp folder, the folder that Python's `tempfile.gettempdir()` returns. uv creates the folder when it is missing. A value that is already set is passed on unchanged. F07's `troy_flow.py series` (F07 design 8.7, D66), which plans the series lock with this section's functions, follows the same rule: when `UV_CACHE_DIR` is not set, or is empty, in the engine's environment, both its commands start with `UV_LINK_MODE=copy UV_CACHE_DIR=<folder>`, with the folder quoted for the shell; when it has one, they start with `UV_LINK_MODE=copy` alone, and the shell that runs them passes the value on. The engine's other uv commands follow the same rule (D289): the first mock's `uv pip install -e . --no-deps` among the checks that `brief` gives (F07 design 6.1), also in a team's brief, where it installs the main checkout, and the same install that a real run gives as the fix of its `program-not-found` problem (F12 design 5.4). Each starts with `series`' variables, before `mamba run`. The problem's message shows the folder as `<uv cache>`, as a real run shows the environment's folder as `<environment>`, so that no local path reaches the PR, and its `fix` holds the command with the folder itself.

The steps that need code, `uv pip install -e . --no-deps` and `cmake --preset coverage`, wait for the first mock: F07 puts them into DV1's brief. Other members of the series get the new lock in their own PRs (F03 design 8.1). `--no-env` skips this section.

### 5.5 Projects that already have code (Q6)

When the project already has test files that match the pack's test patterns, the language step lists them in `[tests] legacy`, so R10 does not fail their names, and reports the list. They must still pass. Old code is not checked against R04 to R07 or R11 until it changes, as Q6 says.

### 5.6 The pack's CI job before code exists (D50)

The pack's job runs on every PR, the design and test plan PRs of the first feature included. Until the first mock PR, the project has no code, and the job's tools fail on nothing: the Python pack's `mypy` cannot read a missing `src`, and `coverage xml` has no data to report.

So both packs' `workflow-job.yml` get a first step that asks `git ls-files` whether the PR's head has any source file under the pack's roots (`src/` for Python, and `src/` or `include/` other than `include/troy/` for C/C++). When it has none, every later step is skipped and the job passes with the note "No code yet" in its summary. That also saves the environment's setup on documentation PRs. From the first mock on, the job always runs in full.

## 6. Upgrade (D54)

Upgrade brings troy-mode's files in a project to the plugin's current version, in a `[rules] Upgrade troy-mode to <version>` PR.

| What | How |
| --- | --- |
| Files troy-init owns | Replaced with the plugin's versions when their hash still matches the install record. A file edited since is a conflict: upgrade stops and lists it, unless it is named with `--replace`. Files the plugin added are created. Files it dropped are deleted when unchanged. |
| The workflow | Rebuilt from F02's workflow and the pack's job, under the same hash rule. |
| `docs/rules.md` and its mirror | Every R row is replaced by the template's. Existing rows keep their "Since" date and new rows get today's. P rows stay. `version` rises by one minor step in both, and `updated` changes. |
| `config.toml`, appended `pyproject.toml` tables, `environment.yml`, `CMakeLists.txt` | Never changed. The report lists where they differ from the plugin's current pack files, for Troy to take into a rules PR. |
| `.troy-mode/install.toml` | Rewritten. |
| R21's branch rule on GitHub | Not a file. When GitHub lists a ruleset of section 4.7 as missing on `main`, the skill asks Troy in upgrade's one message and adds it before the upgrade's PR (D291). recipe-menu's hand-made ruleset counts as R21's, so it gets nothing. |

Every path upgrade changes is in the `config` or `dependencies` class, so its PR is a valid `[rules]` PR.

## 7. The PR flow (D53)

The skill runs these steps around the engine. F07 runs the same steps when it runs the engine itself.

1. **Repository and branch rule.** If the folder is not a git repository, `git init -b main`. If it has no `origin`, the skill asks Troy once whether to create a private GitHub repository under Troy's account, named after the project, with R21's branch rule where Troy's plan allows it (D292). On yes: `gh repo create <owner>/<name> --private --add-readme`, then `git remote add origin` and `git fetch origin`. GitHub makes the first commit on `main`, so nobody commits on `main` locally (R21, D52). Then, at setup and at upgrade, R21's branch rule (section 4.7, D291).
2. **Branch.** `git switch -c troy-mode/init origin/main`, or `troy-mode/lang-<name>`, or `troy-mode/upgrade-<version>`. The language step and upgrade create it before their dry run (section 3.1).
3. **Engine.** Run the step.
4. **Stage.** `git add` exactly the paths the engine's report lists, with `--chmod=+x` for the git hooks. Never `git add -A`.
5. **Commit.** One commit whose subject is the PR title (R01): `[rules] Set up troy-mode`, `[rules] Add the Python pack` or `[rules] Add the C/C++ pack`, or `[rules] Upgrade troy-mode to <version>`. F05's `commit-msg` hook checks it (R19).
6. **Check.** Run `troy-check pr` with the title and description. Stop on any `fail`.
7. **PR.** `git push -u origin <branch>`, then `gh pr create --base main` with the description from the PR template: Why, What, Checks, and Soft-limit reason "None".
8. **Merge.** Wait for the checks once with `gh pr checks <number> --watch`. When all pass, run `git switch --detach`, then merge with `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>`, as R18 lets Claude merge every PR except PR 1 and PR 2 of the first features. Detaching first keeps `gh` from checking out `main` before it deletes the branch. When one fails, stop and report it. Then `git fetch origin`, and record the step in the progress file.

```text
Troy:  /troy-pstack:troy-init
Claude: This folder has no GitHub repository. Create the private repository
  ZJUCao/habit-tracker, with R21's branch rule on main where your GitHub plan allows it
  (changes only through PRs, no force push or deletion)?
Troy:  Yes.
Claude: Setup is done.
  Repository: created ZJUCao/habit-tracker (private). R21's branch rule is on main.
  PR #1 "[rules] Set up troy-mode": troy-check passed (R01, R02, R12, R19, R20), merged.
  Git hooks are on.
  Next: the requirements (Product Manager).
```

## 8. Changes to earlier features

When F06 is built, it also changes:

- **F03's packs.** Both `workflow-job.yml` files get the step of section 5.6, and the sample workflows that mirror them follow, so `test_python_pack.py` and `test_cpp_pack.py` keep comparing them. The C/C++ config fragment adds `include/troy/not_implemented.h` to `config` (D49). Each pack gains its new-project build file and the README rows for it. F03's design gets a change-log row.
- **`build_sample.py`.** It builds each sample with the functions that write troy-init's files, without the preconditions of sections 4.1 and 5.1 and without the environment, in place of its own `install_pack`, so the samples are set up exactly as troy-init sets up a project. It gains a sample state with setup and the language step but no code, on which the pack's job must pass with its code steps skipped.

- **troy-check's R12.** Files under `.troy-mode/` are not documents for R12, as R20 already does not scan them (F02 design 6.7). Setup copies the templates there unchanged, and their headers hold markers and share `troy-doc` IDs with the project's documents, so without this every setup PR and every later document PR would fail R12. Found while building part 1, and approved by Troy on 2026-11-07. F02's design records it in its version 1.2.

F01, F04, and F05 do not change.

R21's branch rule (version 1.7) changes:

- **The rules template and two others (F01, D294).** In `troy-mode/templates/rules.md` and its mirror, R21's Enforced by takes the requirements' cell of 1.71. R17 and R18 take the meaning that F18 gave them in the requirements: the Architect rules at round 3, and spot checks. R24, which F20 added to the requirements, gets its row, and the comment and the change log name R01 to R24. The guidance comments of `feature-design.md` and `test-plan.md` and their mirrors say that the Architect rules after round 3 (R17). Upgrade then carries the new rows into each project (section 6).
- **The role exam (F16, D294).** `troy_exam.py affected` counts a plugin template as a case's input only when the case's project has no file of that name under `.troy-mode/templates/`, or when the case's brief names the template's path. Roles fill templates from the project's copy (F04 common rule 7), which the case's start commit fixes. The instruction set and its hash keep every template (F16 design 9.1), so a template PR still carries the exam's section. This lands first, in its own PR with its own tests, and F16's design records it.
- **The entry skill (F07).** Its project setup names R21's branch rule among troy-init's questions, and its upgrade adds the rule when it is missing, through troy-init's PR flow. Neither is a role section, so no exam case is affected.
- **The guide (F10).** `02-start.md` shows the new question and report in place of the required-check step. `06-rules.md` and `README.md` count R01 to R24, and `08-reference.md` gets R24's row.

## 9. How F06 maps to the requirements

| Requirement | Where F06 covers it |
| --- | --- |
| F06 row: marker folder, document skeleton, rules table, progress file | Sections 4.2 and 4.4. The document skeleton is the templates in `.troy-mode/templates/`. |
| F06 row: after the architecture is approved, the language pack and the CI workflow | Section 5. troy-check's job arrives earlier, at setup (section 4.2, D48), so the requirements and architecture PRs are checked too |
| 5.1 steps 2 and 4 | Sections 4 and 5 |
| F02 D8: copy the checks, record the version, upgrade by rerunning troy-init in a `[rules]` PR | Sections 4.2, 4.6, and 6 |
| F02 D14: mark the check required when the repository allows it | Section 4.5. Dropped by D293: troy-init no longer marks the check required, and troy-mode's merge step still waits for it (R18). |
| R01, R02, R12, R19, R20 on troy-init's own PRs | Sections 4.2, 4.4, and 7 |
| R18: Claude merges what is not PR 1 or PR 2 of the first features | Section 7, step 8 |
| R21: no commit on `main` | Section 7, steps 1 and 2 |
| R21's Enforced by (requirements 1.71): a branch rule on `main` that troy-init adds where GitHub allows it | Section 4.7 (D291 to D293) |
| Q6: old code is fixed when touched | Section 5.5 |
| Q8: the progress file is local | Section 4.2 |
| Section 8, Python environments | Section 5.4 |
| Section 8, new skills run only when Troy types them | Section 2 |

## 10. How F05 and F07 use F06

**F05.** Setup copies the git hooks with troy-check and turns them on. F05's `SessionStart` hook turns them on in other clones. Because F05's hook allows reads of the plugin's files (F05 D45), setup writes no permission rule. If Troy chooses F05 D45 B instead, setup writes `Read(<plugin folder>/**)` into `.claude/settings.local.json` and git-ignores that file.

**F07.**

- It runs the engine directly, because it cannot call a skill marked `disable-model-invocation`, and then the PR flow of section 7. It runs setup when a project has no `.troy-mode/`, and the language step after the architecture's PR merges.
- It opens the requirements PR after the setup PR merges, so troy-check's job checks the requirements too.
- It puts the setup steps that need code (section 5.4) into DV1's brief.
- Once a project is set up, roles fill templates from `.troy-mode/templates/`, and F04 common rule 7's fallback to the plugin's templates is not needed.

## 11. How F06 is checked

### 11.1 Tests

Tests use `unittest` and the standard library. A separate agent writes them from this design before the engine exists. Each test builds a temporary git repository with a local bare `origin`, made with `git clone --bare` from a repository that already has a commit, so no test pushes `main`. The tests live in `troy-mode/init/tests/`, and `troy-checks-tests.yml` runs them on Linux and Windows for every PR that changes `troy-mode/init/`, `troy-mode/checks/`, `troy-mode/templates/`, `troy-mode/lang/`, or `skills/troy-init/`.

| Group | Cases include |
| --- | --- |
| Setup | Every file of section 4.2 with the content section 4 gives. No marker and no template comment is left in the rules table. The config holds the email and every pack's patterns. The install record's hashes match the files. `.gitignore` is created or added to. `core.hooksPath` is set only when `git-hooks/` exists. A dry run changes nothing. |
| Preconditions | Each condition of sections 4.1 and 5.1 stops the step with exit code 1 and changes nothing: no `origin/main`, on `main`, already set up, an existing file, an architecture below 1.0 on `origin/main`, a second pack. `--replace` lets one named file through. |
| Its own PRs pass | The setup files are committed on a branch, and `troy-check pr` with the setup title passes R01, R02, R12, R19, and R20. The language step's files, committed on top with the setup commit as the merge base, pass R02. So do the upgrade's. |
| Language step | Python and C/C++ files. Tables appended to an existing `pyproject.toml`, or a new one created. A table that already exists stops the step. A `CMakeLists.txt` without the include stops it. The `[lang]` table is filled and a filled one stops the step. Existing tests are listed as legacy. The workflow gets the pack's job under `jobs:`. |
| Environment | With a fake `mamba` on the PATH that records its arguments: the environment is created only when missing, the lock is compiled from every member's manifest, and `--env-prefix` and `--no-env` work. uv's cache folder (D213): every call gets `troy-mode-uv-cache` in the temp folder when `UV_CACHE_DIR` is unset or empty, and a value already set unchanged; `series` puts the folder in both commands only when the variable is unset or empty. D289: the first mock's install in a Python DV1 brief, a team's brief included, and a real run's `program-not-found` fix start with the same variables, and the problem's message shows `<uv cache>` in place of the folder. No test uses the network. |
| Upgrade | An unchanged owned file is replaced, and an edited one stops the step. A new template is created. R rows are replaced, P rows and "Since" dates are kept, and the version rises in both languages. The config is never changed. |
| Skill | `SKILL.md`'s front matter has `name: troy-init` and `disable-model-invocation: true`. Its text names the three steps and the PR flow's steps. D291 to D293: it names the protection probe and its 403 that names the plan, `branch-rule` with both files, the POST with `--input`, the second read after it, the private repository question with the rule, that existing rulesets stay as they are, and that a refused call goes to Troy; it no longer marks `troy-mode checks` required. |
| Branch rule | `branch-rule` without `--rules` adds R21's ruleset, with its body's absolute path. A list that holds `deletion`, `non_fast_forward`, and `pull_request`, from one ruleset or from two, keeps it out of `add`; without any one of them, it is added. `existing` lists every ruleset of `--rulesets` with its ID, name, and enforcement, a `disabled` one included. When a listed ruleset, in force or not, already has R21's name, R21's ruleset goes to `held` and not to `add`. A file that is not a JSON list is exit code 2. The body holds exactly what section 4.7 gives: the name, target `branch`, enforcement `active`, an empty bypass list, `~DEFAULT_BRANCH`, and the three rules with their parameters, and no `required_status_checks` rule. No test uses the network. |
| Templates (D294) | Every R row of the rules template has the ID, type, and Enforced by of an R row of requirements section 6, in the same language, and every R row of the requirements has its row in the template. No template comment says that round 3 escalates. |
| Exam (D294, F16's suite) | `affected`: a changed template that every case's project holds affects no case; one that a case's project lacks affects that case; one whose path a case's brief names affects that case. |

### 11.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: an existing file overwritten, a marker left in the rules table, mirrors with different versions, one pack's pattern missing from the config, the `[lang]` table not filled, existing tests not listed, the architecture approval not checked, git hooks without the executable bit, a P row dropped by upgrade, an edited owned file replaced by upgrade, and the pack's job not added. D213's change adds: a value already set overridden, the folder missing from `series`' install command, and a folder outside the temp folder. D289 adds: the variables missing from the first mock's install, put after `mamba run`, given to another check or to a C/C++ brief, a value already set overridden there, a team's brief that loses them, and the folder shown in a real run's message or missing from its fix. R21's branch rule adds: a bypass actor in the body, a required status check in the body, `r21` true without `deletion`, a relative path in `add`, a `held` ruleset put into `add`, and a `disabled` ruleset left out of `existing`. The exam's change adds: a template counted although the project holds it, a template the project lacks not counted, and a template that the brief names not counted. The counts go in the PR description.

### 11.3 Sample projects in CI

Because `build_sample.py` uses troy-init's functions (section 8), troy-pstack's sample workflows prove on Linux that troy-init's output passes the pack's CI job, both on a project with code and on one without.

### 11.4 Trial (D56)

Before the language step's PR opens, troy-init runs in nested `claude -p` sessions on Troy's PC, with troy-pstack loaded from the PR branch through `--plugin-dir`:

1. **Setup** in an empty folder. troy-init creates the private repository `ZJUCao/troy-mode-trial` (the trial's prompt answers the question with yes), opens the setup PR, waits for the checks, and merges it.
2. **Architecture.** The trial merges a prepared `[docs]` PR with a small `docs/architecture.md` at version 1.0, through the same steps.
3. **Language step** for Python, with `--env-prefix` in a scratch folder. Its PR passes with the pack's code steps skipped, and merges.
4. **Upgrade** with nothing to change reports that and opens no PR.
5. **Fresh clone.** When F05 is merged, a fresh clone gets `core.hooksPath` from F05's `SessionStart` hook.

The repository is private and stays for later trials (F07, F11). Deleting it is Troy's call. The trial uses a few minutes of the private repository's free Actions minutes.

**R21's branch rule (D295).** `ZJUCao/troy-mode-trial` is public now and has no branch rule on purpose. Before the branch rule's PR merges, two nested `claude -p` trials run with tstack from the PR branch:

1. **Upgrade** on a clone of `ZJUCao/troy-mode-trial`. troy-init finds R21's ruleset missing, the trial's answers say yes, and it adds it. The upgrade's PR, which carries the new template rows, then merges by rebase under it. The ruleset stays on the repository afterwards.
2. **Setup** in a fresh clone of the new public repository `ZJUCao/troy-init-trial`, which the build's session creates with `gh repo create --public --add-readme` once Troy approves it with this design. troy-init takes the path of a repository that already exists: the probe answers 404, the trial's answers say yes, the rule is on before PR 1, and PR 1 merges under it. Keeping or deleting that repository afterwards is Troy's call.

Each trial checks the rulesets that GitHub lists against section 4.7. No trial uses a private repository, because GitHub Actions did not run on Troy's private repositories on 2026-11-28, so no check would report there. A new repository's path through D52's question, and the 403 of a plan without branch rules, are checked by tests only.

### 11.5 Status

| When | F06's status in requirements 7.2 |
| --- | --- |
| Part 1 merges | Written, part 1 of 2: setup and upgrade. Its unit tests pass on Troy's PC. |
| Part 2 merges after a passing trial | Runs on a sample project: troy-init set up a scratch GitHub project, whose setup and language PRs passed CI and merged. Not yet used on a real project. |
| The pilot (F11) starts with troy-init | Used on a real project |
| R21's branch rule's PR merges after both trials of 11.4 | The F06 row adds: troy-init adds R21's branch rule at setup and upgrade, which runs on a sample project (the two trials), and is not yet used on a real project. |

F06 lands in two PRs (D55), each with one commit and its tests written first:

1. **Setup and upgrade.** The skill, the engine's setup and upgrade, and their tests. Also the R12 change of section 8, and the C/C++ config fragment's line for `include/troy/not_implemented.h` (D49), because setup writes that pattern into the config.
2. **Language step.** The engine's language step, the F03 pack changes, `build_sample.py`, their tests, and the trial.

Each status update is its own PR.

R21's branch rule lands in two PRs, each with one commit and its tests written first:

1. **The exam's change** (section 8, D294): `affected` and its tests, and F16's design. A harness change proves every case's anchors again, about $12 to $40.
2. **The branch rule:** `branch-rule`, the body, the skill, the entry skill's lines, the templates, the guide, and the plugin's next minor version, after both trials of 11.4. With the exam's change merged, its templates affect no case.

Then the status PR, with F06's status only, as requirements 1.72 or the next free version. Requirements 1.71 (PR #137) already holds R21's new Enforced by cell, which the rules template takes, and the F06 row's sentence about the rule.

## 12. Not in F06

- Writing the requirements and the architecture, opening their PRs, and running troy-init from the flows (F04 roles and F07).
- Creating the environment for other members of a series and updating their locks (F07, F03 design 8.1).
- A project's own rules (F09). Upgrade brings only troy-mode's R rules.
- The TypeScript/JavaScript pack (later, Q1).
- A permission rule for the plugin's files (F05 D45).
- Deleting the trial repositories.
- Changing or deleting a ruleset, a bypass actor, classic branch protection, and rulesets of an organization (section 4.7).
- Marking `troy-mode checks` as required on GitHub (D293).

## 13. Decisions for Troy

F05 ends at D46, so F06 continues from D47.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D47 | How is troy-init built? | A: a skill Troy types, plus a Python engine with the standard library only and three steps, `setup`, `lang`, and `upgrade`, with `--dry-run` and `--json` (section 3). The engine changes files only. The skill and F07 commit and open the PR. B: the skill's instructions copy and edit the files by hand. | A. Copying, filling in, and hashing files are exact jobs that tests can check. F07 can run the engine, though it cannot call a skill marked `disable-model-invocation`. |
| D48 | What does setup write, and what about files that already exist? The F06 row brings the CI workflow only after the architecture. | A: the files of section 4.2, troy-check's CI job among them. troy-init never overwrites or deletes a file it did not write. It stops, lists them, and the skill asks Troy about each one (`--replace`). B: the same files without the CI job, which then arrives in the language step. C: overwrite existing files, and let the PR's diff show what changed. | A. With troy-check's job from setup on, the requirements and architecture PRs are checked for R12 and R20 too. A project that adopts troy-mode, such as troy-voice, keeps its own files unless Troy says otherwise. This changes the F06 row and 5.1 in the requirements. |
| D49 | How do the pack's files get their path classes before the language step's PR is checked? troy-check reads classes from the merge base, so without this the PR's `pyproject.toml` is `source`, and a `[rules]` PR may not change source (R02). | A: setup's config already holds every pack's path patterns (section 4.3), and the C/C++ fragment adds `include/troy/not_implemented.h` to `config`. B: the language step takes two PRs, first the config, then the files. C: troy-check's built-in patterns learn the packs' file names. | A. One PR per step, and troy-check's rule that a PR cannot loosen the rules that judge it stays as it is. Its cost is a few patterns for files the project does not have. C puts language files into the language-independent checks. |
| D50 | The pack's CI job runs on every PR, but fails on a project that has no code yet, which is the case from the language step until the first mock. What then? | A: both packs' jobs first check whether the PR has any source file, and skip their code steps until it does (section 5.6). This changes F03's packs. B: troy-init adds an empty package in a `[refactor]` PR. C: leave it, so every PR fails until the first mock. | A. It needs no placeholder code, and documentation PRs also skip setting up the environment. B still fails, because the coverage report has no data, and C would block the design and test plan PRs. |
| D51 | Who creates the build file, the environment, and the lock? | A: the language step creates `pyproject.toml` or `CMakeLists.txt` when it is missing, creates the series environment on Troy's PC when it is missing, compiles the lock, and installs it (section 5.4). B: troy-init writes the files only and prints the commands for Troy. | A. CI needs the lock in the language PR, and a role cannot run the pack's checks without the environment. B gives Troy work that is not a decision. |
| D52 | What if the folder has no GitHub repository? R21 forbids a local commit on `main`, and a PR needs a `main` to target. | A: the skill asks Troy once, then creates a private repository under Troy's account with `gh repo create --private --add-readme`. GitHub makes the first commit on `main` (section 7, step 1). B: troy-init stops and says what Troy must create. | A. One yes from Troy, and R21 still holds. Creating the repository is the only step that reaches outside the project, so it always asks. This adds to the F06 row in the requirements. |
| D53 | Who merges troy-init's PRs? | A: troy-init waits once for the checks and merges when they pass, as R18 lets Claude merge every PR except PR 1 and PR 2 of the first features (section 7). B: troy-init stops at the open PR, and Troy or F07 merges it. | A. A project is not usable until its setup PR merges, and the PR holds no decision for Troy. |
| D54 | How much does upgrade change? F02 D8 says that rerunning troy-init in a `[rules]` PR upgrades a project. | A: replace troy-mode's own files when nobody edited them, and stop on edited ones. Bring the R rows of the rules table up to date and keep the P rows. Only report differences in the config and the build files (section 6). B: replace everything troy-init ever wrote, edits included. C: leave upgrade to the rule change flow (F09). | A. Upgrades are mechanical where troy-mode owns the file, and never silently undo a project's own choices. |
| D55 | How does F06 land? Q10 says one PR per feature, with F03 as the exception. | A: two PRs (section 11.5): setup and upgrade first, then the language step with the F03 pack changes and `build_sample.py`. B: one PR. | A. The second PR changes F03's CI jobs and the sample workflows, and is easier to review without the first. This adds F06 to Q10's exceptions. |
| D56 | How is F06 tried out, and when does its status move? | A: tests and planted bugs, the sample projects in CI, and a trial on a private scratch repository `ZJUCao/troy-mode-trial`, which troy-init creates and later trials reuse (section 11.4). Status after part 2: "Runs on a sample project". B: the same, but the trial uses a local bare `origin`, so no PR or CI really runs. Status "Written" until F07 uses troy-init. | A. Only a real GitHub repository shows that the first PR runs its own workflow, that the checks pass, and that the merge works. It creates one private repository on Troy's account and uses a few Actions minutes. |
| D213 | Which cache folder does uv get when `UV_CACHE_DIR` is not set? In the desktop app's sandbox, the pilot's first lock compile failed because uv could not write its default cache, and passed when troy-mode ran the step again with the cache in the session's temporary folder. From tstack issue #48. Its ID comes from the range D213 to D218 kept for this batch of pilot fixes. | A: the folder `troy-mode-uv-cache` in the system temp folder, as Python's `tempfile.gettempdir()` finds it. B: a folder under the project's git dir, such as `<git dir>/troy-mode/uv-cache`. Both only when `UV_CACHE_DIR` is not set, for the language step and `series` (section 5.4). C, not taken by Troy: only a guide note that says to set `UV_CACHE_DIR`. | A. `gettempdir()` takes the first of `TMPDIR`, `TEMP`, `TMP`, and the platform's usual folders in which it can create a file, so the folder is writable when the step starts, and a sandbox that points these variables at its own folder is followed. uv moves files by renaming them, and Windows cannot rename a file to another drive: that was the pilot's error ("cannot move the file to a different disk drive"), and the cache in the temporary folder fixed it. A folder under the git dir sits on the project's drive, which on Troy's PC is D:, while the temporary folder is on C:. It would also put a cache of hundreds of megabytes inside the project, and an emptied temp folder costs only a new download. Troy approved setting the variable when it is not set on 2026-11-18 (issue #48), and left the folder to this design. |
| D289 | D213 left the pack's checks in F07's feature loop on uv's default cache. Two uv commands that the engine gives still call uv without `UV_CACHE_DIR`: the first mock's `uv pip install -e . --no-deps` in DV1's checks (`troyflow/checksteps.py`), and the same install as the fix of a real run's `program-not-found` problem (`troyflow/realexec.py`). On Windows uv can then fail as the pilot's first lock compile did, when it cannot rename into its cache across drives (tstack issue #48's follow-up). How do they get the cache? | A: `series`' rule (D213): when `UV_CACHE_DIR` is not set, or is empty, in the engine's environment, the command starts with `UV_LINK_MODE=copy UV_CACHE_DIR=<folder>`, the folder from `uv_cache_dir()` and quoted for the shell; otherwise with `UV_LINK_MODE=copy` alone. The real run's message shows the folder as `<uv cache>`, and its fix holds it (section 5.4). B: `UV_CACHE_DIR` only, without `UV_LINK_MODE`. C: a guide note that asks Troy to set `UV_CACHE_DIR` before Claude Code starts. | A, approved under Troy's standing yes of 2026-11-22. Every uv command that troy-mode gives then runs the way troy-init's own runs uv, so a fix that worked for the lock works for the install. B leaves out the copy mode that troy-init and `series` give uv, and C keeps the pilot's failure on each new PC. The real run hides the folder because the message goes into PR 6's description, whose evidence holds no folder of Troy's PC (F12 design 8). |

| D291 | When does troy-init add R21's branch rule? Troy asked on 2026-11-28 for it at the repository's creation ("最好是troy-init在建仓库的时候就直接加上ruleset"), and requirements 1.71 says at setup, before its first PR. | A: at setup, right after `gh repo create`, or at the same point for a repository that already has `origin`, before the step's branch and PR. Upgrade adds it when GitHub lists it missing, after asking. The language step does not look (section 4.7). B: as A, without upgrade, so projects set up earlier keep what they have. C: after the setup PR merges, where the required-check step is today. | A, approved by Troy on 2026-11-28 ("其余按照推荐"). The rule is on before any PR, so PR 1 already merges under it, as Troy asked. Upgrade is how every existing project gets troy-mode's changes (F02 D8): recipe-menu already has the rule, and other projects get it. It asks only when the rule is missing. C leaves PR 1 unprotected and asks a second question after the repository's. |
| D292 | D52 creates a private repository. GitHub enforces branch rules on a private repository only with a paid plan. On 2026-11-28 Troy's private repositories answered the protection probe with 404, not the 403 of 2026-11-07, so Troy's plan now has them; Troy believes it is the GitHub Education pack, which includes Pro. A free or lapsed plan still answers 403. What does the repository question offer, and what happens on a 403? | A: keep D52's private repository. One yes covers the repository and the rule "where your plan allows it". The skill probes each repository (section 4.7): on 404 or 200 it adds the rule, and on a 403 that names the plan it adds none, says that R21 rests on the local hooks, and goes on. No plan is written into troy-mode. B: ask public or private each time, with the trade. C: always public. | A, approved by Troy on 2026-11-28 ("education套餐在私有仓库上应该也可以创建ruleset"). On Troy's plan a private repository gets the rule, so nothing needs to change in D52, and a plan that lapses only costs the rule, with a clear message. B adds a question with no reason on Troy's plan, and C decides privacy for Troy. The requirements' F06 row keeps "creates a private one". |
| D293 | What does the rule hold? F02 D14 also asks troy-init to make `troy-mode checks` required, which version 1.6 does after the setup PR merges, through classic branch protection, only when GitHub has it. R24 wants a PR to merge only on the latest `main`, which GitHub's "up to date" setting would enforce. | A: two rulesets on the default branch, R21's, the same as recipe-menu's, and "troy-mode checks must pass", with the check required and "up to date" off, in place of the classic-protection step. B: R21's ruleset only; troy-init no longer marks the check required, and the classic-protection step goes (sections 4.5 and 4.7). C: one ruleset with both, "up to date" on. A was proposed. | B, chosen by Troy on 2026-11-28 ("只保留R21的ruleset"), with the question whether a required check would keep a test PR whose new tests fail from merging. troy-mode's merge step still merges a PR only when its checks pass (R18, F02 D14), so troy-mode's own merges do not change. What B leaves out: GitHub does not hold back Troy's own merges on GitHub when a check fails, and a PR merged while Actions cannot run is not stopped. |
| D294 | The rules template still says "Hook and CI" for R21, still has R17 escalate at round 3 and R18 without spot checks, both left over from F18, and lacks R24, left over from F20. The design and test plan templates' comments still say that round 3 escalates. The role exam counts every template as an input of all 12 cases, so the fix runs all twelve, about $250 to $400 for the first round (F16 design 10.1), and up to about twice that with second rounds. Yet every case's project has its own `.troy-mode/templates/`, which roles fill from (F04 common rule 7), so those runs would see the same inputs as before. | A: first narrow `affected`: a plugin template counts for a case only when the case's project has no copy of it, or the case's brief names its path (section 8). That harness change proves every case's anchors again: $40 by the exam's estimate, and $12.40 when F17 step 1 did the same (F17 design 12.5). Then the template rows, R17's comments among them, land with the branch rule and affect no case. B: the template rows with the full exam, about $250 to $400, and up to about twice that. C: leave the templates until a change that needs the exam anyway, while upgrade keeps carrying the old rows into projects. | A, approved by Troy on 2026-11-28 ("其余按照推荐"). The exam then measures only what reaches a role, and the fix costs a tenth. The only brief that names a plugin template, the rule change brief with `troy-mode/templates/rules.md` (F09), is used by no case today, so a later case that uses it still counts the template. |
| D295 | How is the branch rule tried? Nested `claude -p` trials that act only on `ZJUCao/troy-mode-trial` are pre-approved, and that repository has no rule on purpose. Creating or deleting a repository needs Troy's yes. | A: two trials (section 11.4): upgrade on troy-mode-trial, which adds R21's ruleset and merges its PR under it, and setup in a clone of a new public repository `ZJUCao/troy-init-trial`, which the build's session creates once Troy approves it with this design. The ruleset on troy-mode-trial stays. No trial uses a private repository, since Actions did not run on Troy's private repositories on 2026-11-28. B: the upgrade trial only, and setup's path by tests only. C: no trial, and the status says "Written". | A, approved by Troy on 2026-11-28 ("其余按照推荐"), with the new public repository. Only GitHub shows that troy-mode's rebase merge passes R21's ruleset, at setup and at upgrade. recipe-menu shows neither yet: its ruleset was added at 17:15 UTC on 2026-11-28, after its last merge, PR 127. A private repository's path waits for real use. |

Requirements 1.16 records the approved changes:

- The F06 row: setup brings troy-check's CI job, the language step brings the pack's job, upgrade is listed, each step lands as one `[rules]` PR that troy-init merges, and troy-init creates a private GitHub repository when there is none (D48, D52, D53, D54).
- 5.1 steps 2 and 4: troy-check's workflow arrives at init, and the language pack's job at the checks step.
- Q10: F06 lands in two PRs (D55).

## 14. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-06 | First draft. |
| 1.0 | 2026-11-06 | Approved by Troy with D47 to D56, every recommended answer. |
| 1.1 | 2026-11-07 | Section 8: troy-check's R12 skips `.troy-mode/`, approved by Troy on 2026-11-07. Section 11.5: part 1 also brings that change and the D49 config line. Found while building part 1. |
| 1.2 | 2026-11-07 | Section 3.2: `lang` also takes `--project-name`, which the option table already gives the build files. Found while building part 2. Sections 3.1 and 7: the language step and upgrade create their branch before the dry run, because every step stops on `main`. Found by the trial of 11.4, where the dry runs of both steps stopped on `main`. |
| 1.3 | 2026-11-07 | Section 7, step 8: detach before the merge and end with `git fetch origin`, in place of `git switch main` and `git pull --ff-only`, so troy-init also works in a worktree, where `main` is often checked out elsewhere. The skill's upgrade with nothing to change detaches the same way before it deletes its branch. From F07 design section 12. |
| 1.4 | 2026-11-09 | Section 4.2: a file troy-init edits in place keeps its line endings, and only the files it creates get LF. Upgrade also reads a rules table with CRLF line endings, as a Windows checkout with `core.autocrlf` has it. Found by F09's trial, where upgrade left the R rows alone on such a checkout because it found no version in the table's header. |
| 1.5 | 2026-11-18 | D213, from tstack issue #48, approved by Troy on 2026-11-18: when `UV_CACHE_DIR` is not set, the language step and `series` give uv the cache folder `troy-mode-uv-cache` in the system temp folder (sections 5.4, 11.1, 11.2, and 13). |
| 1.6 | 2026-11-24 | D289, the follow-up of D213, approved under Troy's standing yes of 2026-11-22: the first mock's `uv pip install -e . --no-deps` in DV1's checks and a real run's install fix start with `series`' uv variables, and the real run's message shows the folder as `<uv cache>` (sections 5.4, 11.1, 11.2, and 13). No requirement changes. |
| 1.7 | 2026-11-28 | D291 to D295, approved by Troy on 2026-11-28, from requirements 1.71 and Troy's request of the same day: before setup's PR, and before an upgrade's when it is missing, troy-init adds R21's ruleset on `main` where GitHub allows it, and no longer marks `troy-mode checks` required (D293 B) (new section 4.7, sections 1, 3, 4.5, 6, 7, 8, 9, 11, 12, and 13). The repository stays private; a probe tells whether the plan allows the rule, and existing rulesets stay as they are. The rules template's stale rows and the role exam's view of templates change with it. |
