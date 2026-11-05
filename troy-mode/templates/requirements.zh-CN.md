---
troy-doc: "requirements"
lang: "zh-CN"
version: "0.1"
updated: "{{YYYY-MM-DD}}"
status: "草稿，等待 Troy 批准。"
mirror-of: "requirements.md"
---

# {{project-name}} 需求文档

<!-- template: 产品经理和 Troy 对话、把需求问清楚之后填写本文档。用简短的陈述句。Troy 批准时把 version 改为 "1.0"。没有内容的章节、字段或表格写“无”。文档合入前，删除所有 template 注释和所有 {{标记}}。 -->

## 1. 目标

<!-- template: 用两到四句话说明项目做什么、解决什么问题。 -->

{{goal}}

## 2. 用户

<!-- template: 谁在用、在哪些设备上用、多久用一次。 -->

{{users}}

## 3. 用户如何使用

<!-- template: 主要流程，一步一步写。每个重要的界面或命令都要有原型。原型是可点击的 HTML 线框图；命令行项目也可以改用 Markdown 文件，写一段终端交互的文字记录：输入的命令和显示的输出。 -->

{{interaction}}

### 3.1 原型

| 原型 | 功能 | 文件 |
| --- | --- | --- |
| {{prototype-name}} | {{feature-id}} | `docs/prototypes/{{feature-id}}-{{slug}}.{{html or md}}` |

## 4. 功能点

<!-- template: 功能点拆得尽量细。每个功能的实现必须能放进一个源码 PR（R03：最多改动 500 行、最多 5 个文件）。硬依赖指没有另一个功能就做不了；软依赖指可以先对着另一个功能的 mock 做。一个格子里有多个依赖时，用逗号分隔。状态只能是：未开始、在 main 上通过测试、在 Troy 的设备上可用、需要返工（写明是哪项变更）。 -->

| 编号 | 功能 | 硬依赖 | 软依赖 | 版本 | 状态 |
| --- | --- | --- | --- | --- | --- |
| {{feature-id}} | {{feature}} | {{feature-ids, or None}} | {{feature-ids, or None}} | {{version}} | 未开始 |

## 5. 依赖图和顺序

<!-- template: 硬依赖画实线箭头，软依赖画虚线箭头，两种都算数。依赖图不能有循环，排序必须满足每一个箭头。有循环说明拆分有问题：把共用部分拆成一个独立的功能，再重新画图。 -->

```mermaid
flowchart LR
  {{feature-id}} --> {{feature-id}}
  {{feature-id}} -.-> {{feature-id}}
```

拓扑顺序：{{F01, F02, ...}}

## 6. 版本计划

<!-- template: 把排序中相邻的功能分组成版本。每个版本自身都必须能用。版本命名为 vMAJOR.MINOR，例如 v0.1。 -->

| 版本 | 功能 | 凭什么能单独使用 |
| --- | --- | --- |
| {{version}} | {{feature-ids}} | {{reason}} |

## 7. 非功能需求

<!-- template: 速度、隐私、硬件限制、平台、语言、离线使用，以及其他不属于功能的要求。 -->

- {{requirement}}

### 7.1 性能指标

<!-- template: 只写能测量的指标。没有指标时，用"无"代替表格。 -->

| 编号 | 指标 | 如何测量 | 适用的功能 |
| --- | --- | --- | --- |
| PT{{nn}} | {{target}} | {{method}} | {{feature-ids}} |

## 8. 不做的范围

- {{item}}

## 9. 待定问题

| 编号 | 问题 | 提议 | 决定 |
| --- | --- | --- | --- |
| Q{{n}} | {{question}} | {{proposal}} | 待定 |

## 10. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | {{YYYY-MM-DD}} | 初稿。 |
