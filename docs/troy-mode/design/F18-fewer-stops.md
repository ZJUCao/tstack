# F18 design: fewer stops

| | |
| --- | --- |
| Feature | F18 in [requirements 1.63](../requirements.md#72-feature-list) |
| Version | 1.3 |
| Date | 2026-11-27 |
| Status | Approved by Troy on 2026-11-25 ("全按推荐"), with D171 to D180, every recommended answer, and the requirement text proposals P1 to P7 of section 12 as written. Requirements 1.64 records the decisions with P1, P2, P5, and P7; P3, P4, and P6 land with F18's builds. The build's costs, about $135 and up to about $195, still wait for Troy's own yes. Version 1.1 records what part 1's build chose and its checks (section 13.5), and 1.2 part 2's (section 13.6). Version 1.3 notes in section 7.3 what F17's PR 2 did for step 2. |
| Source of truth | This English file. [`F18-fewer-stops.zh-CN.md`](F18-fewer-stops.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F18 makes troy-mode stop for Troy only where Troy must decide, as the F18 row of requirements 7.2 says. It has three parts:

1. **The waits for Troy.** The Product Manager's instructions list every step that waits for Troy: the approvals of requirements 3.3 and the escalations of 5.7. Every other step goes on and reports in its PR (section 4).
2. **A review loop's third round and an author's third failed attempt.** A review loop that still disagrees after round 3 no longer stops: the Architect rules, or the Product Manager when the loop is the Architect's own review, writes the reason in the PR, and Troy can overturn the ruling later (section 5). An author's third failed attempt (F07 design D64) gets one more attempt that first tests the premise the failed attempts share, and only then escalates (section 6).
3. **Spot checks.** Once real-run acceptance (F12) and the role exam (F16) give enough evidence, Troy can turn the approvals of the first features' design and test plan PRs (3.3 step 3) into spot checks: Claude merges, and Troy reviews a sample and every PR marked as risky. This design proposes the rule that open question Q15 asks for (section 7).

F18 changes how troy-mode behaves inside a project, such as `ZJUCao/recipe-menu`. It does not change how tstack itself is built: tstack's design PRs, Troy's standing yes for small issues, and tstack's own auto-merge stay as they are.

The facts come from the repository at `ecd5041` (plugin 0.17.3, requirements 1.63), the F07, F12, F14, F15, F16, and F20 designs, the F11 pilot report, `ZJUCao/recipe-menu`'s pull requests and comments read through `gh`, its three main-session transcripts on Troy's PC, read only, and the role exam's case logs in `D:\Troy\troy-mode-work\cases\`. No probe and no model run was needed. F18 changes F04, F07, F08, F14, F15, F16, and F20 (section 9).

## 2. What recipe-menu showed

Times are EST. Links to `#<n>` are PRs of `ZJUCao/recipe-menu`. v0.1 is the pilot, PRs #1 to #97, from 2026-11-09 to 2026-11-16. v0.2 is the work since, PRs #98 to #125, with F14 and F15 accepted, F16 at its architecture change, and #125 open.

### 2.1 Where troy-mode stopped

Every message of Troy's in the three main-session transcripts follows a stop: troy-mode's last message before it is where it stopped, and the time until Troy's message is the wait. Troy sent 102 messages. The start request and one retyped request are not stops, which leaves 63 stops in v0.1 and 37 since. One more is open: #125, which Troy approved on 2026-11-21, cannot merge because GitHub has refused to run its CI for billing since 2026-11-22 00:59.

| Kind of stop | v0.1: stops | v0.1: hours | Since: stops | Since: hours | Listed in 3.3 or 5.7 |
| --- | --- | --- | --- | --- | --- |
| Approval of the requirements or the architecture, or of a change of them | 7 | 12.1 | 2 | 6.4 | Yes |
| Approval of a design or test plan PR | 28 | 43.4 | 6 | 15.2 | Yes |
| The version's acceptance and the retrospective's rules | 3 | 1.2 | 0 | 0 | The acceptance only |
| A review loop at round 3 | 0 | 0 | 0 | 0 | Yes |
| An author's failed attempts | 0 | 0 | 0 | 0 | Yes |
| Any other escalation | 0 | 0 | 0 | 0 | Yes |
| A command that auto mode refused | 1 | 0.2 | 0 | 0 | No |
| A question that no instruction asks for | 3 | 10.3 | 2 | 14.6 | No |
| The request's reach ended while work of the version remained | 15 | 27.9 | 19 | 40.0 | No |
| A usage limit | 5 | 5.2 | 6 | 41.5 | No |
| Other: creating the GitHub repository, a status request, GitHub refusing CI for billing | 1 | 0.0 | 2 | 3.7 | The repository only |
| All | 63 | 100.4 | 37 | 121.6 | |

- **troy-mode waited for Troy 67% of v0.1's 150 hours, and 87% of the 139 hours since.** The pilot report's 48 hours counted only the 34 `Waiting for Troy` comments.
- **No stop came from a review loop's round 3, a failed attempt, or an escalation**, in either period. Part 2 of F18 removes stops that have not happened yet on a real project.
- **The largest stop that 3.3 and 5.7 do not list is the end of a request's reach:** 34 stops and 67.9 hours. In v0.1, 12 of its 15 came after a feature's acceptance, because each request named one feature (pilot report problem 10, which F07 D203 has since fixed for a request that names a version). Since the pilot, 14 of its 19 came after a single stage: in 12 of them, Troy's request had named only that stage, such as "Start the mock", and twice troy-mode merged an approved design and stopped although the request named the whole feature (#113, #123), which D203's "after Troy approves, go on within the same reach" now covers.
- **The questions that no instruction asks for** were whether to restore a file that a hung role run had changed, a case that F05 D231 now catches, where a speed-up goes, into the implementation PR or a refactor PR first, whether Troy wants to merge a typo fix in a document, and whether to turn on the progress issues' sync. A sixth, D62's "keep approving them?", is a question the instructions ask for, W3 here.
- **Usage limits** cost 46.7 hours. Since the pilot, 15.0 of them passed before the limit reset and 26.5 after it, until Troy came back (section 14).

### 2.2 What Troy's approvals changed

Troy approved all 32 design and test plan PRs, 26 in v0.1 and 6 since, without changing anything: no comment on any PR, no revision asked, and every decision point answered with the recommended option or with a plain approval. Two came close: the F03 design (#20) was approved with its two decision points left open, which were settled later as recommended, and the F06 design (#40) was approved as it was, without the Architect's two optional suggestions. The same holds for every other approval: the requirements, the architecture, five architecture changes, one requirement change, and the retrospective's rules. The design and test plan approvals waited 58.6 hours.

### 2.3 Review rounds and attempts

Round 2 was needed on 35 of the 57 reviewed PRs in v0.1 (61%) and on 8 of 15 since (53%). Three PRs reached round 3, all in v0.1, and each was approved there: the F04 mock (#29), the F10 tests (#68), and a P01 test fix (#97). No stage needed more than 2 attempts: the F08 and F09 designs (#52, #59), whose Python examples failed CI's `ruff format`. No escalation was posted.

The full tables, with every stop, its quote, and its wait, are in the evidence notes that the design session kept on Troy's PC; the numbers above come from them.

### 2.4 The evidence F12 and F16 give today

- **Real runs (F12).** In v0.1, F12's acceptance ran 47 prototype commands, 41 matched and 6 waited for F13, and F13's ran all 48, which matched; the v0.1.0 release test matched all 48 again. In v0.2, F14 is "Ran for real on Troy's PC" and F15 "Passes tests on main". The real runs have not caught a design that missed what Troy asked for, and in v0.1 Troy approved every design before the real run could check it.
- **The role exam (F16) on `main`.** The cases of the roles behind PR 1 and PR 2 have little evidence yet:

| Case | Role, task | Newest runs on `main`'s instructions or close to them | Pass |
| --- | --- | --- | --- |
| ar-design-review | Architect, AR2 | Exam 2026-11-23-1, base and head | 0 of 5 and 0 of 5 |
| ar-error-review | Architect, AR2 | Exam 2026-11-23-1, base and head | 1 of 5 and 1 of 5 |
| if-example-format, if-error-rules | Interface Designer, IF1 | None: the Interface Designer's base runs are not made yet (requirements, F16 row) | Unknown |
| tm-plan-expected | Test Manager, TM1 | None | Unknown |
| cr-mock-review, cr-test-review | Code Reviewer, CR1 | Exam 2026-11-24-1 | 5 of 5 each |
| dv-mock-notes, dv-impl-notes | Developer, DV1 and DV2 | Exams 2026-11-22-3 and 2026-11-24-4 | 5 of 5, and 8 of 10 |

So the Architect's design review, which is what stands between a design and the code when Troy does not approve it, passed 2 of 20 runs. In ar-error-review, 7 of 10 runs approved a design whose failure lines break the architecture's error rules. In ar-design-review, every run asked for changes, but none found all three of the pilot's faults; most missed the example lines that `ruff format` rejects. The authors of PR 1 and PR 2 have not been measured. Section 7.3 turns this into the bar for spot checks.

## 3. Where troy-mode stops today

The engine counts and records; the entry skill (`skills/troy-mode/SKILL.md`) and the Product Manager's instructions (`troy-mode/roles/product-manager.md`) decide when to stop. The engine never stops by itself: `status` gives `merged_by: troy` and `waiting_on_troy`, and `check-run`, `merge-check`, and `plan` give an `escalate` flag or a problem. Every place where the skill or the Product Manager's instructions stop today:

| # | Stop | Where today | In 3.3 or 5.7 today | F18 |
| --- | --- | --- | --- | --- |
| S1 | The requirements, and each change of them | PM1 step 9, PM2 step 1; skill "Project setup", "Requirement change" | 3.3 step 1 | Stays: W1 |
| S2 | The architecture, with the series question | Skill "Project setup" step 3 | 3.3 step 2 | Stays: W2 |
| S3 | PR 1 and PR 2 of the first `troy_approves_first` features; the question after them (D62) | `merged_by`; skill "Merging" | 3.3 step 3, Q2 | Stays: W3. Spot checks change which PRs wait (section 7). |
| S4 | The version: Troy's device test and acceptance; deferring an open bug (F08 D74) | Skill "Version release" | 3.3 step 4 | Stays: W4 |
| S5 | Rules: the retrospective's proposals Troy picks (F08 D76), each rule's enforcement and the choice for existing code (F09 D81, D82), a rule for every project as a tstack issue (D83) | Skill "Rule change", "Retrospective" | Neither: 5.5 step 6 and 5.8 say Troy decides, 3.3 does not list it | Stays: W5. Proposal P1 lists it in 3.3. |
| S6 | A change needs the requirements or the architecture to change: a role's `escalate`, AR4's or AR6's architecture change | Skill "Escalation", "Requirement change" | 5.7 | Stays: W6 |
| S7 | A role's `needs-answer` for Troy; a real-run mismatch that TM8 rules a requirement question (PM3 step 4) | Skill "The report"; PM3 | Neither | Goes away unless it is S6: the Product Manager answers from the approved documents (section 4.3) |
| S8 | A review loop's round 3 still ends in `changes-requested` | Skill "Rounds and attempts", "The report" | 5.7, R17, until F18 | Goes away: a ruling (section 5) |
| S9 | An author's third failed attempt | Skill "Rounds and attempts", "The report" | 5.7 | After a premise attempt: W7 (section 6) |
| S10 | A new third-party dependency | AR3's `escalate` | 5.7 | Stays: W8 |
| S11 | An action outside troy-mode's rights: a force push of another branch, deleting data, creating the GitHub repository and replacing files troy-init did not write (F06), opening an issue in tstack | Skill "Escalation", "Project setup", "Rule change" | 5.7 | Stays: W9 |
| S12 | A refusal troy-mode must not work around: Claude Code's permissions or auto mode refuse a command it needs (the pilot's problem 8), `TaskStop` refused, `gh pr merge` refused | Skill "Running a role", "Merging" | Neither | Stays: W10. Proposal P2 lists it in 5.7. |
| S13 | troy-mode's own checks find a fault it cannot repair: a run moved `HEAD` or the branch, broke its write scope twice, or gave no report twice; AR7's plan failed twice; a rebase conflict across scopes (F20 D273); CI failed outside the authors' files; no check reported after two waits; a PR's head or state changed under troy-mode | `check-run`, `plan`, `merge-check`, `wait-checks`; skill "Running a role", "Merging", "Feature teams" | Only the rebase conflict (5.11) | Stays: W11, except that a CI failure outside the authors' files is re-run once first (section 4.3). Proposal P2 lists it in 5.7. |
| S14 | Troy closed an idea whose change PR is still open | Skill "Issues for Troy" | Neither | Goes away: troy-mode closes the PR, which can be reopened, and reports it (section 4.3) |
| S15 | The request fits no flow or two; a folder with no `.troy-mode/`; an unclear idea | Skill "Routing"; PM6 | Neither | Not a stop inside a flow. Section 4.1 keeps it as it is. |
| S16 | The request's reach ends while work of the version remains: after a feature's acceptance when the request named one feature, or after a stage when it named one stage (F07 D63, D203) | Skill "Routing", "How far" | Neither | Goes away: a feature-loop request reaches the rest of the version, through the release's steps up to Troy's device test (W4), unless Troy names where to stop (section 4.3) |
| S17 | A question that no instruction asks for, such as where a refactor goes or whether Troy merges a typo fix | Nowhere: the main session's own judgment | Neither | Goes away: the Product Manager decides, and says why in the PR and the report (section 4.3) |

## 4. The waits for Troy (D171, D172)

### 4.1 The list

Only these steps wait for Troy (D172). The IDs are new; each wait names its ID wherever troy-mode records it.

| ID | Wait | From | How troy-mode asks |
| --- | --- | --- | --- |
| W1 | The requirements, and each change of them | 3.3 step 1, 5.4 | The PR and its summary for Troy; `Waiting for Troy: approve this PR` |
| W2 | The architecture | 3.3 step 2 | The same |
| W3 | PR 1 and PR 2 of the first features, the question after them (D62), and with spot checks on, a PR marked risky (section 7.2) | 3.3 step 3, Q2 | The same |
| W4 | The version: Troy's device test and acceptance, and deferring an open bug | 3.3 step 4, 5.5 | The release PR, `Waiting for Troy: accept <tag>`, and the checklist issue |
| W5 | Rules: the retrospective's proposals, each rule's enforcement and the choice for existing code, and a rule for every project | 5.5 step 6, 5.8 | `Waiting for Troy: <rule question>` in chat and on the release PR or the rule's issue |
| W6 | A change needs the requirements or the architecture to change | 5.7 | `Escalation: <trigger>` |
| W7 | An author's work still fails after 3 attempts and a premise attempt, or after a ruling it was given | 5.7 | The same |
| W8 | A new third-party dependency | 5.7 | The same |
| W9 | An action outside troy-mode's rights | 5.7 | The same |
| W10 | A refusal troy-mode must not work around | 5.7 by proposal P2 | The same |
| W11 | A fault in troy-mode's own checks that it cannot repair | 5.7 by proposal P2 | The same |

Asking what Troy means is not a stop inside a flow. Before a flow starts, troy-mode may ask one question with a recommended answer when a request fits two flows or none, or the folder is not a troy-mode project (F07 section 4), and an unclear idea gets one question on its issue (F15 D143). Once a flow runs, only a wait of the list stops it.

### 4.2 Where the list lives, and what checks it (D171)

The list lives in one place, a new section "Waits for Troy" in `troy-mode/roles/product-manager.md`, which the entry skill reads at every start. Every place where the skill stops names the wait's ID, and the engine knows the IDs:

- A new engine module, `troyflow/waits.py`, holds the eleven IDs, their kind (approval or escalation), and a short English name.
- `status --waiting <text>` gains `--wait <ID>`, and refuses a wait without a listed ID (exit 1, problem `wait`). The progress file says, for example, "Waiting on Troy: W3, approve PR #41".
- Under the `Waiting for Troy:` and `Escalation:` headings, the comment's next line is `Wait: W<n>`. `status` gives the ID in `waiting_on_troy`, and F15's progress issue shows it. An older comment without the line still counts as a wait, with the ID `unlisted`.
- `retro` counts the version's waits by ID, with how long each waited, and lists every wait without a listed ID as `unlisted`, so the retrospective sees a stop that the list does not allow.

The engine cannot see the main session end its turn in chat without recording anything. That gap stays: the list and the record make such a stop visible in the next `status` (nothing waits, so `next` is the next step) and in the retrospective, and a later issue can add a hook if the retrospective finds unlisted stops (D171 option B).

### 4.3 The stops that go away (D172)

- **The end of a request's reach** (S16). A feature-loop request, such as "next feature", "F04", "Start the mock", or "continue", reaches every feature of the current version that is not yet accepted, and the release's steps after them up to Troy's device test (W4): the version tests, the release test on Troy's PC, and the release PR, none of which is irreversible before Troy accepts. Troy limits a request by naming where to stop, such as "only F04" or "stop after the mock". The next version starts with Troy's request. This changes F07 D63 and D203: a request that names one feature or one stage no longer ends there, which is what the 34 stops of section 2.1 did.
- **A question that no instruction asks for** (S17). The Product Manager decides it, as pstack's never-block-on-the-human rule says for reversible work, and says what it chose and why in the PR's description and the report. A choice that changes what Troy will see or keep is W6, since it changes the requirements.
- **A role's question for Troy** (S7). The Product Manager answers it from the approved requirements, architecture, design, and test plan, and puts the answer in the next brief's Input and in the PR's description. Only a question that one of those documents cannot answer without a change is a wait, W6. The same holds for a real-run mismatch that TM8 rules a requirement question (PM3 step 4).
- **A review loop's round 3** (S8): a ruling, section 5.
- **An author's third failed attempt** (S9): a premise attempt first, section 6.
- **A CI failure outside the authors' files** (S13). F07 re-runs the failed jobs once (`gh run rerun <run ID> --failed`), which joins its rights, and waits for the checks again. Only a second such failure on the same commit is W11. In the pilot, the one such failure, the "Repository not found" checkout on #87, passed on the next push.
- **A closed idea with an open change PR** (S14). F07 closes the PR without merging it and says so in its report. Closing is in F07's rights, and Troy can reopen it.

Every other stop of section 3 stays, now under its ID.

## 5. A review loop's third round (D173, D174)

### 5.1 Who rules (D173)

When round 3 of a review loop still ends in `changes-requested` (F07 section 8.3), F07 starts a ruling instead of escalating:

| The loop | Reviewer | Rules at round 3 |
| --- | --- | --- |
| PR 1, a design, and a `[docs]` design update (F07 section 8.7) | Architect (AR2) | Product Manager, new task PM7, in the main session |
| PR 2, the test plan's questions to the Interface Designer | Interface Designer (IF3) | Architect, new task AR8 |
| PR 3 and PR 5, bug PR B, a rule's cleanup PR | Code Reviewer (CR1) | Architect (AR8) |
| PR 4, bug PR A, a test fix | Test Manager (TM2) and Code Reviewer (CR1) | Architect (AR8) |

### 5.2 The ruling (D173)

1. **Input.** The three rounds' review comments, the author's answers from its reports, and the PR's diff or document. The ruler reads only the parts of the document that the open findings name: for PM7, that keeps a design of up to 185,000 characters out of the main session (F14 design D131).
2. **Each open finding** of round 3 gets `fix` or `does not block`, each with one sentence of reason from the requirements, the architecture, the design, the test plan, or the rules. A finding that needs one of those documents changed is W6, an escalation. A finding that does not block but is worth doing later becomes a note for a later feature (F07 section 6.6) or an idea issue.
3. **No `fix`:** the stage goes on to its merge.
4. **Any `fix`:** the author runs once more with only the `fix` findings in Input. This run is neither a round nor an attempt, unless its checks fail, which counts an attempt as always. The ruler then checks only those findings, and the stage goes on to its merge when each is fixed. A finding still not fixed is W7.
5. **The ruler changes no file.** AR8 and PM7 are rulings, like TM4 or IF4 (F07 section 6.3).

### 5.3 The record and Troy's overturn (D174)

- **The comment.** F07 posts the ruling with a new fixed heading, `<Ruler> ruling, round 3: <result>`, where the ruler is `Architect` or `Product Manager` and the result `merge`, `fix`, `fixed`, or `not fixed`, then one numbered line per finding: `1. fix: <reason>` or `1. does not block: <reason>`. `status` reads these headings as `rulings`.
- **The PR.** The description's What gains one sentence: "The <ruler> ruled at round 3 (<link>): <one line>. Troy can overturn it on the feature's progress issue."
- **Troy sees it** in the report after the merge, in Troy's language, and on the feature's progress issue, where F15's body gains a line per ruling with its link.
- **The overturn.** Until the feature's acceptance, Troy overturns a ruling with a comment on the feature's progress issue, or in chat, saying which side wins. Such a comment is already read as a message in chat (F15 D145). F07 answers it on the progress issue with a comment headed `Overturn: <link to the ruling>`, a new heading among those F15 writes on issues (F15 design 8.4), so any session finds the overturn on GitHub, and holds the feature, and its team (F20), after its current stage PR. It carries the overturn out through the flow that the ruled stage already has:

| The ruled PR | How the overturn is carried out |
| --- | --- |
| PR 1, a design | A `[docs]` design update by IF2 with Troy's decision as Input, reviewed by AR2 (F07 section 8.7); stages that merged on the old design are redone as in rework (F07 section 11.2) when an interface changed |
| PR 2, a test plan | A `[docs]` test plan update by TM1, then a test fix when PR 4 has merged |
| PR 3 or PR 5, code | A bug: PR A's test and PR B's fix (5.3), with Troy's decision as the report |
| PR 4, tests | A test fix by TE3, reviewed by TM2 and CR1 |

The feature goes on when those PRs merge. These PRs carry out Troy's own decision, so F07 merges them; Troy sees them in the report. After the feature's acceptance its progress issue is closed, and Troy's disagreement is an idea issue like any other: a requirement change or a bug (F15 D143).

## 6. The premise attempt (D175)

After an author's third failed attempt in a stage (F07 section 8.5), F07 runs the author once more, in a fresh run, with a fixed text that makes it test the premise first:

1. `status` gives `next.premise: true` when the stage's attempt count is 3. F07 runs the author's task with `brief --premise`, the three failures in Input.
2. `brief --premise` adds to the Task line a fixed text from a new module, `troyflow/premise.py`, and adds `skills/principle-attack-the-premise/SKILL.md` to Read first. The text says: this is the fourth attempt, and the three before it failed with the checks in Input; before changing any file, write down in one sentence the premise that all three attempts shared; test it with a check that changes no file, naming the observation that would come out differently if the premise were false; then follow the evidence, fixing on the new cause when it lies inside the role's write scope, or reporting `escalate` when it lies outside, such as in a check, a test the role does not own, the design, or the environment; and start the report's Notes with three lines, `Premise:`, `Check:`, and `Result:`.
3. The run counts as attempt 4, with the usual comment heading, `<Role> attempt 4: failed`, when it fails, and with the three lines under it. CI failures in the author's files count as before (F07 D261).
4. When attempt 4 fails, or its report is `escalate`, F07 escalates (W7). The escalation message gives the premise, the check, and its result, so Troy starts from the evidence. When the evidence names another wait, such as a dependency (W8) or the architecture (W6), the escalation names that one.
5. When the Product Manager is the author (PR 6), the main session follows the same card itself before its fourth try.

In the pilot, the stages that failed more than once were the F08 and F09 designs (#52, #59): their Python examples failed CI's `ruff format` twice each, a check the Interface Designer could not run (pilot report problem 9). A premise attempt there would have named "the design's examples are badly formatted" as the shared premise, checked how CI formats them, and found the cause outside the author's scope: CI's `ruff` read `docs/`. That is an escalation with its evidence, and tstack issue #51 later fixed that cause by keeping `ruff` out of `docs/`.

## 7. Spot checks (D176 to D179)

Spot checks replace the approvals of 3.3 step 3 only: PR 1 and PR 2 of features after the first `troy_approves_first`. They are off until Troy turns them on in a project, and troy-mode never turns them on itself.

### 7.1 The sample (D176)

- **Which features.** One feature in three, counted in the topological order from the first feature after the approved ones: the third, the sixth, the ninth, and so on. `[flow] spot_check_every` sets the number, 3 by default. Any session finds the same sample from the order on `origin/main`, and F15's progress issue says when a feature is in it.
- **When Troy reviews.** After the merge. F07 merges a sampled PR 1 or PR 2 as it merges PR 3 to PR 6, posts `Spot check for Troy: review after the merge` on the PR with one line, "What to decide is in the summary at the top of the description.", and sends Troy its summary for Troy, with the link, in the report. Troy agrees by doing nothing or by a comment, and disagrees with a comment on the feature's progress issue, which works as an overturn (section 5.3). After the feature's acceptance, Troy disagrees with an idea issue that names the PR, which PM6 takes in as a requirement change or a bug, and which counts as an overturn of the sample (section 7.4).
- **Before the version ships.** The version's checklist issue (F15 D144) gains one box for each sampled PR of the version that Troy has not answered, so accepting the version means Troy has looked at every sample. A box Troy ticks records the review.
- **A risky PR waits** before its merge, as an approval does today (section 7.2).

In v0.1, with the first three features approved, this samples F06, F09, and F12, 6 of the 20 later PRs; the other 14 merge without Troy.

### 7.2 Risky PRs (D177)

A PR 1 or PR 2 is risky, and waits for Troy before its merge (W3), when any of these marks it:

- **The engine**, from the state: the design changes an interface of an accepted feature (its section 3 lists one, F07 section 11.2); a review loop on the PR needed a ruling at round 3 (section 5); or the stage needed a premise attempt (section 6). The test plan, PR 2, takes PR 1's mark too.
- **The Architect**, in AR2's report on PR 1: a new line `Risky: no`, or `Risky: <reason>`, with a reason from a fixed list: a stored data format or a file Troy keeps changes; Troy's files are deleted or moved; behavior that Troy will see and that the prototypes do not show; network access, a subprocess, or credentials (F04 design D280's signs). F07 posts the line in the review comment, where `status` reads it.
- **Troy**, at any time before the PR merges: "F12 is risky" in chat, or a comment "risky" on a progress issue. F07 records it as a note for that feature (F07 section 6.6) whose text starts with `Risky:`, so any session sees it.

### 7.3 Enough evidence (D178)

troy-mode recommends spot checks in a project only when all three of these hold, and shows them to Troy whenever it asks (section 7.4):

| | Evidence | Measured by | Today, in `ZJUCao/recipe-menu` |
| --- | --- | --- | --- |
| E1 | Troy's approvals: Troy's answers to the project's last 6 waits for PR 1 and PR 2 changed nothing: each approved every recommendation, with no other option picked and no change asked in a comment | `status`, from the PRs' comments and Troy's replies | Holds: the last 6, F14 to F16's PR 1 and PR 2, changed nothing, nor did any of the 32 (section 2.2) |
| E2 | Real runs: no real-run mismatch of the project's last version came from an error in a design or a test plan, by TM8's rulings | `status`, from the acceptance PRs' Real run sections and TM8's comments | Holds for v0.1 and so far for v0.2 |
| E3 | The role exam: each case of the roles behind PR 1 and PR 2, if-example-format, if-error-rules, ar-design-review, ar-error-review, and tm-plan-expected, passes at least 4 of 5 runs on the plugin's current instructions (F16 D155's bar for a fix) | `status`, from the exam's case logs on Troy's PC (`TROY_EXAM_ROOT`, default `D:\Troy\troy-mode-work`); "unknown" on a PC without them | Does not hold: the Architect's cases pass 0 and 1 of 5, and the other three have no runs |

So spot checks are not recommended now. The earliest is after three steps, none of which is part of F18's build:

1. Base runs of the three author cases on `main`, about $51 by `troy_exam`'s budget code: if-example-format and if-error-rules $18.95 each, tm-plan-expected $13.05. It waits for Troy's yes when its time comes.
2. A hillclimb of the Architect's AR2 (F16 design 8.3) that lifts both Architect cases to 4 of 5. Its cost is unknown until it is designed; one round of both cases costs about $60. F17's PR 2 ran it (F17 design D165 and 12.6, plugin 0.20.1): ar-error-review from 0 of 5 to 5 of 5, and ar-design-review from 0 of 5 to 3 of 5, one run short of E3's bar.
3. E1 and E2 measured again at the end of recipe-menu's v0.2.

Troy can still turn spot checks on at any time; troy-mode then says which evidence is missing.

### 7.4 On and off, per project (D179)

- **The setting.** Two new keys in the project's `.troy-mode/config.toml`, next to D62's count: `[flow] spot_checks`, `true` or `false`, `false` by default, and `spot_check_every`, a whole number of 2 or more. troy-check's config reader learns them, and a project gets that through troy-init's upgrade, as with `[flow]` itself (F07 section 12).
- **The question.** When the first `troy_approves_first` features are accepted, D62's question gains a third answer: Troy goes on approving (and how many), turns on spot checks, or lets Claude merge every PR 1 and PR 2. The question shows E1 to E3 and troy-mode's recommendation.
- **Turning them on or off.** Troy says so in chat, or in a comment on any progress issue, at any time. F07 records it in a `[rules] Set the features Troy approves` PR, the PR of D62, with `troy_approves_first` set to the features accepted so far and a comment line that names Troy's decision and its date, and merges it. Off brings back the approvals of every later PR 1 and PR 2.
- **An overturn turns them off.** When Troy overturns a sampled PR, or a ruling on a PR 1 or PR 2 (section 5.3), F07 turns spot checks off at once in the same kind of `[rules]` PR, since the evidence no longer holds, and says so. Turning them off only adds waits, so troy-mode may do it alone; turning them on again is Troy's.
- **Per project.** Each project's config holds its own setting, so `ZJUCao/recipe-menu` and a second project choose apart.

### 7.5 With feature teams and merges (D179)

- **Teams (F20).** A risky PR's wait stops only its team and the teams that wait for its feature, and it joins the one message that lists every waiting PR (Q23). A sampled PR stops no team: the report lists it under its own line, "Spot checks, after the merge". An overturn holds its feature's team after its current stage PR, as a requirement change holds the teams it affects (Q24), with `held` reason `overturn`. The sample counts features in the topological order, so which team builds a feature does not change whether it is sampled, as for `troy_approves_first` (Q23).
- **Merges.** F07 merges a PR 1 or PR 2 under spot checks exactly as it merges PR 3 to PR 6: `wait-checks` on the pushed head, R24's rebase onto the latest `main`, and `gh pr merge --rebase --match-head-commit`. troy-mode uses no GitHub auto-merge in a project: Troy's private repositories have no branch protection (requirements section 6), and R24 needs the rebase check. tstack's own auto-merge is unchanged.

## 8. The engine

| Command or module | Change | Part |
| --- | --- | --- |
| `troyflow/waits.py` (new) | The eleven wait IDs, their kind, and name (section 4.2) | 1 |
| `status --waiting --wait <ID>` | Refuses a wait without a listed ID; `waiting_on_troy` gives the ID | 1 |
| `github.read_comments` | Reads `Wait: W<n>`, the `<Ruler> ruling, round 3: <result>` heading, and on progress issues `Overturn:` | 1 |
| `status` | `rulings` per open PR; `next.action` `ruling` (task AR8 or PM7) when round 3 ends in `changes-requested` with no ruling; `ruled-revision` after a `fix`; `next.premise` when the attempt count is 3; `overturns`, and `held` reason `overturn` | 1 |
| `brief` | `--task AR8`; `--premise`, with the text of `troyflow/premise.py` (new) and the premise card in Read first | 1 |
| `retro` | `waits` by ID with `unlisted`, `rulings`, `premise_attempts`, and `overturns` (F08 section 7) | 1 |
| `state.merged_by` | With spot checks on: `troy` for the first features and for a risky PR, `f07` otherwise, and `spot` `sample` or `none` for each feature | 2 |
| `status` | `spot`: on or off, the number, and the sample; `risky` per open PR with its reasons; `spot_evidence`, E1 to E3, at `ask-approvals` | 2 |
| `issues` (F15) | Progress issue lines for a wait's ID, a ruling, a sampled PR, and a risky mark; the checklist's boxes for unanswered samples | 1 and 2 |
| troy-check's config reader | `[flow] spot_checks` and `spot_check_every` | 2 |

The engine still never commits, pushes, or writes to GitHub (F07 section 3.1).

## 9. Changes to earlier features

| Feature | Change |
| --- | --- |
| F04 Role definitions | `product-manager.md`: the section "Waits for Troy" (section 4.1), PM7, and PM3 step 4 and PM6 answering from the approved documents (section 4.3). `agents/troy-architect.md`: AR8, and AR2's `Risky:` line (section 7.2). |
| F05 Hooks | None, under D171 A. |
| F07 Entry skill | The engine of section 8. A feature-loop request's reach, D63 and D203, goes on to the version's device test (section 4.3). The skill's sections "Routing", "The report", "Rounds and attempts", "Comments", "Merging", "Feature teams", "Issues for Troy", "Escalation", and "Continue" name the waits and gain the ruling, the premise attempt, the re-run of a CI failure outside the authors' files, the closing of a change PR, and spot checks. F07's rights gain the re-run. |
| F08 Release | `retro` reports waits, rulings, premise attempts, and overturns. The release's waits are W4 and W5. |
| F09 Rule change | Its waits are W5. |
| F10 Docs | The guide's "Taking part" and "Reference" chapters describe the waits, rulings and overturns, and spot checks. |
| F14 Summary | None to the summary. A sampled PR's summary is what Troy reviews after the merge. |
| F15 Issues | The progress issue's lines of section 8; Troy's overturn and "risky" comments on it, read as messages in chat (D145), and the new heading `Overturn:` (design 8.4); the checklist's boxes for unanswered samples. |
| F16 Role exam | The instruction set changes as section 10 says. The Product Manager has no cases yet (F16 D151), so PM7 and the list of waits are checked by the trial only. |
| F20 Teams | The `overturn` hold, and the line for spot checks in the one message (section 7.5). |
| troy-check (F02) | The config reader's two keys (section 7.4). |

## 10. The role exam (F16)

F18 changes these files of F16's instruction set (F16 design 9.1):

| File | Change | Cases it affects |
| --- | --- | --- |
| `agents/troy-architect.md` | AR8 (D173 A) and AR2's `Risky:` line (D177 A) | ar-design-review and ar-error-review: the agent file is part of every Architect case's input |
| `troyflow/brief.py` and `troyflow/premise.py` | AR8's brief and the premise text, only with `--task AR8` or `--premise` | None: no case renders either |
| The entry skill's sections "Running a role" (with "The report") and "The summary for Troy" | The ruling, the premise attempt, and spot checks | None: no case's `input.md` changes (F16 design 9.2) |

`product-manager.md` is not in the instruction set. No template, `common.md`, or other agent file changes.

**The estimate**, from `troy_exam.py`'s budget code with each case's recorded median, $2.77 for ar-design-review and $2.81 for ar-error-review: `main`'s instruction hash has no recorded run of either case, so both versions run fresh, five runs each, plus one $2.00 judge pass per case. The first round is $59.78, and the whole, with each case's second round, $119.55. The first round is just under F16's $60 line, but the same two cases cost $65.14 in exam 2026-11-23-1, so the build asks Troy's yes for up to $119.55 before it starts. An exam whose spending reaches 1.5 times its estimate still waits for Troy (F16 section 10.2). Under D173 B and D177 B, no agent file changes, and the exam costs $0.

## 11. How F18 maps to the requirements

| Requirement | Where F18 covers it |
| --- | --- |
| F18 row: the Product Manager's instructions list the waits | Sections 4.1 and 4.2 |
| F18 row and 3.3: every other step goes on and reports in its PR | Sections 3 and 4.3 |
| F18 row, 5.7, and R17: a review loop's third round | Section 5 |
| F18 row and 5.7: the premise attempt | Section 6 |
| F18 row, 3.3, and Q15: spot checks | Section 7 |
| 3.3 and 5.11: waits with teams (Q23) | Section 7.5 |
| R18: merges under spot checks | Sections 7.1 and 7.5 |

## 12. Requirement text F18 needs (proposals)

Troy approved all seven on 2026-11-25 ("全按推荐"), as written. P1, P2, P5, and P7 land in requirements 1.64, which records F18's decisions; P3, P4, and P6 land with the build that the "When" column names.

| # | Where | Proposed text | When |
| --- | --- | --- | --- |
| P1 | 3.3, the list | Add a sixth item: "6. Rules: which of the retrospective's proposals become rules, each new or changed rule with how existing code meets it, and a rule for every project (5.5, 5.8)." Step 4 adds: "and which open bugs it may ship with". The paragraph after the list adds: "The Product Manager's instructions hold this list, with the escalations of 5.7, as the waits W1 to W11, and troy-mode records each wait with its ID (F18 design D171)." | Requirements 1.64 |
| P2 | 5.7, the triggers | Add two triggers: "Claude Code refuses a step troy-mode needs, such as a permission, which troy-mode never works around." and "troy-mode's own checks find a fault it cannot repair, such as a role that moved its branch, a write scope broken twice, or CI that fails twice outside the authors' files." | Requirements 1.64 |
| P3 | 5.7, the last paragraph, and R17 | 5.7: "When a review loop reaches 3 rounds without agreement, troy-mode does not stop. The Architect, or the Product Manager when the loop is the Architect's own review, rules on each open finding and writes the reason in the PR. Troy can overturn a ruling on the feature's progress issue until the feature's acceptance (F18 design D173, D174)." R17: "At 3 review rounds without agreement, the Architect, or the Product Manager when the loop is the Architect's own review, rules and records the reason in the PR. Troy can overturn the ruling (5.7)." The sentence "Until F18 is built, ..." goes. | With part 1's build |
| P4 | 3.3, the spot check paragraph, and R18 | 3.3: "Once real-run acceptance (F12) and the role exam (F16) give enough evidence, Troy can turn the approvals of step 3 into spot checks, per project: Claude merges, Troy reviews one feature in three after the merge and before the version ships, and every PR marked risky waits for Troy (F18 design D176 to D179)." R18 adds: "With spot checks on, Claude also merges PR 1 and PR 2 of later features, except a risky one." | With part 2's build |
| P5 | Q15 | Proposal column: "Answered by the F18 design: one feature in three, reviewed after the merge and before the version ships; risky PRs, marked by the engine, the Architect, or Troy, wait; the bar is Troy's last 6 approvals unchanged, no real-run mismatch from a design or test plan, and the cases of PR 1's and PR 2's roles at 4 of 5 (D176 to D178)." | Requirements 1.64 |
| P6 | 3.4, Prototype C | Replace the example's trigger with a premise attempt: "Why: the Developer's implementation failed its checks 4 times. The last attempt tested what the first three assumed: that the timeout test is wrong. It is not: the architecture's retry rule makes the call take 31 seconds." The options and the recommendation follow as now. | With part 1's build |
| P7 | The F18 row | Its description gains the IDs and the parts as approved, as the F20 row does after its design. | Requirements 1.64 |

No other requirement text changes. Q2 stays: Troy still decides after the first features, now with spot checks as one answer.

## 13. How F18 is checked (D180)

### 13.1 Tests

A separate agent writes the tests from this design before the code, as for every tstack feature, with `unittest`, the standard library, and the fake `gh` of F07's tests. They run on Linux and Windows in CI.

| Group | Cases include |
| --- | --- |
| Waits | Every ID of the list; the skill's routing gives a request that names one feature or one stage the rest of the version, up to the device test, and "only" or "stop after" a smaller reach; `--wait` missing, unknown, and listed; `Wait: W<n>` read under both headings; an older comment without it counted as `unlisted`; the progress file's line; `retro`'s count by ID and its `unlisted` list. |
| Rulings | `next.action` `ruling` only when round 3 ends in `changes-requested`, with AR8 for each loop of section 5.1 and PM7 for the Architect's; the four results; a `fix` leading to `ruled-revision` and then the check; `not fixed` as W7; Troy's comments never read as rulings; AR8's brief. |
| Overturns | An `Overturn:` comment on a progress issue holds the feature and its team; the flow per stage of section 5.3; the hold ends when those PRs merge; an overturn of a sampled PR or of a ruling on PR 1 or PR 2 turns spot checks off. |
| Premise | `next.premise` only at an attempt count of 3, with attempts from comments and from CI (D261); `brief --premise` adds the text once and the card to Read first, for every author task; a fourth failure gives W7. |
| Spot checks | The config keys accepted and refused (troy-check); the sample by order with `troy_approves_first` at 0, 3, and past the features; `merged_by` for a sampled, a risky, and another PR; each engine risk signal; the Architect's `Risky:` line; Troy's `Risky:` note; E1 to E3, with E3 "unknown" without the case logs; the checklist's boxes; teams' holds and the message's lines. |

### 13.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: the reach ended after one feature, a wait recorded without an ID, an unlisted ID accepted, a ruling started at round 2, a ruling started when round 3 approved, AR8 given the Architect's own loop, the ruled revision counted as a round, `not fixed` merged, a Troy comment read as a ruling, an overturn that does not hold the team, the premise flag at attempt 2 or 4, the premise text added twice or to a reviewer, the fourth failure not escalated, the sample counted from the first feature instead of after the approved ones, a risky PR merged, PR 2 without PR 1's mark, spot checks left on after an overturn, E3 read as passing without logs, and the old `[flow]` table refused by the new reader. The counts go in each PR's description.

### 13.3 Trial

Each part runs a trial on `ZJUCao/troy-mode-trial`, in nested `claude -p` sessions with tstack loaded from the PR's branch (F07 section 14.3). The trial's prompts give Troy's answers. Its repository is public, so the trial's text holds nothing private.

Part 1, about $35:

1. **Waits and the reach.** "Next feature" runs on through the version, past the feature's acceptance, to its first listed wait. Every wait comment and the progress file name the ID, and `retro` finds no `unlisted` wait.
2. **A code loop at round 3.** A mock PR with rounds 1 to 3 of the Code Reviewer's findings prepared as comments, one finding right and one that contradicts the design. AR8 rules `fix` and `does not block`; the Developer fixes the first; AR8's check gives `fixed`; F07 merges.
3. **A design loop at round 3, and an overturn.** A design PR with the Architect's three rounds prepared. PM7 rules `merge`. "Troy" then overturns it on the progress issue: the feature is held, and the `[docs]` design update runs, is reviewed, and merges before the feature goes on.
4. **A premise attempt.** A stage with three attempt comments prepared, whose checks cannot pass from the author's scope. The fourth run writes `Premise:`, `Check:`, and `Result:` and reports `escalate`; F07 escalates with W7 and the evidence.

Part 2, about $40:

5. **The question.** After the trial project's approved features, `ask-approvals` shows E1 to E3, and "Troy" turns on spot checks with `spot_check_every = 2`: the `[rules]` PR merges.
6. **Two features as two teams.** Feature A is sampled: its PR 1 and PR 2 merge without a wait, with the spot check comment and the progress issue's line. Feature B's design changes a file the program keeps, so the Architect marks it risky: it waits for "Troy", and only team B stops.
7. **An overturn of a sample.** "Troy" disagrees with A's design on its progress issue: the overturn runs, and spot checks go off in a `[rules]` PR.

Each part's trial waits for Troy if it runs past 1.5 times its estimate.

### 13.4 Status and order

F18 lands in two PRs (D180), each with one commit and its tests written first:

1. **Part 1**, the next minor plugin version, 0.18.0 if nothing comes before it: the waits (section 4), rulings (section 5), the premise attempt (section 6), the re-run and the closing of a change PR, and AR2's `Risky:` line, so that every file of the instruction set that F18 changes lands here, with one exam (section 10).
2. **Part 2**, the minor version after it: spot checks (section 7), with troy-check's two keys and F15's lines. It changes no agent file, so its exam finds no case affected.

Part 1 changes the instruction set, so it waits until no other PR that changes it is open, as every such PR does.

| When | F18's status in requirements 7.2 |
| --- | --- |
| Part 1 merges after its trial | Runs on a sample project, part 1 of 2: on the scratch GitHub project, every stop named a listed wait, a code loop and a design loop were ruled at round 3, a ruling was overturned, and a premise attempt escalated with its evidence. Spot checks are not built. |
| Part 2 merges after its trial | Runs on a sample project: as part 1, and spot checks: a sampled feature merged without a wait, a risky one waited, and an overturn turned spot checks off. Not yet used on a real project. |
| A real project runs on part 1 | Used on a real project, for the waits, saying which of rulings and premise attempts happened there |
| Troy turns spot checks on in a real project | Used on a real project, spot checks included |

Each part's PR updates F18's status itself, since its tests, planted bugs, and trial run before it opens.

### 13.5 What part 1's build chose

Part 1's build fixed these points, which the sections above leave open. Its tests and trial check them.

- **The wait's line.** `Wait: W<n>` is the first line that is not blank under a `Waiting for Troy:` or `Escalation:` heading. A missing line, or an ID outside W1 to W11, reads as `unlisted`. `status --waiting` needs `--wait <ID>` and is refused otherwise (exit 1, problem `wait`). `status` gives the ID in `wait`, and `waiting_on_troy` starts with it: "W3, approve PR #41", or "W3, PR #7: Waiting for Troy: approve this PR".
- **`next`.** Four new keys: `premise`, true at exactly 3 attempts; `escalate`, the wait to escalate with, W7 from 4 attempts on or after a `not fixed` ruling, until an escalation is recorded; `ruling`, with the ruler, its task, and the newest result; and `overturn`. Three new actions: `ruling`, `ruled-revision`, and `overturn`.
- **The end of an overturn.** The engine cannot tell the PRs that carry an overturn out from the feature's other PRs, so troy-mode records the end with a second heading on the progress issue, `Overturn carried out: <link to the ruling>`, once they have merged.
- **Rulings of merged PRs.** The progress issue shows the rulings of the feature's merged PRs too. Reading every merged stage PR's comments at every sync would cost about half a second per PR, so a merged PR's rulings are read once per checkout and kept in the common git folder, `troy-mode/rulings.json`.
- **Report fields.** Role reports have no Notes field (F04 section 5.2), so the premise attempt's three lines open its Summary, and AR2's `Risky:` line ends its Summary. Part 1 adds the line; part 2 reads it.
- **The re-run.** `ci_failures` gains `rerun`, from the runs' `attempt` field, so a failure outside the authors' files is re-run only once, also across sessions.
- **Where AR8 and `--premise` apply.** AR8 is briefed at a feature's stages 2 to 5, and on test fixes, bug PRs, version tests PRs, and a rule's cleanup PRs. `brief --premise` takes the author tasks IF1, IF2, TM1, TM7, DV1 to DV5, TE1 to TE6, and AR1, and adds the card's absolute path in the plugin to Read first.
- **The environment in a premise attempt.** In the trial's first premise attempt, the Test Engineer found the cause, a wrong `MAMBA_ROOT_PREFIX`, and then set the variable on its own check commands instead of escalating. The premise text now says that a cause in the environment is outside the write scope even when the role's own commands could get around it, and the next premise attempt escalated (W7) with its evidence.
- **Templates.** No template changes, since a template change puts every exam case in play. The rules template's R17 row and two template comments still say that the loop escalates, until the next PR that changes the templates.

The checks of part 1:

- **Tests.** A separate agent wrote 104 tests from this design and the build's contract before the code, in seven new modules. 99 of them failed on the old engine, each for a missing part of the feature; the other 5 cover behavior that does not change. The agent also updated the existing tests whose expected output the contract changes. After the planted bugs, the build added 4 tests of a team's `premise` and `escalate`. The suites pass: flow 1,468, hooks 436, init 282, checks 751, dev 324, and exam 420.
- **Planted bugs.** 29 planted one at a time: 27 caught, and 2 equivalent, where the code refuses or drops the case by another path.
- **Trial.** On `ZJUCao/troy-mode-trial`, for $36.72 in 12 nested sessions: the requirement change adding F07 waited with `Wait: W1`; F07's design and test plan waited with `Wait: W3`; PM7 ruled the design loop's round 3 `merge`; Troy's overturn on the progress issue held F07 until a `[docs]` design update, reviewed by AR2, merged, and `Overturn carried out:` was posted; AR8 ruled the mock loop's round 3 `merge`, both findings `does not block`, so the ruled revision ran in the tests only; after F07's acceptance, a plain "continue" went on into v0.3's release steps; and the premise attempt escalated (W7) with its premise, check, and result. Every wait comment of the trial named a listed ID. A stop at W9 came from the trial's own Python environment, installed from an older clone.
- **Role exam.** Exam 2026-11-25-3 on the instruction hash `02dec4115317`: passed. The two Architect cases, the only ones the change affects, ran five times on each side: ar-design-review 0 of 5 before and after, and ar-error-review 1 of 5 before and 0 of 5 after, both "not worse" by the exam's rule. 20 runs cost $67.87 against the $59.78 estimate, in 9 h 51 min with two pauses at usage limits. Both cases fail most runs before the change too.

### 13.6 What part 2's build chose

Part 2's build fixed these points, which section 7 leaves open. Its tests and trial check them.

- **Where it lives.** A new engine module, `troyflow/spot.py`, outside F16's instruction set. No agent file, template, module of `brief.py`, or role section of the entry skill changed, so the role exam found no case affected.
- **The sample.** One feature in `spot_check_every`, counted from 1 after the first `troy_approves_first` features of the order; turning spot checks on sets `troy_approves_first` to the features accepted so far. `status` gives `spot` (`on`, `configured`, `every`, `approves_first`, `sample`, and `off_due`), each feature's `spot` (`sample` or `none`), and `spot` and `risky` on each PR 1 and PR 2 and on every `next`. The Product Manager now puts a new feature after every feature already accepted or under way, since both counts go by place in the order.
- **The marks.** Each mark says who marked the PR and why, with the PR that carries it. The engine marks a PR 1 whose design's section 3 lists a change ("None", alone or followed by an explanation, lists none), one with a ruling or a round 3 that waits for one, and one whose attempts reached 3; PR 2 takes PR 1's marks and adds its own ruling and premise marks. The Architect's mark is the `Risky:` line of its newest review that has one, which troy-mode posts in the review comment; `Risky: no` marks nothing. Troy's mark is a note for the feature whose text starts with `Risky:`. Attempts recorded before a PR opened are posted on it when it opens. A merged PR 1's comments are read once per checkout and kept in the common git folder, `troy-mode/spot.json`.
- **Turning off at once.** An `Overturn:` comment on any issue turns spot checks off when it is newer than `origin/main`'s newest `[rules] Set the features Troy approves` commit, so an older overturn does not count, and when its link names a PR 1 or PR 2, or no PR the engine finds. From then on every later PR 1 and PR 2 waits for Troy, before the `[rules]` PR lands: `next.action` `spot-off` asks for it, with `spot_checks = false` and `troy_approves_first` set to the number of features. After a feature's acceptance, troy-mode posts the same `Overturn:` on the idea that disagrees with a sample, which turns spot checks off without holding anything.
- **Approval records.** A PR 1 or PR 2 that merged before the newest `[rules] Set the features Troy approves` commit needs no `[docs] Record Troy's approval of ...`, nor does an accepted feature's: F07 merged those under the old count, as it merges samples. `spot-off` comes after such records, so a risky PR that Troy merged on GitHub keeps its record.
- **The evidence.** `spot_evidence` comes with `ask-approvals` or with `status --spot-evidence`. E1 reads the newest merged PR 1 and PR 2 that waited for Troy: the last 6 must show no review, attempt, or ruling after the wait; fewer than 6 is `unknown`. E2 reads the last version with an accepted feature: its acceptance and release PRs must hold no `requirement` line in TM8's rulings, which troy-mode now posts as a comment headed `Test Manager ruling, real run`. E3 reads `TROY_EXAM_ROOT/cases/<case>.tsv` for the plugin's own instruction hash: each of the five cases needs 4 passes in its newest 5 runs; without the folder it is `unknown`.
- **The checklist.** Only a project whose config ever turned spot checks on reads its samples, so other projects make no GitHub call for them. A sample is a merged PR 1 or PR 2 of the version with the spot check comment; it has a box, `**抽查 #<n> <title>**`, until Troy answers it with a comment on the PR or an overturn, and a box Troy ticked stays. `device_test.result` is `ticked` only with each of them ticked.
- **troy-check.** `[flow] spot_checks` must be true or false, and `spot_check_every` a whole number of 2 or more; an old `[flow]` table stays valid. A project needs troy-init's upgrade to 0.19.0 before its config holds them.

The checks of part 2:

- **Tests.** A separate agent wrote 114 tests from this design and the build's contract before the code, 105 in eight new flow modules and 9 for troy-check: on the part 1 engine, 110 failed, each for a missing part of the feature, and 4 passed by design. The build removed two more tests of the agent's that pinned part 1's instruction hash, which every later change of the instruction set would fail, and added 3 tests and one case for the trial's findings. The suites pass: flow 1,576, hooks 436, init 282, checks 760, dev 324, and exam 420.
- **Planted bugs.** 26 planted one at a time, among them the six of section 13.2: all 26 caught.
- **Trial.** On `ZJUCao/troy-mode-trial`, for $40.95 in 10 nested sessions. A requirement change added F08 and F09 to v0.3; the question after the first features then showed E1 (fails: a PR changed after its wait), E2 (holds), and E3 (fails: no runs on the plugin's instructions), and recommended going on approving; "Troy" turned spot checks on with every 2. F08's design waited for Troy, marked by the engine (a changed usage line) and the Architect (a new stored settings file), and its test plan took the design's marks. F09, the sample, waited too: the Architect marked it, because it extends that settings file. A third feature, F10, a library function in v0.4, became the sample with every 3: its design and test plan merged without a wait, each with the spot check comment, the report listed them under "Spot checks, after the merge", and its progress issue showed the sample line. "Troy" then disagreed with F10's design on the progress issue: troy-mode answered with `Overturn:` and turned spot checks off in a `[rules]` PR; carrying the overturn out needs a requirement change, which waits for Troy. The trial found three faults in the engine, each fixed with a test: approval records asked after spot checks went on and after they went off, and a section 3 of "None." with an explanation read as a change; and one in the Product Manager's instructions, which put new features before the accepted ones in the order. Troy's `Risky:` note and the checklist's boxes are checked by tests only.
- **Role exam.** Exam 2026-11-26-1: no case affected. Part 2 changes no file of the instruction set but SKILL.md's sections outside the role sections, so the exam ran nothing and cost $0.

## 14. Not in F18

- A hook that stops the main session from ending its turn while nothing waits (D171 option B). A later issue can add it if the retrospectives find unlisted stops.
- The evidence steps of section 7.3: the author cases' base runs and the Architect's hillclimb.
- The Product Manager's exam cases (F16 D151).
- Going on by itself after a usage limit resets. In recipe-menu since the pilot, 26.5 hours passed between the limit's reset and Troy's next message. troy-mode cannot act while its session is stopped; a later issue can look at a scheduled resume.
- Changes to tstack's own process.
- Turning spot checks on in any project.

## 15. Decisions for Troy

F16 design keeps D171 to D180 for F18. Troy approved every decision on 2026-11-25 with the recommendation ("全按推荐"), and the requirement text proposals P1 to P7 with them. The standing yes for small issues did not cover them, since F18 is a new feature.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D171 | Where does the list of waits live, and does anything check it beyond the instructions? | A: one section "Waits for Troy" in the Product Manager's instructions, with the IDs W1 to W11; the skill's stops name the ID; the engine knows the IDs, refuses a wait recorded without one, and `retro` lists every wait that has none (section 4.2). B: A, plus a Claude Code hook that refuses the main session's end of turn while the request's reach is not done and no listed wait is recorded; it needs a probe of the desktop app's Stop hook first. C: the list in the instructions only. | A, approved by Troy on 2026-11-25 ("全按推荐"). Requirements 5.8 prefers a check to an instruction, and A checks every wait troy-mode records at no model cost. B also catches a stop that records nothing, such as recipe-menu's five questions that no instruction asks for, but it would fight Troy's own questions in the session and the usage-limit stops, and it needs a probe first. A later issue can add it if the retrospectives find such stops again. |
| D172 | Which of today's stops stay, and which go away? | A: as sections 3 and 4.3 say: the waits W1 to W11 stay; a feature-loop request reaches the rest of the version, up to Troy's device test, unless Troy names where to stop; a question that no instruction asks for is decided and reported; a role's question goes to Troy only when a document must change; a CI failure outside the authors' files is re-run once; a change PR whose idea Troy closed is closed. B: keep every stop of today, only named and listed. C: A, but the reach stays as F07 D63 and D203 say: one feature or one stage, unless the request names a version. | A, approved by Troy on 2026-11-25 ("全按推荐"). The end of a request's reach was the largest stop that 3.3 and 5.7 do not list: 34 of recipe-menu's 100 stops and 67.9 of its 222 hours of waiting. Troy can still stop a request where Troy wants. Each other stop that goes away has a safe default that Troy can reverse: a choice reported in the PR, an answer from the approved documents, one re-run, or a PR that can be reopened. B leaves pstack's rule without its list. C keeps the 34 stops. |
| D173 | Who rules at round 3, and what does a ruling do? | A: the Architect (new task AR8), or the Product Manager (new task PM7) for the Architect's own review; each open finding is `fix` or `does not block` with a reason; the author fixes only the `fix` findings once, and the ruler checks them (sections 5.1 and 5.2). B: the ruler picks a side as a whole: merge as is, or one more revision and a fourth review round by the reviewer, then an escalation. C: the Product Manager rules on every loop. | A, approved by Troy on 2026-11-25 ("全按推荐"). Round 3's findings are often partly right, and ruling each one keeps the right ones. The Architect knows the architecture and the design that code and tests follow, so it rules best outside its own review. AR8 changes the Architect's agent file, so the exam costs $59.78, up to $119.55 (section 10); under B or C with AR5's Answer in place of AR8, $0. C puts code and test disputes into the main session's context. |
| D174 | How are a ruling and Troy's overturn recorded and carried out? | A: a comment `<Ruler> ruling, round 3: <result>`, a sentence in the PR's What, a line on the progress issue and in the report; Troy overturns on the progress issue or in chat until the feature's acceptance; F07 records `Overturn:`, holds the feature and its team, and carries it out through the stage's existing side flow (section 5.3). B: a `ruling` issue per ruling with its own label, which Troy closes or comments on. C: the PR comment only. | A, approved by Troy on 2026-11-25 ("全按推荐"). It uses what Troy already reads on the phone, the progress issue, and the flows troy-mode already has. B adds a fourth kind of issue and label, which changes F15's row. C hides rulings in merged PRs that `status` does not read. |
| D175 | What does the premise attempt do, and how is it counted? | A: after attempt 3, the author runs once more with a fixed text and the premise card: write the shared premise, test it with a check that changes no file, then fix or escalate; it counts as attempt 4, and its failure escalates with the evidence (section 6). B: the main session tests the premise itself, then gives the author a fourth attempt with what it found. C: the stage's reviewer tests the premise in a read-only run, then the author's fourth attempt. | A, approved by Troy on 2026-11-25 ("全按推荐"). The author has the failing checks and its own scope, one run costs least, and the evidence reaches Troy either way. B spends the main session's context, which cost $301 in the pilot. C adds a run, and a reviewer cannot try a fix. |
| D176 | Which PRs does Troy review under spot checks, and when? | A: one feature in three after the approved ones, by the order (`spot_check_every`, 3 by default); its PR 1 and PR 2 merge, Troy reviews after the merge, and the version's checklist gets a box for each unanswered sample; risky PRs wait before the merge (section 7.1). B: as A, but a sampled PR waits for Troy before its merge. C: a draw of one in three, seeded by the feature's ID, after the merge. D: no sample, only risky PRs. | A, approved by Troy on 2026-11-25 ("全按推荐"). A sample after the merge stops no team, the checklist makes sure Troy looks before the version ships, and an overturn of a sample turns spot checks off. B is safer per PR, but each sample stops its team, as today's approvals did for 48 hours in the pilot. C gives no gain over A, since no role knows the sample. D tells Troy nothing about the PRs that are not risky. |
| D177 | What marks a PR as risky, and who marks it? | A: the engine (a changed interface of an accepted feature, a ruling, a premise attempt), the Architect in AR2's report with a reason from a fixed list, and Troy at any time; PR 2 takes PR 1's mark (section 7.2). B: the engine and Troy only. C: the Architect only. | A, approved by Troy on 2026-11-25 ("全按推荐"). The engine sees what the state shows, the Architect sees what the design means, and Troy can always ask. Since AR8 changes the Architect's agent file anyway (D173 A), the line costs no exam of its own. B misses a design that changes what Troy keeps or sees, which only a reader notices. |
| D178 | What evidence is enough, and does it exist now? | A: all of E1 (Troy's last 6 approvals of PR 1 and PR 2 changed nothing), E2 (no real-run mismatch from a design or test plan in the last version), and E3 (the IF1, AR2, and TM1 cases at 4 of 5 on the current instructions), shown to Troy at each question (section 7.3). Not now: the earliest is after the author cases' base runs, about $51, an Architect hillclimb, and recipe-menu's v0.2. B: E1 and E2 only. C: no bar; troy-mode shows the evidence and Troy decides. | A, approved by Troy on 2026-11-25 ("全按推荐"). With spot checks, the Architect's review is what stands between a design and the code, and today it passes 2 of 20 runs of the pilot's design faults, approving a design that breaks the error rules in 7 of 10. Troy's 32 unchanged approvals (E1) show that Troy's review changed nothing in recipe-menu, not that the reviews below it would catch what Troy would have caught; E3 measures that. B would turn spot checks on today with that gap. C leaves the requirement's "enough evidence" undefined. Troy can still turn spot checks on at any time under A. |
| D179 | How does Troy turn spot checks on and off, and how do they work with feature teams and merges? | A: `[flow] spot_checks` and `spot_check_every` in the project's config, set by a `[rules]` PR on Troy's word in chat or on an issue, offered as a third answer to D62's question; any overturn of a sample or of a ruling on PR 1 or PR 2 turns them off; a risky wait stops only its team, a sample none; merges as for PR 3 to PR 6, with no GitHub auto-merge (sections 7.4 and 7.5). B: as A, without the overturn turning them off. C: set per version, in the version plan, instead of per project. | A, approved by Troy on 2026-11-25 ("全按推荐"). The setting lives where D62's does, every session reads it, and only Troy turns it on. Turning off on an overturn only adds waits, and it stops a run of unreviewed PRs once Troy has found one wrong. C asks again at every version for a choice that rarely changes. |
| D180 | How does F18 land and get checked? | A: two PRs: part 1, the waits, rulings, premise attempt, and every instruction-set change, with the exam of section 10 ($59.78, up to $119.55); part 2, spot checks, with no case affected. Tests by a separate agent, planted bugs, and a trial of each part on `ZJUCao/troy-mode-trial`, about $35 and $40 (section 13). B: one PR. C: three PRs: the waits; rulings and the premise attempt; spot checks. | A, approved by Troy on 2026-11-25 ("全按推荐"). Part 1 is useful on its own, and spot checks are off until the evidence exists anyway. Putting every instruction-set change in part 1 means one exam, not two. C adds a PR without saving an exam. The build's costs, about $135 for the exam's first round and both trials, up to about $195, are above the $60 line and need Troy's yes, which Troy gives apart from this approval. |

## 16. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-25 | First draft, with D171 to D180 and the requirement text proposals P1 to P7, for Troy. |
| 1.0 | 2026-11-25 | Approved by Troy with D171 to D180, every recommended answer ("全按推荐"), and the requirement text proposals P1 to P7 as written. Requirements 1.64 records them with P1, P2, P5, and P7. The build's costs still wait for Troy's yes (sections 10, 12, and 15). |
| 1.1 | 2026-11-25 | Part 1's build (plugin 0.18.0): section 13.5 records what it chose, its tests, planted bugs, trial, and role exam; the premise text says, from the trial, that a cause in the environment escalates. |
| 1.2 | 2026-11-26 | Part 2's build (plugin 0.19.0): section 13.6 records what it chose, its tests, planted bugs, trial, and role exam; from the trial, approval records skip PRs merged before the count changed, a section 3 of "None." with an explanation lists no change, and new features go after the accepted ones in the order. |
| 1.3 | 2026-11-27 | Section 7.3 notes the result of step 2, the Architect's hillclimb, which F17's PR 2 ran (plugin 0.20.1). |
