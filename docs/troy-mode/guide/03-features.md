# 3. Build features

| | |
| --- | --- |
| Version | 0.5 |
| Date | 2026-11-26 |
| Source of truth | This English file. [`03-features.zh-CN.md`](03-features.zh-CN.md) is the Chinese mirror. |

troy-mode builds features one at a time, in the topological order of the requirements. Each feature takes six PRs, merged in order, each with one commit that holds one stage's output ([requirements section 5.2](../requirements.md#52-feature-loop)). You approve the first two PRs of the first features. troy-mode merges everything else.

## 3.1 The requests

| You type | troy-mode builds |
| --- | --- |
| `/tstack:troy-mode next feature` | The next feature in the order |
| `/tstack:troy-mode F04` | Feature F04 |
| `/tstack:troy-mode F04 to F06` | F04, F05, and F06, in order |
| `/tstack:troy-mode Start v0.1` or `/tstack:troy-mode the rest of v0.1` | Every feature of v0.1 not yet accepted, in order |

A feature-loop request, such as "next feature", "F04", or "continue", reaches every feature of the current version not yet accepted, and then the release's steps up to your test on your devices ([F18 design D172](../design/F18-fewer-stops.md)). To stop earlier, say where, such as "only F04" or "stop after the mock". You can also ask for a release on its own, with `release v0.1`. Within that reach troy-mode goes from stage to stage and from feature to feature by itself, and stops only where it needs you: one of the waits of [section 7.1](07-taking-part.md#71-the-steps-that-wait-for-you), an approval of yours or an escalation. After your answer it goes on. Before F18, a request that named one feature or one stage ended there ([F07 design D63 and D203](../design/F07-entry-skill.md#16-decisions-for-troy)). In the pilot, before D203, "Start v0.1" reached only F01, and each later feature needed its own request, such as "Start F02" or "开始做F09" ([issue #52](https://github.com/ZJUCao/tstack/issues/52)).

What a feature takes: in the pilot, each of the 13 features of `ZJUCao/recipe-menu` took 3 to 16 hours from its design PR to its acceptance, while you approved its design and test plan. Each took 14 to 24 role runs and $45 to $103 at the API's list prices, most of it in the roles that run on opus and in the main session.

troy-mode works on one PR at a time. A new request waits until the open PR merges, unless you say to pause it.

## 3.2 The six PRs

`<name>` is the feature's short name from the requirements. The branches are `troy-mode/f04-1-design` to `troy-mode/f04-6-accept`.

| PR | Title | What it holds | Written by | Reviewed by | Merged by |
| --- | --- | --- | --- | --- | --- |
| 1 | `[F04 1/6 design] <name>` | The interface design, in English and Chinese: each external interface's name, purpose, parameters, return value, errors, and a performance target when the requirements set one. The description opens with a summary for you. | Interface Designer | Architect, against its checklist | troy-mode, after your approval for the first features |
| 2 | `[F04 2/6 test-plan] <name>` | The test plan, in English and Chinese: unit, functional, integration, and performance cases. The description opens with a summary for you. | Test Manager, with the Interface Designer's answers | Agreed with the Interface Designer, at most 3 rounds of questions | As PR 1 |
| 3 | `[F04 3/6 mock] <name>` | Signatures and full doc comments, no bodies | Developer | Code Reviewer | troy-mode |
| 4 | `[F04 4/6 tests] <name>` | The tests. Every new test fails against the mock (R09). | Test Engineer | Test Manager and Code Reviewer, together | troy-mode |
| 5 | `[F04 5/6 impl] <name>` | The implementation. Every test passes, and coverage meets R11. | Developer | Code Reviewer | troy-mode |
| 6 | `[F04 6/6 accept] <name>` | The real run of the prototypes, and the feature's status in both languages: "Ran for real on Troy's PC" or "Passes tests on main". It holds the run files; its description holds the real output, compared with the prototypes. | Product Manager | None. The Test Manager rules on each mismatch. | troy-mode |

Before each push, troy-mode runs the local checks: `troy-check pr` on every PR, and for PRs 3 to 5 also the language pack's steps and `troy-check code`. CI runs the same checks on GitHub. troy-mode merges only when every review of the stage approved, the local checks passed, and every CI check passed ([F07 design section 8.6](../design/F07-entry-skill.md#86-merging-r18-f02-d14)).

## 3.3 What you see

troy-mode reports each stage in your language. When a PR waits for you, it also says so on the PR. This is the trial's PR [#7](https://github.com/ZJUCao/troy-mode-trial/pull/7), the design of F01, shortened:

```text
Architect review, round 1: approved

All six checklist items pass; section 4 of the design and its mirror holds the review.
Findings: None.

Waiting for Troy: approve this PR

F01 is one of the first 3 features whose design Troy approves (D61). The Architect approved
the design in round 1, troy-check pr passes locally on a4eb7a1, and both CI checks pass.
Approve in chat, ask for changes, or merge on GitHub.
```

