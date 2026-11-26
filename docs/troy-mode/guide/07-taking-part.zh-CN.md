# 7. 你在哪些地方参与

> 本文件是 [`07-taking-part.md`](07-taking-part.md) 的中文镜像，同步自英文版 0.3（2026-11-25）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.3 |
| 日期 | 2026-11-25 |
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

产品经理的说明书把这些步骤和第 7.3 节的升级上报列为等待 W1 到 W11（[F18 设计第 4 节](../design/F18-fewer-stops.zh-CN.md)）。每次等待都带着编号：评论标题下一行的 `Wait: W<n>`，进度文件和功能的进度 issue 上也是同一个编号。troy-mode 不在别处停下：没有哪一步要求问的问题，它自己决定，并在 PR 和报告里说明选了什么、为什么。复盘会列出任何没有编号的停顿。

**推翻裁定。** 审查循环到第 3 轮仍有分歧时，由架构师逐条裁定意见并把理由写进 PR；如果是架构师自己的审查，则由产品经理裁定。troy-mode 会在报告里告诉你，功能的进度 issue 上也有一行。在功能验收之前，你可以在那个进度 issue 上评论，或者在聊天里说，哪一方对，就能推翻裁定。troy-mode 在那里用 `Overturn: <裁定的链接>` 回应，停住这个功能，通过平常的 PR（设计更新、测试修正或 bug 修复）执行你的决定，这些 PR 合并后再发 `Overturn carried out:`（[F18 设计第 5 节](../design/F18-fewer-stops.zh-CN.md)）。

## 7.2 troy-mode 自己做的事

