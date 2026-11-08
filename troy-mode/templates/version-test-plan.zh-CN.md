---
troy-doc: "{{version}}-test-plan"
lang: "zh-CN"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "草稿。"
mirror-of: "test-plan.md"
---

# {{version}} 版本测试方案

<!-- template: 测试经理在规划版本时就编写本文档，而不是到最后才写。没有内容的章节、字段或表格写“无”。文档合入前，删除所有 template 注释和所有 {{标记}}。 -->

## 1. 版本

- 版本：{{version}}
- 功能：{{feature-ids}}
- 需求：[docs/requirements.zh-CN.md](../../requirements.zh-CN.md#6-版本计划)

## 2. 端到端场景

<!-- template: 每个场景都取自需求文档中的用户流程。编号为 {{version}}-S01、{{version}}-S02，依此类推。“由谁运行”写明谁来运行这个场景：Claude，作为测试工程师写在 version-tests/ 里、只在发布时于 Troy 的电脑上运行的自动化版本测试；或 Troy，在只有 Troy 有的设备上（比如手机）手工运行。 -->

| 编号 | 场景 | 由谁运行 | 步骤 | 预期结果 |
| --- | --- | --- | --- | --- |
| {{version}}-S01 | {{scenario}} | {{Claude or Troy}} | {{steps}} | {{expected-result}} |

## 3. 性能和压力用例

<!-- template: 压力测试需要整个系统，所以写在这里，而不写在功能测试方案里。编号接着场景编号往下排。每个用例都取自需求文档中的一个性能指标。 -->

| 编号 | 指标 | 负载 | 持续时间 | 机器 | 由谁运行 |
| --- | --- | --- | --- | --- | --- |
| {{version}}-S{{nn}} | PT{{nn}} | {{load}} | {{duration}} | {{machine}} | {{Claude or Troy}} |

## 4. 设备

| 设备 | 操作系统 | 由谁运行 |
| --- | --- | --- |
| {{device}} | {{operating-system}} | {{Troy or Claude}} |

## 5. 验收记录

<!-- template: Troy 验收版本时填写或确认这一行。 -->

| 日期 | 结果 | Troy 的备注 |
| --- | --- | --- |
| {{YYYY-MM-DD}} | {{Accepted or Not accepted}} | {{notes}} |

## 6. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | 初稿。 |
