# F06 设计：项目初始化（troy-init）

> 本文件是 [`F06-troy-init.md`](F06-troy-init.md) 的中文镜像，同步自英文版 1.7（2026-11-28）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.16](../requirements.zh-CN.md#72-功能列表) 中的 F06 |
| 版本 | 1.7 |
| 日期 | 2026-11-28 |
| 状态 | Troy 已于 2026-11-06 批准，含 D47 到 D56。第 8 节对 R12 的改动由 Troy 于 2026-11-07 批准。1.5 版加入 D213，由 Troy 于 2026-11-18 作为 tstack issue #48 批准。1.6 版加入 D289，即 D213 对引擎其他 uv 命令的后续，依据 Troy 2026-11-22 的长期同意批准。1.7 版加入 D291 到 D295，即 GitHub 上 R21 的分支规则（需求文档 1.71），由 Troy 于 2026-11-28 批准：D293 选 B，只加 R21 的规则集，其余按推荐。 |
| 事实来源 | 英文版 [`F06-troy-init.md`](F06-troy-init.md)。本文件是中文镜像。 |

## 1. 范围

F06 把一个文件夹变成 troy-mode 项目，并让其中 troy-mode 的文件保持最新。它交付一个技能 `/troy-pstack:troy-init` 和它背后的引擎，分三步：

1. **初始化**（需求文档 5.1 第 2 步）：标记文件夹，里面有配置、troy-check 及其 git hook、模板和进度文件；规则表；PR 模板；带 troy-check 任务的 CI 工作流。
2. **语言步骤**（5.1 第 4 步），在 Troy 批准架构之后：F03 的语言包和它的 CI 任务。
3. **升级**（F02 D8）：把 troy-mode 自己的文件更新到插件的当前版本。

每一步都作为一个只有一个 commit 的 `[rules]` PR 合入。troy-init 开出这个 PR，检查通过后合并它（D53）。在初始化的 PR 之前，以及缺少时在升级的 PR 之前，troy-init 还会在 GitHub 允许时，在 GitHub 上加上 R21 的分支规则（第 4.7 节）。

F06 不写需求文档、架构文档或其他任何项目文档（角色，F04）。它不启动角色，也不运行功能循环（F07）。它不为插件的文件写权限规则，因为 F05 的 hook 会放行这些读取（F05 D45）。

## 2. 位置

```text
skills/
  troy-init/
    SKILL.md                  Troy 输入的技能（第 3.1 节）
troy-mode/
  init/
    troy_init.py              引擎的入口（第 3.2 节）
    troyinit/                 内部模块（由开发者决定）
    tests/                    单元测试（第 11.1 节）
```

- 引擎和 troy-check 一样，使用 Python 3.11 或更新版本，只用标准库（F02 D7）。
- `SKILL.md` 按需求文档第 8 节的要求设置 `disable-model-invocation: true`，所以只有 Troy 输入时才运行。F07 不能调用这样的技能，所以 F07 直接运行引擎（第 10 节）。
- 技能用 `${CLAUDE_PLUGIN_ROOT}/troy-mode/init/troy_init.py` 指明引擎。Claude Code 会替换插件技能正文里的 `${CLAUDE_PLUGIN_ROOT}`。

## 3. 命令

### 3.1 技能

| 命令 | 步骤 |
| --- | --- |
| `/troy-pstack:troy-init` | 初始化 |
| `/troy-pstack:troy-init lang python` 或 `lang cpp` | 语言步骤 |
| `/troy-pstack:troy-init upgrade` | 升级 |

技能先用 `--dry-run --json` 运行引擎。每一步在 `main` 上都会停下（第 4.1 节和第 5.1 节），所以语言步骤和升级要先创建这一步的分支（第 7 节第 2 步），再做试运行；升级没有东西要改时，再把这个分支删掉。初始化时如果文件夹还没有 `origin`，试运行的问题会指出缺少 `origin` 和所在分支；第 7 节的前两步会解决它们。它用一条消息、用 Troy 的语言，只问没有明确默认值的事：要不要创建私有 GitHub 仓库，并在 Troy 的套餐允许时加上 R21 的分支规则（D52、D292），要不要给已有的仓库加上 R21 的分支规则（D291），要不要替换一个不是 troy-init 写的文件（D48），以及语言步骤里环境所属的系列。然后它运行引擎，把结果走一遍第 7 节的 PR 流程，最后报告做了什么、没做什么。

### 3.2 引擎

```text
python troy_init.py setup   [--project-name <name>] --email <address> [common options]
python troy_init.py lang    (python | cpp) [--project-name <name>] [--environment <name>]
                            [--series <folder>]... [--package <name>] [--mamba <path>]
                            [--env-prefix <path>] [--no-env] [common options]
python troy_init.py upgrade [common options]
python troy_init.py branch-rule [--rules <file>] [--rulesets <file>] [--repo <path>] [--json]

common options: [--repo <path>] [--date <YYYY-MM-DD>] [--replace <path>]... [--dry-run] [--json]
```

| 选项 | 含义 |
| --- | --- |
| `--project-name` | 规则表和构建文件里的名字。默认是仓库文件夹的名字。 |
| `--email` | R19 要求的提交邮箱。技能传入 Troy 全局 CLAUDE.md 里的那个。 |
| `--environment`、`--series` | mamba 环境，以及系列中各成员的文件夹（F03 设计 8.1）。默认是项目名和 `.`。 |
| `--package` | 只用于 Python：`src/` 下的包名。默认是项目名的蛇形写法。 |
| `--mamba` | mamba 的路径，用于它不在 PATH 上也不在 `$MAMBA_EXE` 里的情况。 |
| `--env-prefix` | 在这个文件夹里创建环境，而不是创建一个有名字的环境。试运行用它，这样不会留下有名字的环境。 |
| `--no-env` | 不创建环境，也不编译锁文件。测试和 `build_sample.py` 用它。 |
| `--date` | 写进文件的日期。默认是今天。 |
| `--replace` | 不是 troy-init 写的、但允许它覆盖的路径（D48）。 |
| `--dry-run` | 只检查和规划，什么也不改。 |
| `--json` | 用 JSON 输出报告。 |
| `--rules` | 只用于 `branch-rule`：一个文件，里面是 GitHub 对 `main` 上正在生效的规则的回答（第 4.7 节）。不给时，表示还没有任何规则生效。 |
| `--rulesets` | 只用于 `branch-rule`：一个文件，里面是 GitHub 列出的仓库规则集（第 4.7 节）。不给时，表示仓库没有规则集。 |

引擎只修改文件和仓库的 git 配置。它从不提交、推送或调用 GitHub：这些由主会话来做（F04 D29）。`branch-rule` 什么也不改：它从技能保存的文件里读 GitHub 的回答，说明技能应该加哪些规则集（第 4.7 节）。

### 3.3 报告和退出码

报告列出每个路径和对它的动作（`create`、`replace`、`append`、`edit`、`delete` 或 `keep`）、每个冲突，以及下一步。用 `--json` 时，还列出需要暂存的确切路径。

| 退出码 | 含义 |
| --- | --- |
| 0 | 完成，或者试运行没有发现障碍。 |
| 1 | 在改动任何东西之前停下：某个前提条件不满足，或者某个文件有冲突。报告会说明是哪一个。 |
| 2 | 引擎无法运行：选项错误、不是 git 仓库，或者 git 出错。 |

## 4. 初始化

### 4.1 开始之前

以下条件都满足，初始化才会进行：

- 这个文件夹是 git 仓库的根目录，有一个 `origin` 远程仓库，它的 `main` 分支存在并且已经 fetch 过。技能会让 `origin` 是一个 GitHub 仓库（D52）。引擎不关心它在哪里，所以测试可以用本地仓库；
- 当前分支不是 `main`（PR 流程会先从 `origin/main` 创建 `troy-mode/init`）；
- 仓库里还没有 `.troy-mode/` 文件夹（否则请用 `upgrade`）；
- 初始化要写的文件都不存在，除非用 `--replace` 点名（D48）。

初始化可以在产品经理写需求文档之前或之后运行。它从不碰 `docs/requirements*.md`，而且 PR 流程只暂存初始化自己的文件，所以初始化之前写好的文档不会进入它的 PR。

### 4.2 文件

| 项目中的路径 | 来自 troy-pstack | 说明 |
| --- | --- | --- |
| `.troy-mode/config.toml` | `troy-mode/checks/config.default.toml` | 按第 4.3 节填写。 |
| `.troy-mode/checks/` | `troy-mode/checks/`，不含 `tests/`、`workflow.yml`、`config.default.toml` 和缓存 | troy-check 以及 F05 的 `git-hooks/`。 |
| `.troy-mode/templates/` | `troy-mode/templates/` | 所有模板和 README，中英文，原样复制。角色从这里填写模板（F04 共用规则第 7 条）。 |
| `.troy-mode/install.toml` | 由初始化生成 | 第 4.6 节。 |
| `.troy-mode/progress.md` | `troy-mode/templates/progress.md`，已填写 | 只在本地，被 git 忽略（Q8）。阶段为"初始化"，下一步为"需求"或"架构"。 |
| `docs/rules.md`、`docs/rules.zh-CN.md` | `troy-mode/templates/rules.md` 及其镜像 | 第 4.4 节。 |
| `.github/workflows/troy-mode.yml` | `troy-mode/checks/workflow.yml` | troy-check 的任务。语言步骤再加入语言包的任务。 |
| `.github/pull_request_template.md` | `troy-mode/templates/pull-request.md` | 原样复制。R20 不扫描 `.github/`。 |
| `.gitignore` | 追加几行 | `.troy-mode/progress.md`。文件不存在时就新建。 |

- 按 F02 的内置模式，每个路径都属于 `config` 类别，所以初始化的 PR 是一个有效的 `[rules]` PR。
- troy-init 新建的文件都用 LF 换行写入。它就地修改的文件，例如已有的 `.gitignore`，在工作区里保留原来的换行符：在开启 `core.autocrlf` 的 Windows 检出里就是 CRLF，git 提交的仍是 LF。
- git hook 脚本用 `git add --chmod=+x` 暂存，因为 Windows 上的工作区不会记录可执行位。

### 4.3 配置

`.troy-mode/config.toml` 就是 F02 带注释的默认文件，填入以下值：

```toml
[identity]
commit_email = "148482542+ZJUCao@users.noreply.github.com"

[paths]
# The patterns of every language pack, so that a pack's files already have
# their classes when the language step's PR is checked (F06 design D49).
config = [".clang-format", ".clang-tidy", "include/troy/not_implemented.h"]
dependencies = ["pyproject.toml", "environment.yml", "requirements*.lock", "requirements*.in",
                "CMakeLists.txt", "**/CMakeLists.txt", "cmake/**", "CMakePresets.json"]
tests = ["**/test_*.py", "**/*_test.py", "**/conftest.py", "**/*_test.cc", "**/*_test.cpp"]
lock = ["requirements*.lock"]
```

- `commit_email` 来自 `--email`。如果仓库的 `git config user.email` 不同，报告会指出，技能会把仓库自己的 `user.email` 设成它，这样下一次提交就能通过 R19。
- 在语言步骤之前，`[lang]` 表保持默认文件里的注释。
- **为什么写入所有语言包的模式（D49）。** troy-check 从 PR 的合并基点读取路径类别，所以 PR 不能放宽评判它自己的规则（F02 设计 3.1）。没有这些模式，语言步骤里的 `pyproject.toml` 或 `CMakePresets.json` 在合并基点上就属于 `source`，而 `[rules]` PR 不能修改源码（R02）。代价是 Python 项目的配置里也写着它并没有的 C/C++ 文件。

### 4.4 规则表

初始化在 `docs/rules.md` 及其镜像里填入项目名和日期，并删除所有 template 注释。两者的 `version` 都保持 "1.0"。这样初始化的 commit 能通过 R12 和 R20。

### 4.5 git 和 GitHub 设置

- **git hook。** 如果 `.troy-mode/checks/git-hooks` 存在，初始化就把 `core.hooksPath` 设成它（F05 D44）。在其他克隆里，由 F05 的 `SessionStart` hook 设置。
- **分支规则。** 在初始化的 PR 之前，技能在 GitHub 允许时给 `main` 加上 R21 的规则集（第 4.7 节）。
- **不设必需检查（D293）。** troy-init 不再在 GitHub 上把 `troy-mode checks` 设为必需。1.6 版在初始化 PR 合入后执行的那一步去掉了：那一步先问 GitHub 能不能用经典分支保护，再提出把检查设为必需（F02 D14）。troy-mode 的合并步骤仍然只在检查通过时才合并 PR（R18，F02 D14）。

git 和 GitHub 里的其他设置都不改。

### 4.6 安装记录

`.troy-mode/install.toml` 记录：来自 `.claude-plugin/plugin.json` 的 troy-pstack 版本；插件文件夹是 git 代码目录时，troy-pstack 的 commit；每一步的日期；语言包；以及一张 `[files]` 表，列出 troy-init 拥有的每个文件的 SHA-256 哈希。troy-init 拥有它整份复制的文件：troy-check、模板、PR 模板、工作流和语言包的整份文件。升级时用这些哈希区分没改过的文件和被人改过的文件（D54）。`config.toml`、规则表、`.gitignore` 和构建文件一旦写入，就归项目所有。

### 4.7 R21 的分支规则（D291 到 D293）

R21 规定每个改动都通过 PR 进入 `main`。在打开了 git hook 的每个克隆里，hook 拒绝在 `main` 上提交和推送 `main`（F05 D44）。在 GitHub 上，Troy 于 2026-11-28 决定由分支规则而不是 CI 检查来执行它，因为 CI 检查只在 PR 上运行，看不到直接推送（需求文档 1.71）。

**GitHub 上加什么。** 一个仓库规则集，和 Troy 的会话 2026-11-28 手动给 `ZJUCao/recipe-menu` 加的那个（id 28299856）相同（D293）：

| 字段 | 值 |
| --- | --- |
| 名字 | `R21: main only through PRs` |
| 目标和执行方式 | `branch`，`active` |
| 可绕过者（bypass actor） | 无 |
| 条件 | `~DEFAULT_BRANCH`，所以它跟着 `main` 走 |
| 规则 | `deletion`；`non_fast_forward`；`pull_request`，要求 0 个批准，不要求代码所有者审查、最后一次推送的批准、推送后作废旧审查，也不要求解决所有讨论 |

- 请求体是插件里的文件 `troy-mode/init/rulesets/r21.json`。它不复制进项目。
- 没有可绕过者，所以 Troy 虽然是仓库管理员，也不能推送 `main`。只有 Troy 在 GitHub 的设置里修改或删除规则集。
- 所有合并方式都保持允许。troy-mode 用 rebase 合并（第 7 节第 8 步），Troy 也可以在 GitHub 上合并。
- 它不要求任何状态检查（第 4.5 节）。
- 请求体里没写的参数由 GitHub 用默认值补上。recipe-menu 的规则集里 `require_extra_approval_for_unattributed_changes` 是 true，而创建它的请求里并没有这一项。

**GitHub 在哪里允许（D292）。** GitHub 在任何套餐的公开仓库上都执行规则集，在私有仓库上只有付费套餐才执行，比如 Pro，GitHub 学生包（Education pack）就含 Pro。经典分支保护也随同样的套餐提供。troy-init 读不到套餐，因为 gh 的令牌没有 `user` 权限范围，而且套餐会变：2026-11-07，当时还是私有的 `ZJUCao/troy-mode-trial` 对下面的探测回答 403（F10 指南 `02-start.md`），而 2026-11-28，Troy 的两个私有仓库回答的是 404。所以技能对每个仓库都问一次 GitHub：`gh api repos/<owner>/<project>/branches/main/protection` 在套餐没有分支保护的地方回答 403，消息里提到套餐，比如 "Upgrade to GitHub Pro or make this repository public"；在有的地方回答 404 "Branch not protected" 或 200。

**已经有规则集的仓库。** troy-init 把自己的规则集加在它们旁边，从不修改或删除任何一个。GitHub 同时执行所有生效的规则集，所以已有的更严格的规则仍然有效：比如一条要求批准的规则，会让 troy-mode 的合并等这个批准。没有生效的规则集，比如执行方式为 `disabled` 的，什么也不改变，保持原样。2026-11-28，`ZJUCao/troy-voice` 就有这样一个规则集 "protect"，建于 2026-11-06。技能的问题会列出仓库已有的规则集。

**引擎负责的部分。** `troy_init.py branch-rule --rules <file> --rulesets <file> --json` 读取 GitHub 的两个回答：`gh api repos/<owner>/<project>/rules/branches/main`，即所有生效规则集在 `main` 上正在生效的规则；以及 `gh api repos/<owner>/<project>/rulesets`，即仓库的每个规则集及其名字和执行方式。它报告：

- `r21`：正在生效的规则里有 `deletion`、`non_fast_forward` 和 `pull_request` 时为 true，不管它们来自哪个规则集，所以 Troy 手动加的规则也算；
- `existing`：仓库的规则集，各带 ID、名字和执行方式；
- `add`：`r21` 为 false 时，R21 的规则集，带名字和请求体的绝对路径；
- `held`：`r21` 为 false，而仓库里已经有一个和 R21 同名的规则集时，比如 Troy 关掉的那个，R21 的规则集放在这里，而不放进 `add`。troy-init 从不再加一个同名的规则集，也从不打开已有的那个；报告把它指给 Troy。

不给 `--rules` 时，`r21` 为 false；不给 `--rulesets` 时，`existing` 为空。文件不是一个 JSON 列表时，退出码为 2。引擎不调用任何东西；`gh` 由技能运行。

**技能负责的部分。** 在初始化和升级时，在 PR 流程第 1 步里（第 7 节），在这一步的分支和 PR 之前：

1. **探测。** `gh api repos/<owner>/<project>/branches/main/protection`。消息提到套餐的 403 结束这一部分，不问任何问题：技能说明 GitHub 的套餐在这个私有仓库上没有分支规则，所以 R21 只靠本地 hook 保证。回答不是 404 或 200 时，它报告 GitHub 的消息，不加规则继续。
2. **读取。** 把引擎那部分说的两个回答存到 git 目录里的文件，再运行 `branch-rule --rules <file> --rulesets <file> --json`。`add` 为空时，规则已经生效：报告这一点，指出 `held` 里的规则集（如果有），跳过后面几步。读取失败时，报告 GitHub 的消息，不加规则继续。
3. **询问。** Troy 的同意来自第 3.1 节的那一条消息。新仓库由 D52 的问题一并覆盖（D292）。已有的仓库，技能问要不要给 `<owner>/<project>` 的 `main` 加上 R21 的规则集，说明它做什么，并列出 `existing`，它们保持原样。回答不要时，不加规则继续。
4. **添加。** 对 `add` 里的那一项：`gh api -X POST repos/<owner>/<project>/rulesets --input <body>`，请求体用绝对路径指明，这样 F05 的 hook 能在调用前读到它（F05 D200）。提到套餐的 403 结束这一部分，说明和第 1 项相同。遇到其他错误时，它报告 GitHub 的消息，不加规则继续。
5. **核对。** 它按第 2 项再读一次规则，只有 `add` 变成空时才报告规则已生效。GitHub 接受了某个规则集但它没有生效时，它报告这一点并附上规则集的链接，交给 Troy 处理。

当代理的权限拒绝某个调用时，比如自动模式拒绝了 POST，技能就停下来问 Troy。它从不绕过拒绝：不换别的 API 调用，不去设置页面，不用 `--admin` 合并。troy-init 从不修改或删除规则集，从不加可绕过者，也从不使用经典分支保护。语言步骤不看规则。

**F05 的 hook。** 在主会话里，一个会改动 GitHub 的 `gh api` 调用，只要它发送的文本通过 R19 的检查，hook 就放行（F05 D200）。用 `--input <file>` 时，这段文本就是那个文件，这里是一个不含署名的 JSON 请求体。初始化时项目还没有 `.troy-mode/`，所以 hook 什么也不做。子代理只能运行只读的 `gh` 命令，没有哪个角色执行这一步。

## 5. 语言步骤

### 5.1 开始之前

以下条件都满足，语言步骤才会进行：

- 初始化已完成，并且还没有安装语言包；
- `origin/main` 上的 `docs/architecture.md` 的 `version` 是 1.0 或更高，表示 Troy 已经批准（F01 设计第 4 节）；
- 这种语言有语言包（F03）：`python` 或 `cpp`；
- 当前分支不是 `main`，并且这一步要写的文件都不存在，除非用 `--replace` 点名。

### 5.2 Python

| 路径 | 动作 |
| --- | --- |
| `.troy-mode/config.toml` | `[lang]` 表填入语言包的值：`name`、`source_roots`、`environment` 和 `series`。`[tests] legacy` 列出已有的测试（第 5.5 节）。 |
| `environment.yml` | 语言包的文件，填入环境名。 |
| `pyproject.toml` | 文件存在时，追加语言包的表。不存在时，用新增的语言包文件 `pyproject-project.toml` 创建（`[build-system]` 用 hatchling；`[project]` 写名字、版本 0.1.0、Python 3.13 或更新、没有依赖；wheel 的包是 `src/<package>`），后面再接语言包的表。 |
| `requirements-dev.lock` | 编译生成（第 5.4 节）。 |
| `.github/workflows/troy-mode.yml` | 在 `jobs:` 下加入语言包的 `workflow-job.yml`。 |
| `.gitignore` | `reports/`、`.coverage`、`__pycache__/`，以及 mypy、pytest 和 ruff 的缓存。 |

如果 `pyproject.toml` 里已经有语言包要加的某张表，比如 `[tool.ruff]`，这一步就停下，并列出这些表。

### 5.3 C/C++

| 路径 | 动作 |
| --- | --- |
| `.troy-mode/config.toml` | `[lang]` 表填入 `name`、`include_dirs`、`environment` 和 `series`。`[tests] legacy` 列出已有的测试。 |
| `environment.yml`、`requirements-tools.in` | 语言包的文件，填入环境名。 |
| `requirements-tools.lock` | 编译生成（第 5.4 节）。 |
| `CMakePresets.json`、`cmake/troy.cmake`、`.clang-format`、`.clang-tidy`、`include/troy/not_implemented.h` | 复制。 |
| `.troy-mode/lang/cpp/Doxyfile` | 复制。 |
| `CMakeLists.txt` | 文件存在时，检查它是否包含 `cmake/troy.cmake`，没有就停下，并给出要加的那一行。不存在时，用新增的语言包文件创建（`cmake_minimum_required(VERSION 3.28)`、`project(<name> C CXX)` 和 `include(cmake/troy.cmake)`）。 |
| `.github/workflows/troy-mode.yml` | 在 `jobs:` 下加入语言包的任务。 |
| `.gitignore` | `build/` 和 `reports/`。 |

### 5.4 环境和锁文件（D51）

在 Troy 的电脑上，语言步骤按语言包 README 的安装步骤进行：

1. 环境不存在时，用 `mamba env create -f environment.yml` 创建这个系列的环境。mamba 来自 `--mamba`、PATH 或 `$MAMBA_EXE`。
2. 用这个环境里的 uv，根据系列中每个成员的清单文件编译锁文件，写进本项目。uv 运行时设置 `UV_LINK_MODE=copy`，缓存文件夹见下一段。
3. 把锁文件安装进环境。

**uv 的缓存文件夹（D213）。** 这一步可能写不了 uv 默认的缓存：试点中，在桌面应用的沙箱里，第一次编译锁文件失败，原因是 uv 写不了它（tstack issue #48）。所以 `UV_CACHE_DIR` 没有设置或为空时，本节的每条 mamba 和 uv 命令运行时都把 `UV_CACHE_DIR` 设为系统临时文件夹里的 `troy-mode-uv-cache` 文件夹，系统临时文件夹即 Python 的 `tempfile.gettempdir()` 返回的文件夹。文件夹不存在时由 uv 创建。已经设置的值原样传下去。F07 的 `troy_flow.py series`（F07 设计 8.7，D66）用本节的函数规划系列锁文件，也遵循同一规则：引擎的环境里 `UV_CACHE_DIR` 没有设置或为空时，它的两条命令都以 `UV_LINK_MODE=copy UV_CACHE_DIR=<文件夹>` 开头，文件夹按 shell 的规则加引号；有的时候，只以 `UV_LINK_MODE=copy` 开头，由运行命令的 shell 把这个值传下去。引擎的其他 uv 命令也遵循同一规则（D289）：`brief` 给出的检查里第一个 mock 的 `uv pip install -e . --no-deps`（F07 设计 6.1），团队的任务简报里也一样，那里安装的是主检出；还有真实运行为 `program-not-found` 问题给出的修复，也是这条安装命令（F12 设计 5.4）。每条都以 `series` 的变量开头，放在 `mamba run` 之前。这个问题的消息把文件夹显示为 `<uv cache>`，就像真实运行把环境的文件夹显示为 `<environment>`，这样就没有本地路径进入 PR；它的 `fix` 则带着含文件夹本身的命令。

需要代码的步骤，即 `uv pip install -e . --no-deps` 和 `cmake --preset coverage`，要等到第一个 mock：F07 把它们写进 DV1 的任务简报。系列中的其他成员在各自的 PR 里拿到新的锁文件（F03 设计 8.1）。`--no-env` 跳过本节。

### 5.5 已经有代码的项目（Q6）

如果项目里已经有匹配语言包测试模式的测试文件，语言步骤就把它们列进 `[tests] legacy`，这样 R10 不会因为它们的名字失败，并报告这个列表。它们仍然必须通过。按 Q6 的规定，旧代码在被修改之前，不按 R04 到 R07 或 R11 检查。

### 5.6 代码出现之前语言包的 CI 任务（D50）

语言包的任务在每个 PR 上都会运行，包括第一个功能的设计 PR 和测试计划 PR。在第一个 mock PR 之前，项目里没有代码，任务里的工具面对空项目会失败：Python 包的 `mypy` 读不到不存在的 `src`，`coverage xml` 没有数据可报告。

所以两个语言包的 `workflow-job.yml` 都加一个第一步，用 `git ls-files` 查看 PR 的 head 在语言包的源码目录下有没有源文件（Python 是 `src/`，C/C++ 是 `src/` 或除 `include/troy/` 外的 `include/`）。没有的话，后面的步骤全部跳过，任务通过，并在摘要里写"No code yet"。这样文档 PR 也省掉了搭建环境的时间。从第一个 mock 起，任务总是完整运行。

## 6. 升级（D54）

升级在一个 `[rules] Upgrade troy-mode to <version>` PR 里，把项目里 troy-mode 的文件更新到插件的当前版本。

| 对象 | 怎样处理 |
| --- | --- |
| troy-init 拥有的文件 | 哈希仍和安装记录一致时，替换成插件的版本。之后被人改过的文件算冲突：升级停下并列出它，除非用 `--replace` 点名。插件新增的文件会被创建。插件删掉的文件，没改过就删除。 |
| 工作流 | 用 F02 的工作流和语言包的任务重新生成，遵守同样的哈希规则。 |
| `docs/rules.md` 及其镜像 | 每一行 R 规则都换成模板里的。已有的行保留"起始日期"，新增的行用今天的日期。P 规则保持不变。两者的 `version` 都升一个小版本，`updated` 也更新。 |
| `config.toml`、追加到 `pyproject.toml` 的表、`environment.yml`、`CMakeLists.txt` | 从不修改。报告列出它们和插件当前语言包文件的差别，由 Troy 在某个规则 PR 里采纳。 |
| `.troy-mode/install.toml` | 重写。 |
| GitHub 上 R21 的分支规则 | 不是文件。GitHub 列出 `main` 上缺少第 4.7 节的某个规则集时，技能在升级的那一条消息里问 Troy，并在升级的 PR 之前加上它（D291）。recipe-menu 手动加的规则集算作 R21 的，所以它什么也不加。 |

升级改动的每个路径都属于 `config` 或 `dependencies` 类别，所以它的 PR 是一个有效的 `[rules]` PR。

## 7. PR 流程（D53）

技能在引擎前后执行这些步骤。F07 自己运行引擎时，也执行同样的步骤。

1. **仓库和分支规则。** 如果文件夹不是 git 仓库，就 `git init -b main`。如果没有 `origin`，技能问 Troy 一次：要不要在 Troy 的账号下创建一个以项目命名的私有 GitHub 仓库，并在 Troy 的套餐允许时加上 R21 的分支规则（D292）。回答是的话：`gh repo create <owner>/<name> --private --add-readme`，然后 `git remote add origin` 和 `git fetch origin`。`main` 上的第一个 commit 由 GitHub 生成，所以没有人在本地 `main` 上提交（R21，D52）。然后在初始化和升级时，处理 R21 的分支规则（第 4.7 节，D291）。
2. **分支。** `git switch -c troy-mode/init origin/main`，或者 `troy-mode/lang-<name>`、`troy-mode/upgrade-<version>`。语言步骤和升级在试运行之前就创建它（第 3.1 节）。
3. **引擎。** 运行这一步。
4. **暂存。** 只 `git add` 引擎报告列出的路径，git hook 加 `--chmod=+x`。从不用 `git add -A`。
5. **提交。** 一个 commit，标题行等于 PR 标题（R01）：`[rules] Set up troy-mode`、`[rules] Add the Python pack` 或 `[rules] Add the C/C++ pack`、`[rules] Upgrade troy-mode to <version>`。F05 的 `commit-msg` hook 会检查它（R19）。
6. **检查。** 用标题和描述运行 `troy-check pr`。有任何 `fail` 就停下。
7. **PR。** `git push -u origin <branch>`，然后 `gh pr create --base main`，描述按 PR 模板写：Why、What、Checks，Soft-limit reason 写 "None"。
8. **合并。** 用 `gh pr checks <number> --watch` 等一次检查。全部通过就先运行 `git switch --detach`，再用 `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>` 合并，因为 R18 允许 Claude 合并除前几个功能的 PR 1 和 PR 2 之外的所有 PR。先分离 HEAD，`gh` 就不会在删除分支之前去检出 `main`。有失败就停下并报告。然后运行 `git fetch origin`，并把这一步记进进度文件。

```text
Troy:   /troy-pstack:troy-init
Claude: 这个文件夹还没有 GitHub 仓库。要创建私有仓库 ZJUCao/habit-tracker，并在你的 GitHub
  套餐允许时给 main 加上 R21 的分支规则（只能通过 PR 改动、禁止强制推送和删除）吗？
Troy:   要。
Claude: 初始化完成。
  仓库：已创建 ZJUCao/habit-tracker（私有）。main 上的 R21 分支规则已生效。
  PR #1 "[rules] Set up troy-mode"：troy-check 通过（R01、R02、R12、R19、R20），已合并。
  git hook 已打开。
  下一步：需求（产品经理）。
```

## 8. 对已有功能的改动

实现 F06 时，还要改动：

- **F03 的语言包。** 两个 `workflow-job.yml` 都加上第 5.6 节的那一步，对应的示例工作流也跟着改，这样 `test_python_pack.py` 和 `test_cpp_pack.py` 仍然能比较它们。C/C++ 的配置片段把 `include/troy/not_implemented.h` 加进 `config`（D49）。每个语言包增加新项目的构建文件，以及 README 里对应的行。F03 的设计加一行修改记录。
- **`build_sample.py`。** 它改用 troy-init 写文件的那些函数来搭建每个示例，不检查第 4.1 节和第 5.1 节的前提条件，也不创建环境，代替它自己的 `install_pack`，这样示例的搭建方式和 troy-init 搭建项目完全相同。它还增加一个示例状态：只做了初始化和语言步骤、还没有代码，语言包的任务在上面必须跳过代码步骤并通过。

- **troy-check 的 R12。** R12 不把 `.troy-mode/` 下的文件当文档，和 R20 不扫描这里一样（F02 设计 6.7）。初始化把模板原样复制到这里，它们的文档头带着标记，`troy-doc` 也和项目自己的文档相同，不这样做的话，每个初始化 PR 和之后每个改文档的 PR 都会让 R12 失败。构建第一部分时发现，Troy 于 2026-11-07 批准。F02 的设计在它的 1.2 版里记下了这一点。

F01、F04 和 F05 不变。

R21 的分支规则（1.7 版）会改动：

- **规则表模板和另外两个模板（F01，D294）。** 在 `troy-mode/templates/rules.md` 及其镜像里，R21 的"执行方式"改用需求文档 1.71 的那一格。R17 和 R18 采用 F18 在需求文档里给它们的含义：第 3 轮时由架构师裁决，以及抽查。R24 是 F20 加进需求文档的，在这里补上它的一行，注释和修改记录写 R01 到 R24。`feature-design.md` 和 `test-plan.md` 及其镜像的指导注释改为：第 3 轮之后由架构师裁决（R17）。之后升级会把新的行带进每个项目（第 6 节）。
- **角色考试（F16，D294）。** `troy_exam.py affected` 只在两种情况下把插件的某个模板算作一个用例的输入：用例的项目在 `.troy-mode/templates/` 下没有同名文件，或者用例的任务简报写出了这个模板的路径。角色从项目里的副本填写模板（F04 共用规则第 7 条），而这份副本由用例的起始 commit 固定。指令集和它的哈希仍然包含所有模板（F16 设计 9.1），所以改模板的 PR 仍然要带考试那一节。这一项最先合入，单独一个 PR，带它自己的测试，并由 F16 的设计记下。
- **入口技能（F07）。** 它的项目初始化把 R21 的分支规则列进 troy-init 的问题；它的升级在规则缺少时，通过 troy-init 的 PR 流程加上规则。两处都不是角色章节，所以没有考试用例受影响。
- **指南（F10）。** `02-start.md` 用新的问题和报告取代必需检查那一步。`06-rules.md` 和 `README.md` 写 R01 到 R24，`08-reference.md` 补上 R24 的一行。

## 9. F06 怎样对应需求

| 需求 | F06 在哪里覆盖 |
| --- | --- |
| F06 一行：标记文件夹、文档骨架、规则表、进度文件 | 第 4.2 节和第 4.4 节。文档骨架就是 `.troy-mode/templates/` 里的模板。 |
| F06 一行：架构批准后，语言包和 CI 工作流 | 第 5 节。troy-check 的任务更早，在初始化时就加入（第 4.2 节，D48），所以需求 PR 和架构 PR 也会被检查 |
| 5.1 第 2 步和第 4 步 | 第 4 节和第 5 节 |
| F02 D8：复制检查、记录版本、在 `[rules]` PR 里重新运行 troy-init 来升级 | 第 4.2、4.6 和 6 节 |
| F02 D14：仓库允许时把检查设为必需 | 第 4.5 节。由 D293 取消：troy-init 不再把检查设为必需，troy-mode 的合并步骤仍然等检查通过（R18）。 |
| troy-init 自己的 PR 满足 R01、R02、R12、R19、R20 | 第 4.2、4.4 和 7 节 |
| R18：前几个功能的 PR 1 和 PR 2 以外，都由 Claude 合并 | 第 7 节第 8 步 |
| R21：不在 `main` 上提交 | 第 7 节第 1 步和第 2 步 |
| R21 的执行方式（需求文档 1.71）：troy-init 在 GitHub 允许时给 `main` 加的分支规则 | 第 4.7 节（D291 到 D293） |
| Q6：旧代码在被修改时再修 | 第 5.5 节 |
| Q8：进度文件只在本地 | 第 4.2 节 |
| 第 8 节，Python 环境 | 第 5.4 节 |
| 第 8 节，新技能只在 Troy 输入时运行 | 第 2 节 |

## 10. F05 和 F07 怎样使用 F06

**F05。** 初始化把 git hook 随 troy-check 一起复制进来并打开它们。在其他克隆里，由 F05 的 `SessionStart` hook 打开。因为 F05 的 hook 放行插件文件的读取（F05 D45），初始化不写权限规则。如果 Troy 选了 F05 D45 的 B，初始化就把 `Read(<plugin folder>/**)` 写进 `.claude/settings.local.json`，并让 git 忽略这个文件。

**F07。**

- 它不能调用标了 `disable-model-invocation` 的技能，所以直接运行引擎，再走第 7 节的 PR 流程。项目没有 `.troy-mode/` 时它运行初始化，架构的 PR 合入后它运行语言步骤。
- 它在初始化的 PR 合入之后才开需求 PR，所以 troy-check 的任务也会检查需求文档。
- 它把需要代码的安装步骤（第 5.4 节）写进 DV1 的任务简报。
- 项目初始化之后，角色从 `.troy-mode/templates/` 填写模板，F04 共用规则第 7 条里退回插件模板的做法就用不到了。

## 11. F06 怎样检查

### 11.1 测试

测试使用 `unittest` 和标准库。由一个单独的代理在引擎写出来之前，根据本设计写测试。每个测试建一个临时 git 仓库，配一个本地的裸仓库作 `origin`，它用 `git clone --bare` 从一个已有 commit 的仓库生成，所以没有测试推送 `main`。测试放在 `troy-mode/init/tests/`，凡是修改 `troy-mode/init/`、`troy-mode/checks/`、`troy-mode/templates/`、`troy-mode/lang/` 或 `skills/troy-init/` 的 PR，`troy-checks-tests.yml` 都在 Linux 和 Windows 上运行它们。

| 组 | 用例包括 |
| --- | --- |
| 初始化 | 第 4.2 节的每个文件，内容符合第 4 节。规则表里不留任何标记和 template 注释。配置里有邮箱和所有语言包的模式。安装记录的哈希和文件一致。`.gitignore` 被新建或追加。只有 `git-hooks/` 存在时才设置 `core.hooksPath`。试运行什么也不改。 |
| 前提条件 | 第 4.1 节和第 5.1 节的每个条件都会让这一步以退出码 1 停下，什么也不改：没有 `origin/main`、在 `main` 上、已经初始化过、文件已存在、`origin/main` 上的架构低于 1.0、第二个语言包。`--replace` 放行一个点名的文件。 |
| 自己的 PR 能通过 | 初始化的文件提交到一个分支上，用初始化的标题运行 `troy-check pr`，R01、R02、R12、R19 和 R20 都通过。语言步骤的文件提交在上面，以初始化的 commit 为合并基点，R02 通过。升级的也一样。 |
| 语言步骤 | Python 和 C/C++ 的文件。表追加到已有的 `pyproject.toml`，或者新建一个。已有的表会让这一步停下。缺少 include 的 `CMakeLists.txt` 也会让它停下。`[lang]` 表被填写，已经填过的会让这一步停下。已有的测试被列为 legacy。工作流在 `jobs:` 下多了语言包的任务。 |
| 环境 | PATH 上放一个记录参数的假 `mamba`：只在环境不存在时创建，锁文件根据每个成员的清单文件编译，`--env-prefix` 和 `--no-env` 都有效。uv 的缓存文件夹（D213）：`UV_CACHE_DIR` 未设置或为空时，每次调用都得到临时文件夹里的 `troy-mode-uv-cache`，已经设置的值原样不变；`series` 只在这个变量未设置或为空时把文件夹写进两条命令。D289：Python 项目 DV1 任务简报里第一个 mock 的安装（包括团队的任务简报）和真实运行的 `program-not-found` 修复都以同样的变量开头，问题的消息用 `<uv cache>` 代替文件夹。没有测试使用网络。 |
| 升级 | 没改过的自有文件被替换，改过的会让这一步停下。新增的模板被创建。R 规则行被替换，P 规则行和起始日期保留，中英文的版本都升高。配置从不修改。 |
| 技能 | `SKILL.md` 的 front matter 有 `name: troy-init` 和 `disable-model-invocation: true`。正文写出了三个步骤和 PR 流程的各步。D291 到 D293：它写出分支保护的探测和提到套餐的 403、带两个文件的 `branch-rule`、带 `--input` 的 POST、POST 之后的第二次读取、带规则的私有仓库问题、已有规则集保持原样，以及被拒绝的调用交给 Troy；它不再把 `troy-mode checks` 设为必需。 |
| 分支规则 | 不给 `--rules` 时，`branch-rule` 把 R21 的规则集放进 `add`，带请求体的绝对路径。列表里有 `deletion`、`non_fast_forward` 和 `pull_request` 时，不管来自一个还是两个规则集，它都不进 `add`；缺任何一个，就要加。`existing` 列出 `--rulesets` 里的每个规则集，带 ID、名字和执行方式，`disabled` 的也包括在内。列出的某个规则集已经用了 R21 的名字时，不管它是否生效，R21 的规则集都进 `held` 而不进 `add`。文件不是 JSON 列表时退出码为 2。请求体的内容恰好是第 4.7 节给出的：名字、目标 `branch`、执行方式 `active`、空的可绕过者列表、`~DEFAULT_BRANCH`，以及三条规则和它们的参数，没有 `required_status_checks` 规则。没有测试使用网络。 |
| 模板（D294） | 规则表模板的每一行 R 规则，都和需求文档第 6 节同一语言里某一行 R 规则的编号、类型和执行方式相同；需求文档的每一行 R 规则在模板里也都有对应的行。没有哪个模板注释还说第 3 轮会升级上报。 |
| 考试（D294，F16 的测试） | `affected`：每个用例的项目都有的模板被改动时，不影响任何用例；某个用例的项目没有的模板，影响这个用例；任务简报写出了路径的模板，影响这个用例。 |

### 11.2 埋 bug

代码通过后，在临时副本里一次埋一个 bug，每个都必须让某个测试失败。包括：覆盖了已有文件、规则表里留了标记、镜像版本不一致、配置里缺了某个语言包的模式、`[lang]` 表没填、已有测试没列出、没检查架构是否批准、git hook 没有可执行位、升级时丢了 P 规则行、升级时替换了被改过的自有文件，以及没有加入语言包的任务。D213 的改动再加上：覆盖了已经设置的值、`series` 的安装命令里缺了文件夹、文件夹不在临时文件夹里。D289 再加上：第一个 mock 的安装缺了这些变量、把它们放在 `mamba run` 之后、把它们给了别的检查或 C/C++ 的任务简报、在那里覆盖了已经设置的值、团队的任务简报丢了它们，以及真实运行的消息里显示了文件夹或它的修复里缺了文件夹。R21 的分支规则再加上：请求体里有可绕过者、请求体里有必需的状态检查、缺 `deletion` 时 `r21` 仍为 true、`add` 里是相对路径、`held` 的规则集被放进 `add`，以及 `disabled` 的规则集没列进 `existing`。考试的改动再加上：项目已有的模板仍被算进去、项目没有的模板没算进去，以及任务简报写出的模板没算进去。数量写在 PR 描述里。

### 11.3 CI 里的示例项目

因为 `build_sample.py` 使用 troy-init 的函数（第 8 节），troy-pstack 的示例工作流在 Linux 上证明 troy-init 的产出能通过语言包的 CI 任务，有代码和没代码的项目都包括在内。

### 11.4 试运行（D56）

在语言步骤的 PR 开出之前，troy-init 在 Troy 电脑上的嵌套 `claude -p` 会话里运行，troy-pstack 通过 `--plugin-dir` 从 PR 分支加载：

1. 在空文件夹里**初始化**。troy-init 创建私有仓库 `ZJUCao/troy-mode-trial`（试运行的提示词预先回答"是"），开出初始化的 PR，等待检查，然后合并。
2. **架构。** 试运行用同样的步骤合并一个预先准备好的 `[docs]` PR，里面是一份 1.0 版的小 `docs/architecture.md`。
3. Python 的**语言步骤**，用 `--env-prefix` 指向一个临时文件夹。它的 PR 在跳过语言包代码步骤的情况下通过，并合并。
4. 没有东西要改时，**升级**会说明这一点，不开 PR。
5. **新克隆。** F05 合入后，新克隆的仓库由 F05 的 `SessionStart` hook 设置 `core.hooksPath`。

这个仓库是私有的，保留给以后的试运行（F07、F11）。要不要删除由 Troy 决定。试运行会用掉这个私有仓库几分钟的免费 Actions 时间。

**R21 的分支规则（D295）。** `ZJUCao/troy-mode-trial` 现在是公开的，并且特意没有分支规则。在分支规则的 PR 合入之前，用 PR 分支上的 tstack 跑两个嵌套的 `claude -p` 试运行：

1. 在 `ZJUCao/troy-mode-trial` 的一个克隆上**升级**。troy-init 发现缺少 R21 的规则集，试运行预先给的回答是同意，它就加上它。升级的 PR 带着模板的新行，然后在它之下用 rebase 合并。之后规则集留在这个仓库上。
2. 在新建公开仓库 `ZJUCao/troy-init-trial` 的一个新克隆里**初始化**。Troy 随本设计批准后，由构建的会话用 `gh repo create --public --add-readme` 建这个仓库。troy-init 走"仓库已经存在"的路径：探测回答 404，试运行预先给的回答是同意，规则在 PR 1 之前就生效，PR 1 在它之下合并。之后保留还是删除这个仓库由 Troy 决定。

每次试运行都拿 GitHub 列出的规则集和第 4.7 节对照。没有试运行用私有仓库，因为 2026-11-28 时 GitHub Actions 在 Troy 的私有仓库上不运行，那里不会有检查结果。新仓库经过 D52 问题的路径，以及没有分支规则的套餐给出的 403，只由测试检查。

### 11.5 状态

| 时间点 | 需求文档 7.2 中 F06 的状态 |
| --- | --- |
| 第 1 部分合入 | 已编写，2 部分中的第 1 部分：初始化和升级。它的单元测试在 Troy 的电脑上通过。 |
| 第 2 部分在试运行通过后合入 | 在示例项目上跑通：troy-init 搭建了一个临时 GitHub 项目，它的初始化 PR 和语言 PR 都通过了 CI 并合入。还没有在真实项目上用过。 |
| 试点（F11）用 troy-init 开始 | 在真实项目上用过 |
| R21 分支规则的 PR 在第 11.4 节的两个试运行之后合入 | F06 一行加上：troy-init 在初始化和升级时加上 R21 的分支规则，在示例项目上跑通（那两个试运行），还没有在真实项目上用过。 |

F06 分两个 PR 合入（D55），每个只有一个 commit，测试都先写：

1. **初始化和升级。** 技能、引擎的初始化和升级，以及它们的测试。还包括第 8 节对 R12 的改动，以及 C/C++ 配置片段里 `include/troy/not_implemented.h` 那一行（D49），因为初始化要把这个模式写进配置。
2. **语言步骤。** 引擎的语言步骤、F03 语言包的改动、`build_sample.py`、它们的测试，以及试运行。

每次状态更新都单独开一个 PR。

R21 的分支规则分两个 PR 合入，每个只有一个 commit，测试都先写：

1. **考试的改动**（第 8 节，D294）：`affected` 和它的测试，以及 F16 的设计。改动考试框架会让每个用例的锚点重新证明一次，约 $12 到 $40。
2. **分支规则：** `branch-rule`、请求体、技能、入口技能的那几行、模板、指南，以及插件的下一个小版本，在第 11.4 节的两个试运行之后合入。考试的改动合入之后，它的模板不影响任何用例。

然后是状态 PR，只改 F06 的状态，作为需求文档 1.72 或下一个空闲版本。需求文档 1.71（PR #137）已经有了 R21 新的"执行方式"一格（规则表模板会采用它），以及 F06 一行里关于这条规则的那句话。

## 12. 不在 F06 里的

- 写需求文档和架构文档、开它们的 PR，以及在各流程中运行 troy-init（F04 的角色和 F07）。
- 为系列中的其他成员创建环境、更新它们的锁文件（F07，F03 设计 8.1）。
- 项目自己的规则（F09）。升级只带来 troy-mode 的 R 规则。
- TypeScript/JavaScript 语言包（以后，Q1）。
- 插件文件的权限规则（F05 D45）。
- 删除试运行用的仓库。
- 修改或删除规则集、可绕过者、经典分支保护，以及组织的规则集（第 4.7 节）。
- 在 GitHub 上把 `troy-mode checks` 设为必需（D293）。

## 13. 需要 Troy 决定的事项

F05 到 D46 为止，所以 F06 从 D47 开始。

| 编号 | 问题 | 选项 | 推荐并已批准 |
| --- | --- | --- | --- |
| D47 | troy-init 怎样实现？ | A：一个 Troy 输入的技能，加一个只用标准库的 Python 引擎，分三步 `setup`、`lang` 和 `upgrade`，支持 `--dry-run` 和 `--json`（第 3 节）。引擎只改文件。由技能和 F07 提交并开 PR。B：技能的说明让 Claude 手工复制和修改文件。 | A。复制、填写和计算哈希都是要求精确的工作，可以用测试检查。F07 虽然不能调用标了 `disable-model-invocation` 的技能，但可以运行引擎。 |
| D48 | 初始化写哪些文件？已经存在的文件怎么办？F06 一行把 CI 工作流放在架构之后。 | A：第 4.2 节的文件，其中包括 troy-check 的 CI 任务。troy-init 从不覆盖或删除不是它写的文件。它会停下、列出这些文件，由技能逐个问 Troy（`--replace`）。B：同样的文件但不含 CI 任务，CI 任务到语言步骤才加入。C：覆盖已有文件，让 PR 的 diff 显示改了什么。 | A。troy-check 的任务从初始化就在，需求 PR 和架构 PR 也会检查 R12 和 R20。采用 troy-mode 的已有项目（比如 troy-voice）保留自己的文件，除非 Troy 另有决定。这会改动需求文档里的 F06 一行和 5.1。 |
| D49 | 在语言步骤的 PR 被检查之前，语言包的文件怎样拿到路径类别？troy-check 从合并基点读类别，不这样做的话，PR 里的 `pyproject.toml` 属于 `source`，而 `[rules]` PR 不能改源码（R02）。 | A：初始化的配置里已经写好所有语言包的路径模式（第 4.3 节），C/C++ 片段把 `include/troy/not_implemented.h` 加进 `config`。B：语言步骤分两个 PR，先改配置，再加文件。C：让 troy-check 的内置模式认识各语言包的文件名。 | A。每一步一个 PR，troy-check"PR 不能放宽评判它自己的规则"这一条也保持不变。代价是配置里多几个项目并没有的文件的模式。C 会把语言相关的文件名放进与语言无关的检查里。 |
| D50 | 语言包的 CI 任务在每个 PR 上运行，但项目还没有代码时会失败，而从语言步骤到第一个 mock 正是这种情况。怎么办？ | A：两个语言包的任务先检查 PR 里有没有源文件，没有就跳过代码步骤（第 5.6 节）。这会改动 F03 的语言包。B：troy-init 在一个 `[refactor]` PR 里加一个空的包。C：不管，于是第一个 mock 之前的每个 PR 都失败。 | A。不需要占位代码，文档 PR 还省掉了搭建环境的时间。B 仍然会失败，因为覆盖率报告没有数据；C 会挡住设计 PR 和测试计划 PR。 |
| D51 | 谁来创建构建文件、环境和锁文件？ | A：缺少 `pyproject.toml` 或 `CMakeLists.txt` 时由语言步骤创建；Troy 电脑上没有这个系列的环境时也由它创建；它还编译锁文件并安装（第 5.4 节）。B：troy-init 只写文件，把命令打印出来让 Troy 执行。 | A。CI 在语言 PR 里就需要锁文件，没有环境角色也跑不了语言包的检查。B 给 Troy 的是不需要决策的活。 |
| D52 | 文件夹没有 GitHub 仓库怎么办？R21 禁止在本地 `main` 上提交，而 PR 需要一个目标 `main`。 | A：技能问 Troy 一次，然后用 `gh repo create --private --add-readme` 在 Troy 的账号下创建私有仓库。`main` 上的第一个 commit 由 GitHub 生成（第 7 节第 1 步）。B：troy-init 停下，说明 Troy 要创建什么。 | A。Troy 只需回答一次"是"，R21 仍然成立。创建仓库是唯一会触及项目之外的一步，所以它总是先问。这会给需求文档里的 F06 一行增加内容。 |
| D53 | troy-init 的 PR 由谁合并？ | A：troy-init 等一次检查，通过就合并，因为 R18 允许 Claude 合并除前几个功能的 PR 1 和 PR 2 之外的所有 PR（第 7 节）。B：troy-init 停在开着的 PR，由 Troy 或 F07 合并。 | A。初始化的 PR 合入之前项目没法用，而这个 PR 里没有需要 Troy 决定的事。 |
| D54 | 升级改多少？F02 D8 说在 `[rules]` PR 里重新运行 troy-init 就能升级项目。 | A：替换 troy-mode 自己的、没人改过的文件，遇到改过的就停下。把规则表的 R 规则行更新到最新，保留 P 规则行。配置和构建文件只报告差别（第 6 节）。B：替换 troy-init 写过的所有文件，包括被改过的。C：把升级留给规则变更流程（F09）。 | A。troy-mode 自己拥有的文件机械地升级，而且从不悄悄推翻项目自己的选择。 |
| D55 | F06 怎样合入？Q10 规定每个功能一个 PR，F03 是例外。 | A：两个 PR（第 11.5 节）：先是初始化和升级，再是语言步骤，连同 F03 语言包的改动和 `build_sample.py`。B：一个 PR。 | A。第二个 PR 会改 F03 的 CI 任务和示例工作流，和第一个分开更容易审查。这会把 F06 加进 Q10 的例外。 |
| D56 | F06 怎样试运行？状态什么时候改？ | A：测试和埋 bug、CI 里的示例项目，再在一个私有的临时仓库 `ZJUCao/troy-mode-trial` 上试运行，这个仓库由 troy-init 创建，以后的试运行接着用（第 11.4 节）。第 2 部分之后的状态："在示例项目上跑通"。B：同上，但试运行用本地裸仓库作 `origin`，所以 PR 和 CI 并没有真正运行。状态为"已编写"，直到 F07 用上 troy-init。 | A。只有真实的 GitHub 仓库才能证明第一个 PR 会运行它自己带来的工作流、检查能通过、合并能完成。代价是在 Troy 的账号下建一个私有仓库，用掉几分钟 Actions 时间。 |
| D213 | `UV_CACHE_DIR` 没有设置时，uv 用哪个缓存文件夹？试点中，在桌面应用的沙箱里，第一次编译锁文件失败，原因是 uv 写不了它默认的缓存；troy-mode 把缓存放到会话的临时文件夹里再运行这一步，就通过了。来自 tstack issue #48。它的编号取自为这批试点修复保留的 D213 到 D218。 | A：系统临时文件夹里的 `troy-mode-uv-cache` 文件夹，系统临时文件夹按 Python 的 `tempfile.gettempdir()` 找到。B：项目 git 目录下的一个文件夹，例如 `<git 目录>/troy-mode/uv-cache`。两者都只在 `UV_CACHE_DIR` 没有设置时生效，用于语言步骤和 `series`（第 5.4 节）。C，Troy 没有采用：只在指南里写一条说明，让人设置 `UV_CACHE_DIR`。 | A。`gettempdir()` 取 `TMPDIR`、`TEMP`、`TMP` 和平台常用文件夹中第一个能在里面创建文件的，所以这一步开始时文件夹可写，沙箱把这些变量指向它自己的文件夹时也会跟着走。uv 靠重命名来移动文件，而 Windows 不能把文件重命名到另一个驱动器上：试点的错误正是这个（"cannot move the file to a different disk drive"），把缓存放到临时文件夹就解决了。git 目录下的文件夹在项目所在的驱动器上，在 Troy 的电脑上是 D:，而临时文件夹在 C:。它还会把几百 MB 的缓存放进项目里；临时文件夹被清空，代价只是重新下载。Troy 于 2026-11-18 批准在变量没有设置时设置它（issue #48），文件夹留给本设计决定。 |
| D289 | D213 让 F07 功能循环里语言包的检查仍用 uv 默认的缓存。引擎给出的两条 uv 命令仍然不带 `UV_CACHE_DIR` 调用 uv：DV1 检查里第一个 mock 的 `uv pip install -e . --no-deps`（`troyflow/checksteps.py`），以及作为真实运行 `program-not-found` 问题修复的同一条安装命令（`troyflow/realexec.py`）。在 Windows 上，uv 不能跨盘重命名进它的缓存时，就会像试点第一次编译锁文件那样失败（tstack issue #48 的后续）。它们怎样拿到缓存？ | A：`series` 的规则（D213）：引擎的环境里 `UV_CACHE_DIR` 没有设置或为空时，命令以 `UV_LINK_MODE=copy UV_CACHE_DIR=<文件夹>` 开头，文件夹来自 `uv_cache_dir()`，按 shell 的规则加引号；否则只以 `UV_LINK_MODE=copy` 开头。真实运行的消息把文件夹显示为 `<uv cache>`，它的修复带着文件夹（第 5.4 节）。B：只设 `UV_CACHE_DIR`，不设 `UV_LINK_MODE`。C：在指南里写一句，请 Troy 在启动 Claude Code 之前设置 `UV_CACHE_DIR`。 | A，依据 Troy 2026-11-22 的长期同意批准。这样 troy-mode 给出的每条 uv 命令都像 troy-init 自己那样运行 uv，对锁文件有效的修复对安装也有效。B 漏掉了 troy-init 和 `series` 给 uv 的复制模式，C 让试点的失败在每台新电脑上重现。真实运行隐藏这个文件夹，因为消息会写进 PR 6 的描述，而它的证据不含 Troy 电脑上的文件夹（F12 设计第 8 节）。 |

| D291 | troy-init 什么时候加 R21 的分支规则？Troy 于 2026-11-28 要求在创建仓库时就加（"最好是troy-init在建仓库的时候就直接加上ruleset"），需求文档 1.71 写的是在初始化时、第一个 PR 之前。 | A：初始化时，`gh repo create` 之后立刻加；已经有 `origin` 的仓库在同一位置加，都在这一步的分支和 PR 之前。GitHub 列出规则缺少时，升级在问过之后也加上。语言步骤不看（第 4.7 节）。B：同 A，但升级不加，之前初始化的项目保持原样。C：在初始化 PR 合入之后，即现在必需检查那一步的位置。 | A，由 Troy 于 2026-11-28 批准（"其余按照推荐"）。规则在任何 PR 之前就生效，所以 PR 1 就在它之下合并，正如 Troy 所要求。升级是每个已有项目拿到 troy-mode 改动的途径（F02 D8）：recipe-menu 已经有这条规则，其他项目会加上。只有缺少规则时它才会问。C 让 PR 1 没有保护，还要在仓库那个问题之后再问一次。 |
| D292 | D52 建的是私有仓库。GitHub 只有在付费套餐下才在私有仓库上执行分支规则。2026-11-28，Troy 的私有仓库对分支保护探测回答的是 404，而不是 2026-11-07 的 403，所以 Troy 现在的套餐有分支规则；Troy 认为这是含 Pro 的 GitHub 学生包。免费或过期的套餐仍会回答 403。仓库那个问题给哪些选项？遇到 403 怎么办？ | A：保留 D52 的私有仓库。一次同意覆盖仓库和"在你的套餐允许时"加上的规则。技能对每个仓库都做探测（第 4.7 节）：回答 404 或 200 就加规则；回答提到套餐的 403 就不加，说明 R21 只靠本地 hook 保证，然后继续。troy-mode 里不写死任何套餐。B：每次都问公开还是私有，并说明取舍。C：总是公开。 | A，由 Troy 于 2026-11-28 批准（"education套餐在私有仓库上应该也可以创建ruleset"）。在 Troy 的套餐下私有仓库也能加规则，所以 D52 不需要改；套餐过期也只是失去规则，并有清楚的说明。B 在 Troy 的套餐下多问一个没有必要的问题，C 替 Troy 决定了隐私。需求文档的 F06 一行保留"建一个私有仓库"。 |
| D293 | 规则包含什么？F02 D14 还要求 troy-init 把 `troy-mode checks` 设为必需，1.6 版在初始化 PR 合入后用经典分支保护做这件事，而且只在 GitHub 提供时才做。R24 要求 PR 只在最新的 `main` 上合并，GitHub 的"必须是最新的"设置可以执行它。 | A：默认分支上两个规则集：R21 的，和 recipe-menu 的相同；以及 "troy-mode checks must pass"，检查为必需，"必须是最新的"关闭，取代经典分支保护那一步。B：只有 R21 的规则集；troy-init 不再把检查设为必需，经典分支保护那一步去掉（第 4.5 节和第 4.7 节）。C：一个规则集包含两者，"必须是最新的"打开。原先建议 A。 | B，由 Troy 于 2026-11-28 选定（"只保留R21的ruleset"），同时问到必需检查会不会让新测试失败的测试 PR 合不进去。troy-mode 的合并步骤仍然只在检查通过时才合并 PR（R18，F02 D14），所以 troy-mode 自己的合并不变。B 没有覆盖的：检查失败时，GitHub 不会拦住 Troy 自己在 GitHub 上的合并；Actions 跑不了时合并的 PR 也不会被拦住。 |
| D294 | 规则表模板里 R21 仍写着"Hook 和 CI"，R17 仍是第 3 轮升级上报、R18 没有抽查，这两项是 F18 留下的；它还缺 R24，是 F20 留下的。设计和测试计划模板的注释也还说第 3 轮会升级上报。角色考试把每个模板都算作全部 12 个用例的输入，所以这个修正要跑全部 12 个，第一轮约 $250 到 $400（F16 设计 10.1），加上第二轮最多约两倍。可是每个用例的项目都有自己的 `.troy-mode/templates/`，角色从那里填写模板（F04 共用规则第 7 条），所以这些运行看到的输入和之前一样。 | A：先收窄 `affected`：插件的模板只在用例的项目没有它的副本，或用例的任务简报写出了它的路径时，才算作这个用例的输入（第 8 节）。这个考试框架的改动会让每个用例的锚点重新证明一次：考试自己估算 $40，F17 第 1 步做同样的事时花了 $12.40（F17 设计第 12.5 节）。然后模板的各行，包括 R17 的注释，随分支规则一起合入，不影响任何用例。B：模板的各行跑完整考试，约 $250 到 $400，最多约两倍。C：模板先不改，等到某个反正要考试的改动再说，而升级会继续把旧的行带进项目。 | A，由 Troy 于 2026-11-28 批准（"其余按照推荐"）。这样考试只衡量真正到达角色的东西，修正的花费是十分之一。唯一写出插件模板路径的任务简报，是写着 `troy-mode/templates/rules.md` 的规则变更任务简报（F09），目前没有用例用它，所以以后用它的用例仍会把这个模板算进去。 |
| D295 | 分支规则怎样试运行？只作用于 `ZJUCao/troy-mode-trial` 的嵌套 `claude -p` 试运行已经预先批准，而那个仓库特意没有规则。创建或删除仓库需要 Troy 同意。 | A：两个试运行（第 11.4 节）：在 troy-mode-trial 上升级，加上 R21 的规则集，并在它之下合并它的 PR；以及在新的公开仓库 `ZJUCao/troy-init-trial` 的一个克隆里初始化，Troy 随本设计批准后由构建的会话建这个仓库。troy-mode-trial 上的规则集保留。没有试运行用私有仓库，因为 2026-11-28 时 Actions 在 Troy 的私有仓库上不运行。B：只做升级的试运行，初始化的路径只靠测试。C：不试运行，状态写"已编写"。 | A，由 Troy 于 2026-11-28 批准（"其余按照推荐"），用新的公开仓库。只有在 GitHub 上才能证明：troy-mode 的 rebase 合并在初始化和升级时都能通过 R21 的规则集。recipe-menu 目前两样都还没证明：它的规则集是 2026-11-28 UTC 17:15 加的，在它最后一次合并 PR 127 之后。私有仓库的路径要等真实使用。 |

需求文档 1.16 版记录了已批准的改动：

- F06 一行：初始化带来 troy-check 的 CI 任务，语言步骤带来语言包的任务，列出升级，每一步作为一个由 troy-init 合并的 `[rules]` PR 合入，没有 GitHub 仓库时 troy-init 创建一个私有仓库（D48、D52、D53、D54）。
- 5.1 第 2 步和第 4 步：troy-check 的工作流在初始化时加入，语言包的任务在检查这一步加入。
- Q10：F06 分两个 PR 合入（D55）。

## 14. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-06 | 初稿。 |
| 1.0 | 2026-11-06 | Troy 批准，含 D47 到 D56，全部采用推荐答案。 |
| 1.1 | 2026-11-07 | 第 8 节：troy-check 的 R12 跳过 `.troy-mode/`，Troy 于 2026-11-07 批准。第 11.5 节：第一部分同时带上这项改动和 D49 的配置行。构建第一部分时发现。 |
| 1.2 | 2026-11-07 | 第 3.2 节：`lang` 也接受 `--project-name`，选项表本来就说它用于构建文件。构建第二部分时发现。第 3.1 节和第 7 节：语言步骤和升级在试运行之前创建分支，因为每一步在 `main` 上都会停下。由第 11.4 节的试运行发现：这两步的试运行都在 `main` 上停下了。 |
| 1.3 | 2026-11-07 | 第 7 节第 8 步：合并前先分离 HEAD，最后运行 `git fetch origin`，取代 `git switch main` 和 `git pull --ff-only`，这样 troy-init 在工作树（worktree）里也能用，因为那里的 `main` 常常已在别处检出。技能里无事可做的升级，在删除自己的分支之前也这样分离 HEAD。来自 F07 设计第 12 节。 |
| 1.4 | 2026-11-09 | 第 4.2 节：troy-init 就地修改的文件保留原来的换行符，只有它新建的文件用 LF。升级也能读取 CRLF 换行的规则表，开启 `core.autocrlf` 的 Windows 检出里就是这样。由 F09 的试运行发现：在这样的检出里，升级在规则表的头部找不到版本，于是没有更新 R 行。 |
| 1.5 | 2026-11-18 | D213，来自 tstack issue #48，由 Troy 于 2026-11-18 批准：`UV_CACHE_DIR` 没有设置时，语言步骤和 `series` 把系统临时文件夹里的 `troy-mode-uv-cache` 给 uv 作缓存文件夹（第 5.4、11.1、11.2 和 13 节）。 |
| 1.6 | 2026-11-24 | D289，即 D213 的后续，依据 Troy 2026-11-22 的长期同意批准：DV1 检查里第一个 mock 的 `uv pip install -e . --no-deps` 和真实运行的安装修复都以 `series` 的 uv 变量开头，真实运行的消息把文件夹显示为 `<uv cache>`（第 5.4、11.1、11.2 和 13 节）。不改需求。 |
| 1.7 | 2026-11-28 | D291 到 D295，由 Troy 于 2026-11-28 批准，来自需求文档 1.71 和 Troy 同日的要求：在初始化的 PR 之前，以及缺少时在升级的 PR 之前，troy-init 在 GitHub 允许时给 `main` 加上 R21 的规则集，并且不再把 `troy-mode checks` 设为必需（D293 选 B）（新的第 4.7 节，第 1、3、4.5、6、7、8、9、11、12 和 13 节）。仓库仍是私有的；由探测判断套餐是否允许规则，已有的规则集保持原样。规则表模板里过时的行，以及角色考试看待模板的方式，也随之改动。 |
