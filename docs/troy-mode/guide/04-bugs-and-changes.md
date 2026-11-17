# 4. Bugs and changes

| | |
| --- | --- |
| Version | 0.1 |
| Date | 2026-11-09 |
| Source of truth | This English file. [`04-bugs-and-changes.zh-CN.md`](04-bugs-and-changes.zh-CN.md) is the Chinese mirror. |

A bug gets a test that reproduces it, then a fix. A requirement change goes through the requirements first, then back through the feature loop. A question or an experiment opens no PR at all.

## 4.1 Fix a bug

Describe the bug, or name its GitHub issue:

```text
/tstack:troy-mode bug: count_words("") raises PermissionError instead of FileNotFoundError
/tstack:troy-mode fix #12
```

For a description, troy-mode opens a GitHub issue labeled `bug`. The issue's number gives the bug's ID: issue 12 is `B12`. Then ([requirements section 5.3](../requirements.md#53-bug-fix)):

1. **Triage.** The Test Manager reads the report. If the "bug" is a requirement that was misunderstood, troy-mode tells you, with a recommendation, and it becomes a requirement change (section 4.2).
2. **PR A**, `[B12 A/B test] <summary>` on `troy-mode/b12-test`. The Test Engineer adds a test that reproduces the bug. Its name starts with `test_b12_`, and it fails on the current code. The Test Manager and the Code Reviewer review it.
3. **PR B**, `[B12 B/B fix] <summary>` on `troy-mode/b12-fix`. The Developer fixes the bug, and the new test passes. The description says `Fixes #12`, so GitHub closes the issue when the PR merges. The Code Reviewer reviews it.

troy-mode merges both PRs. The test stays as a regression test (R15). A disputed test or a new dependency during a bug runs as in a feature ([section 3.6](03-features.md#36-side-prs)).

In the trial, bug B13 is issue [#13](https://github.com/ZJUCao/troy-mode-trial/issues/13). PR A, [#14](https://github.com/ZJUCao/troy-mode-trial/pull/14), got this review, shortened:

```text
Test Manager review, round 1: approved

The B13 reproduction test meets every point of the triage: its name starts with test_b13_;
it expects FileNotFoundError from count_words("") on Windows and Linux alike; it has no
skip or xfail marker, so it stays after the fix (R15).
It fails on the current code for the reported reason (PermissionError: [Errno 13]
Permission denied: '.'); R09 passes.
```

PR B is [#15](https://github.com/ZJUCao/troy-mode-trial/pull/15).

## 4.2 Change a requirement

Say what should change:

```text
/tstack:troy-mode change: a word needs at least one letter or digit
```

You can also write the change on GitHub, from your phone: open an issue from the template "Idea / 想法", or any issue with no label, in any language. troy-mode reads it at its next run, at the next natural stop, never between two stages of a feature: it comments what the idea is, under a heading such as `Idea: requirement change`, and goes on with the flow below; the change PR says `Closes #<n>`, so its merge closes the idea. An idea can also be a bug, a rule, a question that troy-mode answers and closes, or something for later. To have it taken at once, say `/tstack:troy-mode idea #<n>` ([section 7.6](07-taking-part.md#76-from-your-phone), [F15 design section 5](../design/F15-issues.md#5-idea-issues-d143)).

1. **The requirements.** The Product Manager updates `docs/requirements.md` and its mirror on `troy-mode/change-<slug>`, and opens `[docs] Change the requirements: <summary>`. You approve it, as you approved the requirements ([section 2.3](02-start.md#23-the-requirements)). Nothing else changes before you do.
2. **The affected features.** For each one, the Architect decides which interfaces, tests, and parts of the architecture change. An architecture change is escalated to you with its ADR as the recommendation.
3. **A feature not yet accepted** gets the status `Needs rework (<the change>)` and goes back to the earliest stage the Architect names. If the feature's open PR is at that stage or a later one, troy-mode closes it unmerged, then runs the stage again.
4. **An accepted feature** keeps its status. The change becomes a new feature, with the next free ID, a hard dependency on the old one, and the status `Not started` ([F07 design D65](../design/F07-entry-skill.md#16-decisions-for-troy)). It goes through the feature loop like any feature.

In the trial, `[docs] Change the requirements: a word needs a letter or digit` ([#16](https://github.com/ZJUCao/troy-mode-trial/pull/16)) added F03 "Words need a letter or digit" for the accepted F01. F03's design ([#17](https://github.com/ZJUCao/troy-mode-trial/pull/17)) and test plan ([#18](https://github.com/ZJUCao/troy-mode-trial/pull/18)) followed, and its mock was skipped.

### What happens to the old tests

When an accepted feature changes, some of its tests become wrong. The new feature's PRs handle them:

- **Design (PR 1).** It lists the interfaces that change. If it adds no new interface, PR 3, the mock, is skipped, and the loop goes from PR 2 to PR 4.
- **Test plan (PR 2).** The Test Manager names the old cases the change retires, and moves them to the "Not tested" section of the old feature's test plan with the reason, in both languages, in the same PR.
- **Tests (PR 4).** The Test Engineer deletes the retired tests and adds the new cases. The new tests fail against the current code (R09).
- Every other test keeps running as a regression test.

## 4.3 Questions and experiments

Questions and investigations open no PR:

```text
/tstack:troy-mode why does count_words read the whole file at once?
/tstack:troy-mode how does the release test find the version tests?
/tstack:troy-mode try a streaming version of count_words
```

troy-mode answers here, following pstack's `how` or `why` skill when it fits, and starts no role. An experiment runs on a throwaway branch `troy-mode/try-<slug>` made from `origin/main`, or in a scratch folder. It is never pushed and never becomes a PR. Code worth keeping goes through a requirement change and the feature loop ([requirements section 5.9](../requirements.md#59-work-outside-the-pipeline)).
