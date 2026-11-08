# troy-mode 模板

> 本文件是 [`README.md`](README.md) 的中文镜像，同步自英文版 1.1（2026-11-05）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 1.1 |
| 日期 | 2026-11-05 |
| 事实来源 | 英文版 [`README.md`](README.md)。本文件是中文镜像。 |

`troy-init` 把这些模板复制到项目里，由 troy-mode 的各个角色填写。本 README 是各角色工作时查阅的参考。[F01 设计](../../docs/troy-mode/design/F01-templates.zh-CN.md)记录了每个选择的理由。

## 1. 模板

| 模板 | 在项目里的路径 | 中文镜像 | 由谁填写 | 在哪些环节修改 |
| --- | --- | --- | --- | --- |
| [`requirements`](requirements.zh-CN.md) | `docs/requirements.md` | 有 | 产品经理 | 项目初始化、需求变更、PR 6、版本验收 |
| [`architecture`](architecture.zh-CN.md) | `docs/architecture.md` | 有 | 架构师 | 项目初始化、需求变更 |
| [`feature-design`](feature-design.zh-CN.md) | `docs/features/<功能编号>-<短名>/design.md` | 有 | 接口设计师 | PR 1 |
| [`test-plan`](test-plan.zh-CN.md) | `docs/features/<功能编号>-<短名>/test-plan.md` | 有 | 测试经理 | PR 2、测试修正 |
| [`version-test-plan`](version-test-plan.zh-CN.md) | `docs/versions/<版本>/test-plan.md` | 有 | 测试经理 | 版本规划、版本验收 |
| [`adr`](adr.zh-CN.md) | `docs/adr/ADR-<四位编号>-<短名>.md` | 有 | 架构师 | 每个架构决策 |
| [`changelog`](changelog.zh-CN.md) | `CHANGELOG.md` | 有 | 产品经理 | 版本发布 |
| [`rules`](rules.zh-CN.md) | `docs/rules.md` | 有 | troy-mode | 项目初始化、规则变更流程 |
| [`progress`](progress.md) | `.troy-mode/progress.md` | 无 | 主会话 | 每个阶段。只在本地，被 git 忽略。 |
| [`escalation`](escalation.md) | 无。它是一条聊天消息的格式。 | 无 | 主会话 | 每次升级上报 |
| [`pull-request`](pull-request.md) | `.github/pull_request_template.md` | 无。PR 用英文写。 | 开 PR 的角色 | 每个 PR |

`<名字>.md` 的中文镜像是同一文件夹下的 `<名字>.zh-CN.md`。`<短名>` 是用连字符连接的小写英文单词，例如 `F04-export-csv`。

## 2. 标记和填写说明

- 待填写标记是 `{{` 和 `}}` 之间的任何文字，例如 `{{feature-id}}` 或 `{{feature-ids, or None}}`。
- 填写说明是以 `template:` 开头的 HTML 注释。
- 没有内容的章节、字段或表格写“无”（英文文档写 None）。
- 文档合入前两者都必须清除。文档里仍残留任何一种时，F02 会拒绝这个 PR。

## 3. 文档头

每份有中文镜像的文档都以 YAML front matter 开头。每个值都加引号，这样脚本会把它们都当作字符串读取。中文镜像和英文文档在同一个 PR 里创建，从 0.1 版开始就是如此。

| 字段 | 含义 |
| --- | --- |
| `troy-doc` | 文档编号，在项目内唯一，例如 `requirements` 或 `F04-design`。 |
| `lang` | `en` 或 `zh-CN`。 |
| `version` | `"主版本.次版本"`，加引号。每次内容修改，次版本加 1。Troy 批准一份文档时，升到下一个主版本，次版本归 0。 |
| `updated` | 最后一次内容修改的日期，格式 `YYYY-MM-DD`。 |
| `status` | 一行，用文档本身的语言写。 |
| `mirror` | 只用于英文文档，填中文镜像的文件名。 |
| `mirror-of` | 只用于中文镜像，填英文文档的文件名。 |

修改英文文档的 PR 要提高它的 `version`，并把中文镜像改到相同的 `version`（R12）。

## 4. 编号格式

| 对象 | 格式 | 例子 |
| --- | --- | --- |
| 功能 | `F` 加两位数字（超过 99 个后用三位） | `F04` |
| 测试用例 | 功能编号、`-T`、两位数字 | `F04-T07` |
| Bug | `B` 加 GitHub issue 编号。bug 记在打了 `bug` 标签的 GitHub issue 里。 | `B12` |
| 端到端场景 | 版本、`-S`、两位数字 | `v0.2-S03` |
| 性能指标 | `PT` 加两位数字 | `PT02` |
| ADR | `ADR-` 加四位数字 | `ADR-0003` |
| troy-mode 规则 | `R` 加两位数字 | `R11` |
| 项目规则 | `P` 加两位数字 | `P01` |
| 待定问题 | `Q` 加数字 | `Q4` |

## 5. 功能状态标签

`docs/requirements.md` 里的功能表只在 PR 6、版本验收和需求变更时修改。中间阶段记录在进度文件里。

| 标签 | 何时设置 |
| --- | --- |
| 未开始 | 需求文档批准时。 |
| 在 main 上通过测试 | PR 6 合入时。从此该功能的测试必须通过。 |
| 在 Troy 的设备上可用 | Troy 验收包含该功能的版本时。 |
| 需要返工 | 某项已批准的变更影响到它时。标签里写明是哪项变更。 |

## 6. PR 类型

PR 标题为 `[<编号> <阶段>] <概要>`；不属于任何功能或 bug 的 PR 用 `[<类型>] <概要>`。

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
| 重构 | `[refactor] Split storage.py`，或规则清理：`[refactor] Apply P01 to storage` | 源码 |

描述分四部分：Why、What、Checks、Soft-limit reason。
