# 7. 你在哪些地方参与

> 本文件是 [`07-taking-part.md`](07-taking-part.md) 的中文镜像，同步自英文版 0.1（2026-11-09）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.1 |
| 日期 | 2026-11-09 |
| 事实来源 | 英文版 [`07-taking-part.md`](07-taking-part.md)。本文件是中文镜像。 |

troy-mode 的设计让你只在需要做决定时出场。本页列出等你处理的步骤、troy-mode 自己做的事、状态标签的含义，以及怎样在新会话里接着做。

## 7.1 等你处理的步骤

只有这些步骤等你批准（[需求文档第 3.3 节](../requirements.zh-CN.md#33-troy-参与的环节)）：

1. 每个项目的需求文档，以及每一项需求变更。
2. 每个项目的总体架构。
3. 前几个功能（默认 3 个）的 PR 1（接口设计）和 PR 2（测试方案）（[第 3.4 节](03-features.zh-CN.md#34-前几个功能之后)）。
4. 每个版本，方式是在你自己的设备上测试它（[第 5.4 节](05-release.zh-CN.md#54-你在自己的设备上测试)）。
5. 每一次升级上报（第 7.3 节）。

第 1 到 3 步的 PR 描述以给你的一页摘要开头，先中文后英文（[F14 设计](../design/F14-summary.zh-CN.md)）：对你作为用户有什么变化、需要你决定的每一件事（带编号，写明各个方案和推荐），以及风险。troy-mode 还会在聊天里用你写的语言把摘要发给你，附上 PR 链接。`Waiting for Troy: approve this PR` 评论只是指向它。每个设计、测试计划、需求和架构 PR 都以这样的摘要开头，troy-mode 自己合并的也一样，CI 会检查它（R22）。

第 1 到 3 步，你可以在聊天里批准，也可以在 GitHub 上合并 PR 来批准：

- **在聊天里**，回复说你批准，比如“批准”。回复「全按推荐」、"all as recommended" 或“批准”，就采用摘要里的全部推荐。要选别的方案，写出编号和方案，比如“2：方案 2”：troy-mode 把它当作要求修改。troy-mode 在文档的文件头和修改记录里记下“Approved by Troy”和日期，中英文都记，然后合并 PR（[F08 设计 D77](../design/F08-release.zh-CN.md#13-需要-troy-决定的事项)）。
- **在 GitHub 上**，合并这个 PR。troy-mode 随后用一个 `[docs] Record Troy's approval of <document>` PR 记下这次批准，并合并它（[F07 设计 D61](../design/F07-entry-skill.zh-CN.md#16-需要-troy-决定的事项)）。
- **要求修改**时，在聊天里或在 PR 的评论里说要改什么。产出方修改，算作一轮审查，然后这个 PR 再次等你。

另外还有两种回答会让工作开始或停下：规则提案（[第 6.1 节](06-rules.zh-CN.md#61-为这个项目加一条规则)），以及前几个功能之后的那个问题。等你处理的步骤在进度文件里写作“Waiting on Troy”，所以任何会话都知道。

## 7.2 troy-mode 自己做的事

除了等你的 PR，troy-mode 在每个审查都批准、每项检查都通过之后，合并其他所有 PR（R18）。它的其他权限（[F07 设计第 9 节](../design/F07-entry-skill.zh-CN.md#9-升级上报57)）：

- 用 `--force-with-lease` 推送自己的分支；
- 开出、编辑、评论、关闭自己的 PR，并在 R18 之内合并它们；
- 在项目里开 `bug` issue；
- 在 PR 合入之后删除自己的分支；
- 在你验收一个版本之后，在发布 PR 的合并 commit 上创建它的 GitHub release；
- 合并你批准的规则的 PR。

其他任何操作都要先问你。特别是，没有你的同意，项目之外的事一件都不做：初始化时创建 GitHub 仓库，以及为适用于所有项目的规则在 troy-pstack 里开 issue。troy-mode 从不在 `main` 上提交、推送 `main` 或从 `main` 开 PR（R21），也从不绕过被拒绝的权限。

## 7.3 回答升级上报

出现以下情况时，troy-mode 停下来问你（[需求文档第 5.7 节](../requirements.zh-CN.md#57-升级上报)）：

- 一个审查循环到 3 轮仍未达成一致；
- 某项改动需要修改需求文档或架构；
- 产出方的工作尝试 3 次后仍过不了检查；
- 需要引入新的第三方依赖；
- 某个角色改了 `HEAD` 或分支，或者第二次写到写入范围之外；
- 某个操作不可逆，而且超出它的权限，比如强制推送或删除数据。

消息用你的语言写，说明在哪里停下、为什么、带链接的事实、各个选项，以及一个建议，形式同需求文档的原型 C。它还会用英文发到开着的 PR 上，标题为 `Escalation: <trigger>`；还没有开着的 PR 时，发到 bug 的 issue 上。下面这条来自试运行的 issue [#13](https://github.com/ZJUCao/troy-mode-trial/issues/13)，经过缩短。issue 上的这份是英文的：

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

你的回答必须包含你的决定：选一个方案，比如“A”，或者你自己的决定，并附上各个角色照着做需要知道的任何信息。对新依赖，就接受或拒绝它。troy-mode 把你的决定放进下一个角色的任务简报，然后继续，无论是在这个会话里还是在新会话里。

## 7.4 状态标签

需求文档功能表里的功能状态，如实说明这个功能做到了哪一步（R13，[F01 设计第 7 节](../design/F01-templates.zh-CN.md#7-功能状态标签)）：

| 标签 | 何时设置 |
| --- | --- |
| 未开始 | 需求文档批准时。 |
| 在 main 上通过测试 | PR 6 合入时。从此这个功能的测试必须通过。它还没在你的设备上检查过。 |
| 在 Troy 的设备上可用 | 你在自己的设备上测试了包含它的版本，并验收之后。 |
| 需要返工（...） | 某项已批准的需求变更在它验收之前影响到它时。括号里写明是哪项变更。 |

所以“在 main 上通过测试”的意思是：代码和它的测试已经合入，并在 CI 里通过。“在 Troy 的设备上可用”的意思是：你在自己的设备上测试了整个版本，并验收了它。两者之间的阶段记在进度文件里。

## 7.5 在新会话里继续

troy-mode 不在对话里保存任何状态。状态在 git 和 GitHub 上：`origin/main` 上的 commit 标题、开着的 PR，以及 troy-mode 自己在这些 PR 上的评论。进度文件 `.troy-mode/progress.md` 是这份状态的本地视图，缺失或过时的时候会从状态重建（[F07 设计第 5 节](../design/F07-entry-skill.zh-CN.md#5-状态d58)）。所以会话可以在任何地方停下，即使是在一个功能做到一半时。

要接着做，在项目里开一个新会话，输入：

```text
/troy-pstack:troy-mode 继续
```

“状态”，或者不带请求的命令，效果一样。troy-mode 报告项目进行到哪里、什么在等你，然后在请求所及的范围内接着做下一步。在 F09 的试运行里，一个新会话就是这样找到了一条规则的清理，并合并了它：

```text
P01 的清理做完了：PR #32 已合并，P01 已经没有基线行了。
下一步：F02「Count lines」的第 2 步，测试计划 PR [F02 2/6 test-plan] Count lines。
F02 是前 3 个需要你批准的功能之一，所以这个 PR 写好后要等你批准。
这次只做了清理这一项，下一步还没开始。要接着做 F02 的话，说「继续」就行。
```

丢了进度文件，丢掉的只有它的备注，以及 PR 开出之前统计的尝试次数。
