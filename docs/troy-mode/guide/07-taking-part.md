# 7. Where you take part

| | |
| --- | --- |
| Version | 0.2 |
| Date | 2026-11-16 |
| Source of truth | This English file. [`07-taking-part.zh-CN.md`](07-taking-part.zh-CN.md) is the Chinese mirror. |

troy-mode is built so that you appear only for decisions. This page lists the steps that wait for you, what troy-mode does alone, what the status labels mean, and how to pick up work in a new session.

## 7.1 The steps that wait for you

Only these steps wait for your approval ([requirements section 3.3](../requirements.md#33-where-troy-takes-part)):

1. Each project's requirements, and each requirement change.
2. Each project's architecture.
3. PR 1 (the design) and PR 2 (the test plan) of the first features, 3 by default ([section 3.4](03-features.md#34-after-the-first-features)).
4. Each version, by testing it on your own devices ([section 5.4](05-release.md#54-your-test-on-your-devices)).
5. Every escalation (section 7.3).

For steps 1 to 3, the PR's description opens with a one-page summary for you, first in Chinese, then in English ([F14 design](../design/F14-summary.md)): what changes for you as a user, each point you decide, numbered, with its options and a recommendation, and the risks. troy-mode also sends you the summary in chat, in the language you write in, with the PR's link. The comment `Waiting for Troy: approve this PR` only points to it. Every design, test plan, requirements, and architecture PR opens with such a summary, even one that troy-mode merges itself, and CI checks it (R22).

You approve steps 1 to 3 in chat or by merging the PR on GitHub:

- **In chat**, reply that you approve. "全按推荐", "all as recommended", or "approved" takes every recommendation of the summary. To pick another option, give its number and the option, for example "2: option 2": troy-mode treats that as a request for changes. troy-mode records "Approved by Troy" with the date in the document's header and change log, in both languages, and merges the PR ([F08 design D77](../design/F08-release.md#13-decisions-for-troy)).
- **On GitHub**, merge the PR. troy-mode then records the approval in a `[docs] Record Troy's approval of <document>` PR, which it merges ([F07 design D61](../design/F07-entry-skill.md#16-decisions-for-troy)).
- **To ask for changes**, say what to change, in chat or as a comment on the PR. The author revises, as a review round, and the PR waits for you again.

Two more answers of yours start or stop work: a rule proposal ([section 6.1](06-rules.md#61-add-a-rule-for-this-project)), and the question after the first features. A step that waits for you is written in the progress file as "Waiting on Troy", so any session knows it.

## 7.2 What troy-mode does alone

troy-mode merges every PR except those that wait for you, once every review approved and every check passed (R18). Its other rights ([F07 design section 9](../design/F07-entry-skill.md#9-escalation-57)):

- push its own branches, with `--force-with-lease`;
- open, edit, comment on, close, and merge its own PRs, within R18;
- open `bug` issues in the project;
- delete its own branches after their PR merges;
- after you accept a version, create its GitHub release on the release PR's merge commit;
- merge the PRs of a rule you approved.

Anything else asks you first. In particular, nothing outside the project happens without your yes: creating the GitHub repository at setup, and opening an issue in tstack for a rule for every project. troy-mode never commits on `main`, pushes `main`, or opens a PR from `main` (R21), and it never works around a refused permission.

## 7.3 Answer an escalation

troy-mode stops and asks you when ([requirements section 5.7](../requirements.md#57-escalation)):

- a review loop reaches 3 rounds without agreement;
- a change needs the requirements or the architecture to change;
- an author's work still fails its checks after 3 attempts;
- a new third-party dependency is needed;
- a role moved `HEAD` or the branch, or wrote outside its scope twice;
- an action is irreversible and outside its rights, such as a force push or deleting data.

The message, in your language, says where it stopped, why, the facts with links, the options, and a recommendation, in the shape of requirements Prototype C. It is also posted in English on the open PR as `Escalation: <trigger>`, or on the bug's issue when no PR is open yet. This one is from the trial's issue [#13](https://github.com/ZJUCao/troy-mode-trial/issues/13), shortened:

```text
Escalation: a new third-party dependency is needed

Stopped at: B13, PR B (fix), before any code change.
Why: Troy asked for the fix to use pathvalidate, a new third-party runtime dependency (R16);
it also needs a requirement change.
Option A: no dependency. count_words raises FileNotFoundError when os.fspath(path) is "",
as open("") does. No document changes; PR B can go on at once.
Option B: add pathvalidate. Needs a requirement change, a dependency table and ADR in the
architecture, and still the wrapper.
Recommendation: A, because it fixes the bug in about two lines.
```

Your answer must contain your decision: one of the options, such as "A", or a decision of your own, with anything the roles need to know to follow it. For a new dependency, accept or refuse it. troy-mode puts your decision into the next role's brief and goes on, in this session or a new one.

## 7.4 Status labels

A feature's status in the requirements' features table says how far it really goes (R13, [F01 design section 7](../design/F01-templates.md#7-feature-status-labels)):

| Label | Set when |
| --- | --- |
| Not started | The requirements are approved. |
| Passes tests on main | PR 6 merges. The feature's tests are now must-pass. It has not been checked on your devices. |
| Ran for real on Troy's PC | PR 6 merges with a real run in which the feature's own prototype commands ran on your PC and matched, apart from those that wait for a later feature (F12). It has not been checked in Windows Terminal itself or on your devices. |
| Usable on Troy's devices | You accept the version that contains it, after testing it on your devices. |
| Needs rework (...) | An approved requirement change affects it before it is accepted. The brackets name the change. |

So "Passes tests on main" means the code and its tests are merged and pass in CI. "Ran for real on Troy's PC" also means that troy-mode ran the commands you type on your PC, and their output matched the prototypes. "Usable on Troy's devices" means you tested the whole version on your own devices and accepted it. The stage in between lives in the progress file.

## 7.5 Continue in a new session

troy-mode keeps no state in the conversation. The state is in git and on GitHub: commit subjects on `origin/main`, open PRs, and troy-mode's own comments on them. The progress file, `.troy-mode/progress.md`, is a local view of that state, rebuilt from it when it is missing or old ([F07 design section 5](../design/F07-entry-skill.md#5-state-d58)). So a session can stop at any point, even in the middle of a feature.

To pick up, open a new session in the project and type:

```text
/tstack:troy-mode continue
```

"status", or the command with no request, does the same. troy-mode reports where the project stands and what waits on you, then goes on with the next step as far as the request reaches. In the F09 trial, a new session found a rule's cleanup this way and merged it:

```text
P01's cleanup is done: PR #32 is merged, and P01 has no baseline lines left.
Next: F02 "Count lines", stage 2, the test plan PR [F02 2/6 test-plan] Count lines.
F02 is one of the first 3 features you approve, so this PR will wait for your approval.
This run did only the cleanup. To go on with F02, say "continue".
```

That excerpt is translated from Chinese, the language that session ran in. Only the progress file's notes and the attempts counted before a PR existed are lost when the file is lost. A note also lasts only while its feature and stage stay the same, so a note for a later feature, such as a reviewer's point for F12's design written during F03, is dropped when the stage moves on. In the pilot, the session kept such notes in its own memory for the project folder, which a session on another PC does not have ([issue #67](https://github.com/ZJUCao/troy-pstack/issues/67)).

**After a usage limit.** When your plan's 5-hour limit stops the session in the middle of a step, wait for the reset and reply in the same session, for example with "continue". In the pilot this happened five times in six days, once in the middle of an Interface Designer run, and the session went on each time. A long session also fills its context: Claude Code then compacts the conversation, 15 times in the pilot's one session, and troy-mode goes on from the state in git and on GitHub.
