---
troy-doc: "rules"
lang: "zh-CN"
version: "1.0"
updated: "{{init-date}}"
status: "由 troy-init 根据 troy-mode 初始化。"
mirror-of: "rules.md"
---

# {{project-name}} 规则

<!-- template: troy-init 填写 {{project-name}} 和 {{init-date}}。R01 到 R23 来自 troy-mode。本项目自己的规则通过规则变更流程（troy-mode 需求文档 5.8）加在它们后面，编号为 P01、P02，依此类推。没有内容的章节、字段或表格写“无”。文档合入前，删除所有 template 注释和所有 {{标记}}。 -->

## 1. 规则类型

- **硬规则**：不满足就不能合入。
- **软规则**：PR 描述里写明原因就可以合入。
- **审查**：由某个角色检查。
- **流程**：由 troy-mode 自己遵守。

## 2. 规则

| 编号 | 规则 | 类型 | 由什么保证 | 适用范围 | 起始日期 |
| --- | --- | --- | --- | --- | --- |
| R01 | 每个 PR 只有一个 commit，且它的标题行等于 PR 标题。审查后的修改通过修改那个 commit 完成，或者用 squash 合并。 | 硬 | CI | troy-mode | {{init-date}} |
| R02 | 每个 PR 只包含一个阶段的产出：文档、源码或测试之一。 | 硬 | CI | troy-mode | {{init-date}} |
| R03 | 源码 PR 最多改动 500 行（新增加删除，不算锁文件和自动生成的文件），最多涉及 5 个文件。测试 PR 不限。只拆分文件的 PR 可以超限，但要写明。 | 软 | CI | troy-mode | {{init-date}} |
| R04 | 函数体最多 50 行，不算注释、文档注释和空行。复杂的对外接口调用多个功能单一的内部函数。 | 硬 | Lint | troy-mode | {{init-date}} |
| R05 | 文档注释使用 Google 风格。代码注释只用英文。 | 硬 | Lint | troy-mode | {{init-date}} |
| R06 | 源码文件最多 500 行（总行数，含注释）。超过就拆分文件。 | 软 | Lint | troy-mode | {{init-date}} |
| R07 | 模块之间只能按架构允许的方向依赖，只通过对外接口调用，不能有循环。 | 硬 | 依赖检查工具 | troy-mode | {{init-date}} |
| R08 | 开发工程师永远不改测试文件。 | 硬 | Hook 和 CI | troy-mode | {{init-date}} |
| R09 | 测试 PR 里的每个新测试对着 mock 都失败。 | 硬 | CI | troy-mode | {{init-date}} |
| R10 | 每个测试都标上它的用例编号或 bug 编号：测试自己的名字以编号开头，例如 `test_f04_t07_writes_header`。尚未验收的功能、尚未修复的 bug，它们的测试失败记为预期失败。其余测试必须通过。 | 硬 | 测试运行器配置和 CI | troy-mode | {{init-date}} |
| R11 | 实现 PR 中，改动代码的行覆盖率不低于 90%，分支覆盖率不低于 80%。95% 是目标，不是门槛。排除的代码行必须写明原因，并经测试经理批准。 | 硬 | CI | troy-mode | {{init-date}} |
| R12 | 英文文档是事实来源。改英文文档的 PR 必须同时更新中文镜像。中文镜像的文档头注明它对应的英文版本。 | 硬 | CI | troy-mode | {{init-date}} |
| R13 | 状态标签要如实说明功能做到哪一步，比如"在 main 上通过测试"和"在 Troy 的设备上可用"要区分开。 | 审查 | 产品经理 | troy-mode | {{init-date}} |
| R14 | 只有带性能指标的接口才写性能测试。在固定的机器上运行，留出余量，和上一次的基线比较。 | 审查 | 测试经理 | troy-mode | {{init-date}} |
| R15 | 每个修过的 bug 都保留它的重现测试。 | 审查 | 测试经理 | troy-mode | {{init-date}} |
| R16 | 引入新的第三方依赖需要架构师批准。 | 审查 | 架构师。CI 会标出所有依赖文件的改动。 | troy-mode | {{init-date}} |
| R17 | 审查循环最多 3 轮，之后升级上报。 | 流程 | troy-mode | troy-mode | {{init-date}} |
| R18 | 前 3 个功能的 PR 1 和 PR 2 由 Troy 批准，方式是在聊天里回复或合并它们。在聊天里批准之后，由 Claude 合并。其他 PR 在检查和审查都通过后由 Claude 合并。什么时候全部交给 Claude 合并，由 Troy 决定。 | 流程 | troy-mode | troy-mode | {{init-date}} |
| R19 | commit 使用 Troy 全局 CLAUDE.md 里规定的邮箱。commit 信息、PR 标题和描述、PR 评论和评审、issue 以及发布说明不带任何 Claude 署名，也完全不提 Claude 或 Anthropic，除非 `.troy-mode/config.toml` 把署名检查模式设为 `trailers`。发到 GitHub 的文字在发出前检查，因为 GitHub 会保留每次编辑的历史。 | 硬 | Hook 和 CI。评论、评审、issue 和发布说明只由 hook 在发出前检查。 | troy-mode | {{init-date}} |
| R20 | 合并的文档和 PR 描述里没有模板标记或填写说明。 | 硬 | CI | troy-mode | {{init-date}} |
| R21 | 每个改动都通过从单独分支发起的 PR 进入 `main`。永远不要在 `main` 上提交、推送 `main`，或从 `main` 开 PR。 | 硬 | Hook 和 CI | troy-mode | {{init-date}} |
| R22 | 每个接口设计、测试计划、需求和架构 PR 的描述都以给 Troy 的摘要开头，先中文后英文：对 Troy 有什么变化、需要 Troy 决定的每一件事及推荐，以及风险。每种语言最多 2,000 个字符（`.troy-mode/config.toml` 里的 `[summary] max_chars`），不含内部编号。 | 硬 | CI | troy-mode | {{init-date}} |
| R23 | 在 troy-mode 运行的命令里，Python 永远不从标准输入读取程序：不用 `python -`，不用 `python -i`，也不在没有脚本、`-c` 或 `-m` 的情况下运行 `python`，无论标准输入来自 heredoc、管道、`/dev/null`，还是什么都没有。这样的运行可能卡在 Python 的交互提示符上。把脚本写到 scratchpad 里的一个文件中，再用项目的 Python 运行这个文件。 | 硬 | Hook（命令启动前就拒绝） | troy-mode | {{init-date}} |

<!-- template: troy-mode 的规则变更流程把本项目自己的规则加在这里，放在 R 行之后，每条一行，用下一个空闲编号（P01、P02，依此类推），适用范围填 "project"。示例行：| P01 | {{rule}} | {{type}} | {{enforced-by}} | project | {{YYYY-MM-DD}} |。停用的规则保留它的行：规则一栏以“已于 <日期> 停用。”开头，由什么保证一栏写“无”，它的编号不再使用。已有代码违反新检查时，工具的配置为每个违规文件写一行豁免，带注释 baseline: P01，直到清理 PR 修好该文件并删掉这一行。 -->

## 3. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 1.0 | {{init-date}} | 初始化，包含来自 troy-mode 的 R01 到 R23。 |
