# F17 design: more pstack in troy-mode

| | |
| --- | --- |
| Feature | F17 in [requirements 1.65](../requirements.md#72-feature-list) |
| Version | 1.0 |
| Date | 2026-11-26 |
| Status | Approved by Troy on 2026-11-26 ("全按推荐"), with D161 to D170, every recommended answer, and the requirement text proposals P1 to P5 of section 11 as written. Requirements 1.67 records the decisions with P1 and P2; P3, P4, and P5 land with the PRs that section 11 names. The build's costs, about $213 to $251 for the first rounds and up to about $446, still wait for Troy's own yes, step by step (section 12.4). |
| Source of truth | This English file. [`F17-more-pstack.zh-CN.md`](F17-more-pstack.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F17 adds a pstack skill to troy-mode only where the pilot showed the same mistake twice, and each addition passes the role exam (F16) first (requirements F17 row and 4.1). This design:

1. checks each candidate of the F17 row against the evidence, names each instance, and drops the candidates without two (section 2);
2. picks the additions and where each is wired (section 3);
3. says how a role reads a pstack skill without copying it (section 4), and what the role exam must see of it (section 5);
4. designs each addition: the test-behavior card (section 6), the Architect's design review, which the list does not name (section 7), `reflect` in the retrospective (section 8), and a measurement of `interrogate` before it is added (section 9);
5. says how upstream pstack updates keep merging (section 10), the requirement text F17 needs (section 11), and the build (section 12).

The facts come from the repository at `c5ce288` (plugin 0.18.0, requirements 1.65), the F07, F08, F09, F16, and F18 designs, the F11 pilot report, `ZJUCao/recipe-menu`'s pull requests #1 to #125 and their comments read through `gh`, the role exam's results and case logs in `D:\Troy\troy-mode-work\` (exams 2026-11-17-2, 2026-11-23-1, and 2026-11-25-3), and F18's hand-over notes. The F11 wrap-up's hand-over note was not in the notes folder; the pilot report and F16 design 2.1 carry its list of the roles' mistakes. No probe and no model run was needed: the design spent $0.

## 2. The evidence

A bare `#<n>` is a PR of `ZJUCao/recipe-menu`. v0.1 is #1 to #97; v0.2 is the work since, #98 to #125.

### 2.1 Candidate by candidate

| Candidate | The row puts it in | Instances of the same mistake | Verdict |
| --- | --- | --- | --- |
| `principle-test-behavior-not-implementation` | The Test Manager's instructions | Tests that check less than their case expects: #17, #43, #62, #68, #75, #82, #89 (pilot problem 2), #105 round 1, #117, #119. Tests that check more than their case, which later features broke: #105 (six tests), #115 (one test). Section 2.2. | In (D161, D164) |
| `principle-fix-root-causes` | Bug fixes | None: v0.1 had no bug (pilot report section 1), and #98 to #125 hold no bug PR | Dropped |
| `poteto-mode`'s investigation playbooks | Bug triage | None, as above: TM5 has never run | Dropped |
| `blast-radius` | Code review and requirement changes | None missed (section 2.6) | Dropped |
| `reflect` | The retrospective | The one retrospective so far, on #94, missed or undercounted four lessons that repeated across the version (section 2.4) | In (D161, D166) |
| `interrogate` | Designs that change a data format or several modules | Two designs of v0.2 that change a stored file, approved by the Architect with a gap that the next stage found: F14 (#102, found in #103) and F15 (#113, found in #117 and fixed in #118). In v0.1, F01's design (#6, fixed in #7). Section 2.5. | Measured first (D167) |
| Not on the list: the Architect's design review | | The role exam: the Architect lets a departure from the architecture pass in 13 of the 16 runs of ar-error-review that approve, and never runs `ruff format`, which CI runs on the design file, in 20 of 20 runs of ar-design-review (section 2.3) | Proposal P2 (D165) |

### 2.2 Tests that check too little, or too much

**Too little.** Pilot problem 2 is the Test Engineer's most repeated mistake: a test checks less than its plan case expects, such as the exit code only (#17, #43, #62, #68, #75, #82, #89). F16's cases te-plan-asserts and tm-test-review come from it. It went on in v0.2:

- #105, round 1: both reviewers found that F13-T22 and F13-T27 no longer checked that the error stream is empty, and F13-T27 checked "only exit code 0".
- #117, the Code Reviewer's round 1: F15-T16 lines 3 and 4 "check only the last line or only the exit code, as the rows of the plan ask".
- #119: "No test saw that": the wrappers of F15-T03 and F15-T04 used a `newline` that is already universal, so an implementation without the design's fix passed on every system.

The plan rows asked for too little too: on #75 the Code Reviewer wrote that "each case's own row asks only for what it checks".

**Too much.** Two tests of accepted features were tied to more than their case's contract, and later features broke them:

- #105: F14's mock adds a command and a settings key, which changes the help and the text of `UNKNOWN_KEY`, so six tests of F05, F11, and F13 failed (F05-T10, F05-T11, F11-T32, F13-T01, F13-T22, F13-T27). F13-T01 expected the whole 21-line help of the F05 prototype, not the line of `shop`.
- #115: F11-T01 took "the two lines right after the line of `search`" as the lines of `menu new` and `menu show`, so F15's `add` broke it.

Both were found at the later feature's design (#102, the Architect's finding 5: "The six tests break again when F15 and F16 add `add`, `edit`, and `editor`"; #113), and each cost a test-fix PR with two reviews. Both rulings changed the Test Manager's plan rows, so the cause sits in the plan (TM1) as well as in the tests (TE1).

**The fit.** The card's two imagined edits name both: "Break the behavior" catches a test that passes when the case's result breaks ("an assertion looser than the contract"), and "Change the internals" catches a test tied to something its users cannot rely on. Its rule is "Assert what the contract promises, no less and no more." troy-mode's own text says only "Test behavior through external interfaces only" (TE1 step 3, TM2 step 3), which does not say how much a test checks.

### 2.3 The Architect's design review

The two Architect cases ran 40 times in exams 2026-11-23-1 and 2026-11-25-3, on `main`'s instructions or one change from them:

| Case | Passed | What the other runs did |
| --- | --- | --- |
| ar-error-review | 3 of 20 | 16 of 20 approved the design. 13 of those 16 reports name the full path of the failed listing, or ADR-0009, and let it pass as a note, for example "I read this case as covered by ADR-0009" (exam 2026-11-25-3, head run 1). |
| ar-design-review | 0 of 20 | Every run asked for changes. K4, the example lines that `ruff format` rewraps, was missed in 20 of 20: no report ran `ruff format`, and one says "I did not run Linux, ruff, mypy, or troy-check. The PR has no code." K2, the full path that departs from architecture 6, was found in 3 of 20, and a fourth report named it as not blocking. |

So the Architect makes two mistakes: it sees a departure from the architecture's words and reads the rule wide enough to let it pass, and it checks a design's examples by running them but does not run the checks that CI runs on the design file. In ar-error-review, 13 of 20 reports did run `ruff format`.

The pilot's Architect found both faults in round 1: the cases' keys are its own findings on #52 and #71. So the exam shows these mistakes on today's instructions, models, and CLI, not in the pilot. They are still the same mistake in two cases and two exams, and F18's spot checks wait on them (F18 design D178, E3).

No pstack skill tells a reviewer to read a rule as written. `principle-prove-it-works` fits the second mistake: verify against the real artifact, not a proxy, and script the check. That second trap is gone from new projects: since tstack issue #51, the Python pack's `ruff` skips `docs/` (F03 design D214). In the cases' project, which is the pilot's state, CI still formats a design's python blocks.

### 2.4 The retrospective

The v0.1 retrospective on #94 read the 94 PRs through `retro`: 56 groups of review findings, 8 of them repeated, and proposals A to D. Four lessons that repeated across the version were missing or undercounted:

| Lesson | What the retrospective said | What the records held | Found by |
| --- | --- | --- | --- |
| Tests that check less than their case | Nothing: the findings fell into groups such as "R09 (#52, #75)" and "test plan details (#89, #92)" | 7 PRs, #17 to #89 | Pilot report problem 2, F16 design 2.1 |
| Python that reads its program from standard input | "5 times while F11 to F13 were built" | 39 of 168 such runs hung | Pilot report problem 14 |
| Waits for Troy and stops | Nothing | 34 `Waiting for Troy` comments, 48 hours; 63 stops, 100.4 hours | Pilot report 5.5, F18 design 2.1 |
| CI failures in an author's files | "1 failed attempt" | CI failed on four pushes in the authors' files | Pilot report problem 19, now `ci_attempts` |

The cause is where `retro` looks. It reads PR comments and groups findings by the rule ID or checklist item each names, and problem 2's findings name plan case IDs, not a rule. Hangs, waits, refusals, and usage limits are only in the sessions' transcripts, which are large: 548 MB for recipe-menu so far, in 3 main-session transcripts and 425 subagent transcripts. The pilot report and F18's evidence work read those; the retrospective did not.

### 2.5 Designs that change a stored file

- **F14**, a week menu's file (#102, approved by the Architect in round 2). Its test plan #103 says: "Two rare file layouts have no test, because the design does not say what happens: a day's header as the last line of the file with no line break after it, and spaces around a key of `dishes`."
- **F15**, a recipe file written from typed answers (#113, approved in round 1 after the Architect probed piped input on Windows). Both reviewers of the tests (#117) found that design 3.3's line ends "stay universal" only on Windows, which #118 fixed in the design and #119 in the tests.
- **F01** in v0.1 (#6): no limit on an amount's digits, while Python refuses more than 4,300; the Test Manager found it while planning, and #7 fixed the design.

Each was found by the next stage, before code. The evidence for `interrogate` is weak in one way: the Architect of #113 already built a model and probed the input, much as an adversary would, and missed the fault because it lies on another system.

### 2.6 What was not found

- **Bugs.** No bug was reported, triaged, or fixed in either version, so the bug-flow candidates have no instance.
- **Breakage elsewhere.** Knock-on effects were found where they belong: at the later design (#102's finding 5, #113), and in the Architect's change impact lists (AR4) on #34, #104, #108, and #125, which no later PR corrected. No code PR broke another feature after its merge, and the v0.1 release's real run matched all 48 prototype commands.
- **F18's trials.** One Test Engineer, in a premise attempt, worked around a cause in the environment instead of reporting it, which F18's premise text now covers; one Product Manager slip put new features before accepted ones. Each happened once, in a scratch trial.
- **Seen twice, but not a skill's job.** Two roles' scripted edits changed a document's bytes: the Architect's `sed -i` turned CRLF into LF (#3, pilot problem 3), and an octal escape left U+0082 in the architecture (#104, fixed in #108). A check fits better than a skill (`principle-encode-lessons-in-structure`): section 15 leaves it as an idea for a tstack issue.

## 3. Which additions go in (D161)

| Addition | Role and tasks | Wired in | The exam | PR |
| --- | --- | --- | --- | --- |
| `principle-test-behavior-not-implementation` | Test Engineer TE1, TE3, TE4; Test Manager TM2 | The card table, in the brief's Read first (section 4) | Target te-plan-asserts; tm-test-review must not get worse | 3 |
| The same card, later | Test Manager TM1 and TM7 | The card table | A new case of tests tied to too much, built first (section 6.3) | Not in this build |
| The Architect's review: one sentence of troy-mode's own in AR2, and `principle-prove-it-works` | Architect AR2 | The agent file, and the card table | ar-error-review, then ar-design-review, by a hillclimb (section 7) | 2 |
| `reflect` | The main session, at the retrospective | The entry skill's section "Retrospective", `product-manager.md`, and `retro --digest` (section 8) | No case: the exam has none for the main session (F16 D151); a replay of v0.1's records instead | 4 |
| `interrogate` | The main session, before AR2's round 1 of a design that changes a stored file | Not yet: a replay first (section 9) | | Probe |

PR 1 builds what every card needs: the card table and the exam's view of it (sections 4 and 5). Section 12 gives the order, the plugin versions, and the costs.

## 4. How a role reads a pstack skill (D162)

### 4.1 The card table

A new engine module, `troyflow/cards.py`, holds one row per task and card: the task ID, the card's folder under `skills/`, and one fixed line. For a brief of a listed task, `brief` adds the card's absolute path in the plugin to Read first, as it adds the premise card since F18 (`premise.py`), and adds the line to the Task field after the task's own text, starting "Apply `<card>`:".

- **The card is read, never copied.** The role reads the `SKILL.md` that tstack ships, which is upstream's text; troy-mode never copies or changes it. Common rule 9 already says how a role reads a pstack skill: read its `SKILL.md` and follow it, since the Skill tool refuses them.
- **The line is troy-mode's.** It says where the card applies in this task, and which troy-mode rule wins where the two differ (requirements 4.1). For example, the test-behavior card says that an exact error message "pins wording that no caller reads", while in troy-mode the texts of the design and the prototypes are Troy's and a test checks them exactly. So the line for the Test Engineer says: "In troy-mode, the design's and the prototypes' texts are the contract: check your case's own texts exactly, and nothing that another feature adds or owns."
- **Only the listed tasks change.** Every other brief renders as before, so only the cases of those tasks are affected (section 5).
- **A missing card is refused.** When a row's `SKILL.md` is missing from the plugin, `brief` refuses with the problem `card`, and a tstack test checks every row.

### 4.2 Why not the agent file

troy-mode names skills in agent files today: `technical-writing` in common rule 7, and `benchmark-checklist` in TM1 step 3. A card named there would work the same for the role. But the agent file is input to every case of the role, so any change to it runs all of them: one sentence for TM2 in the Test Manager's file would run tm-plan-expected, whose runs cost $8.22 to $14.38 each in exam 2026-11-17-2, about $125 for one first round. The card table keeps an addition's exam to the cases of the tasks it serves.

## 5. What the role exam sees (D163)

Two gaps in today's exam would let a card escape the gate:

1. **The premise card is outside the instruction set.** `named_skills` reads only the agent files and `common.md`. `premise.py` names `skills/principle-attack-the-premise/` from the brief, so a change to that folder changes no instruction hash, and no exam runs. A card named only by the card table would have the same gap.
2. **A skill's change affects every case.** `affected` compares, for every case, the files of every named skill, so a change to `benchmark-checklist`, which only the Test Manager reads, affects all twelve cases.

PR 1 changes both, in `troy-mode/exam/troyexam/`:

- `named_skills` also reads the brief's modules (`brief_modules`), so every `skills/<name>/` that they name joins the instruction set: the premise card now, and each card of the card table.
- `affected` compares, for each case, only the skill folders that its role's agent file, `common.md`, or its own rendered brief names.
- `check_exam.py` reads the set from the same code, so CI follows.

This is a change to the exam's harness, so `prove --anchors` proves every case's anchors again: $40.00 by the exam's estimate, against $11.46 for the same proof in exam 2026-11-21-1. It changes `main`'s instruction hash, so no later exam reuses a base run from before it. That costs nothing extra in this plan, since every later step measures its base fresh.

## 6. The test-behavior card (D164)

### 6.1 Where

| Task | When | Line after the task's text |
| --- | --- | --- |
| TE1 Tests | PR 4 | Apply `principle-test-behavior-not-implementation` to each test you write, with its plan case's expected result as the contract. In troy-mode, the design's and the prototypes' texts are the contract: check your case's own texts exactly, and nothing that another feature adds or owns. |
| TE3 Test fix | A ruling of the Test Manager | The same, for each test the ruling changes. |
| TE4 Added cases | Cases added to the plan | The same as TE1. |
| TM2 Test review | PR 4, a test fix, bug PR A, a cleanup, version tests | Apply `principle-test-behavior-not-implementation` to each test of the diff: a test that still passes when its case's expected result breaks, or that checks a text, a line, or an order its case does not expect, is a finding. In troy-mode, the design's and the prototypes' texts are the contract. |

TE1, TE3, and TE4 wrote the tests of section 2.2 (#105 by TE3, #119 by TE4). TE2, TE5, and TE6 get no row: no reproduction test has been written yet, and no instance comes from the version tests or a rule's cleanup.

### 6.2 The exam

`affected` finds te-plan-asserts (TE1) and tm-test-review (TM2). The PR names te-plan-asserts as its target, and tm-test-review must not get worse. No case covers TE3 or TE4.

- **Is the trap live?** te-plan-asserts' base passed 4 of 5 in exam 2026-11-17-2, at an older hash; the case logs hold no run since. The target rule then needs the head at 5 of 5, or at least 8 of 10 and more than the base after a second round (F16 design 7.2). If the base passes 5 of 5 on `main`, the trap is not live, no target can be named, and PR 3 stops: a case from v0.2's instances, such as #119's tests that cannot tell the two implementations apart, is built first in its own PR, with its own cost for Troy.
- **What it costs.** The case logs hold no runs of either case, so `troy_exam.py`'s estimate uses the pilot's role medians, $0.39 and $2.21: $30.00 for the first round, $60.00 with second rounds. The base runs of exam 2026-11-17-2 cost much more: medians of $4.42 for te-plan-asserts, whose runs take 20 to 22 minutes, and $2.41 for tm-test-review. At those medians the first round is $72.30, and the whole $144.60. The exam's guard would pause it for Troy at 1.5 times its own estimate, so the build asks Troy's yes for up to $144.60 before it starts, and that yes covers the pause.

### 6.3 TM1 and TM7, later

Tests tied to too much came from plan rows (both rulings of section 2.2 changed them), so the card belongs in TM1 and TM7 too. It waits, for three reasons:

- tm-plan-expected's trap is not live (5 of 5 in exam 2026-11-17-2, F16 design 14.6), so it can only guard.
- No case holds the too-much mistake. One would start from the F11 test plan's base (#73) and pass when the plan's help case still holds after a command is added next to `search`, as F15's `add` was (#115).
- Its cost: about $65 to prove the new case (five runs at about $12.35 and the judge passes), and about $251 for the first round of the exam with tm-plan-expected.

So it comes after PR 3 shows whether the card moves te-plan-asserts, as a PR of its own with Troy's yes to its cost (D170).

## 7. The Architect's design review (D165)

### 7.1 Why F17 holds it

F18 design 7.3 needs both Architect cases at 4 of 5 before spot checks are recommended, and its step 2 is a hillclimb of AR2 whose cost was unknown. The evidence of section 2.3 shows that the hillclimb needs two changes, and only one is a pstack card. Holding both in F17 lets one design and one series of exams serve F17 and F18. The sentence of H1 is troy-mode's own text, not a pstack skill, so this widens the F17 row: proposal P2.

### 7.2 The hillclimb

F16 design 8.3, with the two cases as the frozen harness and the decision log `climb/ar-review/decision.tsv` in the work root:

| Attempt | Hypothesis | Change | Measured as | Kept when |
| --- | --- | --- | --- | --- |
| H1 | The Architect reads an exception wider than written and keeps a departure as a note, because nothing says that a departure blocks whatever its merit. | AR2 step 2 gains: "A design that departs from the words of the architecture or of an ADR fails the item it breaks, also when you judge the departure right or read the ADR as covering it. Ask the design to name the rule, and to put the change to Troy as a point (requirements 5.7). Read each exception as written." | `run --base origin/main --head <H1>` | ar-error-review passes the target rule, and ar-design-review is not worse |
| H2 | The Architect checks a design's examples by running them, not by running the checks that CI runs on the design file. | A card table row gives AR2 `principle-prove-it-works`, with the line: "Apply it to the design file: run each check that the project's CI runs on it, with the project's settings, such as `ruff format --check` on its python blocks when CI formats them, and give each command and its output in Checks." | `run --base origin/main --head <H1+H2>`, the base runs reused | ar-design-review passes the target rule, and ar-error-review is not worse |

H1 goes first: ar-error-review can pass on H1 alone, while ar-design-review needs both (K2 and K4). An attempt that misses its rule is reverted in full and logged, and the PR holds the kept attempts. When H2 is kept, its measurement against `main` is the PR's own exam (F16 design 8.3, step 4).

### 7.3 K4 and new projects

K4's trap is gone from new projects (section 2.3), so H2's worth outside the case is the habit of running every check CI runs on the design file, such as troy-check's text and pair checks. Making K4 a note first, as case version 2, would let H1 alone lift ar-design-review, but it would drop a fault that is real in the case's project. This design keeps K4 as it is.

### 7.4 What it costs

From `troy_exam.py`'s budget code with each case's recorded median, $2.79 for ar-design-review and $2.95 for ar-error-review, over the 20 runs each that the case logs hold:

| Measurement | First round | With second rounds |
| --- | --- | --- |
| H1 against `main`, base fresh | $61.37 | $122.74 |
| H1 and H2 against `main`, base reused | $32.68 | $94.05 |
| In all | $94.05 | $216.79 |

`main`'s hash is still `02dec4115317` after F18 part 2, which leaves the instruction set alone, and exam 2026-11-25-3's head runs are on it. They could serve as the base until 2026-12-09, but PR 1 changes the hash first, so this plan does not count on them.

## 8. `reflect` in the retrospective (D166)

### 8.1 Today

The skill's section "Retrospective" (F08 D76): `retro --tag <tag>` groups the evidence of the version's PRs, the main session follows `correct` on each repeated problem, sends Troy one message with the proposals (W5), and posts the report on the release PR. The rule change flow (F09) takes each rule Troy picks.

### 8.2 With `reflect`

1. **A digest of the sessions.** `retro --tag <tag> --digest` also writes a digest of the version's sessions, from the transcripts that `costs --tag` already finds (F07 D264): one line per role run with its role, task, item, result, minutes, cost, and failed checks; each tool call that a hook or a permission refused, with its reason; each command that hung or hit its time limit; each `Waiting for Troy` with its wait; each usage-limit stop and compaction; each of Troy's messages cut to 200 characters; and the first line of each review finding with its PR. It holds at most 200,000 characters; past that, the oldest runs' lines give way to counts. It stays on Troy's PC, in the common git folder (`troy-mode/retro/<tag>.md`), and is never posted.
2. **reflect's three lenses.** The main session follows `reflect`'s steps 2 to 4: the judgment, tooling, and divergent reviewers, each a read-only subagent given `reflect`'s own prompt template unchanged, with the digest in place of the transcript path, as the templates allow ("or use the digest below"), and `retro`'s groups; then the synthesizer. The models come from `reflect`'s lines of the model rule, mapped by tstack's adapter. The reviewers may read files and run read-only `gh`; they change nothing.
3. **troy-mode's routing.** `reflect`'s step 5 edits skills once the user approves. In a troy-mode project nothing edits a skill or a role's file, so troy-mode's rule wins (requirements 4.1):

| `reflect`'s output | In the retrospective |
| --- | --- |
| Accepted, about the project's code, tests, or documents | A proposal for a project rule, through the rule change flow (F09) |
| Accepted, about a troy-mode role, the engine, or a tstack skill | A proposal for a rule for every project: a tstack issue (F09 D83) |
| Backlog: a check would enforce it | The proposal's level is a check (F09 D79), as `reflect`'s step 4 and requirements 5.8 both prefer |
| Rejected | One line each under "Dropped" |

4. **The rest stays.** `correct`'s method applies to every proposal as today, and the one message to Troy (W5) and the report on the release PR list the proposals from the sessions under their own heading.

The extra cost is the four subagents, about $10 to $20 per retrospective: each reads a digest of about 50,000 tokens, about the size of a design an AR2 run reads at a median of $2.79, and reasons longer. The retrospective already waits for Troy (W5), so it adds no stop.

### 8.3 The check

No exam case covers the main session (F16 D151), so the exam of PR 4 finds no case affected. The check is a replay of v0.1's records, read only: the digest from recipe-menu's transcripts on Troy's PC up to the `v0.1.0` tag, its PRs through `gh`, and `reflect`'s lenses, with the proposals written to a scratch file. Nothing is posted, and nothing is written in `D:\Troy\Projects\recipe-menu`. It passes when the proposals name at least two of the four lessons of section 2.4 that #94 missed. About $15 to $25.

## 9. `interrogate`, measured first (D167)

The evidence (section 2.5) is two designs, and whether `interrogate` would have caught either is unknown. So a replay comes first: `interrogate`'s adversaries on F15's design 1.0 (#113's head before its review) and F14's design 1.0 (#102's round-1 head), in scratch copies built the way the exam builds a case's project, with no write to GitHub. It passes when a verified finding names #118's line-end fault or one of #103's two layouts.

- **Cost.** About $20: the default panel is two adversaries per design, Opus and Sonnet, each about one AR2 run (median $2.79 to $2.95), plus the verification runs.
- **If it passes,** a later PR adds it: the main session runs `interrogate` before AR2's round 1 of a design that changes a stored file or a module boundary, and its verified findings go into AR2's Input. That changes what Input AR2 gets, so the Architect's cases run then, about $61 for a first round.
- **If it does not,** it is dropped until a later version shows a design fault that the next stage found again (D170).

## 10. Upstream pstack updates (D168)

- **troy-mode changes no pstack file.** The cards, `reflect`, and its prompt templates are read as tstack ships them. troy-mode's words live in the card table's lines and in the entry skill.
- **The pull is gated.** README's "Pull in upstream changes" gains a step after the diff is applied: run `troy_exam.py affected --base origin/main`. When a card or another skill a role reads changed, the merge PR carries the exam of the cases it affects, as any PR that changes the instruction set does (F16 design 9.4). With section 5's per-case folders, a change to the test-behavior card runs only te-plan-asserts and tm-test-review.
- **A card renamed or deleted upstream** fails the card table's test in CI, so the merge PR shows it before any project does, and `brief` refuses a missing card.
- **`reflect`'s templates** shape only the retrospective, which no exam case covers. After an upstream change to them, the replay of section 8.3 can run again if Troy wants.

## 11. Requirement text F17 needs (proposals)

Troy approved all five on 2026-11-26 ("全按推荐"), as written. P1 and P2 land in requirements 1.67, which records F17's decisions; P3, P4, and P5 land with the PRs that the "When" column names.

| # | Where | Proposed text | When |
| --- | --- | --- | --- |
| P1 | The F17 row | Its description gains the decisions as approved, as the F18 row did after its design: the test-behavior card for the Test Engineer and the Test Manager's test review, `reflect` in the retrospective from a digest of the sessions, `interrogate` after a replay, the card table, and the exam's view of it (D161 to D170). | Requirements 1.67 |
| P2 | The F17 row | Add: "Where the evidence shows a role's repeated mistake that no pstack skill fits, F17 changes the role's own instruction by the same hillclimb, measured by the role exam: first the Architect's design review, which F18's spot checks need (F17 design D165)." | Requirements 1.67 |
| P3 | 4.1, the table | A row for `principle-test-behavior-not-implementation`, used for "The Test Engineer's tests and the Test Manager's test review: a test checks what its case promises, no less and no more (F17)". The row of `principle-prove-it-works` adds "and the Architect's design review, which runs the checks CI runs on a design (F17)". The row of `reflect` becomes "Reviewing a version's sessions at the retrospective, from a digest of their transcripts, for lessons that become rules or tstack issues (F17 design D166)". | Each row with the PR that wires it: 3, 2, and 4 |
| P4 | 4.1, the paragraph after the table | Replace its second sentence with: "A role reads such a skill from its brief, which names tstack's copy of upstream's file; troy-mode never changes the file, and an upstream update that changes a file a role reads runs the role exam on the cases that read it (F17 design D162, D168)." | With PR 1 |
| P5 | 5.5, step 6 | "A retrospective turns problems that repeated during the version into new rules or checks (5.8), from the version's PRs and, with `reflect`, from its sessions (F17 design D166)." | With PR 4 |

No other requirement text changes.

## 12. The build (D169)

### 12.1 The PRs

Each PR has one commit, its tests written first by a separate agent, and planted bugs; the plugin versions assume nothing comes between, after F18 part 2's 0.19.0.

| PR | What | Plugin | Role exam | Other checks | Cost |
| --- | --- | --- | --- | --- | --- |
| 1 | `troyflow/cards.py` with an empty table, `brief`'s rendering of it and the `card` problem, `named_skills` reading the brief's modules, `affected` per case, README's upstream step; P4 | 0.20.0 | No case affected; `prove --anchors` for the harness change | Tests and planted bugs | $11.46 to $40.00 |
| 2 | The Architect: H1 in AR2, H2's card row, by the hillclimb; P2's text in the row, P3's `principle-prove-it-works` row | 0.20.1 | ar-error-review and ar-design-review (section 7.4) | A test that AR2's brief names the card and AR8's does not | $94.05, up to $216.79 |
| 3 | The test-behavior card's four rows; P3's row | 0.20.2 | Target te-plan-asserts, tm-test-review not worse (section 6.2) | Tests that only TE1, TE3, TE4, and TM2 get the card | $72.30, up to $144.60 |
| 4 | `retro --digest`, the skill's "Retrospective" section and `product-manager.md` with `reflect` and its routing, the guide; P3's `reflect` row and P5 | 0.21.0 | No case affected: none of its files is in the instruction set | Tests, planted bugs, and the replay of section 8.3 | About $15 to $25 |
| Probe | `interrogate`'s replay (section 9); no PR unless it passes | | | | About $20 |

In all: about $213 to $251 for the first rounds, the replay, and the probe, and up to about $446 with every second round.

### 12.2 Tests and planted bugs

| PR | The tests cover | Planted bugs include |
| --- | --- | --- |
| 1 | A row renders its card's absolute path and its line only for its task; other briefs unchanged; a missing card refused with `card`; `named_skills` finds the premise card and every row's card; `affected` lists a card's change only for the cases whose brief or agent file names it; the instruction hash covers the card folders | A card added to every task's brief; the path left relative; the line added twice; a missing card accepted; `named_skills` skipping the brief's modules; `affected` comparing every case's skills again; the premise card left out |
| 2 | AR2's brief names `principle-prove-it-works` with its line, and AR8's brief does not; the agent file holds H1's sentence | The card given to AR8 or AR5; the line missing |
| 3 | The card for TE1, TE3, TE4, and TM2 only; TM1's brief unchanged, so tm-plan-expected is not affected | The card in TM1's or TE6's brief; TE3 left out |
| 4 | The digest's lines from the main session's and the roles' transcripts between two tags; another project's transcripts left out; the size limit; the routing table's four rows; no skill edit offered | A role run of a later session left out; another project's transcript read; an Accepted item routed to a skill edit; a Backlog item proposed as a written rule; the digest posted |

The counts go in each PR's description.

### 12.3 Status

| When | F17's status in requirements 7.2 |
| --- | --- |
| The design is approved | Not started, with the row rewritten (P1 and P2, requirements 1.67) |
| PR 1 merges | Written, part 1 of 4: the card table and the exam's view of it are built and checked by tests; no role's brief names a card yet. |
| PR 2 merges | Part 2 of 4: the Architect's design review changed by a hillclimb and checked by the role exam: ar-error-review from <n> of 5 to <m> of 5, ar-design-review from <n> to <m>. Not yet used on a real project. |
| PR 3 merges | Part 3 of 4: the Test Engineer's tests and the Test Manager's test review read the test-behavior card, checked by the role exam: te-plan-asserts from <n> of 5 to <m> of 5. Not yet used on a real project. |
| PR 4 merges | Ran on the pilot's records: the retrospective reads the version's sessions with `reflect`, and its replay of recipe-menu v0.1 found <which> of the four lessons #94 missed. Not yet used at a real retrospective. |
| recipe-menu's next version runs on these | Used on a real project, saying which cards a real run read and whether its retrospective used `reflect` |

A PR whose target is not fixed does not merge its card, and the status says so (D170).

### 12.4 Order and waits

- **PR 1 first**, since PRs 2 and 3 need the card table. PR 2 comes before PR 3 because F18's spot checks wait on the Architect's cases.
- **PRs 2 and 3 change the instruction set**, so each waits until no other PR that changes it is open, as every such PR does. Each exam above $60 waits for Troy's yes to its whole (F16 D158): PR 2 at $216.79 and PR 3 at $144.60.
- **PR 4 and the probe** change no file of the instruction set, so they can run beside PRs 2 and 3, each in its own session. Each costs more than $10, so each asks Troy first.
- **The design's approval does not approve these costs**: each step asks Troy with its figures when it is ready.

## 13. Later additions (D170)

F17's build ends with section 12, but the row says "where the pilot shows the need", and the pilot goes on. A candidate dropped here, or a new one, comes back when the evidence shows its mistake twice: in a retrospective, which with `reflect` reads the sessions too, in a second project, or in F16's case runs. troy-mode then proposes it as a rule for every project, a tstack issue (F09 D83), and it lands as its own PR in the way of this design: a live case first, then the card table row, then the exam with the case as its target. A card whose target stays at the base's level is not added (F16 design 13).

The first ones to watch: the first bug through the bug flow, fixed at the symptom (`principle-fix-root-causes`, the investigation playbook in TM5); a merged change that breaks another feature (`blast-radius`); and TM1's half of the test-behavior card (section 6.3).

## 14. Changes to earlier features

| Feature | Change |
| --- | --- |
| F04 Role definitions | `agents/troy-architect.md`: H1's sentence in AR2, if kept (PR 2). No other agent file changes: the cards come through the brief. `product-manager.md`: the retrospective's use of `reflect` (PR 4). |
| F07 Entry skill | `troyflow/cards.py` and `brief`'s Read first (PR 1); the section "Retrospective" (PR 4). |
| F08 Release | `retro --digest`, and D76's retrospective with `reflect`'s lenses and routing (PR 4). |
| F09 Rule change | Takes the retrospective's new proposals as it takes today's; no change to the flow. |
| F10 Docs | The guide's retrospective section says what the digest holds and that it stays on Troy's PC (PR 4). |
| F16 Role exam | 9.1: the skills that roles read include those the brief names; 9.2: per-case skill folders (PR 1). The Architect's hillclimb log (PR 2). |
| F18 Fewer stops | Section 7.3's step 2, the Architect's hillclimb, is F17's PR 2. |
| tstack's README | "Pull in upstream changes" gains the exam step (PR 1). |

## 15. Not in F17

- TM1's and TM7's half of the test-behavior card, until PR 3's result and its own case (section 6.3).
- The investigation playbook in bug triage, `principle-fix-root-causes`, and `blast-radius`, until the evidence shows them twice (section 13).
- Adding `interrogate`, until its replay passes (section 9).
- A check that refuses C1 control characters and changed line ends in documents (section 2.6): an idea for a tstack issue, since it is a check and not a skill.
- The Interface Designer's and the Test Manager's base runs that F18 design 7.3 step 1 asks for: F17 runs only the cases its PRs affect.
- Changes to tstack's own process.

## 16. How F17 maps to the requirements

| Requirement | Where F17 covers it |
| --- | --- |
| F17 row: where the pilot showed the same mistake twice | Section 2 |
| F17 row: principle cards in the role instructions | Sections 4, 6, and 7 |
| F17 row: `blast-radius`, the investigation playbooks, `principle-fix-root-causes` | Sections 2.1 and 2.6: dropped |
| F17 row and 4.1: `reflect` in the retrospective | Section 8 |
| F17 row: `interrogate` | Section 9 |
| F17 row: each addition passes the role exam first | Sections 5, 6.2, 7.4, and 12 |
| 4.1: troy-mode borrows from pstack and never changes it | Sections 4.1 and 10 |
| 4.1: troy-mode's rule wins in a conflict | Sections 4.1 and 8.2 |

## 17. Decisions for Troy

F16 design keeps D161 to D170 for F17. Troy approved every decision on 2026-11-26 with the recommendation ("全按推荐"), and the requirement text proposals P1 to P5 with them. The standing yes for small issues did not cover them, since F17 is a new feature. The build's costs are not approved with them: each step asks Troy (section 12.4).

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D161 | Which candidates go in? | A: by the evidence of section 2: the test-behavior card (TE1, TE3, TE4, TM2 now), the Architect's review (D165), and `reflect` go in; `interrogate` is measured first (D167); `blast-radius`, `principle-fix-root-causes`, and the investigation playbooks are dropped, since neither version has an instance. B: only the two with instances in the pilot's own PRs, the card and `reflect`. C: every candidate of the row. | A, approved by Troy on 2026-11-26 ("全按推荐"). Each addition has at least two instances, linked in section 2, and each dropped one has none: no bug was reported in either version, and every knock-on effect was found at the later design or in AR4's lists. B leaves the Architect's review, which F18 needs, to another design. C adds skills that no case can measure, against F16 design 13. |
| D162 | How does a role read a pstack skill without copying it? | A: a card table in the engine (`troyflow/cards.py`): for a listed task, the brief's Read first gets the card's absolute path in the plugin, and the Task field one fixed line of troy-mode's that says where the card applies and which troy-mode rule wins; a missing card is refused (section 4). B: a sentence in the agent file's task step, as `benchmark-checklist` in TM1. C: copy the card's text into the agent file or `common.md`. | A, approved by Troy on 2026-11-26 ("全按推荐"). The role reads upstream's file as is, and only the tasks the card serves change, so only their cases run: one sentence in the Test Manager's agent file would run tm-plan-expected, about $125 a first round. B works the same for the role but costs every case of the role on every change. C breaks "never changes them", stops upstream updates, and C in `common.md` runs all twelve cases, about $263. |
| D163 | What must the role exam see of a card? | A: `named_skills` also reads the brief's modules, so the cards and the premise card join the instruction set; `affected` compares, per case, only the skills its role's agent file, `common.md`, or its own brief names; one `prove --anchors`, $11.46 to $40.00 (section 5). B: only the first part, so every card change runs all twelve cases. C: no change. | A, approved by Troy on 2026-11-26 ("全按推荐"). Without it, a card changed upstream or by hand escapes the gate, as the premise card does today. Per-case folders keep a card's update to its own cases. B makes every upstream card update cost about $263. |
| D164 | Where does the test-behavior card go, and how is it measured? | A: TE1, TE3, TE4, and TM2 now, with te-plan-asserts as the target and tm-test-review not worse, $72.30 up to $144.60; TM1 and TM7 later, with a new case of tests tied to too much (section 6). B: every Test Engineer and Test Manager task at once, with tm-plan-expected and te-helper-docs in play, about $129 more for the first round and up to about $258 more in all. C: the Test Engineer only. | A, approved by Troy on 2026-11-26 ("全按推荐"). The tests of section 2.2 were written by TE1, TE3, and TE4 and caught by TM2. TM1's half has no live case, and its runs cost $8 to $14 each, so it waits for PR 3's result. C leaves TM2, which caught the mistakes and can catch more, without the card. If te-plan-asserts is not live on `main`, PR 3 stops and asks for a new case first. |
| D165 | Does F17 hold the Architect's hillclimb? | A: yes: H1, a sentence of troy-mode's own in AR2 (a departure blocks and goes to Troy, whatever its merit), then H2, `principle-prove-it-works` in AR2's card row (run the checks CI runs on the design file), each kept only by the exam's rules; requirement proposal P2; $94.05 up to $216.79 (section 7). B: no: the hillclimb is its own tstack issue under F18 design 7.3, with this design's evidence and hypotheses handed over. C: only H2, the card, in F17. | A, approved by Troy on 2026-11-26 ("全按推荐"). The evidence shows two mistakes and only one card; ar-design-review needs both fixed and ar-error-review needs H1, so the hillclimb needs both. One series of exams then serves F17 and F18's spot checks, and the cost is the same under A and B. B adds a design round and a wait for Troy before F18's E3 can move. C cannot move either case, since H2 alone leaves K2 and K1 failing. |
| D166 | How does `reflect` join the retrospective? | A: `retro --digest` writes a digest of the version's sessions on Troy's PC; the main session runs `reflect`'s three lenses and its synthesizer as read-only subagents with its templates unchanged; troy-mode routes each accepted item to a project rule or a tstack issue, never a skill edit; checked by a replay of v0.1's records, about $15 to $25 (section 8). B: follow `reflect`'s `SKILL.md` whole, edits included. C: the main session reads the digest itself with the lenses' questions, with no subagents. | A, approved by Troy on 2026-11-26 ("全按推荐"). The lessons #94 missed lived in the transcripts, which a digest brings within reach, and `reflect`'s lenses are the part troy-mode lacks. B would edit skills inside a project, against requirements 4.1 and F09. C costs less but loses the independent lenses, and the main session's context already cost $301 in the pilot. |
| D167 | What happens with `interrogate`? | A: a replay on F15's and F14's designs first, about $20 with Troy's yes; it is added for designs that change a stored file only if a verified finding names #118's or #103's gap (section 9). B: add it now for such designs. C: drop it. | A, approved by Troy on 2026-11-26 ("全按推荐"). Two instances meet the bar, but the Architect of #113 already probed the input and missed a fault on another system, so whether `interrogate` helps is unknown. A measures it for about $20 before it costs every such design about $10 and the Architect's cases about $61. |
| D168 | How do upstream pstack updates keep merging? | A: troy-mode changes no pstack file; README's upstream pull runs `affected` and the exam of the cases a changed card affects; a renamed or deleted card fails the card table's test and `brief` (section 10). B: keep a pinned copy of each card under `troy-mode/`. C: no check. | A, approved by Troy on 2026-11-26 ("全按推荐"). Upstream's text merges as it does today, and the exam decides whether an upstream change to a card a role reads is safe. B copies, against requirements 4.1, and hides upstream fixes. C lets an upstream change reach roles with no exam. |
| D169 | How does F17 land and get checked? | A: four PRs and a probe in the order of section 12: the card table and the exam's view (0.20.0), the Architect (0.20.1), the test-behavior card (0.20.2), and `reflect` (0.21.0); tests by a separate agent and planted bugs for each; no trial on `ZJUCao/troy-mode-trial`, since the exam checks the roles, the tests the engine, and the replay the retrospective; about $213 to $251, up to about $446, each step with Troy's yes. B: one PR. C: one PR per card and one for the engine, with a trial of each on the trial project. | A, approved by Troy on 2026-11-26 ("全按推荐"). Each PR changes one instruction or one flow, as F16 design 8.1 asks, so each exam stays small, and PR 4 and the probe can run beside the instruction-set PRs. B would run every affected case in one exam and stack untested changes. C adds trials that measure nothing the exam and the replay do not. |
| D170 | How do later additions come? | A: a dropped or new candidate comes back when a retrospective, a second project, or the exam shows its mistake twice; troy-mode proposes it as a tstack issue, and it lands as its own PR with a live case first and the case as its exam's target (section 13). B: F17 ends with this build; later additions are new features. C: add the dropped candidates now, unmeasured. | A, approved by Troy on 2026-11-26 ("全按推荐"). The row's rule, "where the pilot shows the need", keeps working without a new design each time, and the retrospective with `reflect` is where a second instance shows. B asks Troy for a new feature each time. C breaks F16 design 13. |

## 18. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-26 | First draft, with D161 to D170 and the requirement text proposals P1 to P5, for Troy. |
| 1.0 | 2026-11-26 | Approved by Troy with D161 to D170, every recommended answer ("全按推荐"), and the requirement text proposals P1 to P5 as written. Requirements 1.67 records them with P1 and P2. The build's costs still wait for Troy's yes, step by step (sections 12.4 and 17). |
