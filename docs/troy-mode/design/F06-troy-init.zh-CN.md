# F06 设计：项目初始化（troy-init）

> 本文件是 [`F06-troy-init.md`](F06-troy-init.md) 的中文镜像，同步自英文版 1.5（2026-11-18）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.16](../requirements.zh-CN.md#72-功能列表) 中的 F06 |
| 版本 | 1.5 |
| 日期 | 2026-11-18 |
| 状态 | Troy 已于 2026-11-06 批准，含 D47 到 D56。第 8 节对 R12 的改动由 Troy 于 2026-11-07 批准。1.5 版加入 D213，由 Troy 于 2026-11-18 作为 tstack issue #48 批准。 |
| 事实来源 | 英文版 [`F06-troy-init.md`](F06-troy-init.md)。本文件是中文镜像。 |

## 1. 范围

F06 把一个文件夹变成 troy-mode 项目，并让其中 troy-mode 的文件保持最新。它交付一个技能 `/troy-pstack:troy-init` 和它背后的引擎，分三步：

1. **初始化**（需求文档 5.1 第 2 步）：标记文件夹，里面有配置、troy-check 及其 git hook、模板和进度文件；规则表；PR 模板；带 troy-check 任务的 CI 工作流。
2. **语言步骤**（5.1 第 4 步），在 Troy 批准架构之后：F03 的语言包和它的 CI 任务。
3. **升级**（F02 D8）：把 troy-mode 自己的文件更新到插件的当前版本。

每一步都作为一个只有一个 commit 的 `[rules]` PR 合入。troy-init 开出这个 PR，检查通过后合并它（D53）。

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

技能先用 `--dry-run --json` 运行引擎。每一步在 `main` 上都会停下（第 4.1 节和第 5.1 节），所以语言步骤和升级要先创建这一步的分支（第 7 节第 2 步），再做试运行；升级没有东西要改时，再把这个分支删掉。初始化时如果文件夹还没有 `origin`，试运行的问题会指出缺少 `origin` 和所在分支；第 7 节的前两步会解决它们。它用一条消息、用 Troy 的语言，只问没有明确默认值的事：要不要创建 GitHub 仓库（D52），要不要替换一个不是 troy-init 写的文件（D48），以及语言步骤里环境所属的系列。然后它运行引擎，把结果走一遍第 7 节的 PR 流程，最后报告做了什么、没做什么。

### 3.2 引擎

```text
python troy_init.py setup   [--project-name <name>] --email <address> [common options]
python troy_init.py lang    (python | cpp) [--project-name <name>] [--environment <name>]
                            [--series <folder>]... [--package <name>] [--mamba <path>]
                            [--env-prefix <path>] [--no-env] [common options]
python troy_init.py upgrade [common options]

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

引擎只修改文件和仓库的 git 配置。它从不提交、推送或调用 GitHub：这些由主会话来做（F04 D29）。

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
- **必需检查。** F02 D14 要求 troy-init 在仓库允许时把 `troy-mode checks` 设为必需检查。初始化会问 GitHub 这个仓库能不能使用分支保护；免费套餐上的私有仓库不能。只有能用时，技能才会问 Troy，然后把检查设为必需。在 Troy 现在的套餐上，它会说明这个检查仍是可选的。

git 和 GitHub 里的其他设置都不改。

### 4.6 安装记录

`.troy-mode/install.toml` 记录：来自 `.claude-plugin/plugin.json` 的 troy-pstack 版本；插件文件夹是 git 代码目录时，troy-pstack 的 commit；每一步的日期；语言包；以及一张 `[files]` 表，列出 troy-init 拥有的每个文件的 SHA-256 哈希。troy-init 拥有它整份复制的文件：troy-check、模板、PR 模板、工作流和语言包的整份文件。升级时用这些哈希区分没改过的文件和被人改过的文件（D54）。`config.toml`、规则表、`.gitignore` 和构建文件一旦写入，就归项目所有。

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

**uv 的缓存文件夹（D213）。** 这一步可能写不了 uv 默认的缓存：试点中，在桌面应用的沙箱里，第一次编译锁文件失败，原因是 uv 写不了它（tstack issue #48）。所以 `UV_CACHE_DIR` 没有设置或为空时，本节的每条 mamba 和 uv 命令运行时都把 `UV_CACHE_DIR` 设为系统临时文件夹里的 `troy-mode-uv-cache` 文件夹，系统临时文件夹即 Python 的 `tempfile.gettempdir()` 返回的文件夹。文件夹不存在时由 uv 创建。已经设置的值原样传下去。F07 的 `troy_flow.py series`（F07 设计 8.7，D66）用本节的函数规划系列锁文件，也遵循同一规则：引擎的环境里 `UV_CACHE_DIR` 没有设置或为空时，它的两条命令都以 `UV_LINK_MODE=copy UV_CACHE_DIR=<文件夹>` 开头，文件夹按 shell 的规则加引号；有的时候，只以 `UV_LINK_MODE=copy` 开头，由运行命令的 shell 把这个值传下去。F07 功能循环里语言包的检查也调用 uv，在以后的改动之前仍用 uv 默认的缓存。

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

升级改动的每个路径都属于 `config` 或 `dependencies` 类别，所以它的 PR 是一个有效的 `[rules]` PR。

## 7. PR 流程（D53）

技能在引擎前后执行这些步骤。F07 自己运行引擎时，也执行同样的步骤。

1. **仓库。** 如果文件夹不是 git 仓库，就 `git init -b main`。如果没有 `origin`，技能问 Troy 一次：要不要在 Troy 的账号下创建一个以项目命名的私有 GitHub 仓库。回答是的话：`gh repo create <owner>/<name> --private --add-readme`，然后 `git remote add origin` 和 `git fetch origin`。`main` 上的第一个 commit 由 GitHub 生成，所以没有人在本地 `main` 上提交（R21，D52）。
2. **分支。** `git switch -c troy-mode/init origin/main`，或者 `troy-mode/lang-<name>`、`troy-mode/upgrade-<version>`。语言步骤和升级在试运行之前就创建它（第 3.1 节）。
3. **引擎。** 运行这一步。
4. **暂存。** 只 `git add` 引擎报告列出的路径，git hook 加 `--chmod=+x`。从不用 `git add -A`。
5. **提交。** 一个 commit，标题行等于 PR 标题（R01）：`[rules] Set up troy-mode`、`[rules] Add the Python pack` 或 `[rules] Add the C/C++ pack`、`[rules] Upgrade troy-mode to <version>`。F05 的 `commit-msg` hook 会检查它（R19）。
6. **检查。** 用标题和描述运行 `troy-check pr`。有任何 `fail` 就停下。
7. **PR。** `git push -u origin <branch>`，然后 `gh pr create --base main`，描述按 PR 模板写：Why、What、Checks，Soft-limit reason 写 "None"。
8. **合并。** 用 `gh pr checks <number> --watch` 等一次检查。全部通过就先运行 `git switch --detach`，再用 `gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>` 合并，因为 R18 允许 Claude 合并除前几个功能的 PR 1 和 PR 2 之外的所有 PR。先分离 HEAD，`gh` 就不会在删除分支之前去检出 `main`。有失败就停下并报告。然后运行 `git fetch origin`，并把这一步记进进度文件。

```text
Troy:   /troy-pstack:troy-init
Claude: 这个文件夹还没有 GitHub 仓库。要创建私有仓库 ZJUCao/habit-tracker 吗？
Troy:   要。
Claude: 初始化完成。
  PR #1 "[rules] Set up troy-mode"：troy-check 通过（R01、R02、R12、R19、R20），已合并。
  git hook 已打开。你的套餐不能用分支保护，所以这个检查仍是可选的。
  下一步：需求（产品经理）。
```

## 8. 对已有功能的改动

实现 F06 时，还要改动：

- **F03 的语言包。** 两个 `workflow-job.yml` 都加上第 5.6 节的那一步，对应的示例工作流也跟着改，这样 `test_python_pack.py` 和 `test_cpp_pack.py` 仍然能比较它们。C/C++ 的配置片段把 `include/troy/not_implemented.h` 加进 `config`（D49）。每个语言包增加新项目的构建文件，以及 README 里对应的行。F03 的设计加一行修改记录。
- **`build_sample.py`。** 它改用 troy-init 写文件的那些函数来搭建每个示例，不检查第 4.1 节和第 5.1 节的前提条件，也不创建环境，代替它自己的 `install_pack`，这样示例的搭建方式和 troy-init 搭建项目完全相同。它还增加一个示例状态：只做了初始化和语言步骤、还没有代码，语言包的任务在上面必须跳过代码步骤并通过。

- **troy-check 的 R12。** R12 不把 `.troy-mode/` 下的文件当文档，和 R20 不扫描这里一样（F02 设计 6.7）。初始化把模板原样复制到这里，它们的文档头带着标记，`troy-doc` 也和项目自己的文档相同，不这样做的话，每个初始化 PR 和之后每个改文档的 PR 都会让 R12 失败。构建第一部分时发现，Troy 于 2026-11-07 批准。F02 的设计在它的 1.2 版里记下了这一点。

F01、F04 和 F05 不变。

## 9. F06 怎样对应需求

| 需求 | F06 在哪里覆盖 |
| --- | --- |
| F06 一行：标记文件夹、文档骨架、规则表、进度文件 | 第 4.2 节和第 4.4 节。文档骨架就是 `.troy-mode/templates/` 里的模板。 |
| F06 一行：架构批准后，语言包和 CI 工作流 | 第 5 节。troy-check 的任务更早，在初始化时就加入（第 4.2 节，D48），所以需求 PR 和架构 PR 也会被检查 |
| 5.1 第 2 步和第 4 步 | 第 4 节和第 5 节 |
| F02 D8：复制检查、记录版本、在 `[rules]` PR 里重新运行 troy-init 来升级 | 第 4.2、4.6 和 6 节 |
| F02 D14：仓库允许时把检查设为必需 | 第 4.5 节 |
| troy-init 自己的 PR 满足 R01、R02、R12、R19、R20 | 第 4.2、4.4 和 7 节 |
| R18：前几个功能的 PR 1 和 PR 2 以外，都由 Claude 合并 | 第 7 节第 8 步 |
| R21：不在 `main` 上提交 | 第 7 节第 1 步和第 2 步 |
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
| 环境 | PATH 上放一个记录参数的假 `mamba`：只在环境不存在时创建，锁文件根据每个成员的清单文件编译，`--env-prefix` 和 `--no-env` 都有效。uv 的缓存文件夹（D213）：`UV_CACHE_DIR` 未设置或为空时，每次调用都得到临时文件夹里的 `troy-mode-uv-cache`，已经设置的值原样不变；`series` 只在这个变量未设置或为空时把文件夹写进两条命令。没有测试使用网络。 |
| 升级 | 没改过的自有文件被替换，改过的会让这一步停下。新增的模板被创建。R 规则行被替换，P 规则行和起始日期保留，中英文的版本都升高。配置从不修改。 |
| 技能 | `SKILL.md` 的 front matter 有 `name: troy-init` 和 `disable-model-invocation: true`。正文写出了三个步骤和 PR 流程的各步。 |

### 11.2 埋 bug

代码通过后，在临时副本里一次埋一个 bug，每个都必须让某个测试失败。包括：覆盖了已有文件、规则表里留了标记、镜像版本不一致、配置里缺了某个语言包的模式、`[lang]` 表没填、已有测试没列出、没检查架构是否批准、git hook 没有可执行位、升级时丢了 P 规则行、升级时替换了被改过的自有文件，以及没有加入语言包的任务。D213 的改动再加上：覆盖了已经设置的值、`series` 的安装命令里缺了文件夹、文件夹不在临时文件夹里。数量写在 PR 描述里。

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

### 11.5 状态

| 时间点 | 需求文档 7.2 中 F06 的状态 |
| --- | --- |
| 第 1 部分合入 | 已编写，2 部分中的第 1 部分：初始化和升级。它的单元测试在 Troy 的电脑上通过。 |
| 第 2 部分在试运行通过后合入 | 在示例项目上跑通：troy-init 搭建了一个临时 GitHub 项目，它的初始化 PR 和语言 PR 都通过了 CI 并合入。还没有在真实项目上用过。 |
| 试点（F11）用 troy-init 开始 | 在真实项目上用过 |

F06 分两个 PR 合入（D55），每个只有一个 commit，测试都先写：

1. **初始化和升级。** 技能、引擎的初始化和升级，以及它们的测试。还包括第 8 节对 R12 的改动，以及 C/C++ 配置片段里 `include/troy/not_implemented.h` 那一行（D49），因为初始化要把这个模式写进配置。
2. **语言步骤。** 引擎的语言步骤、F03 语言包的改动、`build_sample.py`、它们的测试，以及试运行。

每次状态更新都单独开一个 PR。

## 12. 不在 F06 里的

- 写需求文档和架构文档、开它们的 PR，以及在各流程中运行 troy-init（F04 的角色和 F07）。
- 为系列中的其他成员创建环境、更新它们的锁文件（F07，F03 设计 8.1）。
- 项目自己的规则（F09）。升级只带来 troy-mode 的 R 规则。
- TypeScript/JavaScript 语言包（以后，Q1）。
- 插件文件的权限规则（F05 D45）。
- 删除试运行用的仓库。

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
