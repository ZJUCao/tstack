# F02 设计：与语言无关的检查

> 本文件是 [`F02-checks.md`](F02-checks.md) 的中文镜像，同步自英文版 1.2（2026-11-07）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.3](../requirements.zh-CN.md#72-功能列表) 中的 F02 |
| 版本 | 1.2 |
| 日期 | 2026-11-07 |
| 状态 | Troy 已于 2026-11-05 批准，含 D7 到 D14 |
| 事实来源 | 英文版 [`F02-checks.md`](F02-checks.md)。本文件是中文镜像。 |

## 1. 范围

F02 交付一个命令行工具 `troy-check`，以及一个 GitHub Actions 工作流，在 troy-mode 项目的每个 PR 上运行它。这个工具检查与项目语言无关的规则：

| 规则 | F02 检查什么 |
| --- | --- |
| R01 | PR 恰好有一个 commit。 |
| R02 | PR 标题写的是已知类型（F01 设计 D1），并且每个改动的文件都属于该类型允许改动的类别。 |
| R03 | 源码 PR 最多改 500 行、最多改 5 个文件，否则描述里要给出理由。 |
| R12 | 每个改动的英文文档都升了版本，且中文镜像与它一致。 |
| R16 | 改动的依赖文件会被标出来，交给架构师。 |
| R19 | commit 邮箱正确，commit 信息、PR 标题和 PR 描述里都没有 Claude 署名。 |
| R20（新增，D11） | 改动的文档和 PR 描述里都没有残留的模板标记或填写说明（F01 设计 D2）。 |

它还提供一个 `commit` 子命令，在 commit 生成之前检查这一个 commit 是否符合 R19。F05 的 hook 会用到它。

F02 不往项目里复制任何东西（F06），不做与语言相关的检查（F03），也不决定 Claude 何时合并（F07）。

## 2. 位置

在 troy-pstack 里，和 F01 的模板放在一起：

```text
troy-mode/
  checks/
    troy_check.py          entry point
    troycheck/             internal modules (the Developer's choice)
    config.default.toml    commented copy of the defaults in section 7
    workflow.yml           the workflow in section 8
    tests/                 unit tests (section 10)
```

在项目里，`troy-init`（F06）把这个文件夹复制到 `.troy-mode/checks/`，把工作流复制到 `.github/workflows/troy-mode.yml`（D8）。项目自己的设置放在 `.troy-mode/config.toml`。

## 3. 命令行接口

工具需要 Python 3.11 或更新版本，只用标准库（D7）。在 Windows 上用 `python` 运行，在 Linux 和 macOS 上用 `python3`。

### 3.1 `pr`

检查整个 PR。troy-mode 在每次推送前运行它，CI 在每个 PR 事件上运行它。

```text
python .troy-mode/checks/troy_check.py pr --base <ref> [--head <ref>] --title <text> [--body-file <path>] [--repo <path>] [--json]
```

| 选项 | 含义 |
| --- | --- |
| `--base` | 目标分支，例如 `origin/main` 或某个 commit SHA。PR 的改动是从 `--base` 和 `--head` 的合并基点到 `--head` 之间的 commit。 |
| `--head` | PR 的最后一个 commit。默认 `HEAD`。 |
| `--title` | PR 标题。 |
| `--body-file` | 存放 PR 描述的 UTF-8 文件。不提供时，R03 视为没有超限理由，R20 跳过描述。 |
| `--repo` | 仓库根目录。默认是当前文件夹所在的 git 顶层目录。 |
| `--json` | 输出 JSON 报告（第 3.3 节），代替文本报告。 |

它从合并基点那个 commit 读取 `.troy-mode/config.toml`，而不是从 PR 里读。PR 没法放宽用来检查它自己的规则。规则修改从下一个 PR 起生效。

### 3.2 `commit`

在 commit 生成之前，检查这一个 commit 是否符合 R19。

```text
python .troy-mode/checks/troy_check.py commit (--message-file <path> | --message <text>) [--email <address>] [--repo <path>] [--json]
```

| 选项 | 含义 |
| --- | --- |
| `--message-file`、`--message` | commit 信息。 |
| `--email` | 要检查的作者邮箱。默认取 `git var GIT_AUTHOR_IDENT` 里的邮箱，也就是 git 实际会用的那个。 |
| `--repo`、`--json` | 同 `pr`。 |

它从工作区读取 `.troy-mode/config.toml`。它也可以直接当 git 的 `commit-msg` hook 用：`python .troy-mode/checks/troy_check.py commit --message-file "$1"`。由哪些 hook 调用它，由 F05 决定。

### 3.3 报告和退出码

每条规则的结果是以下四种之一：

| 结果 | 含义 |
| --- | --- |
| `pass` | 规则满足。 |
| `warn` | PR 可以合并，但需要有人看一眼：软限制超了但给了理由，或者改了依赖文件。 |
| `fail` | PR 不能合并。 |
| `skip` | 这条规则不适用于这类 PR。 |

文本报告：

```text
troy-check pr: [F04 5/6 impl] Export history as CSV
Kind: impl, feature F04, stage 5/6. May change: source, dependencies.
pass  R01  1 commit.
pass  R02  4 files, all source.
warn  R03  612 changed lines in 4 files, over 500. Reason given: "Splits storage.py."
skip  R12  No documents changed.
warn  R16  Dependency files changed. Needs the Architect's approval.
      pyproject.toml
pass  R19  1 commit by 148482542+ZJUCao@users.noreply.github.com. No attribution.
pass  R20  No template markers.
Result: pass, 2 warnings.
```

JSON 报告（`--json`）：

```json
{
  "command": "pr",
  "ok": true,
  "title": {"kind": "impl", "id": "F04", "stage": "5/6", "summary": "Export history as CSV"},
  "results": [
    {
      "rule": "R16",
      "result": "warn",
      "message": "Dependency files changed. Needs the Architect's approval.",
      "details": [{"path": "pyproject.toml", "line": null, "message": "changed"}]
    }
  ]
}
```

只要有一个结果是 `fail`，`ok` 就是 false。标题解析不了时，以及 `commit` 子命令，`title` 为 null。

环境变量 `GITHUB_ACTIONS` 为 `true` 时，工具还会为每条 `fail` 或 `warn` 明细输出一条 GitHub 注解（`::error file=<path>,line=<n>::R12 ...`），并把文本报告追加到 `$GITHUB_STEP_SUMMARY`。使用 `--json` 时，注解改为输出到 stderr，保证 stdout 仍是合法的 JSON。

| 退出码 | 含义 |
| --- | --- |
| 0 | 没有 `fail`。 |
| 1 | 至少一个 `fail`。 |
| 2 | 工具无法运行：选项错误、不是 git 仓库、git 出错，或配置文件无效。 |

## 4. PR 标题

把 F01 设计 D1 的标题格式定死。空格只能有一个。编号和阶段名区分大小写。摘要至少要有一个非空格字符。

| 类型 | 格式 | 示例 |
| --- | --- | --- |
| 功能阶段 | `[<F-ID> <n>/6 <stage>] <summary>`，`<n>` 和 `<stage>` 只能是以下配对之一：1 `design`、2 `test-plan`、3 `mock`、4 `tests`、5 `impl`、6 `accept` | `[F04 3/6 mock] Export history as CSV` |
| bug 测试 | `[<B-ID> A/B test] <summary>` | `[B12 A/B test] Crash on empty history` |
| bug 修复 | `[<B-ID> B/B fix] <summary>` | `[B12 B/B fix] Crash on empty history` |
| 测试修正 | `[<F-ID or B-ID> test-fix] <summary>` | `[F04 test-fix] Wrong date format in F04-T03` |
| 其他 | `[docs] <summary>`、`[rules] <summary>`、`[refactor] <summary>` | `[rules] Add P01, no global state` |

`<F-ID>` 是 `F` 加两位或三位数字。`<B-ID>` 是 `B` 加 GitHub issue 编号。标题不符合任何格式时，R02 失败，R03 跳过。

## 5. 路径类别（R02）

每个改动的路径恰好属于一个类别。按下表顺序，第一个匹配上的类别生效：

| 顺序 | 类别 | 内置规则 | 由谁添加 |
| --- | --- | --- | --- |
| 1 | `config` | `.troy-mode/**`、`.github/**`、`docs/rules.md`、`docs/rules.zh-CN.md`、`.gitignore`、`.gitattributes`、`.editorconfig` | 项目配置 |
| 2 | `dependencies` | 无 | 语言包（F03）、项目配置 |
| 3 | `tests` | `tests/**`、`test/**` | 语言包（F03）、项目配置 |
| 4 | `docs` | `docs/**`、`**/*.md`、`LICENSE*` | 项目配置 |
| 5 | `source` | 其余所有文件 | 无 |

规则匹配从仓库根目录开始的完整路径，分隔符用 `/`。`*` 匹配一个文件夹名之内的任意字符，`**` 匹配任意层文件夹，`?` 匹配一个字符。

每类 PR 允许改动的类别（D9）：

| 类型 | 允许的类别 |
| --- | --- |
| `design`、`test-plan`、`accept`、`docs` | `docs` |
| `mock`、`impl`、`fix`、`refactor` | `source`、`dependencies` |
| `tests`、`test`（bug PR A）、`test-fix` | `tests`、`dependencies` |
| `rules` | `config`、`dependencies` |

重命名的文件按旧路径和新路径各检查一次。每个不允许改动的路径，R02 各报一次失败。

## 6. 检查

所有检查都比较合并基点和 `--head`。"改动"包括新增、修改、删除和重命名。

### 6.1 R01：一个 commit

统计从合并基点到 `--head` 的 commit 数，合并 commit 也算。恰好一个就通过，否则 R01 失败并列出这些 commit。

### 6.2 R02：一个阶段

解析标题（第 4 节），给每个改动的路径分类（第 5 节），这类 PR 不允许改动的路径逐个报失败。

### 6.3 R03：源码 PR 的大小

只适用于 `mock`、`impl`、`fix` 和 `refactor`，其他类型跳过。

- 行数是 `git diff --numstat --find-renames` 给出的新增行加删除行。二进制文件算 0 行。
- 匹配 `lock` 或 `generated` 规则（第 7 节）的文件，既不算行数，也不算文件数。
- 超过 500 行或超过 5 个文件时：描述的"Soft-limit reason"一节给了理由就是 `warn`，没给就是 `fail`。
- 理由是这一节去掉 HTML 注释后的文字。空、`None`、`None.` 和 `无` 都表示没有理由。

### 6.4 R12：中英文镜像

文档指以 front matter 开头、且 front matter 里有 `troy-doc` 的 `.md` 文件（F01 设计第 4 节）。`.troy-mode/` 下的文件不算文档：troy-init 把模板复制到这里，它们的文档头有意带着标记，`troy-doc` 也和项目自己的文档相同（F06 设计第 8 节）。对每个改动的文档：

1. 文档头有效：`troy-doc`、`lang`、`version`、`updated`、`status` 都在。`lang` 是 `en` 或 `zh-CN`。英文文档有 `mirror`，中文文档有 `mirror-of`。每个值都加了双引号。`version` 的格式是 `MAJOR.MINOR`。`updated` 的格式是 `YYYY-MM-DD`。
2. 配对文件在同一个文件夹里，且 `mirror` 和 `mirror-of` 互相指向对方。
3. 两者的 `troy-doc` 相同，`version` 也相同。
4. 修改过的英文文档，`version` 比合并基点时更高。新增的英文文档要和它的镜像一起加入。
5. 删除英文文档时，镜像也一起删除。
6. 在代码块之外，两者标题层级的顺序相同，对应表格的列数相同（D12）。

只改中文的 PR，满足第 1 到 3 点和第 6 点即可通过，这样可以单独修正翻译。

在 `--head` 时的整个仓库里，任意两个英文文档的 `troy-doc` 都不能相同。

### 6.5 R16：依赖文件

把每个属于 `dependencies` 类别的改动路径列为 `warn`。它从不失败，由架构师审查把关。

### 6.6 R19：commit 身份和署名

对 PR 里的每个 commit：

- 作者邮箱等于配置里的 `commit_email`。
- 提交者邮箱等于 `commit_email`，或者是 `noreply@github.com`。在 GitHub 网页上直接做的 commit 用的是这个邮箱。

对每条 commit 信息、PR 标题和 PR 描述，出现 Claude 署名时 R19 失败：

- 任何模式下都算署名的：提到 Claude 或 `anthropic.com` 邮箱的 `Co-Authored-By:` 行、"Generated with Claude Code"字样、指向 `claude.com/claude-code` 或 `claude.ai/code` 的链接，以及 `noreply@anthropic.com` 这个邮箱。
- 默认的 `strict` 模式下（D10），还包括任何大小写的完整单词 `Claude` 或 `Anthropic`。这和 Troy 的全局 CLAUDE.md 一致：commit 和 PR 里不允许提到 Claude。

配置里没有 `commit_email` 时，邮箱这部分给出 `warn` 并说明原因。

### 6.7 R20：模板标记（D11）

改动的文档或 PR 描述里，每个残留的模板标记或填写说明都报一次失败：

- 标记是前面不紧跟 `$` 的 `{{`，接着一段不含花括号、不换行、首尾都不是空格的文字，再接 `}}`。F01 的所有标记都是这个形状，例如 `{{feature-id}}`。花括号内侧带空格的代码，例如 GitHub Actions（`${{ github.sha }}`）、Vue、Jinja 的常见写法，都不会匹配。C++ 的大括号初始化，例如 `{{1, 2}, {3, 4}}`，也不会匹配。
- 填写说明是 `<!--`，可能跟着空格，然后是 `template:`。

代码块也要扫描，因为模板会把标记放在代码块里。`.github/` 和 `.troy-mode/` 下的文件不扫描，因为 PR 模板和复制过来的模板本来就带标记。列在 `allow_markers` 里的文件也不扫描。

每个失败都给出路径和行号。

## 7. 项目配置

`.troy-mode/config.toml`。每个键都可以不写。列表是在内置规则之上追加，从不替换。出现未知的键或类型不对时，工具以退出码 2 停止，免得一个拼写错误悄悄关掉某条规则。

```toml
[identity]
commit_email = "148482542+ZJUCao@users.noreply.github.com"  # R19. troy-init fills it in.

[paths]
config = []         # added to the config class
dependencies = []   # language packs add manifests, for example "pyproject.toml"
tests = []          # language packs add patterns, for example "**/test_*.py"
docs = []
lock = []           # not counted by R03, for example "uv.lock"
generated = []      # not counted by R03
allow_markers = []  # documents that hold {{ }} on purpose

[limits]
source_lines = 500  # R03
source_files = 5    # R03

[attribution]
mode = "strict"     # "strict" or "trailers" (D10)
```

## 8. GitHub Actions 工作流

`troy-mode/checks/workflow.yml`，由 `troy-init` 复制到 `.github/workflows/troy-mode.yml`：

```yaml
name: troy-mode checks
on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
permissions:
  contents: read
jobs:
  troy-check:
    name: troy-mode checks
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@<full commit SHA>
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0
      - name: Run troy-check
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
          PR_TITLE: ${{ github.event.pull_request.title }}
          PR_BODY: ${{ github.event.pull_request.body }}
        run: |
          checks=.troy-mode/checks
          if git cat-file -e "$BASE_SHA:$checks/troy_check.py" 2>/dev/null; then
            mkdir -p "$RUNNER_TEMP/base"
            git archive "$BASE_SHA" "$checks" | tar -x -C "$RUNNER_TEMP/base"
            checks="$RUNNER_TEMP/base/$checks"
          fi
          printf '%s' "$PR_BODY" > "$RUNNER_TEMP/pr-body.md"
          python3 "$checks/troy_check.py" pr --base "$BASE_SHA" --head "$HEAD_SHA" \
            --title "$PR_TITLE" --body-file "$RUNNER_TEMP/pr-body.md"
```

- `edited` 让标题或描述修改后重新检查。
- 基点 commit 里有检查程序时，就运行基点里的那份，所以 PR 改不了检查它自己的代码。第一个加入检查程序的 PR 运行它自带的那份。
- 标题和描述只通过环境变量进入 shell，从不直接拼进脚本，所以精心构造的标题没法执行命令。
- 用 `pull_request`，从不用 `pull_request_target`，对仓库只有读权限。
- 任务名 `troy-mode checks` 固定不变，这样才能把它设为必需检查（D14）。

## 9. 非功能需求

- **平台。** Windows 11、Linux 和 macOS。路径统一用 `/`。文件按 UTF-8 读取，输出也一律是 UTF-8，与控制台代码页无关，所以中文在中文区域设置的 Windows 控制台里也不会乱码。
- **速度。** `commit` 在 200 ms 内完成，这是 hook 的时间预算。在 1,000 个文件的仓库、50 个文件的 PR 上，`pr` 在 5 秒内完成。
- **安全。** 工具只读取 git 对象和文件，从不运行仓库里的代码，也不联网。
- **不需要环境。** 工具只用标准库，所以不需要任何环境，也不用安装包。PATH 上任何 Python 3.11 或更新版本都能运行它。Python 项目自己的环境用 mamba 和 uv 管理（需求文档第 8 节），由 F03 负责。
- **代码规则。** 虽然 troy-pstack 不是 troy-mode 项目，工具自己的代码也遵守 R04 到 R06，并使用 Google 风格的文档注释。

## 10. F02 怎么测试

测试先写，和实现放在同一个 PR 里（需求 Q10）。测试用 `unittest`，不用安装任何东西：`python -m unittest discover -s troy-mode/checks/tests`。每个测试在临时文件夹里建一个小 git 仓库。

| 组 | 用例包括 |
| --- | --- |
| 标题 | 每种类型都能解析。阶段编号和阶段名对不上。缺摘要。编号小写。连续两个空格。 |
| R01 | 一个 commit。两个 commit。合并 commit 也算。 |
| R02 | docs PR 里有源码文件。tests PR 里有依赖文件。跨类别的重命名。无法识别的标题。 |
| R03 | 500 行通过，501 行失败。501 行但给了理由是 warn。第 6 个文件。lock 文件不计入。二进制文件。docs PR 跳过。 |
| R12 | 没升版本。镜像没改。版本不一致。互指字段错误。新增英文文档没带镜像。标题层级不同。表格列数不同。值没加引号。只改中文的修正通过。只删了英文文档。`troy-doc` 重复。 |
| R16 | 改了依赖清单是 warn。没改就通过。 |
| R19 | 作者邮箱错误。GitHub 提交者允许。`Co-Authored-By` 署名行。strict 模式下出现单词。trailers 模式下同一个单词。没配置邮箱。 |
| R20 | 标记带行号。填写说明注释。C++ 大括号初始化通过。`${{ github.sha }}` 和 `{{ count }}` 通过。`allow_markers`。描述里的标记。`.github/` 不扫描。 |
| 命令行 | 退出码 0、1、2。JSON 结构。GitHub 注解。从合并基点读取配置。配置里的未知键。 |
| `commit` | 信息文件。从 `git var` 取作者邮箱。 |

troy-pstack 增加一个工作流 `.github/workflows/troy-checks-tests.yml`，在每个改动 `troy-mode/checks/` 的 PR 上，于 Linux 和 Windows 两个平台运行这些测试（D13）。

F02 合并后，状态改为"已编写"。等它的工作流在一个临时项目的 PR 上真正跑过之后，才改为"在示例项目上跑通"。F06 的 troy-init 会让这一步变得容易。

## 11. 不属于 F02 的内容

- 与语言相关的检查：R04 到 R07、R09 到 R11（F03）。
- 把检查程序和工作流复制进项目、填写 `commit_email`、把检查设为必需（F06）。
- Claude Code 的 hook（F05）。
- 阶段顺序，例如 PR 3 之前 PR 1 和 PR 2 是否已合并；以及功能或 bug 编号是否存在（F07）。

## 12. 需要 Troy 决定的事项

D1 到 D6 属于 F01 设计，F02 从 D7 接着编号。Troy 已于 2026-11-05 批准全部八项提议。

| 编号 | 待决定的事 | 提议 |
| --- | --- | --- |
| D7 | 检查程序用什么语言写。 | Python 3.11 或更新版本，只用标准库，测试用 `unittest`。每台 GitHub 运行机和你的电脑上都有 Python，它也是你的第一个语言包。TypeScript 需要每个项目都装 Node，C/C++ 项目也不例外。Bash 在 Windows 上不好用，做解析也弱。 |
| D8 | 项目怎么拿到检查程序。troy-pstack 是私有仓库，别的仓库的 CI 没有令牌就读不到它。 | `troy-init` 把检查程序复制到 `.troy-mode/checks/`，并记下插件版本。复制还能固定每个项目运行的规则版本。升级时在一个 `[rules]` PR 里重新运行 `troy-init`（F06）。 |
| D9 | 每类 PR 能改哪些文件。F01 把这个问题留给了 F02。 | 采用第 5 节的路径类别和表格。依赖文件可以在源码、测试和规则 PR 里改。`test-fix` 也接受 bug 编号，例如 `[B12 test-fix]`。 |
| D10 | R19 有多严。需求里的 R19 写的是"没有 Claude 署名"，你的 CLAUDE.md 还禁止任何提到 Claude 的地方。 | 默认 `strict`：commit 信息、PR 标题和 PR 描述里都不能出现 Claude 或 Anthropic 这两个词。与 Claude 有关的项目，例如调用 Claude API 的项目，设置 `mode = "trailers"`。需求文档和规则模板里 R19 的文字随之修改。 |
| D11 | 模板标记检查（F01 D2）没有规则编号，报告里没法指名。 | 新增规则 R20："合并的文档和 PR 描述里没有模板标记或填写说明。"硬性，由 CI 执行。这把 PR 描述也纳入了 D2。需求文档和规则模板都加上 R20。 |
| D12 | 按现在的写法，R12 只检查文档头。镜像可能版本对得上，却漏了新加的章节。 | R12 还要比较标题层级和表格列数（第 6.4 节第 6 点）。 |
| D13 | 检查程序自己的测试要有地方跑。troy-pstack 没有 CI。 | 给 troy-pstack 加 `.github/workflows/troy-checks-tests.yml`，在 Linux 和 Windows 上运行。这是新文件，不改上游的任何文件。 |
| D14 | "硬性"在 GitHub 上意味着什么。只有分支保护把检查设为必需时，检查失败才会挡住合并；而私有仓库只有在 GitHub 付费套餐下才有分支保护。 | 无论什么套餐，troy-mode 都不合并检查失败的 PR（F07）。仓库允许时，`troy-init` 再把 `troy-mode checks` 设为必需检查（F06）。Troy 目前用的是 GitHub 免费套餐（2026-11-05），所以暂时只靠 troy-mode 的合并步骤把关，`troy-init` 不打开这项设置。 |

需求文档 1.3 记录了批准后的修改：

- F02 那一行加上 R20 和 `commit` 子命令。
- R19 的文字随 D10 修改，第 6 节和规则模板加上 R20（D11）。
- 第 6 节写明由 troy-mode 的合并步骤执行硬规则（D14）。

F02 的 PR 合并时，F02 的状态改为"已编写"。

## 13. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-05 | 初稿。 |
| 1.0 | 2026-11-05 | Troy 批准，含 D7 到 D14。D14 记下了 Troy 的 GitHub 免费套餐。第 9 节说明工具不需要 Python 环境。 |
| 1.1 | 2026-11-05 | 第 3.3 节：使用 `--json` 时，注解输出到 stderr。实现时发现。 |
| 1.2 | 2026-11-07 | 第 6.4 节：R12 不把 `.troy-mode/` 下的文件当文档，和 R20 不扫描这里一样。否则 troy-init 复制到这里的模板会让每个初始化 PR 和之后每个改文档的 PR 都失败。构建 F06 时发现，Troy 于 2026-11-07 批准。 |
