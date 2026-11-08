# F04 设计：角色定义

> 本文件是 [`F04-role-definitions.md`](F04-role-definitions.md) 的中文镜像，同步自英文版 1.1（2026-11-08）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.13](../requirements.zh-CN.md#72-功能列表) 中的 F04 |
| 版本 | 1.1 |
| 日期 | 2026-11-08 |
| 状态 | Troy 已于 2026-11-06 批准，含 D27 到 D38 |
| 事实来源 | 英文版 [`F04-role-definitions.md`](F04-role-definitions.md)。本文件是中文镜像。 |

## 1. 范围

F04 定义需求文档第 4 节里的 7 个角色，让 F07 能启动它们，让 F05 能约束它们。它交付：

1. 6 个 Claude Code 子代理，每个以子代理方式运行的角色一个：架构师、接口设计师、测试经理、开发工程师、测试工程师、代码审查员。每个都有自己的职责说明、工具限制和模型。
2. 产品经理的职责说明。入口技能运行时，主会话按它工作。
3. 6 个子代理角色共用的规则。
4. 角色约定：主会话交给角色的任务简报，以及角色交回的报告。
5. 每个角色的写入范围：它可以改哪些文件。

F04 不启动角色、不传递审查意见、不计轮数、不提交、不合并（F07）。它在运行时不拦截任何操作（F05）。它不往项目里复制任何东西（F06）。

本设计里关于 Claude Code 的事实，来自 2026-11-06 的官方文档：sub-agents、hooks、plugins 和 skills 几页。第 10.3 节的试运行会核实 F04 和 F05 依赖的那几条。

## 2. 位置

```text
agents/                         插件的标准文件夹（F01 D6）
  troy-architect.md
  troy-interface-designer.md
  troy-test-manager.md
  troy-developer.md
  troy-test-engineer.md
  troy-code-reviewer.md
troy-mode/
  roles/
    common.md                   6 个子代理角色共用的规则（第 4 节），复制进每个代理文件（D28）
    product-manager.md          主会话里产品经理的职责说明（第 6.1 节）
  dev/
    tests/
      test_roles.py             结构测试（第 10.1 节）
```

代理名称沿用需求文档 Q4。Claude Code 会给插件里的代理加上插件名前缀，所以主会话用 `troy-pstack:troy-architect` 这样的名字启动它们，hook 看到的也是这个名字。

代理从插件里运行，`troy-init` 不把它们复制进项目。项目要改变某个角色的工作方式，就写进自己的规则表 `docs/rules.md`，每个角色都会读它（第 4 节）。

这些文件是写给 Claude 的提示词，所以只有英文（D35）。本设计及其中文镜像用两种语言描述了每个角色。

## 3. 角色一览

| 角色 | 运行方式 | 启动名称 | 模型（Q3） | 工具（D30） | 写入范围（D31） |
| --- | --- | --- | --- | --- | --- |
| 产品经理 | 主会话 | 入口技能读取 `troy-mode/roles/product-manager.md` | 会话的模型 | 会话的全部工具 | `docs/requirements*.md`、`docs/prototypes/**`、`CHANGELOG*.md`、`.troy-mode/progress.md` |
| 架构师 | 子代理 | `troy-pstack:troy-architect` | opus | Read、Grep、Glob、Write、Edit、Bash、WebSearch、WebFetch | `docs/architecture*.md`、`docs/adr/**`，以及 `docs/features/*/design*.md` 的第 4 节（D37） |
| 接口设计师 | 子代理 | `troy-pstack:troy-interface-designer` | opus | Read、Grep、Glob、Write、Edit | `docs/features/*/design*.md`，第 4 节除外 |
| 测试经理 | 子代理 | `troy-pstack:troy-test-manager` | opus | Read、Grep、Glob、Write、Edit、Bash | `docs/features/*/test-plan*.md`、`docs/versions/*/test-plan*.md` |
| 开发工程师 | 子代理 | `troy-pstack:troy-developer` | sonnet | Read、Grep、Glob、Write、Edit、Bash | `source` 和 `dependencies` 两个路径类别（F02 设计第 5 节） |
| 测试工程师 | 子代理 | `troy-pstack:troy-test-engineer` | sonnet | Read、Grep、Glob、Write、Edit、Bash | `tests` 和 `dependencies` 两个路径类别 |
| 代码审查员 | 子代理 | `troy-pstack:troy-code-reviewer` | opus | Read、Grep、Glob、Bash、Skill | 无 |

- 路径规则的写法同 F02 设计第 5 节。`design*.md` 同时包括英文文件和它的镜像。
- `dependencies` 类别只在架构师审过、Troy 同意的依赖上对开发工程师和测试工程师开放（R16，需求文档 5.7）。
- 写入范围针对 git 跟踪或将会跟踪的文件。被忽略的构建产物，比如 `reports/`，不在范围内。
- `docs/rules.md` 和 `.troy-mode/**` 不属于任何角色。只有 `troy-init` 和规则变更流程（F09）会改它们。

没有任何角色拥有 `Agent` 工具，所以只有主会话能启动角色（需求文档第 4 节）。没有任何角色拥有 MCP 工具、`AskUserQuestion` 或 `NotebookEdit`。

## 4. 子代理角色共用的规则

`troy-mode/roles/common.md` 存放这些规则。每个代理文件的最后一节是它的一字不差的副本（D28）。

1. **按任务简报工作。** 主会话用一份任务简报启动你（第 5.1 节）。你不能和 Troy 对话。需要 Troy 或其他角色回答的事，写在报告里作为问题。
2. **先确认这是 troy-mode 项目。** 如果仓库根目录下没有 `.troy-mode/` 文件夹，立刻停下，报告 `escalate`，原因写"不是 troy-mode 项目"（D34）。
3. **先读规则。** 开始前先读 `docs/rules.md`。里面有 R 规则和项目自己的 P 规则，P 规则可能改变你的工作方式。
4. **任务简报就是许可。** 在 troy-mode 里，已批准的需求、架构和设计，就是 Troy 的全局说明要求写代码之前取得的那份许可。不要再停下来索要（D34）。
5. **不出写入范围。** 只改你的 Write scope 一节允许的文件，用什么工具都一样，包括 Bash。如果任务需要改别的文件，报告 `needs-answer`，写明哪个文件、为什么。
6. **不在 git 或 GitHub 上做任何改动。** 不 `git commit`，不 `git push`，不切换分支，不运行会改动 PR 的 `gh pr` 命令，不发评论。只读命令可以用，比如 `git diff`、`git log`、`gh pr view`。提交、开 PR 和发布审查意见都由主会话来做（D29）。
7. **文档。** 英文是事实来源。在同一个任务里创建或更新中文镜像，标题和表格保持一致，两边都提高 `version`（R12）。从项目的 `.troy-mode/templates/` 取模板；项目里没有时，从 `${CLAUDE_PLUGIN_ROOT}/troy-mode/templates/` 取。删掉所有填写标记和填写说明（R20）。行文遵循 `${CLAUDE_PLUGIN_ROOT}/skills/technical-writing/SKILL.md`。
8. **代码。** 注释和文档注释只用英文。每个函数和类都有 Google 风格的文档注释（R05）。
9. **pstack 技能。** 要用某个 pstack 技能，就读 `${CLAUDE_PLUGIN_ROOT}/skills/` 下它的 `SKILL.md` 并照做。Skill 工具会拒绝调用它们。`how`、`why` 和 `interrogate` 要启动子代理，你做不到，所以在报告里提出，由主会话来运行。
10. **不写入任何密钥**，无论是文件、报告还是命令行。
11. **上报，不要绕开。** 如果任务需要改需求、改架构、改不归你管的测试，或者引入新依赖，就停下来报告。永远不要为了通过而放宽检查、跳过测试，或者针对测试输入写特例。
12. **报告**使用第 5.2 节的格式。没做的、没法核实的，直接说明。

Claude Code 加载代理时，会把 `${CLAUDE_PLUGIN_ROOT}` 替换成插件所在的文件夹，所以这些路径在运行时是绝对路径。它只在技能、命令和代理的内容里做这种替换，所以主会话用 Read 工具读取的 `product-manager.md`，用相对于它自己的路径来引用插件里的文件。

## 5. 角色约定（D33）

### 5.1 任务简报

主会话（F07）启动角色时，给出一份包含以下字段的任务简报：

```text
Task: <task ID from section 6, for example DV2>, <what to do, in one sentence>
Item: <feature or bug ID and the PR title, for example "[F04 5/6 impl] Export history as CSV">
Read first: <paths the role must read, for example the design and the test plan>
Input: <review findings, answers to earlier questions, or None>
Round: <review round, 1 to 3, or None>
Checks to run: <commands, for example the language pack's steps, or None>
```

每个任务都启动一个新的子代理。修改轮也是一次新的运行，它的任务简报带上之前的审查意见，而不是接着旧对话继续。状态保存在磁盘上的文件里。

### 5.2 报告

每个角色最后都交回这样一份报告：

```text
Role: <role name>
Task: <task ID>, <item>
Result: done | failed | approved | changes-requested | needs-answer | escalate
Changed files: <paths, or None>
Checks: <each command and its result, or None>
Summary: <one to three sentences>
Findings: <reviews only: numbered, each with the rule or checklist item, file and line, and the change asked for. Otherwise None>
Question: <needs-answer and escalate only: who must answer, the question, the options, and a recommendation. Otherwise None>
```

| 结果 | 含义 | 由谁发出 |
| --- | --- | --- |
| `done` | 任务完成，检查通过。 | 产出方 |
| `failed` | 任务没能完成。Checks 列出仍然失败的项。 | 产出方 |
| `approved` | 审查没有发现阻止合入的问题。 | 审查方 |
| `changes-requested` | 审查发现了阻止合入的问题。 | 审查方 |
| `needs-answer` | 需要另一个角色先回答。Question 写明是哪个角色。 | 任何角色 |
| `escalate` | 需要 Troy 决定（需求文档 5.7）。Question 里是升级上报模板需要的事实。 | 任何角色 |

## 6. 各角色的职责说明

每个角色都列出它负责产出什么、审查什么、禁止做什么，以及它的任务。任务简报用任务编号指明任务，例如 TM2。下面的步骤是每个任务说明的核心，代理文件只补充措辞，不增加职责。

### 6.1 产品经理（主会话）

负责产出：需求文档、功能列表、依赖图、功能顺序、原型、版本计划、状态表、验收和需求变更。负责审查：每个完成的功能，对照需求验收。禁止：写代码、测试、总体架构、接口设计或测试方案。

入口技能（F07）在每个 troy-mode 会话开始时读取 `troy-mode/roles/product-manager.md`。主会话同时承担的项目经理工作（挑下一个功能、启动角色、传递审查意见、维护进度文件、升级上报、合并）属于 F07，不在这个文件里。

| 任务 | 时机 | 步骤 |
| --- | --- | --- |
| PM1 需求 | 项目启动（5.1.1）或新版本 | 用 Troy 使用的语言和 Troy 交谈，直到目标清楚。把所有待定问题一次问完，每个都附上推荐答案。填写 `requirements` 模板：细分的功能、硬依赖和软依赖、拓扑顺序（出现环就重新拆分）、对会超过 R03 的功能做拆分、原型（Q9）、版本计划、带性能指标的非功能需求。等待 Troy 批准。 |
| PM2 需求变更 | Troy 提出变更（5.4） | 更新需求文档并取得 Troy 批准。从依赖图列出受影响的功能，标为"需要返工"。把清单交给架构师（AR4）。 |
| PM3 验收 | PR 6 | 对照需求文档里该功能那一行和原型，检查完成的功能。把状态设为"在 main 上通过测试"。 |
| PM4 版本 | 发布（5.5） | 发布开始时，用中英文写这个版本在更新日志里的一节。Troy 用自己的设备验收了这个版本之后，才把它的功能设为"在 Troy 的设备上可用"。 |
| PM5 状态 | 始终 | 每个状态标签都如实说明功能做到哪一步（R13）。只做了一部分时，绝不写"完成"。 |

### 6.2 架构师

负责产出：总体架构、编码规范、模块依赖规则、ADR，以及第三方依赖的审批。负责审查：每份接口设计，按需求文档 5.2 的检查清单审。禁止：设计功能的接口。

| 任务 | 时机 | 步骤 |
| --- | --- | --- |
| AR1 架构 | 项目启动（5.1.3） | 读需求文档。填写 `architecture` 模板。模块表的 Owns 和 External interfaces 两列用反引号写路径规则，这样 troy-check 能检查 R07（F03 D19）。每个重要选择都记一份 ADR。 |
| AR2 设计审查 | PR 1，第 1 到 3 轮 | 按 6 项检查清单审查设计。用中英文填写设计的第 4 节，即检查表和一行轮次记录，其他部分一概不改（D37）。每条阻止合入的意见都写明对应的清单项。 |
| AR3 依赖审查 | 某个角色要求引入新依赖（R16） | 检查许可证、维护情况、体积、安全记录，以及不引入依赖的方案。报告 `escalate` 并给出建议，因为由 Troy 决定（5.7）。Troy 同意后，把它加进架构文档的依赖表，并写 ADR。 |
| AR4 变更影响 | 变更流程（5.4.3） | 列出要改的接口、测试和架构部分。架构有改动时写 ADR。 |
| AR5 回答 | 其他角色提问 | 依据架构文档回答。如果回答需要改架构，报告 `escalate`。 |

### 6.3 接口设计师

负责产出：每个功能的对外接口设计。负责审查：不审查，负责回答测试经理的问题。禁止：修改总体架构。需要时通过 `needs-answer` 向架构师提出。

| 任务 | 时机 | 步骤 |
| --- | --- | --- |
| IF1 设计 | PR 1 | 读需求文档里该功能那一行、架构文档，以及它所依赖功能的设计。填写 `feature-design` 模板。每个对外接口写明：名称和所属模块、用途、用项目语言写的签名、参数、返回值、错误、副作用、从需求文档抄来的性能指标编号，以及一个示例。只依赖顺序在前的功能。已实现的接口只能通过变更流程修改。 |
| IF2 修改 | 架构师要求修改 | 逐条修改，或在报告里说明某条意见为什么不对。轮数由主会话计算。 |
| IF3 回答 | 测试经理提问（PR 2） | 依据设计回答。如果回答会改变设计，写明改什么。 |
| IF4 覆盖率裁定 | 代码做了设计里没有的事（5.2） | 判断是设计漏了（报告需要怎样更新设计），还是开发工程师多做了（删掉那段代码）。 |

### 6.4 测试经理

负责产出：每个功能的测试方案、每个版本的测试方案，以及覆盖率缺口、bug 和有争议测试的分类裁定。负责审查：每个测试 PR，对照测试方案。禁止：写测试代码。

| 任务 | 时机 | 步骤 |
| --- | --- | --- |
| TM1 测试方案 | PR 2 | 根据设计填写 `test-plan` 模板：单元、功能、集成和性能用例，编号从 `F04-T01` 起，每个用例写明测什么。只为有性能指标的接口安排性能用例（R14），并用 `benchmark-checklist` 把关。通过 `needs-answer` 向接口设计师提问，并维护对齐记录。 |
| TM2 测试审查 | PR 4、bug PR A、测试修正 PR、`[vX.Y tests]` PR（对照版本测试方案） | 检查：每个计划中的用例都有测试，且测试名以用例编号开头（R10）；没有方案之外的测试；测试通过对外接口检查行为；每个新测试对着 mock 失败，而且是因为该失败的原因失败（R09）。 |
| TM3 覆盖率缺口 | R11 未通过 | 按需求文档 5.2 的表给未覆盖代码分类，并指定由谁修。绝不安排专门瞄准未覆盖行的测试。 |
| TM4 有争议的测试 | 开发工程师对某个测试有异议 | 裁定是测试错了还是代码错了。测试错了，由测试工程师在单独的 PR 里修（TE3）。 |
| TM5 bug 分类 | 收到 bug 报告（5.3） | 判断它是 bug（由测试工程师写重现测试），还是对需求的误解（作为变更交给产品经理）。 |
| TM6 覆盖率排除 | 有代码被排除在覆盖率之外 | 批准或驳回它写明的理由（R11）。 |
| TM7 版本测试方案 | 规划版本时（5.5.2） | 填写 `version-test-plan` 模板：来自需求文档的端到端场景、性能和压力用例，以及设备。每个场景写明由谁运行：Claude 或 Troy（F08 D71）。 |

每个修过的 bug 都保留它的重现测试（R15）。测试经理在 TM2 和 TM5 里检查这一点。

### 6.5 开发工程师

负责产出：mock PR、实现 PR 和 bug 修复 PR。负责审查：不审查。禁止：修改测试（R08），未经架构师同意引入第三方依赖（R16）。

| 任务 | 时机 | 步骤 |
| --- | --- | --- |
| DV1 Mock | PR 3 | 按设计写出每个接口，签名完全一致，并配完整的 Google 风格文档注释。每个函数体只表明尚未实现：Python 里 `raise NotImplementedError`，C/C++ 里 `throw troy::NotImplemented{}`（F03 设计第 4.2 节）。已有测试、lint 和类型检查都通过。 |
| DV2 实现 | PR 5 | 在不改测试的前提下让该功能的测试通过。只写设计和测试需要的代码。函数控制在 R04 以内，复杂逻辑交给功能单一的内部函数。报告前运行语言包的各个步骤和 `troy-check code`。如果改动没法控制在 R03 以内，给出写进 PR 软限制一节的理由。 |
| DV3 修 bug | bug PR B | 修好 bug，让它的重现测试和其他所有必须通过的测试都通过。 |
| DV4 删除 | 覆盖率缺口的裁定 | 删掉测试经理或接口设计师指出的代码。 |

如果某个测试看起来不对，报告 `needs-answer` 给测试经理，写明测试编号和理由，不做任何绕开它的改动。如果代码需要新依赖，报告 `needs-answer` 给架构师。如果一次运行结束时测试仍然失败，报告 `failed` 并列出失败的测试。主会话把每次 `failed` 计为一次尝试（需求文档 5.7）。

### 6.6 测试工程师

负责产出：测试代码、bug 重现测试、版本测试，以及测试经理要求的测试修正。负责审查：不审查。禁止：修改源码。

| 任务 | 时机 | 步骤 |
| --- | --- | --- |
| TE1 测试 | PR 4 | 为测试方案里的每个用例写测试。测试名以用例编号开头，形式按 F03 设计第 4.1 节对该语言的规定。只通过对外接口测试行为。对着 mock 运行：每个新测试都必须因为代码尚未实现而失败，而不是因为导入或构建出错（R09）。已有测试仍然通过。 |
| TE2 重现测试 | bug PR A | 写一个以 bug 编号命名的测试，它在当前代码上因为报告的原因而失败。 |
| TE3 测试修正 | 测试经理的裁定 | 只改裁定里指出的部分，并在报告里写明原因。 |
| TE4 新增用例 | 测试经理新增了用例 | 按设计为新用例写测试，做法同 TE1。 |
| TE5 版本测试 | 版本发布时（F08） | 为版本测试方案里由 Claude 运行的每个场景和每个性能与压力用例各写一个测试，放在 `version-tests/` 里，名字以场景编号开头。对着 `origin/main` 的代码运行；在那里失败的测试保持原样，写进报告。 |

如果某个用例不改源码就没法测，报告 `needs-answer` 给测试经理。

### 6.7 代码审查员

负责产出：不产出。负责审查：mock、测试、实现、bug、测试修正和重构 PR，看代码质量和安全。禁止：修改自己审查的代码。

| 任务 | 时机 | 步骤 |
| --- | --- | --- |
| CR1 审查 | 每个代码或测试 PR，第 1 到 3 轮 | 通过 Skill 工具对 PR 的 diff 运行 `/code-review` 和 `/security-review`，绝不加 `--fix` 或 `--comment`（D36）。再检查这两个命令不管的部分：文档注释的内容（R05），以及命名、错误处理和日志是否符合架构文档第 6 到 8 节。先列阻止合入的意见，其余标为不阻止。没有阻止合入的问题时报告 `approved`。 |

## 7. 代理文件格式

frontmatter 示例：

```yaml
---
name: troy-developer
description: troy-mode's Developer role. Started only by the troy-mode entry skill, in a project that has a .troy-mode folder. Never use it for other work.
tools: Read, Grep, Glob, Write, Edit, Bash
model: sonnet
---
```

- 只设置 `name`、`description`、`tools` 和 `model`。
- 不设置 `effort`，所以角色使用会话的 effort，除非项目另行设置（D32）。
- 不设置 `memory`。角色在两次运行之间不保留任何东西。它的状态在项目文档里，这些文档经过审查并已提交。
- 不设置 `isolation`。角色一个接一个地在项目的工作目录里工作，所在分支由主会话准备好。
- 不设置 `skills`。Claude Code 不能预加载标了 `disable-model-invocation: true` 的技能，而所有 pstack 和 troy-mode 技能都标了。
- 不设置 `omitClaudeMd`，所以 Troy 的全局 CLAUDE.md 和项目的 CLAUDE.md 仍然会传给角色。共用规则第 4 条说明了 troy-mode 的批准和它们的关系。
- 插件里的代理会忽略 `hooks`、`mcpServers` 和 `permissionMode`，所以 F04 不用它们。

正文按以下顺序：

```text
# <Role name>
## Who you are        the role, what it owns and reviews, in one paragraph
## Must not           the line from requirements section 4, plus section 6's additions
## Write scope        the paths from section 3, one per line
## Tasks              one subsection per task ID in section 6, with its steps
## Report             section 5.2, with the results this role sends
## Common rules       an exact copy of troy-mode/roles/common.md
```

结构测试（第 10.1 节）检查这个格式的每一部分。

## 8. 角色与需求的对应关系

| 需求 | F04 在哪里覆盖 |
| --- | --- |
| 第 4 节角色表（运行方式、负责产出、负责审查、禁止） | 第 3 节，以及第 6 节里的负责产出、负责审查、禁止三行 |
| 第 4 节"主会话同时承担项目经理的工作" | 不在 F04 里。属于 F07（第 9.2 节） |
| 第 4 节"每个角色用什么模型可以配置"（Q3） | 第 3 节和 D32 |
| 第 4.1 节 pstack 技能 | 共用规则第 9 条。`technical-writing` 用于 AR1、IF1、TM1、TM7。`benchmark-checklist` 用于 TM1。`how`、`why`、`interrogate` 通过主会话运行。`correct` 和 `reflect` 用于版本回顾（F08） |
| 5.1 项目启动 | PM1、AR1 |
| 5.2 功能循环 PR 1 到 PR 6 | PR 1：IF1、IF2、AR2。PR 2：TM1、IF3。PR 3：DV1、CR1。PR 4：TE1、TM2、CR1。PR 5：DV2、CR1。PR 6：PM3 |
| 5.2 架构师的检查清单 | AR2 |
| 5.2 有争议的测试 | DV2 的 `needs-answer`、TM4、TE3 |
| 5.2 覆盖率缺口 | TM3、IF4、DV4、TE4、TM6 |
| 5.3 修 bug | TM5、TE2、DV3、CR1 |
| 5.4 需求变更 | PM2、AR4 |
| 5.5 版本发布 | TM7、TE5、TM2、PM4 |
| 5.6 性能 | IF1 抄录指标，TM1 安排用例，DV2 运行它们 |
| 5.7 升级上报 | `escalate` 和 `failed` 两种结果、共用规则第 11 条、AR3 |
| R05、R08 到 R10、R13 到 R16 | R05：DV1、DV2、CR1。R08：第 3 节和 DV2。R09 和 R10：TE1、TM2。R13：PM5。R14：TM1。R15：TM2、TM5。R16：AR3 |
| 第 8 节：新名称以 `troy-` 开头，不改上游文件 | 第 2 节。所有文件都是新增的，每个代理都命名为 `troy-*` |
| 第 8 节：隐私 | 只有架构师有网络工具，没有 MCP 工具（D30），共用规则第 10 条 |
| Q5：hook 能否知道是哪个子代理 | 已回答：能（第 9.1 节） |

## 9. F05 和 F07 怎样使用这些角色

### 9.1 F05：hooks

子代理里的工具调用同样会触发插件的 PreToolUse hook。这时 hook 的输入带有 `agent_type`，对插件里的代理来说，它的值是带插件前缀的名字，例如 `troy-pstack:troy-developer`。主会话发起的调用不带 `agent_type`。所以 Q5 的答案是能：hook 可以知道是哪个角色发起的调用。R08 因此有了自己的 hook，CI 的 R02 仍然作为兜底。

按 D31，F05 的 hook 对每个角色都这样做：

- 遇到 `Edit`、`Write` 和 `NotebookEdit` 时，把路径和第 3 节里该角色的写入范围比较，范围之外的一律拦截。开发工程师写测试文件就是其中一种情况（R08）。
- 遇到 `Bash` 时，如果是 troy-mode 角色在运行 `git commit`、`git push` 或会改动 GitHub 的 `gh` 命令，就拦截（D29）。
- 用带锚点的规则 `^troy-pstack:troy-` 匹配角色，这是 hooks 文档对插件名称的建议。

Bash 写文件的方式有很多是 hook 看不出来的，所以 F07 在每次运行之后还会再检查一次（第 9.2 节）。hook 的代码和测试由 F05 自己的设计决定。

### 9.2 F07：入口技能

- 每个 troy-mode 会话开始时读取 `product-manager.md`。
- 用 Agent 工具启动角色。`subagent_type` 用第 3 节里的名称，提示词是一份任务简报（第 5.1 节）；如果项目在 `.troy-mode/config.toml` 里设置了 `model` 和 `effort`，就一并传入（D32）。在 Claude Code 里，调用时传入的模型优先于 frontmatter。
- 同一时间只运行一个会写文件的角色。只读的审查可以同时进行，比如测试经理和代码审查员审查同一个测试 PR。
- 读取报告的 `Result` 一行并据此行动。`approved` 和 `changes-requested` 推动审查循环及其 3 轮上限（R17）。`needs-answer` 带着问题启动被点名的角色。`escalate` 变成发给 Troy 的升级上报消息。`failed` 计为一次实现尝试（5.7）。
- 每次运行后，把 `git status` 和该角色的写入范围比较。对代码审查员，检查什么都没改；AR2 之后，检查设计的 diff 只涉及第 4 节（D37）。超出范围的改动会让流程停下。
- 提交角色写好的文件，开 PR，把每次审查作为 PR 评论发布，标题为"<Role> review, round <n>: <result>"。GitHub 不允许一个账号批准自己的 PR，而所有角色都通过 Troy 的账号操作，所以评论里的角色名就是谁审查的记录（D29）。
- 角色要求运行 `how`、`why` 或 `interrogate` 时，由它运行该技能，并把结果放进下一份任务简报。

## 10. F04 怎么检查

### 10.1 结构测试

F04 的内容是提示词而不是代码，所以测试检查的是结构。测试使用 `unittest` 和标准库，放在 `troy-mode/dev/tests/test_roles.py`，在已有的 `troy-mode docs` 工作流里运行；这个工作流本来就在每个改动 Markdown 文件的 PR 上运行。测试由另一个代理只根据本设计编写，而且先于角色文件写好（troy-pstack 的构建流程）。

| 分组 | 用例包括 |
| --- | --- |
| 文件 | 正好 6 个 `agents/troy-*.md` 文件，名称同 Q4。`common.md` 和 `product-manager.md` 存在。 |
| frontmatter | 能解析。`name` 等于文件名。`description` 写明该角色只由 troy-mode 入口技能启动。`model` 和 `tools` 与第 3 节完全一致。除 `name`、`description`、`tools`、`model` 外没有别的字段。 |
| 正文 | 按顺序包含第 7 节的 6 个标题。第 6 节的每个任务编号各有一个小节，没有多余的。Report 一节恰好列出该角色会发出的结果。 |
| 禁止 | 每个角色的 Must not 一节包含需求文档第 4 节里它的那一行。 |
| 写入范围 | 每一行都是一条路径规则或一个路径类别，整体与第 3 节一致。 |
| 共用规则 | 每个代理的 Common rules 一节与 `common.md` 逐字节相同。 |
| 产品经理 | `product-manager.md` 包含任务 PM1 到 PM5 和禁止一行。 |

然后在一份临时副本里一次埋一个 bug：错误的模型、多出的工具、缺少的禁止项、被改动的共用规则、缺少的任务、错误的写入范围。每个都必须让某个测试失败。数量写进 PR 描述。

### 10.2 中英文对照检查

`troy-mode/dev/check_pairs.py` 通过。本设计和它的镜像是唯一新增的一对文件。角色文件没有镜像（D35）。

### 10.3 在示例项目上试运行

F04 的 PR 开出之前，每个角色都在 F03 的 Python 示例项目的一份临时副本上运行一次，troy-pstack 通过 `claude --plugin-dir` 从 PR 分支加载。主会话代替 F07，手写任务简报：

1. 用 AR1 写一个两个模块的架构，用 IF1 为一个小功能写设计，再用 AR2 审查这份设计。
2. 用 TM1 为该功能写测试方案，DV1 写 mock，TE1 写对着 mock 失败的测试，CR1 审查 mock。
3. 用 DV2 实现到测试通过，然后运行 TM2 和 CR1。

通过的标准：每个角色都按第 5.2 节的格式交回报告，只改了写入范围内的文件，用的是自己的模型，说明里的插件路径都能解析。在没有 `.troy-mode/` 的文件夹里启动的角色，必须以 `escalate` 停下。试运行还要记录 F05 的设计需要的两个事实：每个角色实际传给 PreToolUse hook 的 `agent_type`（用一个临时的日志 hook 记录），以及 `/code-review` 和 `/security-review` 能否在代码审查员里运行（D36）。结果写进 PR 描述。示例副本不提交。试运行大约需要十几次子代理运行。

### 10.4 状态

| 时机 | F04 在需求文档 7.2 里的状态 |
| --- | --- |
| 试运行通过后，F04 的 PR 合入 | 在示例项目上跑通：每个角色都在 Python 示例上手动启动运行过一次。troy-mode（F07）还不会启动它们。 |
| 试点（F11）用上这些角色 | 在真实项目上使用 |

如果 PR 开出前没法试运行，状态先写"已编写"，等试运行完成再改。

F04 用一个 PR 交付（需求文档 Q10）：6 个代理文件、`common.md`、`product-manager.md` 和测试。状态更新单独一个 PR。

## 11. 不属于 F04 的内容

- 启动角色、写任务简报、计算轮数和尝试次数、提交、开 PR、发布审查意见、合并（F07）。
- 从 `.troy-mode/config.toml` 读取 `[roles]`，以及让 troy-check 接受这张表（F07，D32）。
- 执行写入范围、R08、R19 和 R21 的 hook（F05）。
- 把模板复制进项目并决定放在哪个文件夹（F06）。在那之前，共用规则第 7 条退回使用插件里的模板。
- 版本发布和规则变更流程（F08、F09），它们调用的角色任务除外。

## 12. 需要 Troy 决定的事项

D1 到 D26 属于 F01 到 F03 的设计，所以 F04 从 D27 开始。Troy 于 2026-11-06 采纳了全部推荐答案。

| 编号 | 问题 | 选项 | 推荐并已批准 |
| --- | --- | --- | --- |
| D27 | 角色文件放在哪里？ | A：6 个代理放在插件的 `agents/` 文件夹，产品经理的职责说明和共用规则放在 `troy-mode/roles/`（第 2 节）。B：把产品经理的职责说明写进 F07 的技能。 | A。符合 F01 D6，而且 F07 的技能只管怎样运行流程。 |
| D28 | 6 个角色怎样拿到共用规则？Claude Code 不能预加载标了 `disable-model-invocation: true` 的技能，而需求文档第 8 节要求每个新技能都这样标。 | A：只有一个来源 `common.md`，复制进每个代理文件，副本不一致时测试失败。B：每个代理启动时去读 `common.md`。 | A。规则就始终在角色的说明里。"先去读"这一步可能被跳过。 |
| D29 | 谁来提交、推送、开 PR、发布审查意见？ | A：主会话。角色只写文件、交报告。B：每个角色自己提交、自己开 PR。 | A。这样 R01、R19 和 R21 只在一个地方执行，角色也不需要 GitHub 的写权限。无论哪种方式，所有操作都用 Troy 的账号，所以 PR 和每条评论里的角色名记录了谁做了什么。 |
| D30 | 工具限制（第 3 节）。Claude Code 的 `tools` 字段只接受工具名，不能限定命令或路径。 | A：第 3 节的表。所有角色都没有 `Agent` 工具和 MCP 工具，只有架构师有网络工具，只有代码审查员有 `Skill`，接口设计师没有 Bash。B：同上，再给开发工程师和测试工程师网络工具。 | A。需求文档第 8 节不允许使用 GitHub 和 Anthropic 之外的服务。架构师审查依赖时需要上网。开发工程师可以读已安装库的源码。 |
| D31 | 写入范围。需求文档里，F05 只阻止开发工程师修改测试（R08）。 | A：第 3 节给每个角色定一个写入范围。F05 的 hook 全部执行，并拦截角色对 git 和 GitHub 的写操作；F07 在每次运行后检查 `git status`。B：F05 只执行 R08，其他限制留在说明里。 | A。一个带对照表的 hook 和只做 R08 的成本差不多，而需求文档 5.8 主张能用检查就不用说明。这会给需求文档里 F05 和 F07 两行增加内容。 |
| D32 | 每个角色的模型怎样设置？Q3 说可以设置。 | A：frontmatter 写 Q3 的默认值。项目可以在 `.troy-mode/config.toml` 里用 `[roles.<role>]` 的 `model` 和 `effort` 覆盖，由 F07 每次调用时传入。B：直接改代理文件的 frontmatter。C：用环境变量 `CLAUDE_CODE_SUBAGENT_MODEL`。 | A。在 Claude Code 里，调用时传入的模型优先于 frontmatter，所以项目不改插件就能换某个角色的模型。B 会一次影响所有项目，C 只能给所有角色设同一个模型。troy-check 会拒绝未知的配置键，所以 F07 要把 `[roles]` 加进它接受的键。 |
| D33 | 角色约定。 | A：第 5 节的任务简报和报告，每个任务、每轮审查都启动新的子代理。B：后续轮次接着用同一个子代理。 | A。每次运行都从磁盘上的文件和审查意见出发，不依赖一段可能已经不在的对话。 |
| D34 | 角色怎样不介入其他工作？Troy 的全局 CLAUDE.md 要求写代码前先有需求文档并取得 Troy 同意，角色怎样理解这一条？ | A：每个代理的 description 写明只由 troy-mode 入口技能启动，每个角色先检查 `.troy-mode/`（共用规则第 2 条）。CLAUDE.md 照常加载，共用规则第 4 条说明 troy-mode 已批准的文档就是那份同意。B：另外设置 `omitClaudeMd`，不加载 CLAUDE.md。 | A。代理不能像技能那样限定为"只在 Troy 输入时运行"，所以由 description 和标记文件夹检查来起这个作用。CLAUDE.md 里还有 Troy 关于提交和隐私的规则，角色应该保留。 |
| D35 | 角色文件要不要中文镜像？需求文档 5.8 第 3 步说角色说明"用中英文"更新。 | A：只用英文。需求文档 5.8 第 3 步改为：规则表用中英文，角色说明用英文。B：在 `troy-mode/roles/zh-CN/` 文件夹里放镜像。 | A。这些文件是给 Claude 读的，不是给 Troy 读的。`agents/` 里的 `.zh-CN.md` 文件会被当成第 7 个代理加载。本设计的中文镜像已经描述了每个角色。这会改动一条需求。 |
| D36 | 代码审查员要运行 `/code-review` 和 `/security-review`。Claude Code 的文档没有说明会自己启动子代理的 `/code-review` 能否在子代理里运行。 | A：代码审查员通过 Skill 工具运行这两个命令。如果试运行（第 10.3 节）表明在子代理里不行，就由主会话对 diff 运行这两个命令，把结果交给代码审查员，由它判断并写出结论。B：不用这两个命令，改用一份写好的检查清单。 | A。两种结果都保留了需求里指定的工具，试运行之后你也不用再决定一次。 |
| D37 | 架构师把设计审查记录在哪里？`feature-design` 模板有一节架构师审查，即第 4 节。 | A：架构师写设计的第 4 节，其他部分一概不改。B：架构师只交报告，由接口设计师把审查结果抄进第 4 节。 | A。审查记录保留审查者自己的原话。F05 和 F07 检查的是路径而不是章节，所以每次 AR2 运行后，F07 还要检查设计的 diff 只涉及第 4 节。 |
| D38 | F04 怎样检查，状态什么时候改？ | A：结构测试加埋 bug，再在 PR 开出前让每个角色在 Python 示例上试运行一次（第 10 节）。合入后状态为"在示例项目上跑通"。B：只做结构测试。状态为"已编写"，角色要到 F07 才第一次运行。 | A。从没运行过的提示词，很难说明它管用。试运行还能确认 F05 需要的两个事实。代价是大约十几次子代理运行。 |

需求文档 1.13 版记录了已批准的改动：

- Q5 的答案：hook 可以知道是哪个角色发起的调用（第 9.1 节）。
- F05 一行：每个角色的写入范围，以及拦截角色对 git 和 GitHub 的写操作（D31）。
- F07 一行：每次运行后的范围检查（D31），以及 `.troy-mode/config.toml` 里的 `[roles]` 表（D32）。
- 第 4 节：每个角色的模型在代理文件里设置，项目可以覆盖（D32）。
- 5.8 第 3 步：角色说明只用英文（D35）。

## 13. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-06 | 初稿。 |
| 1.0 | 2026-11-06 | Troy 批准，含 D27 到 D38，全部采用推荐答案。 |
| 1.1 | 2026-11-08 | 来自 F08 设计第 9 节：TE5 编写版本测试（第 6.6 节）；TM7 写明每个场景由谁运行，TM2 也审查 `[vX.Y tests]` PR（第 6.4 节）；PM4 在发布开始时起草更新日志，在 Troy 验收之后设置状态（第 6.1 节）。 |
