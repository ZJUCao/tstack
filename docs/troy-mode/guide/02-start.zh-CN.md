# 2. 开始一个项目

> 本文件是 [`02-start.md`](02-start.md) 的中文镜像，同步自英文版 0.2（2026-11-16）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.2 |
| 日期 | 2026-11-16 |
| 事实来源 | 英文版 [`02-start.md`](02-start.md)。本文件是中文镜像。 |

一个项目经过四步成为 troy-mode 项目：初始化、需求文档、架构和语言步骤。需求文档和架构由你批准。其余的由 troy-mode 完成，并合并每一步的 PR（[需求文档第 5.1 节](../requirements.zh-CN.md#51-项目初始化每个项目一次)）。

## 2.1 请求

开始之前，先给项目加上合并权限（[第 1.4 节](01-install.zh-CN.md#14-合并权限)）。然后在项目的文件夹里打开一个新的 Claude Code 会话，新的或已有的文件夹都可以。在桌面应用里，选这个文件夹本身：试点整个版本都在那里运行，而在项目的 git worktree 里开的会话还没试过。这个项目的每个 troy-mode 请求都在这样的会话里输入，不要输在别的项目的会话里。然后输入你想做的东西：

```text
/tstack:troy-mode 开始一个项目：一个统计文本文件里单词数的命令行工具
```

在没有 `.troy-mode/` 的文件夹里，troy-mode 会回答问题，但什么都不改。对其他任何请求，它会问你一次，要不要把这个文件夹变成 troy-mode 项目。然后它按顺序运行这四步，在需要你的地方停下来。已经做过其中几步的项目，会从第一个缺少的步骤接着做。

只想运行初始化这一步时，输入 `/tstack:troy-init`。它把文件夹变成 troy-mode 项目，然后停下（[troy-init 技能](../../../skills/troy-init/SKILL.md)）。

## 2.2 初始化

troy-init 的引擎先规划初始化，不做任何改动。然后 troy-mode 在一条消息里问你所有没有明确默认值的事：

- **GitHub 仓库。** 文件夹没有 `origin` 远程仓库时，troy-mode 问你要不要创建私有仓库 `<your account>/<folder name>`，也就是你的账号加文件夹名。创建仓库是唯一会触及项目以外的步骤，所以它每次都会问。GitHub 会在 `main` 上做第一个 commit。
- **不是 troy-init 写的文件。** troy-init 从不覆盖不是它写的文件。对每个挡在路上的这类文件，troy-mode 都会问你要不要替换。选择保留，这一步就停下。
- **有 commit 但没有 `origin` 的文件夹。** troy-mode 停下来，问你怎样发布这些 commit，因为 R21 禁止推送 `main`。

初始化作为一个 PR 合入：`[rules] Set up troy-mode`，分支是 `troy-mode/init`。troy-mode 等它的检查通过后合并它。下面是 troy-init 试运行的初始化报告，说的是 PR [#1](https://github.com/ZJUCao/troy-mode-trial/pull/1)，经过缩短。那次试运行用英文进行，所以报告是英文的：

```text
Setup is done.
- Repository: I created the private repository ZJUCao/troy-mode-trial (GitHub made the
  first commit on main) and added it as origin over SSH. There were no conflicts.
- PR #1 "[rules] Set up troy-mode": one commit with 57 files.
  On GitHub, troy-mode checks passed and the PR was merged by rebase.
- Git hooks: they're on in this clone (core.hooksPath is .troy-mode/checks/git-hooks).
- Required check: branch protection isn't available on your plan (GitHub answered 403,
  "Upgrade to GitHub Pro"), so troy-mode checks stays optional.
Next: the requirements (Product Manager writes docs/requirements.md).
```

在 GitHub 免费套餐上，私有仓库没有分支保护。这时由 troy-mode 自己的合并步骤执行硬规则：检查失败的 PR 一律不合并（[需求文档第 6 节](../requirements.zh-CN.md#6-规则)）。

## 2.3 需求文档

产品经理就是主会话。它先问你它需要知道的问题，然后写 `docs/requirements.md` 和它的中文镜像。文档包括目标、带编号的功能、依赖图、拓扑排序、原型和版本计划（[需求文档第 5.1 节](../requirements.zh-CN.md#51-项目初始化每个项目一次)）。每个功能都有一个短名，比如 “Export history as CSV”，因为这个名字会成为这个功能每个 PR 标题的一部分，也会成为它的文件夹名。

它在 `troy-mode/requirements` 上开 `[docs] Add the requirements`。PR 描述的开头是给你的一页摘要，先中文后英文：程序会做什么、需要你决定的每一件事和推荐，以及风险（[第 7.1 节](07-taking-part.zh-CN.md#71-等你处理的步骤)）。troy-mode 发一条 `Waiting for Troy: approve this PR` 评论，在聊天里把同样的摘要发给你，然后停下。你可以用两种方式批准：

- **在聊天里。** 回复说你批准，比如“批准”。troy-mode 把你的批准记进文档的文件头和修改记录，然后合并 PR。
- **在 GitHub 上。** 自己合并 PR。troy-mode 随后用一个 `[docs] Record Troy's approval of <document>` PR 记下这次批准，并合并它。

要求修改时，说出要改什么。产品经理修改之后，PR 再次等你处理。详情见[第 7.1 节](07-taking-part.zh-CN.md#71-等你处理的步骤)。

## 2.4 架构

需求文档合入之后，架构师写 `docs/architecture.md` 和它的镜像：技术栈、模块划分及模块之间允许的依赖方向、数据模型、错误处理、日志、命名和编码规范。它在 `troy-mode/architecture` 上开 `[docs] Add the architecture`，描述开头是架构师写给你的摘要：你会注意到什么，比如速度、程序保存的文件、要安装的工具。你用同样的方式批准。

请你批准的那条消息还会多问一个问题：这个项目属于哪个系列，如果有的话。将来要在同一个平台上一起运行的项目组成一个系列，共用一个以系列命名的 mamba 环境（[需求文档第 8 节](../requirements.zh-CN.md#8-非功能需求)）。不属于任何系列时，环境以项目命名。

## 2.5 语言步骤

语言来自架构里的技术栈：Python 或 C/C++。troy-mode 在 `troy-mode/lang-python`（或 `troy-mode/lang-cpp`）上运行 troy-init 的语言步骤，并合并 `[rules] Add the Python pack`（或 `[rules] Add the C/C++ pack`）。这一步：

- 加入语言包的文件、它的工具配置和它的 CI 任务；
- 项目没有 `pyproject.toml` 或 `CMakeLists.txt` 时创建一个；已经有时，在 `pyproject.toml` 的末尾加上语言包的表，或者检查 `CMakeLists.txt` 有没有包含 `cmake/troy.cmake`；
- 你的电脑上缺少 mamba 环境时创建它，这要下载 Python 和各个工具，需要几分钟；然后编译锁文件并安装。

如果你的 `pyproject.toml` 里已经有语言包的某个表，或者你的 `CMakeLists.txt` 没有包含 `cmake/troy.cmake`，这一步会停下。troy-mode 会在改你的构建文件之前先问你。在第一个 mock PR 之前，语言包的 CI 任务找不到代码，会以 “No code yet” 通过。试运行的语言步骤 PR 是 [#3](https://github.com/ZJUCao/troy-mode-trial/pull/3)。

这一步之后，只有你的请求要求了，troy-mode 才会接着做第一个功能。否则它报告结果，然后停下。

## 2.6 已经有代码的项目

已经有代码和测试的项目，也可以接入 troy-mode。旧代码不必符合规则：只有新增和修改的代码要符合，旧代码在被改动时再整改（[需求文档 Q6](../requirements.zh-CN.md#10-待定问题)）。这条路径还没有运行过：试运行都是从空仓库开始的。Python 语言包要求项目根目录下有一个 `pyproject.toml` 和一个 `src/`，所以像 troy-voice 这样把每个包放在 `packages/<name>/` 里、各带自己的 `pyproject.toml` 的项目，目前还不适用（[F11 设计第 3.2 节](../design/F11-pilot.zh-CN.md#32-候选项目d93)）。

- **已有测试。** 语言步骤把符合语言包测试模式的测试文件列进 `.troy-mode/config.toml` 的 `[tests] legacy`，troy-mode 会告诉你是哪些。这样 R10 不会因为它们的名字没有用例编号而判它们失败。它们仍然必须通过。
- **已有文件。** 不是 troy-init 写的文件，它都保留，除非你同意替换。
- **已有的 `pyproject.toml`** 会在末尾加上语言包的表。如果它已经有其中某个表，这一步会停下，并说明要把什么移走。

## 2.7 troy-mode 加入的文件

| 路径 | 是什么 |
| --- | --- |
| `.troy-mode/config.toml` | 项目的配置：路径分类、上限、语言包、角色，以及由你批准的功能数。 |
| `.troy-mode/checks/` | troy-check 和它的 git hook。 |
| `.troy-mode/templates/` | 文档模板，两种语言都有。 |
| `.troy-mode/install.toml` | troy-init 记录它安装了什么。不要改它。 |
| `.troy-mode/progress.md` | 进度文件。只在本地，被 git 忽略。 |
| `docs/rules.md`、`docs/rules.zh-CN.md` | 项目的规则表。 |
| `.github/workflows/troy-mode.yml` | troy-check 的 CI 任务，语言步骤之后还有语言包的任务。 |
| `.github/pull_request_template.md` | PR 描述模板。 |
| `.gitignore` | 加入 `.troy-mode/progress.md`，语言步骤之后还加入语言包的几行。 |

项目的文档之后才会有：`docs/requirements.md`、`docs/architecture.md`、`docs/features/` 里每个功能一个文件夹，等等。[第 8.4 节](08-reference.zh-CN.md#84-项目里的文件)列出了它们，以及每个文件由谁修改。