除了等你的 PR，troy-mode 在每个审查都批准、每项检查都通过之后，合并其他所有 PR（R18）。它的其他权限（[F07 设计第 9 节](../design/F07-entry-skill.zh-CN.md#9-升级上报57)）：

- 用 `--force-with-lease` 推送自己的分支；
- 开出、编辑、评论、关闭自己的 PR，并在 R18 之内合并它们；
- 在项目里开 `bug` issue；
- 缺少标签 `idea`、`progress` 和 `device-test` 时创建它们，维护进度 issue 和设备测试清单；在你的想法上评论、加标签、关闭它们，并为你在聊天里给出、暂时不做的想法开一个想法 issue（[第 7.6 节](#76-在手机上)）；
- 在 PR 合入之后删除自己的分支；
- 在你验收一个版本之后，在发布 PR 的合并 commit 上创建它的 GitHub release；
- 合并你批准的规则的 PR。

其他任何操作都要先问你。特别是，没有你的同意，项目之外的事一件都不做：初始化时创建 GitHub 仓库，以及为适用于所有项目的规则在 tstack 里开 issue。troy-mode 从不在 `main` 上提交、推送 `main` 或从 `main` 开 PR（R21），从不删除 issue 或标签，从不替你勾选清单，也从不绕过被拒绝的权限。

## 7.3 回答升级上报

出现以下情况时，troy-mode 停下来问你（[需求文档第 5.7 节](../requirements.zh-CN.md#57-升级上报)）：

- 某项改动需要修改需求文档或架构；
- 产出方的工作尝试 3 次、再加一次检验它们共同假设的尝试之后仍过不了检查，或者按裁定修改后仍然不行；
- 需要引入新的第三方依赖；
- 某个角色改了 `HEAD` 或分支，或者第二次写到写入范围之外，或者 CI 两次在产出方的文件之外失败；
- 权限或自动模式拒绝了 troy-mode 需要的一步，它从不绕过；
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
| 在 Troy 的电脑上真跑过 | PR 6 合入，且其中的真跑里，这个功能自己的原型命令在你的电脑上跑过并且一致，等待后续功能的命令除外（F12）。它还没在 Windows Terminal 本身里、也没在你的设备上检查过。 |
| 在 Troy 的设备上可用 | 你在自己的设备上测试了包含它的版本，并验收之后。 |
| 需要返工（...） | 某项已批准的需求变更在它验收之前影响到它时。括号里写明是哪项变更。 |

所以“在 main 上通过测试”的意思是：代码和它的测试已经合入，并在 CI 里通过。“在 Troy 的电脑上真跑过”还表示：troy-mode 在你的电脑上跑过你会打的那些命令，输出和原型一致。“在 Troy 的设备上可用”的意思是：你在自己的设备上测试了整个版本，并验收了它。两者之间的阶段记在进度文件里。

## 7.5 在新会话里继续

troy-mode 不在对话里保存任何状态。状态在 git 和 GitHub 上：`origin/main` 上的 commit 标题、开着的 PR，以及 troy-mode 自己在这些 PR 上的评论。进度文件 `.troy-mode/progress.md` 是这份状态的本地视图，缺失或过时的时候会从状态重建（[F07 设计第 5 节](../design/F07-entry-skill.zh-CN.md#5-状态d58)）。所以会话可以在任何地方停下，即使是在一个功能做到一半时。

要接着做，在项目里开一个新会话，输入：

```text
/tstack:troy-mode 继续
```

“状态”，或者不带请求的命令，效果一样。troy-mode 报告项目进行到哪里、什么在等你，然后在请求所及的范围内接着做下一步。在 F09 的试运行里，一个新会话就是这样找到了一条规则的清理，并合并了它：

```text
P01 的清理做完了：PR #32 已合并，P01 已经没有基线行了。
下一步：F02「Count lines」的第 2 步，测试计划 PR [F02 2/6 test-plan] Count lines。
F02 是前 3 个需要你批准的功能之一，所以这个 PR 写好后要等你批准。
这次只做了清理这一项，下一步还没开始。要接着做 F02 的话，说「继续」就行。
```

丢了进度文件，丢掉的只有它的备注，以及 PR 开出之前统计的尝试次数。备注也只在它的功能和阶段不变时保留，所以给后面功能的备注，比如 F03 时审查者为 F12 的设计留下的一点意见，会在阶段往前走时被丢掉。试点中，会话把这类备注存在它自己针对项目文件夹的记忆里，换一台电脑的会话就没有（[issue #67](https://github.com/ZJUCao/troy-pstack/issues/67)）。

**用量上限之后。** 你的套餐的 5 小时上限在某一步中途让会话停下时，等它重置，然后在同一个会话里回复，比如“继续”。试点中六天里发生了五次，有一次在界面设计师运行到一半时，会话每次都接着做下去了。长会话的上下文也会填满：这时 Claude Code 会压缩对话，试点的那一个会话压缩了 15 次，troy-mode 根据 git 和 GitHub 上的状态接着做。

## 7.6 在手机上

从 F15 起，你可以在 GitHub 应用里，通过项目仓库的 issue 跟进和指挥一个项目（[F15 设计](../design/F15-issues.zh-CN.md)）。文档仍然在仓库里；issue 只显示状态，或者带来你的输入。你不在电脑前时什么都不会运行：troy-mode 在你电脑上的下一次运行时读你的修改和评论，比如 `/tstack:troy-mode continue`。

| 你在手机上 | troy-mode 在下次运行时 |
| --- | --- |
| 用模板"Idea / 想法"开一个 issue，或开一个不带标签的 issue | 在下一个自然停顿点处理这个想法（[第 4.2 节](04-bugs-and-changes.zh-CN.md#42-修改需求)），并用你的语言评论它是什么 |
| 在想法上评论 | 把它和想法一起读：更多细节，或者你对它的问题的回答 |
| 在功能的进度 issue 上评论 | 当作聊天里的消息读：问题会得到一条 `Reply to Troy` 评论，关于当前 PR 的意见转给那个 PR 的作者 |
| 在等你的 PR 上评论，或留下"Comment"评审 | 当作你在聊天里的回复："全按推荐"、"all as recommended"或"approved"批准这个 PR；选别的方案就是要求修改 |
| 勾选设备测试清单，或在上面评论 | 全部勾上就是你对这个版本的验收（[第 5.4 节](05-release.zh-CN.md#54-你在自己的设备上测试)） |
| 改了 troy-mode 写的文字，或关闭进度 issue 或清单 | 把文字换回来，或重新打开它 |

标签是 `idea`、`progress` 和 `device-test`。缺少的由 troy-mode 创建，已有的它从不修改。它写的 issue 中文在前，英文折叠在下面；除了你要运行的场景，不放文档的正文，只链接到 `main` 上的文档。

GitHub 从不为你自己的操作通知你，而每个角色都通过你的账号操作，所以 troy-mode 的 issue 和评论不会给你发通知。troy-mode 仍会在聊天里告诉你什么在等你。写 issue 失败时，troy-mode 记下来、告诉你，然后继续；下一次运行会把 issue 改对。
