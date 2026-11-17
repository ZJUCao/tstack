# 5. 发布版本

> 本文件是 [`05-release.md`](05-release.md) 的中文镜像，同步自英文版 0.2（2026-11-17）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.2 |
| 日期 | 2026-11-17 |
| 事实来源 | 英文版 [`05-release.md`](05-release.md)。本文件是中文镜像。 |

一个版本把功能顺序里相邻的几个功能放在一起，它自身就能用。它的测试方案在它的第一个功能开始之前写好。发布时，troy-mode 先在你的电脑上运行这个版本的测试，然后请你在自己的设备上测试它。你验收之后，troy-mode 给它打标签（[F08 设计](../design/F08-release.zh-CN.md)）。

## 5.1 版本测试方案

在一个版本的第一个功能的第一个阶段之前，troy-mode 让测试经理写出这个版本的测试方案：`docs/versions/v0.1/test-plan.md` 及其镜像（[F08 设计 D70](../design/F08-release.zh-CN.md#13-需要-troy-决定的事项)）。每个场景都写明由谁运行：

- **troy-mode**，作为版本测试，在发布时在你的电脑上运行；
- **你**，在只有你才有的设备上运行，比如你的手机。

troy-mode 在 `troy-mode/v0.1-test-plan` 上开出 `[docs] Add the v0.1 test plan`，以产品经理的身份检查它，然后合并。它不需要你批准。之后版本的功能有变化时，会再有一个 `[docs] Update the v0.1 test plan`。这些都不用你请求：它们在做功能的路上自然发生。

## 5.2 请求

版本的最后一个功能验收之后，输入：

```text
/tstack:troy-mode 发布 v0.1
```

只说“发布”，指的是 troy-mode 说该发布的那个版本。发布请求从不做功能。如果版本里有功能还没验收，troy-mode 会告诉你是哪些，然后停下：先请求这些功能，比如“v0.1 剩下的功能”，再请求发布（[F07 设计 D63](../design/F07-entry-skill.zh-CN.md#16-需要-troy-决定的事项)）。

## 5.3 步骤

| 步骤 | 做什么 | PR | 你 |
| --- | --- | --- | --- |
| 1. 就绪 | 开着的 PR 先合并。未关闭的 bug 先修好，除非你推迟它。 | 无 | 如果你愿意，推迟一个 bug |
| 2. 版本测试 | 测试工程师为 troy-mode 运行的每个场景写一个测试，放在 `version-tests/` 里 | `[v0.1 tests] End-to-end and stress tests` | |
| 3. 发布 PR | 产品经理在 `CHANGELOG.md` 及其镜像里加上这个版本的一节 | `troy-mode/release-v0.1.0` 上的 `[docs] Release v0.1.0` | |
| 4. 发布测试 | 在你的电脑上运行回归测试和版本测试，然后 `real-run --all` 像你打字那样跑一遍每个已验收功能的原型。有一处不一致，发布测试就失败。报告发到发布 PR 上。 | 无 | |
| 5. 你的测试 | 你在自己的设备上运行你的场景，然后回复 | 无 | 测试并回复 |
| 6. 验收 | 每个功能的状态改为“在 Troy 的设备上可用”，发布 PR 合并 | 发布 PR | |
| 7. 标签 | 在发布 PR 的合并 commit 上创建 GitHub release `v0.1.0`，说明取自 changelog 的这一节 | 无 | |
| 8. 复盘 | 这个版本期间反复出现的问题，以及能防止它们的规则 | 无 | 如果你愿意，挑选规则 |

从发布 PR 开始，每一步都在它上面留评论，所以新会话能在中断的地方找到这次发布。即使有版本测试失败，版本测试 PR 也会合并：CI 不运行它们，失败的场景是发布测试的发现。性能测试和压力测试也在第 4 步运行（[F08 设计第 5.5 节](../design/F08-release.zh-CN.md#55-发布测试)）。

## 5.4 你在自己的设备上测试

发布测试通过之后，troy-mode 在发布 PR 上发出 `Waiting for Troy: accept v0.1.0`，并用你的语言告诉你：

- 要测试的 commit，以及带 changelog 的发布 PR 的链接；
- troy-mode 运行过的场景及其结果；
- 你要运行的每个场景：设备、步骤和预期结果。

然后它停下。下面是试运行的发布 PR [#27](https://github.com/ZJUCao/troy-mode-trial/pull/27) 上的评论，经过缩短。PR 评论用英文写：

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

从 F15 起，troy-mode 还会为这个版本开一个**设备测试清单**，即标签为 `device-test` 的 issue：你要运行的每个场景一个复选框，附上设备、步骤和预期结果，都从版本测试方案里复制过来；最后一个复选框是"我接受 <tag>。"。场景结果和预期一样就勾上；不一样就不勾，写一条评论说明。所有复选框都勾上，包括最后一个，就是你的验收：troy-mode 下次运行时把它记录在发布 PR 上，然后继续。版本里没有你要运行的场景时，清单里也有这个接受框。修了 bug、重新做发布测试之后，troy-mode 会清掉接受框和没通过的场景，保留你的其他勾选，并评论 `Device test, run <n>: ready`（[F15 设计第 6 节](../design/F15-issues.zh-CN.md#6-设备测试清单d144)）。

在聊天里回复，或者在发布 PR 上评论。回复有三种（[F08 设计第 5.6 节](../design/F08-release.zh-CN.md#56-troy-的测试)）：

| 你的回复 | 接下来会怎样 |
| --- | --- |
| 接受，可以附带备注，例如“接受，没有意见。” | 验收、打标签和复盘（第 6 到 8 步）。 |
| 某个场景失败，例如“v0.1-S03 在我手机上失败了：它显示的是一个空列表。”写明是哪个场景、在哪台设备上，以及你看到了什么。 | troy-mode 记下它，由测试经理分类裁定。bug 会有它的 issue 和两个 PR（[第 4.1 节](04-bugs-and-changes.zh-CN.md#41-修-bug)）。写错的版本测试会被修正。误解的需求会成为一项需求变更。然后 changelog 列出这些修复，发布测试作为第 2 次运行重新进行，你只重新测试失败的场景，除非你要求测更多。 |
| 不验收，原因不是 bug，比如某个功能不是你想要的 | 需求变更流程（[第 4.2 节](04-bugs-and-changes.zh-CN.md#42-修改需求)）。发布要等变更后的功能重新验收之后再继续。 |

troy-mode 把每次回复记录到发布 PR 上，标题为 `Release test by Troy, run <n>: accepted`、`failed` 或 `not accepted`，后面附上你的原话。试运行里是 `Release test by Troy, run 1: accepted`。

## 5.5 未关闭的 bug

带 `bug` 标签的未关闭 issue 会挡住发布，直到它修好或者你推迟它。要推迟一个，就在聊天里说，例如“把 #21 推迟到 v0.2”。troy-mode 把它记录到发布 PR 上，标题为 `Bug deferred by Troy: #21`，后面附上你的原话。

## 5.6 验收和标签

你验收之后，产品经理把这个版本里每个功能的状态改为“在 Troy 的设备上可用”，中英文都改，troy-mode 把你的验收记进版本测试方案。然后它合并发布 PR，在合并 commit 上创建 GitHub release。你的电脑上不推送任何东西：标签由 GitHub 创建。创建 release 是 troy-mode 的权限之一，只在你验收之后进行（[第 7.2 节](07-taking-part.zh-CN.md#72-troy-mode-自己做的事)）。

如果你自己在 GitHub 上合并了发布 PR，troy-mode 会用一个 `[docs] Record Troy's acceptance of v0.1.0` PR 记下你的验收，然后创建 release。

## 5.7 补丁版本

```text
/tstack:troy-mode 发布 v0.1.1
```

补丁版本发布 v0.1.0 之后合入的 bug 修复。它没有自己的版本测试方案，也不加新的版本测试，但发布测试会把全部版本测试再运行一遍，你测试修好的 bug 涉及的场景。changelog 的这一节只有 Fixed，功能保持原来的状态。补丁版本不做复盘。

只有在打标签之后还没有合入后续版本功能的代码时，才能发布补丁版本。否则 troy-mode 会说明这些修复随下一个版本发布，然后停下（[F08 设计 D75](../design/F08-release.zh-CN.md#13-需要-troy-决定的事项)）。

## 5.8 复盘

打标签之后，troy-mode 把这个版本各个 PR 的证据分组：按规则分组的审查意见、失败的尝试、升级上报、bug，以及 hook 日志行。hook 日志只保留最近一天的行，所以版本早些时候的拦截到不了复盘里（[issue #66](https://github.com/ZJUCao/troy-pstack/issues/66)）。对出现在两个或更多 PR 里的每个问题，它按 pstack 的 `correct` 技能提出一条规则，并选用可行的最强执行方式。它给你发一条消息，写明这些问题、它们的 PR 链接和它的建议，并把同一份报告以 `Retrospective: v0.1.0` 为标题发到发布 PR 上，这次发布到此结束。

你挑选的每条规则随后逐条走规则变更流程（[第 6 节](06-rules.zh-CN.md)）。下面摘自试运行的发布 PR [#27](https://github.com/ZJUCao/troy-mode-trial/pull/27)，经过缩短。这条评论也是英文的：

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
