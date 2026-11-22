# 9. 修改 troy-mode

> 本文件是 [`09-changing-troy-mode.md`](09-changing-troy-mode.md) 的中文镜像，同步自英文版 0.2（2026-11-16）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.2 |
| 日期 | 2026-11-16 |
| 事实来源 | 英文版 [`09-changing-troy-mode.md`](09-changing-troy-mode.md)。本文件是中文镜像。 |

本页讲的是在 tstack 里改 troy-mode 本身的工作：由你来做，或者由你在那里启动的 Claude Code 会话来做。troy-mode 自己的流水线不在这里运行。tstack 有它自己的流程，写在本页，这样每个会话都能找到（[F10 设计 D92](../design/F10-docs.zh-CN.md#11-需要-troy-决定的事项)）。

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
| tstack 自己的工具 | `troy-mode/dev/`：`check_pairs.py`、`check_links.py`、`check_name.py`、`check_exam.py`、`build_sample.py`，以及示例项目的测试 |
| 角色考试 | `troy-mode/exam/`：`troy_exam.py`、它的引擎和考题（第 9.7 节） |

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

使用 `tstack` mamba 环境里的 Python：`D:\miniforge3\envs\tstack\python.exe`。在这个环境建好之前，`troy-pstack` 环境里装着同样的包，对 tstack 一样能用（[F19 设计第 6.4 节](../design/F19-rename.zh-CN.md#64-mamba-环境d196)）。永远不要用系统的 Python 3.14，它会掩盖 CI 的 Python 能发现的缺失导入；也永远不要创建 `.venv`。把这个 Python 当作 `python`，在仓库根目录运行每个测试套件：

```bash
python -m unittest discover -s troy-mode/checks/tests
python -m unittest discover -s troy-mode/init/tests
python -m unittest discover -s troy-mode/hooks/tests
python -m unittest discover -s troy-mode/flow/tests
python -m unittest discover -s troy-mode/exam/tests
python -m unittest discover -s troy-mode/dev/tests
python troy-mode/dev/check_pairs.py
python troy-mode/dev/check_links.py
python troy-mode/dev/check_name.py
```

每个套件都必须打印“Ran N tests”和 OK。不要加 `-t`。`check_pairs.py` 检查每个英文文档和它的镜像有相同的标题、表格、代码块、标记和版本。`check_links.py` 检查 `README.md` 和 `docs/troy-mode/` 里的每个相对链接和锚点都能解析。`check_name.py` 检查历史之外的文字（历史如已批准的设计和修改记录）不再提到插件的旧名字（[F19 设计第 11.2 节](../design/F19-rename.zh-CN.md#112-名字检查)）。CI 在 GitHub 上运行所有这些检查；Windows 的测试任务大约要 20 到 25 分钟，时间上限是 45 分钟。

## 9.4 试运行

试运行在你的电脑上用嵌套的 `claude -p` 会话运行 troy-mode，tstack 从 PR 分支加载，仓库是私有的 `ZJUCao/troy-mode-trial`。你的回答写在这些会话的提示里。

会话用 `git archive` 把 PR 的最新提交复制到它的 scratchpad 里一个名叫 `tstack` 的文件夹，这样 hook 的 Read 规则 `Read(//**/tstack/**)` 才能匹配它；再用 `--plugin-dir` 加载，路径要写成 Windows 路径，比如 `C:/...`，写成 Git Bash 路径 `/c/...` 时什么也不会加载，也不报错。每个嵌套会话还带上 `--settings '{"enabledPlugins":{"tstack@tstack":false}}'`，它只在这个会话里关掉你安装的那份插件，这样两份插件永远不会同时运行（[F19 设计第 3 节](../design/F19-rename.zh-CN.md#3-探测)）。

你在 2026-11-08 为此给了长期许可，2026-11-16 又把它扩展到 tstack 这个名字，形式是 tstack 的 `.claude/settings.local.json` 里的一条 `autoMode.allow` 规则（[F08 设计第 11.3 节](../design/F08-release.zh-CN.md#113-试运行d78)）：加载 tstack 的嵌套 `claude -p` 会话，可以不经询问在 `ZJUCao/troy-mode-trial` 里创建分支、issue 和 PR，并合并 PR。它不包括：

- 其他任何仓库；
- 推送 `main`；
- 创建或删除仓库。

如果试运行仍然被拒绝，会话会告诉你，不会绕过去。

## 9.5 谁来合并 tstack 的 PR

你在 2026-11-06 给的长期许可：

- **代码 PR**，实现你批准过的设计，每项检查一通过，就由会话合并。
- **状态 PR**，只改需求文档里的状态标签、版本和修改记录行，检查通过后就合并。
- **设计和需求变更**，在你于聊天里批准内容之后，由会话合并。问题还没决定的草稿从不合并。
- **PR 分支**可以修订 commit 并强制推送，以保持每个 PR 一个 commit。

会话用 `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>` 合并，而且只在每项检查都通过时。谁都不在 `main` 上提交，也不推送 `main`。tstack 的 `.claude/settings.local.json` 允许 `gh pr merge`，并拒绝任何提到 `main` 的 `git push` 命令行，所以推送和 `gh pr create --base main` 要作为两条命令分开运行。合并被拒绝时，会报告给你，从不绕过。

## 9.6 新的插件版本

只有 `.claude-plugin/plugin.json` 里的 `version` 升高时，Claude Code 才会更新已安装的插件（[F10 设计第 6 节](../design/F10-docs.zh-CN.md#6-插件版本d89)）。所以凡是改变项目所得内容的 tstack PR，比如改 troy-check、模板、语言包、技能或角色，都要升版本：

- 修复升补丁号，比如从 0.2.0 到 0.2.1；
- 功能升次版本号，比如从 0.2.0 到 0.3.0。

合入之后，按[第 1.3 节](01-install.zh-CN.md#13-插件出新版本后更新)更新已安装的插件：拉取 tstack 的主检出，用自带的命令行更新插件市场和插件，然后重启 Claude Code。然后每个项目用 `/tstack:troy-mode 升级 troy-mode` 拿到新版本，这个请求开出的 PR 标题写明版本号（[第 8.6 节](08-reference.zh-CN.md#86-常见问题)）。试点（F11）靠这一点把修复带进它的项目（[F11 设计](../design/F11-pilot.zh-CN.md)）。

## 9.7 角色考试

改动角色所遵循的说明，在合入之前要通过角色考试（[F16 设计](../design/F16-role-exam.zh-CN.md)）。考试在试点项目状态的临时副本上运行角色，一次用 PR 的基线，一次用 PR 的最新提交，再由一个没做过这项任务的新会话在不知道版本的情况下给结果打分。

**哪些 PR。** 改动说明集合中任何文件的 PR：`agents/troy-*.md`、`troy-mode/roles/common.md`、`troy-mode/flow/troyflow/brief.py` 以及它导入的引擎模块、`troy-mode/templates/`、角色会读的技能（`skills/technical-writing/` 和 `skills/benchmark-checklist/`）、`skills/troy-mode/SKILL.md` 里“Running a role”和“The summary for Troy”这两节，以及 `troy-mode/exam/` 里考试自己的考题和代码。在 PR 描述里有带最新提交说明哈希的考试小节之前，CI 的文档任务会拒绝这样的 PR（[F16 设计第 9 节](../design/F16-role-exam.zh-CN.md#9-哪些修改要通过考试以及-prd157)）。

**怎样启动。** 在 PR 的工作树里，用 `tstack` 环境的 Python：

```bash
python troy-mode/exam/troy_exam.py affected --base origin/main
python troy-mode/exam/troy_exam.py run --base origin/main
```

`affected` 列出改动涉及的考题，不调用模型。`run` 先估算花费，然后对每道受影响的考题用两个版本各运行 5 次，让评分会话给每次运行打分，比较两个版本，写出报告。基线在 14 天内的运行，只要它们依赖的东西都没变，就会重复使用。它要几分钟到几小时，所以会话在后台等它。修复某道考题的 PR 用 `--fixes <case>` 写明它。遇到用量上限后，用 `troy_exam.py resume <exam ID>` 继续。

**预算。** 第一轮按标价不超过 60 美元时，考试不问就开始。超过时，会话先给你看第一轮和总额（加上每道考题的第二轮）、考题和时间，你同意后才开始，你的同意涵盖总额。规则要求的第二轮会让考试超过 60 美元、或者超过你同意过的总额时，考试在这一轮之前等你答复。花费达到估算的 1.5 倍时，考试也等你答复；这里的估算算上规则已经要求的第二轮。等待期间，会话给你看已经花了多少、还剩多少：你同意，它就运行 `troy_exam.py resume <exam ID> --yes`；你不同意，就运行 `resume <exam ID> --stop`，用已有的运行结束考试，被切断的考题显示 "no verdict"。同时最多运行两个角色，每次运行都有花费上限（[F16 设计](../design/F16-role-exam.zh-CN.md) 10.3）。

**PR 里写什么。** `troy_exam.py block <exam ID>` 打印“Role exam”小节，会话把它贴进 PR 描述。它的 `Instructions` 一行必须和 PR 的最新提交一致，所以之后再推送、改动了说明集合时，要重新考试。考试没通过时，不在同一个最新提交上重考：要么改动最新提交，要么你在聊天里接受这次失败，小节里就写 `failed, accepted by Troy on <date>: <reason>`。

**文件放在哪里。** `D:\Troy\troy-mode-work` 里放着试点仓库的镜像、每个起点一个的环境、运行期间每次运行的临时项目、带全部报告的结果，以及每道考题的运行记录。`TROY_EXAM_ROOT` 可以指定别的文件夹。
