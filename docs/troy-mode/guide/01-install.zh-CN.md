# 1. 安装

> 本文件是 [`01-install.md`](01-install.md) 的中文镜像，同步自英文版 0.1（2026-11-09）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.1 |
| 日期 | 2026-11-09 |
| 事实来源 | 英文版 [`01-install.md`](01-install.md)。本文件是中文镜像。 |

troy-mode 包含在 troy-pstack 插件里。插件只需安装一次，每个项目给一项权限；只有默认的模型不合适时，才需要自己选。

## 1.1 你的电脑需要什么

| 需要什么 | 为什么 |
| --- | --- |
| Claude Code，桌面应用或命令行都可以 | troy-mode 是一个 Claude Code 技能。 |
| Git for Windows，带 Git Bash | troy-mode 通过 Bash 工具运行它的引擎、git 和 gh，而 Bash 工具在 Windows 上就是 Git Bash。 |
| `gh`，已登录你的 GitHub 账号 | troy-mode 用 `gh` 开 PR、在 PR 上评论、合并 PR。`gh auth status` 必须通过。 |
| Python 3.11 或更新版本 | troy-mode 的引擎和 hook 只用标准库。它们在 Windows 上运行 `python`，在其他系统上运行 `python3`；你设置了 `TROY_MODE_PYTHON` 时，运行它指定的程序。 |
| Miniforge，用于 Python 项目 | 语言步骤用 mamba 创建项目的环境。环境里有 Python 3.13 和 uv，uv 按项目的锁文件安装每个包。troy-mode 从不创建 `.venv`（[需求文档第 8 节](../requirements.zh-CN.md#8-非功能需求)）。 |

- **mamba。** troy-init 先在 PATH 里找 mamba，再看 `MAMBA_EXE`；troy-mode 也可以用 `--mamba` 把它的路径传给语言步骤（[troy-init 技能](../../../skills/troy-init/SKILL.md)）。troy-mode 在功能循环里运行的检查只在 PATH 里和 `MAMBA_EXE` 里找（[F07 设计第 6.1 节](../design/F07-entry-skill.zh-CN.md#61-任务简报)）。在你的电脑上，mamba 不在 Git Bash 的 PATH 里，所以要在 Claude Code 启动时所在的环境里，把 `MAMBA_EXE` 设为 `D:\miniforge3\Library\bin\mamba.exe`，把 `MAMBA_ROOT_PREFIX` 设为 Miniforge 文件夹 `D:\miniforge3`。
- **找不到 Python。** 在 troy-mode 项目里，hook 会停下并报 “troy-mode: no Python 3.11 or newer found; set TROY_MODE_PYTHON”。把 `TROY_MODE_PYTHON` 设为一个 Python 3.11 或更新版本即可。
- **C/C++ 项目**的 CMake、Ninja 和 clang 工具来自它的 mamba 环境。编译器来自环境之外：在你的电脑上，是 PATH 里的 MSYS2 GCC（[C/C++ 语言包的 README](../../../troy-mode/lang/cpp/README.zh-CN.md)）。功能循环目前还不能用于 C/C++：测试 PR 要在 `CMakeLists.txt` 里登记它的测试，而这个文件算作依赖文件，所以在那里 troy-mode 会撤销测试工程师的每次运行。第一个 C/C++ 项目之前，要先对 troy-mode 做一个小修复（[F11 设计第 3.3 节](../design/F11-pilot.zh-CN.md#33-cc-和-f07-修复)）。

## 1.2 安装 troy-pstack

troy-pstack 的文件夹既是插件，也是只含这一个插件的插件市场。在 Claude Code 里输入：

```text
/plugin marketplace add D:/Troy/Projects/troy-pstack
/plugin install troy-pstack@troy-pstack
```

Claude Code 会在插件的技能和代理名前面加上插件名。所以你输入的是 `/troy-pstack:troy-mode` 和 `/troy-pstack:troy-init`，各个角色是代理 `troy-pstack:troy-architect`、`troy-pstack:troy-interface-designer`、`troy-pstack:troy-test-manager`、`troy-pstack:troy-developer`、`troy-pstack:troy-test-engineer` 和 `troy-pstack:troy-code-reviewer`。

要确认 troy-mode 已经装上，开一个新会话：`/troy-pstack:troy-mode` 和 `/troy-pstack:troy-init` 会出现在 Claude Code 提供的命令里（[F11 设计第 2 节](../design/F11-pilot.zh-CN.md#2-前提条件)）。插件版本必须是 0.2.0 或更新：这是第一个为使用而写了 troy-mode 文档的版本。

## 1.3 插件出新版本后更新

Claude Code 安装插件时会复制一份，只有插件的版本升高时才更新这份副本（[F10 设计第 6 节](../design/F10-docs.zh-CN.md#6-插件版本d89)）。插件市场就是 troy-pstack 自己的文件夹，所以更新复制的是这个文件夹里现有的内容：先把它的检出更新到最新的 `main`。某个 troy-pstack PR 升了版本之后，运行下面的命令，然后重启 Claude Code：

```text
claude plugin update troy-pstack@troy-pstack
```

已经初始化过的项目保留着自己的一份 troy-check、模板和工作流。要把它带到新版本，在项目里输入 `/troy-pstack:troy-mode 升级 troy-mode`（[参考：较旧的副本](08-reference.zh-CN.md#86-常见问题)）。

## 1.4 合并权限

troy-mode 在自己的权限范围内合并自己的 PR（R18）。Claude Code 的自动模式仍可能把 `gh pr merge` 当作未经审查的合并而拒绝。这时 troy-mode 会停下来，告诉你要加哪项权限（[F07 设计第 8.6 节](../design/F07-entry-skill.zh-CN.md#86-合并r18f02-d14)）。为了避免这次停顿，在开始之前把下面这一行加到项目的 `.claude/settings.local.json` 里：

```json
{ "permissions": { "allow": ["Bash(gh pr merge *)"] } }
```

如果这个文件已经存在，就把 `"Bash(gh pr merge *)"` 加进它的 `allow` 列表。这个文件被 git 忽略，是你自己的，所以 troy-init 不写它。有了它，troy-mode 在那个项目里合并任何 PR 都不再弹出提示。troy-mode 自己的权限范围仍然只让它合并允许它合并的 PR：等你批准的 PR，它从不合并（[第 7.2 节](07-taking-part.zh-CN.md#72-troy-mode-自己做的事)）。

## 1.5 模型和 effort

每个角色作为一个子代理运行，有自己的模型。产品经理就是主会话。

| 角色 | 运行方式 | 模型 |
| --- | --- | --- |
| 产品经理 | 主会话 | 会话的模型 |
| 架构师 | `troy-pstack:troy-architect` | opus |
| 接口设计师 | `troy-pstack:troy-interface-designer` | opus |
| 测试经理 | `troy-pstack:troy-test-manager` | opus |
| 开发工程师 | `troy-pstack:troy-developer` | sonnet |
| 测试工程师 | `troy-pstack:troy-test-engineer` | sonnet |
| 代码审查员 | `troy-pstack:troy-code-reviewer` | opus |

每个角色都用会话的 effort 运行。要在某个项目里改一个角色，在项目的 `.troy-mode/config.toml` 里加一个 `[roles.<role>]` 表（[F07 设计第 3.2 节](../design/F07-entry-skill.zh-CN.md#32-模型和-effortf04-d32)）。比如让开发工程师用 opus、high effort 运行：

```toml
[roles.developer]
model = "opus"
effort = "high"
```

- `<role>` 是 `architect`、`interface-designer`、`test-manager`、`developer`、`test-engineer` 或 `code-reviewer`。
- `model` 是 Agent 工具接受的名字，比如 `opus` 或 `sonnet`。`effort` 是 `low`、`medium`、`high`、`xhigh` 或 `max`。不写某个键，就保留它的默认值。
- 这项改动用它自己的 `[rules]` PR 合入，因为 `.troy-mode/config.toml` 是配置文件（R02）。这个 PR 由你自己来开：troy-mode 只在 troy-init 的各个步骤里、在规则变更流程里，以及在记录由你批准的功能数时改配置（[第 3.4 节](03-features.zh-CN.md#34-前几个功能之后)），没有哪个流程会设置 `[roles]`。从 `origin/main` 拉一个分支，改这个文件，用 `[rules] Set the Developer's model and effort` 这样的标题提交，推送，然后开 PR。试运行里的 PR [#5](https://github.com/ZJUCao/troy-mode-trial/pull/5)，`[rules] Set the Code Reviewer's effort`，就是这样一个 PR。
- 检查通过后合并它。troy-mode 从它所工作的 commit 读取 `[roles]`，所以在合并之后新建的分支上启动的角色，会用新的值。
- 项目里的 troy-check 必须足够新，才能接受 `[roles]`。如果它比较旧，troy-check 会拒绝这个键，`status` 会说升级能把它更新（[参考：较旧的副本](08-reference.zh-CN.md#86-常见问题)）。
