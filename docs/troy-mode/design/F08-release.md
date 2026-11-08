# F08 design: the version release flow

| | |
| --- | --- |
| Feature | F08 in [requirements 1.24](../requirements.md#72-feature-list) |
| Version | 1.0 |
| Date | 2026-11-08 |
| Status | Approved by Troy on 2026-11-08, with D70 to D78. |
| Source of truth | This English file. [`F08-release.zh-CN.md`](F08-release.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F08 adds the version release flow (requirements 5.5) to troy-mode's entry skill (F07). With it, the main session:

1. has the Test Manager write each version's test plan before the version's first feature starts (5.5 step 2, D70);
2. on "release v0.1", checks that the version is ready, has the Test Engineer write the version's automated tests, and runs the release test on Troy's PC (5.5 step 3, 5.6, D71);
3. opens a release PR that holds the changelog, and asks Troy to test the version on Troy's devices and accept it (3.3 step 4, D72);
4. sends each bug found through the bug flow and runs the release test again (5.5 step 4, D74);
5. after Troy accepts, merges the release PR and makes the tag `vMAJOR.MINOR.PATCH` as a GitHub release (5.5 step 5, D73);
6. runs the retrospective and hands the rules Troy picks to the rule change flow (5.5 step 6, D76);
7. releases a patch, such as v0.1.1, for bugs fixed after a release (D75).

F08 also settles the point that F07 left open: F07's `approve` adds a row to the document's change log (D77).

Version planning (5.5 step 1) is already the Product Manager's PM1 (F04 section 6.1), and F07 reads the version plan. F08 adds no skill: it extends F07's skill and engine. It lands in one PR, as Q10 says for every feature.

## 2. Location

```text
skills/
  troy-mode/
    SKILL.md                  gains the section "Version release" (sections 4 to 8)
troy-mode/
  flow/
    troy_flow.py              gains the commands of section 3
    troyflow/                 new modules (the Developer's choice)
    tests/                    unit tests (section 11.1)
```

Section 9 lists the changes to F01 to F04 and F07. The engine stays on Python 3.11 or newer and the standard library (F07 section 2).

## 3. The engine

### 3.1 Commands

```text
python troy_flow.py release-test   --version <vX.Y> --junit <path>... [common options]
python troy_flow.py accept-version --tag <vX.Y.Z> --notes-file <path> [--date <YYYY-MM-DD>] [common options]
python troy_flow.py release-notes  --tag <vX.Y.Z> --out <path> [common options]
python troy_flow.py retro          --tag <vX.Y.Z> [common options]
```

| Command | What it does |
| --- | --- |
| `release-test` | Reads the version test plan on `origin/main` and the JUnit files of the release test (section 5.5). Gives each scenario's result, the failed tests, the scenarios Troy runs with their devices and steps, the commit tested, and the text of the comment `Release test, run <n>: passed` or `failed`. Exit code 1 when anything failed. |
| `accept-version` | Records Troy's acceptance in the version test plan and its mirror: a row in the acceptance record (date, "Accepted" with the tag, and Troy's notes), the next major version, and the status "Accepted by Troy on <date>", with D77's change-log row (section 5.7). |
| `release-notes` | Writes the tag's section of `CHANGELOG.md` on `origin/main` to a file, for the GitHub release's notes. |
| `retro` | Gathers the evidence for the retrospective from GitHub and groups it (section 7). It changes nothing. |

- `status` gains the release state and its next actions (sections 3.2 and 3.3). `brief` learns TM7 and TE5, and the reviews of a version tests PR (section 5.3). `approve` gains D77's change-log row (section 8).
- As in F07, the engine reads git and GitHub and never commits, pushes, or writes to GitHub. The skill does that (F04 D29). The exit codes are F07's.

### 3.2 State

The release state lives in git and on GitHub, like the rest of F07's state (D58).

| What | Read from |
| --- | --- |
| Each feature's version, and the versions in order | The features table's Version column and the version plan, in `docs/requirements.md` on `origin/main` |
| A version's test plan | `docs/versions/<vX.Y>/test-plan.md` on `origin/main`. Its section 1 lists the features it covers. |
| A version's tests | A commit `[vX.Y tests] ...` on `origin/main` |
| The release PR | An open PR titled `[docs] Release vX.Y.Z`, or that commit subject on `origin/main` |
| Release test runs and Troy's results | F08's comments on the release PR (section 5.6) |
| Released versions | GitHub's releases of the repository, read with `gh release list` |
| The retrospective | A `Retrospective: vX.Y.Z` comment on the merged release PR |

### 3.3 Next actions

`status` gives these new `next.action` values. They come after F07's setup steps and after the open PRs, which F07 continues first.

| Action | When | What follows |
| --- | --- | --- |
| `version-test-plan` | The next feature's version has no test plan, or its plan lists other features than the requirements give that version (section 4) | TM7 on `troy-mode/<vX.Y>-test-plan`, merged by F07 |
| `release` | Every feature of the earliest version without a release is accepted. `next.step` names the release's next step from the state: `version-tests` when the plan has scenarios that Claude runs and no `[vX.Y tests]` commit is on `origin/main`, then `release-pr` when no release PR exists, then `release-test` when the release PR has no run or its newest run failed and every bug found since is fixed | Section 5 |
| `tag` | The release commit is on `origin/main` and GitHub has no release for its tag | Section 5.7 |
| `retro` | A version, not a patch, is released and its release PR has no `Retrospective:` comment | Section 7 |

- While a release is in progress, its release PR comes after every other open troy-mode PR, such as a bug's PRs, because it waits for them. F07's rule puts side PRs before stage PRs and otherwise takes the lowest number (F07 section 5.1).
- When a release PR waits for Troy, `status` gives it in `waiting_on_troy`, as F07 does for an approval.

## 4. The version test plan (D70)

The Test Manager writes a version's test plan when the version is planned (5.5 step 2). In practice, `status` asks for it before the first stage of any feature of that version that has not started:

1. **TM7** fills the `version-test-plan` template as `docs/versions/<vX.Y>/test-plan.md` and its mirror, from the requirements' user flows, prototypes, performance targets, and version plan. Each scenario says who runs it: Claude, as an automated version test, or Troy, by hand on a device that only Troy has, such as a phone (D71). Performance and stress cases come from the targets in the requirements.
2. **The main session** checks the plan against the requirements as the Product Manager: every feature of the version appears, and every user flow of those features has a scenario. A gap goes back to TM7 as Input. No other role reviews it.
3. **The PR** is `[docs] Add the v0.1 test plan`. F07 merges it, because requirements 3.3 does not list it among Troy's approvals. Troy reads it when the release asks for Troy's test.

When the version's features change through a requirement change, the plan's feature list no longer matches, and `status` asks for TM7 again: `[docs] Update the v0.1 test plan`. A change inside a feature that keeps the list the same reaches the plan through TM2's review of the version tests (section 5.3).

## 5. The release

### 5.1 Steps

"Release v0.1", or "continue" when `status` gives `release`, starts these steps. "Release" alone means the version that `status` names.

| Step | What happens | PR | Merged by |
| --- | --- | --- | --- |
| 1. Ready | The checks of section 5.2 | None | |
| 2. Version tests | TE5 writes the tests of the scenarios Claude runs. TM2 and CR1 review them together. Skipped when no scenario is Claude's. | `[v0.1 tests] End-to-end and stress tests`, on `troy-mode/v0.1-tests` | F07 |
| 3. Release PR | PM4 drafts the changelog section, in the main session | `[docs] Release v0.1.0`, on `troy-mode/release-v0.1.0` | F07, after Troy accepts |
| 4. Release test | The regression and the version tests on Troy's PC. The report goes on the release PR. | None | |
| 5. Troy's test | Troy runs Troy's scenarios on Troy's devices and replies | None | |
| 6. Acceptance | PM4 sets the statuses, and `accept-version` fills the acceptance record. Then the merge. | The release PR | F07 |
| 7. Tag | A GitHub release `v0.1.0` on the release PR's merge commit | None | |
| 8. Retrospective | Section 7 | None | |

### 5.2 Ready

F08 checks, and reports each problem with what fixes it:

- Every feature of the version is accepted: its `accept` commit is on `origin/main`.
- No open troy-mode PR. The open PRs go first, as F07 continues them.
- No open issue labeled `bug`, unless Troy deferred it (D74).
- No mock, tests, implementation, or acceptance PR of a later version's feature has merged since the previous release. Otherwise the tag would hold a feature the version does not include. F08 escalates this case (5.7), with Troy's options.
- The version's test plan lists the version's features (section 4).
- The project's copy of troy-mode's files matches the plugin's. The version tests PR needs the new troy-check (section 9). When `status` says the copy is older, F08 first runs troy-init's upgrade through its PR flow, as F07 does for "upgrade troy-mode" (F07 section 10).

### 5.3 Version tests (D71)

- **Where.** Version tests live in the top-level folder `version-tests/`, which troy-check classes as tests (section 9). The language packs' per-PR test runs do not collect it: pytest collects only `tests/`, and the C/C++ pack builds version tests only when the release test asks for them. So the per-PR regression stays at unit, functional, and integration tests, as 5.6 says.
- **TE5** writes one test for each scenario that the plan has Claude run, and one for each performance and stress case. Each test's own name starts with its scenario ID: `test_v0_1_s01_counts_words_and_lines` in Python, `TEST(Version, V0_1_S01_CountsWordsAndLines)` in C++. Tests work through the project's external interfaces, as a user would (TE1's rule). TE5 runs them against the code on `origin/main`. A test that fails there stays as written: TE5 lists it in its report with the scenario's expected result and what happened, and never bends the test to pass (F04 common rule 11).
- **Reviews.** TM2 checks that every scenario Claude runs has a test, that no test lies outside the plan, that each test checks the scenario's expected result, and that a failing test fails because the code differs from the plan, not because the test is wrong. CR1 reviews the code. When TM2 finds that a scenario no longer matches the requirements, the plan goes back to TM7 in a `[docs]` PR first.
- **Merge.** F07 merges the PR when the reviews approve and CI passes, even when some version tests fail, because CI does not run them. A failing scenario is a finding of the release test (section 5.8).
- **Later versions** add their tests to the same folder, and every release runs all of them, so the scenarios of earlier versions stay as regression. A patch release adds none (section 6). A wrong version test is fixed by TE3 in a `[v0.1 tests] Fix v0.1-S03` PR, on TM4's ruling.

### 5.4 The release PR (D72)

On `troy-mode/release-v0.1.0` from `origin/main`, under a snapshot with `--role product-manager`:

- **PM4** adds the version's section to `CHANGELOG.md` and its mirror, from the `changelog` template, and creates both files for a project's first release. The engine's `status` lists the version's features and the bugs fixed since the previous release, from the commit subjects. PM4 sorts them into Added, Changed, and Fixed. A feature that changes an accepted one (F07 D65) goes under Changed. The section's date is the day of the release PR, and PM4 changes it to the day of Troy's acceptance in step 6.
- **The description** says Why (the version's line in the version plan), What (the changelog section and the features), and Checks.
- F07 pushes the branch and opens the PR. Every later step comments on this PR, so a new session finds the release where it stopped.

### 5.5 The release test

On Troy's PC, on the release branch, which holds `origin/main` plus the changelog:

1. **Regression.** The language pack's steps, as for an implementation PR (F07 section 8.1), with `troy-check code`. Every test must pass, or skip on this platform with CI's result on `main` (F07 D69).
2. **Version tests.** The pack's release command, from the brief's checks. Python: `pytest version-tests --junitxml=reports/version-junit.xml`. C/C++: a build with `TROY_VERSION_TESTS=ON`, then `ctest -L version` with `--output-junit reports/version-junit.xml`. Performance and stress cases run here, on Troy's PC (Q7).
3. **The report.** `release-test --version v0.1 --junit reports/junit.xml --junit reports/version-junit.xml`. F08 posts its comment on the release PR: `Release test, run 1: passed` or `failed`, then each scenario with its result and the failed tests.

The run passes when no test failed and every scenario Claude runs has a passing test. Failures go to section 5.8 before Troy is asked to test.

### 5.6 Troy's test

After a run that passed, F08 posts `Waiting for Troy: accept v0.1.0` on the release PR, runs `status --waiting`, and tells Troy in chat, in Troy's language:

- the commit to test, and the release PR's link with the changelog;
- the scenarios Claude ran, with their results;
- each scenario Troy runs: the device, the steps, and the expected result, from the plan.

Then it stops. Troy replies in chat or in a comment on the release PR:

| Troy's reply | What F08 does |
| --- | --- |
| Accepted, with any notes | Section 5.7 |
| A scenario failed | Section 5.8. Troy then tests again only the scenarios that failed, unless Troy asks for more (D74). |
| Not accepted, for a reason that is not a bug, such as a feature that is not what Troy wanted | The requirement change flow (F07 section 11.2). The release waits until the changed features are accepted. |

F08 records each reply on the release PR as `Release test by Troy, run <n>: accepted`, `failed`, or `not accepted`, followed by Troy's words, so a new session knows the answer.

### 5.7 Acceptance and the tag (D73)

On Troy's acceptance:

1. **PM4**, on the release branch under a snapshot with `--role product-manager`: each feature of the version gets the status "Usable on Troy's devices" in both languages (F01 section 7, R13), the requirements' `version` rises by one minor step with a change-log row, and the changelog section takes the day of acceptance.
2. **`accept-version --tag v0.1.0 --notes-file <file>`**, with Troy's notes in the file.
3. **Merge.** F07 stages both sets of paths, amends the commit, runs the local checks, pushes, waits for CI, and merges (F07 section 8.6).
4. **Tag.** `release-notes --tag v0.1.0 --out <file>`, then `gh release create v0.1.0 --target <merge commit> --title v0.1.0 --notes-file <file>`. GitHub creates the tag on that commit, so nothing is pushed from Troy's PC.
5. **Report** to Troy, and `status --write-progress`.

If Troy merges the release PR on GitHub instead, the statuses and the acceptance record are missing. `status` then gives `[docs] Record Troy's acceptance of v0.1.0`, which F07 opens and merges before the tag.

Creating the GitHub release joins F07's rights (F07 section 9). It happens only after Troy's acceptance, and only for the release PR's merge commit.

### 5.8 Failures and bugs (D74)

- **A failed test or scenario,** in the release test or in Troy's test, goes to TM5 with the report in Input. A bug gets an issue and the bug flow's PR A and PR B (F07 section 11.1). A wrong version test gets TE3's fix (section 5.3). A misunderstood requirement goes to the change flow.
- **Open bugs.** The release waits until every open `bug` issue is fixed. Troy may defer one in chat: F08 notes it on the release PR, and `accept-version` puts it into Troy's notes in the acceptance record.
- **After the fixes,** PM4 adds the fixed bugs to the changelog section, F07 rebases the release branch on `origin/main` and amends the commit, and the release test runs again as run 2. It runs every version test, because they are cheap. Troy tests again only what failed.

## 6. Patch releases (D75)

"Release v0.1.1" releases the bug fixes merged since v0.1.0. It is allowed only while no mock, tests, implementation, or acceptance PR of a later version's feature has merged since v0.1.0. Otherwise the fixes ship with the next version, and F08 says so.

A patch release runs steps 1 and 3 to 7 of section 5.1. It writes no version test plan and no version tests. The release test runs the same regression and every version test. Troy tests the scenarios that the fixed bugs touched. The changelog section `v0.1.1` lists only Fixed. The features keep their statuses. `accept-version` adds a row for v0.1.1 to v0.1's acceptance record. A patch has no retrospective.

## 7. Retrospective (D76)

After a version's tag, F08 turns the problems that repeated during the version into proposed rules (5.5 step 6):

1. **Evidence.** `retro --tag v0.1.0` reads the PRs merged since the previous version's tag, or since the project's first PR. It gathers F07's comments on them: every review that requested changes, with its findings grouped by the rule ID or checklist item each one names (F04 section 5.2); every failed attempt, with the checks that failed; and every escalation. It adds the bugs fixed in that time, from their issues, and the `hooks.log` lines still on Troy's PC (F05 section 10). It counts each group across PRs. A group seen in two or more PRs is a repeated problem, which is how `correct` counts a mistake class.
2. **Proposals.** The main session follows `correct`'s method (`${CLAUDE_PLUGIN_ROOT}/skills/correct/SKILL.md`) on the repeated problems: for each one, the strongest enforcement that works (requirements 5.8 step 2), and whether it belongs to this project or to every troy-mode project. It writes no code: every proposal is a rule for the rule change flow.
3. **Troy picks.** One message to Troy: each repeated problem with its evidence and PR links, and each proposal with a recommendation. When nothing repeated, the message says so. F08 posts the same report in English on the release PR as `Retrospective: v0.1.0`, which ends the release.
4. **Rules.** Each rule Troy picks runs through the rule change flow (5.8, F09), one at a time. If F09 is not built yet, F08 says so and lists the picked rules in the progress file's notes.

`reflect`, which requirements 4.1 also names, mines one conversation's transcript. A version spans many sessions, so F08 reads the PR comments instead, which hold the same reviews and failures.

## 8. Recording an approval in the change log (D77)

F07's `approve` changes only header fields (F07 D61), so a document's change log skips the version that Troy's approval gives it. The trial repository's requirements show this: version 2.0, with change-log rows for 0.1, 1.1, and 1.2 only.

F08 makes `approve` also add a row to the document's change log, in both languages: the new version, the date, and "Approved by Troy." (Chinese "Troy 批准。"). The row goes last in the table whose heading is the document's change log. A document without a change log gets no row. `accept-version` adds its row the same way, with "Accepted by Troy as v0.1.0." This changes requirements 3.3: troy-mode records an approval in the document's header and change log.

## 9. Changes to earlier features

- **F01 templates.** In `version-test-plan`, the scenarios table gains a column "Run by", Claude or Troy, and the performance and stress table gains the same column. The README's PR kinds gain `[v0.1 tests]`. F01's design gets a change-log row.
- **F02 troy-check.**
  - A new title kind: `[v<MAJOR>.<MINOR> tests] <summary>`, kind `version-tests`, which may change the `tests` and `dependencies` classes. R03 skips it.
  - The built-in `tests` patterns gain `version-tests/**`.
  - F02's design gets a change-log row.
- **F03 language packs and `troy-check code`.** A `version-tests` PR is "any other kind" for R09 and R10: nothing must fail, and the tests of accepted features and fixed bugs must pass. The Python pack needs no change, because `testpaths = ["tests"]` leaves `version-tests/` out. The C/C++ pack's `cmake/troy.cmake` gains `troy_add_version_test`, which builds a version test only when `TROY_VERSION_TESTS` is on and labels its tests `version`. Both READMEs give the release command, and F07's engine gives it in the brief's checks. F03's design gets a change-log row.
- **F04 roles.**
  - TE5, a new task: the version tests of section 5.3.
  - TM7 says who runs each scenario. TM2 also reviews `[vX.Y tests]` PRs, against the version test plan.
  - PM4 drafts the changelog when the release starts, and sets the statuses after Troy accepts.
  - F04's design gets a change-log row.
- **F07 entry skill.** The routing table sends "release" requests to F08. `status`, `brief`, and `approve` change as section 3 says. F07's rights gain the GitHub release of section 5.7. F07's design gets a change-log row.
- **F05 and F06** do not change. The Test Engineer's scope is the `tests` class, which now holds `version-tests/`. troy-init's upgrade brings the new templates and troy-check to a project.

**C/C++ registration.** In a C/C++ project, tests are registered in `CMakeLists.txt`, which is in the `dependencies` class. F07's check after each run flags a change there unless `--allow-dependency` names it, so a C/C++ test PR, and a C/C++ version tests PR, cannot pass that check yet. F07's trials used Python only. F08 does not fix this, because it belongs to every C/C++ test PR (section 12).

## 10. How F08 maps to the requirements

| Requirement | Where F08 covers it |
| --- | --- |
| F08 row: the version release flow (5.5) | Sections 4 to 7 |
| 3.3 step 4: Troy approves each version by testing it on Troy's devices | Sections 5.6 and 5.7 |
| 5.5 step 1: the version plan | F04's PM1, read by `status` (section 3.2) |
| 5.5 step 2: the version test plan, written when the version is planned | Section 4 |
| 5.5 step 3: the release test on Troy's devices | Sections 5.3, 5.5, and 5.6 |
| 5.5 step 4: bugs go through the bug flow | Section 5.8 |
| 5.5 step 5: the tag and the changelog | Sections 5.4 and 5.7 |
| 5.5 step 6: the retrospective | Section 7 |
| 5.6: version tests: Test Manager designs, Test Engineer implements, Product Manager and Troy accept | Sections 4, 5.3, and 5.7 |
| Q7: performance tests on Troy's PC at release | Section 5.5 |
| R13: status labels | Section 5.7 |
| R14, R15 | R14: TM7 plans the performance cases from the targets. R15: bugs found at release keep their reproduction tests (F07 section 11.1). |
| 4.1: `correct` and `reflect` | Section 7 |
| F07 D58: state in git and on GitHub | Section 3.2 |

## 11. How F08 is checked

### 11.1 Tests

Tests use `unittest` and the standard library. A separate agent writes them from this design before the code exists. They follow F07's setup: a temporary git repository with a local bare `origin`, and a fake `gh` on the `PATH` that serves PRs, comments, issues, and releases from a JSON file and records its calls. They live in `troy-mode/flow/tests/`, and the troy-check, template, and role changes add tests in their own suites.

| Group | Cases include |
| --- | --- |
| Status | `version-test-plan` before the first stage of a version without a plan, and again when the plan's feature list differs. `release` once every feature of the version is accepted. The release's steps `version-tests`, `release-pr`, and `release-test`, then `tag` and `retro`, in turn. No `version-tests` step when the plan has no scenario that Claude runs. The release PR after a bug's PRs. Waiting for Troy after a passing run. A patch allowed, and refused after a later version's implementation merged. |
| Release test | Scenarios matched to tests by ID, with case, `-`, `_`, and `.` alike. A scenario run by Claude with no test fails. A failed regression test fails. A test skipped on this platform passes. Troy's scenarios listed with devices and steps. The comment's heading and run number. |
| Accept and approve | `accept-version` writes the acceptance row, the next major, the status, and the change-log row in both languages. `approve` adds the change-log row in both languages, and none to a document without a change log. |
| Notes and retro | `release-notes` writes exactly the tag's section. `retro` reads only the PRs since the previous tag, groups findings by rule and checklist item, counts across PRs, and tells Troy's comments apart. |
| Briefs | TM7, TE5, and the version tests reviews: Read first, the title, and the release command in the checks for Python and C/C++. |
| troy-check | The `[v0.1 tests]` title parses, and its kind may change tests and dependencies only. `version-tests/**` is in the tests class. R09 and R10 treat the kind as "any other kind". |
| Templates and roles | The "Run by" columns in both languages. TE5 in the Test Engineer's agent file and in F04's structure tests. |

### 11.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: the version test plan not asked for before a version's first feature, the plan's feature list not compared, a release offered with a feature not accepted, the release PR continued before a bug's PR, a scenario without a test counted as passing, a skipped test counted as failing, the acceptance row written in English only, `approve` without the change-log row, notes taken from the wrong section, a patch allowed after a later version's implementation merged, `retro` reading PRs from before the previous tag, and a finding seen once counted as repeated. The counts go in the PR description.

### 11.3 Trial (D78)

Before the PR opens, F08 runs in nested `claude -p` sessions on Troy's PC, with troy-pstack loaded from the PR branch, on the private scratch repository `ZJUCao/troy-mode-trial`, as F07's trials did (F07 section 14.3). The trial's prompt gives Troy's answers, including Troy's device results. These sessions reach GitHub, so the trial starts only after Troy says yes in chat.

The repository's v0.1 holds F01 (accepted), F03 (at stage 4), and F02 (not started).

1. **Upgrade.** troy-init's upgrade brings the new troy-check and templates, through its own PR.
2. **Smaller version.** A requirement change moves F02 to v0.2, so v0.1 is F01 and F03. Troy's approval is given in the prompt.
3. **Version test plan.** "Continue" asks for v0.1's test plan before F03 goes on. TM7 writes it, and F07 merges it.
4. **F03.** F03 runs through its tests, implementation, and acceptance PRs.
5. **Release.** "Release v0.1": TE5 writes the version tests, TM2 and CR1 review them, and the release test runs on Troy's PC. The release PR waits for Troy, and that session ends.
6. **Resume and accept.** A new session gets Troy's acceptance from the prompt, merges the release PR, and creates the GitHub release `v0.1.0`.
7. **Retrospective.** `retro` over every PR since the start. Troy's answer, from the prompt, picks no rule.
8. **Routing.** "Release v0.2" reports that F02 is not accepted. "Release v0.1.1" reports that no fix has merged since v0.1.0.

It takes about 9 role runs (TM7, TE1, TM2, CR1, DV2, CR1, TE5, TM2, CR1), about $8 to $12 from F07's trials, plus a few minutes of Actions for each of about 9 PRs. The repository and its release stay. Deleting them is Troy's call.

### 11.4 Status

| When | F08's status in requirements 7.2 |
| --- | --- |
| The F08 PR merges after a passing trial | Runs on a sample project: troy-mode wrote the version test plan of a scratch GitHub project and released its v0.1.0, with version tests, a release test on Troy's PC, Troy's acceptance given in the trial's prompt, a GitHub release, and a retrospective. Not yet used on a real project. |
| The pilot (F11) releases a version | Used on a real project |

If the trial cannot run before the PR, the status is "Written" until it does. The status update is its own PR.

## 12. Not in F08

- Building, installing, or deploying the version onto Troy's devices, or publishing it anywhere (requirements section 9).
- Running version tests in CI.
- Release branches. A patch is released from `main` only (D75).
- The rule change flow itself (F09).
- The C/C++ registration problem of section 9, which needs a fix to F07's check for every C/C++ test PR.

## 13. Decisions for Troy

F07 ends at D69, so F08 continues from D70. Troy accepted every recommended answer on 2026-11-08.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D70 | When does the Test Manager write a version's test plan? 5.5 says "when the version is planned, not at the end". | A: before the first stage of the version's first feature that has not started. `status` asks for it then, and again when a requirement change changes the version's features (section 4). B: all versions' plans as soon as Troy approves the requirements. C: when the release starts. | A. The plan is written before the version's code, as 5.5 asks, and each plan sees the designs of the versions before it. B writes plans for versions that may change a lot before they start. C writes the plan after the code. |
| D71 | Who writes and runs the end-to-end, stress, and performance tests? 5.6 says the Test Manager designs them, the Test Engineer implements them, and they run on Troy's devices. | A: each scenario in the plan says who runs it. Claude's scenarios become version tests, which TE5 writes in `version-tests/` when the release starts and which run only at release, on Troy's PC. Troy's scenarios are steps that Troy follows on Troy's own devices (section 5.3). B: no test code; Claude and Troy run every scenario by hand from the plan. C: as A, but the version tests also run in CI on every PR. | A. The scenarios that a script can run are repeatable and stay as regression for later releases. Troy is asked only for what needs Troy's devices. C would put slow end-to-end and timing tests into every PR's CI, which 5.6 keeps out. |
| D72 | Where do the release's report, Troy's answer, and the changelog live until the tag? | A: a release PR `[docs] Release v0.1.0`, opened when the release test starts. The release test report and Troy's results are comments on it. Troy accepts in chat, and F08 then adds the statuses and the acceptance record and merges it (sections 5.4 to 5.7). B: a GitHub issue per release, with a `[docs]` PR only after Troy accepts. C: the progress file only. | A. Troy sees the changelog while testing, and a new session finds the release on GitHub, as F07 D58 needs. C is lost with the progress file. B adds an issue that the PR already does the job of. |
| D73 | How is the tag made? | A: `gh release create v0.1.0 --target <merge commit>`, which creates the tag on GitHub and a release page with the changelog section as notes (section 5.7). B: an annotated git tag, pushed from Troy's PC, with no release page. | A. One command, nothing pushed from Troy's PC, and the release notes are readable on GitHub. A release page is not a deployment, so requirements section 9 still holds. |
| D74 | What happens to bugs at release time? 5.5 says that bugs found go through the bug flow. | A: open `bug` issues are fixed before the release, unless Troy defers one in chat, which the acceptance record then names. After the fixes, the release test runs every version test again, and Troy tests again only the scenarios that failed (section 5.8). B: the release ignores open bugs, and Troy tests everything again after each fix. | A. Troy accepts a version knowing its open bugs, and each retest asks Troy only for what changed. |
| D75 | Are there patch releases, such as v0.1.1? | A: yes. "Release v0.1.1" releases the fixes merged since v0.1.0, while no code PR of a later version's feature has merged since then. It skips the version test plan, the version tests, and the retrospective (section 6). B: no. Fixes ship with the next version. | A. A released version that Troy uses can get its fixes without waiting for the next version. Without release branches, a patch is possible only before the next version's code lands, and F08 says when it is not. |
| D76 | How does the retrospective work? | A: the engine gathers the version's review findings, failed attempts, escalations, and bugs from F07's comments and the issues, grouped by rule and checklist item. The main session follows `correct`'s method on the problems seen in two or more PRs and proposes rules. Troy picks, and each picked rule runs through the rule change flow. The report is a comment on the release PR (section 7). B: as A, plus a `docs/versions/<vX.Y>/retrospective.md` document. C: the main session reads the PRs itself, with no engine command. | A. Counting findings by rule is exact work that tests can check. The rules Troy picks are the lasting result, and they land in the rules table. B adds a document that nothing reads later. |
| D77 | F07's `approve` changes only header fields (D61), so a document's change log has no row for the version Troy's approval gives it. Should `approve` add one? | A: yes. `approve` adds "Approved by Troy." with the new version and date to the change log, in both languages (section 8). B: no. The header alone records the approval. | A. Every version then has its row, so the change log explains the jump from 0.3 to 1.0. This changes requirements 3.3 to say that troy-mode records an approval in the document's header and change log. |
| D78 | How is F08 tried out, and when does its status move? | A: tests and planted bugs, plus a trial on `ZJUCao/troy-mode-trial` that releases its v0.1.0 across a session break, with Troy's answers in the trial's prompt (section 11.3). B: the same, on a local bare `origin`, with no GitHub release or CI. Status "Written" until the pilot. | A. Only a real repository shows that the release PR, CI, the merge, and the GitHub release work end to end. It costs about 9 role runs, about $8 to $12, and a few Actions minutes, and starts only on Troy's yes in chat. |

Requirements 1.24 records the approved changes:

- The F08 row: the version test plan, the version tests, the release PR, the GitHub release, bugs at release, patch releases, the retrospective, and `approve`'s change-log row (D70 to D77).
- 3.3: troy-mode records an approval in the document's header and change log (D77).
- 5.5: the version test plan comes before the version's first feature (D70); each scenario says whether Claude or Troy runs it (D71); the tag is a GitHub release (D73); and patch releases (D75).

## 14. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-08 | First draft. |
| 1.0 | 2026-11-08 | Approved by Troy with D70 to D78, every recommended answer. |
