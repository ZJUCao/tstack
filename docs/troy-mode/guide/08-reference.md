# 8. Reference

| | |
| --- | --- |
| Version | 0.3 |
| Date | 2026-11-25 |
| Source of truth | This English file. [`08-reference.zh-CN.md`](08-reference.zh-CN.md) is the Chinese mirror. |

Lookup tables for daily use. The entry skill, [`skills/troy-mode/SKILL.md`](../../../skills/troy-mode/SKILL.md), is the source for every request, title, and heading here.

## 8.1 Requests

Type each after `/tstack:troy-mode`, in your own words.

| Request, for example | Flow | Guide |
| --- | --- | --- |
| "start a project: ...", or any request in a folder with no `.troy-mode/` | Project setup | [2](02-start.md) |
| "next feature", "F04", "F04 to F06", "the rest of v0.1" | Feature loop | [3](03-features.md) |
| "bug: ...", "fix #12" | Bug fix | [4.1](04-bugs-and-changes.md#41-fix-a-bug) |
| "change: ...", "the export should also ..." | Requirement change | [4.2](04-bugs-and-changes.md#42-change-a-requirement) |
| "idea #101", "change: #101" | An idea issue, taken in at once | [7.6](07-taking-part.md#76-from-your-phone) |
| "why ...", "how does ...", "try ..." | Work outside the pipeline: no PR | [4.3](04-bugs-and-changes.md#43-questions-and-experiments) |
| "release v0.1", "release v0.1.1", "release" | Version release | [5](05-release.md) |
| "add a rule ...", "change P01 ...", "retire P02", "a rule for every project ..." | Rule change | [6](06-rules.md) |
| "upgrade troy-mode" | Upgrade the project's troy-mode files | [8.6](#86-problems) |
| "continue", "status", or nothing | Continue | [7.5](07-taking-part.md#75-continue-in-a-new-session) |

A request that fits two flows, or none, gets one question with a recommended answer. `/tstack:troy-init` alone runs only the setup step; `/tstack:troy-init lang python` and `/tstack:troy-init upgrade` run the language step and the upgrade.

## 8.2 PR titles and branches

Every PR has one commit whose subject is the PR title (R01). "After your approval" means: you reply in chat and troy-mode merges, or you merge the PR on GitHub yourself. `F04`, `B12`, `P01`, `v0.1`, and `v0.1.0` stand for the feature, bug, rule, version, and tag.

| PR | Title | Branch | Merged by |
| --- | --- | --- | --- |
| Setup | `[rules] Set up troy-mode` | `troy-mode/init` | troy-mode |
| Requirements | `[docs] Add the requirements` | `troy-mode/requirements` | troy-mode, after your approval |
| Architecture | `[docs] Add the architecture` | `troy-mode/architecture` | troy-mode, after your approval |
| Language step | `[rules] Add the Python pack`, `[rules] Add the C/C++ pack` | `troy-mode/lang-python`, `troy-mode/lang-cpp` | troy-mode |
| Feature, PR 1 to 6 | `[F04 1/6 design] <name>` to `[F04 6/6 accept] <name>` | `troy-mode/f04-1-design` to `troy-mode/f04-6-accept` | troy-mode; PR 1 and 2 of the first features after your approval |
| Your approval, merged on GitHub | `[docs] Record Troy's approval of <document>` | `troy-mode/approve-<slug>` | troy-mode |
| Features you approve | `[rules] Set the features Troy approves` | `troy-mode/approvals` | troy-mode |
| Test fix | `[F04 test-fix] <summary>` | `troy-mode/f04-test-fix` | troy-mode |
| Document side PR | `[docs] Add cases to the F04 test plan`, `[docs] Accept the dependency <name>` | `troy-mode/f04-docs` | troy-mode |
| Bug, PR A and B | `[B12 A/B test] <summary>`, `[B12 B/B fix] <summary>` | `troy-mode/b12-test`, `troy-mode/b12-fix` | troy-mode |
| Requirement change | `[docs] Change the requirements: <summary>` | `troy-mode/change-<slug>` | troy-mode, after your approval |
| Version test plan | `[docs] Add the v0.1 test plan`, `[docs] Update the v0.1 test plan` | `troy-mode/v0.1-test-plan` | troy-mode |
| Version tests | `[v0.1 tests] End-to-end and stress tests`; a wrong version test is fixed in `[v0.1 tests] Fix <scenario ID>` | `troy-mode/v0.1-tests` | troy-mode |
| Release | `[docs] Release v0.1.0` | `troy-mode/release-v0.1.0` | troy-mode, after you accept |
| Your acceptance, merged on GitHub | `[docs] Record Troy's acceptance of v0.1.0` | `troy-mode/record-v0.1.0` | troy-mode |
| Rule | `[rules] Add P01, <summary>`, `[rules] Change P01, <summary>`, `[rules] Retire P01, <summary>` | `troy-mode/rule-p01`, `troy-mode/rule-p01-change`, `troy-mode/rule-p01-retire` | troy-mode |
| A rule's architecture | `[docs] Change the architecture for P01` | `troy-mode/p01-architecture` | troy-mode |
| A rule's cleanup | `[refactor] Apply P01 to <area>`, `[P01 test-fix] Apply P01 to tests` | `troy-mode/p01-cleanup-<area>`, `troy-mode/p01-test-fix` | troy-mode |
| Upgrade | `[rules] Upgrade troy-mode to <version>` | `troy-mode/upgrade-<version>` | troy-mode |

An experiment's branch, `troy-mode/try-<slug>`, is never pushed.

## 8.3 Comment headings

troy-mode posts every review, failed attempt, escalation, and request to you as a PR comment whose first line is one of these. A comment without one of them is yours.

| Heading | Posted when |
| --- | --- |
| `<Role> review, round <n>: <result>` | A reviewer reports, for example `Architect review, round 2: changes-requested`. Findings follow, one numbered line each, starting with the rule ID or checklist item. |
| `<Role> attempt <n>: failed` | An author's attempt fails. The failing checks follow. For a CI failure, a `Commit:` line first names the pushed commit. |
| `Escalation: <trigger>` | troy-mode stops for you ([section 7.3](07-taking-part.md#73-answer-an-escalation)). The line `Wait: W<n>` under it names the wait. |
| `Waiting for Troy: approve this PR` | The PR waits for your approval. The line `Wait: W<n>` under it names the wait, and the next line points to the summary for you at the top of the description. |
| `Architect ruling, round 3: <result>`, or `Product Manager ruling, round 3: <result>` | A review loop still disagreed after round 3, and the ruler decided each finding: `merge`, `fix`, then `fixed` or `not fixed` after the one revision ([section 7.1](07-taking-part.md#71-the-steps-that-wait-for-you)). |
| `Waiting for Troy: accept <tag>` | The release waits for your test on your devices. |
| `Real run output, part <n>` | The real output of PR 6's real run, when it does not fit the description. |
| `Release test, run <n>: passed` or `failed` | The release test's report, with a "Real run" part for `real-run --all`. |
| `Release test by Troy, run <n>: accepted`, `failed`, or `not accepted` | Your reply to the release, with your words. |
| `Bug deferred by Troy: #<n>` | You deferred an open bug past the release. |
| `Retrospective: <tag>` | The retrospective, which ends the release. |

On issues, troy-mode's comments start with `Idea: requirement change`, `Idea: bug`, `Idea: rule`, `Idea: answered`, `Idea: later`, `Idea: in the requirements`, `Waiting for Troy: <question>`, `Reply to Troy`, or `Device test, run <n>: ready`, in the language you wrote in. The engine command `troy_flow.py issues` works out each progress issue and checklist; the labels are `idea`, `progress`, and `device-test` ([section 7.6](07-taking-part.md#76-from-your-phone)).

## 8.4 Files in a project

| Path | What it holds | Changed by |
| --- | --- | --- |
| `docs/requirements.md` and mirror | Requirements, features, order, versions, statuses | Product Manager |
| `docs/prototypes/` | Prototypes | Product Manager |
| `docs/prototypes/<name>.run.toml` | A prototype's run file: the path map, how each section's data folder starts, replaced date words, and the `later` and `skip` marks, which `troy_flow.py real-run --item <ID>` and `real-run --all` read ([F12 design section 4](../design/F12-real-run.md#4-the-run-file-d103)) | Product Manager, in PR 6 |
| `docs/architecture.md` and mirror, `docs/adr/` | Architecture and its decision records | Architect |
| `docs/features/<id>-<slug>/design.md` and mirror | A feature's interface design | Interface Designer; the Architect writes its review section |
| `docs/features/<id>-<slug>/test-plan.md` and mirror | A feature's test plan | Test Manager |
| `docs/versions/<version>/test-plan.md` and mirror | A version's test plan and acceptance record | Test Manager; troy-mode adds your acceptance |
| `CHANGELOG.md` and mirror | One section per release | Product Manager |
| Source files | The code | Developer |
| `tests/`, `version-tests/` | The tests and the version tests | Test Engineer |
| `docs/rules.md` and mirror | The rules table | troy-init (R rows) and the rule change flow (P rows) only |
| `.troy-mode/config.toml` | The project's config (section 8.5) | troy-init, the rule change flow, the approvals PR, and you |
| `.troy-mode/checks/`, `.troy-mode/templates/` | troy-mode's own files | troy-init only. An edit makes the next upgrade stop on that file. |
| `.troy-mode/install.toml` | troy-init's record of what it installed | troy-init, which rewrites it at each step. Do not edit it. |
| `pyproject.toml`, `environment.yml`, `requirements-dev.lock` (Python); `CMakeLists.txt`, `CMakePresets.json`, `cmake/troy.cmake`, `requirements-tools.in`, `requirements-tools.lock`, `.clang-format`, `.clang-tidy` (C/C++) | The build file, the environment, the lock, and the tools' settings | The language step; the author and the series lock after a dependency you accepted; a rule PR's config and baseline lines; and you, in a `[rules]` PR |
| `.github/workflows/project-rules.yml` | The project's own check steps for its rules | The rule change flow |
| `.troy-mode/progress.md` | The progress file. Local and git-ignored. | troy-mode |
| `.github/workflows/troy-mode.yml`, `.github/pull_request_template.md` | troy-check's CI job and the PR template | troy-init only |
| `.github/ISSUE_TEMPLATE/idea.md` | The issue template "Idea / 想法", which adds the `idea` label | troy-init only |
| `.claude/settings.local.json` | Your Claude Code permissions. Git-ignored. | You |

Each role's write scope is enforced by hooks while it runs, and checked again after the run ([F05 design section 5](../design/F05-hooks.md#5-write-scopes), [F07 design section 7](../design/F07-entry-skill.md#7-the-check-after-each-run-d59)). A Developer edit to a test is refused (R08).

## 8.5 Config keys

`.troy-mode/config.toml`. Every key is optional, and an unknown key or a wrong type stops troy-check, so a typo never turns a rule off. troy-check reads the file from the PR's merge base, so a change takes effect on the PRs after the one that makes it. A change lands in a `[rules]` PR. The commented default is [`troy-mode/checks/config.default.toml`](../../../troy-mode/checks/config.default.toml).

| Table | Keys | Default and meaning |
| --- | --- | --- |
| `[identity]` | `commit_email` | The only allowed author email (R19). troy-init fills it in. |
| `[paths]` | `config`, `dependencies`, `tests`, `docs`, `lock`, `generated`, `allow_markers` | Patterns added to the built-in path classes. They never replace them. |
| `[limits]` | `source_lines`, `source_files` | R03: 500 lines and 5 files per source PR. |
| `[limits]` | `line_coverage`, `branch_coverage` | R11: 90% line and 80% branch coverage of the changed code. |
| `[limits]` | `function_lines`, `file_lines` | R04 and R06: 50 lines per function body, 500 per source file. |
| `[tests]` | `legacy` | Test files whose names need no case ID (R10). They must still pass. |
| `[lang]` | `name`, `source_roots` or `include_dirs`, `environment`, `series` | Set by the language step. |
| `[attribution]` | `mode` | R19: `strict` (default) or `trailers`, for a project about Claude. |
| `[roles.<role>]` | `model`, `effort` | A role's model and effort in this project ([section 1.5](01-install.md#15-models-and-effort)). |
| `[flow]` | `troy_approves_first` | How many features, first in the order, have PR 1 and PR 2 approved by you. Default 3; 0 means none. |
| `[summary]` | `max_chars` | R22: the most characters in each language of the summary for you that opens a design, test plan, requirements, or architecture PR. Default 2000. |
| `[hooks]` | `log_days` | How many days `hooks.log` keeps its lines. Each session start removes older lines, and the retrospective reads them for a whole version, so keep it above your longest version. Default 30 ([F05 design D219](../design/F05-hooks.md#10-errors-speed-and-the-log)). |

## 8.6 Problems

| Problem | What to do |
| --- | --- |
| **A merge, an amend, or a force push was refused by a permission.** troy-mode stopped and named the permission to add. Auto mode refused `gh pr merge` as a merge without review, or `git commit --amend --no-edit` or `git push --force-with-lease` as "Git Destructive". | Add the three entries of [section 1.4](01-install.md#14-the-merge-permission) to the `allow` list in the project's `.claude/settings.local.json`, then type `/tstack:troy-mode continue`. troy-mode never works around a refusal. |
| **A hook blocked a role.** | Nothing, usually. troy-mode's hooks keep each role inside its write scope and record every block in `<git dir>/troy-mode/hooks.log`, which holds no command line or file content and keeps its lines for `[hooks] log_days` days, 30 by default ([section 8.5](#85-config-keys)), so the retrospective sees a whole version. troy-mode names the run's log lines in its report. A file a role changed outside its scope is undone and the role runs once more. A second time in the same stage, troy-mode escalates ([F05 design section 10](../design/F05-hooks.md#10-errors-speed-and-the-log), [F07 design section 7](../design/F07-entry-skill.md#7-the-check-after-each-run-d59)). |
| **Right after the rename to tstack, every role's write is refused as outside its scope.** | troy-pstack is still installed or enabled, and its hooks treat tstack's roles as unknown subagents. Uninstall it and restart Claude Code ([section 1.3](01-install.md#13-update-after-a-new-plugin-version)). |
| **`/poteto-mode` or `/no-comments` was refused.** A hook said that the command is off in this project. | Use `/tstack:troy-mode <request>`; to try poteto-mode, use a folder that is not a troy-mode project ([F13 design section 5](../design/F13-mode-guard.md#5-refuse-with-no-override-d123)). |
| **A test runs on one platform only.** The local `troy-check code` fails only because a test is skipped on your PC, such as a test that runs only on Linux. | Nothing. troy-mode counts the local checks as passed, lists the case in the PR's Checks section as "skipped here, checked by CI", and merges only on CI's result, which proves the test ran. The test plan must say why the case runs on one platform only ([F07 design D69](../design/F07-entry-skill.md#16-decisions-for-troy)). |
| **Windows path lengths.** `git add` fails on a long path under `docs/features/`. | Keep each feature's name short in the requirements, such as "Export history as CSV": it becomes the feature's folder name and every PR title. A whole sentence there passed Windows' path limit in the trial ([F07 design section 8.1](../design/F07-entry-skill.md#81-stages)). Outside troy-mode, Git for Windows can also be told to accept long paths with `git config --global core.longpaths true`, which changes the setting for every repository on your PC. |
| **The project's troy-mode is older than the plugin.** `status` says that the project's troy-check is older than the plugin's. `[roles]`, `[flow]`, and some checks need the new copy. | First update the plugin ([section 1.3](01-install.md#13-update-after-a-new-plugin-version)). Then type `/tstack:troy-mode upgrade troy-mode`. It opens `[rules] Upgrade troy-mode to <version>`, which replaces troy-mode's own files that nobody edited, brings the R rows of the rules table up to date, keeps the P rows, and merges. An edited file stops it: troy-mode asks you whether to replace it. It never changes the config or the build files; it lists where they differ, for you to take into a rules PR. With nothing to upgrade, it opens no PR. |
| **No Python found.** The hooks stop with "troy-mode: no Python 3.11 or newer found". | Set `TROY_MODE_PYTHON` to a Python 3.11 or newer ([section 1.1](01-install.md#11-what-your-pc-needs)). |
| **A lock compile or install failed in the desktop app.** uv says that it cannot move a file to a different disk drive, or cannot write its cache. | The cause is the app's sandbox, which blocks uv's default cache folder, not your PC. When `UV_CACHE_DIR` is not set, troy-init's language step and the series lock give uv the folder `troy-mode-uv-cache` in your temp folder, and keep a value you set ([F06 design D213](../design/F06-troy-init.md#13-decisions-for-troy)). The first mock's install among the feature loop's checks, and the install that a real run gives as a fix, start with the same folder ([F06 design D289](../design/F06-troy-init.md#13-decisions-for-troy)). |
| **A hook refused a Python command with R23.** The reason says that the command makes Python read its program from standard input. | Nothing, usually. Since plugin 0.9.0, troy-mode's hooks refuse `python -`, `python -i`, and Python with no script, `-c`, or `-m`, for the main session and every role, because such a run can hang at Python's prompt ([F05 design section 8.3](../design/F05-hooks.md#83-python-that-reads-its-program-from-standard-input-r23-d223)). Claude writes the script to a file in the scratchpad and runs that file instead. Python with a script, `-c`, or `-m` may still read a pipe or `/dev/null`. |
| **A command never ends, or a `python.exe` stays after a role's report.** | On Windows, `python3` can be the Microsoft Store's stub, which waits for ever. Before plugin 0.9.0, a command whose Python read its program from standard input could also wait at Python's prompt: in the pilot this happened 39 times ([issue #64](https://github.com/ZJUCao/troy-pstack/issues/64)), and the hooks now refuse it (R23, the row above). Such a command runs into the shell tool's time limit, and troy-mode then stops it. A `python.exe` that a role left behind, from the project's environment, can be ended in Task Manager once no role is running. |
| **A role's command still ran after its report.** `check-run` or `snapshot` stopped with a `running` problem that names an agent. | Nothing, usually. A command that passes the shell tool's time limit moves to the background, and the role cannot stop it. Since plugin 0.10.0, troy-mode's hooks record such a command, and troy-mode ends the named agent with `TaskStop` before it checks the run or starts the next one ([F05 design section 6.1](../design/F05-hooks.md#61-work-a-role-leaves-running-d231-d232)). Before that, in the pilot, such a command wrote its old change 11.5 hours late, during another role's run ([issue #49](https://github.com/ZJUCao/troy-pstack/issues/49)). If a permission refuses `TaskStop`, troy-mode names the agent and waits: stop it yourself, then type `continue`. |
| **A CI check failed outside the author's files**, for example a download error on the runner, or "Repository not found" in the checkout step. | troy-mode stops and tells you; it does not re-run CI itself. A download error on the runner usually passes on a second run: you can re-run the failed jobs yourself, for example with `gh run rerun <run ID> --failed`, then type `continue`. In the pilot, "Repository not found" came from GitHub's side and cleared on the next push. |

## 8.7 Rules R01 to R23

The full text is in the [rules template](../../../troy-mode/templates/rules.md), which every project copies into `docs/rules.md`, and in [requirements section 6](../requirements.md#6-rules). Hard blocks the merge, Soft needs a reason in the PR description, Review is checked by a role, and Process is followed by troy-mode itself.

| ID | In short | Type |
| --- | --- | --- |
| R01 | One commit per PR, its subject equal to the PR title | Hard |
| R02 | One stage's output per PR: documents, source, or tests | Hard |
| R03 | A source PR changes at most 500 lines in at most 5 files | Soft |
| R04 | A function body has at most 50 lines | Hard |
| R05 | Google-style doc comments; code comments in English | Hard |
| R06 | A source file has at most 500 lines | Soft |
| R07 | Modules depend only as the architecture allows, never in a cycle | Hard |
| R08 | The Developer never edits test files | Hard |
| R09 | Every new test in a test PR fails against the mock | Hard |
| R10 | Every test's name starts with its case ID or bug ID | Hard |
| R11 | Changed code has at least 90% line and 80% branch coverage | Hard |
| R12 | A changed English document updates its Chinese mirror | Hard |
| R13 | A status label says how far a feature really goes | Review |
| R14 | Only interfaces with a performance target get performance tests | Review |
| R15 | Every fixed bug keeps its reproduction test | Review |
| R16 | A new third-party dependency needs the Architect's approval | Review |
| R17 | At 3 review rounds without agreement, the Architect, or the Product Manager on the Architect's own review, rules; you can overturn the ruling | Process |
| R18 | You approve PR 1 and PR 2 of the first features; troy-mode merges the rest | Process |
| R19 | Commits use your email. Commits, PRs, comments, reviews, issues, and release notes carry no Claude attribution, checked before they are posted | Hard |
| R20 | No template markers or guidance in a merged document or PR description | Hard |
| R21 | Every change reaches `main` through a PR from its own branch | Hard |
| R22 | A design, test plan, requirements, or architecture PR opens with a summary for you, in Chinese and English | Hard |
| R23 | Python never reads its program from standard input: no `python -`, `python -i`, or Python without a script | Hard |
