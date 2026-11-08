# F10 设计：troy-pstack 里 troy-mode 的文档

> 本文件是 [`F10-docs.md`](F10-docs.md) 的中文镜像，同步自英文版 1.0（2026-11-08）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.26](../requirements.zh-CN.md#72-功能列表) 中的 F10 |
| 版本 | 1.0 |
| 日期 | 2026-11-08 |
| 状态 | Troy 已于 2026-11-08 批准，含 D86 到 D92。 |
| 事实来源 | 英文版 [`F10-docs.md`](F10-docs.md)。本文件是中文镜像。 |

## 1. 范围

F10 在 troy-pstack 里为 troy-mode 写文档，让 Troy 只看文档就能安装它、开始一个项目、走完每个流程。它交付：

1. 仓库 `README.md` 里的 troy-mode 一节（第 3 节）；
2. 中英文使用指南，放在 `docs/troy-mode/guide/`（第 4 节，D86）；
3. 在 README 这一节和指南里注明：troy-mode 是 Troy 自己的作品，不属于 Lauren Tan 的 pstack（第 3.2 节，D88）；
4. 新的插件版本，让已安装的 troy-pstack 能拿到 troy-mode（第 6 节，D89）；
5. 对 troy-pstack 自己文档的链接检查（第 9.1 节，D90）。

指南描述的是 F10 合入时已经实现的 troy-mode：F01 到 F07，加上版本发布流程（F08）和规则变更流程（F09）。所以 F10 在 F09 合入之后再做（D91）。试点（F11）是指南的第一个真实读者：Troy 在真实项目上照着它做，F11 修正它写错的地方。

F10 不新增技能、代理、钩子或引擎命令，也不改变 troy-mode 的任何行为。它按 Q10 对每个功能的规定，用一个 PR 合入。

## 2. 位置

```text
README.md                         新增 "troy-mode" 一节（第 3 节）
.claude-plugin/
  plugin.json                     版本 0.2.0 和新的描述（第 6 节）
  marketplace.json                插件的描述（第 6 节）
docs/
  troy-mode/
    guide/
      README.md                   指南的首页（第 4 节）
      README.zh-CN.md             每一页都有中文镜像
      01-install.md ... 09-changing-troy-mode.md
troy-mode/
  dev/
    check_links.py                链接检查（第 9.1 节）
    tests/
      test_check_links.py         它的单元测试
.github/
  workflows/
    troy-docs.yml                 在 check_pairs.py 之后运行 check_links.py
```

上游的指南 `docs/guide/` 是 Lauren Tan 的作品，为 Claude Code 做过改编。F10 不改它。需求文档第 8 节只允许 troy-mode 改动三个共用文件：`README.md`、`plugin.json` 和 `marketplace.json`，F10 也只改这三个。

## 3. README 里的一节

### 3.1 放在哪里，写什么

新的一节 `## troy-mode` 放在 "Get started" 之后、"How the port works" 之前。它只用英文（D87），内容是：

- **声明**：第 3.2 节的那段话。
- **troy-mode 是什么**，三句话：一条固定的角色流水线，把项目从需求带到发布的版本；每个角色在自己的上下文里工作，由另一个角色审查，规则靠检查来执行。
- **快速开始**：Troy 要输入的两个命令，每个项目一次的 `/troy-pstack:troy-init`，以及所有工作都用的 `/troy-pstack:troy-mode <请求>`；还有 troy-mode 会停下来等 Troy 的五个步骤（需求文档 3.3）。
- **troy-mode 还是 poteto-mode**：需求文档 3.2 那张表的精简版。
- **它给插件加了什么**：技能 `troy-init` 和 `troy-mode`、六个 `troy-*` 代理、`hooks/hooks.json` 里的钩子，以及 `troy-mode/` 下的文件。后面的技能表保持不变：它记录的是上游技能的移植情况，而 troy-mode 的部分不是移植来的。
- **链接**：英文和中文指南、需求文档和各设计文档。

"Make it yours" 一节改为说明：troy-mode 是 Troy 自己的模式，在这个分支里实现，并链接到新的一节。它原来建议用 `automate-me` 起草一个 troy-mode 技能，这已经不是现在的做法。

### 3.2 声明（D88）

README 这一节和指南首页都以下面这段话开头，中文指南用它的译文：

> **troy-mode 是 Troy 自己的作品。** 它由 Troy 设计，在这个分支里实现。它不属于 Lauren Tan 的 pstack，Lauren Tan 和 Cursor 没有审阅或认可过它。它原样复用 `how`、`why`、`interrogate`、`correct` 等 pstack 技能，也不改变 `poteto-mode` 的行为。它和 troy-pstack 的其余部分一样，采用 MIT 许可证。

README 现有的致谢一节保持不变：troy-mode 之外，几乎每个技能、playbook、代理和指南页面都是 Lauren Tan 的作品。

## 4. 指南

### 4.1 页面

每一页都有中文镜像，带需求文档 R12 要求的同步说明，所以 `check_pairs.py` 会检查每一对。

| 页面 | 内容 |
| --- | --- |
| `README.md` | 声明（第 3.2 节）。troy-mode 是什么，以及只需记住的一件事：输入 `/troy-pstack:troy-mode` 加上你想做的事，它只在需要你的地方停下来。各页面和阅读顺序。 |
| `01-install.md` | Troy 的电脑需要什么：带 Git Bash 的 Git for Windows、已登录 GitHub 的 `gh`、troy-mode 引擎需要的 Python 3.11 或更新版本，以及 Python 项目需要的 Miniforge（mamba）和 uv。从本地文件夹安装 troy-pstack，以及插件出新版本后怎么更新。让 troy-mode 能合并自己 PR 的权限（第 4.3 节）。每个角色的模型和推理强度，以及在单个项目里用 `.troy-mode/config.toml` 的 `[roles]` 修改它们。 |
| `02-start.md` | 开始一个项目：在新的或已有的文件夹里输入 `/troy-pstack:troy-mode start a project: <想法>`，或者只运行 `/troy-pstack:troy-init`。troy-init 的初始化 PR 和它的问题：私有 GitHub 仓库，以及不是它写的文件。产品经理的问题和需求文档，Troy 在聊天里批准，或在 GitHub 上合并来批准。架构、环境所属的系列，以及语言步骤。已经有代码的项目（Q6）：已有测试列为遗留测试，旧代码只在改动时才检查。troy-mode 加进项目的文件。 |
| `03-features.md` | 功能循环：请求 "next feature"、"F04"、"F04 to F06" 和 "the rest of v0.1"；一个请求做到哪里为止（F07 D63）；六个 PR 和各自的内容；每个阶段之后 Troy 看到什么；批准前几个功能的 PR 1 和 PR 2，以及之后的那个问题（F07 D62）；审查、轮次和尝试次数；有争议的测试、覆盖率缺口和新依赖这三种旁支 PR；在 Troy 电脑上跑的性能测试。 |
| `04-bugs-and-changes.md` | bug："bug: ..." 或 "fix #12"，以及 bug 的两个 PR。需求变更："change: ..."、Troy 的批准、需要返工的功能，以及对已验收功能的变更会成为一个新功能（F07 D65）。问题和实验，它们不开 PR。 |
| `05-release.md` | 版本第一个功能开始之前的版本测试计划（F08 D70）。"Release v0.1"：版本测试、发布 PR、在 Troy 电脑上跑的发布测试，以及 Troy 在自己设备上的测试，和 Troy 可以给的三种回复（F08 第 5.6 节）。未修复的 bug 和推迟其中一个。验收、状态和 GitHub release。补丁版本。复盘，以及从中挑选规则。 |
| `06-rules.md` | "Add a rule ..."：架构师的提案，Troy 的一次回答既批准规则，也选择现有代码怎么处理（F09 D82），基线和清理 PR，修改和废止规则，调整 troy-mode 的规则（比如 R03 的上限），以及适用于所有项目的规则，Troy 同意后会成为 troy-pstack 里的 issue（F09 D83）。 |
| `07-taking-part.md` | Troy 在哪些地方参与：需求文档 3.3 的五个步骤，以及怎样回答升级（原型 C）。troy-mode 自己做什么：它的合并权限（R18，F07 D61 和 D62）、F07 第 9 节的其他操作、Troy 验收版本之后的 GitHub release，以及没有 Troy 同意就不碰项目以外的任何东西。项目使用的功能状态标签（F01 第 7 节，R13）。在新会话里继续（5.10）：进度文件和 "continue"。 |
| `08-reference.md` | troy-mode 能理解的每种请求和对应的流程。按种类列出 PR 标题和分支。troy-mode 在 PR 评论里用的标题。项目里的文件，以及谁可以改哪个。配置项。R01 到 R21 规则，每条一行，并链接到规则模板。问题和解决办法：合并被拒、钩子挡住了角色、只在一个平台上运行的测试（F07 D69）、Windows 路径长度，以及项目里的 troy-mode 副本比插件旧。 |
| `09-changing-troy-mode.md` | 给在 troy-pstack 里改 troy-mode 本身的工作：需求文档和设计文档在哪里；开发流程（Troy 批准的设计、由另一个代理按设计先写测试、埋 bug、试运行，最后是状态 PR）；推送前要跑的检查；在 Troy 的长期许可下，在 `ZJUCao/troy-mode-trial` 上的试运行（第 4.4 节）；谁来合并 troy-pstack 的 PR；以及发布新的插件版本（第 6 节）。 |

实现时如果拆分或合并页面读起来更好，可以调整，只要表里的内容都在，每一页都有镜像。

### 4.2 页面怎么写

- **请求按 Troy 实际输入的样子写。** 英文页面给英文请求。中文页面给同样请求的中文说法，因为 troy-mode 用 Troy 的语言和 Troy 交流（F07 第 2 节）。
- **示例来自真实运行。** troy-mode 在一个阶段、一次发布测试或一份规则提案之后说的话，摘自 F07、F08 和 F09 在 `ZJUCao/troy-mode-trial` 上的试运行记录，经过缩短，并链接到试运行的 PR。需求文档 3.4 的原型只是文字模拟，指南不把它们当作输出。
- **每个事实只有一个来源。** 写到某条规则、某个上限或某项决定的页面，链接到规定它的需求或设计，这样以后改动时只需改一处。命令、标题、评论标题和路径都从技能和引擎里复制，不凭记忆重打。
- **状态用词遵守 R13。** 指南不会把一个流程说得比它的状态更完成、更可用。F10 合入时，每个功能最多是"在示例项目上跑通"，指南会说明试点（F11）才是第一次真实使用。
- **风格。** 和上游指南一样，用短句和第二人称，遵循 `technical-writing` 技能的写法。

### 4.3 合并权限

troy-mode 在自己的权限范围内合并自己的 PR（R18）。Claude Code 的自动模式仍可能把 `gh pr merge` 当作未经审查的合并而拒绝，在 troy-pstack 里就发生过一次。这时 F07 会停下来，说出需要加的权限（F07 第 8.6 节）。`01-install.md` 给出 Troy 在开始前要加到项目 `.claude/settings.local.json` 里的那一行：

```json
{ "permissions": { "allow": ["Bash(gh pr merge *)"] } }
```

这个文件不进 git，是 Troy 自己的，所以 troy-init 不写它。指南会说明：这让 troy-mode 在那个项目里合并任何 PR 都不再弹出提示，而它的权限只允许合并 R18 允许的那些 PR。

### 4.4 试运行的长期许可

`09-changing-troy-mode.md` 记录 Troy 在 2026-11-08 以 `autoMode.allow` 规则的形式，加到 troy-pstack 的 `.claude/settings.local.json` 里的长期许可（F08 设计第 11.3 节）：加载 troy-pstack 的嵌套 `claude -p` 会话，可以不经询问在 `ZJUCao/troy-mode-trial` 里创建分支、issue 和 PR，并合并 PR。这一页也写明它不包括什么：其他任何仓库、推送 `main`，以及创建或删除仓库。如果试运行仍然被拒绝，会话会告诉 Troy，不会绕过去。

## 5. F10 不写什么

- **不再抄一遍设计。** 指南讲 Troy 输入什么、看到什么，每一步内部怎么运作，链接到设计文档。
- **不写中文 README。** README 里混着 Lauren 的文字、移植说明和 troy-mode 的一节，只有 troy-mode 的文档遵守 R12。中文 README 要翻译上游的文字，并且每次合并上游都会走样（D87）。README 链接到中文指南。
- **不改上游的指南**，也不改 `poteto-help`。

## 6. 插件版本（D89）

Claude Code 从插件市场安装插件时会复制一份，只有 `.claude-plugin/plugin.json` 里的 `version` 升高时才更新这份副本。troy-pstack 现在仍是 0.1.0，也就是分叉时的版本，而 troy-init 会把这个数字记进每个项目的 `.troy-mode/install.toml`，并写进升级 PR 的标题（F06 第 6 节）。F10 把它升到 **0.2.0**，这是第一个为使用而写了 troy-mode 文档的版本，并让两处描述都提到 troy-mode：

- `plugin.json`："Troy's Claude Code fork of Lauren Tan's pstack 0.15.36: verification-first engineering skills, principles, and subagent workflows, plus troy-mode, Troy's own workflow from requirements to released versions. Not affiliated with or endorsed by Lauren Tan or Cursor."
- `marketplace.json`：同上，和现在一样不带最后一句。

F10 合入后，Troy 按 README 说的运行 `claude plugin update troy-pstack@troy-pstack` 并重启 Claude Code，或者第一次安装这个插件。从那以后，凡是改变项目所得内容的 troy-pstack PR 都要再升版本：修复升补丁号，功能升次版本号。`09-changing-troy-mode.md` 会写明这一点，F11 也靠它把修复带进试点项目。

## 7. 对之前功能的改动

- **troy-pstack 的 CI。** `troy-docs.yml` 在 `check_pairs.py` 之后运行 `python3 troy-mode/dev/check_links.py`。它的触发条件已经覆盖所有 Markdown 文件和 `troy-mode/dev/**`。
- **F01 到 F09** 不变。F10 读取它们的技能、引擎和设计，事实核对（第 9.3 节）可能会发现某个设计和实际实现对不上。这种不一致在 F10 的 PR 之前，用它自己的 PR 修正设计或代码，F10 的 PR 描述会列出来。

## 8. F10 和需求的对应

| 需求 | F10 在哪里覆盖 |
| --- | --- |
| F10 行：README 里的一节 | 第 3 节 |
| F10 行：中英文使用指南 | 第 4 节 |
| F10 行：注明 troy-mode 是 Troy 自己的作品 | 第 3.2 节 |
| 3.1 和 3.2：命令，以及 troy-mode 还是 poteto-mode | 第 3.1 节和第 4.1 节 |
| 3.3：Troy 在哪些地方参与 | `07-taking-part.md` |
| 5.1 到 5.10：每个流程 | `02-start.md` 到 `07-taking-part.md` |
| 7.1 和 R13：状态标签 | 第 4.2 节和第 9.5 节 |
| 第 8 节：不影响 troy-pstack，合并上游仍然容易 | 第 2 节和第 5 节 |
| 第 8 节：语言，中英文对照 | 第 4.1 节和第 9 节 |
| Q10：每个功能一个 PR | 第 1 节 |

## 9. F10 怎样检查

### 9.1 链接检查（D90）

`troy-mode/dev/check_links.py` 和 `check_pairs.py` 一样，只用 Python 3.11 或更新版本以及标准库。它读取 `README.md` 和 git 跟踪的 `docs/troy-mode/` 下的每个 Markdown 文件，检查代码块和行内代码之外的每个链接：

- 指向文件的链接，相对于所在文件的文件夹，必须指向 git 跟踪的文件。指向文件夹的链接必须指向被跟踪的文件夹。
- 锚点，比如 `../requirements.md#72-feature-list` 或 `#troy-mode`，必须按 GitHub 的规则对上目标 Markdown 文件里的某个标题：转成小写，去掉 `-` 和 `_` 以外的标点，空格变成 `-`，中文字符保留，重复的标题依次加上 `-1`、`-2`。
- 带协议的链接，比如 `https:` 或 `mailto:`，不检查，因为 CI 不应依赖其他网站。

它打印每个坏链接及其文件和行号。退出码和 `check_pairs.py` 一样：所有链接都能解析时为 0，有链接解析不了时为 1，脚本无法运行时为 2。

### 9.2 测试和埋 bug

在脚本写出来之前，由另一个代理按这份设计用 `unittest` 和一个临时 git 仓库写 `test_check_links.py`。用例包括：缺失的文件、未跟踪的文件、指向文件夹的链接、同一文件和另一文件里的锚点、中文标题、重复标题、带标点和行内代码的标题、代码块和行内代码里的链接（忽略）、引用式链接，以及 `https:` 链接（忽略）。

代码通过之后，在一份临时副本里一次埋一个 bug，每个都必须让某个测试失败。包括：不检查锚点、锚点里丢掉中文字符、重复标题没有编号、检查了代码块里的链接、接受未跟踪的文件，以及检查了带协议的链接。数量写进 PR 描述。

### 9.3 事实核对

PR 开出来之前，由一个没有写过指南的新代理，把指南和它的来源对照着读：`troy-mode` 和 `troy-init` 两个技能、各引擎的 `--help` 输出、代理文件、F01 的模板、需求文档，以及 F01 到 F09 的设计。它列出指南里每一个没有来源支持、或与来源矛盾的请求、命令、PR 标题、评论标题、路径、配置项和状态文字。每一条要么修正，要么在 PR 描述里说明为什么保留。

### 9.4 读者测试

两个新代理各自只读一种语言的指南，不读其他任何文件，然后像 Troy 需要的那样回答下面的问题：

1. 怎样安装 troy-pstack，怎样确认 troy-mode 已经在里面？
2. 怎样把一个空文件夹变成 troy-mode 项目？
3. 我的项目已经有代码和测试，它们会怎样？
4. 做下一个功能要输入什么？troy-mode 会在哪里停下来等我？
5. 不打开 GitHub，怎样批准一份设计？
6. 做完三个功能后，troy-mode 问我还要不要继续批准设计。每种回答会怎样？
7. 我在一个已验收的功能里发现了 bug。我输入什么，接下来有哪些 PR？
8. 我想让一个已验收的功能换个做法。它的测试会怎样？
9. 怎样发布 v0.1？troy-mode 会让我在自己的设备上做什么？
10. 发布时有个场景在我手机上失败了。我怎么回复，接下来会怎样？
11. 现有代码违反了一条新规则时，怎样给这个项目加这条规则？
12. 怎样提议一条适用于所有 troy-mode 项目的规则？
13. troy-mode 因为升级停下来了。我的回答要包含什么？
14. 我在一个功能做到一半时关掉了会话。怎样在新会话里继续？
15. 合并因为权限被拒绝了。我该怎么办？
16. "在 main 上通过测试"和"在 Troy 的设备上可用"有什么区别？
17. 怎样让某个项目里的开发者用 opus、高推理强度运行？
18. 怎样把更新的 troy-mode 带进一个已有的项目？
19. troy-pstack 里哪些部分是 Lauren Tan 的作品，哪些是 Troy 的？

实现的会话按设计文档给每个回答打分。答错或答不出，就修改指南，并把那个问题交给一个新代理再问一次。PR 描述给出每种语言的结果。

### 9.5 状态

| 时间点 | 需求文档 7.2 中 F10 的状态 |
| --- | --- |
| F10 的 PR 合入 | 已编写：README 一节和中英文指南，按 F01 到 F09 的实际实现编写。对照检查和链接检查通过，事实核对没有遗留的不一致，读者测试只靠指南就答对了每种语言的全部 19 个问题。尚未在真实项目上照着使用。 |
| 试点（F11）结束，指南的修正已合入 | 在真实项目上使用：Troy 在 <项目> 的试点中照着指南做了，试点发现的指南问题已修正。 |

"在示例项目上跑通"不适用：读者测试只是读指南，指南里没有东西会运行。状态更新是它自己的 PR。

## 10. 不在 F10 里

- 修改上游的指南、`poteto-help` 或任何上游技能。
- 中文 README（D87）。
- 检查指向其他网站的链接。
- 给 Troy 以外的人看的文档，比如公开的安装页面（需求文档第 9 节：只有一个用户）。
- 试点本身，以及试点发现的指南修正（F11）。

## 11. 需要 Troy 决定的事项

F09 的设计到 D85 为止，所以 F10 从 D86 开始。Troy 于 2026-11-08 接受了全部推荐答案。

| 编号 | 问题 | 选项 | 推荐并已批准 |
| --- | --- | --- | --- |
| D86 | 指南放在哪里？ | A：单独的文件夹 `docs/troy-mode/guide/`，大约十页，每页都有中文镜像，和需求文档、设计文档放在一起（第 4 节）。B：作为新页面放进上游指南 `docs/guide/`。C：一个很长的页面 `docs/troy-mode/guide.md` 和它的镜像。 | A。上游指南是 Lauren 的作品，而且只有英文，改它会混淆作者归属，也让合并上游更难（需求文档第 8 节）。C 每种语言都是一个很长的页面。 |
| D87 | README 这一节要不要双语？ | A：只用英文，写在 `README.md` 里，链接到两种语言的指南（第 5 节）。B：另外为整个 README 写一份中文 `README.zh-CN.md`。 | A。README 的其余部分是上游和移植的文字，R12 不管它们，中文副本每次合并上游都会走样。中文由指南承担。 |
| D88 | 怎样注明 troy-mode 是 Troy 自己的作品？ | A：在 README 这一节和指南首页的开头放第 3.2 节的声明，并在 `plugin.json` 和 `marketplace.json` 里写明 troy-mode 是 Troy 的。B：同 A，另加一个单独的 `NOTICE` 文件。 | A。声明放在读者第一次见到 troy-mode 的地方。许可证同样是 MIT，`NOTICE` 文件说的内容，`LICENSE` 和声明都已经说了。 |
| D89 | F10 要不要升插件版本？ | A：要，升到 0.2.0，之后凡是改变项目所得内容的 troy-pstack PR 都再升版本（第 6 节）。B：不升，保持 0.1.0。C：升到 1.0.0。 | A。不升版本，已安装的 troy-pstack 永远拿不到 troy-mode，每个升级 PR 也都写着 0.1.0。1.0.0 应该等试点用过之后。 |
| D90 | 文档怎样检查？ | A：对照检查、CI 里新的链接检查（第 9.1 节）、新代理做的事实核对，以及两种语言的读者测试（第 9.3 节和第 9.4 节）。B：同 A，但不写链接检查脚本，由一个代理检查一次链接。C：同 A，再加上在 `ZJUCao/troy-mode-trial` 上用嵌套 `claude -p` 会话照着指南从初始化走到第一个功能的 PR 1，约 5 到 10 美元。 | A。链接检查很小，只用标准库，能防止指南里大量指向设计和需求的链接以后失效。C 重复了试运行和试点已经做的事：试点紧接着就会在真实项目上照着指南做。 |
| D91 | F10 什么时候做？ | A：F09 合入之后，这样指南按已实现的 F08 和 F09 来写；在 F11 之前，这样 Troy 在试点中用得上指南。于是 F10 那一行依赖 F08 和 F09，F11 那一行也依赖 F10。B：现在就做，和 F09 并行，按 F08 和 F09 的设计来写，它们合入后再补一个 PR。C：F11 之后再做，这样指南能写进试点的经验。 | A。指南对照已实现的代码检查，试点是它的第一个真实读者。B 要把两个流程写两遍。C 让 Troy 在试点期间没有指南可用。这会改动需求文档 7.2 的依赖列和依赖图。 |
| D92 | 指南要不要涵盖改 troy-mode 本身的工作？ | A：要，最后一页 `09-changing-troy-mode.md`：文档、开发流程、检查、试运行和 Troy 对试运行的长期许可、谁来合并，以及插件版本（第 4.1 节和第 4.4 节）。B：不要，指南只讲怎样使用 troy-mode。 | A。这些规则现在只写在设计文档和代理的本地记忆里。放进仓库的一页，任何会话和 Troy 都能看到。 |

需求文档 1.26 记录了批准的改动：

- F10 行写明 F10 实现什么（D86 到 D90），并依赖 F08 和 F09（D91）。
- F11 行也依赖 F10，依赖图用 `F08 --> F10`、`F09 --> F10` 和 `F10 --> F11` 替换 `F07 --> F10`（D91）。
- 第 8 节"语言"：troy-pstack 的 CI 还会检查 troy-mode 文档里的相对链接和锚点都能解析（D90）。

## 12. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-08 | 初稿。 |
| 1.0 | 2026-11-08 | Troy 批准，含 D86 到 D92，全部采用推荐答案。 |