Since F14, the description of PR 1 and PR 2 opens with a one-page summary for you, in Chinese and then English: what changes for you as a user, each point you decide with a recommendation, and the risks. For a test plan, it says what the tests check of what you will see, what they leave out, and anything you run by hand. The comment `Waiting for Troy: approve this PR` then has one line under it, "What to decide is in the summary at the top of the description.", and troy-mode sends you the summary in chat. The [F14 design](../design/F14-summary.md#35-an-example) shows the summary of a real design, and [section 7.1](07-taking-part.md#71-the-steps-that-wait-for-you) says how to answer it.

After a step, troy-mode also tells you what comes next and whether it needs you. The first session of the F09 trial ended:

```text
I did nothing else. The next step is [F02 2/6 test-plan] Count lines. Its PR also needs
your approval, because F02 is among the first 3 features you approve.
```

Since F12, PR 6 first runs the real program the way you type it. `troy_flow.py real-run` replays every `PS> ` command of the prototypes of the feature and of every accepted feature, in a scratch home folder, and compares the output with the prototype character for character, the spaces that line up Chinese columns included. A run file next to each prototype, `docs/prototypes/<name>.run.toml`, says how each section's data folder starts. The Test Manager rules on each mismatch: a bug goes to the bug flow before acceptance, and a prototype changes only where a design you approved chose the new output ([F12 design](../design/F12-real-run.md)). The description gets a "Real run" section with the commit, the counts, a row per command, and the real output, and troy-mode reports, for example:

```text
[6/6] Real run: 41 commands of 6 prototypes match on your PC. 3 wait for F12.
      Acceptance PR #96 merged. F11 status is now "Ran for real on Troy's PC".
      F11 cost $103.20 at list prices: 18 role runs, 5 helper agents, and the main session ($25.32).
      Not yet checked in Windows Terminal itself or on your devices.
```

PR 6 sets the feature's status to "Ran for real on Troy's PC" when all its own commands ran on your PC and matched, apart from those that wait for a later feature, and otherwise to "Passes tests on main", with the reason in the PR. The run goes through pipes, not a console, so it does not show how Windows Terminal draws the text. The feature has not been checked on your devices yet: that happens when you test its version ([section 5](05-release.md)).

PR 6 also has a "Cost" section: the feature's role runs per role, with the model, the helper agents, and the main session, and their cost at the API's list prices, read from the session transcripts on your PC. It counts this PC only, names any stage whose runs it did not find here, and gives the date of the price table it used ([F07 design section 8.8](../design/F07-entry-skill.md#88-role-runs-and-cost-d264-to-d267)).

Since F15, each feature also has a **progress issue** on GitHub, labeled `progress`, from the moment it is the next feature or has a stage PR until its acceptance. Its title holds the feature's ID and name, and its body shows the six stages as boxes, ticked as each PR merges, what waits for you, and links to the documents, first in Chinese, with the English folded below. Each stage PR starts its Why with `Progress: #<n>`, so GitHub lists it in the issue, and PR 6's `Closes #<n>` closes it. troy-mode keeps the text: an edit of yours is put back at the next run, and to say something to troy-mode you write a comment ([section 7.6](07-taking-part.md#76-from-your-phone), [F15 design section 4](../design/F15-issues.md#4-the-progress-issue-d142)).

## 3.4 After the first features

You approve PR 1 and PR 2 of the first 3 features in the order (requirements Q2, R18). The number is `troy_approves_first` in the `[flow]` table of `.troy-mode/config.toml`, 3 by default.

To approve, reply in chat or merge the PR on GitHub, as for the requirements ([section 2.3](02-start.md#23-the-requirements)). After a reply in chat, troy-mode records your approval in the document's header and change log, then merges. To ask for changes, say what to change: the author revises, and the PR waits for you again.

When the last of those features is accepted, troy-mode asks you once whether to go on approving PR 1 and PR 2 of later features, and for how many ([F07 design D62](../design/F07-entry-skill.md#16-decisions-for-troy)):

| You answer | What happens |
| --- | --- |
| No | `troy_approves_first` stays at the features already done. troy-mode merges every later design and test plan itself, once the Architect approved the design and the test plan's questions are settled. |
| Yes, for N more features | `troy_approves_first` rises by N. You approve PR 1 and PR 2 of the next N features, and after the last of them troy-mode asks again. |
| Spot checks | troy-mode merges later designs and test plans too, and you review one feature in three after the merge and before the version ships; a PR marked risky still waits for you. |

The question shows three kinds of evidence for spot checks, E1 to E3: your last 6 approvals of a design or test plan changed nothing, no real-run mismatch of the last version came from a design or test plan, and the role exam's cases of the Architect, the Interface Designer, and the Test Manager pass 4 of 5 runs. troy-mode recommends spot checks only when all three hold ([F18 design section 7](../design/F18-fewer-stops.md)).

**Spot checks.** With them on, troy-mode samples one feature in three (`spot_check_every` in `[flow]`) after the features you approved, by the order. After a sampled feature's design or test plan merges, troy-mode posts `Spot check for Troy: review after the merge` on it and sends you its summary. Doing nothing agrees; to disagree, comment on the feature's progress issue, which works like overturning a ruling ([section 7.1](07-taking-part.md#71-the-steps-that-wait-for-you)). Before a version ships, its checklist has a box for each sample you have not answered. A design or test plan waits for you before its merge when it is risky: the Architect marks it in its review (a stored format or a file you keep changes, your files are deleted or moved, behavior you will see that the prototypes do not show, or network access, a subprocess, or credentials), troy-mode marks it after a ruling, a premise attempt, or a change to an existing interface, or you mark it yourself: "F12 is risky" in chat, or a comment "risky" on its progress issue. You turn spot checks on or off at any time, in chat or on any progress issue; any overturn of a sample turns them off, and every later design and test plan waits for you again.

troy-mode records your answer in `.troy-mode/config.toml`, with a comment line that names the decision and its date, in a `[rules] Set the features Troy approves` PR, and merges it. Apart from troy-init's steps and the rule change flow, this is the only config change troy-mode makes.

## 3.5 Reviews, rounds, and attempts

- **Rounds (R17).** A round is one run of the stage's reviewers. A review that asks for changes sends the findings back to the author, and the next round starts. After 3 rounds without approval, a ruling decides, not you: the Architect, or the Product Manager when the loop is the Architect's own review, rules on each open finding and writes the reason in the PR, and you can overturn the ruling until the feature's acceptance ([section 7.1](07-taking-part.md#71-the-steps-that-wait-for-you)). On PR 4, a change request from either reviewer fails the round.
- **Attempts (D64).** An attempt is an author's run that fails, whose local checks fail, or whose CI fails in the author's files. Each stage allows 3. After the third, the author runs once more and first tests what the three attempts assumed; only when that fourth attempt fails too does troy-mode escalate, with what the test showed ([F07 design section 8.5](../design/F07-entry-skill.md#85-attempts-d64), [F18 design section 6](../design/F18-fewer-stops.md)). troy-mode counts a CI failure even when nobody posted a comment for it: each pushed commit that failed a check in CI counts once, and a failure in the checkout or the setup counts nothing. When it finds a failure without a comment, it posts the comment, with a `Commit:` line that names the commit.
- **Comments.** Every review and failed attempt is a PR comment with a heading such as `Test Manager review, round 1: changes-requested` or `Developer attempt 2: failed`. Every role acts through your GitHub account, so a comment without one of troy-mode's headings counts as yours ([reference: comment headings](08-reference.md#83-comment-headings)). troy-mode passes your comments on a PR to its author.

In the trial's PR [#10](https://github.com/ZJUCao/troy-mode-trial/pull/10), F01's tests, both reviewers asked for changes in round 1 because one test's input differed from the plan, and both approved in round 2.

## 3.6 Side PRs

Some problems need a small PR of their own in the middle of a stage. troy-mode opens it, merges it, then goes back to the stage. You are asked only where a decision is yours.

| Problem | What troy-mode does | PRs |
| --- | --- | --- |
| The Developer says a test is wrong | The Test Manager rules. Wrong code: the Developer tries again. Wrong test: the Test Engineer fixes only that test. | `[F04 test-fix] <summary>` |
| Coverage below R11 | The Test Manager decides what the uncovered code is: code nothing needs is deleted, a case the test plan missed is added and tested, behavior not in the design goes to the Interface Designer, and untestable code is excluded with a reason the Test Manager approves. | `[docs] Add cases to the F04 test plan`, then `[F04 test-fix] <summary>` |
| A new third-party dependency (R16) | The Architect reviews it and escalates to you with a recommendation. You accept or refuse. | On yes: `[docs] Accept the dependency <name>`, with an ADR |

Tests are added only from the design, never by aiming at uncovered lines ([requirements section 5.2](../requirements.md#52-feature-loop)).

## 3.7 Performance tests

Only interfaces with a performance target in the requirements get performance tests (R14). The Interface Designer copies the target into the design, and the Test Manager plans the cases. They run after the implementation, because a mock always returns at once: PR 5's local checks run them on your PC ([F07 design section 8.1](../design/F07-entry-skill.md#81-stages)), not in CI, whose runners are too noisy (requirements Q7). Stress tests need the whole system, so they run only at the version's release ([section 5](05-release.md)).
