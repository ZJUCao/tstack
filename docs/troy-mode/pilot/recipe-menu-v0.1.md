# Pilot report: recipe-menu v0.1

| | |
| --- | --- |
| Feature | F11 in [requirements 1.38](../requirements.md#72-feature-list), [F11 design](../design/F11-pilot.md) section 8 |
| Version | 1.0 |
| Date | 2026-11-16 |
| Status | Read and approved by Troy on 2026-11-16. |
| Source of truth | This English file. [`recipe-menu-v0.1.zh-CN.md`](recipe-menu-v0.1.zh-CN.md) is the Chinese mirror. |

Times are EST, the clock on Troy's PC. Costs are at the API's list prices of the day: opus $4 per million input tokens and $20 per million output tokens, sonnet $2 and $10; cache writes cost 1.25 times the input price for 5 minutes and 2 times for an hour, and cache reads cost $0.20 (opus) and $0.10 (sonnet). Links to `#<n>` without a repository name are PRs of `ZJUCao/recipe-menu`.

## 1. Summary

- **Project.** `ZJUCao/recipe-menu`, a new private Python command-line tool for recipes, a week's menu, and its shopping list, in Chinese and English (F11 design D93).
- **Version.** v0.1 with 13 features, F01 to F13. On 2026-11-10 Troy chose to keep all 13 rather than D94's 4 or 5 (problem 4).
- **Dates.** Setup started on 2026-11-09 at 23:39. Troy accepted v0.1.0 on Troy's devices on 2026-11-16 at 02:55, and the GitHub release `v0.1.0` was created at 02:58 on the merge commit `14d0d88` of the release PR [#94](https://github.com/ZJUCao/recipe-menu/pull/94). The retrospective followed at 03:02, and the rule Troy picked for the project went through the rule change flow by 05:40 ([#97](https://github.com/ZJUCao/recipe-menu/pull/97)).
- **Outcome.** Every v0.1 feature reads "Usable on Troy's devices". 97 PRs merged, 94 for v0.1 and 3 for the rule P01, and CI passed on each, on #47 only after it merged (problem 13). The release test on Troy's PC passed 583 tests with 4 skipped there (Linux only), the 29 version tests, and a real run in which 48 of 48 prototype commands matched. Troy ran the three scenarios for Troy's devices and replied "All accepted".
- **troy-mode.** One desktop session ran the whole version, on plugin 0.2.0 and from [#78](https://github.com/ZJUCao/recipe-menu/pull/78) on 0.5.0, which brought the real run (F12), the mode guard (F13), and the summary for Troy (F14). No escalation, no bug, and one recorded failed attempt.
- **Problems.** 20 (section 3): 1 fixed, 13 open as issues in troy-pstack, and 6 that need no fix. Troy accepted three of the four rule candidates for troy-mode (section 4.2).
- **Cost.** $1,092 at list prices for 263 role runs and the main session, against the design's $50 to $90 for 4 or 5 features and the $130 to $235 estimated for 13 features on 2026-11-10 (section 5).

## 2. Timeline

| When | Step | PRs |
| --- | --- | --- |
| 11-09 23:20 | The F11 session checks the prerequisites. Troy installs plugin 0.2.0, sets `MAMBA_EXE`, adds the merge permission, and restarts the app. | |
| 11-09 23:39 | The pilot session starts in `D:\Troy\Projects\recipe-menu` with "start a project: a Python command-line tool for my recipes, a week's menu, and the shopping list for that menu, with Chinese and English text". | |
| 11-09 23:43 | Setup: troy-init creates the private repository, and the setup PR merges. | [#1](https://github.com/ZJUCao/recipe-menu/pull/1) |
| 11-10 00:10 | Troy answers the Product Manager's 14 questions ("All recommended") and approves the requirements: 16 features, v0.1 = F01 to F13. | [#2](https://github.com/ZJUCao/recipe-menu/pull/2) |
| 11-10 02:18 | Troy approves the architecture, with no series: Python 3.13 standard library only, 7 ADRs. | [#3](https://github.com/ZJUCao/recipe-menu/pull/3) |
| 11-10 02:21 | The language step adds the Python pack. | [#4](https://github.com/ZJUCao/recipe-menu/pull/4) |
| 11-10 03:26 | Troy keeps all 13 features in v0.1 (problem 4). | |
| 11-10 03:49 | The v0.1 test plan. | [#5](https://github.com/ZJUCao/recipe-menu/pull/5) |
| 11-10 14:16 | F01 accepted, with two side PRs to its design. | #6 to #13 |
| 11-10 20:08 | F02 accepted. | #14 to #19 |
| 11-11 11:58 | F03 accepted at 11:47. Asked the question after the first three features, Troy keeps approving the design and test plan of all 16. | #20 to #26 |
| 11-12 01:21 | F04 accepted. | #27 to #32 |
| 11-12 14:15 | F05 accepted, with an architecture change. | #33 to #39 |
| 11-12 19:19 | F06 accepted. | #40 to #45 |
| 11-13 00:12 | F07 accepted. | #46 to #51 |
| 11-13 11:47 | F08 accepted, with an architecture change. | #52 to #58 |
| 11-13 19:38 | F09 accepted. | #59 to #64 |
| 11-13 19:50 | The first status PR in troy-pstack (D100), late: it was due at F01's acceptance, but the F11 session learned of progress only when Troy wrote. | [troy-pstack#45](https://github.com/ZJUCao/troy-pstack/pull/45) |
| 11-14 04:07 | F10 accepted. | #65 to #70 |
| 11-15 03:37 | F11 accepted, with an architecture change. | #71 to #77 |
| 11-15 12:36 | Troy updates the plugin, and troy-mode upgrades the project to 0.5.0. | [#78](https://github.com/ZJUCao/recipe-menu/pull/78) |
| 11-15 16:11 | F12 accepted, with the first real run: 41 commands matched, 6 waited for F13. | #79 to #84 |
| 11-16 01:08 | F13 accepted, with a requirement change, as the first feature that "Ran for real on Troy's PC". | #85 to #91 |
| 11-16 02:19 | The version tests, and an update of the v0.1 test plan. | #92, #93 |
| 11-16 02:58 | Troy accepts v0.1.0 at 02:55; the release PR merges, and troy-mode creates the GitHub release. | [#94](https://github.com/ZJUCao/recipe-menu/pull/94) |
| 11-16 03:10 | The retrospective is posted at 03:02, and Troy picks all four proposals. | [#94](https://github.com/ZJUCao/recipe-menu/pull/94) |
| 11-16 05:40 | P01 through the rule change flow, with two cleanup PRs. Proposals B, C, and D become troy-pstack issues. | #95 to #97 |

## 3. Problems

Kinds: **blocker** (troy-mode could not go on without Troy), **worked around** (troy-mode, or Troy's yes, got past it), **rule break** (a rule or design was broken and nobody stopped it), **cosmetic**, and **no fault**. Issues are in troy-pstack and carry the `pilot` label where they came from the pilot.

| # | When | What happened | Kind | Feature | Fix or issue |
| --- | --- | --- | --- | --- | --- |
| 1 | 11-10, [#2](https://github.com/ZJUCao/recipe-menu/pull/2) | The Product Manager named the Chinese change-log section 变更记录, not the template's 修改记录, so `approve` added Troy's approval to the English file only. The Product Manager renamed the section and added the row by hand. | Worked around | F01, F07 | [#46](https://github.com/ZJUCao/troy-pstack/issues/46) |
| 2 | 11-10, [#3](https://github.com/ZJUCao/recipe-menu/pull/3) | After Troy's approval, the ADRs' status words still said "Proposed". The Product Manager's own edit was undone by the check after the run, and an extra Architect run changed them. | Worked around | F07 | [#47](https://github.com/ZJUCao/troy-pstack/issues/47) |
| 3 | 11-10, [#3](https://github.com/ZJUCao/recipe-menu/pull/3) | The Architect's `sed -i` on CRLF files changed nothing and turned their line endings to LF; it restored them and used a script. | Cosmetic | F04 | None |
| 4 | 11-10, [#2](https://github.com/ZJUCao/recipe-menu/pull/2) | v0.1 had 13 features, where D94 says 4 or 5: the start request did not state the pilot's size. | No fault | F11 | Troy kept 13 (choice B). |
| 5 | 11-10, [#3](https://github.com/ZJUCao/recipe-menu/pull/3) | The Architect could not try `uv tool install` before the language step, because uv was not installed yet. | Cosmetic | F04 | None |
| 6 | 11-10, [#4](https://github.com/ZJUCao/recipe-menu/pull/4) | The lock compile failed in the app's sandbox: uv could not write its default cache. troy-init restored the files, and the step passed again with `UV_CACHE_DIR` in the session's temporary folder. | Worked around | F06 | [#48](https://github.com/ZJUCao/troy-pstack/issues/48) |
| 7 | 11-11, [#23](https://github.com/ZJUCao/recipe-menu/pull/23) | A Developer run of F01's [#12](https://github.com/ZJUCao/recipe-menu/pull/12) hung in the background for 11.5 hours, then wrote 33 duplicate lines during F03's Test Engineer run. The check blamed the Test Engineer; Troy said "Yes, restore it". On 11-13 a Test Engineer also left a Python process behind. | Worked around with Troy's yes | F07 | [#49](https://github.com/ZJUCao/troy-pstack/issues/49) |
| 8 | 11-11 to 11-13, [#27](https://github.com/ZJUCao/recipe-menu/pull/27), [#40](https://github.com/ZJUCao/recipe-menu/pull/40), [#59](https://github.com/ZJUCao/recipe-menu/pull/59) | Auto mode refused `git commit --amend --no-edit` and `git push --force-with-lease` as "Git Destructive", six times in all. Troy allowed both commands; three refusals of chained commands came after that, and troy-mode ran each command alone. | Blocker, worked around with Troy's yes | F07, F10 | Guide fix [troy-pstack#69](https://github.com/ZJUCao/troy-pstack/pull/69), closing [#50](https://github.com/ZJUCao/troy-pstack/issues/50) |
| 9 | 11-10 to 11-13, [#9](https://github.com/ZJUCao/recipe-menu/pull/9), [#52](https://github.com/ZJUCao/recipe-menu/pull/52), [#59](https://github.com/ZJUCao/recipe-menu/pull/59) | CI's `ruff format --check` also formats the python examples in design documents, which the Interface Designer cannot run: a side PR for F01, two failed CI runs for F08, and a failed attempt for F09. | Worked around, three features | F03, F07 | [#51](https://github.com/ZJUCao/troy-pstack/issues/51) |
| 10 | 11-10 to 11-15 | "Start v0.1" took troy-mode through F01 only, so Troy started each later feature by hand: 12 more requests. | Cosmetic | F07 | [#52](https://github.com/ZJUCao/troy-pstack/issues/52) |
| 11 | Whole pilot | One session held the whole version: 15 compactions, the largest at 883,000 tokens, and 5 stops at the 5-hour usage limit. The main session cost $301, 28% of the total. | Cost | F07 | Section 8 |
| 12 | 11-12, 11-16 | F05's R19 hook refused two PR descriptions with a word that the strict mode refuses, once in a local path; troy-mode rewrote them. | No fault | F05 | None |
| 13 | 11-12, [#47](https://github.com/ZJUCao/recipe-menu/pull/47) | The F07 test plan merged before its CI checks had reported: the watch said "no checks reported", and the merge was chained with `;`. Both runs passed afterwards. The session then used a wait script of its own for every merge. | Rule break | F07 | [#68](https://github.com/ZJUCao/troy-pstack/issues/68) |
| 14 | 11-12 to 11-16 | Python that reads its program from standard input hung: 39 of 168 such runs hit the 120-second limit, from roles and the main session, although every brief warned about it. | Worked around | F04, F05 | [#64](https://github.com/ZJUCao/troy-pstack/issues/64) (retrospective C) |
| 15 | 11-12 to 11-16, seven mock PRs | Mock notes that pointed at nothing or said the opposite of the mock, from [#36](https://github.com/ZJUCao/recipe-menu/pull/36) to [#88](https://github.com/ZJUCao/recipe-menu/pull/88), each costing a review round. | Repeated review finding | F04 | [#63](https://github.com/ZJUCao/troy-pstack/issues/63) (retrospective B) |
| 16 | 11-16, [#92](https://github.com/ZJUCao/recipe-menu/pull/92) | A Test Manager review comment holding a word that R19's strict mode refuses was posted, because the command tested `check-text`'s output with grep rather than its exit code. It was edited at once, but GitHub keeps the old text. | Rule break | F05, F07 | [#65](https://github.com/ZJUCao/troy-pstack/issues/65) (retrospective D) |
| 17 | 11-16 | `hooks.log` keeps only the last day's lines, so the retrospective could not see the version's earlier hook blocks. | Design gap | F05, F08 | [#66](https://github.com/ZJUCao/troy-pstack/issues/66) |
| 18 | 11-10 to 11-16 | Reviewers' notes for later features are dropped when a stage moves on, so the main session kept several dozen of them in its own memory and copied each into a brief by hand. | Worked around | F07 | [#67](https://github.com/ZJUCao/troy-pstack/issues/67) |
| 19 | 11-13, [#52](https://github.com/ZJUCao/recipe-menu/pull/52) | The F08 design failed CI twice in the Interface Designer's file, and no attempt comment was posted, so the retrospective counted 1 failed attempt while CI had failed on four pushes in authors' files, twice on #52 and twice on #59. | Rule break | F07 | [#73](https://github.com/ZJUCao/troy-pstack/issues/73) (candidate T1) |
| 20 | 11-16, [#87](https://github.com/ZJUCao/recipe-menu/pull/87) | CI's checkout step failed with "Repository not found", from GitHub's side; the next push passed. | No fault | None | None |

The roles' own mistakes, which F16's role exam takes its cases from, are problems 1, 2, 3, 7, 9, 13, 14, 15, 16, and 19, and the review findings that requested changes (section 5.5).

## 4. Rule candidates

### 4.1 For the project

The retrospective on [#94](https://github.com/ZJUCao/recipe-menu/pull/94) (F08 D76) read 94 PRs: 56 groups of review findings, 8 of them in two or more PRs, 1 failed attempt, no escalation, and no bug. It proposed four rules, and Troy picked all four ("All four"):

| Proposal | Seen in | What happened |
| --- | --- | --- |
| A. A test support module's doc comment says what the module is for and its limits, and lists no names (R05). | #62, #68, #75, #82 | The project rule P01, through the rule change flow: [#95](https://github.com/ZJUCao/recipe-menu/pull/95) with the Architect's enforcement, then the cleanup PRs [#96](https://github.com/ZJUCao/recipe-menu/pull/96) and [#97](https://github.com/ZJUCao/recipe-menu/pull/97). |
| B. The DV1 brief gives the mock's notes as fixed sentences. | 7 mock PRs | A rule for every project: [troy-pstack#63](https://github.com/ZJUCao/troy-pstack/issues/63) (F09 D83). |
| C. F05's hook refuses Python that reads its program from standard input. | 39 hung runs | [troy-pstack#64](https://github.com/ZJUCao/troy-pstack/issues/64). |
| D. F05's gh guard runs `check-text` before a comment, PR, or issue is posted. | [#92](https://github.com/ZJUCao/recipe-menu/pull/92), once | [troy-pstack#65](https://github.com/ZJUCao/troy-pstack/issues/65). |

### 4.2 For troy-mode

Problems that repeated across features or flows, and that a rule or check for every project would prevent. Those that already have an issue are not proposed again: B, C, and D above, and [#49](https://github.com/ZJUCao/troy-pstack/issues/49) (role runs that outlive their report), [#51](https://github.com/ZJUCao/troy-pstack/issues/51) (code examples in designs), [#52](https://github.com/ZJUCao/troy-pstack/issues/52) (a request that names a version), [#66](https://github.com/ZJUCao/troy-pstack/issues/66) (the hook log), [#67](https://github.com/ZJUCao/troy-pstack/issues/67) (notes for later features), and [#68](https://github.com/ZJUCao/troy-pstack/issues/68) (waiting for CI before a merge). The new candidates:

| ID | Candidate | Evidence | Recommended | Troy's answer |
| --- | --- | --- | --- | --- |
| T1 | `status` and `retro` count attempts from the failed check runs of a PR's pushed commits, not only from the comments troy-mode posts. | Problem 19: two failed CI runs on #52 were never counted, and the retrospective saw 1 failed attempt where CI had failed on four pushes. | Yes | Accepted |
| T2 | Each acceptance PR, and the release PR, gives the role runs and the cost of its feature or version, read from the session's transcripts. | Problem 11: the version cost $1,092 against an estimate of $130 to $235, and nobody saw it until this report. | Yes | Accepted |
| T3 | The Code Reviewer runs `security-review` once per version, on the release PR's whole diff, and on any PR that adds a dependency, a subprocess, or network access, rather than on every code PR. | 71 runs in the pilot, none of which found anything, on a program with no network, subprocess, or secret. | Yes | Accepted |
| T4 | P01 becomes a troy-mode rule for every project. | Four PRs in one project. | No: wait until a second project shows it. | Not accepted |

Troy accepted T1, T2, and T3 on 2026-11-16, and they are now [#73](https://github.com/ZJUCao/troy-pstack/issues/73), [#74](https://github.com/ZJUCao/troy-pstack/issues/74), and [#75](https://github.com/ZJUCao/troy-pstack/issues/75), to be built later through troy-pstack's process. T4 was not accepted.

## 5. Time and cost

### 5.1 Against the estimates

| Measure | F11 design 8.4, 4 or 5 features | Estimate for 13 features, 2026-11-10 | Real, 13 features |
| --- | --- | --- | --- |
| Role runs | 50 to 70 | 160 to 180 | 263, plus 74 helper agents that the Code Reviewer's `code-review` skill started |
| Cost | $50 to $90 | $130 to $235 | $1,092 |
| PRs | About 35 | About 80 | 97: 94 for v0.1 and 3 for P01 |
| CI | A few Actions minutes per PR | | 274 runs, 220 minutes of run time, 48 seconds a run |
| Elapsed | | Several days | 6 days and 6 hours, from 11-09 23:39 to 11-16 05:40 |
| Troy's time | 2 to 3 hours | | 65 messages; Troy gave no estimate of the time |

Per feature, the number of role runs was close to the estimate, 18 against 10 to 18, but each run cost three to four times as much: $4.15 per role run with the main session's share, against $1.00 to $1.30 in the estimate, and the main session cost $13 to $32 per feature. The estimate came from the trials' features, which were far smaller: in the pilot, one feature's design and test plan held 60,000 to 185,000 characters of English (requirements, F14 row).

GitHub's timing API lists no billable time for these runs, so the CI figures are run time.

### 5.2 By role

Every Agent call left the model and effort to the role's definition, and the project set no `[roles]` table, so each role ran on its own model with the session's effort.

| Role | Runs | Model | Cost | Per run |
| --- | --- | --- | --- | --- |
| Product Manager (the main session) | 1 session | opus | $300.97 | |
| Test Manager | 54 | opus | $246.54 | $4.57 |
| Interface Designer | 28 | opus | $139.49 | $4.98 |
| Code Reviewer | 73 | opus | $139.39 | $1.91 |
| Its helper agents | 74 | opus | $94.06 | $1.27 |
| Architect | 33 | opus | $108.61 | $3.29 |
| Test Engineer | 31 | sonnet | $45.70 | $1.47 |
| Developer | 44 | sonnet | $17.89 | $0.41 |
| Total | 263 role runs | | $1,092.66 | |

The desktop app keeps its own running cost for a session. Its last record, at 03:37 on 11-15, said $864.06; the same computation up to that moment gives $848.53, 1.8% less.

### 5.3 By step

| Step | Hours | Role runs | Helpers | Roles' cost | Main session | Total | Review rounds, changes requested |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Setup to the language step | 2.7 | 2 | 0 | $6.28 | $9.15 | $15.43 | |
| v0.1 test plan | 1.5 | 1 | 0 | $5.68 | $1.72 | $7.40 | |
| F01 | 10.2 | 24 | 6 | $32.30 | $12.60 | $44.91 | 3 of 9 |
| F02 | 5.3 | 16 | 4 | $37.48 | $12.83 | $50.31 | 3 of 8 |
| F03 | 13.0 | 14 | 4 | $61.32 | $15.05 | $76.38 | 2 of 7 |
| F04 | 12.8 | 21 | 6 | $69.84 | $20.21 | $90.04 | 4 of 10 |
| F05 | 11.7 | 20 | 5 | $75.54 | $25.88 | $101.41 | 2 of 9 |
| F06 | 3.2 | 17 | 5 | $53.41 | $15.03 | $68.44 | 3 of 8 |
| F07 | 4.2 | 15 | 5 | $47.25 | $17.71 | $64.96 | 2 of 8 |
| F08 | 9.4 | 19 | 5 | $58.89 | $16.25 | $75.13 | 3 of 8 |
| F09 | 5.3 | 19 | 5 | $64.40 | $19.71 | $84.11 | 3 of 9 |
| F10 | 5.8 | 18 | 6 | $50.18 | $16.28 | $66.47 | 4 of 10 |
| F11 | 15.5 | 18 | 5 | $77.88 | $25.32 | $103.20 | 3 of 9 |
| Upgrade to 0.5.0 | 0.1 | 0 | 0 | $0.00 | $5.33 | $5.33 | |
| F12 | 3.1 | 16 | 5 | $44.11 | $24.53 | $68.63 | 3 of 8 |
| F13 | 7.5 | 17 | 5 | $66.91 | $31.79 | $98.69 | 3 of 8 |
| Release | 1.8 | 7 | 2 | $12.77 | $10.16 | $22.93 | 2 of 4 |
| Retrospective and P01 | 2.7 | 19 | 6 | $27.47 | $21.16 | $48.64 | 4 of 10 |

A feature's hours run from its design PR's creation to its acceptance PR's merge, and include the time it waited for Troy. Each step's runs and cost are those between the previous step's last merge and its own; side PRs count with the step they happened in. Roles' cost includes the helpers.

### 5.4 By stage of the feature loop

Summed over F01 to F13, with the side PRs of each stage:

| Stage | Role runs | Roles | Roles' cost |
| --- | --- | --- | --- |
| 1. Design | 40 | Interface Designer 20, Architect 20 | $215 |
| 2. Test plan | 32 | Test Manager 20, Interface Designer 7, Architect 5 | $184 |
| 3. Mock | 50 | Developer 25, Code Reviewer 23, others 2 | $43 |
| 4. Tests | 72 | Test Engineer 24, Test Manager 24, Code Reviewer 24 | $164 |
| 5. Implementation | 39 | Developer 19, Code Reviewer 19, Architect 1 | $42 |
| 6. Acceptance | 1 | Test Manager 1 (TM8) | $1 |

The two document stages took 30% of the role runs and 60% of the roles' cost.

### 5.5 Reviews, attempts, escalations, and waits

- **Reviews.** 127 review comments: the Architect 23 (4 requested changes), the Test Manager 31 (12), and the Code Reviewer 73 (28). 35 PRs needed a second round, and 3 a third ([#29](https://github.com/ZJUCao/recipe-menu/pull/29), [#68](https://github.com/ZJUCao/recipe-menu/pull/68), [#97](https://github.com/ZJUCao/recipe-menu/pull/97)). None reached the escalation after round 3.
- **Attempts.** One comment, Interface Designer attempt 1 on [#59](https://github.com/ZJUCao/recipe-menu/pull/59); two more failures in CI were not recorded (problem 19).
- **Escalations.** None.
- **Waits for Troy.** 34 `Waiting for Troy` comments: 33 approvals and the acceptance of v0.1.0. Troy answered in a median of 27 minutes; 11 waits were under 15 minutes, and 4 overnight waits were over 4 hours. In all, troy-mode waited 48 hours.
- **Troy's messages.** 65: the start and the upgrade request; 4 answers at setup; 14 requests to start a feature, because of problem 10; 26 approvals of designs and test plans; 4 approvals of architecture and requirement changes; 6 other decisions, such as "Keep approving them" and "Allow both commands"; 5 restarts after a usage limit; and 4 at release. Troy wrote in English, and from F09 on started features in Chinese.
- **Hook blocks.** Two, both correct (problem 12). `hooks.log` held only the second when this report was written (problem 17).

## 6. The guide

Troy followed the guide in the pilot. Each place where it was wrong, missing, or unclear, all fixed in [troy-pstack#69](https://github.com/ZJUCao/troy-pstack/pull/69):

| Guide section | What happened | Fix |
| --- | --- | --- |
| 1.1 | It said to set `MAMBA_EXE` "in the environment the app starts in", but not how; `MAMBA_ROOT_PREFIX` was not needed. | A user variable, set with one PowerShell line, then a full quit of the app; `MAMBA_ROOT_PREFIX` is optional. |
| 1.2 | The `/plugin` commands are not offered in the desktop app's Code tab, and the CLI is not on PowerShell's PATH. There was no way to see the installed version. | Install with the bundled CLI, found with one PowerShell line; `plugin list` shows the version. |
| 1.3 | On 11-15 the update found no new version: the marketplace is the main checkout, which was five commits behind. | Pull the main checkout, update the marketplace, then the plugin; restart at a natural stop. |
| 1.4 | It gave only the merge permission (problem 8). | All three allow entries, and what happens with chained commands. |
| 2.1 | Troy typed the first request in the F11 session instead of a session in the pilot's folder, and the guide did not say to avoid a worktree. | A new session in the project's folder itself, for every request of the project. |
| 3.1 | It was right that "the rest of v0.1" builds the version, but "Start v0.1" built one feature (problem 10), and nothing said what a feature takes. | A note on "Start v0.1", and each feature's hours, role runs, and cost from this report. |
| 5.8, 8.6 | It did not say that the hook log keeps one day (problem 17). | Said in both. |
| 7.5 | It did not say that notes for later features are dropped (problem 18), or what to do after a usage limit or a compaction. | Both said. |
| 8.6 | No rows for problems 6, 7, 14, and 20, and the permission row named only the merge. | Four rows added or extended. |
| 9 | `plugin update` alone, without the pull. | Points to section 1.3. |
| README | It said that nothing had run on a real project, and listed paths that the pilot has now run. | What the pilot ran, and what has still not run. |

Gaps that the F10 build's reader test had named, and that the pilot settled: how to see the installed version, where `MAMBA_EXE` is set, and that the marketplace's checkout must be on an up-to-date `main`. The pilot did not need the others, such as a hand-made `[rules]` PR.

## 7. Statuses

In requirements 7.2. The final status PR (F11 design section 9, item 2) makes these moves after this report and the guide PR merge:

| Feature | Before (requirements 1.38) | After | Why |
| --- | --- | --- | --- |
| F01 to F07 | Used on a real project, "so far" | Used on a real project, with the whole version | Their conditions were met at the first status PR; the text now covers v0.1 to its release. |
| F03, the C/C++ pack | Runs on a sample project | Unchanged | The pilot used only the Python pack. |
| F08 | Runs on a sample project | Used on a real project | troy-mode released v0.1.0: version tests, the release test with a real run, Troy's test on Troy's devices, the GitHub release, and the retrospective. |
| F09 | Runs on a sample project | Used on a real project | P01 went through the rule change flow with a cleanup, and three rules for every project became troy-pstack issues (D99). |
| F10 | Written | Used on a real project | Troy followed the guide, and its fixes merge in troy-pstack#69. |
| F11 | Used on a real project, in progress | Used on a real project | v0.1.0 accepted on Troy's devices on 2026-11-16, with this report. |
| F12, F13, F14 | Runs on a sample project, or Written | Used on a real project | Not in F11's table, but each design gives its own condition for a real project, and the pilot met each one: real runs in #84 and #91, the hook on in every session since #78 (it refused nothing), and summaries Troy approved from #79 on. Troy chose on 2026-11-16 to move them in the same PR. |

## 8. Next

- **Open issues from the pilot.** [#46](https://github.com/ZJUCao/troy-pstack/issues/46) to [#49](https://github.com/ZJUCao/troy-pstack/issues/49), [#51](https://github.com/ZJUCao/troy-pstack/issues/51), [#52](https://github.com/ZJUCao/troy-pstack/issues/52), and [#63](https://github.com/ZJUCao/troy-pstack/issues/63) to [#68](https://github.com/ZJUCao/troy-pstack/issues/68), and the accepted candidates [#73](https://github.com/ZJUCao/troy-pstack/issues/73) to [#75](https://github.com/ZJUCao/troy-pstack/issues/75).
- **Cost.** The largest parts are the two document stages and the main session's context (problem 11). Worth trying, each measured on a second pilot: a new session per feature, since the state lives in git and on GitHub; the summaries of F14, which may let roles read less; candidate T3; and a lower effort for the reviewers.
- **The planned features.** F15 (issues for Troy), F16 (the role exam, with cases from section 3), F17, F18 (fewer stops: in this pilot troy-mode stopped at every design and test plan, because Troy chose to approve all 16), and F19, the rename, which waits for this report's PRs.
- **A second pilot** should try what this one did not: a project that already has code, such as `nuo_voice`, or HiLog with the C/C++ fix of F11 design section 3.3; a bug fix and an escalation on a real project; a dependency Troy accepts; an approval by merging on GitHub; the answer "No" to the question after the first features, so that troy-mode merges designs itself; a patch release; and changing or retiring a project rule.
- **recipe-menu goes on.** Its v0.2 has F14 to F16. Two more P01 cleanup PRs followed the version: [#98](https://github.com/ZJUCao/recipe-menu/pull/98) merged at 06:14, and [#99](https://github.com/ZJUCao/recipe-menu/pull/99), for the version tests' helpers, was open when this report was written.
