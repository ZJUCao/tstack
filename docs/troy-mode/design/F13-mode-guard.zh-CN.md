# F13 设计：模式守卫

> 本文件是 [`F13-mode-guard.md`](F13-mode-guard.md) 的中文镜像，同步自英文版 1.0（2026-11-14）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.33](../requirements.zh-CN.md#72-功能列表) 中的 F13 |
| 版本 | 1.0 |
| 日期 | 2026-11-14 |
| 状态 | Troy 已于 2026-11-14 批准，含 D121 到 D126。 |
| 事实来源 | 英文版 [`F13-mode-guard.md`](F13-mode-guard.md)。本文件是中文镜像。 |

## 1. 范围

F13 让 poteto-mode 不进入 troy-mode 项目。需求文档 3.2 说按项目选模式：troy-mode 项目用 troy-mode，其他地方用 poteto-mode。Troy 敲错命令时，F13 让这个选择仍然成立。它交付：

1. **一个 hook 条目**，放在插件的 `hooks/hooks.json` 里。在有 `.troy-mode/` 文件夹的项目里，它拒绝 `/poteto-mode` 和 `/no-comments`，不论带不带插件前缀，在技能的内容到达 Claude 之前就拒绝。Troy 会看到一条提示：请改用 `/troy-pstack:troy-mode`（第 3 到第 7 节）。
2. **测试**：这个 hook 的测试，以及对 F05 的 `hooks.json` 测试的更新（第 11 节）。
3. README 的"troy-mode or poteto-mode"表格下**加一句话**，指南的问题表里加一行，中英文都加（第 9 节）。README 只有英文。

**为什么。** 在 troy-mode 项目里，poteto-mode 和 troy-mode 在五个地方冲突：

1. 它的 `poteto-agent` 委托代理写代码，而 F05 的 hook 会拒绝这些写入，因为在那里只有 6 个角色可以写（F05 D40）。
2. 主会话会自己写代码，绕过角色审查和 R08。
3. `/no-comments` 启动 `comment-sicko` 代理，它会删掉 R05 要求的文档注释。
4. 它的 PR 混合多个阶段，违反 R01 和 R02。
5. 它的 shipping 和 autopilot 剧本会合并 Troy 必须批准的设计 PR（R18）。

不论改动是哪种模式做的，CI 都会检查 PR 规则（需求文档 3.2），但那要等工作做完以后。守卫在任何工作开始之前就把它拦下。

F13 不修改任何上游文件：`poteto-mode`、`no-comments`、`poteto-agent` 和 `comment-sicko` 保持原样（需求文档第 8 节）。在 troy-mode 项目之外，包括 troy-pstack 本身，这两个命令照常可用。

本设计中关于 Claude Code 的事实来自它 2026-11-14 的 hooks 和 skills 文档，以及第 3.2 节的试运行。试运行用的是 Claude Code 2.1.321，即桌面应用自带的版本。

## 2. 位置

```text
hooks/
  hooks.json                  增加一个 UserPromptExpansion 条目（第 7.1 节）
troy-mode/
  hooks/
    troyhook/
      events.py               增加 UserPromptExpansion 的处理函数（第 7.2 节）
      modeguard.py            受守卫的命令名和提示信息（第 4 和第 6 节）
    tests/
      test_mode_guard.py      单元测试（第 11.1 节）
      test_hooks_json.py      为新条目更新（第 9 节）
README.md                     在"troy-mode or poteto-mode"里加一句话（第 9 节）
docs/troy-mode/guide/
  08-reference.md             "问题"里加一行，中文镜像同样加（第 9 节）
.claude-plugin/
  plugin.json                 下一个次版本号（第 7.4 节）
```

`hooks.json` 和事件名由 Claude Code 规定。`modeguard.py` 在 `troyhook` 里面，这里的模块名不以 `troy-` 开头（F05 第 2 节）。

## 3. 机制

### 3.1 Claude Code 提供什么

有两个 hook 事件能看到 Troy 敲的命令：

| 事件 | 何时运行 | 拿到什么 | 匹配器 |
| --- | --- | --- | --- |
| `UserPromptSubmit` | 每条输入都运行，在 Claude 看到之前。定时任务、后台子代理的报告、其他会话发来的消息也会触发它。 | `prompt`：原样输入的那一行，比如 `/poteto-mode build X`。 | 没有。每条输入都运行。 |
| `UserPromptExpansion` | 敲入的命令展开成技能或命令的内容时，在到达 Claude 之前。 | `command_name`、`command_args`、`command_source`、`expansion_type` 和 `prompt`。 | 按 `command_name` 匹配。 |

- 两个事件都可以拦截：在 stdout 输出 `{"decision": "block", "reason": "..."}`，或者用退出码 2 并把原因写到 stderr。这样输入就不会到达 Claude，Troy 会看到原因。
- 敲入的 `/skill` 不会触发 `Skill` 工具的 `PreToolUse` hook。那个 hook 只在 Claude 自己调用这个工具时运行。
- `poteto-mode` 和 `no-comments` 都设置了 `disable-model-invocation: true`，所以 Claude 不能通过 `Skill` 工具启动它们。只有 Troy 敲命令才能启动。

### 3.2 试运行

2026-11-14，一个临时的探测插件记录了每次 `UserPromptSubmit`、`UserPromptExpansion`，以及 `Skill` 和 `Agent` 的 `PreToolUse` 输入，并在一个模式文件要求时拦截这两个命令。嵌套的 `claude -p` 会话把它和本分支上的 troy-pstack 一起加载（`--plugin-dir`），用 haiku，只跑一轮。会话 scratchpad 里的两个临时 git 仓库充当项目：一个有 `.troy-mode/` 文件夹，一个没有。没有碰任何 GitHub 仓库。

| 运行 | Troy 敲的 | 项目 | 探测 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | `/no-comments` | troy-mode | 只记录 | `UserPromptSubmit` 拿到的 `prompt` 是 `/no-comments`。`UserPromptExpansion` 拿到的 `command_name` 是 `troy-pstack:no-comments`，`command_source` 是 `plugin`，`command_args` 为空，`prompt` 是 `/troy-pstack:no-comments`。然后技能运行了。 |
| 2 | `/no-comments` | troy-mode | `UserPromptExpansion` 用 JSON 拦截 | 被拦下。一轮都没跑，花费为 0。显示了提示信息（第 6 节）。 |
| 3 | `/troy-pstack:no-comments` | troy-mode | 同运行 2 | 同样被拦下。 |
| 4 | `/poteto-mode build the export feature` | troy-mode | 同运行 2 | `command_name` 是 `troy-pstack:poteto-mode`，`command_args` 是 `build the export feature`。被拦下。 |
| 5 | `/troy-pstack:poteto-mode build the export feature` | troy-mode | `UserPromptExpansion` 用退出码 2 拦截 | 被拦下，但提示里还显示了 hook 的命令行和"This hook comes from the f13-probe@inline plugin."。 |
| 6 | `/poteto-mode build the export feature` | troy-mode | `UserPromptSubmit` 用 JSON 拦截 | 被拦下。结果里写着 `prompt_kept: false`。 |
| 7 | `/poteto-mode build the export feature`，以 stream-json 输入发送，即桌面应用和 CLI 通信的方式 | troy-mode | 同运行 2 | 和运行 4 一样被拦下。 |
| 8 | `/poteto-mode say hi in two words` | 不是 troy-mode | 同运行 2 | 没有拦截。技能运行了。 |
| 9 | `/troy-pstack:bro hello there` | troy-mode | 同运行 2，加上第 7.1 节的匹配器 | `UserPromptExpansion` hook 没有启动。技能运行了。 |
| 10 | `/troy-pstack:troy-mode status` | troy-mode | 同运行 9 | hook 没有启动。troy-mode 运行了。 |
| 11 | `/POTETO-MODE hi` | troy-mode | 同运行 2 | 不是命令，所以没有展开。Claude 拿到的是文字，没有运行任何技能。 |
| 12 | `   /poteto-mode hi`，前面有空格 | troy-mode | 同运行 2 | 也不是命令。Claude 自己去找 poteto-mode 的 `SKILL.md`。 |
| 13 | "Load the poteto-mode skill with the Skill tool, then say hi." | troy-mode | 只记录 | Claude 用 `poteto-mode` 调用了 `Skill`。Claude Code 因为 `disable-model-invocation` 拒绝了这次调用，任何 `PreToolUse` hook 都还没启动。 |

所以：

- **它会触发，而且看得到命令。** 两个命令带不带前缀，`UserPromptExpansion` 都会运行，而且不论 Troy 敲哪种写法，它给出的都是完整名字 `troy-pstack:<name>`。
- **它能拦截，Troy 也看得到原因。** 被拦下的命令不花钱，因为一轮都不跑。JSON 给出干净的提示；退出码 2 会在提示里加上 hook 的命令行。
- **匹配器起作用。** hook 只为这两个命令启动。其他命令，包括 troy-mode 自己的命令，以及普通输入，都不会启动它。
- **桌面应用的路径可用。** stream-json 输入和 `-p` 文字的表现一样。

给以后试运行的一个坑：Git Bash 在 `claude.exe` 看到参数之前，就把 `/no-comments` 改写成了 `D:/Program Files/Git/no-comments`。试运行脚本设置了 `MSYS_NO_PATHCONV=1`。

### 3.3 选择（D121）

守卫是一个 `UserPromptExpansion` hook，按 `command_name` 匹配：

- 它看到的是解析后的命令，所以不需要解析 Troy 敲的文字，不带前缀和带前缀的名字看起来一样。
- 它的匹配器让它不为任何别的东西启动。其他每条输入和每个命令，在每个项目里，都不付任何代价。
- `UserPromptSubmit` 会在每个项目里为每条输入启动 Python，每次约 77 毫秒（第 7.3 节）。它读的是文字，所以还得分清一个命令和一条引用了命令的其他会话消息。

技能自己的说明做不了这件事：这些技能是上游的，保持不改。

## 4. 清单（D122）

| 命令 | 为什么在清单上 |
| --- | --- |
| `poteto-mode` | 第 1 节的五个冲突。 |
| `no-comments` | 冲突 3：它会删掉 R05 要求的文档注释。poteto-mode 在每次审查前都运行它。 |

匹配器接受任何插件前缀，或者没有前缀：`^([^:]+:)?(poteto-mode|no-comments)$`。所以 F19 把插件改名为 `tstack` 以后它照样有效，也能覆盖上游 pstack 的副本或者同名的个人技能。

**不在清单上的：**

- **其他 pstack 技能**，比如 `arena`、`swarm`、`tdd`、`figure-it-out`、`how`、`why` 和 `interrogate`。它们是工具，而不是一种工作方式。troy-mode 借用其中一些（需求文档 4.1，F17），而且它们都不合并 PR。它们启动写代码的子代理时，F05 的 hook 已经让这个子代理只读（D40）。
- **代理 `poteto-agent` 和 `comment-sicko`。** Claude 不用这两个命令也能启动它们，但在 troy-mode 项目里，F05 D40 已经拒绝不是角色的子代理的每次写入。在它们启动时就拒绝，只是让提示来得更早。
- **内置命令**，比如 `/simplify` 和 `/code-review`。它们是 Claude Code 自己的，troy-mode 的代码审查员也运行 `/code-review`。

## 5. 拒绝，不留例外（D123）

守卫直接拒绝，不是警告后放行。否则 poteto-mode 的说明仍然会主导会话，五个冲突照样会发生。

它没有例外，即使在用完就丢的试验分支上也没有（需求文档 5.9）：

- 需求文档 3.2 已经把 troy-mode 项目里的提问和试验交给 troy-mode 的轻量路径，不开 PR。
- 只在 F13 里留例外，并不能让 poteto-mode 在项目里正常工作。F05 的 hook 仍然会拒绝 `poteto-agent` 的每次写入，poteto-mode 只能做一半。
- 想用 poteto-mode 试一个想法，Troy 就在一个不是 troy-mode 项目的文件夹里做，比如一份不含 `.troy-mode/` 的代码临时副本。

## 6. 提示信息（D124）

原因里写出 Claude Code 解析后的命令名，用一个分句说明冲突，并指向 `/troy-pstack:troy-mode`。它有一行英文和一行中文，因为 hook 无法知道 Troy 正在用哪种语言，而且只有 Troy 会读到它。

`poteto-mode` 的提示：

```text
troy-mode: /troy-pstack:poteto-mode is off here. This project uses troy-mode (it has a .troy-mode folder), and poteto-mode's way of working breaks troy-mode's rules: only troy-mode's roles write code, each PR holds one stage, and Troy approves the designs. Type /troy-pstack:troy-mode and your request instead. It also handles questions and experiments, which open no PR.
troy-mode：这里停用 /troy-pstack:poteto-mode。本项目使用 troy-mode（有 .troy-mode 文件夹），而 poteto-mode 的工作方式会破坏 troy-mode 的规则：只有 troy-mode 的角色写代码，每个 PR 只放一个阶段，设计要 Troy 批准。请改用 /troy-pstack:troy-mode 加上你的请求。提问和试验也用它，不开 PR。
```

`no-comments` 的提示里，"and"后面的冲突换成"/no-comments deletes doc comments that troy-mode's rule R05 requires"，中文换成"而 /no-comments 会删除 troy-mode 规则 R05 要求的文档注释"。其余相同。

Claude Code 会在原因上面加一行自己的话，在下面附上敲入的命令。试运行里显示成这样（这里把原因缩短了）：

```text
UserPromptExpansion operation blocked by hook:
troy-mode: /troy-pstack:poteto-mode is off here. ...
troy-mode：这里停用 /troy-pstack:poteto-mode。...

Original prompt: /troy-pstack:poteto-mode build the export feature
```

提示里的命令名是 `command_name` 前面加一个 `/`。"Type ... instead"里的名字来自 `troyhook` 的插件前缀常量，所以 F19 改名时它会和其他 hook 一起改。

## 7. 怎样实现（D125）

### 7.1 `hooks.json` 条目

`hooks/hooks.json` 增加第六个事件：

```json
"UserPromptExpansion": [
  {
    "matcher": "^([^:]+:)?(poteto-mode|no-comments)$",
    "hooks": [
      {
        "type": "command",
        "shell": "bash",
        "command": "<the same interpreter pick as the other entries> ... troy_hook.py UserPromptExpansion",
        "timeout": 10
      }
    ]
  }
]
```

- 命令就是其他条目的命令，只换了事件名，所以解释器的选择、`TROY_MODE_PYTHON` 和找不到 Python 时的规则都不变（F05 第 10 节）。
- 匹配器是作用在 `command_name` 上的正则表达式，两头都锚定，所以 `troy-pstack:no-comments-extra` 或 `my-poteto-mode` 不匹配。
- `"timeout": 10`，和其他每个条目一样。
- `description` 字段在 F05 旁边写上 F13。

### 7.2 处理函数

`troyhook/events.py` 的处理函数表里增加 `user_prompt_expansion`，`troyhook/modeguard.py` 存放受守卫的命令名、两个分句和提示信息：

1. **门禁。** `main()` 已经会从输入的 `cwd` 找到项目（F05 第 4 节）。在 troy-mode 项目之外，hook 以退出码 0 退出，什么都不输出，命令照常运行。
2. **检查。** 处理函数读取 `command_name`，有第一个 `:` 时去掉它前面的部分，把剩下的和 `poteto-mode`、`no-comments` 比较。虽然匹配器已经过滤过，它还是再查一次，这样匹配器写错也不会拦住别的命令，测试也可以直接给它输入。其他情况什么都不返回。
3. **拒绝。** 遇到受守卫的命令名，它输出 `{"decision": "block", "reason": <message>}`，以退出码 0 退出。用 JSON 而不用退出码 2，是因为退出码 2 会把 hook 的命令行加进 Troy 看到的内容（第 3.2 节，运行 5）。

**出错。** 调用者总是主会话，所以适用 F05 D39 对主会话的规则：hook 内部出错时，在 stderr 输出一条通知，以退出码 1 退出，Claude Code 把它当作不拦截的错误，命令照常运行。找不到 Python 3.11 或更新版本时，`hooks.json` 的命令在 troy-mode 项目里以退出码 2 退出，和 F05 的每个条目一样，于是命令被拦下，显示"找不到 Python"的提示。不论哪种情况，troy-mode 项目之外都不会拦任何东西。

**不写日志。** 守卫不往 `hooks.log` 写任何内容（F05 第 10 节）。Troy 在屏幕上就能看到拒绝。F07 运行后的检查把主会话的日志行算作产品经理的，F08 的回顾会统计每一行，所以这里写一行会被当成 troy-mode 自己的错误。

### 7.3 速度

只有 Troy 敲这两个命令之一时 hook 才启动。试运行在 Troy 的电脑上，按 `hooks.json` 的命令形式，经过 Git Bash、Python、`troyhook` 的导入和门禁，每个项目计时 20 次：中位数 77 毫秒，最多 85 毫秒，troy-mode 项目内外都一样。这低于需求文档第 8 节 200 毫秒的目标。其他每条输入花 0 毫秒。

### 7.4 插件版本

F13 改变了项目拿到的内容，所以它的 PR 提高插件的次版本号（F10 设计第 6 节）：0.2.0 变成 0.3.0；如果 F12 或 F14 的实现先提高了，就用下一个空着的次版本号。试点在 Troy 下次更新插件时拿到守卫。试点不需要暂停：troy-mode 从不敲这两个命令。

## 8. 守卫能拦住什么、拦不住什么

它拦得住 Troy 在 troy-mode 项目的任何文件夹里（包括 worktree），从 CLI 或桌面应用敲 `/poteto-mode` 或 `/no-comments`，带不带前缀都一样。

它拦不住：

- **不是命令的文字。** `/` 前面有空格的一行，或者句子里的"用 poteto 的风格做"，都不会展开任何东西。Claude 自己不能加载这两个技能（运行 13），但可以读技能文件并模仿它，就像运行 12 开始做的那样。F05 的 hook 仍然拒绝 `poteto-agent` 和 `comment-sicko` 的每次写入，CI 也仍然检查 R01、R02、R05 和 R19。
- **没有 `.troy-mode/` 的项目。** 这是有意的设计：在那里 poteto-mode 才是对的选择（需求文档 3.2）。

## 9. 对已有功能的改动

- **F05。** `hooks.json` 增加第 7.1 节的条目。`test_hooks_json.py` 期望 6 个事件，带第 7.1 节的 `UserPromptExpansion` 匹配器。F05 的设计保持批准时的样子，新条目记录在本设计里。
- **F10。** README 的"troy-mode or poteto-mode"表格下面加一句话："In a troy-mode project, a hook refuses `/poteto-mode` and `/no-comments` and points to troy-mode (F13)."指南的 `08-reference.md` 在"问题"里加一行："`/poteto-mode` or `/no-comments` was refused"，处理办法是"Use `/troy-pstack:troy-mode <request>`; to try poteto-mode, use a folder that is not a troy-mode project."它的中文镜像加同样的一行。
- **F19。** 改名会修改 `troyhook` 的插件前缀常量，提示信息用的就是它。匹配器不用改。
- **F16。** troy-mode 把 poteto-mode 的 `eval` 和 `hillclimb` 剧本当文件来读（需求文档 4.1）。守卫只拒绝敲入的命令，所以不影响 F16。

## 10. F13 怎样对应需求

| 需求 | F13 在哪里覆盖 |
| --- | --- |
| F13 一行：hook 拒绝 Troy 敲的 `/poteto-mode` 和 `/no-comments` | 第 3.3、4 和 7 节 |
| F13 一行：提示改用 troy-mode | 第 6 节 |
| F13 一行：先确认 hook 能看到敲入的斜杠命令 | 第 3.2 节 |
| 3.2：troy-mode 项目用 troy-mode，其他地方用 poteto-mode | 第 5 和第 8 节 |
| 第 8 节：在 troy-mode 项目之外，hook 立即退出 | 第 3.3 和 7.2 节 |
| 第 8 节：每次调用低于 200 毫秒 | 第 7.3 节 |
| 第 8 节和第 9 节：不修改上游文件 | 第 1 和第 3.3 节 |

## 11. F13 怎样检查（D126）

### 11.1 测试

在处理函数写出来之前，由另一个代理根据本设计写 `test_mode_guard.py`，用 `unittest` 和 F05 测试的辅助代码：一个临时 git 仓库，加上从 stdin 送入的 hook 输入。对每个修改 `hooks/` 或 `troy-mode/hooks/` 的 PR，`troy-checks-tests.yml` 已经会在 Linux 和 Windows 上运行 hook 的测试。

| 组 | 用例包括 |
| --- | --- |
| 拒绝 | `troy-pstack:poteto-mode` 和 `troy-pstack:no-comments`，带和不带 `command_args`，在项目根目录、子文件夹和 worktree 里：输出 `decision` 为 `block` 的 JSON，退出码 0。`tstack:poteto-mode`、`pstack:no-comments` 和不带前缀的 `poteto-mode` 也被拒绝。 |
| 提示信息 | 写出带 `/` 的命令名，含这个命令对应的分句，指向 `/troy-pstack:troy-mode`，有英文和中文两行。 |
| 放行 | 没有 `.troy-mode/`：退出码 0，什么都不输出。不是 git 仓库。`troy-pstack:troy-mode`、`troy-pstack:bro`、`troy-pstack:poteto-help`、`troy-pstack:poteto-mode-extra`、`troy-pstack:no-comment`，以及为空或缺失的 `command_name`。 |
| 出错 | 处理函数里的异常：在 stderr 输出通知，退出码 1，stdout 什么都不输出。不是 JSON 的输入：退出码 1。 |
| 不写日志 | 一次拒绝之后 `hooks.log` 不变。 |
| `hooks.json` | 6 个事件。`UserPromptExpansion` 这一组有第 7.1 节的匹配器，超时 10，没有 `if` 规则，命令里写着 `troy_hook.py UserPromptExpansion`。把匹配器编译成正则表达式后，它匹配每个被拒绝的名字，不匹配任何放行的名字。 |

### 11.2 埋 bug

代码通过以后，在一份临时副本里一次埋一个 bug，每个都必须让某个测试失败：跳过门禁、不锚定的匹配、保留前缀导致不带前缀的名字被放行、漏掉 `no-comments`、用退出码 2 代替 JSON、出错时拦截、写了日志行，以及匹配器缺 `^`。数字写进 PR 描述。

### 11.3 试运行

F13 的 PR 开出之前，用实现好的 hook 代替探测插件，把第 3.2 节的试运行再跑一遍：用 `--plugin-dir` 从 PR 分支加载 troy-pstack，在同样两个临时仓库里，设置 `MSYS_NO_PATHCONV=1`。预期：运行 2 到 4 和运行 7 被拒绝，显示第 6 节的提示；运行 8 到 10 不被拒绝。`hooks.json` 的命令在每个项目里计时 20 次，中位数写进 PR 描述。不需要 GitHub 仓库。

### 11.4 状态

| 时间点 | F13 在需求文档 7.2 中的状态 |
| --- | --- |
| F13 的 PR 在试运行通过后合入 | 在示例项目上跑通：在一个临时项目上的试运行里，hook 拒绝了 `/poteto-mode` 和 `/no-comments`（带和不带前缀），放行了其他命令和其他项目。 |
| 一个真实项目用上这个插件版本 | 在真实项目上使用：这个项目的每个会话里 hook 都开着。状态里写明它拒绝了几个命令，包括零个的情况。 |

状态更新是单独的 PR。

## 12. 不在 F13 里的

- 修改 `poteto-mode`、`no-comments`、`poteto-agent`、`comment-sicko` 或 `poteto-help`（需求文档第 9 节）。
- 在两个代理启动时拒绝它们，或者拒绝其他 pstack 技能（第 4 节）。
- 为试验留例外（第 5 节）。
- 拦住不用命令而模仿 poteto-mode 的文字（第 8 节）。
- 插件改名（F19）。

## 13. 需要 Troy 决定的事项

D101 到 D120 以及 D131 以后的编号属于同时在写的 F12 和 F14 设计，所以 F13 用 D121 到 D130。Troy 于 2026-11-14 接受了全部推荐答案。

| 编号 | 问题 | 选项 | 推荐并已批准 |
| --- | --- | --- | --- |
| D121 | hook 怎样看到 Troy 敲的命令？ | A：一个 `UserPromptExpansion` hook，按 `command_name` 匹配，试运行已经证明可行（第 3.2 和 3.3 节）。B：一个读取输入文字的 `UserPromptSubmit` hook。C：不用 hook，只在 troy-mode 的文档里写一句。 | A。不论 Troy 敲哪种写法，它拿到的都是解析后的名字，而且只为这两个命令启动，别的都不付代价。B 会在每个项目里为每条输入启动 Python，还要解析文字。C 靠记性，而 troy-mode 正是为了不靠记性。 |
| D122 | 拒绝哪些命令？ | A：只拒绝 `poteto-mode` 和 `no-comments`，来自任何插件或不带前缀都算（第 4 节）。B：A 再加上其他 pstack 技能，比如 `arena`、`swarm` 和 `tdd`。C：A 再加上在 Claude 启动 `poteto-agent` 和 `comment-sicko` 代理时拒绝。 | A。这两个命令承载 poteto-mode 的工作方式。其他技能是 troy-mode 借用或可能借用的工具，而 F05 已经让这两个代理在 troy-mode 项目里只读。接受任何前缀，改名为 `tstack` 以后守卫照样有效。 |
| D123 | 拒绝还是警告？有没有例外？ | A：拒绝，没有例外（第 5 节）。B：拒绝，但在名为 `experiment/*` 的分支上放行。C：警告后放行。 | A。troy-mode 已经能不开 PR 地处理试验（需求文档 3.2）。选 B 或 C，F05 的 hook 仍然会拒绝 poteto-agent 的写入，poteto-mode 只能做一半。真要用 poteto-mode 做试验，Troy 就用一个不是 troy-mode 项目的文件夹。 |
| D124 | 提示信息写什么，用什么语言？ | A：第 6 节的文字：命令名、一个分句说明冲突、`/troy-pstack:troy-mode`，中英文各一行。B：同样内容，只用英文，和 F05 的提示一样。 | A。只有 Troy 会读到它，而 hook 无法知道 Troy 在用哪种语言。两行不费什么。 |
| D125 | 怎样实现？ | A：在 `hooks/hooks.json` 里加一个运行 `troy_hook.py` 的 `UserPromptExpansion` 条目，加一个小的 `troyhook/modeguard.py`，沿用 F05 的门禁和出错规则，输出 JSON，不写 `hooks.log`（第 7 节）。B：A 再加上每次拒绝写一行 `hooks.log`。C：一个有自己门禁的独立脚本。 | A。它复用 F05 的解释器选择、门禁、出错处理和测试。写日志行会让 F07 运行后的检查和 F08 的回顾把 Troy 自己敲的命令算成 troy-mode 的错误。C 会重复写一遍门禁。 |
| D126 | F13 怎样检查？状态什么时候改？ | A：由另一个代理根据本设计写单元测试，埋 bug，再用实现好的 hook 把本设计的试运行跑一遍（第 11 节）。合入后状态为"在示例项目上跑通"。B：只做单元测试，状态为"已编写"。 | A。试运行只花几美分，不需要 GitHub 仓库，而且能像本设计的试运行证明探测插件那样证明实现好的 hook。 |

需求文档 1.33 记录了批准的改动：

- F13 行写明 F13 实现的内容：`UserPromptExpansion` hook（D121），带任何插件前缀的这两个命令（D122），拒绝且没有例外（D123），中英文的提示信息（D124），在 F05 的 hook 上实现、不写 `hooks.log`（D125），以及检查方式（D126）。
- 第 3.2 节写明守卫拒绝这两个命令，带不带插件前缀都一样（D122），而且没有例外，所以要用 poteto-mode 做试验，需要一个不是 troy-mode 项目的文件夹（D123）。
- 第 5.9 节写明临时分支不会关掉守卫（D123）。

## 14. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-14 | 初稿，含第 3.2 节的试运行。 |
| 1.0 | 2026-11-14 | Troy 批准，含 D121 到 D126，全部采用推荐答案。 |
