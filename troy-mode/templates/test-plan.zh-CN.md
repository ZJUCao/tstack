---
troy-doc: "{{feature-id}}-test-plan"
lang: "zh-CN"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "草稿，正在和接口设计师对齐。"
mirror-of: "test-plan.md"
---

# {{feature-id}} {{feature-name}}：测试方案

<!-- template: 测试经理为 PR 2 编写本文档，只依据接口设计，绝不依据代码。每个用例测的都是调用方能观察到的行为。没有内容的章节、字段或表格写“无”。文档合入前，删除所有 template 注释和所有 {{标记}}。 -->

## 1. 功能

- 编号和名称：{{feature-id}} {{feature-name}}
- 设计：[design.zh-CN.md](design.zh-CN.md)

## 2. 用例

<!-- template: 层级为单元、功能、集成或性能。用例编号为 {{feature-id}}-T01、{{feature-id}}-T02，依此类推。测试工程师给每个测试标上功能编号（R10）。 -->

| 编号 | 层级 | 接口 | 测什么 | 准备和输入 | 预期结果 |
| --- | --- | --- | --- | --- | --- |
| {{feature-id}}-T01 | {{level}} | `{{interface-name}}` | {{behavior}} | {{setup-and-input}} | {{expected-result}} |

## 3. 性能用例

<!-- template: 只用于带性能指标的接口（R14）。在实现之后、在固定的机器上运行。没有时用"无"代替表格。 -->

| 编号 | 指标 | 机器 | 余量 | 基线 |
| --- | --- | --- | --- | --- |
| {{feature-id}}-T{{nn}} | PT{{nn}} | {{machine}} | {{margin}} | {{baseline, or First run}} |

## 4. 不测的内容

<!-- template: 如果设计中的内容全部都测，用"无"代替表格。 -->

| 内容 | 原因 |
| --- | --- |
| {{item}} | {{reason}} |

## 5. 与接口设计师的对齐记录

<!-- template: 每个问题一行。3 轮仍未达成一致时，troy-mode 向 Troy 升级上报（R17）。 -->

| 轮次 | 问题 | 回答 |
| --- | --- | --- |
| 1 | {{question}} | {{answer}} |

## 6. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | 初稿。 |
