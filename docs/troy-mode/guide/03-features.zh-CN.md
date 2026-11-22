# 3. 做功能

> 本文件是 [`03-features.md`](03-features.md) 的中文镜像，同步自英文版 0.3（2026-11-18）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.3 |
| 日期 | 2026-11-18 |
| 事实来源 | 英文版 [`03-features.md`](03-features.md)。本文件是中文镜像。 |

troy-mode 按需求文档里的拓扑顺序，一次做一个功能。每个功能分六个 PR，按顺序合入，每个 PR 只有一个 commit，只包含一个阶段的产出（[需求文档第 5.2 节](../requirements.zh-CN.md#52-功能循环)）。前几个功能的前两个 PR 由你批准，其他的都由 troy-mode 合并。

## 3.1 请求

| 你输入 | troy-mode 做什么 |
| --- | --- |
| `/tstack:troy-mode 下一个功能` | 按顺序的下一个功能 |
| `/tstack:troy-mode F04` | 功能 F04 |
| `/tstack:troy-mode F04 到 F06` | F04、F05 和 F06，按顺序 |
| `/tstack:troy-mode 开始做 v0.1` 或 `/tstack:troy-mode v0.1 剩下的功能` | v0.1 里所有还没验收的功能，按顺序 |

一个请求只做到一个功能为止，除非它点名了更多，像最后两行那样：几个功能，或者一个版本。点名一个版本的请求，做到这个版本里所有还没验收的功能，在发布之前停下；发布要用 `release v0.1` 来请求（[F07 设计 D203](../design/F07-entry-skill.zh-CN.md#16-需要-troy-决定的事项)）。做完之后 troy-mode 报告结果并停下（[D63](../design/F07-entry-skill.zh-CN.md#16-需要-troy-决定的事项)）。在这个范围之内，它自己从一个阶段走到下一个阶段、从一个功能走到下一个功能，只在需要你的地方停下：你的批准，或者升级上报。你批准之后它接着做。试点中，在 D203 之前，“Start v0.1” 只做到了 F01，后面每个功能都要单独请求，比如 “Start F02” 或 “开始做F09”（[issue #52](https://github.com/ZJUCao/tstack/issues/52)）。

一个功能要花多少：试点中，`ZJUCao/recipe-menu` 的 13 个功能，从设计 PR 到验收，每个用了 3 到 16 小时，期间你批准了它的设计和测试计划。每个功能有 14 到 24 次角色运行，按 API 标价花了 45 到 103 美元，大部分花在用 opus 的角色和主会话上。

troy-mode 同一时间只处理一个 PR。新的请求要等开着的 PR 合入，除非你说先暂停它。

## 3.2 六个 PR

`<name>` 是需求文档里功能的短名。分支从 `troy-mode/f04-1-design` 到 `troy-mode/f04-6-accept`。

| PR | 标题 | 内容 | 作者 | 审查 | 谁来合并 |
| --- | --- | --- | --- | --- | --- |
| 1 | `[F04 1/6 design] <name>` | 接口设计，中英文：每个对外接口的名称、功能、参数、返回值和错误，需求里定了性能指标时还有性能指标。描述以给你的摘要开头。 | 接口设计师 | 架构师，按它的检查清单 | troy-mode，前几个功能在你批准之后 |
| 2 | `[F04 2/6 test-plan] <name>` | 测试方案，中英文：单元、功能、集成和性能用例。描述以给你的摘要开头。 | 测试经理，参考接口设计师的回答 | 和接口设计师对齐，最多 3 轮提问 | 同 PR 1 |
| 3 | `[F04 3/6 mock] <name>` | 函数签名和完整的文档注释，不写函数体 | 开发工程师 | 代码审查员 | troy-mode |
| 4 | `[F04 4/6 tests] <name>` | 测试。每个新测试对着 mock 都失败（R09）。 | 测试工程师 | 测试经理和代码审查员一起审查 | troy-mode |
| 5 | `[F04 5/6 impl] <name>` | 功能实现。每个测试都通过，覆盖率满足 R11。 | 开发工程师 | 代码审查员 | troy-mode |
| 6 | `[F04 6/6 accept] <name>` | 原型的真跑，以及功能的状态，中英文都改：“在 Troy 的电脑上真跑过”或“在 main 上通过测试”。PR 里有运行文件；描述里是真实输出和它与原型的对比。 | 产品经理 | 无。每处不一致由测试经理裁定。 | troy-mode |

每次推送之前，troy-mode 先运行本地检查：每个 PR 都跑 `troy-check pr`，PR 3 到 PR 5 还要跑语言包的各个步骤和 `troy-check code`。CI 在 GitHub 上运行同样的检查。只有这个阶段的每个审查都通过、本地检查通过、每个 CI 检查也都通过，troy-mode 才合并（[F07 设计第 8.6 节](../design/F07-entry-skill.zh-CN.md#86-合并r18f02-d14)）。

## 3.3 你会看到什么

troy-mode 用你的语言报告每个阶段。PR 等你处理时，它还会在 PR 上写明。下面是试运行里的 PR [#7](https://github.com/ZJUCao/troy-mode-trial/pull/7)，也就是 F01 的设计，经过缩短。PR 评论总是用英文写：

```text
Architect review, round 1: approved

All six checklist items pass; section 4 of the design and its mirror holds the review.
Findings: None.

Waiting for Troy: approve this PR

F01 is one of the first 3 features whose design Troy approves (D61). The Architect approved
the design in round 1, troy-check pr passes locally on a4eb7a1, and both CI checks pass.
Approve in chat, ask for changes, or merge on GitHub.
```

从 F14 起，PR 1 和 PR 2 的描述以给你的一页摘要开头，先中文后英文：对你作为用户有什么变化、需要你决定的每一件事和推荐，以及风险。测试方案的摘要说明测试检查了你会看到的哪些东西、没有测什么，以及哪些要你手动运行。这时 `Waiting for Troy: approve this PR` 评论下面只有一行：“What to decide is in the summary at the top of the description.”，troy-mode 还会在聊天里把摘要发给你。[F14 设计](../design/F14-summary.zh-CN.md#35-一个例子)里有一份真实设计的摘要，[第 7.1 节](07-taking-part.zh-CN.md#71-等你处理的步骤)说明怎样回答。

每一步之后，troy-mode 还会告诉你接下来是什么，以及需不需要你。下面是 F09 试运行第一个会话的结尾。那个会话用英文进行：

```text
I did nothing else. The next step is [F02 2/6 test-plan] Count lines. Its PR also needs
your approval, because F02 is among the first 3 features you approve.
```

从 F12 起，PR 6 先像你打字那样真跑一遍程序。`troy_flow.py real-run` 在一个临时的主文件夹里，把这个功能和每个已验收功能的原型里的每条 `PS> ` 命令重放一遍，把输出和原型逐字比较，对齐中文列的空格也算在内。每个原型旁边有一个运行文件 `docs/prototypes/<name>.run.toml`，写明每一节的数据文件夹怎样开始。每处不一致都由测试经理裁定：bug 在验收之前走 bug 流程；只有你批准的设计有意选了新的输出时，原型才改（[F12 设计](../design/F12-real-run.zh-CN.md)）。PR 描述里多一节 “Real run”，写着 commit、计数、每条命令一行，以及真实输出。troy-mode 随后会这样报告，下面是英文的例子：

```text
[6/6] Real run: 41 commands of 6 prototypes match on your PC. 3 wait for F12.
      Acceptance PR #96 merged. F11 status is now "Ran for real on Troy's PC".
      Not yet checked in Windows Terminal itself or on your devices.
```

功能自己的命令都在你的电脑上跑过并且一致时（等待后续功能的命令除外），PR 6 把它的状态改为“在 Troy 的电脑上真跑过”，否则改为“在 main 上通过测试”，并在 PR 里写明原因。真跑通过管道而不是控制台，所以看不出 Windows Terminal 怎样显示文字。这个功能还没在你的设备上验证过：那要等你测试它所在的版本时才做（[第 5 节](05-release.zh-CN.md)）。

从 F15 起，每个功能在 GitHub 上还有一个**进度 issue**，标签是 `progress`，从它成为下一个功能或有了某一步的 PR 开始，直到验收。它的标题是功能的编号和名字，正文把六步列成复选框，每个 PR 合入就勾上一项，还写着等你做什么，以及文档的链接；中文在前，英文折叠在下面。每一步的 PR 在 Why 开头写 `Progress: #<n>`，所以 GitHub 会在 issue 里列出它；PR 6 的 `Closes #<n>` 会关闭它。正文由 troy-mode 维护：你的改动会在下次运行时被换回来；想对 troy-mode 说什么，就写评论（[第 7.6 节](07-taking-part.zh-CN.md#76-在手机上)，[F15 设计第 4 节](../design/F15-issues.zh-CN.md#4-进度-issued142)）。

## 3.4 前几个功能之后

按顺序的前 3 个功能，PR 1 和 PR 2 由你批准（需求文档 Q2、R18）。这个数字是 `.troy-mode/config.toml` 里 `[flow]` 表的 `troy_approves_first`，默认是 3。

批准的方式和需求文档一样：在聊天里回复，或者在 GitHub 上合并 PR（[第 2.3 节](02-start.zh-CN.md#23-需求文档)）。在聊天里回复之后，troy-mode 把你的批准记进文档的文件头和修改记录，然后合并。要求修改时，说出要改什么：作者修改之后，PR 再次等你处理。

这些功能里的最后一个验收之后，troy-mode 会问你一次：之后的功能还要不要继续批准 PR 1 和 PR 2，要的话再批准几个（[F07 设计 D62](../design/F07-entry-skill.zh-CN.md#16-需要-troy-决定的事项)）：

| 你的回答 | 结果 |
| --- | --- |
| 不用了 | `troy_approves_first` 停在已经做完的功能数。之后的设计和测试方案都由 troy-mode 自己合并，前提是架构师已批准设计，测试方案的问题也都已解决。 |
| 要，再批准 N 个功能 | `troy_approves_first` 加 N。接下来 N 个功能的 PR 1 和 PR 2 由你批准，最后一个做完后 troy-mode 再问一次。 |

troy-mode 把你的回答记进 `.troy-mode/config.toml`，附一行注释写明这项决定和日期，用一个 `[rules] Set the features Troy approves` PR 提交，并合并它。除了 troy-init 的各个步骤和规则变更流程，这是 troy-mode 做的唯一一项配置改动。

## 3.5 审查、轮次和尝试次数

- **轮次（R17）。** 一轮就是这个阶段的审查者运行一次。审查要求修改时，意见会交回作者，然后开始下一轮。3 轮仍未通过，troy-mode 就向你升级上报。在 PR 4 上，任何一位审查者要求修改，这一轮就算没通过。
- **尝试次数（D64）。** 一次尝试指作者的一次失败的运行：运行本身失败、它的本地检查失败，或者它的 CI 在作者的文件里失败。每个阶段允许 3 次。第三次之后，troy-mode 升级上报（[F07 设计第 8.5 节](../design/F07-entry-skill.zh-CN.md#85-尝试次数d64)）。即使没有人为某次 CI 失败发评论，troy-mode 也会算上它：每个在 CI 里有检查失败的推送提交算一次，检出或环境安装的失败不算。发现没有评论的失败时，它会补发评论，用 `Commit:` 一行写明是哪个提交。
- **评论。** 每次审查和每次失败的尝试都是一条 PR 评论，标题像 `Test Manager review, round 1: changes-requested` 或 `Developer attempt 2: failed`。每个角色都通过你的 GitHub 账号操作，所以没有 troy-mode 标题的评论都算是你的（[参考：评论标题](08-reference.zh-CN.md#83-评论标题)）。troy-mode 会把你在 PR 上的评论转给这个 PR 的作者。

在试运行的 PR [#10](https://github.com/ZJUCao/troy-mode-trial/pull/10)（F01 的测试）里，两位审查者在第 1 轮都要求修改，因为有一个测试的输入和测试方案不一致；第 2 轮两人都通过了。

## 3.6 旁支 PR

有些问题需要在一个阶段中途单独开一个小 PR。troy-mode 开这个 PR、合并它，然后回到原来的阶段。只有该由你做的决定才会问你。

| 问题 | troy-mode 怎么做 | PR |
| --- | --- | --- |
| 开发工程师认为某个测试错了 | 测试经理裁定。代码错了：开发工程师再试一次。测试错了：测试工程师只修那一个测试。 | `[F04 test-fix] <summary>` |
| 覆盖率低于 R11 | 测试经理判断没覆盖到的是什么代码：用不到的代码删掉；测试方案漏掉的用例补上并写测试；设计里没有的行为交给接口设计师；测不了的代码标记排除，并写明经测试经理批准的原因。 | `[docs] Add cases to the F04 test plan`，然后是 `[F04 test-fix] <summary>` |
| 新的第三方依赖（R16） | 架构师审查它，并带着建议向你升级上报。由你接受或拒绝。 | 接受时：`[docs] Accept the dependency <name>`，附一条 ADR |

补测试只能从设计出发，不能对着没覆盖到的代码行凑测试（[需求文档第 5.2 节](../requirements.zh-CN.md#52-功能循环)）。

## 3.7 性能测试

只有在需求里有性能指标的接口才写性能测试（R14）。接口设计师把指标写进设计，测试经理设计性能用例。它们在实现之后运行，因为 mock 总是立即返回：PR 5 的本地检查在你的电脑上运行它们（[F07 设计第 8.1 节](../design/F07-entry-skill.zh-CN.md#81-阶段)），而不是在 CI 上，因为 CI 机器的性能波动太大（需求文档 Q7）。压力测试需要整个系统，所以只在版本发布时运行（[第 5 节](05-release.zh-CN.md)）。
