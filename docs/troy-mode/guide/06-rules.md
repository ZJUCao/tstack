# 6. Rules

| | |
| --- | --- |
| Version | 0.1 |
| Date | 2026-11-09 |
| Source of truth | This English file. [`06-rules.zh-CN.md`](06-rules.zh-CN.md) is the Chinese mirror. |

Every troy-mode project has a rules table, `docs/rules.md` and its mirror. Rows R01 to R22 are troy-mode's rules for every project. Rows P01, P02, and so on are the project's own. You add a project rule with one request and one answer. troy-mode writes and merges the rest ([F09 design](../design/F09-rule-change.md)).

## 6.1 Add a rule for this project

```text
/tstack:troy-mode add a rule: no f-string in exception messages
```

If the request does not say whether the rule is for this project or for every troy-mode project, troy-mode asks you that one question, and recommends this project. Then:

1. **The proposal.** The Architect picks the strongest enforcement that works and finds the existing code that breaks the rule. A project rule is enforced, from strongest to weakest, by the architecture; by a lint or CI check, which is a check of a tool the project already runs, a troy-check limit, or a step in the project's own workflow; or by its row in the rules table, which the reviewers check (Review) or troy-mode follows (Process). A test never enforces a project rule ([F09 design D80](../design/F09-rule-change.md#12-decisions-for-troy)). Nothing is written yet.
2. **One message to you**, in your language: the rule as the table will say it, in English and Chinese, with its ID and type; the enforcement, and why nothing stronger works; the files the rule PR changes; and the existing code that breaks it, with the choice below.
3. **Your answer** approves the rule and makes the choice, or asks for a change. It is your only step: no PR of this flow waits for you again ([F09 design D82](../design/F09-rule-change.md#12-decisions-for-troy)).

The choice for existing code that breaks the rule:

| You choose | What happens |
| --- | --- |
| Fix it now | The rule PR exempts today's violations in a baseline, so CI stays green. Cleanup PRs then fix the code and remove the baseline, at most 5 files each. |
| Only new and changed code | The baseline stays. Whenever the Developer or the Test Engineer changes a baselined file, they fix it and remove its baseline line. |

When the tool has no per-file exemption that a `[rules]` PR may change, such as clang-tidy, whose exemptions live in the source files, troy-mode offers only "fix it now": the cleanup PRs come first, and the rule PR turns the check on after them.

This is the trial's proposal for P01, shortened ([PR #31](https://github.com/ZJUCao/troy-mode-trial/pull/31) followed it). That session ran in Chinese, and the excerpt is translated:

```text
Troy, the proposal for rule P01 is ready for your approval. I have written no file and
opened no branch or PR.
Rule P01 (this project only): An exception message is never an f-string written inside
the raise. | Type: Hard | Enforced by: Lint (ruff EM102)
Existing code that breaks it: 1 file, 1 place
- src/troy_mode_trial/counting.py:61
Please choose:
- A. Fix it now (recommended). The rule PR adds one baseline line for this file to
  pyproject.toml. A cleanup PR [refactor] Apply P01 to counting follows.
- B. Only new and changed code. The baseline stays until someone changes counting.py.
```

### The PRs

| PR | Title | Merged by |
| --- | --- | --- |
| Architecture, only when the rule needs it | `[docs] Change the architecture for P01` | troy-mode: your answer to the proposal already approved it |
| The rule | `[rules] Add P01, <summary>` on `troy-mode/rule-p01`: the row in both languages, the tool's config, and the baseline | troy-mode |
| Cleanup of source files, after "fix it now" | `[refactor] Apply P01 to <area>`, written by the Developer, reviewed by the Code Reviewer | troy-mode |
| Cleanup of test files, after "fix it now" | `[P01 test-fix] Apply P01 to tests`, written by the Test Engineer, reviewed by the Test Manager and the Code Reviewer | troy-mode |

A baseline line sits in the tool's own config and names the rule, for example in `pyproject.toml`:

```toml
"src/troy_mode_trial/counting.py" = ["EM102"]  # baseline: P01
```

A rule's cleanup PRs come before the feature loop's next stage. In the trial, the cleanup [#32](https://github.com/ZJUCao/troy-mode-trial/pull/32) removed P01's only baseline line in the same commit as the fix. A review rule, such as the trial's P02 "every error message names its file" ([#33](https://github.com/ZJUCao/troy-mode-trial/pull/33)), changes no config: its rule PR adds only the row, and the reviewers its Enforced by names check it from then on.

## 6.2 Change or retire a rule

```text
/tstack:troy-mode change P01: also cover messages built with %
/tstack:troy-mode retire P02
```

- **A change** runs the same steps and lands as `[rules] Change P01, <summary>`. The row keeps its Since date, and its config and baseline change in the same PR.
- **A retirement** needs no proposal. troy-mode shows you the row and the config and baseline lines the PR removes, and your yes approves it. It lands as `[rules] Retire P02, <summary>`. The row stays, starting `Retired on <date>.`, and its ID is never used again. The trial retired P02 in [#34](https://github.com/ZJUCao/troy-mode-trial/pull/34).

## 6.3 Adjust a troy-mode rule in one project

Never edit an R row: troy-init's upgrade replaces the R rows. Where troy-check's config allows an adjustment, such as R03's size limits, R11's coverage limits, or R19's attribution mode, ask for it as a project rule:

```text
/tstack:troy-mode in this project, R03's limit is 800 lines
```

A P row records the adjustment, for example "In this project, R03's limit is 800 changed lines.", and the same rule PR changes `.troy-mode/config.toml`. Any other change to an R rule is a rule for every project (section 6.4).

## 6.4 Propose a rule for every project

```text
/tstack:troy-mode a rule for every project: no TODO comments in merged source
```

A rule for every troy-mode project lives in tstack and ships in a new plugin version. So this flow changes nothing in the project and nothing in tstack ([F09 design D83](../design/F09-rule-change.md#12-decisions-for-troy)):

1. The Architect proposes the enforcement as for a project rule, names the tstack files that would change, and says whether existing projects' code would break the rule when the upgrade brings it.
2. troy-mode sends you the proposal and asks whether to open an issue in tstack.
3. **Only on your yes**, it opens the issue `Rule proposal: <summary>` in tstack. Opening it reaches outside the project, so it always asks. On a no, it opens nothing.
4. tstack builds the rule through its own process ([section 9](09-changing-troy-mode.md)), and the project gets it through the upgrade.

In the trial, the proposal for R22, no TODO comments, was declined, and no issue was opened.
