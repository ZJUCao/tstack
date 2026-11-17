# 8. 参考

> 本文件是 [`08-reference.md`](08-reference.md) 的中文镜像，同步自英文版 0.2（2026-11-17）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 0.2 |
| 日期 | 2026-11-17 |
| 事实来源 | 英文版 [`08-reference.md`](08-reference.md)。本文件是中文镜像。 |

日常查阅用的表。这里的每个请求、标题和评论标题，都以入口技能 [`skills/troy-mode/SKILL.md`](../../../skills/troy-mode/SKILL.md) 为准。

## 8.1 请求

每个请求都输入在 `/tstack:troy-mode` 后面，用你自己的话说。

| 请求，例如 | 流程 | 指南 |
| --- | --- | --- |
| “开始一个项目：……”，或者在没有 `.troy-mode/` 的文件夹里提出任何请求 | 项目初始化 | [2](02-start.zh-CN.md) |
| “下一个功能”、“F04”、“F04 到 F06”、“v0.1 剩下的功能” | 功能循环 | [3](03-features.zh-CN.md) |
| “bug：……”、“修复 #12” | 修 bug | [4.1](04-bugs-and-changes.zh-CN.md#41-修-bug) |
| “变更：……”、“导出功能还应该……” | 需求变更 | [4.2](04-bugs-and-changes.zh-CN.md#42-修改需求) |
| “为什么……”、“……怎样……”、“试一个……” | 流水线之外的工作：不开 PR | [4.3](04-bugs-and-changes.zh-CN.md#43-问题和试验) |
| “发布 v0.1”、“发布 v0.1.1”、“发布” | 版本发布 | [5](05-release.zh-CN.md) |
| “加一条规则……”、“修改 P01……”、“废止 P02”、“所有项目的一条规则……” | 规则变更 | [6](06-rules.zh-CN.md) |
| “升级 troy-mode” | 升级项目里 troy-mode 的文件 | [8.6](#86-常见问题) |
| “继续”、“状态”，或者什么都不写 | 接续 | [7.5](07-taking-part.zh-CN.md#75-在新会话里继续) |

一个请求同时符合两个流程，或者一个都不符合时，troy-mode 会问你一个问题，并给出推荐的答案。单独运行 `/tstack:troy-init` 只做初始化这一步；`/tstack:troy-init lang python` 和 `/tstack:troy-init upgrade` 分别运行语言步骤和升级。

## 8.2 PR 标题和分支

每个 PR 只有一个 commit，它的标题行就是 PR 标题（R01）。“在你批准之后”的意思是：你在聊天里回复，由 troy-mode 合并；或者你自己在 GitHub 上合并这个 PR。`F04`、`B12`、`P01`、`v0.1` 和 `v0.1.0` 分别代表功能、bug、规则、版本和标签。

| PR | 标题 | 分支 | 合并者 |
| --- | --- | --- | --- |
| 初始化 | `[rules] Set up troy-mode` | `troy-mode/init` | troy-mode |
| 需求文档 | `[docs] Add the requirements` | `troy-mode/requirements` | troy-mode，在你批准之后 |
| 架构 | `[docs] Add the architecture` | `troy-mode/architecture` | troy-mode，在你批准之后 |
| 语言步骤 | `[rules] Add the Python pack`、`[rules] Add the C/C++ pack` | `troy-mode/lang-python`、`troy-mode/lang-cpp` | troy-mode |
| 功能，PR 1 到 6 | `[F04 1/6 design] <name>` 到 `[F04 6/6 accept] <name>` | `troy-mode/f04-1-design` 到 `troy-mode/f04-6-accept` | troy-mode；前几个功能的 PR 1 和 2 在你批准之后 |
| 你的批准，在 GitHub 上合并时 | `[docs] Record Troy's approval of <document>` | `troy-mode/approve-<slug>` | troy-mode |
| 由你批准的功能 | `[rules] Set the features Troy approves` | `troy-mode/approvals` | troy-mode |
| 测试修正 | `[F04 test-fix] <summary>` | `troy-mode/f04-test-fix` | troy-mode |
| 文档旁支 PR | `[docs] Add cases to the F04 test plan`、`[docs] Accept the dependency <name>` | `troy-mode/f04-docs` | troy-mode |
| bug，PR A 和 B | `[B12 A/B test] <summary>`、`[B12 B/B fix] <summary>` | `troy-mode/b12-test`、`troy-mode/b12-fix` | troy-mode |
| 需求变更 | `[docs] Change the requirements: <summary>` | `troy-mode/change-<slug>` | troy-mode，在你批准之后 |
| 版本测试方案 | `[docs] Add the v0.1 test plan`、`[docs] Update the v0.1 test plan` | `troy-mode/v0.1-test-plan` | troy-mode |
| 版本测试 | `[v0.1 tests] End-to-end and stress tests`；写错的版本测试在 `[v0.1 tests] Fix <scenario ID>` 里修 | `troy-mode/v0.1-tests` | troy-mode |
| 发布 | `[docs] Release v0.1.0` | `troy-mode/release-v0.1.0` | troy-mode，在你验收之后 |
| 你的验收，在 GitHub 上合并时 | `[docs] Record Troy's acceptance of v0.1.0` | `troy-mode/record-v0.1.0` | troy-mode |
| 规则 | `[rules] Add P01, <summary>`、`[rules] Change P01, <summary>`、`[rules] Retire P01, <summary>` | `troy-mode/rule-p01`、`troy-mode/rule-p01-change`、`troy-mode/rule-p01-retire` | troy-mode |
| 规则的架构改动 | `[docs] Change the architecture for P01` | `troy-mode/p01-architecture` | troy-mode |
| 规则的清理 | `[refactor] Apply P01 to <area>`、`[P01 test-fix] Apply P01 to tests` | `troy-mode/p01-cleanup-<area>`、`troy-mode/p01-test-fix` | troy-mode |
| 升级 | `[rules] Upgrade troy-mode to <version>` | `troy-mode/upgrade-<version>` | troy-mode |

试验的分支 `troy-mode/try-<slug>` 从不推送。

## 8.3 评论标题

troy-mode 把每次审查、每次失败的尝试、每次升级上报，以及每次请你处理的事，都作为 PR 评论发出，评论的第一行是下面的标题之一。没有这些标题的评论是你写的。

| 标题 | 什么时候发出 |
| --- | --- |
| `<Role> review, round <n>: <result>` | 某个审查方报告时，例如 `Architect review, round 2: changes-requested`。后面是审查意见，每条一行、带编号，以规则编号或检查项开头。 |
| `<Role> attempt <n>: failed` | 产出方的一次尝试失败时。后面是失败的检查。 |
| `Escalation: <trigger>` | troy-mode 停下来等你时（[第 7.3 节](07-taking-part.zh-CN.md#73-回答升级上报)）。 |
| `Waiting for Troy: approve this PR` | PR 等你批准时。下面一行指向描述开头给你的摘要。 |
| `Waiting for Troy: accept <tag>` | 发布等你在自己的设备上测试时。 |
| `Real run output, part <n>` | PR 6 真跑的真实输出放不进描述时，放在这里。 |
| `Release test, run <n>: passed` 或 `failed` | 发布测试的报告；跑了 `real-run --all` 时带一段 “Real run”。 |
| `Release test by Troy, run <n>: accepted`、`failed` 或 `not accepted` | 你对发布的回复，附上你的原话。 |
| `Bug deferred by Troy: #<n>` | 你把一个未关闭的 bug 推迟到这次发布之后时。 |
| `Retrospective: <tag>` | 复盘，它结束这次发布。 |

## 8.4 项目里的文件

| 路径 | 内容 | 谁来改 |
| --- | --- | --- |
| `docs/requirements.md` 及镜像 | 需求、功能、顺序、版本、状态 | 产品经理 |
| `docs/prototypes/` | 原型 | 产品经理 |
| `docs/prototypes/<name>.run.toml` | 原型的运行文件：路径映射、每一节的数据文件夹怎样开始、替换掉的日期词，以及 `later` 和 `skip` 标记，由 `troy_flow.py real-run --item <ID>` 和 `real-run --all` 读取（[F12 设计第 4 节](../design/F12-real-run.zh-CN.md#4-运行文件d103)） | 产品经理，在 PR 6 里 |
| `docs/architecture.md` 及镜像、`docs/adr/` | 架构及其决策记录 | 架构师 |
| `docs/features/<id>-<slug>/design.md` 及镜像 | 一个功能的接口设计 | 接口设计师；架构师写其中的审查一节 |
| `docs/features/<id>-<slug>/test-plan.md` 及镜像 | 一个功能的测试方案 | 测试经理 |
| `docs/versions/<version>/test-plan.md` 及镜像 | 一个版本的测试方案和验收记录 | 测试经理；troy-mode 加上你的验收 |
| `CHANGELOG.md` 及镜像 | 每次发布一节 | 产品经理 |
| 源文件 | 代码 | 开发工程师 |
| `tests/`、`version-tests/` | 测试和版本测试 | 测试工程师 |
| `docs/rules.md` 及镜像 | 规则表 | 只有 troy-init（R 行）和规则变更流程（P 行） |
| `.troy-mode/config.toml` | 项目的配置（第 8.5 节） | troy-init、规则变更流程、“由你批准的功能”PR，以及你 |
| `.troy-mode/checks/`、`.troy-mode/templates/` | troy-mode 自己的文件 | 只有 troy-init。改了其中一个，下次升级就会在那个文件上停下。 |
| `.troy-mode/install.toml` | troy-init 记录它安装了什么 | troy-init，它在每一步都重写这个文件。不要改它。 |
| `pyproject.toml`、`environment.yml`、`requirements-dev.lock`（Python）；`CMakeLists.txt`、`CMakePresets.json`、`cmake/troy.cmake`、`requirements-tools.in`、`requirements-tools.lock`、`.clang-format`、`.clang-tidy`（C/C++） | 构建文件、环境、锁文件和各个工具的配置 | 语言步骤；你接受一个依赖之后，产出方和系列锁文件；规则 PR 的配置行和基线行；以及你，在一个 `[rules]` PR 里 |
| `.github/workflows/project-rules.yml` | 项目为自己的规则设的检查步骤 | 规则变更流程 |
| `.troy-mode/progress.md` | 进度文件。只在本地，被 git 忽略。 | troy-mode |
| `.github/workflows/troy-mode.yml`、`.github/pull_request_template.md` | troy-check 的 CI 任务和 PR 模板 | 只有 troy-init |
| `.claude/settings.local.json` | 你的 Claude Code 权限。被 git 忽略。 | 你 |

每个角色运行时，hook 把它限制在自己的写入范围之内，运行之后再检查一次（[F05 设计第 5 节](../design/F05-hooks.zh-CN.md#5-写入范围)、[F07 设计第 7 节](../design/F07-entry-skill.zh-CN.md#7-每次运行之后的检查d59)）。开发工程师对测试的修改会被拒绝（R08）。

## 8.5 配置项

`.troy-mode/config.toml`。每一项都可以不写；未知的项或错误的类型会让 troy-check 停下，所以打错字永远不会关掉一条规则。troy-check 从 PR 的合并基点读取这个文件，所以一项改动从做出它的那个 PR 之后的 PR 起生效。改动在一个 `[rules]` PR 里合入。带注释的默认配置是 [`troy-mode/checks/config.default.toml`](../../../troy-mode/checks/config.default.toml)。

| 表 | 键 | 默认值和含义 |
| --- | --- | --- |
| `[identity]` | `commit_email` | 唯一允许的作者邮箱（R19）。由 troy-init 填写。 |
| `[paths]` | `config`、`dependencies`、`tests`、`docs`、`lock`、`generated`、`allow_markers` | 加到内置路径类别上的模式。它们从不替换内置的模式。 |
| `[limits]` | `source_lines`、`source_files` | R03：每个源码 PR 500 行、5 个文件。 |
| `[limits]` | `line_coverage`、`branch_coverage` | R11：改动代码的行覆盖率 90%，分支覆盖率 80%。 |
| `[limits]` | `function_lines`、`file_lines` | R04 和 R06：每个函数体 50 行，每个源文件 500 行。 |
| `[tests]` | `legacy` | 名字不需要用例编号的测试文件（R10）。它们仍然必须通过。 |
| `[lang]` | `name`、`source_roots` 或 `include_dirs`、`environment`、`series` | 由语言步骤设置。 |
| `[attribution]` | `mode` | R19：`strict`（默认），或 `trailers`，用于关于 Claude 本身的项目。 |
| `[roles.<role>]` | `model`、`effort` | 一个角色在这个项目里的模型和 effort（[第 1.5 节](01-install.zh-CN.md#15-模型和-effort)）。 |
| `[flow]` | `troy_approves_first` | 顺序里排在最前面的多少个功能的 PR 1 和 PR 2 由你批准。默认 3；0 表示一个都没有。 |
| `[summary]` | `max_chars` | R22：设计、测试计划、需求和架构 PR 开头给你的摘要，每种语言最多多少个字符。默认 2000。 |

## 8.6 常见问题

| 问题 | 怎么办 |
| --- | --- |
| **合并、修改提交或强推被权限拒绝了。** troy-mode 停下来，说出了要加的权限。自动模式把 `gh pr merge` 当作未经审查的合并拒绝，或把 `git commit --amend --no-edit`、`git push --force-with-lease` 当作 “Git Destructive” 拒绝。 | 把[第 1.4 节](01-install.zh-CN.md#14-合并权限)的三项加进项目的 `.claude/settings.local.json` 的 `allow` 列表，然后输入 `/tstack:troy-mode 继续`。troy-mode 从不绕过拒绝。 |
| **hook 挡住了一个角色。** | 通常什么都不用做。troy-mode 的 hook 让每个角色留在自己的写入范围之内，并把每次拦截记进 `<git dir>/troy-mode/hooks.log`，日志里没有命令行，也没有文件内容，而且只保留最近一天的行（[issue #66](https://github.com/ZJUCao/troy-pstack/issues/66)）。troy-mode 会在报告里点出这次运行的日志行。角色在范围之外改的文件会被撤销，角色再运行一次。同一个阶段里第二次发生时，troy-mode 升级上报（[F05 设计第 10 节](../design/F05-hooks.zh-CN.md#10-错误速度和日志)、[F07 设计第 7 节](../design/F07-entry-skill.zh-CN.md#7-每次运行之后的检查d59)）。 |
| **刚改名为 tstack 之后，每个角色写文件都因超出范围被拒绝。** | troy-pstack 还装着或还启用着，它的 hook 把 tstack 的角色当作未知的子代理。卸载它，然后重启 Claude Code（[第 1.3 节](01-install.zh-CN.md#13-插件出新版本后更新)）。 |
| **`/poteto-mode` 或 `/no-comments` 被拒绝了。** 一个 hook 说这个命令在本项目里停用。 | 改用 `/tstack:troy-mode <请求>`；想试 poteto-mode，就用一个不是 troy-mode 项目的文件夹（[F13 设计第 5 节](../design/F13-mode-guard.zh-CN.md#5-拒绝不留例外d123)）。 |
| **测试只在一个平台上运行。** 本地的 `troy-check code` 失败，只是因为有个测试在你的电脑上跳过了，比如只在 Linux 上运行的测试。 | 什么都不用做。troy-mode 把本地检查算作通过，在 PR 的 Checks 一节把这个用例列为“skipped here, checked by CI”，并只按 CI 的结果合并，CI 通过就证明这个测试运行过。测试方案必须写明这个用例为什么只在一个平台上运行（[F07 设计 D69](../design/F07-entry-skill.zh-CN.md#16-需要-troy-决定的事项)）。 |
| **Windows 路径长度。** `git add` 在 `docs/features/` 下的一个长路径上失败。 | 在需求文档里把每个功能的名称写短，比如“Export history as CSV”：它会成为功能的文件夹名，以及每个 PR 的标题。试运行里那里写了一整句话，超过了 Windows 的路径长度上限（[F07 设计第 8.1 节](../design/F07-entry-skill.zh-CN.md#81-阶段)）。在 troy-mode 之外，也可以用 `git config --global core.longpaths true` 让 Git for Windows 接受长路径，这会改变你电脑上每个仓库的这项设置。 |
| **项目里的 troy-mode 比插件旧。** `status` 说项目的 troy-check 比插件的旧。`[roles]`、`[flow]` 和一些检查需要新的副本。 | 先更新插件（[第 1.3 节](01-install.zh-CN.md#13-插件出新版本后更新)）。然后输入 `/tstack:troy-mode 升级 troy-mode`。它会开出 `[rules] Upgrade troy-mode to <version>`：替换没人改过的 troy-mode 自有文件，把规则表的 R 行更新到最新，保留 P 行，然后合并。改过的文件会让它停下：troy-mode 问你是否替换。它从不改配置或构建文件；它会列出它们不同的地方，供你放进一个 `[rules]` PR。没有要升级的东西时，它不开 PR。 |
| **找不到 Python。** hook 停下，提示“troy-mode: no Python 3.11 or newer found”。 | 把 `TROY_MODE_PYTHON` 设为一个 Python 3.11 或更新版本（[第 1.1 节](01-install.zh-CN.md#11-你的电脑需要什么)）。 |
| **语言步骤的锁文件编译在桌面应用里失败了。** uv 说它无法把文件移到另一个磁盘驱动器。 | 原因是应用的沙箱挡住了 uv 默认的缓存文件夹，不是你的电脑有问题。试点中，troy-mode 恢复了这一步的文件，把 `UV_CACHE_DIR` 设为会话临时文件夹里的一个文件夹，再运行这一步，就通过了。如果 troy-mode 停了下来，就让它照样做（[issue #48](https://github.com/ZJUCao/troy-pstack/issues/48)）。 |
| **一条命令一直不结束，或者角色报告之后还留着一个 `python.exe`。** | 用 `-` 作为脚本启动 Python，或者让它从 heredoc、管道或 `/dev/null` 读输入的命令，可能永远停在 Python 的提示符上；在 Windows 上，`python3` 还可能是 Microsoft Store 的占位程序，同样会一直等。这样的命令会碰到 shell 工具的时间上限，troy-mode 随后停掉它；试点中这发生了 39 次（[issue #64](https://github.com/ZJUCao/troy-pstack/issues/64)）。角色留下的、来自项目环境的 `python.exe`，可以在没有角色运行时在任务管理器里结束。 |
| **一个文件被改了，而当前运行的角色并没在改它。** troy-mode 每次运行之后的检查怪错了角色。 | 一个之前在后台启动的角色运行很晚才结束，写下了它的旧改动；试点中，一次开发者运行晚了 11.5 小时，在测试工程师运行期间才结束。troy-mode 停下来，先问你再恢复这个文件（[issue #49](https://github.com/ZJUCao/troy-pstack/issues/49)）。如果这个改动不属于当前任何阶段，就回答“是”。 |
| **CI 检查在产出方的文件之外失败了**，比如运行器上的下载错误，或者检出步骤里的 “Repository not found”。 | troy-mode 停下来告诉你；它自己不重新运行 CI。运行器上的下载错误通常在第二次运行时就能通过：你可以自己重新运行失败的任务，比如用 `gh run rerun <run ID> --failed`，然后输入“继续”。试点中，“Repository not found” 来自 GitHub 那边，下一次推送时就消失了。 |

## 8.7 规则 R01 到 R22

完整的规则文字在[规则模板](../../../troy-mode/templates/rules.zh-CN.md)里，每个项目都把它复制成 `docs/rules.md`；也在[需求文档第 6 节](../requirements.zh-CN.md#6-规则)里。硬规则不满足就不能合并，软规则要在 PR 描述里写明原因，审查由某个角色检查，流程由 troy-mode 自己遵守。

| 编号 | 简述 | 类型 |
| --- | --- | --- |
| R01 | 每个 PR 一个 commit，它的标题行等于 PR 标题 | 硬 |
| R02 | 每个 PR 只包含一个阶段的产出：文档、源码或测试 | 硬 |
| R03 | 源码 PR 最多改动 500 行，最多涉及 5 个文件 | 软 |
| R04 | 函数体最多 50 行 | 硬 |
| R05 | 文档注释使用 Google 风格；代码注释用英文 | 硬 |
| R06 | 源码文件最多 500 行 | 软 |
| R07 | 模块之间只按架构允许的方向依赖，不能有循环 | 硬 |
| R08 | 开发工程师永远不改测试文件 | 硬 |
| R09 | 测试 PR 里的每个新测试对着 mock 都失败 | 硬 |
| R10 | 每个测试的名字以它的用例编号或 bug 编号开头 | 硬 |
| R11 | 改动代码的行覆盖率至少 90%，分支覆盖率至少 80% | 硬 |
| R12 | 改了英文文档，就要同时更新它的中文镜像 | 硬 |
| R13 | 状态标签如实说明功能做到了哪一步 | 审查 |
| R14 | 只有带性能指标的接口才写性能测试 | 审查 |
| R15 | 每个修过的 bug 都保留它的重现测试 | 审查 |
| R16 | 引入新的第三方依赖需要架构师批准 | 审查 |
| R17 | 审查循环最多 3 轮，之后升级上报 | 流程 |
| R18 | 前几个功能的 PR 1 和 PR 2 由你批准；其余由 troy-mode 合并 | 流程 |
| R19 | commit 使用你的邮箱。commit、PR、评论、评审、issue 和发布说明不带 Claude 署名，发出前检查 | 硬 |
| R20 | 合并的文档和 PR 描述里没有模板标记或填写说明 | 硬 |
| R21 | 每个改动都通过从单独分支发起的 PR 进入 `main` | 硬 |
| R22 | 设计、测试计划、需求和架构 PR 以给你的中英文摘要开头 | 硬 |
