# 9. 修改 troy-mode

> 本文件是 [`09-changing-troy-mode.md`](09-changing-troy-mode.md) 的中文镜像，同步自英文版 0.2（2026-11-16）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.2 |
| 日期 | 2026-11-16 |
| 事实来源 | 英文版 [`09-changing-troy-mode.md`](09-changing-troy-mode.md)。本文件是中文镜像。 |

本页讲的是在 troy-pstack 里改 troy-mode 本身的工作：由你来做，或者由你在那里启动的 Claude Code 会话来做。troy-mode 自己的流水线不在这里运行。troy-pstack 有它自己的流程，写在本页，这样每个会话都能找到（[F10 设计 D92](../design/F10-docs.zh-CN.md#11-需要-troy-决定的事项)）。

## 9.1 各部分在哪里

| 内容 | 位置 |
| --- | --- |
| 需求文档 | `docs/troy-mode/requirements.md` 和它的镜像 [`requirements.zh-CN.md`](../requirements.zh-CN.md) |
| 每个功能一份设计 | [`docs/troy-mode/design/`](../design/)，从 `F01-templates.md` 到 `F11-pilot.md`，每份都有镜像 |
| 本指南 | `docs/troy-mode/guide/` |
| 技能 | `skills/troy-mode/SKILL.md`、`skills/troy-init/SKILL.md` |
| 角色 | `agents/troy-*.md`，以及 `troy-mode/roles/` 里产品经理的说明 |
| hook | `hooks/hooks.json` 和 `troy-mode/hooks/` |
| 引擎 | `troy-mode/checks/`（troy-check）、`troy-mode/init/`（troy-init）、`troy-mode/flow/`（入口技能的引擎） |
| 项目得到的内容 | `troy-mode/templates/`、`troy-mode/lang/`（语言包）、`troy-mode/checks/` |
| troy-pstack 自己的工具 | `troy-mode/dev/`：`check_pairs.py`、`check_links.py`、`build_sample.py`，以及示例项目的测试 |

所有新增的技能和代理名都以 `troy-` 开头，troy-mode 不改任何上游文件，它只改动三个共用文件：`README.md`、`.claude-plugin/plugin.json` 和 `.claude-plugin/marketplace.json`（[需求文档第 8 节](../requirements.zh-CN.md#8-非功能需求)）。

## 9.2 开发流程

[需求文档第 7.2 节](../requirements.zh-CN.md#72-功能列表)里的功能一次做一个：

1. **设计。** 一份设计文档及其镜像，每个待定问题都列为一项决定，并给出推荐答案，这样你可以回复“全按推荐”。你批准设计、它的 PR 合入之前，不写任何代码。修改需求文档也要你同意。
2. **先写测试。** 由另一个代理只按设计写测试，这时代码还不存在。开发会话审查这些测试，找出不可能失败的断言。
3. **写代码**，直到每个测试套件都通过。
4. **埋 bug。** 在一份临时副本里一次埋一个，每个都必须让某个测试失败。没被发现的 bug 要补一个测试。数量写进 PR 描述。
5. **一个 PR，一个 commit。** 修改通过修订（amend）这个 commit 完成。
6. **试运行**，设计里有试运行时，在临时仓库 `ZJUCao/troy-mode-trial` 上进行（第 9.4 节）。试运行发现的事实写进设计的修改记录。
7. **状态 PR**，单独一个：用需求文档第 7.1 节的标签，更新需求文档第 7.2 节里这个功能的状态，并提高需求文档的版本，中英文都改。标签从不说得比实际运行过的更多（R13）。

决定编号在各份设计之间连续：F11 的设计到 D100 为止，所以下一份设计从 D101 开始。

## 9.3 推送前的检查

使用 `troy-pstack` mamba 环境里的 Python：`D:\miniforge3\envs\troy-pstack\python.exe`。永远不要用系统的 Python 3.14，它会掩盖 CI 的 Python 能发现的缺失导入；也永远不要创建 `.venv`。把这个 Python 当作 `python`，在仓库根目录运行每个测试套件：

```bash
python -m unittest discover -s troy-mode/checks/tests
python -m unittest discover -s troy-mode/init/tests
python -m unittest discover -s troy-mode/hooks/tests
python -m unittest discover -s troy-mode/flow/tests
python -m unittest discover -s troy-mode/dev/tests
python troy-mode/dev/check_pairs.py
python troy-mode/dev/check_links.py
```

每个套件都必须打印“Ran N tests”和 OK。不要加 `-t`。`check_pairs.py` 检查每个英文文档和它的镜像有相同的标题、表格、代码块、标记和版本。`check_links.py` 检查 `README.md` 和 `docs/troy-mode/` 里的每个相对链接和锚点都能解析。CI 在 GitHub 上运行所有这些检查；Windows 的测试任务大约要 20 到 25 分钟，时间上限是 45 分钟。

## 9.4 试运行

试运行在你的电脑上用嵌套的 `claude -p` 会话运行 troy-mode，troy-pstack 从 PR 分支加载，仓库是私有的 `ZJUCao/troy-mode-trial`。你的回答写在这些会话的提示里。

你在 2026-11-08 为此给了长期许可，形式是 troy-pstack 的 `.claude/settings.local.json` 里的一条 `autoMode.allow` 规则（[F08 设计第 11.3 节](../design/F08-release.zh-CN.md#113-试运行d78)）：加载 troy-pstack 的嵌套 `claude -p` 会话，可以不经询问在 `ZJUCao/troy-mode-trial` 里创建分支、issue 和 PR，并合并 PR。它不包括：

- 其他任何仓库；
- 推送 `main`；
- 创建或删除仓库。

如果试运行仍然被拒绝，会话会告诉你，不会绕过去。

## 9.5 谁来合并 troy-pstack 的 PR

你在 2026-11-06 给的长期许可：

- **代码 PR**，实现你批准过的设计，每项检查一通过，就由会话合并。
- **状态 PR**，只改需求文档里的状态标签、版本和修改记录行，检查通过后就合并。
- **设计和需求变更**，在你于聊天里批准内容之后，由会话合并。问题还没决定的草稿从不合并。
- **PR 分支**可以修订 commit 并强制推送，以保持每个 PR 一个 commit。

会话用 `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>` 合并，而且只在每项检查都通过时。谁都不在 `main` 上提交，也不推送 `main`。troy-pstack 的 `.claude/settings.local.json` 允许 `gh pr merge`，并拒绝任何提到 `main` 的 `git push` 命令行，所以推送和 `gh pr create --base main` 要作为两条命令分开运行。合并被拒绝时，会报告给你，从不绕过。

## 9.6 新的插件版本

只有 `.claude-plugin/plugin.json` 里的 `version` 升高时，Claude Code 才会更新已安装的插件（[F10 设计第 6 节](../design/F10-docs.zh-CN.md#6-插件版本d89)）。所以凡是改变项目所得内容的 troy-pstack PR，比如改 troy-check、模板、语言包、技能或角色，都要升版本：

- 修复升补丁号，比如从 0.2.0 到 0.2.1；
- 功能升次版本号，比如从 0.2.0 到 0.3.0。

合入之后，按[第 1.3 节](01-install.zh-CN.md#13-插件出新版本后更新)更新已安装的插件：拉取 troy-pstack 的主检出，用自带的命令行更新插件市场和插件，然后重启 Claude Code。然后每个项目用 `/troy-pstack:troy-mode 升级 troy-mode` 拿到新版本，这个请求开出的 PR 标题写明版本号（[第 8.6 节](08-reference.zh-CN.md#86-常见问题)）。试点（F11）靠这一点把修复带进它的项目（[F11 设计](../design/F11-pilot.zh-CN.md)）。
