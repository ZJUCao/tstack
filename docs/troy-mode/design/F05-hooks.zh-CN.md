# F05 设计：hook

> 本文件是 [`F05-hooks.md`](F05-hooks.md) 的中文镜像，同步自英文版 1.6（2026-11-22）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.15](../requirements.zh-CN.md#72-功能列表) 中的 F05 |
| 版本 | 1.6 |
| 日期 | 2026-11-22 |
| 状态 | Troy 已于 2026-11-06 批准，含 D39 到 D46。1.1 版记录第 13.3 节试运行确认的事实。1.2 版加入 D200，即 Troy 于 2026-11-16 批准的 tstack issue #65。1.3 版加入 D219，即 Troy 于 2026-11-18 批准的 tstack issue #66。1.4 版加入 D223，即 Troy 于 2026-11-16 批准的 tstack issue #64。1.5 版加入 D231、D232 和 D234，即 Troy 于 2026-11-21 批准的 tstack issue #49（第 6.1 节）。1.6 版记下 F20 设计（D268 到 D279，Troy 已于 2026-11-22 批准）带来的改动，这些改动随 F20 的构建落地。 |
| 事实来源 | 英文版 [`F05-hooks.md`](F05-hooks.md)。本文件是中文镜像。 |

## 1. 范围

角色或 Claude 可能无意中违反的规则，F05 让它们在被违反的那一刻就失败，而不是等到 CI 才发现。它交付：

1. **Claude Code hook**，随插件发布。在 troy-mode 项目里，它们：
   - 让每个角色留在自己的写入范围内（F04 设计 D31），开发工程师修改测试（R08）是其中一种情况；
   - 让其他所有子代理只读；
   - 只允许角色运行只读的 git 和 GitHub 命令，以及它们需要的技能；
   - 阻止 Claude 跳过 git hook、从 `main` 开 PR（R21）、发出文字里带署名的 PR、评论、评审、issue 或发布说明（R19，D200）；
   - 阻止每个调用方运行从标准输入读取程序的 Python（R23，D223）；
   - 不让角色留在后台运行的命令在角色报告之后修改工作区：把这样的命令记下来，让 F07 结束它，并拒绝已经停止的角色的每次调用（第 6.1 节，D231，D232）；
   - 让角色不需要权限规则就能读插件自己的文件。
2. **git hook**，放在 troy-check 的文件夹里，由 troy-init 复制进每个项目。不论谁运行 git，它们都拒绝违反 R19 的提交、在 `main` 上的提交和推送到 `main`（R21）。
3. **一份本地日志**，记录每次拦截。F07 在每次角色运行后读取它，F08 的回顾按整个版本读取它（D219）。

在 troy-mode 项目之外，每个 hook 都立即退出（需求文档第 8 节）。

F05 不往项目里复制文件（F06），不启动角色，也不在运行后检查 `git status`（F07），不检查 PR（CI 里的 F02 和 F03）。

**hook 能拦住什么、拦不住什么。** 它们拦得住配合工作的角色犯的错，以及 Claude 的习惯，比如署名行或在 `main` 上提交。它们拦不住刻意的绕过：Bash 修改文件的方式有很多是 hook 看不到的，测试运行的代码也可以做任何事。CI 的 R02 和 R19，以及 F07 每次运行后的检查，仍然是最后的防线。

本设计中关于 Claude Code 的事实来自它 2026-11-06 的文档（hooks、permissions、plugins 和 sub-agents 页面），以及 F04 的试运行（PR 15）。第 13.3 节的试运行会核实文档没有说清的事实。

## 2. 位置

```text
hooks/
  hooks.json                  插件的 hook 配置，放在插件的标准文件夹里（F01 D6）
troy-mode/
  hooks/
    troy_hook.py              入口，每个 hook 事件一个子命令
    troyhook/                 内部模块（由开发者决定）
    tests/                    单元测试（第 13.1 节）
  checks/
    git-hooks/                和 troy-check 的其余部分一起复制进项目（F02 D8）
      commit-msg
      pre-commit
      pre-merge-commit
      pre-push
    tests/
      test_git_hooks.py       git hook 的测试（第 13.1 节）
```

- Claude Code hook 和 troy-check 一样，使用 Python 3.11 或更新版本，只用标准库（F02 D7）。它们从插件自己的 `troy-mode/checks/` 导入 troy-check 的路径类别、路径模式、配置读取和署名规则，所以 hook 和 CI 对路径的分类完全一样。
- `hooks.json` 和 git hook 的文件名由 Claude Code 和 git 规定，不能以 `troy-` 开头。其他新名字都以它开头。
- `hooks.json` 的每条命令都在 Git Bash 里运行（`"shell": "bash"`）。它只用 shell 内置命令选择解释器，所以不会多启动一个进程：设置了 `$TROY_MODE_PYTHON` 就用它，否则在 Windows 上用 `python`，在其他系统上用 `python3`。在 Windows 上，`python3` 常常是 Microsoft Store 的占位程序。然后它运行 `troy_hook.py <event>`。
- git hook 是 POSIX `sh` 脚本，使用 LF 换行，带可执行位。只有 `commit-msg` 需要 Python，它用同样的方法选择解释器。

## 3. hook 事件

| 事件 | 匹配条件 | 做什么 |
| --- | --- | --- |
| `SessionStart` | 全部 | `core.hooksPath` 未设置时，打开项目的 git hook（第 8.1 节）。删除一天前的角色记录，以及 `[hooks] log_days` 天前的日志行，默认 30 天（第 10 节，D219）。 |
| `SubagentStart` | `^troy-pstack:troy-` | 记录角色开始时的状态，供变更检测使用（第 6 节）。已经停止的角色，它的记录保持原样（第 6.1 节）。 |
| `PreToolUse` | `Bash\|PowerShell\|Edit\|Write\|NotebookEdit\|Skill\|TaskStop` | 用写入范围检查文件路径（第 5 节），检查 git、GitHub 和技能命令（第 7 节），R19 和 R21 的防护（第 8.2 节），以及 R23 的 Python 检查（第 8.3 节）。拒绝已经停止的角色的每次调用；主会话用 `TaskStop` 停止一个角色时，关闭它的记录（第 6.1 节）。 |
| `PreToolUse` | `Read`，带 `"if": "Read(//**/troy-pstack/**)"` | 允许读取插件自己的文件（第 9 节）。 |
| `PreToolUse` | `Glob\|Grep` | 允许搜索插件自己的文件（第 9 节）。 |
| `PostToolUse` | `Bash\|PowerShell\|Skill` | 对角色：报告这次调用在写入范围之外做的改动（第 6 节），并记下被 Claude Code 转到后台的命令（第 6.1 节）。 |
| `SubagentStop` | `^troy-pstack:troy-` | 对角色：让角色继续工作，直到它撤销范围之外的改动，只拦一次（第 6 节）。然后把角色标为已停止，并保留它留在后台运行的命令（第 6.1 节）。 |
| `SessionEnd` | 全部 | 关闭正在结束的会话里各角色的记录（第 6.1 节）。 |

- `SubagentStart` 和 `SubagentStop` 的匹配条件匹配的是 `agent_type`，是一个不锚定的正则表达式，所以模式以 `^` 开头。
- 每一项都设置 `"timeout": 10`。Claude Code 的默认值是 600 秒，而 `PreToolUse` hook 超时后，调用会照常进行。
- hook 通过 stdout 上的 JSON 并以退出码 0 来拦截：`PreToolUse` 用 `permissionDecision: "deny"` 加原因，`PostToolUse` 和 `SubagentStop` 用 `decision: "block"` 加原因。Claude Code 会把原因告诉 Claude。
- 不论 hook 返回什么，Claude Code 都会检查设置里的 deny 和 ask 规则，所以 hook 的 `allow` 永远不会覆盖它们。

## 4. 谁在调用

**门槛。** 每个事件先从输入里的 `cwd` 往上找，直到最近一个含有 `.git` 的文件夹（`.git` 可以是文件夹，在 worktree 里是文件）。如果这个文件夹里有 `.troy-mode/` 文件夹，这次调用就在 troy-mode 项目里。否则 hook 以退出码 0 退出，什么也不输出。

**调用者。** 在 troy-mode 项目里，hook 把每次调用归入三类调用者之一（D40）：

| 调用者 | 怎样识别 | 文件 | git 和 GitHub | 技能 | 变更检测 |
| --- | --- | --- | --- | --- | --- |
| 主会话 | 输入里没有 `agent_id` | 不限制 | 允许写操作，但有第 8.2 节的 R19 和 R21 防护 | 任意 | 无 |
| 角色 | `agent_type` 匹配 `^troy-pstack:troy-(architect\|interface-designer\|test-manager\|developer\|test-engineer\|code-reviewer)$` | 角色的写入范围（第 5 节） | 只读（第 7 节） | 只有 `code-review` 和 `security-review` | 有（第 6 节） |
| 其他子代理 | 其他任何 `agent_id`：`general-purpose` 分叉（比如 `/code-review` 的）、Explore，或未知的 `troy-pstack:troy-*` 名字 | 仓库里除被忽略的文件外一概不能改（第 5 节） | 只读（第 7 节） | 同角色 | 无 |

- 主会话同时是产品经理和项目经理，hook 分不清哪一个在工作。所以 F05 不限制它的文件。由 F07 让产品经理留在自己的范围内。
- F04 的试运行表明，`/code-review` 以分叉方式运行，它的调用带的 `agent_type` 是 `general-purpose`。只匹配 `^troy-pstack:troy-` 的 hook 会漏掉这些调用。让其他所有子代理只读，就不需要知道它们的上级，也能覆盖这些调用；Claude Code 本来也不报告上级是谁。

## 5. 写入范围

### 5.1 对照表

写入范围就是 F04 设计第 3 节里的那些。`troyhook` 把它们存成一张表，有一个测试保证这张表和每个代理文件的 Write scope 一节相同。

| 角色 | 可以修改 |
| --- | --- |
| 架构师 | `docs/architecture*.md`、`docs/adr/**`、`docs/features/*/design*.md` |
| 接口设计师 | `docs/features/*/design*.md` |
| 测试经理 | `docs/features/*/test-plan*.md`、`docs/versions/*/test-plan*.md` |
| 开发工程师 | `source` 和 `dependencies` 两个路径类别 |
| 测试工程师 | `tests` 和 `dependencies` 两个路径类别 |
| 代码审查员 | 无 |
| 其他子代理 | 无 |

- 架构师只能改设计文档的第 4 节。hook 看到的是路径而不是章节，所以每次 AR2 运行后由 F07 检查章节（F04 D37）。
- 在 hook 这一层，`dependencies` 类别对开发工程师和测试工程师开放。依赖是否经过架构师审查、Troy 是否接受，由 CI 的 R16 标记和知道任务简报内容的 F07 来管。
- 任何角色都不能修改 `docs/rules*.md`、`.troy-mode/**`、`.github/**` 或其他任何 `config` 路径。

### 5.2 检查一个路径

对 `Edit`、`Write` 和 `NotebookEdit`，hook 在调用之前检查工具的路径：

1. **规范化。** 相对 `cwd` 转成绝对路径，解析 `..` 和链接，把 `/c/Users/...`、`/tmp/...` 这类 Git Bash 写法转成真实路径，在 Windows 上比较时不区分大小写。
2. **在仓库里：**
   1. `.git` 文件夹里的路径一律拒绝。
   2. git 忽略的路径（`git check-ignore`）允许，这是 F04 共用规则第 5 条的规定。构建产物和缓存都在这里。
   3. 其他路径，由 troy-check 的 `classify` 给出类别，用的是 `HEAD` 中已提交的 `.troy-mode/config.toml` 里的 `[paths]` 表。未提交的配置修改不能扩大写入范围。调用者的范围包含这个类别，或者范围里某个模式匹配，就允许。
3. **在仓库外**（D42）：系统临时文件夹（Python 的 `tempfile.gettempdir()`，在 Linux 和 macOS 上还有 `/tmp`）和会话的 scratchpad（hook 输入里的 `scratchpad_dir`）允许，其他地方一律拒绝。F04 试运行里测试经理把临时副本放在临时文件夹，这样仍然允许。hook 只是不拦这些写入：Claude Code 自己的权限照样生效，在没人能批准提示的会话里，它会拒绝项目之外的 `Write`。F05 试运行证实了这一点，所以角色用 Bash 做临时副本，就像 F04 试运行里的测试经理那样。

拒绝时，hook 告诉调用者路径、它的类别、调用者的写入范围，以及该怎么做："如果任务需要修改这个文件，就停下来报告 `needs-answer`。"

## 6. 通过 Bash 做的改动（D41）

F04 的试运行表明，开发工程师和测试工程师大多通过 Bash 的 heredoc 写文件。hook 无法从每条 shell 命令里读出写入目标，所以对角色，F05 改为比较工作区。

1. **开始。** 在 `SubagentStart` 时，hook 把角色开始时的状态记在 `<git dir>/troy-mode/agents/<agent_id>.json` 里：`git status --porcelain=v1 -z --untracked-files=all` 列出的每个路径，以及它内容的 SHA-256 哈希。如果这份记录不存在，就在角色第一次 `PreToolUse` 调用时生成。
2. **每次 shell 或技能调用之后。** 在 `Bash`、`PowerShell` 和 `Skill` 的 `PostToolUse` 时，hook 再拍一次同样的快照。一个路径在列表里是新的、从列表里消失了，或者哈希不同，就算改动过。改动过的路径如果在角色范围之外（第 5 节），hook 就回答 `decision: "block"`，列出这些路径和恢复方法：已跟踪的文件用 `git restore -- <path>`，角色新建的文件就删掉。命令已经执行了，所以这是反馈，不是阻止。
3. **结束时。** 在 `SubagentStop` 时，hook 再检查一次。如果还有范围之外的改动，并且 `stop_hook_active` 是 false，它就用同样的列表拦住这次停止，让角色撤销这些改动。如果 `stop_hook_active` 是 true，说明角色已经有过一次机会：hook 让它停止，把路径记进日志，由 F07 在运行后的检查中停下整个流程。最后它把这份记录标为已停止并保留下来（第 6.1 节）。

`Skill` 在 `PostToolUse` 的匹配条件里，是因为分叉的技能（比如 `/code-review`）工作时角色在等待。分叉自己的改动就会算在角色头上。

- **前提。** 角色运行期间，没有别的东西修改工作区。F07 一次只运行一个写文件的角色，并等它结束（F04 第 9.2 节）。如果有别的东西写了文件，hook 会算在角色头上，这样出错的方向是安全的。试点中，早先一个角色留在后台运行的命令打破了这个前提。第 6.1 节守住它。
- **其他子代理没有变更检测。** 它们可能在后台和主会话同时运行，主会话自己的修改就会被算到它们头上。它们只有每次调用之前的检查。
- **看不到的。** Bash 在仓库外的写入，以及 `.git` 文件夹里的改动。
- **代价。** 角色每次 shell 调用，一次 `git status` 加上改动文件的哈希：在 Troy 的电脑上，小项目大约 50 毫秒。

### 6.1 角色留在后台运行的工作（D231，D232）

**试点表明了什么。** tstack issue #49 说 `ZJUCao/recipe-menu#12` 的一次开发工程师运行在后台卡了 11.5 小时。它的会话记录表明，这次运行本身 3 分钟就结束了。它的一条命令，一个 `python -` heredoc，超过了 Bash 工具的 120 秒时限，Claude Code 没有停掉它，而是把它转到了后台。开发工程师想停掉它，但子代理没有 `TaskStop` 工具（"No such tool available"）。它报告之后，主会话继续往下走。11.5 小时后这条命令结束，在 F03 的测试工程师运行期间写入了它的旧修改，33 行重复代码，`check-run` 把这算到了测试工程师头上。2026-11-13 的两个 Python 进程也是这样来的：测试工程师的命令被转到后台，在报告之后约 40 分钟自己结束。

在 `ZJUCao/recipe-menu` 的三份会话记录里，331 次角色运行中有 52 次有命令被转到后台，大多是因为 120 秒时限，其中 19 次在角色报告时命令还在运行。当前的 CLI 也还会这样。2026-11-21，用 Claude Code 2.1.328 时，一个测试经理卡住的命令在它报告后又运行了 2 小时。权限分类器拒绝了测试经理的 `taskkill`（"Destructive or Unwanted Actions"），主会话也没有停掉这个任务。命令结束时，Claude Code 唤醒了测试经理。F05 的 `SubagentStart` hook 重新记录了工作区，而这时工作区里已有正在运行的开发工程师的修改；到测试经理再次停止时，`SubagentStop` hook 让它对开发工程师的三个文件执行 `git restore`。测试经理拒绝了。

**Claude Code 怎样做。** 依据试点的桌面应用会话记录，以及 2026-11-21 用自带 CLI 2.1.328 在嵌套 `claude -p` 会话里做的探测。探测在一个临时 git 项目里进行，用一个记录每次 hook 输入的插件和一个 haiku 工作代理，花费 $0.09。

| 事实 | 依据 |
| --- | --- |
| 桌面应用里，Agent 工具没有 `run_in_background` 参数，每个角色都作为后台代理运行。用 `claude -p` 时有这个参数。 | `ZJUCao/recipe-menu` 会话记录里 331 次角色调用中有 327 次，CLI 2.1.317 到 2.1.328，返回"Async agent launched"；另外 4 次在记录里没有结果。探测 1。 |
| 超过 Bash 工具时限的命令被转到后台，成为一个带 ID 的任务。这时 `PostToolUse` 输入里有 `tool_response.backgroundTaskId` 和 `timedOutAfterMs`。 | 探测 1 |
| `SubagentStop` 和 `Stop` 的输入列出会话里正在运行的 `background_tasks`：`id`、`type`（`subagent` 或 `shell`）、`status`，以及 shell 的 `command`。它们不说明 shell 是哪个代理启动的。 | 探测 1 和 A |
| 子代理给出最终回复之后，它的命令继续运行。命令结束时，Claude Code 唤醒这个子代理：`SubagentStart` 和 `SubagentStop` 以同一个 `agent_id` 再次触发。 | 探测 A；试点 2026-11-11 和 2026-11-21 |
| 子代理只有在工具里有 `TaskStop` 时才能停掉自己的命令。这时，点名该任务的 `SubagentStop` 拦截会让它这样做。 | 探测 F 和 G；试点 2026-11-10 |
| 主会话用命令的任务 ID 调用 `TaskStop`，会结束这条命令及其子进程，并唤醒子代理。用子代理的代理 ID 调用，会结束子代理和它的命令，不唤醒它。 | 探测 B 和 C |
| 会话退出时，Claude Code 结束它的后台命令及其子进程。 | 探测 D |
| 桌面应用会告诉主会话："This agent stopped with background work of its own still running. It may resume on its own when that work completes or reports"。 | 上面那 19 次角色运行的通知 |
| 设置 `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` 后，Agent 工具在前台运行子代理，超过时限的命令被停掉（退出码 143），而不是转到后台。没有在桌面应用里试过。 | 探测 E |
| 用 `claude -p` 时，后台命令 10 分钟后被停掉。桌面应用没有表现出这样的上限：有一条运行了 2 小时。 | 探测 1；试点 2026-11-21 |

所以 issue 提出的第一种修法，让角色在前台运行，在 troy-mode 所在的桌面应用里做不到。现在的记录也分辨不出角色的工作是否还在运行。hook 在角色第一次停止时就删除它的记录，所以试点里遗留的命令根本没有记录。被用量上限或关闭的会话结束的角色，即使什么也没在运行，也会把记录保留一天。也不需要列出进程：Claude Code 把每条这样的命令当作任务来跟踪，并把它的 ID 交给 hook。

**记录（D231）。** `<git dir>/troy-mode/agents/<agent_id>.json` 除了第 6 节的开始状态，还保存：

| 字段 | 含义 |
| --- | --- |
| `session` | `SubagentStart` 的 `session_id`，也就是主会话的。 |
| `started` | 记录生成的时间，UTC。 |
| `stopped` | 角色最终停止的时间；运行期间为 null。 |
| `background` | 角色被 Claude Code 转到后台、可能仍在运行的命令的任务 ID。 |

只要 `stopped` 为 null，或者 `background` 里还有任务，记录就是**未关闭**的。没有这些字段的记录，由旧版插件写入，算作已关闭。

**hook（D231）。**

1. **命令转到后台。** 在角色 `Bash` 或 `PowerShell` 的 `PostToolUse` 时，hook 把 `tool_response.backgroundTaskId` 加进 `background`。带 `run_in_background` 的调用应该以同样方式报告它的任务；探测没有试过，由构建时的试运行核实（第 13.3 节）。hook 还用 `additionalContext` 告诉角色："troy-mode: this command now runs in the background as task <ID>. You cannot stop it, and the main session stops it after your report, so do not wait for its result. Say in your report what you could not check."
2. **角色停止。** 当 `SubagentStop` 让角色停止时（第 6 节第 3 步），hook 设置 `stopped`，并且 `background` 里只保留输入的 `background_tasks` 列为正在运行的 shell 的任务。如果还剩任务，它写一行日志，规则为 `background`，决定为 `stop`，任务 ID 放在 `tasks` 里（第 10 节）。它不再删除记录。
3. **主会话停止一个任务。** 在主会话 `TaskStop` 的 `PreToolUse` 时，如果 `task_id` 是某份记录的代理 ID，就关闭这份记录：hook 设置 `stopped`，清空 `background`。如果 `task_id` 在某份记录的 `background` 里，就把它从中删除。hook 什么也不输出，所以调用照常进行。因为 hook 在调用之前关闭记录，所以对一个已不在运行的任务调用 `TaskStop`，即使失败，也能清除过期的记录。
4. **会话结束。** `SessionEnd` 关闭 `session` 等于正在结束的会话的每份记录，因为 Claude Code 退出时会结束会话的后台命令（探测 D）。
5. **一天的上限。** `SessionStart` 仍然删除一天前的记录（第 10 节）。

**已经停止的角色（D232）。** 当 Claude Code 唤醒一个记录已停止的角色时：

- `SubagentStart` 让它的记录保持原样。
- `PreToolUse` 以规则 `stopped` 拒绝它的每次调用（`Bash`、`PowerShell`、`Edit`、`Write`、`NotebookEdit` 和 `Skill`）："Your run has ended and your report was delivered. Do nothing more, and end your turn."
- `SubagentStop` 不做变更检测，也从不拦截，只按输入更新 `background`。

它的读取（`Read`、`Glob` 和 `Grep`）不被拒绝，因为它们不改动任何东西。troy-mode 从不给已停止的角色发新消息：修改是一次新的运行（F07 第 6.1 节）。

**F07 的部分。** `check-run` 和 `snapshot` 读取这些记录（F07 第 7 节）。只要这次运行的角色有未关闭的记录，`check-run` 就拒绝；只要有任何未关闭的记录，`snapshot` 就拒绝。两者都列出代理 ID，入口技能用 `TaskStop` 逐一结束它们。探测 C 表明，这样会结束角色的命令而不唤醒角色。在角色考试里，`check-run` 在角色的会话退出之后才运行，那时 `SessionEnd` 已经关闭了它的记录，所以这个新问题永远不会改变 U2 的评分（F16 第 4.3 节）。

**角色考试（F16）。** D231 每个选项改动 F16 指令集（F16 第 9.1 节）中的哪些文件，考试花多少钱。估算来自 `troy_exam.py` 自己的预算代码：`D:\Troy\troy-mode-work\cases\` 里记录的运行，没有记录的题用试点的中位数。没有运行任何考试。`main` 的指令哈希 `67c8098d051d` 没有记录过的基线运行，所以每次基线运行都要重新测。

| 选项 | 改动的指令集文件 | 要跑的题 | 估算 |
| --- | --- | --- | --- |
| A | 入口技能的"Running a role"一节 | 无：没有一道题的 Input 改变，所以 `affected` 找不到受影响的题（F16 第 9.2 节） | $0 |
| B | 同上。hook 和 `runs.py` 不在指令集里。 | 无 | $0 |
| C | B，再加上有 Bash 的五个角色的代理文件，它们的 `tools` 加上 `TaskStop`。如果加一条共用规则"报告前停掉你启动的每条命令"，还要改每个代理文件都复制的 `common.md`。 | 这五个角色的十道题；改 `common.md` 时是全部十二道 | $188.93；改 `common.md` 时 $258.73。超过 $60，所以先要 Troy 同意（F16 第 10.2 节）。 |
| D | 无：改的是 troy-init 的设置 | 无 | $0 |

改动 U5（D233）会改 `troy-mode/exam/troyexam/`，之后要重新证明每道题的锚点：估算 $40.00。tstack issue #64 同类的证明花了 $11.46。Troy 选了 B，并让 U5 仍是记录项，所以构建的角色考试不跑任何题。

**对其他功能的改动。** F07 的第 6.2 和 7 节，以及入口技能的"Running a role"一节（F07 设计 1.10 版）。F10 的指南：参考部分里"有文件被改了，但没有正在运行的角色在处理它"那一行，改为 `check-run` 的 `running` 问题。troy-init 和项目里的文件不变：hook 和记录属于插件和 git 文件夹。

**不覆盖的。**

- 离开 Claude Code 进程树的进程，比如通过 `start`、`Start-Process` 或 `setsid` 启动的。会话退出不会结束它，也没有记录提到它。F16 的 U5 在考试中报告这样的进程（F16 第 4.3 节，D233）。
- 其他子代理的后台命令，比如 `/code-review` 的分叉。它们没有记录（第 4 节）。
- 没有经过 `SessionEnd` 就结束的 Claude Code 进程，比如被强制结束的。它的记录保持未关闭，直到 `TaskStop` 或一天的上限把它清除。

## 7. 子代理的 git、GitHub 和技能（D43）

### 7.1 读懂一条命令

对 `Bash` 和 `PowerShell`，hook 把命令拆成简单命令：

- 在 `;`、`&&`、`||`、`|`、`&`、换行和括号处拆开，把 `$(...)` 和反引号当作独立的命令。
- 把 `bash -c`、`sh -c` 和 `eval` 后面的字符串当作命令读。
- 跳过开头的变量赋值，以及包装命令 `command`、`env`、`exec`、`nohup`、`time`、`timeout` 和 `xargs`，连同它们的选项。`timeout` 还要去掉它的时长，即选项之后的第一个词。经过 `xargs` 的命令会被标记出来，因为 `xargs` 会给它加上词（第 8.3 节）。
- 因为 `timeout` 是包装命令（D223），第 7.2 节和第 8.2 节的检查把 `timeout 60 git push` 看作 `git push`。以前 `timeout` 会把这条 git 命令藏起来。
- 丢掉每个 heredoc 的正文，所以正在写入的文件里出现"git commit"这样的文字，不算命令。
- 记住每个 `cd <literal path>`，用于它后面的命令。路径也可以来自同一条命令里前面设置的变量，只要它被设成字面路径，或者设成 `mktemp -d` 建的文件夹。F05 试运行里，测试经理用 `DST=$(mktemp -d <temp folder>/name-XXXXXX)` 和 `cd "$DST"` 做了临时副本。其他变量一律当作未知，在未知文件夹里运行的 git 命令按在项目里运行处理。
- `git`、`git.exe` 以及以它们结尾的路径都按 git 读，`gh` 也一样。

如果命令拆不开，比如引号不成对，那么只要子代理调用的文本里任何地方匹配 git 写操作或 `gh` 写操作，就拒绝。PowerShell 的语法用同样的方法尽力去读。

### 7.2 git

子代理可以运行这些 git 命令：

| 类型 | 命令 |
| --- | --- |
| 始终允许 | `status`、`diff`、`log`、`show`、`blame`、`grep`、`rev-parse`、`rev-list`、`ls-files`、`ls-tree`、`cat-file`、`merge-base`、`describe`、`shortlog`、`for-each-ref`、`show-ref`、`name-rev`、`check-ignore`、`check-attr`、`var`、`diff-tree`、`diff-index`、`diff-files`、`count-objects`、`archive`、`fetch`、`ls-remote`、`version`、`help` |
| 只允许列出的形式 | 不创建名字的 `branch` 和 `tag`；不带子命令或带 `-v`、`get-url`、`show` 的 `remote`；带 `--get`、`--get-all`、`--get-regexp`、`--list`，或者只有一个键、没有值的 `config`；`stash list` 和 `stash show`；`worktree list`；`reflog` 和 `reflog show` |
| 只改工作区 | 不带 `--staged`、`-S`、`--source` 或 `-s` 的 `restore`。角色用它撤销范围之外的改动（第 6 节）。 |

- 其他 git 命令一律拒绝：`commit`、`push`、`add`、`rm`、`mv`、`reset`、会改动内容的 `stash`、`switch`、`checkout`、`merge`、`rebase`、`cherry-pick`、`revert`、`am`、`apply`、`clean`、创建或删除的 `tag` 和 `branch`、设置值的 `config`、`worktree add`、`update-ref` 等等。拒绝时引用共用规则第 6 条：由主会话提交、开 PR、发布审查意见。
- **临时仓库。** 如果一条 git 命令的仓库在临时文件夹或 scratchpad 里（由 `-C`、`--git-dir`、`--work-tree`、`GIT_DIR`、`GIT_WORK_TREE` 或前面的 `cd` 指定，路径都要是第 7.1 节能跟踪的），它除了 `push` 什么都可以做。这样测试经理可以提交一个临时副本，在上面运行 `troy-check code` 来检查 R09。项目的克隆可以推送回项目，所以 `push` 仍然拒绝。
- 子命令前面的全局选项，比如 `-C`、`-c`、`--no-pager` 和 `--git-dir`，会被读取并跳过。`-c core.hooksPath=...` 对所有调用者都拒绝（第 8.2 节）。

### 7.3 GitHub CLI

子代理可以运行 `gh pr view`、`gh pr diff`、`gh pr list`、`gh pr checks`、`gh pr status`、`gh issue view`、`gh issue list`、`gh issue status`、`gh repo view`、`gh run view`、`gh run list`、`gh release view`、`gh release list`、`gh search`、`gh status`、`gh auth status`，以及方法只能是 `GET`、不带 `-f`、`-F`、`--field`、`--raw-field` 或 `--input` 的 `gh api`。其他 `gh` 命令一律拒绝。

### 7.4 技能

子代理的 `Skill` 调用只允许 `code-review` 和 `security-review`（带不带插件前缀都行），而且参数里既不能有 `--fix` 也不能有 `--comment`。这样就执行了 F04 的 D36：代码审查员只审查，不修改任何东西。`Skill` 的输入字段名没有文档说明。试运行（第 13.3 节）表明：`skill` 是技能名，`args` 是参数，没有参数时不出现。

## 8. R19、R21 和 R23（D44、D223）

### 8.1 git hook

| git hook | 规则 | 拒绝 |
| --- | --- | --- |
| `commit-msg` | R19 | `troy_check.py commit --message-file "$1"` 不通过的提交信息或作者邮箱（F02 设计 3.2）。它运行项目自己的 troy-check 副本，用项目的署名模式。 |
| `pre-commit` | R21 | 当前分支是 `main` 时的提交。 |
| `pre-merge-commit` | R21 | 当前分支是 `main` 时的合并提交。 |
| `pre-push` | R21 | 更新或删除远程 `refs/heads/main` 的推送，从 git 在标准输入上给出的各行读取。 |

- 它们作用于这个克隆里的每一次提交，包括 Troy 自己在终端里做的。Troy 仍然可以用 `--no-verify` 跳过它们，Claude 不能（第 8.2 节）。
- `commit-msg` 找不到 Python 3.11 或更新版本时拒绝提交，因为那样就无法检查 R19。
- **打开它们。** `core.hooksPath` 是 `.troy-mode/checks/git-hooks` 时，git 才运行它们。troy-init 在初始化时设置它（F06）。新克隆的仓库没有这个设置，所以 `SessionStart` hook 在它未设置时设置它，并在 `additionalContext` 里告诉 Claude。如果它是别的值，hook 不动它，只告诉 Claude troy-mode 的 git hook 没有打开。
- 在 `main` 上的分离 `HEAD`、rebase 和 cherry-pick 不会运行 `pre-commit`。`pre-push` 仍然阻止它们到达 `main`。Troy 的 GitHub 套餐没有分支保护（F02 D14），所以 `pre-push` 是本地最后一道关，CI 是最后一道关。

### 8.2 Claude Code 防护

对 troy-mode 项目里的每个调用者，包括主会话，`PreToolUse` hook 拒绝：

- 带 `--no-verify` 或 `-n` 的 `git commit`，以及带 `--no-verify` 的 `git push`、`git merge`、`git am` 或 `git rebase`。`git push -n` 是试运行，仍然允许。
- 任何 git 子命令前的 `-c core.hooksPath=...`，以及设置或取消 `core.hooksPath` 的 `git config`。
- `core.hooksPath` 不是 `.troy-mode/checks/git-hooks` 或者 hook 文件缺失时的 `git commit`、`git merge` 和 `git push`。原因里会说明怎样打开它们。
- 从 `main` 发出的 `gh pr create`：带 `--head main` 或 `-H main`，或者没有 `--head` 而当前分支是 `main`（R21）。
对主会话，同一个 hook 在每条向 GitHub 发文字的 `gh` 命令运行前检查它的文字（R19，D200）。子代理的每个 `gh` 写操作仍然一律拒绝（第 7.3 节）。

| 命令 | 读取的文字 |
| --- | --- |
| `gh pr create`、`gh pr edit`、`gh issue create`、`gh issue edit` | `--title`/`-t`、`--body`/`-b`、`--body-file`/`-F` |
| `gh pr comment`、`gh issue comment`、`gh pr review` | `--body`/`-b`、`--body-file`/`-F` |
| `gh pr merge` | `--subject`/`-t`、`--body`/`-b`、`--body-file`/`-F` |
| `gh release create`、`gh release edit` | `--title`/`-t`、`--notes`/`-n`、`--notes-file`/`-F` |
| 方法不是 `GET` 或带字段的 `gh api` | `-f`/`--raw-field` 和 `-F`/`--field` 的值、`-F key=@file` 指定的文件，以及 `--input` 文件 |

- **检查什么。** 每个选项都认 `--x v`、`--x=v`、`-x v` 和 `-xv` 几种写法。检查的文字是选项的值、这次调用里的每个 heredoc，以及每个指定文件的内容，文件按命令运行所在的文件夹解析。`troycheck.attribution.find_attribution` 按项目 `HEAD` 上提交的 `[attribution] mode` 检查，和 `check-text` 一样。没有文字要发的 `gh` 命令，比如 `gh pr merge --rebase` 或 `gh pr review --approve`，直接通过。发往另一个仓库（`--repo`）的命令同样检查。
- **拒绝。** 规则为 `attribution`。原因里写明 R19、命令和第一行不通过的文字。日志行只记命令名，比如 `gh pr comment`，从不记文字或文件路径（第 10 节）。
- **失败即拒绝。** 以下发文字的命令也以规则 `attribution` 拒绝：
  - 正文、发布说明或输入文件不存在或读不了，或者由 hook 解析不了的词指定（未知变量，或在 hook 跟不上的 `cd` 之后的相对路径）；
  - 用了 `--body-file -`、`--notes-file -`、`--input -` 或 `-F key=@-`，而调用里没有 heredoc，因为管道里的文字 hook 看不到；
  - 用了 `--editor`/`-e` 或 `--web`/`-w`，因为文字会写在 hook 看不到的地方；
  - 文字选项里有未知变量，或者不是对 heredoc 做 `cat` 的命令替换，比如 `--body "$(cat c.md)"`，因为这样的文字 hook 也看不到。

  主会话的调用拆不开、而文本里有发文字的 `gh` 命令时，以规则 `unparsed` 拒绝（第 7.1 节）。检查发文字的命令时出错，以规则 `error` 拒绝（第 10 节）。
- **从不扫描路径。** hook 从不扫描文件路径或整条命令行：临时目录的路径本身可能含有 strict 模式拒绝的词，扫描路径会拒绝从那里发出的每一条。
- **已知限制。** 文件按调用开始时的样子检查。同一行里先改写正文文件再发出的调用，按旧文字检查；文件那时还不存在则拒绝。troy-mode 技能要求在更早的一次调用里写好文件。hook 不把 heredoc 和它喂给的命令对应起来，所以同一次调用里另有 heredoc 时，通过管道进 `--body-file -` 的文字会放行，而那个 heredoc 会被检查。带字段的 `gh api -X GET` 按表格算作发文字。
- 这样在 PR 出现之前就能拦住"Generated with Claude Code"那一行，也能拦住 #92 那种 `check-text` 失败后仍发出的评论，赶在 GitHub 保存文字和编辑历史之前。

### 8.3 从标准输入读取程序的 Python（R23，D223）

在 troy-mode 项目里，对每个调用方，包括主会话，`PreToolUse` hook 拒绝运行这样一条 `Bash` 或 `PowerShell` 命令：它运行的 Python 从标准输入读取程序。这样的运行可能卡在 Python 的交互提示符上，直到碰到 shell 工具的时限。在 `ZJUCao/recipe-menu` 的两份会话记录里，有 168 次 Python 运行从标准输入读取程序，其中 39 次碰到了 120 秒的时限。标准输入什么都没有或来自 `/dev/null` 的此类运行，每一次都卡住了，而每份 brief 里的警告都没能防住（tstack issue #64）。

**哪些程序。** 经过第 7.1 节的拆包后，程序是 `python`、`python3`、`python3.N` 或 `py` 的简单命令，带不带路径和 `.exe` 都算。先去掉运行器 `mamba run`、`micromamba run`、`conda run`、`uv run` 和 `pixi run` 及其选项，再检查它们后面的程序。程序放在第 7.1 节解析不出的变量里时，不检查。

**参数，从左往右读：**

| 参数 | 结果 |
| --- | --- |
| `-`，或 `--` 后面跟着 `-` | 拒绝，算作 `python -` |
| `-i`，单独出现或在 `-ui` 这样的选项组里 | 拒绝，算作 `python -i` |
| `-c` 或 `-m`，单独出现、在 `-Bc` 这样的选项组里，或像 `-mpytest` 这样连着值 | 允许 |
| `-W`、`-X` 或 `--check-hash-based-pycs` | 连同它的值一起跳过：值是这个词剩下的部分，比如 `-Xutf8`，否则是下一个词 |
| `-V`、`--version`、`-h`、`-?`，或以 `--help` 开头的选项 | 允许 |
| 其他选项 | 跳过 |
| 第一个不是选项的词 | 脚本：允许 |
| 读到最后，以上都没有 | 拒绝，算作没有脚本的 `python`，除非命令经过 `xargs`，因为 `xargs` 会给它加上自己的词 |

- 选项组逐个字母从左往右读，每个字母按同名的选项处理，`c`、`m`、`W` 或 `X` 之后的字母是这个选项的值。所以 `-ic` 拒绝，因为 `i` 在前；`-ci` 允许，因为它运行的是程序 `i`；`-VV` 允许。
- `--` 结束选项：它后面的词是脚本。所以 `python -- x.py` 允许，单独的 `python --` 拒绝。
- 对 `py`，第一个参数可以是启动器自己的选项。`-0`、`-0p`、`--list` 和 `--list-paths` 允许，`-3`、`-3.13`、`-3.13-64` 或 `-V:3.13` 这样的版本选择跳过。
- 标准输入来自哪里无关紧要：heredoc、管道、`/dev/null`、文件，或者什么都没有。检查看的是程序从哪里来，而且只需要词，所以解析时丢掉的重定向不改变结果。带脚本文件、`-c` 或 `-m` 的 Python 仍然可以从管道或 `/dev/null` 读取数据。会话记录里 257 次这样的运行没有一次卡住，主会话就是这样用 `| python -X utf8 -c "..."` 读取 `troy_flow.py` 的输出的。
- heredoc 正文里的文字，比如正在写入的文件里的 `python -`，不算命令（第 7.1 节）。
- 拆不开的命令（第 7.1 节）不做 R23 检查。

**拒绝。** 规则 `python-stdin`，决定 `deny`。理由：

```text
R23: `python -` makes Python read its program from standard input, and such a run can hang at Python's interactive prompt. Write the script to a file in the scratchpad (<scratchpad folder>) and run that file with the project's Python (`[lang] environment` <name>), for example `python -X utf8 <file>`. Python with a script file, `-c`, or `-m` may still read data from a pipe or `/dev/null`.
```

- 理由里写的形式是 `python -`、`python -i`，或没有脚本的 `python`，不管程序本身叫什么、路径是什么。一行里有几条这样的命令时，只写第一条。同一行里被拒绝的 git 或 `gh` 命令保留各自的理由，按命令在行里的顺序排列，第一个拒绝决定日志行的规则。
- hook 输入给了 `scratchpad_dir` 时，写出 scratchpad 的文件夹；`HEAD` 上的配置设了 `[lang] environment` 时，写出环境名。否则省掉相应括号里的部分。配置读不了只会省掉环境名：命令仍然被拒绝。
- 日志行记录规则和决定，没有子命令，也从不记录命令文本（第 10 节）。
- 插件一更新，拒绝就开始生效，早于 troy-init 的升级把 R23 加进项目的规则表，所以理由本身就要讲清楚。

**看不到的。** CI、git hook、`hooks.json` 自己的命令，以及测试里的子进程调用都不经过 Bash 工具，所以 hook 永远看不到它们。现有项目的文件里没有这样的命令（`ZJUCao/recipe-menu`：没有），所以 R23 不需要基线，也不需要清理。

## 9. 插件文件（D45）

F04 的试运行表明，在没人能批准权限提示的会话里，角色读不了插件自己的文件，比如 `skills/technical-writing/SKILL.md`。而 Troy 也会在每次这样的读取时看到一个提示。

`Read`、`Glob` 和 `Grep` 上的 `PreToolUse` hook，在调用位于 troy-mode 项目、路径在 `CLAUDE_PLUGIN_ROOT`（Claude Code 导出给插件 hook 的环境变量）之内时，回答 `allow`。对其他路径或项目，它什么也不输出。

- `if` 规则 `Read(//**/troy-pstack/**)` 让 hook 在读取别处时不启动。它既匹配安装好的插件（`~/.claude/plugins/cache/<marketplace>/troy-pstack/<version>/`），也匹配用 `--plugin-dir` 加载的代码目录。
- 试运行表明，这条规则只过滤 `Read`。把 `Read|Glob|Grep` 放在同一个 `if` 下时，插件文件夹里的 `Glob` 和 `Grep` 调用根本没有到达 hook，Claude Code 因为缺少权限拒绝了它们。所以按本节原来的计划，`Glob` 和 `Grep` 不带 `if` 直接运行 hook，每次付出门槛的开销（第 10 节）。
- 安装路径随每个插件版本变化。hook 每次都读 `CLAUDE_PLUGIN_ROOT`，所以不需要更新。
- 因此 troy-init（F06）不写任何权限规则。

## 10. 错误、速度和日志

**错误（D39）。** `troy_hook.py` 里的任何错误，比如配置读不了或 git 失败，都会被捕获。对角色或其他子代理，调用被拒绝，并附上错误。对主会话，hook 在 stderr 上输出一条提示，以退出码 1 退出，Claude Code 把它当作不阻断的错误，所以主会话仍然可以修复项目。有一个例外（D200）：检查发文字的 `gh` 命令（第 8.2 节）时出错，比如配置无效，主会话的调用以规则 `error` 拒绝，因为发到 GitHub 的文字会保留编辑历史。主会话的其他调用仍然只给警告。`SessionStart` 不把无效的配置当作错误：它保留每一行日志，打开 git hook，并以退出码 0 结束（D219，见下文日志一段）。没有 Python 3.11 或更新版本时，在 troy-mode 项目里拦住调用，在别处放行：解释器缺失时，`hooks.json` 的命令用 shell 内置命令检查 `$CLAUDE_PROJECT_DIR/.troy-mode`，以退出码 2 或 0 退出；`troy_hook.py` 在导入其他任何东西之前先检查版本。不使用 `onFailure: "block"`，因为它在 troy-mode 项目之外也会拦住调用。

**速度。** 2026-11-06 在 Troy 的电脑上测得：Python 启动 40 到 65 毫秒，bash 大约 25 毫秒，一条 git 命令 40 到 50 毫秒。

| 调用 | 工作 | 估计 |
| --- | --- | --- |
| troy-mode 之外的任何项目 | bash、Python、门槛 | 70 到 90 毫秒 |
| 角色的 `Write` 或 `Edit` | 再加上读取 `HEAD` 的配置，对范围外的路径还有 `git check-ignore` | 120 到 170 毫秒 |
| 角色的 shell 调用结束后 | 再加上 `git status` 和哈希 | 120 到 170 毫秒 |
| 用 `Read` 读取 `troy-pstack` 文件夹以外的文件 | 无。`if` 规则跳过这个 hook。 | 0 毫秒 |
| 任何地方的 `Glob` 或 `Grep` | bash、Python、门槛和插件路径判断 | 70 到 90 毫秒 |

都在需求文档第 8 节 200 毫秒的目标之内。hook 把配置的文本存在 git 文件夹里，以 `HEAD` 的提交 ID 为键，所以大多数调用不用启动 git 进程就能读到它。试运行把每类 hook 各测了 20 次：中位数在 74 到 151 毫秒之间（表格见 F05 的 PR）。

**日志。** 每次拒绝和拦截都在 `<git dir>/troy-mode/hooks.log` 里追加一行 JSON：时间、会话、代理 ID、代理类型、事件、工具、规则、路径或 git 子命令、决定。它从不记录命令行或文件内容，所以命令里输入的机密不会进入日志。R23 的拒绝（第 8.3 节）规则是 `python-stdin`，没有子命令。角色停止时还有命令在后台运行，会得到一行规则为 `background`、决定为 `stop` 的日志，任务 ID 放在 `tasks` 字段里，从不记录命令文本；已经停止的角色的调用以规则 `stopped` 拒绝（第 6.1 节）。git 文件夹永远不会被提交。F07 在每次角色运行后读取日志（第 12 节）。

**日志保留多久（D219）。** F08 的回顾（`retro --tag`，F08 第 7 节）统计上一个版本标签以来的日志行，而一个版本可能持续很多天：试点里用了六天。所以 `SessionStart` 按项目配置里设定的天数保留日志行：

```toml
[hooks]
log_days = 30   # hooks.log 保留日志行的天数
```

- **取值。** `.troy-mode/config.toml` 里的 `[hooks] log_days`，和 hook 读取的其他配置一样，读 `HEAD` 上已提交的版本（第 5.2 节）。它是 1 或更大的整数；这个键、这个表或整个文件不存在时为 30。`[hooks]` 没有别的键。
- **错误的值。** `log_days` 为 0、小于 0、`true` 或 `false`、小数或字符串，都是配置错误；`[hooks]` 里未知的键也是。troy-check 和遇到其他配置错误时一样以退出码 2 停止（F02 第 7 节），角色的 hook 调用被拒绝（第 10 节，D39）。
- **删除哪些行。** 每次 `SessionStart` 时，`time` 早于现在 `log_days` 乘 24 小时以上的行被删除。正好 `log_days` 天的行保留。读不出时间的行和以前一样被删除。其余的行按原来的顺序保留。
- **角色记录。** 第 6 节的记录仍然在文件超过一天时删除，不管 `log_days` 是多少。
- **配置无效时。** `SessionStart` 不删除任何日志行，仍然删除旧的角色记录，仍然打开 git hook（第 8.1 节），并以退出码 0 结束。它的 `additionalContext` 说明已提交的配置无效、`hooks.log` 没有清理。所以坏掉的配置既不会让日志丢行，也不会让 git hook 打不开。

一个版本持续的时间超过 `log_days` 时，回顾看不到它最早的那些行；这时项目在一个 `[rules]` PR 里调大 `log_days`。日志每次拒绝只有一短行，不含文字（见上文），所以 30 天的日志也很小。

## 11. F05 怎样对应需求

| 需求 | F05 在哪里覆盖 |
| --- | --- |
| F05 一行：标记文件夹门槛 | 第 4 节，门槛 |
| F05 一行和 F04 D31：每个角色的写入范围，包括 R08 | 第 5 节和第 6 节 |
| F05 一行和 F04 D31：角色不做 git 和 GitHub 写操作 | 第 7 节 |
| F05 一行：违反 R19 的提交 | 第 8.1 节（`commit-msg`）和第 8.2 节（PR 标题和描述） |
| 第 6 节 R19：PR 评论和评审、issue 以及发布说明在发出前检查（D200） | 第 8.2 节（每条发文字的 `gh` 命令）和第 10 节（出错时拒绝发出） |
| F05 一行：在 `main` 上提交和推送 `main`（R21） | 第 8.1 节（`pre-commit`、`pre-merge-commit`、`pre-push`），以及第 8.2 节的 `gh pr create` |
| 第 6 节 R23 和 F05 一行：Python 永远不从标准输入读取程序（D223） | 第 8.3 节，对每个调用方；`timeout` 和 `xargs` 见第 7.1 节 |
| F05 一行，按 D231 和 D232 修改后：角色留在后台运行的命令，以及已经停止的角色 | 第 6.1 节 |
| 第 8 节，hook 在 troy-mode 项目之外立即退出 | 第 4 节的门槛，以及第 9 节的 `if` 规则 |
| 第 8 节，每次调用低于 200 毫秒 | 第 10 节 |
| 第 8 节，隐私 | 日志不记录命令行（第 10 节） |
| 第 8 节，新名字以 `troy-` 开头 | 第 2 节。`hooks.json` 和 git hook 的名字由 Claude Code 和 git 规定 |
| F04 D36，代码审查员从不运行 `--fix` 或 `--comment` | 第 7.4 节 |

## 12. F06 和 F07 怎样使用 F05

**F06。** troy-init 把 troy-check 的文件夹（包括 `git-hooks/`）复制进 `.troy-mode/checks/`，并在初始化时设置 `core.hooksPath`。它不为插件文件写任何权限规则（第 9 节）。

**F07。**

- 它一次只运行一个写文件的角色，并等它结束，这样第 6 节才能把改动算到正确的角色头上。
- 它在暂存这次运行的改动之前、在下一次运行之前，结束角色遗留的工作：只要角色的记录未关闭，`check-run` 和 `snapshot` 就拒绝，技能用 `TaskStop` 停掉每个列出的代理（第 6.1 节，D231）。
- 每次运行后，它保留自己的 `git status` 检查（F04 第 9.2 节）作为最后防线，再加上检查 `HEAD` 和分支没有变，并读取 `hooks.log` 里这个角色的记录。角色留在范围之外的路径会停下整个流程。
- 它在主会话里提交、推送、开 PR，所以第 8.1 节的 git hook 会检查它做的每一次提交和推送。
- **troy-check code。** 它只读提交，而角色不能提交（第 7 节），所以开发工程师在 DV2 里运行 `troy-check code` 时，检查的是上一个提交，而不是它自己的工作。F04 的试运行表明了这一点。F07 要在提交后再运行它，或者让 troy-check 增加一种检查工作区的模式。这属于 F07 的设计。

## 13. F05 怎样检查

### 13.1 测试

测试使用 `unittest` 和标准库。按 troy-pstack 的构建流程，由一个单独的代理在 hook 写出来之前，根据本设计写测试。每个测试在临时文件夹里建一个小 git 仓库，通过 stdin 给 `troy_hook.py` 一份 hook 输入。测试放在 `troy-mode/hooks/tests/` 和 `troy-mode/checks/tests/test_git_hooks.py`。凡是修改 `hooks/`、`troy-mode/hooks/`、`troy-mode/checks/` 或 `agents/` 的 PR，`troy-checks-tests.yml` 都在 Linux 和 Windows 上运行它们。

| 组 | 用例包括 |
| --- | --- |
| 门槛 | 没有 `.troy-mode/`：每个事件都以 0 退出，什么也不输出。`cwd` 在 troy-mode 项目的子文件夹里。不是 git 仓库。 |
| 调用者 | 主会话、每个角色、未知的 `troy-pstack:troy-*` 名字、`general-purpose`、`Explore`。角色名前后多出文字就不算角色。 |
| 范围表 | 等于 F04 第 3 节，也等于每个代理文件的 Write scope 一节。 |
| 路径 | 每个角色对每个路径类别和模式。被忽略的路径允许。`.git/` 拒绝。临时文件夹和 scratchpad 允许，用户主目录拒绝。反斜杠、盘符大小写、Git Bash 路径和 `..`。未提交的配置修改不扩大范围。无效的配置拒绝角色的调用。 |
| 命令 | 每个允许的 git 和 `gh` 命令通过，每个拒绝的都被拒绝，无论单独出现，还是在 `;`、`&&`、`\|`、换行、`( )`、`$( )`、反引号、`bash -c` 里，或者前面有变量赋值或 `timeout`。含有"git commit"的 heredoc 通过，heredoc 写成脚本文件再运行时也一样。临时仓库：`git -C <temp> commit` 和 `cd <temp> && git commit` 通过，`git -C <temp> push` 拒绝。`gh api` 用 `GET` 通过，带 `-X POST` 或 `-f` 拒绝。引号不成对、包着 git 写操作的命令被拒绝。 |
| 技能 | `code-review` 通过，带 `--fix` 或 `--comment` 拒绝，其他技能拒绝。主会话可以运行任何技能。 |
| 改动 | 开发工程师通过 Bash 新建一个测试文件：`PostToolUse` 拦截并指出它。`git restore` 或删掉之后，不再拦截。原本已改动的文件再次改动，通过哈希发现。范围内的改动不报告。`SubagentStop` 拦一次，然后让角色停止。缺失的开始记录在第一次调用时生成。 |
| 防护 | `--no-verify` 和 `commit -n` 拒绝，`push -n` 通过。`-c core.hooksPath=` 和 `git config core.hooksPath` 拒绝。`core.hooksPath` 未设置时的提交拒绝。在 `main` 上和带 `--head main` 的 `gh pr create` 拒绝，在分支上通过。含有"Generated with Claude Code"的 PR 描述拒绝。`trailers` 模式下的 Claude 一词通过。 |
| 发文字防护（D200） | 第 8.2 节的每条发文字命令，用长、短和 `=` 写法，标题、正文、发布说明或文件有问题时拒绝，干净时通过；strict 模式拒绝的词在 `trailers` 模式下通过。#92 那种 `check-text ... \| grep -q ok; gh pr comment ...` 拒绝。stdin 上的 heredoc 被检查。来自管道的 `--body-file -` 拒绝。文件不存在拒绝。文件夹名是 strict 模式拒绝的词、里面的干净文件通过。`gh api -X POST` 带 `-f`、`-F key=@file` 或 `--input` 且文字有问题时拒绝，`GET` 通过。发往另一个仓库的 `gh issue create --repo` 也检查。`--editor` 和 `--web` 拒绝。`--body "$(cat <file>)"` 拒绝，`--body "$(cat <<'EOF' ...)"` 被检查。主会话拆不开的发文字调用拒绝。检查出错时拒绝发文字的命令，其他命令只警告。日志行只有命令名，没有文字。子代理仍然得到第 7.3 节的 `gh` 拒绝。 |
| 从标准输入读取的 Python（D223） | 第 8.3 节每种拒绝的形式（`python -`、`python3 -`、`python -- -`、`python -i x.py`、选项组里的 `-i`、没有脚本的 `python`、带值但没有脚本的 `-W` 和 `-X`，以及 `py -3.13 -`），对主会话、角色和其他子代理，也在 `&&`、`;`、`\|`、`$( )`、`bash -c`、`timeout`、`mamba run`、`uv run` 里，以及 PowerShell 的 `@'...'@ \| python -`。允许的：`python x.py < /dev/null`、`\| python -c "..."`、`python -m pytest`、`--version`、`py -0p`、`xargs python`，以及 heredoc 正文里作为文字的 `python -`。troy-mode 之外不输出。理由写出 R23、形式和改法，知道时还写出 scratchpad 和环境。日志行的规则是 `python-stdin`，决定是 `deny`，没有子命令，也没有命令文本。子代理的 `timeout 60 git push` 被拒绝。 |
| 后台工作（D231、D232） | 角色 `Bash` 和 `PowerShell` 的 `PostToolUse` 带 `tool_response.backgroundTaskId` 时，把任务加进 `background`，并用点名该任务的 `additionalContext` 回答。没有它时，记录不变。主会话和其他子代理的调用不记录任何东西。让角色停止的 `SubagentStop` 设置 `stopped`，只保留 `background_tasks` 列为正在运行的 shell 的任务，并写一行带任务 ID、不含命令文本的 `background` 日志。没有正在运行的任务时不写日志。被拦截的停止什么也不设置。已停止代理的 `SubagentStart` 让记录保持原样。已停止角色的 `Bash`、`PowerShell`、`Edit`、`Write`、`NotebookEdit` 和 `Skill` 调用以规则 `stopped` 拒绝，它的读取通过，它的停止不做变更检测、也从不拦截，即使工作区里有另一个角色的改动（2026-11-21 的情形）。主会话的 `TaskStop` 用代理 ID 时关闭那份记录，用任务 ID 时删除那个任务，用未知 ID 时什么也不改，每种情况都不输出任何东西。子代理的 `TaskStop` 不关闭任何记录。`SessionEnd` 只关闭正在结束的会话的记录。没有新字段的记录算作已关闭。`hooks.json` 的 `PreToolUse` 匹配条件里有 `TaskStop`，并有一项 `SessionEnd`。 |
| 插件文件 | troy-mode 项目里读取 `CLAUDE_PLUGIN_ROOT` 之内的文件得到 `allow`。之外的路径，或在别的项目里，什么也不输出。 |
| 错误和日志 | 异常会拒绝角色的调用，对主会话只给警告。每次拒绝写一行不含命令文本的日志。 |
| SessionStart | 未设置的 `core.hooksPath` 被设置。别的值保持不变并报告。hook 文件缺失会报告。旧记录被删除。 |
| 日志天数（D219） | 没有 `[hooks]` 表时，29 天的行保留，31 天的行删除。`log_days = 7` 时，差一小时满 7 天的行保留，超过一小时的行删除；`log_days = 1` 时，2 天的行删除。2 天的角色记录不管 `log_days` 是多少都被删除，一小时的记录保留。读不出时间的行被删除。保留的行顺序不变。未提交的 `log_days` 修改不会被读取。`log_days` 为 0、-1、`true`、1.5、`"30"`，以及 `[hooks]` 里未知的键，对 troy-check 都是配置错误；1 和 365 能解析。已提交的配置无效时，`SessionStart` 以退出码 0 结束，不删除日志行，删除旧记录，设置未设置的 `core.hooksPath`，并输出 `additionalContext`。`config.default.toml` 设置 `log_days = 30`。 |
| `hooks.json` | 能解析。事件、匹配条件和超时都和第 3 节一致，命令指向存在的脚本。 |
| git hook | 在设置了 `core.hooksPath` 的临时仓库里真实提交：在 `main` 上的提交拒绝，分支上的正常提交通过，署名 trailer 拒绝，错误的 `--author` 邮箱拒绝，在 `main` 上的合并提交拒绝。`pre-push` 直接运行，从 stdin 读入各行：更新或删除 `refs/heads/main` 拒绝，分支或标签通过。没有任何测试向 `main` 分支执行 `git push`，临时仓库也不例外。 |

### 13.2 埋 bug

代码通过后，在临时副本里一次埋一个 bug，每个都必须让某个测试失败。包括：开发工程师的范围里有 `tests` 类别、角色模式不锚定、不检查忽略、临时文件夹判断接受 `/tmp-other`、允许的 git 命令里有 `commit`、临时仓库判断接受项目本身、`pre-push` 读本地 ref 而不是远程 ref、出异常时放行角色的调用、`SubagentStop` 从不拦截、忽略 `stop_hook_active`、从工作区读配置，以及在 `CLAUDE_PLUGIN_ROOT` 之外放行插件读取。D200 的改动再加上：发文字命令表里漏了 `comment`、不读 `-F`、扫描路径而不是内容，以及放行不存在的文件。D219 的改动再加上：截止时间差一天、忽略默认值（只保留一天）、角色记录保留 `log_days` 天、接受为 0 的 `log_days`、从工作区读配置，以及配置无效时 `SessionStart` 在打开 git hook 之前就停下。D223 的改动再加上：漏掉 `python3 -`、漏掉 `--` `-` 的写法、漏掉选项组里的 `-i`、`-W` 不跳过它的值、`py -3.13` 不跳过、不拆 `timeout`、`xargs` 不豁免、不检查主会话，以及日志行带上命令文本。D231 和 D232 的改动再加上：漏掉 `PowerShell` 的 `backgroundTaskId`、记录主会话的命令、不读 `background_tasks` 就保留 `background`、被拦截的停止也设置 `stopped`、`SubagentStart` 覆盖已停止的记录、放过已停止角色的 `Bash`、对被唤醒角色的停止做变更检测、用代理 ID 调用 `TaskStop` 后记录仍未关闭、子代理的 `TaskStop` 关闭记录、`SessionEnd` 关闭别的会话的记录、没有新字段的记录算作未关闭，以及 `background` 日志行带上命令文本。数量写在 PR 描述里。

### 13.3 在示例项目上试运行

F05 的 PR 开出之前，hook 在嵌套的 `claude -p` 会话里运行，用的是 F03 Python 示例项目的一次性副本，troy-pstack 通过 `--plugin-dir` 从 PR 分支加载，使用 `acceptEdits` 模式，不给插件文件夹配 Read 规则。`build_sample.py` 增加把 `git-hooks/` 复制进示例项目的步骤，就像 troy-init 将来做的那样。主会话手写每份任务简报：

1. **探测。** 给开发工程师一份简报，列出要逐个尝试并报告结果的动作：用 Write 写一个测试文件、用 Bash heredoc 写一个、`git commit`、`gh pr comment`、往用户主目录写文件、往临时文件夹写文件、读一个插件文件。预期：拒绝、调用后拦截、拒绝、拒绝、拒绝、允许、允许。最后，`SubagentStop` 让它继续工作，直到第二个测试文件被删除。
2. **正常运行。** 测试工程师的 TE1 通过 Bash 写测试，开发工程师的 DV2 运行测试，都没有拦截。测试经理的 TM2 在临时文件夹里提交一个临时副本，没有拦截。代码审查员的 CR1 运行 `/code-review` 和 `/security-review`，没有拦截。要求运行 `/code-review --fix` 的探测被拒绝。
3. **主会话。** 在 `main` 上的提交被 `pre-commit` 拒绝。分支上带 Claude trailer 的提交被 `commit-msg` 拒绝。`git commit --no-verify` 被拒绝。在 `main` 上的 `gh pr create` 在运行前被拒绝。新克隆的仓库由 `SessionStart` 设置 `core.hooksPath`。试运行从不推送 `main`，临时仓库也不例外。`pre-push` 由单元测试覆盖。
4. **troy-mode 之外。** 在没有 `.troy-mode/` 的文件夹里，没有任何 hook 输出。
5. **事实。** 试运行记录 `Skill` 工具的输入字段、hook 的 `deny` 在 `acceptEdits` 模式下是否有效，以及 `if` 规则能否过滤 `Glob` 和 `Grep`。如果某个事实和本设计不同，就在同一个 PR 里更新设计。
6. **速度。** 每种 hook 在 Troy 的电脑上各运行 20 次。中位数写进 PR 描述，必须低于 200 毫秒。

试运行大约需要 8 次角色运行。示例副本不提交。

**D231 和 D232（D234）。** 构建的 PR 开出之前，hook 和引擎在自带 CLI 的嵌套 `claude -p` 会话里运行，用的是 F03 Python 示例项目的一次性副本。tstack 通过 `--plugin-dir` 从 PR 分支加载，已安装的插件关闭，`BASH_DEFAULT_TIMEOUT_MS` 设为 5 秒，让角色的测试命令转到后台：

1. 一次测试工程师运行在测试命令仍在运行时报告。`check-run` 给出带代理 ID 的 `running` 问题。主会话用这个 ID 调用 `TaskStop` 结束命令，之后 `check-run` 和 `snapshot` 都通过。
2. 第二次运行里，命令在报告之后自己结束。被唤醒的角色的调用以规则 `stopped` 被拒绝，它的记录关闭。
3. 第三个会话在命令运行时退出，`SessionEnd` 关闭记录。
4. 角色带 `run_in_background` 的调用像超时的调用一样被记录，否则在同一个 PR 里更新设计。

大约需要 4 次角色运行，不到 $5。有两件事只有桌面应用能表现出来：角色在等待自己后台工作的通知，以及自动模式是否放行主会话的 `TaskStop`。由第一次真实运行核实。

### 13.4 状态

| 时间点 | 需求文档 7.2 中 F05 的状态 |
| --- | --- |
| F05 的 PR 在试运行通过后合入 | 在示例项目上跑通：在 Python 示例上的试运行中，hook 拦住了每一项探测，角色由人手启动。troy-mode（F07）还不会启动角色。 |
| 试点（F11）在 hook 下运行 | 在真实项目上用过 |

如果试运行不能在 PR 之前进行，状态就保持"已编写"，直到试运行完成。F05 用一个 PR 发布：`hooks/hooks.json`、`troy-mode/hooks/`、`troy-mode/checks/git-hooks/`、测试、工作流的修改和 `build_sample.py` 的修改。状态更新另开一个 PR。

## 14. 不在 F05 里的

- 把 git hook 复制进项目，以及初始化时设置 `core.hooksPath`（F06）。
- 每次角色运行后检查 `git status`、`HEAD` 和分支，检查架构师只改了第 4 节，以及提交后运行 `troy-check code`（F07）。
- 判断依赖改动是否经过批准（F07，加上 CI 的 R16 标记）。
- R21 在 CI 里的 troy-check 分支检查，即 PR 的源分支是 `main` 时失败（以后对 F02 的修改）。
- 把主会话的文件限制在产品经理的范围内（F07）。

## 15. 需要 Troy 决定的事项

D1 到 D38 属于 F01 到 F04 的设计，所以 F05 从 D39 开始。

| 编号 | 问题 | 选项 | 推荐并已批准 |
| --- | --- | --- | --- |
| D39 | hook 怎样实现？出错时怎么办？ | A：Python 3.11 加标准库，复用插件里 troy-check 的模块。`hooks/hooks.json` 放在插件的标准文件夹里。出错时拒绝子代理的调用，对主会话只给警告（第 10 节）。B：只用 shell 脚本。C：出错时一律放行，这是 Claude Code 的默认行为。 | A。这符合 F02 D7，而且 hook 对路径的分类和 CI 完全一样。对子代理出错即拒绝，崩溃就不会让写入范围失效，主会话也仍然可以修复项目。 |
| D40 | hook 限制哪些调用者？F04 的试运行表明，`/code-review` 的分叉以 `general-purpose` 的身份到达 hook，而 Claude Code 不报告子代理的上级是谁。 | A：角色受各自写入范围的限制。troy-mode 项目里的其他所有子代理只读。主会话的文件不受限制（第 4 节）。B：只限制 6 个角色，其他子代理不受限制。C：其他子代理继承正在运行的角色的范围，用一个状态文件记录。 | A。不用猜上级是谁就能覆盖 `/code-review` 的分叉，而在 troy-mode 里本来就只有主会话和角色修改文件。代价是：主会话在 troy-mode 项目里为写文件的任务启动的子代理会被拒绝，主会话要自己做这件事。C 依赖可能丢失的启动和停止事件。 |
| D41 | hook 怎样知道角色通过 Bash 改了什么？F04 试运行里，测试工程师和开发工程师都通过 Bash 写文件。 | A：调用前检查 Write 和 Edit；每次 shell 或技能调用后、以及角色停止时，把工作区和角色开始时的状态比较。停止会被拦一次，直到角色撤销改动（第 6 节）。B：从每条命令里读出写入目标，比如 `>` 和 `cp`。C：只管 Write 和 Edit，由 F07 运行后的检查兜底。 | A。不论用什么方式改，`git status` 都能看到仓库里的每个改动。B 会漏掉大多数写文件的方式；C 会让开发工程师最常用的写法在运行结束前都没人检查。 |
| D42 | 仓库外的路径算不算写入范围之外？F04 试运行里，测试经理在临时文件夹里做了临时副本。 | A：临时文件夹和会话的 scratchpad 允许，其他地方拒绝（第 5.2 节）。B：仓库外一律允许。C：仓库外一律拒绝。 | A。临时副本照常可用，角色也不能通过 Write 或 Edit 改别的项目或 Troy 的设置。C 会让测试经理无法用 mock 检查 R09。 |
| D43 | 子代理在 git 和 GitHub CLI 里可以运行什么？ | A：一张只读命令的清单。在临时文件夹的临时仓库里，除 `push` 外任何 git 命令都可以。技能只有 `code-review` 和 `security-review`，不带 `--fix` 或 `--comment`（第 7 节）。B：一张禁止命令的清单，其余都允许。 | A。这样新出现的 git 或 `gh` 子命令在有人加进清单之前是被拒绝的，而不是在有人发现之前是被允许的。临时仓库这条规则让测试经理可以提交副本来检查 R09。 |
| D44 | 提交和推送时怎样执行 R19 和 R21？从 shell 命令里读出提交信息并不可靠。 | A：troy-check 文件夹里的 git hook（`commit-msg`、`pre-commit`、`pre-merge-commit`、`pre-push`），通过 `core.hooksPath` 打开：troy-init 设置它，新克隆里由 `SessionStart` 修复。Claude Code hook 拒绝 `--no-verify` 和对 `core.hooksPath` 的修改，并对 `gh pr create` 和 `gh pr edit` 检查 R19 和 R21（第 8 节）。B：只用 Claude Code hook，从命令里读出提交信息和分支。 | A。git 把准确的提交信息、作者和推送的 ref 交给它的 hook，不需要猜。它们还覆盖 Troy 在 troy-mode 项目里自己从终端做的提交，这正是 R21 的要求。Troy 仍然可以用 `--no-verify` 跳过它们，Claude 不能。 |
| D45 | 在没人能批准提示的会话里，角色怎样读插件自己的文件，比如 `technical-writing/SKILL.md`？F04 试运行里的 IF1 就因此失败。 | A：一个 `PreToolUse` hook 在 troy-mode 项目里放行 `CLAUDE_PLUGIN_ROOT` 之内的 `Read`、`Glob` 和 `Grep`，所以 troy-init 不写任何权限规则（第 9 节）。B：troy-init 把 `Read(<plugin folder>/**)` 写进项目的 `.claude/settings.local.json`。C：Troy 在用户设置里加一次 `Read(~/.claude/plugins/**)`。 | A。插件文件夹随每个版本变化，写下的规则会过时，而且每个新的 worktree 和克隆里都没有 `settings.local.json`。hook 每次读取当前的文件夹，而且只放行读取。 |
| D46 | F05 怎样检查？状态什么时候改？ | A：单元测试和埋 bug，再在 PR 开出前在 Python 示例上做带探测的试运行（第 13 节）。合入后状态为"在示例项目上跑通"。B：只做单元测试，状态为"已编写"。 | A。试运行能确认文档没有说清的事实（`Skill` 的输入、`acceptEdits` 模式下的 `deny`、`if` 规则对 `Glob` 和 `Grep` 是否有效），并在 Windows 上实测速度。代价大约是 8 次角色运行。 |
| D200 | 主会话发到 GitHub 的文字怎样检查？`ZJUCao/recipe-menu#92` 上的一条评审评论在 `check-text` 失败后仍被发出，而 GitHub 会保留每次编辑的历史。来自 tstack issue #65，即 recipe-menu v0.1.0 回顾提出的规则提案。D161 到 D199 留给 F17 到 F19，所以这个决定用 D200。 | 架构师在 issue 里权衡过的层级：项目的架构；lint、troy-check 或 CI 里的 `project-rules.yml` 任务；Review 或 Process 一行；或者 F05 的 `PreToolUse` `gh` 防护。以及是放宽 R19 还是新增一行 R 规则。 | F05 的 `gh` 防护，硬规则，并把 R19 放宽到 PR 评论和评审、issue 以及发布说明，不新增 R 规则。对主会话，防护用 `check-text` 的函数和模式检查每条发文字的 `gh` 命令的文字，读不到的文字和检查出错时都拒绝（第 8.2 节和第 10 节）。只有 hook 这一层在文字离开本机之前运行，而且对每个调用者都运行。其他层级读的是仓库，或者在 CI 里运行，那时 GitHub 已经保存了文字和编辑历史；Review 一行实际上已经存在，#92 说明它在形式上执行了，实际上没有起作用。Troy 于 2026-11-16 按架构师的推荐批准（AR6：A2、B1、C）。 |
| D219 | `hooks.log` 保留多久？F08 的回顾和 F11 的报告按整个版本统计 hook 拦截，试点里一个版本用了六天，而 `SessionStart` 会删除一天前的日志行。所以 `ZJUCao/recipe-menu` 的 v0.1.0 回顾最多只看到最后一天的行，在整个版本里反复出现的拦截没法变成规则提案。来自 tstack issue #66。这一批给 F05 的编号是 D219 到 D222。 | A：按配置里设定的天数保留，即 `[hooks] log_days`，默认 30，角色记录仍在一天后删除。B：保留到下一个版本的标签。C：`check-run` 把每次角色运行的日志行复制进流程状态，由 `retro` 读取。 | A。hook 不需要标签或流程状态，所以 `SessionStart` 仍然只是读一个文件、读一次配置。30 天足够覆盖试点六天的版本，还有余量；版本更长的项目可以调大这个数。B 会让 hook 去读标签和 F08 的发布状态。C 会改动F07 和 F08 的状态，而且会漏掉主会话的拦截，因为它们不属于任何一次角色运行。角色记录仍是一天，因为记录只在它的角色运行时才有用。错误的值是配置错误，配置无效时保留每一行（第 10 节）。Troy 于 2026-11-18 按推荐批准。 |
| D223 | 怎样拦住从标准输入读取程序的 Python？在 `ZJUCao/recipe-menu` 的两份会话记录里，代理或主会话这样运行了 168 次 Python，其中 39 次卡在 Python 的提示符上，直到 120 秒的时限。每份 brief 里的警告都没能防住。来自 tstack issue #64，即 recipe-menu v0.1.0 回顾的规则提案。这一批给 F05 的编号是 D223 到 D230。 | 架构师在 issue 里权衡过的层级：架构、lint、CI、troy-check 的上限或 `project-rules.yml`；权限的 deny 规则；或者 F05 的 `PreToolUse` hook，对每个调用方，再加一条新的 R 规则。以及拒绝多少：按回顾的字面意思，拒绝所有由 heredoc、管道或 `/dev/null` 提供输入的 Python；还是只拒绝程序来自标准输入的 Python。 | F05 的 hook，对每个调用方，加一条新的硬规则 R23，并采用较窄的理解：只拒绝 `python -`、`python -i`，以及没有脚本、`-c` 或 `-m` 的 Python，不管标准输入来自哪里（第 8.3 节）。命令不会在提交或 PR 里留下痕迹，所以架构、lint、CI 和 troy-check 都看不到它；deny 规则只匹配命令的前缀，会漏掉完整路径、`cd ... &&` 和包装命令，而大多数卡住的运行正是这些写法。hook 在每条命令启动前就看到它，这是 R08、R19 和 R21 已经在用的层级，而且它也检查主会话：在构建 F11 到 F13 的会话里，7 次超时有 2 次是主会话造成的。较窄的理解不会拒绝 257 次带脚本、`-c` 或 `-m`、从管道或 `/dev/null` 读取并正常结束的运行中的任何一次，其中 237 次是主会话读取 `troy_flow.py` 的输出。`timeout` 加入第 7.1 节的包装命令，这也让 git 和 `gh` 的检查能看到 `timeout 60 git push`。Troy 于 2026-11-16 按架构师的推荐批准（AR6：Q1 A、Q2 A、Q3 A），并采用较窄的理解。 |
| D231 | 怎样不让角色留下仍在运行的命令在后来的运行中修改工作区？试点里，每一次都是角色的命令在 Bash 工具的 120 秒时限被 Claude Code 转到后台，在角色报告之后继续运行，而角色停不掉它。在桌面应用里，角色不能在前台运行（第 6.1 节）。issue 提出的候选是：角色在前台运行或在 `check-run` 之前停掉、某个角色还在运行时 `snapshot` 拒绝、角色停掉自己启动的每个进程。来自 tstack issue #49。这一批使用 D231 到 D240：D231、D232 和 D234 属于 F05，关于角色考试 U5 的 D233 属于 F16。 | A：只改入口技能。通知说某个角色在等待自己的后台工作时，主会话在 `check-run` 之前用 `TaskStop` 结束这个角色。B：A，再加一项检查。hook 记下角色每条转到后台的命令，并保留角色的记录，直到命令结束或被停掉。只要有未关闭的记录，`check-run` 和 `snapshot` 就拒绝，并列出要停掉的代理 ID（第 6.1 节，F07 第 7 节）。C：B，再让角色结束自己的命令：有 Bash 的五个角色得到 `TaskStop`，`SubagentStop` 让角色继续工作一次，直到它停掉这些命令。D：在 troy-mode 项目里关闭 Claude Code 的后台任务，由 troy-init 在一个设置文件里写入 `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`，这样超过时限的命令被停掉，每个角色都在前台运行。 | B。需求文档 5.8 更看重检查而不是指令。2026-11-21 主会话读到了通知，仍然让任务继续运行，所以只有 A 可能重演。B 用的是 Claude Code 自己交给 hook 的任务 ID，不需要列出进程（分类器在 Windows 上拒绝过），也不用猜命令是哪个代理启动的。过期记录唯一的出路也是同一个 `TaskStop`。它不改任何角色的指令，所以它的角色考试没有受影响的题，不花钱。C 能更早结束命令，但对没有这样做的角色，仍然需要主会话的检查；C 还要一场十道题、基线重测的角色考试，$188.93，却不多带来安全。D 没有在桌面应用里试过，会改变项目里的每个会话，包括 Troy 自己的，而且依赖 Claude Code 可能变化的一项设置。Troy 于 2026-11-21 按推荐批准（"全按推荐"）。 |
| D232 | Claude Code 在角色报告之后，因为它留下的命令结束或被停掉而唤醒它时，hook 怎么处理？2026-11-21，`SubagentStart` hook 在开发工程师的修改还在工作区里时，给这样一个测试经理重新做了记录，随后 `SubagentStop` hook 让它对开发工程师的三个文件执行 `git restore`。来自 tstack issue #49。 | A：把这个角色当作已经结束。保留它已停止的记录，以规则 `stopped` 拒绝它可能改动东西的调用，在它停止时跳过变更检测（第 6.1 节）。B：保持现在的做法，重新记录并做变更检测。C：同 A，但连它的读取也拒绝。 | A。已停止角色的报告已经交付，troy-mode 也从不给它发新消息，所以它没有事可做。拒绝它的调用，就不会在另一个角色运行时改动工作区；跳过变更检测，hook 就不会把另一个角色的工作算到它头上。B 留着 2026-11-21 的隐患，一次 `git restore` 就会毁掉正在进行的工作。读取不改动任何东西，所以 C 只会多出拒绝。Troy 于 2026-11-21 按推荐批准（"全按推荐"）。 |
| D234 | D231 和 D232 的改动怎样检查，状态什么时候前进？来自 tstack issue #49。 | A：由另一个代理按本设计写测试，埋 bug，再在 F03 Python 示例项目的副本上用嵌套 `claude -p` 会话试运行（第 13.3 节），大约 4 次角色运行，不到 $5。试运行后，F05 和 F07 的状态说这项改动"在示例项目上运行过"；一次真实运行结束过遗留的命令后，说"在真实项目上用过"。B：只写测试、埋 bug，真实运行之前状态为"已编写"。 | A。探测是在临时项目里用探测插件做的，不是 tstack 的 hook 加真实角色。试运行核实两者配合得上，也核实带 `run_in_background` 的调用像超时的命令一样报告它的任务。Troy 于 2026-11-21 按推荐批准（"全按推荐"）。 |

需求文档 1.15 版记录了已批准的改动：F05 一行按第 4 到第 9 节的实际做法描述 hook，包括 git hook、只读的子代理、shell 调用后的检查，以及插件文件的读取。需求文档 1.46 版记录 D200：第 6 节的 R19 和 F05 一行。D219 不改需求文字：F05 一行说一份本地日志记录每次拦截，这仍然成立，只有它的状态提到了 issue #66。需求文档 1.50 版记录 D223：第 6 节新增的 R23，以及 F05 一行。

需求文档 1.52 版在第 7.2 节的两行里记录 D231 和 D232：

- F05 一行在关于 R23 的那句之后加上："They record each command that a role leaves running in the background, so that troy-mode ends it before the next run, and refuse every call of a role that has already stopped (D231, D232)."（中文镜像："它们记下角色留在后台运行的每条命令，让 troy-mode 在下一次运行之前结束它，并拒绝已经停止的角色的每次调用（D231、D232）。"）
- F07 一行的"checks after each run that the role changed only files in its write scope (D31)"后面加上", and that nothing the role started still runs, which it then ends (F05 design D231)"（中文镜像：在"每次运行后检查角色只改了写入范围内的文件（D31）"后面加上"，并检查角色启动的东西都已不再运行，否则就结束它（F05 设计 D231）"）。

R 行都不变：这项检查属于 troy-mode 自己在每次运行后的检查（F07 设计 D59），这也没有哪一条 R 行提到。D234 和 F16 的 D233 不改需求文字。

## 16. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-06 | 初稿。 |
| 1.0 | 2026-11-06 | Troy 批准，含 D39 到 D46，全部采用推荐答案。 |
| 1.1 | 2026-11-07 | 第 13.3 节试运行确认的事实：`if` 规则只过滤 `Read`，所以 `Glob` 和 `Grep` 单独一项、不带 `if`（第 3、9、10 节）。在没人能批准提示的会话里，Claude Code 自己的权限会拒绝项目之外的 `Write`，所以角色用 Bash 做临时副本（第 5.2 节）。试运行里测试经理用一个 `mktemp -d` 变量指定临时文件夹，所以第 7.1 节也跟踪同一条命令里前面设成字面路径或 `mktemp -d` 的变量（第 7.1、7.2 节）。`Skill` 的输入字段（第 7.4 节）。实测的中位数（第 10 节）。 |
| 1.2 | 2026-11-17 | D200，来自 Troy 于 2026-11-16 批准的 tstack issue #65：主会话向 GitHub 发文字的 `gh` 命令在运行前检查，读不到时拒绝（第 1、8.2、10、11、13.1、13.2 和 15 节）。 |
| 1.3 | 2026-11-18 | D219，来自 Troy 于 2026-11-18 批准的 tstack issue #66：`hooks.log` 按 `[hooks] log_days` 天保留日志行，默认 30 天，角色记录仍在一天后删除（第 1、3、10、13.1、13.2 和 15 节）。第 15 节的表格在 D200 之前不再断开。 |
| 1.4 | 2026-11-20 | D223，来自 Troy 于 2026-11-16 批准的 tstack issue #64：每个调用方从标准输入读取程序的 Python 都在启动前被拒绝，作为新规则 R23；`timeout` 加入第 7.1 节拆掉的包装命令，经过 `xargs` 的命令会被标记（第 1、3、7.1、8、8.3、10、11、13.1、13.2 和 15 节）。 |
| 1.5 | 2026-11-21 | D231、D232 和 D234，来自 tstack issue #49，Troy 已于 2026-11-21 批准（"全按推荐"）：试点里遗留的工作是被 Claude Code 转到后台的角色命令，不是卡住的角色。hook 记下这样的命令，保留角色的记录直到它的工作结束，在主会话 `TaskStop` 时和 `SessionEnd` 时关闭记录，并拒绝已经停止的角色的每次调用。事实来自试点的会话记录和用 CLI 2.1.328 做的探测（第 1、3、6、6.1、10、11、12、13.1、13.2、13.3 和 15 节）。 |
| 1.6 | 2026-11-22 | F20 设计（D268 到 D279，Troy 已于 2026-11-22 批准）：hook 从简报得知角色的团队，让它的命令在团队的工作树里运行，把它的记录和日志行放在该工作树的 git 文件夹里，给日志追加和记录更新加锁，在团队的角色运行时拒绝主会话在该团队工作树里的写入（规则 `team-busy`），并把共用文档移出团队的写入范围；`SubagentStart` 不再写角色的记录（第 3、4、5、6、6.1 和 10 节）。这些改动随 F20 的构建落地。 |
