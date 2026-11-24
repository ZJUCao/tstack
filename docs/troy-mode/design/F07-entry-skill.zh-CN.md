# F07 设计：入口技能（troy-mode）

> 本文件是 [`F07-entry-skill.md`](F07-entry-skill.md) 的中文镜像，同步自英文版 1.18（2026-11-24）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.20](../requirements.zh-CN.md#72-功能列表) 中的 F07 |
| 版本 | 1.18 |
| 日期 | 2026-11-24 |
| 状态 | Troy 已于 2026-11-07 批准，含 D57 到 D68。1.1 版记录第 14.3 节第一部分试运行确认的事实。1.2 版记录 Troy 的 D69 和第二部分确定的细节。1.6 版加入 D201，Troy 已于 2026-11-18 以 tstack issue #46 批准；1.7 版加入 D202，同一天以 issue #47 批准；1.8 版加入 D203，同一天以 issue #52 批准；1.9 版加入 D204，同一天以 issue #68 批准。1.10 版跟随 F05 的 D231，即 Troy 于 2026-11-21 批准的 tstack issue #49（第 6.2 和 7 节）。1.11 版为 tstack issue #73（Troy 于 2026-11-16 接受）加入 D261 到 D263；每项都取推荐答案，依据 Troy 2026-11-22 的长期同意批准。1.12 版为同一天接受的 tstack issue #74 加入 D264 到 D267，同样批准。1.13 版加入 D205 到 D207，即 tstack issue #63 的设计，Troy 已于 2026-11-16 接受这条规则；其中的选择按 Troy 2026-11-22 的长期同意采用推荐选项，Troy 已于 2026-11-22 批准它的需求子句（第 6.4 节）。1.14 版记下 F20 设计（D268 到 D279，Troy 已于 2026-11-22 批准）带来的改动，这些改动随 F20 的构建落地。1.15 版为 CR1 的任务简报加上安全审查的检查，并加入 CR2 的任务简报，来自 F04 为 tstack issue #75 定的 D280 到 D283，依据 Troy 2026-11-22 的长期同意批准（第 6.5 节）。1.16 版为 tstack issue #67（F11 试点里的一个问题）加入 D284 到 D287：给后续功能的备注保存在 GitHub 上，并送到那些功能的任务简报里；每项都采用推荐答案，依据 Troy 2026-11-22 的长期同意批准（第 6.6 节）。1.17 版记录 tstack #75 的构建确定的细节（第 6.5 节），1.18 版记录 tstack #67 的构建和它的试运行确定的细节（第 6.6 和 14.4 节）。 |
| 事实来源 | 英文版 [`F07-entry-skill.md`](F07-entry-skill.md)。本文件是中文镜像。 |

## 1. 范围

F07 是 Troy 在 troy-mode 项目里做任何工作时输入的命令：`/troy-pstack:troy-mode <请求>`（需求文档 3.1）。它交付一个技能和它背后的引擎。有了它们，主会话会：

1. 把每个请求分到一个流程（第 4 节）；
2. 运行这些流程：项目初始化（5.1）、功能循环（5.2）、修 bug（5.3）、需求变更（5.4）、流水线之外的工作（5.9），以及跨会话接续（5.10）；
3. 用任务简报启动每个角色，模型和 effort 取自 `.troy-mode/config.toml`（F04 D32），同一时间只运行一个会写文件的角色；
4. 在每次运行之后检查角色只改了写入范围内的文件（F04 D31）；
5. 提交、开 PR、发布审查意见、统计审查轮数和尝试次数、升级上报（5.7），并在合并权限之内合并（R17、R18）；
6. 维护进度文件。

版本发布流程（5.5）和规则变更流程（5.8）属于 F08 和 F09。F07 把这类请求分给它们。5.6（测试什么时候运行）和 5.7（升级上报）不是请求，而是其他流程里的步骤。

F07 分两部分合入（D67）。第 1 部分包括请求分派、项目初始化、功能循环的主线、流水线之外的工作和接续。第 2 部分加上功能循环的旁支 PR（有争议的测试、覆盖率缺口和新依赖）、修 bug 和需求变更。

关于 Claude Code 的事实来自它的文档，以及 F04 到 F06 的试运行。其中两条决定了这份设计的形状。Claude 不能调用标了 `disable-model-invocation: true` 的技能，所以 F07 自己运行 troy-init 的引擎（F06 第 10 节），并通过读取 pstack 技能的 `SKILL.md` 来照着做。Agent 工具在每次调用时接受 `model` 和 `effort`；在桌面应用里，子代理在后台运行，结束时报告。试运行（第 14.3 节）会检查这两条。第一部分的试运行确认了它们：代码审查员的每次调用都带着 `[roles]` 设置的 `effort`，其他角色都没有带；写文件的角色在前台运行，所以会话会等每一个结束；在 `claude -p` 里，后台审查结束后会话会接着运行。后来的试点表明，桌面应用的 Agent 工具没有办法在前台启动子代理：在那里每个角色都在后台运行（F05 设计第 6.1 节）。

## 2. 位置

```text
skills/
  troy-mode/
    SKILL.md                  Troy 输入的技能（第 4 到 11 节）
troy-mode/
  flow/
    troy_flow.py              引擎的入口（第 3 节）
    troyflow/                 内部模块（由开发者决定）
    tests/                    单元测试（第 14.1 节）
```

- 引擎和 troy-check 一样，使用 Python 3.11 或更新版本，只用标准库（F02 D7）。它从插件自己的文件夹导入 troy-check 的配置读取、路径类别、标题解析和署名规则，以及 F05 的写入范围表。这样 F07 判断路径的方式和 hook、CI 完全一样。
- `SKILL.md` 设置 `disable-model-invocation: true`（需求文档第 8 节）。它用 `${CLAUDE_PLUGIN_ROOT}/troy-mode/flow/troy_flow.py` 指明引擎，用 `${CLAUDE_PLUGIN_ROOT}/troy-mode/roles/product-manager.md` 指明产品经理的说明，并且最先读取后者（F04 第 9.2 节）。它通过 Bash 工具运行两个引擎、git 和 gh：试运行里有一个会话选了 PowerShell，需要一项 `claude -p` 不会授予的权限，结果根本没有运行 `status`。
- F07 用 Troy 使用的语言和 Troy 交谈。文件、PR 和评论用英文，文档带中文镜像（R12）。

## 3. 引擎（D57）

### 3.1 命令

```text
python troy_flow.py status     [--write-progress] [--waiting <text>] [--note <text>] [common options]
python troy_flow.py brief      --task <task ID> --item <feature or bug ID> [--title <PR title>]
                               [--round <n>] [--input-file <path>] [common options]
python troy_flow.py snapshot   --role <role> [common options]
python troy_flow.py check-run  --run <run ID> [--allow-dependency <path>]... [common options]
python troy_flow.py approve    --doc <path> [--date <YYYY-MM-DD>] [common options]
python troy_flow.py check-text --file <path> [common options]
python troy_flow.py check-skips --report <troy-check JSON> --junit <path>... [common options]
python troy_flow.py series     [common options]
python troy_flow.py wait-checks --pr <number> --sha <commit> [--timeout <s>] [--interval <s>]
                               [--settle <s>] [common options]
python troy_flow.py costs      (--item <ID> | --tag <vX.Y.Z>) [--until <time>]
                               [--transcripts <folder>]... [common options]
python troy_flow.py note       --for <feature ID> --from <source> --file <path> [common options]

common options: [--repo <path>] [--json]
```

| 命令 | 作用 |
| --- | --- |
| `status` | 读取项目的状态（第 5 节），连同下一步一起输出。`--write-progress` 用它重写进度文件。它从 F07 的评论和 PR 推送过的提交的 CI 运行统计每个开着的 PR 的尝试次数（第 8.5 节，D261）。 |
| `brief` | 输出一次角色运行的任务简报（第 6.1 节），以及 Agent 工具的参数：`subagent_type`、`model` 和 `effort`。`--title` 给出状态推不出标题的 PR：bug 的 PR、旁支 PR（第 8.7 节），或者重做的阶段（第 11.2 节）。 |
| `snapshot` | 记录一次运行之前的状态（第 7 节），输出这次运行的 ID。 |
| `check-run` | 把运行之后的状态和快照比较（第 7 节）。输出要暂存的路径、发现的问题，以及每个问题怎样撤销。 |
| `approve` | 把 Troy 的批准记进文档和它的镜像的文件头（第 8.6 节）。对架构，它还会接受架构列出的 ADR（D202）。 |
| `check-text` | 按项目的 `[attribution] mode`，用 troy-check 的署名规则检查一条 PR 评论（R19）。 |
| `check-skips` | 读取 `troy-check code` 的 JSON 报告和 JUnit 文件，判断失败是否只是在本平台跳过的测试（第 8.6 节，D69）。 |
| `series` | 接受的依赖改动之后，规划系列锁文件：编译和安装它的命令、每个成员的测试，以及锁文件因此过期的成员（第 8.7 节，D66）。命令由技能运行。 |
| `wait-checks` | 等到 PR 的头提交 `--sha` 的每项 CI 检查都已登记并结束，然后报告是否全部通过（第 8.6 节，D204）。它只读 GitHub。 |
| `costs` | 读取 Troy 电脑上 Claude Code 的会话记录，给出一个功能或一个版本的角色运行（按角色，带模型）和按标价算的 token 费用，以及写进 PR 说明的那一节（第 8.8 节，D264 到 D267）。 |
| `note` | 把给后续功能的一条备注渲染成进度 issue 上的一条评论，给出要发到的 issue 和由技能运行的 `gh issue comment` 命令（第 6.6 节，D284 到 D287）。 |

- 引擎读取 git，并通过只读的 `gh` 调用读取 GitHub。`costs` 还读取 Claude Code 的会话记录，从不往那里写。它只写进度文件、`approve` 改动的文件头字段，以及它在 `<git dir>/troy-mode/flow/` 里的记录。它从不提交、推送或写 GitHub。这些由技能来做（F04 D29）。
- 退出码和 F06 设计 3.3 相同：0 表示完成；1 表示有问题让这一步停下，报告会说明是什么问题；2 表示引擎无法运行。

### 3.2 模型和 effort（F04 D32）

```toml
[roles.developer]
model = "opus"
effort = "high"

[roles.code-reviewer]
effort = "medium"

[flow]
troy_approves_first = 3
```

- `[roles.<role>]` 接受 `model` 和 `effort`。`model` 是 Agent 工具接受的别名，比如 `opus` 或 `sonnet`；`effort` 是 `low`、`medium`、`high`、`xhigh` 或 `max`。`<role>` 是 `architect`、`interface-designer`、`test-manager`、`developer`、`test-engineer` 或 `code-reviewer`。产品经理用主会话的模型（Q3）。
- `brief` 和 F05 的 hook 一样，读取 `HEAD` 上的配置，所以未提交的修改不起作用。
- 只有项目设置了 `model` 或 `effort`，技能才在 Agent 调用里传它们。调用时传入的模型优先于代理的 frontmatter（F04 D32）。没有设置时，角色用 Q3 的默认值。
- `[flow] troy_approves_first` 属于 D62。
- troy-check 拒绝未知的配置键，所以要让它的配置读取认识这两张表（第 12 节）。未知的角色、未知的键或错误的 effort 值，仍然会让 troy-check 以退出码 2 停下。

## 4. 分派请求

每次开始时，F07 先读 `product-manager.md`，运行 `status`，然后选择流程。

| 请求，例如 | 流程 | 所在章节 |
| --- | --- | --- |
| 在没有 `.troy-mode/` 的文件夹里的任何请求，或"开始一个项目 ……" | 项目初始化 | 第 10 节 |
| "下一个功能"、"F04"、"F04 到 F06"、"开始做 v0.1"、"v0.1 剩下的" | 功能循环 | 第 8 节 |
| "bug：……"、"修 #12" | 修 bug | 第 11.1 节 |
| "变更：……"、"导出也应该 ……" | 需求变更 | 第 11.2 节 |
| "为什么 ……"、"…… 是怎么工作的"、"试一下 ……" | 流水线之外的工作 | 第 11.3 节 |
| "继续"、"状态"，或什么都不写 | 接续 | 第 11.4 节 |
| "升级 troy-mode" | troy-init 的升级（F06 第 6 节） | 第 10 节 |
| "发布 v0.1" | 版本发布（5.5） | F08 设计 |
| "加一条规则 ……" | 规则变更（5.8） | F09 设计 |

- 在没有 `.troy-mode/` 的文件夹里，F07 回答问题，但不做任何改动。对其他请求，它问 Troy 一次，是否把这个文件夹变成 troy-mode 项目。
- 一个请求同时适合两个流程，或一个都不适合时，F07 问 Troy 一个问题，并给出推荐答案。
- **一个请求做到哪里（D63、D203）。** 一个功能、一个 bug 或一项变更，除非请求点名了更多，比如"F04 到 F06"。点名一个版本的功能循环请求，比如"开始做 v0.1"、"v0.1"或"v0.1 剩下的"，做到这个版本里所有还没验收的功能，按顺序（D203）。Troy 的批准仍在今天的位置让循环停下，Troy 批准之后，F07 在同一个范围里接着做。范围在这个版本发布之前结束，发布是单独的请求（"发布 v0.1"）。做完后 F07 报告并停下。
- **同一时间一个 PR。** 在一个工作副本里，F07 同一时间只处理一个 PR。新的请求要等这个 PR 合入，除非 Troy 说先暂停它。被暂停的 PR 恢复时，它的分支先变基到 `origin/main` 上。
- **开工许可。** 在 troy-mode 里，需求文档 3.3 中的各项批准，就是 Troy 的全局说明要求在写代码前取得的许可，F04 的共用规则第 4 条对角色也是这么说的。F07 不再为此另外询问。
- **报告。** F07 按原型 B 的样子向 Troy 报告每个阶段。

## 5. 状态（D58）

### 5.1 从哪里读取

| 内容 | 读取来源 |
| --- | --- |
| 初始化和语言包 | `origin/main` 上的 `.troy-mode/install.toml` |
| Troy 是否批准了需求文档和架构 | 它们在 `origin/main` 上的 `version`：1.0 或更高（F01 设计第 4 节） |
| 功能、依赖、顺序和版本 | `origin/main` 上的 `docs/requirements.md`：功能表、"Topological order"那一行和版本计划 |
| 一个功能已经合入了哪些阶段 | `origin/main` 上的 commit 标题，比如 `[F04 3/6 mock] ...`。R01 让每个标题等于它的 PR 标题（F03 D17），而 rebase、squash 和合并 commit 都会保留它。 |
| 开着的 PR 和它们的阶段 | `gh pr list` 给出的标题和分支 |
| 审查轮数、尝试次数，以及什么在等 Troy | F07 在每个开着的 PR 上自己发的评论（第 8.4 节）。尝试次数还来自 PR 推送过的提交的 CI 运行（第 8.5 节，D261）。 |
| PR 开出之前的尝试次数，以及 `status --note` 的各行 | 只在进度文件里 |
| 给后续功能的备注 | troy-mode 在进度 issue 上的 `Note for <ID>` 评论（第 6.6 节） |

- `status` 用依赖列检查顺序那一行：每个依赖都必须排在前面。不一致时，功能循环停下，并点出是哪些功能。修正它属于需求变更。
- 下一个功能，是顺序里第一个在 `origin/main` 上还没有 `accept` commit 的功能。
- commit 标题按历史顺序计算。一个阶段再次合入时，比如第 11.2 节的重做，这个功能在它之前合入的后续阶段不再算数。功能的当前阶段是它还没合入的最小阶段号；第 11.2 节跳过的 mock 算作已合入。
- bug 也从 commit 标题和开着的 PR 读出：`[B12 A/B test]` 已合入，说明接下来是 PR B；`[B12 B/B fix]` 已合入，说明这个 bug 已修好（第 11.1 节）。
- 同时开着多个 troy-mode PR 时，不是功能阶段的 PR，比如旁支 PR、bug 的 PR 或 `[docs]` PR，排在被它打断的阶段 PR 前面（第 8.7 节）。其余按编号从小到大。
- `status` 还把项目里的 troy-check（`.troy-mode/checks/`）和插件里的比较。项目的副本较旧时，它会说明 troy-init 的升级能把它更新。`[roles]`、`[flow]` 和 `troy-check code --worktree` 都需要新的副本（第 12 节）。

### 5.2 进度文件

- `.troy-mode/progress.md` 保存在本地、被 git 忽略（Q8）、只用英文（F01 D4），格式是 F01 的 `progress` 模板。
- 每一步之后，F07 都用 `status --write-progress` 重写它：每次角色运行、提交、推送、审查、合并和升级上报之后。
- 它不存在，或比第 5.1 节的状态旧时，`status` 用那份状态重新生成它。这样，即使在一个新的 clone 里，或在桌面应用刚建好、从来没有这个文件的 worktree 里，新会话也能接着做（5.10）。
- 丢了这个文件，丢掉的只有 PR 开出之前统计的尝试次数和备注。`status` 重新生成文件时会说明。

## 6. 运行角色

### 6.1 任务简报

`brief` 填写 F04 的任务简报字段（F04 设计 5.1）：

| 字段 | 来源 |
| --- | --- |
| Task | 任务 ID 和一句话，例如"DV1, write the mock of F04's interfaces"。 |
| Item | 功能或 bug 的 ID，以及 PR 标题。 |
| Read first | 按任务而定：`docs/rules.md`、这个功能在需求文档里的那一行、架构，以及已经有了的功能设计和测试方案，再加上它所依赖的功能的设计。 |
| Input | 用 `--input-file` 给出的文件：审查意见、一个回答、失败的检查，或 Troy 的一项决定。否则为 None。 |
| Round | 审查轮次，或 None。 |
| Checks to run | 在项目环境里运行的语言包步骤（F03 第 8.3 节和第 9.4 节）。对写代码和写测试的角色，再加上带 PR 标题的 `troy-check code --worktree`（D60）。 |

- IF1 的 Task 还说明第 4 节归架构师，并要求在那里写 "Not reviewed yet."。试运行里 IF1 把第 4 节的模板标记留给了架构师，于是在 AR2 填好这一节之前，`troy-check pr` 一直因 R20 不通过。
- 第一个 mock 时，DV1 的检查以需要代码的初始化步骤开头：Python 是 `uv pip install -e . --no-deps`，C/C++ 是 `cmake --preset coverage`（F06 设计 5.4）。
- 在 PR 3 和 PR 5，DV1、DV2 和 CR1 的 Task 加上第 6.4 节的固定 mock 说明文字（tstack #63）。
- 每个 CR1 的 Task 都根据第 6.5 节的检查，说明要不要运行 `/security-review`（tstack #75）。CR2 的任务简报用于一次发布的审查分支（F08 设计 5.9）。
- IF1、IF2 和 DV2 的 Input 加上之前的工作给这个功能留下的备注（第 6.6 节，tstack #67）。
- 命令通过 `mamba run -n <environment>` 运行；设置了 `TROY_MODE_ENV_PREFIX` 时，用 `mamba run -p <folder>`。试运行会设置它，这样不会留下有名字的环境。mamba 的查找方式和不带 `--mamba` 时的 troy-init 相同：先找 PATH，再找 `$MAMBA_EXE`（F06 设计 5.4）。`brief` 没有 `--mamba` 选项。
- 修改是同一个任务的一次新运行（设计的修改用 IF2），Input 里是审查意见，Round 是下一轮（F04 D33）。

### 6.2 同一时间只运行一个会写文件的角色

1. `snapshot --role <role>`。工作区里有 git 不忽略的改动时，以及某个角色的工作还在运行时（第 7 节问题 5），它会拒绝。F07 在每次会写文件的运行之后都会提交，所以下一次运行之前工作区是干净的。
2. Agent 调用：`subagent_type` 和 `brief` 给出的任务简报，`brief` 给出 `model` 和 `effort` 时也一并传入。
3. F07 等角色的报告，在此期间不在工作副本里做别的事，因为 F05 会把运行期间的每个改动都算到这个角色头上（F05 第 6 节）。只读的角色可以同时运行，比如测试经理和代码审查员审查同一个测试 PR（F04 第 9.2 节）。它们共用一个快照，而且不能有任何改动。通知说角色"is waiting on its own background work"时，这里也不变：报告就是最终结果，第 4 步会结束那项工作。
4. `check-run --run <run ID>`（第 7 节）。

### 6.3 根据报告行动

| 结果 | F07 做什么 |
| --- | --- |
| `done` | `check-run`、提交、本地检查、推送，然后进入这个阶段的审查（第 8.2 节）。 |
| `failed` | 记一次尝试（第 8.5 节）。把失败的检查放进 Input，再运行一次产出方；第三次之后升级上报。 |
| `approved` | 启动下一个审查方，或进入合并。 |
| `changes-requested` | 把审查意见交给产出方，作为下一轮再运行一次；第 3 轮之后升级上报（第 8.3 节）。 |
| `needs-answer` | 启动问题里点名的角色，问题作为 Input，然后带着回答再运行提问的角色。给 Troy 的问题交给 Troy。 |
| `escalate` | 升级上报（第 9 节）。 |
| 报告不符合 F04 的格式 | 再运行这个角色一次。第二次仍然如此，F07 升级上报。 |

角色要求用 `how`、`why` 或 `interrogate` 时，F07 照着那个技能的 `SKILL.md` 去做，把结果放进下一份任务简报的 Input（F04 共用规则第 9 条）。

### 6.4 mock 说明（tstack #63，D205 到 D207）

试点的七个 mock PR（ZJUCao/recipe-menu #36、#42、#55、#57、#67、#81 和 #88）里，代码审查员要求修改，原因是某条 mock 说明没有指向任何东西，或者说的和 mock 相反。"The mock leaves these checks out." 写在它所指的 Raises 一节前面，或者某个桩函数的文档注释说它会抛出或排序，而 mock 并不这样做。Troy 于 2026-11-16 接受了这条规则（ZJUCao/recipe-menu#94，AR6 选项 A）：由任务简报给出固定的句子，不加 R 规则，因为没有哪种架构、工具、troy-check 检查或工作流步骤能判断一条注释指向什么（理由见 tstack #63）。

**文字放在哪里。** `troyflow/mocknotes.py` 保存这些文字，按 `HEAD` 上配置里的 `[lang] name` 选择，就像 `summary.py` 保存给 Troy 的摘要那句话一样。`brief` 只在功能的阶段 PR 里把它加到 Task 行、任务本身那句话之后，返工时某个阶段的重做也算（第 11.2 节）。旁支 PR、bug、版本和规则都不加。

| 任务 | 阶段 | 加上的文字 |
| --- | --- | --- |
| DV1 | PR 3 | 注释的规则，带语言包的句子 |
| CR1 | PR 3 | 对注释的检查，带语言包的句子 |
| DV2 | PR 5 | 删掉注释 |
| CR1 | PR 5 | 检查没有留下注释 |

PR 4 的 CR1 和其他所有任务都不加文字。

**这些句子**（D205）：

| 位置 | Python | C/C++ |
| --- | --- | --- |
| 函数体只抛出异常的函数或方法 | `The mock raises ``NotImplementedError``.` | `The mock throws ``troy::NotImplemented``.` |
| 自己写了构造函数的类的文档注释 | `The mock's constructor raises ``NotImplementedError``.` | `The mock's constructor throws ``troy::NotImplemented``.` |
| 构造函数由语言生成（比如 dataclass），而设计要它检查参数的类 | `The mock leaves out the constructor's checks.` | 无：C++ 生成的构造函数不能做检查 |
| 同上，而且这个构造函数还会改动参数，比如排序 | `The mock keeps the values as given and leaves out the constructor's checks.` | 无 |

**DV1 的 Python 文字：**

> Where the mock does less than a doc comment says, add the mock's note as a paragraph of its own, after the description and before Args, Attributes, Returns, and Raises. Use these sentences word for word: `The mock raises ``NotImplementedError``.` for a function or method whose body only raises; `The mock's constructor raises ``NotImplementedError``.` in the doc comment of a class that writes its own constructor, besides the constructor's own note; `The mock leaves out the constructor's checks.` for a class whose constructor Python generates, such as a dataclass's, when the design has that constructor check its arguments, or `The mock keeps the values as given and leaves out the constructor's checks.` when it also changes them, for example by sorting; and, for a body that the design itself gives the mock, one sentence that says all it does, such as `The mock reads no file, writes nothing, raises nothing, and gives 0.` Every other body only raises, a constructor that the class writes too, and a generated constructor gets no `__post_init__`. A note never points elsewhere: no "these", "this", "above", or "below". The description and the sections describe the implementation as the design gives it, for example "The constructor checks its values, as Raises gives them.", so that PR 5 has only the notes to delete.

**DV1 的 C/C++ 文字：**

> Where the mock does less than a doc comment says, add the mock's note as a paragraph of its own, after the description and before Args, Attributes, Returns, and Raises. Use these sentences word for word: `The mock throws ``troy::NotImplemented``.` for a function or method whose body only throws; `The mock's constructor throws ``troy::NotImplemented``.` in the doc comment of a class that writes its own constructor, besides the constructor's own note; and, for a body that the design itself gives the mock, one sentence that says all it does, such as `The mock reads no file, writes nothing, throws nothing, and returns 0.` Every other body only throws, a constructor's too. A note never points elsewhere: no "these", "this", "above", or "below". The description and the sections describe the implementation as the design gives it, for example "The constructor checks its values, as Raises gives them.", so that PR 5 has only the notes to delete.

**PR 3 时 CR1 的 Python 文字：**

> Check the mock's notes. Every stub, and every class whose constructor does less in the mock than in the design, has one, as a paragraph of its own after the description. Each is one of these sentences, word for word: `The mock raises ``NotImplementedError``.` for a body that only raises; `The mock's constructor raises ``NotImplementedError``.` for a class that writes its own constructor; `The mock leaves out the constructor's checks.`, or `The mock keeps the values as given and leaves out the constructor's checks.` when the constructor also changes them, for a class whose constructor Python generates; or one sentence that says all that a body given by the design does. No other sentence says what only the mock does.

**PR 3 时 CR1 的 C/C++ 文字：**

> Check the mock's notes. Every stub, and every class whose constructor does less in the mock than in the design, has one, as a paragraph of its own after the description. Each is one of these sentences, word for word: `The mock throws ``troy::NotImplemented``.` for a body that only throws; `The mock's constructor throws ``troy::NotImplemented``.` for a class that writes its own constructor; or one sentence that says all that a body given by the design does. No other sentence says what only the mock does.

**DV2 的文字**（D207）：

> Delete every paragraph of the feature's doc comments that starts with "The mock". Change the rest of those doc comments only where a sentence is not true of the code you write.

**PR 5 时 CR1 的文字**（D207）：

> Check that no paragraph of the feature's doc comments starts with "The mock", and that every other change to those doc comments makes them true of the code.

DV2 和 PR 5 时 CR1 的文字两种语言相同。

**代理文件。** 开发工程师的 DV1 多一步：把任务简报给出的 mock 说明一字不差地加上。它的第 2 步补充：类自己写的构造函数也只表示未实现。它的 DV2 多一步：按任务简报删掉 mock 说明。各个标题不变，所以 `troy-mode/dev/tests/test_roles.py` 仍然通过。代码审查员的代理文件不改（D206）。

**不变的部分。** 规则模板、troy-check、F05 的钩子和 troy-init。引擎和代理文件从插件文件夹运行，所以这些文字随下一个插件版本到达每个项目，不需要 troy-init 的升级。recipe-menu 的 `main` 上已经没有 mock 说明，因为每个 PR 5 都把它们删掉了。处在 PR 3 和 PR 5 之间的功能保留它原来的注释：DV2 删掉以 "The mock" 开头的那些，PR 5 时的 CR1 抓住其余的。

**考试（F16 设计 7.2 和 9）。** `brief.py`、新的 `mocknotes.py` 和开发工程师的代理文件都属于指令集（F16 设计 9.1）。于是 `affected` 列出 dv-mock-notes（DV1）、dv-impl-notes（DV2）和 cr-mock-review（PR 3 时的 CR1）；cr-test-review 审查的是 PR 4，所以不受影响（D206）。构建 PR 写明 `Fixes case: dv-mock-notes`，这个用例的陷阱在 `main` 上是活的：在考试 2026-11-21-2 里它的基线通过了 5 次中的 2 次。另外两个用例不能变差。没有哪条记录下来的基线运行带着 `main` 的哈希，所以基线要重新运行。如果新版本没有达到目标，评分标准保持不变：会话报告数字，并提出一步爬坡（F16 设计 8.3），连同它的费用。

### 6.5 安全审查（tstack #75，F04 D280 到 D283）

原因见 F04 设计 6.8：试点里，代码审查员几乎在每个代码 PR 上都运行了 `/security-review`，一无所获。现在 `brief` 为 CR1 检查 PR 的 diff 里有没有四种迹象，并在 Task 里说明要不要运行 `/security-review`。

**diff。** 从 `origin/main` 和 `HEAD` 的合并基点到 `HEAD`，在 `brief` 读取的检出里；功能以团队方式运行时，就是团队的 worktree（F20 设计 3.11）。只看新增的行，而且只看源码文件和依赖文件：在子进程里运行程序的测试，并没有给程序本身增加什么。文件的类别取自 troy-check 的模式和 `HEAD` 上配置的 `[paths]` 表，和写入范围用的一样（F02 D9）。

**迹象。**

| 迹象 | 什么时候算 |
| --- | --- |
| 依赖 | `dependencies` 类的文件有改动。CMake 文件（`CMakeLists.txt` 或 `cmake/` 下的文件）里，只有新增的、指明一个包的行才算：`find_package`、`FetchContent_Declare`、`ExternalProject_Add`、`CPMAddPackage` 或 `pkg_check_modules`，因为 C/C++ 项目添加自己的文件时也要改 `CMakeLists.txt`。 |
| 子进程调用 | 源码文件新增的某一行启动了进程。Python：模块 `subprocess` 和 `pty`、`os.system`、`os.popen`，以及调用 `os.exec*`、`os.spawn*`、`os.posix_spawn*` 和 `asyncio.create_subprocess_*`。C/C++：`system`、`popen`、`_popen`、`exec*` 系列调用、`fork`、`vfork`、`posix_spawn`、`CreateProcess*`、`ShellExecute*` 和 `WinExec`，以及头文件 `<spawn.h>` 和 `boost/process`。 |
| 网络访问 | 源码文件新增的某一行导入了网络模块或包含了网络头文件。Python：`socket`、`ssl`、`http`、`urllib`、`urllib3`、`ftplib`、`smtplib`、`poplib`、`imaplib`、`xmlrpc`、`socketserver`、`webbrowser`、`requests`、`httpx`、`aiohttp`、`websockets`、`grpc` 和 `paramiko`，以及调用 `asyncio.open_connection` 和 `asyncio.start_server`。C/C++：`<sys/socket.h>`、`<netinet/*>`、`<arpa/inet.h>`、`<netdb.h>`、`<winsock2.h>`、`<ws2tcpip.h>`、`<curl/curl.h>`、`boost/asio` 和 `<asio.hpp>`，以及调用 `getaddrinfo` 和 `WSAStartup`。 |
| 凭据处理 | 源码文件新增的某一行导入了 `getpass`、`keyring`、`netrc` 或 `secrets`（Python），或者含有一个名字，其中包含 `password`、`passwd`、`passphrase`、`credential`、`secret`、`api_key`、`apikey`、`access_token`、`auth_token` 或 `private_key`，不分大小写。 |

`troyflow/risks.py` 保存这些列表，按 `HEAD` 上配置的 `[lang] name` 选择，就像 `mocknotes.py` 保存 mock 说明一样（第 6.4 节）。提到其中某项的注释或字符串也算：误报只多花一次审查，漏报则等发布时的审查。这个模块不认识的语言包，让每个 CR1 都做审查。它的那句话是 ``Run `/security-review` too, because troy-mode's check has no lists for the language pack <name>.`` troy-check 目前只接受 `python` 和 `cpp`，所以只有 troy-check 比这个模块先认识一个新语言包时，任务简报才会用到它。

**Task 的文字。** 在任务自己的句子之后，以及 PR 3 和 PR 5 的 mock 说明文字之后，CR1 的 Task 加上两句之一。检查发现迹象时：

> Run `/security-review` too, because the diff adds <signs>.

`<signs>` 列出发现的每种迹象，每种最多三个位置，写成 `path:line`，依赖文件只写路径，后面再加 "and <n> more"，例如 "a subprocess call (src/app/run.py:12) and network access (src/net/fetch.py:3, src/net/fetch.py:40)"。什么都没发现时：

> troy-mode's check finds no dependency, subprocess call, network access, or credential handling that the diff adds, so `/security-review` is not needed, unless you see one of those four that the check missed.

每份 CR1 任务简报都带其中一句：每个阶段的、旁支 PR 的、bug 各个 PR 的、版本测试 PR 的，以及规则清理 PR 的。其他任务都不带。

**CR2 的任务简报。** `brief --task CR2 --item <vX.Y>` 只在 F08 设计 5.9 的审查分支上运行：`HEAD` 必须是分支 `troy-mode/<vX.Y.Z>-security`，它唯一的 commit 带着 `origin/main` 的文件，父 commit 是前一个发布 commit 或第一个 commit。在别处运行时，它以一个问题停下，问题写明审查分支和哪里不对：别的分支或版本、不止一个 commit、文件和 `origin/main` 的不同，或者别的父 commit。Task 写作：

> CR2, review the security of <tag>: this branch's one commit holds every change since <the previous tag, or "the first commit">. Run `/security-review` on it, judge each finding, and change no file.

Read first 含 `docs/rules.md`、带这个版本各行的 `docs/requirements.md`，以及 `docs/architecture.md`。Checks to run 为 None。

### 6.6 给后续功能的备注（tstack #67，D284 到 D287）

在 `ZJUCao/recipe-menu` 上的 F11 试点里，前面功能的审查给后面的功能留下了备注：F11 和 F13 应当从 F06 的模块里拿什么，F12 必须按相等而不是按同一性分组，以及 F09 和 F10 速度目标的计时模型。`status --note` 只在功能和阶段都不变时才保留一条备注（第 5.2 节），而进度文件是从 git 和 GitHub 重建的视图（D58），所以 troy-mode 没有地方保存它们。试点的主会话把它们存在自己为这个项目文件夹准备的记忆文件里，到 2026-11-15 已有几十条，再一条条手工复制进对应的 IF1 或 DV2 任务简报。换一台电脑上的会话，或者没有那份记忆的会话，就丢了这些备注，也没有什么检查每条备注是否送到了它的任务简报。

**备注存在哪里（D284）。** 一条备注是 troy-mode 在一个进度 issue（F15 设计第 4 节）上的评论，所以它和其余状态一起存在 GitHub 上（D58）：

```markdown
Note for F12, from #57, Code Reviewer, round 1

F12 groups recipes by equality of their names, not by identity: F06's loader makes a new
object for each file, so two files that hold the same recipe give two objects.
```

- 第一行是标题 `Note for <feature ID>, from <source>`，F15 设计 8.4 把它加进 troy-mode 的评论标题。来源是 PR、角色和轮次，或者 `Troy, in chat`。下面的正文用英文，因为是角色来读。
- 它发在产生它的那项工作所属功能的进度 issue 上，比如审查 F06 的某个 PR 时产生的备注就发在 F06 的 issue 上。来自聊天的备注，或者来自功能之外的工作（比如 bug 或发布的 PR）的备注，目标功能有进度 issue 时发在那里，否则发在下一个功能的 issue 上，下一个功能总有一个（F15 设计 4.1）。
- troy-mode 从不删除进度 issue，因为 F05 的守卫拒绝 `gh issue delete`（F15 设计 10.2），关闭的 issue 也保留评论。`status` 本来就读取每个 issue（开着的和关闭的）及其评论（F15 设计 3.3），所以在那里找备注不多花一次调用。
- 备注可以指向产生它的功能本身（给它后面的阶段），或者任何还没验收的后续功能。给已验收功能的备注是需求变更（D65），所以 `note` 拒绝它，并给出说明原因的问题。

**记下一条备注（D285）。** 每条备注都由主会话记下。它本来就读每个角色的报告（第 6.3 节）：报告里说某个后续功能、或这个功能后面的阶段必须采纳什么时，主会话用自己的话按上面的格式写下备注，再运行 `note --for <ID> --from <source> --file <text file>`。Troy 在聊天里给的备注走同样的路。`note` 检查功能，选定 issue，把评论文件写到 `<git dir>/troy-mode/flow/notes/` 下，并给出 `gh issue comment <n> --body-file <file>` 命令。技能用 `check-text` 检查这个文件，再运行命令，和每次往 issue 上发内容一样（F15 设计 3.4）。没有角色的报告格式改变，所以不会因此改动任何代理文件，也不会改动技能里属于 F16 指令集的任何一节。

**哪些任务简报拿到备注（D286）。** `brief` 把一个功能的备注加进这个功能每次 IF1、IF2 和 DV2 运行的 Input：每个阶段的第一次运行和之后的每一轮，更新设计的 `[docs]` 旁支 PR（第 8.7 节），以及返工时某个阶段的重做（第 11.2 节）。它用一次 `gh` 调用读遍进度 issue，留下标题指向这个功能的备注，按时间先后排列。在 Input 文件的文字之后（没有 Input 文件时就作为整个 Input），它加上：

```text
Notes for F12 from earlier work, kept on its progress issues:
1. From #57, Code Reviewer, round 1 (<link to the comment>):
   <the note's text>
2. From Troy, in chat (<link>):
   <the note's text>
```

以及按任务不同的一句话。IF1 和 IF2："Take each note into the design where it applies, and say in your report which ones you did not take, and why." DV2："Where a note differs from the approved design, follow the design and say so in your report."

- 功能没有备注时，任务简报和今天完全一样。仓库的 `origin` 不在 GitHub 上时（比如角色考试的临时项目）也一样：那里没有进度 issue 可读，`brief` 不调用 `gh`。
- `origin` 在 GitHub 上、而 `gh` 读不了 issue 时，`brief` 以一个问题停下，退出码 1，不给任务简报：悄悄丢掉备注的任务简报，就是试点的问题又出现了。等 `gh` 能用了，主会话再运行一次。`status` 也需要 `gh`，所以没有它流程本来也走不下去（F15 设计第 9 节）。
- 其他任务都不拿备注。试点的备注都送到了设计和实现，测试经理读的是已经采纳了备注的设计。

**迟到的备注（D287）。** `status` 增加 `notes`：对每个还没验收、有备注的功能，给出每条备注的 issue、评论链接、来源、时间，以及它还能送到哪里。在功能的 PR 1 开出之前记下的备注，能送到设计和实现。PR 1 开出之后记下的，对设计来说是 `late`；PR 5 开出之后记下的，对实现来说也是 `late`：`brief` 仍会把它加进之后每次 IF2 和 DV2 运行，但没有再运行就被批准的阶段看不到它。对每条迟到的备注，`status` 在它的 notes 里加一行，由主会话决定，并在给 Troy 的报告里说明：用 IF2 在 `[docs]` 旁支 PR 里更新设计（第 8.7 节）、把备注作为开着的 PR 下一轮的 Input，或者在已合入的工作已经做到备注要求时什么都不做。无论怎样，备注都留在它的 issue 上。

**功能团队（F20）。** 备注存在 GitHub 上，不在任何检出里，所以它适合 F20 的团队：

- **送到对的团队的任务简报。** 团队的任务简报 `brief --repo <worktree>` 在团队的 worktree 里通过 `gh` 读取备注，这个 worktree 和仓库共用远端，它只留下这个团队的功能的备注。每个团队的 IF1、IF2 和 DV2 拿到的备注，和在主检出里拿到的一样。
- **`team end` 之后。** `team end` 删除 worktree 和它的 git 文件夹（F20 设计 3.1）。那里没有任何备注：每条备注都是进度 issue 上的一条评论，而功能的进度 issue 在验收之后还在。F08 的团队给 F10 留下的备注，在 F10 的团队之后开始时仍然送得到。
- **谁来记下。** 只有主会话和 GitHub 打交道（F04 D29），每个团队的报告都交到它那里，所以任何团队的审查里发现的备注，都由主会话在自己的检出里记下，发在这个团队的功能的进度 issue 上。两个团队给同一个功能留备注，就是两条评论，按时间先后读取。
- **等待。** 给正在运行的团队的功能的迟到备注不会让任何东西停下。`status` 把它和那个团队一起列出，主会话按上面的办法决定。

**进度 issue。** 功能有备注、并且它的 issue 已经存在时，目标功能的进度 issue 增加一行："备注：2 条（#31、#40）"，英文部分是 "Notes from earlier work: 2 (#31, #40)"，每个编号链接到它的评论（F15 设计 4.2）。这样 Troy 在手机上就能看到每个功能有哪些备注在等它。

**构建确定的细节。** `status` 的列表用键 `feature_notes`，因为报告里的 `notes` 已经用来放消息；每一项给出功能和它的备注，每条备注带 `issue`、`url`、`source`、`created` 和 `late`。一个阶段 PR 的开出时间是它各个 PR 中最早的 `createdAt`，关闭的也算，所以 PR 列表现在读取 `createdAt`；恰好在那个时间记下的备注不算迟到。`note` 的报告给出 `issue`、`file` 和 `gh`，最后一项是把文件路径按 shell 加好引号的命令。`origin` 是否在 GitHub 上，看它配置的 URL `remote.origin.url`，在任何 `insteadOf` 改写之前，所以 SSH 形式的 URL 也算。`gh` 报告仓库关闭了 issue 时，视为没有备注，而不是问题。`notes.py` 自己运行 `gh`，不经过 `github.py`，所以 `github.py` 不进入 F16 的指令集。

**不变的部分。** `status --note` 的作用不变：进度文件 Open issues 里的一行，功能和阶段都不变时保留（第 5.2 节）。代理文件、`common.md`、模板，以及技能的"Running a role"和"The summary for Troy"两节都不变。技能增加一节"Notes for later features"，说明什么时候记下备注，它的"One stage"一节指向那里。

**考试（F16 设计第 9 节）。** `brief.py` 和它新增的模块 `troyflow/notes.py` 都属于 F16 的指令集（F16 设计 9.1），所以构建会改变指令哈希。`brief` 导入的每个模块都会加入指令集，所以 `notes.py` 尽量少导入。`affected` 在 `origin` 是本地文件夹的临时项目里渲染每个用例的任务简报，所以没有任务简报会多出备注，预期结果是"没有受影响的用例"，不花钱。如果 `affected` 还是列出了某个用例，构建就停下并报告。按 troy_exam 的预算代码，IF1 和 DV2 的用例 if-example-format、if-error-rules 和 dv-impl-notes，第一轮要 $79.74，加上第二轮共 $159.47，超过 F16 的 $60 线，所以那样的考试要等 Troy（F16 D158）。没有 F16 用例测试备注：试点里的错误是主会话的，不是某个角色的（F16 设计第 3 节）。

## 7. 每次运行之后的检查（D59）

`snapshot` 把 `HEAD`、分支和时间记在 `<git dir>/troy-mode/flow/<run ID>.json` 里。因为工作区原本是干净的，运行之后 `git status` 列出的每个改动都是这次运行做的。`check-run` 找这些问题：

1. **`HEAD` 或分支变了。** 角色不能提交，也不能切换分支（F05 第 7 节），所以这说明 hook 失效了。F07 立即停下并升级上报。
2. **改动的路径在角色的写入范围之外**（F04 第 3 节）。检查用 F05 的写入范围表、troy-check 的路径类别和 `HEAD` 上的配置。被忽略的路径不算。对代码审查员，任何改动都是问题。
3. **AR2 之后，设计在第 4 节之外有改动**（F04 D37）。`check-run` 把设计和它的镜像与 `HEAD` 逐节比较。
4. **改了 `dependencies` 路径，却没有用 `--allow-dependency` 点名。** F07 只点名 Troy 已经接受的依赖（R16、5.7、第 8.7 节）。
5. **角色，或者它启动的命令，还在运行**（F05 设计第 6.1 节，D231）。这次运行的角色在快照之后生成的某份记录未关闭：角色还没有停止，或者它的某条命令被 Claude Code 转到后台、可能还在运行。这个问题的类别是 `running`，报告的 `stop` 列出每个这样的代理 ID。F07 用 `TaskStop` 逐一结束它们，然后再运行一次 `check-run`。结束角色会结束它的命令，并且不唤醒它。过期的记录，即被用量上限或关闭的会话结束的角色留下的，也这样清除：对已不在运行的 ID 调用 `TaskStop` 会失败，但 hook 已经关闭了记录。这个问题不算一次尝试，也没有撤销步骤：命令结束前改动的东西属于这次运行，下一次 `check-run` 像检查别的改动一样检查它。如果代理的权限拒绝 `TaskStop`，F07 告诉 Troy 要停掉哪个代理，然后等待。

只要任何角色的记录未关闭，不论属于哪次运行，`snapshot` 都以同样的 `running` 问题拒绝；F07 用同样的方式结束列出的每个代理，再重新拍快照。

`check-run` 还会列出快照之后这个角色在 `hooks.log` 里的记录（F05 第 10 节）。这些记录本身不会让流程停下。`background` 行说明角色停止时还有命令在运行，问题 5 会点到同一个代理。

主会话以产品经理身份工作时，F07 用 `--role product-manager` 拍快照，并用这个范围检查结果（F04 第 3 节）。这样主会话自己写的文档也留在产品经理的范围之内（F05 第 4 节）。

遇到第 2、3、4 类问题时，F07 撤销报告列出的改动：已跟踪的文件用 `git restore`，这次运行新建的文件直接删除。快照时工作区是干净的，所以撤销只会丢掉这次运行自己的改动。然后 F07 再运行这个角色一次，Input 里写明这些路径和它的写入范围。同一阶段第二次出现问题时升级上报。没有问题时，F07 只暂存 `check-run` 列出的那些路径。

## 8. 功能循环（5.2）

### 8.1 阶段

| PR | 标题 | 产出方 | 审查方 | 每次推送前的本地检查 | 由谁合并 |
| --- | --- | --- | --- | --- | --- |
| 1 | `[F04 1/6 design] <name>` | IF1，每次修改用 IF2 | AR2 | `troy-check pr` | 前几个功能由 Troy 合并（D61、D62），其余由 F07 |
| 2 | `[F04 2/6 test-plan] <name>` | TM1，问题由 IF3 回答 | 无。接口设计师的回答就是双方的一致意见，提问最多 3 轮。 | `troy-check pr` | 同 PR 1 |
| 3 | `[F04 3/6 mock] <name>` | DV1 | CR1 | `troy-check pr`、语言包的步骤和 `troy-check code` | F07 |
| 4 | `[F04 4/6 tests] <name>` | TE1 | TM2 和 CR1，同时进行 | 同 PR 3。`troy-check code` 检查 R09。 | F07 |
| 5 | `[F04 5/6 impl] <name>` | DV2 | CR1 | 同 PR 3；功能有性能目标时，再在 Troy 的电脑上运行它的性能用例（5.6、Q7）。`troy-check code` 检查 R10 和 R11。 | F07 |
| 6 | `[F04 6/6 accept] <name>` | PM3，在主会话里 | 无 | `troy-check pr` | F07 |

`<name>` 是这个功能在需求文档里的名称。分支是从 `troy-mode/f04-1-design` 到 `troy-mode/f04-6-accept`。名称必须简短，例如 "Export history as CSV"，因为它会成为每个 PR 的标题和功能文件夹的名字。试运行里产品经理在 Feature 单元格里写了一整句话，文件夹路径超过了 Windows 的路径长度上限，普通的 `git add` 因此失败。技能要求产品经理在这个单元格里只写简短的名称。

### 8.2 一个阶段的步骤

1. **顺序。** 前一个阶段已经合入 `origin/main`，而且这个功能的每个硬依赖都已经验收。F02 第 11 节把阶段顺序留给了 F07。
2. **分支。** `git fetch origin --prune`，然后 `git switch -c <branch> origin/main`。F07 从不检出 `main`。在桌面应用建的 worktree 里，`main` 常常已经在另一个 worktree 里检出，git 不允许同一个分支检出两次。
3. **产出方。** 一次角色运行（第 6 节）和它之后的检查（第 7 节）。
4. **提交。** 用 `git add -- <path>` 暂存 `check-run` 列出的那些路径，不多不少。第一次运行生成 commit，它的标题就是 PR 标题（R01）。之后的运行修订（amend）这个 commit，所以 PR 始终只有一个 commit。F05 的 `commit-msg` hook 检查 R19。
5. **本地检查。** 在这个 commit 上运行表里的检查。失败时，结果作为 Input 交回产出方，并记一次尝试。
6. **PR。** `git push --force-with-lease -u origin <branch>`。第一次推送后运行 `gh pr create --base main --head <branch>`，带上标题和按 PR 模板写的说明：Why（这个功能的目标）、What（这个阶段的产出及其 ID）、Checks（运行了什么、结果如何）和 Soft-limit reason（取自开发工程师的报告，或 None）。之后的推送用 `gh pr edit` 更新说明。
7. **审查。** 每个审查方在这个 PR 上运行，F07 把它的报告作为评论发出（第 8.4 节）。AR2 还会写设计的第 4 节，所以 F07 在它之后也像对产出方一样检查并修订 commit。`changes-requested` 把审查意见交给产出方，作为下一轮。
8. **合并**（第 8.6 节）。

### 8.3 轮数（R17）

一轮是这个阶段的审查方在 PR 上的一次运行。在 PR 4 上，任何一个审查方给出 `changes-requested`，这一轮就不通过。第 3 轮仍然是 `changes-requested` 时，F07 升级上报。对 PR 2，一轮是向接口设计师提出的一个问题和它的回答，测试方案的对齐记录会记下每一轮（F01 设计 5.4）。F07 根据自己发的评论统计轮数，所以新会话能接着上一个会话停下的地方继续计数。

### 8.4 评论

F07 把每次审查、每次失败的尝试、每次升级上报，以及每次请 Troy 处理的事，都作为 PR 评论发出，开头是固定的标题行：

- `Architect review, round 2: changes-requested`，后面是审查意见；
- `Developer attempt 2: failed`，后面是失败的检查。CI 失败时，标题行下面第一行是 `Commit: <commit ID>`，即失败的那个推送提交（第 8.5 节，D261）；
- `Escalation: <trigger>`，后面是第 9 节的消息；
- `Waiting for Troy: approve this PR`。

GitHub 不允许一个账号批准自己的 PR，而每个角色都通过 Troy 的账号工作，所以由标题行记录是谁做了什么（F04 D29）。没有这些标题行的评论是 Troy 写的。F07 读取 Troy 在开着的 PR 上的评论，把它们作为 Input 交给产出方。F07 发出自己的每条评论之前，都先用 `check-text` 检查。

### 8.5 尝试次数（D64）

一次尝试，是产出方的一次运行报告了 `failed`，或者报告了 `done` 但 F07 的本地检查失败，或者导致 CI 在产出方的文件上失败。每个阶段允许 3 次尝试。第三次之后，F07 升级上报（5.7）。检查通过的修改算一轮，不算尝试。

**从 CI 统计尝试（D261 到 D263）。** 评论可能漏发：试点中，CI 有四次推送在界面设计师的文件上失败，ZJUCao/recipe-menu#52 两次、#59 两次，却只发了一条尝试评论，所以复盘只看到 1 次失败的尝试（tstack issue #73）。因此 `status` 还读取每个开着的 PR 的 CI 运行，`retro` 读取这个版本每个已合并 PR 的 CI 运行（F08 第 7 节）：

- **运行。** `status` 用 `gh run list --branch <branch> --event pull_request --limit 100 --json databaseId,headBranch,headSha,status,conclusion,createdAt,updatedAt,workflowName` 列出 PR 头分支的工作流运行。`retro` 用一次调用列出这个版本各 PR 的运行：用 `--created <date>..*`（GitHub 表示"当天或之后"的写法，不需要 `>`）加最早那个 PR 的创建日期代替 `--branch`，并用 `--limit 1000`；返回了 1,000 个运行时，它会说明更早的运行可能缺失。一个 PR 只保留它的头分支上在 PR 开出时或之后创建的运行，已合并或已关闭的 PR 还要在合并或关闭时或之前创建，这样后来又用同一个分支名的 PR 的运行不会混进来（D261）。
- **每个推送提交最多一次尝试（D261）。** 运行按头提交分组。每个工作流只算它在这个提交上最新的那次运行，和 `wait-checks` 一样：改了 PR 说明而重新开始的运行，或者失败后重跑并通过的作业，只留下较新的结果。其中有一次运行的结论是 `failure` 时，这个提交算失败。运行被取消或仍在运行的提交不算。
- **在产出方的文件上（D262）。** 对每个失败的运行，`gh run view <run ID> --json jobs` 给出失败的步骤。在仓库文件上运行检查的步骤失败了，就算产出方的：troy-check 作业里的 `Run troy-check`（F02 第 8 节），以及语言包作业（F03）里 `Install from the lock` 之后的每个步骤：Python 是 `Lint and format`、`Types`、`Tests`、`Coverage report` 和 `Run troy-check code`，C/C++ 是 `Configure and build`、`Format and lint changed files`、`Tests`、`Coverage report`、`Doc comments` 和 `Run troy-check code`。PR 里只有这个阶段的工作，放在检查已通过的 `main` 上，所以检查在这里失败，就是在产出方的文件上失败。其他步骤的失败都不在产出方的文件上：检出（试点里 ZJUCao/recipe-menu#87 的 "Repository not found"）、`Look for code`、环境安装、`Install from the lock`、GitHub 自己的步骤、被取消或超时的步骤，以及 troy-mode 没有写的工作流的每个作业。这样的失败不算尝试。如果它在 PR 最新的提交上，F07 停下并告诉 Troy（第 8.6 节）。
- **已经算过的（D261）。** 尝试评论算它的 `Commit:` 行点名的那个失败提交，7 到 40 位十六进制，按前缀匹配。没有这一行的评论，比如本地检查的评论，或者这次改动之前发的评论，算它发出时 PR 最新的推送提交：前提是那个提交当时已经在产出方的文件上失败（它失败的运行的 `updatedAt` 不晚于这条评论），而且没有别的评论算过它。先匹配所有 `Commit:` 行，再按从旧到新处理其他评论。最新的推送提交，是第一次运行开始得最晚的那个，因为推送之后几秒内运行就会开始。
- **次数。** 一个 PR 的尝试次数，是它的尝试评论里最大的编号，加上每个在产出方文件上失败、又没有评论算过的提交。每个这样的提交按推送的顺序依次取下一个编号。
- **漏发的评论（D263）。** `status` 在 `ci_failures` 里按从旧到新给出每个开着的 PR 的失败提交：`commit`、`runs`、`steps`（每项写作 `<job> / <step>`）、`author`（失败在产出方的文件上）、`counted`（有评论算过它），以及 `attempt`，即还没算过的产出方失败要取的编号，否则为 null。F07 继续之前，为每个带 `attempt` 的失败发出 `<Role> attempt <n>: failed`，用这个编号，加上 `Commit: <commit ID>` 一行和失败的步骤，这样 PR 上能看到每次尝试，次数也保持不变。角色是这个阶段的产出方，按 `next.task` 从 PR 标题得出。`retro` 什么也不发：它只统计（F08 第 7 节）。
- **gh 列不出运行时，** `status` 加一条说明，像以前一样只从评论统计。

### 8.6 合并（R18、F02 D14）

只有以下各项都成立时，F07 才合并 PR：

- 这个阶段的每个审查都以 `approved` 结束；
- 推送的 commit 通过了本地检查，或者只在本平台跳过的测试上失败（D69，见下）；
- 用 F07 推送的完整提交 ID 运行 `wait-checks --pr <n> --sha <sha>`（D204），结果是 `passed`：这个头提交的每项检查都已登记并结束，并且每项都通过；
- 合并权限允许。顺序里前 `troy_approves_first` 个功能的 PR 1 和 PR 2 要等 Troy（D61、D62）。其他 PR 都由 F07 合并。

然后 F07 运行 `git switch --detach`、`gh pr merge <n> --rebase --delete-branch --match-head-commit <sha>`、`git fetch origin --prune` 和 `status --write-progress`。先 detach，是为了让 `gh` 在删除分支之前不去检出 `main`。每次 fetch 都带 prune：PR 合入之后，同一个分支名可能再用一次，比如更新测试方案时的 `troy-mode/v0.1-test-plan`，而过时的 `origin/<branch>` 会让 `git push --force-with-lease` 拒绝新分支（F08 试运行时发现）。这些命令各自单独运行，在 F07 读过等待的退出码之后：合并永远不和等待写在同一行命令里，不管是用 `;` 还是别的方式连起来（D204）。

**等检查（D204）。** `wait-checks` 每隔 `--interval` 秒（15）读一次 `gh pr view <n> --json headRefOid,state,statusCheckRollup`，看这几件事：
- **头提交。** PR 的头提交还是别的提交时，继续等，因为刚推送后 GitHub 可能还没更新。PR 已合并或已关闭时，以 `closed` 结束。
- **还没有检查。** 刚推送后 GitHub 可能还没登记工作流，汇总是空的。这仍然是在等，绝不算通过（试点的 ZJUCao/recipe-menu#47）。
- **检查。** 头提交的每个 check run 和提交状态。同一个头提交上一个工作流运行了不止一次时，比如 `gh pr edit` 改了 PR 说明之后，每项检查只算最新的那次运行：还没开始的那次（没有 `startedAt`，或者是 gh 的零时间 `0001-01-01T00:00:00Z`），否则是最晚开始的那次。check run 的结论是 `SUCCESS`、`NEUTRAL` 或 `SKIPPED` 时算通过；状态是 `SUCCESS` 时算通过。还在排队或运行的算未完成；其他的都算失败。
- **稳定。** `passed` 要求两次读取都看到每项检查已结束并通过，两次至少相隔 `--settle` 秒（30），而且检查相同，这样稍晚登记的工作流不会漏掉。
- **结果。** `passed` 的退出码是 0。其他每个结果的退出码都是 1，并带一条问题：每项检查都结束、但有一项失败时是 `failed`，失败的检查在 `failed` 里，它们的运行 ID 在 `runs` 里，用于 `gh run view <id> --log-failed`；`--timeout`（540 秒，在一次 Bash 调用最多的十分钟以内）先到时是 `pending`，一项检查都没报告时写 "No check has reported"；头提交仍是别的提交时是 `other-head`；还有 `closed`。遇到 `pending`，F07 再运行一次，这仍是同一次等待；第二次运行仍然没有检查时，F07 停下并告诉 Troy。失败的 gh 调用在下一次读取时重试；连续失败三次时退出码为 2。

- **只在另一个平台上运行的测试（D69）。** 测试方案的某个用例可能只在一个平台上运行，比如试运行里的 F01-T17（不可读的文件），它在 Linux 上运行，在 Windows 上跳过。troy-check 把跳过的测试既不算失败（R09），也不算通过（R10），所以 Troy 电脑上的本地 `troy-check code` 不通过，而 CI 在 Ubuntu 上运行了这个测试。`check-skips` 说明本地的失败只有这类跳过的测试时，本地检查算作通过：不记尝试，PR 说明的 Checks 一节把这些用例列为只由 CI 检查，F07 按 CI 的结果合并，CI 通过就证明这些测试运行过。测试方案必须写明这个用例为什么只在一个平台上运行，由 TM2 和 CR1 检查。产出方的任务简报也这样说明，所以产出方会报告这个跳过，而不是因它失败。
- **CI 检查失败。** F07 运行 `status`，在这个 PR 的 `ci_failures` 里读推送的那个提交（第 8.5 节）。`author` 为 true 时，这次运行记一次尝试：F07 用 `attempt` 里的编号和 `Commit:` 行发出它的评论，再把失败的日志（`gh run view --log-failed`）作为 Input 交给产出方。`author` 为 false 时，失败不在产出方的文件上，比如在工作流里或在运行器上：F07 停下并告诉 Troy。
- **合并被拒绝。** 如果 Claude Code 的权限拒绝了 `gh pr merge`，F07 停下，并告诉 Troy 需要加哪条权限。它从不绕过拒绝。

**Troy 的批准（D61）。** PR 要等 Troy 时，F07 发出 `Waiting for Troy`，在聊天里把链接告诉 Troy，然后停下。Troy 可以在聊天里回复，也可以在 GitHub 上合并这个 PR。

- 收到表示批准的回复时，F07 对这个 PR 的文档运行 `approve`：`version` 升到下一个主版本（F01 设计第 4 节），`updated` 改为当天日期，状态改为"Approved by Troy on <date>"及其中文形式。`approve` 只改两种语言文件头里的这几个字段，并在修改记录里加一行“Troy 批准。”（F08 D77），所以不需要运行角色。这一对文件里任何一个没有修改记录表格时，`approve` 什么都不改，以退出码 1 结束，并指出是哪个文件（D201）：文档的作者在一次新的运行里补上表格，输入里带上这条问题，然后 F07 再运行一次 `approve`。F07 修订 commit、推送、等检查，然后合并。
- **架构的 ADR（D202）。** 文档是架构时，`approve` 同时接受架构的决策记录表列出、仍处于提议状态的 ADR，所以改它们的状态字不需要再运行架构师。ADR 的状态一节第一行以 "Proposed"（中文为 "提议中"、"已提议"、"提议" 或 "Proposed"）开头时，就是提议状态。对每条这样的 ADR，`approve` 在两种语言里都像对架构一样改文件头（ADR 没有修改记录，所以不加修改记录行），并把状态行写成 "Accepted. Troy accepted it on <date> by approving `docs/architecture.md`."（中文 "已接受。Troy 于 <date> 批准 `docs/architecture.md`，接受了这条记录。"），保留原来那个词后面的文字。架构表格里这一行的状态单元格改为 "Accepted"（"已接受"）。列出的 ADR 在 `docs/adr/` 下不是恰好有一个英文文件加上它的镜像、各带 troy-doc 文件头，或者两个文件的版本不同时，`approve` 以退出码 1 结束，什么都不写。报告的 `changed` 列出每个文件，`adrs` 列出接受了的编号。
- 收到要求修改的回复时，产出方修改，算作一轮。
- Troy 在 GitHub 上合并时，文档的版本仍低于 1.0。F07 随后开出并合并 `[docs] Record Troy's approval of <document>`，里面只有 `approve` 做的改动。

需求文档和架构也走同样的步骤（第 10 节）。

**前几个功能之后（D62）。** 顺序里前 `troy_approves_first` 个功能中的最后一个验收后，F07 问 Troy 一次，是否继续由 Troy 批准 PR 1 和 PR 2。一个 `[rules] Set the features Troy approves` PR 把回答记进 `[flow] troy_approves_first`，由 F07 合并。

### 8.7 旁支 PR（第 2 部分）

旁支 PR 会打断一个阶段。F07 先完成旁支 PR，把这个阶段的分支变基到 `origin/main` 上，再运行一次这个阶段的产出方。

| 情况 | 流程 | PR |
| --- | --- | --- |
| 有争议的测试（5.2） | DV2 报告 `needs-answer`，问题交给测试经理，由 TM4 裁定。 | 测试错了：`[F04 test-fix] <summary>`，由 TE3 修改，TM2 和 CR1 审查。代码错了：带着裁定再运行 DV2。 |
| 覆盖率缺口（5.2） | R11 不通过，由 TM3 给未覆盖的代码分类。 | 没有用处的代码：在同一个 PR 里由 DV4 删除。漏掉的用例：测试经理在一个 `[docs]` PR 里补上，再由 TE4 在一个 `[F04 test-fix]` PR 里写测试。设计里没有的行为：IF4 裁定，然后是一个 `[docs]` 设计更新和测试，或者 DV4。无法测试的代码：写明理由后排除，由 TM6 批准。 |
| 新依赖（R16） | 角色报告 `needs-answer`，问题交给架构师。AR3 审查后升级上报，并给出建议。 | Troy 接受：AR3 在一个 `[docs]` PR 里把它和一份 ADR 记进架构。产出方再运行一次，`check-run` 放行那个依赖文件。然后处理系列锁文件（D66）。Troy 拒绝：产出方不用它再运行一次。 |

**系列锁文件（D66）。** 锁文件改动时，F07 用 troy-init 的函数（F06 设计 5.4），从每个成员的清单编译系列锁文件，装进共享环境，并在合并之前在那里运行每个成员的测试（F03 设计 8.1）。PR 说明列出锁文件因此过期的成员。F07 不在它们那里开 PR。

第二部分这样运行这些情况：

- **谁写旁支 PR。** 裁定不改任何文件：TM3、TM4、TM6、IF4，以及 AR3 的审查。测试经理用 TM1 补上漏掉的用例；接口设计师用 IF2 写设计更新，由 AR2 审查；Troy 接受之后，架构师在 AR3 的第二次运行里写依赖的 ADR。这些运行都用 `brief --title` 带上各自 PR 的标题，这样它们的检查对应正确的 PR。
- **标题和分支。** 测试修正是 `[F04 test-fix] <summary>`，分支 `troy-mode/f04-test-fix`。`[docs]` 旁支 PR 的标题写明它加了什么，比如 `[docs] Add cases to the F04 test plan`，分支 `troy-mode/f04-docs`。bug 的旁支 PR 同样使用 bug ID。
- **系列锁文件。** `series` 列出编译和安装锁文件、运行每个成员测试的命令，以及锁文件因此过期的成员。F07 在 `check-run` 放行的产出方运行之后执行它们，并把新的锁文件和产出方的文件一起暂存。
- **顺序。** 旁支 PR 开着时，`status` 先接着做它，再回到被它打断的阶段 PR（第 5.1 节）。

### 8.8 角色运行和费用（D264 到 D267）

试点中，v0.1 按 API 标价花了 1,092 美元：263 次角色运行、74 个辅助代理和主会话，而估计是 130 到 235 美元。直到发布之后写报告时才有人看到，因为 troy-mode 没有哪一步报告费用（tstack issue #74）。所以验收 PR（PR 6）和发布 PR（F08 第 5.7 节）报告它们的功能或版本的角色运行和 token 费用，由 `costs` 从 Troy 电脑上 Claude Code 的会话记录里读出：

- **会话记录在哪里（D264）。** Claude Code 把每个会话存为 `<config>/projects/<folder>/` 里的 `<session ID>.jsonl`。`<config>` 是 `$CLAUDE_CONFIG_DIR`，或者主目录下的 `.claude`；`<folder>` 是会话的工作文件夹，把 ASCII 字母和数字以外的每个字符都换成 `-`：`D:\Troy\Projects\recipe-menu` 得到 `D--Troy-Projects-recipe-menu`。子代理的记录是 `<session ID>/subagents/agent-<agent ID>.jsonl`，旁边是 `agent-<agent ID>.meta.json`，它的 `agentType` 用 `<plugin>:troy-<role>` 写出角色，`parentAgentId` 写出启动辅助代理的那个代理。`costs` 读取主检出的文件夹、`git worktree list` 给出的每个工作树的文件夹，以及名字是主检出的文件夹名后接 `--claude-worktrees-` 的每个文件夹：这是桌面应用的工作树，工作树删掉之后它们的记录还在。给出一次或多次 `--transcripts` 时，改读它指定的文件夹。它从不往那里写。
- **哪些运行属于一个条目。** 一次角色运行属于它的任务简报点名的条目，即它的记录第一条消息里的 `Item: <ID>, <title>` 一行（第 6.1 节），不管它在哪个会话里运行。`--item <ID>` 汇总这个条目的每次运行、这些运行启动的辅助代理，以及主会话从这个条目第一次运行开始到结束之间的消息：结束是功能的 `accept` commit 合入 `origin/main` 之后的那个时间，否则是 `costs` 运行的时间，或者 `--until`。不是角色、也不是由角色启动的代理，比如主会话启动的一次搜索，在同一段时间里算作主会话的其他代理。功能的主会话费用也包含这段时间里它做的其他事，比如另一个功能的旁支 PR。
- **一个版本。** `--tag <vX.Y.Z>` 汇总从 `origin/main` 上前一个 `[docs] Release` commit（任何更早的标签都算），没有时从项目的第一份会话记录开始，到这个标签的发布 commit 合入之后，否则到 `costs` 运行的时间或 `--until` 为止的一切：这段时间里开始的每次角色运行、辅助代理、其他代理和主会话的消息。`items` 按条目给出角色运行的费用。
- **token 费用。** 每条助手消息只算一次：会话记录为一条消息的每个内容块重复写一条记录，用量相同，所以按消息的 ID 区分记录。它的费用是输入、输出、缓存读取、5 分钟缓存写入和 1 小时缓存写入的 token，以及网页搜索，按它的模型的标价计算（D265）；`speed` 为 `fast` 时按这个模型的快速价格。价格表里没有的模型，连同它的 token 列在 `unpriced` 里，绝不猜测；这时总数写作"至少"。Claude Code 自己的、不留助手记录的调用，比如压缩时的摘要，不计入。试点中，这样算出的每个角色的费用和试点报告的数字分毫不差。
- **会话和电脑。** 跨多个会话的功能会把所有会话加起来。在另一台电脑上的运行，记录留在那台电脑上，所以报告写明只读了这台电脑，并列出读过的每个会话。用 `--item` 时，它点名这个功能已合入 `origin/main`、但在这里没找到角色运行的第 1 到 5 阶段（它不调用 gh，所以不检查开着的阶段）；用 `--tag` 时，点名版本里一次运行都没找到的每个功能。
- **桌面应用自己的数字（D266）。** 桌面应用会往会话记录里写 `cost-state` 记录：应用启动以来按模型的累计费用，以及背后的 token 数。`costs` 用自己的价格表给最新一条记录的 token 数定价，某个模型的数字和应用的相差超过 1% 时加一条说明：这说明价格表过时了。
- **报告。** JSON 里有：`roles`（每个角色的 `runs`、`models` 和 `cost`）、`helpers`、`others`、`main`、`total`、`items`、`window`、`prices`（价格表的 `as_of`）、`sessions`、`unpriced`、`missing` 和 `notes`。`description` 是 PR 说明里的 `## Cost` 一节：一句话写明条目、价格的日期、时间段和"这台电脑的会话记录"，然后是一张表，每个角色、辅助代理、有其他代理时的其他代理、主会话和总计各占一行，再为每条说明写一行。`line` 是给 Troy 的报告用的一句话。两者都不用 ID 写模型，也不含路径，因为 R19 的严格模式拒绝两者都含有的那个完整单词：模型写成系列和版本，比如"Opus 5.5"。只要能读取，`costs` 的退出码就是 0，没找到任何记录时也是，这时那一节就这样写明。
- **PR 6。** 验收 PR 最后一次推送之前，F07 运行 `costs --item <ID>`，把它的 `description` 放在"Real run"一节之后。合并之后给 Troy 的报告加上它的 `line`，用 Troy 的语言。
- **给 Troy 的摘要（D267）**不带费用：它出现在 PR 1、PR 2、需求文档和架构的 PR 开头（F14 设计），而一个功能的费用要到验收时才知道。

**价格表（D265）。** `troy-mode/flow/prices.toml` 放在插件里、引擎旁边，存着以美元计、每百万 token 的标价。`as_of` 是从 Anthropic 价格页读取这些价格的日期，`web_search` 是一次网页搜索的价格。每个 `[models."<model ID>"]` 表有 `input`、`output`、`cache_read`、`cache_write_5m` 和 `cache_write_1h`，有快速模式的模型还有一个键相同的 `fast` 表。标价变了或有新模型时，由一个 tstack PR 更新它，并提升插件版本（F10 D89）。第一份价格表截至 2026-11-03，含当前的 Opus、Sonnet、Haiku 和 Fable 模型；试点的 `cost-state` 记录分毫不差地证实了其中 Opus 5.5、Sonnet 5.5 和 Haiku 5.5 的价格。

## 9. 升级上报（5.7）

| 触发条件 | F07 怎样发现 |
| --- | --- |
| 审查循环到了 3 轮仍未达成一致 | 它统计的轮数（第 8.3 节） |
| 一项改动需要修改需求文档或架构 | 某个角色的 `escalate` 报告，或 AR5 的回答 |
| 产出方 3 次尝试后仍然失败 | 它统计的尝试次数（第 8.5 节、D64） |
| 需要新的第三方依赖 | AR3 的 `escalate` 报告（第 8.7 节） |
| 合并权限之外的不可逆操作 | F07 在动手之前检查。它的权限是：用 `--force-with-lease` 推送自己的分支；开出、编辑、评论、关闭和在 R18 之内合并自己的 PR；开 bug issue；在 PR 合入之后删除自己的分支；在 Troy 验收一个版本之后，在发布 PR 的合并 commit 上创建它的 GitHub release（F08 第 5.7 节）。其他任何操作都要问 Troy。 |
| 一次运行改了 `HEAD` 或分支，或者第二次越出写入范围 | `check-run`（第 7 节） |

消息按 F01 的 `escalation` 模板、用 Troy 使用的语言写：在哪里停下、为什么、带链接的事实、各个选项，以及一个建议（原型 C）。F07 还会用英文把它发到开着的 PR 上，在进度文件里写上"Waiting on Troy"，然后停下。还没有开着的 PR 时，如果有 bug 的 issue，F07 就发到那个 issue 上：第二部分的试运行里，开发工程师在 PR B 出现之前就请求了一个依赖，升级上报发在了 issue 上。Troy 回答之后，无论是在这个会话里还是在新会话里，F07 都把这个决定放进下一份任务简报的 Input，继续往下做。

## 10. 项目初始化（5.1）

1. **初始化。** 文件夹里没有 `.troy-mode/` 而 Troy 同意时，F07 运行 troy-init 引擎的 `setup` 和 F06 第 7 节的 PR 流程，并问 F06 的那些问题：是否创建 GitHub 仓库，以及是否替换不是 troy-init 写的文件。那个流程的第 8 步在这里按第 8.6 节做：合并之前先 detach，之后 `git fetch origin`。
2. **需求文档。** 在初始化的 PR 合入之后进行，这样 troy-check 也会检查需求文档（F06 第 10 节）。主会话以产品经理身份工作（PM1），并拍快照。PR 是 `[docs] Add the requirements`，Troy 按第 8.6 节批准。
3. **架构。** AR1，然后是 `[docs] Add the architecture`，用同样的方式批准。请 Troy 批准架构的那条消息，同时问语言步骤的问题：这个项目属于哪个系列。
4. **语言步骤。** troy-init 引擎的 `lang` 加上 PR 流程。引擎在 `main` 上的每一步都会停下，连试运行也是，所以 F07 在试运行之前先创建分支 `troy-mode/lang-<name>`（F06 设计 1.2）。语言取自架构的技术栈。
5. **下一步。** F07 报告；只有请求里要求了，才接着做第一个功能（D63）。

已经完成了其中几步的项目，从第一个缺少的步骤接着做。**升级**也这样运行：在试运行之前建好分支，再运行引擎的 `upgrade`。没有要改的东西时，F07 再把这个分支删掉。

## 11. 其他流程

### 11.1 修 bug（5.3，第 2 部分）

1. Troy 在聊天里报告一个 bug，或者给出一个 issue。没有 issue 时，F07 开一个带 `bug` 标签的 issue，它的编号就是 bug ID（F01 D3）。
2. TM5 对它分类。误解了需求的情况转入变更流程。
3. PR A，`[B12 A/B test] <summary>`：TE2，由 TM2 和 CR1 审查。`troy-check code` 检查 B12 的测试会失败（R09）。
4. PR B，`[B12 B/B fix] <summary>`：DV3，由 CR1 审查。`troy-check code` 检查 B12 的测试通过。说明里写"Fixes #12"，所以 F07 合并这个 PR 时，GitHub 会关闭 issue。

分支是 `troy-mode/b12-test` 和 `troy-mode/b12-fix`。PR B 的标题沿用 PR A 的摘要；PR A 合入之后，`status` 把 PR B 作为下一步，所以新的会话也能把这个 bug 做完。TM5 不改任何文件。DV3 对某个测试有争议时，由 TM4 裁定，TE3 在 `[B12 test-fix]` 里修正它，和第 8.7 节对功能的做法一样。

### 11.2 需求变更（5.4，第 2 部分，D65）

1. **PM2。** 产品经理在一个 `[docs] Change the requirements: <summary>` PR 里更新需求文档。Troy 批准它（第 8.6 节），受影响的功能变为"需要返工"。
2. **AR4。** 架构师列出要改的接口、测试和架构的部分，架构的改动要有 ADR。
3. **还没有验收的功能**回到 AR4 点出的最早阶段。如果这个功能有开着的 PR，F07 不合并就关闭它，然后从那个阶段重新运行循环。
4. **已经验收的功能**为这项变更新增一个功能，由 PM2 加入，它硬依赖旧功能。新功能的设计在第 3 节列出改动的接口。它的测试方案点出这项变更要淘汰的旧用例，并把它们记进旧功能测试方案的"不测试"一节。它的测试 PR 删除这些测试，加上新的用例，新用例在当前代码上会失败（R09）。它的 mock PR 只包含新接口；没有新接口时，F07 跳过 PR 3。troy-check 不需要改，因为旧功能剩下的每个测试仍然通过。

和每个 PR 一样，所有已有测试都作为回归测试运行（5.6）。

第二部分这样把这些状态保存在 git 里（D58）：

- **需要返工。** PM2 在状态列里把每个受影响、还没验收的功能标为"Needs rework (<这项变更>)"。已经验收的功能保持原来的状态，由新功能那一行写明这项变更。一个功能的状态这样写着、而且在最新的 `[docs] Change the requirements:` commit 之后它的阶段都还没再合入时，它处于返工中。这时 `status` 要求运行 AR4，在新的会话里也一样。
- **重做。** 重做的 PR 用这个阶段平常的标题；功能处于返工中时，带这个标题的 `brief --title` 接受当前阶段之前的阶段。重做合入之后，它后面的阶段不再算数（第 5.1 节），循环从那里继续。变更之前开出、分支里没有变更 commit 的阶段 PR，会让 `status` 先要求 AR4，再继续它。功能的实现已经合入、而测试要改时，重做最晚从阶段 3 开始：R09 要求这个功能的每个测试在 mock 上失败。
- **跳过的 mock。** "没有新接口"指新功能已合入的设计第 2 节里没有接口小节。这时 `status` 和 `brief` 从 PR 2 直接到 PR 4。
- **Troy 的批准。** 变更 PR 和需求文档一样要等 Troy（第 8.6 节）。`approve` 把需求文档升到下一个主版本。Troy 改在 GitHub 上合并时，它的版本仍带着次版本号，`status` 会要求 `[docs] Record Troy's approval of docs/requirements.md`。

### 11.3 流水线之外的工作（5.9）

F07 在主会话里回答问题、做调查，合适时照着 `how` 或 `why` 去做，不启动角色。试验在从 `origin/main` 建出的临时分支 `troy-mode/try-<slug>` 上进行，或在一个临时文件夹里进行。F07 从不推送它，也不从它开 PR。值得保留的代码要走需求变更和功能循环。

### 11.4 接续（5.10）

F07 运行 `status`，报告项目进行到了哪里。有事在等 Troy 时，它说明是什么事。否则它接着做下一步。

## 12. 对之前功能的改动

- **troy-check（F02、F03）。**
  - 配置读取接受带 `model` 和 `effort` 的 `[roles.<role>]`，以及带 `troy_approves_first` 的 `[flow]`，后者是 0 或更大的整数（第 3.2 节）。`config.default.toml` 用注释说明这两张表。
  - `troy-check code` 增加 `--worktree`（D60）。它把工作区当作已经提交来检查：在工作区之外用一个临时索引构造一个 commit 对象，以 `HEAD` 为父 commit，再把这个 commit 当作 `--head` 来检查。它不移动任何 ref，也不改动索引和工作区。它只写入没有任何 ref 指向的 git 对象。
  - F02 和 F03 的设计各增加一行修改记录。项目通过 troy-init 的升级得到这两项改动。
- **F05 的 hook** 通过 troy-check 的配置读取来读配置，所以不用自己改动就能接受新表。
- **troy-init 的技能（F06）。** 它的 PR 流程第 8 步在合并之前先 detach，最后用 `git fetch origin`，代替 `git switch main` 和 `git pull`，这样 troy-init 在 worktree 里也能用。F06 的设计增加一行修改记录。
- **F04** 不变。`--worktree` 通过任务简报里的检查传给角色。

F07 不给项目的工作流添加步骤。它的测试在 troy-pstack 的 `troy-checks-tests.yml` 里用默认 shell 运行。用 `shell: bash -leo pipefail` 的步骤绝不能调用 `exit`，因为在运行器上 `~/.bash_logout` 会把 `exit 0` 变成 1（F06 第 2 部分时发现）。

## 13. F07 与需求的对应

| 需求 | F07 在哪里覆盖它 |
| --- | --- |
| F07 一行：把每个请求分到一个流程（5.1 到 5.10） | 第 4 节 |
| F07 一行：运行功能循环 | 第 8 节 |
| F07 一行：在角色之间传递审查意见 | 第 6.3 节、第 8.2 节和第 8.4 节 |
| F07 一行：升级上报 | 第 9 节 |
| F07 一行：执行合并权限 | 第 8.6 节 |
| F07 一行：维护进度文件 | 第 5.2 节 |
| F07 一行和 F04 D32：模型和 effort 取自 `[roles]` | 第 3.2 节 |
| F07 一行和 F04 D31：每次运行之后的检查 | 第 7 节 |
| 3.3：Troy 参与的环节 | 第 8.6 节、第 9 节和第 10 节 |
| 5.1 项目初始化 | 第 10 节 |
| 5.3 修 bug 和 5.4 需求变更 | 第 11.1 节和第 11.2 节 |
| 5.6 测试什么时候运行 | 第 8.1 节的本地检查，以及每个 PR 上的 CI |
| 5.9 流水线之外的工作和 5.10 接续 | 第 11.3 节、第 11.4 节和第 5 节 |
| R01、R02、R17、R18、R19、R21 | R01、R02 和 R21：第 8.2 节。R17：第 8.3 节。R18：第 8.6 节。R19：第 8.2 节和第 8.4 节 |
| F02 第 11 节：阶段顺序 | 第 8.2 节第 1 步 |
| F03 设计 8.1：依赖改动后系列的锁文件和测试 | 第 8.7 节 |
| F05 第 12 节：同一时间一个会写文件的角色、每次运行之后的检查、hook 日志和 `troy-check code` | 第 6.2 节、第 7 节和第 12 节（D60） |
| F06 第 10 节：运行 troy-init 的引擎、初始化之后才写需求文档、DV1 的初始化步骤 | 第 10 节和第 6.1 节 |
| 第 8 节：新技能只在 Troy 输入时运行 | 第 2 节 |

## 14. F07 怎样检查

### 14.1 测试

测试用 `unittest` 和标准库。由另一个代理在引擎写出来之前，根据这份设计来写。每个测试建一个临时 git 仓库，用 `git clone --bare` 做一个本地裸仓库作 `origin`，所以没有测试会推送 `main`。`PATH` 上有一个假的 `gh`，它从一个 JSON 文件提供 PR 和评论，并记录每次调用。测试放在 `troy-mode/flow/tests/`。凡是改动 `troy-mode/flow/`、`skills/troy-mode/`、`troy-mode/checks/` 或 `troy-mode/hooks/` 的 PR，`troy-checks-tests.yml` 都在 Linux 和 Windows 上运行它们。

| 分组 | 用例包括 |
| --- | --- |
| 状态 | 从 rebase、squash（带 ` (#41)`）和合并 commit 的标题读出阶段。开着的 PR。下一个功能。违反依赖的顺序行。`troy_approves_first` 为 0、为 3 和超过这个数时的合并权限。从评论统计轮数和尝试次数，并区分出 Troy 的评论。项目里的 troy-check 副本比插件的旧。 |
| 进度 | F01 模板的字段，英文，没有标记。不存在时重新生成，并附上说明。 |
| 任务简报 | F04 的六个字段。按任务决定的 Read first。Python 和 C/C++ 的语言包步骤，产出方的 `--worktree`，只在第一个 mock 时出现的 DV1 初始化步骤，以及 `TROY_MODE_ENV_PREFIX`。模型和 effort 取自 `HEAD` 上而不是工作区里的 `[roles]`，没有设置时不传。 |
| 快照和检查 | 工作区不干净时拒绝拍快照。每个角色在范围之内的改动都通过。问题：每个角色在范围之外的改动、代码审查员的任何改动、AR2 改了第 4 节以外的内容、没有 `--allow-dependency` 的依赖路径，以及 `HEAD` 或分支变了。被忽略的路径和已放行的依赖通过。撤销步骤。只列出快照之后这个角色的 `hooks.log` 记录。产品经理的范围。 |
| 批准和文字 | `approve` 把两种语言都升到下一个主版本，并写好两条状态行。任何一个文件没有修改记录表格时，它以退出码 1 结束，什么都不写（D201）。对架构，它在两种语言里接受列出的、处于提议状态的 ADR，连同它们在架构表格里的行，其他的不动；列出的 ADR 缺少任何一个文件时拒绝（D202）。严格模式下 `check-text` 拒绝署名。 |
| troy-check | 接受 `[roles]` 和 `[flow]`。拒绝未知的角色、未知的键、错误的 effort 值和负数。`--worktree` 能看到新文件、跳过被忽略的文件、结果和真实 commit 相同，而且索引、ref 和工作区都保持原样。 |
| 技能 | front matter 有 `name: troy-mode` 和 `disable-model-invocation: true`。它点到第 4 节的每个流程、每个引擎命令，以及第 8.1 节的阶段标题。它的路由把点名一个版本的请求，比如 "Start v0.1"，交给这个版本剩下的功能，不包括发布（D203）。 |
| 第 2 部分 | 从 commit 标题和开着的 PR 读出 bug，以及作为下一步的 PR B。旁支 PR 排在阶段 PR 前面。阶段的重做，以及需要 AR4 的返工。跳过的 mock。Troy 合并的变更 PR，以及记录它的批准。每个第二部分任务的任务简报，按阶段、bug 步骤和标题。`check-skips` 在只有跳过的测试失败、以及有其他失败时的结果。`series` 的命令和过期的成员。 |
| 运行中的工作（F05 D231） | 这次运行的角色有未关闭的记录，不论是未停止，还是已停止但 `background` 里还有任务，`check-run` 都给出 `running` 问题，`stop` 里是代理 ID，退出码 1，`escalate` 为 false，没有要暂存的，也没有对应的撤销。已关闭的记录、别的角色的记录、快照之前生成的记录都不给出问题。有任何未关闭的记录时，`snapshot` 以同样的问题拒绝；工作区也不干净时两个问题都给出。没有新字段的记录算作已关闭。技能的"Running a role"一节提到 `running`、`TaskStop` 和再运行一次 `check-run`，并且不要求角色在前台运行。 |
| 从 CI 统计尝试（D261 到 D263） | 在检查步骤上失败的提交只算一次，不管它有几个运行或作业失败。每个工作流在一个提交上只算最新的运行：较新的通过运行会抵消较早的失败。被取消和正在运行的运行不算。同一分支在 PR 开出之前或合并之后的运行不计入。检出、环境安装、`Install from the lock` 或 troy-mode 没有写的工作流里的失败不算尝试，`author` 为 false。评论的 `Commit:` 行，不管是完整的还是 7 位前缀，都算它点名的提交。没有这一行的评论算它发出时最新的推送提交，前提是那个提交的失败已经结束，并且没有别的评论算过它。次数是评论里最大的编号加上每个没算过的提交，按推送顺序编号。`ci_failures` 给出每个失败的提交和它的 `attempt`。`gh run list` 失败时加一条说明，只统计评论。技能的合并步骤带着 `Commit:` 行补发漏掉的评论。 |
| 角色运行和费用（D264 到 D267） | 由 Windows 路径和桌面工作树路径得出的文件夹名，以及 `$CLAUDE_CONFIG_DIR`。由 `agentType` 得出角色，由 `parentAgentId` 得出辅助代理，以及其他代理。一条消息重复的记录只算一次。用一张测试价格表给每种 token、网页搜索和快速模式定价；表里没有的模型列在 `unpriced` 里。用 `Item:` 行把两个会话里的运行对到条目上。`--item` 的时间从第一次运行到 `accept` commit，合入之前到现在；`--tag` 的时间从任何标签的前一个发布 commit 开始；`--until`。时间段之外的主会话消息不计入。没找到运行的阶段列在 `missing` 里。`cost-state` 的数字相差超过 1% 时有说明，在 1% 以内没有。`description` 和 `line` 含有这些数字，不含模型 ID，也不含路径。没找到记录：退出码 0，那一节写明这一点。技能的 PR 6 步骤写出 `costs` 和这一节。 |
| 等检查（D204） | 起初没有检查，之后通过；稍晚登记的第二个工作流；一项失败，在每项检查都结束后才报告，带上运行 ID；同一项检查较早的失败运行和较新的通过运行；提交状态；`SKIPPED` 和 `NEUTRAL`；别的头提交；已合并的 PR；超时；gh 失败一次和三次。技能的合并步骤写出 `wait-checks`，永远不用 `;` 把合并接在后面。 |
| mock 说明（D205 到 D207） | 在 `test_mock_notes_brief.py` 里，仿照 `test_summary_brief.py`：Python 项目和 C/C++ 项目里 DV1 的 Task 行，DV2 的，以及 PR 3 和 PR 5 时 CR1 的，都恰好含一次第 6.4 节里它的文字，带语言包的句子，从不带另一种语言的。返工时 PR 3 的重做含 DV1 的文字。PR 4 时的 CR1、测试修复旁支 PR 里的 CR1、bug PR 里的 CR1 和 DV3，以及其他任务，都不含。 |
| 安全审查（F04 D280 到 D283） | 在 `test_security_brief.py` 里：Python 和 C/C++ 的每种迹象，出现在源码文件新增的行里，带它的位置；删掉的行、上下文行和测试文件里的行都不算；依赖文件给出它的迹象，CMake 文件只在有指明包的行时才算；每种最多三个位置，再加 "and <n> more"；什么都没发现时给出"不需要"的那句；每份 CR1 任务简报恰有一句，位于 mock 说明文字之后，其他任务的都没有；模块不认识的语言包要求审查；diff 从合并基点算起，团队的 worktree 里也一样。审查分支上的 CR2 任务简报，带它的标签和基点；不在审查分支上时给出问题。代码审查员的代理文件有 CR2，它的 CR1 步骤只按任务简报或角色自己看到的迹象运行 `/security-review`。 |
| 给后续功能的备注（D284 到 D287） | 在 `test_notes.py` 里，用假的 `gh`：`note` 先选来源功能的进度 issue，再选目标功能的，再选下一个功能的；拒绝已验收的功能、不认识的功能，以及关闭了 issue 的仓库；写出标题和正文，给出命令。`brief` 只把它自己功能的备注加进 IF1、IF2 和 DV2，按时间先后，带链接，覆盖每个阶段的第一次运行、之后的一轮、`[docs]` 旁支 PR 和返工时的重做，放在 Input 文件的文字之后或作为整个 Input，带上每个任务的那句话；其他任务都拿不到；关闭的进度 issue 上的备注也算；没有备注的任务简报，以及 `origin` 不在 GitHub 上的任务简报，都和今天一样，也不调用 `gh`；`gh` 失败时任务简报以问题停下；团队的任务简报从它的 worktree 读取备注。`status` 给出 `notes`，PR 1 或 PR 5 开出之后记下的备注标为迟到。 |

### 14.2 埋 bug

代码通过之后，在一份临时副本里一次埋一个 bug，每个都必须让某个测试失败。这些 bug 包括：从 PR 标题而不是 `origin/main` 读阶段、不检查顺序行、F07 合并了第三个功能的 PR 2、`troy_approves_first` 差一、从所有评论统计轮数、从工作区读 `[roles]`、没有设置时也传 effort、`snapshot` 接受不干净的工作区、开发工程师的范围包含 `tests` 类别、允许 AR2 改整份设计、没有 `--allow-dependency` 也放行依赖改动、报告了其他角色的日志记录、`approve` 只升英文文件，以及 `--worktree` 在索引里留下暂存的文件。第二部分的包括：PR A 合入之前就给出 PR B、阶段 PR 排在它的旁支 PR 前面、重做之后后续阶段仍算数、第 2 节有接口时也跳过 mock、代码任务没有 `--worktree`、已修好的 bug 也给出任务简报、`check-skips` 放过了不是跳过的失败，以及漏掉成员过期的锁文件。D201 加上：在 `approve`、`accept-version` 和 `rule-row` 里，保留退出码 0 加说明、还没检查英文文件的表格就先写了镜像、只检查英文文件。D202 加上：接受了的 ADR 在镜像里仍是提议状态、它的文件头没改、已经接受的 ADR 又被升版本、架构表格的单元格没改、接受了架构没有列出的 ADR，以及拒绝了某条 ADR 却仍写了架构。D204 加上：没有检查算作通过、未完成的检查算作已结束、不比较头提交、算上一项检查较早的运行、不等稳定、把 `SKIPPED` 算作失败、忽略提交状态、还有检查没结束就报告失败、忽略超时，以及一次 gh 调用失败就结束等待。F05 的 D231 再加上：未停止的记录算作已关闭、算上快照之前的记录、有未关闭的记录时 `snapshot` 仍然通过、`running` 设置了 `escalate`，以及给 `running` 问题加上撤销步骤。D261 到 D263 加上：按每个失败的运行而不是每个提交计数、一个工作流较早的运行和较新的一起算、被取消的运行算作失败、保留了 PR 开出之前的运行、检出失败算作产出方的、忽略 `Commit:` 行、没有这一行的评论算了一个在它发出之后才失败的提交、一条评论算了两个提交、把 CI 次数加在评论条数上而不是最大编号上，以及 `gh run list` 失败让 `status` 停下。D264 到 D267 加上：一条消息重复的记录又算一次、1 小时缓存写入按 5 分钟的定价、快速模式按标准定价、没有价格的模型悄悄按零计算、辅助代理算作一次独立的角色运行、算上了另一个条目的运行、算上了结束之后的主会话消息、没读工作树的文件夹、说明里出现模型 ID，以及有任何差别就给出价格说明。D205 到 D207 再加上：PR 4 时的 CR1 拿到 PR 3 的文字、测试修复旁支 PR 里的 CR1 拿到 PR 5 的文字、PR 3 时的 CR1 拿到 PR 5 的文字、C/C++ 的任务简报里出现 Python 的句子，以及 PR 3 的重做没有文字。F04 的 D280 到 D283 加上：删掉的行被算作迹象、测试文件里的子进程调用被算进去、添加项目自己文件的 CMake 行被算作依赖、Python 项目用了 C/C++ 的列表、diff 从 `origin/main` 而不是从合并基点算起、bug 的 CR1 任务简报里漏了那句，以及在审查分支之外给出 CR2 的任务简报。D284 到 D287 加上：别的功能的备注被加进任务简报、TM1 的任务简报里加了备注、关闭的进度 issue 上的备注被跳过、`gh` 失败被当作没有备注、对 `origin` 不在 GitHub 上的仓库调用了 `gh`、PR 1 开出之后记下的备注没有标为迟到、`note` 接受已验收的功能，以及备注顺序错乱。数量写进 PR 说明。

### 14.3 试运行（D68）

每一部分的 PR 开出之前，F07 在 Troy 电脑上的嵌套 `claude -p` 会话里运行，troy-pstack 通过 `--plugin-dir` 从 PR 分支加载，用的是私有临时仓库 `ZJUCao/troy-mode-trial`。这个仓库里已经有 F06 试运行留下的初始化、1.0 版的架构和 Python 语言包。环境通过 `TROY_MODE_ENV_PREFIX` 放在一个临时前缀下，Troy 的回答由试运行的提示给出。这些会话会访问 GitHub，所以只有 Troy 在聊天里同意之后才开始试运行，否则 Claude Code 的自动模式会拒绝它们。

第 1 部分：

1. **升级和角色配置。** troy-init 的升级通过它自己的 PR 把新的 troy-check 带进试运行仓库。然后一个事先准备好的 `[rules]` PR 在 `[roles]` 里给一个角色设置 `effort`。
2. **troy-mode 之外。** 在一个空文件夹里的请求，会提出初始化，但不做任何改动。
3. **需求文档。** "开始这个项目：统计文本文件里的词数。" PM1 写出包含两个小功能的需求文档。Troy 在聊天里批准后，F07 合并它。
4. **中断。** "下一个功能"开出第一个功能的 PR 1，它要等 Troy。那个会话结束。
5. **接续。** 在一个新 clone 的 git worktree 里、没有进度文件的新会话，收到"继续"和 Troy 的批准。它从 GitHub 重建状态，合并 PR 1，再把这个功能从 PR 2 做到 PR 6，CI 全绿。
6. **分派。** "发布 v0.1"和"加一条规则"会说明流程还没有实现。"为什么 ……"会得到回答，不建分支，也不开 PR。
7. **事实。** 从会话记录里确认：Agent 调用带着 `[roles]` 里的模型和 effort；F07 等每个会写文件的角色运行完；`gh pr merge --delete-branch` 在 detach 的 worktree 里能用；以及 Claude Code 在 `-p` 模式下的权限是否放行 `gh pr merge`。如果某个事实和这份设计不同，就在同一个 PR 里更新设计。

第 2 部分运行一个 bug 的 PR A 和 PR B；一项涉及已验收功能的需求变更，做到新功能的 PR 1 和 PR 2；以及一个被 Troy 拒绝的依赖请求。第 1 部分大约运行 12 次角色，第 2 部分大约 14 次，每个 PR 另外用几分钟 Actions 时间。仓库保留。是否删除由 Troy 决定。

### 14.4 状态

| 时间点 | 需求文档 7.2 中 F07 的状态 |
| --- | --- |
| 第 1 部分在试运行通过后合入 | 在示例项目上跑通，2 部分中的第 1 部分：troy-mode 为一个临时 GitHub 项目写了需求文档，并跨过一次会话中断，把一个功能的六个 PR 做完，CI 全绿。修 bug、需求变更和循环的旁支 PR 还没有实现。 |
| 第 2 部分在试运行通过后合入 | 在示例项目上跑通：同第 1 部分，另外跑通了一次修 bug 和一次需求变更。还没有在真实项目上用过。 |
| 试点（F11）用 troy-mode 运行 | 在真实项目上用过 |

如果某一部分的试运行没能在它的 PR 之前完成，状态就是"已编写，2 部分中的第 n 部分"，直到试运行完成。F07 分两个 PR 合入（D67），每个只有一个 commit，测试都先写：

1. **第 1 部分。** 引擎、第 12 节对 troy-check 和 troy-init 的改动，以及包含请求分派、项目初始化、功能循环主线、流水线之外的工作和接续的技能。
2. **第 2 部分。** 旁支 PR 和系列锁文件（第 8.7 节）、修 bug 和需求变更。

每次状态更新都单独开一个 PR。

第 6.4 节的 mock 说明在它的构建通过角色考试并合入后，给 F07 的状态加一句：它们在试点状态的临时副本上通过了角色考试，还没有在真实项目上运行过。这次更新也单独开一个 PR。

**从 CI 统计尝试（D261 到 D263）。** 构建 PR 开出之前，在临时文件夹里新克隆一份 `ZJUCao/recipe-menu`，运行 `retro --tag v0.1.0`，gh 只读 GitHub。它必须把 #52 和 #59 的四次失败推送算作界面设计师的尝试，其中 #59 的那条评论算掉其中一次，并且 #87 的检出失败不算尝试。然后构建 PR 在需求文档 7.2 里 F07 的状态加一句话：尝试次数也从 CI 运行统计，已在试点的 PR 上检查过，还没有在项目运行时用过。这次改动的状态在构建 PR 里更新，而不是单独开 PR，因为每项检查都在构建 PR 开出之前运行。

**角色运行和费用（D264 到 D267）。** 构建 PR 开出之前，在新克隆的 `ZJUCao/recipe-menu` 上运行 `costs`，用 `--transcripts` 指定试点的会话记录文件夹，它只读这个文件夹。`costs --tag v0.1.0 --until 2026-11-16T10:40:00Z`（试点报告统计的截止时间）必须给出那份报告第 5.2 节的表：每个角色的运行次数相同，每个角色的费用相差不超过 1 美元。然后构建 PR 在 F07 和 F08 的状态各加一句话：费用报告已在试点的会话记录上检查过，还没有在项目运行时用过。和 D261 到 D263 一样，状态在构建 PR 里更新。

**给后续功能的备注（D284 到 D287）。** 构建 PR 开出之前，在 `ZJUCao/troy-mode-trial` 上按 Troy 对那里试运行的长期许可做一次简短试运行：给一个还没开始的功能记下一条备注，再分别从一个团队的 worktree 和主检出渲染它的 IF1 任务简报，检查两份都带着这条备注。它不运行任何角色。试运行在 2026-11-24 进行：在 `ZJUCao/troy-mode-trial`（功能已全部验收）的本地克隆里，只在本地的 `origin/main` 加了一个虚设的功能 F99。`note --for F99 --from "#74, Code Reviewer, round 1"` 选中了 F06 已关闭的进度 issue #64，这条评论作为标明是试运行的备注发在那里；F99 的 IF1 任务简报，无论从主检出还是从 `.troy-teams/f99` 渲染，都带着它；`status` 列出了它，`late` 为空。在 Windows 上，这个克隆需要 `core.longpaths`。构建合入之后，它的状态 PR 在需求文档 7.2 里 F07 和 F15 的状态各加一句：给后续功能的备注保存在进度 issue 上，并送到那些功能的设计和实现的任务简报里，已由测试和试运行检查，还没有在真实项目上用过。

## 15. 不在 F07 里的

- 版本发布流程（F08）、规则变更流程（F09）、troy-pstack 的文档（F10）和试点（F11）。
- 在系列其他成员那里开 PR（D66）。
- 在并行的 worktree 里运行角色，或同时做两个功能。
- R21 在 CI 里的 troy-check 分支检查，那是以后对 F02 的改动。
- TypeScript/JavaScript 语言包（Q1）。
- 删除试运行用的仓库。

## 16. 需要 Troy 决定的事项

F06 到 D56 为止，所以 F07 从 D57 开始。

| 编号 | 问题 | 选项 | 推荐并已批准 |
| --- | --- | --- | --- |
| D57 | F07 怎样实现？ | A：技能负责需要判断的部分：分派请求、和 Troy 交谈、阅读报告，以及以产品经理身份写文档。一个只用标准库的引擎负责要求精确的工作：状态、任务简报、每次运行之后的检查，以及在文件头里记录批准（第 3 节）。B：只有技能，每一步都写在它的说明里。 | A。阶段顺序、合并权限、轮数和写入范围都是精确的规则，可以用测试检查，而且需求文档 5.8 优先用检查而不是说明。这和 F06 D47 一致。 |
| D58 | 流程的状态保存在哪里？ | A：在 git 和 GitHub 上：`main` 上的 commit 标题、开着的 PR，以及 F07 在 PR 上的评论。进度文件是 F07 重写的一个视图，不存在时重新生成（第 5 节）。B：只在进度文件里。C：在一个提交进仓库的状态文件里。 | A。桌面应用常常在新的 worktree 里开始会话，那里没有进度文件；长对话也会被压缩。用 A，流程照样能接着做。C 每次更新都要一个 PR，Q8 已经否决了这种做法。 |
| D59 | 一次运行改了角色写入范围之外的文件，F05 的 hook 也没能让它撤销。怎么办？ | A：F07 撤销这次运行的改动（每次运行前工作区都是干净的，所以撤销是安全的），再运行这个角色一次，Input 里写明这些路径。同一阶段第二次出现时升级上报。`HEAD` 或分支变了，立即升级上报（第 7 节）。B：立即停下并升级上报。 | A。撤销是机械操作，不会丢掉之前已有的东西，所以只有再次发生时才需要问 Troy。 |
| D60 | `troy-check code` 只读 commit，而角色不能提交（F05 第 12 节）。产出方怎样在报告之前检查 R04 到 R11？ | A：`troy-check code --worktree` 把工作区当作一个 commit 来检查（第 12 节）。每次推送之前，F07 仍然在真实的 commit 上运行 `troy-check code`。B：只由 F07 在提交之后运行它，把失败交回去再运行一次。 | A。一次角色运行的花费远高于一次检查。用 A，开发工程师在自己的那次运行里就能修好 R04、R05、R07 和 R11。B 每发现一个问题就多一次运行。 |
| D61 | Troy 怎样批准需求文档、架构，以及前几个功能的 PR 1 和 PR 2？需求文档 3.3 和 R18 说由 Troy 合并它们。 | A：Troy 在聊天里回复，或在 GitHub 上合并。收到回复时，F07 把批准记进文档的文件头（下一个主版本）并合并。在 GitHub 上合并之后，F07 用一个小的 `[docs]` PR 记下批准（第 8.6 节）。B：只能由 Troy 在 GitHub 上合并。 | A。批准是 Troy 的决定，点合并按钮不是。这也是 Troy 在 troy-pstack 里的做法。用 B，每份批准过的文档都需要那个补充 PR，因为在 GitHub 上合并无法提升文档的版本。这会改动需求文档的 3.3 和 R18。 |
| D62 | F07 怎样知道哪些是"前几个功能"（Q2），以及 Troy 在那之后的决定？ | A：配置里的 `[flow] troy_approves_first = 3`。这些功能中的最后一个验收后，F07 问 Troy 一次，用一个 `[rules]` PR 记下回答（第 8.6 节）。这是 F07 唯一会做的配置改动，其他规则变更等 F09。B：固定为 3，之后 F07 合并一切，不再询问。C：每个功能之前都问一次。 | A。Q2 里"之后由 Troy 决定"落在一个每个会话都会读取的文件里，而且只有 Troy 说了才会改。 |
| D63 | 一个请求做到哪里？ | A：一个功能、一个 bug 或一项变更，除非请求点名了更多（"F04 到 F06"、"v0.1 剩下的"）。B：一直做完整个版本。 | A。每个功能结束时都是一个自然的停顿点，Troy 能看到结果，而请求仍然可以要求做更多。 |
| D64 | 需求文档 5.7 把实现的尝试次数限制为 3 次。其他产出方，比如开发工程师写 mock、测试工程师写测试，没有限制。 | A：每个阶段都允许 3 次尝试。一次尝试是一份 `failed` 报告、一份检查没通过的 `done` 报告，或在产出方文件上的一次 CI 失败（第 8.5 节）。B：只统计 DV2，和 5.7 现在说的一样。 | A。没有限制的话，一个阶段可能一直循环、一直花钱，直到有人发现。这会把 5.7 的第三个触发条件改为"产出方 3 次尝试后仍过不了检查"。 |
| D65 | 需求变更涉及一个已经验收的功能时怎么办？troy-check 要求这个功能的测试必须通过，所以不能简单地让它的循环重来。 | A：PM2 为这项变更新增一个功能，它硬依赖旧功能。它的测试 PR 淘汰被这项变更证明为错的旧测试，并加上新测试；没有新接口时，F07 跳过它的 mock PR（第 11.2 节）。B：在以后的功能设计出办法之前，F07 把每一项这样的变更都升级上报。 | A。规则和 troy-check 都保持不变，历史里这项变更也是一个独立的功能。这会给需求文档的 5.4 增加内容。 |
| D66 | F03 把系列锁文件留给了 F07：依赖改动之后，每个成员的测试都要在共享环境里运行，其他成员在各自的 PR 里拿到新的锁文件。F07 做多少？ | A：F07 编译锁文件、安装、运行每个成员的测试，并列出锁文件因此过期的成员。它不在其他仓库里开 PR。B：F07 还在每个属于 troy-mode 项目的成员里开一个 `[rules]` PR。 | A。没有 Troy 的同意，项目之外的东西一概不动；而且现在还没有哪个系列有第二个 troy-mode 成员。B 可以等出现第一个这样的系列时再做。 |
| D67 | F07 怎样合入？Q10 规定每个功能一个 PR。 | A：两个 PR（第 14.4 节）。第 1 部分包括请求分派、项目初始化、功能循环主线和接续。第 2 部分包括旁支 PR、修 bug 和需求变更。B：一个 PR。C：按层分两个 PR，先引擎后技能。 | A。第 1 部分已经能用于项目初始化和做功能，每个 PR 也都便于审查。C 的第一个 PR 合入后，什么都还用不了。这会把 F07 加进 Q10 的例外。 |
| D68 | F07 怎样试运行？状态什么时候改？ | A：测试和埋 bug，再在 `ZJUCao/troy-mode-trial` 上对每一部分试运行，包括一次会话中断和在新 worktree 里的接续（第 14.3 节）。B：同上，但用本地裸仓库作 `origin`，所以 PR 和 CI 并没有真正运行。状态为"已编写"，直到试点。 | A。只有真实的仓库才能证明审查、CI 和合并能从头跑到尾。总共大约运行 26 次角色，用几分钟 Actions 时间，而且每一部分的试运行都要 Troy 在聊天里同意才开始。 |
| D69 | 测试方案的某个用例只在一个平台上运行，所以 Troy 电脑上的本地 `troy-check code` 不通过，而 CI 通过（第一部分试运行中发现）。F07 怎样合并？ | A：本地的失败只有在本平台跳过的测试时，F07 不记尝试，在 PR 里列出这些用例，按 CI 的结果合并（第 8.6 节）。B：每次都升级上报。C：禁止这样的用例；测试经理把每个用例都写成到处都能运行，或者放进"不测试"。D：troy-check 不再把跳过的测试算作失败。 | A，Troy 已于 2026-11-07 批准。CI 通过就证明这些测试运行过。B 会在每个这样的功能的 PR 4 和 PR 5 上问 Troy。C 会丢掉对真实行为的测试。D 在 CI 里也会放过，于是一个在所有平台都跳过的测试永远没人检查。需求不用改，因为 R09 和 R10 是 CI 规则。 |
| D201 | 试点中（ZJUCao/recipe-menu#2），中文需求文档把修改记录一节写成 `变更记录`，而不是模板里的 `修改记录`。`approve` 在那里找不到修改记录表格，只在英文文件里加了批准的那一行，并以退出码 0 结束，只给了一条说明。这一对文件里任何一个缺少修改记录表格时，`approve`、`accept-version`（F08）和 `rule-row`（F09）该怎么做？来自 tstack issue #46。D70 到 D200 属于后来的设计，所以这个决定用 D201。 | A：以退出码 1 结束，两个文件都不改；问题里写出是哪个文件，以及查找的标题。B：保留说明，以退出码 0 结束。C：A，另外由 R12 或 R20 检查文档每种语言的章节标题是否和模板一致。 | A，Troy 已于 2026-11-18 批准。这样批准要么在两种语言里都记下，要么都不记。`rule-row` 原本就拒绝这样的一对文件（F09 设计第 3.3 节）；现在它的问题也写出查找的标题。C 的标题检查不属于这个决定。需求不用改：需求文档 3.3 已经说了批准要记进修改记录。 |
| D202 | 试点中（ZJUCao/recipe-menu#3），对架构运行 `approve` 只改了它的文件头和修改记录。它的决策记录表，以及七条 ADR 每条的状态一节，在两种语言里都仍写着 "Proposed"。产品经理自己去改，被 `check-run` 拒绝了，因为架构不在它的范围里，于是 AR1 又运行了一次，只为改这些字。来自 tstack issue #47。 | A：`approve --doc docs/architecture.md` 同时把架构列出的 ADR 的状态在两种语言里都改为已接受，架构自己的状态单元格也一起改。B：架构和 ADR 模板只在文件头里保存状态，这样只用 `approve` 就够了。 | A，Troy 已于 2026-11-18 批准。每次批准带 ADR 的架构都能省一次架构师运行，而且文件头里的状态字本来就由引擎负责。B 要改 F01 的模板，而 F16 的角色考试正在衡量这些模板。只改仍处于提议状态的 ADR；已接受和已取代的不动。功能设计里提出的 ADR 不在范围内。需求不用改。 |
| D203 | 试点中，Troy 输入了 "Start v0.1"。troy-mode 把 F01 做完六个 PR，然后停下，说 "Next is F02"，之后 Troy 每个功能都要单独请求一次。路由表把 "the rest of v0.1" 列为做到这个版本每个功能的请求（D63），但 "Start v0.1" 也点名了一个版本。来自 tstack issue #52。 | A：点名一个版本的功能循环请求，做到这个版本剩下的功能。B：范围不变，在一个功能验收后的报告里说明怎样请求做完这个版本剩下的部分。 | A，Troy 已于 2026-11-18 批准。每个 PR 仍在今天的位置等 Troy 批准，变的只是请求的次数。范围在发布之前停下，发布仍是单独的请求。需求不用改：D63 写在本设计和技能里。 |
| D204 | 试点中（ZJUCao/recipe-menu#47，2026-11-12），一个 PR 刚推送就合并了：`gh pr checks 47 --watch` 打印了 "no checks reported"，因为 GitHub 还没登记工作流，而用 `;` 接在后面的合并照样运行了。之后试点的主会话自己留了一个脚本，等推送的头提交的检查。来自 tstack issue #68。 | A：一个引擎命令 `wait-checks --pr <n> --sha <head>`，等到这个头提交的每项检查都已登记并结束，用退出码报告通过还是失败；合并步骤和 `gh pr merge --match-head-commit <head>` 一起用它，永远不用 `;` 把合并接在后面。B：技能的合并步骤用文字写出这次等待，并禁止连写。 | A，Troy 已于 2026-11-18 批准。退出码是检查，需求 5.8 更愿意用检查而不是指令。在 troy-mode 项目里等 CI 是 troy-mode 合并步骤的一部分。需求不用改：R18 已经说了检查通过后 troy-mode 才合并。 |
| D205 | 类的构造函数用哪条注释？tstack #63 给出 "The mock leaves out the constructor's checks."，对还会改动参数的构造函数给出 "The mock keeps the values as given and leaves out the constructor's checks."。F16 的试运行里，考试 2026-11-19-5 用了这段文字：五次新版本运行全都写了一个保存参数的 `UsageError.__init__`，这违反了开发工程师的第 2 步和必须项检查 `mock_bodies_only_raise`。第二句话只对由语言生成的构造函数成立。F16 设计 14.6 把这个问题留给 #63 的设计。 | A：#63 的两句话，用于每个类。B：#63 的两句话只用于由语言生成的构造函数，比如 dataclass 的；类自己写的构造函数和其他函数体一样只抛出异常，类的文档注释写 "The mock's constructor raises ``NotImplementedError``."。C：同 B，但自己写了构造函数的类写 "The mock leaves out the constructor's checks."。D：mock 的构造函数可以保存参数；DV1 的第 2 步、CR1 对 mock 的审查和 dv-mock-notes 的 `mock_bodies_only_raise` 跟着改。 | B，按 Troy 2026-11-22 对小问题的长期同意批准。B 的新句子对类自己写的每个构造函数都成立，不论它检查或改动什么；C 的句子没有说到排序或转换，比如 `UsageError` 按名字排序的参数。A 在这一点上五次运行全部失败，D 要改 mock 规则和一个用例。考试 2026-11-19-8 的文字点到了排序，七次新版本运行里仍有两次栽在 `UsageError` 上：一次让类的文档注释没有注释，一次给 `__init__` 写了函数体。B 给类的句子和 "a constructor that the class writes too" 针对的正是这两种。 |
| D206 | 代码审查员的代理文件要不要改？tstack #63 在 CR1 的第 4 步加上 "and in a mock or implementation PR, the mock's notes as the brief gives them"。任务简报已经在 PR 3 和 PR 5 给出这项检查。每次 CR1 运行都会读代理文件，所以这一行也会让审查 PR 4 的 cr-test-review 成为受影响的用例（F16 设计 9.2）。 | A：按 #63 改。B：代码审查员的代理文件保持原样，由任务简报在适用的地方带上这项检查。 | B，按 Troy 2026-11-22 对小问题的长期同意批准。这一行没有说出任务简报以外的东西。不加它，cr-test-review 的十次 opus 运行就不进构建的考试：按试运行每次 $2.95 的中位数，连同评审一次约 $31。考试第一轮因此约 $37，而不是约 $68，低于 F16 D158 的 $60 线。开发工程师的代理文件照样改，因为它的两个用例反正要运行。 |
| D207 | PR 5 可以改功能文档注释里的什么？tstack #63 的 DV2 文字说 "change nothing else in those doc comments"，它在 PR 5 时的 CR1 文字检查 "that nothing else in those doc comments changed"。可是试点自己的 F08 实现，也就是用例 dv-impl-notes 的通过锚点，把 `os.path.isfile` 加进了某个文档注释列出的探测里，因为代码调用了它，而这个用例的标准 1 要求文档注释对代码成立（R05）。 | A：按 #63。B：DV2 删掉注释，其余文档注释只在某句话对它的代码不成立时才改；PR 5 时的 CR1 检查没有留下注释，并且其他每处改动都让文档注释对代码成立。 | B，按 Troy 2026-11-22 对小问题的长期同意批准；Troy 已于 2026-11-22 按原文批准 PR 3 和 PR 5 两行的需求子句。按 A，代码需要某个 mock 文档注释漏掉的调用时，开发工程师只能留下一句假话。DV1 仍要求文档注释描述实现，所以 PR 5 很少需要删除以外的改动。 |
| D261 | tstack issue #73（试点报告的候选 T1，Troy 于 2026-11-16 接受）：`status` 和 `retro` 只从 F07 的评论统计尝试次数，而试点中 CI 有四次推送在产出方的文件上失败，只发了一条评论。哪些推送提交要算，一条评论又怎样算是已经算过某个提交？ | A：CI 为这个 PR 运行过的每个提交最多算一次，由它上面每个工作流最新的运行决定；被取消和正在运行的运行不算；评论算它的 `Commit:` 行点名的提交，没有这一行的评论算它发出时 PR 最新的推送提交，前提是那个提交当时已经失败，并且没有别的评论算过它（第 8.5 节）。B：同 A，但只认 `Commit:` 行。C：每个失败的运行都算，包括重跑和改 PR 说明而开始的运行。D：只算 PR 的最后一个提交。 | A，依据 Troy 2026-11-22 的长期同意批准。一次推送是产出方的一次尝试，所以重跑不能增加尝试次数（反对 C）；产出方修好了的失败仍然是一次尝试，而 D 会漏掉它：这正是 #52 的情况。B 会把试点的 #59 算成三次，因为它的评论发在 `Commit:` 行出现之前，而且主会话每次忘了写这一行都会重复计数。A 把试点的 PR 算对：#52 两次，#59 两次。 |
| D262 | 对每个语言包的作业，怎样把失败的运行和产出方的文件对上？ | A：按失败的步骤。`Run troy-check`，以及语言包作业里 `Install from the lock` 之后的每个步骤，都在仓库文件上运行检查，所以它们失败就是产出方的。其他步骤的失败，比如检出、环境安装、`Install from the lock`、被取消或超时的步骤，或者 troy-mode 没有写的工作流，都不算尝试，F07 停下并告诉 Troy（第 8.5 节）。B：按日志：读 `gh run view --log-failed`，找 PR 改过的路径。C：每个失败的运行都算尝试。 | A，依据 Troy 2026-11-22 的长期同意批准。PR 里只有这个阶段的工作，放在检查已通过的 `main` 上，所以检查步骤在这里失败，就是在这份工作上失败。B 会漏掉实现没通过测试的情况，因为 pytest 的日志只点名测试文件，而测试文件是测试工程师的；它还要为每个运行下载日志。C 会把试点 #87 的 "Repository not found" 也算进去（指南第 8.6 节）。步骤名来自 troy-mode 自己的工作流文件，有一个测试把这份名单和它们对照。 |
| D263 | `status` 算上的失败，事后也补发评论，让 PR 上能看到吗？ | A：补发。`status` 在 `ci_failures` 里给出每个开着的 PR 的失败提交，以及每个还没算过的提交要取的尝试编号；F07 继续之前发出 `<Role> attempt <n>: failed`，带 `Commit: <commit ID>` 一行，次数保持不变。`retro` 什么也不发（第 8.5 节）。B：不补发。`status` 算上它，PR 上显示的尝试比次数少。 | A，依据 Troy 2026-11-22 的长期同意批准。流程的状态放在 GitHub 上（D58），所以 Troy、新会话和复盘都从 PR 上读到同样的尝试。补发的评论用 `status` 给出的次数编号，发出前后次数都一样。`retro` 不改任何东西（F08 第 3.1 节），所以已合并 PR 的失败只出现在它的报告里。 |

| D264 | tstack issue #74（试点报告的候选 T2，Troy 于 2026-11-16 接受）：每个验收 PR 和发布 PR 给出它的角色运行和费用，从会话记录读出。会话记录在哪里找，一个功能跨多个会话或多台电脑时怎么办？ | A：`costs` 自己去找，在主检出、它的工作树和桌面应用已删掉的工作树的记录文件夹里；一次角色运行属于它的任务简报 `Item:` 行点名的条目，不管在哪个会话；多个会话加起来；报告写明只读了这台电脑，并点名没找到运行的每个阶段（第 8.8 节）。B：技能传入它运行过的每个会话的 ID。C：主会话边做边记下每次运行的 token，记在进度文件或 PR 评论里。 | A，依据 Troy 2026-11-22 的长期同意批准。不需要记住任何事：试点的版本已经跨了两个会话文件，而 B 每次重启后都会丢掉一个会话。C 每次运行后都要多一步，进度文件丢了就没了，而且 Agent 工具的结果不按种类给出 token，所以价格算不对。在另一台电脑上运行很少见，因为 Troy 只用一台电脑工作，而没找到运行的阶段会指出缺了哪里。 |
| D265 | 价格表放在哪里，谁来更新？ | A：插件里的 `troy-mode/flow/prices.toml`：每个模型每种 token 每百万的美元价格，有快速模式的另有快速价格表，一次网页搜索的价格，以及读取价格的日期；标价变了或有新模型时由一个 tstack PR 更新（第 8.8 节）。B：每个项目 `.troy-mode/config.toml` 里的 `[prices]` 表。C：引擎每次都去读 Anthropic 的价格页。 | A，依据 Troy 2026-11-22 的长期同意批准。一张表服务每个项目，和读它的引擎一起变，测试也能检查它。B 要手动更新每个项目的配置，troy-check 的配置读取器也得认识这张表。C 需要联网，还依赖可能变化的页面格式，而引擎只读 git、GitHub 和会话记录。 |
| D266 | 桌面应用记下会话自己的累计费用时，报告要显示它吗？试点中它和算出的数字相差不到 2%。 | A：PR 里不放应用的数字；`costs` 用自己的价格表给最新一条 `cost-state` 记录的 token 数定价，某个模型相差超过 1% 时加一条说明，这表示价格表过时了（第 8.8 节）。B：把应用的数字和算出的数字并排显示。C：不理这些记录。 | A，依据 Troy 2026-11-22 的长期同意批准。这条记录是应用一次运行跨所有功能的累计总数，没有时间，所以没法切到一个功能或一个版本上。作为价格检查它很准：试点的记录分毫不差地给出了价格表里 Opus 5.5、Sonnet 5.5 和 Haiku 5.5 的价格。 |
| D267 | F14 给 Troy 的摘要要带一行费用吗？ | A：不带。费用放在验收和发布 PR 说明里它自己的一节，以及给 Troy 的报告里的一行（第 8.8 节）。B：在 PR 1 的摘要里加一行，写这个功能到目前为止的费用，或者上一个功能的费用。 | A，依据 Troy 2026-11-22 的长期同意批准。摘要出现在 PR 1、PR 2、需求文档和架构的 PR 开头，不在验收或发布 PR 上，而一个功能的费用要到最后才知道。摘要的模板和技能的"The summary for Troy"一节属于 F16 的指令集，所以 B 会改变角色写的内容，还需要角色考试。 |
| D284 | tstack issue #67，F11 试点里的一个问题：审查给后续功能留下备注，而 `status --note` 只在功能和阶段都不变时才保留备注。这些备注存在哪里，才能在任何电脑上、在 F20 团队的 worktree 里、以及 `team end` 之后，都送到对的功能的任务简报？ | A：troy-mode 在进度 issue 上的 `Note for <ID>, from <source>` 评论：发在来源功能的 issue 上；来自聊天或来自功能之外工作的备注，发在目标功能的 issue 上，否则发在下一个功能的 issue 上（第 6.6 节）。B：发在审查发现它的那个 PR 上的评论。C：项目里一个专门的备注 issue，带自己的标签。D：每个功能一个受版本管理的文件 `docs/features/<id>-<slug>/notes.md` 及其镜像，通过 `[docs]` PR 落地。E：`status --note --for <ID>`，保存在流程状态里，直到这个功能的第 1 阶段开始。 | A，依据 Troy 2026-11-22 的长期同意批准。它和其余状态一起存在 GitHub 上（D58），所以换电脑、换会话、团队的 worktree 和 `team end` 都不会丢东西，而 `status` 本来就读取每个 issue 及其评论。B 要读取每个已合入 PR 的评论，而且来自聊天的备注没有 PR。C 增加第四种 issue 和标签，会改动需求文档里 F15 那一行。D 每批备注都要一个 PR、一份镜像和一次 CI，而试点有几十条，F20 也把共用文档排除在团队之外（D277）。E 只留在一台电脑上，正是试点的问题。 |
| D285 | 谁来记下备注，怎样记？ | A：主会话，根据任何角色的报告或 Troy 在聊天里说的，用自己的话，通过引擎的 `note` 命令记下，评论由技能检查并发出（第 6.6 节）。B：在每个角色的 Report 一节加一个新字段 `Later:`，由引擎读取。C：同 A，另外让审查角色的代理文件要求它们把这类意见以 `Later <ID>:` 开头。 | A，依据 Troy 2026-11-22 的长期同意批准。主会话本来就读每份报告，试点的备注也是这样来的。B 会改 `common.md` 和每个代理文件，十二道考试用例都要运行：按 troy_exam 的预算代码第一轮 $255.43。C 改三个代理文件，它们的六道用例要 $159.30。 |
| D286 | 哪些任务简报拿到一个功能的备注？ | A：这个功能每次 IF1、IF2 和 DV2 运行，放在 Input 里，每个任务带一句话；功能没有备注时都不加（第 6.6 节）。B：备注指明它的阶段（设计或实现），只有那个产出方的任务简报拿到它。C：这个功能每个产出方的任务简报。 | A，依据 Troy 2026-11-22 的长期同意批准。试点把每条备注复制进一份 IF1 或 DV2 任务简报。两者都拿到每条备注，主会话就不用判断阶段，而 DV2 的那句话让已批准的设计在两者不一致时优先。C 会给 TM1、DV1 和 TE1 加上它们用不上的备注。 |
| D287 | troy-mode 怎样看出一条备注送到了它的任务简报？ | A：`status` 给出每条备注还能送到哪里，依据它记下的时间和功能的 PR 1、PR 5 开出的时间，并标出迟到的备注；迟到的备注需要什么，由主会话决定并告诉 Troy（第 6.6 节）。B：除了 `brief` 加上备注之外什么都不做。C：迟到的备注让这个功能停下，直到 Troy 决定。 | A，依据 Troy 2026-11-22 的长期同意批准。`brief` 会加上它找到的每条备注，所以只有在某个阶段的运行之后才记下的备注会错过，而 A 恰好指出这些。C 会为一条已合入的工作可能已经做到的备注让一个团队停下。 |

D261 到 D263 不改需求：D64 已经把产出方文件上的 CI 失败算作一次尝试（需求文档 5.7）。D264 到 D267 也不改需求：这份报告是 F07 和 F08 负责的验收和发布步骤的一部分，就像 D204 的等待是合并的一部分。D284 到 D287 也不改需求：备注是 GitHub 上的状态（D58），也是任务简报的 Input，而进度 issue 保持它的六个方框和它的生命周期（F15 D142）。

D205 到 D207 是 tstack issue #63 的设计，Troy 已于 2026-11-16 接受这条规则（ZJUCao/recipe-menu#94，AR6 选项 A）。需求文档 1.55 版在它第 5.2 节的 PR 3 和 PR 5 两行各加一个子句，第 6 节不加新行。Troy 已于 2026-11-22 批准这两个子句。

F05 的 D231（F05 设计第 6.1 节），Troy 已于 2026-11-21 批准，改动第 6.2 和 7 节以及入口技能的"Running a role"一节，并在需求文档 1.52 版的 F07 一行加上一个分句（F05 设计第 15 节）。F07 不为它另作决定。

需求文档 1.20 版记录了批准的改动：

- F07 一行：引擎和技能、保存在 git 和 GitHub 上的状态、每次运行之后的检查、`troy-check code --worktree`，以及分两部分合入（D57 到 D60、D67）。
- 3.3、5.2 表的合并方一栏和 R18：Troy 在聊天里批准或通过合并批准，在聊天里批准之后由 troy-mode 合并（D61）。troy-mode 规则模板里的 R18 一行随之改动。
- 5.7：对每个产出方的尝试次数限制（D64）。
- 5.4：对已验收功能的变更成为一个新功能（D65）。
- Q10：F07 分两个 PR 合入（D67）。

## 17. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-07 | 初稿。 |
| 1.0 | 2026-11-07 | Troy 批准，含 D57 到 D68，全部采用推荐答案。 |
| 1.1 | 2026-11-07 | 第一部分试运行（第 14.3 节）确认的事实：Agent 调用带上 `[roles]`，会话会等写文件的角色（第 1 节）；技能通过 Bash 运行引擎、git 和 gh（第 2 节）；IF1 不在第 4 节留模板标记（第 6.1 节）；功能名称保持简短（第 8.1 节）；刚推送后 `gh pr checks --watch` 可能要再启动一次（第 8.6 节）。 |
| 1.2 | 2026-11-07 | Troy 的 D69：只在另一个平台上运行的测试交给 CI（第 8.6 节）。第二部分确定的细节：`brief --title`、`check-skips` 和 `series`（第 3.1 节）；状态里的历史顺序、bug 和旁支 PR 优先（第 5.1 节）；谁写每个旁支 PR（第 8.7 节）；bug 的分支（第 11.1 节）；返工、重做、跳过的 mock 和变更的批准（第 11.2 节）；第二部分的测试和埋 bug（第 14.1 和 14.2 节）。来自第二部分试运行：没有开着的 PR 时，升级上报发到 bug 的 issue 上（第 9 节）。 |
| 1.3 | 2026-11-08 | 来自 F08 设计第 9 节：“发布”请求交给 F08 的版本发布流程（第 4 节）；`status`、`brief` 和 `approve` 按 F08 第 3 节修改，`approve` 会加一行修改记录（D77，第 8.6 节）；权限加上 GitHub release（第 9 节）。来自 F08 的试运行：每次 fetch 都带 prune（第 8.2、8.6 节）。 |
| 1.4 | 2026-11-08 | 来自 F09 设计第 8 节：“加一条规则”的请求交给 F09 的规则变更流程（第 4 节）；引擎加上 `rule-id`、`rule-row`、`rules` 快照角色、`check-run` 对只删 `baseline:` 行的依赖改动的规则，以及 `cleanup` 动作；技能每次启动时读取类型为流程的 P 行。 |
| 1.5 | 2026-11-09 | 第 6.1 节：按实际构建，brief 只在 PATH 和 `$MAMBA_EXE` 里找 mamba。由 F10 的事实核查发现；同时发现技能里的两句话和产品经理的 PM2 与 F09 和 D65 的决定不符，现已改正：规则变更流程也会改配置，已验收的功能在变更后保留原状态。 |
| 1.6 | 2026-11-18 | D201，来自 tstack issue #46，Troy 已于 2026-11-18 批准：这一对文件里任何一个没有修改记录表格时，`approve`、`accept-version` 和 `rule-row` 以退出码 1 结束，什么都不改（第 8.6、14.1、14.2 和 16 节）。 |
| 1.7 | 2026-11-18 | D202，来自 tstack issue #47，Troy 已于 2026-11-18 批准：批准架构时，同时在两种语言里接受它列出的、仍处于提议状态的 ADR，以及它们在架构表格里的状态单元格（第 3.1、8.6、14.1、14.2 和 16 节）。 |
| 1.8 | 2026-11-18 | D203，来自 tstack issue #52，Troy 已于 2026-11-18 批准：点名一个版本的功能循环请求，比如 "Start v0.1"，做到这个版本剩下的功能，在发布之前停下（第 4、14.1 和 16 节）。 |
| 1.9 | 2026-11-18 | D204，来自 tstack issue #68，Troy 已于 2026-11-18 批准：引擎的 `wait-checks` 等到推送的头提交的每项检查都已登记并结束，合并在它之后单独运行，永远不用 `;` 连起来（第 3.1、8.6、14.1、14.2 和 16 节）。 |
| 1.10 | 2026-11-21 | 跟随 F05 的 D231，来自 tstack issue #49，Troy 已于 2026-11-21 批准：某个角色，或它留在后台的命令，还在运行时，`check-run` 和 `snapshot` 以 `running` 问题拒绝，F07 用 `TaskStop` 结束每个列出的代理。桌面应用让每个角色都在后台运行（第 1、6.2、7、14.1、14.2 和 16 节）。 |
| 1.11 | 2026-11-22 | D261 到 D263，来自 tstack issue #73，依据 Troy 2026-11-22 的长期同意批准：`status` 和 `retro` 还从 PR 推送过的提交的 CI 运行统计尝试次数，每个提交最多一次，只在检查步骤失败时算，评论已经算过的不再算；F07 带着 `Commit:` 行补发漏掉的评论（第 3.1、5.1、8.4、8.5、8.6、14.1、14.2、14.4 和 16 节）。 |
| 1.12 | 2026-11-22 | D264 到 D267，来自 tstack issue #74，依据 Troy 2026-11-22 的长期同意批准：引擎的 `costs` 读取 Troy 电脑上的会话记录，按 `prices.toml` 的标价给出一个功能或一个版本的角色运行和费用，用于验收 PR 里的 `## Cost` 一节和给 Troy 的报告里的一行；桌面应用的数字用来检查价格；F14 的摘要不带费用（第 3.1、8.8、14.1、14.2、14.4 和 16 节）。 |
| 1.13 | 2026-11-22 | D205 到 D207，来自 tstack issue #63，Troy 已于 2026-11-16 接受这条规则；这些选择按 Troy 2026-11-22 的长期同意采用推荐选项，Troy 已于 2026-11-22 批准需求子句：在 PR 3 和 PR 5，DV1、DV2 和 CR1 的 Task 加上新的 `mocknotes.py` 给出的固定 mock 说明文字，按 `[lang] name` 选择；类自己写的构造函数只抛出异常，类的文档注释写明这一点；代码审查员的代理文件不改；PR 5 只在代码让文档注释不成立时才改注释以外的部分（第 6.1、6.4、14.1、14.2、14.4 和 16 节）。 |
| 1.14 | 2026-11-22 | F20 设计（D268 到 D279，Troy 已于 2026-11-22 批准）：引擎增加 `team`、`plan` 和 `merge-check`，`status`、`brief`、`snapshot`、`check-run`、`retro` 和 `costs` 学会处理多个团队；每个团队同一时间一个会写文件的角色，主会话管各团队的循环，PR 按做好的先后合并并 rebase（R24）；第 15 节的同时做两个功能移入 F20（第 3.1、5、6.2、7、8.6、8.8 和 15 节）。这些改动随 F20 的构建落地。 |
| 1.15 | 2026-11-23 | F04 的 D280 到 D283，来自 tstack issue #75，依据 Troy 2026-11-22 的长期同意批准：`brief` 按新的 `troyflow/risks.py` 里各语言包的列表，检查 CR1 所审 PR 的 diff 里有没有依赖、子进程调用、网络访问和凭据处理，CR1 的 Task 说明要不要运行 `/security-review`；CR2 的任务简报在一次发布的审查分支上运行（第 6.1、6.5、14.1 和 14.2 节）。 |
| 1.16 | 2026-11-23 | D284 到 D287，来自 tstack issue #67，依据 Troy 2026-11-22 的长期同意批准：给后续功能的备注是主会话用新的 `note` 命令在进度 issue 上发的 `Note for <ID>` 评论；`brief` 把一个功能的备注加进它的 IF1、IF2 和 DV2 运行的 Input，在团队的 worktree 里和 `team end` 之后也一样；`status` 给出备注并标出迟到的（第 3.1、5.1、6.1、6.6、14.1、14.2、14.4 和 16 节）。 |
| 1.17 | 2026-11-24 | tstack #75 的构建确定的细节：`risks.py` 不认识的语言包用的那句话，以及在审查分支之外给出 CR2 任务简报时的问题（第 6.5 节）。 |
| 1.18 | 2026-11-24 | tstack #67 的构建和它的试运行确定的细节：`status` 的键 `feature_notes`、用 `createdAt` 定阶段 PR 的开出时间、`note` 的报告、在 `insteadOf` 之前读取 origin、关闭 issue 视为没有备注、`notes.py` 自己读取 `gh`，以及试运行的结果（第 6.6 和 14.4 节）。 |
