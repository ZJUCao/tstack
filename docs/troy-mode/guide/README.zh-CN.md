# troy-mode 使用指南

> 本文件是 [`README.md`](README.md) 的中文镜像，同步自英文版 0.1（2026-11-09）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.1 |
| 日期 | 2026-11-09 |
| 事实来源 | 英文版 [`README.md`](README.md)。本文件是中文镜像。 |

> **troy-mode 是 Troy 自己的作品。** 它由 Troy 设计，在这个分支里实现。它不属于 Lauren Tan 的 pstack，Lauren Tan 和 Cursor 没有审阅或认可过它。它原样复用 `how`、`why`、`interrogate`、`correct` 等 pstack 技能，也不改变 `poteto-mode` 的行为。它和 troy-pstack 的其余部分一样，采用 MIT 许可证。

troy-mode 的组成部分是：技能 `troy-mode` 和 `troy-init`、六个 `troy-*` 代理、`hooks/hooks.json` 里的 hook、`troy-mode/` 下的所有文件，以及 `docs/troy-mode/` 里的文档。troy-pstack 的其余部分是移植到 Claude Code 的 Lauren Tan 的 pstack：其他几乎每个技能、playbook、代理和指南页面，比如 `poteto-mode` 和 `docs/guide/` 里的指南，都是她的作品，按 MIT 许可证使用（[README：致谢和许可证](../../../README.md#credit-and-license)）。

## troy-mode 是什么

troy-mode 让一个软件项目经过一条固定的角色流水线，从需求一直走到发布的版本。每个角色在自己的上下文里工作，产出由另一个角色审查。规则由自动检查来执行，所以不依赖 Claude 记住它们（[需求文档第 1 节](../requirements.zh-CN.md#1-目标)）。

## 只需记住的一件事

输入 `/troy-pstack:troy-mode`，再用你自己的话说出你想做的事：

```text
/troy-pstack:troy-mode 下一个功能
```

troy-mode 判断请求属于哪个流程，运行各个角色，开 PR 并合并，只在需要你的地方停下来：你的批准、在你自己设备上的测试，或者升级上报。它用你的语言和你交流。它写进项目的所有内容都用英文，文档另附中文镜像。

## 目前跑通到哪一步

troy-mode 目前没有哪一部分超过“在示例项目上跑通”。本指南里每个流程的主路径都在临时仓库 `ZJUCao/troy-mode-trial` 上运行过一次，那是一个 Python 项目，示例都摘自这些运行。有些路径还没有运行过：有争议的测试和覆盖率缺口的旁支 PR、你接受的依赖、你在 GitHub 上合并来给出的批准、前几个功能之后的那个问题、架构师为项目写架构（试运行的架构是事先准备好的）、补丁版本、发布时失败的场景或推迟的 bug、修改规则或调整 R 规则、已经有代码的项目，以及任何 C/C++ 项目。试点（F11）是 troy-mode 第一次用在真实项目上，也是本指南的第一个真实读者。每一部分的状态见[需求文档第 7.2 节](../requirements.zh-CN.md#72-功能列表)。

## 页面

第一次读时，按这个顺序读。

| 页面 | 内容 |
| --- | --- |
| [1. 安装](01-install.zh-CN.md) | 你的电脑需要什么，安装和更新 troy-pstack，合并权限，以及每个角色的模型 |
| [2. 开始一个项目](02-start.zh-CN.md) | 初始化、需求文档、架构、语言步骤，以及已经有代码的项目 |
| [3. 做功能](03-features.zh-CN.md) | 功能循环：六个 PR、你的批准、审查和旁支 PR |
| [4. Bug 和变更](04-bugs-and-changes.zh-CN.md) | 修 bug、修改需求，以及不开 PR 的问题 |
| [5. 发布版本](05-release.zh-CN.md) | 版本测试方案、发布测试、你在自己设备上的测试，以及复盘 |
| [6. 规则](06-rules.zh-CN.md) | 新增、修改和废止规则，以及提议一条适用于所有项目的规则 |
| [7. 你在哪些地方参与](07-taking-part.zh-CN.md) | 等你处理的步骤、升级上报、troy-mode 自己做的事、状态标签，以及在新会话里接着做 |
| [8. 参考](08-reference.zh-CN.md) | 每种请求、PR 标题、评论标题、文件、配置项和规则，以及常见问题的解决办法 |
| [9. 修改 troy-mode](09-changing-troy-mode.zh-CN.md) | 在 troy-pstack 里修改 troy-mode 本身 |

## 细节在哪里

本指南讲你输入什么、看到什么。每一步内部怎样运作，写在需求文档和设计文档里，指南链接过去，不再重复：

- [需求文档](../requirements.zh-CN.md)：目标、流程、规则 R01 到 R22，以及功能列表。
- [设计文档](../design/)：每个功能一份，F01 到 F11。[F07](../design/F07-entry-skill.zh-CN.md) 是入口技能和功能循环，[F08](../design/F08-release.zh-CN.md) 是版本发布，[F09](../design/F09-rule-change.zh-CN.md) 是规则变更。
- 运行它的技能：[`skills/troy-mode/SKILL.md`](../../../skills/troy-mode/SKILL.md) 和 [`skills/troy-init/SKILL.md`](../../../skills/troy-init/SKILL.md)。
