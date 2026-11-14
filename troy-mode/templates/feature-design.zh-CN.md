---
troy-doc: "{{feature-id}}-design"
lang: "zh-CN"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "草稿，架构师审查中。"
mirror-of: "design.md"
---

# {{feature-id}} {{feature-name}}：接口设计

<!-- template: 接口设计师为 PR 1 编写本文档。只设计对外接口，也就是其他代码会调用的部分。内部函数由开发工程师自己决定。没有内容的章节、字段或表格写“无”。文档合入前，删除所有 template 注释和所有 {{标记}}。 -->

## 1. 功能

- 编号和名称：{{feature-id}} {{feature-name}}
- 需求：[docs/requirements.zh-CN.md](../../requirements.zh-CN.md#4-功能点)
- 硬依赖：{{feature-ids, or None}}
- 软依赖：{{feature-ids, or None}}

## 2. 接口

<!-- template: 每个对外接口一个小节。每个接口复制一份完整的小节，编号为 2.1、2.2，依此类推。接口就是其他模块或用户调用的东西：函数、类、命令行命令、HTTP 接口或界面。命令行命令的签名是它的用法行，参数是它的参数和选项，返回值是它的退出码和输出。只设计最外层的调用面，背后的函数由开发工程师决定。 -->

### 2.1 `{{interface-name}}`

- 模块：{{module from docs/architecture.md section 3}}
- 功能：{{one or two sentences}}

签名：

```{{language}}
{{signature}}
```

参数：

| 名称 | 类型 | 含义 | 约束 |
| --- | --- | --- | --- |
| {{name}} | {{type}} | {{meaning}} | {{constraints}} |

- 返回值：{{type and meaning, or None}}

错误：

| 错误 | 何时发生 |
| --- | --- |
| {{error}} | {{condition}} |

- 副作用：{{side-effects, or None}}
- 性能指标：{{PT ID from the requirements, or None}}

示例：

```{{language}}
{{usage-example}}
```

## 3. 对已有接口的修改

<!-- template: 没有就写"无"；有修改时逐条列出，并链接到在需求文档中批准该修改、已经合并的 [docs] PR（troy-mode 需求变更流程）。 -->

{{changes, or None}}

## 4. 架构师审查

| 项目 | 结果 | 备注 |
| --- | --- | --- |
| 符合模块划分和数据模型 | {{Pass or Fail}} | {{note}} |
| 遵守错误处理和命名约定 | {{Pass or Fail}} | {{note}} |
| 不和已有接口重复 | {{Pass or Fail}} | {{note}} |
| 只依赖排序在前面的功能 | {{Pass or Fail}} | {{note}} |
| 不在模块之间增加隐性耦合 | {{Pass or Fail}} | {{note}} |
| 修改已实现的接口时走了变更流程 | {{Pass or Fail}} | {{note}} |
| 给 Troy 的摘要和设计说的一致，并列出了需要 Troy 决定的每一件事 | {{Pass or Fail}} | {{note}} |

<!-- template: 每轮审查一行。3 轮仍未达成一致时，troy-mode 向 Troy 升级上报（R17）。 -->

| 轮次 | 问题 | 解决方式 |
| --- | --- | --- |
| 1 | {{issue}} | {{resolution}} |

## 5. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | 初稿。 |
