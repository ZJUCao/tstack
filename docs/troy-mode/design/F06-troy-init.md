# F06 design: project init (troy-init)

| | |
| --- | --- |
| Feature | F06 in [requirements 1.16](../requirements.md#72-feature-list) |
| Version | 1.1 |
| Date | 2026-11-07 |
| Status | Approved by Troy on 2026-11-06, with D47 to D56. Troy approved the R12 change of section 8 on 2026-11-07. |
| Source of truth | This English file. [`F06-troy-init.zh-CN.md`](F06-troy-init.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F06 turns a folder into a troy-mode project and keeps troy-mode's files in it current. It delivers one skill, `/troy-pstack:troy-init`, and the engine behind it, with three steps:

1. **Setup** (requirements 5.1 step 2): the marker folder with the config, troy-check and its git hooks, the templates, and the progress file; the rules table; the PR template; and the CI workflow with troy-check's job.
2. **Language step** (5.1 step 4), after Troy approves the architecture: the language pack from F03 and its CI job.
3. **Upgrade** (F02 D8): troy-mode's own files brought to the plugin's current version.

Each step lands as one `[rules]` PR with one commit. troy-init opens it and merges it once its checks pass (D53).

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

The skill runs the engine with `--dry-run --json` first. It asks Troy, in one message and in Troy's language, only what has no clear default: whether to create the GitHub repository (D52), whether to replace a file troy-init did not write (D48), and the environment's series for the language step. It then runs the engine, takes the result through the PR flow of section 7, and reports what it did and what it did not do.

### 3.2 The engine

```text
python troy_init.py setup   [--project-name <name>] --email <address> [common options]
python troy_init.py lang    (python | cpp) [--environment <name>] [--series <folder>]...
                            [--package <name>] [--mamba <path>] [--env-prefix <path>] [--no-env]
                            [common options]
python troy_init.py upgrade [common options]

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

The engine changes files and the repository's git config only. It never commits, pushes, or calls GitHub: the main session does that (F04 D29).

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
- Files are written with LF line endings.
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
- **Required checks.** F02 D14 asks troy-init to mark `troy-mode checks` as required where the repository allows it. Setup asks GitHub whether the repository can use branch protection, which a private repository on a free plan cannot. Only if it can, the skill asks Troy and then marks the check required. On Troy's current plan it says the check stays optional.

Nothing else in git or GitHub changes.

### 4.6 The install record

`.troy-mode/install.toml` records the troy-pstack version from `.claude-plugin/plugin.json`, the troy-pstack commit when the plugin folder is a git checkout, the date of each step, the language pack, and a `[files]` table with the SHA-256 hash of every file troy-init owns. troy-init owns the files it copies whole: troy-check, the templates, the PR template, the workflow, and the pack's whole files. Upgrade uses the hashes to tell an unchanged file from one someone edited (D54). `config.toml`, the rules table, `.gitignore`, and the build files belong to the project once written.

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
2. It compiles the lock with that environment's uv, from the manifests of every member of the series, and writes it into this project. uv runs with `UV_LINK_MODE=copy`.
3. It installs the lock into the environment.

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

Every path upgrade changes is in the `config` or `dependencies` class, so its PR is a valid `[rules]` PR.

## 7. The PR flow (D53)

The skill runs these steps around the engine. F07 runs the same steps when it runs the engine itself.

1. **Repository.** If the folder is not a git repository, `git init -b main`. If it has no `origin`, the skill asks Troy once whether to create a private GitHub repository under Troy's account, named after the project. On yes: `gh repo create <owner>/<name> --private --add-readme`, then `git remote add origin` and `git fetch origin`. GitHub makes the first commit on `main`, so nobody commits on `main` locally (R21, D52).
2. **Branch.** `git switch -c troy-mode/init origin/main`, or `troy-mode/lang-<name>`, or `troy-mode/upgrade-<version>`.
3. **Engine.** Run the step.
4. **Stage.** `git add` exactly the paths the engine's report lists, with `--chmod=+x` for the git hooks. Never `git add -A`.
5. **Commit.** One commit whose subject is the PR title (R01): `[rules] Set up troy-mode`, `[rules] Add the Python pack` or `[rules] Add the C/C++ pack`, or `[rules] Upgrade troy-mode to <version>`. F05's `commit-msg` hook checks it (R19).
6. **Check.** Run `troy-check pr` with the title and description. Stop on any `fail`.
7. **PR.** `git push -u origin <branch>`, then `gh pr create --base main` with the description from the PR template: Why, What, Checks, and Soft-limit reason "None".
8. **Merge.** Wait for the checks once with `gh pr checks <number> --watch`. When all pass, merge with `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>`, as R18 lets Claude merge every PR except PR 1 and PR 2 of the first features. When one fails, stop and report it. Then `git switch main` and `git pull --ff-only`, and record the step in the progress file.

```text
Troy:  /troy-pstack:troy-init
Claude: This folder has no GitHub repository. Create the private repository ZJUCao/habit-tracker?
Troy:  Yes.
Claude: Setup is done.
  PR #1 "[rules] Set up troy-mode": troy-check passed (R01, R02, R12, R19, R20), merged.
  Git hooks are on. Branch protection is not available on your plan, so the check stays optional.
  Next: the requirements (Product Manager).
```

## 8. Changes to earlier features

When F06 is built, it also changes:

- **F03's packs.** Both `workflow-job.yml` files get the step of section 5.6, and the sample workflows that mirror them follow, so `test_python_pack.py` and `test_cpp_pack.py` keep comparing them. The C/C++ config fragment adds `include/troy/not_implemented.h` to `config` (D49). Each pack gains its new-project build file and the README rows for it. F03's design gets a change-log row.
- **`build_sample.py`.** It builds each sample with the functions that write troy-init's files, without the preconditions of sections 4.1 and 5.1 and without the environment, in place of its own `install_pack`, so the samples are set up exactly as troy-init sets up a project. It gains a sample state with setup and the language step but no code, on which the pack's job must pass with its code steps skipped.

- **troy-check's R12.** Files under `.troy-mode/` are not documents for R12, as R20 already does not scan them (F02 design 6.7). Setup copies the templates there unchanged, and their headers hold markers and share `troy-doc` IDs with the project's documents, so without this every setup PR and every later document PR would fail R12. Found while building part 1, and approved by Troy on 2026-11-07. F02's design records it in its version 1.2.

F01, F04, and F05 do not change.

## 9. How F06 maps to the requirements

| Requirement | Where F06 covers it |
| --- | --- |
| F06 row: marker folder, document skeleton, rules table, progress file | Sections 4.2 and 4.4. The document skeleton is the templates in `.troy-mode/templates/`. |
| F06 row: after the architecture is approved, the language pack and the CI workflow | Section 5. troy-check's job arrives earlier, at setup (section 4.2, D48), so the requirements and architecture PRs are checked too |
| 5.1 steps 2 and 4 | Sections 4 and 5 |
| F02 D8: copy the checks, record the version, upgrade by rerunning troy-init in a `[rules]` PR | Sections 4.2, 4.6, and 6 |
| F02 D14: mark the check required when the repository allows it | Section 4.5 |
| R01, R02, R12, R19, R20 on troy-init's own PRs | Sections 4.2, 4.4, and 7 |
| R18: Claude merges what is not PR 1 or PR 2 of the first features | Section 7, step 8 |
| R21: no commit on `main` | Section 7, steps 1 and 2 |
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
| Environment | With a fake `mamba` on the PATH that records its arguments: the environment is created only when missing, the lock is compiled from every member's manifest, and `--env-prefix` and `--no-env` work. No test uses the network. |
| Upgrade | An unchanged owned file is replaced, and an edited one stops the step. A new template is created. R rows are replaced, P rows and "Since" dates are kept, and the version rises in both languages. The config is never changed. |
| Skill | `SKILL.md`'s front matter has `name: troy-init` and `disable-model-invocation: true`. Its text names the three steps and the PR flow's steps. |

### 11.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: an existing file overwritten, a marker left in the rules table, mirrors with different versions, one pack's pattern missing from the config, the `[lang]` table not filled, existing tests not listed, the architecture approval not checked, git hooks without the executable bit, a P row dropped by upgrade, an edited owned file replaced by upgrade, and the pack's job not added. The counts go in the PR description.

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

### 11.5 Status

| When | F06's status in requirements 7.2 |
| --- | --- |
| Part 1 merges | Written, part 1 of 2: setup and upgrade. Its unit tests pass on Troy's PC. |
| Part 2 merges after a passing trial | Runs on a sample project: troy-init set up a scratch GitHub project, whose setup and language PRs passed CI and merged. Not yet used on a real project. |
| The pilot (F11) starts with troy-init | Used on a real project |

F06 lands in two PRs (D55), each with one commit and its tests written first:

1. **Setup and upgrade.** The skill, the engine's setup and upgrade, and their tests. Also the R12 change of section 8, and the C/C++ config fragment's line for `include/troy/not_implemented.h` (D49), because setup writes that pattern into the config.
2. **Language step.** The engine's language step, the F03 pack changes, `build_sample.py`, their tests, and the trial.

Each status update is its own PR.

## 12. Not in F06

- Writing the requirements and the architecture, opening their PRs, and running troy-init from the flows (F04 roles and F07).
- Creating the environment for other members of a series and updating their locks (F07, F03 design 8.1).
- A project's own rules (F09). Upgrade brings only troy-mode's R rules.
- The TypeScript/JavaScript pack (later, Q1).
- A permission rule for the plugin's files (F05 D45).
- Deleting the trial repository.

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
