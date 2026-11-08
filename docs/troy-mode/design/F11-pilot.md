# F11 design: the pilot

| | |
| --- | --- |
| Feature | F11 in [requirements 1.27](../requirements.md#72-feature-list) |
| Version | 1.0 |
| Date | 2026-11-08 |
| Status | Approved by Troy on 2026-11-08, with D93 to D100. |
| Source of truth | This English file. [`F11-pilot.zh-CN.md`](F11-pilot.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F11 takes one small real project of Troy's through one version with troy-mode. It is the first full run of the pipeline (Q10), and the first time any troy-mode feature is used on a real project rather than on the scratch repository `ZJUCao/troy-mode-trial`.

F11 delivers:

1. the pilot project's first version, released and accepted by Troy on Troy's devices, made entirely through troy-mode's flows (sections 4 and 5);
2. a pilot report in troy-pstack that lists the problems found, the rule candidates, and the time and cost of each step (section 8, D97);
3. fixes for the problems that block the pilot, made through troy-pstack's own process (section 7, D96), and an issue in troy-pstack for each other problem;
4. status updates for every troy-mode feature that the pilot really used (section 9, D100).

F11 writes no troy-mode code of its own. Fixes are their own troy-pstack PRs. The pilot project's code, documents, and PRs belong to that project and are made by troy-mode, not by F11.

## 2. Prerequisites

The pilot starts only when all of these hold:

1. **F08 and F09 are merged**, with their trials passed: both read "Runs on a sample project".
2. **F10 is merged** (F10 design D91), so Troy has the guide, and troy-pstack's version is 0.2.0 or later (F10 design D89).
3. **Troy's Claude Code runs that version.** Troy installs or updates troy-pstack as `01-install.md` says and restarts Claude Code. A new session in the pilot folder lists `/troy-pstack:troy-mode`.
4. **The merge permission** is in the pilot project's `.claude/settings.local.json` (D98, F10 design section 4.3).
5. **The tools**: `gh auth status` passes, and for a Python project, Miniforge and uv are where troy-init finds them (F06 design 5.4).
6. **For a C/C++ project only**, the F07 fix of section 3.3 is merged.

The F11 session (section 6.3) checks each item and reports the ones that fail before Troy starts.

## 3. Choosing the project

### 3.1 What makes a good pilot

- **Real.** Troy will use the result, so Troy's device test and acceptance mean something.
- **Small.** Its first version fits in 4 or 5 features, each within R03's 500 lines (D94).
- **A built language pack.** Python is ready. C/C++ needs the F07 fix first (section 3.3). TypeScript/JavaScript has no pack (Q1).
- **On Troy's PC.** It builds and tests on Windows 11, and its device test needs only Troy's own devices.
- **No outside services** beyond GitHub and Anthropic (requirements section 8, Privacy), and no secrets in its tests.
- **A private GitHub repository**, new or existing.

### 3.2 Candidates (D93)

| Candidate | What it is | What the pilot would exercise | What it needs first |
| --- | --- | --- | --- |
| 1. A new small Python project | A command-line project Troy wants, started in an empty folder. If Troy names no idea, a Python command-line version of Troy's earlier recipe apps, `PrivateRecipes` (私房菜单) and `MyMenu` (个人菜单): recipes, a week's menu, and the shopping list for it, with Chinese and English text. | Every step from an empty folder: troy-init creating the private repository (F06 D52), requirements from zero with a terminal-session prototype (Q9), the architecture and its series question, the Python pack and its environment, 4 or 5 features through all six PRs, the question after the third feature (F07 D62), the version test plan, the release with Troy's test on Troy's PC, the GitHub release, and the retrospective. | Nothing beyond section 2. It does not test adopting existing code (Q6). |
| 2. `nuo_voice` | Troy's voice front-end for AI agents: Python, `src/` layout, about 2,300 lines of source, unit and integration tests, and EN/ZH design documents. Last changed 2026-11-03. | Adopting an existing project (Q6): legacy tests, old code checked only when it changes, merging the pack's `pyproject.toml` tables with its existing `[tool.ruff]` and `[tool.pytest.ini_options]`, moving its shared `nuo_env` environment to mamba and uv with a lock, and turning its design documents into troy-mode's requirements. | troy-init's language step stops on existing tool tables today (F06 section 5.2), so the tables must be merged first. Its integration tests need Ollama serving `qwen3.8:27b`, which does not fit the 12 GB GPU that troy-voice's notes give for Troy's PC, so its release scenarios would need another of Troy's machines. |
| 3. HiLog, in `HiCommonUtils` | A small C++ logging library with CMake, about 10 KB of source. Last changed in 2024. | The C/C++ pack on a real project, which nothing has done yet, with Q6 for its existing code and an existing `CMakeLists.txt` that must include `cmake/troy.cmake`. | The F07 fix (section 3.3). It has not changed since 2024, so its v0.1 would be new work that Troy may not need. |

**Not suggested now: troy-voice.** It is Troy's most active project, but the Python pack expects one `pyproject.toml` and one `src/` at the root, while troy-voice keeps each package in `packages/<name>/` with its own `pyproject.toml`. It also has about 5,900 lines, its own CI, its own agent hooks, and its own requirements format. It fits a second pilot, after troy-mode supports that layout.

Troy may name another project. The F11 session then checks it against section 3.1 and says what it would exercise and what it needs first, before the pilot starts.

**Troy's choice.** On 2026-11-08 Troy chose candidate 1 and named no other idea (D93). The pilot is therefore a new Python command-line project for recipes, a week's menu, and its shopping list, with Chinese and English text. It does not need the F07 fix of section 3.3.

### 3.3 C/C++ and the F07 fix

In a C/C++ project, tests are registered in `CMakeLists.txt` with `troy_add_test`, and that file is in the `dependencies` class. F07's check after each run flags every change to a dependency file that `--allow-dependency` does not name, so every Test Engineer run in a C/C++ project fails the check and is undone (F08 design section 9). F07's trials used Python only.

If Troy picks a C/C++ project, a small F07 fix comes first, with its own short design change and Troy's approval, for example: test registration moves into `tests/CMakeLists.txt` and `version-tests/CMakeLists.txt`, which are in the `tests` class, or `check-run` lets through a change that only adds or removes `troy_add_test` lines for a test-writing role. For a Python pilot the fix is not needed, and it stays a follow-up before any C/C++ project.

## 4. Setup

For a new project (candidate 1):

1. **Folder.** `D:\Troy\Projects\<name>`, empty. The F11 session suggests the name from the idea, and Troy may change it.
2. **Session.** Troy opens a Claude Code session in that folder in the desktop app and adds the merge permission (D98).
3. **Start.** Troy types `/troy-pstack:troy-mode start a project: <idea>`. troy-mode asks whether to make the folder a troy-mode project, and troy-init asks whether to create the private repository `ZJUCao/<name>` (F06 D52). Troy says yes to both. The setup PR merges.
4. **Requirements.** The Product Manager asks its questions, Troy answers, and Troy approves the requirements in chat (requirements 3.3 step 1). The version plan names v0.1 (section 5).
5. **Architecture.** The Architect writes it, and Troy approves it in the same way (3.3 step 2). The same message asks which series the project belongs to. Unless Troy says otherwise, the project is in no series and has its own environment.
6. **Language step.** troy-init's language step adds the pack, and its PR merges.

For an existing project (candidates 2 and 3), step 1 is its existing folder and repository, troy-init's setup and language step run on it as F06 section 5.5 says, and the F11 session first lists what section 3.2 says the project needs.

## 5. One version (D94)

"One version" is the project's v0.1 as its version plan defines it: **4 or 5 features**, each within R03. Four is the minimum, because the first three features' PR 1 and PR 2 wait for Troy (Q2), and only the fourth shows troy-mode merging them itself after F07 D62's question.

The version is done when:

- every feature of v0.1 reads "Usable on Troy's devices" in the project's requirements;
- the GitHub release `v0.1.0` exists on the release PR's merge commit (F08 D73);
- the `Retrospective: v0.1.0` comment is on the release PR, and every rule Troy picked from it has gone through the rule change flow or, for a rule for every project, become an issue in troy-pstack (F09 D83).

Bugs, requirement changes, side PRs, and escalations during the version are part of the pilot, not a reason to stop it. A patch release such as v0.1.1 happens only when a bug turns up after v0.1.0, and is not required.

## 6. Who does what

### 6.1 Troy

| Step | What Troy does | Requirements 3.3 |
| --- | --- | --- |
| Setup | Opens the session, adds the permission, types the first request, and says yes to the repository | |
| Requirements | Answers the Product Manager's questions and approves the document in chat | Step 1 |
| Architecture | Approves it and answers the series question | Step 2 |
| Features 1 to 3 | Reads and approves each feature's design (PR 1) and test plan (PR 2) | Step 3 |
| After feature 3 | Answers whether troy-mode goes on asking for PR 1 and PR 2 approvals | Step 3 |
| Escalations | Answers each one | Step 5 |
| Release | Runs the scenarios the version test plan gives Troy, on Troy's devices, and replies accepted, failed, or not accepted | Step 4 |
| Retrospective | Picks the rules to add, if any | |
| Between steps | Types `/troy-pstack:troy-mode continue`, "the rest of v0.1", or "release v0.1" in the pilot session (D95) | |
| At the end | Reads the pilot report | |

Everything else is troy-mode's work, within its merge rights.

### 6.2 The pilot sessions (D95)

Troy types the requests in a Claude Code session in the pilot folder, in the desktop app, as the guide says. troy-mode runs exactly as installed. A request such as "the rest of v0.1" takes troy-mode through every feature of the version, and it stops only at Troy's steps of section 6.1 (F07 D63). After a break, a new session in the same folder continues with "continue" (requirements 5.10).

A pilot session never edits troy-pstack, and never patches troy-mode's files in the pilot project by hand. A problem goes to the F11 session (section 7).

### 6.3 The F11 session

A troy-pstack session, started by the coordinating session after F10 merges, does F11's own work:

- checks the prerequisites (section 2) and tells Troy in one message what to type, and where;
- keeps a running log of the pilot in the side-session notes folder, so nothing is lost when a conversation is compacted;
- reads the pilot repository's PRs, comments, CI runs, and issues, the pilot sessions' transcripts, and the project's `hooks.log` (section 8);
- handles the problems that Troy or troy-mode's escalations report (section 7);
- writes the pilot report and the status PRs (sections 8 and 9).

It does not run troy-mode in the pilot project or answer for Troy.

## 7. When troy-mode breaks (D96)

| Problem | What happens |
| --- | --- |
| **A blocker**: troy-mode cannot go on, or would break a rule or lose work | The pilot waits. The F11 session opens an issue in troy-pstack with the `pilot` label. The fix goes through troy-pstack's process: a design change when it changes a design, a test written first, and a PR that raises the plugin's patch version (F10 D89). Troy updates the plugin and restarts Claude Code. troy-mode then brings the pilot project up to date with "upgrade troy-mode" (F06 section 6) and continues. |
| **A problem troy-mode gets past**, with an escalation answered or a step repeated | The F11 session opens an issue with the `pilot` label, and the pilot goes on. The fix comes after the pilot, or alongside it when it does not touch what the pilot is doing. |
| **A wrong or missing part of the guide** | A note in the running log, fixed in one guide PR before the final status PR (F10 section 9.5). |

Nobody works around a blocker by hand without Troy's yes in chat. If Troy says yes, the report lists the workaround as a problem.

## 8. What is measured and written down (D97)

### 8.1 The pilot report

`docs/troy-mode/pilot/<project>-v0.1.md` and its Chinese mirror, in troy-pstack, written by the F11 session in one PR after the version is done:

| Section | Holds |
| --- | --- |
| 1. Summary | The project, the version, the dates, and the outcome in a few lines |
| 2. Timeline | Each step with its PRs and dates, from setup to the retrospective |
| 3. Problems | Section 8.2 |
| 4. Rule candidates | Section 8.3 |
| 5. Time and cost | Section 8.4 |
| 6. The guide | Section 8.5 |
| 7. Statuses | Each feature's status before and after, with why it moved |
| 8. Next | Open issues, and what a second pilot should try |

### 8.2 Problems

One row per problem: its number in the report, when it happened (flow, step, PR link), what happened, its kind (blocker, worked around, or cosmetic), the troy-mode feature it belongs to (F01 to F10), and the fix (PR link) or the open issue. Problems come from troy-mode's escalations and failed attempts on the pilot's PRs, the hooks' blocks, Troy's remarks, and anything the F11 session sees in the transcripts that breaks a design or a rule.

### 8.3 Rule candidates

- **For the project:** the repeated problems that the retrospective found (F08 D76), the rules Troy picked, and what the rule change flow did with each.
- **For troy-mode:** problems that repeated across the pilot's features or flows and would be prevented by a rule or check for every project. The report proposes them, and each one Troy accepts becomes an issue in troy-pstack, built later through troy-pstack's process.

### 8.4 Time and cost

| Measure | Source |
| --- | --- |
| Role runs per feature and stage, with model and effort | The pilot sessions' transcripts: each Agent call |
| Cost in US dollars per feature, per role, and for the main session | Token counts by model in the transcripts, subagents included, at the list prices of the day. Where the desktop app shows a session's cost, the report gives it next to the computed figure. |
| Elapsed time per feature | The first PR's creation to the acceptance PR's merge, from GitHub |
| Review rounds, attempts, and escalations per stage | troy-mode's comments on the PRs (F07 section 8.4), as `retro` counts them |
| Times troy-mode waited for Troy, and Troy's time | Troy's messages in the transcripts, and Troy's own estimate at the end |
| CI minutes | `gh run list` durations for the pilot repository |
| Hook blocks | The project's `hooks.log` (F05 section 10) |

From the trials' figures, a version of 4 or 5 features takes about 50 to 70 role runs and about $50 to $90, plus about 35 PRs of a few Actions minutes each. Troy's own time is estimated at 2 to 3 hours, spread over the pilot: mostly the requirements conversation, the six approvals of the first three features, and the device test. The report compares the real figures with these.

The scripts that read the transcripts live in the F11 session's scratchpad. They are not committed, because they serve this report only.

### 8.5 The guide

Each place where the guide was wrong, missing, or unclear while Troy followed it, and the fix. The guide PR (section 7) lands before the final status PR, so F10's status can move.

## 9. Statuses (D100)

Two status PRs in troy-pstack, each its own PR:

1. **When the pilot's first feature is accepted.** F11 reads "Used on a real project, in progress: troy-mode set up <project> and accepted its first feature. v0.1 is not released yet." Every feature whose condition below has been met by then moves too.
2. **When the version is done** (section 5) and the report and the guide fixes have merged. F11 reads "Used on a real project: troy-mode took <project> from requirements to v0.1.0, which Troy accepted on Troy's devices on <date>. The pilot report lists <n> problems: <m> fixed, <k> open as issues." The other features move as below.

| Feature | Moves to "Used on a real project" when the pilot | Its design |
| --- | --- | --- |
| F01 | writes its documents from troy-mode's templates | |
| F02 | runs `troy-check pr` as CI on its PRs | |
| F03 | runs its pack's CI job and `troy-check code` on its code PRs. Only the pack used moves. | |
| F04 | runs every role | |
| F05 | runs with the hooks on | |
| F06 | starts with troy-init | F06 section 11.5 |
| F07 | runs on troy-mode | F07 section 14.4 |
| F08 | releases a version | F08 section 11.4 |
| F09 | adds or changes a rule (D99) | F09 section 10.4 |
| F10 | is done with the guide's fixes merged | F10 section 9.5 |

Each new status says what really happened, with the pilot repository's name, as R13 asks. A feature whose condition was not met keeps its status, and the report says why.

## 10. How F11 maps to the requirements

| Requirement | Where F11 covers it |
| --- | --- |
| F11 row: one small real project through one version | Sections 3 to 5 |
| 3.3: where Troy takes part | Section 6.1 |
| 5.1 to 5.10: the flows | Sections 4 and 5, run by troy-mode |
| 5.5 step 6 and 5.8: the retrospective and the rules it proposes | Section 8.3 |
| 7.1 and R13: status labels | Section 9 |
| Section 8: Cost, Privacy, and Platform | Sections 3.1 and 8.4 |
| Q6: existing projects | Sections 3.2 and 4 |
| Q10: the pilot is the first full run of the pipeline | Section 1 |

## 11. Not in F11

- A second pilot, such as an existing project or troy-voice (section 3.2). The report proposes one.
- The F07 fix for C/C++ projects, unless Troy picks a C/C++ project (section 3.3).
- Supporting `packages/<name>/` layouts or the TypeScript/JavaScript pack.
- Deploying or publishing the pilot's version anywhere (requirements section 9).
- Fixing problems that do not block the pilot, beyond opening their issues.
- Deleting the pilot repository or `ZJUCao/troy-mode-trial`.

## 12. Decisions for Troy

F10's design ends at D92, so F11 continues from D93. Troy accepted every recommended answer on 2026-11-08.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D93 | Which project is the pilot? | A: a new small Python project of Troy's idea, or, if Troy names none, a Python command-line version of Troy's recipe apps: recipes, a week's menu, and its shopping list (candidate 1). B: `nuo_voice` (candidate 2). C: HiLog in `HiCommonUtils` (candidate 3), with the F07 fix first. D: another project Troy names. | A. The first pilot should run the main path that F01 to F10 were built for, from an empty folder to a released version, with nothing to adapt first. B and C each need work before the pilot can start, and test adoption of existing code, which suits a second pilot. |
| D94 | How big is "one version"? | A: the project's v0.1, 4 or 5 features, released and accepted, with the retrospective done (section 5). B: 2 features. C: whatever the version plan says, with no limit. | A. Four features is the fewest that reaches F07 D62's question and a feature whose designs troy-mode merges itself. More than five makes the pilot long before its first lessons come back. |
| D95 | How does Troy run the pilot? | A: Troy types the requests in a desktop session in the pilot folder: the start, "the rest of v0.1", "release v0.1", and "continue" after a break; troy-mode stops only at Troy's steps (section 6.2). B: the coordinating session starts a session in the pilot folder for each request, and Troy answers in those sessions. C: nested `claude -p` sessions with Troy's answers in the prompts, as in the trials. | A. It is how Troy will use troy-mode after the pilot, and the guide describes it. It takes about eight short requests. B is untested: a session started for Troy may not be able to run a skill that only Troy may type. C is a trial, not real use. |
| D96 | What happens when troy-mode breaks during the pilot? | A: a blocker stops the pilot until troy-pstack fixes it through its own process and a new plugin version, which Troy installs and troy-mode brings into the project with its upgrade. Other problems become issues and are fixed later (section 7). B: work around every problem by hand and fix them all after the pilot. | A. The pilot then runs only on troy-mode as shipped, so its results hold. A workaround by hand needs Troy's yes and is recorded as a problem. |
| D97 | Where is the pilot written down? | A: a pilot report `docs/troy-mode/pilot/<project>-v0.1.md` with its mirror, in troy-pstack, in one PR at the end, plus an issue in troy-pstack with the `pilot` label for each problem (section 8). B: issues only. C: a report inside the pilot project. | A. The report is about troy-mode, so it belongs with troy-mode's documents, and the issues track each fix. The pilot project keeps only its own documents. |
| D98 | How may troy-mode merge in the pilot project? | A: before the start, Troy adds `Bash(gh pr merge *)` to the pilot project's `.claude/settings.local.json`, the line F10's guide gives, as troy-pstack has (F10 section 4.3). B: Troy approves each merge when Claude Code asks. C: the same rule in Troy's user settings, for every project. | A. troy-mode merges only within its rights (R18), and without the rule auto mode may refuse its merges, as it once did in troy-pstack. B adds about 35 prompts. C reaches projects that do not use troy-mode. |
| D99 | Must the pilot add a rule? | A: no. A rule is added when Troy wants one, from the retrospective or during the pilot. F09's status moves only if that happens. B: yes, Troy adds at least one real project rule, so F09 is used. | A. A rule added only to use F09 is not real use, and its trial already covers the flow. |
| D100 | When do the statuses move? | A: two status PRs, one when the pilot's first feature is accepted and one when the version is done and the report has merged, each moving only the features whose condition was met (section 9). B: one status PR at the end. | A. The pilot may take several days, and Troy follows progress in the status table (requirements 3.3), which should not say "Not started" while the pilot runs. |

Requirements 1.27 records the approved changes:

- The F11 row says how the pilot runs: the project Troy chose (D93), the size of the version (D94), how Troy runs it (D95), what happens on a blocker (D96), and the report (D97). Requirements 1.26 already made it depend on F10 (F10 design D91).
- Troy picked a Python project, so the F11 row does not depend on the F07 fix of section 3.3.

## 13. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-08 | First draft. |
| 1.0 | 2026-11-08 | Approved by Troy with D93 to D100, every recommended answer. |
