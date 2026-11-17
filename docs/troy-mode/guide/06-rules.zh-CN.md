# 6. 规则

> 本文件是 [`06-rules.md`](06-rules.md) 的中文镜像，同步自英文版 0.1（2026-11-09）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.1 |
| 日期 | 2026-11-09 |
| 事实来源 | 英文版 [`06-rules.md`](06-rules.md)。本文件是中文镜像。 |

每个 troy-mode 项目都有一张规则表：`docs/rules.md` 及其镜像。R01 到 R22 这几行是 troy-mode 对每个项目都适用的规则。P01、P02 等行是项目自己的规则。加一条项目规则，你只需要一个请求和一次回答，其余的由 troy-mode 写好并合并（[F09 设计](../design/F09-rule-change.zh-CN.md)）。

## 6.1 为这个项目加一条规则

```text
/tstack:troy-mode 加一条规则：异常信息里不用 f-string
```

如果请求没有说明这条规则是给这个项目，还是给所有 troy-mode 项目，troy-mode 只问你这一个问题，并推荐“这个项目”。然后：

1. **提案。** 架构师选出可行的最强执行方式，并找出违反这条规则的现有代码。项目规则从强到弱可以这样执行：架构；lint 或 CI 检查，也就是项目已在运行的某个工具的检查、troy-check 的一项上限，或项目自己工作流里的一个步骤；或者它在规则表里的那一行，由审查者检查（审查）或由 troy-mode 遵守（流程）。项目规则从不由测试来执行（[F09 设计 D80](../design/F09-rule-change.zh-CN.md#12-需要-troy-决定的事项)）。这时还什么都不写。
2. **给你的一条消息**，用你的语言：表格里会写的规则，中英文都有，带上编号和类型；执行方式，以及为什么没有更强的方式可行；规则 PR 会改的文件；以及违反它的现有代码，附上下面的选择。
3. **你的回答**批准这条规则并做出选择，或者要求修改。这是你唯一的一步：这个流程里没有 PR 会再等你（[F09 设计 D82](../design/F09-rule-change.zh-CN.md#12-需要-troy-决定的事项)）。

违反这条规则的现有代码怎么处理，有两种选择：

| 你选择 | 会怎样 |
| --- | --- |
| 现在就修 | 规则 PR 用一份基线豁免今天已有的违规，这样 CI 保持通过。之后由清理 PR 修好代码并删除基线，每个最多 5 个文件。 |
| 只管新代码和改动的代码 | 基线保留。开发工程师或测试工程师每次改动基线里的文件时，都要修好它，并删除它的那一行基线。 |

当工具没有 `[rules]` PR 可以改的按文件豁免方式时，比如 clang-tidy 的豁免写在源文件里，troy-mode 只提供“现在就修”：清理 PR 先做，规则 PR 在它们之后才打开检查。

这是试运行里 P01 的提案，经过缩短（[PR #31](https://github.com/ZJUCao/troy-mode-trial/pull/31) 照着它执行）：

```text
Troy，规则 P01 的提案写好了，等你批准。批准之前我没有写任何文件，
也没有开分支或 PR。
规则 P01（只用于本项目）：异常信息不能在 raise 里直接写成 f-string。
类型：硬 | 执行方式：Lint（ruff EM102）
现有代码里违反规则的地方：1 个文件，1 处
- src/troy_mode_trial/counting.py:61
请你二选一：
- A. 现在就修（推荐）。规则 PR 在 pyproject.toml 里给这个文件加一行基线豁免。
  之后开一个清理 PR [refactor] Apply P01 to counting。
- B. 只管新代码和改动的代码。基线一直留着，以后谁改 counting.py 谁顺手修掉。
```

### 这些 PR

| PR | 标题 | 合并者 |
| --- | --- | --- |
| 架构，只在规则需要时 | `[docs] Change the architecture for P01` | troy-mode：你对提案的答复已经批准了它 |
| 规则 | `troy-mode/rule-p01` 上的 `[rules] Add P01, <summary>`：两种语言的规则行、工具的配置和基线 | troy-mode |
| 源文件的清理，选“现在就修”之后 | `[refactor] Apply P01 to <area>`，由开发工程师编写，代码审查员审查 | troy-mode |
| 测试文件的清理，选“现在就修”之后 | `[P01 test-fix] Apply P01 to tests`，由测试工程师编写，测试经理和代码审查员审查 | troy-mode |

基线行放在工具自己的配置里，并写明是哪条规则，例如在 `pyproject.toml` 里：

```toml
"src/troy_mode_trial/counting.py" = ["EM102"]  # baseline: P01
```

一条规则的清理 PR 排在功能循环的下一个阶段之前。试运行里，清理 PR [#32](https://github.com/ZJUCao/troy-mode-trial/pull/32) 在修复代码的同一个 commit 里删掉了 P01 唯一的一行基线。审查类规则不改任何配置，比如试运行的 P02“每条错误信息都要写出它说的是哪个文件”（[#33](https://github.com/ZJUCao/troy-mode-trial/pull/33)）：它的规则 PR 只加那一行，从此由“由什么保证”一栏写明的审查者检查它。

## 6.2 修改或废止规则

```text
/tstack:troy-mode 修改 P01：用 % 拼出来的信息也要管
/tstack:troy-mode 废止 P02
```

- **修改**走同样的步骤，以 `[rules] Change P01, <summary>` 合入。这一行保留它的起始日期，它的配置和基线在同一个 PR 里修改。
- **废止**不需要提案。troy-mode 给你看这一行，以及这个 PR 会删除的配置行和基线行，你同意就是批准。它以 `[rules] Retire P02, <summary>` 合入。这一行保留，开头写上 `Retired on <date>.`，它的编号永远不再使用。试运行在 [#34](https://github.com/ZJUCao/troy-mode-trial/pull/34) 里废止了 P02。

## 6.3 在一个项目里调整 troy-mode 的规则

永远不要改 R 行：troy-init 的升级会替换 R 行。在 troy-check 的配置允许调整的地方，比如 R03 的规模上限、R11 的覆盖率下限或 R19 的署名模式，把调整当作一条项目规则来请求：

```text
/tstack:troy-mode 在这个项目里，R03 的上限是 800 行
```

一行 P 规则记下这项调整，例如“In this project, R03's limit is 800 changed lines.”，同一个规则 PR 修改 `.troy-mode/config.toml`。对 R 规则的其他任何改动，都是适用于所有项目的规则（第 6.4 节）。

## 6.4 提议一条适用于所有项目的规则

```text
/tstack:troy-mode 所有项目的一条规则：合并的源码里不能有 TODO 注释
```

适用于所有 troy-mode 项目的规则放在 tstack 里，随新的插件版本发布。所以这个流程既不改项目，也不改 tstack（[F09 设计 D83](../design/F09-rule-change.zh-CN.md#12-需要-troy-决定的事项)）：

1. 架构师像对项目规则那样提出执行方式，写明 tstack 里要改的文件，并说明升级带来这条规则时，现有项目的代码会不会违反它。
2. troy-mode 把提案发给你，并问你是否在 tstack 里开一个 issue。
3. **只有你同意时**，它才在 tstack 里开 issue `Rule proposal: <summary>`。开 issue 会触及项目之外，所以它总是先问。你不同意，它就什么都不开。
4. tstack 按它自己的流程做出这条规则（[第 9 节](09-changing-troy-mode.zh-CN.md)），项目通过升级拿到它。

试运行里，R22（不能有 TODO 注释）的提案被拒绝了，没有开 issue。
