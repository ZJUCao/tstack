# 4. Bug 和变更

> 本文件是 [`04-bugs-and-changes.md`](04-bugs-and-changes.md) 的中文镜像，同步自英文版 0.1（2026-11-09）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.1 |
| 日期 | 2026-11-09 |
| 事实来源 | 英文版 [`04-bugs-and-changes.md`](04-bugs-and-changes.md)。本文件是中文镜像。 |

bug 先得到一个重现它的测试，然后才修复。需求变更先改需求文档，再回到功能循环。问题或试验根本不开 PR。

## 4.1 修 bug

描述这个 bug，或者给出它的 GitHub issue：

```text
/troy-pstack:troy-mode bug：count_words("") 抛出 PermissionError，而不是 FileNotFoundError
/troy-pstack:troy-mode 修复 #12
```

如果你给的是描述，troy-mode 会开一个带 `bug` 标签的 GitHub issue。issue 的编号就是 bug 的编号：issue 12 是 `B12`。然后（[需求文档第 5.3 节](../requirements.zh-CN.md#53-修-bug)）：

1. **分类。** 测试经理阅读报告。如果这个“bug”其实是需求理解错了，troy-mode 会告诉你，并给出建议，它就变成一项需求变更（第 4.2 节）。
2. **PR A**，`[B12 A/B test] <summary>`，分支 `troy-mode/b12-test`。测试工程师加一个重现这个 bug 的测试。测试名以 `test_b12_` 开头，在当前代码上失败。由测试经理和代码审查员审查。
3. **PR B**，`[B12 B/B fix] <summary>`，分支 `troy-mode/b12-fix`。开发工程师修复 bug，新测试通过。PR 描述里写着 `Fixes #12`，所以 PR 合入时 GitHub 会关闭这个 issue。由代码审查员审查。

两个 PR 都由 troy-mode 合并。这个测试作为回归测试保留（R15）。修 bug 时遇到有争议的测试或新依赖，处理方式和功能里一样（[第 3.6 节](03-features.zh-CN.md#36-旁支-pr)）。

在试运行里，bug B13 是 issue [#13](https://github.com/ZJUCao/troy-mode-trial/issues/13)。PR A [#14](https://github.com/ZJUCao/troy-mode-trial/pull/14) 收到了下面这条审查，经过缩短。PR 评论是英文的：

```text
Test Manager review, round 1: approved

The B13 reproduction test meets every point of the triage: its name starts with test_b13_;
it expects FileNotFoundError from count_words("") on Windows and Linux alike; it has no
skip or xfail marker, so it stays after the fix (R15).
It fails on the current code for the reported reason (PermissionError: [Errno 13]
Permission denied: '.'); R09 passes.
```

PR B 是 [#15](https://github.com/ZJUCao/troy-mode-trial/pull/15)。

## 4.2 修改需求

说出要改什么：

```text
/troy-pstack:troy-mode 变更：一个单词至少要有一个字母或数字
```

1. **需求文档。** 产品经理在 `troy-mode/change-<slug>` 上更新 `docs/requirements.md` 和它的镜像，开 `[docs] Change the requirements: <summary>`。你像批准需求文档时那样批准它（[第 2.3 节](02-start.zh-CN.md#23-需求文档)）。在你批准之前，其他什么都不改。
2. **受影响的功能。** 对每一个受影响的功能，架构师决定哪些接口、测试和架构部分要改。架构的改动会向你升级上报，以它的 ADR 作为建议。
3. **还没验收的功能**，状态改为 `Needs rework (<the change>)`（中文镜像里是“需要返工”），回到架构师指出的最早的阶段。如果这个功能开着的 PR 处在那个阶段或更后的阶段，troy-mode 不合并就关闭它，然后把这个阶段重新跑一遍。
4. **已验收的功能**保持它的状态。这项变更成为一个新功能，用下一个空闲的编号，硬依赖旧功能，状态是 `Not started`（中文镜像里是“未开始”）（[F07 设计 D65](../design/F07-entry-skill.zh-CN.md#16-需要-troy-决定的事项)）。它像其他功能一样走功能循环。

在试运行里，`[docs] Change the requirements: a word needs a letter or digit`（[#16](https://github.com/ZJUCao/troy-mode-trial/pull/16)）为已验收的 F01 加了 F03 “Words need a letter or digit”。之后是 F03 的设计（[#17](https://github.com/ZJUCao/troy-mode-trial/pull/17)）和测试方案（[#18](https://github.com/ZJUCao/troy-mode-trial/pull/18)），它的 mock 被跳过了。

### 旧测试会怎样

已验收的功能一改，它的一些测试就会变成错的。新功能的 PR 会处理它们：

- **设计（PR 1）。** 它列出要改的接口。如果它没有新增接口，就跳过 PR 3，也就是 mock，循环从 PR 2 直接到 PR 4。
- **测试方案（PR 2）。** 测试经理指出这项变更淘汰了哪些旧用例，在同一个 PR 里把它们移到旧功能测试方案的 “Not tested” 一节（中文镜像里是“不测的内容”），写明原因，中英文都改。
- **测试（PR 4）。** 测试工程师删掉被淘汰的测试，加入新的用例。新测试对着当前代码失败（R09）。
- 其他所有测试继续作为回归测试运行。

## 4.3 问题和试验

问题和调查不开 PR：

```text
/troy-pstack:troy-mode 为什么 count_words 一次读入整个文件？
/troy-pstack:troy-mode 发布测试怎样找到版本测试？
/troy-pstack:troy-mode 试一个流式读取的 count_words
```

troy-mode 直接在对话里回答，合适时按 pstack 的 `how` 或 `why` 技能来做，不启动任何角色。试验在从 `origin/main` 拉出的临时分支 `troy-mode/try-<slug>` 上进行，或者在一个临时文件夹里。它从不推送，也从不成为 PR。值得保留的代码要走需求变更和功能循环（[需求文档第 5.9 节](../requirements.zh-CN.md#59-流水线之外的工作)）。
