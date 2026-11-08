# F01 设计：模板和规则表

> 本文件是 [`F01-templates.md`](F01-templates.md) 的中文镜像，同步自英文版 1.3（2026-11-08）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.1](../requirements.zh-CN.md#72-功能列表) 中的 F01 |
| 版本 | 1.3 |
| 日期 | 2026-11-08 |
| 状态 | Troy 已于 2026-11-05 批准，含 D1 到 D6 |
| 事实来源 | 英文版 [`F01-templates.md`](F01-templates.md)。本文件是中文镜像。 |

## 1. 范围

F01 提供五样东西，后续功能都建立在它们之上：

1. 文档模板，由 `troy-init` 复制到项目里。
2. 文档头，用来把英文文档和它的中文镜像配成一对（R12）。
3. 规则表，初始内容取自需求文档第 6 节。
4. 编号格式和功能状态标签（R10、R13）。
5. PR 标题格式和 PR 描述模板（D1）。

F01 不负责把模板复制进项目（F06），不负责检查文档头（F02），也不负责填写模板（各角色，F04 和 F07）。F01 不包含代码。

本设计只描述其他功能和角色要依赖的部分：文件位置、文件名、文档头字段、章节、编号格式和标签。

## 2. 在 troy-pstack 里的位置

troy-mode 除技能、代理和 hook 以外的文件，都放在一个新的顶层文件夹里。后续功能会在 `templates/` 旁边加上 `checks/`（F02）和 `lang/`（F03）。

```text
troy-mode/
  templates/
    requirements.md          requirements.zh-CN.md
    architecture.md          architecture.zh-CN.md
    feature-design.md        feature-design.zh-CN.md
    test-plan.md             test-plan.zh-CN.md
    version-test-plan.md     version-test-plan.zh-CN.md
    adr.md                   adr.zh-CN.md
    changelog.md             changelog.zh-CN.md
    rules.md                 rules.zh-CN.md
    progress.md
    escalation.md
    pull-request.md
    README.md                README.zh-CN.md
```

`templates/README.md` 列出每个模板的用途、在项目里放在哪里，以及由哪个角色填写。它还收录编号格式（第 6 节）、状态标签（第 7 节）和 PR 类型（第 5.11 节），方便各角色在一个地方查到。

## 3. 每个模板在项目里的位置

| 模板 | 在项目里的路径 | 中文镜像 | 由谁填写 | 在哪些环节修改 |
| --- | --- | --- | --- | --- |
| `requirements` | `docs/requirements.md` | 有 | 产品经理 | 项目初始化、需求变更、PR 6、版本验收 |
| `architecture` | `docs/architecture.md` | 有 | 架构师 | 项目初始化、需求变更 |
| `feature-design` | `docs/features/<功能编号>-<短名>/design.md` | 有 | 接口设计师 | PR 1 |
| `test-plan` | `docs/features/<功能编号>-<短名>/test-plan.md` | 有 | 测试经理 | PR 2、测试修正 |
| `version-test-plan` | `docs/versions/<版本>/test-plan.md` | 有 | 测试经理 | 版本规划、版本验收 |
| `adr` | `docs/adr/ADR-<四位编号>-<短名>.md` | 有 | 架构师 | 每个架构决策 |
| `changelog` | `CHANGELOG.md` | 有 | 产品经理 | 版本发布 |
| `rules` | `docs/rules.md` | 有 | troy-mode | 项目初始化、规则变更流程 |
| `progress` | `.troy-mode/progress.md` | 无 | 主会话 | 每个阶段。只在本地，被 git 忽略（Q8）。 |
| `escalation` | 无。它是一条聊天消息的格式。 | 无 | 主会话 | 每次升级上报 |
| `pull-request` | `.github/pull_request_template.md`。GitHub 会把它自动填进每个新 PR。 | 无。PR 用英文写。 | 开 PR 的角色 | 每个 PR |

`<名字>.md` 的中文镜像是同一文件夹下的 `<名字>.zh-CN.md`。`<短名>` 是用连字符连接的小写英文单词，例如 `F04-export-csv`。

## 4. 文档头

每份有中文镜像的文档都以 YAML front matter 开头。GitHub 会把它显示成表格，人能看到，F02 的检查也能解析。每个值都加引号，这样脚本会把它们都当作字符串读取。中文镜像和英文文档在同一个 PR 里创建，从 0.1 版开始就是如此。

英文文档：

```yaml
---
troy-doc: "requirements"
lang: "en"
version: "1.0"
updated: "2026-11-05"
status: "Approved by Troy on 2026-11-05"
mirror: "requirements.zh-CN.md"
---
```

中文镜像：

```yaml
---
troy-doc: "requirements"
lang: "zh-CN"
version: "1.0"
updated: "2026-11-05"
status: "Troy 已于 2026-11-05 批准"
mirror-of: "requirements.md"
---
```

| 字段 | 含义 |
| --- | --- |
| `troy-doc` | 文档编号，在项目内唯一。例如：`requirements`、`architecture`、`F04-design`、`F04-test-plan`、`v0.2-test-plan`、`ADR-0003`、`changelog`、`rules`。 |
| `lang` | `en` 或 `zh-CN`。 |
| `version` | `"主版本.次版本"`，加引号。每次内容修改，次版本加 1。Troy 批准一份文档时，升到下一个主版本，次版本归 0。 |
| `updated` | 最后一次内容修改的日期，格式 `YYYY-MM-DD`。 |
| `status` | 一行，用文档本身的语言写。 |
| `mirror` | 只用于英文文档，填中文镜像的文件名。 |
| `mirror-of` | 只用于中文镜像，填英文文档的文件名。 |

F02 依据这个文档头检查（R12）：

- PR 中被修改的英文文档，`version` 比 `main` 上的高。
- 它的中文镜像在同一个 PR 里也被修改，并且 `troy-doc` 和 `version` 与英文版相同。
- `mirror` 和 `mirror-of` 互相指向对方。

## 5. 模板内容

每个模板包含下面列出的章节标题、待填写标记和简短的填写说明。待填写标记是 `{{` 和 `}}` 之间的任何文字，例如 `{{feature-id}}`。填写说明是以 `template:` 开头的 HTML 注释。文档合入前两者都必须清除（提议 D2）。没有内容的章节、字段或表格写“无”。

### 5.1 `requirements`

1. 目标。
2. 用户。
3. 用户如何使用，包括 `docs/prototypes/` 中的原型列表。
4. 功能点。表格列：编号、功能、硬依赖、软依赖、版本、状态。
5. 依赖图（Mermaid）和拓扑顺序。
6. 版本计划。表格列：版本、功能、凭什么能单独使用。
7. 非功能需求，含性能指标表。列：编号、指标、如何测量、适用的功能。
8. 不做的范围。
9. 待定问题。列：编号、问题、提议、决定。
10. 修改记录。

### 5.2 `architecture`

1. 背景和约束，链接到非功能需求。
2. 技术栈。列：部分、选择、理由。
3. 模块。列：模块、负责什么、对外接口、可以依赖谁。
4. 依赖规则，用 Mermaid 图加列表表示。F03 的依赖检查工具（R07）按这一节配置。
5. 数据模型。
6. 错误处理。
7. 日志。
8. 在 R04 到 R07 之外补充的命名和编码规范。
9. 第三方依赖。列：名称、版本、许可证、理由、批准记录（ADR 编号）。
10. 测试配置：测试运行器、测试如何标注编号（R10）、覆盖率如何统计（R11）。
11. 决策记录：ADR 列表。
12. 修改记录。

### 5.3 `feature-design`（PR 1）

1. 功能：编号、名称、指向需求文档中对应行的链接、硬依赖和软依赖。
2. 接口。每个对外接口一个小节，包括：
   - 名称和所属模块。
   - 功能，一两句话。
   - 签名，用项目语言写在代码块里。
   - 参数。列：名称、类型、含义、约束。
   - 返回值。
   - 错误。列：错误、何时发生。
   - 副作用，没有就写"无"。
   - 需求文档中的性能指标编号，没有就写"无"。
   - 一个使用示例。
3. 对已有接口的修改，没有就写"无"。有修改时链接到对应的需求变更（5.4）。
4. 架构师审查。检查清单表（项目、结果、备注），包含需求文档 5.2 中的六项；以及轮次记录（轮次、问题、解决方式）。
5. 修改记录。

### 5.4 `test-plan`（PR 2）

1. 功能，以及指向其设计的链接。
2. 用例。列：编号、层级（单元、功能、集成或性能）、接口、测什么、准备和输入、预期结果。
3. 性能用例：指标编号、机器、余量、基线。
4. 不测的内容，每项写明原因。
5. 与接口设计师的对齐记录。列：轮次、问题、回答。
6. 修改记录。

### 5.5 `version-test-plan`

1. 版本及其包含的功能。
2. 端到端场景，取自需求文档。列：编号、场景、由谁运行、步骤、预期结果。“由谁运行”写 Claude，表示自动化的版本测试；或写 Troy，表示 Troy 在自己的设备上手工运行的场景（F08 D71）。
3. 性能和压力用例。列：编号、指标编号、负载、持续时间、机器、由谁运行。
4. 设备。列：设备、操作系统、由谁运行。
5. 验收记录。列：日期、结果、Troy 的备注。
6. 修改记录。

### 5.6 `adr`

1. 标题和编号。
2. 状态：提议中、已采纳，或已被另一条 ADR 取代。
3. 背景。
4. 决定。
5. 考虑过的方案。列：方案、优点、缺点。
6. 影响。
7. 相关的功能和规则。

### 5.7 `changelog`

每个版本一节，最新的在最前面，标题为 `vMAJOR.MINOR.PATCH (YYYY-MM-DD)`。每节分为新增、修改、修复三个列表。每一项都写明对应的功能编号或 bug 编号。

### 5.8 `rules`

一张表，列为：编号、规则、类型、由什么保证、适用范围、起始版本。类型是硬、软、审查或流程，定义与需求文档第 6 节相同。适用范围：来自 troy-pstack 的规则填 `troy-mode`，本项目自己的规则填 `project`。模板自带 R01 到 R19，内容从需求文档第 6 节复制。它的填写说明写明 F09 的规则变更流程怎样加 P 行：用下一个空闲编号；停用的行保留它的编号；每一行为某个文件豁免新检查的配置都带注释 `baseline: P01`（F09 设计第 8 节）。

### 5.9 `progress`

只用英文，因为这是主会话每个阶段都要重写的工作文件。字段：

- 当前版本及其功能。
- 当前功能和阶段（1 到 6，或 bug 的 A、B）。
- 未合并的 PR 及链接。
- 在等 Troy 处理的事项。
- 未解决的问题。
- 下一步。
- 最后更新时间。

### 5.10 `escalation`

升级上报消息的字段。troy-mode 用 Troy 在当前会话里使用的语言来写。

- 停在哪里：功能和阶段。
- 原因：触发了需求文档 5.7 中的哪一条。
- 事实：各方的说法，附链接。
- 方案：每个方案及其影响。
- 建议及理由。

### 5.11 `pull-request`（D1）

**标题。** `[<编号> <阶段>] <概要>`；不属于任何功能或 bug 的 PR 用 `[<类型>] <概要>`。F02 从标题读取 PR 类型。每种类型具体能改哪些路径，由 F02 的设计决定。

| 类型 | 标题示例 | 包含 |
| --- | --- | --- |
| 功能 PR 1 | `[F04 1/6 design] Export history as CSV` | 文档 |
| 功能 PR 2 | `[F04 2/6 test-plan] Export history as CSV` | 文档 |
| 功能 PR 3 | `[F04 3/6 mock] Export history as CSV` | 源码 |
| 功能 PR 4 | `[F04 4/6 tests] Export history as CSV` | 测试 |
| 功能 PR 5 | `[F04 5/6 impl] Export history as CSV` | 源码 |
| 功能 PR 6 | `[F04 6/6 accept] Export history as CSV` | 文档 |
| Bug PR A | `[B12 A/B test] Crash on empty history` | 测试 |
| Bug PR B | `[B12 B/B fix] Crash on empty history` | 源码 |
| 测试修正 | `[F04 test-fix] Wrong expected date format in F04-T03` | 测试 |
| 规则测试清理 | `[P01 test-fix] Apply P01 to tests` | 按项目规则修正的测试 |
| 版本测试 | `[v0.1 tests] End-to-end and stress tests` | `version-tests/` 里的测试 |
| 文档 | `[docs] Requirements change for offline mode` | 文档 |
| 规则变更 | `[rules] Add P01, no global state` | 规则表和检查配置 |
| 重构 | `[refactor] Split storage.py` | 源码 |

**描述的各个部分。**

1. Why：目标，一两句话。
2. What：改了什么，以及涉及的编号。
3. Checks：运行了哪些检查，结果如何。
4. Soft-limit reason：为什么超出 R03 或 R06 的限制，没有就写"None"。

## 6. 编号格式

| 对象 | 格式 | 例子 |
| --- | --- | --- |
| 功能 | `F` 加两位数字（超过 99 个后用三位） | `F04` |
| 测试用例 | 功能编号、`-T`、两位数字 | `F04-T07` |
| Bug | `B` 加 GitHub issue 编号（提议 D3） | `B12` |
| 端到端场景 | 版本、`-S`、两位数字 | `v0.2-S03` |
| 性能指标 | `PT` 加两位数字 | `PT02` |
| ADR | `ADR-` 加四位数字 | `ADR-0003` |
| troy-mode 规则 | `R` 加两位数字 | `R11` |
| 项目规则 | `P` 加两位数字 | `P01` |
| 待定问题 | `Q` 加数字 | `Q4` |

R10 要求每个测试都用上述格式标注功能编号或 bug 编号。各语言具体怎么标注，由 F03 决定。

## 7. 功能状态标签

项目需求文档里的功能表，只在 PR 6、版本验收和需求变更时修改，因为 R02 不允许在源码 PR 和测试 PR 里改文档。中间阶段记录在进度文件里。

| 标签 | 何时设置 |
| --- | --- |
| 未开始 | 需求文档批准时。 |
| 在 main 上通过测试 | PR 6 合入时。从此该功能的测试必须通过。 |
| 在 Troy 的设备上可用 | Troy 验收包含该功能的版本时。 |
| 需要返工 | 某项已批准的变更影响到它时。标签里写明是哪项变更。 |

## 8. 如何检查 F01

F01 没有代码，所以靠审查来检查：

- 第 3 节中标为"有"镜像的模板，以及 README，都有中文镜像，两者的章节标题和表格列相同，顺序也相同。
- 每个有镜像的模板都以第 4 节的文档头开头。
- 在仓库外建一个示例项目文件夹，用一个玩具功能填写 `requirements` 和 `feature-design` 两个模板，确认模板好用。这个示例不提交。

从 F02 开始，文档头和镜像由脚本自动检查。

## 9. 需要 Troy 决定的事项

Troy 已于 2026-11-05 批准全部六项提议。

| 编号 | 事项 | 提议 |
| --- | --- | --- |
| D1 | F02 需要知道每个 PR 属于哪个阶段（R02），还要能读到超出软限制的理由（R03）。需求文档没有说明这些信息从哪里来。 | 在 F01 中加入 PR 标题和描述模板。标题：`[F04 3/6 mock] <概要>` 或 `[B12 A/B test] <概要>`。描述分为：Why、What、Checks、Soft-limit reason。这扩大了 F01 的范围，需要你批准。 |
| D2 | 合入的文档里可能残留模板标记。 | F02 拒绝文档中含有 `{{` 标记或 `template:` 注释的 PR。这给 F02 增加了一项检查。 |
| D3 | 需求文档 5.3 用到了 bug 编号，但没有说明 bug 记录在哪里。 | 记在 GitHub issue 里，打上 `bug` 标签。bug 编号为 `B` 加 issue 编号。 |
| D4 | 进度文件用什么语言。 | 只用英文（第 5.9 节）。 |
| D5 | 文档头格式。 | 用 YAML front matter（第 4 节），不用 `docs/troy-mode/requirements.md` 那种可见表格。troy-pstack 自己的文档保持现有格式，因为 troy-pstack 不是 troy-mode 项目。 |
| D6 | troy-mode 文件在插件里放在哪里。 | 一个顶层文件夹 `troy-mode/`（第 2 节）。只有技能、代理和 hook 放在插件的标准文件夹里。 |

## 10. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-05 | 初稿。 |
| 1.0 | 2026-11-05 | Troy 批准，含 D1 到 D6。新增 PR 模板（第 5.11 节）和中文 README。 |
| 1.1 | 2026-11-05 | 根据试填 requirements 和 feature-design 模板的结果修正：front matter 的值全部加引号；中文镜像与英文文档同时创建；双花括号内的任何文字都是标记；没有内容的部分写“无”。 |
| 1.2 | 2026-11-08 | 来自 F08 设计第 9 节：`version-test-plan` 模板的场景表和性能与压力表都加了“由谁运行”一列（第 5.5 节），PR 类型加了 `[v0.1 tests]`（第 6 节）。 |
| 1.3 | 2026-11-08 | 来自 F09 设计第 8 节：`rules` 模板的填写说明讲 P 行、停用的行和 `baseline: P01` 注释（第 5.8 节）；PR 类型加上 `[P01 test-fix]`（第 5.11 节）。 |
