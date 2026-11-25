# F15 设计：给 Troy 的 issue

> 本文件是 [`F15-issues.md`](F15-issues.md) 的中文镜像，同步自英文版 1.5（2026-11-25）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.39](../requirements.zh-CN.md#72-功能列表) 中的 F15 |
| 版本 | 1.5 |
| 日期 | 2026-11-25 |
| 状态 | Troy 已于 2026-11-16 批准，含 D141 到 D150。1.1 版记录构建和试运行确认的事实。1.2 版记下 F20 设计（D268 到 D279，Troy 已于 2026-11-22 批准）带来的改动，这些改动随 F20 的构建落地。1.3 版跟随 F07 为 tstack issue #67 定的 D284 到 D287，依据 Troy 2026-11-22 的长期同意批准：给后续功能的备注是 troy-mode 在进度 issue 上的评论（第 3.3、4.2、4.4 和 8.4 节）。1.4 版记录 tstack #67 的构建把备注一行放在哪里（第 4.2 节）。1.5 版记下 F18 设计（D171 到 D180，Troy 已于 2026-11-25 批准）带来的改动，这些改动随 F18 的构建落地。 |
| 事实来源 | 英文版 [`F15-issues.md`](F15-issues.md)。本文件是中文镜像。 |

## 1. 范围

F15 让 Troy 用手机跟进和引导一个 troy-mode 项目，方式是项目仓库里的 GitHub issue（需求文档 3.3、5.4 和 5.5）。它交付三种 issue：

1. **每个功能一个进度 issue**，把它的 6 个 PR 列成勾选清单，每一步之后都保持最新，验收时关闭（第 4 节，D142）。
2. **想法 issue。** Troy 为每个新想法或改动请求开一个，产品经理把它变成需求变更，或者 bug、规则、回答（第 5 节，D143）。
3. **每个版本一个设备测试清单**，列出 Troy 在自己设备上运行的场景。Troy 一边测一边勾，最后一项勾上就是验收这个版本（第 6 节，D144）。

围绕它们，F15 确定：

- 每个 issue 由谁写、什么时候写：一个新的引擎命令从状态生成 issue，主会话把它发出去（第 3 节，D141）；
- Troy 在手机上的编辑和评论怎样传回来，包括 issue 上的和等 Troy 的 PR 上的（第 7 节，D145）；
- 标签、语言，以及 issue 里放什么、只放链接的是什么（第 8 节，D146）；
- `gh` 或网络出问题时怎么办（第 9 节，D147）；
- 检查和 hook（第 10 节，D148）；
- 已有项目怎样用上 F15，以及插件版本（第 12 节，D149）；
- 在真实项目用上之前怎样检查 F15（第 13 节，D150）。

文档留在仓库里。检查和 hook 把它们当文件读，而且试点的 44 份英文文档里有 12 份超过了 GitHub 对 issue 正文的长度上限。issue 是状态的一个视图，和进度文件一样（F07 D58），或者是 Troy 的一条输入。F15 用一个 PR 合入（Q10）。

## 2. 试点和两次探测发现了什么

- **还没有 issue。** 在 `ZJUCao/recipe-menu` 上，troy-mode 合并了 98 个 PR，没有开过 issue。Troy 在聊天里和发布 PR 上跟进工作。发布 v0.1.0 时，Troy 在自己的设备上跑了三个场景：在电脑上安装、Windows Terminal 里的中文、手机上的购物清单，然后在聊天里回复"All accepted"。这些场景的步骤是版本测试计划里一张 Markdown 表格的行，手机上显示成一张很宽的表。
- **正文上限按字符算。** 2026-11-16 在 `ZJUCao/troy-mode-trial` 上做了一次探测：创建一个正文有 65,537 个字符的 issue，几乎全是中文（196,563 字节）。GitHub 拒绝了："Body is too long (maximum is 65536 characters)"。没有创建任何 issue。评论的上限相同。
- **标签要先有。** 第二次探测用一个仓库里没有的标签运行 `gh issue create --label`。`gh` 拒绝了，"could not add label: 'f15-probe-missing-label' not found"，什么也没创建。所以第 8.1 节的标签必须在第一个用到它们的 issue 之前就存在。
- **没有通知。** 每个角色都通过 Troy 的账号行事（F04 D29），所以 troy-mode 做的每个 issue、评论和编辑，在 GitHub 上都是 Troy 自己的。GitHub 从不就一个人自己的操作通知他。Troy 要打开 issue 才能看到，而 troy-mode 仍然在聊天里告诉 Troy 什么在等他（第 7 节）。
- **文字未经检查就到了 GitHub。** `ZJUCao/recipe-menu#92` 上的一条审查评论，在 `check-text` 失败的情况下发了出去：命令读的是检查的输出，而不是它的退出码。F05 的 `gh` 守卫只检查 `gh pr create` 和 `gh pr edit`（F05 设计 8.2），所以现在 issue 正文和评论不经检查就能发出去。troy-pstack 的 issue #65（Troy 于 2026-11-16 批准）会扩大这个守卫（第 10 节）。
- **试运行仓库。** 在 `ZJUCao/troy-mode-trial` 里，v0.1.0 已发布；v0.2 包括已验收的 F04 "Word count command"，以及设计已合并（PR #29）的 F02 "Count lines"。它的 v0.2 测试计划有 17 个场景，全部自动运行，所以还没有需要 Troy 设备的场景。

## 3. 谁来写这些 issue（D141）

### 3.1 规则

引擎算出每个 issue 应该写什么，主会话把它发出去。这守住了 F07 的分工：引擎读 git 和 GitHub，从不写 GitHub，所有写操作由技能来做（F07 设计 3.1，F04 D29）。这样每次发出都经过 `check-text` 和 F05 的 `gh` 守卫，它们看得到主会话的工具调用，看不到一个程序自己启动的子进程。

| issue | 谁创建 | 什么时候 | 谁修改 | 怎样关闭 |
| --- | --- | --- | --- | --- |
| 进度 | 主会话，依据引擎 `issues` 的报告 | 功能成为下一个功能，或者有了阶段 PR 时（第 4.1 节） | 同上，每次同步时 | 验收时由 PR 6 的 `Closes #<n>` 关闭，同步也会关闭 |
| 想法 | Troy，在手机或网页上。Troy 在聊天里给出、troy-mode 暂不处理的想法，也由主会话创建（第 5.5 节）。 | 随时 | Troy。troy-mode 只评论和加标签。 | 由处理它的 PR 关闭，比如需求变更 PR 的 `Closes #<n>`；或者回答之后由主会话关闭（第 5.4 节） |
| 设备测试清单 | 主会话，依据引擎 `issues` 的报告 | 发布测试通过之后（第 6.1 节） | Troy 勾选。只有新一轮发布测试开始时，同步才改动文字。 | 发布 PR 合并之后，由同步关闭 |

bug 保留 bug 流程里它自己的 issue（F07 设计 11.1）：PR A 提到它，PR B 修复它，所以它的时间线已经显示了进度。

### 3.2 引擎命令 `issues`

```text
python troy_flow.py issues [--device-test-scenarios <ID>,<ID>...] [common options]
```

`issues` 像 `status` 一样读取状态，再加上仓库的标签和 issue，然后比较每个进度 issue 和清单应该是什么样、现在是什么样。它什么也不改。它的报告列出：

| 字段 | 内容 |
| --- | --- |
| `labels` | 仓库缺少的每个第 8.1 节的标签，以及创建它的 `gh label create` 命令。 |
| `actions` | 每项改动，按顺序：`create`、`edit`、`close`、`reopen` 或 `close-duplicate`，附上 issue 的种类、条目（`F04` 或 `v0.1.0`）、编号、标题和标签，它写在 `<git dir>/troy-mode/flow/issues/` 下的正文文件，以及确切的 `gh` 命令。 |
| `skipped` | 它略过了什么、为什么，比如关闭了 issue 功能的仓库。 |
| `problems` | 它不得不缩短的正文（第 8.3 节）。 |

- 正文每次都从状态重新生成，所以一次失败或没跑的同步，会由下一次修好。
- 只有标题或正文和重新生成的不同时，才会出现 `edit`。对清单来说，先读出并保留 Troy 的勾选，所以单纯勾选从不引起编辑（第 6.3 节）。
- 主会话创建补丁版本的清单时，用 `--device-test-scenarios` 指定场景，因为哪些场景被修复影响到是一个判断（F08 设计 6）。之后的同步从清单自己的文字里保留这份列表。
- 退出码和 F07 一样：能读出状态时为 0，不能时为 2。

### 3.3 `status` 增加了什么

`status` 增加一个 `issues` 部分和一个新的动作。它最多多用两次 `gh` 调用来读 issue：所有 issue，开着的和已关闭的，连同评论；以及所有 PR，开着的、已合并的和已关闭的，用来得到 `issues.pending` 需要的各阶段 PR 编号。构建时选了这两次读取，而不是开着的 issue 加所有状态的进度 issue：这样一个列表就同时用于想法、进度 issue 和清单。

- `issues.ideas`：每个开着的想法 issue（第 5.1 节）及其评论；troy-mode 还没回答过它，或者 troy-mode 上次评论之后 Troy 又写了东西时，标为 `new`。
- `issues.troy_comments`：每个进度 issue 和清单上，troy-mode 上次评论之后 Troy 写的评论。`Note for <ID>` 评论（第 8.4 节）不算 troy-mode 的上次评论，所以备注不会把 Troy 等着回复的评论盖掉。
- `issues.device_test`：开着的清单的标签版本、轮次、各个场景及其勾选、验收框，以及 `result`：`waiting`、`ticked`（每个场景和验收框都勾了），或 `incomplete`（勾了验收框，但有场景没勾）。
- `issues.pending`：`issues` 会做几项改动。
- `next.issue`：功能的进度 issue 编号，出现在 `stage` 或 `continue-pr` 条目上。
- **`ideas` 动作**（第 5.2 节）。
- PR 评论：引擎也读取 Troy 在 PR 上留的审查（review）的正文，因为 GitHub 的"Comment"审查可能就是手机上回复 PR 的方式（第 7 节）。

### 3.4 技能做什么

1. **开始时。** 在 `status` 之后、分派请求之前，运行 `issues --json` 并执行它。这样手机上改动过的 troy-mode 文字会被修好，标签也会在 Troy 开想法 issue 之前就存在。
2. **每一步之后。** 每次 `status --write-progress` 之后（F07 设计 8.2 第 8 步），马上运行 `issues --json` 并执行它。
3. **执行。** 运行 `labels` 里的每条命令。对每个动作，先用 `troy_flow.py check-text --file <file>` 检查正文文件并读取它的退出码，绝不读它的输出，再运行这个动作的命令。
4. **出了问题时**，按第 9 节：记下来，然后继续。

## 4. 进度 issue（D142）

### 4.1 哪些功能有

一个功能还没验收，并且它是顺序里的下一个功能（F07 设计 5.1）或者有阶段 PR（开着的或已合并的），它就有一个开着的进度 issue。同步会创建它，所以前一个功能一验收，下一个功能的 issue 就出现了，一项都没勾。

- 功能验收后，它的 issue 关闭（第 4.5 节）。
- 一个没有阶段 PR 的功能不再是下一个时，比如一次需求变更调整了功能顺序，同步把它的 issue 以"不计划做"（not planned）关闭；它再次成为下一个时重新打开。
- 从需求里删掉的功能也一样。
- 已验收的功能不会再有新的进度 issue。对它的改动会成为一个新功能（F07 D65），由新功能自己的 issue 跟进。

### 4.2 显示什么

标题是功能的编号和名字，中文在前：`F04 把历史导出为 CSV / Export history as CSV`；镜像里的名字和英文相同时，就是 `F04 Export history as CSV`。一个处在第 3 步的功能，正文是：

```markdown
<!-- troy-mode: progress F04 -->
**F04 把历史导出为 CSV** · v0.2 · 第 3 步，共 6 步

等你：没有。

- [x] 1/6 接口设计：#41，已合并
- [x] 2/6 测试计划：#42，已合并
- [ ] 3/6 模拟：#43，进行中。代码审查员第 1 轮：要求修改
- [ ] 4/6 测试
- [ ] 5/6 实现
- [ ] 6/6 验收

依赖：F02（#7，已验收），F03（#9，已验收）
文档：需求 · 设计 · 测试计划 · 原型（链接）

troy-mode 维护这段文字，改动会被替换。想对 troy-mode 说什么，请写评论。

<details><summary>English</summary>

**F04 Export history as CSV** · v0.2 · stage 3 of 6

Waiting for you: nothing.

1/6 Interface design: #41, merged
2/6 Test plan: #42, merged
3/6 Mock: #43, open. Code Reviewer, round 1: changes requested
4/6 Tests
5/6 Implementation
6/6 Acceptance

Depends on: F02 (#7, accepted), F03 (#9, accepted)
Documents: requirements · design · test plan · prototype (links)

troy-mode keeps this text and replaces edits to it. To reach troy-mode, write a comment.

</details>
```

- **勾选框**归 troy-mode：一个阶段的 PR 合并了，这一步就勾上。需求变更流程跳过的模拟（F07 D65）也勾上，并写明"跳过：没有新接口"。
- **阶段那一行**写出这个阶段的 PR 和它的状态。对开着的 PR，再加上最近一次审查或尝试的标题，换成固定的说法，比如"代码审查员第 1 轮：要求修改"。
- **"等你"**说明什么在等 Troy，来自 `status`："批准 #41；要决定的事在它描述的开头"，或者一次升级上报及其链接。
- **状态**是这个功能在需求文档及其镜像里的状态栏，只在它比"未开始"多说了点什么时才显示：返工期间的"需要返工（<改动>）"，以及验收时的新状态。
- **其他行**，有的时候才出现：标题里带这个功能编号的旁支 PR，比如 `[F04 test-fix]`；标题为 `Real run of F04: ...` 的 bug issue（F12 设计 D107）；没合并就关掉的阶段 PR；"需要返工"和引起它的改动；以及之前的工作给这个功能留下的备注，"备注：2 条（#31、#40）"和"Notes from earlier work: 2 (#31, #40)"，每个编号链接到它的 `Note for` 评论（F07 设计 6.6，D284）。这一行在各阶段的行之后、依赖之前。
- **链接**指向 `main` 上的文档和所依赖功能的进度 issue。issue 里从不放文档的正文或给 Troy 的摘要（第 8.3 节）。
- **没有每次同步都会变的时间戳**，所以只有真有变化时，同步才编辑正文。

### 4.3 时间线

每个阶段 PR 描述里 Why 一节的开头是 `Progress: #<n>`，PR 6 的开头是 `Closes #<n>`，编号取自 `next.issue`。这样 GitHub 会把每个阶段 PR 列进 issue 的时间线，带着标题和它是开着、已合并还是已关闭，不需要再写任何东西。即使 PR 6 之后的同步失败了，PR 6 的合并也会关闭这个 issue。

### 4.4 保持最新

同步在每次开始时和每一步之后运行，只在正文不同时才编辑。troy-mode 在进度 issue 上不写评论，除了回复 Troy（第 7 节）和给后续功能的备注（F07 设计 6.6）；备注从不编辑或删除。Troy 改了正文或标题，下一次同步会把 troy-mode 的文字放回去。功能还没验收时 Troy 关掉了这个 issue，下一次同步会重新打开它。想对 troy-mode 说什么，Troy 就写评论。

### 4.5 验收时关闭

PR 6 的合并会关闭这个 issue，见第 4.3 节。下一次同步再生成一次正文：6 项全勾，加上功能的新状态，比如"在 Troy 的电脑上真实运行过"；如果它还开着，就以"已完成"关闭。即使 PR 6 的 `Closes #<n>` 已经把它关闭，同步也会再生成一次；`6/6` 一项勾上了，就说明它已是最终的样子。之后同步不再动已关闭的进度 issue。后来的状态，比如版本验收后的"在 Troy 的设备上可用"，显示在需求文档里和这个版本的清单上（第 6.2 节）。

## 5. 想法 issue（D143）

### 5.1 Troy 怎么写

- **在 GitHub 上，用手机或网页**，Troy 从模板"Idea / 想法"新开一个 issue，模板会加上 `idea` 标签。troy-init 把这个模板加为 `.github/ISSUE_TEMPLATE/idea.md`（第 11 节）。Troy 用什么语言写都行，长短和聊天里的一条消息一样。
- **没有标签的 issue** 也算想法。troy-mode 开的每个 issue 都有标签，所以 troy-mode 项目里没有标签的 issue 就是 Troy 的。app 不提供模板，或者 Troy 忘了用，也不会丢：troy-mode 回答时会加上 `idea` 标签。
- **之后再补充。** Troy 加一条评论。troy-mode 看得到新评论，看不到对最初那段文字的修改。

### 5.2 troy-mode 什么时候读

Troy 不在时什么都不运行。下一次 troy-mode 运行时，`status` 列出新想法（第 3.3 节），并在下一个自然停顿处给出 `ideas` 动作：

- 在已经开始的工作之后：开着的 PR、记录批准或验收的 PR、bug 的 PR B、需求变更后的返工、进行中的发布、打标签、回顾，以及规则的清理；
- 在下一件新事之前：关于之后由谁批准的那个问题（F07 D62）、版本测试计划、还没开始的发布、一个功能的第一步，或"所有功能都已验收"。

所以想法从不在一个功能的两步之间打断它，而需求变更会排在它可能改动的下一个功能之前。Troy 的请求点名了某个想法时，比如"idea #101"或"change: #101"，troy-mode 马上处理它。请求到此为止时（F07 D63），想法等下一次运行，报告里会说还有几个没处理。

### 5.3 产品经理怎么处理

主会话以产品经理的身份（新任务 PM6）读每个新想法及其评论，判断它是什么，并用 Troy 写它时用的语言发一条评论说明。评论的第一行是固定的英文标题，这样引擎能把 troy-mode 的评论和 Troy 的区分开（F07 设计 8.4）：

| 想法是 | 标题 | 接下来 |
| --- | --- | --- |
| 需求变更 | `Idea: requirement change` | 用一两句话说明改动。然后在 `troy-mode/change-<slug>` 上做 PM2，把这个想法放进 Input。变更 PR 的描述对它吸收的每个想法写 `Closes #<n>`，并像每次需求变更一样等 Troy 批准（F07 设计 11.2）。改动同一批功能的几个想法可以放进一个变更 PR。 |
| bug | `Idea: bug` | 用 `bug` 标签换掉 `idea`，这个 issue 就成为 bug `B<n>`（F07 设计 11.1）。它等 bug 流程：Troy 要求修它，或者下一次发布先修掉它（F08 D74）。 |
| 规则 | `Idea: rule` | 规则变更流程（F09），在写任何东西之前先问 Troy（F09 D82）。 |
| 一个问题，或者 troy-mode 不会去改的事 | `Idea: answered` | 回答，然后主会话关闭这个 issue。关于 troy-mode 本身、而不是这个项目的事，回答 Troy 可以怎么做：一条适用于所有项目的规则（F09 D83）。 |
| Troy 在里面说了以后再做 | `Idea: later` | 什么也不做，直到 Troy 再评论或点名它。 |
| 不清楚 | `Waiting for Troy: <question>` | 一个问题，附推荐答案。`status` 把它列为在等 Troy。 |

分类不会比各个流程本来问得更多：需求变更等 Troy 批准它的 PR，规则等 Troy 点头。其他种类都不问 Troy 就继续（需求文档 3.3）。

### 5.4 关闭

- **需求变更：**变更 PR 合并时关闭这个想法。主会话随后评论 `Idea: in the requirements`，写出新增或改动的功能，以及它们有了之后的进度 issue。
- **被否决：**Troy 拒绝这个改动时，主会话评论 `Idea: answered`，附上 Troy 的原话，然后关闭想法。
- **bug：**PR B 的 `Fixes #<n>` 关闭它（F07 设计 11.1）。
- **规则：**规则 PR 的描述写 `Closes #<n>`。
- **已回答：**回答后关闭。
- **Troy 关闭的：**troy-mode 不再处理它。如果为它开的变更 PR 还开着，troy-mode 问 Troy 要不要一并关掉那个 PR。

### 5.5 聊天里暂缓的想法

Troy 在聊天里给出一个 troy-mode 现在不处理的想法时，比如因为有 PR 开着（F07 设计第 4 节"一次一个 PR"），或者 Troy 说了"以后再说"，主会话为它开一个想法 issue，写上 Troy 的原话，这样会话结束后也不会丢。troy-mode 马上处理的请求不开 issue。

## 6. 设备测试清单（D144）

### 6.1 什么时候创建

在 F08 的第 5 步、Troy 的测试（F08 设计 5.6），发布测试通过之后：`status` 给出发布步骤 `troy-test`，下一次同步创建清单。主会话随后像现在一样在聊天里告诉 Troy，附上清单的链接。

- **每个版本一个。** 修完 bug 后新一轮发布测试，改的是同一个 issue（第 6.3 节）。
- **补丁版本**只列修复影响到的场景，由主会话用 `--device-test-scenarios` 指定（F08 设计 6）。
- **没有 Troy 场景的版本**也有一个，只有验收框，让 Troy 可以在手机上验收。

### 6.2 显示什么

标题：`v0.1.0 在你的设备上测试 / Test v0.1.0 on your devices`。正文，有删节：

```markdown
<!-- troy-mode: device-test v0.1.0 -->
**在你的设备上测试 v0.1.0** · 第 1 轮 · 要测的提交：34a7728
发布 PR：#94 · 更新记录 · 版本测试计划（链接）
功能：F01 到 F13，自动场景全部通过。

测完一项、结果和预期一样，就勾上它。哪一项不对，就不勾，写一条评论说明。全部通过后，勾最后一项。

- [ ] **v0.1-S24 安装发布版本，在两种 shell 里从任何文件夹运行。**
  设备：你的电脑。
  步骤：1. … 2. … 3. …
  预期：两个标签页都显示 `recipe-menu 0.1.0`。
- [ ] **v0.1-S25 Windows Terminal 里中文显示正确。** …
- [ ] **v0.1-S26 在手机上勾选购物清单。** …
- [ ] **我接受 v0.1.0。**

<details><summary>English</summary>

**Test v0.1.0 on your devices** · run 1 · commit to test: 34a7728
...
v0.1-S24 Install the release and run it from any folder, in both shells.
Device: your PC. Steps: 1. … Expected: …
...

</details>
```

- Troy 运行的每个场景，取自版本测试计划的第 2 和第 3 节，带编号、标题、设备、步骤和预期结果。中文取自计划的镜像，英文取自计划本身，都照原样。计划仍是事实来源；清单是给手机用的副本。
- 要测的提交，取自发布测试的评论 `Release test, run <n>: passed`，以及发布 PR、更新记录那一节和计划的链接。
- 这个版本的功能，一行，带它们的状态。
- 验收框在最后。troy-mode 从不勾清单里的任何一项。

### 6.3 勾选、失败和验收

| Troy | troy-mode 在下一次运行时 |
| --- | --- |
| 勾上每个场景和验收框 | `device_test.result` 是 `ticked`。主会话在发布 PR 上发出 `Release test by Troy, run <n>: accepted`，把 Troy 在清单上的评论作为 Troy 的备注，然后继续验收（F08 设计 5.7）。 |
| 有一个场景没勾，并写了评论 | 主会话读这条评论。失败就记为 `Release test by Troy, run <n>: failed`，附上 Troy 的原话，交给测试经理分类（F08 设计 5.8）。问题或备注就用 `Reply to Troy` 回复。 |
| 勾了验收框，但有场景没勾 | `result` 是 `incomplete`。主会话在清单上用 `Waiting for Troy: <question>`、也在聊天里，问 Troy 是什么意思。 |
| 勾了几项就停下了 | 什么都不变。发布继续等 Troy。 |

**新的一轮。**修完 bug 后，发布测试再跑一次（F08 设计 5.8）。通过后，同步更新清单：轮次和提交；清掉验收框；取消勾选 `Release test by Troy, run <n>: failed` 评论里点名的场景；保留 Troy 的其他勾选，因为 Troy 只重测失败的部分（F08 D74）。主会话在清单上发出 `Device test, run <n>: ready`，列出要重测的场景，并在聊天里告诉 Troy。

### 6.4 聊天照样可用

Troy 仍然可以像现在一样在聊天里或发布 PR 上回复（F08 设计 5.6）。在那里给出的验收不需要勾选。这时清单随发布一起关闭。

### 6.5 随发布关闭

发布 PR 合并之后，下一次同步把清单以"已完成"关闭。它的勾选和评论留下来，作为 Troy 这次测试的记录，和版本测试计划里的验收记录放在一起。

## 7. 从手机回复（D145）

Troy 不在时什么都不运行。Troy 的编辑和评论等到 troy-mode 下一次在电脑上运行时才被读到，比如 `/troy-pstack:troy-mode continue`，`status` 会先读它们。

| Troy 在手机上 | troy-mode 在下一次运行时 |
| --- | --- |
| 开一个 issue，用模板或者不加标签 | 一个想法（第 5 节）。 |
| 在想法上评论 | 和想法一起读：更多细节，或者对 troy-mode 所提问题的回答。 |
| 在进度 issue 上评论 | 当成聊天里的一条消息来读。问题用 `Reply to Troy` 评论回答。关于开着的 PR 的意见，交给那个 PR 的作者作为 Input，和现在 Troy 的 PR 评论一样（F07 设计 8.4）。新的请求当作想法处理。 |
| 在等 Troy 的 PR 上评论，或者在上面留一条"Comment"审查 | Troy 的回复，和在聊天里完全一样："全按推荐"、"all as recommended"或"approved"就是批准这个 PR；选了别的方案就是要求修改（F07 D61，F14 设计 5.4）。描述的 What 写明 Troy 是在评论里批准的。 |
| 在另一个开着的 troy-mode PR 上评论 | 和现在一样，作为它作者的 Input。 |
| 合并一个等 Troy 的 PR | 和现在一样：troy-mode 用一个 `[docs]` PR 记录批准（F07 D61）。 |
| 在设备测试清单上勾选或评论 | 第 6.3 节。 |
| 改了 troy-mode 的文字或标题，或者关掉了进度 issue 或清单 | 下一次同步时替换回去，或者重新打开（第 4.4 节）。 |
| 关掉一个想法 | 第 5.4 节。 |

troy-mode 在 issue 上回复一条评论时，用 Troy 写那条评论的语言，放在固定的英文标题下面（第 8.4 节）。PR 上的评论仍然用英文，和现在一样。

## 8. 标签、语言，以及 issue 里放什么（D146）

### 8.1 标签

| 标签 | 用在 | 颜色 | 说明 |
| --- | --- | --- | --- |
| `idea` | Troy 的想法 | `FBCA04` | `An idea or change for troy-mode to take in / 交给 troy-mode 的想法或改动` |
| `progress` | 进度 issue | `1D76DB` | `A feature's progress, kept by troy-mode / 功能进度，由 troy-mode 维护` |
| `device-test` | 设备测试清单 | `0E8A16` | `What Troy tests on Troy's devices for a release / 发布前 Troy 在自己设备上测的项目` |

- `bug` 照 F07 的用法不变。GitHub 在每个新仓库里都会创建它。
- 主会话依据 `issues` 的报告创建缺少的标签。已经存在的标签它从不改，所以 Troy 自己建的标签保持原来的颜色。
- 引擎靠标签和正文的第一行找到 troy-mode 的 issue：`<!-- troy-mode: progress F04 -->` 或 `<!-- troy-mode: device-test v0.1.0 -->`，GitHub 不显示这一行。Troy 改了标题，也不会找不到这个 issue。

### 8.2 语言

Troy 在手机上读这些 issue，先读中文，和给 Troy 的摘要一样（F14 D135）：

- **正文**中文部分在前，英文部分放在折叠的"English"块里。勾选框只在中文部分，所以每个框只有一个。
- **固定的说法**，比如阶段名、审查结果和"等你"，来自引擎里的一张表，两种语言都有。
- **来自文档的文字**，比如功能名、状态和场景步骤，取自各文档及其镜像。
- **标题**两种语言都有，中文在前。
- **troy-mode 在 issue 上的评论**用 Troy 写的语言，放在英文标题下面。PR 评论仍用英文。
- **想法模板**用两种语言提示。

### 8.3 issue 里放什么、链接什么

| 放在 issue 里 | 只放链接 |
| --- | --- |
| 从状态生成的行：阶段、PR 编号、审查标题、状态、什么在等 Troy | `main` 上的每份文档：需求、设计、测试计划、版本测试计划、更新记录、原型 |
| Troy 的场景，从版本测试计划及其镜像复制 | 各个 PR（按编号），以及 PR 描述开头的给 Troy 的摘要 |
| troy-mode 的简短评论：分类、回复、新的一轮 | PR 6 描述里的真实运行报告 |

- **issue 里从不放：**除 Troy 的场景行以外的文档正文、给 Troy 的摘要、代码、日志、文档里本来没有的本地路径，以及密钥（需求文档 8，隐私）。
- **长度。**引擎让每段正文都少于 60,000 个字符，低于 GitHub 的 65,536（第 2 节）。清单复制的步骤会超出时，每个场景保留编号、标题和预期结果，步骤改为链接到计划里的那一行，`issues` 在 `problems` 里报告这次缩短。`check-text` 拒绝超过 65,536 个字符的文件（第 10.1 节）。试点的清单大约有 4,000 个字符。
- **链接**用完整 URL，`https://github.com/<owner>/<repo>/blob/main/<path>`，因为 issue 里相对链接不起作用。

### 8.4 troy-mode 在 issue 上评论的标题

每个都放在评论的第一行，这样 `status` 能把 troy-mode 的评论和 Troy 的区分开：

- `Idea: requirement change`、`Idea: bug`、`Idea: rule`、`Idea: answered`、`Idea: later` 和 `Idea: in the requirements`（第 5 节）；
- `Waiting for Troy: <question>`（F07 的标题）；
- `Reply to Troy`；
- `Device test, run <n>: ready`（第 6.3 节）；
- `Note for <feature ID>, from <source>`，在进度 issue 上，用英文，因为是角色来读（F07 设计 6.6）。

## 9. gh 或网络出问题时（D147）

进度 issue 和清单是视图。流程从不因为其中一个写不进去而停下，下一次同步会修好它。从 Troy 那里读的东西从不靠猜。

| 出问题的是 | troy-mode 怎么做 |
| --- | --- |
| 创建标签，或者创建、编辑、关闭、重新打开 issue | 用 `status --note "Issue sync failed: <what>"` 记下来，在下一次给 Troy 的报告里说明，然后继续。下一次同步重新生成视图，再试一次。 |
| agent 的权限拒绝了一条 `gh issue` 或 `gh label` 命令 | 告诉 Troy 一次要加哪条权限规则，比如 `Bash(gh issue *)` 和 `Bash(gh label create *)`，然后像上面一样继续。它从不绕过拒绝。 |
| `check-text` 在一段正文或一条评论上失败 | 什么都不发。引擎生成的正文出错是 troy-mode 自己的错误，troy-mode 告诉 Troy。评论就改写。 |
| `status` 读不到 issue | `issues.error` 写明原因。没有 `ideas` 动作，也不从清单接受验收。`status` 的其余部分照常，流程继续。 |
| `gh` 或 GitHub 完全不可用 | 和现在一样：`status` 需要 `gh` 读 PR，以退出码 2 停下，也没有 PR 能合并。 |
| 仓库关闭了 issue 功能 | `issues` 在 `skipped` 里报告，F15 在那里什么都不做。聊天照旧。 |
| 一次创建成功了，但回复丢了，于是一个功能或版本有了两个 issue | 下一次同步靠第一行找到两个，保留较早的，把较新的以"Duplicate of #<n>"关闭。 |
| 清单创建不了 | 主会话像 F08 现在这样在聊天里告诉 Troy 那些场景，Troy 在聊天里回复。 |
| Troy 勾选的同时 troy-mode 在编辑清单 | troy-mode 只在新一轮开始时编辑清单，那时 Troy 已经报告了失败、在等修复，所以很少发生。那次勾选可能丢失；Troy 看到它没勾，再勾一次。 |

## 10. 检查和 hook（D148）

### 10.1 `check-text`

- 主会话在发出每个正文文件和每条评论之前，都用 `troy_flow.py check-text --file <file>` 检查，并读取它的退出码。在 #92 里读的是输出，于是一次失败的检查也被发了出去。
- 文件超过 65,536 个字符时，`check-text` 也失败，这样 GitHub 会拒绝的内容会先被拦下。

### 10.2 F05 的 `gh` 守卫

troy-pstack 的 issue #65（Troy 于 2026-11-16 批准）扩大了 R19 和 F05 的守卫：在主会话发出之前，hook 检查 `gh issue create`、`gh issue edit`、`gh issue comment`、`gh pr comment`、`gh pr review`、`gh pr merge`、`gh release create` 和 `edit`，以及带字段的 `gh api` 的文字，读不到文字时一律拒绝。F15 通过这些命令发出内容，需要这个检查。F15 在它的表里再加上：

| 命令 | hook 检查的文字 |
| --- | --- |
| `gh issue close`、`gh issue reopen` | `--comment` 和 `-c` |
| `gh label create`、`gh label edit` | `--description` 和 `-d` |

并且在 troy-mode 项目里，对每个调用者都拒绝 `gh issue delete` 和 `gh label delete`：删除不可撤销，也不在 troy-mode 的权限之内（F07 设计 9）。

角色在 GitHub 上仍然只读。F05 给子代理的列表只允许 `gh issue view`、`gh issue list` 和 `gh issue status`（F05 设计 7.3），所以没有角色会写 issue。

### 10.3 其他检查

- **没有新的 R 规则。**按 #65 扩大后的 R19 覆盖 issue 和评论。troy-check 的 CI 检查不变，因为 issue 从不进入仓库。
- **想法模板**在 `.github/` 里，属于 `config` 路径类，R20 不扫描它（F06 设计 4.2）。
- **引擎的测试**精确检查每个生成的正文、每个解析出的勾选，以及每个同步决定（第 13.1 节）。
- **不检查：**主会话的分类对不对，回复够不够平实。这两样 Troy 都会读到。

## 11. 位置和对之前功能的改动

```text
skills/troy-mode/SKILL.md          新的一节"Issues for Troy"（第 3 到第 9 节）；Start、One stage、Merging、Version release、Comments、Escalation、Routing 和 Continue
troy-mode/
  flow/
    troyflow/                      issues 命令及其模块（由开发者决定）
    troyflow/github.py             读 issue、新的评论标题、Troy 在 PR 上的审查
    troyflow/status.py, nextstep.py   issues 部分、next.issue 和 ideas 动作
    troyflow/textcheck.py          长度检查
    troyflow/cli.py                issues 命令
    tests/                         第 13.1 节的测试
  templates/
    progress-issue.md              新增：进度 issue 的格式，两种语言
    device-test-issue.md           新增：清单的格式，两种语言
    idea-issue.md                  新增：GitHub 的想法 issue 模板
    README.md, .zh-CN.md           列出这三个
  roles/product-manager.md         PM6 想法；PM2 以想法为输入
  init/troyinit/                   初始化和升级写入 .github/ISSUE_TEMPLATE/idea.md
  hooks/troyhook/ghcmd.py          第 10.2 节的命令
docs/troy-mode/guide/              第 01、03、04、05、07 和 08 页，两种语言
.claude-plugin/plugin.json         下一个次版本号（第 12 节）
```

| 功能 | 改动 |
| --- | --- |
| F01 模板 | 三个新模板。`progress-issue.md` 和 `device-test-issue.md` 给出正文的格式，由引擎在代码里生成，就像 `progress.md` 给出进度文件的格式。每个都包含两种语言，中文在前，和 `summary-for-troy.md` 一样。`idea-issue.md` 是 GitHub 的 issue 模板：front matter 有 `name: Idea / 想法`、`about` 和 `labels: idea`，正文两行，请 Troy 用任何语言写下想法。README 的表格列出它们。 |
| F04 角色 | 产品经理的新任务 PM6 想法：什么时候做、第 5.3 节的种类，以及评论标题。PM2 以想法 issue 为输入，它的 PR 写 `Closes #<n>`。代理文件都不变。 |
| F05 hook | 第 10.2 节的命令，在 #65 的改动之上。`hooks.json` 不变。 |
| F06 troy-init | 初始化和升级用 `idea-issue.md` 写入 `.github/ISSUE_TEMPLATE/idea.md`，就像写入 `.github/pull_request_template.md` 一样，按同样的哈希规则（F06 设计 6）。troy-init 不创建标签。 |
| F07 入口技能 | 引擎的 `issues` 命令和 `status` 增加的部分（第 3 节）。技能："Issues for Troy"；Start 运行同步；One stage 的第 5 步把 `Progress: #<n>` 或 `Closes #<n>` 放在 Why 的开头，第 8 步运行同步；Merging 从 PR 评论或审查里读取 Troy 的回复（第 7 节）；Comments 列出 issue 上的标题；Escalation 的权限增加写 issue 和标签；Routing 增加"idea #<n>"；Continue 增加 `ideas`。`check-text` 增加长度检查。 |
| F08 发布 | 第 5 步通过同步创建清单，`ticked` 的清单就是 Troy 的验收。新的一轮会更新它（第 6.3 节）。`status` 里这个发布步骤的说明会提到清单。 |
| F10 指南 | `01-install.md`：第 9 节的权限规则。`03-features.md`：进度 issue。`04-bugs-and-changes.md`：想法。`05-release.md`：清单。`07-taking-part.md`：在手机上工作，以及 GitHub 不会为 troy-mode 的写操作发通知。`08-reference.md`：标签、`issues` 命令和评论标题。每页两种语言。 |

不改动任何上游 pstack 文件。F02、F03、F09、F12、F13 和 F14 不变。

## 12. 已有项目和插件版本（D149）

F15 的构建 PR 提高插件的次版本号，合并时取下一个空闲的：如果之前没有别的改动提高过，就是 0.6.0（F10 D89）。F19 用了 0.6.0，#65 用了 0.6.1，所以 F15 带来 0.7.0。然后：

1. **Troy 更新插件**并重启 Claude Code（F10 设计 6）。#65 的改动同一天合入时，一次更新就把两者都带来。
2. **项目里第一次运行 troy-mode** 时，创建这些标签和当前或下一个功能的进度 issue，并读取 Troy 的想法。它不需要项目里的任何文件：技能、引擎和 hook 都随插件而来。
3. **`upgrade troy-mode`** 通过 troy-init 的 `[rules] Upgrade troy-mode to <version>` PR 带来想法模板和新模板，troy-init 合并它（F06 设计 6）。在那之前，Troy 把想法写成一个不加标签的 issue。`origin/main` 上没有 `.github/ISSUE_TEMPLATE/idea.md` 时，`status` 会提一句，因为它对项目副本的检查只覆盖 troy-check。
4. **不补建。**已验收的功能没有进度 issue，已发布的版本没有清单，之前聊天里的想法也没有 issue。

对 `ZJUCao/recipe-menu`：v0.1.0 已发布，v0.2 包括还没开始的 F14 到 F16。更新之后，第一次运行会创建这三个标签和 F14 的进度 issue，一项都没勾。v0.2 的发布带来第一个清单。如果桌面应用的自动模式拒绝 `gh issue` 命令，Troy 加上第 9 节的规则，就像试点为 amend 和强制推送做的那样（troy-pstack #50）。

## 13. F15 怎样检查（D150）

### 13.1 测试

由另一个代理在代码存在之前依据本设计编写测试，沿用 F07 的做法：一个带本地裸仓库 `origin` 的临时 git 仓库，以及 `PATH` 上一个假的 `gh`，它从一个 JSON 文件提供 PR、评论、审查、issue 和标签，并记录每次调用（F07 设计 14.1）。

| 组 | 用例包括 |
| --- | --- |
| 进度 issue | 为下一个功能创建、一项都没勾，以及为有阶段 PR 的功能创建。已合并阶段的勾选，提交标题来自 rebase、squash 和合并提交三种方式。跳过的模拟。返工和重做。开着的 PR 最近的审查标题，换成固定说法。来自 `Waiting for Troy` 评论的"等你"。列出旁支 PR 和真实运行的 bug。没有变化时不编辑。Troy 改了正文或标题后编辑。Troy 关闭后重新打开。不再是下一个时以"不计划做"关闭，再次成为下一个时重新打开。PR 6 之后以"已完成"关闭。从不为已验收的功能创建。 |
| 想法 | 带 `idea` 标签和没有标签的 issue 都算；`bug`、`progress` 和 `device-test` 的 issue 不算。直到 troy-mode 写了带标题的评论之前都是 `new`，Troy 再写后又是 `new`。`ideas` 动作出现在功能的第一步、版本测试计划、还没开始的发布和 `all-accepted` 之前；从不出现在两步之间、开着 PR 时或进行中的发布期间。 |
| 清单 | 在 `troy-test` 时创建，包含 Troy 在第 2 和第 3 节的场景，两种语言，验收框在最后。补丁版本指定的场景在多次同步间保持。没有 Troy 场景时只有验收框。结果 `waiting`、`ticked` 和 `incomplete`。单纯勾选不引起编辑。新的一轮清掉验收框、取消勾选失败评论里点名的场景、保留其他勾选，并更换提交。发布 PR 合并后关闭。 |
| 标签和文字 | 缺少的标签给出创建命令；已有的从不改。两种语言，中文在前，勾选框只出现一次。没有时间戳。完整 URL。超过 60,000 个字符的正文被缩短，并报告一个问题。重复的 issue 被关闭，保留较早的。关闭了 issue 功能：略过。 |
| 读取 Troy 的输入 | 等 Troy 的 PR 上的评论和审查结束等待，并进入 `troy_comments`。Troy 在进度 issue 和清单上的评论。第 8.4 节的每个新标题都算 troy-mode 的。Troy 评论之后的 `Note for` 评论不会把 Troy 的评论移出 `troy_comments`。 |
| 备注（F07 D284） | 目标功能的进度 issue 上的备注一行，两种语言，每条备注一个链接；没有备注时没有这一行。关闭的进度 issue 上的备注也算。 |
| `check-text` | 65,537 个字符的文件失败，65,536 个字符的通过。 |
| hook | 第 10.2 节的每条命令，长短两种写法，带归属信息时拒绝，不带时放行。对主会话和角色都拒绝 `gh issue delete` 和 `gh label delete`。 |
| 技能、模板、初始化 | 技能提到 `issues`、各个标题和第 3.4 节的步骤。三个模板及其 README 行。初始化和升级写入想法模板，升级只在它没被改过时替换。 |

### 13.2 埋 bug

代码通过之后，在一个临时副本里一次埋一个 bug，每个都必须让某个测试失败。包括：为已验收的功能创建进度 issue、用开着的 PR 勾选阶段、跳过的模拟没勾、没有变化也编辑正文、Troy 关闭后不管、已关闭的进度 issue 又被编辑、没有标签的 issue 不算想法、`bug` issue 被算作想法、`ideas` 动作出现在两步之间、同步时丢掉 Troy 的勾选、新的一轮保留验收框、有一个场景没勾也算 `ticked`、引擎勾了清单、在标签存在之前就用它、改动已有的标签、长度上限按字节算、保留了较新的重复 issue、忽略 Troy 在等待中的 PR 上的审查、`check-text` 的长度检查差一个，以及 `gh issue close --comment` 未经检查就放行。F07 的 D284 到 D287 加上：备注被算作 troy-mode 对 Troy 的回复，以及备注那一行显示在来源功能的 issue 上而不是目标功能的。数量写进构建 PR 的描述。

### 13.3 试运行

构建 PR 开出之前，F15 在 Troy 的电脑上用嵌套的 `claude -p` 会话运行，troy-pstack 从 PR 分支加载，在 `ZJUCao/troy-mode-trial` 上，依据 Troy 对 troy-mode 试运行的长期许可（F08 设计 11.3）。插件里必须先有 #65 的改动。试运行脚本扮演 Troy 的手机：它以 Troy 的身份用 `gh` 开 issue、评论和勾选，试运行的答案文件给出 Troy 在聊天里的回答。

1. **第一次同步。**第一次运行创建三个标签和 F02 的进度 issue，第 1 步已勾（PR #29），下一步是第 2 步。
2. **升级。**"upgrade troy-mode"通过它的 PR 带来想法模板。
3. **想法。**试运行脚本开两个 issue：一个带 `idea` 标签，要求在新版本 v0.3 里给 `wordcount` 加一个 `--lines` 选项；一个不加标签，问 `count_lines` 是不是一次读入整个文件。troy-mode 回答第二个并关闭它，把第一个变成一个写着 `Closes #<n>` 的变更 PR。Troy 在答案文件里批准它。它合并后关闭这个想法。
4. **F02 的第 2 到第 6 步。**进度 issue 每一步都更新，每个阶段 PR 以 `Progress: #<n>` 开头，PR 6 关闭它。在两步之间，试运行脚本像误触那样改掉 issue 的正文并关闭它，再用中文评论一个问题。下一次同步把它恢复并重新打开，troy-mode 在 `Reply to Troy` 下用中文回答。
5. **一次被拒绝的写入。**有一个会话带着 `--disallowedTools "Bash(gh issue edit:*)"` 运行。troy-mode 报告这次拒绝和要加的规则，然后继续，下一个会话把它补上。
6. **发布 v0.2.0。**一个事先准备好的 `[docs] Update the v0.2 test plan` PR（在试运行之前做好）加入一个由 Troy 运行的场景：对一个含中文的文件运行 `wordcount`，在 Windows Terminal 里看结果。发布测试通过后，清单出现，会话停下。试运行脚本勾上这个场景和验收框，就像 Troy 的手机会做的那样。一个新会话收到"continue"，读到勾选，在发布 PR 上记录验收，合并它，创建 release，并关闭清单。
7. **事实。**从会话记录和 GitHub 上看：每段正文发出前都通过了 `check-text`，没有会话问 Troy 答案文件没覆盖的问题，每个 issue 的时间线都列出了它的 PR。如果某个事实和本设计不同，就在构建 PR 里更新设计。

大约需要 13 次角色运行：TM1 加 IF3、DV1、CR1、TE1、TM2、CR1、DV2、CR1，然后是版本测试的 TE5、TM2 和 CR1，变更需要时再加 AR4。按 F08 试运行的花费，大约 13 到 20 美元，另加约 11 个 PR 的 Actions 分钟数。如果试运行时 Troy 在电脑旁，Troy 用 GitHub app 勾一下它清单里的一项，就能看出 app 能不能勾 issue 里的框；否则由试点的 v0.2 来看。仓库、它的 issue 和 release 都保留。删不删由 Troy 决定。

### 13.4 状态

| 什么时候 | F15 在需求文档 7.2 中的状态 |
| --- | --- |
| 试运行通过后构建 PR 合并 | 在样例项目上运行过：在一个临时 GitHub 项目上，troy-mode 让一个功能的进度 issue 跟完了它的 6 个 PR，把 Troy 开的两个 issue 变成一次改动和一个回答，并根据 Troy 勾满的清单验收了一个版本。还没在真实项目上用过。 |
| 试点有了进度 issue、想法或清单 | 在真实项目上用过：<`ZJUCao/recipe-menu` 的哪些 issue，以及 Troy 用它们做了什么>。 |

如果构建 PR 之前没法试运行，状态就是"已编写"，直到试运行完成。状态更新单独一个 PR。

### 13.5 试运行的结果（2026-11-17）

试运行在 `ZJUCao/troy-mode-trial` 上用七个嵌套会话进行，tstack 从构建分支加载，已安装的插件关闭。按标价共 $18.56，在估计范围之内，角色运行 15 次（DV1、CR1；TE1、TM2、CR1 各两次，DV2、CR1、AR4；TE5 两次，TM2、CR1）。

| 步骤 | 发生了什么 |
| --- | --- |
| 1. 首次同步 | 建了 `idea`、`progress` 和 `device-test` 三个标签，以及 F02 的进度 issue #49：第 1 步已勾（#29），第 2 步进行中（#48），"等你：批准 #48"。 |
| 2. 升级 | `[rules] Upgrade troy-mode to 0.7.0`（#50）带来了 `.github/ISSUE_TEMPLATE/idea.md` 和 #65 的 R19 文字，并已合入。 |
| 3 和 4. 想法和 F02 | Troy 在聊天里批准 #48；接着是模拟（#54）、测试（#55）、实现（#56）和验收（#57）。每个阶段 PR 的 Why 以 `Progress: #49` 开头，PR 6 以 `Closes #49` 开头，#49 的时间线列出了 #48 和 #54 到 #57。在两步之间，试运行脚本改了 #49 的文字、关闭了它，并用中文提了一个问题：下一个会话重新打开了它，并在 `Reply to Troy` 下用中文回答。F02 处于两步之间时，两个想法一直等着。F02 验收后，同一个会话处理了它们：#52（无标签，中文问题）得到 `Idea: answered` 并被关闭；#51（`idea`）变成带 `Closes #51` 的修改 PR #58，按 Troy 的批准合入，`Idea: in the requirements` 写明了 F05 和它的进度 issue #59。 |
| 5. 被拒绝的写入 | 第 3、4 步的会话运行时 `gh issue edit` 被拒绝。它说明了要加的规则，记下失败，然后继续；下一个会话把 #49 再生成一次最终的样子（6/6），并保持关闭。 |
| 6. 发布 v0.2.0 | 版本测试 #60、发布 PR #61，发布测试在 Troy 的电脑上通过；同步创建了清单 #62，里面是 Troy 的场景 v0.2-S18 和接受框。试运行脚本勾上了两项。下一个会话在 #61 上发了 `Release test by Troy, run 1: accepted`，合入它，创建了 GitHub release v0.2.0，并以"已完成"关闭了 #62。 |
| 7. 事实 | 40 次带正文文件的发出，每次都先用 `check-text` 检查，并读取了退出码。hook 拒绝了两次 `gh pr create`，它们的文件用 `$(git rev-parse --absolute-git-dir)/...` 指定，正如 F05 设计第 8.2 节所说；会话随后用路径发出。没有会话问过 Troy 答案文件没覆盖的问题。 |

**试运行和第 13.3 节的不同之处。**

1. 仓库已经往前走了：`main` 在 `2c2940c`，F02 的测试计划 PR #48 开着、等 Troy 批准，tstack 0.6.0，`troy_approves_first = 4`。所以首次同步显示第 2 步在等 Troy，Troy 对 #48 的批准在第三个会话的请求里给出。
2. 两个想法是在升级之后、F02 处于两步之间时开的。按 D143，troy-mode 在 F02 验收之后才处理它们，所以第 3 步排在第 4 步之后。验收 F02 的会话接着处理了想法，它判断"continue"到达了这个自然停顿点。
3. 被拒绝的写入（第 5 步）和 F02 的最后几步、想法在同一个会话里进行。
4. 事先准备的 `[docs] Update the v0.2 test plan` PR（#53）还把 v0.2-S11、v0.2-S12 和 v0.2-S17 中文件错误的退出码改成了 2，这是 F04 的设计和 ADR-0002 决定的；方案里仍写着 1，这从 F12 起就已知道。
5. 发布会话在 TE5 期间碰到套餐的 5 小时用量上限而停下，之后用 `--resume` 恢复；它从被打断的草稿出发重新运行了 TE5。
6. Troy 不在电脑前，所以没有做在 GitHub 应用里勾选的可选步骤。
7. 前三个会话用的是这个分支较早的构建：两个模板文件里有乱码，只影响它们的参考文字；写成 `[X]` 的勾选会引起一次编辑。两处都在第四个会话之前修好了。

**试运行带来的构建改动。** 清单按原样复制每个场景的单元格，包括代码标记：#62 丢了方案里的反引号，因为引擎的表格读取会去掉它们，现在有测试检查。镜像里的名字和英文相同时，进度 issue 的标题是 `<编号> <名字>`，试运行的需求就是这样。hook 拒绝用 `$(...)` 指定的文件时，原因现在会说明这一点，技能也要求用路径指定正文文件。

**后续事项，这里没有修。** 发布 PR 合入后，`status` 的 `waiting_on_troy` 仍带着"PR #61: Waiting for Troy: accept v0.2.0"，来自进度文件沿用的文字（F08 的发布流程）。被拒绝的 `gh issue edit --add-label idea` 不会再试，所以 #52 一直没有标签。在试运行项目里，F02 测试计划的 F02-T09 一行丢了设计示例文件中的一个 U+2028 字符。

## 14. F15 和需求的对应

| 需求 | F15 在哪里覆盖 |
| --- | --- |
| F15 行：每个新想法或改动请求一个带 `idea` 标签的 issue，由产品经理变成需求变更 | 第 5 节 |
| F15 行和 3.3：每个功能一个进度 issue，把 6 个 PR 列成勾选清单，每个阶段更新，验收时关闭 | 第 4 节 |
| F15 行和 5.5 第 3 步：每个版本一个清单 issue，边测边勾 | 第 6 节 |
| F15 行：文档留在仓库里 | 第 1 和第 8.3 节 |
| 3.3：Troy 参与的环节；其他步骤不问 Troy 就继续 | 第 5.3 和第 7 节 |
| 5.4 第 1 步：在想法 issue 里提出的改动 | 第 5.2 和第 5.3 节 |
| 5.10：从状态接续 | 第 3.1 和第 4.4 节 |
| 第 6 节，R19 | 第 10 节 |
| 第 8 节：隐私、可接续和语言 | 第 8.2、8.3 和第 9 节 |
| Q10：每个功能一个 PR | 第 1 节 |

## 15. 不在 F15 里

- 从手机启动 troy-mode，或者 Troy 编辑 issue 时自动醒来的会话。Troy 在手机上的编辑等到下一次在电脑上运行时才被读到。
- 通知。troy-mode 通过 Troy 的账号行事，GitHub 不会就 Troy 自己的操作通知 Troy。给 troy-mode 单独一个账号会改变 F04 D29。
- 置顶 issue、里程碑、GitHub Projects 看板和子 issue。
- 为规则变更、清理、版本测试计划或流水线之外的工作开 issue。
- troy-pstack 里的 issue，F09 的规则提议除外。
- #65 的改动本身的构建，它排在前面（第 10.2 节）。

## 16. 需要 Troy 决定的事项

F12、F13 和 F14 用了 D101 到 D137，D151 起留给 F16，D191 起留给 F19，所以 F15 用 D141 到 D150。Troy 于 2026-11-16 接受了全部推荐答案。

| 编号 | 问题 | 方案 | 推荐并已批准 |
| --- | --- | --- | --- |
| D141 | 谁来写这些 issue，什么时候写？ | A：一个新的引擎命令 `issues`，从状态算出每个进度 issue 和清单，把正文写进文件，并给出 `gh` 命令；主会话检查每个文件再发出，在每次开始时和每一步之后。`status` 读取 Troy 的想法、评论和勾选（第 3 节）。B：引擎自己创建和编辑 issue。C：主会话按技能里的说明，自己写和更新每个 issue。 | A。引擎在 GitHub 上保持只读（F07 设计 3.1），每次发出都经过 `check-text` 和 F05 的守卫，而它们看不到一个程序自己的 `gh` 调用；测试也能精确检查每段正文。C 要靠在长会话里记住，而试点的会话被压缩了 10 次。 |
| D142 | 一个功能的进度 issue 什么时候存在，显示什么？ | A：从功能成为下一个或有了阶段 PR 开始，到验收为止。正文从状态重新生成：6 个阶段作为勾选框、开着的 PR 最近的审查、什么在等 Troy，以及链接。每个阶段 PR 写 `Progress: #<n>`，GitHub 就会把它列进 issue，PR 6 写 `Closes #<n>`。Troy 的编辑会被替换，Troy 用评论来说话（第 4 节）。B：同 A，但到 PR 1 开出时才创建。C：一次为需求里的每个功能都开一个 issue。 | A。Troy 在手机上能看到接下来是什么，而且只有正在进行的功能有开着的 issue。B 让下一个功能在它的第一个 PR 之前看不到。C 一次开出很多几周都是空的 issue；试点的 16 个功能会开 16 个。 |
| D143 | troy-mode 怎样找到 Troy 的想法，什么时候处理？ | A：从"Idea"模板开的 issue（模板加上 `idea` 标签），或者任何没有标签的 issue。在下一个自然停顿处，即新功能、发布或版本测试计划开始之前，从不在两步之间，产品经理回复每个新想法说明它是什么，然后继续：需求变更走它的 PR，这个 PR 关闭想法并等 Troy 批准；或者是 bug、规则、回答或"以后再说"。Troy 在聊天里给出、暂时不做的想法也开一个 issue（第 5 节）。B：只有 Troy 在聊天里点名时，troy-mode 才读想法。C：同 A，但马上处理，两步之间也处理。 | A。Troy 在手机上写的想法，下一次运行就会处理，Troy 不用再说一遍；改动排在它可能改变的功能之前。每次需求变更仍由 Troy 批准。C 会在一个功能做到一半时重新打开已做的工作。 |
| D144 | 设备测试清单怎样用，Troy 怎样用它验收一个版本？ | A：每个版本一个 issue，发布测试通过后创建，Troy 运行的每个场景一个勾选框，步骤和预期结果从计划复制，最后一个框是"我接受"。全部勾上就是 Troy 的验收；失败写评论。新的一轮保留 Troy 已通过的勾选，清掉其余的（第 6 节）。B：同 A，但只能在聊天里验收；勾选只是 Troy 的记录。C：版本测试计划合并时就创建，在这个版本任何功能开始之前。 | A。Troy 在手机上测、在手机上验收，不用滚动表格。聊天和发布 PR 也照样可用。B 让 Troy 只为说一句话回到电脑前。C 在有东西可测的几个月前就显示勾选框。 |
| D145 | Troy 在手机上的回复怎样传回来？ | A：troy-mode 下一次运行时，Troy 在等 Troy 的 PR 上的评论，或一条"Comment"审查，算作 Troy 在聊天里的回复；进度 issue 上的评论当作聊天消息来读；Troy 对 troy-mode 文字的编辑会被替换，关掉的进度 issue 或清单会被重新打开（第 7 节）。B：同 A，但批准仍然只在聊天里或靠合并；PR 评论只作为作者的 Input。 | A。能在手机上批准正是 F15 的意义，而 F08 已经接受 PR 评论里的发布回复。两处说的话一样有效："全按推荐"就是批准。 |
| D146 | 用哪些标签、什么语言，issue 里可以放什么？ | A：标签 `idea`、`progress` 和 `device-test`，缺少时由主会话创建，已经存在就从不改。正文中文在前，英文折叠在下面。issue 里放从状态生成的行和从计划复制的 Troy 的场景；其他一律放链接。正文少于 60,000 个字符（第 8 节）。B：同 A，但只用英文，和 PR 评论一样。C：带前缀的标签，比如 `troy-mode:progress`。 | A。Troy 在手机上读这些，先读中文，和 F14 对摘要的决定一样。短标签在手机上好筛选。清单的步骤必须在手机上，其他都不需要。 |
| D147 | `gh` 或网络出问题时怎么办？ | A：issue 是视图。一次失败的写入会被记下、报告，并由下一次同步修好；流程继续。权限拒绝会连同要加的规则一起报告。读不到的想法或勾选从不靠猜：能读到之前，不处理任何想法，也不接受验收。重复的 issue 会被关闭（第 9 节）。B：任何 issue 出错都停下流程并升级上报。C：每次写入重试几次，然后继续。 | A。进度 issue 晚几分钟没有损失，下一次同步就会改正。B 会为一个视图停下一个功能。C 在 GitHub 不可用时增加等待，而下一次同步本来就会补上。 |
| D148 | issue 的文字怎样检查，哪些 hook 要改？ | A：troy-pstack #65 扩大的守卫先单独用一个 PR 合入，F15 的构建在上面加上 `gh issue close` 和 `reopen` 的评论、`gh label create` 和 `edit` 的说明，并拒绝 `gh issue delete` 和 `gh label delete`。主会话用 `check-text` 检查每段正文和每条评论，并读取它的退出码；`check-text` 也拒绝超过 65,536 个字符的内容。没有新的 R 规则（第 10 节）。B：F15 的构建包含 #65 的全部内容。C：只在技能里用 `check-text`，hook 不变。 | A。发到 GitHub 的文字会留下编辑历史，所以检查必须在发出之前，而 #65 已经设计好了。#65 单独一个 PR，让每个 PR 只做一件事。C 正是 #92 那条评论漏过去的原因。 |
| D149 | 已有项目怎样用上 F15？ | A：下一个次版本号的插件。更新后第一次运行 troy-mode 时，创建标签和当前功能的进度 issue，不需要项目里的文件。`upgrade troy-mode` 带来想法模板；在那之前，没有标签的 issue 就是想法。不为已验收的功能或已发布的版本补建（第 12 节）。B：同 A，再为每个已验收的功能补建已关闭的进度 issue。C：只有在 `upgrade troy-mode` 之后 F15 才开始。 | A。F15 在插件里，试点不用停下就能用上，它的 v0.2 从 F14 的进度 issue 开始。B 会一次给试点开出 13 个没人读的 issue。C 为了一个模板文件推迟了进度 issue。 |
| D150 | F15 怎样检查，状态什么时候变？ | A：由另一个代理依据本设计写的测试、埋 bug，以及在 `ZJUCao/troy-mode-trial` 上的一次试运行：把 Troy 的两个 issue 变成一次改动和一个回答，带着进度 issue 把 F02 走完各个阶段，并根据勾满的清单发布 v0.2.0；大约 13 次角色运行，13 到 20 美元（第 13 节）。合并后状态为"在样例项目上运行过"。B：测试、埋 bug，加一次只覆盖第一次同步、想法和 F02 第 2 步的短试运行；大约 3 次角色运行。试点之前状态为"已编写"。C：只有测试。 | A。清单和靠勾选验收是风险最大的部分，只有一次真实的发布才能看出来。它还会完成试运行仓库自 F12 以来一直在等的 v0.2。 |

需求文档 1.39 记录了批准的改动：

- F15 行写明 F15 构建了什么（D141 到 D150）。
- 3.3：Troy 可以在手机上用评论回复一个 PR 或 issue，troy-mode 下一次运行时读取（D145）。
- 5.4 第 1 步：troy-mode 在下一个自然停顿处处理想法 issue，变更 PR 关闭它（D143）。
- 5.5 第 3 步：清单 issue 在发布测试通过后出现，勾上最后一个框就是验收这个版本（D144）。
- 5.10：每个功能的进度 issue 是从状态重新生成的视图，和进度文件一样（D142，D147）。
- 第 8 节，隐私：issue 里也不放任何密钥（D146）。

## 17. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-16 | 初稿，含在 `ZJUCao/troy-mode-trial` 上的两次探测（第 2 节）。 |
| 1.0 | 2026-11-16 | Troy 批准，含 D141 到 D150，全部采用推荐答案。 |
| 1.1 | 2026-11-17 | 构建和试运行确认的事实：`status` 的两次读取（第 3.3 节）、PR 6 之后的最终生成（4.5）、镜像名字相同时的标题（4.2）、版本 0.7.0（12），以及试运行的记录（13.5）。 |
| 1.2 | 2026-11-22 | F20 设计（D268 到 D279，Troy 已于 2026-11-22 批准）：每个可以开始的功能都有进度 issue，而不只是下一个功能（第 4.1 节）。这个改动随 F20 的构建落地。 |
| 1.3 | 2026-11-23 | F07 的 D284 到 D287，来自 tstack issue #67，依据 Troy 2026-11-22 的长期同意批准：troy-mode 在进度 issue 上的 `Note for <ID>` 评论保存给后续功能的备注；目标功能的 issue 显示备注一行；备注不会盖掉 Troy 的评论（第 3.3、4.2、4.4、8.4、13.1 和 13.2 节）。 |
| 1.4 | 2026-11-24 | tstack #67 的构建：备注一行在各阶段的行之后、依赖之前（第 4.2 节）。 |
| 1.5 | 2026-11-25 | F18 设计（D171 到 D180，Troy 已于 2026-11-25 批准）：进度 issue 显示等待的编号、每次裁定、抽查的 PR 和风险标记；Troy 在上面的推翻和"risky"评论按聊天消息来读（D145），troy-mode 用新标题 `Overturn:` 回复一次推翻（第 8.4 节）；设备测试清单为 Troy 还没回应的每个抽查 PR 加一个勾选框（D144；F18 设计第 5.3、7.1 和 8 节）。这些改动随 F18 的构建落地。 |
