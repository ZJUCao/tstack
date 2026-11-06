---
troy-doc: "architecture"
lang: "zh-CN"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "草稿，等待 Troy 批准。"
mirror-of: "architecture.md"
---

# {{project-name}} 总体架构

<!-- template: Troy 批准需求后，由架构师编写本文档。它只管跨功能的问题；每个功能的接口写在该功能的设计文档里，不写在这里。Troy 批准时把 version 改为 "1.0"。没有内容的章节、字段或表格写“无”。文档合入前，删除所有 template 注释和所有 {{标记}}。 -->

## 1. 背景和约束

<!-- template: 影响设计的非功能需求。每一条都链接到 docs/requirements.md 中对应的位置。 -->

- {{constraint}}

## 2. 技术栈

| 部分 | 选择 | 理由 |
| --- | --- | --- |
| {{part}} | {{choice}} | {{reason}} |

## 3. 模块

<!-- template: 每个模块一行。troy-check 会读取这张表来检查 R07，所以路径要写准确。"负责什么"先用反引号写出模块的文件路径规则，再写模块负责的内容。"对外接口"用反引号写出其他模块唯一可以引用的文件的路径规则。"可以依赖谁"列出它唯一允许引用的模块，或者写"无"。 -->

| 模块 | 负责什么 | 对外接口 | 可以依赖谁 |
| --- | --- | --- | --- |
| {{module}} | {{path patterns, then responsibility}} | {{interface path patterns}} | {{modules, or None}} |

## 4. 依赖规则

<!-- template: 依赖图不能有循环。F03 的依赖检查工具（R07）按本节配置，所以模块名必须和第 3 节完全一致。 -->

```mermaid
flowchart TD
  {{module-a}} --> {{module-b}}
```

- {{rule}}

## 5. 数据模型

<!-- template: 各个实体、它们的字段和类型，以及彼此的关系。 -->

{{data-model}}

## 6. 错误处理

<!-- template: 错误怎么表示、在哪里捕获、用户会看到什么。 -->

{{error-handling}}

## 7. 日志

<!-- template: 记录什么、用什么级别、日志写到哪里、什么绝不记录。 -->

{{logging}}

## 8. 命名和编码规范

<!-- template: 只写在 docs/rules.md 的 R04 到 R07 之外补充的规范。能用工具检查的规范，同时作为项目规则（P01、P02 等）写进 docs/rules.md。 -->

- {{rule}}

## 9. 第三方依赖

<!-- template: 每个依赖都需要架构师批准（R16），并记录在一条 ADR 里。 -->

| 名称 | 版本 | 许可证 | 理由 | 批准记录 |
| --- | --- | --- | --- | --- |
| {{name}} | {{version}} | {{license}} | {{reason}} | ADR-{{NNNN}} |

## 10. 测试配置

- 测试运行器：{{runner}}
- 测试如何标注功能编号和 bug 编号（R10）：{{tagging}}
- 改动代码的覆盖率如何统计（R11）：{{coverage-tool}}

## 11. 决策记录

| ADR | 标题 | 状态 |
| --- | --- | --- |
| ADR-{{NNNN}} | {{title}} | {{status}} |

## 12. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | 初稿。 |
