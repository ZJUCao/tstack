# 试点报告：recipe-menu v0.1

> 本文件是 [`recipe-menu-v0.1.md`](recipe-menu-v0.1.md) 的中文镜像，同步自英文版 1.0（2026-11-16）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.38](../requirements.zh-CN.md#72-功能列表) 中的 F11，[F11 设计](../design/F11-pilot.zh-CN.md)第 8 节 |
| 版本 | 1.0 |
| 日期 | 2026-11-16 |
| 状态 | Troy 已于 2026-11-16 阅读并批准。 |
| 事实来源 | 英文版 [`recipe-menu-v0.1.md`](recipe-menu-v0.1.md)。本文件是中文镜像。 |

时间都是美国东部时间（EST），即 Troy 电脑上的时间。费用按当天的 API 标价计算：opus 每百万输入 token 4 美元、每百万输出 token 20 美元，sonnet 分别是 2 美元和 10 美元；缓存写入按输入价的 1.25 倍（5 分钟）和 2 倍（1 小时）计，缓存读取每百万 token 0.20 美元（opus）和 0.10 美元（sonnet）。没写仓库名的 `#<n>` 链接都是 `ZJUCao/recipe-menu` 的 PR。

## 1. 摘要

- **项目。** `ZJUCao/recipe-menu`，一个新的私有 Python 命令行工具，管理菜谱、一周的菜单和它的购物清单，中英双语（F11 设计 D93）。
- **版本。** v0.1，13 个功能，F01 到 F13。2026-11-10，Troy 选择保留全部 13 个，而不是 D94 的 4 到 5 个（问题 4）。
- **日期。** 初始化从 2026-11-09 23:39 开始。2026-11-16 02:55，Troy 在自己的设备上验收了 v0.1.0；02:58，GitHub release `v0.1.0` 建在发布 PR [#94](https://github.com/ZJUCao/recipe-menu/pull/94) 的合并提交 `14d0d88` 上。03:02 发出复盘；Troy 为项目选的规则在 05:40 之前走完了规则变更流程（[#97](https://github.com/ZJUCao/recipe-menu/pull/97)）。
- **结果。** v0.1 的每个功能都是“在 Troy 的设备上可用”。共合并 97 个 PR，94 个属于 v0.1，3 个属于规则 P01；每个的 CI 都通过了，其中 #47 是合并之后才通过的（问题 13）。Troy 电脑上的发布测试通过了 583 个测试（4 个只在 Linux 上运行，在这里跳过）、29 个版本测试，以及一次真实运行，原型里的 48 条命令全部一致。Troy 在自己的设备上跑了三个场景，回复 “All accepted”。
- **troy-mode。** 整个版本在一个桌面会话里完成，插件先是 0.2.0，从 [#78](https://github.com/ZJUCao/recipe-menu/pull/78) 起是 0.5.0，带来了真实运行（F12）、模式守卫（F13）和给 Troy 的摘要（F14）。没有升级上报，没有 bug，记录在案的失败尝试只有一次。
- **问题。** 共 20 个（第 3 节）：1 个已修复，13 个作为 troy-pstack 的 issue 待修，6 个不需要修。给 troy-mode 的四个规则候选，Troy 接受了三个（第 4.2 节）。
- **费用。** 按标价共 1,092 美元，含 263 次角色运行和主会话；设计估计 4 到 5 个功能要 50 到 90 美元，2026-11-10 估计 13 个功能要 130 到 235 美元（第 5 节）。

## 2. 时间线

| 时间 | 步骤 | PR |
| --- | --- | --- |
| 11-09 23:20 | F11 会话检查前提条件。Troy 安装插件 0.2.0，设置 `MAMBA_EXE`，加上合并权限，重启应用。 | |
| 11-09 23:39 | 试点会话在 `D:\Troy\Projects\recipe-menu` 开始，请求是 “start a project: a Python command-line tool for my recipes, a week's menu, and the shopping list for that menu, with Chinese and English text”。 | |
| 11-09 23:43 | 初始化：troy-init 创建私有仓库，初始化 PR 合并。 | [#1](https://github.com/ZJUCao/recipe-menu/pull/1) |
| 11-10 00:10 | Troy 回答产品经理的 14 个问题（“All recommended”），批准需求：16 个功能，v0.1 = F01 到 F13。 | [#2](https://github.com/ZJUCao/recipe-menu/pull/2) |
| 11-10 02:18 | Troy 批准架构，不属于任何系列：只用 Python 3.13 标准库，7 个 ADR。 | [#3](https://github.com/ZJUCao/recipe-menu/pull/3) |
| 11-10 02:21 | 语言步骤加入 Python 语言包。 | [#4](https://github.com/ZJUCao/recipe-menu/pull/4) |
| 11-10 03:26 | Troy 保留 v0.1 的全部 13 个功能（问题 4）。 | |
| 11-10 03:49 | v0.1 测试计划。 | [#5](https://github.com/ZJUCao/recipe-menu/pull/5) |
| 11-10 14:16 | F01 验收，期间对它的设计有两个旁支 PR。 | #6 到 #13 |
| 11-10 20:08 | F02 验收。 | #14 到 #19 |
| 11-11 11:58 | F03 在 11:47 验收。被问到前三个功能之后的那个问题时，Troy 决定继续批准全部 16 个功能的设计和测试计划。 | #20 到 #26 |
| 11-12 01:21 | F04 验收。 | #27 到 #32 |
| 11-12 14:15 | F05 验收，期间有一次架构变更。 | #33 到 #39 |
| 11-12 19:19 | F06 验收。 | #40 到 #45 |
| 11-13 00:12 | F07 验收。 | #46 到 #51 |
| 11-13 11:47 | F08 验收，期间有一次架构变更。 | #52 到 #58 |
| 11-13 19:38 | F09 验收。 | #59 到 #64 |
| 11-13 19:50 | troy-pstack 的第一个状态 PR（D100），晚了：它本该在 F01 验收时提交，但 F11 会话只有在 Troy 写信时才知道进展。 | [troy-pstack#45](https://github.com/ZJUCao/troy-pstack/pull/45) |
| 11-14 04:07 | F10 验收。 | #65 到 #70 |
| 11-15 03:37 | F11 验收，期间有一次架构变更。 | #71 到 #77 |
| 11-15 12:36 | Troy 更新插件，troy-mode 把项目升级到 0.5.0。 | [#78](https://github.com/ZJUCao/recipe-menu/pull/78) |
| 11-15 16:11 | F12 验收，第一次真实运行：41 条命令一致，6 条等 F13。 | #79 到 #84 |
| 11-16 01:08 | F13 验收，期间有一次需求变更；它是第一个“在 Troy 的电脑上真跑过”的功能。 | #85 到 #91 |
| 11-16 02:19 | 版本测试，以及 v0.1 测试计划的一次更新。 | #92、#93 |
| 11-16 02:58 | Troy 在 02:55 验收 v0.1.0；发布 PR 合并，troy-mode 创建 GitHub release。 | [#94](https://github.com/ZJUCao/recipe-menu/pull/94) |
| 11-16 03:10 | 复盘在 03:02 发出，Troy 选了全部四条提议。 | [#94](https://github.com/ZJUCao/recipe-menu/pull/94) |
| 11-16 05:40 | P01 走完规则变更流程，带两个清理 PR。提议 B、C、D 成为 troy-pstack 的 issue。 | #95 到 #97 |

## 3. 问题

类型：**阻塞**（没有 Troy，troy-mode 就走不下去）、**绕过**（troy-mode 自己，或经 Troy 同意，绕了过去）、**违规**（违反了规则或设计，而没有东西拦住）、**外观**，以及**无过错**。issue 都在 troy-pstack 里，来自试点的带 `pilot` 标签。

| # | 时间 | 发生了什么 | 类型 | 功能 | 修复或 issue |
| --- | --- | --- | --- | --- | --- |
| 1 | 11-10，[#2](https://github.com/ZJUCao/recipe-menu/pull/2) | 产品经理把中文的修改记录一节命名为“变更记录”，而不是模板里的“修改记录”，所以 `approve` 只在英文文件里记下了 Troy 的批准。产品经理手动改了节名并加上那一行。 | 绕过 | F01、F07 | [#46](https://github.com/ZJUCao/troy-pstack/issues/46) |
| 2 | 11-10，[#3](https://github.com/ZJUCao/recipe-menu/pull/3) | Troy 批准之后，ADR 的状态文字仍是 “Proposed”。产品经理自己的修改被运行后的检查撤销，另跑了一次架构师才改过来。 | 绕过 | F07 | [#47](https://github.com/ZJUCao/troy-pstack/issues/47) |
| 3 | 11-10，[#3](https://github.com/ZJUCao/recipe-menu/pull/3) | 架构师在 CRLF 文件上用 `sed -i`，没有替换任何内容，却把行尾改成了 LF；它恢复了文件，改用脚本。 | 外观 | F04 | 无 |
| 4 | 11-10，[#2](https://github.com/ZJUCao/recipe-menu/pull/2) | v0.1 有 13 个功能，而 D94 说 4 到 5 个：开始请求没有写明试点的规模。 | 无过错 | F11 | Troy 保留 13 个（选项 B）。 |
| 5 | 11-10，[#3](https://github.com/ZJUCao/recipe-menu/pull/3) | 语言步骤之前还没装 uv，架构师没法试 `uv tool install`。 | 外观 | F04 | 无 |
| 6 | 11-10，[#4](https://github.com/ZJUCao/recipe-menu/pull/4) | 在应用的沙箱里编译锁文件失败：uv 写不了它默认的缓存。troy-init 恢复了文件，把 `UV_CACHE_DIR` 设到会话的临时文件夹后，这一步再跑就通过了。 | 绕过 | F06 | [#48](https://github.com/ZJUCao/troy-pstack/issues/48) |
| 7 | 11-11，[#23](https://github.com/ZJUCao/recipe-menu/pull/23) | F01 的 [#12](https://github.com/ZJUCao/recipe-menu/pull/12) 的一次开发者运行在后台挂了 11.5 小时，然后在 F03 的测试工程师运行期间写进 33 行重复代码。检查怪到了测试工程师头上；Troy 说 “Yes, restore it”。11-13 还有一个测试工程师留下了一个 Python 进程。 | 经 Troy 同意绕过 | F07 | [#49](https://github.com/ZJUCao/troy-pstack/issues/49) |
| 8 | 11-11 到 11-13，[#27](https://github.com/ZJUCao/recipe-menu/pull/27)、[#40](https://github.com/ZJUCao/recipe-menu/pull/40)、[#59](https://github.com/ZJUCao/recipe-menu/pull/59) | 自动模式把 `git commit --amend --no-edit` 和 `git push --force-with-lease` 当作 “Git Destructive” 拒绝，共六次。Troy 允许了这两条命令；之后又有三次拒绝连在一起的命令，troy-mode 就把每条命令单独运行。 | 阻塞，经 Troy 同意绕过 | F07、F10 | 指南修复 [troy-pstack#69](https://github.com/ZJUCao/troy-pstack/pull/69)，关闭 [#50](https://github.com/ZJUCao/troy-pstack/issues/50) |
| 9 | 11-10 到 11-13，[#9](https://github.com/ZJUCao/recipe-menu/pull/9)、[#52](https://github.com/ZJUCao/recipe-menu/pull/52)、[#59](https://github.com/ZJUCao/recipe-menu/pull/59) | CI 的 `ruff format --check` 连设计文档里的 python 示例也一起检查，而界面设计师没法运行它：F01 为此开了一个旁支 PR，F08 的 CI 失败两次，F09 有一次失败尝试。 | 绕过，三个功能 | F03、F07 | [#51](https://github.com/ZJUCao/troy-pstack/issues/51) |
| 10 | 11-10 到 11-15 | “Start v0.1” 只让 troy-mode 做到 F01，所以 Troy 手动开始后面每个功能：多了 12 个请求。 | 外观 | F07 | [#52](https://github.com/ZJUCao/troy-pstack/issues/52) |
| 11 | 整个试点 | 一个会话做完整个版本：压缩 15 次，最大一次时上下文有 883,000 个 token；5 次碰到 5 小时用量上限而停下。主会话花了 301 美元，占总数的 28%。 | 费用 | F07 | 第 8 节 |
| 12 | 11-12、11-16 | F05 的 R19 hook 拒绝了两个 PR 描述，里面有严格模式不允许的一个词，其中一次是在本地路径里；troy-mode 改写了它们。 | 无过错 | F05 | 无 |
| 13 | 11-12，[#47](https://github.com/ZJUCao/recipe-menu/pull/47) | F07 的测试计划在 CI 检查报告之前就合并了：等待命令说 “no checks reported”，而合并是用 `;` 接在后面的。两次运行事后都通过了。此后会话每次合并都用它自己写的等待脚本。 | 违规 | F07 | [#68](https://github.com/ZJUCao/troy-pstack/issues/68) |
| 14 | 11-12 到 11-16 | 从标准输入读程序的 Python 会挂住：这样的 168 次运行里有 39 次碰到 120 秒上限，角色和主会话都有，尽管每份任务简报都提醒过。 | 绕过 | F04、F05 | [#64](https://github.com/ZJUCao/troy-pstack/issues/64)（复盘 C） |
| 15 | 11-12 到 11-16，七个 mock PR | mock 的说明指向不存在的内容，或者和 mock 正好相反，从 [#36](https://github.com/ZJUCao/recipe-menu/pull/36) 到 [#88](https://github.com/ZJUCao/recipe-menu/pull/88)，每次都多一轮评审。 | 重复的评审意见 | F04 | [#63](https://github.com/ZJUCao/troy-pstack/issues/63)（复盘 B） |
| 16 | 11-16，[#92](https://github.com/ZJUCao/recipe-menu/pull/92) | 一条测试经理的评审评论被发了出去，里面有 R19 严格模式不允许的一个词，因为命令用 grep 检查 `check-text` 的输出，而不是它的退出码。评论随即改了，但 GitHub 保留旧文本。 | 违规 | F05、F07 | [#65](https://github.com/ZJUCao/troy-pstack/issues/65)（复盘 D） |
| 17 | 11-16 | `hooks.log` 只保留最近一天的行，所以复盘看不到这个版本早些时候的 hook 拦截。 | 设计缺口 | F05、F08 | [#66](https://github.com/ZJUCao/troy-pstack/issues/66) |
| 18 | 11-10 到 11-16 | 审查者给后面功能的备注会在阶段往前走时被丢掉，所以主会话把几十条这样的备注存在自己的记忆里，再一条条手动抄进任务简报。 | 绕过 | F07 | [#67](https://github.com/ZJUCao/troy-pstack/issues/67) |
| 19 | 11-13，[#52](https://github.com/ZJUCao/recipe-menu/pull/52) | F08 的设计在界面设计师的文件上两次 CI 失败，却没有发尝试失败的评论，所以复盘只数到 1 次失败尝试，而 CI 在作者的文件上失败了四次推送，#52 和 #59 各两次。 | 违规 | F07 | [#73](https://github.com/ZJUCao/troy-pstack/issues/73)（候选 T1） |
| 20 | 11-16，[#87](https://github.com/ZJUCao/recipe-menu/pull/87) | CI 的检出步骤报 “Repository not found”，原因在 GitHub 那边；下一次推送就通过了。 | 无过错 | 无 | 无 |

各个角色自己的失误是问题 1、2、3、7、9、13、14、15、16 和 19，以及要求修改的评审意见（第 5.5 节）；F16 的角色考试从这些失误里取题。

## 4. 规则候选

### 4.1 针对这个项目

[#94](https://github.com/ZJUCao/recipe-menu/pull/94) 上的复盘（F08 D76）看了 94 个 PR：56 组评审意见，其中 8 组出现在两个或更多 PR 里，1 次失败尝试，没有升级上报，没有 bug。它提了四条规则，Troy 四条都选了（“All four”）：

| 提议 | 出现在 | 结果 |
| --- | --- | --- |
| A. 测试辅助模块的文档注释写明模块的用途和限制，不列名字（R05）。 | #62、#68、#75、#82 | 项目规则 P01，走了规则变更流程：[#95](https://github.com/ZJUCao/recipe-menu/pull/95)，带架构师给的执行方式，然后是清理 PR [#96](https://github.com/ZJUCao/recipe-menu/pull/96) 和 [#97](https://github.com/ZJUCao/recipe-menu/pull/97)。 |
| B. DV1 的任务简报用固定的句子给出 mock 的说明。 | 7 个 mock PR | 适用于每个项目的规则：[troy-pstack#63](https://github.com/ZJUCao/troy-pstack/issues/63)（F09 D83）。 |
| C. F05 的 hook 拒绝从标准输入读程序的 Python。 | 39 次挂住的运行 | [troy-pstack#64](https://github.com/ZJUCao/troy-pstack/issues/64)。 |
| D. F05 的 gh 守卫在发评论、PR 或 issue 之前先跑 `check-text`。 | [#92](https://github.com/ZJUCao/recipe-menu/pull/92)，一次 | [troy-pstack#65](https://github.com/ZJUCao/troy-pstack/issues/65)。 |

### 4.2 针对 troy-mode

在多个功能或流程里重复出现、一条适用于每个项目的规则或检查就能防住的问题。已经有 issue 的不再重复提：上面的 B、C、D，以及 [#49](https://github.com/ZJUCao/troy-pstack/issues/49)（报告之后还在跑的角色运行）、[#51](https://github.com/ZJUCao/troy-pstack/issues/51)（设计里的代码示例）、[#52](https://github.com/ZJUCao/troy-pstack/issues/52)（点名一个版本的请求）、[#66](https://github.com/ZJUCao/troy-pstack/issues/66)（hook 日志）、[#67](https://github.com/ZJUCao/troy-pstack/issues/67)（给后面功能的备注）和 [#68](https://github.com/ZJUCao/troy-pstack/issues/68)（合并前等 CI）。新的候选：

| ID | 候选 | 证据 | 推荐 | Troy 的回答 |
| --- | --- | --- | --- | --- |
| T1 | `status` 和 `retro` 根据 PR 每次推送的提交上失败的检查来数尝试次数，而不只靠 troy-mode 发的评论。 | 问题 19：#52 上两次 CI 失败一直没被数进去，CI 失败了四次推送，复盘却只看到 1 次失败尝试。 | 是 | 接受 |
| T2 | 每个验收 PR 和发布 PR 写明它的功能或版本的角色运行次数和费用，从会话记录里读出。 | 问题 11：这个版本花了 1,092 美元，估计是 130 到 235 美元，直到这份报告才有人看到。 | 是 | 接受 |
| T3 | 代码审查员每个版本跑一次 `security-review`，在发布 PR 的完整 diff 上跑，另外在新增依赖、子进程或网络访问的 PR 上跑，而不是每个代码 PR 都跑。 | 试点里跑了 71 次，一次也没发现问题；这个程序没有网络、子进程或密钥。 | 是 | 接受 |
| T4 | P01 成为适用于每个项目的 troy-mode 规则。 | 一个项目里的四个 PR。 | 否：等第二个项目也出现再说。 | 不接受 |

Troy 在 2026-11-16 接受了 T1、T2 和 T3，它们现在是 [#73](https://github.com/ZJUCao/troy-pstack/issues/73)、[#74](https://github.com/ZJUCao/troy-pstack/issues/74) 和 [#75](https://github.com/ZJUCao/troy-pstack/issues/75)，之后按 troy-pstack 的流程来做。T4 没有被接受。

## 5. 时间和费用

### 5.1 和估计对比

| 指标 | F11 设计 8.4，4 到 5 个功能 | 2026-11-10 对 13 个功能的估计 | 实际，13 个功能 |
| --- | --- | --- | --- |
| 角色运行 | 50 到 70 次 | 160 到 180 次 | 263 次，另有代码审查员的 `code-review` 技能启动的 74 个辅助代理 |
| 费用 | 50 到 90 美元 | 130 到 235 美元 | 1,092 美元 |
| PR | 约 35 个 | 约 80 个 | 97 个：94 个属于 v0.1，3 个属于 P01 |
| CI | 每个 PR 几分钟 Actions | | 274 次运行，共 220 分钟运行时间，平均每次 48 秒 |
| 耗时 | | 好几天 | 6 天 6 小时，从 11-09 23:39 到 11-16 05:40 |
| Troy 的时间 | 2 到 3 小时 | | 65 条消息；Troy 没有给出时间估计 |

按功能算，角色运行次数接近估计，18 次对 10 到 18 次，但每次运行贵了三到四倍：算上主会话的份额，每次角色运行 4.15 美元，估计是 1.00 到 1.30 美元；主会话每个功能花 13 到 32 美元。估计来自试运行的功能，那些功能小得多：试点中，一个功能的设计和测试计划有 60,000 到 185,000 个英文字符（需求文档 F14 一行）。

GitHub 的计时 API 对这些运行没有列出计费时间，所以 CI 的数字是运行时间。

### 5.2 按角色

每次 Agent 调用都让角色按自己的定义选模型和 effort，项目也没设 `[roles]` 表，所以每个角色用它自己的模型，effort 跟随会话。

| 角色 | 运行次数 | 模型 | 费用 | 每次 |
| --- | --- | --- | --- | --- |
| 产品经理（主会话） | 1 个会话 | opus | 300.97 美元 | |
| 测试经理 | 54 | opus | 246.54 美元 | 4.57 美元 |
| 界面设计师 | 28 | opus | 139.49 美元 | 4.98 美元 |
| 代码审查员 | 73 | opus | 139.39 美元 | 1.91 美元 |
| 它的辅助代理 | 74 | opus | 94.06 美元 | 1.27 美元 |
| 架构师 | 33 | opus | 108.61 美元 | 3.29 美元 |
| 测试工程师 | 31 | sonnet | 45.70 美元 | 1.47 美元 |
| 开发者 | 44 | sonnet | 17.89 美元 | 0.41 美元 |
| 合计 | 263 次角色运行 | | 1,092.66 美元 | |

桌面应用会给会话记一个累计费用。它的最后一条记录在 11-15 03:37，是 864.06 美元；同样的算法算到那一刻是 848.53 美元，少 1.8%。

### 5.3 按步骤

| 步骤 | 小时 | 角色运行 | 辅助代理 | 角色费用 | 主会话 | 合计 | 评审轮次，要求修改的 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 初始化到语言步骤 | 2.7 | 2 | 0 | 6.28 美元 | 9.15 美元 | 15.43 美元 | |
| v0.1 测试计划 | 1.5 | 1 | 0 | 5.68 美元 | 1.72 美元 | 7.40 美元 | |
| F01 | 10.2 | 24 | 6 | 32.30 美元 | 12.60 美元 | 44.91 美元 | 9 轮中 3 轮 |
| F02 | 5.3 | 16 | 4 | 37.48 美元 | 12.83 美元 | 50.31 美元 | 8 轮中 3 轮 |
| F03 | 13.0 | 14 | 4 | 61.32 美元 | 15.05 美元 | 76.38 美元 | 7 轮中 2 轮 |
| F04 | 12.8 | 21 | 6 | 69.84 美元 | 20.21 美元 | 90.04 美元 | 10 轮中 4 轮 |
| F05 | 11.7 | 20 | 5 | 75.54 美元 | 25.88 美元 | 101.41 美元 | 9 轮中 2 轮 |
| F06 | 3.2 | 17 | 5 | 53.41 美元 | 15.03 美元 | 68.44 美元 | 8 轮中 3 轮 |
| F07 | 4.2 | 15 | 5 | 47.25 美元 | 17.71 美元 | 64.96 美元 | 8 轮中 2 轮 |
| F08 | 9.4 | 19 | 5 | 58.89 美元 | 16.25 美元 | 75.13 美元 | 8 轮中 3 轮 |
| F09 | 5.3 | 19 | 5 | 64.40 美元 | 19.71 美元 | 84.11 美元 | 9 轮中 3 轮 |
| F10 | 5.8 | 18 | 6 | 50.18 美元 | 16.28 美元 | 66.47 美元 | 10 轮中 4 轮 |
| F11 | 15.5 | 18 | 5 | 77.88 美元 | 25.32 美元 | 103.20 美元 | 9 轮中 3 轮 |
| 升级到 0.5.0 | 0.1 | 0 | 0 | 0.00 美元 | 5.33 美元 | 5.33 美元 | |
| F12 | 3.1 | 16 | 5 | 44.11 美元 | 24.53 美元 | 68.63 美元 | 8 轮中 3 轮 |
| F13 | 7.5 | 17 | 5 | 66.91 美元 | 31.79 美元 | 98.69 美元 | 8 轮中 3 轮 |
| 发布 | 1.8 | 7 | 2 | 12.77 美元 | 10.16 美元 | 22.93 美元 | 4 轮中 2 轮 |
| 复盘和 P01 | 2.7 | 19 | 6 | 27.47 美元 | 21.16 美元 | 48.64 美元 | 10 轮中 4 轮 |

一个功能的小时数从它的设计 PR 创建算到验收 PR 合并，包括等 Troy 的时间。每一步的运行次数和费用，是上一步最后一次合并到这一步最后一次合并之间的；旁支 PR 算在它发生的那一步里。角色费用包括辅助代理。

### 5.4 按功能循环的阶段

F01 到 F13 加起来，含各阶段的旁支 PR：

| 阶段 | 角色运行 | 角色 | 角色费用 |
| --- | --- | --- | --- |
| 1. 设计 | 40 | 界面设计师 20，架构师 20 | 215 美元 |
| 2. 测试计划 | 32 | 测试经理 20，界面设计师 7，架构师 5 | 184 美元 |
| 3. mock | 50 | 开发者 25，代码审查员 23，其他 2 | 43 美元 |
| 4. 测试 | 72 | 测试工程师 24，测试经理 24，代码审查员 24 | 164 美元 |
| 5. 实现 | 39 | 开发者 19，代码审查员 19，架构师 1 | 42 美元 |
| 6. 验收 | 1 | 测试经理 1（TM8） | 1 美元 |

两个文档阶段占了角色运行的 30%，角色费用的 60%。

### 5.5 评审、尝试、升级上报和等待

- **评审。** 共 127 条评审评论：架构师 23 条（4 条要求修改），测试经理 31 条（12 条），代码审查员 73 条（28 条）。35 个 PR 需要第二轮，3 个需要第三轮（[#29](https://github.com/ZJUCao/recipe-menu/pull/29)、[#68](https://github.com/ZJUCao/recipe-menu/pull/68)、[#97](https://github.com/ZJUCao/recipe-menu/pull/97)）。没有一个到达第三轮之后的升级上报。
- **尝试。** 一条评论：[#59](https://github.com/ZJUCao/recipe-menu/pull/59) 上的界面设计师第 1 次尝试；另外两次 CI 失败没有记下（问题 19）。
- **升级上报。** 没有。
- **等 Troy。** 34 条 `Waiting for Troy` 评论：33 次批准，以及 v0.1.0 的验收。Troy 回复时间的中位数是 27 分钟；11 次等待不到 15 分钟，4 次过夜的等待超过 4 小时。troy-mode 一共等了 48 小时。
- **Troy 的消息。** 共 65 条：开始请求和升级请求；初始化时的 4 个回答；14 个开始功能的请求，原因是问题 10；26 次批准设计和测试计划；4 次批准架构和需求变更；6 个其他决定，比如 “Keep approving them” 和 “Allow both commands”；5 次用量上限之后的继续；发布时 4 条。Troy 用英文写，从 F09 起用中文开始功能。
- **hook 拦截。** 两次，都正确（问题 12）。写这份报告时，`hooks.log` 里只剩第二次（问题 17）。

## 6. 指南

Troy 在试点中照着指南做。指南错了、缺了或不清楚的每个地方，都在 [troy-pstack#69](https://github.com/ZJUCao/troy-pstack/pull/69) 里修好了：

| 指南章节 | 发生了什么 | 修复 |
| --- | --- | --- |
| 1.1 | 它说要“在应用启动时所在的环境里”设置 `MAMBA_EXE`，但没说怎么设；`MAMBA_ROOT_PREFIX` 其实不需要。 | 设为用户环境变量，一行 PowerShell，然后彻底退出应用；`MAMBA_ROOT_PREFIX` 可以不设。 |
| 1.2 | 桌面应用的 Code 标签页不提供 `/plugin` 命令，PowerShell 的 PATH 里也没有命令行。也没法看已安装的版本。 | 用自带的命令行安装，一行 PowerShell 就能找到它；`plugin list` 显示版本。 |
| 1.3 | 11-15 的更新找不到新版本：插件市场是主检出，它落后了五个提交。 | 先拉取主检出，再更新插件市场，然后更新插件；在自然的停顿点重启。 |
| 1.4 | 它只给了合并权限（问题 8）。 | 三项允许规则都列出，并说明连在一起的命令会怎样。 |
| 2.1 | Troy 把第一个请求打在了 F11 会话里，而不是试点文件夹里的会话；指南也没说不要用 worktree。 | 在项目文件夹本身开一个新会话，项目的每个请求都在那里输入。 |
| 3.1 | 它说对了，“the rest of v0.1” 会做整个版本；但 “Start v0.1” 只做了一个功能（问题 10），也没说一个功能要花多少。 | 加了关于 “Start v0.1” 的说明，以及本报告里每个功能的小时数、角色运行次数和费用。 |
| 5.8、8.6 | 没说 hook 日志只保留一天（问题 17）。 | 两处都写了。 |
| 7.5 | 没说给后面功能的备注会被丢掉（问题 18），也没说用量上限或压缩之后怎么办。 | 都写了。 |
| 8.6 | 问题 6、7、14 和 20 没有对应的行，权限那一行只提了合并。 | 新增或扩充了四行。 |
| 9 | 只写了 `plugin update`，没先拉取。 | 改为指向第 1.3 节。 |
| README | 它说还没有任何部分在真实项目上跑过，列出的未跑路径有些试点已经跑过。 | 写明试点跑了什么，以及什么还没跑过。 |

F10 构建时读者测试提到、而试点解决了的缺口：怎样看已安装的版本，`MAMBA_EXE` 设在哪里，以及插件市场的检出必须在最新的 `main` 上。其他的试点没有用到，比如手工开的 `[rules]` PR。

## 7. 状态

在需求文档第 7.2 节。这份报告和指南 PR 合并之后，最终的状态 PR（F11 设计第 9 节第 2 项）做这些变动：

| 功能 | 之前（需求文档 1.38） | 之后 | 原因 |
| --- | --- | --- | --- |
| F01 到 F07 | 已在真实项目上使用，“到目前为止” | 已在真实项目上使用，覆盖整个版本 | 第一个状态 PR 时条件就已满足；文字现在覆盖 v0.1 直到发布。 |
| F03 的 C/C++ 语言包 | 在示例项目上跑通 | 不变 | 试点只用了 Python 语言包。 |
| F08 | 在示例项目上跑通 | 已在真实项目上使用 | troy-mode 发布了 v0.1.0：版本测试、带真实运行的发布测试、Troy 在自己设备上的测试、GitHub release，以及复盘。 |
| F09 | 在示例项目上跑通 | 已在真实项目上使用 | P01 走完了规则变更流程并做了清理，三条适用于每个项目的规则成为 troy-pstack 的 issue（D99）。 |
| F10 | 已写好 | 已在真实项目上使用 | Troy 照着指南做了，指南的修复在 troy-pstack#69 合并。 |
| F11 | 已在真实项目上使用，进行中 | 已在真实项目上使用 | v0.1.0 于 2026-11-16 在 Troy 的设备上验收，并有这份报告。 |
| F12、F13、F14 | 在示例项目上跑通，或已写好 | 已在真实项目上使用 | 不在 F11 的表里，但每份设计都给出了自己在真实项目上使用的条件，试点都满足了：#84 和 #91 的真实运行，从 #78 起每个会话里 hook 都开着（它没有拒绝任何命令），以及从 #79 起 Troy 根据摘要批准。Troy 在 2026-11-16 决定在同一个 PR 里一起改。 |

## 8. 下一步

- **试点留下的未关闭 issue。** [#46](https://github.com/ZJUCao/troy-pstack/issues/46) 到 [#49](https://github.com/ZJUCao/troy-pstack/issues/49)、[#51](https://github.com/ZJUCao/troy-pstack/issues/51)、[#52](https://github.com/ZJUCao/troy-pstack/issues/52)，以及 [#63](https://github.com/ZJUCao/troy-pstack/issues/63) 到 [#68](https://github.com/ZJUCao/troy-pstack/issues/68)，以及 Troy 接受的候选 [#73](https://github.com/ZJUCao/troy-pstack/issues/73) 到 [#75](https://github.com/ZJUCao/troy-pstack/issues/75)。
- **费用。** 最大的部分是两个文档阶段和主会话的上下文（问题 11）。值得在第二个试点上逐一试、逐一测量的：每个功能开一个新会话，因为状态在 git 和 GitHub 上；F14 的摘要，可能让角色少读一些；候选 T3；以及降低审查者的 effort。
- **已计划的功能。** F15（给 Troy 的 issue）、F16（角色考试，题目来自第 3 节）、F17、F18（更少的停顿：这次试点里 troy-mode 在每个设计和测试计划处都停下，因为 Troy 选择批准全部 16 个），以及 F19 改名，它要等这份报告的 PR 合并。
- **第二个试点**应该试这次没试到的：已经有代码的项目，比如 `nuo_voice`，或者先做 F11 设计第 3.3 节的 C/C++ 修复再试 HiLog；真实项目上的修 bug 和升级上报；Troy 接受的依赖；在 GitHub 上合并来给出批准；对前几个功能之后的那个问题回答“不”，让 troy-mode 自己合并设计；补丁版本；以及修改或废止项目规则。
- **recipe-menu 继续。** 它的 v0.2 有 F14 到 F16。这个版本之后又有两个 P01 清理 PR：[#98](https://github.com/ZJUCao/recipe-menu/pull/98) 在 06:14 合并，写这份报告时，给版本测试辅助代码的 [#99](https://github.com/ZJUCao/recipe-menu/pull/99) 还开着。
