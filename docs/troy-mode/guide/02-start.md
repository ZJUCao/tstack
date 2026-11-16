# 2. Start a project

| | |
| --- | --- |
| Version | 0.2 |
| Date | 2026-11-16 |
| Source of truth | This English file. [`02-start.zh-CN.md`](02-start.zh-CN.md) is the Chinese mirror. |

A project becomes a troy-mode project in four steps: setup, the requirements, the architecture, and the language step. You approve the requirements and the architecture. troy-mode does the rest and merges each step's PR ([requirements section 5.1](../requirements.md#51-project-setup-once-per-project)).

## 2.1 The request

Before you start, give the project the merge permission ([section 1.4](01-install.md#14-the-merge-permission)). Then open a new Claude Code session in the project's folder, new or existing. In the desktop app, choose the folder itself: the pilot ran there for its whole version, and a session in a git worktree of the project has not been tried. Type every troy-mode request for the project in such a session, not in a session of another project. Then type what you want to build:

```text
/troy-pstack:troy-mode start a project: a command-line tool that counts the words in a text file
```

In a folder with no `.troy-mode/`, troy-mode answers a question but changes nothing. For any other request it asks you once whether to make the folder a troy-mode project. Then it runs the four steps in order, and stops where it needs you. A project that has some steps already resumes at the first missing one.

To run only the setup step, type `/troy-pstack:troy-init`. It turns the folder into a troy-mode project and stops there ([troy-init skill](../../../skills/troy-init/SKILL.md)).

## 2.2 Setup

troy-init's engine first plans the setup without changing anything. Then troy-mode asks you, in one message, everything that has no clear default:

- **The GitHub repository.** When the folder has no `origin` remote, troy-mode asks whether to create the private repository `<your account>/<folder name>`. Creating it is the only step that reaches outside the project, so it always asks. GitHub makes the first commit on `main`.
- **Files troy-init did not write.** troy-init never overwrites a file it did not write. For each such file in its way, troy-mode asks whether to replace it. Keeping it stops the step.
- **A folder with commits but no `origin`.** troy-mode stops and asks how to publish them, because R21 forbids pushing `main`.

Setup lands as one PR, `[rules] Set up troy-mode`, on the branch `troy-mode/init`. troy-mode waits for its checks and merges it. This is the setup report of troy-init's trial, about PR [#1](https://github.com/ZJUCao/troy-mode-trial/pull/1), shortened:

```text
Setup is done.
- Repository: I created the private repository ZJUCao/troy-mode-trial (GitHub made the
  first commit on main) and added it as origin over SSH. There were no conflicts.
- PR #1 "[rules] Set up troy-mode": one commit with 57 files.
  On GitHub, troy-mode checks passed and the PR was merged by rebase.
- Git hooks: they're on in this clone (core.hooksPath is .troy-mode/checks/git-hooks).
- Required check: branch protection isn't available on your plan (GitHub answered 403,
  "Upgrade to GitHub Pro"), so troy-mode checks stays optional.
Next: the requirements (Product Manager writes docs/requirements.md).
```

On GitHub's free plan, a private repository has no branch protection. troy-mode's own merge step then enforces the Hard rules: it never merges a PR whose checks fail ([requirements section 6](../requirements.md#6-rules)).

## 2.3 The requirements

The Product Manager, which is the main session, asks you the questions it needs, then writes `docs/requirements.md` and its Chinese mirror. The document holds the goal, the features with their IDs, the dependency graph, the topological order, the prototypes, and the version plan ([requirements section 5.1](../requirements.md#51-project-setup-once-per-project)). Each feature has a short name, such as "Export history as CSV", because the name becomes part of every PR title of that feature and the name of its folder.

It opens `[docs] Add the requirements` on `troy-mode/requirements`. The PR's description opens with a one-page summary for you, in Chinese and then English: what the program will do, each point you decide with a recommendation, and the risks ([section 7.1](07-taking-part.md#71-the-steps-that-wait-for-you)). troy-mode posts `Waiting for Troy: approve this PR`, sends you the same summary in chat, and stops. You approve in one of two ways:

- **In chat.** Reply that you approve, for example "Approved". troy-mode records your approval in the document's header and change log, and merges the PR.
- **On GitHub.** Merge the PR yourself. troy-mode then records the approval in a `[docs] Record Troy's approval of <document>` PR, which it merges.

To ask for changes, say what to change. The Product Manager revises, and the PR waits for you again. [Section 7.1](07-taking-part.md#71-the-steps-that-wait-for-you) has the details.

## 2.4 The architecture

After the requirements merge, the Architect writes `docs/architecture.md` and its mirror: the tech stack, the modules and the directions they may depend on each other, the data model, error handling, logging, naming, and coding rules. It opens `[docs] Add the architecture` on `troy-mode/architecture`, with the Architect's summary for you at the top of the description: what you will notice, such as speed, the files the program keeps, and tools to install. You approve it the same way.

The message that asks for this approval also asks one more question: which series the project belongs to, if any. Projects that will run together on one platform form a series and share one mamba environment, named after the series ([requirements section 8](../requirements.md#8-non-functional-requirements)). With no series, the environment is named after the project.

## 2.5 The language step

The language comes from the architecture's tech stack: Python or C/C++. troy-mode runs troy-init's language step on `troy-mode/lang-python` (or `troy-mode/lang-cpp`) and merges `[rules] Add the Python pack` (or `[rules] Add the C/C++ pack`). The step:

- adds the language pack's files, its tool settings, and its CI job;
- creates `pyproject.toml` or `CMakeLists.txt` when the project has none; otherwise it adds the pack's tables at the end of `pyproject.toml`, or checks that `CMakeLists.txt` includes `cmake/troy.cmake`;
- creates the mamba environment on your PC when it is missing, which downloads Python and the tools and takes a few minutes, then compiles the lock and installs it.

It stops when your `pyproject.toml` already holds one of the pack's tables, or your `CMakeLists.txt` does not include `cmake/troy.cmake`. troy-mode then asks you before it changes your build file. Until the first mock PR, the pack's CI job finds no code and passes with "No code yet". The trial's language PR is [#3](https://github.com/ZJUCao/troy-mode-trial/pull/3).

After this step, troy-mode goes on to the first feature only if your request asked for it. Otherwise it reports and stops.

## 2.6 A project that already has code

A project with code and tests can adopt troy-mode. Old code does not have to meet the rules: only new and changed code does, and old code is fixed when it is touched ([requirements Q6](../requirements.md#10-open-questions)). This path has not run yet: the trials started from an empty repository. The Python pack expects one `pyproject.toml` and one `src/` at the project's root, so a project that keeps each package in `packages/<name>/` with its own `pyproject.toml`, such as troy-voice, does not fit yet ([F11 design section 3.2](../design/F11-pilot.md#32-candidates-d93)).

- **Existing tests.** The language step lists the test files that match the pack's test patterns in `[tests] legacy` in `.troy-mode/config.toml`, and troy-mode tells you which. R10 then does not fail their names for lacking a case ID. They must still pass.
- **Existing files.** troy-init keeps every file it did not write unless you say yes to replacing it.
- **An existing `pyproject.toml`** gets the pack's tables added at its end. If it already holds one of them, the step stops and says what to move.

## 2.7 The files troy-mode adds

| Path | What it is |
| --- | --- |
| `.troy-mode/config.toml` | The project's config: path classes, limits, the language pack, roles, and how many features you approve. |
| `.troy-mode/checks/` | troy-check and its git hooks. |
| `.troy-mode/templates/` | The document templates, in both languages. |
| `.troy-mode/install.toml` | troy-init's record of what it installed. Do not edit it. |
| `.troy-mode/progress.md` | The progress file. Local and git-ignored. |
| `docs/rules.md`, `docs/rules.zh-CN.md` | The project's rules table. |
| `.github/workflows/troy-mode.yml` | troy-check's CI job, and the language pack's job after the language step. |
| `.github/pull_request_template.md` | The PR description template. |
| `.gitignore` | Gains `.troy-mode/progress.md`, and the pack's lines after the language step. |

The project's documents come later: `docs/requirements.md`, `docs/architecture.md`, a folder per feature in `docs/features/`, and so on. [Section 8.4](08-reference.md#84-files-in-a-project) lists them with who may change each.
