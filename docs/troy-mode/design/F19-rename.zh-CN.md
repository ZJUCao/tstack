# F19 设计：改名为 tstack

> 本文件是 [`F19-rename.md`](F19-rename.md) 的中文镜像，同步自英文版 1.0（2026-11-16）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.40](../requirements.zh-CN.md#72-功能列表) 中的 F19 |
| 版本 | 1.0 |
| 日期 | 2026-11-16 |
| 状态 | Troy 已于 2026-11-16 批准，含 D191 到 D199。 |
| 事实来源 | 英文版 [`F19-rename.md`](F19-rename.md)。本文件是中文镜像。 |

## 1. 范围

F19 把插件 `troy-pstack` 改名为 `tstack`，意思是 Troy 自己的 stack，就像 Lauren Tan 的 `pstack` 以 poteto 命名一样（需求文档的 F19 行、Q4 和修改记录 1.32）。它交付：

1. **一个构建 PR**，改掉这个名字所有现行的出现：插件的身份、命令和 agent 的前缀、钩子的匹配规则、troy-init 写进项目的文件、文档、测试和 CI（第 4 节和第 5 节）。
2. **一个名字检查**，放在 CI 里，让旧名字不再出现在现行文字里（第 11.2 节）。
3. **仓库之外的步骤**，按顺序：GitHub 仓库、新的本地文件夹、marketplace、Troy 已安装的插件、mamba 环境，以及已有的项目（第 6 到 8 节）。

命令变成 `/tstack:troy-mode` 和 `/tstack:troy-init`。里面的名字不变：skill、前缀之后的 agent 名、标记文件夹 `.troy-mode/`、插件里的文件夹、troy-check、troy-init 和引擎（第 4.2 节）。README 和插件描述写明：大部分 skill 来自 Lauren Tan 的 pstack，按其 MIT 许可使用；troy-mode 是 Troy 自己的作品（第 4.3 节）。

本设计里的事实来自 `3a14119` 时的仓库（插件 0.5.0，需求文档 1.38）、2026-11-16 时 Troy 的电脑，以及第 3 节的探测。探测用的是 Claude Code 2.1.325，也就是桌面应用自带的版本。

## 2. 这个名字现在在哪里

### 2.1 仓库里

在 `3a14119` 上运行 `git grep -i -E "troy[-_ ]?pstack"`，在 561 个受跟踪文件中的 157 个里、749 行上，共找到 931 处。每一处都写作 `troy-pstack`，没有 `troy_pstack` 或 `troy pstack`。

| 类别 | 行数 | 文件数 | 在哪里 | F19 怎么做 |
| --- | --- | --- | --- | --- |
| 插件身份 | 6 | 3 | `.claude-plugin/plugin.json`（名字和一个关键词）、`.claude-plugin/marketplace.json`（marketplace 的名字、描述和插件的名字）、`LICENSE`（Troy 修改的那一行） | 新名字和署名（第 4.1 节和第 4.3 节） |
| 模型规则 | 15 | 11 | `~/.claude/rules/troy-pstack-models.md`，出现在 `setup-pstack`、另外八个 skill、README、上游指南和适配说明里 | 改为 `tstack-models.md`（第 4.1 节） |
| npm 作用域 | 3 | 3 | 两个 `package.json` 和 `bun.lock` 里的 `@troy-pstack/poteto-mode-tools` 和 `@troy-pstack/statechart` | 改为 `@tstack/...` |
| 钩子的匹配规则和路径 | 3 | 1 | `hooks/hooks.json`：两个 `^troy-pstack:troy-` 匹配规则，以及 Read 规则 `Read(//**/troy-pstack/**)` | 第 5.2 节 |
| 代码里的 agent 名 | 4 | 3 | `troyhook/scopes.py`（`PLUGIN_PREFIX`、`ROLE_PATTERN`）、`troyflow/brief.py`（`subagent_type`）、`troyflow/runs.py`（`hooks.log` 的匹配） | 每个包一个常量（第 5.1 节） |
| 写进项目的文件 | 6 | 5 | 插件里这些文件的来源：`.troy-mode/checks/troy_check.py`、`.github/workflows/troy-mode.yml`、`.troy-mode/config.toml`、Python 语言包的 `pyproject.toml`，以及 troy-init 写进 `docs/rules.md` 的修改记录行 | 新文字；项目通过升级拿到（第 8 节） |
| 代码注释和提示 | 39 | 19 | troy-init、引擎、钩子和开发工具里的文档字符串和提示 | 改用新名字 |
| 文字里的命令名和 agent 名 | 107 | 29 | README、两份指南、`skills/troy-init`、`skills/poteto-help` 和适配说明里的 `/troy-pstack:<skill>` 和 `troy-pstack:<agent>` | 改为 `/tstack:` 和 `tstack:` |
| 其他现行文字 | 153 | 54 | README、上游指南 `docs/guide/`、适配说明、troy-mode 的指南、skill 和 playbook 的文字、各角色的共同规则及其在 `agents/` 里的六份副本、语言包的 README，以及示例项目 | 改用新名字（第 5.3 节） |
| 需求文档 | 50 | 2 | 现行各节、文首的状态行和修改记录 | 现行文字改，历史不改（第 9 节） |
| 已批准的设计 | 268 | 28 | F01 到 F14，中英文 | 不改（第 9 节） |
| 测试 | 82 | 20 | 钩子 56、引擎 19、开发工具 4、troy-init 2、troy-check 1 | 第 11.1 节 |
| CI | 10 | 3 | `troy-python-sample.yml` 和 `troy-cpp-sample.yml` 把插件检出到文件夹 `troy-pstack`；`troy-docs.yml` 在一条注释和一个步骤名里提到它 | 第 5.4 节 |
| mamba 环境 | 3 | 1 | `troy-mode/dev/environment.yml`：`name: troy-pstack` 及其注释 | 第 6.4 节 |

### 2.2 仓库之外

| 地方 | 哪里写着 troy-pstack | 章节 |
| --- | --- | --- |
| GitHub | 私有仓库 `ZJUCao/troy-pstack`，描述为 "Personal fork of Lauren Tan's pstack (MIT)"，PR 编到 #62。没有分支保护，自动合并是关的。 | 6.1 |
| 本地文件夹 | `D:\Troy\Projects\troy-pstack`：在 `main` 上的主检出、`.claude/worktrees/` 里的 9 个 worktree，以及被 git 忽略的 `.claude/settings.local.json`，里面有 Troy 的权限规则和长期的试运行许可，许可的文字写着 troy-pstack。 | 6.2 |
| marketplace | `~/.claude/plugins/known_marketplaces.json` 和 `~/.claude/settings.json` 里的 `extraKnownMarketplaces`：一个 `directory` 来源 `troy-pstack`，指向这个文件夹。 | 6.3 |
| 已安装的插件 | `troy-pstack@troy-pstack` 0.5.0，用户范围，记在 `~/.claude/plugins/installed_plugins.json` 和 `enabledPlugins` 里，缓存文件夹是 `~/.claude/plugins/cache/troy-pstack/troy-pstack/0.2.0` 和 `0.5.0`。 | 7 |
| 项目记忆 | `C:\Users\Troy\.claude\projects\D--Troy-Projects-troy-pstack\memory`，以文件夹的路径为键。里面的笔记写着这个文件夹、插件和环境的名字。 | 6.2 |
| mamba 环境 | `D:\miniforge3\envs\troy-pstack`（F03 设计 D26）。 | 6.4 |
| 模型规则 | `~/.claude/rules/` 不存在：`/setup-pstack` 从没运行过，所以没有规则文件要搬。 | 4.1 |
| 笔记和会话 | 侧会话笔记、会话的任务说明，以及文件夹是这个文件夹的 worktree 的桌面会话。 | 6.2 |

### 2.3 项目里

在 `ZJUCao/recipe-menu` 和 `ZJUCao/troy-mode-trial` 上做代码搜索，各自找到同样的六个文件：

| 文件 | 写着什么 | 归谁 | 现在升级时怎么处理 |
| --- | --- | --- | --- |
| `.troy-mode/checks/troy_check.py` | "See docs/troy-mode/design/F02-checks.md in troy-pstack" | troy-init | 没人改过时替换 |
| `.github/workflows/troy-mode.yml` | "Design: ... in troy-pstack." | troy-init | 没人改过时替换 |
| `.troy-mode/config.toml` | "# Set by the language pack (troy-mode/lang/ in troy-pstack), for example:" | 项目 | 从不修改，只列出差异（F06 设计 D54） |
| `pyproject.toml` | "# troy-check is checked in troy-pstack, not in the project." | 项目 | 从不修改，只列出差异 |
| `docs/rules.md` | 修改记录行 "troy-mode's rules brought up to troy-pstack 0.5.0." | troy-init 写它的行 | 加一行 |
| `docs/rules.zh-CN.md` | 同一行的中文 | troy-init 写它的行 | 加一行 |

试点的 `.claude/settings.local.json` 有三条 allow 规则，都没有提到 troy-pstack；troy-init 也不写任何权限规则（F05 设计 D45）。每个克隆的 git 文件夹里的 `troy-mode/hooks.log`，有些行的 `agent_type` 是 `troy-pstack:troy-developer` 这样的值。

## 3. 探测

2026-11-16，在本会话 scratchpad 里一个带 `.troy-mode/` 文件夹的临时 git 仓库中，运行了嵌套的 `claude -p` 会话，用 haiku，最多 3 轮。改名后的插件是本分支的一份副本，只把 `plugin.json` 的 `name` 改成 `tstack`，用 `--plugin-dir` 加载。`TROY_MODE_PYTHON` 指向一个替身，它记录每次钩子调用及其 `CLAUDE_PLUGIN_ROOT` 和输入，什么也不执行。没有改动任何 GitHub 仓库、已安装的插件、marketplace 或设置。总花费不到 0.10 美元。

| 探测 | 设置 | 结果 |
| --- | --- | --- |
| 1 | 副本放在名为 `tstack` 的文件夹里，以 Git Bash 路径 `/c/...` 交给 `--plugin-dir`，并设 `MSYS_NO_PATHCONV=1` | 副本没有加载：init 事件只列出 `troy-pstack@troy-pstack`。`--plugin-dir` 需要 Windows 路径，例如 `C:/...`。 |
| 2 | 同探测 1，改用 Windows 路径。Troy 已安装的插件开着，和每个会话一样。提示：`/poteto-mode reply with the single word ok`。 | 两个插件都加载了：`tstack@inline` 和 `troy-pstack@troy-pstack`。agent 里既有 `troy-pstack:troy-architect` 也有 `tstack:troy-architect`，每个角色都如此。不带前缀的 `/poteto-mode` 解析为 `tstack:poteto-mode`，两个插件的 `UserPromptExpansion` 钩子都为它运行了。已安装插件的 `path` 和它钩子的 `CLAUDE_PLUGIN_ROOT` 都是 `D:\Troy\Projects\troy-pstack`，也就是文件夹本身，不是缓存文件夹。 |
| 3 | 副本放在名为 `copy-of-plugin` 的文件夹里，加 `--settings '{"enabledPlugins":{"troy-pstack@troy-pstack":false}}'`。提示：调用一次 `Agent`，`subagent_type` 为 `tstack:troy-code-reviewer`。 | 只加载了 `tstack@inline`。它的 agent 和命令都叫 `tstack:...`，名字来自 `plugin.json`，与文件夹叫什么无关。它钩子的 `CLAUDE_PLUGIN_ROOT` 就是给定的文件夹。子 agent 运行了，而副本里没改的 `SubagentStart` 匹配规则 `^troy-pstack:troy-` 没有启动它的钩子。之后 Troy 的 `~/.claude/settings.json` 里仍是 `"troy-pstack@troy-pstack": true`。 |
| 4 | 直接运行现在的 `troy_hook.py`，输入是在临时 troy-mode 项目里对 `docs/architecture.md` 的一次 `PreToolUse` `Write` | 来自 `troy-pstack:troy-architect`：允许，因为文件在架构师的范围内。来自 `tstack:troy-architect`：拒绝，"outside your write scope: nothing in the repository except files git ignores"。 |

所以：

- **名字来自 `plugin.json`。** 文件夹叫什么，不影响 agent 名和命令名。
- **两个插件绝不能同时开着。** 两个都启用时，每个插件的钩子都把另一个插件的角色当作未知子 agent，拒绝它们写文件（F05 设计 D40），两个模式守卫也都会运行。Troy 的迁移在 tstack 启动前先关掉 troy-pstack（第 7 节），构建的试运行用 `--settings` 只为它的会话关掉 troy-pstack（第 11.4 节）。
- **所有匹配规则一起改。** 旧的匹配规则会悄无声息地跳过改名后的角色。
- **已安装的插件从它的文件夹里运行。** 在 2.1.325 里，来自 `directory` marketplace 的插件就地运行：init 事件里的路径和钩子的 `CLAUDE_PLUGIN_ROOT` 都是 `D:\Troy\Projects\troy-pstack`，尽管 `installed_plugins.json` 写的是一个缓存文件夹。所以每个会话运行的都是这个文件夹的工作区，现在是 `3a14119` 上的 `main`。移动这个文件夹，会让所有正在运行的会话失去插件；把 F19 的构建拉进这个文件夹，会在会话的 agent 仍用旧名字时改掉它们的钩子。指南说 Claude Code "以副本形式安装插件"（指南 1.3，来自 F10 设计第 6 节）。构建的试运行会再查一次；如果探测 2 的结论成立，构建就修正指南。

## 4. 新名字

### 4.1 身份

| 项目 | 现在 | F19 之后 |
| --- | --- | --- |
| 插件名，在 `plugin.json` 里 | `troy-pstack` | `tstack` |
| marketplace 名，在 `marketplace.json` 里 | `troy-pstack` | `tstack`（D193） |
| 安装 ID | `troy-pstack@troy-pstack` | `tstack@tstack` |
| 命令 | `/troy-pstack:troy-mode`、`/troy-pstack:troy-init`、`/troy-pstack:poteto-mode` 等 | `/tstack:troy-mode`、`/tstack:troy-init`、`/tstack:poteto-mode` 等 |
| agent | `troy-pstack:troy-architect` 和其他角色、`troy-pstack:poteto-agent`、`troy-pstack:comment-sicko` | `tstack:troy-architect` 和其他角色、`tstack:poteto-agent`、`tstack:comment-sicko` |
| 版本 | 0.5.0 | 0.6.0，或下一个空着的次版本号（D193） |
| 模型规则 | `~/.claude/rules/troy-pstack-models.md` | `~/.claude/rules/tstack-models.md` |
| bun 辅助包的 npm 作用域 | `@troy-pstack/` | `@tstack/` |
| GitHub 仓库 | `ZJUCao/troy-pstack` | `ZJUCao/tstack`（D191） |
| 本地文件夹 | `D:\Troy\Projects\troy-pstack` | `D:\Troy\Projects\tstack`（D192） |
| mamba 环境 | `troy-pstack` | `tstack`（D196） |

### 4.2 不变的名字

- 每个 skill 的名字：`troy-mode`、`troy-init`、`setup-pstack`、`poteto-mode`、`poteto-help` 等。`setup-pstack` 是上游的名字。
- 每个 agent 前缀之后的名字：六个 `troy-*` 角色、`poteto-agent` 和 `comment-sicko`。
- 标记文件夹 `.troy-mode/`、插件里的文件夹（`troy-mode/`、`skills/`、`agents/`、`hooks/`、`docs/`）、troy-check、troy-init、`troy_flow.py`，以及代码里的 `troy_mode` 名字。
- 适配说明里的 `<pstack>` 仍然指插件的文件夹。
- `pstack`、`poteto-mode`、`poteto-agent` 和 `poteto-help` 这些名字，它们注明作品来自 Lauren Tan。

### 4.3 署名

`plugin.json` 的描述，以及 `marketplace.json` 里插件条目的描述：

> tstack, Troy's own stack for Claude Code. Most of its skills, principles, playbooks, and subagent workflows come from Lauren Tan's pstack 0.15.36, used under its MIT license. troy-mode, the workflow from requirements to released versions, is Troy's own work. Not affiliated with or endorsed by Lauren Tan or Cursor.

marketplace 的描述改为 "Troy's personal Claude Code plugins. Currently one: tstack."。关键词 `tstack` 替换 `troy-pstack`，`pstack-fork` 保留。

README 的开头：

> tstack is Troy's own stack for Claude Code, named the way Lauren Tan's pstack is named after poteto. It was called troy-pstack until version 0.5.0. Most of its skills, playbooks, agents, and guide pages are Lauren Tan's work from pstack, used under the MIT License. troy-mode is Troy's own work.

README 其余的署名不变："Not affiliated" 说明、关于 Lauren Tan 的 MIT 许可的段落，以及 troy-mode 的说明（F10 设计 D88）。`LICENSE` 里 Lauren Tan 的版权和许可声明原样保留，Troy 那一行改为 "Copyright (c) 2026 Troy (modifications made in tstack, formerly troy-pstack)"。

## 5. 仓库里

### 5.1 每个包只写一次名字

- **钩子。** `troyhook/scopes.py` 存放 `PLUGIN_PREFIX = "tstack:"`，并用 `re.escape` 从它构造 `ROLE_PATTERN`，这样名字只写一次。`modeguard.py` 本来就从 `PLUGIN_PREFIX` 取提示里的 `/tstack:troy-mode`（F13 设计第 6 节）。
- **引擎。** `troyflow` 里一个常量 `PLUGIN_PREFIX = "tstack:"`，`brief.py` 和 `runs.py` 导入它，取代原来的两处字面值。
- **troy-init。** 它从 `plugin.json` 读 `name`，就像它已经读 `version` 一样，修改记录行和提示都用它："troy-mode's rules brought up to tstack 0.6.0."
- **一个测试**检查 `plugin.json`、`marketplace.json`、`hooks.json` 和两个常量彼此一致（第 11.1 节）。

没有选的做法：钩子每次调用都读 `plugin.json`。这会给每次钩子调用多加一次读文件，也多一种出错的可能，只为了一个只改一次的名字。

角色的匹配仍然精确：只有 `tstack:troy-<role>` 是角色。如果像模式守卫那样接受任何前缀（F13 设计 D122），别的插件的 `x:troy-developer` 就能写源代码，而 F05 的冒充者测试禁止这样。

### 5.2 `hooks/hooks.json`

| 条目 | 现在 | F19 之后 |
| --- | --- | --- |
| `SubagentStart` 匹配规则 | `^troy-pstack:troy-` | `^tstack:troy-` |
| `SubagentStop` 匹配规则 | `^troy-pstack:troy-` | `^tstack:troy-` |
| `PreToolUse` `Read` 的 `if` 规则 | `Read(//**/troy-pstack/**)` | `Read(//**/tstack/**)` |
| `UserPromptExpansion` 匹配规则 | `^([^:]+:)?(poteto-mode\|no-comments)$` | 不变（F13 设计 D122） |

`if` 规则只是让钩子不为这个名字的文件夹之外的读取启动；钩子本身仍然检查 `CLAUDE_PLUGIN_ROOT`（F05 设计第 9 节）。按 D192，插件从 `D:\Troy\Projects\tstack` 运行（探测 2），所以 `Read(//**/tstack/**)` 能匹配它、它在 `D:\Troy\Projects\tstack\.claude\worktrees\` 里的 worktree，以及缓存文件夹 `~/.claude/plugins/cache/tstack/tstack/<version>/`。放在别的名字的文件夹里的检出，比如旧文件夹，没有权限规则就读不了插件文件。所以构建的试运行从名为 `tstack` 的文件夹加载副本（第 11.4 节）。

### 5.3 文字

每处现行的出现（第 9 节）都改成 `tstack`，大多是直接替换。下面这些要多做一点：

- **安装。** README 和指南第 1.2 节写 `/plugin marketplace add D:/Troy/Projects/tstack` 和 `/plugin install tstack@tstack`。指南第 1.3 节加上 "从 troy-pstack 迁移"，内容是第 7 节的步骤。
- **问题。** 指南的问题表（指南第 8.6 节）加一行："改名之后，每个角色写文件都被当作超出范围而拒绝。" 解决办法："troy-pstack 还装着或还开着。卸载它并重启（第 1.3 节）。"
- **在 tstack 上工作。** 指南第 9.3 节和第 9.4 节：环境路径 `D:\miniforge3\envs\tstack\python.exe`，以及试运行的 `--settings` 参数和名为 `tstack` 的文件夹（第 11.4 节）。
- **规则提案。** 在 `skills/troy-mode/SKILL.md` 里，`gh issue create --repo <owner>/<name>`，两者都取自插件文件夹的 `origin` 远程，取代 `<owner>/troy-pstack`。
- **上游文件。** 来自 pstack 的文件（`docs/guide/`、适配说明 `docs/harness/claude-code.md`、`poteto-help`、`setup-pstack`、各 playbook、`automations/benny/TODO.md`）里，只改分叉当初为改名已经改过的那些行。这些行本来就和上游不同，所以 README 里合并上游的步骤照样能用（需求文档第 8 节）。

### 5.4 CI

- `troy-python-sample.yml` 和 `troy-cpp-sample.yml` 把插件检出到 `tstack/`，并运行 `tstack/troy-mode/dev/build_sample.py`。
- `troy-docs.yml` 加一个运行 `check_name.py` 的步骤（第 11.2 节），并去掉路径过滤，这样每个 PR 都运行它。它的作业大约 30 秒。每个 PR 都运行，也让它以后有了分支保护时能成为必需检查。
- 不改任何工作流或作业的名字，所以 PR 上的检查名字不变。CI 不建名为 `troy-pstack` 的环境：示例作业用的是示例自己的 `environment.yml`。

### 5.5 插件版本（D193）

F19 改变了项目拿到的东西，所以它的 PR 提升次版本号（F10 设计 D89）：0.5.0 变成 0.6.0，如果别的构建先提升了，就用下一个空着的次版本号。版本号接着 troy-pstack 的往下走。每个项目的 `.troy-mode/install.toml` 记着 0.5.0，`docs/rules.md` 的修改记录也写着各个版本，所以升级到 0.6.0 读起来就是下一步。

## 6. 仓库之外

### 6.1 GitHub 仓库（D191）

在构建 PR 合并后的安静时段（第 7 节），把 `ZJUCao/troy-pstack` 改名为 `ZJUCao/tstack`。之后 GitHub 会把旧的网页链接、`git fetch` 和 `git push`、API 调用都转到新名字，只要没有新仓库占用旧名字。issue、PR、CI 历史，以及修改记录里的链接，比如 `https://github.com/ZJUCao/troy-pstack/pull/57`，都照常可用。

- Troy 在仓库设置里改名；或者 Troy 当时在聊天里说可以，由会话运行 `gh repo rename tstack --repo ZJUCao/troy-pstack --yes`。这一步涉及这台电脑之外，所以总要 Troy 同意。
- 仓库描述改为 "tstack: Troy's own stack for Claude Code. Most skills come from Lauren Tan's pstack (MIT); troy-mode is Troy's own work."
- 之后每个克隆设一次远程，每个文件夹一次：`git remote set-url origin git@github.com:ZJUCao/tstack.git`。

### 6.2 本地文件夹（D192）

由 `D:\Troy\Projects\tstack` 的一个新克隆接手，旧文件夹保持原样，直到没人再用它：

1. `git clone git@github.com:ZJUCao/tstack.git D:\Troy\Projects\tstack`，在第 6.1 节之后做，然后检查 `git config user.email`。
2. 把被 git 忽略的 `.claude\settings.local.json` 从旧文件夹复制到新文件夹。Troy 改写其中的长期试运行许可，让它写 tstack。由 Troy 粘贴进去，因为自动模式的分类器拒绝 agent 修改这条规则。
3. 复制项目记忆：把 `C:\Users\Troy\.claude\projects\D--Troy-Projects-troy-pstack\memory` 复制到 `C:\Users\Troy\.claude\projects\D--Troy-Projects-tstack\memory`，这是 Claude Code 从新路径得出的键。新文件夹里的第一个会话更新笔记里的文件夹、插件和环境名字。
4. marketplace 搬到新文件夹（第 7 节）。
5. 之后没有人再在旧文件夹里拉取 `main`。在 Troy 重启 Claude Code 之前，旧插件一直从这里运行（探测 2），它的 9 个 worktree 和上面的会话也照常工作。等没有会话需要它，而且在那里运行 `git worktree list` 看不到还有没推送工作的分支时，Troy 删除旧文件夹。这是 Troy 的步骤，什么时候做都可以。

没有选的做法：

- **就地给文件夹改名。** 文件夹一移动，所有正在运行的会话就失去插件：钩子的 `exec python ... troy_hook.py` 找不到文件，Python 以退出码 2 结束，Claude Code 把它当作阻止，挡住钩子匹配的每个调用，在每个项目里都是。所有会话都得先停下，`git worktree repair` 要修好 9 个 worktree，已归档的会话还会丢掉它们的文件夹。
- **文件夹名不变。** 插件从这个文件夹运行，所以 Read 的 `if` 规则得继续匹配 `troy-pstack`，文档也会写着一个叫 troy-pstack、装的却是 tstack 的文件夹。

### 6.3 marketplace

marketplace 名为 `tstack`，是一个指向 `D:\Troy\Projects\tstack` 的 `directory` 来源。第 7 节用命令行添加它，命令行也会把它记进 `~/.claude/settings.json`。

### 6.4 mamba 环境（D196）

`troy-mode/dev/environment.yml` 把环境命名为 `tstack`。在安静时段，Troy 或经 Troy 同意的会话，从新文件夹创建它：

```powershell
$env:MAMBA_ROOT_PREFIX = 'D:\miniforge3'
$env:UV_LINK_MODE = 'copy'
D:\miniforge3\Library\bin\mamba.exe env create -f D:\Troy\Projects\tstack\troy-mode\dev\environment.yml
D:\miniforge3\envs\tstack\Library\bin\uv.exe pip install --python D:\miniforge3\envs\tstack\python.exe -r D:\Troy\Projects\tstack\troy-mode\dev\requirements-dev.lock
```

在那之前，会话继续用 `D:\miniforge3\envs\troy-pstack\python.exe`，它装的包一样。旧环境随旧文件夹一起删除：`mamba env remove -n troy-pstack`。CI 不需要任何改动（第 5.4 节）。

## 7. Troy 的迁移（D194）

迁移在构建 PR 合并后的一个安静时段里完成，那时没有会话在工作。在第 6 步重启之前启动的会话，一直用 troy-pstack 到重启为止。

| 步骤 | 做什么 | 谁做 |
| --- | --- | --- |
| 1 | 给 GitHub 仓库改名（第 6.1 节）。 | Troy，或经 Troy 同意的会话 |
| 2 | 克隆新文件夹，复制本地设置和记忆（第 6.2 节）。 | 经 Troy 同意的会话；试运行许可由 Troy 粘贴 |
| 3 | 创建环境 `tstack`（第 6.4 节）。这一步也可以晚些做。 | 经 Troy 同意的会话 |
| 4 | 用下面的命令换插件。 | Troy，或经 Troy 同意的会话 |
| 5 | 如果 `~/.claude/settings.json` 的 `extraKnownMarketplaces` 或 `enabledPlugins` 下仍有 `troy-pstack` 键，删掉它。 | Troy |
| 6 | 重启 Claude Code：退出桌面应用再打开。 | Troy |
| 7 | 检查：在 troy-mode 项目的新会话里，`/tstack:troy-mode status` 能运行，命令列表里没有 `/troy-pstack:` 命令。 | Troy |
| 8 | 升级各项目（第 8 节）。 | Troy 输入请求 |

`claude` 不在 PowerShell 的 PATH 上，所以第 4 步用桌面应用自带的命令行。它的版本文件夹会随应用更新而变；2026-11-16 时是 `2.1.325\806e0a45e6f5`：

```powershell
$cli = 'C:\Users\Troy\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.325\806e0a45e6f5\claude.exe'
& $cli plugin uninstall troy-pstack@troy-pstack
& $cli plugin marketplace remove troy-pstack
& $cli plugin marketplace add D:\Troy\Projects\tstack
& $cli plugin install tstack@tstack
& $cli plugin list
& $cli plugin marketplace list
```

`plugin list` 必须显示 `tstack@tstack` 0.6.0 已启用，而且没有 troy-pstack；`marketplace list` 必须显示 `tstack`，没有 `troy-pstack`。先卸载，所以新会话里两个插件绝不会同时运行（第 3 节）。

**退回的办法**，只要旧文件夹还在：卸载 `tstack@tstack`，删除 marketplace `tstack`，添加旧文件夹的 marketplace，安装 `troy-pstack@troy-pstack`，然后重启。已经升级过的项目这时的 troy-check 比插件的新，`status` 会要求升级，升级会把 0.5.0 的文件带回来。

## 8. 已有的项目（D195）

每个项目在一个自然停顿处、没有阶段 PR 开着时，用 `/tstack:troy-mode upgrade troy-mode` 迁移，和每个插件版本一样（F14 设计 D137）：

- `ZJUCao/troy-mode-trial` 在构建的试运行里，通过副本迁移，早于 Troy 的迁移（第 11.4 节）。
- `ZJUCao/recipe-menu` 在 Troy 迁移之后，Troy 在那里输入请求时迁移。

升级之前，项目用 tstack 也照常工作：它提交的文件里没有 agent 名或命令名；`status` 会说它的 troy-check 和插件的不同，和任何新版本之后一样。

升级 PR `[rules] Upgrade troy-mode to 0.6.0` 对第 2.3 节的每个文件做这些改动：

| 文件 | 改动 |
| --- | --- |
| `.troy-mode/checks/troy_check.py` | 替换，因为它归 troy-init，没人改过 |
| `.github/workflows/troy-mode.yml` | 同样替换 |
| `.troy-mode/config.toml` | 改写它的那一行注释，只在这一行和 troy-init 写的完全一样时 |
| `pyproject.toml` | 它的那一行注释，同样处理 |
| `docs/rules.md` 及其镜像 | 新的一行修改记录 "troy-mode's rules brought up to tstack 0.6.0."；以前的行仍写着 troy-pstack |
| `.troy-mode/install.toml` | 版本 0.6.0 |

改写这两行注释是 troy-init 升级的新功能，范围很窄。一张固定的表列出两行旧文字和对应的新文字，比较时去掉行尾的回车符。有人改过的行原样不动，升级报告把它列为差异。`config.toml` 和 `pyproject.toml` 里别的东西都不改，符合 F06 设计 D54。

**不改的。** 已经写下的 `hooks.log` 行保留旧名字。没有东西依赖它们：F07 每次运行后的检查只读该次运行快照之后的行，这些行都在重启之后；F08 的回顾按规则给行分组，不按 agent。git 历史和已合并的 PR 文字也保留旧名字。

升级之后，在项目里代码搜索 `troy-pstack`，只会找到 `docs/rules.md` 及其镜像里较早的几行。

## 9. 哪些文字保留旧名字（D197）

规则：说 tstack 现在是什么、做什么的文字用新名字；记录发生过什么的文字保留当时的名字。

这些保留旧名字：

- **已批准的设计。** F01 到 F14，以及 F19 构建合并前批准的任何后续设计。它们按原样记录决定和试运行：F13 的试运行看到的 `command_name` 是 `troy-pstack:poteto-mode`。它们的版本、同步说明和批准都不变。本设计把旧名字和新名字连起来。
- **修改记录。** 每份文档的修改记录一节，以及需求文档文首的状态行，它概括了各个版本。
- **试点的记录。** 试点报告和 F11 的其他记录。
- **链接和历史。** PR 和 issue 的链接、git 历史，以及已合并 PR 的文字。
- **仓库之外的笔记和记忆。** 会话下次用到时更新（第 6.2 节），不在 F19 的 PR 里改。
- **项目的规则表。** 每个项目 `docs/rules.md` 里较早的行（第 8 节）。

README 的开头和 `LICENSE` 写明 "formerly troy-pstack"（第 4.3 节）。

其余的都在那一个构建 PR 里改：README、两份指南、适配说明、skill、agent、角色、模板、troy-check、troy-init、引擎、钩子、测试、CI、示例项目、语言包的 README、`environment.yml`，以及需求文档里除文首状态行和修改记录之外的部分。第 11.2 节的名字检查让它保持这样。

## 10. 对已有功能的改动

| 功能 | 改动 |
| --- | --- |
| F02 检查 | `troy_check.py`、`workflow.yml` 和 `config.default.toml` 里的文字。 |
| F03 语言包 | Python 语言包 `pyproject.toml` 里的注释、各语言包的 README 和示例项目。环境改名为 `tstack`，仍是以项目命名、只有一个成员的系列（F03 设计 D26）。 |
| F04 角色 | `troy-mode/roles/common.md`，以及六个 agent 文件末尾它的完全副本，还有架构师写规则提案的任务。 |
| F05 钩子 | 匹配规则和 `if` 规则（第 5.2 节）、`PLUGIN_PREFIX` 和 `ROLE_PATTERN`（第 5.1 节），以及它们的测试。 |
| F06 troy-init | 从 `plugin.json` 取插件名，修改记录行和提示，以及升级时改写那两行注释（第 8 节）。 |
| F07 入口 skill | 任务说明里的 `subagent_type`，以及运行后检查对 `hooks.log` 的匹配，都经由引擎的常量。`SKILL.md` 里的命令名。 |
| F09 规则修改 | 规则提案 issue 的仓库取自插件文件夹的 `origin`（第 5.3 节）。 |
| F10 文档 | README、两份指南和插件描述（第 4.3 节）。指南里安装、迁移和问题表的几行，以及关于副本的那句话，如果试运行证实了探测 2。 |
| F13 模式守卫 | 提示里的 `/tstack:troy-mode`，经由 `PLUGIN_PREFIX`，正如 F13 设计第 9 节预见的。匹配规则不变。 |

除了分叉当初为改名已经改过的行，上游 pstack 的行一行都不改（第 5.3 节）。

## 11. F19 怎样检查（D198）

### 11.1 测试

由另一个 agent 根据本设计，在代码改动之前修改和补充测试。测试里每个字面的 `troy-pstack:` 都改成 `tstack:`。新增的用例包括：

| 测试集 | 用例包括 |
| --- | --- |
| 钩子 | `tstack:troy-<role>` 是角色，有它的写入范围。`troy-pstack:troy-<role>` 现在是未知子 agent，只读，和探测 4 一样。冒充者 `xtstack:troy-developer`、`tstack:troy-developer-2` 和 `my-tstack:troy-test-engineer` 都不是角色。`hooks.json` 有第 5.2 节的匹配规则和 `if` 规则。辅助代码里假的安装根目录是 `.../cache/tstack/tstack/<version>`。 |
| 模式守卫 | 提示指向 `/tstack:troy-mode`。`troy-pstack:poteto-mode` 和 `tstack:poteto-mode` 都被拒绝。 |
| 引擎 | 任务说明给出 `tstack:troy-<role>`。运行后的检查只算 `tstack:` 角色的 `hooks.log` 行，不算 `troy-pstack:` 角色的。 |
| troy-init | 修改记录行写的是 `plugin.json` 里的 `tstack` 和版本。每行注释在完全一致时被改写，CRLF 也一样；被改过时原样不动并被列出。 |
| 开发工具 | `test_plugin_name.py`：`plugin.json`、`marketplace.json`、`hooks.json` 的匹配规则和 `if` 规则、`troyhook` 的 `PLUGIN_PREFIX` 和引擎的常量都写 `tstack`。还有 `check_name.py` 的测试。 |

troy-check、troy-init、引擎、开发工具和钩子的测试集在 Linux 和 Windows 上都通过。

### 11.2 名字检查

`troy-mode/dev/check_name.py` 读每个受跟踪的文本文件，报告每一行提到旧插件名（`troy-pstack`、`troy_pstack` 或 `troy pstack`，不分大小写）的行，除非满足下面之一：

1. 文件在工具的历史文件清单里：F19 构建合并前批准的设计、本设计，以及试点报告。
2. 这一行在修改记录一节里：在编号之后的文字正好是 `Change log` 或 `修改记录` 的标题之下，直到下一个同级或更高级的标题。
3. 这一行是文档文首表格的 `| Status |` 或 `| 状态 |` 行。
4. 这一行同时提到了 `tstack`，也就是在讲改名这件事。

什么也没找到时以 0 退出，找到一行时以 1 退出，无法运行时以 2 退出，和 `check_pairs.py` 一样。每条结果写明文件和行号。`troy-docs.yml` 在每个 PR 上运行它（第 5.4 节）。

### 11.3 埋 bug

代码通过之后，在一份临时副本里一次埋一个 bug，每个都必须让某个测试或名字检查失败：`ROLE_PATTERN` 仍用旧前缀；留下一个 `SubagentStart` 或 `SubagentStop` 匹配规则；留下 `if` 规则；留下引擎的 `subagent_type`；留下运行后检查对 `hooks.log` 的匹配；守卫的提示指向 `/troy-pstack:troy-mode`；留下 `plugin.json` 或 `marketplace.json` 的名字；指南某页里残留一个 `/troy-pstack:troy-mode`；升级改写了被改过的注释行；troy-init 的修改记录行写死了名字；留下 `environment.yml` 的名字；名字检查漏掉大写的 `Troy-pstack` 或某个中文镜像。各项计数写进构建 PR 的描述。

### 11.4 试运行

构建 PR 开出之前，改名后的插件在一个真实项目上运行：

- **插件。** 用 `git archive` 把 PR 的最新提交导出到 `<scratchpad>/trial/tstack`，文件夹名为 `tstack`，好让 `if` 规则匹配；用 `--plugin-dir` 加 Windows 路径加载。
- **关掉旧插件。** 只对每个嵌套会话加 `--settings '{"enabledPlugins":{"troy-pstack@troy-pstack":false}}'`，探测 3 证明了这样可行。Troy 的设置不变。
- **项目。** `ZJUCao/troy-mode-trial` 的一个新克隆，设 `MSYS_NO_PATHCONV=1`，嵌套会话的设置和以往的试运行一样（指南第 9.4 节）。
- **许可。** 长期试运行许可的文字写的是 troy-pstack。试运行之前，Troy 更新它的措辞，让它也涵盖 tstack 及其临时副本。

运行内容：

1. init 事件列出 `tstack@inline`，没有 `troy-pstack`，角色都是 `tstack:troy-*`。
2. `/tstack:troy-mode upgrade troy-mode` 开出 `[rules] Upgrade troy-mode to 0.6.0`。它的检查通过，troy-init 合并它；之后代码搜索只在 `docs/rules.md` 及其镜像较早的行里找到 `troy-pstack`。
3. `/tstack:troy-mode continue`，事先给出对 `troy_approves_first` 问题的回答。测试经理 `tstack:troy-test-manager` 写 F02 的测试计划。它的写入被允许，它不靠权限规则读插件文件，运行后的检查通过，新的 `hooks.log` 行写着 `tstack:`，会话停在 "Waiting for Troy"。
4. `/poteto-mode hi` 被拒绝，提示指向 `/tstack:troy-mode`。
5. 用构建好的钩子再做一次探测 4：`tstack:troy-architect` 被允许，`troy-pstack:troy-architect` 被拒绝。
6. 只读地再查一次探测 2 的结论：已安装的插件从哪里运行。结果决定指南里关于副本的那句话（第 10 节）。

试运行花几美元，大部分是测试经理那次运行。构建 PR 的描述写明结果，以及试运行之后试验仓库的状态。

### 11.5 状态

| 什么时候 | 需求文档 7.2 中 F19 的状态 |
| --- | --- |
| 试运行通过后构建 PR 合并 | Runs on a sample project：试运行把 `ZJUCao/troy-mode-trial` 升级到 tstack 0.6.0，并在关掉 troy-pstack 的情况下用新名字运行了一个角色。Troy 的电脑仍在运行 troy-pstack。 |
| Troy 完成迁移，试点升级并用 tstack 运行了一个角色 | Used on a real project：Troy 的电脑运行 tstack 0.6.0，`ZJUCao/recipe-menu` 升级到它，并用新名字运行了 troy-mode。 |

状态更新各自单独开 PR。

## 12. 什么时候做（D199）

1. **等待。** 下面这些都合并之后才开始构建：F11 收尾的 PR（指南修正、试点报告和最终状态）、F15 设计 PR，以及 troy-pstack 里其他所有开着的 PR；而且没有会话在这个仓库里做构建。构建要改大约 130 个文件，所以同时开着的任何 PR 都会冲突。
2. **构建。** 一个会话，一个只有一个提交的 PR，包括第 11 节的测试、名字检查、埋 bug 和试运行。
3. **合并**，在所有检查都通过时。
4. **迁移。** Troy 的安静时段，能的话就在同一天（第 6 节和第 7 节）。然后在试点的下一个自然停顿处升级试点。
5. **状态。** 从新文件夹开状态 PR。
6. **之后。** 这之后才让第二个项目采用 troy-mode（F19 行）。构建合并前写的设计保留它们的名字（第 9 节），之后的设计和构建用新名字。

## 13. F19 怎样对应需求

| 需求 | F19 在哪里覆盖 |
| --- | --- |
| F19 行：`troy-pstack` 变成 `tstack` | 第 4.1 节和第 5 节 |
| F19 行：命令变成 `/tstack:troy-mode` 和 `/tstack:troy-init` | 第 4.1 节 |
| F19 行和 Q4：里面的 skill、agent 和文件夹名字不变 | 第 4.2 节 |
| F19 行：钩子对 agent 名的匹配 | 第 5.1 节和第 5.2 节 |
| F19 行：测试 | 第 11.1 节 |
| F19 行：文档 | 第 5.3 节和第 9 节 |
| F19 行：GitHub 仓库 | 第 6.1 节 |
| F19 行：README 和插件描述注明 Lauren Tan 的 pstack，并说明 troy-mode 是 Troy 自己的作品 | 第 4.3 节 |
| F19 行：一个 PR，在试点的 v0.1 发布之后、第二个项目之前 | 第 12 节 |
| 第 8 节：不改上游文件，合并上游保持容易 | 第 5.3 节 |
| 第 8 节：语言，CI 检查 | 第 5.4 节和第 11.2 节 |
| 第 8 节：Python 环境 | 第 6.4 节 |

## 14. 不在 F19 里的

- 给 skill、前缀之后的 agent 名、插件里的文件夹、`.troy-mode/`、troy-check、troy-init 或 `setup-pstack` 改名。
- 修改已批准的设计或修改记录（第 9 节）。
- 改写本仓库或项目的 git 历史（需求文档第 9 节）。
- 删除旧文件夹、旧环境或旧的缓存文件夹。Troy 以后再做。
- 一个能发现第二个 troy-mode 插件的钩子。第 7 节的检查和指南问题表里的那一行已经覆盖。
- 在构建 PR 里更新仓库之外的记忆和笔记。

## 15. 需要 Troy 决定的事项

F19 使用 D191 到 D199。Troy 于 2026-11-16 接受了全部推荐答案，并同意在构建的试运行之前改写长期试运行许可，让它涵盖 tstack（第 11.4 节）。

| 编号 | 问题 | 选项 | 推荐并已批准 |
| --- | --- | --- | --- |
| D191 | GitHub 仓库 `ZJUCao/troy-pstack` 要改名为 `ZJUCao/tstack` 吗？ | A：在构建 PR 合并后的安静时段改名。Troy 在仓库设置里改，或在聊天里说可以，由会话运行 `gh repo rename`。描述随之改，每个克隆设好远程（第 6.1 节）。B：仓库名不变，只给插件改名。C：新建仓库 `ZJUCao/tstack`，把旧仓库归档。 | A。GitHub 会转发旧链接、克隆和 API 调用，所以什么都不会坏，仓库也和插件一致。B 让每个克隆地址和链接都留着旧名字。C 把修改记录链接的 issue 和 PR 分到两处。 |
| D192 | 文件夹 `D:\Troy\Projects\troy-pstack` 怎么办？ | A：在 `D:\Troy\Projects\tstack` 新克隆一份作为 marketplace，复制本地设置和项目记忆。旧文件夹原样不动，再也不拉取 `main`，直到没有会话需要它，然后由 Troy 删除（第 6.2 节）。B：就地给文件夹改名，修好它的 9 个 worktree，期间所有会话都停下。C：文件夹名不变。 | A。已安装的插件从这个文件夹运行（探测 2），在会话运行时移动它，会挡住它们的工具调用。新克隆让它们能做完。B 需要一个什么都不运行的时刻，已归档的会话也会丢掉文件夹。C 留下一个叫 troy-pstack 的文件夹，钩子的 Read 规则得一直匹配它。 |
| D193 | marketplace 叫什么，插件版本是多少？ | A：marketplace 叫 `tstack`，安装 ID 为 `tstack@tstack`；版本 0.6.0，或构建合并时下一个空着的次版本号（第 5.5 节）。B：marketplace 仍叫 `troy-pstack`，ID 为 `tstack@troy-pstack`。C：tstack 从 1.0.0 开始。 | A。marketplace 反正要为新文件夹重新添加，改名不多花什么。次版本号的一步让每个项目的版本历史从 0.5.0 接着走。1.0.0 会宣称一种谁也没决定过的稳定性。 |
| D194 | Troy 的电脑怎样从 `troy-pstack@troy-pstack` 0.5.0 迁到 tstack？ | A：在一个安静时段按第 7 节的步骤：先卸载 troy-pstack，删除它的 marketplace，添加新文件夹的 marketplace，安装 `tstack@tstack`，用 `plugin list` 检查，重启 Claude Code。B：先装 tstack，以后再卸载 troy-pstack。C：同 A，但把 troy-pstack 停用而不卸载，方便退回。 | A。两个都开着时，每个插件的钩子都拒绝另一个的角色写文件（探测 2 和 4），所以它们绝不能同时运行，而 B 会让它们同时运行。C 留着一个指向将被删除的文件夹的 marketplace；只要旧文件夹还在，第 7 节就给出了退回的办法。 |
| D195 | 已有的项目怎样迁移？ | A：在每个项目的自然停顿处运行 `/tstack:troy-mode upgrade troy-mode`：`ZJUCao/troy-mode-trial` 在构建的试运行里，`ZJUCao/recipe-menu` 在 Troy 迁移之后。升级替换 troy-init 拥有的文件，给 `rules.md` 加一行，并且只在 `config.toml` 和 `pyproject.toml` 里 troy-init 写的两行注释没被改过时改写它们（第 8 节）。B：同 A，但那两行注释不动。C：同 A，那两行注释手工改。 | A。升级之后，代码搜索只会在 `docs/rules.md` 的历史行里找到旧名字。改写只碰每个文件里已知的一行，绝不碰别人改过的行。B 留下两行注释，提到一个已不存在的插件。C 要靠记得。 |
| D196 | mamba 环境叫什么？ | A：`tstack`，在安静时段从 `environment.yml` 创建。`troy-pstack` 留到旧文件夹删除时一起删除（第 6.4 节）。B：仍叫 `troy-pstack`。 | A。环境以它的系列命名，而这个系列现在叫 tstack（F03 设计 D26，需求文档第 8 节）。创建只要几分钟，CI 不用它，旧环境在此期间照常可用。 |
| D197 | 哪些文字保留旧名字？ | A：历史保留旧名字：构建合并前批准的设计、修改记录、需求文档文首的状态行、试点报告、链接、git 历史，以及仓库之外的笔记。README 和 `LICENSE` 写明 "formerly troy-pstack"。其余的都改（第 9 节）。B：每一处都改，包括已批准的设计，每份都升一个版本。C：只改插件身份、匹配规则、代码和测试，文档都不改。 | A。记录如实反映发生过的事，比如 F13 的试运行看到的是 `troy-pstack:poteto-mode`；而 Troy 或角色干活时读的一切都用新名字。B 要改写 28 份已批准设计里的 268 行，还会让它们的试运行记录声称从没发生过的事。C 会让指南叫 Troy 输入已经不存在的命令。 |
| D198 | 构建怎样检查？ | A：由另一个 agent 根据本设计修改和补充测试；CI 在每个 PR 上运行名字检查 `check_name.py`，再加一个检查各处名字一致的测试；埋 bug；在 `ZJUCao/troy-mode-trial` 上试运行，用放在名为 `tstack` 的文件夹里的 PR 副本，只为试运行的会话关掉 troy-pstack：升级、一次角色运行、守卫，再做一次探测 4（第 11 节）。B：同 A，但不要名字检查，只在 PR 描述里做一次搜索。C：只有测试和埋 bug。 | A。改名失败的方式就是某处漏改。只有每个 PR 都运行的检查，才能防止会话（它们的笔记里满是旧名字）把它带回来。试运行花几美元，就在真实项目上证明角色在新名字下仍能写文件、读插件文件。 |
| D199 | 构建什么时候做？ | A：等 F11 收尾的 PR（指南修正、试点报告、最终状态）、F15 设计 PR 和 troy-pstack 里其他所有开着的 PR 都合并，而且没有会话在这个仓库里做构建。Troy 的迁移能的话就在同一天，第二个项目在那之后才采用 troy-mode（第 12 节）。B：现在就开始，最后再在其他 PR 之上变基。C：还要等 F15 到 F18 都构建完。 | A。构建要改大约 130 个文件，所以同时开着的任何 PR 都会冲突，B 就得手工解决这些冲突。C 白白推迟改名：之后的功能直接用新名字构建就是了。 |

需求文档 1.40 记录了批准的改动：

- F19 行说明 F19 构建什么，引用 D191 到 D199：仓库改名（D191）、新文件夹（D192）、marketplace `tstack` 和下一个次版本号（D193）、Troy 的迁移先卸载 troy-pstack（D194）、项目升级及那两行注释（D195）、环境 `tstack`（D196）、保留旧名字的历史（D197）、检查和试运行（D198），以及顺序（D199）。
- 第 8 节，语言：CI 还检查现行文字不再提到旧插件名（`troy-mode/dev/check_name.py`，D198）。
- 需求文档里其余的出现，在构建 PR 里随其余改名一起改，好让改名仍是一个 PR。

## 16. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-16 | 初稿，含第 3 节的探测。 |
| 1.0 | 2026-11-16 | Troy 批准，含 D191 到 D199，全部采用推荐答案。 |
