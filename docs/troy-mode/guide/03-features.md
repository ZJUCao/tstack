# 3. Build features

| | |
| --- | --- |
| Version | 0.1 |
| Date | 2026-11-09 |
| Source of truth | This English file. [`03-features.zh-CN.md`](03-features.zh-CN.md) is the Chinese mirror. |

troy-mode builds features one at a time, in the topological order of the requirements. Each feature takes six PRs, merged in order, each with one commit that holds one stage's output ([requirements section 5.2](../requirements.md#52-feature-loop)). You approve the first two PRs of the first features. troy-mode merges everything else.

## 3.1 The requests

| You type | troy-mode builds |
| --- | --- |
| `/troy-pstack:troy-mode next feature` | The next feature in the order |
| `/troy-pstack:troy-mode F04` | Feature F04 |
| `/troy-pstack:troy-mode F04 to F06` | F04, F05, and F06, in order |
| `/troy-pstack:troy-mode the rest of v0.1` | Every feature of v0.1 not yet accepted |

A request reaches one feature unless it names more, as the last two do. Then troy-mode reports and stops ([F07 design D63](../design/F07-entry-skill.md#16-decisions-for-troy)). Within that reach it goes from stage to stage by itself, and stops only where it needs you: an approval of yours, or an escalation.

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
| 6 | `[F04 6/6 accept] <name>` | The feature's status, "Passes tests on main", in both languages | Product Manager | None | troy-mode |

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

PR 6 sets the feature's status to "Passes tests on main". The feature has not been checked on your devices yet: that happens when you test its version ([section 5](05-release.md)).

## 3.4 After the first features

You approve PR 1 and PR 2 of the first 3 features in the order (requirements Q2, R18). The number is `troy_approves_first` in the `[flow]` table of `.troy-mode/config.toml`, 3 by default.

To approve, reply in chat or merge the PR on GitHub, as for the requirements ([section 2.3](02-start.md#23-the-requirements)). After a reply in chat, troy-mode records your approval in the document's header and change log, then merges. To ask for changes, say what to change: the author revises, and the PR waits for you again.

When the last of those features is accepted, troy-mode asks you once whether to go on approving PR 1 and PR 2 of later features, and for how many ([F07 design D62](../design/F07-entry-skill.md#16-decisions-for-troy)):

| You answer | What happens |
| --- | --- |
| No | `troy_approves_first` stays at the features already done. troy-mode merges every later design and test plan itself, once the Architect approved the design and the test plan's questions are settled. |
| Yes, for N more features | `troy_approves_first` rises by N. You approve PR 1 and PR 2 of the next N features, and after the last of them troy-mode asks again. |

troy-mode records your answer in `.troy-mode/config.toml`, with a comment line that names the decision and its date, in a `[rules] Set the features Troy approves` PR, and merges it. Apart from troy-init's steps and the rule change flow, this is the only config change troy-mode makes.

## 3.5 Reviews, rounds, and attempts

- **Rounds (R17).** A round is one run of the stage's reviewers. A review that asks for changes sends the findings back to the author, and the next round starts. After 3 rounds without approval, troy-mode escalates to you. On PR 4, a change request from either reviewer fails the round.
- **Attempts (D64).** An attempt is an author's run that fails, whose local checks fail, or whose CI fails in the author's files. Each stage allows 3. After the third, troy-mode escalates ([F07 design section 8.5](../design/F07-entry-skill.md#85-attempts-d64)).
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
