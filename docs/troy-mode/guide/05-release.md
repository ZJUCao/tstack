# 5. Release a version

| | |
| --- | --- |
| Version | 0.2 |
| Date | 2026-11-16 |
| Source of truth | This English file. [`05-release.zh-CN.md`](05-release.zh-CN.md) is the Chinese mirror. |

A version groups consecutive features of the order and is usable on its own. Its test plan is written before its first feature starts. At release, troy-mode runs the version's tests on your PC, then asks you to test it on your own devices. You accept it, and troy-mode tags it ([F08 design](../design/F08-release.md)).

## 5.1 The version test plan

Before the first stage of a version's first feature, troy-mode has the Test Manager write the version's test plan, `docs/versions/v0.1/test-plan.md` and its mirror ([F08 design D70](../design/F08-release.md#13-decisions-for-troy)). Each scenario says who runs it:

- **troy-mode**, as a version test, on your PC at release;
- **you**, on a device only you have, such as your phone.

troy-mode opens `[docs] Add the v0.1 test plan` on `troy-mode/v0.1-test-plan`, checks it as the Product Manager, and merges it. It is not one of your approvals. When a version's features change later, `[docs] Update the v0.1 test plan` follows. You need not ask for any of this: it happens on the way to the feature.

## 5.2 The request

After the version's last feature is accepted, type:

```text
/tstack:troy-mode release v0.1
```

"release" alone means the version that troy-mode names as due. A release request never builds features. If a feature of the version is not accepted, troy-mode tells you which and stops: ask for the features first, such as "the rest of v0.1", then for the release ([F07 design D63](../design/F07-entry-skill.md#16-decisions-for-troy)).

## 5.3 The steps

| Step | What happens | PR | You |
| --- | --- | --- | --- |
| 1. Ready | Open PRs merge first. Open bugs are fixed first, unless you defer them. | None | Defer a bug, if you want |
| 2. Version tests | The Test Engineer writes one test per scenario troy-mode runs, in `version-tests/` | `[v0.1 tests] End-to-end and stress tests` | |
| 3. Release PR | The Product Manager adds the version's section to `CHANGELOG.md` and its mirror | `[docs] Release v0.1.0` on `troy-mode/release-v0.1.0` | |
| 4. Release test | The regression tests and the version tests run on your PC, then `real-run --all` runs the prototypes of every accepted feature the way you type them. A mismatch fails the release test. The report goes on the release PR. | None | |
| 5. Your test | You run your scenarios on your devices and reply | None | Test and reply |
| 6. Acceptance | Each feature's status becomes "Usable on Troy's devices", and the release PR merges | The release PR | |
| 7. Tag | A GitHub release `v0.1.0` on the release PR's merge commit, with the changelog section as its notes | None | |
| 8. Retrospective | Problems that repeated during the version, and rules that would prevent them | None | Pick rules, if you want |

From the release PR on, every step comments on it, so a new session finds the release where it stopped. The version tests PR merges even when some version tests fail: CI does not run them, and a failing scenario is a finding of the release test. Performance and stress tests run in step 4 too ([F08 design section 5.5](../design/F08-release.md#55-the-release-test)).

## 5.4 Your test on your devices

After a release test that passed, troy-mode posts `Waiting for Troy: accept v0.1.0` on the release PR and tells you, in your language:

- the commit to test, and the release PR's link with the changelog;
- the scenarios troy-mode ran, with their results;
- each scenario you run: its device, its steps, and the expected result.

Then it stops. This is the trial's release PR [#27](https://github.com/ZJUCao/troy-mode-trial/pull/27), shortened:

```text
Release test, run 1: passed

Commit tested: 73fc746e6749e63617a22a9acf5fc217e3f521f5
Regression: ruff, ruff format, mypy pass; pytest 48 passed, 1 skipped; ...
Automated scenarios (version tests on Troy's PC, Windows 11, Python 3.13):
- v0.1-S01 Count the words of a file, as in the F01 prototype.: passed
- ...
- v0.1-S07 ... gets the same count for the same words whatever the line endings.: passed

Waiting for Troy: accept v0.1.0

The v0.1 test plan has no scenario that Troy runs by hand. Reply "accepted", with any
notes, or name what failed or what is not what Troy wanted.
```

Reply in chat or in a comment on the release PR. There are three kinds of reply ([F08 design section 5.6](../design/F08-release.md#56-troys-test)):

| You reply | What happens next |
| --- | --- |
| Accepted, with any notes, for example "Accepted, no notes." | Acceptance, the tag, and the retrospective (steps 6 to 8). |
| A scenario failed, for example "v0.1-S03 failed on my phone: it shows an empty list." Say which scenario, on which device, and what you saw. | troy-mode records it, and the Test Manager triages it. A bug gets its issue and its two PRs ([section 4.1](04-bugs-and-changes.md#41-fix-a-bug)). A wrong version test is fixed. A misunderstood requirement becomes a requirement change. Then the changelog lists the fixes, the release test runs again as run 2, and you test again only the scenarios that failed, unless you ask for more. |
| Not accepted, for a reason that is not a bug, such as a feature that is not what you wanted | The requirement change flow ([section 4.2](04-bugs-and-changes.md#42-change-a-requirement)). The release waits until the changed features are accepted again. |

troy-mode records each reply on the release PR as `Release test by Troy, run <n>: accepted`, `failed`, or `not accepted`, followed by your words. In the trial: `Release test by Troy, run 1: accepted`.

## 5.5 Open bugs

An open issue labeled `bug` stops the release until it is fixed or you defer it. To defer one, say so in chat, for example "defer #21 to v0.2". troy-mode records it on the release PR as `Bug deferred by Troy: #21`, followed by your words.

## 5.6 Acceptance and the tag

On your acceptance, the Product Manager sets every feature of the version to "Usable on Troy's devices" in both languages, and troy-mode records your acceptance in the version test plan. Then it merges the release PR and creates the GitHub release on the merge commit. Nothing is pushed from your PC: GitHub creates the tag. Creating the release is one of troy-mode's rights, only after your acceptance ([section 7.2](07-taking-part.md#72-what-troy-mode-does-alone)).

If you merge the release PR on GitHub yourself, troy-mode records your acceptance in a `[docs] Record Troy's acceptance of v0.1.0` PR, then creates the release.

## 5.7 Patch releases

```text
/tstack:troy-mode release v0.1.1
```

A patch releases the bug fixes merged since v0.1.0. It has no version test plan of its own and no new version tests, but the release test runs every version test again, and you test the scenarios the fixed bugs touched. The changelog section lists only Fixed, and the features keep their statuses. A patch has no retrospective.

A patch is possible only while no code of a later version's feature has merged since the tag. Otherwise troy-mode says that the fixes ship with the next version, and stops ([F08 design D75](../design/F08-release.md#13-decisions-for-troy)).

## 5.8 The retrospective

After the tag, troy-mode groups the evidence of the version's PRs: review findings by rule, failed attempts, escalations, bugs, and hook log lines. The hook log keeps only the last day's lines, so blocks from earlier in the version do not reach it ([issue #66](https://github.com/ZJUCao/troy-pstack/issues/66)). For each problem seen in two or more PRs, it proposes a rule, with the strongest enforcement that works, following pstack's `correct` skill. It sends you one message with the problems, their PR links, and its recommendations, and posts the same report on the release PR as `Retrospective: v0.1.0`, which ends the release.

Each rule you pick then goes through the rule change flow, one at a time ([section 6](06-rules.md)). From the trial's release PR [#27](https://github.com/ZJUCao/troy-mode-trial/pull/27), shortened:

```text
Retrospective: v0.1.0

troy_flow.py retro found no group seen in two or more PRs. In total: 3 reviews requested
changes, 1 failed attempt, no escalation, 1 bug fixed (B13), no hooks.log lines.
One theme spans two PRs under different keys:
1. Test inputs whose characters differ from the test plan or cannot be seen.
   - Proposal: a lint, not a doc rule. ... Recommendation: worth adding if it shows
     up again; two cases in one version are a weak signal.
Troy's decision: "No rule this time." No rule goes to the rule change flow.
```
